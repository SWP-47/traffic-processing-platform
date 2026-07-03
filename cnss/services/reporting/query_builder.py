# ==============================================================================
# CnSS Query Builder Utilities
# Provides safe, parameterized SQL fragment generation for dynamic subscriptions.
# Enforces strict whitelisting for SQL identifiers (ORDER BY, LIMIT) to prevent
# SQL Injection, as identifiers cannot be parameterized via asyncpg.
#
# This module is subscription-agnostic. Each subscription handler defines its
# own whitelist and passes it to the builder methods.
# ==============================================================================
import logging
from typing import Any, Dict, List, Optional

# --- Module Logger ---
logger = logging.getLogger(__name__)

# --- Default Limits ---
# Sensible defaults for LIMIT clause enforcement.
DEFAULT_LIMIT = 50
MAX_LIMIT = 1000

# --- Sort Order Whitelist ---
# Strictly limits sort direction to prevent SQL injection via ORDER BY clause.
# This is universal across all subscription targets.
SORT_ORDER_WHITELIST: Dict[str, str] = {
    "asc": "ASC",
    "desc": "DESC",
}

# --- Period Mapping ---
# Maps human-readable period strings to PostgreSQL INTERVAL literals.
# Used by hosts_table, host_details, host_top_destinations, host_top_ports.
PERIOD_TO_INTERVAL: Dict[str, str] = {
    "5m": "5 minutes",
    "15m": "15 minutes",
    "1h": "1 hour",
    "24h": "24 hours",
    "7d": "7 days",
    "30d": "30 days",
}
DEFAULT_PERIOD = "5m"


# ==============================================================================
# Parameterized Query Builder
# ==============================================================================


class ParameterizedQuery:
    """
    Tracks positional parameter placeholders ($1, $2, ...) and their values
    for asyncpg queries. Enables dynamic WHERE clause construction with
    a variable number of filters while maintaining SQL injection safety.

    Usage:
        pq = ParameterizedQuery(start_index=1)
        ph1 = pq.add_param("bridge-01")   # returns "$1"
        ph2 = pq.add_param(50)             # returns "$2"
        conn.fetch(f"WHERE id = {ph1} LIMIT {ph2}", *pq.get_params())
    """

    def __init__(self, start_index: int = 1) -> None:
        """
        Initializes the parameter tracker.

        :param start_index: The first parameter index to use (default 1).
                            Use values > 1 when combining with pre-defined parameters.
        """
        self._params: List[Any] = []
        self._next_index = start_index

    def add_param(self, value: Any) -> str:
        """
        Registers a parameter value and returns its placeholder string ($N).
        Each call increments the internal index counter automatically.

        :param value: The parameter value (string, int, float, etc.).
        :return: The asyncpg placeholder string (e.g., "$1", "$2").
        """
        placeholder = f"${self._next_index}"
        self._params.append(value)
        self._next_index += 1
        return placeholder

    def get_params(self) -> List[Any]:
        """
        Returns a copy of the accumulated parameter values in insertion order.
        Safe to pass directly to asyncpg's fetch/execute methods.
        """
        return list(self._params)

    @property
    def next_index(self) -> int:
        """Returns the next available parameter index (useful for combining queries)."""
        return self._next_index


# ==============================================================================
# Legacy SQL Fragment Builders (used by TelemetryHandler)
# These use fixed parameter indices and are kept for backward compatibility.
# ==============================================================================


def build_order_by(
    sort_by: Optional[str],
    sort_order: Optional[str],
    sort_whitelist: Dict[str, str],
) -> str:
    """
    Safely constructs an ORDER BY SQL clause using strict whitelisting.
    Returns an empty string if inputs are invalid or missing, ensuring
    no SQL injection is possible through user-controlled identifiers.

    :param sort_by: User-provided column alias (e.g., 'received', 'total').
    :param sort_order: User-provided direction ('asc' or 'desc').
    :param sort_whitelist: Target-specific mapping of user aliases to SQL expressions.
                           Keys should be lowercase for case-insensitive matching.
    :return: A safe SQL ORDER BY fragment (e.g., "ORDER BY packets_in DESC") or "".
    """
    # If no sort_by is provided, return empty string (DB will use default ordering)
    if not sort_by:
        logger.debug("No sort_by provided. Skipping ORDER BY clause.")
        return ""

    # Validate sort_by against the provided whitelist (case-insensitive)
    normalized_sort_by = sort_by.lower().strip()
    sql_column = sort_whitelist.get(normalized_sort_by)
    if not sql_column:
        logger.warning(
            f"Invalid sort_by '{sort_by}'. "
            f"Allowed values: {list(sort_whitelist.keys())}. Skipping ORDER BY."
        )
        return ""

    # Validate sort_order (default to ASC if invalid or missing)
    normalized_order = (sort_order or "asc").lower().strip()
    sql_order = SORT_ORDER_WHITELIST.get(normalized_order, "ASC")
    if normalized_order not in SORT_ORDER_WHITELIST:
        logger.debug(
            f"Invalid sort_order '{sort_order}'. Defaulting to ASC."
        )

    # Construct the safe fragment
    order_clause = f"ORDER BY {sql_column} {sql_order}"
    logger.debug(f"Built ORDER BY clause: {order_clause}")
    return order_clause


def build_limit(
    limit: Optional[int],
    default_limit: int = DEFAULT_LIMIT,
    max_limit: int = MAX_LIMIT,
) -> str:
    """
    Safely constructs a LIMIT SQL clause with boundary enforcement.

    :param limit: User-provided limit value.
    :param default_limit: Default limit if none is provided.
    :param max_limit: Hard cap to prevent excessive memory usage or DB load.
    :return: A safe SQL LIMIT fragment (e.g., "LIMIT 50") or "".
    """
    if limit is None:
        effective_limit = default_limit
        logger.debug(f"No limit provided. Using default: {default_limit}")
    else:
        # Enforce boundaries: must be positive and not exceed max_limit
        effective_limit = max(1, min(limit, max_limit))
        if limit != effective_limit:
            logger.debug(
                f"Limit {limit} adjusted to {effective_limit} "
                f"(bounds: 1-{max_limit})"
            )

    limit_clause = f"LIMIT {effective_limit}"
    logger.debug(f"Built LIMIT clause: {limit_clause}")
    return limit_clause


def build_where_channel(channel_id: str) -> str:
    """
    Constructs a safe WHERE clause for filtering by channel_id.
    Uses parameterized query placeholder ($1) to prevent SQL injection.

    :param channel_id: The channel identifier to filter by.
    :return: A SQL WHERE clause fragment (e.g., "WHERE channel_id = $1").
    """
    if not channel_id:
        logger.warning("Empty channel_id provided. WHERE clause will be empty.")
        return ""

    where_clause = "WHERE channel_id = $1"
    logger.debug(f"Built WHERE clause: {where_clause} for channel '{channel_id}'")
    return where_clause


def build_time_window(window_sec: Optional[float], param_index: int = 2) -> str:
    """
    Constructs a safe time window filter using parameterized interval calculation.

    :param window_sec: Time window in seconds. Defaults to 5.0 if not provided.
    :param param_index: The parameter index for asyncpg (e.g., $2, $3).
    :return: A SQL time filter fragment (e.g., "AND time > NOW() - ($2 * INTERVAL '1 second')").
    """
    effective_window = window_sec if window_sec and window_sec > 0 else 5.0
    time_clause = f"AND time > NOW() - (${param_index} * INTERVAL '1 second')"
    logger.debug(f"Built time window clause: {time_clause} (window: {effective_window}s)")
    return time_clause


# ==============================================================================
# Dynamic SQL Fragment Builders (used by new subscription handlers)
# These use ParameterizedQuery for flexible parameter index tracking.
# ==============================================================================


def resolve_period_interval(period: Optional[str]) -> str:
    """
    Maps a human-readable period string to a PostgreSQL INTERVAL literal.
    Falls back to DEFAULT_PERIOD if the input is invalid or None.

    The returned string is a hardcoded SQL literal (e.g., "5 minutes"),
    NOT user input — it is selected from a fixed dictionary.

    :param period: Period string (e.g., "5m", "1h", "7d").
    :return: A valid PostgreSQL INTERVAL literal string.
    """
    if period and period in PERIOD_TO_INTERVAL:
        return PERIOD_TO_INTERVAL[period]
    logger.debug(f"Invalid or missing period '{period}'. Using default: {DEFAULT_PERIOD}")
    return PERIOD_TO_INTERVAL[DEFAULT_PERIOD]


def build_ip_exact_filter(
    ip: Optional[str],
    ip_column: str,
    pq: ParameterizedQuery,
) -> str:
    """
    Builds a SQL equality expression for exact IP address matching.
    Uses parameterized query placeholder to prevent SQL injection.
    The ::inet cast ensures PostgreSQL treats the value as a network address.

    The ip_column parameter MUST come from a handler-defined whitelist.

    :param ip: IP address string or None (no filter applied).
    :param ip_column: Whitelisted SQL column name to compare against.
    :param pq: ParameterizedQuery instance for placeholder tracking.
    :return: A SQL equality expression or empty string.
    """
    if not ip:
        return ""

    placeholder = pq.add_param(ip)
    fragment = f"{ip_column} = {placeholder}::inet"
    logger.debug(f"Built IP exact filter: {fragment}")
    return fragment


def build_offset(
    offset: Optional[int],
    pq: ParameterizedQuery,
) -> str:
    """
    Builds a safe OFFSET SQL clause with parameterized value.
    Returns empty string for offset=0 (no offset needed).

    :param offset: Pagination offset or None (defaults to 0).
    :param pq: ParameterizedQuery instance for placeholder tracking.
    :return: A SQL OFFSET fragment (e.g., "OFFSET $3") or empty string.
    """
    effective_offset = max(0, offset) if offset is not None else 0
    if effective_offset == 0:
        return ""

    placeholder = pq.add_param(effective_offset)
    fragment = f"OFFSET {placeholder}"
    logger.debug(f"Built OFFSET clause: {fragment}")
    return fragment


def build_limit_param(
    limit: Optional[int],
    pq: ParameterizedQuery,
    default_limit: int = DEFAULT_LIMIT,
    max_limit: int = MAX_LIMIT,
) -> str:
    """
    Parameterized version of build_limit for use with ParameterizedQuery.
    Enforces boundary constraints and uses a placeholder instead of interpolation.

    :param limit: User-provided limit value.
    :param pq: ParameterizedQuery instance for placeholder tracking.
    :param default_limit: Default limit if none is provided.
    :param max_limit: Hard cap to prevent excessive memory usage or DB load.
    :return: A parameterized SQL LIMIT fragment (e.g., "LIMIT $4").
    """
    if limit is None:
        effective_limit = default_limit
        logger.debug(f"No limit provided. Using default: {default_limit}")
    else:
        effective_limit = max(1, min(limit, max_limit))
        if limit != effective_limit:
            logger.debug(
                f"Limit {limit} adjusted to {effective_limit} "
                f"(bounds: 1-{max_limit})"
            )

    placeholder = pq.add_param(effective_limit)
    fragment = f"LIMIT {placeholder}"
    logger.debug(f"Built parameterized LIMIT clause: {fragment}")
    return fragment
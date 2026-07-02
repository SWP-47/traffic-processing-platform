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
from typing import Dict, Optional

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

# --- SQL Fragment Builders ---

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
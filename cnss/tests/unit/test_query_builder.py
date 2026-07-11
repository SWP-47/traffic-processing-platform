# ==============================================================================
# CnSS SQL Query Builder Unit Tests
# Validates parameters tracking, sorting whitelisting, boundary limitations,
# and PostgreSQL dynamic filter construction functions in query_builder.
# ==============================================================================

import pytest
from services.reporting.query_builder import (
    ParameterizedQuery,
    build_order_by,
    build_limit,
    build_where_channel,
    build_time_window,
    resolve_period_interval,
    build_ip_exact_filter,
    build_offset,
    build_limit_param,
)

# Whitelist map for testing sorting functions
TEST_SORT_WHITELIST = {
    "packets": "packets_in + packets_out",
    "received": "packets_in",
    "sent": "packets_out",
}


def test_parameterized_query_tracker():
    """
    Ensure ParameterizedQuery correctly tracks values, dynamically assigns
    index placeholders, and supports retrieval in insertion order.
    """
    pq = ParameterizedQuery(start_index=1)
    
    assert pq.next_index == 1
    
    ph1 = pq.add_param("bridge-01")
    assert ph1 == "$1"
    assert pq.next_index == 2
    
    ph2 = pq.add_param(42)
    assert ph2 == "$2"
    assert pq.next_index == 3
    
    assert pq.get_params() == ["bridge-01", 42]


def test_parameterized_query_custom_start_index():
    """
    Ensure tracker can start at a custom positional index (e.g. index > 1).
    """
    pq = ParameterizedQuery(start_index=3)
    assert pq.next_index == 3
    ph = pq.add_param("value")
    assert ph == "$3"
    assert pq.get_params() == ["value"]


def test_build_order_by_whitelisting():
    """
    Verify build_order_by generates safe sorting clauses only for whitelisted columns
    and correctly falls back to ASC or skips clause construction when invalid or empty.
    """
    # 1. Successful ascending sort
    clause = build_order_by("received", "asc", TEST_SORT_WHITELIST)
    assert clause == "ORDER BY packets_in ASC"

    # 2. Case insensitive & whitespace stripping matching
    clause_desc = build_order_by(" SENT  ", "DESC", TEST_SORT_WHITELIST)
    assert clause_desc == "ORDER BY packets_out DESC"

    # 3. Invalid sort column (should skip clause)
    clause_invalid = build_order_by("invalid_column", "desc", TEST_SORT_WHITELIST)
    assert clause_invalid == ""

    # 4. Invalid sort order direction (defaults to ASC)
    clause_default_dir = build_order_by("packets", "invalid_dir", TEST_SORT_WHITELIST)
    assert clause_default_dir == "ORDER BY packets_in + packets_out ASC"

    # 5. Empty sort_by parameter
    clause_empty = build_order_by(None, "desc", TEST_SORT_WHITELIST)
    assert clause_empty == ""


def test_build_limit_boundary_enforcement():
    """
    Verify build_limit generates correct SQL fragments and clamps bounds properly.
    """
    # 1. No limit provided (uses default)
    assert build_limit(None, default_limit=10, max_limit=100) == "LIMIT 10"

    # 2. Limit within bounds
    assert build_limit(25, default_limit=10, max_limit=100) == "LIMIT 25"

    # 3. Limit exceeding max_limit (clamps to max)
    assert build_limit(150, default_limit=10, max_limit=100) == "LIMIT 100"

    # 4. Negative limit (clamps to 1)
    assert build_limit(-5, default_limit=10, max_limit=100) == "LIMIT 1"


def test_build_where_channel():
    """
    Verify channel WHERE clause helper.
    """
    assert build_where_channel("ch-1") == "WHERE channel_id = $1"
    assert build_where_channel("") == ""


def test_build_time_window():
    """
    Verify parameterized time window constraints.
    """
    assert build_time_window(10.0, param_index=2) == "AND time > NOW() - ($2 * INTERVAL '1 second')"
    # Defaults to 5.0 when window_sec is invalid/missing
    assert build_time_window(None, param_index=3) == "AND time > NOW() - ($3 * INTERVAL '1 second')"
    assert build_time_window(-2.0, param_index=3) == "AND time > NOW() - ($3 * INTERVAL '1 second')"


def test_resolve_period_interval():
    """
    Verify conversion of numeric period seconds to PostgreSQL INTERVAL literal.
    """
    assert resolve_period_interval(120.5) == "120.5 seconds"
    # Fallback default (5 minutes / 300 seconds) when period is None or negative
    assert resolve_period_interval(None) == "300.0 seconds"
    assert resolve_period_interval(-10.0) == "300.0 seconds"


def test_build_ip_exact_filter():
    """
    Verify exact IP comparison clause with ParameterizedQuery.
    """
    pq = ParameterizedQuery(start_index=1)
    
    # 1. Valid filter
    clause = build_ip_exact_filter("192.168.1.1", "src_ip", pq)
    assert clause == "src_ip = $1::inet"
    assert pq.get_params() == ["192.168.1.1"]

    # 2. Missing IP parameter
    clause_empty = build_ip_exact_filter(None, "dst_ip", pq)
    assert clause_empty == ""


def test_build_offset():
    """
    Verify build_offset pagination helper.
    """
    pq = ParameterizedQuery(start_index=1)

    # 1. Offset = 0 (ignored/skipped)
    assert build_offset(0, pq) == ""
    assert build_offset(None, pq) == ""
    assert build_offset(-10, pq) == ""
    assert len(pq.get_params()) == 0

    # 2. Offset > 0
    clause = build_offset(25, pq)
    assert clause == "OFFSET $1"
    assert pq.get_params() == [25]


def test_build_limit_param():
    """
    Verify build_limit_param clamps parameters and populates ParameterizedQuery correctly.
    """
    pq = ParameterizedQuery(start_index=1)

    # 1. Limit None (uses default)
    assert build_limit_param(None, pq, default_limit=15, max_limit=50) == "LIMIT $1"
    assert pq.get_params() == [15]

    # 2. Clamped value
    pq2 = ParameterizedQuery(start_index=1)
    assert build_limit_param(200, pq2, default_limit=10, max_limit=100) == "LIMIT $1"
    assert pq2.get_params() == [100]

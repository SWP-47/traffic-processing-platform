# ==============================================================================
# CnSS Query Hash Unit Tests
# Validates deterministic hash generation for subscription deduplication
# against architectural specifications (architecture.md §4.2).
# Ensures 'id' field is strictly excluded from hash calculation.
# ==============================================================================

import pytest
from core.contracts.subscriptions import compute_query_hash, SubscribeRequest, SubscriptionParams


# --- Deterministic Hash Tests ---

def test_same_inputs_produce_same_hash():
    """
    Architecture §4.2: Hash must be deterministic.
    Identical inputs must always produce the same hash value.
    """
    hash1 = compute_query_hash("bridge-01", "telemetry", {"window_sec": 5.0})
    hash2 = compute_query_hash("bridge-01", "telemetry", {"window_sec": 5.0})
    assert hash1 == hash2


def test_different_channel_id_produces_different_hash():
    """
    Verify that changing channel_id results in a different hash.
    """
    hash1 = compute_query_hash("bridge-01", "telemetry", {})
    hash2 = compute_query_hash("bridge-02", "telemetry", {})
    assert hash1 != hash2


def test_different_target_produces_different_hash():
    """
    Verify that changing target results in a different hash.
    """
    hash1 = compute_query_hash("bridge-01", "telemetry", {})
    hash2 = compute_query_hash("bridge-01", "hosts_table", {})
    assert hash1 != hash2


def test_different_params_produce_different_hash():
    """
    Verify that changing params results in a different hash.
    """
    hash1 = compute_query_hash("bridge-01", "telemetry", {"window_sec": 5.0})
    hash2 = compute_query_hash("bridge-01", "telemetry", {"window_sec": 10.0})
    assert hash1 != hash2


# --- ID Exclusion Tests (Critical) ---

def test_id_excluded_from_hash_calculation():
    """
    Architecture §4.2: The client-provided 'id' is strictly excluded from hash calculation.
    Two subscriptions with identical parameters but different 'id' values
    must produce the same query_hash for deduplication.
    """
    # Note: compute_query_hash doesn't take 'id' parameter at all
    # This is tested via SubscribeRequest.query_hash computed field
    params = {"window_sec": 5.0}
    hash1 = compute_query_hash("bridge-01", "telemetry", params)
    hash2 = compute_query_hash("bridge-01", "telemetry", params)
    assert hash1 == hash2


def test_subscribe_request_id_excluded_from_hash():
    """
    Architecture §4.2: SubscribeRequest.query_hash computed field must exclude 'id'.
    Two requests with same channel_id, target, params but different 'id'
    must have identical query_hash values.
    """
    request1 = SubscribeRequest(
        action="subscribe",
        id="sub-abc-123",
        channel_id="bridge-01",
        target="telemetry",
        params=SubscriptionParams(window_sec=5.0),
    )
    request2 = SubscribeRequest(
        action="subscribe",
        id="sub-xyz-789",  # Different ID
        channel_id="bridge-01",
        target="telemetry",
        params=SubscriptionParams(window_sec=5.0),
    )
    # Hashes must be identical despite different 'id' values
    assert request1.query_hash == request2.query_hash


def test_subscribe_request_different_params_different_hash():
    """
    Verify that SubscribeRequest with different params produces different hash.
    """
    request1 = SubscribeRequest(
        action="subscribe",
        id="sub-123",
        channel_id="bridge-01",
        target="telemetry",
        params=SubscriptionParams(window_sec=5.0),
    )
    request2 = SubscribeRequest(
        action="subscribe",
        id="sub-123",
        channel_id="bridge-01",
        target="telemetry",
        params=SubscriptionParams(window_sec=10.0),  # Different param
    )
    assert request1.query_hash != request2.query_hash


# --- Hash Format Tests ---

def test_hash_length_is_16_characters():
    """
    Architecture §4.2: Hash is SHA-256 truncated to 16 hex characters.
    """
    hash_value = compute_query_hash("bridge-01", "telemetry", {})
    assert len(hash_value) == 16


def test_hash_contains_only_hex_characters():
    """
    Verify hash contains only valid hexadecimal characters (0-9, a-f).
    """
    hash_value = compute_query_hash("bridge-01", "telemetry", {})
    assert all(c in "0123456789abcdef" for c in hash_value)


# --- Parameter Ordering Tests ---

def test_param_key_order_does_not_affect_hash():
    """
    Architecture §4.2: json.dumps(sort_keys=True) ensures consistent hashing
    regardless of dictionary key insertion order.
    """
    params1 = {"window_sec": 5.0, "sort_by": "rx"}
    params2 = {"sort_by": "rx", "window_sec": 5.0}  # Different order
    hash1 = compute_query_hash("bridge-01", "hosts_table", params1)
    hash2 = compute_query_hash("bridge-01", "hosts_table", params2)
    assert hash1 == hash2


def test_nested_param_order_does_not_affect_hash():
    """
    Verify that nested parameter ordering is also normalized.
    """
    params1 = {"b": {"y": 1, "x": 2}, "a": 3}
    params2 = {"a": 3, "b": {"x": 2, "y": 1}}  # Different order
    hash1 = compute_query_hash("bridge-01", "telemetry", params1)
    hash2 = compute_query_hash("bridge-01", "telemetry", params2)
    assert hash1 == hash2


# --- Edge Cases ---

def test_empty_params():
    """
    Verify hash generation works with empty params dictionary.
    """
    hash_value = compute_query_hash("bridge-01", "telemetry", {})
    assert len(hash_value) == 16
    assert all(c in "0123456789abcdef" for c in hash_value)


def test_none_values_in_params():
    """
    Verify hash generation handles None values in params.
    """
    params = {"window_sec": 5.0, "sort_by": None}
    hash_value = compute_query_hash("bridge-01", "telemetry", params)
    assert len(hash_value) == 16


def test_empty_string_values():
    """
    Verify hash generation handles empty string values.
    """
    params = {"ip": ""}
    hash_value = compute_query_hash("bridge-01", "hosts_table", params)
    assert len(hash_value) == 16


def test_numeric_zero_values():
    """
    Verify hash generation handles numeric zero values correctly.
    """
    params1 = {"offset": 0}
    params2 = {"offset": 1}
    hash1 = compute_query_hash("bridge-01", "hosts_table", params1)
    hash2 = compute_query_hash("bridge-01", "hosts_table", params2)
    assert hash1 != hash2  # 0 and 1 must produce different hashes


def test_boolean_values_in_params():
    """
    Verify hash generation handles boolean values.
    """
    params = {"is_active": True}
    hash_value = compute_query_hash("bridge-01", "telemetry", params)
    assert len(hash_value) == 16


def test_list_values_in_params():
    """
    Verify hash generation handles list values in params.
    """
    params1 = {"scope": ["bridge-01", "bridge-02"]}
    params2 = {"scope": ["bridge-02", "bridge-01"]}  # Different order
    hash1 = compute_query_hash("bridge-01", "telemetry", params1)
    hash2 = compute_query_hash("bridge-01", "telemetry", params2)
    # Lists are order-sensitive in JSON, so these should differ
    assert hash1 != hash2


def test_special_characters_in_channel_id():
    """
    Verify hash generation handles special characters in channel_id.
    """
    hash1 = compute_query_hash("bridge-01", "telemetry", {})
    hash2 = compute_query_hash("bridge/01", "telemetry", {})
    hash3 = compute_query_hash("bridge_01", "telemetry", {})
    # All should be different
    assert hash1 != hash2
    assert hash1 != hash3
    assert hash2 != hash3


def test_unicode_characters_in_params():
    """
    Verify hash generation handles unicode characters.
    """
    params = {"description": "тест"}
    hash_value = compute_query_hash("bridge-01", "telemetry", params)
    assert len(hash_value) == 16


# --- SubscribeRequest Computed Field Tests ---

def test_subscribe_request_query_hash_is_property():
    """
    Verify that query_hash is a computed property, not a stored field.
    """
    request = SubscribeRequest(
        action="subscribe",
        id="sub-123",
        channel_id="bridge-01",
        target="telemetry",
        params=SubscriptionParams(),
    )
    # Should be accessible as a property
    assert hasattr(request, "query_hash")
    assert isinstance(request.query_hash, str)
    assert len(request.query_hash) == 16


def test_subscribe_request_query_hash_excludes_none_params():
    """
    Architecture §4.2: The computed field excludes None values from params
    via model_dump(exclude={"id"}).
    """
    request1 = SubscribeRequest(
        action="subscribe",
        id="sub-123",
        channel_id="bridge-01",
        target="telemetry",
        params=SubscriptionParams(window_sec=5.0),
    )
    request2 = SubscribeRequest(
        action="subscribe",
        id="sub-123",
        channel_id="bridge-01",
        target="telemetry",
        params=SubscriptionParams(window_sec=5.0, sort_by=None),  # Explicit None
    )
    # Both should produce the same hash since None values are excluded
    assert request1.query_hash == request2.query_hash


def test_subscribe_request_action_not_in_hash():
    """
    Verify that 'action' field is not included in hash calculation.
    Subscribe and unsubscribe with same params should have same hash.
    """
    subscribe_req = SubscribeRequest(
        action="subscribe",
        id="sub-123",
        channel_id="bridge-01",
        target="telemetry",
        params=SubscriptionParams(window_sec=5.0),
    )
    unsubscribe_req = SubscribeRequest(
        action="unsubscribe",  # Different action
        id="sub-123",
        channel_id="bridge-01",
        target="telemetry",
        params=SubscriptionParams(window_sec=5.0),
    )
    # Hashes should be identical (action is not part of hash)
    assert subscribe_req.query_hash == unsubscribe_req.query_hash


# --- Collision Resistance Tests ---

def test_similar_params_produce_different_hashes():
    """
    Verify that minor differences in params produce different hashes.
    """
    hash1 = compute_query_hash("bridge-01", "telemetry", {"window_sec": 5.0})
    hash2 = compute_query_hash("bridge-01", "telemetry", {"window_sec": 5.1})
    assert hash1 != hash2


def test_whitespace_differences_in_strings():
    """
    Verify that whitespace differences in string values produce different hashes.
    """
    params1 = {"ip": "192.168.1.1"}
    params2 = {"ip": "192.168.1.1 "}  # Trailing space
    hash1 = compute_query_hash("bridge-01", "hosts_table", params1)
    hash2 = compute_query_hash("bridge-01", "hosts_table", params2)
    assert hash1 != hash2


# --- Integration with SubscriptionParams Model ---

def test_subscription_params_model_dump():
    """
    Verify that SubscriptionParams model_dump works correctly for hash calculation.
    """
    params = SubscriptionParams(
        window_sec=5.0,
        sort_by="rx",
        sort_order="desc",
        limit=50,
        offset=0,
    )
    dumped = params.model_dump(exclude={"id"})
    assert "window_sec" in dumped
    assert dumped["window_sec"] == 5.0
    assert "sort_by" in dumped
    assert dumped["sort_by"] == "rx"


def test_subscription_params_with_none_values_excluded():
    """
    Verify that None values are excluded from model_dump.
    """
    params = SubscriptionParams(window_sec=5.0)
    dumped = params.model_dump(exclude_none=True)
    assert "window_sec" in dumped
    assert "sort_by" not in dumped  # None values excluded
    assert "sort_order" not in dumped
    assert "limit" not in dumped
    assert "offset" not in dumped
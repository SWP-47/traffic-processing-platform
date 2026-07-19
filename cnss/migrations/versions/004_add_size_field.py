# ==============================================================================
# Packet Size & Bytes-per-Second Metrics Migration
# Adds the 'size' column to packet_flows and recreates the telemetry_1s
# continuous aggregate to include bytes_in and bytes_out aggregations for
# bandwidth/throughput metrics calculation.
#
# IMPORTANT: This migration causes ~1-2 seconds of downtime when dropping
# the materialized view. Execute during a maintenance window or low-traffic period.
# ==============================================================================
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# --- Migration Identity ---
# Unique revision identifier and dependency chain
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ==============================================================================
# Upgrade: Add size column and recreate telemetry_1s view with byte aggregations
# ==============================================================================
def upgrade() -> None:
    """
    Applies the packet size feature:
    1. Adds 'size' column to packet_flows (BIGINT, in bytes)
    2. Drops the old telemetry_1s continuous aggregate
    3. Recreates telemetry_1s with bytes_in and bytes_out aggregations
    4. Re-establishes the continuous aggregate refresh policy
    """
    # --- Step 1: Add Size Column ---
    # BIGINT is sufficient for packet size metadata (max value ~4.3 exabytes)
    # NOT NULL with DEFAULT 0 ensures backward compatibility with older CNs
    op.add_column(
        "packet_flows",
        sa.Column(
            "size",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
            comment="Packet size in bytes",
        ),
    )

    # --- Step 2: Drop Old Materialized View ---
    # CRITICAL: This operation causes brief downtime (~1-2 seconds)
    # The view must be dropped before recreation with new byte aggregations
    op.execute("DROP MATERIALIZED VIEW IF EXISTS telemetry_1s")

    # --- Step 3: Recreate Materialized View with Byte Aggregations ---
    # The new view includes SUM(size) FILTER aggregations for both directions
    # to enable real-time bytes-per-second (BPS) calculations in the Reporting Worker.
    # Multiple rows may exist per second (one per active protocol).
    op.execute("""
        CREATE MATERIALIZED VIEW telemetry_1s
        WITH (timescaledb.continuous) AS
        SELECT
            channel_id,
            time_bucket('1 second', time) AS bucket,
            protocol,
            COUNT(*) FILTER (WHERE direction = 0) AS packets_in,
            COUNT(*) FILTER (WHERE direction = 1) AS packets_out,
            SUM(size) FILTER (WHERE direction = 0) AS bytes_in,
            SUM(size) FILTER (WHERE direction = 1) AS bytes_out
        FROM packet_flows
        GROUP BY channel_id, bucket, protocol
        """)

    # --- Step 4: Re-establish Continuous Aggregate Policy ---
    # Refresh policy runs every 1 second with a 1-second end offset
    # to ensure only closed buckets are queried (preventing partial data)
    op.execute("""
        SELECT add_continuous_aggregate_policy('telemetry_1s',
            start_offset => INTERVAL '5 seconds',
            end_offset => INTERVAL '1 second',
            schedule_interval => INTERVAL '1 second'
        )
        """)


# ==============================================================================
# Downgrade: Remove size column and restore original telemetry_1s view
# ==============================================================================
def downgrade() -> None:
    """
    Reverts the packet size feature:
    1. Drops the bytes-aware telemetry_1s view
    2. Recreates the original telemetry_1s view (without byte aggregations)
    3. Re-establishes the continuous aggregate policy
    4. Removes the 'size' column from packet_flows
    """
    # --- Step 1: Drop Bytes-Aware View ---
    op.execute("DROP MATERIALIZED VIEW IF EXISTS telemetry_1s")

    # --- Step 2: Recreate Original View (Without Bytes) ---
    # Restores the pre-size-field schema for rollback scenarios
    op.execute("""
        CREATE MATERIALIZED VIEW telemetry_1s
        WITH (timescaledb.continuous) AS
        SELECT
            channel_id,
            time_bucket('1 second', time) AS bucket,
            protocol,
            COUNT(*) FILTER (WHERE direction = 0) AS packets_in,
            COUNT(*) FILTER (WHERE direction = 1) AS packets_out
        FROM packet_flows
        GROUP BY channel_id, bucket, protocol
        """)

    # --- Step 3: Re-establish Continuous Aggregate Policy ---
    op.execute("""
        SELECT add_continuous_aggregate_policy('telemetry_1s',
            start_offset => INTERVAL '5 seconds',
            end_offset => INTERVAL '1 second',
            schedule_interval => INTERVAL '1 second'
        )
        """)

    # --- Step 4: Drop Size Column ---
    # Remove the size column from packet_flows table
    op.drop_column("packet_flows", "size")

# ==============================================================================
# Protocol Field Addition and Telemetry View Recreate Migration
# Adds the 'protocol' column to packet_flows and recreates the telemetry_1s
# continuous aggregate to group by protocol for protocol-level granularity.
# 
# IMPORTANT: This migration causes ~1-2 seconds of downtime when dropping
# the materialized view. Execute during a maintenance window or low-traffic period.
# ==============================================================================
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# --- Migration Identity ---
# Unique revision identifier and dependency chain
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ==============================================================================
# Upgrade: Add protocol column and recreate telemetry_1s view
# ==============================================================================
def upgrade() -> None:
    """
    Applies the protocol field feature:
    1. Adds 'protocol' column to packet_flows with backward-compatible default
    2. Drops the old telemetry_1s continuous aggregate
    3. Recreates telemetry_1s with protocol-level grouping
    4. Re-establishes the continuous aggregate refresh policy
    """
    # --- Step 1: Add Protocol Column ---
    # VARCHAR(20) provides sufficient space for protocol names (TCP, UDP, ICMP, etc.)
    # NOT NULL with DEFAULT 'UNKNOWN' ensures backward compatibility with older CNs
    op.add_column(
        "packet_flows",
        sa.Column(
            "protocol",
            sa.String(20),
            nullable=False,
            server_default="UNKNOWN",
            comment="Network protocol identifier (e.g., TCP, UDP, ICMP)",
        ),
    )

    # --- Step 2: Drop Old Materialized View ---
    # CRITICAL: This operation causes brief downtime (~1-2 seconds)
    # The view must be dropped before recreation with new GROUP BY clause
    op.execute("DROP MATERIALIZED VIEW IF EXISTS telemetry_1s")

    # --- Step 3: Recreate Materialized View with Protocol Grouping ---
    # The new view groups by (channel_id, bucket, protocol) to enable
    # protocol-level telemetry granularity. Multiple rows may exist per second
    # (one per active protocol), requiring COUNT(DISTINCT bucket) in handlers.
    op.execute(
        """
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
        """
    )

    # --- Step 4: Re-establish Continuous Aggregate Policy ---
    # Refresh policy runs every 1 second with a 1-second end offset
    # to ensure only closed buckets are queried (preventing partial data)
    op.execute(
        """
        SELECT add_continuous_aggregate_policy('telemetry_1s',
            start_offset => INTERVAL '5 seconds',
            end_offset => INTERVAL '1 second',
            schedule_interval => INTERVAL '1 second'
        )
        """
    )


# ==============================================================================
# Downgrade: Remove protocol column and restore original telemetry_1s view
# ==============================================================================
def downgrade() -> None:
    """
    Reverts the protocol field feature:
    1. Drops the protocol-aware telemetry_1s view
    2. Recreates the original telemetry_1s view (without protocol grouping)
    3. Re-establishes the continuous aggregate policy
    4. Removes the 'protocol' column from packet_flows
    """
    # --- Step 1: Drop Protocol-Aware View ---
    op.execute("DROP MATERIALIZED VIEW IF EXISTS telemetry_1s")

    # --- Step 2: Recreate Original View (Without Protocol) ---
    # Restores the pre-protocol schema for rollback scenarios
    op.execute(
        """
        CREATE MATERIALIZED VIEW telemetry_1s
        WITH (timescaledb.continuous) AS
        SELECT
            channel_id,
            time_bucket('1 second', time) AS bucket,
            COUNT(*) FILTER (WHERE direction = 0) AS packets_in,
            COUNT(*) FILTER (WHERE direction = 1) AS packets_out
        FROM packet_flows
        GROUP BY channel_id, bucket
        """
    )

    # --- Step 3: Re-establish Original Policy ---
    op.execute(
        """
        SELECT add_continuous_aggregate_policy('telemetry_1s',
            start_offset => INTERVAL '5 seconds',
            end_offset => INTERVAL '1 second',
            schedule_interval => INTERVAL '1 second'
        )
        """
    )

    # --- Step 4: Remove Protocol Column ---
    op.drop_column("packet_flows", "protocol")
# ==============================================================================
# TimescaleDB Setup and Continuous Aggregates Migration
# Initializes the high-performance time-series schema for packet telemetry.
# Creates the packet_flows hypertable, continuous aggregates for real-time
# metrics, and automated retention policies to manage storage lifecycle.
# ==============================================================================

from typing import Sequence, Union

from core.config import settings
from alembic import op

# --- Revision Identifiers ---
# Auto-generated identifiers used by Alembic to track migration history and order.
# '002' denotes the TimescaleDB specific schema extensions following the initial relational setup.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# --- Upgrade Operations ---
# Applies schema changes to transition the database to this revision.
# Uses raw SQL execution to leverage TimescaleDB-specific DDL and functions.
def upgrade() -> None:
    # Create the base packet_flows table matching the architecture specification.
    # Uses BIGSERIAL for IDs and TIMESTAMPTZ for time-series partitioning.
    op.execute("""
        CREATE TABLE packet_flows (
            id BIGSERIAL,
            time TIMESTAMPTZ NOT NULL,
            channel_id TEXT NOT NULL,
            direction SMALLINT NOT NULL,
            src_ip INET NOT NULL,
            dst_ip INET NOT NULL,
            src_port INTEGER NOT NULL,
            dst_port INTEGER NOT NULL,
            PRIMARY KEY (id, time)
        );
    """)

    # Convert the standard PostgreSQL table into a TimescaleDB hypertable.
    # Partitions the data automatically by the 'time' column for high-performance ingestion.
    op.execute("""
        SELECT create_hypertable('packet_flows', 'time', if_not_exists => TRUE);
    """)

    # Create a composite index to optimize channel-specific time-series queries.
    op.execute("""
        CREATE INDEX idx_packet_flows_channel_time ON packet_flows (channel_id, time DESC);
    """)

    # --- Continuous Aggregate Creation (AUTOCOMMIT Mode) ---
    # TimescaleDB continuous aggregates cannot be created inside a transaction block.
    # Since we disabled automatic transaction wrapping in env.py, these commands
    # will execute in AUTOCOMMIT mode by default.
    op.execute("""
        CREATE MATERIALIZED VIEW telemetry_1s
        WITH (timescaledb.continuous) AS
        SELECT 
            channel_id, 
            time_bucket('1 second', time) AS bucket,
            COUNT(*) FILTER (WHERE direction = 0) AS packets_in,
            COUNT(*) FILTER (WHERE direction = 1) AS packets_out
        FROM packet_flows 
        GROUP BY channel_id, bucket;
    """)

    # Add continuous aggregate policy for real-time refresh (every 1 second).
    op.execute("""
        SELECT add_continuous_aggregate_policy('telemetry_1s',
            start_offset => INTERVAL '5 seconds',
            end_offset => INTERVAL '1 second',
            schedule_interval => INTERVAL '1 second');
    """)

    # Add retention policy to automatically drop data older than the configured period.
    op.execute(f"""
        SELECT add_retention_policy('packet_flows', INTERVAL '{settings.retention_days} days', if_not_exists => TRUE);
    """)


# --- Downgrade Operations ---
# Reverts the schema changes to transition the database to the previous revision.
def downgrade() -> None:
    # Drop the retention policy
    op.execute("""
        SELECT remove_retention_policy('packet_flows', if_exists => TRUE);
    """)

    # Drop the continuous aggregate policy
    op.execute("""
        SELECT remove_continuous_aggregate_policy('telemetry_1s', if_exists => TRUE);
    """)

    # Drop the continuous aggregate materialized view
    op.execute("""
        DROP MATERIALIZED VIEW IF EXISTS telemetry_1s;
    """)

    # Drop the composite index
    op.execute("DROP INDEX IF EXISTS idx_packet_flows_channel_time;")

    # Drop the hypertable (which also drops the underlying table)
    op.execute("DROP TABLE IF EXISTS packet_flows;")
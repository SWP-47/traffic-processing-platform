-- ==============================================================================
-- CnSS TimescaleDB Hypertables Setup
-- Standalone SQL script for creating the packet_flows hypertable.
-- This script can be executed directly via psql for manual deployments
-- or environments where Alembic migrations are not used.
-- ==============================================================================

-- --- Hypertable Creation ---
-- Create the base packet_flows table matching the architecture specification (§3.1).
-- Uses BIGSERIAL for auto-incrementing IDs and TIMESTAMPTZ for time-series partitioning.
CREATE TABLE IF NOT EXISTS packet_flows (
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

-- --- Hypertable Conversion ---
-- Convert the standard PostgreSQL table into a TimescaleDB hypertable.
-- Partitions the data automatically by the 'time' column for high-performance ingestion.
-- The IF NOT EXISTS check ensures idempotency if the script is run multiple times.
SELECT create_hypertable('packet_flows', 'time', if_not_exists => TRUE);

-- --- Composite Index ---
-- Create a composite index to optimize channel-specific time-series queries.
-- Sorting by time DESC ensures the most recent packets are fetched instantly.
-- This index is critical for the Reporting Worker's SQL query performance.
CREATE INDEX IF NOT EXISTS idx_channel_time 
ON packet_flows (channel_id, time DESC);
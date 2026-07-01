-- ==============================================================================
-- CnSS TimescaleDB Retention Policies Setup
-- Standalone SQL script for configuring automated data retention policies.
-- This script can be executed directly via psql for manual deployments
-- or environments where Alembic migrations are not used.
-- ==============================================================================

-- --- Retention Policy for packet_flows ---
-- Automatically drops data older than 7 days to prevent unbounded storage growth.
-- This policy runs in the background and ensures the hypertable maintains
-- optimal query performance by removing stale time-series data.
-- Note: This SQL file uses the default 7-day retention period.
-- For custom retention periods, use the Alembic migration which reads from settings.
SELECT add_retention_policy('packet_flows', INTERVAL '7 days', if_not_exists => TRUE);
-- ==============================================================================
-- CnSS TimescaleDB Continuous Aggregates Setup
-- Standalone SQL script for creating continuous aggregates that pre-compute
-- telemetry metrics for real-time reporting. These aggregates prevent heavy
-- GROUP BY queries on the raw packet_flows hypertable.
-- ==============================================================================

-- --- Drop Existing Aggregate (Idempotency) ---
-- Remove the continuous aggregate if it already exists to allow re-running this script.
-- This is necessary because CREATE MATERIALIZED VIEW does not support IF NOT EXISTS
-- for continuous aggregates in TimescaleDB.
DROP MATERIALIZED VIEW IF EXISTS telemetry_1s;

-- --- Create 1-Second Continuous Aggregate ---
-- Pre-calculates packet counts (IN/OUT) per channel in 1-second time buckets.
-- The Reporting Worker queries this view instead of the raw packet_flows table
-- to achieve sub-millisecond response times for real-time telemetry updates.
CREATE MATERIALIZED VIEW telemetry_1s
WITH (timescaledb.continuous) AS
SELECT 
    channel_id, 
    time_bucket('1 second', time) AS bucket,
    COUNT(*) FILTER (WHERE direction = 0) AS packets_in,
    COUNT(*) FILTER (WHERE direction = 1) AS packets_out
FROM packet_flows 
GROUP BY channel_id, bucket;

-- --- Add Refresh Policy ---
-- Configures automatic refresh of the continuous aggregate every 1 second.
-- The policy aggregates data from 5 seconds ago to 1 second ago, ensuring
-- that late-arriving packets are included while maintaining near-real-time updates.
-- start_offset: How far back to look (5 seconds allows for network latency)
-- end_offset: How recent to include (1 second ago to avoid incomplete buckets)
-- schedule_interval: Refresh frequency (1 second for real-time telemetry)
SELECT add_continuous_aggregate_policy('telemetry_1s', 
    start_offset => INTERVAL '5 seconds', 
    end_offset => INTERVAL '1 second', 
    schedule_interval => INTERVAL '1 second');
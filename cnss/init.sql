-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Raw packet metadata hypertable
CREATE TABLE packet_flows (
    id         BIGSERIAL,
    time       TIMESTAMPTZ NOT NULL,
    channel_id TEXT        NOT NULL,
    direction  SMALLINT    NOT NULL,   -- 0 = IN, 1 = OUT
    src_ip     INET        NOT NULL,
    dst_ip     INET        NOT NULL,
    src_port   INTEGER     NOT NULL,
    dst_port   INTEGER     NOT NULL,
    PRIMARY KEY (id, time)
);

SELECT create_hypertable('packet_flows', 'time');

CREATE INDEX idx_channel_time ON packet_flows (channel_id, time DESC);

-- Auto-drop chunks older than 7 days
SELECT add_retention_policy('packet_flows', INTERVAL '7 days');
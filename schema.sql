CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE TABLE IF NOT EXISTS file_events (
    id BIGSERIAL,
    event_time TIMESTAMPTZ NOT NULL,
    operation VARCHAR(50) NOT NULL,
    filename VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(200),
    storage_url TEXT,
    uploader_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
SELECT create_hypertable(
    'file_events',
    'event_time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);
CREATE INDEX IF NOT EXISTS idx_file_events_operation ON file_events (operation, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_file_events_uploader ON file_events (uploader_id, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_file_events_filename ON file_events (filename, event_time DESC);
CREATE MATERIALIZED VIEW IF NOT EXISTS file_events_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', event_time) AS bucket,
    operation,
    COUNT(*) AS num_events,
    SUM(file_size) AS total_size,
    AVG(file_size) AS avg_size,
    MAX(file_size) AS max_size,
    MIN(file_size) AS min_size
FROM file_events
GROUP BY bucket, operation
WITH NO DATA;
SELECT add_continuous_aggregate_policy('file_events_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

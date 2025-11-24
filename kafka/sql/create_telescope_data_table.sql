-- Migration to add telescope data raw table for Kafka Connect sink
-- This table receives data from the telescope.data Kafka topic via Kafka Connect

CREATE TABLE IF NOT EXISTS telescope_data_raw (
    -- Primary identification
    data_id VARCHAR(255) PRIMARY KEY,
    observation_id VARCHAR(255) NOT NULL,
    sequence_number INTEGER NOT NULL,
    timestamp BIGINT NOT NULL,
    
    data BYTEA,
    
    -- Processing metadata
    processed BOOLEAN DEFAULT FALSE,
    processing_pipeline_version VARCHAR(50),
    
    -- Kafka sink metadata
    sink_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Standard timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX idx_telescope_data_observation_id ON telescope_data_raw(observation_id);
CREATE INDEX idx_telescope_data_timestamp ON telescope_data_raw(timestamp);
CREATE INDEX idx_telescope_data_processed ON telescope_data_raw(processed);

-- Comments
COMMENT ON TABLE telescope_data_raw IS 'Raw telescope observation data ingested from Kafka';
COMMENT ON COLUMN telescope_data_raw.data_id IS 'Unique identifier for this data record';
COMMENT ON COLUMN telescope_data_raw.observation_id IS 'ID of the observation this data belongs to';
COMMENT ON COLUMN telescope_data_raw.sequence_number IS 'Sequence number within the observation';
COMMENT ON COLUMN telescope_data_raw.timestamp IS 'Unix timestamp in milliseconds when data was captured';
COMMENT ON COLUMN telescope_data_raw.sink_timestamp IS 'Timestamp when data was written by Kafka Connect';

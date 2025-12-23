-- Create measurements_v2 table for CabinPython v2
-- This table uses a normalized structure with JSON for flexible sensor data

USE cabinpi;

-- Create the new measurements table with normalized structure
CREATE TABLE IF NOT EXISTS measurements_v2 (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME(6) NOT NULL,
    sensor_id VARCHAR(100) NOT NULL,
    measurements JSON NOT NULL,
    error TEXT,
    synced BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes for common queries
    INDEX idx_timestamp (timestamp),
    INDEX idx_sensor_id (sensor_id),
    INDEX idx_synced (synced),
    INDEX idx_sensor_timestamp (sensor_id, timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Sensor measurements (v2 normalized format)';

-- Display table info
DESCRIBE measurements_v2;
SELECT 'measurements_v2 table created successfully!' as status;

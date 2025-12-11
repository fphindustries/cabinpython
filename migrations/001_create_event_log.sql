-- Create event_log table for CabinPython v2
-- This table stores system events, alerts, and state changes

CREATE TABLE IF NOT EXISTS event_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    sensor_id VARCHAR(100),
    message TEXT,
    data JSON,
    notified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_timestamp (timestamp),
    INDEX idx_event_type (event_type),
    INDEX idx_severity (severity),
    INDEX idx_sensor_id (sensor_id),
    INDEX idx_notified (notified)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='System events and alerts';

-- Add synced column to measurements table if it doesn't exist
-- This tracks which measurements have been synced to remote API
ALTER TABLE measurements
ADD COLUMN IF NOT EXISTS synced BOOLEAN DEFAULT FALSE,
ADD INDEX IF NOT EXISTS idx_synced (synced);

-- Display table info
DESCRIBE event_log;
SELECT COUNT(*) as row_count FROM measurements;

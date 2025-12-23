# MariaDB Integration - Setup Complete

## Summary

CabinPython v2 is now successfully integrated with MariaDB for persistent storage of sensor measurements and system events.

## Database Structure

### Database: `cabinpi`
- **User**: `cabinpi`
- **Password**: Stored in `.env` file as `DB_PASSWORD`
- **Host**: localhost
- **Character Set**: utf8mb4

### Tables Created

#### 1. `measurements_v2` - Sensor Readings
Wide table with dedicated columns for each sensor type, optimized for React dashboard queries.

**Schema**: 78 columns organized by sensor type
- **Indoor Environmental**: `indoor_temp_c`, `indoor_temp_f`, `indoor_humidity`
- **Solar Controller**: `solar_battery_voltage`, `solar_pv_voltage`, `solar_power_watts`, `solar_kwh`, etc.
- **Battery Monitor**: `battery_voltage_v`, `battery_current_ma`, `battery_power_w`, `battery_temp_c`
- **Solar Panel Monitor**: `solar_panel_voltage_v`, `solar_panel_current_ma`, `solar_panel_power_w`
- **Outdoor Weather**: `outdoor_temp_c`, `outdoor_humidity`, `outdoor_wind_avg`, `outdoor_uv`, etc.
- **Inverter**: `inverter_on`, `inverter_vac_out`, `inverter_aac_out`, `inverter_vdc`
- **Temperature Sensors**: `outdoor_sensor_temp_c`, `outdoor_sensor_temp_f`, `outdoor_sensor_device_id`
- **System**: `synced`, `created_at`

**Example Query Results**:
```
Timestamp                  In°C    In°F    Humid%  BatV    BatmA    BatW    BatT°C
2025-12-23 08:35:30.473830 21.17   70.10   40.73   0.016   -0.31    0.000   21.14
2025-12-23 08:35:20.473702 21.16   70.09   40.67   0.056   -0.31    0.000   21.12
```

#### 2. `event_log` - System Events
Stores daemon events, sensor failures, and alerts.

**Schema**:
```sql
CREATE TABLE event_log (
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
);
```

**Example Data**:
```
[2025-12-21 15:24:03] INFO - daemon_started
  CabinPython v2 daemon started successfully

[2025-12-21 15:24:03] ERROR - sensor_init_failed [ds18b20_outdoor]
  Sensor 'ds18b20_outdoor' initialization failed
```

#### 3. `measurements` - Legacy v1 Table
Preserved from the original CabinPython v1 system. Contains historical data in wide table format.

## Configuration

### Environment Variables (`.env`)
```bash
DB_PASSWORD=BeardLice!
```

### Daemon Configuration (`config.yaml`)
```yaml
plugins:
  outputs:
    database:
      enabled: true
      type: measurement_storage
      module: cabinpi.plugins.outputs.mariadb_storage
      config:
        host: localhost
        database: cabinpi
        username: cabinpi
        password: ${DB_PASSWORD}
        table: measurements_v2

    event_log:
      enabled: true
      type: event_log
      module: cabinpi.plugins.outputs.mariadb_events
      config:
        host: localhost
        database: cabinpi
        username: cabinpi
        password: ${DB_PASSWORD}
```

## Testing Results

✅ **Database Connection**: Successfully connected from Python
✅ **Table Creation**: All tables created with proper indexes (78 columns in measurements_v2)
✅ **Measurement Storage**: SHT45 and INA228 data writing to dedicated columns every 10s
✅ **Event Logging**: System events captured (daemon start, sensor failures)
✅ **Wide Table Format**: React dashboard can query specific columns efficiently
✅ **Column Mapping**: Automatic mapping from sensor readings to database columns

### Sample Queries for React Dashboard

**Get latest temperature readings:**
```sql
SELECT
    timestamp,
    indoor_temp_c,
    indoor_temp_f,
    indoor_humidity,
    outdoor_sensor_temp_c,
    outdoor_temp_c
FROM measurements_v2
WHERE timestamp > NOW() - INTERVAL 24 HOUR
ORDER BY timestamp DESC
LIMIT 100;
```

**Get battery monitor time-series:**
```sql
SELECT
    timestamp,
    battery_voltage_v,
    battery_current_ma,
    battery_power_w,
    battery_temp_c
FROM measurements_v2
WHERE battery_voltage_v IS NOT NULL
  AND timestamp > NOW() - INTERVAL 7 DAY
ORDER BY timestamp;
```

**Get hourly averages for dashboard:**
```sql
SELECT
    DATE_FORMAT(timestamp, '%Y-%m-%d %H:00:00') as hour,
    AVG(indoor_temp_c) as avg_indoor_temp,
    AVG(indoor_humidity) as avg_humidity,
    AVG(battery_voltage_v) as avg_battery_voltage,
    AVG(battery_current_ma) as avg_battery_current,
    AVG(solar_power_watts) as avg_solar_power,
    AVG(outdoor_temp_c) as avg_outdoor_temp
FROM measurements_v2
WHERE timestamp > NOW() - INTERVAL 7 DAY
GROUP BY hour
ORDER BY hour;
```

**Get solar panel daily statistics:**
```sql
SELECT
    DATE(timestamp) as date,
    MAX(solar_power_watts) as peak_power,
    AVG(solar_power_watts) as avg_power,
    SUM(solar_kwh) as total_kwh,
    MAX(solar_pv_voltage) as max_voltage
FROM measurements_v2
WHERE solar_power_watts IS NOT NULL
  AND timestamp > NOW() - INTERVAL 30 DAY
GROUP BY date
ORDER BY date;
```

**Get all events from last 24 hours:**
```sql
SELECT timestamp, event_type, severity, message
FROM event_log
WHERE timestamp > NOW() - INTERVAL 24 HOUR
ORDER BY timestamp DESC;
```

**Get min/max values for dashboard gauges:**
```sql
SELECT
    MIN(battery_voltage_v) as min_battery_v,
    MAX(battery_voltage_v) as max_battery_v,
    MIN(indoor_temp_c) as min_indoor_temp,
    MAX(indoor_temp_c) as max_indoor_temp,
    MAX(solar_power_watts) as max_solar_power
FROM measurements_v2
WHERE timestamp > NOW() - INTERVAL 24 HOUR;
```

## Migration Scripts

All migration scripts are in the `migrations/` directory:

1. **000_setup_database.sql** - Creates database, user, and legacy measurements table
2. **001_create_event_log.sql** - Creates event_log table and adds synced column to legacy table
3. **002_create_measurements_v2.sql** - Creates normalized JSON-based measurements_v2 table (deprecated)
4. **003_recreate_measurements_v2_wide.sql** - Recreates measurements_v2 as wide table with 78 columns (current)

## Plugin Implementation

### MariaDB Storage Plugin
**File**: `cabinpi/plugins/outputs/mariadb_storage.py`
- Writes SensorReading objects to `measurements_v2` wide table
- Maps sensor readings to appropriate columns using `COLUMN_MAPPING` dictionary
- Supports multiple sensor types (SHT45, INA228, DS18B20, Solar, Inverter, Weather)
- Auto-reconnects on connection loss
- Dynamic INSERT statements based on available sensor data
- Logs all database operations

### MariaDB Events Plugin
**File**: `cabinpi/plugins/outputs/mariadb_events.py`
- Writes Event objects to `event_log` table
- Auto-creates table if missing
- Tracks notification status
- Stores event data as JSON

## Python Dependencies

```bash
pip install mysql-connector-python
```

Or using system packages:
```bash
apt install python3-mysql.connector
```

## Maintenance

### Backup Database
```bash
mysqldump -u cabinpi -p cabinpi > cabinpi_backup_$(date +%Y%m%d).sql
```

### Check Table Sizes
```sql
SELECT
    table_name,
    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS "Size (MB)",
    table_rows
FROM information_schema.TABLES
WHERE table_schema = 'cabinpi'
ORDER BY (data_length + index_length) DESC;
```

### Cleanup Old Data
```sql
-- Delete measurements older than 90 days
DELETE FROM measurements_v2
WHERE timestamp < NOW() - INTERVAL 90 DAY;

-- Delete old events (keep errors/warnings)
DELETE FROM event_log
WHERE timestamp < NOW() - INTERVAL 30 DAY
AND severity = 'info';
```

## Next Steps

1. ✅ Database setup complete
2. ✅ Tables created
3. ✅ Sensors writing to database
4. ✅ Events being logged
5. 🔲 Set up automated backups
6. 🔲 Create data visualization dashboard
7. 🔲 Implement data retention policies
8. 🔲 Add database monitoring

## Status

**✅ COMPLETE - MariaDB integration fully functional**

Last Updated: 2025-12-21

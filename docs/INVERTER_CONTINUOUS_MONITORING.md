# Inverter Continuous Monitoring

## Overview

The inverter sensor has been updated to use **continuous monitoring** instead of polling. This provides better data quality through aggregation and real-time event detection for mode changes and faults.

## Key Features

### 1. Continuous Reading with Aggregation
- Polls inverter every 2 seconds (configurable)
- Maintains sliding window of samples (default: 30 samples)
- Reports aggregated values every 60 seconds (configurable)
- All voltage, current, and temperature readings include min/max/avg

### 2. Real-Time Event Detection
- **Mode Changes**: Generates INFO events when inverter changes operating mode
  - Standby (0)
  - Invert (1)
  - Charge (2)
  - Sell (3)

- **Fault Detection**: Generates ERROR events when faults occur
  - Automatic notification (notify=True)
  - Tracks fault code
  - Generates INFO event when fault clears

### 3. Comprehensive Measurements

#### State Values (Current)
- `InverterOn` - Inverter LED status
- `ChargerOn` - Charger LED status
- `InverterMode` - Operating mode (0-3)
- `InverterModeName` - Mode name (Standby/Invert/Charge/Sell)
- `InverterFault` - Fault code (0=no fault)

#### Voltage Readings (Aggregated)
- **DC Voltage (VDC)**
  - `Invertervdc` - Average battery voltage
  - `vdc_min` - Minimum voltage in window
  - `vdc_max` - Maximum voltage in window

- **AC Output Voltage (VACout)**
  - `InverterVACOut` - Average output voltage
  - `VACout_min` - Minimum output voltage
  - `VACout_max` - Maximum output voltage

- **AC Input Voltage (VACin)**
  - `VACin` - Average input voltage
  - `VACin_min` - Minimum input voltage
  - `VACin_max` - Maximum input voltage

#### Current Readings (Aggregated)
- **AC Output Current (AACout)**
  - `InverterAACOut` - Average output current
  - `AACout_min` - Minimum output current
  - `AACout_max` - Maximum output current

- **AC Input Current (AACin)**
  - `AACin` - Average input current
  - `AACin_min` - Minimum input current
  - `AACin_max` - Maximum input current

#### Temperature Readings (Aggregated)
- **Battery Temperature**
  - `battery_temp_c` - Average battery temperature (°C)
  - `battery_temp_min` - Minimum battery temperature
  - `battery_temp_max` - Maximum battery temperature

- **Transformer Temperature**
  - `transformer_temp_c` - Average transformer temperature (°C)
  - `transformer_temp_min` - Minimum transformer temperature
  - `transformer_temp_max` - Maximum transformer temperature

- **FET Temperature**
  - `fet_temp_c` - Average FET temperature (°C)
  - `fet_temp_min` - Minimum FET temperature
  - `fet_temp_max` - Maximum FET temperature

## Configuration

### Basic Configuration
```yaml
plugins:
  sensors:
    inverter:
      enabled: true
      module: cabinpi.plugins.sensors.inverter
      type: continuous  # Changed from 'polling'
      config:
        port: /dev/ttyUSB1
        timeout: 3
        poll_interval: 2        # Read from inverter every 2 seconds
        aggregate_interval: 60  # Report aggregated values every 60 seconds
        window_size: 30         # Keep 30 samples for aggregation
```

### Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `port` | `/dev/ttyUSB1` | Serial port for RS232 connection |
| `timeout` | `3` | Serial read timeout (seconds) |
| `poll_interval` | `2.0` | Seconds between inverter polls |
| `aggregate_interval` | `60.0` | Seconds between aggregated reports |
| `window_size` | `30` | Number of samples to aggregate |

### Tuning Guidelines

**For More Responsive Data:**
- Decrease `poll_interval` to 1-2 seconds
- Decrease `aggregate_interval` to 30 seconds
- Decrease `window_size` to 15-20 samples

**For Lower System Load:**
- Increase `poll_interval` to 5-10 seconds
- Increase `aggregate_interval` to 120 seconds
- Keep `window_size` proportional (poll_interval × window_size ≈ 60 seconds)

## Database Schema

### New Columns Added (measurements_v2)

The migration added 22 new columns for inverter aggregates:

```sql
-- State columns
charger_on TINYINT(1)
inverter_mode_name VARCHAR(20)

-- Voltage aggregates (6 columns)
inverter_vdc_min DECIMAL(5,2)
inverter_vdc_max DECIMAL(5,2)
inverter_vac_out_min DECIMAL(5,2)
inverter_vac_out_max DECIMAL(5,2)
inverter_vac_in DECIMAL(5,2)
inverter_vac_in_min DECIMAL(5,2)
inverter_vac_in_max DECIMAL(5,2)

-- Current aggregates (6 columns)
inverter_aac_out_min DECIMAL(6,2)
inverter_aac_out_max DECIMAL(6,2)
inverter_aac_in DECIMAL(6,2)
inverter_aac_in_min DECIMAL(6,2)
inverter_aac_in_max DECIMAL(6,2)

-- Temperature aggregates (9 columns)
inverter_battery_temp_c_min DECIMAL(5,2)
inverter_battery_temp_c_max DECIMAL(5,2)
inverter_transformer_temp_c DECIMAL(5,2)
inverter_transformer_temp_c_min DECIMAL(5,2)
inverter_transformer_temp_c_max DECIMAL(5,2)
inverter_fet_temp_c DECIMAL(5,2)
inverter_fet_temp_c_min DECIMAL(5,2)
inverter_fet_temp_c_max DECIMAL(5,2)
```

**Total**: measurements_v2 now has **100 columns** (was 78)

## Event Types

### inverter_mode_change
- **Severity**: `info`
- **Trigger**: Inverter operating mode changes
- **Data**:
  - `old_mode`: Previous mode number (0-3)
  - `new_mode`: New mode number (0-3)
  - `old_mode_name`: Previous mode name
  - `new_mode_name`: New mode name
- **Example**: "Inverter mode changed: Standby → Invert"

### inverter_fault
- **Severity**: `error`
- **Trigger**: Fault code becomes non-zero
- **Notify**: `true` (sends notifications)
- **Data**:
  - `fault_code`: Numeric fault code from inverter
- **Example**: "Inverter fault detected: code 5"

### inverter_fault_cleared
- **Severity**: `info`
- **Trigger**: Fault code returns to zero
- **Data**:
  - `previous_fault_code`: The fault code that was cleared
- **Example**: "Inverter fault cleared"

## React Dashboard Queries

### Get Current Inverter Status
```sql
SELECT
    timestamp,
    InverterModeName,
    InverterFault,
    Invertervdc,
    InverterVACOut,
    InverterAACOut
FROM measurements_v2
WHERE Invertervdc IS NOT NULL
ORDER BY timestamp DESC
LIMIT 1;
```

### Get Voltage Trends with Min/Max
```sql
SELECT
    timestamp,
    Invertervdc as avg_vdc,
    vdc_min,
    vdc_max,
    InverterVACOut as avg_vac_out,
    VACout_min,
    VACout_max
FROM measurements_v2
WHERE timestamp > NOW() - INTERVAL 24 HOUR
  AND Invertervdc IS NOT NULL
ORDER BY timestamp;
```

### Get Temperature Monitoring
```sql
SELECT
    timestamp,
    battery_temp_c,
    battery_temp_min,
    battery_temp_max,
    transformer_temp_c,
    transformer_temp_max,
    fet_temp_c,
    fet_temp_max
FROM measurements_v2
WHERE battery_temp_c IS NOT NULL
  AND timestamp > NOW() - INTERVAL 24 HOUR
ORDER BY timestamp;
```

### Get Mode Change History
```sql
SELECT
    timestamp,
    event_type,
    message,
    data
FROM event_log
WHERE event_type = 'inverter_mode_change'
  AND timestamp > NOW() - INTERVAL 7 DAY
ORDER BY timestamp DESC;
```

### Get Fault History
```sql
SELECT
    timestamp,
    event_type,
    severity,
    message,
    JSON_EXTRACT(data, '$.fault_code') as fault_code
FROM event_log
WHERE event_type IN ('inverter_fault', 'inverter_fault_cleared')
  AND timestamp > NOW() - INTERVAL 30 DAY
ORDER BY timestamp DESC;
```

## Benefits Over Polling

### 1. Better Data Quality
- **Polling**: Single sample every 5 minutes - can miss spikes/dips
- **Continuous**: 30 samples aggregated - captures min/max/avg accurately

### 2. Real-Time Event Detection
- **Polling**: Mode changes only detected when polled (could be 5 minutes late)
- **Continuous**: Mode changes detected within 2 seconds

### 3. Fault Response Time
- **Polling**: Fault detection delayed up to polling interval
- **Continuous**: Immediate fault detection with automatic notification

### 4. Historical Data
- Tracking min/max values allows detection of:
  - Voltage sags during high loads
  - Current spikes during motor starts
  - Temperature rise patterns
  - Power quality issues

## Migration

### Required Steps
1. Run database migration: `004_add_inverter_aggregates.sql`
2. Update `config.yaml`:
   - Change `type: polling` to `type: continuous`
   - Add `poll_interval`, `aggregate_interval`, `window_size` if desired
3. Restart daemon

### Backward Compatibility
- Column names unchanged for basic fields (VACout, AACout, vdc)
- React dashboard queries for existing fields work without changes
- New min/max fields are optional enhancements

## Performance Considerations

### CPU Usage
- Continuous monitoring adds minimal CPU overhead
- Async I/O ensures non-blocking operation
- Aggregation calculations are O(n) where n=window_size

### Memory Usage
- Each aggregator stores window_size float values
- 8 aggregators × 30 samples × 8 bytes = ~2KB per sensor
- Negligible memory footprint

### Serial Port
- Reading every 2 seconds is well within RS232 capabilities
- pymagnum library handles communication efficiently
- Timeout ensures no hanging on communication errors

## Troubleshooting

### "No data available yet (monitoring starting up)"
- Normal during first `aggregate_interval` seconds after startup
- Wait for first aggregation cycle to complete

### Event callback warnings
- Ensure sensor manager sets event callback during initialization
- Check daemon logs for callback registration

### Missing min/max values in database
- Verify migration ran successfully (100 columns in measurements_v2)
- Check that column mapping in mariadb_storage.py includes aggregates
- Review daemon logs for INSERT statement errors

### Mode change events not appearing
- Verify event_log output is enabled in configuration
- Check that mode is actually changing (use test queries)
- Review event detector logs

## Status

✅ **COMPLETE** - Inverter sensor updated to continuous monitoring
- Continuous reading loop implemented
- Value aggregation (min/max/avg) working
- Event generation for mode changes and faults
- Database schema updated (100 columns)
- Column mapping updated in mariadb_storage.py
- Migration script created and tested

Last Updated: 2025-12-23

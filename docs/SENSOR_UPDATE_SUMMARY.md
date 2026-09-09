# Sensor Update Summary

## Overview
This document provides a complete summary of the sensor system updates for the Cabin monitoring system.

## Changes Made

### 1. New Sensors Added

#### SHT45 Temperature & Humidity Sensor (Replaces SHT31)
- **Interface**: I2C (address 0x44 or 0x45)
- **Measurements**: Indoor temperature (°C/°F) and relative humidity (%)
- **Accuracy**: ±0.1°C, ±1.0% RH
- **Features**: CRC-8 checksum validation, high precision mode

#### INA228 DC Power Monitor (New)
- **Interface**: I2C (address 0x40)
- **Purpose**: Monitor cabin DC power system
- **Library**: Adafruit CircuitPython INA228 (v2.0.3)
- **Measurements**:
  - Bus voltage (V)
  - Current (A)
  - Power (W)
  - Shunt voltage (mV)
- **Shunt Resistor**: 15mΩ (0.015Ω) - handled by Adafruit library

#### DS18B20 Temperature Sensor (New)
- **Interface**: 1-Wire bus
- **Purpose**: Measure basement temperature
- **Measurements**: Temperature in °C and °F
- **Accuracy**: ±0.5°C

### 2. Updated Files

#### Python Scripts Created
- **[sht45_driver.py](sht45_driver.py)**: Driver module for SHT45 sensor
- **[ina228_driver.py](ina228_driver.py)**: Wrapper for Adafruit INA228 library
- **[ds18b20_driver.py](ds18b20_driver.py)**: Driver module for DS18B20 temperature sensor
- **[test_sht45.py](test_sht45.py)**: Test script for SHT45 sensor
- **[test_ina228.py](test_ina228.py)**: Test script for INA228 power monitor (updated to use Adafruit library)
- **[test_ds18b20.py](test_ds18b20.py)**: Test script for DS18B20 sensor (existing)

#### Python Scripts Modified
- **[capture_measurements.py](capture_measurements.py)**: Updated to read from all three new sensors
- **[sync_common.py](sync_common.py)**: Updated API format conversion to include new sensor fields

## Installation & Deployment Checklist

### Step 1: Database Migration
Follow the instructions in **[DATABASE_MIGRATION.md](DATABASE_MIGRATION.md)**

```bash
# Backup database
mysqldump -u cabinpi -p cabinpi > cabinpi_backup_$(date +%Y%m%d_%H%M%S).sql

# Run migration SQL
mysql -u cabinpi -p cabinpi < migration_script.sql
```

**Required columns to add:**
- `dc_bus_voltage`, `dc_current`, `dc_power`, `dc_shunt_voltage`
- `basement_c`, `basement_f`

### Step 2: Hardware Setup

#### SHT45 Sensor
- Connect SDA to GPIO2 (pin 3)
- Connect SCL to GPIO3 (pin 5)
- Connect VDD to 3.3V
- Connect GND to GND
- Enable I2C: `sudo raspi-config` → Interface Options → I2C → Enable

#### INA228 Power Monitor
- Connect to same I2C bus as SHT45
- Default address: 0x40
- Connect shunt resistor in series with DC power line
- Verify with: `i2cdetect -y 1`

#### DS18B20 Temperature Sensor
- Connect data pin to GPIO4 (default)
- Connect VDD to 3.3V or 5V
- Connect GND to GND
- Add 4.7kΩ pull-up resistor between data and VDD
- Enable 1-wire: Add to `/boot/config.txt`: `dtoverlay=w1-gpio`
- Load modules: `sudo modprobe w1-gpio && sudo modprobe w1-therm`

### Step 3: Test Sensors

```bash
# Test SHT45
./test_sht45.py

# Test INA228
./test_ina228.py

# Test DS18B20
./test_ds18b20.py
```

### Step 4: Update Cloudflare API
Follow the instructions in **[API_SCHEMA_UPDATE.md](API_SCHEMA_UPDATE.md)**

Update your Cloudflare Worker to accept the new fields:
- `intC`, `intF`, `humidity` (SHT45)
- `dcBusVoltage`, `dcCurrent`, `dcPower`, `dcShuntVoltage` (INA228)
- `basementC`, `basementF` (DS18B20)

### Step 5: Deploy Updated Scripts

```bash
# Stop the measurement service if running
sudo systemctl stop cabin-measurements.timer
sudo systemctl stop cabin-measurements.service

# Test the updated capture script manually
cd /opt/cabinpython
./capture_measurements.py --verbose

# If successful, restart the service
sudo systemctl start cabin-measurements.timer
```

### Step 6: Monitor & Verify

```bash
# Watch logs for errors
journalctl -u cabin-measurements.service -f

# Check database for new data
mysql -u cabinpi -p -e "SELECT Date, int_f, humidity, dc_power, basement_f FROM cabinpi.measurements ORDER BY Date DESC LIMIT 5;"

# Verify API sync
tail -f /var/log/cabin-measurements.log | grep -i sync
```

## Data Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   SHT45     │────▶│             │     │             │
│  (Indoor)   │     │             │     │             │
└─────────────┘     │             │     │             │
                    │             │     │             │
┌─────────────┐     │  capture_   │     │   MariaDB   │
│   INA228    │────▶│ measurements│────▶│   Database  │
│  (Power)    │     │     .py     │     │             │
└─────────────┘     │             │     └──────┬──────┘
                    │             │            │
┌─────────────┐     │             │            │
│  DS18B20    │────▶│             │            │
│ (Basement)  │     │             │            │
└─────────────┘     └─────────────┘            │
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │ sync_common │
                                        │     .py     │
                                        └──────┬──────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │ Cloudflare  │
                                        │     API     │
                                        └─────────────┘
```

## New Database Fields

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| dc_bus_voltage | DECIMAL(10,6) | INA228 | DC system voltage (V) |
| dc_current | DECIMAL(10,6) | INA228 | DC current draw (A) |
| dc_power | DECIMAL(10,6) | INA228 | DC power consumption (W) |
| dc_shunt_voltage | DECIMAL(10,6) | INA228 | Shunt voltage drop (mV) |
| basement_c | DECIMAL(5,2) | DS18B20 | Basement temperature (°C) |
| basement_f | DECIMAL(5,2) | DS18B20 | Basement temperature (°F) |

**Note**: Indoor sensor fields (`int_c`, `int_f`, `humidity`) remain the same, now populated by SHT45 instead of SHT31.

## API Field Mapping

| Database Column | API Field (camelCase) |
|----------------|----------------------|
| int_c | intC |
| int_f | intF |
| humidity | humidity |
| dc_bus_voltage | dcBusVoltage |
| dc_current | dcCurrent |
| dc_power | dcPower |
| dc_shunt_voltage | dcShuntVoltage |
| basement_c | basementC |
| basement_f | basementF |

## Configuration

No changes to [config.ini](config.ini) are required for the new sensors. They use auto-detection:
- SHT45: Auto-detected on I2C bus
- INA228: Fixed address 0x40 on I2C bus
- DS18B20: Auto-detected on 1-wire bus

## Troubleshooting

### SHT45 Not Detected
```bash
# Check I2C bus
i2cdetect -y 1

# Should show device at 0x44 or 0x45
# If not, check wiring and I2C enabled
```

### INA228 Not Responding
```bash
# Verify device on I2C bus
i2cdetect -y 1

# Check if address conflicts with SHT45
# INA228 should be at 0x40
```

### DS18B20 Not Found
```bash
# Check 1-wire devices
ls /sys/bus/w1/devices/

# Should see 28-xxxxxxxxxxxx
# If not, check 1-wire enabled and wiring

# Load modules manually
sudo modprobe w1-gpio
sudo modprobe w1-therm
```

### Database Insert Errors
```bash
# Check if columns exist
mysql -u cabinpi -p -e "DESCRIBE cabinpi.measurements" | grep -E "dc_|basement_"

# If missing, run the migration from DATABASE_MIGRATION.md
```

### API Sync Failures
```bash
# Test API manually
curl -X POST https://cabinpi.com/api/sensors/ingest \
  -H "CF-Access-Client-Id: <your-id>" \
  -H "CF-Access-Client-Secret: <your-secret>" \
  -H "Content-Type: application/json" \
  -d '{"records":[{"date":"2025-12-26T10:00:00Z","dcPower":50}]}'

# Check logs for detailed error messages
tail -f /var/log/cabin-measurements.log
```

## Performance Impact

- **Additional I2C reads**: ~30ms per measurement cycle (SHT45 + INA228)
- **Additional 1-wire read**: ~750ms for DS18B20 with retries
- **Database size increase**: ~48 bytes per record
- **API payload increase**: ~150 bytes per record

Total measurement cycle time should remain under 2 seconds.

## Rollback Instructions

If you need to revert to the old system:

1. Restore database backup
2. Revert code changes: `git checkout <previous-commit>`
3. Reinstall SHT31 library: `pip install adafruit-circuitpython-sht31d`
4. Restart service: `sudo systemctl restart cabin-measurements.service`

## Support & Maintenance

- Test scripts available for each sensor
- All new fields are optional (backward compatible)
- Comprehensive error logging and exception handling
- Automatic retry logic for sensor read failures

## Next Steps

After successful deployment:

1. Monitor system for 24 hours
2. Verify data accuracy against known values
3. Set up alerts for abnormal readings
4. Document any sensor-specific calibration needs
5. Create visualization dashboards for new metrics

## Related Documentation

- [DATABASE_MIGRATION.md](DATABASE_MIGRATION.md) - Complete database migration guide
- [API_SCHEMA_UPDATE.md](API_SCHEMA_UPDATE.md) - Cloudflare API update instructions
- [test_sht45.py](test_sht45.py) - SHT45 test and usage examples
- [test_ina228.py](test_ina228.py) - INA228 test and usage examples
- [test_ds18b20.py](test_ds18b20.py) - DS18B20 test and usage examples

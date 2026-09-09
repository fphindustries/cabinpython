# Quick Start Guide: Sensor Update Deployment

## Prerequisites
- [ ] SHT45 sensor physically installed and connected to I2C
- [ ] INA228 power monitor installed on DC power line
- [ ] DS18B20 sensor installed in basement
- [ ] Required Python libraries installed (adafruit-circuitpython-ina228)
- [ ] Database backup completed
- [ ] Cloudflare Worker API updated (see API_SCHEMA_UPDATE.md)

**Check library installation:**
```bash
cd /opt/cabinpython
source env/bin/activate
pip list | grep ina228
# Should show: adafruit-circuitpython-ina228  2.0.3 (or similar)
```

## 5-Minute Deployment

### Step 1: Backup Database (30 seconds)
```bash
cd /opt/cabinpython
mysqldump -u cabinpi -p cabinpi > cabinpi_backup_$(date +%Y%m%d_%H%M%S).sql
```

### Step 2: Update Database Schema (30 seconds)
```bash
mysql -u cabinpi -p cabinpi < migration_add_sensors.sql
```
**Password**: `BeardLice!` (from config.ini)

### Step 3: Test Individual Sensors (2 minutes)

Test SHT45:
```bash
./test_sht45.py
# Expected: Temperature and humidity readings
# Press Ctrl+C after verifying it works
```

Test INA228:
```bash
./test_ina228.py
# Expected: Voltage, current, and power readings
# Press Ctrl+C after verifying it works
```

Test DS18B20:
```bash
./test_ds18b20.py
# Expected: Temperature readings
# Press Ctrl+C after verifying it works
```

### Step 4: Test Complete System (1 minute)
```bash
./capture_measurements.py --verbose
```

**Expected output:**
```
Starting measurement capture at 2025-12-26 10:30:00
Reading SHT45 sensor...
Reading INA228 power monitor...
Reading DS18B20 basement temperature...
Reading solar charge controller...
Reading weather data...
Reading inverter data...
Battery: 13.20V, Solar: 245W, Indoor: 70.7F/45%, Outdoor: 42.3F
Successfully inserted measurement record for 2025-12-26 10:30:00
Measurement capture completed
```

### Step 5: Verify Database (30 seconds)
```bash
mysql -u cabinpi -p cabinpi -e "
SELECT Date, int_f, humidity, dc_power, dc_current, basement_f
FROM measurements
ORDER BY Date DESC
LIMIT 1;"
```

**Expected**: Most recent record showing all new sensor values (not NULL).

### Step 6: Deploy to Production (30 seconds)
```bash
# If using systemd service:
sudo systemctl restart cabin-measurements.service
sudo systemctl status cabin-measurements.service

# Watch it run:
journalctl -u cabin-measurements.service -f
```

## Verification Checklist

After deployment, verify:

- [ ] Database has new columns (dc_bus_voltage, dc_current, dc_power, dc_shunt_voltage, basement_c, basement_f)
- [ ] SHT45 is reading indoor temperature and humidity
- [ ] INA228 is reading DC power system metrics
- [ ] DS18B20 is reading basement temperature
- [ ] Data is being inserted into database
- [ ] Data is syncing to Cloudflare API (check logs)
- [ ] No errors in system logs

## Quick Troubleshooting

### "No SHT45 sensor found"
```bash
i2cdetect -y 1
# Should show device at 0x44 or 0x45
# If not: sudo raspi-config → Interface → I2C → Enable → Reboot
```

### "No DS18B20 sensor found"
```bash
ls /sys/bus/w1/devices/28-*
# If empty, enable 1-wire:
echo "dtoverlay=w1-gpio" | sudo tee -a /boot/config.txt
sudo reboot
```

### "INA228 not responding"
```bash
i2cdetect -y 1
# Should show device at 0x40
# Check wiring and power connections
```

### Database errors
```bash
# Verify columns exist
mysql -u cabinpi -p cabinpi -e "DESCRIBE measurements" | grep dc_
# If missing, re-run migration script
```

### API sync failures
Check logs:
```bash
tail -50 /var/log/cabin-measurements.log | grep -i error
# Verify Cloudflare Worker has been updated with new fields
```

## Rollback (if needed)

```bash
# Stop service
sudo systemctl stop cabin-measurements.service

# Restore database
mysql -u cabinpi -p cabinpi < cabinpi_backup_YYYYMMDD_HHMMSS.sql

# Remove new code (if needed)
git checkout HEAD~1 capture_measurements.py sync_common.py

# Restart
sudo systemctl start cabin-measurements.service
```

## Success Criteria

The deployment is successful when:
1. All three test scripts run without errors
2. capture_measurements.py completes without errors
3. Database shows new sensor values (not NULL)
4. Logs show successful API sync
5. No errors in systemd service logs for 1 hour

## Next Steps After Deployment

1. Monitor for 24 hours
2. Check data accuracy
3. Set up dashboards for new metrics
4. Configure alerts for abnormal values
5. Update any monitoring/graphing tools

## Getting Help

- Review detailed docs: [SENSOR_UPDATE_SUMMARY.md](SENSOR_UPDATE_SUMMARY.md)
- Database details: [DATABASE_MIGRATION.md](DATABASE_MIGRATION.md)
- API details: [API_SCHEMA_UPDATE.md](API_SCHEMA_UPDATE.md)
- Check sensor test scripts for working examples

## File Reference

- `sht45_driver.py` - SHT45 sensor driver
- `ina228_driver.py` - INA228 power monitor driver
- `ds18b20_driver.py` - DS18B20 temperature sensor driver
- `capture_measurements.py` - Main data collection script (MODIFIED)
- `sync_common.py` - API sync helper (MODIFIED)
- `migration_add_sensors.sql` - Database migration script

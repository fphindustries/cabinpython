# CabinPi Monitoring System

A comprehensive off-grid cabin monitoring system running on Raspberry Pi. This system collects environmental, power system, and weather data from multiple sensors and synchronizes it to a remote API protected by Cloudflare Access.

## Overview

The CabinPi system monitors:
- **Solar Power System**: Charge controller metrics (battery voltage, PV voltage, charging current, power output, charge states)
- **Inverter**: Operating status, mode, AC output voltage/current
- **Indoor Environment**: Temperature and humidity via SHT31 sensor
- **Outdoor Weather**: Temperature, humidity, barometric pressure, wind, UV, solar radiation, rainfall, lightning strikes via WeatherFlow API
- **Photos**: Automated daylight photo capture

All data is stored locally in MariaDB and synchronized to a remote Cloudflare-protected API when internet connectivity is available.

## System Architecture

```
Sensors → capture_measurements.py → Local MariaDB → sync_to_cloudflare.py → Cloudflare D1
                                          ↓
                                   Email Alerts
```

The system is designed to be resilient to unreliable internet connections:
- All measurements are always saved to local database first
- Remote synchronization is best-effort and non-blocking
- Failed syncs don't prevent new measurements
- Unsynced records accumulate locally and sync when connection is restored

## Scripts

### capture_measurements.py

Main data collection script that runs every 5 minutes (typically via cron).

**Functions:**
- Collects data from all sensors (SHT31, solar controller, weather API, inverter)
- Writes measurements to local MariaDB database
- Sends low battery email alerts based on configurable thresholds
- Attempts to sync all unsynced records to remote API
- Stops syncing on first failure (will retry in 5 minutes)

**Usage:**
```bash
# Normal operation
./capture_measurements.py

# With custom config file
./capture_measurements.py --config /path/to/config.ini

# Enable verbose debug logging
./capture_measurements.py --verbose
```

**Cron setup (runs every 5 minutes):**
```cron
*/5 * * * * /opt/cabinpython/capture_measurements.py >> /var/log/cabinpi.log 2>&1
```

### sync_to_cloudflare.py

Dedicated synchronization script for syncing all unsynced records directly into Cloudflare D1.

**Functions:**
- Fetches all records where `synced = 0` from the database
- Sends records to remote API in configurable batches
- Marks successfully synced records with `synced = 1`
- Processes batches until all unsynced records are sent
- Useful for catching up on large backlogs after extended outages

**Usage:**
```bash
# Sync all unsynced records (default: 10 per batch)
./sync_to_cloudflare.py

# Custom batch size
./sync_to_cloudflare.py --batch-size 50

# Test mode (only 1 record, marks as synced)
./sync_to_cloudflare.py --test

# Custom config file
./sync_to_cloudflare.py --config /path/to/config.ini
```

### capture_image.py

Captures photos during daylight hours only.

**Functions:**
- Calculates sunrise/sunset times based on configured location
- Captures timestamped JPG images using Pi Camera 2
- Only operates when the sun is up

**Usage:**
```bash
# Capture image (if it's daytime)
./capture_image.py

# With custom config file
./capture_image.py --config /path/to/config.ini
```

**Cron setup (runs every 15 minutes):**
```cron
*/15 * * * * /opt/cabinpython/capture_image.py >> /var/log/cabinpi-photos.log 2>&1
```

### sync_common.py

Shared library module containing common functions used by both `capture_measurements.py` and `sync_to_cloudflare.py`:
- `get_unsynced_measurements()` - Fetches unsynced records from database
- `mark_as_synced()` - Marks records as synced
- `convert_measurement_to_d1_row()` - Converts DB records to Cloudflare D1 row format
- `insert_measurements_to_d1()` - Inserts measurements directly into Cloudflare D1
- `sync_unsynced_records()` - High-level sync function

## Configuration

All configuration is stored in `config.ini`:

```ini
[Database]
database=cabinpi
username=cabinpi
password=YourPasswordHere

[Solar]
# Solar charge controller serial port
port=/dev/serial/by-id/usb-FTDI_USB_Serial_Converter_FTDY7VMG-if00-port0

[Inverter]
# Inverter serial port
port=/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_B0027QYY-if00-port0

[Location]
# For sunrise/sunset calculations
latitude=00.000000
longitude=-000.000000

[Images]
# Directory for captured photos
directory=/opt/images/

[Weather]
# WeatherFlow API credentials
token=your-weatherflow-token
device=your-device-id

[Notify]
# Email alert configuration
method = email
smtp_server = smtp.gmail.com
smtp_port = 465
smtp_user = your-email@gmail.com
smtp_pass = your-app-password
from_addr = your-email@gmail.com
to_addr = recipient1@example.com,recipient2@example.com

# Battery alert thresholds (volts)
battery_low_threshold = 12.0
battery_recovery_threshold = 12.8
# Cooldown period in minutes (prevents alert spam)
alert_cooldown_minutes = 1440

[CloudflareD1]
# Cloudflare API token scoped with D1:Edit permission
account_id=your-cf-account-id
database_id=your-d1-database-uuid
api_token=your-cf-api-token
```

## Database Setup

### Create Database and User

```sql
CREATE DATABASE cabinpi;
CREATE USER 'cabinpi'@'localhost' IDENTIFIED BY 'YourPasswordHere';
GRANT ALL PRIVILEGES ON cabinpi.* TO 'cabinpi'@'localhost';
FLUSH PRIVILEGES;
```

### Add Sync Column

The `measurements` table requires a `synced` column to track synchronization state:

```sql
USE cabinpi;
ALTER TABLE measurements ADD COLUMN synced TINYINT DEFAULT 0;

-- Optional: Create index for better performance
CREATE INDEX idx_synced ON measurements(synced, Date);
```

## Installation

### Prerequisites

```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install python3 python3-venv mariadb-server

# Create virtual environment
cd /opt/cabinpython
python3 -m venv env
source env/bin/activate

# Install Python packages
pip install mysql-connector-python
pip install adafruit-circuitpython-sht31d
pip install minimalmodbus
pip install requests
pip install python-dateutil
pip install suntime
pip install picamera2
pip install magnum  # For Magnum inverter communication
```

### File Permissions

```bash
# Make scripts executable
chmod +x /opt/cabinpython/capture_measurements.py
chmod +x /opt/cabinpython/sync_to_cloudflare.py
chmod +x /opt/cabinpython/capture_image.py

# Ensure proper ownership
chown -R ckent:cabinpi /opt/cabinpython
```

## Hardware Requirements

- **Raspberry Pi** (tested on Pi 4)
- **SHT31 Temperature/Humidity Sensor** (I2C)
- **Classic Solar Charge Controller** (RS485/Modbus)
- **Magnum Inverter** (RS232/Serial)
- **WeatherFlow Weather Station** (API access)
- **Pi Camera Module** (optional, for photos)

### Serial Port Configuration

The system uses two USB-to-serial adapters:
- Solar controller: `/dev/serial/by-id/usb-FTDI_USB_Serial_Converter_FTDY7VMG-if00-port0`
- Inverter: `/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_B0027QYY-if00-port0`

Using `/dev/serial/by-id/` paths ensures devices don't swap if USB ports change.

## Cloudflare D1 Integration

The system writes measurement rows directly into a Cloudflare D1 database using
[D1's HTTP query API](https://developers.cloudflare.com/api/resources/d1/subresources/database/methods/query/) —
there is no intermediate Worker or REST API in between.

Records are inserted as a batch (one `INSERT` statement per record, executed
atomically by D1) into the `measurements` table, whose columns match the
camelCase field names produced by `convert_measurement_to_d1_row()` in
`sync_common.py`.

### Authentication

Requests are authenticated with a Cloudflare API token (`Authorization: Bearer <token>`)
scoped to `D1:Edit` on the target account, configured via the `[CloudflareD1]`
section of `config.ini`.

## Monitoring and Logging

### Log Files

Recommended log file locations:
- `/var/log/cabinpi.log` - Main measurement capture logs
- `/var/log/cabinpi-sync.log` - Synchronization logs
- `/var/log/cabinpi-photos.log` - Photo capture logs

### Log Rotation

Create `/etc/logrotate.d/cabinpi`:
```
/var/log/cabinpi*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
}
```

### Key Metrics Logged

The system logs important metrics on each run:
```
2025-12-06 10:30:00 INFO Battery: 13.20V, Solar: 250W, Indoor: 68.5F/45%, Outdoor: 55.3F
2025-12-06 10:30:00 INFO Synced 5 records to remote API
```

## Troubleshooting

### No data being collected

1. Check sensor connections and serial ports
2. Run with verbose logging: `./capture_measurements.py --verbose`
3. Check system logs: `journalctl -xe`
4. Verify database connectivity: `mysql -u cabinpi -p cabinpi`

### Sync failing

1. Test D1 connectivity: `./sync_to_cloudflare.py --test`
2. Verify the `[CloudflareD1]` credentials in config.ini (account_id, database_id, api_token)
3. Check network connectivity: `ping api.cloudflare.com`
4. Review sync logs for error details

### Database errors

1. Verify `synced` column exists: `DESCRIBE measurements;`
2. Check database permissions
3. Ensure MariaDB service is running: `systemctl status mariadb`

### Serial port errors

1. Check USB connections
2. Verify serial ports exist: `ls -l /dev/serial/by-id/`
3. Ensure user has dialout permissions: `sudo usermod -a -G dialout $USER`

## Battery Alert System

The system monitors battery voltage and sends email alerts:

- **Low Battery Alert**: Triggered when voltage drops below threshold
- **Recovery Alert**: Sent when voltage recovers above recovery threshold
- **Cooldown Period**: Prevents alert spam (configurable, default 1440 minutes)
- **Hysteresis**: Different thresholds for alerting vs. recovery prevent flapping

Alert state is persisted in `/opt/cabinpython/last_battery_alert.json`.

## Development

### Running Tests

```bash
# Test database sync with 1 record
./sync_to_cloudflare.py --test

# Test with verbose logging
./capture_measurements.py --verbose

# Test photo capture
./capture_image.py
```

### Adding New Sensors

1. Create a new `get_<sensor>_data()` function in `capture_measurements.py`
2. Add sensor data to the `all_data` dictionary merge
3. Update the local database schema to include new columns
4. Add the new column to the Cloudflare D1 `measurements` table
5. Update `convert_measurement_to_d1_row()` and `D1_MEASUREMENT_COLUMNS` in `sync_common.py`

## License

ISC License

## Support

For issues and questions, refer to the project repository or contact the cabin administrators.

## Version History

- **1.0.0** - Initial release with sync functionality and battery alerts
- **0.9.0** - Basic sensor data collection and local storage

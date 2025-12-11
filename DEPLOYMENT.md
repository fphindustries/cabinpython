# CabinPython v2 - Deployment Guide

Complete guide for deploying CabinPython v2 daemon to production.

## Prerequisites

### Hardware

- **Raspberry Pi 5** running Raspbian/Raspberry Pi OS
- **I2C devices**: SHT31 temperature/humidity sensor (address 0x44)
- **Serial devices**:
  - Solar charge controller (Modbus RTU, `/dev/ttyUSB0`)
  - Magnum inverter (RS232, `/dev/ttyUSB1`)
- **Network access** for WeatherFlow API and Cloudflare sync

### Software

- Python 3.9 or higher
- MariaDB/MySQL 10.5+
- systemd (included in Raspbian)
- Git

### Accounts

- WeatherFlow API token and device ID
- Cloudflare Access credentials (client ID and secret)
- SMTP account for email notifications (e.g., Gmail)

## Installation Steps

### 1. Clone Repository

```bash
cd ~
git clone https://github.com/fphindustries/cabinpython.git
cd cabinpython
git checkout feature/issue-2-directory-structure  # or main/master when merged
```

### 2. Install System Dependencies

```bash
sudo apt-get update
sudo apt-get install -y \
    python3-venv \
    python3-dev \
    mariadb-server \
    libmariadb-dev \
    i2c-tools \
    python3-smbus
```

### 3. Setup Database

```bash
# Start MariaDB
sudo systemctl start mariadb
sudo systemctl enable mariadb

# Secure installation
sudo mysql_secure_installation

# Create database and user
sudo mysql -e "CREATE DATABASE IF NOT EXISTS cabinpi;"
sudo mysql -e "CREATE USER IF NOT EXISTS 'cabinpi'@'localhost' IDENTIFIED BY 'your_password_here';"
sudo mysql -e "GRANT ALL PRIVILEGES ON cabinpi.* TO 'cabinpi'@'localhost';"
sudo mysql -e "FLUSH PRIVILEGES;"
```

### 4. Import Existing Schema

If migrating from v1:

```bash
# Backup existing database first!
mysqldump -u cabinpi -p cabinpi > cabinpi_backup_$(date +%Y%m%d).sql

# Your existing measurements table should already exist
# Just run the migration to add event_log and synced column
cd migrations
./migrate.sh
```

If starting fresh:

```bash
# Create measurements table (use your existing schema)
# Then run migration
cd migrations
./migrate.sh
```

### 5. Configure Hardware Access

```bash
# Enable I2C
sudo raspi-config nonint do_i2c 0

# Add user to hardware groups
sudo usermod -a -G dialout,i2c,gpio $USER

# Reboot to apply group changes
sudo reboot
```

After reboot, verify:

```bash
# Check I2C
ls -l /dev/i2c-1
i2cdetect -y 1

# Check serial devices
ls -l /dev/ttyUSB*
```

### 6. Run Installation Script

```bash
cd ~/cabinpython
sudo ./install.sh
```

This will:
- Copy files to `/opt/cabinpython`
- Create Python virtual environment
- Install dependencies
- Create default config files
- Install systemd service
- Set permissions

### 7. Configure Daemon

Edit configuration:

```bash
sudo nano /opt/cabinpython/config.yaml
```

Key settings to adjust:
- Sensor ports (`/dev/ttyUSB0`, etc.)
- Polling intervals
- Event detection thresholds
- Enable/disable specific sensors and outputs

Edit secrets:

```bash
sudo nano /opt/cabinpython/.env
```

Required variables:
```bash
# Database
DB_PASSWORD=your_mariadb_password

# WeatherFlow API
WEATHER_DEVICE=your_device_id
WEATHER_TOKEN=your_api_token

# Cloudflare (optional)
CF_API_URL=https://your-api.com/endpoint
CF_CLIENT_ID=your_client_id
CF_CLIENT_SECRET=your_client_secret

# Email notifications
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
ALERT_EMAIL_1=recipient1@example.com
ALERT_EMAIL_2=recipient2@example.com
```

### 8. Test Configuration

Test the daemon before enabling as a service:

```bash
cd /opt/cabinpython
source env/bin/activate
python daemon.py --config config.yaml --log-level DEBUG
```

Watch for:
- Successful sensor initialization
- Database connection
- No errors in first reading cycle

Press Ctrl+C to stop.

### 9. Enable and Start Service

```bash
# Enable service to start on boot
sudo systemctl enable cabinpi-daemon

# Start service
sudo systemctl start cabinpi-daemon

# Check status
sudo systemctl status cabinpi-daemon
```

### 10. Monitor Logs

```bash
# Follow live logs
journalctl -u cabinpi-daemon -f

# Check for errors
journalctl -u cabinpi-daemon -p err -n 50
```

## Post-Deployment Verification

### Check Sensor Readings

```bash
# View recent sensor data
mysql -u cabinpi -p cabinpi -e "SELECT Date, int_f, humidity, dispavgVbatt, watts FROM measurements ORDER BY Date DESC LIMIT 5;"
```

### Check Events

```bash
# View recent events
mysql -u cabinpi -p cabinpi -e "SELECT timestamp, event_type, severity, message FROM event_log ORDER BY timestamp DESC LIMIT 10;"
```

### Verify Watchdog

The watchdog ensures the daemon is responsive:

```bash
# Check watchdog pings in logs
journalctl -u cabinpi-daemon | grep -i watchdog
```

### Test Configuration Reload

Make a change to `config.yaml`, then:

```bash
sudo systemctl reload cabinpi-daemon
journalctl -u cabinpi-daemon -n 20
```

Should see "Configuration reloaded successfully" in logs.

### Test Email Alerts

Trigger a test alert by manually editing an event threshold in config.yaml to trigger easily, then reload.

## Migration from v1 (Cron-based)

### Before Migration

1. **Backup everything**:
   ```bash
   mysqldump -u cabinpi -p cabinpi > cabinpi_backup_$(date +%Y%m%d).sql
   tar -czf cabinpython_v1_backup.tar.gz ~/cabinpython_v1
   ```

2. **Document current cron schedule**:
   ```bash
   crontab -l > cron_backup.txt
   ```

3. **Test v2 in parallel** (optional):
   - Run v2 with database pointing to a test database
   - Verify readings match v1

### Migration Day

1. **Stop v1 cron jobs**:
   ```bash
   crontab -e
   # Comment out all cabinpython lines with #
   ```

2. **Verify cron stopped**:
   ```bash
   crontab -l
   # Wait 5 minutes and check no new measurements
   ```

3. **Start v2 daemon**:
   ```bash
   sudo systemctl start cabinpi-daemon
   sudo systemctl enable cabinpi-daemon
   ```

4. **Monitor for 1 hour**:
   ```bash
   journalctl -u cabinpi-daemon -f
   # Watch for successful readings
   # Check database for new rows
   ```

5. **Monitor for 24 hours**:
   - Check logs periodically
   - Verify email alerts work
   - Check Cloudflare sync (if enabled)
   - Monitor system resource usage

### Rollback Procedure

If issues occur:

1. **Stop v2**:
   ```bash
   sudo systemctl stop cabinpi-daemon
   sudo systemctl disable cabinpi-daemon
   ```

2. **Restore v1 cron**:
   ```bash
   crontab -e
   # Uncomment cabinpython lines
   ```

3. **Verify v1 working**:
   ```bash
   # Wait 5 minutes for next cron run
   # Check database for new measurements
   ```

4. **Document issues** for troubleshooting v2

## Troubleshooting

### Service Won't Start

```bash
# Check service status
sudo systemctl status cabinpi-daemon

# View detailed logs
journalctl -u cabinpi-daemon -n 100 --no-pager

# Test manually
cd /opt/cabinpython
source env/bin/activate
python daemon.py --config config.yaml
```

### Sensor Not Found

```bash
# Check device exists
ls -l /dev/ttyUSB*
ls -l /dev/i2c-*

# Check permissions
groups $USER  # Should include dialout, i2c, gpio

# Check I2C device
i2cdetect -y 1  # Should show 0x44 for SHT31

# Check serial device
sudo minicom -D /dev/ttyUSB0  # Test serial communication
```

### Database Connection Failed

```bash
# Test database connection
mysql -u cabinpi -p cabinpi -e "SELECT 1;"

# Check password in .env
cat /opt/cabinpython/.env | grep DB_PASSWORD

# Verify user privileges
mysql -u root -p -e "SHOW GRANTS FOR 'cabinpi'@'localhost';"
```

### Email Alerts Not Sending

```bash
# Check SMTP configuration in .env
cat /opt/cabinpython/.env | grep SMTP

# Test SMTP manually
python3 << 'EOF'
import smtplib
server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
server.login('your_email@gmail.com', 'your_app_password')
print("SMTP login successful!")
server.quit()
EOF
```

### High CPU/Memory Usage

```bash
# Check resource usage
systemctl status cabinpi-daemon

# Adjust limits in service file
sudo nano /etc/systemd/system/cabinpi-daemon.service
# Increase MemoryMax or CPUQuota

# Reload systemd
sudo systemctl daemon-reload
sudo systemctl restart cabinpi-daemon
```

### Circuit Breaker Tripping

If sensors keep failing:

```bash
# Check logs for specific sensor errors
journalctl -u cabinpi-daemon | grep "circuit breaker"

# Adjust circuit breaker settings in config.yaml
# Increase failure_threshold or recovery_timeout

# Reload configuration
sudo systemctl reload cabinpi-daemon
```

## Monitoring and Maintenance

### Daily Checks

```bash
# Check service status
sudo systemctl status cabinpi-daemon

# Check for errors
journalctl -u cabinpi-daemon -p err --since today

# Verify recent measurements
mysql -u cabinpi -p cabinpi -e "SELECT COUNT(*) FROM measurements WHERE Date > NOW() - INTERVAL 1 DAY;"
```

### Weekly Tasks

- Review event log for anomalies
- Check disk space usage
- Verify remote sync working (if enabled)
- Review alert emails received

### Monthly Tasks

- Update system packages
- Check for daemon updates
- Review and rotate logs
- Database optimization

### Automated Monitoring

Consider setting up:

- **Cron health check**: Script to verify daemon is running and recording data
- **Grafana dashboard**: Visualize sensor data and system health
- **Uptime monitoring**: External service to check API endpoint
- **Log aggregation**: Centralized logging with alerts

## Performance Tuning

### Polling Intervals

Default is 300 seconds (5 minutes). Adjust per sensor:

```yaml
plugins:
  sensors:
    sht31:
      interval: 60  # Read every minute

    weather:
      interval: 600  # Read every 10 minutes
```

### Resource Limits

Current defaults:
- Memory: 256MB
- CPU: 50% of one core

Adjust in `/etc/systemd/system/cabinpi-daemon.service`:

```ini
MemoryMax=512M
CPUQuota=75%
```

### Database Optimization

```sql
-- Add indexes if needed
CREATE INDEX idx_date ON measurements(Date);

-- Optimize tables monthly
OPTIMIZE TABLE measurements;
OPTIMIZE TABLE event_log;
```

## Security Considerations

### File Permissions

```bash
# Verify restrictive permissions
ls -l /opt/cabinpython/.env  # Should be 600
ls -l /opt/cabinpython/config.yaml  # Should be 644

# Fix if needed
sudo chmod 600 /opt/cabinpython/.env
sudo chmod 644 /opt/cabinpython/config.yaml
```

### Database Access

- Use strong password for database user
- Restrict database user to localhost only
- Regularly backup database

### API Credentials

- Use environment variables for secrets (never commit to git)
- Rotate API tokens periodically
- Use app-specific passwords for Gmail SMTP

### System Updates

```bash
# Keep system updated
sudo apt-get update
sudo apt-get upgrade -y

# Update Python packages
cd /opt/cabinpython
source env/bin/activate
pip install --upgrade -r requirements.txt
```

## Backup and Disaster Recovery

### Automated Backups

Create `/opt/cabinpython/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/home/$USER/cabinpi_backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Backup database
mysqldump -u cabinpi -p$(grep DB_PASSWORD /opt/cabinpython/.env | cut -d= -f2) cabinpi \
  | gzip > "$BACKUP_DIR/cabinpi_db_$DATE.sql.gz"

# Backup configuration
tar -czf "$BACKUP_DIR/cabinpi_config_$DATE.tar.gz" \
  /opt/cabinpython/config.yaml \
  /opt/cabinpython/.env

# Keep only last 30 days
find "$BACKUP_DIR" -name "*.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR"
```

Schedule via cron:

```bash
# Daily at 2 AM
0 2 * * * /opt/cabinpython/backup.sh
```

### Restore Procedure

```bash
# Restore database
gunzip < backup_file.sql.gz | mysql -u cabinpi -p cabinpi

# Restore configuration
sudo tar -xzf backup_config.tar.gz -C /

# Restart daemon
sudo systemctl restart cabinpi-daemon
```

## Support and Updates

### Getting Help

1. Check logs: `journalctl -u cabinpi-daemon -n 200`
2. Review this documentation
3. Check GitHub issues: https://github.com/fphindustries/cabinpython/issues

### Updating to New Version

```bash
# Stop daemon
sudo systemctl stop cabinpi-daemon

# Backup current installation
sudo tar -czf /tmp/cabinpython_backup.tar.gz /opt/cabinpython

# Pull updates
cd ~/cabinpython
git pull

# Run installation
sudo ./install.sh

# Restart daemon
sudo systemctl start cabinpi-daemon

# Monitor logs
journalctl -u cabinpi-daemon -f
```

## Success Criteria

Deployment is successful when:

- ✅ Service starts automatically on boot
- ✅ All sensors reporting data every 5 minutes
- ✅ New measurements appearing in database
- ✅ Event log capturing state changes
- ✅ Email alerts working for critical events
- ✅ Cloudflare sync working (if enabled)
- ✅ Watchdog keeping daemon responsive
- ✅ Configuration reload working (SIGHUP)
- ✅ No errors in logs for 24 hours
- ✅ System resource usage acceptable (<50% CPU, <256MB RAM)

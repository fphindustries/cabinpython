# CabinPython v2 - systemd Integration Guide

This guide covers the systemd integration for CabinPython v2 daemon.

## Features

- **Type=notify**: Daemon signals readiness to systemd
- **Watchdog**: Automatic restart if daemon hangs (120s timeout)
- **SIGHUP Reload**: Reload configuration without restart
- **Resource Limits**: Memory and CPU constraints
- **Security Hardening**: Minimal privileges, private /tmp
- **Hardware Access**: Automatic access to I2C, serial, GPIO
- **Logging**: Integrated with systemd journal

## Installation

### Quick Install

```bash
sudo ./install.sh
```

This script will:
1. Copy files to `/opt/cabinpython`
2. Create Python virtual environment
3. Install dependencies
4. Install systemd service
5. Set permissions

### Manual Install

```bash
# Create installation directory
sudo mkdir -p /opt/cabinpython

# Copy files
sudo cp -r cabinpi daemon.py requirements.txt config.yaml.example .env.example /opt/cabinpython/

# Create virtual environment
cd /opt/cabinpython
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt

# Create configuration
cp config.yaml.example config.yaml
cp .env.example .env
# Edit config.yaml and .env with your settings

# Set ownership
sudo chown -R ckent:ckent /opt/cabinpython

# Add user to hardware groups
sudo usermod -a -G dialout,i2c,gpio ckent

# Install systemd service
sudo cp systemd/cabinpi-daemon.service /etc/systemd/system/
sudo systemctl daemon-reload
```

## Configuration

### Edit Configuration Files

```bash
# Main configuration
sudo nano /opt/cabinpython/config.yaml

# Secrets (passwords, API keys)
sudo nano /opt/cabinpython/.env
```

### Important Settings

**config.yaml**:
- Enable/disable sensors and outputs
- Sensor polling intervals
- Event detection rules
- Circuit breaker thresholds

**.env**:
- `DB_PASSWORD` - MariaDB password
- `WEATHER_TOKEN` - WeatherFlow API token
- `CF_CLIENT_ID`, `CF_CLIENT_SECRET` - Cloudflare Access credentials
- `SMTP_USER`, `SMTP_PASS` - Email notification credentials
- `ALERT_EMAIL` - Email recipient for alerts

## Service Management

### Enable and Start

```bash
# Enable service to start on boot
sudo systemctl enable cabinpi-daemon

# Start service now
sudo systemctl start cabinpi-daemon

# Check status
sudo systemctl status cabinpi-daemon
```

### View Logs

```bash
# Follow live logs
journalctl -u cabinpi-daemon -f

# View recent logs
journalctl -u cabinpi-daemon -n 100

# View logs since boot
journalctl -u cabinpi-daemon -b

# View logs for specific time
journalctl -u cabinpi-daemon --since "2025-01-01 00:00:00"
```

### Reload Configuration

Reload configuration without restarting (sensors continue running):

```bash
sudo systemctl reload cabinpi-daemon
```

This sends SIGHUP signal, which:
1. Reloads config.yaml and .env
2. Shuts down current sensors/outputs gracefully
3. Reinitializes with new configuration
4. Resumes sensor polling

### Restart Service

Full restart (brief downtime):

```bash
sudo systemctl restart cabinpi-daemon
```

### Stop Service

```bash
sudo systemctl stop cabinpi-daemon
```

### Disable Service

```bash
sudo systemctl disable cabinpi-daemon
```

## Monitoring

### Check Service Status

```bash
systemctl status cabinpi-daemon
```

Output shows:
- Active/inactive state
- Memory usage
- Recent log entries
- Process ID

### Check Health

The daemon exposes health status internally. To check:

```bash
# View active alerts in logs
journalctl -u cabinpi-daemon -n 100 | grep "active_alerts"

# Check for errors
journalctl -u cabinpi-daemon -p err -n 50
```

### Watchdog Status

The watchdog ensures the daemon is responsive. If the daemon hangs for >120 seconds:
- systemd automatically restarts it
- Event logged in journal

Check watchdog activity:

```bash
journalctl -u cabinpi-daemon | grep -i watchdog
```

## Troubleshooting

### Service Won't Start

```bash
# Check service status
sudo systemctl status cabinpi-daemon

# View full logs
journalctl -u cabinpi-daemon -n 200

# Check configuration syntax
/opt/cabinpython/env/bin/python /opt/cabinpython/daemon.py --config /opt/cabinpython/config.yaml
```

### Permission Errors

```bash
# Verify user is in required groups
groups ckent

# Should see: dialout i2c gpio

# If missing, add and reboot
sudo usermod -a -G dialout,i2c,gpio ckent
sudo reboot
```

### Sensor Connection Issues

```bash
# Check I2C devices
ls -l /dev/i2c-*

# Check serial devices
ls -l /dev/ttyUSB*

# Verify permissions
sudo chmod 666 /dev/i2c-1  # if needed
```

### Database Connection

```bash
# Test database connection
mysql -u cabinpi -p cabinpi

# Check if tables exist
mysql -u cabinpi -p cabinpi -e "SHOW TABLES;"
```

### Memory Issues

If daemon uses too much memory:

```bash
# Check current memory usage
systemctl status cabinpi-daemon

# Adjust limit in service file
sudo nano /etc/systemd/system/cabinpi-daemon.service
# Change: MemoryMax=256M

# Reload systemd
sudo systemctl daemon-reload
sudo systemctl restart cabinpi-daemon
```

## Advanced Configuration

### Custom Service Location

To install in a different location:

1. Edit `cabinpi-daemon.service`:
   ```ini
   WorkingDirectory=/custom/path
   ExecStart=/custom/path/env/bin/python /custom/path/daemon.py ...
   ```

2. Reload systemd:
   ```bash
   sudo systemctl daemon-reload
   ```

### Multiple Instances

To run multiple instances with different configs:

```bash
# Copy service file with new name
sudo cp /etc/systemd/system/cabinpi-daemon.service /etc/systemd/system/cabinpi-daemon@.service

# Edit to use instance name
ExecStart=/opt/cabinpython/env/bin/python /opt/cabinpython/daemon.py --config /opt/cabinpython/config-%i.yaml

# Start instances
sudo systemctl start cabinpi-daemon@primary
sudo systemctl start cabinpi-daemon@secondary
```

### Email on Service Failure

Add to `[Service]` section:

```ini
OnFailure=status-email-user@%n.service
```

This requires setting up systemd email notifications.

## Integration with Monitoring Tools

### Prometheus

The daemon could expose metrics via HTTP endpoint (future enhancement).

### Nagios/Icinga

Check service status:

```bash
systemctl is-active cabinpi-daemon
```

Exit codes:
- 0 = active
- 3 = inactive

### Grafana

Configure Loki to read systemd journal:

```yaml
scrape_configs:
  - job_name: systemd-journal
    journal:
      matches: _SYSTEMD_UNIT=cabinpi-daemon.service
```

## Performance Tuning

### Polling Intervals

Adjust in `config.yaml`:

```yaml
daemon:
  polling_interval: 300  # Global default (seconds)

plugins:
  sensors:
    sht31:
      interval: 60  # Override for specific sensor
```

### Resource Limits

Adjust in service file:

```ini
# Memory limit
MemoryMax=512M

# CPU limit (50% of one core)
CPUQuota=50%
```

### Log Verbosity

```yaml
daemon:
  log_level: INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

Or override at runtime:

```bash
sudo systemctl edit cabinpi-daemon
```

Add:
```ini
[Service]
Environment="LOG_LEVEL=DEBUG"
```

## Backup and Restore

### Backup Configuration

```bash
sudo tar -czf cabinpython-backup-$(date +%Y%m%d).tar.gz \
  /opt/cabinpython/config.yaml \
  /opt/cabinpython/.env \
  /etc/systemd/system/cabinpi-daemon.service
```

### Restore Configuration

```bash
sudo tar -xzf cabinpython-backup-20250101.tar.gz -C /
sudo systemctl daemon-reload
sudo systemctl restart cabinpi-daemon
```

## Uninstall

```bash
# Stop and disable service
sudo systemctl stop cabinpi-daemon
sudo systemctl disable cabinpi-daemon

# Remove service file
sudo rm /etc/systemd/system/cabinpi-daemon.service
sudo systemctl daemon-reload

# Remove installation
sudo rm -rf /opt/cabinpython

# Remove user from groups (optional)
sudo gpasswd -d ckent dialout
sudo gpasswd -d ckent i2c
sudo gpasswd -d ckent gpio
```

## References

- [systemd Service Unit Documentation](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [systemd Watchdog](https://www.freedesktop.org/software/systemd/man/sd_watchdog_enabled.html)
- [Journal Documentation](https://www.freedesktop.org/software/systemd/man/journalctl.html)

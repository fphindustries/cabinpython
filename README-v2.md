# CabinPython v2 - Daemon-based Modular Monitoring System

A fault-tolerant, modular Python daemon service for monitoring off-grid cabin systems on Raspberry Pi 5.

## Architecture

CabinPython v2 is a complete redesign of the monitoring system with:

- **systemd daemon** - Runs as a service with automatic restart and watchdog monitoring
- **Modular plugins** - Easy to add/remove sensors and outputs via configuration
- **Fault tolerance** - Circuit breakers, automatic reconnection, graceful degradation
- **Event system** - Comprehensive event logging and alerting
- **Local-first** - All data stored locally, remote sync is best-effort

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/fphindustries/cabinpython.git
cd cabinpython

# Create virtual environment
python3 -m venv env
source env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy configuration templates
cp .env.example .env
cp config.yaml.example config.yaml

# Edit configuration files
nano .env
nano config.yaml
```

### Configuration

1. **Edit `.env`** - Add your secrets (database password, API keys, etc.)
2. **Edit `config.yaml`** - Configure sensors, outputs, and event rules

### Running

```bash
# Development mode (console logging)
python daemon.py --config config.yaml

# Production mode (systemd service)
sudo cp systemd/cabinpi-daemon.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable cabinpi-daemon.service
sudo systemctl start cabinpi-daemon.service
```

### Monitoring

```bash
# Check status
sudo systemctl status cabinpi-daemon.service

# View logs
journalctl -u cabinpi-daemon.service -f

# Reload configuration (without restart)
sudo systemctl reload cabinpi-daemon.service
```

## Project Structure

```
cabinpython/
├── daemon.py                    # Entry point
├── config.yaml                  # Configuration
├── requirements.txt             # Dependencies
├── cabinpi/                     # Main package
│   ├── core/                    # Core abstractions (protocols, models)
│   ├── managers/                # Plugin managers
│   ├── plugins/                 # Sensor and output implementations
│   └── utils/                   # Utilities
├── systemd/                     # systemd unit files
└── tests/                       # Unit tests
```

## Sensors

- **SHT31** - Indoor temperature and humidity (I2C)
- **Solar Controller** - Midnite Classic via Modbus RTU
- **Inverter** - Magnum inverter via RS232
- **Weather** - WeatherFlow API

## Outputs

- **MariaDB Storage** - Local database for measurements
- **Event Log** - Database for events and alarms
- **Cloudflare Sync** - Remote API synchronization
- **Email Alerts** - SMTP notifications

## Development

See [CLAUDE.md](CLAUDE.md) for development workflow and project tracking.

See [GitHub Issues](https://github.com/fphindustries/cabinpython/issues) for implementation status.

## Migration from v1

See [GITHUB_ISSUES.md](GITHUB_ISSUES.md) Issue #28 for migration scripts and procedures.

## License

See existing cabinpython license.

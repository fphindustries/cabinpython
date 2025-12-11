# CabinPython v2 - Claude Project Management

This file tracks the CabinPython v2 daemon-based architecture redesign project for Claude Code sessions.

## Project Overview

**Goal**: Transform the current cron-based sensor monitoring system into a fault-tolerant, modular Python daemon service running on Raspberry Pi 5.

**Epic Issue**: [#1 - CabinPython v2 - Daemon-based Modular Architecture](https://github.com/fphindustries/cabinpython/issues/1)

**Plan Document**: `~/.claude/plans/ticklish-dreaming-hennessy.md`

## Quick Links

- **GitHub Issues**: https://github.com/fphindustries/cabinpython/issues
- **Epic Issue**: https://github.com/fphindustries/cabinpython/issues/1
- **Current Branch**: `master` (will create feature branches for each phase)

## Architecture Summary

### Technology Stack
- **Process Management**: systemd Type=notify with watchdog
- **Event Loop**: asyncio + APScheduler
- **Plugin System**: Protocol-based with YAML config
- **Fault Tolerance**: pybreaker circuit breakers + auto-reconnection
- **Sensors**: pymodbus (solar), pymagnum (inverter), smbus2 (SHT31), httpx (weather)
- **Configuration**: YAML with environment variable substitution
- **Logging**: systemd journal via JournalHandler

### Core Design Principles
1. **Fault Tolerance**: Individual sensor failures don't crash the daemon
2. **Modular**: Easy to add/remove sensors and outputs via configuration
3. **Local-First**: All data stored locally, remote sync is best-effort
4. **Observable**: Health monitoring, watchdog, structured logging
5. **Maintainable**: Clear separation of concerns, testable components

## Implementation Status

### Phase 1: Core Framework (Issues #2-7)
Status: Not Started

- [ ] #2 - Setup directory structure and project scaffolding
- [ ] #3 - Implement core plugin protocols
- [ ] #4 - Build plugin loader and managers
- [ ] #5 - Implement daemon lifecycle and signal handling
- [ ] #6 - YAML configuration loading
- [ ] #7 - Setup logging infrastructure

### Phase 2: Sensor Plugins (Issues #8-13)
Status: Not Started

- [ ] #8 - Port SHT31 sensor to smbus2
- [ ] #9 - Port solar controller to pymodbus
- [ ] #10 - Port inverter to pymagnum
- [ ] #11 - Port weather API to httpx
- [ ] #12 - Implement circuit breaker wrapper
- [ ] #13 - Implement sensor scheduling

### Phase 3: Output Plugins (Issues #14-18)
Status: Not Started

- [ ] #14 - Create MariaDB measurement storage plugin
- [ ] #15 - Create MariaDB event log plugin
- [ ] #16 - Port Cloudflare sync plugin
- [ ] #17 - Port email notification plugin
- [ ] #18 - Implement output manager orchestration

### Phase 4: Event System (Issues #19-21)
Status: Not Started

- [ ] #19 - Implement event detector and rule engine
- [ ] #20 - Implement alert cooldown mechanism
- [ ] #21 - Add state change detection

### Phase 5: systemd Integration (Issues #22-25)
Status: Not Started

- [ ] #22 - Create systemd unit file
- [ ] #23 - Implement watchdog integration
- [ ] #24 - Implement health monitoring
- [ ] #25 - Add SIGHUP config reload

### Phase 6: Testing and Migration (Issues #26-29)
Status: Not Started

- [ ] #26 - Create unit tests
- [ ] #27 - Integration testing
- [ ] #28 - Create migration scripts
- [ ] #29 - Documentation

## Current System Reference

### Key Files (Existing System)
- `capture_measurements.py` - All sensor reading logic
  - Lines 134-152: SHT31 sensor
  - Lines 154-187: Magnum inverter
  - Lines 189-254: Solar charge controller
  - Lines 439-497: WeatherFlow weather
  - Lines 40-132: Email alerting
- `sync_common.py` - Database and API sync logic
- `README.md` - System documentation

### Database Schema (Existing)
- **measurements** table: 39 columns
  - Solar metrics (14 fields)
  - Indoor environmental (3 fields)
  - Outdoor weather (13 fields)
  - Inverter data (5 fields)
  - Sync tracking (synced flag)

### New Database Requirements
- **event_log** table (to be created):
  - id, timestamp, event_type, severity
  - sensor_id, message, data (JSON)
  - notified, indexes

## Directory Structure (Target)

```
/opt/cabinpython/
├── daemon.py                       # Entry point
├── config.yaml                     # Main configuration
├── .env                           # Secrets (DB password, API keys)
├── requirements.txt               # Dependencies
│
├── cabinpi/                       # Main package
│   ├── __init__.py
│   ├── daemon.py                 # SensorDaemon class
│   ├── signal_handler.py         # SIGTERM, SIGHUP handling
│   ├── health.py                 # Health monitoring
│   ├── config.py                 # YAML config loader
│   │
│   ├── core/                     # Core abstractions
│   │   ├── __init__.py
│   │   ├── protocols.py          # SensorPlugin, OutputPlugin protocols
│   │   ├── models.py             # SensorReading, SensorType dataclasses
│   │   ├── sliding_window.py     # Min/max/avg tracking
│   │   └── circuit_breaker.py    # Circuit breaker wrapper
│   │
│   ├── managers/                 # Plugin orchestration
│   │   ├── __init__.py
│   │   ├── sensor_manager.py     # Manages sensor lifecycle
│   │   ├── output_manager.py     # Manages output lifecycle
│   │   └── plugin_loader.py      # Dynamic plugin loading
│   │
│   ├── plugins/
│   │   ├── sensors/              # Sensor implementations
│   │   │   ├── __init__.py
│   │   │   ├── sht31.py         # Indoor temp/humidity (smbus2)
│   │   │   ├── solar_modbus.py  # Solar controller (pymodbus)
│   │   │   ├── inverter.py      # Magnum inverter (pymagnum)
│   │   │   └── weatherflow.py   # Weather API (httpx)
│   │   │
│   │   └── outputs/              # Output implementations
│   │       ├── __init__.py
│   │       ├── mariadb_storage.py      # Measurement storage
│   │       ├── mariadb_events.py       # Event log storage
│   │       ├── cloudflare_sync.py      # Remote API sync
│   │       └── email_notifier.py       # Email notifications
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logging.py            # Logging setup
│       └── conversions.py        # Unit conversions (reuse existing)
│
├── systemd/
│   └── cabinpi-daemon.service   # systemd unit file
│
└── tests/                        # Unit tests
    ├── test_sensors.py
    ├── test_outputs.py
    └── test_circuit_breaker.py
```

## Development Workflow

### Starting a New Issue
1. Create feature branch: `git checkout -b feature/issue-N-description`
2. Implement the feature following the issue checklist
3. Write tests (if applicable)
4. Commit with reference: `git commit -m "feat: description (#N)"`
5. Push and create PR: `gh pr create --fill`

### Branch Naming Convention
- `feature/issue-N-description` - Feature implementation
- `bugfix/issue-N-description` - Bug fixes
- `docs/issue-N-description` - Documentation updates

### Commit Message Format
```
<type>: <description> (#issue-number)

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`

## Environment Setup

### Dependencies (requirements.txt)
```
# Core async and scheduling
apscheduler>=3.11.0

# systemd integration
systemd-python>=235
systemd-watchdog>=1.0.1

# Fault tolerance
pybreaker>=1.0.1
tenacity>=8.2.0

# Configuration
PyYAML>=6.0
python-dotenv>=1.0.0

# Database
mysql-connector-python>=8.0

# Sensors (NEW)
smbus2>=0.4.3              # SHT31 (I2C)
pymodbus>=3.11.0           # Solar (Modbus)
pymagnum>=2.0.8            # Inverter
httpx>=0.27.0              # Weather API

# Utilities
python-dateutil
suntime
picamera2

# Development
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
```

### Installation Commands
```bash
# Create virtual environment
python3 -m venv /opt/cabinpython/env

# Activate environment
source /opt/cabinpython/env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Testing Strategy

### Unit Tests
- Mock all hardware interfaces (I2C, Serial, HTTP)
- Test each sensor plugin independently
- Test each output plugin independently
- Test circuit breaker state transitions
- Test event detection logic
- Target: >80% code coverage

### Integration Tests
- Full daemon lifecycle (startup, run, shutdown)
- Sensor failure scenarios
- Output failure scenarios
- Circuit breaker recovery
- Config reload (SIGHUP)
- Watchdog timeout

### Manual Testing on Pi 5
- Test with actual hardware sensors
- Verify systemd integration
- Monitor resource usage (CPU, memory)
- Test graceful shutdown
- Verify data accuracy

## Migration Strategy

### Pre-Migration Checklist
- [ ] All Phase 1-6 issues completed
- [ ] Unit tests passing (>80% coverage)
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] Migration scripts tested

### Cutover Process
1. Install dependencies: `pip install -r requirements.txt`
2. Convert config: `python scripts/convert_config.py config.ini > config.yaml`
3. Create .env file with secrets
4. Create event_log table: `mysql cabinpi < migrations/001_event_log.sql`
5. Test daemon: `python daemon.py --config config.yaml`
6. Install systemd service: `sudo cp systemd/cabinpi-daemon.service /etc/systemd/system/`
7. Disable cron: `crontab -e` (comment out cabinpython entries)
8. Start daemon: `sudo systemctl start cabinpi-daemon.service`
9. Monitor logs: `journalctl -u cabinpi-daemon.service -f`
10. Monitor for 48 hours

### Rollback Plan
If issues arise:
1. Stop daemon: `sudo systemctl stop cabinpi-daemon.service`
2. Re-enable cron: `crontab -e` (uncomment lines)
3. Verify old system working
4. Document issues for resolution

## Success Criteria

- [x] Planning complete
- [x] GitHub issues created (29 issues)
- [ ] Phase 1 complete (Core Framework)
- [ ] Phase 2 complete (Sensor Plugins)
- [ ] Phase 3 complete (Output Plugins)
- [ ] Phase 4 complete (Event System)
- [ ] Phase 5 complete (systemd Integration)
- [ ] Phase 6 complete (Testing and Migration)
- [ ] Daemon running as systemd service
- [ ] All sensors working
- [ ] Data written to MariaDB
- [ ] Remote sync working
- [ ] Email alerts working
- [ ] Event log working
- [ ] Circuit breakers working
- [ ] Config reload working
- [ ] Graceful shutdown working

## Important Notes for Claude

### When Resuming Work
1. Check this file for current phase and progress
2. Review open issues on GitHub
3. Check git status for any uncommitted work
4. Review plan document: `~/.claude/plans/ticklish-dreaming-hennessy.md`

### Code Style Guidelines
- Use type hints throughout
- Follow PEP 8 style guide
- Write comprehensive docstrings
- Add logging at appropriate levels
- Handle errors gracefully
- Write tests for new code

### Key Constraints
- Must run on Raspberry Pi 5 (Raspbian)
- Must maintain backward compatibility with existing database schema
- Must support graceful degradation (sensors can fail independently)
- Must be fault-tolerant (automatic reconnection, circuit breakers)
- Must log to systemd journal
- No emojis in code or logs unless explicitly requested

### Hardware Access Requirements
- I2C access (SHT31 sensor)
- Serial port access (Solar controller, Inverter)
- Network access (Weather API, Cloudflare sync)
- User must be in `dialout` group for serial access

## Session History

### Session 1 - 2025-12-10
- ✅ Analyzed current codebase
- ✅ Researched daemon architecture and sensor libraries
- ✅ Created comprehensive implementation plan
- ✅ Created 29 GitHub issues (#1-29)
- ✅ Created GITHUB_ISSUES.md template file
- ✅ Created this CLAUDE.md tracking file

**Next Session**: Start Phase 1 - Issue #2 (Setup directory structure)

---

## Quick Commands Reference

```bash
# Git
git status
git checkout -b feature/issue-N-description
git add .
git commit -m "feat: description (#N)"
git push origin feature/issue-N-description

# GitHub CLI
gh issue list
gh issue view N
gh pr create --fill

# Python/Testing
source /opt/cabinpython/env/bin/activate
python -m pytest tests/
python -m pytest --cov=cabinpi tests/

# systemd (when ready)
sudo systemctl daemon-reload
sudo systemctl status cabinpi-daemon.service
sudo systemctl start cabinpi-daemon.service
sudo systemctl stop cabinpi-daemon.service
sudo systemctl reload cabinpi-daemon.service
journalctl -u cabinpi-daemon.service -f

# Database
mysql -u cabinpi -p cabinpi
```

---

Last Updated: 2025-12-10

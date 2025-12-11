# GitHub Issues for CabinPython v2

Use this file to create GitHub issues in the `fphindustries/cabinpython` repository.

---

## Epic Issue

**Title**: `[Epic] CabinPython v2 - Daemon-based Modular Architecture`

**Labels**: `enhancement`, `epic`

**Body**:
```markdown
# CabinPython v2 - Complete System Redesign

Transform the current cron-based sensor monitoring system into a fault-tolerant, modular Python daemon service.

## Plan Document
See: `/home/ckent/.claude/plans/ticklish-dreaming-hennessy.md`

## Architecture Overview
- **Process Management**: systemd with watchdog
- **Event Loop**: asyncio + APScheduler
- **Plugin System**: Protocol-based plugins with YAML config
- **Fault Tolerance**: Circuit breakers + auto-reconnection
- **New Libraries**: pymodbus, pymagnum, smbus2, httpx

## Implementation Phases
- Phase 1: Core Framework (Issues #1-6)
- Phase 2: Sensor Plugins (Issues #7-12)
- Phase 3: Output Plugins (Issues #13-17)
- Phase 4: Event System (Issues #18-20)
- Phase 5: systemd Integration (Issues #21-24)
- Phase 6: Testing and Migration (Issues #25-28)
```

---

## Phase 1: Core Framework

### Issue #1
**Title**: Setup directory structure and project scaffolding

**Labels**: `phase-1`, `infrastructure`

**Body**:
```markdown
## Objective
Create the new `/opt/cabinpython/cabinpi/` package structure and initial project files.

## Tasks
- [ ] Create directory structure as per plan
- [ ] Create `requirements.txt` with new dependencies
- [ ] Create `.env.example` template
- [ ] Create all `__init__.py` files
- [ ] Setup Python package configuration

## Directory Structure
```
/opt/cabinpython/
├── daemon.py
├── config.yaml
├── .env
├── requirements.txt
├── cabinpi/
│   ├── __init__.py
│   ├── core/
│   ├── managers/
│   ├── plugins/
│   └── utils/
└── tests/
```

## Dependencies
```
apscheduler>=3.11.0
systemd-python>=235
systemd-watchdog>=1.0.1
pybreaker>=1.0.1
tenacity>=8.2.0
PyYAML>=6.0
python-dotenv>=1.0.0
mysql-connector-python>=8.0
smbus2>=0.4.3
pymodbus>=3.11.0
pymagnum>=2.0.8
httpx>=0.27.0
python-dateutil
suntime
picamera2
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
```

## Related Issues
Part of #EPIC
```

---

### Issue #2
**Title**: Implement core plugin protocols

**Labels**: `phase-1`, `core`

**Body**:
```markdown
## Objective
Create the plugin protocols and data models that define the interface for sensors and outputs.

## Tasks
- [ ] Create `SensorPlugin` protocol in `cabinpi/core/protocols.py`
- [ ] Create `OutputPlugin` protocol in `cabinpi/core/protocols.py`
- [ ] Create `SensorReading` dataclass in `cabinpi/core/models.py`
- [ ] Create `SensorType` enum in `cabinpi/core/models.py`
- [ ] Add comprehensive docstrings
- [ ] Add type hints throughout

## SensorPlugin Protocol
```python
class SensorPlugin(Protocol):
    @property
    def sensor_id(self) -> str: ...

    @property
    def sensor_type(self) -> SensorType: ...

    async def initialize(self, config: Dict[str, Any]) -> bool: ...

    async def read(self) -> SensorReading: ...

    async def shutdown(self) -> None: ...

    async def health_check(self) -> bool: ...
```

## OutputPlugin Protocol
```python
class OutputPlugin(Protocol):
    @property
    def output_id(self) -> str: ...

    @property
    def output_type(self) -> str: ...

    async def initialize(self, config: Dict[str, Any]) -> bool: ...

    async def write(self, data: Any) -> bool: ...

    async def shutdown(self) -> None: ...
```

## Related Issues
Part of #EPIC
Depends on #1
```

---

### Issue #3
**Title**: Build plugin loader and managers

**Labels**: `phase-1`, `core`

**Body**:
```markdown
## Objective
Implement the plugin loading system and lifecycle managers.

## Tasks
- [ ] Implement `PluginLoader` in `cabinpi/managers/plugin_loader.py`
  - Dynamic module loading via importlib
  - Plugin validation against protocols
  - Error handling for failed loads
- [ ] Implement `SensorManager` in `cabinpi/managers/sensor_manager.py`
  - Sensor initialization
  - Sensor lifecycle management
  - Health tracking
- [ ] Implement `OutputManager` in `cabinpi/managers/output_manager.py`
  - Output initialization
  - Data routing by output type
  - Failure handling

## Plugin Loader Features
- Load plugins by module path from config
- Validate plugins implement required protocol
- Handle import errors gracefully
- Return plugin instances

## Manager Features
- Initialize all enabled plugins
- Track plugin health status
- Graceful shutdown of all plugins
- Report plugin states

## Related Issues
Part of #EPIC
Depends on #2
```

---

### Issue #4
**Title**: Implement daemon lifecycle and signal handling

**Labels**: `phase-1`, `core`

**Body**:
```markdown
## Objective
Create the main daemon class with signal handling and event loop.

## Tasks
- [ ] Create `SignalHandler` in `cabinpi/signal_handler.py`
  - Handle SIGTERM (graceful shutdown)
  - Handle SIGINT (Ctrl+C)
  - Handle SIGHUP (config reload)
- [ ] Create `SensorDaemon` class in `cabinpi/daemon.py`
  - asyncio event loop setup
  - APScheduler integration
  - Main run loop
  - Graceful shutdown sequence
- [ ] Create daemon entry point in `/opt/cabinpython/daemon.py`
  - Argument parsing
  - Daemon instantiation
  - Error handling

## Signal Handling
- SIGTERM: Set shutdown event, cleanup, exit
- SIGHUP: Set reload event, reload config
- SIGINT: Same as SIGTERM

## Daemon Lifecycle
1. Load configuration
2. Initialize managers
3. Setup signal handlers
4. Start scheduler
5. Notify systemd (READY=1)
6. Run main loop
7. Wait for shutdown signal
8. Cleanup and exit

## Related Issues
Part of #EPIC
Depends on #3
```

---

### Issue #5
**Title**: YAML configuration loading

**Labels**: `phase-1`, `configuration`

**Body**:
```markdown
## Objective
Implement YAML configuration loading with environment variable substitution.

## Tasks
- [ ] Create config loader in `cabinpi/config.py`
  - Load YAML file
  - Substitute ${VAR} with environment variables
  - Validate required sections
  - Provide sensible defaults
- [ ] Create example `config.yaml`
- [ ] Create `.env.example` template
- [ ] Add configuration validation
- [ ] Document configuration schema

## Environment Variable Substitution
Support `${VAR_NAME}` syntax in YAML:
```yaml
config:
  password: ${DB_PASSWORD}
```

## Validation
- Required sections: daemon, plugins
- Required daemon fields: polling_interval
- Validate sensor/output module paths exist
- Validate threshold values are numeric

## Related Issues
Part of #EPIC
Depends on #1
```

---

### Issue #6
**Title**: Setup logging infrastructure

**Labels**: `phase-1`, `infrastructure`

**Body**:
```markdown
## Objective
Configure logging with systemd journal integration.

## Tasks
- [ ] Create logging setup in `cabinpi/utils/logging.py`
  - systemd JournalHandler integration
  - Console handler for development
  - Structured log formatting
  - Log level configuration
- [ ] Add logging to all modules
- [ ] Document logging patterns

## Logging Handlers
1. **JournalHandler**: For systemd journal (production)
2. **StreamHandler**: For console (development)

## Log Levels
- DEBUG: Detailed sensor readings, internal state
- INFO: Normal operations, sensor polls, syncs
- WARNING: Degraded operations, sensor failures
- ERROR: Critical errors, circuit breaker trips
- EXCEPTION: Full stack traces

## Log Format
```
2025-12-10 10:30:00 [INFO] cabinpi.sensors.sht31: Temperature: 20.5°C, Humidity: 45%
```

## Related Issues
Part of #EPIC
Depends on #1
```

---

## Phase 2: Sensor Plugins

### Issue #7
**Title**: Port SHT31 sensor to smbus2

**Labels**: `phase-2`, `sensor`, `migration`

**Body**:
```markdown
## Objective
Migrate SHT31 temperature/humidity sensor from adafruit_sht31d to smbus2.

## Tasks
- [ ] Create `cabinpi/plugins/sensors/sht31.py`
- [ ] Implement SensorPlugin protocol
- [ ] Implement direct I2C communication via smbus2
- [ ] Calculate temperature and humidity from raw values
- [ ] Add error handling for I2C failures
- [ ] Implement health_check method
- [ ] Add unit tests

## Migration Source
Migrate logic from [capture_measurements.py:134-152](/home/ckent/repos/cabinpython/capture_measurements.py#L134-L152)

## I2C Communication
- Address: 0x44 (default)
- Command: 0x2C06 (high repeatability measurement)
- Wait: 15ms for measurement
- Read: 6 bytes (temp + CRC + humidity + CRC)

## Calculations
```python
temp_c = -45 + (175 * raw_temp / 65535.0)
humidity = 100 * raw_hum / 65535.0
```

## Data Output
```python
{
    'int_c': float,  # Temperature in Celsius
    'int_f': float,  # Temperature in Fahrenheit
    'humidity': float  # Relative humidity %
}
```

## Related Issues
Part of #EPIC
Depends on #2, #3
```

---

### Issue #8
**Title**: Port solar controller to pymodbus

**Labels**: `phase-2`, `sensor`, `migration`

**Body**:
```markdown
## Objective
Migrate Midnite Classic solar charge controller from minimalmodbus to pymodbus.

## Tasks
- [ ] Create `cabinpi/plugins/sensors/solar_modbus.py`
- [ ] Implement SensorPlugin protocol
- [ ] Use AsyncModbusSerialClient
- [ ] Configure automatic reconnection
- [ ] Read registers 4114-4142 (29 registers)
- [ ] Parse register values
- [ ] Implement health_check method
- [ ] Add unit tests

## Migration Source
Migrate logic from [capture_measurements.py:189-254](/home/ckent/repos/cabinpython/capture_measurements.py#L189-L254)

## Modbus Configuration
- Port: `/dev/serial/by-id/usb-FTDI_USB_Serial_Converter_FTDY7VMG-if00-port0`
- Slave ID: 10
- Baudrate: 9600
- Registers: 4114-4142 (29 total)

## Auto-Reconnection
```python
client = AsyncModbusSerialClient(
    port=port,
    baudrate=9600,
    timeout=3,
    retries=3,
    reconnect_delay=0.1,
    reconnect_delay_max=300
)
```

## Data Output
All solar metrics as per existing schema (dispavgVbatt, dispavgVpv, watts, etc.)

## Related Issues
Part of #EPIC
Depends on #2, #3
```

---

### Issue #9
**Title**: Port inverter to pymagnum

**Labels**: `phase-2`, `sensor`, `migration`

**Body**:
```markdown
## Objective
Install pymagnum and create inverter sensor plugin.

## Tasks
- [ ] Install `pymagnum` library
- [ ] Create `cabinpi/plugins/sensors/inverter.py`
- [ ] Implement SensorPlugin protocol
- [ ] Wrap synchronous pymagnum in async executor
- [ ] Parse inverter device data
- [ ] Implement health_check method
- [ ] Add unit tests

## Migration Source
Migrate logic from [capture_measurements.py:154-187](/home/ckent/repos/cabinpython/capture_measurements.py#L154-L187)

## Async Wrapper Pattern
```python
async def read(self):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, self._read_sync)
```

## Data Output
```python
{
    'InverterOn': int,
    'InverterMode': int,
    'InverterFault': int,
    'InverterVACOut': float,
    'InverterAACOut': float,
    'Invertervdc': float
}
```

## Related Issues
Part of #EPIC
Depends on #2, #3
```

---

### Issue #10
**Title**: Port weather API to httpx

**Labels**: `phase-2`, `sensor`, `migration`

**Body**:
```markdown
## Objective
Migrate WeatherFlow API from requests to httpx with async support.

## Tasks
- [ ] Create `cabinpi/plugins/sensors/weatherflow.py`
- [ ] Implement SensorPlugin protocol
- [ ] Use httpx.AsyncClient
- [ ] Add retry logic with tenacity
- [ ] Parse observation data
- [ ] Implement unit conversions
- [ ] Implement health_check method
- [ ] Add unit tests

## Migration Source
Migrate logic from [capture_measurements.py:439-497](/home/ckent/repos/cabinpython/capture_measurements.py#L439-L497)

## API Details
- Endpoint: `https://swd.weatherflow.com/swd/rest/observations/device/{device}?token={token}`
- Method: GET
- Timeout: 10s

## Retry Logic
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60)
)
```

## Unit Conversions (reuse existing)
- m/s → mph
- mb → inHg
- °C → °F
- mm → inches
- km → miles

## Related Issues
Part of #EPIC
Depends on #2, #3
```

---

### Issue #11
**Title**: Implement circuit breaker wrapper

**Labels**: `phase-2`, `fault-tolerance`

**Body**:
```markdown
## Objective
Wrap all sensors with circuit breaker pattern using pybreaker.

## Tasks
- [ ] Create `cabinpi/core/circuit_breaker.py`
- [ ] Integrate pybreaker library
- [ ] Add circuit state change event logging
- [ ] Configure thresholds from config
- [ ] Update SensorManager to use circuit breakers
- [ ] Add unit tests

## Circuit Breaker Config
```yaml
circuit_breaker:
  failure_threshold: 5  # Open after 5 failures
  recovery_timeout: 60  # Try recovery after 60s
```

## State Transitions
- **Closed**: Normal operation
- **Open**: Too many failures, stop trying
- **Half-Open**: Testing recovery

## Event Logging
Log state changes as system events:
```python
{
    'sensor_id': 'sht31',
    'event': 'circuit_opened',
    'failure_count': 5
}
```

## Related Issues
Part of #EPIC
Depends on #2, #3, #7, #8, #9, #10
```

---

### Issue #12
**Title**: Implement sensor scheduling

**Labels**: `phase-2`, `scheduling`

**Body**:
```markdown
## Objective
Configure APScheduler to poll sensors at configured intervals.

## Tasks
- [ ] Update SensorManager to use APScheduler
- [ ] Support per-sensor interval overrides
- [ ] Configure job max_instances and coalesce
- [ ] Handle job failures gracefully
- [ ] Log scheduling events
- [ ] Add unit tests

## Scheduling Pattern
```python
scheduler.add_job(
    self._poll_sensor,
    trigger=IntervalTrigger(seconds=interval),
    args=[sensor_id],
    id=f"poll_{sensor_id}",
    max_instances=1,  # Don't run if previous still running
    coalesce=True     # If missed, only run once
)
```

## Interval Configuration
- Global default: 300s (5 minutes)
- Per-sensor override in config
- Weather sensor: 600s (10 minutes)

## Related Issues
Part of #EPIC
Depends on #3, #7, #8, #9, #10
```

---

## Phase 3: Output Plugins

### Issue #13
**Title**: Create MariaDB measurement storage plugin

**Labels**: `phase-3`, `output`, `database`

**Body**:
```markdown
## Objective
Create output plugin for storing measurements in MariaDB.

## Tasks
- [ ] Create `cabinpi/plugins/outputs/mariadb_storage.py`
- [ ] Implement OutputPlugin protocol
- [ ] Port database insertion logic
- [ ] Keep existing `measurements` table schema
- [ ] Add connection pooling
- [ ] Implement error handling
- [ ] Add unit tests

## Migration Source
Reuse logic from [sync_common.py](/home/ckent/repos/cabinpython/sync_common.py)

## Database Operations
- Insert measurements with synced=0
- Handle connection failures gracefully
- Use mysql-connector-python

## Schema Compatibility
Must write to existing `measurements` table with all 39 columns.

## Related Issues
Part of #EPIC
Depends on #2, #3
```

---

### Issue #14
**Title**: Create MariaDB event log plugin

**Labels**: `phase-3`, `output`, `database`

**Body**:
```markdown
## Objective
Create output plugin for storing events in new event_log table.

## Tasks
- [ ] Create SQL migration for event_log table
- [ ] Create `cabinpi/plugins/outputs/mariadb_events.py`
- [ ] Implement OutputPlugin protocol
- [ ] Store events with severity
- [ ] Track notification status
- [ ] Implement error handling
- [ ] Add unit tests

## Event Log Table
```sql
CREATE TABLE event_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    severity ENUM('info', 'warning', 'error', 'critical') NOT NULL,
    sensor_id VARCHAR(50),
    message TEXT,
    data JSON,
    notified BOOLEAN DEFAULT FALSE,
    INDEX idx_timestamp (timestamp),
    INDEX idx_event_type (event_type),
    INDEX idx_severity (severity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

## Related Issues
Part of #EPIC
Depends on #2, #3
```

---

### Issue #15
**Title**: Port Cloudflare sync plugin

**Labels**: `phase-3`, `output`, `api`

**Body**:
```markdown
## Objective
Create output plugin for syncing to Cloudflare-protected API.

## Tasks
- [ ] Create `cabinpi/plugins/outputs/cloudflare_sync.py`
- [ ] Implement OutputPlugin protocol
- [ ] Reuse API conversion logic from sync_common.py
- [ ] Implement batch sync
- [ ] Handle Cloudflare Access authentication
- [ ] Update synced flag on success
- [ ] Add retry logic
- [ ] Add unit tests

## Migration Source
Reuse logic from [sync_common.py](/home/ckent/repos/cabinpython/sync_common.py)

## API Format
- Convert database fields to camelCase
- Batch records in "records" array
- Include Cloudflare Access headers

## Batch Processing
- Default batch size: 10
- Stop on first failure
- Mark synced=1 on success

## Related Issues
Part of #EPIC
Depends on #2, #3, #13
```

---

### Issue #16
**Title**: Port email notification plugin

**Labels**: `phase-3`, `output`, `notification`

**Body**:
```markdown
## Objective
Create output plugin for email notifications via SMTP.

## Tasks
- [ ] Create `cabinpi/plugins/outputs/email_notifier.py`
- [ ] Implement OutputPlugin protocol
- [ ] Reuse SMTP logic from capture_measurements.py
- [ ] Implement per-event-type cooldown
- [ ] Support multiple recipients
- [ ] Add error handling
- [ ] Add unit tests

## Migration Source
Reuse logic from [capture_measurements.py:40-132](/home/ckent/repos/cabinpython/capture_measurements.py#L40-L132)

## SMTP Configuration
- SMTP_SSL on port 465
- Support Gmail and standard SMTP
- Comma-separated recipient list

## Cooldown Mechanism
- Track last notification time per event type
- Configurable cooldown period (default: 1440 min)
- Store state in database or file

## Related Issues
Part of #EPIC
Depends on #2, #3
```

---

### Issue #17
**Title**: Implement output manager orchestration

**Labels**: `phase-3`, `core`

**Body**:
```markdown
## Objective
Implement output routing and failure handling in OutputManager.

## Tasks
- [ ] Update OutputManager to route data by type
- [ ] Route measurements to measurement_storage outputs
- [ ] Route events to event_log and notification outputs
- [ ] Handle output failures gracefully
- [ ] Log output errors
- [ ] Add unit tests

## Output Routing
```python
# Measurements go to measurement_storage
for output in storage_outputs:
    await output.write(measurement)

# Events go to event_log and notifications
for output in event_outputs:
    await output.write(event)
```

## Failure Handling
- If output fails, log error but continue
- Don't block other outputs
- Track output health

## Related Issues
Part of #EPIC
Depends on #3, #13, #14, #15, #16
```

---

## Phase 4: Event System

### Issue #18
**Title**: Implement event detector and rule engine

**Labels**: `phase-4`, `events`

**Body**:
```markdown
## Objective
Implement event detection and rule evaluation engine.

## Tasks
- [ ] Create event detector in `cabinpi/events/detector.py`
- [ ] Parse event rules from config
- [ ] Implement threshold condition checking
- [ ] Implement state change detection
- [ ] Support conditional dependencies
- [ ] Emit events to outputs
- [ ] Add unit tests

## Event Rule Types
1. **Threshold**: `condition: below/above`, `threshold: value`
2. **State Change**: `condition: changed`
3. **Conditional**: `depends_on: other_event`

## Example Rules
```yaml
events:
  battery_low:
    sensor: solar_controller
    field: dispavgVbatt
    condition: below
    threshold: 12.0
    severity: critical
    notify: true
```

## Related Issues
Part of #EPIC
Depends on #12
```

---

### Issue #19
**Title**: Implement alert cooldown mechanism

**Labels**: `phase-4`, `events`

**Body**:
```markdown
## Objective
Implement cooldown to prevent alert spam.

## Tasks
- [ ] Track last notification time per event type
- [ ] Support configurable cooldown periods
- [ ] Store state in database
- [ ] Check cooldown before sending notifications
- [ ] Add unit tests

## Cooldown Logic
```python
if last_alert_time and (now - last_alert_time) < cooldown:
    # Skip notification
    return

# Send notification and update last_alert_time
```

## Storage
Store in event_log table or separate state table.

## Related Issues
Part of #EPIC
Depends on #14, #18
```

---

### Issue #20
**Title**: Add state change detection

**Labels**: `phase-4`, `events`

**Body**:
```markdown
## Objective
Track sensor values and detect state changes.

## Tasks
- [ ] Create state tracker
- [ ] Store previous values
- [ ] Compare current vs previous
- [ ] Emit change events
- [ ] Support specific fields (chargeState, inverterMode, etc.)
- [ ] Add unit tests

## State Change Detection
For fields like:
- Solar chargeState
- Solar batteryState
- Inverter mode
- Inverter fault status

## Event Emission
```python
if current_value != previous_value:
    emit_event({
        'type': 'charge_state_change',
        'sensor': 'solar_controller',
        'field': 'chargeState',
        'old_value': previous_value,
        'new_value': current_value
    })
```

## Related Issues
Part of #EPIC
Depends on #18
```

---

## Phase 5: systemd Integration

### Issue #21
**Title**: Create systemd unit file

**Labels**: `phase-5`, `systemd`

**Body**:
```markdown
## Objective
Create production-ready systemd service definition.

## Tasks
- [ ] Create `/opt/cabinpython/systemd/cabinpi-daemon.service`
- [ ] Configure Type=notify
- [ ] Setup watchdog monitoring
- [ ] Add security hardening
- [ ] Configure resource limits
- [ ] Add installation instructions
- [ ] Test service lifecycle

## Unit File Location
`/etc/systemd/system/cabinpi-daemon.service`

## Key Features
- Type=notify for startup notification
- WatchdogSec=90 for health monitoring
- Restart=always for auto-recovery
- Security hardening (NoNewPrivileges, ProtectSystem, etc.)
- Resource limits (MemoryMax, CPUQuota)

## Installation
```bash
sudo cp systemd/cabinpi-daemon.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable cabinpi-daemon.service
sudo systemctl start cabinpi-daemon.service
```

## Related Issues
Part of #EPIC
Depends on #4
```

---

### Issue #22
**Title**: Implement watchdog integration

**Labels**: `phase-5`, `systemd`

**Body**:
```markdown
## Objective
Integrate systemd watchdog for health monitoring.

## Tasks
- [ ] Install systemd-watchdog library
- [ ] Send READY=1 on startup
- [ ] Send WATCHDOG=1 heartbeats
- [ ] Calculate heartbeat interval (WatchdogSec/2)
- [ ] Add watchdog task to event loop
- [ ] Test watchdog timeout behavior

## Watchdog Protocol
```python
from systemd import daemon as sd_daemon

# On startup
sd_daemon.notify('READY=1')

# Every 45s (for WatchdogSec=90)
sd_daemon.notify('WATCHDOG=1')

# On shutdown
sd_daemon.notify('STOPPING=1')
```

## Health Check
Only send heartbeat if daemon is healthy:
- Sensors responding
- Event loop running
- No critical errors

## Related Issues
Part of #EPIC
Depends on #4, #21
```

---

### Issue #23
**Title**: Implement health monitoring

**Labels**: `phase-5`, `monitoring`

**Body**:
```markdown
## Objective
Track and report daemon health status.

## Tasks
- [ ] Create health monitor in `cabinpi/health.py`
- [ ] Track sensor health status
- [ ] Track output health status
- [ ] Report degraded state
- [ ] Log health metrics
- [ ] Expose health status

## Health States
- **Healthy**: All sensors and outputs working
- **Degraded**: Some sensors/outputs failing
- **Critical**: All sensors failing or core failure

## Health Metrics
- Sensor success/failure counts
- Output success/failure counts
- Circuit breaker states
- Last successful poll times

## Health Reporting
```python
{
    'status': 'degraded',
    'sensors': {
        'sht31': 'healthy',
        'solar': 'circuit_open',
        'inverter': 'healthy',
        'weather': 'healthy'
    },
    'outputs': {
        'database': 'healthy',
        'remote_sync': 'failing'
    }
}
```

## Related Issues
Part of #EPIC
Depends on #11, #17
```

---

### Issue #24
**Title**: Add SIGHUP config reload

**Labels**: `phase-5`, `configuration`

**Body**:
```markdown
## Objective
Implement configuration reload on SIGHUP signal.

## Tasks
- [ ] Handle SIGHUP in SignalHandler
- [ ] Reload YAML configuration
- [ ] Identify config changes
- [ ] Restart affected sensors/outputs
- [ ] Maintain state during reload
- [ ] Test reload scenarios

## Reload Process
1. Receive SIGHUP signal
2. Reload config.yaml
3. Compare with current config
4. Shutdown changed plugins
5. Initialize new plugins
6. Resume operations

## Restart Logic
- If sensor config changed → restart sensor
- If sensor enabled/disabled → start/stop sensor
- If output config changed → restart output
- If global config changed → log warning (requires full restart)

## State Preservation
- Keep scheduler running
- Don't lose in-flight measurements
- Maintain circuit breaker states

## Related Issues
Part of #EPIC
Depends on #4, #5
```

---

## Phase 6: Testing and Migration

### Issue #25
**Title**: Create unit tests

**Labels**: `phase-6`, `testing`

**Body**:
```markdown
## Objective
Create comprehensive unit test suite.

## Tasks
- [ ] Test sensor plugins (mocked hardware)
- [ ] Test output plugins (mocked databases)
- [ ] Test circuit breaker behavior
- [ ] Test event detection logic
- [ ] Test configuration loading
- [ ] Test signal handling
- [ ] Achieve >80% code coverage

## Test Framework
- pytest
- pytest-asyncio for async tests
- pytest-cov for coverage reports

## Test Categories
1. **Sensor Tests**: Mock I2C, Modbus, Serial, HTTP
2. **Output Tests**: Mock database, API, SMTP
3. **Circuit Breaker**: Test state transitions
4. **Events**: Test rule evaluation
5. **Config**: Test YAML parsing and validation

## Coverage Target
Minimum 80% code coverage

## Related Issues
Part of #EPIC
```

---

### Issue #26
**Title**: Integration testing

**Labels**: `phase-6`, `testing`

**Body**:
```markdown
## Objective
Test complete daemon lifecycle and failure scenarios.

## Tasks
- [ ] Test full daemon startup and shutdown
- [ ] Test graceful shutdown (SIGTERM)
- [ ] Test config reload (SIGHUP)
- [ ] Test sensor failure scenarios
- [ ] Test output failure scenarios
- [ ] Test circuit breaker recovery
- [ ] Test watchdog timeout
- [ ] Document test procedures

## Test Scenarios
1. **Normal Operation**: All sensors working
2. **Sensor Failure**: One sensor fails, others continue
3. **Network Failure**: Remote sync fails, local storage continues
4. **Database Failure**: Database down, data queued
5. **Config Reload**: Change sensor interval, verify reload
6. **Watchdog**: Stop heartbeat, verify restart

## Test Environment
Run tests on Raspberry Pi 5 or similar environment

## Related Issues
Part of #EPIC
Depends on all previous issues
```

---

### Issue #27
**Title**: Create migration scripts

**Labels**: `phase-6`, `migration`

**Body**:
```markdown
## Objective
Create tools to migrate from old system to new.

## Tasks
- [ ] Create config converter (INI → YAML)
- [ ] Create cutover checklist
- [ ] Create rollback procedure
- [ ] Test migration process
- [ ] Document migration steps

## Config Converter
Script to convert `config.ini` to `config.yaml`:
```bash
python scripts/convert_config.py config.ini > config.yaml
```

## Cutover Checklist
1. Install dependencies
2. Convert configuration
3. Create event_log table
4. Test daemon manually
5. Install systemd service
6. Disable cron jobs
7. Start daemon
8. Monitor for 48 hours

## Rollback Procedure
1. Stop daemon
2. Re-enable cron jobs
3. Verify old system working

## Related Issues
Part of #EPIC
```

---

### Issue #28
**Title**: Documentation

**Labels**: `phase-6`, `documentation`

**Body**:
```markdown
## Objective
Update all documentation for new architecture.

## Tasks
- [ ] Update README.md
- [ ] Create plugin development guide
- [ ] Create troubleshooting guide
- [ ] Document systemd commands
- [ ] Document configuration options
- [ ] Add architecture diagrams
- [ ] Document migration process

## Documentation Sections

### README.md Updates
- New architecture overview
- Installation instructions
- Configuration guide
- systemd commands
- Migration guide

### Plugin Development Guide
- How to create sensor plugins
- How to create output plugins
- Protocol requirements
- Testing plugins

### Troubleshooting Guide
- Common issues
- Circuit breaker diagnostics
- Log analysis
- Health monitoring

### systemd Commands
```bash
# Status
sudo systemctl status cabinpi-daemon.service

# Logs
journalctl -u cabinpi-daemon.service -f

# Reload config
sudo systemctl reload cabinpi-daemon.service

# Restart
sudo systemctl restart cabinpi-daemon.service
```

## Related Issues
Part of #EPIC
```

---

## How to Use This File

1. **Install GitHub CLI (optional)**:
   ```bash
   sudo apt install gh
   gh auth login
   ```

2. **Create Issues Manually**:
   - Copy each issue body
   - Create new issue on GitHub
   - Paste title, labels, and body
   - Link to epic issue

3. **Create Issues via CLI** (if installed):
   ```bash
   # Epic
   gh issue create --title "[Epic] CabinPython v2 - Daemon-based Modular Architecture" --label "enhancement,epic" --body-file epic.md

   # Individual issues
   gh issue create --title "Setup directory structure" --label "phase-1,infrastructure" --body-file issue01.md
   ```

4. **Track Progress**:
   - Use GitHub project board
   - Link all issues to epic
   - Close issues as completed
   - Create PRs referencing issue numbers

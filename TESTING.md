# CabinPython v2 - Testing Guide

Comprehensive testing guide for CabinPython v2 daemon.

## Test Structure

```
tests/
├── test_event_detector.py    # Event detection and rule engine tests
├── test_sensors.py            # Sensor plugin tests (with mocks)
├── test_integration.py        # Integration tests
└── __init__.py
```

## Running Tests

### Install Test Dependencies

```bash
cd /opt/cabinpython
source env/bin/activate
pip install pytest pytest-asyncio pytest-cov
```

### Run All Tests

```bash
pytest tests/
```

### Run Specific Test File

```bash
pytest tests/test_event_detector.py
```

### Run Specific Test

```bash
pytest tests/test_event_detector.py::TestEventRule::test_rule_below_threshold_triggers
```

### Run with Coverage

```bash
pytest tests/ --cov=cabinpi --cov-report=html
```

View coverage report:
```bash
open htmlcov/index.html
```

### Run with Verbose Output

```bash
pytest tests/ -v
```

### Run Only Unit Tests

```bash
pytest tests/ -m unit
```

### Run Only Integration Tests

```bash
pytest tests/ -m integration
```

## Test Categories

### Unit Tests

Test individual components in isolation:

- **Event Detector**: Rule evaluation, cooldowns, state changes
- **Sensors**: Plugin initialization and reading (mocked hardware)
- **Outputs**: Data writing and formatting (mocked connections)
- **Models**: Data class validation

**Characteristics**:
- Fast execution (< 1 second per test)
- No external dependencies
- Use mocks for I/O
- High coverage target (>80%)

### Integration Tests

Test interactions between components:

- **Daemon Lifecycle**: Initialization, running, shutdown
- **Event Detection**: Reading → Event → Output flow
- **Signal Handling**: SIGTERM, SIGHUP handling
- **Health Monitoring**: Status aggregation

**Characteristics**:
- Slower execution (1-5 seconds per test)
- May use temporary files/databases
- Test component interactions
- Focus on critical paths

### Hardware Tests

Test with actual hardware (manual testing):

- **SHT31 Sensor**: Actual I2C readings
- **Solar Controller**: Actual Modbus communication
- **Inverter**: Actual serial communication
- **WeatherFlow API**: Live API calls

**Characteristics**:
- Require physical hardware
- Run manually before deployment
- Verify calibration and accuracy
- Not in automated test suite

## Writing Tests

### Test Naming Convention

```python
class TestComponentName:
    """Test ComponentName class."""

    def test_specific_behavior(self):
        """Test that component does X when Y."""
        # Arrange
        # Act
        # Assert
```

### Async Test Example

```python
import pytest

class TestAsyncComponent:
    @pytest.mark.asyncio
    async def test_async_operation(self):
        """Test async operation."""
        result = await some_async_function()
        assert result is not None
```

### Mock Example

```python
from unittest.mock import Mock, patch

class TestSensorPlugin:
    @patch('cabinpi.plugins.sensors.sht31.SMBus')
    async def test_sensor_read(self, mock_smbus):
        """Test sensor reading with mocked I2C."""
        # Setup mock
        mock_bus = Mock()
        mock_bus.read_i2c_block_data.return_value = [0x63, 0x00, ...]
        mock_smbus.return_value = mock_bus

        # Test
        sensor = SHT31Sensor("test")
        await sensor.initialize({})
        reading = await sensor.read()

        # Verify
        assert reading.is_valid
        assert "int_c" in reading.measurements
```

### Fixture Example

```python
@pytest.fixture
def sample_config():
    """Provide sample configuration for tests."""
    return {
        "daemon": {"polling_interval": 300},
        "plugins": {"sensors": {}, "outputs": {}},
        "events": {}
    }

class TestWithFixture:
    def test_using_fixture(self, sample_config):
        """Test using fixture."""
        daemon = SensorDaemon(sample_config)
        assert daemon.config == sample_config
```

## Manual Testing Procedures

### Pre-Deployment Hardware Test

1. **SHT31 Sensor**:
   ```bash
   # Check I2C device
   i2cdetect -y 1  # Should show 0x44

   # Test reading
   cd /opt/cabinpython
   source env/bin/activate
   python3 << 'EOF'
   import asyncio
   from cabinpi.plugins.sensors.sht31 import SHT31Sensor

   async def test():
       sensor = SHT31Sensor("sht31")
       await sensor.initialize({"i2c_bus": 1, "i2c_address": 0x44})
       reading = await sensor.read()
       print(f"Temperature: {reading.measurements.get('int_f')}°F")
       print(f"Humidity: {reading.measurements.get('humidity')}%")

   asyncio.run(test())
   EOF
   ```

2. **Solar Controller**:
   ```bash
   # Check serial device
   ls -l /dev/ttyUSB0

   # Test Modbus communication
   python3 << 'EOF'
   import asyncio
   from cabinpi.plugins.sensors.solar_modbus import SolarModbusSensor

   async def test():
       sensor = SolarModbusSensor("solar")
       await sensor.initialize({"port": "/dev/ttyUSB0", "slave_address": 10})
       reading = await sensor.read()
       print(f"Battery Voltage: {reading.measurements.get('dispavgVbatt')}V")
       print(f"PV Voltage: {reading.measurements.get('dispavgVpv')}V")
       print(f"Power: {reading.measurements.get('watts')}W")

   asyncio.run(test())
   EOF
   ```

3. **Inverter**:
   ```bash
   # Test inverter communication
   python3 << 'EOF'
   import asyncio
   from cabinpi.plugins.sensors.inverter import InverterSensor

   async def test():
       sensor = InverterSensor("inverter")
       await sensor.initialize({"port": "/dev/ttyUSB1"})
       reading = await sensor.read()
       print(f"Inverter On: {reading.measurements.get('InverterOn')}")
       print(f"AC Out: {reading.measurements.get('InverterVACOut')}V")
       print(f"DC In: {reading.measurements.get('Invertervdc')}V")

   asyncio.run(test())
   EOF
   ```

4. **WeatherFlow API**:
   ```bash
   # Test API access
   python3 << 'EOF'
   import asyncio
   from cabinpi.plugins.sensors.weatherflow import WeatherFlowSensor

   async def test():
       sensor = WeatherFlowSensor("weather")
       await sensor.initialize({
           "device_id": "YOUR_DEVICE_ID",
           "api_token": "YOUR_TOKEN"
       })
       reading = await sensor.read()
       print(f"Temperature: {reading.measurements.get('ext_temp')}°F")
       print(f"Wind: {reading.measurements.get('wind_avg')} mph")
       print(f"Humidity: {reading.measurements.get('ext_humidity')}%")

   asyncio.run(test())
   EOF
   ```

### Database Test

```bash
# Test database connection
mysql -u cabinpi -p cabinpi << 'EOF'
-- Insert test measurement
INSERT INTO measurements (Date, int_f, humidity)
VALUES (NOW(), 72.5, 45.0);

-- Verify insert
SELECT * FROM measurements ORDER BY Date DESC LIMIT 1;

-- Delete test row
DELETE FROM measurements WHERE Date > NOW() - INTERVAL 1 MINUTE;
EOF
```

### Event Detection Test

1. Edit config.yaml to add a test rule:
   ```yaml
   events:
     test_alert:
       sensor: sht31
       field: int_f
       condition: above
       threshold: 70.0
       severity: info
       notify: false
   ```

2. Start daemon and trigger alert:
   ```bash
   sudo systemctl reload cabinpi-daemon
   journalctl -u cabinpi-daemon -f | grep test_alert
   ```

3. Check event log:
   ```bash
   mysql -u cabinpi -p cabinpi -e "SELECT * FROM event_log WHERE event_type='test_alert';"
   ```

### Email Notification Test

1. Edit config.yaml to add test event with notify:
   ```yaml
   events:
     test_email:
       sensor: sht31
       field: int_f
       condition: above
       threshold: 60.0  # Set low to trigger
       severity: warning
       notify: true
   ```

2. Reload and wait for trigger:
   ```bash
   sudo systemctl reload cabinpi-daemon
   ```

3. Check email inbox for alert

### Watchdog Test

```bash
# Check watchdog is enabled
journalctl -u cabinpi-daemon | grep -i watchdog

# Monitor watchdog pings
journalctl -u cabinpi-daemon -f | grep "Sent watchdog ping"
```

### Configuration Reload Test

```bash
# Make a change to config.yaml
sudo nano /opt/cabinpython/config.yaml

# Reload without restart
sudo systemctl reload cabinpi-daemon

# Verify reload in logs
journalctl -u cabinpi-daemon -n 20 | grep reload
```

### Circuit Breaker Test

Simulate sensor failure:

1. Disconnect a sensor (unplug USB)
2. Monitor logs for circuit breaker:
   ```bash
   journalctl -u cabinpi-daemon -f | grep "circuit breaker"
   ```
3. Reconnect sensor
4. Verify recovery:
   ```bash
   journalctl -u cabinpi-daemon | grep "recovered"
   ```

## Continuous Integration

### GitHub Actions Example

Create `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov

      - name: Run tests
        run: pytest tests/ --cov=cabinpi

      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Performance Testing

### Memory Usage

```bash
# Monitor memory during operation
watch -n 5 'systemctl status cabinpi-daemon | grep Memory'
```

### CPU Usage

```bash
# Monitor CPU
top -p $(systemctl show -p MainPID cabinpi-daemon | cut -d= -f2)
```

### Database Performance

```sql
-- Check slow queries
SHOW FULL PROCESSLIST;

-- Check table sizes
SELECT
    table_name,
    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb
FROM information_schema.TABLES
WHERE table_schema = 'cabinpi';

-- Analyze query performance
EXPLAIN SELECT * FROM measurements WHERE Date > NOW() - INTERVAL 1 DAY;
```

### Polling Performance

```bash
# Check time between readings
journalctl -u cabinpi-daemon | grep "Inserted measurement" | tail -20
```

## Test Coverage Goals

| Component | Target Coverage | Current |
|-----------|----------------|---------|
| Event Detector | >90% | TBD |
| Sensor Plugins | >80% | TBD |
| Output Plugins | >80% | TBD |
| Daemon Core | >85% | TBD |
| Overall | >80% | TBD |

## Troubleshooting Test Failures

### Import Errors

```bash
# Ensure cabinpi package is importable
cd /opt/cabinpython
export PYTHONPATH=/opt/cabinpython:$PYTHONPATH
pytest tests/
```

### Async Test Failures

```bash
# Install pytest-asyncio
pip install pytest-asyncio

# Verify pytest.ini has asyncio_mode = auto
```

### Mock Failures

```bash
# Ensure unittest.mock is available (Python 3.3+)
python3 -c "from unittest.mock import Mock; print('OK')"
```

## Best Practices

1. **Write tests first** (TDD) for new features
2. **Mock external dependencies** (hardware, network, database)
3. **Keep tests isolated** (no shared state between tests)
4. **Use descriptive names** (test name should describe behavior)
5. **Test edge cases** (null values, errors, timeouts)
6. **Clean up resources** (use fixtures and teardown)
7. **Run tests before commit** (use pre-commit hooks)
8. **Maintain test coverage** (aim for >80%)

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [pytest-cov](https://pytest-cov.readthedocs.io/)

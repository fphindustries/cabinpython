# SHT45 Temperature and Humidity Sensor Guide

Complete guide for using SHT45 high-accuracy temperature and humidity sensors with CabinPython v2.

## Overview

The SHT45 is a high-accuracy digital humidity and temperature sensor from Sensirion. It features improved power efficiency and accuracy compared to the SHT31, with ultra-low power consumption and excellent long-term stability.

### Key Features

- **High accuracy**: ±1.0% RH (25-75%), ±0.1°C (0-75°C)
- **Wide operating range**: 0-100% RH, -40 to +125°C
- **Ultra-low power**: 0.4µA average current, 80nA idle
- **Extended voltage range**: 1.08V to 3.6V
- **Fast measurement**: 1.7ms to 8.2ms depending on repeatability
- **I2C interface**: Standard address 0x44
- **CRC data validation**: Built-in data integrity checking
- **Small package**: Compact DFN housing

## Hardware Setup

### Components Needed

- SHT45 temperature/humidity sensor (or breakout board like Adafruit #5665)
- 4.7kΩ pull-up resistors for I2C (often included on breakout boards)
- Wires for connections
- Raspberry Pi 5 (or compatible)

### Wiring Diagram

```
SHT45 Pin Configuration:
    1 - SDA    (I2C data)
    2 - VDD    (Power: 1.08V - 3.6V, use 3.3V)
    3 - SCL    (I2C clock)
    4 - VSS    (Ground)

Raspberry Pi Connections:
    Pin 1  (3.3V)  -----> SHT45 VDD (Pin 2)
    Pin 6  (GND)   -----> SHT45 VSS (Pin 4)
    Pin 3  (SDA)   -----> SHT45 SDA (Pin 1)
    Pin 5  (SCL)   -----> SHT45 SCL (Pin 3)

    Note: 4.7kΩ pull-up resistors on SDA and SCL
    (usually included on Raspberry Pi and breakout boards)
```

**Important Notes:**
- SHT45 supports 1.08V to 3.6V supply (use 3.3V on Raspberry Pi)
- Pull-up resistors required on I2C lines (typically 4.7kΩ)
- Keep sensor away from heat sources for accurate readings
- Allow sensor to stabilize after power-on (< 1ms)

### Breakout Boards

Popular breakout boards:
- **Adafruit SHT45**: STEMMA QT/Qwiic connectors, built-in pull-ups
- **SparkFun SHT45**: Qwiic connectors, easy plug-and-play
- **Generic boards**: Usually include voltage regulation and pull-ups

## Raspberry Pi Configuration

### Enable I2C Interface

1. **Enable I2C via raspi-config**:
   ```bash
   sudo raspi-config
   # Navigate to: Interface Options → I2C → Enable
   ```

2. **Or edit boot configuration manually**:
   ```bash
   sudo nano /boot/firmware/config.txt
   ```

   Ensure this line exists:
   ```
   dtparam=i2c_arm=on
   ```

3. **Reboot**:
   ```bash
   sudo reboot
   ```

### Verify I2C Device Detection

```bash
# Install i2c-tools
sudo apt-get install i2c-tools

# Scan I2C bus (should show 0x44)
i2cdetect -y 1
```

Expected output:
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
40: -- -- -- -- 44 -- -- -- -- -- -- -- -- -- -- --
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
70: -- -- -- -- -- -- -- --
```

### Install Dependencies

```bash
sudo apt-get install python3-smbus i2c-tools
```

## CabinPython Configuration

### Basic Configuration

Edit `config.yaml`:

```yaml
plugins:
  sensors:
    sht45:
      enabled: true
      type: polling
      module: cabinpi.plugins.sensors.sht45
      interval: 300  # Read every 5 minutes
      config:
        i2c_bus: 1
        i2c_address: 0x44
        repeatability: "high"  # high, medium, or low
```

### Repeatability Settings

The SHT45 supports three measurement modes with different trade-offs:

| Repeatability | Measurement Time | Noise Level | Use Case |
|---------------|------------------|-------------|----------|
| High | 8.2 ms | Lowest | Best accuracy (default) |
| Medium | 4.3 ms | Medium | Balanced |
| Low | 1.7 ms | Higher | Fastest response |

**Configuration Examples:**

```yaml
# Maximum accuracy (default)
sht45_accurate:
  enabled: true
  type: polling
  module: cabinpi.plugins.sensors.sht45
  interval: 300
  config:
    i2c_bus: 1
    i2c_address: 0x44
    repeatability: "high"

# Fast response
sht45_fast:
  enabled: true
  type: polling
  module: cabinpi.plugins.sensors.sht45
  interval: 60
  config:
    i2c_bus: 1
    i2c_address: 0x44
    repeatability: "low"
```

### Configuration Options

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `i2c_bus` | No | 1 | I2C bus number (usually 1 on Raspberry Pi) |
| `i2c_address` | No | 0x44 | I2C device address |
| `repeatability` | No | "high" | Measurement mode: "high", "medium", or "low" |

## Measurement Specifications

### Temperature

- **Range**: -40°C to +125°C
- **Accuracy**: ±0.1°C (typical, 0-75°C)
- **Resolution**: 0.01°C (16-bit)
- **Response time**: < 10 seconds (τ63%)

### Humidity

- **Range**: 0-100% RH
- **Accuracy**: ±1.0% RH (typical, 25-75% RH)
- **Resolution**: 0.01% RH (16-bit)
- **Response time**: ~8 seconds (τ63%)
- **Hysteresis**: ±1% RH

### Long-term Drift

- **Temperature**: < 0.02°C/year
- **Humidity**: < 0.25% RH/year

## Data Format

### Sensor Reading

The SHT45 plugin returns:

```python
{
    "temp_c": 21.85,        # Temperature in Celsius
    "temp_f": 71.33,        # Temperature in Fahrenheit
    "humidity": 45.20       # Relative humidity (%)
}
```

### Database Storage

If using MariaDB output, add columns for SHT45 data:

```sql
-- For indoor environment monitoring
ALTER TABLE measurements
ADD COLUMN sht45_temp_c DECIMAL(5,2),
ADD COLUMN sht45_temp_f DECIMAL(5,2),
ADD COLUMN sht45_humidity DECIMAL(5,2);
```

Or reuse existing columns if replacing SHT31:

```sql
-- SHT45 is pin-compatible replacement for SHT31
-- Can use same columns: int_c, int_f, humidity
```

## Testing

### Manual Test

Test the sensor directly:

```bash
cd /opt/cabinpython
source env/bin/activate

python3 << 'EOF'
import asyncio
from cabinpi.plugins.sensors.sht45 import SHT45Sensor

async def test():
    sensor = SHT45Sensor("test_sht45")

    # Configure sensor
    config = {
        "i2c_bus": 1,
        "i2c_address": 0x44,
        "repeatability": "high"
    }

    success = await sensor.initialize(config)
    if not success:
        print("Initialization failed!")
        return

    # Take 5 readings
    for i in range(5):
        reading = await sensor.read()

        if reading.is_valid:
            m = reading.measurements
            print(f"Reading {i+1}:")
            print(f"  Temperature: {m['temp_c']:.2f}°C ({m['temp_f']:.2f}°F)")
            print(f"  Humidity: {m['humidity']:.2f}%")
        else:
            print(f"Reading {i+1} failed: {reading.error}")

        await asyncio.sleep(1)

    await sensor.shutdown()

asyncio.run(test())
EOF
```

### CRC Validation Test

The plugin automatically validates CRC checksums. To verify:

```bash
# Enable debug logging to see CRC validation
journalctl -u cabinpi-daemon -f | grep -i crc
```

Good readings will not show CRC warnings.

### Integration Test

Start the daemon and verify readings:

```bash
sudo systemctl start cabinpi-daemon
journalctl -u cabinpi-daemon -f | grep sht45
```

Check database:

```sql
SELECT Date, sht45_temp_c, sht45_temp_f, sht45_humidity
FROM measurements
WHERE Date > NOW() - INTERVAL 10 MINUTE
ORDER BY Date DESC;
```

## Event Detection

Configure environmental alerts:

```yaml
events:
  temp_high:
    sensor: sht45
    field: temp_f
    condition: above
    threshold: 85.0
    severity: warning
    notify: true
    message: "Indoor temperature high: {value}°F"

  temp_low:
    sensor: sht45
    field: temp_f
    condition: below
    threshold: 50.0
    severity: warning
    notify: true
    message: "Indoor temperature low: {value}°F"

  humidity_high:
    sensor: sht45
    field: humidity
    condition: above
    threshold: 70.0
    severity: warning
    notify: true
    message: "High humidity detected: {value}%"

  humidity_low:
    sensor: sht45
    field: humidity
    condition: below
    threshold: 30.0
    severity: info
    notify: false
    message: "Low humidity: {value}%"
```

## Troubleshooting

### No Device Detected

**Problem**: `i2cdetect -y 1` doesn't show device at 0x44

**Solutions**:

1. **Check wiring**:
   - Verify VDD connected to 3.3V
   - Verify VSS connected to GND
   - Verify SDA/SCL connections
   - Check for loose connections

2. **Check I2C enabled**:
   ```bash
   ls -l /dev/i2c-1
   # Should exist

   lsmod | grep i2c
   # Should show i2c modules
   ```

3. **Check power**:
   - Measure voltage between VDD and VSS (should be ~3.3V)
   - Ensure power supply can provide enough current

4. **Try different sensor**:
   - Sensor may be damaged
   - Test with known-good sensor

### CRC Errors

**Problem**: Readings fail with "CRC validation failed"

**Solutions**:

1. **Check I2C signal integrity**:
   - Shorten wires (keep under 30cm if possible)
   - Use shielded cable for longer runs
   - Verify pull-up resistors (4.7kΩ)

2. **Reduce electrical noise**:
   - Keep I2C wires away from power cables
   - Add 0.1µF capacitor across VDD and VSS at sensor
   - Use twisted pair for SDA/SCL

3. **Lower I2C speed** (if needed):
   ```bash
   # Edit /boot/firmware/config.txt
   dtparam=i2c_arm_baudrate=50000  # Slower than default 100kHz
   ```

### Incorrect Readings

**Problem**: Temperature or humidity readings seem wrong

**Solutions**:

1. **Allow stabilization time**:
   - Wait 5-10 seconds after power-on
   - Allow sensor to equilibrate with environment

2. **Check sensor placement**:
   - Keep away from heat sources (CPU, voltage regulators)
   - Ensure good airflow
   - Avoid direct sunlight
   - Don't enclose in sealed container

3. **Calibration check**:
   - Compare with known-good thermometer
   - For humidity, compare with calibrated hygrometer
   - SHT45 is factory calibrated, no user calibration needed

4. **Self-heating**:
   - Reduce polling frequency
   - Allow more time between readings
   - Use lower repeatability mode

### Humidity Always 0% or 100%

**Problem**: Humidity stuck at extreme values

**Solutions**:

1. **Sensor saturation**:
   - May have been exposed to excessive humidity
   - Perform reconditioning (see Datasheet section 4.3)

2. **Check for damage**:
   - Sensor membrane may be damaged
   - Replace sensor if necessary

### Permission Errors

**Problem**: Cannot access `/dev/i2c-1`

**Solutions**:

```bash
# Add user to i2c group
sudo usermod -a -G i2c ckent

# Set permissions (if needed)
sudo chmod a+rw /dev/i2c-1

# Reboot
sudo reboot
```

## SHT31 vs SHT45 Comparison

Upgrading from SHT31 to SHT45:

| Feature | SHT31 | SHT45 | Notes |
|---------|-------|-------|-------|
| **RH Accuracy** | ±2% | ±1% | SHT45 2x better |
| **Temp Accuracy** | ±0.3°C | ±0.1°C | SHT45 3x better |
| **Power (avg)** | 2.4µA | 0.4µA | SHT45 6x more efficient |
| **Voltage Range** | 2.4-5.5V | 1.08-3.6V | Different ranges |
| **I2C Address** | 0x44/0x45 | 0x44 | Compatible |
| **Package** | DFN | DFN | Pin-compatible |
| **Measurement Time** | 4-15ms | 1.7-8.2ms | SHT45 faster |
| **Price** | Lower | Higher | SHT45 ~2x cost |

**Migration Notes:**
- SHT45 is a drop-in replacement for SHT31 in most applications
- Change module name in config.yaml
- Update repeatability settings if desired
- Database schema can remain the same

## Advanced Usage

### Multiple SHT45 Sensors

The SHT45 has a fixed I2C address (0x44), making multiple sensors on the same bus challenging. Options:

1. **Use I2C multiplexer** (TCA9548A):
   ```
   Pi I2C ---- TCA9548A ---- Channel 0 ---- SHT45 #1
                        |-- Channel 1 ---- SHT45 #2
                        |-- Channel 2 ---- SHT45 #3
   ```

2. **Use separate I2C buses**:
   - Raspberry Pi supports multiple I2C buses
   - Configure additional buses in `/boot/firmware/config.txt`

3. **Mix with SHT31**:
   - SHT31 can use address 0x45
   - Use one SHT31 (0x45) and one SHT45 (0x44) on same bus

### Heater Function

The SHT45 has a built-in heater for:
- Removing condensation from sensor
- Testing sensor functionality
- Plausibility check of temperature readings

This feature is not currently exposed in the plugin but could be added if needed.

### Serial Number

Each SHT45 has a unique 32-bit serial number. The plugin uses this for health checks but doesn't expose it in measurements. Could be added for sensor tracking.

## Performance Considerations

### Polling Interval

- **Minimum**: 2 seconds (allow time for measurement + self-heating recovery)
- **Recommended**: 5-10 minutes for ambient monitoring
- **High-frequency**: 30-60 seconds if needed (watch for self-heating)

### Self-Heating

Continuous measurements can cause self-heating:
- Temperature rise: ~0.1°C per measurement in still air
- Allow recovery time between readings
- Use ventilation if polling frequently

### Power Consumption

The SHT45 is extremely power-efficient:
- Idle: 80nA (essentially zero)
- Measurement: Brief current spike
- Average: < 0.5µA at 1 reading/second

Perfect for battery-powered applications.

## Best Practices

1. **Placement**: Away from heat sources, good airflow
2. **Protection**: Use dust filter if in dirty environment
3. **Calibration**: Not required, factory calibrated
4. **Condensation**: Avoid if possible, use heater if occurs
5. **Handling**: Avoid touching sensor membrane
6. **Storage**: Store in dry location, 20-60% RH
7. **Validation**: Monitor CRC errors in logs
8. **Comparison**: Cross-check with other sensors periodically

## References

- [SHT45 Product Page](https://sensirion.com/products/catalog/SHT45) (Sensirion)
- [SHT4x Datasheet](https://sensirion.com/media/documents/33FD6951/6555C40E/Sensirion_Datasheet_SHT4x.pdf) (Sensirion)
- [Adafruit SHT45 Guide](https://www.adafruit.com/product/5665)
- [I2C Specification](https://www.nxp.com/docs/en/user-guide/UM10204.pdf) (NXP)

**Sources:**
- [Sensirion SHT45 Product Page](https://sensirion.com/products/catalog/SHT45)
- [SHT45 Datasheet](https://cdn.sparkfun.com/assets/9/7/7/a/d/SHT45-AD1B-R2_datasheet.pdf)
- [Adafruit SHT45 Sensor](https://www.adafruit.com/product/5665)
- [SHT4x Series Datasheet](https://sensirion.com/media/documents/33FD6951/6555C40E/Sensirion_Datasheet_SHT4x.pdf)

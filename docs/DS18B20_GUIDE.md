# DS18B20 Temperature Sensor Guide

Complete guide for using DS18B20 1-wire temperature sensors with CabinPython v2.

## Overview

The DS18B20 is a digital temperature sensor that communicates over the 1-wire protocol. It offers:

- **High precision**: ±0.5°C accuracy from -10°C to +85°C
- **Wide range**: -55°C to +125°C operating range
- **Simple wiring**: Only needs one data wire (plus power and ground)
- **Multiple sensors**: Many sensors can share the same 1-wire bus
- **Unique addressing**: Each sensor has a unique 64-bit serial number
- **Low cost**: Inexpensive and widely available

## Hardware Setup

### Components Needed

- DS18B20 temperature sensor(s)
- 4.7kΩ pull-up resistor
- Wires for connections
- Raspberry Pi 5 (or compatible)

### Wiring Diagram

```
DS18B20 Pin Configuration:
    1 - GND    (Black)
    2 - Data   (Yellow/White)
    3 - VCC    (Red)

Raspberry Pi Connections:
    Pin 1  (3.3V)  -----> DS18B20 VCC (Pin 3)
    Pin 6  (GND)   -----> DS18B20 GND (Pin 1)
    Pin 7  (GPIO4) -----> DS18B20 Data (Pin 2)
                          |
                        [4.7kΩ]
                          |
                         3.3V
```

**Pull-up Resistor**: Connect a 4.7kΩ resistor between the data line and VCC (3.3V).

### Multiple Sensors

Multiple DS18B20 sensors can share the same 1-wire bus:

```
Raspberry Pi GPIO4 ----+---- DS18B20 #1 Data
                       |
                       +---- DS18B20 #2 Data
                       |
                       +---- DS18B20 #3 Data
                       |
                     [4.7kΩ]
                       |
                      3.3V
```

All sensors share:
- Common VCC (3.3V)
- Common GND
- Common data line with one 4.7kΩ pull-up resistor

## Raspberry Pi Configuration

### Enable 1-Wire Interface

1. **Edit boot configuration**:
   ```bash
   sudo nano /boot/firmware/config.txt
   ```

2. **Add 1-wire overlay**:
   ```
   dtoverlay=w1-gpio
   ```

   Or specify a custom GPIO pin:
   ```
   dtoverlay=w1-gpio,gpiopin=4
   ```

3. **Save and reboot**:
   ```bash
   sudo reboot
   ```

### Load Kernel Modules

After reboot, verify modules are loaded:

```bash
# Check for 1-wire modules
lsmod | grep w1

# Should see:
# w1_therm
# w1_gpio
# wire
```

If not automatically loaded, load manually:

```bash
sudo modprobe w1-gpio
sudo modprobe w1-therm
```

To load on boot automatically:

```bash
echo "w1-gpio" | sudo tee -a /etc/modules
echo "w1-therm" | sudo tee -a /etc/modules
```

### Verify Sensor Detection

```bash
# List detected devices
ls -l /sys/bus/w1/devices/

# Should see entries like:
# 28-0000123456ab -> ../../../devices/w1_bus_master1/28-0000123456ab
# 28-0000123456cd -> ../../../devices/w1_bus_master1/28-0000123456cd

# Read sensor directly
cat /sys/bus/w1/devices/28-0000123456ab/w1_slave

# Output should be like:
# 5e 01 4b 46 7f ff 0c 10 d8 : crc=d8 YES
# 5e 01 4b 46 7f ff 0c 10 d8 t=21875
```

The `t=21875` means 21.875°C.

## CabinPython Configuration

### Basic Configuration

Edit `config.yaml`:

```yaml
plugins:
  sensors:
    ds18b20_outdoor:
      enabled: true
      type: polling
      module: cabinpi.plugins.sensors.ds18b20
      interval: 60  # Read every 60 seconds
      config:
        device_id: "28-0000123456ab"
        label: "outdoor"
```

### Auto-Detection

Let the plugin auto-detect the first DS18B20 sensor:

```yaml
ds18b20_auto:
  enabled: true
  type: polling
  module: cabinpi.plugins.sensors.ds18b20
  interval: 60
  config:
    label: "auto_detected"
    # device_id not specified = auto-detect
```

### Multiple Sensors

Configure multiple DS18B20 sensors with unique IDs:

```yaml
plugins:
  sensors:
    ds18b20_outdoor:
      enabled: true
      type: polling
      module: cabinpi.plugins.sensors.ds18b20
      interval: 60
      config:
        device_id: "28-0000123456ab"
        label: "outdoor"

    ds18b20_water_tank:
      enabled: true
      type: polling
      module: cabinpi.plugins.sensors.ds18b20
      interval: 120
      config:
        device_id: "28-0000123456cd"
        label: "water_tank"

    ds18b20_greenhouse:
      enabled: true
      type: polling
      module: cabinpi.plugins.sensors.ds18b20
      interval: 60
      config:
        device_id: "28-0000123456ef"
        label: "greenhouse"
```

### Configuration Options

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `device_id` | No | Auto-detect | 1-wire device ID (e.g., "28-0000123456ab") |
| `label` | No | "" | Human-readable label for sensor |
| `base_dir` | No | "/sys/bus/w1/devices" | Base directory for 1-wire devices |

## Finding Device IDs

### List All Sensors

```bash
ls /sys/bus/w1/devices/ | grep "^28-"
```

Output:
```
28-0000123456ab
28-0000123456cd
28-0000123456ef
```

### Identify Specific Sensors

Heat or cool each sensor one at a time and watch the readings:

```bash
# Monitor all DS18B20 sensors
watch -n 1 'for sensor in /sys/bus/w1/devices/28-*/w1_slave; do echo $sensor; cat $sensor | grep "t="; done'
```

Touch or heat a sensor - the temperature should change, identifying which device ID corresponds to which physical sensor.

### Label Sensors

Create a physical label map:

1. Read each sensor's ID
2. Heat/cool to identify location
3. Create labels in config matching physical locations
4. Document in a spreadsheet:

| Device ID | Label | Location | Notes |
|-----------|-------|----------|-------|
| 28-0000123456ab | outdoor | North wall | Shaded location |
| 28-0000123456cd | water_tank | Tank bottom | Waterproof probe |
| 28-0000123456ef | greenhouse | Center | High humidity area |

## Data Format

### Sensor Reading

The DS18B20 plugin returns:

```python
{
    "temp_c": 21.88,        # Temperature in Celsius
    "temp_f": 71.38,        # Temperature in Fahrenheit
    "device_id": "28-0000123456ab",
    "label": "outdoor"      # If configured
}
```

### Database Storage

If using MariaDB output, you may need to add columns for DS18B20 data:

```sql
ALTER TABLE measurements
ADD COLUMN ds18b20_outdoor_c DECIMAL(5,2),
ADD COLUMN ds18b20_outdoor_f DECIMAL(5,2);
```

Or create a generic approach with JSON:

```sql
ALTER TABLE measurements
ADD COLUMN extra_sensors JSON;
```

## Testing

### Manual Test

Test the sensor directly:

```bash
cd /opt/cabinpython
source env/bin/activate

python3 << 'EOF'
import asyncio
from cabinpi.plugins.sensors.ds18b20 import DS18B20Sensor

async def test():
    sensor = DS18B20Sensor("test_ds18b20")

    # Test with specific device ID
    config = {
        "device_id": "28-0000123456ab",
        "label": "test_sensor"
    }

    success = await sensor.initialize(config)
    if not success:
        print("Initialization failed!")
        return

    # Read temperature
    reading = await sensor.read()

    if reading.is_valid:
        print(f"Device ID: {reading.measurements['device_id']}")
        print(f"Label: {reading.measurements.get('label', 'N/A')}")
        print(f"Temperature: {reading.measurements['temp_c']:.2f}°C")
        print(f"Temperature: {reading.measurements['temp_f']:.2f}°F")
    else:
        print(f"Reading failed: {reading.error}")

    await sensor.shutdown()

asyncio.run(test())
EOF
```

### Auto-Detection Test

```bash
python3 << 'EOF'
import asyncio
from cabinpi.plugins.sensors.ds18b20 import DS18B20Sensor

async def test():
    sensor = DS18B20Sensor("auto_test")

    # Test auto-detection
    success = await sensor.initialize({})

    if success:
        reading = await sensor.read()
        if reading.is_valid:
            print(f"Auto-detected: {reading.measurements['device_id']}")
            print(f"Temperature: {reading.measurements['temp_c']:.2f}°C")
    else:
        print("Auto-detection failed")

    await sensor.shutdown()

asyncio.run(test())
EOF
```

### Integration Test

Start the daemon and verify readings:

```bash
sudo systemctl start cabinpi-daemon
journalctl -u cabinpi-daemon -f | grep ds18b20
```

Check database:

```sql
SELECT Date, temp_c, temp_f, device_id
FROM measurements
WHERE Date > NOW() - INTERVAL 10 MINUTE
ORDER BY Date DESC;
```

## Event Detection

Configure temperature alerts:

```yaml
events:
  ds18b20_outdoor_high:
    sensor: ds18b20_outdoor
    field: temp_f
    condition: above
    threshold: 100.0
    severity: warning
    notify: true
    message: "Outdoor temperature is {value}°F"

  ds18b20_outdoor_low:
    sensor: ds18b20_outdoor
    field: temp_f
    condition: below
    threshold: 32.0
    severity: warning
    notify: true
    message: "Freeze warning: outdoor temperature is {value}°F"

  ds18b20_water_high:
    sensor: ds18b20_water_tank
    field: temp_c
    condition: above
    threshold: 60.0
    severity: critical
    notify: true
    message: "Water tank overheating: {value}°C"
```

## Troubleshooting

### No Devices Detected

**Problem**: `ls /sys/bus/w1/devices/` shows no 28-* devices

**Solutions**:

1. **Check wiring**:
   - Verify VCC is connected to 3.3V (NOT 5V)
   - Verify GND connection
   - Verify data line on GPIO4
   - Check pull-up resistor (4.7kΩ) is present

2. **Check kernel modules**:
   ```bash
   sudo modprobe w1-gpio
   sudo modprobe w1-therm
   lsmod | grep w1
   ```

3. **Check boot configuration**:
   ```bash
   grep "dtoverlay=w1" /boot/firmware/config.txt
   ```

4. **Try different GPIO pin**:
   ```
   # In /boot/firmware/config.txt
   dtoverlay=w1-gpio,gpiopin=17
   ```

5. **Check sensor power**:
   - Measure voltage between VCC and GND (should be ~3.3V)
   - Try different power source if low

### CRC Errors

**Problem**: Readings show "CRC NO" or fail intermittently

**Solutions**:

1. **Shorten wires**: Long wires cause signal degradation
   - Keep under 3 meters for reliable operation
   - Use shielded cable for longer runs

2. **Check pull-up resistor**:
   - Use 4.7kΩ (not 10kΩ)
   - One resistor per bus (not per sensor)

3. **Reduce electrical noise**:
   - Keep 1-wire cable away from power cables
   - Add capacitor (0.1µF) across VCC and GND at sensor

4. **Slow down communication** (if needed):
   ```bash
   # Edit /boot/firmware/config.txt
   dtoverlay=w1-gpio,pullup=on
   ```

### Temperature Reading Errors

**Problem**: Temperature reads as 85°C or -127°C

**Solutions**:

- **85°C**: Sensor power-on default, not yet read. Wait 750ms after power-on.
- **-127°C**: Sensor not responding. Check connections.

**Add retry logic** (already in plugin):
```python
# Plugin automatically handles CRC failures
# Will return error if read fails
```

### Permission Errors

**Problem**: Cannot read `/sys/bus/w1/devices/...`

**Solutions**:

```bash
# Add user to gpio group
sudo usermod -a -G gpio ckent

# Set permissions
sudo chmod -R a+r /sys/bus/w1/devices/

# Reboot
sudo reboot
```

### Multiple Sensors Conflict

**Problem**: Multiple sensors, but only one detected

**Solutions**:

1. **Check each sensor individually**:
   - Connect one sensor at a time
   - Verify it's detected
   - Add next sensor

2. **Check for shorts**:
   - Ensure data wires don't touch
   - Verify each sensor has proper connections

3. **Power supply**:
   - Multiple sensors draw more current
   - May need stronger pull-up (3.3kΩ instead of 4.7kΩ)
   - Or use parasitic power mode with external power

## Advanced Usage

### Parasitic Power Mode

DS18B20 can operate with only 2 wires (data + ground):

```
Wiring:
    GND -----> DS18B20 Pin 1 (GND)
    GPIO4 ---> DS18B20 Pin 2 (Data) + Pin 3 (VCC tied together)
               |
             [4.7kΩ]
               |
              3.3V
```

Enable in config:
```
dtoverlay=w1-gpio,pullup=on
```

**Note**: Less reliable than 3-wire mode, avoid for critical applications.

### Waterproof Probes

For outdoor or submersible applications:

- Use DS18B20 in waterproof stainless steel probe
- Available with pre-attached cables
- Seal cable entry point
- Test in water before deployment

### High Precision Mode

DS18B20 supports different resolution settings (9-12 bits):

- 9-bit: 0.5°C resolution, 93.75ms conversion
- 10-bit: 0.25°C resolution, 187.5ms conversion
- 11-bit: 0.125°C resolution, 375ms conversion
- 12-bit: 0.0625°C resolution, 750ms conversion (default)

Current plugin uses default 12-bit mode for maximum precision.

## Performance Considerations

### Polling Interval

- **Minimum**: 1 second (750ms conversion time + overhead)
- **Recommended**: 30-60 seconds for most applications
- **Slow-changing**: 5-10 minutes for ambient temperature

### Multiple Sensors

- All sensors on same bus convert sequentially
- Each takes ~750ms
- 10 sensors = ~7.5 seconds total
- Adjust polling interval accordingly

### Resource Usage

- **CPU**: Minimal (file read operations)
- **Memory**: ~1KB per sensor
- **I/O**: Very low (one file read per poll)

## Best Practices

1. **Label everything**: Physical labels + config labels
2. **Test individually**: Verify each sensor before deployment
3. **Document locations**: Keep map of sensor positions
4. **Plan for failures**: Set up alerts for sensor health
5. **Regular checks**: Monitor CRC errors in logs
6. **Protect sensors**: Use appropriate enclosures
7. **Stable mounting**: Ensure good thermal contact
8. **Cable management**: Secure cables, avoid strain

## References

- [DS18B20 Datasheet](https://www.maximintegrated.com/en/products/sensors/DS18B20.html)
- [Raspberry Pi 1-Wire Documentation](https://www.raspberrypi.org/documentation/usage/gpio/one-wire.md)
- [1-Wire Protocol](https://en.wikipedia.org/wiki/1-Wire)

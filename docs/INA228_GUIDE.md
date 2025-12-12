# INA228 Power Monitor Guide

Complete guide for using INA228 high-precision power monitor sensors with CabinPython v2.

## Overview

The INA228 is an ultra-precise digital power monitor with a 20-bit delta-sigma ADC specifically designed for current-sensing applications. It measures shunt voltage, bus voltage, and internal temperature while calculating current, power, and energy.

### Key Features

- **High precision**: 20-bit ADC resolution
- **Wide voltage range**: Measures bus voltages from -0.3V to +85V
- **Current sensing**: Via external shunt resistor
- **Integrated temperature sensor**: ±1°C accuracy
- **Multiple measurements**: Current, voltage, power, energy, charge
- **I2C interface**: 16 configurable addresses (0x40-0x4F)
- **Low power**: Operates from 2.7V to 5.5V supply

## Hardware Setup

### Components Needed

- INA228 power monitor (or breakout board like Adafruit #5832)
- Shunt resistor (typically 0.01Ω to 0.1Ω, 1% tolerance or better)
- Wires for connections
- Raspberry Pi 5 (or compatible)

### Wiring Diagram

```
INA228 Connections:
    VIN+   -----> Positive power rail being monitored
    VIN-   -----> Connect to shunt resistor
    Shunt  -----> Other side of shunt to load
    GND    -----> System ground
    VCC    -----> 3.3V power
    SDA    -----> I2C SDA (GPIO 2, Pin 3)
    SCL    -----> I2C SCL (GPIO 3, Pin 5)

Example Battery Monitoring:
    Battery (+) ---[Shunt]--- VIN+ ---- VIN- --- Load
                               |         |
                             INA228   (connect both to INA228)
```

**Shunt Resistor Selection:**
- Lower resistance = higher current capacity, lower voltage drop
- Higher resistance = better precision at low currents
- Common values: 0.01Ω (100A max), 0.015Ω (67A max), 0.1Ω (10A max)
- Power rating must exceed: I²×R (use 2-3x safety margin)

### I2C Address Configuration

The INA228 has two address pins (A0 and A1) that allow configuring 16 different addresses:

| A1 | A0 | Address |
|----|----| --------|
| GND| GND| 0x40 (default) |
| GND| VS | 0x41 |
| GND| SDA| 0x42 |
| GND| SCL| 0x43 |
| VS | GND| 0x44 |
| VS | VS | 0x45 |
| VS | SDA| 0x46 |
| VS | SCL| 0x47 |
| SDA| GND| 0x48 |
| SDA| VS | 0x49 |
| SDA| SDA| 0x4A |
| SDA| SCL| 0x4B |
| SCL| GND| 0x4C |
| SCL| VS | 0x4D |
| SCL| SDA| 0x4E |
| SCL| SCL| 0x4F |

Multiple INA228 sensors can share the same I2C bus with different addresses.

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

# Scan I2C bus (should show 0x40 or your configured address)
i2cdetect -y 1
```

Expected output:
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
40: 40 -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
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
    ina228_battery:
      enabled: true
      type: polling
      module: cabinpi.plugins.sensors.ina228
      interval: 60  # Read every 60 seconds
      config:
        i2c_bus: 1
        i2c_address: 0x40
        shunt_resistor: 0.015    # 15 milliohm (Ω)
        max_current: 10.0        # 10A maximum expected
        label: "battery"
```

### Multiple Sensors

Monitor different power rails with multiple INA228 sensors:

```yaml
plugins:
  sensors:
    ina228_battery:
      enabled: true
      type: polling
      module: cabinpi.plugins.sensors.ina228
      interval: 60
      config:
        i2c_bus: 1
        i2c_address: 0x40
        shunt_resistor: 0.015
        max_current: 10.0
        label: "battery"

    ina228_solar:
      enabled: true
      type: polling
      module: cabinpi.plugins.sensors.ina228
      interval: 60
      config:
        i2c_bus: 1
        i2c_address: 0x41      # Different address
        shunt_resistor: 0.010
        max_current: 15.0
        label: "solar_panel"

    ina228_inverter:
      enabled: true
      type: polling
      module: cabinpi.plugins.sensors.ina228
      interval: 60
      config:
        i2c_bus: 1
        i2c_address: 0x42
        shunt_resistor: 0.020
        max_current: 8.0
        label: "inverter_dc"
```

### Configuration Options

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `i2c_bus` | No | 1 | I2C bus number (usually 1 on Raspberry Pi) |
| `i2c_address` | No | 0x40 | I2C device address (0x40-0x4F) |
| `shunt_resistor` | No | 0.015 | Shunt resistance in Ohms |
| `max_current` | No | 10.0 | Maximum expected current in Amps |
| `label` | No | "" | Human-readable label for sensor |

## Shunt Resistor Calculation

### Selecting Shunt Resistance

The shunt resistor determines your measurement range and resolution:

1. **Calculate voltage drop at max current**:
   ```
   V_shunt = I_max × R_shunt
   ```
   - Must be ≤ 163.84mV (full-scale range of INA228)
   - Recommended: Keep < 100mV to minimize power loss

2. **Calculate power dissipation**:
   ```
   P_shunt = I_max² × R_shunt
   ```
   - Choose resistor with power rating 2-3x this value

3. **Example for 10A max**:
   ```
   R_shunt = 0.015Ω (15 milliohm)
   V_drop = 10A × 0.015Ω = 0.15V = 150mV ✓ (under 163.84mV)
   P_dissipation = 10² × 0.015 = 1.5W
   Use: 3W or 5W resistor
   ```

### Common Shunt Values

| Shunt (Ω) | Max Current @ 100mV | Power Rating | Use Case |
|-----------|---------------------|--------------|----------|
| 0.001 | 100A | 10W+ | High current (inverters, motors) |
| 0.005 | 20A | 2W | Medium current (battery banks) |
| 0.010 | 10A | 1W | Low current (solar panels) |
| 0.015 | 6.7A | 1W | General purpose (default) |
| 0.020 | 5A | 0.5W | Low current monitoring |
| 0.100 | 1A | 0.1W | Precision low current |

## Data Format

### Sensor Reading

The INA228 plugin returns these measurements:

```python
{
    "current_a": 5.2341,          # Current in Amps
    "current_ma": 5234.10,        # Current in milliamps
    "bus_voltage_v": 12.456,      # Bus voltage in Volts
    "shunt_voltage_mv": 78.52,    # Shunt voltage in millivolts
    "power_w": 65.234,            # Power in Watts
    "power_mw": 65234.5,          # Power in milliwatts
    "die_temp_c": 32.5,           # Die temperature in Celsius
    "die_temp_f": 90.5,           # Die temperature in Fahrenheit
    "label": "battery"            # If configured
}
```

### Database Storage

Add columns to your measurements table for INA228 data:

```sql
-- Battery monitoring
ALTER TABLE measurements
ADD COLUMN battery_current_a DECIMAL(8,4),
ADD COLUMN battery_voltage_v DECIMAL(6,3),
ADD COLUMN battery_power_w DECIMAL(8,3),
ADD COLUMN battery_temp_c DECIMAL(5,2);

-- Solar panel monitoring
ALTER TABLE measurements
ADD COLUMN solar_current_a DECIMAL(8,4),
ADD COLUMN solar_voltage_v DECIMAL(6,3),
ADD COLUMN solar_power_w DECIMAL(8,3);
```

Or use a flexible JSON approach:

```sql
ALTER TABLE measurements
ADD COLUMN power_monitors JSON;
```

## Testing

### Manual Test

Test the sensor directly:

```bash
cd /opt/cabinpython
source env/bin/activate

python3 << 'EOF'
import asyncio
from cabinpi.plugins.sensors.ina228 import INA228Sensor

async def test():
    sensor = INA228Sensor("test_ina228")

    # Configure for your setup
    config = {
        "i2c_bus": 1,
        "i2c_address": 0x40,
        "shunt_resistor": 0.015,  # 15 milliohm
        "max_current": 10.0,      # 10A max
        "label": "battery"
    }

    success = await sensor.initialize(config)
    if not success:
        print("Initialization failed!")
        return

    # Read measurements
    reading = await sensor.read()

    if reading.is_valid:
        m = reading.measurements
        print(f"Label: {m.get('label', 'N/A')}")
        print(f"Current: {m['current_a']:.4f} A ({m['current_ma']:.2f} mA)")
        print(f"Bus Voltage: {m['bus_voltage_v']:.3f} V")
        print(f"Shunt Voltage: {m['shunt_voltage_mv']:.4f} mV")
        print(f"Power: {m['power_w']:.3f} W ({m['power_mw']:.2f} mW)")
        print(f"Temperature: {m['die_temp_c']:.2f}°C ({m['die_temp_f']:.2f}°F)")
    else:
        print(f"Reading failed: {reading.error}")

    await sensor.shutdown()

asyncio.run(test())
EOF
```

### Integration Test

Start the daemon and verify readings:

```bash
sudo systemctl start cabinpi-daemon
journalctl -u cabinpi-daemon -f | grep ina228
```

Check database:

```sql
SELECT Date, battery_current_a, battery_voltage_v, battery_power_w
FROM measurements
WHERE Date > NOW() - INTERVAL 10 MINUTE
ORDER BY Date DESC;
```

## Event Detection

Configure alerts for power monitoring:

```yaml
events:
  battery_high_current:
    sensor: ina228_battery
    field: current_a
    condition: above
    threshold: 8.0
    severity: warning
    notify: true
    message: "Battery current high: {value}A"

  battery_low_voltage:
    sensor: ina228_battery
    field: bus_voltage_v
    condition: below
    threshold: 11.5
    severity: critical
    notify: true
    message: "Battery voltage low: {value}V"

  battery_overpower:
    sensor: ina228_battery
    field: power_w
    condition: above
    threshold: 100.0
    severity: critical
    notify: true
    message: "Battery power excessive: {value}W"

  die_overtemp:
    sensor: ina228_battery
    field: die_temp_c
    condition: above
    threshold: 60.0
    severity: warning
    notify: true
    message: "INA228 die temperature high: {value}°C"
```

## Troubleshooting

### No Device Detected

**Problem**: `i2cdetect -y 1` doesn't show device at expected address

**Solutions**:

1. **Check wiring**:
   - Verify VCC connected to 3.3V (not 5V for some breakouts)
   - Verify GND connection
   - Verify SDA/SCL connections
   - Check address pins (A0, A1) configuration

2. **Check I2C enabled**:
   ```bash
   ls -l /dev/i2c-1
   # Should exist

   lsmod | grep i2c
   # Should show i2c modules
   ```

3. **Try different address**:
   - Check address pin configuration on breakout board
   - Try scanning: `i2cdetect -y 1`

### Incorrect Readings

**Problem**: Current or voltage readings are way off

**Solutions**:

1. **Verify shunt resistor value**:
   - Measure actual resistance with multimeter
   - Update `shunt_resistor` in config.yaml

2. **Check max_current setting**:
   - Should be set to maximum expected current
   - Affects current_lsb calculation
   - Update if your current range has changed

3. **Verify shunt connections**:
   - Shunt must be in series with current path
   - Check polarity (VIN+ should be positive side)

### High Die Temperature

**Problem**: Die temperature reading very high

**Solutions**:

1. **Check ambient temperature**:
   - Die temp will be above ambient due to I²R heating in shunt

2. **Reduce current or improve cooling**:
   - High currents cause more heating
   - Add heatsink if needed
   - Improve ventilation

3. **Check shunt power dissipation**:
   - Calculate: P = I² × R
   - May need larger/higher-power shunt resistor

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

### Noisy or Unstable Readings

**Problem**: Readings fluctuate excessively

**Solutions**:

1. **Check connections**:
   - Ensure solid connections
   - Use twisted pair for SDA/SCL if long wires
   - Keep I2C wires away from power cables

2. **Add filtering** (hardware):
   - 0.1µF capacitor across VCC and GND at INA228
   - Shielded cable for long runs

3. **Adjust averaging** (done automatically in driver):
   - Plugin uses 1024-sample averaging for stable readings

## Advanced Usage

### Energy and Charge Measurement

The INA228 includes registers for accumulated energy and charge. Future versions of the plugin may expose these:

- **Energy Register**: Accumulated energy in Joules
- **Charge Register**: Accumulated charge in Coulombs

Useful for:
- Battery state-of-charge (SOC) estimation
- Energy consumption tracking
- Coulomb counting for battery management

### Alert Pin Configuration

The INA228 has a hardware alert pin that can be configured for:
- Over-current detection
- Under-voltage detection
- Over-power detection
- Temperature limits

This could be integrated with Raspberry Pi GPIO for immediate hardware alerts.

### Multiple Conversion Times

The plugin uses 1.1ms conversion time with 1024 samples averaging. Alternative configurations:

| Mode | Conversion | Averaging | Update Rate | Noise |
|------|------------|-----------|-------------|-------|
| Fast | 50µs | 1x | ~200 Hz | High |
| Normal | 1.1ms | 64x | ~14 Hz | Medium |
| Precise | 4.1ms | 1024x | ~0.24 Hz | Low (default) |

## Performance Considerations

### Polling Interval

- **Minimum**: 1 second (allow time for averaging)
- **Recommended**: 30-60 seconds for most applications
- **Fast monitoring**: 5-10 seconds for dynamic loads
- **Energy tracking**: 1-5 minutes for long-term stats

### Multiple Sensors

- All sensors on same I2C bus are read sequentially
- Each read takes ~100ms (with averaging)
- 10 sensors = ~1 second total read time
- Adjust polling interval accordingly

### Resource Usage

- **CPU**: Minimal (I2C reads via kernel)
- **Memory**: ~2KB per sensor instance
- **I/O**: Very low (one I2C transaction per poll)

## Best Practices

1. **Shunt selection**: Match to expected current range
2. **Power rating**: Use 2-3x safety margin on shunt
3. **Calibration**: Verify with known load/current
4. **Labeling**: Use descriptive labels in config
5. **Monitoring**: Set up alerts for abnormal conditions
6. **Documentation**: Keep record of shunt values and locations
7. **Thermal management**: Monitor die temperature
8. **Wiring**: Keep shunt leads short and heavy gauge

## References

- [INA228 Datasheet](https://www.ti.com/lit/ds/symlink/ina228.pdf) (Texas Instruments)
- [Adafruit INA228 Guide](https://learn.adafruit.com/adafruit-ina228-i2c-power-monitor)
- [I2C Protocol Specification](https://www.nxp.com/docs/en/user-guide/UM10204.pdf)

**Sources:**
- [INA228 Datasheet](https://download.mikroe.com/documents/datasheets/INA228%20Datasheet.pdf)
- [Adafruit INA228 I2C Power Monitor](https://cdn-learn.adafruit.com/downloads/pdf/adafruit-ina228-i2c-power-monitor.pdf)
- [TI INA228 Product Page](https://www.ti.com/product/INA228)
- [Adafruit INA228 Learning Guide](https://learn.adafruit.com/adafruit-ina228-i2c-power-monitor?view=all)

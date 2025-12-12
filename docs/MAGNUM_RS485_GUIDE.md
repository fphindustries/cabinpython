# Magnum RS-485 Network Driver Guide

Complete guide for using the Magnum RS-485 network driver with CabinPython v2 for full inverter monitoring and control.

## Overview

The Magnum RS-485 driver implements the native Magnum Energy networking protocol, providing direct access to Magnum inverter/char

gers and network devices. Unlike the pymagnum-based driver (which uses the remote panel RS-232 interface), this driver connects directly to the RS-485 network bus.

### Key Features

- **Full network protocol**: Native RS-485 Magnum network communication
- **Multiple device support**: Read from inverter, AGS, BMK, and other network devices
- **Inverter control**: Turn inverter and charger on/off programmatically
- **Real-time monitoring**: 100ms update rate from inverter
- **Comprehensive data**: Status, faults, voltages, currents, temperatures
- **Model detection**: Automatic inverter model identification
- **Extended packet support**: Works with MS rev 4.0+ (21-byte packets)

### Advantages Over RS-232 Driver

| Feature | RS-232 (pymagnum) | RS-485 (native) |
|---------|-------------------|-----------------|
| Connection | Remote panel port | Network bus |
| Protocol | Custom pymagnum | Official Magnum protocol |
| Control capability | Read-only | Read + control (on/off) |
| Update rate | Polled (~5 sec) | Real-time (100ms) |
| Network devices | Inverter only | All devices (AGS, BMK, etc) |
| Packet format | Parsed by library | Direct protocol access |
| Model support | All | All (with auto-detect) |

## Hardware Setup

### Components Needed

- **USB RS-485 converter** (e.g., FTDI USB-RS485, CH340-based)
- **Magnum inverter/charger** with RJ-11 network port
- **RJ-11 cable** (or custom wiring)
- **Raspberry Pi 5** (or compatible)

### Wiring Diagram

```
Magnum RJ-11 Network Port (looking at jack, tab down):
    Pin 1 (top)    = B (RS-485 differential pair)
    Pin 2          = +14V (DO NOT CONNECT - not needed)
    Pin 3          = GND (connect to converter GND)
    Pin 4 (bottom) = A (RS-485 differential pair)

USB RS-485 Converter:
    A  ----> Magnum Pin 4 (A)
    B  ----> Magnum Pin 1 (B)
    GND ----> Magnum Pin 3 (GND)

    Note: DO NOT connect Pin 2 (+14V) - the USB converter
    provides its own power via USB.
```

**Important Notes:**
- RS-485 uses differential signaling (A and B pins)
- Polarity matters! Swap A/B if communication fails
- GND connection is required for proper signal reference
- Do NOT connect the +14V pin (Pin 2) to the USB converter
- Maximum cable length: ~1200 meters (4000 feet) for RS-485
- Recommended cable: Cat5/Cat6 twisted pair

### USB RS-485 Converter Options

**Recommended:**
- FTDI-based USB-RS485 converters (most reliable)
- CH340/CH341-based USB-RS485 (budget option)
- Industrial USB-RS485 isolators (for electrical isolation)

**Features to look for:**
- Automatic TX/RX direction control (no manual DE/RE pin)
- 3.3V or 5V tolerant
- Surge protection
- ESD protection

### RJ-11 Connector

If using an RJ-11 cable:
1. Cut one end off the cable
2. Strip and identify the wires (usually red, green, black, yellow)
3. Use a multimeter to determine which wire connects to which pin
4. Common color codes:
   - Pin 1 (B): Yellow or Green
   - Pin 2 (+14V): Red
   - Pin 3 (GND): Black
   - Pin 4 (A): Green or Yellow

## Raspberry Pi Configuration

### Install Dependencies

```bash
sudo apt-get update
sudo apt-get install python3-serial
```

### Identify USB RS-485 Device

```bash
# Before plugging in converter
ls /dev/ttyUSB*

# After plugging in converter
ls /dev/ttyUSB*
# Should see new device like /dev/ttyUSB0

# Get persistent device ID
ls -l /dev/serial/by-id/
# Use this path in config for stability across reboots
```

### Test Serial Port

```bash
# Check port exists and has correct permissions
ls -l /dev/ttyUSB0

# Add user to dialout group for serial access
sudo usermod -a -G dialout $USER

# Reboot to apply group changes
sudo reboot
```

## CabinPython Configuration

### Basic Configuration

Edit `config.yaml`:

```yaml
plugins:
  sensors:
    magnum_rs485:
      enabled: true
      type: polling
      module: cabinpi.plugins.sensors.magnum_rs485
      interval: 5  # Read every 5 seconds
      config:
        port: /dev/ttyUSB0
        baudrate: 19200
        timeout: 0.5
        remote_revision: 10  # 1.0
```

### Using Persistent Device Path

```yaml
magnum_rs485:
  enabled: true
  type: polling
  module: cabinpi.plugins.sensors.magnum_rs485
  interval: 5
  config:
    port: /dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A12345-if00-port0
    baudrate: 19200
    timeout: 0.5
```

### Configuration Options

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `port` | Yes | /dev/ttyUSB0 | Serial port device path |
| `baudrate` | No | 19200 | Baud rate (MUST be 19200 for Magnum) |
| `timeout` | No | 0.5 | Read timeout in seconds |
| `remote_revision` | No | 10 | Remote firmware version (10 = 1.0) |

**Important:** The baudrate MUST be 19200 for Magnum network protocol.

## Protocol Details

### Communication Timing

```
|<------ 100ms ------>|<------ 100ms ------>|

INVERTER ----[16-21 bytes]----
           |
           | 10ms delay
           |
         REMOTE ----[16 bytes]----
                                  |
                                  | 90ms idle
```

- Inverter (master) transmits every 100ms
- Remote (slave) responds 10ms after receiving inverter packet
- This driver acts as a passive listener and occasional responder

### Packet Format

**Inverter Packet (16 bytes minimum):**

| Byte | Name | Description | Units |
|------|------|-------------|-------|
| 0 | Status | Operating mode | See status codes |
| 1 | Fault | Fault code | See fault codes |
| 2-3 | DC Volts | Battery voltage | 0.1V per count |
| 4-5 | DC Amps | Battery current | 1A per count |
| 6 | AC Volts Out | Output voltage | 1V RMS |
| 7 | AC Volts In | Input voltage | 1V peak |
| 8 | Inverter LED | LED status | 0=off, 1=on |
| 9 | Charger LED | LED status | 0=off, 1=on |
| 10 | Revision | Firmware version | x.y format |
| 11 | Battery Temp | Temperature | 1°C |
| 12 | Xformer Temp | Temperature | 1°C |
| 13 | FET Temp | Temperature | 1°C |
| 14 | Model | Model code | See model table |
| 15+ | Extended | MS 4.0+ only | Stack, amps, Hz |

**Extended Bytes (MS rev 4.0+, bytes 15-20):**

| Byte | Name | Description |
|------|------|-------------|
| 15 | Stack Mode | 0=standalone, 1=parallel master, etc |
| 16 | AC Input Amps | 1A per count |
| 17 | AC Output Amps | 1A per count |
| 18-19 | AC Hz | Frequency, 0.1Hz per count |
| 20 | Not used | Reserved |

## Data Format

### Sensor Reading

The driver returns these measurements:

```python
{
    # Status
    "status_code": 64,                    # Raw status byte
    "status_name": "INVERT_MODE",         # Human-readable status
    "fault_code": 0,                      # Raw fault byte
    "fault_name": "NO_FAULT",             # Human-readable fault

    # Electrical measurements
    "dc_volts": 12.6,                     # Battery voltage
    "dc_amps": 15,                        # Battery current (charging or discharging)
    "ac_volts_out": 120,                  # AC output voltage (RMS)
    "ac_volts_in": 120,                   # AC input voltage (peak)

    # LED status
    "inverter_led": 1,                    # 1=on, 0=off
    "charger_led": 0,                     # 1=on, 0=off

    # System information
    "inverter_revision": "4.0",           # Firmware version
    "model_code": 107,                    # Raw model code
    "model_name": "MS4024PAE",            # Model name

    # Temperatures (°C and °F)
    "battery_temp_c": 25,
    "battery_temp_f": 77,
    "transformer_temp_c": 35,
    "transformer_temp_f": 95,
    "fet_temp_c": 40,
    "fet_temp_f": 104,

    # Extended (MS 4.0+ only)
    "stack_mode": 0,                      # 0=standalone
    "ac_input_amps": 15,
    "ac_output_amps": 8,
    "ac_hz": 60.0
}
```

### Status Codes

| Code | Name | Description |
|------|------|-------------|
| 0x00 | CHARGER_STANDBY | AC in, charging disabled |
| 0x01 | EQ_MODE | Equalizing with AC |
| 0x02 | FLOAT_MODE | Float charging with AC |
| 0x04 | ABSORB_MODE | Absorb charging with AC |
| 0x08 | BULK_MODE | Bulk charging with AC |
| 0x09 | BAT_SAVER_MODE | Charge mode, no current (battery full) |
| 0x10 | CHARGE_MODE | Charge mode, no AC |
| 0x20 | OFF | Inverter off, charger off |
| 0x40 | INVERT_MODE | Inverter on |
| 0x50 | INVERTER_STANDBY | PAE mode (MS 4.0+) |
| 0x80 | SEARCH_MODE | Searching for load |

### Fault Codes

| Code | Name | Description |
|------|------|-------------|
| 0x00 | NO_FAULT | Normal operation |
| 0x01 | STUCK_RELAY | Relay fault |
| 0x02 | DC_OVERLOAD | DC bridge overload |
| 0x03 | AC_OVERLOAD | AC output overload |
| 0x04 | DEAD_BAT | Charging dead battery |
| 0x05 | BACKFEED | AC backfeed detected |
| 0x08 | LOW_BAT | Low battery cutout |
| 0x09 | HIGH_BAT | High battery cutout |
| 0x0A | HIGH_AC_VOLTS | High AC output voltage |
| 0x10 | BAD_BRIDGE | Internal fault 1 (bad FET bridge) |
| 0x12 | NTC_FAULT | Internal fault 2 (FETs too hot) |
| 0x13 | FET_OVERLOAD | FET overload (temp rise too fast) |
| 0x20 | OVERTEMP | Overtemp shutdown |
| 0x21 | RELAY_FAULT | Transfer relay not closed |
| 0x80 | CHARGER_FAULT | Bridge fault in charge mode |
| 0x81 | HI_BAT_TEMP | High battery temperature |
| 0x90 | OPEN_SELCO_TCO | Open transformer TCO |
| 0x91 | CB3_OPEN_FAULT | Open input 30A breaker |

### Model Codes

| Code | Model |
|------|-------|
| 0x23 | MS2012 |
| 0x28 | MS2012E |
| 0x2D | MS2812 |
| 0x5A | MS4124E |
| 0x5B | MS2024 |
| 0x69 | MS4024 |
| 0x6A | MS4024AE |
| 0x6B | MS4024PAE |
| 0x6F | MS4448AE |
| 0x73 | MS4448PAE |
| ... | See full list in driver |

## Inverter Control

### Control Methods

The driver provides methods to control the inverter:

```python
# Toggle inverter on/off
await sensor.toggle_inverter()

# Turn inverter on (when currently off)
await sensor.turn_inverter_on()

# Turn inverter off (when currently on)
await sensor.turn_inverter_off()

# Toggle charger on/off (when AC is present)
await sensor.toggle_charger()
```

### How Control Works

1. Control commands are **toggle-based** (not absolute on/off)
2. Commands are sent as part of the next remote packet
3. The driver queues commands and sends them on the next `read()` call
4. Commands take effect within 100ms (one inverter cycle)

**Important:** The inverter uses toggle commands, so you need to know the current state before sending a command. Always read the status first.

### Example Control Sequence

```python
# Read current status
reading = await sensor.read()
status = reading.measurements['status_code']

# Check if inverter is off
if status == 0x20:  # OFF
    # Turn on
    await sensor.turn_inverter_on()
    print("Inverter turned on")
elif status == 0x40:  # INVERT_MODE
    # Already on
    print("Inverter already on")
```

### Control Limitations

- **Toggling only**: Cannot set absolute on/off state
- **No feedback**: Command success not directly confirmed (check status on next read)
- **AC required for charger**: Charger toggle only works when AC is present
- **Remote priority**: Physical remote panel commands take precedence

## Database Storage

### Recommended Schema

Add columns for Magnum RS-485 data:

```sql
ALTER TABLE measurements
-- Status and identification
ADD COLUMN inv_status VARCHAR(50),
ADD COLUMN inv_fault VARCHAR(50),
ADD COLUMN inv_model VARCHAR(20),

-- Electrical
ADD COLUMN inv_dc_volts DECIMAL(5,2),
ADD COLUMN inv_dc_amps DECIMAL(6,2),
ADD COLUMN inv_ac_volts_out INT,
ADD COLUMN inv_ac_volts_in INT,
ADD COLUMN inv_ac_input_amps INT,
ADD COLUMN inv_ac_output_amps INT,
ADD COLUMN inv_ac_hz DECIMAL(4,1),

-- Temperatures
ADD COLUMN inv_battery_temp_c INT,
ADD COLUMN inv_transformer_temp_c INT,
ADD COLUMN inv_fet_temp_c INT,

-- Status
ADD COLUMN inv_inverter_led BOOLEAN,
ADD COLUMN inv_charger_led BOOLEAN;
```

## Event Detection

Configure alerts for inverter conditions:

```yaml
events:
  inverter_fault:
    sensor: magnum_rs485
    field: fault_code
    condition: above
    threshold: 0
    severity: critical
    notify: true
    message: "Inverter fault: {fault_name}"

  inverter_low_battery:
    sensor: magnum_rs485
    field: dc_volts
    condition: below
    threshold: 11.5
    severity: warning
    notify: true
    message: "Battery voltage low: {value}V"

  inverter_overtemp:
    sensor: magnum_rs485
    field: fet_temp_c
    condition: above
    threshold: 70
    severity: warning
    notify: true
    message: "Inverter FET temperature high: {value}°C"

  charger_active:
    sensor: magnum_rs485
    field: status_name
    condition: equals
    threshold: "BULK_MODE"
    severity: info
    notify: false
    message: "Charger entered bulk mode"
```

## Testing

### Manual Test

```bash
cd /opt/cabinpython
source env/bin/activate

python3 << 'EOF'
import asyncio
from cabinpi.plugins.sensors.magnum_rs485 import MagnumRS485Sensor

async def test():
    sensor = MagnumRS485Sensor("test_magnum")

    config = {
        "port": "/dev/ttyUSB0",
        "baudrate": 19200,
        "timeout": 0.5
    }

    success = await sensor.initialize(config)
    if not success:
        print("Initialization failed!")
        return

    # Read 5 times
    for i in range(5):
        reading = await sensor.read()

        if reading.is_valid:
            m = reading.measurements
            print(f"\nReading {i+1}:")
            print(f"  Status: {m.get('status_name')} ({m.get('status_code'):02X})")
            print(f"  Fault: {m.get('fault_name')} ({m.get('fault_code'):02X})")
            print(f"  Model: {m.get('model_name')}")
            print(f"  DC: {m.get('dc_volts')}V @ {m.get('dc_amps')}A")
            print(f"  AC Out: {m.get('ac_volts_out')}V")
            print(f"  Temps: Bat={m.get('battery_temp_c')}°C, FET={m.get('fet_temp_c')}°C")
        else:
            print(f"Reading {i+1} failed: {reading.error}")

        await asyncio.sleep(1)

    await sensor.shutdown()

asyncio.run(test())
EOF
```

### Control Test

```bash
python3 << 'EOF'
import asyncio
from cabinpi.plugins.sensors.magnum_rs485 import MagnumRS485Sensor

async def test_control():
    sensor = MagnumRS485Sensor("test_control")

    await sensor.initialize({"port": "/dev/ttyUSB0"})

    # Read current status
    reading = await sensor.read()
    print(f"Current status: {reading.measurements.get('status_name')}")

    # Toggle inverter
    print("Toggling inverter...")
    await sensor.toggle_inverter()

    # Wait and read again
    await asyncio.sleep(2)
    reading = await sensor.read()
    print(f"New status: {reading.measurements.get('status_name')}")

    await sensor.shutdown()

asyncio.run(test_control())
EOF
```

## Troubleshooting

### No Data Received

**Problem**: Driver times out waiting for inverter packets

**Solutions**:

1. **Check wiring**:
   ```bash
   # Verify A and B are connected correctly
   # Try swapping A and B if no data
   ```

2. **Check serial port**:
   ```bash
   # Verify device exists
   ls -l /dev/ttyUSB0

   # Test with minicom
   sudo minicom -D /dev/ttyUSB0 -b 19200
   # Should see binary data every 100ms
   ```

3. **Check permissions**:
   ```bash
   # Add user to dialout group
   sudo usermod -a -G dialout $USER
   sudo reboot
   ```

4. **Verify baudrate**:
   - MUST be 19200 bps
   - Check config.yaml setting

### Garbled Data

**Problem**: Receiving data but it's corrupted

**Solutions**:

1. **Swap RS-485 polarity**:
   - Try swapping A and B wires
   - RS-485 is polarity-sensitive

2. **Check GND connection**:
   - Ensure Pin 3 (GND) is connected
   - Required for proper signal reference

3. **Cable length**:
   - Keep under 1200 meters
   - Use shielded twisted pair for long runs

4. **Electrical noise**:
   - Keep RS-485 cable away from power cables
   - Use isolated USB converter if near noisy equipment

### Control Commands Not Working

**Problem**: Toggle commands don't affect inverter

**Solutions**:

1. **Check remote revision**:
   - Must be >= 1.0 (10 in config)
   - Inverter may ignore commands from old revisions

2. **Physical remote connected**:
   - Physical remote panel takes priority
   - Disconnect remote panel for testing

3. **Verify command timing**:
   - Commands sent on next read() call
   - Allow 100ms for command to take effect

4. **Check inverter mode**:
   - Some commands only work in specific modes
   - e.g., charger toggle only works when AC present

### Packet Size Mismatch

**Problem**: Receiving 21 bytes but expecting 16

**Solution**:

This is normal for MS rev 4.0+ inverters. The driver automatically handles both 16-byte and 21-byte packets. No action needed.

## Advanced Usage

### Reading Multiple Network Devices

The current driver focuses on the inverter, but the protocol supports multiple devices:

- **ME-AGS**: Auto Generator Start controller (header 0xA1)
- **ME-BMK**: Battery Monitor Kit (header 0x81)
- **ME-RTR**: Router (header 0x91)

Future versions could decode these devices as well.

### Acting as Full Remote Panel

The driver currently sends minimal remote packets. To act as a full remote panel:

1. Implement all remote packet bytes (battery settings, shore amps, etc.)
2. Send packets on every inverter cycle
3. Handle AGS/BMK extended packets (footers 0xA0-0xA4, 0x80)

### Stacked Inverters

For parallel or series stacked inverters:
- `stack_mode` field indicates master/slave configuration
- Both inverters transmit on the network
- May need packet filtering by source

## Performance Considerations

### Polling Interval

- **Minimum**: 1 second (allow time for packet reception)
- **Recommended**: 5 seconds (responsive control + low overhead)
- **Fast monitoring**: 1-2 seconds for critical applications
- **Normal monitoring**: 30-60 seconds for logging only

### Resource Usage

- **CPU**: Very low (serial I/O is kernel-based)
- **Memory**: ~5KB per sensor instance
- **Serial bandwidth**: ~2000 bytes/second at 19200 baud
- **Network bandwidth**: Negligible (local serial only)

## Best Practices

1. **Use persistent device path**: `/dev/serial/by-id/...` instead of `/dev/ttyUSB0`
2. **Start with read-only**: Test thoroughly before enabling control
3. **Monitor fault codes**: Set up event detection for all faults
4. **Log status changes**: Track mode transitions for troubleshooting
5. **Backup configuration**: Keep inverter settings documented
6. **Test control commands**: Verify toggle behavior in safe environment
7. **Use fast polling for control**: 5 second interval for responsive control
8. **Coordinate with remote**: Only one control source should be active

## Protocol Reference

Based on **Magnum Networking Communications Protocol (2009-10-15)**

- Copyright 2003-2009 Magnum Energy
- Permission required to use this protocol
- Protocol is proprietary to Magnum Energy

## Comparison: RS-232 vs RS-485

### When to Use RS-232 Driver (pymagnum)

- Simple monitoring (no control needed)
- Existing remote panel connection available
- Don't want to modify wiring
- Prefer higher-level abstraction (pymagnum library)

### When to Use RS-485 Driver (this driver)

- Need inverter control capability
- Want access to all network devices (AGS, BMK)
- Need faster update rates (< 5 seconds)
- Want raw protocol access
- Building automation system
- Multiple inverters (stacked systems)

## References

- Magnum Energy Networking Communications Protocol (2009-10-15)
- [PySerial Documentation](https://pyserial.readthedocs.io/)
- [RS-485 Specification](https://en.wikipedia.org/wiki/RS-485)
- [Magnum Energy Website](https://www.magnum-dimensions.com/)

**Sources:**
- [PySerial API Documentation](https://pyserial.readthedocs.io/en/latest/pyserial_api.html)
- [PySerial RS-485 Support](https://github.com/pyserial/pyserial/blob/master/serial/rs485.py)
- [RS-485 with Raspberry Pi](https://forums.raspberrypi.com/viewtopic.php?t=234122)
- [Python RS-485 Communication](https://gist.github.com/remceTkedaR/ea180f43e718efe9236cc8dc0b4a064b)
- [RS-485 Serial Communication](https://circuitdigest.com/microcontroller-projects/rs485-serial-communication-between-arduino-and-raspberry-pi)

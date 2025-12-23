# CabinPython Sensor Testing Guide

This guide explains how to test the new sensors (SHT45, INA228, DS18B20) without a database.

## Prerequisites

### 1. Install Dependencies

```bash
cd /home/ckent/repos/cabinpython

# Install I2C library for SHT45 and INA228
pip install smbus2

# Or if using system Python
sudo apt-get install python3-smbus

# Enable I2C interface
sudo raspi-config
# Navigate to: Interface Options → I2C → Enable
sudo reboot
```

### 2. Enable 1-Wire for DS18B20

```bash
# Edit boot config
sudo nano /boot/firmware/config.txt

# Add this line:
dtoverlay=w1-gpio

# Save and reboot
sudo reboot
```

### 3. Verify Hardware

```bash
# Check I2C devices (should see 0x40 for INA228, 0x44 for SHT45)
i2cdetect -y 1

# Check DS18B20 (should see device starting with "28-")
ls /sys/bus/w1/devices/28-*
```

## Quick Start

```bash
# Method 1: Test individual sensors
python3 test_sensors.py --all

# Method 2: Test with daemon and file output
python3 daemon.py --config config_test.yaml

# Monitor output in another terminal
tail -f /tmp/sensor_readings.jsonl | jq .
```

## See full guide in file for detailed instructions

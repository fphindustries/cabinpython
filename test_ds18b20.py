#!/opt/cabinpython/env/bin/python3

"""
Test script for reading DS18B20 temperature sensor via 1-wire bus.
The DS18B20 is accessed through the Linux w1 (1-wire) kernel interface.
"""

import time
import glob
import os

# Base directory for 1-wire devices on Linux
W1_BASE_DIR = '/sys/bus/w1/devices/'


class DS18B20:
    """Driver for DS18B20 temperature sensor via 1-wire."""

    def __init__(self, device_id=None):
        """
        Initialize the DS18B20 sensor.

        Args:
            device_id: Optional specific device ID (e.g., '28-xxxxxxxxxxxx').
                      If None, will use the first DS18B20 found.
        """
        if device_id:
            self.device_path = os.path.join(W1_BASE_DIR, device_id)
        else:
            # Find first DS18B20 device (starts with 28-)
            devices = glob.glob(W1_BASE_DIR + '28-*')
            if not devices:
                raise RuntimeError("No DS18B20 sensor found. Make sure 1-wire is enabled.")
            self.device_path = devices[0]
            device_id = os.path.basename(self.device_path)

        self.device_id = device_id
        self.device_file = os.path.join(self.device_path, 'w1_slave')

        if not os.path.exists(self.device_file):
            raise RuntimeError(f"Device file not found: {self.device_file}")

        print(f"Found DS18B20 sensor: {self.device_id}")

    def _read_raw(self):
        """Read raw data from the sensor."""
        try:
            with open(self.device_file, 'r') as f:
                lines = f.readlines()
            return lines
        except Exception as e:
            raise RuntimeError(f"Error reading sensor: {e}")

    def get_temperature_c(self):
        """
        Get temperature in Celsius.

        Returns:
            float: Temperature in Celsius, or None if read failed.
        """
        max_retries = 3
        retry_delay = 0.1

        for attempt in range(max_retries):
            lines = self._read_raw()

            # Check if the CRC is valid (line 1 ends with 'YES')
            if len(lines) >= 2 and lines[0].strip().endswith('YES'):
                # Parse temperature from second line
                # Format: "xx xx xx xx xx xx xx xx xx : crc=xx YES"
                # Second line: "xx xx xx xx xx xx xx xx xx t=xxxxx"
                temp_pos = lines[1].find('t=')
                if temp_pos != -1:
                    temp_string = lines[1][temp_pos + 2:].strip()
                    temp_c = float(temp_string) / 1000.0
                    return temp_c

            # If CRC check failed or data invalid, retry
            if attempt < max_retries - 1:
                time.sleep(retry_delay)

        return None

    def get_temperature_f(self):
        """
        Get temperature in Fahrenheit.

        Returns:
            float: Temperature in Fahrenheit, or None if read failed.
        """
        temp_c = self.get_temperature_c()
        if temp_c is not None:
            return (temp_c * 9/5) + 32
        return None

    def get_raw_data(self):
        """
        Get raw sensor data for debugging.

        Returns:
            list: Raw lines from the sensor file.
        """
        return self._read_raw()


def list_sensors():
    """List all DS18B20 sensors found on the 1-wire bus."""
    devices = glob.glob(W1_BASE_DIR + '28-*')
    if not devices:
        print("No DS18B20 sensors found.")
        print("\nTroubleshooting:")
        print("1. Check if 1-wire is enabled in /boot/config.txt:")
        print("   dtoverlay=w1-gpio")
        print("2. Verify the sensor is connected properly:")
        print("   - Data pin to GPIO4 (default)")
        print("   - VDD to 3.3V or 5V")
        print("   - GND to GND")
        print("   - 4.7kΩ pull-up resistor between Data and VDD")
        print("3. Load kernel modules:")
        print("   sudo modprobe w1-gpio")
        print("   sudo modprobe w1-therm")
        return []

    print(f"Found {len(devices)} DS18B20 sensor(s):")
    for device in devices:
        device_id = os.path.basename(device)
        print(f"  - {device_id}")
    return devices


def main():
    """Main test function."""
    print("DS18B20 Temperature Sensor Test")
    print("=" * 50)

    # List all sensors
    sensors = list_sensors()
    if not sensors:
        return

    print()

    try:
        # Initialize first sensor found
        sensor = DS18B20()

        print("\nStarting continuous measurements...")
        print("Press Ctrl+C to exit\n")

        # Continuous reading loop
        while True:
            temp_c = sensor.get_temperature_c()
            temp_f = sensor.get_temperature_f()

            if temp_c is not None:
                print(f"Temperature: {temp_c:6.2f} °C  ({temp_f:6.2f} °F)")
            else:
                print("Failed to read temperature (CRC error)")

            time.sleep(2)

    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

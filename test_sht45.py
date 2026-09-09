#!/opt/cabinpython/env/bin/python3

"""
Test script for reading SHT45 temperature and humidity sensor via I2C.
The SHT45 is a high-accuracy digital sensor from Sensirion.
"""

import board
import busio
import time

# SHT45 I2C address (default is 0x44, can be 0x45 depending on ADDR pin)
SHT45_I2CADDR_DEFAULT = 0x44
SHT45_I2CADDR_ALTERNATE = 0x45

# SHT45 Commands
SHT45_CMD_MEASURE_HIGH_PRECISION = 0xFD  # High precision measurement (~8.2ms)
SHT45_CMD_MEASURE_MEDIUM_PRECISION = 0xF6  # Medium precision measurement (~4.5ms)
SHT45_CMD_MEASURE_LOW_PRECISION = 0xE0  # Low precision measurement (~1.7ms)
SHT45_CMD_READ_SERIAL = 0x89  # Read serial number
SHT45_CMD_SOFT_RESET = 0x94  # Soft reset
SHT45_CMD_HEATER_200MW_1S = 0x39  # Activate heater 200mW for 1s
SHT45_CMD_HEATER_200MW_100MS = 0x32  # Activate heater 200mW for 0.1s
SHT45_CMD_HEATER_110MW_1S = 0x2F  # Activate heater 110mW for 1s
SHT45_CMD_HEATER_110MW_100MS = 0x24  # Activate heater 110mW for 0.1s
SHT45_CMD_HEATER_20MW_1S = 0x1E  # Activate heater 20mW for 1s
SHT45_CMD_HEATER_20MW_100MS = 0x15  # Activate heater 20mW for 0.1s


class SHT45:
    """Driver for SHT45 temperature and humidity sensor."""

    def __init__(self, i2c, address=SHT45_I2CADDR_DEFAULT):
        """
        Initialize the SHT45 sensor.

        Args:
            i2c: The I2C bus object
            address: I2C address (default 0x44, can be 0x45)
        """
        self.i2c = i2c
        self.address = address

        # Verify device by attempting to soft reset
        try:
            self.soft_reset()
            print(f"SHT45 sensor found at address 0x{address:02X}")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize SHT45 at address 0x{address:02X}: {e}")

    def _crc8(self, data):
        """
        Calculate CRC-8 checksum for SHT45 data.

        Polynomial: 0x31 (x^8 + x^5 + x^4 + 1)
        Initialization: 0xFF
        """
        crc = 0xFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x31
                else:
                    crc = crc << 1
            crc &= 0xFF
        return crc

    def soft_reset(self):
        """Perform a soft reset of the sensor."""
        self.i2c.writeto(self.address, bytes([SHT45_CMD_SOFT_RESET]))
        time.sleep(0.001)  # Wait 1ms for reset to complete

    def read_serial_number(self):
        """
        Read the sensor's serial number.

        Returns:
            int: 32-bit serial number
        """
        self.i2c.writeto(self.address, bytes([SHT45_CMD_READ_SERIAL]))
        time.sleep(0.001)  # Wait for serial number to be ready

        # Read 6 bytes (2 data + 1 CRC, repeated twice)
        data = bytearray(6)
        self.i2c.readfrom_into(self.address, data)

        # Verify CRC for both words
        if self._crc8(data[0:2]) != data[2]:
            raise RuntimeError("CRC mismatch in serial number (first word)")
        if self._crc8(data[3:5]) != data[5]:
            raise RuntimeError("CRC mismatch in serial number (second word)")

        # Combine the two 16-bit words into a 32-bit serial number
        serial = (data[0] << 24) | (data[1] << 16) | (data[3] << 8) | data[4]
        return serial

    def read_measurement(self, precision='high'):
        """
        Trigger and read a temperature and humidity measurement.

        Args:
            precision: Measurement precision ('high', 'medium', or 'low')

        Returns:
            tuple: (temperature_c, relative_humidity)
        """
        # Select command based on precision
        if precision == 'high':
            cmd = SHT45_CMD_MEASURE_HIGH_PRECISION
            delay = 0.009  # 8.2ms + margin
        elif precision == 'medium':
            cmd = SHT45_CMD_MEASURE_MEDIUM_PRECISION
            delay = 0.005  # 4.5ms + margin
        elif precision == 'low':
            cmd = SHT45_CMD_MEASURE_LOW_PRECISION
            delay = 0.002  # 1.7ms + margin
        else:
            raise ValueError("Precision must be 'high', 'medium', or 'low'")

        # Send measurement command
        self.i2c.writeto(self.address, bytes([cmd]))

        # Wait for measurement to complete
        time.sleep(delay)

        # Read 6 bytes: temp_msb, temp_lsb, temp_crc, hum_msb, hum_lsb, hum_crc
        data = bytearray(6)
        self.i2c.readfrom_into(self.address, data)

        # Verify CRC for temperature
        if self._crc8(data[0:2]) != data[2]:
            raise RuntimeError("CRC mismatch in temperature data")

        # Verify CRC for humidity
        if self._crc8(data[3:5]) != data[5]:
            raise RuntimeError("CRC mismatch in humidity data")

        # Convert temperature (raw value to Celsius)
        # Formula: T = -45 + 175 * (raw / 65535)
        temp_raw = (data[0] << 8) | data[1]
        temperature = -45 + (175 * temp_raw / 65535.0)

        # Convert humidity (raw value to %RH)
        # Formula: RH = -6 + 125 * (raw / 65535)
        hum_raw = (data[3] << 8) | data[4]
        humidity = -6 + (125 * hum_raw / 65535.0)

        # Clamp humidity to valid range [0, 100]
        humidity = max(0.0, min(100.0, humidity))

        return temperature, humidity

    def get_temperature_c(self, precision='high'):
        """
        Get temperature in Celsius.

        Args:
            precision: Measurement precision ('high', 'medium', or 'low')

        Returns:
            float: Temperature in Celsius
        """
        temp_c, _ = self.read_measurement(precision)
        return temp_c

    def get_temperature_f(self, precision='high'):
        """
        Get temperature in Fahrenheit.

        Args:
            precision: Measurement precision ('high', 'medium', or 'low')

        Returns:
            float: Temperature in Fahrenheit
        """
        temp_c = self.get_temperature_c(precision)
        return (temp_c * 9/5) + 32

    def get_humidity(self, precision='high'):
        """
        Get relative humidity.

        Args:
            precision: Measurement precision ('high', 'medium', or 'low')

        Returns:
            float: Relative humidity percentage (0-100)
        """
        _, humidity = self.read_measurement(precision)
        return humidity

    def activate_heater(self, power='200mw', duration='1s'):
        """
        Activate the built-in heater (useful for condensation removal).

        Args:
            power: Heater power ('200mw', '110mw', or '20mw')
            duration: Heater duration ('1s' or '100ms')
        """
        cmd_map = {
            ('200mw', '1s'): SHT45_CMD_HEATER_200MW_1S,
            ('200mw', '100ms'): SHT45_CMD_HEATER_200MW_100MS,
            ('110mw', '1s'): SHT45_CMD_HEATER_110MW_1S,
            ('110mw', '100ms'): SHT45_CMD_HEATER_110MW_100MS,
            ('20mw', '1s'): SHT45_CMD_HEATER_20MW_1S,
            ('20mw', '100ms'): SHT45_CMD_HEATER_20MW_100MS,
        }

        key = (power.lower(), duration.lower())
        if key not in cmd_map:
            raise ValueError(f"Invalid heater configuration: {power}, {duration}")

        self.i2c.writeto(self.address, bytes([cmd_map[key]]))


def scan_i2c_bus(i2c):
    """Scan the I2C bus for SHT45 sensors."""
    print("Scanning I2C bus for SHT45 sensors...")
    found_devices = []

    for addr in [SHT45_I2CADDR_DEFAULT, SHT45_I2CADDR_ALTERNATE]:
        try:
            i2c.writeto(addr, bytes([SHT45_CMD_SOFT_RESET]))
            time.sleep(0.001)
            found_devices.append(addr)
            print(f"  Found SHT45 at address 0x{addr:02X}")
        except Exception:
            pass

    if not found_devices:
        print("  No SHT45 sensors found.")
        print("\nTroubleshooting:")
        print("1. Check if I2C is enabled:")
        print("   sudo raspi-config -> Interface Options -> I2C -> Enable")
        print("2. Verify the sensor is connected properly:")
        print("   - SDA to GPIO2 (pin 3)")
        print("   - SCL to GPIO3 (pin 5)")
        print("   - VDD to 3.3V")
        print("   - GND to GND")
        print("3. Check for any devices on the I2C bus:")
        print("   sudo i2cdetect -y 1")

    return found_devices


def main():
    """Main test function."""
    print("SHT45 Temperature & Humidity Sensor Test")
    print("=" * 50)

    try:
        # Initialize I2C
        i2c = board.I2C()

        # Scan for devices
        devices = scan_i2c_bus(i2c)
        if not devices:
            return

        print()

        # Initialize SHT45 (use first found device)
        sht45 = SHT45(i2c, address=devices[0])

        # Read and display serial number
        try:
            serial = sht45.read_serial_number()
            print(f"Serial Number: 0x{serial:08X}")
        except Exception as e:
            print(f"Could not read serial number: {e}")

        print("\nStarting continuous measurements...")
        print("Press Ctrl+C to exit\n")

        # Continuous reading loop
        while True:
            try:
                temperature_c, humidity = sht45.read_measurement(precision='high')
                temperature_f = (temperature_c * 9/5) + 32

                print(f"Temperature: {temperature_c:6.2f} °C  ({temperature_f:6.2f} °F)")
                print(f"Humidity:    {humidity:6.2f} %RH")
                print("-" * 50)

            except Exception as e:
                print(f"Measurement error: {e}")

            time.sleep(2)

    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

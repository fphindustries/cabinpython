"""
SHT45 Temperature and Humidity Sensor Driver

This module provides a driver for the SHT45 sensor via I2C.
"""

import time
import logging


# SHT45 I2C addresses
SHT45_I2CADDR_DEFAULT = 0x44
SHT45_I2CADDR_ALTERNATE = 0x45

# SHT45 Commands
SHT45_CMD_MEASURE_HIGH_PRECISION = 0xFD
SHT45_CMD_SOFT_RESET = 0x94


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
            logging.debug(f"SHT45 sensor initialized at address 0x{address:02X}")
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
        time.sleep(0.001)

    def read_measurement(self, precision='high'):
        """
        Trigger and read a temperature and humidity measurement.

        Args:
            precision: Measurement precision ('high', 'medium', or 'low')

        Returns:
            tuple: (temperature_c, relative_humidity)
        """
        # Use high precision command
        cmd = SHT45_CMD_MEASURE_HIGH_PRECISION
        delay = 0.009  # 8.2ms + margin

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

    def get_temperature_c(self):
        """Get temperature in Celsius."""
        temp_c, _ = self.read_measurement()
        return temp_c

    def get_temperature_f(self):
        """Get temperature in Fahrenheit."""
        temp_c = self.get_temperature_c()
        return (temp_c * 9/5) + 32

    def get_humidity(self):
        """Get relative humidity percentage (0-100)."""
        _, humidity = self.read_measurement()
        return humidity

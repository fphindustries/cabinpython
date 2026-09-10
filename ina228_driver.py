"""
INA228 Power Monitor Driver

This module provides a wrapper for the Adafruit INA228 library.
"""

import logging
import time
import adafruit_ina228


# INA228 I2C address (default is 0x40, can be 0x41-0x4F depending on A0/A1 pins)
INA228_I2CADDR_DEFAULT = 0x40


class INA228:
    """Wrapper for Adafruit INA228 power monitor library."""

    def __init__(self, i2c, address=INA228_I2CADDR_DEFAULT, shunt_resistor=0.015):
        """
        Initialize the INA228 sensor using Adafruit library.

        Args:
            i2c: The I2C bus object
            address: I2C address (default 0x40)
            shunt_resistor: Shunt resistor value in ohms (default 15mΩ = 0.015Ω)
                           Note: This parameter is accepted for compatibility but the
                           Adafruit library handles calibration internally.
        """
        self.sensor = adafruit_ina228.INA228(i2c, address=address)
        self.shunt_resistor = shunt_resistor
        logging.debug(f"INA228 initialized at address 0x{address:02X}")

        # Wait for first measurement to complete (INA228 needs settling time)
        # This prevents the first reading from returning 0 values
        time.sleep(0.2)  # 200ms settling time
        logging.debug("INA228 sensor settled and ready")

    def get_bus_voltage(self):
        """Get bus voltage in volts."""
        return self.sensor.bus_voltage

    def get_shunt_voltage(self):
        """Get shunt voltage in millivolts."""
        # Adafruit library returns shunt voltage in volts, convert to mV
        return self.sensor.shunt_voltage * 1000.0

    def get_current(self):
        """Get current in amperes."""
        return self.sensor.current

    def get_power(self):
        """Get power in watts."""
        return self.sensor.power

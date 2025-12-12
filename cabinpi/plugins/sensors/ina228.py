"""
INA228 power monitor sensor plugin.

This plugin reads from the INA228 power monitor via I2C using smbus2.
The INA228 provides high-precision current, voltage, power, and energy measurements.

Hardware:
- I2C address: 0x40 (default), configurable via A0/A1 pins (0x40-0x4F)
- Requires I2C bus access (typically bus 1 on Raspberry Pi)
- 20-bit ADC for ultra-precise measurements
- Supports bus voltages up to 85V
"""

import logging
import struct
from datetime import datetime
from typing import Dict, Any, Optional

from smbus2 import SMBus

from cabinpi.core.protocols import SensorPlugin
from cabinpi.core.models import SensorReading, SensorType

logger = logging.getLogger(__name__)


class INA228Sensor:
    """
    INA228 power monitor sensor implementation.

    Implements the SensorPlugin protocol for reading current, voltage,
    power, and energy from an INA228 sensor via I2C.

    Configuration example:
        ina228_battery:
          enabled: true
          module: cabinpi.plugins.sensors.ina228
          type: polling
          interval: 60
          config:
            i2c_bus: 1
            i2c_address: 0x40
            shunt_resistor: 0.015  # 15 milliohm
            max_current: 10.0      # 10A max expected
            label: "battery"
    """

    # INA228 Register addresses
    REG_CONFIG = 0x00
    REG_ADC_CONFIG = 0x01
    REG_SHUNT_CAL = 0x02
    REG_SHUNT_TEMPCO = 0x03
    REG_VSHUNT = 0x04
    REG_VBUS = 0x05
    REG_DIETEMP = 0x06
    REG_CURRENT = 0x07
    REG_POWER = 0x08
    REG_ENERGY = 0x09
    REG_CHARGE = 0x0A
    REG_DIAG_ALRT = 0x0B
    REG_SOVL = 0x0C
    REG_SUVL = 0x0D
    REG_BOVL = 0x0E
    REG_BUVL = 0x0F
    REG_TEMP_LIMIT = 0x10
    REG_PWR_LIMIT = 0x11
    REG_MANUFACTURER_ID = 0x3E
    REG_DEVICE_ID = 0x3F

    # Constants for calculations
    MANUFACTURER_ID = 0x5449  # "TI" in ASCII
    DEVICE_ID = 0x228

    def __init__(self, sensor_id: str) -> None:
        """
        Initialize the INA228 sensor.

        Args:
            sensor_id: Unique sensor identifier
        """
        self._sensor_id = sensor_id
        self._bus: Optional[SMBus] = None
        self._i2c_bus: int = 1
        self._i2c_address: int = 0x40
        self._shunt_resistor: float = 0.015  # Ohms (15 milliohm default)
        self._max_current: float = 10.0  # Amps
        self._label: str = ""
        self._current_lsb: float = 0.0

    @property
    def sensor_id(self) -> str:
        """Return the sensor ID."""
        return self._sensor_id

    @property
    def sensor_type(self) -> SensorType:
        """Return sensor type (polling)."""
        return SensorType.POLLING

    async def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the INA228 sensor.

        Args:
            config: Configuration dict with:
                - i2c_bus: I2C bus number (default: 1)
                - i2c_address: I2C address (default: 0x40)
                - shunt_resistor: Shunt resistance in Ohms (default: 0.015)
                - max_current: Maximum expected current in Amps (default: 10.0)
                - label: Optional label for this sensor

        Returns:
            True if initialization succeeded
        """
        try:
            # Get configuration
            self._i2c_bus = config.get("i2c_bus", 1)
            self._i2c_address = config.get("i2c_address", 0x40)
            self._shunt_resistor = config.get("shunt_resistor", 0.015)
            self._max_current = config.get("max_current", 10.0)
            self._label = config.get("label", "")

            # Open I2C bus
            self._bus = SMBus(self._i2c_bus)

            # Verify device ID
            manufacturer_id = self._read_register_16bit(self.REG_MANUFACTURER_ID)
            device_id = self._read_register_16bit(self.REG_DEVICE_ID)

            if manufacturer_id != self.MANUFACTURER_ID:
                logger.error(
                    f"INA228 manufacturer ID mismatch: expected 0x{self.MANUFACTURER_ID:04X}, "
                    f"got 0x{manufacturer_id:04X}"
                )
                return False

            # Device ID check (upper 12 bits should be 0x228)
            device_id_upper = (device_id >> 4) & 0xFFF
            if device_id_upper != self.DEVICE_ID:
                logger.error(
                    f"INA228 device ID mismatch: expected 0x{self.DEVICE_ID:03X}, "
                    f"got 0x{device_id_upper:03X}"
                )
                return False

            # Calculate current LSB
            # Current LSB = Max Expected Current / 2^19
            self._current_lsb = self._max_current / (2 ** 19)

            # Calculate calibration register value
            # CAL = 0.00512 / (Current_LSB × RSHUNT)
            cal_value = int(0.00512 / (self._current_lsb * self._shunt_resistor))
            self._write_register_16bit(self.REG_SHUNT_CAL, cal_value)

            # Configure ADC (default: continuous mode, 1024 samples averaging)
            # ADC_CONFIG: MODE[3:0]=1111 (continuous), VBUSCT[2:0]=100 (1.1ms),
            #             VSHCT[2:0]=100 (1.1ms), VTCT[2:0]=100 (1.1ms),
            #             AVG[2:0]=111 (1024 samples)
            adc_config = 0xFB68  # Continuous, 1.1ms conversion, 1024 avg
            self._write_register_16bit(self.REG_ADC_CONFIG, adc_config)

            logger.info(
                f"INA228 sensor '{self._label or self._sensor_id}' initialized on "
                f"bus {self._i2c_bus}, address 0x{self._i2c_address:02x}, "
                f"shunt={self._shunt_resistor}Ω, max_current={self._max_current}A, "
                f"current_lsb={self._current_lsb*1000:.3f}mA"
            )
            return True

        except Exception as e:
            logger.exception(f"Failed to initialize INA228 sensor: {e}")
            return False

    def _read_register_16bit(self, register: int) -> int:
        """Read a 16-bit register value."""
        if not self._bus:
            raise RuntimeError("I2C bus not initialized")

        data = self._bus.read_i2c_block_data(self._i2c_address, register, 2)
        return (data[0] << 8) | data[1]

    def _read_register_24bit(self, register: int) -> int:
        """Read a 24-bit register value (signed)."""
        if not self._bus:
            raise RuntimeError("I2C bus not initialized")

        data = self._bus.read_i2c_block_data(self._i2c_address, register, 3)
        # Combine bytes (MSB first)
        value = (data[0] << 16) | (data[1] << 8) | data[2]

        # Convert to signed (24-bit two's complement)
        if value & 0x800000:
            value -= 0x1000000

        return value

    def _write_register_16bit(self, register: int, value: int) -> None:
        """Write a 16-bit register value."""
        if not self._bus:
            raise RuntimeError("I2C bus not initialized")

        msb = (value >> 8) & 0xFF
        lsb = value & 0xFF
        self._bus.write_i2c_block_data(self._i2c_address, register, [msb, lsb])

    async def read(self) -> SensorReading:
        """
        Read current, voltage, power, and temperature from INA228.

        Returns:
            SensorReading with measurements:
                - current_a: Current in Amps
                - current_ma: Current in milliamps
                - bus_voltage_v: Bus voltage in Volts
                - shunt_voltage_mv: Shunt voltage in millivolts
                - power_w: Power in Watts
                - power_mw: Power in milliwatts
                - die_temp_c: Die temperature in Celsius
                - die_temp_f: Die temperature in Fahrenheit
                - label: Optional label (if configured)
        """
        try:
            if not self._bus:
                return SensorReading(
                    sensor_id=self._sensor_id,
                    timestamp=datetime.now(),
                    measurements={},
                    error="Sensor not initialized"
                )

            measurements = {}

            # Read shunt voltage (24-bit signed, LSB = 312.5 nV)
            shunt_raw = self._read_register_24bit(self.REG_VSHUNT)
            shunt_voltage_v = shunt_raw * 312.5e-9
            shunt_voltage_mv = shunt_voltage_v * 1000

            # Read bus voltage (24-bit signed, LSB = 195.3125 µV)
            vbus_raw = self._read_register_24bit(self.REG_VBUS)
            bus_voltage_v = vbus_raw * 195.3125e-6

            # Read current (24-bit signed, in current_lsb units)
            current_raw = self._read_register_24bit(self.REG_CURRENT)
            current_a = current_raw * self._current_lsb
            current_ma = current_a * 1000

            # Read power (24-bit unsigned, LSB = 3.2 × current_lsb)
            power_raw = self._read_register_24bit(self.REG_POWER)
            power_w = power_raw * 3.2 * self._current_lsb
            power_mw = power_w * 1000

            # Read die temperature (16-bit signed, LSB = 7.8125 m°C)
            dietemp_raw = self._read_register_16bit(self.REG_DIETEMP)
            # Convert to signed
            if dietemp_raw & 0x8000:
                dietemp_raw -= 0x10000
            die_temp_c = dietemp_raw * 7.8125e-3
            die_temp_f = (die_temp_c * 9/5) + 32

            measurements = {
                "current_a": round(current_a, 4),
                "current_ma": round(current_ma, 2),
                "bus_voltage_v": round(bus_voltage_v, 3),
                "shunt_voltage_mv": round(shunt_voltage_mv, 4),
                "power_w": round(power_w, 3),
                "power_mw": round(power_mw, 2),
                "die_temp_c": round(die_temp_c, 2),
                "die_temp_f": round(die_temp_f, 2)
            }

            if self._label:
                measurements["label"] = self._label

            return SensorReading(
                sensor_id=self._sensor_id,
                timestamp=datetime.now(),
                measurements=measurements
            )

        except Exception as e:
            logger.exception(f"Error reading INA228 sensor: {e}")
            return SensorReading(
                sensor_id=self._sensor_id,
                timestamp=datetime.now(),
                measurements={},
                error=str(e)
            )

    async def shutdown(self) -> None:
        """Close I2C bus connection."""
        try:
            if self._bus:
                self._bus.close()
                self._bus = None
                logger.info(f"INA228 sensor '{self._label or self._sensor_id}' shutdown complete")
        except Exception as e:
            logger.warning(f"Error shutting down INA228 sensor: {e}")

    async def health_check(self) -> bool:
        """
        Check if sensor is responsive.

        Returns:
            True if sensor responds to I2C communication
        """
        try:
            if not self._bus:
                return False

            # Try to read manufacturer ID
            manufacturer_id = self._read_register_16bit(self.REG_MANUFACTURER_ID)
            return manufacturer_id == self.MANUFACTURER_ID

        except Exception as e:
            logger.debug(f"INA228 health check failed: {e}")
            return False

"""
SHT31 temperature and humidity sensor plugin.

This plugin reads from the SHT31 sensor via I2C using smbus2.
The SHT31 provides indoor temperature and humidity measurements.

Hardware:
- I2C address: 0x44 (default) or 0x45
- Requires I2C bus access (typically bus 1 on Raspberry Pi)
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from smbus2 import SMBus

from cabinpi.core.protocols import SensorPlugin
from cabinpi.core.models import SensorReading, SensorType

logger = logging.getLogger(__name__)


class SHT31Sensor:
    """
    SHT31 temperature and humidity sensor implementation.

    Implements the SensorPlugin protocol for reading temperature and
    humidity from an SHT31 sensor via I2C.

    Configuration example:
        sht31:
          enabled: true
          module: cabinpi.plugins.sensors.sht31
          type: polling
          interval: 300
          config:
            i2c_bus: 1
            i2c_address: 0x44
    """

    # SHT31 Commands
    CMD_MEASURE_HIGH_REP = [0x2C, 0x06]  # High repeatability measurement
    CMD_SOFT_RESET = [0x30, 0xA2]

    def __init__(self, sensor_id: str) -> None:
        """
        Initialize the SHT31 sensor.

        Args:
            sensor_id: Unique sensor identifier
        """
        self._sensor_id = sensor_id
        self._bus: Optional[SMBus] = None
        self._i2c_bus: int = 1
        self._i2c_address: int = 0x44

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
        Initialize the SHT31 sensor.

        Args:
            config: Configuration dict with:
                - i2c_bus: I2C bus number (default: 1)
                - i2c_address: I2C address (default: 0x44)

        Returns:
            True if initialization succeeded
        """
        try:
            # Get configuration
            self._i2c_bus = config.get("i2c_bus", 1)
            self._i2c_address = config.get("i2c_address", 0x44)

            # Open I2C bus
            self._bus = SMBus(self._i2c_bus)

            # Perform soft reset
            self._bus.write_i2c_block_data(
                self._i2c_address,
                self.CMD_SOFT_RESET[0],
                self.CMD_SOFT_RESET[1:]
            )

            logger.info(
                f"SHT31 sensor initialized on bus {self._i2c_bus}, "
                f"address 0x{self._i2c_address:02x}"
            )
            return True

        except Exception as e:
            logger.exception(f"Failed to initialize SHT31 sensor: {e}")
            return False

    async def read(self) -> SensorReading:
        """
        Read temperature and humidity from SHT31.

        Returns:
            SensorReading with measurements:
                - int_c: Temperature in Celsius
                - int_f: Temperature in Fahrenheit
                - humidity: Relative humidity (%)
        """
        try:
            if not self._bus:
                return SensorReading(
                    sensor_id=self._sensor_id,
                    timestamp=datetime.now(),
                    measurements={},
                    error="Sensor not initialized"
                )

            # Trigger measurement
            self._bus.write_i2c_block_data(
                self._i2c_address,
                self.CMD_MEASURE_HIGH_REP[0],
                self.CMD_MEASURE_HIGH_REP[1:]
            )

            # Wait for measurement (typical: 15ms for high repeatability)
            import asyncio
            await asyncio.sleep(0.02)

            # Read 6 bytes (temp MSB, temp LSB, temp CRC, hum MSB, hum LSB, hum CRC)
            data = self._bus.read_i2c_block_data(self._i2c_address, 0x00, 6)

            # Parse temperature (first 2 bytes)
            temp_raw = (data[0] << 8) | data[1]
            temp_c = -45 + (175 * temp_raw / 65535.0)

            # Parse humidity (bytes 3-4)
            hum_raw = (data[3] << 8) | data[4]
            humidity = 100 * hum_raw / 65535.0

            # Convert to Fahrenheit
            temp_f = (temp_c * 9/5) + 32

            return SensorReading(
                sensor_id=self._sensor_id,
                timestamp=datetime.now(),
                measurements={
                    "int_c": round(temp_c, 2),
                    "int_f": round(temp_f, 2),
                    "humidity": round(humidity, 2)
                }
            )

        except Exception as e:
            logger.exception(f"Error reading SHT31 sensor: {e}")
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
                logger.info("SHT31 sensor shutdown complete")
        except Exception as e:
            logger.warning(f"Error shutting down SHT31 sensor: {e}")

    async def health_check(self) -> bool:
        """
        Check if sensor is responsive.

        Returns:
            True if sensor responds to I2C communication
        """
        try:
            if not self._bus:
                return False

            # Try to read status register (0xF32D command)
            self._bus.write_i2c_block_data(self._i2c_address, 0xF3, [0x2D])
            import asyncio
            await asyncio.sleep(0.01)
            data = self._bus.read_i2c_block_data(self._i2c_address, 0x00, 3)

            # If we got data, sensor is responsive
            return len(data) == 3

        except Exception as e:
            logger.debug(f"SHT31 health check failed: {e}")
            return False

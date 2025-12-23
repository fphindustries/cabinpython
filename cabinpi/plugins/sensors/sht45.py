"""
SHT45 temperature and humidity sensor plugin.

This plugin reads from the SHT45 sensor via I2C using smbus2.
The SHT45 provides high-accuracy temperature and humidity measurements
with improved power efficiency compared to SHT31.

Hardware:
- I2C address: 0x44 (default)
- Requires I2C bus access (typically bus 1 on Raspberry Pi)
- Ultra-low power consumption
- Higher accuracy: ±1.0% RH, ±0.1°C
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional

from smbus2 import SMBus

from cabinpi.core.protocols import SensorPlugin
from cabinpi.core.models import SensorReading, SensorType

logger = logging.getLogger(__name__)


class SHT45Sensor:
    """
    SHT45 temperature and humidity sensor implementation.

    Implements the SensorPlugin protocol for reading temperature and
    humidity from an SHT45 sensor via I2C.

    Configuration example:
        sht45:
          enabled: true
          module: cabinpi.plugins.sensors.sht45
          type: polling
          interval: 300
          config:
            i2c_bus: 1
            i2c_address: 0x44
            repeatability: "high"  # high, medium, or low
    """

    # SHT45 Commands (16-bit)
    CMD_MEASURE_HIGH_REP = 0xFD  # High repeatability, 8.2ms
    CMD_MEASURE_MED_REP = 0xF6   # Medium repeatability, 4.3ms
    CMD_MEASURE_LOW_REP = 0xE0   # Low repeatability, 1.7ms
    CMD_SOFT_RESET = 0x94
    CMD_READ_SERIAL = 0x89

    # Measurement timing (milliseconds)
    TIMING_HIGH = 9    # 8.2ms + margin
    TIMING_MEDIUM = 5  # 4.3ms + margin
    TIMING_LOW = 2     # 1.7ms + margin

    # CRC-8 polynomial
    CRC_POLYNOMIAL = 0x31
    CRC_INIT = 0xFF

    def __init__(self, sensor_id: str) -> None:
        """
        Initialize the SHT45 sensor.

        Args:
            sensor_id: Unique sensor identifier
        """
        self._sensor_id = sensor_id
        self._bus: Optional[SMBus] = None
        self._i2c_bus: int = 1
        self._i2c_address: int = 0x44
        self._repeatability: str = "high"
        self._measure_cmd: int = self.CMD_MEASURE_HIGH_REP
        self._measure_delay: float = self.TIMING_HIGH / 1000.0

    @property
    def sensor_id(self) -> str:
        """Return the sensor ID."""
        return self._sensor_id

    @property
    def sensor_type(self) -> SensorType:
        """Return sensor type (polling)."""
        return SensorType.POLLING

    def _calculate_crc(self, data: bytes) -> int:
        """
        Calculate CRC-8 checksum for data validation.

        Args:
            data: Bytes to calculate CRC for

        Returns:
            CRC-8 checksum
        """
        crc = self.CRC_INIT
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ self.CRC_POLYNOMIAL
                else:
                    crc = crc << 1
            crc &= 0xFF
        return crc

    async def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the SHT45 sensor.

        Args:
            config: Configuration dict with:
                - i2c_bus: I2C bus number (default: 1)
                - i2c_address: I2C address (default: 0x44)
                - repeatability: Measurement repeatability - "high", "medium", or "low"
                                (default: "high")

        Returns:
            True if initialization succeeded
        """
        try:
            # Get configuration
            self._i2c_bus = config.get("i2c_bus", 1)
            self._i2c_address = config.get("i2c_address", 0x44)
            self._repeatability = config.get("repeatability", "high").lower()

            # Set measurement command and delay based on repeatability
            if self._repeatability == "high":
                self._measure_cmd = self.CMD_MEASURE_HIGH_REP
                self._measure_delay = self.TIMING_HIGH / 1000.0
            elif self._repeatability == "medium":
                self._measure_cmd = self.CMD_MEASURE_MED_REP
                self._measure_delay = self.TIMING_MEDIUM / 1000.0
            elif self._repeatability == "low":
                self._measure_cmd = self.CMD_MEASURE_LOW_REP
                self._measure_delay = self.TIMING_LOW / 1000.0
            else:
                logger.warning(
                    f"Invalid repeatability '{self._repeatability}', using 'high'"
                )
                self._repeatability = "high"
                self._measure_cmd = self.CMD_MEASURE_HIGH_REP
                self._measure_delay = self.TIMING_HIGH / 1000.0

            # Open I2C bus
            self._bus = SMBus(self._i2c_bus)

            # Perform soft reset
            self._bus.write_byte(self._i2c_address, self.CMD_SOFT_RESET)

            # Wait for reset to complete
            import asyncio
            await asyncio.sleep(0.001)

            logger.info(
                f"SHT45 sensor initialized on bus {self._i2c_bus}, "
                f"address 0x{self._i2c_address:02x}, "
                f"repeatability={self._repeatability}"
            )
            return True

        except Exception as e:
            logger.exception(f"Failed to initialize SHT45 sensor: {e}")
            return False

    async def read(self) -> SensorReading:
        """
        Read temperature and humidity from SHT45.

        Returns:
            SensorReading with measurements:
                - temp_c: Temperature in Celsius
                - temp_f: Temperature in Fahrenheit
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
            self._bus.write_byte(self._i2c_address, self._measure_cmd)

            # Wait for measurement to complete
            import asyncio
            await asyncio.sleep(self._measure_delay)

            # Read 6 bytes: temp MSB, temp LSB, temp CRC, hum MSB, hum LSB, hum CRC
            # Note: SHT45 doesn't use register addressing for data read, just I2C read
            from smbus2 import i2c_msg
            msg = i2c_msg.read(self._i2c_address, 6)
            self._bus.i2c_rdwr(msg)
            data = list(msg)

            # Validate temperature CRC
            temp_data = bytes([data[0], data[1]])
            temp_crc = data[2]
            if self._calculate_crc(temp_data) != temp_crc:
                logger.warning("SHT45 temperature CRC mismatch")
                return SensorReading(
                    sensor_id=self._sensor_id,
                    timestamp=datetime.now(),
                    measurements={},
                    error="Temperature CRC validation failed"
                )

            # Validate humidity CRC
            hum_data = bytes([data[3], data[4]])
            hum_crc = data[5]
            if self._calculate_crc(hum_data) != hum_crc:
                logger.warning("SHT45 humidity CRC mismatch")
                return SensorReading(
                    sensor_id=self._sensor_id,
                    timestamp=datetime.now(),
                    measurements={},
                    error="Humidity CRC validation failed"
                )

            # Parse temperature (first 2 bytes)
            temp_raw = (data[0] << 8) | data[1]
            temp_c = -45 + (175 * temp_raw / 65535.0)

            # Parse humidity (bytes 3-4)
            hum_raw = (data[3] << 8) | data[4]
            humidity = -6 + (125 * hum_raw / 65535.0)

            # Clamp humidity to valid range
            humidity = max(0.0, min(100.0, humidity))

            # Convert to Fahrenheit
            temp_f = (temp_c * 9/5) + 32

            return SensorReading(
                sensor_id=self._sensor_id,
                timestamp=datetime.now(),
                measurements={
                    "temp_c": round(temp_c, 2),
                    "temp_f": round(temp_f, 2),
                    "humidity": round(humidity, 2)
                }
            )

        except Exception as e:
            logger.exception(f"Error reading SHT45 sensor: {e}")
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
                logger.info("SHT45 sensor shutdown complete")
        except Exception as e:
            logger.warning(f"Error shutting down SHT45 sensor: {e}")

    async def health_check(self) -> bool:
        """
        Check if sensor is responsive.

        Returns:
            True if sensor responds to I2C communication
        """
        try:
            if not self._bus:
                return False

            # Try to read serial number
            self._bus.write_byte(self._i2c_address, self.CMD_READ_SERIAL)
            import asyncio
            await asyncio.sleep(0.001)

            # Serial number is 6 bytes (2 bytes + CRC, repeated)
            data = self._bus.read_i2c_block_data(self._i2c_address, 0x00, 6)

            # If we got data, sensor is responsive
            return len(data) == 6

        except Exception as e:
            logger.debug(f"SHT45 health check failed: {e}")
            return False

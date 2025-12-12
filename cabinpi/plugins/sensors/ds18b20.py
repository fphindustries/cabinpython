"""
DS18B20 temperature sensor plugin.

This plugin reads from the DS18B20 1-wire temperature sensor.
The DS18B20 provides high-precision temperature measurements and can be
connected via the 1-wire interface on Raspberry Pi.

Hardware:
- 1-wire interface (GPIO4 by default on Raspberry Pi)
- Device ID: 28-xxxxxxxxxxxx (auto-detected or configured)
- Multiple sensors supported on same bus
- Requires 1-wire kernel module enabled
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from cabinpi.core.protocols import SensorPlugin
from cabinpi.core.models import SensorReading, SensorType

logger = logging.getLogger(__name__)


class DS18B20Sensor:
    """
    DS18B20 temperature sensor implementation.

    Implements the SensorPlugin protocol for reading temperature from
    DS18B20 sensors via 1-wire interface.

    Configuration example:
        ds18b20_outdoor:
          enabled: true
          module: cabinpi.plugins.sensors.ds18b20
          type: polling
          interval: 60
          config:
            device_id: "28-0000123456ab"  # Optional, auto-detect if not provided
            label: "outdoor"               # Optional, for multiple sensors
            base_dir: "/sys/bus/w1/devices"  # Optional, default path
    """

    # 1-wire base directory
    DEFAULT_BASE_DIR = "/sys/bus/w1/devices"

    # DS18B20 family code
    FAMILY_CODE = "28"

    def __init__(self, sensor_id: str) -> None:
        """
        Initialize the DS18B20 sensor.

        Args:
            sensor_id: Unique sensor identifier
        """
        self._sensor_id = sensor_id
        self._device_id: Optional[str] = None
        self._device_path: Optional[Path] = None
        self._base_dir: Path = Path(self.DEFAULT_BASE_DIR)
        self._label: str = ""

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
        Initialize the DS18B20 sensor.

        Args:
            config: Configuration dict with:
                - device_id: 1-wire device ID (optional, auto-detect first device)
                - label: Human-readable label for this sensor (optional)
                - base_dir: Base directory for 1-wire devices (optional)

        Returns:
            True if initialization succeeded
        """
        try:
            # Get configuration
            self._device_id = config.get("device_id")
            self._label = config.get("label", "")
            base_dir_str = config.get("base_dir", self.DEFAULT_BASE_DIR)
            self._base_dir = Path(base_dir_str)

            # Verify base directory exists
            if not self._base_dir.exists():
                logger.error(
                    f"1-wire base directory not found: {self._base_dir}. "
                    "Is the w1-gpio module loaded?"
                )
                return False

            # If device_id not provided, auto-detect first DS18B20
            if not self._device_id:
                self._device_id = self._auto_detect_device()
                if not self._device_id:
                    logger.error("No DS18B20 sensors detected on 1-wire bus")
                    return False
                logger.info(f"Auto-detected DS18B20 device: {self._device_id}")

            # Set device path
            self._device_path = self._base_dir / self._device_id / "w1_slave"

            # Verify device file exists
            if not self._device_path.exists():
                logger.error(f"Device file not found: {self._device_path}")
                return False

            # Test read to verify sensor is working
            temp = self._read_temperature()
            if temp is None:
                logger.error(f"Failed to read from DS18B20 device {self._device_id}")
                return False

            logger.info(
                f"DS18B20 sensor initialized: {self._device_id} "
                f"({self._label or 'unlabeled'}), current temp: {temp}°C"
            )
            return True

        except Exception as e:
            logger.exception(f"Failed to initialize DS18B20 sensor: {e}")
            return False

    def _auto_detect_device(self) -> Optional[str]:
        """
        Auto-detect first DS18B20 device on 1-wire bus.

        Returns:
            Device ID if found, None otherwise
        """
        try:
            # List all devices starting with DS18B20 family code
            for device_dir in self._base_dir.iterdir():
                if device_dir.is_dir() and device_dir.name.startswith(f"{self.FAMILY_CODE}-"):
                    return device_dir.name
            return None
        except Exception as e:
            logger.warning(f"Error during auto-detection: {e}")
            return None

    def _read_temperature(self) -> Optional[float]:
        """
        Read raw temperature from device file.

        Returns:
            Temperature in Celsius, or None if read failed
        """
        try:
            # Read device file
            with open(self._device_path, 'r') as f:
                lines = f.readlines()

            # Verify CRC check passed (first line should end with "YES")
            if len(lines) < 2:
                logger.warning("Incomplete data from DS18B20")
                return None

            if not lines[0].strip().endswith("YES"):
                logger.warning("CRC check failed for DS18B20 reading")
                return None

            # Parse temperature from second line
            # Format: "... t=23500" where value is in millidegrees Celsius
            temp_pos = lines[1].find("t=")
            if temp_pos == -1:
                logger.warning("Temperature value not found in DS18B20 data")
                return None

            temp_string = lines[1][temp_pos + 2:].strip()
            temp_millidegrees = int(temp_string)
            temp_celsius = temp_millidegrees / 1000.0

            return temp_celsius

        except Exception as e:
            logger.warning(f"Error reading DS18B20 temperature: {e}")
            return None

    async def read(self) -> SensorReading:
        """
        Read temperature from DS18B20.

        Returns:
            SensorReading with measurements:
                - temp_c: Temperature in Celsius
                - temp_f: Temperature in Fahrenheit
                - device_id: 1-wire device ID
                - label: Sensor label (if configured)
        """
        try:
            if not self._device_path:
                return SensorReading(
                    sensor_id=self._sensor_id,
                    timestamp=datetime.now(),
                    measurements={},
                    error="Sensor not initialized"
                )

            # Read temperature
            temp_c = self._read_temperature()

            if temp_c is None:
                return SensorReading(
                    sensor_id=self._sensor_id,
                    timestamp=datetime.now(),
                    measurements={},
                    error="Failed to read temperature"
                )

            # Convert to Fahrenheit
            temp_f = (temp_c * 9/5) + 32

            # Build measurements dict
            measurements = {
                "temp_c": round(temp_c, 2),
                "temp_f": round(temp_f, 2),
                "device_id": self._device_id
            }

            # Add label if configured
            if self._label:
                measurements["label"] = self._label

            return SensorReading(
                sensor_id=self._sensor_id,
                timestamp=datetime.now(),
                measurements=measurements
            )

        except Exception as e:
            logger.exception(f"Error reading DS18B20 sensor: {e}")
            return SensorReading(
                sensor_id=self._sensor_id,
                timestamp=datetime.now(),
                measurements={},
                error=str(e)
            )

    async def shutdown(self) -> None:
        """Shutdown sensor (no cleanup needed for 1-wire)."""
        logger.info(f"DS18B20 sensor shutdown: {self._device_id}")

    async def health_check(self) -> bool:
        """
        Check if sensor is responsive.

        Returns:
            True if sensor can be read successfully
        """
        try:
            if not self._device_path or not self._device_path.exists():
                return False

            temp = self._read_temperature()
            return temp is not None

        except Exception as e:
            logger.debug(f"DS18B20 health check failed: {e}")
            return False

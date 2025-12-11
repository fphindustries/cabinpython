"""
Magnum inverter sensor plugin.

This plugin reads data from a Magnum inverter via RS232 serial
using the pymagnum library.

Hardware:
- Serial port: /dev/ttyUSB1 or similar (RS232)
- Magnum inverter with remote control panel
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from pymagnum import Magnum

from cabinpi.core.protocols import SensorPlugin
from cabinpi.core.models import SensorReading, SensorType

logger = logging.getLogger(__name__)


class InverterSensor:
    """
    Magnum inverter sensor implementation.

    Implements the SensorPlugin protocol for reading inverter status
    and measurements via RS232 serial.

    Configuration example:
        inverter:
          enabled: true
          module: cabinpi.plugins.sensors.inverter
          type: polling
          interval: 300
          config:
            port: /dev/ttyUSB1
            timeout: 3
    """

    def __init__(self, sensor_id: str) -> None:
        """
        Initialize the inverter sensor.

        Args:
            sensor_id: Unique sensor identifier
        """
        self._sensor_id = sensor_id
        self._magnum: Optional[Magnum] = None
        self._port: str = "/dev/ttyUSB1"
        self._timeout: int = 3

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
        Initialize the inverter connection.

        Args:
            config: Configuration dict with:
                - port: Serial port (e.g., /dev/ttyUSB1)
                - timeout: Read timeout in seconds (default: 3)

        Returns:
            True if initialization succeeded
        """
        try:
            # Get configuration
            self._port = config.get("port", "/dev/ttyUSB1")
            self._timeout = config.get("timeout", 3)

            # Create Magnum reader
            self._magnum = Magnum(device=self._port, timeout=self._timeout)

            # Test connection by reading devices
            devices = self._magnum.getDevices()

            # Verify we have an inverter device
            inverter = next(
                (d for d in devices if d.get('device') == 'INVERTER'),
                None
            )

            if not inverter:
                logger.error("No INVERTER device found on Magnum bus")
                return False

            logger.info(f"Inverter sensor initialized on {self._port}")
            return True

        except Exception as e:
            logger.exception(f"Failed to initialize inverter sensor: {e}")
            return False

    async def read(self) -> SensorReading:
        """
        Read inverter status and measurements.

        Returns:
            SensorReading with measurements including:
                - Inverter on/off status
                - Operating mode
                - Fault status
                - Output voltage (VAC)
                - Output current (AAC)
                - DC voltage (VDC)
        """
        try:
            if not self._magnum:
                return SensorReading(
                    sensor_id=self._sensor_id,
                    timestamp=datetime.now(),
                    measurements={},
                    error="Inverter not initialized"
                )

            # Get all devices
            devices = self._magnum.getDevices()

            # Find the inverter device
            inverter = next(
                (d for d in devices if d.get('device') == 'INVERTER'),
                None
            )

            if not inverter or 'data' not in inverter:
                return SensorReading(
                    sensor_id=self._sensor_id,
                    timestamp=datetime.now(),
                    measurements={},
                    error="Inverter device not found"
                )

            # Extract inverter data
            data = inverter['data']
            measurements = {
                'InverterOn': data.get('invled'),           # LED status (0=off, 1=on)
                'InverterMode': data.get('mode'),           # Operating mode
                'InverterFault': data.get('fault'),         # Fault code (0=no fault)
                'InverterVACOut': data.get('VACout'),       # Output voltage (VAC)
                'InverterAACOut': data.get('adc'),          # Output current (AAC)
                'Invertervdc': data.get('vdc')              # DC input voltage (VDC)
            }

            return SensorReading(
                sensor_id=self._sensor_id,
                timestamp=datetime.now(),
                measurements=measurements
            )

        except Exception as e:
            logger.exception(f"Error reading inverter: {e}")
            return SensorReading(
                sensor_id=self._sensor_id,
                timestamp=datetime.now(),
                measurements={},
                error=str(e)
            )

    async def shutdown(self) -> None:
        """Close inverter connection."""
        try:
            if self._magnum:
                # pymagnum doesn't have explicit close, but cleanup reference
                self._magnum = None
                logger.info("Inverter sensor shutdown complete")
        except Exception as e:
            logger.warning(f"Error shutting down inverter: {e}")

    async def health_check(self) -> bool:
        """
        Check if inverter is responsive.

        Returns:
            True if inverter responds to queries
        """
        try:
            if not self._magnum:
                return False

            # Try to read devices
            devices = self._magnum.getDevices()

            # Check if we can find the inverter
            inverter = next(
                (d for d in devices if d.get('device') == 'INVERTER'),
                None
            )

            return inverter is not None

        except Exception as e:
            logger.debug(f"Inverter health check failed: {e}")
            return False

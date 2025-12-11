"""
Solar charge controller sensor plugin.

This plugin reads data from a Modbus-enabled solar charge controller
(Classic series) via RS485/serial using pymodbus.

Hardware:
- Modbus slave address: 10 (default)
- Serial port: /dev/ttyUSB0 or similar
- Registers: 4114-4142 (29 registers)
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from pymodbus.client import AsyncModbusSerialClient
from pymodbus.exceptions import ModbusException

from cabinpi.core.protocols import SensorPlugin
from cabinpi.core.models import SensorReading, SensorType

logger = logging.getLogger(__name__)


class SolarModbusSensor:
    """
    Solar charge controller sensor implementation.

    Implements the SensorPlugin protocol for reading solar charge
    controller data via Modbus RTU.

    Configuration example:
        solar_controller:
          enabled: true
          module: cabinpi.plugins.sensors.solar_modbus
          type: polling
          interval: 300
          config:
            port: /dev/ttyUSB0
            baudrate: 19200
            slave_address: 10
            timeout: 3
    """

    def __init__(self, sensor_id: str) -> None:
        """
        Initialize the solar controller sensor.

        Args:
            sensor_id: Unique sensor identifier
        """
        self._sensor_id = sensor_id
        self._client: Optional[AsyncModbusSerialClient] = None
        self._port: str = "/dev/ttyUSB0"
        self._baudrate: int = 19200
        self._slave_address: int = 10
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
        Initialize the solar controller connection.

        Args:
            config: Configuration dict with:
                - port: Serial port (e.g., /dev/ttyUSB0)
                - baudrate: Baud rate (default: 19200)
                - slave_address: Modbus slave ID (default: 10)
                - timeout: Read timeout in seconds (default: 3)

        Returns:
            True if initialization succeeded
        """
        try:
            # Get configuration
            self._port = config.get("port", "/dev/ttyUSB0")
            self._baudrate = config.get("baudrate", 19200)
            self._slave_address = config.get("slave_address", 10)
            self._timeout = config.get("timeout", 3)

            # Create Modbus client
            self._client = AsyncModbusSerialClient(
                port=self._port,
                baudrate=self._baudrate,
                timeout=self._timeout,
                parity='N',
                stopbits=1,
                bytesize=8,
            )

            # Connect to the device
            connected = await self._client.connect()
            if not connected:
                logger.error(f"Failed to connect to solar controller on {self._port}")
                return False

            logger.info(
                f"Solar controller initialized on {self._port} "
                f"(slave {self._slave_address})"
            )
            return True

        except Exception as e:
            logger.exception(f"Failed to initialize solar controller: {e}")
            return False

    async def read(self) -> SensorReading:
        """
        Read solar charge controller data.

        Returns:
            SensorReading with measurements including:
                - Battery voltage, PV voltage, current
                - Power, energy, charge state
                - Temperature and timing data
        """
        try:
            if not self._client or not self._client.connected:
                # Try to reconnect
                if self._client:
                    await self._client.connect()

                if not self._client or not self._client.connected:
                    return SensorReading(
                        sensor_id=self._sensor_id,
                        timestamp=datetime.now(),
                        measurements={},
                        error="Not connected to solar controller"
                    )

            # Read 29 registers starting at address 4114
            response = await self._client.read_holding_registers(
                address=4114,
                count=29,
                slave=self._slave_address
            )

            if response.isError():
                raise ModbusException(f"Modbus read error: {response}")

            registers = response.registers

            # Parse register data according to Classic documentation
            measurements = {
                'dispavgVbatt': registers[0] / 10.0,      # Battery voltage (V)
                'dispavgVpv': registers[1] / 10.0,        # PV voltage (V)
                'IbattDisplay': registers[2] / 10.0,      # Battery current (A)
                'kWHours': registers[3] / 10.0,           # Daily energy (kWh)
                'watts': registers[4],                     # Power (W)
                'chargeState': registers[5],              # Raw charge state
                'batteryState': (registers[5] & 0xFF00) >> 8,  # Battery state
                'classicState': registers[5] & 0xFF,      # Controller state
                'PvInputCurrent': registers[6] / 10.0,    # PV current (A)
                'VocLastMeasured': registers[7] / 10.0,   # Last Voc (V)
                'HighestVinputLog': registers[8] / 10.0,  # Highest input V (V)
                'AmpHours': registers[10],                # Daily Ah
                'LifeTimekWHours': registers[11],         # Lifetime kWh
                'LifetimeAmpHours': registers[12],        # Lifetime Ah
                'BATTtemperature': registers[17],         # Battery temp (C)
                'NiteMinutesNoPwr': registers[20],        # Minutes no power
                'FloatTime': registers[23],               # Float time (min)
                'AbsorbTime': registers[24],              # Absorb time (min)
                'EqualizeTime': registers[28]             # Equalize time (min)
            }

            return SensorReading(
                sensor_id=self._sensor_id,
                timestamp=datetime.now(),
                measurements=measurements
            )

        except ModbusException as e:
            logger.error(f"Modbus error reading solar controller: {e}")
            return SensorReading(
                sensor_id=self._sensor_id,
                timestamp=datetime.now(),
                measurements={},
                error=f"Modbus error: {e}"
            )
        except Exception as e:
            logger.exception(f"Error reading solar controller: {e}")
            return SensorReading(
                sensor_id=self._sensor_id,
                timestamp=datetime.now(),
                measurements={},
                error=str(e)
            )

    async def shutdown(self) -> None:
        """Close Modbus connection."""
        try:
            if self._client:
                self._client.close()
                self._client = None
                logger.info("Solar controller sensor shutdown complete")
        except Exception as e:
            logger.warning(f"Error shutting down solar controller: {e}")

    async def health_check(self) -> bool:
        """
        Check if solar controller is responsive.

        Returns:
            True if connected and responsive
        """
        try:
            if not self._client or not self._client.connected:
                return False

            # Try to read a single register
            response = await self._client.read_holding_registers(
                address=4114,
                count=1,
                slave=self._slave_address
            )

            return not response.isError()

        except Exception as e:
            logger.debug(f"Solar controller health check failed: {e}")
            return False

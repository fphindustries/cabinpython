"""
Magnum inverter RS-485 network sensor plugin.

This plugin reads data from Magnum inverters and network devices via RS-485
serial using the native Magnum network protocol. It supports reading status
from multiple devices (inverter, AGS, BMK) and controlling the inverter.

Hardware:
- Serial port: USB RS-485 converter (/dev/ttyUSB* or similar)
- Magnum inverter/charger connected via RS-485 network
- Baud rate: 19,200 bps
- RJ-11 connector wiring: Pin 1=B, Pin 2=+14V, Pin 3=GND, Pin 4=A

Based on Magnum Networking Communications Protocol (2009-10-15)
Copyright 2003-2009 Magnum Energy
"""

import logging
import struct
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import IntEnum

import serial

from cabinpi.core.protocols import SensorPlugin
from cabinpi.core.models import SensorReading, SensorType

logger = logging.getLogger(__name__)


class InverterStatus(IntEnum):
    """Inverter status codes (byte 0 from inverter)."""
    CHARGER_STANDBY = 0x00      # AC in, charging disabled
    EQ_MODE = 0x01              # Equalizing with AC
    FLOAT_MODE = 0x02           # Float charging with AC
    ABSORB_MODE = 0x04          # Absorb charging with AC
    BULK_MODE = 0x08            # Bulk charging with AC
    BAT_SAVER_MODE = 0x09       # Charge mode but no current (bat full)
    CHARGE_MODE = 0x10          # Charge mode, no AC applied
    OFF = 0x20                  # Inverter off, charger off
    INVERT_MODE = 0x40          # Inverter on (charger on or off)
    INVERTER_STANDBY = 0x50     # MS rev 4.0+ only (PAE)
    SEARCH_MODE = 0x80          # Searching for load


class InverterFault(IntEnum):
    """Inverter fault codes (byte 1 from inverter)."""
    NO_FAULT = 0x00
    STUCK_RELAY = 0x01
    DC_OVERLOAD = 0x02
    AC_OVERLOAD = 0x03
    DEAD_BAT = 0x04
    BACKFEED = 0x05
    LOW_BAT = 0x08
    HIGH_BAT = 0x09
    HIGH_AC_VOLTS = 0x0A
    BAD_BRIDGE = 0x10
    NTC_FAULT = 0x12
    FET_OVERLOAD = 0x13
    INTERNAL_FAULT4 = 0x14
    STACKER_MODE_FAULT = 0x16
    STACKER_CLK_PH_FAULT = 0x18
    STACKER_NO_CLK_FAULT = 0x17
    STACKER_PH_LOSS_FAULT = 0x19
    OVERTEMP = 0x20
    RELAY_FAULT = 0x21
    CHARGER_FAULT = 0x80
    HI_BAT_TEMP = 0x81
    OPEN_SELCO_TCO = 0x90
    CB3_OPEN_FAULT = 0x91


class RemoteCommand:
    """Remote command byte encoding."""

    # Byte 0 bit definitions
    TOGGLE_INVERTER = 0x01      # Bit 0: Toggle inverter on/off
    TOGGLE_CHARGER = 0x02       # Bit 1: Toggle charger on/off
    TOGGLE_EQ_MODE = 0x0A       # Bits 1 & 3: Toggle EQ mode

    # Default values for remote packet
    DEFAULT_SEARCH_WATTS = 5
    DEFAULT_BATTERY_SIZE = 40       # 400Ah in 10Ah units
    DEFAULT_BATTERY_TYPE = 4        # Flooded
    DEFAULT_CHARGER_AMPS = 80       # 80%
    DEFAULT_SHORE_AMPS = 30         # 30A
    DEFAULT_LBCO = 100              # 10.0V for 12V system
    DEFAULT_VAC_CUTOUT = 155        # 80V
    DEFAULT_FLOAT_VOLTS = 132       # 13.2V
    DEFAULT_EQ_VOLTS = 12           # 1.2V above absorption
    DEFAULT_ABSORB_TIME = 20        # 2.0 hours


class MagnumRS485Sensor:
    """
    Magnum RS-485 network sensor implementation.

    Implements the SensorPlugin protocol for reading status from Magnum
    network devices and controlling the inverter via RS-485.

    Configuration example:
        magnum_rs485:
          enabled: true
          module: cabinpi.plugins.sensors.magnum_rs485
          type: polling
          interval: 5  # Read every 5 seconds
          config:
            port: /dev/ttyUSB0
            baudrate: 19200
            timeout: 0.5
            remote_revision: 10  # 1.0
    """

    BAUDRATE = 19200
    PACKET_SIZE = 16        # Standard packet size (older inverters)
    PACKET_SIZE_EXTENDED = 21  # Extended packet size (newer models)
    MASTER_INTERVAL = 0.1   # 100ms between master packets
    SLAVE_DELAY = 0.01      # 10ms delay before slave responds

    def __init__(self, sensor_id: str) -> None:
        """
        Initialize the Magnum RS-485 sensor.

        Args:
            sensor_id: Unique sensor identifier
        """
        self._sensor_id = sensor_id
        self._serial: Optional[serial.Serial] = None
        self._port: str = "/dev/ttyUSB0"
        self._baudrate: int = self.BAUDRATE
        self._timeout: float = 0.5
        self._remote_revision: int = 10  # 1.0

        # Cached data from last read
        self._last_packet: Optional[bytes] = None
        self._last_packet_time: float = 0

        # Control flags
        self._pending_inverter_toggle: bool = False
        self._pending_charger_toggle: bool = False

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
        Initialize the RS-485 connection.

        Args:
            config: Configuration dict with:
                - port: Serial port (e.g., /dev/ttyUSB0)
                - baudrate: Baud rate (default: 19200)
                - timeout: Read timeout in seconds (default: 0.5)
                - remote_revision: Remote firmware version (default: 10 = 1.0)

        Returns:
            True if initialization succeeded
        """
        try:
            # Get configuration
            self._port = config.get("port", "/dev/ttyUSB0")
            self._baudrate = config.get("baudrate", self.BAUDRATE)
            self._timeout = config.get("timeout", 0.5)
            self._remote_revision = config.get("remote_revision", 10)

            # Open serial port
            self._serial = serial.Serial(
                port=self._port,
                baudrate=self._baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self._timeout
            )

            # Clear buffers
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()

            logger.info(
                f"Magnum RS-485 sensor initialized on {self._port} "
                f"at {self._baudrate} baud"
            )
            return True

        except Exception as e:
            logger.exception(f"Failed to initialize Magnum RS-485 sensor: {e}")
            return False

    def _parse_inverter_packet(self, packet: bytes) -> Dict[str, Any]:
        """
        Parse inverter packet (master transmission).

        Args:
            packet: Raw packet bytes (16 or 21 bytes)

        Returns:
            Dictionary of parsed measurements
        """
        if len(packet) < self.PACKET_SIZE:
            return {}

        measurements = {}

        # Byte 0: Inverter status
        status = packet[0]
        measurements['status_code'] = status
        measurements['status_name'] = self._get_status_name(status)

        # Byte 1: Fault code
        fault = packet[1]
        measurements['fault_code'] = fault
        measurements['fault_name'] = self._get_fault_name(fault)

        # Bytes 2-3: DC volts (16-bit, 0.1V per count)
        dc_volts_raw = (packet[2] << 8) | packet[3]
        measurements['dc_volts'] = dc_volts_raw / 10.0

        # Bytes 4-5: DC amps (16-bit, 0-500A range)
        dc_amps_raw = (packet[4] << 8) | packet[5]
        measurements['dc_amps'] = dc_amps_raw

        # Byte 6: AC volts output (0-150V RMS)
        measurements['ac_volts_out'] = packet[6]

        # Byte 7: AC volts input (0-255V peak)
        measurements['ac_volts_in'] = packet[7]

        # Byte 8: Inverter LED (0=off, else on)
        measurements['inverter_led'] = 1 if packet[8] != 0 else 0

        # Byte 9: Charger LED (0=off, else on)
        measurements['charger_led'] = 1 if packet[9] != 0 else 0

        # Byte 10: Inverter revision
        rev = packet[10]
        measurements['inverter_revision'] = f"{rev // 10}.{rev % 10}"

        # Byte 11: Battery temp (°C)
        measurements['battery_temp_c'] = packet[11]
        measurements['battery_temp_f'] = (packet[11] * 9/5) + 32

        # Byte 12: Transformer temp (°C)
        measurements['transformer_temp_c'] = packet[12]
        measurements['transformer_temp_f'] = (packet[12] * 9/5) + 32

        # Byte 13: FET temp (°C)
        measurements['fet_temp_c'] = packet[13]
        measurements['fet_temp_f'] = (packet[13] * 9/5) + 32

        # Byte 14: Inverter model
        measurements['model_code'] = packet[14]
        measurements['model_name'] = self._get_model_name(packet[14])

        # Extended packet (21 bytes) - MS rev 4.0+
        if len(packet) >= self.PACKET_SIZE_EXTENDED:
            # Byte 15: Stack mode
            measurements['stack_mode'] = packet[15]

            # Byte 16: AC input amps
            measurements['ac_input_amps'] = packet[16]

            # Byte 17: AC output amps
            measurements['ac_output_amps'] = packet[17]

            # Bytes 18-19: AC frequency (0.1Hz per count)
            ac_hz_raw = (packet[18] << 8) | packet[19]
            measurements['ac_hz'] = ac_hz_raw / 10.0

        return measurements

    def _get_status_name(self, code: int) -> str:
        """Convert status code to human-readable name."""
        try:
            return InverterStatus(code).name
        except ValueError:
            return f"UNKNOWN_0x{code:02X}"

    def _get_fault_name(self, code: int) -> str:
        """Convert fault code to human-readable name."""
        try:
            return InverterFault(code).name
        except ValueError:
            return f"UNKNOWN_0x{code:02X}"

    def _get_model_name(self, code: int) -> str:
        """Convert model code to model name."""
        models = {
            0x06: "MM612", 0x07: "MM612-AE", 0x08: "MM1212",
            0x09: "MMS1012", 0x0A: "MM1012E", 0x0B: "MM1512",
            0x0F: "ME1512", 0x14: "ME2012", 0x19: "ME2512",
            0x1E: "ME3112", 0x23: "MS2012", 0x28: "MS2012E",
            0x2D: "MS2812", 0x2F: "MS2712E", 0x35: "MM1324E",
            0x36: "MM1524", 0x37: "RD1824", 0x3B: "RD2624E",
            0x3F: "RD2824", 0x45: "RD4024E", 0x4A: "RD3924",
            0x5A: "MS4124E", 0x5B: "MS2024", 0x69: "MS4024",
            0x6A: "MS4024AE", 0x6B: "MS4024PAE", 0x6F: "MS4448AE",
            0x70: "MS3748AEJ", 0x73: "MS4448PAE", 0x74: "MS3748PAEJ"
        }
        return models.get(code, f"UNKNOWN_0x{code:02X}")

    def _build_remote_packet(self) -> bytes:
        """
        Build remote packet to send to inverter.

        Returns:
            16-byte remote packet
        """
        packet = bytearray(16)

        # Byte 0: Control commands
        if self._pending_inverter_toggle:
            packet[0] |= RemoteCommand.TOGGLE_INVERTER
            self._pending_inverter_toggle = False

        if self._pending_charger_toggle:
            packet[0] |= RemoteCommand.TOGGLE_CHARGER
            self._pending_charger_toggle = False

        # Byte 1: Search watts
        packet[1] = RemoteCommand.DEFAULT_SEARCH_WATTS

        # Byte 2: Battery size (10Ah units)
        packet[2] = RemoteCommand.DEFAULT_BATTERY_SIZE

        # Byte 3: Battery type
        packet[3] = RemoteCommand.DEFAULT_BATTERY_TYPE

        # Byte 4: Charger amps (%)
        packet[4] = RemoteCommand.DEFAULT_CHARGER_AMPS

        # Byte 5: AC shore amps
        packet[5] = RemoteCommand.DEFAULT_SHORE_AMPS

        # Byte 6: Remote revision
        packet[6] = self._remote_revision

        # Byte 7: Ambient temp (0 = not available)
        packet[7] = 0

        # Byte 8: Auto genstart (0 = off)
        packet[8] = 0

        # Byte 9: Low battery cutout
        packet[9] = RemoteCommand.DEFAULT_LBCO

        # Byte 10: VAC cutout voltage
        packet[10] = RemoteCommand.DEFAULT_VAC_CUTOUT

        # Byte 11: Float volts
        packet[11] = RemoteCommand.DEFAULT_FLOAT_VOLTS

        # Byte 12: EQ volts (added to absorption)
        packet[12] = RemoteCommand.DEFAULT_EQ_VOLTS

        # Byte 13: Absorb time
        packet[13] = RemoteCommand.DEFAULT_ABSORB_TIME

        # Bytes 14-15: Hours and minutes (always send current time)
        now = time.localtime()
        packet[14] = now.tm_hour
        packet[15] = now.tm_min

        return bytes(packet)

    async def read(self) -> SensorReading:
        """
        Read inverter status from RS-485 network.

        This acts as a passive listener on the RS-485 bus, reading
        the master (inverter) packets and optionally responding.

        Returns:
            SensorReading with inverter measurements
        """
        try:
            if not self._serial:
                return SensorReading(
                    sensor_id=self._sensor_id,
                    timestamp=datetime.now(),
                    measurements={},
                    error="Serial port not initialized"
                )

            # Clear any stale data
            self._serial.reset_input_buffer()

            # Wait for and read inverter packet
            # Look for start of packet by finding valid status byte
            packet_data = bytearray()
            timeout_start = time.time()

            while len(packet_data) < self.PACKET_SIZE:
                if time.time() - timeout_start > 2.0:  # 2 second timeout
                    return SensorReading(
                        sensor_id=self._sensor_id,
                        timestamp=datetime.now(),
                        measurements={},
                        error="Timeout waiting for inverter packet"
                    )

                # Read available bytes
                available = self._serial.in_waiting
                if available > 0:
                    data = self._serial.read(available)
                    packet_data.extend(data)

            # Extract first complete packet
            packet = bytes(packet_data[:self.PACKET_SIZE])

            # Parse packet
            measurements = self._parse_inverter_packet(packet)

            # If we have pending commands, send remote packet
            if self._pending_inverter_toggle or self._pending_charger_toggle:
                # Wait for slave delay
                import asyncio
                await asyncio.sleep(self.SLAVE_DELAY)

                # Build and send remote packet
                remote_packet = self._build_remote_packet()
                self._serial.write(remote_packet)
                logger.debug("Sent remote command packet")

            # Cache packet info
            self._last_packet = packet
            self._last_packet_time = time.time()

            return SensorReading(
                sensor_id=self._sensor_id,
                timestamp=datetime.now(),
                measurements=measurements
            )

        except Exception as e:
            logger.exception(f"Error reading Magnum RS-485: {e}")
            return SensorReading(
                sensor_id=self._sensor_id,
                timestamp=datetime.now(),
                measurements={},
                error=str(e)
            )

    async def shutdown(self) -> None:
        """Close serial port."""
        try:
            if self._serial and self._serial.is_open:
                self._serial.close()
                self._serial = None
                logger.info("Magnum RS-485 sensor shutdown complete")
        except Exception as e:
            logger.warning(f"Error shutting down Magnum RS-485 sensor: {e}")

    async def health_check(self) -> bool:
        """
        Check if RS-485 communication is working.

        Returns:
            True if we can read data from the bus
        """
        try:
            if not self._serial or not self._serial.is_open:
                return False

            # Check if we have recent packet data
            if self._last_packet and (time.time() - self._last_packet_time) < 5.0:
                return True

            # Try to read a packet
            self._serial.reset_input_buffer()
            available = self._serial.in_waiting

            return available > 0 or self._serial.is_open

        except Exception as e:
            logger.debug(f"Magnum RS-485 health check failed: {e}")
            return False

    # Control methods

    async def toggle_inverter(self) -> bool:
        """
        Toggle inverter on/off state.

        This sets a flag that will be sent in the next remote packet.
        The actual toggle happens on the next read() call.

        Returns:
            True if command was queued successfully
        """
        try:
            self._pending_inverter_toggle = True
            logger.info("Inverter toggle command queued")
            return True
        except Exception as e:
            logger.error(f"Failed to queue inverter toggle: {e}")
            return False

    async def toggle_charger(self) -> bool:
        """
        Toggle charger on/off state.

        This sets a flag that will be sent in the next remote packet.
        The actual toggle happens on the next read() call.

        Returns:
            True if command was queued successfully
        """
        try:
            self._pending_charger_toggle = True
            logger.info("Charger toggle command queued")
            return True
        except Exception as e:
            logger.error(f"Failed to queue charger toggle: {e}")
            return False

    async def turn_inverter_on(self) -> bool:
        """
        Turn inverter on.

        Note: This toggles the state, so it should only be called when
        inverter is currently off.

        Returns:
            True if command was queued successfully
        """
        return await self.toggle_inverter()

    async def turn_inverter_off(self) -> bool:
        """
        Turn inverter off.

        Note: This toggles the state, so it should only be called when
        inverter is currently on.

        Returns:
            True if command was queued successfully
        """
        return await self.toggle_inverter()

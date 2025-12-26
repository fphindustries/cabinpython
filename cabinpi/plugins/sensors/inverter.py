"""
Magnum inverter sensor plugin (continuous monitoring).

This plugin continuously reads data from a Magnum inverter via RS232 serial
using the pymagnum library. It aggregates voltage, current, and temperature
readings (min/max/avg) and generates events for mode changes and faults.

Hardware:
- Serial port: /dev/ttyUSB1 or similar (RS232)
- Magnum inverter with remote control panel

Readings from INVERTER device:
- mode: Operating mode (0=Standby, 1=Invert, 2=Charge, 3=Sell)
- fault: Fault code (0=no fault)
- vdc: DC battery voltage
- adc: AC output current
- VACout: AC output voltage
- VACin: AC input voltage
- invled: Inverter LED status (0=off, 1=on)
- chgled: Charger LED status (0=off, 1=on)
- bat: Battery temperature (°C)
- tfmr: Transformer temperature (°C)
- fet: FET temperature (°C)
- AACin: AC input current
- AACout: AC output current
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from collections import deque

from pymagnum import Magnum

from cabinpi.core.protocols import SensorPlugin
from cabinpi.core.models import SensorReading, SensorType, Event

logger = logging.getLogger(__name__)


class ValueAggregator:
    """Aggregates values over a time window (min/max/avg)."""

    def __init__(self, window_size: int = 60):
        """
        Initialize aggregator.

        Args:
            window_size: Number of samples to keep for aggregation
        """
        self.window_size = window_size
        self.values: deque = deque(maxlen=window_size)

    def add(self, value: Optional[float]) -> None:
        """Add a value to the window."""
        if value is not None:
            self.values.append(value)

    def get_min(self) -> Optional[float]:
        """Get minimum value in window."""
        return min(self.values) if self.values else None

    def get_max(self) -> Optional[float]:
        """Get maximum value in window."""
        return max(self.values) if self.values else None

    def get_avg(self) -> Optional[float]:
        """Get average value in window."""
        if not self.values:
            return None
        return sum(self.values) / len(self.values)

    def reset(self) -> None:
        """Clear the window."""
        self.values.clear()


class InverterSensor:
    """
    Magnum inverter sensor implementation (continuous monitoring).

    Implements the SensorPlugin protocol for reading inverter status
    and measurements via RS232 serial with continuous monitoring.

    Configuration example:
        inverter:
          enabled: true
          module: cabinpi.plugins.sensors.inverter
          type: continuous
          config:
            port: /dev/ttyUSB1
            timeout: 3
            poll_interval: 2        # Read from inverter every 2 seconds
            aggregate_interval: 60  # Report aggregated values every 60 seconds
            window_size: 30         # Keep 30 samples for aggregation
    """

    # Inverter mode names (from pymagnum documentation)
    MODE_NAMES = {
        0: "Standby",
        1: "Invert",
        2: "Charge",
        3: "Sell"
    }

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
        self._poll_interval: float = 2.0      # How often to poll inverter
        self._aggregate_interval: float = 60.0  # How often to report aggregated values
        self._window_size: int = 30           # Number of samples to aggregate

        # Aggregators for voltage, current, temperature
        self._vdc_agg = ValueAggregator(self._window_size)
        self._vac_out_agg = ValueAggregator(self._window_size)
        self._vac_in_agg = ValueAggregator(self._window_size)
        self._aac_out_agg = ValueAggregator(self._window_size)
        self._aac_in_agg = ValueAggregator(self._window_size)
        self._bat_temp_agg = ValueAggregator(self._window_size)
        self._tfmr_temp_agg = ValueAggregator(self._window_size)
        self._fet_temp_agg = ValueAggregator(self._window_size)

        # State tracking for event generation
        self._last_mode: Optional[int] = None
        self._last_fault: Optional[int] = None

        # Continuous monitoring
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._last_reading: Optional[SensorReading] = None

        # Event callback (set by sensor manager)
        self._event_callback: Optional[callable] = None

    @property
    def sensor_id(self) -> str:
        """Return the sensor ID."""
        return self._sensor_id

    @property
    def sensor_type(self) -> SensorType:
        """Return sensor type (continuous)."""
        return SensorType.CONTINUOUS

    def set_event_callback(self, callback: callable) -> None:
        """
        Set callback for event generation.

        Args:
            callback: Function to call with Event objects
        """
        self._event_callback = callback

    async def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the inverter connection and start continuous monitoring.

        Args:
            config: Configuration dict with:
                - port: Serial port (e.g., /dev/ttyUSB1)
                - timeout: Read timeout in seconds (default: 3)
                - poll_interval: Seconds between inverter polls (default: 2)
                - aggregate_interval: Seconds between aggregated reports (default: 60)
                - window_size: Number of samples to aggregate (default: 30)

        Returns:
            True if initialization succeeded
        """
        try:
            # Get configuration
            self._port = config.get("port", "/dev/ttyUSB1")
            self._timeout = config.get("timeout", 3)
            self._poll_interval = config.get("poll_interval", 2.0)
            self._aggregate_interval = config.get("aggregate_interval", 60.0)
            self._window_size = config.get("window_size", 30)

            # Recreate aggregators with configured window size
            self._vdc_agg = ValueAggregator(self._window_size)
            self._vac_out_agg = ValueAggregator(self._window_size)
            self._vac_in_agg = ValueAggregator(self._window_size)
            self._aac_out_agg = ValueAggregator(self._window_size)
            self._aac_in_agg = ValueAggregator(self._window_size)
            self._bat_temp_agg = ValueAggregator(self._window_size)
            self._tfmr_temp_agg = ValueAggregator(self._window_size)
            self._fet_temp_agg = ValueAggregator(self._window_size)

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

            logger.info(
                f"Inverter sensor initialized on {self._port} "
                f"(poll={self._poll_interval}s, aggregate={self._aggregate_interval}s)"
            )

            # Start continuous monitoring
            self._running = True
            self._monitor_task = asyncio.create_task(self._continuous_monitor())

            return True

        except Exception as e:
            logger.exception(f"Failed to initialize inverter sensor: {e}")
            return False

    async def _continuous_monitor(self) -> None:
        """
        Continuous monitoring loop.

        Polls the inverter at poll_interval and aggregates values.
        Generates events for mode changes and faults.
        """
        logger.info("Starting continuous inverter monitoring")
        last_aggregate = datetime.now()

        while self._running:
            try:
                # Read from inverter
                raw_data = await self._read_inverter()

                if raw_data:
                    # Add values to aggregators
                    self._vdc_agg.add(raw_data.get('vdc'))
                    self._vac_out_agg.add(raw_data.get('VACout'))
                    self._vac_in_agg.add(raw_data.get('VACin'))
                    self._aac_out_agg.add(raw_data.get('AACout'))
                    self._aac_in_agg.add(raw_data.get('AACin'))
                    self._bat_temp_agg.add(raw_data.get('bat'))
                    self._tfmr_temp_agg.add(raw_data.get('tfmr'))
                    self._fet_temp_agg.add(raw_data.get('fet'))

                    # Check for mode changes
                    current_mode = raw_data.get('mode')
                    if current_mode is not None and current_mode != self._last_mode:
                        if self._last_mode is not None:  # Skip first reading
                            self._emit_event(Event(
                                event_type="inverter_mode_change",
                                severity="info",
                                sensor_id=self._sensor_id,
                                message=f"Inverter mode changed: {self.MODE_NAMES.get(self._last_mode, 'Unknown')} → {self.MODE_NAMES.get(current_mode, 'Unknown')}",
                                data={
                                    'old_mode': self._last_mode,
                                    'new_mode': current_mode,
                                    'old_mode_name': self.MODE_NAMES.get(self._last_mode, 'Unknown'),
                                    'new_mode_name': self.MODE_NAMES.get(current_mode, 'Unknown')
                                }
                            ))
                        self._last_mode = current_mode

                    # Check for faults
                    current_fault = raw_data.get('fault', 0)
                    if current_fault != 0 and current_fault != self._last_fault:
                        self._emit_event(Event(
                            event_type="inverter_fault",
                            severity="error",
                            sensor_id=self._sensor_id,
                            message=f"Inverter fault detected: code {current_fault}",
                            data={'fault_code': current_fault},
                            notify=True
                        ))
                        self._last_fault = current_fault
                    elif current_fault == 0 and self._last_fault != 0:
                        # Fault cleared
                        self._emit_event(Event(
                            event_type="inverter_fault_cleared",
                            severity="info",
                            sensor_id=self._sensor_id,
                            message="Inverter fault cleared",
                            data={'previous_fault_code': self._last_fault}
                        ))
                        self._last_fault = 0

                # Check if it's time to report aggregated values
                now = datetime.now()
                if (now - last_aggregate).total_seconds() >= self._aggregate_interval:
                    self._last_reading = self._create_aggregated_reading(raw_data)
                    last_aggregate = now

                # Wait before next poll
                await asyncio.sleep(self._poll_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in continuous monitor: {e}")
                await asyncio.sleep(self._poll_interval)

        logger.info("Continuous inverter monitoring stopped")

    async def _read_inverter(self) -> Optional[Dict[str, Any]]:
        """
        Read raw data from inverter.

        Returns:
            Dictionary of inverter data or None on error
        """
        try:
            if not self._magnum:
                return None

            # Get all devices
            devices = self._magnum.getDevices()

            # Find the inverter device
            inverter = next(
                (d for d in devices if d.get('device') == 'INVERTER'),
                None
            )

            if inverter and 'data' in inverter:
                return inverter['data']

            return None

        except Exception as e:
            logger.debug(f"Error reading inverter: {e}")
            return None

    def _create_aggregated_reading(self, latest_raw: Optional[Dict[str, Any]]) -> SensorReading:
        """
        Create a sensor reading with aggregated values.

        Args:
            latest_raw: Latest raw reading for non-aggregated fields

        Returns:
            SensorReading with aggregated measurements
        """
        measurements = {}

        # Current state values (from latest reading)
        if latest_raw:
            measurements['InverterMode'] = latest_raw.get('mode')
            measurements['InverterFault'] = latest_raw.get('fault', 0)
            measurements['InverterOn'] = latest_raw.get('invled')
            measurements['ChargerOn'] = latest_raw.get('chgled')

            # Add mode name for convenience
            if 'mode' in latest_raw:
                measurements['InverterModeName'] = self.MODE_NAMES.get(
                    latest_raw['mode'], 'Unknown'
                )

        # Aggregated voltage readings (VDC, VACout, VACin)
        vdc_min = self._vdc_agg.get_min()
        vdc_max = self._vdc_agg.get_max()
        vdc_avg = self._vdc_agg.get_avg()
        if vdc_avg is not None:
            measurements['Invertervdc'] = round(vdc_avg, 2)
            measurements['vdc_min'] = round(vdc_min, 2)
            measurements['vdc_max'] = round(vdc_max, 2)

        vac_out_min = self._vac_out_agg.get_min()
        vac_out_max = self._vac_out_agg.get_max()
        vac_out_avg = self._vac_out_agg.get_avg()
        if vac_out_avg is not None:
            measurements['InverterVACOut'] = round(vac_out_avg, 2)
            measurements['VACout_min'] = round(vac_out_min, 2)
            measurements['VACout_max'] = round(vac_out_max, 2)

        vac_in_avg = self._vac_in_agg.get_avg()
        if vac_in_avg is not None:
            measurements['VACin'] = round(vac_in_avg, 2)
            measurements['VACin_min'] = round(self._vac_in_agg.get_min(), 2)
            measurements['VACin_max'] = round(self._vac_in_agg.get_max(), 2)

        # Aggregated current readings (AACout, AACin)
        aac_out_avg = self._aac_out_agg.get_avg()
        if aac_out_avg is not None:
            measurements['InverterAACOut'] = round(aac_out_avg, 2)
            measurements['AACout_min'] = round(self._aac_out_agg.get_min(), 2)
            measurements['AACout_max'] = round(self._aac_out_agg.get_max(), 2)

        aac_in_avg = self._aac_in_agg.get_avg()
        if aac_in_avg is not None:
            measurements['AACin'] = round(aac_in_avg, 2)
            measurements['AACin_min'] = round(self._aac_in_agg.get_min(), 2)
            measurements['AACin_max'] = round(self._aac_in_agg.get_max(), 2)

        # Aggregated temperature readings (bat, tfmr, fet)
        bat_temp_avg = self._bat_temp_agg.get_avg()
        if bat_temp_avg is not None:
            measurements['battery_temp_c'] = round(bat_temp_avg, 2)
            measurements['battery_temp_min'] = round(self._bat_temp_agg.get_min(), 2)
            measurements['battery_temp_max'] = round(self._bat_temp_agg.get_max(), 2)

        tfmr_temp_avg = self._tfmr_temp_agg.get_avg()
        if tfmr_temp_avg is not None:
            measurements['transformer_temp_c'] = round(tfmr_temp_avg, 2)
            measurements['transformer_temp_min'] = round(self._tfmr_temp_agg.get_min(), 2)
            measurements['transformer_temp_max'] = round(self._tfmr_temp_agg.get_max(), 2)

        fet_temp_avg = self._fet_temp_agg.get_avg()
        if fet_temp_avg is not None:
            measurements['fet_temp_c'] = round(fet_temp_avg, 2)
            measurements['fet_temp_min'] = round(self._fet_temp_agg.get_min(), 2)
            measurements['fet_temp_max'] = round(self._fet_temp_agg.get_max(), 2)

        return SensorReading(
            sensor_id=self._sensor_id,
            timestamp=datetime.now(),
            measurements=measurements,
            metadata={
                'poll_interval': self._poll_interval,
                'aggregate_interval': self._aggregate_interval,
                'samples': len(self._vdc_agg.values)
            }
        )

    def _emit_event(self, event: Event) -> None:
        """
        Emit an event via callback.

        Args:
            event: Event to emit
        """
        if self._event_callback:
            try:
                self._event_callback(event)
            except Exception as e:
                logger.error(f"Error emitting event: {e}")
        else:
            logger.warning(f"No event callback set, event not emitted: {event}")

    async def read(self) -> SensorReading:
        """
        Return the latest aggregated reading.

        For continuous sensors, the read() method returns cached data
        from the background monitoring task.

        Returns:
            SensorReading with aggregated measurements
        """
        if self._last_reading:
            return self._last_reading

        # No reading yet, return empty
        return SensorReading(
            sensor_id=self._sensor_id,
            timestamp=datetime.now(),
            measurements={},
            error="No data available yet (monitoring starting up)"
        )

    async def shutdown(self) -> None:
        """Stop continuous monitoring and close inverter connection."""
        try:
            # Stop monitoring loop
            self._running = False

            if self._monitor_task:
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass

            # Cleanup pymagnum reference
            if self._magnum:
                self._magnum = None

            logger.info("Inverter sensor shutdown complete")

        except Exception as e:
            logger.warning(f"Error shutting down inverter: {e}")

    async def health_check(self) -> bool:
        """
        Check if inverter is responsive.

        Returns:
            True if we have recent data from the monitoring loop
        """
        try:
            # Check if monitoring task is running
            if not self._running or not self._monitor_task or self._monitor_task.done():
                return False

            # Check if we have recent data (within 2x poll interval)
            if self._last_reading:
                age = (datetime.now() - self._last_reading.timestamp).total_seconds()
                return age < (self._poll_interval * 2)

            return False

        except Exception as e:
            logger.debug(f"Inverter health check failed: {e}")
            return False

"""
Sensor lifecycle management for CabinPython v2 daemon.

This module manages the lifecycle of all sensor plugins including:
- Loading and initialization
- Scheduling polling intervals
- Circuit breaker protection
- Health monitoring
- Graceful shutdown
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pybreaker import CircuitBreaker, CircuitBreakerError

from cabinpi.core.protocols import SensorPlugin
from cabinpi.core.models import SensorReading, SensorType, Event, HealthStatus
from cabinpi.managers.plugin_loader import PluginLoader, PluginLoadError

logger = logging.getLogger(__name__)


class SensorManager:
    """
    Manages the lifecycle of all sensor plugins.

    Responsibilities:
    - Load sensor plugins from configuration
    - Initialize sensors with their configs
    - Schedule polling for POLLING and API sensors
    - Wrap sensors with circuit breakers for fault tolerance
    - Coordinate sensor readings
    - Track sensor health status
    - Handle graceful shutdown

    Example usage:
        >>> manager = SensorManager(scheduler, config, event_callback)
        >>> await manager.initialize()
        >>> await manager.start()
        >>> # ... daemon runs ...
        >>> await manager.shutdown()
    """

    def __init__(
        self,
        scheduler: AsyncIOScheduler,
        config: Dict[str, Any],
        on_reading: Optional[Callable[[SensorReading], None]] = None,
        on_event: Optional[Callable[[Event], None]] = None,
    ) -> None:
        """
        Initialize the sensor manager.

        Args:
            scheduler: APScheduler instance for scheduling sensor polls
            config: Full configuration dict from config.yaml
            on_reading: Callback when sensor reading is available
            on_event: Callback when sensor generates an event
        """
        self.scheduler = scheduler
        self.config = config
        self.on_reading = on_reading
        self.on_event = on_event

        self.loader = PluginLoader()
        self.sensors: Dict[str, SensorPlugin] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.health_status: Dict[str, HealthStatus] = {}
        self._jobs: Dict[str, str] = {}  # sensor_id -> job_id mapping

        # Circuit breaker configuration
        cb_config = config.get("circuit_breaker", {})
        self.failure_threshold = cb_config.get("failure_threshold", 5)
        self.recovery_timeout = cb_config.get("recovery_timeout", 60)

    async def initialize(self) -> None:
        """
        Load and initialize all enabled sensor plugins.

        Reads sensor configuration, loads plugin modules, creates circuit
        breakers, and initializes each sensor with its config.

        Raises:
            RuntimeError: If no sensors are configured or all fail to load
        """
        sensor_configs = self.config.get("plugins", {}).get("sensors", {})

        if not sensor_configs:
            raise RuntimeError("No sensors configured in config.yaml")

        loaded_count = 0
        for sensor_id, sensor_config in sensor_configs.items():
            if not sensor_config.get("enabled", True):
                logger.info(f"Sensor '{sensor_id}' disabled in configuration, skipping")
                continue

            try:
                # Load the plugin
                plugin = self.loader.load_sensor_plugin(sensor_id, sensor_config)

                # Initialize the plugin
                plugin_config = sensor_config.get("config", {})
                success = await plugin.initialize(plugin_config)

                if not success:
                    logger.error(f"Sensor '{sensor_id}' initialization returned False")
                    self._emit_event(Event(
                        event_type="sensor_init_failed",
                        severity="error",
                        sensor_id=sensor_id,
                        message=f"Sensor '{sensor_id}' initialization failed"
                    ))
                    continue

                # Create circuit breaker for this sensor
                breaker = self._create_circuit_breaker(sensor_id)

                # Store sensor and circuit breaker
                self.sensors[sensor_id] = plugin
                self.circuit_breakers[sensor_id] = breaker

                # Initialize health status
                self.health_status[sensor_id] = HealthStatus(
                    component_id=sensor_id,
                    status="healthy",
                    last_success=datetime.now(),
                    message="Initialized successfully"
                )

                loaded_count += 1
                logger.info(f"Initialized sensor: {sensor_id}")

            except PluginLoadError as e:
                logger.error(f"Failed to load sensor '{sensor_id}': {e}")
                self._emit_event(Event(
                    event_type="sensor_load_failed",
                    severity="error",
                    sensor_id=sensor_id,
                    message=str(e)
                ))
            except Exception as e:
                logger.exception(f"Unexpected error loading sensor '{sensor_id}': {e}")
                self._emit_event(Event(
                    event_type="sensor_load_error",
                    severity="error",
                    sensor_id=sensor_id,
                    message=f"Unexpected error: {e}"
                ))

        if loaded_count == 0:
            raise RuntimeError("No sensors loaded successfully")

        logger.info(f"Sensor manager initialized with {loaded_count} sensors")

    async def start(self) -> None:
        """
        Start scheduling sensor readings.

        Schedules polling jobs for POLLING and API sensors according to
        their configured intervals. CONTINUOUS sensors are not scheduled
        (they manage their own connection lifecycle).
        """
        sensor_configs = self.config.get("plugins", {}).get("sensors", {})
        default_interval = self.config.get("daemon", {}).get("polling_interval", 300)

        for sensor_id, plugin in self.sensors.items():
            # Get sensor-specific config
            sensor_config = sensor_configs.get(sensor_id, {})

            # Only schedule POLLING and API sensors
            if plugin.sensor_type in (SensorType.POLLING, SensorType.API):
                interval = sensor_config.get("interval", default_interval)

                # Schedule the sensor read job
                job = self.scheduler.add_job(
                    self._read_sensor,
                    "interval",
                    seconds=interval,
                    args=[sensor_id],
                    id=f"sensor_{sensor_id}",
                    name=f"Read {sensor_id}",
                    max_instances=1,  # Prevent overlapping reads
                )

                self._jobs[sensor_id] = job.id
                logger.info(f"Scheduled sensor '{sensor_id}' every {interval}s")

            elif plugin.sensor_type == SensorType.CONTINUOUS:
                logger.info(f"Sensor '{sensor_id}' is CONTINUOUS type, not scheduling")
                # TODO: Future work - handle continuous sensors

        logger.info("Sensor scheduling started")

    async def _read_sensor(self, sensor_id: str) -> None:
        """
        Read a sensor with circuit breaker protection.

        Args:
            sensor_id: ID of sensor to read
        """
        plugin = self.sensors.get(sensor_id)
        if not plugin:
            logger.error(f"Sensor '{sensor_id}' not found")
            return

        breaker = self.circuit_breakers[sensor_id]
        health = self.health_status[sensor_id]

        try:
            # Call sensor read through circuit breaker
            reading = await breaker.call_async(plugin.read)

            # Update health status
            health.last_success = datetime.now()
            health.failure_count = 0
            if health.status != "healthy":
                health.status = "healthy"
                health.message = "Recovered"
                logger.info(f"Sensor '{sensor_id}' recovered")
                self._emit_event(Event(
                    event_type="sensor_recovered",
                    severity="info",
                    sensor_id=sensor_id,
                    message=f"Sensor '{sensor_id}' has recovered"
                ))

            # Check if reading is valid
            if not reading.is_valid:
                logger.warning(f"Sensor '{sensor_id}' returned invalid reading: {reading.error}")
                health.failure_count += 1
                health.last_failure = datetime.now()
                health.status = "degraded"
                health.message = reading.error or "Invalid reading"
                return

            # Emit reading to outputs
            if self.on_reading:
                self.on_reading(reading)

        except CircuitBreakerError:
            # Circuit is open - sensor has failed repeatedly
            health.status = "failed"
            health.message = "Circuit breaker open"
            logger.warning(f"Sensor '{sensor_id}' circuit breaker is open")

        except Exception as e:
            # Unexpected error during read
            logger.exception(f"Error reading sensor '{sensor_id}': {e}")
            health.failure_count += 1
            health.last_failure = datetime.now()
            health.status = "degraded"
            health.message = str(e)

            self._emit_event(Event(
                event_type="sensor_read_error",
                severity="warning",
                sensor_id=sensor_id,
                message=f"Read error: {e}",
                data={"error": str(e)}
            ))

    def _create_circuit_breaker(self, sensor_id: str) -> CircuitBreaker:
        """
        Create a circuit breaker for a sensor.

        Args:
            sensor_id: ID of sensor

        Returns:
            Configured CircuitBreaker instance
        """
        def on_open(breaker):
            logger.error(f"Circuit breaker opened for sensor '{sensor_id}'")
            self._emit_event(Event(
                event_type="circuit_breaker_open",
                severity="error",
                sensor_id=sensor_id,
                message=f"Sensor '{sensor_id}' circuit breaker opened after {self.failure_threshold} failures"
            ))

        def on_close(breaker):
            logger.info(f"Circuit breaker closed for sensor '{sensor_id}'")
            self._emit_event(Event(
                event_type="circuit_breaker_closed",
                severity="info",
                sensor_id=sensor_id,
                message=f"Sensor '{sensor_id}' circuit breaker closed"
            ))

        breaker = CircuitBreaker(
            fail_max=self.failure_threshold,
            timeout_duration=self.recovery_timeout,
            name=f"sensor_{sensor_id}",
            listeners=[on_open, on_close]
        )

        return breaker

    def _emit_event(self, event: Event) -> None:
        """
        Emit an event to the event handler.

        Args:
            event: Event to emit
        """
        if self.on_event:
            self.on_event(event)

    async def get_health_status(self) -> List[HealthStatus]:
        """
        Get health status for all sensors.

        Returns:
            List of HealthStatus objects
        """
        # Optionally run health checks
        for sensor_id, plugin in self.sensors.items():
            try:
                is_healthy = await asyncio.wait_for(
                    plugin.health_check(),
                    timeout=5.0
                )
                if not is_healthy:
                    self.health_status[sensor_id].status = "degraded"
                    self.health_status[sensor_id].message = "Health check failed"
            except asyncio.TimeoutError:
                self.health_status[sensor_id].status = "degraded"
                self.health_status[sensor_id].message = "Health check timeout"
            except Exception as e:
                logger.exception(f"Error checking health of '{sensor_id}': {e}")

        return list(self.health_status.values())

    async def shutdown(self) -> None:
        """
        Gracefully shutdown all sensors.

        Removes scheduled jobs and calls shutdown on each sensor plugin.
        """
        logger.info("Shutting down sensor manager")

        # Remove scheduled jobs
        for sensor_id, job_id in self._jobs.items():
            try:
                self.scheduler.remove_job(job_id)
                logger.debug(f"Removed job for sensor '{sensor_id}'")
            except Exception as e:
                logger.warning(f"Error removing job for '{sensor_id}': {e}")

        self._jobs.clear()

        # Shutdown each sensor
        for sensor_id, plugin in self.sensors.items():
            try:
                await plugin.shutdown()
                logger.info(f"Shutdown sensor: {sensor_id}")
            except Exception as e:
                logger.exception(f"Error shutting down sensor '{sensor_id}': {e}")

        self.sensors.clear()
        self.circuit_breakers.clear()
        self.health_status.clear()

        logger.info("Sensor manager shutdown complete")

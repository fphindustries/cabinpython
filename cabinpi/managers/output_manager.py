"""
Output lifecycle management for CabinPython v2 daemon.

This module manages the lifecycle of all output plugins including:
- Loading and initialization
- Routing data to appropriate outputs
- Retry logic for failed writes
- Health monitoring
- Graceful shutdown
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_result,
)

from cabinpi.core.protocols import OutputPlugin
from cabinpi.core.models import SensorReading, Event, HealthStatus
from cabinpi.managers.plugin_loader import PluginLoader, PluginLoadError

logger = logging.getLogger(__name__)


class OutputManager:
    """
    Manages the lifecycle of all output plugins.

    Responsibilities:
    - Load output plugins from configuration
    - Initialize outputs with their configs
    - Route SensorReading to measurement_storage outputs
    - Route Event to event_log and notification outputs
    - Retry failed writes with exponential backoff
    - Track output health status
    - Handle graceful shutdown

    Example usage:
        >>> manager = OutputManager(config)
        >>> await manager.initialize()
        >>> await manager.write_reading(sensor_reading)
        >>> await manager.write_event(event)
        >>> await manager.shutdown()
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize the output manager.

        Args:
            config: Full configuration dict from config.yaml
        """
        self.config = config
        self.loader = PluginLoader()

        # Outputs by type
        self.measurement_outputs: Dict[str, OutputPlugin] = {}
        self.event_log_outputs: Dict[str, OutputPlugin] = {}
        self.notification_outputs: Dict[str, OutputPlugin] = {}

        # Health tracking
        self.health_status: Dict[str, HealthStatus] = {}

    async def initialize(self) -> None:
        """
        Load and initialize all enabled output plugins.

        Reads output configuration, loads plugin modules, and initializes
        each output with its config. Organizes outputs by type for routing.

        Raises:
            RuntimeError: If no outputs are configured
        """
        output_configs = self.config.get("plugins", {}).get("outputs", {})

        if not output_configs:
            logger.warning("No outputs configured in config.yaml")
            return

        loaded_count = 0
        for output_id, output_config in output_configs.items():
            if not output_config.get("enabled", True):
                logger.info(f"Output '{output_id}' disabled in configuration, skipping")
                continue

            try:
                # Load the plugin
                plugin = self.loader.load_output_plugin(output_id, output_config)

                # Initialize the plugin
                plugin_config = output_config.get("config", {})
                success = await plugin.initialize(plugin_config)

                if not success:
                    logger.error(f"Output '{output_id}' initialization returned False")
                    continue

                # Store output by type
                output_type = plugin.output_type
                if output_type == "measurement_storage":
                    self.measurement_outputs[output_id] = plugin
                elif output_type == "event_log":
                    self.event_log_outputs[output_id] = plugin
                elif output_type == "notification":
                    self.notification_outputs[output_id] = plugin
                else:
                    logger.warning(
                        f"Output '{output_id}' has unknown type '{output_type}', skipping"
                    )
                    continue

                # Initialize health status
                self.health_status[output_id] = HealthStatus(
                    component_id=output_id,
                    status="healthy",
                    message="Initialized successfully"
                )

                loaded_count += 1
                logger.info(f"Initialized output: {output_id} ({output_type})")

            except PluginLoadError as e:
                logger.error(f"Failed to load output '{output_id}': {e}")
            except Exception as e:
                logger.exception(f"Unexpected error loading output '{output_id}': {e}")

        logger.info(
            f"Output manager initialized with {loaded_count} outputs "
            f"({len(self.measurement_outputs)} storage, "
            f"{len(self.event_log_outputs)} event log, "
            f"{len(self.notification_outputs)} notification)"
        )

    async def write_reading(self, reading: SensorReading) -> None:
        """
        Write a sensor reading to all measurement_storage outputs.

        Args:
            reading: SensorReading to write

        Note:
            Writes happen concurrently to all outputs. Failed writes are
            logged but don't prevent other outputs from succeeding.
        """
        if not reading.is_valid:
            logger.debug(f"Skipping invalid reading from '{reading.sensor_id}'")
            return

        if not self.measurement_outputs:
            logger.debug("No measurement storage outputs configured")
            return

        # Write to all measurement outputs concurrently
        tasks = [
            self._write_with_retry(output_id, output, reading)
            for output_id, output in self.measurement_outputs.items()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Log any failures
        for output_id, result in zip(self.measurement_outputs.keys(), results):
            if isinstance(result, Exception):
                logger.error(
                    f"Failed to write reading to '{output_id}': {result}"
                )

    async def write_event(self, event: Event) -> None:
        """
        Write an event to event_log and notification outputs.

        Args:
            event: Event to write

        Note:
            - All events go to event_log outputs
            - Only events with notify=True go to notification outputs
            - Writes happen concurrently
        """
        tasks = []

        # Write to all event log outputs
        for output_id, output in self.event_log_outputs.items():
            tasks.append(
                self._write_with_retry(output_id, output, event)
            )

        # Write to notification outputs if notify flag is set
        if event.notify:
            for output_id, output in self.notification_outputs.items():
                tasks.append(
                    self._write_with_retry(output_id, output, event)
                )

        if not tasks:
            logger.debug("No outputs configured for events")
            return

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Log any failures
        all_output_ids = list(self.event_log_outputs.keys())
        if event.notify:
            all_output_ids.extend(self.notification_outputs.keys())

        for output_id, result in zip(all_output_ids, results):
            if isinstance(result, Exception):
                logger.error(
                    f"Failed to write event to '{output_id}': {result}"
                )

    async def _write_with_retry(
        self,
        output_id: str,
        output: OutputPlugin,
        data: Any
    ) -> bool:
        """
        Write data to output with retry logic.

        Uses exponential backoff for retries. Updates health status on
        success/failure.

        Args:
            output_id: ID of output
            output: Output plugin instance
            data: Data to write (SensorReading or Event)

        Returns:
            True if write succeeded (eventually), False otherwise
        """
        health = self.health_status[output_id]

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_result(lambda x: x is False),
            reraise=True,
        )
        async def _write():
            return await output.write(data)

        try:
            success = await _write()

            if success:
                # Update health status
                if health.status != "healthy":
                    health.status = "healthy"
                    health.message = "Recovered"
                    health.failure_count = 0
                    logger.info(f"Output '{output_id}' recovered")

                return True
            else:
                # Write returned False (non-exception failure)
                health.failure_count += 1
                health.status = "degraded"
                health.message = "Write failed"
                logger.warning(f"Output '{output_id}' write failed")
                return False

        except Exception as e:
            # Exception during write
            logger.exception(f"Error writing to output '{output_id}': {e}")
            health.failure_count += 1
            health.status = "degraded"
            health.message = str(e)
            return False

    async def get_health_status(self) -> List[HealthStatus]:
        """
        Get health status for all outputs.

        Returns:
            List of HealthStatus objects
        """
        return list(self.health_status.values())

    async def shutdown(self) -> None:
        """
        Gracefully shutdown all outputs.

        Calls shutdown on each output plugin to flush buffers and close
        connections.
        """
        logger.info("Shutting down output manager")

        all_outputs = {
            **self.measurement_outputs,
            **self.event_log_outputs,
            **self.notification_outputs,
        }

        for output_id, plugin in all_outputs.items():
            try:
                await plugin.shutdown()
                logger.info(f"Shutdown output: {output_id}")
            except Exception as e:
                logger.exception(f"Error shutting down output '{output_id}': {e}")

        self.measurement_outputs.clear()
        self.event_log_outputs.clear()
        self.notification_outputs.clear()
        self.health_status.clear()

        logger.info("Output manager shutdown complete")

"""
Main daemon class for CabinPython v2.

This module contains the SensorDaemon class which orchestrates the entire
monitoring system including sensor polling, output handling, and event management.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from cabinpi.core.models import SensorReading, Event
from cabinpi.core.event_detector import EventDetector
from cabinpi.managers import SensorManager, OutputManager
from cabinpi.signal_handler import SignalHandler

logger = logging.getLogger(__name__)


class SensorDaemon:
    """
    Main daemon class for CabinPython v2.

    Orchestrates:
    - Sensor polling via SensorManager
    - Output handling via OutputManager
    - Event generation and routing
    - Signal handling for shutdown/reload
    - Health monitoring
    - systemd watchdog integration

    Example usage:
        >>> daemon = SensorDaemon(config)
        >>> await daemon.initialize()
        >>> await daemon.run()
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize the daemon.

        Args:
            config: Full configuration dict from config.yaml
        """
        self.config = config
        self.running = False

        # Create scheduler
        self.scheduler = AsyncIOScheduler()

        # Create managers (initialized later)
        self.sensor_manager: Optional[SensorManager] = None
        self.output_manager: Optional[OutputManager] = None
        self.event_detector: Optional[EventDetector] = None

        # Create signal handler
        self.signal_handler = SignalHandler(
            on_shutdown=self._request_shutdown,
            on_reload=self._request_reload,
        )

        # State
        self._reload_requested = False
        self._shutdown_requested = False

        # Watchdog
        self._watchdog_enabled = config.get("daemon", {}).get("enable_watchdog", True)
        self._watchdog = None

    async def initialize(self) -> None:
        """
        Initialize all daemon components.

        - Creates sensor and output managers
        - Initializes all plugins
        - Starts scheduler
        - Sets up signal handlers
        - Initializes systemd watchdog

        Raises:
            RuntimeError: If initialization fails
        """
        logger.info("Initializing CabinPython v2 daemon")

        try:
            # Initialize output manager first (for event logging)
            self.output_manager = OutputManager(self.config)
            await self.output_manager.initialize()

            # Initialize event detector
            self.event_detector = EventDetector(
                config=self.config,
                on_event=self._handle_event
            )

            # Initialize sensor manager (with callbacks to outputs)
            self.sensor_manager = SensorManager(
                scheduler=self.scheduler,
                config=self.config,
                on_reading=self._handle_reading,
                on_event=self._handle_event,
            )
            await self.sensor_manager.initialize()

            # Start the scheduler
            self.scheduler.start()
            logger.info("Scheduler started")

            # Setup signal handlers
            self.signal_handler.setup()

            # Initialize watchdog if enabled
            if self._watchdog_enabled:
                self._init_watchdog()

            logger.info("Daemon initialization complete")

        except Exception as e:
            logger.exception(f"Failed to initialize daemon: {e}")
            raise RuntimeError(f"Daemon initialization failed: {e}") from e

    def _init_watchdog(self) -> None:
        """
        Initialize systemd watchdog.

        Sets up periodic watchdog pings to systemd.
        """
        try:
            from systemd import daemon as sd_daemon

            # Check if watchdog is enabled in systemd
            watchdog_usec = sd_daemon.watchdog_enabled()
            if watchdog_usec:
                # Convert to seconds and ping at half the interval
                watchdog_sec = watchdog_usec / 1_000_000
                ping_interval = watchdog_sec / 2

                logger.info(
                    f"Watchdog enabled: {watchdog_sec}s timeout, "
                    f"pinging every {ping_interval}s"
                )

                # Schedule watchdog pings
                self.scheduler.add_job(
                    self._ping_watchdog,
                    "interval",
                    seconds=ping_interval,
                    id="watchdog_ping",
                    name="Systemd Watchdog Ping",
                )

                self._watchdog = sd_daemon
            else:
                logger.info("Watchdog not enabled in systemd")

        except ImportError:
            logger.warning("systemd-python not available, watchdog disabled")
        except Exception as e:
            logger.warning(f"Failed to initialize watchdog: {e}")

    def _ping_watchdog(self) -> None:
        """Send watchdog ping to systemd."""
        if self._watchdog:
            self._watchdog.notify("WATCHDOG=1")
            logger.debug("Sent watchdog ping")

    async def run(self) -> None:
        """
        Run the daemon main loop.

        This is the main entry point. It:
        1. Starts sensor polling
        2. Waits for shutdown signal
        3. Handles graceful shutdown

        Does not return until shutdown is complete.
        """
        logger.info("Starting CabinPython v2 daemon")
        self.running = True

        try:
            # Notify systemd we're ready
            self._notify_systemd_ready()

            # Start sensor polling
            await self.sensor_manager.start()

            # Log startup event
            self._handle_event(Event(
                event_type="daemon_started",
                severity="info",
                message="CabinPython v2 daemon started successfully"
            ))

            # Main loop - wait for signals
            while self.running:
                # Wait for shutdown signal (or timeout to check reload)
                try:
                    await asyncio.wait_for(
                        self.signal_handler.wait_for_shutdown(),
                        timeout=5.0
                    )
                    # Shutdown signal received
                    break
                except asyncio.TimeoutError:
                    # No signal, check for reload
                    if await self.signal_handler.wait_for_reload():
                        await self._reload_config()

            logger.info("Daemon main loop exiting")

        except Exception as e:
            logger.exception(f"Fatal error in daemon main loop: {e}")
            self._handle_event(Event(
                event_type="daemon_error",
                severity="critical",
                message=f"Fatal daemon error: {e}",
                notify=True
            ))
            raise
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """
        Gracefully shutdown the daemon.

        Stops sensors, flushes outputs, and cleans up resources.
        """
        if not self.running:
            return

        logger.info("Shutting down daemon")
        self.running = False

        try:
            # Log shutdown event
            self._handle_event(Event(
                event_type="daemon_stopping",
                severity="info",
                message="CabinPython v2 daemon shutting down"
            ))

            # Stop sensor manager
            if self.sensor_manager:
                await self.sensor_manager.shutdown()

            # Stop scheduler
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)
                logger.info("Scheduler stopped")

            # Shutdown output manager (flush buffers)
            if self.output_manager:
                await self.output_manager.shutdown()

            # Cleanup signal handlers
            self.signal_handler.cleanup()

            # Notify systemd we're stopping
            self._notify_systemd_stopping()

            logger.info("Daemon shutdown complete")

        except Exception as e:
            logger.exception(f"Error during shutdown: {e}")

    def _request_shutdown(self) -> None:
        """Request daemon shutdown (called by signal handler)."""
        logger.info("Shutdown requested")
        self._shutdown_requested = True
        self.running = False

    def _request_reload(self) -> None:
        """Request configuration reload (called by signal handler)."""
        logger.info("Configuration reload requested")
        self._reload_requested = True

    async def _reload_config(self) -> None:
        """
        Reload configuration and restart managers.

        Reloads config.yaml and reinitializes all managers with new configuration.
        Useful for adding/removing sensors or changing thresholds without restart.
        """
        logger.info("Reloading configuration")
        self._reload_requested = False

        try:
            # Reload configuration from file
            from pathlib import Path
            import yaml
            from dotenv import load_dotenv
            import os
            import re

            # Reload environment variables
            env_path = Path(__file__).parent.parent / ".env"
            if env_path.exists():
                load_dotenv(env_path, override=True)

            # Reload YAML config
            config_file = Path(__file__).parent.parent / "config.yaml"
            if not config_file.exists():
                logger.error("config.yaml not found, cannot reload")
                return

            with open(config_file, 'r') as f:
                new_config = yaml.safe_load(f)

            # Substitute environment variables
            def substitute_env_vars(obj):
                if isinstance(obj, dict):
                    return {key: substitute_env_vars(value) for key, value in obj.items()}
                elif isinstance(obj, list):
                    return [substitute_env_vars(item) for item in obj]
                elif isinstance(obj, str):
                    pattern = re.compile(r'\$\{([^}]+)\}')
                    matches = pattern.findall(obj)
                    for var_name in matches:
                        var_value = os.environ.get(var_name, "")
                        obj = obj.replace(f"${{{var_name}}}", var_value)
                    return obj
                else:
                    return obj

            new_config = substitute_env_vars(new_config)
            self.config = new_config

            # Shutdown and reinitialize managers
            logger.info("Shutting down managers for reload")

            if self.sensor_manager:
                await self.sensor_manager.shutdown()

            if self.output_manager:
                await self.output_manager.shutdown()

            # Reinitialize with new config
            logger.info("Reinitializing with new configuration")

            self.output_manager = OutputManager(self.config)
            await self.output_manager.initialize()

            self.event_detector = EventDetector(
                config=self.config,
                on_event=self._handle_event
            )

            self.sensor_manager = SensorManager(
                scheduler=self.scheduler,
                config=self.config,
                on_reading=self._handle_reading,
                on_event=self._handle_event,
            )
            await self.sensor_manager.initialize()

            # Restart sensor polling
            await self.sensor_manager.start()

            self._handle_event(Event(
                event_type="config_reloaded",
                severity="info",
                message="Configuration reloaded successfully"
            ))
            logger.info("Configuration reload complete")

        except Exception as e:
            logger.exception(f"Error reloading configuration: {e}")
            self._handle_event(Event(
                event_type="config_reload_failed",
                severity="error",
                message=f"Configuration reload failed: {e}",
                notify=True
            ))

    def _handle_reading(self, reading: SensorReading) -> None:
        """
        Handle a sensor reading from SensorManager.

        Routes the reading to output manager for storage and
        processes it through event detector.

        Args:
            reading: SensorReading to process
        """
        # Process through event detector
        if self.event_detector:
            self.event_detector.process_reading(reading)

        # Write to outputs
        if self.output_manager:
            # Schedule the async write
            asyncio.create_task(self.output_manager.write_reading(reading))

    def _handle_event(self, event: Event) -> None:
        """
        Handle an event from anywhere in the system.

        Routes the event to output manager for logging/notification.

        Args:
            event: Event to process
        """
        logger.info(f"Event: {event}")

        if self.output_manager:
            # Schedule the async write
            asyncio.create_task(self.output_manager.write_event(event))

    def _notify_systemd_ready(self) -> None:
        """Notify systemd that daemon is ready."""
        try:
            from systemd import daemon as sd_daemon
            sd_daemon.notify("READY=1")
            logger.info("Notified systemd: READY")
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Failed to notify systemd ready: {e}")

    def _notify_systemd_stopping(self) -> None:
        """Notify systemd that daemon is stopping."""
        try:
            from systemd import daemon as sd_daemon
            sd_daemon.notify("STOPPING=1")
            logger.debug("Notified systemd: STOPPING")
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Failed to notify systemd stopping: {e}")

    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get overall daemon health status.

        Returns:
            Dict with health information for all components
        """
        health = {
            "daemon": {
                "running": self.running,
                "timestamp": datetime.now().isoformat(),
            },
            "sensors": [],
            "outputs": [],
        }

        # Get sensor health
        if self.sensor_manager:
            health["sensors"] = [
                {
                    "id": status.component_id,
                    "status": status.status,
                    "message": status.message,
                    "failure_count": status.failure_count,
                }
                for status in await self.sensor_manager.get_health_status()
            ]

        # Get output health
        if self.output_manager:
            health["outputs"] = [
                {
                    "id": status.component_id,
                    "status": status.status,
                    "message": status.message,
                    "failure_count": status.failure_count,
                }
                for status in await self.output_manager.get_health_status()
            ]

        # Get active alerts
        if self.event_detector:
            health["active_alerts"] = self.event_detector.get_active_alerts()

        return health

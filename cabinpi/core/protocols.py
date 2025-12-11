"""
Plugin protocols for CabinPython v2 daemon.

This module defines the plugin interfaces that all sensors and outputs
must implement. Uses Python Protocol (PEP 544) for structural subtyping.
"""

from typing import Protocol, Dict, Any, runtime_checkable
from cabinpi.core.models import SensorReading, SensorType, Event


@runtime_checkable
class SensorPlugin(Protocol):
    """
    Protocol that all sensor plugins must implement.

    Sensors are responsible for reading data from physical devices or APIs
    and returning standardized SensorReading objects. The daemon handles
    scheduling, error recovery, and circuit breaker logic.

    Example implementation:
        >>> class MySensor:
        ...     @property
        ...     def sensor_id(self) -> str:
        ...         return "my_sensor"
        ...
        ...     @property
        ...     def sensor_type(self) -> SensorType:
        ...         return SensorType.POLLING
        ...
        ...     async def initialize(self, config: Dict[str, Any]) -> bool:
        ...         # Setup connection, load config
        ...         return True
        ...
        ...     async def read(self) -> SensorReading:
        ...         # Read from device
        ...         return SensorReading(...)
        ...
        ...     async def shutdown(self) -> None:
        ...         # Close connections
        ...         pass
        ...
        ...     async def health_check(self) -> bool:
        ...         # Verify sensor is responsive
        ...         return True
    """

    @property
    def sensor_id(self) -> str:
        """
        Unique identifier for this sensor instance.

        Used for configuration lookups, database storage, and event correlation.
        Should match the key in config.yaml under plugins.sensors.

        Returns:
            Unique sensor identifier (e.g., "sht31", "solar_controller")
        """
        ...

    @property
    def sensor_type(self) -> SensorType:
        """
        Connection pattern for this sensor.

        Determines how the sensor manager schedules readings:
        - POLLING: Read at fixed intervals (default)
        - CONTINUOUS: Maintain persistent connection with streaming data
        - API: External API calls (may have rate limits)

        Returns:
            SensorType enum value
        """
        ...

    async def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the sensor with configuration.

        Called once when the daemon starts or when configuration is reloaded.
        Should establish connections, validate config, and prepare for readings.

        Args:
            config: Sensor-specific configuration from config.yaml

        Returns:
            True if initialization succeeded, False otherwise

        Raises:
            May raise exceptions for invalid configuration
        """
        ...

    async def read(self) -> SensorReading:
        """
        Read current sensor values.

        Called by the sensor manager according to the sensor's schedule.
        Should return quickly (< 5 seconds) to avoid blocking other sensors.

        Returns:
            SensorReading with measurements or error information

        Note:
            - If reading fails, return SensorReading with error field set
            - Circuit breaker will handle repeated failures
            - Don't retry within read() - let the circuit breaker manage retries
        """
        ...

    async def shutdown(self) -> None:
        """
        Gracefully shutdown the sensor.

        Called when daemon stops or during configuration reload.
        Should close connections, release resources, and save state if needed.

        Should not raise exceptions - log errors instead.
        """
        ...

    async def health_check(self) -> bool:
        """
        Check if sensor is healthy and responsive.

        Called periodically by health monitoring system.
        Should be faster than read() - just verify basic connectivity.

        Returns:
            True if sensor is healthy, False if degraded/failed

        Note:
            - Keep this lightweight (< 1 second)
            - Don't perform full reads - just verify device responds
        """
        ...


@runtime_checkable
class OutputPlugin(Protocol):
    """
    Protocol that all output plugins must implement.

    Outputs receive data from sensors and events from the event system.
    Three types of outputs:
    - measurement_storage: Store SensorReading objects (database, API)
    - event_log: Store Event objects (database, logging)
    - notification: Send Event notifications (email, SMS, webhooks)

    Example implementation:
        >>> class MyOutput:
        ...     @property
        ...     def output_id(self) -> str:
        ...         return "my_output"
        ...
        ...     @property
        ...     def output_type(self) -> str:
        ...         return "measurement_storage"
        ...
        ...     async def initialize(self, config: Dict[str, Any]) -> bool:
        ...         # Setup database connection, API client, etc.
        ...         return True
        ...
        ...     async def write(self, data: Any) -> bool:
        ...         # Write SensorReading or Event
        ...         return True
        ...
        ...     async def shutdown(self) -> None:
        ...         # Close connections
        ...         pass
    """

    @property
    def output_id(self) -> str:
        """
        Unique identifier for this output instance.

        Used for configuration lookups and logging.
        Should match the key in config.yaml under plugins.outputs.

        Returns:
            Unique output identifier (e.g., "database", "email_alerts")
        """
        ...

    @property
    def output_type(self) -> str:
        """
        Type of output this plugin provides.

        Determines what data is routed to this output:
        - "measurement_storage": Receives SensorReading objects
        - "event_log": Receives Event objects
        - "notification": Receives Event objects (only notify=True events)

        Returns:
            Output type string
        """
        ...

    async def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the output with configuration.

        Called once when the daemon starts or when configuration is reloaded.
        Should establish connections, validate config, and prepare for writes.

        Args:
            config: Output-specific configuration from config.yaml

        Returns:
            True if initialization succeeded, False otherwise

        Raises:
            May raise exceptions for invalid configuration
        """
        ...

    async def write(self, data: Any) -> bool:
        """
        Write data to the output destination.

        Called by output manager with either SensorReading or Event objects
        depending on the output_type.

        Args:
            data: Either SensorReading (for measurement_storage) or Event
                  (for event_log/notification outputs)

        Returns:
            True if write succeeded, False otherwise

        Note:
            - Should be idempotent where possible
            - Handle transient errors gracefully (return False)
            - Output manager will retry on failure
            - Should complete quickly (< 10 seconds)
        """
        ...

    async def shutdown(self) -> None:
        """
        Gracefully shutdown the output.

        Called when daemon stops or during configuration reload.
        Should flush buffers, close connections, and save state if needed.

        Should not raise exceptions - log errors instead.
        """
        ...

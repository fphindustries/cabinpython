"""
MariaDB event log output plugin.

This plugin stores events and alarms to a MariaDB/MySQL database.
Writes to the 'event_log' table for tracking system events, sensor
state changes, and alerts.

Database:
- Host: localhost (configurable)
- Table: event_log
- Schema: id, timestamp, event_type, severity, sensor_id, message, data, notified
"""

import logging
import json
from typing import Dict, Any, Optional

import mysql.connector
from mysql.connector import Error as MySQLError

from cabinpi.core.protocols import OutputPlugin
from cabinpi.core.models import Event

logger = logging.getLogger(__name__)


class MariaDBEventsOutput:
    """
    MariaDB event log output implementation.

    Implements the OutputPlugin protocol for writing events to a
    MariaDB database.

    Configuration example:
        event_log:
          enabled: true
          module: cabinpi.plugins.outputs.mariadb_events
          type: event_log
          config:
            host: localhost
            database: cabinpi
            username: cabinpi
            password: "${DB_PASSWORD}"
            table: event_log
            create_table: true
    """

    def __init__(self, output_id: str, output_type: str) -> None:
        """
        Initialize the MariaDB events output.

        Args:
            output_id: Unique output identifier
            output_type: Output type (should be "event_log")
        """
        self._output_id = output_id
        self._output_type = output_type
        self._connection: Optional[mysql.connector.MySQLConnection] = None
        self._host: str = "localhost"
        self._database: str = "cabinpi"
        self._username: str = "cabinpi"
        self._password: str = ""
        self._table: str = "event_log"
        self._create_table: bool = True

    @property
    def output_id(self) -> str:
        """Return the output ID."""
        return self._output_id

    @property
    def output_type(self) -> str:
        """Return the output type."""
        return self._output_type

    async def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the database connection and create table if needed.

        Args:
            config: Configuration dict with:
                - host: Database host (default: localhost)
                - database: Database name (default: cabinpi)
                - username: Database username
                - password: Database password
                - table: Table name (default: event_log)
                - create_table: Create table if missing (default: true)

        Returns:
            True if initialization succeeded
        """
        try:
            # Get configuration
            self._host = config.get("host", "localhost")
            self._database = config.get("database", "cabinpi")
            self._username = config.get("username", "cabinpi")
            self._password = config.get("password", "")
            self._table = config.get("table", "event_log")
            self._create_table = config.get("create_table", True)

            # Connect to database
            self._connection = mysql.connector.connect(
                host=self._host,
                database=self._database,
                user=self._username,
                password=self._password,
                autocommit=True
            )

            # Create table if requested and it doesn't exist
            if self._create_table:
                self._ensure_table_exists()

            logger.info(
                f"MariaDB events initialized: {self._username}@{self._host}/{self._database}.{self._table}"
            )
            return True

        except MySQLError as e:
            logger.exception(f"Failed to initialize MariaDB events: {e}")
            return False

    def _ensure_table_exists(self) -> None:
        """Create event_log table if it doesn't exist."""
        create_sql = f"""
        CREATE TABLE IF NOT EXISTS {self._table} (
            id INT AUTO_INCREMENT PRIMARY KEY,
            timestamp DATETIME NOT NULL,
            event_type VARCHAR(100) NOT NULL,
            severity VARCHAR(20) NOT NULL,
            sensor_id VARCHAR(100),
            message TEXT,
            data JSON,
            notified BOOLEAN DEFAULT FALSE,
            INDEX idx_timestamp (timestamp),
            INDEX idx_event_type (event_type),
            INDEX idx_severity (severity),
            INDEX idx_sensor_id (sensor_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """

        try:
            cursor = self._connection.cursor()
            cursor.execute(create_sql)
            cursor.close()
            logger.info(f"Ensured {self._table} table exists")
        except MySQLError as e:
            logger.warning(f"Error creating {self._table} table: {e}")

    async def write(self, data: Any) -> bool:
        """
        Write an event to the database.

        Args:
            data: Event object to write

        Returns:
            True if write succeeded
        """
        if not isinstance(data, Event):
            logger.error(f"Expected Event, got {type(data)}")
            return False

        try:
            # Ensure connection is alive
            if not self._connection or not self._connection.is_connected():
                self._connection = mysql.connector.connect(
                    host=self._host,
                    database=self._database,
                    user=self._username,
                    password=self._password,
                    autocommit=True
                )

            # Build INSERT statement
            sql = (
                f"INSERT INTO {self._table} ("
                "timestamp, event_type, severity, sensor_id, message, data, notified"
                ") VALUES (%s, %s, %s, %s, %s, %s, %s)"
            )

            # Convert data dict to JSON string
            data_json = json.dumps(data.data) if data.data else None

            values = (
                data.timestamp,
                data.event_type,
                data.severity,
                data.sensor_id,
                data.message,
                data_json,
                data.notify
            )

            # Execute insert
            cursor = self._connection.cursor()
            cursor.execute(sql, values)
            cursor.close()

            logger.debug(
                f"Logged event: {data.event_type} ({data.severity}) "
                f"from {data.sensor_id or 'system'}"
            )
            return True

        except MySQLError as e:
            logger.error(f"Database error writing event: {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error writing event: {e}")
            return False

    async def shutdown(self) -> None:
        """Close database connection."""
        try:
            if self._connection and self._connection.is_connected():
                self._connection.close()
                logger.info("MariaDB events connection closed")
        except Exception as e:
            logger.warning(f"Error closing database connection: {e}")

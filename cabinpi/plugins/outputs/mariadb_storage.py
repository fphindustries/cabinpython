"""
MariaDB measurement storage output plugin.

This plugin stores sensor readings to a MariaDB/MySQL database.
Writes to the 'measurements' table with all sensor data columns.

Database:
- Host: localhost (configurable)
- Table: measurements
- Columns: 39 fields covering solar, indoor, outdoor, and inverter data
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

import mysql.connector
from mysql.connector import Error as MySQLError

from cabinpi.core.protocols import OutputPlugin
from cabinpi.core.models import SensorReading

logger = logging.getLogger(__name__)


class MariaDBStorageOutput:
    """
    MariaDB measurement storage output implementation.

    Implements the OutputPlugin protocol for writing sensor readings
    to a MariaDB database.

    Configuration example:
        database:
          enabled: true
          module: cabinpi.plugins.outputs.mariadb_storage
          type: measurement_storage
          config:
            host: localhost
            database: cabinpi
            username: cabinpi
            password: "${DB_PASSWORD}"
            table: measurements
    """

    def __init__(self, output_id: str, output_type: str) -> None:
        """
        Initialize the MariaDB storage output.

        Args:
            output_id: Unique output identifier
            output_type: Output type (should be "measurement_storage")
        """
        self._output_id = output_id
        self._output_type = output_type
        self._connection: Optional[mysql.connector.MySQLConnection] = None
        self._host: str = "localhost"
        self._database: str = "cabinpi"
        self._username: str = "cabinpi"
        self._password: str = ""
        self._table: str = "measurements"

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
        Initialize the database connection.

        Args:
            config: Configuration dict with:
                - host: Database host (default: localhost)
                - database: Database name (default: cabinpi)
                - username: Database username
                - password: Database password
                - table: Table name (default: measurements)

        Returns:
            True if initialization succeeded
        """
        try:
            # Get configuration
            self._host = config.get("host", "localhost")
            self._database = config.get("database", "cabinpi")
            self._username = config.get("username", "cabinpi")
            self._password = config.get("password", "")
            self._table = config.get("table", "measurements")

            # Test connection
            self._connection = mysql.connector.connect(
                host=self._host,
                database=self._database,
                user=self._username,
                password=self._password,
                autocommit=True
            )

            logger.info(
                f"MariaDB storage initialized: {self._username}@{self._host}/{self._database}"
            )
            return True

        except MySQLError as e:
            logger.exception(f"Failed to initialize MariaDB connection: {e}")
            return False

    async def write(self, data: Any) -> bool:
        """
        Write a sensor reading to the database.

        Args:
            data: SensorReading object to write

        Returns:
            True if write succeeded
        """
        if not isinstance(data, SensorReading):
            logger.error(f"Expected SensorReading, got {type(data)}")
            return False

        if not data.is_valid:
            logger.debug(f"Skipping invalid reading from {data.sensor_id}")
            return True

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

            # Merge all measurements from the reading
            measurements = data.measurements

            # Build INSERT statement for measurements table
            # This table has 39 columns covering all sensor data
            sql = (
                f"INSERT INTO {self._table} ("
                "Date, AbsorbTime, AmpHours, EqualizeTime, FloatTime, "
                "HighestVinputLog, IbattDisplay, NiteMinutesNoPwr, PvInputCurrent, VocLastMeasured, "
                "BatteryState, ChargeState, ClassicState, DispavgVbatt, DispavgVpv, kWHours, Watts, "
                "BATTtemperature, LifeTimekWHours, LifetimeAmpHours, "
                "int_c, int_f, humidity, Ext_F, inHg, wind_avg, wind_gust, wind_direction, illuminance, "
                "uv, solar_radiation, rain, avg_strike_distance, strike_count, weather_battery, "
                "daily_accumulation, Ext_humidity, InverterOn, InverterMode, InverterFault, "
                "InverterVACOut, InverterAACOut, Invertervdc"
                ") VALUES ("
                "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
                "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
                "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
                "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
                "%s, %s, %s"
                ")"
            )

            # Extract values using .get() to handle missing fields
            values = (
                data.timestamp,
                measurements.get('AbsorbTime'),
                measurements.get('AmpHours'),
                measurements.get('EqualizeTime'),
                measurements.get('FloatTime'),
                measurements.get('HighestVinputLog'),
                measurements.get('IbattDisplay'),
                measurements.get('NiteMinutesNoPwr'),
                measurements.get('PvInputCurrent'),
                measurements.get('VocLastMeasured'),
                measurements.get('batteryState'),
                measurements.get('chargeState'),
                measurements.get('classicState'),
                measurements.get('dispavgVbatt'),
                measurements.get('dispavgVpv'),
                measurements.get('kWHours'),
                measurements.get('watts'),
                measurements.get('BATTtemperature'),
                measurements.get('LifeTimekWHours'),
                measurements.get('LifetimeAmpHours'),
                measurements.get('int_c'),
                measurements.get('int_f'),
                measurements.get('humidity'),
                measurements.get('ext_temp'),
                measurements.get('pressure'),
                measurements.get('wind_avg'),
                measurements.get('wind_gust'),
                measurements.get('wind_direction'),
                measurements.get('illuminance'),
                measurements.get('uv'),
                measurements.get('solar_radiation'),
                measurements.get('rain'),
                measurements.get('avg_strike_distance'),
                measurements.get('strike_count'),
                measurements.get('weather_battery'),
                measurements.get('daily_accumulation'),
                measurements.get('ext_humidity'),
                measurements.get('InverterOn'),
                measurements.get('InverterMode'),
                measurements.get('InverterFault'),
                measurements.get('InverterVACOut'),
                measurements.get('InverterAACOut'),
                measurements.get('Invertervdc')
            )

            # Execute insert
            cursor = self._connection.cursor()
            cursor.execute(sql, values)
            cursor.close()

            logger.debug(f"Inserted measurement from {data.sensor_id} at {data.timestamp}")
            return True

        except MySQLError as e:
            logger.error(f"Database error writing measurement: {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error writing to database: {e}")
            return False

    async def shutdown(self) -> None:
        """Close database connection."""
        try:
            if self._connection and self._connection.is_connected():
                self._connection.close()
                logger.info("MariaDB storage connection closed")
        except Exception as e:
            logger.warning(f"Error closing database connection: {e}")

"""
MariaDB measurement storage output plugin.

This plugin stores sensor readings to a MariaDB/MySQL database.
Writes to the 'measurements_v2' table with wide format (queryable columns).

Database:
- Host: localhost (configurable)
- Table: measurements_v2 (default)
- Format: Wide table with dedicated columns for each sensor type
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

import mysql.connector
from mysql.connector import Error as MySQLError

from cabinpi.core.protocols import OutputPlugin
from cabinpi.core.models import SensorReading

logger = logging.getLogger(__name__)


class MariaDBStorageOutput:
    """
    MariaDB measurement storage output implementation.

    Implements the OutputPlugin protocol for writing sensor readings
    to a MariaDB database with wide table format for efficient querying.

    The plugin maintains an in-memory buffer of readings and writes them
    as a single row per timestamp, combining data from all sensors.

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
            table: measurements_v2
            batch_interval: 60  # Write buffered data every 60 seconds
    """

    # Sensor-to-column mapping
    COLUMN_MAPPING = {
        # SHT45/SHT31 indoor sensor
        'sht45': {
            'temp_c': 'indoor_temp_c',
            'temp_f': 'indoor_temp_f',
            'humidity': 'indoor_humidity',
        },
        'sht31': {
            'int_c': 'indoor_temp_c',
            'int_f': 'indoor_temp_f',
            'humidity': 'indoor_humidity',
        },

        # Solar charge controller (Modbus)
        'solar_controller': {
            'AbsorbTime': 'solar_absorb_time',
            'AmpHours': 'solar_amp_hours',
            'EqualizeTime': 'solar_equalize_time',
            'FloatTime': 'solar_float_time',
            'HighestVinputLog': 'solar_highest_input_voltage',
            'IbattDisplay': 'solar_battery_current',
            'NiteMinutesNoPwr': 'solar_nite_minutes_no_power',
            'PvInputCurrent': 'solar_pv_input_current',
            'VocLastMeasured': 'solar_voc_last_measured',
            'batteryState': 'solar_battery_state',
            'chargeState': 'solar_charge_state',
            'classicState': 'solar_classic_state',
            'dispavgVbatt': 'solar_battery_voltage',
            'dispavgVpv': 'solar_pv_voltage',
            'kWHours': 'solar_kwh',
            'watts': 'solar_power_watts',
            'BATTtemperature': 'solar_battery_temp_c',
            'LifeTimekWHours': 'solar_lifetime_kwh',
            'LifetimeAmpHours': 'solar_lifetime_amp_hours',
        },

        # Weather station (WeatherFlow API)
        'weather': {
            'ext_temp': 'outdoor_temp_c',
            'Ext_F': 'outdoor_temp_f',
            'ext_humidity': 'outdoor_humidity',
            'pressure': 'outdoor_pressure_hpa',
            'inHg': 'outdoor_pressure_inhg',
            'wind_avg': 'outdoor_wind_avg',
            'wind_gust': 'outdoor_wind_gust',
            'wind_direction': 'outdoor_wind_direction',
            'illuminance': 'outdoor_illuminance',
            'uv': 'outdoor_uv',
            'solar_radiation': 'outdoor_solar_radiation',
            'rain': 'outdoor_rain',
            'daily_accumulation': 'outdoor_daily_accumulation',
            'avg_strike_distance': 'outdoor_strike_distance',
            'strike_count': 'outdoor_strike_count',
            'weather_battery': 'outdoor_station_battery',
        },

        # Magnum inverter (continuous monitoring with aggregation)
        'inverter': {
            'InverterOn': 'inverter_on',
            'ChargerOn': 'charger_on',
            'InverterMode': 'inverter_mode',
            'InverterModeName': 'inverter_mode_name',
            'InverterFault': 'inverter_fault',

            # Voltage aggregates
            'Invertervdc': 'inverter_vdc',
            'vdc_min': 'inverter_vdc_min',
            'vdc_max': 'inverter_vdc_max',

            'InverterVACOut': 'inverter_vac_out',
            'VACout_min': 'inverter_vac_out_min',
            'VACout_max': 'inverter_vac_out_max',

            'VACin': 'inverter_vac_in',
            'VACin_min': 'inverter_vac_in_min',
            'VACin_max': 'inverter_vac_in_max',

            # Current aggregates
            'InverterAACOut': 'inverter_aac_out',
            'AACout_min': 'inverter_aac_out_min',
            'AACout_max': 'inverter_aac_out_max',

            'AACin': 'inverter_aac_in',
            'AACin_min': 'inverter_aac_in_min',
            'AACin_max': 'inverter_aac_in_max',

            # Temperature aggregates
            'battery_temp_c': 'inverter_battery_temp_c',
            'battery_temp_min': 'inverter_battery_temp_c_min',
            'battery_temp_max': 'inverter_battery_temp_c_max',

            'transformer_temp_c': 'inverter_transformer_temp_c',
            'transformer_temp_min': 'inverter_transformer_temp_c_min',
            'transformer_temp_max': 'inverter_transformer_temp_c_max',

            'fet_temp_c': 'inverter_fet_temp_c',
            'fet_temp_min': 'inverter_fet_temp_c_min',
            'fet_temp_max': 'inverter_fet_temp_c_max',
        },
        'magnum_rs485': {
            'inverter_on': 'inverter_on',
            'inverter_mode': 'inverter_mode',
            'inverter_fault': 'inverter_fault',
            'ac_voltage': 'inverter_vac_out',
            'ac_current': 'inverter_aac_out',
            'dc_voltage': 'inverter_vdc',
            'battery_temp_c': 'inverter_battery_temp_c',
            'battery_temp_f': 'inverter_battery_temp_f',
        },

        # INA228 battery monitor
        'ina228_battery': {
            'bus_voltage_v': 'battery_voltage_v',
            'current_a': 'battery_current_a',
            'current_ma': 'battery_current_ma',
            'power_w': 'battery_power_w',
            'power_mw': 'battery_power_mw',
            'shunt_voltage_mv': 'battery_shunt_voltage_mv',
            'die_temp_c': 'battery_temp_c',
            'die_temp_f': 'battery_temp_f',
        },

        # INA228 solar panel monitor
        'ina228_solar': {
            'bus_voltage_v': 'solar_panel_voltage_v',
            'current_a': 'solar_panel_current_a',
            'current_ma': 'solar_panel_current_ma',
            'power_w': 'solar_panel_power_w',
            'power_mw': 'solar_panel_power_mw',
            'shunt_voltage_mv': 'solar_panel_shunt_voltage_mv',
            'die_temp_c': 'solar_panel_temp_c',
            'die_temp_f': 'solar_panel_temp_f',
        },

        # DS18B20 outdoor temperature sensor
        'ds18b20_outdoor': {
            'temp_c': 'outdoor_sensor_temp_c',
            'temp_f': 'outdoor_sensor_temp_f',
            'device_id': 'outdoor_sensor_device_id',
        },
    }

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
        self._table: str = "measurements_v2"

        # Buffer for accumulating readings from different sensors
        # Key: timestamp (rounded to nearest second), Value: Dict of column->value
        self._reading_buffer: Dict[datetime, Dict[str, Any]] = {}

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
                - table: Table name (default: measurements_v2)

        Returns:
            True if initialization succeeded
        """
        try:
            # Get configuration
            self._host = config.get("host", "localhost")
            self._database = config.get("database", "cabinpi")
            self._username = config.get("username", "cabinpi")
            self._password = config.get("password", "")
            self._table = config.get("table", "measurements_v2")

            # Test connection
            self._connection = mysql.connector.connect(
                host=self._host,
                database=self._database,
                user=self._username,
                password=self._password,
                autocommit=True
            )

            logger.info(
                f"MariaDB storage initialized: {self._username}@{self._host}/{self._database}.{self._table}"
            )
            return True

        except MySQLError as e:
            logger.exception(f"Failed to initialize MariaDB connection: {e}")
            return False

    async def write(self, data: Any) -> bool:
        """
        Write a sensor reading to the database.

        This method maps sensor readings to the appropriate columns in the
        wide table format. Readings are buffered and written immediately
        (v2 writes each sensor reading as a separate row with timestamp).

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

            # Map sensor readings to table columns
            column_values = self._map_reading_to_columns(data)

            if not column_values:
                logger.warning(f"No column mapping found for sensor {data.sensor_id}")
                return True

            # Build dynamic INSERT statement
            columns = ['timestamp'] + list(column_values.keys())
            placeholders = ', '.join(['%s'] * len(columns))
            column_names = ', '.join(columns)

            sql = f"INSERT INTO {self._table} ({column_names}) VALUES ({placeholders})"

            # Prepare values
            values = [data.timestamp] + list(column_values.values())

            # Execute insert
            cursor = self._connection.cursor()
            cursor.execute(sql, values)
            cursor.close()

            logger.debug(f"Inserted measurement from {data.sensor_id} at {data.timestamp}")
            return True

        except MySQLError as e:
            logger.error(f"Database error writing measurement from {data.sensor_id}: {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error writing to database: {e}")
            return False

    def _map_reading_to_columns(self, reading: SensorReading) -> Dict[str, Any]:
        """
        Map a sensor reading to database columns.

        Args:
            reading: SensorReading object

        Returns:
            Dictionary of column_name -> value
        """
        column_values = {}

        # Get the mapping for this sensor type
        sensor_mapping = self.COLUMN_MAPPING.get(reading.sensor_id, {})

        if not sensor_mapping:
            logger.debug(f"No column mapping defined for sensor: {reading.sensor_id}")
            return column_values

        # Map each measurement field to its corresponding column
        for field_name, value in reading.measurements.items():
            column_name = sensor_mapping.get(field_name)

            if column_name:
                column_values[column_name] = value
            else:
                logger.debug(f"No mapping for {reading.sensor_id}.{field_name}")

        return column_values

    async def shutdown(self) -> None:
        """Close database connection."""
        try:
            if self._connection and self._connection.is_connected():
                self._connection.close()
                logger.info("MariaDB storage connection closed")
        except Exception as e:
            logger.warning(f"Error closing database connection: {e}")

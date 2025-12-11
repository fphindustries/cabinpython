"""
Unit tests for sensor plugins.

These tests use mocks to avoid requiring actual hardware.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from cabinpi.core.models import SensorReading, SensorType


class TestSHT31Sensor:
    """Test SHT31 sensor plugin."""

    @pytest.mark.asyncio
    async def test_sht31_initialization(self):
        """Test SHT31 sensor initializes with I2C bus."""
        from cabinpi.plugins.sensors.sht31 import SHT31Sensor

        sensor = SHT31Sensor("sht31")
        assert sensor.sensor_id == "sht31"
        assert sensor.sensor_type == SensorType.POLLING

    @pytest.mark.asyncio
    @patch('cabinpi.plugins.sensors.sht31.SMBus')
    async def test_sht31_read_success(self, mock_smbus):
        """Test successful temperature and humidity reading."""
        from cabinpi.plugins.sensors.sht31 import SHT31Sensor

        # Mock I2C data (temperature and humidity bytes)
        mock_bus = MagicMock()
        mock_bus.read_i2c_block_data.return_value = [
            0x63, 0x00, 0x00,  # Temp: ~25°C
            0x80, 0x00, 0x00   # Humidity: ~50%
        ]
        mock_smbus.return_value = mock_bus

        sensor = SHT31Sensor("sht31")
        await sensor.initialize({"i2c_bus": 1, "i2c_address": 0x44})

        reading = await sensor.read()

        assert reading.is_valid
        assert "int_c" in reading.measurements
        assert "int_f" in reading.measurements
        assert "humidity" in reading.measurements
        assert reading.measurements["humidity"] > 0
        assert reading.measurements["int_c"] > -50
        assert reading.measurements["int_c"] < 100


class TestSolarModbusSensor:
    """Test solar controller sensor plugin."""

    @pytest.mark.asyncio
    async def test_solar_initialization(self):
        """Test solar controller initializes."""
        from cabinpi.plugins.sensors.solar_modbus import SolarModbusSensor

        sensor = SolarModbusSensor("solar")
        assert sensor.sensor_id == "solar"
        assert sensor.sensor_type == SensorType.POLLING

    @pytest.mark.asyncio
    @patch('cabinpi.plugins.sensors.solar_modbus.AsyncModbusSerialClient')
    async def test_solar_read_success(self, mock_client_class):
        """Test successful Modbus register reading."""
        from cabinpi.plugins.sensors.solar_modbus import SolarModbusSensor

        # Mock Modbus response with 29 registers
        mock_response = MagicMock()
        mock_response.isError.return_value = False
        mock_response.registers = [
            125,  # Battery voltage * 10 = 12.5V
            180,  # PV voltage * 10 = 18.0V
            50,   # Current * 10 = 5.0A
            100,  # kWHours * 10
            500,  # Watts
            0,    # Charge state
            0, 0, 0, 0,  # More registers
            100,  # AmpHours
            1000, # Lifetime kWh
            5000, # Lifetime Ah
            0, 0, 0, 0,
            25,   # Battery temp (C)
            0, 0, 0,
            120,  # Float time
            60,   # Absorb time
            0, 0, 0, 0,
            30    # Equalize time
        ]

        mock_client = MagicMock()
        mock_client.connect.return_value = True
        mock_client.connected = True
        mock_client.read_holding_registers.return_value = mock_response
        mock_client_class.return_value = mock_client

        sensor = SolarModbusSensor("solar")
        await sensor.initialize({
            "port": "/dev/ttyUSB0",
            "slave_address": 10
        })

        reading = await sensor.read()

        assert reading.is_valid
        assert reading.measurements["dispavgVbatt"] == 12.5
        assert reading.measurements["dispavgVpv"] == 18.0
        assert reading.measurements["watts"] == 500


class TestInverterSensor:
    """Test inverter sensor plugin."""

    @pytest.mark.asyncio
    async def test_inverter_initialization(self):
        """Test inverter initializes."""
        from cabinpi.plugins.sensors.inverter import InverterSensor

        sensor = InverterSensor("inverter")
        assert sensor.sensor_id == "inverter"
        assert sensor.sensor_type == SensorType.POLLING

    @pytest.mark.asyncio
    @patch('cabinpi.plugins.sensors.inverter.Magnum')
    async def test_inverter_read_success(self, mock_magnum_class):
        """Test successful inverter data reading."""
        from cabinpi.plugins.sensors.inverter import InverterSensor

        # Mock Magnum response
        mock_magnum = MagicMock()
        mock_magnum.getDevices.return_value = [
            {
                'device': 'INVERTER',
                'data': {
                    'invled': 1,
                    'mode': 2,
                    'fault': 0,
                    'VACout': 120,
                    'adc': 5,
                    'vdc': 12.5
                }
            }
        ]
        mock_magnum_class.return_value = mock_magnum

        sensor = InverterSensor("inverter")
        await sensor.initialize({"port": "/dev/ttyUSB1"})

        reading = await sensor.read()

        assert reading.is_valid
        assert reading.measurements["InverterOn"] == 1
        assert reading.measurements["InverterVACOut"] == 120
        assert reading.measurements["Invertervdc"] == 12.5


class TestWeatherFlowSensor:
    """Test WeatherFlow API sensor plugin."""

    @pytest.mark.asyncio
    async def test_weatherflow_initialization(self):
        """Test WeatherFlow sensor initializes."""
        from cabinpi.plugins.sensors.weatherflow import WeatherFlowSensor

        sensor = WeatherFlowSensor("weather")
        assert sensor.sensor_id == "weather"
        assert sensor.sensor_type == SensorType.API

    @pytest.mark.asyncio
    @patch('cabinpi.plugins.sensors.weatherflow.httpx.AsyncClient')
    async def test_weatherflow_read_success(self, mock_client_class):
        """Test successful API reading."""
        from cabinpi.plugins.sensors.weatherflow import WeatherFlowSensor

        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'obs': [[
                1234567890,  # timestamp
                0,           # station_pressure
                2.5,         # wind_avg (m/s)
                5.0,         # wind_gust (m/s)
                180,         # wind_direction
                0,           # wind_lull
                1013,        # pressure (mb)
                20,          # temp (C)
                50,          # humidity (%)
                1000,        # illuminance
                2,           # UV
                100,         # solar_radiation
                0,           # rain
                0,           # precipitation_type
                5,           # avg_strike_distance (km)
                0,           # strike_count
                3.5,         # battery
                0,           # report_interval
                2.5          # daily_accumulation (mm)
            ]]
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        sensor = WeatherFlowSensor("weather")
        await sensor.initialize({
            "device_id": "12345",
            "api_token": "test_token"
        })

        reading = await sensor.read()

        assert reading.is_valid
        assert "wind_avg" in reading.measurements
        assert "ext_temp" in reading.measurements
        assert "pressure" in reading.measurements
        # Wind speed converted from m/s to mph
        assert reading.measurements["wind_avg"] > 0

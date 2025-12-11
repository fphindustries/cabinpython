"""
Sensor plugins for CabinPython v2 daemon.

This package contains sensor implementations for various hardware devices:
- SHT31: Indoor temperature and humidity (I2C)
- Solar Controller: Modbus charge controller data
- Inverter: Magnum inverter status and measurements
- WeatherFlow: External weather station data via API
"""

from cabinpi.plugins.sensors.sht31 import SHT31Sensor
from cabinpi.plugins.sensors.solar_modbus import SolarModbusSensor
from cabinpi.plugins.sensors.inverter import InverterSensor
from cabinpi.plugins.sensors.weatherflow import WeatherFlowSensor

__all__ = [
    "SHT31Sensor",
    "SolarModbusSensor",
    "InverterSensor",
    "WeatherFlowSensor",
]

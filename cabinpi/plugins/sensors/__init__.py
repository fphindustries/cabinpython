"""
Sensor plugins for CabinPython v2 daemon.

This package contains sensor implementations for various hardware devices:
- SHT31: Indoor temperature and humidity (I2C)
- SHT45: High-accuracy temperature and humidity (I2C)
- INA228: High-precision power monitor (I2C)
- Solar Controller: Modbus charge controller data
- Inverter: Magnum inverter status and measurements (RS-232 via pymagnum)
- MagnumRS485: Magnum inverter network with control (RS-485 native protocol)
- WeatherFlow: External weather station data via API
- DS18B20: Temperature sensor (1-wire)

Note: Sensors are loaded dynamically by the plugin loader.
This __init__.py file is for documentation only.
"""

# Do NOT import sensors here - they are loaded dynamically
# This prevents import errors when optional dependencies are missing

__all__ = []

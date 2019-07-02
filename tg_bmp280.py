#!/usr/bin/python
# Author: Bastien Wirtz <bastien.wirtz@gmail.com>

# Can enable debug output by uncommenting:
#import logging
#logging.basicConfig(level=logging.DEBUG)

#import Adafruit_BMP.BMP280 as BMP280
from bmp280 import BMP280
try:
    from smbus2 import SMBus
except ImportError:
    from smbus import SMBus

bus = SMBus(1)
sensor = BMP280(i2c_dev=bus)

celsius = sensor.get_temperature()
pascals = sensor.get_pressure()
hPa = pascals * .01
inHg = pascals * 0.00029529983071445
fahrenheit = (9.0/5.0) * celsius + 32

print 'bmp280 celsius={},fahrenheit={},hPa={},inHg={}'.format(celsius,fahrenheit,hPa,inHg)

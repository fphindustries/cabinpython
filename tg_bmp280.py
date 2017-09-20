#!/usr/bin/python
# Author: Bastien Wirtz <bastien.wirtz@gmail.com>

# Can enable debug output by uncommenting:
#import logging
#logging.basicConfig(level=logging.DEBUG)

import Adafruit_BMP.BMP280 as BMP280

sensor = BMP280.BMP280()
celsius = sensor.read_temperature()
pascals = sensor.read_pressure()
hPa = pascals * .01
inHg = pascals * 0.00029529983071445
fahrenheit = (9.0/5.0) * celsius + 32

print 'bmp280 celsius={},fahrenheit={},hPa={},inHg={}'.format(celsius,fahrenheit,hPa,inHg)

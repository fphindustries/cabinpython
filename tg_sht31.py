#!/usr/bin/python3

import time
import board
import busio
import adafruit_sht31d

i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_sht31d.SHT31D(i2c)

celsius = sensor.temperature
fahrenheit = (9.0/5.0) * celsius + 32
humidity = sensor.relative_humidity

#print(f"sht31 celsius={celsius},fahrenheit={fahrenheit},humidity={humidity}")

print('bmp280 celsius={celsius},fahrenheit={fahrenheit},humidity={humidity}'.format(celsius=celsius, fahrenheit=fahrenheit,humidity=humidity))


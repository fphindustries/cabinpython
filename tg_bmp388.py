#!/usr/bin/python3

import time
import board
import busio
import adafruit_bmp3xx

# I2C setup
i2c = busio.I2C(board.SCL, board.SDA)
bmp = adafruit_bmp3xx.BMP3XX_I2C(i2c)

# SPI setup
# from digitalio import DigitalInOut, Direction
# spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
# cs = DigitalInOut(board.D5)
# bmp = adafruit_bmp3xx.BMP3XX_SPI(spi, cs)

bmp.pressure_oversampling = 8
bmp.temperature_oversampling = 2

celsius = bmp.temperature
pascals = bmp.pressure
hPa = pascals * .01
inHg = pascals * 0.029529983071445
fahrenheit = (9.0/5.0) * celsius + 32

print('bmp280 celsius={celsius},fahrenheit={fahrenheit},hPa={hPa},inHg={inHg}'.format(celsius=celsius, fahrenheit=fahrenheit,hPa=hPa, inHg=inHg))


#!/usr/bin/python3
"""first please add python library via this command: python -m easy_install --user https://github.com/pl31/python-liquidcrystal_i2c/archive/master.zip """
#import socket
#import os.path
#import sys
#import struct
#import fcntl
#import os
#import time
import liquidcrystal_i2c
import board
import busio
import adafruit_bmp3xx

i2c = busio.I2C(board.SCL, board.SDA)
bmp = adafruit_bmp3xx.BMP3XX_I2C(i2c)

lcd = liquidcrystal_i2c.LiquidCrystal_I2C(0x27, 1, numlines=4)
lcd.backlight()
bmp.pressure_oversampling = 8
bmp.temperature_oversampling = 2

while True:
	i2c = busio.I2C(board.SCL, board.SDA)
	bmp = adafruit_bmp3xx.BMP3XX_I2C(i2c)
	celsius = bmp.temperature
	pascals = bmp.pressure
	hPa = pascals * .01
	inHg = pascals * 0.029529983071445
	fahrenheit = (9.0/5.0) * celsius + 32

	lcd.printline(0, f'fahrenheit={fahrenheit:.1f}')
	lcd.printline(1, f'inHg={inHg:.2f}')

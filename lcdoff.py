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

lcd = liquidcrystal_i2c.LiquidCrystal_I2C(0x27, 1, numlines=4)
lcd.noBacklight()

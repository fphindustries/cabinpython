#!/usr/bin/env python
from Adafruit_SHT31 import *
from datetime import datetime

SHT31_ADDRESS = 0x44

def read_env():
    sensor = SHT31(address = SHT31_ADDRESS)

    celsius, humidity = sensor.read_temperature_humidity()
    fahrenheit = (9.0/5.0) * celsius + 32

    return celsius, fahrenheit, humidity


def main():  
    celsius, fahrenheit, humidity =read_env()
    print("sht31,addr={} celsius={},fahrenheit={},humidity={}".format(SHT31_ADDRESS, celsius, fahrenheit, humidity))

if __name__ == '__main__':
    main()

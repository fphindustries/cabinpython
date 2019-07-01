#!/usr/bin/python
import Adafruit_BMP.BMP280 as BMP280
from w1thermsensor import W1ThermSensor
from ina219 import INA219
from ina219 import DeviceRangeError
from Adafruit_SHT31 import *
from datetime import datetime

def read_bmp280():
    try:
        sensor = BMP280.BMP280()
        celsius = sensor.read_temperature()
        pascals = sensor.read_pressure()
        hPa = pascals * .01
        inHg = pascals * 0.00029529983071445
        fahrenheit = (9.0/5.0) * celsius + 32
        return {'celsius':celsius, 'fahrenheit': fahrenheit, 'pascals': pascals, 'hPa': hPa, 'inHg': inHg}
    except:
        return {'celsius':None, 'fahrenheit': None, 'pascals': None, 'hPa': None, 'inHg': None}

def read_ds18b20():        
    try:
        for sensor in W1ThermSensor.get_available_sensors([W1ThermSensor.THERM_SENSOR_DS18B20]):
            celsius=sensor.get_temperature()
            fahrenheit = (9.0/5.0) * celsius + 32

        return {'celsius':celsius, 'fahrenheit':fahrenheit};
    except:
        return {'celsius':None, 'fahrenheit':None}

def read_ina219():
    try:
        SHUNT_OHMS = 0.1
        ina = INA219(SHUNT_OHMS)
        ina.configure()

        return {'voltage':ina.voltage(), 'current':ina.current()*.001, 'power':ina.power()*.001}
    except DeviceRangeError as e:
        return {'voltage':None, 'current':None, 'power':None}

def read_sht31():
    try:
        SHT31_ADDRESS = 0x44
        sensor = SHT31(address = SHT31_ADDRESS)

        celsius, humidity = sensor.read_temperature_humidity()
        fahrenheit = (9.0/5.0) * celsius + 32

        return {'celsius':celsius, 'fahrenheit':fahrenheit, 'humidity':humidity}
    except:
        return {'celsius':None, 'fahrenheit':None, 'humidity':None}


def main():
    bmp280 = read_bmp280()
    # ina219 = read_ina219()
    ds18b20 = read_ds18b20()
    sht31 = read_sht31()

    #print("sensors case_c={},case_f={},hPa={},inHg={},ext_c={},ext_f={},int_c={},int_f={},humidity={},pi_v={},pi_i={},pi_w={}".format(bmp280['celsius'],bmp280['fahrenheit'],bmp280['hPa'],bmp280['inHg'],ds18b20['celsius'],ds18b20['fahrenheit'],sht31['celsius'],sht31['fahrenheit'],sht31['humidity'],ina219['voltage'],ina219['current'],ina219['power']))
    print("sensors case_c={},case_f={},hPa={},inHg={},ext_c={},ext_f={},int_c={},int_f={},humidity={}".format(bmp280['celsius'],bmp280['fahrenheit'],bmp280['hPa'],bmp280['inHg'],ds18b20['celsius'],ds18b20['fahrenheit'],sht31['celsius'],sht31['fahrenheit'],sht31['humidity']))

if __name__ == '__main__':
    main()

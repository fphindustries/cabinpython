#!/usr/bin/python3

import time
import board
import busio
import adafruit_sht31d
import adafruit_bmp3xx
from adafruit_ina219 import ADCResolution, BusVoltageRange, INA219
from w1thermsensor import W1ThermSensor, Unit

i2c = busio.I2C(board.SCL, board.SDA)
#ow_file="/mnt/1wire/28.0EFE79971103/temperature"

def read_bmp388():
    try:
        bmp = adafruit_bmp3xx.BMP3XX_I2C(i2c)
        bmp.pressure_oversampling = 8
        bmp.temperature_oversampling = 2

        celsius = bmp.temperature
        pascals = bmp.pressure
        hPa = pascals * .01
        inHg = pascals * 0.029529983071445
        fahrenheit = (9.0/5.0) * celsius + 32

        return {'celsius':celsius, 'fahrenheit': fahrenheit, 'pascals': pascals, 'hPa': hPa, 'inHg': inHg}
    except:
        return {'celsius':None, 'fahrenheit': None, 'pascals': None, 'hPa': None, 'inHg': None}

def read_ds18b20():
    try:
        sensor = W1ThermSensor()
        temperature_in_all_units = sensor.get_temperatures([
            Unit.DEGREES_C,
            Unit.DEGREES_F])

        return {'celsius':temperature_in_all_units[0], 'fahrenheit':temperature_in_all_units[1]};
    except:
        return {'celsius':None, 'fahrenheit':None}

def read_ina219():
    try:
        ina219 = INA219(i2c)
        ina219.bus_adc_resolution = ADCResolution.ADCRES_12BIT_32S
        ina219.shunt_adc_resolution = ADCResolution.ADCRES_12BIT_32S
        # optional : change voltage range to 16V
        ina219.bus_voltage_range = BusVoltageRange.RANGE_16V


        return {'voltage':ina219.bus_voltage + ina219.shunt_voltage, 'current':ina219.current*.001, 'power':ina219.power}
    except:
        return {'voltage':None, 'current':None, 'power':None}

def read_sht31():
    try:
        sensor = adafruit_sht31d.SHT31D(i2c)

        celsius = sensor.temperature
        fahrenheit = (9.0/5.0) * celsius + 32
        humidity = sensor.relative_humidity

        return {'celsius':celsius, 'fahrenheit':fahrenheit, 'humidity':humidity}
    except:
        return {'celsius':None, 'fahrenheit':None, 'humidity':None}


def main():
    bmp388 = read_bmp388()
    ina219 = read_ina219()
    ds18b20 = read_ds18b20()
    sht31 = read_sht31()

    print(f"sensors case_c={bmp388['celsius']},case_f={bmp388['fahrenheit']},hPa={bmp388['hPa']},inHg={bmp388['inHg']},ext_c={ds18b20['celsius']},ext_f={ds18b20['fahrenheit']},int_c={sht31['celsius']},int_f={sht31['fahrenheit']},humidity={sht31['humidity']}")
    #print("sensors case_c={},case_f={},hPa={},inHg={},ext_c={},ext_f={},int_c={},int_f={},humidity={}".format(bmp280['celsius'],bmp280['fahrenheit'],bmp280['hPa'],bmp280['inHg'],ds18b20['celsius'],ds18b20['fahrenheit'],sht31['celsius'],sht31['fahrenheit'],sht31['humidity']))

if __name__ == '__main__':
    main()

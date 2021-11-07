#!/usr/bin/env python3
from gpiozero import Button
from signal import pause
from influxdb import InfluxDBClient
import configparser
import liquidcrystal_i2c

config = configparser.ConfigParser()
config.read('influx.ini')
influx_client = InfluxDBClient(config['influxdb']['host'], config['influxdb']['port'], config['influxdb']['user'], config['influxdb']['password'], config['influxdb']['database'])
lcd = liquidcrystal_i2c.LiquidCrystal_I2C(0x27, 1, numlines=4)

def pressed():
    print("button was pressed")

def released():
    print("button was released")

def displayEnvironment():
    degree_sign = u"\N{DEGREE SIGN}"
    result = influx_client.query('select * from sensors where time > now() - 1d order by desc limit 1;')
    points = result.get_points()
    point = next(points)
    print(point)
    lcd.printline(0, "Environment")
    lcd.printline(1, f"Out: {point['ext_f']:.1f}° In: {point['int_f']:.1f}°")
    lcd.printline(2, f"Humidity: {point['humidity']:.2f}%")
    lcd.printline(3, f"Pressure: {point['inHg']:.2f} inHg")
    print(f"Result: {point}")

def displaySolar():
    result = influx_client.query('select * from solar where time > now() - 1h group by * order by desc limit 1;')
    points = result.get_points()
    point = next(points)
    print(point)
    lcd.printline(0, "Environment")
    lcd.printline(1, f"Out: {point['ext_f']:.1f}° In: {point['int_f']:.1f}°")
    lcd.printline(2, f"Humidity: {point['humidity']:.2f}%")
    lcd.printline(3, f"Pressure: {point['inHg']:.2f} inHg")
    print(f"Result: {point}")

displaySolar()


btn = Button(6)

btn.when_pressed = pressed
btn.when_released = released

input()
#!/usr/bin/env python
#
#PATH="/sys/bus/w1/devices/28-000008e482da/w1_slave"
#
#def read_env():
#    file = open(PATH, "r")
#    lines = file.readlines()
#    file.close()
#    
#    if "YES" in lines[0]:
#        celsius = int(lines[1][lines[1].find("=")+1:-1]) * .001
#        fahrenheit = (9.0/5.0) * celsius + 32
#        return celsius, fahrenheit
#    raise BufferError('Unable to read sensor data')
#
#def main():
#    celsius, fahrenheit =read_env()
#    print("ds18b20 celsius={},fahrenheit={}".format(celsius, fahrenheit))
#
#if __name__ == '__main__':
#    main()
from w1thermsensor import W1ThermSensor

for sensor in W1ThermSensor.get_available_sensors([W1ThermSensor.THERM_SENSOR_DS18B20]):
    celsius=sensor.get_temperature()
    fahrenheit = (9.0/5.0) * celsius + 32
    print("ds18b20,addr={} celsius={},fahrenheit={}".format(sensor.id, celsius, fahrenheit))

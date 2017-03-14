#!/usr/bin/env python
import sys
import requests

from Adafruit_SHT31 import *
from datetime import datetime
#logging.basicConfig(filename='example.log',level=logging.DEBUG)
from ina219 import INA219
from ina219 import DeviceRangeError

SHUNT_OHMS = 0.1


def read_power():
    ina = INA219(SHUNT_OHMS)
    ina.configure()
    return ina.voltage(), ina.current(), ina.power()

def read_env():
    sensor = SHT31(address = 0x44)
    #sensor = SHT31(address = 0x45)

    degrees, humidity = sensor.read_temperature_humidity()
    degrees = (9.0/5.0) * degrees + 32

    return degrees, humidity

def create_sample(sensorName, reading):
    return {'SensorName':sensorName, 'SampleTime':datetime.now().isoformat(), 'Value':reading}

def main():  
    try:
        while True:
            degrees, humidity =read_env()
            v,a,w = read_power()
            readings = []
            readings.append(create_sample('InsideTemp', degrees))
            readings.append(create_sample('InsideHum', humidity))
            readings.append(create_sample('PiVolts', v))
            readings.append(create_sample('PimAmps', a))
            readings.append(create_sample('PimWatts', w))

            print(readings)
            r=requests.post('http://cabinpi.azurewebsites.net/api/telemetry/', json = readings)
            print(r)
            time.sleep(30)

    except KeyboardInterrupt:
        print ( "IoTHubClient sample stopped" )

def usage():
    print ( "Usage: cabinpython.py -p <protocol> -c <connectionstring>" )
    print ( "    protocol        : <amqp, amqp_ws, http, mqtt, mqtt_ws>" )
    print ( "    connectionstring: <HostName=<host_name>;DeviceId=<device_id>;SharedAccessKey=<device_key>>" )


if __name__ == '__main__':
    print ( "\nPython %s" % sys.version )

    main()

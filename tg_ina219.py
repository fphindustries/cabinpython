#!/usr/bin/env python
from ina219 import INA219 
from ina219 import DeviceRangeError 

SHUNT_OHMS = 0.1 
def read():
    ina = INA219(SHUNT_OHMS) 
    ina.configure() 

    try:
        print "ina219 voltage={},current={},power={}".format(ina.voltage(), ina.current()*.001, ina.power()*.001) 
    except DeviceRangeError as e:
        print e 

if __name__ == "__main__":
    read()

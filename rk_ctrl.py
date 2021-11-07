#!/usr/bin/env python3

import RPi.GPIO as GPIO
#from pcf8574 import PCF8574
import pcf8574_io
from influxdb import InfluxDBClient
import configparser
import liquidcrystal_i2c
from datetime import datetime

#pcf = PCF8574(1, 0x20)
pcf=pcf8574_io.PCF(0x20)
lcd = liquidcrystal_i2c.LiquidCrystal_I2C(0x27, 1, numlines=4)

BUTTON_GPIO = 6

button_last_pressed = datetime.now()
button_up_pressed = False;
button_down_pressed = False;
button_left_pressed = False;
button_right_pressed = False;
button_center_pressed = False;

def resetButtons() :
    global button_last_pressed
    button_last_pressed = datetime.now()

    global button_up_pressed
    global button_down_pressed
    global button_left_pressed
    global button_right_pressed
    global button_center_pressed
    button_up_pressed = False;
    button_down_pressed = False;
    button_left_pressed = False;
    button_right_pressed = False;
    button_center_pressed = False;

def handleButton() :
    if(button_up_pressed) :
        showSolar()
    else:
        showTemp()

    resetButtons()


def button_callback(channel) :
    print(f'0:{pcf.read("p0")} 1:{pcf.read("p1")} 2:{pcf.read("p2")} 3:{pcf.read("p3")} 4:{pcf.read("p4")} 5:{pcf.read("p5")} 6:{pcf.read("p6")} 7:{pcf.read("p7")}')
    
    #if((datetime.now() - button_last_pressed).seconds < 1):
    #    return

    global button_up_pressed
    global button_down_pressed
    global button_left_pressed
    global button_right_pressed
    global button_center_pressed

    #button_up_pressed = 	pcf.read("p3") == False
    #button_down_pressed = 	pcf.read("p4") == False
    #button_left_pressed = 	pcf.read("p6") == False
    #button_right_pressed = 	pcf.read("p5") == False
    #button_center_pressed = 	pcf.read("p2") == False
    
    #print("Top Pressed: {0}".format(pcf.read('p3') == False))
    #print("button_up: {0}".format(button_up_pressed))
    #print("button_down: {0}".format(button_down_pressed))
    #print(f'0:{pcf.read("p0")} 1:{pcf.read("p1")} 2:{pcf.read("p2")} 3:{pcf.read("p3")} 4:{pcf.read("p4")} 5:{pcf.read("p5")} 6:{pcf.read("p6")} 7:{pcf.read("p7")}')
    #handleButton()
    #resetButtons()


def initButtons() :
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(BUTTON_GPIO, GPIO.FALLING, callback=button_callback, bouncetime=100)


def initData() :
    config = configparser.ConfigParser()
    config.read('influx.ini')
    client = InfluxDBClient(config['influxdb']['host'], config['influxdb']['port'], config['influxdb']['user'], config['influxdb']['password'], config['influxdb']['database'])
    result = client.query('select * from solar where time > now() - 1h group by * order by desc limit 1;')
    #print("AmpHours: {0}".format( result['AmpHours'] ))
    print("results: {0}".format(result))

def initLcd() :
    lcd.printline(0, 'init')

def showSolar(data) :
    lcd.printline(0,'solar')

def showTemp() :
    lcd.printline(0, 'temp')



if __name__ == '__main__':
    initButtons()
    while(True):
        
#    print('init data')
#    initData()
#    showSolar('nope')
#    showTemp()


    input();



#results: ResultSet({'('solar', {'host': 'cabinpi'})': [{'time': '2021-11-06T22:03:20Z', 'AbsorbTime': 7200.0, 'AmpHours': 13.0, 
#'EqualizeTime': 3600.0, 'FloatTime': 247.0, 'HighestVinputLog': 147.6, 'IbattDisplay': 5.7, 
#'NiteMinutesNoPwr': 0.0, 'PvInputCurrent': 1.0, 'VocLastMeasured': 86.8, 
#'batteryState': 6.0, 'chargeState': 1539.0, 'classicState': 3.0, 
#'dispavgVbatt': 12.5, 'dispavgVpv': 76.1, 'kWHours': 0.1, 'watts': 71.0}]})


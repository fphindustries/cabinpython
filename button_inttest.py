#!/usr/bin/env python3

import RPi.GPIO as GPIO
from pcf8574 import PCF8574

pcf = PCF8574(1, 0x20)
BUTTON_GPIO = 6

if __name__ == '__main__':
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    while True:
        GPIO.wait_for_edge(BUTTON_GPIO, GPIO.FALLING)
        #print("Button pressed!")
        print(pcf.port)

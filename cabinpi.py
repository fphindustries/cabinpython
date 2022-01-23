#!/usr/bin/env python3
from RPi import GPIO
from liquidcrystal_i2c import LiquidCrystal_I2C
from smbus import SMBus
from time import monotonic, sleep
import math

poll_delay = 1/125 # Time between input polling in seconds
idle_delay = 30    # Time to go to idle state in seconds

BUTTON_UP = 3
BUTTON_RIGHT = 4
BUTTON_LEFT = 5
BUTTON_DOWN = 6
BUTTON_CENTER = 7

bus = SMBus(1)
lcd = LiquidCrystal_I2C(0x27, 1, numlines=4)

def screen1(elapsed):
    lcd.printline(0, "Screen 1 %is" % elapsed)

def screen2(elapsed):
    lcd.printline(0, "Screen 2 %is" % elapsed)

def screen3(elapsed):
    lcd.printline(0, "Screen 3 %is" % elapsed)

def screen4(elapsed):
    lcd.printline(0, "Screen 4 %is" % elapsed)

screens = [
    screen1,
    screen2,
    screen3,
    screen4
]

cur_screen = 0

def init():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(6, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    bus.write_byte(0x20, 0xff)

# Actively polling for input
def active():
    global cur_screen
    lcd.display()
    lcd.backlight()
    cur_pins = 0xff
    dis_start = idle_start = monotonic()
    dis_elapsed = idle_elapsed = 0.0
    while idle_elapsed <= idle_delay:
        # Call display function
        display = screens[cur_screen % len(screens)]
        display(dis_elapsed)
        sleep(poll_delay)
        pins = bus.read_byte(0x20)
        button_press = cur_pins == 0xff and pins != 0xff
        cur_pins = pins
        cur_time = monotonic()
        if pins != 0xff:
            idle_start = cur_time
        if button_press:
            inv = ~pins & 0xFF
            tc = (-1 * (255 - inv + 1)) & 0xFF
            button = int(math.log2(inv & tc))
            if button == BUTTON_RIGHT:
                cur_screen += 1
                dis_start = cur_time
            elif button == BUTTON_LEFT:
                cur_screen -= 1
                dis_start = cur_time
        idle_elapsed = cur_time - idle_start
        dis_elapsed = cur_time - dis_start

# Wait for wake-up signal
def idle():
    while True:
        global cur_screen
        cur_screen = cur_screen % len(screens)
        lcd.noDisplay()
        lcd.noBacklight()
        # Block until wake-up
        # TODO: This prevents SIGINT (Ctrl-C) from working, look into event callback
        GPIO.wait_for_edge(6, GPIO.FALLING)
        active()

try:
    init()
    idle()
finally:
    GPIO.cleanup()

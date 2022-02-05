#!/usr/bin/env python3
from RPi import GPIO
import signal
import sys
from smbus import SMBus
import math
from threading import Timer
from liquidcrystal_i2c import LiquidCrystal_I2C
from influxdb import InfluxDBClient
import configparser
import psutil

BUTTON_GPIO=6
BUTTON_UP = 3
BUTTON_RIGHT = 5
BUTTON_LEFT = 4
BUTTON_DOWN = 6
BUTTON_CENTER = 7
LCD_ON_TIME=30.0

bus = SMBus(1)
cur_screen=0
lcd = LiquidCrystal_I2C(0x27, 1, numlines=4)
config = configparser.ConfigParser()
config.read('influx.ini')
influxClient = InfluxDBClient(config['influxdb']['host'], config['influxdb']['port'], config['influxdb']['user'], config['influxdb']['password'], config['influxdb']['database'])

def screen_off():
    lcd.noDisplay()
    lcd.noBacklight()

timer = Timer(LCD_ON_TIME, screen_off)

battery_states = {
    0: "Resting",
    3: "Absorb",
    4: "Bulk MPPT",
    5: "Float",
    6: "Float MPPT",
    7: "Equalize",
    10: "Hyper VOC",
    18: "Equalize MPPT"
}
def clear_lcd():
    lcd.printline(0,f"{' ':>20}")
    lcd.printline(1,f"{' ':>20}")
    lcd.printline(2,f"{' ':>20}")
    lcd.printline(3,f"{' ':>20}")

def solarScreen():
    clear_lcd()

    rows = list(influxClient.query('select * from solar where time > now() - 1h group by * order by desc limit 1;').get_points())
    row = rows[0]
    dispavgVbatt = row["dispavgVbatt"]
    VocLastMeasured = row["VocLastMeasured"]
    batteryState = row["batteryState"]
    AmpHours = row["AmpHours"]
    kWHours = row["kWHours"]
    watts = row["watts"]
    
    lcd.printline(0, f"{battery_states[batteryState]:<14}")
    lcd.printline(1, f"vBat:{dispavgVbatt} vPnl:{VocLastMeasured}")
    lcd.printline(2, f"AH:{AmpHours} kWH:{kWHours}")
    lcd.printline(3, f"Watts:{watts}")

def tempScreen():
    clear_lcd()
    lcd.printline(0, f"Environment")
    rows = list(influxClient.query('select * from sensors where time > now() - 1h group by * order by desc limit 1;').get_points())
    row = rows[0]
    case_f = row["case_f"]
    ext_f = row["ext_f"]
    humidity = row["humidity"]
    inHg = row["inHg"]
    
    lcd.printline(1, f"In:{case_f:.2f} Out:{ext_f:.2f}")
    lcd.printline(2, f"Humidity:{humidity:.2f}%")
    lcd.printline(3, f"Pressure:{inHg:.2f}inHg")

def systemScreen():
    clear_lcd()
    load = psutil.getloadavg()
    memory = psutil.virtual_memory()
    mem_total = memory.total / 1073741824
    mem_used = memory.used / 1073741824
    disk = psutil.disk_usage('/')
    disk_total = disk.total / 1073741824
    disk_used = disk.used / 1073741824

    lcd.printline(0, f"System {psutil.cpu_percent():>12.0f}%")
    lcd.printline(1, f"Load {load[0]:.2f} {load[1]:.2f} {load[2]:.2f}")
    lcd.printline(2, f"Mem {mem_used:.2f} of {mem_total:.2f}")
    lcd.printline(3, f"Dsk {disk_used:.2f} of {disk_total:.2f}")

screens = [
    solarScreen,
    tempScreen,
    systemScreen
]

def button_pressed_callback(channel):
    global cur_screen
    global timer

    pins = bus.read_byte(0x20)
    if pins == 255: #Button Up
        return

    inv = ~pins & 0xFF
    tc = (-1 * (255 - inv + 1)) & 0xFF
    button = int(math.log2(inv & tc))

    if button == BUTTON_RIGHT:
        cur_screen = (cur_screen + 1) % len(screens)
    if button == BUTTON_LEFT:
        cur_screen = (cur_screen -1) % len(screens)

    #screen on
    lcd.display()
    lcd.backlight()

    screens[cur_screen]()
    timer.cancel()
    timer = Timer(LCD_ON_TIME, screen_off)
    timer.start()

def signal_handler(sig, frame):
    GPIO.cleanup()
    sys.exit(0)

if __name__ == '__main__':
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(BUTTON_GPIO, GPIO.FALLING, 
            callback=button_pressed_callback, bouncetime=100)
    bus.write_byte(0x20, 0xff)
    screen_off()
    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()
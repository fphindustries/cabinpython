#import keyboard
import time
import board
import adafruit_character_lcd.character_lcd_rgb_i2c as character_lcd

lcd_columns = 16
lcd_rows = 2

#lcd = None

def alphaAlpha():
    lcd.clear()
    lcd.message='Alpha-Alpha'

def alphaBravo():
    lcd.clear()
    lcd.message='Alpha-Bravo'

def bravoAlpha():
    lcd.clear()
    lcd.message='Bravo-Alpha'

def bravoBravo():
    lcd.clear()
    lcd.message='Bravo-Bravo'

def charlieAlpha():
    lcd.clear()
    lcd.message='Charlie-Alpha'

def charlieBravo():
    lcd.clear()
    lcd.message='Charlie-Bravo'

NONE=0
LEFT=1
RIGHT=2
UP=3
DOWN=4
SELECT=5
QUIT=6

labels = [
    'Apple',
    'Butter',
    'Church'
]

menus = [
    [alphaAlpha, alphaBravo],
    [bravoAlpha, bravoBravo],
    [charlieAlpha, charlieBravo],
]

def main():
    # Initialise I2C bus.
    i2c = board.I2C()  # uses board.SCL and board.SDA

    # Initialise the LCD class
    global lcd
    lcd = character_lcd.Character_LCD_RGB_I2C(i2c, lcd_columns, lcd_rows)

    lcd.clear()
    # Set LCD color to red
    lcd.color = [100, 0, 0]

    menuIndex = 0
    subMenuIndex = 0
    activeMenu = menus[menuIndex]
    activeSubMenu = activeMenu[subMenuIndex]

    running = True
    lastPress = NONE
    pressed = False
    while running:
        pressed = False
        changed = False

        currentPress=NONE
        if lcd.left_button:
            currentPress=LEFT
        elif lcd.right_button:
            currentPress=RIGHT
        elif lcd.up_button:
            currentPress=UP
        elif lcd.down_button:
            currentPress=DOWN
#        elif keyboard.is_pressed(" ":
#            currentPress=SELECT
        elif lcd.select_button:
            currentPress=QUIT

        if currentPress != lastPress:
            pressed=True
            lastPress = currentPress

        if pressed:
            if currentPress == LEFT:
                menuIndex -= 1
                if menuIndex < 0:
                    menuIndex= len(menus)-1
                subMenuIndex=0
                changed=True
            elif currentPress == RIGHT:
                menuIndex += 1
                if menuIndex >= len(menus):
                    menuIndex = 0
                subMenuIndex=0
                changed=True
            elif currentPress == UP:
                subMenuIndex -= 1
                if subMenuIndex < 0:
                    subMenuIndex= len(activeMenu)-1
                changed=True
            elif currentPress == DOWN:
                subMenuIndex += 1
                if subMenuIndex >= len(activeMenu):
                    subMenuIndex = 0
                changed=True
            elif currentPress == QUIT:
                #changed=True
                running = False
                lcd.clear()
                #lcd.backlight = False
                lcd.color = [0, 0, 0]

        if changed:
            activeMenu = menus[menuIndex]
            activeSubMenu = activeMenu[subMenuIndex]
            activeSubMenu()

        time.sleep(.05)

if __name__ == '__main__':
    main()

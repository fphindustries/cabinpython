import keyboard
import time

def printHi():
    print('Hi')

def printBravo():
    print('Bravo')

def printCharlie():
    print('Charlie')

def alphaAlpha():
    print('Alpha-Alpha')

def alphaBravo():
    print('Alpha-Bravo')

def bravoAlpha():
    print('Bravo-Alpha')

def bravoBravo():
    print('Bravo-Bravo')

def charlieAlpha():
    print('Charlie-Alpha')

def charlieBravo():
    print('Charlie-Bravo')

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
        if keyboard.is_pressed("a"):
            currentPress=LEFT
        elif keyboard.is_pressed("d"):
            currentPress=RIGHT
        elif keyboard.is_pressed("w"):
            currentPress=UP
        elif keyboard.is_pressed("s"):
            currentPress=DOWN
        elif keyboard.is_pressed(" "):
            currentPress=SELECT
        elif keyboard.is_pressed("q"):
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
                changed=True
                running = False
        
        if changed:
            activeMenu = menus[menuIndex]
            activeSubMenu = activeMenu[subMenuIndex]
            activeSubMenu()

        time.sleep(.05)
    
if __name__ == '__main__':
    main()
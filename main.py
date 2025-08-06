import machine
import utime
from machine import I2C, Pin
from ssd1306 import SSD1306_I2C

# === Display ===
SCREEN_WIDTH = 128
SCREEN_HEIGHT = 64
I2C_SDA = 0  # GPIO0
I2C_SCL = 1  # GPIO1
OLED_ADDR = 0x3C

i2c = I2C(0, scl=Pin(I2C_SCL), sda=Pin(I2C_SDA))
display = SSD1306_I2C(SCREEN_WIDTH, SCREEN_HEIGHT, i2c, addr=OLED_ADDR)

# === Rotary & Buttons ===
ENCA = 5
ENCB = 6
BTN1 = 3     # Rotary press = SELECT/CONFIRM
PWR_BUT = 2  # Back button
BTN3 = 4     # Set as origin

encA = Pin(ENCA, Pin.IN, Pin.PULL_UP)
encB = Pin(ENCB, Pin.IN, Pin.PULL_UP)
btn1 = Pin(BTN1, Pin.IN, Pin.PULL_UP)
pwr_btn = Pin(PWR_BUT, Pin.IN, Pin.PULL_UP)
btn3 = Pin(BTN3, Pin.IN, Pin.PULL_UP)

lastENCA = 1
menuIndex = 0
currentMenu = "home"
currentStepper = 0  # 1 or 2
stepperOption = 0

selectedRPM = 800
stepper1Angle = 0
stepper2Angle = 0
confirmFlashIndex = -1
flashStartTime = 0
settingOrigin = False
originStepperRunning = False

# Stepper state
stepper1Steps = 0
stepper2Steps = 0

encoderPos = 0
lastEncoded = 0

def drawTitle(title):
    display.fill(0)
    # Simple top bar as rectangle imitation
    display.fill_rect(0, 0, SCREEN_WIDTH, 16, 1)
    display.text(title, 4, 4, 0)  # 0=black on white bar
    display.show()

def drawArrow(x, y):
    # Simple right-pointing arrow for highlight
    display.fill_rect(x, y, 6, 8, 1)

def drawHome():
    drawTitle("Home")
    drawArrow(10, 24 + menuIndex * 16)
    display.text("Motor", 20, 24, 1)
    display.text("Stepper", 20, 40, 1)
    display.text("Monitor", 20, 56, 1)
    display.show()

def drawRPMMenu():
    drawTitle("RPM")
    visibleCount = 3
    topIndex = menuIndex - (menuIndex % visibleCount)
    for i in range(visibleCount):
        idx = topIndex + i
        if idx > 17:
            break
        rpm = 800 + idx * 100
        y = 20 + i * 14
        if idx == menuIndex:
            drawArrow(6, y)
        if idx == confirmFlashIndex:
            display.fill_rect(18, y - 1, 100, 12, 1)
            display.text(str(rpm), 20, y, 0)
        else:
            display.text(str(rpm), 20, y, 1)
    display.show()

def drawStepperMenu():
    drawTitle("OCS")
    drawArrow(10, 24 + menuIndex * 16)
    display.text("Stepper 1", 20, 24, 1)
    display.text("Stepper 2", 20, 40, 1)
    display.show()

def drawStepperOptionsMenu():
    title = "Stepper 1" if currentStepper == 1 else "Stepper 2"
    drawTitle(title)
    drawArrow(10, 24 + menuIndex * 16)
    display.text("Set origin", 20, 24, 1)
    display.text("Set angle", 20, 40, 1)
    display.show()

def drawSetOriginPage():
    title = "Set Origin 1" if currentStepper == 1 else "Set Origin 2"
    drawTitle(title)
    display.text("Rotate encoder to move", 0, 22, 1)
    display.text("Btn1: Spin motor", 0, 32, 1)
    display.text("Btn3: Set as origin", 0, 42, 1)
    display.text("Back: Return", 0, 52, 1)
    # Show current step count
    steps = stepper1Steps if currentStepper == 1 else stepper2Steps
    display.text("Steps: {}".format(steps), 80, 54, 1)
    display.show()

def drawAngleMenu():
    drawTitle("Angle")
    options = ["10 deg", "30 deg", "45 deg", "90 deg", "180 deg", "Custom"]
    visibleCount = 4
    topIndex = menuIndex - (menuIndex % visibleCount)
    for i in range(visibleCount):
        idx = topIndex + i
        if idx > 5:
            break
        y = 20 + i * 12
        if idx == menuIndex:
            drawArrow(6, y)
        if idx == confirmFlashIndex:
            display.fill_rect(18, y - 1, 100, 12, 1)
            display.text(options[idx], 20, y, 0)
        else:
            display.text(options[idx], 20, y, 1)
    display.show()

def drawCustomAngleMenu():
    drawTitle("Custom")
    angle = menuIndex * 5
    display.text(str(angle) + "\xb0", 40, 32, 1)
    display.show()

def drawMonitorPage():
    drawTitle("Monitor")
    display.text("Motor: {} RPM".format(selectedRPM), 10, 20, 1)
    display.text("Stepper 1: {} deg".format(stepper1Angle), 10, 34, 1)
    display.text("Stepper 2: {} deg".format(stepper2Angle), 10, 48, 1)
    display.show()

def updateMenu():
    if currentMenu == "home":
        global menuIndex
        if menuIndex < 0: menuIndex = 2
        if menuIndex > 2: menuIndex = 0
        drawHome()
    elif currentMenu == "motor":
        if menuIndex < 0: menuIndex = 17
        if menuIndex > 17: menuIndex = 0
        drawRPMMenu()
    elif currentMenu == "stepper":
        if menuIndex < 0: menuIndex = 1
        if menuIndex > 1: menuIndex = 0
        drawStepperMenu()
    elif currentMenu == "stepper_options":
        if menuIndex < 0: menuIndex = 1
        if menuIndex > 1: menuIndex = 0
        drawStepperOptionsMenu()
    elif currentMenu == "set_origin":
        drawSetOriginPage()
    elif currentMenu == "angle":
        if menuIndex < 0: menuIndex = 5
        if menuIndex > 5: menuIndex = 0
        drawAngleMenu()
    elif currentMenu == "custom_angle":
        if menuIndex < 0: menuIndex = 0
        if menuIndex > 72: menuIndex = 72
        drawCustomAngleMenu()
    elif currentMenu == "monitor":
        drawMonitorPage()

def stepStepper(stepper, direction):
    global stepper1Steps, stepper2Steps
    if stepper == 1:
        stepper1Steps += direction
        # TODO: Add your hardware code here
    elif stepper == 2:
        stepper2Steps += direction
        # TODO: Add your hardware code here

def handleEncoder():
    global encoderPos, lastEncoded, menuIndex
    global stepper1Steps, stepper2Steps
    MSB = encA.value()
    LSB = encB.value()
    encoded = (MSB << 1) | LSB
    sum_ = (lastEncoded << 2) | encoded
    inSetOriginMode = (currentMenu == "set_origin" and not originStepperRunning)
    moved = False

    if sum_ in [0b1101, 0b0100, 0b0010, 0b1011]:
        encoderPos += 1
        moved = True
        if inSetOriginMode:
            stepStepper(currentStepper, +1)
    if sum_ in [0b1110, 0b0111, 0b0001, 0b1000]:
        encoderPos -= 1
        moved = True
        if inSetOriginMode:
            stepStepper(currentStepper, -1)
    lastEncoded = encoded

    if not inSetOriginMode:
        if encoderPos >= 2:
            encoderPos = 0
            menuIndex += 1
            updateMenu()
        elif encoderPos <= -2:
            encoderPos = 0
            menuIndex -= 1
            updateMenu()

def handleButtons():
    if not btn1.value():
        utime.sleep_ms(150)
        handleSelect()
    if not pwr_btn.value():
        utime.sleep_ms(150)
        handleBack()
    if not btn3.value():
        utime.sleep_ms(150)
        handleBtn3()

def handleBtn3():
    global stepper1Steps, stepper2Steps, settingOrigin, currentMenu, menuIndex
    if currentMenu == "set_origin" and not originStepperRunning:
        if currentStepper == 1:
            stepper1Steps = 0
        elif currentStepper == 2:
            stepper2Steps = 0
        settingOrigin = False
        currentMenu = "stepper_options"
        menuIndex = 0
        updateMenu()

def handleSelect():
    global currentMenu, menuIndex, selectedRPM
    global stepper1Angle, stepper2Angle, currentStepper, settingOrigin, originStepperRunning
    if currentMenu == "home":
        if menuIndex == 0:
            currentMenu = "motor"
        elif menuIndex == 1:
            currentMenu = "stepper"
        elif menuIndex == 2:
            currentMenu = "monitor"
        menuIndex = 0
        updateMenu()
    elif currentMenu == "motor":
        selectedRPM = 800 + menuIndex * 100
        flashSelected(menuIndex)
    elif currentMenu == "stepper":
        currentStepper = 1 if menuIndex == 0 else 2
        currentMenu = "stepper_options"
        menuIndex = 0
        updateMenu()
    elif currentMenu == "stepper_options":
        if menuIndex == 0:  # Set Origin
            currentMenu = "set_origin"
            settingOrigin = True
            originStepperRunning = False
            updateMenu()
        elif menuIndex == 1:  # Set Angle
            currentMenu = "angle"
            menuIndex = 0
            updateMenu()
    elif currentMenu == "set_origin":
        originStepperRunning = not originStepperRunning
        updateMenu()
        # TODO: add spin/stop code
    elif currentMenu == "angle":
        if menuIndex < 5:
            angles = [10, 30, 45, 90, 180]
            if currentStepper == 1:
                stepper1Angle = angles[menuIndex]
            else:
                stepper2Angle = angles[menuIndex]
            flashSelected(menuIndex)
        else:
            currentMenu = "custom_angle"
            menuIndex = 0
            updateMenu()
    elif currentMenu == "custom_angle":
        custom = menuIndex * 5
        if currentStepper == 1:
            stepper1Angle = custom
        else:
            stepper2Angle = custom
        flashSelected(-2)

def flashSelected(idx):
    global confirmFlashIndex, flashStartTime
    confirmFlashIndex = idx
    flashStartTime = utime.ticks_ms()
    updateMenu()

def handleBack():
    global currentMenu, menuIndex
    if currentMenu in ["motor", "stepper"]:
        currentMenu = "home"
        menuIndex = 0
        drawHome()
    elif currentMenu == "stepper_options":
        currentMenu = "stepper"
        menuIndex = 0
        drawStepperMenu()
    elif currentMenu == "set_origin":
        currentMenu = "stepper_options"
        menuIndex = 0
        drawStepperOptionsMenu()
    elif currentMenu == "angle":
        currentMenu = "stepper_options"
        menuIndex = 0
        drawStepperOptionsMenu()
    elif currentMenu == "custom_angle":
        currentMenu = "angle"
        menuIndex = 0
        drawAngleMenu()
    elif currentMenu == "monitor":
        currentMenu = "home"
        menuIndex = 0
        drawHome()

def main():
    updateMenu()
    global confirmFlashIndex
    while True:
        handleEncoder()
        handleButtons()
        # Handle flash timeout
        if confirmFlashIndex >= 0 and utime.ticks_diff(utime.ticks_ms(), flashStartTime) > 300:
            confirmFlashIndex = -1
            updateMenu()
        utime.sleep_ms(25)

main()

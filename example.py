# Import all board pins.
from board import SCL, SDA
import busio

import board
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw.digitalio import DigitalIO
from adafruit_seesaw.rotaryio import IncrementalEncoder

import sh1106

def showit():
    display.fill(0)
    display.text("Position: {}".format(rposition),12,32,1)
    display.text("Position: {}".format(lposition),12,43,1)
    display.show()

# Create the I2C interface.
i2c = busio.I2C(SCL, SDA,frequency=400000)


display = sh1106.SH1106_I2C(128,64,i2c)
rightseesaw = Seesaw(i2c, addr=0x37)
leftseesaw = Seesaw(i2c, addr=0x38)

right = IncrementalEncoder(rightseesaw)
left = IncrementalEncoder(leftseesaw)

last_rposition = 0
last_lposition = 0
rposition = 0
lposition = 0
showit()

while True:
    dirty = False
    # read position of the rotary encoder
    rposition = right.position
    if rposition != last_rposition:
        last_rposition = rposition
        dirty = True
        
    lposition = left.position
    if lposition != last_lposition:
        last_lposition = lposition
        dirty = True

    if dirty:
        showit()
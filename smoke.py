
#!/usr/bin/env python

import time
import datetime
import math
import os
import blynklib
#import numpy as np

import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)

import Adafruit_GPIO.SPI as SPI
import Adafruit_MAX31855.MAX31855 as MAX31855
import Adafruit_SSD1306

#oled defs
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
RST = None
disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST)

#PID setup
from simple_pid import PID
pid = PID(1, 0, 0, setpoint = 250)
pid.output_limits = (0, 1000)
airflow = 200  #use this to control both the louver and fan
pid.sample_time = 10 #seconds

#blynk setup
from config import * # pull in blynk credentials
blynk = blynklib.Blynk(BLYNK_AUTH, server=server, port=port, heartbeat=60)

# Raspberry Pi hardware SPI configuration.
SPI_PORT1 = 0
SPI_PORT2 = 0
SPI_DEVICE1 = 0
SPI_DEVICE2 = 1
sensor1 = MAX31855.MAX31855(spi=SPI.SpiDev(SPI_PORT1, SPI_DEVICE1, max_speed_hz=5000000))
sensor2 = MAX31855.MAX31855(spi=SPI.SpiDev(SPI_PORT2, SPI_DEVICE2, max_speed_hz=5000000))

# fan relay setup
relayPin = 17
GPIO.setup(relayPin, GPIO.OUT)
GPIO.output(relayPin, False)

# servo setup
servoPin = 18
freq = 50
GPIO.setup(servoPin, GPIO.OUT)
servo = GPIO.PWM(servoPin, freq)
open = 12.5
close = 2.5
stop = 7.5

#init variables
setTemp = 250
curTemp = 72
meatTemp = 32
firstRun = 1  #allows blynk overwrites
switch = 3   # test var - set to 0 to run tests
temp = [250,250,250,250,250]

#Prep display
disp.begin()
disp.clear()
disp.display()
width = disp.width
height = disp.height
image = Image.new('1', (width, height))
draw = ImageDraw.Draw(image)
draw.rectangle((0,0,width,height), outline=0, fill=0)
padding = -2
top = padding
bottom = height-padding
x = 0
font = ImageFont.load_default()

# Register Virtual Pins
@blynk.handle_event('write V2')
def v2_write_handler(pin, value):
    global setTemp # update setTemp point
    setTemp  = int(value[1])


def c_to_f(c):   # handy
        return c * 9.0 / 5.0 + 32.0

def fanON():
	GPIO.output(relayPin, True)

def fanOFF():
	GPIO.output(relayPin, False)

def moving_average(x, w):
	return np.convolve(x, np.ones(w), 'valid') / w

def average(x):
	return sum(x)/len(x)

print('Press Ctrl-C to quit.')

try:
 while True:
    blynk.run() # must be first to allow other blynk functions to work

    if firstRun == 1:
        firstRun = 0
        blynk.virtual_write(2, setTemp)  #reset set smoker setpoint

    rpiTemp = sensor1.readInternalC()
    blynk.virtual_write(10, rpiTemp)   #Get rpi temp and send

    tempread = c_to_f(sensor1.readTempC())
    #temp = np.append(temp, temptemp) # Step 1: Get the current temp

    if tempread == tempread: #skips nans
        temp.append(tempread) #adds latest reading to array
        temp = temp[:-1]     # removes oldest array value
        curTemp = average(temp)      #computes average of last 5 readings

    time.sleep(0.1)

    meatread = sensor2.readTempC()
    if meatread == meatread: meatTemp = meatRead

    print "BBQ Temp: {} *F" .format(curTemp)
    print "Meat Temp: {} *F" .format(meatTemp)
    print "Set Point: {} *F" .format(setTemp)
    blynk.virtual_write(1, curTemp)

    #update pid settings
    pid.setpoint = setTemp #Step 2: Make sure setpoint is up to date
    airflow = pid(curTemp) # Step 3: Compute new 'output'
    p, i, d = pid.components #errors

    #get the time
    now = datetime.datetime.now()
    timeString = now.strftime("%Y-%m-%d %H:%M")

    # Display data on oled
    # Draw a black filled box to clear the image.
    draw.rectangle((0,0,width,height), outline=0, fill=0)
    draw.text((x, top),       timeString,  font=font, fill=255)
    draw.text((x, top+8),     "BBQ Temp: %3.0f F" % curTemp, font=font, fill=255)
    draw.text((x, top+16),    "Meat Temp: %3.0f F" % meatTemp, font=font, fill=255)
    draw.text((x, top+25),    "Set Point: %3.0f F" % setTemp, font=font, fill=255)

    # Display image (box)
    disp.image(image)
    disp.display()

    #test relay and servo
    if switch == 0:
        switch = 1
        fanOFF()
        print('Going Low')
	servo.start(close)
        time.sleep(1)
    else:
        switch = 0
        fanON()
        print('Going High')
        servo.start(open)
        time.sleep(1)

    time.sleep(5.0)


except KeyboardInterrupt:
	print('Exiting from ctrl c')

#except:
#	print('Errors')

finally:
	GPIO.cleanup()

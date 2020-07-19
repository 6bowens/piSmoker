#!/usr/bin/env python

import time
import datetime
import math
import os
import blynklib
import subprocess
from pyky040 import pyky040
import threading
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

# Rotary click callback
def sw_callback():
    global setTemp
    global knob
    setTemp = knob
    print ("Button Click")

# Rotary turn callback
def rotary_callback(counter):
    global knob
    knob = counter
    #print("Counter value: ", counter)  #uncomment for debug

#rotary encoder
my_encoder = pyky040.Encoder(CLK=23, DT=22, SW=27)
my_encoder.setup(scale_min=200, scale_max=600, step=5, chg_callback=rotary_callback, sw_callback=sw_callback, sw_debounce_time=300)
my_thread = threading.Thread(target=my_encoder.watch)
my_thread.start() # start rotary encoder thread
knob = 250

#PID setup
from simple_pid import PID
pid = PID(1, 0, 0, setpoint = 250)
#pid.proportional_on_measurement = True
pid.output_limits = (0, 100)
output = 50  #use this to control both the louver and fan
pid.sample_time = 10 # seconds
pidtime = 10
runPID = 1

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
GPIO.output(relayPin, True)

# servo setup
servoPin = 18
freq = 50
GPIO.setup(servoPin, GPIO.OUT)
servo = GPIO.PWM(servoPin, freq)
close = 10 #12.5 is fully closed
open = 2.5
angle = 6 # 6 is 50% closed

#init variables
setTemp = 250
curTemp = 5
meatTemp = 5
firstRun = 1  #allows blynk overwrites
switch = 5   #test var - set to 0 to run tests
temp = [70] * 10
meatList = [70] * 10


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

#Query IP for display
cmd = "hostname -I | cut -d\' \' -f1"
IP = subprocess.check_output(cmd, shell = True )


# Register Virtual Pins
@blynk.handle_event('write V2')
def v2_write_handler(pin, value):
    global setTemp # update setTemp point
    setTemp  = int(value[-1])

@blynk.handle_event('write V5')
def v5_write_handler(pin, value):
    openVent()

@blynk.handle_event('write V6')
def v6_write_handler(pin, value):
    closeVent()

@blynk.handle_event('write V9')
def v9_write_handler(pin, value):
    if int(value[-1]) == 1:
	fanON()
    elif int(value[-1]) == 0:
	fanOFF()

@blynk.handle_event('write V11')
def v11_write_handler(pin, value):
    global runPID
    runPID  = int(value[-1])

@blynk.handle_event('write V13')
def v13_write_handler(pin, value):
    global angle
    angle = open
    moveVent(angle)

@blynk.handle_event('write V14')
def v14_write_handler(pin, value):
    global angle
    angle = close
    moveVent(angle)

def closeVent():
    global angle
    if angle < 9.5:
    	angle += 0.5
    	GPIO.setup(servoPin, GPIO.OUT)
    	servo.start(angle)
    	time.sleep(1)
    	GPIO.setup(servoPin, GPIO.IN)
	print "Closing Louver"

def openVent():
    global angle
    if angle > 2.5:
    	angle -= 0.5
    	GPIO.setup(servoPin, GPIO.OUT)
    	servo.start(angle)
    	time.sleep(1)
    	GPIO.setup(servoPin, GPIO.IN)
	print "Opening Louver"

def moveVent(angle):
	GPIO.setup(servoPin, GPIO.OUT)
        servo.start(angle)
        time.sleep(1)
        GPIO.setup(servoPin, GPIO.IN)
        print "Moving Louver"

def c_to_f(c):   # handy
        return c * 9.0 / 5.0 + 32.0

def fanON():
	GPIO.output(relayPin, False)
	print "Fan On"

def fanOFF():
	GPIO.output(relayPin, True)
	print "Fan Off"

def average(x):
	return sum(x)/len(x)

try:
 while True:
    blynk.run() # must be first to allow other blynk functions to work

    #run this only on first loop .. after blynk has run
    if firstRun == 1:
        firstRun = 0
        blynk.virtual_write(2, setTemp)  #reset set smoker setpoint
        lastTime = 0

    # run this section only every pidTime windows to slow down PID internval
    if (time.time() - lastTime) > pidtime:


        # Get RPi Internal Chip Temp for shits
        rpiTemp = sensor1.readInternalC()
        blynk.virtual_write(10, rpiTemp)

        # PID Step #1: Get the current temp and average over time
        tempread =c_to_f(sensor2.readTempC())

        if tempread == tempread:    #skips nans
        	temp.append(tempread)   #adds latest reading to array
        	del temp[0]             #removes oldest array value
        	curTemp = average(temp) #computes average of last X readings

        time.sleep(0.1) #give a sec between readings

        #print temp  # debug print

        # Grab the meat reading
        meatread =c_to_f(sensor1.readTempC())

        if meatread == meatread:
            meatList.append(meatread)
            del meatList[0]
            meatTemp = average(meatList)

        #print meatList   # debug print

        #update pid settings
        pid.setpoint = setTemp #Step 2: Make sure setpoint is up to date
        output = pid(curTemp) # Step 3: Compute new 'output'
        p, i, d = pid.components #errors - print to tune


	#only runPID if desired ADD CONTROL LOGIC HERE
	if (runPID == 1):
		print "Running PID"
		angle = ( (1 - output/100) * 7.5) + 2.5
		moveVent(angle)

        #calculate percent open (this is here for non-PID mode
        louver = (1 - ((angle - 2.5) / 7.5)) * 100

        #get the time
        now = datetime.datetime.now()
        timeString = now.strftime("%Y-%m-%d %H:%M")

        #test prints
        print "BBQ Temp: {} *F" .format(curTemp)
        print "Meat Temp: {} *F" .format(meatTemp)
        print "Set Point: {} *F" .format(setTemp)
        blynk.virtual_write(1, curTemp)
        blynk.virtual_write(2, setTemp)
        blynk.virtual_write(3, meatTemp)
        blynk.virtual_write(7, louver)
        blynk.virtual_write(8, angle)
        blynk.virtual_write(12, output)

        lastTime = time.time() #reset pid interval (leave last)

    disp.clear()
    # Display data on oled
    # Draw a black filled box to clear the image.
    draw.rectangle((0,0,width,height), outline=0, fill=0)
    draw.text((x, top),      "   " + timeString,  font=font, fill=255)
    draw.text((x, top+8),     "   IP: " + str(IP),   font=font, fill=255)
    draw.text((x, top+16),    "   RPi Temp: %3.0f C" % rpiTemp, font=font, fill=255)

    draw.text((x, top+32),    "   Set Point: %3.0f F" % knob, font=font, fill=255)

    if (setTemp == knob):
    	draw.text((x, top+40),    "   BBQ Temp:  %3.0f F" % curTemp, font=font, fill=255)
    	draw.text((x, top+56),    "   Meat Temp: %3.0f F" % meatTemp, font=font, fill=255)

    # Display image (box)
    disp.image(image)
    disp.display()

    #test relay and servo
    if switch == 0:
        switch = 1
        fanOFF()
        print('Going Low')
	servo.start(half)
        time.sleep(1)
    elif switch == 1:
        switch = 0
        fanON()
        print('Going High')
        servo.start(open)
        time.sleep(1)

    #test servo
    if switch == 3:
        while (angle < 13):
            print angle
            servo.start(angle)
            angle += 0.5
            time.sleep (5)

    time.sleep(0.1)

except KeyboardInterrupt:
	print('Exiting from ctrl c')

#except:
#	print('Errors')

finally:
	GPIO.cleanup()

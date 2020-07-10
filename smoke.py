#!/usr/bin/env python

import time
import datetime
import os
import blynklib

import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
import Adafruit_GPIO.SPI as SPI
import Adafruit_MAX31855.MAX31855 as MAX31855

from config import *

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
curTemp = 0
firstRun = 1  #allows blynk overwrites
switch = 3   # test var - set to 0 to run tests

# Register Virtual Pins
@blynk.handle_event('write V2')
def v2_write_handler(pin, value):
    global setTemp # update setTemp point
    setTemp  = int(value[0])

def c_to_f(c):   # handy
        return c * 9.0 / 5.0 + 32.0

def fanON():
	GPIO.output(relayPin, True)

def fanOFF():
	GPIO.output(relayPin, False)


print('Press Ctrl-C to quit.')
try:
 while True:
    blynk.run() # must be first to allow other blynk functions to work

    if firstRun == 1:
        firstRun = 0
        blynk.virtual_write(2, setTemp)  #reset set smoker setpoint


    rpiTemp = sensor1.readInternalC()
    blynk.virtual_write(10, rpiTemp)  # read rpi temp and send

    temp = sensor1.readTempC()
    curTemp = temp # add a rolling average here !!!!!!!!!!!!!!!!

    time.sleep(0.1)
    meatTemp = sensor2.readTempC()

    print('Air Temp: {0:0.3F}*C / {1:0.3F}*F'.format(curTemp, c_to_f(curTemp)))
    print('Meat Temp: {0:0.3F}*C / {1:0.3F}*F'.format(meatTemp, c_to_f(meatTemp)))
    print('Set Point: {}'.format(setTemp))
    blynk.virtual_write(1, curTemp)










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

    time.sleep(3.0)


except KeyboardInterrupt:
	print('Exiting from ctrl c')


#except:
#	print('Errors')

finally:
	GPIO.cleanup()



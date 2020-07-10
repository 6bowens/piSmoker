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

# relay setup
relayPin = 17

GPIO.setup(relayPin, GPIO.OUT)
GPIO.output(relayPin, GPIO.HIGH)

# servo setup
servoPin = 18

#init variables
setTemp = 250
curTemp = 0
firstRun = 1
switch = 0

# Register Virtual Pins
@blynk.handle_event('write V2')
def v2_write_handler(pin, value):
    global setTemp # update setTemp point
    setTemp  = int(value[0])

def c_to_f(c):   # handy
        return c * 9.0 / 5.0 + 32.0

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

    #test relay
    if switch == 0:
        switch = 1
        GPIO.output(relayPin, GPIO.LOW)
        print('Going Low')
    else:
        switch = 0
        GPIO.output(relayPin, GPIO.HIGH)
        print('Going High')

    print('Set Point: {}'.format(setTemp))
    blynk.virtual_write(1, curTemp)
    time.sleep(3.0)


except KeyboardInterrupt:
	print('Exiting from ctrl c')


except:
	print('Errors')

finally:
	GPIO.cleanup()



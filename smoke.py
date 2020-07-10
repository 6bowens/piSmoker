#!/usr/bin/env python

import time
import datetime
import os
import blynklib

import Adafruit_GPIO.SPI as SPI
import Adafruit_MAX31855.MAX31855 as MAX31855

from config import *

blynk = blynklib.Blynk(BLYNK_AUTH, server=server, port=port, heartbeat=60)

# Raspberry Pi hardware SPI configuration.
SPI_PORT = 0
SPI_DEVICE = 0
sensor = MAX31855.MAX31855(spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE, max_speed_hz=5000000))

#init variables
setTemp = 250
curTemp = 0
firstRun = 1

# Register Virtual Pins
@blynk.handle_event('write V2')
def v2_write_handler(pin, value):
    global setTemp # update setTemp point
    setTemp  = int(value[0])

def c_to_f(c):   # handy
        return c * 9.0 / 5.0 + 32.0

print('Press Ctrl-C to quit.')


while True:
    blynk.run() # must be first to allow other blynk functions to work

    if firstRun == 1:
        firstRun = 0
        blynk.virtual_write(2, setTemp)  #reset set smoker setpoint


    rpiTemp = sensor.readInternalC()
    blynk.virtual_write(10, rpiTemp)  # read rpi temp and send

    temp = sensor.readTempC()
    curTemp = temp # add a rolling average here !!!!!!!!!!!!!!!!

    print('Thermocouple Temperature: {0:0.3F}*C / {1:0.3F}*F'.format(curTemp, c_to_f(temp)))
    print('Set Point: {}'.format(setTemp))
    blynk.virtual_write(1, curTemp)
    time.sleep(3.0)

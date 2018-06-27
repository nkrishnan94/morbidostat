
"""The basic idea is this: the bugs grow for a certain period of time, dt. After this time, if their optical density,
OD, (as read by a photodetector) is above a threshhold, OD_thr, and they have grown since the last time point, drug is
administered through a pump, P_drug. If OD is less than OD_thr, then nutrient solution is added through another pump,
P_nut.

This system will be controlled by a Raspberry Pi, using the SPI and GPIO ports. To activate the pumps, GPIO ports are
set to 1/GPIO.HIGH/True for a certain period of time, t_pump. Optical density data is read via an analogue to digital
converter attached to one of the SPI ports on the RPi.

Data will be saved on the RPi and stored in the cloud. Using the Slack API, we will be able to query the RPi to find
out how the experiment is progressing."""

import time
import datetime
import csv
import threading

import RPi.GPIO as GPIO
import Adafruit_ADS1x15

# define experimental variables
time_between_pumps = 0.5  # how often to activate pumps, in minutes
OD_thr = 15  # threshold above which to activate drug pump
time_between_ODs = 2  # how often to gather OD data, in seconds
time_between_writes = 1  # how often to write out OD data, in minutes
running_data = []  # the list which will hold our 2-tuples of time and OD

# setup the GPIO pins to control the pumps
P_drug = 20
P_nut = 25
P_waste = 24
pin_list = [P_drug, P_nut, P_waste]
GPIO.setmode(GPIO.BCM)
for pin in pin_list:
    GPIO.setup(pin, GPIO.OUT)

# set up I2C to read OD data
adc = Adafruit_ADS1x15.ADS1015()
photoreceptor_channel = 0


# Read data from the ADC
def get_OD():
    value = adc.read_adc(photoreceptor_channel)
    return value


# activate the pumps
pump_activation_times = {P_drug: 200, P_nut: 200, P_waste: 200}  # in seconds
def activate_pump(pump):
    GPIO.output(pump, 1)
    print('Turning on pump',pump)
    time.sleep(pump_activation_times[pump])
    GPIO.output(pump, 0)
    print('Turning off pump',pump)


# write data
def write_data(data):
    filename = str(datetime.datetime.now()) + '.csv'
    print('writing data to', filename)
    with open(filename, 'w') as output:
        writer = csv.writer(output)
        for timepoint in data:
            writer.writerow(timepoint)


GPIO.output(24,1)
GPIO.output(20,1)
GPIO.output(25,1)

time.sleep(10)

GPIO.output(20,0)
GPIO.output(24,0)
GPIO.output(25,0)







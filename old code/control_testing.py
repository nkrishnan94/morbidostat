
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
import Adafruit_ADS1x15
import RPi.GPIO as GPIO
from slackclient import SlackClient

# define experimental variables
t_control = 0.5  # how often to activate pumps, in minutes
OD_thr = 15
t_pump = 1  # how long to run the pumps for, in seconds
data_dt = 1  # how often to gather OD data, in seconds
t_write = 0.5  # how often to write out OD data, in minutes
running_data = []

# set the GPIO pins to control the pumps
P_drug = 20
P_nut = 21
P_waste = 16
pin_list = [P_drug, P_nut, P_waste]
GPIO.setmode(GPIO.BCM)
for pin in pin_list:
    GPIO.setup(pin, GPIO.OUT)

# set up I2C
adc = Adafruit_ADS1x15.ADS1015()
photoreceptor_channel = 0


# Read data from the ADC
def get_OD():
    value = adc.read_adc(photoreceptor_channel)
    return value

# activate the pumps
def activate_pump(pump):
    GPIO.output(pump, 1)
    time.sleep(t_pump)
    GPIO.output(pump, 0)


# control loop
dt_control = 0
dt_write = 0
while True:
    time.sleep(data_dt)
    dt_control += data_dt
    dt_write += data_dt

    OD = get_OD()
    print(OD)
    running_data.append(OD)

    if dt_control >= (t_control * 60):
        if OD > OD_thr:
            activate_pump(P_drug)
        else:
            activate_pump(P_nut)

        activate_pump(P_waste)

        dt_control = 0

    if dt_write >= (t_write * 60):
        dt_write = 0
        print('writing')
        print(running_data)
        with open(str(datetime.datetime.now()) + '.csv', 'w') as output:
            writer = csv.writer(output,lineterminator='\n')
            for timepoint in running_data:
                writer.writerow([timepoint])
        running_data = []

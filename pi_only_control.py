
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

import Adafruit_ADS1x15
import RPi.GPIO as GPIO

# define experimental variables
time_between_pumps = 0.5  # how often to activate pumps, in minutes
OD_thr = 15  # threshold above which to activate drug pump
time_between_ODs = 2  # how often to gather OD data, in seconds
time_between_writes = 0.5  # how often to write out OD data, in minutes
running_data = []  # the list which will hold our 2-tuples of time and OD

# setup the GPIO pins to control the pumps
P_drug = 20
P_nut = 21
P_waste = 16
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
pump_activation_times = {P_drug: 1, P_nut: 1, P_waste: 1}  # how long to run the pumps for, in seconds
def activate_pump(pump):
    GPIO.output(pump, 1)
    time.sleep(pump_activation_times[pump])
    GPIO.output(pump, 0)


# write data
def write_data(data):
    filename = str(datetime.datetime.now()) + '.csv'
    print('writing data to', filename)
    with open(filename, 'w') as output:
            writer = csv.writer(output, lineterminator='\n')
            for timepoint in running_data:
                writer.writerow([timepoint])


elapsed_loop_time = 0

# control loop
while True:

    # note the time the loop starts
    beginning = time.time()

    # read OD data to be used for both controlling and saving during this loop
    OD = get_OD()
    running_data.append((beginning, OD))
    print(running_data[-1])
    print(elapsed_loop_time)

    # activate pumps if needed and it's time (threaded to preserve time b/w ODs if this takes > time_between_ODs)
    if elapsed_loop_time % (time_between_pumps * 60) < 1:
        print('activating pumps')
        if OD > OD_thr:
            threading.Thread(target=activate_pump, args=(P_drug))
        else:
            threading.Thread(target=activate_pump, args=(P_nut))

        threading.Thread(target=activate_pump, args=(P_waste))

    # save the data to disk if it's time (threaded to preserve time b/w ODs if this takes > time_between_ODs)
    if time_between_writes % (time_between_writes * 60) < 1:
        threading.Thread(target=write_data, args=(running_data))
        # clear the data
        running_data = []
    
    GPIO.cleanup()
    
    # note the time the functions end
    end = time.time()
    interval = beginning - end

    # wait some period of time so that the total is time_between_ODs
    if interval > time_between_ODs:
        print('warning: loop took longer than requested OD interval')
    time.sleep(time_between_ODs - interval)
    elapsed_loop_time += time_between_ODs

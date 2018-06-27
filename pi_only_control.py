
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
import os
import RPi.GPIO as GPIO
import Adafruit_ADS1x15
import numpy as np
# define experimental variables
time_between_pumps = 12  # how often to activate pumps, in minutes
OD_thr = 1000  # threshold above which to activate drug pump
time_between_ODs = 2  # how often to gather OD data, in seconds
time_between_writes = 1  # how often to write out OD data, in minutes
running_data = []  # the list which will hold our 2-tuples of time and OD
avg_OD = []
total_time = 43200*time_between_ODs #in loops

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
pump_activation_times = {P_drug: 5/2.2, P_nut: 5/2.4, P_waste: 5/2.6}  # in seconds
def pump_on(pump):
    GPIO.output(pump, 1)
    print('Turning on pump',pump)
    
def pump_off(pump):
    
    GPIO.output(pump, 0)
    print('Turning off pump',pump)

def all_pump_off():
    for i in pin_list:
        GPIO.output(i, 0)
    print('Turning off all pumps')
        
        
start_time =datetime.datetime.now()
os.makedirs(str(start_time))
# write data
def write_data(data):
    filename = str(datetime.datetime.now() + '.csv')
    print('writing data to', filename)
    with open(filename, 'w') as output:
        writer = csv.writer(output)
        for timepoint in data:
            writer.writerow(timepoint)
            
def savefunc(outfile,data):


    outfile = outfile
    out = open(outfile, 'a')
    l = data
    with out as output:
        writer = csv.writer(output)
        for timepoint in data:
            writer.writerow(timepoint) 


elapsed_loop_time = 0
loops = 0
filenum = 0

# control loop

print('Experiment begun at %02s:%02s:%02s' % (start_time.hour, start_time.minute, start_time.second))

while loops < total_time/time_between_ODs:
	loops += 1

    # note the time the loop starts
	beginning = time.time()

    # read OD data to be used for both controlling and saving during this loop
	OD = get_OD()
	avg_OD.append(OD)
	now = datetime.datetime.now()
	print('Elapsed Time: %02s:%02s:%02s; OD = ' % (now.hour, now.minute, now.second), OD)
	nut = 0	
	drug = 1
	waste = 2
    # activate pumps if needed and it's time (threaded to preserve time b/w ODss if this takes > time_between_OD
	if elapsed_loop_time % (time_between_pumps * 60) < 1:
		if np.mean(avg_OD[-30:-1]) > OD_thr:
			print('OD Threshold exceeded, pumping drug')
			threading.Thread(target=pump_on, args=(P_drug,)).start()
			threading.Timer(pump_activation_times[P_drug],pump_off, args=(P_drug,)).start()
			drug = 2   
		else:
			print('OD below threshold, pumping nutrient')
			threading.Thread(target=pump_on, args=(P_nut,)).start()
			threading.Timer(pump_activation_times[P_nut],pump_off, args=(P_nut,)).start()
			nut = 1
		threading.Thread(target=pump_on, args=(P_waste,)).start()
		threading.Timer(pump_activation_times[P_waste],pump_off, args=(P_waste,)).start()
		waste = 3
		avg_OD = []
    # save the data to disk if it's time (threaded to preserve time b/w ODs if this takes > time_between_ODs)
	
	running_data.append((OD,nut,drug,waste,now))
	
	if elapsed_loop_time % (time_between_writes * 60) < 1:
		print('saving to disk')
		
		outfile = "%s/%s.%d.csv" % (start_time, start_time, filenum)
		threading.Thread(target=savefunc, args=(outfile,running_data,)).start()
        # clear the data
		running_data = []
		filenum =+1

    # note the time the functions end
	end = time.time()
	interval = beginning - end

    # wait some period of time so that the total is time_between_ODs
	if interval > time_between_ODs:
		print('warning: loop took longer than requested OD interval')
	time.sleep(time_between_ODs - interval)
	elapsed_loop_time += time_between_ODs
all_pump_off()

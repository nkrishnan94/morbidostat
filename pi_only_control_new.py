
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
#time_between_writes = 1  # how often to write out OD data, in minutes

total_time = 30*60*60 #in seconds
loops_between_ODs = 1 
loops_between_pumps = (time_between_pumps*60)/time_between_ODs # time between pumps in loops
#loops_between_writes = (time_between_writes*60)/time_between_ODs # time bewteen writes in loops
num_cham = 1 # number of morbidostat vials being used

OD_av_length = 30 #number of OD measurements to be averaged

# setup the GPIO pins to control the pumps
P_drug_pins = [20]
P_nut_pins = [24]
P_waste_pins = [25]
pin_list = [P_drug_pins+ P_nut_pins+P_waste_pins]
GPIO.setmode(GPIO.BCM)
for pin in pin_list:
    GPIO.setup(pin, GPIO.OUT)

# set up I2C to read OD data
adc = Adafruit_ADS1x15.ADS1015()
photoreceptor_channel_pins = [0]


P_drug_times = [2/1.7]
P_nut_times = [2/1.7]
p_waste_times = [2/1.8]
class Morbidostat():
    # Read data from the ADC
    def __init__(self):
        self.running_data = []  # the list which will hold our 2-tuples of time and OD
        self.pump_data = []
        self.currOD = np.zeros(num_cham)
        # averaged OD value 
        self.avOD = np.zeros(num_cham)
        # OD averaging buffer 
        self.avOD_buffer = np.zeros((OD_av_length, num_cham))
        self.start_time =datetime.datetime.now()
        os.makedirs(str(self.start_time))
        
        self.elapsed_loop_time = 0
        self.loops = 0
        
        self.nut = 0	
        self.drug = 1
        self.waste = 2  
        
        self.outfile_OD = "%s/ODdata_%s.csv" % (self.start_time, self.start_time)
        file = open(self.outfile_OD, 'ab') 
        wr = csv.writer(file)
        wr.writerow(['Current OD', 'Average OD','OD timing'])
        file.close()

        self.outfile_pump = "%s/pump_%s.csv" % (self.start_time, self.start_time)
        file = open(self.outfile_pump, 'ab') 
        wr = csv.writer(file)
        wr.writerow(['Nutrient Pump', 'Drug Pump','Waste Pump','Pump timing'])
        file.close()


        print('Experiment begun at %02s:%02s:%02s' % (self.start_time.hour, self.start_time.minute, self.start_time.second))
        self.on_timer()

    def get_OD(self):
        self.value = []
        for i in photoreceptor_channel_pins:
            self.value.append( adc.read_adc(i))
        self.currOD = np.asarray(self.value)
        #print("OD: current voltage (raw) = ", self.currOD[0:num_cham])
        print('Elapsed Time: %02s:%02s:%02s; OD = ' % (self.now.hour, self.now.minute, self.now.second), self.currOD[0:num_cham])
        
        #process the data
        self.avOD_buffer = np.append(self.avOD_buffer, self.currOD.reshape(1,num_cham), axis=0) 
 
        # then remove the first item in the array, i.e. the oldest 
        self.avOD_buffer = np.delete(self.avOD_buffer, 0, axis=0)          
        # calculate average for each flask
        self.avOD = np.mean(self.avOD_buffer, axis=0)
        
    
    # activate the pumps
    #pump_activation_times = {P_drug: [5/2.2], P_nut: 5/2.4, P_waste: 5/2.6}  # in seconds

    
    
    def pump_on(self,pump):
        GPIO.output(pump, 1)
        print('Turning on pump',pump)
        
    def pump_off(self,pump):
        
        GPIO.output(pump, 0)
        print('Turning off pump',pump)
    
    def all_pump_off(self):
        for i in pin_list:
            GPIO.output(i, 0)
        print('Turning off all pumps')
            
            
    
    # write data
    #def write_data(self,data):
    #    filename = (str('datetime.datetime.now()) + '.csv')
    #    print('writing data to', filename)
    #    with open(filename, 'w') as output:
    #        writer = csv.writer(output)
    #        for timepoint in data:
    #            writer.writerow(timepoint)
                
    def savefunc(self):
        print('saving to disk')
        OD_tmplist = []
        pump_tmplist = []
        
        file = open(self.outfile_OD, 'ab') 
        
        for i in range(num_cham):        
            OD_tmplist.append(self.currOD[i])
            OD_tmplist.append(self.avOD[i])
           
            
        OD_tmplist.append(self.now)
        wr = csv.writer(file)
        wr.writerow(OD_tmplist)
        file.close()

        
        file = open(self.outfile_pump, 'ab') 
        pump_tmplist =[self.nut,self.drug,self.waste,self.now]
        wr = csv.writer(file)
        wr.writerow(pump_tmplist)
        file.close()
        self.nut = 0	
        self.drug = 1
        self.waste = 2
    
    
    
    def morbidostat(self):

        for i in range(num_cham):
            if self.avOD[i] > OD_thr:
                print('OD Threshold exceeded, pumping drug')
                threading.Thread(target=self.pump_on, args=(P_drug_pins[i],)).start()
                threading.Timer(P_drug_times[i],self.pump_off, args=(P_drug_pins[i],)).start()
                self.drug = 2 
            else:
                print('OD below threshold, pumping nutrient')
                threading.Thread(target=self.pump_on, args=(P_nut_pins[i],)).start()
                threading.Timer(P_nut_times[i],self.pump_off, args=(P_nut_pins[i],)).start()
                self.nut = 1
            threading.Thread(target=self.pump_on, args=(P_waste_pins[i],)).start()
            threading.Timer(P_nut_times[i],self.pump_off, args=(P_waste_pins[i],)).start()
            self.waste = 3
    		
    
    def on_timer(self):
        if self.loops < total_time/time_between_ODs:
            threading.Timer(time_between_ODs,self.on_timer).start()
        else:
            self.now = datetime.datetime.now()
            print('Experiment Complete at %02s:%02s:%02s ' % (self.now.hour, self.now.minute, self.now.second))
                
            
        self.loops += 1
        #print(self.loops)
        # note the time the loop starts
        self.beginning = time.time()
        self.now = datetime.datetime.now()
        
        # read OD data to be used for both controlling and saving during this loop
        threading.Thread(target=self.get_OD()).start()
        print('Elapsed Time: %02s:%02s:%02s; OD = ' % (self.now.hour, self.now.minute, self.now.second), self.currOD)

        # activate pumps if needed and it's time (threaded to preserve time b/w ODss if this takes > time_between_OD
        if self.loops % (loops_between_pumps ) < 1:
        
            threading.Thread(self.morbidostat()).start()
        # save the data to disk if it's time (threaded to preserve time b/w ODs if this takes > time_between_ODs)
    	
        threading.Thread(self.savefunc()).start()
    
        # note the time the functions end
        self.end = time.time()
        self.interval = self.beginning - self.end
    
        # wait some period of time so that the total is time_between_ODs
        if self.interval > time_between_ODs:
            print('warning: loop took longer than requested OD interval')
        time.sleep(time_between_ODs - self.interval)
        #self.elapsed_loop_time += time_between_ODs
    
Morbidostat()

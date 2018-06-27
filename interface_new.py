from functools import partial
from random import random
from threading import Thread
import time
import pandas as pd
import os
import subprocess
import psutil

from bokeh.models import ColumnDataSource, Legend
from bokeh.models.widgets import Button, Select, Dropdown
from bokeh.plotting import curdoc, figure
from bokeh.layouts import layout, gridplot, widgetbox

from tornado import gen

# I don't know what decorators do, especially stuff dealing with tornado
@gen.coroutine
def update(currOD, avOD,pump_nut, pump_drug, pump_waste, OD_timing, pump_timing):
    #print(currOD, avOD,pump_nut, pump_drug, pump_waste, OD_timing, pump_timing)    
    source.stream(dict(currOD=[currOD], avOD=[avOD],pump_nut=[pump_nut], pump_drug=[pump_drug], pump_waste=[pump_waste], OD_timing=[OD_timing], pump_timing=[pump_timing]), 129600)

# set the current directory where files are being written
curr_dir = os.getcwd()


# define functions
def find_current_file():
    # bring in the current working directory
    global curr_dir

    # make a list of 2-tuples  consisting of each file in the directory and the last time it was modified
    #files = [[x, os.stat(x).st_mtime] for x in os.listdir(curr_dir) if x[-1] == 'v']
    ODdata_files = [[os.path.join(root, name),os.stat(os.path.join(root, name)).st_mtime] 
         for root, dirs, files in os.walk(curr_dir)
         for name in files
         if name.endswith((".csv")) and name.startswith(("ODdata"))]
    

    # sort the list of lists based on the last modified time
    ODdata_files_sorted = sorted(ODdata_files, key=lambda x: x[1])

    # the current file being written to is the last file in the sorted list and we only want the file name
    if len(ODdata_files_sorted)==0:
        ODdata_current_file = []
    else:
        ODdata_current_file = ODdata_files_sorted[-1][0]
    
    
    pump_files = [[os.path.join(root, name),os.stat(os.path.join(root, name)).st_mtime] 
         for root, dirs, files in os.walk(curr_dir)
         for name in files
         if name.endswith((".csv")) and name.startswith(("pump"))]
    
    # sort the list of lists based on the last modified time
    pump_files_sorted = sorted(pump_files, key=lambda x: x[1])
    
    # the current file being written to is the last file in the sorted list and we only want the file name
    

    if len(pump_files_sorted)==0:
        pump_current_file = []
    else:
        pump_current_file = pump_files_sorted[-1][0]
            
    
    return ODdata_current_file, pump_current_file


def tail(f, n):
    proc = subprocess.Popen('tail -n'+str(n)+' '+ f, shell = True, stdout=subprocess.PIPE)
    lines = proc.stdout.readlines()
    return lines

def read_in_data():
    # find the file that's currently being written to
    ODdata_current_file, pump_current_file = find_current_file()  # maybe this doesn't need to happen every time
    #print(ODdata_current_file,pump_current_file)   
    if len(ODdata_current_file) != 0:
    # load the header and the last row into memory as a dataframe
        ODline = subprocess.Popen("tail -n1 '%s'"  %  ODdata_current_file,  shell =True, stdout=subprocess.PIPE).stdout.readlines()
        pumpline = subprocess.Popen("tail -n1 '%s'"  %  pump_current_file,  shell =True, stdout=subprocess.PIPE).stdout.readlines()
        ODline=[ODline[0].decode()[0:-2].split(",")]
        pumpline=[pumpline[0].decode()[0:-2].split(",")]
        df_OD = pd.DataFrame(ODline,columns = ['Current OD', 'Average OD','OD timing'])
        df_OD['OD timing'] = pd.to_datetime(df_OD['OD timing'])
        
        df_pump = pd.DataFrame(pumpline,columns = ['Nutrient Pump', 'Drug Pump','Waste Pump','Pump timing'])
        df_pump['Pump timing'] = pd.to_datetime(df_pump['Pump timing'])
        # set the values of the new data;
        # the labels (e.g., Nutrient Pump) will likely need to changed in the final version
        currOD = df_OD.iloc[-1, 0]
        avOD = df_OD.iloc[-1, 1]
        OD_timing = df_OD.iloc[-1, 2]
        
        pump_nut = df_pump.iloc[-1,0]
        pump_drug = df_pump.iloc[-1,1]
        pump_waste = df_pump.iloc[-1,2]
        pump_timing = df_pump.iloc[-1,3]
    
    
    
    
        return currOD, avOD,pump_nut, pump_drug, pump_waste, OD_timing, pump_timing
    




def load_new_data():
    while len(find_current_file()) ==0:
        time.sleep(1)
    while True:
        # gather the new data
        currOD, avOD,pump_nut, pump_drug, pump_waste, OD_timing, pump_timing = read_in_data()
        
        # # print to the console so you know it's working during this testing period
        # print('http://bit.ly/2mPJog3')

        # but update the document from callback

        doc.add_next_tick_callback(partial(update, currOD, avOD,pump_nut, pump_drug, pump_waste, OD_timing, pump_timing))
        # take a wee break until the next data point has been written;
        # this will ideally be replaced by having a signal sent from the control 
        # script that a new measurement has been taken/written
        time.sleep(2)


# tell the program what to do when the prime pumps button is pushed
def prime_handler():
    print('pumps priming')
    # uncomment and change filename below when ready
    subprocess.Popen('python pi_only_equilibrate.py', shell=True)


# tell the program what to do when the begin experiment button is pushed
def activate_handler():
    print('beginning experiment')
    # uncomment and change filename below when ready
    subprocess.Popen('python pi_only_control_new.py', shell=True)
    time.sleep(2)
    # fire it up
    thread = Thread(target=load_new_data)
    thread.start()
    

# tell the program what to do when the save data button is pushed
def upload_handler():
    print('uploading data to Dropbox')
    # uncomment and change filename below when ready
    # subprocess.Popen('python save_data.py', shell=True)


# # tell the program what to do when the quit button is pushed
# def quit_handler():
#     print('shutting down')
#     # uncomment and change filename below when ready
#     # subprocess.Popen('python stop_and_reset.py', shell=True)


# tell the program what to do when the dropdown is changed
def dropdown_handler_time(attr, old, new):
    p1.x_range.follow_interval = int(dropdown_time.value)
    p2.x_range.follow_interval = int(dropdown_time.value)
    
def dropdown_handler_avg(attr,old,new):
    #p1 = figure(x_axis_type='datetime', plot_width=500, title=dropdown_avg.value[1])
    if dropdown_avg.value == 'avOD':
        p1 = figure(x_axis_type='datetime', plot_width=500, title='Averaged OD Readings')    
        l_od = p1.line(x='OD_timing', y=dropdown_avg.value, source=source, color='black')
    else:
        if dropdown_avg.value == 'currOD':
            p1 = figure(x_axis_type='datetime', plot_width=500, title='Raw OD Readings') 
            l_od = p1.line(x='OD_timing', y=dropdown_avg.value, source=source, color='black')



    
# this must only be modified from a Bokeh session callback
#currOD, avOD,pump_nut, pump_drug, pump_waste, OD_timing, pump_timing = read_in_data()
currOD, avOD,pump_nut, pump_drug, pump_waste, OD_timing, pump_timing = [0,0,0,0,0,0,0]
source = ColumnDataSource(data=dict(currOD=[], avOD=[],pump_nut=[], pump_drug=[], pump_waste=[], OD_timing=[], pump_timing=[]))

# This is important! Save curdoc() to make sure all threads
# see the same document.
doc = curdoc()

# time (x-axis) window dropdown
menu_time = [('10 seconds', str(int(1000*10))),('1 minute', str(int(1000*60))), ('15 minutes', str(int(1000*60*15))),
        ('1 hour', str(int(1000*60*60))), ('24 hours', str(int(1000*60*60*24)))]
dropdown_time = Dropdown(label='Time Window:', menu=menu_time)
dropdown_time.on_change('value', dropdown_handler_time)

menu_avg = [('Averaged OD', 'avOD'), ('Raw OD', 'currOD')]
dropdown_avg = Dropdown(label='OD Data type', menu=menu_avg)
dropdown_avg.on_change('value', dropdown_handler_avg)

# OD data plot
p1 = figure(x_axis_type='datetime', plot_width=500, title='Averaged OD Readings')
l_od = p1.line(x='OD_timing', y='avOD', source=source, color='black')
p1.xaxis.visible = False
p1.x_range.follow = "end"
p1.x_range.follow_interval = 1000*10
p1.x_range.range_padding = 0

# pumps activation plot
p2 = figure(x_axis_type='datetime', plot_width=500, plot_height=200, title='Pump Activations')
l_nut = p2.line(x='pump_timing', y='pump_nut', source=source, line_width=3, color='red', legend='Nutrient Pump')
l_drug = p2.line(x='pump_timing', y='pump_drug', source=source, line_width=3, color='green', legend='Drug Pump')
l_waste = p2.line(x='pump_timing', y='pump_waste', source=source, line_width=3, color='blue', legend='Waste Pump')
p2.yaxis.visible = False
p2.legend.location = 'top_left'
p2.x_range.follow = "end"
p2.x_range.follow_interval = 1000*10
p2.x_range.range_padding = 0

# the legend is too big to fit onto the pump plot on the pi's small screen so it
# needs to be positioned outside the plot
#legend = Legend(items=[('Nutrient Pump', [l_nut]),
#                       ('Drug Pump', [l_drug]),
#                       ('Waste Pump', [l_waste])],
#                location=(0, -10))
#p2.add_layout(legend, 'right')
p2.legend.label_text_font_size = '8pt'

# prime pumps button
prime_pumps = Button(label='Prime Pumps', button_type='success')
prime_pumps.on_click(prime_handler)

# activate control sequence button
activate = Button(label='ACTIVATE', button_type='success')
activate.on_click(activate_handler)

# being saving data button
upload = Button(label='Upload Data', button_type='success')
upload.on_click(upload_handler)

# # shutdown button
# quit = Button(label='Kill Me', button_type='success')
# quit.on_click(quit_handler)

# add the figures to the document
widg = widgetbox(prime_pumps, activate)
drop = widgetbox(dropdown_time,dropdown_avg)
doc.add_root(layout([p1, widg],
                    [p2, drop], sizing_mode='fixed'))


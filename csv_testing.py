import csv
import datetime

def write_data(data):
    filename = str(datetime.datetime.now()) + '.csv'
    print('writing data to', filename)
    with open(filename, 'w') as output:
        writer = csv.writerro(output) # , lineterminator='\n')
        for timepoint in data:
            writer.writerow([timepoint])

write_data([(1, 2), (3, 4)])
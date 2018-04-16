import RPi.GPIO as GPIO
import sys

GPIO.setmode(GPIO.BCM) # Broadcom pin-numbering scheme

for i in range (2, 26):
    print(i)
    GPIO.setup(i, GPIO.OUT) 

for i in range(2,26):
    GPIO.output(i, GPIO.LOW) 

GPIO.cleanup()

sys.exit(0)

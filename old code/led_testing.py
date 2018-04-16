
import time
import RPi.GPIO as GPIO
import Adafruit_ADS1x15

adc = Adafruit_ADS1x15.ADS1015()

GPIO.setmode(GPIO.BCM)
GPIO.setup(4, GPIO.OUT)
GPIO.output(4, 1)
time.sleep(10)
GPIO.output(4, 0)

# for x in range(10):
#     time.sleep(1)
#     value = adc.read_adc(0)
#     value = value * 3.3/2047
#     print(value)
#     if value > 2.85:
#         GPIO.output(4, 1)
#     else:
#         GPIO.output(4, 0)

GPIO.cleanup()

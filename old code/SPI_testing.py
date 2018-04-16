import time
import sys
import spidev
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(6, GPIO.OUT)

spi = spidev.SpiDev()
spi.open(0,0)

def buildReadCommand(channel):
    startBit = 0x01
    singleEnded = 0x08
    
    return [startBit, singleEnded|(channel<<4), 0]
    
def processAdcValue(result):
    '''Take in result as array of three bytes. 
       Return the two lowest bits of the 2nd byte and
       all of the third byte'''
    byte2 = (result[1] & 0x03)
    return (byte2 << 8) | result[2]
    
        
def readAdc(channel):
    if ((channel > 7) or (channel < 0)):
        return -1
    r = spi.xfer2(buildReadCommand(channel))
    return processAdcValue(r)
        
if __name__ == '__main__':
    try:
        while True:
            val = readAdc(0)
            print("ADC Result: ", str(val))
            if val > 900:
                GPIO.output(6, 1)
                time.sleep(1)
                GPIO.output(6, 0)
            time.sleep(0.5)
    except KeyboardInterrupt:
        spi.close() 
        GPIO.cleanup()
        sys.exit(0)

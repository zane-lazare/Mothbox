#!/usr/bin/python3

#GPIO
import RPi.GPIO as GPIO
import time
import datetime
from datetime import datetime

print("----------------- Attract On!-------------------")
now = datetime.now()
formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")  # Adjust the format as needed

print(f"Current time: {formatted_time}")

global onlyflash
onlyflash=False

# Load GPIO pins from configuration
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from mothbox_paths import get_gpio_pins

pins = get_gpio_pins()
Relay_Ch1 = pins['Relay_Ch1']
Relay_Ch2 = pins['Relay_Ch2']
Relay_Ch3 = pins['Relay_Ch3']

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

GPIO.setup(Relay_Ch1,GPIO.OUT)
GPIO.setup(Relay_Ch2,GPIO.OUT)

GPIO.setup(Relay_Ch3,GPIO.OUT)

print("Setup The Relay Module is [success]")

def get_control_values(filename):
    """Reads key-value pairs from the control file."""
    control_values = {}
    with open(filename, "r") as file:
        for line in file:
            key, value = line.strip().split("=")
            control_values[key] = value
    return control_values


def AttractOn():
    GPIO.output(Relay_Ch3,GPIO.HIGH)
    GPIO.output(Relay_Ch2,GPIO.HIGH)
    GPIO.output(Relay_Ch1,GPIO.HIGH)

    print("Attract Lights On\n")
    
def AttractOff():
    GPIO.output(Relay_Ch3,GPIO.LOW)
    GPIO.output(Relay_Ch2,GPIO.LOW)
    GPIO.output(Relay_Ch1,GPIO.LOW)

    print("Attract Lights Off\n")


AttractOn()
#AttractOff()


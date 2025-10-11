#!/usr/bin/python3

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from mothbox_paths import (
    CONTROLS_FILE,
    get_script_path,
    get_gpio_pins
)

import time
import datetime
from datetime import datetime
import RPi.GPIO as GPIO

print("----------------- STARTING Scheduler!-------------------")
now = datetime.now()
formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")  # Adjust the format as needed

print(f"Current time: {formatted_time}")

global onlyflash
onlyflash=False

# Load GPIO pins from configuration
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
    GPIO.output(Relay_Ch3,GPIO.LOW)
    if(onlyflash):
        GPIO.output(Relay_Ch2,GPIO.LOW)
        print("Always Flash mode is on")
    else:
        GPIO.output(Relay_Ch2,GPIO.HIGH)

    GPIO.output(Relay_Ch1,GPIO.LOW)
    print("Attract Lights On\n")
    
def AttractOff():
    GPIO.output(Relay_Ch1,GPIO.HIGH)
    if(onlyflash):
        GPIO.output(Relay_Ch2,GPIO.HIGH)
        print("Always Flash mode is on")
    else:
        GPIO.output(Relay_Ch2,GPIO.HIGH)
    GPIO.output(Relay_Ch3,GPIO.HIGH)

    print("Attract Lights Off\n")


control_values = get_control_values(str(CONTROLS_FILE))
onlyflash = control_values.get("OnlyFlash", "True").lower() == "true"
#AttractOn()
AttractOff()



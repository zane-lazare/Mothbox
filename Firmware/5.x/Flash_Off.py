#!/usr/bin/python3
# GPIO
import datetime
from datetime import datetime

import RPi.GPIO as GPIO

print("----------------- attract off!-------------------")
now = datetime.now()
formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")  # Adjust the format as needed

print(f"Current time: {formatted_time}")

global onlyflash
onlyflash = False

# Load GPIO pins from configuration
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from mothbox_paths import get_gpio_pins

pins = get_gpio_pins()
Relay_Ch1 = pins["Relay_Ch2"]  # Use Ch2 for photo flash

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

GPIO.setup(Relay_Ch1, GPIO.OUT)

print("Setup The Relay Module is [success]")


def get_control_values(filename):
    """Reads key-value pairs from the control file."""
    control_values = {}
    with open(filename) as file:
        for line in file:
            key, value = line.strip().split("=")
            control_values[key] = value
    return control_values


def AttractOff():
    GPIO.output(Relay_Ch1, GPIO.LOW)
    print("Attract Lights Off\n")


def AttractOn():
    GPIO.output(Relay_Ch1, GPIO.HIGH)

    print("Attract Lights On\n")


# control_values = get_control_values("/home/pi/Desktop/Mothbox/controls.txt")
# AttractOn()
AttractOff()

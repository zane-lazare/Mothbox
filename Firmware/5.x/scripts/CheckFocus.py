#!/usr/bin/python
# DEPRECATED: This script uses RPi.GPIO directly, which conflicts with the GPIO daemon.
# For relay control, use the gpio_client library instead: lib.gpio_client.relay_on/relay_off
# This script is retained for reference only. See issue #404.
import subprocess
import sys

# Load GPIO pins from configuration
from pathlib import Path

import RPi.GPIO as GPIO

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from mothbox_paths import get_gpio_pins

pins = get_gpio_pins()
Relay_Ch1 = pins["Relay_Ch1"]
Relay_Ch2 = pins["Relay_Ch2"]
Relay_Ch3 = pins["Relay_Ch3"]

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(Relay_Ch1, GPIO.OUT)
GPIO.setup(Relay_Ch2, GPIO.OUT)
GPIO.setup(Relay_Ch3, GPIO.OUT)

print("Setup The Relay Module is [success]")


def flashOn():
    GPIO.output(Relay_Ch3, GPIO.LOW)
    GPIO.output(Relay_Ch2, GPIO.LOW)
    print("Flash On\n")


def flashOff():
    GPIO.output(Relay_Ch2, GPIO.HIGH)
    print("Flash Off\n")


photo_command = [
    "libcamera-still",
    "--lens-position",
    "7.4",
    "-n",
    "--roi",
    ".25,.2,.3,.3",
    "--width",
    "9152",
    "--height",
    "6944",
    "--awb",
    "cloudy",
    "--metering",
    "average",
    "--ev",
    ".5",
    "-o",
    "test64mp_7.4_cloud_met_av_ev05.jpg",
    "--raw",
]
# full FOV
# hello_command = ["libcamera-hello","--analoggain", "1", "--info-text", "'lens %lp' 'shutter %exp' 'analogue gain %ag", "-t", "0",       ]

# Full FOV Flipped
hello_command = [
    "libcamera-hello",
    "--analoggain",
    "1",
    "--info-text",
    "'lens %lp' 'shutter %exp' 'analogue gain %ag",
    "-t",
    "0",
    "--vflip",
]


# Zoomed
# hello_command = ["libcamera-hello","--analoggain", "1", "--info-text", "'lens %lp' 'shutter %exp' 'analogue gain %ag", "-t", "0","--roi", ".4,.4,.2,.2",       ]

flashOn()

subprocess.run(hello_command)

print("command executed successfully!")

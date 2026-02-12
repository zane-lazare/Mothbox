#!/usr/bin/python3

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.gpio_client import read_switch
from mothbox_paths import get_switch_pins

# Define GPIO pin for checking
switch_pins = get_switch_pins()
off_pin = switch_pins["off_pin"]
debug_pin = switch_pins["debug_pin"]
mode = "ARMED"  # possible modes are OFF or DEBUG or ARMED


# Function to check for connection to ground
def off_connected_to_ground():
    return read_switch(off_pin)


def debug_connected_to_ground():
    return read_switch(debug_pin)


# Check for connection
if debug_connected_to_ground():
    print("GPIO pin", off_pin, "DEBUG connected to ground.")
    mode = "DEBUG"
else:
    print("GPIO pin", debug_pin, "DEBUG NOT connected to ground.")


# Check for connection
if off_connected_to_ground():
    print("GPIO pin", off_pin, "OFF PIN connected to ground.")
    mode = "OFF"  # this check comes second as the OFF state should override the DEBUG state in case both are attached
else:
    print("GPIO pin", off_pin, "OFF PIN NOT connected to ground.")

print("Current Mothbox MODE: ", mode)

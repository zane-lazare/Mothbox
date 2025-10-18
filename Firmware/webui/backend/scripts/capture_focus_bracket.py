#!/usr/bin/python3

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from mothbox_paths import CONTROLS_FILE, CAMERA_SETTINGS_FILE, PHOTOS_DIR

import time
from picamera2 import Picamera2, Preview
from libcamera import controls

import datetime
from datetime import datetime

computerName = "mothboxD"
import cv2


import csv
from exif import Image as ExifImage
from PIL import Image as PillowImage
from PIL import ExifTags

# Focus Bracketing Controls
num_steps = 5
focus_start = 2.0  # diopters
focus_end = 8.0    # diopters

print("----------------- STARTING TAKEPHOTO FOCUS BRACKET -------------------")
now = datetime.now()
formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")

print(f"Current time: {formatted_time}")


import os, platform
if platform.system() == "Windows":
	print(platform.uname().node)
else:
	computerName = os.uname()[1]
	print(os.uname()[1])   # doesnt work on windows



#GPIO
import RPi.GPIO as GPIO
import time

# Load GPIO pins from configuration
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
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

global onlyflash
onlyflash=False


def get_control_values(filepath):
    """Reads key-value pairs from the control file."""
    control_values = {}
    with open(filepath, "r") as file:
        for line in file:
            key, value = line.strip().split("=")
            control_values[key] = value
    return control_values


def flashOn():
    GPIO.output(Relay_Ch3,GPIO.LOW)
    GPIO.output(Relay_Ch2,GPIO.LOW)
    print("Flash On\n")

def flashOff():
    GPIO.output(Relay_Ch2,GPIO.HIGH)
    print("Flash Off\n")


def load_camera_settings():
    """
    Reads camera settings from a CSV file and converts them to appropriate data types.

    Args:
        filepath (str): Path to the CSV file containing camera settings.

    Returns:
        dict: Dictionary containing camera settings with converted data types.

    Raises:
        ValueError: If an invalid value is encountered in the CSV file.
    """


    #first look for any updated CSV files on external media, we will prioritize those
    external_media_paths = ("/media", "/mnt")  # Common external media mount points
    default_path = str(CAMERA_SETTINGS_FILE)
    file_path=default_path

    found = 0
    for path in external_media_paths:
        if(found==0):
            files=os.listdir(path) #don't look for files recursively, only if new settings in top level
            if "camera_settings.csv" in files:
                file_path = os.path.join(root, "camera_settings.csv")
                print(f"Found settings on external media: {file_path}")
                found=1
                break
            else:
                print("No external settings here...")
                file_path=default_path

    if(found==0):
        #redundant but being extra safe
        print("No external settings, using internal csv")
        file_path=default_path


    try:
        with open(file_path) as csv_file:
            reader = csv.DictReader(csv_file)
            camera_settings = {}
            for row in reader:
                setting, value, details = row["SETTING"], row["VALUE"], row["DETAILS"]

                # Convert data types based on setting name (adjust as needed)
                if setting == "LensPosition":
                    try:
                        value = float(value)
                    except ValueError:
                        raise ValueError(f"Invalid value for LensPosition: {value}")
                elif setting == "AnalogueGain":
                    try:
                        value = float(value)
                    except ValueError:
                        raise ValueError(f"Invalid value for AnalogueGain: {value}")
                elif setting == "AeEnable" or setting == "AwbEnable":
                    value = value.lower() == "true"  # Convert to bool (adjust logic if needed)
                elif setting == "AwbMode" or setting == "AfTrigger" or setting == "AfRange"  or setting == "AfSpeed" or setting == "AfMode":
                    value=int(value)
                    #value = getattr(controls.AwbModeEnum, value)  # Access enum value
                    # Assuming AwbMode is a string representing an enum value
                    #pass  # No conversion needed for string
                elif setting == "ExposureTime":
                    try:
                        value = int(value)
                    except ValueError:
                        raise ValueError(f"Invalid value for ExposureTime: {value}")
                else:
                    print(f"Warning: Unknown setting: {setting}. Ignoring.")

                camera_settings[setting] = value

        return camera_settings

    except FileNotFoundError as e:
        print(f"Error: CSV file not found: {file_path}")
        return None


control_values = get_control_values(str(CONTROLS_FILE))
onlyflash = control_values.get("OnlyFlash", "True").lower() == "true"
if(onlyflash):
    print("operating in always on flash mode")

picam2 = Picamera2()

capture_main = {"size": (9000, 6000), "format": "RGB888"}
capture_config = picam2.create_still_configuration(main=capture_main)
picam2.configure(capture_config)



'''
#This is for getting min and max details for certain settings, (See the picam pdf manual)
print(picam2.camera_controls["AnalogueGain"])
min_gain, max_gain, default_gain = picam2.camera_controls["AnalogueGain"]
'''
camera_settings = load_camera_settings()

# Extract focus bracketing settings
num_steps = int(camera_settings.pop("FocusBracket", num_steps))
focus_start = float(camera_settings.pop("FocusBracket_Start", focus_start))
focus_end = float(camera_settings.pop("FocusBracket_End", focus_end))

# Validate focus bracket settings
if num_steps < 1:
    num_steps = 1
    print(f"Warning: Invalid FocusBracket value, defaulting to {num_steps}")

if focus_start < 0.0 or focus_start > 10.0:
    focus_start = 2.0
    print(f"Warning: Invalid FocusBracket_Start, defaulting to {focus_start}")

if focus_end < 0.0 or focus_end > 10.0:
    focus_end = 8.0
    print(f"Warning: Invalid FocusBracket_End, defaulting to {focus_end}")

# Ensure start and end are different for multiple steps
if num_steps > 1 and abs(focus_end - focus_start) < 0.1:
    print(f"Warning: FocusBracket_Start and FocusBracket_End are too close. Adjusting...")
    focus_end = focus_start + 2.0
    if focus_end > 10.0:
        focus_end = 10.0
        focus_start = 8.0

if camera_settings:
    picam2.set_controls(camera_settings)

picam2.start()
time.sleep(.1)

print("cam started");

picam2.stop()
picam2.configure(capture_config)


def calculate_focus_positions(start, end, steps):
    """
    Calculate evenly-spaced focus positions for bracketing.

    Args:
        start: Starting focus position in diopters
        end: Ending focus position in diopters
        steps: Number of focus positions to generate

    Returns:
        List of focus positions
    """
    if steps == 1:
        # Single focus at the start position
        return [start]

    # Calculate evenly-spaced positions
    positions = []
    for i in range(steps):
        pos = start + i * (end - start) / (steps - 1)
        positions.append(pos)

    return positions


def takePhoto_FocusBracket():
    """
    Capture multiple photos at different focus positions (focus bracketing)
    """
    now = datetime.now()
    timestamp = now.strftime("%Y_%m_%d__%H_%M_%S")

    # Apply camera settings
    if camera_settings:
        picam2.set_controls(camera_settings)
    else:
        print("can't set controls")

    # Lock color gains for consistency
    cgains = 2.25943877696990967, 1.500129925489425659
    picam2.set_controls({"ColourGains": cgains})

    # Calculate focus positions
    focus_positions = calculate_focus_positions(focus_start, focus_end, num_steps)
    print(f"Focus bracket positions (diopters): {focus_positions}")

    time.sleep(5)
    picam2.start()

    time.sleep(5)

    start_time = time.time()

    if num_steps > 1:
        print(f"About to take Focus Bracket photo ({num_steps} steps): {timestamp}")
    else:
        print(f"About to take single focus photo: {timestamp}")

    focus_settle_delay = 0.5  # Time for lens to settle between focus changes

    # Focus bracketing loop
    for i, focus_pos in enumerate(focus_positions):
        # Set focus position (manual mode)
        picam2.set_controls({"LensPosition": focus_pos, "AfMode": 0})
        print(f"Setting focus position: {focus_pos:.2f} diopters (step {i+1}/{num_steps})")

        # Wait for focus to settle
        time.sleep(focus_settle_delay)

        # Turn on flash
        flashOn()

        # Capture the image
        request = picam2.capture_request(flush=True)

        # Turn off flash (unless in always-on mode)
        if not onlyflash:
            flashOff()

        capture_time = time.time() - start_time
        print(f"Picture capture time: {capture_time:.2f}s")

        # Save the image with focus bracket suffix
        folderPath = str(PHOTOS_DIR) + "/"
        filepath = folderPath + f"ManFocus_{computerName}_{timestamp}_FB{i}.jpg"

        request.save("main", filepath)
        print(f"Image saved to {filepath}")
        request.release()

        print(f"✓ Captured focus bracket {i+1}/{num_steps} at {focus_pos:.2f} diopters\n")


# Execute focus bracket capture
time.sleep(.5)
takePhoto_FocusBracket()

picam2.stop()

quit()

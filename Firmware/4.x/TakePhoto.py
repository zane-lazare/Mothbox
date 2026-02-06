#!/usr/bin/python

"""
Takephoto - Andy Quitmeyer - Public Domain

This script goes through the proper setup for using 64MP cameras on a pi4 or pi5

Its order of operations is like this
-Determine if pi4 or pi5 to set max resolution
-Read in camera settings
-Configure camera settings like HDR mode
-Calibrate camera's exposure and focus (if mandated)
-prepare the camera for capturing pixels
-Turning camera flash on
-Capturing the pixels
-Turning the camera flash off as quickly as possible after
-Saving the pixels to disk


TODO:
-Add safety function to detect if disk space left is less than 7GB and refuse to take more photos, and give a debug flash pattern (such as SOS with ring lights)
"""

import datetime
import time
from datetime import datetime, timedelta

from libcamera import Transform
from picamera2 import Picamera2

computerName = "mothboxNOTSET"

import csv
import os
import platform
import subprocess
import sys
from pathlib import Path

import piexif

# GPIO
import RPi.GPIO as GPIO

# Add parent directory to path to import mothbox_paths
sys.path.insert(0, str(Path(__file__).parent.parent))
from camera_settings_schema import (
    ALL_KNOWN_SETTINGS,
    BOOL_STRING_SETTINGS,
    FLOAT_SETTINGS,
    INT_SETTINGS,
    STRING_SETTINGS,
    WEBUI_ONLY_SETTINGS,
)
from mothbox_paths import (
    CAMERA_SETTINGS_FILE,
    CONTROLS_FILE,
    MOTHBOX_HOME,
    PHOTOS_DIR,
    get_gpio_pins,
)

# Load GPIO pins from configuration
pins = get_gpio_pins()
Relay_Ch1 = pins["Relay_Ch1"]
Relay_Ch2 = pins["Relay_Ch2"]  # Photo flash
Relay_Ch3 = pins["Relay_Ch3"]  # UV

# IF the mothbox is supposed to be off, don't take a photo!
GPIO.setmode(GPIO.BCM)


# Function to check for connection to ground
def off_connected_to_ground():
    # Set an internal pull-up resistor (optional, some circuits might have one already)
    GPIO.setup(off_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    # Read the pin value
    pin_value = GPIO.input(off_pin)

    # If pin value is LOW (0), then it's connected to ground
    return pin_value == 0


def debug_connected_to_ground():
    # Set an internal pull-up resistor (optional, some circuits might have one already)
    GPIO.setup(debug_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    # Read the pin value
    pin_value = GPIO.input(debug_pin)

    # If pin value is LOW (0), then it's connected to ground
    return pin_value == 0


# Define GPIO pin for checking
off_pin = 16
debug_pin = 12
mode = "ARMED"  # possible modes are OFF or DEBUG or ARMED
# Set GPIO pin as input
GPIO.setup(off_pin, GPIO.IN)
GPIO.setup(debug_pin, GPIO.IN)

# Check for connection
if debug_connected_to_ground():
    print("GPIO pin", debug_pin, "DEBUG connected to ground.")
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

if mode == "OFF":
    print("no photo!")
    # GPIO.cleanup()
    sys.exit(0)  # Normal exit when mode is OFF


internal_storage_minimum = (
    5  # This is Gigabytes, below 4 on a raspberry pi 4, can make weird OS problems
)
extra_photo_storage_minimum = internal_storage_minimum - 1
# Define paths - now using mothbox_paths module
desktop_path = MOTHBOX_HOME  # For backward compatibility with variable name


def restart_script():
    """
    Terminates the current script and restarts it.
    """
    print("Restarting script...")
    time.sleep(1)  # Optional: Add a small delay for clarity
    python_executable = sys.executable
    script_path = sys.argv[0]
    os.execv(python_executable, [python_executable, script_path])


def get_control_values(filepath):
    """Reads key-value pairs from the control file."""
    control_values = {}
    with open(filepath) as file:
        for line in file:
            line = line.strip()
            # Skip empty lines silently
            if not line:
                continue
            # Log warning for malformed lines (helps troubleshooting)
            if "=" not in line:
                print(f"WARNING: Skipping malformed line in {filepath}: '{line}'")
                continue
            key, value = line.split("=", 1)  # maxsplit=1 to handle values with '=' chars
            control_values[key] = value
    return control_values


def set_last_calibration(filepath):
    with open(filepath) as file:
        lines = file.readlines()

    with open(filepath, "w") as file:
        for line in lines:
            print(line)
            if line.startswith("LastCalibration"):
                file.write("LastCalibration=" + str(time.time()) + "\n")  # Replace with False
                print("reset last calibration")
            else:
                file.write(line)  # Keep other lines unchanged


def flashOn():
    GPIO.output(
        Relay_Ch3, GPIO.LOW
    )  # might as well ensure attract is on because new wiring dictates that
    GPIO.output(Relay_Ch2, GPIO.LOW)
    print("Flash On\n")


def flashOff():
    GPIO.output(Relay_Ch2, GPIO.HIGH)
    GPIO.output(
        Relay_Ch3, GPIO.LOW
    )  # might as well ensure attract is on because new wiring dictates that

    print("Flash Off\n")


# Tuned colour gains for plain white LEDs (overnight field testing)
DEFAULT_COLOUR_GAIN_RED = 2.25943877696990967
DEFAULT_COLOUR_GAIN_BLUE = 1.500129925489425659


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
    global middleexposure, calib_lens_position, calib_exposure

    # first look for any updated CSV files on external media, we will prioritize those
    external_media_paths = ("/media", "/mnt")  # Common external media mount points
    default_path = str(CAMERA_SETTINGS_FILE)
    file_path = default_path

    found = 0
    for path in external_media_paths:
        if found == 0:
            try:
                files = os.listdir(
                    path
                )  # don't look for files recursively, only if new settings in top level
            except (PermissionError, OSError, FileNotFoundError) as e:
                print(f"Cannot access {path}: {e}")
                continue  # Skip this path and try next

            if "camera_settings.csv" in files:
                file_path = os.path.join(path, "camera_settings.csv")
                print(f"Found settings on external media: {file_path}")
                found = 1
                break
            else:
                print("No external settings here...")
                file_path = default_path

    if found == 0:
        # redundant but being extra safe
        print("No external settings, using internal csv")
        file_path = default_path

    # set the global path to the one we chose
    chosen_settings_path = file_path
    try:
        with open(file_path) as csv_file:
            reader = csv.DictReader(csv_file)
            the_camera_settings = {}
            for row in reader:
                setting, value, details = row["SETTING"], row["VALUE"], row["DETAILS"]

                # Coerce CSV strings to correct types using shared schema
                if setting in INT_SETTINGS:
                    value = int(value)
                elif setting in FLOAT_SETTINGS:
                    value = float(value)
                elif setting in BOOL_STRING_SETTINGS:
                    value = value.lower() == "true"
                elif setting not in STRING_SETTINGS and setting not in ALL_KNOWN_SETTINGS:
                    print(f"WARNING: Unknown setting '{setting}' in camera_settings.csv")

                # Special handling: ExposureTime sets a global
                if setting == "ExposureTime":
                    middleexposure = value
                    print("middleexposurevalue ", middleexposure)

                the_camera_settings[setting] = value

            return the_camera_settings

    except FileNotFoundError:
        print(f"Error: CSV file not found: {file_path}")
        return None


def update_camera_settings(filename, new_settings):
    """
    Updates the values in a CSV file based on a dictionary of new settings.

    Args:
        filename (str): The name of the CSV file to update.
        new_settings (dict): A dictionary containing key-value pairs for the new settings.
    """

    # Open the CSV file in read-write mode
    with open(filename, "r+") as csvfile:
        # Create a CSV reader object
        reader = csv.DictReader(csvfile)
        # Create an empty list to store modified data
        updated_data = []

        # Read all rows from the CSV file
        for row in reader:
            # Check if the current row matches a setting to update
            if row["SETTING"] in new_settings:
                # Update the value in the current row with the new value from the dictionary
                row["VALUE"] = new_settings[row["SETTING"]]
            # Append the modified or original row to the updated data list
            updated_data.append(row)

        # Clear the file contents and move the pointer to the beginning
        csvfile.seek(0)
        csvfile.truncate()

        # Create a CSV writer object
        writer = csv.DictWriter(csvfile, fieldnames=reader.fieldnames)
        # Write the updated data back to the CSV file
        writer.writeheader()
        writer.writerows(updated_data)


def get_serial_number():
    """
    This function retrieves the Raspberry Pi's serial number from the CPU info file.
    """
    try:
        with open("/proc/cpuinfo") as cpuinfo:
            for line in cpuinfo:
                if line.startswith("Serial"):
                    return line.split(":")[1].strip()
    except (OSError, IndexError):
        return None


def stop_cron():
    """Runs the command 'service cron stop' to stop the cron service."""
    try:
        subprocess.run(["sudo", "service", "cron", "stop"], check=True)
        print("Cron service stopped successfully.")
    except subprocess.CalledProcessError as error:
        print("Error stopping cron service:", error)


def start_cron():
    """Runs the command 'service cron stop' to stop the cron service."""
    try:
        subprocess.run(["sudo", "service", "cron", "start"], check=True)
        print("Cron service started successfully.")
    except subprocess.CalledProcessError as error:
        print("Error starting cron service:", error)


def print_af_state(request):
    md = request.get_metadata()
    # print(("Idle", "Scanning", "Success", "Fail")[md['AfState']], md.get('LensPosition'))


def run_calibration():
    global calib_lens_position, calib_exposure, camera_settings, width, height, picam2
    # preview_config = picam2.create_preview_configuration(main={'format': 'RGB888', 'size': (4624, 3472)})
    preview_config = picam2.create_preview_configuration(main={"size": (1920 * 2, 1080 * 2)})
    # still_config = picam2.create_still_configuration(main={"size": (width, height), "format": "RGB888"}, buffer_count=1)
    picam2.configure(preview_config)

    # picam2.set_controls({"AfMode":0,"AfSpeed":0,"AfRange":0, "LensPosition":7.0})

    # time.sleep(1)
    picam2.pre_callback = print_af_state

    time.sleep(2)
    picam2.set_controls({"LensPosition": 7.0})
    # picam2.set_controls({"AfSpeed":controls.AfSpeedEnum.Fast})

    exposurevalue = camera_settings["ExposureValue"]
    picam2.set_controls(
        {"ExposureValue": exposurevalue}
    )  # Floating point number between -8.0 and 8.0
    picam2.set_controls(
        {"ExposureTime": 500}
    )  # we want a fast photo so we don't get blurry insects. We lock the exposure time and adjust gain. The max speed seems to be 469, but we will leave some overhead

    time.sleep(1)

    print("!!! Autofocusing !!!")
    afstart = time.time()
    flashOn()
    picam2.start(show_preview=False)
    # picam2.start()

    for i in range(5):
        if i == 15 or i == 50:
            pass
            # picam2.set_controls({'AnalogueGain': 1.2})
            # picam2.set_controls({"ExposureValue":8.0})# Floating point number between -8.0 and 8.0

        md = picam2.capture_metadata()
        print(
            i,
            "Calibrating for BRIGHTNESS--  exposure: ",
            md["ExposureTime"],
            "  gain: ",
            md["AnalogueGain"],
            "  Lensposition:",
            md["LensPosition"],
        )

    md = picam2.capture_metadata()
    calib_exposure = md["ExposureTime"]
    autogain = md["AnalogueGain"]

    print("Exposure: " + str(calib_exposure))
    print("Autogain: " + str(autogain))

    time.sleep(0.1)  # give a tiny bit of time to let the flash start up

    # picam2.set_controls({"AfMode": 2})
    # time.sleep(7)
    print("Running autofocus...")
    # picam2.start(show_preview=True, ) #preview has to be on for some reason to work
    success = picam2.autofocus_cycle()

    # picam2.pre_callback = None
    flashOff()
    print("Autofocus completed! " + str(time.time() - afstart))
    md = picam2.capture_metadata()
    calib_lens_position = md["LensPosition"]
    focusstate = md["AfState"]

    print("LensPosition: " + str(calib_lens_position))
    print(focusstate)

    camera_settings["LensPosition"] = calib_lens_position

    camera_settings["ExposureTime"] = calib_exposure
    camera_settings["AnalogueGain"] = autogain

    picam2.stop()
    picam2.stop_preview()

    # save last time
    set_last_calibration(control_values_fpath)

    # save the calibrated settings back to the CSV
    new_settings = {
        "LensPosition": calib_lens_position,
        "ExposureTime": calib_exposure,
        "AnalogueGain": autogain,
    }
    update_camera_settings(chosen_settings_path, new_settings)

    # restart the whole script now because for some reason if we just run the phot taking it is always slightly brighter
    time.sleep(1)
    restart_script()


def list_exposuretimes(middle_exposuretime, num_photos, exposure_width):
    """
    This function calculates exposure times for HDR photos.

    Args:
        middle_exposuretime: The middle exposure time in microseconds.
        num_photos: The number of photos to take.
        exposure_width: The exposure width in steps (added/subtracted to middle time).

    Returns:
        A list of exposure times in microseconds for each HDR photo.
    """

    exposure_times = []
    half_num_photos = int((num_photos - 1) / 2)  # Ensure at least one photo on each side
    # print(half_num_photos)
    # Start with middle exposure for the first photo
    current_exposure = middle_exposuretime
    exposure_times.append(current_exposure)

    # Loop for positive adjustments (excluding middle)
    for i in range(1, half_num_photos + 1):
        direction = 1
        current_exposure = middle_exposuretime + direction * exposure_width * i
        exposure_times.append(current_exposure)

    # Loop for negative adjustments (excluding middle, if applicable)
    for i in range(half_num_photos):
        direction = -1
        current_exposure = middle_exposuretime + direction * exposure_width * (
            i + 1
        )  # Adjust index for missing middle photo
        exposure_times.append(current_exposure)
    return exposure_times


def create_dated_folder(base_path):
    """
    Creates a folder with the current date in the format YYYY-MM-DD if it doesn't exist.

    Args:
        base_path: The base path where the folder will be created.

    Returns:
        The full path to the created folder.
    """
    now = datetime.now()
    # Adjust for time between 12:00 pm and 11:59 am next day
    if 12 <= now.hour < 24:
        date_str = now.strftime("%Y-%m-%d")
    else:
        # Add a day if time is between 12:00 pm and next day's 11:59 am
        date_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    folder_path = os.path.join(base_path, date_str)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    os.chmod(folder_path, 0o750)  # nosec B103 - Group access for webui service
    return folder_path + "/"


def takePhoto_Manual():
    global middleexposure, calib_lens_position, calib_exposure
    # LensPosition: Manual focus, Set the lens position.
    now = datetime.now()
    timestamp = now.strftime("%Y_%m_%d__%H_%M_%S")  # Adjust the format as needed
    # timestamp = now.strftime("%y%m%d%H%M%S")
    # serial_number = get_serial_number()
    # lastfivedigits=serial_number[-5:]

    """"""
    if camera_settings:
        picam2.set_controls(camera_settings)
    else:
        print("can't set controls")
    """"""
    min_exp, max_exp, default_exp = picam2.camera_controls["ExposureTime"]
    # print(min_exp,"   ", max_exp,"   ", default_exp)

    # Lock down AWB with colour gains from CSV (defaults: tuned values from field testing)
    picam2.set_controls({"ColourGains": (colour_gain_red, colour_gain_blue)})

    middleexposure = camera_settings["ExposureTime"]
    exposure_times = list_exposuretimes(middleexposure, num_photos, exposuretime_width)
    print(exposure_times)

    time.sleep(1)
    picam2.start()

    time.sleep(3)

    start = time.time()

    if num_photos > 2:
        print("About to take HDR photo:  ", timestamp)
    else:
        print("About to take single photo:  ", timestamp)

    exposureset_delay = 0.3  # values less than 5 don't seem to work! (unless you restart the cam!)
    requests = []  # Create an empty list to store requests
    PILs = []
    metadatas = []
    # HDR loop
    for i in range(num_photos):
        # middleexposure = camera_settings["ExposureTime"]

        picam2.set_controls({"ExposureTime": exposure_times[i]})
        print("exp  ", exposure_times[i], "  ", i)
        # picam2.set_controls({"NoiseReductionMode":controls.draft.NoiseReductionModeEnum.HighQuality})
        picam2.start()  # need to restart camera or wait a couple frames for settings to change

        time.sleep(exposureset_delay)  # need some time for the settings to sink into the camera)

        flashOn()
        request = picam2.capture_request(flush=True)

        if not onlyflash:
            flashOff()
        flashtime = time.time() - start

        pilImage = request.make_image("main")
        PILs.append(pilImage)
        # image_buffer = request.make_array("main")
        # requests.append(image_buffer)

        # print(request.get_metadata()) # this is the metadata for this image
        metadatas.append(request.get_metadata())
        request.release()

        picam2.stop()
        print("picture take time: " + str(flashtime))

    # Saving loop (can be done later)
    i = 0
    for img in PILs:
        exif_data = metadatas[i]
        pil_image = img
        # Save the image using PIL to get the image data on disk
        folderPath = str(PHOTOS_DIR) + "/"
        if not os.path.exists(folderPath):
            os.makedirs(folderPath)
        os.chmod(folderPath, 0o750)  # nosec B103 - Group access for webui service

        folderPath = create_dated_folder(folderPath)

        print(ImageFileType)
        if ImageFileType == 1:  # png
            filepath = folderPath + computerName + "_" + timestamp + "_HDR" + str(i) + ".png"
        elif ImageFileType == 0:  # jpeg
            filepath = folderPath + computerName + "_" + timestamp + "_HDR" + str(i) + ".jpg"
        elif ImageFileType == 2:  # bmp
            filepath = folderPath + computerName + "_" + timestamp + "_HDR" + str(i) + ".bmp"

        # print(exif_data) #This is a LOT of data
        print(camera_settings.get("LensPosition"))
        # https://github.com/hMatoba/Piexif/blob/3422fbe7a12c3ebcc90532d8e1f4e3be32ece80c/piexif/_exif.py#L406
        # https://piexif.readthedocs.io/en/latest/functions.html#dump
        zeroth_ifd = {
            piexif.ImageIFD.Make: "MothboxV4",
        }
        exif_ifd = {  # piexif.ExifIFD.DateTimeOriginal: u"2099:09:29 10:10:10",
            # piexif.ExifIFD.LensMake: u"LensMake",
            piexif.ExifIFD.ExposureTime: (1, int(1 / (abs(exposure_times[i]) / 1000000))),
            piexif.ExifIFD.FocalLength: (
                int(camera_settings.get("LensPosition") * 100),
                10,
            ),  # Purposefully shifted digits for more sig figs
            piexif.ExifIFD.ISOSpeed: int(camera_settings.get("AnalogueGain") * 100),
            piexif.ExifIFD.ISOSpeedRatings: int(camera_settings.get("AnalogueGain") * 100),
        }
        gps_ifd = {
            # piexif.GPSIFD.GPSVersionID: (2, 0, 0, 0),
            # piexif.GPSIFD.GPSAltitudeRef: 1,
            # piexif.GPSIFD.GPSDateStamp: u"1999:99:99 99:99:99",
        }
        first_ifd = {
            piexif.ImageIFD.Make: "Arducam64mp",
            # piexif.ImageIFD.XResolution: (40, 1),
            # piexif.ImageIFD.YResolution: (40, 1),
            piexif.ImageIFD.Software: "piexif",
        }

        exif_dict = {"0th": zeroth_ifd, "Exif": exif_ifd, "GPS": gps_ifd, "1st": first_ifd}
        exif_bytes = piexif.dump(exif_dict)
        img.save(filepath, exif=exif_bytes, quality=jpeg_quality)
        print("Image saved to " + filepath)
        i = i + 1


def determinePiModel():
    # Check Raspberry Pi model using CPU info
    cpuinfo = open("/proc/cpuinfo")
    model = None  # Initialize model variable outside the loop
    themodel = None

    for line in cpuinfo:
        # print(line)
        if line.startswith("Model"):
            model = line.split(":")[1].strip()
            break
    cpuinfo.close()

    # Execute function based on model
    print(model)
    if model:  # Check if model was found
        if "Pi 4" in model:  # Model identifier for Raspberry Pi 4
            themodel = 4
        elif "Pi 5" in model:  # Model identifier for Raspberry Pi 5
            themodel = 5
        else:
            print("Unknown Raspberry Pi model detected. Going to treat as model 5")
            themodel = 5
    else:
        print("Error: Could not read Raspberry Pi model information.")
        themodel = 5
    return themodel


def get_storage_info(path):
    """
    Gets the total and available storage space of a path.
    Args:
        path: The path to the storage device.

    Returns:
        A tuple containing the total and available storage in bytes.
    """
    try:
        stat = os.statvfs(path)
        return stat.f_blocks * stat.f_bsize, stat.f_bavail * stat.f_bsize
    except OSError:
        return 0, 0  # Handle non-existent or inaccessible storages


# ---------------MAIN CODE--------------------- #

print("----------------- STARTING TAKEPHOTO-------------------")
now = datetime.now()
formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")  # Adjust the format as needed

print(f"Current time: {formatted_time}")


# First check and see if we have enough storage left to keep taking photos, or else do nothing
# Get total and available space on desktop and external storage
desktop_total, desktop_available = get_storage_info(desktop_path)
print("Desktop Total    Storage: \t" + str(desktop_total))
print("Desktop Available Storage: \t" + str(desktop_available))

x = extra_photo_storage_minimum

if desktop_available < x * 1024**3:  # x GB in bytes
    print("=" * 60)
    print("ERROR: Insufficient storage space")
    print("=" * 60)
    print(f"Required minimum: {x} GB")
    print(f"Available space:  {desktop_available / (1024**3):.2f} GB")
    print(f"Shortfall:        {(x * 1024**3 - desktop_available) / (1024**3):.2f} GB")
    print("=" * 60)
    print("Action: Free up disk space or reduce extra_photo_storage_minimum")
    sys.exit(1)  # Exit with error code for insufficient storage


# First figure out if this is a Pi4 or a Pi5
rpiModel = None
rpiModel = determinePiModel()

# default resolution
width = 9000
height = 6000

# the Pi4 can't really handle the FULL resolution, but pi5 can!
if rpiModel == 5:
    width = 9248
    height = 6944


# I don't really know why we need this below code, but it's here. it may have been an earlier attempt to find the pi model
if platform.system() == "Windows":
    print(platform.uname().node)
else:
    # computerName = os.uname()[1]
    print(os.uname()[1])  # doesnt work on windows


# HDR Controls
num_photos = 3
exposuretime_width = 18000
middleexposure = 500  # 500 #minimum exposure time for Hawkeye camera 64mp arducam

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

# GPIO.setup(Relay_Ch1,GPIO.OUT)
GPIO.setup(Relay_Ch2, GPIO.OUT)
GPIO.setup(Relay_Ch3, GPIO.OUT)

print("Setup The Relay Module is [success]")

# Wrap GPIO operations in try/finally to ensure cleanup on crash
try:
    GPIO.output(Relay_Ch2, GPIO.HIGH)
    GPIO.output(
        Relay_Ch3, GPIO.LOW
    )  # might as well ensure attract is on because new wiring dictates that

    global onlyflash
    onlyflash = False

    control_values_fpath = str(CONTROLS_FILE)
    control_values = get_control_values(control_values_fpath)
    onlyflash = control_values.get("OnlyFlash", "True").lower() == "true"
    LastCalibration = float(control_values.get("LastCalibration", 0))
    computerName = control_values.get("name", "wrong")
    jpeg_quality = int(
        control_values.get("jpeg_quality", 96)
    )  # Default: 96 for backward compatibility
    print(f"Using JPEG quality: {jpeg_quality}")

    if onlyflash:
        print("operating in always on flash mode")

    # ------- Setting up camera settings -------------

    """
    #This is for getting min and max details for certain settings, (See the picam pdf manual)
    print(picam2.camera_controls["AnalogueGain"])
    min_gain, max_gain, default_gain = picam2.camera_controls["AnalogueGain"]
    """
    # This will be the path to the CSV holding the settings whether it is the one on the disk or the external CSV
    global chosen_settings_path
    default_path = str(CAMERA_SETTINGS_FILE)
    chosen_settings_path = default_path

    # camera_settings = load_camera_settings("camera_settings.csv")#CRONTAB CAN'T TAKE RELATIVE LINKS!
    camera_settings = load_camera_settings()

    # before calibration, set these values to the default we read in

    calib_lens_position = 6

    calib_lens_position = camera_settings["LensPosition"]
    calib_exposure = camera_settings["ExposureTime"]

    AutoCalibration = camera_settings.pop(
        "AutoCalibration", 1
    )  # defaults to what is set above if not in the files being read
    AutoCalibrationPeriod = int(camera_settings.pop("AutoCalibrationPeriod", 1000))

    # Start up cameras
    picam2 = Picamera2()

    # ----Autocalibration ---------

    current_time = int(time.time())
    timesincelastcalibration = current_time - LastCalibration
    print(
        "Last calibration was   ",
        timesincelastcalibration,
        "  seconds ago \n Autocalibration period is   ",
        AutoCalibrationPeriod,
    )
    recalibrated = False
    if AutoCalibration and (timesincelastcalibration > AutoCalibrationPeriod):
        print("Do Autocalibrate")
        recalibrated = True
        print(current_time)
        # picam2.configure(preview_config)
        # picam2.configure(capture_config_fastAuto)
        run_calibration()
    else:
        print("Don't Autocalibration")

    # ------ Prepare to take actual photo -----------
    # Only reload if calibration ran (it may have updated settings)
    if recalibrated:
        camera_settings = load_camera_settings()
        AutoCalibration = camera_settings.pop(
            "AutoCalibration", 1
        )  # defaults to what is set above if not in the files being read
        AutoCalibrationPeriod = int(camera_settings.pop("AutoCalibrationPeriod", 1000))

    calib_lens_position = camera_settings["LensPosition"]
    calib_exposure = camera_settings["ExposureTime"]

    # remove settings that aren't actually in picamera2
    oldsettingsnames = camera_settings.pop(
        "Name", computerName
    )  # defaults to what is set above if not in the files being read
    ImageFileType = int(camera_settings.pop("ImageFileType", 0))
    VerticalFlip = int(camera_settings.pop("VerticalFlip", 0))

    # HDR settings
    num_photos = int(
        camera_settings.pop("HDR", num_photos)
    )  # defaults to what is set above if not in the files being read
    exposuretime_width = int(camera_settings.pop("HDR_width", exposuretime_width))

    # Colour gains (webui stores as separate CSV keys; picamera2 needs ColourGains tuple)
    colour_gain_red = float(camera_settings.pop("ColourGainRed", DEFAULT_COLOUR_GAIN_RED))
    colour_gain_blue = float(camera_settings.pop("ColourGainBlue", DEFAULT_COLOUR_GAIN_BLUE))

    # Pop remaining webui-only settings not used by TakePhoto.py
    for key in WEBUI_ONLY_SETTINGS:
        camera_settings.pop(key, None)

    if num_photos < 1 or num_photos == 2:
        num_photos = 1

    # Note: Picamera2 "BGR888" outputs RGB byte order (counterintuitive naming)
    # See: https://github.com/raspberrypi/picamera2/discussions/568
    capture_main = {
        "size": (width, height),
        "format": "BGR888",  # Outputs RGB-ordered bytes for PIL compatibility
    }
    capture_config = picam2.create_still_configuration(main=capture_main, raw=None, lores=None)
    capture_config_flipped = picam2.create_still_configuration(
        main=capture_main, transform=Transform(vflip=True, hflip=True), raw=None, lores=None
    )
    picam2.configure(capture_config)

    if camera_settings:
        picam2.set_controls(camera_settings)

    picam2.start()
    time.sleep(1)

    print("cam started")

    picam2.stop()

    if VerticalFlip:
        picam2.configure(capture_config_flipped)
    else:
        picam2.configure(capture_config)

    time.sleep(0.5)
    takePhoto_Manual()

    picam2.stop()

    # cannot call GPIO cleanup here because it will kill the relay turning on the attractor
    GPIO.output(
        Relay_Ch3, GPIO.LOW
    )  # might as well ensure attract is on because new wiring dictates that

finally:
    # Cleanup camera resources to prevent memory leaks
    try:
        picam2.close()
        print("Camera closed successfully")
    except Exception as e:
        print(f"Warning: Camera close failed: {e}")

    # Cleanup flash relay (Relay_Ch2) on exit to ensure it's off
    # Note: We don't cleanup Relay_Ch3 (attractor) as it's intentionally left on
    try:
        GPIO.cleanup(Relay_Ch2)
        print("GPIO cleanup completed for flash relay")
    except Exception as e:
        print(f"Warning: GPIO cleanup failed: {e}")

sys.exit(0)  # Normal exit after successful photo capture

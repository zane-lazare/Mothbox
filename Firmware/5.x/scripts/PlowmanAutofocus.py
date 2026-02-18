# os.environ["LIBCAMERA_LOG_LEVELS"] = "0"
# DEPRECATED: This script uses RPi.GPIO directly, which conflicts with the GPIO daemon.
# For relay control, use the gpio_client library instead: lib.gpio_client.relay_on/relay_off
# This script is retained for reference only. See issue #404.
import sys
import time

# Load GPIO pins from configuration
from pathlib import Path

import RPi.GPIO as GPIO
from picamera2 import Picamera2

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
global start


def flashOn():
    # GPIO.output(Relay_Ch3,GPIO.LOW)
    GPIO.output(Relay_Ch2, GPIO.LOW)
    print("Flash On\n")


def flashOff():
    GPIO.output(Relay_Ch2, GPIO.HIGH)
    print("Flash Off\n")


def print_af_state(request):
    md = request.get_metadata()
    # starttime=start
    timestamp = time.strftime("%Y-%m-%d %X")

    print(
        ("Idle", "Scanning", "Success", "Fail")[md["AfState"]],
        md.get("LensPosition"),
        " time ",
        timestamp,
    )


flashOn()

picam2 = Picamera2()
# capture_main = {"size": (9000, 6000), "format": "RGB888", }
# capture_main = {"size": (1920, 1080), }

# capture_config = picam2.create_still_configuration(main=capture_main,raw=None, lores=None)

# picam2.configure(capture_config)

# preview_config = picam2.create_preview_configuration(main={"size": (4000, 3000)})
# picam2.configure(preview_config)
# picam2.start_preview(show_preview=True)
# picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous,"AfSpeed": controls.AfSpeedEnum.Fast,})

# picam2.set_controls({"AfSpeed":1,"AfRange":0, "LensPosition":8.0})
# picam2.set_controls({"LensPosition":8.0})
# picam2.set_controls({"AfRange":1})
preview_config = picam2.create_preview_configuration(
    main={"format": "RGB888", "size": (4624, 3472)}
)
still_config = picam2.create_still_configuration(
    main={"size": (9000, 6000), "format": "RGB888"}, buffer_count=1
)
picam2.configure(preview_config)

time.sleep(1)
picam2.pre_callback = print_af_state
# picam2.start(show_preview=True)
picam2.start(show_preview=False)

time.sleep(2)

picam2.set_controls({"LensPosition": 8})
picam2.set_controls({"AfSpeed": 0})

time.sleep(2)
start = time.time()
# picam2.set_controls({"AfMode": 2})
success = picam2.autofocus_cycle()

time.sleep(1)

# success = picam2.autofocus_cycle()
# picam2.pre_callback = None
flashOff()

picam2.stop()
quit()

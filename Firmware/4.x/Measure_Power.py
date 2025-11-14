#!/usr/bin/python

import datetime
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import mothbox_paths
sys.path.insert(0, str(Path(__file__).parent.parent))

import adafruit_ina260
import board

from mothbox_paths import get_hardware_config

now = datetime.now()
formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")  # Adjust the format as needed

# Load hardware configuration
hw_config = get_hardware_config()

if not hw_config["ina260_enabled"]:
    print("INA260 sensor disabled in configuration  Time: %s" % (formatted_time))
    quit()

try:
    i2c = board.I2C()  # uses board.SCL and board.SDA
    # i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
    ina260 = adafruit_ina260.INA260(i2c, address=hw_config["ina260_address"])
    print(
        "Current: %.2f mA Voltage: %.2f V Power:%.2f mW  Time: %s"
        % (ina260.current, ina260.voltage, ina260.power, formatted_time)
    )

except (OSError, ValueError):
    # Handle exceptions like sensor not connected or communication errors
    print("Sensor NOT CONNECTED  Time: %s" % (formatted_time))
quit()

# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import adafruit_ina260
from pathlib import Path
import sys

# Add parent directory to path to import mothbox_paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from mothbox_paths import get_hardware_config

# Load hardware configuration
hw_config = get_hardware_config()

i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
ina260 = adafruit_ina260.INA260(i2c, address=hw_config['ina260_address'])

print(f"INA260 {'enabled' if hw_config['ina260_enabled'] else 'disabled'} at address {hex(hw_config['ina260_address'])}")

while True:
    if not hw_config['ina260_enabled']:
        print("INA260 sensor disabled in configuration")
        break
    print(
        "Current: %.2f mA Voltage: %.2f V Power:%.2f mW"
        % (ina260.current, ina260.voltage, ina260.power)
    )
    time.sleep(1)

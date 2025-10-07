# Distributed with a free-will license.
# Use it any way you want, profit or free, provided it fits in the licenses of its associated works.
# PCA9536
# This code is designed to work with the PCA9536_I2CIO I2C Mini Module available from ControlEverything.com.
# https://www.controleverything.com/content/Digital-IO?sku=PCA9536_I2CIO#tabs-0-product_tabset-2

import time
from pathlib import Path
import sys

# Add parent directory to path to import mothbox_paths
sys.path.insert(0, str(Path(__file__).parent.parent))
from mothbox_paths import get_hardware_config

# Load hardware configuration
hw_config = get_hardware_config()

if not hw_config['pca9536_enabled']:
    print("PCA9536 GPIO expander disabled in configuration")
    quit()

from PCA9536 import PCA9536
pca9536 = PCA9536()

while True :
	pca9536.select_io()
	pca9536.select_pin()
	pca9536.input_output_config()
	time.sleep(0.5)
	pca9536.read_data()
	print (" ******************************** ")
	time.sleep(0.5)

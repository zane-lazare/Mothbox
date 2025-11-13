from smbus2 import SMBus
import time
from pathlib import Path
import sys

# Add parent directory to path to import mothbox_paths
sys.path.insert(0, str(Path(__file__).parent.parent))
from mothbox_paths import get_hardware_config

# Load hardware configuration
hw_config = get_hardware_config()

if not hw_config['light_sensor_enabled']:
    print("Light sensor disabled in configuration")
    quit()

I2C_BUS = 1
ADDR = hw_config['light_sensor_address']
ONE_TIME_H_RES_MODE = 0x20  # one-time high res mode (1 lx, ~120 ms)

with SMBus(I2C_BUS) as bus:
    while True:
        # Trigger one-time measurement
        bus.write_byte(ADDR, ONE_TIME_H_RES_MODE)

        time.sleep(0.2)  # wait for conversion (~120 ms)

        # Read 2 bytes
        data = bus.read_i2c_block_data(ADDR, 0x00, 2)
        raw_val = (data[0] << 8) | data[1]
        lux = raw_val / 1.2

        print(f"Ambient Light: {lux:.2f} lx")

        time.sleep(1)  # adjust loop speed as needed

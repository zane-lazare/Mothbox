import sys
import time
from pathlib import Path

import RPi.GPIO as GPIO

# Add parent directory to path to import mothbox_paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from mothbox_paths import get_hardware_config, get_mux_pins

# Load hardware configuration
hw_config = get_hardware_config()

if not hw_config["mux_enabled"]:
    print("Multiplexer disabled in configuration")
    quit()

# Setup GPIO
GPIO.setmode(GPIO.BOARD)

# Pin definitions - loaded from configuration
mux_pins = get_mux_pins()
EN_A = mux_pins["EN_A"]
EN_B = mux_pins["EN_B"]
S0 = mux_pins["S0"]
S1 = mux_pins["S1"]
S2 = mux_pins["S2"]
S3 = mux_pins["S3"]
SIG = mux_pins["SIG"]

# Setup pins
GPIO.setup(EN_A, GPIO.OUT)
GPIO.setup(EN_B, GPIO.OUT)
GPIO.setup(S0, GPIO.OUT)
GPIO.setup(S1, GPIO.OUT)
GPIO.setup(S2, GPIO.OUT)
GPIO.setup(S3, GPIO.OUT)
GPIO.setup(SIG, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Assuming switches pull to ground


# Multiplexer channel selection
def select_channel(channel):
    """Set the select pins to choose the specified channel (0-15)"""
    GPIO.output(S0, channel & 0x01)
    GPIO.output(S1, channel & 0x02)
    GPIO.output(S2, channel & 0x04)
    GPIO.output(S3, channel & 0x08)


def set_pull_up(pin):
    """
    Sets the internal pull-up resistor for a given GPIO pin on a Raspberry Pi.

    Args:
      pin: The GPIO pin number to configure.
    """
    try:
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        print(f"Pullup resistor enabled for pin {pin}")  # Confirmation
    except Exception as e:
        print(f"Error setting pull-up for pin {pin}: {e}")


def read_switches():
    """Read all switches from both multiplexers"""
    switches = {"A": [], "B": []}

    # Read Multiplexer A
    GPIO.output(EN_A, GPIO.LOW)  # Enable MUX A
    GPIO.output(EN_B, GPIO.HIGH)  # Disable MUX B

    for channel in range(16):
        select_channel(channel)
        time.sleep(0.001)  # Small delay for settling
        switches["A"].append(GPIO.input(SIG))

    # Read Multiplexer B
    GPIO.output(EN_A, GPIO.HIGH)  # Disable MUX A
    GPIO.output(EN_B, GPIO.LOW)  # Enable MUX B

    for channel in range(16):
        select_channel(channel)
        time.sleep(0.001)  # Small delay for settling
        switches["B"].append(GPIO.input(SIG))

    return switches


def display_switches(switches):
    """Display the switch states in a readable format"""
    print("\nSwitch States:")
    print("Multiplexer A:")
    for i, state in enumerate(switches["A"]):
        print(f"  A{i:02d}: {'ON' if state == 0 else 'OFF'}")

    print("\nMultiplexer B:")
    for i, state in enumerate(switches["B"]):
        print(f"  B{i:02d}: {'ON' if state == 0 else 'OFF'}")


set_pull_up(SIG)
try:
    print("Reading multiplexer switches. Press CTRL+C to exit.")

    while True:
        switches = read_switches()
        display_switches(switches)
        time.sleep(2)  # Update every second

except KeyboardInterrupt:
    print("\nExiting...")
finally:
    GPIO.cleanup()

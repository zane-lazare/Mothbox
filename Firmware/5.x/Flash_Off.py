#!/usr/bin/python3

"""Turn camera flash OFF (Relay Ch2 only)."""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.gpio_helpers import relay_off, setup_relay
from mothbox_paths import get_gpio_pins

print("----------------- Flash Off! -------------------")
print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

pins = get_gpio_pins()
flash_pin = pins["Relay_Ch2"]

setup_relay(flash_pin)
relay_off(flash_pin)

print("Camera flash OFF")

# GPIO.cleanup() intentionally omitted.
# Relay pins must persist in their current state after this script exits.
# Cleanup is performed only by Scheduler.py before system shutdown.

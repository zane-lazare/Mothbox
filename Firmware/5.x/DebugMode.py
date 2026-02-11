#!/usr/bin/python3

"""
Debug mode script — safe state for troubleshooting.

Actions:
- Stops cron service
- Turns OFF all relays (UV, flash, spare)
- Keeps internet alive
- Disables scheduled shutdown
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.gpio_client import relay_off, setup_relay
from mothbox_paths import CONTROLS_FILE, get_gpio_pins, get_script_path

now = datetime.now()
print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")


# --- Stop cron ----------------------------------------------------------------

print("----------------- STOP CRON -------------------")


def stop_cron():
    """Runs the command 'service cron stop' to stop the cron service."""
    try:
        subprocess.run(["sudo", "service", "cron", "stop"], check=True)  # noqa: S603, S607
        print("Cron service stopped successfully.")
    except subprocess.CalledProcessError as error:
        print("Error stopping cron service:", error)


stop_cron()


# --- Turn OFF all relays ------------------------------------------------------

print("----------------- ALL RELAYS OFF -------------------")

pins = get_gpio_pins()

for name in ("Relay_Ch1", "Relay_Ch2", "Relay_Ch3"):
    setup_relay(pins[name])
    relay_off(pins[name])

print("All relays OFF")


# --- Keep internet alive ------------------------------------------------------

print("----------------- KEEP INTERNET ON -------------------")

script_path = str(get_script_path("scripts/MothPower/stop_lowpower.sh"))
subprocess.run([script_path])  # noqa: S603
print("WIFI Script execution completed!")


# --- Disable scheduled shutdown -----------------------------------------------

print("----------------- KEEP PI ON INDEFINITELY -------------------")

with open(str(CONTROLS_FILE)) as file:
    lines = file.readlines()

with open(str(CONTROLS_FILE), "w") as file:
    for line in lines:
        if line.startswith("shutdown_enabled="):
            file.write("shutdown_enabled=False\n")
            print("Scheduled shutdown disabled")
        else:
            file.write(line)

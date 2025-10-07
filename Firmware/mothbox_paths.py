#!/usr/bin/env python3
"""
Mothbox Path Configuration Module

This module provides centralized path management for the Mothbox firmware.
It supports multiple installation locations and maintains backward compatibility.

Directory Structure Options:
1. Production (FHS-compliant):
   - /opt/mothbox/firmware/          # Application code
   - /etc/mothbox/                   # Configuration files
   - /var/lib/mothbox/photos/        # Data storage

2. Legacy (backward compatible):
   - /home/pi/Desktop/Mothbox/       # All files

3. Development:
   - Any location via MOTHBOX_HOME environment variable

Usage:
    from mothbox_paths import MOTHBOX_HOME, PHOTOS_DIR, CONFIG_DIR, get_gpio_pins

    camera_settings_path = CONFIG_DIR / "camera_settings.csv"

    # Load GPIO pin configuration
    pins = get_gpio_pins()
    Relay_Ch1 = pins['Relay_Ch1']
"""

import os
from pathlib import Path

# Check for environment variable override first
MOTHBOX_HOME_ENV = os.environ.get('MOTHBOX_HOME')

if MOTHBOX_HOME_ENV:
    # Use environment variable if set (useful for development/testing)
    MOTHBOX_HOME = Path(MOTHBOX_HOME_ENV)
    _installation_type = "custom"
elif Path("/opt/mothbox").exists():
    # Production FHS-compliant installation
    MOTHBOX_HOME = Path("/opt/mothbox")
    _installation_type = "production"
else:
    # Legacy Desktop installation (backward compatibility)
    MOTHBOX_HOME = Path("/home/pi/Desktop/Mothbox")
    _installation_type = "legacy"

# Derive other paths based on installation type
if _installation_type == "production":
    # FHS-compliant paths
    CONFIG_DIR = Path("/etc/mothbox")
    DATA_DIR = Path("/var/lib/mothbox")
    FIRMWARE_DIR = MOTHBOX_HOME / "firmware"
else:
    # Legacy or custom: everything under MOTHBOX_HOME
    CONFIG_DIR = MOTHBOX_HOME
    DATA_DIR = MOTHBOX_HOME
    FIRMWARE_DIR = MOTHBOX_HOME

# Common subdirectories
PHOTOS_DIR = DATA_DIR / "photos"

# Configuration files
CAMERA_SETTINGS_FILE = CONFIG_DIR / "camera_settings.csv"
SCHEDULE_SETTINGS_FILE = CONFIG_DIR / "schedule_settings.csv"
CONTROLS_FILE = CONFIG_DIR / "controls.txt"
WORDLIST_FILE = CONFIG_DIR / "wordlist.csv"

# Helper function to parse controls.txt
def get_control_values(filename):
    """
    Reads key-value pairs from the control file.

    Args:
        filename: Path to the control file (str or Path)

    Returns:
        dict: Dictionary with key-value pairs from controls.txt
    """
    control_values = {}
    try:
        with open(filename, "r") as file:
            for line in file:
                line = line.strip()
                if line and '=' in line and not line.startswith('#'):
                    key, value = line.split("=", 1)
                    control_values[key] = value
    except FileNotFoundError:
        pass  # Return empty dict if file doesn't exist
    return control_values


def get_gpio_pins():
    """
    Load GPIO pin configuration from controls.txt with fallback defaults.

    Returns:
        dict: GPIO pin mappings {'Relay_Ch1': int, 'Relay_Ch2': int, 'Relay_Ch3': int}

    Note:
        Defaults to 4.x firmware pin assignments (26/20/21) if not specified.
        To customize, add the following lines to controls.txt:
            Relay_Ch1=5
            Relay_Ch2=19
            Relay_Ch3=9
    """
    try:
        pins = get_control_values(CONTROLS_FILE)
        return {
            'Relay_Ch1': int(pins.get('Relay_Ch1', 26)),  # Default to 4.x pins
            'Relay_Ch2': int(pins.get('Relay_Ch2', 20)),
            'Relay_Ch3': int(pins.get('Relay_Ch3', 21))
        }
    except (FileNotFoundError, ValueError, KeyError):
        # Fallback to defaults if file not found or parse error
        return {'Relay_Ch1': 26, 'Relay_Ch2': 20, 'Relay_Ch3': 21}


# Script paths (commonly referenced scripts)
def get_script_path(script_name):
    """
    Get the full path to a firmware script.

    Args:
        script_name: Name of the script (e.g., "TakePhoto.py", "GPS.py")

    Returns:
        Path object pointing to the script

    Raises:
        ValueError: If script_name contains path traversal attempts or is absolute
    """
    # Security: Prevent path traversal attacks
    if '..' in script_name or script_name.startswith('/'):
        raise ValueError(f"Invalid script name (path traversal attempt): {script_name}")

    script_path = FIRMWARE_DIR / script_name

    # Security: Ensure resolved path stays within FIRMWARE_DIR
    try:
        if not str(script_path.resolve()).startswith(str(FIRMWARE_DIR.resolve())):
            raise ValueError(f"Script path outside firmware directory: {script_name}")
    except (OSError, RuntimeError):
        # Handle cases where resolve() fails (e.g., path doesn't exist yet)
        pass

    return script_path

# Utility function to ensure directories exist
def ensure_directories():
    """
    Create necessary directories if they don't exist.
    Should be called during installation or first run.
    """
    dirs_to_create = [
        CONFIG_DIR,
        DATA_DIR,
        PHOTOS_DIR,
    ]

    for directory in dirs_to_create:
        directory.mkdir(parents=True, exist_ok=True)
        # Set permissions: owner rwx, group rx, others rx
        try:
            os.chmod(directory, 0o755)
        except (OSError, PermissionError):
            pass  # Skip if we don't have permission

# Debug function
def print_paths():
    """Print all configured paths for debugging purposes."""
    print("=" * 60)
    print("Mothbox Path Configuration")
    print("=" * 60)
    print(f"Installation Type: {_installation_type}")
    print(f"MOTHBOX_HOME:      {MOTHBOX_HOME}")
    print(f"CONFIG_DIR:        {CONFIG_DIR}")
    print(f"DATA_DIR:          {DATA_DIR}")
    print(f"FIRMWARE_DIR:      {FIRMWARE_DIR}")
    print(f"PHOTOS_DIR:        {PHOTOS_DIR}")
    print("-" * 60)
    print("Configuration Files:")
    print(f"  Camera Settings: {CAMERA_SETTINGS_FILE}")
    print(f"  Schedule:        {SCHEDULE_SETTINGS_FILE}")
    print(f"  Controls:        {CONTROLS_FILE}")
    print(f"  Wordlist:        {WORDLIST_FILE}")
    print("=" * 60)

if __name__ == "__main__":
    # When run directly, print configuration
    print_paths()

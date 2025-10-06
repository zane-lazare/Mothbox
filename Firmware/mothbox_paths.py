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
    from mothbox_paths import MOTHBOX_HOME, PHOTOS_DIR, CONFIG_DIR

    camera_settings_path = CONFIG_DIR / "camera_settings.csv"
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

# Script paths (commonly referenced scripts)
def get_script_path(script_name):
    """
    Get the full path to a firmware script.

    Args:
        script_name: Name of the script (e.g., "TakePhoto.py", "GPS.py")

    Returns:
        Path object pointing to the script
    """
    return FIRMWARE_DIR / script_name

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
        # Set permissions to be accessible by pi user
        try:
            os.chmod(directory, 0o777)
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

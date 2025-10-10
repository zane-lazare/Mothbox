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
    from mothbox_paths import MOTHBOX_HOME, PHOTOS_DIR, CONFIG_DIR, get_gpio_pins, get_hardware_config

    camera_settings_path = CONFIG_DIR / "camera_settings.csv"

    # Load GPIO pin configuration
    pins = get_gpio_pins()
    Relay_Ch1 = pins['Relay_Ch1']

    # Load all hardware configuration
    hw_config = get_hardware_config()
    if hw_config['ina260_enabled']:
        # Initialize INA260 sensor
"""

import os
import sys
from pathlib import Path
from typing import Dict, Union, Any

# Detect installation type
# Priority: marker file > /opt/mothbox exists > env var > legacy path
installation_marker = Path("/opt/mothbox/.installation_type")
MOTHBOX_HOME_ENV = os.environ.get('MOTHBOX_HOME')

if installation_marker.exists():
    # Read installation type from marker file (most reliable)
    try:
        _installation_type = installation_marker.read_text().strip()
        MOTHBOX_HOME = Path("/opt/mothbox")
    except (ValueError, OSError, KeyError) as e:
        print(f"Warning: Failed to detect installation type ({e}), defaulting to production", file=sys.stderr)
        _installation_type = "production"
        MOTHBOX_HOME = Path("/opt/mothbox")
elif Path("/opt/mothbox").exists() and not MOTHBOX_HOME_ENV:
    # Production FHS-compliant installation
    # Only if /opt/mothbox exists AND no env var override
    MOTHBOX_HOME = Path("/opt/mothbox")
    _installation_type = "production"
elif MOTHBOX_HOME_ENV:
    # Custom location via environment variable
    MOTHBOX_HOME = Path(MOTHBOX_HOME_ENV)
    _installation_type = "custom"
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
WEBUI_SETTINGS_FILE = CONFIG_DIR / "webui_settings.txt"

# Helper function to parse controls.txt
def get_control_values(filename: Union[Path, str]) -> Dict[str, str]:
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


def get_gpio_pins() -> Dict[str, int]:
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
    except (FileNotFoundError, ValueError, KeyError) as e:
        import sys
        print(f"Warning: Could not load GPIO configuration ({e}). Using defaults.", file=sys.stderr)
        # Fallback to defaults if file not found or parse error
        return {'Relay_Ch1': 26, 'Relay_Ch2': 20, 'Relay_Ch3': 21}


def get_epaper_pins() -> Dict[str, int]:
    """
    Load e-paper display GPIO pin configuration from controls.txt.

    Returns:
        dict: E-paper GPIO pin mappings

    Note:
        Default pins for Waveshare 2.13" e-paper display:
            RST_PIN=17, DC_PIN=25, CS_PIN=8, BUSY_PIN=24, PWR_PIN=18
    """
    try:
        config = get_control_values(CONTROLS_FILE)
        return {
            'RST_PIN': int(config.get('epaper_rst_pin', '17')),
            'DC_PIN': int(config.get('epaper_dc_pin', '25')),
            'CS_PIN': int(config.get('epaper_cs_pin', '8')),
            'BUSY_PIN': int(config.get('epaper_busy_pin', '24')),
            'PWR_PIN': int(config.get('epaper_pwr_pin', '18')),
        }
    except (FileNotFoundError, ValueError, KeyError) as e:
        import sys
        print(f"Warning: Could not load e-paper pin configuration ({e}). Using defaults.", file=sys.stderr)
        return {
            'RST_PIN': 17,
            'DC_PIN': 25,
            'CS_PIN': 8,
            'BUSY_PIN': 24,
            'PWR_PIN': 18,
        }


def get_mux_pins() -> Dict[str, int]:
    """
    Load multiplexer GPIO pin configuration from controls.txt.

    Returns:
        dict: Multiplexer GPIO pin mappings (BOARD mode)

    Note:
        Default pins for CD74HC4067 dual multiplexer setup:
            EN_A=31, EN_B=29, S0=33, S1=13, S2=12, S3=15, SIG=36
    """
    try:
        config = get_control_values(CONTROLS_FILE)
        return {
            'EN_A': int(config.get('mux_en_a', '31')),
            'EN_B': int(config.get('mux_en_b', '29')),
            'S0': int(config.get('mux_s0', '33')),
            'S1': int(config.get('mux_s1', '13')),
            'S2': int(config.get('mux_s2', '12')),
            'S3': int(config.get('mux_s3', '15')),
            'SIG': int(config.get('mux_sig', '36')),
        }
    except (FileNotFoundError, ValueError, KeyError) as e:
        import sys
        print(f"Warning: Could not load multiplexer pin configuration ({e}). Using defaults.", file=sys.stderr)
        return {
            'EN_A': 31,
            'EN_B': 29,
            'S0': 33,
            'S1': 13,
            'S2': 12,
            'S3': 15,
            'SIG': 36,
        }


def get_hardware_config() -> Dict[str, Any]:
    """
    Load all hardware module configuration from controls.txt.

    Returns:
        dict: Complete hardware configuration including enable/disable flags,
              I2C addresses, GPIO pins, and device paths for all modules.

    Modules configured:
        - Relay module (already implemented)
        - INA260 power sensor
        - E-paper display
        - GPS module
        - Light sensor (optional)
        - PCA9536 GPIO expander (optional)
        - Multiplexer (optional)
    """
    try:
        config = get_control_values(CONTROLS_FILE)
        return {
            # Relay module (already implemented via get_gpio_pins)
            'relay_enabled': config.get('relay_enabled', 'true').lower() == 'true',

            # INA260 power sensor
            'ina260_enabled': config.get('ina260_enabled', 'false').lower() == 'true',
            'ina260_address': int(config.get('ina260_address', '0x40'), 16),

            # E-paper display
            'epaper_enabled': config.get('epaper_enabled', 'false').lower() == 'true',
            'epaper_rst_pin': int(config.get('epaper_rst_pin', '17')),
            'epaper_dc_pin': int(config.get('epaper_dc_pin', '25')),
            'epaper_cs_pin': int(config.get('epaper_cs_pin', '8')),
            'epaper_busy_pin': int(config.get('epaper_busy_pin', '24')),
            'epaper_pwr_pin': int(config.get('epaper_pwr_pin', '18')),

            # GPS module
            'gps_enabled': config.get('gps_enabled', 'false').lower() == 'true',
            'gps_device': config.get('gps_device', '/dev/ttyAMA0'),
            'gps_baudrate': int(config.get('gps_baudrate', '9600')),
            'gps_timeout': int(config.get('gps_timeout', '10')),

            # Light sensor (optional)
            'light_sensor_enabled': config.get('light_sensor_enabled', 'false').lower() == 'true',
            'light_sensor_type': config.get('light_sensor_type', 'LTR303'),  # BH1750 or LTR303
            'light_sensor_address': int(config.get('light_sensor_address', '0x29'), 16),

            # PCA9536 GPIO expander (optional)
            'pca9536_enabled': config.get('pca9536_enabled', 'false').lower() == 'true',
            'pca9536_address': int(config.get('pca9536_address', '0x21'), 16),

            # Multiplexer (optional)
            'mux_enabled': config.get('mux_enabled', 'false').lower() == 'true',
            'mux_type': config.get('mux_type', 'i2c'),  # 'gpio' or 'i2c'
            'mux_address': int(config.get('mux_address', '0x20'), 16),  # I2C address if i2c mode
            'mux_en_a': int(config.get('mux_en_a', '31')),  # GPIO pins if gpio mode
            'mux_en_b': int(config.get('mux_en_b', '29')),
            'mux_s0': int(config.get('mux_s0', '33')),
            'mux_s1': int(config.get('mux_s1', '13')),
            'mux_s2': int(config.get('mux_s2', '12')),
            'mux_s3': int(config.get('mux_s3', '15')),
            'mux_sig': int(config.get('mux_sig', '36')),
        }
    except (FileNotFoundError, ValueError, KeyError) as e:
        import sys
        print(f"Warning: Could not load hardware configuration ({e}). Using defaults.", file=sys.stderr)
        # Return defaults for all modules - all disabled by default except relays
        return {
            'relay_enabled': True,  # Relays are core hardware, enabled by default
            'ina260_enabled': False,
            'ina260_address': 0x40,
            'epaper_enabled': False,
            'epaper_rst_pin': 17,
            'epaper_dc_pin': 25,
            'epaper_cs_pin': 8,
            'epaper_busy_pin': 24,
            'epaper_pwr_pin': 18,
            'gps_enabled': False,
            'gps_device': '/dev/ttyAMA0',
            'gps_baudrate': 9600,
            'gps_timeout': 10,
            'light_sensor_enabled': False,
            'light_sensor_type': 'LTR303',
            'light_sensor_address': 0x29,
            'pca9536_enabled': False,
            'pca9536_address': 0x21,
            'mux_enabled': False,
            'mux_type': 'i2c',
            'mux_address': 0x20,
            'mux_en_a': 31,
            'mux_en_b': 29,
            'mux_s0': 33,
            'mux_s1': 13,
            'mux_s2': 12,
            'mux_s3': 15,
            'mux_sig': 36,
        }


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

    Security validations performed:
        1. Prevents parent directory traversal (../)
        2. Prevents absolute path injection (/)
        3. Prevents symlink attacks (resolves symlinks then validates)
        4. Prevents encoded path attacks (%2e%2e/, etc. - resolved by Path)
        5. Prevents partial directory name matches (/firmware vs /firmware-evil)
    """
    # Security: Prevent obvious path traversal attacks
    if '..' in script_name or script_name.startswith('/'):
        raise ValueError(f"Invalid script name (path traversal attempt): {script_name}")

    script_path = FIRMWARE_DIR / script_name

    # Security: Resolve symlinks and verify final path stays within FIRMWARE_DIR
    # This catches:
    # - Symlink attacks (follows links to real destination)
    # - Encoded paths (Path.resolve() normalizes these)
    # - Partial directory name matches (relative_to() requires exact containment)
    try:
        resolved_path = script_path.resolve()
        firmware_base = FIRMWARE_DIR.resolve()

        # Use relative_to() which raises ValueError if path is not within base
        # This prevents partial path matching (e.g., /firmware vs /firmware-evil)
        resolved_path.relative_to(firmware_base)
    except ValueError:
        raise ValueError(
            f"Security: Script path resolves outside firmware directory. "
            f"Script: {script_name}"
        )
    except (OSError, RuntimeError):
        # Handle cases where resolve() fails (e.g., path doesn't exist yet)
        # This is acceptable - we validate at runtime when path exists
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

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

4. Test (CI/CD and local testing):
   - Repository root via MOTHBOX_ENV=test
   - Auto-detects pytest execution

Usage:
    from mothbox_paths import MOTHBOX_HOME, PHOTOS_DIR, CONFIG_DIR, get_gpio_pins, get_hardware_config, get_firmware_version, get_takephoto_script

    camera_settings_path = CONFIG_DIR / "camera_settings.csv"

    # Get firmware version
    firmware_version = get_firmware_version()  # Returns "4" or "5"

    # Get TakePhoto.py script path
    takephoto_script = get_takephoto_script()  # Returns Path to TakePhoto.py

    # Load GPIO pin configuration
    pins = get_gpio_pins()
    Relay_Ch1 = pins['Relay_Ch1']

    # Load all hardware configuration
    hw_config = get_hardware_config()
    if hw_config['ina260_enabled']:
        # Initialize INA260 sensor
"""

import os
import re
import sys
from contextlib import suppress
from pathlib import Path
from typing import Any

# Detect installation type
# Priority: test mode > marker file > /opt/mothbox exists > env var > legacy path
installation_marker = Path("/opt/mothbox/.installation_type")
MOTHBOX_HOME_ENV = os.environ.get("MOTHBOX_HOME")
MOTHBOX_ENV = os.environ.get("MOTHBOX_ENV", "production")


# Auto-detect test/CI environment
def _is_test_environment():
    """Detect if running in test or CI environment."""
    # Check explicit test mode
    if MOTHBOX_ENV == "test":
        return True

    # Check for pytest execution
    if os.environ.get("PYTEST_CURRENT_TEST") or "pytest" in sys.modules:
        return True

    # Check for common CI environment variables
    ci_indicators = ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_HOME", "CIRCLECI", "TRAVIS"]
    return any(os.environ.get(var) for var in ci_indicators)


# TEST MODE: Use repository root for testing (CI/CD and local tests)
if _is_test_environment():
    # In test environment: use current file's parent directory (repository root)
    MOTHBOX_HOME = Path(__file__).parent
    _installation_type = "test"
elif installation_marker.exists():
    # Read installation type from marker file (most reliable)
    try:
        _installation_type = installation_marker.read_text().strip()
        MOTHBOX_HOME = Path("/opt/mothbox")
    except (ValueError, OSError, KeyError) as e:
        print(
            f"Warning: Failed to detect installation type ({e}), defaulting to production",
            file=sys.stderr,
        )
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
    FIRMWARE_DIR = MOTHBOX_HOME
else:
    # Test, legacy, or custom: everything under MOTHBOX_HOME
    CONFIG_DIR = MOTHBOX_HOME
    DATA_DIR = MOTHBOX_HOME
    FIRMWARE_DIR = MOTHBOX_HOME

# Common subdirectories
PHOTOS_DIR = DATA_DIR / "photos"
CACHE_DIR = DATA_DIR / "cache"
THUMBNAIL_CACHE_DIR = CACHE_DIR / "thumbnails"

# Configuration files
CAMERA_SETTINGS_FILE = (
    CONFIG_DIR / "camera_settings.csv"
)  # Photo capture settings (firmware controls only)
WEBUI_WORKFLOW_SETTINGS_FILE = (
    CONFIG_DIR / "webui_settings.csv"
)  # WebUI workflow settings (HDR, FocusBracket, etc.)
SCHEDULE_SETTINGS_FILE = CONFIG_DIR / "schedule_settings.csv"
CONTROLS_FILE = CONFIG_DIR / "controls.txt"
WORDLIST_FILE = CONFIG_DIR / "wordlist.csv"
LIVEVIEW_SETTINGS_FILE = CONFIG_DIR / "liveview_settings.txt"  # Live view stream settings
WEBUI_SETTINGS_FILE = LIVEVIEW_SETTINGS_FILE  # Deprecated: Use LIVEVIEW_SETTINGS_FILE
USER_PREFERENCES_FILE = CONFIG_DIR / "user_preferences.json"

# ISP tuning configuration
ISP_TUNING_DIR = CONFIG_DIR / "isp_tuning"
ISP_DEFAULT_TUNING_FILE = ISP_TUNING_DIR / "camera_isp_tuning.json"

# Preset configuration (camera presets)
PRESET_DIR = CONFIG_DIR / "presets"
BUILTIN_PRESET_DIR = PRESET_DIR / "built-in"
USER_PRESET_DIR = PRESET_DIR / "user"

# Export preset configuration (unified namespace under presets/)
EXPORT_BUILTIN_PRESET_DIR = BUILTIN_PRESET_DIR / "export"
EXPORT_USER_PRESET_DIR = USER_PRESET_DIR / "export"

# Schedule configuration
SCHEDULES_DIR = CONFIG_DIR / "schedules"
BUILTIN_SCHEDULES_DIR = MOTHBOX_HOME / "webui" / "backend" / "presets_builtin" / "schedules"


def get_schedule_path(schedule_id: str, is_builtin: bool = False) -> Path | None:
    """
    Build a safe path to a schedule file.

    Sanitizes the schedule_id to prevent path traversal attacks.

    Args:
        schedule_id: Schedule identifier (alphanumeric, hyphens, underscores only)
        is_builtin: If True, use built-in schedules directory

    Returns:
        Path to schedule JSON file, or None if schedule_id is invalid

    Example:
        >>> get_schedule_path("nightly-survey")
        PosixPath('/etc/mothbox/schedules/nightly-survey.json')
        >>> get_schedule_path("../etc/passwd")
        None
    """
    # Sanitize: extract just the filename component
    safe_id = os.path.basename(schedule_id)

    # Reject if sanitization changed the value (path traversal attempt)
    if safe_id != schedule_id:
        return None

    # Validate format: alphanumeric, hyphens, underscores, must start with alphanumeric
    if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$", safe_id):
        return None

    base_dir = BUILTIN_SCHEDULES_DIR if is_builtin else SCHEDULES_DIR
    schedule_path = base_dir / f"{safe_id}.json"

    # Final safety check: verify resolved path is within expected directory
    try:
        if not schedule_path.resolve().is_relative_to(base_dir.resolve()):
            return None
    except ValueError:
        return None

    return schedule_path


# Helper function to parse controls.txt
def get_control_values(filename: Path | str) -> dict[str, str]:
    """
    Reads key-value pairs from the control file.

    Args:
        filename: Path to the control file (str or Path)

    Returns:
        dict: Dictionary with key-value pairs from controls.txt
    """
    control_values = {}
    try:
        with open(filename) as file:
            for line in file:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    # Strip whitespace from key and value (Issue #13 bug fix)
                    control_values[key.strip()] = value.strip()
    except FileNotFoundError:
        pass  # Return empty dict if file doesn't exist
    return control_values


def get_firmware_version() -> str:
    """
    Detect firmware version (4.x or 5.x) from controls.txt.

    Returns:
        str: "4" or "5" representing the firmware version

    Note:
        Reads softwareversion from controls.txt (format: X.Y.Z).
        Falls back to "5" if softwareversion not found or invalid.
        This is separate from Pi hardware version - users can choose
        5.x firmware on Pi 4 hardware for different GPIO mappings.
    """
    try:
        controls = get_control_values(CONTROLS_FILE)
        version_string = controls.get("softwareversion", "5.0.0")
        # Extract major version (first digit before '.')
        firmware_version = version_string.split(".")[0]
        if firmware_version in ["4", "5"]:
            return firmware_version
        else:
            print(
                f"Warning: Unexpected firmware version '{version_string}', defaulting to 5.x",
                file=sys.stderr,
            )
            return "5"
    except Exception as e:
        print(
            f"Warning: Could not detect firmware version ({e}). Defaulting to 5.x", file=sys.stderr
        )
        return "5"


def get_takephoto_script() -> Path:
    """
    Get path to TakePhoto.py script based on firmware version.

    Returns:
        Path: Absolute path to TakePhoto.py for the installed firmware version

    Raises:
        FileNotFoundError: If TakePhoto.py doesn't exist for detected firmware version

    Example:
        >>> takephoto = get_takephoto_script()
        >>> # Returns: /opt/mothbox/5.x/TakePhoto.py (if firmware 5.x is installed)
    """
    firmware_version = get_firmware_version()
    takephoto_dir = MOTHBOX_HOME / f"{firmware_version}.x"
    takephoto_script = takephoto_dir / "TakePhoto.py"

    if not takephoto_script.exists():
        raise FileNotFoundError(
            f"TakePhoto.py not found at {takephoto_script}. "
            f"Detected firmware version: {firmware_version}.x. "
            f"Ensure firmware {firmware_version}.x is installed in {MOTHBOX_HOME}."
        )

    return takephoto_script


def _validate_gpio_pin(pin: int, pin_name: str, mode: str = "BCM") -> int:
    """
    Validate GPIO pin number for Raspberry Pi.

    Args:
        pin: GPIO pin number to validate
        pin_name: Name of the pin for error messages (e.g., 'Relay_Ch1')
        mode: Pin numbering mode - 'BCM' (Broadcom) or 'BOARD' (physical)

    Returns:
        int: The validated pin number

    Raises:
        ValueError: If pin number is invalid for the specified mode

    Note:
        - BCM mode: Valid range 2-27 (avoid 0,1 reserved for I2C)
        - BOARD mode: Valid range 1-40 (physical pin positions)
        - Added in Issue #13 Phase 1 for input validation
    """
    import sys

    if mode == "BCM":
        # BCM GPIO numbering (Broadcom chip)
        if pin < 0 or pin > 27:
            raise ValueError(
                f"Invalid BCM GPIO pin for {pin_name}: {pin}. "
                f"Valid range is 0-27. Check controls.txt configuration."
            )
        if pin in (0, 1):
            # Pins 0 and 1 are typically reserved for I2C (ID_SD, ID_SC)
            print(
                f"Warning: {pin_name} uses BCM GPIO {pin}, which is typically "
                f"reserved for I2C. Ensure this doesn't conflict with hardware.",
                file=sys.stderr,
            )
    elif mode == "BOARD":
        # Physical pin numbering (1-40 on 40-pin header)
        if pin < 1 or pin > 40:
            raise ValueError(
                f"Invalid BOARD mode pin for {pin_name}: {pin}. "
                f"Valid range is 1-40 (physical pins). Check controls.txt configuration."
            )
        # Pins 1,2,4,6,9,14,17,20,25,27,28,30,34,39 are power/ground (not GPIO)
        # But we allow them - validation happens at GPIO library level
    else:
        raise ValueError(f"Invalid GPIO mode: {mode}. Must be 'BCM' or 'BOARD'.")

    return pin


def get_gpio_pins() -> dict[str, int]:
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

        Pins are validated to be in BCM range (0-27). Invalid pins raise ValueError.
    """
    try:
        pins = get_control_values(CONTROLS_FILE)
        # Parse and validate each pin (BCM mode)
        return {
            "Relay_Ch1": _validate_gpio_pin(int(pins.get("Relay_Ch1", 26)), "Relay_Ch1", "BCM"),
            "Relay_Ch2": _validate_gpio_pin(int(pins.get("Relay_Ch2", 20)), "Relay_Ch2", "BCM"),
            "Relay_Ch3": _validate_gpio_pin(int(pins.get("Relay_Ch3", 21)), "Relay_Ch3", "BCM"),
        }
    except (FileNotFoundError, ValueError, KeyError) as e:
        import sys

        print(f"Warning: Could not load GPIO configuration ({e}). Using defaults.", file=sys.stderr)
        # Fallback to defaults if file not found or parse error
        return {"Relay_Ch1": 26, "Relay_Ch2": 20, "Relay_Ch3": 21}


def get_epaper_pins() -> dict[str, int]:
    """
    Load e-paper display GPIO pin configuration from controls.txt.

    Returns:
        dict: E-paper GPIO pin mappings

    Note:
        Default pins for Waveshare 2.13" e-paper display:
            RST_PIN=17, DC_PIN=25, CS_PIN=8, BUSY_PIN=24, PWR_PIN=18

        Pins are validated to be in BCM range (0-27). Invalid pins raise ValueError.
    """
    try:
        config = get_control_values(CONTROLS_FILE)
        # Parse and validate each pin (BCM mode)
        return {
            "RST_PIN": _validate_gpio_pin(
                int(config.get("epaper_rst_pin", "17")), "epaper_rst_pin", "BCM"
            ),
            "DC_PIN": _validate_gpio_pin(
                int(config.get("epaper_dc_pin", "25")), "epaper_dc_pin", "BCM"
            ),
            "CS_PIN": _validate_gpio_pin(
                int(config.get("epaper_cs_pin", "8")), "epaper_cs_pin", "BCM"
            ),
            "BUSY_PIN": _validate_gpio_pin(
                int(config.get("epaper_busy_pin", "24")), "epaper_busy_pin", "BCM"
            ),
            "PWR_PIN": _validate_gpio_pin(
                int(config.get("epaper_pwr_pin", "18")), "epaper_pwr_pin", "BCM"
            ),
        }
    except (FileNotFoundError, ValueError, KeyError) as e:
        import sys

        print(
            f"Warning: Could not load e-paper pin configuration ({e}). Using defaults.",
            file=sys.stderr,
        )
        return {
            "RST_PIN": 17,
            "DC_PIN": 25,
            "CS_PIN": 8,
            "BUSY_PIN": 24,
            "PWR_PIN": 18,
        }


def get_mux_pins() -> dict[str, int]:
    """
    Load multiplexer GPIO pin configuration from controls.txt.

    Returns:
        dict: Multiplexer GPIO pin mappings (BOARD mode)

    Note:
        Default pins for CD74HC4067 dual multiplexer setup:
            EN_A=31, EN_B=29, S0=33, S1=13, S2=12, S3=15, SIG=36

        Pins are validated to be in BOARD range (1-40). Invalid pins raise ValueError.
    """
    try:
        config = get_control_values(CONTROLS_FILE)
        # Parse and validate each pin (BOARD mode - physical pin numbers)
        return {
            "EN_A": _validate_gpio_pin(int(config.get("mux_en_a", "31")), "mux_en_a", "BOARD"),
            "EN_B": _validate_gpio_pin(int(config.get("mux_en_b", "29")), "mux_en_b", "BOARD"),
            "S0": _validate_gpio_pin(int(config.get("mux_s0", "33")), "mux_s0", "BOARD"),
            "S1": _validate_gpio_pin(int(config.get("mux_s1", "13")), "mux_s1", "BOARD"),
            "S2": _validate_gpio_pin(int(config.get("mux_s2", "12")), "mux_s2", "BOARD"),
            "S3": _validate_gpio_pin(int(config.get("mux_s3", "15")), "mux_s3", "BOARD"),
            "SIG": _validate_gpio_pin(int(config.get("mux_sig", "36")), "mux_sig", "BOARD"),
        }
    except (FileNotFoundError, ValueError, KeyError) as e:
        import sys

        print(
            f"Warning: Could not load multiplexer pin configuration ({e}). Using defaults.",
            file=sys.stderr,
        )
        return {
            "EN_A": 31,
            "EN_B": 29,
            "S0": 33,
            "S1": 13,
            "S2": 12,
            "S3": 15,
            "SIG": 36,
        }


def get_hardware_config() -> dict[str, Any]:
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
            # I2C bus configuration
            "i2c_bus": int(config.get("i2c_bus", "1")),
            # Relay module (already implemented via get_gpio_pins)
            "relay_enabled": config.get("relay_enabled", "true").lower() == "true",
            # INA260 power sensor
            "ina260_enabled": config.get("ina260_enabled", "false").lower() == "true",
            "ina260_address": int(config.get("ina260_address", "0x40"), 16),
            # E-paper display
            "epaper_enabled": config.get("epaper_enabled", "false").lower() == "true",
            "epaper_rst_pin": int(config.get("epaper_rst_pin", "17")),
            "epaper_dc_pin": int(config.get("epaper_dc_pin", "25")),
            "epaper_cs_pin": int(config.get("epaper_cs_pin", "8")),
            "epaper_busy_pin": int(config.get("epaper_busy_pin", "24")),
            "epaper_pwr_pin": int(config.get("epaper_pwr_pin", "18")),
            # GPS module
            "gps_enabled": config.get("gps_enabled", "false").lower() == "true",
            "gps_device": config.get("gps_device", "/dev/ttyAMA0"),
            "gps_baudrate": int(config.get("gps_baudrate", "9600")),
            "gps_timeout": int(config.get("gps_timeout", "60")),  # Legacy/fallback timeout
            # GPS adaptive timeout ranges for different start conditions
            "gps_timeout_hot": int(config.get("gps_timeout_hot", "15")),  # Hot start (<4 hours)
            "gps_timeout_warm": int(config.get("gps_timeout_warm", "60")),  # Warm start (4h-6d)
            "gps_timeout_cold": int(config.get("gps_timeout_cold", "90")),  # Cold start (6-28d)
            "gps_timeout_almanac": int(
                config.get("gps_timeout_almanac", "1200")
            ),  # Almanac expired (>28d)
            # Light sensor (optional)
            "light_sensor_enabled": config.get("light_sensor_enabled", "false").lower() == "true",
            "light_sensor_type": config.get("light_sensor_type", "BH1750"),  # BH1750 or LTR303
            "light_sensor_address": int(config.get("light_sensor_address", "0x23"), 16),
            # Temperature sensor (optional)
            "temperature_sensor_enabled": config.get("temperature_sensor_enabled", "false").lower()
            == "true",
            "temperature_sensor_type": config.get(
                "temperature_sensor_type", "TMP102"
            ),  # TMP102 or MCP9808
            "temperature_sensor_address": int(config.get("temperature_sensor_address", "0x48"), 16),
            # PCA9536 GPIO expander (optional)
            "pca9536_enabled": config.get("pca9536_enabled", "false").lower() == "true",
            "pca9536_address": int(config.get("pca9536_address", "0x21"), 16),
            # Multiplexer (optional)
            "mux_enabled": config.get("mux_enabled", "false").lower() == "true",
            "mux_type": config.get("mux_type", "i2c"),  # 'gpio' or 'i2c'
            "mux_address": int(config.get("mux_address", "0x20"), 16),  # I2C address if i2c mode
            "mux_en_a": int(config.get("mux_en_a", "31")),  # GPIO pins if gpio mode
            "mux_en_b": int(config.get("mux_en_b", "29")),
            "mux_s0": int(config.get("mux_s0", "33")),
            "mux_s1": int(config.get("mux_s1", "13")),
            "mux_s2": int(config.get("mux_s2", "12")),
            "mux_s3": int(config.get("mux_s3", "15")),
            "mux_sig": int(config.get("mux_sig", "36")),
        }
    except (FileNotFoundError, ValueError, KeyError) as e:
        import sys

        print(
            f"Warning: Could not load hardware configuration ({e}). Using defaults.",
            file=sys.stderr,
        )
        # Return defaults for all modules - all disabled by default except relays
        return {
            "i2c_bus": 1,
            "relay_enabled": True,  # Relays are core hardware, enabled by default
            "ina260_enabled": False,
            "ina260_address": 0x40,
            "epaper_enabled": False,
            "epaper_rst_pin": 17,
            "epaper_dc_pin": 25,
            "epaper_cs_pin": 8,
            "epaper_busy_pin": 24,
            "epaper_pwr_pin": 18,
            "gps_enabled": False,
            "gps_device": "/dev/ttyAMA0",
            "gps_baudrate": 9600,
            "gps_timeout": 60,
            "gps_timeout_hot": 15,
            "gps_timeout_warm": 60,
            "gps_timeout_cold": 90,
            "gps_timeout_almanac": 1200,
            "light_sensor_enabled": False,
            "light_sensor_type": "BH1750",
            "light_sensor_address": 0x23,
            "temperature_sensor_enabled": False,
            "temperature_sensor_type": "TMP102",
            "temperature_sensor_address": 0x48,
            "pca9536_enabled": False,
            "pca9536_address": 0x21,
            "mux_enabled": False,
            "mux_type": "i2c",
            "mux_address": 0x20,
            "mux_en_a": 31,
            "mux_en_b": 29,
            "mux_s0": 33,
            "mux_s1": 13,
            "mux_s2": 12,
            "mux_s3": 15,
            "mux_sig": 36,
        }


# Script paths (commonly referenced scripts)
def get_script_path(script_name):
    """
    Get the full path to a firmware script, preferring version-specific directories.

    Checks for the script in the version-specific directory first (e.g., 5.x/GPS.py),
    then falls back to the base firmware directory for backwards compatibility.

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
    if ".." in script_name or script_name.startswith("/"):
        raise ValueError(f"Invalid script name (path traversal attempt): {script_name}")

    # Check version-specific directory first (e.g., 5.x/GPS.py)
    # This matches how get_takephoto_script() works
    firmware_version = get_firmware_version()
    version_script_path = MOTHBOX_HOME / f"{firmware_version}.x" / script_name

    if version_script_path.exists():
        script_path = version_script_path
    else:
        # Fall back to base firmware directory for backwards compatibility
        script_path = FIRMWARE_DIR / script_name

    # Security: Resolve symlinks and verify final path stays within MOTHBOX_HOME
    # This catches:
    # - Symlink attacks (follows links to real destination)
    # - Encoded paths (Path.resolve() normalizes these)
    # - Partial directory name matches (relative_to() requires exact containment)
    try:
        resolved_path = script_path.resolve()
        mothbox_base = MOTHBOX_HOME.resolve()

        # Use relative_to() which raises ValueError if path is not within base
        # This prevents partial path matching (e.g., /firmware vs /firmware-evil)
        resolved_path.relative_to(mothbox_base)
    except ValueError:
        raise ValueError(
            f"Security: Script path resolves outside mothbox directory. Script: {script_name}"
        ) from None
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
        ISP_TUNING_DIR,
    ]

    for directory in dirs_to_create:
        directory.mkdir(parents=True, exist_ok=True)
        # Set permissions: owner rwx, group rx, no world access (single-user device)
        # Group access required for webui service (runs as gpio group)
        with suppress(OSError, PermissionError):
            os.chmod(directory, 0o750)  # nosec B103


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

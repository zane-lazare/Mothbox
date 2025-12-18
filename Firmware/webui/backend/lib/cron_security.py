"""
Cron job security utilities.

Provides whitelist-based validation for schedulable scripts,
preventing command injection attacks. Used by both:
- routes/scheduler.py (low-level cron API)
- routes/scheduler_ui.py (high-level schedule API - future)

This module implements a defense-in-depth approach:
1. Whitelist validation: Only approved scripts can be scheduled
2. Path validation: Scripts must resolve to valid paths within MOTHBOX_HOME
3. Command detection: Heuristics to identify Mothbox jobs for safe deletion

Issue #207 - Scheduler Phase 0: Extract Cron Security Library
"""

from typing import Final, TypeAlias

from mothbox_paths import MOTHBOX_HOME, get_script_path

# Type alias for validation result tuple
# Using TypeAlias for Python 3.11 compatibility (type keyword requires 3.12+)
ValidationResult: TypeAlias = tuple[bool, str | None]  # noqa: UP040

# =============================================================================
# CONSTANTS
# =============================================================================


# Whitelist of allowed Mothbox scripts
# Maps friendly keys to script filenames
ALLOWED_SCRIPTS: Final[dict[str, str]] = {
    # Photo capture
    "takephoto": "TakePhoto.py",
    # Scheduling
    "scheduler": "Scheduler.py",
    # Data management
    "backup": "Backup_Files.py",
    # GPIO control - Attraction lights
    "attract_on": "Attract_On.py",
    "attract_off": "Attract_Off.py",
    # GPIO control - Flash
    "flash_on": "Flash_On.py",
    "flash_off": "Flash_Off.py",
    # GPS
    "gps_sync": "GPS.py",
    # Display
    "update_display": "UpdateDisplay.py",
    # Debug/maintenance
    "debug_mode": "DebugMode.py",
    "stop_cron": "StopCron.py",
    "start_cron": "StartCron.py",
}


# Action type to script key mapping (for schedule actions)
# Maps action_type -> {action_name: script_key}
ACTION_TYPE_SCRIPTS: Final[dict[str, dict[str, str]]] = {
    "gpio": {
        "attract_on": "attract_on",
        "attract_off": "attract_off",
        "flash_on": "flash_on",
        "flash_off": "flash_off",
    },
    "camera": {
        "takephoto": "takephoto",
    },
    "gps_sync": {
        "sync": "gps_sync",
    },
    "service": {
        "backup": "backup",
        "update_display": "update_display",
    },
}


# =============================================================================
# FUNCTIONS
# =============================================================================


def get_allowed_script_keys() -> list[str]:
    """
    Get list of all allowed script keys.

    Returns:
        List of valid script key strings.
    """
    return list(ALLOWED_SCRIPTS.keys())


def validate_script_key(script_key: str | None) -> ValidationResult:
    """
    Validate script key against whitelist.

    Args:
        script_key: The script key to validate (e.g., "takephoto", "scheduler")

    Returns:
        ValidationResult: (True, None) if valid, (False, error_message) if invalid
    """
    if not script_key:
        allowed = ", ".join(ALLOWED_SCRIPTS.keys())
        return False, f"Script key is required. Allowed: {allowed}"

    if script_key not in ALLOWED_SCRIPTS:
        allowed = ", ".join(ALLOWED_SCRIPTS.keys())
        return False, f"Invalid script_key '{script_key}'. Allowed: {allowed}"

    return True, None


def get_script_filename(script_key: str | None) -> str | None:
    """
    Get the filename for a script key.

    Args:
        script_key: The script key to look up

    Returns:
        Script filename if found (e.g., "TakePhoto.py"), None otherwise
    """
    if not script_key:
        return None
    return ALLOWED_SCRIPTS.get(script_key)


def get_validated_script_path(script_key: str) -> str:
    """
    Get validated full path for a script key.

    Args:
        script_key: The script key to validate and resolve

    Returns:
        Full path string (e.g., "/opt/mothbox/TakePhoto.py")

    Raises:
        ValueError: If script_key is not in whitelist
    """
    valid, error = validate_script_key(script_key)
    if not valid:
        raise ValueError(error)

    script_name = ALLOWED_SCRIPTS[script_key]
    return str(get_script_path(script_name))


def get_validated_command(script_key: str) -> str:
    """
    Get validated command string for a script key.

    Constructs a cron-compatible command using the Python 3 interpreter
    and the validated script path.

    Args:
        script_key: The script key to validate and build command for

    Returns:
        Full command string (e.g., "/usr/bin/python3 /opt/mothbox/TakePhoto.py")

    Raises:
        ValueError: If script_key is not in whitelist
    """
    script_path = get_validated_script_path(script_key)
    return f"/usr/bin/python3 {script_path}"


def get_script_key_for_action(action_type: str, action_name: str) -> str | None:
    """
    Get the script key for a schedule action.

    Used by the scheduler UI to map action types and names to script keys
    that can be validated and executed.

    Args:
        action_type: Action type ("gpio", "camera", "gps_sync", "service")
        action_name: Specific action name ("attract_on", "takephoto", etc.)

    Returns:
        Script key if found, None otherwise
    """
    type_scripts = ACTION_TYPE_SCRIPTS.get(action_type, {})
    return type_scripts.get(action_name)


def is_mothbox_command(command: str | None) -> bool:
    """
    Check if a command string appears to be a Mothbox job.

    Uses multiple heuristics to identify Mothbox jobs:
    - Contains "mothbox" (case-insensitive)
    - Contains "TakePhoto" (common Mothbox script)
    - Contains MOTHBOX_HOME path

    This is used for safe deletion of cron jobs to prevent
    accidentally deleting system jobs.

    Note: This is a heuristic check, not a security guarantee.
    It's designed to be conservative and reject uncertain commands.

    Args:
        command: The cron command string to check

    Returns:
        True if command appears to be a Mothbox job, False otherwise
    """
    if not command:
        return False

    # Check for various Mothbox indicators
    indicators = [
        "mothbox" in command.lower(),
        "TakePhoto" in command,
        str(MOTHBOX_HOME) in command,
    ]

    return any(indicators)

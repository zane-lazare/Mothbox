"""
Mothbox Web UI - Shared Utility Functions

This module provides utilities shared across multiple route modules,
eliminating circular import issues and reducing code duplication.

Created to resolve issue #35: Refactor shared utility module to avoid circular imports
"""

import shutil
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

# ============================================================================
# CSV Security
# ============================================================================


def sanitize_csv_value(value):
    """
    Sanitize value to prevent CSV injection attacks

    Prevents formula injection (=, +, -, @) and removes dangerous characters.
    Limits length to prevent DoS attacks.

    This function protects against CSV injection vulnerabilities where malicious
    users could inject formulas that execute when the CSV is opened in spreadsheet
    applications like Excel, LibreOffice Calc, or Google Sheets.

    Security measures:
    - Prefixes values starting with =, +, -, @, tab, or CR with single quote
    - Removes newlines and carriage returns (prevents multi-line injection)
    - Limits value length to 1000 characters (DoS prevention)

    Args:
        value: Value to sanitize (any type, will be converted to string)

    Returns:
        str: Sanitized string safe for CSV output

    Examples:
        >>> sanitize_csv_value("=SUM(A1:A10)")
        "'=SUM(A1:A10)"
        >>> sanitize_csv_value("Normal text")
        "Normal text"
        >>> sanitize_csv_value(42)
        "42"
        >>> sanitize_csv_value("Multi\\nLine\\nText")
        "Multi Line Text"
    """
    str_value = str(value)

    # Prevent CSV formula injection by prefixing with single quote if starts with dangerous chars
    if str_value.startswith(("=", "+", "-", "@", "\t", "\r")):
        str_value = "'" + str_value

    # Remove newlines and carriage returns to prevent multi-line injection
    str_value = str_value.replace("\n", " ").replace("\r", " ")

    # Limit length to prevent DoS
    if len(str_value) > 1000:
        str_value = str_value[:1000]

    return str_value


# ============================================================================
# Camera Settings Validation
# ============================================================================


def _validate_int_enum(v, allowed_values):
    """
    Validate integer enum - rejects floats, raises exception for invalid types

    Used for camera settings that must be specific integer values (like modes).
    Strictly validates that the value is an integer (not float, not bool) and
    is in the allowed set.

    Args:
        v: Value to validate (int or convertible to int)
        allowed_values: List/set of allowed integer values

    Returns:
        bool: True if valid integer in allowed_values

    Raises:
        TypeError: If value is bool or float

    Examples:
        >>> _validate_int_enum(1, [0, 1, 2])
        True
        >>> _validate_int_enum(1.0, [0, 1, 2])
        TypeError: Float not allowed for integer enum
    """
    if isinstance(v, bool):
        raise TypeError("Boolean not allowed")
    if isinstance(v, float):
        raise TypeError("Float not allowed for integer enum")
    return int(v) in allowed_values


def _validate_exposure_time(v):
    """
    Validate ExposureTime - strict integer microseconds validation

    Validates exposure time is a positive integer in microseconds,
    preventing scientific notation, floats, and booleans.

    Args:
        v: Value to validate (int or string)

    Returns:
        bool: True if valid (positive int <1s in microseconds)

    Raises:
        TypeError: If value is bool or None
        ValueError: If value cannot be converted to int

    Examples:
        >>> _validate_exposure_time(500)
        True
        >>> _validate_exposure_time("500")
        True
        >>> _validate_exposure_time(500.5)
        TypeError: Float not allowed...
    """
    if v is None:
        raise TypeError("None not allowed for ExposureTime")
    if isinstance(v, bool):
        raise TypeError("Boolean not allowed for ExposureTime")

    # Try to convert to integer
    try:
        value = int(v)
    except (ValueError, TypeError) as err:
        raise ValueError(
            f"ExposureTime must be integer or digit string, got {type(v).__name__}"
        ) from err

    # Check range: must be positive and less than 1 second (1000000µs)
    return 0 < value < 1000000


def _validate_noise_reduction_mode(v):
    """
    Validate NoiseReductionMode - accepts int or digit string in [0,1,2]

    Validates the noise reduction mode setting for the camera.

    Args:
        v: Value to validate (int or string)

    Returns:
        bool: True if valid (int in [0,1,2] OR digit string converting to [0,1,2])

    Notes:
        - 0 = Off (no noise reduction)
        - 1 = Fast (minimal processing)
        - 2 = High Quality (maximum quality, slower)

    Examples:
        >>> _validate_noise_reduction_mode(0)
        True
        >>> _validate_noise_reduction_mode("2")
        True
        >>> _validate_noise_reduction_mode(3)
        False
    """
    # Accept integers directly or digit strings that convert to valid values
    return (isinstance(v, int) and v in [0, 1, 2]) or (
        isinstance(v, str) and v.isdigit() and int(v) in [0, 1, 2]
    )


# ============================================================================
# FIRMWARE CAMERA CONTROLS
# ============================================================================
# These are actual libcamera controls that can be passed to picamera2.set_controls()
# Used by TakePhoto.py and other firmware scripts
# These settings are stored in camera_settings.csv and read by firmware

ALLOWED_CAMERA_SETTINGS: dict[str, Callable[[Any], bool]] = {
    # Image quality controls (practical ranges: 0-4 for sharpness/contrast/saturation)
    "Sharpness": lambda v: 0.0 <= float(v) <= 4.0,
    "Brightness": lambda v: -1.0 <= float(v) <= 1.0,
    "Contrast": lambda v: 0.0 <= float(v) <= 4.0,
    "Saturation": lambda v: 0.0 <= float(v) <= 4.0,
    # Exposure controls
    "ExposureTime": _validate_exposure_time,  # microseconds
    "ExposureValue": lambda v: -8.0 <= float(v) <= 8.0,  # EV compensation
    "AnalogueGain": lambda v: 1.0 <= float(v) <= 16.0,  # ISO gain
    "AeEnable": lambda v: str(v).lower() in ["true", "false"],  # Auto exposure
    # Focus controls
    "AfMode": lambda v: _validate_int_enum(v, [0, 1, 2]),  # 0=Manual, 1=Auto Single, 2=Continuous
    "AfSpeed": lambda v: _validate_int_enum(v, [0, 1]),  # 0=Normal, 1=Fast
    "AfRange": lambda v: _validate_int_enum(v, [0, 1, 2]),  # 0=Normal, 1=Macro, 2=Full
    "AfMetering": lambda v: _validate_int_enum(v, [0, 1, 2]),  # Metering mode
    "LensPosition": lambda v: 0.0 <= float(v) <= 10.0,  # Diopters (manual focus)
    # Exposure metering controls
    "AeMeteringMode": lambda v: int(v) in [0, 1, 2],  # 0=Centre, 1=Spot, 2=Matrix
    # White balance controls
    "AwbEnable": lambda v: str(v).lower() in ["true", "false"],
    "AwbMode": lambda v: 0 <= int(v) <= 7,  # 0=Auto, 1=Incandescent, ..., 7=Custom
    "ColourGainRed": lambda v: 1.0 <= float(v) <= 4.0,  # Red channel gain
    "ColourGainBlue": lambda v: 1.0 <= float(v) <= 4.0,  # Blue channel gain
    # Noise reduction controls
    "NoiseReductionMode": lambda v: _validate_noise_reduction_mode(
        v
    ),  # 0=Off, 1=Fast, 2=High Quality
    # ISP features
    "LensShadingEnable": lambda v: str(v).lower() in ["true", "false"],
    "DefectCorrectionEnable": lambda v: str(v).lower() in ["true", "false"],
    "UseCustomTuning": lambda v: str(v).lower() in ["true", "false"],
}

# ============================================================================
# WEBUI WORKFLOW SETTINGS
# ============================================================================
# These are webui-specific settings that control capture workflows
# NOT passed to picamera2.set_controls() - used by webui logic only
# These settings are stored in webui_settings.csv

ALLOWED_WEBUI_SETTINGS: dict[str, Callable[[Any], bool]] = {
    # HDR/Bracketing workflow
    "HDR": lambda v: int(v) in [1, 3, 5, 7],  # Number of bracketed exposures
    "HDR_width": lambda v: 1000 <= int(v) <= 50000,  # Bracket step size (µs)
    # Focus Bracketing workflow
    "FocusBracket": lambda v: 1 <= int(v) <= 10,  # Number of focus steps
    "FocusBracket_Start": lambda v: 0.0 <= float(v) <= 10.0,  # Start focus position (diopters)
    "FocusBracket_End": lambda v: 0.0 <= float(v) <= 10.0,  # End focus position (diopters)
    # Focus Bracketing - Advanced Timing Settings
    "FlashDelay_BeforeCapture": lambda v: 0
    <= int(v)
    <= 500,  # Delay after flash on, before capture (ms)
    "FlashDelay_AfterCapture": lambda v: 0
    <= int(v)
    <= 500,  # Delay after capture, before flash off (ms)
    "FocusBracket_SettleDelay": lambda v: 100
    <= int(v)
    <= 2000,  # Lens settle delay between focus changes (ms)
    # Focus Bracketing - Color Consistency Settings
    "FocusBracket_LockColorGains": lambda v: int(v) in [0, 1],  # 0=Use AWB, 1=Lock gains
    "FocusBracket_ColorGainRed": lambda v: 1.0 <= float(v) <= 4.0,  # Red channel gain
    "FocusBracket_ColorGainBlue": lambda v: 1.0 <= float(v) <= 4.0,  # Blue channel gain
    # Auto-calibration
    "AutoCalibration": lambda v: int(v) in [0, 1],  # 0=Off, 1=On
    "AutoCalibrationPeriod": lambda v: 1 <= int(v) <= 10000,  # Photos between calibrations
    # Image format
    "ImageFileType": lambda v: int(v) in [0, 1, 2],  # 0=JPEG, 1=PNG, 2=BMP
    "VerticalFlip": lambda v: int(v) in [0, 1],  # 0=No flip, 1=Flip
    # Device naming
    "Name": lambda v: isinstance(v, str) and 1 <= len(v) <= 50,  # Device name
    # Focus peaking (preview-only overlay)
    "FocusPeakingEnabled": lambda v: str(v).lower() in ["true", "false"],
    "FocusPeakingIntensity": lambda v: 50 <= int(v) <= 200,
    "FocusPeakingColour": lambda v: str(v).lower() in ["green", "red", "yellow", "cyan", "magenta"],
    "FocusPeakingColor": lambda v: str(v).lower()
    in ["green", "red", "yellow", "cyan", "magenta"],  # American spelling alias
    "FocusPeakingAlgorithm": lambda v: str(v).lower() in ["laplacian", "sobel", "canny"],
}

# Liveview settings validation schema (snake_case WebUI settings)
# These settings control the live preview stream and real-time camera controls
ALLOWED_LIVEVIEW_SETTINGS: dict[str, Callable[[Any], bool]] = {
    # Boolean controls - Enable/disable features
    "focus_peaking_enabled": lambda v: str(v).lower() in ["true", "false"],
    "awb_enable": lambda v: str(v).lower() in ["true", "false"],
    "ae_enable": lambda v: str(v).lower() in ["true", "false"],
    "lens_shading_enable": lambda v: str(v).lower() in ["true", "false"],
    "defect_correction_enable": lambda v: str(v).lower() in ["true", "false"],
    "use_custom_tuning": lambda v: str(v).lower() in ["true", "false"],
    # Integer enumeration controls (modes/ranges/speeds)
    "af_mode": lambda v: _validate_int_enum(v, [0, 1, 2]),  # 0=Manual, 1=Auto Single, 2=Continuous
    "af_speed": lambda v: _validate_int_enum(v, [0, 1]),  # 0=Normal, 1=Fast
    "af_range": lambda v: _validate_int_enum(v, [0, 1, 2]),  # 0=Normal, 1=Macro, 2=Full
    "af_metering": lambda v: _validate_int_enum(v, [0, 1, 2]),  # 0=Auto, 1=Windows, 2=Off
    "awb_mode": lambda v: int(v) in [0, 1, 2, 3, 4, 5, 6, 7],  # 0=Auto, 1-7=Presets
    "noise_reduction_mode": lambda v: _validate_noise_reduction_mode(v),  # 0=Off, 1=Fast, 2=HQ
    "ae_metering_mode": lambda v: int(v) in [0, 1, 2],  # 0=Centre, 1=Spot, 2=Matrix
    # Float controls - Image quality and camera parameters
    "sharpness": lambda v: 0.0 <= float(v) <= 4.0,
    "brightness": lambda v: -1.0 <= float(v) <= 1.0,
    "contrast": lambda v: 0.0 <= float(v) <= 4.0,
    "saturation": lambda v: 0.0 <= float(v) <= 4.0,
    "lens_position": lambda v: 0.0 <= float(v) <= 10.0,  # Diopters (manual focus)
    "exposure_value": lambda v: -8.0 <= float(v) <= 8.0,  # EV compensation
    "analogue_gain": lambda v: 1.0 <= float(v) <= 16.0,  # ISO gain
    "colour_gains_red": lambda v: 1.0 <= float(v) <= 4.0,  # Red channel gain
    "colour_gains_blue": lambda v: 1.0 <= float(v) <= 4.0,  # Blue channel gain
    # Integer controls - Timing and discrete values
    "exposure_time": _validate_exposure_time,  # Microseconds (µs)
    # Focus peaking overlay controls (preview-only visual aid)
    "focus_peaking_intensity": lambda v: 50 <= int(v) <= 200,  # Edge detection strength
    "focus_peaking_colour": lambda v: str(v).lower()
    in ["green", "red", "yellow", "cyan", "magenta"],
    "focus_peaking_color": lambda v: str(v).lower()
    in ["green", "red", "yellow", "cyan", "magenta"],  # American spelling
    "focus_peaking_algorithm": lambda v: str(v).lower() in ["laplacian", "sobel", "canny"],
}


# ============================================================================
# CSV VALUE COERCION
# ============================================================================
# TakePhoto.py reads camera_settings.csv and expects specific types:
#   - Integer settings (HDR, FocusBracket, ImageFileType, etc.): "1", "3", "0"
#   - Float settings (Sharpness, LensPosition, etc.): "1.5", "2.0"
#   - Bool-string settings (AeEnable, AwbEnable): "True", "False"
#   - String settings (Name): "mothbox"
#
# The webui form may pass Python booleans (True/False) or strings ("True"/"False")
# for integer settings. This function normalizes values before CSV write.

# Import type sets from shared schema (single source of truth)
from camera_settings_schema import BOOL_STRING_SETTINGS as _BOOL_STRING_SETTINGS
from camera_settings_schema import FLOAT_SETTINGS as _FLOAT_SETTINGS
from camera_settings_schema import INT_SETTINGS as _INT_SETTINGS


def coerce_for_csv(key: str, value) -> str:
    """Coerce a setting value to the correct string representation for CSV.

    Ensures TakePhoto.py receives values in the types it expects.
    Python booleans and string "True"/"False" are converted to "1"/"0"
    for integer settings, preserving "True"/"False" only for settings
    that TakePhoto.py reads as boolean strings.
    """
    if key in _INT_SETTINGS:
        # Convert bool -> int first (True=1, False=0), then to string
        if isinstance(value, bool):
            return str(int(value))
        # Handle string "True"/"False" for int settings
        if isinstance(value, str) and value.lower() in ("true", "false"):
            return "1" if value.lower() == "true" else "0"
        return str(int(value))
    elif key in _FLOAT_SETTINGS:
        return str(float(value))
    elif key in _BOOL_STRING_SETTINGS:
        # Normalize to capitalized "True"/"False"
        if isinstance(value, bool):
            return str(value)
        return str(value).capitalize() if str(value).lower() in ("true", "false") else str(value)
    else:
        return str(value)


# ============================================================================
# File Management Utilities
# ============================================================================


def create_backup(file_path: Path, keep: int = 5) -> Path | None:
    """
    Create a timestamped backup of a configuration file

    Creates backup with format: filename.ext.backup.YYYYMMDD_HHMMSS
    Automatically cleans up old backups beyond the keep limit.

    Args:
        file_path: Path to the file to backup
        keep: Number of backups to retain (default: 5)

    Returns:
        Path to the backup file, or None if backup failed

    Examples:
        >>> backup = create_backup(Path("/config/settings.csv"))
        >>> # Creates: /config/settings.csv.backup.20250129_143052

        >>> backup = create_backup(Path("/config/controls.txt"), keep=3)
        >>> # Creates backup and keeps only 3 most recent backups
    """
    if not file_path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = file_path.with_suffix(f"{file_path.suffix}.backup.{timestamp}")

    try:
        shutil.copy2(file_path, backup_path)

        # Cleanup old backups - keep only the most recent 'keep' backups
        backup_pattern = f"{file_path.name}.backup.*"
        backups = sorted(
            file_path.parent.glob(backup_pattern), key=lambda p: p.stat().st_mtime, reverse=True
        )

        # Remove old backups beyond the keep limit
        for old_backup in backups[keep:]:
            try:
                old_backup.unlink()
            except Exception as e:
                print(f"Warning: Could not delete old backup {old_backup}: {e}")

        return backup_path
    except Exception as e:
        print(f"Warning: Failed to create backup of {file_path}: {e}")
        return None


def validate_path_within_directory(path: Path, base_dir: Path) -> Path:
    """
    Validate that a path is within a base directory (path traversal protection)

    Uses resolve() and relative_to() to ensure the resolved path
    is actually within the base directory, preventing path traversal attacks
    like "../../../etc/passwd".

    Args:
        path: Path to validate (can be relative or contain .. components)
        base_dir: Base directory that path must be within

    Returns:
        Path: Resolved absolute path (guaranteed to be within base_dir)

    Raises:
        ValueError: If path is outside base_dir (path traversal detected)
        RuntimeError: If resolve() fails (e.g., symlink loop, permission denied)

    Examples:
        >>> # Valid path within directory
        >>> validate_path_within_directory(
        ...     Path("photos/2025/image.jpg"), Path("/home/mothbox/photos")
        ... )
        Path('/home/mothbox/photos/2025/image.jpg')

        >>> # Path traversal attempt - raises ValueError
        >>> validate_path_within_directory(
        ...     Path("../../../etc/passwd"), Path("/home/mothbox/photos")
        ... )
        ValueError: Path is outside base directory

    Security:
        - Resolves all symlinks and .. components
        - Checks that final absolute path is within base_dir
        - Prevents directory traversal attacks
        - Safe for user-provided input
    """
    full_path = (base_dir / path).resolve()
    base_dir_resolved = base_dir.resolve()

    # Ensure path is within base_dir (raises ValueError if not)
    full_path.relative_to(base_dir_resolved)

    return full_path


# ============================================================================
# Disk Space Management
# ============================================================================


def check_disk_space(directory: Path, min_mb: int = 100) -> tuple[bool, int]:
    """
    Check if directory has sufficient free space

    Args:
        directory: Path to check
        min_mb: Minimum required space in MB

    Returns:
        tuple: (has_space: bool, available_mb: int)
    """
    try:
        stat = shutil.disk_usage(directory)
        available_mb = stat.free // (1024 * 1024)
        return available_mb >= min_mb, available_mb
    except Exception:
        return False, 0


def get_last_calibration_time(camera_settings_path: Path) -> datetime | None:
    """
    Extract LastCalibration timestamp from camera_settings.csv

    Args:
        camera_settings_path: Path to camera_settings.csv

    Returns:
        datetime | None: Last calibration timestamp or None if not found
    """
    try:
        with open(camera_settings_path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("LastCalibration,"):
                    timestamp_str = line.split(",", 1)[1].strip()
                    return datetime.fromisoformat(timestamp_str)
    except Exception:
        pass
    return None

"""
Mothbox Web UI - Shared Utility Functions

This module provides utilities shared across multiple route modules,
eliminating circular import issues and reducing code duplication.

Created to resolve issue #35: Refactor shared utility module to avoid circular imports
"""

from pathlib import Path
from typing import Callable, Dict, Any, Optional
import shutil
from datetime import datetime


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
    if str_value.startswith(('=', '+', '-', '@', '\t', '\r')):
        str_value = "'" + str_value

    # Remove newlines and carriage returns to prevent multi-line injection
    str_value = str_value.replace('\n', ' ').replace('\r', ' ')

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
    Validate ExposureTime - must be integer or digit string in range

    Exposure time is specified in microseconds. Must be positive and less
    than 1 second (1,000,000 µs) to prevent excessively long exposures.

    Args:
        v: Value to validate (int or string digits)

    Returns:
        bool: True if valid exposure time

    Raises:
        TypeError: If value is None or bool
        ValueError: If value cannot be converted to int

    Examples:
        >>> _validate_exposure_time(10000)  # 10ms
        True
        >>> _validate_exposure_time("50000")  # 50ms
        True
        >>> _validate_exposure_time(2000000)  # 2s - too long
        False
    """
    if v is None:
        raise TypeError("None not allowed for ExposureTime")
    if isinstance(v, bool):
        raise TypeError("Boolean not allowed for ExposureTime")

    # Try to convert to integer
    try:
        value = int(v)
    except (ValueError, TypeError):
        raise ValueError(f"ExposureTime must be integer or digit string, got {type(v).__name__}")

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
    # Accept integers directly
    if isinstance(v, int) and v in [0, 1, 2]:
        return True
    # Accept digit strings that convert to valid values
    if isinstance(v, str) and v.isdigit() and int(v) in [0, 1, 2]:
        return True
    return False


# Camera settings validation schema (PascalCase picamera2 controls)
# These map to libcamera controls used when capturing photos
ALLOWED_CAMERA_SETTINGS: Dict[str, Callable[[Any], bool]] = {
    # Image quality controls (practical ranges: 0-4 for sharpness/contrast/saturation)
    'Sharpness': lambda v: 0.0 <= float(v) <= 4.0,
    'Brightness': lambda v: -1.0 <= float(v) <= 1.0,
    'Contrast': lambda v: 0.0 <= float(v) <= 4.0,
    'Saturation': lambda v: 0.0 <= float(v) <= 4.0,

    # Exposure controls
    'ExposureTime': _validate_exposure_time,  # microseconds
    'ExposureValue': lambda v: -8.0 <= float(v) <= 8.0,  # EV compensation
    'AnalogueGain': lambda v: 1.0 <= float(v) <= 16.0,  # ISO gain
    'AeEnable': lambda v: str(v).lower() in ['true', 'false'],  # Auto exposure

    # Focus controls
    'AfMode': lambda v: _validate_int_enum(v, [0, 1, 2]),  # 0=Manual, 1=Auto Single, 2=Continuous
    'AfSpeed': lambda v: _validate_int_enum(v, [0, 1]),  # 0=Normal, 1=Fast
    'AfRange': lambda v: _validate_int_enum(v, [0, 1, 2]),  # 0=Normal, 1=Macro, 2=Full
    'AfMetering': lambda v: _validate_int_enum(v, [0, 1, 2]),  # Metering mode
    'LensPosition': lambda v: 0.0 <= float(v) <= 10.0,  # Diopters (manual focus)

    # Exposure metering controls
    'AeMeteringMode': lambda v: int(v) in [0, 1, 2],  # 0=Centre, 1=Spot, 2=Matrix

    # White balance controls
    'AwbEnable': lambda v: str(v).lower() in ['true', 'false'],
    'AwbMode': lambda v: 0 <= int(v) <= 7,  # 0=Auto, 1=Incandescent, ..., 7=Custom
    'ColourGainRed': lambda v: 1.0 <= float(v) <= 4.0,  # Red channel gain
    'ColourGainBlue': lambda v: 1.0 <= float(v) <= 4.0,  # Blue channel gain

    # Noise reduction controls
    'NoiseReductionMode': lambda v: _validate_noise_reduction_mode(v),  # 0=Off, 1=Fast, 2=High Quality

    # ISP features (Phase: ISP Tuning)
    'LensShadingEnable': lambda v: str(v).lower() in ['true', 'false'],
    'DefectCorrectionEnable': lambda v: str(v).lower() in ['true', 'false'],
    'UseCustomTuning': lambda v: str(v).lower() in ['true', 'false'],

    # HDR/Bracketing
    'HDR': lambda v: int(v) in [1, 3, 5, 7],  # Number of bracketed exposures
    'HDR_width': lambda v: 1000 <= int(v) <= 50000,  # Bracket step size (µs)

    # Focus Bracketing
    'FocusBracket': lambda v: 1 <= int(v) <= 10,  # Number of focus steps
    'FocusBracket_Start': lambda v: 0.0 <= float(v) <= 10.0,  # Start focus position (diopters)
    'FocusBracket_End': lambda v: 0.0 <= float(v) <= 10.0,  # End focus position (diopters)

    # Focus Bracketing - Advanced Timing Settings
    'FlashDelay_BeforeCapture': lambda v: 0 <= int(v) <= 500,  # Delay after flash on, before capture (ms)
    'FlashDelay_AfterCapture': lambda v: 0 <= int(v) <= 500,  # Delay after capture, before flash off (ms)
    'FocusBracket_SettleDelay': lambda v: 100 <= int(v) <= 2000,  # Lens settle delay between focus changes (ms)

    # Focus Bracketing - Color Consistency Settings
    'FocusBracket_LockColorGains': lambda v: int(v) in [0, 1],  # 0=Use AWB, 1=Lock gains
    'FocusBracket_ColorGainRed': lambda v: 1.0 <= float(v) <= 4.0,  # Red channel gain
    'FocusBracket_ColorGainBlue': lambda v: 1.0 <= float(v) <= 4.0,  # Blue channel gain

    # Auto-calibration
    'AutoCalibration': lambda v: int(v) in [0, 1],  # 0=Off, 1=On
    'AutoCalibrationPeriod': lambda v: 1 <= int(v) <= 10000,  # Photos between calibrations

    # Image format
    'ImageFileType': lambda v: int(v) in [0, 1, 2],  # 0=JPEG, 1=PNG, 2=BMP
    'VerticalFlip': lambda v: int(v) in [0, 1],  # 0=No flip, 1=Flip

    # Focus peaking (preview-only overlay)
    'FocusPeakingEnabled': lambda v: str(v).lower() in ['true', 'false'],
    'FocusPeakingIntensity': lambda v: 50 <= int(v) <= 200,
    'FocusPeakingColor': lambda v: str(v).lower() in ['green', 'red', 'yellow', 'cyan', 'magenta'],
    'FocusPeakingAlgorithm': lambda v: str(v).lower() in ['laplacian', 'sobel', 'canny'],
}

# Liveview settings validation schema (snake_case WebUI settings)
# These settings control the live preview stream and real-time camera controls
ALLOWED_LIVEVIEW_SETTINGS: Dict[str, Callable[[Any], bool]] = {
    # Boolean controls - Enable/disable features
    'focus_peaking_enabled': lambda v: str(v).lower() in ['true', 'false'],
    'awb_enable': lambda v: str(v).lower() in ['true', 'false'],
    'ae_enable': lambda v: str(v).lower() in ['true', 'false'],
    'lens_shading_enable': lambda v: str(v).lower() in ['true', 'false'],
    'defect_correction_enable': lambda v: str(v).lower() in ['true', 'false'],
    'use_custom_tuning': lambda v: str(v).lower() in ['true', 'false'],

    # Integer controls - Modes and discrete values
    'noise_reduction_mode': lambda v: int(v) in [0, 1, 2],  # 0=Off, 1=Fast, 2=High Quality
    'awb_mode': lambda v: 0 <= int(v) <= 7,  # 0=Auto, 1=Incandescent, ..., 7=Custom
    'af_mode': lambda v: int(v) in [0, 1, 2],  # 0=Manual, 1=Auto Single, 2=Continuous
    'af_speed': lambda v: int(v) in [0, 1],  # 0=Normal, 1=Fast
    'af_range': lambda v: int(v) in [0, 1, 2],  # 0=Normal, 1=Macro, 2=Full
    'ae_metering_mode': lambda v: int(v) in [0, 1, 2],  # 0=Centre, 1=Spot, 2=Matrix

    # Stream configuration (integers)
    'stream_width': lambda v: 640 <= int(v) <= 1920,
    'stream_height': lambda v: 480 <= int(v) <= 1080,
    'stream_quality': lambda v: 1 <= int(v) <= 100,  # JPEG quality
    'stream_framerate': lambda v: 1 <= int(v) <= 60,

    # Float controls - Continuous adjustments
    'sharpness': lambda v: 0.0 <= float(v) <= 4.0,
    'brightness': lambda v: -1.0 <= float(v) <= 1.0,
    'contrast': lambda v: 0.0 <= float(v) <= 4.0,
    'saturation': lambda v: 0.0 <= float(v) <= 4.0,
    'analogue_gain': lambda v: 1.0 <= float(v) <= 16.0,  # ISO gain
    'exposure_value': lambda v: -8.0 <= float(v) <= 8.0,  # EV compensation
    'lens_position': lambda v: 0.0 <= float(v) <= 10.0,  # Diopters (manual focus)

    # Color gains (floats) - for manual white balance
    'colour_gains_red': lambda v: 1.0 <= float(v) <= 4.0,
    'colour_gains_blue': lambda v: 1.0 <= float(v) <= 4.0,

    # Focus peaking configuration
    'focus_peaking_intensity': lambda v: 0.0 <= float(v) <= 200.0,
    'focus_peaking_color': lambda v: str(v).lower() in ['green', 'red', 'yellow', 'cyan', 'magenta'],
    'focus_peaking_algorithm': lambda v: str(v).lower() in ['laplacian', 'sobel', 'canny'],
}


# ============================================================================
# File Backup Utilities
# ============================================================================

def create_backup(file_path: Path, keep: int = 5) -> Optional[Path]:
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
    backup_path = file_path.with_suffix(f'{file_path.suffix}.backup.{timestamp}')

    try:
        shutil.copy2(file_path, backup_path)

        # Cleanup old backups - keep only the most recent 'keep' backups
        backup_pattern = f"{file_path.name}.backup.*"
        backups = sorted(
            file_path.parent.glob(backup_pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True
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


# ============================================================================
# Path Security Utilities
# ============================================================================

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
        ...     Path("photos/2025/image.jpg"),
        ...     Path("/home/mothbox/photos")
        ... )
        Path('/home/mothbox/photos/2025/image.jpg')

        >>> # Path traversal attempt - raises ValueError
        >>> validate_path_within_directory(
        ...     Path("../../../etc/passwd"),
        ...     Path("/home/mothbox/photos")
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

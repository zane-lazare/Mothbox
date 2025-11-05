"""
Camera Control Naming Convention Mappings

This module provides centralized mapping between the three naming conventions
used throughout the camera control system:

Naming Convention Layers:
--------------------------
1. Frontend (JavaScript):  camelCase    - colourGainRed, exposureTime
2. Backend Settings:       snake_case   - colour_gains_red, exposure_time
3. Picamera2/libcamera:   PascalCase   - ColourGainRed, ExposureTime

Why Three Conventions?
----------------------
- Frontend: JavaScript convention is camelCase
- Backend: Python convention is snake_case
- Camera API: Picamera2/libcamera requires PascalCase

This module eliminates implicit conversions by providing:
- Complete bidirectional mappings
- Type conversion utilities
- Helper functions for common operations
- Single source of truth for control names

Usage Examples:
--------------
# Convert settings to camera controls
settings = {'exposure_time': 500, 'sharpness': 1.0}
controls = build_picamera_controls(settings)
camera.set_controls(controls)

# Convert metadata for frontend
metadata = camera.capture_metadata()
frontend_data = from_picamera_metadata(metadata)
emit('metadata_update', frontend_data)

# Handle dual naming (PascalCase or snake_case)
key = normalize_control_key('colour_gains_red')  # → 'ColourGainRed'
key = normalize_control_key('ColourGainRed')     # → 'ColourGainRed'

Adding New Controls:
-------------------
1. Add to SNAKE_TO_PASCAL mapping
2. Add to CAMEL_TO_SNAKE if used in frontend
3. PASCAL_TO_SNAKE updates automatically (reverse mapping)
4. Update type conversion functions if needed
5. Update unit tests

See Also:
---------
- Frontend: /webui/frontend/src/utils/cameraControlMapping.js
- Tests: /Tests/unit/test_camera_control_mapping.py
- Documentation: NAMING_CONVENTION_ANALYSIS.md
"""

from typing import Any

# ============================================================================
# MAPPING DICTIONARIES
# ============================================================================

# Backend snake_case → Picamera2 PascalCase
SNAKE_TO_PASCAL = {
    # Core image quality (4)
    "sharpness": "Sharpness",
    "brightness": "Brightness",
    "contrast": "Contrast",
    "saturation": "Saturation",
    # Autofocus (6)
    "af_mode": "AfMode",
    "af_speed": "AfSpeed",
    "af_range": "AfRange",
    "af_metering": "AfMetering",
    "af_state": "AfState",
    "af_windows": "AfWindows",
    "lens_position": "LensPosition",
    # Auto exposure (4)
    "ae_enable": "AeEnable",
    "ae_locked": "AeLocked",
    "ae_metering_mode": "AeMeteringMode",
    "exposure_time": "ExposureTime",
    "analogue_gain": "AnalogueGain",
    # Auto white balance (6)
    "awb_enable": "AwbEnable",
    "awb_locked": "AwbLocked",
    "awb_mode": "AwbMode",
    "colour_gains": "ColourGains",
    "colour_gains_red": "ColourGainRed",
    "colour_gains_blue": "ColourGainBlue",
    "colour_temperature": "ColourTemperature",
    # ISP features (3)
    "noise_reduction_mode": "NoiseReductionMode",
    "lens_shading_map_mode": "LensShadingMapMode",
    "hot_pixel_mode": "HotPixelMode",
    # Metadata/other controls (15)
    "scaler_crop": "ScalerCrop",
    "digital_gain": "DigitalGain",
    "focus_fom": "FocusFoM",
    "sensor_timestamp": "SensorTimestamp",
    "frame_duration": "FrameDuration",
    "sensor_black_levels": "SensorBlackLevels",
    "sensor_temperature": "SensorTemperature",
    "lux": "Lux",
    # Focus peaking (liveview only - not hardware controls)
    "focus_peaking_enabled": "FocusPeakingEnabled",
    "focus_peaking_intensity": "FocusPeakingIntensity",
    "focus_peaking_colour": "FocusPeakingColour",
    "focus_peaking_algorithm": "FocusPeakingAlgorithm",
}

# Auto-generated reverse mapping: PascalCase → snake_case
PASCAL_TO_SNAKE = {v: k for k, v in SNAKE_TO_PASCAL.items()}

# Frontend camelCase → Backend snake_case
CAMEL_TO_SNAKE = {
    # Core image quality
    "sharpness": "sharpness",
    "brightness": "brightness",
    "contrast": "contrast",
    "saturation": "saturation",
    # Colour gains (note: separate components)
    "colourGainRed": "colour_gains_red",
    "colourGainBlue": "colour_gains_blue",
    # Exposure
    "exposureTime": "exposure_time",
    "analogueGain": "analogue_gain",
    "aeEnable": "ae_enable",
    "aeLocked": "ae_locked",
    "aeMeteringMode": "ae_metering_mode",
    # White balance
    "awbEnable": "awb_enable",
    "awbLocked": "awb_locked",
    "awbMode": "awb_mode",
    "colourTemperature": "colour_temperature",
    # Focus
    "afMode": "af_mode",
    "afSpeed": "af_speed",
    "afRange": "af_range",
    "afState": "af_state",
    "lensPosition": "lens_position",
    "focusFom": "focus_fom",
    # Other
    "noiseReductionMode": "noise_reduction_mode",
    "digitalGain": "digital_gain",
    "scalerCrop": "scaler_crop",
    "sensorTimestamp": "sensor_timestamp",
    "frameDuration": "frame_duration",
    "lux": "lux",
    # Focus peaking (liveview only)
    "focusPeakingEnabled": "focus_peaking_enabled",
    "focusPeakingIntensity": "focus_peaking_intensity",
    "focusPeakingColour": "focus_peaking_colour",
    "focusPeakingAlgorithm": "focus_peaking_algorithm",
}

# Auto-generated reverse mapping: snake_case → camelCase
SNAKE_TO_CAMEL = {v: k for k, v in CAMEL_TO_SNAKE.items()}


# ============================================================================
# TYPE CONVERSION UTILITIES
# ============================================================================

# Define which controls expect which types
BOOLEAN_CONTROLS = {
    "ae_enable",
    "awb_enable",
    "ae_locked",
    "awb_locked",
    "focus_peaking_enabled",
}

INTEGER_CONTROLS = {
    "af_mode",
    "af_speed",
    "af_range",
    "af_metering",
    "af_state",
    "ae_metering_mode",
    "awb_mode",
    "exposure_time",
    "noise_reduction_mode",
    "lens_shading_map_mode",
    "hot_pixel_mode",
    "sensor_timestamp",
    "frame_duration",
    "focus_peaking_intensity",
}

FLOAT_CONTROLS = {
    "sharpness",
    "brightness",
    "contrast",
    "saturation",
    "analogue_gain",
    "digital_gain",
    "lens_position",
    "colour_gains_red",
    "colour_gains_blue",
    "focus_fom",
    "sensor_temperature",
    "lux",
    "colour_temperature",
}


def convert_from_settings_file(key: str, value: Any) -> Any:
    """
    Convert string from settings file to proper Python type.

    Handles conversion from text files (liveview_settings.txt, camera_settings.csv)
    where all values are stored as strings.

    Args:
        key: Control name in snake_case
        value: String value from file

    Returns:
        Properly typed value

    Examples:
        convert_from_settings_file('ae_enable', 'true') → True
        convert_from_settings_file('exposure_time', '500') → 500
        convert_from_settings_file('sharpness', '1.5') → 1.5
    """
    if not isinstance(value, str):
        return value  # Already proper type

    # Convert boolean strings
    if key in BOOLEAN_CONTROLS:
        return value.lower() in ("true", "1", "yes", "on")

    # Convert integer strings
    if key in INTEGER_CONTROLS:
        try:
            return int(value)
        except (ValueError, TypeError):
            return value

    # Convert float strings
    if key in FLOAT_CONTROLS:
        try:
            return float(value)
        except (ValueError, TypeError):
            # Intentional silent pass-through: Return original value unchanged
            # if conversion fails. Invalid values will be caught by the validation
            # layer (ALLOWED_CAMERA_SETTINGS/ALLOWED_LIVEVIEW_SETTINGS) with
            # proper error messages. This allows legitimate non-numeric values
            # (e.g., 'auto', 'default') to pass through without logging noise.
            return value

    # Special handling for colour_gains tuple
    if key == "colour_gains" and isinstance(value, str):
        # Expect format: "(2.259, 1.5)" or "2.259,1.5"
        value = value.strip("()").replace(" ", "")
        try:
            parts = value.split(",")
            if len(parts) == 2:
                return (float(parts[0]), float(parts[1]))
        except (ValueError, IndexError):
            pass

    return value


def convert_to_settings_file(key: str, value: Any) -> str:
    """
    Convert Python value to string for settings file.

    Used when writing liveview_settings.txt or camera_settings.csv.

    Args:
        key: Control name in snake_case
        value: Python value (any type)

    Returns:
        String representation for file storage

    Examples:
        convert_to_settings_file('ae_enable', True) → 'true'
        convert_to_settings_file('exposure_time', 500) → '500'
        convert_to_settings_file('sharpness', 1.5) → '1.5'
    """
    if key in BOOLEAN_CONTROLS:
        return "true" if value else "false"

    if key == "colour_gains" and isinstance(value, (tuple, list)):
        return f"({value[0]}, {value[1]})"

    return str(value)


def convert_to_picamera_type(key: str, value: Any) -> Any:
    """
    Convert value to type expected by Picamera2 for given control.

    This is used when accepting values from API requests that might be
    strings or wrong types.

    Args:
        key: Control name in snake_case
        value: Control value (any type)

    Returns:
        Value converted to proper type for Picamera2

    Examples:
        convert_to_picamera_type('ae_enable', 'true') → True
        convert_to_picamera_type('exposure_time', '500') → 500
    """
    return convert_from_settings_file(key, value)


# ============================================================================
# CORE CONVERSION FUNCTIONS
# ============================================================================


def normalize_control_key(key: str) -> str:
    """
    Accept any case variant, return PascalCase (for dual naming support).

    Handles the dual naming pattern in liveview_stream.py where
    both 'ColourGainRed' and 'colour_gains_red' should work.

    Args:
        key: Control name in any case

    Returns:
        PascalCase control name

    Examples:
        normalize_control_key('colour_gains_red') → 'ColourGainRed'
        normalize_control_key('ColourGainRed') → 'ColourGainRed'
        normalize_control_key('colourGainRed') → 'ColourGainRed'
    """
    # If already PascalCase, return as-is
    if key in PASCAL_TO_SNAKE:
        return key

    # Try converting from snake_case
    if key in SNAKE_TO_PASCAL:
        return SNAKE_TO_PASCAL[key]

    # Try converting from camelCase
    if key in CAMEL_TO_SNAKE:
        snake_key = CAMEL_TO_SNAKE[key]
        if snake_key in SNAKE_TO_PASCAL:
            return SNAKE_TO_PASCAL[snake_key]

    # Unknown key - return as-is
    return key


def to_picamera_control(key: str, value: Any) -> tuple[str, Any]:
    """
    Convert snake_case or camelCase key → PascalCase with type conversion.

    Args:
        key: Control name in snake_case or camelCase
        value: Control value (any type)

    Returns:
        Tuple of (PascalCase_key, typed_value)

    Examples:
        to_picamera_control('exposure_time', '500') → ('ExposureTime', 500)
        to_picamera_control('ae_enable', 'true') → ('AeEnable', True)
    """
    # Normalize key to PascalCase
    pascal_key = normalize_control_key(key)

    # Get snake_case version for type conversion
    snake_key = PASCAL_TO_SNAKE.get(pascal_key, key)

    # Convert value to proper type
    typed_value = convert_to_picamera_type(snake_key, value)

    return (pascal_key, typed_value)


def from_picamera_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """
    Convert entire metadata dict from PascalCase → snake_case.

    Args:
        metadata: Camera metadata dict with PascalCase keys

    Returns:
        Dict with snake_case keys for frontend emission

    Examples:
        from_picamera_metadata({'ExposureTime': 500, 'AnalogueGain': 8.0})
        → {'exposure_time': 500, 'analogue_gain': 8.0}
    """
    result = {}

    for pascal_key, value in metadata.items():
        # Convert key to snake_case
        snake_key = PASCAL_TO_SNAKE.get(pascal_key, pascal_key.lower())
        result[snake_key] = value

    return result


def build_picamera_controls(
    settings_dict: dict[str, Any], convert_types: bool = True
) -> dict[str, Any]:
    """
    Convert entire settings dict to Picamera2 controls dict.

    Args:
        settings_dict: Settings with snake_case keys
        convert_types: Whether to apply type conversion

    Returns:
        Dict with PascalCase keys ready for camera.set_controls()

    Examples:
        build_picamera_controls({
            'sharpness': 1.0,
            'exposure_time': '500',
            'ae_enable': 'true'
        })
        → {
            'Sharpness': 1.0,
            'ExposureTime': 500,
            'AeEnable': True
        }
    """
    controls = {}

    for key, value in settings_dict.items():
        if convert_types:
            pascal_key, typed_value = to_picamera_control(key, value)
            controls[pascal_key] = typed_value
        else:
            pascal_key = normalize_control_key(key)
            controls[pascal_key] = value

    return controls


# ============================================================================
# SPECIAL HANDLING FUNCTIONS
# ============================================================================


def handle_colour_gains(
    red: float | None = None, blue: float | None = None, current: tuple[float, float] = (2.259, 1.5)
) -> dict[str, tuple[float, float]]:
    """
    Handle colour gains component → tuple conversion.

    Colour gains are sent as separate red/blue values but must be
    applied as a tuple to the camera.

    Args:
        red: Red gain value (None to keep current)
        blue: Blue gain value (None to keep current)
        current: Current colour gains tuple

    Returns:
        Dict with 'ColourGains' key and tuple value

    Examples:
        handle_colour_gains(red=2.5, current=(2.0, 1.5))
        → {'ColourGains': (2.5, 1.5)}

        handle_colour_gains(blue=1.8, current=(2.0, 1.5))
        → {'ColourGains': (2.0, 1.8)}

        handle_colour_gains(red=2.5, blue=1.8)
        → {'ColourGains': (2.5, 1.8)}
    """
    current_red, current_blue = current

    new_red = red if red is not None else current_red
    new_blue = blue if blue is not None else current_blue

    return {"ColourGains": (new_red, new_blue)}


def split_colour_gains(colour_gains: tuple[float, float]) -> dict[str, float]:
    """
    Split colour gains tuple into separate red/blue components.

    Useful when converting from hardware format to frontend format.

    Args:
        colour_gains: Tuple of (red, blue) gains

    Returns:
        Dict with 'colour_gains_red' and 'colour_gains_blue' keys

    Examples:
        split_colour_gains((2.259, 1.5))
        → {'colour_gains_red': 2.259, 'colour_gains_blue': 1.5}
    """
    return {
        "colour_gains_red": colour_gains[0],
        "colour_gains_blue": colour_gains[1],
    }

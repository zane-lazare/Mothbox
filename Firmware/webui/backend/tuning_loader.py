"""
Camera ISP Tuning File Loader

Loads and applies Picamera2 tuning files for ISP features:
- Lens shading correction (vignetting correction) - runtime toggle available
- Defect pixel correction (stuck/dead pixel correction) - runtime toggle available
- Chromatic aberration correction (colour fringing correction) - Pi 5 only, tuning file only

Tuning files are JSON-based configuration files that control the Image Signal
Processor (ISP) pipeline. They must be loaded when the camera is created,
before configuration.

Note: CAC (Chromatic Aberration Correction) is only available on Raspberry Pi 5
with the PiSP hardware. It requires camera calibration and tuning file configuration
(rpi.cac block with lookup tables). CAC cannot be toggled at runtime.
"""

import json

# Setup path for mothbox imports
# Import camera control mapping
from camera_control_mapping import SNAKE_TO_PASCAL

from mothbox_paths import ISP_DEFAULT_TUNING_FILE, ISP_TUNING_DIR

# Tuning directory from centralized path configuration
TUNING_DIR = ISP_TUNING_DIR


def get_camera_model():
    """
    Detect camera model from Picamera2.

    Returns:
        str: Camera model name (e.g., 'imx708', 'imx477'), or 'unknown' if detection fails

    Note:
        This function requires Picamera2 to be available. If import fails,
        it returns 'unknown' to allow graceful fallback.
    """
    try:
        from picamera2 import Picamera2

        camera_info = Picamera2.global_camera_info()
        if camera_info:
            # Extract model from first camera
            model = camera_info[0].get("Model", "unknown")
            print(f"Detected camera model: {model}")
            return model
    except Exception as e:
        print(f"Warning: Could not detect camera model: {e}")

    return "unknown"


def load_tuning_file(camera_model=None):
    """
    Load tuning file for camera model.

    Args:
        camera_model (str, optional): Camera model name. If None, auto-detects.

    Returns:
        dict: Parsed tuning file JSON, or None if no tuning file found

    Lookup order:
        1. {camera_model}.json (e.g., ov64a40.json)
        2. camera_isp_tuning.json (fallback)

    Example:
        >>> tuning = load_tuning_file("imx708")
        >>> if tuning:
        ...     print(f"Loaded tuning version {tuning['version']}")
    """
    if not camera_model:
        camera_model = get_camera_model()

    # Try model-specific tuning file first
    tuning_file = TUNING_DIR / f"{camera_model}.json"

    if not tuning_file.exists():
        # Try fallback to default tuning file
        tuning_file = ISP_DEFAULT_TUNING_FILE
        print(f"Model-specific tuning not found, using default: {tuning_file}")

    if tuning_file.exists():
        try:
            with open(tuning_file) as f:
                tuning_data = json.load(f)
                print(f"Loaded ISP tuning file: {tuning_file}")
                return tuning_data
        except json.JSONDecodeError as e:
            print(f"Error parsing tuning file {tuning_file}: {e}")
            return None
        except Exception as e:
            print(f"Error loading tuning file {tuning_file}: {e}")
            return None

    print(f"No tuning file found (searched: {tuning_file})")
    return None


def apply_isp_controls(camera, lens_shading=True, defect_correction=True):
    """
    Apply ISP feature toggles to camera at runtime.

    Args:
        camera: Picamera2 instance (must be started)
        lens_shading (bool): Enable lens shading correction (vignetting fix)
        defect_correction (bool): Enable defect pixel correction (stuck pixel fix)

    Returns:
        bool: True if at least one control was applied successfully, False if all failed

    Note:
        Control names used here are based on libcamera control documentation:
        - LensShadingMapMode: 0=Off, 1=On (may not be available on all cameras)
        - HotPixelMode: 0=Off, 1=Fast, 2=HighQuality (we use Fast for performance)

        Controls are applied individually so one failure doesn't block others.
        Function checks control availability before attempting to set.

        Chromatic aberration correction (CAC) is NOT included here because:
        - Requires Pi 5 hardware (PiSP) - not available on Pi 4
        - Must be configured in tuning file (rpi.cac block with lookup tables)
        - Cannot be toggled at runtime - requires camera calibration data
        - Enabled automatically by libcamera if present in tuning file

    Important:
        This must be called AFTER camera.start() as controls only work on
        a running camera instance.
    """
    available_controls = camera.camera_controls
    applied_count = 0

    # Lens shading correction (vignetting fix)
    # Mode 0 = Off, Mode 1 = On
    # Note: Not available on some cameras (e.g., ov64a40) - always on via tuning file
    # Use centralized mapping
    lens_shading_control = SNAKE_TO_PASCAL["lens_shading_map_mode"]
    if lens_shading_control in available_controls:
        try:
            camera.set_controls({lens_shading_control: 1 if lens_shading else 0})
            print(f"ISP: Lens shading correction {'enabled' if lens_shading else 'disabled'}")
            applied_count += 1
        except Exception as e:
            print(f"Warning: Could not apply {lens_shading_control}: {e}")
    else:
        print(f"ISP: {lens_shading_control} not available (always on via tuning file)")

    # Defect pixel correction (hot/dead pixel fix)
    # Mode 0 = Off, Mode 1 = Fast, Mode 2 = HighQuality
    # We use Fast (1) for better performance
    # Use centralized mapping
    hot_pixel_control = SNAKE_TO_PASCAL["hot_pixel_mode"]
    if hot_pixel_control in available_controls:
        try:
            camera.set_controls({hot_pixel_control: 1 if defect_correction else 0})
            print(
                f"ISP: Defect pixel correction {'enabled (Fast mode)' if defect_correction else 'disabled'}"
            )
            applied_count += 1
        except Exception as e:
            print(f"Warning: Could not apply {hot_pixel_control}: {e}")
    else:
        print(f"Warning: {hot_pixel_control} not available on this camera")

    # Return True if at least one control was applied successfully
    if applied_count > 0:
        print(f"ISP: {applied_count} control(s) applied successfully")
        return True
    else:
        print("Warning: No ISP controls could be applied")
        return False


def get_tuning_path(camera_model=None):
    """
    Get the path to the tuning file for a camera model.

    Args:
        camera_model (str, optional): Camera model name. If None, auto-detects.

    Returns:
        Path: Path to tuning file, or None if not found

    This is useful for passing to Picamera2 constructor's tuning parameter.

    Example:
        >>> tuning_path = get_tuning_path("imx708")
        >>> if tuning_path:
        ...     picam2 = Picamera2(tuning=Picamera2.load_tuning_file(str(tuning_path)))
    """
    if not camera_model:
        camera_model = get_camera_model()

    # Try model-specific tuning file first
    tuning_file = TUNING_DIR / f"{camera_model}.json"

    if not tuning_file.exists():
        # Try fallback to default tuning file
        tuning_file = ISP_DEFAULT_TUNING_FILE

    if tuning_file.exists():
        return tuning_file

    return None

"""
Camera ISP Tuning File Loader

Loads and applies Picamera2 tuning files for ISP features:
- Lens shading correction (vignetting correction)
- Defect pixel correction (stuck/dead pixel correction)
- Chromatic aberration correction (color fringing correction)

Tuning files are JSON-based configuration files that control the Image Signal
Processor (ISP) pipeline. They must be loaded when the camera is created,
before configuration.
"""

import json
from pathlib import Path

# Tuning directory relative to this file: webui/backend/../../5.x/tuning
TUNING_DIR = Path(__file__).parent.parent.parent / '5.x' / 'tuning'


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
            model = camera_info[0].get('Model', 'unknown')
            print(f"Detected camera model: {model}")
            return model
    except Exception as e:
        print(f"Warning: Could not detect camera model: {e}")

    return 'unknown'


def load_tuning_file(camera_model=None):
    """
    Load tuning file for camera model.

    Args:
        camera_model (str, optional): Camera model name. If None, auto-detects.

    Returns:
        dict: Parsed tuning file JSON, or None if no tuning file found

    Lookup order:
        1. {camera_model}.json (e.g., imx708.json)
        2. default.json (fallback)

    Example:
        >>> tuning = load_tuning_file('imx708')
        >>> if tuning:
        ...     print(f"Loaded tuning version {tuning['version']}")
    """
    if not camera_model:
        camera_model = get_camera_model()

    # Try model-specific tuning file first
    tuning_file = TUNING_DIR / f"{camera_model}.json"

    if not tuning_file.exists():
        # Try fallback to default
        tuning_file = TUNING_DIR / "default.json"
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
        bool: True if controls were applied successfully, False otherwise

    Note:
        Control names used here are based on libcamera control documentation:
        - LensShadingMapMode: 0=Off, 1=On
        - HotPixelMode: 0=Off, 1=Fast, 2=HighQuality (we use Fast for performance)

        Chromatic aberration correction is typically configured in the tuning file
        and cannot be toggled at runtime.

    Important:
        This must be called AFTER camera.start() as controls only work on
        a running camera instance.
    """
    controls = {}

    # Lens shading correction (vignetting fix)
    # Mode 0 = Off, Mode 1 = On
    if lens_shading:
        controls['LensShadingMapMode'] = 1
        print("ISP: Lens shading correction enabled")
    else:
        controls['LensShadingMapMode'] = 0
        print("ISP: Lens shading correction disabled")

    # Defect pixel correction (hot/dead pixel fix)
    # Mode 0 = Off, Mode 1 = Fast, Mode 2 = HighQuality
    # We use Fast (1) for better performance
    if defect_correction:
        controls['HotPixelMode'] = 1
        print("ISP: Defect pixel correction enabled (Fast mode)")
    else:
        controls['HotPixelMode'] = 0
        print("ISP: Defect pixel correction disabled")

    try:
        camera.set_controls(controls)
        print(f"ISP controls applied: {controls}")
        return True
    except Exception as e:
        print(f"Error applying ISP controls: {e}")
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
        >>> tuning_path = get_tuning_path('imx708')
        >>> if tuning_path:
        ...     picam2 = Picamera2(tuning=Picamera2.load_tuning_file(str(tuning_path)))
    """
    if not camera_model:
        camera_model = get_camera_model()

    # Try model-specific tuning file first
    tuning_file = TUNING_DIR / f"{camera_model}.json"

    if not tuning_file.exists():
        # Try fallback to default
        tuning_file = TUNING_DIR / "default.json"

    if tuning_file.exists():
        return tuning_file

    return None

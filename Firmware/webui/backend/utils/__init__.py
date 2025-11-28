"""
Mothbox Web UI - Utils Package

This package contains utility modules for the Mothbox web backend.
It re-exports all utilities from the parent utils.py module to maintain
backward compatibility with existing imports.
"""

import importlib.util
import sys
from pathlib import Path

# Setup paths once at module load
# __file__ is .../webui/backend/utils/__init__.py
_utils_package_dir = Path(__file__).parent
_backend_dir = _utils_package_dir.parent  # webui/backend/
_webui_dir = _backend_dir.parent  # webui/

# Add directories to path if not already present
for _dir in [_backend_dir, _webui_dir]:
    _dir_str = str(_dir)
    if _dir_str not in sys.path:
        sys.path.insert(0, _dir_str)

# Import from the utils.py module at the parent level
# Using importlib to avoid conflicts with this package
_utils_file = _backend_dir / "utils.py"
_spec = importlib.util.spec_from_file_location("_backend_utils", _utils_file)
_backend_utils = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_backend_utils)

# Re-export all public items from utils.py
sanitize_csv_value = _backend_utils.sanitize_csv_value
ALLOWED_CAMERA_SETTINGS = _backend_utils.ALLOWED_CAMERA_SETTINGS
ALLOWED_WEBUI_SETTINGS = _backend_utils.ALLOWED_WEBUI_SETTINGS
ALLOWED_LIVEVIEW_SETTINGS = _backend_utils.ALLOWED_LIVEVIEW_SETTINGS
create_backup = _backend_utils.create_backup
validate_path_within_directory = _backend_utils.validate_path_within_directory
check_disk_space = _backend_utils.check_disk_space
get_last_calibration_time = _backend_utils.get_last_calibration_time

# Re-export private validation functions (used by tests)
_validate_int_enum = _backend_utils._validate_int_enum
_validate_exposure_time = _backend_utils._validate_exposure_time
_validate_noise_reduction_mode = _backend_utils._validate_noise_reduction_mode

# Import GPS coordinate utilities from webui.shared
from webui.shared.gps_coordinates import (
    decimal_to_dms,
    dms_to_decimal,
    format_coordinate_display,
    validate_coordinate,
)

__all__ = [
    # From parent utils.py
    "sanitize_csv_value",
    "ALLOWED_CAMERA_SETTINGS",
    "ALLOWED_WEBUI_SETTINGS",
    "ALLOWED_LIVEVIEW_SETTINGS",
    "create_backup",
    "validate_path_within_directory",
    "check_disk_space",
    "get_last_calibration_time",
    # From this package
    "decimal_to_dms",
    "dms_to_decimal",
    "format_coordinate_display",
    "validate_coordinate",
]

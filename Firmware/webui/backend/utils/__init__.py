"""
Mothbox Web UI - Utils Package

This package contains utility modules for the Mothbox web backend.
It re-exports all utilities from the parent utils.py module to maintain
backward compatibility with existing imports.
"""

# Re-export all utilities from the parent utils.py module
# This is needed because when Python imports 'from utils import X',
# it finds this package (utils/) instead of the utils.py file.
import sys
from pathlib import Path

# Add parent directory to path to import from utils.py
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Import from the utils.py module at the parent level
# Using importlib to avoid conflicts
import importlib.util

utils_file = parent_dir / "utils.py"
spec = importlib.util.spec_from_file_location("_backend_utils", utils_file)
_backend_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_backend_utils)

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

# Also export items from webui.shared (for backward compatibility)
# Use relative import to parent package since webui may not be in sys.path
import sys
from pathlib import Path

# Add webui directory to path if not already present
# __file__ is .../webui/backend/utils/__init__.py
# We need .../webui
webui_dir = Path(__file__).parent.parent.parent
if str(webui_dir) not in sys.path:
    sys.path.insert(0, str(webui_dir))

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

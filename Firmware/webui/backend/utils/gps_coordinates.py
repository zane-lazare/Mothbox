"""
Backward compatibility stub for GPS coordinate utilities.

This module has been moved to webui/lib/gps_coordinates.py to properly
organize webui-shared utilities. This stub re-exports all functions to
maintain backward compatibility with existing code.

For new code, prefer importing from:
    from webui.lib.gps_coordinates import decimal_to_dms, dms_to_decimal

For backward compatibility, this still works:
    from webui.backend.utils.gps_coordinates import decimal_to_dms, dms_to_decimal
"""

import sys
from pathlib import Path

# Add parent webui directory to path to import from webui.lib
webui_dir = Path(__file__).parent.parent.parent
if str(webui_dir) not in sys.path:
    sys.path.insert(0, str(webui_dir))

# Re-export all functions from new location
from webui.lib.gps_coordinates import (  # noqa: E402, F401
    decimal_to_dms,
    dms_to_decimal,
    format_coordinate_display,
    validate_coordinate,
)

__all__ = [
    "decimal_to_dms",
    "dms_to_decimal",
    "format_coordinate_display",
    "validate_coordinate",
]

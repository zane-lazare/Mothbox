"""
Mothbox Web UI - Shared Library Package

This package contains shared utilities used across all webui components
(backend, frontend integration, etc.).
"""

# Export GPS coordinate utilities for easy import
from .gps_coordinates import (
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

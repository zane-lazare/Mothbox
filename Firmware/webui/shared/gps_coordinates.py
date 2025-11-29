"""GPS coordinate conversion and formatting utilities.

This module provides utilities for converting between decimal degrees and
DMS (Degrees, Minutes, Seconds) format, validating GPS coordinates, and
formatting coordinates for display.

These utilities are designed for web UI display and API responses, extracting
core coordinate math from the EXIF-specific implementation in webui/backend/lib/gps_exif_lib.py.
"""

import math
from typing import Literal

__all__ = [
    "decimal_to_dms",
    "dms_to_decimal",
    "validate_coordinate",
    "format_coordinate_display",
]


def validate_coordinate(decimal: float, is_latitude: bool) -> bool:
    """Validate a GPS coordinate.

    Args:
        decimal: Decimal degrees to validate
        is_latitude: True if latitude, False if longitude

    Returns:
        True if coordinate is valid, False otherwise

    Example:
        >>> validate_coordinate(37.7749, is_latitude=True)
        True
        >>> validate_coordinate(91.0, is_latitude=True)
        False
        >>> validate_coordinate(-122.4194, is_latitude=False)
        True
    """
    # Check for None
    if decimal is None:
        return False

    # Check for NaN
    if math.isnan(decimal):
        return False

    # Check for infinity
    if math.isinf(decimal):
        return False

    # Check range
    if is_latitude:
        return -90 <= decimal <= 90
    else:
        return -180 <= decimal <= 180


def decimal_to_dms(decimal: float, is_latitude: bool) -> tuple[int, int, float, str]:
    """Convert decimal degrees to DMS format.

    Args:
        decimal: Decimal degrees (e.g., 37.7749 or -122.4194)
        is_latitude: True if latitude, False if longitude

    Returns:
        Tuple of (degrees, minutes, seconds, reference)
        - degrees: Integer degrees (0-180)
        - minutes: Integer minutes (0-59)
        - seconds: Float seconds (0.0-59.999...)
        - reference: 'N', 'S', 'E', or 'W'

    Raises:
        ValueError: If coordinate is invalid (out of range, NaN, infinity)

    Example:
        >>> decimal_to_dms(37.7749, is_latitude=True)
        (37, 46, 29.64, 'N')
        >>> decimal_to_dms(-122.4194, is_latitude=False)
        (122, 25, 9.84, 'W')
    """
    # Validate input coordinate
    if decimal is None:
        raise ValueError("Coordinate cannot be None")
    if math.isnan(decimal):
        raise ValueError("Coordinate cannot be NaN")
    if math.isinf(decimal):
        raise ValueError("Coordinate cannot be infinity")

    # Validate coordinate range
    if is_latitude:
        if not (-90 <= decimal <= 90):
            raise ValueError(f"Invalid latitude: {decimal} (must be in range [-90, 90])")
    else:
        if not (-180 <= decimal <= 180):
            raise ValueError(f"Invalid longitude: {decimal} (must be in range [-180, 180])")

    # Determine reference (N/S for latitude, E/W for longitude)
    if is_latitude:  # noqa: SIM108  # More readable than nested ternary
        ref = "N" if decimal >= 0 else "S"
    else:
        ref = "E" if decimal >= 0 else "W"

    # Use absolute value for conversion (sign is captured in ref)
    decimal_abs = abs(decimal)

    # Extract degrees (integer part)
    degrees = int(decimal_abs)

    # Extract minutes (fractional part * 60)
    minutes_decimal = (decimal_abs - degrees) * 60
    minutes = int(minutes_decimal)

    # Extract seconds (remaining fractional minutes * 60)
    seconds_decimal = (minutes_decimal - minutes) * 60

    # Round to 2 decimal places
    seconds = round(seconds_decimal, 2)

    # Handle seconds overflow (rounding 59.995 -> 60.00)
    if seconds >= 60.0:
        minutes += 1
        seconds = 0.0

    # Handle minutes overflow (59 minutes + 1 -> 60 minutes)
    if minutes >= 60:
        degrees += 1
        minutes = 0

    return (degrees, minutes, seconds, ref)


def dms_to_decimal(degrees: int, minutes: int, seconds: float, ref: str) -> float:
    """Convert DMS format to decimal degrees.

    Args:
        degrees: Degrees (0-180)
        minutes: Minutes (0-59)
        seconds: Seconds (0.0-59.999...)
        ref: Reference direction ('N', 'S', 'E', or 'W')

    Returns:
        Decimal degrees (positive for N/E, negative for S/W)

    Raises:
        ValueError: If ref is invalid

    Example:
        >>> dms_to_decimal(37, 46, 29.64, "N")
        37.7749
        >>> dms_to_decimal(122, 25, 9.84, "W")
        -122.4194
    """
    # Validate reference
    if ref not in ["N", "S", "E", "W"]:
        raise ValueError(f"Invalid reference: {ref} (must be 'N', 'S', 'E', or 'W')")

    # Convert to decimal
    decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)

    # Apply sign based on reference
    if ref in ["S", "W"]:
        decimal = -decimal

    return decimal


def format_coordinate_display(
    decimal: float, is_latitude: bool, format: Literal["dms", "decimal", "short"] = "dms"
) -> str:
    """Format a coordinate for display.

    Args:
        decimal: Decimal degrees
        is_latitude: True if latitude, False if longitude
        format: Display format:
            - 'dms': Degrees, minutes, seconds with symbols (e.g., "37°46'29.64\"N")
            - 'decimal': Decimal degrees with direction (e.g., "37.774900°N")
            - 'short': Short decimal with direction (e.g., "37.77°N")

    Returns:
        Formatted coordinate string

    Raises:
        ValueError: If coordinate is invalid

    Example:
        >>> format_coordinate_display(37.7749, is_latitude=True, format="dms")
        "37°46'29.64\\"N"
        >>> format_coordinate_display(37.7749, is_latitude=True, format="decimal")
        '37.774900°N'
        >>> format_coordinate_display(37.7749, is_latitude=True, format="short")
        '37.77°N'
    """
    if format == "dms":
        deg, min, sec, ref = decimal_to_dms(decimal, is_latitude)
        return f"{deg}°{min}'{sec:.2f}\"{ref}"
    elif format == "decimal":
        # Determine reference
        if is_latitude:  # noqa: SIM108  # More readable than nested ternary
            ref = "N" if decimal >= 0 else "S"
        else:
            ref = "E" if decimal >= 0 else "W"
        return f"{abs(decimal):.6f}°{ref}"
    elif format == "short":
        # Determine reference
        if is_latitude:  # noqa: SIM108  # More readable than nested ternary
            ref = "N" if decimal >= 0 else "S"
        else:
            ref = "E" if decimal >= 0 else "W"
        return f"{abs(decimal):.2f}°{ref}"
    else:
        raise ValueError(f"Invalid format: {format} (must be 'dms', 'decimal', or 'short')")

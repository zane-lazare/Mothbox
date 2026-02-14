"""
Date extraction utilities for Mothbox photo filenames.

Provides functions to extract dates from Mothbox photo filenames and validate
ISO 8601 date strings for export filtering.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

# Mothbox filename pattern - supports various prefixes (HDR, ManFocus, custom)
# Pattern: name_YYYY_MM_DD__HH_MM_SS[_suffix].ext
# Matches: moth_2024_01_15__10_30_00.jpg
#          moth_2024_01_15__10_30_00_HDR0.jpg
#          ManFocus_moth_2024_01_15__10_30_00_FB0.jpg
MOTHBOX_FILENAME_PATTERN = re.compile(
    r"(?P<name>.+?)_(?P<year>\d{4})_(?P<month>\d{2})_(?P<day>\d{2})__"
    r"(?P<hour>\d{2})_(?P<minute>\d{2})_(?P<second>\d{2})"
)


def extract_date_from_filename(photo_path: Path | str) -> date | None:
    """
    Extract date from Mothbox photo filename.

    Primary method for date filtering. Uses filename timestamp which is
    more reliable than file mtime (doesn't change on copy/move).

    Args:
        photo_path: Path to photo file

    Returns:
        date object if pattern matches, None otherwise

    Examples:
        >>> extract_date_from_filename("moth_2024_01_15__10_30_00.jpg")
        datetime.date(2024, 1, 15)
        >>> extract_date_from_filename("ManFocus_moth_2024_01_15__10_30_00_FB0.jpg")
        datetime.date(2024, 1, 15)
        >>> extract_date_from_filename("unknown.jpg")
        None
    """
    if isinstance(photo_path, str):
        photo_path = Path(photo_path)

    filename = photo_path.name
    match = MOTHBOX_FILENAME_PATTERN.search(filename)

    if not match:
        return None

    try:
        year = int(match.group("year"))
        month = int(match.group("month"))
        day = int(match.group("day"))
        return date(year, month, day)
    except (ValueError, TypeError):
        return None


def get_photo_date(photo_path: Path) -> date | None:
    """
    Get photo date with fallback to file mtime.

    Priority:
    1. Filename timestamp (preferred - doesn't change on file copy)
    2. File modification time (fallback)

    Args:
        photo_path: Path to photo file

    Returns:
        date object, or None if date cannot be determined
    """
    # Try filename first
    filename_date = extract_date_from_filename(photo_path)
    if filename_date:
        return filename_date

    # Fallback to mtime
    try:
        mtime = photo_path.stat().st_mtime
        return datetime.fromtimestamp(mtime).date()
    except (OSError, ValueError):
        return None


def validate_date_string(date_str: str) -> tuple[bool, str | None]:
    """
    Validate ISO 8601 date string format (YYYY-MM-DD).

    Args:
        date_str: Date string to validate

    Returns:
        Tuple of (is_valid, error_message)

    Examples:
        >>> validate_date_string("2024-01-15")
        (True, None)
        >>> validate_date_string("2024-13-01")
        (False, "Invalid date: month must be in 1..12")
        >>> validate_date_string("not-a-date")
        (False, "Invalid date format. Use ISO 8601: YYYY-MM-DD")
    """
    if not isinstance(date_str, str):
        return False, "Date must be a string"

    try:
        date.fromisoformat(date_str)
        return True, None
    except ValueError:
        # Provide helpful error message
        if len(date_str) != 10 or date_str.count("-") != 2:
            return False, "Invalid date format. Use ISO 8601: YYYY-MM-DD"
        return False, "Invalid date value"


def parse_date_filter(date_str: str | None) -> date | None:
    """
    Parse a date filter string to date object.

    Args:
        date_str: ISO 8601 date string or None

    Returns:
        date object or None if input is None/empty

    Raises:
        ValueError: If date string is invalid
    """
    if not date_str:
        return None

    is_valid, error = validate_date_string(date_str)
    if not is_valid:
        raise ValueError(error)

    return date.fromisoformat(date_str)

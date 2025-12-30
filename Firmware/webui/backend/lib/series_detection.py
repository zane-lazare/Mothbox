"""
Series Detection Library for Mothbox Photo Gallery

Detects and groups HDR and Focus Bracket photo series based on filename patterns.
Supports cross-directory series detection (photos spanning date folders).

Naming Patterns (from TakePhoto.py scripts):
- HDR: {name}_{timestamp}_HDR{index}.jpg (e.g., moth_2024_01_15__10_00_00_HDR0.jpg)
- Focus Bracket: ManFocus_{name}_{timestamp}_FB{index}.jpg

Usage:
    from webui.backend.lib.series_detection import (
        detect_series_type,
        get_series_id,
        group_photos_into_series,
    )

    # Detect single photo
    info = detect_series_type("moth_2024_01_15__10_00_00_HDR0.jpg")
    if info:
        print(f"Type: {info.series_type}, Index: {info.index}")

    # Group photos by series
    groups = group_photos_into_series(photo_paths)
    for series_id, photos in groups.items():
        print(f"Series {series_id}: {len(photos)} photos")
"""

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class SeriesType(str, Enum):
    """Enumeration of supported series types."""

    HDR = "hdr"
    FOCUS_BRACKET = "focus_bracket"


@dataclass(frozen=True)
class SeriesInfo:
    """Information about a photo's series membership.

    Attributes:
        series_type: Type of series ("hdr" or "focus_bracket")
        base_name: Common prefix for grouping (timestamp-based, excludes index suffix)
        index: Zero-based position in series (0, 1, 2...)
    """

    series_type: str
    base_name: str
    index: int


# ============================================================================
# Regex Patterns (case-insensitive)
# ============================================================================

# HDR Pattern: {name}_{YYYY_MM_DD__HH_MM_SS}_HDR{index}.{ext}
# Matches: moth_2024_01_15__10_00_00_HDR0.jpg, mb12345_2024_01_15__10_00_00_HDR1.png
# Groups: (1) base_name, (2) index, (3) extension
HDR_PATTERN = re.compile(
    r"^(.+_\d{4}_\d{2}_\d{2}__\d{2}_\d{2}_\d{2})_[Hh][Dd][Rr](\d+)\.(jpg|jpeg|png|bmp)$",
    re.IGNORECASE,
)

# Focus Bracket Pattern: ManFocus_{name}_{YYYY_MM_DD__HH_MM_SS}[_{microseconds}]_FB{index}.{ext}
# Matches: ManFocus_moth_2024_01_15__11_00_00_000000_FB0.jpg
# Also matches: ManFocus_moth_2024_01_15__11_00_00_FB0.jpg (without microseconds)
# Groups: (1) base_name (including ManFocus prefix), (2) index, (3) extension
FB_PATTERN = re.compile(
    r"^(ManFocus_.+_\d{4}_\d{2}_\d{2}__\d{2}_\d{2}_\d{2}(?:_\d+)?)_[Ff][Bb](\d+)\.(jpg|jpeg|png|bmp)$",
    re.IGNORECASE,
)

# 16MP ManFocus with HDR suffix (from TakePhoto16mp.py)
# Pattern: 16MPManFocus_{name}_{timestamp}_HDR{index}.jpg
MP16_HDR_PATTERN = re.compile(
    r"^(16MPManFocus_.+_\d{4}_\d{2}_\d{2}__\d{2}_\d{2}_\d{2})_[Hh][Dd][Rr](\d+)\.(jpg|jpeg|png|bmp)$",
    re.IGNORECASE,
)


def _extract_filename(path: str | Path | None) -> str | None:
    """Extract filename from path (handles str, Path, or None).

    Args:
        path: File path as string, Path object, or None

    Returns:
        Filename string or None if invalid input
    """
    if path is None:
        return None

    if isinstance(path, Path):
        return path.name

    if isinstance(path, str):
        # Handle both full paths and bare filenames
        if "/" in path or "\\" in path:
            return Path(path).name
        return path

    return None


def detect_series_type(filename: str | Path | None) -> SeriesInfo | None:
    """Detect if a photo is part of an HDR or Focus Bracket series.

    Analyzes the filename pattern to identify series membership.

    Args:
        filename: Photo filename, full path, or Path object

    Returns:
        SeriesInfo with type, base_name, and index if part of series, None otherwise

    Example:
        >>> detect_series_type("moth_2024_01_15__10_00_00_HDR0.jpg")
        SeriesInfo(series_type='hdr', base_name='moth_2024_01_15__10_00_00', index=0)

        >>> detect_series_type("regular_photo.jpg")
        None
    """
    name = _extract_filename(filename)
    if not name:
        return None

    # Try 16MP HDR pattern first (more specific)
    match = MP16_HDR_PATTERN.match(name)
    if match:
        return SeriesInfo(
            series_type=SeriesType.HDR.value, base_name=match.group(1), index=int(match.group(2))
        )

    # Try standard HDR pattern
    match = HDR_PATTERN.match(name)
    if match:
        return SeriesInfo(
            series_type=SeriesType.HDR.value, base_name=match.group(1), index=int(match.group(2))
        )

    # Try Focus Bracket pattern
    match = FB_PATTERN.match(name)
    if match:
        return SeriesInfo(
            series_type=SeriesType.FOCUS_BRACKET.value,
            base_name=match.group(1),
            index=int(match.group(2)),
        )

    return None


def get_series_id(filename: str | Path | None) -> str | None:
    """Get a unique series identifier for grouping photos.

    Photos from the same series will return the same ID, enabling cross-directory
    grouping (e.g., if HDR capture spans midnight across date folders).

    Args:
        filename: Photo filename, full path, or Path object

    Returns:
        Series ID string (format: "{type}_{base_name}") or None if not in series

    Example:
        >>> get_series_id("moth_2024_01_15__10_00_00_HDR0.jpg")
        'hdr_moth_2024_01_15__10_00_00'

        >>> get_series_id("moth_2024_01_15__10_00_00_HDR1.jpg")
        'hdr_moth_2024_01_15__10_00_00'  # Same ID for same series

        >>> get_series_id("regular_photo.jpg")
        None
    """
    info = detect_series_type(filename)
    if info is None:
        return None

    return f"{info.series_type}_{info.base_name}"


def group_photos_into_series(photo_paths: list[str | Path]) -> dict[str, list[Path]]:
    """Group photos by their series membership.

    Analyzes filenames and groups photos that belong to the same HDR or
    Focus Bracket series. Photos not in any series are excluded from results.
    Supports cross-directory grouping (series can span date folders).

    Args:
        photo_paths: List of photo paths (str or Path objects)

    Returns:
        Dictionary mapping series_id to sorted list of photo Paths.
        Photos within each series are sorted by index (HDR0, HDR1, HDR2...).
        Photos not in any series are excluded.

    Example:
        >>> paths = [
        ...     Path("moth_2024_01_15__10_00_00_HDR0.jpg"),
        ...     Path("moth_2024_01_15__10_00_00_HDR1.jpg"),
        ...     Path("regular_photo.jpg"),  # Excluded
        ... ]
        >>> groups = group_photos_into_series(paths)
        >>> len(groups)
        1
        >>> list(groups.keys())
        ['hdr_moth_2024_01_15__10_00_00']
    """
    if not photo_paths:
        return {}

    # Group by series_id
    groups: dict[str, list[tuple[int, Path]]] = {}

    for path in photo_paths:
        # Normalize to Path
        if isinstance(path, str):
            path = Path(path)

        info = detect_series_type(path)
        if info is None:
            continue  # Skip non-series photos

        series_id = f"{info.series_type}_{info.base_name}"

        if series_id not in groups:
            groups[series_id] = []

        groups[series_id].append((info.index, path))

    # Sort each series by index and extract paths
    result: dict[str, list[Path]] = {}
    for series_id, indexed_photos in groups.items():
        sorted_photos = sorted(indexed_photos, key=lambda x: x[0])
        result[series_id] = [photo for _, photo in sorted_photos]

    return result


# ============================================================================
# Module exports
# ============================================================================

__all__ = [
    "SeriesType",
    "SeriesInfo",
    "detect_series_type",
    "get_series_id",
    "group_photos_into_series",
    "HDR_PATTERN",
    "FB_PATTERN",
]

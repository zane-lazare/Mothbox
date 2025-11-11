"""GPS EXIF embedding library for Mothbox photos.

This module provides functions to read GPS data from controls.txt
and embed it into JPEG EXIF metadata without modifying the original
photo capture workflow.

Architecture:
- Post-processing approach: Photos captured first, GPS added later
- Idempotent: Safe to run multiple times on same photo
- Non-invasive: TakePhoto.py remains unchanged
- Graceful degradation: Works without GPS (no-op)

Functions:
- get_gps_data_from_controls(): Read GPS data from controls.txt
- decimal_to_dms(): Convert decimal degrees to EXIF DMS format
- build_gps_ifd(): Build piexif GPS IFD dictionary
- embed_gps_exif(): Embed GPS EXIF into JPEG photo
- verify_gps_exif(): Read and verify GPS EXIF from photo
- is_already_tagged(): Check if photo has GPS EXIF

Related:
- Issue #98: GPS EXIF Embedding
- Spec: webui/docs/dev/issues/ISSUE_98_GPS_EXIF_IMPLEMENTATION_SPEC.md
"""

from pathlib import Path
from typing import Optional, Dict, Tuple, Any

# Import path resolution from mothbox_paths (reuse existing infrastructure)
from mothbox_paths import get_control_values, CONTROLS_FILE


def get_gps_data_from_controls(controls_file: Optional[Path] = None) -> Dict[str, Any]:
    """
    Read current GPS data from controls.txt.

    Uses the existing get_control_values() parser from mothbox_paths.py
    to read GPS fields written by GPS.py. Handles missing fields gracefully
    with sensible defaults.

    GPS fields in controls.txt (written by GPS.py):
        - gpstime: Unix timestamp from GPS (int)
        - lat: Decimal latitude (float or 'n/a')
        - lon: Decimal longitude (float or 'n/a')
        - gps_altitude: Altitude in meters (float, optional)
        - gps_fix_mode: 0=no fix, 2=2D, 3=3D (int)
        - gps_satellites_used: Number of satellites in fix (int)
        - gps_hdop: Horizontal dilution of precision (float)
        - gps_pdop: Position dilution of precision (float)

    Returns:
        dict: GPS data dictionary with keys:
            - latitude (float or None): Decimal latitude
            - longitude (float or None): Decimal longitude
            - gpstime (int): Unix timestamp from GPS (0 if missing)
            - altitude (float or None): Altitude in meters (if available)
            - fix_mode (int): 0=no fix, 2=2D, 3=3D
            - satellites_used (int): Number of satellites in fix
            - hdop (float): Horizontal dilution of precision
            - pdop (float): Position dilution of precision
            - has_fix (bool): Whether GPS has valid position

    Example:
        >>> gps_data = get_gps_data_from_controls()
        >>> if gps_data['has_fix']:
        ...     print(f"Position: {gps_data['latitude']}, {gps_data['longitude']}")
        Position: 37.7749, -122.4194

    Implementation Notes:
        - Reuses get_control_values() for consistency with existing code
        - Whitespace is stripped automatically by get_control_values()
        - Missing fields use sensible defaults (0, None, 99.99 for poor DOP)
        - 'n/a' string values are converted to None
        - Invalid numeric values are converted to None/defaults
    """
    # Read all control values from controls.txt
    # This function already handles missing file, comments, whitespace
    # Allow override for testing (dependency injection pattern)
    if controls_file is None:
        controls_file = CONTROLS_FILE
    controls = get_control_values(controls_file)

    # Helper to safely parse float or return None
    def safe_float(value: str, default: Optional[float] = None) -> Optional[float]:
        """Parse float from string, handling 'n/a' and invalid values."""
        if not value or value == 'n/a':
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    # Helper to safely parse int or return default
    def safe_int(value: str, default: int = 0) -> int:
        """Parse int from string, handling 'n/a' and invalid values."""
        if not value or value == 'n/a':
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    # Parse GPS coordinates (None if missing or 'n/a')
    latitude = safe_float(controls.get('lat', 'n/a'))
    longitude = safe_float(controls.get('lon', 'n/a'))

    # Parse GPS timestamp (0 if missing)
    gpstime = safe_int(controls.get('gpstime', '0'), default=0)

    # Parse altitude (None if missing - only available with 3D fix)
    altitude = safe_float(controls.get('gps_altitude'))

    # Parse fix quality metrics
    fix_mode = safe_int(controls.get('gps_fix_mode', '0'), default=0)
    satellites_used = safe_int(controls.get('gps_satellites_used', '0'), default=0)

    # Parse dilution of precision (99.99 = poor/no fix)
    hdop = safe_float(controls.get('gps_hdop', '99.99'), default=99.99)
    pdop = safe_float(controls.get('gps_pdop', '99.99'), default=99.99)

    # Determine if GPS has valid fix
    # Valid fix requires: non-None coordinates AND fix_mode > 0
    has_fix = (latitude is not None and
               longitude is not None and
               fix_mode > 0)

    # Return structured GPS data
    return {
        'latitude': latitude,
        'longitude': longitude,
        'gpstime': gpstime,
        'altitude': altitude,
        'fix_mode': fix_mode,
        'satellites_used': satellites_used,
        'hdop': hdop,
        'pdop': pdop,
        'has_fix': has_fix
    }


def decimal_to_dms(decimal: float, is_latitude: bool) -> Tuple[Tuple, str]:
    """
    Convert decimal degrees to EXIF GPS format (degrees, minutes, seconds).

    EXIF GPS coordinates are stored in DMS (Degrees, Minutes, Seconds) format
    with rational numbers for precision. This function converts decimal degrees
    to the EXIF standard format.

    Args:
        decimal: Decimal degrees (e.g., 37.7749 or -122.4194)
        is_latitude: True if this is latitude, False if longitude

    Returns:
        tuple: (dms_tuple, ref_string) where:
            - dms_tuple: ((degrees, 1), (minutes, 1), (seconds, 100))
            - ref_string: 'N'/'S' for latitude, 'E'/'W' for longitude

    Example:
        >>> dms, ref = decimal_to_dms(37.7749, is_latitude=True)
        >>> print(dms, ref)
        ((37, 1), (46, 1), (2964, 100)) 'N'

    Note:
        Seconds are multiplied by 100 and stored as rational (seconds*100, 100)
        to preserve precision per EXIF standard.

    EXIF GPS Format:
        - Degrees: (degrees, 1) - whole degrees
        - Minutes: (minutes, 1) - whole minutes
        - Seconds: (seconds*100, 100) - seconds with 2 decimal places
    """
    # TODO: Implement for Day 2
    pass


def build_gps_ifd(gps_data: Dict[str, Any]) -> Dict:
    """
    Build piexif GPS IFD dictionary from GPS data.

    Creates a GPS Image File Directory (IFD) compatible with EXIF 2.3 standard
    for embedding in JPEG files. Includes all available GPS metadata.

    Args:
        gps_data: GPS data dictionary from get_gps_data_from_controls()

    Returns:
        dict: piexif GPS IFD dictionary ready for embedding

    EXIF GPS tags included:
        - GPSVersionID: (2, 3, 0, 0) - EXIF 2.3 standard
        - GPSLatitude: DMS tuple
        - GPSLatitudeRef: 'N' or 'S'
        - GPSLongitude: DMS tuple
        - GPSLongitudeRef: 'E' or 'W'
        - GPSAltitude: (altitude_meters * 100, 100) if available
        - GPSAltitudeRef: 0 (above sea level) or 1 (below)
        - GPSTimeStamp: (hour, minute, second) - UTC time
        - GPSDateStamp: 'YYYY:MM:DD' - UTC date
        - GPSDOP: (hdop * 100, 100) - Dilution of precision
        - GPSSatellites: f"{satellites_used}" - Number of satellites

    Example:
        >>> gps_data = get_gps_data_from_controls()
        >>> gps_ifd = build_gps_ifd(gps_data)
        >>> print(gps_ifd[piexif.GPSIFD.GPSLatitudeRef])
        'N'
    """
    # TODO: Implement for Day 2
    pass


def embed_gps_exif(
    photo_path: Path,
    gps_data: Optional[Dict[str, Any]] = None,
    backup: bool = False,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Embed GPS EXIF data into a JPEG photo in-place.

    This function:
    1. Reads existing EXIF from photo
    2. Builds GPS IFD from current GPS data (or provided data)
    3. Merges GPS IFD with existing EXIF
    4. Writes EXIF back to photo atomically
    5. Verifies integrity after write

    Args:
        photo_path: Path to JPEG photo file
        gps_data: GPS data dict (or None to read from controls.txt)
        backup: If True, create .bak file before modifying
        dry_run: If True, validate but don't write changes

    Returns:
        dict: Operation result with keys:
            - success (bool): True if GPS EXIF was embedded
            - skipped (bool): True if no GPS fix available
            - error (str or None): Error message if failed
            - gps_embedded (bool): True if GPS tags were written
            - original_had_gps (bool): True if photo already had GPS EXIF
            - backup_path (Path or None): Path to backup file if created

    Raises:
        FileNotFoundError: If photo_path doesn't exist
        ValueError: If photo_path is not a JPEG file
        PermissionError: If unable to write to photo

    Example:
        >>> result = embed_gps_exif(Path('/photos/mothbox_2025_01_15__12_30_00.jpg'))
        >>> if result['success']:
        ...     print("GPS EXIF embedded successfully")
        >>> elif result['skipped']:
        ...     print("No GPS fix available, skipped")

    Security:
        - Uses atomic write (write to temp, then rename)
        - Validates JPEG integrity after write
        - Original file preserved if backup=True
    """
    # TODO: Implement for Day 3
    pass


def verify_gps_exif(photo_path: Path) -> Dict[str, Any]:
    """
    Read and verify GPS EXIF data from a photo.

    Extracts GPS EXIF tags from a JPEG photo and converts them to a
    human-readable format for verification and display.

    Args:
        photo_path: Path to JPEG photo file

    Returns:
        dict: GPS EXIF data with keys:
            - has_gps (bool): True if GPS EXIF tags present
            - latitude (float or None): Extracted latitude
            - longitude (float or None): Extracted longitude
            - timestamp (str or None): GPS timestamp
            - altitude (float or None): Altitude in meters
            - satellites (str or None): Number of satellites
            - hdop (float or None): Horizontal DOP
            - raw_gps_ifd (dict): Raw piexif GPS IFD

    Example:
        >>> info = verify_gps_exif(Path('/photos/mothbox_2025_01_15__12_30_00.jpg'))
        >>> if info['has_gps']:
        ...     print(f"Photo location: {info['latitude']}, {info['longitude']}")
    """
    # TODO: Implement for Day 3
    pass


def is_already_tagged(photo_path: Path) -> bool:
    """
    Check if photo already has GPS EXIF data.

    Simple check for idempotency - avoids re-processing photos that
    already have GPS EXIF tags.

    Args:
        photo_path: Path to JPEG photo file

    Returns:
        bool: True if photo has GPSLatitude and GPSLongitude tags

    Note:
        Used for idempotency - avoids re-processing tagged photos.

    Example:
        >>> if not is_already_tagged(photo):
        ...     embed_gps_exif(photo)
    """
    # TODO: Implement for Day 3
    pass

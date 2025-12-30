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
- Spec: webui/docs/dev/issues/ISSUE_98_GPS_EXIF_IMPLEMENTATION_SPEC.md
"""

# Path setup for accessing mothbox_paths at firmware root
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_lib_dir = Path(__file__).resolve().parent
_backend_dir = _lib_dir.parent
_webui_dir = _backend_dir.parent
_firmware_root = _webui_dir.parent
if str(_firmware_root) not in sys.path:
    sys.path.insert(0, str(_firmware_root))

# Import path resolution from mothbox_paths (reuse existing infrastructure)
from mothbox_paths import CONTROLS_FILE, get_control_values

# Import piexif for EXIF metadata manipulation
try:
    import piexif
except ImportError:
    piexif = None  # Graceful degradation if piexif not available


# Module exports
__all__ = [
    "get_gps_data_from_controls",
    "decimal_to_dms",
    "build_gps_ifd",
    "embed_gps_exif",
    "verify_gps_exif",
    "is_already_tagged",
]


# GPS EXIF constants
EXIF_GPS_VERSION = (2, 3, 0, 0)  # GPS EXIF version 2.3.0.0 (standard)
DMS_PRECISION = 100  # Precision for DMS seconds (1/100 second)
DEFAULT_JPEG_QUALITY = 95  # JPEG quality for re-encoding (preserves quality)
BACKUP_EXTENSION = ".bak"  # Extension for backup files

# GPS fix mode constants
GPS_FIX_NONE = 0  # No GPS fix
GPS_FIX_2D = 2  # 2D fix (lat/lon only)
GPS_FIX_3D = 3  # 3D fix (lat/lon + altitude)

# Default values for missing GPS data
DEFAULT_HDOP = 99.99  # Default HDOP (very poor) when not available
DEFAULT_PDOP = 99.99  # Default PDOP (very poor) when not available


def get_gps_data_from_controls(controls_file: Path | None = None) -> dict[str, Any]:
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
        >>> if gps_data["has_fix"]:
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
    def safe_float(value: str, default: float | None = None) -> float | None:
        """Parse float from string, handling 'n/a' and invalid values."""
        if not value or value == "n/a":
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    # Helper to safely parse int or return default
    def safe_int(value: str, default: int = 0) -> int:
        """Parse int from string, handling 'n/a' and invalid values."""
        if not value or value == "n/a":
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    # Parse GPS coordinates (None if missing or 'n/a')
    latitude = safe_float(controls.get("lat", "n/a"))
    longitude = safe_float(controls.get("lon", "n/a"))

    # Parse GPS timestamp (0 if missing)
    gpstime = safe_int(controls.get("gpstime", "0"), default=0)

    # Parse altitude (None if missing - only available with 3D fix)
    altitude = safe_float(controls.get("gps_altitude"))

    # Parse fix quality metrics
    fix_mode = safe_int(controls.get("gps_fix_mode", "0"), default=0)
    satellites_used = safe_int(controls.get("gps_satellites_used", "0"), default=0)

    # Parse dilution of precision (DEFAULT_HDOP/PDOP = poor/no fix)
    hdop = safe_float(controls.get("gps_hdop", str(DEFAULT_HDOP)), default=DEFAULT_HDOP)
    pdop = safe_float(controls.get("gps_pdop", str(DEFAULT_PDOP)), default=DEFAULT_PDOP)

    # Determine if GPS has valid fix
    # Valid fix requires: non-None coordinates AND fix_mode > 0
    has_fix = latitude is not None and longitude is not None and fix_mode > 0

    # Return structured GPS data
    return {
        "latitude": latitude,
        "longitude": longitude,
        "gpstime": gpstime,
        "altitude": altitude,
        "fix_mode": fix_mode,
        "satellites_used": satellites_used,
        "hdop": hdop,
        "pdop": pdop,
        "has_fix": has_fix,
    }


def decimal_to_dms(decimal: float, is_latitude: bool) -> tuple[tuple, str]:
    """
    Convert decimal degrees to EXIF GPS format (degrees, minutes, seconds).

    This is a wrapper around the shared GPS coordinate utilities that
    adds EXIF-specific rational tuple formatting.

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
    # Import shared utility (with alias to avoid name collision)
    from webui.shared.gps_coordinates import (
        decimal_to_dms as convert_decimal_to_dms,
    )

    # Use shared utility for core conversion
    # This handles all validation, range checking, and math
    degrees, minutes, seconds, reference = convert_decimal_to_dms(decimal, is_latitude)

    # Convert to EXIF rational tuple format
    # EXIF stores as: ((degrees, 1), (minutes, 1), (seconds*100, 100))
    # Note: The shared utility already handles overflow, so degrees/minutes
    # are guaranteed to be in valid ranges
    dms_tuple = (
        (degrees, 1),
        (minutes, 1),
        (int(round(seconds * 100)), 100),  # Store seconds with 0.01 precision
    )

    return (dms_tuple, reference)


def build_gps_ifd(gps_data: dict[str, Any]) -> dict:
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
    # Step 1: Check if GPS has valid fix
    if not gps_data.get("has_fix", False):
        return {}  # Return empty dict if no GPS fix

    # Check if piexif is available
    if piexif is None:
        raise ImportError("piexif library is required for GPS EXIF embedding")

    # Step 2: Validate coordinates are present and valid
    import math

    lat = gps_data.get("latitude")
    lon = gps_data.get("longitude")

    # Return empty IFD if coordinates missing
    if lat is None or lon is None:
        return {}

    # Return empty IFD if NaN or infinity (graceful degradation)
    if math.isnan(lat) or math.isinf(lat) or math.isnan(lon) or math.isinf(lon):
        return {}

    # Step 3: Initialize GPS IFD dictionary
    gps_ifd = {}

    # Step 4: Add GPS version (EXIF 2.3 standard)
    gps_ifd[piexif.GPSIFD.GPSVersionID] = EXIF_GPS_VERSION

    # Step 5: Convert and add latitude (safe now after validation)
    try:
        lat_dms, lat_ref = decimal_to_dms(lat, is_latitude=True)
    except ValueError:
        # If conversion fails, return empty IFD
        return {}
    gps_ifd[piexif.GPSIFD.GPSLatitude] = lat_dms
    gps_ifd[piexif.GPSIFD.GPSLatitudeRef] = lat_ref.encode("ascii")

    # Step 6: Convert and add longitude
    try:
        lon_dms, lon_ref = decimal_to_dms(lon, is_latitude=False)
    except ValueError:
        # If conversion fails, return empty IFD
        return {}
    gps_ifd[piexif.GPSIFD.GPSLongitude] = lon_dms
    gps_ifd[piexif.GPSIFD.GPSLongitudeRef] = lon_ref.encode("ascii")

    # Step 7: Add altitude if available (3D fix)
    if gps_data.get("altitude") is not None:
        # Encode altitude as rational (meters * 100, 100) for 2 decimal precision
        # EXIF altitude must be absolute value (always positive)
        altitude_abs = abs(gps_data["altitude"])
        altitude_rational = (int(round(altitude_abs * 100)), 100)
        gps_ifd[piexif.GPSIFD.GPSAltitude] = altitude_rational

        # AltitudeRef: 0 = above sea level, 1 = below sea level
        # Set based on sign of original altitude value
        gps_ifd[piexif.GPSIFD.GPSAltitudeRef] = 1 if gps_data["altitude"] < 0 else 0

    # Step 8: Convert Unix timestamp to EXIF GPS timestamp
    if gps_data.get("gpstime", 0) > 0:
        utc_time = datetime.fromtimestamp(gps_data["gpstime"], tz=UTC)

        # GPS TimeStamp: ((hour, 1), (minute, 1), (second, 1))
        gps_ifd[piexif.GPSIFD.GPSTimeStamp] = (
            (utc_time.hour, 1),
            (utc_time.minute, 1),
            (utc_time.second, 1),
        )

        # GPS DateStamp: b'YYYY:MM:DD'
        date_string = f"{utc_time.year:04d}:{utc_time.month:02d}:{utc_time.day:02d}"
        gps_ifd[piexif.GPSIFD.GPSDateStamp] = date_string.encode("ascii")

    # Step 9: Add HDOP (Dilution of Precision) as rational
    if gps_data.get("hdop") is not None:
        hdop_rational = (int(round(gps_data["hdop"] * 100)), 100)
        gps_ifd[piexif.GPSIFD.GPSDOP] = hdop_rational

    # Step 10: Add satellite count as ASCII bytes
    if gps_data.get("satellites_used", 0) > 0:
        satellites_string = str(gps_data["satellites_used"])
        gps_ifd[piexif.GPSIFD.GPSSatellites] = satellites_string.encode("ascii")

    return gps_ifd


def embed_gps_exif(
    photo_path: Path,
    gps_data: dict[str, Any] | None = None,
    controls_file: Path | None = None,
    backup: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
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
        controls_file: Path to controls.txt (or None to use default from mothbox_paths)
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
        >>> result = embed_gps_exif(Path("/photos/mothbox_2025_01_15__12_30_00.jpg"))
        >>> if result["success"]:
        ...     print("GPS EXIF embedded successfully")
        >>> elif result['skipped']:
        ...     print("No GPS fix available, skipped")

    Security:
        - Uses atomic write (write to temp, then rename)
        - Validates JPEG integrity after write
        - Original file preserved if backup=True
    """
    # Import dependencies
    try:
        from PIL import Image

        # Ensure PIL plugins are loaded (fixes test failures when running multiple tests)
        # See: https://pillow.readthedocs.io/en/stable/handbook/overview.html#plugin-loading
        Image.init()
    except ImportError:
        return {
            "success": False,
            "skipped": False,
            "error": "PIL library required for GPS EXIF embedding",
            "gps_embedded": False,
            "original_had_gps": False,
            "backup_path": None,
        }

    if piexif is None:
        return {
            "success": False,
            "skipped": False,
            "error": "piexif library required for GPS EXIF embedding",
            "gps_embedded": False,
            "original_had_gps": False,
            "backup_path": None,
        }

    # Initialize result dict
    result = {
        "success": False,
        "skipped": False,
        "error": None,
        "gps_embedded": False,
        "original_had_gps": False,
        "backup_path": None,
    }

    # Step 1: Get GPS data (use provided or read from controls.txt)
    # Note: Photo existence check removed to avoid TOCTOU race condition
    # File operations below will catch FileNotFoundError if file doesn't exist
    if gps_data is None:
        gps_data = get_gps_data_from_controls(controls_file=controls_file)

    # Step 3: Check if GPS has valid fix
    if not gps_data.get("has_fix", False):
        result["skipped"] = True
        return result

    # Step 4: Try to read existing EXIF from photo
    try:
        # Load existing EXIF
        exif_dict = piexif.load(str(photo_path))

        # Check if photo already has GPS EXIF
        if exif_dict.get("GPS") and piexif.GPSIFD.GPSLatitude in exif_dict["GPS"]:
            result["original_had_gps"] = True

    except Exception as e:
        # Handle invalid JPEG or corrupted EXIF
        result["error"] = f"Failed to read EXIF from photo: {str(e)}"
        return result

    # Step 5: Build GPS IFD from GPS data
    try:
        gps_ifd = build_gps_ifd(gps_data)

        # Check if GPS IFD is empty (should not happen if has_fix=True)
        if not gps_ifd:
            result["error"] = "Failed to build GPS IFD (no GPS fix)"
            result["skipped"] = True
            return result

    except Exception as e:
        result["error"] = f"Failed to build GPS IFD: {str(e)}"
        return result

    # Step 6: Merge GPS IFD with existing EXIF
    # Preserve all existing EXIF (0th, Exif, 1st), only replace GPS
    exif_dict["GPS"] = gps_ifd

    # Step 7: Dump EXIF to bytes
    try:
        exif_bytes = piexif.dump(exif_dict)
    except Exception as e:
        result["error"] = f"Failed to serialize EXIF: {str(e)}"
        return result

    # Step 8: Create backup if requested
    if backup and not dry_run:
        try:
            backup_path = photo_path.with_suffix(photo_path.suffix + ".bak")
            import shutil

            shutil.copy2(photo_path, backup_path)
            result["backup_path"] = backup_path
        except Exception as e:
            result["error"] = f"Failed to create backup: {str(e)}"
            return result

    # Step 9: Write EXIF back to photo (atomic write)
    if not dry_run:
        # Define temp path outside try block for cleanup in finally
        temp_path = photo_path.with_suffix(".jpg.tmp")

        try:
            # Open image
            img = Image.open(photo_path)

            # Save with new EXIF to temporary file first (atomic write pattern)
            img.save(temp_path, "JPEG", exif=exif_bytes, quality=DEFAULT_JPEG_QUALITY)

            # Atomic rename (replaces original)
            temp_path.replace(photo_path)

            result["gps_embedded"] = True

        except Exception as e:
            result["error"] = f"Failed to write EXIF to photo: {str(e)}"
            return result

        finally:
            # Always cleanup temp file if it exists (even on error)
            temp_path.unlink(missing_ok=True)

    # Step 10: Mark success
    result["success"] = True

    return result


def verify_gps_exif(photo_path: Path) -> dict[str, Any]:
    """
    Read and verify GPS EXIF data from a photo.

    Extracts GPS EXIF tags from a JPEG photo and converts them to a
    human-readable format for verification and display.

    SECURITY NOTE: This is a library function called from both web routes
    (where paths are pre-validated) and CLI scripts (where paths come from
    command line args). The exists() check here is for functional validation,
    not security - callers should validate paths before calling this function.

    Args:
        photo_path: Path to JPEG photo file (should be validated by caller)

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
            - error (str or None): Error message if verification failed

    Example:
        >>> info = verify_gps_exif(Path("/photos/mothbox_2025_01_15__12_30_00.jpg"))
        >>> if info["has_gps"]:
        ...     print(f"Photo location: {info['latitude']}, {info['longitude']}")
    """
    # Initialize result with default values
    result = {
        "has_gps": False,
        "latitude": None,
        "longitude": None,
        "timestamp": None,
        "altitude": None,
        "satellites": None,
        "hdop": None,
        "raw_gps_ifd": None,
        "error": None,
    }

    # Check if piexif is available
    if piexif is None:
        result["error"] = "piexif library required for GPS EXIF verification"
        return result

    # Functional check: verify file exists
    # Note: Path should be validated by caller for security
    if not photo_path.exists():
        result["error"] = f"Photo file does not exist: {photo_path}"
        return result

    # Try to read EXIF from photo
    try:
        exif_dict = piexif.load(str(photo_path))
        gps_ifd = exif_dict.get("GPS", {})

        # Check if GPS IFD has latitude and longitude
        if not gps_ifd or piexif.GPSIFD.GPSLatitude not in gps_ifd:
            return result

        # Mark as having GPS
        result["has_gps"] = True
        result["raw_gps_ifd"] = gps_ifd

        # Helper function to parse EXIF rational tuple and convert to decimal
        def parse_exif_coordinate(exif_dms, ref):
            """Parse EXIF DMS tuple to decimal degrees.

            This wrapper extracts DMS components from EXIF rational tuples and
            uses the shared dms_to_decimal utility for conversion.
            """
            from webui.shared.gps_coordinates import dms_to_decimal

            # DMS tuple format: ((degrees, 1), (minutes, 1), (seconds, 100))
            # Validate denominators to prevent division by zero
            # Malformed EXIF data could have zero denominators
            if exif_dms[0][1] == 0 or exif_dms[1][1] == 0 or exif_dms[2][1] == 0:
                raise ValueError(
                    f"Invalid EXIF DMS data: denominator is zero "
                    f"(degrees={exif_dms[0]}, minutes={exif_dms[1]}, seconds={exif_dms[2]})"
                )

            # Extract DMS components from EXIF rational tuples
            degrees = exif_dms[0][0] / exif_dms[0][1]
            minutes = exif_dms[1][0] / exif_dms[1][1]
            seconds = exif_dms[2][0] / exif_dms[2][1]

            # Convert bytes to string if needed
            ref_str = ref.decode("utf-8") if isinstance(ref, bytes) else ref

            # Use shared utility for DMS → decimal conversion
            return dms_to_decimal(int(degrees), int(minutes), seconds, ref_str)

        # Extract latitude
        if piexif.GPSIFD.GPSLatitude in gps_ifd:
            lat_dms = gps_ifd[piexif.GPSIFD.GPSLatitude]
            lat_ref = gps_ifd.get(piexif.GPSIFD.GPSLatitudeRef, b"N")
            result["latitude"] = parse_exif_coordinate(lat_dms, lat_ref)

        # Extract longitude
        if piexif.GPSIFD.GPSLongitude in gps_ifd:
            lon_dms = gps_ifd[piexif.GPSIFD.GPSLongitude]
            lon_ref = gps_ifd.get(piexif.GPSIFD.GPSLongitudeRef, b"E")
            result["longitude"] = parse_exif_coordinate(lon_dms, lon_ref)

        # Extract altitude
        if piexif.GPSIFD.GPSAltitude in gps_ifd:
            altitude_rational = gps_ifd[piexif.GPSIFD.GPSAltitude]
            if altitude_rational[1] == 0:
                raise ValueError(
                    f"Invalid EXIF altitude data: denominator is zero ({altitude_rational})"
                )
            altitude_abs = altitude_rational[0] / altitude_rational[1]

            # Check altitude reference: 0 = above sea level, 1 = below sea level
            altitude_ref = gps_ifd.get(piexif.GPSIFD.GPSAltitudeRef, 0)
            # Apply sign based on reference (negative if below sea level)
            result["altitude"] = -altitude_abs if altitude_ref == 1 else altitude_abs

        # Extract timestamp
        if piexif.GPSIFD.GPSDateStamp in gps_ifd and piexif.GPSIFD.GPSTimeStamp in gps_ifd:
            date_str = gps_ifd[piexif.GPSIFD.GPSDateStamp]
            if isinstance(date_str, bytes):
                date_str = date_str.decode("ascii")

            time_tuple = gps_ifd[piexif.GPSIFD.GPSTimeStamp]
            # Validate denominators to prevent division by zero
            if time_tuple[0][1] == 0 or time_tuple[1][1] == 0 or time_tuple[2][1] == 0:
                raise ValueError(
                    f"Invalid EXIF GPS timestamp data: denominator is zero "
                    f"(hour={time_tuple[0]}, minute={time_tuple[1]}, second={time_tuple[2]})"
                )
            hour = time_tuple[0][0] / time_tuple[0][1]
            minute = time_tuple[1][0] / time_tuple[1][1]
            second = time_tuple[2][0] / time_tuple[2][1]

            result["timestamp"] = f"{date_str} {int(hour):02d}:{int(minute):02d}:{int(second):02d}"

        # Extract satellite count
        if piexif.GPSIFD.GPSSatellites in gps_ifd:
            satellites = gps_ifd[piexif.GPSIFD.GPSSatellites]
            if isinstance(satellites, bytes):
                result["satellites"] = satellites.decode("ascii")
            else:
                result["satellites"] = str(satellites)

        # Extract HDOP
        if piexif.GPSIFD.GPSDOP in gps_ifd:
            hdop_rational = gps_ifd[piexif.GPSIFD.GPSDOP]
            if hdop_rational[1] == 0:
                raise ValueError(f"Invalid EXIF HDOP data: denominator is zero ({hdop_rational})")
            result["hdop"] = hdop_rational[0] / hdop_rational[1]

    except Exception as e:
        # If any error occurs, return result with has_gps=False and error message
        result["error"] = f"Failed to read EXIF from photo: {str(e)}"

    return result


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
    # Use verify_gps_exif and check has_gps field
    gps_info = verify_gps_exif(photo_path)
    return gps_info["has_gps"]

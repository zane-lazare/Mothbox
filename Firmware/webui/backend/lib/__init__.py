"""Shared libraries for Mothbox WebUI backend.

This package contains shared library modules:
- gps_exif_lib: GPS EXIF embedding and verification functions
- series_detection: HDR/Focus Bracket photo series detection
"""

from .gps_exif_lib import (
    BACKUP_EXTENSION,
    DEFAULT_HDOP,
    DEFAULT_JPEG_QUALITY,
    DEFAULT_PDOP,
    DMS_PRECISION,
    EXIF_GPS_VERSION,
    GPS_FIX_2D,
    GPS_FIX_3D,
    GPS_FIX_NONE,
    build_gps_ifd,
    decimal_to_dms,
    embed_gps_exif,
    get_gps_data_from_controls,
    is_already_tagged,
    verify_gps_exif,
)
from .series_detection import (
    FB_PATTERN,
    HDR_PATTERN,
    SeriesInfo,
    SeriesType,
    detect_series_type,
    get_series_id,
    group_photos_into_series,
)

__all__ = [
    # GPS EXIF exports
    'get_gps_data_from_controls',
    'decimal_to_dms',
    'build_gps_ifd',
    'embed_gps_exif',
    'verify_gps_exif',
    'is_already_tagged',
    'EXIF_GPS_VERSION',
    'DMS_PRECISION',
    'DEFAULT_JPEG_QUALITY',
    'BACKUP_EXTENSION',
    'GPS_FIX_NONE',
    'GPS_FIX_2D',
    'GPS_FIX_3D',
    'DEFAULT_HDOP',
    'DEFAULT_PDOP',
    # Series detection exports
    'SeriesInfo',
    'SeriesType',
    'detect_series_type',
    'get_series_id',
    'group_photos_into_series',
    'HDR_PATTERN',
    'FB_PATTERN',
]

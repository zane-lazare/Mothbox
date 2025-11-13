"""
Metadata service for extracting comprehensive EXIF data from photos (Issue #99)

This service provides structured metadata extraction from Mothbox photos for
gallery display. Parses camera settings, GPS location, capture parameters,
series information (HDR/focus bracket), and file metadata.

Architecture:
- Pure Python service (no Flask dependencies)
- Integrates with existing gps_exif_lib for GPS coordinate extraction
- Performance optimized: <50ms per photo, >20 photos/sec batch throughput
- Graceful degradation: handles missing/corrupted EXIF data

Data Structure:
Returns metadata organized into 5 categories:
- camera: Make, model, lens, sensor
- location: GPS coordinates, altitude, satellites, HDOP
- capture: Timestamp, exposure, ISO, focal length, white balance, flash
- deployment: Mothbox ID, firmware version, series type/count/index
- file: Path, filename, size, dimensions, format

Usage:
    from services.metadata_service import MetadataService

    service = MetadataService()

    # Single photo
    metadata = service.get_photo_metadata(Path('/photos/mothbox_2024_01_15__12_30_00.jpg'))

    # Batch processing
    photos = [Path('/photos/photo1.jpg'), Path('/photos/photo2.jpg')]
    results = service.batch_get_metadata(photos)

Related:
- Issue #99: Comprehensive EXIF metadata parser for gallery
- lib/gps_exif_lib.py: GPS coordinate extraction (reused)
"""

from pathlib import Path
from typing import Any, Optional
from datetime import datetime
import re

# Image processing libraries
try:
    from PIL import Image
    import piexif
except ImportError:
    Image = None
    piexif = None

# Import GPS EXIF library for coordinate extraction
from lib.gps_exif_lib import verify_gps_exif


class MetadataService:
    """
    Service for extracting comprehensive EXIF metadata from photos.

    Provides structured metadata extraction organized into 5 categories:
    camera, location, capture, deployment, and file information.

    Attributes:
        None (stateless service)
    """

    def __init__(self):
        """Initialize metadata service"""
        pass

    def get_photo_metadata(self, photo_path: Path) -> dict[str, Any]:
        """
        Extract comprehensive metadata from a single photo.

        Args:
            photo_path: Path to JPEG photo file

        Returns:
            dict: Structured metadata with 5 categories:
                - camera: Camera hardware information
                - location: GPS coordinates and quality metrics
                - capture: Photo capture settings
                - deployment: Mothbox deployment information
                - file: File system metadata

        Example:
            >>> service = MetadataService()
            >>> metadata = service.get_photo_metadata(Path('/photos/photo.jpg'))
            >>> print(f"Camera: {metadata['camera']['make']} {metadata['camera']['model']}")
        """
        # TODO: Implement metadata extraction
        return {
            'camera': {},
            'location': {},
            'capture': {},
            'deployment': {},
            'file': {}
        }

    def batch_get_metadata(self, photo_paths: list[Path]) -> list[dict[str, Any]]:
        """
        Extract metadata from multiple photos in batch.

        Processes photos efficiently with error handling per photo.
        Failed photos return error information instead of raising exceptions.

        Args:
            photo_paths: List of paths to JPEG photos

        Returns:
            list: List of metadata dictionaries, one per photo
                  Failed photos return dict with 'error' key

        Example:
            >>> service = MetadataService()
            >>> photos = [Path('/photos/photo1.jpg'), Path('/photos/photo2.jpg')]
            >>> results = service.batch_get_metadata(photos)
            >>> print(f"Processed {len(results)} photos")
        """
        # TODO: Implement batch processing
        return []

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    def _extract_camera_metadata(self, exif_data: dict) -> dict[str, Optional[str]]:
        """
        Extract camera hardware metadata from EXIF.

        Args:
            exif_data: EXIF dictionary from piexif

        Returns:
            dict: Camera metadata with keys: make, model, lens, sensor
        """
        # TODO: Implement camera metadata extraction
        return {
            'make': None,
            'model': None,
            'lens': None,
            'sensor': None
        }

    def _extract_capture_metadata(self, exif_data: dict) -> dict[str, Any]:
        """
        Extract capture settings metadata from EXIF.

        Args:
            exif_data: EXIF dictionary from piexif

        Returns:
            dict: Capture metadata with timestamp, exposure, ISO, etc.
        """
        # TODO: Implement capture metadata extraction
        return {
            'timestamp': None,
            'exposure_time': None,
            'f_number': None,
            'iso': None,
            'focal_length': None,
            'white_balance': None,
            'flash': None
        }

    def _extract_location_metadata(self, photo_path: Path) -> dict[str, Any]:
        """
        Extract GPS location metadata using gps_exif_lib.

        Reuses existing GPS EXIF extraction logic from gps_exif_lib.py.

        Args:
            photo_path: Path to photo file

        Returns:
            dict: Location metadata with coordinates, altitude, quality metrics
        """
        # TODO: Implement GPS metadata extraction via verify_gps_exif()
        return {
            'latitude': None,
            'longitude': None,
            'altitude': None,
            'gps_timestamp': None,
            'satellites': None,
            'hdop': None
        }

    def _extract_deployment_metadata(self, photo_path: Path, exif_data: dict) -> dict[str, Any]:
        """
        Extract Mothbox deployment metadata.

        Extracts Mothbox ID from filename pattern, firmware version from EXIF,
        and series information (HDR/focus bracket) from filename.

        Args:
            photo_path: Path to photo file
            exif_data: EXIF dictionary from piexif

        Returns:
            dict: Deployment metadata with Mothbox ID, firmware, series info
        """
        # TODO: Implement deployment metadata extraction
        return {
            'mothbox_id': None,
            'firmware_version': None,
            'series_type': None,
            'series_count': None,
            'series_index': None
        }

    def _extract_file_metadata(self, photo_path: Path, image: Image.Image) -> dict[str, Any]:
        """
        Extract file system and image metadata.

        Args:
            photo_path: Path to photo file
            image: PIL Image object

        Returns:
            dict: File metadata with path, size, dimensions, format
        """
        # TODO: Implement file metadata extraction
        return {
            'path': None,
            'filename': None,
            'size': None,
            'width': None,
            'height': None,
            'format': None
        }

    def _detect_series_info(self, photo_path: Path) -> tuple[Optional[str], Optional[int], Optional[int]]:
        """
        Detect if photo is part of a series (HDR or focus bracket).

        Analyzes filename patterns to identify series type, count, and index:
        - HDR: mothbox_YYYY_MM_DD__HH_MM_SS_N.jpg (e.g., _1, _2, _3)
        - Focus bracket: mothbox_YYYY_MM_DD__HH_MM_SS_focus_N.jpg

        Args:
            photo_path: Path to photo file

        Returns:
            tuple: (series_type, series_count, series_index)
                   series_type: 'hdr', 'focus_bracket', or None
                   series_count: Total photos in series or None
                   series_index: 1-indexed position in series or None
        """
        # TODO: Implement series detection logic
        return None, None, None

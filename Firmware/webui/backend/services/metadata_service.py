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
- webui/backend/lib/gps_exif_lib.py: GPS coordinate extraction (reused)
"""

import contextlib
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Setup path to import mothbox modules
# This ensures webui.backend.lib.gps_exif_lib can be imported regardless of how this module is loaded
# (e.g., when run from systemd service at /opt/mothbox/webui/backend/)
services_dir = Path(__file__).resolve().parent
backend_dir = services_dir.parent
webui_dir = backend_dir.parent
firmware_root = webui_dir.parent  # services -> backend -> webui -> Firmware (or /opt/mothbox)
if str(firmware_root) not in sys.path:
    sys.path.insert(0, str(firmware_root))

# Image processing libraries
try:
    import piexif
    from PIL import Image
except ImportError:
    Image = None
    piexif = None

logger = logging.getLogger(__name__)

# GPS EXIF library imported lazily in _extract_gps_location() to avoid import order issues


def _parse_exif_rational(value: Any) -> tuple[int, int] | None:
    """
    Parse an EXIF rational value (numerator/denominator tuple).

    EXIF stores fractional values as (numerator, denominator) tuples.
    This function validates the structure and types before returning.

    Args:
        value: The EXIF value to parse (expected to be a 2-tuple of integers)

    Returns:
        (numerator, denominator) tuple if valid, None otherwise.
        Valid means: tuple of exactly 2 integers with positive denominator.
    """
    if not isinstance(value, tuple) or len(value) != 2:
        return None
    numerator, denominator = value
    if not isinstance(numerator, int) or not isinstance(denominator, int):
        return None
    if denominator <= 0:
        return None
    return (numerator, denominator)


class MetadataService:
    """
    Service for extracting comprehensive EXIF metadata from photos.

    Provides structured metadata extraction organized into 5 categories:
    camera, location, capture, deployment, and file information.

    SECURITY ARCHITECTURE:
        Path validation is handled by the routes layer using validate_photo_path()
        from security_utils.py. This service expects pre-validated paths and focuses
        on metadata extraction. Do not call methods directly with user-provided paths.

        Validation is performed at:
        - routes/metadata.py: Uses validate_photo_path() for single and batch endpoints
        - routes/gallery.py: Uses _resolve_photo_path() → validate_photo_path()

    Attributes:
        None (stateless service)
    """

    def __init__(self):
        """Initialize metadata service"""

    def get_photo_metadata(self, photo_path: Path) -> dict[str, Any]:
        """
        Extract comprehensive metadata from a single photo.

        SECURITY: This method expects photo_path to be pre-validated by the
        routes layer using validate_photo_path() from security_utils.py.
        Direct calls with untrusted paths will bypass path traversal protection.
        See class docstring for security architecture details.

        Args:
            photo_path: Path to JPEG photo file (must be validated/resolved by caller)

        Returns:
            dict: Structured metadata with 5 categories:
                - camera: Camera hardware information
                - location: GPS coordinates and quality metrics
                - capture: Photo capture settings
                - deployment: Mothbox deployment information
                - file: File system metadata
            Returns {'error': ...} if photo cannot be processed.

        Example:
            >>> service = MetadataService()
            >>> # Path should be validated first by routes layer
            >>> metadata = service.get_photo_metadata(Path('/photos/photo.jpg'))
            >>> print(f"Camera: {metadata['camera']['make']} {metadata['camera']['model']}")
        """
        # Initialize result structure with all categories
        metadata = {
            'camera': {'make': None, 'model': None, 'lens': None, 'sensor': None},
            'location': {'latitude': None, 'longitude': None, 'altitude': None,
                        'gps_timestamp': None, 'satellites': None, 'hdop': None},
            'capture': {'timestamp': None, 'exposure_time': None, 'f_number': None,
                       'iso': None, 'focal_length': None, 'white_balance': None, 'flash': None},
            'deployment': {'mothbox_id': None, 'capture_type': None, 'firmware_version': None,
                          'series_type': None, 'series_count': None, 'series_index': None},
            'file': {'path': None, 'filename': None, 'size': None,
                    'width': None, 'height': None, 'format': None}
        }

        try:
            # Defensive check: photo_path should be validated by caller
            # Check if photo exists (safe operation after path validation)
            if not photo_path.exists():
                metadata['error'] = "Photo not found"
                return metadata

            # Populate basic file info even if image can't be opened
            # These operations are safe because path was validated by caller
            metadata['file']['path'] = str(photo_path)
            metadata['file']['filename'] = photo_path.name
            # Redundant exists() check can be removed (already checked above)
            metadata['file']['size'] = photo_path.stat().st_size

            # Open image and extract EXIF data
            # Use context manager to ensure image is always closed, even on error paths
            try:
                with Image.open(photo_path) as image:
                    try:
                        exif_dict = piexif.load(str(photo_path))
                    except Exception as e:
                        # Handle corrupted EXIF gracefully (image still valid)
                        # Log full error details server-side (CodeQL security requirement)
                        logger.warning(f"Failed to load EXIF data from {photo_path.name}: {e}", exc_info=True)
                        exif_dict = {}
                        # Add generic warning flag to metadata (don't expose exception details)
                        metadata['exif_warning'] = "EXIF parsing failed"

                    # Extract metadata from each category
                    metadata['camera'] = self._extract_camera_metadata(exif_dict)
                    metadata['capture'] = self._extract_capture_metadata(exif_dict)
                    metadata['location'] = self._extract_location_metadata(photo_path)
                    metadata['deployment'] = self._extract_deployment_metadata(photo_path, exif_dict)
                    metadata['file'] = self._extract_file_metadata(photo_path, image)
                    # Image automatically closed when exiting 'with' block

            except Exception as img_error:
                # Failed to open image file
                # Log full error details server-side (CodeQL security requirement)
                logger.error(f"Failed to open image {photo_path}: {img_error}", exc_info=True)
                # Return generic message to user (don't expose internal details)
                metadata['error'] = "Failed to open image"
                return metadata

        except PermissionError:
            # Log full error details server-side
            logger.error(f"Permission denied accessing {photo_path}", exc_info=True)
            # Return generic message to user
            metadata['error'] = "Permission denied"
        except Exception as e:
            # Log full error details server-side
            logger.error(f"Unexpected error processing {photo_path}: {e}", exc_info=True)
            # Return generic message to user
            metadata['error'] = "Failed to read metadata"

        return metadata

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
        results = []

        for photo_path in photo_paths:
            try:
                metadata = self.get_photo_metadata(photo_path)
                results.append(metadata)
            except Exception as e:
                # Log full error details server-side (CodeQL security requirement)
                logger.error(f"Failed to process photo {photo_path}: {e}", exc_info=True)
                # Add error entry for failed photo with generic message (don't expose internal details)
                error_entry = {
                    'error': "Failed to process photo",
                    'file': {'path': str(photo_path), 'filename': photo_path.name if photo_path else None}
                }
                results.append(error_entry)

        return results

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    def _extract_camera_metadata(self, exif_data: dict) -> dict[str, str | None]:
        """
        Extract camera hardware metadata from EXIF.

        Args:
            exif_data: EXIF dictionary from piexif

        Returns:
            dict: Camera metadata with keys: make, model, lens, sensor
        """
        camera = {
            'make': None,
            'model': None,
            'lens': None,
            'sensor': None
        }

        try:
            # Extract from 0th IFD (Image File Directory)
            if '0th' in exif_data:
                ifd = exif_data['0th']

                # Camera make
                if piexif.ImageIFD.Make in ifd:
                    camera['make'] = ifd[piexif.ImageIFD.Make].decode('utf-8', errors='ignore').strip()

                # Camera model
                if piexif.ImageIFD.Model in ifd:
                    camera['model'] = ifd[piexif.ImageIFD.Model].decode('utf-8', errors='ignore').strip()

            # Extract from Exif IFD
            if 'Exif' in exif_data:
                exif_ifd = exif_data['Exif']

                # Lens model
                if piexif.ExifIFD.LensModel in exif_ifd:
                    camera['lens'] = exif_ifd[piexif.ExifIFD.LensModel].decode('utf-8', errors='ignore').strip()

                # Sensor from MakerNote (Mothbox-specific)
                if piexif.ExifIFD.MakerNote in exif_ifd:
                    try:
                        import json
                        maker_note_json = exif_ifd[piexif.ExifIFD.MakerNote].decode('utf-8', errors='ignore')
                        maker_note = json.loads(maker_note_json)
                        if 'sensor' in maker_note:
                            camera['sensor'] = maker_note['sensor']
                    except (json.JSONDecodeError, KeyError):
                        pass

        except (AttributeError, KeyError, TypeError, UnicodeDecodeError) as e:
            # Gracefully handle EXIF parsing errors (missing keys, decode failures)
            logger.debug(f"Camera metadata extraction failed: {e}")

        return camera

    def _extract_capture_metadata(self, exif_data: dict) -> dict[str, Any]:
        """
        Extract capture settings metadata from EXIF.

        Args:
            exif_data: EXIF dictionary from piexif

        Returns:
            dict: Capture metadata with timestamp, exposure, ISO, etc.
        """
        capture = {
            'timestamp': None,
            'exposure_time': None,
            'f_number': None,
            'iso': None,
            'focal_length': None,
            'white_balance': None,
            'flash': None,
            'exposure_mode': None,
            'metering_mode': None,
            'sharpness': None,
            'contrast': None,
            'saturation': None,
            'brightness': None,
            'focus_mode': None,
            'af_range': None,
            'af_speed': None,
            'noise_reduction': None,
            'lens_position': None,
            'colour_gain_red': None,
            'colour_gain_blue': None,
        }

        try:
            # Extract from Exif IFD
            if 'Exif' in exif_data:
                exif_ifd = exif_data['Exif']

                # Timestamp (DateTimeOriginal)
                if piexif.ExifIFD.DateTimeOriginal in exif_ifd:
                    dt_str = exif_ifd[piexif.ExifIFD.DateTimeOriginal].decode('utf-8', errors='ignore')
                    # Convert EXIF format (YYYY:MM:DD HH:MM:SS) to ISO 8601
                    try:
                        dt = datetime.strptime(dt_str, '%Y:%m:%d %H:%M:%S')
                        capture['timestamp'] = dt.isoformat()
                    except ValueError:
                        capture['timestamp'] = dt_str

                # Exposure time
                if piexif.ExifIFD.ExposureTime in exif_ifd:
                    rational = _parse_exif_rational(exif_ifd[piexif.ExifIFD.ExposureTime])
                    if rational:
                        numerator, denominator = rational
                        capture['exposure_time'] = f"{numerator}/{denominator}"

                # F-number (aperture)
                if piexif.ExifIFD.FNumber in exif_ifd:
                    rational = _parse_exif_rational(exif_ifd[piexif.ExifIFD.FNumber])
                    if rational:
                        numerator, denominator = rational
                        f_value = numerator / denominator
                        capture['f_number'] = f"f/{f_value:.1f}"

                # ISO
                if piexif.ExifIFD.ISOSpeedRatings in exif_ifd:
                    capture['iso'] = exif_ifd[piexif.ExifIFD.ISOSpeedRatings]

                # Focal length
                if piexif.ExifIFD.FocalLength in exif_ifd:
                    rational = _parse_exif_rational(exif_ifd[piexif.ExifIFD.FocalLength])
                    if rational:
                        numerator, denominator = rational
                        focal_mm = numerator / denominator
                        capture['focal_length'] = f"{int(focal_mm)}mm"

                # White balance
                if piexif.ExifIFD.WhiteBalance in exif_ifd:
                    wb_code = exif_ifd[piexif.ExifIFD.WhiteBalance]
                    capture['white_balance'] = 'Auto' if wb_code == 0 else 'Manual'

                # Flash
                if piexif.ExifIFD.Flash in exif_ifd:
                    flash_code = exif_ifd[piexif.ExifIFD.Flash]
                    # Flash fired if bit 0 is set
                    capture['flash'] = bool(flash_code & 0x01)

                # Exposure mode (0 = Manual, 1 = Auto)
                if piexif.ExifIFD.ExposureMode in exif_ifd:
                    exp_mode = exif_ifd[piexif.ExifIFD.ExposureMode]
                    capture['exposure_mode'] = 'Manual' if exp_mode == 0 else 'Auto'

                # Metering mode (0 = Centre-Weighted, 1 = Spot, 2 = Matrix/Average)
                if piexif.ExifIFD.MeteringMode in exif_ifd:
                    meter_code = exif_ifd[piexif.ExifIFD.MeteringMode]
                    metering_modes = {0: 'Centre-Weighted', 1: 'Spot', 2: 'Matrix'}
                    capture['metering_mode'] = metering_modes.get(meter_code, f'Unknown ({meter_code})')

                # Sharpness (integer value)
                if piexif.ExifIFD.Sharpness in exif_ifd:
                    capture['sharpness'] = exif_ifd[piexif.ExifIFD.Sharpness]

                # Contrast (integer value)
                if piexif.ExifIFD.Contrast in exif_ifd:
                    capture['contrast'] = exif_ifd[piexif.ExifIFD.Contrast]

                # Saturation (integer value)
                if piexif.ExifIFD.Saturation in exif_ifd:
                    capture['saturation'] = exif_ifd[piexif.ExifIFD.Saturation]

                # Brightness (rational tuple)
                if piexif.ExifIFD.BrightnessValue in exif_ifd:
                    rational = _parse_exif_rational(exif_ifd[piexif.ExifIFD.BrightnessValue])
                    if rational:
                        numerator, denominator = rational
                        capture['brightness'] = numerator / denominator

                # MakerNote contains custom Mothbox metadata (focus, noise reduction, colour gains)
                if piexif.ExifIFD.MakerNote in exif_ifd:
                    try:
                        import json
                        maker_note_json = exif_ifd[piexif.ExifIFD.MakerNote].decode('utf-8', errors='ignore')
                        maker_note = json.loads(maker_note_json)

                        # Focus mode (0=Manual, 1=Auto, 2=Continuous)
                        if 'focus_mode' in maker_note:
                            focus_modes = {0: 'Manual', 1: 'Auto Single', 2: 'Continuous AF'}
                            capture['focus_mode'] = focus_modes.get(maker_note['focus_mode'], f"Unknown ({maker_note['focus_mode']})")

                        # AF Range (0=Normal, 1=Macro, 2=Full)
                        if 'af_range' in maker_note:
                            af_ranges = {0: 'Normal', 1: 'Macro', 2: 'Full'}
                            capture['af_range'] = af_ranges.get(maker_note['af_range'], f"Unknown ({maker_note['af_range']})")

                        # AF Speed (0=Normal, 1=Fast)
                        if 'af_speed' in maker_note:
                            af_speeds = {0: 'Normal', 1: 'Fast'}
                            capture['af_speed'] = af_speeds.get(maker_note['af_speed'], f"Unknown ({maker_note['af_speed']})")

                        # Noise Reduction (0=Off, 1=Fast, 2=High Quality)
                        if 'noise_reduction' in maker_note:
                            nr_modes = {0: 'Off', 1: 'Fast', 2: 'High Quality'}
                            capture['noise_reduction'] = nr_modes.get(maker_note['noise_reduction'], f"Unknown ({maker_note['noise_reduction']})")

                        # Lens position (diopters)
                        if 'lens_position' in maker_note:
                            capture['lens_position'] = maker_note['lens_position']

                        # Colour gains
                        if 'colour_gain_red' in maker_note:
                            capture['colour_gain_red'] = maker_note['colour_gain_red']
                        if 'colour_gain_blue' in maker_note:
                            capture['colour_gain_blue'] = maker_note['colour_gain_blue']

                    except (json.JSONDecodeError, KeyError):
                        # MakerNote is not JSON or malformed, skip gracefully
                        pass

        except (AttributeError, KeyError, TypeError, UnicodeDecodeError, ValueError) as e:
            # Gracefully handle EXIF parsing errors (missing keys, decode failures, numeric conversions)
            logger.debug(f"Capture metadata extraction failed: {e}")

        return capture

    def _extract_location_metadata(self, photo_path: Path) -> dict[str, Any]:
        """
        Extract GPS location metadata using gps_exif_lib.

        Reuses existing GPS EXIF extraction logic from gps_exif_lib.py.

        Args:
            photo_path: Path to photo file

        Returns:
            dict: Location metadata with coordinates, altitude, quality metrics
        """
        location = {
            'latitude': None,
            'longitude': None,
            'altitude': None,
            'gps_timestamp': None,
            'satellites': None,
            'hdop': None
        }

        try:
            # Lazy import to avoid module-level import order issues
            from webui.backend.lib.gps_exif_lib import verify_gps_exif

            # Use existing GPS EXIF library
            gps_info = verify_gps_exif(photo_path)

            if gps_info.get('has_gps'):
                location['latitude'] = gps_info.get('latitude')
                location['longitude'] = gps_info.get('longitude')
                location['altitude'] = gps_info.get('altitude')
                location['gps_timestamp'] = gps_info.get('timestamp')

                # Convert satellites from string to int if present
                satellites_str = gps_info.get('satellites')
                if satellites_str:
                    with contextlib.suppress(ValueError, TypeError):
                        location['satellites'] = int(satellites_str)

                location['hdop'] = gps_info.get('hdop')

        except (ImportError, AttributeError, KeyError, TypeError) as e:
            # Gracefully handle GPS extraction errors (import failure, missing data)
            logger.debug(f"Location metadata extraction failed: {e}")

        return location

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
        deployment = {
            'mothbox_id': None,
            'capture_type': None,
            'firmware_version': None,
            'series_type': None,
            'series_count': None,
            'series_index': None
        }

        try:
            # Try to get Mothbox ID and capture type from MakerNote first (preferred)
            if 'Exif' in exif_data:
                exif_ifd = exif_data['Exif']
                if piexif.ExifIFD.MakerNote in exif_ifd:
                    try:
                        import json
                        maker_note_json = exif_ifd[piexif.ExifIFD.MakerNote].decode('utf-8', errors='ignore')
                        maker_note = json.loads(maker_note_json)
                        if 'mothbox_name' in maker_note:
                            deployment['mothbox_id'] = maker_note['mothbox_name']
                        if 'capture_type' in maker_note:
                            deployment['capture_type'] = maker_note['capture_type']
                    except (json.JSONDecodeError, KeyError):
                        pass

            # Fall back to filename parsing if MakerNote didn't have mothbox_name
            if deployment['mothbox_id'] is None:
                filename = photo_path.stem
                match = re.match(r'^([a-zA-Z0-9_-]+)_\d{4}_\d{2}_\d{2}', filename)
                if match:
                    deployment['mothbox_id'] = match.group(1)

            # Extract firmware version from EXIF Software tag
            if '0th' in exif_data:
                ifd = exif_data['0th']
                if piexif.ImageIFD.Software in ifd:
                    deployment['firmware_version'] = ifd[piexif.ImageIFD.Software].decode('utf-8', errors='ignore').strip()

            # Detect series information
            series_type, series_count, series_index = self._detect_series_info(photo_path)
            deployment['series_type'] = series_type
            deployment['series_count'] = series_count
            deployment['series_index'] = series_index

        except (AttributeError, KeyError, TypeError, UnicodeDecodeError) as e:
            # Gracefully handle parsing errors (missing keys, decode failures)
            logger.debug(f"Deployment metadata extraction failed: {e}")

        return deployment

    def _extract_file_metadata(self, photo_path: Path, image: Image.Image) -> dict[str, Any]:
        """
        Extract file system and image metadata.

        SECURITY NOTE: photo_path should be pre-validated by caller.

        Args:
            photo_path: Path to photo file (pre-validated)
            image: PIL Image object

        Returns:
            dict: File metadata with path, size, dimensions, format
        """
        file_info = {
            'path': str(photo_path),
            'filename': photo_path.name,
            'size': None,
            'width': None,
            'height': None,
            'format': None
        }

        try:
            # File size (safe after path validation)
            # photo_path.exists() would be redundant here since we already
            # opened the image successfully in get_photo_metadata()
            try:
                file_info['size'] = photo_path.stat().st_size
            except OSError as e:
                logger.warning(f"Failed to get file size: {e}")

            # Image dimensions and format
            if image:
                file_info['width'] = image.width
                file_info['height'] = image.height
                file_info['format'] = image.format

        except (OSError, AttributeError, TypeError) as e:
            # Gracefully handle file system errors (I/O errors, None image object)
            logger.debug(f"File metadata extraction failed: {e}")

        return file_info

    def _detect_series_info(self, photo_path: Path) -> tuple[str | None, int | None, int | None]:
        """
        Detect if photo is part of a series (HDR or focus bracket).

        Uses the series_detection library to analyze filename patterns.
        Patterns match actual TakePhoto.py output:
        - HDR: {name}_{timestamp}_HDR{index}.jpg (e.g., moth_2024_01_15__10_00_00_HDR0.jpg)
        - Focus bracket: ManFocus_{name}_{timestamp}_FB{index}.jpg

        SECURITY NOTE: photo_path should be pre-validated by caller.
        The parent directory access is safe because photo_path was validated.

        Args:
            photo_path: Path to photo file (pre-validated)

        Returns:
            tuple: (series_type, series_count, series_index)
                   series_type: 'hdr', 'focus_bracket', or None
                   series_count: Total photos in series or None
                   series_index: 0-indexed position in series or None
        """
        try:
            # Import series detection library (Issue #110)
            from webui.backend.lib.series_detection import (
                detect_series_type,
                get_series_id,
            )

            # Detect series type from filename
            info = detect_series_type(photo_path)
            if info is None:
                return None, None, None

            series_type = info.series_type
            series_index = info.index

            # Count total series files in same directory
            # Safe: photo_path was validated, so parent_dir is also within allowed directory
            parent_dir = photo_path.parent
            try:
                # Get series ID for this photo to count matching files
                series_id = get_series_id(photo_path)
                if series_id is None:
                    return series_type, None, series_index

                # Count files with same series ID in directory
                # Import PHOTO_PATTERNS for all supported extensions
                from constants import PHOTO_PATTERNS

                series_count = 0
                for pattern in PHOTO_PATTERNS:
                    for jpg_file in parent_dir.glob(pattern):
                        if get_series_id(jpg_file) == series_id:
                            series_count += 1

                return series_type, series_count, series_index

            except OSError as e:
                logger.warning(f"Failed to glob series files: {e}")
                return series_type, None, series_index

        except ImportError as e:
            logger.warning(f"Series detection library not available: {e}")
            return None, None, None
        except (AttributeError, TypeError) as e:
            # Gracefully handle pattern matching errors (None values, etc.)
            logger.debug(f"Series detection failed: {e}")
            return None, None, None

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

import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Setup path to import mothbox modules (lib/)
# This ensures lib.gps_exif_lib can be imported regardless of how this module is loaded
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

    def get_photo_metadata(self, photo_path: Path) -> dict[str, Any]:
        """
        Extract comprehensive metadata from a single photo.

        SECURITY NOTE: This method expects photo_path to be pre-validated by the
        caller (routes layer) using validate_photo_path(). The service layer focuses
        on metadata extraction, not path validation.

        Args:
            photo_path: Path to JPEG photo file (must be validated/resolved)

        Returns:
            dict: Structured metadata with 5 categories:
                - camera: Camera hardware information
                - location: GPS coordinates and quality metrics
                - capture: Photo capture settings
                - deployment: Mothbox deployment information
                - file: File system metadata

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
            'deployment': {'mothbox_id': None, 'firmware_version': None,
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

                # Sensor type (may not be available in all EXIF data)
                # We'll leave this as None for now as it's rarely populated

        except Exception:
            # Gracefully handle any EXIF parsing errors
            pass

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
                    exposure = exif_ifd[piexif.ExifIFD.ExposureTime]
                    if isinstance(exposure, tuple) and len(exposure) == 2:
                        numerator, denominator = exposure
                        if denominator != 0:
                            capture['exposure_time'] = f"{numerator}/{denominator}"

                # F-number (aperture)
                if piexif.ExifIFD.FNumber in exif_ifd:
                    f_num = exif_ifd[piexif.ExifIFD.FNumber]
                    if isinstance(f_num, tuple) and len(f_num) == 2:
                        numerator, denominator = f_num
                        if denominator != 0:
                            f_value = numerator / denominator
                            capture['f_number'] = f"f/{f_value:.1f}"

                # ISO
                if piexif.ExifIFD.ISOSpeedRatings in exif_ifd:
                    capture['iso'] = exif_ifd[piexif.ExifIFD.ISOSpeedRatings]

                # Focal length
                if piexif.ExifIFD.FocalLength in exif_ifd:
                    focal = exif_ifd[piexif.ExifIFD.FocalLength]
                    if isinstance(focal, tuple) and len(focal) == 2:
                        numerator, denominator = focal
                        if denominator != 0:
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
                    brightness = exif_ifd[piexif.ExifIFD.BrightnessValue]
                    if isinstance(brightness, tuple) and len(brightness) == 2:
                        numerator, denominator = brightness
                        if denominator != 0:
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

        except Exception:
            # Gracefully handle any EXIF parsing errors
            pass

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
            from lib.gps_exif_lib import verify_gps_exif

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
                    try:
                        location['satellites'] = int(satellites_str)
                    except (ValueError, TypeError):
                        pass

                location['hdop'] = gps_info.get('hdop')

        except Exception:
            # Gracefully handle GPS extraction errors
            pass

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
            'firmware_version': None,
            'series_type': None,
            'series_count': None,
            'series_index': None
        }

        try:
            # Extract Mothbox ID from filename (first part before date)
            # Example: mothbox_2024_10_15__14_30_00.jpg -> "mothbox"
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

        except Exception:
            # Gracefully handle any parsing errors
            pass

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

        except Exception:
            # Gracefully handle any file system errors
            pass

        return file_info

    def _detect_series_info(self, photo_path: Path) -> tuple[str | None, int | None, int | None]:
        """
        Detect if photo is part of a series (HDR or focus bracket).

        Analyzes filename patterns to identify series type, count, and index:
        - HDR: mothbox_YYYY_MM_DD__HH_MM_SS_N.jpg (e.g., _1, _2, _3)
        - Focus bracket: mothbox_YYYY_MM_DD__HH_MM_SS_focus_N.jpg

        SECURITY NOTE: photo_path should be pre-validated by caller.
        The parent directory access is safe because photo_path was validated.

        Args:
            photo_path: Path to photo file (pre-validated)

        Returns:
            tuple: (series_type, series_count, series_index)
                   series_type: 'hdr', 'focus_bracket', or None
                   series_count: Total photos in series or None
                   series_index: 1-indexed position in series or None
        """
        try:
            filename = photo_path.stem

            # Check for focus bracket pattern: *_focus_N
            focus_match = re.search(r'_focus_(\d+)$', filename)
            if focus_match:
                series_index = int(focus_match.group(1))

                # Count total focus bracket files in same directory
                # Safe: photo_path was validated, so parent_dir is also within allowed directory
                base_pattern = re.sub(r'_focus_\d+$', '', filename)
                parent_dir = photo_path.parent
                try:
                    series_files = list(parent_dir.glob(f"{base_pattern}_focus_*.jpg"))
                    series_count = len(series_files)
                except OSError as e:
                    logger.warning(f"Failed to glob series files: {e}")
                    series_count = None

                return 'focus_bracket', series_count, series_index

            # Check for HDR pattern: *_N where N is single digit
            # Ensure it's not part of timestamp (avoid matching date/time numbers)
            hdr_match = re.search(r'_(\d)$', filename)
            if hdr_match:
                series_index = int(hdr_match.group(1))

                # Count total HDR files in same directory
                # Safe: photo_path was validated, so parent_dir is also within allowed directory
                base_pattern = re.sub(r'_\d$', '', filename)
                parent_dir = photo_path.parent
                try:
                    series_files = list(parent_dir.glob(f"{base_pattern}_*.jpg"))

                    # Filter to only single-digit suffixes (HDR series)
                    hdr_files = [f for f in series_files if re.search(r'_\d\.jpg$', f.name)]
                    series_count = len(hdr_files)
                except OSError as e:
                    logger.warning(f"Failed to glob series files: {e}")
                    series_count = None

                if series_count > 1:
                    return 'hdr', series_count, series_index

        except Exception:
            # Gracefully handle any pattern matching errors
            pass

        return None, None, None

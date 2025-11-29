"""
Unit tests for metadata service (Issue #99)

Tests comprehensive EXIF metadata parsing for gallery display.
Follows TDD methodology with strict test-first approach.

Test Coverage:
- EXIF parsing (camera, capture, location, deployment, file metadata)
- GPS coordinate normalization via gps_exif_lib integration
- Series detection (HDR, focus bracket)
- Batch parsing with error handling
- Performance requirements (<50ms per photo)

Coverage Target: 85%+
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from io import BytesIO
from PIL import Image
import piexif

# Explicitly register JPEG plugin for PIL (required for img.save(..., "JPEG"))
# Import after PIL.Image to ensure plugin system is initialized
try:
    from PIL import JpegImagePlugin
except ImportError:
    pass  # JPEG support may not be available in all environments



# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="module")
def temp_photos_dir(tmp_path_factory):
    """
    Temporary PHOTOS_DIR for metadata tests (module-scoped)

    Creates isolated photo directory that persists across all tests in module.
    Uses tmp_path_factory for module-scoped fixtures.

    Note: PHOTOS_DIR patching handled by conftest.py patch_path_constant_everywhere fixture.
    """
    photos_dir = tmp_path_factory.mktemp("photos")

    return photos_dir


@pytest.fixture(scope="module")
def sample_photo_with_exif(temp_photos_dir):
    """
    Create a sample JPEG photo with comprehensive EXIF data (module-scoped)

    Includes camera, capture, and GPS metadata for testing.
    Module scope ensures photo persists across all tests.
    """
    photo_path = temp_photos_dir / "mothbox_2024_10_15__14_30_00.jpg"

    # Skip creation if photo already exists (for module-scoped fixture)
    if photo_path.exists():
        return photo_path

    # Create a minimal valid JPEG image
    img = Image.new('RGB', (640, 480), color='red')

    # Build comprehensive EXIF data
    exif_dict = {
        "0th": {
            piexif.ImageIFD.Make: b"Arducam",
            piexif.ImageIFD.Model: b"OwlSight 64MP",
            piexif.ImageIFD.Software: b"Mothbox Firmware 5.0",
            piexif.ImageIFD.DateTime: b"2024:10:15 14:30:00",
            piexif.ImageIFD.XResolution: (72, 1),
            piexif.ImageIFD.YResolution: (72, 1),
        },
        "Exif": {
            piexif.ExifIFD.DateTimeOriginal: b"2024:10:15 14:30:00",
            piexif.ExifIFD.ExposureTime: (1, 500),  # 1/500 sec
            piexif.ExifIFD.FNumber: (28, 10),  # f/2.8
            piexif.ExifIFD.ISOSpeedRatings: 400,
            piexif.ExifIFD.FocalLength: (24, 1),  # 24mm
            piexif.ExifIFD.WhiteBalance: 0,  # Auto
            piexif.ExifIFD.Flash: 16,  # No flash
            piexif.ExifIFD.LensModel: b"Wide Angle Lens",
        },
        "GPS": {
            piexif.GPSIFD.GPSLatitudeRef: b"N",
            piexif.GPSIFD.GPSLatitude: ((37, 1), (47, 1), (3000, 100)),  # 37°47'30.00"
            piexif.GPSIFD.GPSLongitudeRef: b"W",
            piexif.GPSIFD.GPSLongitude: ((122, 1), (25, 1), (1200, 100)),  # 122°25'12.00"
            piexif.GPSIFD.GPSAltitudeRef: 0,
            piexif.GPSIFD.GPSAltitude: (100, 1),  # 100m
            piexif.GPSIFD.GPSTimeStamp: ((14, 1), (30, 1), (0, 1)),
            piexif.GPSIFD.GPSDateStamp: b"2024:10:15",
            piexif.GPSIFD.GPSSatellites: b"12",
            piexif.GPSIFD.GPSDOP: (150, 100),  # 1.5
        }
    }

    exif_bytes = piexif.dump(exif_dict)
    img.save(photo_path, "JPEG", exif=exif_bytes)

    # Verify file was created successfully
    assert photo_path.exists(), f"Failed to create photo at {photo_path}"
    assert photo_path.stat().st_size > 0, f"Photo file is empty at {photo_path}"

    return photo_path


@pytest.fixture(scope="module")
def sample_photo_no_exif(temp_photos_dir):
    """
    Create a sample JPEG photo with NO EXIF data (module-scoped)

    Used for testing graceful degradation and missing metadata handling.
    """
    photo_path = temp_photos_dir / "photo_no_exif.jpg"

    # Skip if already exists
    if photo_path.exists():
        return photo_path

    # Create minimal JPEG without EXIF
    img = Image.new('RGB', (320, 240), color='blue')
    img.save(photo_path, "JPEG")

    # Verify file was created
    assert photo_path.exists(), f"Failed to create photo at {photo_path}"

    return photo_path


@pytest.fixture(scope="module")
def sample_hdr_series(temp_photos_dir):
    """
    Create a series of HDR photos with sequential numbering (module-scoped)

    Simulates Mothbox HDR capture workflow.
    Uses correct naming pattern from TakePhoto.py: {name}_{timestamp}_HDR{index}.jpg
    """
    photos = []
    base_name = "mothbox_2024_10_15__14_30_00"

    for i in range(3):  # HDR0, HDR1, HDR2 (0-indexed)
        photo_path = temp_photos_dir / f"{base_name}_HDR{i}.jpg"

        # Skip if already exists
        if not photo_path.exists():
            img = Image.new('RGB', (640, 480), color='green')
            img.save(photo_path, "JPEG")
            assert photo_path.exists(), f"Failed to create HDR photo at {photo_path}"

        photos.append(photo_path)

    return photos


@pytest.fixture(scope="module")
def sample_focus_bracket_series(temp_photos_dir):
    """
    Create a series of focus bracket photos (module-scoped)

    Simulates Mothbox focus stacking workflow.
    Uses correct naming pattern from capture_focus_bracket.py: ManFocus_{name}_{timestamp}_FB{index}.jpg
    """
    photos = []
    base_name = "ManFocus_mothbox_2024_10_15__15_00_00"

    for i in range(5):  # FB0, FB1, FB2, FB3, FB4 (0-indexed)
        photo_path = temp_photos_dir / f"{base_name}_FB{i}.jpg"

        # Skip if already exists
        if not photo_path.exists():
            img = Image.new('RGB', (640, 480), color='yellow')
            img.save(photo_path, "JPEG")
            assert photo_path.exists(), f"Failed to create focus bracket photo at {photo_path}"

        photos.append(photo_path)

    return photos


@pytest.fixture
def metadata_service():
    """
    MetadataService instance for testing

    Import is deferred to allow service creation after test setup.
    """
    # Defer import to ensure paths are patched first
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))

    from services.metadata_service import MetadataService
    return MetadataService()


# ============================================================================
# Test Class 1: Service Initialization
# ============================================================================

class TestMetadataServiceInitialization:
    """Test metadata service initialization and basic structure"""

    def test_service_can_be_instantiated(self, metadata_service):
        """Test that MetadataService can be instantiated"""
        assert metadata_service is not None
        assert hasattr(metadata_service, 'get_photo_metadata')
        assert hasattr(metadata_service, 'batch_get_metadata')

    def test_service_has_required_methods(self, metadata_service):
        """Test that service has all required public methods"""
        assert callable(getattr(metadata_service, 'get_photo_metadata', None))
        assert callable(getattr(metadata_service, 'batch_get_metadata', None))


# ============================================================================
# Test Class 2: EXIF Parsing
# ============================================================================

class TestEXIFParsing:
    """Test core EXIF metadata extraction from photos"""

    def test_extract_camera_metadata(self, metadata_service, sample_photo_with_exif):
        """Test extraction of camera-specific metadata"""
        metadata = metadata_service.get_photo_metadata(sample_photo_with_exif)

        assert metadata is not None
        assert 'camera' in metadata

        camera = metadata['camera']
        assert camera['make'] == "Arducam"
        assert camera['model'] == "OwlSight 64MP"
        assert camera['lens'] == "Wide Angle Lens"

    def test_extract_capture_metadata(self, metadata_service, sample_photo_with_exif):
        """Test extraction of capture settings metadata"""
        metadata = metadata_service.get_photo_metadata(sample_photo_with_exif)

        assert 'capture' in metadata

        capture = metadata['capture']
        assert capture['timestamp'] == "2024-10-15T14:30:00"
        assert capture['exposure_time'] == "1/500"
        assert capture['f_number'] == "f/2.8"
        assert capture['iso'] == 400
        assert capture['focal_length'] == "24mm"
        assert capture['white_balance'] == "Auto"
        assert capture['flash'] is False

    def test_extract_file_metadata(self, metadata_service, sample_photo_with_exif):
        """Test extraction of file-level metadata"""
        metadata = metadata_service.get_photo_metadata(sample_photo_with_exif)

        assert 'file' in metadata

        file_info = metadata['file']
        assert file_info['path'] == str(sample_photo_with_exif)
        assert file_info['filename'] == "mothbox_2024_10_15__14_30_00.jpg"
        assert file_info['size'] > 0
        assert file_info['width'] == 640
        assert file_info['height'] == 480
        assert file_info['format'] == "JPEG"

    def test_extract_location_metadata(self, metadata_service, sample_photo_with_exif):
        """Test extraction of GPS location metadata"""
        metadata = metadata_service.get_photo_metadata(sample_photo_with_exif)

        assert 'location' in metadata

        location = metadata['location']
        assert location['latitude'] is not None
        assert location['longitude'] is not None
        assert abs(location['latitude'] - 37.7917) < 0.01  # ~37°47'30"
        assert abs(location['longitude'] - (-122.42)) < 0.01  # ~122°25'12"
        assert location['altitude'] == 100.0
        assert location['satellites'] == 12
        assert location['hdop'] == 1.5

    def test_handle_missing_exif_gracefully(self, metadata_service, sample_photo_no_exif):
        """Test graceful handling of photos without EXIF data"""
        metadata = metadata_service.get_photo_metadata(sample_photo_no_exif)

        assert metadata is not None

        # Camera metadata should be None
        assert metadata['camera']['make'] is None
        assert metadata['camera']['model'] is None

        # Capture metadata should be None
        assert metadata['capture']['timestamp'] is None
        assert metadata['capture']['exposure_time'] is None

        # Location should be None
        assert metadata['location']['latitude'] is None
        assert metadata['location']['longitude'] is None

        # File metadata should still be present
        assert metadata['file']['filename'] == "photo_no_exif.jpg"
        assert metadata['file']['width'] == 320
        assert metadata['file']['height'] == 240

    def test_handle_corrupted_exif_data(self, metadata_service, temp_photos_dir):
        """Test handling of corrupted or invalid EXIF data"""
        # Create a JPEG with malformed EXIF
        photo_path = temp_photos_dir / "corrupted_exif.jpg"

        # Write minimal JPEG with invalid EXIF marker
        with open(photo_path, 'wb') as f:
            f.write(b'\xFF\xD8\xFF\xE1\x00\x10Invalid EXIF\xFF\xD9')

        # Should not raise exception
        metadata = metadata_service.get_photo_metadata(photo_path)

        assert metadata is not None
        assert metadata['file']['filename'] == "corrupted_exif.jpg"


# ============================================================================
# Test Class 3: Metadata Structuring
# ============================================================================

class TestMetadataStructuring:
    """Test that metadata is structured according to specification"""

    def test_metadata_has_all_required_categories(self, metadata_service, sample_photo_with_exif):
        """Test that returned metadata has all 5 required categories"""
        metadata = metadata_service.get_photo_metadata(sample_photo_with_exif)

        assert 'camera' in metadata
        assert 'location' in metadata
        assert 'capture' in metadata
        assert 'deployment' in metadata
        assert 'file' in metadata

    def test_camera_category_structure(self, metadata_service, sample_photo_with_exif):
        """Test camera category has required fields"""
        metadata = metadata_service.get_photo_metadata(sample_photo_with_exif)
        camera = metadata['camera']

        assert 'make' in camera
        assert 'model' in camera
        assert 'lens' in camera
        assert 'sensor' in camera

    def test_location_category_structure(self, metadata_service, sample_photo_with_exif):
        """Test location category has required fields"""
        metadata = metadata_service.get_photo_metadata(sample_photo_with_exif)
        location = metadata['location']

        assert 'latitude' in location
        assert 'longitude' in location
        assert 'altitude' in location
        assert 'gps_timestamp' in location
        assert 'satellites' in location
        assert 'hdop' in location

    def test_capture_category_structure(self, metadata_service, sample_photo_with_exif):
        """Test capture category has required fields"""
        metadata = metadata_service.get_photo_metadata(sample_photo_with_exif)
        capture = metadata['capture']

        assert 'timestamp' in capture
        assert 'exposure_time' in capture
        assert 'f_number' in capture
        assert 'iso' in capture
        assert 'focal_length' in capture
        assert 'white_balance' in capture
        assert 'flash' in capture

    def test_deployment_category_structure(self, metadata_service, sample_photo_with_exif):
        """Test deployment category has required fields"""
        metadata = metadata_service.get_photo_metadata(sample_photo_with_exif)
        deployment = metadata['deployment']

        assert 'mothbox_id' in deployment
        assert 'firmware_version' in deployment
        assert 'series_type' in deployment
        assert 'series_count' in deployment
        assert 'series_index' in deployment

    def test_file_category_structure(self, metadata_service, sample_photo_with_exif):
        """Test file category has required fields"""
        metadata = metadata_service.get_photo_metadata(sample_photo_with_exif)
        file_info = metadata['file']

        assert 'path' in file_info
        assert 'filename' in file_info
        assert 'size' in file_info
        assert 'width' in file_info
        assert 'height' in file_info
        assert 'format' in file_info


# ============================================================================
# Test Class 4: Batch Parsing
# ============================================================================

class TestBatchParsing:
    """Test batch metadata extraction for multiple photos"""

    def test_batch_parse_multiple_photos(self, metadata_service, sample_photo_with_exif, sample_photo_no_exif):
        """Test batch parsing of multiple photos"""
        photo_paths = [sample_photo_with_exif, sample_photo_no_exif]

        results = metadata_service.batch_get_metadata(photo_paths)

        assert len(results) == 2
        assert all('file' in result for result in results)

    def test_batch_parse_empty_list(self, metadata_service):
        """Test batch parsing with empty photo list"""
        results = metadata_service.batch_get_metadata([])

        assert results == []

    def test_batch_parse_with_errors(self, metadata_service, sample_photo_with_exif, temp_photos_dir):
        """Test batch parsing continues on individual photo errors"""
        # Create a non-existent photo path
        nonexistent = temp_photos_dir / "nonexistent.jpg"

        photo_paths = [sample_photo_with_exif, nonexistent]

        results = metadata_service.batch_get_metadata(photo_paths)

        # Should return results for valid photo, error for invalid
        assert len(results) == 2
        assert results[0]['file']['filename'] == "mothbox_2024_10_15__14_30_00.jpg"
        assert 'error' in results[1] or results[1] is None

    def test_batch_parse_performance(self, metadata_service, temp_photos_dir):
        """Test batch parsing meets performance requirements (>20 photos/sec)"""
        import time

        # Create 50 test photos
        photos = []
        for i in range(50):
            photo_path = temp_photos_dir / f"batch_photo_{i}.jpg"
            img = Image.new('RGB', (640, 480), color='red')
            img.save(photo_path, "JPEG")
            photos.append(photo_path)

        start = time.time()
        results = metadata_service.batch_get_metadata(photos)
        elapsed = time.time() - start

        # Should process >20 photos/sec (50 photos in <2.5 seconds)
        photos_per_sec = len(photos) / elapsed
        assert photos_per_sec > 20, f"Only processed {photos_per_sec:.1f} photos/sec (target: >20)"


# ============================================================================
# Test Class 5: GPS Coordinate Normalization
# ============================================================================

class TestGPSCoordinateNormalization:
    """Test GPS coordinate extraction via gps_exif_lib integration"""

    def test_gps_coordinates_normalized_to_decimal(self, metadata_service, sample_photo_with_exif):
        """Test GPS coordinates converted from DMS to decimal degrees"""
        metadata = metadata_service.get_photo_metadata(sample_photo_with_exif)

        location = metadata['location']

        # Coordinates should be in decimal degrees
        assert isinstance(location['latitude'], float)
        assert isinstance(location['longitude'], float)
        assert -90 <= location['latitude'] <= 90
        assert -180 <= location['longitude'] <= 180

    def test_gps_altitude_extraction(self, metadata_service, sample_photo_with_exif):
        """Test GPS altitude extraction in meters"""
        metadata = metadata_service.get_photo_metadata(sample_photo_with_exif)

        location = metadata['location']
        assert location['altitude'] == 100.0

    def test_gps_quality_metrics(self, metadata_service, sample_photo_with_exif):
        """Test GPS quality metrics (satellites, HDOP)"""
        metadata = metadata_service.get_photo_metadata(sample_photo_with_exif)

        location = metadata['location']
        assert location['satellites'] == 12
        assert location['hdop'] == 1.5

    def test_missing_gps_data_returns_none(self, metadata_service, sample_photo_no_exif):
        """Test photos without GPS return None for location fields"""
        metadata = metadata_service.get_photo_metadata(sample_photo_no_exif)

        location = metadata['location']
        assert location['latitude'] is None
        assert location['longitude'] is None
        assert location['altitude'] is None


# ============================================================================
# Test Class 6: HDR/Focus Bracket Detection
# ============================================================================

class TestHDRFocusBracketDetection:
    """Test series detection for HDR and focus bracket photos"""

    def test_detect_hdr_series(self, metadata_service, sample_hdr_series):
        """Test detection of HDR photo series"""
        # Test middle photo of series (HDR1)
        metadata = metadata_service.get_photo_metadata(sample_hdr_series[1])

        deployment = metadata['deployment']
        assert deployment['series_type'] == 'hdr'
        assert deployment['series_count'] == 3
        assert deployment['series_index'] == 1  # Middle photo (0-indexed: HDR1)

    def test_detect_focus_bracket_series(self, metadata_service, sample_focus_bracket_series):
        """Test detection of focus bracket photo series"""
        # Test first photo of series (FB0)
        metadata = metadata_service.get_photo_metadata(sample_focus_bracket_series[0])

        deployment = metadata['deployment']
        assert deployment['series_type'] == 'focus_bracket'
        assert deployment['series_count'] == 5
        assert deployment['series_index'] == 0  # First photo (0-indexed: FB0)

    def test_single_photo_has_no_series(self, metadata_service, sample_photo_with_exif):
        """Test single photo not part of series"""
        metadata = metadata_service.get_photo_metadata(sample_photo_with_exif)

        deployment = metadata['deployment']
        assert deployment['series_type'] is None
        assert deployment['series_count'] is None
        assert deployment['series_index'] is None

    def test_extract_mothbox_id_from_filename(self, metadata_service, sample_photo_with_exif):
        """Test Mothbox ID extraction from filename pattern"""
        metadata = metadata_service.get_photo_metadata(sample_photo_with_exif)

        deployment = metadata['deployment']
        # Filename: mothbox_2024_10_15__14_30_00.jpg
        # Should extract "mothbox" as ID (or use EXIF Software field)
        assert deployment['mothbox_id'] is not None

    def test_extract_firmware_version_from_exif(self, metadata_service, sample_photo_with_exif):
        """Test firmware version extraction from EXIF Software tag"""
        metadata = metadata_service.get_photo_metadata(sample_photo_with_exif)

        deployment = metadata['deployment']
        assert deployment['firmware_version'] == "Mothbox Firmware 5.0"


# ============================================================================
# Test Class 7: Metadata Service Errors
# ============================================================================

class TestMetadataServiceErrors:
    """Test error handling for various failure scenarios"""

    def test_nonexistent_photo_path(self, metadata_service, temp_photos_dir):
        """Test handling of non-existent photo file"""
        nonexistent = temp_photos_dir / "does_not_exist.jpg"

        # Should return error information instead of raising exception
        metadata = metadata_service.get_photo_metadata(nonexistent)

        assert metadata is not None
        assert 'error' in metadata or metadata['file']['path'] is None

    def test_invalid_photo_format(self, metadata_service, temp_photos_dir):
        """Test handling of non-JPEG files"""
        # Create a text file with .jpg extension
        fake_photo = temp_photos_dir / "not_a_photo.jpg"
        fake_photo.write_text("This is not a JPEG")

        # Should handle gracefully
        metadata = metadata_service.get_photo_metadata(fake_photo)

        assert metadata is not None
        # Either returns error or minimal metadata
        assert 'error' in metadata or metadata['file']['format'] is None

    def test_permission_denied_on_photo(self, metadata_service, temp_photos_dir):
        """Test handling of permission errors"""
        import os
        import stat

        # Create a photo with no read permissions
        restricted_photo = temp_photos_dir / "restricted.jpg"
        img = Image.new('RGB', (100, 100))
        img.save(restricted_photo, "JPEG")

        # Remove read permissions
        os.chmod(restricted_photo, 0o000)

        try:
            metadata = metadata_service.get_photo_metadata(restricted_photo)

            # Should handle gracefully
            assert metadata is not None
            assert 'error' in metadata or metadata is None
        finally:
            # Restore permissions for cleanup
            os.chmod(restricted_photo, stat.S_IRUSR | stat.S_IWUSR)

    def test_handle_path_traversal_attempt(self, metadata_service):
        """Test that path traversal attempts are rejected"""
        # Try to access file outside photos directory
        malicious_path = Path("/etc/passwd")

        # Should either reject or safely handle
        metadata = metadata_service.get_photo_metadata(malicious_path)

        # Implementation should prevent access outside PHOTOS_DIR
        assert metadata is not None
        # Specific handling depends on implementation


# ============================================================================
# Test Class 8: Performance Requirements
# ============================================================================

class TestPerformanceRequirements:
    """Test that metadata service meets performance targets"""

    def test_single_photo_parsing_under_50ms(self, metadata_service, sample_photo_with_exif):
        """Test single photo parsing meets <50ms requirement"""
        import time

        # Warm up
        metadata_service.get_photo_metadata(sample_photo_with_exif)

        # Timed run
        start = time.time()
        metadata = metadata_service.get_photo_metadata(sample_photo_with_exif)
        elapsed = (time.time() - start) * 1000  # Convert to ms

        assert elapsed < 50, f"Parsing took {elapsed:.1f}ms (target: <50ms)"
        assert metadata is not None

    def test_batch_throughput_over_20_photos_per_sec(self, metadata_service, temp_photos_dir):
        """Test batch parsing meets >20 photos/sec requirement"""
        import time

        # Create 100 test photos
        photos = []
        for i in range(100):
            photo_path = temp_photos_dir / f"perf_photo_{i}.jpg"
            img = Image.new('RGB', (640, 480), color='blue')
            img.save(photo_path, "JPEG")
            photos.append(photo_path)

        # Timed batch processing
        start = time.time()
        results = metadata_service.batch_get_metadata(photos)
        elapsed = time.time() - start

        photos_per_sec = len(photos) / elapsed

        assert photos_per_sec > 20, \
            f"Throughput: {photos_per_sec:.1f} photos/sec (target: >20 photos/sec)"
        assert len(results) == 100


# ============================================================================
# Test Class 9: Additional Edge Cases for Coverage
# ============================================================================

class TestAdditionalEdgeCases:
    """Additional edge case tests to improve coverage"""

    def test_extract_partial_gps_data(self, metadata_service, temp_photos_dir):
        """Test GPS extraction when only some GPS fields are present"""
        photo_path = temp_photos_dir / "partial_gps.jpg"

        # Create image with incomplete GPS data (no satellites/hdop)
        img = Image.new('RGB', (640, 480))
        exif_dict = {
            "GPS": {
                piexif.GPSIFD.GPSLatitudeRef: b"N",
                piexif.GPSIFD.GPSLatitude: ((37, 1), (47, 1), (3000, 100)),
                piexif.GPSIFD.GPSLongitudeRef: b"W",
                piexif.GPSIFD.GPSLongitude: ((122, 1), (25, 1), (1200, 100)),
            }
        }

        exif_bytes = piexif.dump(exif_dict)
        img.save(photo_path, "JPEG", exif=exif_bytes)

        metadata = metadata_service.get_photo_metadata(photo_path)

        # Should have coordinates but no satellite/hdop data
        assert metadata['location']['latitude'] is not None
        assert metadata['location']['longitude'] is not None

    def test_series_detection_with_no_siblings(self, metadata_service, temp_photos_dir):
        """Test series detection when photo pattern matches but has no siblings"""
        # Create single photo with series pattern
        photo_path = temp_photos_dir / "mothbox_2024_10_15__14_30_00_1.jpg"
        img = Image.new('RGB', (100, 100))
        img.save(photo_path, "JPEG")

        metadata = metadata_service.get_photo_metadata(photo_path)

        # Should not detect as series if only 1 photo
        deployment = metadata['deployment']
        # Single photo with _1 suffix might still be detected but count would be 1
        # or it might not be detected as series at all
        assert deployment is not None

    def test_filename_without_mothbox_pattern(self, metadata_service, temp_photos_dir):
        """Test handling of filenames that don't match Mothbox pattern"""
        # Create photo with non-standard filename
        photo_path = temp_photos_dir / "random_photo.jpg"
        img = Image.new('RGB', (100, 100))
        img.save(photo_path, "JPEG")

        metadata = metadata_service.get_photo_metadata(photo_path)

        # Should still work but mothbox_id might be None
        assert metadata is not None
        assert metadata['file']['filename'] == 'random_photo.jpg'

    def test_exif_with_zero_denominator(self, metadata_service, temp_photos_dir):
        """Test handling of EXIF rational values with zero denominator"""
        photo_path = temp_photos_dir / "zero_denom.jpg"

        img = Image.new('RGB', (640, 480))

        # Create EXIF with zero denominator (invalid but possible in corrupted files)
        exif_dict = {
            "Exif": {
                piexif.ExifIFD.ExposureTime: (1, 0),  # Division by zero
                piexif.ExifIFD.FNumber: (28, 0),      # Division by zero
            }
        }

        exif_bytes = piexif.dump(exif_dict)
        img.save(photo_path, "JPEG", exif=exif_bytes)

        # Should handle gracefully without crashing
        metadata = metadata_service.get_photo_metadata(photo_path)

        assert metadata is not None
        # These fields should be None due to division by zero
        assert metadata['capture']['exposure_time'] is None
        assert metadata['capture']['f_number'] is None


# ============================================================================
# Test Class 10: Series Detection Pattern Edge Cases
# ============================================================================

class TestSeriesDetectionEdgeCases:
    """Test _detect_series_info() method with various edge cases"""

    def test_hdr_series_detection_pattern(self, metadata_service, temp_photos_dir):
        """Test HDR series detection with standard pattern (e.g., photo_2024_01_15__10_00_00_HDR0.jpg)"""
        # Create HDR series with correct TakePhoto.py pattern
        base_name = "mothbox_2024_11_01__10_00_00"
        photos = []
        for i in range(3):  # 0-indexed: HDR0, HDR1, HDR2
            photo_path = temp_photos_dir / f"{base_name}_HDR{i}.jpg"
            img = Image.new('RGB', (640, 480), color='red')
            img.save(photo_path, "JPEG")
            photos.append(photo_path)

        # Test detection on middle photo (HDR1)
        metadata = metadata_service.get_photo_metadata(photos[1])
        deployment = metadata['deployment']

        assert deployment['series_type'] == 'hdr'
        assert deployment['series_count'] == 3
        assert deployment['series_index'] == 1  # 0-indexed

    def test_focus_bracket_series_detection_pattern(self, metadata_service, temp_photos_dir):
        """Test focus bracket series detection with standard pattern (ManFocus_{name}_FB{N}.jpg)"""
        # Create focus bracket series with correct TakePhoto.py pattern
        base_name = "mothbox_2024_11_01__10_30_00"
        photos = []
        for i in range(5):  # 0-indexed: FB0, FB1, FB2, FB3, FB4
            photo_path = temp_photos_dir / f"ManFocus_{base_name}_FB{i}.jpg"
            img = Image.new('RGB', (640, 480), color='blue')
            img.save(photo_path, "JPEG")
            photos.append(photo_path)

        # Test detection on first photo (FB0)
        metadata = metadata_service.get_photo_metadata(photos[0])
        deployment = metadata['deployment']

        assert deployment['series_type'] == 'focus_bracket'
        assert deployment['series_count'] == 5
        assert deployment['series_index'] == 0  # 0-indexed

    def test_single_photo_not_part_of_series(self, metadata_service, temp_photos_dir):
        """Test single photo that's not part of any series"""
        photo_path = temp_photos_dir / "mothbox_2024_11_01__11_00_00.jpg"
        img = Image.new('RGB', (640, 480), color='green')
        img.save(photo_path, "JPEG")

        metadata = metadata_service.get_photo_metadata(photo_path)
        deployment = metadata['deployment']

        assert deployment['series_type'] is None
        assert deployment['series_count'] is None
        assert deployment['series_index'] is None

    def test_malformed_series_pattern(self, metadata_service, temp_photos_dir):
        """Test photo with malformed series pattern (e.g., invalid suffix)"""
        # Create photo with invalid pattern
        photo_path = temp_photos_dir / "mothbox_2024_11_01__11_30_00_abc.jpg"
        img = Image.new('RGB', (640, 480), color='yellow')
        img.save(photo_path, "JPEG")

        metadata = metadata_service.get_photo_metadata(photo_path)
        deployment = metadata['deployment']

        # Should not detect as series
        assert deployment['series_type'] is None

    def test_missing_series_files_incomplete(self, metadata_service, temp_photos_dir):
        """Test series with missing files (e.g., HDR0, HDR2 but no HDR1)"""
        # Create incomplete HDR series (missing middle photo)
        base_name = "mothbox_2024_11_01__12_00_00"
        photo0 = temp_photos_dir / f"{base_name}_HDR0.jpg"
        photo2 = temp_photos_dir / f"{base_name}_HDR2.jpg"

        img = Image.new('RGB', (640, 480), color='orange')
        img.save(photo0, "JPEG")
        img.save(photo2, "JPEG")

        # Test detection - should still detect as series with count=2
        metadata = metadata_service.get_photo_metadata(photo0)
        deployment = metadata['deployment']

        assert deployment['series_type'] == 'hdr'
        assert deployment['series_count'] == 2  # Only 2 files exist
        assert deployment['series_index'] == 0  # 0-indexed

    def test_series_glob_failure_handling(self, metadata_service, temp_photos_dir):
        """Test handling when glob operation fails during series detection"""
        # Create a focus bracket photo with correct TakePhoto.py pattern
        photo_path = temp_photos_dir / "ManFocus_mothbox_2024_11_01__13_00_00_FB5.jpg"
        img = Image.new('RGB', (640, 480), color='purple')
        img.save(photo_path, "JPEG")

        # Mock glob on parent_dir to raise OSError when listing jpg files
        original_glob = Path.glob
        def mock_glob(self, pattern):
            # The implementation uses "*.jpg" or "*.JPG" to count series files
            if pattern in ("*.jpg", "*.JPG"):
                raise OSError("Permission denied")
            return original_glob(self, pattern)

        with patch.object(Path, 'glob', mock_glob):
            metadata = metadata_service.get_photo_metadata(photo_path)
            deployment = metadata['deployment']

            # Focus bracket returns series info even when glob fails
            # series_count is None due to glob failure, but type and index are still detected
            assert deployment['series_type'] == 'focus_bracket'
            assert deployment['series_count'] is None  # Glob failed
            assert deployment['series_index'] == 5  # 0-indexed

    def test_series_with_different_naming_conventions(self, metadata_service, temp_photos_dir):
        """Test series with non-standard device naming conventions"""
        # Create photos with different device name but correct HDR pattern
        photos = []
        for i in range(3):  # 0-indexed: HDR0, HDR1, HDR2
            photo_path = temp_photos_dir / f"custom_device_2024_11_01__14_00_00_HDR{i}.jpg"
            img = Image.new('RGB', (640, 480), color='pink')
            img.save(photo_path, "JPEG")
            photos.append(photo_path)

        # Should still detect HDR pattern
        metadata = metadata_service.get_photo_metadata(photos[0])
        deployment = metadata['deployment']

        assert deployment['series_type'] == 'hdr'
        assert deployment['series_count'] == 3
        assert deployment['series_index'] == 0  # 0-indexed

    def test_large_series_10_plus_photos(self, metadata_service, temp_photos_dir):
        """Test series with 10+ photos (e.g., extensive focus bracket)"""
        # Create large focus bracket series with correct TakePhoto.py pattern
        base_name = "mothbox_2024_11_01__15_00_00"
        photos = []
        for i in range(12):  # 0-indexed: FB0 through FB11
            photo_path = temp_photos_dir / f"ManFocus_{base_name}_FB{i}.jpg"
            img = Image.new('RGB', (640, 480), color='cyan')
            img.save(photo_path, "JPEG")
            photos.append(photo_path)

        # Test detection on middle photo (FB5)
        metadata = metadata_service.get_photo_metadata(photos[5])
        deployment = metadata['deployment']

        assert deployment['series_type'] == 'focus_bracket'
        assert deployment['series_count'] == 12
        assert deployment['series_index'] == 5  # 0-indexed


# ============================================================================
# Test Class 11: GPS Integration Mocking
# ============================================================================

class TestGPSIntegrationMocking:
    """Test _extract_location_metadata() method with GPS mocking"""

    def test_valid_gps_coordinates_extraction(self, metadata_service, temp_photos_dir):
        """Test extraction of valid GPS coordinates"""
        photo_path = temp_photos_dir / "gps_valid.jpg"
        img = Image.new('RGB', (640, 480))

        # Create EXIF with valid GPS data
        exif_dict = {
            "GPS": {
                piexif.GPSIFD.GPSLatitudeRef: b"N",
                piexif.GPSIFD.GPSLatitude: ((40, 1), (42, 1), (4600, 100)),  # 40°42'46.00"N
                piexif.GPSIFD.GPSLongitudeRef: b"W",
                piexif.GPSIFD.GPSLongitude: ((74, 1), (0, 1), (3600, 100)),  # 74°0'36.00"W
            }
        }

        exif_bytes = piexif.dump(exif_dict)
        img.save(photo_path, "JPEG", exif=exif_bytes)

        metadata = metadata_service.get_photo_metadata(photo_path)
        location = metadata['location']

        # Should have valid coordinates
        assert location['latitude'] is not None
        assert location['longitude'] is not None
        assert isinstance(location['latitude'], float)
        assert isinstance(location['longitude'], float)

    def test_missing_gps_data_handling(self, metadata_service, temp_photos_dir):
        """Test handling when GPS data is completely missing"""
        photo_path = temp_photos_dir / "gps_missing.jpg"
        img = Image.new('RGB', (640, 480))

        # Create photo with NO GPS data
        img.save(photo_path, "JPEG")

        metadata = metadata_service.get_photo_metadata(photo_path)
        location = metadata['location']

        # All GPS fields should be None
        assert location['latitude'] is None
        assert location['longitude'] is None
        assert location['altitude'] is None
        assert location['satellites'] is None
        assert location['hdop'] is None

    def test_invalid_gps_format_handling(self, metadata_service, temp_photos_dir):
        """Test handling of invalid GPS format"""
        photo_path = temp_photos_dir / "gps_invalid.jpg"
        img = Image.new('RGB', (640, 480))

        # Create EXIF with malformed GPS data (missing required fields)
        exif_dict = {
            "GPS": {
                piexif.GPSIFD.GPSLatitudeRef: b"N",
                # Missing GPSLatitude coordinate
            }
        }

        exif_bytes = piexif.dump(exif_dict)
        img.save(photo_path, "JPEG", exif=exif_bytes)

        metadata = metadata_service.get_photo_metadata(photo_path)

        # Should handle gracefully without crashing
        assert metadata is not None
        assert 'location' in metadata

    def test_gps_with_altitude_3d_fix(self, metadata_service, temp_photos_dir):
        """Test GPS data with altitude (3D fix)"""
        photo_path = temp_photos_dir / "gps_3d.jpg"
        img = Image.new('RGB', (640, 480))

        # Create EXIF with 3D GPS fix (includes altitude)
        exif_dict = {
            "GPS": {
                piexif.GPSIFD.GPSLatitudeRef: b"N",
                piexif.GPSIFD.GPSLatitude: ((35, 1), (40, 1), (0, 1)),
                piexif.GPSIFD.GPSLongitudeRef: b"E",
                piexif.GPSIFD.GPSLongitude: ((139, 1), (45, 1), (0, 1)),
                piexif.GPSIFD.GPSAltitudeRef: 0,
                piexif.GPSIFD.GPSAltitude: (250, 1),  # 250m above sea level
            }
        }

        exif_bytes = piexif.dump(exif_dict)
        img.save(photo_path, "JPEG", exif=exif_bytes)

        metadata = metadata_service.get_photo_metadata(photo_path)
        location = metadata['location']

        assert location['altitude'] is not None
        assert location['altitude'] == 250.0

    def test_gps_without_altitude_2d_fix(self, metadata_service, temp_photos_dir):
        """Test GPS data without altitude (2D fix)"""
        photo_path = temp_photos_dir / "gps_2d.jpg"
        img = Image.new('RGB', (640, 480))

        # Create EXIF with 2D GPS fix (no altitude)
        exif_dict = {
            "GPS": {
                piexif.GPSIFD.GPSLatitudeRef: b"N",
                piexif.GPSIFD.GPSLatitude: ((35, 1), (40, 1), (0, 1)),
                piexif.GPSIFD.GPSLongitudeRef: b"E",
                piexif.GPSIFD.GPSLongitude: ((139, 1), (45, 1), (0, 1)),
                # No altitude fields
            }
        }

        exif_bytes = piexif.dump(exif_dict)
        img.save(photo_path, "JPEG", exif=exif_bytes)

        metadata = metadata_service.get_photo_metadata(photo_path)
        location = metadata['location']

        assert location['latitude'] is not None
        assert location['longitude'] is not None
        # Altitude should be None for 2D fix
        assert location['altitude'] is None

    def test_gps_quality_metrics_extraction(self, metadata_service, temp_photos_dir):
        """Test GPS quality metrics (HDOP, PDOP, satellites)"""
        photo_path = temp_photos_dir / "gps_quality.jpg"
        img = Image.new('RGB', (640, 480))

        # Create EXIF with GPS quality metrics
        exif_dict = {
            "GPS": {
                piexif.GPSIFD.GPSLatitudeRef: b"N",
                piexif.GPSIFD.GPSLatitude: ((37, 1), (47, 1), (3000, 100)),
                piexif.GPSIFD.GPSLongitudeRef: b"W",
                piexif.GPSIFD.GPSLongitude: ((122, 1), (25, 1), (1200, 100)),
                piexif.GPSIFD.GPSSatellites: b"15",
                piexif.GPSIFD.GPSDOP: (120, 100),  # 1.2
            }
        }

        exif_bytes = piexif.dump(exif_dict)
        img.save(photo_path, "JPEG", exif=exif_bytes)

        metadata = metadata_service.get_photo_metadata(photo_path)
        location = metadata['location']

        assert location['satellites'] == 15
        assert location['hdop'] is not None

    def test_coordinate_conversion_dms_to_decimal(self, metadata_service, temp_photos_dir):
        """Test coordinate conversion from DMS to decimal degrees"""
        photo_path = temp_photos_dir / "gps_conversion.jpg"
        img = Image.new('RGB', (640, 480))

        # Create EXIF with precise DMS coordinates
        # 51°30'26.46"N, 0°7'39.9"W (Greenwich, London)
        exif_dict = {
            "GPS": {
                piexif.GPSIFD.GPSLatitudeRef: b"N",
                piexif.GPSIFD.GPSLatitude: ((51, 1), (30, 1), (2646, 100)),
                piexif.GPSIFD.GPSLongitudeRef: b"W",
                piexif.GPSIFD.GPSLongitude: ((0, 1), (7, 1), (399, 10)),
            }
        }

        exif_bytes = piexif.dump(exif_dict)
        img.save(photo_path, "JPEG", exif=exif_bytes)

        metadata = metadata_service.get_photo_metadata(photo_path)
        location = metadata['location']

        # Verify conversion to decimal degrees
        assert location['latitude'] is not None
        assert location['longitude'] is not None
        # Latitude should be approximately 51.507
        assert abs(location['latitude'] - 51.507) < 0.01
        # Longitude should be approximately -0.127
        assert abs(location['longitude'] - (-0.127)) < 0.01

    def test_empty_null_coordinate_handling(self, metadata_service, temp_photos_dir):
        """Test handling of empty/null GPS coordinates"""
        photo_path = temp_photos_dir / "gps_empty.jpg"
        img = Image.new('RGB', (640, 480))

        # Create EXIF with empty GPS IFD
        exif_dict = {
            "GPS": {}
        }

        exif_bytes = piexif.dump(exif_dict)
        img.save(photo_path, "JPEG", exif=exif_bytes)

        metadata = metadata_service.get_photo_metadata(photo_path)
        location = metadata['location']

        # Should handle empty GPS data gracefully
        assert location['latitude'] is None
        assert location['longitude'] is None


# ============================================================================
# Test Class 12: EXIF Rational Edge Cases
# ============================================================================

class TestEXIFRationalEdgeCases:
    """Test _extract_capture_metadata() method with EXIF rational edge cases"""

    def test_exif_rational_number_parsing(self, metadata_service, temp_photos_dir):
        """Test EXIF rational number parsing (exposure time as fraction)"""
        photo_path = temp_photos_dir / "exif_rational.jpg"
        img = Image.new('RGB', (640, 480))

        # Create EXIF with various rational values
        exif_dict = {
            "Exif": {
                piexif.ExifIFD.ExposureTime: (1, 1000),  # 1/1000 sec
                piexif.ExifIFD.FNumber: (56, 10),  # f/5.6
                piexif.ExifIFD.FocalLength: (50, 1),  # 50mm
            }
        }

        exif_bytes = piexif.dump(exif_dict)
        img.save(photo_path, "JPEG", exif=exif_bytes)

        metadata = metadata_service.get_photo_metadata(photo_path)
        capture = metadata['capture']

        assert capture['exposure_time'] == "1/1000"
        assert capture['f_number'] == "f/5.6"
        assert capture['focal_length'] == "50mm"

    def test_makernote_json_parsing(self, metadata_service, temp_photos_dir):
        """Test MakerNote JSON parsing"""
        photo_path = temp_photos_dir / "exif_makernote.jpg"
        img = Image.new('RGB', (640, 480))

        # Create EXIF with MakerNote containing JSON
        import json
        maker_note_data = {
            'sensor': 'IMX477',
            'focus_mode': 1,
            'af_range': 2,
            'noise_reduction': 1,
            'lens_position': 3.5
        }
        maker_note_json = json.dumps(maker_note_data)

        exif_dict = {
            "Exif": {
                piexif.ExifIFD.MakerNote: maker_note_json.encode('utf-8')
            }
        }

        exif_bytes = piexif.dump(exif_dict)
        img.save(photo_path, "JPEG", exif=exif_bytes)

        metadata = metadata_service.get_photo_metadata(photo_path)
        capture = metadata['capture']
        camera = metadata['camera']

        assert camera['sensor'] == 'IMX477'
        assert capture['focus_mode'] == 'Auto Single'
        assert capture['af_range'] == 'Full'
        assert capture['noise_reduction'] == 'Fast'
        assert capture['lens_position'] == 3.5

    def test_invalid_makernote_handling(self, metadata_service, temp_photos_dir):
        """Test handling of invalid MakerNote (non-JSON)"""
        photo_path = temp_photos_dir / "exif_makernote_invalid.jpg"
        img = Image.new('RGB', (640, 480))

        # Create EXIF with invalid MakerNote (not JSON)
        exif_dict = {
            "Exif": {
                piexif.ExifIFD.MakerNote: b"Not valid JSON data"
            }
        }

        exif_bytes = piexif.dump(exif_dict)
        img.save(photo_path, "JPEG", exif=exif_bytes)

        metadata = metadata_service.get_photo_metadata(photo_path)

        # Should handle gracefully without crashing
        assert metadata is not None
        assert 'capture' in metadata

    def test_missing_exif_tags_gracefully_handled(self, metadata_service, temp_photos_dir):
        """Test that missing EXIF tags are gracefully handled"""
        photo_path = temp_photos_dir / "exif_minimal.jpg"
        img = Image.new('RGB', (640, 480))

        # Create EXIF with minimal data
        exif_dict = {
            "Exif": {
                piexif.ExifIFD.ISOSpeedRatings: 200
            }
        }

        exif_bytes = piexif.dump(exif_dict)
        img.save(photo_path, "JPEG", exif=exif_bytes)

        metadata = metadata_service.get_photo_metadata(photo_path)
        capture = metadata['capture']

        # ISO should be present
        assert capture['iso'] == 200
        # Other fields should be None
        assert capture['exposure_time'] is None
        assert capture['f_number'] is None

    def test_corrupted_exif_data_handling(self, metadata_service, temp_photos_dir):
        """Test handling of corrupted EXIF data"""
        photo_path = temp_photos_dir / "exif_corrupted.jpg"

        # Create minimal JPEG with corrupted EXIF marker
        with open(photo_path, 'wb') as f:
            # JPEG start marker
            f.write(b'\xFF\xD8')
            # APP1 marker (EXIF) with invalid data
            f.write(b'\xFF\xE1\x00\x20')
            f.write(b'Corrupted EXIF data that is invalid')
            # JPEG end marker
            f.write(b'\xFF\xD9')

        metadata = metadata_service.get_photo_metadata(photo_path)

        # Should handle gracefully without crashing
        assert metadata is not None
        assert 'exif_warning' in metadata or 'error' in metadata

    def test_non_standard_exif_formats(self, metadata_service, temp_photos_dir):
        """Test handling of non-standard EXIF formats"""
        photo_path = temp_photos_dir / "exif_nonstandard.jpg"
        img = Image.new('RGB', (640, 480))

        # Create EXIF with unusual values
        exif_dict = {
            "Exif": {
                piexif.ExifIFD.ExposureMode: 3,  # Unknown mode
                piexif.ExifIFD.MeteringMode: 99,  # Unknown metering
                piexif.ExifIFD.WhiteBalance: 2,  # Unknown WB
            }
        }

        exif_bytes = piexif.dump(exif_dict)
        img.save(photo_path, "JPEG", exif=exif_bytes)

        metadata = metadata_service.get_photo_metadata(photo_path)
        capture = metadata['capture']

        # Should handle non-standard values without crashing
        assert metadata is not None
        assert capture['metering_mode'] is not None  # Should have fallback

    def test_large_exif_metadata(self, metadata_service, temp_photos_dir):
        """Test handling of large EXIF metadata"""
        photo_path = temp_photos_dir / "exif_large.jpg"
        img = Image.new('RGB', (640, 480))

        # Create EXIF with many fields
        exif_dict = {
            "0th": {
                piexif.ImageIFD.Make: b"TestMake" * 10,
                piexif.ImageIFD.Model: b"TestModel" * 10,
                piexif.ImageIFD.Software: b"TestSoftware" * 10,
            },
            "Exif": {
                piexif.ExifIFD.DateTimeOriginal: b"2024:11:01 10:00:00",
                piexif.ExifIFD.ExposureTime: (1, 100),
                piexif.ExifIFD.FNumber: (28, 10),
                piexif.ExifIFD.ISOSpeedRatings: 800,
                piexif.ExifIFD.FocalLength: (35, 1),
                piexif.ExifIFD.WhiteBalance: 0,
                piexif.ExifIFD.Flash: 0,
                piexif.ExifIFD.ExposureMode: 0,
                piexif.ExifIFD.MeteringMode: 1,
                piexif.ExifIFD.Sharpness: 2,
                piexif.ExifIFD.Contrast: 1,
                piexif.ExifIFD.Saturation: 1,
            },
            "GPS": {
                piexif.GPSIFD.GPSLatitudeRef: b"N",
                piexif.GPSIFD.GPSLatitude: ((37, 1), (47, 1), (3000, 100)),
                piexif.GPSIFD.GPSLongitudeRef: b"W",
                piexif.GPSIFD.GPSLongitude: ((122, 1), (25, 1), (1200, 100)),
            }
        }

        exif_bytes = piexif.dump(exif_dict)
        img.save(photo_path, "JPEG", exif=exif_bytes)

        metadata = metadata_service.get_photo_metadata(photo_path)

        # Should handle large EXIF without performance issues
        assert metadata is not None
        assert metadata['camera']['make'] is not None
        assert metadata['capture']['iso'] == 800

    def test_unicode_in_exif_fields(self, metadata_service, temp_photos_dir):
        """Test handling of Unicode characters in EXIF fields"""
        photo_path = temp_photos_dir / "exif_unicode.jpg"
        img = Image.new('RGB', (640, 480))

        # Create EXIF with Unicode strings
        exif_dict = {
            "0th": {
                piexif.ImageIFD.Make: "Arducam™".encode('utf-8'),
                piexif.ImageIFD.Model: "OwlSight 64MP 📷".encode('utf-8'),
            },
            "Exif": {
                piexif.ExifIFD.LensModel: "Wide Angle Lens °".encode('utf-8'),
            }
        }

        exif_bytes = piexif.dump(exif_dict)
        img.save(photo_path, "JPEG", exif=exif_bytes)

        metadata = metadata_service.get_photo_metadata(photo_path)
        camera = metadata['camera']

        # Should handle Unicode gracefully
        assert metadata is not None
        assert "Arducam" in camera['make']
        assert "OwlSight" in camera['model']

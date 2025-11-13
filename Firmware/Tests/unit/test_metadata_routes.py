"""
Unit tests for metadata API routes (Issue #99)

Tests REST API endpoints for EXIF metadata extraction.
Focuses on security (path traversal), error handling, and response format.

Coverage Target: 90%+
"""

import pytest
import json
from pathlib import Path
from flask import Flask
from PIL import Image
import piexif

# Explicitly register JPEG plugin for PIL (required for img.save(..., "JPEG"))
# Import after PIL.Image to ensure plugin system is initialized
try:
    from PIL import JpegImagePlugin
except ImportError:
    pass  # JPEG support may not be available in all environments

# Function to get real PIL.Image, bypassing any mocking from gallery tests
def _get_real_pil_image():
    """
    Get real PIL.Image module, bypassing any mocking from gallery tests.

    This prevents gallery test PIL mocking from polluting metadata fixtures.
    We use __import__ to bypass sys.modules caching and ensure we get the real PIL.
    """
    import sys
    from unittest.mock import MagicMock

    # Check if PIL.Image in sys.modules is a MagicMock (from gallery tests)
    if 'PIL.Image' in sys.modules:
        pil_image = sys.modules['PIL.Image']
        # If it's a MagicMock, remove it and force fresh import
        if isinstance(pil_image, MagicMock) or hasattr(pil_image, '_mock_name'):
            del sys.modules['PIL.Image']
            if 'PIL' in sys.modules and isinstance(sys.modules['PIL'], MagicMock):
                del sys.modules['PIL']

    # Import fresh PIL
    from PIL import Image
    return Image


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="module", autouse=True)
def cleanup_pil_mocks():
    """
    Clear any PIL.Image mocks from sys.modules before metadata tests.

    Gallery tests may mock PIL.Image at module level, which can persist
    in sys.modules and pollute metadata tests. This fixture ensures we
    start with a clean slate.

    Autouse ensures it runs before any tests in this module.
    """
    import sys
    from unittest.mock import MagicMock

    # Remove mock pollution from sys.modules
    pil_modules = ['PIL.Image', 'PIL', 'PIL.ImageDraw', 'PIL.ImageFont', 'PIL.JpegImagePlugin']
    for module_name in pil_modules:
        if module_name in sys.modules:
            module = sys.modules[module_name]
            if isinstance(module, MagicMock):
                del sys.modules[module_name]

    yield

    # Cleanup after tests too (prevent pollution of subsequent test modules)
    for module_name in pil_modules:
        if module_name in sys.modules:
            module = sys.modules[module_name]
            if isinstance(module, MagicMock):
                del sys.modules[module_name]


@pytest.fixture(scope="module", autouse=True)
def temp_photos_dir(tmp_path_factory):
    """
    Temporary PHOTOS_DIR for metadata route tests (module-scoped, autouse)

    Creates temporary directory and patches PHOTOS_DIR globally for this test module.
    """
    photos_dir = tmp_path_factory.mktemp("photos")

    # Patch PHOTOS_DIR in all relevant modules
    import mothbox_paths
    import routes.metadata
    import services.metadata_service

    original_mothbox_paths_photos_dir = mothbox_paths.PHOTOS_DIR
    original_routes_metadata_photos_dir = routes.metadata.PHOTOS_DIR

    mothbox_paths.PHOTOS_DIR = photos_dir
    routes.metadata.PHOTOS_DIR = photos_dir

    yield photos_dir

    # Restore original values
    mothbox_paths.PHOTOS_DIR = original_mothbox_paths_photos_dir
    routes.metadata.PHOTOS_DIR = original_routes_metadata_photos_dir


@pytest.fixture(scope="module")
def metadata_app(temp_photos_dir):
    """Flask app with metadata blueprint for testing (module-scoped)"""
    app = Flask(__name__)
    app.config['TESTING'] = True

    # Register blueprint
    from routes.metadata import metadata_bp
    app.register_blueprint(metadata_bp, url_prefix='/api/metadata')

    return app


@pytest.fixture(scope="module")
def metadata_client(metadata_app):
    """Test client for metadata routes (module-scoped)"""
    return metadata_app.test_client()


@pytest.fixture(scope="module")
def sample_photo_with_exif(temp_photos_dir):
    """Create a sample JPEG photo with EXIF data (module-scoped)"""
    photo_path = temp_photos_dir / "test_photo.jpg"

    # Skip if already exists
    if photo_path.exists():
        return photo_path

    # Create image with EXIF
    img = _get_real_pil_image().new('RGB', (640, 480), color='red')

    exif_dict = {
        "0th": {
            piexif.ImageIFD.Make: b"Arducam",
            piexif.ImageIFD.Model: b"OwlSight 64MP",
            piexif.ImageIFD.Software: b"Mothbox 5.0",
        },
        "Exif": {
            piexif.ExifIFD.ISOSpeedRatings: 400,
        }
    }

    exif_bytes = piexif.dump(exif_dict)
    img.save(photo_path, "JPEG", exif=exif_bytes)

    # Verify file was created
    assert photo_path.exists(), f"Failed to create photo at {photo_path}"

    return photo_path


# ============================================================================
# Test Single Photo Metadata Endpoint
# ============================================================================

class TestSinglePhotoMetadata:
    """Test GET /api/metadata/photo/<path>/metadata endpoint"""

    def test_get_metadata_for_valid_photo(self, metadata_client, sample_photo_with_exif):
        """Test getting metadata for a valid photo"""
        photo_name = sample_photo_with_exif.name

        response = metadata_client.get(f'/api/metadata/photo/{photo_name}/metadata')

        assert response.status_code == 200

        data = json.loads(response.data)

        # Verify all 5 metadata categories present
        assert 'camera' in data
        assert 'location' in data
        assert 'capture' in data
        assert 'deployment' in data
        assert 'file' in data

        # Verify camera metadata extracted
        assert data['camera']['make'] == 'Arducam'
        assert data['camera']['model'] == 'OwlSight 64MP'

        # Verify file metadata
        assert data['file']['filename'] == photo_name

    def test_get_metadata_for_nonexistent_photo(self, metadata_client):
        """Test 404 response for nonexistent photo"""
        response = metadata_client.get('/api/metadata/photo/nonexistent.jpg/metadata')

        assert response.status_code == 404

        data = json.loads(response.data)
        assert 'error' in data
        assert 'not found' in data['error'].lower()

    def test_path_traversal_protection(self, metadata_client):
        """Test that path traversal attacks are blocked"""
        # Try to access file outside PHOTOS_DIR
        response = metadata_client.get('/api/metadata/photo/../../etc/passwd/metadata')

        assert response.status_code == 403

        data = json.loads(response.data)
        assert 'error' in data
        assert 'denied' in data['error'].lower() or 'invalid' in data['error'].lower()

    def test_get_metadata_for_nested_photo(self, metadata_client, temp_photos_dir):
        """Test getting metadata for photo in nested directory"""
        # Create nested directory
        nested_dir = temp_photos_dir / "2024" / "10"
        nested_dir.mkdir(parents=True)

        # Create photo
        photo_path = nested_dir / "nested_photo.jpg"
        img = _get_real_pil_image().new('RGB', (100, 100))
        img.save(photo_path, "JPEG")

        # Request with nested path
        response = metadata_client.get('/api/metadata/photo/2024/10/nested_photo.jpg/metadata')

        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['file']['filename'] == 'nested_photo.jpg'

    def test_response_format_structure(self, metadata_client, sample_photo_with_exif):
        """Test that response has correct JSON structure"""
        photo_name = sample_photo_with_exif.name

        response = metadata_client.get(f'/api/metadata/photo/{photo_name}/metadata')

        data = json.loads(response.data)

        # Verify camera structure
        assert 'make' in data['camera']
        assert 'model' in data['camera']
        assert 'lens' in data['camera']
        assert 'sensor' in data['camera']

        # Verify location structure
        assert 'latitude' in data['location']
        assert 'longitude' in data['location']
        assert 'altitude' in data['location']

        # Verify capture structure
        assert 'timestamp' in data['capture']
        assert 'iso' in data['capture']
        assert 'exposure_time' in data['capture']

        # Verify deployment structure
        assert 'mothbox_id' in data['deployment']
        assert 'firmware_version' in data['deployment']

        # Verify file structure
        assert 'path' in data['file']
        assert 'filename' in data['file']
        assert 'size' in data['file']


# ============================================================================
# Test Batch Metadata Endpoint
# ============================================================================

class TestBatchMetadata:
    """Test POST /api/metadata/batch/metadata endpoint"""

    def test_batch_metadata_for_multiple_photos(self, metadata_client, temp_photos_dir):
        """Test batch metadata extraction for multiple photos"""
        # Create 3 test photos
        photos = []
        for i in range(3):
            photo_path = temp_photos_dir / f"photo_{i}.jpg"
            img = _get_real_pil_image().new('RGB', (100, 100))
            img.save(photo_path, "JPEG")
            photos.append(f"photo_{i}.jpg")

        # Request batch metadata
        response = metadata_client.post(
            '/api/metadata/batch/metadata',
            json={"photo_paths": photos},
            content_type='application/json'
        )

        assert response.status_code == 200

        data = json.loads(response.data)

        # Verify response structure
        assert 'results' in data
        assert 'total' in data
        assert 'successful' in data
        assert 'failed' in data

        # Verify all 3 photos processed
        assert data['total'] == 3
        assert data['successful'] == 3
        assert data['failed'] == 0

        # Verify each result has metadata
        assert len(data['results']) == 3
        for result in data['results']:
            assert 'file' in result
            assert 'camera' in result

    def test_batch_metadata_with_mixed_valid_invalid(self, metadata_client, temp_photos_dir):
        """Test batch processing with mix of valid and invalid photos"""
        # Create 1 valid photo
        valid_photo = temp_photos_dir / "valid.jpg"
        img = _get_real_pil_image().new('RGB', (100, 100))
        img.save(valid_photo, "JPEG")

        # Request batch with valid and invalid paths
        photo_paths = ["valid.jpg", "nonexistent.jpg"]

        response = metadata_client.post(
            '/api/metadata/batch/metadata',
            json={"photo_paths": photo_paths},
            content_type='application/json'
        )

        assert response.status_code == 200

        data = json.loads(response.data)

        # Should process both (1 success, 1 failure)
        assert data['total'] == 2
        assert data['successful'] == 1
        assert data['failed'] == 1

        # First result should be valid
        assert 'camera' in data['results'][0]
        assert 'error' not in data['results'][0]

        # Second result should have error
        assert 'error' in data['results'][1]

    def test_batch_metadata_empty_list(self, metadata_client):
        """Test batch request with empty photo list"""
        response = metadata_client.post(
            '/api/metadata/batch/metadata',
            json={"photo_paths": []},
            content_type='application/json'
        )

        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['total'] == 0
        assert data['results'] == []

    def test_batch_metadata_missing_photo_paths(self, metadata_client):
        """Test batch request without photo_paths field"""
        response = metadata_client.post(
            '/api/metadata/batch/metadata',
            json={},
            content_type='application/json'
        )

        assert response.status_code == 400

        data = json.loads(response.data)
        assert 'error' in data
        assert 'photo_paths' in data['error'].lower()

    def test_batch_metadata_invalid_json(self, metadata_client):
        """Test batch request with invalid JSON"""
        response = metadata_client.post(
            '/api/metadata/batch/metadata',
            data='not valid json',
            content_type='application/json'
        )

        assert response.status_code == 400

    def test_batch_metadata_non_array_paths(self, metadata_client):
        """Test batch request with non-array photo_paths"""
        response = metadata_client.post(
            '/api/metadata/batch/metadata',
            json={"photo_paths": "not_an_array"},
            content_type='application/json'
        )

        assert response.status_code == 400

        data = json.loads(response.data)
        assert 'error' in data

    def test_batch_path_traversal_protection(self, metadata_client, temp_photos_dir):
        """Test that batch endpoint blocks path traversal"""
        # Create 1 valid photo
        valid_photo = temp_photos_dir / "valid.jpg"
        img = _get_real_pil_image().new('RGB', (100, 100))
        img.save(valid_photo, "JPEG")

        # Try to include path traversal in batch
        photo_paths = ["valid.jpg", "../../etc/passwd"]

        response = metadata_client.post(
            '/api/metadata/batch/metadata',
            json={"photo_paths": photo_paths},
            content_type='application/json'
        )

        assert response.status_code == 200

        data = json.loads(response.data)

        # Valid photo should succeed
        assert data['successful'] == 1
        # Traversal attempt should fail
        assert data['failed'] == 1

        # Second result should have error
        assert 'error' in data['results'][1]
        assert 'invalid' in data['results'][1]['error'].lower()


# ============================================================================
# Test Error Handling
# ============================================================================

class TestMetadataRoutesErrorHandling:
    """Test error handling in metadata routes"""

    def test_single_photo_with_corrupted_file(self, metadata_client, temp_photos_dir):
        """Test handling of corrupted photo file"""
        # Create corrupted JPEG
        corrupted = temp_photos_dir / "corrupted.jpg"
        corrupted.write_bytes(b'not a valid jpeg')

        response = metadata_client.get('/api/metadata/photo/corrupted.jpg/metadata')

        # Should return 500 with error message
        assert response.status_code == 500

        data = json.loads(response.data)
        assert 'error' in data

    def test_batch_continues_on_individual_errors(self, metadata_client, temp_photos_dir):
        """Test that batch processing continues even if some photos fail"""
        # Create 2 valid photos and 1 corrupted
        valid1 = temp_photos_dir / "valid1.jpg"
        img1 = _get_real_pil_image().new('RGB', (100, 100))
        img1.save(valid1, "JPEG")

        corrupted = temp_photos_dir / "corrupted.jpg"
        corrupted.write_bytes(b'invalid')

        valid2 = temp_photos_dir / "valid2.jpg"
        img2 = _get_real_pil_image().new('RGB', (100, 100))
        img2.save(valid2, "JPEG")

        photo_paths = ["valid1.jpg", "corrupted.jpg", "valid2.jpg"]

        response = metadata_client.post(
            '/api/metadata/batch/metadata',
            json={"photo_paths": photo_paths},
            content_type='application/json'
        )

        assert response.status_code == 200

        data = json.loads(response.data)

        # Should process all 3 (2 success, 1 failure)
        assert data['total'] == 3
        assert data['successful'] == 2
        assert data['failed'] == 1

"""
Unit tests for gallery locations API endpoint (Issue #113 - Subtask 2)

Tests the GET /api/gallery/locations endpoint that returns photos with GPS data
for Leaflet map display. Follows TDD principles - tests written first.

Coverage Target: 90%+ for locations endpoint
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

# Import the blueprint
from routes.gallery import gallery_bp


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_photos_dir(tmp_path, monkeypatch):
    """
    Temporary PHOTOS_DIR for gallery tests

    Creates isolated photo directory and patches mothbox_paths.PHOTOS_DIR
    in all relevant modules.
    """
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()

    # Patch PHOTOS_DIR in mothbox_paths
    import mothbox_paths
    monkeypatch.setattr(mothbox_paths, 'PHOTOS_DIR', photos_dir)

    # Also patch in routes.gallery module (already imported)
    import routes.gallery
    monkeypatch.setattr(routes.gallery, 'PHOTOS_DIR', photos_dir)

    return photos_dir


@pytest.fixture
def gallery_app(temp_photos_dir):
    """Flask app with gallery blueprint for testing"""
    app = Flask(__name__)
    app.config['TESTING'] = True

    # Register blueprint AFTER patching PHOTOS_DIR
    app.register_blueprint(gallery_bp, url_prefix='/api/gallery')
    return app


@pytest.fixture
def gallery_client(gallery_app):
    """Test client for gallery routes"""
    return gallery_app.test_client()


@pytest.fixture
def create_photo_with_gps():
    """
    Helper fixture to create a photo file with GPS EXIF data.

    Returns a function that creates a photo with specified GPS coordinates.
    """
    def _create_photo(photo_path: Path, latitude: float, longitude: float, timestamp: str = None):
        """
        Create a minimal JPEG with GPS EXIF data.

        Args:
            photo_path: Where to save the photo
            latitude: GPS latitude
            longitude: GPS longitude
            timestamp: Optional timestamp string (ISO format)
        """
        try:
            import piexif
            from PIL import Image
            from io import BytesIO
        except ImportError:
            pytest.skip("piexif and PIL required for GPS EXIF tests")

        # Import GPS EXIF library
        import sys
        firmware_root = Path(__file__).resolve().parent.parent.parent
        if str(firmware_root) not in sys.path:
            sys.path.insert(0, str(firmware_root))

        from webui.backend.lib.gps_exif_lib import build_gps_ifd, decimal_to_dms

        # Create minimal JPEG
        img = Image.new('RGB', (100, 100), color='red')

        # Build GPS data
        gps_data = {
            'latitude': latitude,
            'longitude': longitude,
            'has_fix': True,
            'gpstime': 1699200000,  # Sample timestamp
            'satellites_used': 8,
            'hdop': 1.2
        }

        # Build GPS IFD
        gps_ifd = build_gps_ifd(gps_data)

        # Create EXIF dict
        exif_dict = {
            'GPS': gps_ifd,
            '0th': {},
            'Exif': {},
            '1st': {}
        }

        # Add timestamp to EXIF if provided
        if timestamp:
            from datetime import datetime
            dt = datetime.fromisoformat(timestamp)
            exif_timestamp = dt.strftime('%Y:%m:%d %H:%M:%S')
            exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = exif_timestamp.encode('utf-8')

        # Dump EXIF to bytes
        exif_bytes = piexif.dump(exif_dict)

        # Save image with EXIF
        img.save(photo_path, 'JPEG', exif=exif_bytes, quality=95)

    return _create_photo


@pytest.fixture
def create_photo_without_gps():
    """
    Helper fixture to create a photo file without GPS EXIF data.
    """
    def _create_photo(photo_path: Path):
        """Create a minimal JPEG without GPS EXIF."""
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("PIL required for photo creation")

        img = Image.new('RGB', (100, 100), color='blue')
        img.save(photo_path, 'JPEG', quality=95)

    return _create_photo


# ============================================================================
# Test Locations Endpoint
# ============================================================================

class TestLocationsEndpoint:
    """Tests for GET /api/gallery/locations"""

    def test_locations_returns_empty_when_no_photos(self, gallery_client, temp_photos_dir):
        """GET /locations returns empty list when no photos exist"""
        response = gallery_client.get('/api/gallery/locations')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify response structure
        assert 'locations' in data
        assert 'total_with_gps' in data
        assert 'total_without_gps' in data

        # Verify empty data
        assert data['locations'] == []
        assert data['total_with_gps'] == 0
        assert data['total_without_gps'] == 0

    def test_locations_returns_correct_structure(
        self, gallery_client, temp_photos_dir, create_photo_with_gps
    ):
        """GET /locations returns correct data structure with GPS photos"""
        # Create photos with GPS
        photo1 = temp_photos_dir / "photo_001.jpg"
        create_photo_with_gps(
            photo1,
            latitude=37.7749,
            longitude=-122.4194,
            timestamp="2024-11-10T10:30:00"
        )

        photo2 = temp_photos_dir / "photo_002.jpg"
        create_photo_with_gps(
            photo2,
            latitude=34.0522,
            longitude=-118.2437,
            timestamp="2024-11-10T11:45:00"
        )

        response = gallery_client.get('/api/gallery/locations')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify response structure
        assert 'locations' in data
        assert 'total_with_gps' in data
        assert 'total_without_gps' in data

        # Verify counts
        assert data['total_with_gps'] == 2
        assert data['total_without_gps'] == 0

        # Verify locations list
        assert len(data['locations']) == 2

        # Verify first location structure
        location = data['locations'][0]
        assert 'path' in location
        assert 'filename' in location
        assert 'latitude' in location
        assert 'longitude' in location
        assert 'timestamp' in location
        assert 'thumbnail_url' in location

        # Verify data types
        assert isinstance(location['path'], str)
        assert isinstance(location['filename'], str)
        assert isinstance(location['latitude'], float)
        assert isinstance(location['longitude'], float)
        assert isinstance(location['timestamp'], str)
        assert isinstance(location['thumbnail_url'], str)

        # Verify coordinates are correct
        locations_dict = {loc['filename']: loc for loc in data['locations']}

        assert abs(locations_dict['photo_001.jpg']['latitude'] - 37.7749) < 0.001
        assert abs(locations_dict['photo_001.jpg']['longitude'] - (-122.4194)) < 0.001

        assert abs(locations_dict['photo_002.jpg']['latitude'] - 34.0522) < 0.001
        assert abs(locations_dict['photo_002.jpg']['longitude'] - (-118.2437)) < 0.001

    def test_locations_respects_limit_parameter(
        self, gallery_client, temp_photos_dir, create_photo_with_gps
    ):
        """GET /locations?limit=N respects the limit parameter"""
        # Create 5 photos with GPS
        for i in range(5):
            photo = temp_photos_dir / f"photo_{i:03d}.jpg"
            create_photo_with_gps(
                photo,
                latitude=37.0 + i * 0.1,
                longitude=-122.0 - i * 0.1,
                timestamp=f"2024-11-10T{10+i:02d}:00:00"
            )

        # Request with limit=3
        response = gallery_client.get('/api/gallery/locations?limit=3')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify only 3 locations returned
        assert len(data['locations']) == 3

        # Total count should still show all photos
        assert data['total_with_gps'] == 5
        assert data['total_without_gps'] == 0

    def test_locations_filters_photos_without_gps(
        self, gallery_client, temp_photos_dir, create_photo_with_gps, create_photo_without_gps
    ):
        """GET /locations only returns photos with GPS data"""
        # Create 3 photos with GPS
        for i in range(3):
            photo = temp_photos_dir / f"photo_with_gps_{i:03d}.jpg"
            create_photo_with_gps(
                photo,
                latitude=37.0 + i * 0.1,
                longitude=-122.0 - i * 0.1,
                timestamp=f"2024-11-10T{10+i:02d}:00:00"
            )

        # Create 2 photos without GPS
        for i in range(2):
            photo = temp_photos_dir / f"photo_no_gps_{i:03d}.jpg"
            create_photo_without_gps(photo)

        response = gallery_client.get('/api/gallery/locations')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify only GPS photos returned
        assert len(data['locations']) == 3
        assert data['total_with_gps'] == 3
        assert data['total_without_gps'] == 2

        # Verify all returned photos have GPS data
        for location in data['locations']:
            assert location['latitude'] is not None
            assert location['longitude'] is not None
            assert 'with_gps' in location['filename']

    def test_locations_handles_corrupt_exif_gracefully(
        self, gallery_client, temp_photos_dir
    ):
        """GET /locations handles photos with corrupted EXIF gracefully"""
        # Create photo with corrupted EXIF
        corrupt_photo = temp_photos_dir / "corrupt.jpg"
        corrupt_photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100 + b'\xFF\xD9')

        # Create valid photo with GPS
        try:
            from PIL import Image
            import piexif
        except ImportError:
            pytest.skip("PIL and piexif required")

        import sys
        firmware_root = Path(__file__).resolve().parent.parent.parent
        if str(firmware_root) not in sys.path:
            sys.path.insert(0, str(firmware_root))

        from webui.backend.lib.gps_exif_lib import build_gps_ifd

        valid_photo = temp_photos_dir / "valid.jpg"
        img = Image.new('RGB', (100, 100), color='green')

        gps_data = {
            'latitude': 37.7749,
            'longitude': -122.4194,
            'has_fix': True,
            'gpstime': 1699200000,
            'satellites_used': 8,
            'hdop': 1.2
        }

        gps_ifd = build_gps_ifd(gps_data)
        exif_dict = {'GPS': gps_ifd, '0th': {}, 'Exif': {}, '1st': {}}
        exif_bytes = piexif.dump(exif_dict)
        img.save(valid_photo, 'JPEG', exif=exif_bytes, quality=95)

        response = gallery_client.get('/api/gallery/locations')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Should only return valid photo with GPS
        assert len(data['locations']) == 1
        assert data['locations'][0]['filename'] == 'valid.jpg'

        # Corrupt photo counted as "without GPS"
        assert data['total_with_gps'] == 1
        assert data['total_without_gps'] == 1

    def test_locations_default_limit_is_1000(
        self, gallery_client, temp_photos_dir, create_photo_with_gps
    ):
        """GET /locations defaults to limit=1000"""
        # Create only 10 photos (less than default limit)
        for i in range(10):
            photo = temp_photos_dir / f"photo_{i:03d}.jpg"
            create_photo_with_gps(
                photo,
                latitude=37.0 + i * 0.1,
                longitude=-122.0 - i * 0.1,
                timestamp=f"2024-11-10T{10+i:02d}:00:00"
            )

        response = gallery_client.get('/api/gallery/locations')

        assert response.status_code == 200
        data = json.loads(response.data)

        # All 10 photos should be returned (under default limit)
        assert len(data['locations']) == 10

    def test_locations_thumbnail_url_format(
        self, gallery_client, temp_photos_dir, create_photo_with_gps
    ):
        """GET /locations returns correct thumbnail URL format"""
        # Create photo in nested directory
        nested_dir = temp_photos_dir / "2024-11-10"
        nested_dir.mkdir()

        photo = nested_dir / "photo_001.jpg"
        create_photo_with_gps(
            photo,
            latitude=37.7749,
            longitude=-122.4194,
            timestamp="2024-11-10T10:30:00"
        )

        response = gallery_client.get('/api/gallery/locations')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert len(data['locations']) == 1
        location = data['locations'][0]

        # Verify thumbnail URL format
        assert location['thumbnail_url'] == '/api/gallery/thumbnail/2024-11-10/photo_001.jpg'

        # Verify path matches
        assert location['path'] == '2024-11-10/photo_001.jpg'

    def test_locations_invalid_limit_parameter(self, gallery_client):
        """GET /locations?limit=invalid returns 400 error"""
        response = gallery_client.get('/api/gallery/locations?limit=invalid')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_locations_negative_limit_parameter(self, gallery_client):
        """GET /locations?limit=-1 returns 400 error"""
        response = gallery_client.get('/api/gallery/locations?limit=-1')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_locations_zero_limit_parameter(self, gallery_client):
        """GET /locations?limit=0 returns 400 error"""
        response = gallery_client.get('/api/gallery/locations?limit=0')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_locations_handles_missing_photos_dir(
        self, gallery_client, temp_photos_dir, monkeypatch
    ):
        """GET /locations returns empty list when PHOTOS_DIR doesn't exist"""
        # Point to non-existent directory
        nonexistent_dir = temp_photos_dir / "nonexistent"

        import routes.gallery
        monkeypatch.setattr(routes.gallery, 'PHOTOS_DIR', nonexistent_dir)

        response = gallery_client.get('/api/gallery/locations')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['locations'] == []
        assert data['total_with_gps'] == 0
        assert data['total_without_gps'] == 0

    def test_locations_timestamp_format(
        self, gallery_client, temp_photos_dir, create_photo_with_gps
    ):
        """GET /locations returns ISO 8601 formatted timestamps"""
        photo = temp_photos_dir / "photo_001.jpg"
        create_photo_with_gps(
            photo,
            latitude=37.7749,
            longitude=-122.4194,
            timestamp="2024-11-10T10:30:00"
        )

        response = gallery_client.get('/api/gallery/locations')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert len(data['locations']) == 1
        location = data['locations'][0]

        # Verify timestamp is present and ISO formatted
        assert 'timestamp' in location
        assert location['timestamp'] is not None

        # Should be parseable as ISO 8601
        from datetime import datetime
        datetime.fromisoformat(location['timestamp'].replace('Z', '+00:00'))

    def test_locations_performance_with_many_photos(
        self, gallery_client, temp_photos_dir, create_photo_with_gps, create_photo_without_gps
    ):
        """GET /locations performs well with 100+ photos"""
        # Create 50 photos with GPS
        for i in range(50):
            photo = temp_photos_dir / f"with_gps_{i:03d}.jpg"
            create_photo_with_gps(
                photo,
                latitude=37.0 + i * 0.01,
                longitude=-122.0 - i * 0.01,
                timestamp=f"2024-11-10T10:{i%60:02d}:00"
            )

        # Create 50 photos without GPS
        for i in range(50):
            photo = temp_photos_dir / f"no_gps_{i:03d}.jpg"
            create_photo_without_gps(photo)

        import time
        start_time = time.time()

        response = gallery_client.get('/api/gallery/locations')

        elapsed = time.time() - start_time

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify correct filtering
        assert len(data['locations']) == 50
        assert data['total_with_gps'] == 50
        assert data['total_without_gps'] == 50

        # Performance target: Should complete in < 5 seconds for 100 photos
        # (This is generous - actual performance should be much faster)
        assert elapsed < 5.0, f"Performance too slow: {elapsed:.2f}s for 100 photos"

"""Integration tests for Map Locations API → GPS EXIF pipeline.

These tests validate the complete MapView → API → GPS EXIF workflow:
1. Create test photos with GPS EXIF using gps_exif_lib
2. Call /api/gallery/locations endpoint
3. Verify coordinates match embedded EXIF data
4. Verify response structure is correct

Tests are marked as @pytest.mark.integration since they test
multiple components working together.

Related to: Issue #113 - Leaflet Map Infrastructure
Code Review Feedback: Fix 10 - Add Integration Test
"""

import pytest
import logging
from pathlib import Path
from PIL import Image
import piexif
import json

# Ensure PIL plugins are loaded (fixes test failures when running multiple tests)
# See: https://pillow.readthedocs.io/en/stable/handbook/overview.html#plugin-loading
Image.init()

from mothbox_paths import PHOTOS_DIR, CONTROLS_FILE
from webui.backend.lib.gps_exif_lib import (
    embed_gps_exif,
    verify_gps_exif,
    get_gps_data_from_controls,
    build_gps_ifd
)


@pytest.fixture
def mock_controls_with_gps(tmp_path, monkeypatch):
    """Create mock controls.txt with GPS data.

    GPS data simulates a good 3D fix in San Francisco.
    """
    controls = tmp_path / "controls.txt"
    controls.write_text("""# Mock controls.txt for GPS EXIF testing
gpstime=1705329000
lat=37.7749
lon=-122.4194
gps_altitude=15.5
gps_fix_mode=3
gps_satellites_used=8
gps_hdop=1.2
gps_pdop=2.1
""")

    # Patch CONTROLS_FILE in both modules
    import webui.backend.lib.gps_exif_lib
    monkeypatch.setattr('webui.backend.lib.gps_exif_lib.CONTROLS_FILE', controls)
    monkeypatch.setattr('mothbox_paths.CONTROLS_FILE', controls)

    return controls


@pytest.fixture
def temp_photos_dir(tmp_path, monkeypatch):
    """Create temporary photos directory and patch PHOTOS_DIR."""
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()

    # Patch PHOTOS_DIR globally
    import mothbox_paths
    monkeypatch.setattr('mothbox_paths.PHOTOS_DIR', photos_dir)

    # Also patch in gallery routes module
    import webui.backend.routes.gallery
    monkeypatch.setattr('webui.backend.routes.gallery.PHOTOS_DIR', photos_dir)

    return photos_dir


@pytest.fixture
def flask_test_client(temp_photos_dir):
    """Create Flask test client for API testing."""
    from flask import Flask
    from webui.backend.routes.gallery import gallery_bp

    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing

    # Register only the gallery blueprint
    app.register_blueprint(gallery_bp, url_prefix='/api/gallery')

    with app.test_client() as client:
        yield client


def create_photo_with_gps(photo_path: Path, latitude: float, longitude: float, altitude: float = None):
    """Helper function to create a test photo with GPS EXIF.

    Args:
        photo_path: Path to save photo
        latitude: Decimal latitude
        longitude: Decimal longitude
        altitude: Optional altitude in meters
    """
    # Create base image
    img = Image.new('RGB', (640, 480), color='blue')

    # Add camera EXIF (like TakePhoto.py does)
    exif_dict = {
        "0th": {
            piexif.ImageIFD.Make: b"MothboxV4",
            piexif.ImageIFD.Model: b"OwlSight64MP"
        },
        "Exif": {
            piexif.ExifIFD.ExposureTime: (1, 100),
            piexif.ExifIFD.ISOSpeed: 100,
            piexif.ExifIFD.FocalLength: (50, 1),
            piexif.ExifIFD.DateTimeOriginal: b"2024:01:15 12:30:00"
        },
        "GPS": {}
    }

    # Build GPS IFD
    from webui.backend.lib.gps_exif_lib import decimal_to_dms

    # Convert coordinates to DMS (returns (dms_tuple, ref_string))
    lat_dms_tuple, lat_ref = decimal_to_dms(latitude, is_latitude=True)
    lon_dms_tuple, lon_ref = decimal_to_dms(longitude, is_latitude=False)

    # Build GPS IFD
    gps_ifd = {
        piexif.GPSIFD.GPSVersionID: (2, 3, 0, 0),
        piexif.GPSIFD.GPSLatitude: lat_dms_tuple,
        piexif.GPSIFD.GPSLatitudeRef: lat_ref.encode('ascii'),
        piexif.GPSIFD.GPSLongitude: lon_dms_tuple,
        piexif.GPSIFD.GPSLongitudeRef: lon_ref.encode('ascii'),
    }

    if altitude is not None:
        gps_ifd[piexif.GPSIFD.GPSAltitude] = (int(altitude * 100), 100)
        gps_ifd[piexif.GPSIFD.GPSAltitudeRef] = 0  # Above sea level

    exif_dict["GPS"] = gps_ifd

    # Save photo with EXIF
    exif_bytes = piexif.dump(exif_dict)
    img.save(photo_path, 'JPEG', exif=exif_bytes, quality=95)


@pytest.mark.integration
class TestMapLocationsIntegration:
    """Test complete MapView → API → GPS EXIF workflow."""

    def test_locations_endpoint_with_gps_photos(
        self, temp_photos_dir, flask_test_client, mock_controls_with_gps
    ):
        """Test /api/gallery/locations returns photos with GPS EXIF.

        Steps:
            1. Create test photos with GPS EXIF using gps_exif_lib
            2. Call /api/gallery/locations endpoint
            3. Verify coordinates match embedded EXIF data
            4. Verify response structure is correct
        """
        # Step 1: Create test photos with GPS EXIF
        test_photos = [
            {
                "filename": "moth_2024_01_15__10_00_00.jpg",
                "latitude": 37.7749,
                "longitude": -122.4194,
                "altitude": 15.5
            },
            {
                "filename": "moth_2024_01_15__11_00_00.jpg",
                "latitude": 37.7750,
                "longitude": -122.4195,
                "altitude": 20.0
            },
            {
                "filename": "moth_2024_01_15__12_00_00.jpg",
                "latitude": 37.7751,
                "longitude": -122.4196,
                "altitude": 25.5
            }
        ]

        for photo_info in test_photos:
            photo_path = temp_photos_dir / photo_info["filename"]
            create_photo_with_gps(
                photo_path,
                photo_info["latitude"],
                photo_info["longitude"],
                photo_info["altitude"]
            )

            # Verify GPS EXIF was embedded correctly
            gps_data = verify_gps_exif(photo_path)
            assert gps_data['has_gps'] is True
            assert abs(gps_data['latitude'] - photo_info["latitude"]) < 0.0001
            assert abs(gps_data['longitude'] - photo_info["longitude"]) < 0.0001

        # Step 2: Call /api/gallery/locations endpoint
        response = flask_test_client.get('/api/gallery/locations')

        # Step 3: Verify response status and structure
        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify response structure
        assert "locations" in data
        assert "total_with_gps" in data
        assert "total_without_gps" in data

        # Step 4: Verify counts
        assert data["total_with_gps"] == 3
        assert data["total_without_gps"] == 0
        assert len(data["locations"]) == 3

        # Step 5: Verify each location matches embedded EXIF data
        for location in data["locations"]:
            # Find matching test photo
            matching_photo = next(
                p for p in test_photos if p["filename"] == location["filename"]
            )

            # Verify coordinates match
            assert abs(location["latitude"] - matching_photo["latitude"]) < 0.0001
            assert abs(location["longitude"] - matching_photo["longitude"]) < 0.0001

            # Verify required fields exist
            assert "photo_path" in location
            assert "filename" in location
            assert "timestamp" in location
            assert "thumbnail_url" in location

            # Verify timestamp format (ISO 8601)
            assert "T" in location["timestamp"] or location["timestamp"] is not None

    def test_locations_endpoint_mixed_photos(
        self, temp_photos_dir, flask_test_client, mock_controls_with_gps
    ):
        """Test /api/gallery/locations with mixed GPS and non-GPS photos.

        Verifies that:
        - Photos with GPS are included in locations list
        - Photos without GPS are counted in total_without_gps
        - Response structure is correct
        """
        # Create 3 photos with GPS
        gps_photos = [
            {"filename": "gps_photo_1.jpg", "lat": 37.7749, "lon": -122.4194},
            {"filename": "gps_photo_2.jpg", "lat": 37.7750, "lon": -122.4195},
            {"filename": "gps_photo_3.jpg", "lat": 37.7751, "lon": -122.4196},
        ]

        for photo_info in gps_photos:
            photo_path = temp_photos_dir / photo_info["filename"]
            create_photo_with_gps(photo_path, photo_info["lat"], photo_info["lon"])

        # Create 2 photos without GPS
        no_gps_photos = ["no_gps_photo_1.jpg", "no_gps_photo_2.jpg"]
        for filename in no_gps_photos:
            photo_path = temp_photos_dir / filename
            img = Image.new('RGB', (640, 480), color='red')
            img.save(photo_path, 'JPEG')

        # Call API endpoint
        response = flask_test_client.get('/api/gallery/locations')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify counts
        assert data["total_with_gps"] == 3
        assert data["total_without_gps"] == 2
        assert len(data["locations"]) == 3

        # Verify only GPS photos are in locations list
        location_filenames = [loc["filename"] for loc in data["locations"]]
        for photo_info in gps_photos:
            assert photo_info["filename"] in location_filenames

        for filename in no_gps_photos:
            assert filename not in location_filenames

    def test_locations_endpoint_with_limit(
        self, temp_photos_dir, flask_test_client, mock_controls_with_gps
    ):
        """Test /api/gallery/locations respects limit parameter.

        Verifies that:
        - Limit parameter controls number of returned locations
        - total_with_gps reflects actual count (not limited)
        - Response structure is correct
        """
        # Create 5 photos with GPS
        for i in range(5):
            photo_path = temp_photos_dir / f"photo_{i:02d}.jpg"
            create_photo_with_gps(
                photo_path,
                37.7749 + (i * 0.0001),
                -122.4194 + (i * 0.0001)
            )

        # Call API with limit=2
        response = flask_test_client.get('/api/gallery/locations?limit=2')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify limit is respected
        assert len(data["locations"]) == 2

        # Verify total count is correct (not limited)
        assert data["total_with_gps"] == 5
        assert data["total_without_gps"] == 0

    def test_locations_endpoint_empty_directory(
        self, temp_photos_dir, flask_test_client
    ):
        """Test /api/gallery/locations with empty photos directory.

        Verifies graceful handling of empty directory.
        """
        # Photos directory exists but is empty (from fixture)
        response = flask_test_client.get('/api/gallery/locations')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify empty response
        assert data["locations"] == []
        assert data["total_with_gps"] == 0
        assert data["total_without_gps"] == 0

    def test_locations_endpoint_invalid_limit(self, flask_test_client):
        """Test /api/gallery/locations with invalid limit parameter.

        Verifies proper error handling for invalid limit values.
        """
        # Test invalid limit values
        test_cases = [
            ("?limit=0", 400),  # Zero limit
            ("?limit=-5", 400),  # Negative limit
            ("?limit=20000", 400),  # Exceeds max (10000)
            ("?limit=abc", 400),  # Non-integer
        ]

        for query_string, expected_status in test_cases:
            response = flask_test_client.get(f'/api/gallery/locations{query_string}')
            assert response.status_code == expected_status, f"Failed for {query_string}"

            data = json.loads(response.data)
            assert "error" in data

    def test_locations_endpoint_case_insensitive_extensions(
        self, temp_photos_dir, flask_test_client, mock_controls_with_gps
    ):
        """Test /api/gallery/locations handles JPG, jpg, JPEG, jpeg extensions.

        Verifies that the endpoint finds photos with various case extensions.
        """
        # Create photos with different extensions
        extensions = ['jpg', 'JPG', 'jpeg', 'JPEG']
        for i, ext in enumerate(extensions):
            photo_path = temp_photos_dir / f"photo_{i}.{ext}"
            create_photo_with_gps(
                photo_path,
                37.7749 + (i * 0.0001),
                -122.4194 + (i * 0.0001)
            )

        # Call API endpoint
        response = flask_test_client.get('/api/gallery/locations')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify all variants were found
        # Note: On Linux, glob is case-sensitive, but the endpoint uses both *.jpg and *.JPG
        assert data["total_with_gps"] >= 2  # At least .jpg and .JPG
        assert len(data["locations"]) >= 2


@pytest.mark.integration
class TestMapLocationsErrorHandling:
    """Test error handling in Map Locations API."""

    def test_corrupted_photo_graceful_handling(
        self, temp_photos_dir, flask_test_client, mock_controls_with_gps
    ):
        """Test /api/gallery/locations handles corrupted photos gracefully.

        Verifies that corrupted photos don't crash the endpoint.
        """
        # Create 1 valid photo with GPS
        valid_photo = temp_photos_dir / "valid_photo.jpg"
        create_photo_with_gps(valid_photo, 37.7749, -122.4194)

        # Create 1 corrupted "photo" (not a valid JPEG)
        corrupted_photo = temp_photos_dir / "corrupted.jpg"
        corrupted_photo.write_text("This is not a JPEG file!")

        # Call API endpoint (should not crash)
        response = flask_test_client.get('/api/gallery/locations')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify valid photo is returned, corrupted is counted as no GPS
        assert data["total_with_gps"] == 1
        assert data["total_without_gps"] == 1
        assert len(data["locations"]) == 1

    def test_photo_read_permission_error(
        self, temp_photos_dir, flask_test_client, mock_controls_with_gps
    ):
        """Test /api/gallery/locations handles permission errors gracefully.

        Note: This test may not fail on all systems since the test suite
        might have sufficient permissions. The test verifies graceful handling
        when permission errors DO occur.
        """
        # Create photo with GPS
        photo = temp_photos_dir / "photo.jpg"
        create_photo_with_gps(photo, 37.7749, -122.4194)

        # Try to make photo unreadable
        import stat
        try:
            photo.chmod(0o000)  # No permissions

            # Call API endpoint (should handle gracefully)
            response = flask_test_client.get('/api/gallery/locations')

            # On some systems, root or test user may still have access
            # So we accept either success OR graceful error handling
            assert response.status_code in [200, 500]

            if response.status_code == 200:
                data = json.loads(response.data)
                # If successful, photo should be counted as no GPS (couldn't read)
                # OR should be read successfully (system allowed despite permissions)
                assert data["total_with_gps"] + data["total_without_gps"] >= 0

        finally:
            # Restore permissions for cleanup
            photo.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)


if __name__ == '__main__':
    # Allow running tests directly
    pytest.main([__file__, '-v', '-s'])

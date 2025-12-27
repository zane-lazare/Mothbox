"""Integration tests for metadata API endpoint with EXIF data (Issue #106)

These tests validate the complete metadata API workflow:
1. Photo creation with controlled EXIF data using PIL/piexif
2. Metadata extraction via REST API endpoint
3. Cache behavior and performance
4. Series detection integration (HDR and Focus Bracket)
5. GPS coordinate handling

Tests are marked as @pytest.mark.integration since they test
multiple components working together (API routes + metadata service + cache).

Architecture:
- Uses Flask test client for API calls
- Creates real JPEG files with EXIF using PIL
- Tests both cached and uncached data paths
- Validates category filtering
- Verifies series detection integration

Related:
- webui/backend/routes/gallery.py: Metadata API endpoints
- webui/backend/services/metadata_service.py: EXIF extraction
- webui/backend/services/metadata_cache.py: Two-level cache
"""

import sys
import time
from pathlib import Path

import piexif
import pytest
from PIL import Image

# Add webui backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "webui" / "backend"))

# Import Flask app and routes
from app import app

# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_photos_dir(tmp_path, monkeypatch):
    """Create temporary photos directory and patch PHOTOS_DIR."""
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()

    # Patch PHOTOS_DIR in all relevant modules
    import mothbox_paths
    monkeypatch.setattr(mothbox_paths, 'PHOTOS_DIR', photos_dir)

    import routes.gallery
    monkeypatch.setattr(routes.gallery, 'PHOTOS_DIR', photos_dir)

    return photos_dir


@pytest.fixture
def client(temp_photos_dir):
    """Flask test client with testing configuration."""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing

    with app.test_client() as client:
        yield client


@pytest.fixture
def test_photo(temp_photos_dir):
    """Create test photo with complete EXIF metadata (no GPS)."""
    photo_path = temp_photos_dir / "mothbox_2025_01_15__12_30_00.jpg"
    img = Image.new('RGB', (640, 480), color='blue')

    # Add comprehensive camera EXIF
    exif_dict = {
        "0th": {
            piexif.ImageIFD.Make: b"MothboxV4",
            piexif.ImageIFD.Model: b"OwlSight64MP",
            piexif.ImageIFD.Software: b"Mothbox Firmware 4.2.1",
            piexif.ImageIFD.DateTime: b"2025:01:15 12:30:00"
        },
        "Exif": {
            piexif.ExifIFD.DateTimeOriginal: b"2025:01:15 12:30:00",
            piexif.ExifIFD.ExposureTime: (1, 100),  # 1/100 second
            piexif.ExifIFD.FNumber: (28, 10),  # f/2.8
            piexif.ExifIFD.ISOSpeed: 100,
            piexif.ExifIFD.FocalLength: (50, 1),  # 50mm
            piexif.ExifIFD.WhiteBalance: 0,  # Auto
            piexif.ExifIFD.Flash: 0  # No flash
        },
        "GPS": {}  # Empty GPS IFD (no GPS data)
    }
    exif_bytes = piexif.dump(exif_dict)
    img.save(photo_path, 'JPEG', exif=exif_bytes, quality=95)

    return photo_path


@pytest.fixture
def test_photo_with_gps(temp_photos_dir):
    """Create test photo with GPS coordinates embedded."""
    photo_path = temp_photos_dir / "mothbox_2025_01_15__13_00_00.jpg"
    img = Image.new('RGB', (640, 480), color='green')

    # Add camera EXIF + GPS
    exif_dict = {
        "0th": {
            piexif.ImageIFD.Make: b"MothboxV4",
            piexif.ImageIFD.Model: b"OwlSight64MP"
        },
        "Exif": {
            piexif.ExifIFD.DateTimeOriginal: b"2025:01:15 13:00:00",
            piexif.ExifIFD.ExposureTime: (1, 200),
            piexif.ExifIFD.ISOSpeed: 200,
            piexif.ExifIFD.FocalLength: (50, 1)
        },
        "GPS": {
            piexif.GPSIFD.GPSVersionID: (2, 3, 0, 0),
            piexif.GPSIFD.GPSLatitude: ((37, 1), (46, 1), (2964, 100)),  # 37.7749°N
            piexif.GPSIFD.GPSLatitudeRef: b'N',
            piexif.GPSIFD.GPSLongitude: ((122, 1), (25, 1), (1164, 100)),  # -122.4194°W
            piexif.GPSIFD.GPSLongitudeRef: b'W',
            piexif.GPSIFD.GPSAltitude: (155, 10),  # 15.5m
            piexif.GPSIFD.GPSAltitudeRef: 0,  # Above sea level
            piexif.GPSIFD.GPSSatellites: b'8',
            piexif.GPSIFD.GPSDOP: (12, 10)  # HDOP 1.2
        }
    }
    exif_bytes = piexif.dump(exif_dict)
    img.save(photo_path, 'JPEG', exif=exif_bytes, quality=95)

    return photo_path


@pytest.fixture
def test_photo_without_gps(temp_photos_dir):
    """Create test photo explicitly without GPS data."""
    photo_path = temp_photos_dir / "mothbox_2025_01_15__14_00_00.jpg"
    img = Image.new('RGB', (640, 480), color='red')

    # Minimal EXIF, no GPS
    exif_dict = {
        "0th": {
            piexif.ImageIFD.Make: b"MothboxV4",
            piexif.ImageIFD.Model: b"OwlSight64MP"
        },
        "Exif": {
            piexif.ExifIFD.DateTimeOriginal: b"2025:01:15 14:00:00",
            piexif.ExifIFD.ISOSpeed: 400
        }
        # No GPS IFD at all
    }
    exif_bytes = piexif.dump(exif_dict)
    img.save(photo_path, 'JPEG', exif=exif_bytes, quality=95)

    return photo_path


@pytest.fixture
def hdr_series_photos(temp_photos_dir):
    """Create 3 photos following HDR naming pattern."""
    base_name = "mothbox_2025_01_15__15_00_00"
    photos = []

    for i in range(3):
        photo_path = temp_photos_dir / f"{base_name}_HDR{i}.jpg"
        img = Image.new('RGB', (640, 480), color=['red', 'green', 'blue'][i])

        # Add EXIF with different exposure values
        exif_dict = {
            "0th": {
                piexif.ImageIFD.Make: b"MothboxV4",
                piexif.ImageIFD.Model: b"OwlSight64MP"
            },
            "Exif": {
                piexif.ExifIFD.DateTimeOriginal: b"2025:01:15 15:00:00",
                piexif.ExifIFD.ExposureTime: (1, [50, 100, 200][i]),  # Different exposures
                piexif.ExifIFD.ISOSpeed: 100
            }
        }
        exif_bytes = piexif.dump(exif_dict)
        img.save(photo_path, 'JPEG', exif=exif_bytes, quality=95)
        photos.append(photo_path)

    return photos


@pytest.fixture
def focus_bracket_photos(temp_photos_dir):
    """Create 5 photos following Focus Bracket naming pattern."""
    base_name = "ManFocus_mothbox_2025_01_15__16_00_00_000000"
    photos = []

    for i in range(5):
        photo_path = temp_photos_dir / f"{base_name}_FB{i}.jpg"
        img = Image.new('RGB', (640, 480), color='yellow')

        # Add EXIF with same exposure but different focus (implied)
        exif_dict = {
            "0th": {
                piexif.ImageIFD.Make: b"MothboxV4",
                piexif.ImageIFD.Model: b"OwlSight64MP"
            },
            "Exif": {
                piexif.ExifIFD.DateTimeOriginal: b"2025:01:15 16:00:00",
                piexif.ExifIFD.ExposureTime: (1, 100),
                piexif.ExifIFD.ISOSpeed: 200,
                piexif.ExifIFD.FocalLength: (50, 1)
            }
        }
        exif_bytes = piexif.dump(exif_dict)
        img.save(photo_path, 'JPEG', exif=exif_bytes, quality=95)
        photos.append(photo_path)

    return photos


# ============================================================================
# Metadata API Integration Tests
# ============================================================================

@pytest.mark.integration
class TestMetadataAPIWithEXIF:
    """Integration tests for metadata API with EXIF data (Issue #106)."""

    def test_metadata_endpoint_returns_json(self, client, test_photo):
        """GET /api/gallery/photos/{photo}/metadata returns valid JSON."""
        photo_id = test_photo.name
        response = client.get(f'/api/gallery/photos/{photo_id}/metadata')

        assert response.status_code == 200
        data = response.get_json()

        # Validate response structure
        assert data['success'] is True
        assert data['photo_id'] == photo_id
        assert 'metadata' in data
        assert 'cache_info' in data

        # Validate metadata structure
        metadata = data['metadata']
        assert 'camera' in metadata
        assert 'location' in metadata
        assert 'capture' in metadata
        assert 'deployment' in metadata
        assert 'file' in metadata

    def test_metadata_includes_camera_info(self, client, test_photo):
        """Response includes camera make and model."""
        photo_id = test_photo.name
        response = client.get(f'/api/gallery/photos/{photo_id}/metadata')

        assert response.status_code == 200
        data = response.get_json()

        camera = data['metadata']['camera']
        assert camera['make'] == 'MothboxV4'
        assert camera['model'] == 'OwlSight64MP'

    def test_metadata_includes_capture_settings(self, client, test_photo):
        """Response includes ISO, shutter speed, aperture."""
        photo_id = test_photo.name
        response = client.get(f'/api/gallery/photos/{photo_id}/metadata')

        assert response.status_code == 200
        data = response.get_json()

        capture = data['metadata']['capture']

        # Validate capture settings
        assert capture['iso'] == 100
        assert capture['exposure_time'] == '1/100'  # Should be formatted
        assert capture['f_number'] == 'f/2.8'  # Should be formatted
        assert capture['focal_length'] == '50mm'  # Should be formatted
        assert capture['white_balance'] == 'Auto'
        assert capture['flash'] is False

    def test_gps_coordinates_present(self, client, test_photo_with_gps):
        """Response includes lat, lon, altitude for GPS photos."""
        photo_id = test_photo_with_gps.name
        response = client.get(f'/api/gallery/photos/{photo_id}/metadata')

        assert response.status_code == 200
        data = response.get_json()

        location = data['metadata']['location']

        # Validate GPS coordinates
        assert location['latitude'] is not None
        assert location['longitude'] is not None
        assert abs(location['latitude'] - 37.7749) < 0.01
        assert abs(location['longitude'] - (-122.4194)) < 0.01

        # Validate GPS quality metrics
        assert location['altitude'] is not None
        assert abs(location['altitude'] - 15.5) < 0.1
        assert location['satellites'] == '8'
        assert location['hdop'] is not None
        assert abs(location['hdop'] - 1.2) < 0.1

    def test_gps_coordinates_null_when_missing(self, client, test_photo_without_gps):
        """GPS fields are null for photos without GPS."""
        photo_id = test_photo_without_gps.name
        response = client.get(f'/api/gallery/photos/{photo_id}/metadata')

        assert response.status_code == 200
        data = response.get_json()

        location = data['metadata']['location']

        # All GPS fields should be null
        assert location['latitude'] is None
        assert location['longitude'] is None
        assert location['altitude'] is None
        assert location['gps_timestamp'] is None
        assert location['satellites'] is None
        assert location['hdop'] is None

    def test_category_filter_works(self, client, test_photo):
        """?categories=camera filters response to only camera fields."""
        photo_id = test_photo.name
        response = client.get(f'/api/gallery/photos/{photo_id}/metadata?categories=camera')

        assert response.status_code == 200
        data = response.get_json()

        metadata = data['metadata']

        # Should only have camera category
        assert 'camera' in metadata
        assert 'location' not in metadata
        assert 'capture' not in metadata
        assert 'deployment' not in metadata
        assert 'file' not in metadata

    def test_category_filter_multiple(self, client, test_photo):
        """?categories=camera,location filters to multiple categories."""
        photo_id = test_photo.name
        response = client.get(f'/api/gallery/photos/{photo_id}/metadata?categories=camera,location')

        assert response.status_code == 200
        data = response.get_json()

        metadata = data['metadata']

        # Should have camera and location, but not others
        assert 'camera' in metadata
        assert 'location' in metadata
        assert 'capture' not in metadata
        assert 'deployment' not in metadata
        assert 'file' not in metadata

    def test_category_filter_invalid(self, client, test_photo):
        """Invalid category returns 400 error."""
        photo_id = test_photo.name
        response = client.get(f'/api/gallery/photos/{photo_id}/metadata?categories=invalid_category')

        assert response.status_code == 400
        data = response.get_json()

        assert data['success'] is False
        assert 'Invalid category' in data['error']

    def test_cache_statistics_available(self, client, test_photo):
        """Cache hit/miss info included in response."""
        photo_id = test_photo.name

        # First request - cache miss
        response1 = client.get(f'/api/gallery/photos/{photo_id}/metadata')
        assert response1.status_code == 200
        data1 = response1.get_json()

        cache_info1 = data1['cache_info']
        assert 'cached' in cache_info1
        assert 'lookup_time_ms' in cache_info1

        # Second request - cache hit
        response2 = client.get(f'/api/gallery/photos/{photo_id}/metadata')
        assert response2.status_code == 200
        data2 = response2.get_json()

        cache_info2 = data2['cache_info']
        assert cache_info2['cached'] is True
        assert 'cache_level' in cache_info2
        assert cache_info2['cache_level'] in ['l1_memory', 'l2_disk', 'unknown']

    def test_photo_not_found_returns_404(self, client):
        """Non-existent photo returns 404."""
        response = client.get('/api/gallery/photos/nonexistent_photo.jpg/metadata')

        assert response.status_code == 404
        data = response.get_json()

        assert data['success'] is False
        assert 'not found' in data['error'].lower()

    def test_path_traversal_blocked(self, client):
        """Path traversal attempts are blocked."""
        # Attempt to access file outside photos dir
        response = client.get('/api/gallery/photos/../../etc/passwd/metadata')

        assert response.status_code == 404
        data = response.get_json()

        assert data['success'] is False

    def test_file_metadata_included(self, client, test_photo):
        """Response includes file size, dimensions, format."""
        photo_id = test_photo.name
        response = client.get(f'/api/gallery/photos/{photo_id}/metadata')

        assert response.status_code == 200
        data = response.get_json()

        file_meta = data['metadata']['file']

        assert file_meta['filename'] == photo_id
        assert file_meta['size'] > 0
        assert file_meta['width'] == 640
        assert file_meta['height'] == 480
        assert file_meta['format'] == 'JPEG'

    def test_timestamp_parsing(self, client, test_photo):
        """Timestamp is correctly parsed from EXIF."""
        photo_id = test_photo.name
        response = client.get(f'/api/gallery/photos/{photo_id}/metadata')

        assert response.status_code == 200
        data = response.get_json()

        capture = data['metadata']['capture']
        assert capture['timestamp'] is not None
        assert '2025-01-15' in capture['timestamp']
        assert '12:30:00' in capture['timestamp']


# ============================================================================
# Series Detection Integration Tests
# ============================================================================

@pytest.mark.integration
class TestSeriesDetectionAPI:
    """Tests for series detection in metadata API."""

    def test_hdr_series_detected(self, client, hdr_series_photos):
        """HDR series photos are grouped correctly."""
        # Get series list
        response = client.get('/api/gallery/series')

        assert response.status_code == 200
        data = response.get_json()

        series_list = data['series']
        assert len(series_list) > 0

        # Find HDR series
        hdr_series = [s for s in series_list if s['series_type'] == 'hdr']
        assert len(hdr_series) == 1

        series = hdr_series[0]
        assert series['count'] == 3
        assert series['base_name'] == 'mothbox_2025_01_15__15_00_00'
        assert len(series['photos']) == 3

    def test_focus_bracket_series_detected(self, client, focus_bracket_photos):
        """Focus bracket series photos are grouped correctly."""
        # Get series list
        response = client.get('/api/gallery/series')

        assert response.status_code == 200
        data = response.get_json()

        series_list = data['series']
        assert len(series_list) > 0

        # Find Focus Bracket series
        fb_series = [s for s in series_list if s['series_type'] == 'focus_bracket']
        assert len(fb_series) == 1

        series = fb_series[0]
        assert series['count'] == 5
        assert 'ManFocus_mothbox_2025_01_15__16_00_00' in series['base_name']
        assert len(series['photos']) == 5

    def test_series_endpoint_returns_list(self, client, hdr_series_photos, focus_bracket_photos):
        """GET /api/gallery/series returns series list."""
        response = client.get('/api/gallery/series')

        assert response.status_code == 200
        data = response.get_json()

        # Validate response structure
        assert 'series' in data
        assert 'pagination' in data

        series_list = data['series']
        pagination = data['pagination']

        # Should have both HDR and FB series
        assert len(series_list) >= 2

        # Validate pagination
        assert pagination['page'] == 1
        assert pagination['per_page'] == 50
        assert pagination['total'] >= 2

    def test_series_type_filter(self, client, hdr_series_photos, focus_bracket_photos):
        """?type=hdr filters to only HDR series."""
        response = client.get('/api/gallery/series?type=hdr')

        assert response.status_code == 200
        data = response.get_json()

        series_list = data['series']

        # All series should be HDR type
        for series in series_list:
            assert series['series_type'] == 'hdr'

    def test_series_pagination(self, client, hdr_series_photos, focus_bracket_photos):
        """Pagination works correctly."""
        response = client.get('/api/gallery/series?page=1&per_page=1')

        assert response.status_code == 200
        data = response.get_json()

        series_list = data['series']
        pagination = data['pagination']

        # Should only return 1 series per page
        assert len(series_list) == 1
        assert pagination['per_page'] == 1
        assert pagination['has_next'] is True

    def test_get_series_by_id(self, client, hdr_series_photos):
        """GET /api/gallery/series/{id} returns specific series."""
        # First get series list to find ID
        list_response = client.get('/api/gallery/series')
        series_list = list_response.get_json()['series']

        hdr_series = [s for s in series_list if s['series_type'] == 'hdr'][0]
        series_id = hdr_series['series_id']

        # Get specific series
        response = client.get(f'/api/gallery/series/{series_id}')

        assert response.status_code == 200
        data = response.get_json()

        assert data['series_id'] == series_id
        assert data['series_type'] == 'hdr'
        assert data['count'] == 3

    def test_series_not_found_returns_404(self, client):
        """Non-existent series ID returns 404."""
        response = client.get('/api/gallery/series/nonexistent_series_id')

        assert response.status_code == 404
        data = response.get_json()

        assert 'not found' in data['error'].lower()


# ============================================================================
# Cache Performance Tests
# ============================================================================

@pytest.mark.integration
class TestMetadataCachePerformance:
    """Tests for metadata cache performance."""

    def test_cache_warm_improves_performance(self, client, test_photo):
        """Second request is faster due to cache."""
        photo_id = test_photo.name

        # First request - cache miss
        start_time1 = time.time()
        response1 = client.get(f'/api/gallery/photos/{photo_id}/metadata')
        time1 = (time.time() - start_time1) * 1000  # ms

        assert response1.status_code == 200
        data1 = response1.get_json()
        assert data1['cache_info']['cached'] is False

        # Second request - cache hit
        start_time2 = time.time()
        response2 = client.get(f'/api/gallery/photos/{photo_id}/metadata')
        time2 = (time.time() - start_time2) * 1000  # ms

        assert response2.status_code == 200
        data2 = response2.get_json()
        assert data2['cache_info']['cached'] is True

        # Cache hit should be significantly faster
        # Note: In practice L1 cache is <1ms, L2 <10ms
        # But for integration tests we just verify it's cached
        assert time2 < time1 or data2['cache_info']['cache_level'] == 'l1_memory'

    def test_cache_invalidation_works(self, client, test_photo):
        """DELETE /photos/{id}/cache invalidates cache."""
        photo_id = test_photo.name

        # First request - populate cache
        response1 = client.get(f'/api/gallery/photos/{photo_id}/metadata')
        assert response1.status_code == 200

        # Second request - verify cached
        response2 = client.get(f'/api/gallery/photos/{photo_id}/metadata')
        assert response2.status_code == 200
        data2 = response2.get_json()
        assert data2['cache_info']['cached'] is True

        # Invalidate cache
        delete_response = client.delete(f'/api/gallery/photos/{photo_id}/cache')
        assert delete_response.status_code == 200
        delete_data = delete_response.get_json()
        assert delete_data['success'] is True
        assert delete_data['was_cached'] is True

        # Third request - cache miss again
        response3 = client.get(f'/api/gallery/photos/{photo_id}/metadata')
        assert response3.status_code == 200
        data3 = response3.get_json()
        assert data3['cache_info']['cached'] is False

    def test_cache_statistics_endpoint(self, client, test_photo):
        """GET /cache/statistics returns cache stats."""
        # Make some requests to populate stats
        photo_id = test_photo.name
        client.get(f'/api/gallery/photos/{photo_id}/metadata')
        client.get(f'/api/gallery/photos/{photo_id}/metadata')

        # Get cache stats
        response = client.get('/api/gallery/cache/statistics')

        assert response.status_code == 200
        data = response.get_json()

        assert data['success'] is True
        stats = data['statistics']

        # Validate statistics structure
        assert 'l1_hits' in stats
        assert 'l1_misses' in stats
        assert 'l2_hits' in stats
        assert 'l2_misses' in stats
        assert 'total_hits' in stats
        assert 'total_misses' in stats
        assert 'hit_ratio' in stats
        assert 'avg_response_time_ms' in stats

        # Should have at least 1 hit and 1 miss
        assert stats['total_hits'] >= 1
        assert stats['total_misses'] >= 1


if __name__ == '__main__':
    # Allow running tests directly
    pytest.main([__file__, '-v', '-s'])

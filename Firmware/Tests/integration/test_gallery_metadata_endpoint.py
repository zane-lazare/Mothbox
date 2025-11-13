"""
Integration tests for gallery metadata endpoint (Issue #100).

Tests the full integration of gallery routes with MetadataCache and MetadataService.
"""

import pytest
import json
import time
from pathlib import Path
from flask import Flask
from unittest.mock import patch, MagicMock
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import after path setup
from webui.backend.routes.gallery import gallery_bp, _reset_cache
from mothbox_paths import PHOTOS_DIR, DATA_DIR


@pytest.fixture
def app(tmp_path, monkeypatch):
    """Flask app with gallery blueprint"""
    # Patch PHOTOS_DIR and DATA_DIR to use tmp_path
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Monkeypatch the paths
    import mothbox_paths
    monkeypatch.setattr(mothbox_paths, 'PHOTOS_DIR', photos_dir)
    monkeypatch.setattr(mothbox_paths, 'DATA_DIR', data_dir)

    # Also patch in gallery module
    import webui.backend.routes.gallery as gallery_module
    monkeypatch.setattr(gallery_module, 'PHOTOS_DIR', photos_dir)
    monkeypatch.setattr(gallery_module, 'DATA_DIR', data_dir)

    # Reset cache singleton
    _reset_cache()

    # Create Flask app
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(gallery_bp)

    return app


@pytest.fixture
def client(app):
    """Flask test client"""
    return app.test_client()


@pytest.fixture
def sample_photo(app):
    """Create sample photo with EXIF for testing"""
    from PIL import Image
    import piexif
    import mothbox_paths

    # Use the PHOTOS_DIR from the app fixture (already configured)
    photos_dir = mothbox_paths.PHOTOS_DIR
    photos_dir.mkdir(parents=True, exist_ok=True)

    # Create test photo with EXIF
    photo_path = photos_dir / "test_photo.jpg"
    img = Image.new('RGB', (100, 100), color='red')

    exif_dict = {
        "0th": {
            piexif.ImageIFD.Make: b"Arducam",
            piexif.ImageIFD.Model: b"OwlSight 64MP"
        }
    }
    exif_bytes = piexif.dump(exif_dict)
    img.save(photo_path, "JPEG", exif=exif_bytes)

    return photo_path


@pytest.fixture
def sample_metadata():
    """Sample metadata response"""
    return {
        "camera": {
            "make": "Arducam",
            "model": "OwlSight 64MP",
            "iso": 100
        },
        "location": {
            "latitude": 34.0522,
            "longitude": -118.2437
        },
        "capture": {
            "timestamp": "2024-01-15T22:30:45"
        },
        "deployment": {
            "mothbox_id": "mothbox-test-001"
        },
        "file": {
            "path": "/photos/test.jpg",
            "size": 1024000
        }
    }


class TestGalleryMetadataEndpoint:
    """Test gallery metadata endpoint integration"""

    def test_get_metadata_success(self, client, sample_photo, sample_metadata):
        """GET /api/gallery/photos/:id/metadata returns metadata"""
        photo_id = sample_photo.name

        # Mock MetadataService
        with patch('webui.backend.routes.gallery.MetadataService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_photo_metadata.return_value = sample_metadata
            mock_service.return_value = mock_instance

            response = client.get(f'/api/gallery/photos/{photo_id}/metadata')

        assert response.status_code == 200
        data = response.get_json()

        assert data['success'] is True
        assert data['photo_id'] == photo_id
        assert 'metadata' in data
        assert 'cache_info' in data
        assert data['metadata']['camera']['make'] == 'Arducam'

    def test_get_metadata_with_category_filter(self, client, sample_photo, sample_metadata):
        """Can filter metadata by category"""
        photo_id = sample_photo.name

        with patch('webui.backend.routes.gallery.MetadataService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_photo_metadata.return_value = sample_metadata
            mock_service.return_value = mock_instance

            response = client.get(f'/api/gallery/photos/{photo_id}/metadata?categories=camera,location')

        assert response.status_code == 200
        data = response.get_json()

        # Should only have camera and location
        metadata = data['metadata']
        assert 'camera' in metadata
        assert 'location' in metadata
        assert 'capture' not in metadata
        assert 'deployment' not in metadata

    def test_get_metadata_cache_hit(self, client, sample_photo, sample_metadata):
        """Second request hits cache"""
        photo_id = sample_photo.name

        with patch('webui.backend.routes.gallery.MetadataService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_photo_metadata.return_value = sample_metadata
            mock_service.return_value = mock_instance

            # First request (cache miss)
            response1 = client.get(f'/api/gallery/photos/{photo_id}/metadata')
            data1 = response1.get_json()
            assert data1['cache_info']['cached'] is False

            # Second request (cache hit)
            response2 = client.get(f'/api/gallery/photos/{photo_id}/metadata')
            data2 = response2.get_json()
            assert data2['cache_info']['cached'] is True
            assert data2['cache_info']['cache_level'] in ['l1_memory', 'l2_disk']

            # MetadataService should only be called once
            assert mock_instance.get_photo_metadata.call_count == 1

    def test_get_metadata_photo_not_found(self, client):
        """Returns 404 for nonexistent photo"""
        response = client.get('/api/gallery/photos/nonexistent.jpg/metadata')

        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False
        assert 'not found' in data['error'].lower()

    def test_get_metadata_invalid_category(self, client, sample_photo):
        """Returns 400 for invalid category"""
        photo_id = sample_photo.name

        response = client.get(f'/api/gallery/photos/{photo_id}/metadata?categories=invalid_cat')

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'Invalid category' in data['error']

    def test_get_metadata_path_traversal_protection(self, client):
        """Blocks path traversal attempts"""
        # Try path traversal
        response = client.get('/api/gallery/photos/../../../etc/passwd/metadata')

        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False

    def test_get_metadata_absolute_path_blocked(self, client):
        """Blocks absolute paths"""
        response = client.get('/api/gallery/photos//etc/passwd/metadata')

        # Flask redirects double-slash URLs (308) or returns 404
        # Either is acceptable - request doesn't reach our handler
        assert response.status_code in [308, 404]

    def test_get_metadata_with_all_categories(self, client, sample_photo, sample_metadata):
        """categories=all returns all metadata"""
        photo_id = sample_photo.name

        with patch('webui.backend.routes.gallery.MetadataService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_photo_metadata.return_value = sample_metadata
            mock_service.return_value = mock_instance

            response = client.get(f'/api/gallery/photos/{photo_id}/metadata?categories=all')

        assert response.status_code == 200
        data = response.get_json()
        metadata = data['metadata']

        # Should have all categories
        assert 'camera' in metadata
        assert 'location' in metadata
        assert 'capture' in metadata
        assert 'deployment' in metadata
        assert 'file' in metadata

    def test_get_metadata_default_is_all(self, client, sample_photo, sample_metadata):
        """Default (no categories param) returns all metadata"""
        photo_id = sample_photo.name

        with patch('webui.backend.routes.gallery.MetadataService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_photo_metadata.return_value = sample_metadata
            mock_service.return_value = mock_instance

            response = client.get(f'/api/gallery/photos/{photo_id}/metadata')

        assert response.status_code == 200
        data = response.get_json()
        metadata = data['metadata']

        # Should have all categories
        assert len(metadata) >= 4  # At least camera, location, capture, deployment


class TestGalleryMetadataCacheEndpoint:
    """Test cache management endpoint"""

    def test_clear_cache_success(self, client, sample_photo, sample_metadata):
        """DELETE /api/gallery/photos/:id/cache clears cache"""
        photo_id = sample_photo.name

        with patch('webui.backend.routes.gallery.MetadataService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_photo_metadata.return_value = sample_metadata
            mock_service.return_value = mock_instance

            # First, cache the metadata
            client.get(f'/api/gallery/photos/{photo_id}/metadata')

            # Clear cache
            response = client.delete(f'/api/gallery/photos/{photo_id}/cache')

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['was_cached'] is True

    def test_clear_cache_uncached_photo(self, client, sample_photo):
        """DELETE on uncached photo returns success with was_cached=False"""
        photo_id = sample_photo.name

        response = client.delete(f'/api/gallery/photos/{photo_id}/cache')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['was_cached'] is False

    def test_clear_cache_photo_not_found(self, client):
        """DELETE returns 404 for nonexistent photo"""
        response = client.delete('/api/gallery/photos/nonexistent.jpg/cache')

        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False


class TestGalleryCacheStatistics:
    """Test cache statistics endpoint"""

    def test_get_cache_statistics(self, client):
        """GET /api/gallery/cache/statistics returns stats"""
        response = client.get('/api/gallery/cache/statistics')

        assert response.status_code == 200
        data = response.get_json()

        assert data['success'] is True
        assert 'statistics' in data

        stats = data['statistics']
        assert 'l1_hits' in stats
        assert 'l1_misses' in stats
        assert 'l2_hits' in stats
        assert 'l2_misses' in stats
        assert 'total_hits' in stats
        assert 'total_misses' in stats
        assert 'hit_ratio' in stats
        assert 'avg_response_time_ms' in stats

    def test_cache_statistics_track_operations(self, client, sample_photo, sample_metadata):
        """Cache statistics update after operations"""
        photo_id = sample_photo.name

        with patch('webui.backend.routes.gallery.MetadataService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_photo_metadata.return_value = sample_metadata
            mock_service.return_value = mock_instance

            # Get initial stats
            response1 = client.get('/api/gallery/cache/statistics')
            stats1 = response1.get_json()['statistics']

            # Cache miss
            client.get(f'/api/gallery/photos/{photo_id}/metadata')

            # Cache hit
            client.get(f'/api/gallery/photos/{photo_id}/metadata')

            # Get updated stats
            response2 = client.get('/api/gallery/cache/statistics')
            stats2 = response2.get_json()['statistics']

            # Should have more hits/misses
            assert stats2['total_hits'] + stats2['total_misses'] > stats1['total_hits'] + stats1['total_misses']


class TestGalleryMetadataEdgeCases:
    """Test edge cases and error handling"""

    def test_metadata_extraction_failure(self, client, sample_photo):
        """Handles metadata extraction errors gracefully"""
        photo_id = sample_photo.name

        with patch('webui.backend.routes.gallery.MetadataService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_photo_metadata.side_effect = Exception("EXIF read error")
            mock_service.return_value = mock_instance

            response = client.get(f'/api/gallery/photos/{photo_id}/metadata')

            assert response.status_code == 500
            data = response.get_json()
            assert data['success'] is False
            assert 'Failed to read metadata' in data['error']

    def test_category_filter_whitespace_handling(self, client, sample_photo, sample_metadata):
        """Handles whitespace in category filter"""
        photo_id = sample_photo.name

        with patch('webui.backend.routes.gallery.MetadataService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_photo_metadata.return_value = sample_metadata
            mock_service.return_value = mock_instance

            response = client.get(f'/api/gallery/photos/{photo_id}/metadata?categories=camera, location')

            assert response.status_code == 200
            data = response.get_json()
            assert 'camera' in data['metadata']
            assert 'location' in data['metadata']

    def test_multiple_requests_concurrent_caching(self, client, sample_photo, sample_metadata):
        """Multiple requests work correctly with caching"""
        photo_id = sample_photo.name

        with patch('webui.backend.routes.gallery.MetadataService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_photo_metadata.return_value = sample_metadata
            mock_service.return_value = mock_instance

            # Make multiple requests
            for i in range(5):
                response = client.get(f'/api/gallery/photos/{photo_id}/metadata')
                assert response.status_code == 200

            # MetadataService should only be called once (rest from cache)
            assert mock_instance.get_photo_metadata.call_count == 1

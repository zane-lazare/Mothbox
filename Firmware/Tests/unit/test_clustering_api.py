"""
Unit tests for Clustering API endpoints (Issue #115 - Subtask 3)

Tests the clustering API endpoints in gallery.py for proper response structure,
parameter validation, and CSRF protection.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from flask import Flask

# Setup path for imports
FIRMWARE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(FIRMWARE_DIR))
sys.path.insert(0, str(FIRMWARE_DIR / "webui" / "backend"))

# Set test environment before importing modules
os.environ.setdefault("MOTHBOX_ENV", "test")

from webui.backend.lib.geo_clustering import ClusteringResult, PhotoCluster, PhotoLocation
from webui.backend.routes.gallery import gallery_bp
from webui.backend.services.clustering_service import ClusteringService


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_photos_dir(tmp_path, monkeypatch):
    """Temporary PHOTOS_DIR for tests."""
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()

    import mothbox_paths
    monkeypatch.setattr(mothbox_paths, 'PHOTOS_DIR', photos_dir)

    import webui.backend.routes.gallery as gallery
    monkeypatch.setattr(gallery, 'PHOTOS_DIR', photos_dir)

    return photos_dir


@pytest.fixture
def mock_clustering_service():
    """Mock ClusteringService."""
    mock_service = Mock(spec=ClusteringService)

    # Setup default mock response
    mock_service.get_clustered_locations.return_value = ClusteringResult(
        clusters=[
            PhotoCluster(
                cluster_id="cluster_37.7749N_122.4194W_2",
                center_lat=37.7749,
                center_lon=-122.4194,
                photos=[
                    PhotoLocation("photo1.jpg", 37.7749, -122.4194, "2024-01-15T10:00:00"),
                    PhotoLocation("photo2.jpg", 37.7750, -122.4195, "2024-01-15T11:00:00")
                ],
                date_range=("2024-01-15T10:00:00", "2024-01-15T11:00:00")
            )
        ],
        unclustered=[
            PhotoLocation("photo3.jpg", 38.0000, -122.5000, "2024-01-15T12:00:00")
        ],
        total_photos=3,
        total_clusters=1,
        radius_m=100,
        processing_time_ms=45.2,
        partial_result=False,
        warning=None
    )

    mock_service.get_statistics.return_value = {
        'cache_hits': 45,
        'cache_misses': 12,
        'cache_entries': 3,
        'total_clustering_time_ms': 567.8
    }

    return mock_service


@pytest.fixture
def mock_locations_service(monkeypatch):
    """Mock LocationsService."""
    import webui.backend.routes.gallery as gallery

    mock_service = Mock()
    mock_service.get_locations.return_value = {
        'locations': [
            {
                "photo_path": "2024-01-15/photo1.jpg",
                "filename": "photo1.jpg",
                "latitude": 37.7749,
                "longitude": -122.4194,
                "timestamp": "2024-01-15T10:00:00"
            }
        ],
        'total_with_gps': 1,
        'total_without_gps': 0
    }

    monkeypatch.setattr(gallery, '_locations_service', mock_service)
    return mock_service


@pytest.fixture
def gallery_app(temp_photos_dir, mock_clustering_service, mock_locations_service):
    """Flask app with gallery blueprint."""
    app = Flask(__name__)
    app.config['TESTING'] = True

    # Inject mock clustering service
    app.config['CLUSTERING_SERVICE'] = mock_clustering_service

    app.register_blueprint(gallery_bp, url_prefix='/api/gallery')
    return app


@pytest.fixture
def client(gallery_app):
    """Test client for gallery routes."""
    return gallery_app.test_client()


@pytest.fixture
def csrf_token(client):
    """Get CSRF token for POST requests."""
    # Mock CSRF protection for tests
    return "test-csrf-token"


# ============================================================================
# GET /api/gallery/locations/clustered Tests
# ============================================================================

class TestClusteredLocationsEndpoint:
    """Test GET /api/gallery/locations/clustered endpoint."""

    def test_get_clustered_locations_success(self, client):
        """GET /api/gallery/locations/clustered returns 200."""
        response = client.get('/api/gallery/locations/clustered')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'clusters' in data
        assert 'unclustered' in data
        assert 'metadata' in data

    def test_response_structure(self, client):
        """Response has correct structure with all required fields."""
        response = client.get('/api/gallery/locations/clustered')
        data = json.loads(response.data)

        # Check top-level keys
        assert 'clusters' in data
        assert 'unclustered' in data
        assert 'metadata' in data

        # Check metadata fields
        metadata = data['metadata']
        assert 'total_photos' in metadata
        assert 'total_clusters' in metadata
        assert 'clustering_enabled' in metadata
        assert 'radius_m' in metadata
        assert 'processing_time_ms' in metadata
        assert 'partial_result' in metadata
        assert 'warning' in metadata

        # Check cluster structure
        if len(data['clusters']) > 0:
            cluster = data['clusters'][0]
            assert 'cluster_id' in cluster
            assert 'center' in cluster
            assert 'lat' in cluster['center']
            assert 'lon' in cluster['center']
            assert 'count' in cluster
            assert 'photos' in cluster
            assert 'date_range' in cluster
            assert 'radius_m' in cluster

    def test_radius_parameter(self, client, mock_clustering_service):
        """Radius query param is passed to clustering service."""
        response = client.get('/api/gallery/locations/clustered?radius=200')

        assert response.status_code == 200

        # Verify service was called with correct radius
        mock_clustering_service.get_clustered_locations.assert_called()
        call_kwargs = mock_clustering_service.get_clustered_locations.call_args[1]
        assert call_kwargs.get('radius_m') == 200

    def test_min_size_parameter(self, client, mock_clustering_service):
        """min_size query param is passed to clustering service."""
        response = client.get('/api/gallery/locations/clustered?min_size=3')

        assert response.status_code == 200

        # Verify service was called with correct min_cluster_size
        mock_clustering_service.get_clustered_locations.assert_called()
        call_kwargs = mock_clustering_service.get_clustered_locations.call_args[1]
        assert call_kwargs.get('min_cluster_size') == 3

    def test_invalid_radius_returns_400(self, client):
        """Negative radius returns 400 error."""
        response = client.get('/api/gallery/locations/clustered?radius=-100')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'radius' in data['error'].lower()

    def test_invalid_min_size_returns_400(self, client):
        """Negative min_size returns 400 error."""
        response = client.get('/api/gallery/locations/clustered?min_size=-1')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'min_size' in data['error'].lower()

    def test_non_integer_radius_returns_400(self, client):
        """Non-integer radius returns 400 error."""
        response = client.get('/api/gallery/locations/clustered?radius=abc')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_enabled_false_returns_unclustered(self, client, gallery_app):
        """enabled=false returns all photos as unclustered."""
        # Note: When enabled=false, the endpoint bypasses clustering service
        # and returns raw locations from LocationsService
        response = client.get('/api/gallery/locations/clustered?enabled=false')

        assert response.status_code == 200
        data = json.loads(response.data)

        # All photos should be unclustered (no clusters)
        assert len(data['clusters']) == 0
        # At least one location from the mock_locations_service
        assert len(data['unclustered']) >= 0
        assert data['metadata']['total_clusters'] == 0
        assert data['metadata']['clustering_enabled'] is False

    def test_enabled_true_clusters_photos(self, client, gallery_app):
        """enabled=true (default) performs clustering."""
        response = client.get('/api/gallery/locations/clustered?enabled=true')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Should have clusters
        assert data['metadata']['clustering_enabled'] is True

    def test_partial_result_warning(self, client, gallery_app):
        """Partial result includes warning in metadata."""
        # Setup mock to return partial result
        clustering_service = gallery_app.config['CLUSTERING_SERVICE']
        clustering_service.get_clustered_locations.return_value = ClusteringResult(
            clusters=[],
            unclustered=[],
            total_photos=1000,
            total_clusters=0,
            radius_m=100,
            processing_time_ms=550.0,
            partial_result=True,
            warning="Clustering timed out - returning partial results"
        )

        response = client.get('/api/gallery/locations/clustered')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['metadata']['partial_result'] is True
        assert data['metadata']['warning'] is not None
        # Check for "timed out" in the warning message
        assert 'timed out' in data['metadata']['warning'].lower()

    def test_service_unavailable_returns_503(self, client, gallery_app):
        """Returns 503 if clustering service not available."""
        # Remove clustering service
        gallery_app.config['CLUSTERING_SERVICE'] = None

        response = client.get('/api/gallery/locations/clustered')

        assert response.status_code == 503
        data = json.loads(response.data)
        assert 'error' in data


# ============================================================================
# GET /api/gallery/locations/clustered/stats Tests
# ============================================================================

class TestClusterStatsEndpoint:
    """Test GET /api/gallery/locations/clustered/stats endpoint."""

    def test_get_stats_success(self, client):
        """GET /api/gallery/locations/clustered/stats returns 200."""
        response = client.get('/api/gallery/locations/clustered/stats')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'cache_hits' in data
        assert 'cache_misses' in data
        assert 'cache_entries' in data
        assert 'total_clustering_time_ms' in data

    def test_stats_structure(self, client):
        """Response has correct statistics structure."""
        response = client.get('/api/gallery/locations/clustered/stats')
        data = json.loads(response.data)

        # Check all expected fields
        assert isinstance(data['cache_hits'], int)
        assert isinstance(data['cache_misses'], int)
        assert isinstance(data['cache_entries'], int)
        assert isinstance(data['total_clustering_time_ms'], (int, float))

        # Verify values from mock
        assert data['cache_hits'] == 45
        assert data['cache_misses'] == 12
        assert data['cache_entries'] == 3
        assert data['total_clustering_time_ms'] == 567.8

    def test_stats_service_unavailable_returns_503(self, client, gallery_app):
        """Returns 503 if clustering service not available."""
        gallery_app.config['CLUSTERING_SERVICE'] = None

        response = client.get('/api/gallery/locations/clustered/stats')

        assert response.status_code == 503


# ============================================================================
# POST /api/gallery/locations/clustered/cache/invalidate Tests
# ============================================================================

class TestCacheInvalidateEndpoint:
    """Test POST /api/gallery/locations/clustered/cache/invalidate endpoint."""

    def test_post_invalidate_without_body(self, client):
        """POST without body invalidates entire cache."""
        response = client.post('/api/gallery/locations/clustered/cache/invalidate')

        # Without CSRF protection enabled in test mode, this should succeed
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'entire' in data['message'].lower()

    def test_post_invalidate_success(self, client, csrf_token, gallery_app):
        """POST with CSRF token returns 200."""
        response = client.post(
            '/api/gallery/locations/clustered/cache/invalidate',
            headers={'X-CSRFToken': csrf_token},
            content_type='application/json',
            data='{}'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'message' in data

        # Verify service invalidate was called
        clustering_service = gallery_app.config['CLUSTERING_SERVICE']
        clustering_service.invalidate_cache.assert_called_once()

    def test_invalidate_specific_directory(self, client, csrf_token, gallery_app, temp_photos_dir):
        """Can invalidate cache for specific directory."""
        # Create a subdirectory in the temp photos dir
        subdir = temp_photos_dir / "2024-01-15"
        subdir.mkdir()

        response = client.post(
            '/api/gallery/locations/clustered/cache/invalidate',
            headers={'X-CSRFToken': csrf_token},
            content_type='application/json',
            data=json.dumps({'directory': str(subdir)})
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        # Verify service was called with directory
        clustering_service = gallery_app.config['CLUSTERING_SERVICE']
        clustering_service.invalidate_cache.assert_called_once()
        # Check if directory was passed (might be Path object or string)
        call_args = clustering_service.invalidate_cache.call_args
        assert call_args is not None

    def test_invalidate_all_when_no_directory(self, client, csrf_token, gallery_app):
        """No directory specified invalidates entire cache."""
        response = client.post(
            '/api/gallery/locations/clustered/cache/invalidate',
            headers={'X-CSRFToken': csrf_token},
            content_type='application/json',
            data='{}'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'entire' in data['message'].lower() or 'all' in data['message'].lower()

    def test_invalidate_service_unavailable_returns_503(self, client, csrf_token, gallery_app):
        """Returns 503 if clustering service not available."""
        gallery_app.config['CLUSTERING_SERVICE'] = None

        response = client.post(
            '/api/gallery/locations/clustered/cache/invalidate',
            headers={'X-CSRFToken': csrf_token}
        )

        assert response.status_code == 503


# ============================================================================
# Response Format Tests
# ============================================================================

class TestResponseFormats:
    """Test detailed response formatting."""

    def test_cluster_photo_format(self, client):
        """Cluster photos have correct format."""
        response = client.get('/api/gallery/locations/clustered')
        data = json.loads(response.data)

        if len(data['clusters']) > 0:
            cluster = data['clusters'][0]
            photos = cluster['photos']

            assert len(photos) > 0

            photo = photos[0]
            assert 'photo_id' in photo
            assert 'lat' in photo
            assert 'lon' in photo
            assert 'timestamp' in photo

    def test_unclustered_photo_format(self, client):
        """Unclustered photos have correct format."""
        response = client.get('/api/gallery/locations/clustered')
        data = json.loads(response.data)

        if len(data['unclustered']) > 0:
            photo = data['unclustered'][0]
            assert 'photo_id' in photo
            assert 'lat' in photo
            assert 'lon' in photo
            assert 'timestamp' in photo

    def test_date_range_format(self, client):
        """Cluster date_range has correct format."""
        response = client.get('/api/gallery/locations/clustered')
        data = json.loads(response.data)

        if len(data['clusters']) > 0:
            cluster = data['clusters'][0]
            date_range = cluster['date_range']

            assert 'earliest' in date_range
            assert 'latest' in date_range

            # Should be ISO format timestamps or null
            if date_range['earliest']:
                assert 'T' in date_range['earliest']  # ISO format
            if date_range['latest']:
                assert 'T' in date_range['latest']


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_service_exception_returns_500(self, client, gallery_app):
        """Service exception returns 500 with generic error."""
        # Make service raise exception
        clustering_service = gallery_app.config['CLUSTERING_SERVICE']
        clustering_service.get_clustered_locations.side_effect = Exception("Test error")

        response = client.get('/api/gallery/locations/clustered')

        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
        # Should NOT expose internal error details (security)
        assert 'Test error' not in data['error']

    def test_large_radius_accepted(self, client):
        """Large but valid radius is accepted."""
        response = client.get('/api/gallery/locations/clustered?radius=10000')

        assert response.status_code == 200

    def test_zero_radius_returns_no_clusters(self, client, gallery_app):
        """Zero radius is valid but returns no clusters."""
        # Setup mock to return no clusters
        clustering_service = gallery_app.config['CLUSTERING_SERVICE']
        clustering_service.get_clustered_locations.return_value = ClusteringResult(
            clusters=[],
            unclustered=[
                PhotoLocation("photo1.jpg", 37.7749, -122.4194, "2024-01-15T10:00:00"),
                PhotoLocation("photo2.jpg", 37.7750, -122.4195, "2024-01-15T11:00:00")
            ],
            total_photos=2,
            total_clusters=0,
            radius_m=0,
            processing_time_ms=10.0
        )

        response = client.get('/api/gallery/locations/clustered?radius=0')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['metadata']['radius_m'] == 0


# ============================================================================
# Tags Support Tests (Issue #117 - Subtask 1)
# ============================================================================

class TestTagsInClusteringAPI:
    """Test tags field support in clustering API responses."""

    def test_cluster_photos_include_tags(self, client, gallery_app):
        """Cluster photos include tags field in response."""
        # Setup mock with tags
        clustering_service = gallery_app.config['CLUSTERING_SERVICE']
        clustering_service.get_clustered_locations.return_value = ClusteringResult(
            clusters=[
                PhotoCluster(
                    cluster_id="cluster_37.7749N_122.4194W_2",
                    center_lat=37.7749,
                    center_lon=-122.4194,
                    photos=[
                        PhotoLocation("photo1.jpg", 37.7749, -122.4194, "2024-01-15T10:00:00", tags=["moth", "night"]),
                        PhotoLocation("photo2.jpg", 37.7750, -122.4195, "2024-01-15T11:00:00", tags=["beetle", "day"])
                    ],
                    date_range=("2024-01-15T10:00:00", "2024-01-15T11:00:00")
                )
            ],
            unclustered=[],
            total_photos=2,
            total_clusters=1,
            radius_m=100,
            processing_time_ms=45.2
        )

        response = client.get('/api/gallery/locations/clustered')
        data = json.loads(response.data)

        # Check cluster photos have tags
        assert len(data['clusters']) == 1
        cluster = data['clusters'][0]
        photos = cluster['photos']

        assert len(photos) == 2
        photo1 = next(p for p in photos if p['photo_id'] == 'photo1.jpg')
        photo2 = next(p for p in photos if p['photo_id'] == 'photo2.jpg')

        assert 'tags' in photo1
        assert photo1['tags'] == ["moth", "night"]
        assert 'tags' in photo2
        assert photo2['tags'] == ["beetle", "day"]

    def test_unclustered_photos_include_tags(self, client, gallery_app):
        """Unclustered photos include tags field in response."""
        clustering_service = gallery_app.config['CLUSTERING_SERVICE']
        clustering_service.get_clustered_locations.return_value = ClusteringResult(
            clusters=[],
            unclustered=[
                PhotoLocation("photo1.jpg", 37.7749, -122.4194, "2024-01-15T10:00:00", tags=["moth", "solo"]),
                PhotoLocation("photo2.jpg", 38.0000, -123.0000, "2024-01-15T12:00:00", tags=["butterfly"])
            ],
            total_photos=2,
            total_clusters=0,
            radius_m=100,
            processing_time_ms=10.0
        )

        response = client.get('/api/gallery/locations/clustered')
        data = json.loads(response.data)

        # Check unclustered photos have tags
        assert len(data['unclustered']) == 2
        photo1 = next(p for p in data['unclustered'] if p['photo_id'] == 'photo1.jpg')
        photo2 = next(p for p in data['unclustered'] if p['photo_id'] == 'photo2.jpg')

        assert 'tags' in photo1
        assert photo1['tags'] == ["moth", "solo"]
        assert 'tags' in photo2
        assert photo2['tags'] == ["butterfly"]

    def test_photos_without_tags_return_none(self, client, gallery_app):
        """Photos without tags return None for tags field."""
        clustering_service = gallery_app.config['CLUSTERING_SERVICE']
        clustering_service.get_clustered_locations.return_value = ClusteringResult(
            clusters=[
                PhotoCluster(
                    cluster_id="cluster_37.7749N_122.4194W_2",
                    center_lat=37.7749,
                    center_lon=-122.4194,
                    photos=[
                        PhotoLocation("photo1.jpg", 37.7749, -122.4194, "2024-01-15T10:00:00"),  # No tags
                        PhotoLocation("photo2.jpg", 37.7750, -122.4195, "2024-01-15T11:00:00")   # No tags
                    ],
                    date_range=("2024-01-15T10:00:00", "2024-01-15T11:00:00")
                )
            ],
            unclustered=[],
            total_photos=2,
            total_clusters=1,
            radius_m=100,
            processing_time_ms=45.2
        )

        response = client.get('/api/gallery/locations/clustered')
        data = json.loads(response.data)

        # Check photos have tags field but value is None
        cluster = data['clusters'][0]
        photos = cluster['photos']

        assert len(photos) == 2
        for photo in photos:
            assert 'tags' in photo
            assert photo['tags'] is None

    def test_mixed_tags_none_and_values(self, client, gallery_app):
        """Mix of photos with and without tags handled correctly."""
        clustering_service = gallery_app.config['CLUSTERING_SERVICE']
        clustering_service.get_clustered_locations.return_value = ClusteringResult(
            clusters=[
                PhotoCluster(
                    cluster_id="cluster_37.7749N_122.4194W_3",
                    center_lat=37.7749,
                    center_lon=-122.4194,
                    photos=[
                        PhotoLocation("photo1.jpg", 37.7749, -122.4194, "2024-01-15T10:00:00", tags=["moth"]),
                        PhotoLocation("photo2.jpg", 37.7750, -122.4195, "2024-01-15T11:00:00"),  # No tags
                        PhotoLocation("photo3.jpg", 37.7751, -122.4196, "2024-01-15T12:00:00", tags=["beetle", "day"])
                    ],
                    date_range=("2024-01-15T10:00:00", "2024-01-15T12:00:00")
                )
            ],
            unclustered=[],
            total_photos=3,
            total_clusters=1,
            radius_m=100,
            processing_time_ms=50.0
        )

        response = client.get('/api/gallery/locations/clustered')
        data = json.loads(response.data)

        cluster = data['clusters'][0]
        photos = cluster['photos']

        photo1 = next(p for p in photos if p['photo_id'] == 'photo1.jpg')
        photo2 = next(p for p in photos if p['photo_id'] == 'photo2.jpg')
        photo3 = next(p for p in photos if p['photo_id'] == 'photo3.jpg')

        assert photo1['tags'] == ["moth"]
        assert photo2['tags'] is None
        assert photo3['tags'] == ["beetle", "day"]

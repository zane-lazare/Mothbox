"""
Unit tests for Series API endpoints (Issue #110 - Phase 3)

Tests REST API endpoints for series queries.
TDD approach: tests written first, then implementation.

Coverage Target: 90%+
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from flask import Flask


# Import will fail until implementation exists - that's expected in TDD
try:
    from routes.gallery import gallery_bp
    from services.series_service import SeriesService, PhotoSeries
    IMPLEMENTATION_EXISTS = True
except ImportError:
    IMPLEMENTATION_EXISTS = False
    gallery_bp = None
    SeriesService = None
    PhotoSeries = None


# Skip all tests if implementation doesn't exist yet (TDD red phase)
pytestmark = pytest.mark.skipif(
    not IMPLEMENTATION_EXISTS,
    reason="Implementation not yet created (TDD red phase)"
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_photos_dir(tmp_path, monkeypatch):
    """Temporary PHOTOS_DIR for tests."""
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()

    import mothbox_paths
    monkeypatch.setattr(mothbox_paths, 'PHOTOS_DIR', photos_dir)

    import routes.gallery
    monkeypatch.setattr(routes.gallery, 'PHOTOS_DIR', photos_dir)

    return photos_dir


@pytest.fixture
def sample_hdr_series(temp_photos_dir):
    """Create sample HDR series."""
    base = "moth_2024_01_15__10_00_00"
    photos = []
    for i in range(3):
        p = temp_photos_dir / f"{base}_HDR{i}.jpg"
        p.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
        photos.append(p)
    return photos


@pytest.fixture
def sample_fb_series(temp_photos_dir):
    """Create sample Focus Bracket series."""
    base = "ManFocus_moth_2024_01_15__11_00_00_000000"
    photos = []
    for i in range(5):
        p = temp_photos_dir / f"{base}_FB{i}.jpg"
        p.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
        photos.append(p)
    return photos


@pytest.fixture
def gallery_app(temp_photos_dir):
    """Flask app with gallery blueprint."""
    app = Flask(__name__)
    app.config['TESTING'] = True

    # Create a mock series service
    mock_service = Mock(spec=SeriesService)
    app.config['SERIES_SERVICE'] = mock_service

    app.register_blueprint(gallery_bp, url_prefix='/api/gallery')
    return app


@pytest.fixture
def gallery_client(gallery_app):
    """Test client for gallery routes."""
    return gallery_app.test_client()


@pytest.fixture
def mock_photo_series(temp_photos_dir):
    """Create mock PhotoSeries objects."""
    return [
        PhotoSeries(
            series_id="hdr_moth_2024_01_15__10_00_00",
            series_type="hdr",
            base_name="moth_2024_01_15__10_00_00",
            photos=[
                temp_photos_dir / "moth_2024_01_15__10_00_00_HDR0.jpg",
                temp_photos_dir / "moth_2024_01_15__10_00_00_HDR1.jpg",
                temp_photos_dir / "moth_2024_01_15__10_00_00_HDR2.jpg",
            ],
            count=3,
            cover_photo=temp_photos_dir / "moth_2024_01_15__10_00_00_HDR0.jpg"
        ),
        PhotoSeries(
            series_id="focus_bracket_ManFocus_moth_2024_01_15__11_00_00_000000",
            series_type="focus_bracket",
            base_name="ManFocus_moth_2024_01_15__11_00_00_000000",
            photos=[
                temp_photos_dir / "ManFocus_moth_2024_01_15__11_00_00_000000_FB0.jpg",
                temp_photos_dir / "ManFocus_moth_2024_01_15__11_00_00_000000_FB1.jpg",
            ],
            count=2,
            cover_photo=temp_photos_dir / "ManFocus_moth_2024_01_15__11_00_00_000000_FB0.jpg"
        ),
    ]


# ============================================================================
# Test GET /series Endpoint
# ============================================================================

class TestSeriesListEndpoint:
    """Tests for GET /api/gallery/series endpoint."""

    def test_list_series_empty(self, gallery_app, gallery_client, temp_photos_dir):
        """GET /series returns empty list when no series exist."""
        # Configure mock
        gallery_app.config['SERIES_SERVICE'].get_series_for_directory.return_value = []

        response = gallery_client.get('/api/gallery/series')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'series' in data
        assert data['series'] == []

    def test_list_series_returns_series(self, gallery_app, gallery_client, mock_photo_series, temp_photos_dir):
        """GET /series returns series with correct structure."""
        gallery_app.config['SERIES_SERVICE'].get_series_for_directory.return_value = mock_photo_series

        response = gallery_client.get('/api/gallery/series')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'series' in data
        assert len(data['series']) == 2

        # Check first series structure
        series = data['series'][0]
        assert 'series_id' in series
        assert 'series_type' in series
        assert 'count' in series
        assert 'cover_photo' in series
        assert 'photos' in series

    def test_list_series_with_pagination(self, gallery_app, gallery_client, mock_photo_series):
        """GET /series?page=1&per_page=10 returns paginated results."""
        gallery_app.config['SERIES_SERVICE'].get_series_for_directory.return_value = mock_photo_series

        response = gallery_client.get('/api/gallery/series?page=1&per_page=10')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'pagination' in data
        assert data['pagination']['page'] == 1
        assert data['pagination']['per_page'] == 10

    def test_list_series_filter_by_type(self, gallery_app, gallery_client, mock_photo_series):
        """GET /series?type=hdr filters by series type."""
        # Only return HDR series
        hdr_series = [s for s in mock_photo_series if s.series_type == "hdr"]
        gallery_app.config['SERIES_SERVICE'].get_series_for_directory.return_value = hdr_series

        response = gallery_client.get('/api/gallery/series?type=hdr')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert all(s['series_type'] == 'hdr' for s in data['series'])

    def test_list_series_invalid_page(self, gallery_app, gallery_client):
        """GET /series?page=-1 returns 400."""
        response = gallery_client.get('/api/gallery/series?page=-1')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_list_series_service_unavailable(self, gallery_app, gallery_client):
        """GET /series returns 503 when service unavailable."""
        gallery_app.config['SERIES_SERVICE'] = None

        response = gallery_client.get('/api/gallery/series')

        assert response.status_code == 503
        data = json.loads(response.data)
        assert 'error' in data


# ============================================================================
# Test GET /series/<series_id> Endpoint
# ============================================================================

class TestSeriesDetailEndpoint:
    """Tests for GET /api/gallery/series/<series_id> endpoint."""

    def test_get_series_by_id(self, gallery_app, gallery_client, mock_photo_series, temp_photos_dir):
        """GET /series/<id> returns specific series."""
        series_id = mock_photo_series[0].series_id
        gallery_app.config['SERIES_SERVICE'].get_series_by_id.return_value = mock_photo_series[0]

        response = gallery_client.get(f'/api/gallery/series/{series_id}')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['series_id'] == series_id
        assert data['series_type'] == 'hdr'
        assert data['count'] == 3

    def test_get_series_not_found(self, gallery_app, gallery_client):
        """GET /series/<id> returns 404 for nonexistent series."""
        gallery_app.config['SERIES_SERVICE'].get_series_by_id.return_value = None

        response = gallery_client.get('/api/gallery/series/nonexistent_id')

        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data

    def test_get_series_includes_photos(self, gallery_app, gallery_client, mock_photo_series, temp_photos_dir):
        """GET /series/<id> includes photo list."""
        series_id = mock_photo_series[0].series_id
        gallery_app.config['SERIES_SERVICE'].get_series_by_id.return_value = mock_photo_series[0]

        response = gallery_client.get(f'/api/gallery/series/{series_id}')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'photos' in data
        assert len(data['photos']) == 3

    def test_get_series_includes_cover_photo(self, gallery_app, gallery_client, mock_photo_series, temp_photos_dir):
        """GET /series/<id> includes cover photo path."""
        series_id = mock_photo_series[0].series_id
        gallery_app.config['SERIES_SERVICE'].get_series_by_id.return_value = mock_photo_series[0]

        response = gallery_client.get(f'/api/gallery/series/{series_id}')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'cover_photo' in data
        assert 'HDR0' in data['cover_photo']


# ============================================================================
# Test Series Cache Endpoints
# ============================================================================

class TestSeriesCacheEndpoints:
    """Tests for series cache management endpoints."""

    def test_get_series_statistics(self, gallery_app, gallery_client):
        """GET /series/stats returns cache statistics."""
        gallery_app.config['SERIES_SERVICE'].get_statistics.return_value = {
            'cache_entries': 5,
            'cache_hits': 42,
            'cache_misses': 8,
            'total_series': 10,
            'series_by_type': {'hdr': 6, 'focus_bracket': 4}
        }

        response = gallery_client.get('/api/gallery/series/stats')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['cache_hits'] == 42
        assert data['total_series'] == 10

    def test_invalidate_series_cache(self, gallery_app, gallery_client):
        """POST /series/cache/invalidate clears cache."""
        response = gallery_client.post(
            '/api/gallery/series/cache/invalidate',
            data=json.dumps({}),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        # Verify service was called
        gallery_app.config['SERIES_SERVICE'].invalidate_cache.assert_called_once()

    def test_invalidate_series_cache_service_unavailable(self, gallery_app, gallery_client):
        """POST /series/cache/invalidate returns 503 when service unavailable."""
        gallery_app.config['SERIES_SERVICE'] = None

        response = gallery_client.post(
            '/api/gallery/series/cache/invalidate',
            data=json.dumps({}),
            content_type='application/json'
        )

        assert response.status_code == 503


# ============================================================================
# Test Photo Path Handling
# ============================================================================

class TestSeriesPhotoPathHandling:
    """Tests for photo path security and formatting."""

    def test_series_photo_paths_relative(self, gallery_app, gallery_client, mock_photo_series, temp_photos_dir):
        """Series photo paths should be relative to PHOTOS_DIR."""
        gallery_app.config['SERIES_SERVICE'].get_series_by_id.return_value = mock_photo_series[0]

        response = gallery_client.get(f'/api/gallery/series/{mock_photo_series[0].series_id}')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Photo paths should be relative (no absolute paths exposed)
        for photo in data['photos']:
            assert not photo.startswith('/var')
            assert not photo.startswith('/home')

    def test_cover_photo_path_relative(self, gallery_app, gallery_client, mock_photo_series, temp_photos_dir):
        """Cover photo path should be relative."""
        gallery_app.config['SERIES_SERVICE'].get_series_by_id.return_value = mock_photo_series[0]

        response = gallery_client.get(f'/api/gallery/series/{mock_photo_series[0].series_id}')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Cover photo should be relative
        assert not data['cover_photo'].startswith('/var')


# ============================================================================
# Test Error Handling
# ============================================================================

class TestSeriesErrorHandling:
    """Tests for error handling in series endpoints."""

    def test_service_exception_returns_500(self, gallery_app, gallery_client):
        """Service exceptions should return 500."""
        gallery_app.config['SERIES_SERVICE'].get_series_for_directory.side_effect = Exception("Service error")

        response = gallery_client.get('/api/gallery/series')

        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data

    def test_invalid_series_type_filter(self, gallery_app, gallery_client):
        """Invalid type filter should return 400."""
        response = gallery_client.get('/api/gallery/series?type=invalid_type')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

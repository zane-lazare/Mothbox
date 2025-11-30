"""
Integration tests for the clustering workflow (Issue #115).

Tests the complete flow from photo locations through clustering to API response.

Run with: MOTHBOX_ENV=test pytest Tests/integration/test_clustering_workflow.py -v -s
"""

import os
import sys
import json
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

# Setup path
FIRMWARE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(FIRMWARE_DIR))
sys.path.insert(0, str(FIRMWARE_DIR / "webui" / "backend"))
os.environ.setdefault("MOTHBOX_ENV", "test")

from flask import Flask
from webui.backend.routes.gallery import gallery_bp
from webui.backend.services.clustering_service import ClusteringService


class TestClusteringWorkflow:
    """Test complete clustering workflow from locations to API."""

    @pytest.fixture
    def mock_locations(self):
        """Sample photo locations for testing."""
        return {
            'locations': [
                # Cluster 1: Two photos within 50m
                {'path': 'photo1.jpg', 'filename': 'photo1.jpg',
                 'latitude': 37.7749, 'longitude': -122.4194, 'timestamp': '2024-01-15T10:00:00'},
                {'path': 'photo2.jpg', 'filename': 'photo2.jpg',
                 'latitude': 37.7750, 'longitude': -122.4195, 'timestamp': '2024-01-15T10:05:00'},
                # Cluster 2: Two photos within 50m (far from cluster 1)
                {'path': 'photo3.jpg', 'filename': 'photo3.jpg',
                 'latitude': 38.5000, 'longitude': -121.5000, 'timestamp': '2024-01-15T11:00:00'},
                {'path': 'photo4.jpg', 'filename': 'photo4.jpg',
                 'latitude': 38.5001, 'longitude': -121.5001, 'timestamp': '2024-01-15T11:05:00'},
                # Unclustered: Single photo far from others
                {'path': 'photo5.jpg', 'filename': 'photo5.jpg',
                 'latitude': 40.0000, 'longitude': -120.0000, 'timestamp': '2024-01-15T12:00:00'},
            ],
            'total_with_gps': 5,
            'total_without_gps': 0
        }

    @pytest.fixture
    def app(self, mock_locations, tmp_path, monkeypatch):
        """Flask app with clustering service."""
        # Mock PHOTOS_DIR
        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'PHOTOS_DIR', photos_dir)

        import webui.backend.routes.gallery as gallery
        monkeypatch.setattr(gallery, 'PHOTOS_DIR', photos_dir)

        # Mock locations service
        mock_loc_service = Mock()
        mock_loc_service.get_locations.return_value = mock_locations
        monkeypatch.setattr(gallery, '_locations_service', mock_loc_service)

        # Create app with clustering service
        app = Flask(__name__)
        app.config['TESTING'] = True

        with patch('webui.backend.services.clustering_service.LocationsService') as MockLS:
            MockLS.return_value = mock_loc_service
            clustering_service = ClusteringService(cache_ttl=60)
            app.config['CLUSTERING_SERVICE'] = clustering_service

        app.register_blueprint(gallery_bp, url_prefix='/api/gallery')
        return app

    @pytest.fixture
    def client(self, app):
        """Test client."""
        return app.test_client()

    def test_end_to_end_clustering(self, client):
        """Test complete clustering workflow."""
        response = client.get('/api/gallery/locations/clustered?radius=100')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Should have 2 clusters and 1 unclustered
        assert len(data['clusters']) == 2
        assert len(data['unclustered']) == 1
        assert data['metadata']['total_photos'] == 5
        assert data['metadata']['total_clusters'] == 2

    def test_cluster_contains_correct_photos(self, client):
        """Verify clusters contain the expected photos."""
        response = client.get('/api/gallery/locations/clustered?radius=100')
        data = json.loads(response.data)

        # Get all photo paths in clusters
        clustered_paths = set()
        for cluster in data['clusters']:
            for photo in cluster['photos']:
                clustered_paths.add(photo['path'])

        # Photos 1-4 should be clustered, photo5 should be unclustered
        assert 'photo1.jpg' in clustered_paths
        assert 'photo2.jpg' in clustered_paths
        assert 'photo3.jpg' in clustered_paths
        assert 'photo4.jpg' in clustered_paths

        # Photo5 should be unclustered
        unclustered_paths = {p['path'] for p in data['unclustered']}
        assert 'photo5.jpg' in unclustered_paths

    def test_cluster_centers_are_centroids(self, client):
        """Verify cluster centers are geographic centroids."""
        response = client.get('/api/gallery/locations/clustered?radius=100')
        data = json.loads(response.data)

        for cluster in data['clusters']:
            # Center should be within reasonable distance of all photos
            center_lat = cluster['center']['lat']
            center_lon = cluster['center']['lon']

            for photo in cluster['photos']:
                # Centroid should be close to all photos in cluster
                lat_diff = abs(center_lat - photo['lat'])
                lon_diff = abs(center_lon - photo['lon'])

                # Differences should be small (within cluster radius)
                assert lat_diff < 0.01, f"Center lat differs by {lat_diff}"
                assert lon_diff < 0.01, f"Center lon differs by {lon_diff}"

    def test_disabled_clustering_returns_all_unclustered(self, client):
        """When clustering disabled, all photos are unclustered."""
        response = client.get('/api/gallery/locations/clustered?enabled=false')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert len(data['clusters']) == 0
        assert data['metadata']['clustering_enabled'] is False

    def test_small_radius_creates_no_clusters(self, client):
        """Very small radius should create no clusters."""
        response = client.get('/api/gallery/locations/clustered?radius=1')

        assert response.status_code == 200
        data = json.loads(response.data)

        # With 1m radius, no photos should cluster
        assert len(data['clusters']) == 0

    def test_large_radius_creates_fewer_clusters(self, client):
        """Large radius should merge clusters."""
        # With very large radius, all nearby photos might merge
        response = client.get('/api/gallery/locations/clustered?radius=500000')

        assert response.status_code == 200
        data = json.loads(response.data)

        # With huge radius, might get 1 or 2 clusters
        assert data['metadata']['total_clusters'] <= 2

    def test_cache_hit_on_repeated_request(self, client, app):
        """Second request should hit cache."""
        # First request
        response1 = client.get('/api/gallery/locations/clustered?radius=100')
        assert response1.status_code == 200

        # Get stats
        stats1 = app.config['CLUSTERING_SERVICE'].get_statistics()

        # Second request (same parameters)
        response2 = client.get('/api/gallery/locations/clustered?radius=100')
        assert response2.status_code == 200

        # Should have 1 cache hit
        stats2 = app.config['CLUSTERING_SERVICE'].get_statistics()
        assert stats2['cache_hits'] == stats1['cache_hits'] + 1

    def test_cache_invalidation(self, client, app):
        """Cache invalidation should force re-clustering."""
        # First request to populate cache
        client.get('/api/gallery/locations/clustered?radius=100')
        stats1 = app.config['CLUSTERING_SERVICE'].get_statistics()

        # Invalidate cache
        response = client.post('/api/gallery/locations/clustered/cache/invalidate')
        assert response.status_code == 200

        # Next request should be cache miss
        client.get('/api/gallery/locations/clustered?radius=100')
        stats2 = app.config['CLUSTERING_SERVICE'].get_statistics()

        assert stats2['cache_misses'] > stats1['cache_misses']

    def test_stats_endpoint(self, client):
        """Stats endpoint returns cache statistics."""
        # Make some requests first
        client.get('/api/gallery/locations/clustered?radius=100')
        client.get('/api/gallery/locations/clustered?radius=100')

        response = client.get('/api/gallery/locations/clustered/stats')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert 'cache_hits' in data
        assert 'cache_misses' in data
        assert data['cache_hits'] >= 1  # At least one hit from second request


class TestClusteringEdgeCases:
    """Test edge cases in clustering workflow."""

    @pytest.fixture
    def empty_locations(self):
        """Empty locations for testing."""
        return {'locations': [], 'total_with_gps': 0, 'total_without_gps': 0}

    @pytest.fixture
    def app_empty(self, empty_locations, tmp_path, monkeypatch):
        """Flask app with empty locations."""
        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'PHOTOS_DIR', photos_dir)

        import webui.backend.routes.gallery as gallery
        monkeypatch.setattr(gallery, 'PHOTOS_DIR', photos_dir)

        mock_loc_service = Mock()
        mock_loc_service.get_locations.return_value = empty_locations
        monkeypatch.setattr(gallery, '_locations_service', mock_loc_service)

        app = Flask(__name__)
        app.config['TESTING'] = True

        with patch('webui.backend.services.clustering_service.LocationsService') as MockLS:
            MockLS.return_value = mock_loc_service
            clustering_service = ClusteringService(cache_ttl=60)
            app.config['CLUSTERING_SERVICE'] = clustering_service

        app.register_blueprint(gallery_bp, url_prefix='/api/gallery')
        return app

    def test_empty_locations(self, app_empty):
        """Handle empty location list gracefully."""
        client = app_empty.test_client()
        response = client.get('/api/gallery/locations/clustered')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['clusters'] == []
        assert data['unclustered'] == []
        assert data['metadata']['total_photos'] == 0

    def test_invalid_radius_parameter(self, app_empty):
        """Invalid radius returns 400."""
        client = app_empty.test_client()
        response = client.get('/api/gallery/locations/clustered?radius=-100')

        assert response.status_code == 400

    def test_non_numeric_radius(self, app_empty):
        """Non-numeric radius returns 400."""
        client = app_empty.test_client()
        response = client.get('/api/gallery/locations/clustered?radius=abc')

        assert response.status_code == 400

"""
Unit tests for ClusteringService (Issue #115 - Subtask 3)

Tests the cached clustering service for photo locations with thread-safety,
TTL management, and performance characteristics.
"""

import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from webui.backend.lib.geo_clustering import ClusteringResult, PhotoCluster, PhotoLocation
from webui.backend.services.clustering_service import ClusteringService


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_locations_service():
    """Mock LocationsService that returns test data."""
    mock = MagicMock()
    mock.get_locations.return_value = {
        'locations': [
            {
                "photo_path": "2024-01-15/photo1.jpg",
                "filename": "photo1.jpg",
                "latitude": 37.7749,
                "longitude": -122.4194,
                "timestamp": "2024-01-15T10:00:00",
                "thumbnail_url": "/api/gallery/thumbnail/2024-01-15/photo1.jpg"
            },
            {
                "photo_path": "2024-01-15/photo2.jpg",
                "filename": "photo2.jpg",
                "latitude": 37.7750,
                "longitude": -122.4195,
                "timestamp": "2024-01-15T11:00:00",
                "thumbnail_url": "/api/gallery/thumbnail/2024-01-15/photo2.jpg"
            },
            {
                "photo_path": "2024-01-15/photo3.jpg",
                "filename": "photo3.jpg",
                "latitude": 37.8000,
                "longitude": -122.4500,
                "timestamp": "2024-01-15T12:00:00",
                "thumbnail_url": "/api/gallery/thumbnail/2024-01-15/photo3.jpg"
            }
        ],
        'total_with_gps': 3,
        'total_without_gps': 0
    }
    return mock


@pytest.fixture
def service(mock_locations_service):
    """Create ClusteringService instance with mocked LocationsService."""
    with patch('webui.backend.services.clustering_service.LocationsService',
               return_value=mock_locations_service):
        service = ClusteringService(cache_ttl=300)
        service._locations_service = mock_locations_service
        return service


# ============================================================================
# Initialization Tests
# ============================================================================

class TestClusteringServiceInit:
    """Test ClusteringService initialization."""

    def test_initialization_default_params(self):
        """Service initializes with default parameters."""
        with patch('webui.backend.services.clustering_service.LocationsService'):
            service = ClusteringService()

            assert service._cache_ttl == 300
            assert service._default_radius_m == 100
            assert service._default_min_cluster_size == 2
            assert service._timeout_ms == 500
            assert service._cache == {}
            assert service._stats == {
                'cache_hits': 0,
                'cache_misses': 0,
                'total_clustering_time_ms': 0.0
            }

    def test_initialization_custom_params(self):
        """Service accepts custom parameters."""
        with patch('webui.backend.services.clustering_service.LocationsService'):
            service = ClusteringService(
                cache_ttl=600,
                default_radius_m=200,
                default_min_cluster_size=3,
                timeout_ms=1000
            )

            assert service._cache_ttl == 600
            assert service._default_radius_m == 200
            assert service._default_min_cluster_size == 3
            assert service._timeout_ms == 1000


# ============================================================================
# Get Clustered Locations Tests
# ============================================================================

class TestGetClusteredLocations:
    """Test get_clustered_locations method."""

    def test_returns_clustering_result(self, service):
        """Returns ClusteringResult object with expected structure."""
        result = service.get_clustered_locations()

        assert isinstance(result, ClusteringResult)
        assert hasattr(result, 'clusters')
        assert hasattr(result, 'unclustered')
        assert hasattr(result, 'total_photos')
        assert hasattr(result, 'total_clusters')
        assert hasattr(result, 'radius_m')
        assert hasattr(result, 'processing_time_ms')
        assert hasattr(result, 'partial_result')
        assert hasattr(result, 'warning')

    def test_uses_default_directory(self, service):
        """Uses PHOTOS_DIR when directory is None."""
        from mothbox_paths import PHOTOS_DIR

        result = service.get_clustered_locations(directory=None)

        # Should have called LocationsService with default directory
        service._locations_service.get_locations.assert_called()
        call_args = service._locations_service.get_locations.call_args
        # Check first positional argument or 'directory' kwarg
        assert call_args[0][0] == PHOTOS_DIR or call_args[1].get('directory') == PHOTOS_DIR

    def test_uses_cache_when_valid(self, service):
        """Cache hit returns cached result without re-clustering."""
        # First call - populates cache
        result1 = service.get_clustered_locations()

        # Reset mock to verify second call doesn't trigger LocationsService
        service._locations_service.get_locations.reset_mock()

        # Second call - should use cache
        result2 = service.get_clustered_locations()

        # Should NOT have called LocationsService again
        service._locations_service.get_locations.assert_not_called()

        # Should return same structure
        assert result2.total_photos == result1.total_photos
        assert result2.radius_m == result1.radius_m

        # Cache hit should be counted
        stats = service.get_statistics()
        assert stats['cache_hits'] == 1
        assert stats['cache_misses'] == 1  # Only first call

    def test_cache_miss_triggers_clustering(self, service):
        """Cache miss calls cluster_locations."""
        with patch('webui.backend.services.clustering_service.cluster_locations') as mock_cluster:
            # Setup mock to return valid ClusteringResult
            mock_cluster.return_value = ClusteringResult(
                clusters=[],
                unclustered=[],
                total_photos=3,
                total_clusters=0,
                radius_m=100,
                processing_time_ms=10.0
            )

            result = service.get_clustered_locations()

            # Should have called cluster_locations
            mock_cluster.assert_called_once()
            call_args = mock_cluster.call_args
            assert call_args[1]['radius_m'] == 100
            assert call_args[1]['min_cluster_size'] == 2

    def test_force_refresh_bypasses_cache(self, service):
        """force_refresh=True ignores cache and re-clusters."""
        # First call - populates cache
        result1 = service.get_clustered_locations()

        # Reset mock
        service._locations_service.get_locations.reset_mock()

        # Second call with force_refresh - should bypass cache
        result2 = service.get_clustered_locations(force_refresh=True)

        # Should have called LocationsService again
        service._locations_service.get_locations.assert_called_once()

        # Cache misses should increase
        stats = service.get_statistics()
        assert stats['cache_misses'] == 2  # Both calls are cache misses

    def test_radius_change_invalidates_cache(self, service):
        """Different radius triggers re-clustering."""
        # First call with radius=100
        result1 = service.get_clustered_locations(radius_m=100)

        # Reset mock
        service._locations_service.get_locations.reset_mock()

        # Second call with radius=200 - different cache key
        result2 = service.get_clustered_locations(radius_m=200)

        # Should have called LocationsService again
        service._locations_service.get_locations.assert_called_once()

        # Both should be cache misses (different keys)
        stats = service.get_statistics()
        assert stats['cache_misses'] == 2

    def test_min_cluster_size_change_invalidates_cache(self, service):
        """Different min_cluster_size triggers re-clustering."""
        # First call with min_cluster_size=2
        result1 = service.get_clustered_locations(min_cluster_size=2)

        # Reset mock
        service._locations_service.get_locations.reset_mock()

        # Second call with min_cluster_size=3 - different cache key
        result2 = service.get_clustered_locations(min_cluster_size=3)

        # Should have called LocationsService again
        service._locations_service.get_locations.assert_called_once()

    def test_empty_locations_handled(self, service):
        """Empty location list returns empty result."""
        # Mock empty locations
        service._locations_service.get_locations.return_value = {
            'locations': [],
            'total_with_gps': 0,
            'total_without_gps': 10
        }

        result = service.get_clustered_locations()

        assert result.total_photos == 0
        assert result.total_clusters == 0
        assert len(result.clusters) == 0
        assert len(result.unclustered) == 0

    def test_cache_ttl_expiration(self, service):
        """Cache expires after TTL and re-clusters."""
        # Use very short TTL for testing
        service._cache_ttl = 0.1  # 100ms

        # First call
        result1 = service.get_clustered_locations()

        # Wait for cache to expire
        time.sleep(0.2)

        # Reset mock
        service._locations_service.get_locations.reset_mock()

        # Second call - cache should be expired
        result2 = service.get_clustered_locations()

        # Should have called LocationsService again
        service._locations_service.get_locations.assert_called_once()

        # Should have 2 cache misses (first call + expired)
        stats = service.get_statistics()
        assert stats['cache_misses'] == 2


# ============================================================================
# Cache Invalidation Tests
# ============================================================================

class TestCacheInvalidation:
    """Test cache invalidation methods."""

    def test_invalidate_specific_directory(self, service):
        """Invalidate single directory cache."""
        directory = Path("/var/lib/mothbox/photos")

        # Populate cache
        service.get_clustered_locations(directory=directory)

        # Verify cached
        stats = service.get_statistics()
        assert stats['cache_entries'] == 1

        # Invalidate specific directory
        service.invalidate_cache(directory=directory)

        # Cache should be empty for that directory
        stats = service.get_statistics()
        assert stats['cache_entries'] == 0

    def test_invalidate_all_caches(self, service):
        """Invalidate all cached results."""
        # Populate cache with different parameters
        service.get_clustered_locations(radius_m=100)
        service.get_clustered_locations(radius_m=200)

        # Verify cached
        stats = service.get_statistics()
        assert stats['cache_entries'] == 2

        # Invalidate all
        service.invalidate_cache()

        # All caches should be cleared
        stats = service.get_statistics()
        assert stats['cache_entries'] == 0


# ============================================================================
# Cache Statistics Tests
# ============================================================================

class TestCacheStatistics:
    """Test cache statistics tracking."""

    def test_statistics_structure(self, service):
        """Statistics dict has expected keys."""
        stats = service.get_statistics()

        assert 'cache_hits' in stats
        assert 'cache_misses' in stats
        assert 'cache_entries' in stats
        assert 'total_clustering_time_ms' in stats

    def test_cache_hits_counted(self, service):
        """Cache hits are tracked correctly."""
        # First call - miss
        service.get_clustered_locations()

        # Second call - hit
        service.get_clustered_locations()

        # Third call - hit
        service.get_clustered_locations()

        stats = service.get_statistics()
        assert stats['cache_hits'] == 2
        assert stats['cache_misses'] == 1

    def test_cache_misses_counted(self, service):
        """Cache misses are tracked correctly."""
        # Three different parameter combinations - all misses
        service.get_clustered_locations(radius_m=100)
        service.get_clustered_locations(radius_m=200)
        service.get_clustered_locations(radius_m=300)

        stats = service.get_statistics()
        assert stats['cache_misses'] == 3
        assert stats['cache_hits'] == 0

    def test_clustering_time_accumulated(self, service):
        """Total clustering time is accumulated across calls."""
        # Make multiple calls
        service.get_clustered_locations()
        service.get_clustered_locations(force_refresh=True)

        stats = service.get_statistics()
        # Should have accumulated time from 2 clustering operations
        assert stats['total_clustering_time_ms'] > 0


# ============================================================================
# Thread Safety Tests
# ============================================================================

class TestThreadSafety:
    """Test thread-safe concurrent access."""

    def test_concurrent_access(self, service):
        """Multiple threads can access safely without race conditions."""
        results = []
        errors = []

        def worker():
            try:
                result = service.get_clustered_locations()
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Start 10 threads
        threads = []
        for _ in range(10):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Should have no errors
        assert len(errors) == 0

        # Should have 10 results
        assert len(results) == 10

        # All results should be valid ClusteringResult objects
        for result in results:
            assert isinstance(result, ClusteringResult)

        # Stats should show correct counts (1 miss + 9 hits for concurrent access to same key)
        stats = service.get_statistics()
        assert stats['cache_hits'] + stats['cache_misses'] == 10

    def test_concurrent_different_parameters(self, service):
        """Concurrent access with different parameters doesn't cause conflicts."""
        results = []
        errors = []

        def worker(radius):
            try:
                result = service.get_clustered_locations(radius_m=radius)
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Start threads with different radii
        threads = []
        for radius in [50, 100, 150, 200, 250]:
            t = threading.Thread(target=worker, args=(radius,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Should have no errors
        assert len(errors) == 0

        # Should have 5 results
        assert len(results) == 5

        # Should have 5 cache entries (different parameters)
        stats = service.get_statistics()
        assert stats['cache_entries'] == 5


# ============================================================================
# Integration Tests with Real Clustering
# ============================================================================

class TestRealClustering:
    """Test with actual cluster_locations function."""

    def test_clusters_nearby_photos(self, service):
        """Photos within radius are clustered together."""
        # Mock locations with two nearby photos and one far away
        service._locations_service.get_locations.return_value = {
            'locations': [
                {
                    "photo_path": "photo1.jpg",
                    "filename": "photo1.jpg",
                    "latitude": 37.7749,
                    "longitude": -122.4194,
                    "timestamp": "2024-01-15T10:00:00",
                    "thumbnail_url": "/api/thumbnail/photo1.jpg"
                },
                {
                    "photo_path": "photo2.jpg",
                    "filename": "photo2.jpg",
                    "latitude": 37.7750,  # ~11 meters from photo1
                    "longitude": -122.4194,
                    "timestamp": "2024-01-15T11:00:00",
                    "thumbnail_url": "/api/thumbnail/photo2.jpg"
                },
                {
                    "photo_path": "photo3.jpg",
                    "filename": "photo3.jpg",
                    "latitude": 38.0000,  # ~25km from photo1
                    "longitude": -122.5000,
                    "timestamp": "2024-01-15T12:00:00",
                    "thumbnail_url": "/api/thumbnail/photo3.jpg"
                }
            ],
            'total_with_gps': 3,
            'total_without_gps': 0
        }

        result = service.get_clustered_locations(radius_m=100)

        # Should have 1 cluster (photo1 + photo2) and 1 unclustered (photo3)
        assert result.total_clusters == 1
        assert len(result.clusters) == 1
        assert len(result.unclustered) == 1

        # Cluster should have 2 photos
        cluster = result.clusters[0]
        assert cluster.count == 2

    def test_min_cluster_size_filtering(self, service):
        """Photos below min_cluster_size go to unclustered."""
        # Mock locations with 3 separate photos (no clusters)
        service._locations_service.get_locations.return_value = {
            'locations': [
                {
                    "photo_path": "photo1.jpg",
                    "filename": "photo1.jpg",
                    "latitude": 37.0000,
                    "longitude": -122.0000,
                    "timestamp": "2024-01-15T10:00:00",
                    "thumbnail_url": "/api/thumbnail/photo1.jpg"
                },
                {
                    "photo_path": "photo2.jpg",
                    "filename": "photo2.jpg",
                    "latitude": 38.0000,
                    "longitude": -122.0000,
                    "timestamp": "2024-01-15T11:00:00",
                    "thumbnail_url": "/api/thumbnail/photo2.jpg"
                },
                {
                    "photo_path": "photo3.jpg",
                    "filename": "photo3.jpg",
                    "latitude": 39.0000,
                    "longitude": -122.0000,
                    "timestamp": "2024-01-15T12:00:00",
                    "thumbnail_url": "/api/thumbnail/photo3.jpg"
                }
            ],
            'total_with_gps': 3,
            'total_without_gps': 0
        }

        result = service.get_clustered_locations(radius_m=100, min_cluster_size=2)

        # All should be unclustered (no clusters of size >= 2)
        assert result.total_clusters == 0
        assert len(result.clusters) == 0
        assert len(result.unclustered) == 3

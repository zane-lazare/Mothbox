"""
Unit tests for Locations Service (Issue #113 - Fix 6)

Tests LocationsService with caching, thread-safety, and two-pass scanning.
TDD approach: tests written first, then implementation.

Addresses code review feedback:
- Fix 6: Add LocationsService with caching (following SeriesService pattern)
- Fix 1: Two-pass approach for accurate counts
- Fix 5: Avoid repeated EXIF loads
- Fix 9: Use iterators

Coverage Target: 90%+
"""

import pytest
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


# Import will fail until implementation exists - that's expected in TDD
try:
    from webui.backend.services.locations_service import LocationsService
    IMPLEMENTATION_EXISTS = True
except ImportError:
    IMPLEMENTATION_EXISTS = False
    LocationsService = None


# Skip all tests if implementation doesn't exist yet (TDD red phase)
pytestmark = pytest.mark.skipif(
    not IMPLEMENTATION_EXISTS,
    reason="Implementation not yet created (TDD red phase)"
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_photos_dir(tmp_path):
    """Create temporary photos directory with sample photos."""
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()
    return photos_dir


@pytest.fixture
def mock_gps_photo(temp_photos_dir):
    """Create a mock photo with GPS data."""
    photo = temp_photos_dir / "photo_with_gps.jpg"
    # Create minimal valid JPEG
    photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
    return photo


@pytest.fixture
def mock_no_gps_photo(temp_photos_dir):
    """Create a mock photo without GPS data."""
    photo = temp_photos_dir / "photo_no_gps.jpg"
    # Create minimal valid JPEG
    photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
    return photo


@pytest.fixture
def service(temp_photos_dir):
    """Create LocationsService instance with short TTL for testing."""
    return LocationsService(cache_ttl=1)  # 1 second TTL for fast testing


# ============================================================================
# Test LocationsService Initialization
# ============================================================================

class TestLocationsServiceInit:
    """Tests for LocationsService initialization."""

    def test_service_creation_default_ttl(self):
        """LocationsService should be created with default TTL."""
        service = LocationsService()
        assert service is not None
        assert service._cache_ttl == 300  # Default 5 minutes

    def test_service_creation_custom_ttl(self):
        """LocationsService should accept custom TTL."""
        service = LocationsService(cache_ttl=60)
        assert service._cache_ttl == 60

    def test_service_starts_with_empty_cache(self):
        """LocationsService should start with empty cache."""
        service = LocationsService()
        stats = service.get_statistics()
        assert stats['cache_entries'] == 0
        assert stats['cache_hits'] == 0
        assert stats['cache_misses'] == 0


# ============================================================================
# Test get_locations Method
# ============================================================================

class TestGetLocations:
    """Tests for get_locations method."""

    def test_get_locations_returns_dict(self, service, temp_photos_dir):
        """get_locations should return dict with expected keys."""
        with patch('webui.backend.lib.gps_exif_lib.verify_gps_exif') as mock_verify:
            mock_verify.return_value = {'has_gps': False}

            result = service.get_locations(temp_photos_dir, limit=100)

            assert isinstance(result, dict)
            assert 'locations' in result
            assert 'total_with_gps' in result
            assert 'total_without_gps' in result

    def test_get_locations_empty_directory(self, service, temp_photos_dir):
        """get_locations should return empty list for empty directory."""
        result = service.get_locations(temp_photos_dir, limit=100)

        assert result['locations'] == []
        assert result['total_with_gps'] == 0
        assert result['total_without_gps'] == 0

    def test_get_locations_respects_limit(self, service, temp_photos_dir):
        """get_locations should respect limit parameter."""
        # Create 5 photos with GPS
        for i in range(5):
            photo = temp_photos_dir / f"photo_{i}.jpg"
            photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        with patch('webui.backend.lib.gps_exif_lib.verify_gps_exif') as mock_verify:
            # All photos have GPS
            mock_verify.return_value = {
                'has_gps': True,
                'latitude': 37.7749,
                'longitude': -122.4194,
                'timestamp': '2025:01:15 12:30:00'
            }

            result = service.get_locations(temp_photos_dir, limit=3)

            # Should return exactly 3 locations (limit)
            assert len(result['locations']) == 3
            # But total_with_gps should be accurate (5)
            assert result['total_with_gps'] == 5
            assert result['total_without_gps'] == 0

    def test_get_locations_mixed_gps_status(self, service, temp_photos_dir):
        """get_locations should count both GPS and non-GPS photos."""
        # Create 3 photos with GPS, 2 without
        for i in range(5):
            photo = temp_photos_dir / f"photo_{i}.jpg"
            photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        def mock_verify_side_effect(photo_path):
            # First 3 photos have GPS, last 2 don't
            filename = photo_path.name
            if filename in ['photo_0.jpg', 'photo_1.jpg', 'photo_2.jpg']:
                return {
                    'has_gps': True,
                    'latitude': 37.7749,
                    'longitude': -122.4194,
                    'timestamp': '2025:01:15 12:30:00'
                }
            else:
                return {'has_gps': False}

        with patch('webui.backend.lib.gps_exif_lib.verify_gps_exif', side_effect=mock_verify_side_effect):
            result = service.get_locations(temp_photos_dir, limit=100)

            assert len(result['locations']) == 3  # Only GPS photos
            assert result['total_with_gps'] == 3
            assert result['total_without_gps'] == 2

    def test_get_locations_uses_verify_gps_exif_timestamp(self, service, temp_photos_dir):
        """get_locations should use timestamp from verify_gps_exif (Fix 5)."""
        photo = temp_photos_dir / "photo.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        with patch('webui.backend.lib.gps_exif_lib.verify_gps_exif') as mock_verify:
            mock_verify.return_value = {
                'has_gps': True,
                'latitude': 37.7749,
                'longitude': -122.4194,
                'timestamp': '2025:01:15 12:30:00'  # Already in verify_gps_exif
            }

            result = service.get_locations(temp_photos_dir, limit=100)

            # Should use timestamp from verify_gps_exif, not load EXIF again
            assert len(result['locations']) == 1
            assert result['locations'][0]['timestamp'] == '2025-01-15T12:30:00'
            # verify_gps_exif should only be called once per photo
            assert mock_verify.call_count == 1


# ============================================================================
# Test Caching Behavior
# ============================================================================

class TestCaching:
    """Tests for caching functionality."""

    def test_caching_returns_same_results(self, service, temp_photos_dir):
        """Second call should return cached results."""
        photo = temp_photos_dir / "photo.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        with patch('webui.backend.lib.gps_exif_lib.verify_gps_exif') as mock_verify:
            mock_verify.return_value = {
                'has_gps': True,
                'latitude': 37.7749,
                'longitude': -122.4194,
                'timestamp': '2025:01:15 12:30:00'
            }

            # First call - cache miss
            result1 = service.get_locations(temp_photos_dir, limit=100)
            call_count_after_first = mock_verify.call_count

            # Second call - cache hit
            result2 = service.get_locations(temp_photos_dir, limit=100)
            call_count_after_second = mock_verify.call_count

            # Results should be identical
            assert result1 == result2
            # verify_gps_exif should NOT be called again (cache hit)
            assert call_count_after_second == call_count_after_first

    def test_cache_statistics_incremented(self, service, temp_photos_dir):
        """Cache statistics should track hits and misses."""
        photo = temp_photos_dir / "photo.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        with patch('webui.backend.lib.gps_exif_lib.verify_gps_exif') as mock_verify:
            mock_verify.return_value = {'has_gps': False}

            # First call - cache miss
            service.get_locations(temp_photos_dir, limit=100)
            stats1 = service.get_statistics()
            assert stats1['cache_misses'] == 1
            assert stats1['cache_hits'] == 0

            # Second call - cache hit
            service.get_locations(temp_photos_dir, limit=100)
            stats2 = service.get_statistics()
            assert stats2['cache_misses'] == 1
            assert stats2['cache_hits'] == 1

    def test_cache_expires_after_ttl(self, temp_photos_dir):
        """Cache should expire after TTL."""
        service = LocationsService(cache_ttl=1)  # 1 second TTL
        photo = temp_photos_dir / "photo.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        with patch('webui.backend.lib.gps_exif_lib.verify_gps_exif') as mock_verify:
            mock_verify.return_value = {'has_gps': False}

            # First call
            service.get_locations(temp_photos_dir, limit=100)
            call_count_after_first = mock_verify.call_count

            # Wait for TTL expiration
            time.sleep(1.1)

            # Second call after TTL - should trigger new scan
            service.get_locations(temp_photos_dir, limit=100)
            call_count_after_second = mock_verify.call_count

            # verify_gps_exif should be called again (cache expired)
            assert call_count_after_second > call_count_after_first


# ============================================================================
# Test Cache Invalidation
# ============================================================================

class TestCacheInvalidation:
    """Tests for cache invalidation."""

    def test_invalidate_entire_cache(self, service, temp_photos_dir):
        """invalidate_cache() should clear entire cache."""
        photo = temp_photos_dir / "photo.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        with patch('webui.backend.lib.gps_exif_lib.verify_gps_exif') as mock_verify:
            mock_verify.return_value = {'has_gps': False}

            # Populate cache
            service.get_locations(temp_photos_dir, limit=100)
            stats1 = service.get_statistics()
            assert stats1['cache_entries'] == 1

            # Invalidate entire cache
            service.invalidate_cache()
            stats2 = service.get_statistics()
            assert stats2['cache_entries'] == 0

    def test_invalidate_specific_directory(self, service, tmp_path):
        """invalidate_cache(directory) should clear specific directory cache."""
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        photo1 = dir1 / "photo.jpg"
        photo2 = dir2 / "photo.jpg"
        photo1.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
        photo2.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        with patch('webui.backend.lib.gps_exif_lib.verify_gps_exif') as mock_verify:
            mock_verify.return_value = {'has_gps': False}

            # Populate cache for both directories
            service.get_locations(dir1, limit=100)
            service.get_locations(dir2, limit=100)
            stats1 = service.get_statistics()
            assert stats1['cache_entries'] == 2

            # Invalidate only dir1
            service.invalidate_cache(dir1)
            stats2 = service.get_statistics()
            assert stats2['cache_entries'] == 1


# ============================================================================
# Test Statistics
# ============================================================================

class TestStatistics:
    """Tests for get_statistics method."""

    def test_get_statistics_returns_dict(self, service):
        """get_statistics should return dict with expected keys."""
        stats = service.get_statistics()

        assert isinstance(stats, dict)
        assert 'cache_entries' in stats
        assert 'cache_hits' in stats
        assert 'cache_misses' in stats
        assert 'total_locations' in stats

    def test_statistics_counts_locations_across_cache(self, service, tmp_path):
        """Statistics should count total locations across all cached directories."""
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        # Dir1 has 2 photos with GPS
        for i in range(2):
            photo = dir1 / f"photo_{i}.jpg"
            photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        # Dir2 has 3 photos with GPS
        for i in range(3):
            photo = dir2 / f"photo_{i}.jpg"
            photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        with patch('webui.backend.lib.gps_exif_lib.verify_gps_exif') as mock_verify:
            mock_verify.return_value = {
                'has_gps': True,
                'latitude': 37.7749,
                'longitude': -122.4194,
                'timestamp': '2025:01:15 12:30:00'
            }

            service.get_locations(dir1, limit=100)
            service.get_locations(dir2, limit=100)

            stats = service.get_statistics()
            assert stats['cache_entries'] == 2
            assert stats['total_locations'] == 5  # 2 + 3


# ============================================================================
# Test Thread Safety
# ============================================================================

class TestThreadSafety:
    """Tests for thread-safe operations."""

    def test_concurrent_access_safe(self, service, temp_photos_dir):
        """Multiple threads should be able to access cache safely."""
        photo = temp_photos_dir / "photo.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        with patch('webui.backend.lib.gps_exif_lib.verify_gps_exif') as mock_verify:
            mock_verify.return_value = {'has_gps': False}

            results = []
            errors = []

            def worker():
                try:
                    result = service.get_locations(temp_photos_dir, limit=100)
                    results.append(result)
                except Exception as e:
                    errors.append(e)

            # Start 5 threads
            threads = [threading.Thread(target=worker) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # No errors should occur
            assert len(errors) == 0
            # All results should be identical
            assert len(results) == 5
            assert all(r == results[0] for r in results)


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_nonexistent_directory(self, service):
        """get_locations should handle nonexistent directory gracefully."""
        result = service.get_locations(Path("/nonexistent/path"), limit=100)

        assert result['locations'] == []
        assert result['total_with_gps'] == 0
        assert result['total_without_gps'] == 0

    def test_handles_corrupted_photo(self, service, temp_photos_dir):
        """get_locations should handle corrupted photos gracefully."""
        good_photo = temp_photos_dir / "good.jpg"
        bad_photo = temp_photos_dir / "bad.jpg"
        good_photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
        bad_photo.write_bytes(b'corrupted')

        def mock_verify_side_effect(photo_path):
            if photo_path.name == 'good.jpg':
                return {
                    'has_gps': True,
                    'latitude': 37.7749,
                    'longitude': -122.4194,
                    'timestamp': '2025:01:15 12:30:00'
                }
            else:
                raise Exception("Corrupted EXIF")

        with patch('webui.backend.lib.gps_exif_lib.verify_gps_exif', side_effect=mock_verify_side_effect):
            result = service.get_locations(temp_photos_dir, limit=100)

            # Should process good photo, skip bad photo
            assert len(result['locations']) == 1
            assert result['total_with_gps'] == 1
            assert result['total_without_gps'] == 1  # Bad photo counted as no GPS

    def test_accepts_string_or_path(self, service, temp_photos_dir):
        """get_locations should accept both string and Path."""
        photo = temp_photos_dir / "photo.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        with patch('webui.backend.lib.gps_exif_lib.verify_gps_exif') as mock_verify:
            mock_verify.return_value = {'has_gps': False}

            # Call with Path object
            result1 = service.get_locations(temp_photos_dir, limit=100)

            # Call with string
            result2 = service.get_locations(str(temp_photos_dir), limit=100)

            # Results should be identical
            assert result1 == result2

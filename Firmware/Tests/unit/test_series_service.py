"""
Unit tests for Series Service (Issue #110 - Phase 3)

Tests SeriesService with caching, thread-safety, and cross-directory support.
TDD approach: tests written first, then implementation.

Coverage Target: 90%+
"""

import pytest
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass


# Import will fail until implementation exists - that's expected in TDD
try:
    from webui.backend.services.series_service import (
        SeriesService,
        PhotoSeries,
    )
    IMPLEMENTATION_EXISTS = True
except ImportError:
    IMPLEMENTATION_EXISTS = False
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
def temp_photos_dir(tmp_path):
    """Create temporary photos directory with sample photos."""
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()
    return photos_dir


@pytest.fixture
def sample_hdr_series(temp_photos_dir):
    """Create HDR series in photos directory."""
    base = "moth_2024_01_15__10_00_00"
    photos = []
    for i in range(3):
        p = temp_photos_dir / f"{base}_HDR{i}.jpg"
        p.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
        photos.append(p)
    return photos


@pytest.fixture
def sample_fb_series(temp_photos_dir):
    """Create Focus Bracket series in photos directory."""
    base = "ManFocus_moth_2024_01_15__11_00_00_000000"
    photos = []
    for i in range(5):
        p = temp_photos_dir / f"{base}_FB{i}.jpg"
        p.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
        photos.append(p)
    return photos


@pytest.fixture
def mixed_photos_dir(temp_photos_dir):
    """Create directory with HDR, FB, and regular photos."""
    # HDR series (3 photos)
    for i in range(3):
        p = temp_photos_dir / f"moth_2024_01_15__10_00_00_HDR{i}.jpg"
        p.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

    # FB series (5 photos)
    for i in range(5):
        p = temp_photos_dir / f"ManFocus_moth_2024_01_15__11_00_00_000000_FB{i}.jpg"
        p.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

    # Regular photos
    for name in ["regular1.jpg", "regular2.jpg"]:
        p = temp_photos_dir / name
        p.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

    return temp_photos_dir


@pytest.fixture
def service(temp_photos_dir):
    """Create SeriesService instance with short TTL for testing."""
    return SeriesService(cache_ttl=1)  # 1 second TTL for fast testing


# ============================================================================
# Test PhotoSeries Data Class
# ============================================================================

class TestPhotoSeriesDataClass:
    """Tests for PhotoSeries data class structure."""

    def test_photo_series_has_required_fields(self, temp_photos_dir):
        """PhotoSeries should have all required fields."""
        series = PhotoSeries(
            series_id="hdr_moth_2024_01_15__10_00_00",
            series_type="hdr",
            base_name="moth_2024_01_15__10_00_00",
            photos=[temp_photos_dir / "test.jpg"],
            count=1,
            cover_photo=temp_photos_dir / "test.jpg"
        )

        assert series.series_id == "hdr_moth_2024_01_15__10_00_00"
        assert series.series_type == "hdr"
        assert series.base_name == "moth_2024_01_15__10_00_00"
        assert len(series.photos) == 1
        assert series.count == 1
        assert series.cover_photo is not None


# ============================================================================
# Test SeriesService Initialization
# ============================================================================

class TestSeriesServiceInit:
    """Tests for SeriesService initialization."""

    def test_service_creation_default_ttl(self):
        """SeriesService should be created with default TTL."""
        service = SeriesService()
        assert service is not None
        assert service._cache_ttl == 300  # Default 5 minutes

    def test_service_creation_custom_ttl(self):
        """SeriesService should accept custom TTL."""
        service = SeriesService(cache_ttl=60)
        assert service._cache_ttl == 60

    def test_service_starts_with_empty_cache(self):
        """SeriesService should start with empty cache."""
        service = SeriesService()
        stats = service.get_statistics()
        assert stats['cache_entries'] == 0


# ============================================================================
# Test get_series_for_directory
# ============================================================================

class TestGetSeriesForDirectory:
    """Tests for get_series_for_directory method."""

    def test_get_series_from_empty_directory(self, service, temp_photos_dir):
        """Empty directory should return empty list."""
        series_list = service.get_series_for_directory(temp_photos_dir)
        assert series_list == []

    def test_get_hdr_series(self, service, temp_photos_dir, sample_hdr_series):
        """Should detect HDR series correctly."""
        series_list = service.get_series_for_directory(temp_photos_dir)

        assert len(series_list) == 1
        series = series_list[0]
        assert series.series_type == "hdr"
        assert series.count == 3
        assert len(series.photos) == 3

    def test_get_fb_series(self, service, temp_photos_dir, sample_fb_series):
        """Should detect Focus Bracket series correctly."""
        series_list = service.get_series_for_directory(temp_photos_dir)

        assert len(series_list) == 1
        series = series_list[0]
        assert series.series_type == "focus_bracket"
        assert series.count == 5

    def test_get_multiple_series(self, service, mixed_photos_dir):
        """Should detect multiple series in directory."""
        series_list = service.get_series_for_directory(mixed_photos_dir)

        assert len(series_list) == 2

        types = {s.series_type for s in series_list}
        assert types == {"hdr", "focus_bracket"}

    def test_regular_photos_excluded(self, service, mixed_photos_dir):
        """Regular photos should not create series."""
        series_list = service.get_series_for_directory(mixed_photos_dir)

        # Should only have HDR and FB series, not regular photos
        assert len(series_list) == 2

        # Verify no single-photo "series"
        for series in series_list:
            assert series.count > 1

    def test_series_sorted_by_timestamp(self, service, temp_photos_dir):
        """Series should be sorted by base_name (timestamp)."""
        # Create two HDR series with different timestamps
        for i in range(3):
            p = temp_photos_dir / f"moth_2024_01_15__12_00_00_HDR{i}.jpg"
            p.write_bytes(b'\xFF\xD8\xFF\xE0')

        for i in range(3):
            p = temp_photos_dir / f"moth_2024_01_15__10_00_00_HDR{i}.jpg"
            p.write_bytes(b'\xFF\xD8\xFF\xE0')

        series_list = service.get_series_for_directory(temp_photos_dir)

        assert len(series_list) == 2
        # Should be sorted by base_name
        assert series_list[0].base_name < series_list[1].base_name

    def test_cover_photo_is_first_in_series(self, service, temp_photos_dir, sample_hdr_series):
        """Cover photo should be the first photo in series (index 0)."""
        series_list = service.get_series_for_directory(temp_photos_dir)

        series = series_list[0]
        assert "HDR0" in series.cover_photo.name

    def test_photos_sorted_by_index(self, service, temp_photos_dir, sample_hdr_series):
        """Photos within series should be sorted by index."""
        series_list = service.get_series_for_directory(temp_photos_dir)

        series = series_list[0]
        for i, photo in enumerate(series.photos):
            assert f"HDR{i}" in photo.name

    def test_nonexistent_directory_returns_empty(self, service, tmp_path):
        """Nonexistent directory should return empty list."""
        nonexistent = tmp_path / "nonexistent"
        series_list = service.get_series_for_directory(nonexistent)
        assert series_list == []

    def test_accepts_path_string(self, service, temp_photos_dir, sample_hdr_series):
        """Should accept directory as string."""
        series_list = service.get_series_for_directory(str(temp_photos_dir))
        assert len(series_list) == 1


# ============================================================================
# Test Caching Behavior
# ============================================================================

class TestCaching:
    """Tests for cache behavior."""

    def test_cache_hit_on_second_call(self, service, temp_photos_dir, sample_hdr_series):
        """Second call should use cache."""
        # First call - cache miss
        series1 = service.get_series_for_directory(temp_photos_dir)
        stats1 = service.get_statistics()

        # Second call - cache hit
        series2 = service.get_series_for_directory(temp_photos_dir)
        stats2 = service.get_statistics()

        assert series1 == series2
        assert stats2['cache_hits'] == stats1['cache_hits'] + 1

    def test_cache_miss_tracked(self, service, temp_photos_dir):
        """Cache misses should be tracked."""
        stats1 = service.get_statistics()
        initial_misses = stats1['cache_misses']

        service.get_series_for_directory(temp_photos_dir)
        stats2 = service.get_statistics()

        assert stats2['cache_misses'] == initial_misses + 1

    def test_cache_expiry_ttl(self, temp_photos_dir, sample_hdr_series):
        """Cache should expire after TTL."""
        service = SeriesService(cache_ttl=0.1)  # 100ms TTL

        # First call
        service.get_series_for_directory(temp_photos_dir)
        stats1 = service.get_statistics()

        # Wait for TTL to expire
        time.sleep(0.15)

        # Second call - should be cache miss
        service.get_series_for_directory(temp_photos_dir)
        stats2 = service.get_statistics()

        # Should have two misses (initial + after expiry)
        assert stats2['cache_misses'] == stats1['cache_misses'] + 1

    def test_cache_invalidation_all(self, service, temp_photos_dir, sample_hdr_series):
        """invalidate_cache() should clear all cache."""
        # Populate cache
        service.get_series_for_directory(temp_photos_dir)

        stats1 = service.get_statistics()
        assert stats1['cache_entries'] == 1

        # Invalidate all
        service.invalidate_cache()

        stats2 = service.get_statistics()
        assert stats2['cache_entries'] == 0

    def test_cache_invalidation_specific_directory(self, service, tmp_path):
        """invalidate_cache(directory) should only clear that directory."""
        # Create two directories
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        # Add photos to both
        (dir1 / "moth_2024_01_15__10_00_00_HDR0.jpg").write_bytes(b'\xFF\xD8\xFF\xE0')
        (dir1 / "moth_2024_01_15__10_00_00_HDR1.jpg").write_bytes(b'\xFF\xD8\xFF\xE0')
        (dir2 / "moth_2024_01_15__11_00_00_HDR0.jpg").write_bytes(b'\xFF\xD8\xFF\xE0')
        (dir2 / "moth_2024_01_15__11_00_00_HDR1.jpg").write_bytes(b'\xFF\xD8\xFF\xE0')

        # Populate cache for both
        service.get_series_for_directory(dir1)
        service.get_series_for_directory(dir2)

        stats1 = service.get_statistics()
        assert stats1['cache_entries'] == 2

        # Invalidate only dir1
        service.invalidate_cache(dir1)

        stats2 = service.get_statistics()
        assert stats2['cache_entries'] == 1


# ============================================================================
# Test get_series_by_id
# ============================================================================

class TestGetSeriesById:
    """Tests for get_series_by_id method."""

    def test_get_existing_series(self, service, temp_photos_dir, sample_hdr_series):
        """Should return series by ID."""
        # First populate cache
        series_list = service.get_series_for_directory(temp_photos_dir)
        series_id = series_list[0].series_id

        # Get by ID
        result = service.get_series_by_id(series_id)

        assert result is not None
        assert result.series_id == series_id
        assert result.series_type == "hdr"

    def test_get_nonexistent_series(self, service, temp_photos_dir):
        """Should return None for nonexistent series ID."""
        result = service.get_series_by_id("nonexistent_series_id")
        assert result is None

    def test_get_series_from_specific_directory(self, service, temp_photos_dir, sample_hdr_series):
        """Should find series when directory hint provided."""
        series_list = service.get_series_for_directory(temp_photos_dir)
        series_id = series_list[0].series_id

        # Get by ID with directory hint
        result = service.get_series_by_id(series_id, directory=temp_photos_dir)

        assert result is not None
        assert result.series_id == series_id


# ============================================================================
# Test Thread Safety
# ============================================================================

class TestThreadSafety:
    """Tests for thread-safe cache operations."""

    def test_concurrent_reads(self, service, temp_photos_dir, sample_hdr_series):
        """Multiple concurrent reads should work safely."""
        results = []
        errors = []

        def read_series():
            try:
                series = service.get_series_for_directory(temp_photos_dir)
                results.append(len(series))
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=read_series) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert all(r == 1 for r in results)  # All should see 1 series

    def test_concurrent_invalidate_and_read(self, service, temp_photos_dir, sample_hdr_series):
        """Concurrent invalidation and reads should work safely."""
        errors = []

        def read_and_invalidate():
            try:
                service.get_series_for_directory(temp_photos_dir)
                service.invalidate_cache()
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=read_and_invalidate) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


# ============================================================================
# Test Statistics
# ============================================================================

class TestStatistics:
    """Tests for get_statistics method."""

    def test_statistics_structure(self, service):
        """Statistics should have expected fields."""
        stats = service.get_statistics()

        assert 'cache_entries' in stats
        assert 'cache_hits' in stats
        assert 'cache_misses' in stats
        assert 'total_series' in stats
        assert 'series_by_type' in stats

    def test_statistics_updates_after_operations(self, service, temp_photos_dir, sample_hdr_series):
        """Statistics should update after operations."""
        stats1 = service.get_statistics()
        initial_misses = stats1['cache_misses']

        service.get_series_for_directory(temp_photos_dir)

        stats2 = service.get_statistics()
        assert stats2['cache_misses'] == initial_misses + 1
        assert stats2['cache_entries'] == 1
        assert stats2['total_series'] == 1

    def test_statistics_series_by_type(self, service, mixed_photos_dir):
        """Statistics should count series by type."""
        service.get_series_for_directory(mixed_photos_dir)
        stats = service.get_statistics()

        assert stats['series_by_type']['hdr'] == 1
        assert stats['series_by_type']['focus_bracket'] == 1


# ============================================================================
# Test Cross-Directory Series
# ============================================================================

class TestCrossDirectorySeries:
    """Tests for series spanning multiple directories."""

    def test_series_spans_directories(self, service, tmp_path):
        """Series with same base_name in different dirs should group together."""
        dir1 = tmp_path / "2024-01-15"
        dir2 = tmp_path / "2024-01-16"
        dir1.mkdir()
        dir2.mkdir()

        # Same series base_name in both directories
        base = "moth_2024_01_15__23_59_59"
        (dir1 / f"{base}_HDR0.jpg").write_bytes(b'\xFF\xD8\xFF\xE0')
        (dir2 / f"{base}_HDR1.jpg").write_bytes(b'\xFF\xD8\xFF\xE0')

        # Scan parent directory
        series_list = service.get_series_for_directory(tmp_path)

        # Should find one series with 2 photos
        assert len(series_list) == 1
        assert series_list[0].count == 2


# ============================================================================
# Test Error Handling
# ============================================================================

class TestErrorHandling:
    """Tests for error handling."""

    def test_permission_error_handled(self, service, tmp_path, monkeypatch):
        """Permission errors should return empty list."""
        def raise_permission_error(*args, **kwargs):
            raise PermissionError("Access denied")

        with patch('pathlib.Path.glob', side_effect=raise_permission_error):
            result = service.get_series_for_directory(tmp_path)
            assert result == []

    def test_io_error_handled(self, service, tmp_path, monkeypatch):
        """I/O errors should return empty list."""
        def raise_io_error(*args, **kwargs):
            raise IOError("I/O error")

        with patch('pathlib.Path.glob', side_effect=raise_io_error):
            result = service.get_series_for_directory(tmp_path)
            assert result == []


# ============================================================================
# Test Performance (lightweight)
# ============================================================================

class TestServicePerformance:
    """Lightweight performance tests."""

    def test_cache_hit_fast(self, service, temp_photos_dir, sample_hdr_series):
        """Cache hit should be very fast (<10ms)."""
        # Prime cache
        service.get_series_for_directory(temp_photos_dir)

        start = time.perf_counter()
        for _ in range(100):
            service.get_series_for_directory(temp_photos_dir)
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed / 100) * 1000
        assert avg_ms < 10, f"Cache hit avg {avg_ms:.2f}ms exceeds 10ms target"

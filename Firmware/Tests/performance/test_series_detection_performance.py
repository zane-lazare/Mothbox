"""
Performance tests for Series Detection Algorithm (Issue #110)

Validates performance targets:
- Single filename parsing: <10ms
- 1000 photos grouping: <100ms (with warm cache)
- Cache hit ratio: >80%
"""

import pytest
import time
import threading
from pathlib import Path
from unittest.mock import patch


# Import will fail until implementation exists
try:
    from webui.backend.lib.series_detection import (
        detect_series_type,
        get_series_id,
        group_photos_into_series,
    )
    from webui.backend.services.series_service import SeriesService, PhotoSeries
    IMPLEMENTATION_EXISTS = True
except ImportError:
    IMPLEMENTATION_EXISTS = False


pytestmark = pytest.mark.skipif(
    not IMPLEMENTATION_EXISTS,
    reason="Implementation not yet created"
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_photos_dir(tmp_path):
    """Create a temporary photos directory."""
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()
    return photos_dir


@pytest.fixture
def large_photo_set(temp_photos_dir):
    """Create 1000 photos for performance testing (mix of series and singles)."""
    photos = []

    # Create 100 HDR series (3 photos each = 300 photos)
    for series_num in range(100):
        base = f"moth_2024_01_{series_num:02d}__10_00_00"
        for i in range(3):
            p = temp_photos_dir / f"{base}_HDR{i}.jpg"
            p.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
            photos.append(p)

    # Create 100 Focus Bracket series (5 photos each = 500 photos)
    for series_num in range(100):
        base = f"ManFocus_moth_2024_02_{series_num:02d}__11_00_00"
        for i in range(5):
            p = temp_photos_dir / f"{base}_FB{i}.jpg"
            p.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
            photos.append(p)

    # Create 200 single photos (non-series)
    for i in range(200):
        p = temp_photos_dir / f"single_2024_03_{i:03d}__12_00_00.jpg"
        p.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
        photos.append(p)

    return photos  # Total: 1000 photos


@pytest.fixture
def series_service():
    """Create a fresh SeriesService instance."""
    return SeriesService(cache_ttl=60)


# ============================================================================
# Single Filename Parsing Performance (<10ms)
# ============================================================================

class TestSingleFilenameParsing:
    """Test single filename parsing performance."""

    def test_hdr_filename_parsing_under_10ms(self):
        """Parsing HDR filename should complete in <10ms."""
        filename = Path("moth_2024_01_15__10_30_00_HDR0.jpg")

        start = time.perf_counter()
        for _ in range(100):  # Run 100 times for stable measurement
            result = detect_series_type(filename)
        elapsed = (time.perf_counter() - start) / 100  # Average

        assert result is not None
        assert result.series_type == "hdr"
        assert elapsed < 0.010, f"Parsing took {elapsed*1000:.2f}ms, expected <10ms"

    def test_focus_bracket_filename_parsing_under_10ms(self):
        """Parsing Focus Bracket filename should complete in <10ms."""
        filename = Path("ManFocus_moth_2024_01_15__10_30_00_000000_FB0.jpg")

        start = time.perf_counter()
        for _ in range(100):
            result = detect_series_type(filename)
        elapsed = (time.perf_counter() - start) / 100

        assert result is not None
        assert result.series_type == "focus_bracket"
        assert elapsed < 0.010, f"Parsing took {elapsed*1000:.2f}ms, expected <10ms"

    def test_non_series_filename_parsing_under_10ms(self):
        """Parsing non-series filename should complete in <10ms."""
        filename = Path("regular_photo_2024_01_15__10_30_00.jpg")

        start = time.perf_counter()
        for _ in range(100):
            result = detect_series_type(filename)
        elapsed = (time.perf_counter() - start) / 100

        assert result is None  # Not a series
        assert elapsed < 0.010, f"Parsing took {elapsed*1000:.2f}ms, expected <10ms"

    def test_get_series_id_under_10ms(self):
        """get_series_id() should complete in <10ms."""
        filenames = [
            Path("moth_2024_01_15__10_30_00_HDR0.jpg"),
            Path("ManFocus_moth_2024_01_15__10_30_00_FB0.jpg"),
            Path("regular_photo.jpg"),
        ]

        for filename in filenames:
            start = time.perf_counter()
            for _ in range(100):
                get_series_id(filename)
            elapsed = (time.perf_counter() - start) / 100

            assert elapsed < 0.010, f"get_series_id took {elapsed*1000:.2f}ms for {filename}"


# ============================================================================
# Batch Grouping Performance (<100ms for 1000 photos)
# ============================================================================

class TestBatchGroupingPerformance:
    """Test grouping performance for large photo sets."""

    def test_group_1000_photos_under_100ms(self, large_photo_set):
        """Grouping 1000 photos should complete in <100ms."""
        start = time.perf_counter()
        result = group_photos_into_series(large_photo_set)
        elapsed = time.perf_counter() - start

        # Verify correct grouping (200 series: 100 HDR + 100 FB)
        assert len(result) == 200, f"Expected 200 series, got {len(result)}"

        # Verify performance
        assert elapsed < 0.100, f"Grouping took {elapsed*1000:.1f}ms, expected <100ms"

    def test_service_scan_1000_photos_under_500ms(self, series_service, large_photo_set, temp_photos_dir):
        """SeriesService should scan 1000 photos in <500ms (first scan, cold cache)."""
        start = time.perf_counter()
        result = series_service.get_series_for_directory(temp_photos_dir)
        elapsed = time.perf_counter() - start

        # Should find 200 series
        assert len(result) == 200

        # First scan can be slower due to I/O, but should still be reasonable
        assert elapsed < 0.500, f"Service scan took {elapsed*1000:.1f}ms, expected <500ms"

    def test_service_cached_lookup_under_10ms(self, series_service, large_photo_set, temp_photos_dir):
        """Cached lookups should complete in <10ms."""
        # Warm the cache
        series_service.get_series_for_directory(temp_photos_dir)

        # Measure cached lookup
        start = time.perf_counter()
        for _ in range(10):
            result = series_service.get_series_for_directory(temp_photos_dir)
        elapsed = (time.perf_counter() - start) / 10

        assert len(result) == 200
        assert elapsed < 0.010, f"Cached lookup took {elapsed*1000:.2f}ms, expected <10ms"


# ============================================================================
# Cache Hit Ratio (>80%)
# ============================================================================

class TestCacheEfficiency:
    """Test cache hit ratio targets."""

    def test_cache_hit_ratio_above_80_percent(self, series_service, large_photo_set, temp_photos_dir):
        """Cache hit ratio should exceed 80% for typical usage patterns."""
        # Initial scan (cache miss)
        series_service.get_series_for_directory(temp_photos_dir)

        # Simulate typical usage: 10 repeated queries
        for _ in range(10):
            series_service.get_series_for_directory(temp_photos_dir)

        stats = series_service.get_statistics()

        total = stats['cache_hits'] + stats['cache_misses']
        hit_ratio = stats['cache_hits'] / total if total > 0 else 0

        # Should have 10 hits and 1 miss = 90.9% hit rate
        assert hit_ratio >= 0.80, f"Cache hit ratio {hit_ratio*100:.1f}%, expected >80%"

    def test_cache_statistics_tracking(self, series_service, large_photo_set, temp_photos_dir):
        """Cache statistics should be accurately tracked."""
        initial_stats = series_service.get_statistics()
        assert initial_stats['cache_hits'] == 0
        assert initial_stats['cache_misses'] == 0

        # First call - cache miss
        series_service.get_series_for_directory(temp_photos_dir)
        stats_after_first = series_service.get_statistics()
        assert stats_after_first['cache_misses'] == 1

        # Second call - cache hit
        series_service.get_series_for_directory(temp_photos_dir)
        stats_after_second = series_service.get_statistics()
        assert stats_after_second['cache_hits'] == 1

    def test_cache_invalidation_forces_rescan(self, series_service, large_photo_set, temp_photos_dir):
        """Cache invalidation should force a rescan."""
        # Warm cache
        series_service.get_series_for_directory(temp_photos_dir)

        # Invalidate
        series_service.invalidate_cache()

        # Next call should be a cache miss
        series_service.get_series_for_directory(temp_photos_dir)

        stats = series_service.get_statistics()
        assert stats['cache_misses'] == 2  # Initial + after invalidation


# ============================================================================
# Concurrent Access Performance
# ============================================================================

class TestConcurrentAccessPerformance:
    """Test performance under concurrent access."""

    def test_concurrent_reads_no_contention(self, series_service, large_photo_set, temp_photos_dir):
        """Concurrent reads should not cause significant contention."""
        # Warm cache
        series_service.get_series_for_directory(temp_photos_dir)

        results = []
        errors = []

        def reader():
            try:
                start = time.perf_counter()
                result = series_service.get_series_for_directory(temp_photos_dir)
                elapsed = time.perf_counter() - start
                results.append((len(result), elapsed))
            except Exception as e:
                errors.append(str(e))

        # Start 10 concurrent readers
        threads = [threading.Thread(target=reader) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No errors
        assert len(errors) == 0, f"Errors: {errors}"

        # All readers got correct results
        for count, elapsed in results:
            assert count == 200
            assert elapsed < 0.100, f"Concurrent read took {elapsed*1000:.1f}ms"

    def test_mixed_read_write_operations(self, series_service, large_photo_set, temp_photos_dir):
        """Mixed read/write operations should not deadlock."""
        # Warm cache
        series_service.get_series_for_directory(temp_photos_dir)

        results = []
        errors = []

        def reader():
            try:
                for _ in range(5):
                    series_service.get_series_for_directory(temp_photos_dir)
                results.append("read_ok")
            except Exception as e:
                errors.append(f"read: {e}")

        def writer():
            try:
                for _ in range(3):
                    series_service.invalidate_cache()
                    time.sleep(0.001)
                results.append("write_ok")
            except Exception as e:
                errors.append(f"write: {e}")

        # Start mixed operations
        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=reader))
        for _ in range(2):
            threads.append(threading.Thread(target=writer))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)  # 5 second timeout to detect deadlocks

        # Check for timeouts (deadlock indicator)
        alive = [t for t in threads if t.is_alive()]
        assert len(alive) == 0, "Potential deadlock detected"

        # No errors
        assert len(errors) == 0, f"Errors: {errors}"


# ============================================================================
# Memory Efficiency
# ============================================================================

class TestMemoryEfficiency:
    """Test memory usage patterns."""

    def test_photoSeries_dataclass_memory_footprint(self, temp_photos_dir):
        """PhotoSeries dataclass should have reasonable memory footprint."""
        import sys

        # Create a PhotoSeries with 5 photos
        photos = [temp_photos_dir / f"photo_{i}.jpg" for i in range(5)]
        for p in photos:
            p.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        series = PhotoSeries(
            series_id="test_series",
            series_type="hdr",
            base_name="test_2024_01_15__10_00_00",
            photos=photos,
            count=5,
            cover_photo=photos[0]
        )

        # Check basic size (rough estimate)
        size = sys.getsizeof(series)
        # Dataclass overhead should be minimal (<500 bytes excluding paths)
        assert size < 500, f"PhotoSeries overhead {size} bytes, expected <500"

    def test_service_cache_does_not_grow_unbounded(self, series_service, tmp_path):
        """Cache should not grow unbounded when scanning multiple directories."""
        # Create and scan 10 different directories
        for i in range(10):
            dir_path = tmp_path / f"photos_{i}"
            dir_path.mkdir()

            # Create some photos in each
            for j in range(10):
                p = dir_path / f"moth_2024_01_{i:02d}__10_00_0{j}_HDR0.jpg"
                p.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

            series_service.get_series_for_directory(dir_path)

        stats = series_service.get_statistics()

        # Cache should contain all 10 directories
        assert stats['cache_entries'] == 10

        # Total series should be 10 (one per directory, since we only made HDR0 files)
        # Actually 0 because single photos don't form series (count < 2)
        assert stats['total_series'] == 0


# ============================================================================
# Regression Tests for Known Performance Issues
# ============================================================================

class TestPerformanceRegressions:
    """Prevent known performance regressions."""

    def test_regex_compilation_is_cached(self):
        """Regex patterns should be pre-compiled (not compiled on each call)."""
        # This is a code quality check - patterns should be module-level constants
        from webui.backend.lib import series_detection

        # Check that patterns exist as module-level attributes
        assert hasattr(series_detection, 'HDR_PATTERN')
        assert hasattr(series_detection, 'FB_PATTERN')

    def test_no_excessive_file_io_on_repeated_calls(self, series_service, large_photo_set, temp_photos_dir):
        """Repeated calls should use cache, not re-scan filesystem."""
        # First call
        series_service.get_series_for_directory(temp_photos_dir)

        # Track glob calls
        glob_calls = []
        original_glob = Path.glob

        def tracking_glob(self, pattern):
            glob_calls.append(pattern)
            return original_glob(self, pattern)

        # Second call (should hit cache)
        with patch.object(Path, 'glob', tracking_glob):
            series_service.get_series_for_directory(temp_photos_dir)

        # No glob calls should have been made (cache hit)
        assert len(glob_calls) == 0, f"Unexpected glob calls: {glob_calls}"

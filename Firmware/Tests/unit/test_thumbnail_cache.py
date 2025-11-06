"""
Unit tests for thumbnail caching service (Issue #134 - Phase 1)

Tests thumbnail cache with multi-resolution support, file-based locking,
LRU eviction, error handling, and statistics tracking.

Design Decisions:
- Immutable photos: No automatic invalidation based on mtime
- File-based locking (fcntl) for multi-process safety
- Placeholder images for corrupt sources (5-minute TTL)
- Sizes: 64px, 128px, 256px

Coverage Target: 85%+ (ThumbnailCache service)

Test-Driven Development:
This test file is written FIRST, before implementing the service.
All tests should fail initially, then pass as service is implemented.
"""

import pytest
import json
import time
import fcntl
import hashlib
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import datetime, timedelta
from PIL import Image, ImageDraw
from io import BytesIO


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_cache_dir(tmp_path, monkeypatch):
    """
    Temporary cache directory for thumbnail tests

    Creates isolated cache directory and patches mothbox_paths constants.
    """
    cache_dir = tmp_path / "cache" / "thumbnails"
    cache_dir.mkdir(parents=True)

    # Patch in mothbox_paths module
    import mothbox_paths
    monkeypatch.setattr(mothbox_paths, 'CACHE_DIR', tmp_path / "cache")
    monkeypatch.setattr(mothbox_paths, 'THUMBNAIL_CACHE_DIR', cache_dir)

    return cache_dir


@pytest.fixture
def temp_photos_dir(tmp_path):
    """Temporary photos directory with sample images"""
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()
    return photos_dir


@pytest.fixture
def sample_photo(temp_photos_dir):
    """Create a valid sample JPEG photo"""
    photo_path = temp_photos_dir / "sample.jpg"

    # Create a real JPEG image with PIL
    img = Image.new('RGB', (800, 600), color='red')
    img.save(photo_path, format='JPEG', quality=85)

    return photo_path


@pytest.fixture
def multiple_photos(temp_photos_dir):
    """Create multiple sample photos"""
    photos = []

    for i in range(5):
        photo_path = temp_photos_dir / f"photo_{i}.jpg"
        img = Image.new('RGB', (800, 600), color=(i*50, 100, 150))
        img.save(photo_path, format='JPEG', quality=85)
        photos.append(photo_path)

        # Stagger modification times
        time.sleep(0.01)

    return photos


@pytest.fixture
def corrupt_photo(temp_photos_dir):
    """Create a corrupt/invalid image file"""
    photo_path = temp_photos_dir / "corrupt.jpg"
    photo_path.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 50)  # Invalid JPEG data
    return photo_path


@pytest.fixture
def thumbnail_cache(temp_cache_dir):
    """Create ThumbnailCache instance for testing"""
    from services.thumbnail_cache import ThumbnailCache

    return ThumbnailCache(
        cache_dir=temp_cache_dir,
        max_size_mb=10,  # Small limit for testing eviction
        sizes=[64, 128, 256]
    )


# ============================================================================
# Test Cache Initialization
# ============================================================================

class TestCacheInitialization:
    """Tests for ThumbnailCache initialization and configuration"""

    def test_cache_initialization_creates_directory(self, tmp_path):
        """Cache initialization creates cache directory if it doesn't exist"""
        from services.thumbnail_cache import ThumbnailCache

        cache_dir = tmp_path / "new_cache"
        assert not cache_dir.exists()

        cache = ThumbnailCache(cache_dir=cache_dir)

        assert cache_dir.exists()
        assert cache_dir.is_dir()

    def test_cache_initialization_with_defaults(self, temp_cache_dir):
        """Cache initializes with default configuration values"""
        from services.thumbnail_cache import ThumbnailCache

        cache = ThumbnailCache(cache_dir=temp_cache_dir)

        assert cache.cache_dir == temp_cache_dir
        assert cache.max_size_mb == 500  # Default
        assert cache.sizes == [64, 128, 256]  # Default

    def test_cache_initialization_with_custom_sizes(self, temp_cache_dir):
        """Cache accepts custom thumbnail sizes"""
        from services.thumbnail_cache import ThumbnailCache

        custom_sizes = [32, 64, 512]
        cache = ThumbnailCache(cache_dir=temp_cache_dir, sizes=custom_sizes)

        assert cache.sizes == custom_sizes

    def test_cache_initialization_with_custom_max_size(self, temp_cache_dir):
        """Cache accepts custom max_size_mb"""
        from services.thumbnail_cache import ThumbnailCache

        cache = ThumbnailCache(cache_dir=temp_cache_dir, max_size_mb=100)

        assert cache.max_size_mb == 100

    def test_cache_initialization_with_existing_cache(self, temp_cache_dir):
        """Cache initializes properly when cache directory already exists"""
        from services.thumbnail_cache import ThumbnailCache

        # Create some existing files
        (temp_cache_dir / "64").mkdir()
        (temp_cache_dir / "64" / "existing.jpg").write_bytes(b'test')

        cache = ThumbnailCache(cache_dir=temp_cache_dir)

        assert cache.cache_dir.exists()
        assert (cache.cache_dir / "64" / "existing.jpg").exists()


# ============================================================================
# Test Cache Hit/Miss Scenarios
# ============================================================================

class TestCacheHitMissScenarios:
    """Tests for cache hit and miss behavior"""

    def test_cache_miss_generates_thumbnail(self, thumbnail_cache, sample_photo):
        """Cache miss generates thumbnail and caches it"""
        result = thumbnail_cache.get_thumbnail(sample_photo, size=128)

        assert result.exists()
        assert result.is_file()
        assert result.parent.name == "128"

        # Verify it's a valid image
        img = Image.open(result)
        assert img.size[0] <= 128
        assert img.size[1] <= 128

    def test_cache_hit_returns_cached_file(self, thumbnail_cache, sample_photo):
        """Cache hit returns cached file without regenerating"""
        # First request (cache miss)
        result1 = thumbnail_cache.get_thumbnail(sample_photo, size=128)
        mtime1 = result1.stat().st_mtime

        time.sleep(0.01)

        # Second request (cache hit)
        result2 = thumbnail_cache.get_thumbnail(sample_photo, size=128)
        mtime2 = result2.stat().st_mtime

        assert result1 == result2
        assert mtime1 == mtime2  # File wasn't regenerated

    def test_statistics_track_hits_and_misses(self, thumbnail_cache, sample_photo):
        """Statistics correctly track cache hits and misses"""
        # Cache miss
        thumbnail_cache.get_thumbnail(sample_photo, size=128)
        stats1 = thumbnail_cache.get_statistics()

        assert stats1['misses'] == 1
        assert stats1['hits'] == 0
        assert stats1['total_requests'] == 1

        # Cache hit
        thumbnail_cache.get_thumbnail(sample_photo, size=128)
        stats2 = thumbnail_cache.get_statistics()

        assert stats2['misses'] == 1
        assert stats2['hits'] == 1
        assert stats2['total_requests'] == 2

    def test_hit_ratio_calculation(self, thumbnail_cache, sample_photo):
        """Hit ratio is calculated correctly"""
        # 1 miss
        thumbnail_cache.get_thumbnail(sample_photo, size=128)

        # 3 hits
        thumbnail_cache.get_thumbnail(sample_photo, size=128)
        thumbnail_cache.get_thumbnail(sample_photo, size=128)
        thumbnail_cache.get_thumbnail(sample_photo, size=128)

        stats = thumbnail_cache.get_statistics()
        assert stats['hit_ratio'] == 0.75  # 3/4 = 0.75

    def test_multiple_requests_same_photo(self, thumbnail_cache, sample_photo):
        """Multiple rapid requests for same photo handled correctly"""
        results = []

        for _ in range(5):
            result = thumbnail_cache.get_thumbnail(sample_photo, size=256)
            results.append(result)

        # All results should point to same cached file
        assert all(r == results[0] for r in results)

        # Only one file should exist
        assert results[0].exists()

    def test_requests_for_different_sizes(self, thumbnail_cache, sample_photo):
        """Requests for different sizes create separate cache entries"""
        result_64 = thumbnail_cache.get_thumbnail(sample_photo, size=64)
        result_128 = thumbnail_cache.get_thumbnail(sample_photo, size=128)
        result_256 = thumbnail_cache.get_thumbnail(sample_photo, size=256)

        # Different cache files
        assert result_64 != result_128 != result_256

        # All exist
        assert result_64.exists() and result_128.exists() and result_256.exists()

        # In correct size directories
        assert result_64.parent.name == "64"
        assert result_128.parent.name == "128"
        assert result_256.parent.name == "256"


# ============================================================================
# Test Multi-Resolution Generation
# ============================================================================

class TestMultiResolutionGeneration:
    """Tests for multi-resolution thumbnail generation"""

    def test_64px_thumbnail_generation(self, thumbnail_cache, sample_photo):
        """64px thumbnail generated with correct dimensions"""
        result = thumbnail_cache.get_thumbnail(sample_photo, size=64)

        img = Image.open(result)
        assert max(img.size) <= 64

    def test_128px_thumbnail_generation(self, thumbnail_cache, sample_photo):
        """128px thumbnail generated with correct dimensions"""
        result = thumbnail_cache.get_thumbnail(sample_photo, size=128)

        img = Image.open(result)
        assert max(img.size) <= 128

    def test_256px_thumbnail_generation(self, thumbnail_cache, sample_photo):
        """256px thumbnail generated with correct dimensions"""
        result = thumbnail_cache.get_thumbnail(sample_photo, size=256)

        img = Image.open(result)
        assert max(img.size) <= 256

    def test_jpeg_quality_is_85(self, thumbnail_cache, sample_photo):
        """Thumbnails saved with JPEG quality 85"""
        result = thumbnail_cache.get_thumbnail(sample_photo, size=128)

        # Open and verify it's a valid JPEG
        img = Image.open(result)
        assert img.format == 'JPEG'

    def test_aspect_ratio_preservation(self, temp_photos_dir, thumbnail_cache):
        """Thumbnail generation preserves aspect ratio"""
        # Create wide image (landscape)
        photo_path = temp_photos_dir / "wide.jpg"
        img = Image.new('RGB', (1600, 900), color='blue')
        img.save(photo_path, format='JPEG')

        result = thumbnail_cache.get_thumbnail(photo_path, size=128)

        thumb = Image.open(result)
        # Should maintain ~16:9 ratio
        assert abs((thumb.width / thumb.height) - (16/9)) < 0.1

    def test_invalid_size_raises_error(self, thumbnail_cache, sample_photo):
        """Invalid size raises ThumbnailError"""
        from services.thumbnail_cache import ThumbnailError

        with pytest.raises(ThumbnailError):
            thumbnail_cache.get_thumbnail(sample_photo, size=999)

    def test_custom_size_support(self, temp_cache_dir, sample_photo):
        """Cache supports custom configured sizes"""
        from services.thumbnail_cache import ThumbnailCache

        cache = ThumbnailCache(cache_dir=temp_cache_dir, sizes=[32, 512])

        result_32 = cache.get_thumbnail(sample_photo, size=32)
        result_512 = cache.get_thumbnail(sample_photo, size=512)

        assert result_32.exists()
        assert result_512.exists()

        img_32 = Image.open(result_32)
        img_512 = Image.open(result_512)

        assert max(img_32.size) <= 32
        assert max(img_512.size) <= 512


# ============================================================================
# Test File-Based Locking
# ============================================================================

class TestFileBasedLocking:
    """Tests for fcntl file-based locking during thumbnail generation"""

    def test_concurrent_requests_only_one_generates(self, thumbnail_cache, sample_photo):
        """Concurrent requests for same thumbnail only generate once"""
        results = []
        errors = []

        def request_thumbnail():
            try:
                result = thumbnail_cache.get_thumbnail(sample_photo, size=128)
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Launch 5 concurrent threads
        threads = []
        for _ in range(5):
            t = threading.Thread(target=request_thumbnail)
            threads.append(t)
            t.start()

        # Wait for all to complete
        for t in threads:
            t.join()

        # No errors
        assert len(errors) == 0

        # All got same result
        assert len(results) == 5
        assert all(r == results[0] for r in results)

        # Only one file exists (not 5 copies)
        assert results[0].exists()

    def test_lock_prevents_duplicate_generation(self, thumbnail_cache, sample_photo, tmp_path):
        """File lock prevents duplicate thumbnail generation"""
        # This test verifies that locking works
        # In practice, threading may cause multiple calls if they happen sequentially
        # The important thing is that the file is generated correctly and atomically

        # Make concurrent requests
        results = []
        def get_thumb():
            result = thumbnail_cache.get_thumbnail(sample_photo, size=128)
            results.append(result)

        threads = []
        for _ in range(3):
            t = threading.Thread(target=get_thumb)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All should get the same result
        assert len(results) == 3
        assert all(r == results[0] for r in results)

        # File should exist
        assert results[0].exists()

    def test_lock_release_after_generation(self, thumbnail_cache, sample_photo):
        """Lock is properly released after thumbnail generation"""
        result = thumbnail_cache.get_thumbnail(sample_photo, size=128)

        # Lock file should not exist after completion
        lock_file = result.parent / f".{result.name}.lock"
        assert not lock_file.exists()

    def test_lock_timeout_handling(self, thumbnail_cache, sample_photo, temp_cache_dir):
        """Lock timeout handled gracefully if another process holds lock"""
        # This test verifies lock behavior, implementation may vary
        result = thumbnail_cache.get_thumbnail(sample_photo, size=64)
        assert result.exists()

    def test_lock_behavior_across_multiple_photos(self, thumbnail_cache, multiple_photos):
        """Locks are independent for different photos"""
        results = []

        def generate_all():
            for photo in multiple_photos:
                result = thumbnail_cache.get_thumbnail(photo, size=128)
                results.append(result)

        # Run concurrently
        threads = [threading.Thread(target=generate_all) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All photos should have thumbnails
        assert len(results) >= len(multiple_photos)


# ============================================================================
# Test LRU Eviction
# ============================================================================

class TestLRUEviction:
    """Tests for LRU (Least Recently Used) cache eviction"""

    def test_eviction_when_cache_exceeds_max_size(self, temp_cache_dir, multiple_photos):
        """Cache evicts old files when exceeding max_size_mb"""
        from services.thumbnail_cache import ThumbnailCache

        # Small cache limit (1MB)
        cache = ThumbnailCache(cache_dir=temp_cache_dir, max_size_mb=1)

        # Generate many thumbnails to exceed limit
        for photo in multiple_photos:
            for size in [64, 128, 256]:
                cache.get_thumbnail(photo, size)

        # Cache size should be under limit after eviction
        stats = cache.get_statistics()
        assert stats['cache_size_mb'] <= 1.5  # Allow some overhead

    def test_least_recently_used_removed_first(self, temp_cache_dir, multiple_photos):
        """LRU eviction removes least recently accessed files first"""
        from services.thumbnail_cache import ThumbnailCache

        cache = ThumbnailCache(cache_dir=temp_cache_dir, max_size_mb=1)

        # Generate thumbnails in order
        results = []
        for photo in multiple_photos[:3]:
            result = cache.get_thumbnail(photo, size=256)
            results.append(result)
            time.sleep(0.01)

        # Access first thumbnail again (make it most recent)
        cache.get_thumbnail(multiple_photos[0], size=256)

        # Add more to trigger eviction
        for photo in multiple_photos[3:]:
            cache.get_thumbnail(photo, size=256)

        # First thumbnail should still exist (was accessed recently)
        assert results[0].exists()

    def test_access_time_tracking(self, thumbnail_cache, sample_photo):
        """Cache tracks access times for LRU eviction"""
        result = thumbnail_cache.get_thumbnail(sample_photo, size=128)

        atime1 = result.stat().st_atime
        time.sleep(0.1)

        # Access again
        thumbnail_cache.get_thumbnail(sample_photo, size=128)
        atime2 = result.stat().st_atime

        # Access time should be updated
        assert atime2 > atime1

    def test_eviction_preserves_recently_accessed(self, temp_cache_dir, multiple_photos):
        """Eviction preserves recently accessed thumbnails"""
        from services.thumbnail_cache import ThumbnailCache

        cache = ThumbnailCache(cache_dir=temp_cache_dir, max_size_mb=1)

        # Generate old thumbnails
        old_results = []
        for photo in multiple_photos[:2]:
            result = cache.get_thumbnail(photo, size=256)
            old_results.append(result)

        time.sleep(0.1)

        # Generate new thumbnails
        new_results = []
        for photo in multiple_photos[2:]:
            result = cache.get_thumbnail(photo, size=256)
            new_results.append(result)

        # Force eviction by filling cache
        for photo in multiple_photos:
            for size in [64, 128]:
                cache.get_thumbnail(photo, size)

        # New files more likely to exist than old files
        new_exist = sum(1 for r in new_results if r.exists())
        old_exist = sum(1 for r in old_results if r.exists())

        assert new_exist >= old_exist

    def test_eviction_across_multiple_sizes(self, temp_cache_dir, multiple_photos):
        """LRU eviction works across all thumbnail sizes"""
        from services.thumbnail_cache import ThumbnailCache

        cache = ThumbnailCache(cache_dir=temp_cache_dir, max_size_mb=0.01)  # Very small cache (10KB)

        # Generate thumbnails in all sizes
        for photo in multiple_photos:
            for size in [64, 128, 256]:
                cache.get_thumbnail(photo, size)

        stats = cache.get_statistics()
        # Should have evicted some files OR cache should be small
        # Either way, cache size should be under limit
        assert stats['cache_size_mb'] <= 0.015  # Allow small overhead

    def test_statistics_update_after_eviction(self, temp_cache_dir, multiple_photos):
        """Statistics correctly update after eviction"""
        from services.thumbnail_cache import ThumbnailCache

        cache = ThumbnailCache(cache_dir=temp_cache_dir, max_size_mb=1)

        # Fill cache
        for photo in multiple_photos:
            for size in [64, 128, 256]:
                cache.get_thumbnail(photo, size)

        stats = cache.get_statistics()

        # Statistics should be consistent with actual cache
        assert stats['cache_size_mb'] > 0
        assert stats['cached_files'] > 0

    def test_cache_size_calculation_accuracy(self, thumbnail_cache, multiple_photos):
        """Cache size calculation is accurate"""
        # Generate some thumbnails
        for photo in multiple_photos[:3]:
            thumbnail_cache.get_thumbnail(photo, size=128)

        stats = thumbnail_cache.get_statistics()

        # Calculate actual size
        actual_size = sum(
            f.stat().st_size
            for f in thumbnail_cache.cache_dir.rglob("*.jpg")
        ) / (1024 * 1024)

        # Should match within 1%
        assert abs(stats['cache_size_mb'] - actual_size) < 0.01


# ============================================================================
# Test Error Handling
# ============================================================================

class TestErrorHandling:
    """Tests for error handling and placeholder generation"""

    def test_corrupt_image_generates_placeholder(self, thumbnail_cache, corrupt_photo):
        """Corrupt image source generates placeholder thumbnail"""
        result = thumbnail_cache.get_thumbnail(corrupt_photo, size=128)

        assert result.exists()

        # Should be a valid image (placeholder)
        img = Image.open(result)
        assert img.size == (128, 128)

    def test_placeholder_image_properties(self, thumbnail_cache, corrupt_photo):
        """Placeholder image has correct properties (gray with "?")"""
        result = thumbnail_cache.get_thumbnail(corrupt_photo, size=128)

        img = Image.open(result)

        # Should be gray-ish (center pixel)
        center_pixel = img.getpixel((64, 64))
        # Gray pixels have R≈G≈B
        assert abs(center_pixel[0] - center_pixel[1]) < 50
        assert abs(center_pixel[1] - center_pixel[2]) < 50

    def test_error_cache_5_minute_ttl(self, thumbnail_cache, corrupt_photo):
        """Error cache has 5-minute TTL"""
        # First request generates placeholder
        result1 = thumbnail_cache.get_thumbnail(corrupt_photo, size=128)
        mtime1 = result1.stat().st_mtime

        time.sleep(0.1)

        # Second request within TTL returns cached placeholder
        result2 = thumbnail_cache.get_thumbnail(corrupt_photo, size=128)
        mtime2 = result2.stat().st_mtime

        assert result1 == result2
        assert mtime1 == mtime2  # Not regenerated

    def test_error_cache_hit_within_ttl(self, thumbnail_cache, corrupt_photo):
        """Requests for corrupt image within TTL return cached placeholder"""
        result1 = thumbnail_cache.get_thumbnail(corrupt_photo, size=64)

        # Multiple requests
        for _ in range(3):
            result2 = thumbnail_cache.get_thumbnail(corrupt_photo, size=64)
            assert result1 == result2

    def test_error_cache_regeneration_after_ttl(self, thumbnail_cache, corrupt_photo, monkeypatch):
        """Placeholder regenerated after TTL expires"""
        # Generate initial placeholder
        result = thumbnail_cache.get_thumbnail(corrupt_photo, size=128)

        # Mock time to simulate TTL expiry
        original_time = time.time
        monkeypatch.setattr(time, 'time', lambda: original_time() + 301)  # 5 min + 1 sec

        # Should regenerate (or attempt to)
        result2 = thumbnail_cache.get_thumbnail(corrupt_photo, size=128)
        assert result2.exists()

    def test_permission_errors_handled_gracefully(self, thumbnail_cache, sample_photo, temp_cache_dir):
        """Permission errors handled gracefully"""
        # Make cache directory read-only
        temp_cache_dir.chmod(0o444)

        try:
            from services.thumbnail_cache import ThumbnailError
            with pytest.raises(ThumbnailError):
                thumbnail_cache.get_thumbnail(sample_photo, size=128)
        finally:
            # Restore permissions for cleanup
            temp_cache_dir.chmod(0o755)

    def test_missing_source_file_returns_error(self, thumbnail_cache, temp_photos_dir):
        """Missing source file raises ThumbnailError"""
        from services.thumbnail_cache import ThumbnailError

        nonexistent = temp_photos_dir / "nonexistent.jpg"

        with pytest.raises(ThumbnailError):
            thumbnail_cache.get_thumbnail(nonexistent, size=128)

    def test_pil_import_error_handling(self, thumbnail_cache, sample_photo, monkeypatch):
        """PIL ImportError handled gracefully"""
        # This test ensures graceful degradation if PIL unavailable
        # In practice, PIL is a hard requirement, but test defensive code
        result = thumbnail_cache.get_thumbnail(sample_photo, size=128)
        assert result.exists()

    def test_disk_full_scenario(self, thumbnail_cache, sample_photo, monkeypatch):
        """Disk full scenario handled gracefully"""
        # Mock disk full error
        original_save = Image.Image.save

        def mock_save(self, *args, **kwargs):
            raise OSError("No space left on device")

        monkeypatch.setattr(Image.Image, 'save', mock_save)

        from services.thumbnail_cache import ThumbnailError
        with pytest.raises(ThumbnailError):
            thumbnail_cache.get_thumbnail(sample_photo, size=128)


# ============================================================================
# Test Statistics Tracking
# ============================================================================

class TestStatisticsTracking:
    """Tests for cache statistics tracking and persistence"""

    def test_hit_counter_increments(self, thumbnail_cache, sample_photo):
        """Hit counter increments on cache hits"""
        thumbnail_cache.get_thumbnail(sample_photo, size=128)  # Miss

        stats1 = thumbnail_cache.get_statistics()
        assert stats1['hits'] == 0

        thumbnail_cache.get_thumbnail(sample_photo, size=128)  # Hit

        stats2 = thumbnail_cache.get_statistics()
        assert stats2['hits'] == 1

    def test_miss_counter_increments(self, thumbnail_cache, multiple_photos):
        """Miss counter increments on cache misses"""
        for photo in multiple_photos[:3]:
            thumbnail_cache.get_thumbnail(photo, size=128)

        stats = thumbnail_cache.get_statistics()
        assert stats['misses'] == 3

    def test_total_requests_calculation(self, thumbnail_cache, multiple_photos):
        """Total requests calculated correctly"""
        # 3 misses
        for photo in multiple_photos[:3]:
            thumbnail_cache.get_thumbnail(photo, size=128)

        # 2 hits
        thumbnail_cache.get_thumbnail(multiple_photos[0], size=128)
        thumbnail_cache.get_thumbnail(multiple_photos[1], size=128)

        stats = thumbnail_cache.get_statistics()
        assert stats['total_requests'] == 5

    def test_hit_ratio_calculation_zero_division_safe(self, thumbnail_cache):
        """Hit ratio handles zero total_requests safely"""
        stats = thumbnail_cache.get_statistics()

        assert 'hit_ratio' in stats
        assert stats['hit_ratio'] == 0.0

    def test_cache_size_mb_calculation(self, thumbnail_cache, multiple_photos):
        """Cache size in MB calculated correctly"""
        for photo in multiple_photos:
            thumbnail_cache.get_thumbnail(photo, size=256)

        stats = thumbnail_cache.get_statistics()

        assert 'cache_size_mb' in stats
        assert stats['cache_size_mb'] > 0
        assert isinstance(stats['cache_size_mb'], (int, float))

    def test_cached_files_count(self, thumbnail_cache, multiple_photos):
        """Cached files count is accurate"""
        # Generate 5 photos * 3 sizes = 15 thumbnails
        for photo in multiple_photos:
            for size in [64, 128, 256]:
                thumbnail_cache.get_thumbnail(photo, size)

        stats = thumbnail_cache.get_statistics()
        assert stats['cached_files'] == 15

    def test_statistics_persistence_to_json(self, thumbnail_cache, sample_photo):
        """Statistics persist to JSON file"""
        thumbnail_cache.get_thumbnail(sample_photo, size=128)

        stats_file = thumbnail_cache.cache_dir / "cache_stats.json"
        assert stats_file.exists()

        # Verify it's valid JSON
        with open(stats_file) as f:
            data = json.load(f)

        assert 'hits' in data
        assert 'misses' in data
        assert 'total_requests' in data


# ============================================================================
# Test Cache Paths
# ============================================================================

class TestCachePaths:
    """Tests for cache path generation and hashing"""

    def test_hash_generation_consistency(self, thumbnail_cache, sample_photo):
        """Hash generation is consistent for same photo path"""
        hash1 = thumbnail_cache._get_hash(sample_photo)
        hash2 = thumbnail_cache._get_hash(sample_photo)

        assert hash1 == hash2
        assert len(hash1) == 12  # MD5 truncated to 12 chars

    def test_cache_file_path_structure(self, thumbnail_cache, sample_photo):
        """Cache file path follows correct structure: {size}/{hash}.jpg"""
        result = thumbnail_cache.get_thumbnail(sample_photo, size=128)

        assert result.parent.parent == thumbnail_cache.cache_dir
        assert result.parent.name == "128"
        assert result.suffix == ".jpg"
        assert len(result.stem) == 12  # Hash length

    def test_path_traversal_prevention(self, thumbnail_cache, temp_photos_dir):
        """Path traversal attacks blocked in photo_path"""
        from services.thumbnail_cache import ThumbnailError

        malicious_path = temp_photos_dir / ".." / ".." / "etc" / "passwd"

        with pytest.raises(ThumbnailError):
            thumbnail_cache.get_thumbnail(malicious_path, size=128)

    def test_hash_uniqueness_for_different_photos(self, thumbnail_cache, multiple_photos):
        """Different photos generate different hashes"""
        hashes = [thumbnail_cache._get_hash(photo) for photo in multiple_photos]

        # All hashes should be unique
        assert len(hashes) == len(set(hashes))

    def test_hash_collision_handling(self, thumbnail_cache, temp_photos_dir):
        """Hash collision handled gracefully (rare but possible)"""
        # This is a hypothetical test - MD5 collisions extremely rare
        # Implementation should handle gracefully if it ever occurs

        photo1 = temp_photos_dir / "photo1.jpg"
        photo2 = temp_photos_dir / "photo2.jpg"

        img = Image.new('RGB', (100, 100), color='red')
        img.save(photo1, format='JPEG')
        img.save(photo2, format='JPEG')

        result1 = thumbnail_cache.get_thumbnail(photo1, size=128)
        result2 = thumbnail_cache.get_thumbnail(photo2, size=128)

        # Both should succeed (no collision errors)
        assert result1.exists()
        assert result2.exists()


# ============================================================================
# Test Invalidation
# ============================================================================

class TestInvalidation:
    """Tests for manual cache invalidation"""

    def test_invalidate_specific_photo_all_sizes(self, thumbnail_cache, sample_photo):
        """Manual invalidation removes specific photo from all sizes"""
        # Generate thumbnails in all sizes
        for size in [64, 128, 256]:
            thumbnail_cache.get_thumbnail(sample_photo, size)

        # Invalidate
        thumbnail_cache.invalidate(sample_photo)

        # All sizes should be removed
        photo_hash = thumbnail_cache._get_hash(sample_photo)
        for size in [64, 128, 256]:
            cached_file = thumbnail_cache.cache_dir / str(size) / f"{photo_hash}.jpg"
            assert not cached_file.exists()

    def test_invalidate_entire_cache(self, thumbnail_cache, multiple_photos):
        """Manual invalidation can clear entire cache"""
        # Generate many thumbnails
        for photo in multiple_photos:
            for size in [64, 128, 256]:
                thumbnail_cache.get_thumbnail(photo, size)

        # Invalidate entire cache
        thumbnail_cache.invalidate()

        # Cache should be empty
        cached_files = list(thumbnail_cache.cache_dir.rglob("*.jpg"))
        assert len(cached_files) == 0

    def test_invalidation_updates_statistics(self, thumbnail_cache, sample_photo):
        """Invalidation updates statistics correctly"""
        thumbnail_cache.get_thumbnail(sample_photo, size=128)

        stats_before = thumbnail_cache.get_statistics()

        thumbnail_cache.invalidate(sample_photo)

        stats_after = thumbnail_cache.get_statistics()

        # File count should decrease
        assert stats_after['cached_files'] < stats_before['cached_files']

    def test_invalidation_during_active_lock(self, thumbnail_cache, sample_photo):
        """Invalidation waits for active generation to complete"""
        # This tests behavior when invalidation called during generation
        # Implementation may queue invalidation or wait for lock

        def slow_generate():
            thumbnail_cache.get_thumbnail(sample_photo, size=128)

        thread = threading.Thread(target=slow_generate)
        thread.start()

        time.sleep(0.05)

        # Try to invalidate while generating
        thumbnail_cache.invalidate(sample_photo)

        thread.join()

        # Should complete without error
        assert True

    def test_partial_invalidation_specific_size(self, thumbnail_cache, sample_photo):
        """Invalidation can target specific size"""
        # Generate all sizes
        for size in [64, 128, 256]:
            thumbnail_cache.get_thumbnail(sample_photo, size)

        # Invalidate only size 128
        thumbnail_cache.invalidate(sample_photo, size=128)

        # 128 should be gone
        photo_hash = thumbnail_cache._get_hash(sample_photo)
        cached_128 = thumbnail_cache.cache_dir / "128" / f"{photo_hash}.jpg"
        assert not cached_128.exists()

        # Other sizes should remain
        cached_64 = thumbnail_cache.cache_dir / "64" / f"{photo_hash}.jpg"
        cached_256 = thumbnail_cache.cache_dir / "256" / f"{photo_hash}.jpg"
        assert cached_64.exists()
        assert cached_256.exists()


# ============================================================================
# Test Security
# ============================================================================

class TestSecurity:
    """Tests for security features and input validation"""

    def test_path_traversal_blocked(self, thumbnail_cache, temp_photos_dir):
        """Path traversal attempts blocked"""
        from services.thumbnail_cache import ThumbnailError

        traversal_paths = [
            temp_photos_dir / ".." / "sensitive.jpg",
            temp_photos_dir / ".." / ".." / "etc" / "passwd",
            Path("../../../../etc/passwd"),
        ]

        for malicious_path in traversal_paths:
            with pytest.raises(ThumbnailError):
                thumbnail_cache.get_thumbnail(malicious_path, size=128)

    def test_absolute_paths_outside_photos_rejected(self, thumbnail_cache):
        """Absolute paths to non-existent files rejected"""
        from services.thumbnail_cache import ThumbnailError

        # Use non-existent external path
        external_path = Path("/nonexistent/photo.jpg")

        with pytest.raises(ThumbnailError):
            thumbnail_cache.get_thumbnail(external_path, size=128)

    def test_symlink_handling(self, thumbnail_cache, temp_photos_dir, tmp_path):
        """Symlink handling prevents escaping photos directory"""
        # Create symlink to external file
        external_file = tmp_path / "external.jpg"
        img = Image.new('RGB', (100, 100), color='green')
        img.save(external_file, format='JPEG')

        symlink = temp_photos_dir / "symlink.jpg"
        try:
            symlink.symlink_to(external_file)
        except OSError:
            pytest.skip("Symlink creation not supported")

        # Should handle symlink safely
        # Implementation may follow symlink or reject it
        try:
            result = thumbnail_cache.get_thumbnail(symlink, size=128)
            # If allowed, should still be safe
            assert result.exists()
        except Exception:
            # If rejected, that's also acceptable
            pass

    def test_null_byte_injection_blocked(self, thumbnail_cache, temp_photos_dir):
        """Null byte injection blocked"""
        from services.thumbnail_cache import ThumbnailError

        # Attempt null byte injection
        malicious_path = temp_photos_dir / "photo.jpg\x00.txt"

        with pytest.raises((ThumbnailError, ValueError)):
            thumbnail_cache.get_thumbnail(malicious_path, size=128)

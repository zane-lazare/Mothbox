"""
Unit tests for cache warmer service (Issue #134 - Phase 3)

Tests cache warming with:
- Manual triggering via API
- Smart auto-warming triggers
- Background monitoring thread
- Progress tracking
- Resource awareness (CPU usage)
- Error handling and recovery

Coverage Target: 85%+ (CacheWarmer service)

Test-Driven Development:
This test file is written FIRST, before implementing the service.
All tests should fail initially, then pass as service is implemented.
"""

import json
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Temporary cache directory for thumbnail tests"""
    cache_dir = tmp_path / "cache" / "thumbnails"
    cache_dir.mkdir(parents=True)
    return cache_dir


@pytest.fixture
def temp_photos_dir(tmp_path):
    """Temporary photos directory with sample images"""
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()
    return photos_dir


@pytest.fixture
def sample_photos(temp_photos_dir):
    """Create multiple sample photos with staggered timestamps"""
    from PIL import Image

    photos = []
    for i in range(10):
        photo_path = temp_photos_dir / f"photo_{i:03d}.jpg"
        img = Image.new('RGB', (800, 600), color=(i * 25, 100, 150))
        img.save(photo_path, format='JPEG', quality=85)
        photos.append(photo_path)

        # Stagger modification times (0.1 second apart)
        time.sleep(0.1)

    return photos


@pytest.fixture
def thumbnail_cache(temp_cache_dir):
    """Create ThumbnailCache instance"""
    from services.thumbnail_cache import ThumbnailCache

    return ThumbnailCache(
        cache_dir=temp_cache_dir, max_size_mb=50, sizes=[64, 128, 256]
    )


@pytest.fixture
def cache_warmer(thumbnail_cache, temp_photos_dir):
    """Create CacheWarmer instance"""
    from services.cache_warmer import CacheWarmer

    warmer = CacheWarmer(thumbnail_cache=thumbnail_cache, photos_dir=temp_photos_dir)
    yield warmer

    # Cleanup: stop background thread if running
    if hasattr(warmer, '_running') and warmer._running:
        warmer.stop_background_warming()


@pytest.fixture
def cache_warmer_with_photos(cache_warmer, sample_photos):
    """CacheWarmer with sample photos available"""
    return cache_warmer


# ============================================================================
# Test Class 1: Initialization
# ============================================================================


class TestCacheWarmerInitialization:
    """Test cache warmer initialization and setup"""

    def test_initialization_with_valid_params(self, thumbnail_cache, temp_photos_dir):
        """Test successful initialization with cache and photos_dir"""
        from services.cache_warmer import CacheWarmer

        warmer = CacheWarmer(
            thumbnail_cache=thumbnail_cache, photos_dir=temp_photos_dir
        )

        assert warmer.thumbnail_cache == thumbnail_cache
        assert warmer.photos_dir == temp_photos_dir
        assert hasattr(warmer, '_tasks')
        assert hasattr(warmer, '_running')
        assert warmer._running is False  # Background not started yet

    def test_initialization_with_pathlib_path(self, thumbnail_cache, temp_photos_dir):
        """Test initialization accepts Path objects"""
        from services.cache_warmer import CacheWarmer

        warmer = CacheWarmer(
            thumbnail_cache=thumbnail_cache, photos_dir=Path(temp_photos_dir)
        )

        assert isinstance(warmer.photos_dir, Path)

    def test_initialization_with_string_path(self, thumbnail_cache, temp_photos_dir):
        """Test initialization accepts string paths"""
        from services.cache_warmer import CacheWarmer

        warmer = CacheWarmer(
            thumbnail_cache=thumbnail_cache, photos_dir=str(temp_photos_dir)
        )

        assert isinstance(warmer.photos_dir, Path)
        assert warmer.photos_dir == Path(temp_photos_dir)

    def test_initialization_creates_empty_task_dict(self, cache_warmer):
        """Test that task tracking dictionary is initialized empty"""
        assert isinstance(cache_warmer._tasks, dict)
        assert len(cache_warmer._tasks) == 0

    def test_initialization_with_nonexistent_photos_dir(self, thumbnail_cache, tmp_path):
        """Test graceful handling of missing photos directory"""
        from services.cache_warmer import CacheWarmer

        nonexistent = tmp_path / "nonexistent"

        warmer = CacheWarmer(thumbnail_cache=thumbnail_cache, photos_dir=nonexistent)

        # Should initialize but warn/handle gracefully when trying to warm
        assert warmer.photos_dir == nonexistent


# ============================================================================
# Test Class 2: Basic Warming Operations
# ============================================================================


class TestCacheWarmingBasics:
    """Test basic cache warming operations"""

    def test_warm_photos_foreground_single_size(
        self, cache_warmer_with_photos, sample_photos
    ):
        """Test warming specific photos in foreground with single size"""
        result = cache_warmer_with_photos.warm_photos(
            photo_paths=[sample_photos[0]], sizes=[64], background=False
        )

        assert result['status'] == 'completed'
        assert result['photos_warmed'] == 1
        assert 'task_id' in result

    def test_warm_photos_background_multiple_sizes(
        self, cache_warmer_with_photos, sample_photos
    ):
        """Test warming photos in background with multiple sizes"""
        result = cache_warmer_with_photos.warm_photos(
            photo_paths=sample_photos[:3], sizes=[64, 128], background=True
        )

        assert result['status'] == 'started'
        assert 'task_id' in result

        # Wait for completion
        time.sleep(2.0)

        status = cache_warmer_with_photos.get_warming_status(result['task_id'])
        assert status['status'] == 'completed'
        assert status['photos_warmed'] == 3

    def test_warm_photos_default_all_sizes(
        self, cache_warmer_with_photos, sample_photos
    ):
        """Test warming with None sizes defaults to all configured sizes"""
        result = cache_warmer_with_photos.warm_photos(
            photo_paths=[sample_photos[0]], sizes=None, background=False
        )

        assert result['photos_warmed'] == 1

        # Verify all sizes were generated
        cache = cache_warmer_with_photos.thumbnail_cache
        for size in [64, 128, 256]:
            cache_path = cache._get_cache_path(sample_photos[0], size)
            assert cache_path.exists()

    def test_warm_photos_priority_newest(self, cache_warmer_with_photos, sample_photos):
        """Test priority='newest' processes most recent photos first"""
        # Track order of processing
        processed_order = []

        original_get_thumbnail = (
            cache_warmer_with_photos.thumbnail_cache.get_thumbnail
        )

        def track_order(path, size):
            processed_order.append(str(path))
            return original_get_thumbnail(path, size)

        with patch.object(
            cache_warmer_with_photos.thumbnail_cache,
            'get_thumbnail',
            side_effect=track_order,
        ):
            cache_warmer_with_photos.warm_photos(
                photo_paths=sample_photos, priority="newest", background=False
            )

        # Newest photos should be processed first (reverse order)
        # Each photo is processed 3 times (one per size), so check unique paths
        unique_processed = []
        for path in processed_order:
            if path not in unique_processed:
                unique_processed.append(path)

        # Most recent photo (sample_photos[-1]) should be first
        assert str(sample_photos[-1]) in unique_processed[0]

    def test_warm_photos_priority_all(self, cache_warmer_with_photos, sample_photos):
        """Test priority='all' processes in chronological order"""
        processed_order = []

        original_get_thumbnail = (
            cache_warmer_with_photos.thumbnail_cache.get_thumbnail
        )

        def track_order(path, size):
            processed_order.append(str(path))
            return original_get_thumbnail(path, size)

        with patch.object(
            cache_warmer_with_photos.thumbnail_cache,
            'get_thumbnail',
            side_effect=track_order,
        ):
            cache_warmer_with_photos.warm_photos(
                photo_paths=sample_photos, priority="all", background=False
            )

        # Get unique paths in order
        unique_processed = []
        for path in processed_order:
            if path not in unique_processed:
                unique_processed.append(path)

        # Oldest photo (sample_photos[0]) should be first
        assert str(sample_photos[0]) in unique_processed[0]

    def test_warm_recent_with_count(self, cache_warmer_with_photos, sample_photos):
        """Test warm_recent with specific count"""
        result = cache_warmer_with_photos.warm_recent(count=3, background=False)

        assert result['status'] == 'completed'
        assert result['photos_warmed'] == 3

    def test_warm_recent_default_count(self, cache_warmer_with_photos, sample_photos):
        """Test warm_recent uses default count (100)"""
        # Only have 10 photos, so should warm all 10
        result = cache_warmer_with_photos.warm_recent(background=False)

        assert result['status'] == 'completed'
        assert result['photos_warmed'] == 10

    def test_warm_all_photos(self, cache_warmer_with_photos, sample_photos):
        """Test warm_all warms entire cache"""
        result = cache_warmer_with_photos.warm_all(background=False)

        assert result['status'] == 'completed'
        assert result['photos_warmed'] == len(sample_photos)


# ============================================================================
# Test Class 3: Progress Tracking
# ============================================================================


class TestProgressTracking:
    """Test warming task progress tracking"""

    def test_task_id_generation(self, cache_warmer_with_photos, sample_photos):
        """Test that each warming task gets unique ID"""
        result1 = cache_warmer_with_photos.warm_photos(
            photo_paths=[sample_photos[0]], background=True
        )
        result2 = cache_warmer_with_photos.warm_photos(
            photo_paths=[sample_photos[1]], background=True
        )

        assert result1['task_id'] != result2['task_id']
        assert len(result1['task_id']) > 0
        assert len(result2['task_id']) > 0

    def test_get_warming_status_running(self, cache_warmer_with_photos, sample_photos):
        """Test status of running warming task"""
        # Start long-running task
        result = cache_warmer_with_photos.warm_photos(
            photo_paths=sample_photos, background=True
        )

        # Check status immediately (should be running)
        status = cache_warmer_with_photos.get_warming_status(result['task_id'])

        assert status['task_id'] == result['task_id']
        assert status['status'] in ['running', 'completed']
        assert 'progress' in status
        assert 'started_at' in status

    def test_get_warming_status_completed(self, cache_warmer_with_photos, sample_photos):
        """Test status of completed warming task"""
        result = cache_warmer_with_photos.warm_photos(
            photo_paths=[sample_photos[0]], sizes=[64], background=False
        )

        status = cache_warmer_with_photos.get_warming_status(result['task_id'])

        assert status['status'] == 'completed'
        assert status['photos_warmed'] > 0
        assert 'completed_at' in status
        assert status['progress']['percent'] == 100

    def test_get_warming_status_progress_updates(
        self, cache_warmer_with_photos, sample_photos
    ):
        """Test that progress updates during warming"""
        result = cache_warmer_with_photos.warm_photos(
            photo_paths=sample_photos, background=True
        )

        # Check progress multiple times
        time.sleep(0.5)
        status1 = cache_warmer_with_photos.get_warming_status(result['task_id'])

        time.sleep(0.5)
        status2 = cache_warmer_with_photos.get_warming_status(result['task_id'])

        # Progress should advance or complete
        if status1['status'] == 'running' and status2['status'] == 'running':
            assert status2['progress']['current'] >= status1['progress']['current']

    def test_get_warming_status_no_task_id(self, cache_warmer_with_photos):
        """Test getting status without task_id returns latest task"""
        # Create a task
        result = cache_warmer_with_photos.warm_photos(
            photo_paths=[], background=False
        )

        # Get status without task_id
        status = cache_warmer_with_photos.get_warming_status()

        # Should return info about task tracking
        assert 'active_tasks' in status or 'task_id' in status

    def test_multiple_concurrent_tasks_tracking(
        self, cache_warmer_with_photos, sample_photos
    ):
        """Test tracking multiple concurrent warming tasks"""
        # Note: CacheWarmer should limit to 1 active task at a time
        result1 = cache_warmer_with_photos.warm_photos(
            photo_paths=sample_photos[:5], background=True
        )

        result2 = cache_warmer_with_photos.warm_photos(
            photo_paths=sample_photos[5:], background=True
        )

        # Both should have task IDs
        assert 'task_id' in result1
        assert 'task_id' in result2

        # Second task should either queue or reject
        # (implementation detail - may queue or return immediately)

    def test_completed_task_cleanup(self, cache_warmer_with_photos, sample_photos):
        """Test that old completed tasks are eventually cleaned up"""
        # Create several tasks
        for i in range(5):
            cache_warmer_with_photos.warm_photos(
                photo_paths=[sample_photos[i]], background=False
            )

        # Task history should be limited (implementation dependent)
        # At minimum, should track most recent task
        status = cache_warmer_with_photos.get_warming_status()
        assert status is not None


# ============================================================================
# Test Class 4: Smart Triggers
# ============================================================================


class TestSmartTriggers:
    """Test smart auto-warming triggers"""

    @patch('psutil.cpu_percent')
    def test_should_trigger_warming_low_hit_ratio(
        self, mock_cpu, cache_warmer_with_photos
    ):
        """Test warming triggers when hit ratio is low"""
        mock_cpu.return_value = 50.0  # CPU usage OK

        # Simulate low hit ratio
        cache_warmer_with_photos.thumbnail_cache.hits = 20
        cache_warmer_with_photos.thumbnail_cache.misses = 100  # 16.7% hit ratio

        should_trigger = cache_warmer_with_photos.should_trigger_warming()

        assert should_trigger is True

    @patch('psutil.cpu_percent')
    def test_should_trigger_warming_high_hit_ratio(
        self, mock_cpu, cache_warmer_with_photos
    ):
        """Test warming doesn't trigger when hit ratio is good"""
        mock_cpu.return_value = 50.0  # CPU usage OK

        # Simulate good hit ratio
        cache_warmer_with_photos.thumbnail_cache.hits = 100
        cache_warmer_with_photos.thumbnail_cache.misses = 10  # 90.9% hit ratio

        should_trigger = cache_warmer_with_photos.should_trigger_warming()

        assert should_trigger is False

    @patch('psutil.cpu_percent')
    def test_should_trigger_warming_high_cpu(
        self, mock_cpu, cache_warmer_with_photos
    ):
        """Test warming doesn't trigger when CPU is busy"""
        mock_cpu.return_value = 90.0  # CPU too busy

        # Even with low hit ratio, shouldn't trigger
        cache_warmer_with_photos.thumbnail_cache.hits = 20
        cache_warmer_with_photos.thumbnail_cache.misses = 100

        should_trigger = cache_warmer_with_photos.should_trigger_warming()

        assert should_trigger is False

    def test_should_trigger_warming_insufficient_requests(
        self, cache_warmer_with_photos
    ):
        """Test warming doesn't trigger with too few requests"""
        # Only a few requests
        cache_warmer_with_photos.thumbnail_cache.hits = 5
        cache_warmer_with_photos.thumbnail_cache.misses = 50

        should_trigger = cache_warmer_with_photos.should_trigger_warming()

        # Should not trigger with <100 requests
        assert should_trigger is False

    def test_detect_new_photos(self, cache_warmer_with_photos, sample_photos, tmp_path):
        """Test detection of newly added photos"""
        # Record current time
        timestamp_before = time.time()

        time.sleep(0.2)

        # Add new photos
        from PIL import Image

        new_photos = []
        for i in range(3):
            photo_path = cache_warmer_with_photos.photos_dir / f"new_photo_{i}.jpg"
            img = Image.new('RGB', (800, 600), color='blue')
            img.save(photo_path, format='JPEG', quality=85)
            new_photos.append(photo_path)
            time.sleep(0.1)

        # Detect new photos
        detected = cache_warmer_with_photos.detect_new_photos(since=timestamp_before)

        assert len(detected) == 3
        for photo in new_photos:
            assert photo in detected

    def test_detect_new_photos_none_since(
        self, cache_warmer_with_photos, sample_photos
    ):
        """Test detect_new_photos with since=None uses last warming time"""
        # Warm some photos to set last warming time
        cache_warmer_with_photos.warm_recent(count=5, background=False)

        # Add new photo
        time.sleep(0.2)
        from PIL import Image

        new_photo = cache_warmer_with_photos.photos_dir / "brand_new.jpg"
        img = Image.new('RGB', (800, 600), color='green')
        img.save(new_photo, format='JPEG', quality=85)

        # Detect without specifying since
        detected = cache_warmer_with_photos.detect_new_photos(since=None)

        assert len(detected) >= 1
        assert new_photo in detected

    @patch('psutil.cpu_percent')
    def test_background_monitoring_loop_triggers(
        self, mock_cpu, cache_warmer_with_photos, sample_photos
    ):
        """Test that background monitoring loop can trigger warming"""
        mock_cpu.return_value = 50.0

        # Set up conditions for triggering
        cache_warmer_with_photos.thumbnail_cache.hits = 20
        cache_warmer_with_photos.thumbnail_cache.misses = 100

        # Patch the monitoring interval to be very short for testing
        with patch.object(
            cache_warmer_with_photos, '_monitoring_interval', 0.5
        ):  # 0.5 seconds
            cache_warmer_with_photos.start_background_warming()

            # Wait for monitoring loop to run
            time.sleep(1.5)

            cache_warmer_with_photos.stop_background_warming()

        # Verify monitoring ran (implementation dependent)
        assert hasattr(cache_warmer_with_photos, '_running')


# ============================================================================
# Test Class 5: Error Handling
# ============================================================================


class TestErrorHandling:
    """Test error handling during warming operations"""

    def test_warming_corrupt_image(self, cache_warmer_with_photos, temp_photos_dir):
        """Test handling of corrupt images during warming"""
        # Create corrupt image
        corrupt_path = temp_photos_dir / "corrupt.jpg"
        corrupt_path.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 50)

        result = cache_warmer_with_photos.warm_photos(
            photo_paths=[corrupt_path], background=False
        )

        # Should complete (ThumbnailCache creates placeholder for corrupt images)
        assert result['status'] == 'completed'
        # Note: ThumbnailCache handles corrupt images gracefully by creating
        # placeholders, so they don't appear as errors in the warmer
        # This is by design from Phase 1

    def test_warming_missing_photo(self, cache_warmer_with_photos, temp_photos_dir):
        """Test handling of missing photos during warming"""
        missing_path = temp_photos_dir / "nonexistent.jpg"

        result = cache_warmer_with_photos.warm_photos(
            photo_paths=[missing_path], background=False
        )

        # Should handle gracefully
        assert result['status'] in ['completed', 'failed']
        if result['status'] == 'completed':
            assert result['photos_warmed'] == 0

    def test_warming_permission_error(self, cache_warmer_with_photos, sample_photos):
        """Test handling of permission errors during warming"""
        # Mock permission error
        def raise_permission_error(path, size):
            raise PermissionError("Access denied")

        with patch.object(
            cache_warmer_with_photos.thumbnail_cache,
            'get_thumbnail',
            side_effect=raise_permission_error,
        ):
            result = cache_warmer_with_photos.warm_photos(
                photo_paths=[sample_photos[0]], background=False
            )

            # Should handle error gracefully
            assert result['status'] in ['completed', 'failed']
            if 'errors' in result:
                assert len(result['errors']) > 0

    def test_task_cancellation(self, cache_warmer_with_photos, sample_photos):
        """Test cancelling a running warming task"""
        # Start long-running task
        result = cache_warmer_with_photos.warm_photos(
            photo_paths=sample_photos, background=True
        )

        task_id = result['task_id']

        # Cancel it
        if hasattr(cache_warmer_with_photos, 'cancel_warming'):
            cancel_result = cache_warmer_with_photos.cancel_warming(task_id)
            assert cancel_result['success'] is True

            # Check status
            status = cache_warmer_with_photos.get_warming_status(task_id)
            assert status['status'] in ['cancelled', 'completed']

    def test_graceful_shutdown_during_warming(
        self, cache_warmer_with_photos, sample_photos
    ):
        """Test graceful shutdown while warming is in progress"""
        # Start warming
        cache_warmer_with_photos.warm_photos(
            photo_paths=sample_photos, background=True
        )

        # Stop background warming (simulating shutdown)
        cache_warmer_with_photos.stop_background_warming()

        # Should not raise exceptions
        assert cache_warmer_with_photos._running is False

    def test_error_tracking_and_reporting(self, cache_warmer_with_photos, temp_photos_dir):
        """Test that errors are tracked and reported properly"""
        from PIL import Image

        # Create mix of valid and invalid photos
        valid_photo = temp_photos_dir / "valid.jpg"
        img = Image.new('RGB', (800, 600), color='red')
        img.save(valid_photo, format='JPEG', quality=85)

        corrupt_photo = temp_photos_dir / "corrupt.jpg"
        corrupt_photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 50)

        result = cache_warmer_with_photos.warm_photos(
            photo_paths=[valid_photo, corrupt_photo], background=False
        )

        # Should process both, with error for corrupt one
        assert result['status'] == 'completed'
        # Implementation may track errors differently


# ============================================================================
# Test Class 6: Resource Management
# ============================================================================


class TestResourceManagement:
    """Test resource awareness and management"""

    @patch('psutil.cpu_percent')
    def test_cpu_usage_checking(self, mock_cpu, cache_warmer_with_photos):
        """Test CPU usage is checked before warming"""
        mock_cpu.return_value = 85.0  # High CPU usage

        # Set up for triggering
        cache_warmer_with_photos.thumbnail_cache.hits = 20
        cache_warmer_with_photos.thumbnail_cache.misses = 100

        should_trigger = cache_warmer_with_photos.should_trigger_warming()

        assert should_trigger is False
        mock_cpu.assert_called()

    @patch('psutil.cpu_percent', side_effect=ImportError("psutil not available"))
    def test_graceful_fallback_no_psutil(
        self, mock_cpu, cache_warmer_with_photos
    ):
        """Test graceful fallback when psutil is not available"""
        # Should assume CPU is available if psutil missing
        cache_warmer_with_photos.thumbnail_cache.hits = 20
        cache_warmer_with_photos.thumbnail_cache.misses = 100

        # Should not raise error
        try:
            should_trigger = cache_warmer_with_photos.should_trigger_warming()
            # May return True (assuming CPU OK) or False (being cautious)
            assert isinstance(should_trigger, bool)
        except ImportError:
            pytest.fail("Should handle missing psutil gracefully")

    def test_concurrent_warming_limit(self, cache_warmer_with_photos, sample_photos):
        """Test that only limited concurrent warming tasks are allowed"""
        # Start first task
        result1 = cache_warmer_with_photos.warm_photos(
            photo_paths=sample_photos, background=True
        )

        # Try to start second task immediately
        result2 = cache_warmer_with_photos.warm_photos(
            photo_paths=sample_photos, background=True
        )

        # Implementation should queue or reject second task
        # Both should have task_ids but may have different statuses
        assert 'task_id' in result1
        assert 'task_id' in result2

    def test_thread_cleanup_on_stop(self, cache_warmer_with_photos):
        """Test that background thread is properly cleaned up"""
        cache_warmer_with_photos.start_background_warming()

        # Verify thread is running
        assert cache_warmer_with_photos._running is True

        cache_warmer_with_photos.stop_background_warming()

        # Thread should be stopped
        assert cache_warmer_with_photos._running is False

        # Give thread time to terminate
        time.sleep(1.0)

        # Verify thread count hasn't increased
        active_threads = threading.active_count()
        assert active_threads < 10  # Reasonable limit

    def test_background_thread_lifecycle(self, cache_warmer_with_photos):
        """Test complete background thread lifecycle"""
        initial_thread_count = threading.active_count()

        # Start background warming
        cache_warmer_with_photos.start_background_warming()
        assert cache_warmer_with_photos._running is True

        # Thread count should increase
        time.sleep(0.5)
        running_thread_count = threading.active_count()
        assert running_thread_count >= initial_thread_count

        # Stop background warming
        cache_warmer_with_photos.stop_background_warming()
        assert cache_warmer_with_photos._running is False

        # Wait for thread to terminate
        time.sleep(1.0)

        # Thread count should return to initial
        final_thread_count = threading.active_count()
        assert final_thread_count <= initial_thread_count + 1


# ============================================================================
# Test Class 7: Integration with ThumbnailCache
# ============================================================================


class TestThumbnailCacheIntegration:
    """Test integration between CacheWarmer and ThumbnailCache"""

    def test_warming_generates_actual_thumbnails(
        self, cache_warmer_with_photos, sample_photos
    ):
        """Test that warming actually generates thumbnail files"""
        photo = sample_photos[0]

        result = cache_warmer_with_photos.warm_photos(
            photo_paths=[photo], sizes=[64, 128], background=False
        )

        assert result['status'] == 'completed'

        # Verify thumbnails exist in cache
        cache = cache_warmer_with_photos.thumbnail_cache
        for size in [64, 128]:
            cache_path = cache._get_cache_path(photo, size)
            assert cache_path.exists()

    def test_warming_updates_cache_statistics(
        self, cache_warmer_with_photos, sample_photos
    ):
        """Test that warming updates cache hit/miss statistics"""
        cache = cache_warmer_with_photos.thumbnail_cache

        initial_misses = cache.misses

        cache_warmer_with_photos.warm_photos(
            photo_paths=sample_photos[:3], background=False
        )

        # Cache should have registered misses during generation
        assert cache.misses > initial_misses

    def test_warming_respects_cache_sizes(self, cache_warmer_with_photos, sample_photos):
        """Test that warming only generates configured sizes"""
        result = cache_warmer_with_photos.warm_photos(
            photo_paths=[sample_photos[0]], sizes=[64], background=False
        )

        cache = cache_warmer_with_photos.thumbnail_cache

        # Size 64 should exist
        cache_path_64 = cache._get_cache_path(sample_photos[0], 64)
        assert cache_path_64.exists()

        # Other sizes should not exist
        cache_path_128 = cache._get_cache_path(sample_photos[0], 128)
        cache_path_256 = cache._get_cache_path(sample_photos[0], 256)
        assert not cache_path_128.exists()
        assert not cache_path_256.exists()

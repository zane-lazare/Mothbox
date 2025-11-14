"""
Test atomic deque behavior for statistics tracking in MetadataCache.

This module verifies that using collections.deque(maxlen=1000) prevents
the race condition where multiple threads could cause _total_response_times
list to grow beyond 1000 entries.

Original Issue:
- List append + conditional pop is not atomic
- Multiple threads could cause list to grow beyond 1000 (memory leak)

Solution:
- Use collections.deque(maxlen=1000) which handles bounded size atomically

Related to: Issue #100 - Metadata API caching, statistics race condition
"""

import threading
import time
from collections import deque

import pytest

from webui.backend.services.metadata_cache import MetadataCache


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create temporary cache directory"""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def cache(temp_cache_dir):
    """Create MetadataCache instance"""
    return MetadataCache(
        cache_dir=temp_cache_dir,
        l1_max_size=100,
        l2_max_size=1000,
        cache_version="1.0"
    )


def test_response_times_uses_deque(cache):
    """
    Test that _total_response_times is a deque with maxlen=1000.

    This ensures the atomic bounded collection is being used instead of
    a regular list with manual size management.
    """
    # Verify type is deque
    assert isinstance(cache._total_response_times, deque), \
        f"Expected deque, got {type(cache._total_response_times)}"

    # Verify maxlen is set to 1000
    assert cache._total_response_times.maxlen == 1000, \
        f"Expected maxlen=1000, got {cache._total_response_times.maxlen}"


def test_deque_automatically_bounds_size(cache):
    """
    Test that deque automatically maintains maxlen without manual pop().

    When adding more than maxlen items, deque automatically evicts oldest.
    """
    # Add 1500 response times (exceeds maxlen of 1000)
    for i in range(1500):
        cache._record_hit("l1", float(i))

    # Verify size never exceeds maxlen
    assert len(cache._total_response_times) == 1000, \
        f"Expected exactly 1000 items, got {len(cache._total_response_times)}"

    # Verify oldest items were evicted (should start at 500, not 0)
    first_item = cache._total_response_times[0]
    assert first_item == 500.0, \
        f"Expected first item to be 500.0 (oldest evicted), got {first_item}"

    # Verify newest items are retained
    last_item = cache._total_response_times[-1]
    assert last_item == 1499.0, \
        f"Expected last item to be 1499.0, got {last_item}"


def test_concurrent_statistics_recording_no_overflow(cache):
    """
    Test that concurrent threads recording statistics don't cause overflow.

    This is the main race condition test - verifies that deque's atomic
    maxlen enforcement prevents the list from growing beyond 1000 even
    with concurrent appends from multiple threads.
    """
    # Storage for any size violations observed
    size_violations: list[int] = []
    lock = threading.Lock()

    def record_many_stats(thread_id: int, count: int):
        """Worker thread that records many statistics"""
        for i in range(count):
            # Record hit with response time
            cache._record_hit("l1", float(thread_id * 10000 + i))

            # Occasionally check size (simulate real concurrent access pattern)
            if i % 50 == 0:
                current_size = len(cache._total_response_times)
                if current_size > 1000:
                    with lock:
                        size_violations.append(current_size)

            # Small delay to increase thread interleaving
            if i % 100 == 0:
                time.sleep(0.0001)

    # Create 10 threads, each recording 500 statistics (5000 total)
    threads = []
    for thread_id in range(10):
        thread = threading.Thread(
            target=record_many_stats,
            args=(thread_id, 500)
        )
        threads.append(thread)

    # Start all threads
    for thread in threads:
        thread.start()

    # Wait for completion
    for thread in threads:
        thread.join()

    # Verify no size violations occurred
    assert len(size_violations) == 0, \
        f"Size violations detected: {size_violations}"

    # Verify final size is exactly maxlen
    final_size = len(cache._total_response_times)
    assert final_size == 1000, \
        f"Expected final size of 1000, got {final_size}"


def test_deque_fifo_behavior_under_load(cache):
    """
    Test that deque maintains FIFO eviction under concurrent load.

    Verifies that even with concurrent access, deque correctly evicts
    oldest items first (FIFO behavior).
    """
    # Pre-fill with known sequence
    for i in range(1000):
        cache._record_hit("l1", float(i))

    # Verify initial state
    assert cache._total_response_times[0] == 0.0
    assert cache._total_response_times[-1] == 999.0

    # Add 100 more items concurrently
    def add_items(start_value: int):
        for i in range(50):
            cache._record_hit("l1", float(start_value + i))

    threads = [
        threading.Thread(target=add_items, args=(1000,)),
        threading.Thread(target=add_items, args=(1050,))
    ]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    # Verify oldest 100 items were evicted (FIFO)
    # First item should now be 100.0 (items 0-99 evicted)
    first_item = cache._total_response_times[0]
    assert first_item == 100.0, \
        f"Expected first item to be 100.0 after FIFO eviction, got {first_item}"

    # Size should still be exactly 1000
    assert len(cache._total_response_times) == 1000


def test_statistics_calculation_with_deque(cache):
    """
    Test that statistics calculation works correctly with deque.

    Verifies that average response time calculation and other statistics
    work correctly with deque data structure.
    """
    # Add known response times
    response_times = [10.0, 20.0, 30.0, 40.0, 50.0]
    for rt in response_times:
        cache._record_hit("l1", rt)

    # Get statistics
    stats = cache.get_statistics()

    # Verify average response time calculation
    expected_avg = sum(response_times) / len(response_times)
    assert stats.avg_response_time_ms == expected_avg, \
        f"Expected avg {expected_avg}, got {stats.avg_response_time_ms}"

    # Verify hit count
    assert stats.l1_hits == 5


def test_clear_resets_deque(cache):
    """
    Test that clear() properly resets the deque.

    Verifies that clearing statistics creates a fresh deque with maxlen.
    """
    # Add some response times
    for i in range(100):
        cache._record_hit("l1", float(i))

    # Clear cache
    cache.clear()

    # Verify deque is empty but still has maxlen
    assert len(cache._total_response_times) == 0, \
        "Expected empty deque after clear"
    assert cache._total_response_times.maxlen == 1000, \
        "Expected maxlen to be preserved after clear"

    # Verify we can still add items
    cache._record_hit("l1", 1.0)
    assert len(cache._total_response_times) == 1


def test_deque_memory_efficiency(cache):
    """
    Test that deque is more memory efficient than list + manual pop.

    This is a regression test - verifies that the memory leak issue
    from the original list-based implementation is resolved.
    """
    # Simulate heavy load (10,000 statistics recorded)
    for i in range(10000):
        cache._record_hit("l1", float(i))

    # Size should never exceed maxlen (would have been >10000 with buggy list)
    assert len(cache._total_response_times) == 1000, \
        "Memory leak detected: deque size exceeded maxlen"

    # Verify oldest items were evicted (FIFO)
    # Should contain items 9000-9999
    assert cache._total_response_times[0] == 9000.0
    assert cache._total_response_times[-1] == 9999.0


def test_deque_thread_safety_with_stats_lock(cache):
    """
    Test that deque operations are properly protected by _stats_lock.

    Verifies that even though deque operations are atomic, the lock
    is still used for consistency with other statistics operations.
    """
    errors = []

    def concurrent_access():
        try:
            for _ in range(100):
                # These operations should all be protected by _stats_lock
                cache._record_hit("l1", 1.0)
                cache._record_l2_miss(2.0)
                stats = cache.get_statistics()
                assert stats is not None
        except Exception as e:
            errors.append(str(e))

    # Run 5 threads concurrently
    threads = [threading.Thread(target=concurrent_access) for _ in range(5)]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    # Verify no errors occurred
    assert len(errors) == 0, f"Errors during concurrent access: {errors}"

    # Verify statistics are consistent
    stats = cache.get_statistics()
    assert stats.l1_hits == 500  # 5 threads * 100 operations
    assert stats.l2_misses == 500

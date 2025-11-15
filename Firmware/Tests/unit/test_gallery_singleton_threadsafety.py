"""
Test thread-safety of MetadataCache singleton initialization in gallery.py.

This module verifies that the double-checked locking pattern properly prevents
multiple cache instances from being created when get_metadata_cache() is called
concurrently from multiple threads.

Test scenarios:
1. Concurrent initialization - multiple threads calling get_metadata_cache()
2. Singleton property - all threads receive the same cache instance
3. Race condition prevention - no duplicate instances created

Related to: Issue #100 - Metadata API caching
"""

import threading
import time

import pytest


@pytest.fixture(autouse=True)
def reset_cache_singleton():
    """Reset cache singleton before and after each test."""
    from webui.backend.routes import gallery
    gallery._reset_cache()
    yield
    gallery._reset_cache()


def test_concurrent_singleton_initialization():
    """
    Test that concurrent calls to get_metadata_cache() return same instance.

    This test verifies the double-checked locking pattern prevents race conditions
    by spawning multiple threads that simultaneously call get_metadata_cache().
    All threads should receive the same singleton instance.
    """
    from webui.backend.routes.gallery import get_metadata_cache

    # Storage for cache instances retrieved by each thread
    cache_instances: list = []
    lock = threading.Lock()

    def get_cache_instance():
        """Thread worker that fetches cache instance."""
        # Add small random delay to increase chance of race condition
        time.sleep(0.001)

        cache = get_metadata_cache()

        # Store instance in thread-safe manner
        with lock:
            cache_instances.append(cache)

    # Create 20 threads to simulate concurrent access
    threads = []
    num_threads = 20

    for _ in range(num_threads):
        thread = threading.Thread(target=get_cache_instance)
        threads.append(thread)

    # Start all threads simultaneously
    for thread in threads:
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Verify all threads got instances
    assert len(cache_instances) == num_threads, \
        f"Expected {num_threads} instances, got {len(cache_instances)}"

    # Verify all instances are the SAME object (singleton property)
    first_instance = cache_instances[0]
    for i, instance in enumerate(cache_instances[1:], start=1):
        assert instance is first_instance, \
            f"Thread {i} got different cache instance (id={id(instance)}) " \
            f"than thread 0 (id={id(first_instance)})"


def test_singleton_after_initialization():
    """
    Test that subsequent calls return cached instance without locking.

    After initial initialization, get_metadata_cache() should return the
    cached instance via the fast path (without acquiring the lock).
    """
    from webui.backend.routes.gallery import get_metadata_cache

    # First call initializes
    cache1 = get_metadata_cache()
    assert cache1 is not None

    # Subsequent calls should return same instance
    cache2 = get_metadata_cache()
    assert cache2 is cache1

    cache3 = get_metadata_cache()
    assert cache3 is cache1


def test_reset_cache_thread_safety():
    """
    Test that _reset_cache() is thread-safe with concurrent access.

    Verifies that resetting the cache while other threads are accessing it
    doesn't cause race conditions or errors.
    """
    from webui.backend.routes.gallery import _reset_cache, get_metadata_cache

    errors = []
    lock = threading.Lock()

    def access_cache():
        """Thread worker that repeatedly accesses cache."""
        try:
            for _ in range(10):
                cache = get_metadata_cache()
                assert cache is not None
                time.sleep(0.001)
        except Exception as e:
            with lock:
                errors.append(str(e))

    def reset_cache():
        """Thread worker that resets cache."""
        try:
            for _ in range(5):
                _reset_cache()
                time.sleep(0.002)
        except Exception as e:
            with lock:
                errors.append(str(e))

    # Create mix of accessor and reset threads
    threads = []

    # 5 threads accessing cache
    for _ in range(5):
        thread = threading.Thread(target=access_cache)
        threads.append(thread)

    # 2 threads resetting cache
    for _ in range(2):
        thread = threading.Thread(target=reset_cache)
        threads.append(thread)

    # Start all threads
    for thread in threads:
        thread.start()

    # Wait for completion
    for thread in threads:
        thread.join()

    # Verify no errors occurred
    assert len(errors) == 0, f"Errors during concurrent access: {errors}"


def test_lock_acquisition_timeout():
    """
    Test that lock acquisition doesn't cause deadlocks.

    Verifies that the lock is properly released even if initialization fails.
    """
    from unittest.mock import patch

    from webui.backend.routes import gallery

    # Force initialization to fail
    with patch('webui.backend.routes.gallery.MetadataCache') as mock_cache:
        mock_cache.side_effect = RuntimeError("Initialization failed")

        # First call should raise error but release lock
        with pytest.raises(RuntimeError, match="Initialization failed"):
            gallery.get_metadata_cache()

        # Subsequent calls should still be able to acquire lock
        with pytest.raises(RuntimeError, match="Initialization failed"):
            gallery.get_metadata_cache()


def test_memory_visibility_across_threads():
    """
    Test that cache instance is properly visible across threads.

    Verifies that memory barriers are properly established by the lock
    so that the initialized cache is visible to all threads.
    """
    from webui.backend.routes.gallery import get_metadata_cache

    # Storage for cache IDs from each thread
    cache_ids = []
    lock = threading.Lock()
    barrier = threading.Barrier(10)  # Synchronize 10 threads

    def get_cache_id():
        """Thread worker that gets cache and records its ID."""
        # Wait for all threads to be ready
        barrier.wait()

        # All threads fetch cache simultaneously
        cache = get_metadata_cache()
        cache_id = id(cache)

        with lock:
            cache_ids.append(cache_id)

    # Create threads
    threads = [threading.Thread(target=get_cache_id) for _ in range(10)]

    # Start all threads
    for thread in threads:
        thread.start()

    # Wait for completion
    for thread in threads:
        thread.join()

    # Verify all threads saw the same object ID
    assert len(set(cache_ids)) == 1, \
        f"Different cache IDs observed: {set(cache_ids)}"

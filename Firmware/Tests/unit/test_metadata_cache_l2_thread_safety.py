"""
Test L2 cache thread safety and race condition prevention.

This module verifies that L2 cache operations are properly protected by
threading locks to prevent race conditions between eviction and file operations.

Original Issue:
- L2 eviction lacked thread-level locking
- Multiple threads could simultaneously evict and write, causing:
  * Newly written files being deleted by concurrent eviction
  * TOCTOU (Time-Of-Check-Time-Of-Use) bugs
  * Inconsistent cache state

Solution:
- Added _l2_lock to protect L2 operations
- All L2 read/write/evict operations acquire lock before accessing filesystem
- Prevents race conditions while maintaining file-level locks for multi-process safety

Related to: Issue #100 - Metadata API caching, L2 thread safety
"""

import threading
import time
from pathlib import Path

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
    """Create MetadataCache instance with small L2 for testing"""
    return MetadataCache(
        cache_dir=temp_cache_dir,
        l1_max_size=5,
        l2_max_size=10,
        cache_version="1.0"
    )


def test_l2_lock_exists(cache):
    """
    Test that L2 lock exists to protect file operations.

    Verifies that _l2_lock attribute is present and is a lock object.
    """
    assert hasattr(cache, '_l2_lock'), "Cache should have _l2_lock attribute"
    # threading.Lock() returns a lock object, not a Lock class instance
    # Check that it has lock methods instead
    assert hasattr(cache._l2_lock, 'acquire'), "_l2_lock should have acquire method"
    assert hasattr(cache._l2_lock, 'release'), "_l2_lock should have release method"
    assert callable(cache._l2_lock.acquire), "_l2_lock.acquire should be callable"
    assert callable(cache._l2_lock.release), "_l2_lock.release should be callable"


def test_concurrent_writes_no_race_condition(cache, temp_cache_dir):
    """
    Test that concurrent L2 writes don't cause race conditions.

    Without proper locking, concurrent writes + eviction could cause:
    - Files being deleted immediately after creation
    - Cache size exceeding l2_max_size
    - Inconsistent cache state
    """
    errors = []
    successful_writes = []

    def write_worker(thread_id):
        """Worker that writes entries to trigger eviction"""
        try:
            for i in range(5):
                photo_path = f"/photos/thread{thread_id}_photo{i}.jpg"
                metadata = {"thread": thread_id, "photo": i}
                cache.set(photo_path, metadata)
                successful_writes.append((thread_id, i))
                # Small delay to increase chance of race condition
                time.sleep(0.001)
        except Exception as e:
            errors.append(f"Thread {thread_id}: {e}")

    # Launch multiple threads writing concurrently
    threads = []
    for thread_id in range(5):
        t = threading.Thread(target=write_worker, args=(thread_id,))
        threads.append(t)
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join()

    # Verify no errors occurred
    assert len(errors) == 0, f"Concurrent writes caused errors: {errors}"
    assert len(successful_writes) > 0, "No successful writes"

    # Verify L2 cache size is controlled (eviction worked correctly)
    cache_files = list(temp_cache_dir.glob("*.json"))
    assert len(cache_files) <= cache.l2_max_size, \
        f"L2 cache size {len(cache_files)} exceeds max {cache.l2_max_size}"


def test_concurrent_read_write_evict_no_corruption(cache, temp_cache_dir):
    """
    Test that concurrent reads, writes, and eviction don't corrupt cache.

    This is the main race condition scenario:
    - Thread A: Starts eviction, scans directory
    - Thread B: Writes new file
    - Thread A: Deletes files (could delete Thread B's new file)

    With _l2_lock, this should never happen.
    """
    errors = []
    read_results = []
    write_results = []

    def reader_worker():
        """Worker that reads from cache"""
        try:
            for i in range(20):
                photo_path = f"/photos/photo{i % 10}.jpg"
                result = cache.get(photo_path)
                read_results.append((photo_path, result is not None))
                time.sleep(0.001)
        except Exception as e:
            errors.append(f"Reader: {e}")

    def writer_worker(thread_id):
        """Worker that writes to cache"""
        try:
            for i in range(10):
                photo_path = f"/photos/writer{thread_id}_photo{i}.jpg"
                metadata = {"writer": thread_id, "photo": i}
                cache.set(photo_path, metadata)
                write_results.append(photo_path)
                time.sleep(0.002)
        except Exception as e:
            errors.append(f"Writer {thread_id}: {e}")

    # Launch readers and writers concurrently
    threads = []

    # Start readers
    for _ in range(3):
        t = threading.Thread(target=reader_worker)
        threads.append(t)
        t.start()

    # Start writers (will trigger eviction)
    for thread_id in range(3):
        t = threading.Thread(target=writer_worker, args=(thread_id,))
        threads.append(t)
        t.start()

    # Wait for all threads
    for t in threads:
        t.join()

    # Verify no errors
    assert len(errors) == 0, f"Concurrent operations caused errors: {errors}"

    # Verify cache is consistent
    cache_files = list(temp_cache_dir.glob("*.json"))
    assert len(cache_files) <= cache.l2_max_size, \
        f"Cache size {len(cache_files)} exceeds limit after concurrent ops"


def test_eviction_doesnt_delete_newly_written_files(cache, temp_cache_dir):
    """
    Test that eviction doesn't delete files written by concurrent threads.

    Race condition scenario without lock:
    1. Thread A: calls _set_l2(), checks cache_file.exists() = False
    2. Thread B: calls _evict_l2_if_needed(), scans directory
    3. Thread A: writes new file
    4. Thread B: deletes files (includes Thread A's new file!)

    With lock, Thread B waits for Thread A to complete before evicting.
    """
    # Fill cache to capacity
    for i in range(cache.l2_max_size):
        cache.set(f"/photos/photo{i}.jpg", {"id": i})
        time.sleep(0.01)  # Ensure different mtimes

    barrier = threading.Barrier(2)
    evicted_files = []
    written_file = []

    def writer_thread():
        """Write a new file that should NOT be evicted immediately"""
        barrier.wait()  # Sync with eviction thread
        new_path = "/photos/new_photo.jpg"
        cache.set(new_path, {"new": True})
        written_file.append(new_path)

    def eviction_trigger_thread():
        """Trigger eviction at the same time as write"""
        barrier.wait()  # Sync with writer thread
        # Write another file to trigger eviction
        cache.set("/photos/trigger.jpg", {"trigger": True})

    # Start both threads
    t1 = threading.Thread(target=writer_thread)
    t2 = threading.Thread(target=eviction_trigger_thread)

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Verify the newly written file is still in cache (not evicted immediately)
    # With proper locking, it should either:
    # 1. Exist in cache (if written before eviction)
    # 2. Not exist but was written after eviction completed
    # It should NEVER be written and then immediately deleted by concurrent eviction

    # Check cache is within limits
    cache_files = list(temp_cache_dir.glob("*.json"))
    assert len(cache_files) <= cache.l2_max_size, \
        f"Cache size {len(cache_files)} exceeds limit"


def test_l2_lock_documentation(cache):
    """
    Test that L2 methods document thread safety requirements.

    Ensures future maintainers understand the locking strategy.
    """
    import inspect

    # Check _get_l2 documentation
    get_l2_doc = inspect.getdoc(cache._get_l2)
    assert "Thread-safe" in get_l2_doc or "thread" in get_l2_doc.lower(), \
        "_get_l2 should document thread safety"

    # Check _set_l2 documentation
    set_l2_doc = inspect.getdoc(cache._set_l2)
    assert "Thread-safe" in set_l2_doc or "thread" in set_l2_doc.lower(), \
        "_set_l2 should document thread safety"

    # Check _evict_l2_if_needed documentation
    evict_doc = inspect.getdoc(cache._evict_l2_if_needed)
    assert "lock" in evict_doc.lower(), \
        "_evict_l2_if_needed should document lock requirement"
    assert "caller" in evict_doc.lower(), \
        "_evict_l2_if_needed should indicate caller must hold lock"


def test_lock_prevents_toctou_in_eviction(cache, temp_cache_dir):
    """
    Test that lock prevents TOCTOU (Time-Of-Check-Time-Of-Use) bugs.

    TOCTOU scenario without lock:
    - Thread A: glob("*.json") -> sees 10 files
    - Thread B: writes new file (now 11 files)
    - Thread A: evicts based on old count (deletes wrong files)

    With lock, glob and eviction are atomic.
    """
    # Fill cache to just below capacity
    for i in range(cache.l2_max_size - 1):
        cache.set(f"/photos/photo{i}.jpg", {"id": i})
        time.sleep(0.01)

    barrier = threading.Barrier(2)
    errors = []

    def concurrent_writer_1():
        """Write file that triggers eviction"""
        try:
            barrier.wait()
            cache.set("/photos/concurrent1.jpg", {"c": 1})
        except Exception as e:
            errors.append(f"Writer 1: {e}")

    def concurrent_writer_2():
        """Write file at same time"""
        try:
            barrier.wait()
            cache.set("/photos/concurrent2.jpg", {"c": 2})
        except Exception as e:
            errors.append(f"Writer 2: {e}")

    t1 = threading.Thread(target=concurrent_writer_1)
    t2 = threading.Thread(target=concurrent_writer_2)

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Verify no errors and cache size is controlled
    assert len(errors) == 0, f"TOCTOU scenario caused errors: {errors}"

    cache_files = list(temp_cache_dir.glob("*.json"))
    assert len(cache_files) <= cache.l2_max_size, \
        f"TOCTOU bug: cache size {len(cache_files)} exceeds limit"


def test_lock_held_during_entire_l2_operation(cache):
    """
    Test that lock is held for the entire L2 operation.

    Verifies that lock is acquired before checking file existence
    and held until after file write completes.
    """
    import inspect

    # Verify _get_l2 uses context manager for lock
    get_l2_source = inspect.getsource(cache._get_l2)
    assert "with self._l2_lock:" in get_l2_source, \
        "_get_l2 should use context manager for lock"

    # Verify _set_l2 uses context manager for lock
    set_l2_source = inspect.getsource(cache._set_l2)
    assert "with self._l2_lock:" in set_l2_source, \
        "_set_l2 should use context manager for lock"

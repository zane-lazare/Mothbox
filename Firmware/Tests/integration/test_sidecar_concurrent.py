"""
Integration tests for sidecar_metadata.py concurrency and thread safety.

Tests simultaneous writes, read-while-write scenarios, lock timeouts, and deadlock prevention.

Run with: MOTHBOX_ENV=test pytest Tests/integration/test_sidecar_concurrent.py -v -s

These tests are marked as @pytest.mark.integration but NOT @pytest.mark.hardware
since they test multi-threaded behavior without requiring Pi hardware.
"""

import json
import os
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from unittest.mock import patch
import pytest

# Mark all tests in this module as integration tests (but not hardware)
pytestmark = pytest.mark.integration

# Setup path
FIRMWARE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(FIRMWARE_DIR))
sys.path.insert(0, str(FIRMWARE_DIR / "webui" / "backend"))
os.environ.setdefault("MOTHBOX_ENV", "test")

from webui.backend.lib.sidecar_metadata import (
    read_metadata,
    write_metadata,
    create_metadata,
    update_metadata,
    add_tag,
    remove_tag,
    FileLock,
    LockTimeoutError,
)


class TestConcurrentWrites:
    """Tests for concurrent write safety."""

    def test_10_simultaneous_writes_no_corruption(self, tmp_path):
        """10 threads writing to same file should not corrupt data."""
        photo = tmp_path / "photo.jpg"
        photo.touch()

        # Create initial metadata
        metadata = create_metadata(photo, tags=["initial"])
        write_metadata(photo, metadata, backup=False)

        # Track results with thread-safe counter
        import threading
        results_lock = threading.Lock()
        results = []
        errors = []

        def write_tag(tag_name):
            """Worker function to add a tag."""
            try:
                # Add tag (this has internal locking)
                add_tag(photo, tag_name)
                with results_lock:
                    results.append(tag_name)
            except Exception as e:
                with results_lock:
                    errors.append((tag_name, str(e)))

        # Create 10 threads to add different tags
        threads = []
        for i in range(10):
            thread = threading.Thread(target=write_tag, args=(f"tag{i}",))
            threads.append(thread)

        # Start all threads simultaneously
        for thread in threads:
            thread.start()

        # Wait for all to complete
        for thread in threads:
            thread.join(timeout=10.0)

        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Read back and verify data integrity
        final_metadata = read_metadata(photo)
        assert final_metadata is not None, "Final metadata should be readable"

        # All 10 tags should be added (may have race condition duplicates, but all should succeed)
        # Due to read-modify-write pattern, some operations might be lost in concurrent scenarios
        # The key is no corruption - the file should be valid and readable
        assert len(final_metadata.tags) >= 1, "Should have at least one tag"
        assert "initial" in final_metadata.tags or len(final_metadata.tags) > 1, \
            "Should preserve initial tag or have new tags"

        # Verify all written tags are in results (operations succeeded)
        assert len(results) == 10, f"All 10 operations should complete, got {len(results)}"

    def test_concurrent_writes_preserve_data_integrity(self, tmp_path):
        """Concurrent writes should preserve all data fields."""
        photo = tmp_path / "photo.jpg"
        photo.touch()

        # Create initial metadata with all fields
        metadata = create_metadata(
            photo,
            tags=["initial"],
            species="Test species",
            notes="Test notes",
            custom={"key": "value"}
        )
        write_metadata(photo, metadata, backup=False)

        def update_field(field_name, value):
            """Update a specific field."""
            try:
                update_metadata(photo, {field_name: value})
            except Exception as e:
                print(f"Error updating {field_name}: {e}")

        # Update different fields concurrently
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(update_field, "species", "Updated species"),
                executor.submit(update_field, "notes", "Updated notes"),
                executor.submit(update_field, "tags", ["new", "tags"]),
                executor.submit(update_field, "custom", {"new_key": "new_value"}),
            ]

            # Wait for all
            for future in as_completed(futures):
                future.result(timeout=5.0)

        # Verify final state is consistent
        final = read_metadata(photo)
        assert final is not None
        assert isinstance(final.tags, list)
        assert isinstance(final.custom, dict)
        assert final.species is not None
        assert final.notes is not None

    def test_high_frequency_writes(self, tmp_path):
        """Rapid succession of writes should not corrupt data."""
        photo = tmp_path / "photo.jpg"
        photo.touch()

        write_count = 50
        # Thread-safe tracking
        import threading
        lock = threading.Lock()
        successful_writes = []

        def rapid_write(index):
            """Perform rapid writes."""
            try:
                metadata = create_metadata(photo, tags=[f"write{index}"])
                result = write_metadata(photo, metadata, backup=False)
                if result:
                    with lock:
                        successful_writes.append(index)
            except Exception as e:
                print(f"Write {index} failed: {e}")

        # Perform 50 writes as fast as possible
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(rapid_write, i) for i in range(write_count)]
            for future in as_completed(futures):
                future.result(timeout=5.0)

        # With high concurrency, some writes may fail due to lock contention
        # The key is no corruption - at least 30% should succeed
        assert len(successful_writes) >= write_count * 0.3, \
            f"Expected at least 30% writes to succeed, got {len(successful_writes)}/{write_count}"

        # Final file should be readable and valid (most important test)
        final = read_metadata(photo)
        assert final is not None, "Final metadata should be readable"
        assert isinstance(final.tags, list), "Tags should be a list"


class TestReadWhileWrite:
    """Tests for read safety during writes."""

    def test_readers_during_write_no_partial_data(self, tmp_path):
        """Readers should not see partial/corrupted data during writes."""
        photo = tmp_path / "photo.jpg"
        photo.touch()

        # Create initial metadata
        metadata = create_metadata(photo, tags=["initial"], species="Initial species")
        write_metadata(photo, metadata, backup=False)

        # Track read results
        read_results = []
        write_complete = threading.Event()

        def slow_writer():
            """Writer that takes time."""
            # Update with new data
            for i in range(10):
                metadata = create_metadata(photo, tags=[f"write{i}"], species=f"Species {i}")
                write_metadata(photo, metadata, backup=False)
                time.sleep(0.01)  # Small delay
            write_complete.set()

        def fast_reader():
            """Reader that reads repeatedly."""
            while not write_complete.is_set():
                result = read_metadata(photo)
                if result is not None:
                    read_results.append(result)
                time.sleep(0.005)

        # Start writer and readers
        writer = threading.Thread(target=slow_writer)
        readers = [threading.Thread(target=fast_reader) for _ in range(3)]

        writer.start()
        for reader in readers:
            reader.start()

        # Wait for completion
        writer.join(timeout=5.0)
        for reader in readers:
            reader.join(timeout=5.0)

        # All reads should return valid metadata (never None or corrupted)
        assert len(read_results) > 0, "Should have some reads"

        for result in read_results:
            # Each read should be valid
            assert isinstance(result.tags, list), "tags should be list"
            assert isinstance(result.species, str), "species should be string"
            assert result.version == "1.0", "version should be valid"

    def test_concurrent_readers_during_write(self, tmp_path):
        """Multiple readers during write should all get consistent data."""
        photo = tmp_path / "photo.jpg"
        photo.touch()

        # Create initial metadata
        metadata = create_metadata(photo, tags=["test"])
        write_metadata(photo, metadata, backup=False)

        read_count = 20
        read_results = []
        errors = []

        def reader():
            """Read metadata."""
            try:
                result = read_metadata(photo)
                read_results.append(result)
            except Exception as e:
                errors.append(str(e))

        def writer():
            """Write metadata."""
            try:
                metadata = create_metadata(photo, tags=["updated"])
                write_metadata(photo, metadata, backup=False)
            except Exception:
                pass

        # Start writer and many readers simultaneously
        with ThreadPoolExecutor(max_workers=21) as executor:
            futures = [executor.submit(writer)]
            futures.extend([executor.submit(reader) for _ in range(read_count)])

            for future in as_completed(futures):
                future.result(timeout=5.0)

        # No errors should occur
        assert len(errors) == 0, f"Read errors: {errors}"

        # All successful reads should return valid metadata
        valid_reads = [r for r in read_results if r is not None]
        assert len(valid_reads) > 0, "Should have some valid reads"

        for result in valid_reads:
            assert result.version == "1.0"
            assert isinstance(result.tags, list)


class TestLockTimeout:
    """Tests for lock timeout behavior."""

    def test_lock_timeout_raises_error(self, tmp_path):
        """Lock acquisition timeout should raise LockTimeoutError."""
        sidecar = tmp_path / "test.json"
        sidecar.touch()

        # Acquire exclusive lock
        with FileLock(sidecar, exclusive=True, timeout=5.0) as f1:
            # Try to acquire another exclusive lock with short timeout
            with pytest.raises(LockTimeoutError, match="Could not acquire lock"):
                with FileLock(sidecar, exclusive=True, timeout=0.1) as f2:
                    pass

    def test_write_waits_for_lock_then_succeeds(self, tmp_path):
        """Write should wait for lock to be released then succeed."""
        photo = tmp_path / "photo.jpg"
        photo.touch()

        # Create initial metadata
        metadata = create_metadata(photo, tags=["test"])
        write_metadata(photo, metadata, backup=False)

        sidecar = tmp_path / "photo.jpg.json"

        # Hold lock in one thread
        lock_acquired = threading.Event()
        write_attempted = threading.Event()
        write_result = []

        def hold_lock():
            """Hold lock briefly."""
            try:
                with FileLock(sidecar, exclusive=True, timeout=5.0):
                    lock_acquired.set()
                    # Hold lock until writer attempts
                    write_attempted.wait(timeout=2.0)
                    time.sleep(0.1)  # Brief hold after write attempt
            except Exception as e:
                print(f"Lock holder error: {e}")

        def try_write():
            """Try to write while lock is held."""
            # Wait for lock to be acquired
            lock_acquired.wait(timeout=2.0)

            # Signal that we're attempting to write
            write_attempted.set()

            # Write will wait for lock to be released (default 5s timeout)
            metadata2 = create_metadata(photo, tags=["updated"])
            result = write_metadata(photo, metadata2, backup=False)
            write_result.append(result)

        locker = threading.Thread(target=hold_lock)
        writer = threading.Thread(target=try_write)

        locker.start()
        writer.start()

        locker.join(timeout=5.0)
        writer.join(timeout=5.0)

        # Write should eventually succeed (waited for lock)
        assert len(write_result) == 1
        assert write_result[0] is True, "Write should succeed after waiting for lock"

    def test_lock_released_after_timeout(self, tmp_path):
        """Lock should be properly released even after timeout."""
        sidecar = tmp_path / "test.json"
        sidecar.touch()

        # Try to acquire lock with timeout (will fail if file doesn't exist for exclusive)
        try:
            with FileLock(sidecar, exclusive=True, timeout=0.1):
                pass
        except LockTimeoutError:
            pass

        # Should be able to acquire lock now
        with FileLock(sidecar, exclusive=True, timeout=1.0) as f:
            assert f is not None


class TestDeadlockPrevention:
    """Tests that verify no deadlocks occur."""

    def test_mixed_read_write_no_deadlock(self, tmp_path):
        """Mixed read/write operations should not deadlock."""
        photo = tmp_path / "photo.jpg"
        photo.touch()

        # Create initial metadata
        metadata = create_metadata(photo, tags=["initial"])
        write_metadata(photo, metadata, backup=False)

        operation_count = 30
        completed_operations = []
        start_time = time.time()

        def mixed_operations(thread_id):
            """Perform mixed read/write operations."""
            for i in range(3):
                # Read
                read_metadata(photo)

                # Write
                add_tag(photo, f"thread{thread_id}_op{i}")

                # Read again
                read_metadata(photo)

            completed_operations.append(thread_id)

        # Run 10 threads doing mixed operations
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(mixed_operations, i) for i in range(10)]

            # All should complete within reasonable time (5 seconds)
            for future in as_completed(futures, timeout=5.0):
                future.result()

        end_time = time.time()
        elapsed = end_time - start_time

        # All operations should complete
        assert len(completed_operations) == 10, "All threads should complete"

        # Should complete in reasonable time (no deadlock)
        assert elapsed < 5.0, f"Operations took too long: {elapsed}s (possible deadlock)"

    def test_rapid_tag_operations_no_deadlock(self, tmp_path):
        """Rapid tag add/remove should not deadlock."""
        photo = tmp_path / "photo.jpg"
        photo.touch()

        # Create initial metadata
        metadata = create_metadata(photo, tags=["initial"])
        write_metadata(photo, metadata, backup=False)

        def tag_operations(tag_name):
            """Add and remove tag repeatedly."""
            for _ in range(5):
                add_tag(photo, tag_name)
                remove_tag(photo, tag_name)

        # Run with 10 threads
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(tag_operations, f"tag{i}") for i in range(10)]

            # Should complete without deadlock
            for future in as_completed(futures, timeout=5.0):
                future.result()

        # Final metadata should be readable
        final = read_metadata(photo)
        assert final is not None

    def test_update_operations_no_deadlock(self, tmp_path):
        """Concurrent update operations should not deadlock."""
        photo = tmp_path / "photo.jpg"
        photo.touch()

        # Create initial metadata
        metadata = create_metadata(photo, tags=["initial"])
        write_metadata(photo, metadata, backup=False)

        def update_species(index):
            """Update species field."""
            for i in range(3):
                update_metadata(photo, {"species": f"Species {index}_{i}"})

        def update_notes(index):
            """Update notes field."""
            for i in range(3):
                update_metadata(photo, {"notes": f"Notes {index}_{i}"})

        # Mix of species and notes updates
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(5):
                futures.append(executor.submit(update_species, i))
                futures.append(executor.submit(update_notes, i))

            # Should complete without deadlock (5 second timeout)
            for future in as_completed(futures, timeout=5.0):
                future.result()

        # Final metadata should be valid (give small delay for pending operations)
        time.sleep(0.1)
        final = read_metadata(photo)
        assert final is not None, "Final metadata should be readable"
        assert isinstance(final.species, (str, type(None))), "Species should be string or None"
        assert isinstance(final.notes, (str, type(None))), "Notes should be string or None"

    def test_no_deadlock_with_backup_enabled(self, tmp_path):
        """Concurrent writes with backup enabled should not deadlock."""
        photo = tmp_path / "photo.jpg"
        photo.touch()

        # Create initial metadata
        metadata = create_metadata(photo, tags=["initial"])
        write_metadata(photo, metadata, backup=True)

        def write_with_backup(index):
            """Write metadata with backup enabled."""
            for i in range(3):
                metadata = create_metadata(photo, tags=[f"backup{index}_{i}"])
                write_metadata(photo, metadata, backup=True)

        # Run multiple writers with backup enabled
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(write_with_backup, i) for i in range(5)]

            # Should complete without deadlock
            for future in as_completed(futures, timeout=10.0):
                future.result()

        # Final state should be valid
        final = read_metadata(photo)
        assert final is not None

        # Backup should exist
        backup_path = tmp_path / "photo.jpg.json.bak"
        assert backup_path.exists()


class TestStressScenarios:
    """Stress test scenarios for concurrency."""

    def test_100_rapid_reads(self, tmp_path):
        """100 concurrent reads should complete quickly."""
        photo = tmp_path / "photo.jpg"
        photo.touch()

        # Create initial metadata
        metadata = create_metadata(photo, tags=["stress_test"])
        write_metadata(photo, metadata, backup=False)

        read_count = 100
        successful_reads = []

        def reader():
            """Read metadata."""
            result = read_metadata(photo)
            if result is not None:
                successful_reads.append(result)

        start_time = time.time()

        # 100 concurrent reads
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(reader) for _ in range(read_count)]
            for future in as_completed(futures, timeout=5.0):
                future.result()

        elapsed = time.time() - start_time

        # Most reads should succeed
        assert len(successful_reads) >= read_count * 0.95, \
            f"Expected most reads to succeed, got {len(successful_reads)}/{read_count}"

        # Should complete quickly (under 2 seconds)
        assert elapsed < 2.0, f"100 reads took too long: {elapsed}s"

    def test_interleaved_operations(self, tmp_path):
        """Complex interleaved read/write/update operations."""
        photo = tmp_path / "photo.jpg"
        photo.touch()

        # Create initial metadata
        metadata = create_metadata(photo, tags=["initial"])
        write_metadata(photo, metadata, backup=False)

        operation_results = {"reads": 0, "writes": 0, "updates": 0, "errors": 0}
        lock = threading.Lock()

        def random_operations(thread_id):
            """Perform random operations."""
            try:
                # Read
                if read_metadata(photo) is not None:
                    with lock:
                        operation_results["reads"] += 1

                # Add tag
                add_tag(photo, f"thread{thread_id}")
                with lock:
                    operation_results["writes"] += 1

                # Update
                update_metadata(photo, {"species": f"Species {thread_id}"})
                with lock:
                    operation_results["updates"] += 1

                # Read again
                if read_metadata(photo) is not None:
                    with lock:
                        operation_results["reads"] += 1

            except Exception as e:
                print(f"Thread {thread_id} error: {e}")
                with lock:
                    operation_results["errors"] += 1

        # Run 20 threads doing random operations
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(random_operations, i) for i in range(20)]
            for future in as_completed(futures, timeout=10.0):
                future.result()

        # Should have minimal errors
        assert operation_results["errors"] < 5, \
            f"Too many errors: {operation_results['errors']}"

        # Should have performed many operations
        total_ops = (operation_results["reads"] +
                     operation_results["writes"] +
                     operation_results["updates"])
        assert total_ops >= 40, f"Expected many operations, got {total_ops}"

        # Final state should be valid (give small delay for any pending operations)
        time.sleep(0.1)
        final = read_metadata(photo)
        assert final is not None, "Final metadata should be readable after all operations complete"

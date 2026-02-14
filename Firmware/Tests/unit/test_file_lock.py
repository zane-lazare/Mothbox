"""Tests for webui.backend.lib.file_lock module."""

import json
import multiprocessing
import threading
from unittest.mock import patch

import pytest


class TestLockTimeoutError:
    """LockTimeoutError is a plain exception with a message."""

    def test_is_exception(self):
        from webui.backend.lib.file_lock import LockTimeoutError

        with pytest.raises(LockTimeoutError, match="test"):
            raise LockTimeoutError("test")

    def test_contains_path_info(self):
        from webui.backend.lib.file_lock import LockTimeoutError

        err = LockTimeoutError("Could not acquire lock on /tmp/foo within 5s")
        assert "/tmp/foo" in str(err)


class TestPathValidation:
    """_validate_path rejects dangerous paths and resolves valid ones."""

    def test_filelock_rejects_null_byte(self, tmp_path):
        from webui.backend.lib.file_lock import FileLock

        with pytest.raises(ValueError, match="null byte"):
            FileLock(tmp_path / "data\x00.json")

    def test_mutexlock_rejects_null_byte(self, tmp_path):
        from webui.backend.lib.file_lock import MutexLock

        with pytest.raises(ValueError, match="null byte"):
            MutexLock(tmp_path / "lock\x00.lock")

    def test_filelock_resolves_path(self, tmp_path):
        from webui.backend.lib.file_lock import FileLock

        lock = FileLock(tmp_path / "subdir" / ".." / "data.json")
        assert lock.path == tmp_path / "data.json"
        assert lock.path.is_absolute()

    def test_mutexlock_resolves_path(self, tmp_path):
        from webui.backend.lib.file_lock import MutexLock

        lock = MutexLock(tmp_path / "subdir" / ".." / "resource.lock")
        assert lock.lock_path == tmp_path / "resource.lock"
        assert lock.lock_path.is_absolute()


class TestFileLock:
    """FileLock acquires .lock sidecar, then opens data file."""

    def test_creates_lock_file(self, tmp_path):
        from webui.backend.lib.file_lock import FileLock

        data_file = tmp_path / "data.json"
        data_file.write_text("{}")

        with FileLock(data_file, exclusive=True) as f:
            assert f is not None
            assert (tmp_path / "data.json.lock").exists()

    def test_returns_file_handle_for_reading(self, tmp_path):
        from webui.backend.lib.file_lock import FileLock

        data_file = tmp_path / "data.json"
        data_file.write_text('{"key": "value"}')

        with FileLock(data_file, exclusive=False) as f:
            content = f.read()
            assert '"key"' in content

    def test_returns_file_handle_for_writing(self, tmp_path):
        from webui.backend.lib.file_lock import FileLock

        data_file = tmp_path / "data.json"
        data_file.write_text("{}")

        with FileLock(data_file, exclusive=True) as f:
            f.seek(0)
            f.truncate()
            f.write('{"updated": true}')

        assert '"updated"' in data_file.read_text()

    def test_creates_new_file_if_missing_exclusive(self, tmp_path):
        from webui.backend.lib.file_lock import FileLock

        data_file = tmp_path / "new.json"
        assert not data_file.exists()

        with FileLock(data_file, exclusive=True) as f:
            f.write('{"new": true}')

        assert data_file.exists()

    def test_lock_file_closed_when_data_file_open_fails(self, tmp_path):
        """Lock file must not leak if opening the data file raises."""
        from webui.backend.lib.file_lock import FileLock

        data_file = tmp_path / "data.json"
        data_file.write_text("{}")
        # Make data file unreadable to trigger PermissionError
        data_file.chmod(0o000)

        try:
            with pytest.raises(PermissionError):  # noqa: SIM117 - inner with must be inside try
                with FileLock(data_file, exclusive=True):
                    pass  # pragma: no cover

            # Lock file should have been closed — verify by acquiring again
            with FileLock(data_file.parent / "other.json", exclusive=True):
                pass  # Ensures no fd leak prevents further locks
        finally:
            data_file.chmod(0o644)  # Restore for tmp_path cleanup

    def test_timeout_raises_lock_timeout_error(self, tmp_path):
        from webui.backend.lib.file_lock import FileLock, LockTimeoutError

        data_file = tmp_path / "data.json"
        data_file.write_text("{}")

        # Simulate lock always busy
        with (  # noqa: SIM117 - inner with must be inside pytest.raises
            patch("fcntl.flock", side_effect=BlockingIOError),
            pytest.raises(LockTimeoutError, match="data.json"),
        ):
            with FileLock(data_file, exclusive=True, timeout=0.05):
                pass  # pragma: no cover

    def test_lock_released_on_exit(self, tmp_path):
        from webui.backend.lib.file_lock import FileLock

        data_file = tmp_path / "data.json"
        data_file.write_text("{}")

        with FileLock(data_file, exclusive=True):
            pass

        # Should be able to acquire again immediately
        with FileLock(data_file, exclusive=True) as f:
            assert f is not None

    def test_shared_lock_mode(self, tmp_path):
        from webui.backend.lib.file_lock import FileLock

        data_file = tmp_path / "data.json"
        data_file.write_text('{"shared": true}')

        with FileLock(data_file, exclusive=False) as f:
            content = f.read()
            assert "shared" in content

    def test_shared_mode_raises_on_missing_file(self, tmp_path):
        """Shared (read) lock requires the data file to exist."""
        from webui.backend.lib.file_lock import FileLock

        missing = tmp_path / "nonexistent.json"
        with pytest.raises(FileNotFoundError):  # noqa: SIM117 - inner with must be inside pytest.raises
            with FileLock(missing, exclusive=False):
                pass  # pragma: no cover

    def test_default_timeout_is_five_seconds(self):
        from webui.backend.lib.file_lock import FileLock

        lock = FileLock("/tmp/test.json")
        assert lock.timeout == 5.0

    def test_cleanup_removes_lock_file(self, tmp_path):
        """cleanup=True removes the .lock sidecar after exit."""
        from webui.backend.lib.file_lock import FileLock

        data_file = tmp_path / "data.json"
        data_file.write_text("{}")
        lock_path = tmp_path / "data.json.lock"

        with FileLock(data_file, exclusive=True, cleanup=True) as f:
            assert lock_path.exists()
            f.seek(0)
            f.truncate()
            f.write('{"cleaned": true}')

        assert not lock_path.exists()
        assert data_file.read_text() == '{"cleaned": true}'

    def test_no_cleanup_by_default(self, tmp_path):
        """Lock sidecar persists by default (cleanup=False)."""
        from webui.backend.lib.file_lock import FileLock

        data_file = tmp_path / "data.json"
        data_file.write_text("{}")

        with FileLock(data_file, exclusive=True):
            pass

        assert (tmp_path / "data.json.lock").exists()

    def test_concurrent_threads_serialize_writes(self, tmp_path):
        """5 threads concurrently incrementing a JSON counter proves serialization."""
        from webui.backend.lib.file_lock import FileLock

        data_file = tmp_path / "counter.json"
        data_file.write_text('{"count": 0}')

        barrier = threading.Barrier(5)
        errors = []

        def increment():
            try:
                barrier.wait(timeout=5)
                with FileLock(data_file, exclusive=True, timeout=5.0) as f:
                    data = json.load(f)
                    data["count"] += 1
                    f.seek(0)
                    f.truncate()
                    json.dump(data, f)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=increment) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread errors: {errors}"
        result = json.loads(data_file.read_text())
        assert result["count"] == 5

    def test_concurrent_processes_serialize_writes(self, tmp_path):
        """5 processes concurrently incrementing a JSON counter proves cross-process serialization."""
        data_file = tmp_path / "counter.json"
        data_file.write_text('{"count": 0}')

        def increment(path):
            from webui.backend.lib.file_lock import FileLock

            with FileLock(path, exclusive=True, timeout=10.0) as f:
                data = json.load(f)
                data["count"] += 1
                f.seek(0)
                f.truncate()
                json.dump(data, f)

        procs = [multiprocessing.Process(target=increment, args=(data_file,)) for _ in range(5)]
        for p in procs:
            p.start()
        for p in procs:
            p.join(timeout=15)

        assert all(p.exitcode == 0 for p in procs)
        result = json.loads(data_file.read_text())
        assert result["count"] == 5

    def test_lock_file_permissions_error(self, tmp_path):
        """Lock file in unwritable directory raises PermissionError."""
        from webui.backend.lib.file_lock import FileLock

        unwritable = tmp_path / "readonly"
        unwritable.mkdir()
        unwritable.chmod(0o444)

        try:
            with pytest.raises(PermissionError):  # noqa: SIM117
                with FileLock(unwritable / "data.json", exclusive=True):
                    pass  # pragma: no cover
        finally:
            unwritable.chmod(0o755)

    def test_data_file_deleted_while_locked(self, tmp_path):
        """Deleting the data file while lock is held doesn't crash __exit__."""
        import os

        from webui.backend.lib.file_lock import FileLock

        data_file = tmp_path / "ephemeral.json"
        data_file.write_text('{"temp": true}')

        with FileLock(data_file, exclusive=True) as f:
            assert f is not None
            os.unlink(data_file)
        # __exit__ should complete without error


class TestMutexLock:
    """MutexLock is a pure guard — no data file handle."""

    def test_acquires_and_releases(self, tmp_path):
        from webui.backend.lib.file_lock import MutexLock

        lock_path = tmp_path / "resource.lock"

        with MutexLock(lock_path) as _:
            assert lock_path.exists()

    def test_timeout_raises_lock_timeout_error(self, tmp_path):
        from webui.backend.lib.file_lock import LockTimeoutError, MutexLock

        lock_path = tmp_path / "resource.lock"

        with (  # noqa: SIM117 - inner with must be inside pytest.raises
            patch("fcntl.flock", side_effect=BlockingIOError),
            pytest.raises(LockTimeoutError, match="resource.lock"),
        ):
            with MutexLock(lock_path, timeout=0.05):
                pass  # pragma: no cover

    def test_reentrant_after_release(self, tmp_path):
        from webui.backend.lib.file_lock import MutexLock

        lock_path = tmp_path / "resource.lock"

        with MutexLock(lock_path):
            pass

        with MutexLock(lock_path):
            pass  # Should not raise

    def test_default_timeout_is_five_seconds(self):
        from webui.backend.lib.file_lock import MutexLock

        lock = MutexLock("/tmp/test.lock")
        assert lock.timeout == 5.0

    def test_concurrent_threads_serialize_access(self, tmp_path):
        """5 threads appending to a shared list under MutexLock."""
        from webui.backend.lib.file_lock import MutexLock

        lock_path = tmp_path / "shared.lock"
        results = []
        barrier = threading.Barrier(5)
        errors = []

        def append_item(item):
            try:
                barrier.wait(timeout=5)
                with MutexLock(lock_path, timeout=5.0):
                    results.append(item)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=append_item, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread errors: {errors}"
        assert sorted(results) == [0, 1, 2, 3, 4]

    def test_cleanup_removes_lock_file(self, tmp_path):
        """cleanup=True removes the lock file after exit."""
        from webui.backend.lib.file_lock import MutexLock

        lock_path = tmp_path / "temp.lock"

        with MutexLock(lock_path, cleanup=True):
            assert lock_path.exists()

        assert not lock_path.exists()

    def test_no_cleanup_by_default(self, tmp_path):
        """Lock file persists by default (cleanup=False)."""
        from webui.backend.lib.file_lock import MutexLock

        lock_path = tmp_path / "persist.lock"

        with MutexLock(lock_path):
            pass

        assert lock_path.exists()

    def test_lock_file_permissions_error(self, tmp_path):
        """Lock file in unwritable directory raises PermissionError."""
        from webui.backend.lib.file_lock import MutexLock

        unwritable = tmp_path / "readonly"
        unwritable.mkdir()
        unwritable.chmod(0o444)

        try:
            with pytest.raises(PermissionError):  # noqa: SIM117
                with MutexLock(unwritable / "resource.lock"):
                    pass  # pragma: no cover
        finally:
            unwritable.chmod(0o755)

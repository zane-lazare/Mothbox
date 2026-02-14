"""Tests for webui.backend.lib.file_lock module."""

import time
from pathlib import Path
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

    def test_timeout_raises_lock_timeout_error(self, tmp_path):
        from webui.backend.lib.file_lock import FileLock, LockTimeoutError

        data_file = tmp_path / "data.json"
        data_file.write_text("{}")

        # Simulate lock always busy
        with patch("fcntl.flock", side_effect=BlockingIOError):
            with pytest.raises(LockTimeoutError, match="data.json"):
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

    def test_default_timeout_is_five_seconds(self):
        from webui.backend.lib.file_lock import FileLock

        lock = FileLock("/tmp/test.json")
        assert lock.timeout == 5.0


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

        with patch("fcntl.flock", side_effect=BlockingIOError):
            with pytest.raises(LockTimeoutError, match="resource.lock"):
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

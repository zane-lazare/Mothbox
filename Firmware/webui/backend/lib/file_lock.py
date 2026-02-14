"""Shared file locking utilities with timeout support.

Provides two lock types:

- ``FileLock``: Acquires a ``.lock`` sidecar then opens the data file.
  Returns a file handle. Use for read-modify-write patterns.

- ``MutexLock``: Acquires an exclusive lock file as a pure guard.
  Use when you need mutual exclusion but don't need a file handle.

Both use non-blocking ``fcntl.flock`` with exponential backoff so callers
never block indefinitely.

Lock file cleanup:
    Lock files (``.lock`` sidecars) are harmless if left on disk — they are
    zero-byte and re-used on the next acquisition.  Callers that want tidy
    directories can pass ``cleanup=True`` or call
    ``Path(lock_path).unlink(missing_ok=True)`` after the ``with`` block.

    WARNING: ``cleanup=True`` has a theoretical TOCTOU race where Process A
    releases → Process B acquires → Process A unlinks B's lock file.
    Negligible for unique lock paths (e.g., per-file thumbnail locks).

Example::

    from webui.backend.lib.file_lock import FileLock, MutexLock

    # Read-modify-write with timeout
    with FileLock("data.json", exclusive=True, timeout=5.0) as f:
        data = json.load(f)
        f.seek(0)
        f.truncate()
        json.dump(data, f)

    # Pure mutex guard
    with MutexLock("resource.lock", timeout=5.0):
        do_exclusive_work()

Timeout guidelines:
    Default 5.0s — suitable for most operations (config reads, metadata updates,
    preset saves, stats flushes).

    10.0s — use for operations that compete with slow I/O: GPS multi-value
    writes, thumbnail generation, scheduler state activation, boot-time
    schedule reconciliation.
"""

from __future__ import annotations

import fcntl
import logging
import os
import time
from pathlib import Path
from types import TracebackType
from typing import IO

logger = logging.getLogger(__name__)


def _validate_path(path: Path) -> Path:
    """Resolve and validate a lock/data path.

    Rejects null bytes (which bypass OS path checks) and paths that
    cannot be resolved to an absolute location.
    """
    if "\0" in str(path):
        raise ValueError("Path contains null byte")
    try:
        return path.resolve()
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Invalid path: {path}") from e


class LockTimeoutError(Exception):
    """Raised when file lock acquisition times out."""


class FileLock:
    """File lock context manager using fcntl with separate lock file.

    Uses a separate .lock file to acquire the lock BEFORE opening the data file.
    This prevents race conditions where threads open the data file before
    acquiring the lock and read stale content.

    Exclusive mode (default) creates the data file if missing.
    Shared mode requires the file to exist (raises ``FileNotFoundError`` if missing).

    Args:
        path: Path to data file to lock
        exclusive: True for exclusive lock (LOCK_EX), False for shared (LOCK_SH)
        timeout: Maximum seconds to wait for lock acquisition
    """

    def __init__(
        self,
        path: str | Path,
        exclusive: bool = True,
        timeout: float = 5.0,
        cleanup: bool = False,
    ) -> None:
        self.path = _validate_path(Path(path))
        self.lock_path = Path(str(self.path) + ".lock")
        self.exclusive = exclusive
        self.timeout = timeout
        self.cleanup = cleanup
        self.lock_file = None
        self.data_file = None

    def __enter__(self) -> IO[str]:
        self.lock_file = open(self.lock_path, "w")

        lock_type = fcntl.LOCK_EX if self.exclusive else fcntl.LOCK_SH
        start_time = time.time()
        wait_time = 0.001

        while True:
            try:
                fcntl.flock(self.lock_file.fileno(), lock_type | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                elapsed = time.time() - start_time
                if elapsed >= self.timeout:
                    self.lock_file.close()
                    raise LockTimeoutError(
                        f"Could not acquire lock on {self.path} within {self.timeout}s"
                    ) from None
                time.sleep(wait_time)
                wait_time = min(wait_time * 2, 0.25)

        try:
            if self.exclusive:
                fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o644)
                self.data_file = os.fdopen(fd, "r+")
            else:
                self.data_file = open(self.path)
        except Exception:
            try:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
            except OSError as e:
                logger.debug("Failed to unlock during error cleanup: %s", e)
            self.lock_file.close()
            raise
        return self.data_file

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        # ValueError covers "I/O operation on closed file" if handle was already closed
        if self.data_file:
            try:
                self.data_file.close()
            except (OSError, ValueError) as e:
                logger.debug("Failed to close data file: %s", e)
        if self.lock_file:
            try:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
            except (OSError, ValueError) as e:
                logger.debug("Failed to unlock: %s", e)
            try:
                self.lock_file.close()
            except (OSError, ValueError) as e:
                logger.debug("Failed to close lock file: %s", e)
        if self.cleanup:
            try:
                self.lock_path.unlink(missing_ok=True)
            except OSError as e:
                logger.debug("Failed to clean up lock file: %s", e)


class MutexLock:
    """Pure mutex guard using fcntl with a lock file.

    Unlike FileLock, does not open or manage a data file. Use when you
    need mutual exclusion around a block of code.

    Args:
        lock_path: Path to the lock file (created if missing)
        timeout: Maximum seconds to wait for lock acquisition
    """

    def __init__(self, lock_path: str | Path, timeout: float = 5.0, cleanup: bool = False) -> None:
        self.lock_path = _validate_path(Path(lock_path))
        self.timeout = timeout
        self.cleanup = cleanup
        self.lock_file = None

    def __enter__(self) -> MutexLock:
        self.lock_file = open(self.lock_path, "a")

        start_time = time.time()
        wait_time = 0.001

        while True:
            try:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                elapsed = time.time() - start_time
                if elapsed >= self.timeout:
                    self.lock_file.close()
                    raise LockTimeoutError(
                        f"Could not acquire lock on {self.lock_path} within {self.timeout}s"
                    ) from None
                time.sleep(wait_time)
                wait_time = min(wait_time * 2, 0.25)

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        # ValueError covers "I/O operation on closed file" if handle was already closed
        if self.lock_file:
            try:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
            except (OSError, ValueError) as e:
                logger.debug("Failed to unlock: %s", e)
            try:
                self.lock_file.close()
            except (OSError, ValueError) as e:
                logger.debug("Failed to close lock file: %s", e)
        if self.cleanup:
            try:
                self.lock_path.unlink(missing_ok=True)
            except OSError as e:
                logger.debug("Failed to clean up lock file: %s", e)

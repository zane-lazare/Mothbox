"""Shared file locking utilities with timeout support.

Provides two lock types:

- ``FileLock``: Acquires a ``.lock`` sidecar then opens the data file.
  Returns a file handle. Use for read-modify-write patterns.

- ``MutexLock``: Acquires an exclusive lock file as a pure guard.
  Use when you need mutual exclusion but don't need a file handle.

Both use non-blocking ``fcntl.flock`` with exponential backoff so callers
never block indefinitely.

Example::

    from webui.backend.lib.file_lock import FileLock, MutexLock

    # Read-modify-write with timeout
    with FileLock("data.json", exclusive=True, timeout=5.0) as f:
        data = json.load(f)
        f.seek(0); f.truncate()
        json.dump(data, f)

    # Pure mutex guard
    with MutexLock("resource.lock", timeout=5.0):
        do_exclusive_work()
"""

import contextlib
import fcntl
import time
from pathlib import Path


class LockTimeoutError(Exception):
    """Raised when file lock acquisition times out."""


class FileLock:
    """File lock context manager using fcntl with separate lock file.

    Uses a separate .lock file to acquire the lock BEFORE opening the data file.
    This prevents race conditions where threads open the data file before
    acquiring the lock and read stale content.

    Args:
        path: Path to data file to lock
        exclusive: True for exclusive lock (LOCK_EX), False for shared (LOCK_SH)
        timeout: Maximum seconds to wait for lock acquisition
    """

    def __init__(self, path, exclusive=True, timeout=5.0):
        self.path = Path(path)
        self.lock_path = Path(str(self.path) + ".lock")
        self.exclusive = exclusive
        self.timeout = timeout
        self.lock_file = None
        self.data_file = None

    def __enter__(self):
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
                wait_time = min(wait_time * 2, 0.1)

        mode = ("r+" if self.path.exists() else "w+") if self.exclusive else "r"
        self.data_file = open(self.path, mode)
        return self.data_file

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.data_file:
            with contextlib.suppress(Exception):
                self.data_file.close()
        if self.lock_file:
            with contextlib.suppress(Exception):
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
            with contextlib.suppress(Exception):
                self.lock_file.close()


class MutexLock:
    """Pure mutex guard using fcntl with a lock file.

    Unlike FileLock, does not open or manage a data file. Use when you
    need mutual exclusion around a block of code.

    Args:
        lock_path: Path to the lock file (created if missing)
        timeout: Maximum seconds to wait for lock acquisition
    """

    def __init__(self, lock_path, timeout=5.0):
        self.lock_path = Path(lock_path)
        self.timeout = timeout
        self.lock_file = None

    def __enter__(self):
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
                wait_time = min(wait_time * 2, 0.1)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.lock_file:
            with contextlib.suppress(Exception):
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
            with contextlib.suppress(Exception):
                self.lock_file.close()

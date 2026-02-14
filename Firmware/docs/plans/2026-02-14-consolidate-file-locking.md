# Consolidate File Locking Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extract file locking into a shared module with timeout support, eliminating 8 raw `fcntl.flock()` sites and fixing the GPS.py infinite-block bug (#377).

**Architecture:** New `webui/backend/lib/file_lock.py` module with `FileLock` (data file + lock) and `MutexLock` (pure guard). Migrate all raw fcntl sites, update all existing consumers, remove locking code from `sidecar_metadata.py`.

**Tech Stack:** Python `fcntl`, `pathlib.Path`, context managers

---

### Task 1: Create `file_lock.py` with tests (TDD)

**Files:**
- Create: `webui/backend/lib/file_lock.py`
- Create: `Tests/unit/test_file_lock.py`

**Step 1: Write failing tests for `LockTimeoutError`, `FileLock`, and `MutexLock`**

```python
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
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest Tests/unit/test_file_lock.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'webui.backend.lib.file_lock'`

**Step 3: Implement `file_lock.py`**

Move `FileLock`, `LockTimeoutError` from `sidecar_metadata.py` lines 106-538, add `MutexLock`:

```python
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
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest Tests/unit/test_file_lock.py -v`
Expected: All 12 tests PASS

**Step 5: Commit**

```bash
git add webui/backend/lib/file_lock.py Tests/unit/test_file_lock.py
git commit -m "feat: add shared file_lock module with FileLock and MutexLock (#377)"
```

---

### Task 2: Remove `FileLock` and `LockTimeoutError` from `sidecar_metadata.py`

**Files:**
- Modify: `webui/backend/lib/sidecar_metadata.py` — remove class definitions, import from `file_lock`
- Modify: `webui/backend/lib/schedule_storage.py:78` — update import
- Modify: `webui/backend/lib/deployment_sidecar.py:83` — update import
- Modify: `webui/backend/lib/active_state.py:17` — update import
- Modify: `webui/backend/services/scheduler_service.py:83` — update import
- Modify: `webui/cli/refresh_schedule.py:54` — update import
- Modify: `Tests/unit/test_scheduler_concurrent.py:539,582` — update imports

**Step 1: Update `sidecar_metadata.py`**

- Remove `LockTimeoutError` class (line 106-107)
- Remove `FileLock` class (lines 464-538)
- Add `from webui.backend.lib.file_lock import FileLock, LockTimeoutError` at top
- Remove `import fcntl` and `import time` if no longer used directly

**Step 2: Update all 5 production import sites**

Each file: change `from webui.backend.lib.sidecar_metadata import FileLock` (and/or `LockTimeoutError`) to `from webui.backend.lib.file_lock import FileLock` (and/or `LockTimeoutError`).

Files:
- `webui/backend/lib/schedule_storage.py:78`
- `webui/backend/lib/deployment_sidecar.py:83`
- `webui/backend/lib/active_state.py:17`
- `webui/backend/services/scheduler_service.py:83`
- `webui/cli/refresh_schedule.py:54`

**Step 3: Update test import**

- `Tests/unit/test_scheduler_concurrent.py:539,582` — change both `from webui.backend.lib.sidecar_metadata import LockTimeoutError` to `from webui.backend.lib.file_lock import LockTimeoutError`

**Step 4: Run existing tests to verify nothing broke**

Run: `python3 -m pytest Tests/unit/test_file_lock.py Tests/unit/test_sidecar_metadata_lib.py Tests/unit/test_sidecar_metadata_errors.py Tests/unit/test_scheduler_concurrent.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add webui/backend/lib/sidecar_metadata.py webui/backend/lib/schedule_storage.py \
  webui/backend/lib/deployment_sidecar.py webui/backend/lib/active_state.py \
  webui/backend/services/scheduler_service.py webui/cli/refresh_schedule.py \
  Tests/unit/test_scheduler_concurrent.py
git commit -m "refactor: extract FileLock from sidecar_metadata to file_lock module (#377)"
```

---

### Task 3: Migrate `preset_manager.py` and `export_preset_manager.py`

**Files:**
- Modify: `webui/backend/preset_manager.py:12,519-527`
- Modify: `webui/backend/export_preset_manager.py:15,291-299`
- Test: `Tests/unit/test_preset_manager.py` (existing tests verify locking)

**Step 1: Migrate `preset_manager.py`**

Replace `import fcntl` with `from webui.backend.lib.file_lock import FileLock`.

Replace the raw fcntl block (lines 519-527):
```python
            with open(preset_path, "w") as f:
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    json.dump(preset_data, f, indent=2)
                    f.flush()
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

With:
```python
            with FileLock(preset_path, exclusive=True) as f:
                json.dump(preset_data, f, indent=2)
                f.flush()
```

Note: `FileLock` opens the file in `w+` mode when it doesn't exist (or `r+` when it does). For preset saves, the file is being written fresh. The `FileLock` opens with `r+` if exists or `w+` if not — for a full overwrite, seek(0)+truncate after open, or the simpler approach: since presets are small JSON files being fully rewritten, truncate first:
```python
            with FileLock(preset_path, exclusive=True) as f:
                f.seek(0)
                f.truncate()
                json.dump(preset_data, f, indent=2)
                f.flush()
```

**Step 2: Migrate `export_preset_manager.py`**

Same pattern — replace `import fcntl` with `from webui.backend.lib.file_lock import FileLock`, replace raw fcntl block (lines 291-299) with `FileLock`.

**Step 3: Run existing tests**

Run: `python3 -m pytest Tests/unit/test_preset_manager.py Tests/unit/test_export_preset_manager.py -v`
Expected: All PASS (existing tests mock `fcntl.flock` — may need minor updates if they mock the import path)

**Step 4: If preset tests fail due to mock path**

The existing tests in `test_preset_manager.py` (lines 222-343) mock `fcntl.flock` directly. Since `FileLock` internally calls `fcntl.flock`, these mocks should still work. If not, update mock targets to `webui.backend.lib.file_lock.fcntl.flock`.

**Step 5: Commit**

```bash
git add webui/backend/preset_manager.py webui/backend/export_preset_manager.py \
  Tests/unit/test_preset_manager.py Tests/unit/test_export_preset_manager.py
git commit -m "refactor: migrate preset managers to FileLock (#377)"
```

---

### Task 4: Migrate `metadata_cache.py`

**Files:**
- Modify: `webui/backend/services/metadata_cache.py:18,344-392`

**Step 1: Migrate shared read (line 344-350)**

Replace:
```python
                with open(cache_file) as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                    try:
                        data = json.load(f)
                        entry = CacheEntry.from_dict(data)
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

With:
```python
                with FileLock(cache_file, exclusive=False) as f:
                    data = json.load(f)
                    entry = CacheEntry.from_dict(data)
```

**Step 2: Migrate exclusive write (line 386-392)**

Replace:
```python
                with open(temp_file, "w") as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    try:
                        json.dump(entry.to_dict(), f, indent=2)
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

With:
```python
                with FileLock(temp_file, exclusive=True) as f:
                    json.dump(entry.to_dict(), f, indent=2)
```

**Step 3: Update imports** — replace `import fcntl` with `from webui.backend.lib.file_lock import FileLock`

**Step 4: Run tests**

Run: `python3 -m pytest Tests/unit/test_metadata_cache.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add webui/backend/services/metadata_cache.py
git commit -m "refactor: migrate metadata_cache to FileLock (#377)"
```

---

### Task 5: Migrate `thumbnail_cache.py` (2 sites — MutexLock)

**Files:**
- Modify: `webui/backend/services/thumbnail_cache.py:26,168-209,498-548`

**Step 1: Migrate thumbnail generation lock (lines 168-209)**

Replace the raw fcntl mutex pattern:
```python
        with open(lock_path, "a") as lock_file:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                # ... generation logic ...
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                lock_path.unlink(missing_ok=True)
```

With:
```python
        with MutexLock(lock_path, timeout=10.0):
            # Check again if file exists (another process may have generated it)
            if cache_path.exists():
                return cache_path
            # ... generation logic (same as before, without the lock boilerplate) ...

        # Clean up lock file after release
        lock_path.unlink(missing_ok=True)
```

Note: Move the `lock_path.unlink()` outside the `MutexLock` block since it should happen after lock release.

**Step 2: Migrate stats flush lock (lines 498-548)**

Same pattern — replace raw fcntl with `MutexLock(lock_path, timeout=5.0)`.

**Step 3: Update imports** — replace `import fcntl` with `from webui.backend.lib.file_lock import MutexLock`

**Step 4: Run tests**

Run: `python3 -m pytest Tests/unit/test_thumbnail_cache.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add webui/backend/services/thumbnail_cache.py
git commit -m "refactor: migrate thumbnail_cache to MutexLock (#377)"
```

---

### Task 6: Migrate `services/__init__.py` (MutexLock)

**Files:**
- Modify: `webui/backend/services/__init__.py:68,82-85`

**Step 1: Migrate cache purge lock**

Replace:
```python
        import fcntl
        # ...
        lock_file = cache_dir / ".purge.lock"
        try:
            with open(lock_file, "w") as lock:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                # ... purge logic ...
```

With:
```python
        from webui.backend.lib.file_lock import MutexLock
        # ...
        lock_file = cache_dir / ".purge.lock"
        with MutexLock(lock_file, timeout=5.0):
            # ... purge logic (same) ...
```

**Step 2: Run a quick smoke test**

Run: `python3 -m pytest Tests/unit/test_sidecar_service.py -v -k "test_get" --maxfail=3`
Expected: PASS (sidecar service init uses this code path)

**Step 3: Commit**

```bash
git add webui/backend/services/__init__.py
git commit -m "refactor: migrate services/__init__ to MutexLock (#377)"
```

---

### Task 7: Migrate `routes/gps.py`

**Files:**
- Modify: `webui/backend/routes/gps.py:3,554-592`

**Step 1: Migrate GPS config write**

Replace `import fcntl` with `from webui.backend.lib.file_lock import FileLock`.

Replace the raw fcntl block (lines 555-592):
```python
    with open(CONTROLS_FILE, "r+") as f:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            # ... read-modify-write logic ...
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

With:
```python
    with FileLock(CONTROLS_FILE, exclusive=True, timeout=10.0) as f:
        # ... read-modify-write logic (same) ...
```

**Step 2: Run tests**

Run: `python3 -m pytest Tests/unit/test_gps_routes.py -v --maxfail=3`
Expected: PASS

**Step 3: Commit**

```bash
git add webui/backend/routes/gps.py
git commit -m "refactor: migrate routes/gps.py to FileLock (#377)"
```

---

### Task 8: Migrate `GPS.py` (both 4.x and 5.x) — fixes infinite-block bug

**Files:**
- Modify: `4.x/GPS.py:7,132-173`
- Modify: `5.x/GPS.py:7,132-173`

**Step 1: Migrate `5.x/GPS.py`**

Replace `import fcntl` with `from webui.backend.lib.file_lock import FileLock, LockTimeoutError`.

Replace the raw fcntl block (lines 132-173):
```python
    with open(filepath, "r+") as f:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            lines = f.readlines()
            # ... read-modify-write ...
            f.seek(0)
            f.truncate()
            f.writelines(updated_lines)
            f.flush()
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

With:
```python
    try:
        with FileLock(filepath, exclusive=True, timeout=10.0) as f:
            lines = f.readlines()
            # ... read-modify-write (same logic) ...
            f.seek(0)
            f.truncate()
            f.writelines(updated_lines)
            f.flush()
    except LockTimeoutError:
        logger.error(
            "Could not acquire lock on %s within 10s — skipping GPS config update",
            filepath,
        )
```

**Step 2: Apply identical change to `4.x/GPS.py`**

Same migration — files are identical in the locking section.

**Step 3: Run GPS tests**

Run: `python3 -m pytest Tests/unit/test_gps_routes.py -v --maxfail=3`
Expected: PASS

**Step 4: Commit**

```bash
git add 4.x/GPS.py 5.x/GPS.py
git commit -m "fix: GPS.py no longer blocks indefinitely on locked config file (#377)"
```

---

### Task 9: Verify no raw fcntl remains, run full test suite

**Step 1: Verify no raw `fcntl.flock` in production code**

Run: `rg 'fcntl\.flock' --type py --glob '!Tests/**' --glob '!docs/**'`
Expected: Only `webui/backend/lib/file_lock.py` should appear (the implementation itself).

**Step 2: Run full affected test suite**

Run: `python3 -m pytest Tests/unit/test_file_lock.py Tests/unit/test_sidecar_metadata_lib.py Tests/unit/test_sidecar_metadata_errors.py Tests/unit/test_preset_manager.py Tests/unit/test_export_preset_manager.py Tests/unit/test_thumbnail_cache.py Tests/unit/test_metadata_cache.py Tests/unit/test_gps_routes.py Tests/unit/test_scheduler_concurrent.py Tests/unit/test_sidecar_service.py -v`
Expected: All PASS

**Step 3: Run linter**

Run: `ruff check webui/backend/lib/file_lock.py webui/backend/lib/sidecar_metadata.py webui/backend/preset_manager.py webui/backend/export_preset_manager.py webui/backend/services/thumbnail_cache.py webui/backend/services/metadata_cache.py webui/backend/services/__init__.py webui/backend/routes/gps.py 4.x/GPS.py 5.x/GPS.py`
Expected: No errors

**Step 4: Commit any final fixes**

If lint or test issues found, fix and commit:
```bash
git commit -m "fix: address lint/test issues from file locking migration (#377)"
```

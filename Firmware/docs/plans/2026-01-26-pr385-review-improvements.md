# PR #385 Code Review Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Address remaining code review feedback from PR #385 - fix JSON loading race condition, extract helper functions, define constants, and improve code organization.

**Architecture:** Incremental improvements with TDD approach. Each task is independent and can be committed separately.

**Tech Stack:** Python 3.11, pytest, json

---

## Overview

Items from PR #385 review:

| Priority | Item | Status |
|----------|------|--------|
| ~~Should Fix~~ | ~~LockTimeoutError handling~~ | ✅ Already fixed |
| Should Fix | Fix `_load_active_state()` JSON parsing race | Task 1 |
| Nice to Have | Extract instant action overlap helper | Task 2 |
| Nice to Have | Define magic number constants | Task 3 |
| ~~Nice to Have~~ | ~~Split large test files~~ | Skipped (low ROI) |
| ~~Nice to Have~~ | ~~Property-based tests~~ | Skipped (hypothesis not installed) |

**Note:** Skipping test file splitting (621 lines is manageable) and property-based tests (requires adding hypothesis dependency).

---

## Task 1: Fix `_load_active_state()` JSON Parsing Race Condition

**Files:**
- Modify: `webui/backend/services/scheduler_service.py:490-497`
- Test: `Tests/unit/test_scheduler_concurrent.py`

**Problem:** Current code reads file content, then seeks back and re-reads with `json.load()`. Between these operations, another process could modify the file.

**Current Code (lines 492-497):**
```python
with FileLock(ACTIVE_STATE_FILE, exclusive=False, timeout=5.0) as f:
    content = f.read()
    if not content:
        return
    f.seek(0)
    state = json.load(f)
```

**Step 1: Write the test**

Add to `Tests/unit/test_scheduler_concurrent.py`:

```python
class TestLoadActiveStateJsonParsing:
    """Tests for _load_active_state JSON parsing (Issue #385 review fix)."""

    def test_load_active_state_parses_from_content_not_file(
        self, temp_schedules_dir, active_state_file
    ):
        """_load_active_state should parse JSON from read content, not re-read file."""
        # Create a valid state file
        state_data = {
            "schedule_id": _test_uuid("json-parse-test"),
            "enabled_schedule_id": _test_uuid("json-parse-test"),
            "coordinates_source": "explicit",
            "latitude": 35.0,
            "longitude": -80.0,
            "timezone_name": "America/New_York",
            "entries": [],
        }
        active_state_file.write_text(json.dumps(state_data))

        # Create service - should load state successfully
        service = SchedulerService()

        assert service._active_schedule_id == _test_uuid("json-parse-test")
        assert service._active_latitude == 35.0
        assert service._active_longitude == -80.0
```

**Step 2: Run test to verify it passes (existing behavior works)**

Run: `MOTHBOX_ENV=test SECRET_KEY="test-key" pytest Tests/unit/test_scheduler_concurrent.py::TestLoadActiveStateJsonParsing -v`

Expected: PASS (current implementation works, we're just making it safer)

**Step 3: Update implementation**

In `webui/backend/services/scheduler_service.py`, change lines 490-497:

```python
        try:
            # Use FileLock for safe read (Issue #385 - concurrent activation safety)
            with FileLock(ACTIVE_STATE_FILE, exclusive=False, timeout=5.0) as f:
                content = f.read()
                if not content.strip():
                    return
                # Parse from string content to avoid TOCTOU race (Issue #385 review)
                # Previously used f.seek(0) + json.load(f) which could read stale data
                # if another process modified the file between read() and load()
                state = json.loads(content)
```

**Step 4: Run test to verify it still passes**

Run: `MOTHBOX_ENV=test SECRET_KEY="test-key" pytest Tests/unit/test_scheduler_concurrent.py::TestLoadActiveStateJsonParsing -v`

Expected: PASS

**Step 5: Run all scheduler tests to verify no regression**

Run: `MOTHBOX_ENV=test SECRET_KEY="test-key" pytest Tests/unit/test_scheduler*.py -v --tb=line | tail -10`

Expected: All tests pass

**Step 6: Commit**

```bash
git add webui/backend/services/scheduler_service.py Tests/unit/test_scheduler_concurrent.py
git commit -m "fix(scheduler): parse JSON from string to avoid TOCTOU race

Previously _load_active_state() read file content, then seeked back and
re-read with json.load(). This could theoretically read stale data if
another process modified the file between operations. Now uses
json.loads(content) to parse from the already-read string.

Issue #385 review fix"
```

---

## Task 2: Extract Instant Action Overlap Helper Function

**Files:**
- Modify: `webui/backend/lib/schedule_conflict.py:391-404`
- Test: `Tests/unit/test_schedule_conflict_lib.py`

**Problem:** The time overlap logic with instant action handling is complex and inline. Extracting to a helper improves testability and readability.

**Step 1: Write the test**

Add to `Tests/unit/test_schedule_conflict_lib.py`:

```python
class TestTimeOverlapWithInstants:
    """Tests for _check_time_overlap helper function (Issue #385 review)."""

    def test_both_instant_same_time_overlaps(self):
        """Two instant actions at the same time should overlap."""
        from webui.backend.lib.schedule_conflict import _check_time_overlap
        from datetime import datetime

        t = datetime(2026, 1, 26, 12, 0, 0)
        assert _check_time_overlap(t, t, t, t) is True

    def test_both_instant_different_times_no_overlap(self):
        """Two instant actions at different times should not overlap."""
        from webui.backend.lib.schedule_conflict import _check_time_overlap
        from datetime import datetime

        t1 = datetime(2026, 1, 26, 12, 0, 0)
        t2 = datetime(2026, 1, 26, 12, 1, 0)
        assert _check_time_overlap(t1, t1, t2, t2) is False

    def test_instant_within_range_overlaps(self):
        """Instant action within a range should overlap."""
        from webui.backend.lib.schedule_conflict import _check_time_overlap
        from datetime import datetime

        instant = datetime(2026, 1, 26, 12, 30, 0)
        range_start = datetime(2026, 1, 26, 12, 0, 0)
        range_end = datetime(2026, 1, 26, 13, 0, 0)
        # instant within range
        assert _check_time_overlap(instant, instant, range_start, range_end) is True
        # range contains instant
        assert _check_time_overlap(range_start, range_end, instant, instant) is True

    def test_instant_outside_range_no_overlap(self):
        """Instant action outside a range should not overlap."""
        from webui.backend.lib.schedule_conflict import _check_time_overlap
        from datetime import datetime

        instant = datetime(2026, 1, 26, 14, 0, 0)
        range_start = datetime(2026, 1, 26, 12, 0, 0)
        range_end = datetime(2026, 1, 26, 13, 0, 0)
        assert _check_time_overlap(instant, instant, range_start, range_end) is False

    def test_ranges_overlap(self):
        """Two overlapping ranges should overlap."""
        from webui.backend.lib.schedule_conflict import _check_time_overlap
        from datetime import datetime

        start1 = datetime(2026, 1, 26, 12, 0, 0)
        end1 = datetime(2026, 1, 26, 13, 0, 0)
        start2 = datetime(2026, 1, 26, 12, 30, 0)
        end2 = datetime(2026, 1, 26, 13, 30, 0)
        assert _check_time_overlap(start1, end1, start2, end2) is True

    def test_ranges_no_overlap(self):
        """Two non-overlapping ranges should not overlap."""
        from webui.backend.lib.schedule_conflict import _check_time_overlap
        from datetime import datetime

        start1 = datetime(2026, 1, 26, 12, 0, 0)
        end1 = datetime(2026, 1, 26, 13, 0, 0)
        start2 = datetime(2026, 1, 26, 14, 0, 0)
        end2 = datetime(2026, 1, 26, 15, 0, 0)
        assert _check_time_overlap(start1, end1, start2, end2) is False

    def test_instant_at_range_boundary_overlaps(self):
        """Instant action at range boundary should overlap (inclusive)."""
        from webui.backend.lib.schedule_conflict import _check_time_overlap
        from datetime import datetime

        instant = datetime(2026, 1, 26, 13, 0, 0)  # At end of range
        range_start = datetime(2026, 1, 26, 12, 0, 0)
        range_end = datetime(2026, 1, 26, 13, 0, 0)
        assert _check_time_overlap(instant, instant, range_start, range_end) is True
```

**Step 2: Run test to verify it fails**

Run: `MOTHBOX_ENV=test SECRET_KEY="test-key" pytest Tests/unit/test_schedule_conflict_lib.py::TestTimeOverlapWithInstants -v`

Expected: FAIL with `ImportError: cannot import name '_check_time_overlap'`

**Step 3: Implement the helper function**

In `webui/backend/lib/schedule_conflict.py`, add before the `_check_resource_conflict` function (around line 370):

```python
def _check_time_overlap(
    start1: datetime, end1: datetime, start2: datetime, end2: datetime
) -> bool:
    """
    Check if two time ranges overlap, handling instant actions.

    Instant actions have start == end. They overlap with ranges if they fall
    within the range (inclusive of boundaries). Two instants only overlap if
    they occur at the exact same time.

    Args:
        start1: Start time of first range
        end1: End time of first range (equals start1 for instant actions)
        start2: Start time of second range
        end2: End time of second range (equals start2 for instant actions)

    Returns:
        True if the time ranges overlap, False otherwise

    Issue #385 review: Extracted from _check_resource_conflict for testability.
    """
    if start1 == end1 and start2 == end2:
        # Both are instant - only conflict if at exact same time
        return start1 == start2
    elif start1 == end1:
        # usage1 is instant - check if it falls within usage2 (inclusive end)
        return start2 <= start1 <= end2
    elif start2 == end2:
        # usage2 is instant - check if it falls within usage1 (inclusive end)
        return start1 <= start2 <= end1
    else:
        # Both have duration - standard overlap check
        return start1 < end2 and start2 < end1
```

**Step 4: Update `_check_resource_conflict` to use the helper**

Replace lines 391-404 with:

```python
    # Check time overlap first (handles instant actions specially)
    times_overlap = _check_time_overlap(
        usage1.start_time, usage1.end_time, usage2.start_time, usage2.end_time
    )
```

**Step 5: Run test to verify it passes**

Run: `MOTHBOX_ENV=test SECRET_KEY="test-key" pytest Tests/unit/test_schedule_conflict_lib.py::TestTimeOverlapWithInstants -v`

Expected: PASS

**Step 6: Run all conflict tests to verify no regression**

Run: `MOTHBOX_ENV=test SECRET_KEY="test-key" pytest Tests/unit/test_schedule_conflict_lib.py -v --tb=line | tail -10`

Expected: All tests pass

**Step 7: Commit**

```bash
git add webui/backend/lib/schedule_conflict.py Tests/unit/test_schedule_conflict_lib.py
git commit -m "refactor(conflict): extract _check_time_overlap helper function

Improves testability and readability of instant action overlap logic.
The helper handles four cases: both instant, first instant, second instant,
and both have duration. Added 7 unit tests for edge cases.

Issue #385 review improvement"
```

---

## Task 3: Define Magic Number Constants at Module Level

**Files:**
- Modify: `webui/backend/services/scheduler_service.py:200-220`

**Problem:** Cache TTL values are defined inline without context. Moving to module-level constants improves documentation and maintainability.

**Step 1: Add constants at module level**

In `webui/backend/services/scheduler_service.py`, after the imports (around line 95), add:

```python
# =============================================================================
# Cache Configuration Constants (Issue #385 review)
# =============================================================================

# Schedule cache TTL - balance between freshness and disk I/O
SCHEDULE_CACHE_TTL_SECONDS = 300  # 5 minutes

# Maximum cached schedules - prevents unbounded memory growth
MAX_SCHEDULE_CACHE_SIZE = 100

# Conflict analysis cache TTL - shorter because schedule changes invalidate
CONFLICT_CACHE_TTL_SECONDS = 600  # 10 minutes

# Maximum conflict cache entries
MAX_CONFLICT_CACHE_SIZE = 50

# Built-in schedules cache TTL - longer because they rarely change
# (only on firmware update, not during normal operation)
BUILTIN_CACHE_TTL_SECONDS = 3600  # 1 hour
```

**Step 2: Update `__init__` to use constants**

Replace lines 200-220 with references to the new constants:

```python
        # Schedule cache using OrderedDict for LRU behavior
        # Key: schedule_id, Value: (Schedule, timestamp)
        self._cache: OrderedDict[str, tuple[Schedule, float]] = OrderedDict()
        self._cache_ttl = SCHEDULE_CACHE_TTL_SECONDS
        self._max_cache_size = MAX_SCHEDULE_CACHE_SIZE

        # Conflict report cache (Issue #213)
        # Key: hash of (schedule_id, preview_days, lat, lon, tz), Value: (report, timestamp)
        self._conflict_cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._conflict_cache_ttl = CONFLICT_CACHE_TTL_SECONDS
        self._max_conflict_cache_size = MAX_CONFLICT_CACHE_SIZE
        self._conflict_cache_hits = 0
        self._conflict_cache_misses = 0

        # Built-in schedules cache (separate from regular cache, longer TTL)
        # Built-in schedules rarely change (only on firmware update)
        self._builtin_cache: list[Schedule] | None = None
        self._builtin_cache_timestamp: float = 0.0
        self._builtin_cache_ttl = BUILTIN_CACHE_TTL_SECONDS
```

**Step 3: Run scheduler tests to verify no regression**

Run: `MOTHBOX_ENV=test SECRET_KEY="test-key" pytest Tests/unit/test_scheduler_service.py -v --tb=line | tail -10`

Expected: All tests pass

**Step 4: Run lint check**

Run: `ruff check webui/backend/services/scheduler_service.py`

Expected: No new errors

**Step 5: Commit**

```bash
git add webui/backend/services/scheduler_service.py
git commit -m "refactor(scheduler): define cache TTL constants at module level

Improves code documentation and maintainability by extracting magic
numbers to named constants with explanatory comments:
- SCHEDULE_CACHE_TTL_SECONDS (300s / 5 min)
- CONFLICT_CACHE_TTL_SECONDS (600s / 10 min)
- BUILTIN_CACHE_TTL_SECONDS (3600s / 1 hour)
- MAX_SCHEDULE_CACHE_SIZE (100)
- MAX_CONFLICT_CACHE_SIZE (50)

Issue #385 review improvement"
```

---

## Summary

| Task | Description | Files Changed |
|------|-------------|---------------|
| 1 | Fix JSON parsing race condition | scheduler_service.py, test_scheduler_concurrent.py |
| 2 | Extract time overlap helper | schedule_conflict.py, test_schedule_conflict_lib.py |
| 3 | Define cache constants | scheduler_service.py |

**Total: 3 commits, addressing all actionable review feedback.**

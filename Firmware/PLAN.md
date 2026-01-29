# PR #385 Review Implementation Plan

## Overview

This plan addresses the remaining issues from the PR #385 code reviews. The previous commit (e4630587) already addressed:
- ✅ FileLock for active_state.json read/write
- ✅ Activation lock for TOCTOU race prevention
- ✅ UTC timezone standardization in datetime calls
- ✅ Cron command security documentation
- ✅ Concurrent activation tests (8 tests)

---

## Before Merge (Must Fix)

### Issue 1: GPS Coordinate Validation Gap

**Problem:** Coordinates from GPS fallback (controls.txt) bypass `validate_coordinates()`. Only explicitly provided coordinates are validated.

**Location:** `webui/backend/routes/scheduler_ui.py:1090-1099`

**Current Code:**
```python
if lat_provided and lon_provided:  # Only validates explicit coordinates!
    valid, coord_error = validate_coordinates(latitude, longitude)
```

**Fix:** Validate ALL coordinates regardless of source:
```python
# Always validate coordinates (explicit, GPS, or timezone fallback)
valid, coord_error = validate_coordinates(latitude, longitude)
if not valid:
    return jsonify({"error": f"Invalid coordinates: {coord_error}"}), 400
```

**Files to modify:**
- `webui/backend/routes/scheduler_ui.py` - Lines 1090-1099

---

### Issue 2: FileLock Timeout Silent Failure

**Problem:** When `_save_active_state()` catches `LockTimeoutError`, it logs but doesn't re-raise. This means:
1. Cron entries are applied
2. In-memory state is updated
3. Disk state FAILS to save
4. Activation appears successful, but state is lost on restart

**Location:** `webui/backend/services/scheduler_service.py:469-470`

**Current Code:**
```python
except LockTimeoutError as e:
    logger.error(f"Failed to acquire lock for active state: {e}")
    # Does NOT re-raise - caller doesn't know save failed!
```

**Fix:** Re-raise the exception so `activate_schedule()` can rollback cron:
```python
except LockTimeoutError as e:
    logger.error(f"Failed to acquire lock for active state: {e}")
    raise  # Let caller handle rollback
```

**Files to modify:**
- `webui/backend/services/scheduler_service.py` - Line 470

---

### Issue 3: Defense-in-Depth Validation in activate_schedule()

**Problem:** `activate_schedule()` relies entirely on caller validation. If called programmatically (e.g., from tests or future code), invalid data could be stored.

**Location:** `webui/backend/services/scheduler_service.py:983-1022`

**Fix:** Add parameter validation inside `activate_schedule()`:
```python
def activate_schedule(self, schedule_id: str, ...):
    # Validate coordinates (defense-in-depth)
    if latitude is not None and (latitude < -90 or latitude > 90):
        raise ScheduleActivationError(f"Invalid latitude: {latitude}")
    if longitude is not None and (longitude < -180 or longitude > 180):
        raise ScheduleActivationError(f"Invalid longitude: {longitude}")

    # Validate timezone (defense-in-depth)
    try:
        import pytz
        pytz.timezone(timezone_name)
    except Exception:
        raise ScheduleActivationError(f"Invalid timezone: {timezone_name}")
```

**Files to modify:**
- `webui/backend/services/scheduler_service.py` - After line 1023

---

### Issue 4: Enabled Field Handling Clarification

**Problem:** The `enabled` field is in `ALLOWED_UPDATE_FIELDS` whitelist, but it's actually managed via `active_state.json`. This creates potential confusion.

**Analysis:** Looking at the code:
- `scheduler_ui.py:700-717` already pops `enabled` from json_data before calling `update_schedule()`
- Service layer derives `enabled` from `active_state.json`, not schedule JSON

**Decision:** This is already handled correctly. The whitelist allows it for backward compatibility, but the service layer ignores it. No changes needed, but could add a comment.

**Files to modify:** None (optional comment in `schedule_storage.py`)

---

## Post-Merge Improvements

### Issue 5: HTML Sanitization Optimization

**Problem:** Iterative regex loop is O(n²) worst case for deeply nested tags.

**Location:** `webui/frontend/src/components/scheduler/ScheduleEditor/ScheduleEditor.jsx:47-54`

**Current Code:**
```javascript
let previousLength;
do {
  previousLength = message.length;
  message = message.replace(/<[^>]*>?/g, '');
} while (message.length < previousLength);
```

**Fix Option A (Quick):** Single-pass regex (sufficient for server error messages):
```javascript
const sanitized = message.replace(/<[^>]*>/g, '');
```

**Fix Option B (Robust):** Use DOMPurify library:
```javascript
import DOMPurify from 'dompurify';
const sanitized = DOMPurify.sanitize(message, { ALLOWED_TAGS: [] });
```

**Priority:** Low - current code works, just inefficient

---

### Issue 6: Additional E2E Tests

**Missing Coverage:**
1. Coordinate source persistence across service restart
2. Enabled schedule enforcement (only one at a time)
3. Idempotent activation (re-activating same schedule succeeds)

**Location:** `webui/frontend/e2e/scheduler-*.spec.js`

---

### Issue 7: MAX_CRON_ENTRIES Threshold Tests

**Problem:** No integration tests verify behavior at entry limit boundaries.

**Tests to add:**
1. Schedule with 9,900 entries activates successfully
2. Schedule exceeding 10,000 entries fails with helpful error
3. Warning at 75% threshold (7,500 entries)

**Location:** `Tests/unit/test_cron_bridge.py` or new integration test

---

### Issue 8: Lock Ordering Stress Test

**Problem:** No concurrent stress test to verify lock ordering doesn't cause deadlocks.

**Test to add:**
```python
def test_concurrent_operations_no_deadlock():
    """Spawn 10 threads doing random activate/deactivate/update operations."""
    # 10 threads, 100 operations each, 10-second timeout
    # Pass if all threads complete without deadlock
```

**Location:** `Tests/unit/test_scheduler_concurrent.py`

---

## Implementation Order

### Before Merge:
1. **Issue 2** - FileLock timeout re-raise (critical - silent data loss)
2. **Issue 1** - GPS coordinate validation (security/reliability)
3. **Issue 3** - Defense-in-depth validation in activate_schedule()

### Post-Merge (separate PRs):
4. Issue 5 - HTML sanitization
5. Issue 6 - E2E tests
6. Issue 7 - Cron entry limit tests
7. Issue 8 - Lock stress test

---

## Verification

After implementing before-merge fixes:

1. Run existing tests:
```bash
python3 -m pytest Tests/unit/test_scheduler*.py -v
```

2. Test GPS coordinate validation:
- Activate with invalid GPS in controls.txt (lat > 90)
- Verify error is returned, not silent failure

3. Test FileLock timeout rollback:
- Mock FileLock to timeout
- Verify cron entries are rolled back
- Verify error is propagated to API response

4. Test defense-in-depth validation:
- Call `scheduler_service.activate_schedule()` directly with invalid lat/lon
- Verify `ScheduleActivationError` is raised

---

## Files Summary

| File | Before Merge | Post-Merge |
|------|--------------|------------|
| `scheduler_service.py` | Issues 2, 3 | - |
| `scheduler_ui.py` | Issue 1 | - |
| `ScheduleEditor.jsx` | - | Issue 5 |
| `scheduler-*.spec.js` | - | Issue 6 |
| `test_cron_bridge.py` | - | Issue 7 |
| `test_scheduler_concurrent.py` | - | Issue 8 |

# PR #385 Security Fixes and Remaining Improvements

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 3 security vulnerabilities flagged by GitHub Advanced Security and implement remaining PR review improvements.

**Architecture:** Security fixes first (critical), then UX improvements. Each task is independent with TDD approach.

**Tech Stack:** Python 3.11, Flask, pytest, React

---

## Overview

### Security Issues (from github-advanced-security[bot])

| # | Issue | Severity | File:Line |
|---|-------|----------|-----------|
| 1 | Reflected XSS via error message | Medium | scheduler_ui.py:1124 |
| 2 | Clear-text logging of sensitive info (GPS) | Low | scheduler_ui.py:1087 |
| 3 | Information exposure via exception | Low | scheduler_ui.py:747 |

### PR Review Improvements

| # | Item | Priority |
|---|------|----------|
| 4 | Document 10k cron limit in UI | Medium |
| 5 | Standardize error codes backend/frontend | Low |

---

## Task 1: Fix Reflected XSS in Error Responses

**Files:**
- Modify: `webui/backend/routes/scheduler_ui.py:69-97`
- Test: `Tests/unit/test_scheduler_ui_security.py` (new file)

**Problem:** The `_validate_location_params` helper returns error dicts that may contain user-provided values (like invalid timezone names). When passed to `jsonify()`, these could be exploited for XSS if the frontend renders them unsafely.

**Current vulnerable pattern (line 1122-1124):**
```python
error, status = _validate_location_params(latitude, longitude, timezone_name)
if error:
    return jsonify(error), status
```

The `timezone_name` comes from user input and could contain `<script>` tags.

**Step 1: Create test file**

Create `Tests/unit/test_scheduler_ui_security.py`:

```python
"""Security tests for scheduler_ui routes (Issue #385 security review)."""

import pytest


class TestErrorMessageSanitization:
    """Tests for XSS prevention in error responses."""

    def test_validate_location_params_sanitizes_timezone_error(self):
        """Error messages should not contain raw user input."""
        from webui.backend.routes.scheduler_ui import _validate_location_params

        # Malicious timezone input
        malicious_tz = "<script>alert('xss')</script>"
        error, status = _validate_location_params(0.0, 0.0, malicious_tz)

        assert error is not None
        assert status == 400
        # Error message should NOT contain the raw script tag
        error_msg = error.get("error", "")
        assert "<script>" not in error_msg
        assert "alert" not in error_msg

    def test_validate_location_params_sanitizes_coordinate_error(self):
        """Coordinate error messages should be safe."""
        from webui.backend.routes.scheduler_ui import _validate_location_params

        # Invalid coordinates
        error, status = _validate_location_params(999.0, 999.0, "UTC")

        assert error is not None
        assert status == 400
        # Error should contain generic message, not raw values
        error_msg = error.get("error", "")
        assert "Invalid coordinates" in error_msg

    def test_sanitize_error_message_strips_html(self):
        """_sanitize_error_message should strip HTML tags."""
        from webui.backend.routes.scheduler_ui import _sanitize_error_message

        malicious = "<script>alert('xss')</script>Normal text<b>bold</b>"
        sanitized = _sanitize_error_message(malicious)

        assert "<script>" not in sanitized
        assert "<b>" not in sanitized
        assert "Normal text" in sanitized
        assert "bold" in sanitized

    def test_sanitize_error_message_truncates_long_messages(self):
        """Long error messages should be truncated."""
        from webui.backend.routes.scheduler_ui import _sanitize_error_message

        long_msg = "x" * 500
        sanitized = _sanitize_error_message(long_msg)

        assert len(sanitized) <= 200

    def test_sanitize_error_message_handles_none(self):
        """None input should return generic message."""
        from webui.backend.routes.scheduler_ui import _sanitize_error_message

        assert _sanitize_error_message(None) == "An error occurred"

    def test_sanitize_error_message_handles_empty(self):
        """Empty input should return generic message."""
        from webui.backend.routes.scheduler_ui import _sanitize_error_message

        assert _sanitize_error_message("") == "An error occurred"
```

**Step 2: Run tests to verify they fail**

Run: `MOTHBOX_ENV=test SECRET_KEY="test-key" pytest Tests/unit/test_scheduler_ui_security.py -v`

Expected: FAIL with `ImportError: cannot import name '_sanitize_error_message'`

**Step 3: Add sanitization helper function**

In `webui/backend/routes/scheduler_ui.py`, add after the imports (around line 67):

```python
import re


def _sanitize_error_message(message: str | None, max_length: int = 200) -> str:
    """
    Sanitize error message for safe display to users.

    Prevents XSS by stripping HTML tags and truncating long messages.
    This is defense-in-depth - Flask's jsonify escapes by default,
    but we strip tags to prevent any frontend rendering issues.

    Args:
        message: Raw error message (may contain user input)
        max_length: Maximum length before truncation

    Returns:
        Sanitized error message safe for display

    Issue #385 security fix: Reflected XSS prevention
    """
    if not message:
        return "An error occurred"

    # Convert to string if needed
    msg = str(message)

    # Strip HTML tags iteratively (handles nested/malformed tags)
    prev_len = -1
    while len(msg) != prev_len:
        prev_len = len(msg)
        msg = re.sub(r"<[^>]*>", "", msg)
        msg = re.sub(r"<[^>]*$", "", msg)  # Incomplete tags

    # Truncate if too long
    if len(msg) > max_length:
        msg = msg[:max_length - 3] + "..."

    return msg.strip() or "An error occurred"
```

**Step 4: Update `_validate_location_params` to sanitize errors**

Update the helper function (around line 95):

```python
def _validate_location_params(
    latitude: float | None,
    longitude: float | None,
    timezone_name: str | None,
) -> tuple[dict | None, int | None]:
    """Validate location parameters for schedule operations.

    Consolidates coordinate and timezone validation logic (Issue #385 review fix).
    Error messages are sanitized to prevent XSS (Issue #385 security fix).

    Args:
        latitude: Latitude value to validate
        longitude: Longitude value to validate
        timezone_name: Optional timezone name to validate

    Returns:
        Tuple of (error_dict, status_code) if validation fails, or (None, None) if valid.
    """
    valid, coord_error = validate_coordinates(latitude, longitude)
    if not valid:
        # Sanitize error - coord_error may contain user input
        safe_error = _sanitize_error_message(coord_error)
        return {"error": f"Invalid coordinates: {safe_error}"}, 400

    if timezone_name:
        valid, tz_error = validate_timezone(timezone_name)
        if not valid:
            # Sanitize error - timezone_name is user input
            safe_error = _sanitize_error_message(tz_error)
            return {"error": f"Invalid timezone: {safe_error}"}, 400

    return None, None
```

**Step 5: Run tests to verify they pass**

Run: `MOTHBOX_ENV=test SECRET_KEY="test-key" pytest Tests/unit/test_scheduler_ui_security.py -v`

Expected: PASS

**Step 6: Run linter**

Run: `ruff check webui/backend/routes/scheduler_ui.py`

Expected: No errors

**Step 7: Commit**

```bash
git add webui/backend/routes/scheduler_ui.py Tests/unit/test_scheduler_ui_security.py
git commit -m "fix(security): sanitize error messages to prevent XSS

Add _sanitize_error_message helper that strips HTML tags and truncates
long messages. Applied to _validate_location_params error responses.

This is defense-in-depth - Flask's jsonify already escapes, but we
strip tags to prevent any frontend rendering issues with user input.

Fixes GitHub security alert #298: Reflected server-side XSS"
```

---

## Task 2: Remove Sensitive GPS Coordinates from Logs

**Files:**
- Modify: `webui/backend/routes/scheduler_ui.py:1087,1092-1095,1100-1103`

**Problem:** GPS coordinates are logged at INFO level, which could expose user location in log files.

**Current code (line 1087):**
```python
logger.info(f"Using device GPS: {latitude}, {longitude}")
```

**Step 1: Update logging to DEBUG level and redact coordinates**

Replace lines 1087, 1092-1095, and 1100-1103:

```python
# Line 1087 - change from:
logger.info(f"Using device GPS: {latitude}, {longitude}")
# To:
logger.debug(f"Using device GPS coordinates (redacted for privacy)")

# Lines 1092-1095 - change from:
logger.info(
    f"GPS values invalid, using timezone '{fallback_timezone}': "
    f"{latitude}, {longitude}"
)
# To:
logger.debug(
    f"GPS values invalid, using timezone fallback: {fallback_timezone}"
)

# Lines 1100-1103 - change from:
logger.info(
    f"No GPS available, using timezone '{fallback_timezone}': "
    f"{latitude}, {longitude}"
)
# To:
logger.debug(
    f"No GPS available, using timezone fallback: {fallback_timezone}"
)
```

**Step 2: Run linter**

Run: `ruff check webui/backend/routes/scheduler_ui.py`

Expected: No errors

**Step 3: Commit**

```bash
git add webui/backend/routes/scheduler_ui.py
git commit -m "fix(security): remove GPS coordinates from log messages

Change coordinate logging from INFO to DEBUG level and remove actual
coordinate values. GPS location is sensitive PII that shouldn't appear
in production logs.

Fixes GitHub security alert #296: Clear-text logging of sensitive info"
```

---

## Task 3: Prevent Exception Details Leaking to Users

**Files:**
- Modify: `webui/backend/routes/scheduler_ui.py:747`

**Problem:** `str(e)` from ValueError is returned directly to users, potentially exposing internal implementation details.

**Current code (line 747):**
```python
return jsonify({"error": str(e)}), 400
```

**Step 1: Sanitize exception message**

Replace line 747:

```python
# Sanitize exception message before returning to user
safe_error = _sanitize_error_message(str(e))
return jsonify({"error": safe_error}), 400
```

**Step 2: Add test**

Add to `Tests/unit/test_scheduler_ui_security.py`:

```python
class TestExceptionSanitization:
    """Tests for exception message sanitization."""

    def test_update_schedule_enabled_error_sanitized(self, client, mocker):
        """Exception details should be sanitized in error responses."""
        from uuid import uuid4

        # Mock service to raise ValueError with sensitive info
        mock_service = mocker.patch(
            "webui.backend.routes.scheduler_ui.get_scheduler_service"
        )
        mock_instance = mock_service.return_value
        mock_instance.get_schedule.return_value = mocker.MagicMock()
        mock_instance.set_enabled_schedule.side_effect = ValueError(
            "Internal path: /etc/secrets/api_key.txt not found"
        )

        schedule_id = str(uuid4())
        response = client.patch(
            f"/api/schedules/{schedule_id}",
            json={"enabled": True},
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 400
        data = response.get_json()
        # Should not contain full internal path
        assert "/etc/secrets" not in data.get("error", "")
```

**Step 3: Run test**

Run: `MOTHBOX_ENV=test SECRET_KEY="test-key" pytest Tests/unit/test_scheduler_ui_security.py::TestExceptionSanitization -v`

Expected: PASS

**Step 4: Commit**

```bash
git add webui/backend/routes/scheduler_ui.py Tests/unit/test_scheduler_ui_security.py
git commit -m "fix(security): sanitize exception messages in error responses

Apply _sanitize_error_message to ValueError exceptions before returning
to users. Prevents internal paths or implementation details from leaking.

Fixes GitHub security alert #297: Information exposure through exception"
```

---

## Task 4: Add Cron Entry Limit Warning to UI

**Files:**
- Create: `webui/frontend/src/components/scheduler/CronLimitWarning.jsx`
- Modify: `webui/frontend/src/components/scheduler/ScheduleEditor/ScheduleEditor.jsx`

**Problem:** Users can create schedules that exceed the 10,000 cron entry limit, but there's no warning until activation fails.

**Step 1: Create warning component**

Create `webui/frontend/src/components/scheduler/CronLimitWarning.jsx`:

```jsx
import PropTypes from 'prop-types'
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline'

/**
 * Warning banner shown when schedule approaches cron entry limit.
 *
 * The system has a 10,000 cron entry limit. This component warns users
 * when their schedule configuration is approaching or exceeding this limit.
 *
 * Issue #385 review: Document 10k cron limit in user-facing UI
 */

/** Maximum cron entries supported by the system */
const MAX_CRON_ENTRIES = 10000

/** Threshold percentage for showing warning (75%) */
const WARNING_THRESHOLD = 0.75

/**
 * CronLimitWarning component
 *
 * @param {Object} props
 * @param {number} props.estimatedEntries - Estimated number of cron entries
 * @returns {JSX.Element|null}
 */
function CronLimitWarning({ estimatedEntries }) {
  if (!estimatedEntries || estimatedEntries < MAX_CRON_ENTRIES * WARNING_THRESHOLD) {
    return null
  }

  const isOverLimit = estimatedEntries > MAX_CRON_ENTRIES
  const percentage = Math.round((estimatedEntries / MAX_CRON_ENTRIES) * 100)

  return (
    <div
      role="alert"
      className={`flex items-start gap-2 p-3 rounded-lg text-sm ${
        isOverLimit
          ? 'bg-red-50 border border-red-200 text-red-800'
          : 'bg-amber-50 border border-amber-200 text-amber-800'
      }`}
    >
      <ExclamationTriangleIcon className="h-5 w-5 flex-shrink-0 mt-0.5" />
      <div>
        <p className="font-medium">
          {isOverLimit ? 'Schedule exceeds system limit' : 'Approaching system limit'}
        </p>
        <p className="mt-1">
          {isOverLimit ? (
            <>
              This schedule would generate ~{estimatedEntries.toLocaleString()} cron entries,
              exceeding the {MAX_CRON_ENTRIES.toLocaleString()} entry limit.
              Reduce frequency or duration.
            </>
          ) : (
            <>
              This schedule generates ~{estimatedEntries.toLocaleString()} cron entries
              ({percentage}% of {MAX_CRON_ENTRIES.toLocaleString()} limit).
              Consider reducing frequency for complex schedules.
            </>
          )}
        </p>
      </div>
    </div>
  )
}

CronLimitWarning.propTypes = {
  estimatedEntries: PropTypes.number,
}

export default CronLimitWarning
```

**Step 2: Add to ScheduleEditor**

In `webui/frontend/src/components/scheduler/ScheduleEditor/ScheduleEditor.jsx`:

Add import at top:
```jsx
import CronLimitWarning from '../CronLimitWarning'
```

Add in the editor JSX, after the ConflictPanel (around line 660):
```jsx
{/* Cron entry limit warning (Issue #385) */}
{conflictReport?.estimated_entries && (
  <CronLimitWarning estimatedEntries={conflictReport.estimated_entries} />
)}
```

**Step 3: Verify component renders**

Manual test: Open schedule editor with a complex schedule and verify warning appears.

**Step 4: Commit**

```bash
git add webui/frontend/src/components/scheduler/CronLimitWarning.jsx \
        webui/frontend/src/components/scheduler/ScheduleEditor/ScheduleEditor.jsx
git commit -m "feat(ui): add cron entry limit warning in schedule editor

Show warning when schedule approaches 75% of 10,000 entry limit.
Shows error state when exceeding limit. Helps users understand why
complex schedules may fail to activate.

Issue #385 review: Document 10k cron limit in user-facing UI"
```

---

## Task 5: Standardize Backend Error Codes

**Files:**
- Modify: `webui/backend/routes/scheduler_ui.py`
- Modify: `webui/frontend/src/components/scheduler/ScheduleEditor/ScheduleEditor.jsx`

**Problem:** Backend returns raw error messages, but frontend has `KNOWN_ERROR_CODES` that expect structured codes.

**Step 1: Define error codes in backend**

Add to `webui/backend/routes/scheduler_ui.py` after imports:

```python
# Standardized error codes for frontend handling (Issue #385 review)
ERROR_CODES = {
    "VALIDATION_ERROR": "VALIDATION_ERROR",
    "NOT_FOUND": "NOT_FOUND",
    "CONFLICT_ERROR": "CONFLICT_ERROR",
    "ACTIVATION_ERROR": "ACTIVATION_ERROR",
    "SERVER_ERROR": "SERVER_ERROR",
}
```

**Step 2: Update error responses to include codes**

Example pattern - update key error responses:

```python
# Instead of:
return jsonify({"error": "Schedule not found"}), 404

# Use:
return jsonify({
    "error": "Schedule not found",
    "code": ERROR_CODES["NOT_FOUND"]
}), 404
```

Apply to:
- Line 404: Schedule not found
- Line 747: Validation error
- Line 1124: Coordinate/timezone validation error

**Step 3: Update frontend to use codes**

In `ScheduleEditor.jsx`, update error handling:

```jsx
const KNOWN_ERROR_CODES = {
  NETWORK_ERROR: 'Unable to save. Please check your connection.',
  VALIDATION_ERROR: 'Please fix the errors above.',
  NOT_FOUND: 'Schedule not found. It may have been deleted.',
  CONFLICT_ERROR: 'Schedule has conflicts that must be resolved.',
  ACTIVATION_ERROR: 'Failed to activate schedule.',
  SERVER_ERROR: 'Server error. Please try again later.',
};

// In error handler:
const errorCode = error?.response?.data?.code;
const message = KNOWN_ERROR_CODES[errorCode] || error.message;
```

**Step 4: Commit**

```bash
git add webui/backend/routes/scheduler_ui.py \
        webui/frontend/src/components/scheduler/ScheduleEditor/ScheduleEditor.jsx
git commit -m "feat(api): standardize error codes between backend and frontend

Add ERROR_CODES dict to backend, include 'code' field in error responses.
Update frontend KNOWN_ERROR_CODES to match. Provides better UX with
user-friendly error messages.

Issue #385 review: Standardize error codes backend/frontend"
```

---

## Summary

| Task | Type | Description | Priority |
|------|------|-------------|----------|
| 1 | Security | XSS prevention in error messages | High |
| 2 | Security | Remove GPS from logs | Medium |
| 3 | Security | Sanitize exception details | Medium |
| 4 | UX | Cron limit warning component | Medium |
| 5 | DX | Standardize error codes | Low |

**Total: 5 commits addressing all security alerts and actionable review feedback.**

---

## Verification Commands

After all tasks complete:

```bash
# Run security tests
MOTHBOX_ENV=test SECRET_KEY="test-key" pytest Tests/unit/test_scheduler_ui_security.py -v

# Run all scheduler tests
MOTHBOX_ENV=test SECRET_KEY="test-key" pytest Tests/unit/test_scheduler*.py -v --tb=line | tail -20

# Run linter
ruff check webui/backend/routes/scheduler_ui.py

# Run frontend linter
cd webui/frontend && npm run lint
```

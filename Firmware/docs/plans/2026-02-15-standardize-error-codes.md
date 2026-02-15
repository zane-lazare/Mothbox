# Standardize Error Codes Across Backend/Frontend (#388) — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a shared error codes module for backend and frontend, migrate scheduler_ui.py as first adopter, and update frontend error handling to use the shared module.

**Architecture:** New `webui/backend/lib/error_codes.py` defines error code constants, a message sanitizer (HTML stripping + path redaction), and an `error_response()` helper that returns standardized `{"error": "...", "code": "..."}` JSON. Frontend gets `webui/frontend/src/utils/errorCodes.js` mirroring the codes with user-friendly messages. `scheduler_ui.py` migrates from inline constants to the shared module.

**Tech Stack:** Python/Flask (backend), JavaScript/React (frontend), pytest (testing)

**Important context:**
- `security_utils.py` already has a `sanitize_error_message(error, generic_message)` that logs exceptions and returns generic messages. The new module's sanitizer is different — it sanitizes string content (strips HTML, redacts paths). Named `sanitize_message()` to avoid confusion.
- Some scheduler error responses include extra fields (`"message"`, `"conflict": True`). The helper supports `**kwargs` for extra fields.
- No existing tests assert on the `"code"` field, so migration is backward-compatible.
- `_validate_location_params()` in scheduler_ui.py calls `_sanitize_error_message()` directly — must update to import from shared module.

---

### Task 1: Create shared error codes module with tests (TDD)

**Files:**
- Create: `webui/backend/lib/error_codes.py`
- Create: `Tests/unit/test_error_codes.py`

**Step 1: Write the failing tests**

Create `Tests/unit/test_error_codes.py`:

```python
"""Tests for shared error codes module."""

import json

import pytest


class TestErrorCodes:
    """Test error code constants."""

    def test_all_codes_are_strings(self):
        from webui.backend.lib.error_codes import ERROR_CODES

        for key, value in ERROR_CODES.items():
            assert isinstance(value, str), f"{key} should be a string"
            assert value == key, f"Value should match key: {key}"

    def test_required_codes_exist(self):
        from webui.backend.lib.error_codes import ERROR_CODES

        required = [
            "VALIDATION_ERROR",
            "NOT_FOUND",
            "CONFLICT_ERROR",
            "ACTIVATION_ERROR",
            "RATE_LIMIT_ERROR",
            "HARDWARE_ERROR",
            "STORAGE_ERROR",
            "PERMISSION_ERROR",
            "SERVER_ERROR",
        ]
        for code in required:
            assert code in ERROR_CODES, f"Missing required code: {code}"

    def test_codes_importable_as_module_attributes(self):
        from webui.backend.lib.error_codes import (
            ACTIVATION_ERROR,
            CONFLICT_ERROR,
            HARDWARE_ERROR,
            NOT_FOUND,
            PERMISSION_ERROR,
            RATE_LIMIT_ERROR,
            SERVER_ERROR,
            STORAGE_ERROR,
            VALIDATION_ERROR,
        )

        assert VALIDATION_ERROR == "VALIDATION_ERROR"
        assert NOT_FOUND == "NOT_FOUND"
        assert CONFLICT_ERROR == "CONFLICT_ERROR"
        assert ACTIVATION_ERROR == "ACTIVATION_ERROR"
        assert RATE_LIMIT_ERROR == "RATE_LIMIT_ERROR"
        assert HARDWARE_ERROR == "HARDWARE_ERROR"
        assert STORAGE_ERROR == "STORAGE_ERROR"
        assert PERMISSION_ERROR == "PERMISSION_ERROR"
        assert SERVER_ERROR == "SERVER_ERROR"


class TestSanitizeMessage:
    """Test message sanitization for safe display."""

    def test_strips_html_tags(self):
        from webui.backend.lib.error_codes import sanitize_message

        assert sanitize_message("<b>bold</b> text") == "bold text"

    def test_strips_script_tags(self):
        from webui.backend.lib.error_codes import sanitize_message

        result = sanitize_message("<script>alert('xss')</script>hello")
        assert "<script>" not in result
        assert "hello" in result

    def test_strips_incomplete_tags(self):
        from webui.backend.lib.error_codes import sanitize_message

        result = sanitize_message("text <script without closing")
        assert "<" not in result

    def test_redacts_internal_paths(self):
        from webui.backend.lib.error_codes import sanitize_message

        result = sanitize_message("Error reading /etc/secrets/key.pem")
        assert "/etc/secrets" not in result
        assert "[path]" in result

    def test_redacts_var_paths(self):
        from webui.backend.lib.error_codes import sanitize_message

        result = sanitize_message("File not found: /var/lib/mothbox/data.json")
        assert "/var/lib" not in result

    def test_redacts_home_paths(self):
        from webui.backend.lib.error_codes import sanitize_message

        result = sanitize_message("Error in /home/pi/Desktop/Mothbox/config")
        assert "/home/pi" not in result

    def test_truncates_long_messages(self):
        from webui.backend.lib.error_codes import sanitize_message

        long_msg = "x" * 300
        result = sanitize_message(long_msg)
        assert len(result) <= 200
        assert result.endswith("...")

    def test_custom_max_length(self):
        from webui.backend.lib.error_codes import sanitize_message

        result = sanitize_message("x" * 100, max_length=50)
        assert len(result) <= 50

    def test_none_returns_default(self):
        from webui.backend.lib.error_codes import sanitize_message

        assert sanitize_message(None) == "An error occurred"

    def test_empty_string_returns_default(self):
        from webui.backend.lib.error_codes import sanitize_message

        assert sanitize_message("") == "An error occurred"

    def test_normal_message_unchanged(self):
        from webui.backend.lib.error_codes import sanitize_message

        assert sanitize_message("Schedule not found") == "Schedule not found"


class TestErrorResponse:
    """Test error_response helper produces correct JSON format."""

    @pytest.fixture(autouse=True)
    def _flask_app(self):
        """Create minimal Flask app for jsonify context."""
        from flask import Flask

        app = Flask(__name__)
        with app.app_context():
            yield app

    def test_basic_error_response(self):
        from webui.backend.lib.error_codes import VALIDATION_ERROR, error_response

        response, status = error_response(VALIDATION_ERROR, "Bad input", 400)
        data = json.loads(response.get_data(as_text=True))
        assert data["error"] == "Bad input"
        assert data["code"] == "VALIDATION_ERROR"
        assert status == 400

    def test_default_status_is_400(self):
        from webui.backend.lib.error_codes import VALIDATION_ERROR, error_response

        _, status = error_response(VALIDATION_ERROR, "Bad input")
        assert status == 400

    def test_server_error_status(self):
        from webui.backend.lib.error_codes import SERVER_ERROR, error_response

        _, status = error_response(SERVER_ERROR, "Internal error", 500)
        assert status == 500

    def test_not_found_status(self):
        from webui.backend.lib.error_codes import NOT_FOUND, error_response

        response, status = error_response(NOT_FOUND, "Schedule not found", 404)
        data = json.loads(response.get_data(as_text=True))
        assert data["code"] == "NOT_FOUND"
        assert status == 404

    def test_extra_fields_included(self):
        from webui.backend.lib.error_codes import CONFLICT_ERROR, error_response

        response, status = error_response(
            CONFLICT_ERROR, "Conflict", 409, conflict=True
        )
        data = json.loads(response.get_data(as_text=True))
        assert data["conflict"] is True
        assert data["code"] == "CONFLICT_ERROR"

    def test_message_is_sanitized(self):
        from webui.backend.lib.error_codes import VALIDATION_ERROR, error_response

        response, _ = error_response(
            VALIDATION_ERROR, "<script>xss</script>Bad input", 400
        )
        data = json.loads(response.get_data(as_text=True))
        assert "<script>" not in data["error"]

    def test_path_redacted_in_response(self):
        from webui.backend.lib.error_codes import SERVER_ERROR, error_response

        response, _ = error_response(
            SERVER_ERROR, "Error reading /etc/mothbox/config.txt", 500
        )
        data = json.loads(response.get_data(as_text=True))
        assert "/etc/mothbox" not in data["error"]
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest Tests/unit/test_error_codes.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'webui.backend.lib.error_codes'`

**Step 3: Write minimal implementation**

Create `webui/backend/lib/error_codes.py`:

```python
"""
Shared error codes and response helpers for the Mothbox API.

Provides standardized error code constants, message sanitization,
and a response helper to ensure consistent error JSON format across
all backend routes.

Usage:
    from webui.backend.lib.error_codes import (
        error_response, sanitize_message,
        VALIDATION_ERROR, NOT_FOUND, SERVER_ERROR,
    )

    return error_response(VALIDATION_ERROR, "Invalid input", 400)
    # Returns: (jsonify({"error": "Invalid input", "code": "VALIDATION_ERROR"}), 400)

Issue #388 - Standardize error codes across backend/frontend
"""

import re

from flask import jsonify

# ---------------------------------------------------------------------------
# Error code constants
# ---------------------------------------------------------------------------
# Each constant is its own string value, usable as both dict key and JSON value.

VALIDATION_ERROR = "VALIDATION_ERROR"
NOT_FOUND = "NOT_FOUND"
CONFLICT_ERROR = "CONFLICT_ERROR"
ACTIVATION_ERROR = "ACTIVATION_ERROR"
RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
HARDWARE_ERROR = "HARDWARE_ERROR"
STORAGE_ERROR = "STORAGE_ERROR"
PERMISSION_ERROR = "PERMISSION_ERROR"
SERVER_ERROR = "SERVER_ERROR"

# Convenience dict for iteration / membership checks
ERROR_CODES = {
    VALIDATION_ERROR: VALIDATION_ERROR,
    NOT_FOUND: NOT_FOUND,
    CONFLICT_ERROR: CONFLICT_ERROR,
    ACTIVATION_ERROR: ACTIVATION_ERROR,
    RATE_LIMIT_ERROR: RATE_LIMIT_ERROR,
    HARDWARE_ERROR: HARDWARE_ERROR,
    STORAGE_ERROR: STORAGE_ERROR,
    PERMISSION_ERROR: PERMISSION_ERROR,
    SERVER_ERROR: SERVER_ERROR,
}


# ---------------------------------------------------------------------------
# Message sanitization
# ---------------------------------------------------------------------------
# NOTE: This is distinct from security_utils.sanitize_error_message(), which
# takes an Exception and returns a generic message (hiding all details).
# This function sanitizes a *string* for safe display while preserving
# meaningful content: strips HTML tags, redacts internal file paths, truncates.


def sanitize_message(message: str | None, max_length: int = 200) -> str:
    """
    Sanitize an error message string for safe display to users.

    Strips HTML tags (defense-in-depth against XSS), redacts internal
    file paths (prevents information disclosure), and truncates long messages.

    Args:
        message: Raw error message (may contain user input or internal details)
        max_length: Maximum length before truncation (default 200)

    Returns:
        Sanitized message safe for display, or "An error occurred" for empty input
    """
    if not message:
        return "An error occurred"

    msg = str(message)

    # Strip HTML tags iteratively (handles nested/malformed tags)
    prev_len = -1
    while len(msg) != prev_len:
        prev_len = len(msg)
        msg = re.sub(r"<[^>]*>", "", msg)
        msg = re.sub(r"<[^>]*$", "", msg)  # Incomplete tags

    # Redact internal file paths to prevent information disclosure
    msg = re.sub(r"/(?:etc|var|home|opt|usr|tmp|root)/[^\s'\"]*", "[path]", msg)

    if len(msg) > max_length:
        msg = msg[: max_length - 3] + "..."

    return msg.strip() or "An error occurred"


# ---------------------------------------------------------------------------
# Response helper
# ---------------------------------------------------------------------------


def error_response(
    code: str, message: str, status: int = 400, **extra
) -> tuple:
    """
    Return a standardized JSON error response.

    Produces: ``(jsonify({"error": "<sanitized>", "code": "<CODE>", ...}), status)``

    Args:
        code: Error code constant (e.g., ``VALIDATION_ERROR``)
        message: Human-readable error description (will be sanitized)
        status: HTTP status code (default 400)
        **extra: Additional fields to include in the response JSON
                 (e.g., ``conflict=True``, ``message="detail"``)

    Returns:
        Tuple of (Flask Response, int) suitable for returning from a route
    """
    body = {"error": sanitize_message(message), "code": code, **extra}
    return jsonify(body), status
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest Tests/unit/test_error_codes.py -v`
Expected: All 20 tests PASS

**Step 5: Commit**

```bash
git add webui/backend/lib/error_codes.py Tests/unit/test_error_codes.py
git commit -m "feat: add shared error codes module with response helper (#388)"
```

---

### Task 2: Migrate scheduler_ui.py to shared module

**Files:**
- Modify: `webui/backend/routes/scheduler_ui.py`
- Test: `Tests/unit/test_scheduler_ui_routes.py` (existing)

**Step 1: Run existing scheduler tests to establish baseline**

Run: `python3 -m pytest Tests/unit/test_scheduler_ui_routes.py -v`
Expected: All tests PASS (baseline)

**Step 2: Update imports in scheduler_ui.py**

Add import at top of file (after existing imports, around line 53):

```python
from webui.backend.lib.error_codes import (
    ACTIVATION_ERROR,
    CONFLICT_ERROR,
    NOT_FOUND,
    SERVER_ERROR,
    VALIDATION_ERROR,
    error_response,
    sanitize_message,
)
```

**Step 3: Remove inline ERROR_CODES dict**

Delete lines 55-63 (the `ERROR_CODES = { ... }` dict and its comment).

**Step 4: Remove inline _sanitize_error_message function**

Delete lines 116-153 (the `_sanitize_error_message` function and its docstring).

**Step 5: Update _validate_location_params to use shared sanitizer**

Change the two calls from `_sanitize_error_message(...)` to `sanitize_message(...)`:
- Line ~100: `safe_error = sanitize_message(coord_error)`
- Line ~1566: `safe_error = sanitize_message(coord_error)`

**Step 6: Replace all jsonify error responses with error_response()**

There are 25 error responses to migrate. The pattern is:

**Before:**
```python
return jsonify(
    {
        "error": "Schedule not found",
        "code": ERROR_CODES["NOT_FOUND"],
    }
), 404
```

**After:**
```python
return error_response(NOT_FOUND, "Schedule not found", 404)
```

**For responses with extra fields:**
```python
# Before:
return jsonify(
    {
        "error": "Internal server error",
        "code": ERROR_CODES["SERVER_ERROR"],
        "message": "Failed to generate preview",
    }
), 500

# After:
return error_response(SERVER_ERROR, "Internal server error", 500, message="Failed to generate preview")
```

**For responses with conflict flag:**
```python
# Before:
return jsonify(
    {
        "error": "Schedule conflict detected",
        "code": ERROR_CODES["CONFLICT_ERROR"],
        "conflict": True,
    }
), 409

# After:
return error_response(CONFLICT_ERROR, "Schedule conflict detected", 409, conflict=True)
```

**Important:** Some error responses do NOT have a `"code"` field (e.g., line 396 `ValueError` handler, line 741 generic failure). These should also be converted to use `error_response()` with appropriate codes:
- `ValueError` in preview → `error_response(VALIDATION_ERROR, "Preview generation failed", 400)`
- Generic "Failed to create schedule" → `error_response(SERVER_ERROR, "Failed to create schedule", 500)`

**Step 7: Run existing tests to verify no regressions**

Run: `python3 -m pytest Tests/unit/test_scheduler_ui_routes.py -v`
Expected: All tests PASS (response format is backward-compatible)

**Step 8: Run ruff on modified file**

Run: `ruff check webui/backend/routes/scheduler_ui.py`
Expected: No errors (unused ERROR_CODES import removed)

**Step 9: Commit**

```bash
git add webui/backend/routes/scheduler_ui.py
git commit -m "refactor: migrate scheduler_ui.py to shared error codes (#388)"
```

---

### Task 3: Create frontend error codes module

**Files:**
- Create: `webui/frontend/src/utils/errorCodes.js`

**Step 1: Create the shared frontend module**

Create `webui/frontend/src/utils/errorCodes.js`:

```javascript
/**
 * Shared error codes and message mapping for the Mothbox API.
 *
 * Mirrors backend error codes from webui/backend/lib/error_codes.py.
 * Use getErrorMessage() to extract user-friendly messages from API errors.
 *
 * Issue #388 - Standardize error codes across backend/frontend
 *
 * @module utils/errorCodes
 */

/**
 * Error code constants matching the backend.
 * Used for programmatic error handling (e.g., switch statements).
 */
export const ERROR_CODES = {
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  NOT_FOUND: 'NOT_FOUND',
  CONFLICT_ERROR: 'CONFLICT_ERROR',
  ACTIVATION_ERROR: 'ACTIVATION_ERROR',
  RATE_LIMIT_ERROR: 'RATE_LIMIT_ERROR',
  HARDWARE_ERROR: 'HARDWARE_ERROR',
  STORAGE_ERROR: 'STORAGE_ERROR',
  PERMISSION_ERROR: 'PERMISSION_ERROR',
  SERVER_ERROR: 'SERVER_ERROR',
  // Client-side only (no backend equivalent)
  NETWORK_ERROR: 'NETWORK_ERROR',
  TIMEOUT_ERROR: 'TIMEOUT_ERROR',
};

/**
 * User-friendly messages for each error code.
 * These are shown to the user when an API error occurs.
 */
export const ERROR_MESSAGES = {
  [ERROR_CODES.VALIDATION_ERROR]: 'Please fix the errors above.',
  [ERROR_CODES.NOT_FOUND]: 'Resource not found. It may have been deleted.',
  [ERROR_CODES.CONFLICT_ERROR]: 'Schedule has conflicts that must be resolved.',
  [ERROR_CODES.ACTIVATION_ERROR]: 'Failed to activate schedule.',
  [ERROR_CODES.RATE_LIMIT_ERROR]: 'Too many requests. Please wait a moment.',
  [ERROR_CODES.HARDWARE_ERROR]: 'Hardware unavailable. Please check connections.',
  [ERROR_CODES.STORAGE_ERROR]: 'Storage error. Check available disk space.',
  [ERROR_CODES.PERMISSION_ERROR]: 'Permission denied.',
  [ERROR_CODES.SERVER_ERROR]: 'Server error. Please try again later.',
  [ERROR_CODES.NETWORK_ERROR]: 'Unable to save. Please check your connection.',
  [ERROR_CODES.TIMEOUT_ERROR]: 'Request timed out. Please try again.',
};

/**
 * Sanitize an error message string for safe display.
 *
 * Strips HTML tags (defense-in-depth — React escapes by default)
 * and truncates long messages.
 *
 * @param {string} message - Raw error message
 * @param {number} [maxLength=200] - Maximum message length
 * @returns {string} Sanitized message
 */
export function sanitizeMessage(message, maxLength = 200) {
  if (!message) return 'An unexpected error occurred.';
  let msg = String(message);

  // Strip HTML tags iteratively (handles incomplete/malformed tags)
  let previousLength;
  do {
    previousLength = msg.length;
    msg = msg.replace(/<[^>]*>?/g, '');
  } while (msg.length < previousLength);

  return msg.length > maxLength ? msg.slice(0, maxLength) + '...' : msg;
}

/**
 * Extract a user-friendly error message from an API error.
 *
 * Checks for known error codes first (from API response or error object),
 * then falls back to the server-provided error message (sanitized),
 * then to a generic fallback.
 *
 * @param {Error|Object} error - Axios error or error-like object
 * @param {string} [fallback='An unexpected error occurred.'] - Fallback message
 * @returns {string} User-friendly error message
 */
export function getErrorMessage(error, fallback = 'An unexpected error occurred.') {
  // Check for known error code from API response (axios pattern)
  const apiCode = error?.response?.data?.code;
  if (apiCode && ERROR_MESSAGES[apiCode]) {
    return ERROR_MESSAGES[apiCode];
  }

  // Check for known error code on the error object itself
  if (error?.code && ERROR_MESSAGES[error.code]) {
    return ERROR_MESSAGES[error.code];
  }

  // Fall back to server-provided message, sanitized
  const rawMessage = error?.response?.data?.error || error?.message;
  if (rawMessage) {
    return sanitizeMessage(rawMessage);
  }

  return fallback;
}
```

**Step 2: Commit**

```bash
git add webui/frontend/src/utils/errorCodes.js
git commit -m "feat: add frontend error codes module mirroring backend (#388)"
```

---

### Task 4: Migrate ScheduleEditor.jsx to shared module

**Files:**
- Modify: `webui/frontend/src/components/scheduler/ScheduleEditor/ScheduleEditor.jsx`

**Step 1: Add import for shared module**

Add at top of file (with other utility imports, after line 11):

```javascript
import { getErrorMessage } from '../../../utils/errorCodes';
```

**Step 2: Remove inline KNOWN_ERROR_CODES**

Delete the `KNOWN_ERROR_CODES` object (lines 23-30) and its JSDoc comment (lines 18-22).

**Step 3: Remove inline sanitizeErrorMessage**

Delete the `sanitizeErrorMessage` function (lines 47-75) and its JSDoc comment (lines 32-46).

**Step 4: Update all call sites**

Find all uses of `sanitizeErrorMessage(...)` in the file and replace with `getErrorMessage(...)`. Search for the pattern. The function signature is compatible — both accept an error object and return a string.

**Step 5: Run frontend lint**

Run: `cd webui/frontend && npx eslint src/components/scheduler/ScheduleEditor/ScheduleEditor.jsx`
Expected: No errors about unused imports or missing functions

**Step 6: Commit**

```bash
git add webui/frontend/src/components/scheduler/ScheduleEditor/ScheduleEditor.jsx
git commit -m "refactor: migrate ScheduleEditor to shared error codes module (#388)"
```

---

### Task 5: Final verification

**Step 1: Run backend linting**

Run: `ruff check webui/backend/lib/error_codes.py webui/backend/routes/scheduler_ui.py`
Expected: No errors

**Step 2: Run backend tests**

Run: `python3 -m pytest Tests/unit/test_error_codes.py Tests/unit/test_scheduler_ui_routes.py Tests/unit/test_scheduler_ui_security.py -v`
Expected: All tests PASS

**Step 3: Run security scan**

Run: `bandit -c pyproject.toml -r webui/backend/lib/error_codes.py`
Expected: No issues

**Step 4: Build frontend**

Run: `cd webui/frontend && npm run build`
Expected: Build succeeds with no errors

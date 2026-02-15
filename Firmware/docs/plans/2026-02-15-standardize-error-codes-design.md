# Design: Standardize Error Codes Across Backend/Frontend (#388)

## Problem

Backend routes return errors in inconsistent formats — some use `{"error": "msg"}`, some add `{"error": "msg", "message": "detail"}`, and only `scheduler_ui.py` includes structured error codes. The frontend has to guess error types from HTTP status codes or parse message strings. There are 517 error responses across 17 route files.

## Decision

- **Scope**: All route files, rolled out incrementally
- **This PR**: Shared module + scheduler migration + frontend update
- **Follow-up PRs**: Remaining 16 route files in logical batches

## Architecture

### Backend: `webui/backend/lib/error_codes.py`

Single source of truth for error codes, sanitization, and response helper.

**Error codes:**

| Code | Typical HTTP Status | Usage |
|------|-------------------|-------|
| `VALIDATION_ERROR` | 400 | Invalid input, bad parameters |
| `NOT_FOUND` | 404 | Resource doesn't exist |
| `CONFLICT_ERROR` | 409 | Schedule conflict, duplicate resource |
| `ACTIVATION_ERROR` | 400 | Schedule activation failure |
| `RATE_LIMIT_ERROR` | 429 | Too many requests |
| `HARDWARE_ERROR` | 503 | Camera/GPIO/sensor unavailable |
| `STORAGE_ERROR` | 500 | Disk full, file I/O failure |
| `PERMISSION_ERROR` | 403 | Path traversal, forbidden access |
| `SERVER_ERROR` | 500 | Catch-all internal error |

**Helper function:**

```python
def error_response(code: str, message: str, status: int = 400) -> tuple:
    """Return a standardized JSON error response."""
    safe_message = sanitize_error_message(message)
    return jsonify({"error": safe_message, "code": code}), status
```

**Sanitization:** `_sanitize_error_message()` moves from `scheduler_ui.py` to `error_codes.py` as the shared `sanitize_error_message()`. Strips HTML, redacts internal paths, truncates to 200 chars.

### Frontend: `webui/frontend/src/utils/errorCodes.js`

Mirrors backend codes with user-friendly message mapping.

```javascript
export const ERROR_CODES = {
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  NOT_FOUND: 'NOT_FOUND',
  // ... all codes
};

export const ERROR_MESSAGES = {
  VALIDATION_ERROR: 'Please fix the errors above.',
  NOT_FOUND: 'Resource not found. It may have been deleted.',
  // ... user-friendly messages for each code
  NETWORK_ERROR: 'Unable to connect. Please check your connection.',
};

export function getErrorMessage(error) { /* code -> message mapping with fallback */ }
```

**ScheduleEditor.jsx** removes inline `KNOWN_ERROR_CODES` and `sanitizeErrorMessage()`, imports from `errorCodes.js`. The existing `errorMessages.js` (form field validation messages) stays unchanged.

### Response Format

All error responses follow this structure:

```json
{
  "error": "User-readable sanitized message",
  "code": "ERROR_CODE_CONSTANT"
}
```

Backwards compatible — the `error` field (already present in all routes) stays the same. The `code` field is additive.

## Scheduler Migration

- Remove `ERROR_CODES` dict from `scheduler_ui.py` (lines 55-63)
- Remove `_sanitize_error_message()` from `scheduler_ui.py` (lines 116-153)
- Import `error_response`, `sanitize_error_message`, and codes from `error_codes.py`
- Replace 17 `jsonify({"error": ..., "code": ...})` calls with `error_response(...)`

## Testing

- Unit tests for `error_codes.py`: response format, sanitization, all code constants
- Existing scheduler tests verify backward-compatible format
- Frontend: existing ScheduleEditor error handling tests still pass

## Follow-up Work

Migrate remaining route files in batches:
1. `camera.py`, `gpio.py`, `system.py` (hardware)
2. `gallery.py`, `photos.py`, `metadata.py` (media)
3. `deployment.py`, `sidecar.py`, `config.py` (config)
4. `export.py`, `export_presets.py` (export)
5. `search.py`, `gps.py`, `gps_exif.py` (search/GPS)
6. `preferences.py`, `scheduler.py` (misc)

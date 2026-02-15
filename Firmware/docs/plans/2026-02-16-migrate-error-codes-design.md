# Design: Migrate Remaining Route Files to Shared Error Codes (#414)

## Problem

PR #413 introduced `webui/backend/lib/error_codes.py` and migrated `scheduler_ui.py` as the first route file. The remaining 16 route files still use inline `jsonify({"error": ...})` responses (472 total) and need migration to `error_response()`.

## Decision

- **Approach**: Mechanical replacement with context-aware error code selection
- **PR strategy**: 7 PRs, one per logical batch
- **No new constants**: Existing 9 error codes cover all cases
- **No frontend changes**: Frontend module already exists from PR #413

## Error Code Mapping

| HTTP Status | Error Code | Rationale |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Invalid input/parameters |
| 403 | `PERMISSION_ERROR` | Path traversal, forbidden access |
| 404 | `NOT_FOUND` | Resource doesn't exist |
| 408 | `VALIDATION_ERROR` | GPS timeout (gps.py, 1 instance) |
| 500 (generic) | `SERVER_ERROR` | Catch-all internal errors |
| 500 (disk/IO) | `STORAGE_ERROR` | Disk full, file write failures |
| 503 | `HARDWARE_ERROR` | Camera/GPIO/service unavailable |

Context-aware override: When a 500 is clearly about file I/O or disk space, use `STORAGE_ERROR` instead of `SERVER_ERROR`.

## Extra Fields

3 edge cases with extra JSON fields preserved via `**extra` kwargs:
- `gallery.py`: `error_response(NOT_FOUND, "Series not found", 404, series_id=series_id)`
- `export.py` (2 places): `error_response(SERVER_ERROR, "ZIP export failed", 500, details=result.errors)`

## Batch Structure

| Batch | Files | Est. Responses | Branch |
|---|---|---|---|
| 1 | `camera.py`, `gpio.py`, `system.py` | 18 | `refactor/414-batch1-hardware` |
| 2 | `gallery.py`, `metadata.py` | 70 | `refactor/414-batch2-media` |
| 3 | `config.py` | 49 | `refactor/414-batch3-config` |
| 4 | `export.py`, `export_presets.py` | 139 | `refactor/414-batch4-export` |
| 5 | `deployment.py`, `sidecar.py` | 125 | `refactor/414-batch5-deployment` |
| 6 | `search.py`, `gps.py`, `gps_exif.py` | 46 | `refactor/414-batch6-search-gps` |
| 7 | `preferences.py`, `presets.py`, `scheduler.py` | 33 | `refactor/414-batch7-misc` |

## Per-File Migration Pattern

1. Add `from webui.backend.lib.error_codes import error_response, VALIDATION_ERROR, ...` (only codes used)
2. Replace `return jsonify({"error": "..."}), 4xx` → `return error_response(CODE, "...", 4xx)`
3. For extra-field responses, pass via `**extra` kwargs
4. `ruff check && ruff format` on modified files
5. Run relevant test files to verify backward compatibility

## Testing Strategy

Each batch runs corresponding test files before PR. The `"error"` field is unchanged (backward compatible). The additive `"code"` field won't break existing assertions.

## What This Does NOT Change

- No new error code constants
- No frontend changes
- No changes to `error_codes.py` itself
- No test file modifications needed

## References

- Design: `docs/plans/2026-02-15-standardize-error-codes-design.md`
- Shared module: `webui/backend/lib/error_codes.py`
- Reference migration: `webui/backend/routes/scheduler_ui.py`
- Initial PR: #413
- Parent issue: #388

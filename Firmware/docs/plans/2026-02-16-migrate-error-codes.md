# Migrate Remaining Route Files to Shared Error Codes — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate 472 inline `jsonify({"error": ...})` responses across 16 route files to the shared `error_response()` helper, adding structured error codes to every API error response.

**Architecture:** Each route file gets an import of `error_response` and the specific error code constants it needs from `webui/backend/lib/error_codes.py`. Every `return jsonify({"error": "..."}), status` becomes `return error_response(CODE, "...", status)`. Extra JSON fields pass through via `**extra` kwargs. The `"error"` field is unchanged for backward compatibility; the `"code"` field is additive.

**Tech Stack:** Python/Flask (backend), pytest (testing), ruff (linting)

**Important context:**
- Reference implementation: `webui/backend/routes/scheduler_ui.py` (already migrated in PR #413)
- Shared module: `webui/backend/lib/error_codes.py` — provides `error_response()`, `sanitize_message()`, and 9 error code constants
- Error code mapping: 400→`VALIDATION_ERROR`, 403→`PERMISSION_ERROR`, 404→`NOT_FOUND`, 408→`VALIDATION_ERROR`, 500→`SERVER_ERROR` (or `STORAGE_ERROR` for disk/IO), 503→`HARDWARE_ERROR`
- Extra-field edge cases: `gallery.py` line 870 has `series_id`, `export.py` lines 984/1128 have `details` — preserved via `**extra`
- No test changes needed — format is backward compatible (additive `"code"` field)
- Design doc: `docs/plans/2026-02-16-migrate-error-codes-design.md`

---

### Task 1: Batch 1 — Hardware routes (camera.py, gpio.py, system.py)

**Files:**
- Modify: `webui/backend/routes/camera.py` (6 error responses)
- Modify: `webui/backend/routes/gpio.py` (8 error responses)
- Modify: `webui/backend/routes/system.py` (4 error responses)
- Test: `Tests/unit/test_camera_routes.py`, `Tests/unit/test_gpio_routes.py`, `Tests/unit/test_system_routes.py`

**Step 1: Create branch**

Run: `git checkout -b refactor/414-batch1-hardware dev`

**Step 2: Run baseline tests**

Run: `python3 -m pytest Tests/unit/test_camera_routes.py Tests/unit/test_gpio_routes.py Tests/unit/test_system_routes.py -v --tb=short -q`
Expected: All tests PASS

**Step 3: Migrate camera.py**

Add import at top of file (after existing Flask imports):

```python
from webui.backend.lib.error_codes import (
    VALIDATION_ERROR,
    SERVER_ERROR,
    error_response,
)
```

Replace these 6 error responses:

| Line | Before | After |
|------|--------|-------|
| 673 | `return jsonify({"error": "Failed to get camera settings"}), 500` | `return error_response(SERVER_ERROR, "Failed to get camera settings", 500)` |
| 696 | `return jsonify({"error": f"Invalid setting: {key}"}), 400` | `return error_response(VALIDATION_ERROR, f"Invalid setting: {key}")` |
| 699 | `return jsonify({"error": f"Invalid value for {key}"}), 400` | `return error_response(VALIDATION_ERROR, f"Invalid value for {key}")` |
| 701 | `return jsonify({"error": f"Invalid type for {key}"}), 400` | `return error_response(VALIDATION_ERROR, f"Invalid type for {key}")` |
| 743 | `return jsonify({"error": "Failed to update camera settings"}), 500` | `return error_response(SERVER_ERROR, "Failed to update camera settings", 500)` |
| 1203 | `return jsonify({"error": "Failed to freeze settings"}), 500` | `return error_response(SERVER_ERROR, "Failed to freeze settings", 500)` |

Note: 400 is the default status for `error_response()`, so omit it for VALIDATION_ERROR calls.

**Step 4: Migrate gpio.py**

Add import at top of file:

```python
from webui.backend.lib.error_codes import (
    HARDWARE_ERROR,
    SERVER_ERROR,
    VALIDATION_ERROR,
    error_response,
)
```

Replace these 8 error responses:

| Line | Before | After |
|------|--------|-------|
| 30 | `return jsonify({"error": "Failed to get GPIO status"}), 500` | `return error_response(SERVER_ERROR, "Failed to get GPIO status", 500)` |
| 42 | `return jsonify({"error": "Missing relay or state parameter"}), 400` | `return error_response(VALIDATION_ERROR, "Missing relay or state parameter")` |
| 44 | `return jsonify({"error": "State must be a boolean value (true/false)"}), 400` | `return error_response(VALIDATION_ERROR, "State must be a boolean value (true/false)")` |
| 48 | `return jsonify({"error": f"Invalid relay: {relay}"}), 400` | `return error_response(VALIDATION_ERROR, f"Invalid relay: {relay}")` |
| 63 | `return jsonify({"error": "GPIO daemon not available"}), 503` | `return error_response(HARDWARE_ERROR, "GPIO daemon not available", 503)` |
| 66 | `return jsonify({"error": "Failed to control GPIO"}), 500` | `return error_response(SERVER_ERROR, "Failed to control GPIO", 500)` |
| 97 | `return jsonify({"error": "GPIO daemon not available"}), 503` | `return error_response(HARDWARE_ERROR, "GPIO daemon not available", 503)` |
| 100 | `return jsonify({"error": "Failed to trigger flash"}), 500` | `return error_response(SERVER_ERROR, "Failed to trigger flash", 500)` |

**Step 5: Migrate system.py**

Add import at top of file:

```python
from webui.backend.lib.error_codes import (
    SERVER_ERROR,
    error_response,
)
```

Replace these 4 error responses:

| Line | Before | After |
|------|--------|-------|
| 144 | `return jsonify({"error": "Failed to get storage info"}), 500` | `return error_response(SERVER_ERROR, "Failed to get storage info", 500)` |
| 235 | `return jsonify({"error": "Failed to get power status"}), 500` | `return error_response(SERVER_ERROR, "Failed to get power status", 500)` |
| 275 | `return jsonify({"error": "Failed to get system info"}), 500` | `return error_response(SERVER_ERROR, "Failed to get system info", 500)` |
| 372 | `return jsonify({"error": "Failed to get diagnostic info"}), 500` | `return error_response(SERVER_ERROR, "Failed to get diagnostic info", 500)` |

**Step 6: Run ruff**

Run: `ruff check webui/backend/routes/camera.py webui/backend/routes/gpio.py webui/backend/routes/system.py && ruff format webui/backend/routes/camera.py webui/backend/routes/gpio.py webui/backend/routes/system.py`
Expected: Clean (may warn about unused `jsonify` import if all uses removed — unlikely since success responses still use it)

**Step 7: Run tests**

Run: `python3 -m pytest Tests/unit/test_camera_routes.py Tests/unit/test_gpio_routes.py Tests/unit/test_system_routes.py -v --tb=short -q`
Expected: All tests PASS

**Step 8: Verify no remaining inline errors**

Run: `grep -n 'jsonify({"error"' webui/backend/routes/camera.py webui/backend/routes/gpio.py webui/backend/routes/system.py`
Expected: No output (all migrated)

**Step 9: Commit and PR**

```bash
git add webui/backend/routes/camera.py webui/backend/routes/gpio.py webui/backend/routes/system.py
git commit -m "$(cat <<'EOF'
refactor: migrate hardware routes to shared error codes (#414)

Migrate camera.py (6), gpio.py (8), and system.py (4) error responses
to use error_response() from the shared error codes module.

Batch 1 of 7 for issue #414.
EOF
)"
```

Push and create PR:
```bash
git push -u origin refactor/414-batch1-hardware
gh pr create --base dev --title "refactor: migrate hardware routes to shared error codes (#414)" --body "$(cat <<'EOF'
## Summary
- Migrate `camera.py` (6), `gpio.py` (8), and `system.py` (4) error responses to `error_response()`
- Batch 1 of 7 for #414

## Test plan
- [x] All existing tests pass (`test_camera_routes.py`, `test_gpio_routes.py`, `test_system_routes.py`)
- [x] No remaining inline `jsonify({"error"` patterns in migrated files
- [x] ruff clean
EOF
)"
```

---

### Task 2: Batch 2 — Media routes (gallery.py, metadata.py)

**Files:**
- Modify: `webui/backend/routes/gallery.py` (~63 error responses)
- Modify: `webui/backend/routes/metadata.py` (~13 error responses)
- Test: `Tests/unit/test_gallery_routes.py`, `Tests/unit/test_metadata_routes.py`

**Step 1: Create branch**

Run: `git checkout -b refactor/414-batch2-media dev`

**Step 2: Run baseline tests**

Run: `python3 -m pytest Tests/unit/test_gallery_routes.py Tests/unit/test_metadata_routes.py -v --tb=short -q`
Expected: All tests PASS

**Step 3: Migrate gallery.py**

Add import at top of file:

```python
from webui.backend.lib.error_codes import (
    HARDWARE_ERROR,
    NOT_FOUND,
    SERVER_ERROR,
    VALIDATION_ERROR,
    error_response,
)
```

Apply the error code mapping to all ~63 responses:
- 400 responses → `error_response(VALIDATION_ERROR, "...", 400)` (omit status since 400 is default)
- 404 responses → `error_response(NOT_FOUND, "...", 404)`
- 500 responses → `error_response(SERVER_ERROR, "...", 500)`
- 503 responses → `error_response(HARDWARE_ERROR, "...", 503)`

**Special case** — line 870 has extra field:
```python
# Before:
return jsonify({"error": "Series not found", "series_id": series_id}), 404
# After:
return error_response(NOT_FOUND, "Series not found", 404, series_id=series_id)
```

**Step 4: Migrate metadata.py**

Add import at top of file:

```python
from webui.backend.lib.error_codes import (
    HARDWARE_ERROR,
    NOT_FOUND,
    PERMISSION_ERROR,
    SERVER_ERROR,
    VALIDATION_ERROR,
    error_response,
)
```

Apply mapping to all ~13 responses:
- Line 71 (403 "Access denied") → `error_response(PERMISSION_ERROR, "Invalid path: Access denied", 403)`
- 400 responses → `VALIDATION_ERROR`
- 404 responses → `NOT_FOUND`
- 500 responses → `SERVER_ERROR`
- 503 responses → `HARDWARE_ERROR`

**Step 5: Run ruff**

Run: `ruff check webui/backend/routes/gallery.py webui/backend/routes/metadata.py && ruff format webui/backend/routes/gallery.py webui/backend/routes/metadata.py`
Expected: Clean

**Step 6: Run tests**

Run: `python3 -m pytest Tests/unit/test_gallery_routes.py Tests/unit/test_metadata_routes.py -v --tb=short -q`
Expected: All tests PASS

**Step 7: Verify no remaining inline errors**

Run: `grep -n 'jsonify({"error"' webui/backend/routes/gallery.py webui/backend/routes/metadata.py`
Expected: No output

**Step 8: Commit and PR**

```bash
git add webui/backend/routes/gallery.py webui/backend/routes/metadata.py
git commit -m "$(cat <<'EOF'
refactor: migrate media routes to shared error codes (#414)

Migrate gallery.py (~63) and metadata.py (~13) error responses
to use error_response() from the shared error codes module.

Batch 2 of 7 for issue #414.
EOF
)"
git push -u origin refactor/414-batch2-media
gh pr create --base dev --title "refactor: migrate media routes to shared error codes (#414)" --body "$(cat <<'EOF'
## Summary
- Migrate `gallery.py` (~63) and `metadata.py` (~13) error responses to `error_response()`
- Batch 2 of 7 for #414

## Test plan
- [x] All existing tests pass (`test_gallery_routes.py`, `test_metadata_routes.py`)
- [x] No remaining inline `jsonify({"error"` patterns in migrated files
- [x] ruff clean
EOF
)"
```

---

### Task 3: Batch 3 — Config routes (config.py)

**Files:**
- Modify: `webui/backend/routes/config.py` (~53 error responses)
- Test: `Tests/unit/test_config_routes.py`

**Step 1: Create branch**

Run: `git checkout -b refactor/414-batch3-config dev`

**Step 2: Run baseline tests**

Run: `python3 -m pytest Tests/unit/test_config_routes.py -v --tb=short -q`
Expected: All tests PASS

**Step 3: Migrate config.py**

Add import at top of file:

```python
from webui.backend.lib.error_codes import (
    SERVER_ERROR,
    VALIDATION_ERROR,
    error_response,
)
```

Apply mapping to all ~53 responses:
- All 400 responses → `VALIDATION_ERROR` (default status, omit 400)
- All 500 responses → `SERVER_ERROR`

This file has no 403/404/503 responses — just validation errors and server errors.

**Step 4: Run ruff**

Run: `ruff check webui/backend/routes/config.py && ruff format webui/backend/routes/config.py`
Expected: Clean

**Step 5: Run tests**

Run: `python3 -m pytest Tests/unit/test_config_routes.py -v --tb=short -q`
Expected: All tests PASS

**Step 6: Verify no remaining inline errors**

Run: `grep -n 'jsonify({"error"' webui/backend/routes/config.py`
Expected: No output

**Step 7: Commit and PR**

```bash
git add webui/backend/routes/config.py
git commit -m "$(cat <<'EOF'
refactor: migrate config routes to shared error codes (#414)

Migrate config.py (~53) error responses to use error_response()
from the shared error codes module.

Batch 3 of 7 for issue #414.
EOF
)"
git push -u origin refactor/414-batch3-config
gh pr create --base dev --title "refactor: migrate config routes to shared error codes (#414)" --body "$(cat <<'EOF'
## Summary
- Migrate `config.py` (~53) error responses to `error_response()`
- Batch 3 of 7 for #414

## Test plan
- [x] All existing tests pass (`test_config_routes.py`)
- [x] No remaining inline `jsonify({"error"` patterns
- [x] ruff clean
EOF
)"
```

---

### Task 4: Batch 4 — Export routes (export.py, export_presets.py)

**Files:**
- Modify: `webui/backend/routes/export.py` (~125 error responses)
- Modify: `webui/backend/routes/export_presets.py` (~13 error responses)
- Test: `Tests/unit/test_export_routes.py`, `Tests/unit/test_export_preset_routes.py`

**Step 1: Create branch**

Run: `git checkout -b refactor/414-batch4-export dev`

**Step 2: Run baseline tests**

Run: `python3 -m pytest Tests/unit/test_export_routes.py Tests/unit/test_export_preset_routes.py -v --tb=short -q`
Expected: All tests PASS

**Step 3: Migrate export.py**

Add import at top of file:

```python
from webui.backend.lib.error_codes import (
    NOT_FOUND,
    PERMISSION_ERROR,
    SERVER_ERROR,
    VALIDATION_ERROR,
    error_response,
)
```

Apply mapping to all ~125 responses:
- 400 responses → `VALIDATION_ERROR`
- 403 responses → `PERMISSION_ERROR`
- 404 responses → `NOT_FOUND`
- 500 responses → `SERVER_ERROR`

**Special cases** — lines 984 and 1128 have extra `details` field:
```python
# Before:
return jsonify({"error": "ZIP export failed", "details": result.errors}), 500
# After:
return error_response(SERVER_ERROR, "ZIP export failed", 500, details=result.errors)
```

This is the largest file. Work methodically top-to-bottom.

**Step 4: Migrate export_presets.py**

Add import at top of file:

```python
from webui.backend.lib.error_codes import (
    NOT_FOUND,
    SERVER_ERROR,
    VALIDATION_ERROR,
    error_response,
)
```

Apply mapping to all ~13 responses.

**Step 5: Run ruff**

Run: `ruff check webui/backend/routes/export.py webui/backend/routes/export_presets.py && ruff format webui/backend/routes/export.py webui/backend/routes/export_presets.py`
Expected: Clean

**Step 6: Run tests**

Run: `python3 -m pytest Tests/unit/test_export_routes.py Tests/unit/test_export_preset_routes.py -v --tb=short -q`
Expected: All tests PASS

**Step 7: Verify no remaining inline errors**

Run: `grep -n 'jsonify({"error"' webui/backend/routes/export.py webui/backend/routes/export_presets.py`
Expected: No output

**Step 8: Commit and PR**

```bash
git add webui/backend/routes/export.py webui/backend/routes/export_presets.py
git commit -m "$(cat <<'EOF'
refactor: migrate export routes to shared error codes (#414)

Migrate export.py (~125) and export_presets.py (~13) error responses
to use error_response() from the shared error codes module.

Batch 4 of 7 for issue #414.
EOF
)"
git push -u origin refactor/414-batch4-export
gh pr create --base dev --title "refactor: migrate export routes to shared error codes (#414)" --body "$(cat <<'EOF'
## Summary
- Migrate `export.py` (~125) and `export_presets.py` (~13) error responses to `error_response()`
- Batch 4 of 7 for #414

## Test plan
- [x] All existing tests pass (`test_export_routes.py`, `test_export_preset_routes.py`)
- [x] No remaining inline `jsonify({"error"` patterns in migrated files
- [x] ruff clean
EOF
)"
```

---

### Task 5: Batch 5 — Deployment routes (deployment.py, sidecar.py)

**Files:**
- Modify: `webui/backend/routes/deployment.py` (~93 error responses)
- Modify: `webui/backend/routes/sidecar.py` (~153 error responses)
- Test: `Tests/unit/test_deployment_routes.py`, `Tests/unit/test_sidecar_routes_filtering.py`

**Step 1: Create branch**

Run: `git checkout -b refactor/414-batch5-deployment dev`

**Step 2: Run baseline tests**

Run: `python3 -m pytest Tests/unit/test_deployment_routes.py Tests/unit/test_sidecar_routes_filtering.py -v --tb=short -q`
Expected: All tests PASS

**Step 3: Migrate deployment.py**

Add import at top of file:

```python
from webui.backend.lib.error_codes import (
    HARDWARE_ERROR,
    NOT_FOUND,
    PERMISSION_ERROR,
    SERVER_ERROR,
    VALIDATION_ERROR,
    error_response,
)
```

Apply mapping to all ~93 responses:
- 400 responses → `VALIDATION_ERROR`
- 403 responses → `PERMISSION_ERROR`
- 404 responses → `NOT_FOUND`
- 500 responses → `SERVER_ERROR`
- 503 responses → `HARDWARE_ERROR`

**Step 4: Migrate sidecar.py**

Add import at top of file:

```python
from webui.backend.lib.error_codes import (
    HARDWARE_ERROR,
    NOT_FOUND,
    PERMISSION_ERROR,
    SERVER_ERROR,
    VALIDATION_ERROR,
    error_response,
)
```

Apply mapping to all ~153 responses.

**Step 5: Run ruff**

Run: `ruff check webui/backend/routes/deployment.py webui/backend/routes/sidecar.py && ruff format webui/backend/routes/deployment.py webui/backend/routes/sidecar.py`
Expected: Clean

**Step 6: Run tests**

Run: `python3 -m pytest Tests/unit/test_deployment_routes.py Tests/unit/test_sidecar_routes_filtering.py -v --tb=short -q`
Expected: All tests PASS

**Step 7: Verify no remaining inline errors**

Run: `grep -n 'jsonify({"error"' webui/backend/routes/deployment.py webui/backend/routes/sidecar.py`
Expected: No output

**Step 8: Commit and PR**

```bash
git add webui/backend/routes/deployment.py webui/backend/routes/sidecar.py
git commit -m "$(cat <<'EOF'
refactor: migrate deployment routes to shared error codes (#414)

Migrate deployment.py (~93) and sidecar.py (~153) error responses
to use error_response() from the shared error codes module.

Batch 5 of 7 for issue #414.
EOF
)"
git push -u origin refactor/414-batch5-deployment
gh pr create --base dev --title "refactor: migrate deployment routes to shared error codes (#414)" --body "$(cat <<'EOF'
## Summary
- Migrate `deployment.py` (~93) and `sidecar.py` (~153) error responses to `error_response()`
- Batch 5 of 7 for #414

## Test plan
- [x] All existing tests pass (`test_deployment_routes.py`, `test_sidecar_routes_filtering.py`)
- [x] No remaining inline `jsonify({"error"` patterns in migrated files
- [x] ruff clean
EOF
)"
```

---

### Task 6: Batch 6 — Search & GPS routes (search.py, gps.py, gps_exif.py)

**Files:**
- Modify: `webui/backend/routes/search.py` (10 error responses)
- Modify: `webui/backend/routes/gps.py` (14 error responses)
- Modify: `webui/backend/routes/gps_exif.py` (20 error responses)
- Test: `Tests/unit/test_search_api.py`, `Tests/unit/test_gps_routes.py`, `Tests/unit/test_gps_exif_routes.py`

**Step 1: Create branch**

Run: `git checkout -b refactor/414-batch6-search-gps dev`

**Step 2: Run baseline tests**

Run: `python3 -m pytest Tests/unit/test_search_api.py Tests/unit/test_gps_routes.py Tests/unit/test_gps_exif_routes.py -v --tb=short -q`
Expected: All tests PASS

**Step 3: Migrate search.py**

Add import at top of file:

```python
from webui.backend.lib.error_codes import (
    HARDWARE_ERROR,
    SERVER_ERROR,
    VALIDATION_ERROR,
    error_response,
)
```

Apply mapping to all 10 responses:
- 400 responses → `VALIDATION_ERROR`
- 500 responses → `SERVER_ERROR`
- 503 responses → `HARDWARE_ERROR`

**Step 4: Migrate gps.py**

Add import at top of file:

```python
from webui.backend.lib.error_codes import (
    SERVER_ERROR,
    VALIDATION_ERROR,
    error_response,
)
```

Apply mapping to all 14 responses:
- 400 responses → `VALIDATION_ERROR`
- 408 responses → `VALIDATION_ERROR` (GPS timeout — treated as a request-level validation failure)
- 500 responses → `SERVER_ERROR`

**Step 5: Migrate gps_exif.py**

Add import at top of file:

```python
from webui.backend.lib.error_codes import (
    NOT_FOUND,
    SERVER_ERROR,
    VALIDATION_ERROR,
    error_response,
)
```

Apply mapping to all 20 responses.

**Step 6: Run ruff**

Run: `ruff check webui/backend/routes/search.py webui/backend/routes/gps.py webui/backend/routes/gps_exif.py && ruff format webui/backend/routes/search.py webui/backend/routes/gps.py webui/backend/routes/gps_exif.py`
Expected: Clean

**Step 7: Run tests**

Run: `python3 -m pytest Tests/unit/test_search_api.py Tests/unit/test_gps_routes.py Tests/unit/test_gps_exif_routes.py -v --tb=short -q`
Expected: All tests PASS

**Step 8: Verify no remaining inline errors**

Run: `grep -n 'jsonify({"error"' webui/backend/routes/search.py webui/backend/routes/gps.py webui/backend/routes/gps_exif.py`
Expected: No output

**Step 9: Commit and PR**

```bash
git add webui/backend/routes/search.py webui/backend/routes/gps.py webui/backend/routes/gps_exif.py
git commit -m "$(cat <<'EOF'
refactor: migrate search & GPS routes to shared error codes (#414)

Migrate search.py (10), gps.py (14), and gps_exif.py (20) error
responses to use error_response() from the shared error codes module.

Batch 6 of 7 for issue #414.
EOF
)"
git push -u origin refactor/414-batch6-search-gps
gh pr create --base dev --title "refactor: migrate search & GPS routes to shared error codes (#414)" --body "$(cat <<'EOF'
## Summary
- Migrate `search.py` (10), `gps.py` (14), and `gps_exif.py` (20) error responses to `error_response()`
- Batch 6 of 7 for #414

## Test plan
- [x] All existing tests pass (`test_search_api.py`, `test_gps_routes.py`, `test_gps_exif_routes.py`)
- [x] No remaining inline `jsonify({"error"` patterns in migrated files
- [x] ruff clean
EOF
)"
```

---

### Task 7: Batch 7 — Misc routes (preferences.py, presets.py, scheduler.py)

**Files:**
- Modify: `webui/backend/routes/preferences.py` (9 error responses)
- Modify: `webui/backend/routes/presets.py` (~21 error responses)
- Modify: `webui/backend/routes/scheduler.py` (8 error responses)
- Test: `Tests/unit/test_preferences_routes.py`, `Tests/unit/test_presets_routes.py`, `Tests/unit/test_scheduler_routes.py`

**Step 1: Create branch**

Run: `git checkout -b refactor/414-batch7-misc dev`

**Step 2: Run baseline tests**

Run: `python3 -m pytest Tests/unit/test_preferences_routes.py Tests/unit/test_presets_routes.py Tests/unit/test_scheduler_routes.py -v --tb=short -q`
Expected: All tests PASS

**Step 3: Migrate preferences.py**

Add import at top of file:

```python
from webui.backend.lib.error_codes import (
    SERVER_ERROR,
    VALIDATION_ERROR,
    error_response,
)
```

Apply mapping to all 9 responses.

**Step 4: Migrate presets.py**

Add import at top of file:

```python
from webui.backend.lib.error_codes import (
    NOT_FOUND,
    SERVER_ERROR,
    VALIDATION_ERROR,
    error_response,
)
```

Apply mapping to all ~21 responses.

**Step 5: Migrate scheduler.py**

Add import at top of file:

```python
from webui.backend.lib.error_codes import (
    SERVER_ERROR,
    VALIDATION_ERROR,
    error_response,
)
```

Apply mapping to all 8 responses.

**Step 6: Run ruff**

Run: `ruff check webui/backend/routes/preferences.py webui/backend/routes/presets.py webui/backend/routes/scheduler.py && ruff format webui/backend/routes/preferences.py webui/backend/routes/presets.py webui/backend/routes/scheduler.py`
Expected: Clean

**Step 7: Run tests**

Run: `python3 -m pytest Tests/unit/test_preferences_routes.py Tests/unit/test_presets_routes.py Tests/unit/test_scheduler_routes.py -v --tb=short -q`
Expected: All tests PASS

**Step 8: Verify no remaining inline errors**

Run: `grep -n 'jsonify({"error"' webui/backend/routes/preferences.py webui/backend/routes/presets.py webui/backend/routes/scheduler.py`
Expected: No output

**Step 9: Final sweep — verify zero inline errors across ALL route files**

Run: `grep -rn 'jsonify({"error"' webui/backend/routes/`
Expected: No output (all 16 files migrated, scheduler_ui.py was already done)

**Step 10: Commit and PR**

```bash
git add webui/backend/routes/preferences.py webui/backend/routes/presets.py webui/backend/routes/scheduler.py
git commit -m "$(cat <<'EOF'
refactor: migrate misc routes to shared error codes (#414)

Migrate preferences.py (9), presets.py (~21), and scheduler.py (8)
error responses to use error_response() from the shared error codes
module.

Batch 7 of 7 for issue #414. All 16 route files now use the shared
error codes module.
EOF
)"
git push -u origin refactor/414-batch7-misc
gh pr create --base dev --title "refactor: migrate misc routes to shared error codes (#414)" --body "$(cat <<'EOF'
## Summary
- Migrate `preferences.py` (9), `presets.py` (~21), and `scheduler.py` (8) error responses to `error_response()`
- Batch 7 of 7 for #414 — completes the migration

## Test plan
- [x] All existing tests pass (`test_preferences_routes.py`, `test_presets_routes.py`, `test_scheduler_routes.py`)
- [x] No remaining inline `jsonify({"error"` patterns in ANY route file
- [x] ruff clean
- [x] Final sweep: `grep -rn 'jsonify({"error"' webui/backend/routes/` returns nothing
EOF
)"
```

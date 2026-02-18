# Tier 2 Frontend Infrastructure & Testing Design

**Date**: 2026-02-18
**Branch**: `test/tier2-frontend-infra`
**Issues**: #408, #406, #68

## Issue #408: Lock File Cleanup at Startup

### Problem
Two cleanup functions exist (`schedule_storage.cleanup_temp_files()`, `deployment_sidecar.cleanup_temp_files()`) but are never called. Orphaned `.lock` files accumulate in `CONFIG_DIR/schedules/` and `PHOTOS_DIR/` after crashes.

### Solution
Call both during Flask app initialization in `app.py` with try/except so failures don't block startup. Both use a 1-hour age threshold and are already tested.

### Files
- `webui/backend/app.py` — ~5 lines in initialization

---

## Issue #406: Frontend Testing Infrastructure

### Item 1: CI Pipeline
Create `.github/workflows/frontend-tests.yml`:
- Trigger on push/PR to `main` and `dev`
- Node.js setup, install deps
- 4 parallel test shards (scripts exist in package.json)
- Upload coverage report
- Fail on threshold violation

### Item 2: Coverage Threshold
Add to `vitest.config.js`:
- 70% statements, lines, functions
- 60% branches
- Conservative starting point, tighten later

### Item 3: Hook Tests
- `useSelection` (~3 tests): inside/outside provider, context value, error on missing provider
- `useValidateDraft` (~10-15 tests): debouncing, query caching, routine filtering, error states, reset

### Item 4: Page Test Audit
Quick pass through `src/pages/` to identify zero-coverage pages. Add basic tests if gaps found.

### Files
- `.github/workflows/frontend-tests.yml` (new)
- `webui/frontend/vitest.config.js` (modify)
- `webui/frontend/src/hooks/__tests__/useSelection.test.jsx` (new)
- `webui/frontend/src/hooks/__tests__/useValidateDraft.test.jsx` (new)

---

## Issue #68: SavePresetModal Tests

### Problem
`SavePresetModal.jsx` is the only preset component without a test file.

### Solution
~10-15 tests covering: render states, name validation, description field, workflow selector, save behavior, settings validation errors, close/cancel.

### Files
- `webui/frontend/src/components/__tests__/SavePresetModal.test.jsx` (new)

---

## Branch Strategy

Single branch `test/tier2-frontend-infra`, 5-6 commits:

1. `fix(backend): wire up orphaned lock cleanup at startup (#408)`
2. `ci(frontend): add GitHub Actions workflow with 4-shard parallelization (#406)`
3. `test(frontend): add coverage threshold to vitest config (#406)`
4. `test(frontend): add tests for useSelection and useValidateDraft hooks (#406)`
5. `test(frontend): audit page components for coverage gaps (#406)` (if gaps found)
6. `test(frontend): add tests for SavePresetModal (#68)`

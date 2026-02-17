# Tier 1 Quick Wins Design

**Date**: 2026-02-18
**Branch**: `perf/tier1-quick-wins`
**Issues**: #426, #386, #387

## Issue #426: Focus Validation (Auto-correct + Warning)

### Problem
Direct API calls can write conflicting `AutoCalibration=1, AfMode=2` to `camera_settings.csv`. The frontend prevents this via a unified dropdown, and `TakePhoto.py` auto-corrects at runtime, but the CSV retains the conflicting state.

### Solution
Add cross-field validation in `update_camera_settings()` (`routes/camera.py`, ~line 706). When `AutoCalibration=1` and `AfMode != 0`, silently correct `AfMode` to `0` and include a warning in the response.

### Response format
```json
{
  "success": true,
  "warnings": ["AutoCalibration enabled: AfMode auto-corrected to Manual (0)"]
}
```

### Files
- `webui/backend/routes/camera.py` — ~15 lines after individual validation
- `Tests/unit/` — 3-4 new test cases for the cross-field validation

---

## Issue #386: Conflict Detection Sort-and-Sweep

### Problem
`detect_conflicts()` in `schedule_conflict.py` has O(n^2 x m^2) complexity from nested execution pairs x nested resource usage pairs.

### Solution
Replace with sort-and-sweep:

1. **Sort** executions by `start_time` — O(n log n)
2. **Sweep** with active set: only compare while `exec2.start < exec1.end` — O(n + k) where k = actual overlaps
3. **Resource index**: Pre-build `resource_name -> [usage]` dict per execution, compare only matching resources — O(m) instead of O(m^2)

### Invariant
Identical output for all inputs. All 98 existing tests must pass unchanged.

### Files
- `webui/backend/lib/schedule_conflict.py` — refactor `detect_conflicts()` (~74 lines)
- `Tests/unit/test_schedule_conflict_lib.py` — add perf edge case tests

---

## Issue #387: WeekHourlyTimeline Map-Based Lookups + Tests

### Problem
Three O(n*m) patterns in `weekTimelineUtils.js`: `.find()` inside `.forEach()`, `indexOf()` inside loop.

### Solution
1. **`buildExecutionConflictsMap()`**: Pre-build two `Map` lookups (by `pattern_id`, by `start_time`). O(n + m) total.
2. **`groupExecutionsByDayAndHour()`**: Replace `indexOf()` on `dateKeyList` with `Map<dateKey, index>` for O(1) lookup.
3. **`getConflictsForDay()`**: Already O(n), consider memoization if called repeatedly.
4. **New test file**: Comprehensive tests for all 3 functions.

### Files
- `webui/frontend/src/components/scheduler/WeekHourlyTimeline/weekTimelineUtils.js`
- `webui/frontend/src/components/scheduler/WeekHourlyTimeline/__tests__/weekTimelineUtils.test.js` (new)

---

## Branch Strategy

Single branch `perf/tier1-quick-wins` with 3 commits:

1. `fix(camera): auto-correct conflicting AutoCalibration+AfMode combinations (#426)`
2. `perf(scheduler): optimize O(n^4) conflict detection with sort-and-sweep (#386)`
3. `perf(frontend): optimize WeekHourlyTimeline with Map lookups, add tests (#387)`

# Tier 1 Quick Wins Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ship three low-risk improvements — focus setting validation (#426), conflict detection perf (#386), and WeekHourlyTimeline perf + tests (#387).

**Architecture:** Three independent changes on one branch. Each is a pure backend or frontend change with no cross-cutting dependencies. All are refactors or additions to existing code with existing test infrastructure.

**Tech Stack:** Python/Flask (backend), JavaScript/React/Vitest (frontend), pytest (backend tests)

---

## Task 1: Focus Validation — Write Failing Tests (#426)

**Files:**
- Test: `Tests/unit/test_camera_routes.py`

Add tests to the existing `TestPostCameraSettings` class. The test client and `temp_camera_settings` fixture are already available (CSRF disabled in test mode).

**Step 1: Write failing tests**

Add to `Tests/unit/test_camera_routes.py`, inside `class TestPostCameraSettings`:

```python
def test_post_settings_autocorrects_conflicting_focus_mode(self, client, temp_camera_settings):
    """AutoCalibration=1 with AfMode!=0 should auto-correct AfMode to 0 with warning (#426)."""
    initial_csv = "SETTING,VALUE,DETAILS\nAutoCalibration,0,\nAfMode,0,\n"
    temp_camera_settings.write_text(initial_csv)

    # Send conflicting combination: AutoCalibration=1 + AfMode=2
    response = client.post(
        "/api/camera/settings",
        json={"AutoCalibration": "1", "AfMode": "2"},
        content_type="application/json",
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "warnings" in data
    assert any("AfMode" in w for w in data["warnings"])

    # Verify AfMode was corrected to 0 in the CSV
    content = temp_camera_settings.read_text()
    assert "AutoCalibration,1" in content
    assert "AfMode,0" in content

def test_post_settings_no_warning_for_valid_focus_mode(self, client, temp_camera_settings):
    """Valid combinations should not produce warnings (#426)."""
    initial_csv = "SETTING,VALUE,DETAILS\nAutoCalibration,0,\nAfMode,0,\n"
    temp_camera_settings.write_text(initial_csv)

    # AutoCalibration=1 + AfMode=0 is valid
    response = client.post(
        "/api/camera/settings",
        json={"AutoCalibration": "1", "AfMode": "0"},
        content_type="application/json",
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data.get("warnings", []) == []

def test_post_settings_autocorrects_afmode_1_with_autocalibration(self, client, temp_camera_settings):
    """AfMode=1 (Single) should also be corrected when AutoCalibration=1 (#426)."""
    initial_csv = "SETTING,VALUE,DETAILS\nAutoCalibration,0,\nAfMode,0,\n"
    temp_camera_settings.write_text(initial_csv)

    response = client.post(
        "/api/camera/settings",
        json={"AutoCalibration": "1", "AfMode": "1"},
        content_type="application/json",
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert len(data.get("warnings", [])) > 0

    content = temp_camera_settings.read_text()
    assert "AfMode,0" in content

def test_post_settings_no_autocorrect_when_autocalibration_off(self, client, temp_camera_settings):
    """AfMode=2 without AutoCalibration=1 should not be corrected (#426)."""
    initial_csv = "SETTING,VALUE,DETAILS\nAutoCalibration,0,\nAfMode,0,\n"
    temp_camera_settings.write_text(initial_csv)

    response = client.post(
        "/api/camera/settings",
        json={"AfMode": "2"},
        content_type="application/json",
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data.get("warnings", []) == []

    content = temp_camera_settings.read_text()
    assert "AfMode,2" in content
```

**Step 2: Run tests to verify they fail**

Run: `pytest Tests/unit/test_camera_routes.py::TestPostCameraSettings::test_post_settings_autocorrects_conflicting_focus_mode -v`
Expected: FAIL — response has no `warnings` key

---

## Task 2: Focus Validation — Implement Auto-correct (#426)

**Files:**
- Modify: `webui/backend/routes/camera.py:706-745`

**Step 1: Add cross-field validation after individual validation**

In `update_camera_settings()`, after the individual validation loop (line 706) and before the CSV read (line 708), add:

```python
        # Cross-field validation: auto-correct conflicting focus modes (#426)
        # When AutoCalibration=1, AfMode must be 0 (Manual) — TakePhoto.py
        # enforces this at runtime, but we correct it at save time too.
        warnings = []
        auto_cal = str(new_settings.get("AutoCalibration", "")).strip()
        af_mode = str(new_settings.get("AfMode", "")).strip()
        if auto_cal == "1" and af_mode not in ("", "0"):
            new_settings["AfMode"] = "0"
            warnings.append(
                f"AutoCalibration enabled: AfMode auto-corrected from {af_mode} to Manual (0)"
            )
```

**Step 2: Update the success response to include warnings**

Change line 745 from:

```python
        return jsonify({"success": True})
```

to:

```python
        response_data = {"success": True}
        if warnings:
            response_data["warnings"] = warnings
        return jsonify(response_data)
```

**Step 3: Run tests to verify they pass**

Run: `pytest Tests/unit/test_camera_routes.py::TestPostCameraSettings -v -k "autocorrect or no_warning or no_autocorrect"`
Expected: All 4 new tests PASS

**Step 4: Run full camera routes test file**

Run: `pytest Tests/unit/test_camera_routes.py -v`
Expected: All existing tests still PASS (no regressions)

**Step 5: Lint**

Run: `ruff check webui/backend/routes/camera.py Tests/unit/test_camera_routes.py`
Expected: No errors

**Step 6: Commit**

```bash
git add webui/backend/routes/camera.py Tests/unit/test_camera_routes.py
git commit -m "fix(camera): auto-correct conflicting AutoCalibration+AfMode combinations (#426)"
```

---

## Task 3: Conflict Detection — Write Perf Edge Case Tests (#386)

**Files:**
- Test: `Tests/unit/test_schedule_conflict_lib.py`

**Step 1: Write tests that exercise large execution counts**

Add at the end of the test file:

```python
class TestDetectConflictsPerformance:
    """Performance tests for detect_conflicts with large datasets (#386)."""

    def _make_schedule_with_routines(self, n_routines):
        """Create a schedule with n routines that will generate overlapping executions."""
        from webui.backend.lib.schedule_schema import (
            Action,
            FixedTimeTrigger,
            Routine,
            Schedule,
        )

        routines = []
        for i in range(n_routines):
            routine = Routine(
                routine_id=f"routine_{i}",
                name=f"Routine {i}",
                trigger=FixedTimeTrigger(time="08:00"),
                actions=[
                    Action(type="takephoto", params={"count": 1}),
                ],
                enabled=True,
            )
            routines.append(routine)
        return Schedule(
            schedule_id="perf_test",
            name="Perf Test",
            routines=routines,
        )

    def test_detect_conflicts_100_executions_under_1s(self):
        """100 overlapping executions should complete well under 1 second."""
        import time as time_mod

        from webui.backend.lib.schedule_conflict import (
            RoutineExecution,
            ResourceUsage,
            detect_conflicts,
        )
        from webui.backend.lib.schedule_schema import Schedule

        # Create 100 overlapping executions with 2 resource usages each
        executions = []
        base = datetime(2025, 1, 1, 8, 0, 0)
        for i in range(100):
            start = base + timedelta(minutes=i)
            end = start + timedelta(minutes=10)  # All overlap with neighbors
            executions.append(
                RoutineExecution(
                    routine_id=f"r{i}",
                    routine_name=f"Routine {i}",
                    start_time=start,
                    end_time=end,
                    resource_usages=[
                        ResourceUsage(
                            resource_type="camera",
                            resource_name="camera",
                            start_time=start,
                            end_time=end,
                            routine_id=f"r{i}",
                            action_index=0,
                        ),
                        ResourceUsage(
                            resource_type="attract",
                            resource_name="attract_on",
                            start_time=start,
                            end_time=end,
                            routine_id=f"r{i}",
                            action_index=1,
                        ),
                    ],
                )
            )

        schedule = Schedule(
            schedule_id="perf", name="Perf", routines=[]
        )

        start_t = time_mod.monotonic()
        result = detect_conflicts(
            schedule,
            executions=executions,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 1),
        )
        elapsed = time_mod.monotonic() - start_t

        assert elapsed < 1.0, f"detect_conflicts took {elapsed:.2f}s for 100 executions"
        assert result.total_executions == 100
        assert len(result.conflicts) > 0  # Should find overlaps

    def test_detect_conflicts_no_overlaps_fast(self):
        """Non-overlapping executions should be very fast (no pairs to check)."""
        import time as time_mod

        from webui.backend.lib.schedule_conflict import (
            RoutineExecution,
            ResourceUsage,
            detect_conflicts,
        )
        from webui.backend.lib.schedule_schema import Schedule

        # 200 non-overlapping executions (each 1 min, 5 min apart)
        executions = []
        base = datetime(2025, 1, 1, 0, 0, 0)
        for i in range(200):
            start = base + timedelta(minutes=i * 5)
            end = start + timedelta(minutes=1)
            executions.append(
                RoutineExecution(
                    routine_id=f"r{i}",
                    routine_name=f"Routine {i}",
                    start_time=start,
                    end_time=end,
                    resource_usages=[
                        ResourceUsage(
                            resource_type="camera",
                            resource_name="camera",
                            start_time=start,
                            end_time=end,
                            routine_id=f"r{i}",
                            action_index=0,
                        ),
                    ],
                )
            )

        schedule = Schedule(schedule_id="perf", name="Perf", routines=[])

        start_t = time_mod.monotonic()
        result = detect_conflicts(
            schedule,
            executions=executions,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 1),
        )
        elapsed = time_mod.monotonic() - start_t

        assert elapsed < 0.5, f"Non-overlapping took {elapsed:.2f}s for 200 executions"
        assert len(result.conflicts) == 0
```

**Step 2: Run to verify tests pass (they should pass on current code too, just slowly)**

Run: `pytest Tests/unit/test_schedule_conflict_lib.py::TestDetectConflictsPerformance -v`
Expected: PASS (current code handles 100 execs, just slower than optimal)

---

## Task 4: Conflict Detection — Implement Sort-and-Sweep (#386)

**Files:**
- Modify: `webui/backend/lib/schedule_conflict.py:838-963`

**Step 1: Replace the main detection loop**

Replace the body of `detect_conflicts()` from line 852 (`conflicts: list[Conflict] = []`) through line 945 (end of instant_actions block) with:

```python
    conflicts: list[Conflict] = []

    # Sort executions by start_time for sweep-line algorithm
    # (generate_routine_executions already sorts, but be defensive)
    sorted_execs = sorted(executions, key=lambda e: e.start_time)

    # Phase 1: Sweep-line for time overlaps + resource contention
    # For each execution, only compare against executions that could overlap
    # (those whose start_time < current end_time). O(n log n + n*k) where
    # k = average overlap count, vs previous O(n^2).
    for i, exec1 in enumerate(sorted_execs):
        # Only check subsequent executions that start before exec1 ends
        # Skip zero-duration executions here (handled in Phase 2)
        if exec1.start_time == exec1.end_time:
            continue

        for j in range(i + 1, len(sorted_execs)):
            exec2 = sorted_execs[j]

            # Since sorted by start_time, once exec2 starts after exec1 ends,
            # no further executions can overlap with exec1
            if exec2.start_time >= exec1.end_time:
                break

            # Skip zero-duration in this phase
            if exec2.start_time == exec2.end_time:
                continue

            overlaps, overlap_start, overlap_end = check_time_overlap(exec1, exec2)

            if overlaps and overlap_start and overlap_end:
                time_conflict = Conflict(
                    conflict_type=CONFLICT_TIME_OVERLAP,
                    event1_id=exec1.routine_id,
                    event1_name=exec1.routine_name,
                    event2_id=exec2.routine_id,
                    event2_name=exec2.routine_name,
                    start_time=overlap_start,
                    end_time=overlap_end,
                    message=(
                        f"Routines '{exec1.routine_name}' and '{exec2.routine_name}' "
                        f"overlap from {overlap_start.strftime('%H:%M:%S')} to "
                        f"{overlap_end.strftime('%H:%M:%S')}"
                    ),
                    suggested_resolution=(
                        "Adjust routine offsets or increase interval between triggers"
                    ),
                    severity=SEVERITY_WARNING,
                )
                conflicts.append(time_conflict)

                # Resource contention: index by resource_type for O(m) comparison
                # instead of O(m^2) all-pairs
                resource_index: dict[str, list[ResourceUsage]] = defaultdict(list)
                for usage in exec2.resource_usages:
                    resource_index[usage.resource_type].append(usage)

                for usage1 in exec1.resource_usages:
                    # Only compare with usages of matching resource type
                    candidates = resource_index.get(usage1.resource_type, [])
                    # Also check GPIO cross-type conflicts (attract vs flash)
                    if usage1.resource_type in GPIO_RESOURCES:
                        for gpio_type in GPIO_RESOURCES:
                            if gpio_type != usage1.resource_type:
                                candidates = candidates + resource_index.get(gpio_type, [])

                    for usage2 in candidates:
                        contends, conflict_type = check_resource_contention(usage1, usage2)
                        if contends:
                            resource_conflict = Conflict(
                                conflict_type=conflict_type,
                                event1_id=exec1.routine_id,
                                event1_name=exec1.routine_name,
                                event2_id=exec2.routine_id,
                                event2_name=exec2.routine_name,
                                start_time=max(usage1.start_time, usage2.start_time),
                                end_time=min(usage1.end_time, usage2.end_time),
                                resource=usage1.resource_type,
                                message=_generate_conflict_message(conflict_type, usage1, usage2),
                                suggested_resolution=_generate_resolution(
                                    conflict_type, usage1, usage2
                                ),
                                severity=SEVERITY_ERROR,
                            )
                            conflicts.append(resource_conflict)

    # Phase 2: Instant action collisions (zero-duration at same time)
    # These are skipped by check_time_overlap() but still cause resource conflicts
    instant_actions = [e for e in sorted_execs if e.start_time == e.end_time]

    if instant_actions:
        time_groups: dict[datetime, list[RoutineExecution]] = defaultdict(list)
        for execution in instant_actions:
            time_groups[execution.start_time].append(execution)

        for collision_time, colliding_execs in time_groups.items():
            if len(colliding_execs) < 2:
                continue

            for i, exec1 in enumerate(colliding_execs):
                for exec2 in colliding_execs[i + 1 :]:
                    # Index resources for O(m) comparison
                    resource_index: dict[str, list[ResourceUsage]] = defaultdict(list)
                    for usage in exec2.resource_usages:
                        resource_index[usage.resource_type].append(usage)

                    for usage1 in exec1.resource_usages:
                        candidates = resource_index.get(usage1.resource_type, [])
                        if usage1.resource_type in GPIO_RESOURCES:
                            for gpio_type in GPIO_RESOURCES:
                                if gpio_type != usage1.resource_type:
                                    candidates = candidates + resource_index.get(gpio_type, [])

                        for usage2 in candidates:
                            contends, conflict_type = check_resource_contention(usage1, usage2)
                            if contends:
                                instant_conflict = Conflict(
                                    conflict_type=conflict_type,
                                    event1_id=exec1.routine_id,
                                    event1_name=exec1.routine_name,
                                    event2_id=exec2.routine_id,
                                    event2_name=exec2.routine_name,
                                    start_time=collision_time,
                                    end_time=collision_time,
                                    resource=usage1.resource_type,
                                    message=(
                                        f"'{exec1.routine_name}' and '{exec2.routine_name}' "
                                        f"both use {usage1.resource_type} at "
                                        f"{collision_time.strftime('%H:%M:%S')}"
                                    ),
                                    suggested_resolution=(
                                        "Stagger trigger times or combine into single routine"
                                    ),
                                    severity=SEVERITY_ERROR,
                                )
                                conflicts.append(instant_conflict)
```

**Step 2: Run ALL existing tests**

Run: `pytest Tests/unit/test_schedule_conflict_lib.py -v`
Expected: All 98 existing tests + 2 new perf tests PASS

**Step 3: Lint**

Run: `ruff check webui/backend/lib/schedule_conflict.py`
Expected: No errors

**Step 4: Commit**

```bash
git add webui/backend/lib/schedule_conflict.py Tests/unit/test_schedule_conflict_lib.py
git commit -m "perf(scheduler): optimize conflict detection with sort-and-sweep (#386)"
```

---

## Task 5: WeekHourlyTimeline — Write Tests (#387)

**Files:**
- Create: `webui/frontend/src/components/scheduler/WeekHourlyTimeline/__tests__/weekTimelineUtils.test.js`

**Step 1: Write comprehensive tests for the 3 target functions**

Follow the pattern from `DayTimeline/__tests__/dayTimelineUtils.test.js` — use local time strings (no Z suffix) for timezone-agnostic testing.

```javascript
/**
 * Tests for WeekHourlyTimeline utility functions (#387)
 *
 * TIMEZONE HANDLING: Uses local time (no Z suffix) for timezone-agnostic tests.
 */

import { describe, it, expect } from 'vitest'
import {
  groupExecutionsByDayAndHour,
  getConflictsForDay,
  buildExecutionConflictsMap,
} from '../weekTimelineUtils'

// Helper to create week dates starting Monday
function makeWeekDates(startDateStr) {
  const dates = []
  const start = new Date(startDateStr + 'T00:00:00')
  for (let i = 0; i < 7; i++) {
    const d = new Date(start)
    d.setDate(d.getDate() + i)
    dates.push(d)
  }
  return dates
}

describe('weekTimelineUtils', () => {
  describe('groupExecutionsByDayAndHour', () => {
    const weekDates = makeWeekDates('2025-01-13') // Mon-Sun

    it('returns empty object for null/undefined executions', () => {
      expect(groupExecutionsByDayAndHour(null, weekDates)).toEqual({})
      expect(groupExecutionsByDayAndHour(undefined, weekDates)).toEqual({})
    })

    it('returns empty day buckets for empty array', () => {
      const result = groupExecutionsByDayAndHour([], weekDates)
      expect(Object.keys(result)).toHaveLength(7)
      // Each day should have empty hours
      Object.values(result).forEach(hours => {
        expect(Object.keys(hours)).toHaveLength(0)
      })
    })

    it('groups single execution by date and hour', () => {
      const execs = [
        { pattern_id: 'p1', start_time: '2025-01-15T18:30:00' },
      ]
      const result = groupExecutionsByDayAndHour(execs, weekDates)
      expect(result['2025-01-15'][18]).toHaveLength(1)
      expect(result['2025-01-15'][18][0].pattern_id).toBe('p1')
    })

    it('groups multiple executions in same hour', () => {
      const execs = [
        { pattern_id: 'p1', start_time: '2025-01-15T18:00:00' },
        { pattern_id: 'p2', start_time: '2025-01-15T18:30:00' },
      ]
      const result = groupExecutionsByDayAndHour(execs, weekDates)
      expect(result['2025-01-15'][18]).toHaveLength(2)
    })

    it('groups executions across different days', () => {
      const execs = [
        { pattern_id: 'p1', start_time: '2025-01-13T10:00:00' },
        { pattern_id: 'p2', start_time: '2025-01-14T10:00:00' },
      ]
      const result = groupExecutionsByDayAndHour(execs, weekDates)
      expect(result['2025-01-13'][10]).toHaveLength(1)
      expect(result['2025-01-14'][10]).toHaveLength(1)
    })

    it('skips executions outside the week', () => {
      const execs = [
        { pattern_id: 'p1', start_time: '2025-01-12T10:00:00' }, // Sunday before
        { pattern_id: 'p2', start_time: '2025-01-20T10:00:00' }, // Monday after
      ]
      const result = groupExecutionsByDayAndHour(execs, weekDates)
      Object.values(result).forEach(hours => {
        expect(Object.keys(hours)).toHaveLength(0)
      })
    })

    it('deduplicates same pattern_id at same time', () => {
      const execs = [
        { pattern_id: 'p1', start_time: '2025-01-15T18:00:00' },
        { pattern_id: 'p1', start_time: '2025-01-15T18:00:00' },
      ]
      const result = groupExecutionsByDayAndHour(execs, weekDates)
      expect(result['2025-01-15'][18]).toHaveLength(1)
    })

    it('skips executions with missing start_time', () => {
      const execs = [
        { pattern_id: 'p1' },
        { pattern_id: 'p2', start_time: null },
      ]
      const result = groupExecutionsByDayAndHour(execs, weekDates)
      Object.values(result).forEach(hours => {
        expect(Object.keys(hours)).toHaveLength(0)
      })
    })

    describe('overnight schedules', () => {
      it('shifts post-midnight executions to previous day', () => {
        const cycleInfo = { start_hour: 21, end_hour: 5 }
        const execs = [
          { pattern_id: 'p1', start_time: '2025-01-14T02:00:00' }, // Should go to Jan 13
        ]
        const result = groupExecutionsByDayAndHour(execs, weekDates, cycleInfo)
        expect(result['2025-01-13'][2]).toHaveLength(1)
        expect(result['2025-01-14'][2] || []).toHaveLength(0)
      })

      it('skips post-midnight on first day of week (belongs to previous week)', () => {
        const cycleInfo = { start_hour: 21, end_hour: 5 }
        const execs = [
          { pattern_id: 'p1', start_time: '2025-01-13T03:00:00' }, // First day, skip
        ]
        const result = groupExecutionsByDayAndHour(execs, weekDates, cycleInfo)
        expect(result['2025-01-13'][3] || []).toHaveLength(0)
      })

      it('does not shift executions outside overnight window', () => {
        const cycleInfo = { start_hour: 21, end_hour: 5 }
        const execs = [
          { pattern_id: 'p1', start_time: '2025-01-14T22:00:00' }, // After start, not shifted
        ]
        const result = groupExecutionsByDayAndHour(execs, weekDates, cycleInfo)
        expect(result['2025-01-14'][22]).toHaveLength(1)
      })
    })
  })

  describe('getConflictsForDay', () => {
    it('returns empty array for null/undefined conflicts', () => {
      expect(getConflictsForDay(null, '2025-01-15')).toEqual([])
      expect(getConflictsForDay(undefined, '2025-01-15')).toEqual([])
    })

    it('returns empty array for null dateKey', () => {
      expect(getConflictsForDay([{ start_time: '2025-01-15T10:00:00' }], null)).toEqual([])
    })

    it('returns empty array for non-array conflicts', () => {
      expect(getConflictsForDay('not-array', '2025-01-15')).toEqual([])
    })

    it('filters conflicts matching the date', () => {
      const conflicts = [
        { start_time: '2025-01-15T10:00:00', id: 'c1' },
        { start_time: '2025-01-16T10:00:00', id: 'c2' },
        { start_time: '2025-01-15T22:00:00', id: 'c3' },
      ]
      const result = getConflictsForDay(conflicts, '2025-01-15')
      expect(result).toHaveLength(2)
      expect(result.map(c => c.id)).toEqual(['c1', 'c3'])
    })

    it('skips conflicts with missing start_time', () => {
      const conflicts = [
        { id: 'c1' },
        { start_time: null, id: 'c2' },
        { start_time: '2025-01-15T10:00:00', id: 'c3' },
      ]
      const result = getConflictsForDay(conflicts, '2025-01-15')
      expect(result).toHaveLength(1)
    })
  })

  describe('buildExecutionConflictsMap', () => {
    it('returns empty object for null inputs', () => {
      expect(buildExecutionConflictsMap(null, [])).toEqual({})
      expect(buildExecutionConflictsMap([], null)).toEqual({})
    })

    it('maps execution to conflict by event1_id', () => {
      const execs = [{ pattern_id: 'r1', start_time: '2025-01-15T10:00:00' }]
      const conflicts = [{ event1_id: 'r1', event2_id: 'r2', start_time: '2025-01-15T10:00:00' }]
      const result = buildExecutionConflictsMap(execs, conflicts)
      expect(result['r1']).toBeDefined()
      expect(result['r1'].event1_id).toBe('r1')
    })

    it('maps execution to conflict by event2_id', () => {
      const execs = [{ pattern_id: 'r2', start_time: '2025-01-15T10:00:00' }]
      const conflicts = [{ event1_id: 'r1', event2_id: 'r2', start_time: '2025-01-15T10:00:00' }]
      const result = buildExecutionConflictsMap(execs, conflicts)
      expect(result['r2']).toBeDefined()
    })

    it('maps execution to conflict by start_time', () => {
      const execs = [{ pattern_id: 'r3', start_time: '2025-01-15T10:00:00' }]
      const conflicts = [{ event1_id: 'r1', event2_id: 'r2', start_time: '2025-01-15T10:00:00' }]
      const result = buildExecutionConflictsMap(execs, conflicts)
      expect(result['r3']).toBeDefined()
    })

    it('does not map executions with no matching conflict', () => {
      const execs = [{ pattern_id: 'r5', start_time: '2025-01-15T12:00:00' }]
      const conflicts = [{ event1_id: 'r1', event2_id: 'r2', start_time: '2025-01-15T10:00:00' }]
      const result = buildExecutionConflictsMap(execs, conflicts)
      expect(result['r5']).toBeUndefined()
    })

    it('handles multiple executions with same conflict', () => {
      const execs = [
        { pattern_id: 'r1', start_time: '2025-01-15T10:00:00' },
        { pattern_id: 'r2', start_time: '2025-01-15T10:00:00' },
      ]
      const conflicts = [{ event1_id: 'r1', event2_id: 'r2', start_time: '2025-01-15T10:00:00' }]
      const result = buildExecutionConflictsMap(execs, conflicts)
      expect(result['r1']).toBeDefined()
      expect(result['r2']).toBeDefined()
    })
  })
})
```

**Step 2: Run tests to verify they pass on current code**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/WeekHourlyTimeline/__tests__/weekTimelineUtils.test.js`
Expected: All tests PASS (they test current behavior)

---

## Task 6: WeekHourlyTimeline — Implement Map Optimizations (#387)

**Files:**
- Modify: `webui/frontend/src/components/scheduler/WeekHourlyTimeline/weekTimelineUtils.js`

**Step 1: Optimize `groupExecutionsByDayAndHour` — replace indexOf with Map**

Replace line 108:
```javascript
  const dateKeyList = weekDates.map(d => getLocalDateKey(d))
```

With:
```javascript
  const dateKeyList = weekDates.map(d => getLocalDateKey(d))
  const dateKeyIndex = new Map(dateKeyList.map((key, idx) => [key, idx]))
```

Replace lines 136-143:
```javascript
      const dateIndex = dateKeyList.indexOf(dateKey)
      if (dateIndex > 0) {
        // Shift to previous day
        dateKey = dateKeyList[dateIndex - 1]
      } else if (dateIndex === 0) {
        // First day - skip post-midnight executions (they belong to previous week)
        return
      }
```

With:
```javascript
      const dateIndex = dateKeyIndex.get(dateKey)
      if (dateIndex === undefined) return
      if (dateIndex > 0) {
        dateKey = dateKeyList[dateIndex - 1]
      } else {
        // First day - skip post-midnight executions (they belong to previous week)
        return
      }
```

**Step 2: Optimize `buildExecutionConflictsMap` — pre-index conflicts**

Replace lines 190-205:

```javascript
export function buildExecutionConflictsMap(executions, conflicts) {
  if (!executions || !conflicts) return {}

  const map = {}
  executions.forEach(execution => {
    const conflict = conflicts.find(c =>
      c.event1_id === execution.pattern_id ||
      c.event2_id === execution.pattern_id ||
      c.start_time === execution.start_time
    )
    if (conflict) {
      map[execution.pattern_id] = conflict
    }
  })
  return map
}
```

With:

```javascript
export function buildExecutionConflictsMap(executions, conflicts) {
  if (!executions || !conflicts) return {}

  // Pre-index conflicts for O(1) lookup instead of O(m) find per execution
  const byEvent1 = new Map()
  const byEvent2 = new Map()
  const byStartTime = new Map()
  conflicts.forEach(c => {
    if (c.event1_id && !byEvent1.has(c.event1_id)) byEvent1.set(c.event1_id, c)
    if (c.event2_id && !byEvent2.has(c.event2_id)) byEvent2.set(c.event2_id, c)
    if (c.start_time && !byStartTime.has(c.start_time)) byStartTime.set(c.start_time, c)
  })

  const map = {}
  executions.forEach(execution => {
    const conflict =
      byEvent1.get(execution.pattern_id) ||
      byEvent2.get(execution.pattern_id) ||
      byStartTime.get(execution.start_time)
    if (conflict) {
      map[execution.pattern_id] = conflict
    }
  })
  return map
}
```

**Step 3: Run tests**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/WeekHourlyTimeline/__tests__/weekTimelineUtils.test.js`
Expected: All tests PASS

**Step 4: Run full scheduler test suite to check for regressions**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/`
Expected: All scheduler tests PASS

**Step 5: Lint**

Run: `cd webui/frontend && npx eslint src/components/scheduler/WeekHourlyTimeline/weekTimelineUtils.js`
Expected: No errors (or only pre-existing warnings)

**Step 6: Commit**

```bash
git add webui/frontend/src/components/scheduler/WeekHourlyTimeline/weekTimelineUtils.js \
        webui/frontend/src/components/scheduler/WeekHourlyTimeline/__tests__/weekTimelineUtils.test.js
git commit -m "perf(frontend): optimize WeekHourlyTimeline with Map lookups, add tests (#387)"
```

---

## Task 7: Final Verification

**Step 1: Run all backend tests touched**

Run: `pytest Tests/unit/test_camera_routes.py Tests/unit/test_schedule_conflict_lib.py -v`
Expected: All PASS

**Step 2: Run all frontend scheduler tests**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/`
Expected: All PASS

**Step 3: Lint everything**

Run: `ruff check webui/backend/routes/camera.py webui/backend/lib/schedule_conflict.py && cd webui/frontend && npx eslint src/components/scheduler/WeekHourlyTimeline/`
Expected: Clean

**Step 4: Verify git log**

Run: `git log --oneline -3`
Expected:
```
abc1234 perf(frontend): optimize WeekHourlyTimeline with Map lookups, add tests (#387)
def5678 perf(scheduler): optimize conflict detection with sort-and-sweep (#386)
ghi9012 fix(camera): auto-correct conflicting AutoCalibration+AfMode combinations (#426)
```

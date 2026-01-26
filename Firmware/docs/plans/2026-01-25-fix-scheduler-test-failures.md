# Fix Scheduler Test Failures Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 7 failing CI tests related to scheduler schema migration and test fixtures.

**Architecture:** The scheduler has migrated from Schema 2.0 (pattern-based) to Schema 3.0 (routine-based). Most failures stem from: (1) asymmetric serialization in PreviewExecution, (2) missing builtin schedule files, (3) test mock fixtures not providing proper `to_dict()` methods, and (4) cron validation accepting 6-field expressions.

**Tech Stack:** Python 3.11, pytest, Flask, JSON schema files

---

## Summary of Failures

| Test | Root Cause | Fix |
|------|------------|-----|
| `test_preview_execution_to_dict` | Test expects `routine_id` but `to_dict()` returns `pattern_id` | Update test to expect `pattern_id` (API contract) |
| `test_preview_result_roundtrip` | `from_dict()` expects `routine_id` but receives `pattern_id` | Fix `from_dict()` to accept both field names |
| `test_all_required_220_schedules_exist` | Missing 5 builtin schedule files | Create the 5 JSON files |
| `test_list_schedules_with_data` | Mock routines lack `to_dict()` method | Fix `schedule_factory` fixture |
| `test_list_schedules_active_only` | Mock routines lack `to_dict()` method | Fix `schedule_factory` fixture |
| `test_list_builtin_schedules_with_data` | Mock routines lack `to_dict()` method | Fix `schedule_factory` fixture |
| `test_validate_cron_invalid_patterns` | `is_valid_expression()` accepts 6-field cron | Add field count validation |

---

## Task 1: Fix PreviewExecution Serialization Roundtrip

**Files:**
- Modify: `webui/backend/lib/schedule_preview.py:156-166`
- Test: `Tests/unit/test_schedule_preview.py`

**Step 1: Update `from_dict()` to accept both field name conventions**

The `to_dict()` method returns `pattern_id`/`pattern_name` for API backward compatibility.
The `from_dict()` must accept BOTH conventions for proper roundtrip serialization.

```python
# In schedule_preview.py, replace lines 156-166 with:
@classmethod
def from_dict(cls, data: dict) -> "PreviewExecution":
    """Deserialize from dictionary.

    Accepts both old (pattern_id/pattern_name) and new (routine_id/routine_name)
    field names for backward compatibility with API responses.
    """
    return cls(
        start_time=datetime.fromisoformat(data["start_time"]),
        end_time=datetime.fromisoformat(data["end_time"]),
        routine_id=data.get("routine_id") or data.get("pattern_id", ""),
        routine_name=data.get("routine_name") or data.get("pattern_name", ""),
        trigger_info=data["trigger_info"],
        actions=[ActionExecution.from_dict(a) for a in data.get("actions", [])],
    )
```

**Step 2: Update test to expect API contract field names**

The test `test_preview_execution_to_dict` expects `routine_id` but API returns `pattern_id`.
Update test to match the actual API contract.

```python
# In test_schedule_preview.py, around line 358, change:
#   assert result["routine_id"] == "uv-cycle"
#   assert result["routine_name"] == "UV Capture Cycle"
# To:
    assert result["pattern_id"] == "uv-cycle"
    assert result["pattern_name"] == "UV Capture Cycle"
```

**Step 3: Run tests to verify fixes**

```bash
SECRET_KEY=test MOTHBOX_ENV=test pytest Tests/unit/test_schedule_preview.py::TestPreviewExecution::test_preview_execution_to_dict Tests/unit/test_schedule_preview.py::TestPreviewResult::test_preview_result_roundtrip -v
```

Expected: PASS

**Step 4: Commit**

```bash
git add webui/backend/lib/schedule_preview.py Tests/unit/test_schedule_preview.py
git commit -m "fix(preview): support bidirectional serialization for pattern_id/routine_id"
```

---

## Task 2: Fix Test Mock Fixture for Routine Serialization

**Files:**
- Modify: `Tests/unit/test_scheduler_ui_routes.py:109-136`

**Step 1: Update schedule_factory to create routines with working `to_dict()`**

The issue is that `schedule.routines` contains MagicMock objects, and when the route calls
`[r.to_dict() for r in schedule.routines]`, the MagicMock.to_dict() returns another MagicMock
which is not JSON serializable.

```python
# In test_scheduler_ui_routes.py, replace the schedule_factory fixture (lines 98-138) with:
@pytest.fixture
def schedule_factory():
    """
    Factory fixture for creating mock schedule objects.

    Usage:
        schedule = schedule_factory()  # defaults
        schedule = schedule_factory(name="Custom", is_active=True)
        schedule = schedule_factory(routine_count=3)  # creates 3 mock routines
    """

    def _create_schedule(**overrides):
        # Handle routine_count specially
        routine_count = overrides.pop("routine_count", 1)

        # Create mock routines with working to_dict() methods
        routines = []
        for i in range(routine_count):
            routine = MagicMock()
            routine.to_dict.return_value = {
                "routine_id": f"routine-{i}",
                "name": f"Test Routine {i}",
                "trigger": {"trigger_type": "interval", "interval_minutes": 15},
                "actions": [{"action_type": "gpio", "action_name": "attract_on", "offset_minutes": 0}],
            }
            routines.append(routine)

        defaults = {
            "schedule_id": "test-schedule",
            "name": "Test Schedule",
            "description": "A test schedule",
            "routines": routines,
            "enabled": True,
            "is_active": False,
            "created_at": "2025-06-15T00:00:00Z",
            "modified_at": "2025-06-15T00:00:00Z",
        }
        defaults.update(overrides)

        schedule = MagicMock()
        for key, value in defaults.items():
            setattr(schedule, key, value)

        # Default to_dict returns basic structure
        schedule.to_dict.return_value = {
            "schedule_id": defaults["schedule_id"],
            "name": defaults["name"],
            "routines": [r.to_dict() for r in routines],
        }
        return schedule

    return _create_schedule
```

**Step 2: Run tests to verify fixes**

```bash
SECRET_KEY=test MOTHBOX_ENV=test pytest Tests/unit/test_scheduler_ui_routes.py::TestListSchedulesEndpoint::test_list_schedules_with_data Tests/unit/test_scheduler_ui_routes.py::TestListSchedulesEndpoint::test_list_schedules_active_only Tests/unit/test_scheduler_ui_routes.py::TestListBuiltinSchedulesEndpoint::test_list_builtin_schedules_with_data -v
```

Expected: PASS

**Step 3: Commit**

```bash
git add Tests/unit/test_scheduler_ui_routes.py
git commit -m "fix(tests): update schedule_factory to provide serializable routines"
```

---

## Task 3: Create Missing Builtin Schedule Files

**Files:**
- Create: `webui/backend/presets_builtin/schedules/nightly_hourly.json`
- Create: `webui/backend/presets_builtin/schedules/full_moon_survey.json`
- Create: `webui/backend/presets_builtin/schedules/dawn_transect.json`
- Create: `webui/backend/presets_builtin/schedules/dusk_transect.json`
- Create: `webui/backend/presets_builtin/schedules/continuous_monitoring.json`
- Test: `Tests/unit/test_builtin_schedule_patterns.py`

Use the existing `overnight-moth-survey.json` as the Schema 3.0 template.

**Step 1: Create nightly_hourly.json**

```json
{
  "schedule_id": "nightly_hourly",
  "name": "Nightly Hourly Survey",
  "description": "Captures photos every hour during fixed nighttime window (01:00-06:00)",
  "version": "3.0",
  "is_builtin": true,
  "routines": [
    {
      "routine_id": "nightly-hourly-capture",
      "name": "Hourly Photo Capture",
      "trigger": {
        "trigger_type": "interval",
        "interval_minutes": 60,
        "time_window": {"start_time": "01:00", "end_time": "06:00"}
      },
      "actions": [
        {"action_type": "gpio", "action_name": "flash_on", "offset_minutes": 0},
        {"action_type": "camera", "action_name": "takephoto", "offset_minutes": 1},
        {"action_type": "gpio", "action_name": "flash_off", "offset_minutes": 2}
      ]
    }
  ]
}
```

**Step 2: Create full_moon_survey.json**

```json
{
  "schedule_id": "full_moon_survey",
  "name": "Full Moon Survey",
  "description": "Captures photos during full moon nights when natural light is sufficient",
  "version": "3.0",
  "is_builtin": true,
  "routines": [
    {
      "routine_id": "full-moon-capture",
      "name": "Full Moon Photo Capture",
      "trigger": {
        "trigger_type": "moon_phase",
        "target_phase": "full",
        "phase_tolerance": 2,
        "time_window": {"start_time": "dusk", "end_time": "dawn"}
      },
      "actions": [
        {"action_type": "camera", "action_name": "takephoto", "offset_minutes": 0}
      ]
    }
  ]
}
```

**Step 3: Create dawn_transect.json**

```json
{
  "schedule_id": "dawn_transect",
  "name": "Dawn Transect",
  "description": "Captures photos at sunrise minus 15 minutes for dawn insect activity",
  "version": "3.0",
  "is_builtin": true,
  "routines": [
    {
      "routine_id": "dawn-transect-capture",
      "name": "Dawn Photo Capture",
      "trigger": {
        "trigger_type": "solar",
        "solar_event": "sunrise",
        "offset_minutes": -15
      },
      "actions": [
        {"action_type": "gpio", "action_name": "flash_on", "offset_minutes": 0},
        {"action_type": "camera", "action_name": "takephoto", "offset_minutes": 1},
        {"action_type": "gpio", "action_name": "flash_off", "offset_minutes": 2}
      ]
    }
  ]
}
```

**Step 4: Create dusk_transect.json**

```json
{
  "schedule_id": "dusk_transect",
  "name": "Dusk Transect",
  "description": "Captures photos at sunset minus 15 minutes for dusk insect activity",
  "version": "3.0",
  "is_builtin": true,
  "routines": [
    {
      "routine_id": "dusk-transect-capture",
      "name": "Dusk Photo Capture",
      "trigger": {
        "trigger_type": "solar",
        "solar_event": "sunset",
        "offset_minutes": -15
      },
      "actions": [
        {"action_type": "gpio", "action_name": "flash_on", "offset_minutes": 0},
        {"action_type": "camera", "action_name": "takephoto", "offset_minutes": 1},
        {"action_type": "gpio", "action_name": "flash_off", "offset_minutes": 2}
      ]
    }
  ]
}
```

**Step 5: Create continuous_monitoring.json**

```json
{
  "schedule_id": "continuous_monitoring",
  "name": "Continuous Monitoring",
  "description": "Captures photos every 15 minutes from sunset to sunrise for maximum coverage",
  "version": "3.0",
  "is_builtin": true,
  "routines": [
    {
      "routine_id": "continuous-attract",
      "name": "Attract Lights On",
      "trigger": {
        "trigger_type": "solar",
        "solar_event": "sunset",
        "offset_minutes": 0
      },
      "actions": [
        {"action_type": "gpio", "action_name": "attract_on", "offset_minutes": 0}
      ]
    },
    {
      "routine_id": "continuous-capture",
      "name": "Continuous Photo Capture",
      "trigger": {
        "trigger_type": "interval",
        "interval_minutes": 15,
        "time_window": {"start_time": "sunset", "end_time": "sunrise"}
      },
      "actions": [
        {"action_type": "gpio", "action_name": "flash_on", "offset_minutes": 0},
        {"action_type": "camera", "action_name": "takephoto", "offset_minutes": 1},
        {"action_type": "gpio", "action_name": "flash_off", "offset_minutes": 2}
      ]
    },
    {
      "routine_id": "continuous-lights-off",
      "name": "Attract Lights Off",
      "trigger": {
        "trigger_type": "solar",
        "solar_event": "sunrise",
        "offset_minutes": 0
      },
      "actions": [
        {"action_type": "gpio", "action_name": "attract_off", "offset_minutes": 0}
      ]
    }
  ]
}
```

**Step 6: Run test to verify**

```bash
SECRET_KEY=test MOTHBOX_ENV=test pytest Tests/unit/test_builtin_schedule_patterns.py::TestIssue220SchedulesExist::test_all_required_220_schedules_exist -v
```

Expected: PASS

**Step 7: Run full builtin schedule tests**

```bash
SECRET_KEY=test MOTHBOX_ENV=test pytest Tests/unit/test_builtin_schedule_patterns.py -v
```

Expected: All tests pass (some may skip if files missing, but no failures)

**Step 8: Commit**

```bash
git add webui/backend/presets_builtin/schedules/*.json
git commit -m "feat(schedules): add 5 required builtin schedules for Issue #220"
```

---

## Task 4: Fix Cron Expression Field Count Validation

**Files:**
- Modify: `webui/backend/lib/cron_bridge.py:76-120` (CronEntry.is_valid_expression)
- Test: `Tests/unit/test_cron_validation_routes.py`

**Step 1: Check current is_valid_expression implementation**

Read the current implementation to understand what validation is being done.

**Step 2: Add field count validation to reject 6-field expressions**

The issue is that `croniter` accepts 6-field cron expressions (with seconds), but standard cron uses 5 fields.
Add explicit field count validation before croniter check.

```python
# In cron_bridge.py, update is_valid_expression method in CronEntry class:
@staticmethod
def is_valid_expression(expression: str) -> bool:
    """Validate a cron expression.

    Args:
        expression: Cron expression string (e.g., "0 21 * * *")

    Returns:
        True if valid 5-field cron expression, False otherwise.
    """
    if not expression or not isinstance(expression, str):
        return False

    # Cron must have exactly 5 fields (minute, hour, day, month, weekday)
    fields = expression.strip().split()
    if len(fields) != 5:
        return False

    try:
        # Use croniter to validate the expression syntax
        croniter(expression)
        return True
    except (ValueError, KeyError):
        return False
```

**Step 3: Run test to verify**

```bash
SECRET_KEY=test MOTHBOX_ENV=test pytest Tests/unit/test_cron_validation_routes.py::TestValidateCronEndpoint::test_validate_cron_invalid_patterns -v
```

Expected: PASS

**Step 4: Run all cron validation tests to ensure no regressions**

```bash
SECRET_KEY=test MOTHBOX_ENV=test pytest Tests/unit/test_cron_validation_routes.py -v
```

Expected: All tests pass

**Step 5: Commit**

```bash
git add webui/backend/lib/cron_bridge.py
git commit -m "fix(cron): reject 6-field cron expressions (seconds not supported)"
```

---

## Task 5: Final Verification

**Step 1: Run all previously failing tests**

```bash
SECRET_KEY=test MOTHBOX_ENV=test pytest \
  Tests/unit/test_schedule_preview.py::TestPreviewExecution::test_preview_execution_to_dict \
  Tests/unit/test_schedule_preview.py::TestPreviewResult::test_preview_result_roundtrip \
  Tests/unit/test_builtin_schedule_patterns.py::TestIssue220SchedulesExist::test_all_required_220_schedules_exist \
  Tests/unit/test_scheduler_ui_routes.py::TestListSchedulesEndpoint::test_list_schedules_with_data \
  Tests/unit/test_scheduler_ui_routes.py::TestListSchedulesEndpoint::test_list_schedules_active_only \
  Tests/unit/test_scheduler_ui_routes.py::TestListBuiltinSchedulesEndpoint::test_list_builtin_schedules_with_data \
  Tests/unit/test_cron_validation_routes.py::TestValidateCronEndpoint::test_validate_cron_invalid_patterns \
  -v
```

Expected: 7/7 tests pass

**Step 2: Run full scheduler test suite**

```bash
SECRET_KEY=test MOTHBOX_ENV=test pytest Tests/unit/test_cron_*.py Tests/unit/test_schedule*.py Tests/unit/test_scheduler*.py -v --tb=short
```

Expected: No new failures introduced

**Step 3: Run linting**

```bash
ruff check webui/backend/lib/schedule_preview.py webui/backend/lib/cron_bridge.py
```

Expected: No errors

**Step 4: Push and verify CI**

```bash
git push
```

Monitor CI for green status.

---

## Files Modified Summary

| File | Change |
|------|--------|
| `webui/backend/lib/schedule_preview.py` | Fix `from_dict()` to accept both pattern_id and routine_id |
| `webui/backend/lib/cron_bridge.py` | Add 5-field validation to `is_valid_expression()` |
| `Tests/unit/test_schedule_preview.py` | Update test to expect pattern_id (API contract) |
| `Tests/unit/test_scheduler_ui_routes.py` | Fix schedule_factory to provide serializable routines |
| `webui/backend/presets_builtin/schedules/nightly_hourly.json` | New file |
| `webui/backend/presets_builtin/schedules/full_moon_survey.json` | New file |
| `webui/backend/presets_builtin/schedules/dawn_transect.json` | New file |
| `webui/backend/presets_builtin/schedules/dusk_transect.json` | New file |
| `webui/backend/presets_builtin/schedules/continuous_monitoring.json` | New file |

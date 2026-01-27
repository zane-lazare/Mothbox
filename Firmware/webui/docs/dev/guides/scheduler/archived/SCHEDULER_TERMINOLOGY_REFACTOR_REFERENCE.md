# Scheduler Terminology Refactor - Reference

**Purpose**: Quick lookup for patterns, API spec, TimeWindow, and file checklists.

**Use When**: You need to look up specific implementation details during development.

---

## Table of Contents

1. [Common Patterns](#common-patterns)
2. [TimeWindow Usage](#timewindow-usage)
3. [File Checklist](#file-checklist)
4. [Success Criteria](#success-criteria)

---

## Common Patterns

### Pattern 1: Dataclass with to_dict/from_dict

**Used in**: All data classes in schedule_schema.py

```python
@dataclass
class Action:
    action_type: str
    action_name: str
    offset_minutes: int = 0

    def to_dict(self) -> dict:
        return {
            "action_type": self.action_type,
            "action_name": self.action_name,
            "offset_minutes": self.offset_minutes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Action":
        return cls(
            action_type=data["action_type"],
            action_name=data["action_name"],
            offset_minutes=data.get("offset_minutes", 0),
        )
```

### Pattern 2: Validation Function

**Used in**: All validate_* functions

```python
def validate_action(action: Action) -> tuple[bool, str | None]:
    """Validate action, return (valid, error_message)."""
    if action.action_type not in ACTION_TYPES:
        return False, f"Invalid action type: {action.action_type}"

    if action.offset_minutes < 0:
        return False, "Offset cannot be negative"

    return True, None
```

### Pattern 3: Unified Date-Specific Cron Generation

**Used for**: Converting all trigger types to cron entries

All trigger types generate **date-specific cron entries** (no patterns like `*/15`).
This unified approach pre-computes 5 years of execution times at activation.

```python
def routine_to_dated_cron(
    routine: Routine,
    latitude: float,
    longitude: float,
    years_ahead: int = 5,
) -> list[CronEntry]:
    """Generate date-specific cron entries for any trigger type."""
    # Calculate all execution times for this routine's trigger
    execution_times = calculate_execution_times(
        trigger=routine.trigger,
        latitude=latitude,
        longitude=longitude,
        years_ahead=years_ahead,
    )

    # All triggers produce the same output format: specific dates
    entries = []
    for exec_time in execution_times:
        for action in routine.actions:
            action_time = exec_time + timedelta(minutes=action.offset_minutes)
            entries.append(CronEntry(
                expression=datetime_to_cron(action_time),
                command=build_action_command(action),
                routine_id=routine.routine_id,
                execution_time=action_time,
            ))

    return entries


def datetime_to_cron(dt: datetime) -> str:
    """Convert datetime to date-specific cron expression."""
    return f"{dt.minute} {dt.hour} {dt.day} {dt.month} *"


def calculate_execution_times(trigger: Trigger, ...) -> list[datetime]:
    """Dispatch to trigger-specific calculators."""
    trigger_type = getattr(trigger, "trigger_type", None)

    if trigger_type == "interval":
        return _calculate_interval_times(trigger, years_ahead)
    elif trigger_type == "solar":
        return _calculate_solar_times(trigger, latitude, longitude, years_ahead)
    elif trigger_type == "fixed_time":
        return _calculate_fixed_time_times(trigger, years_ahead)
    elif trigger_type == "moon_phase":
        return _calculate_moon_phase_times(trigger, years_ahead)
    elif trigger_type == "recurring_days":
        return _calculate_recurring_days_times(trigger, years_ahead)
    elif trigger_type == "cron":
        return _calculate_cron_times(trigger, years_ahead)
    elif trigger_type == "sensor":
        logger.warning("Sensor triggers are pre-conditions only")
        return []
    else:
        raise ValueError(f"Unknown trigger type: {trigger_type}")
```

**Why unified date-specific?**
1. Solar/moon events vary daily - can't use repeating patterns
2. RecurringDaysTrigger ("every N days") can't be expressed in standard cron
3. Offline operation - no GPS/internet needed at execution time
4. Uniform approach simplifies code and debugging

### Pattern 4: Adding a New Trigger Type

When adding a new trigger type:

1. **Create the dataclass** in `schedule_schema.py`:
```python
@dataclass
class NewTrigger:
    trigger_type: str = "new_trigger"
    # ... trigger-specific fields

    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, data: dict) -> "NewTrigger": ...
```

2. **Add to Trigger union**:
```python
Trigger = Union[
    IntervalTrigger,
    SolarTrigger,
    # ... other triggers
    NewTrigger,  # Add here
]
```

3. **Update trigger_from_dict()**:
```python
elif trigger_type == "new_trigger":
    return NewTrigger.from_dict(data)
```

4. **Add validation function**:
```python
def validate_new_trigger(trigger: NewTrigger) -> tuple[bool, str | None]:
    # Validation logic
    return True, None
```

5. **Update _validate_trigger()**:
```python
elif trigger_type == "new_trigger":
    return validate_new_trigger(trigger)
```

6. **Add cron converter** in `cron_bridge.py`:
```python
def _routine_new_trigger_to_cron(routine: Routine) -> list[CronEntry]:
    # Cron conversion logic
    ...
```

7. **Update routine_to_cron()**:
```python
elif trigger_type == "new_trigger":
    return _routine_new_trigger_to_cron(routine)
```

8. **Add frontend form** component:
```jsx
function NewTriggerForm({ trigger, onChange }) {
  // Form for trigger-specific fields
}
```

9. **Update TriggerSelector**:
```jsx
<option value="new_trigger">New Trigger</option>
// ...
{triggerType === 'new_trigger' && <NewTriggerForm ... />}
```

10. **Add test fixtures** and tests

---

## TimeWindow Usage

**Import location**: `webui.backend.lib.schedule_schema`

**Purpose**: Constrain when interval or moon phase triggers are active

### Basic Usage

```python
from webui.backend.lib.schedule_schema import TimeWindow, IntervalTrigger, MoonPhaseTrigger

# Fixed time windows (HH:MM format)
TimeWindow(start_time="22:00", end_time="06:00")  # Overnight: 10pm - 6am
TimeWindow(start_time="09:00", end_time="17:00")  # Daytime: 9am - 5pm

# Solar-based time windows (uses astral library)
TimeWindow(start_time="sunset", end_time="sunrise")  # Night (calculated)
TimeWindow(start_time="sunrise", end_time="sunset")  # Day (calculated)
TimeWindow(start_time="dusk", end_time="dawn")       # Civil twilight

# With triggers
interval_overnight = IntervalTrigger(
    trigger_type="interval",
    interval_minutes=15,
    time_window=TimeWindow(start_time="22:00", end_time="06:00"),
)

moon_night = MoonPhaseTrigger(
    trigger_type="moon_phase",
    phases=["full"],
    time_window=TimeWindow(start_time="sunset", end_time="sunrise"),
)
```

### TimeWindow Class Definition

```python
@dataclass
class TimeWindow:
    start_time: str  # "HH:MM" or solar event name
    end_time: str    # "HH:MM" or solar event name

    def to_dict(self) -> dict:
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TimeWindow":
        return cls(
            start_time=data["start_time"],
            end_time=data["end_time"],
        )

    def is_active(self, current_time: datetime, lat: float, lon: float) -> bool:
        """Check if current time falls within this window."""
        # Implementation handles both fixed times and solar events
        ...
```

### Supported Solar Event Names

- `sunrise`, `sunset`
- `dawn`, `dusk` (civil twilight)
- `nautical_dawn`, `nautical_dusk`
- `astronomical_dawn`, `astronomical_dusk`
- `noon`, `midnight`

---

## Implementation Phases

See [Index](./SCHEDULER_TERMINOLOGY_REFACTOR_INDEX.md) for the authoritative
phase structure and progress checklists.

This document provides file-level checklists for quick reference during implementation.

---

## File Checklist

### Files to Modify (Backend)

- [ ] `webui/backend/lib/schedule_schema.py` - Major restructure
- [ ] `webui/backend/lib/cron_bridge.py` - Update iteration and functions
- [ ] `webui/backend/lib/schedule_conflict.py` - Field renames
- [ ] `webui/backend/lib/schedule_storage.py` - Minor updates
- [ ] `webui/backend/lib/schedule_preview.py` - Rename function
- [ ] `webui/backend/services/scheduler_service.py` - Minor updates
- [ ] `webui/backend/routes/scheduler_ui.py` - API updates

### Files to Create (Backend)

- [ ] `webui/backend/presets_builtin/schedules/overnight-moth-survey.json`
- [ ] `webui/backend/presets_builtin/schedules/daytime-pollinator.json`

### Files to Rename (Frontend)

- [ ] `src/components/scheduler/PatternEditor/` → `RoutineEditor/`
- [ ] `src/hooks/useEventPatterns.js` → `useRoutines.js`
- [ ] `src/components/scheduler/ScheduleEditor/EventPatternSelector.jsx` → `RoutineSelector.jsx`

### Files to Remove (Frontend)

- [ ] `src/components/scheduler/PatternLibrary/` (entire directory)

### Test Files to Update

- [ ] `Tests/unit/test_schedule_schema.py`
- [ ] `Tests/unit/test_cron_bridge.py`
- [ ] `Tests/unit/test_schedule_conflict_lib.py`
- [ ] `Tests/unit/test_scheduler_service.py`
- [ ] `Tests/integration/test_scheduler*.py`
- [ ] All frontend test files

### Documentation Checklist

- [ ] Update `CLAUDE.md` - Visual Scheduler System section
- [ ] Rewrite `webui/docs/dev/api/scheduler.md`
- [ ] Update/remove `webui/docs/dev/api/event-patterns.md`
- [ ] Update `webui/docs/dev/api/cron-bridge.md`
- [ ] Rewrite `webui/docs/SCHEDULER_USER_GUIDE.md`
- [ ] Archive planning docs (`webui/docs/dev/planning/scheduler/`)
- [ ] Archive refactor guide docs (`webui/docs/dev/guides/scheduler/`)

---

## Success Criteria

See [Index](./SCHEDULER_TERMINOLOGY_REFACTOR_INDEX.md#success-criteria) for the authoritative success criteria checklist.

---

## Related Documentation

- [Index](./SCHEDULER_TERMINOLOGY_REFACTOR_INDEX.md) - Navigation hub
- [Overview](./SCHEDULER_TERMINOLOGY_REFACTOR_OVERVIEW.md) - Architecture context
- [Backend Implementation](./SCHEDULER_TERMINOLOGY_REFACTOR_BACKEND.md)
- [Frontend Implementation](./SCHEDULER_TERMINOLOGY_REFACTOR_FRONTEND.md)
- [Testing Strategy](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md)

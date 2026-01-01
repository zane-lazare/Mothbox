# Scheduler Terminology Refactor

**Status**: Draft
**Priority**: High (prerequisite for One-Time Actions #295)
**Type**: Refactor / Tech Debt

---

## Problem Statement

The current scheduler terminology is inconsistent and confusing:

1. **`EventPattern`** - Combines two words that mean the same thing
2. **`PatternAction`** - Redundant "Pattern" prefix
3. **"Event"** is overloaded - used for both patterns and scheduled executions
4. **Trigger lives on Schedule** - Forces all routines to share same timing
5. **Complex hierarchy** - Schedule → EventPattern → PatternAction is verbose

### Current Model

```
Schedule
├── trigger (one for entire schedule)
├── start_date, end_date, days_of_week
└── EventPattern(s)
    └── PatternAction(s)
        └── offset_minutes (relative to pattern start)
```

**Limitation**: Cannot mix different timing types (e.g., UV on at dusk + photos every 15min + UV off at dawn) in a single schedule.

---

## Proposed Model

```
Schedule
├── name: str
├── description: str
├── enabled: bool (only one schedule active at a time)
└── routines: [Routine, ...]

Routine
├── name: str | None (auto-generated if null)
├── trigger: Trigger
└── actions: [Action, ...]

Action
├── action_type: "gpio" | "camera" | "gps_sync" | "service"
├── action_name: str
├── offset_minutes: int (relative to routine start)
├── parameters: dict
└── description: str | None
```

### Key Changes

| Aspect | Current | Proposed |
|--------|---------|----------|
| Pattern container | `EventPattern` | `Routine` |
| Action class | `PatternAction` | `Action` |
| Trigger location | Schedule level | Routine level |
| Schedule constraints | `start_date`, `end_date`, `days_of_week` | Just `enabled` |
| Preview function | `get_next_events()` | `preview_schedule()` |
| Built-in library | Many built-in patterns | 1-2 built-in schedules |

---

## Trigger Types

Each routine has its own trigger:

### IntervalTrigger
```python
IntervalTrigger:
    interval_minutes: int        # e.g., 15
    time_window: TimeWindow | None  # e.g., 22:00-06:00
    days_of_week: list[int] | None  # 0=Mon..6=Sun
```

### FixedTimeTrigger
```python
FixedTimeTrigger:
    time: str                    # "HH:MM" format
    days_of_week: list[int] | None
```

### SolarTrigger
```python
SolarTrigger:
    solar_event: str             # "dusk", "dawn", "sunset", etc.
    offset_minutes: int          # +/- from event
    days_of_week: list[int] | None
```

### MoonPhaseTrigger
```python
MoonPhaseTrigger:
    phases: list[str]            # ["full", "new", etc.]
    time_window: TimeWindow | None
    days_of_week: list[int] | None
```

### RecurringDaysTrigger
```python
RecurringDaysTrigger:
    every_n_days: int            # e.g., 3 for every 3 days
    time: str                    # "HH:MM" format
    start_date: str | None       # When to start counting
```

### CronTrigger (Expert Mode)
```python
CronTrigger:
    cron_expression: str         # Raw cron syntax
```

---

## Auto-Generated Names

Routine and action names are auto-generated from content when not explicitly set.

### Routine Name Generation

| Trigger | Actions | Generated Name |
|---------|---------|----------------|
| `solar(dusk)` | `[attract_on]` | "Attract On at Dusk" |
| `interval(15min, 22:00-06:00)` | `[flash_on, takephoto, flash_off]` | "Flash + Photo every 15min" |
| `fixed_time(09:00)` | `[backup]` | "Backup at 09:00" |
| `solar(dawn)` | `[attract_off]` | "Attract Off at Dawn" |
| `every_n_days(3, 21:00)` | `[gps_sync]` | "GPS Sync every 3 days" |

### Action Display Names

| `action_name` | Display Name |
|---------------|--------------|
| `attract_on` | "Attract On" |
| `attract_off` | "Attract Off" |
| `flash_on` | "Flash On" |
| `flash_off` | "Flash Off" |
| `takephoto` | "Take Photo" |
| `gps_sync` | "GPS Sync" |
| `backup` | "Backup" |
| `update_display` | "Update Display" |

### Implementation

```python
def get_routine_display_name(routine: Routine) -> str:
    """Get display name for routine, auto-generating if not set."""
    if routine.name:
        return routine.name
    return _generate_routine_name(routine.trigger, routine.actions)

def _generate_routine_name(trigger: Trigger, actions: list[Action]) -> str:
    """Generate name from trigger and actions."""
    action_summary = _summarize_actions(actions)
    trigger_desc = _describe_trigger(trigger)
    return f"{action_summary} {trigger_desc}"
```

---

## Example Schedule

### "Overnight Moth Survey"

```python
Schedule(
    name="Overnight Moth Survey",
    description="UV-attracted moth photography session",
    enabled=True,
    routines=[
        Routine(
            name=None,  # Auto: "Attract On at Dusk"
            trigger=SolarTrigger(solar_event="dusk", offset_minutes=0),
            actions=[
                Action(action_type="gpio", action_name="attract_on"),
            ],
        ),
        Routine(
            name=None,  # Auto: "Flash + Photo every 15min"
            trigger=IntervalTrigger(
                interval_minutes=15,
                time_window=TimeWindow(start_time="22:00", end_time="06:00"),
            ),
            actions=[
                Action(action_type="gpio", action_name="flash_on", offset_minutes=0),
                Action(action_type="camera", action_name="takephoto", offset_minutes=1),
                Action(action_type="gpio", action_name="flash_off", offset_minutes=2),
            ],
        ),
        Routine(
            name=None,  # Auto: "Attract Off at Dawn"
            trigger=SolarTrigger(solar_event="dawn", offset_minutes=0),
            actions=[
                Action(action_type="gpio", action_name="attract_off"),
            ],
        ),
    ],
)
```

### "Daytime Pollinator"

```python
Schedule(
    name="Daytime Pollinator",
    description="Daylight pollinator monitoring",
    enabled=False,
    routines=[
        Routine(
            name=None,  # Auto: "Photo every 30min"
            trigger=IntervalTrigger(
                interval_minutes=30,
                time_window=TimeWindow(start_time="sunrise", end_time="sunset"),
            ),
            actions=[
                Action(action_type="camera", action_name="takephoto"),
            ],
        ),
    ],
)
```

---

## Storage

### JSON File Storage (Unchanged)

Schedules continue to be stored as JSON files:

- **User schedules**: `CONFIG_DIR/schedules/{schedule_id}.json`
- **Built-in schedules**: `webui/backend/presets_builtin/schedules/{schedule_id}.json`

Features retained:
- One file per schedule
- Thread-safe with FileLock
- Built-in schedules are read-only
- Backup (.bak) before overwrite/delete

### Example Schedule JSON

```json
{
  "schedule_id": "overnight-moth-survey",
  "name": "Overnight Moth Survey",
  "description": "UV-attracted moth photography session",
  "enabled": true,
  "created_at": "2025-12-31T10:00:00Z",
  "updated_at": "2025-12-31T10:00:00Z",
  "routines": [
    {
      "name": null,
      "trigger": {
        "trigger_type": "solar",
        "solar_event": "dusk",
        "offset_minutes": 0
      },
      "actions": [
        {
          "action_type": "gpio",
          "action_name": "attract_on",
          "offset_minutes": 0,
          "parameters": {},
          "description": null
        }
      ]
    },
    {
      "name": null,
      "trigger": {
        "trigger_type": "interval",
        "interval_minutes": 15,
        "time_window": {
          "start_time": "22:00",
          "end_time": "06:00"
        }
      },
      "actions": [
        {
          "action_type": "gpio",
          "action_name": "flash_on",
          "offset_minutes": 0,
          "parameters": {},
          "description": null
        },
        {
          "action_type": "camera",
          "action_name": "takephoto",
          "offset_minutes": 1,
          "parameters": {},
          "description": null
        },
        {
          "action_type": "gpio",
          "action_name": "flash_off",
          "offset_minutes": 2,
          "parameters": {},
          "description": null
        }
      ]
    },
    {
      "name": null,
      "trigger": {
        "trigger_type": "solar",
        "solar_event": "dawn",
        "offset_minutes": 0
      },
      "actions": [
        {
          "action_type": "gpio",
          "action_name": "attract_off",
          "offset_minutes": 0,
          "parameters": {},
          "description": null
        }
      ]
    }
  ]
}
```

---

## Migration Strategy

No migration needed - the scheduler is new and there are no existing user schedules to convert. We'll implement the new schema directly.

---

## Scope of Changes

### Backend Files

| File | Changes |
|------|---------|
| `lib/schedule_schema.py` | Rename classes, move trigger to Routine |
| `lib/cron_bridge.py` | Update to iterate routines with individual triggers |
| `lib/schedule_conflict.py` | Update for new structure |
| `lib/schedule_preview.py` | Rename to use `preview_schedule()` |
| `lib/schedule_storage.py` | Update serialization |
| `services/scheduler_service.py` | Update all references |
| `routes/scheduler_ui.py` | Update API |

### Frontend Files

| File | Changes |
|------|---------|
| `hooks/useSchedules.js` | Update for new structure |
| `hooks/useEventPatterns.js` | Remove or rename to `useRoutines.js` |
| `components/scheduler/PatternEditor/*` | Rename to `RoutineEditor/*` |
| `components/scheduler/PatternLibrary/*` | Remove (replaced by built-in schedules) |
| `utils/schedulerApi.js` | Update field names |

### Test Files

| Pattern | Changes |
|---------|---------|
| `test_schedule*.py` | Update all class/field references |
| `test_cron_bridge.py` | Update for routine-level triggers |
| `**/scheduler/**/*.test.jsx` | Update component tests |

### Documentation

| File | Changes |
|------|---------|
| `CLAUDE.md` | Update scheduler section |
| `webui/docs/dev/api/scheduler.md` | Rewrite for new model |
| `webui/docs/SCHEDULER_USER_GUIDE.md` | Rewrite |
| `webui/docs/dev/guides/ONE_TIME_ACTIONS_DEV_GUIDE.md` | Update or remove (feature now built-in) |

---

## Built-in Schedules

Replace the pattern library with 1-2 complete built-in schedules:

1. **Overnight Moth Survey** - UV at dusk, photos every 15min overnight, UV off at dawn
2. **Daytime Pollinator** - Photos every 30min during daylight

Users can:
- Activate a built-in schedule as-is
- Clone and customize a built-in schedule
- Create from scratch

---

## Implementation Phases

### Phase 1: Backend Schema Refactor

1. Rename `EventPattern` → `Routine`
2. Rename `PatternAction` → `Action`
3. Move trigger from Schedule to Routine
4. Remove Schedule-level date/day constraints
5. Update validation functions
6. Add auto-name generation
7. Update `schedule_storage.py` for new format
8. Create built-in schedules in new format

### Phase 2: Cron Bridge Update

1. Update `schedule_to_cron()` to iterate routines
2. Each routine generates cron entries from its own trigger
3. Rename `get_next_events()` → `preview_schedule()`
4. Update preview to handle per-routine triggers

### Phase 3: Frontend Refactor

1. Rename components (`PatternEditor` → `RoutineEditor`)
2. Update hooks for new data structure
3. Add trigger selection per routine
4. Remove pattern library, add built-in schedule selector
5. Implement auto-name display

### Phase 4: Documentation & Cleanup

1. Update CLAUDE.md
2. Rewrite scheduler API docs
3. Rewrite user guide
4. Remove obsolete planning docs
5. Update/remove ONE_TIME_ACTIONS_DEV_GUIDE.md

---

## Success Criteria

- [ ] All backend tests pass with new terminology
- [ ] All frontend tests pass
- [ ] E2E scheduler tests pass
- [ ] Existing saved schedules migrate correctly
- [ ] Built-in schedules work out of box
- [ ] Auto-generated names display correctly
- [ ] No references to old names (`EventPattern`, `PatternAction`, `get_next_events`)
- [ ] One-time action use cases work (UV on at dusk, off at dawn)

---

## Estimated Effort

| Phase | Effort |
|-------|--------|
| Backend Schema Refactor | 1-2 days |
| Cron Bridge Update | 1 day |
| Frontend Refactor | 1-2 days |
| Documentation & Cleanup | 0.5 day |
| **Total** | **3-5 days** |

---

## Next Steps

1. [ ] Review and approve this planning doc
2. [ ] Create GitHub issue for refactor
3. [ ] Implement in phases
4. [ ] Update ONE_TIME_ACTIONS_DEV_GUIDE.md (or archive if no longer needed)
5. [ ] Close #295 as resolved by this refactor

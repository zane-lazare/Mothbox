# Scheduler Terminology Refactor - Overview

**Purpose**: Understand the architecture changes and schema transformations in this refactor.

**Prerequisites**: None - start here for context.

**Next Steps**: [Backend Implementation](./SCHEDULER_TERMINOLOGY_REFACTOR_BACKEND.md) or [Frontend Implementation](./SCHEDULER_TERMINOLOGY_REFACTOR_FRONTEND.md)

---

## Table of Contents

1. [Purpose](#purpose)
2. [Scope](#scope)
3. [Schema Version](#schema-version)
4. [Architecture](#architecture)
5. [Data Structures](#data-structures)
6. [Key Decisions](#key-decisions)

---

## Purpose

This refactor restructures the scheduler data model to:

1. **Simplify terminology**: `EventPattern` → `Routine`, `PatternAction` → `Action`
2. **Enable per-routine triggers**: Move trigger from Schedule level to Routine level
3. **Support one-time actions natively**: UV on at dusk + photos every 15min + UV off at dawn

### User Stories

- As a researcher, I want UV lights on at dusk and off at dawn with photos every 15min between, so that I can run unattended overnight surveys
- As a field operator, I want to see auto-generated names for my routines, so that I don't have to name everything manually
- As a developer, I want cleaner terminology, so that the codebase is easier to understand

---

## Scope

**Included:**
- Rename all classes, functions, and references
- Move trigger configuration from Schedule to Routine
- Remove Schedule-level date/day constraints (`start_date`, `end_date`, `days_of_week`)
- Add auto-generated routine/action names
- Update cron bridge to iterate per-routine triggers
- Rename frontend components and hooks
- Update all tests
- Create 1-2 built-in schedules (replacing pattern library)

**Excluded:**
- New action types
- Migration of existing schedules (none exist yet)

**Note**: RecurringDaysTrigger IS included (7 trigger types total after refactor).

---

## Schema Version

This is a **breaking change** that increments the schema version:

| Version | Description |
|---------|-------------|
| 1.0 | Original single-pattern schedule |
| 2.0 | Multi-pattern with schedule-level trigger (current codebase) |
| **3.0** | **Routine-level triggers (this refactor)** |

**Key decisions**:
- **Fresh start (no migration)**: Schema 3.0 completely replaces 2.0
- **No backwards compatibility layer**: Clean break, simpler codebase
- **No API versioning**: Single API version, updated in place
- **No user data migration needed**: No production deployments exist with user-created schedules

**Implementation notes**:
- Update `SCHEDULE_SCHEMA_VERSION` constant from `"2.0"` to `"3.0"`
- Update `SUPPORTED_VERSIONS` to only include `["3.0"]`
- Loading a 2.0 schedule file will raise a validation error (this is intentional)
- Any existing test fixtures using 2.0 format must be updated to 3.0 format

---

## Architecture

### Current Model (Before Refactor)

```
Schedule
├── schedule_id, name, description, enabled, is_active
├── trigger_type: "interval" | "solar" | "moon_phase" | "fixed_time" | "sensor" | "cron"
├── interval_trigger / solar_trigger / ... (one active per trigger_type)
├── start_date, end_date, days_of_week (schedule-level constraints)
└── event_patterns: [EventPattern, ...]
    └── PatternAction(s)
        └── offset_minutes (relative to pattern start)
```

**Limitation**: All patterns share the same trigger. Cannot mix "UV on at dusk" + "photos every 15min" + "UV off at dawn".

### New Model (After Refactor)

```
Schedule
├── schedule_id, name, description, enabled
└── routines: [Routine, ...]

Routine
├── routine_id, name (auto-generated if null)
├── trigger: Trigger (moved from Schedule!)
├── pre_condition: SensorTrigger | None (optional)
└── actions: [Action, ...]

Action
├── action_type, action_name, offset_minutes, parameters, description
```

**Key Change**: Each Routine has its own trigger, enabling independent timing.

### Data Flow

```
1. User creates schedule with multiple routines (each with its own trigger)
   ↓
2. Frontend sends schedule to POST /api/scheduler/ui/schedules
   ↓
3. scheduler_service validates via schedule_schema.validate_schedule()
   ↓
4. On activation, schedule_to_cron() processes each routine:
   ├── Routine 1: SolarTrigger(dusk) → cron entries for attract_on
   ├── Routine 2: IntervalTrigger(15min) → cron entries for photo cycle
   └── Routine 3: SolarTrigger(dawn) → cron entries for attract_off
   ↓
5. Cron entries written to system crontab
   ↓
6. Actions execute at scheduled times
```

---

## Data Structures

### Summary of Renames

| Old Name | New Name | Location |
|----------|----------|----------|
| `PatternAction` | `Action` | schedule_schema.py |
| `EventPattern` | `Routine` | schedule_schema.py |
| `event_patterns` | `routines` | Schedule field |
| `pattern_id` | `routine_id` | Routine field |
| `validate_pattern_action()` | `validate_action()` | schedule_schema.py |
| `validate_event_pattern()` | `validate_routine()` | schedule_schema.py |
| `get_next_events()` | `preview_schedule()` | cron_bridge.py |
| `PatternExecution` | `RoutineExecution` | schedule_conflict.py |
| `generate_pattern_executions()` | `generate_routine_executions()` | schedule_conflict.py |

### Key Structural Change

**Before**: Trigger on Schedule, shared by all patterns
```python
Schedule(
    trigger_type="interval",
    interval_trigger=IntervalTrigger(...),
    event_patterns=[
        EventPattern(actions=[...]),
        EventPattern(actions=[...]),
    ]
)
```

**After**: Trigger on each Routine
```python
Schedule(
    routines=[
        Routine(
            trigger=SolarTrigger(solar_event="dusk"),
            actions=[Action(...)]
        ),
        Routine(
            trigger=IntervalTrigger(interval_minutes=15),
            actions=[Action(...), Action(...)]
        ),
        Routine(
            trigger=SolarTrigger(solar_event="dawn"),
            actions=[Action(...)]
        ),
    ]
)
```

### Trigger Types (7 total)

| Trigger Type | Purpose | Example |
|--------------|---------|---------|
| `IntervalTrigger` | Every N minutes | Photos every 15min |
| `SolarTrigger` | At solar event | UV on at dusk |
| `FixedTimeTrigger` | At specific time | Backup at 09:00 |
| `MoonPhaseTrigger` | On moon phases | Full moon nights only |
| `RecurringDaysTrigger` | Every N days | GPS sync every 3 days |
| `SensorTrigger` | Pre-condition check | Only if light < 100 |
| `CronTrigger` | Raw cron expression | Expert mode |

### Pre-Condition Semantics

The `pre_condition` field enables conditional execution:

```python
Routine(
    routine_id="daylight-photo",
    name="Photo if bright",
    trigger=IntervalTrigger(interval_minutes=30),  # Primary trigger
    pre_condition=SensorTrigger(
        sensor_type="light",
        condition="above",
        threshold=500
    ),
    actions=[Action(action_type="camera", action_name="takephoto")]
)
```

**Behavior**:
- Routine runs on its `trigger` schedule (primary timing)
- Before executing actions, checks if `pre_condition` is met
- If condition is met: execute actions normally
- If condition is NOT met: skip this execution (log warning), wait for next trigger

> **⚠️ Sensor Trigger Limitations**
>
> Sensor triggers in this version are **pre-conditions only**, not event-driven triggers.
> The routine runs on its primary trigger's schedule, but actions only execute if
> the sensor condition is met at that moment.
> True event-driven sensor triggers are planned for a future release.

---

## Key Decisions

### From Q&A Clarifications

| Decision | Choice | Rationale |
|----------|--------|-----------|
| SensorTrigger design | Separate `pre_condition` field | Cleaner API, avoids trigger confusion |
| Time collision tolerance | Exact match only | Simple, predictable behavior |
| Backwards compatibility | None (clean break) | No existing user schedules |
| API versioning | None (single version) | Simpler implementation |
| Pattern library | Replace with built-in schedules | More useful starting points |
| `enabled` vs `is_active` | Separate fields | `enabled` = user preference, `is_active` = runtime state |
| Cron generation | Unified 5-year pre-computation | All triggers generate date-specific entries for reliability |

### Schedule State Fields

The Schedule has two state-related boolean fields:

- **`enabled`**: User-controlled preference flag. If `false`, the schedule cannot be activated. Used to temporarily disable a schedule without deleting it.
- **`is_active`**: Runtime state flag. If `true`, the schedule's cron entries are installed in the system crontab and executing. Only one schedule can be active at a time.

**Valid states:**
| `enabled` | `is_active` | Meaning |
|-----------|-------------|---------|
| `true` | `false` | Available but not running |
| `true` | `true` | Currently running |
| `false` | `false` | Disabled by user |
| `false` | `true` | **Invalid** (code prevents this) |

### Unified Cron Generation

All trigger types are converted to **date-specific cron entries** at activation time, pre-computed for 5 years ahead.

**Why date-specific for all triggers?**
1. Solar/moon events vary daily - can't use repeating cron patterns
2. RecurringDaysTrigger ("every N days") can't be expressed in standard cron
3. Offline operation - no GPS/internet needed at execution time
4. Uniform approach simplifies code and debugging

**Considerations:**
- Typical overnight survey: ~60,000 entries over 5 years
- Crontab size: ~6MB (acceptable for Pi storage)
- Re-activation required after 5 years or on location change (solar times shift)

### Built-in Schedules

Replace pattern library with 1-2 complete built-in schedules:

1. **Overnight Moth Survey** - UV at dusk, photos every 15min overnight, UV off at dawn
2. **Daytime Pollinator** - Photos every 30min during daylight

Users can:
- Activate a built-in schedule as-is
- Clone and customize a built-in schedule
- Create from scratch

---

## Success Criteria

- [ ] All backend tests pass with new terminology
- [ ] All frontend tests pass
- [ ] E2E scheduler tests pass
- [ ] Built-in schedules work out of box
- [ ] Auto-generated names display correctly
- [ ] No references to old names (`EventPattern`, `PatternAction`, `get_next_events`)
- [ ] One-time action use cases work (UV on at dusk, off at dawn)

---

## Related Documentation

- [Index](./SCHEDULER_TERMINOLOGY_REFACTOR_INDEX.md) - Navigation hub
- [Backend Implementation](./SCHEDULER_TERMINOLOGY_REFACTOR_BACKEND.md)
- [Frontend Implementation](./SCHEDULER_TERMINOLOGY_REFACTOR_FRONTEND.md)
- [Testing Strategy](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md)
- [Reference](./SCHEDULER_TERMINOLOGY_REFACTOR_REFERENCE.md)

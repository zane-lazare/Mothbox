# Feature: One-Time Actions for Scheduler

**Status**: Proposed
**Priority**: High (MVP gap)
**Created**: 2025-12-30
**Updated**: 2025-12-31

---

## Problem Statement

The current scheduler only supports **repeating interval patterns**, which forces all actions to repeat at every interval. This doesn't support common use cases like:

- **Setup actions** that run once at session start (e.g., UV lights on at dusk)
- **Repeating actions** that run every N minutes (e.g., flash + photo)
- **Teardown actions** that run once at session end (e.g., UV lights off at dawn)

---

## Use Cases

### Use Case 1: Overnight Moth Survey (Primary)

**Requirements**:
- Turn UV on at 9pm (once)
- Take photos every 15 min from 10pm-6am with 1-min flash pre-warm
- Turn UV off at 6am (once)

**Current limitation**: UV would either cycle on/off every 15 minutes (not wanted) or stay on forever requiring manual intervention.

### Use Case 2: Solar-Triggered Indefinite Operation

**Requirements**:
- Turn UV on at dusk (once per night)
- Take photos every 15 minutes until dawn
- Turn UV off at dawn (once per night)
- Repeat indefinitely (no date range)

**Current limitation**: Cannot tie one-time actions to solar events.

### Use Case 3: GPS Sync Before Session

**Requirements**:
- Sync GPS 5 minutes before session starts
- Run normal photo capture pattern

### Use Case 4: End-of-Session Backup

**Requirements**:
- Run backup service after final photo
- Update e-paper display with session stats

### Use Case 5: Flash Test

**Requirements**:
- Turn flash on for 30 seconds before session starts
- Visual confirmation that hardware is working

---

## Proposed Solution: One-Time Flag on Actions

Instead of a separate data structure, add a `one_time` flag to the existing `PatternAction`. One-time actions use absolute times (fixed or solar) instead of relative offsets.

### Schema Design

Extend existing `PatternAction` with new optional fields:

```python
@dataclass
class PatternAction:
    """
    A single action within an event pattern.

    Regular actions: Use offset_minutes (relative to pattern start)
    One-time actions: Use fixed_time or solar_event (absolute timing)
    """
    action_type: str
    action_name: str
    offset_minutes: int = 0           # For repeating actions
    parameters: dict = {}
    description: str = ""

    # NEW: One-time action fields
    one_time: bool = False            # If True, runs once per trigger cycle
    fixed_time: str | None = None     # "HH:MM" - absolute time
    solar_event: str | None = None    # "dusk", "dawn", etc.
    # Note: offset_minutes is reused - means "offset from timing reference"
    # For repeating actions: offset from pattern start
    # For one-time actions: offset from fixed_time or solar_event
```

### Example Schedule

All actions in one pattern - simple and unified:

```json
{
  "name": "Overnight Moth Survey",
  "trigger_type": "interval",
  "interval_trigger": {
    "interval_minutes": 15,
    "time_window": {
      "start_time": "22:00",
      "end_time": "06:00"
    }
  },
  "patterns": [
    {
      "name": "Moth Survey with UV",
      "actions": [
        {
          "action_type": "gps_sync",
          "action_name": "gps_sync",
          "one_time": true,
          "fixed_time": "20:55",
          "description": "GPS sync before session"
        },
        {
          "action_type": "gpio",
          "action_name": "attract_on",
          "one_time": true,
          "solar_event": "dusk",
          "description": "UV on at dusk"
        },
        {
          "action_type": "gpio",
          "action_name": "flash_on",
          "offset_minutes": 0,
          "description": "Flash + photo cycle (every 15 min)"
        },
        {
          "action_type": "camera",
          "action_name": "takephoto",
          "offset_minutes": 1
        },
        {
          "action_type": "gpio",
          "action_name": "flash_off",
          "offset_minutes": 2
        },
        {
          "action_type": "gpio",
          "action_name": "attract_off",
          "one_time": true,
          "solar_event": "dawn",
          "description": "UV off at dawn"
        },
        {
          "action_type": "service",
          "action_name": "backup",
          "one_time": true,
          "fixed_time": "06:05",
          "description": "Backup after session"
        }
      ]
    }
  ]
}
```

### Key Insight

**Repeating actions** (default):
- `one_time: false` (or omitted)
- Use `offset_minutes` relative to pattern start
- Run every interval

**One-time actions**:
- `one_time: true`
- Use `fixed_time` OR `solar_event` (absolute timing)
- Run once per day at specified time

---

## Resulting Timeline

### Fixed Time Example (9pm-6am)
```
20:55 - gps_sync (one-time, fixed)
21:00 - attract_on (one-time, fixed)
22:00 - flash_on → takephoto → flash_off (interval pattern)
22:15 - flash_on → takephoto → flash_off (interval pattern)
...
06:00 - flash_on → takephoto → flash_off (interval pattern, final)
06:00 - attract_off (one-time, fixed)
06:05 - backup (one-time, fixed)
```

### Solar Trigger Example (dusk-dawn)
```
~19:45 - attract_on (one-time, dusk) [time varies by season/location]
~20:15 - flash_on → takephoto → flash_off (interval pattern starts)
~20:30 - flash_on → takephoto → flash_off
...
~05:30 - flash_on → takephoto → flash_off (interval pattern, final)
~05:45 - attract_off (one-time, dawn) [time varies by season/location]
```

---

## Supported Action Types

One-time actions support all existing action types:

| Type | Actions | Description |
|------|---------|-------------|
| `gpio` | attract_on, attract_off, flash_on, flash_off | GPIO relay control |
| `camera` | takephoto | Photo capture (with HDR/bracket params) |
| `gps_sync` | gps_sync | Synchronize system time with GPS |
| `service` | backup, update_display | System service execution |

### Supported Trigger Types

| Trigger | Example | Description |
|---------|---------|-------------|
| `fixed_time` | "21:00" | Specific clock time (HH:MM) |
| `solar_event` | "dusk" | Solar position (15 events supported) |
| `solar_event` + offset | "sunset" + 30 | Solar event with minute offset |

**Available solar events**: dawn, sunrise, noon, sunset, dusk, civil_dawn, civil_dusk, nautical_dawn, nautical_dusk, astronomical_dawn, astronomical_dusk, golden_hour_start, golden_hour_end, blue_hour_start, blue_hour_end

---

## Extended Examples

### Example 1: Flash Test Before Session

For timed sequences like a 30-second flash test, use a dedicated script that handles its own timing:

```json
{
  "actions": [
    {
      "action_type": "gpio",
      "action_name": "flash_test",
      "one_time": true,
      "fixed_time": "20:59",
      "description": "30-second flash test (script handles timing)"
    }
  ]
}
```

The `flash_test` script turns flash on, waits 30 seconds, then turns off. The scheduler just triggers the script at the specified time.

### Example 2: Power-Optimized Survey (Solar-Based)

```json
{
  "actions": [
    {
      "action_type": "gpio",
      "action_name": "attract_on",
      "one_time": true,
      "solar_event": "astronomical_dusk",
      "description": "UV on when truly dark"
    },
    {
      "action_type": "gpio",
      "action_name": "flash_on",
      "offset_minutes": 0,
      "description": "Repeating photo cycle"
    },
    {
      "action_type": "camera",
      "action_name": "takephoto",
      "offset_minutes": 1
    },
    {
      "action_type": "gpio",
      "action_name": "flash_off",
      "offset_minutes": 2
    },
    {
      "action_type": "gpio",
      "action_name": "attract_off",
      "one_time": true,
      "solar_event": "astronomical_dawn",
      "description": "UV off before any light"
    }
  ]
}
```

### Example 3: Sensor Reading at Session Boundaries

```json
{
  "actions": [
    {
      "action_type": "sensor",
      "action_name": "read_all",
      "one_time": true,
      "solar_event": "dusk",
      "parameters": { "log_to_metadata": true },
      "description": "Log environmental conditions at start"
    },
    {
      "action_type": "camera",
      "action_name": "takephoto",
      "offset_minutes": 0,
      "description": "Regular photo cycle"
    },
    {
      "action_type": "sensor",
      "action_name": "read_all",
      "one_time": true,
      "solar_event": "dawn",
      "parameters": { "log_to_metadata": true },
      "description": "Log conditions at end"
    }
  ]
}
```

### Example 4: Simple Fixed-Time Schedule

Your original use case in the simplest form:

```json
{
  "actions": [
    {
      "action_type": "gpio",
      "action_name": "attract_on",
      "one_time": true,
      "fixed_time": "21:00",
      "description": "UV on at 9pm"
    },
    {
      "action_type": "gpio",
      "action_name": "flash_on",
      "offset_minutes": 0,
      "description": "Flash cycle every 15 min"
    },
    {
      "action_type": "camera",
      "action_name": "takephoto",
      "offset_minutes": 1
    },
    {
      "action_type": "gpio",
      "action_name": "flash_off",
      "offset_minutes": 2
    },
    {
      "action_type": "gpio",
      "action_name": "attract_off",
      "one_time": true,
      "fixed_time": "06:00",
      "description": "UV off at 6am"
    }
  ]
}
```

---

## Implementation

### Backend Changes

| File | Changes |
|------|---------|
| `lib/schedule_schema.py` | Add `one_time`, `fixed_time`, `solar_event` fields to `PatternAction` |
| `lib/schedule_schema.py` | Add validation: one-time actions require `fixed_time` OR `solar_event` |
| `lib/cron_bridge.py` | Filter one-time vs repeating actions; generate separate cron entries |
| `lib/schedule_conflict.py` | Include one-time actions in conflict detection |
| `services/scheduler_service.py` | Validate and process mixed action lists |
| `routes/scheduler_ui.py` | No changes needed (actions already handled) |

### Frontend Changes

| Component | Changes |
|-----------|---------|
| Action editor component | Add one-time toggle, fixed_time/solar_event inputs |
| Pattern preview component | Display one-time actions separately from repeating |
| Schedule hooks | No changes needed (actions already in pattern) |

**Note:** Specific component paths TBD during implementation - will be defined in spec document.

### Schema Validation Rules

```python
def validate_action(action: PatternAction) -> list[str]:
    errors = []
    if action.one_time:
        # One-time actions need absolute timing
        if not action.fixed_time and not action.solar_event:
            errors.append("One-time action requires fixed_time or solar_event")
        if action.offset_minutes != 0:
            errors.append("One-time actions should not use offset_minutes")
    else:
        # Repeating actions use relative timing
        if action.fixed_time or action.solar_event:
            errors.append("Repeating actions should not use fixed_time/solar_event")
    return errors
```

### Cron Generation Strategy

The cron bridge separates one-time and repeating actions:

```python
def schedule_to_cron(schedule: Schedule) -> list[CronEntry]:
    entries = []

    for pattern in schedule.patterns:
        # Split actions by type
        one_time_actions = [a for a in pattern.actions if a.one_time]
        repeating_actions = [a for a in pattern.actions if not a.one_time]

        # One-time actions: absolute time cron entries
        for action in one_time_actions:
            if action.fixed_time:
                entries.extend(fixed_time_to_cron(action))
            elif action.solar_event:
                entries.extend(solar_action_to_cron(action))

        # Repeating actions: interval-based (existing logic)
        entries.extend(pattern_to_cron_entries(repeating_actions, ...))

    return entries
```

**Solar Lookup Table**: Solar times are pre-calculated for 1 year and stored in a lookup table (~55KB). The table is regenerated:
- Quarterly (configurable in settings)
- When GPS location changes by > N km (configurable threshold)
- On user manual refresh
- On schedule activation if table is missing

This eliminates daily recalculation overhead and enables year-ahead schedule preview.

---

## UI Design

All actions (one-time and repeating) are in a unified list within the pattern editor. The UI groups them for clarity:

```
┌─────────────────────────────────────────────────────────────┐
│ Schedule: Overnight Moth Survey                              │
├─────────────────────────────────────────────────────────────┤
│ Trigger: Every 15 min from 22:00 to 06:00                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ PATTERN ACTIONS                                     [+ Add]  │
│                                                              │
│ One-Time Actions (run once at specified time):               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ☀ Dusk      Attract ON     "UV lights on"          [×]  │ │
│ │ 🕐 20:55    GPS Sync       "Time sync"             [×]  │ │
│ │ ☀ Dawn     Attract OFF    "UV lights off"         [×]  │ │
│ │ 🕐 06:05    Backup         "Save photos"           [×]  │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ Repeating Actions (run every 15 min):                        │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ +0 min   Flash ON                                  [×]  │ │
│ │ +1 min   Take Photo                                [×]  │ │
│ │ +2 min   Flash OFF                                 [×]  │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Add Action Modal** (unified for both types):
```
┌─────────────────────────────────────────────────┐
│ Add Action                                       │
├─────────────────────────────────────────────────┤
│                                                  │
│ Action Type: [GPIO            ▼]                │
│ Action:      [Attract ON      ▼]                │
│                                                  │
│ ☑ One-time action (runs once, not every interval)│
│                                                  │
│ ┌─ When to run ─────────────────────────────────┐│
│ │ ○ Fixed Time   ● Solar Event                  ││
│ │                                               ││
│ │ Solar Event: [Dusk            ▼]             ││
│ │ Offset:      [0    ] minutes (before/after)   ││
│ └───────────────────────────────────────────────┘│
│                                                  │
│ Description: [UV lights on at dusk         ]    │
│                                                  │
│            [Cancel]  [Add Action]                │
└─────────────────────────────────────────────────┘
```

When "One-time action" is unchecked, the "When to run" section changes to show `offset_minutes` instead.

---

## Backwards Compatibility

- New fields on `PatternAction` are optional with sensible defaults:
  - `one_time: bool = False`
  - `fixed_time: str | None = None`
  - `solar_event: str | None = None`
- Existing `offset_minutes` field is reused (no new offset field needed)
- Existing schedules work unchanged (all actions default to repeating)
- No breaking changes to API
- JSON serialization includes new fields only when non-default values set

---

## Testing

| Test File | Test Cases |
|-----------|------------|
| `test_schedule_schema.py` | PatternAction with one_time fields: validation, serialization, defaults |
| `test_schedule_schema.py` | Validation errors for invalid combinations (one_time + offset_minutes) |
| `test_cron_bridge.py` | Cron generation for fixed_time one-time actions |
| `test_cron_bridge.py` | Solar event one-time action handling |
| `test_cron_bridge.py` | Mixed pattern with one-time and repeating actions |
| `test_schedule_conflict.py` | Conflicts between one-time and interval actions |
| `test_scheduler_service.py` | End-to-end processing of mixed action patterns |
| Frontend tests | ActionEditor component with one-time toggle and timing inputs |

---

## Success Criteria

- [ ] User can add one-time actions with fixed times
- [ ] User can add one-time actions with solar events
- [ ] One-time actions support all action types (gpio, camera, gps_sync, service)
- [ ] Solar-based one-time actions automatically adjust for season/location
- [ ] Preview timeline shows one-time actions
- [ ] Cron generation includes one-time actions
- [ ] Conflict detection includes one-time actions
- [ ] Existing schedules continue to work unchanged

---

## Future Enhancements

- Sensor actions (read_light, read_temp) with metadata logging
- Conditional one-time actions (only if sensor threshold met)
- Moon phase triggers for one-time actions

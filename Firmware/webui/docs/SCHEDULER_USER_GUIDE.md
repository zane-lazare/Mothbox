# Scheduler User Guide

## Overview

The Mothbox Scheduler enables automated photo capture with flexible timing controls. Create schedules with multiple **routines**, each with its own trigger and action sequence, to run complex surveys autonomously.

### Key Concepts

- **Schedule**: A collection of routines that work together (e.g., "Summer Moth Survey")
- **Routine**: A trigger + actions combination (e.g., "Turn on UV at dusk")
- **Trigger**: When to execute (interval, solar event, moon phase, etc.)
- **Action**: What to do (take photo, control GPIO, sync GPS)
- **Pre-condition**: Optional sensor check before executing actions

### Architecture (Schema 3.0)

Each routine has its own embedded trigger, enabling independent timing:

```
Schedule
└── Routines
    ├── Routine 1: SolarTrigger(dusk) → attract_on
    ├── Routine 2: IntervalTrigger(15min) → flash_on, photo, flash_off
    └── Routine 3: SolarTrigger(dawn) → attract_off
```

This allows mixing trigger types within one schedule—UV on at dusk, photos every 15 minutes, UV off at dawn.

---

## Quick Start

1. Navigate to **Scheduler** page in Web UI
2. Click **New Schedule**
3. Enter name and description
4. Click **Add Routine**
5. Select trigger type and configure timing
6. Add actions (GPIO, camera, GPS sync)
7. Save and **Activate Schedule**

<!-- Screenshot: Schedule editor with routine list -->

---

## Trigger Types

The scheduler supports 7 trigger types.

### Interval Trigger

Execute actions every N minutes within a time window.

| Field | Description |
|-------|-------------|
| Interval Minutes | 1-10,080 (1 min to 7 days) |
| Time Window | Start/end times (HH:MM or solar event) |
| Days of Week | Optional restriction |

**Example**: Photos every 30 minutes from sunset to sunrise
```json
{
  "trigger_type": "interval",
  "interval_minutes": 30,
  "time_window": {"start_time": "sunset", "end_time": "sunrise"}
}
```

### Solar Trigger

Execute at sun-based events with optional offset.

**Supported events** (15 total):
- `sunrise`, `sunset`, `noon`
- `dawn`, `dusk` (sun 6° below horizon)
- `civil_dawn`, `civil_dusk`
- `nautical_dawn`, `nautical_dusk`
- `astronomical_dawn`, `astronomical_dusk`
- `golden_hour_start`, `golden_hour_end`
- `blue_hour_start`, `blue_hour_end`

| Field | Description |
|-------|-------------|
| Solar Event | Which event to trigger on |
| Offset Minutes | -120 to +120 from event |
| Days of Week | Optional restriction |

**Example**: 30 minutes after sunset
```json
{
  "trigger_type": "solar",
  "solar_event": "sunset",
  "offset_minutes": 30
}
```

**Requires**: GPS coordinates for sun position calculation.

### Moon Phase Trigger

Execute on specific lunar phases.

**Phases**: `new`, `waxing_crescent`, `first_quarter`, `waxing_gibbous`, `full`, `waning_gibbous`, `last_quarter`, `waning_crescent`

| Field | Description |
|-------|-------------|
| Phases | One or more phases to match |
| Offset Days | 0-7 days from exact phase |
| Time Window | Optional time restriction |

**Example**: Full moon ±2 days
```json
{
  "trigger_type": "moon_phase",
  "phases": ["full"],
  "offset_days": 2
}
```

### Fixed Time Trigger

Execute at a specific clock time daily.

| Field | Description |
|-------|-------------|
| Time | HH:MM (24-hour format) |
| Days of Week | Optional restriction |

**Example**: Every night at 21:00
```json
{
  "trigger_type": "fixed_time",
  "time": "21:00"
}
```

### Recurring Days Trigger

Execute every N days at a specific time.

| Field | Description |
|-------|-------------|
| Every N Days | 1-365 days |
| Time | HH:MM (24-hour format) |
| Start Date | Optional pattern anchor (YYYY-MM-DD) |

**Example**: Every 3 days at 21:00
```json
{
  "trigger_type": "recurring_days",
  "every_n_days": 3,
  "time": "21:00",
  "start_date": "2025-01-01"
}
```

### Cron Trigger (Expert Mode)

Direct cron expression for advanced patterns.

```
┌─────── minute (0-59)
│ ┌───── hour (0-23)
│ │ ┌─── day of month (1-31)
│ │ │ ┌─ month (1-12)
│ │ │ │ ┌ day of week (0-7)
* * * * *
```

| Pattern | Expression | Description |
|---------|------------|-------------|
| Every hour | `0 * * * *` | Top of each hour |
| Every 15 min | `*/15 * * * *` | Minutes 0, 15, 30, 45 |
| Nightly 9pm | `0 21 * * *` | 21:00 daily |
| Weekends 10pm | `0 22 * * 5,6` | Fri/Sat at 22:00 |

### Sensor Trigger (Pre-condition Only)

Sensor triggers can only be used as **pre-conditions**, not primary triggers. They gate action execution based on sensor readings.

See [Pre-conditions](#pre-conditions) section below.

---

## Pre-conditions

A pre-condition is an optional sensor check that must pass before a routine's actions execute.

### How It Works

1. Primary trigger fires (interval, solar, etc.)
2. System checks pre-condition sensor reading
3. If condition met → actions execute
4. If condition not met → skip this execution, wait for next trigger

### Configuration

| Field | Description |
|-------|-------------|
| Sensor Type | `light`, `temperature`, `motion` |
| Comparison | `gt`, `lt`, `eq`, `gte`, `lte` |
| Threshold | Numeric value (lux, °C, etc.) |

**Example**: Only capture if temperature ≥ 15°C
```json
{
  "routine_id": "abc123",
  "trigger": {"trigger_type": "interval", "interval_minutes": 30},
  "pre_condition": {
    "sensor_type": "temperature",
    "comparison": "gte",
    "threshold": 15.0
  },
  "actions": [...]
}
```

**Hardware Required**: I2C sensor connected and enabled in `controls.txt`.

---

## Built-in Schedules

Two built-in schedules are available as starting points.

### Overnight Moth Survey

Classic moth trapping with UV lights and interval photography.

**Routines**:
1. **UV On at Dusk**: Solar trigger → `attract_on`
2. **Photo Cycle**: Every 15 min (sunset-sunrise) → `flash_on`, `takephoto`, `flash_off`
3. **UV Off at Dawn**: Solar trigger → `attract_off`

**Use case**: Standard nocturnal moth diversity surveys.

### Daytime Pollinator Survey

Simple interval photography during daylight hours.

**Routines**:
1. **Photo Capture**: Every 10 min (sunrise-sunset) → `takephoto`

**Use case**: Pollinator monitoring without artificial lighting.

### Using Built-in Schedules

1. Go to **Scheduler** → **Built-in Schedules**
2. Click a schedule to preview
3. Click **Clone** to create editable copy
4. Customize routines as needed
5. **Activate** when ready

<!-- Screenshot: Built-in schedules list -->

---

## Creating a Schedule

### Step 1: Create Schedule

1. Click **New Schedule**
2. Enter **Name**: e.g., "Summer Moth Survey 2025"
3. Enter **Description**: Document research goals

### Step 2: Add Routines

Click **Add Routine** for each timing pattern needed:

**Routine 1: UV Lights On**
- Trigger: Solar → `dusk`
- Actions: `gpio/attract_on` at offset 0

**Routine 2: Photo Capture**
- Trigger: Interval → 30 minutes, window sunset-sunrise
- Actions:
  - `gpio/flash_on` at offset 0
  - `camera/takephoto` at offset 1
  - `gpio/flash_off` at offset 2

**Routine 3: UV Lights Off**
- Trigger: Solar → `dawn`
- Actions: `gpio/attract_off` at offset 0

<!-- Screenshot: Routine editor with actions -->

### Step 3: Preview

Click **Preview** to see upcoming executions:

```
2025-06-15 20:45:00 - UV lights on (dusk)
2025-06-15 21:00:00 - Flash + Photo
2025-06-15 21:30:00 - Flash + Photo
...
2025-06-16 05:15:00 - UV lights off (dawn)
```

### Step 4: Save and Activate

1. Click **Save Schedule**
2. Click **Activate Schedule**
3. Confirm activation (deactivates any current schedule)

---

## Action Types

| Type | Name | Description |
|------|------|-------------|
| gpio | `attract_on` | Turn on UV attract lights |
| gpio | `attract_off` | Turn off UV attract lights |
| gpio | `flash_on` | Turn on flash |
| gpio | `flash_off` | Turn off flash |
| camera | `takephoto` | Capture photo (supports HDR, focus bracket) |
| gps_sync | `gps_sync` | Synchronize system time with GPS |
| service | `backup` | Run backup routine |
| service | `update_display` | Update e-paper display |

### Action Offsets

Actions use `offset_minutes` relative to the routine's trigger time:

```
Trigger fires at 21:00
├── Action 1: flash_on     (offset: 0)  → 21:00
├── Action 2: takephoto    (offset: 1)  → 21:01
└── Action 3: flash_off    (offset: 2)  → 21:02
```

---

## Conflict Detection

The scheduler detects conflicts between routines and highlights them.

### Conflict Types

| Type | Severity | Description |
|------|----------|-------------|
| Time Overlap | Error (red) | Routines execute at same time |
| Resource Contention | Error (red) | Same resource used simultaneously (camera, GPS) |
| GPIO State Conflict | Warning (yellow) | Conflicting GPIO states (on vs off) |

### Severity Levels

- **Error (red)**: Blocks activation. Must resolve before activating.
- **Warning (yellow)**: Non-blocking. Allows activation with confirmation.

<!-- Screenshot: Conflict warning banner -->

### Resolution

1. Adjust action offsets to avoid overlap
2. Modify time windows to separate routines
3. Remove conflicting actions

---

## Activation and Deactivation

### Single Active Schedule

Only one schedule can be active at a time. Activating a new schedule automatically deactivates the current one.

### Activation Process

1. **Validation**: Check required fields, trigger config
2. **Conflict Check**: Detect time/resource conflicts
3. **Cron Generation**: Convert triggers to cron entries
4. **System Apply**: Write cron jobs, set RTC wakealarm
5. **Mark Active**: Update schedule status

### Deactivation

1. Click active schedule
2. Click **Deactivate**
3. Confirm deactivation

System clears cron jobs and RTC wakealarm.

---

## Troubleshooting

### Schedule Not Executing

| Check | Solution |
|-------|----------|
| Schedule status | Verify "Active" badge is green |
| RTC wakealarm | Run `cat /sys/class/rtc/rtc0/wakealarm` - should show timestamp |
| Cron jobs | Run `crontab -l` - should list Mothbox entries |
| System time | Run `date` - verify timezone is correct |
| Date range | Check current date is within schedule range |
| Battery | Verify RTC battery (CR2032) is fresh |

### Activation Failed

| Error | Solution |
|-------|----------|
| Validation errors | Fix missing fields shown in editor |
| Conflict detected | Resolve conflicts or deactivate conflicting schedule |
| RTC permission denied | Backend needs root/sudo permissions |
| GPS required | Configure GPS for solar/lunar triggers |

### Preview Shows No Executions

| Check | Solution |
|-------|----------|
| Date range | Ensure range includes current/near-future dates |
| Time window | Widen window or reduce interval |
| Days of week | Select more days |
| Moon phase | Increase offset_days or extend preview range |

### Pre-condition Never Passes

| Check | Solution |
|-------|----------|
| Sensor connected | Verify I2C sensor in `controls.txt` |
| Threshold value | Check units (lux for light, °C for temperature) |
| Comparison operator | Verify gt/lt/gte/lte logic |

---

## Best Practices

### For Scientific Surveys

- Use explicit date ranges aligned with ecological seasons
- Document research goals in schedule description
- Enable GPS EXIF tagging for photo geolocation
- Export schedule JSON for reproducibility

### For Power Conservation

- Use solar triggers (adapt to seasonal changes)
- Minimize wakeups (longer intervals)
- Consider no-UV photography for presence/absence data
- Consolidate actions into fewer routines

### For Data Quality

- Allow 3-5 minute settling time between UV on and photo
- Add GPS sync action for accurate timestamps
- Use consistent intervals throughout survey
- Test schedule for 1 week before deployment

---

## Version History

### v3.0 (January 2025)

**Schema 3.0 Refactor** (Issue #296):
- Renamed EventPattern → Routine, PatternAction → Action
- Moved triggers from schedule-level to per-routine
- Added RecurringDaysTrigger (every N days)
- Added pre-conditions for sensor gating
- Replaced pattern library with 2 built-in schedules
- Updated conflict detection with severity levels

### v2.0 (December 2024)

- Visual scheduler UI release
- Six trigger types (interval, solar, moon, fixed, sensor, cron)
- Calendar view and execution preview
- Deployment integration

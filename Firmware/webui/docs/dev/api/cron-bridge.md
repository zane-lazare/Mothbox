# Cron Bridge API

**Issues**: #215, #334
**Module**: `webui/backend/lib/cron_bridge.py`

## Overview

The Cron Bridge translates schedule configurations from `schedule_schema.py` into system cron expressions and RTC wakealarm settings. It enables automated Mothbox operation by converting high-level schedule patterns into low-level system scheduling.

### Schema 3.0 Architecture

In Schema 3.0, triggers are embedded within individual routines rather than at the schedule level. The cron bridge processes schedules using a unified per-routine approach:

```
Schedule → Routines → routine_to_dated_cron() → CronEntry[]
```

All trigger types (fixed time, interval, solar, moon phase, recurring days, cron) produce the same output format: **date-specific cron entries** with explicit day and month values. This provides a consistent, pre-computed approach that unifies all trigger types.

**Key differences from Schema 2.0:**

| Aspect | Schema 2.0 | Schema 3.0 |
|--------|------------|------------|
| Trigger location | Schedule-level | Per-routine embedded |
| Main function | Individual `*_trigger_to_cron()` | `routine_to_dated_cron()` |
| Output format | Repeating patterns (`*/15 * * * *`) | Date-specific (`30 21 15 6 *`) |
| Time range parameter | `days_ahead` | `years_ahead` (default: 1) |
| CronEntry fields | Basic | + `routine_id`, `execution_time` |
| RecurringDaysTrigger | N/A | Fully supported |

## Data Structures

### CronEntry

Represents a single cron job entry with tracking metadata for Schema 3.0.

```python
@dataclass
class CronEntry:
    expression: str                      # e.g., "30 21 15 6 *"
    command: str                         # Full command to execute
    comment: str = ""                    # Optional comment
    enabled: bool = True                 # Whether entry is active
    routine_id: str = ""                 # Links back to source routine
    execution_time: datetime | None = None  # Exact execution time
```

**Methods**:
- `to_cron_line()`: Convert to crontab line format
- `is_valid_expression(expr)`: Static method to validate cron syntax

The `routine_id` field enables tracing cron entries back to their source routine for debugging and management. The `execution_time` field stores the exact datetime for date-specific entries.

### CronBridgeResult

Result of schedule-to-cron conversion.

```python
@dataclass
class CronBridgeResult:
    entries: list[CronEntry]    # Generated cron entries
    rtc_waketime: int | None    # Next waketime as Unix epoch
    schedule_id: str            # Source schedule ID
    errors: list[str] = field(default_factory=list)
```

## Core Functions (Schema 3.0)

These are the primary functions for Schema 3.0 cron generation. New code should use these instead of the legacy trigger converters.

### routine_to_dated_cron

The primary conversion function for Schema 3.0. Generates date-specific cron entries for a routine based on its embedded trigger.

```python
def routine_to_dated_cron(
    routine: Routine,
    latitude: float | None = None,
    longitude: float | None = None,
    timezone_name: str = "UTC",
    years_ahead: int = 1,
) -> list[CronEntry]
```

**Parameters**:
- `routine`: Routine with embedded trigger and actions
- `latitude`: Observer latitude (required for solar triggers)
- `longitude`: Observer longitude (required for solar triggers)
- `timezone_name`: Timezone for calculations (default: "UTC")
- `years_ahead`: Number of years to pre-calculate (default: 1, max recommended)

**Returns**: List of `CronEntry` objects with date-specific expressions

**Example**:
```python
from webui.backend.lib.cron_bridge import routine_to_dated_cron
from webui.backend.lib.schedule_schema import Routine, Action, SolarTrigger

routine = Routine(
    routine_id="r1",
    name="Sunset Capture",
    trigger=SolarTrigger(solar_event="sunset", offset_minutes=30),
    actions=[
        Action(action_type="gpio", action_name="attract_on", offset_minutes=0),
        Action(action_type="camera", action_name="takephoto", offset_minutes=5),
    ],
)

entries = routine_to_dated_cron(
    routine,
    latitude=35.96,
    longitude=-83.92,
    timezone_name="America/New_York",
    years_ahead=1,
)
# Returns ~365 entries per action (730 total) for one year
# Each entry has expression like "30 20 15 6 *" (sunset+30 on June 15)
```

### datetime_to_cron

Helper function to convert a datetime to a date-specific cron expression.

```python
def datetime_to_cron(dt: datetime) -> str
```

**Returns**: Cron expression in format `"minute hour day month *"`

**Example**:
```python
from datetime import datetime
from webui.backend.lib.cron_bridge import datetime_to_cron

dt = datetime(2025, 6, 15, 21, 30)
expr = datetime_to_cron(dt)
# Returns: "30 21 15 6 *"
```

### calculate_execution_times

Dispatcher function that routes to trigger-specific calculators. Returns a flat list of datetime objects representing all execution times within the specified period.

```python
def calculate_execution_times(
    trigger: FixedTimeTrigger | IntervalTrigger | SolarTrigger |
             MoonPhaseTrigger | RecurringDaysTrigger | CronTrigger | SensorTrigger,
    latitude: float | None = None,
    longitude: float | None = None,
    timezone_name: str = "UTC",
    years_ahead: int = 1,
    from_date: date | None = None,
) -> list[datetime]
```

**Parameters**:
- `trigger`: Any supported trigger type
- `latitude`, `longitude`: Required for solar triggers
- `timezone_name`: Timezone for calculations
- `years_ahead`: Number of years to pre-calculate
- `from_date`: Start date (defaults to today)

**Returns**: List of datetime objects for each execution

**Raises**: `ValueError` if trigger is `SensorTrigger` (not schedulable) or unknown type

**Example**:
```python
from datetime import date
from webui.backend.lib.cron_bridge import calculate_execution_times
from webui.backend.lib.schedule_schema import RecurringDaysTrigger

trigger = RecurringDaysTrigger(
    every_n_days=3,
    time="21:00",
    start_date="2025-01-01",
)

times = calculate_execution_times(
    trigger,
    years_ahead=1,
    from_date=date(2025, 1, 1),
)
# Returns ~122 datetime objects (every 3 days for 1 year)
```

### build_action_command

Build command string for a cron entry from an action, optionally wrapped with a sensor pre-condition check.

```python
def build_action_command(
    action: Action,
    pre_condition: SensorTrigger | None = None,
) -> str
```

**Returns**: Command string for cron execution

If `pre_condition` is set, the command is wrapped with `check_and_run.py` that validates the sensor condition before executing the action.

## Execution Time Calculators

Internal functions that compute execution times for each trigger type. These are called by `calculate_execution_times()`.

### _calculate_fixed_time_times

Generates one datetime per matching day at the fixed time.

```python
def _calculate_fixed_time_times(
    trigger: FixedTimeTrigger,
    from_date: date,
    years_ahead: int,
) -> list[datetime]
```

Respects `days_of_week` restriction if set.

### _calculate_interval_times

Generates multiple datetimes within time windows for each matching day.

```python
def _calculate_interval_times(
    trigger: IntervalTrigger,
    from_date: date,
    years_ahead: int,
) -> list[datetime]
```

Handles overnight windows (e.g., 22:00 to 02:00).

### _calculate_solar_times

Calculates solar event times for each day. Requires latitude/longitude.

```python
def _calculate_solar_times(
    trigger: SolarTrigger,
    latitude: float,
    longitude: float,
    timezone_name: str,
    from_date: date,
    years_ahead: int,
) -> list[datetime]
```

Returns empty list for days where solar event doesn't occur (polar regions).

### _calculate_moon_phase_times

Calculates execution times for days matching the moon phase criteria.

```python
def _calculate_moon_phase_times(
    trigger: MoonPhaseTrigger,
    from_date: date,
    years_ahead: int,
) -> list[datetime]
```

Supports `offset_days` for targeting days around the exact phase date.

### _calculate_recurring_days_times

Calculates execution times for "every N days" patterns.

```python
def _calculate_recurring_days_times(
    trigger: RecurringDaysTrigger,
    from_date: date,
    years_ahead: int,
) -> list[datetime]
```

Uses `trigger.start_date` as the pattern anchor if set, otherwise `from_date`.

### _calculate_cron_times

Expands cron expressions using croniter.

```python
def _calculate_cron_times(
    trigger: CronTrigger,
    from_date: date,
    years_ahead: int,
) -> list[datetime]
```

## Schedule Conversion

### schedule_to_cron

Main entry point for converting a complete Schedule to cron entries. Iterates over each routine and generates date-specific cron entries using `routine_to_dated_cron()`.

```python
def schedule_to_cron(
    schedule: Schedule,
    latitude: float | None = None,
    longitude: float | None = None,
    timezone_name: str = "UTC",
    years_ahead: int = 1,
) -> CronBridgeResult
```

**Parameters**:
- `schedule`: Schedule object to convert
- `latitude`, `longitude`: Observer coordinates (required for solar triggers)
- `timezone_name`: Timezone for calculations
- `years_ahead`: Number of years to pre-calculate (default: 1)

**Example**:
```python
from webui.backend.lib.cron_bridge import schedule_to_cron, apply_to_system

result = schedule_to_cron(
    schedule,
    latitude=35.96,
    longitude=-83.92,
    timezone_name="America/New_York",
    years_ahead=1,
)

if result.errors:
    logger.warning(f"Conversion warnings: {result.errors}")

# Apply entries to system
apply_to_system(result.entries, schedule.schedule_id)
```

## Edge Cases

### Polar Latitudes

Solar events (sunrise, sunset) may not occur at extreme latitudes during certain times of year. When a solar trigger cannot calculate an execution time for a given date, that date is silently omitted from the output. No error is raised.

```python
# At 70°N latitude, sunset may not occur in midsummer
entries = routine_to_dated_cron(
    routine_with_sunset_trigger,
    latitude=70.0,
    longitude=25.0,
    years_ahead=1,
)
# Some summer dates will be missing from entries
```

### Crontab Size Limits

System crontabs have practical limits (~10,000 lines). With `years_ahead=1`, a schedule with moderate complexity stays well within limits:

- 1 routine × 1 action × 365 days = 365 entries
- 5 routines × 2 actions × 365 days = 3,650 entries

The default `years_ahead=1` is chosen to balance coverage and crontab size.

### RecurringDaysTrigger Start Date

The `start_date` field determines the anchor for the "every N days" pattern:

```python
trigger = RecurringDaysTrigger(
    every_n_days=3,
    time="21:00",
    start_date="2025-01-01",  # Pattern anchor
)

# With from_date=2025-01-05, first execution is 2025-01-07
# (3 days after 2025-01-04, which is 3 days after start)
```

If `start_date` is not set, `from_date` is used as the anchor.

### SensorTrigger Not Schedulable

`SensorTrigger` cannot be converted to cron entries because it requires real-time sensor polling. It is only valid as a `pre_condition` on a routine (to gate action execution).

```python
# This raises ValueError:
calculate_execution_times(SensorTrigger(sensor_type="motion", ...))

# Correct usage - sensor as pre_condition:
routine = Routine(
    trigger=FixedTimeTrigger(time="21:00"),
    pre_condition=SensorTrigger(
        sensor_type="temperature",
        comparison=">=",
        threshold=15.0,
    ),
    actions=[...],
)
```

## Legacy Trigger Converters

> **Deprecation Notice**: These functions are maintained for backward compatibility. New code should use `routine_to_dated_cron()` instead.

### fixed_time_trigger_to_cron

Convert a FixedTimeTrigger to cron entries (repeating pattern).

```python
def fixed_time_trigger_to_cron(
    trigger: FixedTimeTrigger,
    command: str,
    comment_prefix: str = CRON_COMMENT_PREFIX,
) -> list[CronEntry]
```

**Example**:
```python
trigger = FixedTimeTrigger(time="21:00", days_of_week=[0, 1, 2, 3, 4])
entries = fixed_time_trigger_to_cron(trigger, "/usr/bin/python3 TakePhoto.py")
# Returns: [CronEntry(expression="0 21 * * 1,2,3,4,5", ...)]
```

### interval_trigger_to_cron

Convert an IntervalTrigger to cron entries (repeating pattern).

```python
def interval_trigger_to_cron(
    trigger: IntervalTrigger,
    command: str,
    comment_prefix: str = CRON_COMMENT_PREFIX,
) -> list[CronEntry]
```

**Example**:
```python
trigger = IntervalTrigger(
    interval_minutes=60,
    time_window=TimeWindow(start_time="21:00", end_time="05:00"),
)
entries = interval_trigger_to_cron(trigger, command)
# Returns entries for 21:00, 22:00, 23:00, 00:00, 01:00, 02:00, 03:00, 04:00, 05:00
```

### solar_trigger_to_cron

Convert a SolarTrigger to cron entries for specified days ahead.

```python
def solar_trigger_to_cron(
    trigger: SolarTrigger,
    command: str,
    latitude: float,
    longitude: float,
    timezone_name: str = "UTC",
    days_ahead: int = 7,
    comment_prefix: str = CRON_COMMENT_PREFIX,
) -> list[CronEntry]
```

**Parameters**:
- `days_ahead`: Number of days to pre-calculate (1-365)

**Example**:
```python
trigger = SolarTrigger(solar_event="sunset", offset_minutes=30)
entries = solar_trigger_to_cron(trigger, command, lat=35.96, lon=-83.92, days_ahead=7)
# Returns 7 entries, one for each day at sunset+30
```

### moon_phase_trigger_to_cron

Convert a MoonPhaseTrigger to cron entries.

```python
def moon_phase_trigger_to_cron(
    trigger: MoonPhaseTrigger,
    command: str,
    days_ahead: int = 30,
    comment_prefix: str = CRON_COMMENT_PREFIX,
) -> list[CronEntry]
```

**Parameters**:
- `days_ahead`: Minimum 30 days (one lunar cycle), max 365

**Example**:
```python
trigger = MoonPhaseTrigger(phases=["full"], offset_days=2)
entries = moon_phase_trigger_to_cron(trigger, command, days_ahead=60)
# Returns entries for full moon days +/- 2 days
```

### sensor_trigger_to_cron

Sensor triggers cannot be scheduled via cron (event-driven).

```python
def sensor_trigger_to_cron(
    trigger: SensorTrigger,
    command: str,
) -> list[CronEntry]
```

**Returns**: Empty list with warning logged.

## RTC Wakealarm Functions

### set_rtc_wakealarm

Set the RTC wakealarm for next scheduled wakeup.

```python
def set_rtc_wakealarm(epoch_time: int) -> bool
```

**Path**: `/sys/class/rtc/rtc0/wakealarm`

### clear_rtc_wakealarm

Clear the current RTC wakealarm.

```python
def clear_rtc_wakealarm() -> bool
```

### calculate_next_waketime

Calculate next execution time from cron expression.

```python
def calculate_next_waketime(cron_expression: str) -> int | None
```

**Returns**: Unix epoch timestamp or None on error.

### calculate_next_from_entries

Get the earliest next execution from multiple cron entries.

```python
def calculate_next_from_entries(entries: list[CronEntry]) -> int | None
```

## System Integration

### apply_to_system

Apply cron entries to system crontab.

```python
def apply_to_system(
    entries: list[CronEntry],
    schedule_id: str,
    set_rtc: bool = True,
    user: str | None = None,
) -> bool
```

**Behavior**:
1. Removes existing Mothbox cron jobs
2. Adds new entries
3. Sets RTC wakealarm if enabled

### remove_from_system

Remove all Mothbox cron jobs from system.

```python
def remove_from_system(
    clear_rtc: bool = True,
    user: str | None = None,
) -> bool
```

**Safety**: Only removes jobs matching `is_mothbox_command()` heuristic.

## Schedule Preview

### preview_schedule

Preview upcoming schedule executions without modifying system.

```python
def preview_schedule(
    schedule: Schedule,
    count: int = 10,
    from_time: datetime | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    timezone_name: str = "UTC",
) -> list[dict]
```

**Returns**: List of dicts with:
- `datetime`: ISO 8601 timestamp
- `action_type`: Action type (gpio, camera, etc.)
- `action_name`: Specific action (takephoto, attract_on, etc.)
- `routine_name`: Source routine name
- `routine_id`: Source routine ID

## Integration with SchedulerService

The cron bridge is automatically called by `scheduler_service.py`:

**activate_schedule()**:
```python
result = schedule_to_cron(schedule, latitude, longitude, timezone_name, years_ahead=1)
if result.errors:
    return False, f"Cron conversion failed: {'; '.join(result.errors)}"
apply_to_system(result.entries, schedule_id, set_rtc=True)
```

**deactivate_schedule()**:
```python
remove_from_system(clear_rtc=True)
```

## Security

- Commands are validated against whitelist in `cron_security.py`
- Comment sanitization prevents cron file injection
- Only Mothbox jobs are removed (heuristic detection)

## Dependencies

- `croniter`: Cron expression iteration
- `python-crontab`: System crontab access
- `cron_security.py`: Command whitelist
- `solar_time.py`: Solar event calculations
- `moon_phase.py`: Moon phase calculations
- `schedule_schema.py`: Schedule, Routine, Action, Trigger data structures

## Testing

```bash
# Run all tests
pytest Tests/unit/test_cron_bridge.py -v

# With coverage
pytest Tests/unit/test_cron_bridge.py --cov=webui.backend.lib.cron_bridge
```

**Coverage**: 80%+ (96 tests)

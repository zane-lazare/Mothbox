# Cron Bridge API

**Issue**: #215
**Module**: `webui/backend/lib/cron_bridge.py`

## Overview

The Cron Bridge translates schedule configurations from `schedule_schema.py` into system cron expressions and RTC wakealarm settings. It enables automated Mothbox operation by converting high-level schedule patterns into low-level system scheduling.

## Data Structures

### CronEntry

Represents a single cron job entry.

```python
@dataclass
class CronEntry:
    expression: str  # Cron expression, e.g., "0 21 * * *"
    command: str     # Full command to execute
    comment: str = ""
    enabled: bool = True
```

**Methods**:
- `to_cron_line()`: Convert to crontab line format
- `is_valid_expression(expr)`: Static method to validate cron syntax

### CronBridgeResult

Result of schedule-to-cron conversion.

```python
@dataclass
class CronBridgeResult:
    entries: list[CronEntry]    # Generated cron entries
    rtc_waketime: int | None    # Next waketime as Unix epoch
    schedule_id: str | None     # Source schedule ID
    errors: list[str] = field(default_factory=list)
```

## Trigger Conversion Functions

### fixed_time_trigger_to_cron

Convert a FixedTimeTrigger to cron entries.

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

Convert an IntervalTrigger to cron entries.

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

Convert a SolarTrigger to cron entries. Generates entries for specified number of days ahead.

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

## Schedule Conversion

### schedule_to_cron

Main entry point for converting a complete Schedule to cron entries.

```python
def schedule_to_cron(
    schedule: Schedule,
    latitude: float = 0.0,
    longitude: float = 0.0,
    timezone_name: str = "UTC",
    days_ahead: int = 7,
) -> CronBridgeResult
```

**Example**:
```python
result = schedule_to_cron(schedule, latitude=35.96, longitude=-83.92)
if result.errors:
    logger.warning(f"Conversion warnings: {result.errors}")
# Apply entries to system
apply_to_system(result.entries, schedule.schedule_id)
```

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
    schedule_id: str | None = None,
    set_rtc: bool = True,
    user: bool = True,
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
    user: bool = True,
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
result = schedule_to_cron(schedule, latitude, longitude, timezone_name)
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
- `schedule_schema.py`: Schedule data structures

## Testing

```bash
# Run all tests
pytest Tests/unit/test_cron_bridge.py -v

# With coverage
pytest Tests/unit/test_cron_bridge.py --cov=webui.backend.lib.cron_bridge
```

**Coverage**: 80%+ (96 tests)

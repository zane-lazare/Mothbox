"""
Cron Bridge - Translates schedule configurations to cron expressions.

This module converts Schedule objects from schedule_schema.py into
system cron expressions and RTC wakealarm settings.

Issue: #215
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Final

from croniter import croniter
from crontab import CronTab

from mothbox_paths import MOTHBOX_HOME
from webui.backend.lib.cron_security import (
    get_script_key_for_action,
    get_validated_command,
    is_mothbox_command,
)
from webui.backend.lib.moon_phase import get_moon_phase, is_within_moon_phase
from webui.backend.lib.schedule_schema import (
    Action,
    CronTrigger,
    FixedTimeTrigger,
    IntervalTrigger,
    MoonPhaseTrigger,
    RecurringDaysTrigger,
    Routine,
    Schedule,
    SensorTrigger,
    SolarTrigger,
)
from webui.backend.lib.solar_time import parse_time_spec

logger = logging.getLogger(__name__)

# Constants
CRON_COMMENT_PREFIX: Final[str] = "Mothbox:"
RTC_WAKEALARM_PATH: Final[str] = "/sys/class/rtc/rtc0/wakealarm"
LUNAR_CYCLE_DAYS: Final[int] = 30  # Minimum days to look ahead for moon phase schedules

# Pre-compiled regex patterns for cron field validation (performance optimization)
_CRON_FIELD_PATTERNS: Final[tuple[re.Pattern, ...]] = (
    re.compile(r"^(\*|([0-5]?\d)(,([0-5]?\d))*|([0-5]?\d)-([0-5]?\d)|\*/([1-5]?\d))$"),  # minute
    re.compile(
        r"^(\*|([01]?\d|2[0-3])(,([01]?\d|2[0-3]))*|([01]?\d|2[0-3])-([01]?\d|2[0-3])|\*/([01]?\d|2[0-3]))$"
    ),  # hour
    re.compile(
        r"^(\*|([1-9]|[12]\d|3[01])(,([1-9]|[12]\d|3[01]))*|([1-9]|[12]\d|3[01])-([1-9]|[12]\d|3[01])|\*/([1-9]|[12]\d|3[01]))$"
    ),  # day
    re.compile(
        r"^(\*|([1-9]|1[0-2])(,([1-9]|1[0-2]))*|([1-9]|1[0-2])-([1-9]|1[0-2])|\*/([1-9]|1[0-2]))$"
    ),  # month
    re.compile(r"^(\*|[0-7](,[0-7])*|[0-7]-[0-7]|\*/[0-7])$"),  # weekday
)

# Cron field range validation constants
_CRON_FIELD_RANGES: Final[dict[str, tuple[int, int]]] = {
    "minute": (0, 59),
    "hour": (0, 23),
    "day": (1, 31),
    "month": (1, 12),
    "weekday": (0, 7),  # 0 and 7 both represent Sunday
}


@dataclass
class CronEntry:
    """Represents a single cron job entry.

    Attributes:
        expression: Cron expression (e.g., "0 21 * * *")
        command: Full command to execute
        comment: Optional comment for the job
        enabled: Whether the entry is enabled
        routine_id: ID of the source routine (for tracking)
    """

    expression: str  # e.g., "0 21 * * *"
    command: str  # e.g., "/usr/bin/python3 /opt/mothbox/TakePhoto.py"
    comment: str = ""
    enabled: bool = True
    routine_id: str = ""  # Links back to source routine
    execution_time: datetime | None = None  # Exact execution time

    def to_cron_line(self) -> str:
        """Convert entry to crontab line format.

        Returns:
            String in crontab format with optional comment line.
            Disabled entries are commented out with #.
        """
        lines = []

        # Add comment if present (sanitize to prevent injection)
        if self.comment:
            # Remove newlines and additional # to prevent comment injection
            clean_comment = self.comment.replace("\n", " ").replace("#", "")
            lines.append(f"# {clean_comment}")

        # Add cron expression and command
        cron_line = f"{self.expression} {self.command}"
        if not self.enabled:
            cron_line = f"# {cron_line}"

        lines.append(cron_line)

        return "\n".join(lines)

    @staticmethod
    def is_valid_expression(expr: str) -> bool:
        """Validate cron expression syntax.

        Args:
            expr: Cron expression string to validate

        Returns:
            True if expression is valid cron syntax, False otherwise
        """
        if not expr or not isinstance(expr, str):
            return False

        # Split expression into fields
        fields = expr.split()

        # Cron expression must have exactly 5 fields (minute hour day month weekday)
        if len(fields) != 5:
            return False

        # Validate each field using pre-compiled patterns
        for field_value, pattern in zip(fields, _CRON_FIELD_PATTERNS, strict=True):
            # Handle range expressions (e.g., 9-17)
            if "-" in field_value and not field_value.startswith("*/"):
                parts = field_value.split("-")
                if len(parts) == 2:
                    try:
                        start, end = int(parts[0]), int(parts[1])
                        if start > end:
                            return False
                    except ValueError:
                        return False

            # Handle step expressions (e.g., */5)
            if field_value.startswith("*/"):
                try:
                    step = int(field_value[2:])
                    if step <= 0:
                        return False
                except ValueError:
                    return False
                continue

            # Handle comma-separated lists (e.g., 0,30)
            if "," in field_value:
                values = field_value.split(",")
                for val in values:
                    if not val.strip():
                        return False
                continue

            # Validate against pre-compiled pattern
            if not pattern.match(field_value):
                return False

        # Additional validation: check numeric ranges using constants
        try:
            field_names = ("minute", "hour", "day", "month", "weekday")
            for field_value, field_name in zip(fields, field_names, strict=True):
                # Skip wildcards, steps, lists, and ranges
                if (
                    field_value == "*"
                    or field_value.startswith("*/")
                    or "," in field_value
                    or "-" in field_value
                ):
                    continue

                min_val, max_val = _CRON_FIELD_RANGES[field_name]
                val = int(field_value)
                if val < min_val or val > max_val:
                    return False

        except (ValueError, IndexError, KeyError):
            return False

        return True


@dataclass
class CronBridgeResult:
    """Result of schedule-to-cron conversion.

    Attributes:
        entries: List of cron entries generated
        rtc_waketime: Unix timestamp for RTC alarm (None if not applicable)
        schedule_id: ID of the schedule converted
        errors: List of warnings/errors encountered
    """

    entries: list[CronEntry]
    rtc_waketime: int | None
    schedule_id: str
    errors: list[str] = field(default_factory=list)


# =============================================================================
# TRIGGER CONVERSION FUNCTIONS
# =============================================================================


def _iso_to_cron_weekday(iso_days: list[int] | None) -> str:
    """Convert ISO weekday list to cron weekday string.

    Args:
        iso_days: List of ISO weekdays (0=Mon..6=Sun) or None for all days

    Returns:
        Cron weekday string (e.g., "1,2,3,4,5" for weekdays or "*" for all)
    """
    if iso_days is None:
        return "*"
    # ISO: 0=Mon..6=Sun -> Cron: 0=Sun..6=Sat
    # Formula: (iso_day + 1) % 7
    cron_days = sorted([(d + 1) % 7 for d in iso_days])
    return ",".join(str(d) for d in cron_days)


def _generate_execution_times(
    start_hour: int,
    start_minute: int,
    end_hour: int,
    end_minute: int,
    interval_minutes: int,
) -> list[tuple[int, int]]:
    """Generate (hour, minute) tuples for execution times within window.

    Handles overnight windows (end < start).

    Args:
        start_hour: Starting hour (0-23)
        start_minute: Starting minute (0-59)
        end_hour: Ending hour (0-23)
        end_minute: Ending minute (0-59)
        interval_minutes: Interval between executions in minutes

    Returns:
        List of (hour, minute) tuples representing execution times
    """
    times = []

    # Convert to minutes since midnight for easier arithmetic
    start_mins = start_hour * 60 + start_minute
    end_mins = end_hour * 60 + end_minute

    # Handle overnight window (e.g., 22:00 to 02:00)
    if end_mins < start_mins:
        end_mins += 24 * 60  # Add 24 hours to end

    current = start_mins
    while current <= end_mins:
        # Normalize to 24-hour format
        normalized = current % (24 * 60)
        hour = normalized // 60
        minute = normalized % 60
        times.append((hour, minute))
        current += interval_minutes

    return times


def datetime_to_cron(dt: datetime) -> str:
    """Convert datetime to date-specific cron expression.

    Generates a cron expression that will execute once at the specific
    date and time represented by the datetime object.

    Args:
        dt: Datetime object to convert

    Returns:
        Cron expression in format: "minute hour day month *"
        The weekday field is always "*" since day/month is specific.

    Example:
        >>> datetime_to_cron(datetime(2025, 6, 15, 21, 30))
        '30 21 15 6 *'
    """
    return f"{dt.minute} {dt.hour} {dt.day} {dt.month} *"


# =============================================================================
# EXECUTION TIME CALCULATORS (for unified date-specific cron generation)
# =============================================================================


def _calculate_fixed_time_times(
    trigger: FixedTimeTrigger,
    from_date: date,
    years_ahead: int,
) -> list[datetime]:
    """Calculate execution times for a fixed time trigger.

    Fixed time triggers execute at the same time every day (or specific
    days of the week). We generate one datetime per matching day.

    Args:
        trigger: FixedTimeTrigger with time and optional days_of_week
        from_date: Start date for calculations
        years_ahead: Number of years to calculate ahead

    Returns:
        List of datetime objects for each execution
    """
    hour, minute = map(int, trigger.time.split(":"))
    end_date = from_date + timedelta(days=years_ahead * 365)

    times = []
    current = from_date
    while current <= end_date:
        # Check day-of-week restriction
        if trigger.days_of_week is None or current.weekday() in trigger.days_of_week:
            times.append(datetime(current.year, current.month, current.day, hour, minute))
        current += timedelta(days=1)

    return times


def _calculate_interval_times(
    trigger: IntervalTrigger,
    from_date: date,
    years_ahead: int,
) -> list[datetime]:
    """Calculate execution times for an interval trigger.

    Interval triggers execute at regular intervals within a time window.
    We generate datetimes for each execution within the window for each
    matching day.

    Args:
        trigger: IntervalTrigger with interval_minutes, time_window, optional days_of_week
        from_date: Start date for calculations
        years_ahead: Number of years to calculate ahead

    Returns:
        List of datetime objects for each execution
    """
    start_hour, start_minute = map(int, trigger.time_window.start_time.split(":"))
    end_hour, end_minute = map(int, trigger.time_window.end_time.split(":"))
    end_date = from_date + timedelta(days=years_ahead * 365)

    # Generate time-of-day execution times
    exec_times = _generate_execution_times(
        start_hour, start_minute, end_hour, end_minute, trigger.interval_minutes
    )

    times = []
    current = from_date
    while current <= end_date:
        # Check day-of-week restriction
        if trigger.days_of_week is None or current.weekday() in trigger.days_of_week:
            for hour, minute in exec_times:
                times.append(datetime(current.year, current.month, current.day, hour, minute))
        current += timedelta(days=1)

    return times


def _calculate_solar_times(
    trigger: SolarTrigger,
    latitude: float,
    longitude: float,
    timezone_name: str,
    from_date: date,
    years_ahead: int,
) -> list[datetime]:
    """Calculate execution times for a solar trigger.

    Solar triggers execute at sun-based events (sunrise, sunset, etc.)
    which vary by date and location.

    Args:
        trigger: SolarTrigger with solar_event, offset_minutes, optional days_of_week
        latitude: Observer latitude
        longitude: Observer longitude
        timezone_name: Timezone for calculations
        from_date: Start date for calculations
        years_ahead: Number of years to calculate ahead

    Returns:
        List of datetime objects for each execution
    """
    end_date = from_date + timedelta(days=years_ahead * 365)

    times = []
    current = from_date
    while current <= end_date:
        # Check day-of-week restriction
        if trigger.days_of_week is not None and current.weekday() not in trigger.days_of_week:
            current += timedelta(days=1)
            continue

        exec_time = get_solar_execution_time(trigger, current, latitude, longitude, timezone_name)
        if exec_time is not None:
            times.append(exec_time)
        current += timedelta(days=1)

    return times


def _calculate_moon_phase_times(
    trigger: MoonPhaseTrigger,
    from_date: date,
    years_ahead: int,
) -> list[datetime]:
    """Calculate execution times for a moon phase trigger.

    Moon phase triggers execute when the moon is in a specific phase.

    Args:
        trigger: MoonPhaseTrigger with phases, offset_days, optional time_window
        from_date: Start date for calculations
        years_ahead: Number of years to calculate ahead

    Returns:
        List of datetime objects for each execution
    """
    # Determine execution time from time_window or default to midnight
    if trigger.time_window:
        hour, minute = map(int, trigger.time_window.start_time.split(":"))
    else:
        hour, minute = 0, 0

    end_date = from_date + timedelta(days=years_ahead * 365)

    times = []
    current = from_date
    while current <= end_date:
        if is_moon_phase_active(trigger, current):
            times.append(datetime(current.year, current.month, current.day, hour, minute))
        current += timedelta(days=1)

    return times


def _calculate_recurring_days_times(
    trigger: RecurringDaysTrigger,
    from_date: date,
    years_ahead: int,
) -> list[datetime]:
    """Calculate execution times for a recurring days trigger.

    Recurring days triggers execute every N days from a start date.

    Args:
        trigger: RecurringDaysTrigger with every_n_days, time, start_date
        from_date: Start date for calculations (overrides trigger.start_date)
        years_ahead: Number of years to calculate ahead

    Returns:
        List of datetime objects for each execution
    """
    if not trigger.time or trigger.every_n_days < 1:
        return []

    hour, minute = map(int, trigger.time.split(":"))

    # Use trigger's start_date if specified, otherwise use from_date
    start = date.fromisoformat(trigger.start_date) if trigger.start_date else from_date
    end_date = from_date + timedelta(days=years_ahead * 365)

    times = []
    current = start
    while current <= end_date:
        days_since_start = (current - start).days
        if (
            days_since_start >= 0
            and days_since_start % trigger.every_n_days == 0
            and current >= from_date  # Only include dates from from_date onwards
        ):
            times.append(datetime(current.year, current.month, current.day, hour, minute))
        current += timedelta(days=1)

    return times


def _calculate_cron_times(
    trigger: CronTrigger,
    from_date: date,
    years_ahead: int,
) -> list[datetime]:
    """Calculate execution times for a cron expression trigger.

    Uses croniter to expand the cron expression into specific datetimes.

    Args:
        trigger: CronTrigger with cron_expression
        from_date: Start date for calculations
        years_ahead: Number of years to calculate ahead

    Returns:
        List of datetime objects for each execution
    """
    if not CronEntry.is_valid_expression(trigger.cron_expression):
        return []

    from_datetime = datetime.combine(from_date, datetime.min.time())
    end_datetime = from_datetime + timedelta(days=years_ahead * 365)

    times = []
    cron = croniter(trigger.cron_expression, from_datetime)

    while True:
        next_time = cron.get_next(datetime)
        if next_time > end_datetime:
            break
        times.append(next_time)

    return times


def calculate_execution_times(
    trigger: FixedTimeTrigger
    | IntervalTrigger
    | SolarTrigger
    | MoonPhaseTrigger
    | RecurringDaysTrigger
    | CronTrigger
    | SensorTrigger,
    latitude: float | None = None,
    longitude: float | None = None,
    timezone_name: str = "UTC",
    years_ahead: int = 1,
    from_date: date | None = None,
) -> list[datetime]:
    """Calculate all execution times for a trigger over a given period.

    Dispatches to trigger-specific calculators. All return a flat list
    of datetime objects representing when the trigger should fire.

    Args:
        trigger: Any trigger type (Interval, Solar, Moon, etc.)
        latitude: Observer latitude (required for solar triggers)
        longitude: Observer longitude (required for solar triggers)
        timezone_name: Timezone for calculations
        years_ahead: Number of years to pre-calculate
        from_date: Start date (defaults to today)

    Returns:
        List of datetime objects for each execution

    Raises:
        ValueError: If trigger type is SensorTrigger (not schedulable) or unknown
    """
    if from_date is None:
        from_date = date.today()

    if isinstance(trigger, FixedTimeTrigger):
        return _calculate_fixed_time_times(trigger, from_date, years_ahead)

    if isinstance(trigger, IntervalTrigger):
        return _calculate_interval_times(trigger, from_date, years_ahead)

    if isinstance(trigger, SolarTrigger):
        if latitude is None or longitude is None:
            raise ValueError("Solar triggers require latitude and longitude")
        return _calculate_solar_times(
            trigger, latitude, longitude, timezone_name, from_date, years_ahead
        )

    if isinstance(trigger, MoonPhaseTrigger):
        return _calculate_moon_phase_times(trigger, from_date, years_ahead)

    if isinstance(trigger, RecurringDaysTrigger):
        return _calculate_recurring_days_times(trigger, from_date, years_ahead)

    if isinstance(trigger, CronTrigger):
        return _calculate_cron_times(trigger, from_date, years_ahead)

    if isinstance(trigger, SensorTrigger):
        raise ValueError(
            "SensorTrigger cannot be scheduled via cron - it requires real-time sensor polling"
        )

    raise ValueError(f"Unknown trigger type: {type(trigger).__name__}")


def build_action_command(
    action: Action,
    pre_condition: SensorTrigger | None = None,
) -> str:
    """Build command string for cron entry.

    If pre_condition is set, wraps the command with a sensor check script.

    Args:
        action: Action to build command for
        pre_condition: Optional sensor trigger as gate condition

    Returns:
        Command string for cron execution
    """
    script_key = get_script_key_for_action(action.action_type, action.action_name)
    if script_key:
        base_command = get_validated_command(script_key)
    else:
        base_command = f"# Unknown action: {action.action_type}/{action.action_name}"

    if pre_condition:
        # Wrap with pre-condition checker using path from mothbox_paths
        check_and_run_script = MOTHBOX_HOME / "check_and_run.py"
        return (
            f"python3 {check_and_run_script} "
            f"--sensor {pre_condition.sensor_type} "
            f"--op {pre_condition.comparison} "
            f"--threshold {pre_condition.threshold} "
            f"-- {base_command}"
        )

    return base_command


def routine_to_dated_cron(
    routine: Routine,
    latitude: float | None = None,
    longitude: float | None = None,
    timezone_name: str = "UTC",
    years_ahead: int = 1,
) -> list[CronEntry]:
    """Generate date-specific cron entries for a routine.

    All trigger types produce the same output format: date-specific cron entries.
    This unifies solar, moon, interval, and recurring_days triggers into a
    consistent pre-computed cron entry format.

    Args:
        routine: Routine with embedded trigger and actions
        latitude: Observer latitude (required for solar triggers)
        longitude: Observer longitude (required for solar triggers)
        timezone_name: Timezone for calculations
        years_ahead: Number of years to pre-calculate

    Returns:
        List of CronEntry objects with date-specific expressions

    Raises:
        ValueError: If trigger requires coordinates but none provided

    Example:
        >>> routine = Routine(
        ...     routine_id="r1",
        ...     trigger=FixedTimeTrigger(time="21:00", days_of_week=None),
        ...     actions=[Action(action_type="camera", action_name="takephoto", offset_minutes=0)],
        ... )
        >>> entries = routine_to_dated_cron(routine, years_ahead=1)
        >>> len(entries)  # ~365 entries for 1 year
        365
    """
    if routine.trigger is None:
        return []

    execution_times = calculate_execution_times(
        trigger=routine.trigger,
        latitude=latitude,
        longitude=longitude,
        timezone_name=timezone_name,
        years_ahead=years_ahead,
    )

    entries = []
    routine_name = routine.get_display_name()

    for exec_time in execution_times:
        for action in routine.actions:
            # Apply action offset
            action_time = exec_time + timedelta(minutes=action.offset_minutes)

            entries.append(
                CronEntry(
                    expression=datetime_to_cron(action_time),
                    command=build_action_command(action, routine.pre_condition),
                    comment=f"{CRON_COMMENT_PREFIX} {routine_name} ({action_time.date().isoformat()})",
                    routine_id=routine.routine_id,
                    execution_time=action_time,
                )
            )

    return entries


def fixed_time_trigger_to_cron(
    trigger: FixedTimeTrigger,
    command: str,
    comment_prefix: str = CRON_COMMENT_PREFIX,
) -> list[CronEntry]:
    """Convert FixedTimeTrigger to cron entries.

    Args:
        trigger: FixedTimeTrigger with time (HH:MM) and optional days_of_week
        command: Full command string to execute
        comment_prefix: Prefix for cron comment

    Returns:
        List containing single CronEntry

    Note:
        ISO weekday (0=Mon..6=Sun) is converted to cron weekday (0=Sun..6=Sat)
    """
    # Parse HH:MM
    hour, minute = map(int, trigger.time.split(":"))

    # Convert ISO weekday to cron weekday using helper function
    dow_str = _iso_to_cron_weekday(trigger.days_of_week)

    expression = f"{minute} {hour} * * {dow_str}"

    comment = f"{comment_prefix} Fixed time {trigger.time}"
    if trigger.days_of_week:
        comment += f" on days {trigger.days_of_week}"

    return [CronEntry(expression=expression, command=command, comment=comment)]


def interval_trigger_to_cron(
    trigger: IntervalTrigger,
    command: str,
    comment_prefix: str = CRON_COMMENT_PREFIX,
) -> list[CronEntry]:
    """Convert IntervalTrigger to cron entries.

    Args:
        trigger: IntervalTrigger with interval_minutes, time_window, optional days_of_week
        command: Full command string to execute
        comment_prefix: Prefix for cron comment

    Returns:
        List of CronEntry objects, one per execution time within the window
    """
    # Parse time window
    start_hour, start_minute = map(int, trigger.time_window.start_time.split(":"))
    end_hour, end_minute = map(int, trigger.time_window.end_time.split(":"))

    # Generate execution times
    exec_times = _generate_execution_times(
        start_hour, start_minute, end_hour, end_minute, trigger.interval_minutes
    )

    # Convert days of week
    dow_str = _iso_to_cron_weekday(trigger.days_of_week)

    # Create cron entries
    entries = []
    for hour, minute in exec_times:
        expression = f"{minute} {hour} * * {dow_str}"
        comment = (
            f"{comment_prefix} Interval {trigger.interval_minutes}min at {hour:02d}:{minute:02d}"
        )
        entries.append(CronEntry(expression=expression, command=command, comment=comment))

    return entries


# =============================================================================
# RTC WAKEALARM FUNCTIONS
# =============================================================================


def calculate_next_waketime(
    cron_expression: str,
    from_time: datetime | None = None,
) -> int:
    """Calculate next execution time as Unix epoch.

    Uses python-crontab library (same pattern as Scheduler.py).

    Args:
        cron_expression: Cron expression (e.g., "0 21 * * *")
        from_time: Calculate from this time (defaults to now)

    Returns:
        Unix timestamp of next execution

    Raises:
        ValueError: If cron expression is invalid or calculation fails
    """
    if from_time is None:
        from_time = datetime.now()

    try:
        # Create a temporary cron job to calculate schedule
        cron = CronTab(tab="")  # In-memory crontab
        job = cron.new(command="placeholder")
        job.setall(cron_expression)

        # Get next execution time
        schedule = job.schedule(date_from=from_time)
        next_scheduled = schedule.get_next()

        return int(next_scheduled.timestamp())
    except (KeyError, AttributeError, TypeError) as e:
        raise ValueError(f"Invalid cron expression '{cron_expression}': {e}") from e


def calculate_next_from_entries(
    entries: list[CronEntry],
    from_time: datetime | None = None,
) -> int | None:
    """Return earliest next execution from multiple cron entries.

    Args:
        entries: List of CronEntry objects
        from_time: Calculate from this time (defaults to now)

    Returns:
        Unix timestamp of earliest next execution, or None if no entries
    """
    if not entries:
        return None

    if from_time is None:
        from_time = datetime.now()

    next_times = []
    for entry in entries:
        if entry.enabled:
            try:
                next_time = calculate_next_waketime(entry.expression, from_time)
                next_times.append(next_time)
            except (ValueError, KeyError):
                # Skip invalid expressions
                continue

    return min(next_times) if next_times else None


def set_rtc_wakealarm(epoch_time: int) -> bool:
    """Set RTC wakealarm (Pi5).

    Reference: Scheduler.py lines 702-716

    Args:
        epoch_time: Unix timestamp for wakeup

    Returns:
        True if successful, False on error
    """
    try:
        with open(RTC_WAKEALARM_PATH, "w") as f:
            f.write(str(epoch_time))
        logger.info(f"Set RTC wakealarm to {epoch_time}")
        return True
    except (PermissionError, FileNotFoundError, OSError) as e:
        logger.error(f"Failed to set RTC wakealarm: {e}")
        return False


def clear_rtc_wakealarm() -> bool:
    """Clear existing RTC wakealarm.

    Writes "0" to clear the alarm.

    Returns:
        True if successful, False on error
    """
    try:
        with open(RTC_WAKEALARM_PATH, "w") as f:
            f.write("0")
        logger.info("Cleared RTC wakealarm")
        return True
    except (PermissionError, FileNotFoundError, OSError) as e:
        logger.error(f"Failed to clear RTC wakealarm: {e}")
        return False


def get_solar_execution_time(
    trigger: SolarTrigger,
    target_date: date,
    latitude: float,
    longitude: float,
    timezone_name: str = "UTC",
) -> datetime | None:
    """Calculate execution time for a solar trigger on a specific date.

    Args:
        trigger: SolarTrigger with solar_event and offset_minutes
        target_date: Date to calculate for
        latitude: Observer latitude
        longitude: Observer longitude
        timezone_name: Timezone for calculations

    Returns:
        Datetime of execution, or None if event doesn't occur (polar regions)
    """
    # Build time_spec string (e.g., "sunset+30" or "sunrise-15")
    if trigger.offset_minutes >= 0:
        time_spec = f"{trigger.solar_event}+{trigger.offset_minutes}"
    else:
        time_spec = f"{trigger.solar_event}{trigger.offset_minutes}"

    try:
        return parse_time_spec(time_spec, target_date, latitude, longitude, timezone_name)
    except ValueError:
        # Solar event doesn't occur on this date (e.g., polar regions)
        return None


def solar_trigger_to_cron(
    trigger: SolarTrigger,
    command: str,
    latitude: float,
    longitude: float,
    timezone_name: str = "UTC",
    days_ahead: int = 7,
    from_date: date | None = None,
    comment_prefix: str = CRON_COMMENT_PREFIX,
) -> list[CronEntry]:
    """Convert SolarTrigger to cron entries for upcoming days.

    Pre-calculates solar times for the next N days and generates fixed
    cron entries for each day. Requires regeneration when approaching
    the end of the pre-calculated period.

    Args:
        trigger: SolarTrigger with solar_event, offset_minutes, optional days_of_week
        command: Full command string to execute
        latitude: Observer latitude
        longitude: Observer longitude
        timezone_name: Timezone for calculations
        days_ahead: Number of days to pre-calculate (default 7)
        from_date: Start date (defaults to today)
        comment_prefix: Prefix for cron comment

    Returns:
        List of CronEntry objects, one per day the trigger should execute

    Raises:
        ValueError: If days_ahead is not in range 1-365
    """
    if not 1 <= days_ahead <= 365:
        raise ValueError(
            f"days_ahead must be between 1 and 365, got {days_ahead}. "
            "Values beyond 365 days lead to excessive computation and memory usage."
        )

    if from_date is None:
        from_date = date.today()

    entries = []

    for day_offset in range(days_ahead):
        target_date = from_date + timedelta(days=day_offset)

        # Check day-of-week restriction (ISO: 0=Mon..6=Sun)
        if trigger.days_of_week is not None and target_date.weekday() not in trigger.days_of_week:
            continue

        # Calculate execution time for this date
        exec_time = get_solar_execution_time(
            trigger, target_date, latitude, longitude, timezone_name
        )

        if exec_time is None:
            # Solar event doesn't occur (polar region handling)
            continue

        # Build cron expression with specific day and month
        # Format: minute hour day month weekday
        expression = f"{exec_time.minute} {exec_time.hour} {target_date.day} {target_date.month} *"

        comment = (
            f"{comment_prefix} {trigger.solar_event}"
            f"{'+' if trigger.offset_minutes >= 0 else ''}{trigger.offset_minutes}min "
            f"on {target_date.isoformat()}"
        )

        entries.append(CronEntry(expression=expression, command=command, comment=comment))

    return entries


def is_moon_phase_active(
    trigger: MoonPhaseTrigger,
    target_date: date,
) -> bool:
    """Check if moon phase trigger should be active on target_date.

    Args:
        trigger: MoonPhaseTrigger with phases and offset_days
        target_date: Date to check

    Returns:
        True if date matches any of the trigger's phases within offset tolerance
    """
    for phase in trigger.phases:
        if is_within_moon_phase(target_date, phase, trigger.offset_days):
            return True
    return False


def moon_phase_trigger_to_cron(
    trigger: MoonPhaseTrigger,
    command: str,
    days_ahead: int = 30,
    from_date: date | None = None,
    comment_prefix: str = CRON_COMMENT_PREFIX,
) -> list[CronEntry]:
    """Convert MoonPhaseTrigger to cron entries for upcoming matching days.

    Pre-calculates which days match the moon phase criteria and generates
    fixed cron entries for each matching day.

    Args:
        trigger: MoonPhaseTrigger with phases, offset_days, optional time_window
        command: Full command string to execute
        days_ahead: Number of days to pre-calculate (default 30)
        from_date: Start date (defaults to today)
        comment_prefix: Prefix for cron comment

    Returns:
        List of CronEntry objects, one per day that matches the moon phase criteria

    Raises:
        ValueError: If days_ahead is not in range 1-365
    """
    if not 1 <= days_ahead <= 365:
        raise ValueError(
            f"days_ahead must be between 1 and 365, got {days_ahead}. "
            "Values beyond 365 days lead to excessive computation and memory usage."
        )

    if from_date is None:
        from_date = date.today()

    # Determine execution time from time_window or default to midnight
    if trigger.time_window:
        hour, minute = map(int, trigger.time_window.start_time.split(":"))
    else:
        hour, minute = 0, 0

    entries = []

    for day_offset in range(days_ahead):
        target_date = from_date + timedelta(days=day_offset)

        # Check if this date matches the moon phase criteria
        if not is_moon_phase_active(trigger, target_date):
            continue

        # Build cron expression with specific day and month
        expression = f"{minute} {hour} {target_date.day} {target_date.month} *"

        # Get current moon phase for comment
        phase_info = get_moon_phase(target_date)
        comment = (
            f"{comment_prefix} Moon phase ({phase_info['phase']}) on {target_date.isoformat()}"
        )

        entries.append(CronEntry(expression=expression, command=command, comment=comment))

    return entries


def cron_to_human_readable(expression: str) -> str:
    """Convert cron expression to human-readable text.

    Handles common patterns and provides a fallback for complex expressions.

    Args:
        expression: Cron expression string (e.g., "*/5 * * * *")

    Returns:
        Human-readable description of the schedule

    Examples:
        - "*/5 * * * *" -> "Every 5 minutes"
        - "0 * * * *" -> "Every hour"
        - "0 21 * * *" -> "Daily at 9:00 PM"
        - "0 0 * * 0" -> "Weekly on Sunday at midnight"
        - "0,30 * * * *" -> "At minute 0 and 30"
    """
    if not expression or not isinstance(expression, str):
        return "Custom schedule"

    fields = expression.split()
    if len(fields) != 5:
        return "Custom schedule"

    minute, hour, day, month, weekday = fields

    # Every minute
    if expression == "* * * * *":
        return "Every minute"

    # Every N minutes: */N * * * *
    if minute.startswith("*/") and hour == "*" and day == "*" and month == "*" and weekday == "*":
        try:
            interval = int(minute[2:])
            return f"Every {interval} minutes"
        except ValueError:
            pass

    # Every N hours: 0 */N * * *
    if minute == "0" and hour.startswith("*/") and day == "*" and month == "*" and weekday == "*":
        try:
            interval = int(hour[2:])
            if interval == 1:
                return "Every hour"
            return f"Every {interval} hours"
        except ValueError:
            pass

    # Every hour at specific minute: M * * * *
    if (
        hour == "*"
        and day == "*"
        and month == "*"
        and weekday == "*"
        and not minute.startswith("*")
    ):
        try:
            min_val = int(minute)
            return f"Every hour at minute {min_val}"
        except ValueError:
            pass

    # Daily at midnight: 0 0 * * *
    if minute == "0" and hour == "0" and day == "*" and month == "*" and weekday == "*":
        return "Daily at midnight"

    # Daily at specific time: M H * * *
    if (
        day == "*"
        and month == "*"
        and weekday == "*"
        and not hour.startswith("*")
        and not minute.startswith("*")
    ):
        try:
            hour_val = int(hour)
            min_val = int(minute)
            # Convert to 12-hour format
            if hour_val == 0:
                time_str = f"12:{min_val:02d} AM"
            elif hour_val < 12:
                time_str = f"{hour_val}:{min_val:02d} AM"
            elif hour_val == 12:
                time_str = f"12:{min_val:02d} PM"
            else:
                time_str = f"{hour_val - 12}:{min_val:02d} PM"
            return f"Daily at {time_str}"
        except ValueError:
            pass

    # Weekly on specific day: M H * * W
    if day == "*" and month == "*" and weekday.isdigit():
        try:
            weekday_names = [
                "Sunday",
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
            ]
            day_num = int(weekday) % 7
            hour_val = int(hour)
            min_val = int(minute)

            if hour_val == 0 and min_val == 0:
                return f"Weekly on {weekday_names[day_num]} at midnight"

            # Convert to 12-hour format
            if hour_val == 0:
                time_str = f"12:{min_val:02d} AM"
            elif hour_val < 12:
                time_str = f"{hour_val}:{min_val:02d} AM"
            elif hour_val == 12:
                time_str = f"12:{min_val:02d} PM"
            else:
                time_str = f"{hour_val - 12}:{min_val:02d} PM"

            return f"Weekly on {weekday_names[day_num]} at {time_str}"
        except ValueError:
            pass

    # List patterns (e.g., 0,30 * * * *)
    if "," in minute and hour == "*" and day == "*" and month == "*" and weekday == "*":
        return f"At minute {minute}"

    # Fallback for complex patterns
    return "Custom schedule"


def sensor_trigger_to_cron(
    trigger: SensorTrigger,
    command: str,
    comment_prefix: str = CRON_COMMENT_PREFIX,
) -> list[CronEntry]:
    """Convert SensorTrigger to cron entries.

    NOTE: Sensor triggers are not yet implemented. They require
    GPIO interrupt handling which is beyond traditional cron scheduling.
    This function returns an empty list with a warning logged.

    Args:
        trigger: SensorTrigger with sensor_type and threshold
        command: Full command string to execute
        comment_prefix: Prefix for cron comment

    Returns:
        Empty list (sensor triggers not implemented via cron)
    """
    logger.warning(
        f"Sensor triggers not yet implemented for cron scheduling. "
        f"Sensor type: {trigger.sensor_type}"
    )
    return []


def cron_trigger_to_cron(
    trigger: CronTrigger,
    command: str,
    comment_prefix: str = CRON_COMMENT_PREFIX,
) -> list[CronEntry]:
    """Convert raw cron expression trigger to cron entries.

    Args:
        trigger: CronTrigger with cron_expression
        command: Full command to execute
        comment_prefix: Prefix for cron job comment

    Returns:
        List with single CronEntry using the raw expression
    """
    if not CronEntry.is_valid_expression(trigger.cron_expression):
        return []

    return [
        CronEntry(
            expression=trigger.cron_expression,
            command=command,
            comment=f"{comment_prefix} Expert Mode",
            enabled=True,
        )
    ]


def routine_to_cron_entries(
    routine: Routine,
    base_time: str,  # "HH:MM" format
    days_of_week: list[int] | None = None,
    comment_prefix: str = CRON_COMMENT_PREFIX,
) -> list[CronEntry]:
    """Convert Routine actions to cron entries.

    Each action in the routine becomes a separate cron entry with:
    - Execution time = base_time + action.offset_minutes
    - Command from cron_security.get_validated_command()

    Args:
        routine: Routine with actions list
        base_time: Base execution time in "HH:MM" format
        days_of_week: Optional ISO weekday restrictions (0=Mon..6=Sun)
        comment_prefix: Prefix for cron comments

    Returns:
        List of CronEntry objects, one per action in the routine
    """
    base_hour, base_minute = map(int, base_time.split(":"))
    base_total_minutes = base_hour * 60 + base_minute

    # Convert days_of_week to cron format
    dow_str = _iso_to_cron_weekday(days_of_week)

    entries = []

    routine_name = routine.get_display_name()
    for action in routine.actions:
        # Calculate execution time
        exec_total_minutes = base_total_minutes + action.offset_minutes

        # Normalize to 24-hour format (handle midnight crossing)
        exec_total_minutes = exec_total_minutes % (24 * 60)
        exec_hour = exec_total_minutes // 60
        exec_minute = exec_total_minutes % 60

        # Get validated command from cron_security
        script_key = get_script_key_for_action(action.action_type, action.action_name)
        if script_key:
            command = get_validated_command(script_key)
        else:
            # Fallback for unknown actions (shouldn't happen with proper validation)
            logger.warning(
                f"Unknown action type '{action.action_type}/{action.action_name}' "
                f"in routine - skipping cron entry"
            )
            command = f"# Unknown action: {action.action_type}/{action.action_name}"

        # Build cron expression
        expression = f"{exec_minute} {exec_hour} * * {dow_str}"

        # Build comment
        comment = (
            f"{comment_prefix} {routine_name}: {action.action_type}/{action.action_name} "
            f"at offset +{action.offset_minutes}min"
        )

        entries.append(CronEntry(expression=expression, command=command, comment=comment))

    return entries


# =============================================================================
# SCHEDULE-TO-CRON CONVERSION
# =============================================================================


def schedule_to_cron(
    schedule: Schedule,
    latitude: float | None = None,
    longitude: float | None = None,
    timezone_name: str = "UTC",
    years_ahead: int = 1,
) -> CronBridgeResult:
    """Convert Schedule to date-specific cron entries.

    Main entry point for the cron bridge. Iterates over each routine and
    generates date-specific cron entries using routine_to_dated_cron().

    All trigger types produce the same output format: date-specific cron entries
    with explicit day and month values. This provides a unified approach for
    solar, moon, interval, fixed-time, and recurring-days triggers.

    Args:
        schedule: Schedule object to convert
        latitude: Observer latitude (required for solar triggers)
        longitude: Observer longitude (required for solar triggers)
        timezone_name: Timezone for calculations
        years_ahead: Number of years to pre-calculate (default 1)

    Returns:
        CronBridgeResult with entries, rtc_waketime, and any errors
    """
    result = CronBridgeResult(
        entries=[],
        rtc_waketime=None,
        schedule_id=schedule.schedule_id,
        errors=[],
    )

    # Check if schedule is enabled
    if not schedule.enabled:
        return result

    # Check for routines
    if not schedule.routines:
        return result

    # Process each routine using unified date-specific cron generation
    for routine in schedule.routines:
        try:
            entries = routine_to_dated_cron(
                routine=routine,
                latitude=latitude,
                longitude=longitude,
                timezone_name=timezone_name,
                years_ahead=years_ahead,
            )
            result.entries.extend(entries)
        except ValueError as e:
            result.errors.append(f"Routine '{routine.get_display_name()}': {str(e)}")

    # Calculate RTC waketime if we have entries
    if result.entries:
        result.rtc_waketime = calculate_next_from_entries(result.entries)

    return result


# =============================================================================
# SCHEDULE PREVIEW
# =============================================================================


def preview_schedule(
    schedule: Schedule,
    count: int = 10,
    from_time: datetime | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    timezone_name: str = "UTC",
) -> list[dict]:
    """Preview upcoming schedule executions (Schema 3.0).

    Iterates over each routine in the schedule, calculates upcoming
    execution times based on the routine's embedded trigger, and aggregates
    all results.

    Args:
        schedule: Schedule object to preview
        count: Maximum number of executions to return (default 10)
        from_time: Calculate executions from this time (defaults to now)
        latitude: Observer latitude (required for solar triggers)
        longitude: Observer longitude (required for solar triggers)
        timezone_name: Timezone for calculations

    Returns:
        List of dicts with:
        - datetime: ISO 8601 string
        - action_type: str (gpio, camera, etc.)
        - action_name: str (attract_on, takephoto, etc.)
        - routine_name: str
        - routine_id: str
    """
    if not schedule.enabled:
        return []

    if from_time is None:
        from_time = datetime.now()

    all_events = []

    # Process each routine
    for routine in schedule.routines:
        routine_events = _get_events_for_routine(
            routine=routine,
            max_events=count * 2,  # Get extra to account for merging
            from_time=from_time,
            latitude=latitude,
            longitude=longitude,
            timezone_name=timezone_name,
        )
        all_events.extend(routine_events)

    # Sort chronologically and trim to count
    all_events.sort(key=lambda e: e["datetime"])
    return all_events[:count]


def _get_events_for_routine(
    routine: Routine,
    max_events: int,
    from_time: datetime,
    latitude: float | None,
    longitude: float | None,
    timezone_name: str,
) -> list[dict]:
    """Generate events for a single routine based on its trigger type."""
    trigger = routine.trigger

    if isinstance(trigger, FixedTimeTrigger):
        return _get_events_fixed_time_routine(routine, max_events, from_time)
    elif isinstance(trigger, IntervalTrigger):
        return _get_events_interval_routine(routine, max_events, from_time)
    elif isinstance(trigger, SolarTrigger):
        return _get_events_solar_routine(
            routine, max_events, from_time, latitude, longitude, timezone_name
        )
    elif isinstance(trigger, MoonPhaseTrigger):
        return _get_events_moon_phase_routine(routine, max_events, from_time)
    elif isinstance(trigger, CronTrigger):
        return _get_events_cron_routine(routine, max_events, from_time)
    elif isinstance(trigger, RecurringDaysTrigger):
        return _get_events_recurring_days_routine(routine, max_events, from_time)
    elif isinstance(trigger, SensorTrigger):
        # Sensor triggers cannot generate preview events
        return []

    return []


def _get_events_fixed_time_routine(
    routine: Routine,
    max_events: int,
    from_time: datetime,
) -> list[dict]:
    """Generate events for fixed time trigger."""
    events = []
    trigger = routine.trigger
    hour, minute = map(int, trigger.time.split(":"))

    current_date = from_time.date()
    days_checked = 0
    max_days = max_events * 7  # Check up to max_events weeks

    while len(events) < max_events and days_checked < max_days:
        # Check day of week restriction
        if trigger.days_of_week is not None and current_date.weekday() not in trigger.days_of_week:
            current_date += timedelta(days=1)
            days_checked += 1
            continue

        # Generate events for this day
        trigger_time = datetime.combine(
            current_date, datetime.min.time().replace(hour=hour, minute=minute)
        )

        if trigger_time > from_time:
            for action in routine.actions:
                event_time = trigger_time + timedelta(minutes=action.offset_minutes)
                events.append(
                    {
                        "datetime": event_time.isoformat(),
                        "action_type": action.action_type,
                        "action_name": action.action_name,
                        "routine_name": routine.name,
                        "routine_id": routine.routine_id,
                    }
                )

        current_date += timedelta(days=1)
        days_checked += 1

    return events


def _get_events_interval_routine(
    routine: Routine,
    max_events: int,
    from_time: datetime,
) -> list[dict]:
    """Generate events for interval trigger."""
    events = []
    trigger = routine.trigger

    # Parse time window
    start_hour, start_min = map(int, trigger.time_window.start_time.split(":"))
    end_hour, end_min = map(int, trigger.time_window.end_time.split(":"))

    current_date = from_time.date()
    days_checked = 0
    max_days = max_events * 2

    while len(events) < max_events and days_checked < max_days:
        # Check day of week restriction
        if trigger.days_of_week is not None and current_date.weekday() not in trigger.days_of_week:
            current_date += timedelta(days=1)
            days_checked += 1
            continue

        # Generate execution times for this day
        exec_times = _generate_execution_times(
            start_hour, start_min, end_hour, end_min, trigger.interval_minutes
        )

        for exec_hour, exec_min in exec_times:
            trigger_time = datetime.combine(
                current_date, datetime.min.time().replace(hour=exec_hour, minute=exec_min)
            )

            if trigger_time > from_time:
                for action in routine.actions:
                    event_time = trigger_time + timedelta(minutes=action.offset_minutes)
                    events.append(
                        {
                            "datetime": event_time.isoformat(),
                            "action_type": action.action_type,
                            "action_name": action.action_name,
                            "routine_name": routine.name,
                            "routine_id": routine.routine_id,
                        }
                    )

        current_date += timedelta(days=1)
        days_checked += 1

    return events


def _get_events_solar_routine(
    routine: Routine,
    max_events: int,
    from_time: datetime,
    latitude: float | None,
    longitude: float | None,
    timezone_name: str,
) -> list[dict]:
    """Generate events for solar trigger."""
    events = []

    if latitude is None or longitude is None:
        return events  # Cannot calculate without coordinates

    trigger = routine.trigger
    current_date = from_time.date()
    days_checked = 0
    max_days = max_events * 2

    while len(events) < max_events and days_checked < max_days:
        # Check day of week restriction
        if trigger.days_of_week is not None and current_date.weekday() not in trigger.days_of_week:
            current_date += timedelta(days=1)
            days_checked += 1
            continue

        # Calculate solar time
        exec_time = get_solar_execution_time(
            trigger, current_date, latitude, longitude, timezone_name
        )

        if exec_time and exec_time > from_time:
            for action in routine.actions:
                event_time = exec_time + timedelta(minutes=action.offset_minutes)
                events.append(
                    {
                        "datetime": event_time.isoformat(),
                        "action_type": action.action_type,
                        "action_name": action.action_name,
                        "routine_name": routine.name,
                        "routine_id": routine.routine_id,
                    }
                )

        current_date += timedelta(days=1)
        days_checked += 1

    return events


def _get_events_moon_phase_routine(
    routine: Routine,
    max_events: int,
    from_time: datetime,
) -> list[dict]:
    """Generate events for moon phase trigger."""
    events = []
    trigger = routine.trigger

    # Get execution time from time window
    if trigger.time_window:
        hour, minute = map(int, trigger.time_window.start_time.split(":"))
    else:
        hour, minute = 0, 0

    current_date = from_time.date()
    days_checked = 0
    max_days = max_events * 30  # Check up to 30x max_events days

    while len(events) < max_events and days_checked < max_days:
        # Check moon phase
        if is_moon_phase_active(trigger, current_date):
            trigger_time = datetime.combine(
                current_date, datetime.min.time().replace(hour=hour, minute=minute)
            )

            if trigger_time > from_time:
                for action in routine.actions:
                    event_time = trigger_time + timedelta(minutes=action.offset_minutes)
                    events.append(
                        {
                            "datetime": event_time.isoformat(),
                            "action_type": action.action_type,
                            "action_name": action.action_name,
                            "routine_name": routine.name,
                            "routine_id": routine.routine_id,
                        }
                    )

        current_date += timedelta(days=1)
        days_checked += 1

    return events


def _get_events_cron_routine(
    routine: Routine,
    max_events: int,
    from_time: datetime,
) -> list[dict]:
    """Generate events for cron trigger."""
    events = []
    trigger = routine.trigger

    try:
        cron_iter = croniter(trigger.cron_expression, from_time)
        events_added = 0

        while events_added < max_events:
            next_time = cron_iter.get_next(datetime)
            for action in routine.actions:
                event_time = next_time + timedelta(minutes=action.offset_minutes)
                events.append(
                    {
                        "datetime": event_time.isoformat(),
                        "action_type": action.action_type,
                        "action_name": action.action_name,
                        "routine_name": routine.name,
                        "routine_id": routine.routine_id,
                    }
                )
            events_added += 1
    except (ValueError, KeyError):
        # Invalid cron expression
        pass

    return events


def _get_events_recurring_days_routine(
    routine: Routine,
    max_events: int,
    from_time: datetime,
) -> list[dict]:
    """Generate events for recurring days trigger.

    RecurringDaysTrigger specifies "every N days" from a start date.
    Events are generated for dates matching the N-day pattern.
    """
    events = []
    trigger = routine.trigger

    if not trigger.time or trigger.every_n_days < 1:
        return events

    hour, minute = map(int, trigger.time.split(":"))

    # Determine start date for the pattern
    if trigger.start_date:
        pattern_start = date.fromisoformat(trigger.start_date)
    else:
        pattern_start = from_time.date()

    current_date = from_time.date()
    days_checked = 0
    max_days = max_events * trigger.every_n_days * 2  # Check enough days

    while len(events) < max_events and days_checked < max_days:
        # Check if current day matches the N-day pattern from start
        days_since_start = (current_date - pattern_start).days
        if days_since_start >= 0 and days_since_start % trigger.every_n_days == 0:
            trigger_time = datetime.combine(
                current_date, datetime.min.time().replace(hour=hour, minute=minute)
            )

            if trigger_time > from_time:
                for action in routine.actions:
                    event_time = trigger_time + timedelta(minutes=action.offset_minutes)
                    events.append(
                        {
                            "datetime": event_time.isoformat(),
                            "action_type": action.action_type,
                            "action_name": action.action_name,
                            "routine_name": routine.name,
                            "routine_id": routine.routine_id,
                        }
                    )

        current_date += timedelta(days=1)
        days_checked += 1

    return events


# =============================================================================
# SYSTEM CRON MANAGEMENT
# =============================================================================


def apply_to_system(
    entries: list[CronEntry],
    schedule_id: str,
    set_rtc: bool = True,
    user: str | None = None,
) -> bool:
    """Apply cron entries to system crontab.

    1. Remove existing Mothbox jobs (preserves system jobs)
    2. Add new entries
    3. Optionally set RTC wakealarm

    Args:
        entries: List of CronEntry objects to add
        schedule_id: ID of the schedule being applied
        set_rtc: Whether to set RTC wakealarm (default True)
        user: Username for crontab (None for current user)

    Returns:
        True if successful, False on error
    """
    try:
        # Open user crontab
        cron = CronTab(user=user) if user else CronTab(user=True)

        # Remove existing Mothbox jobs
        jobs_to_remove = []
        for job in cron:
            if is_mothbox_command(job.command):
                jobs_to_remove.append(job)

        for job in jobs_to_remove:
            cron.remove(job)

        logger.info(f"Removed {len(jobs_to_remove)} existing Mothbox cron jobs")

        # Add new entries
        added_count = 0
        for entry in entries:
            if entry.enabled:
                job = cron.new(command=entry.command, comment=entry.comment)
                job.setall(entry.expression)
                added_count += 1

        # Write changes
        cron.write()
        logger.info(f"Applied {added_count} cron entries for schedule {schedule_id}")

        # Set RTC wakealarm AFTER cron entries are written.
        # Ordering rationale: If process crashes between writes:
        #   - Current order (cron→RTC): Jobs exist but no wake. Recoverable on next activation.
        #   - Reversed (RTC→cron): Wake set but no jobs. Wastes power waking for nothing.
        # For battery-powered field devices, the current order is safer.
        if set_rtc and entries:
            next_wake = calculate_next_from_entries(entries)
            if next_wake:
                # Setting overwrites any existing alarm atomically
                set_rtc_wakealarm(next_wake)
            else:
                # Only clear if no new alarm to set
                clear_rtc_wakealarm()

        return True

    except (OSError, ValueError) as e:
        logger.error(f"Failed to apply cron entries: {e}")
        return False


def remove_from_system(
    clear_rtc: bool = True,
    user: str | None = None,
) -> bool:
    """Remove all Mothbox cron jobs from system.

    Uses is_mothbox_command() from cron_security to identify jobs safely.
    Preserves non-Mothbox system jobs.

    Args:
        clear_rtc: Whether to clear RTC wakealarm (default True)
        user: Username for crontab (None for current user)

    Returns:
        True if successful, False on error
    """
    try:
        # Open user crontab
        cron = CronTab(user=user) if user else CronTab(user=True)

        # Find and remove Mothbox jobs
        jobs_to_remove = []
        for job in cron:
            if is_mothbox_command(job.command):
                jobs_to_remove.append(job)

        for job in jobs_to_remove:
            cron.remove(job)

        # Write changes
        cron.write()
        logger.info(f"Removed {len(jobs_to_remove)} Mothbox cron jobs")

        # Clear RTC wakealarm
        if clear_rtc:
            clear_rtc_wakealarm()

        return True

    except (OSError, ValueError) as e:
        logger.error(f"Failed to remove cron jobs: {e}")
        return False

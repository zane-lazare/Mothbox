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

from crontab import CronTab

from webui.backend.lib.cron_security import (
    get_script_key_for_action,
    get_validated_command,
    is_mothbox_command,
)
from webui.backend.lib.moon_phase import get_moon_phase, is_within_moon_phase
from webui.backend.lib.schedule_schema import (
    EventPattern,
    FixedTimeTrigger,
    IntervalTrigger,
    MoonPhaseTrigger,
    Schedule,
    SensorTrigger,
    SolarTrigger,
)
from webui.backend.lib.solar_time import parse_time_spec

logger = logging.getLogger(__name__)

# Constants
CRON_COMMENT_PREFIX: Final[str] = "Mothbox:"
RTC_WAKEALARM_PATH: Final[str] = "/sys/class/rtc/rtc0/wakealarm"

# Pre-compiled regex patterns for cron field validation (performance optimization)
_CRON_FIELD_PATTERNS: Final[tuple[re.Pattern, ...]] = (
    re.compile(r'^(\*|([0-5]?\d)(,([0-5]?\d))*|([0-5]?\d)-([0-5]?\d)|\*/([1-5]?\d))$'),  # minute
    re.compile(r'^(\*|([01]?\d|2[0-3])(,([01]?\d|2[0-3]))*|([01]?\d|2[0-3])-([01]?\d|2[0-3])|\*/([01]?\d|2[0-3]))$'),  # hour
    re.compile(r'^(\*|([1-9]|[12]\d|3[01])(,([1-9]|[12]\d|3[01]))*|([1-9]|[12]\d|3[01])-([1-9]|[12]\d|3[01])|\*/([1-9]|[12]\d|3[01]))$'),  # day
    re.compile(r'^(\*|([1-9]|1[0-2])(,([1-9]|1[0-2]))*|([1-9]|1[0-2])-([1-9]|1[0-2])|\*/([1-9]|1[0-2]))$'),  # month
    re.compile(r'^(\*|[0-7](,[0-7])*|[0-7]-[0-7]|\*/[0-7])$'),  # weekday
)


@dataclass
class CronEntry:
    """Represents a single cron job entry.

    Attributes:
        expression: Cron expression (e.g., "0 21 * * *")
        command: Full command to execute
        comment: Optional comment for the job
        enabled: Whether the entry is enabled
    """
    expression: str  # e.g., "0 21 * * *"
    command: str     # e.g., "/usr/bin/python3 /opt/mothbox/TakePhoto.py"
    comment: str = ""
    enabled: bool = True

    def to_cron_line(self) -> str:
        """Convert entry to crontab line format.

        Returns:
            String in crontab format with optional comment line.
            Disabled entries are commented out with #.
        """
        lines = []

        # Add comment if present
        if self.comment:
            lines.append(f"# {self.comment}")

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
            if '-' in field_value and not field_value.startswith('*/'):
                parts = field_value.split('-')
                if len(parts) == 2:
                    try:
                        start, end = int(parts[0]), int(parts[1])
                        if start >= end:
                            return False
                    except ValueError:
                        return False

            # Handle step expressions (e.g., */5)
            if field_value.startswith('*/'):
                try:
                    step = int(field_value[2:])
                    if step <= 0:
                        return False
                except ValueError:
                    return False
                continue

            # Handle comma-separated lists (e.g., 0,30)
            if ',' in field_value:
                values = field_value.split(',')
                for val in values:
                    if not val.strip():
                        return False
                continue

            # Validate against pre-compiled pattern
            if not pattern.match(field_value):
                return False

        # Additional validation: check numeric ranges
        try:
            minute, hour, day, month, weekday = fields

            # Check minute range (0-59)
            if minute != '*' and not minute.startswith('*/') and ',' not in minute and '-' not in minute and int(minute) > 59:
                return False

            # Check hour range (0-23)
            if hour != '*' and not hour.startswith('*/') and ',' not in hour and '-' not in hour and int(hour) > 23:
                return False

            # Check day range (1-31)
            if day != '*' and not day.startswith('*/') and ',' not in day and '-' not in day:
                day_val = int(day)
                if day_val < 1 or day_val > 31:
                    return False

            # Check month range (1-12)
            if month != '*' and not month.startswith('*/') and ',' not in month and '-' not in month:
                month_val = int(month)
                if month_val < 1 or month_val > 12:
                    return False

            # Check weekday range (0-7)
            if weekday != '*' and not weekday.startswith('*/') and ',' not in weekday and '-' not in weekday and int(weekday) > 7:
                return False

        except (ValueError, IndexError):
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
        start_hour, start_minute,
        end_hour, end_minute,
        trigger.interval_minutes
    )

    # Convert days of week
    dow_str = _iso_to_cron_weekday(trigger.days_of_week)

    # Create cron entries
    entries = []
    for hour, minute in exec_times:
        expression = f"{minute} {hour} * * {dow_str}"
        comment = f"{comment_prefix} Interval {trigger.interval_minutes}min at {hour:02d}:{minute:02d}"
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
        return parse_time_spec(
            time_spec,
            target_date,
            latitude,
            longitude,
            timezone_name
        )
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
        raise ValueError(f"days_ahead must be between 1 and 365, got {days_ahead}")

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
        raise ValueError(f"days_ahead must be between 1 and 365, got {days_ahead}")

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
            f"{comment_prefix} Moon phase ({phase_info['phase']}) "
            f"on {target_date.isoformat()}"
        )

        entries.append(CronEntry(expression=expression, command=command, comment=comment))

    return entries


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


def pattern_to_cron_entries(
    pattern: EventPattern,
    base_time: str,  # "HH:MM" format
    days_of_week: list[int] | None = None,
    comment_prefix: str = CRON_COMMENT_PREFIX,
) -> list[CronEntry]:
    """Convert EventPattern actions to cron entries.

    Each action in the pattern becomes a separate cron entry with:
    - Execution time = base_time + action.offset_minutes
    - Command from cron_security.get_validated_command()

    Args:
        pattern: EventPattern with actions list
        base_time: Base execution time in "HH:MM" format
        days_of_week: Optional ISO weekday restrictions (0=Mon..6=Sun)
        comment_prefix: Prefix for cron comments

    Returns:
        List of CronEntry objects, one per action in the pattern
    """
    base_hour, base_minute = map(int, base_time.split(":"))
    base_total_minutes = base_hour * 60 + base_minute

    # Convert days_of_week to cron format
    dow_str = _iso_to_cron_weekday(days_of_week)

    entries = []

    for action in pattern.actions:
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
            command = f"# Unknown action: {action.action_type}/{action.action_name}"

        # Build cron expression
        expression = f"{exec_minute} {exec_hour} * * {dow_str}"

        # Build comment
        comment = (
            f"{comment_prefix} {pattern.name}: {action.action_type}/{action.action_name} "
            f"at offset +{action.offset_minutes}min"
        )

        entries.append(CronEntry(expression=expression, command=command, comment=comment))

    return entries


# =============================================================================
# SCHEDULE-TO-CRON CONVERSION
# =============================================================================


def _convert_fixed_time_schedule(schedule: Schedule, days_ahead: int = 7) -> CronBridgeResult:
    """Convert fixed-time schedule to cron entries."""
    trigger = schedule.fixed_time_trigger
    entries = []

    for pattern in schedule.event_patterns:
        pattern_entries = pattern_to_cron_entries(
            pattern,
            base_time=trigger.time,
            days_of_week=trigger.days_of_week,
        )
        entries.extend(pattern_entries)

    return CronBridgeResult(
        entries=entries,
        rtc_waketime=calculate_next_from_entries(entries) if entries else None,
        schedule_id=schedule.schedule_id,
    )


def _convert_interval_schedule(schedule: Schedule) -> CronBridgeResult:
    """Convert interval schedule to cron entries."""
    trigger = schedule.interval_trigger
    entries = []

    # Generate base execution times from interval trigger
    base_entries = interval_trigger_to_cron(trigger, command="placeholder")

    # For each base time, generate pattern actions
    for base_entry in base_entries:
        # Extract hour:minute from expression (format: "minute hour * * dow")
        parts = base_entry.expression.split()
        base_time = f"{int(parts[1]):02d}:{int(parts[0]):02d}"  # "HH:MM"

        for pattern in schedule.event_patterns:
            pattern_entries = pattern_to_cron_entries(
                pattern,
                base_time=base_time,
                days_of_week=trigger.days_of_week,
            )
            entries.extend(pattern_entries)

    return CronBridgeResult(
        entries=entries,
        rtc_waketime=calculate_next_from_entries(entries) if entries else None,
        schedule_id=schedule.schedule_id,
    )


def _convert_solar_schedule(
    schedule: Schedule,
    latitude: float,
    longitude: float,
    timezone_name: str,
    days_ahead: int,
) -> CronBridgeResult:
    """Convert solar schedule to cron entries."""
    entries = []

    # Generate base entries from solar trigger
    for pattern in schedule.event_patterns:
        # For each action in pattern, generate solar-timed entries
        for action in pattern.actions:
            script_key = get_script_key_for_action(action.action_type, action.action_name)
            command = get_validated_command(script_key) if script_key else f"# Unknown: {action.action_type}/{action.action_name}"

            # Create modified trigger with action offset
            modified_trigger = SolarTrigger(
                solar_event=schedule.solar_trigger.solar_event,
                offset_minutes=schedule.solar_trigger.offset_minutes + action.offset_minutes,
                days_of_week=schedule.solar_trigger.days_of_week,
            )

            solar_entries = solar_trigger_to_cron(
                modified_trigger,
                command=command,
                latitude=latitude,
                longitude=longitude,
                timezone_name=timezone_name,
                days_ahead=days_ahead,
            )
            entries.extend(solar_entries)

    return CronBridgeResult(
        entries=entries,
        rtc_waketime=calculate_next_from_entries(entries) if entries else None,
        schedule_id=schedule.schedule_id,
    )


def _convert_moon_phase_schedule(schedule: Schedule, days_ahead: int) -> CronBridgeResult:
    """Convert moon phase schedule to cron entries."""
    entries = []

    # Get base execution time from time_window
    trigger = schedule.moon_phase_trigger
    if trigger.time_window:
        base_hour, base_minute = map(int, trigger.time_window.start_time.split(":"))
    else:
        base_hour, base_minute = 0, 0

    # Get dates matching moon phases
    from_date = date.today()
    matching_dates = []

    for day_offset in range(days_ahead):
        target_date = from_date + timedelta(days=day_offset)
        if is_moon_phase_active(trigger, target_date):
            matching_dates.append(target_date)

    # For each matching date, generate entries for all pattern actions
    for target_date in matching_dates:
        for pattern in schedule.event_patterns:
            for action in pattern.actions:
                # Calculate execution time with action offset
                exec_total_minutes = base_hour * 60 + base_minute + action.offset_minutes
                exec_total_minutes = exec_total_minutes % (24 * 60)
                exec_hour = exec_total_minutes // 60
                exec_minute = exec_total_minutes % 60

                # Get validated command
                script_key = get_script_key_for_action(action.action_type, action.action_name)
                command = get_validated_command(script_key) if script_key else f"# Unknown: {action.action_type}/{action.action_name}"

                # Build cron expression with specific day and month
                expression = f"{exec_minute} {exec_hour} {target_date.day} {target_date.month} *"

                # Get current moon phase for comment
                phase_info = get_moon_phase(target_date)
                comment = (
                    f"{CRON_COMMENT_PREFIX} {pattern.name}: {action.action_type}/{action.action_name} "
                    f"Moon phase ({phase_info['phase']}) on {target_date.isoformat()}"
                )

                entries.append(CronEntry(expression=expression, command=command, comment=comment))

    return CronBridgeResult(
        entries=entries,
        rtc_waketime=calculate_next_from_entries(entries) if entries else None,
        schedule_id=schedule.schedule_id,
    )


def schedule_to_cron(
    schedule: Schedule,
    latitude: float | None = None,
    longitude: float | None = None,
    timezone_name: str = "UTC",
    days_ahead: int = 7,
) -> CronBridgeResult:
    """Convert Schedule to cron entries.

    Main entry point for the cron bridge. Routes to appropriate
    trigger converter based on schedule.trigger_type.

    Args:
        schedule: Schedule object to convert
        latitude: Observer latitude (required for solar triggers)
        longitude: Observer longitude (required for solar triggers)
        timezone_name: Timezone for calculations
        days_ahead: Number of days to pre-calculate (for solar/moon triggers)

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

    # Check for event patterns
    if not schedule.event_patterns:
        return result

    # Route to appropriate trigger converter
    if schedule.trigger_type == "fixed_time" and schedule.fixed_time_trigger:
        result = _convert_fixed_time_schedule(schedule, days_ahead)

    elif schedule.trigger_type == "interval" and schedule.interval_trigger:
        result = _convert_interval_schedule(schedule)

    elif schedule.trigger_type == "solar" and schedule.solar_trigger:
        if latitude is None or longitude is None:
            result.errors.append("Solar triggers require latitude and longitude")
        else:
            result = _convert_solar_schedule(schedule, latitude, longitude, timezone_name, days_ahead)

    elif schedule.trigger_type == "moon_phase" and schedule.moon_phase_trigger:
        # Use 30 days for moon phase schedules to capture at least one full moon cycle
        moon_days_ahead = 30 if days_ahead == 7 else days_ahead
        result = _convert_moon_phase_schedule(schedule, moon_days_ahead)

    elif schedule.trigger_type == "sensor" and schedule.sensor_trigger:
        # Sensor triggers are stubbed
        result.errors.append("Sensor triggers not yet implemented for cron scheduling")

    else:
        result.errors.append(f"Unsupported or invalid trigger type: {schedule.trigger_type}")

    # Calculate RTC waketime if we have entries
    if result.entries:
        result.rtc_waketime = calculate_next_from_entries(result.entries)

    return result


# =============================================================================
# EVENT PREVIEW
# =============================================================================


def get_next_events(
    schedule: Schedule,
    count: int = 10,
    from_time: datetime | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    timezone_name: str = "UTC",
) -> list[dict]:
    """Preview next N scheduled events without modifying system.

    Calculates upcoming event execution times based on the schedule's
    trigger type and event patterns.

    Args:
        schedule: Schedule object to preview
        count: Maximum number of events to return (default 10)
        from_time: Calculate events from this time (defaults to now)
        latitude: Observer latitude (required for solar triggers)
        longitude: Observer longitude (required for solar triggers)
        timezone_name: Timezone for calculations

    Returns:
        List of event dicts with:
        - datetime: ISO 8601 string
        - action_type: str (gpio, camera, etc.)
        - action_name: str (attract_on, takephoto, etc.)
        - pattern_name: str
        - pattern_id: str
    """
    if not schedule.enabled:
        return []

    if from_time is None:
        from_time = datetime.now()

    events = []

    # Get date constraints
    start_date = date.fromisoformat(schedule.start_date) if schedule.start_date else None
    end_date = date.fromisoformat(schedule.end_date) if schedule.end_date else None

    # Calculate trigger times based on type
    if schedule.trigger_type == "fixed_time" and schedule.fixed_time_trigger:
        events = _get_events_fixed_time(
            schedule, count * 2, from_time, start_date, end_date
        )
    elif schedule.trigger_type == "interval" and schedule.interval_trigger:
        events = _get_events_interval(
            schedule, count * 2, from_time, start_date, end_date
        )
    elif schedule.trigger_type == "solar" and schedule.solar_trigger:
        events = _get_events_solar(
            schedule, count * 2, from_time, start_date, end_date,
            latitude, longitude, timezone_name
        )
    elif schedule.trigger_type == "moon_phase" and schedule.moon_phase_trigger:
        events = _get_events_moon_phase(
            schedule, count * 2, from_time, start_date, end_date
        )

    # Sort chronologically and trim to count
    events.sort(key=lambda e: e["datetime"])
    return events[:count]


def _get_events_fixed_time(
    schedule: Schedule,
    max_events: int,
    from_time: datetime,
    start_date: date | None,
    end_date: date | None,
) -> list[dict]:
    """Generate events for fixed time trigger."""
    events = []
    trigger = schedule.fixed_time_trigger
    hour, minute = map(int, trigger.time.split(":"))

    current_date = from_time.date()
    days_checked = 0
    max_days = max_events * 7  # Check up to max_events weeks

    while len(events) < max_events and days_checked < max_days:
        # Check date constraints
        if start_date and current_date < start_date:
            current_date += timedelta(days=1)
            days_checked += 1
            continue
        if end_date and current_date > end_date:
            break

        # Check day of week restriction
        if trigger.days_of_week is not None and current_date.weekday() not in trigger.days_of_week:
            current_date += timedelta(days=1)
            days_checked += 1
            continue

        # Generate events for this day
        trigger_time = datetime.combine(current_date, datetime.min.time().replace(hour=hour, minute=minute))

        if trigger_time > from_time:
            for pattern in schedule.event_patterns:
                for action in pattern.actions:
                    event_time = trigger_time + timedelta(minutes=action.offset_minutes)
                    events.append({
                        "datetime": event_time.isoformat(),
                        "action_type": action.action_type,
                        "action_name": action.action_name,
                        "pattern_name": pattern.name,
                        "pattern_id": pattern.pattern_id,
                    })

        current_date += timedelta(days=1)
        days_checked += 1

    return events


def _get_events_interval(
    schedule: Schedule,
    max_events: int,
    from_time: datetime,
    start_date: date | None,
    end_date: date | None,
) -> list[dict]:
    """Generate events for interval trigger."""
    events = []
    trigger = schedule.interval_trigger

    # Parse time window
    start_hour, start_min = map(int, trigger.time_window.start_time.split(":"))
    end_hour, end_min = map(int, trigger.time_window.end_time.split(":"))

    current_date = from_time.date()
    days_checked = 0
    max_days = max_events * 2

    while len(events) < max_events and days_checked < max_days:
        # Check date constraints
        if start_date and current_date < start_date:
            current_date += timedelta(days=1)
            days_checked += 1
            continue
        if end_date and current_date > end_date:
            break

        # Check day of week restriction
        if trigger.days_of_week is not None and current_date.weekday() not in trigger.days_of_week:
            current_date += timedelta(days=1)
            days_checked += 1
            continue

        # Generate execution times for this day
        exec_times = _generate_execution_times(start_hour, start_min, end_hour, end_min, trigger.interval_minutes)

        for exec_hour, exec_min in exec_times:
            trigger_time = datetime.combine(current_date, datetime.min.time().replace(hour=exec_hour, minute=exec_min))

            if trigger_time > from_time:
                for pattern in schedule.event_patterns:
                    for action in pattern.actions:
                        event_time = trigger_time + timedelta(minutes=action.offset_minutes)
                        events.append({
                            "datetime": event_time.isoformat(),
                            "action_type": action.action_type,
                            "action_name": action.action_name,
                            "pattern_name": pattern.name,
                            "pattern_id": pattern.pattern_id,
                        })

        current_date += timedelta(days=1)
        days_checked += 1

    return events


def _get_events_solar(
    schedule: Schedule,
    max_events: int,
    from_time: datetime,
    start_date: date | None,
    end_date: date | None,
    latitude: float | None,
    longitude: float | None,
    timezone_name: str,
) -> list[dict]:
    """Generate events for solar trigger."""
    events = []

    if latitude is None or longitude is None:
        return events  # Cannot calculate without coordinates

    trigger = schedule.solar_trigger
    current_date = from_time.date()
    days_checked = 0
    max_days = max_events * 2

    while len(events) < max_events and days_checked < max_days:
        # Check date constraints
        if start_date and current_date < start_date:
            current_date += timedelta(days=1)
            days_checked += 1
            continue
        if end_date and current_date > end_date:
            break

        # Check day of week restriction
        if trigger.days_of_week is not None and current_date.weekday() not in trigger.days_of_week:
            current_date += timedelta(days=1)
            days_checked += 1
            continue

        # Calculate solar time
        exec_time = get_solar_execution_time(trigger, current_date, latitude, longitude, timezone_name)

        if exec_time and exec_time > from_time:
            for pattern in schedule.event_patterns:
                for action in pattern.actions:
                    event_time = exec_time + timedelta(minutes=action.offset_minutes)
                    events.append({
                        "datetime": event_time.isoformat(),
                        "action_type": action.action_type,
                        "action_name": action.action_name,
                        "pattern_name": pattern.name,
                        "pattern_id": pattern.pattern_id,
                    })

        current_date += timedelta(days=1)
        days_checked += 1

    return events


def _get_events_moon_phase(
    schedule: Schedule,
    max_events: int,
    from_time: datetime,
    start_date: date | None,
    end_date: date | None,
) -> list[dict]:
    """Generate events for moon phase trigger."""
    events = []
    trigger = schedule.moon_phase_trigger

    # Get execution time from time window
    if trigger.time_window:
        hour, minute = map(int, trigger.time_window.start_time.split(":"))
    else:
        hour, minute = 0, 0

    current_date = from_time.date()
    days_checked = 0
    max_days = max_events * 30  # Check up to 30x max_events days

    while len(events) < max_events and days_checked < max_days:
        # Check date constraints
        if start_date and current_date < start_date:
            current_date += timedelta(days=1)
            days_checked += 1
            continue
        if end_date and current_date > end_date:
            break

        # Check moon phase
        if is_moon_phase_active(trigger, current_date):
            trigger_time = datetime.combine(current_date, datetime.min.time().replace(hour=hour, minute=minute))

            if trigger_time > from_time:
                for pattern in schedule.event_patterns:
                    for action in pattern.actions:
                        event_time = trigger_time + timedelta(minutes=action.offset_minutes)
                        events.append({
                            "datetime": event_time.isoformat(),
                            "action_type": action.action_type,
                            "action_name": action.action_name,
                            "pattern_name": pattern.name,
                            "pattern_id": pattern.pattern_id,
                        })

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

        # Set RTC wakealarm
        if set_rtc and entries:
            next_wake = calculate_next_from_entries(entries)
            if next_wake:
                set_rtc_wakealarm(next_wake)

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

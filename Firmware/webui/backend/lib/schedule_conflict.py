"""
Schedule conflict detection library.

Provides conflict detection for Mothbox scheduler patterns, detecting:
- Time overlaps between pattern executions
- Resource contention (camera, GPS single-instance resources)
- GPIO state conflicts (on vs off for same GPIO resource)

This module is used by SchedulerService to validate schedules before
activation and provide preview mode for conflict analysis.

Issue #213 - Scheduler Phase 3: Conflict Detection
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from typing import Final

from webui.backend.lib.schedule_schema import (
    EventPattern,
    PatternAction,
    Schedule,
)

# ============================================================================
# Constants
# ============================================================================

# Single-instance resources - only one can be active at a time
SINGLE_RESOURCES: Final[set[str]] = {"camera", "gps"}

# GPIO resources - can conflict if states differ (on vs off)
GPIO_RESOURCES: Final[set[str]] = {"attract", "flash"}

# Conflict types
CONFLICT_TIME_OVERLAP: Final[str] = "time_overlap"
CONFLICT_RESOURCE_CONTENTION: Final[str] = "resource_contention"
CONFLICT_GPIO_STATE: Final[str] = "gpio_state_conflict"

# Severity levels
SEVERITY_ERROR: Final[str] = "error"
SEVERITY_WARNING: Final[str] = "warning"

# Logger
logger = logging.getLogger(__name__)


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class ResourceUsage:
    """
    Describes resource usage by a single action.

    Attributes:
        resource_type: Category ("camera", "gps", "attract", "flash", "service")
        resource_name: Specific action name (e.g., "takephoto", "attract_on")
        start_time: When resource is acquired
        end_time: When resource is released
        pattern_id: Source pattern ID
        action_index: Index within pattern's actions list
    """

    resource_type: str
    resource_name: str
    start_time: datetime
    end_time: datetime
    pattern_id: str
    action_index: int

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "resource_type": self.resource_type,
            "resource_name": self.resource_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "pattern_id": self.pattern_id,
            "action_index": self.action_index,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ResourceUsage":
        """Deserialize from dictionary."""
        return cls(
            resource_type=data["resource_type"],
            resource_name=data["resource_name"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]),
            pattern_id=data["pattern_id"],
            action_index=data["action_index"],
        )


@dataclass
class PatternExecution:
    """
    Represents a single execution of an EventPattern at a specific time.

    Attributes:
        pattern_id: The EventPattern ID
        pattern_name: Human-readable pattern name
        start_time: Absolute start time of pattern execution
        end_time: When pattern completes (start + duration)
        resource_usages: List of resources used during execution
    """

    pattern_id: str
    pattern_name: str
    start_time: datetime
    end_time: datetime
    resource_usages: list[ResourceUsage] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "pattern_id": self.pattern_id,
            "pattern_name": self.pattern_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "resource_usages": [r.to_dict() for r in self.resource_usages],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PatternExecution":
        """Deserialize from dictionary."""
        return cls(
            pattern_id=data["pattern_id"],
            pattern_name=data["pattern_name"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]),
            resource_usages=[
                ResourceUsage.from_dict(r) for r in data.get("resource_usages", [])
            ],
        )


@dataclass
class Conflict:
    """
    Describes a detected conflict between pattern executions.

    Attributes:
        conflict_type: "time_overlap", "resource_contention", "gpio_state_conflict"
        event1_id: First pattern execution ID
        event1_name: First pattern name
        event2_id: Second pattern execution ID
        event2_name: Second pattern name
        start_time: Conflict start (overlap beginning)
        end_time: Conflict end (overlap ending)
        resource: Conflicting resource name (if resource contention)
        message: Human-readable conflict description
        suggested_resolution: Suggested fix for user
        severity: "error" (blocking) or "warning" (advisory)
    """

    conflict_type: str
    event1_id: str
    event1_name: str
    event2_id: str
    event2_name: str
    start_time: datetime
    end_time: datetime
    resource: str = ""
    message: str = ""
    suggested_resolution: str = ""
    severity: str = SEVERITY_ERROR

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "conflict_type": self.conflict_type,
            "event1_id": self.event1_id,
            "event1_name": self.event1_name,
            "event2_id": self.event2_id,
            "event2_name": self.event2_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "resource": self.resource,
            "message": self.message,
            "suggested_resolution": self.suggested_resolution,
            "severity": self.severity,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Conflict":
        """Deserialize from dictionary."""
        return cls(
            conflict_type=data["conflict_type"],
            event1_id=data["event1_id"],
            event1_name=data["event1_name"],
            event2_id=data["event2_id"],
            event2_name=data["event2_name"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]),
            resource=data.get("resource", ""),
            message=data.get("message", ""),
            suggested_resolution=data.get("suggested_resolution", ""),
            severity=data.get("severity", SEVERITY_ERROR),
        )


@dataclass
class ConflictReport:
    """
    Complete conflict detection report for a schedule.

    Attributes:
        schedule_id: The analyzed schedule
        schedule_name: Schedule name
        preview_start: Analysis start date
        preview_end: Analysis end date
        total_executions: Number of pattern executions in preview period
        conflicts: List of detected conflicts
        has_blocking_conflicts: True if any severity="error" conflicts
        analyzed_at: Timestamp of analysis
    """

    schedule_id: str
    schedule_name: str
    preview_start: datetime
    preview_end: datetime
    total_executions: int
    conflicts: list[Conflict]
    has_blocking_conflicts: bool
    analyzed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "schedule_id": self.schedule_id,
            "schedule_name": self.schedule_name,
            "preview_start": self.preview_start.isoformat(),
            "preview_end": self.preview_end.isoformat(),
            "total_executions": self.total_executions,
            "conflicts": [c.to_dict() for c in self.conflicts],
            "has_blocking_conflicts": self.has_blocking_conflicts,
            "analyzed_at": self.analyzed_at.isoformat(),
        }


# ============================================================================
# Time Overlap Detection
# ============================================================================

def check_time_overlap(
    exec1: PatternExecution,
    exec2: PatternExecution,
) -> tuple[bool, datetime | None, datetime | None]:
    """
    Check if two pattern executions overlap in time.

    Two intervals [a1, a2] and [b1, b2] overlap if a1 < b2 AND b1 < a2.
    Adjacent patterns (a2 == b1) are NOT considered overlapping.

    Args:
        exec1: First pattern execution
        exec2: Second pattern execution

    Returns:
        Tuple of (overlaps: bool, overlap_start: datetime | None, overlap_end: datetime | None)
    """
    # Handle zero-duration patterns (start == end)
    # A point in time doesn't have duration, so can't truly overlap
    if exec1.start_time == exec1.end_time or exec2.start_time == exec2.end_time:
        return False, None, None

    # Check for overlap: a1 < b2 AND b1 < a2
    overlaps = exec1.start_time < exec2.end_time and exec2.start_time < exec1.end_time

    if not overlaps:
        return False, None, None

    # Calculate overlap period
    overlap_start = max(exec1.start_time, exec2.start_time)
    overlap_end = min(exec1.end_time, exec2.end_time)

    return True, overlap_start, overlap_end


# ============================================================================
# Resource Type Detection
# ============================================================================

def get_resource_type(action: PatternAction) -> str:
    """
    Determine resource type from action.

    Maps action types and names to resource categories for conflict detection.

    Args:
        action: PatternAction to analyze

    Returns:
        Resource type: "camera", "gps", "attract", "flash", or "service"
    """
    if action.action_type == "camera":
        return "camera"
    elif action.action_type == "gps_sync":
        return "gps"
    elif action.action_type == "gpio":
        # Extract base resource from action_name
        if action.action_name.startswith("attract"):
            return "attract"
        elif action.action_name.startswith("flash"):
            return "flash"
        # Default for unknown GPIO actions
        return "gpio"
    return "service"


# ============================================================================
# Resource Contention Detection
# ============================================================================

def check_resource_contention(
    usage1: ResourceUsage,
    usage2: ResourceUsage,
) -> tuple[bool, str]:
    """
    Check if two resource usages conflict.

    Conflicts occur when:
    - Single-instance resources (camera, gps) are used simultaneously
    - GPIO resources have conflicting states (attract_on vs attract_off)

    Args:
        usage1: First resource usage
        usage2: Second resource usage

    Returns:
        Tuple of (conflicts: bool, conflict_type: str)
        conflict_type is "resource_contention" or "gpio_state_conflict" or ""
    """
    # Check time overlap first
    # Handle instant actions (start == end) specially
    if usage1.start_time == usage1.end_time and usage2.start_time == usage2.end_time:
        # Both are instant - only conflict if at exact same time
        times_overlap = usage1.start_time == usage2.start_time
    elif usage1.start_time == usage1.end_time:
        # usage1 is instant - check if it falls within usage2 (inclusive end)
        times_overlap = usage2.start_time <= usage1.start_time <= usage2.end_time
    elif usage2.start_time == usage2.end_time:
        # usage2 is instant - check if it falls within usage1 (inclusive end)
        times_overlap = usage1.start_time <= usage2.start_time <= usage1.end_time
    else:
        # Both have duration - standard overlap check
        times_overlap = usage1.start_time < usage2.end_time and usage2.start_time < usage1.end_time

    if not times_overlap:
        return False, ""

    # Service resources never conflict
    if usage1.resource_type == "service" or usage2.resource_type == "service":
        return False, ""

    # Check if same resource type
    if usage1.resource_type != usage2.resource_type:
        return False, ""

    # Single-instance resource conflict
    if usage1.resource_type in SINGLE_RESOURCES:
        return True, CONFLICT_RESOURCE_CONTENTION

    # GPIO state conflict (on vs off for same resource)
    if usage1.resource_type in GPIO_RESOURCES:
        state1 = "on" if usage1.resource_name.endswith("_on") else "off"
        state2 = "on" if usage2.resource_name.endswith("_on") else "off"
        if state1 != state2:
            return True, CONFLICT_GPIO_STATE
        # Same state is not a conflict
        return False, ""

    return False, ""


# ============================================================================
# Pattern Execution Generation
# ============================================================================

def _parse_time_string(time_str: str) -> time:
    """Parse HH:MM time string to time object."""
    parts = time_str.split(":")
    return time(int(parts[0]), int(parts[1]))


def _is_schedule_active_on_date(schedule: Schedule, target_date: date) -> bool:
    """Check if schedule is active on a given date."""
    # Check date range constraints
    if schedule.start_date:
        start = date.fromisoformat(schedule.start_date)
        if target_date < start:
            return False

    if schedule.end_date:
        end = date.fromisoformat(schedule.end_date)
        if target_date > end:
            return False

    # Check day of week constraints based on trigger type
    weekday = target_date.weekday()  # 0=Monday, 6=Sunday

    if schedule.trigger_type == "interval" and schedule.interval_trigger:
        days = schedule.interval_trigger.days_of_week
        if days is not None and weekday not in days:
            return False

    elif schedule.trigger_type == "solar" and schedule.solar_trigger:
        days = schedule.solar_trigger.days_of_week
        if days is not None and weekday not in days:
            return False

    elif schedule.trigger_type == "fixed_time" and schedule.fixed_time_trigger:
        days = schedule.fixed_time_trigger.days_of_week
        if days is not None and weekday not in days:
            return False

    return True


def _get_trigger_times_for_day(
    schedule: Schedule,
    target_date: date,
    latitude: float,
    longitude: float,
    timezone_name: str,
) -> list[datetime]:
    """
    Get all trigger times for a schedule on a specific day.

    Supports: interval, solar, moon_phase, fixed_time, sensor triggers.
    """
    trigger_times = []

    if schedule.trigger_type == "interval" and schedule.interval_trigger:
        trigger = schedule.interval_trigger

        # Parse time window
        try:
            # Try to parse as HH:MM first
            window_start_time = _parse_time_string(trigger.time_window.start_time)
            window_start = datetime.combine(target_date, window_start_time)
        except (ValueError, AttributeError):
            # If it's a solar event, use solar_time module
            try:
                from webui.backend.lib.solar_time import parse_time_spec
                window_start = parse_time_spec(
                    trigger.time_window.start_time,
                    target_date,
                    latitude,
                    longitude,
                    timezone_name,
                )
            except (ImportError, ValueError):
                window_start = datetime.combine(target_date, time(0, 0))

        # Apply start offset
        window_start += timedelta(minutes=trigger.time_window.start_offset_minutes)

        try:
            window_end_time = _parse_time_string(trigger.time_window.end_time)
            window_end = datetime.combine(target_date, window_end_time)
        except (ValueError, AttributeError):
            try:
                from webui.backend.lib.solar_time import parse_time_spec
                window_end = parse_time_spec(
                    trigger.time_window.end_time,
                    target_date,
                    latitude,
                    longitude,
                    timezone_name,
                )
            except (ImportError, ValueError):
                window_end = datetime.combine(target_date, time(23, 59))

        # Apply end offset
        window_end += timedelta(minutes=trigger.time_window.end_offset_minutes)

        # Handle overnight windows (end < start)
        if window_end <= window_start:
            window_end += timedelta(days=1)

        # Generate interval times within window
        current = window_start
        while current < window_end:
            trigger_times.append(current)
            current += timedelta(minutes=trigger.interval_minutes)

    elif schedule.trigger_type == "solar" and schedule.solar_trigger:
        trigger = schedule.solar_trigger
        try:
            from webui.backend.lib.solar_time import parse_time_spec
            trigger_time = parse_time_spec(
                trigger.solar_event,
                target_date,
                latitude,
                longitude,
                timezone_name,
            )
            trigger_time += timedelta(minutes=trigger.offset_minutes)
            trigger_times.append(trigger_time)
        except (ImportError, ValueError) as e:
            logger.debug(
                f"Solar trigger calculation failed for {schedule.schedule_id}: {e}"
            )

    elif schedule.trigger_type == "moon_phase" and schedule.moon_phase_trigger:
        trigger = schedule.moon_phase_trigger
        try:
            from webui.backend.lib.moon_phase import is_within_moon_phase
            # Check if any target phase is active on this date
            for phase in trigger.phases:
                if is_within_moon_phase(target_date, phase, trigger.offset_days):
                    # If time_window provided, use it; otherwise trigger at noon
                    if trigger.time_window:
                        try:
                            window_start_time = _parse_time_string(
                                trigger.time_window.start_time
                            )
                            trigger_times.append(
                                datetime.combine(target_date, window_start_time)
                            )
                        except ValueError:
                            trigger_times.append(
                                datetime.combine(target_date, time(12, 0))
                            )
                    else:
                        trigger_times.append(
                            datetime.combine(target_date, time(12, 0))
                        )
                    break  # Only need one trigger per day
        except ImportError as e:
            logger.debug(
                f"Moon phase module unavailable for {schedule.schedule_id}: {e}"
            )

    elif schedule.trigger_type == "fixed_time" and schedule.fixed_time_trigger:
        trigger = schedule.fixed_time_trigger
        try:
            trigger_time = _parse_time_string(trigger.time)
            trigger_times.append(datetime.combine(target_date, trigger_time))
        except ValueError as e:
            logger.debug(
                f"Fixed time parse failed for {schedule.schedule_id}: {e}"
            )

    elif schedule.trigger_type == "sensor" and schedule.sensor_trigger:
        trigger = schedule.sensor_trigger
        # Sensor triggers are unpredictable; assume one trigger at window start
        if trigger.time_window:
            try:
                window_start_time = _parse_time_string(trigger.time_window.start_time)
                trigger_times.append(datetime.combine(target_date, window_start_time))
            except ValueError as e:
                logger.debug(
                    f"Sensor trigger parse failed for {schedule.schedule_id}: {e}"
                )

    return trigger_times


def _create_resource_usage(
    action: PatternAction,
    pattern_id: str,
    action_index: int,
    execution_start: datetime,
) -> ResourceUsage:
    """Create ResourceUsage from a PatternAction."""
    resource_type = get_resource_type(action)

    # Calculate actual times
    action_start = execution_start + timedelta(minutes=action.offset_minutes)

    # Most actions are instantaneous; camera takes ~30 seconds
    if action.action_type == "camera":
        action_end = action_start + timedelta(seconds=30)
    else:
        action_end = action_start  # Instantaneous

    return ResourceUsage(
        resource_type=resource_type,
        resource_name=action.action_name,
        start_time=action_start,
        end_time=action_end,
        pattern_id=pattern_id,
        action_index=action_index,
    )


def _create_pattern_execution(
    pattern: EventPattern,
    trigger_time: datetime,
) -> PatternExecution:
    """Create PatternExecution from EventPattern at trigger time."""
    # Calculate execution duration from max action offset
    duration_minutes = pattern.duration_minutes if pattern.actions else 0
    end_time = trigger_time + timedelta(minutes=duration_minutes)

    # Create resource usages for all actions
    resource_usages = [
        _create_resource_usage(action, pattern.pattern_id, i, trigger_time)
        for i, action in enumerate(pattern.actions)
    ]

    return PatternExecution(
        pattern_id=pattern.pattern_id,
        pattern_name=pattern.name,
        start_time=trigger_time,
        end_time=end_time,
        resource_usages=resource_usages,
    )


def generate_pattern_executions(
    schedule: Schedule,
    start_date: date,
    end_date: date,
    latitude: float,
    longitude: float,
    timezone_name: str = "UTC",
) -> list[PatternExecution]:
    """
    Generate all pattern executions for a schedule within a date range.

    Uses solar_time.py and moon_phase.py to resolve trigger times.

    Args:
        schedule: Schedule to analyze
        start_date: Start of preview period
        end_date: End of preview period
        latitude: Location latitude for solar calculations
        longitude: Location longitude for solar calculations
        timezone_name: Timezone for time resolution

    Returns:
        List of PatternExecution objects sorted by start_time
    """
    executions = []

    # Iterate through each day in range
    current = start_date
    while current <= end_date:
        # Check if schedule is active on this day
        if not _is_schedule_active_on_date(schedule, current):
            current += timedelta(days=1)
            continue

        # Generate trigger times based on trigger_type
        trigger_times = _get_trigger_times_for_day(
            schedule, current, latitude, longitude, timezone_name
        )

        # Create execution for each trigger time and each pattern
        for trigger_time in trigger_times:
            for pattern in schedule.event_patterns:
                execution = _create_pattern_execution(pattern, trigger_time)
                executions.append(execution)

        current += timedelta(days=1)

    sorted_executions = sorted(executions, key=lambda e: e.start_time)
    days_analyzed = (end_date - start_date).days + 1
    logger.debug(
        f"Generated {len(sorted_executions)} executions for schedule "
        f"{schedule.schedule_id} over {days_analyzed} days"
    )
    return sorted_executions


# ============================================================================
# Main Conflict Detection
# ============================================================================

def _generate_conflict_message(
    conflict_type: str,
    usage1: ResourceUsage,
    usage2: ResourceUsage,
) -> str:
    """Generate human-readable conflict message."""
    if conflict_type == CONFLICT_RESOURCE_CONTENTION:
        return (
            f"{usage1.resource_type.title()} resource conflict: "
            f"both patterns use {usage1.resource_name} at the same time"
        )
    elif conflict_type == CONFLICT_GPIO_STATE:
        return (
            f"GPIO state conflict: {usage1.resource_name} and "
            f"{usage2.resource_name} cannot be active simultaneously"
        )
    return "Pattern execution conflict detected"


def _generate_resolution(
    conflict_type: str,
    usage1: ResourceUsage,
    usage2: ResourceUsage,
) -> str:
    """Generate suggested resolution for conflict."""
    if conflict_type == CONFLICT_RESOURCE_CONTENTION:
        return (
            f"Adjust action timing so {usage1.resource_type} is not used "
            f"simultaneously, or increase interval between pattern triggers"
        )
    elif conflict_type == CONFLICT_GPIO_STATE:
        return (
            f"Ensure {usage1.resource_type} state changes don't overlap: "
            f"add delay between {usage1.resource_name} and {usage2.resource_name}"
        )
    return "Adjust pattern timing or increase trigger interval"


def detect_conflicts(
    schedule: Schedule,
    preview_days: int = 7,
    latitude: float = 0.0,
    longitude: float = 0.0,
    timezone_name: str = "UTC",
) -> ConflictReport:
    """
    Detect all conflicts in a schedule over a preview period.

    Analyzes time overlaps and resource contention for all pattern
    executions within the preview window.

    Args:
        schedule: Schedule to analyze
        preview_days: Number of days to preview (default 7)
        latitude: Location latitude for solar calculations
        longitude: Location longitude for solar calculations
        timezone_name: Timezone for time resolution

    Returns:
        ConflictReport with all detected conflicts
    """
    logger.debug(f"Analyzing schedule {schedule.schedule_id} for conflicts...")

    start_date = date.today()
    end_date = start_date + timedelta(days=preview_days - 1)

    # Generate all pattern executions
    executions = generate_pattern_executions(
        schedule, start_date, end_date, latitude, longitude, timezone_name
    )

    conflicts: list[Conflict] = []

    # Check all pairs of executions
    for i, exec1 in enumerate(executions):
        for exec2 in executions[i + 1:]:
            # Check time overlap
            overlaps, overlap_start, overlap_end = check_time_overlap(exec1, exec2)

            if overlaps and overlap_start and overlap_end:
                # Create time overlap conflict (warning severity)
                time_conflict = Conflict(
                    conflict_type=CONFLICT_TIME_OVERLAP,
                    event1_id=exec1.pattern_id,
                    event1_name=exec1.pattern_name,
                    event2_id=exec2.pattern_id,
                    event2_name=exec2.pattern_name,
                    start_time=overlap_start,
                    end_time=overlap_end,
                    message=(
                        f"Patterns '{exec1.pattern_name}' and "
                        f"'{exec2.pattern_name}' overlap in time"
                    ),
                    suggested_resolution=(
                        "Adjust pattern offsets or increase interval between triggers"
                    ),
                    severity=SEVERITY_WARNING,
                )
                conflicts.append(time_conflict)

                # Check resource contention within overlapping patterns
                for usage1 in exec1.resource_usages:
                    for usage2 in exec2.resource_usages:
                        contends, conflict_type = check_resource_contention(
                            usage1, usage2
                        )
                        if contends:
                            resource_conflict = Conflict(
                                conflict_type=conflict_type,
                                event1_id=exec1.pattern_id,
                                event1_name=exec1.pattern_name,
                                event2_id=exec2.pattern_id,
                                event2_name=exec2.pattern_name,
                                start_time=max(usage1.start_time, usage2.start_time),
                                end_time=min(usage1.end_time, usage2.end_time),
                                resource=usage1.resource_type,
                                message=_generate_conflict_message(
                                    conflict_type, usage1, usage2
                                ),
                                suggested_resolution=_generate_resolution(
                                    conflict_type, usage1, usage2
                                ),
                                severity=SEVERITY_ERROR,
                            )
                            conflicts.append(resource_conflict)

    has_blocking = any(c.severity == SEVERITY_ERROR for c in conflicts)
    blocking_count = sum(1 for c in conflicts if c.severity == SEVERITY_ERROR)

    logger.debug(
        f"Found {len(conflicts)} conflicts ({blocking_count} blocking) "
        f"in {len(executions)} executions for schedule {schedule.schedule_id}"
    )

    return ConflictReport(
        schedule_id=schedule.schedule_id,
        schedule_name=schedule.name,
        preview_start=datetime.combine(start_date, time(0, 0), tzinfo=UTC),
        preview_end=datetime.combine(end_date, time(23, 59, 59), tzinfo=UTC),
        total_executions=len(executions),
        conflicts=conflicts,
        has_blocking_conflicts=has_blocking,
    )


# ============================================================================
# Validation Function
# ============================================================================

def validate_schedule_conflicts(
    schedule: Schedule,
    preview_days: int = 7,
    latitude: float = 0.0,
    longitude: float = 0.0,
    timezone_name: str = "UTC",
) -> tuple[bool, str | None]:
    """
    Validate schedule for conflicts before activation.

    Following the existing validation pattern (tuple[bool, str | None]).

    Args:
        schedule: Schedule to validate
        preview_days: Days to analyze
        latitude: Location latitude
        longitude: Location longitude
        timezone_name: Timezone name

    Returns:
        (True, None) if no blocking conflicts
        (False, error_message) if blocking conflicts exist
    """
    report = detect_conflicts(
        schedule, preview_days, latitude, longitude, timezone_name
    )

    if report.has_blocking_conflicts:
        blocking = [c for c in report.conflicts if c.severity == SEVERITY_ERROR]
        # Limit to first 3 conflicts in message
        messages = [c.message for c in blocking[:3]]
        error = (
            f"Schedule has {len(blocking)} blocking conflict(s): "
            + "; ".join(messages)
        )
        logger.debug(f"Schedule {schedule.schedule_id} failed validation: {error}")
        return False, error

    return True, None

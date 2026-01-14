"""
Schedule conflict detection library.

Provides conflict detection for Mothbox scheduler routines, detecting:
- Time overlaps between routine executions
- Resource contention (camera, GPS single-instance resources)
- GPIO state conflicts (on vs off for same GPIO resource)

This module is used by SchedulerService to validate schedules before
activation and provide preview mode for conflict analysis.

Issue #213 - Scheduler Phase 3: Conflict Detection
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from typing import Final

from webui.backend.lib.schedule_schema import (
    Action,
    FixedTimeTrigger,
    IntervalTrigger,
    MoonPhaseTrigger,
    Routine,
    Schedule,
    SensorTrigger,
    SolarTrigger,
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
        routine_id: Source routine ID
        action_index: Index within routine's actions list
    """

    resource_type: str
    resource_name: str
    start_time: datetime
    end_time: datetime
    routine_id: str
    action_index: int

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "resource_type": self.resource_type,
            "resource_name": self.resource_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "routine_id": self.routine_id,
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
            routine_id=data["routine_id"],
            action_index=data["action_index"],
        )


@dataclass
class RoutineExecution:
    """
    Represents a single execution of a Routine at a specific time.

    Attributes:
        routine_id: The Routine ID
        routine_name: Human-readable routine name
        start_time: Absolute start time of routine execution
        end_time: When routine completes (start + duration)
        resource_usages: List of resources used during execution
    """

    routine_id: str
    routine_name: str
    start_time: datetime
    end_time: datetime
    resource_usages: list[ResourceUsage] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "routine_id": self.routine_id,
            "routine_name": self.routine_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "resource_usages": [r.to_dict() for r in self.resource_usages],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RoutineExecution":
        """Deserialize from dictionary."""
        return cls(
            routine_id=data["routine_id"],
            routine_name=data["routine_name"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]),
            resource_usages=[ResourceUsage.from_dict(r) for r in data.get("resource_usages", [])],
        )


@dataclass
class Conflict:
    """
    Describes a detected conflict between routine executions.

    Attributes:
        conflict_type: "time_overlap", "resource_contention", "gpio_state_conflict"
        event1_id: First routine execution ID
        event1_name: First routine name
        event2_id: Second routine execution ID
        event2_name: Second routine name
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
class TimeCollision:
    """
    Represents two or more routines executing at the exact same time.

    Time collisions are blocking errors that prevent schedule activation
    because hardware resources (especially camera) cannot be shared.

    Attributes:
        time: The exact datetime when collision occurs
        routine_ids: List of routine IDs that collide
        message: Human-readable description of the collision
    """

    time: datetime
    routine_ids: list[str]
    message: str

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "type": "time_collision",
            "time": self.time.isoformat(),
            "routine_ids": self.routine_ids,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TimeCollision":
        """Deserialize from dictionary."""
        return cls(
            time=datetime.fromisoformat(data["time"]),
            routine_ids=data["routine_ids"],
            message=data["message"],
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
        total_executions: Number of routine executions in preview period
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
    exec1: RoutineExecution,
    exec2: RoutineExecution,
) -> tuple[bool, datetime | None, datetime | None]:
    """
    Check if two routine executions overlap in time.

    Two intervals [a1, a2] and [b1, b2] overlap if a1 < b2 AND b1 < a2.
    Adjacent routines (a2 == b1) are NOT considered overlapping.

    Args:
        exec1: First routine execution
        exec2: Second routine execution

    Returns:
        Tuple of (overlaps: bool, overlap_start: datetime | None, overlap_end: datetime | None)

    Note:
        Zero-duration routines (start == end) return False because a point in
        time has no duration to overlap. However, check_resource_contention()
        uses different logic - instant actions CAN conflict with resources they
        touch, even at boundaries. This is intentional: routine overlap is about
        scheduling (do routines run simultaneously?), while resource contention
        is about hardware access (can two actions use the same resource?).
    """
    # Handle zero-duration routines (start == end)
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


def get_resource_type(action: Action) -> str:
    """
    Determine resource type from action.

    Maps action types and names to resource categories for conflict detection.

    Args:
        action: Action to analyze

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

    # Service resources (logging, metrics, notifications) are non-exclusive by design.
    # They can run concurrently without hardware contention. If an action requires
    # exclusive access to a resource, use a different resource type (camera, gps, gpio).
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
    """Check if schedule is active on a given date (Schema 3.0).

    A schedule is active if at least one of its routines is active on the date.
    """
    if not schedule.routines:
        return False

    weekday = target_date.weekday()  # 0=Monday, 6=Sunday

    # Check if any routine is active on this date
    for routine in schedule.routines:
        if _is_routine_active_on_date(routine, target_date, weekday):
            return True

    return False


def _is_routine_active_on_date(routine: Routine, target_date: date, weekday: int) -> bool:
    """Check if a routine is active on a given date based on its trigger."""
    trigger = routine.trigger
    if trigger is None:
        return False

    # Check day of week constraints based on trigger type
    if isinstance(trigger, (IntervalTrigger, SolarTrigger, FixedTimeTrigger)):
        days = trigger.days_of_week
        if days is not None and weekday not in days:
            return False

    elif isinstance(trigger, SensorTrigger):
        # Sensor triggers could have day constraints too
        if (
            hasattr(trigger, "days_of_week")
            and trigger.days_of_week is not None
            and weekday not in trigger.days_of_week
        ):
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
    Get all trigger times for a schedule on a specific day (Schema 3.0).

    Iterates over all routines and collects trigger times from each.
    """
    trigger_times = []

    for routine in schedule.routines:
        routine_times = _get_routine_trigger_times_for_day(
            routine, target_date, latitude, longitude, timezone_name
        )
        trigger_times.extend(routine_times)

    return trigger_times


def _get_routine_trigger_times_for_day(
    routine: Routine,
    target_date: date,
    latitude: float,
    longitude: float,
    timezone_name: str,
) -> list[datetime]:
    """Get trigger times for a single routine on a specific day."""
    trigger_times = []
    trigger = routine.trigger

    if trigger is None:
        return trigger_times

    if isinstance(trigger, IntervalTrigger):
        # Parse time window (defaults to all day if not specified)
        if trigger.time_window is None:
            window_start = datetime.combine(target_date, time(0, 0))
            window_end = datetime.combine(target_date, time(23, 59))
        else:
            try:
                window_start_time = _parse_time_string(trigger.time_window.start_time)
                window_start = datetime.combine(target_date, window_start_time)
            except (ValueError, AttributeError):
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

            window_end += timedelta(minutes=trigger.time_window.end_offset_minutes)

        if window_end <= window_start:
            window_end += timedelta(days=1)

        current = window_start
        while current < window_end:
            trigger_times.append(current)
            current += timedelta(minutes=trigger.interval_minutes)

    elif isinstance(trigger, SolarTrigger):
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
            logger.warning(f"Solar trigger calculation failed for routine {routine.name}: {e}")

    elif isinstance(trigger, MoonPhaseTrigger):
        try:
            from webui.backend.lib.moon_phase import is_within_moon_phase

            for phase in trigger.phases:
                if is_within_moon_phase(target_date, phase, trigger.offset_days):
                    if trigger.time_window:
                        try:
                            window_start_time = _parse_time_string(trigger.time_window.start_time)
                            trigger_times.append(datetime.combine(target_date, window_start_time))
                        except ValueError:
                            trigger_times.append(datetime.combine(target_date, time(12, 0)))
                    else:
                        trigger_times.append(datetime.combine(target_date, time(12, 0)))
                    break
        except ImportError as e:
            logger.warning(f"Moon phase module unavailable for routine {routine.name}: {e}")

    elif isinstance(trigger, FixedTimeTrigger):
        try:
            trigger_time = _parse_time_string(trigger.time)
            trigger_times.append(datetime.combine(target_date, trigger_time))
        except ValueError as e:
            logger.debug(f"Fixed time parse failed for routine {routine.name}: {e}")

    elif isinstance(trigger, SensorTrigger):
        if trigger.time_window:
            try:
                window_start_time = _parse_time_string(trigger.time_window.start_time)
                trigger_times.append(datetime.combine(target_date, window_start_time))
            except ValueError as e:
                logger.debug(f"Sensor trigger parse failed for routine {routine.name}: {e}")

    return trigger_times


def _create_resource_usage(
    action: Action,
    routine_id: str,
    action_index: int,
    execution_start: datetime,
) -> ResourceUsage:
    """Create ResourceUsage from an Action."""
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
        routine_id=routine_id,
        action_index=action_index,
    )


def _create_routine_execution(
    routine: Routine,
    trigger_time: datetime,
) -> RoutineExecution:
    """Create RoutineExecution from Routine at trigger time (Schema 3.0)."""
    # Calculate execution duration from max action offset
    duration_minutes = routine.duration_minutes if routine.actions else 0
    end_time = trigger_time + timedelta(minutes=duration_minutes)

    # Create resource usages for all actions
    resource_usages = [
        _create_resource_usage(action, routine.routine_id, i, trigger_time)
        for i, action in enumerate(routine.actions)
    ]

    return RoutineExecution(
        routine_id=routine.routine_id,
        routine_name=routine.name or routine.routine_id,
        start_time=trigger_time,
        end_time=end_time,
        resource_usages=resource_usages,
    )


def generate_routine_executions(
    schedule: Schedule,
    start_date: date,
    end_date: date,
    latitude: float,
    longitude: float,
    timezone_name: str = "UTC",
) -> list[RoutineExecution]:
    """
    Generate all routine executions for a schedule within a date range (Schema 3.0).

    Each routine has its own trigger, so we generate executions per-routine.

    Args:
        schedule: Schedule to analyze
        start_date: Start of preview period
        end_date: End of preview period
        latitude: Location latitude for solar calculations
        longitude: Location longitude for solar calculations
        timezone_name: Timezone for time resolution

    Returns:
        List of RoutineExecution objects sorted by start_time
    """
    executions = []

    # Process each routine independently
    for routine in schedule.routines:
        # Iterate through each day in range
        current = start_date
        weekday = current.weekday()

        while current <= end_date:
            # Check if this routine is active on this day
            if not _is_routine_active_on_date(routine, current, weekday):
                current += timedelta(days=1)
                weekday = current.weekday()
                continue

            # Generate trigger times for this routine on this day
            routine_trigger_times = _get_routine_trigger_times_for_day(
                routine, current, latitude, longitude, timezone_name
            )

            # Create execution for each trigger time
            for trigger_time in routine_trigger_times:
                execution = _create_routine_execution(routine, trigger_time)
                executions.append(execution)

            current += timedelta(days=1)
            weekday = current.weekday()

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
            f"both routines use {usage1.resource_name} at the same time"
        )
    elif conflict_type == CONFLICT_GPIO_STATE:
        return (
            f"GPIO state conflict: {usage1.resource_name} and "
            f"{usage2.resource_name} cannot be active simultaneously"
        )
    return "Routine execution conflict detected"


def _generate_resolution(
    conflict_type: str,
    usage1: ResourceUsage,
    usage2: ResourceUsage,
) -> str:
    """Generate suggested resolution for conflict."""
    if conflict_type == CONFLICT_RESOURCE_CONTENTION:
        return (
            f"Adjust action timing so {usage1.resource_type} is not used "
            f"simultaneously, or increase interval between routine triggers"
        )
    elif conflict_type == CONFLICT_GPIO_STATE:
        return (
            f"Ensure {usage1.resource_type} state changes don't overlap: "
            f"add delay between {usage1.resource_name} and {usage2.resource_name}"
        )
    return "Adjust routine timing or increase trigger interval"


def detect_conflicts(
    schedule: Schedule,
    preview_days: int = 7,
    latitude: float = 0.0,
    longitude: float = 0.0,
    timezone_name: str = "UTC",
) -> ConflictReport:
    """
    Detect all conflicts in a schedule over a preview period.

    Analyzes time overlaps and resource contention for all routine
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

    # Generate all routine executions
    executions = generate_routine_executions(
        schedule, start_date, end_date, latitude, longitude, timezone_name
    )

    conflicts: list[Conflict] = []

    # Check all pairs of executions
    for i, exec1 in enumerate(executions):
        for exec2 in executions[i + 1 :]:
            # Check time overlap
            overlaps, overlap_start, overlap_end = check_time_overlap(exec1, exec2)

            if overlaps and overlap_start and overlap_end:
                # Create time overlap conflict (warning severity)
                time_conflict = Conflict(
                    conflict_type=CONFLICT_TIME_OVERLAP,
                    event1_id=exec1.routine_id,
                    event1_name=exec1.routine_name,
                    event2_id=exec2.routine_id,
                    event2_name=exec2.routine_name,
                    start_time=overlap_start,
                    end_time=overlap_end,
                    message=(
                        f"Routines '{exec1.routine_name}' and '{exec2.routine_name}' "
                        f"overlap from {overlap_start.strftime('%H:%M:%S')} to "
                        f"{overlap_end.strftime('%H:%M:%S')}"
                    ),
                    suggested_resolution=(
                        "Adjust routine offsets or increase interval between triggers"
                    ),
                    severity=SEVERITY_WARNING,
                )
                conflicts.append(time_conflict)

                # Check resource contention within overlapping routines
                for usage1 in exec1.resource_usages:
                    for usage2 in exec2.resource_usages:
                        contends, conflict_type = check_resource_contention(usage1, usage2)
                        if contends:
                            resource_conflict = Conflict(
                                conflict_type=conflict_type,
                                event1_id=exec1.routine_id,
                                event1_name=exec1.routine_name,
                                event2_id=exec2.routine_id,
                                event2_name=exec2.routine_name,
                                start_time=max(usage1.start_time, usage2.start_time),
                                end_time=min(usage1.end_time, usage2.end_time),
                                resource=usage1.resource_type,
                                message=_generate_conflict_message(conflict_type, usage1, usage2),
                                suggested_resolution=_generate_resolution(
                                    conflict_type, usage1, usage2
                                ),
                                severity=SEVERITY_ERROR,
                            )
                            conflicts.append(resource_conflict)

    # Check instant action collisions (zero-duration executions at same time)
    # These are skipped by check_time_overlap() but still cause resource conflicts
    time_groups: dict[datetime, list[RoutineExecution]] = defaultdict(list)
    for execution in executions:
        if execution.start_time == execution.end_time:  # Instant action
            time_groups[execution.start_time].append(execution)

    # Check resource contention within each time group
    for collision_time, colliding_execs in time_groups.items():
        if len(colliding_execs) < 2:
            continue

        # Check all pairs for resource contention
        for i, exec1 in enumerate(colliding_execs):
            for exec2 in colliding_execs[i + 1 :]:
                for usage1 in exec1.resource_usages:
                    for usage2 in exec2.resource_usages:
                        contends, conflict_type = check_resource_contention(usage1, usage2)
                        if contends:
                            instant_conflict = Conflict(
                                conflict_type=conflict_type,
                                event1_id=exec1.routine_id,
                                event1_name=exec1.routine_name,
                                event2_id=exec2.routine_id,
                                event2_name=exec2.routine_name,
                                start_time=collision_time,
                                end_time=collision_time,
                                resource=usage1.resource_type,
                                message=(
                                    f"'{exec1.routine_name}' and '{exec2.routine_name}' "
                                    f"both use {usage1.resource_type} at "
                                    f"{collision_time.strftime('%H:%M:%S')}"
                                ),
                                suggested_resolution=(
                                    "Stagger trigger times or combine into single routine"
                                ),
                                severity=SEVERITY_ERROR,
                            )
                            conflicts.append(instant_conflict)

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
    report = detect_conflicts(schedule, preview_days, latitude, longitude, timezone_name)

    if report.has_blocking_conflicts:
        blocking = [c for c in report.conflicts if c.severity == SEVERITY_ERROR]
        # Limit to first 3 conflicts in message
        messages = [c.message for c in blocking[:3]]
        error = f"Schedule has {len(blocking)} blocking conflict(s): " + "; ".join(messages)
        logger.debug(f"Schedule {schedule.schedule_id} failed validation: {error}")
        return False, error

    return True, None


# ============================================================================
# Time Collision Detection
# ============================================================================


def detect_time_collisions(
    schedule: Schedule,
    preview_days: int = 7,
    latitude: float | None = None,
    longitude: float | None = None,
    timezone_name: str = "UTC",
) -> list[TimeCollision]:
    """
    Detect when two or more routines execute at exactly the same time.

    Uses generate_routine_executions() to get all routine execution times
    over the preview period, then identifies exact time matches.

    Time collisions are blocking errors because hardware resources
    (especially camera) cannot be shared simultaneously.

    Args:
        schedule: Schedule to analyze
        preview_days: Number of days to analyze (default 7)
        latitude: Location latitude for solar calculations
        longitude: Location longitude for solar calculations
        timezone_name: Timezone for time resolution

    Returns:
        List of TimeCollision objects. Empty list if no collisions.
    """
    if not schedule.routines:
        return []

    start_date = date.today()
    end_date = start_date + timedelta(days=preview_days - 1)

    # Use latitude/longitude defaults if None
    lat = latitude if latitude is not None else 0.0
    lon = longitude if longitude is not None else 0.0

    # Generate all routine executions
    executions = generate_routine_executions(
        schedule, start_date, end_date, lat, lon, timezone_name
    )

    if len(executions) < 2:
        return []

    # Group executions by start_time
    by_time: dict[datetime, list[RoutineExecution]] = {}
    for execution in executions:
        by_time.setdefault(execution.start_time, []).append(execution)

    # Find collisions (times with 2+ executions)
    collisions = []
    for exec_time, execs in by_time.items():
        if len(execs) >= 2:
            routine_ids = [e.routine_id for e in execs]
            routine_names = [e.routine_name or e.routine_id for e in execs]

            # Generate human-readable message
            if len(routine_names) == 2:
                message = f"'{routine_names[0]}' and '{routine_names[1]}' execute at identical time"
            else:
                names_str = ", ".join(f"'{n}'" for n in routine_names)
                message = f"{len(routine_names)} routines execute at identical time: {names_str}"

            collisions.append(
                TimeCollision(
                    time=exec_time,
                    routine_ids=routine_ids,
                    message=message,
                )
            )

    if collisions:
        logger.debug(
            f"Found {len(collisions)} time collision(s) in schedule {schedule.schedule_id}"
        )

    return collisions


# ============================================================================
# GPIO State Warning Detection
# ============================================================================


@dataclass
class GPIOStateWarning:
    """
    Warning for unbalanced GPIO states (non-blocking).

    Represents a warning when GPIO resources (attract, flash) are
    left in an inconsistent state, such as turning on without
    a corresponding off action within the same routine.

    These warnings are advisory and do not block schedule activation.

    Attributes:
        resource_type: GPIO resource type ("attract" or "flash")
        routine_id: Source routine ID
        routine_name: Human-readable routine name
        issue: Description of the state imbalance
        suggested_fix: Recommended action to resolve
    """

    resource_type: str
    routine_id: str
    routine_name: str
    issue: str
    suggested_fix: str

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "type": "gpio_state_warning",
            "resource_type": self.resource_type,
            "routine_id": self.routine_id,
            "routine_name": self.routine_name,
            "issue": self.issue,
            "suggested_fix": self.suggested_fix,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GPIOStateWarning":
        """Deserialize from dictionary."""
        return cls(
            resource_type=data["resource_type"],
            routine_id=data["routine_id"],
            routine_name=data["routine_name"],
            issue=data["issue"],
            suggested_fix=data["suggested_fix"],
        )


def detect_gpio_conflicts(schedule: Schedule) -> list[GPIOStateWarning]:
    """
    Detect unbalanced GPIO states in a schedule.

    Analyzes routines for GPIO actions that may leave hardware
    in an inconsistent state (e.g., attract_on without attract_off).

    These are non-blocking warnings that don't prevent schedule
    activation but alert users to potential issues.

    Args:
        schedule: Schedule to analyze

    Returns:
        List of GPIOStateWarning objects. Empty if no issues detected.
    """
    warnings: list[GPIOStateWarning] = []

    for routine in schedule.routines:
        # Track GPIO state changes within routine
        gpio_states: dict[str, list[str]] = {"attract": [], "flash": []}

        for action in routine.actions:
            if action.action_type == "gpio":
                if action.action_name.startswith("attract"):
                    state = "on" if action.action_name.endswith("_on") else "off"
                    gpio_states["attract"].append(state)
                elif action.action_name.startswith("flash"):
                    state = "on" if action.action_name.endswith("_on") else "off"
                    gpio_states["flash"].append(state)

        # Check for imbalanced states
        for resource, states in gpio_states.items():
            if states:
                on_count = states.count("on")
                off_count = states.count("off")

                if on_count > off_count:
                    warnings.append(
                        GPIOStateWarning(
                            resource_type=resource,
                            routine_id=routine.routine_id,
                            routine_name=routine.name or routine.routine_id,
                            issue=(
                                f"{resource.title()} turned on {on_count} time(s) "
                                f"but off {off_count} time(s)"
                            ),
                            suggested_fix=f"Add {resource}_off action at end of routine",
                        )
                    )
                elif off_count > on_count:
                    warnings.append(
                        GPIOStateWarning(
                            resource_type=resource,
                            routine_id=routine.routine_id,
                            routine_name=routine.name or routine.routine_id,
                            issue=(
                                f"{resource.title()} turned off {off_count} time(s) "
                                f"but on {on_count} time(s)"
                            ),
                            suggested_fix=(
                                f"Verify {resource}_on action exists before {resource}_off"
                            ),
                        )
                    )

    if warnings:
        logger.debug(
            f"Found {len(warnings)} GPIO state warning(s) in schedule {schedule.schedule_id}"
        )

    return warnings

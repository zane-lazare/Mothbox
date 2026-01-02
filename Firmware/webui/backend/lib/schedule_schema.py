"""
Schedule Schema for Mothbox Visual Scheduler.

Defines the core data structures for the scheduler system using a routine-based model:
- Action: Single action with type, name, offset, and parameters
- Routine: Action sequence with embedded trigger configuration
- Schedule: Contains routines (each with its own trigger)

Single-file storage: Each schedule is a self-contained JSON file with routines embedded
inline, making schedules portable and easy to export/import between Mothbox units.

Schema Version: 3.0
- Action: action_type, action_name, offset_minutes, parameters, description
- Routine: routine_id, name, trigger, actions, pre_condition (optional)
- TimeWindow: start_time, end_time, offsets (supports "sunset", "01:00")
- Trigger types: IntervalTrigger, SolarTrigger, MoonPhaseTrigger, FixedTimeTrigger,
                 SensorTrigger, CronTrigger, RecurringDaysTrigger
- Schedule: schedule_id, name, routines (embedded with triggers)

Usage:
    from webui.backend.lib.schedule_schema import (
        Schedule,
        Routine,
        Action,
        TimeWindow,
        IntervalTrigger,
        SolarTrigger,
        validate_schedule,
    )

    # Create a schedule with multiple routines (each with own trigger)
    schedule = Schedule(
        schedule_id="",
        name="Overnight Moth Survey",
        routines=[
            Routine(
                routine_id="",
                trigger=SolarTrigger(solar_event="dusk"),
                actions=[Action(action_type="gpio", action_name="attract_on")],
            ),
            Routine(
                routine_id="",
                trigger=IntervalTrigger(
                    interval_minutes=15,
                    time_window=TimeWindow(start_time="22:00", end_time="06:00"),
                ),
                actions=[
                    Action(action_type="gpio", action_name="flash_on"),
                    Action(action_type="camera", action_name="takephoto", offset_minutes=1),
                    Action(action_type="gpio", action_name="flash_off", offset_minutes=2),
                ],
            ),
            Routine(
                routine_id="",
                trigger=SolarTrigger(solar_event="dawn"),
                actions=[Action(action_type="gpio", action_name="attract_off")],
            ),
        ],
    )

    # Validate
    valid, error = validate_schedule(schedule)
    if valid:
        data = schedule.to_dict()  # Serialize to JSON

Issue #208 - Scheduler Phase 1: Schedule Schema
Issue #300 - Update Schedule Class for Routine-Based Model
"""

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Final

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# Schema version
SCHEDULE_SCHEMA_VERSION: Final[str] = "3.0"
SUPPORTED_VERSIONS: Final[list[str]] = ["3.0"]

# Validation limits
MAX_PATTERN_NAME_LENGTH: Final[int] = 200
MAX_DESCRIPTION_LENGTH: Final[int] = 2000
MAX_ACTIONS_PER_PATTERN: Final[int] = 20
MAX_ROUTINES_PER_SCHEDULE: Final[int] = 10
MAX_OFFSET_MINUTES: Final[int] = 1440  # 24 hours
MAX_INTERVAL_MINUTES: Final[int] = 10080  # 7 days
MIN_INTERVAL_MINUTES: Final[int] = 1
MAX_COOLDOWN_MINUTES: Final[int] = 60
MAX_OFFSET_DAYS: Final[int] = 7
MAX_RECURRING_DAYS: Final[int] = 365

# Action display names for auto-generation (used by Routine.get_display_name())
ACTION_DISPLAY_NAMES: Final[dict[str, str]] = {
    "attract_on": "Attract On",
    "attract_off": "Attract Off",
    "flash_on": "Flash On",
    "flash_off": "Flash Off",
    "takephoto": "Photo",
    "gps_sync": "GPS Sync",
    "backup": "Backup",
    "update_display": "Update Display",
}

# Action types (aligned with cron_security.py ACTION_TYPE_SCRIPTS)
ACTION_TYPES: Final[list[str]] = ["gpio", "camera", "gps_sync", "service"]

# GPIO action names (UV lights = attract lights, same GPIO)
GPIO_ACTIONS: Final[list[str]] = [
    "attract_on",
    "attract_off",
    "flash_on",
    "flash_off",
]

# Trigger types
TRIGGER_TYPES: Final[list[str]] = [
    "interval",
    "solar",
    "moon_phase",
    "fixed_time",
    "sensor",
    "cron",
    "recurring_days",
]

# Primary trigger types (excludes sensor which can only be pre_condition)
PRIMARY_TRIGGER_TYPES: Final[list[str]] = [
    "interval",
    "solar",
    "moon_phase",
    "fixed_time",
    "cron",
    "recurring_days",
]

# Moon phases (8 phases of lunar cycle)
MOON_PHASES: Final[list[str]] = [
    "new",
    "waxing_crescent",
    "first_quarter",
    "waxing_gibbous",
    "full",
    "waning_gibbous",
    "last_quarter",
    "waning_crescent",
]

# Solar events (from astral library)
SOLAR_EVENTS: Final[list[str]] = [
    "dawn",
    "sunrise",
    "noon",
    "sunset",
    "dusk",
    "civil_dawn",
    "civil_dusk",
    "nautical_dawn",
    "nautical_dusk",
    "astronomical_dawn",
    "astronomical_dusk",
    "golden_hour_start",
    "golden_hour_end",
    "blue_hour_start",
    "blue_hour_end",
]

# Sensor types and comparisons
SENSOR_TYPES: Final[list[str]] = ["motion", "light", "temperature"]
SENSOR_COMPARISONS: Final[list[str]] = ["gt", "lt", "eq", "gte", "lte"]

# Days of week (0=Monday, 6=Sunday per ISO 8601)
DAYS_OF_WEEK: Final[list[int]] = [0, 1, 2, 3, 4, 5, 6]

# Pattern categories
PATTERN_CATEGORIES: Final[list[str]] = ["built-in", "user"]

# Time format regex (HH:MM, 24-hour format)
TIME_FORMAT_REGEX = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")

# Date format regex (YYYY-MM-DD)
DATE_FORMAT_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# =============================================================================
# EXCEPTIONS
# =============================================================================


class ScheduleValidationError(Exception):
    """Raised when schedule validation fails."""


class ScheduleConflictError(Exception):
    """Raised when schedule activation is blocked by conflicts."""


class ScheduleActivationError(Exception):
    """Raised when schedule activation fails (not due to conflicts)."""


# =============================================================================
# TIER 1: PATTERN ACTION
# =============================================================================


@dataclass
class Action:
    """
    A single action within a routine.

    Actions use relative offsets from routine start (t=0), enabling
    coordinated multi-action sequences like:
    - UV_ON at t+0
    - TakePhoto at t+5
    - UV_OFF at t+15

    Attributes:
        action_type: Category ("gpio", "camera", "gps_sync", "service")
        action_name: Specific action (e.g., "attract_on", "takephoto")
        offset_minutes: Minutes from routine start (t=0). Default 0, max 1440.
        parameters: Action-specific configuration dict
        description: Human-readable description (max 500 chars)

    Example:
        >>> action = Action(
        ...     action_type="gpio",
        ...     action_name="attract_on",
        ...     offset_minutes=0,
        ...     description="Turn on UV attract lights",
        ... )
    """

    action_type: str
    action_name: str
    offset_minutes: int = 0
    parameters: dict = field(default_factory=dict)
    description: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "action_type": self.action_type,
            "action_name": self.action_name,
            "offset_minutes": self.offset_minutes,
            "parameters": self.parameters,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Action":
        """Create from dictionary."""
        return cls(
            action_type=data["action_type"],
            action_name=data["action_name"],
            offset_minutes=data.get("offset_minutes", 0),
            parameters=data.get("parameters", {}),
            description=data.get("description", ""),
        )


# =============================================================================
# TIER 1: EVENT PATTERN
# =============================================================================


@dataclass
class EventPattern:
    """
    Reusable template defining a sequence of timed actions.

    Event patterns are library items that can be reused across multiple
    schedules. Actions use relative offsets from pattern start (t=0).

    Example: "UV Capture Cycle"
    - UV_ON at offset +0 minutes
    - TakePhoto at offset +5 minutes
    - UV_OFF at offset +15 minutes
    - duration_minutes = 15 (computed from max offset)

    Attributes:
        pattern_id: Unique identifier (UUID string, auto-generated if empty)
        name: Human-readable name (required, max 200 chars)
        description: Detailed description (max 2000 chars)
        actions: Ordered list of Action objects
        category: "built-in" or "user"
        tags: Tags for filtering/search

    Example:
        >>> pattern = EventPattern(
        ...     pattern_id="",
        ...     name="UV Capture Cycle",
        ...     actions=[
        ...         Action(action_type="gpio", action_name="attract_on"),
        ...         Action(action_type="camera", action_name="takephoto", offset_minutes=5),
        ...         Action(action_type="gpio", action_name="attract_off", offset_minutes=15),
        ...     ],
        ... )
        >>> pattern.duration_minutes
        15
    """

    pattern_id: str
    name: str
    description: str = ""
    actions: list[Action] = field(default_factory=list)
    category: str = "user"
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Generate UUID if pattern_id is empty."""
        if not self.pattern_id:
            self.pattern_id = str(uuid.uuid4())

    @property
    def duration_minutes(self) -> int:
        """Total duration = max action offset."""
        return max((action.offset_minutes for action in self.actions), default=0)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "pattern_id": self.pattern_id,
            "name": self.name,
            "description": self.description,
            "actions": [action.to_dict() for action in self.actions],
            "category": self.category,
            "tags": self.tags,
            "duration_minutes": self.duration_minutes,  # Computed, read-only
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EventPattern":
        """Create from dictionary."""
        return cls(
            pattern_id=data.get("pattern_id", ""),
            name=data["name"],
            description=data.get("description", ""),
            actions=[Action.from_dict(a) for a in data.get("actions", [])],
            category=data.get("category", "user"),
            tags=data.get("tags", []),
        )


# =============================================================================
# TIER 2: TIME WINDOW
# =============================================================================


@dataclass
class TimeWindow:
    """
    Daily time window for schedule execution.

    Supports both fixed times ("HH:MM") and solar events ("sunset").

    Attributes:
        start_time: Window start ("HH:MM" or solar event name)
        end_time: Window end ("HH:MM" or solar event name)
        start_offset_minutes: Offset from start solar event (default 0)
        end_offset_minutes: Offset from end solar event (default 0)

    Example:
        >>> # Fixed time window
        >>> window = TimeWindow(start_time="21:00", end_time="05:00")

        >>> # Solar-based window with offsets
        >>> window = TimeWindow(
        ...     start_time="sunset",
        ...     end_time="sunrise",
        ...     start_offset_minutes=30,  # 30 min after sunset
        ...     end_offset_minutes=-30,  # 30 min before sunrise
        ... )
    """

    start_time: str
    end_time: str
    start_offset_minutes: int = 0
    end_offset_minutes: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "start_offset_minutes": self.start_offset_minutes,
            "end_offset_minutes": self.end_offset_minutes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TimeWindow":
        """Create from dictionary."""
        return cls(
            start_time=data["start_time"],
            end_time=data["end_time"],
            start_offset_minutes=data.get("start_offset_minutes", 0),
            end_offset_minutes=data.get("end_offset_minutes", 0),
        )


# =============================================================================
# TIER 2: TRIGGER DATACLASSES
# =============================================================================


@dataclass
class IntervalTrigger:
    """
    Execute pattern every N minutes within time window.

    Example: Every 60 minutes from 21:00 to 05:00

    Attributes:
        interval_minutes: Interval in minutes (1 to 10080, i.e., 1 min to 7 days)
        time_window: When executions can occur
        days_of_week: 0=Mon..6=Sun, None=every day
    """

    interval_minutes: int
    time_window: TimeWindow
    days_of_week: list[int] | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "interval_minutes": self.interval_minutes,
            "time_window": self.time_window.to_dict(),
            "days_of_week": self.days_of_week,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "IntervalTrigger":
        """Create from dictionary."""
        return cls(
            interval_minutes=data["interval_minutes"],
            time_window=TimeWindow.from_dict(data["time_window"]),
            days_of_week=data.get("days_of_week"),
        )


@dataclass
class SolarTrigger:
    """
    Execute pattern relative to solar event.

    Example: At sunset+30 every day

    Attributes:
        solar_event: Event name ("sunset", "astronomical_dusk", etc.)
        offset_minutes: +/- minutes from event
        days_of_week: 0=Mon..6=Sun, None=every day
    """

    solar_event: str
    offset_minutes: int = 0
    days_of_week: list[int] | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "solar_event": self.solar_event,
            "offset_minutes": self.offset_minutes,
            "days_of_week": self.days_of_week,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SolarTrigger":
        """Create from dictionary."""
        return cls(
            solar_event=data["solar_event"],
            offset_minutes=data.get("offset_minutes", 0),
            days_of_week=data.get("days_of_week"),
        )


@dataclass
class MoonPhaseTrigger:
    """
    Execute pattern on moon phases.

    Example: On full moon +/- 2 days, from dusk to dawn

    Attributes:
        phases: List of phases to match (["full", "new"], etc.)
        offset_days: +/- days from exact phase (max 7)
        time_window: Optional execution window on phase days
    """

    phases: list[str]
    offset_days: int = 0
    time_window: TimeWindow | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "phases": self.phases,
            "offset_days": self.offset_days,
            "time_window": self.time_window.to_dict() if self.time_window else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MoonPhaseTrigger":
        """Create from dictionary."""
        return cls(
            phases=data["phases"],
            offset_days=data.get("offset_days", 0),
            time_window=(
                TimeWindow.from_dict(data["time_window"]) if data.get("time_window") else None
            ),
        )


@dataclass
class FixedTimeTrigger:
    """
    Execute pattern at specific fixed time daily.

    Example: Every day at 21:00

    Attributes:
        time: Fixed time in "HH:MM" format
        days_of_week: 0=Mon..6=Sun, None=every day
    """

    time: str
    days_of_week: list[int] | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "time": self.time,
            "days_of_week": self.days_of_week,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FixedTimeTrigger":
        """Create from dictionary."""
        return cls(
            time=data["time"],
            days_of_week=data.get("days_of_week"),
        )


@dataclass
class SensorTrigger:
    """
    Execute pattern based on sensor readings.

    Supported sensors:
    - "motion": PIR sensor, trigger on detection (threshold ignored)
    - "light": LDR sensor, trigger when lux crosses threshold
    - "temperature": Temp sensor, trigger on threshold crossing

    Attributes:
        sensor_type: Sensor type ("motion", "light", "temperature")
        threshold: Trigger threshold value (ignored for motion)
        comparison: Comparison operator ("gt", "lt", "eq", "gte", "lte")
        cooldown_minutes: Min time between triggers (default 5, max 60)
        time_window: Optional window to restrict sensor triggers
    """

    sensor_type: str
    threshold: float = 0.0
    comparison: str = "gt"
    cooldown_minutes: int = 5
    time_window: TimeWindow | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "sensor_type": self.sensor_type,
            "threshold": self.threshold,
            "comparison": self.comparison,
            "cooldown_minutes": self.cooldown_minutes,
            "time_window": self.time_window.to_dict() if self.time_window else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SensorTrigger":
        """Create from dictionary."""
        return cls(
            sensor_type=data["sensor_type"],
            threshold=data.get("threshold", 0.0),
            comparison=data.get("comparison", "gt"),
            cooldown_minutes=data.get("cooldown_minutes", 5),
            time_window=(
                TimeWindow.from_dict(data["time_window"]) if data.get("time_window") else None
            ),
        )


@dataclass
class CronTrigger:
    """Raw cron expression trigger for expert mode.

    Attributes:
        cron_expression: Standard 5-field cron expression (minute hour day month weekday)
    """

    cron_expression: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "cron_expression": self.cron_expression,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CronTrigger":
        """Create from dictionary."""
        return cls(
            cron_expression=data["cron_expression"],
        )


@dataclass
class RecurringDaysTrigger:
    """
    Execute pattern every N days at a specific time.

    Example: GPS sync every 3 days at 21:00

    Attributes:
        every_n_days: Days between executions (1-365)
        time: Fixed time in "HH:MM" format
        start_date: ISO 8601 date (YYYY-MM-DD). If None, defaults to today
                    when cron expressions are generated (handled by cron_bridge.py)
    """

    every_n_days: int = 1
    time: str = "00:00"
    start_date: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "every_n_days": self.every_n_days,
            "time": self.time,
            "start_date": self.start_date,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RecurringDaysTrigger":
        """Create from dictionary."""
        return cls(
            every_n_days=data.get("every_n_days", 1),
            time=data.get("time", "00:00"),
            start_date=data.get("start_date"),
        )


# =============================================================================
# TRIGGER UNION TYPE
# =============================================================================

# Trigger union type - all trigger types that can drive a routine
Trigger = (
    IntervalTrigger
    | SolarTrigger
    | MoonPhaseTrigger
    | FixedTimeTrigger
    | SensorTrigger
    | CronTrigger
    | RecurringDaysTrigger
)

# Mapping from trigger class to trigger_type string (DRY principle)
TRIGGER_TYPE_MAP: Final[dict[type, str]] = {
    IntervalTrigger: "interval",
    SolarTrigger: "solar",
    MoonPhaseTrigger: "moon_phase",
    FixedTimeTrigger: "fixed_time",
    SensorTrigger: "sensor",
    CronTrigger: "cron",
    RecurringDaysTrigger: "recurring_days",
}

# Inverse mapping from trigger_type string to trigger class
TRIGGER_CLASS_MAP: Final[dict[str, type]] = {v: k for k, v in TRIGGER_TYPE_MAP.items()}


def trigger_from_dict(data: dict) -> Trigger:
    """
    Factory function to create appropriate trigger from dictionary.

    Example:
        >>> data = {"trigger_type": "recurring_days", "every_n_days": 3, "time": "21:00"}
        >>> trigger = trigger_from_dict(data)
        >>> isinstance(trigger, RecurringDaysTrigger)
        True
        >>> trigger.every_n_days
        3

    Args:
        data: Dictionary containing trigger_type and trigger-specific fields

    Returns:
        Appropriate trigger instance based on trigger_type

    Raises:
        ValueError: If trigger_type is missing or unknown
    """
    trigger_type = data.get("trigger_type")

    if not trigger_type:
        raise ValueError("trigger_type is required")

    trigger_class = TRIGGER_CLASS_MAP.get(trigger_type)
    if trigger_class is None:
        raise ValueError(f"Unknown trigger_type: {trigger_type}")

    return trigger_class.from_dict(data)


# =============================================================================
# TIER 2: ROUTINE
# =============================================================================


@dataclass
class Routine:
    """
    Simplified single-pattern schedule with unified trigger.

    Routine represents a single action sequence with one trigger, providing
    a simpler alternative to Schedule for common use cases. It combines
    actions, trigger, and optional sensor pre-condition into one entity.

    Attributes:
        routine_id: Unique identifier (UUID string, auto-generated if empty)
        name: Optional human-readable name (None for auto-generated)
        trigger: Trigger configuration (any supported trigger type)
        actions: Ordered list of Action objects
        pre_condition: Optional sensor trigger as gate (must pass before execution)
        description: Human-readable description (max 2000 chars)

    Example:
        >>> routine = Routine(
        ...     routine_id="",
        ...     name="Sunset Photos",
        ...     trigger=SolarTrigger(solar_event="sunset", offset_minutes=30),
        ...     actions=[
        ...         Action(action_type="camera", action_name="takephoto"),
        ...     ],
        ... )
        >>> routine.get_display_name()
        'Sunset Photos'
        >>> routine.duration_minutes
        0
    """

    routine_id: str
    name: str | None = None
    trigger: Trigger = field(
        default_factory=lambda: IntervalTrigger(
            interval_minutes=60,
            time_window=TimeWindow(start_time="00:00", end_time="23:59"),
        )
    )
    actions: list[Action] = field(default_factory=list)
    pre_condition: SensorTrigger | None = None
    description: str = ""

    def __post_init__(self):
        """Generate UUID if routine_id is empty, normalize name."""
        if not self.routine_id:
            self.routine_id = str(uuid.uuid4())
        # Normalize empty string to None
        if self.name == "":
            self.name = None

    @property
    def duration_minutes(self) -> int:
        """Total duration = max action offset."""
        return max((action.offset_minutes for action in self.actions), default=0)

    def get_display_name(self) -> str:
        """Get display name (explicit name or auto-generated)."""
        if self.name:
            return self.name
        return self._generate_name()

    def _generate_name(self) -> str:
        """Generate name from actions and trigger."""
        action_summary = self._summarize_actions()
        trigger_desc = self._describe_trigger()
        return f"{action_summary} {trigger_desc}"

    def _summarize_actions(self) -> str:
        """Smart action summary using ACTION_DISPLAY_NAMES."""
        if not self.actions:
            return "Empty Routine"

        action_names = [action.action_name for action in self.actions]

        # If all actions are the same type (e.g., 3x takephoto), show count prefix
        if len(set(action_names)) == 1:
            action_name = action_names[0]
            display_name = ACTION_DISPLAY_NAMES.get(action_name, action_name.title())
            if len(action_names) == 1:
                return display_name
            # Repeated same action
            return f"{len(action_names)}x {display_name}"

        # Detect flash_on + takephoto pattern
        action_set = set(action_names)
        if action_set == {"flash_on", "takephoto"}:
            return "Flash + Photo"

        # Multiple different actions
        return f"{len(self.actions)} Actions"

    def _describe_trigger(self) -> str:
        """Human-readable trigger description."""
        if isinstance(self.trigger, SolarTrigger):
            event = self.trigger.solar_event.replace("_", " ").title()
            if self.trigger.offset_minutes == 0:
                return f"at {event}"
            sign = "+" if self.trigger.offset_minutes > 0 else ""
            return f"at {event} {sign}{self.trigger.offset_minutes}min"

        elif isinstance(self.trigger, IntervalTrigger):
            minutes = self.trigger.interval_minutes
            if minutes < 60:
                return f"every {minutes}min"
            hours = minutes // 60
            if hours == 1:
                return "every 1h"
            return f"every {hours}h"

        elif isinstance(self.trigger, FixedTimeTrigger):
            return f"at {self.trigger.time}"

        elif isinstance(self.trigger, MoonPhaseTrigger):
            phases = [p.replace("_", " ").title() for p in self.trigger.phases]
            phase_str = ", ".join(phases)
            return f"on {phase_str}"

        elif isinstance(self.trigger, RecurringDaysTrigger):
            if self.trigger.every_n_days == 1:
                return f"daily at {self.trigger.time}"
            return f"every {self.trigger.every_n_days} days at {self.trigger.time}"

        elif isinstance(self.trigger, CronTrigger):
            return "(cron)"

        elif isinstance(self.trigger, SensorTrigger):
            sensor = self.trigger.sensor_type
            comparison = self.trigger.comparison
            threshold = self.trigger.threshold
            return f"when {sensor} {comparison} {threshold}"

        return "(unknown trigger)"

    def _trigger_to_dict(self) -> dict:
        """Serialize trigger with trigger_type added."""
        trigger_dict = self.trigger.to_dict()
        trigger_type = TRIGGER_TYPE_MAP.get(type(self.trigger))
        if trigger_type:
            trigger_dict["trigger_type"] = trigger_type
        return trigger_dict

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "routine_id": self.routine_id,
            "name": self.name,
            "trigger": self._trigger_to_dict(),
            "actions": [action.to_dict() for action in self.actions],
            "pre_condition": self.pre_condition.to_dict() if self.pre_condition else None,
            "description": self.description,
            "display_name": self.get_display_name(),
            "duration_minutes": self.duration_minutes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Routine":
        """Create from dictionary."""
        # Parse trigger using trigger_from_dict factory
        trigger_data = data.get("trigger", {})
        try:
            trigger = trigger_from_dict(trigger_data)
        except (ValueError, KeyError) as e:
            raise ValueError(f"Failed to deserialize routine trigger: {e}") from e

        # Parse pre_condition if present
        pre_condition = None
        if data.get("pre_condition"):
            try:
                pre_condition = SensorTrigger.from_dict(data["pre_condition"])
            except (ValueError, KeyError) as e:
                raise ValueError(f"Failed to deserialize pre_condition: {e}") from e

        return cls(
            routine_id=data.get("routine_id", ""),
            name=data.get("name"),
            trigger=trigger,
            actions=[Action.from_dict(a) for a in data.get("actions", [])],
            pre_condition=pre_condition,
            description=data.get("description", ""),
        )


# =============================================================================
# TIER 2: SCHEDULE
# =============================================================================


@dataclass
class Schedule:
    """
    Complete schedule with embedded routines (single-file storage).

    Each schedule is fully self-contained with routines embedded inline,
    making it portable and easy to export/import between Mothbox units.

    Schema 3.0: Routines contain their own trigger configuration, eliminating
    schedule-level trigger fields. This allows mixed trigger types within a
    single schedule (e.g., solar triggers for UV on/off + interval for photos).

    Attributes:
        schedule_id: Unique identifier (UUID string, auto-generated if empty)
        name: Human-readable name (required, max 200 chars)
        description: Detailed description (max 2000 chars)
        routines: Embedded Routine objects (each with its own trigger)
        deployment_id: Linked deployment ID
        create_deployment: Create deployment on activation
        enabled: Whether schedule is enabled
        is_active: Whether schedule is currently active
        created_at: Creation timestamp (ISO 8601)
        modified_at: Last modification timestamp (ISO 8601)
        modified_by: User identifier

    Example:
        >>> schedule = Schedule(
        ...     schedule_id="",
        ...     name="Overnight Moth Survey",
        ...     routines=[
        ...         Routine(
        ...             routine_id="",
        ...             trigger=SolarTrigger(solar_event="dusk"),
        ...             actions=[Action(action_type="gpio", action_name="attract_on")],
        ...         ),
        ...         Routine(
        ...             routine_id="",
        ...             trigger=IntervalTrigger(interval_minutes=15),
        ...             actions=[Action(action_type="camera", action_name="takephoto")],
        ...         ),
        ...     ],
        ... )
    """

    schedule_id: str
    name: str
    description: str = ""
    routines: list[Routine] = field(default_factory=list)

    # Deployment linkage
    deployment_id: str | None = None
    create_deployment: bool = False

    # State
    enabled: bool = True
    is_active: bool = False

    # Metadata
    created_at: str = ""
    modified_at: str = ""
    modified_by: str | None = None

    def __post_init__(self):
        """Generate UUID and timestamps if empty."""
        if not self.schedule_id:
            self.schedule_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.modified_at:
            self.modified_at = self.created_at

    @property
    def total_duration_minutes(self) -> int:
        """Total duration of all routines combined."""
        return sum(routine.duration_minutes for routine in self.routines)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "schema_version": SCHEDULE_SCHEMA_VERSION,
            "schedule_id": self.schedule_id,
            "name": self.name,
            "description": self.description,
            "routines": [r.to_dict() for r in self.routines],
            "deployment_id": self.deployment_id,
            "create_deployment": self.create_deployment,
            "enabled": self.enabled,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "modified_by": self.modified_by,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Schedule":
        """Create from dictionary.

        Args:
            data: Dictionary with schedule data in schema 3.0 format.
                  Must contain 'routines' list with embedded triggers.

        Returns:
            Schedule instance

        Raises:
            ValueError: If data uses old schema format (event_patterns or
                       schedule-level triggers) or unsupported schema version
        """
        # Validate schema version if present
        schema_version = data.get("schema_version")
        if schema_version is not None and schema_version not in SUPPORTED_VERSIONS:
            raise ValueError(
                f"Unsupported schema version: {schema_version}. "
                f"Supported versions: {SUPPORTED_VERSIONS}"
            )

        # Reject old schema format
        if "event_patterns" in data:
            raise ValueError(
                "Old schema format detected: 'event_patterns' is no longer supported. "
                "Use 'routines' with embedded triggers instead (schema 3.0)."
            )

        if "trigger_type" in data or "trigger" in data:
            raise ValueError(
                "Old schema format detected: Schedule-level triggers are no longer "
                "supported. Each routine must have its own trigger (schema 3.0)."
            )

        return cls(
            schedule_id=data.get("schedule_id", ""),
            name=data["name"],
            description=data.get("description", ""),
            routines=[Routine.from_dict(r) for r in data.get("routines", [])],
            deployment_id=data.get("deployment_id"),
            create_deployment=data.get("create_deployment", False),
            enabled=data.get("enabled", True),
            is_active=data.get("is_active", False),
            created_at=data.get("created_at", ""),
            modified_at=data.get("modified_at", ""),
            modified_by=data.get("modified_by"),
        )


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================


def _is_valid_time_format(time_str: str) -> bool:
    """Check if string is valid HH:MM format."""
    return TIME_FORMAT_REGEX.match(time_str) is not None


def _is_valid_solar_event(event: str) -> bool:
    """Check if string is a valid solar event name."""
    return event in SOLAR_EVENTS


def _is_valid_time_spec(time_str: str) -> bool:
    """Check if string is valid time specification (HH:MM or solar event)."""
    return _is_valid_time_format(time_str) or _is_valid_solar_event(time_str)


def _validate_days_of_week(days: list[int] | None) -> tuple[bool, str | None]:
    """Validate days of week list."""
    if days is None:
        return True, None

    if not isinstance(days, list):
        return False, "days_of_week must be a list"

    if len(days) == 0:
        return False, "days_of_week cannot be empty if provided"

    for day in days:
        if not isinstance(day, int) or day < 0 or day > 6:
            return False, f"Invalid day of week: {day}. Must be 0-6 (Mon-Sun)"

    return True, None


def _validate_date_string(date_str: str | None) -> tuple[bool, str | None]:
    """Validate ISO 8601 date string (YYYY-MM-DD)."""
    if date_str is None:
        return True, None

    if not DATE_FORMAT_REGEX.match(date_str):
        return False, f"Invalid date format: {date_str}. Expected YYYY-MM-DD"

    # Validate the date is actually valid (e.g., not 2024-02-30)
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as e:
        return False, f"Invalid date: {date_str}. {e}"

    return True, None


def _is_valid_uuid(uuid_string: str) -> bool:
    """
    Check if string is a valid UUID format.

    Args:
        uuid_string: String to validate as UUID

    Returns:
        True if valid UUID format, False otherwise
    """
    try:
        uuid.UUID(uuid_string)
        return True
    except (ValueError, AttributeError):
        return False


def validate_action(action: Action) -> tuple[bool, str | None]:
    """
    Validate a single action.

    Args:
        action: Action to validate

    Returns:
        (True, None) if valid, (False, error_message) if invalid
    """
    # Validate action_type
    if action.action_type not in ACTION_TYPES:
        return (
            False,
            f"Invalid action type: '{action.action_type}'. "
            f"Must be one of: {', '.join(ACTION_TYPES)}",
        )

    # Validate offset_minutes range
    if action.offset_minutes < 0:
        return False, "Action offset cannot be negative"

    if action.offset_minutes > MAX_OFFSET_MINUTES:
        return (
            False,
            f"Action offset {action.offset_minutes} exceeds maximum "
            f"of {MAX_OFFSET_MINUTES} minutes (24 hours)",
        )

    return True, None


def validate_event_pattern(pattern: EventPattern) -> tuple[bool, str | None]:
    """
    Validate an event pattern and its actions.

    Args:
        pattern: EventPattern to validate

    Returns:
        (True, None) if valid, (False, error_message) if invalid
    """
    # Validate pattern_id format if provided (auto-generated UUIDs are always valid)
    if pattern.pattern_id and not _is_valid_uuid(pattern.pattern_id):
        return False, "Invalid pattern_id format: must be a valid UUID"

    # Validate name
    if not pattern.name or not pattern.name.strip():
        return False, "Pattern name is required"

    if len(pattern.name) > MAX_PATTERN_NAME_LENGTH:
        return (
            False,
            f"Pattern name exceeds {MAX_PATTERN_NAME_LENGTH} characters",
        )

    # Validate description length
    if len(pattern.description) > MAX_DESCRIPTION_LENGTH:
        return (
            False,
            f"Pattern description exceeds {MAX_DESCRIPTION_LENGTH} characters",
        )

    # Validate actions
    if not pattern.actions:
        return False, "Pattern must have at least one action"

    if len(pattern.actions) > MAX_ACTIONS_PER_PATTERN:
        return (
            False,
            f"Pattern exceeds {MAX_ACTIONS_PER_PATTERN} actions",
        )

    # Validate each action
    for i, action in enumerate(pattern.actions):
        valid, error = validate_action(action)
        if not valid:
            return False, f"Action {i + 1}: {error}"

    # Validate category
    if pattern.category not in PATTERN_CATEGORIES:
        return (
            False,
            f"Invalid category: '{pattern.category}'. "
            f"Must be one of: {', '.join(PATTERN_CATEGORIES)}",
        )

    return True, None


def _validate_routine_trigger(trigger: Trigger) -> tuple[bool, str | None]:
    """
    Validate routine trigger using appropriate validator based on type.

    Args:
        trigger: Trigger instance to validate

    Returns:
        (True, None) if valid, (False, error_message) if invalid
    """
    if isinstance(trigger, IntervalTrigger):
        return validate_interval_trigger(trigger)
    elif isinstance(trigger, SolarTrigger):
        return validate_solar_trigger(trigger)
    elif isinstance(trigger, MoonPhaseTrigger):
        return validate_moon_phase_trigger(trigger)
    elif isinstance(trigger, FixedTimeTrigger):
        return validate_fixed_time_trigger(trigger)
    elif isinstance(trigger, SensorTrigger):
        return validate_sensor_trigger(trigger)
    elif isinstance(trigger, CronTrigger):
        return validate_cron_trigger(trigger)
    elif isinstance(trigger, RecurringDaysTrigger):
        return validate_recurring_days_trigger(trigger)
    else:
        return False, f"Unknown trigger type: {type(trigger).__name__}"


def validate_routine(routine) -> tuple[bool, str | None]:
    """
    Validate a routine and its actions.

    Args:
        routine: Routine to validate

    Returns:
        (True, None) if valid, (False, error_message) if invalid
    """
    # Validate routine_id format if provided (auto-generated UUIDs are always valid)
    if routine.routine_id and not _is_valid_uuid(routine.routine_id):
        return False, "Invalid routine_id format: must be a valid UUID"

    # Validate name length if provided
    if routine.name and len(routine.name) > MAX_PATTERN_NAME_LENGTH:
        return (
            False,
            f"Routine name exceeds {MAX_PATTERN_NAME_LENGTH} characters",
        )

    # Validate description length
    if len(routine.description) > MAX_DESCRIPTION_LENGTH:
        return (
            False,
            f"Routine description exceeds {MAX_DESCRIPTION_LENGTH} characters",
        )

    # Validate trigger exists
    if routine.trigger is None:
        return False, "Routine must have a trigger"

    # Block SensorTrigger as primary trigger (sensor can only be pre_condition)
    # See PRIMARY_TRIGGER_TYPES for the list of valid primary triggers
    if isinstance(routine.trigger, SensorTrigger):
        return (
            False,
            "Sensor triggers can only be used as pre_condition, not as primary trigger",
        )

    # Validate trigger
    valid, error = _validate_routine_trigger(routine.trigger)
    if not valid:
        return False, f"Trigger: {error}"

    # Validate pre_condition if provided
    if routine.pre_condition is not None:
        # Must be a SensorTrigger instance
        if not isinstance(routine.pre_condition, SensorTrigger):
            return False, "pre_condition must be a SensorTrigger"

        # Validate the sensor trigger
        valid, error = validate_sensor_trigger(routine.pre_condition)
        if not valid:
            return False, f"Pre-condition: {error}"

    # Validate actions
    if not routine.actions:
        return False, "Routine must have at least one action"

    if len(routine.actions) > MAX_ACTIONS_PER_PATTERN:
        return (
            False,
            f"Routine exceeds {MAX_ACTIONS_PER_PATTERN} actions",
        )

    # Validate each action
    for i, action in enumerate(routine.actions):
        valid, error = validate_action(action)
        if not valid:
            return False, f"Action {i + 1}: {error}"

    return True, None


def validate_time_window(window: TimeWindow) -> tuple[bool, str | None]:
    """
    Validate time window configuration.

    Args:
        window: TimeWindow to validate

    Returns:
        (True, None) if valid, (False, error_message) if invalid
    """
    # Validate start_time
    if not _is_valid_time_spec(window.start_time):
        return (
            False,
            f"Invalid start_time: '{window.start_time}'. "
            f"Must be HH:MM format or a solar event ({', '.join(SOLAR_EVENTS[:5])}...)",
        )

    # Validate end_time
    if not _is_valid_time_spec(window.end_time):
        return (
            False,
            f"Invalid end_time: '{window.end_time}'. "
            f"Must be HH:MM format or a solar event ({', '.join(SOLAR_EVENTS[:5])}...)",
        )

    # Validate offset ranges (allow +/- 2 hours for solar events)
    max_offset = 120
    if abs(window.start_offset_minutes) > max_offset:
        return (
            False,
            f"start_offset_minutes {window.start_offset_minutes} exceeds +/- {max_offset} minutes",
        )

    if abs(window.end_offset_minutes) > max_offset:
        return (
            False,
            f"end_offset_minutes {window.end_offset_minutes} exceeds +/- {max_offset} minutes",
        )

    return True, None


def validate_interval_trigger(trigger: IntervalTrigger) -> tuple[bool, str | None]:
    """
    Validate interval trigger configuration.

    Args:
        trigger: IntervalTrigger to validate

    Returns:
        (True, None) if valid, (False, error_message) if invalid
    """
    # Validate interval_minutes
    if trigger.interval_minutes < MIN_INTERVAL_MINUTES:
        return (
            False,
            f"Interval must be at least {MIN_INTERVAL_MINUTES} minute",
        )

    if trigger.interval_minutes > MAX_INTERVAL_MINUTES:
        return (
            False,
            f"Interval exceeds {MAX_INTERVAL_MINUTES} minutes (7 days)",
        )

    # Validate time_window
    valid, error = validate_time_window(trigger.time_window)
    if not valid:
        return False, f"Time window: {error}"

    # Validate days_of_week
    valid, error = _validate_days_of_week(trigger.days_of_week)
    if not valid:
        return False, error

    return True, None


def validate_solar_trigger(trigger: SolarTrigger) -> tuple[bool, str | None]:
    """
    Validate solar trigger configuration.

    Args:
        trigger: SolarTrigger to validate

    Returns:
        (True, None) if valid, (False, error_message) if invalid
    """
    # Validate solar_event
    if trigger.solar_event not in SOLAR_EVENTS:
        return (
            False,
            f"Invalid solar event: '{trigger.solar_event}'. "
            f"Must be one of: {', '.join(SOLAR_EVENTS[:5])}...",
        )

    # Validate offset_minutes (allow +/- 2 hours)
    max_offset = 120
    if abs(trigger.offset_minutes) > max_offset:
        return (
            False,
            f"Solar trigger offset {trigger.offset_minutes} exceeds +/- {max_offset} minutes",
        )

    # Validate days_of_week
    valid, error = _validate_days_of_week(trigger.days_of_week)
    if not valid:
        return False, error

    return True, None


def validate_moon_phase_trigger(
    trigger: MoonPhaseTrigger,
) -> tuple[bool, str | None]:
    """
    Validate moon phase trigger configuration.

    Args:
        trigger: MoonPhaseTrigger to validate

    Returns:
        (True, None) if valid, (False, error_message) if invalid
    """
    # Validate phases list
    if not trigger.phases:
        return False, "At least one moon phase must be specified"

    for phase in trigger.phases:
        if phase not in MOON_PHASES:
            return (
                False,
                f"Invalid moon phase: '{phase}'. Must be one of: {', '.join(MOON_PHASES)}",
            )

    # Validate offset_days
    if abs(trigger.offset_days) > MAX_OFFSET_DAYS:
        return (
            False,
            f"Moon phase offset {trigger.offset_days} exceeds +/- {MAX_OFFSET_DAYS} days",
        )

    # Validate time_window if provided
    if trigger.time_window:
        valid, error = validate_time_window(trigger.time_window)
        if not valid:
            return False, f"Time window: {error}"

    return True, None


def validate_fixed_time_trigger(trigger: FixedTimeTrigger) -> tuple[bool, str | None]:
    """
    Validate fixed time trigger configuration.

    Args:
        trigger: FixedTimeTrigger to validate

    Returns:
        (True, None) if valid, (False, error_message) if invalid
    """
    # Validate time format
    if not _is_valid_time_format(trigger.time):
        return (
            False,
            f"Invalid time format: '{trigger.time}'. Must be HH:MM (24-hour)",
        )

    # Validate days_of_week
    valid, error = _validate_days_of_week(trigger.days_of_week)
    if not valid:
        return False, error

    return True, None


def validate_sensor_trigger(trigger: SensorTrigger) -> tuple[bool, str | None]:
    """
    Validate sensor trigger configuration.

    Args:
        trigger: SensorTrigger to validate

    Returns:
        (True, None) if valid, (False, error_message) if invalid
    """
    # Validate sensor_type
    if trigger.sensor_type not in SENSOR_TYPES:
        return (
            False,
            f"Invalid sensor type: '{trigger.sensor_type}'. "
            f"Must be one of: {', '.join(SENSOR_TYPES)}",
        )

    # Validate comparison
    if trigger.comparison not in SENSOR_COMPARISONS:
        return (
            False,
            f"Invalid comparison operator: '{trigger.comparison}'. "
            f"Must be one of: {', '.join(SENSOR_COMPARISONS)}",
        )

    # Validate cooldown_minutes
    if trigger.cooldown_minutes < 0:
        return False, "cooldown_minutes cannot be negative"

    if trigger.cooldown_minutes > MAX_COOLDOWN_MINUTES:
        return (
            False,
            f"cooldown_minutes exceeds maximum of {MAX_COOLDOWN_MINUTES}",
        )

    # Validate time_window if provided
    if trigger.time_window:
        valid, error = validate_time_window(trigger.time_window)
        if not valid:
            return False, f"Time window: {error}"

    return True, None


def validate_cron_trigger(trigger: CronTrigger) -> tuple[bool, str | None]:
    """
    Validate cron trigger configuration.

    Args:
        trigger: CronTrigger to validate

    Returns:
        (True, None) if valid, (False, error_message) if invalid
    """
    # Explicit validation: cron_expression must not be empty
    if not trigger.cron_expression or not trigger.cron_expression.strip():
        return False, "Cron expression cannot be empty"

    # Import CronEntry here to avoid circular imports
    try:
        from webui.backend.lib.cron_bridge import CronEntry
    except ImportError:
        # If cron_bridge not available, do basic validation
        # Basic 5-field check
        fields = trigger.cron_expression.strip().split()
        if len(fields) != 5:
            return (
                False,
                "Cron expression must have exactly 5 fields (minute hour day month weekday)",
            )
        return True, None

    # Use CronEntry.is_valid_expression for thorough validation
    if not CronEntry.is_valid_expression(trigger.cron_expression):
        return False, f"Invalid cron expression: '{trigger.cron_expression}'"

    return True, None


def validate_recurring_days_trigger(
    trigger: RecurringDaysTrigger,
) -> tuple[bool, str | None]:
    """
    Validate recurring days trigger configuration.

    Args:
        trigger: RecurringDaysTrigger to validate

    Returns:
        (True, None) if valid, (False, error_message) if invalid
    """
    # Validate every_n_days range
    if trigger.every_n_days < 1:
        return False, "every_n_days must be at least 1"

    if trigger.every_n_days > MAX_RECURRING_DAYS:
        return False, f"every_n_days exceeds maximum of {MAX_RECURRING_DAYS}"

    # Validate time format (HH:MM)
    if not _is_valid_time_format(trigger.time):
        return False, f"Invalid time format: '{trigger.time}'. Must be HH:MM (24-hour)"

    # Validate start_date if provided
    if trigger.start_date:
        valid, error = _validate_date_string(trigger.start_date)
        if not valid:
            return False, f"start_date: {error}"

    return True, None


def validate_routine_ids_unique(schedule: Schedule) -> tuple[bool, str | None]:
    """
    Ensure all routine IDs within a schedule are unique.

    Args:
        schedule: Schedule to validate

    Returns:
        (True, None) if valid, (False, error_message) if duplicate IDs found
    """
    if not schedule.routines:
        return True, None

    routine_ids = [r.routine_id for r in schedule.routines]

    # Check for empty string IDs (defensive - post_init should auto-generate)
    if any(not rid for rid in routine_ids):
        return False, "Routine IDs cannot be empty"

    if len(routine_ids) != len(set(routine_ids)):
        seen = set()
        duplicates = set()
        for rid in routine_ids:
            if rid in seen:
                duplicates.add(rid)
            seen.add(rid)
        return False, f"Duplicate routine IDs: {sorted(duplicates)}"

    return True, None


def validate_schedule(schedule: Schedule) -> tuple[bool, str | None]:
    """
    Validate a complete schedule with all embedded routines.

    Schema 3.0: Each routine has its own embedded trigger. Schedule-level
    trigger configuration is no longer supported.

    Args:
        schedule: Schedule to validate

    Returns:
        (True, None) if valid, (False, error_message) if invalid
    """
    # Validate schedule_id format if provided (auto-generated UUIDs are always valid)
    if schedule.schedule_id and not _is_valid_uuid(schedule.schedule_id):
        return False, "Invalid schedule_id format: must be a valid UUID"

    # Validate name
    if not schedule.name or not schedule.name.strip():
        return False, "Schedule name is required"

    if len(schedule.name) > MAX_PATTERN_NAME_LENGTH:
        return (
            False,
            f"Schedule name exceeds {MAX_PATTERN_NAME_LENGTH} characters",
        )

    # Validate description length
    if len(schedule.description) > MAX_DESCRIPTION_LENGTH:
        return (
            False,
            f"Schedule description exceeds {MAX_DESCRIPTION_LENGTH} characters",
        )

    # Validate routines
    if not schedule.routines:
        return False, "Schedule must have at least one routine"

    if len(schedule.routines) > MAX_ROUTINES_PER_SCHEDULE:
        return (
            False,
            f"Schedule exceeds {MAX_ROUTINES_PER_SCHEDULE} routines",
        )

    # Validate routine ID uniqueness
    valid, error = validate_routine_ids_unique(schedule)
    if not valid:
        return False, error

    # Validate each routine (includes trigger validation)
    for i, routine in enumerate(schedule.routines):
        valid, error = validate_routine(routine)
        if not valid:
            routine_name = routine.name or routine.get_display_name()
            return False, f"Routine {i + 1} ('{routine_name}'): {error}"

    return True, None

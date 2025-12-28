"""
Schedule Schema for Mothbox Visual Scheduler.

Defines the core data structures for the scheduler system using a two-tier model:
- EventPattern: Reusable action sequences with relative timing (embedded in Schedule)
- Schedule: Contains patterns + trigger configuration + date constraints

Single-file storage: Each schedule is a self-contained JSON file with patterns embedded
inline, making schedules portable and easy to export/import between Mothbox units.

Schema Version: 2.0
- PatternAction: action_type, action_name, offset_minutes, parameters, description
- EventPattern: pattern_id, name, actions list, duration_minutes (computed property)
- TimeWindow: start_time, end_time, offsets (supports "sunset", "01:00")
- IntervalTrigger, SolarTrigger, MoonPhaseTrigger, FixedTimeTrigger, SensorTrigger
- Schedule: schedule_id, name, event_patterns (embedded), trigger config, date constraints

Usage:
    from webui.backend.lib.schedule_schema import (
        Schedule,
        EventPattern,
        PatternAction,
        TimeWindow,
        IntervalTrigger,
        validate_schedule,
    )

    # Create a schedule
    action = PatternAction(action_type="gpio", action_name="attract_on")
    pattern = EventPattern(pattern_id="", name="UV Capture", actions=[action])
    window = TimeWindow(start_time="21:00", end_time="05:00")
    trigger = IntervalTrigger(interval_minutes=60, time_window=window)
    schedule = Schedule(
        schedule_id="",
        name="Nightly Survey",
        event_patterns=[pattern],
        trigger_type="interval",
        interval_trigger=trigger,
    )

    # Validate
    valid, error = validate_schedule(schedule)
    if valid:
        data = schedule.to_dict()  # Serialize to JSON

Issue #208 - Scheduler Phase 1: Schedule Schema
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
SCHEDULE_SCHEMA_VERSION: Final[str] = "2.0"
SUPPORTED_VERSIONS: Final[list[str]] = ["2.0"]

# Validation limits
MAX_PATTERN_NAME_LENGTH: Final[int] = 200
MAX_DESCRIPTION_LENGTH: Final[int] = 2000
MAX_ACTIONS_PER_PATTERN: Final[int] = 20
MAX_PATTERNS_PER_SCHEDULE: Final[int] = 10
MAX_OFFSET_MINUTES: Final[int] = 1440  # 24 hours
MAX_INTERVAL_MINUTES: Final[int] = 10080  # 7 days
MIN_INTERVAL_MINUTES: Final[int] = 1
MAX_COOLDOWN_MINUTES: Final[int] = 60
MAX_OFFSET_DAYS: Final[int] = 7

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
class PatternAction:
    """
    A single action within an event pattern.

    Actions use relative offsets from pattern start (t=0), enabling
    coordinated multi-action sequences like:
    - UV_ON at t+0
    - TakePhoto at t+5
    - UV_OFF at t+15

    Attributes:
        action_type: Category ("gpio", "camera", "gps_sync", "service")
        action_name: Specific action (e.g., "attract_on", "takephoto")
        offset_minutes: Minutes from pattern start (t=0). Default 0, max 1440.
        parameters: Action-specific configuration dict
        description: Human-readable description (max 500 chars)

    Example:
        >>> action = PatternAction(
        ...     action_type="gpio",
        ...     action_name="attract_on",
        ...     offset_minutes=0,
        ...     description="Turn on UV attract lights"
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
    def from_dict(cls, data: dict) -> "PatternAction":
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
        actions: Ordered list of PatternAction objects
        category: "built-in" or "user"
        tags: Tags for filtering/search

    Example:
        >>> pattern = EventPattern(
        ...     pattern_id="",
        ...     name="UV Capture Cycle",
        ...     actions=[
        ...         PatternAction(action_type="gpio", action_name="attract_on"),
        ...         PatternAction(action_type="camera", action_name="takephoto", offset_minutes=5),
        ...         PatternAction(action_type="gpio", action_name="attract_off", offset_minutes=15),
        ...     ]
        ... )
        >>> pattern.duration_minutes
        15
    """

    pattern_id: str
    name: str
    description: str = ""
    actions: list[PatternAction] = field(default_factory=list)
    category: str = "user"
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Generate UUID if pattern_id is empty."""
        if not self.pattern_id:
            self.pattern_id = str(uuid.uuid4())

    @property
    def duration_minutes(self) -> int:
        """Total duration = max action offset."""
        if not self.actions:
            return 0
        return max(action.offset_minutes for action in self.actions)

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
            actions=[PatternAction.from_dict(a) for a in data.get("actions", [])],
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
        ...     end_offset_minutes=-30,   # 30 min before sunrise
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
                TimeWindow.from_dict(data["time_window"])
                if data.get("time_window")
                else None
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
                TimeWindow.from_dict(data["time_window"])
                if data.get("time_window")
                else None
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


# =============================================================================
# TIER 2: SCHEDULE
# =============================================================================


@dataclass
class Schedule:
    """
    Complete schedule with embedded event patterns (single-file storage).

    Each schedule is fully self-contained with event patterns embedded inline,
    making it portable and easy to export/import between Mothbox units.

    Attributes:
        schedule_id: Unique identifier (UUID string, auto-generated if empty)
        name: Human-readable name (required, max 200 chars)
        description: Detailed description (max 2000 chars)
        event_patterns: Embedded EventPattern objects (not references)
        trigger_type: Type of trigger ("interval", "solar", "moon_phase", etc.)
        interval_trigger: Config for interval triggers
        solar_trigger: Config for solar triggers
        moon_phase_trigger: Config for moon phase triggers
        fixed_time_trigger: Config for fixed time triggers
        sensor_trigger: Config for sensor triggers
        start_date: Start of schedule validity (ISO 8601 date YYYY-MM-DD)
        end_date: End of schedule validity (ISO 8601 date YYYY-MM-DD)
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
        ...     name="Nightly Moth Survey",
        ...     event_patterns=[...],
        ...     trigger_type="interval",
        ...     interval_trigger=IntervalTrigger(
        ...         interval_minutes=60,
        ...         time_window=TimeWindow(start_time="21:00", end_time="05:00"),
        ...     ),
        ... )
    """

    schedule_id: str
    name: str
    description: str = ""
    event_patterns: list[EventPattern] = field(default_factory=list)
    trigger_type: str = "interval"

    # Trigger configs (one active based on trigger_type)
    interval_trigger: IntervalTrigger | None = None
    solar_trigger: SolarTrigger | None = None
    moon_phase_trigger: MoonPhaseTrigger | None = None
    fixed_time_trigger: FixedTimeTrigger | None = None
    sensor_trigger: SensorTrigger | None = None
    cron_trigger: CronTrigger | None = None

    # Date constraints
    start_date: str | None = None
    end_date: str | None = None

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
        """Total duration of all event patterns combined."""
        return sum(pattern.duration_minutes for pattern in self.event_patterns)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "schema_version": SCHEDULE_SCHEMA_VERSION,
            "schedule_id": self.schedule_id,
            "name": self.name,
            "description": self.description,
            "event_patterns": [p.to_dict() for p in self.event_patterns],
            "trigger_type": self.trigger_type,
            "interval_trigger": (
                self.interval_trigger.to_dict() if self.interval_trigger else None
            ),
            "solar_trigger": (
                self.solar_trigger.to_dict() if self.solar_trigger else None
            ),
            "moon_phase_trigger": (
                self.moon_phase_trigger.to_dict() if self.moon_phase_trigger else None
            ),
            "fixed_time_trigger": (
                self.fixed_time_trigger.to_dict() if self.fixed_time_trigger else None
            ),
            "sensor_trigger": (
                self.sensor_trigger.to_dict() if self.sensor_trigger else None
            ),
            "cron_trigger": (
                self.cron_trigger.to_dict() if self.cron_trigger else None
            ),
            "start_date": self.start_date,
            "end_date": self.end_date,
            "deployment_id": self.deployment_id,
            "create_deployment": self.create_deployment,
            "enabled": self.enabled,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "modified_by": self.modified_by,
        }

    @staticmethod
    def _is_frontend_format(data: dict) -> bool:
        """Detect if data uses frontend JSON format.

        Frontend format has a nested 'trigger' object containing trigger_type and all config.
        Backend format has trigger_type at top level with separate trigger objects.
        """
        return 'trigger' in data and isinstance(data.get('trigger'), dict)

    @staticmethod
    def _parse_interval_trigger_frontend(data: dict) -> IntervalTrigger:
        """Parse frontend interval trigger format.

        Frontend sends:
        - interval_minutes
        - time_window_start, time_window_end (or nested time_window)
        - days_of_week
        """
        # Handle both flat and nested time_window formats
        if 'time_window' in data and isinstance(data['time_window'], dict):
            time_window = TimeWindow.from_dict(data['time_window'])
        else:
            time_window = TimeWindow(
                start_time=data.get('time_window_start', '00:00'),
                end_time=data.get('time_window_end', '23:59'),
                start_offset_minutes=data.get('start_offset_minutes', 0),
                end_offset_minutes=data.get('end_offset_minutes', 0),
            )

        return IntervalTrigger(
            interval_minutes=data['interval_minutes'],
            time_window=time_window,
            days_of_week=data.get('days_of_week'),
        )

    @staticmethod
    def _parse_solar_trigger_frontend(data: dict) -> SolarTrigger:
        """Parse frontend solar trigger format."""
        return SolarTrigger(
            solar_event=data['solar_event'],
            offset_minutes=data.get('offset_minutes', 0),
            days_of_week=data.get('days_of_week'),
        )

    @staticmethod
    def _parse_moon_phase_trigger_frontend(data: dict) -> MoonPhaseTrigger:
        """Parse frontend moon phase trigger format.

        Frontend sends:
        - moon_phase: single string (wrap in list for backend)
        - time_of_day: single time string (convert to time_window)
        - offset_days
        """
        # Wrap single phase in list
        phase = data.get('moon_phase')
        phases = [phase] if isinstance(phase, str) else data.get('phases', [])

        # Convert time_of_day to time_window
        time_window = None
        if 'time_of_day' in data:
            time_of_day = data['time_of_day']
            time_window = TimeWindow(
                start_time=time_of_day,
                end_time=time_of_day,
            )
        elif 'time_window' in data and data['time_window']:
            time_window = TimeWindow.from_dict(data['time_window'])

        return MoonPhaseTrigger(
            phases=phases,
            offset_days=data.get('offset_days', 0),
            time_window=time_window,
        )

    @staticmethod
    def _parse_fixed_time_trigger_frontend(data: dict) -> FixedTimeTrigger:
        """Parse frontend fixed time trigger format.

        Frontend sends:
        - time_of_day (maps to 'time')
        - days_of_week
        """
        return FixedTimeTrigger(
            time=data.get('time_of_day', data.get('time', '00:00')),
            days_of_week=data.get('days_of_week'),
        )

    @staticmethod
    def _parse_sensor_trigger_frontend(data: dict) -> SensorTrigger:
        """Parse frontend sensor trigger format."""
        time_window = None
        if 'time_window' in data and data['time_window']:
            time_window = TimeWindow.from_dict(data['time_window'])

        return SensorTrigger(
            sensor_type=data['sensor_type'],
            threshold=data.get('threshold', 0.0),
            comparison=data.get('comparison', 'gt'),
            cooldown_minutes=data.get('cooldown_minutes', 5),
            time_window=time_window,
        )

    @staticmethod
    def _parse_cron_trigger_frontend(data: dict) -> CronTrigger:
        """Parse frontend cron trigger format."""
        return CronTrigger(
            cron_expression=data['cron_expression'],
        )

    @staticmethod
    def _parse_frontend_trigger(trigger_data: dict) -> dict:
        """Convert frontend trigger format to backend trigger objects.

        Args:
            trigger_data: Frontend trigger object with trigger_type and config

        Returns:
            Dict with trigger_type and corresponding typed trigger object
        """
        trigger_type = trigger_data.get('trigger_type')

        result = {'trigger_type': trigger_type}

        # Parse based on trigger type
        if trigger_type == 'interval':
            result['interval_trigger'] = Schedule._parse_interval_trigger_frontend(trigger_data)
        elif trigger_type == 'solar':
            result['solar_trigger'] = Schedule._parse_solar_trigger_frontend(trigger_data)
        elif trigger_type == 'moon_phase':
            result['moon_phase_trigger'] = Schedule._parse_moon_phase_trigger_frontend(trigger_data)
        elif trigger_type == 'fixed_time':
            result['fixed_time_trigger'] = Schedule._parse_fixed_time_trigger_frontend(trigger_data)
        elif trigger_type == 'sensor':
            result['sensor_trigger'] = Schedule._parse_sensor_trigger_frontend(trigger_data)
        elif trigger_type == 'cron':
            result['cron_trigger'] = Schedule._parse_cron_trigger_frontend(trigger_data)

        return result

    @classmethod
    def _convert_frontend_format(cls, data: dict) -> dict:
        """Convert frontend JSON format to backend format.

        Converts:
        - trigger object → trigger_type + specific trigger objects
        - date_range object → start_date/end_date at top level

        Args:
            data: Frontend format dict

        Returns:
            Backend format dict
        """
        # Create copy to avoid mutating input
        converted = data.copy()

        # Extract and convert trigger
        if 'trigger' in converted:
            trigger_data = converted.pop('trigger')
            trigger_fields = cls._parse_frontend_trigger(trigger_data)
            converted.update(trigger_fields)

        # Unwrap date_range if present
        if 'date_range' in converted:
            date_range = converted.pop('date_range')
            if isinstance(date_range, dict):
                converted['start_date'] = date_range.get('start_date')
                converted['end_date'] = date_range.get('end_date')

        return converted

    @classmethod
    def from_dict(cls, data: dict) -> "Schedule":
        """Create from dictionary. Supports both frontend and backend formats."""
        # Detect and convert frontend format
        if cls._is_frontend_format(data):
            data = cls._convert_frontend_format(data)

        # Helper to handle both dict and object types for triggers
        def _process_trigger(trigger_data, trigger_class):
            if trigger_data is None:
                return None
            # If already an instance, return as-is (from frontend conversion)
            if isinstance(trigger_data, trigger_class):
                return trigger_data
            # Otherwise parse from dict (backend format)
            return trigger_class.from_dict(trigger_data)

        return cls(
            schedule_id=data.get("schedule_id", ""),
            name=data["name"],
            description=data.get("description", ""),
            event_patterns=[
                EventPattern.from_dict(p) for p in data.get("event_patterns", [])
            ],
            trigger_type=data.get("trigger_type", "interval"),
            interval_trigger=_process_trigger(data.get("interval_trigger"), IntervalTrigger),
            solar_trigger=_process_trigger(data.get("solar_trigger"), SolarTrigger),
            moon_phase_trigger=_process_trigger(data.get("moon_phase_trigger"), MoonPhaseTrigger),
            fixed_time_trigger=_process_trigger(data.get("fixed_time_trigger"), FixedTimeTrigger),
            sensor_trigger=_process_trigger(data.get("sensor_trigger"), SensorTrigger),
            cron_trigger=_process_trigger(data.get("cron_trigger"), CronTrigger),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
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


def validate_pattern_action(action: PatternAction) -> tuple[bool, str | None]:
    """
    Validate a single pattern action.

    Args:
        action: PatternAction to validate

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
        valid, error = validate_pattern_action(action)
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
            f"start_offset_minutes {window.start_offset_minutes} exceeds "
            f"+/- {max_offset} minutes",
        )

    if abs(window.end_offset_minutes) > max_offset:
        return (
            False,
            f"end_offset_minutes {window.end_offset_minutes} exceeds "
            f"+/- {max_offset} minutes",
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
            f"Solar trigger offset {trigger.offset_minutes} exceeds "
            f"+/- {max_offset} minutes",
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
                f"Invalid moon phase: '{phase}'. "
                f"Must be one of: {', '.join(MOON_PHASES)}",
            )

    # Validate offset_days
    if abs(trigger.offset_days) > MAX_OFFSET_DAYS:
        return (
            False,
            f"Moon phase offset {trigger.offset_days} exceeds "
            f"+/- {MAX_OFFSET_DAYS} days",
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
            return False, "Cron expression must have exactly 5 fields (minute hour day month weekday)"
        return True, None

    # Use CronEntry.is_valid_expression for thorough validation
    if not CronEntry.is_valid_expression(trigger.cron_expression):
        return False, f"Invalid cron expression: '{trigger.cron_expression}'"

    return True, None


def validate_schedule(schedule: Schedule) -> tuple[bool, str | None]:
    """
    Validate a complete schedule with all embedded patterns.

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

    # Validate event_patterns
    if not schedule.event_patterns:
        return False, "Schedule must have at least one event pattern"

    if len(schedule.event_patterns) > MAX_PATTERNS_PER_SCHEDULE:
        return (
            False,
            f"Schedule exceeds {MAX_PATTERNS_PER_SCHEDULE} event patterns",
        )

    # Validate each pattern
    for pattern in schedule.event_patterns:
        valid, error = validate_event_pattern(pattern)
        if not valid:
            return False, f"Pattern '{pattern.name}': {error}"

    # Validate trigger_type
    if schedule.trigger_type not in TRIGGER_TYPES:
        return (
            False,
            f"Invalid trigger type: '{schedule.trigger_type}'. "
            f"Must be one of: {', '.join(TRIGGER_TYPES)}",
        )

    # Validate corresponding trigger config exists and is valid
    trigger_validators = {
        "interval": (schedule.interval_trigger, validate_interval_trigger),
        "solar": (schedule.solar_trigger, validate_solar_trigger),
        "moon_phase": (schedule.moon_phase_trigger, validate_moon_phase_trigger),
        "fixed_time": (schedule.fixed_time_trigger, validate_fixed_time_trigger),
        "sensor": (schedule.sensor_trigger, validate_sensor_trigger),
        "cron": (schedule.cron_trigger, validate_cron_trigger),
    }

    trigger_config, validator = trigger_validators.get(
        schedule.trigger_type, (None, None)
    )

    if trigger_config is None:
        return (
            False,
            f"Missing {schedule.trigger_type}_trigger configuration "
            f"for trigger_type='{schedule.trigger_type}'",
        )

    valid, error = validator(trigger_config)
    if not valid:
        return False, f"{schedule.trigger_type.title()} trigger: {error}"

    # Validate date constraints
    valid, error = _validate_date_string(schedule.start_date)
    if not valid:
        return False, f"start_date: {error}"

    valid, error = _validate_date_string(schedule.end_date)
    if not valid:
        return False, f"end_date: {error}"

    # If both dates provided, validate start <= end
    if schedule.start_date and schedule.end_date:
        start = datetime.strptime(schedule.start_date, "%Y-%m-%d")
        end = datetime.strptime(schedule.end_date, "%Y-%m-%d")
        if start > end:
            return False, "start_date must be before or equal to end_date"

    return True, None

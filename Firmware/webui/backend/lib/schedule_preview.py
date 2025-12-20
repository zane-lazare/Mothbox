"""
Schedule preview generation library.

Generates execution timelines for schedules, showing:
- Pattern executions with absolute action times
- Moon phase information for calendar display
- Conflicts detected over the preview period

This module builds on schedule_conflict.py for execution generation
and adds action-level expansion plus moon phase data.

Issue #214 - Scheduler Phase 3: Schedule Preview
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Final

from webui.backend.lib.moon_phase import get_moon_phases_for_range
from webui.backend.lib.schedule_conflict import (
    Conflict,
    PatternExecution,
    detect_conflicts,
    generate_pattern_executions,
)
from webui.backend.lib.schedule_schema import (
    EventPattern,
    Schedule,
)

# Optional import for GPS location from controls.txt
try:
    from mothbox_paths import CONTROLS_FILE, get_control_values

    MOTHBOX_PATHS_AVAILABLE = True
except ImportError:
    MOTHBOX_PATHS_AVAILABLE = False
    CONTROLS_FILE = None
    get_control_values = None

# ============================================================================
# Constants
# ============================================================================

# Maximum preview days
MAX_PREVIEW_DAYS: Final[int] = 90
MIN_PREVIEW_DAYS: Final[int] = 1
DEFAULT_PREVIEW_DAYS: Final[int] = 7

# Default location (equator) when GPS unavailable
DEFAULT_LATITUDE: Final[float] = 0.0
DEFAULT_LONGITUDE: Final[float] = 0.0

# Logger
logger = logging.getLogger(__name__)

# Log warning if mothbox_paths not available (after logger is defined)
if not MOTHBOX_PATHS_AVAILABLE:
    logger.warning("mothbox_paths not available, GPS fallback disabled")


# ============================================================================
# Data Structures
# ============================================================================


@dataclass
class ActionExecution:
    """
    A single action within a pattern execution.

    Represents an instantiated action with absolute execution time.

    Attributes:
        time: Absolute execution time
        action_name: Action identifier (e.g., "attract_on", "takephoto")
        action_type: Action category (e.g., "gpio", "camera", "gps_sync", "service")
        offset_minutes: Offset from pattern start
        description: Human-readable description
    """

    time: datetime
    action_name: str
    action_type: str
    offset_minutes: int
    description: str = ""

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "time": self.time.isoformat(),
            "action_name": self.action_name,
            "action_type": self.action_type,
            "offset_minutes": self.offset_minutes,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ActionExecution":
        """Deserialize from dictionary."""
        return cls(
            time=datetime.fromisoformat(data["time"]),
            action_name=data["action_name"],
            action_type=data["action_type"],
            offset_minutes=data["offset_minutes"],
            description=data.get("description", ""),
        )


@dataclass
class PreviewExecution:
    """
    A single pattern execution with expanded actions.

    Wraps PatternExecution from schedule_conflict.py, adding:
    - Expanded action list with absolute times
    - Trigger description for display

    Attributes:
        start_time: When pattern execution begins
        end_time: When pattern execution completes
        pattern_id: Source pattern identifier
        pattern_name: Human-readable pattern name
        trigger_info: Trigger description (e.g., "interval:60m", "sunset+30")
        actions: Expanded actions with absolute times
    """

    start_time: datetime
    end_time: datetime
    pattern_id: str
    pattern_name: str
    trigger_info: str
    actions: list[ActionExecution] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "pattern_id": self.pattern_id,
            "pattern_name": self.pattern_name,
            "trigger_info": self.trigger_info,
            "actions": [a.to_dict() for a in self.actions],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PreviewExecution":
        """Deserialize from dictionary."""
        return cls(
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]),
            pattern_id=data["pattern_id"],
            pattern_name=data["pattern_name"],
            trigger_info=data["trigger_info"],
            actions=[ActionExecution.from_dict(a) for a in data.get("actions", [])],
        )


@dataclass
class PreviewResult:
    """
    Complete preview result for a schedule.

    Contains:
    - All pattern executions with expanded actions
    - Conflicts detected over preview period
    - Moon phases for calendar display
    - Summary statistics
    - Warnings about potential issues

    Attributes:
        schedule_id: Source schedule identifier
        schedule_name: Human-readable schedule name
        preview_start: Preview period start (midnight UTC)
        preview_end: Preview period end (midnight UTC)
        executions: List of pattern executions
        conflicts: List of detected conflicts
        moon_phases: Moon phase by date {ISO date string: phase dict}
        total_actions: Total count of individual actions
        total_executions: Total count of pattern executions
        warnings: List of warning messages (e.g., default location used)
        generated_at: Timestamp when preview was generated
    """

    schedule_id: str
    schedule_name: str
    preview_start: datetime
    preview_end: datetime
    executions: list[PreviewExecution]
    conflicts: list[Conflict]
    moon_phases: dict[str, dict]
    total_actions: int
    total_executions: int
    warnings: list[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "schedule_id": self.schedule_id,
            "schedule_name": self.schedule_name,
            "preview_start": self.preview_start.isoformat(),
            "preview_end": self.preview_end.isoformat(),
            "executions": [e.to_dict() for e in self.executions],
            "conflicts": [c.to_dict() for c in self.conflicts],
            "moon_phases": self.moon_phases,
            "total_actions": self.total_actions,
            "total_executions": self.total_executions,
            "warnings": self.warnings,
            "generated_at": self.generated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PreviewResult":
        """Deserialize from dictionary."""
        return cls(
            schedule_id=data["schedule_id"],
            schedule_name=data["schedule_name"],
            preview_start=datetime.fromisoformat(data["preview_start"]),
            preview_end=datetime.fromisoformat(data["preview_end"]),
            executions=[PreviewExecution.from_dict(e) for e in data.get("executions", [])],
            conflicts=[Conflict.from_dict(c) for c in data.get("conflicts", [])],
            moon_phases=data.get("moon_phases", {}),
            total_actions=data["total_actions"],
            total_executions=data["total_executions"],
            warnings=data.get("warnings", []),
            generated_at=datetime.fromisoformat(data["generated_at"]),
        )


# ============================================================================
# Helper Functions
# ============================================================================


def _get_default_location() -> tuple[float | None, float | None]:
    """
    Get default location from controls.txt GPS data.

    Returns:
        (latitude, longitude) tuple, or (None, None) if GPS unavailable
    """
    if not MOTHBOX_PATHS_AVAILABLE:
        return None, None

    try:
        controls = get_control_values(CONTROLS_FILE)
        lat_str = controls.get("lat", "n/a")
        lon_str = controls.get("lon", "n/a")

        if lat_str != "n/a" and lon_str != "n/a":
            lat = float(lat_str)
            lon = float(lon_str)
            logger.debug(f"Using GPS location from controls.txt: {lat}, {lon}")
            return lat, lon
    except Exception as e:
        logger.warning(f"Could not read GPS coordinates from controls.txt: {e}")

    return None, None


def _get_trigger_info(schedule: Schedule) -> str:
    """
    Generate human-readable trigger description.

    Args:
        schedule: Schedule to describe

    Returns:
        Trigger description string (e.g., "interval:60m", "sunset+30", "moon:full")
    """
    trigger_type = schedule.trigger_type

    if trigger_type == "interval" and schedule.interval_trigger:
        interval = schedule.interval_trigger.interval_minutes
        window = schedule.interval_trigger.time_window
        return f"interval:{interval}m ({window.start_time}-{window.end_time})"

    elif trigger_type == "solar" and schedule.solar_trigger:
        event = schedule.solar_trigger.solar_event
        offset = schedule.solar_trigger.offset_minutes
        if offset > 0:
            return f"{event}+{offset}"
        elif offset < 0:
            return f"{event}{offset}"
        else:
            return event

    elif trigger_type == "moon_phase" and schedule.moon_phase_trigger:
        phases = schedule.moon_phase_trigger.phases
        offset = schedule.moon_phase_trigger.offset_days
        phases_str = ",".join(phases)
        if offset > 0:
            return f"moon:{phases_str}+{offset}d"
        elif offset < 0:
            return f"moon:{phases_str}{offset}d"
        else:
            return f"moon:{phases_str}"

    elif trigger_type == "fixed_time" and schedule.fixed_time_trigger:
        time_str = schedule.fixed_time_trigger.time
        return f"daily:{time_str}"

    elif trigger_type == "sensor" and schedule.sensor_trigger:
        sensor = schedule.sensor_trigger.sensor_type
        return f"sensor:{sensor}"

    return trigger_type


def _expand_actions(
    pattern: EventPattern,
    trigger_time: datetime,
) -> list[ActionExecution]:
    """
    Expand pattern actions to absolute times.

    Args:
        pattern: EventPattern with actions to expand
        trigger_time: Pattern execution start time

    Returns:
        List of ActionExecution with absolute times
    """
    actions = []

    for action in pattern.actions:
        action_time = trigger_time + timedelta(minutes=action.offset_minutes)
        actions.append(
            ActionExecution(
                time=action_time,
                action_name=action.action_name,
                action_type=action.action_type,
                offset_minutes=action.offset_minutes,
                description=action.description,
            )
        )

    # Sort by time
    actions.sort(key=lambda a: a.time)

    return actions


def _convert_execution(
    execution: PatternExecution,
    trigger_info: str,
    pattern_cache: dict[str, EventPattern],
) -> PreviewExecution:
    """
    Convert PatternExecution to PreviewExecution with expanded actions.

    Args:
        execution: PatternExecution from schedule_conflict.py
        trigger_info: Trigger description string
        pattern_cache: Dict mapping pattern_id to EventPattern for O(1) lookup

    Returns:
        PreviewExecution with expanded actions
    """
    # Look up pattern from cache - O(1) instead of O(n) linear search
    pattern = pattern_cache.get(execution.pattern_id)

    actions = []
    if pattern:
        actions = _expand_actions(pattern, execution.start_time)

    return PreviewExecution(
        start_time=execution.start_time,
        end_time=execution.end_time,
        pattern_id=execution.pattern_id,
        pattern_name=execution.pattern_name,
        trigger_info=trigger_info,
        actions=actions,
    )


def _get_moon_phases_dict(start_date: date, end_date: date) -> dict[str, dict]:
    """
    Get moon phases as dictionary keyed by ISO date string.

    Args:
        start_date: Start of range
        end_date: End of range

    Returns:
        Dict mapping ISO date strings to phase info dicts
    """
    phases_list = get_moon_phases_for_range(start_date, end_date)

    return {phase["date"]: phase for phase in phases_list}


# ============================================================================
# Main Preview Function
# ============================================================================


def generate_preview(
    schedule: Schedule,
    days: int = DEFAULT_PREVIEW_DAYS,
    latitude: float | None = None,
    longitude: float | None = None,
    timezone_name: str = "UTC",
) -> PreviewResult:
    """
    Generate execution preview for a schedule.

    Creates a timeline of all pattern executions over the specified period,
    with expanded actions, conflicts, and moon phases.

    Args:
        schedule: Schedule to preview
        days: Number of days to preview (1-90, default 7)
        latitude: Location latitude (uses GPS from controls.txt if None)
        longitude: Location longitude (uses GPS from controls.txt if None)
        timezone_name: Timezone for time resolution

    Returns:
        PreviewResult with executions, conflicts, and moon phases

    Raises:
        ValueError: If days is out of range (1-90)
    """
    # Validate days
    if days < MIN_PREVIEW_DAYS or days > MAX_PREVIEW_DAYS:
        raise ValueError(
            f"Preview days must be between {MIN_PREVIEW_DAYS} and {MAX_PREVIEW_DAYS}, got {days}"
        )

    # Collect warnings for API response
    warnings: list[str] = []

    # Resolve location
    if latitude is None or longitude is None:
        default_lat, default_lon = _get_default_location()
        if latitude is None:
            latitude = default_lat if default_lat is not None else DEFAULT_LATITUDE
        if longitude is None:
            longitude = default_lon if default_lon is not None else DEFAULT_LONGITUDE

        if latitude == DEFAULT_LATITUDE and longitude == DEFAULT_LONGITUDE:
            warning_msg = "Using default location (0, 0). Solar-based triggers may be inaccurate."
            logger.warning(warning_msg)
            warnings.append(warning_msg)

    # Calculate date range
    start_date = date.today()
    end_date = start_date + timedelta(days=days - 1)

    # Generate trigger info once (shared by all executions)
    trigger_info = _get_trigger_info(schedule)

    # Generate pattern executions using schedule_conflict.py
    raw_executions = generate_pattern_executions(
        schedule=schedule,
        start_date=start_date,
        end_date=end_date,
        latitude=latitude,
        longitude=longitude,
        timezone_name=timezone_name,
    )

    # Build pattern cache once - O(n) where n = number of patterns
    pattern_cache = {p.pattern_id: p for p in schedule.event_patterns}

    # Convert to preview executions with expanded actions
    executions = [
        _convert_execution(exec, trigger_info, pattern_cache) for exec in raw_executions
    ]

    # Detect conflicts
    conflict_report = detect_conflicts(
        schedule=schedule,
        preview_days=days,
        latitude=latitude,
        longitude=longitude,
        timezone_name=timezone_name,
    )

    # Get moon phases for the period
    moon_phases = _get_moon_phases_dict(start_date, end_date)

    # Calculate totals
    total_actions = sum(len(e.actions) for e in executions)
    total_executions = len(executions)

    # Build preview start/end as datetimes in the user's timezone, then convert to UTC
    # This ensures consistency when execution times span timezone boundaries
    try:
        import pytz

        tz = pytz.timezone(timezone_name)
        preview_start = tz.localize(datetime.combine(start_date, datetime.min.time())).astimezone(
            UTC
        )
        preview_end = tz.localize(datetime.combine(end_date, datetime.max.time())).astimezone(UTC)
    except (ImportError, Exception):
        # Fallback to UTC if pytz unavailable or timezone invalid
        preview_start = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
        preview_end = datetime.combine(end_date, datetime.max.time(), tzinfo=UTC)

    return PreviewResult(
        schedule_id=schedule.schedule_id,
        schedule_name=schedule.name,
        preview_start=preview_start,
        preview_end=preview_end,
        executions=executions,
        conflicts=conflict_report.conflicts,
        moon_phases=moon_phases,
        total_actions=total_actions,
        total_executions=total_executions,
        warnings=warnings,
    )


# ============================================================================
# Validation Functions
# ============================================================================


def validate_preview_days(days: int) -> tuple[bool, str | None]:
    """
    Validate preview days parameter.

    Args:
        days: Number of days to validate

    Returns:
        (True, None) if valid, (False, error_message) if invalid
    """
    if not isinstance(days, int):
        return False, f"Preview days must be an integer, got {type(days).__name__}"

    if days < MIN_PREVIEW_DAYS:
        return False, f"Preview days must be at least {MIN_PREVIEW_DAYS}, got {days}"

    if days > MAX_PREVIEW_DAYS:
        return False, f"Preview days must be at most {MAX_PREVIEW_DAYS}, got {days}"

    return True, None


def validate_coordinates(
    latitude: float | None,
    longitude: float | None,
) -> tuple[bool, str | None]:
    """
    Validate geographic coordinates.

    Args:
        latitude: Latitude to validate (-90 to 90)
        longitude: Longitude to validate (-180 to 180)

    Returns:
        (True, None) if valid, (False, error_message) if invalid
    """
    if latitude is not None:
        if not isinstance(latitude, (int, float)):
            return False, f"Latitude must be a number, got {type(latitude).__name__}"
        if latitude < -90 or latitude > 90:
            return False, f"Latitude must be between -90 and 90, got {latitude}"

    if longitude is not None:
        if not isinstance(longitude, (int, float)):
            return False, f"Longitude must be a number, got {type(longitude).__name__}"
        if longitude < -180 or longitude > 180:
            return False, f"Longitude must be between -180 and 180, got {longitude}"

    return True, None


def validate_timezone(timezone_name: str) -> tuple[bool, str | None]:
    """
    Validate timezone name parameter.

    Args:
        timezone_name: IANA timezone name to validate (e.g., "America/New_York", "UTC")

    Returns:
        (True, None) if valid, (False, error_message) if invalid
    """
    if not isinstance(timezone_name, str):
        return False, f"Timezone must be a string, got {type(timezone_name).__name__}"

    if not timezone_name:
        return False, "Timezone cannot be empty"

    try:
        import pytz

        pytz.timezone(timezone_name)
        return True, None
    except ImportError:
        return False, "pytz library required for timezone validation"
    except pytz.UnknownTimeZoneError:
        return (
            False,
            f"Invalid timezone '{timezone_name}'. "
            "Use IANA timezone names (e.g., 'America/New_York', 'Europe/London', 'UTC')",
        )


def parse_and_validate_days(days_str: str) -> tuple[int | None, str | None]:
    """
    Parse and validate days parameter from string.

    Args:
        days_str: String representation of days (e.g., "7")

    Returns:
        (days, None) if valid, (None, error_message) if invalid
    """
    try:
        days = int(days_str)
    except ValueError:
        return None, f"Expected integer, got '{days_str}'"

    valid, error = validate_preview_days(days)
    return (days, None) if valid else (None, error)


def parse_and_validate_coordinate(
    value_str: str | None,
    name: str,
) -> tuple[float | None, str | None]:
    """
    Parse a coordinate value from string.

    Args:
        value_str: String representation of coordinate (e.g., "35.5"), or None
        name: Parameter name for error messages (e.g., "lat", "lon")

    Returns:
        (value, None) if valid or None input, (None, error_message) if invalid
    """
    if value_str is None:
        return None, None  # Optional parameter, no error

    try:
        value = float(value_str)
    except ValueError:
        return None, f"Expected number for {name}, got '{value_str}'"

    return value, None  # Range validation done separately via validate_coordinates

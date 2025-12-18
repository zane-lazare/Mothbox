"""
Moon phase calculations using the astral library.

Provides moon phase detection, moonrise/moonset times, and phase searching
for scheduling triggers based on lunar conditions.

External dependency: astral>=3.2

Issue #210 - Scheduler Phase 2: Moon Phase Calculator

Usage:
    >>> from datetime import date
    >>> from webui.backend.lib.moon_phase import get_moon_phase, next_moon_phase
    >>>
    >>> # Get current moon phase
    >>> phase = get_moon_phase(date.today())
    >>> print(f"Phase: {phase['phase_name']}, Illumination: {phase['illumination']:.0%}")
    Phase: Waxing Gibbous, Illumination: 75%
    >>>
    >>> # Find next full moon
    >>> full_date = next_moon_phase("full", date.today())
    >>> print(f"Next full moon: {full_date}")
    Next full moon: 2024-01-25
"""

import contextlib
import math
from datetime import date, timedelta
from typing import Final

from astral import LocationInfo, moon
from astral.moon import moonrise, moonset

# =============================================================================
# CONSTANTS
# =============================================================================

# Phase value ranges (astral returns 0-27.99)
# 0 = new moon, ~7 = first quarter, ~14 = full moon, ~21 = last quarter
PHASE_RANGES: Final[list[tuple[str, float, float]]] = [
    ("new", 0.0, 1.85),
    ("waxing_crescent", 1.85, 7.38),
    ("first_quarter", 7.38, 11.07),
    ("waxing_gibbous", 11.07, 14.77),
    ("full", 14.77, 18.46),
    ("waning_gibbous", 18.46, 22.15),
    ("last_quarter", 22.15, 25.84),
    ("waning_crescent", 25.84, 28.0),
]

# All 8 moon phases (aligned with schedule_schema.py MOON_PHASES)
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

# Human-readable phase names
PHASE_NAMES: Final[dict[str, str]] = {
    "new": "New Moon",
    "waxing_crescent": "Waxing Crescent",
    "first_quarter": "First Quarter",
    "waxing_gibbous": "Waxing Gibbous",
    "full": "Full Moon",
    "waning_gibbous": "Waning Gibbous",
    "last_quarter": "Last Quarter",
    "waning_crescent": "Waning Crescent",
}

# Maximum offset days allowed for phase matching
MAX_OFFSET_DAYS: Final[int] = 7

# Maximum days to search for next phase
# Set to ~2 lunar cycles (29.53 days each) to guarantee finding any phase.
# A specific phase occurs once per cycle, so 2 cycles ensures we find it
# even if we start just after that phase occurred.
MAX_SEARCH_DAYS: Final[int] = 60


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _phase_value_to_name(phase_value: float) -> str:
    """
    Convert astral phase value (0-27.99) to phase name.

    Args:
        phase_value: Astral moon.phase() return value (0-27.99)

    Returns:
        Phase name string (e.g., "full", "new", "waxing_crescent")
    """
    # Normalize phase value using modulo to handle wrap-around at 28.0
    # This ensures values like 28.0, 28.5, or negative values are handled correctly
    normalized = phase_value % 28.0

    for phase_name, start, end in PHASE_RANGES:
        if start <= normalized < end:
            return phase_name

    # Fallback for edge case at exactly 0.0 after modulo
    return "new"


# Astral library phase value range (0 to ~28)
ASTRAL_PHASE_CYCLE: Final[float] = 28.0


def _calculate_illumination(phase_value: float) -> float:
    """
    Calculate moon illumination fraction from phase value.

    The astral library returns phase values in the range 0-27.99,
    representing a full lunar cycle. The illumination follows a
    sinusoidal curve:
    - 0 at new moon (phase_value = 0)
    - 1 at full moon (phase_value ≈ 14)
    - 0 at new moon again (phase_value ≈ 28)

    Args:
        phase_value: Astral phase value (0-27.99), representing position
                     in the lunar cycle

    Returns:
        Illumination as float (0.0 to 1.0)
    """
    # Convert phase value to radians using astral's 28-day scale
    # This ensures the full cycle maps to 0-2π correctly
    phase_angle = 2 * math.pi * phase_value / ASTRAL_PHASE_CYCLE
    # Illumination follows cosine curve:
    # At new moon (0): cos(0) = 1, so (1-1)/2 = 0
    # At full moon (~14): cos(pi) = -1, so (1-(-1))/2 = 1
    illumination = (1 - math.cos(phase_angle)) / 2
    return round(illumination, 3)


# =============================================================================
# PUBLIC FUNCTIONS
# =============================================================================


def validate_phase_name(phase: str) -> tuple[bool, str | None]:
    """
    Validate a moon phase name.

    Args:
        phase: Phase name to validate

    Returns:
        Tuple of (is_valid, error_message):
        - is_valid: True if valid, False otherwise
        - error_message: None if valid, error description if invalid

    Example:
        >>> validate_phase_name("full")
        (True, None)
        >>> validate_phase_name("half")
        (False, "Invalid phase 'half'. Must be one of: new, waxing_crescent, ...")
    """
    if phase not in MOON_PHASES:
        valid_phases = ", ".join(MOON_PHASES)
        return False, f"Invalid phase '{phase}'. Must be one of: {valid_phases}"
    return True, None


def get_moon_phase(target_date: date) -> dict:
    """
    Get moon phase information for a specific date.

    Uses the astral library to calculate lunar phase based on astronomical
    algorithms. Accuracy is typically within 1 day of actual phase.

    Args:
        target_date: The date to get moon phase for (datetime.date)

    Returns:
        Dict with:
        - date: ISO 8601 date string (YYYY-MM-DD)
        - phase: str (e.g., "full", "new", "first_quarter")
        - phase_name: Human-readable name (e.g., "Full Moon")
        - phase_value: float (0-27.99, astral raw value)
        - illumination: float (0.0 to 1.0, approximate percentage)

    Example:
        >>> from datetime import date
        >>> result = get_moon_phase(date(2024, 1, 25))
        >>> result['phase']
        'full'
        >>> result['illumination']
        0.998
    """
    # Get astral phase value (0-27.99)
    phase_value = moon.phase(target_date)

    # Determine phase name from ranges
    phase = _phase_value_to_name(phase_value)

    # Calculate illumination
    illumination = _calculate_illumination(phase_value)

    return {
        "date": target_date.isoformat(),
        "phase": phase,
        "phase_name": PHASE_NAMES[phase],
        "phase_value": round(phase_value, 2),
        "illumination": illumination,
    }


def get_moon_times(
    target_date: date,
    latitude: float,
    longitude: float,
    timezone_name: str = "UTC",
) -> dict:
    """
    Get moonrise and moonset times for a location.

    Note: Near the poles or on certain dates, the moon may not rise or set.
    In these cases, moonrise and/or moonset will be None.

    Args:
        target_date: The date to calculate for
        latitude: Observer latitude (-90 to 90)
        longitude: Observer longitude (-180 to 180)
        timezone_name: Timezone name (e.g., "America/New_York", default "UTC")

    Returns:
        Dict with:
        - date: ISO 8601 date string
        - moonrise: ISO 8601 datetime string or None if moon doesn't rise
        - moonset: ISO 8601 datetime string or None if moon doesn't set

    Raises:
        ValueError: If coordinates are invalid

    Example:
        >>> from datetime import date
        >>> result = get_moon_times(date(2024, 6, 15), 35.96, -83.92, "America/New_York")
        >>> result['moonrise']
        '2024-06-15T21:34:00-04:00'
    """
    # Validate coordinates
    if not -90 <= latitude <= 90:
        raise ValueError(f"Invalid latitude {latitude}. Must be between -90 and 90.")
    if not -180 <= longitude <= 180:
        raise ValueError(
            f"Invalid longitude {longitude}. Must be between -180 and 180."
        )

    # Create location
    location = LocationInfo(
        name="Observer",
        region="",
        timezone=timezone_name,
        latitude=latitude,
        longitude=longitude,
    )

    rise_time = None
    set_time = None

    with contextlib.suppress(ValueError):
        # Moon may not rise on this date at this location (e.g., polar regions)
        rise_time = moonrise(location.observer, target_date, tzinfo=location.timezone)

    with contextlib.suppress(ValueError):
        # Moon may not set on this date at this location (e.g., polar regions)
        set_time = moonset(location.observer, target_date, tzinfo=location.timezone)

    return {
        "date": target_date.isoformat(),
        "moonrise": rise_time.isoformat() if rise_time else None,
        "moonset": set_time.isoformat() if set_time else None,
    }


def get_moon_phases_for_range(start_date: date, end_date: date) -> list[dict]:
    """
    Get moon phases for a date range.

    Returns phase information for each day in the range, useful for
    calendar displays or batch processing.

    Args:
        start_date: Start of range (inclusive)
        end_date: End of range (inclusive)

    Returns:
        List of moon phase dicts for each day (same format as get_moon_phase)

    Raises:
        ValueError: If start_date > end_date

    Example:
        >>> from datetime import date
        >>> phases = get_moon_phases_for_range(date(2024, 6, 1), date(2024, 6, 7))
        >>> len(phases)
        7
    """
    if start_date > end_date:
        raise ValueError(
            f"start_date ({start_date}) must be before or equal to end_date ({end_date})"
        )

    phases = []
    current = start_date
    while current <= end_date:
        phases.append(get_moon_phase(current))
        current += timedelta(days=1)

    return phases


def get_significant_phases_for_range(start_date: date, end_date: date) -> list[dict]:
    """
    Get only significant moon phases (new, first_quarter, full, last_quarter).

    Returns dates where major phase transitions occur, useful for
    calendar/UI display of significant lunar events.

    Args:
        start_date: Start of range (inclusive)
        end_date: End of range (inclusive)

    Returns:
        List of significant phase events (phase transitions only)

    Example:
        >>> from datetime import date
        >>> phases = get_significant_phases_for_range(date(2024, 6, 1), date(2024, 6, 30))
        >>> [p['phase'] for p in phases]
        ['first_quarter', 'full', 'last_quarter', 'new']
    """
    significant = {"new", "first_quarter", "full", "last_quarter"}
    all_phases = get_moon_phases_for_range(start_date, end_date)

    result = []
    prev_phase = None

    for phase_info in all_phases:
        phase = phase_info["phase"]
        # Include only significant phases, and only when phase changes
        if phase in significant and phase != prev_phase:
            result.append(phase_info)
        prev_phase = phase

    return result


def next_moon_phase(target_phase: str, from_date: date) -> date:
    """
    Find the next occurrence of a specific moon phase.

    Searches forward from the given date to find when the target phase
    next occurs. If the current date is already the target phase, returns
    that date.

    Args:
        target_phase: The phase to find ("full", "new", etc.)
        from_date: Start searching from this date

    Returns:
        Date of next occurrence of the target phase

    Raises:
        ValueError: If target_phase is not a valid phase name

    Example:
        >>> from datetime import date
        >>> next_moon_phase("full", date(2024, 6, 1))
        datetime.date(2024, 6, 22)
    """
    valid, error = validate_phase_name(target_phase)
    if not valid:
        raise ValueError(error)

    current = from_date

    for _ in range(MAX_SEARCH_DAYS):
        phase_info = get_moon_phase(current)
        if phase_info["phase"] == target_phase:
            return current
        current += timedelta(days=1)

    # Fallback (should never reach here for valid lunar calculations)
    return from_date + timedelta(days=30)


def is_within_moon_phase(
    target_date: date,
    target_phase: str,
    offset_days: int = 0,
) -> bool:
    """
    Check if a date is within range of a moon phase.

    Used by MoonPhaseTrigger to determine if a schedule should run.
    With offset_days=0, only the exact phase date matches.
    With offset_days=N, dates within ±N days of the phase also match.

    Args:
        target_date: Date to check
        target_phase: Phase to match ("full", "new", etc.)
        offset_days: +/- days from exact phase (default 0, max 7)

    Returns:
        True if date matches criteria

    Raises:
        ValueError: If target_phase is invalid or offset_days > 7

    Example:
        >>> from datetime import date
        >>> # Full moon is on June 22, 2024
        >>> is_within_moon_phase(date(2024, 6, 20), "full", offset_days=2)
        True
    """
    valid, error = validate_phase_name(target_phase)
    if not valid:
        raise ValueError(error)

    if offset_days < 0 or offset_days > MAX_OFFSET_DAYS:
        raise ValueError(
            f"offset_days must be between 0 and {MAX_OFFSET_DAYS}, got {offset_days}"
        )

    # Simple case: no offset
    if offset_days == 0:
        return get_moon_phase(target_date)["phase"] == target_phase

    # Check range around target date
    for delta in range(-offset_days, offset_days + 1):
        check_date = target_date + timedelta(days=delta)
        if get_moon_phase(check_date)["phase"] == target_phase:
            return True

    return False

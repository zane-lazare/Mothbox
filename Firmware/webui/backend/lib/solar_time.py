"""
Solar time calculations using the astral library.

Provides sun times, twilight times, golden hour, blue hour, and time specification
parsing for scheduling triggers based on solar conditions.

External dependency: astral>=3.2

Issue #211 - Scheduler Phase 2: Solar Time Calculator

Golden Hour / Blue Hour Notes:
    The time specification events "golden_hour_start", "golden_hour_end",
    "blue_hour_start", and "blue_hour_end" refer to EVENING periods only,
    as these are the more commonly used times for moth photography scheduling.

    For morning golden/blue hour times, use the get_golden_hour() and
    get_blue_hour() functions directly, which return both morning and evening
    times in their result dictionaries.

    Example accessing morning golden hour:
        >>> golden = get_golden_hour(date.today(), 35.96, -83.92, "America/New_York")
        >>> morning_start = golden["morning_start"]
        >>> morning_end = golden["morning_end"]

Usage:
    >>> from datetime import date
    >>> from webui.backend.lib.solar_time import get_sun_times, parse_time_spec
    >>>
    >>> # Get sun times for a location
    >>> times = get_sun_times(date.today(), 35.96, -83.92, "America/New_York")
    >>> print(f"Sunrise: {times['sunrise']}, Sunset: {times['sunset']}")
    Sunrise: 2024-06-15T06:23:00-04:00, Sunset: 2024-06-15T20:45:00-04:00
    >>>
    >>> # Parse time specification with offset
    >>> sunset_time = parse_time_spec("sunset+30", date.today(), 35.96, -83.92)
    >>> print(f"30 minutes after sunset: {sunset_time}")
    30 minutes after sunset: 2024-06-15T21:15:00-04:00
"""

import contextlib
import re
from datetime import date, datetime, time, timedelta
from typing import Final

import pytz
from astral import LocationInfo, SunDirection
from astral.sun import blue_hour, golden_hour, sun, time_at_elevation

# =============================================================================
# CONSTANTS
# =============================================================================

# Solar events (aligned with schedule_schema.py SOLAR_EVENTS)
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

# Twilight types (depression angles)
TWILIGHT_TYPES: Final[list[str]] = ["civil", "nautical", "astronomical"]

# Depression angles for twilight calculations
TWILIGHT_DEPRESSION: Final[dict[str, float]] = {
    "civil": 6.0,
    "nautical": 12.0,
    "astronomical": 18.0,
}

# Time specification pattern (solar event with optional offset)
# Matches: "sunset", "sunset+30", "sunrise-15", "astronomical_dusk", etc.
TIME_SPEC_PATTERN = re.compile(
    r"^(dawn|sunrise|noon|sunset|dusk|"
    r"civil_dawn|civil_dusk|"
    r"nautical_dawn|nautical_dusk|"
    r"astronomical_dawn|astronomical_dusk|"
    r"golden_hour_start|golden_hour_end|"
    r"blue_hour_start|blue_hour_end)"
    r"([+-]\d+)?$"
)

# Absolute time pattern (HH:MM format)
ABSOLUTE_TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _validate_coordinates(latitude: float, longitude: float) -> None:
    """
    Validate latitude and longitude coordinates.

    Args:
        latitude: Observer latitude (-90 to 90)
        longitude: Observer longitude (-180 to 180)

    Raises:
        ValueError: If coordinates are invalid
    """
    if not -90 <= latitude <= 90:
        raise ValueError(f"Invalid latitude {latitude}. Must be between -90 and 90.")
    if not -180 <= longitude <= 180:
        raise ValueError(
            f"Invalid longitude {longitude}. Must be between -180 and 180."
        )


def _create_location(
    latitude: float, longitude: float, timezone_name: str
) -> LocationInfo:
    """
    Create LocationInfo object for astral calculations.

    Args:
        latitude: Observer latitude
        longitude: Observer longitude
        timezone_name: Timezone name (e.g., "America/New_York")

    Returns:
        LocationInfo object configured for the observer location
    """
    return LocationInfo(
        name="Observer",
        region="",
        timezone=timezone_name,
        latitude=latitude,
        longitude=longitude,
    )


def _get_sun_event_time(
    event_name: str,
    target_date: date,
    latitude: float,
    longitude: float,
    timezone_name: str,
) -> datetime | None:
    """
    Get datetime for a specific solar event.

    Args:
        event_name: Solar event name (e.g., "sunset", "civil_dawn")
        target_date: The date to calculate for
        latitude: Observer latitude
        longitude: Observer longitude
        timezone_name: Timezone name

    Returns:
        Datetime for the event, or None if event doesn't occur

    Raises:
        ValueError: If event_name is invalid
    """
    _validate_coordinates(latitude, longitude)
    location = _create_location(latitude, longitude, timezone_name)

    # Get basic sun times
    sun_times = None
    with contextlib.suppress(ValueError):
        sun_times = sun(location.observer, target_date, tzinfo=location.timezone)

    # Handle basic sun events
    if event_name in ["dawn", "sunrise", "noon", "sunset", "dusk"]:
        if sun_times is None:
            return None
        return sun_times.get(event_name)

    # Handle twilight events
    twilight_mapping = {
        "civil_dawn": ("civil", "morning"),
        "civil_dusk": ("civil", "evening"),
        "nautical_dawn": ("nautical", "morning"),
        "nautical_dusk": ("nautical", "evening"),
        "astronomical_dawn": ("astronomical", "morning"),
        "astronomical_dusk": ("astronomical", "evening"),
    }

    if event_name in twilight_mapping:
        twilight_type, period = twilight_mapping[event_name]
        twilight_times = get_twilight_times(
            target_date, latitude, longitude, twilight_type, timezone_name
        )
        return (
            datetime.fromisoformat(twilight_times[period])
            if twilight_times[period]
            else None
        )

    # Handle golden hour events
    # Note: golden_hour_start/end refer to EVENING golden hour only.
    # This is intentional for scheduler use case (moth photography occurs at dusk).
    # For morning golden hour, use get_golden_hour() directly.
    if event_name in ["golden_hour_start", "golden_hour_end"]:
        location = _create_location(latitude, longitude, timezone_name)

        # Evening golden hour (SETTING)
        with contextlib.suppress(ValueError):
            evening_result = golden_hour(
                location.observer,
                target_date,
                direction=SunDirection.SETTING,
                tzinfo=location.timezone,
            )
            if evening_result:
                if isinstance(evening_result, tuple) and len(evening_result) >= 2:
                    if event_name == "golden_hour_start":
                        return evening_result[0]
                    else:  # golden_hour_end
                        return evening_result[1]
                else:
                    # Single datetime value
                    return evening_result if event_name == "golden_hour_start" else None

        return None

    # Handle blue hour events
    # Note: blue_hour_start/end refer to EVENING blue hour only.
    # This is intentional for scheduler use case (moth photography occurs at dusk).
    # For morning blue hour, use get_blue_hour() directly.
    if event_name in ["blue_hour_start", "blue_hour_end"]:
        location = _create_location(latitude, longitude, timezone_name)

        # Evening blue hour (SETTING)
        with contextlib.suppress(ValueError):
            evening_result = blue_hour(
                location.observer,
                target_date,
                direction=SunDirection.SETTING,
                tzinfo=location.timezone,
            )
            if evening_result:
                if isinstance(evening_result, tuple) and len(evening_result) >= 2:
                    if event_name == "blue_hour_start":
                        return evening_result[0]
                    else:  # blue_hour_end
                        return evening_result[1]
                else:
                    # Single datetime value
                    return evening_result if event_name == "blue_hour_start" else None

        return None

    raise ValueError(f"Unknown solar event: {event_name}")


# =============================================================================
# PUBLIC FUNCTIONS
# =============================================================================


def validate_solar_event(
    event: str,
    latitude: float,
    longitude: float,
    timezone_name: str = "UTC",
) -> tuple[bool, str | None]:
    """
    Validate a solar event name and location.

    Args:
        event: Event name to validate (e.g., "sunset", "civil_dawn")
        latitude: Observer latitude (-90 to 90)
        longitude: Observer longitude (-180 to 180)
        timezone_name: Timezone name (default "UTC")

    Returns:
        Tuple of (is_valid, error_message):
        - is_valid: True if valid, False otherwise
        - error_message: None if valid, error description if invalid

    Raises:
        ValueError: If coordinates are invalid

    Example:
        >>> validate_solar_event("sunset", 35.96, -83.92, "America/New_York")
        (True, None)
        >>> validate_solar_event("invalid", 35.96, -83.92)
        (False, "Invalid event 'invalid'. Must be one of: dawn, sunrise, ...")
    """
    # Validate coordinates first (raises ValueError if invalid)
    _validate_coordinates(latitude, longitude)

    # Validate event name
    if event not in SOLAR_EVENTS:
        valid_events = ", ".join(SOLAR_EVENTS)
        return False, f"Invalid event '{event}'. Must be one of: {valid_events}"

    return True, None


def get_sun_times(
    target_date: date,
    latitude: float,
    longitude: float,
    timezone_name: str = "UTC",
) -> dict:
    """
    Get basic sun times for a location.

    Uses the astral library to calculate dawn, sunrise, noon, sunset, and dusk
    based on astronomical algorithms. Accuracy is typically within 1-2 minutes.

    Args:
        target_date: The date to calculate for (datetime.date)
        latitude: Observer latitude (-90 to 90)
        longitude: Observer longitude (-180 to 180)
        timezone_name: Timezone name (e.g., "America/New_York", default "UTC")

    Returns:
        Dict with:
        - date: ISO 8601 date string (YYYY-MM-DD)
        - dawn: ISO 8601 datetime string or None if sun doesn't set
        - sunrise: ISO 8601 datetime string or None
        - noon: ISO 8601 datetime string or None
        - sunset: ISO 8601 datetime string or None
        - dusk: ISO 8601 datetime string or None
        - status: "normal", "polar_day" (midnight sun), or "polar_night"

    Raises:
        ValueError: If coordinates are invalid

    Note:
        In polar regions during midnight sun or polar night, some times may be None.
        The status field indicates the condition:
        - "normal": All sun events occur normally
        - "polar_day": Sun doesn't set (midnight sun)
        - "polar_night": Sun doesn't rise (polar night)

    Example:
        >>> from datetime import date
        >>> result = get_sun_times(date(2024, 6, 15), 35.96, -83.92, "America/New_York")
        >>> result['sunrise']
        '2024-06-15T06:23:00-04:00'
        >>> result['status']
        'normal'
    """
    _validate_coordinates(latitude, longitude)
    location = _create_location(latitude, longitude, timezone_name)

    # Get sun times (may raise ValueError for polar regions)
    sun_times = None
    with contextlib.suppress(ValueError):
        sun_times = sun(location.observer, target_date, tzinfo=location.timezone)

    # Extract times, converting to ISO 8601 strings
    result = {
        "date": target_date.isoformat(),
        "dawn": None,
        "sunrise": None,
        "noon": None,
        "sunset": None,
        "dusk": None,
        "status": "normal",
    }

    if sun_times:
        for key in ["dawn", "sunrise", "noon", "sunset", "dusk"]:
            if key in sun_times and sun_times[key]:
                result[key] = sun_times[key].isoformat()

        # Determine polar status based on which events are missing
        has_sunrise = result["sunrise"] is not None
        has_sunset = result["sunset"] is not None

        if not has_sunrise and not has_sunset:
            # Neither sunrise nor sunset - need to check if sun is always up or down
            # If noon exists and is during daytime, it's polar day
            result["status"] = "polar_day" if result["noon"] else "polar_night"
        elif has_sunrise and not has_sunset:
            result["status"] = "polar_day"  # Sun rises but doesn't set
        elif has_sunset and not has_sunrise:
            result["status"] = "polar_night"  # Sun sets but doesn't rise
    else:
        # No sun times at all - polar condition
        # Check latitude to determine if it's polar day or night
        # In summer (Jun-Aug in N hemisphere, Dec-Feb in S), high latitudes have polar day
        month = target_date.month
        is_northern_summer = month in [5, 6, 7, 8]
        is_northern = latitude > 0

        if (is_northern and is_northern_summer) or (not is_northern and not is_northern_summer):
            result["status"] = "polar_day"
        else:
            result["status"] = "polar_night"

    return result


def get_twilight_times(
    target_date: date,
    latitude: float,
    longitude: float,
    twilight_type: str = "civil",
    timezone_name: str = "UTC",
) -> dict:
    """
    Get twilight times for a location.

    Calculates morning and evening twilight periods based on sun depression angle:
    - Civil: 6° below horizon (bright enough to see without artificial light)
    - Nautical: 12° below horizon (horizon still visible at sea)
    - Astronomical: 18° below horizon (sky completely dark for astronomy)

    Args:
        target_date: The date to calculate for
        latitude: Observer latitude (-90 to 90)
        longitude: Observer longitude (-180 to 180)
        twilight_type: Type of twilight ("civil", "nautical", "astronomical")
        timezone_name: Timezone name (default "UTC")

    Returns:
        Dict with:
        - date: ISO 8601 date string
        - twilight_type: The twilight type used
        - morning: ISO 8601 datetime string or None (twilight end, sunrise start)
        - evening: ISO 8601 datetime string or None (sunset end, twilight start)
        - status: "normal", "polar_day" (midnight sun), or "polar_night"

    Raises:
        ValueError: If coordinates or twilight_type are invalid

    Note:
        In polar regions, twilight may not occur on some days. The status field
        indicates the polar condition when times are None.

    Example:
        >>> from datetime import date
        >>> result = get_twilight_times(
        ...     date(2024, 6, 15), 35.96, -83.92, "civil", "America/New_York"
        ... )
        >>> result['morning']
        '2024-06-15T05:50:00-04:00'
        >>> result['status']
        'normal'
    """
    _validate_coordinates(latitude, longitude)

    if twilight_type not in TWILIGHT_TYPES:
        valid_types = ", ".join(TWILIGHT_TYPES)
        raise ValueError(
            f"Invalid twilight type '{twilight_type}'. Must be one of: {valid_types}"
        )

    location = _create_location(latitude, longitude, timezone_name)
    depression = TWILIGHT_DEPRESSION[twilight_type]

    morning_time = None
    evening_time = None

    # Morning twilight end (sun at -depression degrees, rising)
    with contextlib.suppress(ValueError):
        morning_time = time_at_elevation(
            location.observer,
            -depression,
            target_date,
            direction=SunDirection.RISING,
            tzinfo=location.timezone,
        )

    # Evening twilight start (sun at -depression degrees, setting)
    with contextlib.suppress(ValueError):
        evening_time = time_at_elevation(
            location.observer,
            -depression,
            target_date,
            direction=SunDirection.SETTING,
            tzinfo=location.timezone,
        )

    # Determine polar status
    status = "normal"
    if morning_time is None or evening_time is None:
        # Check if we're in polar day or polar night
        month = target_date.month
        is_northern_summer = month in [5, 6, 7, 8]
        is_northern = latitude > 0

        if (is_northern and is_northern_summer) or (not is_northern and not is_northern_summer):
            status = "polar_day"
        else:
            status = "polar_night"

    return {
        "date": target_date.isoformat(),
        "twilight_type": twilight_type,
        "morning": morning_time.isoformat() if morning_time else None,
        "evening": evening_time.isoformat() if evening_time else None,
        "status": status,
    }


def get_golden_hour(
    target_date: date,
    latitude: float,
    longitude: float,
    timezone_name: str = "UTC",
) -> dict:
    """
    Get golden hour times for a location.

    The golden hour is the period shortly after sunrise or before sunset when
    the sun is low on the horizon, producing soft, warm, golden-colored light
    ideal for photography.

    Args:
        target_date: The date to calculate for
        latitude: Observer latitude (-90 to 90)
        longitude: Observer longitude (-180 to 180)
        timezone_name: Timezone name (default "UTC")

    Returns:
        Dict with:
        - date: ISO 8601 date string
        - morning_start: ISO 8601 datetime string or None
        - morning_end: ISO 8601 datetime string or None
        - evening_start: ISO 8601 datetime string or None
        - evening_end: ISO 8601 datetime string or None
        - status: "normal", "polar_day" (midnight sun), or "polar_night"

    Raises:
        ValueError: If coordinates are invalid

    Note:
        In polar regions, golden hour may not occur on some days. The status
        field indicates the polar condition when times are None.

    Example:
        >>> from datetime import date
        >>> result = get_golden_hour(date(2024, 6, 15), 35.96, -83.92, "America/New_York")
        >>> result['evening_start']
        '2024-06-15T19:45:00-04:00'
        >>> result['status']
        'normal'
    """
    _validate_coordinates(latitude, longitude)
    location = _create_location(latitude, longitude, timezone_name)

    morning_start = None
    morning_end = None
    evening_start = None
    evening_end = None

    # Morning golden hour (RISING)
    with contextlib.suppress(ValueError):
        morning_result = golden_hour(
            location.observer,
            target_date,
            direction=SunDirection.RISING,
            tzinfo=location.timezone,
        )
        if morning_result:
            if isinstance(morning_result, tuple) and len(morning_result) >= 2:
                morning_start = morning_result[0]
                morning_end = morning_result[1]
            else:
                # Single datetime value
                morning_start = morning_result

    # Evening golden hour (SETTING)
    with contextlib.suppress(ValueError):
        evening_result = golden_hour(
            location.observer,
            target_date,
            direction=SunDirection.SETTING,
            tzinfo=location.timezone,
        )
        if evening_result:
            if isinstance(evening_result, tuple) and len(evening_result) >= 2:
                evening_start = evening_result[0]
                evening_end = evening_result[1]
            else:
                # Single datetime value
                evening_start = evening_result

    # Determine polar status
    status = "normal"
    all_none = (morning_start is None and morning_end is None and
                evening_start is None and evening_end is None)
    if all_none:
        # Check if we're in polar day or polar night
        month = target_date.month
        is_northern_summer = month in [5, 6, 7, 8]
        is_northern = latitude > 0

        if (is_northern and is_northern_summer) or (not is_northern and not is_northern_summer):
            status = "polar_day"
        else:
            status = "polar_night"

    return {
        "date": target_date.isoformat(),
        "morning_start": morning_start.isoformat() if morning_start else None,
        "morning_end": morning_end.isoformat() if morning_end else None,
        "evening_start": evening_start.isoformat() if evening_start else None,
        "evening_end": evening_end.isoformat() if evening_end else None,
        "status": status,
    }


def get_blue_hour(
    target_date: date,
    latitude: float,
    longitude: float,
    timezone_name: str = "UTC",
) -> dict:
    """
    Get blue hour times for a location.

    The blue hour is the period of twilight when the sun is significantly below
    the horizon and indirect sunlight takes on a predominantly blue hue. This
    occurs before sunrise and after sunset.

    Args:
        target_date: The date to calculate for
        latitude: Observer latitude (-90 to 90)
        longitude: Observer longitude (-180 to 180)
        timezone_name: Timezone name (default "UTC")

    Returns:
        Dict with:
        - date: ISO 8601 date string
        - morning_start: ISO 8601 datetime string or None
        - morning_end: ISO 8601 datetime string or None
        - evening_start: ISO 8601 datetime string or None
        - evening_end: ISO 8601 datetime string or None
        - status: "normal", "polar_day" (midnight sun), or "polar_night"

    Raises:
        ValueError: If coordinates are invalid

    Note:
        In polar regions, blue hour may not occur on some days. The status
        field indicates the polar condition when times are None.

    Example:
        >>> from datetime import date
        >>> result = get_blue_hour(date(2024, 6, 15), 35.96, -83.92, "America/New_York")
        >>> result['evening_start']
        '2024-06-15T20:45:00-04:00'
        >>> result['status']
        'normal'
    """
    _validate_coordinates(latitude, longitude)
    location = _create_location(latitude, longitude, timezone_name)

    morning_start = None
    morning_end = None
    evening_start = None
    evening_end = None

    # Morning blue hour (RISING)
    with contextlib.suppress(ValueError):
        morning_result = blue_hour(
            location.observer,
            target_date,
            direction=SunDirection.RISING,
            tzinfo=location.timezone,
        )
        if morning_result:
            if isinstance(morning_result, tuple) and len(morning_result) >= 2:
                morning_start = morning_result[0]
                morning_end = morning_result[1]
            else:
                # Single datetime value
                morning_start = morning_result

    # Evening blue hour (SETTING)
    with contextlib.suppress(ValueError):
        evening_result = blue_hour(
            location.observer,
            target_date,
            direction=SunDirection.SETTING,
            tzinfo=location.timezone,
        )
        if evening_result:
            if isinstance(evening_result, tuple) and len(evening_result) >= 2:
                evening_start = evening_result[0]
                evening_end = evening_result[1]
            else:
                # Single datetime value
                evening_start = evening_result

    # Determine polar status
    status = "normal"
    all_none = (morning_start is None and morning_end is None and
                evening_start is None and evening_end is None)
    if all_none:
        # Check if we're in polar day or polar night
        month = target_date.month
        is_northern_summer = month in [5, 6, 7, 8]
        is_northern = latitude > 0

        if (is_northern and is_northern_summer) or (not is_northern and not is_northern_summer):
            status = "polar_day"
        else:
            status = "polar_night"

    return {
        "date": target_date.isoformat(),
        "morning_start": morning_start.isoformat() if morning_start else None,
        "morning_end": morning_end.isoformat() if morning_end else None,
        "evening_start": evening_start.isoformat() if evening_start else None,
        "evening_end": evening_end.isoformat() if evening_end else None,
        "status": status,
    }


def parse_time_spec(
    time_spec: str,
    target_date: date,
    latitude: float,
    longitude: float,
    timezone_name: str = "UTC",
) -> datetime:
    """
    Parse time specification string to datetime.

    Supports two formats:
    1. Absolute time: "HH:MM" (e.g., "19:30")
    2. Solar event: "sunset", "sunrise", "civil_dusk", etc.
    3. Solar event with offset: "sunset+30", "sunrise-15" (minutes)

    Args:
        time_spec: Time specification string
        target_date: The date to calculate for
        latitude: Observer latitude (-90 to 90)
        longitude: Observer longitude (-180 to 180)
        timezone_name: Timezone name (default "UTC")

    Returns:
        Datetime for the specified time

    Raises:
        ValueError: If time_spec format is invalid, event doesn't occur, or
                   coordinates are invalid

    Example:
        >>> from datetime import date
        >>> # Absolute time
        >>> parse_time_spec("19:30", date(2024, 6, 15), 35.96, -83.92, "America/New_York")
        datetime.datetime(2024, 6, 15, 19, 30, tzinfo=...)
        >>> # Solar event
        >>> parse_time_spec("sunset", date(2024, 6, 15), 35.96, -83.92, "America/New_York")
        datetime.datetime(2024, 6, 15, 20, 45, tzinfo=...)
        >>> # Solar event with offset
        >>> parse_time_spec("sunset+30", date(2024, 6, 15), 35.96, -83.92, "America/New_York")
        datetime.datetime(2024, 6, 15, 21, 15, tzinfo=...)
    """
    _validate_coordinates(latitude, longitude)

    # Try absolute time format (HH:MM)
    abs_match = ABSOLUTE_TIME_PATTERN.match(time_spec)
    if abs_match:
        hour = int(abs_match.group(1))
        minute = int(abs_match.group(2))

        # Create datetime with timezone
        tz = pytz.timezone(timezone_name)
        naive_dt = datetime.combine(target_date, time(hour, minute))
        return tz.localize(naive_dt)

    # Try solar event format (event or event±offset)
    solar_match = TIME_SPEC_PATTERN.match(time_spec)
    if solar_match:
        event_name = solar_match.group(1)
        offset_str = solar_match.group(2)

        # Get base event time
        event_time = _get_sun_event_time(
            event_name, target_date, latitude, longitude, timezone_name
        )

        if event_time is None:
            raise ValueError(
                f"Solar event '{event_name}' does not occur on {target_date} "
                f"at latitude {latitude}, longitude {longitude}"
            )

        # Apply offset if present
        if offset_str:
            offset_minutes = int(offset_str)
            event_time += timedelta(minutes=offset_minutes)

        return event_time

    # Invalid format
    raise ValueError(
        f"Invalid time specification '{time_spec}'. "
        f"Must be HH:MM format or a solar event (e.g., 'sunset', 'sunset+30')"
    )


def get_daylight_hours(
    target_date: date,
    latitude: float,
    longitude: float,
    timezone_name: str = "UTC",
) -> float:
    """
    Calculate daylight hours for a location and date.

    Returns the number of hours between sunrise and sunset. Useful for
    determining day length for scheduling or analysis.

    Args:
        target_date: The date to calculate for
        latitude: Observer latitude (-90 to 90)
        longitude: Observer longitude (-180 to 180)
        timezone_name: Timezone name (default "UTC")

    Returns:
        Daylight hours as float (e.g., 14.5 for 14 hours 30 minutes)

    Raises:
        ValueError: If coordinates are invalid or sun doesn't rise/set

    Note:
        In polar regions during midnight sun or polar night, this function
        may raise ValueError.

    Example:
        >>> from datetime import date
        >>> # Summer solstice at mid-latitude
        >>> hours = get_daylight_hours(date(2024, 6, 21), 35.96, -83.92)
        >>> hours
        14.5
    """
    _validate_coordinates(latitude, longitude)
    sun_times = get_sun_times(target_date, latitude, longitude, timezone_name)

    if sun_times["sunrise"] is None or sun_times["sunset"] is None:
        raise ValueError(
            f"Cannot calculate daylight hours for {target_date} at "
            f"latitude {latitude}, longitude {longitude}. "
            f"Sun may not rise or set on this date (polar region)."
        )

    sunrise = datetime.fromisoformat(sun_times["sunrise"])
    sunset = datetime.fromisoformat(sun_times["sunset"])

    # Handle case where sunset occurs on the next calendar day (e.g., in UTC for western longitudes)
    # This happens because astral calculates the actual solar noon for the location,
    # and in UTC the sunset time may be past midnight
    if sunset < sunrise:
        # Sunset is on the next day, add 24 hours to calculate correct duration
        sunset += timedelta(days=1)

    duration = sunset - sunrise
    hours = duration.total_seconds() / 3600.0

    return round(hours, 2)

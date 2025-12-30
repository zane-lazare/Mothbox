"""
Haversine distance calculation library for GPS coordinates.

This module provides functions for calculating great-circle distances between
GPS coordinates using the Haversine formula. Used for clustering Mothbox photos
by location and detecting photo series taken at nearby coordinates.

The Haversine formula:
    a = sin²(Δφ/2) + cos φ1 ⋅ cos φ2 ⋅ sin²(Δλ/2)
    c = 2 ⋅ atan2(√a, √(1−a))
    d = R ⋅ c

where:
    φ = latitude in radians
    λ = longitude in radians
    R = Earth's radius (6,371,000 meters)

Example:
    >>> from webui.backend.lib.haversine import haversine_distance, is_within_distance
    >>>
    >>> # Calculate distance between NYC and London
    >>> distance = haversine_distance(40.7128, -74.0060, 51.5074, -0.1278)
    >>> print(f"Distance: {distance / 1000:.2f} km")
    Distance: 5570.23 km
    >>>
    >>> # Check if two coordinates are within 100m
    >>> lat1, lon1 = 37.7749, -122.4194  # San Francisco
    >>> lat2, lon2 = 37.7759, -122.4194  # ~100m north
    >>> nearby = is_within_distance(lat1, lon1, lat2, lon2, 150)
    >>> print(f"Within 150m: {nearby}")
    Within 150m: True

Performance:
    - Single distance calculation: <1ms
    - 1000 calculations: <100ms
    - 10000 validations: <50ms
"""

import math

# Earth's mean radius in meters (WGS84 approximation)
EARTH_RADIUS_M = 6371000


def validate_coordinates(lat: float, lon: float) -> tuple[bool, str | None]:
    """
    Validate GPS coordinates.

    Checks that latitude and longitude are valid numeric values within
    acceptable ranges:
    - Latitude: -90 to 90 degrees
    - Longitude: -180 to 180 degrees

    Args:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees

    Returns:
        Tuple of (is_valid, error_message):
        - is_valid: True if coordinates are valid, False otherwise
        - error_message: None if valid, error description if invalid

    Example:
        >>> validate_coordinates(37.7749, -122.4194)
        (True, None)
        >>>
        >>> validate_coordinates(91.0, 0.0)
        (False, 'Latitude must be between -90 and 90 degrees, got 91.0')
    """
    # Check for None values
    if lat is None or lon is None:
        return False, "Latitude and longitude must not be None"

    # Check for numeric types
    try:
        lat_float = float(lat)
        lon_float = float(lon)
    except (TypeError, ValueError):
        return (
            False,
            f"Latitude and longitude must be numeric, got lat={type(lat).__name__}, lon={type(lon).__name__}",
        )

    # Check for NaN or infinity
    if math.isnan(lat_float) or math.isinf(lat_float):
        return False, f"Latitude must be a finite number, got {lat_float}"

    if math.isnan(lon_float) or math.isinf(lon_float):
        return False, f"Longitude must be a finite number, got {lon_float}"

    # Check latitude range
    if lat_float < -90.0 or lat_float > 90.0:
        return False, f"Latitude must be between -90 and 90 degrees, got {lat_float}"

    # Check longitude range
    if lon_float < -180.0 or lon_float > 180.0:
        return False, f"Longitude must be between -180 and 180 degrees, got {lon_float}"

    return True, None


def normalize_longitude(lon: float) -> float:
    """
    Normalize longitude to -180 to 180 degree range.

    Handles longitude values outside the standard range by wrapping them
    around the international dateline. This is useful for handling GPS
    coordinates that cross the dateline or have been offset by 360°.

    Args:
        lon: Longitude in decimal degrees (can be any value)

    Returns:
        Normalized longitude in range -180 to 180 degrees

    Example:
        >>> normalize_longitude(270.0)
        -90.0
        >>>
        >>> normalize_longitude(-270.0)
        90.0
        >>>
        >>> normalize_longitude(180.0)
        180.0
        >>>
        >>> normalize_longitude(360.0)
        0.0
    """
    # Special handling for values already in range to avoid floating point errors
    if -180.0 <= lon <= 180.0:
        return lon

    # Use modulo to wrap to -180 to 180 range
    # First normalize to 0-360, then shift to -180 to 180
    normalized = ((lon + 180.0) % 360.0) - 180.0

    return normalized


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two GPS coordinates.

    Uses the Haversine formula to compute the shortest distance over the
    Earth's surface between two points specified by latitude and longitude.
    Assumes a spherical Earth with radius 6,371 km (WGS84 approximation).

    The Haversine formula is accurate for most distances but may have
    slight errors (~0.5%) for antipodal points (opposite sides of Earth).

    Args:
        lat1: Latitude of first point in decimal degrees
        lon1: Longitude of first point in decimal degrees
        lat2: Latitude of second point in decimal degrees
        lon2: Longitude of second point in decimal degrees

    Returns:
        Distance in meters (float)

    Raises:
        ValueError: If any coordinates are invalid (out of range, NaN, None)

    Example:
        >>> # Distance from NYC to London
        >>> distance = haversine_distance(40.7128, -74.0060, 51.5074, -0.1278)
        >>> print(f"{distance / 1000:.2f} km")
        5570.23 km
        >>>
        >>> # Same point returns 0
        >>> haversine_distance(37.7749, -122.4194, 37.7749, -122.4194)
        0.0
    """
    # Validate all coordinates
    is_valid, error = validate_coordinates(lat1, lon1)
    if not is_valid:
        raise ValueError(f"Invalid first coordinate: {error}")

    is_valid, error = validate_coordinates(lat2, lon2)
    if not is_valid:
        raise ValueError(f"Invalid second coordinate: {error}")

    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Haversine formula
    # Δφ = lat2 - lat1
    # Δλ = lon2 - lon1
    delta_lat = lat2_rad - lat1_rad
    delta_lon = lon2_rad - lon1_rad

    # a = sin²(Δφ/2) + cos φ1 ⋅ cos φ2 ⋅ sin²(Δλ/2)
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )

    # c = 2 ⋅ atan2(√a, √(1−a))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # d = R ⋅ c
    distance = EARTH_RADIUS_M * c

    return distance


def is_within_distance(
    lat1: float, lon1: float, lat2: float, lon2: float, distance_m: float
) -> bool:
    """
    Check if two GPS coordinates are within a specified distance.

    Convenience function that combines distance calculation and threshold
    comparison. Useful for clustering nearby photos or filtering photos
    by location.

    Args:
        lat1: Latitude of first point in decimal degrees
        lon1: Longitude of first point in decimal degrees
        lat2: Latitude of second point in decimal degrees
        lon2: Longitude of second point in decimal degrees
        distance_m: Maximum distance threshold in meters

    Returns:
        True if the actual distance is less than or equal to distance_m,
        False otherwise

    Raises:
        ValueError: If any coordinates are invalid or distance_m is negative

    Example:
        >>> # Check if two photos were taken within 100m
        >>> lat1, lon1 = 37.7749, -122.4194  # Photo 1
        >>> lat2, lon2 = 37.7759, -122.4194  # Photo 2 (~100m north)
        >>>
        >>> is_within_distance(lat1, lon1, lat2, lon2, 150)
        True
        >>>
        >>> is_within_distance(lat1, lon1, lat2, lon2, 50)
        False
    """
    # Validate distance threshold
    if distance_m < 0:
        raise ValueError(f"Distance threshold must be non-negative, got {distance_m}")

    # Calculate actual distance (this also validates coordinates)
    actual_distance = haversine_distance(lat1, lon1, lat2, lon2)

    # Check if within threshold
    return actual_distance <= distance_m

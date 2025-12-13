"""
Country Code Detection Module for Mothbox Photo Gallery (Issue #116)

Provides offline country code detection from GPS coordinates and system locale
for populating Darwin Core countryCode field.

Uses geopip library for GPS-to-country lookup with system locale fallback.
All operations are offline - no network calls required.

Usage:
    from webui.backend.lib.country_code import detect_country_code

    # From GPS coordinates (primary)
    code = detect_country_code(latitude=37.7749, longitude=-122.4194)
    # Returns: "US"

    # With locale fallback when GPS unavailable
    code = detect_country_code()
    # Returns: country from system locale (e.g., "US" from en_US.UTF-8)

    # Disable locale fallback
    code = detect_country_code(use_locale_fallback=False)
    # Returns: None if no GPS provided

Performance:
    - GPS lookup: ~25 µs per call
    - Locale detection: <1 ms
    - Fully offline (no network calls)
"""

import locale
import logging
import os

logger = logging.getLogger(__name__)


def detect_country_from_gps(latitude: float, longitude: float) -> str | None:
    """Detect ISO 3166-1 alpha-2 country code from GPS coordinates.

    Uses geopip library for offline reverse geocoding at country level.
    The library uses simplified country boundaries (~several km accuracy).

    Note: geopip uses simplified boundaries that may not cover coastal areas
    or border regions accurately. Locations very close to coastlines or
    borders may return None.

    Args:
        latitude: GPS latitude in decimal degrees (-90 to 90)
        longitude: GPS longitude in decimal degrees (-180 to 180)

    Returns:
        ISO 3166-1 alpha-2 country code (e.g., "US", "GB", "JP") or None

    Example:
        >>> detect_country_from_gps(41.8781, -87.6298)  # Chicago
        'US'
        >>> detect_country_from_gps(51.5074, -0.1278)  # London
        'GB'
    """
    try:
        import geopip
        # geopip.search() takes (longitude, latitude) order
        result = geopip.search(longitude, latitude)
        if result:
            return result.get('ISO2')
        return None
    except ImportError:
        logger.warning("geopip not installed - GPS country detection unavailable")
        return None
    except Exception as e:
        logger.warning("GPS country lookup failed for (%s, %s): %s", latitude, longitude, e)
        return None


def detect_country_from_locale() -> str | None:
    """Extract ISO 3166-1 alpha-2 country code from system locale.

    Attempts to extract country code from environment variables (LC_ALL, LANG,
    LC_COLLATE) or locale.getlocale(). This is a fallback when GPS is unavailable.

    Note: This only works if the system locale matches the deployment location,
    which may not be reliable for field-deployed devices.

    Returns:
        ISO 3166-1 alpha-2 country code or None

    Example:
        >>> # With LANG=en_US.UTF-8
        >>> detect_country_from_locale()
        'US'
        >>> # With LANG=de_DE.UTF-8
        >>> detect_country_from_locale()
        'DE'
    """
    # Try environment variables first (most reliable)
    for env_var in ['LC_ALL', 'LANG', 'LC_COLLATE']:
        locale_str = os.environ.get(env_var, '')
        if '_' in locale_str:
            parts = locale_str.split('_')
            if len(parts) >= 2:
                # Handle formats like "en_US.UTF-8" or "en_US"
                country = parts[1].split('.')[0].split('@')[0]
                if len(country) == 2 and country.isalpha():
                    return country.upper()

    # Fall back to locale.getlocale()
    try:
        loc = locale.getlocale()[0]
        if loc and '_' in loc:
            parts = loc.split('_')
            if len(parts) >= 2:
                country = parts[1].split('.')[0].split('@')[0]
                if len(country) == 2 and country.isalpha():
                    return country.upper()
    except Exception as e:
        logger.debug("locale.getlocale() failed: %s", e)

    return None


def detect_country_code(
    latitude: float | None = None,
    longitude: float | None = None,
    use_locale_fallback: bool = True
) -> str | None:
    """Detect country code using GPS coordinates with optional locale fallback.

    Primary strategy uses GPS coordinates for accurate location-based detection.
    Falls back to system locale when GPS is unavailable (if enabled).

    Args:
        latitude: GPS latitude in decimal degrees (-90 to 90), or None
        longitude: GPS longitude in decimal degrees (-180 to 180), or None
        use_locale_fallback: Whether to fall back to system locale when GPS
            unavailable (default True)

    Returns:
        ISO 3166-1 alpha-2 country code (e.g., "US", "GB") or None

    Example:
        >>> # GPS-based detection
        >>> detect_country_code(37.7749, -122.4194)
        'US'

        >>> # Locale fallback when GPS unavailable
        >>> detect_country_code()  # With LANG=en_US.UTF-8
        'US'

        >>> # Disable locale fallback
        >>> detect_country_code(use_locale_fallback=False)
        None
    """
    # Primary: GPS-based detection (most accurate)
    if latitude is not None and longitude is not None:
        # Validate coordinate ranges
        if not (-90 <= latitude <= 90):
            logger.warning("Invalid latitude: %s (must be -90 to 90)", latitude)
        elif not (-180 <= longitude <= 180):
            logger.warning("Invalid longitude: %s (must be -180 to 180)", longitude)
        else:
            code = detect_country_from_gps(latitude, longitude)
            if code:
                logger.debug("GPS country detection: (%s, %s) -> %s", latitude, longitude, code)
                return code
            # GPS lookup returned None (e.g., ocean coordinates)
            logger.debug("GPS country detection returned None for (%s, %s)", latitude, longitude)

    # Fallback: System locale
    if use_locale_fallback:
        code = detect_country_from_locale()
        if code:
            logger.debug("Locale fallback: %s", code)
            return code

    return None


# Valid ISO 3166-1 alpha-2 country codes for validation
# This is a subset of commonly used codes - full validation would require pycountry
COMMON_COUNTRY_CODES = {
    'US', 'GB', 'CA', 'AU', 'DE', 'FR', 'JP', 'CN', 'IN', 'BR',
    'MX', 'ES', 'IT', 'NL', 'SE', 'NO', 'DK', 'FI', 'CH', 'AT',
    'BE', 'PL', 'PT', 'GR', 'CZ', 'HU', 'RO', 'BG', 'IE', 'NZ',
    'ZA', 'KR', 'TW', 'SG', 'HK', 'MY', 'TH', 'ID', 'PH', 'VN',
    'AR', 'CL', 'CO', 'PE', 'VE', 'EC', 'CR', 'PA', 'PR', 'CU',
    'EG', 'NG', 'KE', 'GH', 'TZ', 'UG', 'ET', 'MA', 'TN', 'DZ',
    'RU', 'UA', 'BY', 'KZ', 'UZ', 'TR', 'IR', 'IQ', 'SA', 'AE',
    'IL', 'PK', 'BD', 'LK', 'NP', 'MM', 'KH', 'LA', 'MN', 'AF',
}


def is_valid_country_code(code: str | None) -> bool:
    """Check if a string is a valid ISO 3166-1 alpha-2 country code.

    Uses a common subset of country codes for basic validation.
    For comprehensive validation, consider using the pycountry library.

    Args:
        code: Country code to validate

    Returns:
        True if valid, False otherwise

    Example:
        >>> is_valid_country_code("US")
        True
        >>> is_valid_country_code("XX")
        False
    """
    if code is None:
        return False
    return code.upper() in COMMON_COUNTRY_CODES


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    'detect_country_code',
    'detect_country_from_gps',
    'detect_country_from_locale',
    'is_valid_country_code',
    'COMMON_COUNTRY_CODES',
]

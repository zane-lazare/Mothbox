"""
Timezone to approximate coordinates mapping.

Provides fallback coordinates when GPS is unavailable by mapping
system timezone to representative city coordinates.

Issue #331 - Fix GPS coordinate defaults for solar calculations.
"""

import logging
import subprocess

logger = logging.getLogger(__name__)

# Major IANA timezones mapped to representative city coordinates
# Format: "timezone": (latitude, longitude)
TIMEZONE_COORDINATES = {
    # Oceania
    "Pacific/Auckland": (-36.85, 174.76),
    "Pacific/Chatham": (-43.95, -176.55),
    "Australia/Sydney": (-33.87, 151.21),
    "Australia/Melbourne": (-37.81, 144.96),
    "Australia/Brisbane": (-27.47, 153.03),
    "Australia/Perth": (-31.95, 115.86),
    "Australia/Adelaide": (-34.93, 138.60),
    "Australia/Darwin": (-12.46, 130.84),
    "Australia/Hobart": (-42.88, 147.33),
    "Pacific/Fiji": (-18.14, 178.44),
    "Pacific/Guam": (13.47, 144.75),
    "Pacific/Honolulu": (21.31, -157.86),
    # Asia
    "Asia/Tokyo": (35.68, 139.69),
    "Asia/Singapore": (1.35, 103.82),
    "Asia/Hong_Kong": (22.32, 114.17),
    "Asia/Shanghai": (31.23, 121.47),
    "Asia/Seoul": (37.57, 126.98),
    "Asia/Taipei": (25.03, 121.57),
    "Asia/Bangkok": (13.76, 100.50),
    "Asia/Jakarta": (-6.21, 106.85),
    "Asia/Manila": (14.60, 120.98),
    "Asia/Kuala_Lumpur": (3.14, 101.69),
    "Asia/Kolkata": (28.61, 77.23),
    "Asia/Dubai": (25.20, 55.27),
    "Asia/Jerusalem": (31.77, 35.22),
    # Europe
    "Europe/London": (51.51, -0.13),
    "Europe/Paris": (48.86, 2.35),
    "Europe/Berlin": (52.52, 13.41),
    "Europe/Rome": (41.90, 12.50),
    "Europe/Madrid": (40.42, -3.70),
    "Europe/Amsterdam": (52.37, 4.90),
    "Europe/Brussels": (50.85, 4.35),
    "Europe/Vienna": (48.21, 16.37),
    "Europe/Zurich": (47.38, 8.54),
    "Europe/Stockholm": (59.33, 18.07),
    "Europe/Oslo": (59.91, 10.75),
    "Europe/Copenhagen": (55.68, 12.57),
    "Europe/Helsinki": (60.17, 24.94),
    "Europe/Warsaw": (52.23, 21.01),
    "Europe/Prague": (50.08, 14.44),
    "Europe/Dublin": (53.35, -6.26),
    "Europe/Lisbon": (38.72, -9.14),
    "Europe/Athens": (37.98, 23.73),
    "Europe/Moscow": (55.76, 37.62),
    "Europe/Istanbul": (41.01, 28.98),
    # Americas
    "America/New_York": (40.71, -74.01),
    "America/Chicago": (41.88, -87.63),
    "America/Denver": (39.74, -104.99),
    "America/Los_Angeles": (34.05, -118.24),
    "America/Phoenix": (33.45, -112.07),
    "America/Anchorage": (61.22, -149.90),
    "America/Toronto": (43.65, -79.38),
    "America/Vancouver": (49.28, -123.12),
    "America/Montreal": (45.50, -73.57),
    "America/Mexico_City": (19.43, -99.13),
    "America/Sao_Paulo": (-23.55, -46.63),
    "America/Buenos_Aires": (-34.60, -58.38),
    "America/Lima": (-12.05, -77.04),
    "America/Bogota": (4.71, -74.07),
    "America/Santiago": (-33.45, -70.67),
    "America/Caracas": (10.49, -66.88),
    # Africa
    "Africa/Johannesburg": (-26.20, 28.04),
    "Africa/Cairo": (30.04, 31.24),
    "Africa/Lagos": (6.52, 3.38),
    "Africa/Nairobi": (-1.29, 36.82),
    "Africa/Casablanca": (33.57, -7.59),
    # UTC fallback
    "UTC": (0.0, 0.0),
    "Etc/UTC": (0.0, 0.0),
}


def get_system_timezone() -> str:
    """
    Get system timezone from /etc/timezone or timedatectl.

    Returns:
        str: IANA timezone name (e.g., "Pacific/Auckland") or "UTC" on failure.
    """
    # Try reading /etc/timezone (Debian/Ubuntu/Raspberry Pi OS)
    try:
        with open("/etc/timezone") as f:
            tz = f.read().strip()
            if tz:
                return tz
    except (FileNotFoundError, PermissionError, OSError):
        pass

    # Try timedatectl (systemd)
    try:
        result = subprocess.run(
            ["timedatectl", "show", "-p", "Timezone", "--value"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    # Final fallback
    return "UTC"


def get_coordinates_from_timezone(timezone: str) -> tuple[float, float] | None:
    """
    Get approximate coordinates for a timezone.

    Args:
        timezone: IANA timezone name (e.g., "Pacific/Auckland")

    Returns:
        Tuple of (latitude, longitude) or None if timezone not in mapping.
    """
    return TIMEZONE_COORDINATES.get(timezone)


def get_fallback_coordinates() -> tuple[float, float, str]:
    """
    Get coordinates using system timezone as fallback.

    Returns:
        Tuple of (latitude, longitude, source) where source is the timezone
        name used for the coordinates.
    """
    tz = get_system_timezone()
    coords = get_coordinates_from_timezone(tz)

    if coords:
        logger.debug(f"Using timezone '{tz}' for coordinate fallback (redacted for privacy)")
        return (coords[0], coords[1], tz)

    # Timezone not in mapping - use UTC (0, 0) as last resort
    logger.warning(f"Timezone '{tz}' not in coordinate mapping, using UTC (0, 0)")
    return (0.0, 0.0, "UTC")

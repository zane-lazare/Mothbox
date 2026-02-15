"""GPS coordinate resolver for Mothbox photos.

Resolves GPS coordinates by walking a configurable chain of sources.
Each source is tried in order; the first to return valid coordinates wins.

Sources:
    - deployment: Reads lat/lon from a deployment sidecar (deployment.json)
    - gps: Reads current GPS fix from controls.txt
    - manual: Pass-through from user-supplied coordinates

Usage:
    >>> result = resolve_coordinates(
    ...     photo_path=Path("/photos/test.jpg"),
    ...     sources=("deployment", "gps"),
    ...     deployment_service=deployment_service,
    ... )
    >>> if result:
    ...     print(f"{result['source']}: {result['lat']}, {result['lon']}")
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from webui.backend.lib.gps_exif_lib import get_gps_data_from_controls

# Valid source names that can appear in the sources tuple
VALID_SOURCES = ("deployment", "gps", "manual")


def resolve_coordinates(
    photo_path: Path,
    sources: tuple[str, ...] = ("deployment", "gps"),
    manual_coords: dict[str, float] | None = None,
    deployment_service: Any = None,
) -> dict | None:
    """Resolve GPS coordinates for a photo by trying sources in order.

    Walks the source chain and returns the first valid result. Each source
    resolver either returns a result dict or None to indicate it cannot
    provide coordinates.

    Args:
        photo_path: Path to the photo file.
        sources: Ordered tuple of source names to try.
        manual_coords: Dict with "lat" and "lon" keys for manual source.
        deployment_service: DeploymentService instance for deployment source.
            Passed via dependency injection to avoid module-level import.

    Returns:
        Dict with keys: lat, lon, source, deployment_name, gps_data.
        None if no source could provide valid coordinates.

    Raises:
        ValueError: If an unknown source name is in the sources tuple.
    """
    # Validate all source names up front
    for source in sources:
        if source not in VALID_SOURCES:
            raise ValueError(
                f"Unknown source '{source}'. Valid sources: {', '.join(VALID_SOURCES)}"
            )

    # Dispatch table for source resolvers
    resolvers = {
        "deployment": lambda: _resolve_deployment(photo_path, deployment_service),
        "gps": lambda: _resolve_gps(),
        "manual": lambda: _resolve_manual(manual_coords),
    }

    # Walk the chain; first valid result wins
    for source in sources:
        result = resolvers[source]()
        if result is not None:
            return result

    return None


def _resolve_deployment(
    photo_path: Path,
    deployment_service: Any,
) -> dict | None:
    """Resolve coordinates from deployment sidecar metadata.

    Args:
        photo_path: Path to the photo file.
        deployment_service: DeploymentService instance (may be None).

    Returns:
        Result dict or None if deployment has no valid coordinates.
    """
    if deployment_service is None:
        return None

    metadata = deployment_service.find_deployment_for_photo(photo_path)
    if metadata is None:
        return None

    lat = metadata.latitude
    lon = metadata.longitude
    if lat is None or lon is None:
        return None

    # Build a gps_data dict compatible with embed_gps_exif
    gps_data = _build_gps_data(
        latitude=lat,
        longitude=lon,
        altitude=getattr(metadata, "altitude", None),
    )

    return {
        "lat": lat,
        "lon": lon,
        "source": "deployment",
        "deployment_name": getattr(metadata, "deployment_name", None),
        "gps_data": gps_data,
    }


def _resolve_gps() -> dict | None:
    """Resolve coordinates from the GPS hardware via controls.txt.

    Returns:
        Result dict or None if GPS has no valid fix.
    """
    gps_data = get_gps_data_from_controls()

    if not gps_data.get("has_fix", False):
        return None

    lat = gps_data.get("latitude")
    lon = gps_data.get("longitude")
    if lat is None or lon is None:
        return None

    return {
        "lat": lat,
        "lon": lon,
        "source": "gps",
        "deployment_name": None,
        "gps_data": gps_data,
    }


def _resolve_manual(
    manual_coords: dict[str, float] | None,
) -> dict | None:
    """Resolve coordinates from user-supplied manual values.

    Args:
        manual_coords: Dict with "lat" and "lon" keys, or None.

    Returns:
        Result dict or None if manual_coords is None or missing keys.
    """
    if manual_coords is None:
        return None

    lat = manual_coords.get("lat")
    lon = manual_coords.get("lon")
    if lat is None or lon is None:
        return None

    # Build a gps_data dict compatible with embed_gps_exif
    gps_data = _build_gps_data(latitude=lat, longitude=lon)

    return {
        "lat": lat,
        "lon": lon,
        "source": "manual",
        "deployment_name": None,
        "gps_data": gps_data,
    }


def _build_gps_data(
    latitude: float,
    longitude: float,
    altitude: float | None = None,
    fix_mode: int = 3,
    gpstime: int = 0,
    satellites_used: int = 0,
    hdop: float = 99.99,
    pdop: float = 99.99,
) -> dict:
    """Build a gps_data dict compatible with embed_gps_exif.

    This creates the same structure returned by get_gps_data_from_controls()
    so it can be passed directly to embed_gps_exif(gps_data=...).

    Args:
        latitude: Decimal latitude.
        longitude: Decimal longitude.
        altitude: Altitude in meters (optional).
        fix_mode: GPS fix mode (0=none, 2=2D, 3=3D). Defaults to 3.
        gpstime: Unix timestamp from GPS. Defaults to 0.
        satellites_used: Number of satellites. Defaults to 0.
        hdop: Horizontal dilution of precision. Defaults to 99.99.
        pdop: Position dilution of precision. Defaults to 99.99.

    Returns:
        Dict matching the structure of get_gps_data_from_controls() output.
    """
    return {
        "has_fix": True,
        "latitude": latitude,
        "longitude": longitude,
        "altitude": altitude,
        "fix_mode": fix_mode,
        "gpstime": gpstime,
        "satellites_used": satellites_used,
        "hdop": hdop,
        "pdop": pdop,
    }

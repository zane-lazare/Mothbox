"""
Locations Service for Mothbox Photo Gallery

Provides cached GPS location detection with thread-safety and efficient two-pass scanning.

Design notes:
- Two-pass approach for accurate counts (fast count scan, then detailed build)
- Avoids repeated EXIF loads (uses verify_gps_exif timestamp field)
- Uses iterators (itertools.chain instead of list concatenation)

Usage:
    from webui.backend.services.locations_service import LocationsService

    service = LocationsService(cache_ttl=300)  # 5 minute cache

    # Get locations with GPS data
    result = service.get_locations("/var/lib/mothbox/photos", limit=1000)
    # Returns: {
    #     'locations': [...],
    #     'total_with_gps': int,
    #     'total_without_gps': int
    # }

    # Invalidate cache
    service.invalidate_cache()  # All
    service.invalidate_cache(directory)  # Specific directory
"""

import itertools
import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class _CacheEntry:
    """Internal cache entry with timestamp for TTL expiration."""
    result: dict
    timestamp: float
    directory: Path


class LocationsService:
    """Service for detecting and caching photo GPS locations.

    Thread-safe with configurable cache TTL. Uses two-pass scanning:
    - Pass 1: Fast count scan (check has_gps without building full objects)
    - Pass 2: Build detailed location objects only up to limit

    Attributes:
        _cache_ttl: Time-to-live for cache entries in seconds
    """

    def __init__(self, cache_ttl: int = 300):
        """Initialize LocationsService.

        Args:
            cache_ttl: Cache time-to-live in seconds (default 5 minutes)
        """
        self._cache_ttl = cache_ttl
        self._cache: dict[str, _CacheEntry] = {}
        self._lock = threading.Lock()
        self._stats = {
            'cache_hits': 0,
            'cache_misses': 0,
        }

    def get_locations(
        self,
        directory: str | Path,
        limit: int = 1000
    ) -> dict:
        """Get photos with GPS coordinates.

        Scans directory recursively for photos with GPS EXIF data.
        Results are cached for performance.

        Two-pass approach (Fix 1):
        1. Pass 1: Fast scan to count total_with_gps and total_without_gps
        2. Pass 2: Build detailed location objects only up to limit

        Args:
            directory: Directory to scan (string or Path)
            limit: Maximum number of location objects to build (default 1000)

        Returns:
            dict: {
                'locations': List of location objects (up to limit),
                'total_with_gps': Total count of photos with GPS,
                'total_without_gps': Total count of photos without GPS
            }
        """
        directory = Path(directory) if isinstance(directory, str) else directory
        cache_key = f"{directory.resolve()}:{limit}"

        with self._lock:
            # Check cache
            entry = self._cache.get(cache_key)
            if entry and (time.time() - entry.timestamp) < self._cache_ttl:
                self._stats['cache_hits'] += 1
                logger.debug(f"Cache hit for {directory} (limit={limit})")
                return entry.result

            self._stats['cache_misses'] += 1

        # Cache miss - scan directory
        logger.debug(f"Cache miss for {directory}, scanning...")
        result = self._scan_directory(directory, limit)

        with self._lock:
            self._cache[cache_key] = _CacheEntry(
                result=result,
                timestamp=time.time(),
                directory=directory
            )

        return result

    def _scan_directory(self, directory: Path, limit: int) -> dict:
        """Scan directory for photos with GPS coordinates.

        Two-pass approach:
        1. Pass 1: Fast count scan (check has_gps only)
        2. Pass 2: Build detailed objects up to limit

        Args:
            directory: Directory to scan
            limit: Maximum number of detailed objects to build

        Returns:
            dict with locations list and counts
        """
        if not directory.exists():
            return {
                'locations': [],
                'total_with_gps': 0,
                'total_without_gps': 0
            }

        try:
            # Import GPS EXIF library
            from webui.backend.lib.gps_exif_lib import verify_gps_exif

            # Fix 9: Use itertools.chain instead of list concatenation
            # This avoids loading all paths into memory at once
            jpg_patterns = [
                directory.rglob("*.jpg"),
                directory.rglob("*.JPG"),
                directory.rglob("*.jpeg"),
                directory.rglob("*.JPEG")
            ]
            all_photos = itertools.chain(*jpg_patterns)

            # Pass 1: Fast count scan
            # Build list of photos with GPS status for accurate counts
            photos_with_status = []
            total_with_gps = 0
            total_without_gps = 0

            for photo_path in all_photos:
                try:
                    # Fast check: only verify if GPS exists
                    gps_info = verify_gps_exif(photo_path)
                    has_gps = gps_info.get('has_gps', False)

                    if has_gps:
                        total_with_gps += 1
                        # Store photo path and GPS info for Pass 2
                        photos_with_status.append((photo_path, gps_info))
                    else:
                        total_without_gps += 1

                except Exception as e:
                    # Handle corrupted EXIF or read errors gracefully
                    logger.debug(f"Failed to read GPS from {photo_path.name}: {e}")
                    total_without_gps += 1

            # Pass 2: Build detailed location objects (only up to limit)
            locations = []
            for photo_path, gps_info in photos_with_status[:limit]:
                try:
                    # Get relative path for API URLs
                    photo_relative = photo_path.relative_to(directory)

                    # Fix 5: Use timestamp from verify_gps_exif (already loaded)
                    # Don't load EXIF again - it's already in gps_info
                    timestamp = gps_info.get('timestamp')

                    # Convert timestamp to ISO format if needed
                    if timestamp:
                        # GPS timestamp might be in EXIF format (YYYY:MM:DD HH:MM:SS)
                        # Convert to ISO 8601 format
                        try:
                            if ':' in timestamp and ' ' in timestamp:
                                dt = datetime.strptime(timestamp, '%Y:%m:%d %H:%M:%S')
                                timestamp = dt.isoformat()
                        except Exception:
                            # Keep original timestamp if conversion fails
                            pass

                    # If no GPS timestamp, use file modification time as fallback
                    if not timestamp:
                        timestamp = datetime.fromtimestamp(photo_path.stat().st_mtime).isoformat()

                    locations.append({
                        "path": str(photo_relative),
                        "filename": photo_path.name,
                        "latitude": gps_info['latitude'],
                        "longitude": gps_info['longitude'],
                        "timestamp": timestamp,
                        "thumbnail_url": f"/api/gallery/thumbnail/{photo_relative}"
                    })

                except Exception as e:
                    # Log error but continue processing other photos
                    logger.warning(f"Failed to build location object for {photo_path.name}: {e}")

            logger.debug(
                f"Found {total_with_gps} photos with GPS, "
                f"{total_without_gps} without GPS in {directory}"
            )

            return {
                'locations': locations,
                'total_with_gps': total_with_gps,
                'total_without_gps': total_without_gps
            }

        except (PermissionError, OSError) as e:
            logger.warning(f"Error scanning {directory}: {e}")
            return {
                'locations': [],
                'total_with_gps': 0,
                'total_without_gps': 0
            }

    def invalidate_cache(self, directory: str | Path | None = None) -> None:
        """Invalidate cache entries.

        Args:
            directory: If provided, only invalidate that directory's cache.
                      If None, invalidate entire cache.
        """
        with self._lock:
            if directory is None:
                self._cache.clear()
                logger.debug("Invalidated entire locations cache")
            else:
                # Need to invalidate all cache keys for this directory
                # (since cache keys include limit parameter)
                cache_key_prefix = str(Path(directory).resolve())
                keys_to_remove = [
                    key for key in self._cache
                    if key.startswith(cache_key_prefix)
                ]
                for key in keys_to_remove:
                    del self._cache[key]
                logger.debug(f"Invalidated cache for {directory} ({len(keys_to_remove)} entries)")

    def get_statistics(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache metrics including:
            - cache_entries: Number of cached directory/limit combinations
            - cache_hits: Total cache hit count
            - cache_misses: Total cache miss count
            - total_locations: Total locations across all cached entries
        """
        with self._lock:
            total_locations = 0

            for entry in self._cache.values():
                total_locations += len(entry.result.get('locations', []))

            return {
                'cache_entries': len(self._cache),
                'cache_hits': self._stats['cache_hits'],
                'cache_misses': self._stats['cache_misses'],
                'total_locations': total_locations,
            }


# ============================================================================
# Module exports
# ============================================================================

__all__ = [
    'LocationsService',
]

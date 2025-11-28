"""
Series Service for Mothbox Photo Gallery (Issue #110)

Provides cached series detection with thread-safety and cross-directory support.

Usage:
    from webui.backend.services.series_service import SeriesService

    service = SeriesService(cache_ttl=300)  # 5 minute cache

    # Get all series in a directory
    series_list = service.get_series_for_directory("/var/lib/mothbox/photos")

    # Get specific series by ID
    series = service.get_series_by_id("hdr_moth_2024_01_15__10_00_00")

    # Invalidate cache
    service.invalidate_cache()  # All
    service.invalidate_cache(directory)  # Specific directory
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Union

from webui.backend.lib.series_detection import (
    detect_series_type,
    get_series_id,
    group_photos_into_series,
)

logger = logging.getLogger(__name__)


@dataclass
class PhotoSeries:
    """Represents a photo series (HDR or Focus Bracket).

    Attributes:
        series_id: Unique identifier for grouping (e.g., "hdr_moth_2024_01_15__10_00_00")
        series_type: Type of series ("hdr" or "focus_bracket")
        base_name: Common prefix from filename (timestamp-based)
        photos: List of photo paths in series, sorted by index
        count: Number of photos in series
        cover_photo: First photo in series (index 0), used for thumbnails
    """
    series_id: str
    series_type: str
    base_name: str
    photos: list[Path]
    count: int
    cover_photo: Path


@dataclass
class _CacheEntry:
    """Internal cache entry with timestamp for TTL expiration."""
    series_list: list[PhotoSeries]
    timestamp: float
    directory: Path


class SeriesService:
    """Service for detecting and caching photo series.

    Thread-safe with configurable cache TTL. Supports cross-directory
    series detection (photos can span date folders).

    Attributes:
        _cache_ttl: Time-to-live for cache entries in seconds
    """

    def __init__(self, cache_ttl: int = 300):
        """Initialize SeriesService.

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

    def get_series_for_directory(
        self,
        directory: Union[str, Path]
    ) -> list[PhotoSeries]:
        """Get all photo series in a directory.

        Scans directory recursively for photos and groups them by series.
        Results are cached for performance.

        Args:
            directory: Directory to scan (string or Path)

        Returns:
            List of PhotoSeries objects, sorted by base_name (timestamp)
        """
        directory = Path(directory) if isinstance(directory, str) else directory
        cache_key = str(directory.resolve())

        with self._lock:
            # Check cache
            entry = self._cache.get(cache_key)
            if entry and (time.time() - entry.timestamp) < self._cache_ttl:
                self._stats['cache_hits'] += 1
                logger.debug(f"Cache hit for {directory}")
                return entry.series_list

            self._stats['cache_misses'] += 1

        # Cache miss - scan directory
        logger.debug(f"Cache miss for {directory}, scanning...")
        series_list = self._scan_directory(directory)

        with self._lock:
            self._cache[cache_key] = _CacheEntry(
                series_list=series_list,
                timestamp=time.time(),
                directory=directory
            )

        return series_list

    def _scan_directory(self, directory: Path) -> list[PhotoSeries]:
        """Scan directory for photo series.

        Args:
            directory: Directory to scan

        Returns:
            List of PhotoSeries, sorted by base_name
        """
        if not directory.exists():
            return []

        try:
            # Find all JPEG photos recursively
            photos = list(directory.rglob("*.jpg")) + list(directory.rglob("*.JPG"))
            photos.extend(directory.rglob("*.jpeg"))
            photos.extend(directory.rglob("*.JPEG"))

            if not photos:
                return []

            # Group by series
            groups = group_photos_into_series(photos)

            # Convert to PhotoSeries objects
            series_list: list[PhotoSeries] = []
            for series_id, photo_paths in groups.items():
                if len(photo_paths) < 2:
                    continue  # Skip single photos

                # Determine series type from first photo
                info = detect_series_type(photo_paths[0])
                if not info:
                    continue

                series = PhotoSeries(
                    series_id=series_id,
                    series_type=info.series_type,
                    base_name=info.base_name,
                    photos=photo_paths,
                    count=len(photo_paths),
                    cover_photo=photo_paths[0]  # First photo (index 0)
                )
                series_list.append(series)

            # Sort by base_name (which contains timestamp)
            series_list.sort(key=lambda s: s.base_name)

            logger.debug(f"Found {len(series_list)} series in {directory}")
            return series_list

        except (PermissionError, IOError, OSError) as e:
            logger.warning(f"Error scanning {directory}: {e}")
            return []

    def get_series_by_id(
        self,
        series_id: str,
        directory: Union[str, Path, None] = None
    ) -> PhotoSeries | None:
        """Get a specific series by ID.

        Searches cached data for the series. If directory is provided,
        scans that directory first to ensure cache is populated.

        Args:
            series_id: Series identifier (e.g., "hdr_moth_2024_01_15__10_00_00")
            directory: Optional directory hint to search

        Returns:
            PhotoSeries if found, None otherwise
        """
        if directory:
            self.get_series_for_directory(directory)

        with self._lock:
            for entry in self._cache.values():
                for series in entry.series_list:
                    if series.series_id == series_id:
                        return series

        return None

    def invalidate_cache(self, directory: Union[str, Path, None] = None) -> None:
        """Invalidate cache entries.

        Args:
            directory: If provided, only invalidate that directory's cache.
                      If None, invalidate entire cache.
        """
        with self._lock:
            if directory is None:
                self._cache.clear()
                logger.debug("Invalidated entire series cache")
            else:
                cache_key = str(Path(directory).resolve())
                if cache_key in self._cache:
                    del self._cache[cache_key]
                    logger.debug(f"Invalidated cache for {directory}")

    def get_statistics(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache metrics including:
            - cache_entries: Number of cached directories
            - cache_hits: Total cache hit count
            - cache_misses: Total cache miss count
            - total_series: Total series across all cached directories
            - series_by_type: Count of series by type (hdr, focus_bracket)
        """
        with self._lock:
            total_series = 0
            series_by_type: dict[str, int] = {}

            for entry in self._cache.values():
                for series in entry.series_list:
                    total_series += 1
                    t = series.series_type
                    series_by_type[t] = series_by_type.get(t, 0) + 1

            return {
                'cache_entries': len(self._cache),
                'cache_hits': self._stats['cache_hits'],
                'cache_misses': self._stats['cache_misses'],
                'total_series': total_series,
                'series_by_type': series_by_type,
            }


# ============================================================================
# Module exports
# ============================================================================

__all__ = [
    'SeriesService',
    'PhotoSeries',
]

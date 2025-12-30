"""
Clustering Service for Mothbox Photo Locations

Provides cached geographic clustering with thread-safety and performance optimizations.

Usage:
    from webui.backend.services.clustering_service import ClusteringService

    service = ClusteringService(cache_ttl=300)  # 5 minute cache

    # Get clustered locations
    result = service.get_clustered_locations(
        directory="/var/lib/mothbox/photos",
        radius_m=100,
        min_cluster_size=2
    )

    # Invalidate cache
    service.invalidate_cache()  # All
    service.invalidate_cache(directory)  # Specific directory
"""

import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from webui.backend.lib.geo_clustering import ClusteringResult, cluster_locations
from webui.backend.services.locations_service import LocationsService

logger = logging.getLogger(__name__)


# ============================================================================
# Internal Cache Entry
# ============================================================================


@dataclass
class _CacheEntry:
    """Internal cache entry with timestamp for TTL expiration."""

    result: ClusteringResult
    timestamp: float
    directory: Path
    radius_m: float
    min_cluster_size: int


# ============================================================================
# Clustering Service
# ============================================================================


class ClusteringService:
    """
    Service for clustering photo locations with caching.

    Thread-safe with configurable cache TTL. Integrates with LocationsService
    for photo location data and geo_clustering library for clustering logic.

    Attributes:
        _cache_ttl: Time-to-live for cache entries in seconds
        _default_radius_m: Default clustering radius in meters
        _default_min_cluster_size: Default minimum cluster size
        _timeout_ms: Maximum clustering processing time before partial results
    """

    def __init__(
        self,
        cache_ttl: int = 300,
        default_radius_m: float = 100,
        default_min_cluster_size: int = 2,
        timeout_ms: float = 500,
    ):
        """
        Initialize ClusteringService.

        Args:
            cache_ttl: Cache time-to-live in seconds (default 5 minutes)
            default_radius_m: Default clustering radius in meters (default 100)
            default_min_cluster_size: Default minimum photos per cluster (default 2)
            timeout_ms: Clustering timeout in milliseconds (default 500)
        """
        self._cache_ttl = cache_ttl
        self._default_radius_m = default_radius_m
        self._default_min_cluster_size = default_min_cluster_size
        self._timeout_ms = timeout_ms

        # Cache: key = f"{directory}:{radius_m}:{min_cluster_size}"
        self._cache: dict[str, _CacheEntry] = {}
        self._lock = threading.Lock()

        # Statistics
        self._stats = {"cache_hits": 0, "cache_misses": 0, "total_clustering_time_ms": 0.0}

        # LocationsService for fetching photo locations
        self._locations_service = LocationsService(cache_ttl=cache_ttl)

    def get_clustered_locations(
        self,
        directory: str | Path | None = None,
        radius_m: float | None = None,
        min_cluster_size: int | None = None,
        force_refresh: bool = False,
    ) -> ClusteringResult:
        """
        Get clustered photo locations.

        Uses cache if valid and parameters match, otherwise re-clusters.

        Args:
            directory: Photo directory (uses PHOTOS_DIR if None)
            radius_m: Clustering radius in meters (uses default if None)
            min_cluster_size: Minimum photos per cluster (uses default if None)
            force_refresh: Force re-clustering even if cache valid

        Returns:
            ClusteringResult with clusters and metadata
        """
        # Import here to avoid circular dependency
        from mothbox_paths import PHOTOS_DIR

        # Resolve parameters
        directory = Path(directory) if directory else PHOTOS_DIR
        directory = directory if isinstance(directory, Path) else Path(directory)
        radius_m = radius_m if radius_m is not None else self._default_radius_m
        min_cluster_size = (
            min_cluster_size if min_cluster_size is not None else self._default_min_cluster_size
        )

        # Generate cache key
        cache_key = f"{directory.resolve()}:{radius_m}:{min_cluster_size}"

        # Check cache (unless force_refresh)
        if not force_refresh:
            with self._lock:
                entry = self._cache.get(cache_key)
                if entry and (time.time() - entry.timestamp) < self._cache_ttl:
                    self._stats["cache_hits"] += 1
                    logger.debug(
                        f"Cache hit for {directory} "
                        f"(radius={radius_m}, min_size={min_cluster_size})"
                    )
                    return entry.result

        # Cache miss - perform clustering
        with self._lock:
            self._stats["cache_misses"] += 1

        logger.debug(
            f"Cache miss for {directory}, clustering with "
            f"radius={radius_m}, min_size={min_cluster_size}"
        )

        result = self._cluster_directory(directory, radius_m, min_cluster_size)

        # Store in cache
        with self._lock:
            self._cache[cache_key] = _CacheEntry(
                result=result,
                timestamp=time.time(),
                directory=directory,
                radius_m=radius_m,
                min_cluster_size=min_cluster_size,
            )
            self._stats["total_clustering_time_ms"] += result.processing_time_ms

        return result

    def _cluster_directory(
        self, directory: Path, radius_m: float, min_cluster_size: int
    ) -> ClusteringResult:
        """
        Perform clustering on photos in directory.

        Args:
            directory: Directory to scan
            radius_m: Clustering radius in meters
            min_cluster_size: Minimum photos per cluster

        Returns:
            ClusteringResult with clusters and metadata
        """
        # Get locations from LocationsService (cached)
        locations_result = self._locations_service.get_locations(
            directory,
            limit=10000,  # Large limit for clustering
        )

        locations = locations_result.get("locations", [])

        if not locations:
            # Return empty result
            return ClusteringResult(
                clusters=[],
                unclustered=[],
                total_photos=0,
                total_clusters=0,
                radius_m=radius_m,
                processing_time_ms=0.0,
            )

        # Convert to format expected by cluster_locations
        # locations from LocationsService: {path, filename, latitude, longitude, timestamp, thumbnail_url}
        # cluster_locations expects: {path, lat, lon, timestamp}
        clustering_input = []
        for loc in locations:
            clustering_input.append(
                {
                    "path": loc["path"],
                    "lat": loc["latitude"],
                    "lon": loc["longitude"],
                    "timestamp": loc.get("timestamp"),
                    "filepath": loc.get("path"),
                }
            )

        # Perform clustering
        result = cluster_locations(
            locations=clustering_input,
            radius_m=radius_m,
            min_cluster_size=min_cluster_size,
            timeout_ms=self._timeout_ms,
        )

        return result

    def invalidate_cache(self, directory: str | Path | None = None) -> None:
        """
        Invalidate cache entries.

        Args:
            directory: If provided, only invalidate that directory's cache.
                      If None, invalidate entire cache.
        """
        with self._lock:
            if directory is None:
                self._cache.clear()
                logger.debug("Invalidated entire clustering cache")
            else:
                # Invalidate all cache keys for this directory
                # (cache keys include radius and min_cluster_size)
                directory_path = Path(directory).resolve()
                cache_key_prefix = str(directory_path)

                keys_to_remove = [key for key in self._cache if key.startswith(cache_key_prefix)]

                for key in keys_to_remove:
                    del self._cache[key]

                logger.debug(
                    f"Invalidated clustering cache for {directory} ({len(keys_to_remove)} entries)"
                )

    def get_statistics(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache metrics including:
            - cache_entries: Number of cached configurations
            - cache_hits: Total cache hit count
            - cache_misses: Total cache miss count
            - total_clustering_time_ms: Total time spent clustering
        """
        with self._lock:
            return {
                "cache_entries": len(self._cache),
                "cache_hits": self._stats["cache_hits"],
                "cache_misses": self._stats["cache_misses"],
                "total_clustering_time_ms": self._stats["total_clustering_time_ms"],
            }


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    "ClusteringService",
]

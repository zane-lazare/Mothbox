"""
Deployment Service with LRU Cache

Provides cached access to deployment metadata through an in-memory LRU cache.
Deployment metadata describes entire photo collections (location, time period,
environmental conditions).

Performance targets:
- Cache hit rate: >80%
- Cache hit: <10ms
- Disk read: <50ms
- Batch processing: 100 directories < 1 second

Thread-safe with statistics tracking.

Usage:
    from webui.backend.services.deployment_service import DeploymentService

    service = DeploymentService(cache_ttl=300)

    # Get deployment metadata (cache -> disk)
    metadata = service.get_deployment_metadata("/photos/forest_2024")

    # Update deployment metadata (updates cache and disk)
    metadata = service.update_deployment_metadata(
        "/photos/forest_2024",
        {"end_date": "2024-09-15"}
    )

    # List all deployments under root directory
    deployments = service.list_deployments("/photos")

    # Find deployment for a specific photo
    metadata = service.find_deployment_for_photo("/photos/forest_2024/photo.jpg")

    # Batch operations
    results = service.batch_update_deployments([
        ("/photos/forest_2024", {"end_date": "2024-09-15"}),
        ("/photos/meadow_2024", {"end_date": "2024-09-20"}),
    ])

    # Statistics
    stats = service.get_statistics()
    print(f"Hit ratio: {stats['hit_ratio']:.2%}")
"""

import logging
import time
from collections import OrderedDict
from pathlib import Path
from threading import RLock
from typing import Any

from mothbox_paths import PHOTOS_DIR
from webui.backend.lib.deployment_schema import DeploymentMetadata
from webui.backend.lib.deployment_sidecar import (
    create_deployment_metadata,
    delete_deployment_metadata as lib_delete,
    deployment_has_sidecar,
    find_deployment_sidecar,
    read_deployment_metadata,
    update_deployment_metadata as lib_update,
    write_deployment_metadata,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Deployment Service
# ============================================================================

class DeploymentService:
    """
    LRU cache for deployment metadata.

    In-memory cache with configurable TTL and LRU eviction.

    Performance targets:
    - Cache hit: <10ms
    - Disk read: <50ms
    - Hit rate: >80%

    Thread Safety:
    ---------------
    This class uses three locks to ensure thread-safe operation:
    - _cache_lock: Protects in-memory cache (OrderedDict)
    - _stats_lock: Protects statistics counters

    LOCK ACQUISITION ORDER (to prevent deadlocks):
    -----------------------------------------------
    If multiple locks must be acquired, always acquire in this order:
        1. _cache_lock (first)
        2. _stats_lock (last)

    NEVER acquire locks in a different order, as this can cause deadlocks.
    """

    def __init__(
        self,
        cache_ttl: int = 300,
        max_cache_size: int = 100,
    ):
        """
        Initialize deployment service with LRU cache.

        Args:
            cache_ttl: Cache time-to-live in seconds (default 300s = 5 minutes)
            max_cache_size: Maximum cache entries (default 100)
        """
        self.cache_ttl = cache_ttl
        self.max_cache_size = max_cache_size

        # In-memory cache (LRU using OrderedDict)
        # Maps directory path (str) -> (metadata, timestamp)
        self._cache: OrderedDict[str, tuple[DeploymentMetadata, float]] = OrderedDict()
        self._cache_lock = RLock()

        # Statistics tracking
        self._stats_lock = RLock()
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_evictions = 0
        self._total_reads = 0
        self._total_writes = 0
        self._total_deletes = 0

    # ========================================================================
    # Core CRUD Operations
    # ========================================================================

    def get_deployment_metadata(self, directory: Path | str) -> DeploymentMetadata | None:
        """
        Get deployment metadata from cache or disk.

        Args:
            directory: Directory path

        Returns:
            DeploymentMetadata if found, None otherwise
        """
        directory = str(Path(directory).resolve())
        start_time = time.time()

        # Try cache first
        with self._cache_lock:
            if directory in self._cache:
                metadata, cached_at = self._cache[directory]

                # Check if cache entry is still valid
                if time.time() - cached_at < self.cache_ttl:
                    # Move to end (most recently used)
                    self._cache.move_to_end(directory)

                    # Record cache hit
                    with self._stats_lock:
                        self._cache_hits += 1
                        self._total_reads += 1

                    logger.debug(
                        f"Cache HIT for {directory} "
                        f"({(time.time() - start_time) * 1000:.2f}ms)"
                    )
                    return metadata

                # Cache entry expired - remove it
                del self._cache[directory]

        # Cache miss - read from disk
        metadata = read_deployment_metadata(directory)

        # Record statistics
        with self._stats_lock:
            self._cache_misses += 1
            self._total_reads += 1

        # Cache the result if found
        if metadata:
            with self._cache_lock:
                self._set_cache(directory, metadata)

        logger.debug(
            f"Cache MISS for {directory} "
            f"({(time.time() - start_time) * 1000:.2f}ms)"
        )

        return metadata

    def set_deployment_metadata(
        self,
        directory: Path | str,
        metadata: DeploymentMetadata,
        format: str = "json"
    ) -> bool:
        """
        Store deployment metadata in cache and on disk.

        Args:
            directory: Directory path
            metadata: Metadata to store
            format: File format ("json" or "yaml")

        Returns:
            True if successful, False otherwise
        """
        directory = str(Path(directory).resolve())

        # Write to disk
        success = write_deployment_metadata(directory, metadata, format=format)

        if success:
            # Update cache
            with self._cache_lock:
                self._set_cache(directory, metadata)

            # Record statistics
            with self._stats_lock:
                self._total_writes += 1

        return success

    def update_deployment_metadata(
        self,
        directory: Path | str,
        updates: dict
    ) -> DeploymentMetadata | None:
        """
        Update deployment metadata and cache.

        Args:
            directory: Directory path
            updates: Dictionary of fields to update

        Returns:
            Updated DeploymentMetadata if successful, None if failed
        """
        directory_str = str(Path(directory).resolve())

        try:
            # Update on disk (uses lib function with file locking)
            metadata = lib_update(directory, updates)

            # Update cache
            if metadata:
                with self._cache_lock:
                    self._set_cache(directory_str, metadata)

                # Record statistics
                with self._stats_lock:
                    self._total_writes += 1

            return metadata

        except Exception as e:
            logger.error(f"Failed to update deployment metadata for {directory}: {e}")
            return None

    def delete_deployment_metadata(self, directory: Path | str) -> bool:
        """
        Delete deployment metadata file and invalidate cache.

        Args:
            directory: Directory path

        Returns:
            True if sidecar was deleted successfully, False otherwise
        """
        directory_str = str(Path(directory).resolve())

        # Delete from disk
        success = lib_delete(directory)

        # Always invalidate cache - file may be gone, partially deleted, or corrupted
        with self._cache_lock:
            if directory_str in self._cache:
                del self._cache[directory_str]

        # Record statistics
        if success:
            with self._stats_lock:
                self._total_deletes += 1

        return success

    # ========================================================================
    # Discovery Operations
    # ========================================================================

    def list_deployments(self, root_dir: Path | str | None = None) -> list[DeploymentMetadata]:
        """
        List all deployments under root directory.

        Recursively searches for deployment.json or deployment.yaml files
        and returns their metadata.

        Args:
            root_dir: Root directory to search. If None, uses PHOTOS_DIR.

        Returns:
            List of DeploymentMetadata objects
        """
        if root_dir is None:
            root_dir = PHOTOS_DIR

        root_dir = Path(root_dir).resolve()

        if not root_dir.exists() or not root_dir.is_dir():
            return []

        deployments = []

        # Search for deployment.json files
        for deployment_path in root_dir.rglob("deployment.json"):
            directory = deployment_path.parent
            metadata = self.get_deployment_metadata(directory)
            if metadata:
                deployments.append(metadata)

        # Search for deployment.yaml files (skip if JSON already found)
        for deployment_path in root_dir.rglob("deployment.yaml"):
            directory = deployment_path.parent

            # Skip if directory already has JSON deployment
            if (directory / "deployment.json").exists():
                continue

            metadata = self.get_deployment_metadata(directory)
            if metadata:
                deployments.append(metadata)

        return deployments

    def find_deployment_for_photo(self, photo_path: Path | str) -> DeploymentMetadata | None:
        """
        Find nearest deployment metadata by walking up directory tree.

        Searches current directory and all parent directories up to PHOTOS_DIR root.

        Args:
            photo_path: Photo file path

        Returns:
            DeploymentMetadata if found, None otherwise
        """
        # Find deployment sidecar path (walks up directory tree)
        sidecar_path = find_deployment_sidecar(photo_path)

        if sidecar_path is None:
            return None

        # Get metadata for the directory containing the sidecar
        directory = sidecar_path.parent
        return self.get_deployment_metadata(directory)

    # ========================================================================
    # Batch Operations
    # ========================================================================

    def batch_update_deployments(self, updates: list[tuple[Path | str, dict]]) -> dict:
        """
        Update multiple deployments' metadata.

        Args:
            updates: List of (directory, updates_dict) tuples

        Returns:
            Dictionary with:
            - success: List of successful directory paths (str)
            - failed: List of dicts with index, directory, and error for debugging
            - errors: Dictionary mapping failed paths to error messages
            - total: Total number of updates attempted
            - successful: Number of successful updates
            - failed_count: Number of failed updates
        """
        success = []
        failed = []
        errors = {}

        for index, (directory, update_dict) in enumerate(updates):
            directory_str = str(Path(directory).resolve())

            try:
                metadata = self.update_deployment_metadata(directory, update_dict)
                if metadata:
                    success.append(directory_str)
                else:
                    failed.append({
                        "index": index,
                        "directory": directory_str,
                        "error": "Update returned None"
                    })
                    errors[directory_str] = "Update returned None"
            except Exception as e:
                failed.append({
                    "index": index,
                    "directory": directory_str,
                    "error": str(e)
                })
                errors[directory_str] = str(e)

        return {
            "success": success,
            "failed": failed,
            "errors": errors,
            "total": len(updates),
            "successful": len(success),
            "failed_count": len(failed),
        }

    def generate_sidecars_for_directory(
        self,
        directory: Path | str,
        template: dict
    ) -> int:
        """
        Generate deployment sidecars for subdirectories using a template.

        Creates deployment metadata for each subdirectory that doesn't already
        have one, using the template as a base and customizing with subdirectory name.

        Args:
            directory: Root directory to search
            template: Template dictionary with base metadata fields

        Returns:
            Number of sidecars created
        """
        directory = Path(directory).resolve()

        if not directory.exists() or not directory.is_dir():
            return 0

        created = 0

        # Find all subdirectories
        for subdir in directory.iterdir():
            if not subdir.is_dir():
                continue

            # Skip if already has deployment sidecar
            if deployment_has_sidecar(subdir):
                continue

            try:
                # Create metadata using template
                # Use subdirectory name as deployment_name if not in template
                deployment_name = template.get("deployment_name", subdir.name)

                metadata = create_deployment_metadata(
                    directory=subdir,
                    name=deployment_name,
                    latitude=template.get("latitude"),
                    longitude=template.get("longitude"),
                    altitude=template.get("altitude"),
                    location_name=template.get("location_name"),
                    start_date=template.get("start_date"),
                    end_date=template.get("end_date"),
                    environmental=template.get("environmental"),
                    mothbox_id=template.get("mothbox_id"),
                    firmware_version=template.get("firmware_version"),
                    custom=template.get("custom"),
                    modified_by=template.get("modified_by"),
                )

                # Write sidecar
                success = write_deployment_metadata(subdir, metadata)

                if success:
                    # Cache it
                    with self._cache_lock:
                        self._set_cache(str(subdir), metadata)

                    created += 1

                    # Record statistics
                    with self._stats_lock:
                        self._total_writes += 1

            except Exception as e:
                logger.warning(f"Failed to generate sidecar for {subdir}: {e}")

        return created

    # ========================================================================
    # Cache Management
    # ========================================================================

    def invalidate_cache(self, directory: Path | str | None = None) -> None:
        """
        Invalidate cache entry or entire cache.

        Args:
            directory: Directory path to invalidate, or None to clear entire cache
        """
        with self._cache_lock:
            if directory is None:
                # Clear entire cache
                self._cache.clear()
            else:
                # Remove specific entry
                directory_str = str(Path(directory).resolve())
                if directory_str in self._cache:
                    del self._cache[directory_str]

    def get_statistics(self) -> dict[str, Any]:
        """
        Get current cache statistics.

        Returns:
            Dictionary with cache metrics:
            - cache_hits: Number of cache hits
            - cache_misses: Number of cache misses
            - cache_evictions: Number of LRU evictions
            - cache_size: Current cache size
            - max_cache_size: Maximum cache size
            - cache_ttl: Cache TTL in seconds
            - hit_ratio: Cache hit ratio (0.0 to 1.0)
            - total_reads: Total read operations
            - total_writes: Total write operations
            - total_deletes: Total delete operations
        """
        with self._stats_lock:
            total_requests = self._cache_hits + self._cache_misses
            hit_ratio = 0.0
            if total_requests > 0:
                hit_ratio = self._cache_hits / total_requests

            with self._cache_lock:
                cache_size = len(self._cache)

            return {
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "cache_evictions": self._cache_evictions,
                "cache_size": cache_size,
                "max_cache_size": self.max_cache_size,
                "cache_ttl": self.cache_ttl,
                "hit_ratio": hit_ratio,
                "total_reads": self._total_reads,
                "total_writes": self._total_writes,
                "total_deletes": self._total_deletes,
            }

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    def _set_cache(self, directory: str, metadata: DeploymentMetadata) -> None:
        """
        Set cache entry with LRU eviction.

        Caller must hold _cache_lock.

        Args:
            directory: Directory path (absolute, resolved)
            metadata: Metadata to cache
        """
        # If updating existing entry, move to end
        if directory in self._cache:
            self._cache.move_to_end(directory)
            self._cache[directory] = (metadata, time.time())
        else:
            # Adding new entry - check if eviction needed
            if len(self._cache) >= self.max_cache_size:
                # Evict LRU (first item)
                self._cache.popitem(last=False)

                # Record eviction
                with self._stats_lock:
                    self._cache_evictions += 1

            # Add new entry
            self._cache[directory] = (metadata, time.time())


# ============================================================================
# Module exports
# ============================================================================

__all__ = [
    'DeploymentService',
]

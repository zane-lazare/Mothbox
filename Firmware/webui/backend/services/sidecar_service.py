"""
Sidecar Service with Two-Level Cache (Issue #102 - Phase B)

Provides cached access to photo sidecar metadata through a hybrid cache:
- L1: In-memory LRU cache (fast, ~1000 entries) - <10ms access
- L2: File-based cache (persistent, ~10000 entries) - <50ms access

Performance targets:
- L1 hit rate: ~60% (<10ms)
- L2 hit rate: ~15% (~50ms)
- Overall cache hit rate: >70%
- Batch processing: 1000 files < 2 seconds

Thread-safe with statistics tracking.

Usage:
    from webui.backend.services.sidecar_service import SidecarService

    service = SidecarService(cache_dir="/var/cache/mothbox")

    # Get metadata (L1 -> L2 -> disk)
    metadata = service.get_metadata("/photos/photo.jpg")

    # Update metadata (updates L1, L2, and disk)
    metadata = service.update_metadata("/photos/photo.jpg", {"species": "Actias luna"})

    # Batch operations
    results = service.batch_get_metadata(["/photos/photo1.jpg", "/photos/photo2.jpg"])
    metadata_list = service.list_metadata_for_directory("/photos", limit=50, offset=0)

    # Statistics
    stats = service.get_statistics()
    print(f"Hit ratio: {stats['hit_ratio']:.2%}")
"""

import contextlib
import hashlib
import json
import logging
import time
from collections import OrderedDict, deque
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Lock
from typing import Any

from webui.backend.lib.sidecar_metadata import (
    SidecarMetadata,
    cleanup_temp_files,
    list_photos_with_sidecars,
    read_metadata,
    write_metadata,
)
from webui.backend.lib.sidecar_metadata import (
    update_metadata as lib_update_metadata,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class CacheEntry:
    """Metadata cache entry for L1/L2 storage."""

    photo_path: str
    metadata: dict[str, Any]  # Serialized SidecarMetadata
    cached_at: float
    cache_version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CacheEntry":
        """Create from dictionary."""
        return cls(
            photo_path=data["photo_path"],
            metadata=data["metadata"],
            cached_at=data["cached_at"],
            cache_version=data.get("cache_version", "1.0"),
        )


# ============================================================================
# Sidecar Service
# ============================================================================

class SidecarService:
    """
    Two-level LRU cache for photo sidecar metadata.

    L1: In-memory cache (fast, ~1000 entries)
    L2: File-based cache (persistent, ~10000 entries)

    Performance targets:
    - L1 hit: <10ms
    - L2 hit: <50ms
    - Overall hit rate: >70%

    Thread Safety:
    ---------------
    This class uses three locks to ensure thread-safe operation:
    - _l1_lock: Protects L1 in-memory cache (OrderedDict)
    - _l2_lock: Protects L2 file-based cache operations
    - _stats_lock: Protects statistics counters

    LOCK ACQUISITION ORDER (to prevent deadlocks):
    -----------------------------------------------
    If multiple locks must be acquired, always acquire in this order:
        1. _l1_lock (first)
        2. _l2_lock (second)
        3. _stats_lock (last)

    NEVER acquire locks in a different order, as this can cause deadlocks.
    """

    def __init__(
        self,
        cache_dir: Path | str,
        l1_max_size: int = 1000,
        l2_max_size: int = 10000,
        cache_version: str = "1.0",
    ):
        """
        Initialize sidecar service with two-level cache.

        Args:
            cache_dir: Directory for L2 file-based cache
            l1_max_size: Maximum entries in L1 memory cache
            l2_max_size: Maximum entries in L2 file cache
            cache_version: Cache format version
        """
        self.cache_dir = Path(cache_dir)
        self.l1_max_size = l1_max_size
        self.l2_max_size = l2_max_size
        self.cache_version = cache_version

        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # L1: In-memory cache (LRU using OrderedDict)
        self._l1_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._l1_lock = Lock()

        # L2: File-based cache lock
        self._l2_lock = Lock()

        # Statistics tracking
        self._stats_lock = Lock()
        self._l1_hits = 0
        self._l1_misses = 0
        self._l2_hits = 0
        self._l2_misses = 0
        self._total_response_times: deque[float] = deque(maxlen=1000)

        # Clean up orphaned temp files from previous crashes
        try:
            removed = cleanup_temp_files(self.cache_dir)
            if removed > 0:
                logger.info(f"Cleaned up {removed} orphaned temp files from cache")
        except Exception as e:
            logger.warning(f"Failed to clean up temp files: {e}")

    def get_metadata(self, photo_path: str) -> SidecarMetadata | None:
        """
        Get metadata from cache (L1 -> L2 -> disk).

        Args:
            photo_path: Path to photo file

        Returns:
            SidecarMetadata if found, None otherwise
        """
        start_time = time.time()

        # Try L1 first
        entry = self._get_l1(photo_path)
        if entry:
            response_time = (time.time() - start_time) * 1000
            self._record_hit("l1", response_time)
            return SidecarMetadata.from_dict(entry.metadata)

        # L1 miss - record it
        self._record_l1_miss()

        # Try L2 next
        entry = self._get_l2(photo_path)
        if entry:
            # Promote to L1
            self._set_l1(photo_path, entry)
            response_time = (time.time() - start_time) * 1000
            self._record_hit("l2", response_time)
            return SidecarMetadata.from_dict(entry.metadata)

        # L2 miss - try disk
        self._record_l2_miss_partial()  # Partial to avoid double-counting response time
        metadata = read_metadata(photo_path)

        if metadata:
            # Cache it in L1 and L2
            entry = CacheEntry(
                photo_path=photo_path,
                metadata=metadata.to_dict(),
                cached_at=time.time(),
                cache_version=self.cache_version,
            )
            self._set_l1(photo_path, entry)
            self._set_l2(photo_path, entry)

        response_time = (time.time() - start_time) * 1000
        self._record_response_time(response_time)

        return metadata

    def set_metadata(self, photo_path: str, metadata: SidecarMetadata) -> None:
        """
        Store metadata in L1, L2, and disk sidecar.

        Args:
            photo_path: Path to photo file
            metadata: Metadata to store
        """
        # Write to disk first
        write_metadata(photo_path, metadata)

        # Create cache entry
        entry = CacheEntry(
            photo_path=photo_path,
            metadata=metadata.to_dict(),
            cached_at=time.time(),
            cache_version=self.cache_version,
        )

        # Store in L1
        self._set_l1(photo_path, entry)

        # Store in L2
        self._set_l2(photo_path, entry)

    def update_metadata(self, photo_path: str, updates: dict) -> SidecarMetadata | None:
        """
        Update metadata and cache.

        Args:
            photo_path: Path to photo file
            updates: Dictionary of fields to update

        Returns:
            Updated SidecarMetadata if successful, None if photo doesn't exist
        """
        # Check if photo exists
        photo = Path(photo_path)
        if not photo.exists():
            return None

        # Update on disk (uses lib function)
        metadata = lib_update_metadata(photo_path, updates)

        # Update cache
        if metadata:
            entry = CacheEntry(
                photo_path=photo_path,
                metadata=metadata.to_dict(),
                cached_at=time.time(),
                cache_version=self.cache_version,
            )
            self._set_l1(photo_path, entry)
            self._set_l2(photo_path, entry)

        return metadata

    def invalidate(self, photo_path: str) -> bool:
        """
        Remove photo from L1 and L2 cache.

        Args:
            photo_path: Path to photo file

        Returns:
            True if entry was found and removed, False otherwise
        """
        removed = False

        # Remove from L1
        with self._l1_lock:
            if photo_path in self._l1_cache:
                del self._l1_cache[photo_path]
                removed = True

        # Remove from L2
        cache_file = self._get_cache_file_path(photo_path)
        if cache_file.exists():
            try:
                cache_file.unlink()
                removed = True
            except Exception as e:
                logger.warning(f"Failed to remove L2 cache file {cache_file}: {e}")

        return removed

    def clear(self) -> None:
        """Clear entire cache (both L1 and L2)."""
        # Clear L1
        with self._l1_lock:
            self._l1_cache.clear()

        # Clear L2 (delete all cache files)
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    cache_file.unlink()
                except Exception as e:
                    logger.warning(f"Failed to remove L2 cache file {cache_file}: {e}")
        except Exception as e:
            logger.warning(f"Failed to clear L2 cache: {e}")

        # Reset statistics
        with self._stats_lock:
            self._l1_hits = 0
            self._l1_misses = 0
            self._l2_hits = 0
            self._l2_misses = 0
            self._total_response_times.clear()

    def get_statistics(self) -> dict:
        """
        Get current cache statistics.

        Returns:
            Dictionary with cache metrics:
            - l1_hits: L1 cache hits
            - l1_misses: L1 cache misses
            - l2_hits: L2 cache hits
            - l2_misses: L2 cache misses (complete cache misses)
            - hit_ratio: Overall cache hit ratio
        """
        with self._stats_lock:
            total_hits = self._l1_hits + self._l2_hits
            total_misses = self._l2_misses
            total_requests = total_hits + total_misses

            hit_ratio = 0.0
            if total_requests > 0:
                hit_ratio = total_hits / total_requests

            return {
                'l1_hits': self._l1_hits,
                'l1_misses': self._l1_misses,
                'l2_hits': self._l2_hits,
                'l2_misses': self._l2_misses,
                'hit_ratio': hit_ratio,
            }

    # ========================================================================
    # Batch Operations (Subtask B2)
    # ========================================================================

    def batch_get_metadata(self, photo_paths: list[str]) -> list[SidecarMetadata | None]:
        """
        Get metadata for multiple photos.

        Args:
            photo_paths: List of photo paths

        Returns:
            List of SidecarMetadata (or None if not found), in same order as input
        """
        results = []
        for photo_path in photo_paths:
            metadata = self.get_metadata(photo_path)
            results.append(metadata)
        return results

    def list_metadata_for_directory(
        self,
        directory: Path | str,
        limit: int = 50,
        offset: int = 0
    ) -> dict:
        """
        List metadata for all photos with sidecars in directory.

        Args:
            directory: Directory to search
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            Dictionary with:
            - items: List of metadata dictionaries (serialized)
            - total: Total number of photos with sidecars
            - limit: Limit used
            - offset: Offset used
            - has_next: Whether there are more results
        """
        directory = Path(directory)

        if not directory.exists():
            return {
                'items': [],
                'total': 0,
                'limit': limit,
                'offset': offset,
                'has_next': False,
            }

        # Get all photos with sidecars
        photos_with_sidecars = list_photos_with_sidecars(directory)
        total = len(photos_with_sidecars)

        # Apply pagination
        photos_page = photos_with_sidecars[offset:offset + limit]

        # Get metadata for page
        items = []
        for photo_path in photos_page:
            metadata = self.get_metadata(str(photo_path))
            if metadata:
                items.append(metadata.to_dict())

        # Check if there are more results
        has_next = (offset + limit) < total

        return {
            'items': items,
            'total': total,
            'limit': limit,
            'offset': offset,
            'has_next': has_next,
        }

    def batch_update_metadata(self, updates: list[tuple[str, dict]]) -> list[bool]:
        """
        Update multiple photos' metadata.

        Args:
            updates: List of (photo_path, updates_dict) tuples

        Returns:
            List of boolean success indicators (same order as input)
        """
        results = []
        for photo_path, update_dict in updates:
            metadata = self.update_metadata(photo_path, update_dict)
            results.append(metadata is not None)
        return results

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    def _get_l1(self, photo_path: str) -> CacheEntry | None:
        """Get from L1 memory cache with LRU update."""
        with self._l1_lock:
            if photo_path in self._l1_cache:
                # Move to end (most recently used)
                self._l1_cache.move_to_end(photo_path)
                return self._l1_cache[photo_path]
        return None

    def _set_l1(self, photo_path: str, entry: CacheEntry) -> None:
        """Set in L1 with LRU eviction."""
        with self._l1_lock:
            # If updating existing entry, move to end
            if photo_path in self._l1_cache:
                self._l1_cache.move_to_end(photo_path)
                self._l1_cache[photo_path] = entry
            else:
                # Adding new entry - check if eviction needed
                if len(self._l1_cache) >= self.l1_max_size:
                    # Evict LRU (first item)
                    self._l1_cache.popitem(last=False)

                # Add new entry
                self._l1_cache[photo_path] = entry

    def _get_l2(self, photo_path: str) -> CacheEntry | None:
        """Get from L2 file cache."""
        cache_file = self._get_cache_file_path(photo_path)

        with self._l2_lock:
            if not cache_file.exists():
                return None

            try:
                with open(cache_file) as f:
                    data = json.load(f)
                    entry = CacheEntry.from_dict(data)

                # Update file mtime for LRU tracking (non-critical)
                with contextlib.suppress(Exception):
                    cache_file.touch(exist_ok=True)

                return entry

            except Exception as e:
                logger.warning(f"Failed to read L2 cache file {cache_file}: {e}")
                # Corrupted cache file - remove it
                with contextlib.suppress(Exception):
                    cache_file.unlink()
                return None

    def _set_l2(self, photo_path: str, entry: CacheEntry) -> None:
        """Set in L2 file cache with LRU eviction.

        Note: Eviction check only occurs when adding new entries, not updates.
        This means cache may slightly exceed l2_max_size until the next new
        entry is added. This is acceptable behavior to minimize I/O overhead
        on frequently updated entries.
        """
        cache_file = self._get_cache_file_path(photo_path)

        with self._l2_lock:
            try:
                # Check if L2 eviction needed
                if not cache_file.exists():
                    self._evict_l2_if_needed()

                # Write to temp file first for atomicity
                temp_file = cache_file.with_suffix(".tmp")

                with open(temp_file, "w") as f:
                    json.dump(entry.to_dict(), f, indent=2)

                # Atomic rename
                temp_file.replace(cache_file)

            except Exception as e:
                logger.warning(f"Failed to write L2 cache file {cache_file}: {e}")

    def _get_cache_file_path(self, photo_path: str) -> Path:
        """Get cache file path (hash-based)."""
        path_hash = hashlib.sha256(photo_path.encode()).hexdigest()[:16]
        return self.cache_dir / f"{path_hash}.json"

    def _evict_l2_if_needed(self) -> None:
        """Evict L2 cache entries if cache exceeds l2_max_size.

        Uses LRU eviction based on file modification times.
        Caller must hold _l2_lock.
        """
        try:
            # Get all cache files
            cache_files = list(self.cache_dir.glob("*.json"))
            cache_size = len(cache_files)

            if cache_size >= self.l2_max_size:
                # Evict 10% of cache size
                evict_count = max(1, int(self.l2_max_size * 0.1))

                # Sort by modification time (oldest first)
                cache_files_sorted = sorted(cache_files, key=lambda f: f.stat().st_mtime)

                # Evict oldest files
                for cache_file in cache_files_sorted[:evict_count]:
                    try:
                        cache_file.unlink()
                        logger.debug(f"Evicted L2 cache file: {cache_file.name}")
                    except Exception as e:
                        logger.warning(f"Failed to evict L2 cache file {cache_file}: {e}")

        except Exception as e:
            logger.warning(f"L2 eviction failed: {e}")

    def _record_hit(self, level: str, response_time: float) -> None:
        """Record cache hit statistics."""
        with self._stats_lock:
            if level == "l1":
                self._l1_hits += 1
            elif level == "l2":
                self._l2_hits += 1
            self._total_response_times.append(response_time)

    def _record_l1_miss(self) -> None:
        """Record L1 cache miss."""
        with self._stats_lock:
            self._l1_misses += 1

    def _record_l2_miss_partial(self) -> None:
        """Record L2 cache miss (without response time)."""
        with self._stats_lock:
            self._l2_misses += 1

    def _record_response_time(self, response_time: float) -> None:
        """Record response time."""
        with self._stats_lock:
            self._total_response_times.append(response_time)


# ============================================================================
# Module exports
# ============================================================================

__all__ = [
    'SidecarService',
]

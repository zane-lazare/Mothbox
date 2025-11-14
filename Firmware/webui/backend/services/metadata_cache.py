"""
Metadata cache service with two-level LRU caching (Issue #100).

Provides fast access to photo metadata through a hybrid cache:
- L1: In-memory cache (fast, ~1000 entries) - <10ms access
- L2: File-based cache (persistent, ~10000 entries) - <50ms access

Performance targets:
- L1 hit rate: ~60% (<10ms)
- L2 hit rate: ~15% (~50ms)
- Overall cache hit rate: >70%
- Cached endpoint response: <100ms

Thread-safe with statistics tracking.
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
from collections import OrderedDict
import json
import fcntl
import time
from threading import Lock
from dataclasses import dataclass, asdict
import hashlib
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Metadata cache entry"""

    photo_path: str
    metadata: Dict[str, Any]
    cached_at: float
    cache_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheEntry":
        """Create from dictionary"""
        return cls(
            photo_path=data["photo_path"],
            metadata=data["metadata"],
            cached_at=data["cached_at"],
            cache_version=data.get("cache_version", "1.0"),
        )


@dataclass
class CacheStatistics:
    """Cache performance statistics"""

    l1_hits: int = 0
    l1_misses: int = 0
    l2_hits: int = 0
    l2_misses: int = 0
    total_hits: int = 0
    total_misses: int = 0
    hit_ratio: float = 0.0
    avg_response_time_ms: float = 0.0


class MetadataCache:
    """
    Two-level LRU cache for photo metadata.

    L1: In-memory cache (fast, ~1000 entries)
    L2: File-based cache (persistent, ~10000 entries)

    Performance targets:
    - L1 hit: <10ms
    - L2 hit: <50ms
    - Overall hit rate: >70%
    """

    def __init__(
        self,
        cache_dir: Path,
        l1_max_size: int = 1000,
        l2_max_size: int = 10000,
        cache_version: str = "1.0",
    ):
        """
        Initialize metadata cache.

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
        # OrderedDict maintains insertion order and provides move_to_end() for efficient LRU
        self._l1_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._l1_lock = Lock()

        # Statistics tracking
        self._stats_lock = Lock()
        self._l1_hits = 0
        self._l1_misses = 0
        self._l2_hits = 0
        self._l2_misses = 0
        self._total_response_times: List[float] = []

    def get(self, photo_path: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata from cache (L1 -> L2 -> None).

        Args:
            photo_path: Path to photo file

        Returns:
            Metadata dictionary if cached, None otherwise
        """
        start_time = time.time()

        # Try L1 first
        entry = self._get_l1(photo_path)
        if entry:
            response_time = (time.time() - start_time) * 1000
            self._record_hit("l1", response_time)
            return entry.metadata

        # L1 miss - record it
        self._record_l1_miss()

        # Try L2 next
        entry = self._get_l2(photo_path)
        if entry:
            # Promote to L1
            self._set_l1(photo_path, entry)
            response_time = (time.time() - start_time) * 1000
            self._record_hit("l2", response_time)
            return entry.metadata

        # L2 miss - record it
        response_time = (time.time() - start_time) * 1000
        self._record_l2_miss(response_time)
        return None

    def set(self, photo_path: str, metadata: Dict[str, Any]) -> None:
        """
        Store metadata in both L1 and L2.

        Args:
            photo_path: Path to photo file
            metadata: Metadata dictionary to cache
        """
        entry = CacheEntry(
            photo_path=photo_path,
            metadata=metadata,
            cached_at=time.time(),
            cache_version=self.cache_version,
        )

        # Store in L1
        self._set_l1(photo_path, entry)

        # Store in L2
        self._set_l2(photo_path, entry)

    def invalidate(self, photo_path: str) -> bool:
        """
        Remove photo from cache.

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
        """Clear entire cache (both L1 and L2)"""
        # Clear L1 (OrderedDict.clear() removes all entries)
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

    def get_statistics(self) -> CacheStatistics:
        """
        Get current cache statistics.

        Returns:
            CacheStatistics object with hit rates and performance metrics

        Note:
            - total_hits = L1 hits + L2 hits (data found in cache)
            - total_misses = L2 misses only (complete cache misses)
            - hit_ratio = total_hits / (total_hits + total_misses)
            - L1 misses that become L2 hits are NOT counted as total misses
        """
        with self._stats_lock:
            total_hits = self._l1_hits + self._l2_hits
            total_misses = self._l2_misses  # Only count complete cache misses
            total_requests = total_hits + total_misses

            hit_ratio = 0.0
            if total_requests > 0:
                hit_ratio = total_hits / total_requests

            avg_response_time = 0.0
            if self._total_response_times:
                avg_response_time = sum(self._total_response_times) / len(
                    self._total_response_times
                )

            return CacheStatistics(
                l1_hits=self._l1_hits,
                l1_misses=self._l1_misses,
                l2_hits=self._l2_hits,
                l2_misses=self._l2_misses,
                total_hits=total_hits,
                total_misses=total_misses,
                hit_ratio=hit_ratio,
                avg_response_time_ms=avg_response_time,
            )

    # Private helper methods

    def _get_l1(self, photo_path: str) -> Optional[CacheEntry]:
        """Get from L1 memory cache with LRU update"""
        with self._l1_lock:
            if photo_path in self._l1_cache:
                # Move to end (most recently used) - O(1) with OrderedDict
                self._l1_cache.move_to_end(photo_path)
                return self._l1_cache[photo_path]
        return None

    def _set_l1(self, photo_path: str, entry: CacheEntry) -> None:
        """Set in L1 with LRU eviction using OrderedDict"""
        with self._l1_lock:
            # If updating existing entry, move to end (most recent)
            if photo_path in self._l1_cache:
                self._l1_cache.move_to_end(photo_path)
                self._l1_cache[photo_path] = entry
            else:
                # Adding new entry - check if eviction needed
                if len(self._l1_cache) >= self.l1_max_size:
                    # Evict LRU (first item in OrderedDict)
                    self._l1_cache.popitem(last=False)

                # Add new entry (automatically goes to end)
                self._l1_cache[photo_path] = entry

    def _get_l2(self, photo_path: str) -> Optional[CacheEntry]:
        """Get from L2 file cache with locking"""
        cache_file = self._get_cache_file_path(photo_path)

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "r") as f:
                # Acquire shared lock for reading
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    data = json.load(f)
                    entry = CacheEntry.from_dict(data)
                    return entry
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            logger.warning(f"Failed to read L2 cache file {cache_file}: {e}")
            # Corrupted or invalid cache file - remove it
            try:
                cache_file.unlink()
            except Exception:
                pass
            return None

    def _set_l2(self, photo_path: str, entry: CacheEntry) -> None:
        """Set in L2 file cache with locking"""
        cache_file = self._get_cache_file_path(photo_path)

        try:
            # Write to temp file first for atomicity
            temp_file = cache_file.with_suffix(".tmp")

            with open(temp_file, "w") as f:
                # Acquire exclusive lock for writing
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(entry.to_dict(), f, indent=2)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            # Atomic rename
            temp_file.replace(cache_file)

        except Exception as e:
            logger.warning(f"Failed to write L2 cache file {cache_file}: {e}")
            # L2 write failure is non-fatal (cache is optimization)

    def _get_cache_file_path(self, photo_path: str) -> Path:
        """
        Get cache file path (hash-based).

        Uses SHA256 hash to avoid filesystem issues with long/special paths.
        """
        path_hash = hashlib.sha256(photo_path.encode()).hexdigest()[:16]
        return self.cache_dir / f"{path_hash}.json"

    def _record_hit(self, level: str, response_time: float) -> None:
        """Record cache hit statistics"""
        with self._stats_lock:
            if level == "l1":
                self._l1_hits += 1
            elif level == "l2":
                self._l2_hits += 1
            self._total_response_times.append(response_time)
            # Keep only last 1000 response times for moving average
            if len(self._total_response_times) > 1000:
                self._total_response_times.pop(0)

    def _record_l1_miss(self) -> None:
        """Record L1 cache miss"""
        with self._stats_lock:
            self._l1_misses += 1

    def _record_l2_miss(self, response_time: float) -> None:
        """Record L2 cache miss (complete cache miss)"""
        with self._stats_lock:
            self._l2_misses += 1
            self._total_response_times.append(response_time)
            # Keep only last 1000 response times for moving average
            if len(self._total_response_times) > 1000:
                self._total_response_times.pop(0)

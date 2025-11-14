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

import fcntl
import hashlib
import json
import logging
import time
from collections import OrderedDict, deque
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Metadata cache entry"""

    photo_path: str
    metadata: dict[str, Any]
    cached_at: float
    cache_version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CacheEntry":
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

    Current lock usage patterns:
    - get(): _l1_lock → _l2_lock → _stats_lock (cascading as needed)
    - set(): _l1_lock, _l2_lock (separately, no nesting)
    - Statistics: _stats_lock only (independent)

    Guidelines for future modifications:
    - If you need multiple locks, acquire in the order above
    - Keep lock scope as narrow as possible
    - Never call external code while holding locks
    - Document any new lock acquisition patterns
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

        # L2: File-based cache lock (protects eviction + file operations)
        # Prevents race conditions where eviction could delete newly written files
        self._l2_lock = Lock()

        # Statistics tracking
        self._stats_lock = Lock()
        self._l1_hits = 0
        self._l1_misses = 0
        self._l2_hits = 0
        self._l2_misses = 0
        # Use deque with maxlen for O(1) append and automatic eviction
        # Automatically evicts oldest items when maxlen is reached (no need for pop(0))
        self._total_response_times: deque[float] = deque(maxlen=1000)

    def get(self, photo_path: str) -> dict[str, Any] | None:
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

    def set(self, photo_path: str, metadata: dict[str, Any]) -> None:
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

    def _get_l1(self, photo_path: str) -> CacheEntry | None:
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

    def _get_l2(self, photo_path: str) -> CacheEntry | None:
        """
        Get from L2 file cache with LRU update.

        Thread-safe: Uses _l2_lock to prevent race conditions with eviction.
        """
        cache_file = self._get_cache_file_path(photo_path)

        # Use L2 lock to prevent eviction from deleting file during read
        with self._l2_lock:
            if not cache_file.exists():
                return None

            try:
                with open(cache_file) as f:
                    # Acquire shared lock for reading (file-level lock)
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                    try:
                        data = json.load(f)
                        entry = CacheEntry.from_dict(data)
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)

                # Update file mtime for LRU tracking (after releasing file lock)
                try:
                    cache_file.touch(exist_ok=True)
                except Exception:
                    pass  # mtime update failure is non-critical

                return entry

            except Exception as e:
                logger.warning(f"Failed to read L2 cache file {cache_file}: {e}")
                # Corrupted or invalid cache file - remove it
                try:
                    cache_file.unlink()
                except Exception:
                    pass
                return None

    def _set_l2(self, photo_path: str, entry: CacheEntry) -> None:
        """
        Set in L2 file cache with LRU eviction.

        Thread-safe: Uses _l2_lock to prevent race conditions with eviction
        and concurrent writes.
        """
        cache_file = self._get_cache_file_path(photo_path)

        # Use L2 lock to coordinate eviction and file writes
        with self._l2_lock:
            try:
                # Check if L2 eviction needed (before adding new file)
                if not cache_file.exists():
                    # Only check size when adding NEW file (not updating existing)
                    # _evict_l2_if_needed() assumes _l2_lock is already held
                    self._evict_l2_if_needed()

                # Write to temp file first for atomicity
                temp_file = cache_file.with_suffix(".tmp")

                with open(temp_file, "w") as f:
                    # Acquire exclusive lock for writing (file-level lock)
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

    def _evict_l2_if_needed(self) -> None:
        """
        Evict L2 cache entries if cache exceeds l2_max_size.

        Uses LRU eviction based on file modification times (mtime).
        Evicts oldest files first until cache size is below limit.

        Thread-safety: Caller must hold _l2_lock before calling this method.
        This prevents race conditions where multiple threads could simultaneously:
        - Read the cache file list
        - Perform eviction on the same files
        - Delete newly written files from other threads
        """
        try:
            # Get all cache files (exclude temp files)
            # Note: _l2_lock must be held by caller to prevent TOCTOU bugs
            cache_files = list(self.cache_dir.glob("*.json"))
            cache_size = len(cache_files)

            if cache_size >= self.l2_max_size:
                # Calculate how many files to evict
                # Evict 10% of cache size to avoid thrashing
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
            # Eviction failure is non-fatal (cache will continue growing)

    def _record_hit(self, level: str, response_time: float) -> None:
        """Record cache hit statistics"""
        with self._stats_lock:
            if level == "l1":
                self._l1_hits += 1
            elif level == "l2":
                self._l2_hits += 1
            # deque with maxlen automatically evicts oldest when full (atomic)
            self._total_response_times.append(response_time)

    def _record_l1_miss(self) -> None:
        """Record L1 cache miss"""
        with self._stats_lock:
            self._l1_misses += 1

    def _record_l2_miss(self, response_time: float) -> None:
        """Record L2 cache miss (complete cache miss)"""
        with self._stats_lock:
            self._l2_misses += 1
            # deque with maxlen automatically evicts oldest when full (atomic)
            self._total_response_times.append(response_time)

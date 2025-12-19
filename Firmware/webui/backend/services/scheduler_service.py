"""
Scheduler Service with LRU Cache.

Provides cached access to schedule management with thread-safe operations.
Only one schedule can be active at a time.

Performance targets:
- Cache hit rate: >80%
- Cache hit: <10ms
- Disk read: <50ms

Thread-safe with statistics tracking.

Usage:
    from webui.backend.services.scheduler_service import SchedulerService

    service = SchedulerService(cache_ttl=300)

    # Get schedule (cache -> disk)
    schedule = service.get_schedule("schedule-id")

    # List all schedules
    schedules = service.list_schedules(include_builtin=True)

    # Get active schedule
    active = service.get_active_schedule()

    # Statistics
    stats = service.get_statistics()
    print(f"Hit ratio: {stats['hit_ratio']:.2%}")
"""

import logging
import time
from collections import OrderedDict
from threading import RLock
from typing import Any

from webui.backend.lib.schedule_schema import (
    Schedule,
    ScheduleValidationError,
    validate_schedule,
)
from webui.backend.lib.schedule_storage import (
    create_schedule as storage_create,
)
from webui.backend.lib.schedule_storage import (
    delete_schedule as storage_delete,
)
from webui.backend.lib.schedule_storage import (
    is_builtin_schedule,
)
from webui.backend.lib.schedule_storage import (
    list_schedules as storage_list,
)
from webui.backend.lib.schedule_storage import (
    read_schedule as storage_read,
)
from webui.backend.lib.schedule_storage import (
    update_schedule as storage_update,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Scheduler Service
# ============================================================================


class SchedulerService:
    """
    LRU cache for schedule management.

    In-memory cache with configurable TTL and LRU eviction.
    Only one schedule can be active at a time.

    Performance targets:
    - Cache hit: <10ms
    - Disk read: <50ms
    - Hit rate: >80%

    Thread Safety:
    ---------------
    This class uses two locks to ensure thread-safe operation:
    - _cache_lock: Protects in-memory cache (OrderedDict) and active schedule tracking
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
        Initialize SchedulerService with LRU cache.

        Args:
            cache_ttl: Cache entry time-to-live in seconds (default 300)
            max_cache_size: Maximum cache entries before LRU eviction (default 100)
        """
        self.cache_ttl = cache_ttl
        self.max_cache_size = max_cache_size

        # LRU cache: schedule_id -> (Schedule, timestamp)
        self._cache: OrderedDict[str, tuple[Schedule, float]] = OrderedDict()

        # Separate cache for active schedule (O(1) lookup)
        self._active_schedule_id: str | None = None

        # Thread safety (RLock allows recursive locking)
        self._cache_lock = RLock()
        self._stats_lock = RLock()

        # Statistics tracking
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_evictions = 0
        self._total_reads = 0
        self._total_writes = 0
        self._total_deletes = 0

    # ========================================================================
    # CRUD Read Operations
    # ========================================================================

    def get_schedule(self, schedule_id: str) -> Schedule | None:
        """
        Get schedule by ID with caching.

        Args:
            schedule_id: Schedule identifier

        Returns:
            Schedule if found, None otherwise
        """
        with self._cache_lock:
            self._total_reads += 1

            # Check cache first
            if schedule_id in self._cache:
                schedule, cached_at = self._cache[schedule_id]
                if time.time() - cached_at < self.cache_ttl:
                    # Cache hit - move to end (MRU)
                    self._cache.move_to_end(schedule_id)
                    with self._stats_lock:
                        self._cache_hits += 1
                    return schedule
                else:
                    # TTL expired - remove stale entry
                    del self._cache[schedule_id]

            # Cache miss
            with self._stats_lock:
                self._cache_misses += 1

            # Read from storage
            schedule = storage_read(schedule_id)
            if schedule:
                self._set_cache(schedule_id, schedule)

            return schedule

    def list_schedules(self, include_builtin: bool = True) -> list[Schedule]:
        """
        List all schedules.

        Args:
            include_builtin: Include built-in schedules (default True)

        Returns:
            List of Schedule objects
        """
        schedules = storage_list(include_builtin=include_builtin)

        # Cache individual schedules
        with self._cache_lock:
            for schedule in schedules:
                if schedule.schedule_id not in self._cache:
                    self._set_cache(schedule.schedule_id, schedule)

        return schedules

    def _set_cache(self, schedule_id: str, schedule: Schedule) -> None:
        """
        Add schedule to cache with LRU eviction.

        MUST be called with _cache_lock held.

        Args:
            schedule_id: Schedule identifier
            schedule: Schedule object to cache
        """
        # Evict LRU entry if cache full
        while len(self._cache) >= self.max_cache_size:
            evicted_id, _ = self._cache.popitem(last=False)  # Pop oldest
            with self._stats_lock:
                self._cache_evictions += 1
            logger.debug(f"Evicted schedule {evicted_id} from cache (LRU)")

        self._cache[schedule_id] = (schedule, time.time())

    # ========================================================================
    # CRUD Write/Delete Operations
    # ========================================================================

    def create_schedule(self, schedule: Schedule) -> bool:
        """
        Create a new schedule.

        Args:
            schedule: Schedule to create

        Returns:
            True if created successfully

        Raises:
            ScheduleValidationError: If schedule validation fails
        """
        # Validate schedule
        valid, error = validate_schedule(schedule)
        if not valid:
            raise ScheduleValidationError(error)

        # Write to storage
        success = storage_create(schedule)

        if success:
            with self._cache_lock:
                self._set_cache(schedule.schedule_id, schedule)
            with self._stats_lock:
                self._total_writes += 1

        return success

    def update_schedule(self, schedule_id: str, updates: dict) -> Schedule | None:
        """
        Update a schedule with partial updates.

        Args:
            schedule_id: Schedule to update
            updates: Dict of fields to update

        Returns:
            Updated Schedule if successful, None if not found

        Raises:
            ValueError: If attempting to modify built-in schedule
        """
        # Check if built-in
        if is_builtin_schedule(schedule_id):
            raise ValueError(f"Cannot modify built-in schedule: {schedule_id}")

        # Delegate to storage
        updated = storage_update(schedule_id, updates)

        if updated:
            with self._cache_lock:
                self._set_cache(schedule_id, updated)
            with self._stats_lock:
                self._total_writes += 1

        return updated

    def delete_schedule(self, schedule_id: str) -> bool:
        """
        Delete a schedule.

        Args:
            schedule_id: Schedule to delete

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If attempting to delete built-in schedule
        """
        # Check if built-in
        if is_builtin_schedule(schedule_id):
            raise ValueError(f"Cannot delete built-in schedule: {schedule_id}")

        # Delegate to storage
        success = storage_delete(schedule_id)

        if success:
            with self._cache_lock:
                if schedule_id in self._cache:
                    del self._cache[schedule_id]
            with self._stats_lock:
                self._total_deletes += 1

            # Clear active schedule if deleted
            with self._cache_lock:
                if self._active_schedule_id == schedule_id:
                    self._active_schedule_id = None

        return success

    # ========================================================================
    # Activation/Deactivation
    # ========================================================================

    def get_active_schedule(self) -> Schedule | None:
        """
        Get the currently active schedule (O(1) lookup).

        Returns:
            Active Schedule if one is active, None otherwise
        """
        # Use cached active schedule ID for O(1) lookup
        if self._active_schedule_id is None:
            # Check storage in case of restart
            schedules = self.list_schedules()
            for schedule in schedules:
                if schedule.is_active:
                    self._active_schedule_id = schedule.schedule_id
                    return schedule
            return None

        return self.get_schedule(self._active_schedule_id)

    def activate_schedule(self, schedule_id: str) -> tuple[bool, str]:
        """
        Activate a schedule (deactivates any currently active first).

        Args:
            schedule_id: Schedule to activate

        Returns:
            (success: bool, error_message: str)
            success=True with empty error on success
            success=False with error description on failure
        """
        # Get the schedule
        schedule = self.get_schedule(schedule_id)
        if not schedule:
            return False, f"Schedule not found: {schedule_id}"

        # Check if enabled
        if not schedule.enabled:
            return False, f"Schedule is disabled: {schedule_id}"

        # Already active? Return success (idempotent)
        if schedule.is_active and self._active_schedule_id == schedule_id:
            return True, ""

        # Deactivate any currently active schedule
        if self._active_schedule_id and self._active_schedule_id != schedule_id:
            self.deactivate_schedule()

        # Update is_active flag in storage
        # For built-in schedules, we only update the in-memory state
        try:
            if not is_builtin_schedule(schedule_id):
                self.update_schedule(schedule_id, {"is_active": True})
            else:
                # Built-in: update cache entry directly
                schedule.is_active = True
                with self._cache_lock:
                    self._set_cache(schedule_id, schedule)
        except Exception as e:
            return False, f"Failed to update schedule: {e}"

        # Set active schedule ID
        with self._cache_lock:
            self._active_schedule_id = schedule_id

        # TODO: CronBridge integration
        # Apply schedule to system cron (placeholder for future Issue)
        logger.info(f"Activated schedule: {schedule_id}")

        return True, ""

    def deactivate_schedule(self) -> bool:
        """
        Deactivate the currently active schedule.

        Returns:
            True always (no-op if no active schedule)
        """
        if self._active_schedule_id is None:
            return True  # No-op

        schedule_id = self._active_schedule_id

        # Update storage if not built-in
        try:
            if not is_builtin_schedule(schedule_id):
                self.update_schedule(schedule_id, {"is_active": False})
            else:
                # Built-in: update cache only
                schedule = self.get_schedule(schedule_id)
                if schedule:
                    schedule.is_active = False
                    with self._cache_lock:
                        self._set_cache(schedule_id, schedule)
        except Exception as e:
            logger.warning(f"Failed to deactivate schedule: {e}")

        # Clear active schedule ID
        with self._cache_lock:
            self._active_schedule_id = None

        # TODO: Clear system cron (placeholder for future Issue)
        logger.info(f"Deactivated schedule: {schedule_id}")

        return True

    # ========================================================================
    # Cache Management
    # ========================================================================

    def invalidate_cache(self, schedule_id: str = None) -> None:
        """
        Invalidate cache entries.

        Args:
            schedule_id: If provided, invalidate only this entry.
                         If None, invalidate entire cache.
        """
        with self._cache_lock:
            if schedule_id is None:
                # Clear entire cache
                count = len(self._cache)
                self._cache.clear()
                logger.debug(f"Invalidated entire cache ({count} entries)")
            else:
                # Clear specific entry
                if schedule_id in self._cache:
                    del self._cache[schedule_id]
                    logger.debug(f"Invalidated cache entry: {schedule_id}")

    # ========================================================================
    # Statistics
    # ========================================================================

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
            - active_schedule_id: ID of currently active schedule (or None)
        """
        # IMPORTANT: Acquire locks in correct order to prevent deadlocks
        # Order: cache_lock first, then stats_lock (nested for atomic snapshot)
        with self._cache_lock:
            cache_size = len(self._cache)
            active_schedule_id = self._active_schedule_id

            with self._stats_lock:
                total_requests = self._cache_hits + self._cache_misses
                hit_ratio = 0.0
                if total_requests > 0:
                    hit_ratio = self._cache_hits / total_requests

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
                    "active_schedule_id": active_schedule_id,
                }


# ============================================================================
# Module exports
# ============================================================================

__all__ = [
    "SchedulerService",
]

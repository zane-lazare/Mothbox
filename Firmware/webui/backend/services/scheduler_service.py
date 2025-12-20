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

import hashlib
import json
import logging
import time
from collections import OrderedDict
from copy import deepcopy
from threading import RLock
from typing import Any

# Cron bridge for system integration (Issue #215)
from webui.backend.lib.cron_bridge import (
    apply_to_system,
    remove_from_system,
    schedule_to_cron,
)
from webui.backend.lib.schedule_schema import (
    Schedule,
    ScheduleConflictError,
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

        # Conflict cache: cache_key -> (ConflictReport, timestamp)
        # Uses longer TTL since conflict analysis is expensive
        self._conflict_cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._conflict_cache_ttl = 600  # 10 minutes
        self._max_conflict_cache_size = 50
        self._conflict_cache_hits = 0
        self._conflict_cache_misses = 0

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
            # Check cache first
            if schedule_id in self._cache:
                schedule, cached_at = self._cache[schedule_id]
                if time.time() - cached_at < self.cache_ttl:
                    # Cache hit - move to end (MRU)
                    self._cache.move_to_end(schedule_id)
                    with self._stats_lock:
                        self._cache_hits += 1
                        self._total_reads += 1
                    return schedule
                else:
                    # TTL expired - remove stale entry
                    del self._cache[schedule_id]

            # Cache miss - update stats with proper locking
            with self._stats_lock:
                self._cache_misses += 1
                self._total_reads += 1

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

        Thread Safety:
            Acquires _cache_lock when populating cache. Uses overwrite=False
            to avoid overwriting fresher entries from concurrent operations.
        """
        schedules = storage_list(include_builtin=include_builtin)

        # Cache individual schedules (skip if already cached to avoid race)
        with self._cache_lock:
            for schedule in schedules:
                self._set_cache(schedule.schedule_id, schedule, overwrite=False)

        return schedules

    def _set_cache(
        self, schedule_id: str, schedule: Schedule, overwrite: bool = True
    ) -> None:
        """
        Add schedule to cache with LRU eviction.

        MUST be called with _cache_lock held.

        Args:
            schedule_id: Schedule identifier
            schedule: Schedule object to cache
            overwrite: If False, skip if already cached (default True)
        """
        # Skip if already cached and overwrite is False
        if not overwrite and schedule_id in self._cache:
            return

        # Evict LRU entry if cache full
        while len(self._cache) >= self.max_cache_size:
            evicted_id, _ = self._cache.popitem(last=False)  # Pop oldest
            with self._stats_lock:
                self._cache_evictions += 1
            logger.debug(f"Evicted schedule {evicted_id} from cache (LRU)")

        self._cache[schedule_id] = (schedule, time.time())

    def _update_builtin_schedule_state(self, schedule_id: str, is_active: bool) -> None:
        """
        Update active state for built-in schedule (cache-only, no disk write).

        Args:
            schedule_id: Schedule identifier
            is_active: New active state
        """
        schedule = self.get_schedule(schedule_id)
        if schedule:
            schedule_copy = deepcopy(schedule)
            schedule_copy.is_active = is_active
            with self._cache_lock:
                self._set_cache(schedule_id, schedule_copy)

    # ========================================================================
    # Conflict Cache Methods
    # ========================================================================

    def _schedule_content_hash(self, schedule: Schedule) -> str:
        """
        Generate hash of schedule content for cache key.

        Uses first 8 characters of MD5 hash of schedule JSON representation.
        This ensures cache invalidation when schedule content changes.
        """
        content = json.dumps(schedule.to_dict(), sort_keys=True)
        return hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()[:8]

    def _conflict_cache_key(
        self,
        schedule: Schedule,
        preview_days: int,
        latitude: float,
        longitude: float,
        timezone_name: str,
    ) -> str:
        """
        Generate cache key for conflict detection results.

        Includes content hash to ensure cache invalidation on schedule changes.
        """
        content_hash = self._schedule_content_hash(schedule)
        return f"{schedule.schedule_id}:{content_hash}:{preview_days}:{latitude}:{longitude}:{timezone_name}"

    def _invalidate_conflict_cache(self, schedule_id: str | None = None) -> None:
        """
        Invalidate conflict cache entries.

        MUST be called with _cache_lock held.

        Args:
            schedule_id: If provided, invalidate entries for this schedule.
                         If None, invalidate entire conflict cache.
        """
        if schedule_id is None:
            count = len(self._conflict_cache)
            self._conflict_cache.clear()
            if count > 0:
                logger.debug(f"Invalidated entire conflict cache ({count} entries)")
        else:
            # Find and remove all entries for this schedule_id
            keys_to_remove = [
                key for key in self._conflict_cache
                if key.startswith(f"{schedule_id}:")
            ]
            for key in keys_to_remove:
                del self._conflict_cache[key]
            if keys_to_remove:
                logger.debug(
                    f"Invalidated {len(keys_to_remove)} conflict cache entries "
                    f"for schedule {schedule_id}"
                )

    def get_cached_conflict_report(
        self,
        schedule: Any,
        preview_days: int = 7,
        latitude: float = 0.0,
        longitude: float = 0.0,
        timezone_name: str = "UTC",
    ) -> Any:
        """
        Get conflict report with caching.

        Args:
            schedule: Schedule to analyze
            preview_days: Number of days to preview
            latitude: Location latitude for solar calculations
            longitude: Location longitude for solar calculations
            timezone_name: Timezone for time resolution

        Returns:
            ConflictReport object (cached or freshly computed)
        """
        from webui.backend.lib.schedule_conflict import detect_conflicts

        cache_key = self._conflict_cache_key(
            schedule, preview_days, latitude, longitude, timezone_name
        )

        with self._cache_lock:
            # Check cache first
            if cache_key in self._conflict_cache:
                report, cached_at = self._conflict_cache[cache_key]
                if time.time() - cached_at < self._conflict_cache_ttl:
                    # Cache hit - move to end (MRU)
                    self._conflict_cache.move_to_end(cache_key)
                    with self._stats_lock:
                        self._conflict_cache_hits += 1
                    logger.debug(f"Conflict cache hit for {schedule.schedule_id}")
                    return report
                else:
                    # TTL expired - remove stale entry
                    del self._conflict_cache[cache_key]

            # Cache miss - update stats
            with self._stats_lock:
                self._conflict_cache_misses += 1

        # Compute conflict report (outside lock for performance)
        report = detect_conflicts(
            schedule, preview_days, latitude, longitude, timezone_name
        )

        # Cache the result
        with self._cache_lock:
            # Evict LRU entry if cache full
            while len(self._conflict_cache) >= self._max_conflict_cache_size:
                evicted_key, _ = self._conflict_cache.popitem(last=False)
                logger.debug(f"Evicted conflict cache entry: {evicted_key}")

            self._conflict_cache[cache_key] = (report, time.time())
            logger.debug(f"Cached conflict report for {schedule.schedule_id}")

        return report

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
            ScheduleValidationError: If updated schedule fails validation
        """
        # Check if built-in
        if is_builtin_schedule(schedule_id):
            raise ValueError(f"Cannot modify built-in schedule: {schedule_id}")

        # Delegate to storage
        updated = storage_update(schedule_id, updates)

        if updated:
            # Defense-in-depth: validate before caching
            valid, error = validate_schedule(updated)
            if not valid:
                logger.error(f"Updated schedule failed validation: {error}")
                # Invalidate any stale cache entry
                with self._cache_lock:
                    if schedule_id in self._cache:
                        del self._cache[schedule_id]
                # Raise exception with validation error instead of silent None
                raise ScheduleValidationError(f"Validation failed: {error}")

            with self._cache_lock:
                self._set_cache(schedule_id, updated)
                # Invalidate conflict cache since schedule changed
                self._invalidate_conflict_cache(schedule_id)
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
                # Invalidate conflict cache since schedule is deleted
                self._invalidate_conflict_cache(schedule_id)
                if self._active_schedule_id == schedule_id:
                    self._active_schedule_id = None
                with self._stats_lock:
                    self._total_deletes += 1

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
        if self._active_schedule_id is not None:
            schedule = self.get_schedule(self._active_schedule_id)
            if schedule is None:
                # Schedule was deleted externally - clear the stale ID
                with self._cache_lock:
                    self._active_schedule_id = None
            return schedule

        # Check storage in case of restart
        schedules = self.list_schedules()
        active_schedules = [s for s in schedules if s.is_active]

        if len(active_schedules) > 1:
            # Data corruption: multiple schedules marked active
            active_ids = [s.schedule_id for s in active_schedules]
            logger.warning(
                f"Multiple active schedules detected (data corruption): {active_ids}. "
                f"Using first one: {active_ids[0]}"
            )

        if active_schedules:
            self._active_schedule_id = active_schedules[0].schedule_id
            return active_schedules[0]
        return None

    def activate_schedule(
        self,
        schedule_id: str,
        check_conflicts: bool = True,
        latitude: float = 0.0,
        longitude: float = 0.0,
        timezone_name: str = "UTC",
    ) -> tuple[bool, str]:
        """
        Activate a schedule (deactivates any currently active first).

        Optionally checks for schedule conflicts before activation. Conflict
        detection analyzes the next 7 days of scheduled executions to find
        resource contention (e.g., camera, GPS, GPIO) issues.

        Args:
            schedule_id: Schedule to activate
            check_conflicts: If True, validate schedule for conflicts before
                            activation. Default True. Set False to skip check.
            latitude: Location latitude for solar calculations (default 0.0)
            longitude: Location longitude for solar calculations (default 0.0)
            timezone_name: Timezone for time resolution (default "UTC")

        Returns:
            (success: bool, error_message: str)
            success=True with empty error on success
            success=False with error description on failure (includes conflict info)
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

        # Check for conflicts before activation (Issue #213)
        # Uses cached conflict report to avoid redundant computation
        if check_conflicts:
            try:
                from webui.backend.lib.schedule_conflict import SEVERITY_ERROR

                report = self.get_cached_conflict_report(
                    schedule,
                    preview_days=7,
                    latitude=latitude,
                    longitude=longitude,
                    timezone_name=timezone_name,
                )
                if report.has_blocking_conflicts:
                    blocking = [c for c in report.conflicts if c.severity == SEVERITY_ERROR]
                    messages = [c.message for c in blocking[:3]]
                    error = (
                        f"Schedule has {len(blocking)} blocking conflict(s): "
                        + "; ".join(messages)
                    )
                    raise ScheduleConflictError(f"Conflict detected: {error}")
            except ImportError:
                # Conflict detection module not available - skip check
                logger.warning("Conflict detection module not available, skipping check")
            except ScheduleConflictError:
                # Re-raise conflict errors for caller to handle
                raise
            except Exception as e:
                logger.exception(f"Error during conflict check: {e}")
                return False, f"Conflict check failed: {e}"

        # Deactivate any currently active schedule
        if self._active_schedule_id and self._active_schedule_id != schedule_id:
            self.deactivate_schedule()

        # Update is_active flag in storage
        # For built-in schedules, we only update the in-memory state
        try:
            if not is_builtin_schedule(schedule_id):
                self.update_schedule(schedule_id, {"is_active": True})
            else:
                self._update_builtin_schedule_state(schedule_id, True)
        except Exception as e:
            logger.exception(f"Failed to update schedule: {e}")
            return False, f"Failed to update schedule: {e}"

        # Set active schedule ID
        with self._cache_lock:
            self._active_schedule_id = schedule_id

        # Apply schedule to system cron (Issue #215)
        try:
            result = schedule_to_cron(
                schedule,
                latitude=latitude,
                longitude=longitude,
                timezone_name=timezone_name,
            )
            if result.errors:
                # Required mode: fail activation if cron conversion has errors
                # Rollback the is_active state
                try:
                    if not is_builtin_schedule(schedule_id):
                        self.update_schedule(schedule_id, {"is_active": False})
                    else:
                        self._update_builtin_schedule_state(schedule_id, False)
                except Exception:
                    pass  # Best effort rollback
                with self._cache_lock:
                    self._active_schedule_id = None
                return False, f"Cron conversion failed: {'; '.join(result.errors)}"

            apply_to_system(
                entries=result.entries,
                schedule_id=schedule_id,
                set_rtc=True,
            )
            logger.info(
                f"Activated schedule: {schedule_id} "
                f"({len(result.entries)} cron entries applied)"
            )
        except Exception as e:
            # Required mode: fail activation if cron cannot be applied
            logger.error(f"Failed to apply cron entries: {e}")
            # Rollback the is_active state
            try:
                if not is_builtin_schedule(schedule_id):
                    self.update_schedule(schedule_id, {"is_active": False})
                else:
                    self._update_builtin_schedule_state(schedule_id, False)
            except Exception:
                pass  # Best effort rollback
            with self._cache_lock:
                self._active_schedule_id = None
            return False, f"Failed to apply schedule to system: {e}"

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
                self._update_builtin_schedule_state(schedule_id, False)
        except Exception:
            logger.exception(f"Failed to deactivate schedule {schedule_id}")

        # Clear active schedule ID
        with self._cache_lock:
            self._active_schedule_id = None

        # Clear system cron (Issue #215)
        try:
            remove_from_system(clear_rtc=True)
        except Exception as e:
            logger.error(f"Failed to remove cron jobs: {e}")
            # Still proceed with deactivation - don't block on cron removal failure

        logger.info(f"Deactivated schedule: {schedule_id}")

        return True

    # ========================================================================
    # Cache Management
    # ========================================================================

    def invalidate_cache(self, schedule_id: str = None) -> None:
        """
        Invalidate cache entries (both schedule cache and conflict cache).

        Args:
            schedule_id: If provided, invalidate only this entry.
                         If None, invalidate entire cache.
        """
        with self._cache_lock:
            if schedule_id is None:
                # Clear entire schedule cache
                count = len(self._cache)
                self._cache.clear()
                logger.debug(f"Invalidated entire cache ({count} entries)")
                # Also clear entire conflict cache
                self._invalidate_conflict_cache()
            else:
                # Clear specific schedule entry
                if schedule_id in self._cache:
                    del self._cache[schedule_id]
                    logger.debug(f"Invalidated cache entry: {schedule_id}")
                # Also clear conflict cache for this schedule
                self._invalidate_conflict_cache(schedule_id)

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
            - conflict_cache_size: Size of conflict detection cache
            - conflict_cache_hits: Number of conflict cache hits
            - conflict_cache_misses: Number of conflict cache misses
            - conflict_cache_hit_ratio: Conflict cache hit ratio (0.0 to 1.0)
        """
        # IMPORTANT: Acquire locks in correct order to prevent deadlocks
        # Order: cache_lock first, then stats_lock (nested for atomic snapshot)
        with self._cache_lock:
            cache_size = len(self._cache)
            conflict_cache_size = len(self._conflict_cache)
            active_schedule_id = self._active_schedule_id

            with self._stats_lock:
                total_requests = self._cache_hits + self._cache_misses
                hit_ratio = 0.0
                if total_requests > 0:
                    hit_ratio = self._cache_hits / total_requests

                conflict_total = self._conflict_cache_hits + self._conflict_cache_misses
                conflict_hit_ratio = 0.0
                if conflict_total > 0:
                    conflict_hit_ratio = self._conflict_cache_hits / conflict_total

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
                    "conflict_cache_size": conflict_cache_size,
                    "conflict_cache_hits": self._conflict_cache_hits,
                    "conflict_cache_misses": self._conflict_cache_misses,
                    "conflict_cache_hit_ratio": conflict_hit_ratio,
                }


# ============================================================================
# Module exports
# ============================================================================

__all__ = [
    "SchedulerService",
]

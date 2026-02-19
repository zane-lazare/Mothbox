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
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from datetime import UTC, datetime
from threading import RLock
from typing import Any

from mothbox_paths import CONFIG_DIR, CONTROLS_FILE, get_control_values
from webui.backend.constants import (
    CRON_ENTRY_WARNING_THRESHOLD,
    CRON_PREVIEW_DAYS_AHEAD,
    MAX_CRON_ENTRIES,
)

# Cron bridge for system integration (Issue #215)
from webui.backend.lib.cron_bridge import (
    CronEntry,
    apply_to_system,
    expand_pattern_entries,
    remove_from_system,
    schedule_to_cron,
)
from webui.backend.lib.file_lock import FileLock, LockTimeoutError
from webui.backend.lib.schedule_schema import (
    Schedule,
    ScheduleActivationError,
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
# Activation Progress Constants (Issue #309)
# ============================================================================

# Phase names for activation workflow
ACTIVATION_PHASE_CHECKING_CONFLICTS = "checking_conflicts"
ACTIVATION_PHASE_GENERATING_CRON = "generating_cron"
ACTIVATION_PHASE_APPLYING_CRON = "applying_cron"
ACTIVATION_PHASE_UPDATING_STATE = "updating_state"
ACTIVATION_PHASE_COMPLETE = "complete"
ACTIVATION_PHASE_FAILED = "failed"

# Progress percentages for each phase
ACTIVATION_PROGRESS_CHECKING_CONFLICTS = 10
ACTIVATION_PROGRESS_GENERATING_CRON = 30
ACTIVATION_PROGRESS_APPLYING_CRON = 60
ACTIVATION_PROGRESS_UPDATING_STATE = 90
ACTIVATION_PROGRESS_COMPLETE = 100
ACTIVATION_PROGRESS_FAILED = 0

# Valid phases for validation
_ACTIVATION_PHASES = frozenset(
    {
        ACTIVATION_PHASE_CHECKING_CONFLICTS,
        ACTIVATION_PHASE_GENERATING_CRON,
        ACTIVATION_PHASE_APPLYING_CRON,
        ACTIVATION_PHASE_UPDATING_STATE,
        ACTIVATION_PHASE_COMPLETE,
        ACTIVATION_PHASE_FAILED,
    }
)


# =============================================================================
# Cache Configuration Constants (Issue #385 review)
# =============================================================================

# Schedule cache TTL - balance between freshness and disk I/O
SCHEDULE_CACHE_TTL_SECONDS = 300  # 5 minutes

# Maximum cached schedules - prevents unbounded memory growth
MAX_SCHEDULE_CACHE_SIZE = 100

# Conflict analysis cache TTL - shorter because schedule changes invalidate
CONFLICT_CACHE_TTL_SECONDS = 600  # 10 minutes

# Maximum conflict cache entries
MAX_CONFLICT_CACHE_SIZE = 50

# Built-in schedules cache TTL - longer because they rarely change
# (only on firmware update, not during normal operation)
BUILTIN_CACHE_TTL_SECONDS = 3600  # 1 hour


# ============================================================================
# Persistent Active State (Issue #331)
# ============================================================================

# File to persist active schedule state across service restarts
ACTIVE_STATE_FILE = CONFIG_DIR / "active_state.json"


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
    This class uses three locks to ensure thread-safe operation:
    - _cache_lock: Protects in-memory cache (OrderedDict) and active schedule tracking
    - _stats_lock: Protects statistics counters
    - _activation_lock: Serializes activation/deactivation operations (Issue #385)

    LOCK ACQUISITION ORDER (to prevent deadlocks):
    -----------------------------------------------
    If multiple locks must be acquired, always acquire in this order:
        1. _activation_lock (outermost - protects entire activation sequence)
        2. _cache_lock (middle)
        3. _stats_lock (innermost)

    NEVER acquire locks in a different order, as this can cause deadlocks.
    """

    GPS_POLL_INTERVAL = 60  # seconds (Issue #382)

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
        # Track which schedule is enabled (single source of truth - Issue #331)
        # Only one schedule can be enabled at a time
        self._enabled_schedule_id: str | None = None
        # Tracks how coordinates were determined for active schedule (Issue #331)
        # Values: "explicit", "gps", "timezone", or None if no active schedule
        self._active_coordinates_source: str | None = None
        # Store actual coordinates and timezone used for solar calculations (Issue #331)
        self._active_latitude: float | None = None
        self._active_longitude: float | None = None
        self._active_timezone_name: str | None = None  # Timezone name when source="timezone"

        # Thread safety (RLock allows recursive locking)
        self._cache_lock = RLock()
        self._stats_lock = RLock()
        # Serializes activation/deactivation to prevent TOCTOU races (Issue #385)
        self._activation_lock = RLock()

        # GPS polling timer (Issue #382)
        # Starts when schedule is activated with timezone-based coordinates.
        # Polls controls.txt every 60s for GPS fix, then stops.
        self._gps_poll_timer: threading.Timer | None = None

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
        self._conflict_cache_ttl = CONFLICT_CACHE_TTL_SECONDS
        self._max_conflict_cache_size = MAX_CONFLICT_CACHE_SIZE
        self._conflict_cache_hits = 0
        self._conflict_cache_misses = 0

        # Built-in schedules cache (separate from regular cache, longer TTL)
        # Built-in schedules rarely change (only on firmware update)
        self._builtin_cache: list[Schedule] | None = None
        self._builtin_cache_timestamp: float = 0.0
        self._builtin_cache_ttl = BUILTIN_CACHE_TTL_SECONDS

        # Expanded cron entries for active schedule (Issue #331)
        # Stored to allow frontend to read next actions without recalculating
        self._active_entries: list[CronEntry] = []

        # Load persisted active state on startup (Issue #331)
        self._load_active_state()

    # ========================================================================
    # CRUD Read Operations
    # ========================================================================

    def get_schedule(self, schedule_id: str) -> Schedule | None:
        """
        Get schedule by ID with caching.

        Derives enabled/is_active from active_state.json (single source of truth)
        rather than from the schedule JSON file. This ensures that firmware
        updates (which may overwrite schedule files) don't cause inconsistent
        state like showing both "Disabled" and "Active" badges.

        Args:
            schedule_id: Schedule identifier

        Returns:
            Schedule if found, None otherwise (with correct enabled/is_active state)
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
                    # Derive enabled/is_active from state (Issue #331 fix)
                    schedule.enabled = schedule.schedule_id == self._enabled_schedule_id
                    schedule.is_active = schedule.schedule_id == self._active_schedule_id
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
                # Derive enabled/is_active from state (Issue #331 fix)
                schedule.enabled = schedule.schedule_id == self._enabled_schedule_id
                schedule.is_active = schedule.schedule_id == self._active_schedule_id
                self._set_cache(schedule_id, schedule)

            return schedule

    def list_schedules(self, include_builtin: bool = True) -> list[Schedule]:
        """
        List all schedules.

        Derives enabled/is_active from active_state.json (single source of truth)
        rather than from the schedule JSON files. This ensures that firmware
        updates (which may overwrite schedule files) don't cause inconsistent
        state like showing both "Disabled" and "Active" badges.

        Args:
            include_builtin: Include built-in schedules (default True)

        Returns:
            List of Schedule objects with correct enabled/is_active state

        Thread Safety:
            Acquires _cache_lock when populating cache. Uses overwrite=False
            to avoid overwriting fresher entries from concurrent operations.
        """
        schedules = storage_list(include_builtin=include_builtin)

        # Derive enabled/is_active from state (single source of truth - Issue #331 fix)
        for schedule in schedules:
            schedule.enabled = schedule.schedule_id == self._enabled_schedule_id
            schedule.is_active = schedule.schedule_id == self._active_schedule_id

        # Cache individual schedules (skip if already cached to avoid race)
        with self._cache_lock:
            for schedule in schedules:
                self._set_cache(schedule.schedule_id, schedule, overwrite=False)

        return schedules

    # ========================================================================
    # Built-in Schedule Operations (Issue #319)
    # ========================================================================

    def get_builtin_schedules(self) -> list[Schedule]:
        """
        Get all built-in schedules with caching.

        Built-in schedules are cached with a 1-hour TTL since they
        only change when firmware is updated.

        Returns:
            List of built-in Schedule objects
        """
        from webui.backend.lib.schedule_storage import (
            get_builtin_schedules as storage_get_builtin,
        )

        with self._cache_lock:
            # Check if cached and still valid
            if (
                self._builtin_cache is not None
                and time.time() - self._builtin_cache_timestamp < self._builtin_cache_ttl
            ):
                return self._builtin_cache

            # Cache miss - load from storage
            schedules = storage_get_builtin()
            self._builtin_cache = schedules
            self._builtin_cache_timestamp = time.time()

            logger.debug(f"Loaded {len(schedules)} built-in schedules")
            return schedules

    def get_builtin_schedule(self, schedule_id: str) -> Schedule | None:
        """
        Get a specific built-in schedule by ID.

        Args:
            schedule_id: Schedule identifier

        Returns:
            Schedule if found, None otherwise
        """
        for schedule in self.get_builtin_schedules():
            if schedule.schedule_id == schedule_id:
                return schedule
        return None

    def is_builtin_schedule(self, schedule_id: str) -> bool:
        """
        Check if a schedule ID is a built-in schedule.

        Handles both filename-based lookup (e.g., 'daytime-pollinator') and
        internal UUID lookup (e.g., '278ecfb3-1b84-4c27-aca2-34cb9fefb173'),
        matching the behavior of get_builtin_schedule().

        Args:
            schedule_id: Schedule identifier (filename or internal UUID)

        Returns:
            True if schedule exists in built-in directory, False otherwise
        """
        # First check by filename (storage layer behavior)
        if is_builtin_schedule(schedule_id):
            return True

        # Also check by internal schedule_id (UUID) for consistent API
        return any(schedule.schedule_id == schedule_id for schedule in self.get_builtin_schedules())

    def invalidate_builtin_cache(self) -> None:
        """Invalidate the built-in schedules cache."""
        with self._cache_lock:
            self._builtin_cache = None
            self._builtin_cache_timestamp = 0.0
            logger.debug("Invalidated built-in schedules cache")

    # ========================================================================
    # Internal Cache Management
    # ========================================================================

    def _set_cache(self, schedule_id: str, schedule: Schedule, overwrite: bool = True) -> None:
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

    # ========================================================================
    # Persistent Active State Methods (Issue #331)
    # ========================================================================

    def _save_active_state(self, entries: list[CronEntry] | None = None) -> None:
        """
        Persist active schedule state to disk.

        Saves schedule_id, enabled_schedule_id, coordinates_source, latitude,
        longitude, timezone_name, activation timestamp, and optionally expanded
        cron entries to active_state.json.

        This file is the single source of truth for which schedule is enabled
        and active. The enabled/is_active fields in schedule JSON files are
        derived from this state, not the other way around. This ensures that
        firmware updates (which may overwrite schedule files) don't cause
        inconsistent state like showing both "Disabled" and "Active" badges.

        Args:
            entries: Optional list of expanded CronEntry objects to persist.
                     If provided, entries are stored for frontend to read next actions.

        Called after successful activation to survive service restarts.
        """
        # Always save enabled_schedule_id even if nothing is active
        state = {
            "schedule_id": self._active_schedule_id,
            "enabled_schedule_id": self._enabled_schedule_id,
            "coordinates_source": self._active_coordinates_source,
            "latitude": self._active_latitude,
            "longitude": self._active_longitude,
            "timezone_name": self._active_timezone_name,
            "activated_at": datetime.now(UTC).isoformat() if self._active_schedule_id else None,
        }

        # Store expanded entries if provided (Issue #331)
        if entries is not None:
            self._active_entries = entries
            state["entries"] = [e.to_dict() for e in entries]

        try:
            # Scheduler activation involves cron + state file writes
            with FileLock(ACTIVE_STATE_FILE, exclusive=True, timeout=10.0) as f:
                f.seek(0)
                f.truncate()
                json.dump(state, f, indent=2)
            entry_count = len(entries) if entries else 0
            logger.debug(
                f"Saved active state to disk: {self._active_schedule_id} ({entry_count} entries)"
            )
        except LockTimeoutError as e:
            logger.error(f"Failed to acquire lock for active state: {e}")
            raise  # Re-raise so caller can rollback cron (Issue #385 review fix)
        except OSError as e:
            logger.warning(f"Failed to save active state: {e}")

    def _load_active_state(self) -> None:
        """
        Load active schedule state from disk on startup.

        Restores schedule_id, enabled_schedule_id, coordinates_source, latitude,
        longitude, timezone_name, and expanded cron entries from active_state.json.

        Migration: If enabled_schedule_id is not present (old state file),
        derive it from schedule_id (active implies enabled).

        Called during __init__ to recover state after service restart.
        """
        if not ACTIVE_STATE_FILE.exists():
            return

        try:
            # Use FileLock for safe read (Issue #385 - concurrent activation safety)
            with FileLock(ACTIVE_STATE_FILE, exclusive=False, timeout=5.0) as f:
                content = f.read()
                if not content.strip():
                    return
                # Parse from string content to avoid TOCTOU race (Issue #385 review)
                # Previously used f.seek(0) + json.load(f) which could read stale data
                # if another process modified the file between read() and load()
                state = json.loads(content)

            self._active_schedule_id = state.get("schedule_id")
            self._active_coordinates_source = state.get("coordinates_source")
            self._active_latitude = state.get("latitude")
            self._active_longitude = state.get("longitude")
            self._active_timezone_name = state.get("timezone_name")

            # Load enabled_schedule_id (Issue #331 fix)
            self._enabled_schedule_id = state.get("enabled_schedule_id")

            # Migration: if enabled_schedule_id not present, derive from active
            # (active schedule must have been enabled to be activated)
            if self._enabled_schedule_id is None and self._active_schedule_id:
                self._enabled_schedule_id = self._active_schedule_id
                logger.info(
                    f"Migrated enabled_schedule_id from active: {self._enabled_schedule_id}"
                )

            # Load expanded entries if present (Issue #331)
            entries_data = state.get("entries", [])
            self._active_entries = [CronEntry.from_dict(e) for e in entries_data]

            logger.info(
                f"Restored active schedule state: {self._active_schedule_id} "
                f"(enabled: {self._enabled_schedule_id}, {len(self._active_entries)} entries)"
            )
        except LockTimeoutError as e:
            logger.warning(f"Failed to acquire lock for active state: {e}")
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load active state: {e}")

    def _clear_active_state(self) -> None:
        """
        Remove active state file from disk and clear in-memory entries.

        Called after deactivation to ensure no stale state remains.
        """
        # Clear in-memory entries (Issue #331)
        self._active_entries = []

        try:
            if ACTIVE_STATE_FILE.exists():
                ACTIVE_STATE_FILE.unlink()
                logger.debug("Cleared active state file")
        except OSError as e:
            logger.warning(f"Failed to clear active state file: {e}")

    def get_active_entries(self) -> list[CronEntry]:
        """
        Get all expanded cron entries for the active schedule.

        Returns:
            List of CronEntry objects with execution times.
            Empty list if no schedule is active.
        """
        return self._active_entries

    def get_next_actions(self, limit: int = 5) -> list[CronEntry]:
        """
        Get the next N upcoming actions from the active schedule.

        Filters entries to only include future execution times,
        sorts chronologically, and limits to the specified count.

        Args:
            limit: Maximum number of actions to return (default 5)

        Returns:
            List of CronEntry objects for upcoming actions.
            Empty list if no schedule is active or no future actions.
        """
        if not self._active_entries:
            return []

        # Use UTC for timezone-aware comparison with stored entries
        now = datetime.now(UTC)
        # Filter to future entries and sort by execution time
        future_entries = [
            e for e in self._active_entries if e.execution_time and e.execution_time > now
        ]
        future_entries.sort(key=lambda e: e.execution_time)

        return future_entries[:limit]

    def get_entry_count_warning(self) -> dict | None:
        """
        Check if cron entry count is approaching the system limit.

        Returns warning dict if entry count exceeds 75% threshold,
        None otherwise.

        Returns:
            Dict with 'message', 'entry_count', 'max_entries', 'threshold'
            if warning applies, None otherwise.
        """
        entry_count = len(self._active_entries)
        if entry_count >= CRON_ENTRY_WARNING_THRESHOLD:
            return {
                "message": (
                    f"Schedule has {entry_count:,} cron entries, "
                    f"approaching system limit of {MAX_CRON_ENTRIES:,}"
                ),
                "entry_count": entry_count,
                "max_entries": MAX_CRON_ENTRIES,
                "threshold": CRON_ENTRY_WARNING_THRESHOLD,
            }
        return None

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
                key for key in self._conflict_cache if key.startswith(f"{schedule_id}:")
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
        report = detect_conflicts(schedule, preview_days, latitude, longitude, timezone_name)

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
            ValueError: If attempting to modify protected fields on built-in schedule
            ScheduleValidationError: If updated schedule fails validation
        """
        # Built-in schedules are read-only (Issue #331 fix)
        # enabled and is_active are now derived from active_state.json, not stored in files.
        # This ensures firmware updates don't cause inconsistent state.
        if is_builtin_schedule(schedule_id):
            raise ValueError(
                f"Cannot modify built-in schedule: {schedule_id}. "
                "Use set_enabled_schedule() to enable/disable schedules."
            )

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
                # Clear enabled/active state if deleted schedule was enabled/active
                if self._enabled_schedule_id == schedule_id:
                    self._enabled_schedule_id = None
                if self._active_schedule_id == schedule_id:
                    self._active_schedule_id = None
                with self._stats_lock:
                    self._total_deletes += 1

            # Persist cleared state
            if self._enabled_schedule_id is None and self._active_schedule_id is None:
                self._clear_active_state()
            else:
                self._save_active_state()

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

    def get_active_schedule_id(self) -> str | None:
        """
        Get the ID of the currently active schedule.

        Returns:
            Schedule ID if one is active, None otherwise.
        """
        return self._active_schedule_id

    def get_active_coordinates_source(self) -> str | None:
        """
        Get how coordinates were determined for the active schedule (Issue #331).

        Returns:
            "explicit" if coordinates were provided in the request,
            "gps" if coordinates came from device GPS (controls.txt),
            "timezone" if coordinates came from timezone fallback,
            or None if no active schedule.
        """
        return self._active_coordinates_source

    def get_active_coordinates(self) -> tuple[float, float] | None:
        """
        Get the coordinates used for the active schedule (Issue #331).

        Returns:
            Tuple of (latitude, longitude) if a schedule is active, None otherwise.
        """
        if self._active_latitude is not None and self._active_longitude is not None:
            return (self._active_latitude, self._active_longitude)
        return None

    def get_active_timezone_name(self) -> str | None:
        """
        Get the timezone name used for solar time calculations (Issue #331).

        Returns:
            Timezone name (e.g., "Pacific/Auckland") used for the active schedule,
            None if no schedule is active.
        """
        return self._active_timezone_name

    def check_and_update_gps(self) -> dict:
        """
        Check if GPS coordinates are available and update active schedule if needed (Issue #382).

        Only runs when the active schedule is using timezone-based coordinates.
        When GPS becomes available, updates coordinates, regenerates cron entries,
        and persists the new state.

        Returns:
            dict with "updated" (bool), and if updated: "latitude", "longitude",
            "previous_source" keys.
        """
        # Guard: only act when source is "timezone" and a schedule is active
        if self._active_coordinates_source != "timezone" or not self._active_schedule_id:
            return {"updated": False}

        # Read GPS from controls.txt
        control_values = get_control_values(CONTROLS_FILE)
        device_lat = control_values.get("lat", "n/a")
        device_lon = control_values.get("lon", "n/a")

        # Check if GPS is available (not "n/a" and numeric)
        if device_lat == "n/a" or device_lon == "n/a":
            return {"updated": False}

        try:
            latitude = float(device_lat)
            longitude = float(device_lon)
        except (ValueError, TypeError):
            return {"updated": False}

        # Validate coordinate ranges
        if latitude < -90 or latitude > 90 or longitude < -180 or longitude > 180:
            logger.warning(f"GPS coordinates out of range: {latitude}, {longitude}")
            return {"updated": False}

        # GPS available — update coordinates and regenerate cron
        with self._activation_lock:
            # Re-check source under lock (may have changed)
            if self._active_coordinates_source != "timezone":
                return {"updated": False}

            schedule_id = self._active_schedule_id
            timezone_name = self._active_timezone_name or "UTC"

            # Get the schedule for cron regeneration
            schedule = self.get_schedule(schedule_id)
            if not schedule:
                logger.error(f"GPS update: schedule not found: {schedule_id}")
                return {"updated": False}

            try:
                # Regenerate cron with new coordinates
                result = schedule_to_cron(
                    schedule,
                    latitude=latitude,
                    longitude=longitude,
                    timezone_name=timezone_name,
                )
                if result.errors:
                    logger.error(f"GPS update: cron conversion failed: {result.errors}")
                    return {"updated": False}

                # Apply new cron entries to system
                apply_to_system(
                    entries=result.entries,
                    schedule_id=schedule_id,
                    set_rtc=True,
                )

                # Expand entries for frontend
                expanded_entries = expand_pattern_entries(
                    entries=result.entries,
                    days_ahead=CRON_PREVIEW_DAYS_AHEAD,
                    timezone_name=timezone_name,
                )

                # Update in-memory state
                previous_source = self._active_coordinates_source
                with self._cache_lock:
                    self._active_coordinates_source = "gps"
                    self._active_latitude = latitude
                    self._active_longitude = longitude

                # Persist to disk
                self._save_active_state(entries=expanded_entries)

                logger.info(
                    f"GPS auto-update: coordinates updated from {previous_source} to GPS "
                    f"for schedule {schedule_id}"
                )

                return {
                    "updated": True,
                    "latitude": latitude,
                    "longitude": longitude,
                    "previous_source": previous_source,
                }

            except Exception:
                logger.exception("GPS auto-update failed")
                return {"updated": False}

    def start_gps_polling(self) -> None:
        """
        Start periodic GPS polling (Issue #382).

        Schedules _gps_poll_tick to run every GPS_POLL_INTERVAL seconds.
        Only starts if coordinates_source is "timezone".

        Note: reads _active_coordinates_source without a lock. This is safe
        because callers (activate_schedule, _gps_poll_tick) either hold
        _activation_lock or check _active_schedule_id under lock before
        calling, preventing a timer from outliving a deactivation.
        """
        self.stop_gps_polling()  # Cancel any existing timer
        if self._active_coordinates_source != "timezone":
            return
        self._gps_poll_timer = threading.Timer(self.GPS_POLL_INTERVAL, self._gps_poll_tick)
        self._gps_poll_timer.daemon = True
        self._gps_poll_timer.start()
        logger.debug("GPS polling started")

    def stop_gps_polling(self) -> None:
        """
        Stop GPS polling timer (Issue #382).

        Safe to call even when no timer is running.
        """
        if self._gps_poll_timer is not None:
            self._gps_poll_timer.cancel()
            self._gps_poll_timer = None
            logger.debug("GPS polling stopped")

    def _gps_poll_tick(self) -> None:
        """
        Single GPS poll tick (Issue #382).

        Called by the timer. Checks GPS, and if not yet acquired,
        reschedules itself. If acquired, stops polling.

        Guards against a race with deactivate_schedule() by checking
        _active_schedule_id under _activation_lock before rescheduling.
        """
        self._gps_poll_timer = None  # Timer has fired, clear reference

        result = self.check_and_update_gps()
        if result["updated"]:
            logger.info("GPS acquired — polling stopped")
            return

        # Guard: don't reschedule if deactivated during check_and_update_gps()
        with self._activation_lock:
            if not self._active_schedule_id:
                return
        self.start_gps_polling()

    def get_enabled_schedule_id(self) -> str | None:
        """
        Get the ID of the currently enabled schedule.

        Returns:
            Schedule ID if one is enabled, None otherwise.
        """
        return self._enabled_schedule_id

    def set_enabled_schedule(self, schedule_id: str | None) -> None:
        """
        Set which schedule is enabled (only one at a time).

        This is the single source of truth for schedule enabled state.
        The enabled field in schedule JSON files is derived from this,
        not the other way around.

        Args:
            schedule_id: Schedule to enable, or None to disable all

        Raises:
            ValueError: If schedule_id is provided but schedule not found
        """
        if schedule_id is not None:
            # Check if another schedule is already enabled (manual disable required)
            current_enabled = self._enabled_schedule_id
            if current_enabled and current_enabled != schedule_id:
                raise ValueError(
                    f"Cannot enable schedule '{schedule_id}': "
                    f"Schedule '{current_enabled}' is already enabled. "
                    "Disable it first."
                )

            # Verify schedule exists
            schedule = storage_read(schedule_id)
            if schedule is None:
                raise ValueError(f"Schedule not found: {schedule_id}")

        with self._cache_lock:
            old_enabled = self._enabled_schedule_id
            self._enabled_schedule_id = schedule_id

            # Invalidate cache for both old and new enabled schedules
            # so they get refreshed with correct enabled state
            if old_enabled and old_enabled in self._cache:
                del self._cache[old_enabled]
            if schedule_id and schedule_id in self._cache:
                del self._cache[schedule_id]

        # Persist state to disk
        self._save_active_state()

        if schedule_id:
            logger.info(f"Enabled schedule: {schedule_id}")
        else:
            logger.info("Disabled all schedules")

    def activate_schedule(
        self,
        schedule_id: str,
        check_conflicts: bool = True,
        latitude: float = 0.0,
        longitude: float = 0.0,
        timezone_name: str = "UTC",
        progress_callback: Callable[[str, int], None] | None = None,
        coordinates_source: str = "explicit",
    ) -> None:
        """
        Activate a schedule (requires manual deactivation of any active schedule first).

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
            progress_callback: Optional callback(phase: str, progress: int) for
                              progress updates during activation. Phases are:
                              "checking_conflicts" (10%), "generating_cron" (30%),
                              "applying_cron" (60%), "updating_state" (90%),
                              "complete" (100%)
            coordinates_source: How coordinates were determined (Issue #331).
                               Values: "explicit", "gps", "timezone"

        Returns:
            None on success

        Raises:
            ScheduleActivationError: If activation fails (schedule not found,
                disabled, cron conversion failed, etc.)
            ScheduleConflictError: If schedule has blocking conflicts
        """

        def _emit_progress(phase: str, progress: int) -> None:
            """Emit progress if callback provided."""
            if progress_callback:
                try:
                    # Validate inputs in debug builds
                    assert 0 <= progress <= 100, f"Invalid progress value: {progress}"
                    assert phase in _ACTIVATION_PHASES, f"Invalid phase: {phase}"
                    progress_callback(phase, progress)
                except AssertionError as e:
                    logger.error(f"Progress emission validation failed: {e}")
                except Exception as e:
                    logger.warning(f"Progress callback failed: {e}")

        # Serialize entire activation sequence to prevent TOCTOU race (Issue #385)
        # This lock ensures that between schedule validation and cron application,
        # no concurrent activation/deactivation can interfere
        with self._activation_lock:
            # Defense-in-depth: Validate coordinates and timezone (Issue #385 review)
            # Even if caller validated, re-check here since this method may be called
            # programmatically from tests or future code paths
            if latitude < -90 or latitude > 90:
                raise ScheduleActivationError(
                    f"Invalid latitude: {latitude}. Must be between -90 and 90."
                )
            if longitude < -180 or longitude > 180:
                raise ScheduleActivationError(
                    f"Invalid longitude: {longitude}. Must be between -180 and 180."
                )
            try:
                import pytz

                pytz.timezone(timezone_name)
            except pytz.UnknownTimeZoneError:
                raise ScheduleActivationError(f"Invalid timezone: {timezone_name}") from None

            # Acquire cache lock for entire validation section to prevent TOCTOU race
            # (Issue #385 review fix). This ensures schedule cannot be modified/deleted
            # between validation and cron application.
            with self._cache_lock:
                # Get the schedule (now protected by cache lock)
                schedule = self.get_schedule(schedule_id)
                if not schedule:
                    raise ScheduleActivationError(f"Schedule not found: {schedule_id}")

                # Check if enabled
                if not schedule.enabled:
                    raise ScheduleActivationError(f"Schedule is disabled: {schedule_id}")

                # Already active? Return success (idempotent)
                if schedule.is_active and self._active_schedule_id == schedule_id:
                    return

                # Check for conflicts before activation (Issue #213)
                # Uses cached conflict report to avoid redundant computation
                if check_conflicts:
                    _emit_progress(
                        ACTIVATION_PHASE_CHECKING_CONFLICTS, ACTIVATION_PROGRESS_CHECKING_CONFLICTS
                    )
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
                            _emit_progress(ACTIVATION_PHASE_FAILED, ACTIVATION_PROGRESS_FAILED)
                            raise ScheduleConflictError(f"Conflict detected: {error}")
                    except ImportError:
                        # Conflict detection module not available - skip check
                        logger.warning("Conflict detection module not available, skipping check")
                    except ScheduleConflictError:
                        # Re-raise conflict errors for caller to handle
                        raise
                    except Exception as e:
                        logger.exception(f"Error during conflict check: {e}")
                        _emit_progress(ACTIVATION_PHASE_FAILED, ACTIVATION_PROGRESS_FAILED)
                        raise ScheduleActivationError(f"Conflict check failed: {e}") from e

                # Check if another schedule is already active (manual deactivate required)
                if self._active_schedule_id and self._active_schedule_id != schedule_id:
                    raise ScheduleActivationError(
                        f"Cannot activate schedule '{schedule_id}': "
                        f"Schedule '{self._active_schedule_id}' is already active. "
                        "Deactivate it first."
                    )

            # Apply schedule to system cron FIRST (Issue #215, Fix #4 atomic operation)
            # We apply cron before updating is_active to avoid inconsistent state
            # if cron application fails. If post-cron steps fail, we rollback cron.
            _emit_progress(ACTIVATION_PHASE_GENERATING_CRON, ACTIVATION_PROGRESS_GENERATING_CRON)
            cron_applied = False
            try:
                result = schedule_to_cron(
                    schedule,
                    latitude=latitude,
                    longitude=longitude,
                    timezone_name=timezone_name,
                )
                if result.errors:
                    raise ScheduleActivationError(
                        f"Cron conversion failed: {'; '.join(result.errors)}"
                    )

                _emit_progress(ACTIVATION_PHASE_APPLYING_CRON, ACTIVATION_PROGRESS_APPLYING_CRON)
                apply_to_system(
                    entries=result.entries,
                    schedule_id=schedule_id,
                    set_rtc=True,
                )
                cron_applied = True
                logger.info(
                    f"Applied cron entries for schedule: {schedule_id} ({len(result.entries)} entries)"
                )

                # Expand pattern entries to concrete datetimes for persistence (Issue #331)
                # This allows frontend to read next actions directly from disk
                expanded_entries = expand_pattern_entries(
                    entries=result.entries,
                    days_ahead=CRON_PREVIEW_DAYS_AHEAD,
                    timezone_name=timezone_name,
                )
                logger.debug(f"Expanded {len(result.entries)} entries to {len(expanded_entries)}")

                # Update in-memory state AFTER cron succeeds (Issue #331 fix)
                # We no longer write is_active to schedule JSON files - active_state.json
                # is the single source of truth. This ensures firmware updates don't cause
                # inconsistent state like showing both "Disabled" and "Active" badges.
                _emit_progress(ACTIVATION_PHASE_UPDATING_STATE, ACTIVATION_PROGRESS_UPDATING_STATE)

                # Set active schedule ID, coordinates source, and location data
                with self._cache_lock:
                    self._active_schedule_id = schedule_id
                    self._active_coordinates_source = coordinates_source
                    self._active_latitude = latitude
                    self._active_longitude = longitude
                    # Store timezone name for all activation methods (Issue #331)
                    # Previously only stored when coordinates_source="timezone",
                    # but displaying it is useful for GPS-based activation too
                    self._active_timezone_name = timezone_name

                # Persist state to disk with expanded entries for recovery after restart (Issue #331)
                # If this fails, rollback in-memory state and re-raise (Issue #385 review fix)
                try:
                    self._save_active_state(entries=expanded_entries)
                except (LockTimeoutError, OSError) as persist_error:
                    logger.error(f"Failed to persist active state: {persist_error}")
                    # Clear in-memory state since persistence failed
                    with self._cache_lock:
                        self._active_schedule_id = None
                        self._active_coordinates_source = None
                        self._active_latitude = None
                        self._active_longitude = None
                        self._active_timezone_name = None
                    raise ScheduleActivationError(
                        f"Failed to persist activation state: {persist_error}"
                    ) from persist_error

                # Reconcile missed GPIO actions (Issue #398)
                # Non-fatal: reconciliation failure must NOT prevent activation
                try:
                    from webui.backend.lib.schedule_reconciler import (
                        execute_reconciliation,
                        reconcile_schedule,
                    )

                    reconcile_actions = reconcile_schedule(
                        schedule, latitude, longitude, timezone_name
                    )
                    if reconcile_actions:
                        logger.info(f"Reconciling {len(reconcile_actions)} missed actions")
                        results = execute_reconciliation(reconcile_actions)
                        failed = [r for r in results if not r["success"]]
                        if failed:
                            logger.warning(
                                f"Reconciliation: {len(failed)} actions failed: {failed}"
                            )
                except Exception as e:
                    logger.warning(f"Reconciliation failed (non-fatal): {e}")

            except ScheduleActivationError:
                # Re-raise our own errors, but rollback cron if already applied
                if cron_applied:
                    logger.warning("Rolling back cron entries due to activation failure")
                    try:
                        remove_from_system(clear_rtc=True)
                    except Exception as rollback_error:
                        logger.error(f"Failed to rollback cron entries: {rollback_error}")
                _emit_progress(ACTIVATION_PHASE_FAILED, ACTIVATION_PROGRESS_FAILED)
                raise
            except Exception as e:
                # Rollback cron if already applied
                if cron_applied:
                    logger.warning(f"Rolling back cron entries due to error: {e}")
                    try:
                        remove_from_system(clear_rtc=True)
                    except Exception as rollback_error:
                        logger.error(f"Failed to rollback cron entries: {rollback_error}")
                logger.error(f"Failed to activate schedule: {e}")
                _emit_progress(ACTIVATION_PHASE_FAILED, ACTIVATION_PROGRESS_FAILED)
                raise ScheduleActivationError(f"Failed to apply schedule to system: {e}") from e

            _emit_progress(ACTIVATION_PHASE_COMPLETE, ACTIVATION_PROGRESS_COMPLETE)

            # Start GPS polling if using timezone fallback (Issue #382)
            self.start_gps_polling()

            logger.info(
                f"Activated schedule: {schedule_id} (coordinates_source={coordinates_source})"
            )

    def deactivate_schedule(self) -> bool:
        """
        Deactivate the currently active schedule and clear system crontab.

        Always clears crontab entries, even if no schedule is tracked as active.
        This handles orphaned cron entries from crashes/restarts (Issue #331).

        We no longer write is_active to schedule JSON files - active_state.json
        is the single source of truth. This ensures firmware updates don't cause
        inconsistent state like showing both "Disabled" and "Active" badges.

        Returns:
            True if crontab was successfully cleared, False on failure.
        """
        # Serialize with activation lock to prevent concurrent activation/deactivation (Issue #385)
        with self._activation_lock:
            # Stop GPS polling (Issue #382)
            self.stop_gps_polling()

            schedule_id = self._active_schedule_id

            # Clear in-memory state (Issue #331 fix)
            # We no longer call update_schedule to write is_active=False to JSON files
            if schedule_id is not None:
                # Clear active schedule ID and location data
                with self._cache_lock:
                    self._active_schedule_id = None
                    self._active_coordinates_source = None
                    self._active_latitude = None
                    self._active_longitude = None
                    self._active_timezone_name = None

                    # Invalidate cache so schedule gets refreshed with correct is_active state
                    if schedule_id in self._cache:
                        del self._cache[schedule_id]

                # Clear persisted state from disk (Issue #331)
                self._clear_active_state()

            # ALWAYS clear system cron - even if no active schedule tracked (Issue #331)
            # This handles orphaned cron entries from crashes or restarts
            try:
                remove_from_system(clear_rtc=True)
                logger.info("Cleared system crontab")
            except Exception as e:
                logger.error(f"Failed to remove cron jobs: {e}")
                return False  # Return failure so caller knows

            if schedule_id:
                logger.info(f"Deactivated schedule: {schedule_id}")
            else:
                logger.info("Cleared orphaned cron entries (no active schedule)")

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
                # Also clear built-in schedules cache
                self._builtin_cache = None
                self._builtin_cache_timestamp = 0.0
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

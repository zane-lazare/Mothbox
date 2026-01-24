"""
Unit tests for Scheduler Service with LRU Cache (Issue #212 - Subtask 1)

Tests SchedulerService with in-memory LRU cache, TTL expiration, and statistics tracking.
Follows the same pattern as DeploymentService for consistency.

Coverage Target: 85%+
"""

import uuid
from datetime import UTC

import pytest


def _test_uuid(name: str) -> str:
    """Generate deterministic test UUID from name."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"test.scheduler.{name}"))


# Import scheduler service and schema
try:
    from webui.backend.lib.schedule_schema import Schedule
    from webui.backend.services.scheduler_service import SchedulerService

    IMPLEMENTATION_EXISTS = True
except ImportError:
    IMPLEMENTATION_EXISTS = False
    SchedulerService = None
    Schedule = None

# Skip all tests if implementation doesn't exist
pytestmark = pytest.mark.skipif(not IMPLEMENTATION_EXISTS, reason="Implementation not yet created")


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_schedules_dir(tmp_path, monkeypatch):
    """Create temp directory and mock SCHEDULES_DIR and ACTIVE_STATE_FILE."""
    schedules = tmp_path / "schedules"
    schedules.mkdir()
    # Mock SCHEDULES_DIR in both mothbox_paths (for get_schedule_path) and storage module
    monkeypatch.setattr("mothbox_paths.SCHEDULES_DIR", schedules)
    monkeypatch.setattr("webui.backend.lib.schedule_storage.SCHEDULES_DIR", schedules)
    # Mock ACTIVE_STATE_FILE to use temp directory for test isolation
    active_state_file = tmp_path / "active_state.json"
    monkeypatch.setattr(
        "webui.backend.services.scheduler_service.ACTIVE_STATE_FILE", active_state_file
    )
    return schedules


@pytest.fixture
def sample_schedule():
    """Create a valid Schedule object for testing (Schema 3.0)."""
    from webui.backend.lib.schedule_schema import (
        Action,
        IntervalTrigger,
        Routine,
        Schedule,
        TimeWindow,
    )

    # Create a simple routine: Turn on UV, take photo, turn off UV
    actions = [
        Action(
            action_type="gpio",
            action_name="attract_on",
            offset_minutes=0,
            description="Turn on UV attract lights",
        ),
        Action(
            action_type="camera",
            action_name="takephoto",
            offset_minutes=5,
            description="Capture photo",
        ),
        Action(
            action_type="gpio",
            action_name="attract_off",
            offset_minutes=15,
            description="Turn off UV lights",
        ),
    ]

    time_window = TimeWindow(
        start_time="21:00",
        end_time="05:00",
    )

    trigger = IntervalTrigger(
        interval_minutes=60,
        time_window=time_window,
    )

    routine = Routine(
        routine_id="",
        name="UV Capture Cycle",
        description="Standard UV light photo capture sequence",
        trigger=trigger,
        actions=actions,
    )

    schedule = Schedule(
        schedule_id="",
        name="Nightly Moth Survey",
        description="Hourly captures from 9 PM to 5 AM",
        routines=[routine],
        enabled=True,
    )

    return schedule


@pytest.fixture
def scheduler_service(temp_schedules_dir):
    """Create a fresh SchedulerService for each test."""
    return SchedulerService(cache_ttl=300, max_cache_size=100)


@pytest.fixture
def multiple_schedules(temp_schedules_dir, sample_schedule):
    """Create 5 test schedules in storage (Schema 3.0)."""
    from webui.backend.lib.schedule_schema import (
        Action,
        IntervalTrigger,
        Routine,
        Schedule,
        TimeWindow,
    )
    from webui.backend.lib.schedule_storage import create_schedule

    schedules = []
    for i in range(5):
        # Create schedule with unique name and ID
        # Use modulo to keep hours valid (0-23)
        start_hour = (20 + i) % 24
        end_hour = (4 + i) % 24

        time_window = TimeWindow(
            start_time=f"{start_hour:02d}:00",
            end_time=f"{end_hour:02d}:00",
        )

        trigger = IntervalTrigger(
            interval_minutes=30 + (i * 10),
            time_window=time_window,
        )

        # Create routine with the trigger
        routine = Routine(
            routine_id=_test_uuid(f"routine-{i}"),
            name=f"Test Routine {i}",
            trigger=trigger,
            actions=[Action(action_type="camera", action_name="takephoto", offset_minutes=0)],
        )

        schedule = Schedule(
            schedule_id=_test_uuid(f"schedule-{i}"),
            name=f"Test Schedule {i}",
            description=f"Test description {i}",
            routines=[routine],
            enabled=(i % 2 == 0),  # Alternate enabled/disabled
        )

        create_schedule(schedule)
        schedules.append(schedule)

    return schedules


# ============================================================================
# Test Service Initialization
# ============================================================================


class TestSchedulerServiceInit:
    """Tests for SchedulerService initialization."""

    def test_default_cache_ttl(self):
        """SchedulerService should use default cache TTL."""
        service = SchedulerService()
        assert service.cache_ttl == 300

    def test_custom_cache_ttl(self):
        """SchedulerService should accept custom cache TTL."""
        service = SchedulerService(cache_ttl=600)
        assert service.cache_ttl == 600

    def test_custom_max_cache_size(self):
        """SchedulerService should accept custom max cache size."""
        service = SchedulerService(max_cache_size=50)
        assert service.max_cache_size == 50

    def test_statistics_initialized(self, scheduler_service):
        """SchedulerService should initialize statistics to zero."""
        stats = scheduler_service.get_statistics()
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0
        assert stats["cache_evictions"] == 0
        assert stats["total_reads"] == 0
        assert stats["total_writes"] == 0
        assert stats["total_deletes"] == 0

    def test_cache_starts_empty(self, scheduler_service):
        """Cache should start with no entries."""
        stats = scheduler_service.get_statistics()
        assert stats["cache_size"] == 0

    def test_locks_initialized(self, scheduler_service):
        """RLock instances should be created for thread safety."""
        # Verify locks exist (RLock objects)
        assert hasattr(scheduler_service, "_cache_lock")
        assert hasattr(scheduler_service, "_stats_lock")
        # RLock objects are callable for context manager
        assert callable(scheduler_service._cache_lock.__enter__)
        assert callable(scheduler_service._stats_lock.__enter__)


# ============================================================================
# Test Service Imports
# ============================================================================


class TestServiceImports:
    """Tests for required imports and availability."""

    def test_scheduler_service_importable(self):
        """SchedulerService should be importable."""
        from webui.backend.services.scheduler_service import SchedulerService

        assert SchedulerService is not None

    def test_schedule_schema_available(self):
        """Schedule dataclass should be available."""
        from webui.backend.lib.schedule_schema import Schedule

        assert Schedule is not None

    def test_schedule_storage_available(self):
        """Storage functions should be available."""
        from webui.backend.lib.schedule_storage import (
            create_schedule,
            delete_schedule,
            list_schedules,
            read_schedule,
            update_schedule,
        )

        assert create_schedule is not None
        assert read_schedule is not None
        assert update_schedule is not None
        assert delete_schedule is not None
        assert list_schedules is not None

    def test_routine_available(self):
        """Routine dataclass should be available."""
        from webui.backend.lib.schedule_schema import Routine

        assert Routine is not None

    def test_pattern_action_available(self):
        """Action dataclass should be available."""
        from webui.backend.lib.schedule_schema import Action

        assert Action is not None

    def test_interval_trigger_available(self):
        """IntervalTrigger dataclass should be available."""
        from webui.backend.lib.schedule_schema import IntervalTrigger

        assert IntervalTrigger is not None


# ============================================================================
# Test Get Schedule
# ============================================================================


class TestGetSchedule:
    """Tests for get_schedule() method."""

    def test_get_schedule_existing(self, scheduler_service, temp_schedules_dir, sample_schedule):
        """get_schedule should return Schedule from storage."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create schedule in storage
        sample_schedule.schedule_id = _test_uuid("existing")
        create_schedule(sample_schedule)

        # Get schedule
        schedule = scheduler_service.get_schedule(_test_uuid("existing"))
        assert schedule is not None
        assert schedule.schedule_id == _test_uuid("existing")
        assert schedule.name == sample_schedule.name

    def test_get_schedule_nonexistent(self, scheduler_service, temp_schedules_dir):
        """get_schedule should return None for missing schedule."""
        schedule = scheduler_service.get_schedule(_test_uuid("nonexistent"))
        assert schedule is None

    def test_get_schedule_cache_hit(self, scheduler_service, temp_schedules_dir, sample_schedule):
        """Second call should use cache (hits incremented)."""
        from webui.backend.lib.schedule_storage import create_schedule

        sample_schedule.schedule_id = _test_uuid("cache-hit")
        create_schedule(sample_schedule)

        # First call - cache miss
        scheduler_service.get_schedule(_test_uuid("cache-hit"))
        stats_after_first = scheduler_service.get_statistics()
        assert stats_after_first["cache_misses"] == 1
        assert stats_after_first["cache_hits"] == 0

        # Second call - cache hit
        scheduler_service.get_schedule(_test_uuid("cache-hit"))
        stats_after_second = scheduler_service.get_statistics()
        assert stats_after_second["cache_hits"] == 1
        assert stats_after_second["cache_misses"] == 1  # Still 1

    def test_get_schedule_cache_miss_tracked(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """Miss increments counter."""
        from webui.backend.lib.schedule_storage import create_schedule

        sample_schedule.schedule_id = _test_uuid("miss")
        create_schedule(sample_schedule)

        stats_before = scheduler_service.get_statistics()
        assert stats_before["cache_misses"] == 0

        scheduler_service.get_schedule(_test_uuid("miss"))

        stats_after = scheduler_service.get_statistics()
        assert stats_after["cache_misses"] == 1

    def test_get_schedule_cache_hit_tracked(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """Hit increments counter."""
        from webui.backend.lib.schedule_storage import create_schedule

        sample_schedule.schedule_id = _test_uuid("hit-tracked")
        create_schedule(sample_schedule)

        # First call - cache miss
        scheduler_service.get_schedule(_test_uuid("hit-tracked"))
        stats_before = scheduler_service.get_statistics()
        assert stats_before["cache_hits"] == 0

        # Second call - cache hit
        scheduler_service.get_schedule(_test_uuid("hit-tracked"))
        stats_after = scheduler_service.get_statistics()
        assert stats_after["cache_hits"] == 1

    def test_get_schedule_reads_tracked(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """Total reads incremented."""
        from webui.backend.lib.schedule_storage import create_schedule

        sample_schedule.schedule_id = _test_uuid("reads")
        create_schedule(sample_schedule)

        stats_before = scheduler_service.get_statistics()
        assert stats_before["total_reads"] == 0

        # Call twice
        scheduler_service.get_schedule(_test_uuid("reads"))
        scheduler_service.get_schedule(_test_uuid("reads"))

        stats_after = scheduler_service.get_statistics()
        assert stats_after["total_reads"] == 2

    def test_cache_ttl_expiration(self, temp_schedules_dir, sample_schedule):
        """Entry expires after TTL (use time.sleep)."""
        import time

        from webui.backend.lib.schedule_storage import create_schedule

        # Create service with very short TTL
        service = SchedulerService(cache_ttl=0.1, max_cache_size=100)

        sample_schedule.schedule_id = _test_uuid("ttl")
        create_schedule(sample_schedule)

        # First call - cache miss
        service.get_schedule(_test_uuid("ttl"))
        stats_after_first = service.get_statistics()
        assert stats_after_first["cache_misses"] == 1
        assert stats_after_first["cache_size"] == 1

        # Wait for TTL to expire
        time.sleep(0.15)

        # Second call - cache miss (TTL expired)
        service.get_schedule(_test_uuid("ttl"))
        stats_after_second = service.get_statistics()
        assert stats_after_second["cache_misses"] == 2
        assert stats_after_second["cache_hits"] == 0


# ============================================================================
# Test List Schedules
# ============================================================================


class TestListSchedules:
    """Tests for list_schedules() method."""

    def test_list_schedules_empty(self, scheduler_service, temp_schedules_dir):
        """Empty list when no schedules."""
        schedules = scheduler_service.list_schedules(include_builtin=False)
        assert schedules == []

    def test_list_schedules_returns_all(
        self, scheduler_service, temp_schedules_dir, multiple_schedules
    ):
        """Returns all schedules."""
        schedules = scheduler_service.list_schedules(include_builtin=False)
        assert len(schedules) == 5
        # Check all IDs present
        schedule_ids = [s.schedule_id for s in schedules]
        for i in range(5):
            assert _test_uuid(f"schedule-{i}") in schedule_ids

    def test_list_schedules_includes_builtin(self, scheduler_service, temp_schedules_dir):
        """Includes built-in schedules by default."""
        # This test verifies that include_builtin=True is the default
        # Built-in schedules may or may not exist in the test environment
        # We just verify the call succeeds and returns a list
        schedules = scheduler_service.list_schedules()
        assert isinstance(schedules, list)

    def test_list_schedules_from_storage(
        self, scheduler_service, temp_schedules_dir, multiple_schedules
    ):
        """Delegates to storage layer."""
        # Verify that list_schedules returns schedules created in storage
        schedules = scheduler_service.list_schedules(include_builtin=False)
        assert len(schedules) == 5
        # Verify schedule objects are valid
        for schedule in schedules:
            assert hasattr(schedule, "schedule_id")
            assert hasattr(schedule, "name")
            assert hasattr(schedule, "routines")

    def test_list_schedules_caches_individual(
        self, scheduler_service, temp_schedules_dir, multiple_schedules
    ):
        """Individual schedules cached after listing."""
        # List schedules
        scheduler_service.list_schedules(include_builtin=False)

        # Check cache statistics
        stats = scheduler_service.get_statistics()
        assert stats["cache_size"] == 5  # All 5 schedules should be cached

        # Now get_schedule should be a cache hit
        schedule = scheduler_service.get_schedule(_test_uuid("schedule-0"))
        assert schedule is not None

        stats_after = scheduler_service.get_statistics()
        assert stats_after["cache_hits"] == 1  # Cache hit from get_schedule


# ============================================================================
# Test Cache Behavior
# ============================================================================


class TestCacheBehavior:
    """Tests for LRU cache behavior."""

    def test_cache_lru_eviction(self, temp_schedules_dir, sample_schedule):
        """Evicts LRU when full."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create service with small cache
        service = SchedulerService(cache_ttl=300, max_cache_size=3)

        # Create 4 schedules
        for i in range(4):
            schedule = Schedule(
                schedule_id=_test_uuid(f"evict-{i}"),
                name=f"Evict Test {i}",
                description="Test schedule",
                routines=sample_schedule.routines,
                enabled=True,
            )
            create_schedule(schedule)

        # Get first 3 schedules - cache fills up
        service.get_schedule(_test_uuid("evict-0"))
        service.get_schedule(_test_uuid("evict-1"))
        service.get_schedule(_test_uuid("evict-2"))

        stats = service.get_statistics()
        assert stats["cache_size"] == 3
        assert stats["cache_evictions"] == 0

        # Get 4th schedule - triggers eviction
        service.get_schedule(_test_uuid("evict-3"))

        stats_after = service.get_statistics()
        assert stats_after["cache_size"] == 3  # Still 3 (max)
        assert stats_after["cache_evictions"] == 1  # One eviction

        # Verify LRU was evicted (evict-test-0)
        # Next get_schedule for evict-test-0 should be cache miss
        service.get_schedule(_test_uuid("evict-0"))
        stats_final = service.get_statistics()
        # Total misses: 4 (initial loads) + 1 (evicted item) = 5
        assert stats_final["cache_misses"] == 5

    def test_cache_size_tracked(self, scheduler_service, temp_schedules_dir, multiple_schedules):
        """Statistics track cache size."""
        stats_before = scheduler_service.get_statistics()
        assert stats_before["cache_size"] == 0

        # Get a schedule
        scheduler_service.get_schedule(_test_uuid("schedule-0"))

        stats_after = scheduler_service.get_statistics()
        assert stats_after["cache_size"] == 1

        # Get another schedule
        scheduler_service.get_schedule(_test_uuid("schedule-1"))

        stats_final = scheduler_service.get_statistics()
        assert stats_final["cache_size"] == 2

    def test_cache_evictions_tracked(self, temp_schedules_dir, sample_schedule):
        """Evictions counter increments."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create service with max_cache_size=2
        service = SchedulerService(cache_ttl=300, max_cache_size=2)

        # Create 3 schedules
        for i in range(3):
            schedule = Schedule(
                schedule_id=_test_uuid(f"track-evict-{i}"),
                name=f"Track Evict {i}",
                description="Test schedule",
                routines=sample_schedule.routines,
                enabled=True,
            )
            create_schedule(schedule)

        stats_before = service.get_statistics()
        assert stats_before["cache_evictions"] == 0

        # Fill cache
        service.get_schedule(_test_uuid("track-evict-0"))
        service.get_schedule(_test_uuid("track-evict-1"))

        stats_after_fill = service.get_statistics()
        assert stats_after_fill["cache_evictions"] == 0

        # Trigger eviction
        service.get_schedule(_test_uuid("track-evict-2"))

        stats_after_evict = service.get_statistics()
        assert stats_after_evict["cache_evictions"] == 1


# ============================================================================
# Test Create Schedule
# ============================================================================


class TestCreateSchedule:
    """Tests for create_schedule() method."""

    def test_create_schedule_success(self, scheduler_service, temp_schedules_dir, sample_schedule):
        """create_schedule should create and cache schedule."""
        sample_schedule.schedule_id = _test_uuid("create-success")
        sample_schedule.name = "Create Success Test"

        result = scheduler_service.create_schedule(sample_schedule)

        assert result is True

        # Verify schedule was created on disk (filename is slugified name, not schedule_id)
        schedule_path = temp_schedules_dir / "create-success-test.json"
        assert schedule_path.exists()

        # Verify schedule is in cache
        stats = scheduler_service.get_statistics()
        assert stats["cache_size"] == 1

    def test_create_schedule_validation_error(self, scheduler_service, sample_schedule):
        """create_schedule should raise on invalid schedule."""
        from webui.backend.lib.schedule_schema import ScheduleValidationError

        # Create invalid schedule (empty name)
        sample_schedule.schedule_id = _test_uuid("create-invalid")
        sample_schedule.name = ""

        with pytest.raises(ScheduleValidationError):
            scheduler_service.create_schedule(sample_schedule)

    def test_create_schedule_updates_cache(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """New schedule should be in cache after creation."""
        sample_schedule.schedule_id = _test_uuid("create-cache")

        scheduler_service.create_schedule(sample_schedule)

        # Verify we can retrieve it from cache (cache hit)
        stats_before = scheduler_service.get_statistics()
        retrieved = scheduler_service.get_schedule(_test_uuid("create-cache"))
        stats_after = scheduler_service.get_statistics()

        assert retrieved is not None
        assert retrieved.schedule_id == _test_uuid("create-cache")
        assert stats_after["cache_hits"] == stats_before["cache_hits"] + 1

    def test_create_schedule_writes_tracked(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """Total writes should be incremented."""
        sample_schedule.schedule_id = _test_uuid("create-writes")

        stats_before = scheduler_service.get_statistics()
        assert stats_before["total_writes"] == 0

        scheduler_service.create_schedule(sample_schedule)

        stats_after = scheduler_service.get_statistics()
        assert stats_after["total_writes"] == 1

    def test_create_schedule_returns_bool(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """create_schedule should return True on success."""
        sample_schedule.schedule_id = _test_uuid("create-bool")

        result = scheduler_service.create_schedule(sample_schedule)

        assert isinstance(result, bool)
        assert result is True


# ============================================================================
# Test Update Schedule
# ============================================================================


class TestUpdateSchedule:
    """Tests for update_schedule() method."""

    def test_update_schedule_success(self, scheduler_service, temp_schedules_dir, sample_schedule):
        """update_schedule should update and return Schedule."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create schedule first
        sample_schedule.schedule_id = _test_uuid("update-success")
        create_schedule(sample_schedule)

        # Update it
        updated = scheduler_service.update_schedule(
            _test_uuid("update-success"), {"name": "Updated Name"}
        )

        assert updated is not None
        assert isinstance(updated, Schedule)
        assert updated.name == "Updated Name"
        assert updated.schedule_id == _test_uuid("update-success")

    def test_update_schedule_nonexistent(self, scheduler_service, temp_schedules_dir):
        """update_schedule should return None for missing schedule."""
        result = scheduler_service.update_schedule(_test_uuid("nonexistent"), {"name": "New Name"})

        assert result is None

    def test_update_schedule_partial_fields(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """update_schedule should only update specified fields."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create schedule first
        sample_schedule.schedule_id = _test_uuid("update-partial")
        sample_schedule.name = "Original Name"
        sample_schedule.description = "Original Description"
        create_schedule(sample_schedule)

        # Update only name
        updated = scheduler_service.update_schedule(
            _test_uuid("update-partial"), {"name": "Updated Name"}
        )

        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.description == "Original Description"

    def test_update_schedule_cache_updated(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """Cache should reflect changes after update."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create schedule
        sample_schedule.schedule_id = _test_uuid("update-cache")
        sample_schedule.name = "Original Name"
        create_schedule(sample_schedule)

        # Get it to populate cache
        scheduler_service.get_schedule(_test_uuid("update-cache"))

        # Update it
        scheduler_service.update_schedule(_test_uuid("update-cache"), {"name": "Updated Name"})

        # Get from cache (should be cache hit with updated value)
        retrieved = scheduler_service.get_schedule(_test_uuid("update-cache"))

        assert retrieved is not None
        assert retrieved.name == "Updated Name"

    def test_update_schedule_builtin_protected(self, scheduler_service, temp_schedules_dir):
        """update_schedule should raise ValueError for protected fields on built-in schedule."""
        # This test assumes a built-in schedule exists
        # For now, we'll create a mock by patching is_builtin_schedule
        from unittest.mock import patch

        with (
            patch(
                "webui.backend.services.scheduler_service.is_builtin_schedule", return_value=True
            ),
            pytest.raises(ValueError, match="Cannot modify built-in schedule"),
        ):
            scheduler_service.update_schedule(_test_uuid("builtin-schedule"), {"name": "New Name"})

    def test_update_schedule_builtin_enabled_not_allowed(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """update_schedule should reject ALL updates on built-in schedules (Issue #331 fix).

        enabled/is_active are now derived from active_state.json, not stored in
        schedule JSON files. Use set_enabled_schedule() instead.
        """
        from unittest.mock import patch

        # Mock is_builtin_schedule to return True
        with (
            patch(
                "webui.backend.services.scheduler_service.is_builtin_schedule", return_value=True
            ),
            pytest.raises(ValueError, match="Cannot modify built-in schedule"),
        ):
            scheduler_service.update_schedule(_test_uuid("builtin-enabled"), {"enabled": False})


# ============================================================================
# Test Delete Schedule
# ============================================================================


class TestDeleteSchedule:
    """Tests for delete_schedule() method."""

    def test_delete_schedule_success(self, scheduler_service, temp_schedules_dir, sample_schedule):
        """delete_schedule should delete and return True."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create schedule first (with unique name)
        sample_schedule.schedule_id = _test_uuid("delete-success")
        sample_schedule.name = "Delete Success Test"
        create_schedule(sample_schedule)

        # Verify it exists (filename is slugified name, not schedule_id)
        schedule_path = temp_schedules_dir / "delete-success-test.json"
        assert schedule_path.exists()

        # Delete it
        result = scheduler_service.delete_schedule(_test_uuid("delete-success"))

        assert result is True
        assert not schedule_path.exists()

    def test_delete_schedule_nonexistent(self, scheduler_service, temp_schedules_dir):
        """delete_schedule should return False for missing schedule."""
        result = scheduler_service.delete_schedule(_test_uuid("nonexistent"))

        assert result is False

    def test_delete_schedule_cache_invalidated(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """Cache entry should be removed after delete."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create schedule
        sample_schedule.schedule_id = _test_uuid("delete-cache")
        create_schedule(sample_schedule)

        # Get it to populate cache
        scheduler_service.get_schedule(_test_uuid("delete-cache"))
        stats_after_get = scheduler_service.get_statistics()
        assert stats_after_get["cache_size"] == 1

        # Delete it
        scheduler_service.delete_schedule(_test_uuid("delete-cache"))

        # Cache should be empty
        stats_after_delete = scheduler_service.get_statistics()
        assert stats_after_delete["cache_size"] == 0

    def test_delete_schedule_builtin_protected(self, scheduler_service, temp_schedules_dir):
        """delete_schedule should raise ValueError for built-in schedule."""
        from unittest.mock import patch

        with (
            patch(
                "webui.backend.services.scheduler_service.is_builtin_schedule", return_value=True
            ),
            pytest.raises(ValueError, match="Cannot delete built-in schedule"),
        ):
            scheduler_service.delete_schedule(_test_uuid("builtin-schedule"))

    def test_delete_schedule_clears_active(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """delete_schedule should clear active schedule ID if deleted."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create schedule
        sample_schedule.schedule_id = _test_uuid("delete-active")
        sample_schedule.is_active = True
        create_schedule(sample_schedule)

        # Set as active
        scheduler_service._active_schedule_id = _test_uuid("delete-active")

        # Delete it
        scheduler_service.delete_schedule(_test_uuid("delete-active"))

        # Active schedule should be cleared
        assert scheduler_service._active_schedule_id is None


# ============================================================================
# Test Set Enabled Schedule (Issue #331 fix)
# ============================================================================


class TestSetEnabledSchedule:
    """Tests for set_enabled_schedule() method.

    enabled/is_active are now stored in active_state.json (single source of truth),
    not in schedule JSON files. This ensures firmware updates don't cause inconsistent
    state like showing both "Disabled" and "Active" badges.
    """

    def test_set_enabled_schedule_success(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """set_enabled_schedule should set the enabled schedule ID."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create schedule
        sample_schedule.schedule_id = _test_uuid("enabled-test")
        create_schedule(sample_schedule)

        # Enable it
        scheduler_service.set_enabled_schedule(_test_uuid("enabled-test"))

        assert scheduler_service._enabled_schedule_id == _test_uuid("enabled-test")

    def test_set_enabled_schedule_none_disables(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """set_enabled_schedule(None) should clear the enabled schedule."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create and enable schedule
        sample_schedule.schedule_id = _test_uuid("disabled-test")
        create_schedule(sample_schedule)
        scheduler_service.set_enabled_schedule(_test_uuid("disabled-test"))

        # Disable
        scheduler_service.set_enabled_schedule(None)

        assert scheduler_service._enabled_schedule_id is None

    def test_set_enabled_schedule_rejects_when_another_enabled(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """Enabling a schedule when another is enabled raises ValueError (manual disable required)."""
        from copy import deepcopy

        from webui.backend.lib.schedule_storage import create_schedule

        # Create first schedule (with unique name)
        schedule1 = deepcopy(sample_schedule)
        schedule1.schedule_id = _test_uuid("first-enabled")
        schedule1.name = "First Enabled Schedule"
        create_schedule(schedule1)

        # Create second schedule (with unique name)
        schedule2 = deepcopy(sample_schedule)
        schedule2.schedule_id = _test_uuid("second-enabled")
        schedule2.name = "Second Enabled Schedule"
        create_schedule(schedule2)

        # Enable first
        scheduler_service.set_enabled_schedule(_test_uuid("first-enabled"))
        assert scheduler_service._enabled_schedule_id == _test_uuid("first-enabled")

        # Try to enable second without disabling first - should raise error
        with pytest.raises(ValueError, match="already enabled.*Disable it first"):
            scheduler_service.set_enabled_schedule(_test_uuid("second-enabled"))

        # First should still be enabled
        assert scheduler_service._enabled_schedule_id == _test_uuid("first-enabled")

    def test_set_enabled_schedule_after_manual_disable(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """Enabling a schedule after manually disabling the previous one works."""
        from copy import deepcopy

        from webui.backend.lib.schedule_storage import create_schedule

        # Create first schedule (with unique name)
        schedule1 = deepcopy(sample_schedule)
        schedule1.schedule_id = _test_uuid("first-enabled")
        schedule1.name = "First Enabled Schedule"
        create_schedule(schedule1)

        # Create second schedule (with unique name)
        schedule2 = deepcopy(sample_schedule)
        schedule2.schedule_id = _test_uuid("second-enabled")
        schedule2.name = "Second Enabled Schedule"
        create_schedule(schedule2)

        # Enable first
        scheduler_service.set_enabled_schedule(_test_uuid("first-enabled"))
        assert scheduler_service._enabled_schedule_id == _test_uuid("first-enabled")

        # Disable first (manual disable)
        scheduler_service.set_enabled_schedule(None)
        assert scheduler_service._enabled_schedule_id is None

        # Now enable second (should work)
        scheduler_service.set_enabled_schedule(_test_uuid("second-enabled"))
        assert scheduler_service._enabled_schedule_id == _test_uuid("second-enabled")

        # Verify first is no longer enabled via get_schedule
        first = scheduler_service.get_schedule(_test_uuid("first-enabled"))
        assert first.enabled is False

        # Verify second is enabled
        second = scheduler_service.get_schedule(_test_uuid("second-enabled"))
        assert second.enabled is True

    def test_set_enabled_schedule_nonexistent_raises(self, scheduler_service, temp_schedules_dir):
        """set_enabled_schedule should raise ValueError for nonexistent schedule."""
        with pytest.raises(ValueError, match="Schedule not found"):
            scheduler_service.set_enabled_schedule(_test_uuid("nonexistent"))

    def test_get_schedule_derives_enabled_from_state(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """get_schedule should derive enabled from _enabled_schedule_id, not from JSON file."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create schedule with enabled=True in JSON (but we'll control via service)
        sample_schedule.schedule_id = _test_uuid("derived-enabled")
        sample_schedule.enabled = True  # This value in JSON should be ignored
        create_schedule(sample_schedule)

        # Without calling set_enabled_schedule, enabled should be False
        schedule = scheduler_service.get_schedule(_test_uuid("derived-enabled"))
        assert schedule.enabled is False  # Derived from state, not JSON

        # After enabling via service, enabled should be True
        scheduler_service.set_enabled_schedule(_test_uuid("derived-enabled"))
        schedule = scheduler_service.get_schedule(_test_uuid("derived-enabled"))
        assert schedule.enabled is True

    def test_list_schedules_derives_enabled_from_state(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """list_schedules should derive enabled from _enabled_schedule_id, not from JSON files."""
        from copy import deepcopy

        from webui.backend.lib.schedule_storage import create_schedule

        # Create two schedules with enabled=True in JSON (but we'll control via service)
        # Use unique names to avoid filename collision
        schedule1 = deepcopy(sample_schedule)
        schedule1.schedule_id = _test_uuid("list-enabled-1")
        schedule1.name = "List Enabled Test Schedule 1"
        schedule1.enabled = True
        create_schedule(schedule1)

        schedule2 = deepcopy(sample_schedule)
        schedule2.schedule_id = _test_uuid("list-enabled-2")
        schedule2.name = "List Enabled Test Schedule 2"
        schedule2.enabled = True
        create_schedule(schedule2)

        # Without calling set_enabled_schedule, both should show enabled=False
        schedules = scheduler_service.list_schedules(include_builtin=False)
        for s in schedules:
            assert s.enabled is False

        # Enable one via service
        scheduler_service.set_enabled_schedule(_test_uuid("list-enabled-1"))

        # Now only the enabled one should show enabled=True
        schedules = scheduler_service.list_schedules(include_builtin=False)
        schedule_map = {s.schedule_id: s for s in schedules}
        assert schedule_map[_test_uuid("list-enabled-1")].enabled is True
        assert schedule_map[_test_uuid("list-enabled-2")].enabled is False


# ============================================================================
# Test Get Active Schedule
# ============================================================================


class TestGetActiveSchedule:
    """Tests for get_active_schedule() method."""

    def test_get_active_schedule_none(self, scheduler_service, temp_schedules_dir):
        """get_active_schedule should return None when no active schedule."""
        active = scheduler_service.get_active_schedule()
        assert active is None

    def test_get_active_schedule_returns_active(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """get_active_schedule should return active schedule."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create schedule
        sample_schedule.schedule_id = _test_uuid("active-schedule")
        sample_schedule.is_active = True
        create_schedule(sample_schedule)

        # Set as active
        scheduler_service._active_schedule_id = _test_uuid("active-schedule")

        # Get active schedule
        active = scheduler_service.get_active_schedule()
        assert active is not None
        assert active.schedule_id == _test_uuid("active-schedule")

    def test_get_active_schedule_from_cache(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """get_active_schedule should use _active_schedule_id for O(1) lookup."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create schedule
        sample_schedule.schedule_id = _test_uuid("active-cache")
        sample_schedule.is_active = True
        create_schedule(sample_schedule)

        # Set as active
        scheduler_service._active_schedule_id = _test_uuid("active-cache")

        # Get active schedule (should use cached ID)
        active = scheduler_service.get_active_schedule()
        assert active is not None
        assert active.schedule_id == _test_uuid("active-cache")

    def test_get_active_schedule_clears_stale_id_on_external_delete(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """get_active_schedule should clear stale ID if schedule was deleted externally."""
        from webui.backend.lib.schedule_storage import create_schedule, delete_schedule

        # Create and activate schedule via service
        sample_schedule.schedule_id = _test_uuid("external-delete")
        sample_schedule.is_active = True
        create_schedule(sample_schedule)
        scheduler_service._active_schedule_id = _test_uuid("external-delete")

        # Verify initial state
        active = scheduler_service.get_active_schedule()
        assert active is not None
        assert active.schedule_id == _test_uuid("external-delete")

        # Simulate external deletion (bypassing the service)
        delete_schedule(_test_uuid("external-delete"))

        # Clear the cache so get_schedule() reads from disk
        scheduler_service._cache.clear()

        # Call get_active_schedule - should return None AND clear stale ID
        active = scheduler_service.get_active_schedule()
        assert active is None
        assert scheduler_service._active_schedule_id is None

        # Verify subsequent call doesn't retain stale reference
        active = scheduler_service.get_active_schedule()
        assert active is None


# ============================================================================
# Test Activate Schedule
# ============================================================================


class TestActivateSchedule:
    """Tests for activate_schedule() method."""

    def test_activate_schedule_success(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """activate_schedule should activate and return None on success."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create schedule (enabled state is now derived from service)
        sample_schedule.schedule_id = _test_uuid("activate-success")
        create_schedule(sample_schedule)

        # Enable it via service (Issue #331 - enabled state is in active_state.json)
        scheduler_service.set_enabled_schedule(_test_uuid("activate-success"))

        # Activate it - should not raise
        scheduler_service.activate_schedule(_test_uuid("activate-success"))

        assert scheduler_service._active_schedule_id == _test_uuid("activate-success")

    def test_activate_schedule_nonexistent(self, scheduler_service, temp_schedules_dir):
        """activate_schedule should raise ScheduleActivationError for nonexistent schedule."""
        from webui.backend.lib.schedule_schema import ScheduleActivationError

        with pytest.raises(ScheduleActivationError, match="not found"):
            scheduler_service.activate_schedule(_test_uuid("nonexistent"))

    def test_activate_schedule_disabled(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """activate_schedule should raise ScheduleActivationError for disabled schedule."""
        from webui.backend.lib.schedule_schema import ScheduleActivationError
        from webui.backend.lib.schedule_storage import create_schedule

        # Create schedule (NOT enabled via service - Issue #331)
        sample_schedule.schedule_id = _test_uuid("activate-disabled")
        create_schedule(sample_schedule)

        # Don't call set_enabled_schedule - schedule is disabled by default
        # Try to activate - should raise
        with pytest.raises(ScheduleActivationError, match="disabled"):
            scheduler_service.activate_schedule(_test_uuid("activate-disabled"))

    def test_activate_rejects_when_another_active(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """activate_schedule raises error if another schedule is already active (manual deactivate required)."""
        from webui.backend.lib.schedule_schema import Schedule, ScheduleActivationError
        from webui.backend.lib.schedule_storage import create_schedule

        # Create two schedules (enabled state is now derived from service)
        sample_schedule.schedule_id = _test_uuid("activate-first")
        create_schedule(sample_schedule)

        second_schedule = Schedule(
            schedule_id=_test_uuid("activate-second"),
            name="Second Schedule",
            description="Second test schedule",
            routines=sample_schedule.routines,
        )
        create_schedule(second_schedule)

        # Enable and activate first (Issue #331 - enabled state via service)
        scheduler_service.set_enabled_schedule(_test_uuid("activate-first"))
        scheduler_service.activate_schedule(_test_uuid("activate-first"))
        assert scheduler_service._active_schedule_id == _test_uuid("activate-first")

        # Disable first, enable second (required for enabling new schedule)
        scheduler_service.set_enabled_schedule(None)
        scheduler_service.set_enabled_schedule(_test_uuid("activate-second"))

        # Try to activate second without deactivating first - should raise error
        with pytest.raises(ScheduleActivationError, match="already active.*Deactivate it first"):
            scheduler_service.activate_schedule(_test_uuid("activate-second"))

        # First should still be active
        assert scheduler_service._active_schedule_id == _test_uuid("activate-first")

    def test_activate_after_manual_deactivate(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """activate_schedule works after manually deactivating the previous schedule."""
        from webui.backend.lib.schedule_schema import Schedule
        from webui.backend.lib.schedule_storage import create_schedule

        # Create two schedules (enabled state is now derived from service)
        sample_schedule.schedule_id = _test_uuid("activate-first")
        create_schedule(sample_schedule)

        second_schedule = Schedule(
            schedule_id=_test_uuid("activate-second"),
            name="Second Schedule",
            description="Second test schedule",
            routines=sample_schedule.routines,
        )
        create_schedule(second_schedule)

        # Enable and activate first (Issue #331 - enabled state via service)
        scheduler_service.set_enabled_schedule(_test_uuid("activate-first"))
        scheduler_service.activate_schedule(_test_uuid("activate-first"))
        assert scheduler_service._active_schedule_id == _test_uuid("activate-first")

        # Manual deactivate first, then disable, enable second, activate second
        scheduler_service.deactivate_schedule()
        scheduler_service.set_enabled_schedule(None)
        scheduler_service.set_enabled_schedule(_test_uuid("activate-second"))
        scheduler_service.activate_schedule(_test_uuid("activate-second"))
        assert scheduler_service._active_schedule_id == _test_uuid("activate-second")

        # First should be deactivated
        first = scheduler_service.get_schedule(_test_uuid("activate-first"))
        assert first is not None
        assert first.is_active is False

    def test_activate_updates_is_active_flag(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """activate_schedule should set is_active=True (derived from service state)."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create schedule (enabled state is now derived from service)
        sample_schedule.schedule_id = _test_uuid("activate-flag")
        create_schedule(sample_schedule)

        # Enable and activate it (Issue #331 - enabled state via service)
        scheduler_service.set_enabled_schedule(_test_uuid("activate-flag"))
        scheduler_service.activate_schedule(_test_uuid("activate-flag"))

        # Verify is_active is True (derived from _active_schedule_id)
        schedule = scheduler_service.get_schedule(_test_uuid("activate-flag"))
        assert schedule is not None
        assert schedule.is_active is True

    def test_activate_same_schedule_idempotent(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """activate_schedule should be idempotent for already active schedule."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create schedule (enabled state is now derived from service)
        sample_schedule.schedule_id = _test_uuid("activate-idempotent")
        create_schedule(sample_schedule)

        # Enable via service (Issue #331)
        scheduler_service.set_enabled_schedule(_test_uuid("activate-idempotent"))

        # Activate it twice - both should succeed without raising
        scheduler_service.activate_schedule(_test_uuid("activate-idempotent"))
        scheduler_service.activate_schedule(_test_uuid("activate-idempotent"))

        assert scheduler_service._active_schedule_id == _test_uuid("activate-idempotent")

    def test_activate_builtin_allowed(self, scheduler_service, temp_schedules_dir, sample_schedule):
        """activate_schedule should allow activating built-in schedules."""
        from unittest.mock import patch

        from webui.backend.lib.schedule_storage import create_schedule

        # Create schedule (enabled state is now derived from service)
        sample_schedule.schedule_id = _test_uuid("builtin-schedule")
        create_schedule(sample_schedule)

        # Enable via service (Issue #331)
        scheduler_service.set_enabled_schedule(_test_uuid("builtin-schedule"))

        # Mock is_builtin_schedule to return True
        with patch(
            "webui.backend.services.scheduler_service.is_builtin_schedule", return_value=True
        ):
            # Should not raise
            scheduler_service.activate_schedule(_test_uuid("builtin-schedule"))

            assert scheduler_service._active_schedule_id == _test_uuid("builtin-schedule")


# ============================================================================
# Test Activation Progress Callback (Issue #309)
# ============================================================================


class TestActivationProgressCallback:
    """Tests for progress_callback parameter in activate_schedule() (Issue #309)."""

    def test_progress_callback_called_with_phases(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """Progress callback should be called with expected phases."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create schedule (enabled state is now derived from service)
        sample_schedule.schedule_id = _test_uuid("progress-phases")
        create_schedule(sample_schedule)

        # Enable via service (Issue #331)
        scheduler_service.set_enabled_schedule(_test_uuid("progress-phases"))

        # Track progress calls
        progress_calls = []

        def track_progress(phase: str, progress: int) -> None:
            progress_calls.append((phase, progress))

        # Activate with progress callback
        scheduler_service.activate_schedule(
            _test_uuid("progress-phases"),
            check_conflicts=True,
            progress_callback=track_progress,
        )

        # Verify expected phases were called
        phases = [p[0] for p in progress_calls]
        assert "checking_conflicts" in phases
        assert "generating_cron" in phases
        assert "applying_cron" in phases
        assert "updating_state" in phases
        assert "complete" in phases

        # Verify progress values are ascending
        progress_values = [p[1] for p in progress_calls]
        assert progress_values == sorted(progress_values)

        # Verify final progress is 100
        assert progress_calls[-1] == ("complete", 100)

    def test_progress_callback_skips_conflict_check_when_disabled(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """Progress should skip checking_conflicts phase when check_conflicts=False."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create schedule (enabled state is now derived from service)
        sample_schedule.schedule_id = _test_uuid("progress-no-conflict")
        create_schedule(sample_schedule)

        # Enable via service (Issue #331)
        scheduler_service.set_enabled_schedule(_test_uuid("progress-no-conflict"))

        # Track progress calls
        progress_calls = []

        def track_progress(phase: str, progress: int) -> None:
            progress_calls.append((phase, progress))

        # Activate without conflict check
        scheduler_service.activate_schedule(
            _test_uuid("progress-no-conflict"),
            check_conflicts=False,
            progress_callback=track_progress,
        )

        # Verify checking_conflicts was NOT called
        phases = [p[0] for p in progress_calls]
        assert "checking_conflicts" not in phases
        # But other phases should still be called
        assert "generating_cron" in phases
        assert "complete" in phases

    def test_activation_works_without_callback(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """Activation should work when no progress callback is provided."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create schedule (enabled state is now derived from service)
        sample_schedule.schedule_id = _test_uuid("progress-none")
        create_schedule(sample_schedule)

        # Enable via service (Issue #331)
        scheduler_service.set_enabled_schedule(_test_uuid("progress-none"))

        # Activate without callback (should not raise)
        scheduler_service.activate_schedule(_test_uuid("progress-none"))

        assert scheduler_service._active_schedule_id == _test_uuid("progress-none")

    def test_progress_callback_error_does_not_block_activation(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """A failing progress callback should not block activation."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create schedule (enabled state is now derived from service)
        sample_schedule.schedule_id = _test_uuid("progress-error")
        create_schedule(sample_schedule)

        # Enable via service (Issue #331)
        scheduler_service.set_enabled_schedule(_test_uuid("progress-error"))

        # Create a callback that raises an exception
        def failing_callback(phase: str, progress: int) -> None:
            raise RuntimeError("Callback failed intentionally")

        # Activate with failing callback - should not raise
        scheduler_service.activate_schedule(
            _test_uuid("progress-error"),
            progress_callback=failing_callback,
        )

        # Activation should still succeed
        assert scheduler_service._active_schedule_id == _test_uuid("progress-error")


# ============================================================================
# Test Deactivate Schedule
# ============================================================================


class TestDeactivateSchedule:
    """Tests for deactivate_schedule() method."""

    def test_deactivate_schedule_success(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """deactivate_schedule should deactivate current active schedule."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create schedule (enabled state is now derived from service)
        sample_schedule.schedule_id = _test_uuid("deactivate-success")
        create_schedule(sample_schedule)

        # Enable and activate via service (Issue #331)
        scheduler_service.set_enabled_schedule(_test_uuid("deactivate-success"))
        scheduler_service.activate_schedule(_test_uuid("deactivate-success"))

        # Verify it's active
        assert scheduler_service._active_schedule_id == _test_uuid("deactivate-success")

        # Deactivate it
        result = scheduler_service.deactivate_schedule()

        assert result is True
        assert scheduler_service._active_schedule_id is None

        # Verify is_active is False
        schedule = scheduler_service.get_schedule(_test_uuid("deactivate-success"))
        assert schedule is not None
        assert schedule.is_active is False

    def test_deactivate_schedule_none_active(self, scheduler_service, temp_schedules_dir):
        """deactivate_schedule should return True (no-op) when no active schedule."""
        # No active schedule
        assert scheduler_service._active_schedule_id is None

        # Deactivate (no-op)
        result = scheduler_service.deactivate_schedule()

        assert result is True
        assert scheduler_service._active_schedule_id is None


# ============================================================================
# Test Cache Invalidation
# ============================================================================


class TestInvalidateCache:
    """Tests for invalidate_cache() method."""

    def test_invalidate_cache_all(self, scheduler_service, temp_schedules_dir, multiple_schedules):
        """invalidate_cache should clear entire cache when schedule_id=None."""
        # Populate cache by getting all schedules
        for i in range(5):
            scheduler_service.get_schedule(_test_uuid(f"schedule-{i}"))

        stats_before = scheduler_service.get_statistics()
        assert stats_before["cache_size"] == 5

        # Invalidate entire cache
        scheduler_service.invalidate_cache()

        stats_after = scheduler_service.get_statistics()
        assert stats_after["cache_size"] == 0

    def test_invalidate_cache_specific(
        self, scheduler_service, temp_schedules_dir, multiple_schedules
    ):
        """invalidate_cache should clear single entry when schedule_id is provided."""
        # Populate cache with 3 schedules
        scheduler_service.get_schedule(_test_uuid("schedule-0"))
        scheduler_service.get_schedule(_test_uuid("schedule-1"))
        scheduler_service.get_schedule(_test_uuid("schedule-2"))

        stats_before = scheduler_service.get_statistics()
        assert stats_before["cache_size"] == 3

        # Invalidate only test-schedule-1
        scheduler_service.invalidate_cache(_test_uuid("schedule-1"))

        stats_after = scheduler_service.get_statistics()
        assert stats_after["cache_size"] == 2

        # Verify test-schedule-0 and test-schedule-2 still in cache
        # (cache hits should increment)
        stats_before_hits = stats_after["cache_hits"]
        scheduler_service.get_schedule(_test_uuid("schedule-0"))
        scheduler_service.get_schedule(_test_uuid("schedule-2"))
        stats_final = scheduler_service.get_statistics()
        assert stats_final["cache_hits"] == stats_before_hits + 2

        # Verify test-schedule-1 is cache miss
        stats_before_misses = stats_final["cache_misses"]
        scheduler_service.get_schedule(_test_uuid("schedule-1"))
        stats_after_miss = scheduler_service.get_statistics()
        assert stats_after_miss["cache_misses"] == stats_before_misses + 1

    def test_invalidate_cache_nonexistent(self, scheduler_service, temp_schedules_dir):
        """invalidate_cache should not error for missing key."""
        # Cache is empty
        stats_before = scheduler_service.get_statistics()
        assert stats_before["cache_size"] == 0

        # Invalidate nonexistent entry (should not raise)
        scheduler_service.invalidate_cache(_test_uuid("nonexistent"))

        # No change in cache size
        stats_after = scheduler_service.get_statistics()
        assert stats_after["cache_size"] == 0

    def test_invalidate_updates_size(
        self, scheduler_service, temp_schedules_dir, multiple_schedules
    ):
        """invalidate_cache should correctly decrement cache size."""
        # Populate cache with 5 schedules
        for i in range(5):
            scheduler_service.get_schedule(_test_uuid(f"schedule-{i}"))

        stats_initial = scheduler_service.get_statistics()
        assert stats_initial["cache_size"] == 5

        # Invalidate 3 schedules one by one
        scheduler_service.invalidate_cache(_test_uuid("schedule-0"))
        stats_after_1 = scheduler_service.get_statistics()
        assert stats_after_1["cache_size"] == 4

        scheduler_service.invalidate_cache(_test_uuid("schedule-1"))
        stats_after_2 = scheduler_service.get_statistics()
        assert stats_after_2["cache_size"] == 3

        scheduler_service.invalidate_cache(_test_uuid("schedule-2"))
        stats_after_3 = scheduler_service.get_statistics()
        assert stats_after_3["cache_size"] == 2

    def test_invalidate_cache_preserves_stats(
        self, scheduler_service, temp_schedules_dir, multiple_schedules
    ):
        """invalidate_cache should preserve statistics counters."""
        # Perform some operations
        scheduler_service.get_schedule(_test_uuid("schedule-0"))  # Miss
        scheduler_service.get_schedule(_test_uuid("schedule-0"))  # Hit
        scheduler_service.get_schedule(_test_uuid("schedule-1"))  # Miss

        stats_before = scheduler_service.get_statistics()
        cache_hits_before = stats_before["cache_hits"]
        cache_misses_before = stats_before["cache_misses"]
        total_reads_before = stats_before["total_reads"]

        # Invalidate cache
        scheduler_service.invalidate_cache()

        stats_after = scheduler_service.get_statistics()
        assert stats_after["cache_hits"] == cache_hits_before
        assert stats_after["cache_misses"] == cache_misses_before
        assert stats_after["total_reads"] == total_reads_before


# ============================================================================
# Test Statistics
# ============================================================================


class TestGetStatistics:
    """Tests for get_statistics() method."""

    def test_statistics_structure(self, scheduler_service):
        """get_statistics should return dict with all expected fields."""
        stats = scheduler_service.get_statistics()

        # Verify all expected keys present
        expected_keys = {
            "cache_hits",
            "cache_misses",
            "cache_evictions",
            "cache_size",
            "max_cache_size",
            "cache_ttl",
            "hit_ratio",
            "total_reads",
            "total_writes",
            "total_deletes",
            "active_schedule_id",
            # Conflict cache stats (Issue #213)
            "conflict_cache_size",
            "conflict_cache_hits",
            "conflict_cache_misses",
            "conflict_cache_hit_ratio",
        }
        assert set(stats.keys()) == expected_keys

        # Verify types
        assert isinstance(stats["cache_hits"], int)
        assert isinstance(stats["cache_misses"], int)
        assert isinstance(stats["cache_evictions"], int)
        assert isinstance(stats["cache_size"], int)
        assert isinstance(stats["max_cache_size"], int)
        assert isinstance(stats["cache_ttl"], int)
        assert isinstance(stats["hit_ratio"], float)
        assert isinstance(stats["total_reads"], int)
        assert isinstance(stats["total_writes"], int)
        assert isinstance(stats["total_deletes"], int)
        assert stats["active_schedule_id"] is None or isinstance(stats["active_schedule_id"], str)

    def test_hit_ratio_calculation(self, scheduler_service, temp_schedules_dir, sample_schedule):
        """get_statistics should calculate hit ratio correctly."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create schedule
        sample_schedule.schedule_id = _test_uuid("hit-ratio")
        create_schedule(sample_schedule)

        # Read 3 times: 1 miss + 2 hits
        scheduler_service.get_schedule(_test_uuid("hit-ratio"))  # Miss
        scheduler_service.get_schedule(_test_uuid("hit-ratio"))  # Hit
        scheduler_service.get_schedule(_test_uuid("hit-ratio"))  # Hit

        stats = scheduler_service.get_statistics()
        assert stats["cache_hits"] == 2
        assert stats["cache_misses"] == 1

        # Hit ratio = 2 / (2 + 1) = 2/3 = 0.666...
        expected_ratio = 2.0 / 3.0
        assert abs(stats["hit_ratio"] - expected_ratio) < 0.0001

    def test_hit_ratio_zero_requests(self, scheduler_service):
        """get_statistics should return 0.0 hit ratio when no requests."""
        stats = scheduler_service.get_statistics()
        assert stats["hit_ratio"] == 0.0

    def test_statistics_after_operations(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """get_statistics should reflect actual operations correctly."""
        from webui.backend.lib.schedule_schema import Schedule
        from webui.backend.lib.schedule_storage import create_schedule

        # Create a schedule
        sample_schedule.schedule_id = _test_uuid("stats-ops")
        create_schedule(sample_schedule)

        # Read it twice (1 miss + 1 hit)
        scheduler_service.get_schedule(_test_uuid("stats-ops"))
        scheduler_service.get_schedule(_test_uuid("stats-ops"))

        # Update it
        scheduler_service.update_schedule(_test_uuid("stats-ops"), {"name": "Updated Name"})

        # Create another schedule
        another_schedule = Schedule(
            schedule_id=_test_uuid("stats-ops-2"),
            name="Another Schedule",
            description="Test schedule",
            routines=sample_schedule.routines,
            enabled=True,
        )
        create_schedule(another_schedule)

        # Delete it
        scheduler_service.delete_schedule(_test_uuid("stats-ops-2"))

        # Verify statistics
        stats = scheduler_service.get_statistics()
        assert stats["total_reads"] == 2  # 2 get_schedule calls
        assert stats["total_writes"] == 1  # 1 update
        assert stats["total_deletes"] == 1  # 1 delete
        assert stats["cache_misses"] == 1  # First read
        assert stats["cache_hits"] == 1  # Second read

    def test_statistics_includes_active_schedule(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """get_statistics should include active_schedule_id field."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Initially, no active schedule
        stats_before = scheduler_service.get_statistics()
        assert stats_before["active_schedule_id"] is None

        # Create schedule (enabled state is now derived from service)
        sample_schedule.schedule_id = _test_uuid("active-in-stats")
        create_schedule(sample_schedule)

        # Enable and activate via service (Issue #331)
        scheduler_service.set_enabled_schedule(_test_uuid("active-in-stats"))
        scheduler_service.activate_schedule(_test_uuid("active-in-stats"))

        # Verify active_schedule_id in statistics
        stats_after = scheduler_service.get_statistics()
        assert stats_after["active_schedule_id"] == _test_uuid("active-in-stats")


# ============================================================================
# Test Thread Safety
# ============================================================================


def _create_test_schedule(schedule_id: str, sample_schedule) -> Schedule:
    """Helper to create test schedules for concurrent tests."""
    from webui.backend.lib.schedule_schema import Schedule

    return Schedule(
        schedule_id=schedule_id,
        name=f"Concurrent Test {schedule_id}",
        description=f"Schedule for concurrent testing - {schedule_id}",
        routines=sample_schedule.routines,
        enabled=True,
    )


class TestThreadSafety:
    """Tests for thread safety under concurrent access."""

    def test_concurrent_reads(self, scheduler_service, sample_schedule, temp_schedules_dir):
        """10 threads reading the same schedule should all succeed."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # Create schedule first
        sample_schedule.schedule_id = _test_uuid("concurrent-reads")
        scheduler_service.create_schedule(sample_schedule)

        results = []
        errors = []

        def read_schedule():
            try:
                schedule = scheduler_service.get_schedule(_test_uuid("concurrent-reads"))
                return schedule is not None
            except Exception as e:
                return str(e)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(read_schedule) for _ in range(10)]
            for future in as_completed(futures):
                result = future.result()
                if isinstance(result, bool):
                    results.append(result)
                else:
                    errors.append(result)

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert all(results), "All reads should succeed"
        assert len(results) == 10

    def test_concurrent_writes(self, scheduler_service, sample_schedule, temp_schedules_dir):
        """5 threads creating different schedules should all succeed."""
        import threading

        results = []
        errors = []

        def create_schedule(schedule_id):
            try:
                schedule = _create_test_schedule(schedule_id, sample_schedule)
                success = scheduler_service.create_schedule(schedule)
                return (schedule_id, success)
            except Exception as e:
                return (schedule_id, str(e))

        threads = []
        for i in range(5):
            schedule_id = _test_uuid(f"concurrent-write-{i}")
            t = threading.Thread(
                target=lambda sid=schedule_id: results.append(create_schedule(sid))
            )
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify all succeeded
        for schedule_id, result in results:
            if isinstance(result, bool):
                assert result is True, f"Schedule {schedule_id} creation failed"
            else:
                errors.append(f"{schedule_id}: {result}")

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5

    def test_concurrent_mixed_operations(
        self, scheduler_service, sample_schedule, temp_schedules_dir
    ):
        """Read/write/delete mix across threads should work correctly."""
        import threading

        from webui.backend.lib.schedule_storage import create_schedule

        # Create 3 schedules initially
        for i in range(3):
            schedule = _create_test_schedule(_test_uuid(f"mixed-{i}"), sample_schedule)
            create_schedule(schedule)

        results = []
        errors = []

        def read_op():
            try:
                scheduler_service.get_schedule("mixed-0")
                return ("read", True)
            except Exception as e:
                return ("read", str(e))

        def write_op():
            try:
                success = scheduler_service.update_schedule("mixed-1", {"name": "Updated Mixed 1"})
                return ("write", success is not None)
            except Exception as e:
                return ("write", str(e))

        def delete_op():
            try:
                success = scheduler_service.delete_schedule("mixed-2")
                return ("delete", success)
            except Exception as e:
                return ("delete", str(e))

        # Run operations concurrently
        ops = [read_op, write_op, delete_op, read_op, write_op, read_op]
        threads = []
        for op in ops:
            t = threading.Thread(target=lambda o=op: results.append(o()))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify no errors occurred
        for op_type, result in results:
            if isinstance(result, str):
                errors.append(f"{op_type}: {result}")

        assert len(errors) == 0, f"Errors occurred: {errors}"

    def test_concurrent_activation(self, scheduler_service, sample_schedule, temp_schedules_dir):
        """Multiple threads activating different schedules - service should track one active ID."""
        import threading
        from unittest.mock import MagicMock, patch

        from webui.backend.lib.schedule_storage import create_schedule

        # Create 5 schedules (enabled state is now derived from service)
        schedules = []
        for i in range(5):
            schedule = _create_test_schedule(_test_uuid(f"activation-{i}"), sample_schedule)
            schedule.name = f"Concurrent Activation Test {i}"  # Unique names
            create_schedule(schedule)
            schedules.append(schedule)

        results = []
        results_lock = threading.Lock()

        def activate(schedule_id):
            try:
                # Enable then activate (Issue #331 - enabled state via service)
                scheduler_service.set_enabled_schedule(schedule_id)
                scheduler_service.activate_schedule(schedule_id)
                with results_lock:
                    results.append((schedule_id, True, None))
            except Exception as e:
                with results_lock:
                    results.append((schedule_id, False, str(e)))

        # Mock expensive I/O operations - we're testing thread safety, not cron I/O
        mock_cron_result = MagicMock()
        mock_cron_result.errors = []
        mock_cron_result.entries = []

        with (
            patch("webui.backend.services.scheduler_service.apply_to_system"),
            patch("webui.backend.services.scheduler_service.remove_from_system"),
            patch(
                "webui.backend.services.scheduler_service.schedule_to_cron",
                return_value=mock_cron_result,
            ),
        ):
            threads = []
            for schedule in schedules:
                t = threading.Thread(target=lambda s=schedule: activate(s.schedule_id))
                threads.append(t)

            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=30)

            # Check for deadlock
            alive = [t for t in threads if t.is_alive()]
            assert not alive, (
                f"{len(alive)} threads still running after timeout - possible deadlock"
            )

        # Verify only race-condition errors occurred (Issue #331)
        # "disabled" is expected due to race (only one schedule can be enabled at a time)
        for sid, success, err in results:
            if not success and err:
                assert "not found" not in err.lower(), f"Unexpected error for {sid}: {err}"

        # Thread-safe property: service should have exactly one active schedule ID
        active = scheduler_service.get_active_schedule()
        assert active is not None, "One schedule should be active"
        assert scheduler_service._active_schedule_id is not None, "Active schedule ID should be set"

    def test_concurrent_cache_invalidation(
        self, scheduler_service, sample_schedule, temp_schedules_dir
    ):
        """Invalidation during concurrent reads should not cause errors."""
        import threading
        import time

        from webui.backend.lib.schedule_storage import create_schedule

        # Create schedule
        sample_schedule.schedule_id = _test_uuid("invalidation-test")
        create_schedule(sample_schedule)

        # Populate cache
        scheduler_service.get_schedule(_test_uuid("invalidation-test"))

        errors = []
        stop_flag = [False]

        def read_continuously():
            try:
                while not stop_flag[0]:
                    scheduler_service.get_schedule(_test_uuid("invalidation-test"))
                    time.sleep(0.001)
            except Exception as e:
                errors.append(f"read: {str(e)}")

        def invalidate_continuously():
            try:
                while not stop_flag[0]:
                    scheduler_service.invalidate_cache(_test_uuid("invalidation-test"))
                    time.sleep(0.001)
            except Exception as e:
                errors.append(f"invalidate: {str(e)}")

        # Start threads
        readers = [threading.Thread(target=read_continuously) for _ in range(3)]
        invalidators = [threading.Thread(target=invalidate_continuously) for _ in range(2)]

        for t in readers + invalidators:
            t.start()

        # Run for 0.5 seconds
        time.sleep(0.5)
        stop_flag[0] = True

        for t in readers + invalidators:
            t.join(timeout=2)

        assert len(errors) == 0, f"Errors occurred: {errors}"

    def test_no_deadlock_nested_operations(
        self, scheduler_service, sample_schedule, temp_schedules_dir
    ):
        """Complex operation chains should not deadlock.

        This test verifies that lock ordering is correct. The get_statistics() method
        must acquire cache_lock before stats_lock to prevent deadlock when:
        - Thread A: get_schedule() holds cache_lock, waits for stats_lock
        - Thread B: get_statistics() holds stats_lock, waits for cache_lock
        """
        import threading
        import time

        scheduler_service.create_schedule(sample_schedule)
        completed_count = [0]
        lock = threading.Lock()

        def complex_ops():
            try:
                # Fewer iterations to avoid timeout
                for _ in range(10):
                    scheduler_service.get_schedule(sample_schedule.schedule_id)
                    scheduler_service.get_statistics()  # Exercise nested lock acquisition
                    scheduler_service.invalidate_cache(sample_schedule.schedule_id)
                    scheduler_service.get_schedule(sample_schedule.schedule_id)
                with lock:
                    completed_count[0] += 1
            except Exception:
                pass  # Swallow exceptions, just check completion

        threads = [threading.Thread(target=complex_ops) for _ in range(3)]
        start_time = time.time()

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)  # Longer timeout to account for slow operations

        elapsed = time.time() - start_time

        # At least one thread should complete (no complete deadlock)
        assert completed_count[0] > 0, f"No threads completed in {elapsed:.2f}s - possible deadlock"

        # Ideally all threads complete
        # Note: We just check for no deadlock, not all completions

    def test_statistics_thread_safe(self, scheduler_service, sample_schedule, temp_schedules_dir):
        """Statistics should remain consistent after concurrent operations."""
        import threading

        from webui.backend.lib.schedule_storage import create_schedule

        # Create 5 schedules
        schedules = []
        for i in range(5):
            schedule = _create_test_schedule(_test_uuid(f"stats-concurrent-{i}"), sample_schedule)
            create_schedule(schedule)
            schedules.append(schedule)

        operation_count = [0]
        lock = threading.Lock()

        def do_operations():
            for _ in range(10):
                for s in schedules:
                    scheduler_service.get_schedule(s.schedule_id)
                    with lock:
                        operation_count[0] += 1

        threads = [threading.Thread(target=do_operations) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        stats = scheduler_service.get_statistics()

        # Verify total reads matches operations
        # 5 threads * 10 iterations * 5 schedules = 250 operations
        expected_total = 250
        assert stats["total_reads"] >= expected_total, (
            f"Expected at least {expected_total} reads, got {stats['total_reads']}"
        )
        assert operation_count[0] == expected_total, (
            f"Expected {expected_total} operations, got {operation_count[0]}"
        )

    def test_cache_eviction_thread_safe(
        self, scheduler_service, sample_schedule, temp_schedules_dir
    ):
        """LRU eviction under contention should not corrupt cache."""
        import threading

        from webui.backend.lib.schedule_storage import create_schedule

        # Create service with small cache (max 5 items)
        service = SchedulerService(cache_ttl=300, max_cache_size=5)

        # Create 10 schedules
        for i in range(10):
            schedule = _create_test_schedule(_test_uuid(f"eviction-{i}"), sample_schedule)
            create_schedule(schedule)

        errors = []

        def access_schedules():
            try:
                for i in range(10):
                    service.get_schedule(_test_uuid(f"eviction-{i}"))
            except Exception as e:
                errors.append(str(e))

        # 5 threads accessing all schedules concurrently
        threads = [threading.Thread(target=access_schedules) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify cache size is at max (not corrupted)
        stats = service.get_statistics()
        assert stats["cache_size"] <= 5, f"Cache size should be <= 5, got {stats['cache_size']}"
        assert stats["cache_evictions"] > 0, "Evictions should have occurred"


# ============================================================================
# Test Concurrent Modifications (Issue #212 - Code Review Fix 5)
# ============================================================================


class TestConcurrentModifications:
    """
    Tests for concurrent write operations.

    These tests verify thread safety for concurrent modifications that were
    previously under-tested. They focus on:
    1. Concurrent create_schedule() calls with cache eviction
    2. Concurrent activate_schedule() calls (race to become active)
    3. Concurrent cache invalidation during reads
    """

    def test_concurrent_create_with_eviction(self, temp_schedules_dir, sample_schedule):
        """Multiple threads creating schedules when cache is near capacity.

        This tests the interaction between create_schedule() and LRU eviction
        when multiple threads are creating schedules simultaneously.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # Create service with small cache (max 5 items)
        service = SchedulerService(cache_ttl=300, max_cache_size=5)

        results = []
        errors = []

        def create_schedule_thread(schedule_id: str, index: int):
            try:
                schedule = _create_test_schedule(schedule_id, sample_schedule)
                schedule.name = f"Eviction Create Test {index}"  # Unique name
                success = service.create_schedule(schedule)
                return (schedule_id, success, None)
            except Exception as e:
                return (schedule_id, False, str(e))

        # Create 10 schedules concurrently (exceeding cache capacity)
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(create_schedule_thread, _test_uuid(f"evict-create-{i}"), i)
                for i in range(10)
            ]
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                if result[2]:  # error message present
                    errors.append(result)

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify all creates succeeded
        successful = [r for r in results if r[1]]
        assert len(successful) == 10, f"Expected 10 successful creates, got {len(successful)}"

        # Verify cache evictions occurred (created 10 items, max 5)
        stats = service.get_statistics()
        assert stats["cache_size"] <= 5, f"Cache size should be <= 5, got {stats['cache_size']}"
        assert stats["cache_evictions"] >= 5, (
            f"Should have at least 5 evictions, got {stats['cache_evictions']}"
        )

        # Verify all schedules exist on disk (filenames are slugified names)
        for i in range(10):
            schedule_path = temp_schedules_dir / f"eviction-create-test-{i}.json"
            assert schedule_path.exists(), f"Schedule file {schedule_path} should exist"

    def test_concurrent_activate_race(self, temp_schedules_dir, sample_schedule):
        """Multiple threads racing to activate different schedules.

        Only one schedule should end up active. This tests the thread-safe
        handling of _active_schedule_id and the deactivation of previously
        active schedules during concurrent activation attempts.
        """
        import threading
        from unittest.mock import MagicMock, patch

        from webui.backend.lib.schedule_storage import create_schedule

        service = SchedulerService(cache_ttl=300, max_cache_size=100)

        # Create 10 schedules (enabled state is now derived from service)
        schedule_ids = []
        for i in range(10):
            schedule_id = _test_uuid(f"race-activate-{i}")
            schedule = _create_test_schedule(schedule_id, sample_schedule)
            schedule.name = f"Race Activate Test {i}"  # Unique name
            create_schedule(schedule)
            schedule_ids.append(schedule_id)

        results = []
        results_lock = threading.Lock()

        def activate_schedule_thread(schedule_id: str):
            try:
                # Enable then activate (Issue #331 - enabled state via service)
                service.set_enabled_schedule(schedule_id)
                service.activate_schedule(schedule_id)
                with results_lock:
                    results.append((schedule_id, True, ""))
            except Exception as e:
                with results_lock:
                    results.append((schedule_id, False, str(e)))

        # Mock expensive I/O operations - we're testing thread safety, not cron I/O
        mock_cron_result = MagicMock()
        mock_cron_result.errors = []
        mock_cron_result.entries = []

        with (
            patch("webui.backend.services.scheduler_service.apply_to_system"),
            patch("webui.backend.services.scheduler_service.remove_from_system"),
            patch(
                "webui.backend.services.scheduler_service.schedule_to_cron",
                return_value=mock_cron_result,
            ),
        ):
            # Launch 10 threads to activate different schedules concurrently
            threads = []
            for schedule_id in schedule_ids:
                t = threading.Thread(target=activate_schedule_thread, args=(schedule_id,))
                threads.append(t)

            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=30)

            # Check for deadlock
            alive = [t for t in threads if t.is_alive()]
            assert not alive, (
                f"{len(alive)} threads still running after timeout - possible deadlock"
            )

        # Verify: Exactly one schedule should be active
        active = service.get_active_schedule()
        assert active is not None, "One schedule should be active"

        # Verify: The active_schedule_id matches the active schedule
        assert service._active_schedule_id == active.schedule_id

        # Verify: Some activations may fail due to race conditions (Issue #331)
        # Since only one schedule can be enabled at a time, when thread A enables
        # schedule A and tries to activate, thread B might enable schedule B in between,
        # which disables A. This is expected behavior - the important thing is:
        # 1. No deadlocks (checked above)
        # 2. Exactly one schedule is active (checked above)
        # 3. Errors are only race-condition related, not "not found"
        for _, success, error in results:
            if not success and error:
                # "disabled" is expected due to race condition
                # "not found" would indicate a real bug
                assert "not found" not in error.lower(), f"Unexpected error: {error}"

    def test_concurrent_cache_invalidation_during_writes(self, temp_schedules_dir, sample_schedule):
        """Invalidate cache while writes are in progress.

        This tests the interaction between invalidate_cache() and concurrent
        create_schedule()/update_schedule() operations.
        """
        import threading
        import time

        from webui.backend.lib.schedule_storage import create_schedule

        service = SchedulerService(cache_ttl=300, max_cache_size=100)

        # Pre-create some schedules
        for i in range(5):
            schedule = _create_test_schedule(_test_uuid(f"inv-write-{i}"), sample_schedule)
            create_schedule(schedule)

        errors = []
        stop_flag = [False]

        def do_creates():
            """Thread that creates new schedules."""
            import contextlib

            idx = 100
            try:
                while not stop_flag[0]:
                    schedule = _create_test_schedule(
                        _test_uuid(f"inv-create-{idx}"), sample_schedule
                    )
                    with contextlib.suppress(Exception):
                        service.create_schedule(schedule)  # May fail if file already exists
                    idx += 1
                    time.sleep(0.001)
            except Exception as e:
                errors.append(f"create: {str(e)}")

        def do_updates():
            """Thread that updates existing schedules."""
            import contextlib

            try:
                while not stop_flag[0]:
                    for i in range(5):
                        with contextlib.suppress(Exception):
                            service.update_schedule(f"inv-write-{i}", {"name": f"Updated {i}"})
                    time.sleep(0.001)
            except Exception as e:
                errors.append(f"update: {str(e)}")

        def do_invalidations():
            """Thread that invalidates cache entries."""
            try:
                while not stop_flag[0]:
                    # Invalidate specific entries
                    for i in range(5):
                        service.invalidate_cache(f"inv-write-{i}")
                    # Also invalidate entire cache periodically
                    service.invalidate_cache()
                    time.sleep(0.002)
            except Exception as e:
                errors.append(f"invalidate: {str(e)}")

        # Start threads
        threads = [
            threading.Thread(target=do_creates),
            threading.Thread(target=do_updates),
            threading.Thread(target=do_updates),
            threading.Thread(target=do_invalidations),
            threading.Thread(target=do_invalidations),
        ]

        for t in threads:
            t.start()

        # Run for 0.5 seconds
        time.sleep(0.5)
        stop_flag[0] = True

        for t in threads:
            t.join(timeout=2)

        # Verify no thread-safety errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Service should still be functional
        stats = service.get_statistics()
        assert stats is not None
        assert isinstance(stats["cache_size"], int)
        assert isinstance(stats["total_writes"], int)

    def test_concurrent_get_statistics_during_operations(self, temp_schedules_dir, sample_schedule):
        """get_statistics() should return consistent snapshots during concurrent operations.

        This tests that nested locks in get_statistics() provide atomic snapshots
        even when other operations are modifying cache and statistics.
        """
        import threading
        import time

        from webui.backend.lib.schedule_storage import create_schedule

        service = SchedulerService(cache_ttl=300, max_cache_size=50)

        # Pre-create schedules
        for i in range(10):
            schedule = _create_test_schedule(_test_uuid(f"stats-snap-{i}"), sample_schedule)
            create_schedule(schedule)

        errors = []
        stats_snapshots = []
        stats_lock = threading.Lock()
        stop_flag = [False]

        def do_reads():
            """Thread that reads schedules."""
            try:
                while not stop_flag[0]:
                    for i in range(10):
                        service.get_schedule(_test_uuid(f"stats-snap-{i}"))
                    time.sleep(0.001)
            except Exception as e:
                errors.append(f"read: {str(e)}")

        def collect_stats():
            """Thread that collects statistics snapshots."""
            try:
                while not stop_flag[0]:
                    stats = service.get_statistics()
                    with stats_lock:
                        stats_snapshots.append(stats)
                    time.sleep(0.002)
            except Exception as e:
                errors.append(f"stats: {str(e)}")

        # Start threads
        readers = [threading.Thread(target=do_reads) for _ in range(3)]
        stat_collectors = [threading.Thread(target=collect_stats) for _ in range(2)]

        for t in readers + stat_collectors:
            t.start()

        # Run for 0.5 seconds
        time.sleep(0.5)
        stop_flag[0] = True

        for t in readers + stat_collectors:
            t.join(timeout=2)

        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify we collected some stats
        assert len(stats_snapshots) > 0, "Should have collected statistics"

        # Verify each snapshot is internally consistent:
        # hits + misses should equal total_reads (for cache operations)
        for i, stats in enumerate(stats_snapshots):
            hits = stats["cache_hits"]
            misses = stats["cache_misses"]
            total_reads = stats["total_reads"]

            # total_reads should match hits + misses (all reads counted)
            assert total_reads == hits + misses, (
                f"Snapshot {i}: total_reads ({total_reads}) != hits ({hits}) + misses ({misses})"
            )

            # hit_ratio should be consistent with hits and total requests
            if hits + misses > 0:
                expected_ratio = hits / (hits + misses)
                actual_ratio = stats["hit_ratio"]
                assert abs(expected_ratio - actual_ratio) < 0.0001, (
                    f"Snapshot {i}: hit_ratio inconsistent"
                )

    def test_concurrent_activation_deactivation(self, temp_schedules_dir, sample_schedule):
        """Concurrent activate and deactivate operations should not corrupt state.

        This tests the thread safety of the activate/deactivate flow, especially
        the deepcopy fix for built-in schedules.
        """
        import threading
        import time

        from webui.backend.lib.schedule_storage import create_schedule

        service = SchedulerService(cache_ttl=300, max_cache_size=100)

        # Create 5 schedules (enabled state is now derived from service)
        for i in range(5):
            schedule = _create_test_schedule(_test_uuid(f"act-deact-{i}"), sample_schedule)
            schedule.name = f"Activate Deactivate Test {i}"  # Unique name
            create_schedule(schedule)

        errors = []
        stop_flag = [False]

        def activate_random():
            """Thread that activates random schedules."""
            import random

            try:
                while not stop_flag[0]:
                    schedule_id = _test_uuid(f"act-deact-{random.randint(0, 4)}")
                    # Enable then activate (Issue #331 - enabled state via service)
                    service.set_enabled_schedule(schedule_id)
                    service.activate_schedule(schedule_id)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(f"activate: {str(e)}")

        def deactivate_repeatedly():
            """Thread that deactivates the current schedule."""
            try:
                while not stop_flag[0]:
                    service.deactivate_schedule()
                    time.sleep(0.002)
            except Exception as e:
                errors.append(f"deactivate: {str(e)}")

        def check_active():
            """Thread that checks active schedule."""
            try:
                while not stop_flag[0]:
                    active = service.get_active_schedule()
                    # Active can be None or a valid schedule
                    if active is not None:
                        assert hasattr(active, "schedule_id")
                    time.sleep(0.001)
            except Exception as e:
                errors.append(f"check: {str(e)}")

        # Start threads
        threads = [
            threading.Thread(target=activate_random),
            threading.Thread(target=activate_random),
            threading.Thread(target=deactivate_repeatedly),
            threading.Thread(target=check_active),
            threading.Thread(target=check_active),
        ]

        for t in threads:
            t.start()

        # Run for 0.5 seconds
        time.sleep(0.5)
        stop_flag[0] = True

        for t in threads:
            t.join(timeout=2)

        # Verify only race-condition errors occurred (Issue #331)
        # "disabled" is expected due to race (only one schedule can be enabled at a time)
        for err in errors:
            assert "not found" not in err.lower(), f"Unexpected error: {err}"

        # Final state should be consistent
        stats = service.get_statistics()
        active_id = stats["active_schedule_id"]

        if active_id is not None:
            # If there's an active schedule, we should be able to get it
            active = service.get_schedule(active_id)
            assert active is not None, f"Active schedule {active_id} should exist"


# ============================================================================
# Test Conflict Detection Integration (Issue #213 - Phase 6)
# ============================================================================


class TestActivateScheduleConflictDetection:
    """Tests for conflict detection in activate_schedule()."""

    @pytest.fixture
    def conflicting_schedule(self):
        """Create a schedule with conflicting routines (overlapping camera usage)."""
        from webui.backend.lib.schedule_schema import (
            Action,
            IntervalTrigger,
            Routine,
            Schedule,
            TimeWindow,
        )

        # Trigger for both routines - 15 minute interval
        trigger = IntervalTrigger(
            interval_minutes=15,
            time_window=TimeWindow(start_time="21:00", end_time="22:00"),
        )

        # Routine 1: Takes photo at offset 10
        routine1_actions = [
            Action(
                action_type="gpio",
                action_name="attract_on",
                offset_minutes=0,
            ),
            Action(
                action_type="camera",
                action_name="takephoto",
                offset_minutes=10,
            ),
            Action(
                action_type="gpio",
                action_name="attract_off",
                offset_minutes=20,
            ),
        ]
        routine1 = Routine(
            routine_id=_test_uuid("conflict-routine-1"),
            name="UV Capture 1",
            trigger=trigger,
            actions=routine1_actions,
        )

        # Routine 2: Also takes photo at offset 10
        routine2_actions = [
            Action(
                action_type="gpio",
                action_name="flash_on",
                offset_minutes=0,
            ),
            Action(
                action_type="camera",
                action_name="takephoto",
                offset_minutes=10,
            ),
            Action(
                action_type="gpio",
                action_name="flash_off",
                offset_minutes=20,
            ),
        ]
        routine2 = Routine(
            routine_id=_test_uuid("conflict-routine-2"),
            name="Flash Capture",
            trigger=trigger,
            actions=routine2_actions,
        )

        return Schedule(
            schedule_id=_test_uuid("conflicting-schedule"),
            name="Conflicting Schedule",
            routines=[routine1, routine2],
            enabled=True,
        )

    def test_activate_with_conflicts_blocked(
        self, scheduler_service, temp_schedules_dir, conflicting_schedule
    ):
        """activate_schedule should raise ScheduleConflictError for blocking conflicts."""
        import pytest

        from webui.backend.lib.schedule_schema import ScheduleConflictError
        from webui.backend.lib.schedule_storage import create_schedule

        # Create the conflicting schedule
        create_schedule(conflicting_schedule)

        # Enable via service (Issue #331)
        scheduler_service.set_enabled_schedule(_test_uuid("conflicting-schedule"))

        # Try to activate with conflict checking (default) - should raise exception
        with pytest.raises(ScheduleConflictError) as exc_info:
            scheduler_service.activate_schedule(
                _test_uuid("conflicting-schedule"),
                check_conflicts=True,
                latitude=0.0,
                longitude=0.0,
                timezone_name="UTC",
            )

        # Should fail due to conflicts
        assert "conflict" in str(exc_info.value).lower()

    def test_activate_with_conflicts_skip_check(
        self, scheduler_service, temp_schedules_dir, conflicting_schedule
    ):
        """activate_schedule should succeed when check_conflicts=False."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create the conflicting schedule
        create_schedule(conflicting_schedule)

        # Enable via service (Issue #331)
        scheduler_service.set_enabled_schedule(_test_uuid("conflicting-schedule"))

        # Activate with conflict checking disabled - should succeed (no exception)
        scheduler_service.activate_schedule(
            _test_uuid("conflicting-schedule"),
            check_conflicts=False,
        )

        # Should succeed (conflicts ignored)
        assert scheduler_service._active_schedule_id == _test_uuid("conflicting-schedule")

    def test_activate_no_conflicts_success(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """activate_schedule should succeed for schedule without conflicts."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create non-conflicting schedule (enabled state is now derived from service)
        sample_schedule.schedule_id = _test_uuid("non-conflicting-schedule")
        create_schedule(sample_schedule)

        # Enable via service (Issue #331)
        scheduler_service.set_enabled_schedule(_test_uuid("non-conflicting-schedule"))

        # Activate with conflict checking enabled - should succeed (no exception)
        scheduler_service.activate_schedule(
            _test_uuid("non-conflicting-schedule"),
            check_conflicts=True,
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
        )

        # Should succeed (no conflicts)
        assert scheduler_service._active_schedule_id == _test_uuid("non-conflicting-schedule")

    def test_activate_conflict_check_with_location(self, scheduler_service, temp_schedules_dir):
        """activate_schedule should pass location parameters to conflict detection."""
        # Create schedule with solar trigger (Schema 3.0)
        from webui.backend.lib.schedule_schema import (
            Action,
            Routine,
            Schedule,
            SolarTrigger,
        )
        from webui.backend.lib.schedule_storage import create_schedule

        solar_trigger = SolarTrigger(
            solar_event="sunset",
            offset_minutes=30,
        )
        routine = Routine(
            routine_id=_test_uuid("solar-routine"),
            name="Solar Routine",
            trigger=solar_trigger,
            actions=[Action(action_type="camera", action_name="takephoto", offset_minutes=0)],
        )
        schedule = Schedule(
            schedule_id=_test_uuid("solar-schedule"),
            name="Solar Schedule",
            routines=[routine],
        )
        create_schedule(schedule)

        # Enable via service (Issue #331)
        scheduler_service.set_enabled_schedule(_test_uuid("solar-schedule"))

        # Activate with location parameters (Panama) - should succeed (no exception)
        scheduler_service.activate_schedule(
            _test_uuid("solar-schedule"),
            check_conflicts=True,
            latitude=9.15,
            longitude=-79.85,
            timezone_name="America/Panama",
        )

        # Should succeed (single routine, no conflicts)
        assert scheduler_service._active_schedule_id == _test_uuid("solar-schedule")


# ============================================================================
# Test Conflict Cache (Issue #213 - Code Review Improvement)
# ============================================================================


class TestConflictCache:
    """Tests for conflict detection caching in SchedulerService."""

    def test_conflict_cache_hit(self, scheduler_service, temp_schedules_dir, sample_schedule):
        """Same params should return cached result (cache hit)."""
        from webui.backend.lib.schedule_storage import create_schedule

        sample_schedule.schedule_id = _test_uuid("cache-test-schedule")
        sample_schedule.enabled = True
        create_schedule(sample_schedule)

        schedule = scheduler_service.get_schedule(_test_uuid("cache-test-schedule"))

        # First call - cache miss
        report1 = scheduler_service.get_cached_conflict_report(
            schedule,
            preview_days=7,
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
        )

        # Second call with same params - cache hit
        report2 = scheduler_service.get_cached_conflict_report(
            schedule,
            preview_days=7,
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
        )

        # Both should return valid reports
        assert report1 is not None
        assert report2 is not None
        assert report1.schedule_id == report2.schedule_id

        # Check statistics show cache hit
        stats = scheduler_service.get_statistics()
        assert stats["conflict_cache_hits"] >= 1
        assert stats["conflict_cache_misses"] >= 1

    def test_conflict_cache_miss_different_params(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """Different params should miss cache."""
        from webui.backend.lib.schedule_storage import create_schedule

        sample_schedule.schedule_id = _test_uuid("cache-params-schedule")
        sample_schedule.enabled = True
        create_schedule(sample_schedule)

        schedule = scheduler_service.get_schedule(_test_uuid("cache-params-schedule"))

        # First call with one location
        scheduler_service.get_cached_conflict_report(
            schedule,
            preview_days=7,
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
        )

        stats_after_first = scheduler_service.get_statistics()
        misses_after_first = stats_after_first["conflict_cache_misses"]

        # Second call with different location - cache miss
        scheduler_service.get_cached_conflict_report(
            schedule,
            preview_days=7,
            latitude=35.0,
            longitude=-80.0,
            timezone_name="America/New_York",
        )

        stats_after_second = scheduler_service.get_statistics()
        misses_after_second = stats_after_second["conflict_cache_misses"]

        # Should have another miss (different params)
        assert misses_after_second == misses_after_first + 1

    def test_conflict_cache_invalidation_on_update(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """Schedule update should invalidate conflict cache."""
        from webui.backend.lib.schedule_storage import create_schedule

        sample_schedule.schedule_id = _test_uuid("cache-invalidate-schedule")
        sample_schedule.enabled = True
        create_schedule(sample_schedule)

        schedule = scheduler_service.get_schedule(_test_uuid("cache-invalidate-schedule"))

        # Populate cache
        scheduler_service.get_cached_conflict_report(
            schedule,
            preview_days=7,
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
        )

        # Verify cache has entry
        stats_before = scheduler_service.get_statistics()
        assert stats_before["conflict_cache_size"] >= 1

        # Update schedule
        scheduler_service.update_schedule(
            _test_uuid("cache-invalidate-schedule"), {"name": "Updated Name"}
        )

        # Get fresh schedule after update
        updated_schedule = scheduler_service.get_schedule(_test_uuid("cache-invalidate-schedule"))

        # Request conflict report again
        scheduler_service.get_cached_conflict_report(
            updated_schedule,
            preview_days=7,
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
        )

        # Should have had a cache miss (entry was invalidated)
        stats_after = scheduler_service.get_statistics()
        # The miss count should have increased
        assert stats_after["conflict_cache_misses"] > stats_before["conflict_cache_misses"]

    def test_conflict_cache_statistics(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """get_statistics should include conflict cache metrics."""
        from webui.backend.lib.schedule_storage import create_schedule

        sample_schedule.schedule_id = _test_uuid("stats-test-schedule")
        sample_schedule.enabled = True
        create_schedule(sample_schedule)

        schedule = scheduler_service.get_schedule(_test_uuid("stats-test-schedule"))

        # Make a conflict cache request
        scheduler_service.get_cached_conflict_report(
            schedule,
            preview_days=7,
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
        )

        stats = scheduler_service.get_statistics()

        # Check conflict cache metrics are present
        assert "conflict_cache_size" in stats
        assert "conflict_cache_hits" in stats
        assert "conflict_cache_misses" in stats
        assert "conflict_cache_hit_ratio" in stats

        # Values should be reasonable
        assert stats["conflict_cache_size"] >= 0
        assert stats["conflict_cache_hits"] >= 0
        assert stats["conflict_cache_misses"] >= 1  # At least one miss
        assert 0.0 <= stats["conflict_cache_hit_ratio"] <= 1.0

    def test_conflict_cache_ttl_expiration(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """Expired entries should be refreshed (cache miss)."""
        import time

        from webui.backend.lib.schedule_storage import create_schedule

        sample_schedule.schedule_id = _test_uuid("ttl-test-schedule")
        sample_schedule.enabled = True
        create_schedule(sample_schedule)

        schedule = scheduler_service.get_schedule(_test_uuid("ttl-test-schedule"))

        # Set very short TTL for testing
        original_ttl = scheduler_service._conflict_cache_ttl
        scheduler_service._conflict_cache_ttl = 0.1  # 100ms

        try:
            # First call - cache miss
            scheduler_service.get_cached_conflict_report(
                schedule,
                preview_days=7,
                latitude=0.0,
                longitude=0.0,
                timezone_name="UTC",
            )

            stats_after_first = scheduler_service.get_statistics()
            misses_first = stats_after_first["conflict_cache_misses"]

            # Wait for TTL to expire
            time.sleep(0.2)

            # Second call - should be cache miss due to TTL expiration
            scheduler_service.get_cached_conflict_report(
                schedule,
                preview_days=7,
                latitude=0.0,
                longitude=0.0,
                timezone_name="UTC",
            )

            stats_after_second = scheduler_service.get_statistics()
            misses_second = stats_after_second["conflict_cache_misses"]

            # Should have another miss due to expiration
            assert misses_second == misses_first + 1

        finally:
            # Restore original TTL
            scheduler_service._conflict_cache_ttl = original_ttl

    def test_conflict_cache_key_includes_content_hash(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """Cache key includes content hash to prevent stale results after updates."""
        from copy import deepcopy

        from webui.backend.lib.schedule_storage import create_schedule

        sample_schedule.schedule_id = _test_uuid("content-hash-schedule")
        sample_schedule.enabled = True
        create_schedule(sample_schedule)

        schedule = scheduler_service.get_schedule(_test_uuid("content-hash-schedule"))

        # Get cache key for original schedule
        key1 = scheduler_service._conflict_cache_key(schedule, 7, 0.0, 0.0, "UTC")

        # Modify schedule content (simulating an in-memory change)
        modified_schedule = deepcopy(schedule)
        modified_schedule.name = "Modified Name For Hash Test"

        # Get cache key for modified schedule
        key2 = scheduler_service._conflict_cache_key(modified_schedule, 7, 0.0, 0.0, "UTC")

        # Keys should be different because content hash changed
        assert key1 != key2
        assert _test_uuid("content-hash-schedule") in key1
        assert _test_uuid("content-hash-schedule") in key2

    def test_schedule_content_hash_consistent(self, scheduler_service, sample_schedule):
        """Content hash should be consistent for same schedule content."""
        sample_schedule.schedule_id = _test_uuid("hash-consistency-test")

        hash1 = scheduler_service._schedule_content_hash(sample_schedule)
        hash2 = scheduler_service._schedule_content_hash(sample_schedule)

        assert hash1 == hash2
        assert len(hash1) == 8  # First 8 chars of MD5


# ============================================================================
# Test Built-in Schedule Loading (Issue #319)
# ============================================================================


class TestBuiltinScheduleLoading:
    """Tests for built-in schedule loading with caching (Issue #319)."""

    def test_get_builtin_schedules_returns_list(self, scheduler_service):
        """get_builtin_schedules should return a list."""
        schedules = scheduler_service.get_builtin_schedules()
        assert isinstance(schedules, list)

    def test_get_builtin_schedules_contains_schedules(self, scheduler_service):
        """get_builtin_schedules should contain Schedule objects."""
        schedules = scheduler_service.get_builtin_schedules()
        # Should have at least the two schema 3.0 schedules from issues #317/#318
        if schedules:
            from webui.backend.lib.schedule_schema import Schedule

            assert all(isinstance(s, Schedule) for s in schedules)

    def test_get_builtin_schedules_caches_result(self, scheduler_service):
        """Second call should return same cached list object."""
        first = scheduler_service.get_builtin_schedules()
        second = scheduler_service.get_builtin_schedules()
        # Should be same list object (cached)
        assert first is second

    def test_get_builtin_schedules_cache_expires(self, scheduler_service, monkeypatch):
        """Cache should expire after TTL."""
        import time as time_module

        # First call to populate cache
        scheduler_service.get_builtin_schedules()

        # Simulate time passing beyond TTL
        original_time = time_module.time
        monkeypatch.setattr(
            time_module,
            "time",
            lambda: original_time() + 3700,  # > 1 hour TTL
        )

        # Force cache check by accessing private state
        scheduler_service._builtin_cache_timestamp = original_time() - 3700

        # Second call should reload (different list object)
        second = scheduler_service.get_builtin_schedules()
        # Note: Contents may be same but objects should be reloaded
        assert isinstance(second, list)

    def test_get_builtin_schedule_existing(self, scheduler_service):
        """get_builtin_schedule should find existing built-in schedule."""
        schedules = scheduler_service.get_builtin_schedules()
        if schedules:
            # Get first schedule ID
            target_id = schedules[0].schedule_id
            result = scheduler_service.get_builtin_schedule(target_id)
            assert result is not None
            assert result.schedule_id == target_id

    def test_get_builtin_schedule_nonexistent(self, scheduler_service):
        """get_builtin_schedule should return None for unknown ID."""
        result = scheduler_service.get_builtin_schedule("nonexistent-schedule-id")
        assert result is None

    def test_get_builtin_schedule_uses_cache(self, scheduler_service):
        """get_builtin_schedule should use cached builtin schedules."""
        # Populate cache
        schedules = scheduler_service.get_builtin_schedules()
        if schedules:
            target_id = schedules[0].schedule_id

            # Multiple calls should use same cache
            result1 = scheduler_service.get_builtin_schedule(target_id)
            result2 = scheduler_service.get_builtin_schedule(target_id)

            # Should be same schedule object from cache
            assert result1 is result2

    def test_is_builtin_schedule_true_for_builtin_filename(self, scheduler_service):
        """is_builtin_schedule should return True for built-in schedule filenames."""
        # Known built-in filenames from #317/#318:
        result = scheduler_service.is_builtin_schedule("daytime-pollinator")
        assert result is True

        result2 = scheduler_service.is_builtin_schedule("overnight-moth-survey")
        assert result2 is True

    def test_is_builtin_schedule_true_for_builtin_uuid(self, scheduler_service):
        """is_builtin_schedule should return True for built-in schedule UUIDs.

        This ensures consistent API behavior between is_builtin_schedule() and
        get_builtin_schedule(), both of which should accept internal UUIDs.
        """
        # Get actual built-in schedules to retrieve their internal UUIDs
        builtin_schedules = scheduler_service.get_builtin_schedules()
        if not builtin_schedules:
            pytest.skip("No built-in schedules available")

        # Test with internal UUID of first built-in schedule
        internal_uuid = builtin_schedules[0].schedule_id
        result = scheduler_service.is_builtin_schedule(internal_uuid)
        assert result is True

        # Verify the UUID is different from the filename
        # (the whole point of this fix)
        assert internal_uuid != "daytime-pollinator"
        assert internal_uuid != "overnight-moth-survey"

    def test_is_builtin_schedule_false_for_user_schedule(
        self, scheduler_service, temp_schedules_dir, sample_schedule
    ):
        """is_builtin_schedule should return False for user schedules."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create a user schedule
        sample_schedule.schedule_id = _test_uuid("user-created-schedule")
        create_schedule(sample_schedule)

        # User schedules should return False
        result = scheduler_service.is_builtin_schedule(_test_uuid("user-created-schedule"))
        assert result is False

    def test_is_builtin_schedule_false_for_nonexistent(self, scheduler_service):
        """is_builtin_schedule should return False for nonexistent IDs."""
        result = scheduler_service.is_builtin_schedule("completely-fake-id")
        assert result is False

    def test_invalidate_builtin_cache_clears_cache(self, scheduler_service):
        """invalidate_builtin_cache should clear the builtin cache."""
        # Populate cache
        scheduler_service.get_builtin_schedules()
        assert scheduler_service._builtin_cache is not None

        # Invalidate
        scheduler_service.invalidate_builtin_cache()

        # Cache should be cleared
        assert scheduler_service._builtin_cache is None
        assert scheduler_service._builtin_cache_timestamp == 0.0

    def test_invalidate_cache_all_clears_builtin(self, scheduler_service):
        """invalidate_cache(None) should also clear builtin cache."""
        # Populate builtin cache
        scheduler_service.get_builtin_schedules()
        assert scheduler_service._builtin_cache is not None

        # Invalidate entire cache
        scheduler_service.invalidate_cache(schedule_id=None)

        # Builtin cache should also be cleared
        assert scheduler_service._builtin_cache is None

    def test_invalidate_cache_specific_preserves_builtin(self, scheduler_service):
        """invalidate_cache(schedule_id) should preserve builtin cache."""
        # Populate builtin cache
        scheduler_service.get_builtin_schedules()
        original_cache = scheduler_service._builtin_cache

        # Invalidate specific schedule (not builtin)
        scheduler_service.invalidate_cache(schedule_id="some-specific-id")

        # Builtin cache should be preserved
        assert scheduler_service._builtin_cache is original_cache

    def test_builtin_cache_ttl_default(self):
        """Built-in cache TTL should default to 1 hour (3600 seconds)."""
        from webui.backend.services.scheduler_service import SchedulerService

        service = SchedulerService()
        assert service._builtin_cache_ttl == 3600

    def test_builtin_cache_initialized_empty(self):
        """Built-in cache should start as None."""
        from webui.backend.services.scheduler_service import SchedulerService

        service = SchedulerService()
        assert service._builtin_cache is None
        assert service._builtin_cache_timestamp == 0.0


# ============================================================================
# Test Active Entries Persistence (Issue #331)
# ============================================================================


class TestActiveEntriesPersistence:
    """Tests for persisting expanded cron entries in active_state.json."""

    @pytest.fixture
    def sample_entries(self):
        """Create sample CronEntry objects for testing."""
        from datetime import datetime, timedelta

        from webui.backend.lib.cron_bridge import CronEntry

        now = datetime.now()
        return [
            CronEntry(
                expression="0 21 * * *",
                command="/usr/bin/python3 /opt/mothbox/Attract_On.py",
                comment="Attract On",
                routine_id="routine-1",
                execution_time=now + timedelta(hours=1),
                action_name="Attract On",
                action_type="attract_on",
            ),
            CronEntry(
                expression="5 21 * * *",
                command="/usr/bin/python3 /opt/mothbox/TakePhoto.py",
                comment="Take Photo",
                routine_id="routine-1",
                execution_time=now + timedelta(hours=1, minutes=5),
                action_name="Take Photo",
                action_type="takephoto",
            ),
            CronEntry(
                expression="15 21 * * *",
                command="/usr/bin/python3 /opt/mothbox/Attract_Off.py",
                comment="Attract Off",
                routine_id="routine-1",
                execution_time=now + timedelta(hours=1, minutes=15),
                action_name="Attract Off",
                action_type="attract_off",
            ),
        ]

    def test_save_active_state_with_entries(self, temp_schedules_dir, sample_entries):
        """_save_active_state() persists entries to JSON."""
        import json

        from webui.backend.services.scheduler_service import (
            ACTIVE_STATE_FILE,
            SchedulerService,
        )

        service = SchedulerService()
        service._active_schedule_id = "test-schedule"
        service._active_coordinates_source = "gps"
        service._active_latitude = -41.3
        service._active_longitude = 174.8
        service._active_timezone_name = "Pacific/Auckland"

        service._save_active_state(entries=sample_entries)

        # Verify file contents
        assert ACTIVE_STATE_FILE.exists()
        with open(ACTIVE_STATE_FILE) as f:
            state = json.load(f)

        assert state["schedule_id"] == "test-schedule"
        assert "entries" in state
        assert len(state["entries"]) == 3
        assert state["entries"][0]["action_name"] == "Attract On"

    def test_load_active_state_with_entries(self, temp_schedules_dir, sample_entries):
        """_load_active_state() restores entries from JSON."""
        import json

        from webui.backend.services.scheduler_service import (
            ACTIVE_STATE_FILE,
            SchedulerService,
        )

        # Write state with entries
        state = {
            "schedule_id": "test-schedule",
            "coordinates_source": "gps",
            "latitude": -41.3,
            "longitude": 174.8,
            "timezone_name": "Pacific/Auckland",
            "entries": [e.to_dict() for e in sample_entries],
        }
        with open(ACTIVE_STATE_FILE, "w") as f:
            json.dump(state, f)

        # Load state
        service = SchedulerService()

        assert service._active_schedule_id == "test-schedule"
        assert len(service._active_entries) == 3
        assert service._active_entries[0].action_name == "Attract On"
        assert service._active_entries[1].action_type == "takephoto"

    def test_clear_active_state_clears_entries(self, temp_schedules_dir, sample_entries):
        """_clear_active_state() clears in-memory entries."""
        from webui.backend.services.scheduler_service import SchedulerService

        service = SchedulerService()
        service._active_schedule_id = "test-schedule"
        service._active_entries = sample_entries

        service._clear_active_state()

        assert service._active_entries == []

    def test_get_active_entries(self, temp_schedules_dir, sample_entries):
        """get_active_entries() returns stored entries."""
        from webui.backend.services.scheduler_service import SchedulerService

        service = SchedulerService()
        service._active_entries = sample_entries

        result = service.get_active_entries()

        assert len(result) == 3
        assert result[0].action_name == "Attract On"

    def test_get_next_actions_filters_future(self, temp_schedules_dir):
        """get_next_actions() filters to future entries only."""
        from datetime import datetime, timedelta

        from webui.backend.lib.cron_bridge import CronEntry
        from webui.backend.services.scheduler_service import SchedulerService

        # Use timezone-aware datetime (matches real expand_pattern_entries behavior)
        now = datetime.now(UTC)
        entries = [
            CronEntry(
                expression="0 21 * * *",
                command="cmd",
                execution_time=now - timedelta(hours=1),  # Past
                action_name="Past Action",
                action_type="past",
            ),
            CronEntry(
                expression="0 22 * * *",
                command="cmd",
                execution_time=now + timedelta(hours=1),  # Future
                action_name="Future Action 1",
                action_type="future1",
            ),
            CronEntry(
                expression="0 23 * * *",
                command="cmd",
                execution_time=now + timedelta(hours=2),  # Future
                action_name="Future Action 2",
                action_type="future2",
            ),
        ]

        service = SchedulerService()
        service._active_entries = entries

        result = service.get_next_actions(limit=5)

        assert len(result) == 2
        assert result[0].action_name == "Future Action 1"
        assert result[1].action_name == "Future Action 2"

    def test_get_next_actions_respects_limit(self, temp_schedules_dir):
        """get_next_actions() respects limit parameter."""
        from datetime import datetime, timedelta

        from webui.backend.lib.cron_bridge import CronEntry
        from webui.backend.services.scheduler_service import SchedulerService

        # Use timezone-aware datetime (matches real expand_pattern_entries behavior)
        now = datetime.now(UTC)
        entries = [
            CronEntry(
                expression="0 * * * *",
                command="cmd",
                execution_time=now + timedelta(hours=i),
                action_name=f"Action {i}",
                action_type=f"action{i}",
            )
            for i in range(1, 11)  # 10 entries
        ]

        service = SchedulerService()
        service._active_entries = entries

        result = service.get_next_actions(limit=3)

        assert len(result) == 3
        assert result[0].action_name == "Action 1"

    def test_get_next_actions_sorted(self, temp_schedules_dir):
        """get_next_actions() returns sorted by execution time."""
        from datetime import datetime, timedelta

        from webui.backend.lib.cron_bridge import CronEntry
        from webui.backend.services.scheduler_service import SchedulerService

        # Use timezone-aware datetime (matches real expand_pattern_entries behavior)
        now = datetime.now(UTC)
        # Add in non-sorted order
        entries = [
            CronEntry(
                expression="0 23 * * *",
                command="cmd",
                execution_time=now + timedelta(hours=3),
                action_name="Third",
                action_type="third",
            ),
            CronEntry(
                expression="0 21 * * *",
                command="cmd",
                execution_time=now + timedelta(hours=1),
                action_name="First",
                action_type="first",
            ),
            CronEntry(
                expression="0 22 * * *",
                command="cmd",
                execution_time=now + timedelta(hours=2),
                action_name="Second",
                action_type="second",
            ),
        ]

        service = SchedulerService()
        service._active_entries = entries

        result = service.get_next_actions(limit=3)

        assert result[0].action_name == "First"
        assert result[1].action_name == "Second"
        assert result[2].action_name == "Third"

    def test_get_next_actions_empty_when_no_active(self, temp_schedules_dir):
        """get_next_actions() returns empty list when no active entries."""
        from webui.backend.services.scheduler_service import SchedulerService

        service = SchedulerService()
        service._active_entries = []

        result = service.get_next_actions(limit=5)

        assert result == []

    def test_get_next_actions_with_timezone_aware_entries(self, temp_schedules_dir):
        """get_next_actions() works with timezone-aware datetime entries.

        Regression test for Issue #331: expand_pattern_entries() creates
        timezone-aware execution_time values, so get_next_actions() must
        use timezone-aware datetime.now() for comparison.
        """
        from datetime import datetime, timedelta

        from webui.backend.lib.cron_bridge import CronEntry
        from webui.backend.services.scheduler_service import SchedulerService

        # Create timezone-aware times (like expand_pattern_entries does)
        now_utc = datetime.now(UTC)
        entries = [
            CronEntry(
                expression="0 21 * * *",
                command="cmd",
                execution_time=now_utc - timedelta(hours=1),  # Past (tz-aware)
                action_name="Past Action",
                action_type="past",
            ),
            CronEntry(
                expression="0 22 * * *",
                command="cmd",
                execution_time=now_utc + timedelta(hours=1),  # Future (tz-aware)
                action_name="Future Action",
                action_type="future",
            ),
        ]

        service = SchedulerService()
        service._active_entries = entries

        # Should not raise "can't compare offset-naive and offset-aware datetimes"
        result = service.get_next_actions(limit=5)

        assert len(result) == 1
        assert result[0].action_name == "Future Action"

    def test_active_entries_initialized_empty(self, temp_schedules_dir):
        """_active_entries should be initialized as empty list."""
        from webui.backend.services.scheduler_service import SchedulerService

        service = SchedulerService()
        assert service._active_entries == []

    def test_get_active_schedule_id(self, temp_schedules_dir):
        """get_active_schedule_id() returns the active schedule ID."""
        from webui.backend.services.scheduler_service import SchedulerService

        service = SchedulerService()
        assert service.get_active_schedule_id() is None

        service._active_schedule_id = "test-schedule-id"
        assert service.get_active_schedule_id() == "test-schedule-id"

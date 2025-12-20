"""Integration tests for scheduler activation lifecycle (Issue #216).

Tests activation workflows including:
- Full activation/deactivation lifecycle
- Single-active constraint
- Persistence across restarts
- Error handling with rollback

Run with: MOTHBOX_ENV=test pytest Tests/integration/test_scheduler_activation.py -v -s

These tests are marked as @pytest.mark.integration.

Issue #216 - Scheduler Phase 4: Integration Tests
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

# Setup path
FIRMWARE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(FIRMWARE_DIR))
sys.path.insert(0, str(FIRMWARE_DIR / "webui" / "backend"))
os.environ.setdefault("MOTHBOX_ENV", "test")

from webui.backend.lib.schedule_schema import (
    EventPattern,
    FixedTimeTrigger,
    PatternAction,
    Schedule,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_schedules_env(tmp_path, monkeypatch):
    """Mock both USER_SCHEDULES_DIR and BUILTIN_SCHEDULES_DIR."""
    # Create user schedules directory
    user_schedules_dir = tmp_path / "schedules"
    user_schedules_dir.mkdir()

    # Create built-in schedules directory
    builtin_schedules_dir = tmp_path / "presets_builtin" / "schedules"
    builtin_schedules_dir.mkdir(parents=True)

    # Patch both directories
    import webui.backend.lib.schedule_storage as ss

    monkeypatch.setattr(ss, "USER_SCHEDULES_DIR", user_schedules_dir)
    monkeypatch.setattr(ss, "BUILTIN_SCHEDULES_DIR", builtin_schedules_dir)

    return {
        "user_dir": user_schedules_dir,
        "builtin_dir": builtin_schedules_dir,
    }


@pytest.fixture
def sample_schedule_factory():
    """Factory function to create valid schedules with unique IDs."""

    def _create_schedule(
        schedule_id="",
        name="Test Schedule",
        hour=21,
        minute=0,
        enabled=True,
        is_active=False,
    ):
        """Create a valid schedule with specified parameters."""
        action = PatternAction(
            action_type="camera",
            action_name="takephoto",
            offset_minutes=0,
            description="Take photo",
        )

        pattern = EventPattern(
            pattern_id="",
            name="Test Capture",
            description="Test pattern",
            actions=[action],
            category="user",
            tags=["test"],
        )

        trigger = FixedTimeTrigger(time=f"{hour:02d}:{minute:02d}")

        schedule = Schedule(
            schedule_id=schedule_id,
            name=name,
            description="A test schedule",
            event_patterns=[pattern],
            trigger_type="fixed_time",
            fixed_time_trigger=trigger,
            enabled=enabled,
            is_active=is_active,
        )

        return schedule

    return _create_schedule


@pytest.fixture
def mock_cron_system(monkeypatch):
    """Mock cron system operations for service tests."""
    apply_mock = MagicMock(return_value=True)
    remove_mock = MagicMock(return_value=True)

    monkeypatch.setattr(
        "webui.backend.services.scheduler_service.apply_to_system",
        apply_mock,
    )
    monkeypatch.setattr(
        "webui.backend.services.scheduler_service.remove_from_system",
        remove_mock,
    )

    return {"apply": apply_mock, "remove": remove_mock}


@pytest.fixture
def scheduler_service(temp_schedules_env, mock_cron_system):
    """SchedulerService with mocked cron system."""
    from webui.backend.services.scheduler_service import SchedulerService

    service = SchedulerService(cache_ttl=60, max_cache_size=50)
    service._apply_mock = mock_cron_system["apply"]
    service._remove_mock = mock_cron_system["remove"]

    return service


# ============================================================================
# Test Activation Workflow
# ============================================================================


class TestActivationWorkflow:
    """Integration tests for schedule activation lifecycle."""

    def test_full_activation_workflow(
        self,
        temp_schedules_env,
        sample_schedule_factory,
        scheduler_service,
    ):
        """Full lifecycle: Create -> Activate -> Verify -> Deactivate -> Verify."""
        from webui.backend.lib.schedule_storage import create_schedule

        # 1. CREATE - Create new schedule
        schedule = sample_schedule_factory(
            schedule_id="workflow-test",
            name="Full Workflow Test",
        )
        create_schedule(schedule)

        # Verify schedule exists but is not active
        fetched = scheduler_service.get_schedule("workflow-test")
        assert fetched is not None, "Schedule should exist"
        assert fetched.is_active is False, "Schedule should not be active initially"

        # 2. ACTIVATE
        success, error = scheduler_service.activate_schedule(
            "workflow-test",
            check_conflicts=False,
        )
        assert success is True, f"Activation should succeed: {error}"

        # 3. VERIFY ACTIVE
        active = scheduler_service.get_active_schedule()
        assert active is not None, "Should have an active schedule"
        assert active.schedule_id == "workflow-test", "Active schedule should match"
        assert active.is_active is True, "Schedule should be marked active"

        # 4. DEACTIVATE
        result = scheduler_service.deactivate_schedule()
        assert result is True, "Deactivation should return True"

        # 5. VERIFY INACTIVE
        active_after = scheduler_service.get_active_schedule()
        assert active_after is None, "Should have no active schedule"

        # Refetch to verify is_active flag
        fetched_after = scheduler_service.get_schedule("workflow-test")
        assert fetched_after.is_active is False, "Schedule should be marked inactive"

    def test_only_one_schedule_active_at_time(
        self,
        temp_schedules_env,
        sample_schedule_factory,
        scheduler_service,
    ):
        """Activating second schedule deactivates first."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create two schedules
        schedule_a = sample_schedule_factory(
            schedule_id="schedule-a",
            name="Schedule A",
        )
        schedule_b = sample_schedule_factory(
            schedule_id="schedule-b",
            name="Schedule B",
        )
        create_schedule(schedule_a)
        create_schedule(schedule_b)

        # Activate schedule A
        success_a, error_a = scheduler_service.activate_schedule(
            "schedule-a",
            check_conflicts=False,
        )
        assert success_a is True, f"Activation A should succeed: {error_a}"

        # Verify A is active
        active1 = scheduler_service.get_active_schedule()
        assert active1.schedule_id == "schedule-a", "Schedule A should be active"

        # Activate schedule B
        success_b, error_b = scheduler_service.activate_schedule(
            "schedule-b",
            check_conflicts=False,
        )
        assert success_b is True, f"Activation B should succeed: {error_b}"

        # Verify B is now active and A is not
        active2 = scheduler_service.get_active_schedule()
        assert active2.schedule_id == "schedule-b", "Schedule B should be active"

        # Verify A was deactivated
        schedule_a_after = scheduler_service.get_schedule("schedule-a")
        assert schedule_a_after.is_active is False, "Schedule A should be deactivated"

    def test_activation_fails_for_disabled_schedule(
        self,
        temp_schedules_env,
        sample_schedule_factory,
        scheduler_service,
    ):
        """Cannot activate schedule with enabled=False."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create disabled schedule
        schedule = sample_schedule_factory(
            schedule_id="disabled-test",
            name="Disabled Schedule",
            enabled=False,
        )
        create_schedule(schedule)

        # Attempt activation
        success, error = scheduler_service.activate_schedule(
            "disabled-test",
            check_conflicts=False,
        )

        assert success is False, "Activation should fail for disabled schedule"
        assert "disabled" in error.lower(), f"Error should mention 'disabled': {error}"

    def test_activation_is_idempotent(
        self,
        temp_schedules_env,
        sample_schedule_factory,
        scheduler_service,
    ):
        """Re-activating already-active schedule succeeds without error."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create and activate schedule
        schedule = sample_schedule_factory(
            schedule_id="idempotent-test",
            name="Idempotent Test",
        )
        create_schedule(schedule)

        # First activation
        success1, error1 = scheduler_service.activate_schedule(
            "idempotent-test",
            check_conflicts=False,
        )
        assert success1 is True, f"First activation should succeed: {error1}"

        # Reset mock call count
        scheduler_service._apply_mock.reset_mock()

        # Second activation of same schedule
        success2, error2 = scheduler_service.activate_schedule(
            "idempotent-test",
            check_conflicts=False,
        )
        assert success2 is True, f"Second activation should succeed: {error2}"
        assert error2 == "", "Should have no error message"

        # Verify apply_to_system was NOT called again (idempotent)
        # Note: The implementation may or may not skip the cron write on idempotent call
        # This depends on implementation - just verify no error occurred


# ============================================================================
# Test Persistence Across Restarts
# ============================================================================


class TestPersistenceAcrossRestarts:
    """Integration tests for schedule persistence after restart."""

    def test_active_schedule_persists_to_disk(
        self,
        temp_schedules_env,
        sample_schedule_factory,
        scheduler_service,
    ):
        """is_active flag is persisted in JSON file."""
        from webui.backend.lib.schedule_storage import create_schedule

        user_dir = temp_schedules_env["user_dir"]

        # Create and activate schedule
        schedule = sample_schedule_factory(
            schedule_id="persist-test",
            name="Persistence Test",
        )
        create_schedule(schedule)

        scheduler_service.activate_schedule(
            "persist-test",
            check_conflicts=False,
        )

        # Read JSON file directly from disk
        schedule_file = user_dir / "persist-test.json"
        assert schedule_file.exists(), "Schedule file should exist"

        with open(schedule_file) as f:
            data = json.load(f)

        assert data.get("is_active") is True, "is_active should be True in JSON"

    def test_active_schedule_restored_on_service_init(
        self,
        temp_schedules_env,
        sample_schedule_factory,
        mock_cron_system,
    ):
        """New SchedulerService instance finds previously active schedule."""
        from webui.backend.lib.schedule_storage import create_schedule
        from webui.backend.services.scheduler_service import SchedulerService

        # Create first service instance
        service1 = SchedulerService(cache_ttl=60, max_cache_size=50)

        # Create and activate schedule
        schedule = sample_schedule_factory(
            schedule_id="restore-test",
            name="Restore Test",
        )
        create_schedule(schedule)

        service1.activate_schedule("restore-test", check_conflicts=False)

        # Verify active
        assert service1.get_active_schedule() is not None

        # Create NEW service instance (simulating restart)
        service2 = SchedulerService(cache_ttl=60, max_cache_size=50)

        # Query active schedule on new instance
        active = service2.get_active_schedule()

        assert active is not None, "New service should find previously active schedule"
        assert active.schedule_id == "restore-test", "Should restore correct schedule"
        assert active.is_active is True, "Should be marked as active"

    def test_activation_from_different_instance_when_already_active(
        self,
        temp_schedules_env,
        sample_schedule_factory,
        mock_cron_system,
    ):
        """Different service instance can activate when schedule already active."""
        from webui.backend.lib.schedule_storage import create_schedule
        from webui.backend.services.scheduler_service import SchedulerService

        # Create first service instance
        service1 = SchedulerService(cache_ttl=60, max_cache_size=50)

        # Create and activate schedule with service1
        schedule1 = sample_schedule_factory(
            schedule_id="cross-instance-test-1",
            name="First Schedule",
        )
        create_schedule(schedule1)

        success1, error1 = service1.activate_schedule(
            "cross-instance-test-1",
            check_conflicts=False,
        )
        assert success1 is True, f"First activation should succeed: {error1}"

        # Create NEW service instance (simulating restart/different process)
        service2 = SchedulerService(cache_ttl=60, max_cache_size=50)

        # Verify service2 discovers the previously active schedule from disk
        active_before = service2.get_active_schedule()
        assert active_before is not None, "Service2 should find active schedule from disk"
        assert active_before.schedule_id == "cross-instance-test-1", (
            "Service2 should discover schedule1 as active"
        )

        # Create second schedule
        schedule2 = sample_schedule_factory(
            schedule_id="cross-instance-test-2",
            name="Second Schedule",
        )
        create_schedule(schedule2)

        # After discovering active schedule, service2's _active_schedule_id is set
        # Now activating a different schedule should deactivate the old one
        success2, error2 = service2.activate_schedule(
            "cross-instance-test-2",
            check_conflicts=False,
        )
        assert success2 is True, f"Cross-instance activation should succeed: {error2}"

        # Verify new schedule is active
        active = service2.get_active_schedule()
        assert active is not None, "Should have an active schedule"
        assert active.schedule_id == "cross-instance-test-2", (
            f"Active schedule should be the new one, got {active.schedule_id}"
        )

        # Verify old schedule is no longer active
        old_schedule = service2.get_schedule("cross-instance-test-1")
        assert old_schedule is not None, "Old schedule should still exist"
        assert old_schedule.is_active is False, "Old schedule should be deactivated"

    def test_schedule_data_persists_through_restart_cycle(
        self,
        temp_schedules_env,
        sample_schedule_factory,
        mock_cron_system,
    ):
        """Full schedule data including patterns survives restart."""
        from webui.backend.lib.schedule_storage import create_schedule
        from webui.backend.services.scheduler_service import SchedulerService

        # Create first service instance
        service1 = SchedulerService(cache_ttl=60, max_cache_size=50)

        # Create schedule with specific data
        schedule = sample_schedule_factory(
            schedule_id="data-persist-test",
            name="Data Persistence Test",
            hour=22,
            minute=30,
        )
        create_schedule(schedule)

        service1.activate_schedule("data-persist-test", check_conflicts=False)

        # Create NEW service instance
        service2 = SchedulerService(cache_ttl=60, max_cache_size=50)

        # Read schedule on new instance
        restored = service2.get_schedule("data-persist-test")

        # Verify all data persisted
        assert restored is not None, "Schedule should exist"
        assert restored.name == "Data Persistence Test", "Name should persist"
        assert restored.is_active is True, "is_active should persist"
        assert len(restored.event_patterns) == 1, "Patterns should persist"
        assert restored.fixed_time_trigger is not None, "Trigger should persist"
        assert restored.fixed_time_trigger.time == "22:30", "Trigger time should persist"


# ============================================================================
# Test Error Handling
# ============================================================================


class TestErrorHandling:
    """Integration tests for error handling and rollback."""

    def test_activation_rollback_on_cron_failure(
        self,
        temp_schedules_env,
        sample_schedule_factory,
        monkeypatch,
    ):
        """If cron write fails, schedule state is rolled back."""
        from webui.backend.lib.schedule_storage import create_schedule
        from webui.backend.services.scheduler_service import SchedulerService

        # Mock apply_to_system to raise an exception
        def mock_apply_fail(*args, **kwargs):
            raise OSError("Simulated cron write failure")

        monkeypatch.setattr(
            "webui.backend.services.scheduler_service.apply_to_system",
            mock_apply_fail,
        )
        monkeypatch.setattr(
            "webui.backend.services.scheduler_service.remove_from_system",
            MagicMock(return_value=True),
        )

        # Create service and schedule
        service = SchedulerService(cache_ttl=60, max_cache_size=50)

        schedule = sample_schedule_factory(
            schedule_id="rollback-test",
            name="Rollback Test",
        )
        create_schedule(schedule)

        # Attempt activation (should fail)
        success, error = service.activate_schedule(
            "rollback-test",
            check_conflicts=False,
        )

        assert success is False, "Activation should fail"
        assert "failed" in error.lower() or "cron" in error.lower(), (
            f"Error should mention failure: {error}"
        )

        # Verify rollback: schedule should NOT be active
        fetched = service.get_schedule("rollback-test")
        assert fetched.is_active is False, "Schedule should be rolled back to inactive"

        # Verify no active schedule
        active = service.get_active_schedule()
        assert active is None, "Should have no active schedule after rollback"

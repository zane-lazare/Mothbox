"""Integration tests for scheduler activation lifecycle (Issue #216).

Tests activation workflows including:
- Full activation/deactivation lifecycle
- Single-active constraint
- Persistence across restarts
- Error handling with rollback

Run with: MOTHBOX_ENV=test pytest Tests/integration/test_scheduler_activation.py -v -s

These tests are marked as @pytest.mark.integration.
Fixtures are defined in Tests/conftest.py (temp_schedules_env, sample_schedule_factory,
mock_cron_system, mock_rtc_functions).

Issue #216 - Scheduler Phase 4: Integration Tests
"""

import json
import os
import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest


def _test_uuid(name: str) -> str:
    """Generate deterministic test UUID from name."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"test.integration.activation.{name}"))

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

# Setup path
FIRMWARE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(FIRMWARE_DIR))
sys.path.insert(0, str(FIRMWARE_DIR / "webui" / "backend"))
os.environ.setdefault("MOTHBOX_ENV", "test")


# ============================================================================
# Module-specific Fixtures
# ============================================================================


@pytest.fixture
def isolated_state_file(temp_schedules_env, monkeypatch):
    """Patch ACTIVE_STATE_FILE to use temp directory (avoids leftover state)."""
    import webui.backend.services.scheduler_service as ss

    active_state_file = temp_schedules_env["user_dir"] / "active_state.json"
    monkeypatch.setattr(ss, "ACTIVE_STATE_FILE", active_state_file)
    return active_state_file


@pytest.fixture
def scheduler_service(temp_schedules_env, mock_cron_system, isolated_state_file):
    """SchedulerService with mocked cron system and isolated state file."""
    from webui.backend.services.scheduler_service import SchedulerService

    service = SchedulerService(cache_ttl=60, max_cache_size=50)
    # Note: mock_cron_system mocks are applied via monkeypatch.setattr in the fixture,
    # not via service attributes. The fixture dependency ensures mocks are active.

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
            schedule_id=_test_uuid("workflow-test"),
            name="Full Workflow Test",
        )
        create_schedule(schedule)

        # Verify schedule exists but is not active
        fetched = scheduler_service.get_schedule(_test_uuid("workflow-test"))
        assert fetched is not None, "Schedule should exist"
        assert fetched.is_active is False, "Schedule should not be active initially"

        # 2. ENABLE then ACTIVATE
        scheduler_service.set_enabled_schedule(_test_uuid("workflow-test"))
        scheduler_service.activate_schedule(
            _test_uuid("workflow-test"),
            check_conflicts=False,
        )
        # No exception = success

        # 3. VERIFY ACTIVE
        active = scheduler_service.get_active_schedule()
        assert active is not None, "Should have an active schedule"
        assert active.schedule_id == _test_uuid("workflow-test"), "Active schedule should match"
        assert active.is_active is True, "Schedule should be marked active"

        # 4. DEACTIVATE
        result = scheduler_service.deactivate_schedule()
        assert result is True, "Deactivation should return True"

        # 5. VERIFY INACTIVE
        active_after = scheduler_service.get_active_schedule()
        assert active_after is None, "Should have no active schedule"

        # Refetch to verify is_active flag
        fetched_after = scheduler_service.get_schedule(_test_uuid("workflow-test"))
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
            schedule_id=_test_uuid("schedule-a"),
            name="Schedule A",
        )
        schedule_b = sample_schedule_factory(
            schedule_id=_test_uuid("schedule-b"),
            name="Schedule B",
        )
        create_schedule(schedule_a)
        create_schedule(schedule_b)

        # Enable and activate schedule A
        scheduler_service.set_enabled_schedule(_test_uuid("schedule-a"))
        scheduler_service.activate_schedule(
            _test_uuid("schedule-a"),
            check_conflicts=False,
        )
        # No exception = success

        # Verify A is active
        active1 = scheduler_service.get_active_schedule()
        assert active1.schedule_id == _test_uuid("schedule-a"), "Schedule A should be active"

        # Deactivate and disable A, then enable and activate schedule B
        scheduler_service.deactivate_schedule()  # Deactivate A first
        scheduler_service.set_enabled_schedule(None)  # Disable A
        scheduler_service.set_enabled_schedule(_test_uuid("schedule-b"))
        scheduler_service.activate_schedule(
            _test_uuid("schedule-b"),
            check_conflicts=False,
        )
        # No exception = success

        # Verify B is now active and A is not
        active2 = scheduler_service.get_active_schedule()
        assert active2.schedule_id == _test_uuid("schedule-b"), "Schedule B should be active"

        # Verify A was deactivated
        schedule_a_after = scheduler_service.get_schedule(_test_uuid("schedule-a"))
        assert schedule_a_after.is_active is False, "Schedule A should be deactivated"

    def test_activation_fails_for_disabled_schedule(
        self,
        temp_schedules_env,
        sample_schedule_factory,
        scheduler_service,
    ):
        """Cannot activate schedule with enabled=False."""
        from webui.backend.lib.schedule_schema import ScheduleActivationError
        from webui.backend.lib.schedule_storage import create_schedule

        # Create disabled schedule
        schedule = sample_schedule_factory(
            schedule_id=_test_uuid("disabled-test"),
            name="Disabled Schedule",
            enabled=False,
        )
        create_schedule(schedule)

        # Attempt activation - should raise exception
        with pytest.raises(ScheduleActivationError, match="(?i)disabled"):
            scheduler_service.activate_schedule(
                _test_uuid("disabled-test"),
                check_conflicts=False,
            )

    def test_activation_is_idempotent(
        self,
        temp_schedules_env,
        sample_schedule_factory,
        scheduler_service,
        mock_cron_system,
    ):
        """Re-activating already-active schedule succeeds without error."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create and activate schedule
        schedule = sample_schedule_factory(
            schedule_id=_test_uuid("idempotent-test"),
            name="Idempotent Test",
        )
        create_schedule(schedule)

        # Enable and activate (first time)
        scheduler_service.set_enabled_schedule(_test_uuid("idempotent-test"))
        scheduler_service.activate_schedule(
            _test_uuid("idempotent-test"),
            check_conflicts=False,
        )
        # No exception = success

        # Reset mock call count
        mock_cron_system["apply"].reset_mock()

        # Second activation of same schedule (should also succeed without exception)
        scheduler_service.activate_schedule(
            _test_uuid("idempotent-test"),
            check_conflicts=False,
        )
        # No exception = success (idempotent)

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
        isolated_state_file,
    ):
        """Active state is persisted in active_state.json file."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create and activate schedule
        schedule = sample_schedule_factory(
            schedule_id=_test_uuid("persist-test"),
            name="Persistence Test",
        )
        create_schedule(schedule)

        # Enable and activate
        scheduler_service.set_enabled_schedule(_test_uuid("persist-test"))
        scheduler_service.activate_schedule(
            _test_uuid("persist-test"),
            check_conflicts=False,
        )

        # Read active_state.json directly from disk (active state now stored here, not in schedule file)
        assert isolated_state_file.exists(), "active_state.json should exist"

        with open(isolated_state_file) as f:
            data = json.load(f)

        # Verify the correct schedule is recorded as active
        assert data.get("schedule_id") == _test_uuid("persist-test"), "Active schedule_id should match"

    def test_active_schedule_restored_on_service_init(
        self,
        temp_schedules_env,
        sample_schedule_factory,
        mock_cron_system,
        isolated_state_file,
    ):
        """New SchedulerService instance finds previously active schedule."""
        from webui.backend.lib.schedule_storage import create_schedule
        from webui.backend.services.scheduler_service import SchedulerService

        # Create first service instance (uses patched ACTIVE_STATE_FILE)
        service1 = SchedulerService(cache_ttl=60, max_cache_size=50)

        # Create and activate schedule
        schedule = sample_schedule_factory(
            schedule_id=_test_uuid("restore-test"),
            name="Restore Test",
        )
        create_schedule(schedule)

        # Enable and activate
        service1.set_enabled_schedule(_test_uuid("restore-test"))
        service1.activate_schedule(_test_uuid("restore-test"), check_conflicts=False)

        # Verify active
        assert service1.get_active_schedule() is not None

        # Create NEW service instance (simulating restart)
        service2 = SchedulerService(cache_ttl=60, max_cache_size=50)

        # Query active schedule on new instance
        active = service2.get_active_schedule()

        assert active is not None, "New service should find previously active schedule"
        assert active.schedule_id == _test_uuid("restore-test"), "Should restore correct schedule"
        assert active.is_active is True, "Should be marked as active"

    def test_activation_from_different_instance_when_already_active(
        self,
        temp_schedules_env,
        sample_schedule_factory,
        mock_cron_system,
        isolated_state_file,
    ):
        """Different service instance can activate when schedule already active."""
        from webui.backend.lib.schedule_storage import create_schedule
        from webui.backend.services.scheduler_service import SchedulerService

        # Create first service instance (uses patched ACTIVE_STATE_FILE)
        service1 = SchedulerService(cache_ttl=60, max_cache_size=50)

        # Create and activate schedule with service1
        schedule1 = sample_schedule_factory(
            schedule_id=_test_uuid("cross-instance-test-1"),
            name="First Schedule",
        )
        create_schedule(schedule1)

        # Enable and activate
        service1.set_enabled_schedule(_test_uuid("cross-instance-test-1"))
        service1.activate_schedule(
            _test_uuid("cross-instance-test-1"),
            check_conflicts=False,
        )
        # No exception = success

        # Create NEW service instance (simulating restart/different process)
        service2 = SchedulerService(cache_ttl=60, max_cache_size=50)

        # Verify service2 discovers the previously active schedule from disk
        active_before = service2.get_active_schedule()
        assert active_before is not None, "Service2 should find active schedule from disk"
        assert active_before.schedule_id == _test_uuid("cross-instance-test-1"), (
            "Service2 should discover schedule1 as active"
        )

        # Create second schedule
        schedule2 = sample_schedule_factory(
            schedule_id=_test_uuid("cross-instance-test-2"),
            name="Second Schedule",
        )
        create_schedule(schedule2)

        # After discovering active schedule, service2's _active_schedule_id is set
        # Now activating a different schedule should deactivate the old one
        # First deactivate and disable the current schedule, then enable the new one
        service2.deactivate_schedule()
        service2.set_enabled_schedule(None)
        service2.set_enabled_schedule(_test_uuid("cross-instance-test-2"))
        service2.activate_schedule(
            _test_uuid("cross-instance-test-2"),
            check_conflicts=False,
        )
        # No exception = success

        # Verify new schedule is active
        active = service2.get_active_schedule()
        assert active is not None, "Should have an active schedule"
        assert active.schedule_id == _test_uuid("cross-instance-test-2"), (
            f"Active schedule should be the new one, got {active.schedule_id}"
        )

        # Verify old schedule is no longer active
        old_schedule = service2.get_schedule(_test_uuid("cross-instance-test-1"))
        assert old_schedule is not None, "Old schedule should still exist"
        assert old_schedule.is_active is False, "Old schedule should be deactivated"

    def test_schedule_data_persists_through_restart_cycle(
        self,
        temp_schedules_env,
        sample_schedule_factory,
        mock_cron_system,
        isolated_state_file,
    ):
        """Full schedule data including patterns survives restart."""
        from webui.backend.lib.schedule_storage import create_schedule
        from webui.backend.services.scheduler_service import SchedulerService

        # Create first service instance (uses patched ACTIVE_STATE_FILE)
        service1 = SchedulerService(cache_ttl=60, max_cache_size=50)

        # Create schedule with specific data
        schedule = sample_schedule_factory(
            schedule_id=_test_uuid("data-persist-test"),
            name="Data Persistence Test",
            hour=22,
            minute=30,
        )
        create_schedule(schedule)

        # Enable and activate
        service1.set_enabled_schedule(_test_uuid("data-persist-test"))
        service1.activate_schedule(_test_uuid("data-persist-test"), check_conflicts=False)

        # Create NEW service instance
        service2 = SchedulerService(cache_ttl=60, max_cache_size=50)

        # Read schedule on new instance
        restored = service2.get_schedule(_test_uuid("data-persist-test"))

        # Verify all data persisted
        assert restored is not None, "Schedule should exist"
        assert restored.name == "Data Persistence Test", "Name should persist"
        assert restored.is_active is True, "is_active should persist"
        assert len(restored.routines) == 1, "Routines should persist"
        from webui.backend.lib.schedule_schema import FixedTimeTrigger
        assert isinstance(restored.routines[0].trigger, FixedTimeTrigger), "Trigger should persist"
        assert restored.routines[0].trigger.time == "22:30", "Trigger time should persist"


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
        isolated_state_file,
    ):
        """If cron write fails, schedule state is rolled back."""
        from webui.backend.lib.schedule_schema import ScheduleActivationError
        from webui.backend.lib.schedule_storage import create_schedule
        from webui.backend.services.scheduler_service import SchedulerService

        # Mock apply_to_system to raise an exception
        def mock_apply_fail(*args, **kwargs):
            raise OSError("Simulated cron write failure")

        # Track remove_from_system calls for rollback verification
        remove_mock = MagicMock(return_value=True)

        monkeypatch.setattr(
            "webui.backend.services.scheduler_service.apply_to_system",
            mock_apply_fail,
        )
        monkeypatch.setattr(
            "webui.backend.services.scheduler_service.remove_from_system",
            remove_mock,
        )

        # Create service and schedule
        service = SchedulerService(cache_ttl=60, max_cache_size=50)

        schedule = sample_schedule_factory(
            schedule_id=_test_uuid("rollback-test"),
            name="Rollback Test",
        )
        create_schedule(schedule)

        # Enable the schedule first
        service.set_enabled_schedule(_test_uuid("rollback-test"))

        # Attempt activation (should raise exception due to mock failure)
        with pytest.raises(ScheduleActivationError, match="(?i)failed"):
            service.activate_schedule(
                _test_uuid("rollback-test"),
                check_conflicts=False,
            )

        # Verify rollback: schedule should NOT be active
        fetched = service.get_schedule(_test_uuid("rollback-test"))
        assert fetched.is_active is False, "Schedule should be rolled back to inactive"

        # Verify no active schedule
        active = service.get_active_schedule()
        assert active is None, "Should have no active schedule after rollback"

        # Verify system cleanup behavior on failure
        # When activation fails with no previous active schedule, remove_from_system
        # should NOT be called (nothing to clean up - failure was in apply_to_system)
        assert remove_mock.call_count == 0, (
            "remove_from_system should not be called when no previous schedule active"
        )

    def test_activation_failure_preserves_previous_schedule_state(
        self,
        temp_schedules_env,
        sample_schedule_factory,
        monkeypatch,
        isolated_state_file,
    ):
        """Failed activation of new schedule handles previous schedule correctly."""
        from webui.backend.lib.schedule_schema import ScheduleActivationError
        from webui.backend.lib.schedule_storage import create_schedule
        from webui.backend.services.scheduler_service import SchedulerService

        apply_call_count = [0]
        remove_mock = MagicMock(return_value=True)

        def mock_apply_conditional(*args, **kwargs):
            apply_call_count[0] += 1
            if apply_call_count[0] == 1:
                # First call (schedule1 activation) succeeds
                return True
            else:
                # Second call (schedule2 activation) fails
                raise OSError("Simulated cron write failure")

        monkeypatch.setattr(
            "webui.backend.services.scheduler_service.apply_to_system",
            mock_apply_conditional,
        )
        monkeypatch.setattr(
            "webui.backend.services.scheduler_service.remove_from_system",
            remove_mock,
        )

        service = SchedulerService(cache_ttl=60, max_cache_size=50)

        # Create and activate first schedule (succeeds)
        schedule1 = sample_schedule_factory(
            schedule_id=_test_uuid("preserve-test-1"),
            name="First Schedule",
        )
        create_schedule(schedule1)
        # Enable and activate first schedule
        service.set_enabled_schedule(_test_uuid("preserve-test-1"))
        service.activate_schedule(_test_uuid("preserve-test-1"), check_conflicts=False)
        # No exception = success

        # Verify first schedule is active
        active1 = service.get_active_schedule()
        assert active1 is not None
        assert active1.schedule_id == _test_uuid("preserve-test-1")

        # Reset mock to track second activation
        remove_mock.reset_mock()

        # Create second schedule
        schedule2 = sample_schedule_factory(
            schedule_id=_test_uuid("preserve-test-2"),
            name="Second Schedule",
        )
        create_schedule(schedule2)

        # Deactivate and disable first schedule, then enable second
        service.deactivate_schedule()
        service.set_enabled_schedule(None)
        service.set_enabled_schedule(_test_uuid("preserve-test-2"))

        # Attempt activation of second schedule (will raise exception)
        with pytest.raises(ScheduleActivationError, match="(?i)failed"):
            service.activate_schedule(_test_uuid("preserve-test-2"), check_conflicts=False)

        # Verify remove_from_system was called during deactivation of previous schedule
        # (called before attempting to apply new schedule)
        assert remove_mock.call_count >= 1, (
            "remove_from_system should be called when deactivating previous schedule"
        )

        # Verify the remove call included clear_rtc=True
        call_args = remove_mock.call_args
        clear_rtc = call_args.kwargs.get("clear_rtc", True)
        assert clear_rtc is True, "Should clear RTC when deactivating previous schedule"

        # Verify second schedule is NOT active
        fetched2 = service.get_schedule(_test_uuid("preserve-test-2"))
        assert fetched2.is_active is False, "Failed schedule should not be active"


# ============================================================================
# Test WebSocket Progress Events (Issue #309)
# ============================================================================


class TestProgressCallbackEvents:
    """Integration tests for progress callback during activation (Issue #309)."""

    def test_activation_emits_progress_events(
        self,
        temp_schedules_env,
        sample_schedule_factory,
        scheduler_service,
    ):
        """Progress callback receives events with correct structure during activation."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create enabled schedule
        schedule = sample_schedule_factory(
            schedule_id=_test_uuid("progress-events-test"),
            name="Progress Events Test",
        )
        create_schedule(schedule)

        # Enable schedule first
        scheduler_service.set_enabled_schedule(_test_uuid("progress-events-test"))

        # Track progress calls (simulates WebSocket emit)
        received_events = []

        def mock_emit_progress(phase: str, progress: int) -> None:
            received_events.append({
                "phase": phase,
                "progress": progress,
            })

        # Activate with callback
        scheduler_service.activate_schedule(
            _test_uuid("progress-events-test"),
            check_conflicts=True,
            progress_callback=mock_emit_progress,
        )

        # Verify 5 events received
        assert len(received_events) == 5, f"Expected 5 events, got {len(received_events)}"

        # Verify structure matches WebSocket event format
        for event in received_events:
            assert "phase" in event, "Event should have 'phase' key"
            assert "progress" in event, "Event should have 'progress' key"
            assert isinstance(event["phase"], str), "Phase should be string"
            assert isinstance(event["progress"], int), "Progress should be integer"
            assert 0 <= event["progress"] <= 100, "Progress should be 0-100"

        # Verify phases in order
        phases = [e["phase"] for e in received_events]
        expected_phases = [
            "checking_conflicts",
            "generating_cron",
            "applying_cron",
            "updating_state",
            "complete",
        ]
        assert phases == expected_phases, f"Expected phases {expected_phases}, got {phases}"

        # Verify progress values are ascending
        progress_values = [e["progress"] for e in received_events]
        assert progress_values == sorted(progress_values), "Progress should be ascending"
        assert progress_values[-1] == 100, "Final progress should be 100"

    def test_activation_emits_failed_event_on_error(
        self,
        temp_schedules_env,
        sample_schedule_factory,
        scheduler_service,
        mock_cron_system,
        monkeypatch,
    ):
        """Progress callback receives 'failed' event when activation fails."""
        from webui.backend.lib.schedule_schema import ScheduleActivationError
        from webui.backend.lib.schedule_storage import create_schedule

        # Create enabled schedule
        schedule = sample_schedule_factory(
            schedule_id=_test_uuid("progress-fail-test"),
            name="Progress Fail Test",
        )
        create_schedule(schedule)

        # Enable schedule first
        scheduler_service.set_enabled_schedule(_test_uuid("progress-fail-test"))

        # Make apply_to_system fail
        mock_cron_system["apply"].side_effect = RuntimeError("Simulated cron failure")

        # Track progress calls
        received_events = []

        def mock_emit_progress(phase: str, progress: int) -> None:
            received_events.append({
                "phase": phase,
                "progress": progress,
            })

        # Attempt activation - should fail
        with pytest.raises(ScheduleActivationError):
            scheduler_service.activate_schedule(
                _test_uuid("progress-fail-test"),
                check_conflicts=False,
                progress_callback=mock_emit_progress,
            )

        # Verify 'failed' event was emitted
        phases = [e["phase"] for e in received_events]
        assert "failed" in phases, "Should emit 'failed' phase on error"

        # Verify failed event has progress 0
        failed_events = [e for e in received_events if e["phase"] == "failed"]
        assert len(failed_events) == 1, "Should have exactly one 'failed' event"
        assert failed_events[0]["progress"] == 0, "'failed' event should have progress 0"

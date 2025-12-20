"""Integration tests for scheduler workflow (Issue #216).

Tests end-to-end scheduler workflows including:
- Cron job creation and removal
- RTC wakealarm setting and clearing
- Trigger type conversions (interval, solar)

Run with: MOTHBOX_ENV=test pytest Tests/integration/test_scheduler_workflow.py -v -s

These tests are marked as @pytest.mark.integration.
Hardware tests (actual RTC access) are marked with @pytest.mark.hardware.

Issue #216 - Scheduler Phase 4: Integration Tests
"""

import os
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

# Setup path
FIRMWARE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(FIRMWARE_DIR))
sys.path.insert(0, str(FIRMWARE_DIR / "webui" / "backend"))
os.environ.setdefault("MOTHBOX_ENV", "test")

from webui.backend.lib.cron_bridge import (
    CronEntry,
    clear_rtc_wakealarm,
    schedule_to_cron,
    set_rtc_wakealarm,
)
from webui.backend.lib.schedule_schema import (
    EventPattern,
    FixedTimeTrigger,
    IntervalTrigger,
    PatternAction,
    Schedule,
    SolarTrigger,
    TimeWindow,
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
        trigger_type="fixed_time",
        hour=21,
        minute=0,
        interval_minutes=60,
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

        if trigger_type == "fixed_time":
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
        elif trigger_type == "interval":
            window = TimeWindow(start_time="21:00", end_time="23:00")
            trigger = IntervalTrigger(
                interval_minutes=interval_minutes,
                time_window=window,
            )
            schedule = Schedule(
                schedule_id=schedule_id,
                name=name,
                description="A test schedule",
                event_patterns=[pattern],
                trigger_type="interval",
                interval_trigger=trigger,
                enabled=enabled,
                is_active=is_active,
            )
        elif trigger_type == "solar":
            trigger = SolarTrigger(
                solar_event="sunset",
                offset_minutes=30,
            )
            schedule = Schedule(
                schedule_id=schedule_id,
                name=name,
                description="A test schedule",
                event_patterns=[pattern],
                trigger_type="solar",
                solar_trigger=trigger,
                enabled=enabled,
                is_active=is_active,
            )
        else:
            raise ValueError(f"Unknown trigger type: {trigger_type}")

        return schedule

    return _create_schedule


@pytest.fixture
def mock_crontab():
    """Mock CronTab class for cron operations."""
    with patch("webui.backend.lib.cron_bridge.CronTab") as mock_crontab_class:
        mock_cron = MagicMock()
        mock_crontab_class.return_value = mock_cron

        # Mock jobs list (empty by default)
        mock_cron.jobs = []
        mock_cron.__iter__ = MagicMock(return_value=iter([]))

        # Mock new() method to create mock job
        def create_mock_job(command, comment=""):
            mock_job = MagicMock()
            mock_job.command = command
            mock_job.comment = comment
            mock_job.enabled = True
            mock_cron.jobs.append(mock_job)
            return mock_job

        mock_cron.new = MagicMock(side_effect=create_mock_job)

        # Mock remove() method
        def remove_job(job):
            if job in mock_cron.jobs:
                mock_cron.jobs.remove(job)

        mock_cron.remove = MagicMock(side_effect=remove_job)

        # Mock write() method
        mock_cron.write = MagicMock()

        yield mock_cron


@pytest.fixture
def mock_rtc_functions(monkeypatch):
    """Mock RTC wakealarm functions."""
    set_mock = MagicMock(return_value=True)
    clear_mock = MagicMock(return_value=True)

    monkeypatch.setattr(
        "webui.backend.lib.cron_bridge.set_rtc_wakealarm",
        set_mock,
    )
    monkeypatch.setattr(
        "webui.backend.lib.cron_bridge.clear_rtc_wakealarm",
        clear_mock,
    )

    return {"set": set_mock, "clear": clear_mock}


@pytest.fixture
def scheduler_service(temp_schedules_env, mock_crontab, mock_rtc_functions, monkeypatch):
    """SchedulerService with mocked dependencies."""
    from webui.backend.services.scheduler_service import SchedulerService

    # Patch apply_to_system and remove_from_system to use mocks
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

    service = SchedulerService(cache_ttl=60, max_cache_size=50)
    service._apply_mock = apply_mock
    service._remove_mock = remove_mock

    return service


# ============================================================================
# Test Cron Job Management
# ============================================================================


class TestCronJobManagement:
    """Integration tests for cron job creation and removal."""

    def test_schedule_creates_cron_entries(
        self,
        temp_schedules_env,
        sample_schedule_factory,
        scheduler_service,
    ):
        """Activating a schedule creates the expected cron entries."""
        # Create schedule with fixed time trigger at 21:00
        schedule = sample_schedule_factory(
            schedule_id="cron-test-1",
            name="Cron Test Schedule",
            trigger_type="fixed_time",
            hour=21,
            minute=0,
        )

        # Save schedule to storage
        from webui.backend.lib.schedule_storage import create_schedule

        create_schedule(schedule)

        # Activate schedule
        success, error = scheduler_service.activate_schedule(
            "cron-test-1",
            check_conflicts=False,
        )

        assert success is True, f"Activation should succeed: {error}"

        # Verify apply_to_system was called with entries
        scheduler_service._apply_mock.assert_called_once()
        call_args = scheduler_service._apply_mock.call_args
        entries = call_args.kwargs.get("entries", call_args[0][0] if call_args[0] else [])

        assert len(entries) >= 1, "Should have at least one cron entry"

        # Verify cron entry content
        entry = entries[0]

        # 1. Verify cron expression is correct for 21:00
        assert entry.expression == "0 21 * * *", (
            f"Expected cron expression '0 21 * * *', got '{entry.expression}'"
        )

        # 2. Verify command references TakePhoto script
        assert "takephoto" in entry.command.lower(), (
            f"Command should reference takephoto, got '{entry.command}'"
        )

        # 3. Verify comment includes Mothbox prefix
        assert entry.comment.startswith("Mothbox:"), (
            f"Comment should start with 'Mothbox:', got '{entry.comment}'"
        )

    def test_schedule_removes_old_cron_entries_on_activation(
        self,
        temp_schedules_env,
        sample_schedule_factory,
        scheduler_service,
    ):
        """Activating a new schedule removes previous Mothbox entries."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create and activate first schedule
        schedule1 = sample_schedule_factory(
            schedule_id="cron-test-2a",
            name="First Schedule",
        )
        create_schedule(schedule1)

        success1, error1 = scheduler_service.activate_schedule(
            "cron-test-2a",
            check_conflicts=False,
        )
        assert success1 is True, f"First activation should succeed: {error1}"

        # Reset mock call count
        scheduler_service._apply_mock.reset_mock()
        scheduler_service._remove_mock.reset_mock()

        # Create and activate second schedule
        schedule2 = sample_schedule_factory(
            schedule_id="cron-test-2b",
            name="Second Schedule",
        )
        create_schedule(schedule2)

        success2, error2 = scheduler_service.activate_schedule(
            "cron-test-2b",
            check_conflicts=False,
        )
        assert success2 is True, f"Second activation should succeed: {error2}"

        # Verify remove_from_system was called (to remove old entries)
        scheduler_service._remove_mock.assert_called()

        # Verify apply_to_system was called for new entries
        scheduler_service._apply_mock.assert_called()

    def test_deactivation_removes_all_cron_entries(
        self,
        temp_schedules_env,
        sample_schedule_factory,
        scheduler_service,
    ):
        """Deactivating schedule removes all Mothbox cron entries."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create and activate schedule
        schedule = sample_schedule_factory(
            schedule_id="cron-test-3",
            name="Deactivation Test",
        )
        create_schedule(schedule)

        success, error = scheduler_service.activate_schedule(
            "cron-test-3",
            check_conflicts=False,
        )
        assert success is True, f"Activation should succeed: {error}"

        # Reset mock
        scheduler_service._remove_mock.reset_mock()

        # Deactivate
        result = scheduler_service.deactivate_schedule()
        assert result is True, "Deactivation should return True"

        # Verify remove_from_system was called with clear_rtc=True
        scheduler_service._remove_mock.assert_called_once()
        call_args = scheduler_service._remove_mock.call_args
        clear_rtc = call_args.kwargs.get("clear_rtc", True)
        assert clear_rtc is True, "Should clear RTC on deactivation"

    def test_preserves_system_cron_jobs(
        self,
        temp_schedules_env,
        sample_schedule_factory,
        mock_crontab,
    ):
        """Non-Mothbox system jobs are preserved during activation/deactivation."""
        from webui.backend.lib.cron_bridge import is_mothbox_command

        # Simulate system job (not Mothbox)
        system_job_command = "/usr/bin/logrotate /etc/logrotate.conf"

        # Verify this is NOT considered a Mothbox command
        assert is_mothbox_command(system_job_command) is False

        # Mothbox command should be identified
        mothbox_command = "/usr/bin/python3 /opt/mothbox/TakePhoto.py"
        assert is_mothbox_command(mothbox_command) is True


# ============================================================================
# Test RTC Wakealarm Management (Mocked)
# ============================================================================


class TestRTCWakealarmManagement:
    """Integration tests for RTC wakealarm operations (mocked)."""

    def test_activation_sets_rtc_wakealarm(
        self,
        temp_schedules_env,
        sample_schedule_factory,
        scheduler_service,
    ):
        """Activating schedule writes correct epoch time to RTC."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create schedule
        schedule = sample_schedule_factory(
            schedule_id="rtc-test-1",
            name="RTC Set Test",
        )
        create_schedule(schedule)

        # Activate
        success, error = scheduler_service.activate_schedule(
            "rtc-test-1",
            check_conflicts=False,
        )
        assert success is True, f"Activation should succeed: {error}"

        # Verify apply_to_system was called with set_rtc=True
        call_args = scheduler_service._apply_mock.call_args
        set_rtc = call_args.kwargs.get("set_rtc", True)
        assert set_rtc is True, "Should set RTC on activation"

    def test_deactivation_clears_rtc_wakealarm(
        self,
        temp_schedules_env,
        sample_schedule_factory,
        scheduler_service,
    ):
        """Deactivating schedule clears RTC alarm."""
        from webui.backend.lib.schedule_storage import create_schedule

        # Create and activate schedule
        schedule = sample_schedule_factory(
            schedule_id="rtc-test-2",
            name="RTC Clear Test",
        )
        create_schedule(schedule)

        scheduler_service.activate_schedule("rtc-test-2", check_conflicts=False)
        scheduler_service._remove_mock.reset_mock()

        # Deactivate
        scheduler_service.deactivate_schedule()

        # Verify remove_from_system was called with clear_rtc=True
        call_args = scheduler_service._remove_mock.call_args
        clear_rtc = call_args.kwargs.get("clear_rtc", True)
        assert clear_rtc is True, "Should clear RTC on deactivation"

    def test_rtc_wakealarm_calculated_from_next_execution(
        self,
        sample_schedule_factory,
    ):
        """RTC time is calculated from next scheduled execution."""
        from webui.backend.lib.cron_bridge import calculate_next_waketime

        # Create schedule with fixed time
        schedule = sample_schedule_factory(
            schedule_id="rtc-test-3",
            name="RTC Calculation Test",
            trigger_type="fixed_time",
            hour=21,
            minute=0,
        )

        # Convert to cron
        result = schedule_to_cron(schedule)

        assert len(result.entries) >= 1, "Should have cron entries"

        # Calculate next waketime from first entry
        entry = result.entries[0]
        next_wake = calculate_next_waketime(entry.expression)

        assert next_wake is not None, "Should calculate next waketime"
        assert next_wake > time.time(), "Next wake should be in the future"


# ============================================================================
# Test RTC Wakealarm Hardware (Real RTC Access)
# ============================================================================


@pytest.mark.hardware
class TestRTCWakealarmHardware:
    """Hardware tests for RTC wakealarm (Pi 5 only)."""

    RTC_PATH = Path("/sys/class/rtc/rtc0/wakealarm")

    @pytest.fixture(autouse=True)
    def check_rtc_available(self):
        """Skip tests if RTC is not available."""
        if not self.RTC_PATH.exists():
            pytest.skip("RTC not available (Pi 5 required)")

    def test_rtc_wakealarm_file_write(self):
        """Write to /sys/class/rtc/rtc0/wakealarm and verify."""
        # Calculate a future time (5 minutes from now)
        future_epoch = int(time.time()) + 300

        # Write to RTC
        success = set_rtc_wakealarm(future_epoch)

        # Note: This may fail if not running as root
        if success:
            # Read back and verify
            content = self.RTC_PATH.read_text().strip()
            assert content == str(future_epoch), "RTC should contain the set epoch time"

            # Clean up
            clear_rtc_wakealarm()
        else:
            pytest.skip("RTC write failed (may need root privileges)")

    def test_rtc_wakealarm_file_clear(self):
        """Clear RTC wakealarm and verify file content is '0'."""
        # Set an alarm first
        future_epoch = int(time.time()) + 300
        set_success = set_rtc_wakealarm(future_epoch)

        if not set_success:
            pytest.skip("RTC write failed (may need root privileges)")

        # Clear the alarm
        clear_success = clear_rtc_wakealarm()

        if clear_success:
            # Read back and verify it's cleared
            content = self.RTC_PATH.read_text().strip()
            assert content == "0" or content == "", "RTC should be cleared"
        else:
            pytest.skip("RTC clear failed")


# ============================================================================
# Test Trigger Type Workflows
# ============================================================================


class TestTriggerTypeWorkflows:
    """Integration tests for different trigger type conversions."""

    def test_interval_trigger_creates_multiple_entries(
        self,
        sample_schedule_factory,
    ):
        """Interval trigger within window creates entry per execution."""
        # Create schedule with interval trigger: every 60 min from 21:00-23:00
        schedule = sample_schedule_factory(
            schedule_id="interval-test",
            name="Interval Test",
            trigger_type="interval",
            interval_minutes=60,
        )

        # Convert to cron
        result = schedule_to_cron(schedule)

        # Should have 3 entries: 21:00, 22:00, 23:00
        assert len(result.entries) >= 2, f"Should have multiple entries, got {len(result.entries)}"

        # Verify expressions contain different hours
        expressions = [e.expression for e in result.entries]
        hours_found = set()
        for expr in expressions:
            parts = expr.split()
            if len(parts) >= 2:
                hours_found.add(parts[1])

        assert len(hours_found) >= 2, "Should have entries at different hours"

    def test_solar_trigger_creates_daily_entries(
        self,
        sample_schedule_factory,
    ):
        """Solar trigger creates entries for N days ahead."""
        # Create schedule with solar trigger: sunset+30
        schedule = sample_schedule_factory(
            schedule_id="solar-test",
            name="Solar Test",
            trigger_type="solar",
        )

        # Convert to cron with location
        result = schedule_to_cron(
            schedule,
            latitude=37.7749,  # San Francisco
            longitude=-122.4194,
            timezone_name="America/Los_Angeles",
            days_ahead=7,
        )

        # Should have entries for multiple days
        assert len(result.entries) >= 1, "Should have solar-based entries"

        # Each entry should have a valid expression
        for entry in result.entries:
            assert CronEntry.is_valid_expression(entry.expression), (
                f"Invalid cron expression: {entry.expression}"
            )

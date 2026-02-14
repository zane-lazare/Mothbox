"""Tests for reconciliation integration in scheduler activation (Issue #398)."""

import uuid
from unittest.mock import patch

import pytest

from webui.backend.lib.schedule_schema import (
    Action,
    IntervalTrigger,
    Routine,
    Schedule,
    TimeWindow,
)
from webui.backend.services.scheduler_service import SchedulerService


def _test_uuid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"reconcile-test-{name}"))


@pytest.fixture
def temp_schedules_dir(tmp_path, monkeypatch):
    """Create temp directory and mock SCHEDULES_DIR and ACTIVE_STATE_FILE."""
    schedules = tmp_path / "schedules"
    schedules.mkdir()
    monkeypatch.setattr("mothbox_paths.SCHEDULES_DIR", schedules)
    monkeypatch.setattr("webui.backend.lib.schedule_storage.SCHEDULES_DIR", schedules)
    active_state_file = tmp_path / "active_state.json"
    monkeypatch.setattr(
        "webui.backend.services.scheduler_service.ACTIVE_STATE_FILE", active_state_file
    )
    return schedules


@pytest.fixture
def sample_schedule():
    """Create a valid Schedule for testing."""
    actions = [
        Action(
            action_type="gpio",
            action_name="attract_on",
            offset_minutes=0,
        ),
        Action(
            action_type="gpio",
            action_name="attract_off",
            offset_minutes=15,
        ),
    ]
    trigger = IntervalTrigger(
        interval_minutes=60,
        time_window=TimeWindow(start_time="21:00", end_time="05:00"),
    )
    routine = Routine(
        routine_id="",
        name="Test Routine",
        trigger=trigger,
        actions=actions,
    )
    return Schedule(
        schedule_id="",
        name="Test Schedule",
        routines=[routine],
        enabled=True,
    )


@pytest.fixture
def scheduler_service(temp_schedules_dir):
    return SchedulerService(cache_ttl=300, max_cache_size=100)


class TestActivationReconciliation:
    """Tests for reconciliation during schedule activation."""

    def test_activate_calls_reconciler(
        self, scheduler_service, temp_schedules_dir, sample_schedule, mock_cron_system
    ):
        """Reconciler is called with correct args after activation."""
        from webui.backend.lib.schedule_storage import create_schedule

        schedule_id = _test_uuid("reconcile-called")
        sample_schedule.schedule_id = schedule_id
        create_schedule(sample_schedule)
        scheduler_service.set_enabled_schedule(schedule_id)

        with (
            patch("webui.backend.lib.schedule_reconciler.reconcile_schedule") as mock_reconcile,
            patch("webui.backend.lib.schedule_reconciler.execute_reconciliation") as mock_execute,
        ):
            mock_reconcile.return_value = [
                {"action_type": "gpio", "action_name": "attract_on", "source_time": None}
            ]
            mock_execute.return_value = [
                {"action_name": "attract_on", "success": True, "error": None}
            ]

            scheduler_service.activate_schedule(
                schedule_id=schedule_id,
                check_conflicts=False,
                latitude=9.0,
                longitude=-79.0,
                timezone_name="America/Panama",
            )

            mock_reconcile.assert_called_once()
            call_args = mock_reconcile.call_args
            # Verify schedule, lat, lon, timezone passed
            assert call_args[0][1] == 9.0  # latitude
            assert call_args[0][2] == -79.0  # longitude
            assert call_args[0][3] == "America/Panama"  # timezone
            mock_execute.assert_called_once()

    def test_reconciler_failure_nonfatal(
        self, scheduler_service, temp_schedules_dir, sample_schedule, mock_cron_system
    ):
        """Reconciler raising an exception does NOT prevent activation."""
        from webui.backend.lib.schedule_storage import create_schedule

        schedule_id = _test_uuid("reconcile-failure")
        sample_schedule.schedule_id = schedule_id
        create_schedule(sample_schedule)
        scheduler_service.set_enabled_schedule(schedule_id)

        with patch(
            "webui.backend.lib.schedule_reconciler.reconcile_schedule",
            side_effect=RuntimeError("Reconciliation exploded"),
        ):
            # Should NOT raise — reconciliation failure is non-fatal
            scheduler_service.activate_schedule(
                schedule_id=schedule_id,
                check_conflicts=False,
                latitude=9.0,
                longitude=-79.0,
                timezone_name="America/Panama",
            )

        # Activation succeeded despite reconciliation failure
        assert scheduler_service._active_schedule_id == schedule_id

"""Unit tests for schedule_reconciler module."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytz

from webui.backend.lib.schedule_reconciler import (
    execute_reconciliation,
    reconcile_schedule,
)
from webui.backend.lib.schedule_schema import (
    Action,
    FixedTimeTrigger,
    Routine,
    Schedule,
    SensorTrigger,
    SolarTrigger,
)

TZ = pytz.timezone("America/Panama")


def _make_schedule(routines=None):
    """Helper to create a Schedule with given routines."""
    return Schedule(
        schedule_id="test-sched-1",
        name="Test Schedule",
        routines=routines or [],
        enabled=True,
    )


def _make_routine(trigger, actions, routine_id="routine-1"):
    """Helper to create a Routine."""
    return Routine(
        routine_id=routine_id,
        name="Test Routine",
        trigger=trigger,
        actions=actions,
    )


def _aware(dt):
    """Make a naive datetime timezone-aware in America/Panama."""
    return TZ.localize(dt)


class TestReconcileSchedule:
    """Tests for reconcile_schedule()."""

    def test_no_routines_returns_empty(self):
        schedule = _make_schedule(routines=[])
        now = _aware(datetime(2025, 6, 15, 22, 0, 0))
        result = reconcile_schedule(schedule, 0.0, 0.0, "America/Panama", now=now)
        assert result == []

    @patch("webui.backend.lib.schedule_reconciler.calculate_execution_times")
    def test_attract_on_in_past_returns_attract_on(self, mock_calc):
        """Sunset attract_on 2h ago -> reconcile returns attract_on."""
        now = _aware(datetime(2025, 6, 15, 22, 0, 0))
        trigger_time = _aware(datetime(2025, 6, 15, 20, 0, 0))
        mock_calc.return_value = [trigger_time]

        trigger = SolarTrigger(solar_event="sunset")
        actions = [Action(action_type="gpio", action_name="attract_on", offset_minutes=0)]
        routine = _make_routine(trigger, actions)
        schedule = _make_schedule(routines=[routine])

        result = reconcile_schedule(schedule, 9.0, -79.0, "America/Panama", now=now)

        assert len(result) == 1
        assert result[0]["action_name"] == "attract_on"
        assert result[0]["action_type"] == "gpio"
        assert result[0]["source_time"] == trigger_time

    @patch("webui.backend.lib.schedule_reconciler.calculate_execution_times")
    def test_attract_on_then_off_returns_off(self, mock_calc):
        """attract_on 3h ago, attract_off 1h ago -> returns attract_off."""
        now = _aware(datetime(2025, 6, 15, 22, 0, 0))
        trigger_time = _aware(datetime(2025, 6, 15, 19, 0, 0))
        mock_calc.return_value = [trigger_time]

        trigger = SolarTrigger(solar_event="sunset")
        actions = [
            Action(action_type="gpio", action_name="attract_on", offset_minutes=0),
            Action(action_type="gpio", action_name="attract_off", offset_minutes=120),
        ]
        routine = _make_routine(trigger, actions)
        schedule = _make_schedule(routines=[routine])

        result = reconcile_schedule(schedule, 9.0, -79.0, "America/Panama", now=now)

        assert len(result) == 1
        assert result[0]["action_name"] == "attract_off"
        # attract_off should be trigger_time + 120min = 1h ago
        assert result[0]["source_time"] == trigger_time + timedelta(minutes=120)

    @patch("webui.backend.lib.schedule_reconciler.calculate_execution_times")
    def test_future_actions_ignored(self, mock_calc):
        """Action 2h in the future -> not returned."""
        now = _aware(datetime(2025, 6, 15, 18, 0, 0))
        trigger_time = _aware(datetime(2025, 6, 15, 20, 0, 0))
        mock_calc.return_value = [trigger_time]

        trigger = SolarTrigger(solar_event="sunset")
        actions = [Action(action_type="gpio", action_name="attract_on", offset_minutes=0)]
        routine = _make_routine(trigger, actions)
        schedule = _make_schedule(routines=[routine])

        result = reconcile_schedule(schedule, 9.0, -79.0, "America/Panama", now=now)
        assert result == []

    @patch("webui.backend.lib.schedule_reconciler.calculate_execution_times")
    def test_non_reconcilable_skipped(self, mock_calc):
        """Camera/takephoto actions are filtered out."""
        now = _aware(datetime(2025, 6, 15, 22, 0, 0))
        trigger_time = _aware(datetime(2025, 6, 15, 21, 0, 0))
        mock_calc.return_value = [trigger_time]

        trigger = FixedTimeTrigger(time="21:00")
        actions = [
            Action(action_type="camera", action_name="takephoto", offset_minutes=0),
        ]
        routine = _make_routine(trigger, actions)
        schedule = _make_schedule(routines=[routine])

        result = reconcile_schedule(schedule, 9.0, -79.0, "America/Panama", now=now)
        assert result == []

    @patch("webui.backend.lib.schedule_reconciler.calculate_execution_times")
    def test_multiple_resources_independent(self, mock_calc):
        """Attract and flash reconciled independently."""
        now = _aware(datetime(2025, 6, 15, 22, 0, 0))
        trigger_time = _aware(datetime(2025, 6, 15, 20, 0, 0))
        mock_calc.return_value = [trigger_time]

        trigger = SolarTrigger(solar_event="sunset")
        actions = [
            Action(action_type="gpio", action_name="attract_on", offset_minutes=0),
            Action(action_type="gpio", action_name="flash_on", offset_minutes=5),
        ]
        routine = _make_routine(trigger, actions)
        schedule = _make_schedule(routines=[routine])

        result = reconcile_schedule(schedule, 9.0, -79.0, "America/Panama", now=now)

        assert len(result) == 2
        action_names = {r["action_name"] for r in result}
        assert action_names == {"attract_on", "flash_on"}

    @patch("webui.backend.lib.schedule_reconciler.calculate_execution_times")
    def test_lookback_window_respected(self, mock_calc):
        """Action 72h ago (outside 48h window) -> not returned."""
        now = _aware(datetime(2025, 6, 15, 22, 0, 0))
        # Trigger 72h ago — outside the 48h lookback
        trigger_time = _aware(datetime(2025, 6, 12, 22, 0, 0))
        mock_calc.return_value = [trigger_time]

        trigger = SolarTrigger(solar_event="sunset")
        actions = [Action(action_type="gpio", action_name="attract_on", offset_minutes=0)]
        routine = _make_routine(trigger, actions)
        schedule = _make_schedule(routines=[routine])

        result = reconcile_schedule(schedule, 9.0, -79.0, "America/Panama", now=now)
        assert result == []

    @patch("webui.backend.lib.schedule_reconciler.calculate_execution_times")
    def test_action_offsets_applied(self, mock_calc):
        """Routine triggers at sunset, action at offset_minutes=5 -> correct action_time."""
        now = _aware(datetime(2025, 6, 15, 22, 0, 0))
        trigger_time = _aware(datetime(2025, 6, 15, 21, 0, 0))
        mock_calc.return_value = [trigger_time]

        trigger = SolarTrigger(solar_event="sunset")
        actions = [
            Action(action_type="gpio", action_name="attract_on", offset_minutes=5),
        ]
        routine = _make_routine(trigger, actions)
        schedule = _make_schedule(routines=[routine])

        result = reconcile_schedule(schedule, 9.0, -79.0, "America/Panama", now=now)

        assert len(result) == 1
        expected_time = trigger_time + timedelta(minutes=5)
        assert result[0]["source_time"] == expected_time

    @patch("webui.backend.lib.schedule_reconciler.calculate_execution_times")
    def test_gps_sync_reconciled(self, mock_calc):
        """gps_sync within window -> returned (action_name is 'sync')."""
        now = _aware(datetime(2025, 6, 15, 22, 0, 0))
        trigger_time = _aware(datetime(2025, 6, 15, 21, 0, 0))
        mock_calc.return_value = [trigger_time]

        trigger = FixedTimeTrigger(time="21:00")
        actions = [
            Action(action_type="gps_sync", action_name="sync", offset_minutes=0),
        ]
        routine = _make_routine(trigger, actions)
        schedule = _make_schedule(routines=[routine])

        result = reconcile_schedule(schedule, 9.0, -79.0, "America/Panama", now=now)

        assert len(result) == 1
        assert result[0]["action_name"] == "sync"
        assert result[0]["action_type"] == "gps_sync"

    def test_sensor_trigger_skipped(self):
        """Routines with SensorTrigger are skipped (not schedulable)."""
        trigger = SensorTrigger(
            sensor_type="light",
            comparison="lt",
            threshold=100,
        )
        actions = [Action(action_type="gpio", action_name="attract_on", offset_minutes=0)]
        routine = _make_routine(trigger, actions)
        schedule = _make_schedule(routines=[routine])

        now = _aware(datetime(2025, 6, 15, 22, 0, 0))
        result = reconcile_schedule(schedule, 9.0, -79.0, "America/Panama", now=now)
        assert result == []

    @patch("webui.backend.lib.schedule_reconciler.calculate_execution_times")
    def test_calculation_error_skips_routine(self, mock_calc):
        """If calculate_execution_times raises, that routine is skipped."""
        mock_calc.side_effect = ValueError("Solar calculation failed")

        trigger = SolarTrigger(solar_event="sunset")
        actions = [Action(action_type="gpio", action_name="attract_on", offset_minutes=0)]
        routine = _make_routine(trigger, actions)
        schedule = _make_schedule(routines=[routine])

        now = _aware(datetime(2025, 6, 15, 22, 0, 0))
        result = reconcile_schedule(schedule, 9.0, -79.0, "America/Panama", now=now)
        assert result == []

    @patch("webui.backend.lib.schedule_reconciler.calculate_execution_times")
    def test_multiple_trigger_times_most_recent_wins(self, mock_calc):
        """With triggers on day 1 and day 2, the most recent one wins."""
        now = _aware(datetime(2025, 6, 16, 22, 0, 0))
        day1_trigger = _aware(datetime(2025, 6, 15, 20, 0, 0))
        day2_trigger = _aware(datetime(2025, 6, 16, 20, 0, 0))
        mock_calc.return_value = [day1_trigger, day2_trigger]

        trigger = SolarTrigger(solar_event="sunset")
        actions = [
            Action(action_type="gpio", action_name="attract_on", offset_minutes=0),
            Action(action_type="gpio", action_name="attract_off", offset_minutes=120),
        ]
        routine = _make_routine(trigger, actions)
        schedule = _make_schedule(routines=[routine])

        result = reconcile_schedule(schedule, 9.0, -79.0, "America/Panama", now=now)

        assert len(result) == 1
        # Day 2 attract_on at 20:00 is most recent (attract_off at 22:00 == now, included)
        assert result[0]["action_name"] == "attract_off"
        assert result[0]["source_time"] == day2_trigger + timedelta(minutes=120)

    def test_naive_datetime_raises_valueerror(self):
        """Passing a naive datetime for now raises ValueError."""
        import pytest

        schedule = _make_schedule(routines=[])
        naive_now = datetime(2025, 6, 15, 22, 0, 0)  # no tzinfo

        with pytest.raises(ValueError, match="timezone-aware"):
            reconcile_schedule(schedule, 9.0, -79.0, "America/Panama", now=naive_now)


class TestExecuteReconciliation:
    """Tests for execute_reconciliation()."""

    @patch("webui.backend.lib.schedule_reconciler.subprocess.run")
    @patch("webui.backend.lib.schedule_reconciler.get_validated_command")
    @patch("webui.backend.lib.schedule_reconciler.get_script_key_for_action")
    def test_executes_command_success(self, mock_key, mock_cmd, mock_run):
        mock_key.return_value = "attract_on"
        mock_cmd.return_value = "systemd-cat -t mothbox /usr/bin/python3 /opt/mothbox/Attract_On.py"
        mock_run.return_value.returncode = 0

        actions = [
            {
                "action_type": "gpio",
                "action_name": "attract_on",
                "source_time": datetime(2025, 6, 15, 20, 0, 0),
            }
        ]

        results = execute_reconciliation(actions)

        assert len(results) == 1
        assert results[0]["success"] is True
        mock_run.assert_called_once()

    @patch("webui.backend.lib.schedule_reconciler.subprocess.run")
    @patch("webui.backend.lib.schedule_reconciler.get_validated_command")
    @patch("webui.backend.lib.schedule_reconciler.get_script_key_for_action")
    def test_nonzero_exit_reports_failure(self, mock_key, mock_cmd, mock_run):
        """Non-zero exit code from script is reported as failure."""
        mock_key.return_value = "attract_on"
        mock_cmd.return_value = "systemd-cat -t mothbox /usr/bin/python3 /opt/mothbox/Attract_On.py"
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = b"GPIO daemon not running"

        actions = [
            {
                "action_type": "gpio",
                "action_name": "attract_on",
                "source_time": datetime(2025, 6, 15, 20, 0, 0),
            }
        ]

        results = execute_reconciliation(actions)

        assert len(results) == 1
        assert results[0]["success"] is False
        assert "GPIO daemon not running" in results[0]["error"]

    @patch("webui.backend.lib.schedule_reconciler.get_script_key_for_action")
    def test_unknown_script_key(self, mock_key):
        mock_key.return_value = None

        actions = [
            {
                "action_type": "unknown",
                "action_name": "unknown_action",
                "source_time": datetime(2025, 6, 15, 20, 0, 0),
            }
        ]

        results = execute_reconciliation(actions)
        assert len(results) == 1
        assert results[0]["success"] is False

    @patch("webui.backend.lib.schedule_reconciler.subprocess.run")
    @patch("webui.backend.lib.schedule_reconciler.get_validated_command")
    @patch("webui.backend.lib.schedule_reconciler.get_script_key_for_action")
    def test_timeout_handled(self, mock_key, mock_cmd, mock_run):
        import subprocess as sp

        mock_key.return_value = "attract_on"
        mock_cmd.return_value = "some-command"
        mock_run.side_effect = sp.TimeoutExpired(cmd="some-command", timeout=30)

        actions = [
            {
                "action_type": "gpio",
                "action_name": "attract_on",
                "source_time": datetime(2025, 6, 15, 20, 0, 0),
            }
        ]

        results = execute_reconciliation(actions)
        assert len(results) == 1
        assert results[0]["success"] is False
        assert "timed out" in results[0]["error"]

    @patch("webui.backend.lib.schedule_reconciler.subprocess.run")
    @patch("webui.backend.lib.schedule_reconciler.get_validated_command")
    @patch("webui.backend.lib.schedule_reconciler.get_script_key_for_action")
    def test_oserror_handled(self, mock_key, mock_cmd, mock_run):
        mock_key.return_value = "attract_on"
        mock_cmd.return_value = "some-command"
        mock_run.side_effect = OSError("No such file")

        actions = [
            {
                "action_type": "gpio",
                "action_name": "attract_on",
                "source_time": datetime(2025, 6, 15, 20, 0, 0),
            }
        ]

        results = execute_reconciliation(actions)
        assert len(results) == 1
        assert results[0]["success"] is False
        assert "No such file" in results[0]["error"]

    def test_empty_actions(self):
        results = execute_reconciliation([])
        assert results == []

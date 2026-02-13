"""Unit tests for refresh_schedule CLI script."""

import json
from unittest.mock import MagicMock, patch

from webui.backend.lib.cron_bridge import CronBridgeResult, CronEntry


class TestRefreshSchedule:
    """Tests for the weekly cron refresh CLI."""

    def test_no_active_state_exits_cleanly(self, tmp_path, monkeypatch):
        """No active_state.json -> exits 0."""
        monkeypatch.setattr("mothbox_paths.CONFIG_DIR", tmp_path)

        from webui.cli.refresh_schedule import main

        result = main()
        assert result == 0

    def test_refreshes_cron_entries(self, tmp_path, monkeypatch):
        """Mock cron_bridge functions, verify schedule_to_cron + apply_to_system called."""
        monkeypatch.setattr("mothbox_paths.CONFIG_DIR", tmp_path)

        state = {
            "schedule_id": "test-123",
            "latitude": 9.0,
            "longitude": -79.0,
            "timezone_name": "America/Panama",
        }
        (tmp_path / "active_state.json").write_text(json.dumps(state))

        mock_schedule = MagicMock()
        mock_entries = [
            CronEntry(expression="0 21 * * *", command="test-cmd", comment="Mothbox: test")
        ]
        mock_result = CronBridgeResult(
            entries=mock_entries, rtc_waketime=None, schedule_id="test-123", errors=[]
        )

        with (
            patch(
                "webui.backend.lib.schedule_storage.read_schedule",
                return_value=mock_schedule,
            ),
            patch(
                "webui.backend.lib.cron_bridge.schedule_to_cron",
                return_value=mock_result,
            ) as mock_s2c,
            patch(
                "webui.backend.lib.cron_bridge.apply_to_system",
                return_value=True,
            ) as mock_apply,
            patch(
                "webui.backend.lib.cron_bridge.expand_pattern_entries",
                return_value=mock_entries,
            ),
        ):
            from webui.cli.refresh_schedule import main

            result = main()

        assert result == 0
        mock_s2c.assert_called_once()
        mock_apply.assert_called_once()

    def test_updates_active_state(self, tmp_path, monkeypatch):
        """Verify expanded entries written back to active_state.json."""
        monkeypatch.setattr("mothbox_paths.CONFIG_DIR", tmp_path)

        state = {
            "schedule_id": "test-123",
            "latitude": 9.0,
            "longitude": -79.0,
            "timezone_name": "America/Panama",
        }
        state_file = tmp_path / "active_state.json"
        state_file.write_text(json.dumps(state))

        mock_schedule = MagicMock()
        mock_entry = CronEntry(expression="0 21 * * *", command="test-cmd", comment="Mothbox: test")
        mock_result = CronBridgeResult(
            entries=[mock_entry], rtc_waketime=None, schedule_id="test-123", errors=[]
        )

        with (
            patch(
                "webui.backend.lib.schedule_storage.read_schedule",
                return_value=mock_schedule,
            ),
            patch(
                "webui.backend.lib.cron_bridge.schedule_to_cron",
                return_value=mock_result,
            ),
            patch(
                "webui.backend.lib.cron_bridge.apply_to_system",
                return_value=True,
            ),
            patch(
                "webui.backend.lib.cron_bridge.expand_pattern_entries",
                return_value=[mock_entry],
            ),
        ):
            from webui.cli.refresh_schedule import main

            result = main()

        assert result == 0

        # Verify active_state.json was updated with entries
        updated_state = json.loads(state_file.read_text())
        assert "entries" in updated_state
        assert len(updated_state["entries"]) == 1

        # Verify pre-existing keys are preserved (not clobbered by the save)
        assert updated_state["schedule_id"] == "test-123"
        assert updated_state["latitude"] == 9.0
        assert updated_state["longitude"] == -79.0
        assert updated_state["timezone_name"] == "America/Panama"

    def test_schedule_not_found_returns_1(self, tmp_path, monkeypatch):
        """Schedule not found in storage -> returns 1."""
        monkeypatch.setattr("mothbox_paths.CONFIG_DIR", tmp_path)

        state = {"schedule_id": "nonexistent"}
        (tmp_path / "active_state.json").write_text(json.dumps(state))

        with patch(
            "webui.backend.lib.schedule_storage.read_schedule",
            return_value=None,
        ):
            from webui.cli.refresh_schedule import main

            result = main()

        assert result == 1

    def test_save_aborts_if_schedule_changed(self, tmp_path, monkeypatch):
        """save_active_state returns False if schedule_id changed since load."""
        monkeypatch.setattr("mothbox_paths.CONFIG_DIR", tmp_path)

        state = {
            "schedule_id": "original-schedule",
            "latitude": 9.0,
            "longitude": -79.0,
            "timezone_name": "UTC",
        }
        state_file = tmp_path / "active_state.json"
        state_file.write_text(json.dumps(state))

        from webui.cli.refresh_schedule import save_active_state

        result = save_active_state(
            [{"expression": "0 0 * * *"}],
            expected_schedule_id="different-schedule",
        )
        assert result is False

        # Verify file is unmodified
        unchanged = json.loads(state_file.read_text())
        assert "entries" not in unchanged
        assert unchanged["schedule_id"] == "original-schedule"

    def test_save_succeeds_with_matching_schedule_id(self, tmp_path, monkeypatch):
        """save_active_state succeeds when expected_schedule_id matches."""
        monkeypatch.setattr("mothbox_paths.CONFIG_DIR", tmp_path)

        state = {
            "schedule_id": "test-123",
            "latitude": 9.0,
        }
        state_file = tmp_path / "active_state.json"
        state_file.write_text(json.dumps(state))

        from webui.cli.refresh_schedule import save_active_state

        result = save_active_state(
            [{"expression": "0 0 * * *"}],
            expected_schedule_id="test-123",
        )
        assert result is True

        updated = json.loads(state_file.read_text())
        assert updated["entries"] == [{"expression": "0 0 * * *"}]
        assert updated["schedule_id"] == "test-123"

    def test_cron_conversion_errors_returns_1(self, tmp_path, monkeypatch):
        """Cron conversion errors -> returns 1."""
        monkeypatch.setattr("mothbox_paths.CONFIG_DIR", tmp_path)

        state = {"schedule_id": "test-123"}
        (tmp_path / "active_state.json").write_text(json.dumps(state))

        mock_schedule = MagicMock()
        mock_result = CronBridgeResult(
            entries=[], rtc_waketime=None, schedule_id="test-123", errors=["Solar calc failed"]
        )

        with (
            patch(
                "webui.backend.lib.schedule_storage.read_schedule",
                return_value=mock_schedule,
            ),
            patch(
                "webui.backend.lib.cron_bridge.schedule_to_cron",
                return_value=mock_result,
            ),
        ):
            from webui.cli.refresh_schedule import main

            result = main()

        assert result == 1

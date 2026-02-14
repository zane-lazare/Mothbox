"""Unit tests for reconcile_on_boot CLI script."""

import json
from unittest.mock import MagicMock, patch

from lib.gpio_protocol import SOCKET_PATH


class TestCronSecurityWhitelist:
    """Verify CLI scripts remain in the cron security whitelist."""

    def test_reconcile_on_boot_in_allowed_scripts(self):
        """reconcile_on_boot must be in ALLOWED_SCRIPTS to run via cron."""
        from webui.backend.lib.cron_security import ALLOWED_SCRIPTS

        assert "reconcile_on_boot" in ALLOWED_SCRIPTS

    def test_refresh_schedule_in_allowed_scripts(self):
        """refresh_schedule must be in ALLOWED_SCRIPTS to run via cron."""
        from webui.backend.lib.cron_security import ALLOWED_SCRIPTS

        assert "refresh_schedule" in ALLOWED_SCRIPTS


class TestReconcileOnBoot:
    """Tests for the boot reconciliation CLI."""

    def test_gpio_socket_uses_protocol_constant(self):
        """GPIO_SOCKET path matches the shared gpio_protocol.SOCKET_PATH."""
        from webui.cli.reconcile_on_boot import GPIO_SOCKET

        assert str(GPIO_SOCKET) == SOCKET_PATH

    def test_no_active_state_exits_cleanly(self, tmp_path, monkeypatch):
        """No active_state.json -> exits 0."""
        monkeypatch.setattr("mothbox_paths.CONFIG_DIR", tmp_path)

        from webui.cli.reconcile_on_boot import main

        with patch("webui.cli.reconcile_on_boot.wait_for_gpio_daemon", return_value=True):
            result = main()

        assert result == 0

    def test_empty_schedule_id_exits_cleanly(self, tmp_path, monkeypatch):
        """active_state.json with no schedule_id -> exits 0."""
        monkeypatch.setattr("mothbox_paths.CONFIG_DIR", tmp_path)
        state_file = tmp_path / "active_state.json"
        state_file.write_text(json.dumps({"schedule_id": None}))

        from webui.cli.reconcile_on_boot import main

        with patch("webui.cli.reconcile_on_boot.wait_for_gpio_daemon", return_value=True):
            result = main()

        assert result == 0

    @patch("webui.cli.reconcile_on_boot.wait_for_gpio_daemon", return_value=True)
    def test_loads_schedule_and_reconciles(self, mock_daemon, tmp_path, monkeypatch):
        """Mock file + reconciler, verify flow."""
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
        mock_actions = [{"action_type": "gpio", "action_name": "attract_on", "source_time": None}]

        with (
            patch(
                "webui.backend.lib.schedule_storage.read_schedule",
                return_value=mock_schedule,
            ),
            patch(
                "webui.backend.lib.schedule_reconciler.reconcile_schedule",
                return_value=mock_actions,
            ) as mock_reconcile,
            patch(
                "webui.backend.lib.schedule_reconciler.execute_reconciliation",
                return_value=[{"action_name": "attract_on", "success": True, "error": None}],
            ) as mock_execute,
        ):
            from webui.cli.reconcile_on_boot import main

            result = main()

        assert result == 0
        mock_reconcile.assert_called_once_with(mock_schedule, 9.0, -79.0, "America/Panama")
        mock_execute.assert_called_once()

    @patch("webui.cli.reconcile_on_boot.wait_for_gpio_daemon", return_value=False)
    def test_failed_actions_return_exit_code_2(self, mock_daemon, tmp_path, monkeypatch):
        """Failed reconciliation actions -> returns 2 (partial success)."""
        monkeypatch.setattr("mothbox_paths.CONFIG_DIR", tmp_path)

        state = {
            "schedule_id": "test-123",
            "latitude": 9.0,
            "longitude": -79.0,
            "timezone_name": "America/Panama",
        }
        (tmp_path / "active_state.json").write_text(json.dumps(state))

        mock_schedule = MagicMock()
        mock_actions = [{"action_type": "gpio", "action_name": "attract_on", "source_time": None}]

        with (
            patch(
                "webui.backend.lib.schedule_storage.read_schedule",
                return_value=mock_schedule,
            ),
            patch(
                "webui.backend.lib.schedule_reconciler.reconcile_schedule",
                return_value=mock_actions,
            ),
            patch(
                "webui.backend.lib.schedule_reconciler.execute_reconciliation",
                return_value=[
                    {"action_name": "attract_on", "success": False, "error": "daemon unavailable"}
                ],
            ),
        ):
            from webui.cli.reconcile_on_boot import main

            result = main()

        assert result == 2

    def test_daemon_socket_timeout(self, tmp_path, monkeypatch):
        """Socket never appears -> proceeds with warning, still returns 0 if no state."""
        monkeypatch.setattr("mothbox_paths.CONFIG_DIR", tmp_path)

        from webui.cli.reconcile_on_boot import main

        # Patch wait_for_gpio_daemon to return False (timeout)
        with patch("webui.cli.reconcile_on_boot.wait_for_gpio_daemon", return_value=False):
            result = main()

        # No active state, so exits 0 despite daemon timeout
        assert result == 0

    @patch("webui.cli.reconcile_on_boot.wait_for_gpio_daemon", return_value=True)
    def test_missing_coordinates_uses_timezone_fallback(self, mock_daemon, tmp_path, monkeypatch):
        """Missing lat/lon in state -> falls back to timezone-derived coordinates."""
        monkeypatch.setattr("mothbox_paths.CONFIG_DIR", tmp_path)

        state = {
            "schedule_id": "test-123",
            "timezone_name": "America/Panama",
        }
        (tmp_path / "active_state.json").write_text(json.dumps(state))

        mock_schedule = MagicMock()
        mock_actions = []

        with (
            patch(
                "webui.backend.lib.schedule_storage.read_schedule",
                return_value=mock_schedule,
            ),
            patch(
                "webui.backend.lib.schedule_reconciler.reconcile_schedule",
                return_value=mock_actions,
            ) as mock_reconcile,
            patch(
                "webui.backend.lib.timezone_coordinates.get_fallback_coordinates",
                return_value=(8.98, -79.52, "America/Panama"),
            ),
        ):
            from webui.cli.reconcile_on_boot import main

            result = main()

        assert result == 0
        mock_reconcile.assert_called_once_with(mock_schedule, 8.98, -79.52, "America/Panama")

    @patch("webui.cli.reconcile_on_boot.wait_for_gpio_daemon", return_value=True)
    def test_schedule_not_found_returns_1(self, mock_daemon, tmp_path, monkeypatch):
        """Schedule ID in state but not in storage -> returns 1."""
        monkeypatch.setattr("mothbox_paths.CONFIG_DIR", tmp_path)

        state = {"schedule_id": "nonexistent"}
        (tmp_path / "active_state.json").write_text(json.dumps(state))

        with patch(
            "webui.backend.lib.schedule_storage.read_schedule",
            return_value=None,
        ):
            from webui.cli.reconcile_on_boot import main

            result = main()

        assert result == 1

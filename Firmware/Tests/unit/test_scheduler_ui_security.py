"""Security tests for scheduler_ui routes (Issue #385 security review)."""

from unittest.mock import MagicMock

import pytest

# Try to import Flask app for testing
try:
    from webui.backend.app import app

    IMPLEMENTATION_EXISTS = True
except ImportError:
    IMPLEMENTATION_EXISTS = False
    app = None

# Skip all tests if implementation doesn't exist
pytestmark = pytest.mark.skipif(not IMPLEMENTATION_EXISTS, reason="Implementation not yet created")


def _get_scheduler_ui_module():
    """Get the scheduler_ui module as used by app.py."""
    import sys

    module = sys.modules.get("routes.scheduler_ui")
    if module is None:
        import webui.backend.routes.scheduler_ui as module
    return module


class TestErrorMessageSanitization:
    """Tests for XSS prevention in error responses."""

    def test_validate_location_params_sanitizes_timezone_error(self):
        """Error messages should not contain raw user input."""
        from webui.backend.routes.scheduler_ui import _validate_location_params

        malicious_tz = "<script>alert('xss')</script>"
        with app.app_context():
            result = _validate_location_params(0.0, 0.0, malicious_tz)

        assert result is not None
        response, status = result
        assert status == 400
        data = response.get_json()
        error_msg = data.get("error", "")
        assert "<script>" not in error_msg
        assert "alert" not in error_msg

    def test_validate_location_params_sanitizes_coordinate_error(self):
        """Coordinate error messages should be safe."""
        from webui.backend.routes.scheduler_ui import _validate_location_params

        with app.app_context():
            result = _validate_location_params(999.0, 999.0, "UTC")

        assert result is not None
        response, status = result
        assert status == 400
        data = response.get_json()
        error_msg = data.get("error", "")
        assert "Invalid coordinates" in error_msg

    def test_sanitize_message_strips_html(self):
        """sanitize_message() should strip HTML tags."""
        from webui.backend.lib.error_codes import sanitize_message

        malicious = "<script>alert('xss')</script>Normal text<b>bold</b>"
        sanitized = sanitize_message(malicious)

        assert "<script>" not in sanitized
        assert "<b>" not in sanitized
        assert "Normal text" in sanitized
        assert "bold" in sanitized

    def test_sanitize_message_truncates_long_messages(self):
        """Long error messages should be truncated."""
        from webui.backend.lib.error_codes import sanitize_message

        long_msg = "x" * 500
        sanitized = sanitize_message(long_msg)

        assert len(sanitized) <= 200

    def test_sanitize_message_handles_none(self):
        """None input should return generic message."""
        from webui.backend.lib.error_codes import sanitize_message

        assert sanitize_message(None) == "An error occurred"

    def test_sanitize_message_handles_empty(self):
        """Empty input should return generic message."""
        from webui.backend.lib.error_codes import sanitize_message

        assert sanitize_message("") == "An error occurred"

    def test_sanitize_message_redacts_internal_paths(self):
        """Internal file paths should be redacted."""
        from webui.backend.lib.error_codes import sanitize_message

        msg = "Failed to read /etc/secrets/api_key.txt"
        sanitized = sanitize_message(msg)

        assert "/etc/secrets" not in sanitized
        assert "[path]" in sanitized
        assert "Failed to read" in sanitized

    def test_sanitize_message_redacts_various_paths(self):
        """Various internal paths should be redacted."""
        from webui.backend.lib.error_codes import sanitize_message

        test_cases = [
            "/var/log/mothbox.log",
            "/home/pi/Desktop/Mothbox/config.txt",
            "/opt/mothbox/settings.json",
            "/usr/local/bin/script.sh",
            "/tmp/cache/data.db",
            "/root/.config/secret",
        ]
        for path in test_cases:
            msg = f"Error at {path}"
            sanitized = sanitize_message(msg)
            # Original path should be redacted
            assert path not in sanitized, f"Path {path} should be redacted"
            assert "[path]" in sanitized


class TestExceptionSanitization:
    """Tests for exception message sanitization."""

    @pytest.fixture
    def scheduler_client(self):
        """Create Flask test client with CSRF disabled."""
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        with app.test_client() as client:
            yield client

    @pytest.fixture
    def mock_scheduler_service(self):
        """Mock SchedulerService by directly setting the module variable."""
        module = _get_scheduler_ui_module()
        mock_service = MagicMock()
        # Default return value for entry count warning (no warning by default)
        mock_service.get_entry_count_warning.return_value = None
        original = getattr(module, "_scheduler_service", None)
        module._scheduler_service = mock_service
        yield mock_service
        module._scheduler_service = original

    def test_update_schedule_enabled_error_sanitized(
        self, scheduler_client, mock_scheduler_service
    ):
        """Exception details should be sanitized in error responses."""
        from uuid import uuid4

        # Mock service to raise ValueError with sensitive info
        mock_scheduler_service.get_schedule.return_value = MagicMock()
        mock_scheduler_service.set_enabled_schedule.side_effect = ValueError(
            "Internal path: /etc/secrets/api_key.txt not found"
        )

        schedule_id = str(uuid4())
        response = scheduler_client.put(
            f"/api/scheduler/ui/schedules/{schedule_id}",
            json={"enabled": True},
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 400
        data = response.get_json()
        # Should not contain full internal path
        assert "/etc/secrets" not in data.get("error", "")

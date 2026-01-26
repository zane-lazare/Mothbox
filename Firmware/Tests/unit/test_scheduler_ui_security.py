"""Security tests for scheduler_ui routes (Issue #385 security review)."""

import pytest


class TestErrorMessageSanitization:
    """Tests for XSS prevention in error responses."""

    def test_validate_location_params_sanitizes_timezone_error(self):
        """Error messages should not contain raw user input."""
        from webui.backend.routes.scheduler_ui import _validate_location_params

        malicious_tz = "<script>alert('xss')</script>"
        error, status = _validate_location_params(0.0, 0.0, malicious_tz)

        assert error is not None
        assert status == 400
        error_msg = error.get("error", "")
        assert "<script>" not in error_msg
        assert "alert" not in error_msg

    def test_validate_location_params_sanitizes_coordinate_error(self):
        """Coordinate error messages should be safe."""
        from webui.backend.routes.scheduler_ui import _validate_location_params

        error, status = _validate_location_params(999.0, 999.0, "UTC")

        assert error is not None
        assert status == 400
        error_msg = error.get("error", "")
        assert "Invalid coordinates" in error_msg

    def test_sanitize_error_message_strips_html(self):
        """_sanitize_error_message should strip HTML tags."""
        from webui.backend.routes.scheduler_ui import _sanitize_error_message

        malicious = "<script>alert('xss')</script>Normal text<b>bold</b>"
        sanitized = _sanitize_error_message(malicious)

        assert "<script>" not in sanitized
        assert "<b>" not in sanitized
        assert "Normal text" in sanitized
        assert "bold" in sanitized

    def test_sanitize_error_message_truncates_long_messages(self):
        """Long error messages should be truncated."""
        from webui.backend.routes.scheduler_ui import _sanitize_error_message

        long_msg = "x" * 500
        sanitized = _sanitize_error_message(long_msg)

        assert len(sanitized) <= 200

    def test_sanitize_error_message_handles_none(self):
        """None input should return generic message."""
        from webui.backend.routes.scheduler_ui import _sanitize_error_message

        assert _sanitize_error_message(None) == "An error occurred"

    def test_sanitize_error_message_handles_empty(self):
        """Empty input should return generic message."""
        from webui.backend.routes.scheduler_ui import _sanitize_error_message

        assert _sanitize_error_message("") == "An error occurred"

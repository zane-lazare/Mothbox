"""Tests for shared error codes module."""

import json

import pytest


class TestErrorCodes:
    """Test error code constants."""

    def test_all_codes_are_strings(self):
        from webui.backend.lib.error_codes import ERROR_CODES

        for key, value in ERROR_CODES.items():
            assert isinstance(value, str), f"{key} should be a string"
            assert value == key, f"Value should match key: {key}"

    def test_required_codes_exist(self):
        from webui.backend.lib.error_codes import ERROR_CODES

        required = [
            "VALIDATION_ERROR",
            "NOT_FOUND",
            "CONFLICT_ERROR",
            "ACTIVATION_ERROR",
            "RATE_LIMIT_ERROR",
            "HARDWARE_ERROR",
            "STORAGE_ERROR",
            "PERMISSION_ERROR",
            "SERVER_ERROR",
        ]
        for code in required:
            assert code in ERROR_CODES, f"Missing required code: {code}"

    def test_codes_importable_as_module_attributes(self):
        from webui.backend.lib.error_codes import (
            ACTIVATION_ERROR,
            CONFLICT_ERROR,
            HARDWARE_ERROR,
            NOT_FOUND,
            PERMISSION_ERROR,
            RATE_LIMIT_ERROR,
            SERVER_ERROR,
            STORAGE_ERROR,
            VALIDATION_ERROR,
        )

        assert VALIDATION_ERROR == "VALIDATION_ERROR"
        assert NOT_FOUND == "NOT_FOUND"
        assert CONFLICT_ERROR == "CONFLICT_ERROR"
        assert ACTIVATION_ERROR == "ACTIVATION_ERROR"
        assert RATE_LIMIT_ERROR == "RATE_LIMIT_ERROR"
        assert HARDWARE_ERROR == "HARDWARE_ERROR"
        assert STORAGE_ERROR == "STORAGE_ERROR"
        assert PERMISSION_ERROR == "PERMISSION_ERROR"
        assert SERVER_ERROR == "SERVER_ERROR"


class TestSanitizeMessage:
    """Test message sanitization for safe display."""

    def test_strips_html_tags(self):
        from webui.backend.lib.error_codes import sanitize_message

        assert sanitize_message("<b>bold</b> text") == "bold text"

    def test_strips_script_tags(self):
        from webui.backend.lib.error_codes import sanitize_message

        result = sanitize_message("<script>alert('xss')</script>hello")
        assert "<script>" not in result
        assert "hello" in result

    def test_strips_incomplete_tags(self):
        from webui.backend.lib.error_codes import sanitize_message

        result = sanitize_message("text <script without closing")
        assert "<" not in result

    def test_redacts_internal_paths(self):
        from webui.backend.lib.error_codes import sanitize_message

        result = sanitize_message("Error reading /etc/secrets/key.pem")
        assert "/etc/secrets" not in result
        assert "[path]" in result

    def test_redacts_var_paths(self):
        from webui.backend.lib.error_codes import sanitize_message

        result = sanitize_message("File not found: /var/lib/mothbox/data.json")
        assert "/var/lib" not in result

    def test_redacts_home_paths(self):
        from webui.backend.lib.error_codes import sanitize_message

        result = sanitize_message("Error in /home/pi/Desktop/Mothbox/config")
        assert "/home/pi" not in result

    def test_truncates_long_messages(self):
        from webui.backend.lib.error_codes import sanitize_message

        long_msg = "x" * 300
        result = sanitize_message(long_msg)
        assert len(result) <= 200
        assert result.endswith("...")

    def test_custom_max_length(self):
        from webui.backend.lib.error_codes import sanitize_message

        result = sanitize_message("x" * 100, max_length=50)
        assert len(result) <= 50

    def test_none_returns_default(self):
        from webui.backend.lib.error_codes import sanitize_message

        assert sanitize_message(None) == "An error occurred"

    def test_empty_string_returns_default(self):
        from webui.backend.lib.error_codes import sanitize_message

        assert sanitize_message("") == "An error occurred"

    def test_normal_message_unchanged(self):
        from webui.backend.lib.error_codes import sanitize_message

        assert sanitize_message("Schedule not found") == "Schedule not found"


class TestErrorResponse:
    """Test error_response helper produces correct JSON format."""

    @pytest.fixture(autouse=True)
    def _flask_app(self):
        """Create minimal Flask app for jsonify context."""
        from flask import Flask

        app = Flask(__name__)
        with app.app_context():
            yield app

    def test_basic_error_response(self):
        from webui.backend.lib.error_codes import VALIDATION_ERROR, error_response

        response, status = error_response(VALIDATION_ERROR, "Bad input", 400)
        data = json.loads(response.get_data(as_text=True))
        assert data["error"] == "Bad input"
        assert data["code"] == "VALIDATION_ERROR"
        assert status == 400

    def test_default_status_is_400(self):
        from webui.backend.lib.error_codes import VALIDATION_ERROR, error_response

        _, status = error_response(VALIDATION_ERROR, "Bad input")
        assert status == 400

    def test_server_error_status(self):
        from webui.backend.lib.error_codes import SERVER_ERROR, error_response

        _, status = error_response(SERVER_ERROR, "Internal error", 500)
        assert status == 500

    def test_not_found_status(self):
        from webui.backend.lib.error_codes import NOT_FOUND, error_response

        response, status = error_response(NOT_FOUND, "Schedule not found", 404)
        data = json.loads(response.get_data(as_text=True))
        assert data["code"] == "NOT_FOUND"
        assert status == 404

    def test_extra_fields_included(self):
        from webui.backend.lib.error_codes import CONFLICT_ERROR, error_response

        response, status = error_response(CONFLICT_ERROR, "Conflict", 409, conflict=True)
        data = json.loads(response.get_data(as_text=True))
        assert data["conflict"] is True
        assert data["code"] == "CONFLICT_ERROR"

    def test_message_is_sanitized(self):
        from webui.backend.lib.error_codes import VALIDATION_ERROR, error_response

        response, _ = error_response(VALIDATION_ERROR, "<script>xss</script>Bad input", 400)
        data = json.loads(response.get_data(as_text=True))
        assert "<script>" not in data["error"]

    def test_path_redacted_in_response(self):
        from webui.backend.lib.error_codes import SERVER_ERROR, error_response

        response, _ = error_response(SERVER_ERROR, "Error reading /etc/mothbox/config.txt", 500)
        data = json.loads(response.get_data(as_text=True))
        assert "/etc/mothbox" not in data["error"]

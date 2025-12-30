"""
Unit tests for API Key Authentication Library.

Tests cover:
- API key loading from environment variables and controls.txt
- Constant-time comparison using hmac.compare_digest
- Dual authentication (CSRF OR API key)
- Error responses for missing/invalid keys

Issue: #175 - API Key Authentication for Sidecar Metadata API
"""

import os
from unittest.mock import patch

import pytest


class TestApiKeyConfiguration:
    """Test API key loading from various sources."""

    def test_loads_api_key_from_environment_variable(self):
        """Environment variable MOTHBOX_API_KEY should be the primary source."""
        from webui.backend.lib.api_key_auth import get_api_key_from_config

        with patch.dict(os.environ, {"MOTHBOX_API_KEY": "test-secret-key-123"}):
            assert get_api_key_from_config() == "test-secret-key-123"

    def test_environment_variable_takes_precedence_over_controls_txt(self):
        """Environment variable should override controls.txt if both exist."""
        from webui.backend.lib.api_key_auth import get_api_key_from_config

        mock_controls = {"api_key": "controls-key-456"}

        with patch.dict(os.environ, {"MOTHBOX_API_KEY": "env-key-789"}), patch(
            "webui.backend.lib.api_key_auth.get_control_values",
            return_value=mock_controls,
        ):
            assert get_api_key_from_config() == "env-key-789"

    def test_falls_back_to_controls_txt_when_no_env_var(self):
        """If no env var, should fall back to controls.txt."""
        from webui.backend.lib.api_key_auth import get_api_key_from_config

        mock_controls = {"api_key": "controls-key-456"}

        # Ensure env var is not set
        with patch.dict(os.environ, {}, clear=True):
            # Remove MOTHBOX_API_KEY if it exists
            os.environ.pop("MOTHBOX_API_KEY", None)
            with patch(
                "webui.backend.lib.api_key_auth.get_control_values",
                return_value=mock_controls,
            ):
                assert get_api_key_from_config() == "controls-key-456"

    def test_returns_none_when_no_api_key_configured(self):
        """Should return None if no API key is configured anywhere."""
        from webui.backend.lib.api_key_auth import get_api_key_from_config

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MOTHBOX_API_KEY", None)
            with patch(
                "webui.backend.lib.api_key_auth.get_control_values",
                return_value={},
            ):
                assert get_api_key_from_config() is None

    def test_empty_api_key_treated_as_not_configured(self):
        """Empty string API key should be treated as not configured."""
        from webui.backend.lib.api_key_auth import get_api_key_from_config

        with patch.dict(os.environ, {"MOTHBOX_API_KEY": ""}), patch(
            "webui.backend.lib.api_key_auth.get_control_values",
            return_value={"api_key": ""},
        ):
            assert get_api_key_from_config() is None

    def test_whitespace_only_api_key_treated_as_not_configured(self):
        """Whitespace-only API key should be treated as not configured."""
        from webui.backend.lib.api_key_auth import get_api_key_from_config

        with patch.dict(os.environ, {"MOTHBOX_API_KEY": "   "}):
            assert get_api_key_from_config() is None


class TestApiKeyValidation:
    """Test API key validation with constant-time comparison."""

    def test_valid_api_key_returns_true(self):
        """Valid API key should return True."""
        from webui.backend.lib.api_key_auth import validate_api_key

        expected = "test-secret-key-123"
        provided = "test-secret-key-123"
        assert validate_api_key(provided, expected) is True

    def test_invalid_api_key_returns_false(self):
        """Invalid API key should return False."""
        from webui.backend.lib.api_key_auth import validate_api_key

        expected = "test-secret-key-123"
        provided = "wrong-key-456"
        assert validate_api_key(provided, expected) is False

    def test_none_provided_key_returns_false(self):
        """None provided key should return False."""
        from webui.backend.lib.api_key_auth import validate_api_key

        expected = "test-secret-key-123"
        assert validate_api_key(None, expected) is False

    def test_none_expected_key_returns_false(self):
        """None expected key (not configured) should return False."""
        from webui.backend.lib.api_key_auth import validate_api_key

        provided = "test-secret-key-123"
        assert validate_api_key(provided, None) is False

    def test_empty_provided_key_returns_false(self):
        """Empty provided key should return False."""
        from webui.backend.lib.api_key_auth import validate_api_key

        expected = "test-secret-key-123"
        assert validate_api_key("", expected) is False

    def test_uses_constant_time_comparison(self):
        """Should use hmac.compare_digest for constant-time comparison."""
        from webui.backend.lib.api_key_auth import validate_api_key

        # Verify the function uses constant-time comparison
        # by checking similar timing for same-length strings
        expected = "a" * 32
        wrong_first_char = "b" + "a" * 31

        # Should use constant-time comparison regardless of where mismatch occurs
        # (can't directly test timing, but we verify it uses hmac internally)
        with patch("webui.backend.lib.api_key_auth.hmac.compare_digest") as mock_compare:
            mock_compare.return_value = False
            validate_api_key(wrong_first_char, expected)
            # Verify hmac.compare_digest was called
            mock_compare.assert_called_once()

    def test_different_length_keys_return_false(self):
        """Keys of different lengths should return False."""
        from webui.backend.lib.api_key_auth import validate_api_key

        expected = "abcdefghijklmnop"
        short_key = "abc"
        long_key = "abcdefghijklmnopqrstuvwxyz"

        assert validate_api_key(short_key, expected) is False
        assert validate_api_key(long_key, expected) is False


class TestCheckApiKeyFromRequest:
    """Test checking API key from Flask request."""

    def test_valid_api_key_in_header_returns_true(self, app):
        """Valid X-API-Key header should pass validation."""
        from webui.backend.lib.api_key_auth import check_api_key_from_request

        with app.test_request_context(headers={"X-API-Key": "test-key-123"}), patch(
            "webui.backend.lib.api_key_auth.get_api_key_from_config",
            return_value="test-key-123",
        ):
            assert check_api_key_from_request() is True

    def test_invalid_api_key_in_header_returns_false(self, app):
        """Invalid X-API-Key header should fail validation."""
        from webui.backend.lib.api_key_auth import check_api_key_from_request

        with app.test_request_context(headers={"X-API-Key": "wrong-key"}), patch(
            "webui.backend.lib.api_key_auth.get_api_key_from_config",
            return_value="test-key-123",
        ):
            assert check_api_key_from_request() is False

    def test_missing_api_key_header_returns_false(self, app):
        """Missing X-API-Key header should fail validation."""
        from webui.backend.lib.api_key_auth import check_api_key_from_request

        with app.test_request_context(), patch(
            "webui.backend.lib.api_key_auth.get_api_key_from_config",
            return_value="test-key-123",
        ):
            assert check_api_key_from_request() is False

    def test_returns_true_when_api_key_not_configured(self, app):
        """If no API key is configured, all requests should be allowed."""
        from webui.backend.lib.api_key_auth import check_api_key_from_request

        with app.test_request_context(), patch(
            "webui.backend.lib.api_key_auth.get_api_key_from_config",
            return_value=None,
        ):
            # When API key is not configured, allow all (backwards compatible)
            assert check_api_key_from_request() is True


class TestRequireApiKeyOrCsrf:
    """Test the dual authentication decorator."""

    def test_valid_csrf_token_passes(self, app_with_csrf_exempt, client_csrf_exempt):
        """Valid CSRF token should allow request without API key."""
        from webui.backend.lib.api_key_auth import require_api_key_or_csrf

        app = app_with_csrf_exempt

        @app.route("/test-auth", methods=["POST"])
        @require_api_key_or_csrf
        def test_endpoint():
            return {"success": True}

        client = client_csrf_exempt

        # Get CSRF token
        response = client.get("/api/csrf-token")
        csrf_token = response.json.get("csrf_token")

        # POST with CSRF token should succeed
        response = client.post(
            "/test-auth",
            headers={"X-CSRFToken": csrf_token},
            json={},
        )
        assert response.status_code == 200

    def test_valid_api_key_passes(self, app_no_csrf, client_no_csrf):
        """Valid API key should allow request without CSRF token."""
        from webui.backend.lib.api_key_auth import require_api_key_or_csrf

        app = app_no_csrf

        @app.route("/test-auth-apikey", methods=["POST"])
        @require_api_key_or_csrf
        def test_endpoint():
            return {"success": True}

        client = client_no_csrf

        with patch(
            "webui.backend.lib.api_key_auth.get_api_key_from_config",
            return_value="test-key-123",
        ):
            response = client.post(
                "/test-auth-apikey",
                headers={"X-API-Key": "test-key-123"},
                json={},
            )
            assert response.status_code == 200

    def test_invalid_api_key_without_csrf_fails(self, app_no_csrf, client_no_csrf):
        """Invalid API key without CSRF token should fail."""
        from webui.backend.lib.api_key_auth import require_api_key_or_csrf

        app = app_no_csrf

        @app.route("/test-auth-fail", methods=["POST"])
        @require_api_key_or_csrf
        def test_endpoint():
            return {"success": True}

        client = client_no_csrf

        with patch(
            "webui.backend.lib.api_key_auth.get_api_key_from_config",
            return_value="test-key-123",
        ):
            response = client.post(
                "/test-auth-fail",
                headers={"X-API-Key": "wrong-key"},
                json={},
            )
            assert response.status_code == 401

    def test_no_auth_returns_401(self, app_no_csrf, client_no_csrf):
        """Missing both CSRF and API key should return 401."""
        from webui.backend.lib.api_key_auth import require_api_key_or_csrf

        app = app_no_csrf

        @app.route("/test-auth-none", methods=["POST"])
        @require_api_key_or_csrf
        def test_endpoint():
            return {"success": True}

        client = client_no_csrf

        with patch(
            "webui.backend.lib.api_key_auth.get_api_key_from_config",
            return_value="test-key-123",
        ):
            response = client.post("/test-auth-none", json={})
            assert response.status_code == 401

    def test_error_response_is_generic(self, app_no_csrf, client_no_csrf):
        """Error messages should be generic to prevent information disclosure."""
        from webui.backend.lib.api_key_auth import require_api_key_or_csrf

        app = app_no_csrf

        @app.route("/test-auth-error", methods=["POST"])
        @require_api_key_or_csrf
        def test_endpoint():
            return {"success": True}

        client = client_no_csrf

        with patch(
            "webui.backend.lib.api_key_auth.get_api_key_from_config",
            return_value="test-key-123",
        ):
            response = client.post(
                "/test-auth-error",
                headers={"X-API-Key": "wrong-key"},
                json={},
            )
            # Should not reveal whether key was wrong or missing
            assert "error" in response.json
            assert "invalid" not in response.json["error"].lower()
            assert "wrong" not in response.json["error"].lower()


class TestApiKeyNeverLogged:
    """Test that API keys are never logged."""

    def test_api_key_not_in_error_logs(self, app, caplog):
        """API keys should never appear in log messages."""
        from webui.backend.lib.api_key_auth import check_api_key_from_request

        secret_key = "super-secret-api-key-12345"

        with app.test_request_context(headers={"X-API-Key": secret_key}), patch(
            "webui.backend.lib.api_key_auth.get_api_key_from_config",
            return_value="different-key",
        ):
            check_api_key_from_request()

        # Verify API key not in any log messages
        for record in caplog.records:
            assert secret_key not in record.message
            assert "super-secret" not in record.message


# Fixtures
@pytest.fixture
def app():
    """Create Flask test app with CSRF enabled."""
    from flask import Flask
    from flask_wtf.csrf import CSRFProtect

    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret-for-testing"
    app.config["WTF_CSRF_ENABLED"] = True
    app.config["TESTING"] = True

    CSRFProtect(app)  # Initialize CSRF protection

    @app.route("/api/csrf-token", methods=["GET"])
    def get_csrf_token():
        from flask_wtf.csrf import generate_csrf

        return {"csrf_token": generate_csrf()}

    return app


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()


@pytest.fixture
def app_no_csrf():
    """Create Flask test app without CSRF protection."""
    from flask import Flask

    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret-for-testing"
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["TESTING"] = True

    return app


@pytest.fixture
def client_no_csrf(app_no_csrf):
    """Create Flask test client without CSRF."""
    return app_no_csrf.test_client()


@pytest.fixture
def app_with_csrf_exempt():
    """Create Flask test app with CSRF enabled but routes can be exempted."""
    from flask import Flask
    from flask_wtf.csrf import CSRFProtect

    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret-for-testing"
    app.config["WTF_CSRF_ENABLED"] = True
    app.config["TESTING"] = True

    CSRFProtect(app)  # Initialize CSRF protection

    @app.route("/api/csrf-token", methods=["GET"])
    def get_csrf_token():
        from flask_wtf.csrf import generate_csrf

        return {"csrf_token": generate_csrf()}

    return app


@pytest.fixture
def client_csrf_exempt(app_with_csrf_exempt):
    """Create Flask test client with CSRF support."""
    return app_with_csrf_exempt.test_client()

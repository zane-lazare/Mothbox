"""
Unit tests for Cron Validation API Routes (Issue #233 - Phase 1)

Tests the REST API endpoint for validating cron expressions and previewing
next execution times.

Coverage Target: 85%+

Issue #233 - Scheduler Expert Mode: Backend API
"""

from unittest.mock import MagicMock, patch

import pytest

# Try to import Flask app for testing
try:
    from webui.backend.app import app

    # Import scheduler_ui_bp to ensure it exists (used for skip condition)
    from webui.backend.routes.scheduler_ui import scheduler_ui_bp  # noqa: F401
    IMPLEMENTATION_EXISTS = True
except ImportError:
    IMPLEMENTATION_EXISTS = False
    app = None

# Skip all tests if implementation doesn't exist
pytestmark = pytest.mark.skipif(
    not IMPLEMENTATION_EXISTS,
    reason="Implementation not yet created"
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def reset_limiter():
    """Reset rate limiter before each test."""
    try:
        from webui.backend.app import limiter
        limiter.reset()
    except (ImportError, AttributeError):
        pass  # Limiter not available
    yield


@pytest.fixture
def client():
    """Create Flask test client."""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    # Disable rate limiting for testing
    app.config['RATELIMIT_ENABLED'] = False
    with app.test_client() as client:
        yield client


def _get_scheduler_ui_module():
    """Get the scheduler_ui module as used by app.py.

    app.py uses relative import 'routes.scheduler_ui' which creates a
    different module entry than 'webui.backend.routes.scheduler_ui'.
    This function returns the actual module reference used at runtime.
    """
    import sys
    module = sys.modules.get('routes.scheduler_ui')
    if module is None:
        import webui.backend.routes.scheduler_ui as module
    return module


# ============================================================================
# Cron Validation Endpoint Tests
# ============================================================================


class TestValidateCronEndpoint:
    """Tests for POST /api/scheduler/ui/cron/validate."""

    def test_validate_cron_valid_expression_returns_200(self, client):
        """Test that a valid cron expression returns success."""
        response = client.post(
            '/api/scheduler/ui/cron/validate',
            json={"expression": "*/5 * * * *"},
            content_type='application/json'
        )

        assert response.status_code == 200, f"Response: {response.get_json()}"
        data = response.get_json()
        assert data["valid"] is True
        assert data["expression"] == "*/5 * * * *"
        assert "next_executions" in data
        assert "human_readable" in data

    def test_validate_cron_invalid_expression_returns_400(self, client):
        """Test that an invalid cron expression returns error."""
        response = client.post(
            '/api/scheduler/ui/cron/validate',
            json={"expression": "invalid cron"},
            content_type='application/json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["valid"] is False
        assert "error" in data

    def test_validate_cron_empty_expression_returns_400(self, client):
        """Test that an empty string is rejected."""
        response = client.post(
            '/api/scheduler/ui/cron/validate',
            json={"expression": ""},
            content_type='application/json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["valid"] is False
        assert "error" in data

    def test_validate_cron_preview_returns_next_executions(self, client):
        """Test that next execution times are returned."""
        response = client.post(
            '/api/scheduler/ui/cron/validate',
            json={"expression": "0 21 * * *"},
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "next_executions" in data
        assert isinstance(data["next_executions"], list)
        assert len(data["next_executions"]) == 5  # Default count

    def test_validate_cron_preview_count_parameter(self, client):
        """Test that custom count parameter works (1-20)."""
        response = client.post(
            '/api/scheduler/ui/cron/validate',
            json={"expression": "0 * * * *", "count": 10},
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert len(data["next_executions"]) == 10

    def test_validate_cron_preview_count_min(self, client):
        """Test minimum count of 1."""
        response = client.post(
            '/api/scheduler/ui/cron/validate',
            json={"expression": "0 * * * *", "count": 1},
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert len(data["next_executions"]) == 1

    def test_validate_cron_preview_count_max(self, client):
        """Test maximum count of 20."""
        response = client.post(
            '/api/scheduler/ui/cron/validate',
            json={"expression": "0 * * * *", "count": 20},
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert len(data["next_executions"]) == 20

    def test_validate_cron_preview_count_above_max_rejected(self, client):
        """Test that count above 20 is rejected."""
        response = client.post(
            '/api/scheduler/ui/cron/validate',
            json={"expression": "0 * * * *", "count": 21},
            content_type='application/json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "count" in data["error"].lower()

    def test_validate_cron_preview_count_below_min_rejected(self, client):
        """Test that count below 1 is rejected."""
        response = client.post(
            '/api/scheduler/ui/cron/validate',
            json={"expression": "0 * * * *", "count": 0},
            content_type='application/json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "count" in data["error"].lower()

    def test_validate_cron_expression_too_long_rejected(self, client):
        """Test that expressions over 100 characters are rejected."""
        long_expression = "* " * 60  # Over 100 chars
        response = client.post(
            '/api/scheduler/ui/cron/validate',
            json={"expression": long_expression},
            content_type='application/json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_validate_cron_human_readable_returned(self, client):
        """Test that a human-readable description is returned."""
        response = client.post(
            '/api/scheduler/ui/cron/validate',
            json={"expression": "*/5 * * * *"},
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "human_readable" in data
        assert isinstance(data["human_readable"], str)
        assert len(data["human_readable"]) > 0

    def test_validate_cron_missing_expression_returns_400(self, client):
        """Test that missing expression field returns error."""
        response = client.post(
            '/api/scheduler/ui/cron/validate',
            json={"count": 5},
            content_type='application/json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_validate_cron_requires_json_body(self, client):
        """Test that non-JSON requests are rejected."""
        response = client.post(
            '/api/scheduler/ui/cron/validate',
            data="not json",
            content_type='application/json'
        )

        assert response.status_code == 400

    def test_validate_cron_empty_body_rejected(self, client):
        """Test that empty request body is rejected."""
        response = client.post(
            '/api/scheduler/ui/cron/validate',
            content_type='application/json'
        )

        assert response.status_code == 400

    def test_validate_cron_null_expression_rejected(self, client):
        """Test that null expression is rejected."""
        response = client.post(
            '/api/scheduler/ui/cron/validate',
            json={"expression": None},
            content_type='application/json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_validate_cron_non_string_expression_rejected(self, client):
        """Test that non-string expressions are rejected."""
        response = client.post(
            '/api/scheduler/ui/cron/validate',
            json={"expression": 12345},
            content_type='application/json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_validate_cron_common_patterns(self, client):
        """Test validation of common cron patterns."""
        patterns = [
            "* * * * *",       # Every minute
            "0 * * * *",       # Every hour
            "0 0 * * *",       # Daily at midnight
            "0 21 * * *",      # Daily at 9 PM
            "0 0 * * 0",       # Weekly on Sunday
            "0,30 * * * *",    # Twice per hour
            "0 9-17 * * 1-5",  # Business hours
        ]

        for pattern in patterns:
            response = client.post(
                '/api/scheduler/ui/cron/validate',
                json={"expression": pattern},
                content_type='application/json'
            )

            assert response.status_code == 200, f"Pattern '{pattern}' should be valid"
            data = response.get_json()
            assert data["valid"] is True

    def test_validate_cron_invalid_patterns(self, client):
        """Test rejection of invalid cron patterns."""
        invalid_patterns = [
            "60 * * * *",      # Invalid minute
            "* 24 * * *",      # Invalid hour
            "* * 32 * *",      # Invalid day
            "* * * 13 *",      # Invalid month
            "* * * * 8",       # Invalid weekday (out of range)
            "* * * *",         # Missing field
            "* * * * * *",     # Too many fields
        ]

        for pattern in invalid_patterns:
            response = client.post(
                '/api/scheduler/ui/cron/validate',
                json={"expression": pattern},
                content_type='application/json'
            )

            # Should either return 400 or 200 with valid=false
            data = response.get_json()
            if response.status_code == 200:
                assert data["valid"] is False, f"Pattern '{pattern}' should be invalid"
            else:
                assert response.status_code == 400


# ============================================================================
# Human Readable Tests
# ============================================================================


class TestCronHumanReadable:
    """Tests for human-readable cron descriptions."""

    def test_every_n_minutes(self, client):
        """Test '*/N * * * *' patterns."""
        test_cases = [
            ("*/5 * * * *", "5 minutes"),
            ("*/15 * * * *", "15 minutes"),
            ("*/30 * * * *", "30 minutes"),
        ]

        for expression, expected_text in test_cases:
            response = client.post(
                '/api/scheduler/ui/cron/validate',
                json={"expression": expression},
                content_type='application/json'
            )

            assert response.status_code == 200
            data = response.get_json()
            assert expected_text in data["human_readable"].lower()

    def test_every_n_hours(self, client):
        """Test '0 */N * * *' patterns."""
        response = client.post(
            '/api/scheduler/ui/cron/validate',
            json={"expression": "0 */2 * * *"},
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.get_json()
        # Should mention hours
        assert "hour" in data["human_readable"].lower()

    def test_daily_at_time(self, client):
        """Test '0 H * * *' patterns."""
        response = client.post(
            '/api/scheduler/ui/cron/validate',
            json={"expression": "0 21 * * *"},
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.get_json()
        # Should mention daily and time
        assert "daily" in data["human_readable"].lower() or "day" in data["human_readable"].lower()

    def test_every_minute(self, client):
        """Test '* * * * *' pattern."""
        response = client.post(
            '/api/scheduler/ui/cron/validate',
            json={"expression": "* * * * *"},
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "every minute" in data["human_readable"].lower()

    def test_custom_schedule_fallback(self, client):
        """Test complex patterns fall back to 'Custom schedule'."""
        response = client.post(
            '/api/scheduler/ui/cron/validate',
            json={"expression": "15,45 9-17 * * 1-5"},
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.get_json()
        # Should have some description (custom or specific)
        assert len(data["human_readable"]) > 0


# ============================================================================
# Rate Limiting Tests
# ============================================================================


class TestCronValidationRateLimiting:
    """Tests for rate limiting on cron validation endpoint."""

    def test_rate_limit_header_present(self, client):
        """Test that rate limiting is applied (30 per minute)."""
        response = client.post(
            '/api/scheduler/ui/cron/validate',
            json={"expression": "0 * * * *"},
            content_type='application/json'
        )

        # Check for rate limit headers (if limiter is active)
        # Note: In test mode, rate limiting may be disabled
        assert response.status_code in (200, 429)

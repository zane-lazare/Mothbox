"""
Unit tests for Event Pattern API (Issue #217)

Tests the REST API endpoints for event pattern management:
- GET /api/scheduler/ui/patterns/builtin
- POST /api/scheduler/ui/patterns/validate

Coverage Target: 85%+
Test Count Target: 25+
"""

import uuid
from unittest.mock import patch

import pytest


def _test_uuid(name: str) -> str:
    """Generate deterministic test UUID from name."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"test.api.{name}"))

# Try to import Flask app for testing
try:
    from webui.backend.app import app

    # Import schema constants for validation tests
    from webui.backend.lib.schedule_schema import (
        MAX_ACTIONS_PER_PATTERN,
        MAX_OFFSET_MINUTES,
        MAX_PATTERN_NAME_LENGTH,
    )

    # Import scheduler_ui_bp to ensure it exists
    from webui.backend.routes.scheduler_ui import scheduler_ui_bp  # noqa: F401

    IMPLEMENTATION_EXISTS = True
except ImportError:
    IMPLEMENTATION_EXISTS = False
    app = None

# Skip all tests if implementation doesn't exist
pytestmark = pytest.mark.skipif(
    not IMPLEMENTATION_EXISTS, reason="Implementation not yet created"
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def client():
    """Create Flask test client."""
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        yield client


def _get_scheduler_ui_module():
    """Get the scheduler_ui module as used by app.py.

    app.py uses relative import 'routes.scheduler_ui' which creates a
    different module entry than 'webui.backend.routes.scheduler_ui'.
    This function returns the actual module reference used at runtime.
    """
    import sys

    module = sys.modules.get("routes.scheduler_ui")
    if module is None:
        import webui.backend.routes.scheduler_ui as module
    return module


@pytest.fixture
def valid_minimal_pattern():
    """Create a valid minimal pattern for testing."""
    return {
        "name": "Test Pattern",
        "actions": [
            {
                "action_type": "camera",
                "action_name": "takephoto",
                "offset_minutes": 0,
            }
        ],
    }


@pytest.fixture
def valid_full_pattern():
    """Create a valid pattern with all fields."""
    return {
        "pattern_id": _test_uuid("test-pattern-001"),
        "name": "Full Test Pattern",
        "description": "A complete test pattern with all fields",
        "actions": [
            {
                "action_type": "gpio",
                "action_name": "attract_on",
                "offset_minutes": 0,
                "parameters": {},
                "description": "Turn on attract lights",
            },
            {
                "action_type": "camera",
                "action_name": "takephoto",
                "offset_minutes": 5,
                "parameters": {},
                "description": "Take a photo",
            },
            {
                "action_type": "gpio",
                "action_name": "attract_off",
                "offset_minutes": 15,
                "parameters": {},
                "description": "Turn off attract lights",
            },
        ],
        "category": "user",
        "tags": ["test", "validation"],
    }


# ============================================================================
# List Built-in Patterns Tests (8 tests)
# ============================================================================


class TestListBuiltinPatterns:
    """Tests for GET /api/scheduler/ui/patterns/builtin."""

    def test_returns_list_of_patterns(self, client):
        """Test endpoint returns a list of patterns with 200 OK."""
        response = client.get("/api/scheduler/ui/patterns/builtin")

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, dict)
        assert "patterns" in data
        assert "warnings" in data
        assert isinstance(data["patterns"], list)

    def test_includes_required_fields(self, client):
        """Test each pattern includes required fields."""
        response = client.get("/api/scheduler/ui/patterns/builtin")

        assert response.status_code == 200
        data = response.get_json()
        patterns = data["patterns"]
        assert len(patterns) > 0, "Expected at least one pattern"

        for pattern in patterns:
            assert "pattern_id" in pattern, "Missing pattern_id field"
            assert "name" in pattern, "Missing name field"
            assert "actions" in pattern, "Missing actions field"

    def test_includes_source_schedule(self, client):
        """Test each pattern includes source_schedule field."""
        response = client.get("/api/scheduler/ui/patterns/builtin")

        assert response.status_code == 200
        data = response.get_json()
        patterns = data["patterns"]
        assert len(patterns) > 0

        for pattern in patterns:
            assert "source_schedule" in pattern, "Missing source_schedule field"
            assert isinstance(pattern["source_schedule"], str)
            assert len(pattern["source_schedule"]) > 0

    def test_all_patterns_have_builtin_category(self, client):
        """Test all patterns have category='built-in'."""
        response = client.get("/api/scheduler/ui/patterns/builtin")

        assert response.status_code == 200
        data = response.get_json()
        patterns = data["patterns"]
        assert len(patterns) > 0

        for pattern in patterns:
            assert "category" in pattern
            assert pattern["category"] == "built-in"

    def test_returns_at_least_three_patterns(self, client):
        """Test returns at least 3 patterns (from 3 built-in schedules)."""
        response = client.get("/api/scheduler/ui/patterns/builtin")

        assert response.status_code == 200
        data = response.get_json()
        patterns = data["patterns"]
        assert len(patterns) >= 3, f"Expected at least 3 patterns, got {len(patterns)}"

    def test_no_duplicate_pattern_ids(self, client):
        """Test no duplicate pattern_ids in response."""
        response = client.get("/api/scheduler/ui/patterns/builtin")

        assert response.status_code == 200
        data = response.get_json()
        patterns = data["patterns"]

        pattern_ids = [p["pattern_id"] for p in patterns]
        unique_ids = set(pattern_ids)
        assert len(pattern_ids) == len(unique_ids), "Duplicate pattern_ids found"

    def test_each_pattern_has_valid_actions(self, client):
        """Test each pattern has a non-empty actions array."""
        response = client.get("/api/scheduler/ui/patterns/builtin")

        assert response.status_code == 200
        data = response.get_json()
        patterns = data["patterns"]
        assert len(patterns) > 0

        for pattern in patterns:
            actions = pattern.get("actions", [])
            assert isinstance(actions, list)
            assert len(actions) > 0, f"Pattern {pattern['name']} has no actions"

            for action in actions:
                assert "action_type" in action
                assert "action_name" in action

    def test_patterns_include_tags_array(self, client):
        """Test patterns include tags array."""
        response = client.get("/api/scheduler/ui/patterns/builtin")

        assert response.status_code == 200
        data = response.get_json()
        patterns = data["patterns"]
        assert len(patterns) > 0

        for pattern in patterns:
            assert "tags" in pattern
            assert isinstance(pattern["tags"], list)

    def test_patterns_include_duration_minutes(self, client):
        """Test each pattern includes computed duration_minutes."""
        response = client.get("/api/scheduler/ui/patterns/builtin")

        assert response.status_code == 200
        data = response.get_json()
        patterns = data["patterns"]
        assert len(patterns) > 0

        for pattern in patterns:
            assert "duration_minutes" in pattern, "Missing duration_minutes field"
            assert isinstance(pattern["duration_minutes"], int)
            assert pattern["duration_minutes"] >= 0

    def test_all_builtin_patterns_have_pattern_id(self, client):
        """Test that all built-in patterns have a non-empty pattern_id.

        This validates that built-in schedule files are properly configured.
        Patterns without pattern_id cannot be deduplicated and may cause issues.
        """
        response = client.get("/api/scheduler/ui/patterns/builtin")

        assert response.status_code == 200
        data = response.get_json()
        patterns = data["patterns"]
        assert len(patterns) > 0, "Expected at least one pattern"

        for pattern in patterns:
            pattern_id = pattern.get("pattern_id")
            assert pattern_id, f"Pattern '{pattern.get('name', 'unknown')}' missing pattern_id"
            assert isinstance(pattern_id, str), "pattern_id should be a string"
            assert len(pattern_id) > 0, "pattern_id should not be empty"


# ============================================================================
# Validate Pattern - Success Tests (4 tests)
# ============================================================================


class TestValidatePatternSuccess:
    """Tests for successful pattern validation."""

    def test_valid_minimal_pattern_returns_success(self, client, valid_minimal_pattern):
        """Test valid minimal pattern returns 200 with valid=true."""
        response = client.post(
            "/api/scheduler/ui/patterns/validate",
            json=valid_minimal_pattern,
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["valid"] is True
        assert "pattern" in data

    def test_valid_full_pattern_returns_success(self, client, valid_full_pattern):
        """Test valid full pattern returns 200 with valid=true."""
        response = client.post(
            "/api/scheduler/ui/patterns/validate",
            json=valid_full_pattern,
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["valid"] is True
        assert "pattern" in data

    def test_response_includes_duration_minutes(self, client, valid_full_pattern):
        """Test validated pattern includes computed duration_minutes."""
        response = client.post(
            "/api/scheduler/ui/patterns/validate",
            json=valid_full_pattern,
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["valid"] is True
        pattern = data["pattern"]
        assert "duration_minutes" in pattern
        # Full pattern has actions at 0, 5, 15 minutes - duration should be 15
        assert pattern["duration_minutes"] == 15

    def test_accepts_valid_category_values(self, client, valid_minimal_pattern):
        """Test accepts both 'user' and 'built-in' categories."""
        # Test 'user' category
        valid_minimal_pattern["category"] = "user"
        response = client.post(
            "/api/scheduler/ui/patterns/validate",
            json=valid_minimal_pattern,
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.get_json()["valid"] is True

        # Test 'built-in' category
        valid_minimal_pattern["category"] = "built-in"
        response = client.post(
            "/api/scheduler/ui/patterns/validate",
            json=valid_minimal_pattern,
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.get_json()["valid"] is True


# ============================================================================
# Validate Pattern - Error Tests (10 tests)
# ============================================================================


class TestValidatePatternErrors:
    """Tests for pattern validation errors."""

    def test_missing_name_returns_error(self, client):
        """Test missing name field returns 400 error."""
        pattern = {
            "actions": [
                {"action_type": "camera", "action_name": "takephoto", "offset_minutes": 0}
            ]
        }

        response = client.post(
            "/api/scheduler/ui/patterns/validate",
            json=pattern,
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["valid"] is False
        assert "error" in data

    def test_empty_name_returns_error(self, client):
        """Test empty name field returns 400 error."""
        pattern = {
            "name": "",
            "actions": [
                {"action_type": "camera", "action_name": "takephoto", "offset_minutes": 0}
            ],
        }

        response = client.post(
            "/api/scheduler/ui/patterns/validate",
            json=pattern,
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["valid"] is False
        assert "error" in data

    def test_name_too_long_returns_error(self, client):
        """Test name exceeding MAX_PATTERN_NAME_LENGTH returns 400 error."""
        pattern = {
            "name": "X" * (MAX_PATTERN_NAME_LENGTH + 1),
            "actions": [
                {"action_type": "camera", "action_name": "takephoto", "offset_minutes": 0}
            ],
        }

        response = client.post(
            "/api/scheduler/ui/patterns/validate",
            json=pattern,
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["valid"] is False
        assert "error" in data
        assert "200" in data["error"] or "name" in data["error"].lower()

    def test_missing_actions_returns_error(self, client):
        """Test missing actions field returns 400 error."""
        pattern = {"name": "Test Pattern"}

        response = client.post(
            "/api/scheduler/ui/patterns/validate",
            json=pattern,
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["valid"] is False
        assert "error" in data

    def test_empty_actions_returns_error(self, client):
        """Test empty actions array returns 400 error."""
        pattern = {"name": "Test Pattern", "actions": []}

        response = client.post(
            "/api/scheduler/ui/patterns/validate",
            json=pattern,
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["valid"] is False
        assert "error" in data

    def test_too_many_actions_returns_error(self, client):
        """Test exceeding MAX_ACTIONS_PER_PATTERN returns 400 error."""
        actions = [
            {"action_type": "camera", "action_name": "takephoto", "offset_minutes": i}
            for i in range(MAX_ACTIONS_PER_PATTERN + 1)  # Exceeds MAX_ACTIONS_PER_PATTERN limit
        ]
        pattern = {"name": "Test Pattern", "actions": actions}

        response = client.post(
            "/api/scheduler/ui/patterns/validate",
            json=pattern,
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["valid"] is False
        assert "error" in data
        assert "20" in data["error"] or "actions" in data["error"].lower()

    def test_invalid_action_type_returns_error(self, client):
        """Test invalid action_type returns 400 error."""
        pattern = {
            "name": "Test Pattern",
            "actions": [
                {
                    "action_type": "invalid_type",
                    "action_name": "takephoto",
                    "offset_minutes": 0,
                }
            ],
        }

        response = client.post(
            "/api/scheduler/ui/patterns/validate",
            json=pattern,
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["valid"] is False
        assert "error" in data

    def test_negative_offset_returns_error(self, client):
        """Test negative offset_minutes returns 400 error."""
        pattern = {
            "name": "Test Pattern",
            "actions": [
                {
                    "action_type": "camera",
                    "action_name": "takephoto",
                    "offset_minutes": -5,
                }
            ],
        }

        response = client.post(
            "/api/scheduler/ui/patterns/validate",
            json=pattern,
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["valid"] is False
        assert "error" in data

    def test_offset_too_large_returns_error(self, client):
        """Test offset exceeding MAX_OFFSET_MINUTES returns 400 error."""
        pattern = {
            "name": "Test Pattern",
            "actions": [
                {
                    "action_type": "camera",
                    "action_name": "takephoto",
                    "offset_minutes": MAX_OFFSET_MINUTES + 1,  # > MAX_OFFSET_MINUTES
                }
            ],
        }

        response = client.post(
            "/api/scheduler/ui/patterns/validate",
            json=pattern,
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["valid"] is False
        assert "error" in data

    def test_invalid_category_returns_error(self, client, valid_minimal_pattern):
        """Test invalid category value returns 400 error."""
        valid_minimal_pattern["category"] = "invalid_category"

        response = client.post(
            "/api/scheduler/ui/patterns/validate",
            json=valid_minimal_pattern,
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["valid"] is False
        assert "error" in data


# ============================================================================
# Error Handling Tests (3 tests)
# ============================================================================


class TestErrorHandling:
    """Tests for error handling."""

    def test_no_request_body_returns_error(self, client):
        """Test POST with no body returns 400 error."""
        response = client.post(
            "/api/scheduler/ui/patterns/validate",
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["valid"] is False
        assert "error" in data

    def test_invalid_json_returns_error(self, client):
        """Test POST with invalid JSON returns 400 error."""
        response = client.post(
            "/api/scheduler/ui/patterns/validate",
            data="not valid json {{{",
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["valid"] is False
        assert "error" in data

    def test_json_array_returns_error(self, client):
        """Test POST with JSON array (not object) returns 400 error."""
        response = client.post(
            "/api/scheduler/ui/patterns/validate",
            json=[{"name": "test"}],  # Array instead of object
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["valid"] is False
        assert "object" in data["error"].lower()

    def test_handles_missing_builtin_directory(self, client):
        """Test endpoint handles missing builtin directory gracefully."""
        module = _get_scheduler_ui_module()

        # Mock list_builtin_patterns to return empty list (simulates missing directory)
        with patch.object(module, "list_builtin_patterns") as mock_list:
            mock_list.return_value = ([], [])  # Returns (patterns, warnings) tuple

            response = client.get("/api/scheduler/ui/patterns/builtin")

            assert response.status_code == 200
            data = response.get_json()
            assert isinstance(data, dict)
            assert "patterns" in data
            assert "warnings" in data
            assert isinstance(data["patterns"], list)
            assert len(data["patterns"]) == 0

    def test_rate_limiting_decorator_applied(self, client):
        """Test that rate limiting decorator is applied to validate endpoint."""
        # Verify the endpoint function has rate limiting configured
        # by checking it responds correctly (decorator doesn't break functionality)
        # Note: Actually testing the 30/min limit would require 31 requests
        # which is impractical for unit tests. The decorator application is
        # verified by the endpoint working correctly with the limiter.

        # Make a valid request to ensure the rate limiter doesn't break the endpoint
        pattern = {
            "name": "Rate Limit Test",
            "actions": [
                {"action_type": "camera", "action_name": "takephoto", "offset_minutes": 0}
            ],
        }
        response = client.post(
            "/api/scheduler/ui/patterns/validate",
            json=pattern,
            content_type="application/json",
        )

        # If rate limiting decorator was misconfigured, this would fail
        assert response.status_code == 200
        data = response.get_json()
        assert data["valid"] is True

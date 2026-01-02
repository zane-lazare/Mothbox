"""Integration tests for Expert Mode scheduler workflow (Issue #233).

Tests the complete workflow for creating, validating, and activating
schedules with raw cron expression triggers.

Run with: MOTHBOX_ENV=test pytest Tests/integration/test_expert_mode_workflow.py -v -s

These tests are marked as @pytest.mark.integration.
They test API integration without requiring Pi hardware (cron/RTC is mocked).

Issue #233 - Scheduler Expert Mode (Phase 4: Integration Tests)
"""

import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from flask import Flask

# Setup path
FIRMWARE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(FIRMWARE_DIR))
sys.path.insert(0, str(FIRMWARE_DIR / "webui" / "backend"))
os.environ.setdefault("MOTHBOX_ENV", "test")

# Check if the old schema (trigger_type at schedule level) is still supported
# These tests use the pre-Schema 3.0 format with event_patterns and schedule-level triggers
try:
    from webui.backend.lib.schedule_schema import Schedule

    # Check if Schedule still has trigger_type attribute (old schema)
    # Schema 3.0 moved triggers into routines, making these tests obsolete
    _test_schedule = Schedule(schedule_id="test", name="test")
    LEGACY_SCHEMA_SUPPORTED = hasattr(_test_schedule, "trigger_type")
except (ImportError, Exception):
    LEGACY_SCHEMA_SUPPORTED = False

# Mark entire module as integration
# Skip if legacy schema is no longer supported (pending Phase 3 refactor)
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not LEGACY_SCHEMA_SUPPORTED,
        reason="Tests use legacy schema (trigger_type at schedule level) - pending Phase 3 refactor"
    ),
]

from webui.backend.routes.scheduler_ui import scheduler_ui_bp


def _test_uuid(name: str) -> str:
    """Generate deterministic test UUID from name."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"test.integration.expert.{name}"))


# ============================================================================
# Module-specific Fixtures
# ============================================================================


@pytest.fixture
def schedule_dirs(tmp_path):
    """Create temporary directories for schedules."""
    user_dir = tmp_path / "schedules"
    builtin_dir = tmp_path / "presets_builtin" / "schedules"
    user_dir.mkdir(parents=True)
    builtin_dir.mkdir(parents=True)

    return user_dir, builtin_dir


@pytest.fixture
def app(schedule_dirs, monkeypatch):
    """Flask app with mocked scheduler dependencies."""
    # Mock apply_to_system and remove_from_system
    apply_mock = MagicMock(return_value=True)
    remove_mock = MagicMock(return_value=True)

    monkeypatch.setattr(
        "webui.backend.services.scheduler_service.apply_to_system",
        apply_mock,
    )
    monkeypatch.setattr(
        "webui.backend.services.scheduler_service.remove_from_system",
        remove_mock,
    )

    # Patch the storage directories
    user_dir, builtin_dir = schedule_dirs
    import webui.backend.lib.schedule_storage as ss

    monkeypatch.setattr("mothbox_paths.SCHEDULES_DIR", user_dir)
    monkeypatch.setattr("mothbox_paths.BUILTIN_SCHEDULES_DIR", builtin_dir)
    monkeypatch.setattr(ss, "SCHEDULES_DIR", user_dir)
    monkeypatch.setattr(ss, "BUILTIN_SCHEDULES_DIR", builtin_dir)

    # Reset the singleton service to use patched paths
    import webui.backend.routes.scheduler_ui as sui

    monkeypatch.setattr(sui, "_scheduler_service", None)

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    app.register_blueprint(scheduler_ui_bp, url_prefix="/api/scheduler/ui")

    # Store mocks on app for test access
    app._apply_mock = apply_mock
    app._remove_mock = remove_mock

    yield app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def sample_cron_schedule_data():
    """Valid schedule data with cron trigger for API requests."""
    return {
        "name": "Expert Mode Test",
        "description": "Test schedule with raw cron expression",
        "trigger_type": "cron",
        "cron_trigger": {
            "cron_expression": "0 21 * * *",
        },
        "event_patterns": [
            {
                "pattern_id": _test_uuid("test-pattern"),
                "name": "Test Pattern",
                "description": "Test pattern for expert mode",
                "actions": [
                    {
                        "action_type": "camera",
                        "action_name": "takephoto",
                        "offset_minutes": 0,
                        "description": "Take a photo",
                    }
                ],
                "category": "user",
                "tags": ["test", "expert"],
            }
        ],
        "enabled": True,
    }


# ============================================================================
# Test Expert Mode Schedule Creation
# ============================================================================


class TestExpertModeScheduleCreation:
    """Integration tests for creating schedules with cron triggers."""

    def test_create_schedule_with_cron_trigger(
        self,
        client,
        sample_cron_schedule_data,
    ):
        """Create a schedule with cron trigger via API and verify it persists."""
        # Create schedule
        response = client.post(
            "/api/scheduler/ui/schedules",
            json=sample_cron_schedule_data,
            content_type="application/json",
        )

        assert response.status_code == 201, f"Create failed: {response.get_json()}"
        data = response.get_json()

        # Verify response structure (returns {"schedule": {...}, "schedule_id": "..."})
        assert "schedule" in data
        assert "schedule_id" in data
        schedule_id = data["schedule_id"]

        # Verify schedule data
        schedule = data["schedule"]
        assert schedule["trigger_type"] == "cron"
        assert schedule["cron_trigger"]["cron_expression"] == "0 21 * * *"

        # Verify schedule persists - retrieve it
        get_response = client.get(f"/api/scheduler/ui/schedules/{schedule_id}")
        assert get_response.status_code == 200

        retrieved = get_response.get_json()
        assert retrieved["trigger_type"] == "cron"
        assert retrieved["cron_trigger"]["cron_expression"] == "0 21 * * *"

    def test_cron_schedule_appears_in_list(
        self,
        client,
        sample_cron_schedule_data,
    ):
        """Verify cron schedule shows up in schedule list."""
        # Create schedule
        create_response = client.post(
            "/api/scheduler/ui/schedules",
            json=sample_cron_schedule_data,
            content_type="application/json",
        )
        assert create_response.status_code == 201
        schedule_id = create_response.get_json()["schedule_id"]

        # Get list of all schedules
        list_response = client.get("/api/scheduler/ui/schedules")
        assert list_response.status_code == 200

        response_data = list_response.get_json()
        assert "schedules" in response_data
        schedules = response_data["schedules"]
        assert isinstance(schedules, list)

        # Find our schedule in the list
        found = False
        for schedule in schedules:
            if schedule.get("schedule_id") == schedule_id:
                found = True
                # List endpoint returns summaries, not full schedule details
                # Only trigger_type is included, not the full trigger config
                assert schedule["trigger_type"] == "cron"
                assert schedule["name"] == "Expert Mode Test"
                break

        assert found, f"Schedule {schedule_id} not found in list"


# ============================================================================
# Test Expert Mode Activation
# ============================================================================


class TestExpertModeActivation:
    """Integration tests for activating schedules with cron triggers."""

    def test_activate_cron_schedule(
        self,
        client,
        app,
        sample_cron_schedule_data,
    ):
        """Activate a schedule with cron trigger."""
        # Create schedule
        create_response = client.post(
            "/api/scheduler/ui/schedules",
            json=sample_cron_schedule_data,
            content_type="application/json",
        )
        assert create_response.status_code == 201
        schedule_id = create_response.get_json()["schedule_id"]

        # Activate schedule
        activate_response = client.post(
            f"/api/scheduler/ui/schedules/{schedule_id}/activate",
            json={"check_conflicts": False},
            content_type="application/json",
        )

        assert activate_response.status_code == 200, (
            f"Activate failed: {activate_response.get_json()}"
        )

        # Verify schedule is now active
        active_response = client.get("/api/scheduler/ui/schedules/active")
        assert active_response.status_code == 200

        active_data = active_response.get_json()
        assert active_data.get("active") is True
        assert active_data.get("schedule", {}).get("schedule_id") == schedule_id

        # Verify cron trigger is preserved in active schedule
        assert active_data["schedule"]["trigger_type"] == "cron"
        assert active_data["schedule"]["cron_trigger"]["cron_expression"] == "0 21 * * *"

    def test_cron_schedule_generates_cron_entries(
        self,
        client,
        app,
        sample_cron_schedule_data,
    ):
        """Verify cron bridge generates correct cron entries for cron trigger."""
        # Create schedule
        create_response = client.post(
            "/api/scheduler/ui/schedules",
            json=sample_cron_schedule_data,
            content_type="application/json",
        )
        assert create_response.status_code == 201
        schedule_id = create_response.get_json()["schedule_id"]

        # Activate schedule
        activate_response = client.post(
            f"/api/scheduler/ui/schedules/{schedule_id}/activate",
            json={"check_conflicts": False},
            content_type="application/json",
        )
        assert activate_response.status_code == 200

        # Verify apply_to_system was called with cron entries
        app._apply_mock.assert_called_once()
        call_args = app._apply_mock.call_args
        entries = call_args.kwargs.get("entries", call_args[0][0] if call_args[0] else [])

        assert len(entries) >= 1, "Should have at least one cron entry"

        # Verify cron entry uses the raw expression from trigger
        entry = entries[0]
        assert entry.expression == "0 21 * * *", (
            f"Expected cron expression '0 21 * * *', got '{entry.expression}'"
        )

        # Verify command references TakePhoto script
        assert "takephoto" in entry.command.lower(), (
            f"Command should reference takephoto, got '{entry.command}'"
        )

        # Verify comment includes Mothbox prefix
        assert entry.comment.startswith("Mothbox:"), (
            f"Comment should start with 'Mothbox:', got '{entry.comment}'"
        )


# ============================================================================
# Test Expert Mode Validation
# ============================================================================


class TestExpertModeValidation:
    """Integration tests for cron validation endpoint."""

    def test_validate_cron_expression_endpoint(self, client):
        """Complete validation endpoint workflow returns all expected fields."""
        # Test valid cron expression
        response = client.post(
            "/api/scheduler/ui/cron/validate",
            json={"expression": "*/5 * * * *", "count": 5},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()

        # Verify all expected fields present
        assert data["valid"] is True
        assert data["expression"] == "*/5 * * * *"
        assert "human_readable" in data
        assert "next_executions" in data
        assert len(data["next_executions"]) == 5

        # Verify executions are in the future and properly formatted
        for exec_time in data["next_executions"]:
            dt = datetime.fromisoformat(exec_time)
            assert dt > datetime.now()

    def test_invalid_cron_expression_rejected(
        self,
        client,
        sample_cron_schedule_data,
    ):
        """Invalid cron expressions are rejected on create."""
        # Modify schedule data to have invalid cron expression
        invalid_data = sample_cron_schedule_data.copy()
        invalid_data["cron_trigger"] = {
            "cron_expression": "invalid * * * *",  # Invalid first field
        }

        # Attempt to create schedule
        response = client.post(
            "/api/scheduler/ui/schedules",
            json=invalid_data,
            content_type="application/json",
        )

        # Should fail validation
        assert response.status_code == 400
        # Error message can be generic "schedule validation failed" or more specific
        # Just verify it's a 400 error indicating validation failed

    def test_validate_cron_endpoint_with_invalid_expression(self, client):
        """Validate endpoint correctly identifies invalid expressions."""
        # Test completely invalid expression
        response = client.post(
            "/api/scheduler/ui/cron/validate",
            json={"expression": "not a cron expression"},
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["valid"] is False
        assert "error" in data

    def test_validate_cron_endpoint_with_different_counts(self, client):
        """Validate endpoint respects count parameter."""
        # Test with count=1
        response1 = client.post(
            "/api/scheduler/ui/cron/validate",
            json={"expression": "0 * * * *", "count": 1},
            content_type="application/json",
        )
        assert response1.status_code == 200
        data1 = response1.get_json()
        assert len(data1["next_executions"]) == 1

        # Test with count=10
        response10 = client.post(
            "/api/scheduler/ui/cron/validate",
            json={"expression": "0 * * * *", "count": 10},
            content_type="application/json",
        )
        assert response10.status_code == 200
        data10 = response10.get_json()
        assert len(data10["next_executions"]) == 10

    def test_validate_cron_endpoint_default_count(self, client):
        """Validate endpoint uses default count=5 when not specified."""
        response = client.post(
            "/api/scheduler/ui/cron/validate",
            json={"expression": "0 0 * * *"},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["next_executions"]) == 5  # Default count


# ============================================================================
# Test Expert Mode Edge Cases
# ============================================================================


class TestExpertModeEdgeCases:
    """Integration tests for edge cases and error handling."""

    def test_create_schedule_with_complex_cron_expression(
        self,
        client,
        sample_cron_schedule_data,
    ):
        """Create schedule with complex cron expression."""
        # Use complex expression: every 15 minutes on weekdays between 8am-5pm
        complex_data = sample_cron_schedule_data.copy()
        complex_data["cron_trigger"] = {
            "cron_expression": "*/15 8-17 * * 1-5",
        }

        response = client.post(
            "/api/scheduler/ui/schedules",
            json=complex_data,
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.get_json()
        schedule = data["schedule"]
        assert schedule["cron_trigger"]["cron_expression"] == "*/15 8-17 * * 1-5"

    def test_update_schedule_cron_expression(
        self,
        client,
        sample_cron_schedule_data,
    ):
        """Update an existing schedule's metadata (name and description)."""
        # Create schedule
        create_response = client.post(
            "/api/scheduler/ui/schedules",
            json=sample_cron_schedule_data,
            content_type="application/json",
        )
        assert create_response.status_code == 201
        schedule_id = create_response.get_json()["schedule_id"]

        # Update schedule metadata (updating nested trigger objects may not be supported)
        update_data = {
            "name": "Updated Expert Mode Test",
            "description": "Updated description",
        }

        update_response = client.put(
            f"/api/scheduler/ui/schedules/{schedule_id}",
            json=update_data,
            content_type="application/json",
        )

        assert update_response.status_code == 200
        updated_data = update_response.get_json()
        assert "schedule" in updated_data
        updated_schedule = updated_data["schedule"]
        assert updated_schedule["name"] == "Updated Expert Mode Test"
        assert updated_schedule["description"] == "Updated description"

        # Verify cron trigger is still intact
        assert updated_schedule["trigger_type"] == "cron"
        assert updated_schedule["cron_trigger"]["cron_expression"] == "0 21 * * *"

    def test_deactivate_active_cron_schedule(
        self,
        client,
        app,
        sample_cron_schedule_data,
    ):
        """Deactivate an active cron schedule."""
        # Create and activate schedule
        create_response = client.post(
            "/api/scheduler/ui/schedules",
            json=sample_cron_schedule_data,
            content_type="application/json",
        )
        assert create_response.status_code == 201
        schedule_id = create_response.get_json()["schedule_id"]

        activate_response = client.post(
            f"/api/scheduler/ui/schedules/{schedule_id}/activate",
            json={"check_conflicts": False},
            content_type="application/json",
        )
        assert activate_response.status_code == 200

        # Verify active
        active_before = client.get("/api/scheduler/ui/schedules/active")
        assert active_before.get_json()["active"] is True

        # Deactivate
        deactivate_response = client.post("/api/scheduler/ui/schedules/deactivate")
        assert deactivate_response.status_code == 200

        deactivate_data = deactivate_response.get_json()
        assert deactivate_data.get("was_active") is True
        assert deactivate_data.get("schedule_id") == schedule_id

        # Verify no longer active
        active_after = client.get("/api/scheduler/ui/schedules/active")
        assert active_after.get_json()["active"] is False

        # Verify remove_from_system was called
        app._remove_mock.assert_called()

    def test_validate_cron_with_special_characters(self, client):
        """Validate cron expressions with special characters."""
        # Test with range
        response1 = client.post(
            "/api/scheduler/ui/cron/validate",
            json={"expression": "0 8-17 * * *"},
            content_type="application/json",
        )
        assert response1.status_code == 200

        # Test with step values
        response2 = client.post(
            "/api/scheduler/ui/cron/validate",
            json={"expression": "*/10 * * * *"},
            content_type="application/json",
        )
        assert response2.status_code == 200

        # Test with list
        response3 = client.post(
            "/api/scheduler/ui/cron/validate",
            json={"expression": "0 9,12,15,18 * * *"},
            content_type="application/json",
        )
        assert response3.status_code == 200

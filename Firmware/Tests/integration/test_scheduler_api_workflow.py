"""Integration tests for Schedule Pattern API workflow (Issue #218).

Tests end-to-end API workflows including:
- Full lifecycle: create -> activate -> deactivate -> delete
- Built-in schedule protection (readonly)
- Activation replaces previous schedule
- Delete active schedule deactivates first
- Conflict detection before activation

Run with: MOTHBOX_ENV=test pytest Tests/integration/test_scheduler_api_workflow.py -v -s

These tests are marked as @pytest.mark.integration but NOT @pytest.mark.hardware
since they test multi-layer integration without requiring Pi hardware.

Issue #218 - Schedule Pattern API
"""

import os
import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from flask import Flask


def _test_uuid(name: str) -> str:
    """Generate deterministic test UUID from name."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"test.integration.api.{name}"))

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

# Setup path
FIRMWARE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(FIRMWARE_DIR))
sys.path.insert(0, str(FIRMWARE_DIR / "webui" / "backend"))
os.environ.setdefault("MOTHBOX_ENV", "test")

from webui.backend.routes.scheduler_ui import scheduler_ui_bp

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
def mock_scheduler_service(schedule_dirs):
    """Create a mock scheduler service with basic functionality."""
    user_dir, builtin_dir = schedule_dirs

    # Patch the storage directories in both mothbox_paths and schedule_storage
    import mothbox_paths
    import webui.backend.lib.schedule_storage as ss

    original_mp_user_dir = mothbox_paths.SCHEDULES_DIR
    original_mp_builtin_dir = mothbox_paths.BUILTIN_SCHEDULES_DIR
    original_ss_user_dir = ss.SCHEDULES_DIR
    original_ss_builtin_dir = ss.BUILTIN_SCHEDULES_DIR

    mothbox_paths.SCHEDULES_DIR = user_dir
    mothbox_paths.BUILTIN_SCHEDULES_DIR = builtin_dir
    ss.SCHEDULES_DIR = user_dir
    ss.BUILTIN_SCHEDULES_DIR = builtin_dir

    # Create real service with mocked cron functions
    from webui.backend.services.scheduler_service import SchedulerService

    service = SchedulerService(cache_ttl=60, max_cache_size=50)

    # Track mocks
    service._apply_mock = MagicMock(return_value=True)
    service._remove_mock = MagicMock(return_value=True)

    yield service

    # Restore original directories
    mothbox_paths.SCHEDULES_DIR = original_mp_user_dir
    mothbox_paths.BUILTIN_SCHEDULES_DIR = original_mp_builtin_dir
    ss.SCHEDULES_DIR = original_ss_user_dir
    ss.BUILTIN_SCHEDULES_DIR = original_ss_builtin_dir


@pytest.fixture
def app(mock_scheduler_service, schedule_dirs, monkeypatch):
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

    # Patch the storage directories in both mothbox_paths and schedule_storage
    user_dir, builtin_dir = schedule_dirs
    import webui.backend.lib.schedule_storage as ss

    monkeypatch.setattr('mothbox_paths.SCHEDULES_DIR', user_dir)
    monkeypatch.setattr('mothbox_paths.BUILTIN_SCHEDULES_DIR', builtin_dir)
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
def sample_schedule_data():
    """Valid schedule data for API requests."""
    return {
        "name": "Test Schedule",
        "description": "Integration test schedule",
        "trigger_type": "fixed_time",
        "fixed_time_trigger": {
            "time": "21:00",
            "days_of_week": [0, 1, 2, 3, 4, 5, 6],
        },
        "event_patterns": [
            {
                "pattern_id": _test_uuid("test-pattern"),
                "name": "Test Pattern",
                "description": "Test pattern for integration tests",
                "actions": [
                    {
                        "action_type": "camera",
                        "action_name": "takephoto",
                        "offset_minutes": 0,
                        "description": "Take a photo",
                    }
                ],
                "category": "user",
                "tags": ["test"],
            }
        ],
        "enabled": True,
    }


# ============================================================================
# Test Full Lifecycle Workflow
# ============================================================================


class TestScheduleLifecycleWorkflow:
    """End-to-end tests for schedule lifecycle via API."""

    def test_full_lifecycle_create_activate_deactivate_delete(
        self,
        client,
        sample_schedule_data,
    ):
        """Full lifecycle: create -> activate -> deactivate -> delete."""
        # 1. Create schedule
        create_response = client.post(
            "/api/scheduler/ui/schedules",
            json=sample_schedule_data,
            content_type="application/json",
        )
        assert create_response.status_code == 201, (
            f"Create failed: {create_response.get_json()}"
        )

        data = create_response.get_json()
        schedule_id = data.get("schedule_id")
        assert schedule_id is not None, "Create should return schedule_id"

        # 2. Verify schedule exists
        get_response = client.get(f"/api/scheduler/ui/schedules/{schedule_id}")
        assert get_response.status_code == 200, "Schedule should exist"

        # 3. Activate schedule
        activate_response = client.post(
            f"/api/scheduler/ui/schedules/{schedule_id}/activate",
            json={"check_conflicts": False},
            content_type="application/json",
        )
        assert activate_response.status_code == 200, (
            f"Activate failed: {activate_response.get_json()}"
        )

        # 4. Verify schedule is active
        active_response = client.get("/api/scheduler/ui/schedules/active")
        assert active_response.status_code == 200
        active_data = active_response.get_json()
        assert active_data.get("active") is True
        assert active_data.get("schedule", {}).get("schedule_id") == schedule_id

        # 5. Deactivate schedule
        deactivate_response = client.post("/api/scheduler/ui/schedules/deactivate")
        assert deactivate_response.status_code == 200
        deactivate_data = deactivate_response.get_json()
        assert deactivate_data.get("was_active") is True
        assert deactivate_data.get("schedule_id") == schedule_id

        # 6. Verify no active schedule
        active_response2 = client.get("/api/scheduler/ui/schedules/active")
        assert active_response2.status_code == 200
        assert active_response2.get_json().get("active") is False

        # 7. Delete schedule
        delete_response = client.delete(f"/api/scheduler/ui/schedules/{schedule_id}")
        assert delete_response.status_code == 200

        # 8. Verify schedule is gone
        get_response2 = client.get(f"/api/scheduler/ui/schedules/{schedule_id}")
        assert get_response2.status_code == 404


# ============================================================================
# Test Built-in Schedule Protection
# ============================================================================


class TestBuiltinScheduleProtection:
    """Tests for built-in schedule readonly protection."""

    def test_builtin_schedule_cannot_be_updated(
        self,
        client,
        schedule_dirs,
    ):
        """Verify built-in schedules cannot be modified."""
        import json

        from webui.backend.lib.schedule_schema import (
            EventPattern,
            FixedTimeTrigger,
            Action,
            Schedule,
        )

        user_dir, builtin_dir = schedule_dirs

        # Create a built-in schedule directly in storage
        builtin_id = _test_uuid("builtin-test-readonly")

        action = Action(
            action_type="camera",
            action_name="takephoto",
            offset_minutes=0,
            description="Test action",
        )

        pattern = EventPattern(
            pattern_id=_test_uuid("builtin-pattern"),
            name="Built-in Pattern",
            description="A built-in pattern",
            actions=[action],
            category="built-in",
            tags=["builtin"],
        )

        trigger = FixedTimeTrigger(time="21:00")

        schedule = Schedule(
            schedule_id=builtin_id,
            name="Built-in Test Schedule",
            description="A built-in schedule for testing",
            event_patterns=[pattern],
            trigger_type="fixed_time",
            fixed_time_trigger=trigger,
            enabled=True,
            is_active=False,
        )

        # Write directly to builtin directory
        schedule_file = builtin_dir / f"{builtin_id}.json"
        schedule_file.write_text(json.dumps(schedule.to_dict()))

        # Attempt to update should fail with 403
        update_response = client.put(
            f"/api/scheduler/ui/schedules/{builtin_id}",
            json={"name": "Modified Name"},
            content_type="application/json",
        )
        assert update_response.status_code == 403, (
            f"Update built-in should return 403, got {update_response.status_code}"
        )

    def test_builtin_schedule_cannot_be_deleted(
        self,
        client,
        schedule_dirs,
    ):
        """Verify built-in schedules cannot be deleted."""
        import json

        from webui.backend.lib.schedule_schema import (
            EventPattern,
            FixedTimeTrigger,
            Action,
            Schedule,
        )

        user_dir, builtin_dir = schedule_dirs

        # Create a built-in schedule
        builtin_id = _test_uuid("builtin-test-nodelete")

        action = Action(
            action_type="camera",
            action_name="takephoto",
            offset_minutes=0,
            description="Test action",
        )

        pattern = EventPattern(
            pattern_id=_test_uuid("builtin-pattern-2"),
            name="Built-in Pattern",
            description="A built-in pattern",
            actions=[action],
            category="built-in",
            tags=["builtin"],
        )

        trigger = FixedTimeTrigger(time="21:00")

        schedule = Schedule(
            schedule_id=builtin_id,
            name="Built-in No Delete Test",
            description="A built-in schedule for delete testing",
            event_patterns=[pattern],
            trigger_type="fixed_time",
            fixed_time_trigger=trigger,
            enabled=True,
            is_active=False,
        )

        # Write directly to builtin directory
        schedule_file = builtin_dir / f"{builtin_id}.json"
        schedule_file.write_text(json.dumps(schedule.to_dict()))

        # Attempt to delete should fail with 403
        delete_response = client.delete(f"/api/scheduler/ui/schedules/{builtin_id}")
        assert delete_response.status_code == 403, (
            f"Delete built-in should return 403, got {delete_response.status_code}"
        )


# ============================================================================
# Test Activation Workflow
# ============================================================================


class TestActivationWorkflow:
    """Tests for schedule activation behavior."""

    def test_activation_replaces_previous_schedule(
        self,
        client,
        app,
        sample_schedule_data,
    ):
        """New activation deactivates previous schedule."""
        # Create first schedule
        data1 = {**sample_schedule_data, "name": "First Schedule"}
        create1 = client.post(
            "/api/scheduler/ui/schedules",
            json=data1,
            content_type="application/json",
        )
        schedule_id_1 = create1.get_json().get("schedule_id")

        # Create second schedule
        data2 = {**sample_schedule_data, "name": "Second Schedule"}
        create2 = client.post(
            "/api/scheduler/ui/schedules",
            json=data2,
            content_type="application/json",
        )
        schedule_id_2 = create2.get_json().get("schedule_id")

        # Activate first schedule
        activate1 = client.post(
            f"/api/scheduler/ui/schedules/{schedule_id_1}/activate",
            json={"check_conflicts": False},
            content_type="application/json",
        )
        assert activate1.status_code == 200

        # Verify first is active
        active1 = client.get("/api/scheduler/ui/schedules/active")
        assert active1.get_json().get("schedule", {}).get("schedule_id") == schedule_id_1

        # Reset mock to track new activation
        app._remove_mock.reset_mock()

        # Activate second schedule
        activate2 = client.post(
            f"/api/scheduler/ui/schedules/{schedule_id_2}/activate",
            json={"check_conflicts": False},
            content_type="application/json",
        )
        assert activate2.status_code == 200

        # Verify second is now active (first was replaced)
        active2 = client.get("/api/scheduler/ui/schedules/active")
        assert active2.get_json().get("schedule", {}).get("schedule_id") == schedule_id_2

        # Verify remove_from_system was called (to remove first schedule's cron)
        app._remove_mock.assert_called()

    def test_delete_active_schedule_deactivates(
        self,
        client,
        app,
        sample_schedule_data,
    ):
        """Deleting active schedule marks it as no longer active."""
        # Create and activate schedule
        create_response = client.post(
            "/api/scheduler/ui/schedules",
            json=sample_schedule_data,
            content_type="application/json",
        )
        schedule_id = create_response.get_json().get("schedule_id")

        activate = client.post(
            f"/api/scheduler/ui/schedules/{schedule_id}/activate",
            json={"check_conflicts": False},
            content_type="application/json",
        )
        assert activate.status_code == 200

        # Verify active
        active_before = client.get("/api/scheduler/ui/schedules/active")
        assert active_before.get_json().get("active") is True

        # Delete the active schedule
        delete_response = client.delete(f"/api/scheduler/ui/schedules/{schedule_id}")
        assert delete_response.status_code == 200

        # Verify no longer active - the key assertion
        active_after = client.get("/api/scheduler/ui/schedules/active")
        assert active_after.get_json().get("active") is False

        # Verify schedule is gone
        get_response = client.get(f"/api/scheduler/ui/schedules/{schedule_id}")
        assert get_response.status_code == 404


# ============================================================================
# Test Validation and Conflicts
# ============================================================================


class TestValidationAndConflicts:
    """Tests for schedule validation and conflict detection."""

    def test_validation_without_activation(
        self,
        client,
        sample_schedule_data,
    ):
        """Validate endpoint checks schedule without activating."""
        # Create schedule
        create_response = client.post(
            "/api/scheduler/ui/schedules",
            json=sample_schedule_data,
            content_type="application/json",
        )
        schedule_id = create_response.get_json().get("schedule_id")

        # Validate without activating
        validate_response = client.post(
            f"/api/scheduler/ui/schedules/{schedule_id}/validate",
            json={"days": 7},
            content_type="application/json",
        )
        assert validate_response.status_code == 200

        data = validate_response.get_json()
        assert "valid" in data
        assert "schedule_id" in data
        assert data.get("schedule_id") == schedule_id

        # Verify schedule is NOT active (validation doesn't activate)
        active_response = client.get("/api/scheduler/ui/schedules/active")
        assert active_response.get_json().get("active") is False


# ============================================================================
# Test Activation Input Validation
# ============================================================================


class TestActivationInputValidation:
    """Tests for coordinate and timezone validation on activation."""

    def test_activate_with_invalid_latitude(self, client, sample_schedule_data):
        """Activation with latitude > 90 should fail."""
        # Create schedule first
        create_response = client.post(
            "/api/scheduler/ui/schedules",
            json=sample_schedule_data,
            content_type="application/json",
        )
        assert create_response.status_code == 201
        schedule_id = create_response.get_json()["schedule_id"]

        # Activate with invalid latitude (> 90)
        response = client.post(
            f"/api/scheduler/ui/schedules/{schedule_id}/activate",
            json={"latitude": 95.0, "longitude": 0.0},
            content_type="application/json",
        )
        assert response.status_code == 400
        error_msg = response.get_json()["error"].lower()
        assert "latitude" in error_msg or "coordinate" in error_msg

    def test_activate_with_invalid_longitude(self, client, sample_schedule_data):
        """Activation with longitude < -180 should fail."""
        # Create schedule first
        create_response = client.post(
            "/api/scheduler/ui/schedules",
            json=sample_schedule_data,
            content_type="application/json",
        )
        assert create_response.status_code == 201
        schedule_id = create_response.get_json()["schedule_id"]

        # Activate with invalid longitude (< -180)
        response = client.post(
            f"/api/scheduler/ui/schedules/{schedule_id}/activate",
            json={"latitude": 0.0, "longitude": -200.0},
            content_type="application/json",
        )
        assert response.status_code == 400
        error_msg = response.get_json()["error"].lower()
        assert "longitude" in error_msg or "coordinate" in error_msg

    def test_activate_with_invalid_timezone(self, client, sample_schedule_data):
        """Activation with invalid timezone should fail."""
        # Create schedule first
        create_response = client.post(
            "/api/scheduler/ui/schedules",
            json=sample_schedule_data,
            content_type="application/json",
        )
        assert create_response.status_code == 201
        schedule_id = create_response.get_json()["schedule_id"]

        # Activate with invalid timezone
        response = client.post(
            f"/api/scheduler/ui/schedules/{schedule_id}/activate",
            json={"timezone": "Not/A/Valid/Timezone"},
            content_type="application/json",
        )
        assert response.status_code == 400
        error_msg = response.get_json()["error"].lower()
        assert "timezone" in error_msg

    def test_activate_with_valid_coordinates_and_timezone(self, client, app, sample_schedule_data):
        """Activation with valid coordinates and timezone should succeed."""
        # Create schedule first
        create_response = client.post(
            "/api/scheduler/ui/schedules",
            json=sample_schedule_data,
            content_type="application/json",
        )
        assert create_response.status_code == 201
        schedule_id = create_response.get_json()["schedule_id"]

        # Activate with valid coordinates and timezone
        response = client.post(
            f"/api/scheduler/ui/schedules/{schedule_id}/activate",
            json={
                "latitude": 35.0,
                "longitude": -80.0,
                "timezone": "America/New_York",
                "check_conflicts": False,
            },
            content_type="application/json",
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.get_json()}"

    def test_activate_with_default_coordinates_succeeds(self, client, app, sample_schedule_data):
        """Activation with default coordinates (0.0, 0.0) should succeed."""
        # Create schedule first
        create_response = client.post(
            "/api/scheduler/ui/schedules",
            json=sample_schedule_data,
            content_type="application/json",
        )
        assert create_response.status_code == 201
        schedule_id = create_response.get_json()["schedule_id"]

        # Activate with default coordinates (empty body)
        response = client.post(
            f"/api/scheduler/ui/schedules/{schedule_id}/activate",
            json={"check_conflicts": False},
            content_type="application/json",
        )
        assert response.status_code == 200

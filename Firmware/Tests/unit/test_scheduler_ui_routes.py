"""
Unit tests for Scheduler UI API Routes (Issues #214, #218)

Tests the REST API endpoints for schedule preview and management.

Coverage Target: 85%+

Issue #214 - Schedule Preview
Issue #218 - Schedule Pattern API
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
pytestmark = pytest.mark.skipif(not IMPLEMENTATION_EXISTS, reason="Implementation not yet created")


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def reset_scheduler_service():
    """Reset the scheduler service singleton before each test.

    Note: app.py uses relative import 'routes.scheduler_ui' which creates a
    different module object than 'webui.backend.routes.scheduler_ui'. We need
    to patch both to handle all cases.
    """
    import sys

    # Get the module that app.py actually uses (relative import creates this)
    module = sys.modules.get("routes.scheduler_ui")
    if module is None:
        # Fallback to full path if relative import module not found
        import webui.backend.routes.scheduler_ui as module

    original = getattr(module, "_scheduler_service", None)
    module._scheduler_service = None
    yield
    module._scheduler_service = original


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
def mock_scheduler_service():
    """Mock SchedulerService by directly setting the module variable.

    Uses sys.modules to find the actual module reference used by app.py's
    relative import pattern.
    """
    module = _get_scheduler_ui_module()
    mock_service = MagicMock()
    module._scheduler_service = mock_service
    yield mock_service


@pytest.fixture
def schedule_factory():
    """
    Factory fixture for creating mock schedule objects.

    Usage:
        schedule = schedule_factory()  # defaults
        schedule = schedule_factory(name="Custom", is_active=True)
        schedule = schedule_factory(routine_count=3)  # creates 3 mock routines
    """

    def _create_schedule(**overrides):
        # Handle routine_count specially
        routine_count = overrides.pop("routine_count", 1)
        routines = [MagicMock() for _ in range(routine_count)]

        defaults = {
            "schedule_id": "test-schedule",
            "name": "Test Schedule",
            "description": "A test schedule",
            "routines": routines,
            "enabled": True,
            "is_active": False,
            "created_at": "2025-06-15T00:00:00Z",
            "modified_at": "2025-06-15T00:00:00Z",
        }
        defaults.update(overrides)

        schedule = MagicMock()
        for key, value in defaults.items():
            setattr(schedule, key, value)

        # Default to_dict returns basic structure
        schedule.to_dict.return_value = {
            "schedule_id": defaults["schedule_id"],
            "name": defaults["name"],
            "routines": [{"name": "Test Routine"}] * routine_count,
        }
        return schedule

    return _create_schedule


@pytest.fixture
def sample_schedule(schedule_factory):
    """Create a mock schedule object (uses schedule_factory)."""
    return schedule_factory()


@pytest.fixture
def mock_preview_result():
    """Create a mock PreviewResult."""
    result = MagicMock()
    result.to_dict.return_value = {
        "schedule_id": "test-schedule",
        "schedule_name": "Test Schedule",
        "preview_start": "2025-06-15T00:00:00Z",
        "preview_end": "2025-06-21T23:59:59Z",
        "executions": [],
        "conflicts": [],
        "moon_phases": {},
        "total_actions": 0,
        "total_executions": 0,
        "generated_at": "2025-06-15T12:00:00Z",
    }
    return result


@pytest.fixture
def valid_schedule_payload():
    """Valid schedule JSON for POST/PUT tests (Schema 3.0)."""
    return {
        "name": "Test Schedule",
        "description": "A test schedule",
        "routines": [
            {
                "name": "Simple Capture",
                "trigger": {
                    "trigger_type": "fixed_time",
                    "time": "21:00",
                    "days_of_week": [0, 1, 2, 3, 4, 5, 6],
                },
                "actions": [
                    {
                        "action_type": "camera",
                        "action_name": "takephoto",
                        "offset_minutes": 0,
                    }
                ],
            }
        ],
    }


# ============================================================================
# Preview Endpoint Tests
# ============================================================================


class TestSchedulePreviewEndpoint:
    """Tests for GET /api/scheduler/ui/schedules/{id}/preview."""

    def test_preview_success(self, client, mock_scheduler_service, mock_preview_result):
        """Test successful preview generation."""
        # Configure mock to return a schedule
        schedule = MagicMock()
        schedule.schedule_id = "test-schedule"
        schedule.name = "Test Schedule"
        mock_scheduler_service.get_schedule.return_value = schedule

        module = _get_scheduler_ui_module()
        with patch.object(module, "generate_preview") as mock_gen:
            mock_gen.return_value = mock_preview_result

            response = client.get("/api/scheduler/ui/schedules/test-schedule/preview")

            assert response.status_code == 200, f"Response: {response.get_json()}"
            data = response.get_json()
            assert data["schedule_id"] == "test-schedule"
            assert "executions" in data
            assert "moon_phases" in data

    def test_preview_with_custom_days(self, client, mock_scheduler_service, mock_preview_result):
        """Test preview with custom days parameter."""
        schedule = MagicMock()
        mock_scheduler_service.get_schedule.return_value = schedule

        module = _get_scheduler_ui_module()
        with patch.object(module, "generate_preview") as mock_gen:
            mock_gen.return_value = mock_preview_result

            response = client.get("/api/scheduler/ui/schedules/test-schedule/preview?days=14")

            assert response.status_code == 200
            mock_gen.assert_called_once()
            call_kwargs = mock_gen.call_args.kwargs
            assert call_kwargs["days"] == 14

    def test_preview_with_coordinates(self, client, mock_scheduler_service, mock_preview_result):
        """Test preview with lat/lon parameters."""
        schedule = MagicMock()
        mock_scheduler_service.get_schedule.return_value = schedule

        module = _get_scheduler_ui_module()
        with patch.object(module, "generate_preview") as mock_gen:
            mock_gen.return_value = mock_preview_result

            response = client.get(
                "/api/scheduler/ui/schedules/test-schedule/preview?lat=35.0&lon=-80.0"
            )

            assert response.status_code == 200
            call_kwargs = mock_gen.call_args.kwargs
            assert call_kwargs["latitude"] == 35.0
            assert call_kwargs["longitude"] == -80.0

    def test_preview_schedule_not_found(self, client, mock_scheduler_service):
        """Test preview with non-existent schedule."""
        mock_scheduler_service.get_schedule.return_value = None

        response = client.get("/api/scheduler/ui/schedules/nonexistent/preview")

        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
        assert "not found" in data["error"].lower()

    def test_preview_invalid_days_not_integer(self, client):
        """Test preview with non-integer days."""
        response = client.get("/api/scheduler/ui/schedules/test/preview?days=abc")

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "days" in data["error"].lower()

    def test_preview_invalid_days_below_min(self, client):
        """Test preview with days below minimum."""
        response = client.get("/api/scheduler/ui/schedules/test/preview?days=0")

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_preview_invalid_days_above_max(self, client):
        """Test preview with days above maximum."""
        response = client.get("/api/scheduler/ui/schedules/test/preview?days=100")

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_preview_invalid_latitude(self, client):
        """Test preview with invalid latitude."""
        response = client.get("/api/scheduler/ui/schedules/test/preview?lat=100")

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "coordinates" in data["error"].lower()

    def test_preview_invalid_longitude(self, client):
        """Test preview with invalid longitude."""
        response = client.get("/api/scheduler/ui/schedules/test/preview?lon=200")

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "coordinates" in data["error"].lower()

    def test_preview_invalid_lat_format(self, client):
        """Test preview with non-numeric latitude."""
        response = client.get("/api/scheduler/ui/schedules/test/preview?lat=abc")

        assert response.status_code == 400
        data = response.get_json()
        assert "lat" in data["error"].lower()

    def test_preview_invalid_timezone(self, client):
        """Test preview with invalid timezone name."""
        response = client.get("/api/scheduler/ui/schedules/test/preview?tz=Invalid/Timezone")

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "timezone" in data["error"].lower()

    def test_preview_empty_timezone(self, client):
        """Test preview with empty timezone."""
        response = client.get("/api/scheduler/ui/schedules/test/preview?tz=")

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "timezone" in data["error"].lower()


# ============================================================================
# List Schedules Endpoint Tests
# ============================================================================


class TestListSchedulesEndpoint:
    """Tests for GET /api/scheduler/ui/schedules."""

    def test_list_schedules_empty(self, client, mock_scheduler_service):
        """Test listing with no schedules."""
        mock_scheduler_service.list_schedules.return_value = []

        response = client.get("/api/scheduler/ui/schedules")

        assert response.status_code == 200
        data = response.get_json()
        assert data["schedules"] == []
        assert data["total"] == 0

    def test_list_schedules_with_data(self, client, mock_scheduler_service, schedule_factory):
        """Test listing with schedules."""
        schedule = schedule_factory(routine_count=2)
        mock_scheduler_service.list_schedules.return_value = [schedule]

        response = client.get("/api/scheduler/ui/schedules")

        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 1
        assert len(data["schedules"]) == 1
        assert data["schedules"][0]["schedule_id"] == "test-schedule"
        assert data["schedules"][0]["routine_count"] == 2

    def test_list_schedules_include_builtin(self, client, mock_scheduler_service):
        """Test include_builtin parameter."""
        mock_scheduler_service.list_schedules.return_value = []

        response = client.get("/api/scheduler/ui/schedules?include_builtin=true")

        assert response.status_code == 200
        mock_scheduler_service.list_schedules.assert_called_with(include_builtin=True)

    def test_list_schedules_active_only(self, client, mock_scheduler_service, schedule_factory):
        """Test active_only filter."""
        # One active, one inactive
        active_schedule = schedule_factory(
            schedule_id="active", name="Active", description="", is_active=True
        )
        inactive_schedule = schedule_factory(
            schedule_id="inactive", name="Inactive", description="", is_active=False
        )

        mock_scheduler_service.list_schedules.return_value = [inactive_schedule, active_schedule]

        response = client.get("/api/scheduler/ui/schedules?active_only=true")

        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 1
        assert data["schedules"][0]["schedule_id"] == "active"


# ============================================================================
# Get Schedule Endpoint Tests
# ============================================================================


class TestGetScheduleEndpoint:
    """Tests for GET /api/scheduler/ui/schedules/{id}."""

    def test_get_schedule_success(self, client, mock_scheduler_service):
        """Test successful schedule retrieval."""
        schedule = MagicMock()
        schedule.to_dict.return_value = {
            "schedule_id": "test-schedule",
            "name": "Test Schedule",
        }
        mock_scheduler_service.get_schedule.return_value = schedule

        response = client.get("/api/scheduler/ui/schedules/test-schedule")

        assert response.status_code == 200
        data = response.get_json()
        assert data["schedule_id"] == "test-schedule"

    def test_get_schedule_not_found(self, client, mock_scheduler_service):
        """Test schedule not found."""
        mock_scheduler_service.get_schedule.return_value = None

        response = client.get("/api/scheduler/ui/schedules/nonexistent")

        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
        assert "not found" in data["error"].lower()


# ============================================================================
# Get Active Schedule Endpoint Tests (Issue #218)
# ============================================================================


class TestGetActiveScheduleEndpoint:
    """Tests for GET /api/scheduler/ui/schedules/active."""

    def test_get_active_schedule_none(self, client, mock_scheduler_service):
        """Test when no schedule is active."""
        mock_scheduler_service.get_active_schedule.return_value = None
        mock_scheduler_service.get_active_coordinates_source.return_value = None
        mock_scheduler_service.get_active_coordinates.return_value = None
        mock_scheduler_service.get_active_timezone_name.return_value = None

        response = client.get("/api/scheduler/ui/schedules/active")

        assert response.status_code == 200
        data = response.get_json()
        assert data["active_schedule"] is None
        assert data["coordinates_source"] is None
        assert data["latitude"] is None
        assert data["longitude"] is None
        assert data["timezone_name"] is None

    def test_get_active_schedule_exists(self, client, mock_scheduler_service, sample_schedule):
        """Test when a schedule is active."""
        sample_schedule.to_dict.return_value = {
            "schedule_id": "test-schedule",
            "name": "Test Schedule",
            "enabled": True,
            "is_active": True,
        }
        mock_scheduler_service.get_active_schedule.return_value = sample_schedule
        mock_scheduler_service.get_active_coordinates_source.return_value = "gps"
        mock_scheduler_service.get_active_coordinates.return_value = (-36.848, 174.763)
        mock_scheduler_service.get_active_timezone_name.return_value = None

        response = client.get("/api/scheduler/ui/schedules/active")

        assert response.status_code == 200
        data = response.get_json()
        assert data["active_schedule"] is not None
        assert data["active_schedule"]["schedule_id"] == "test-schedule"
        assert data["coordinates_source"] == "gps"
        assert data["latitude"] == -36.848
        assert data["longitude"] == 174.763
        assert data["timezone_name"] is None

    def test_get_active_schedule_full_object(self, client, mock_scheduler_service, sample_schedule):
        """Test that full schedule object is returned."""
        sample_schedule.to_dict.return_value = {
            "schedule_id": "test-schedule",
            "name": "Test Schedule",
            "routines": [{"name": "Test Routine"}],
            "enabled": True,
            "is_active": True,
        }
        mock_scheduler_service.get_active_schedule.return_value = sample_schedule
        mock_scheduler_service.get_active_coordinates_source.return_value = "timezone"
        mock_scheduler_service.get_active_coordinates.return_value = (-41.286, 174.776)
        mock_scheduler_service.get_active_timezone_name.return_value = "Pacific/Auckland"

        response = client.get("/api/scheduler/ui/schedules/active")

        assert response.status_code == 200
        data = response.get_json()
        assert "routines" in data["active_schedule"]
        assert "enabled" in data["active_schedule"]
        assert data["coordinates_source"] == "timezone"
        assert data["timezone_name"] == "Pacific/Auckland"

    def test_get_active_schedule_error(self, client, mock_scheduler_service):
        """Test error handling."""
        mock_scheduler_service.get_active_schedule.side_effect = Exception("DB error")

        response = client.get("/api/scheduler/ui/schedules/active")

        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data


# ============================================================================
# List Built-in Schedules Endpoint Tests (Issue #218)
# ============================================================================


class TestListBuiltinSchedulesEndpoint:
    """Tests for GET /api/scheduler/ui/schedules/builtin."""

    def test_list_builtin_schedules_empty(self, client, mock_scheduler_service):
        """Test when no built-in schedules exist."""
        mock_scheduler_service.list_schedules.return_value = []

        response = client.get("/api/scheduler/ui/schedules/builtin")

        assert response.status_code == 200
        data = response.get_json()
        assert data["schedules"] == []
        assert data["total"] == 0

    def test_list_builtin_schedules_with_data(
        self, client, mock_scheduler_service, schedule_factory
    ):
        """Test with built-in schedules."""
        builtin_schedule = schedule_factory(
            schedule_id="builtin-nightly",
            name="Nightly Survey",
            description="A built-in schedule",
            routine_count=2,
        )
        mock_scheduler_service.list_schedules.return_value = [builtin_schedule]

        # Mock is_builtin_schedule to return True for this schedule
        module = _get_scheduler_ui_module()
        with patch.object(module, "is_builtin_schedule", return_value=True):
            response = client.get("/api/scheduler/ui/schedules/builtin")

        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 1
        assert data["schedules"][0]["name"] == "Nightly Survey"
        assert data["schedules"][0]["routine_count"] == 2

    def test_list_builtin_schedules_excludes_user(
        self, client, mock_scheduler_service, schedule_factory
    ):
        """Test that user schedules are excluded."""
        user_schedule = schedule_factory(
            schedule_id="user-schedule", name="My Schedule", description=""
        )
        mock_scheduler_service.list_schedules.return_value = [user_schedule]

        # Mock is_builtin_schedule to return False
        module = _get_scheduler_ui_module()
        with patch.object(module, "is_builtin_schedule", return_value=False):
            response = client.get("/api/scheduler/ui/schedules/builtin")

        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 0

    def test_list_builtin_schedules_error(self, client, mock_scheduler_service):
        """Test error handling."""
        mock_scheduler_service.list_schedules.side_effect = Exception("DB error")

        response = client.get("/api/scheduler/ui/schedules/builtin")

        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data


# ============================================================================
# Create Schedule Endpoint Tests (Issue #218)
# ============================================================================


class TestCreateScheduleEndpoint:
    """Tests for POST /api/scheduler/ui/schedules."""

    def test_create_schedule_success(self, client, mock_scheduler_service, valid_schedule_payload):
        """Test successful schedule creation."""
        mock_scheduler_service.create_schedule.return_value = True

        response = client.post(
            "/api/scheduler/ui/schedules",
            json=valid_schedule_payload,
            content_type="application/json",
        )

        assert response.status_code == 201, f"Response: {response.get_json()}"
        data = response.get_json()
        assert data["message"] == "Schedule created"
        assert "schedule_id" in data
        assert "schedule" in data

    def test_create_schedule_returns_id(
        self, client, mock_scheduler_service, valid_schedule_payload
    ):
        """Test that schedule_id is returned."""
        mock_scheduler_service.create_schedule.return_value = True

        response = client.post(
            "/api/scheduler/ui/schedules",
            json=valid_schedule_payload,
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.get_json()
        assert "schedule_id" in data
        assert len(data["schedule_id"]) > 0

    def test_create_schedule_empty_body(self, client):
        """Test with missing JSON body."""
        response = client.post("/api/scheduler/ui/schedules", content_type="application/json")

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_create_schedule_invalid_json(self, client):
        """Test with malformed JSON."""
        response = client.post(
            "/api/scheduler/ui/schedules", data="not valid json", content_type="application/json"
        )

        assert response.status_code == 400

    def test_create_schedule_missing_name(self, client):
        """Test with missing required field."""
        response = client.post(
            "/api/scheduler/ui/schedules",
            json={"routines": []},  # Missing name
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_create_schedule_invalid_trigger(self, client, valid_schedule_payload):
        """Test with invalid trigger type in routine."""
        # Schema 3.0: trigger_type is now inside routines[].trigger
        valid_schedule_payload["routines"][0]["trigger"]["trigger_type"] = "invalid_trigger"

        response = client.post(
            "/api/scheduler/ui/schedules",
            json=valid_schedule_payload,
            content_type="application/json",
        )

        # Should fail validation
        assert response.status_code == 400

    def test_create_schedule_validation_error(
        self, client, mock_scheduler_service, valid_schedule_payload
    ):
        """Test when service validation fails."""
        from webui.backend.lib.schedule_schema import ScheduleValidationError

        mock_scheduler_service.create_schedule.side_effect = ScheduleValidationError(
            "Invalid schedule"
        )

        response = client.post(
            "/api/scheduler/ui/schedules",
            json=valid_schedule_payload,
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "validation failed" in data["error"].lower()

    def test_create_schedule_service_error(
        self, client, mock_scheduler_service, valid_schedule_payload
    ):
        """Test when service returns failure."""
        mock_scheduler_service.create_schedule.return_value = False

        response = client.post(
            "/api/scheduler/ui/schedules",
            json=valid_schedule_payload,
            content_type="application/json",
        )

        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data


# ============================================================================
# Update Schedule Endpoint Tests (Issue #218)
# ============================================================================


class TestUpdateScheduleEndpoint:
    """Tests for PUT /api/scheduler/ui/schedules/{id}."""

    def test_update_schedule_success(self, client, mock_scheduler_service, sample_schedule):
        """Test successful schedule update."""
        mock_scheduler_service.get_schedule.return_value = sample_schedule
        updated = MagicMock()
        updated.to_dict.return_value = {"schedule_id": "test-schedule", "name": "Updated Name"}
        mock_scheduler_service.update_schedule.return_value = updated

        response = client.put(
            "/api/scheduler/ui/schedules/test-schedule",
            json={"name": "Updated Name"},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["message"] == "Schedule updated"
        assert "schedule" in data

    def test_update_schedule_not_found(self, client, mock_scheduler_service):
        """Test updating non-existent schedule."""
        mock_scheduler_service.get_schedule.return_value = None

        response = client.put(
            "/api/scheduler/ui/schedules/nonexistent",
            json={"name": "New Name"},
            content_type="application/json",
        )

        assert response.status_code == 404
        data = response.get_json()
        assert "not found" in data["error"].lower()

    def test_update_schedule_builtin_protected(
        self, client, mock_scheduler_service, sample_schedule
    ):
        """Test that built-in schedules cannot be modified."""
        mock_scheduler_service.get_schedule.return_value = sample_schedule
        mock_scheduler_service.update_schedule.side_effect = ValueError(
            "Cannot modify built-in schedule"
        )

        response = client.put(
            "/api/scheduler/ui/schedules/builtin-id",
            json={"name": "New Name"},
            content_type="application/json",
        )

        assert response.status_code == 403
        data = response.get_json()
        assert "built-in" in data["error"].lower()

    def test_update_schedule_empty_body(self, client, mock_scheduler_service, sample_schedule):
        """Test with missing JSON body."""
        mock_scheduler_service.get_schedule.return_value = sample_schedule

        response = client.put(
            "/api/scheduler/ui/schedules/test-schedule", content_type="application/json"
        )

        assert response.status_code == 400

    def test_update_schedule_invalid_data(self, client, mock_scheduler_service, sample_schedule):
        """Test with invalid update data."""
        mock_scheduler_service.get_schedule.return_value = sample_schedule

        response = client.put(
            "/api/scheduler/ui/schedules/test-schedule",
            data="not json",
            content_type="application/json",
        )

        assert response.status_code == 400

    def test_update_schedule_validation_error(
        self, client, mock_scheduler_service, sample_schedule
    ):
        """Test when validation fails."""
        from webui.backend.lib.schedule_schema import ScheduleValidationError

        mock_scheduler_service.get_schedule.return_value = sample_schedule
        mock_scheduler_service.update_schedule.side_effect = ScheduleValidationError("Invalid data")

        response = client.put(
            "/api/scheduler/ui/schedules/test-schedule",
            json={"name": ""},
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "validation failed" in data["error"].lower()

    def test_update_schedule_partial_update(self, client, mock_scheduler_service, sample_schedule):
        """Test partial field update."""
        mock_scheduler_service.get_schedule.return_value = sample_schedule
        updated = MagicMock()
        updated.to_dict.return_value = {
            "schedule_id": "test-schedule",
            "description": "New description",
        }
        mock_scheduler_service.update_schedule.return_value = updated

        response = client.put(
            "/api/scheduler/ui/schedules/test-schedule",
            json={"description": "New description"},
            content_type="application/json",
        )

        assert response.status_code == 200
        mock_scheduler_service.update_schedule.assert_called_with(
            "test-schedule", {"description": "New description"}
        )

    def test_update_schedule_service_error(self, client, mock_scheduler_service, sample_schedule):
        """Test when update fails."""
        mock_scheduler_service.get_schedule.return_value = sample_schedule
        mock_scheduler_service.update_schedule.return_value = None

        response = client.put(
            "/api/scheduler/ui/schedules/test-schedule",
            json={"name": "New Name"},
            content_type="application/json",
        )

        assert response.status_code == 500


# ============================================================================
# Delete Schedule Endpoint Tests (Issue #218)
# ============================================================================


class TestDeleteScheduleEndpoint:
    """Tests for DELETE /api/scheduler/ui/schedules/{id}."""

    def test_delete_schedule_success(self, client, mock_scheduler_service, sample_schedule):
        """Test successful schedule deletion."""
        mock_scheduler_service.get_schedule.return_value = sample_schedule
        mock_scheduler_service.delete_schedule.return_value = True

        response = client.delete("/api/scheduler/ui/schedules/test-schedule")

        assert response.status_code == 200
        data = response.get_json()
        assert data["message"] == "Schedule deleted"
        assert data["schedule_id"] == "test-schedule"

    def test_delete_schedule_not_found(self, client, mock_scheduler_service):
        """Test deleting non-existent schedule."""
        mock_scheduler_service.get_schedule.return_value = None

        response = client.delete("/api/scheduler/ui/schedules/nonexistent")

        assert response.status_code == 404
        data = response.get_json()
        assert "not found" in data["error"].lower()

    def test_delete_schedule_builtin_protected(
        self, client, mock_scheduler_service, sample_schedule
    ):
        """Test that built-in schedules cannot be deleted."""
        mock_scheduler_service.get_schedule.return_value = sample_schedule
        mock_scheduler_service.delete_schedule.side_effect = ValueError(
            "Cannot delete built-in schedule"
        )

        response = client.delete("/api/scheduler/ui/schedules/builtin-id")

        assert response.status_code == 403
        data = response.get_json()
        assert "built-in" in data["error"].lower()

    def test_delete_schedule_returns_id(self, client, mock_scheduler_service, sample_schedule):
        """Test that deleted schedule_id is returned."""
        mock_scheduler_service.get_schedule.return_value = sample_schedule
        mock_scheduler_service.delete_schedule.return_value = True

        response = client.delete("/api/scheduler/ui/schedules/my-schedule")

        assert response.status_code == 200
        data = response.get_json()
        assert data["schedule_id"] == "my-schedule"

    def test_delete_schedule_service_error(self, client, mock_scheduler_service, sample_schedule):
        """Test when deletion fails."""
        mock_scheduler_service.get_schedule.return_value = sample_schedule
        mock_scheduler_service.delete_schedule.return_value = False

        response = client.delete("/api/scheduler/ui/schedules/test-schedule")

        assert response.status_code == 500


# ============================================================================
# Clone Schedule Endpoint Tests (Issue #320)
# ============================================================================


class TestCloneScheduleEndpoint:
    """Tests for POST /api/scheduler/ui/schedules/{id}/clone."""

    @pytest.fixture
    def clone_schedule_mock(self):
        """Create a mock schedule with all properties needed for cloning."""
        schedule = MagicMock()
        schedule.schedule_id = "original-schedule-id"
        schedule.name = "Original Schedule"
        schedule.description = "Original description"
        schedule.enabled = True
        schedule.is_active = False
        schedule.create_deployment = False
        schedule.deployment_id = None
        schedule.routines = []
        return schedule

    def test_clone_schedule_success(self, client, mock_scheduler_service, clone_schedule_mock):
        """Test successful schedule cloning with default name."""
        # Add a routine with proper to_dict
        routine_mock = MagicMock()
        routine_mock.to_dict.return_value = {
            "routine_id": "original-routine",
            "name": "Test Routine",
            "trigger": {"trigger_type": "fixed_time", "time": "21:00", "days_of_week": [0]},
            "actions": [],
            "pre_condition": None,
            "description": "",
        }
        clone_schedule_mock.routines = [routine_mock]
        mock_scheduler_service.get_schedule.return_value = clone_schedule_mock
        mock_scheduler_service.create_schedule.return_value = True

        response = client.post("/api/scheduler/ui/schedules/test-schedule/clone")

        assert response.status_code == 201
        data = response.get_json()
        assert data["message"] == "Schedule cloned"
        assert "schedule_id" in data
        assert "schedule" in data
        assert data["schedule"]["name"] == "Original Schedule (Copy)"
        mock_scheduler_service.create_schedule.assert_called_once()

    def test_clone_schedule_with_custom_name(
        self, client, mock_scheduler_service, clone_schedule_mock
    ):
        """Test cloning with custom name."""
        mock_scheduler_service.get_schedule.return_value = clone_schedule_mock
        mock_scheduler_service.create_schedule.return_value = True

        response = client.post(
            "/api/scheduler/ui/schedules/test-schedule/clone",
            json={"name": "My Custom Clone"},
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["schedule"]["name"] == "My Custom Clone"

    def test_clone_schedule_not_found(self, client, mock_scheduler_service):
        """Test cloning non-existent schedule."""
        mock_scheduler_service.get_schedule.return_value = None

        response = client.post("/api/scheduler/ui/schedules/nonexistent/clone")

        assert response.status_code == 404
        data = response.get_json()
        assert "not found" in data["error"].lower()

    def test_clone_builtin_schedule_success(
        self, client, mock_scheduler_service, clone_schedule_mock
    ):
        """Test cloning a built-in schedule creates user-owned copy."""
        mock_scheduler_service.get_schedule.return_value = clone_schedule_mock
        mock_scheduler_service.create_schedule.return_value = True

        response = client.post("/api/scheduler/ui/schedules/builtin-nightly/clone")

        assert response.status_code == 201
        # Verify create_schedule was called (creates new user schedule)
        mock_scheduler_service.create_schedule.assert_called_once()

    def test_clone_schedule_generates_new_ids(
        self, client, mock_scheduler_service, clone_schedule_mock
    ):
        """Test that clone generates new schedule ID."""
        clone_schedule_mock.schedule_id = "original-id"
        mock_scheduler_service.get_schedule.return_value = clone_schedule_mock
        mock_scheduler_service.create_schedule.return_value = True

        response = client.post("/api/scheduler/ui/schedules/original-id/clone")

        assert response.status_code == 201
        data = response.get_json()
        # New schedule_id should differ from original
        assert data["schedule_id"] != "original-id"

    def test_clone_schedule_generates_new_routine_ids(
        self, client, mock_scheduler_service, clone_schedule_mock
    ):
        """Test that clone generates new routine IDs."""
        routine_mock = MagicMock()
        routine_mock.to_dict.return_value = {
            "routine_id": "original-routine-id",
            "name": "Test Routine",
            "trigger": {"trigger_type": "fixed_time", "time": "21:00", "days_of_week": [0]},
            "actions": [],
            "pre_condition": None,
            "description": "",
        }
        clone_schedule_mock.routines = [routine_mock]
        mock_scheduler_service.get_schedule.return_value = clone_schedule_mock
        mock_scheduler_service.create_schedule.return_value = True

        response = client.post("/api/scheduler/ui/schedules/test-schedule/clone")

        assert response.status_code == 201
        # Verify create_schedule was called with new routine IDs
        call_args = mock_scheduler_service.create_schedule.call_args
        new_schedule = call_args[0][0]
        assert len(new_schedule.routines) == 1
        assert new_schedule.routines[0].routine_id != "original-routine-id"

    def test_clone_schedule_is_not_active(
        self, client, mock_scheduler_service, clone_schedule_mock
    ):
        """Test that cloned schedule is not active."""
        clone_schedule_mock.is_active = True  # Original is active
        mock_scheduler_service.get_schedule.return_value = clone_schedule_mock
        mock_scheduler_service.create_schedule.return_value = True

        response = client.post("/api/scheduler/ui/schedules/test-schedule/clone")

        assert response.status_code == 201
        data = response.get_json()
        assert data["schedule"]["is_active"] is False

    def test_clone_schedule_long_name_truncated(
        self, client, mock_scheduler_service, clone_schedule_mock
    ):
        """Test that cloning with long original name truncates to fit suffix."""
        clone_schedule_mock.name = "A" * 195  # 195 chars + " (Copy)" = 202 > 200
        mock_scheduler_service.get_schedule.return_value = clone_schedule_mock
        mock_scheduler_service.create_schedule.return_value = True

        response = client.post("/api/scheduler/ui/schedules/test-schedule/clone")

        assert response.status_code == 201
        data = response.get_json()
        assert len(data["schedule"]["name"]) <= 200
        assert data["schedule"]["name"].endswith(" (Copy)")

    def test_clone_schedule_empty_name_rejected(
        self, client, mock_scheduler_service, clone_schedule_mock
    ):
        """Test that empty custom name is rejected."""
        mock_scheduler_service.get_schedule.return_value = clone_schedule_mock

        response = client.post(
            "/api/scheduler/ui/schedules/test-schedule/clone",
            json={"name": "   "},
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "empty" in data["error"].lower()

    def test_clone_schedule_name_too_long_rejected(
        self, client, mock_scheduler_service, clone_schedule_mock
    ):
        """Test that overly long name is rejected."""
        mock_scheduler_service.get_schedule.return_value = clone_schedule_mock

        response = client.post(
            "/api/scheduler/ui/schedules/test-schedule/clone",
            json={"name": "A" * 201},
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "200" in data["error"] or "characters" in data["error"].lower()

    def test_clone_schedule_service_error(
        self, client, mock_scheduler_service, clone_schedule_mock
    ):
        """Test when service fails to create clone."""
        mock_scheduler_service.get_schedule.return_value = clone_schedule_mock
        mock_scheduler_service.create_schedule.return_value = False

        response = client.post("/api/scheduler/ui/schedules/test-schedule/clone")

        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data


# ============================================================================
# Activate Schedule Endpoint Tests (Issue #218)
# ============================================================================


class TestActivateScheduleEndpoint:
    """Tests for POST /api/scheduler/ui/schedules/{id}/activate."""

    def test_activate_schedule_success(self, client, mock_scheduler_service, sample_schedule):
        """Test successful schedule activation."""
        mock_scheduler_service.get_schedule.return_value = sample_schedule
        mock_scheduler_service.activate_schedule.return_value = None  # Success - no exception

        response = client.post("/api/scheduler/ui/schedules/test-schedule/activate")

        assert response.status_code == 200
        data = response.get_json()
        assert data["message"] == "Schedule activated"
        assert data["schedule_id"] == "test-schedule"

    def test_activate_schedule_not_found(self, client, mock_scheduler_service):
        """Test activating non-existent schedule."""
        from webui.backend.lib.schedule_schema import ScheduleActivationError

        mock_scheduler_service.get_schedule.return_value = None
        mock_scheduler_service.activate_schedule.side_effect = ScheduleActivationError(
            "Schedule not found: nonexistent"
        )

        response = client.post("/api/scheduler/ui/schedules/nonexistent/activate")

        assert response.status_code == 400  # ScheduleActivationError returns 400
        data = response.get_json()
        assert "activation failed" in data["error"].lower()

    def test_activate_schedule_disabled(self, client, mock_scheduler_service, sample_schedule):
        """Test activating disabled schedule."""
        from webui.backend.lib.schedule_schema import ScheduleActivationError

        mock_scheduler_service.get_schedule.return_value = sample_schedule
        mock_scheduler_service.activate_schedule.side_effect = ScheduleActivationError(
            "Schedule is disabled"
        )

        response = client.post("/api/scheduler/ui/schedules/test-schedule/activate")

        assert response.status_code == 400
        data = response.get_json()
        # Error message is now sanitized - just check for activation failure
        assert "activation failed" in data["error"].lower()

    def test_activate_schedule_conflict(self, client, mock_scheduler_service, sample_schedule):
        """Test activation blocked by conflict."""
        from webui.backend.lib.schedule_schema import ScheduleConflictError

        mock_scheduler_service.get_schedule.return_value = sample_schedule
        mock_scheduler_service.activate_schedule.side_effect = ScheduleConflictError(
            "Conflict detected: Resource contention"
        )

        response = client.post("/api/scheduler/ui/schedules/test-schedule/activate")

        assert response.status_code == 409
        data = response.get_json()
        assert "conflict" in data["error"].lower()
        assert data["conflict"] is True

    def test_activate_schedule_skip_conflict_check(
        self, client, mock_scheduler_service, sample_schedule
    ):
        """Test activation with conflict check disabled."""
        mock_scheduler_service.get_schedule.return_value = sample_schedule
        mock_scheduler_service.activate_schedule.return_value = None  # Success - no exception

        response = client.post(
            "/api/scheduler/ui/schedules/test-schedule/activate",
            json={"check_conflicts": False},
            content_type="application/json",
        )

        assert response.status_code == 200
        mock_scheduler_service.activate_schedule.assert_called_once()
        call_kwargs = mock_scheduler_service.activate_schedule.call_args.kwargs
        assert call_kwargs["check_conflicts"] is False

    def test_activate_schedule_with_coordinates(
        self, client, mock_scheduler_service, sample_schedule
    ):
        """Test activation with lat/lon parameters."""
        mock_scheduler_service.get_schedule.return_value = sample_schedule
        mock_scheduler_service.activate_schedule.return_value = None  # Success - no exception

        response = client.post(
            "/api/scheduler/ui/schedules/test-schedule/activate",
            json={"latitude": 35.0, "longitude": -80.0, "timezone": "America/New_York"},
            content_type="application/json",
        )

        assert response.status_code == 200
        call_kwargs = mock_scheduler_service.activate_schedule.call_args.kwargs
        assert call_kwargs["latitude"] == 35.0
        assert call_kwargs["longitude"] == -80.0
        assert call_kwargs["timezone_name"] == "America/New_York"

    def test_activate_schedule_idempotent(self, client, mock_scheduler_service, sample_schedule):
        """Test that activating already active schedule succeeds."""
        sample_schedule.is_active = True
        mock_scheduler_service.get_schedule.return_value = sample_schedule
        mock_scheduler_service.activate_schedule.return_value = None  # Success - no exception

        response = client.post("/api/scheduler/ui/schedules/test-schedule/activate")

        assert response.status_code == 200


# ============================================================================
# Deactivate Schedule Endpoint Tests (Issue #218)
# ============================================================================


class TestDeactivateScheduleEndpoint:
    """Tests for POST /api/scheduler/ui/schedules/deactivate."""

    def test_deactivate_schedule_success(self, client, mock_scheduler_service, sample_schedule):
        """Test successful schedule deactivation."""
        mock_scheduler_service.get_active_schedule.return_value = sample_schedule
        mock_scheduler_service.deactivate_schedule.return_value = True

        response = client.post("/api/scheduler/ui/schedules/deactivate")

        assert response.status_code == 200
        data = response.get_json()
        assert data["message"] == "Schedule deactivated"
        assert data["was_active"] is True
        assert data["schedule_id"] == "test-schedule"

    def test_deactivate_schedule_none_active(self, client, mock_scheduler_service):
        """Test deactivating when none is active."""
        mock_scheduler_service.get_active_schedule.return_value = None

        response = client.post("/api/scheduler/ui/schedules/deactivate")

        assert response.status_code == 200
        data = response.get_json()
        assert data["was_active"] is False
        assert data["schedule_id"] is None

    def test_deactivate_schedule_returns_previous_id(
        self, client, mock_scheduler_service, sample_schedule
    ):
        """Test that deactivated schedule_id is returned."""
        sample_schedule.schedule_id = "previous-active"
        mock_scheduler_service.get_active_schedule.return_value = sample_schedule
        mock_scheduler_service.deactivate_schedule.return_value = True

        response = client.post("/api/scheduler/ui/schedules/deactivate")

        assert response.status_code == 200
        data = response.get_json()
        assert data["schedule_id"] == "previous-active"


# ============================================================================
# Validate Schedule Endpoint Tests (Issue #218)
# ============================================================================


class TestValidateScheduleEndpoint:
    """Tests for POST /api/scheduler/ui/schedules/{id}/validate."""

    @pytest.fixture
    def mock_conflict_report(self):
        """Create a mock ConflictReport."""
        report = MagicMock()
        report.has_blocking_conflicts = False
        report.total_conflicts = 0
        report.conflicts = []
        return report

    def test_validate_schedule_no_conflicts(
        self, client, mock_scheduler_service, sample_schedule, mock_conflict_report
    ):
        """Test validation with no conflicts."""
        mock_scheduler_service.get_schedule.return_value = sample_schedule
        mock_scheduler_service.get_cached_conflict_report.return_value = mock_conflict_report

        response = client.post("/api/scheduler/ui/schedules/test-schedule/validate")

        assert response.status_code == 200
        data = response.get_json()
        assert data["valid"] is True
        assert data["has_warnings"] is False
        assert data["total_conflicts"] == 0

    def test_validate_schedule_with_warnings(
        self, client, mock_scheduler_service, sample_schedule, mock_conflict_report
    ):
        """Test validation with warnings but no blocking conflicts."""
        mock_conflict_report.has_blocking_conflicts = False
        mock_conflict_report.total_conflicts = 2
        warning1 = MagicMock()
        warning1.severity = "warning"
        warning1.to_dict.return_value = {"message": "Warning 1", "severity": "warning"}
        warning2 = MagicMock()
        warning2.severity = "warning"
        warning2.to_dict.return_value = {"message": "Warning 2", "severity": "warning"}
        mock_conflict_report.conflicts = [warning1, warning2]

        mock_scheduler_service.get_schedule.return_value = sample_schedule
        mock_scheduler_service.get_cached_conflict_report.return_value = mock_conflict_report

        response = client.post("/api/scheduler/ui/schedules/test-schedule/validate")

        assert response.status_code == 200
        data = response.get_json()
        assert data["valid"] is True
        assert data["has_warnings"] is True
        assert data["total_conflicts"] == 2

    def test_validate_schedule_blocking_conflicts(
        self, client, mock_scheduler_service, sample_schedule, mock_conflict_report
    ):
        """Test validation with blocking conflicts."""
        mock_conflict_report.has_blocking_conflicts = True
        mock_conflict_report.total_conflicts = 1
        error_conflict = MagicMock()
        error_conflict.severity = "error"
        error_conflict.to_dict.return_value = {"message": "Blocking conflict", "severity": "error"}
        mock_conflict_report.conflicts = [error_conflict]

        mock_scheduler_service.get_schedule.return_value = sample_schedule
        mock_scheduler_service.get_cached_conflict_report.return_value = mock_conflict_report

        response = client.post("/api/scheduler/ui/schedules/test-schedule/validate")

        assert response.status_code == 200
        data = response.get_json()
        assert data["valid"] is False
        assert data["blocking_conflicts"] >= 1

    def test_validate_schedule_not_found(self, client, mock_scheduler_service):
        """Test validating non-existent schedule."""
        mock_scheduler_service.get_schedule.return_value = None

        response = client.post("/api/scheduler/ui/schedules/nonexistent/validate")

        assert response.status_code == 404
        data = response.get_json()
        assert "not found" in data["error"].lower()

    def test_validate_schedule_with_coordinates(
        self, client, mock_scheduler_service, sample_schedule, mock_conflict_report
    ):
        """Test validation with location parameters."""
        mock_scheduler_service.get_schedule.return_value = sample_schedule
        mock_scheduler_service.get_cached_conflict_report.return_value = mock_conflict_report

        response = client.post(
            "/api/scheduler/ui/schedules/test-schedule/validate",
            json={"latitude": 35.0, "longitude": -80.0, "timezone": "America/New_York"},
            content_type="application/json",
        )

        assert response.status_code == 200
        call_kwargs = mock_scheduler_service.get_cached_conflict_report.call_args.kwargs
        assert call_kwargs["latitude"] == 35.0
        assert call_kwargs["longitude"] == -80.0
        assert call_kwargs["timezone_name"] == "America/New_York"

    def test_validate_schedule_custom_days(
        self, client, mock_scheduler_service, sample_schedule, mock_conflict_report
    ):
        """Test validation with custom preview days."""
        mock_scheduler_service.get_schedule.return_value = sample_schedule
        mock_scheduler_service.get_cached_conflict_report.return_value = mock_conflict_report

        response = client.post(
            "/api/scheduler/ui/schedules/test-schedule/validate",
            json={"days": 14},
            content_type="application/json",
        )

        assert response.status_code == 200
        call_kwargs = mock_scheduler_service.get_cached_conflict_report.call_args.kwargs
        assert call_kwargs["preview_days"] == 14


# ============================================================================
# CSRF Protection Tests
# ============================================================================


class TestCSRFProtection:
    """Tests verifying CSRF is enforced on state-changing endpoints."""

    @pytest.fixture
    def csrf_enabled_app(self):
        """Flask app with CSRF enabled for testing."""
        from flask import Flask
        from flask_wtf.csrf import CSRFProtect

        from webui.backend.routes.scheduler_ui import scheduler_ui_bp

        test_app = Flask(__name__)
        test_app.config["TESTING"] = True
        test_app.config["SECRET_KEY"] = "test-secret-key-for-csrf"
        test_app.config["WTF_CSRF_ENABLED"] = True

        # Initialize CSRF protection
        CSRFProtect(test_app)

        # Register blueprint
        test_app.register_blueprint(scheduler_ui_bp, url_prefix="/api/scheduler/ui")

        return test_app

    def test_create_schedule_requires_csrf(self, csrf_enabled_app, mock_scheduler_service):
        """POST /schedules without CSRF token should fail."""
        client = csrf_enabled_app.test_client()

        response = client.post(
            "/api/scheduler/ui/schedules", json={"name": "Test"}, content_type="application/json"
        )

        # Should fail without CSRF token (400 Bad Request or 403 Forbidden)
        assert response.status_code in (400, 403), (
            f"Expected 400 or 403, got {response.status_code}"
        )

    def test_activate_schedule_requires_csrf(self, csrf_enabled_app, mock_scheduler_service):
        """POST /schedules/{id}/activate without CSRF token should fail."""
        client = csrf_enabled_app.test_client()

        response = client.post(
            "/api/scheduler/ui/schedules/test-id/activate", json={}, content_type="application/json"
        )

        assert response.status_code in (400, 403)

    def test_delete_schedule_requires_csrf(self, csrf_enabled_app, mock_scheduler_service):
        """DELETE /schedules/{id} without CSRF token should fail."""
        client = csrf_enabled_app.test_client()

        response = client.delete("/api/scheduler/ui/schedules/test-id")

        assert response.status_code in (400, 403)

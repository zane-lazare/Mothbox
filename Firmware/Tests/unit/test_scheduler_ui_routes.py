"""
Unit tests for Scheduler UI API Routes (Issue #214)

Tests the REST API endpoints for schedule preview and management.

Coverage Target: 85%+
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
def reset_scheduler_service():
    """Reset the scheduler service singleton before each test.

    Note: app.py uses relative import 'routes.scheduler_ui' which creates a
    different module object than 'webui.backend.routes.scheduler_ui'. We need
    to patch both to handle all cases.
    """
    import sys
    # Get the module that app.py actually uses (relative import creates this)
    module = sys.modules.get('routes.scheduler_ui')
    if module is None:
        # Fallback to full path if relative import module not found
        import webui.backend.routes.scheduler_ui as module

    original = getattr(module, '_scheduler_service', None)
    module._scheduler_service = None
    yield
    module._scheduler_service = original


@pytest.fixture
def client():
    """Create Flask test client."""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
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
def sample_schedule():
    """Create a mock schedule object."""
    schedule = MagicMock()
    schedule.schedule_id = "test-schedule"
    schedule.name = "Test Schedule"
    schedule.description = "A test schedule"
    schedule.trigger_type = "interval"
    schedule.enabled = True
    schedule.is_active = False
    schedule.created_at = "2025-06-15T00:00:00Z"
    schedule.modified_at = "2025-06-15T00:00:00Z"
    schedule.to_dict.return_value = {
        "schedule_id": "test-schedule",
        "name": "Test Schedule",
        "trigger_type": "interval",
    }
    return schedule


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
        with patch.object(module, 'generate_preview') as mock_gen:
            mock_gen.return_value = mock_preview_result

            response = client.get('/api/scheduler/ui/schedules/test-schedule/preview')

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
        with patch.object(module, 'generate_preview') as mock_gen:
            mock_gen.return_value = mock_preview_result

            response = client.get('/api/scheduler/ui/schedules/test-schedule/preview?days=14')

            assert response.status_code == 200
            mock_gen.assert_called_once()
            call_kwargs = mock_gen.call_args.kwargs
            assert call_kwargs['days'] == 14

    def test_preview_with_coordinates(self, client, mock_scheduler_service, mock_preview_result):
        """Test preview with lat/lon parameters."""
        schedule = MagicMock()
        mock_scheduler_service.get_schedule.return_value = schedule

        module = _get_scheduler_ui_module()
        with patch.object(module, 'generate_preview') as mock_gen:
            mock_gen.return_value = mock_preview_result

            response = client.get(
                '/api/scheduler/ui/schedules/test-schedule/preview?lat=35.0&lon=-80.0'
            )

            assert response.status_code == 200
            call_kwargs = mock_gen.call_args.kwargs
            assert call_kwargs['latitude'] == 35.0
            assert call_kwargs['longitude'] == -80.0

    def test_preview_schedule_not_found(self, client, mock_scheduler_service):
        """Test preview with non-existent schedule."""
        mock_scheduler_service.get_schedule.return_value = None

        response = client.get('/api/scheduler/ui/schedules/nonexistent/preview')

        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
        assert "not found" in data["error"].lower()

    def test_preview_invalid_days_not_integer(self, client):
        """Test preview with non-integer days."""
        response = client.get('/api/scheduler/ui/schedules/test/preview?days=abc')

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "days" in data["error"].lower()

    def test_preview_invalid_days_below_min(self, client):
        """Test preview with days below minimum."""
        response = client.get('/api/scheduler/ui/schedules/test/preview?days=0')

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_preview_invalid_days_above_max(self, client):
        """Test preview with days above maximum."""
        response = client.get('/api/scheduler/ui/schedules/test/preview?days=100')

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_preview_invalid_latitude(self, client):
        """Test preview with invalid latitude."""
        response = client.get('/api/scheduler/ui/schedules/test/preview?lat=100')

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "Latitude" in data["message"]

    def test_preview_invalid_longitude(self, client):
        """Test preview with invalid longitude."""
        response = client.get('/api/scheduler/ui/schedules/test/preview?lon=200')

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "Longitude" in data["message"]

    def test_preview_invalid_lat_format(self, client):
        """Test preview with non-numeric latitude."""
        response = client.get('/api/scheduler/ui/schedules/test/preview?lat=abc')

        assert response.status_code == 400
        data = response.get_json()
        assert "lat" in data["error"].lower()

    def test_preview_invalid_timezone(self, client):
        """Test preview with invalid timezone name."""
        response = client.get('/api/scheduler/ui/schedules/test/preview?tz=Invalid/Timezone')

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "timezone" in data["error"].lower()
        assert "Invalid timezone" in data["message"]

    def test_preview_empty_timezone(self, client):
        """Test preview with empty timezone."""
        response = client.get('/api/scheduler/ui/schedules/test/preview?tz=')

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

        response = client.get('/api/scheduler/ui/schedules')

        assert response.status_code == 200
        data = response.get_json()
        assert data["schedules"] == []
        assert data["total"] == 0

    def test_list_schedules_with_data(self, client, mock_scheduler_service):
        """Test listing with schedules."""
        schedule = MagicMock()
        schedule.schedule_id = "test-schedule"
        schedule.name = "Test Schedule"
        schedule.description = "A test schedule"
        schedule.trigger_type = "interval"
        schedule.enabled = True
        schedule.is_active = False
        schedule.created_at = "2025-06-15T00:00:00Z"
        schedule.modified_at = "2025-06-15T00:00:00Z"
        mock_scheduler_service.list_schedules.return_value = [schedule]

        response = client.get('/api/scheduler/ui/schedules')

        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 1
        assert len(data["schedules"]) == 1
        assert data["schedules"][0]["schedule_id"] == "test-schedule"

    def test_list_schedules_include_builtin(self, client, mock_scheduler_service):
        """Test include_builtin parameter."""
        mock_scheduler_service.list_schedules.return_value = []

        response = client.get('/api/scheduler/ui/schedules?include_builtin=true')

        assert response.status_code == 200
        mock_scheduler_service.list_schedules.assert_called_with(include_builtin=True)

    def test_list_schedules_active_only(self, client, mock_scheduler_service):
        """Test active_only filter."""
        # One active, one inactive
        active_schedule = MagicMock()
        active_schedule.schedule_id = "active"
        active_schedule.name = "Active"
        active_schedule.description = ""
        active_schedule.trigger_type = "interval"
        active_schedule.enabled = True
        active_schedule.is_active = True
        active_schedule.created_at = "2025-06-15T00:00:00Z"
        active_schedule.modified_at = "2025-06-15T00:00:00Z"

        inactive_schedule = MagicMock()
        inactive_schedule.schedule_id = "inactive"
        inactive_schedule.name = "Inactive"
        inactive_schedule.description = ""
        inactive_schedule.trigger_type = "interval"
        inactive_schedule.enabled = True
        inactive_schedule.is_active = False
        inactive_schedule.created_at = "2025-06-15T00:00:00Z"
        inactive_schedule.modified_at = "2025-06-15T00:00:00Z"

        mock_scheduler_service.list_schedules.return_value = [inactive_schedule, active_schedule]

        response = client.get('/api/scheduler/ui/schedules?active_only=true')

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

        response = client.get('/api/scheduler/ui/schedules/test-schedule')

        assert response.status_code == 200
        data = response.get_json()
        assert data["schedule_id"] == "test-schedule"

    def test_get_schedule_not_found(self, client, mock_scheduler_service):
        """Test schedule not found."""
        mock_scheduler_service.get_schedule.return_value = None

        response = client.get('/api/scheduler/ui/schedules/nonexistent')

        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
        assert "not found" in data["error"].lower()

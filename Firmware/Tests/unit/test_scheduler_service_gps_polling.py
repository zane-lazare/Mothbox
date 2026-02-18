"""
Unit tests for GPS auto-update in SchedulerService (Issue #382).

Tests the check_and_update_gps() method that detects GPS availability
after timezone-based activation and updates coordinates + cron entries.
"""

import json
import uuid

import pytest

try:
    from webui.backend.lib.schedule_schema import (
        Action,
        IntervalTrigger,
        Routine,
        Schedule,
        TimeWindow,
    )
    from webui.backend.services.scheduler_service import SchedulerService

    IMPLEMENTATION_EXISTS = True
except ImportError:
    IMPLEMENTATION_EXISTS = False
    SchedulerService = None
    Schedule = None

pytestmark = pytest.mark.skipif(
    not IMPLEMENTATION_EXISTS, reason="Implementation not yet created"
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_schedules_dir(tmp_path, monkeypatch):
    """Create temp directory and mock SCHEDULES_DIR and ACTIVE_STATE_FILE."""
    schedules = tmp_path / "schedules"
    schedules.mkdir()
    monkeypatch.setattr("mothbox_paths.SCHEDULES_DIR", schedules)
    monkeypatch.setattr("webui.backend.lib.schedule_storage.SCHEDULES_DIR", schedules)
    active_state_file = tmp_path / "active_state.json"
    monkeypatch.setattr(
        "webui.backend.services.scheduler_service.ACTIVE_STATE_FILE", active_state_file
    )
    # Mock CONTROLS_FILE for GPS reads
    controls_file = tmp_path / "controls.txt"
    controls_file.write_text("lat=n/a\nlon=n/a\n")
    monkeypatch.setattr("mothbox_paths.CONTROLS_FILE", controls_file)
    monkeypatch.setattr(
        "webui.backend.services.scheduler_service.CONTROLS_FILE", controls_file
    )
    return tmp_path


@pytest.fixture
def sample_schedule():
    """Create a valid Schedule object for testing."""
    actions = [
        Action(action_type="camera", action_name="takephoto", offset_minutes=0),
    ]
    time_window = TimeWindow(start_time="21:00", end_time="05:00")
    trigger = IntervalTrigger(interval_minutes=60, time_window=time_window)
    routine = Routine(
        routine_id=str(uuid.uuid4()),
        name="Test Routine",
        trigger=trigger,
        actions=actions,
    )
    return Schedule(
        schedule_id=str(uuid.uuid4()),
        name="Test Schedule",
        routines=[routine],
        enabled=True,
    )


@pytest.fixture
def service(temp_schedules_dir):
    """Create a fresh SchedulerService for each test."""
    return SchedulerService(cache_ttl=300, max_cache_size=100)


# ============================================================================
# check_and_update_gps() Tests
# ============================================================================


class TestCheckAndUpdateGps:
    """Tests for the check_and_update_gps method."""

    def test_noop_when_source_is_gps(self, service):
        """Should return updated=False when coordinates already from GPS."""
        service._active_coordinates_source = "gps"
        service._active_schedule_id = "test-1"

        result = service.check_and_update_gps()

        assert result["updated"] is False

    def test_noop_when_source_is_explicit(self, service):
        """Should return updated=False when coordinates explicitly provided."""
        service._active_coordinates_source = "explicit"
        service._active_schedule_id = "test-1"

        result = service.check_and_update_gps()

        assert result["updated"] is False

    def test_noop_when_no_active_schedule(self, service):
        """Should return updated=False when no schedule is active."""
        service._active_schedule_id = None
        service._active_coordinates_source = None

        result = service.check_and_update_gps()

        assert result["updated"] is False

    def test_noop_when_gps_still_unavailable(self, service, temp_schedules_dir):
        """Should return updated=False when controls.txt still has n/a."""
        service._active_coordinates_source = "timezone"
        service._active_schedule_id = "test-1"
        # controls.txt already has lat=n/a, lon=n/a from fixture

        result = service.check_and_update_gps()

        assert result["updated"] is False
        assert service._active_coordinates_source == "timezone"

    def test_updates_when_gps_available(
        self, service, temp_schedules_dir, sample_schedule, monkeypatch
    ):
        """Should update coordinates and return updated=True when GPS available."""
        # Write GPS coordinates to controls.txt
        controls_file = temp_schedules_dir / "controls.txt"
        controls_file.write_text("lat=-41.2865\nlon=174.7762\n")

        # Set up active schedule with timezone source
        from webui.backend.lib.schedule_storage import create_schedule

        create_schedule(sample_schedule)
        service.set_enabled_schedule(sample_schedule.schedule_id)
        service._active_schedule_id = sample_schedule.schedule_id
        service._active_coordinates_source = "timezone"
        service._active_latitude = 0.0
        service._active_longitude = 0.0
        service._active_timezone_name = "Pacific/Auckland"

        # Mock cron bridge to avoid system cron changes
        monkeypatch.setattr(
            "webui.backend.services.scheduler_service.apply_to_system",
            lambda **kwargs: None,
        )

        result = service.check_and_update_gps()

        assert result["updated"] is True
        assert result["latitude"] == pytest.approx(-41.2865)
        assert result["longitude"] == pytest.approx(174.7762)
        assert result["previous_source"] == "timezone"
        assert service._active_coordinates_source == "gps"
        assert service._active_latitude == pytest.approx(-41.2865)
        assert service._active_longitude == pytest.approx(174.7762)

    def test_persists_state_after_update(
        self, service, temp_schedules_dir, sample_schedule, monkeypatch
    ):
        """Should write updated coordinates to active_state.json."""
        controls_file = temp_schedules_dir / "controls.txt"
        controls_file.write_text("lat=-41.2865\nlon=174.7762\n")

        from webui.backend.lib.schedule_storage import create_schedule

        create_schedule(sample_schedule)
        service.set_enabled_schedule(sample_schedule.schedule_id)
        service._active_schedule_id = sample_schedule.schedule_id
        service._active_coordinates_source = "timezone"
        service._active_latitude = 0.0
        service._active_longitude = 0.0
        service._active_timezone_name = "Pacific/Auckland"

        monkeypatch.setattr(
            "webui.backend.services.scheduler_service.apply_to_system",
            lambda **kwargs: None,
        )

        service.check_and_update_gps()

        # Verify active_state.json was updated
        state_file = temp_schedules_dir / "active_state.json"
        assert state_file.exists()
        state = json.loads(state_file.read_text())
        assert state["coordinates_source"] == "gps"
        assert state["latitude"] == pytest.approx(-41.2865)
        assert state["longitude"] == pytest.approx(174.7762)

    def test_ignores_invalid_gps_values(self, service, temp_schedules_dir):
        """Should return updated=False when controls.txt has non-numeric GPS."""
        controls_file = temp_schedules_dir / "controls.txt"
        controls_file.write_text("lat=invalid\nlon=bad\n")

        service._active_coordinates_source = "timezone"
        service._active_schedule_id = "test-1"

        result = service.check_and_update_gps()

        assert result["updated"] is False
        assert service._active_coordinates_source == "timezone"

    def test_regenerates_cron_entries(
        self, service, temp_schedules_dir, sample_schedule, monkeypatch
    ):
        """Should call schedule_to_cron and apply_to_system with new coords."""
        controls_file = temp_schedules_dir / "controls.txt"
        controls_file.write_text("lat=-41.2865\nlon=174.7762\n")

        from webui.backend.lib.schedule_storage import create_schedule

        create_schedule(sample_schedule)
        service.set_enabled_schedule(sample_schedule.schedule_id)
        service._active_schedule_id = sample_schedule.schedule_id
        service._active_coordinates_source = "timezone"
        service._active_latitude = 0.0
        service._active_longitude = 0.0
        service._active_timezone_name = "Pacific/Auckland"

        apply_calls = []
        monkeypatch.setattr(
            "webui.backend.services.scheduler_service.apply_to_system",
            lambda **kwargs: apply_calls.append(kwargs),
        )

        service.check_and_update_gps()

        assert len(apply_calls) == 1
        assert apply_calls[0]["schedule_id"] == sample_schedule.schedule_id

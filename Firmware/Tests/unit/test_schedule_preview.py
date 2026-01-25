"""
Unit tests for Schedule Preview Library (Issue #214)

Tests preview generation, action expansion, moon phase integration,
and conflict detection for the scheduler preview system.

Coverage Target: 85%+
Test Count Target: 20+ tests
"""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

# Import schedule preview library
try:
    from webui.backend.lib.schedule_preview import (
        MAX_PREVIEW_DAYS,
        MIN_PREVIEW_DAYS,
        ActionExecution,
        PreviewExecution,
        PreviewResult,
        _expand_actions,
        _get_moon_phases_dict,
        _get_trigger_info,
        generate_preview,
        parse_and_validate_coordinate,
        parse_and_validate_days,
        validate_coordinates,
        validate_preview_days,
        validate_timezone,
    )

    IMPLEMENTATION_EXISTS = True
except ImportError:
    IMPLEMENTATION_EXISTS = False
    ActionExecution = None
    PreviewExecution = None
    PreviewResult = None

# Import schema classes
try:
    from webui.backend.lib.schedule_schema import (
        Action,
        FixedTimeTrigger,
        IntervalTrigger,
        MoonPhaseTrigger,
        Routine,
        Schedule,
        SensorTrigger,
        SolarTrigger,
        TimeWindow,
    )
except ImportError:
    Routine = None
    Schedule = None

# Import conflict types
try:
    from webui.backend.lib.schedule_conflict import Conflict
except ImportError:
    Conflict = None


# Skip all tests if implementation doesn't exist
pytestmark = pytest.mark.skipif(not IMPLEMENTATION_EXISTS, reason="Implementation not yet created")


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_action():
    """Create a sample Action."""
    return Action(
        action_type="gpio",
        action_name="attract_on",
        offset_minutes=0,
        description="Turn on UV attract lights",
    )


@pytest.fixture
def sample_actions():
    """Create sample actions for routines."""
    return [
        Action(
            action_type="gpio",
            action_name="attract_on",
            offset_minutes=0,
            description="Turn on UV attract lights",
        ),
        Action(
            action_type="camera",
            action_name="takephoto",
            offset_minutes=5,
            description="Capture photo",
        ),
        Action(
            action_type="gpio",
            action_name="attract_off",
            offset_minutes=15,
            description="Turn off UV lights",
        ),
    ]


@pytest.fixture
def sample_routine(sample_actions):
    """Create a sample Routine for action expansion tests (Schema 3.0)."""
    time_window = TimeWindow(
        start_time="21:00",
        end_time="05:00",
    )

    trigger = IntervalTrigger(
        interval_minutes=60,
        time_window=time_window,
    )

    return Routine(
        routine_id="uv-capture-cycle",
        name="UV Capture Cycle",
        description="Standard UV light photo capture sequence",
        trigger=trigger,
        actions=sample_actions,
    )


@pytest.fixture
def sample_interval_schedule(sample_actions):
    """Create a schedule with interval trigger (Schema 3.0)."""
    time_window = TimeWindow(
        start_time="21:00",
        end_time="05:00",
    )

    trigger = IntervalTrigger(
        interval_minutes=60,
        time_window=time_window,
    )

    routine = Routine(
        routine_id="uv-capture-cycle",
        name="UV Capture Cycle",
        description="Standard UV light photo capture sequence",
        trigger=trigger,
        actions=sample_actions,
    )

    return Schedule(
        schedule_id="nightly-survey",
        name="Nightly Moth Survey",
        description="Hourly captures from 9 PM to 5 AM",
        routines=[routine],
        enabled=True,
    )


@pytest.fixture
def sample_solar_schedule(sample_actions):
    """Create a schedule with solar trigger (Schema 3.0)."""
    trigger = SolarTrigger(
        solar_event="sunset",
        offset_minutes=30,
        days_of_week=None,
    )

    routine = Routine(
        routine_id="sunset-routine",
        name="Sunset Capture",
        description="Capture 30 minutes after sunset",
        trigger=trigger,
        actions=sample_actions,
    )

    return Schedule(
        schedule_id="sunset-survey",
        name="Sunset Survey",
        description="Capture 30 minutes after sunset",
        routines=[routine],
        enabled=True,
    )


@pytest.fixture
def sample_moon_schedule(sample_actions):
    """Create a schedule with moon phase trigger (Schema 3.0)."""
    trigger = MoonPhaseTrigger(
        phases=["full"],
        offset_days=2,
        time_window=None,
    )

    routine = Routine(
        routine_id="fullmoon-routine",
        name="Full Moon Capture",
        description="Capture around full moon",
        trigger=trigger,
        actions=sample_actions,
    )

    return Schedule(
        schedule_id="fullmoon-survey",
        name="Full Moon Survey",
        description="Capture around full moon",
        routines=[routine],
        enabled=True,
    )


@pytest.fixture
def sample_fixed_time_schedule(sample_actions):
    """Create a schedule with fixed time trigger (Schema 3.0)."""
    trigger = FixedTimeTrigger(
        time="21:00",
        days_of_week=None,
    )

    routine = Routine(
        routine_id="fixed-routine",
        name="Nightly Capture",
        description="Capture every night at 9 PM",
        trigger=trigger,
        actions=sample_actions,
    )

    return Schedule(
        schedule_id="nightly-fixed",
        name="Nightly Fixed Time",
        description="Capture every night at 9 PM",
        routines=[routine],
        enabled=True,
    )


@pytest.fixture
def sample_sensor_schedule(sample_actions):
    """Create a schedule with sensor trigger (Schema 3.0)."""
    trigger = SensorTrigger(
        sensor_type="motion",
        threshold=1.0,
        comparison="gt",
        cooldown_minutes=5,
        time_window=None,
    )

    routine = Routine(
        routine_id="motion-routine",
        name="Motion Capture",
        description="Capture on motion detection",
        trigger=trigger,
        actions=sample_actions,
    )

    return Schedule(
        schedule_id="motion-triggered",
        name="Motion Triggered",
        description="Capture on motion detection",
        routines=[routine],
        enabled=True,
    )


# ============================================================================
# A. Data Structure Tests (5 tests)
# ============================================================================


class TestActionExecution:
    """Tests for ActionExecution dataclass."""

    def test_action_execution_to_dict(self):
        """Test ActionExecution serialization."""
        action = ActionExecution(
            time=datetime(2025, 6, 15, 21, 0, 0, tzinfo=UTC),
            action_name="attract_on",
            action_type="gpio",
            offset_minutes=0,
            description="Turn on UV lights",
        )

        result = action.to_dict()

        assert result["time"] == "2025-06-15T21:00:00+00:00"
        assert result["action_name"] == "attract_on"
        assert result["action_type"] == "gpio"
        assert result["offset_minutes"] == 0
        assert result["description"] == "Turn on UV lights"

    def test_action_execution_from_dict(self):
        """Test ActionExecution deserialization."""
        data = {
            "time": "2025-06-15T21:00:00+00:00",
            "action_name": "takephoto",
            "action_type": "camera",
            "offset_minutes": 5,
            "description": "Capture photo",
        }

        action = ActionExecution.from_dict(data)

        assert action.time == datetime(2025, 6, 15, 21, 0, 0, tzinfo=UTC)
        assert action.action_name == "takephoto"
        assert action.action_type == "camera"
        assert action.offset_minutes == 5
        assert action.description == "Capture photo"

    def test_action_execution_roundtrip(self):
        """Test ActionExecution serialization roundtrip."""
        original = ActionExecution(
            time=datetime(2025, 6, 15, 21, 5, 0, tzinfo=UTC),
            action_name="attract_off",
            action_type="gpio",
            offset_minutes=15,
            description="Turn off UV lights",
        )

        restored = ActionExecution.from_dict(original.to_dict())

        assert restored.time == original.time
        assert restored.action_name == original.action_name
        assert restored.action_type == original.action_type
        assert restored.offset_minutes == original.offset_minutes
        assert restored.description == original.description


class TestPreviewExecution:
    """Tests for PreviewExecution dataclass."""

    def test_preview_execution_to_dict(self):
        """Test PreviewExecution serialization."""
        actions = [
            ActionExecution(
                time=datetime(2025, 6, 15, 21, 0, 0, tzinfo=UTC),
                action_name="attract_on",
                action_type="gpio",
                offset_minutes=0,
            ),
        ]

        execution = PreviewExecution(
            start_time=datetime(2025, 6, 15, 21, 0, 0, tzinfo=UTC),
            end_time=datetime(2025, 6, 15, 21, 15, 0, tzinfo=UTC),
            routine_id="uv-cycle",
            routine_name="UV Capture Cycle",
            trigger_info="interval:60m",
            actions=actions,
        )

        result = execution.to_dict()

        assert result["start_time"] == "2025-06-15T21:00:00+00:00"
        assert result["end_time"] == "2025-06-15T21:15:00+00:00"
        assert result["pattern_id"] == "uv-cycle"
        assert result["pattern_name"] == "UV Capture Cycle"
        assert result["trigger_info"] == "interval:60m"
        assert len(result["actions"]) == 1

    def test_preview_execution_empty_actions(self):
        """Test PreviewExecution with empty actions list."""
        execution = PreviewExecution(
            start_time=datetime(2025, 6, 15, 21, 0, 0, tzinfo=UTC),
            end_time=datetime(2025, 6, 15, 21, 0, 0, tzinfo=UTC),
            routine_id="empty",
            routine_name="Empty Pattern",
            trigger_info="fixed",
            actions=[],
        )

        result = execution.to_dict()

        assert result["actions"] == []


class TestPreviewResult:
    """Tests for PreviewResult dataclass."""

    def test_preview_result_to_dict(self):
        """Test PreviewResult serialization."""
        result = PreviewResult(
            schedule_id="test-schedule",
            schedule_name="Test Schedule",
            preview_start=datetime(2025, 6, 15, 0, 0, 0, tzinfo=UTC),
            preview_end=datetime(2025, 6, 21, 23, 59, 59, tzinfo=UTC),
            executions=[],
            conflicts=[],
            moon_phases={"2025-06-15": {"phase": "full", "illumination": 1.0}},
            total_actions=0,
            total_executions=0,
        )

        output = result.to_dict()

        assert output["schedule_id"] == "test-schedule"
        assert output["schedule_name"] == "Test Schedule"
        assert output["total_actions"] == 0
        assert output["total_executions"] == 0
        assert "moon_phases" in output
        assert "generated_at" in output
        assert "warnings" in output
        assert output["warnings"] == []

    def test_preview_result_with_warnings(self):
        """Test PreviewResult with warnings list."""
        result = PreviewResult(
            schedule_id="test-schedule",
            schedule_name="Test Schedule",
            preview_start=datetime(2025, 6, 15, 0, 0, 0, tzinfo=UTC),
            preview_end=datetime(2025, 6, 21, 23, 59, 59, tzinfo=UTC),
            executions=[],
            conflicts=[],
            moon_phases={},
            total_actions=0,
            total_executions=0,
            warnings=["Warning 1", "Warning 2"],
        )

        output = result.to_dict()

        assert output["warnings"] == ["Warning 1", "Warning 2"]

        # Test roundtrip
        restored = PreviewResult.from_dict(output)
        assert restored.warnings == ["Warning 1", "Warning 2"]

    def test_preview_result_empty_executions(self):
        """Test PreviewResult with no executions."""
        result = PreviewResult(
            schedule_id="empty",
            schedule_name="Empty Schedule",
            preview_start=datetime(2025, 6, 15, 0, 0, 0, tzinfo=UTC),
            preview_end=datetime(2025, 6, 21, 23, 59, 59, tzinfo=UTC),
            executions=[],
            conflicts=[],
            moon_phases={},
            total_actions=0,
            total_executions=0,
        )

        output = result.to_dict()

        assert output["executions"] == []
        assert output["conflicts"] == []
        assert output["moon_phases"] == {}

    def test_preview_result_from_dict(self):
        """Test PreviewResult deserialization."""
        data = {
            "schedule_id": "test-schedule",
            "schedule_name": "Test Schedule",
            "preview_start": "2025-06-15T00:00:00+00:00",
            "preview_end": "2025-06-21T23:59:59+00:00",
            "executions": [
                {
                    "start_time": "2025-06-15T21:00:00+00:00",
                    "end_time": "2025-06-15T21:15:00+00:00",
                    "routine_id": "uv-cycle",
                    "routine_name": "UV Capture Cycle",
                    "trigger_info": "interval:60m",
                    "actions": [
                        {
                            "time": "2025-06-15T21:00:00+00:00",
                            "action_name": "attract_on",
                            "action_type": "gpio",
                            "offset_minutes": 0,
                            "description": "Turn on UV lights",
                        }
                    ],
                }
            ],
            "conflicts": [],
            "moon_phases": {"2025-06-15": {"phase": "full", "illumination": 1.0}},
            "total_actions": 1,
            "total_executions": 1,
            "generated_at": "2025-06-15T12:00:00+00:00",
        }

        result = PreviewResult.from_dict(data)

        assert result.schedule_id == "test-schedule"
        assert result.schedule_name == "Test Schedule"
        assert result.preview_start == datetime(2025, 6, 15, 0, 0, 0, tzinfo=UTC)
        assert result.preview_end == datetime(2025, 6, 21, 23, 59, 59, tzinfo=UTC)
        assert result.total_actions == 1
        assert result.total_executions == 1
        assert len(result.executions) == 1
        assert result.executions[0].routine_id == "uv-cycle"
        assert len(result.executions[0].actions) == 1
        assert result.executions[0].actions[0].action_name == "attract_on"
        assert result.moon_phases == {"2025-06-15": {"phase": "full", "illumination": 1.0}}

    def test_preview_result_roundtrip(self):
        """Test PreviewResult serialization roundtrip."""
        original = PreviewResult(
            schedule_id="roundtrip-test",
            schedule_name="Roundtrip Test Schedule",
            preview_start=datetime(2025, 6, 15, 0, 0, 0, tzinfo=UTC),
            preview_end=datetime(2025, 6, 21, 23, 59, 59, tzinfo=UTC),
            executions=[
                PreviewExecution(
                    start_time=datetime(2025, 6, 15, 21, 0, 0, tzinfo=UTC),
                    end_time=datetime(2025, 6, 15, 21, 15, 0, tzinfo=UTC),
                    routine_id="test-pattern",
                    routine_name="Test Pattern",
                    trigger_info="interval:30m",
                    actions=[
                        ActionExecution(
                            time=datetime(2025, 6, 15, 21, 0, 0, tzinfo=UTC),
                            action_name="takephoto",
                            action_type="camera",
                            offset_minutes=0,
                            description="Capture photo",
                        )
                    ],
                )
            ],
            conflicts=[],
            moon_phases={"2025-06-15": {"phase": "waxing_gibbous", "illumination": 0.75}},
            total_actions=1,
            total_executions=1,
            generated_at=datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC),
        )

        restored = PreviewResult.from_dict(original.to_dict())

        assert restored.schedule_id == original.schedule_id
        assert restored.schedule_name == original.schedule_name
        assert restored.preview_start == original.preview_start
        assert restored.preview_end == original.preview_end
        assert restored.total_actions == original.total_actions
        assert restored.total_executions == original.total_executions
        assert restored.generated_at == original.generated_at
        assert len(restored.executions) == len(original.executions)
        assert restored.executions[0].routine_id == original.executions[0].routine_id
        assert len(restored.executions[0].actions) == len(original.executions[0].actions)


# ============================================================================
# B. Trigger Type Tests (5 tests)
# ============================================================================


class TestTriggerInfo:
    """Tests for trigger info generation."""

    def test_interval_trigger_info(self, sample_interval_schedule):
        """Test interval trigger info generation."""
        info = _get_trigger_info(sample_interval_schedule)

        assert "interval:60m" in info
        assert "21:00" in info
        assert "05:00" in info

    def test_solar_trigger_info_positive_offset(self, sample_solar_schedule):
        """Test solar trigger info with positive offset."""
        info = _get_trigger_info(sample_solar_schedule)

        assert info == "sunset+30"

    def test_solar_trigger_info_negative_offset(self, sample_actions):
        """Test solar trigger info with negative offset (Schema 3.0)."""
        trigger = SolarTrigger(
            solar_event="sunrise",
            offset_minutes=-15,
        )
        routine = Routine(
            routine_id="test-routine",
            name="Test Routine",
            trigger=trigger,
            actions=sample_actions,
        )
        schedule = Schedule(
            schedule_id="test",
            name="Test",
            routines=[routine],
        )

        info = _get_trigger_info(schedule)

        assert info == "sunrise-15"

    def test_moon_phase_trigger_info(self, sample_moon_schedule):
        """Test moon phase trigger info generation."""
        info = _get_trigger_info(sample_moon_schedule)

        assert "moon:full" in info
        assert "+2d" in info

    def test_fixed_time_trigger_info(self, sample_fixed_time_schedule):
        """Test fixed time trigger info generation."""
        info = _get_trigger_info(sample_fixed_time_schedule)

        assert info == "daily:21:00"

    def test_sensor_trigger_info(self, sample_sensor_schedule):
        """Test sensor trigger info generation."""
        info = _get_trigger_info(sample_sensor_schedule)

        assert info == "sensor:motion"


# ============================================================================
# C. Action Expansion Tests (4 tests)
# ============================================================================


class TestActionExpansion:
    """Tests for action expansion (Schema 3.0 - uses Routine instead of EventPattern)."""

    def test_expand_single_action(self):
        """Test expanding single action routine."""
        routine = Routine(
            routine_id="single",
            name="Single Action",
            trigger=FixedTimeTrigger(time="21:00"),
            actions=[
                Action(
                    action_type="camera",
                    action_name="takephoto",
                    offset_minutes=0,
                ),
            ],
        )

        trigger_time = datetime(2025, 6, 15, 21, 0, 0, tzinfo=UTC)
        actions = _expand_actions(routine, trigger_time)

        assert len(actions) == 1
        assert actions[0].time == trigger_time
        assert actions[0].action_name == "takephoto"
        assert actions[0].offset_minutes == 0

    def test_expand_multiple_actions(self, sample_routine):
        """Test expanding multi-action routine."""
        trigger_time = datetime(2025, 6, 15, 21, 0, 0, tzinfo=UTC)
        actions = _expand_actions(sample_routine, trigger_time)

        assert len(actions) == 3

        # First action at t+0
        assert actions[0].time == trigger_time
        assert actions[0].action_name == "attract_on"

        # Second action at t+5
        assert actions[1].time == trigger_time + timedelta(minutes=5)
        assert actions[1].action_name == "takephoto"

        # Third action at t+15
        assert actions[2].time == trigger_time + timedelta(minutes=15)
        assert actions[2].action_name == "attract_off"

    def test_expand_actions_sorted_by_time(self):
        """Test that expanded actions are sorted by time."""
        # Create routine with unsorted offsets
        routine = Routine(
            routine_id="unsorted",
            name="Unsorted",
            trigger=FixedTimeTrigger(time="21:00"),
            actions=[
                Action(
                    action_type="gpio",
                    action_name="action_c",
                    offset_minutes=15,
                ),
                Action(
                    action_type="gpio",
                    action_name="action_a",
                    offset_minutes=0,
                ),
                Action(
                    action_type="gpio",
                    action_name="action_b",
                    offset_minutes=5,
                ),
            ],
        )

        trigger_time = datetime(2025, 6, 15, 21, 0, 0, tzinfo=UTC)
        actions = _expand_actions(routine, trigger_time)

        # Should be sorted by time
        assert actions[0].action_name == "action_a"
        assert actions[1].action_name == "action_b"
        assert actions[2].action_name == "action_c"

    def test_expand_actions_preserves_metadata(self, sample_routine):
        """Test that action expansion preserves description."""
        trigger_time = datetime(2025, 6, 15, 21, 0, 0, tzinfo=UTC)
        actions = _expand_actions(sample_routine, trigger_time)

        # Check first action has description
        assert actions[0].description == "Turn on UV attract lights"
        assert actions[0].action_type == "gpio"


# ============================================================================
# D. Moon Phase Integration Tests (3 tests)
# ============================================================================


class TestMoonPhaseIntegration:
    """Tests for moon phase integration."""

    def test_moon_phases_dict_structure(self):
        """Test moon phases dictionary structure."""
        start = date(2025, 6, 15)
        end = date(2025, 6, 17)

        phases = _get_moon_phases_dict(start, end)

        # Should have 3 days
        assert len(phases) == 3
        assert "2025-06-15" in phases
        assert "2025-06-16" in phases
        assert "2025-06-17" in phases

    def test_moon_phases_contain_required_fields(self):
        """Test moon phase entries contain required fields."""
        start = date(2025, 6, 15)
        end = date(2025, 6, 15)

        phases = _get_moon_phases_dict(start, end)
        phase_info = phases["2025-06-15"]

        assert "date" in phase_info
        assert "phase" in phase_info
        assert "illumination" in phase_info

    def test_moon_phases_illumination_range(self):
        """Test illumination values are in valid range."""
        start = date(2025, 6, 1)
        end = date(2025, 6, 30)

        phases = _get_moon_phases_dict(start, end)

        for date_str, phase_info in phases.items():
            illumination = phase_info["illumination"]
            assert 0.0 <= illumination <= 1.0, f"Invalid illumination for {date_str}"


# ============================================================================
# E. Conflict Integration Tests (3 tests)
# ============================================================================


class TestConflictIntegration:
    """Tests for conflict detection integration."""

    @patch("webui.backend.lib.schedule_preview.detect_conflicts")
    @patch("webui.backend.lib.schedule_preview.generate_routine_executions")
    def test_conflicts_included_in_result(
        self, mock_gen_exec, mock_detect, sample_interval_schedule
    ):
        """Test conflicts are included in preview result."""
        # Mock execution generation
        mock_gen_exec.return_value = []

        # Mock conflict detection with a conflict
        mock_conflict = MagicMock()
        mock_conflict.to_dict.return_value = {
            "conflict_type": "time_overlap",
            "severity": "warning",
        }

        mock_report = MagicMock()
        mock_report.conflicts = [mock_conflict]
        mock_detect.return_value = mock_report

        result = generate_preview(sample_interval_schedule, days=1)

        assert len(result.conflicts) == 1

    @patch("webui.backend.lib.schedule_preview.detect_conflicts")
    @patch("webui.backend.lib.schedule_preview.generate_routine_executions")
    def test_no_conflicts_empty_list(self, mock_gen_exec, mock_detect, sample_interval_schedule):
        """Test empty conflict list when no conflicts."""
        mock_gen_exec.return_value = []

        mock_report = MagicMock()
        mock_report.conflicts = []
        mock_detect.return_value = mock_report

        result = generate_preview(sample_interval_schedule, days=1)

        assert result.conflicts == []

    @patch("webui.backend.lib.schedule_preview.detect_conflicts")
    @patch("webui.backend.lib.schedule_preview.generate_routine_executions")
    def test_conflict_report_called_with_correct_params(
        self, mock_gen_exec, mock_detect, sample_interval_schedule
    ):
        """Test detect_conflicts called with correct parameters."""
        mock_gen_exec.return_value = []

        mock_report = MagicMock()
        mock_report.conflicts = []
        mock_detect.return_value = mock_report

        generate_preview(
            sample_interval_schedule,
            days=14,
            latitude=35.0,
            longitude=-80.0,
            timezone_name="America/New_York",
        )

        mock_detect.assert_called_once()
        call_args = mock_detect.call_args
        assert call_args.kwargs["preview_days"] == 14
        assert call_args.kwargs["latitude"] == 35.0
        assert call_args.kwargs["longitude"] == -80.0
        assert call_args.kwargs["timezone_name"] == "America/New_York"


# ============================================================================
# F. Edge Case Tests (5 tests)
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    def test_preview_days_validation_min(self):
        """Test minimum preview days validation."""
        valid, error = validate_preview_days(MIN_PREVIEW_DAYS)
        assert valid is True
        assert error is None

    def test_preview_days_validation_max(self):
        """Test maximum preview days validation."""
        valid, error = validate_preview_days(MAX_PREVIEW_DAYS)
        assert valid is True
        assert error is None

    def test_preview_days_validation_below_min(self):
        """Test below minimum preview days rejected."""
        valid, error = validate_preview_days(0)
        assert valid is False
        assert "at least" in error

    def test_preview_days_validation_above_max(self):
        """Test above maximum preview days rejected."""
        valid, error = validate_preview_days(91)
        assert valid is False
        assert "at most" in error

    def test_generate_preview_invalid_days_raises(self, sample_interval_schedule):
        """Test generate_preview raises for invalid days."""
        with pytest.raises(ValueError) as excinfo:
            generate_preview(sample_interval_schedule, days=0)

        assert "between" in str(excinfo.value)

    def test_coordinates_validation_valid(self):
        """Test valid coordinates pass validation."""
        valid, error = validate_coordinates(35.0, -80.0)
        assert valid is True
        assert error is None

    def test_coordinates_validation_invalid_latitude(self):
        """Test invalid latitude rejected."""
        valid, error = validate_coordinates(91.0, -80.0)
        assert valid is False
        assert "Latitude" in error

    def test_coordinates_validation_invalid_longitude(self):
        """Test invalid longitude rejected."""
        valid, error = validate_coordinates(35.0, 181.0)
        assert valid is False
        assert "Longitude" in error

    def test_timezone_validation_valid_utc(self):
        """Test valid UTC timezone passes validation."""
        valid, error = validate_timezone("UTC")
        assert valid is True
        assert error is None

    def test_timezone_validation_valid_iana(self):
        """Test valid IANA timezone passes validation."""
        valid, error = validate_timezone("America/New_York")
        assert valid is True
        assert error is None

    def test_timezone_validation_valid_europe(self):
        """Test valid European timezone passes validation."""
        valid, error = validate_timezone("Europe/London")
        assert valid is True
        assert error is None

    def test_timezone_validation_invalid_name(self):
        """Test invalid timezone name rejected."""
        valid, error = validate_timezone("Invalid/Timezone")
        assert valid is False
        assert "Invalid timezone" in error
        assert "IANA" in error

    def test_timezone_validation_empty_string(self):
        """Test empty timezone string rejected."""
        valid, error = validate_timezone("")
        assert valid is False
        assert "empty" in error

    def test_timezone_validation_gibberish(self):
        """Test gibberish timezone rejected."""
        valid, error = validate_timezone("not-a-timezone")
        assert valid is False
        assert "Invalid timezone" in error

    @patch.dict("sys.modules", {"pytz": None})
    def test_timezone_validation_pytz_not_installed(self):
        """Test graceful handling when pytz is not installed."""
        # We need to patch the import inside the function
        import sys

        # Save original pytz module
        original_pytz = sys.modules.get("pytz")

        # Remove pytz from modules to simulate it not being installed
        if "pytz" in sys.modules:
            del sys.modules["pytz"]

        # Also need to patch builtins to make import fail
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pytz":
                raise ImportError("No module named 'pytz'")
            return original_import(name, *args, **kwargs)

        builtins.__import__ = mock_import

        try:
            valid, error = validate_timezone("America/New_York")
            assert valid is False
            assert "pytz library required" in error
        finally:
            # Restore original import and pytz module
            builtins.__import__ = original_import
            if original_pytz is not None:
                sys.modules["pytz"] = original_pytz


# ============================================================================
# G. Location Fallback Tests (2 tests)
# ============================================================================


class TestLocationFallback:
    """Tests for location fallback behavior."""

    @patch("webui.backend.lib.schedule_preview._get_default_location")
    @patch("webui.backend.lib.schedule_preview.detect_conflicts")
    @patch("webui.backend.lib.schedule_preview.generate_routine_executions")
    def test_location_from_params_priority(
        self, mock_gen_exec, mock_detect, mock_default_loc, sample_interval_schedule
    ):
        """Test explicit params override controls.txt location."""
        mock_default_loc.return_value = (10.0, 20.0)  # Default location
        mock_gen_exec.return_value = []

        mock_report = MagicMock()
        mock_report.conflicts = []
        mock_detect.return_value = mock_report

        # Call with explicit params
        generate_preview(
            sample_interval_schedule,
            days=1,
            latitude=35.0,
            longitude=-80.0,
        )

        # generate_routine_executions should be called with explicit params
        call_args = mock_gen_exec.call_args
        assert call_args.kwargs["latitude"] == 35.0
        assert call_args.kwargs["longitude"] == -80.0

    @patch("webui.backend.lib.schedule_preview._get_default_location")
    @patch("webui.backend.lib.schedule_preview.detect_conflicts")
    @patch("webui.backend.lib.schedule_preview.generate_routine_executions")
    def test_location_from_controls_fallback(
        self, mock_gen_exec, mock_detect, mock_default_loc, sample_interval_schedule
    ):
        """Test controls.txt location used when params None."""
        mock_default_loc.return_value = (10.0, 20.0)  # From controls.txt
        mock_gen_exec.return_value = []

        mock_report = MagicMock()
        mock_report.conflicts = []
        mock_detect.return_value = mock_report

        # Call without explicit params
        generate_preview(sample_interval_schedule, days=1)

        # generate_routine_executions should be called with default location
        call_args = mock_gen_exec.call_args
        assert call_args.kwargs["latitude"] == 10.0
        assert call_args.kwargs["longitude"] == 20.0

    @patch("webui.backend.lib.schedule_preview._get_default_location")
    @patch("webui.backend.lib.schedule_preview.detect_conflicts")
    @patch("webui.backend.lib.schedule_preview.generate_routine_executions")
    def test_default_location_warning_included(
        self, mock_gen_exec, mock_detect, mock_default_loc, sample_interval_schedule
    ):
        """Test that default location (0, 0) generates a warning in result."""
        # Simulate no GPS data available - returns None
        mock_default_loc.return_value = (None, None)
        mock_gen_exec.return_value = []

        mock_report = MagicMock()
        mock_report.conflicts = []
        mock_detect.return_value = mock_report

        # Call without explicit params - should use (0, 0) default
        result = generate_preview(sample_interval_schedule, days=1)

        # Should have warning about default location
        assert len(result.warnings) == 1
        assert "default location (0, 0)" in result.warnings[0]
        assert "Solar-based triggers may be inaccurate" in result.warnings[0]

    @patch("webui.backend.lib.schedule_preview._get_default_location")
    @patch("webui.backend.lib.schedule_preview.detect_conflicts")
    @patch("webui.backend.lib.schedule_preview.generate_routine_executions")
    def test_explicit_location_no_warning(
        self, mock_gen_exec, mock_detect, mock_default_loc, sample_interval_schedule
    ):
        """Test that explicit coordinates don't generate warning."""
        mock_default_loc.return_value = (None, None)
        mock_gen_exec.return_value = []

        mock_report = MagicMock()
        mock_report.conflicts = []
        mock_detect.return_value = mock_report

        # Call with explicit coordinates
        result = generate_preview(
            sample_interval_schedule,
            days=1,
            latitude=35.0,
            longitude=-80.0,
        )

        # Should have no warnings
        assert result.warnings == []

    @patch("webui.backend.lib.schedule_preview._get_default_location")
    @patch("webui.backend.lib.schedule_preview.detect_conflicts")
    @patch("webui.backend.lib.schedule_preview.generate_routine_executions")
    def test_controls_location_no_warning(
        self, mock_gen_exec, mock_detect, mock_default_loc, sample_interval_schedule
    ):
        """Test that valid GPS from controls.txt doesn't generate warning."""
        # Simulate valid GPS data from controls.txt
        mock_default_loc.return_value = (35.9606, -83.9207)
        mock_gen_exec.return_value = []

        mock_report = MagicMock()
        mock_report.conflicts = []
        mock_detect.return_value = mock_report

        # Call without explicit params - should use GPS from controls.txt
        result = generate_preview(sample_interval_schedule, days=1)

        # Should have no warnings
        assert result.warnings == []

    @patch("webui.backend.lib.schedule_preview._get_default_location")
    @patch("webui.backend.lib.schedule_preview.detect_conflicts")
    @patch("webui.backend.lib.schedule_preview.generate_routine_executions")
    def test_sensor_trigger_warning_included(
        self, mock_gen_exec, mock_detect, mock_default_loc, sample_sensor_schedule
    ):
        """Test that sensor triggers generate a warning about unpredictable execution."""
        mock_default_loc.return_value = (35.0, -80.0)
        mock_gen_exec.return_value = []

        mock_report = MagicMock()
        mock_report.conflicts = []
        mock_detect.return_value = mock_report

        result = generate_preview(sample_sensor_schedule, days=7)

        # Should have warning about sensor triggers
        assert len(result.warnings) == 1
        assert "Sensor triggers are event-driven" in result.warnings[0]
        assert "cannot be previewed" in result.warnings[0]
        assert result.total_executions == 0


# ============================================================================
# H. Integration Tests (2 tests)
# ============================================================================


class TestPreviewGeneration:
    """Integration tests for full preview generation."""

    @patch("webui.backend.lib.schedule_preview.detect_conflicts")
    @patch("webui.backend.lib.schedule_preview.generate_routine_executions")
    def test_generate_preview_returns_result(
        self, mock_gen_exec, mock_detect, sample_interval_schedule
    ):
        """Test generate_preview returns valid PreviewResult."""
        mock_gen_exec.return_value = []

        mock_report = MagicMock()
        mock_report.conflicts = []
        mock_detect.return_value = mock_report

        result = generate_preview(sample_interval_schedule, days=7)

        assert isinstance(result, PreviewResult)
        assert result.schedule_id == sample_interval_schedule.schedule_id
        assert result.schedule_name == sample_interval_schedule.name
        assert result.total_executions == 0
        assert result.total_actions == 0

    @patch("webui.backend.lib.schedule_preview.detect_conflicts")
    @patch("webui.backend.lib.schedule_preview.generate_routine_executions")
    def test_generate_preview_counts_actions(
        self, mock_gen_exec, mock_detect, sample_interval_schedule
    ):
        """Test generate_preview correctly counts actions."""
        from webui.backend.lib.schedule_conflict import RoutineExecution

        # Mock 2 routine executions (routine_id is routine_id in Schema 3.0)
        mock_exec_1 = RoutineExecution(
            routine_id="uv-capture-cycle",
            routine_name="UV Capture Cycle",
            start_time=datetime(2025, 6, 15, 21, 0, 0, tzinfo=UTC),
            end_time=datetime(2025, 6, 15, 21, 15, 0, tzinfo=UTC),
            resource_usages=[],
        )
        mock_exec_2 = RoutineExecution(
            routine_id="uv-capture-cycle",
            routine_name="UV Capture Cycle",
            start_time=datetime(2025, 6, 15, 22, 0, 0, tzinfo=UTC),
            end_time=datetime(2025, 6, 15, 22, 15, 0, tzinfo=UTC),
            resource_usages=[],
        )
        mock_gen_exec.return_value = [mock_exec_1, mock_exec_2]

        mock_report = MagicMock()
        mock_report.conflicts = []
        mock_detect.return_value = mock_report

        result = generate_preview(sample_interval_schedule, days=1)

        assert result.total_executions == 2
        # Each execution has 3 actions (from routine in sample_interval_schedule)
        assert result.total_actions == 6

    @patch("webui.backend.lib.schedule_preview.detect_conflicts")
    @patch("webui.backend.lib.schedule_preview.generate_routine_executions")
    def test_preview_boundaries_use_timezone(
        self, mock_gen_exec, mock_detect, sample_interval_schedule
    ):
        """Test that preview_start/end respect the timezone parameter."""
        mock_gen_exec.return_value = []

        mock_report = MagicMock()
        mock_report.conflicts = []
        mock_detect.return_value = mock_report

        # Generate preview with New York timezone (UTC-5 or UTC-4 depending on DST)
        result = generate_preview(
            sample_interval_schedule,
            days=1,
            latitude=40.7128,
            longitude=-74.0060,
            timezone_name="America/New_York",
        )

        # preview_start should be midnight in New York, converted to UTC
        # In June (DST), New York is UTC-4, so midnight NY = 04:00 UTC
        # The exact hour depends on the current date, but it should NOT be 00:00 UTC
        # unless the timezone is UTC
        assert result.preview_start.tzinfo == UTC
        assert result.preview_end.tzinfo == UTC

        # Generate same preview with UTC
        result_utc = generate_preview(
            sample_interval_schedule,
            days=1,
            latitude=40.7128,
            longitude=-74.0060,
            timezone_name="UTC",
        )

        # UTC preview should have 00:00:00 start time
        assert result_utc.preview_start.hour == 0
        assert result_utc.preview_start.minute == 0

    @patch("webui.backend.lib.schedule_preview.detect_conflicts")
    @patch("webui.backend.lib.schedule_preview.generate_routine_executions")
    def test_preview_boundaries_timezone_offset(
        self, mock_gen_exec, mock_detect, sample_interval_schedule
    ):
        """Test timezone offset is correctly applied to preview boundaries."""
        mock_gen_exec.return_value = []

        mock_report = MagicMock()
        mock_report.conflicts = []
        mock_detect.return_value = mock_report

        # Use a fixed-offset timezone for predictable testing
        # Asia/Tokyo is UTC+9 (no DST)
        result = generate_preview(
            sample_interval_schedule,
            days=1,
            latitude=35.6762,
            longitude=139.6503,
            timezone_name="Asia/Tokyo",
        )

        # Midnight in Tokyo (UTC+9) = 15:00 previous day in UTC
        # So preview_start.hour should be 15 (from previous day)
        # Actually it's the same date in the preview, so it wraps
        assert result.preview_start.tzinfo == UTC
        # The key assertion: midnight Tokyo != midnight UTC
        # Midnight Tokyo = 15:00 UTC previous day
        # So if start_date is today, preview_start in UTC is yesterday 15:00
        assert result.preview_start.hour == 15  # 00:00 Tokyo = 15:00 UTC (prev day)


# ============================================================================
# Parse and Validate Tests
# ============================================================================


@pytest.mark.skipif(not IMPLEMENTATION_EXISTS, reason="Implementation not found")
class TestParseAndValidate:
    """Tests for combined parse+validate functions."""

    def test_parse_days_valid(self):
        """Test valid days string parses correctly."""
        days, error = parse_and_validate_days("7")
        assert days == 7
        assert error is None

    def test_parse_days_valid_min(self):
        """Test minimum valid days value."""
        days, error = parse_and_validate_days(str(MIN_PREVIEW_DAYS))
        assert days == MIN_PREVIEW_DAYS
        assert error is None

    def test_parse_days_valid_max(self):
        """Test maximum valid days value."""
        days, error = parse_and_validate_days(str(MAX_PREVIEW_DAYS))
        assert days == MAX_PREVIEW_DAYS
        assert error is None

    def test_parse_days_invalid_format(self):
        """Test non-integer string returns error."""
        days, error = parse_and_validate_days("abc")
        assert days is None
        assert "Expected integer" in error

    def test_parse_days_invalid_float(self):
        """Test float string returns error."""
        days, error = parse_and_validate_days("7.5")
        assert days is None
        assert "Expected integer" in error

    def test_parse_days_out_of_range_low(self):
        """Test below minimum returns validation error."""
        days, error = parse_and_validate_days("0")
        assert days is None
        assert "at least" in error

    def test_parse_days_out_of_range_high(self):
        """Test above maximum returns validation error."""
        days, error = parse_and_validate_days("100")
        assert days is None
        assert "at most" in error

    def test_parse_coordinate_valid(self):
        """Test valid coordinate string parses correctly."""
        value, error = parse_and_validate_coordinate("35.5", "lat")
        assert value == 35.5
        assert error is None

    def test_parse_coordinate_valid_negative(self):
        """Test negative coordinate parses correctly."""
        value, error = parse_and_validate_coordinate("-122.4", "lon")
        assert value == -122.4
        assert error is None

    def test_parse_coordinate_valid_integer(self):
        """Test integer string parses correctly."""
        value, error = parse_and_validate_coordinate("45", "lat")
        assert value == 45.0
        assert error is None

    def test_parse_coordinate_none(self):
        """Test None input returns None without error."""
        value, error = parse_and_validate_coordinate(None, "lat")
        assert value is None
        assert error is None

    def test_parse_coordinate_invalid(self):
        """Test non-numeric string returns error."""
        value, error = parse_and_validate_coordinate("abc", "lat")
        assert value is None
        assert "Expected number" in error
        assert "lat" in error

    def test_parse_coordinate_invalid_with_name(self):
        """Test error message includes parameter name."""
        value, error = parse_and_validate_coordinate("xyz", "lon")
        assert value is None
        assert "lon" in error

"""
Unit tests for schedule schema dataclasses.

Tests the core schedule schema including:
- PatternAction, EventPattern dataclasses
- TimeWindow and trigger dataclasses (Interval, Solar, MoonPhase, FixedTime, Sensor)
- Schedule dataclass with embedded event patterns
- Validation functions for all types

Coverage target: 85%+
Test count target: 40+

Issue #208 - Scheduler Phase 1: Schedule Schema
"""

import json
import re
import uuid
from datetime import datetime

import pytest

# Check if implementation exists for graceful skipping during TDD
try:
    from webui.backend.lib.schedule_schema import (
        # Constants
        ACTION_TYPES,
        GPIO_ACTIONS,
        MAX_ACTIONS_PER_PATTERN,
        MAX_DESCRIPTION_LENGTH,
        MAX_OFFSET_MINUTES,
        MAX_PATTERN_NAME_LENGTH,
        MAX_PATTERNS_PER_SCHEDULE,
        MOON_PHASES,
        SCHEDULE_SCHEMA_VERSION,
        SENSOR_COMPARISONS,
        SENSOR_TYPES,
        SOLAR_EVENTS,
        SUPPORTED_VERSIONS,
        TRIGGER_TYPES,
        # Dataclasses
        EventPattern,
        FixedTimeTrigger,
        IntervalTrigger,
        MoonPhaseTrigger,
        PatternAction,
        Schedule,
        ScheduleValidationError,
        SensorTrigger,
        SolarTrigger,
        TimeWindow,
        # Validation functions
        validate_event_pattern,
        validate_fixed_time_trigger,
        validate_interval_trigger,
        validate_moon_phase_trigger,
        validate_pattern_action,
        validate_schedule,
        validate_sensor_trigger,
        validate_solar_trigger,
        validate_time_window,
    )

    IMPLEMENTATION_EXISTS = True
except ImportError:
    IMPLEMENTATION_EXISTS = False


pytestmark = pytest.mark.skipif(
    not IMPLEMENTATION_EXISTS,
    reason="schedule_schema.py not yet implemented",
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_pattern_action():
    """Create a sample PatternAction for testing."""
    return PatternAction(
        action_type="gpio",
        action_name="attract_on",
        offset_minutes=0,
        parameters={},
        description="Turn on attract lights",
    )


@pytest.fixture
def sample_pattern_action_camera():
    """Create a camera PatternAction for testing."""
    return PatternAction(
        action_type="camera",
        action_name="takephoto",
        offset_minutes=5,
        parameters={"hdr": True},
        description="Take photo with HDR",
    )


@pytest.fixture
def sample_event_pattern(sample_pattern_action, sample_pattern_action_camera):
    """Create a sample EventPattern for testing."""
    return EventPattern(
        pattern_id="test-pattern-id",
        name="UV Capture Cycle",
        description="Turn on lights, take photo, turn off lights",
        actions=[
            sample_pattern_action,
            sample_pattern_action_camera,
            PatternAction(
                action_type="gpio",
                action_name="attract_off",
                offset_minutes=15,
            ),
        ],
        category="user",
        tags=["night", "moths"],
    )


@pytest.fixture
def sample_time_window():
    """Create a sample TimeWindow for testing."""
    return TimeWindow(
        start_time="21:00",
        end_time="05:00",
        start_offset_minutes=0,
        end_offset_minutes=0,
    )


@pytest.fixture
def sample_time_window_solar():
    """Create a solar-based TimeWindow for testing."""
    return TimeWindow(
        start_time="sunset",
        end_time="sunrise",
        start_offset_minutes=30,
        end_offset_minutes=-30,
    )


@pytest.fixture
def sample_interval_trigger(sample_time_window):
    """Create a sample IntervalTrigger for testing."""
    return IntervalTrigger(
        interval_minutes=60,
        time_window=sample_time_window,
        days_of_week=None,
    )


@pytest.fixture
def sample_solar_trigger():
    """Create a sample SolarTrigger for testing."""
    return SolarTrigger(
        solar_event="sunset",
        offset_minutes=30,
        days_of_week=[0, 1, 2, 3, 4],
    )


@pytest.fixture
def sample_moon_phase_trigger(sample_time_window):
    """Create a sample MoonPhaseTrigger for testing."""
    return MoonPhaseTrigger(
        phases=["full", "waxing_gibbous"],
        offset_days=2,
        time_window=sample_time_window,
    )


@pytest.fixture
def sample_fixed_time_trigger():
    """Create a sample FixedTimeTrigger for testing."""
    return FixedTimeTrigger(
        time="21:00",
        days_of_week=[0, 1, 2, 3, 4, 5, 6],
    )


@pytest.fixture
def sample_sensor_trigger(sample_time_window):
    """Create a sample SensorTrigger for testing."""
    return SensorTrigger(
        sensor_type="motion",
        threshold=0.0,
        comparison="gt",
        cooldown_minutes=5,
        time_window=sample_time_window,
    )


@pytest.fixture
def sample_schedule(sample_event_pattern, sample_interval_trigger):
    """Create a sample Schedule for testing."""
    return Schedule(
        schedule_id="test-schedule-id",
        name="Nightly Moth Survey",
        description="Hourly captures from dusk to dawn",
        event_patterns=[sample_event_pattern],
        trigger_type="interval",
        interval_trigger=sample_interval_trigger,
        start_date="2024-06-01",
        end_date="2024-08-31",
        deployment_id=None,
        create_deployment=False,
        enabled=True,
        is_active=False,
    )


# =============================================================================
# CONSTANTS TESTS
# =============================================================================


class TestScheduleSchemaConstants:
    """Test schema constants are defined correctly."""

    def test_schema_version_defined(self):
        """SCHEDULE_SCHEMA_VERSION should be defined."""
        assert SCHEDULE_SCHEMA_VERSION == "2.0"

    def test_supported_versions_includes_current(self):
        """SUPPORTED_VERSIONS should include current version."""
        assert SCHEDULE_SCHEMA_VERSION in SUPPORTED_VERSIONS

    def test_action_types_defined(self):
        """ACTION_TYPES should include all expected types."""
        expected = ["gpio", "camera", "gps_sync", "service"]
        assert ACTION_TYPES == expected

    def test_gpio_actions_defined(self):
        """GPIO_ACTIONS should include all expected actions."""
        expected = ["attract_on", "attract_off", "flash_on", "flash_off"]
        assert GPIO_ACTIONS == expected

    def test_trigger_types_defined(self):
        """TRIGGER_TYPES should include all expected types."""
        expected = ["interval", "solar", "moon_phase", "fixed_time", "sensor"]
        assert TRIGGER_TYPES == expected

    def test_moon_phases_defined(self):
        """MOON_PHASES should include all 8 phases."""
        assert len(MOON_PHASES) == 8
        assert "full" in MOON_PHASES
        assert "new" in MOON_PHASES

    def test_solar_events_defined(self):
        """SOLAR_EVENTS should include core events."""
        assert "dawn" in SOLAR_EVENTS
        assert "sunrise" in SOLAR_EVENTS
        assert "sunset" in SOLAR_EVENTS
        assert "dusk" in SOLAR_EVENTS

    def test_sensor_types_defined(self):
        """SENSOR_TYPES should include expected types."""
        expected = ["motion", "light", "temperature"]
        assert SENSOR_TYPES == expected

    def test_sensor_comparisons_defined(self):
        """SENSOR_COMPARISONS should include all operators."""
        expected = ["gt", "lt", "eq", "gte", "lte"]
        assert SENSOR_COMPARISONS == expected

    def test_validation_limits_defined(self):
        """Validation limits should be defined."""
        assert MAX_PATTERN_NAME_LENGTH == 200
        assert MAX_DESCRIPTION_LENGTH == 2000
        assert MAX_ACTIONS_PER_PATTERN == 20
        assert MAX_PATTERNS_PER_SCHEDULE == 10
        assert MAX_OFFSET_MINUTES == 1440


# =============================================================================
# PATTERN ACTION TESTS
# =============================================================================


class TestPatternAction:
    """Test PatternAction dataclass."""

    def test_instantiation_minimal(self):
        """PatternAction can be created with minimal args."""
        action = PatternAction(action_type="gpio", action_name="attract_on")
        assert action.action_type == "gpio"
        assert action.action_name == "attract_on"
        assert action.offset_minutes == 0
        assert action.parameters == {}
        assert action.description == ""

    def test_instantiation_full(self, sample_pattern_action):
        """PatternAction can be created with all args."""
        assert sample_pattern_action.action_type == "gpio"
        assert sample_pattern_action.action_name == "attract_on"
        assert sample_pattern_action.offset_minutes == 0
        assert sample_pattern_action.description == "Turn on attract lights"

    def test_to_dict(self, sample_pattern_action):
        """PatternAction.to_dict() returns correct dict."""
        data = sample_pattern_action.to_dict()
        assert data["action_type"] == "gpio"
        assert data["action_name"] == "attract_on"
        assert data["offset_minutes"] == 0
        assert data["parameters"] == {}
        assert data["description"] == "Turn on attract lights"

    def test_from_dict(self):
        """PatternAction.from_dict() creates instance from dict."""
        data = {
            "action_type": "camera",
            "action_name": "takephoto",
            "offset_minutes": 5,
            "parameters": {"hdr": True},
            "description": "Take HDR photo",
        }
        action = PatternAction.from_dict(data)
        assert action.action_type == "camera"
        assert action.action_name == "takephoto"
        assert action.offset_minutes == 5
        assert action.parameters == {"hdr": True}
        assert action.description == "Take HDR photo"

    def test_round_trip_serialization(self, sample_pattern_action):
        """PatternAction survives JSON round-trip."""
        data = sample_pattern_action.to_dict()
        json_str = json.dumps(data)
        loaded = json.loads(json_str)
        restored = PatternAction.from_dict(loaded)
        assert restored.action_type == sample_pattern_action.action_type
        assert restored.action_name == sample_pattern_action.action_name
        assert restored.offset_minutes == sample_pattern_action.offset_minutes


# =============================================================================
# EVENT PATTERN TESTS
# =============================================================================


class TestEventPattern:
    """Test EventPattern dataclass."""

    def test_instantiation_minimal(self):
        """EventPattern can be created with minimal args."""
        pattern = EventPattern(pattern_id="", name="Test Pattern")
        assert pattern.name == "Test Pattern"
        assert pattern.description == ""
        assert pattern.actions == []
        assert pattern.category == "user"
        assert pattern.tags == []

    def test_uuid_generation_on_empty_id(self):
        """EventPattern generates UUID when pattern_id is empty."""
        pattern = EventPattern(pattern_id="", name="Test")
        # Should be a valid UUID
        uuid.UUID(pattern.pattern_id)

    def test_duration_minutes_computed(self, sample_event_pattern):
        """EventPattern.duration_minutes returns max offset."""
        # Actions have offsets 0, 5, 15
        assert sample_event_pattern.duration_minutes == 15

    def test_duration_minutes_empty_actions(self):
        """EventPattern.duration_minutes is 0 with no actions."""
        pattern = EventPattern(pattern_id="test", name="Empty")
        assert pattern.duration_minutes == 0

    def test_to_dict(self, sample_event_pattern):
        """EventPattern.to_dict() returns correct dict."""
        data = sample_event_pattern.to_dict()
        assert data["pattern_id"] == "test-pattern-id"
        assert data["name"] == "UV Capture Cycle"
        assert len(data["actions"]) == 3
        assert data["category"] == "user"
        assert data["tags"] == ["night", "moths"]
        assert data["duration_minutes"] == 15

    def test_from_dict(self):
        """EventPattern.from_dict() creates instance from dict."""
        data = {
            "pattern_id": "p-123",
            "name": "Test Pattern",
            "description": "A test pattern",
            "actions": [
                {"action_type": "gpio", "action_name": "attract_on", "offset_minutes": 0},
                {"action_type": "camera", "action_name": "takephoto", "offset_minutes": 5},
            ],
            "category": "built-in",
            "tags": ["test"],
        }
        pattern = EventPattern.from_dict(data)
        assert pattern.pattern_id == "p-123"
        assert pattern.name == "Test Pattern"
        assert len(pattern.actions) == 2
        assert pattern.actions[0].action_type == "gpio"
        assert pattern.category == "built-in"

    def test_round_trip_serialization(self, sample_event_pattern):
        """EventPattern survives JSON round-trip."""
        data = sample_event_pattern.to_dict()
        json_str = json.dumps(data)
        loaded = json.loads(json_str)
        restored = EventPattern.from_dict(loaded)
        assert restored.name == sample_event_pattern.name
        assert len(restored.actions) == len(sample_event_pattern.actions)
        assert restored.duration_minutes == sample_event_pattern.duration_minutes


# =============================================================================
# TIME WINDOW TESTS
# =============================================================================


class TestTimeWindow:
    """Test TimeWindow dataclass."""

    def test_instantiation_fixed_times(self, sample_time_window):
        """TimeWindow can be created with fixed times."""
        assert sample_time_window.start_time == "21:00"
        assert sample_time_window.end_time == "05:00"
        assert sample_time_window.start_offset_minutes == 0
        assert sample_time_window.end_offset_minutes == 0

    def test_instantiation_solar_times(self, sample_time_window_solar):
        """TimeWindow can be created with solar events."""
        assert sample_time_window_solar.start_time == "sunset"
        assert sample_time_window_solar.end_time == "sunrise"
        assert sample_time_window_solar.start_offset_minutes == 30
        assert sample_time_window_solar.end_offset_minutes == -30

    def test_to_dict(self, sample_time_window):
        """TimeWindow.to_dict() returns correct dict."""
        data = sample_time_window.to_dict()
        assert data["start_time"] == "21:00"
        assert data["end_time"] == "05:00"
        assert data["start_offset_minutes"] == 0
        assert data["end_offset_minutes"] == 0

    def test_from_dict(self):
        """TimeWindow.from_dict() creates instance from dict."""
        data = {
            "start_time": "sunset",
            "end_time": "06:00",
            "start_offset_minutes": 15,
            "end_offset_minutes": 0,
        }
        window = TimeWindow.from_dict(data)
        assert window.start_time == "sunset"
        assert window.end_time == "06:00"
        assert window.start_offset_minutes == 15

    def test_round_trip_serialization(self, sample_time_window_solar):
        """TimeWindow survives JSON round-trip."""
        data = sample_time_window_solar.to_dict()
        json_str = json.dumps(data)
        loaded = json.loads(json_str)
        restored = TimeWindow.from_dict(loaded)
        assert restored.start_time == sample_time_window_solar.start_time
        assert restored.start_offset_minutes == sample_time_window_solar.start_offset_minutes


# =============================================================================
# INTERVAL TRIGGER TESTS
# =============================================================================


class TestIntervalTrigger:
    """Test IntervalTrigger dataclass."""

    def test_instantiation(self, sample_interval_trigger):
        """IntervalTrigger can be created."""
        assert sample_interval_trigger.interval_minutes == 60
        assert sample_interval_trigger.time_window is not None
        assert sample_interval_trigger.days_of_week is None

    def test_instantiation_with_days(self, sample_time_window):
        """IntervalTrigger can be created with days_of_week."""
        trigger = IntervalTrigger(
            interval_minutes=30,
            time_window=sample_time_window,
            days_of_week=[0, 1, 2, 3, 4],
        )
        assert trigger.days_of_week == [0, 1, 2, 3, 4]

    def test_to_dict(self, sample_interval_trigger):
        """IntervalTrigger.to_dict() returns correct dict."""
        data = sample_interval_trigger.to_dict()
        assert data["interval_minutes"] == 60
        assert "time_window" in data
        assert data["time_window"]["start_time"] == "21:00"

    def test_from_dict(self):
        """IntervalTrigger.from_dict() creates instance from dict."""
        data = {
            "interval_minutes": 120,
            "time_window": {
                "start_time": "22:00",
                "end_time": "04:00",
                "start_offset_minutes": 0,
                "end_offset_minutes": 0,
            },
            "days_of_week": [5, 6],
        }
        trigger = IntervalTrigger.from_dict(data)
        assert trigger.interval_minutes == 120
        assert trigger.time_window.start_time == "22:00"
        assert trigger.days_of_week == [5, 6]


# =============================================================================
# SOLAR TRIGGER TESTS
# =============================================================================


class TestSolarTrigger:
    """Test SolarTrigger dataclass."""

    def test_instantiation(self, sample_solar_trigger):
        """SolarTrigger can be created."""
        assert sample_solar_trigger.solar_event == "sunset"
        assert sample_solar_trigger.offset_minutes == 30
        assert sample_solar_trigger.days_of_week == [0, 1, 2, 3, 4]

    def test_instantiation_minimal(self):
        """SolarTrigger can be created with minimal args."""
        trigger = SolarTrigger(solar_event="sunrise")
        assert trigger.solar_event == "sunrise"
        assert trigger.offset_minutes == 0
        assert trigger.days_of_week is None

    def test_to_dict(self, sample_solar_trigger):
        """SolarTrigger.to_dict() returns correct dict."""
        data = sample_solar_trigger.to_dict()
        assert data["solar_event"] == "sunset"
        assert data["offset_minutes"] == 30
        assert data["days_of_week"] == [0, 1, 2, 3, 4]

    def test_from_dict(self):
        """SolarTrigger.from_dict() creates instance from dict."""
        data = {
            "solar_event": "astronomical_dusk",
            "offset_minutes": -15,
            "days_of_week": None,
        }
        trigger = SolarTrigger.from_dict(data)
        assert trigger.solar_event == "astronomical_dusk"
        assert trigger.offset_minutes == -15


# =============================================================================
# MOON PHASE TRIGGER TESTS
# =============================================================================


class TestMoonPhaseTrigger:
    """Test MoonPhaseTrigger dataclass."""

    def test_instantiation(self, sample_moon_phase_trigger):
        """MoonPhaseTrigger can be created."""
        assert sample_moon_phase_trigger.phases == ["full", "waxing_gibbous"]
        assert sample_moon_phase_trigger.offset_days == 2
        assert sample_moon_phase_trigger.time_window is not None

    def test_instantiation_minimal(self):
        """MoonPhaseTrigger can be created with minimal args."""
        trigger = MoonPhaseTrigger(phases=["full"])
        assert trigger.phases == ["full"]
        assert trigger.offset_days == 0
        assert trigger.time_window is None

    def test_to_dict(self, sample_moon_phase_trigger):
        """MoonPhaseTrigger.to_dict() returns correct dict."""
        data = sample_moon_phase_trigger.to_dict()
        assert data["phases"] == ["full", "waxing_gibbous"]
        assert data["offset_days"] == 2
        assert data["time_window"] is not None

    def test_from_dict(self):
        """MoonPhaseTrigger.from_dict() creates instance from dict."""
        data = {
            "phases": ["new", "waxing_crescent"],
            "offset_days": 1,
            "time_window": None,
        }
        trigger = MoonPhaseTrigger.from_dict(data)
        assert trigger.phases == ["new", "waxing_crescent"]
        assert trigger.offset_days == 1
        assert trigger.time_window is None


# =============================================================================
# FIXED TIME TRIGGER TESTS
# =============================================================================


class TestFixedTimeTrigger:
    """Test FixedTimeTrigger dataclass."""

    def test_instantiation(self, sample_fixed_time_trigger):
        """FixedTimeTrigger can be created."""
        assert sample_fixed_time_trigger.time == "21:00"
        assert sample_fixed_time_trigger.days_of_week == [0, 1, 2, 3, 4, 5, 6]

    def test_instantiation_minimal(self):
        """FixedTimeTrigger can be created with minimal args."""
        trigger = FixedTimeTrigger(time="06:30")
        assert trigger.time == "06:30"
        assert trigger.days_of_week is None

    def test_to_dict(self, sample_fixed_time_trigger):
        """FixedTimeTrigger.to_dict() returns correct dict."""
        data = sample_fixed_time_trigger.to_dict()
        assert data["time"] == "21:00"
        assert data["days_of_week"] == [0, 1, 2, 3, 4, 5, 6]

    def test_from_dict(self):
        """FixedTimeTrigger.from_dict() creates instance from dict."""
        data = {"time": "12:00", "days_of_week": [0, 2, 4]}
        trigger = FixedTimeTrigger.from_dict(data)
        assert trigger.time == "12:00"
        assert trigger.days_of_week == [0, 2, 4]


# =============================================================================
# SENSOR TRIGGER TESTS
# =============================================================================


class TestSensorTrigger:
    """Test SensorTrigger dataclass."""

    def test_instantiation(self, sample_sensor_trigger):
        """SensorTrigger can be created."""
        assert sample_sensor_trigger.sensor_type == "motion"
        assert sample_sensor_trigger.threshold == 0.0
        assert sample_sensor_trigger.comparison == "gt"
        assert sample_sensor_trigger.cooldown_minutes == 5
        assert sample_sensor_trigger.time_window is not None

    def test_instantiation_minimal(self):
        """SensorTrigger can be created with minimal args."""
        trigger = SensorTrigger(sensor_type="light")
        assert trigger.sensor_type == "light"
        assert trigger.threshold == 0.0
        assert trigger.comparison == "gt"
        assert trigger.cooldown_minutes == 5
        assert trigger.time_window is None

    def test_to_dict(self, sample_sensor_trigger):
        """SensorTrigger.to_dict() returns correct dict."""
        data = sample_sensor_trigger.to_dict()
        assert data["sensor_type"] == "motion"
        assert data["threshold"] == 0.0
        assert data["comparison"] == "gt"
        assert data["cooldown_minutes"] == 5

    def test_from_dict(self):
        """SensorTrigger.from_dict() creates instance from dict."""
        data = {
            "sensor_type": "temperature",
            "threshold": 25.0,
            "comparison": "lt",
            "cooldown_minutes": 10,
            "time_window": None,
        }
        trigger = SensorTrigger.from_dict(data)
        assert trigger.sensor_type == "temperature"
        assert trigger.threshold == 25.0
        assert trigger.comparison == "lt"


# =============================================================================
# SCHEDULE TESTS
# =============================================================================


class TestSchedule:
    """Test Schedule dataclass."""

    def test_instantiation(self, sample_schedule):
        """Schedule can be created."""
        assert sample_schedule.schedule_id == "test-schedule-id"
        assert sample_schedule.name == "Nightly Moth Survey"
        assert len(sample_schedule.event_patterns) == 1
        assert sample_schedule.trigger_type == "interval"
        assert sample_schedule.interval_trigger is not None
        assert sample_schedule.enabled is True
        assert sample_schedule.is_active is False

    def test_uuid_generation_on_empty_id(self):
        """Schedule generates UUID when schedule_id is empty."""
        schedule = Schedule(schedule_id="", name="Test", trigger_type="interval")
        uuid.UUID(schedule.schedule_id)

    def test_timestamps_generated(self):
        """Schedule generates timestamps when empty."""
        schedule = Schedule(schedule_id="test", name="Test", trigger_type="interval")
        assert schedule.created_at != ""
        assert schedule.modified_at != ""
        # Validate ISO format
        datetime.fromisoformat(schedule.created_at.replace("Z", "+00:00"))

    def test_total_duration_minutes(self, sample_schedule):
        """Schedule.total_duration_minutes sums pattern durations."""
        # Single pattern with duration 15
        assert sample_schedule.total_duration_minutes == 15

    def test_total_duration_multiple_patterns(self, sample_event_pattern):
        """Schedule.total_duration_minutes handles multiple patterns."""
        pattern2 = EventPattern(
            pattern_id="p2",
            name="Extra",
            actions=[
                PatternAction(action_type="gpio", action_name="flash_on", offset_minutes=10),
            ],
        )
        schedule = Schedule(
            schedule_id="s1",
            name="Multi",
            trigger_type="interval",
            event_patterns=[sample_event_pattern, pattern2],
        )
        # 15 + 10 = 25
        assert schedule.total_duration_minutes == 25

    def test_to_dict_includes_schema_version(self, sample_schedule):
        """Schedule.to_dict() includes schema_version."""
        data = sample_schedule.to_dict()
        assert data["schema_version"] == SCHEDULE_SCHEMA_VERSION
        assert data["schedule_id"] == "test-schedule-id"
        assert data["name"] == "Nightly Moth Survey"
        assert len(data["event_patterns"]) == 1

    def test_from_dict(self, sample_event_pattern, sample_time_window):
        """Schedule.from_dict() creates instance from dict."""
        data = {
            "schema_version": "2.0",
            "schedule_id": "s-123",
            "name": "Test Schedule",
            "description": "A test schedule",
            "event_patterns": [sample_event_pattern.to_dict()],
            "trigger_type": "interval",
            "interval_trigger": {
                "interval_minutes": 30,
                "time_window": sample_time_window.to_dict(),
                "days_of_week": None,
            },
            "solar_trigger": None,
            "moon_phase_trigger": None,
            "fixed_time_trigger": None,
            "sensor_trigger": None,
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "deployment_id": "dep-456",
            "create_deployment": True,
            "enabled": True,
            "is_active": False,
            "created_at": "2024-01-01T00:00:00Z",
            "modified_at": "2024-01-01T00:00:00Z",
            "modified_by": "user123",
        }
        schedule = Schedule.from_dict(data)
        assert schedule.schedule_id == "s-123"
        assert schedule.name == "Test Schedule"
        assert len(schedule.event_patterns) == 1
        assert schedule.interval_trigger is not None
        assert schedule.interval_trigger.interval_minutes == 30

    def test_round_trip_serialization(self, sample_schedule):
        """Schedule survives JSON round-trip."""
        data = sample_schedule.to_dict()
        json_str = json.dumps(data)
        loaded = json.loads(json_str)
        restored = Schedule.from_dict(loaded)
        assert restored.schedule_id == sample_schedule.schedule_id
        assert restored.name == sample_schedule.name
        assert len(restored.event_patterns) == len(sample_schedule.event_patterns)


# =============================================================================
# VALIDATE PATTERN ACTION TESTS
# =============================================================================


class TestValidatePatternAction:
    """Test validate_pattern_action function."""

    def test_valid_gpio_action(self, sample_pattern_action):
        """Valid GPIO action passes validation."""
        valid, error = validate_pattern_action(sample_pattern_action)
        assert valid is True
        assert error is None

    def test_valid_camera_action(self, sample_pattern_action_camera):
        """Valid camera action passes validation."""
        valid, error = validate_pattern_action(sample_pattern_action_camera)
        assert valid is True
        assert error is None

    def test_invalid_action_type(self):
        """Invalid action_type fails validation."""
        action = PatternAction(action_type="invalid", action_name="test")
        valid, error = validate_pattern_action(action)
        assert valid is False
        assert "action type" in error.lower()

    def test_negative_offset_fails(self):
        """Negative offset_minutes fails validation."""
        action = PatternAction(
            action_type="gpio", action_name="attract_on", offset_minutes=-5
        )
        valid, error = validate_pattern_action(action)
        assert valid is False
        assert "negative" in error.lower() or "offset" in error.lower()

    def test_offset_exceeds_max_fails(self):
        """Offset exceeding MAX_OFFSET_MINUTES fails validation."""
        action = PatternAction(
            action_type="gpio",
            action_name="attract_on",
            offset_minutes=MAX_OFFSET_MINUTES + 1,
        )
        valid, error = validate_pattern_action(action)
        assert valid is False
        assert "offset" in error.lower()


# =============================================================================
# VALIDATE EVENT PATTERN TESTS
# =============================================================================


class TestValidateEventPattern:
    """Test validate_event_pattern function."""

    def test_valid_pattern(self, sample_event_pattern):
        """Valid event pattern passes validation."""
        valid, error = validate_event_pattern(sample_event_pattern)
        assert valid is True
        assert error is None

    def test_empty_name_fails(self):
        """Empty name fails validation."""
        pattern = EventPattern(pattern_id="test", name="")
        valid, error = validate_event_pattern(pattern)
        assert valid is False
        assert "name" in error.lower()

    def test_name_too_long_fails(self):
        """Name exceeding MAX_PATTERN_NAME_LENGTH fails validation."""
        pattern = EventPattern(pattern_id="test", name="x" * (MAX_PATTERN_NAME_LENGTH + 1))
        valid, error = validate_event_pattern(pattern)
        assert valid is False
        assert "name" in error.lower()

    def test_no_actions_fails(self):
        """Pattern with no actions fails validation."""
        pattern = EventPattern(pattern_id="test", name="Empty Pattern", actions=[])
        valid, error = validate_event_pattern(pattern)
        assert valid is False
        assert "action" in error.lower()

    def test_too_many_actions_fails(self):
        """Pattern exceeding MAX_ACTIONS_PER_PATTERN fails validation."""
        actions = [
            PatternAction(action_type="gpio", action_name="attract_on", offset_minutes=i)
            for i in range(MAX_ACTIONS_PER_PATTERN + 1)
        ]
        pattern = EventPattern(pattern_id="test", name="Too Many", actions=actions)
        valid, error = validate_event_pattern(pattern)
        assert valid is False
        assert "action" in error.lower()

    def test_invalid_action_fails(self):
        """Pattern with invalid action fails validation."""
        pattern = EventPattern(
            pattern_id="test",
            name="Bad Action",
            actions=[PatternAction(action_type="invalid", action_name="test")],
        )
        valid, error = validate_event_pattern(pattern)
        assert valid is False


# =============================================================================
# VALIDATE TIME WINDOW TESTS
# =============================================================================


class TestValidateTimeWindow:
    """Test validate_time_window function."""

    def test_valid_fixed_times(self, sample_time_window):
        """Valid fixed time window passes validation."""
        valid, error = validate_time_window(sample_time_window)
        assert valid is True
        assert error is None

    def test_valid_solar_times(self, sample_time_window_solar):
        """Valid solar time window passes validation."""
        valid, error = validate_time_window(sample_time_window_solar)
        assert valid is True
        assert error is None

    def test_invalid_time_format_fails(self):
        """Invalid time format fails validation."""
        window = TimeWindow(start_time="25:00", end_time="05:00")
        valid, error = validate_time_window(window)
        assert valid is False
        assert "time" in error.lower() or "format" in error.lower()

    def test_invalid_solar_event_fails(self):
        """Invalid solar event fails validation."""
        window = TimeWindow(start_time="invalid_event", end_time="05:00")
        valid, error = validate_time_window(window)
        assert valid is False


# =============================================================================
# VALIDATE TRIGGER TESTS
# =============================================================================


class TestValidateIntervalTrigger:
    """Test validate_interval_trigger function."""

    def test_valid_trigger(self, sample_interval_trigger):
        """Valid interval trigger passes validation."""
        valid, error = validate_interval_trigger(sample_interval_trigger)
        assert valid is True
        assert error is None

    def test_zero_interval_fails(self, sample_time_window):
        """Zero interval_minutes fails validation."""
        trigger = IntervalTrigger(interval_minutes=0, time_window=sample_time_window)
        valid, error = validate_interval_trigger(trigger)
        assert valid is False
        assert "interval" in error.lower()

    def test_negative_interval_fails(self, sample_time_window):
        """Negative interval_minutes fails validation."""
        trigger = IntervalTrigger(interval_minutes=-10, time_window=sample_time_window)
        valid, error = validate_interval_trigger(trigger)
        assert valid is False

    def test_invalid_days_of_week_fails(self, sample_time_window):
        """Invalid days_of_week fails validation."""
        trigger = IntervalTrigger(
            interval_minutes=60, time_window=sample_time_window, days_of_week=[7]
        )
        valid, error = validate_interval_trigger(trigger)
        assert valid is False
        assert "day" in error.lower()


class TestValidateSolarTrigger:
    """Test validate_solar_trigger function."""

    def test_valid_trigger(self, sample_solar_trigger):
        """Valid solar trigger passes validation."""
        valid, error = validate_solar_trigger(sample_solar_trigger)
        assert valid is True
        assert error is None

    def test_invalid_solar_event_fails(self):
        """Invalid solar_event fails validation."""
        trigger = SolarTrigger(solar_event="invalid")
        valid, error = validate_solar_trigger(trigger)
        assert valid is False
        assert "solar" in error.lower()


class TestValidateMoonPhaseTrigger:
    """Test validate_moon_phase_trigger function."""

    def test_valid_trigger(self, sample_moon_phase_trigger):
        """Valid moon phase trigger passes validation."""
        valid, error = validate_moon_phase_trigger(sample_moon_phase_trigger)
        assert valid is True
        assert error is None

    def test_empty_phases_fails(self):
        """Empty phases list fails validation."""
        trigger = MoonPhaseTrigger(phases=[])
        valid, error = validate_moon_phase_trigger(trigger)
        assert valid is False
        assert "phase" in error.lower()

    def test_invalid_phase_fails(self):
        """Invalid phase fails validation."""
        trigger = MoonPhaseTrigger(phases=["invalid_phase"])
        valid, error = validate_moon_phase_trigger(trigger)
        assert valid is False


class TestValidateFixedTimeTrigger:
    """Test validate_fixed_time_trigger function."""

    def test_valid_trigger(self, sample_fixed_time_trigger):
        """Valid fixed time trigger passes validation."""
        valid, error = validate_fixed_time_trigger(sample_fixed_time_trigger)
        assert valid is True
        assert error is None

    def test_invalid_time_format_fails(self):
        """Invalid time format fails validation."""
        trigger = FixedTimeTrigger(time="invalid")
        valid, error = validate_fixed_time_trigger(trigger)
        assert valid is False
        assert "time" in error.lower()


class TestValidateSensorTrigger:
    """Test validate_sensor_trigger function."""

    def test_valid_trigger(self, sample_sensor_trigger):
        """Valid sensor trigger passes validation."""
        valid, error = validate_sensor_trigger(sample_sensor_trigger)
        assert valid is True
        assert error is None

    def test_invalid_sensor_type_fails(self):
        """Invalid sensor_type fails validation."""
        trigger = SensorTrigger(sensor_type="invalid")
        valid, error = validate_sensor_trigger(trigger)
        assert valid is False
        assert "sensor" in error.lower()

    def test_invalid_comparison_fails(self):
        """Invalid comparison fails validation."""
        trigger = SensorTrigger(sensor_type="motion", comparison="invalid")
        valid, error = validate_sensor_trigger(trigger)
        assert valid is False
        assert "comparison" in error.lower()


# =============================================================================
# VALIDATE SCHEDULE TESTS
# =============================================================================


class TestValidateSchedule:
    """Test validate_schedule function."""

    def test_valid_schedule(self, sample_schedule):
        """Valid schedule passes validation."""
        valid, error = validate_schedule(sample_schedule)
        assert valid is True
        assert error is None

    def test_empty_name_fails(self, sample_event_pattern):
        """Empty name fails validation."""
        schedule = Schedule(
            schedule_id="test",
            name="",
            trigger_type="interval",
            event_patterns=[sample_event_pattern],
        )
        valid, error = validate_schedule(schedule)
        assert valid is False
        assert "name" in error.lower()

    def test_no_patterns_fails(self):
        """Schedule with no patterns fails validation."""
        schedule = Schedule(
            schedule_id="test", name="Empty", trigger_type="interval", event_patterns=[]
        )
        valid, error = validate_schedule(schedule)
        assert valid is False
        assert "pattern" in error.lower()

    def test_invalid_trigger_type_fails(self, sample_event_pattern):
        """Invalid trigger_type fails validation."""
        schedule = Schedule(
            schedule_id="test",
            name="Bad Trigger",
            trigger_type="invalid",
            event_patterns=[sample_event_pattern],
        )
        valid, error = validate_schedule(schedule)
        assert valid is False
        assert "trigger" in error.lower()

    def test_missing_trigger_config_fails(self, sample_event_pattern):
        """Missing trigger config for trigger_type fails validation."""
        schedule = Schedule(
            schedule_id="test",
            name="No Config",
            trigger_type="interval",
            event_patterns=[sample_event_pattern],
            interval_trigger=None,
        )
        valid, error = validate_schedule(schedule)
        assert valid is False
        assert "interval" in error.lower()

    def test_invalid_date_format_fails(self, sample_event_pattern, sample_interval_trigger):
        """Invalid date format fails validation."""
        schedule = Schedule(
            schedule_id="test",
            name="Bad Date",
            trigger_type="interval",
            event_patterns=[sample_event_pattern],
            interval_trigger=sample_interval_trigger,
            start_date="not-a-date",
        )
        valid, error = validate_schedule(schedule)
        assert valid is False
        assert "date" in error.lower()

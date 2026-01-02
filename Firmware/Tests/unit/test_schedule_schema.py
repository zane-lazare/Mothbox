"""
Unit tests for schedule schema dataclasses.

Tests the core schedule schema including:
- Action, EventPattern dataclasses
- TimeWindow and trigger dataclasses (Interval, Solar, MoonPhase, FixedTime, Sensor)
- Schedule dataclass with embedded event patterns
- Validation functions for all types

Coverage target: 85%+
Test count target: 40+

Issue #208 - Scheduler Phase 1: Schedule Schema
"""

import json
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
        MAX_ROUTINES_PER_SCHEDULE,
        MOON_PHASES,
        PRIMARY_TRIGGER_TYPES,
        SCHEDULE_SCHEMA_VERSION,
        SENSOR_COMPARISONS,
        SENSOR_TYPES,
        SOLAR_EVENTS,
        SUPPORTED_VERSIONS,
        TRIGGER_CLASS_MAP,
        TRIGGER_TYPE_MAP,
        TRIGGER_TYPES,
        # Dataclasses
        Action,
        CronTrigger,
        EventPattern,
        FixedTimeTrigger,
        IntervalTrigger,
        MoonPhaseTrigger,
        RecurringDaysTrigger,
        Routine,
        Schedule,
        SensorTrigger,
        SolarTrigger,
        TimeWindow,
        trigger_from_dict,
        # Validation functions
        validate_action,
        validate_cron_trigger,
        validate_event_pattern,
        validate_fixed_time_trigger,
        validate_interval_trigger,
        validate_moon_phase_trigger,
        validate_recurring_days_trigger,
        validate_routine,
        validate_routine_ids_unique,
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
    """Create a sample Action for testing."""
    return Action(
        action_type="gpio",
        action_name="attract_on",
        offset_minutes=0,
        parameters={},
        description="Turn on attract lights",
    )


@pytest.fixture
def sample_pattern_action_camera():
    """Create a camera Action for testing."""
    return Action(
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
        pattern_id="12345678-1234-5678-1234-567812345678",
        name="UV Capture Cycle",
        description="Turn on lights, take photo, turn off lights",
        actions=[
            sample_pattern_action,
            sample_pattern_action_camera,
            Action(
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
def sample_schedule(sample_routine_interval):
    """Create a sample Schedule for testing (Schema 3.0)."""
    return Schedule(
        schedule_id="87654321-4321-8765-4321-876543218765",
        name="Nightly Moth Survey",
        description="Hourly captures from dusk to dawn",
        routines=[sample_routine_interval],
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
        assert SCHEDULE_SCHEMA_VERSION == "3.0"

    def test_supported_versions_includes_current(self):
        """SUPPORTED_VERSIONS should include current version."""
        assert SCHEDULE_SCHEMA_VERSION in SUPPORTED_VERSIONS

    def test_action_types_defined(self):
        """ACTION_TYPES should include all expected types."""
        expected = ["gpio", "camera", "gps_sync", "service"]
        assert expected == ACTION_TYPES

    def test_gpio_actions_defined(self):
        """GPIO_ACTIONS should include all expected actions."""
        expected = ["attract_on", "attract_off", "flash_on", "flash_off"]
        assert expected == GPIO_ACTIONS

    def test_trigger_types_defined(self):
        """TRIGGER_TYPES should include all expected types including cron and recurring_days."""
        expected = [
            "interval",
            "solar",
            "moon_phase",
            "fixed_time",
            "sensor",
            "cron",
            "recurring_days",
        ]
        assert expected == TRIGGER_TYPES

    def test_primary_trigger_types_excludes_sensor(self):
        """PRIMARY_TRIGGER_TYPES excludes sensor (pre_condition only)."""
        assert "sensor" not in PRIMARY_TRIGGER_TYPES
        assert "interval" in PRIMARY_TRIGGER_TYPES
        assert len(PRIMARY_TRIGGER_TYPES) == len(TRIGGER_TYPES) - 1

    def test_trigger_type_map_covers_all_triggers(self):
        """TRIGGER_TYPE_MAP should cover all trigger types."""
        assert len(TRIGGER_TYPE_MAP) == len(TRIGGER_TYPES)
        for trigger_type in TRIGGER_TYPES:
            assert trigger_type in TRIGGER_TYPE_MAP.values()

    def test_trigger_class_map_is_inverse_of_type_map(self):
        """TRIGGER_CLASS_MAP should be inverse of TRIGGER_TYPE_MAP."""
        assert len(TRIGGER_CLASS_MAP) == len(TRIGGER_TYPE_MAP)
        for cls, type_str in TRIGGER_TYPE_MAP.items():
            assert TRIGGER_CLASS_MAP[type_str] == cls

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
        assert expected == SENSOR_TYPES

    def test_sensor_comparisons_defined(self):
        """SENSOR_COMPARISONS should include all operators."""
        expected = ["gt", "lt", "eq", "gte", "lte"]
        assert expected == SENSOR_COMPARISONS

    def test_validation_limits_defined(self):
        """Validation limits should be defined."""
        assert MAX_PATTERN_NAME_LENGTH == 200
        assert MAX_DESCRIPTION_LENGTH == 2000
        assert MAX_ACTIONS_PER_PATTERN == 20
        assert MAX_ROUTINES_PER_SCHEDULE == 10
        assert MAX_OFFSET_MINUTES == 1440


# =============================================================================
# PATTERN ACTION TESTS
# =============================================================================


class TestAction:
    """Test Action dataclass."""

    def test_instantiation_minimal(self):
        """Action can be created with minimal args."""
        action = Action(action_type="gpio", action_name="attract_on")
        assert action.action_type == "gpio"
        assert action.action_name == "attract_on"
        assert action.offset_minutes == 0
        assert action.parameters == {}
        assert action.description == ""

    def test_instantiation_full(self, sample_pattern_action):
        """Action can be created with all args."""
        assert sample_pattern_action.action_type == "gpio"
        assert sample_pattern_action.action_name == "attract_on"
        assert sample_pattern_action.offset_minutes == 0
        assert sample_pattern_action.description == "Turn on attract lights"

    def test_to_dict(self, sample_pattern_action):
        """Action.to_dict() returns correct dict."""
        data = sample_pattern_action.to_dict()
        assert data["action_type"] == "gpio"
        assert data["action_name"] == "attract_on"
        assert data["offset_minutes"] == 0
        assert data["parameters"] == {}
        assert data["description"] == "Turn on attract lights"

    def test_from_dict(self):
        """Action.from_dict() creates instance from dict."""
        data = {
            "action_type": "camera",
            "action_name": "takephoto",
            "offset_minutes": 5,
            "parameters": {"hdr": True},
            "description": "Take HDR photo",
        }
        action = Action.from_dict(data)
        assert action.action_type == "camera"
        assert action.action_name == "takephoto"
        assert action.offset_minutes == 5
        assert action.parameters == {"hdr": True}
        assert action.description == "Take HDR photo"

    def test_round_trip_serialization(self, sample_pattern_action):
        """Action survives JSON round-trip."""
        data = sample_pattern_action.to_dict()
        json_str = json.dumps(data)
        loaded = json.loads(json_str)
        restored = Action.from_dict(loaded)
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
        pattern = EventPattern(pattern_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", name="Empty")
        assert pattern.duration_minutes == 0

    def test_to_dict(self, sample_event_pattern):
        """EventPattern.to_dict() returns correct dict."""
        data = sample_event_pattern.to_dict()
        assert data["pattern_id"] == "12345678-1234-5678-1234-567812345678"
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
# ROUTINE FIXTURES
# =============================================================================


@pytest.fixture
def sample_routine_interval():
    """IntervalTrigger with flash+photo sequence."""
    return Routine(
        routine_id="",
        name=None,
        trigger=IntervalTrigger(
            interval_minutes=15,
            time_window=TimeWindow(start_time="22:00", end_time="06:00"),
        ),
        actions=[
            Action(action_type="gpio", action_name="flash_on", offset_minutes=0),
            Action(action_type="camera", action_name="takephoto", offset_minutes=1),
            Action(action_type="gpio", action_name="flash_off", offset_minutes=2),
        ],
    )


@pytest.fixture
def sample_routine_solar():
    """SolarTrigger with attract_on action."""
    return Routine(
        routine_id="",
        name=None,
        trigger=SolarTrigger(solar_event="dusk", offset_minutes=0),
        actions=[Action(action_type="gpio", action_name="attract_on")],
    )


@pytest.fixture
def sample_routine_with_precondition():
    """Routine with pre_condition sensor check."""
    return Routine(
        routine_id="f47ac10b-58cc-4372-a567-0e02b2c3d479",  # Valid UUID
        name="Photo if Dark",
        trigger=IntervalTrigger(
            interval_minutes=15,
            time_window=TimeWindow(start_time="22:00", end_time="06:00"),
        ),
        actions=[Action(action_type="camera", action_name="takephoto")],
        pre_condition=SensorTrigger(
            sensor_type="light",
            threshold=100,
            comparison="lt",
        ),
    )


# =============================================================================
# ROUTINE TESTS
# =============================================================================


class TestRoutine:
    """Test Routine dataclass."""

    def test_instantiation_minimal(self):
        """Routine can be created with required fields only."""
        trigger = IntervalTrigger(
            interval_minutes=60,
            time_window=TimeWindow(start_time="21:00", end_time="05:00"),
        )
        routine = Routine(
            routine_id="",
            name=None,
            trigger=trigger,
            actions=[Action(action_type="gpio", action_name="attract_on")],
        )
        assert routine.trigger == trigger
        assert len(routine.actions) == 1
        assert routine.name is None
        assert routine.pre_condition is None

    def test_uuid_generation_on_empty_id(self):
        """Empty routine_id generates valid UUID."""
        routine = Routine(
            routine_id="",
            name=None,
            trigger=SolarTrigger(solar_event="sunset"),
            actions=[Action(action_type="gpio", action_name="attract_on")],
        )
        # Should be a valid UUID
        uuid.UUID(routine.routine_id)

    def test_empty_name_normalized_to_none(self):
        """Empty string name becomes None."""
        routine = Routine(
            routine_id="test-id",
            name="",
            trigger=SolarTrigger(solar_event="sunset"),
            actions=[Action(action_type="gpio", action_name="attract_on")],
        )
        assert routine.name is None

    def test_duration_minutes_computed(self, sample_routine_interval):
        """Returns max action offset."""
        # Actions have offsets 0, 1, 2
        assert sample_routine_interval.duration_minutes == 2

    def test_duration_minutes_empty_actions(self):
        """Returns 0 with no actions."""
        routine = Routine(
            routine_id="test-empty",
            name=None,
            trigger=SolarTrigger(solar_event="sunset"),
            actions=[],
        )
        assert routine.duration_minutes == 0


class TestRoutineGetDisplayName:
    """Test Routine.get_display_name() auto-naming."""

    def test_explicit_name_returned(self, sample_routine_with_precondition):
        """Explicit name takes precedence."""
        assert sample_routine_with_precondition.get_display_name() == "Photo if Dark"

    def test_auto_name_solar_single_action(self):
        """Auto-name for solar trigger with single action."""
        routine = Routine(
            routine_id="",
            name=None,
            trigger=SolarTrigger(solar_event="dusk", offset_minutes=0),
            actions=[Action(action_type="gpio", action_name="attract_on")],
        )
        assert routine.get_display_name() == "Attract On at Dusk"

    def test_auto_name_solar_with_offset(self):
        """Auto-name includes offset."""
        routine = Routine(
            routine_id="",
            name=None,
            trigger=SolarTrigger(solar_event="sunset", offset_minutes=30),
            actions=[Action(action_type="gpio", action_name="attract_on")],
        )
        assert routine.get_display_name() == "Attract On at Sunset +30min"

    def test_auto_name_interval_flash_photo(self, sample_routine_interval):
        """Auto-name for interval with multiple actions."""
        display_name = sample_routine_interval.get_display_name()
        # 3 unique action names: flash_on, takephoto, flash_off -> "3 Actions"
        assert "Actions" in display_name or "Flash" in display_name or "Photo" in display_name
        assert "15min" in display_name

    def test_auto_name_interval_hourly(self):
        """Auto-name shows hours for 60min intervals."""
        routine = Routine(
            routine_id="",
            name=None,
            trigger=IntervalTrigger(
                interval_minutes=60,
                time_window=TimeWindow(start_time="21:00", end_time="05:00"),
            ),
            actions=[Action(action_type="camera", action_name="takephoto")],
        )
        display_name = routine.get_display_name()
        assert "1h" in display_name or "60min" in display_name

    def test_auto_name_recurring_days(self):
        """Auto-name for recurring days trigger."""
        routine = Routine(
            routine_id="",
            name=None,
            trigger=RecurringDaysTrigger(every_n_days=3, time="21:00"),
            actions=[Action(action_type="gps_sync", action_name="gps_sync")],
        )
        display_name = routine.get_display_name()
        assert "GPS Sync" in display_name
        assert "3 days" in display_name or "every 3" in display_name
        assert "21:00" in display_name

    def test_auto_name_fixed_time(self):
        """Auto-name for fixed time trigger."""
        routine = Routine(
            routine_id="",
            name=None,
            trigger=FixedTimeTrigger(time="09:00"),
            actions=[Action(action_type="service", action_name="backup")],
        )
        display_name = routine.get_display_name()
        assert "Backup" in display_name
        assert "09:00" in display_name

    def test_auto_name_moon_phase_single(self):
        """Auto-name for moon phase trigger."""
        routine = Routine(
            routine_id="",
            name=None,
            trigger=MoonPhaseTrigger(phases=["full"]),
            actions=[Action(action_type="camera", action_name="takephoto")],
        )
        display_name = routine.get_display_name()
        assert "Photo" in display_name
        assert "Full" in display_name or "full" in display_name

    def test_auto_name_cron(self):
        """Auto-name for cron trigger."""
        routine = Routine(
            routine_id="",
            name=None,
            trigger=CronTrigger(cron_expression="0 21 * * *"),
            actions=[Action(action_type="camera", action_name="takephoto")],
        )
        display_name = routine.get_display_name()
        assert "Photo" in display_name
        assert "cron" in display_name.lower()

    def test_auto_name_repeated_actions(self):
        """Auto-name handles repeated actions."""
        routine = Routine(
            routine_id="",
            name=None,
            trigger=IntervalTrigger(
                interval_minutes=30,
                time_window=TimeWindow(start_time="21:00", end_time="05:00"),
            ),
            actions=[
                Action(action_type="camera", action_name="takephoto", offset_minutes=0),
                Action(action_type="camera", action_name="takephoto", offset_minutes=5),
                Action(action_type="camera", action_name="takephoto", offset_minutes=10),
            ],
        )
        display_name = routine.get_display_name()
        assert "3x Photo" in display_name or "Photo" in display_name
        assert "30min" in display_name

    def test_auto_name_empty_actions(self):
        """Auto-name handles empty actions."""
        routine = Routine(
            routine_id="",
            name=None,
            trigger=SolarTrigger(solar_event="sunset"),
            actions=[],
        )
        display_name = routine.get_display_name()
        assert "Empty" in display_name or "Sunset" in display_name


class TestRoutineSerialization:
    """Test Routine serialization."""

    def test_to_dict_includes_all_fields(self, sample_routine_interval):
        """All fields present in dict."""
        data = sample_routine_interval.to_dict()
        assert "routine_id" in data
        assert "name" in data
        assert "trigger" in data
        assert "actions" in data
        assert "pre_condition" in data
        assert len(data["actions"]) == 3

    def test_to_dict_trigger_has_trigger_type(self, sample_routine_solar):
        """trigger dict includes trigger_type."""
        data = sample_routine_solar.to_dict()
        assert data["trigger"]["trigger_type"] == "solar"
        assert data["trigger"]["solar_event"] == "dusk"

    def test_to_dict_with_pre_condition(self, sample_routine_with_precondition):
        """pre_condition serialized correctly."""
        data = sample_routine_with_precondition.to_dict()
        assert data["pre_condition"] is not None
        assert data["pre_condition"]["sensor_type"] == "light"
        assert data["pre_condition"]["threshold"] == 100
        assert data["pre_condition"]["comparison"] == "lt"

    def test_from_dict_all_trigger_types(self):
        """Test all 7 trigger types deserialize."""
        # IntervalTrigger
        data1 = {
            "routine_id": "test-1",
            "name": None,
            "trigger": {
                "trigger_type": "interval",
                "interval_minutes": 60,
                "time_window": {"start_time": "21:00", "end_time": "05:00"},
            },
            "actions": [{"action_type": "gpio", "action_name": "attract_on"}],
        }
        r1 = Routine.from_dict(data1)
        assert isinstance(r1.trigger, IntervalTrigger)

        # SolarTrigger
        data2 = {
            "routine_id": "test-2",
            "name": None,
            "trigger": {"trigger_type": "solar", "solar_event": "sunset"},
            "actions": [{"action_type": "gpio", "action_name": "attract_on"}],
        }
        r2 = Routine.from_dict(data2)
        assert isinstance(r2.trigger, SolarTrigger)

        # MoonPhaseTrigger
        data3 = {
            "routine_id": "test-3",
            "name": None,
            "trigger": {"trigger_type": "moon_phase", "phases": ["full"]},
            "actions": [{"action_type": "camera", "action_name": "takephoto"}],
        }
        r3 = Routine.from_dict(data3)
        assert isinstance(r3.trigger, MoonPhaseTrigger)

        # FixedTimeTrigger
        data4 = {
            "routine_id": "test-4",
            "name": None,
            "trigger": {"trigger_type": "fixed_time", "time": "21:00"},
            "actions": [{"action_type": "camera", "action_name": "takephoto"}],
        }
        r4 = Routine.from_dict(data4)
        assert isinstance(r4.trigger, FixedTimeTrigger)

        # SensorTrigger
        data5 = {
            "routine_id": "test-5",
            "name": None,
            "trigger": {"trigger_type": "sensor", "sensor_type": "motion"},
            "actions": [{"action_type": "camera", "action_name": "takephoto"}],
        }
        r5 = Routine.from_dict(data5)
        assert isinstance(r5.trigger, SensorTrigger)

        # CronTrigger
        data6 = {
            "routine_id": "test-6",
            "name": None,
            "trigger": {"trigger_type": "cron", "cron_expression": "0 21 * * *"},
            "actions": [{"action_type": "camera", "action_name": "takephoto"}],
        }
        r6 = Routine.from_dict(data6)
        assert isinstance(r6.trigger, CronTrigger)

        # RecurringDaysTrigger
        data7 = {
            "routine_id": "test-7",
            "name": None,
            "trigger": {"trigger_type": "recurring_days", "every_n_days": 3, "time": "21:00"},
            "actions": [{"action_type": "gps_sync", "action_name": "gps_sync"}],
        }
        r7 = Routine.from_dict(data7)
        assert isinstance(r7.trigger, RecurringDaysTrigger)

    def test_round_trip_serialization(self, sample_routine_with_precondition):
        """JSON round-trip preserves data."""
        data = sample_routine_with_precondition.to_dict()
        json_str = json.dumps(data)
        loaded = json.loads(json_str)
        restored = Routine.from_dict(loaded)
        assert restored.routine_id == sample_routine_with_precondition.routine_id
        assert restored.name == sample_routine_with_precondition.name
        assert len(restored.actions) == len(sample_routine_with_precondition.actions)
        assert restored.pre_condition.sensor_type == "light"


class TestValidateRoutine:
    """Test validate_routine function."""

    def test_valid_routine(self, sample_routine_interval):
        """Valid routine passes."""
        valid, error = validate_routine(sample_routine_interval)
        assert valid is True
        assert error is None

    def test_invalid_routine_id_format(self):
        """Non-UUID fails."""
        routine = Routine(
            routine_id="not-a-uuid",
            name=None,
            trigger=SolarTrigger(solar_event="sunset"),
            actions=[Action(action_type="gpio", action_name="attract_on")],
        )
        valid, error = validate_routine(routine)
        assert valid is False
        assert "routine_id" in error.lower()
        assert "uuid" in error.lower()

    def test_name_too_long_fails(self):
        """Exceeds limit."""
        routine = Routine(
            routine_id="",
            name="x" * (MAX_PATTERN_NAME_LENGTH + 1),
            trigger=SolarTrigger(solar_event="sunset"),
            actions=[Action(action_type="gpio", action_name="attract_on")],
        )
        valid, error = validate_routine(routine)
        assert valid is False
        assert "name" in error.lower()

    def test_sensor_trigger_as_primary_fails(self):
        """Sensors are pre_condition only."""
        routine = Routine(
            routine_id="",
            name=None,
            trigger=SensorTrigger(sensor_type="motion"),
            actions=[Action(action_type="camera", action_name="takephoto")],
        )
        valid, error = validate_routine(routine)
        assert valid is False
        assert "sensor" in error.lower()

    def test_empty_actions_fails(self):
        """At least one action required."""
        routine = Routine(
            routine_id="",
            name=None,
            trigger=SolarTrigger(solar_event="sunset"),
            actions=[],
        )
        valid, error = validate_routine(routine)
        assert valid is False
        assert "action" in error.lower()

    def test_too_many_actions_fails(self):
        """Exceeds limit."""
        actions = [
            Action(action_type="gpio", action_name="attract_on", offset_minutes=i)
            for i in range(MAX_ACTIONS_PER_PATTERN + 1)
        ]
        routine = Routine(
            routine_id="",
            name=None,
            trigger=SolarTrigger(solar_event="sunset"),
            actions=actions,
        )
        valid, error = validate_routine(routine)
        assert valid is False
        assert "action" in error.lower()

    def test_invalid_trigger_fails(self):
        """Invalid trigger config fails."""
        routine = Routine(
            routine_id="",
            name=None,
            trigger=IntervalTrigger(
                interval_minutes=0,  # Invalid: must be >= 1
                time_window=TimeWindow(start_time="21:00", end_time="05:00"),
            ),
            actions=[Action(action_type="gpio", action_name="attract_on")],
        )
        valid, error = validate_routine(routine)
        assert valid is False

    def test_valid_pre_condition(self, sample_routine_with_precondition):
        """Valid SensorTrigger as pre_condition passes."""
        valid, error = validate_routine(sample_routine_with_precondition)
        assert valid is True
        assert error is None

    def test_invalid_pre_condition_fails(self):
        """Invalid sensor config fails."""
        routine = Routine(
            routine_id="",
            name=None,
            trigger=IntervalTrigger(
                interval_minutes=15,
                time_window=TimeWindow(start_time="22:00", end_time="06:00"),
            ),
            actions=[Action(action_type="camera", action_name="takephoto")],
            pre_condition=SensorTrigger(
                sensor_type="invalid_sensor",  # Invalid
                threshold=100,
                comparison="lt",
            ),
        )
        valid, error = validate_routine(routine)
        assert valid is False


class TestRoutinePreCondition:
    """Test Routine pre_condition handling."""

    def test_pre_condition_serialization(self, sample_routine_with_precondition):
        """to_dict includes pre_condition."""
        data = sample_routine_with_precondition.to_dict()
        assert "pre_condition" in data
        assert data["pre_condition"]["sensor_type"] == "light"

    def test_pre_condition_deserialization(self):
        """from_dict restores pre_condition."""
        data = {
            "routine_id": "test",
            "name": None,
            "trigger": {
                "trigger_type": "interval",
                "interval_minutes": 15,
                "time_window": {"start_time": "22:00", "end_time": "06:00"},
            },
            "actions": [{"action_type": "camera", "action_name": "takephoto"}],
            "pre_condition": {
                "sensor_type": "light",
                "threshold": 100,
                "comparison": "lt",
            },
        }
        routine = Routine.from_dict(data)
        assert routine.pre_condition is not None
        assert routine.pre_condition.sensor_type == "light"
        assert routine.pre_condition.threshold == 100

    def test_none_pre_condition_omitted(self, sample_routine_interval):
        """to_dict excludes null pre_condition."""
        data = sample_routine_interval.to_dict()
        # pre_condition should be None, not missing
        assert data["pre_condition"] is None

    def test_pre_condition_roundtrip(self, sample_routine_with_precondition):
        """JSON roundtrip preserves pre_condition."""
        data = sample_routine_with_precondition.to_dict()
        json_str = json.dumps(data)
        loaded = json.loads(json_str)
        restored = Routine.from_dict(loaded)
        assert restored.pre_condition is not None
        assert restored.pre_condition.sensor_type == "light"
        assert restored.pre_condition.threshold == 100
        assert restored.pre_condition.comparison == "lt"


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
        assert sample_schedule.schedule_id == "87654321-4321-8765-4321-876543218765"
        assert sample_schedule.name == "Nightly Moth Survey"
        assert len(sample_schedule.routines) == 1
        assert sample_schedule.enabled is True
        assert sample_schedule.is_active is False

    def test_uuid_generation_on_empty_id(self, sample_routine_interval):
        """Schedule generates UUID when schedule_id is empty."""
        schedule = Schedule(schedule_id="", name="Test", routines=[sample_routine_interval])
        uuid.UUID(schedule.schedule_id)

    def test_timestamps_generated(self, sample_routine_interval):
        """Schedule generates timestamps when empty."""
        schedule = Schedule(
            schedule_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            name="Test",
            routines=[sample_routine_interval],
        )
        assert schedule.created_at != ""
        assert schedule.modified_at != ""
        # Validate ISO format
        datetime.fromisoformat(schedule.created_at.replace("Z", "+00:00"))

    def test_total_duration_minutes(self, sample_schedule):
        """Schedule.total_duration_minutes sums routine durations."""
        # Single routine with duration 2 (from sample_routine_interval actions)
        assert sample_schedule.total_duration_minutes == 2

    def test_total_duration_multiple_routines(self, sample_routine_interval):
        """Schedule.total_duration_minutes handles multiple routines."""
        routine2 = Routine(
            routine_id="cccccccc-cccc-cccc-cccc-cccccccccccc",
            name="Extra",
            trigger=SolarTrigger(solar_event="dusk"),
            actions=[
                Action(action_type="gpio", action_name="flash_on", offset_minutes=10),
            ],
        )
        schedule = Schedule(
            schedule_id="dddddddd-dddd-dddd-dddd-dddddddddddd",
            name="Multi",
            routines=[sample_routine_interval, routine2],
        )
        # 2 + 10 = 12
        assert schedule.total_duration_minutes == 12

    def test_to_dict_includes_schema_version(self, sample_schedule):
        """Schedule.to_dict() includes schema_version."""
        data = sample_schedule.to_dict()
        assert data["schema_version"] == SCHEDULE_SCHEMA_VERSION
        assert data["schedule_id"] == "87654321-4321-8765-4321-876543218765"
        assert data["name"] == "Nightly Moth Survey"
        assert len(data["routines"]) == 1

    def test_from_dict(self, sample_routine_interval):
        """Schedule.from_dict() creates instance from dict (schema 3.0)."""
        routine_data = sample_routine_interval.to_dict()
        data = {
            "schema_version": "3.0",
            "schedule_id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
            "name": "Test Schedule",
            "description": "A test schedule",
            "routines": [routine_data],
            "deployment_id": "ffffffff-ffff-ffff-ffff-ffffffffffff",
            "create_deployment": True,
            "enabled": True,
            "is_active": False,
            "created_at": "2024-01-01T00:00:00Z",
            "modified_at": "2024-01-01T00:00:00Z",
            "modified_by": "user123",
        }
        schedule = Schedule.from_dict(data)
        assert schedule.schedule_id == "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
        assert schedule.name == "Test Schedule"
        assert len(schedule.routines) == 1

    def test_from_dict_rejects_old_event_patterns_format(self):
        """Schedule.from_dict() rejects old event_patterns format."""
        data = {
            "name": "Old Format",
            "event_patterns": [],
        }
        with pytest.raises(ValueError, match="event_patterns.*no longer supported"):
            Schedule.from_dict(data)

    def test_from_dict_rejects_old_trigger_type_format(self):
        """Schedule.from_dict() rejects old trigger_type format."""
        data = {
            "name": "Old Format",
            "routines": [],
            "trigger_type": "interval",
        }
        with pytest.raises(ValueError, match="Schedule-level triggers.*no longer supported"):
            Schedule.from_dict(data)

    def test_round_trip_serialization(self, sample_schedule):
        """Schedule survives JSON round-trip."""
        data = sample_schedule.to_dict()
        json_str = json.dumps(data)
        loaded = json.loads(json_str)
        restored = Schedule.from_dict(loaded)
        assert restored.schedule_id == sample_schedule.schedule_id
        assert restored.name == sample_schedule.name
        assert len(restored.routines) == len(sample_schedule.routines)


# =============================================================================
# VALIDATE PATTERN ACTION TESTS
# =============================================================================


class TestValidateAction:
    """Test validate_action function."""

    def test_valid_gpio_action(self, sample_pattern_action):
        """Valid GPIO action passes validation."""
        valid, error = validate_action(sample_pattern_action)
        assert valid is True
        assert error is None

    def test_valid_camera_action(self, sample_pattern_action_camera):
        """Valid camera action passes validation."""
        valid, error = validate_action(sample_pattern_action_camera)
        assert valid is True
        assert error is None

    def test_invalid_action_type(self):
        """Invalid action_type fails validation."""
        action = Action(action_type="invalid", action_name="test")
        valid, error = validate_action(action)
        assert valid is False
        assert "action type" in error.lower()

    def test_negative_offset_fails(self):
        """Negative offset_minutes fails validation."""
        action = Action(action_type="gpio", action_name="attract_on", offset_minutes=-5)
        valid, error = validate_action(action)
        assert valid is False
        assert "negative" in error.lower() or "offset" in error.lower()

    def test_offset_exceeds_max_fails(self):
        """Offset exceeding MAX_OFFSET_MINUTES fails validation."""
        action = Action(
            action_type="gpio",
            action_name="attract_on",
            offset_minutes=MAX_OFFSET_MINUTES + 1,
        )
        valid, error = validate_action(action)
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
        pattern = EventPattern(pattern_id="11111111-1111-1111-1111-111111111111", name="")
        valid, error = validate_event_pattern(pattern)
        assert valid is False
        assert "name" in error.lower()

    def test_name_too_long_fails(self):
        """Name exceeding MAX_PATTERN_NAME_LENGTH fails validation."""
        pattern = EventPattern(
            pattern_id="22222222-2222-2222-2222-222222222222",
            name="x" * (MAX_PATTERN_NAME_LENGTH + 1),
        )
        valid, error = validate_event_pattern(pattern)
        assert valid is False
        assert "name" in error.lower()

    def test_no_actions_fails(self):
        """Pattern with no actions fails validation."""
        pattern = EventPattern(
            pattern_id="33333333-3333-3333-3333-333333333333", name="Empty Pattern", actions=[]
        )
        valid, error = validate_event_pattern(pattern)
        assert valid is False
        assert "action" in error.lower()

    def test_too_many_actions_fails(self):
        """Pattern exceeding MAX_ACTIONS_PER_PATTERN fails validation."""
        actions = [
            Action(action_type="gpio", action_name="attract_on", offset_minutes=i)
            for i in range(MAX_ACTIONS_PER_PATTERN + 1)
        ]
        pattern = EventPattern(
            pattern_id="44444444-4444-4444-4444-444444444444", name="Too Many", actions=actions
        )
        valid, error = validate_event_pattern(pattern)
        assert valid is False
        assert "action" in error.lower()

    def test_invalid_action_fails(self):
        """Pattern with invalid action fails validation."""
        pattern = EventPattern(
            pattern_id="55555555-5555-5555-5555-555555555555",
            name="Bad Action",
            actions=[Action(action_type="invalid", action_name="test")],
        )
        valid, error = validate_event_pattern(pattern)
        assert valid is False

    def test_invalid_pattern_id_format_fails(self):
        """Pattern with invalid UUID format for pattern_id fails validation."""
        pattern = EventPattern(
            pattern_id="not-a-uuid",
            name="Test Pattern",
            actions=[Action(action_type="gpio", action_name="attract_on")],
        )
        valid, error = validate_event_pattern(pattern)
        assert valid is False
        assert "pattern_id" in error.lower()
        assert "uuid" in error.lower()


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
    """Test validate_schedule function for Schema 3.0."""

    def test_valid_schedule(self, sample_schedule):
        """Valid schedule passes validation."""
        valid, error = validate_schedule(sample_schedule)
        assert valid is True
        assert error is None

    def test_empty_name_fails(self, sample_routine_interval):
        """Empty name fails validation."""
        schedule = Schedule(
            schedule_id="66666666-6666-6666-6666-666666666666",
            name="",
            routines=[sample_routine_interval],
        )
        valid, error = validate_schedule(schedule)
        assert valid is False
        assert "name" in error.lower()

    def test_no_routines_fails(self):
        """Schedule with no routines fails validation."""
        schedule = Schedule(
            schedule_id="77777777-7777-7777-7777-777777777777",
            name="Empty",
            routines=[],
        )
        valid, error = validate_schedule(schedule)
        assert valid is False
        assert "routine" in error.lower()

    def test_too_many_routines_fails(self, sample_routine_interval):
        """Schedule with too many routines fails validation."""
        routines = []
        for i in range(MAX_ROUTINES_PER_SCHEDULE + 1):
            routines.append(
                Routine(
                    routine_id=f"aaaaaaaa-aaaa-aaaa-aaaa-{i:012d}",
                    name=f"Routine {i}",
                    trigger=sample_routine_interval.trigger,
                    actions=[Action(action_type="gpio", action_name="attract_on")],
                )
            )
        schedule = Schedule(
            schedule_id="88888888-8888-8888-8888-888888888888",
            name="Too Many Routines",
            routines=routines,
        )
        valid, error = validate_schedule(schedule)
        assert valid is False
        assert "routine" in error.lower()

    def test_invalid_schedule_id_format_fails(self, sample_routine_interval):
        """Schedule with invalid UUID format for schedule_id fails validation."""
        schedule = Schedule(
            schedule_id="not-a-uuid",
            name="Invalid ID",
            routines=[sample_routine_interval],
        )
        valid, error = validate_schedule(schedule)
        assert valid is False
        assert "schedule_id" in error.lower()
        assert "uuid" in error.lower()

    def test_duplicate_routine_ids_fails(self, sample_routine_interval):
        """Schedule with duplicate routine IDs fails validation."""
        routine2 = Routine(
            routine_id=sample_routine_interval.routine_id,  # Same ID
            name="Duplicate ID Routine",
            trigger=sample_routine_interval.trigger,
            actions=[Action(action_type="gpio", action_name="flash_on")],
        )
        schedule = Schedule(
            schedule_id="99999999-9999-9999-9999-999999999999",
            name="Duplicate Routine IDs",
            routines=[sample_routine_interval, routine2],
        )
        valid, error = validate_schedule(schedule)
        assert valid is False
        assert "duplicate" in error.lower()

    def test_invalid_routine_fails(self):
        """Schedule with invalid routine fails validation."""
        # Create a routine with invalid trigger (zero interval)
        bad_routine = Routine(
            routine_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            name="Bad Interval Routine",
            trigger=IntervalTrigger(
                interval_minutes=0,  # Invalid: must be >= 1
                time_window=TimeWindow(start_time="21:00", end_time="05:00"),
            ),
            actions=[Action(action_type="gpio", action_name="attract_on")],
        )
        schedule = Schedule(
            schedule_id="cccccccc-cccc-cccc-cccc-cccccccccccc",
            name="Has Invalid Routine",
            routines=[bad_routine],
        )
        valid, error = validate_schedule(schedule)
        assert valid is False
        assert "routine" in error.lower() or "interval" in error.lower()

    def test_description_too_long_fails(self, sample_routine_interval):
        """Schedule with description exceeding max length fails validation."""
        schedule = Schedule(
            schedule_id="dddddddd-dddd-dddd-dddd-dddddddddddd",
            name="Long Description",
            description="x" * (MAX_DESCRIPTION_LENGTH + 1),
            routines=[sample_routine_interval],
        )
        valid, error = validate_schedule(schedule)
        assert valid is False
        assert "description" in error.lower()


# =============================================================================
# CRON TRIGGER TESTS (Issue #233)
# =============================================================================


class TestCronTrigger:
    """Tests for CronTrigger dataclass."""

    def test_cron_trigger_to_dict(self):
        """CronTrigger serializes to dict correctly."""
        trigger = CronTrigger(cron_expression="0 21 * * *")
        result = trigger.to_dict()
        assert result == {"cron_expression": "0 21 * * *"}

    def test_cron_trigger_from_dict(self):
        """CronTrigger deserializes from dict correctly."""
        data = {"cron_expression": "*/5 * * * *"}
        trigger = CronTrigger.from_dict(data)
        assert trigger.cron_expression == "*/5 * * * *"

    def test_cron_in_trigger_types(self):
        """'cron' is included in TRIGGER_TYPES constant."""
        assert "cron" in TRIGGER_TYPES


class TestValidateCronTrigger:
    """Tests for validate_cron_trigger function."""

    def test_validate_cron_trigger_valid_expression(self):
        """Valid cron expression passes validation."""
        trigger = CronTrigger(cron_expression="0 21 * * *")
        valid, error = validate_cron_trigger(trigger)
        assert valid is True
        assert error is None

    def test_validate_cron_trigger_empty_string_returns_error(self):
        """Empty string cron expression fails validation."""
        trigger = CronTrigger(cron_expression="")
        valid, error = validate_cron_trigger(trigger)
        assert valid is False
        assert "empty" in error.lower()

    def test_validate_cron_trigger_whitespace_only_returns_error(self):
        """Whitespace-only cron expression fails validation."""
        trigger = CronTrigger(cron_expression="   ")
        valid, error = validate_cron_trigger(trigger)
        assert valid is False
        assert "empty" in error.lower()

    def test_validate_cron_trigger_invalid_expression_returns_error(self):
        """Invalid cron syntax fails validation."""
        trigger = CronTrigger(cron_expression="not a cron")
        valid, error = validate_cron_trigger(trigger)
        assert valid is False
        assert error is not None

    def test_validate_cron_trigger_complex_expression(self):
        """Complex cron expression validates correctly."""
        trigger = CronTrigger(cron_expression="*/15 9-17 * * 1-5")
        valid, error = validate_cron_trigger(trigger)
        assert valid is True
        assert error is None


class TestRecurringDaysTrigger:
    """Test RecurringDaysTrigger dataclass."""

    def test_instantiation_defaults(self):
        """RecurringDaysTrigger uses correct defaults."""
        trigger = RecurringDaysTrigger()
        assert trigger.every_n_days == 1
        assert trigger.time == "00:00"
        assert trigger.start_date is None

    def test_instantiation_custom_values(self):
        """RecurringDaysTrigger accepts custom values."""
        trigger = RecurringDaysTrigger(every_n_days=7, time="09:30", start_date="2025-06-01")
        assert trigger.every_n_days == 7
        assert trigger.time == "09:30"
        assert trigger.start_date == "2025-06-01"

    def test_to_dict(self):
        """to_dict returns correct dictionary without trigger_type."""
        trigger = RecurringDaysTrigger(every_n_days=3, time="21:00", start_date="2025-01-01")
        data = trigger.to_dict()
        assert data == {"every_n_days": 3, "time": "21:00", "start_date": "2025-01-01"}
        assert "trigger_type" not in data  # Should NOT include trigger_type

    def test_to_dict_none_start_date(self):
        """to_dict handles None start_date."""
        trigger = RecurringDaysTrigger()
        data = trigger.to_dict()
        assert data["start_date"] is None

    def test_from_dict_full(self):
        """from_dict creates instance with all fields."""
        data = {"every_n_days": 5, "time": "14:00", "start_date": "2025-03-15"}
        trigger = RecurringDaysTrigger.from_dict(data)
        assert trigger.every_n_days == 5
        assert trigger.time == "14:00"
        assert trigger.start_date == "2025-03-15"

    def test_from_dict_defaults(self):
        """from_dict uses defaults for missing fields."""
        trigger = RecurringDaysTrigger.from_dict({})
        assert trigger.every_n_days == 1
        assert trigger.time == "00:00"
        assert trigger.start_date is None

    def test_round_trip_serialization(self):
        """RecurringDaysTrigger survives JSON round-trip."""
        original = RecurringDaysTrigger(every_n_days=10, time="06:00", start_date="2025-07-04")
        data = original.to_dict()
        restored = RecurringDaysTrigger.from_dict(data)
        assert restored.every_n_days == original.every_n_days
        assert restored.time == original.time
        assert restored.start_date == original.start_date


class TestValidateRecurringDaysTrigger:
    """Test validate_recurring_days_trigger function."""

    def test_valid_default_trigger(self):
        """Default trigger passes validation."""
        trigger = RecurringDaysTrigger()
        valid, error = validate_recurring_days_trigger(trigger)
        assert valid is True
        assert error is None

    def test_valid_custom_trigger(self):
        """Custom valid trigger passes validation."""
        trigger = RecurringDaysTrigger(every_n_days=30, time="12:00", start_date="2025-01-01")
        valid, error = validate_recurring_days_trigger(trigger)
        assert valid is True
        assert error is None

    def test_every_n_days_zero_fails(self):
        """every_n_days=0 fails validation."""
        trigger = RecurringDaysTrigger(every_n_days=0)
        valid, error = validate_recurring_days_trigger(trigger)
        assert valid is False
        assert "at least 1" in error

    def test_every_n_days_negative_fails(self):
        """Negative every_n_days fails validation."""
        trigger = RecurringDaysTrigger(every_n_days=-5)
        valid, error = validate_recurring_days_trigger(trigger)
        assert valid is False
        assert "at least 1" in error

    def test_every_n_days_at_max_passes(self):
        """every_n_days=365 passes validation."""
        trigger = RecurringDaysTrigger(every_n_days=365)
        valid, error = validate_recurring_days_trigger(trigger)
        assert valid is True

    def test_every_n_days_exceeds_max_fails(self):
        """every_n_days > 365 fails validation."""
        trigger = RecurringDaysTrigger(every_n_days=366)
        valid, error = validate_recurring_days_trigger(trigger)
        assert valid is False
        assert "365" in error

    def test_invalid_time_format_fails(self):
        """Invalid time format fails validation."""
        trigger = RecurringDaysTrigger(time="25:00")
        valid, error = validate_recurring_days_trigger(trigger)
        assert valid is False
        assert "time" in error.lower()

    def test_invalid_start_date_format_fails(self):
        """Invalid start_date format fails validation."""
        trigger = RecurringDaysTrigger(start_date="2025/01/01")
        valid, error = validate_recurring_days_trigger(trigger)
        assert valid is False
        assert "start_date" in error

    def test_invalid_start_date_value_fails(self):
        """Impossible date fails validation."""
        trigger = RecurringDaysTrigger(start_date="2025-02-30")
        valid, error = validate_recurring_days_trigger(trigger)
        assert valid is False
        assert "start_date" in error


class TestTriggerFromDict:
    """Test trigger_from_dict factory function."""

    def test_interval_trigger(self):
        """trigger_from_dict creates IntervalTrigger."""
        data = {
            "trigger_type": "interval",
            "interval_minutes": 60,
            "time_window": {"start_time": "21:00", "end_time": "05:00"},
        }
        trigger = trigger_from_dict(data)
        assert isinstance(trigger, IntervalTrigger)
        assert trigger.interval_minutes == 60

    def test_solar_trigger(self):
        """trigger_from_dict creates SolarTrigger."""
        data = {"trigger_type": "solar", "solar_event": "sunset"}
        trigger = trigger_from_dict(data)
        assert isinstance(trigger, SolarTrigger)
        assert trigger.solar_event == "sunset"

    def test_moon_phase_trigger(self):
        """trigger_from_dict creates MoonPhaseTrigger."""
        data = {"trigger_type": "moon_phase", "phases": ["full", "new"]}
        trigger = trigger_from_dict(data)
        assert isinstance(trigger, MoonPhaseTrigger)
        assert trigger.phases == ["full", "new"]

    def test_fixed_time_trigger(self):
        """trigger_from_dict creates FixedTimeTrigger."""
        data = {"trigger_type": "fixed_time", "time": "09:00"}
        trigger = trigger_from_dict(data)
        assert isinstance(trigger, FixedTimeTrigger)
        assert trigger.time == "09:00"

    def test_sensor_trigger(self):
        """trigger_from_dict creates SensorTrigger."""
        data = {"trigger_type": "sensor", "sensor_type": "motion"}
        trigger = trigger_from_dict(data)
        assert isinstance(trigger, SensorTrigger)
        assert trigger.sensor_type == "motion"

    def test_cron_trigger(self):
        """trigger_from_dict creates CronTrigger."""
        data = {"trigger_type": "cron", "cron_expression": "0 * * * *"}
        trigger = trigger_from_dict(data)
        assert isinstance(trigger, CronTrigger)
        assert trigger.cron_expression == "0 * * * *"

    def test_recurring_days_trigger(self):
        """trigger_from_dict creates RecurringDaysTrigger."""
        data = {"trigger_type": "recurring_days", "every_n_days": 3, "time": "21:00"}
        trigger = trigger_from_dict(data)
        assert isinstance(trigger, RecurringDaysTrigger)
        assert trigger.every_n_days == 3
        assert trigger.time == "21:00"

    def test_missing_trigger_type_raises(self):
        """Missing trigger_type raises ValueError."""
        with pytest.raises(ValueError, match="trigger_type is required"):
            trigger_from_dict({})

    def test_unknown_trigger_type_raises(self):
        """Unknown trigger_type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown trigger_type"):
            trigger_from_dict({"trigger_type": "invalid"})


class TestRoutineWithCronTrigger:
    """Tests for Routine with cron trigger type."""

    def test_routine_with_cron_trigger_validates(self):
        """Routine with valid cron trigger passes validation."""
        routine = Routine(
            routine_id="eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
            name="Expert Mode Routine",
            trigger=CronTrigger(cron_expression="0 21 * * *"),
            actions=[Action(action_type="gpio", action_name="attract_on")],
        )
        valid, error = validate_routine(routine)
        assert valid is True
        assert error is None

    def test_routine_with_invalid_cron_expression_fails(self):
        """Routine with invalid cron expression fails validation."""
        routine = Routine(
            routine_id="ffffffff-ffff-ffff-ffff-ffffffffffff",
            name="Bad Cron Routine",
            trigger=CronTrigger(cron_expression="invalid cron"),
            actions=[Action(action_type="gpio", action_name="attract_on")],
        )
        valid, error = validate_routine(routine)
        assert valid is False
        assert "cron" in error.lower()

    def test_routine_cron_trigger_serialization(self):
        """Routine with cron trigger serializes and deserializes correctly."""
        routine = Routine(
            routine_id="11111111-2222-3333-4444-555555555555",
            name="Cron Routine",
            trigger=CronTrigger(cron_expression="0 */2 * * *"),
            actions=[Action(action_type="gpio", action_name="flash_on")],
        )

        # Serialize
        data = routine.to_dict()
        assert data["trigger"]["trigger_type"] == "cron"
        assert data["trigger"]["cron_expression"] == "0 */2 * * *"

        # Deserialize
        restored = Routine.from_dict(data)
        assert isinstance(restored.trigger, CronTrigger)
        assert restored.trigger.cron_expression == "0 */2 * * *"


class TestRoutineWithRecurringDaysTrigger:
    """Tests for Routine with recurring_days trigger type."""

    def test_routine_with_recurring_days_trigger_validates(self):
        """Routine with valid recurring_days trigger passes validation."""
        routine = Routine(
            routine_id="22222222-3333-4444-5555-666666666666",
            name="GPS Sync Every 3 Days",
            trigger=RecurringDaysTrigger(
                every_n_days=3,
                time="21:00",
                start_date="2025-01-01",
            ),
            actions=[Action(action_type="gps_sync", action_name="sync")],
        )
        valid, error = validate_routine(routine)
        assert valid is True
        assert error is None

    def test_routine_with_invalid_recurring_days_fails(self):
        """Routine with invalid every_n_days fails validation."""
        routine = Routine(
            routine_id="33333333-4444-5555-6666-777777777777",
            name="Invalid Recurring Days",
            trigger=RecurringDaysTrigger(
                every_n_days=0,  # Invalid: must be at least 1
                time="21:00",
            ),
            actions=[Action(action_type="gpio", action_name="attract_on")],
        )
        valid, error = validate_routine(routine)
        assert valid is False
        assert "at least 1" in error

    def test_routine_recurring_days_trigger_serialization(self):
        """Routine with recurring_days trigger serializes and deserializes correctly."""
        routine = Routine(
            routine_id="44444444-5555-6666-7777-888888888888",
            name="Weekly Sync",
            trigger=RecurringDaysTrigger(
                every_n_days=7,
                time="09:00",
                start_date="2025-06-01",
            ),
            actions=[Action(action_type="gps_sync", action_name="sync")],
        )

        # Serialize
        data = routine.to_dict()
        assert data["trigger"]["trigger_type"] == "recurring_days"
        assert data["trigger"]["every_n_days"] == 7
        assert data["trigger"]["time"] == "09:00"
        assert data["trigger"]["start_date"] == "2025-06-01"

        # Deserialize
        restored = Routine.from_dict(data)
        assert isinstance(restored.trigger, RecurringDaysTrigger)
        assert restored.trigger.every_n_days == 7
        assert restored.trigger.time == "09:00"
        assert restored.trigger.start_date == "2025-06-01"


# =============================================================================
# SCHEMA 3.0 - SCHEDULE FROM_DICT TESTS
# =============================================================================


class TestScheduleFromDict:
    """Test Schedule.from_dict() for Schema 3.0."""

    def test_from_dict_valid_schedule(self, sample_routine_interval):
        """Valid schedule data deserializes correctly."""
        data = {
            "schedule_id": "55555555-6666-7777-8888-999999999999",
            "name": "My Test Schedule",
            "description": "A test schedule",
            "routines": [sample_routine_interval.to_dict()],
            "enabled": True,
            "is_active": False,
        }
        schedule = Schedule.from_dict(data)
        assert schedule.schedule_id == "55555555-6666-7777-8888-999999999999"
        assert schedule.name == "My Test Schedule"
        assert schedule.description == "A test schedule"
        assert len(schedule.routines) == 1
        assert schedule.enabled is True
        assert schedule.is_active is False

    def test_from_dict_rejects_event_patterns(self, sample_event_pattern):
        """from_dict rejects old schema with event_patterns."""
        data = {
            "name": "Old Schema Schedule",
            "event_patterns": [sample_event_pattern.to_dict()],
            "trigger_type": "interval",
        }
        with pytest.raises(ValueError, match="event_patterns.*no longer supported"):
            Schedule.from_dict(data)

    def test_from_dict_rejects_schedule_level_trigger_type(self, sample_routine_interval):
        """from_dict rejects old schema with schedule-level trigger_type."""
        data = {
            "name": "Old Schema Schedule",
            "routines": [sample_routine_interval.to_dict()],
            "trigger_type": "interval",
        }
        with pytest.raises(ValueError, match="Schedule-level triggers.*no longer supported"):
            Schedule.from_dict(data)

    def test_from_dict_rejects_schedule_level_trigger(self, sample_routine_interval):
        """from_dict rejects old schema with schedule-level trigger object."""
        data = {
            "name": "Old Schema Schedule",
            "routines": [sample_routine_interval.to_dict()],
            "trigger": {"trigger_type": "interval", "interval_minutes": 60},
        }
        with pytest.raises(ValueError, match="Schedule-level triggers.*no longer supported"):
            Schedule.from_dict(data)

    def test_from_dict_multiple_routines(self):
        """Schedule with multiple routines deserializes correctly."""
        routine1 = Routine(
            routine_id="aaaa1111-aaaa-1111-aaaa-111111111111",
            name="Morning Routine",
            trigger=FixedTimeTrigger(time="06:00"),
            actions=[Action(action_type="gpio", action_name="attract_on")],
        )
        routine2 = Routine(
            routine_id="bbbb2222-bbbb-2222-bbbb-222222222222",
            name="Evening Routine",
            trigger=SolarTrigger(solar_event="sunset"),
            actions=[Action(action_type="camera", action_name="takephoto")],
        )
        data = {
            "schedule_id": "cccc3333-cccc-3333-cccc-333333333333",
            "name": "Multi-Routine Schedule",
            "routines": [routine1.to_dict(), routine2.to_dict()],
        }
        schedule = Schedule.from_dict(data)
        assert len(schedule.routines) == 2
        assert schedule.routines[0].name == "Morning Routine"
        assert schedule.routines[1].name == "Evening Routine"
        assert isinstance(schedule.routines[0].trigger, FixedTimeTrigger)
        assert isinstance(schedule.routines[1].trigger, SolarTrigger)

    def test_from_dict_accepts_valid_schema_version(self, sample_routine_interval):
        """Valid schema version 3.0 should be accepted."""
        data = {
            "schema_version": "3.0",
            "name": "Test Schedule",
            "routines": [sample_routine_interval.to_dict()],
        }
        schedule = Schedule.from_dict(data)
        assert schedule.name == "Test Schedule"

    def test_from_dict_rejects_unsupported_schema_version(self, sample_routine_interval):
        """Unsupported schema versions should raise ValueError."""
        data = {
            "schema_version": "2.0",
            "name": "Test Schedule",
            "routines": [sample_routine_interval.to_dict()],
        }
        with pytest.raises(ValueError, match="Unsupported schema version"):
            Schedule.from_dict(data)

    def test_from_dict_rejects_future_schema_version(self, sample_routine_interval):
        """Future schema versions should raise ValueError."""
        data = {
            "schema_version": "4.0",
            "name": "Test Schedule",
            "routines": [sample_routine_interval.to_dict()],
        }
        with pytest.raises(ValueError, match="Unsupported schema version"):
            Schedule.from_dict(data)

    def test_from_dict_accepts_missing_schema_version(self, sample_routine_interval):
        """Missing schema_version should be accepted (for API payloads)."""
        data = {
            "name": "Test Schedule",
            "routines": [sample_routine_interval.to_dict()],
        }
        schedule = Schedule.from_dict(data)
        assert schedule.name == "Test Schedule"


class TestRoutineIdsUniqueValidation:
    """Tests for empty routine ID validation in validate_routine_ids_unique()."""

    def test_empty_routine_id_rejected(self):
        """Empty string routine IDs should be rejected."""
        # Create routine normally then force empty ID to bypass post_init
        routine = Routine(
            routine_id="temp-id",
            name="Test Routine",
            trigger=FixedTimeTrigger(time="21:00"),
            actions=[Action(action_type="camera", action_name="takephoto")],
        )
        routine.routine_id = ""  # Force empty after init

        schedule = Schedule(
            schedule_id="test-schedule-id",
            name="Test Schedule",
            routines=[routine],
        )
        valid, error = validate_routine_ids_unique(schedule)
        assert not valid
        assert "empty" in error.lower()

    def test_none_routine_id_rejected(self):
        """None routine IDs should be rejected."""
        routine = Routine(
            routine_id="temp-id",
            name="Test Routine",
            trigger=FixedTimeTrigger(time="21:00"),
            actions=[Action(action_type="camera", action_name="takephoto")],
        )
        routine.routine_id = None  # Force None after init

        schedule = Schedule(
            schedule_id="test-schedule-id",
            name="Test Schedule",
            routines=[routine],
        )
        valid, error = validate_routine_ids_unique(schedule)
        assert not valid
        assert "empty" in error.lower()

    def test_valid_routine_ids_accepted(self):
        """Valid non-empty routine IDs should be accepted."""
        routine = Routine(
            routine_id="valid-uuid-here",
            name="Test Routine",
            trigger=FixedTimeTrigger(time="21:00"),
            actions=[Action(action_type="camera", action_name="takephoto")],
        )

        schedule = Schedule(
            schedule_id="test-schedule-id",
            name="Test Schedule",
            routines=[routine],
        )
        valid, error = validate_routine_ids_unique(schedule)
        assert valid
        assert error is None


class TestScheduleSerialization:
    """Test Schedule serialization (to_dict/from_dict) round-trip."""

    def test_schedule_round_trip(self, sample_schedule):
        """Schedule survives serialization round-trip."""
        data = sample_schedule.to_dict()
        restored = Schedule.from_dict(data)

        assert restored.schedule_id == sample_schedule.schedule_id
        assert restored.name == sample_schedule.name
        assert restored.description == sample_schedule.description
        assert len(restored.routines) == len(sample_schedule.routines)
        assert restored.enabled == sample_schedule.enabled
        assert restored.is_active == sample_schedule.is_active

    def test_schedule_json_round_trip(self, sample_schedule):
        """Schedule survives JSON round-trip."""
        data = sample_schedule.to_dict()
        json_str = json.dumps(data)
        restored_data = json.loads(json_str)
        restored = Schedule.from_dict(restored_data)

        assert restored.schedule_id == sample_schedule.schedule_id
        assert restored.name == sample_schedule.name

    def test_to_dict_includes_schema_version(self, sample_schedule):
        """to_dict includes schema_version field."""
        data = sample_schedule.to_dict()
        assert data["schema_version"] == "3.0"

    def test_to_dict_serializes_routines(self, sample_schedule):
        """to_dict properly serializes routines."""
        data = sample_schedule.to_dict()
        assert "routines" in data
        assert len(data["routines"]) == 1
        routine_data = data["routines"][0]
        assert "routine_id" in routine_data
        assert "name" in routine_data
        assert "trigger" in routine_data
        assert "actions" in routine_data


class TestScheduleWithMixedTriggerTypes:
    """Test schedules with routines using different trigger types."""

    def test_schedule_with_interval_and_solar_routines(self):
        """Schedule can have routines with different trigger types."""
        interval_routine = Routine(
            routine_id="dddd4444-dddd-4444-dddd-444444444444",
            name="Hourly Check",
            trigger=IntervalTrigger(
                interval_minutes=60,
                time_window=TimeWindow(start_time="21:00", end_time="05:00"),
            ),
            actions=[Action(action_type="gpio", action_name="flash_on")],
        )
        solar_routine = Routine(
            routine_id="eeee5555-eeee-5555-eeee-555555555555",
            name="Sunset Start",
            trigger=SolarTrigger(solar_event="sunset", offset_minutes=30),
            actions=[Action(action_type="gpio", action_name="attract_on")],
        )
        schedule = Schedule(
            schedule_id="ffff6666-ffff-6666-ffff-666666666666",
            name="Mixed Trigger Schedule",
            routines=[interval_routine, solar_routine],
        )

        valid, error = validate_schedule(schedule)
        assert valid is True
        assert error is None

        # Round-trip
        data = schedule.to_dict()
        restored = Schedule.from_dict(data)
        assert len(restored.routines) == 2
        assert isinstance(restored.routines[0].trigger, IntervalTrigger)
        assert isinstance(restored.routines[1].trigger, SolarTrigger)

    def test_schedule_with_all_trigger_types(self):
        """Schedule with routines using all trigger types validates."""
        routines = [
            Routine(
                routine_id="11111111-1111-1111-1111-111111111111",
                name="Interval Routine",
                trigger=IntervalTrigger(
                    interval_minutes=30,
                    time_window=TimeWindow(start_time="20:00", end_time="06:00"),
                ),
                actions=[Action(action_type="gpio", action_name="attract_on")],
            ),
            Routine(
                routine_id="22222222-2222-2222-2222-222222222222",
                name="Solar Routine",
                trigger=SolarTrigger(solar_event="sunrise"),
                actions=[Action(action_type="gpio", action_name="attract_off")],
            ),
            Routine(
                routine_id="33333333-3333-3333-3333-333333333333",
                name="Fixed Time Routine",
                trigger=FixedTimeTrigger(time="12:00"),
                actions=[Action(action_type="camera", action_name="takephoto")],
            ),
            Routine(
                routine_id="44444444-4444-4444-4444-444444444444",
                name="Cron Routine",
                trigger=CronTrigger(cron_expression="0 */6 * * *"),
                actions=[Action(action_type="gps_sync", action_name="sync")],
            ),
        ]
        schedule = Schedule(
            schedule_id="00000000-0000-0000-0000-000000000000",
            name="All Trigger Types",
            routines=routines,
        )

        valid, error = validate_schedule(schedule)
        assert valid is True
        assert error is None

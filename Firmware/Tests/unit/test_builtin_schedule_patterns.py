"""
Unit tests for built-in schedule patterns (Schema 3.0).

Tests for the two Schema 3.0 builtin schedules:
- overnight-moth-survey.json (3 routines: solar + interval triggers)
- daytime-pollinator.json (1 routine: interval trigger)

Each builtin is validated for:
1. Valid JSON structure
2. Schema version 3.0
3. Builtin flag
4. Valid UUID schedule ID
5. Correct trigger types and actions
6. Passes validate_schedule()
"""

import json
import uuid
from pathlib import Path

import pytest

from webui.backend.lib.schedule_schema import (
    Schedule,
    validate_schedule,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def builtin_schedules_dir() -> Path:
    """Get the built-in schedules directory."""
    return (
        Path(__file__).parent.parent.parent
        / "webui"
        / "backend"
        / "presets_builtin"
        / "schedules"
    )


@pytest.fixture
def all_schedule_files(builtin_schedules_dir: Path) -> list[Path]:
    """Get all JSON schedule files from built-in directory."""
    if not builtin_schedules_dir.exists():
        pytest.skip(f"Built-in schedules directory not found: {builtin_schedules_dir}")
    return list(builtin_schedules_dir.glob("*.json"))


@pytest.fixture
def all_schedules(all_schedule_files: list[Path]) -> list[dict]:
    """Load and parse all schedule JSON files."""
    schedules = []
    for file_path in all_schedule_files:
        with open(file_path) as f:
            schedules.append(json.load(f))
    return schedules


# =============================================================================
# TEST: ALL BUILTIN SCHEDULES (Generic Validation)
# =============================================================================


class TestAllBuiltinSchedules:
    """Generic tests for all Schema 3.0 builtin schedules."""

    def test_all_builtins_exist(self, builtin_schedules_dir: Path) -> None:
        """All expected builtin schedules must exist."""
        expected = ["overnight-moth-survey.json", "daytime-pollinator.json"]
        for filename in expected:
            path = builtin_schedules_dir / filename
            assert path.exists(), f"Missing builtin: {filename}"

    def test_all_builtins_are_valid_json(self, all_schedule_files: list[Path]) -> None:
        """All builtin schedules must be valid JSON."""
        for file_path in all_schedule_files:
            with open(file_path) as f:
                data = json.load(f)
            assert isinstance(data, dict)

    def test_all_builtins_use_schema_v3(self, all_schedules: list[dict]) -> None:
        """All builtins must use schema version 3.0."""
        for schedule in all_schedules:
            assert schedule.get("version") == "3.0"

    def test_all_builtins_marked_as_builtin(self, all_schedules: list[dict]) -> None:
        """All builtins must have is_builtin=true."""
        for schedule in all_schedules:
            assert schedule.get("is_builtin") is True

    def test_all_builtins_pass_validation(self, all_schedules: list[dict]) -> None:
        """All builtins must pass schema validation."""
        for schedule_data in all_schedules:
            schedule = Schedule.from_dict(schedule_data)
            valid, error = validate_schedule(schedule)
            assert valid, f"{schedule_data['name']} failed: {error}"


# =============================================================================
# TEST: OVERNIGHT-MOTH-SURVEY.JSON (Schema 3.0)
# =============================================================================


class TestOvernightMothSurveySchedule:
    """Tests for overnight-moth-survey.json (Schema 3.0)."""

    @pytest.fixture
    def overnight_moth_survey_schedule(self, builtin_schedules_dir: Path) -> dict:
        """Load overnight-moth-survey.json schedule."""
        path = builtin_schedules_dir / "overnight-moth-survey.json"
        if not path.exists():
            pytest.skip("overnight-moth-survey.json not found")
        with open(path) as f:
            return json.load(f)

    def test_schedule_exists(self, builtin_schedules_dir: Path) -> None:
        """overnight-moth-survey.json must exist."""
        path = builtin_schedules_dir / "overnight-moth-survey.json"
        assert path.exists()

    def test_schedule_is_valid_json(
        self, overnight_moth_survey_schedule: dict
    ) -> None:
        """Schedule must be valid JSON with required fields."""
        assert "schedule_id" in overnight_moth_survey_schedule
        assert "name" in overnight_moth_survey_schedule
        assert "routines" in overnight_moth_survey_schedule

    def test_schedule_id_is_valid_uuid(
        self, overnight_moth_survey_schedule: dict
    ) -> None:
        """Schedule ID must be a valid UUID."""
        uuid.UUID(overnight_moth_survey_schedule["schedule_id"])

    def test_uses_schema_v3(self, overnight_moth_survey_schedule: dict) -> None:
        """Must use schema version 3.0."""
        assert overnight_moth_survey_schedule.get("version") == "3.0"

    def test_is_builtin(self, overnight_moth_survey_schedule: dict) -> None:
        """Must be marked as builtin."""
        assert overnight_moth_survey_schedule.get("is_builtin") is True

    def test_has_three_routines(self, overnight_moth_survey_schedule: dict) -> None:
        """Must have exactly three routines."""
        routines = overnight_moth_survey_schedule["routines"]
        assert len(routines) == 3

    def test_routine_names(self, overnight_moth_survey_schedule: dict) -> None:
        """Routines must have expected names."""
        routines = overnight_moth_survey_schedule["routines"]
        names = [r["name"] for r in routines]
        assert "Lights On at Dusk" in names
        assert "Photo Capture" in names
        assert "Lights Off at Dawn" in names

    def test_lights_on_routine_uses_solar_trigger(
        self, overnight_moth_survey_schedule: dict
    ) -> None:
        """First routine must use solar trigger at dusk."""
        routine = overnight_moth_survey_schedule["routines"][0]
        trigger = routine["trigger"]
        assert trigger["trigger_type"] == "solar"
        assert trigger["solar_event"] == "dusk"

    def test_photo_capture_routine_uses_interval_trigger(
        self, overnight_moth_survey_schedule: dict
    ) -> None:
        """Second routine must use interval trigger."""
        routine = overnight_moth_survey_schedule["routines"][1]
        trigger = routine["trigger"]
        assert trigger["trigger_type"] == "interval"
        assert trigger["interval_minutes"] == 15

    def test_photo_capture_time_window(
        self, overnight_moth_survey_schedule: dict
    ) -> None:
        """Photo capture time window must be dusk to dawn."""
        routine = overnight_moth_survey_schedule["routines"][1]
        time_window = routine["trigger"]["time_window"]
        assert time_window["start_time"] == "dusk"
        assert time_window["end_time"] == "dawn"

    def test_lights_off_routine_uses_solar_trigger(
        self, overnight_moth_survey_schedule: dict
    ) -> None:
        """Third routine must use solar trigger at dawn."""
        routine = overnight_moth_survey_schedule["routines"][2]
        trigger = routine["trigger"]
        assert trigger["trigger_type"] == "solar"
        assert trigger["solar_event"] == "dawn"

    def test_has_attract_on_action(
        self, overnight_moth_survey_schedule: dict
    ) -> None:
        """First routine must have attract_on action."""
        routine = overnight_moth_survey_schedule["routines"][0]
        action_names = [a["action_name"] for a in routine["actions"]]
        assert "attract_on" in action_names

    def test_has_takephoto_action(
        self, overnight_moth_survey_schedule: dict
    ) -> None:
        """Second routine must have takephoto action."""
        routine = overnight_moth_survey_schedule["routines"][1]
        action_names = [a["action_name"] for a in routine["actions"]]
        assert "takephoto" in action_names

    def test_has_flash_sequence(self, overnight_moth_survey_schedule: dict) -> None:
        """Second routine must have flash_on and flash_off."""
        routine = overnight_moth_survey_schedule["routines"][1]
        action_names = [a["action_name"] for a in routine["actions"]]
        assert "flash_on" in action_names
        assert "flash_off" in action_names

    def test_has_attract_off_action(
        self, overnight_moth_survey_schedule: dict
    ) -> None:
        """Third routine must have attract_off action."""
        routine = overnight_moth_survey_schedule["routines"][2]
        action_names = [a["action_name"] for a in routine["actions"]]
        assert "attract_off" in action_names

    def test_passes_schema_validation(
        self, overnight_moth_survey_schedule: dict
    ) -> None:
        """Schedule must pass validate_schedule()."""
        schedule = Schedule.from_dict(overnight_moth_survey_schedule)
        valid, error = validate_schedule(schedule)
        assert valid, f"Validation failed: {error}"


# =============================================================================
# TEST: DAYTIME-POLLINATOR.JSON (Schema 3.0)
# =============================================================================


class TestDaytimePollinatorSchedule:
    """Tests for daytime-pollinator.json schedule (Schema 3.0)."""

    @pytest.fixture
    def daytime_pollinator_schedule(self, builtin_schedules_dir: Path) -> dict:
        """Load daytime-pollinator.json schedule."""
        path = builtin_schedules_dir / "daytime-pollinator.json"
        if not path.exists():
            pytest.skip("daytime-pollinator.json not found")
        with open(path) as f:
            return json.load(f)

    def test_schedule_exists(self, builtin_schedules_dir: Path) -> None:
        """daytime-pollinator.json must exist."""
        path = builtin_schedules_dir / "daytime-pollinator.json"
        assert path.exists(), "daytime-pollinator.json not found"

    def test_schedule_is_valid_json(self, daytime_pollinator_schedule: dict) -> None:
        """Schedule must be valid JSON with required fields."""
        assert "schedule_id" in daytime_pollinator_schedule
        assert "name" in daytime_pollinator_schedule
        assert "routines" in daytime_pollinator_schedule

    def test_schedule_id_is_valid_uuid(
        self, daytime_pollinator_schedule: dict
    ) -> None:
        """Schedule ID must be a valid UUID."""
        schedule_id = daytime_pollinator_schedule["schedule_id"]
        try:
            uuid.UUID(schedule_id)
        except ValueError:
            pytest.fail(f"schedule_id '{schedule_id}' is not a valid UUID")

    def test_uses_schema_v3(self, daytime_pollinator_schedule: dict) -> None:
        """Must use schema version 3.0."""
        version = daytime_pollinator_schedule.get("version")
        assert version == "3.0", f"Expected version '3.0', got '{version}'"

    def test_is_builtin(self, daytime_pollinator_schedule: dict) -> None:
        """Must be marked as builtin."""
        assert daytime_pollinator_schedule.get("is_builtin") is True

    def test_has_single_routine(self, daytime_pollinator_schedule: dict) -> None:
        """Must have exactly one routine."""
        routines = daytime_pollinator_schedule["routines"]
        assert len(routines) == 1, f"Expected 1 routine, got {len(routines)}"

    def test_routine_uses_interval_trigger(
        self, daytime_pollinator_schedule: dict
    ) -> None:
        """Routine must use interval trigger type."""
        routine = daytime_pollinator_schedule["routines"][0]
        trigger = routine["trigger"]
        assert trigger["trigger_type"] == "interval"

    def test_interval_is_10_minutes(self, daytime_pollinator_schedule: dict) -> None:
        """Interval must be exactly 10 minutes."""
        routine = daytime_pollinator_schedule["routines"][0]
        trigger = routine["trigger"]
        assert trigger["interval_minutes"] == 10

    def test_time_window_is_sunrise_to_sunset(
        self, daytime_pollinator_schedule: dict
    ) -> None:
        """Time window must be solar-based (sunrise to sunset)."""
        routine = daytime_pollinator_schedule["routines"][0]
        time_window = routine["trigger"]["time_window"]
        assert time_window["start_time"] == "sunrise"
        assert time_window["end_time"] == "sunset"

    def test_has_takephoto_action(self, daytime_pollinator_schedule: dict) -> None:
        """Must have a takephoto action."""
        routine = daytime_pollinator_schedule["routines"][0]
        actions = routine["actions"]
        action_names = [a["action_name"] for a in actions]
        assert "takephoto" in action_names

    def test_passes_schema_validation(
        self, daytime_pollinator_schedule: dict
    ) -> None:
        """Schedule must pass validate_schedule()."""
        schedule = Schedule.from_dict(daytime_pollinator_schedule)
        valid, error = validate_schedule(schedule)
        assert valid, f"Validation failed: {error}"

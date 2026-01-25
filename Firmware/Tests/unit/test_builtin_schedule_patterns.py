"""
Unit tests for built-in schedule patterns (Issue #220).

NOTE: This test file is skipped because:
1. Issue #220 required 5 specific Schema 2.0 schedule files
2. Schema 3.0 migration (Issue #300) changed the schedule format
3. The codebase now uses only 2 builtin schedules in Schema 3.0 format:
   - overnight-moth-survey.json
   - daytime-pollinator.json
4. Issue #220 requirements are deferred pending Schema 3.0 builtin schedule design

Original test purpose - tests that all required built-in schedule patterns:
1. Parse as valid JSON
2. Pass schema validation
3. Have unique schedule IDs
4. Use correct trigger types
5. Meet the Issue #220 acceptance criteria

The 5 required schedules were:
- nightly_hourly.json (interval trigger, fixed time 01:00-06:00)
- full_moon_survey.json (moon phase trigger, dusk-dawn solar window)
- dawn_transect.json (solar trigger at sunrise-15min)
- dusk_transect.json (solar trigger at sunset-15min)
- continuous_monitoring.json (interval trigger, solar window sunset-sunrise)
"""

import json
import uuid
from pathlib import Path

import pytest

# Skip entire module - Issue #220 schedules deferred pending Schema 3.0 builtin design
pytestmark = pytest.mark.skip(
    reason="Issue #220 schedules deferred. Codebase uses only 2 Schema 3.0 builtins: "
    "overnight-moth-survey.json and daytime-pollinator.json"
)

from webui.backend.lib.schedule_schema import (
    SOLAR_EVENTS,
    TRIGGER_TYPES,
    Schedule,
    validate_schedule,
)

# =============================================================================
# CONSTANTS
# =============================================================================

# Issue #220 required schedule IDs
REQUIRED_SCHEDULES_220 = [
    "nightly_hourly",
    "full_moon_survey",
    "dawn_transect",
    "dusk_transect",
    "continuous_monitoring",
]


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


@pytest.fixture
def schedule_220_files(builtin_schedules_dir: Path) -> dict[str, Path]:
    """Get the 4 issue #220 schedule files."""
    files = {}
    for schedule_id in REQUIRED_SCHEDULES_220:
        path = builtin_schedules_dir / f"{schedule_id}.json"
        if path.exists():
            files[schedule_id] = path
    return files


@pytest.fixture
def schedule_220_data(schedule_220_files: dict[str, Path]) -> dict[str, dict]:
    """Load and parse the 4 issue #220 schedule files."""
    data = {}
    for schedule_id, path in schedule_220_files.items():
        with open(path) as f:
            data[schedule_id] = json.load(f)
    return data


# Individual schedule fixtures
@pytest.fixture
def nightly_hourly_schedule(builtin_schedules_dir: Path) -> dict:
    """Load nightly_hourly.json schedule."""
    path = builtin_schedules_dir / "nightly_hourly.json"
    if not path.exists():
        pytest.skip("nightly_hourly.json not found")
    with open(path) as f:
        return json.load(f)


@pytest.fixture
def full_moon_survey_schedule(builtin_schedules_dir: Path) -> dict:
    """Load full_moon_survey.json schedule."""
    path = builtin_schedules_dir / "full_moon_survey.json"
    if not path.exists():
        pytest.skip("full_moon_survey.json not found")
    with open(path) as f:
        return json.load(f)


@pytest.fixture
def dawn_transect_schedule(builtin_schedules_dir: Path) -> dict:
    """Load dawn_transect.json schedule."""
    path = builtin_schedules_dir / "dawn_transect.json"
    if not path.exists():
        pytest.skip("dawn_transect.json not found")
    with open(path) as f:
        return json.load(f)


@pytest.fixture
def dusk_transect_schedule(builtin_schedules_dir: Path) -> dict:
    """Load dusk_transect.json schedule."""
    path = builtin_schedules_dir / "dusk_transect.json"
    if not path.exists():
        pytest.skip("dusk_transect.json not found")
    with open(path) as f:
        return json.load(f)


@pytest.fixture
def continuous_monitoring_schedule(builtin_schedules_dir: Path) -> dict:
    """Load continuous_monitoring.json schedule."""
    path = builtin_schedules_dir / "continuous_monitoring.json"
    if not path.exists():
        pytest.skip("continuous_monitoring.json not found")
    with open(path) as f:
        return json.load(f)


# =============================================================================
# TEST: SCHEDULE FILES EXIST (Issue #220 Acceptance Criteria)
# =============================================================================


class TestIssue220SchedulesExist:
    """Test that all 4 required Issue #220 schedules exist."""

    def test_all_required_220_schedules_exist(
        self, builtin_schedules_dir: Path
    ) -> None:
        """All 4 Issue #220 schedules must exist as JSON files."""
        missing = []
        for schedule_id in REQUIRED_SCHEDULES_220:
            path = builtin_schedules_dir / f"{schedule_id}.json"
            if not path.exists():
                missing.append(schedule_id)

        assert not missing, f"Missing required schedules: {missing}"

    def test_all_220_files_are_valid_json(
        self, schedule_220_files: dict[str, Path]
    ) -> None:
        """All #220 schedule files must parse as valid JSON."""
        for schedule_id, path in schedule_220_files.items():
            try:
                with open(path) as f:
                    data = json.load(f)
                assert isinstance(data, dict), f"{schedule_id}: Root must be dict"
            except json.JSONDecodeError as e:
                pytest.fail(f"{schedule_id}: Invalid JSON - {e}")

    @pytest.mark.skip(
        reason="Built-in schedule JSON files are Schema 2.0 format - will be updated to Schema 3.0 in Issues #317-319"
    )
    def test_all_220_schedules_pass_validation(
        self, schedule_220_data: dict[str, dict]
    ) -> None:
        """All #220 schedules must pass validate_schedule()."""
        for schedule_id, data in schedule_220_data.items():
            schedule = Schedule.from_dict(data)
            valid, error = validate_schedule(schedule)
            assert valid, f"{schedule_id} failed validation: {error}"


# =============================================================================
# TEST: NIGHTLY_HOURLY.JSON (Interval Trigger, Fixed Time)
# =============================================================================


class TestNightlyHourlySchedule:
    """Tests for nightly_hourly.json schedule (Issue #220 acceptance criterion 1)."""

    def test_schedule_id_is_correct(self, nightly_hourly_schedule: dict) -> None:
        """Schedule ID must be a valid UUID."""
        schedule_id = nightly_hourly_schedule["schedule_id"]
        try:
            uuid.UUID(schedule_id)
        except ValueError:
            pytest.fail(f"schedule_id '{schedule_id}' is not a valid UUID")

    def test_has_interval_trigger(self, nightly_hourly_schedule: dict) -> None:
        """Must use interval trigger type."""
        assert nightly_hourly_schedule["trigger_type"] == "interval"

    def test_interval_is_60_minutes(self, nightly_hourly_schedule: dict) -> None:
        """Interval must be exactly 60 minutes."""
        trigger = nightly_hourly_schedule["interval_trigger"]
        assert trigger["interval_minutes"] == 60

    def test_time_window_is_fixed_01_to_06(
        self, nightly_hourly_schedule: dict
    ) -> None:
        """Time window must be fixed 01:00-06:00, NOT solar-based."""
        window = nightly_hourly_schedule["interval_trigger"]["time_window"]
        assert window["start_time"] == "01:00", "Start time must be 01:00"
        assert window["end_time"] == "06:00", "End time must be 06:00"

    def test_time_window_is_not_solar(self, nightly_hourly_schedule: dict) -> None:
        """Time window must use fixed times, not solar events."""
        window = nightly_hourly_schedule["interval_trigger"]["time_window"]
        # Verify NOT solar events
        assert window["start_time"] not in SOLAR_EVENTS, (
            f"start_time '{window['start_time']}' should not be a solar event"
        )
        assert window["end_time"] not in SOLAR_EVENTS, (
            f"end_time '{window['end_time']}' should not be a solar event"
        )

    def test_has_uv_capture_pattern(self, nightly_hourly_schedule: dict) -> None:
        """Must have at least one event pattern for UV capture."""
        patterns = nightly_hourly_schedule["event_patterns"]
        assert len(patterns) >= 1, "Must have at least one event pattern"

        # Verify pattern has attract_on, takephoto, attract_off sequence
        pattern = patterns[0]
        action_names = [a["action_name"] for a in pattern["actions"]]
        assert "attract_on" in action_names, "Pattern must turn on UV lights"
        assert "takephoto" in action_names, "Pattern must take a photo"
        assert "attract_off" in action_names, "Pattern must turn off UV lights"

    def test_pattern_has_tags(self, nightly_hourly_schedule: dict) -> None:
        """Pattern should have relevant tags."""
        patterns = nightly_hourly_schedule["event_patterns"]
        for pattern in patterns:
            tags = pattern.get("tags", [])
            assert len(tags) >= 1, f"Pattern '{pattern['name']}' has no tags"


# =============================================================================
# TEST: FULL_MOON_SURVEY.JSON (Moon Phase Trigger, Solar Window)
# =============================================================================


class TestFullMoonSurveySchedule:
    """Tests for full_moon_survey.json schedule (Issue #220 acceptance criterion 2)."""

    def test_schedule_id_is_correct(self, full_moon_survey_schedule: dict) -> None:
        """Schedule ID must be a valid UUID."""
        schedule_id = full_moon_survey_schedule["schedule_id"]
        try:
            uuid.UUID(schedule_id)
        except ValueError:
            pytest.fail(f"schedule_id '{schedule_id}' is not a valid UUID")

    def test_has_moon_phase_trigger(self, full_moon_survey_schedule: dict) -> None:
        """Must use moon_phase trigger type."""
        assert full_moon_survey_schedule["trigger_type"] == "moon_phase"

    def test_phase_includes_full(self, full_moon_survey_schedule: dict) -> None:
        """Must trigger on full moon phase."""
        trigger = full_moon_survey_schedule["moon_phase_trigger"]
        assert "full" in trigger["phases"], "Must include 'full' in phases"

    def test_offset_is_2_days(self, full_moon_survey_schedule: dict) -> None:
        """Offset must be +/-2 days from full moon."""
        trigger = full_moon_survey_schedule["moon_phase_trigger"]
        assert trigger["offset_days"] == 2, "offset_days must be 2"

    def test_time_window_is_solar_based(
        self, full_moon_survey_schedule: dict
    ) -> None:
        """Time window must be solar-based (dusk-dawn or civil_dusk-civil_dawn)."""
        trigger = full_moon_survey_schedule["moon_phase_trigger"]
        window = trigger["time_window"]

        # Verify solar events used (dusk/dawn or civil variants)
        valid_starts = ["dusk", "civil_dusk", "sunset"]
        valid_ends = ["dawn", "civil_dawn", "sunrise"]

        assert window["start_time"] in valid_starts, (
            f"start_time '{window['start_time']}' must be solar (dusk/civil_dusk/sunset)"
        )
        assert window["end_time"] in valid_ends, (
            f"end_time '{window['end_time']}' must be solar (dawn/civil_dawn/sunrise)"
        )

    def test_has_uv_capture_pattern(self, full_moon_survey_schedule: dict) -> None:
        """Must have at least one event pattern for UV capture."""
        patterns = full_moon_survey_schedule["event_patterns"]
        assert len(patterns) >= 1, "Must have at least one event pattern"

        pattern = patterns[0]
        action_names = [a["action_name"] for a in pattern["actions"]]
        assert "attract_on" in action_names, "Pattern must turn on UV lights"
        assert "takephoto" in action_names, "Pattern must take a photo"
        assert "attract_off" in action_names, "Pattern must turn off UV lights"


# =============================================================================
# TEST: DAWN_TRANSECT.JSON (Solar Trigger at sunrise-15min)
# =============================================================================


class TestDawnTransectSchedule:
    """Tests for dawn_transect.json schedule (Issue #220 acceptance criterion 3a)."""

    def test_schedule_id_is_correct(self, dawn_transect_schedule: dict) -> None:
        """Schedule ID must be a valid UUID."""
        schedule_id = dawn_transect_schedule["schedule_id"]
        try:
            uuid.UUID(schedule_id)
        except ValueError:
            pytest.fail(f"schedule_id '{schedule_id}' is not a valid UUID")

    def test_uses_solar_trigger(self, dawn_transect_schedule: dict) -> None:
        """Must use solar trigger type."""
        assert dawn_transect_schedule["trigger_type"] == "solar"

    def test_solar_event_is_sunrise(self, dawn_transect_schedule: dict) -> None:
        """Solar trigger must use sunrise event."""
        trigger = dawn_transect_schedule["solar_trigger"]
        assert trigger["solar_event"] == "sunrise", (
            f"Dawn transect must trigger at sunrise, got '{trigger['solar_event']}'"
        )

    def test_solar_trigger_has_negative_offset(
        self, dawn_transect_schedule: dict
    ) -> None:
        """Solar trigger should have negative offset (before sunrise)."""
        trigger = dawn_transect_schedule["solar_trigger"]
        assert "offset_minutes" in trigger, "solar_trigger must have offset_minutes"
        assert trigger["offset_minutes"] < 0, (
            f"Dawn offset should be negative (before sunrise), got {trigger['offset_minutes']}"
        )

    def test_has_dawn_pattern(self, dawn_transect_schedule: dict) -> None:
        """Must have a dawn transect pattern."""
        patterns = dawn_transect_schedule["event_patterns"]
        pattern_names = [p["name"].lower() for p in patterns]
        has_dawn = any("dawn" in name for name in pattern_names)
        assert has_dawn, f"Missing dawn pattern. Found: {pattern_names}"

    def test_pattern_has_photo_sequence(self, dawn_transect_schedule: dict) -> None:
        """Pattern should have multiple photos for transect."""
        patterns = dawn_transect_schedule["event_patterns"]
        for pattern in patterns:
            photo_count = sum(
                1 for a in pattern["actions"] if a["action_name"] == "takephoto"
            )
            assert photo_count >= 2, (
                f"Pattern '{pattern['name']}' should have multiple photos for transect, "
                f"found {photo_count}"
            )

    def test_pattern_has_uv_lights(self, dawn_transect_schedule: dict) -> None:
        """Pattern should turn UV lights on and off."""
        patterns = dawn_transect_schedule["event_patterns"]
        for pattern in patterns:
            action_names = [a["action_name"] for a in pattern["actions"]]
            assert "attract_on" in action_names, "Pattern must turn on UV lights"
            assert "attract_off" in action_names, "Pattern must turn off UV lights"


# =============================================================================
# TEST: DUSK_TRANSECT.JSON (Solar Trigger at sunset-15min)
# =============================================================================


class TestDuskTransectSchedule:
    """Tests for dusk_transect.json schedule (Issue #220 acceptance criterion 3b)."""

    def test_schedule_id_is_correct(self, dusk_transect_schedule: dict) -> None:
        """Schedule ID must be a valid UUID."""
        schedule_id = dusk_transect_schedule["schedule_id"]
        try:
            uuid.UUID(schedule_id)
        except ValueError:
            pytest.fail(f"schedule_id '{schedule_id}' is not a valid UUID")

    def test_uses_solar_trigger(self, dusk_transect_schedule: dict) -> None:
        """Must use solar trigger type."""
        assert dusk_transect_schedule["trigger_type"] == "solar"

    def test_solar_event_is_sunset(self, dusk_transect_schedule: dict) -> None:
        """Solar trigger must use sunset event."""
        trigger = dusk_transect_schedule["solar_trigger"]
        assert trigger["solar_event"] == "sunset", (
            f"Dusk transect must trigger at sunset, got '{trigger['solar_event']}'"
        )

    def test_solar_trigger_has_negative_offset(
        self, dusk_transect_schedule: dict
    ) -> None:
        """Solar trigger should have negative offset (before sunset)."""
        trigger = dusk_transect_schedule["solar_trigger"]
        assert "offset_minutes" in trigger, "solar_trigger must have offset_minutes"
        assert trigger["offset_minutes"] < 0, (
            f"Dusk offset should be negative (before sunset), got {trigger['offset_minutes']}"
        )

    def test_has_dusk_pattern(self, dusk_transect_schedule: dict) -> None:
        """Must have a dusk transect pattern."""
        patterns = dusk_transect_schedule["event_patterns"]
        pattern_names = [p["name"].lower() for p in patterns]
        has_dusk = any("dusk" in name for name in pattern_names)
        assert has_dusk, f"Missing dusk pattern. Found: {pattern_names}"

    def test_pattern_has_photo_sequence(self, dusk_transect_schedule: dict) -> None:
        """Pattern should have multiple photos for transect."""
        patterns = dusk_transect_schedule["event_patterns"]
        for pattern in patterns:
            photo_count = sum(
                1 for a in pattern["actions"] if a["action_name"] == "takephoto"
            )
            assert photo_count >= 2, (
                f"Pattern '{pattern['name']}' should have multiple photos for transect, "
                f"found {photo_count}"
            )

    def test_pattern_has_uv_lights(self, dusk_transect_schedule: dict) -> None:
        """Pattern should turn UV lights on and off."""
        patterns = dusk_transect_schedule["event_patterns"]
        for pattern in patterns:
            action_names = [a["action_name"] for a in pattern["actions"]]
            assert "attract_on" in action_names, "Pattern must turn on UV lights"
            assert "attract_off" in action_names, "Pattern must turn off UV lights"


# =============================================================================
# TEST: CONTINUOUS_MONITORING.JSON (Interval Trigger, Solar Window)
# =============================================================================


class TestContinuousMonitoringSchedule:
    """Tests for continuous_monitoring.json schedule (Issue #220 acceptance criterion 4)."""

    def test_schedule_id_is_correct(
        self, continuous_monitoring_schedule: dict
    ) -> None:
        """Schedule ID must be a valid UUID."""
        schedule_id = continuous_monitoring_schedule["schedule_id"]
        try:
            uuid.UUID(schedule_id)
        except ValueError:
            pytest.fail(f"schedule_id '{schedule_id}' is not a valid UUID")

    def test_has_interval_trigger(
        self, continuous_monitoring_schedule: dict
    ) -> None:
        """Must use interval trigger type."""
        assert continuous_monitoring_schedule["trigger_type"] == "interval"

    def test_interval_is_30_minutes(
        self, continuous_monitoring_schedule: dict
    ) -> None:
        """Interval must be exactly 30 minutes."""
        trigger = continuous_monitoring_schedule["interval_trigger"]
        assert trigger["interval_minutes"] == 30, "Interval must be 30 minutes"

    def test_time_window_is_sunset_to_sunrise(
        self, continuous_monitoring_schedule: dict
    ) -> None:
        """Time window must be solar-based (sunset to sunrise)."""
        window = continuous_monitoring_schedule["interval_trigger"]["time_window"]

        assert window["start_time"] == "sunset", "Start time must be 'sunset'"
        assert window["end_time"] == "sunrise", "End time must be 'sunrise'"

    def test_has_uv_capture_pattern(
        self, continuous_monitoring_schedule: dict
    ) -> None:
        """Must have at least one event pattern for UV capture."""
        patterns = continuous_monitoring_schedule["event_patterns"]
        assert len(patterns) >= 1, "Must have at least one event pattern"

        pattern = patterns[0]
        action_names = [a["action_name"] for a in pattern["actions"]]
        assert "attract_on" in action_names, "Pattern must turn on UV lights"
        assert "takephoto" in action_names, "Pattern must take a photo"
        assert "attract_off" in action_names, "Pattern must turn off UV lights"


# =============================================================================
# TEST: UNIQUE SCHEDULE IDS
# =============================================================================


class TestScheduleIdUniqueness:
    """Test that all schedule IDs are unique across #219 and #220."""

    def test_schedule_ids_unique_across_all(
        self, all_schedule_files: list[Path]
    ) -> None:
        """All schedule IDs (both #219 and #220) must be unique."""
        ids = [f.stem for f in all_schedule_files]
        seen = set()
        duplicates = []
        for schedule_id in ids:
            if schedule_id in seen:
                duplicates.append(schedule_id)
            seen.add(schedule_id)

        assert not duplicates, f"Duplicate schedule IDs: {duplicates}"

# =============================================================================
# TEST: TRIGGER TYPE VALIDATION
# =============================================================================


class TestTriggerTypes:
    """Test that all #220 schedules use correct trigger types."""

    @pytest.mark.parametrize(
        "schedule_id,expected_trigger",
        [
            ("nightly_hourly", "interval"),
            ("full_moon_survey", "moon_phase"),
            ("dawn_transect", "solar"),
            ("dusk_transect", "solar"),
            ("continuous_monitoring", "interval"),
        ],
    )
    def test_schedule_has_correct_trigger_type(
        self,
        schedule_220_data: dict[str, dict],
        schedule_id: str,
        expected_trigger: str,
    ) -> None:
        """Each #220 schedule must use the correct trigger type."""
        if schedule_id not in schedule_220_data:
            pytest.skip(f"{schedule_id}.json not found")

        schedule = schedule_220_data[schedule_id]
        actual_trigger = schedule.get("trigger_type")

        assert actual_trigger == expected_trigger, (
            f"{schedule_id}: expected trigger_type '{expected_trigger}', "
            f"got '{actual_trigger}'"
        )

    def test_all_trigger_types_are_valid(
        self, schedule_220_data: dict[str, dict]
    ) -> None:
        """All trigger types must be in TRIGGER_TYPES constant."""
        for schedule_id, data in schedule_220_data.items():
            trigger_type = data.get("trigger_type")
            assert trigger_type in TRIGGER_TYPES, (
                f"{schedule_id}: invalid trigger_type '{trigger_type}'. "
                f"Valid types: {TRIGGER_TYPES}"
            )


# =============================================================================
# TEST: SCHEMA VERSION
# =============================================================================


class TestSchemaVersion:
    """Test that all #220 schedules use correct schema version."""

    def test_all_220_schedules_use_schema_v2(
        self, schedule_220_data: dict[str, dict]
    ) -> None:
        """All #220 schedules must use schema_version '2.0'."""
        for schedule_id, data in schedule_220_data.items():
            version = data.get("schema_version")
            assert version == "2.0", (
                f"{schedule_id}: expected schema_version '2.0', got '{version}'"
            )


# =============================================================================
# TEST: DAYTIME-POLLINATOR.JSON (Schema 3.0, Issue #318)
# =============================================================================


class TestDaytimePollinatorSchedule:
    """Tests for daytime-pollinator.json schedule (Issue #318)."""

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

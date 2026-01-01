"""
Unit tests for built-in event patterns (Issue #219).

Tests that all required built-in event patterns:
1. Parse as valid JSON
2. Pass schema validation
3. Have unique pattern IDs
4. Use valid action types and names
5. Meet the Issue #219 acceptance criteria

The 5 required patterns are:
- UV Capture Cycle (15 min UV + photo)
- Attract Session (60 min with lights)
- Flash Capture (instant flash + photo)
- Dawn Transect
- Dusk Transect
"""

import json
from pathlib import Path

import pytest

from webui.backend.lib.cron_security import ACTION_TYPE_SCRIPTS
from webui.backend.lib.schedule_schema import (
    PATTERN_CATEGORIES,
    EventPattern,
    Action,
    Schedule,
    validate_event_pattern,
    validate_schedule,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def builtin_schedules_dir() -> Path:
    """Get the built-in schedules directory."""
    return (
        Path(__file__).parent.parent.parent / "webui" / "backend" / "presets_builtin" / "schedules"
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
def all_patterns(all_schedules: list[dict]) -> list[dict]:
    """Extract all event patterns from all schedules."""
    patterns = []
    for schedule in all_schedules:
        for pattern in schedule.get("event_patterns", []):
            # Add source schedule info for debugging
            pattern["_source_schedule"] = schedule.get("name", "unknown")
            patterns.append(pattern)
    return patterns


# =============================================================================
# TEST: JSON PARSING
# =============================================================================


class TestBuiltinSchedulesParsing:
    """Test that all built-in schedule files are valid JSON."""

    def test_schedules_directory_exists(self, builtin_schedules_dir: Path) -> None:
        """Verify the built-in schedules directory exists."""
        assert builtin_schedules_dir.exists(), f"Directory not found: {builtin_schedules_dir}"
        assert builtin_schedules_dir.is_dir(), f"Not a directory: {builtin_schedules_dir}"

    def test_schedule_files_exist(self, all_schedule_files: list[Path]) -> None:
        """Verify at least one schedule file exists."""
        assert len(all_schedule_files) > 0, "No schedule files found"

    def test_all_files_are_valid_json(self, all_schedule_files: list[Path]) -> None:
        """All schedule files must parse as valid JSON."""
        for file_path in all_schedule_files:
            try:
                with open(file_path) as f:
                    data = json.load(f)
                assert isinstance(data, dict), f"{file_path.name}: Root must be dict"
            except json.JSONDecodeError as e:
                pytest.fail(f"{file_path.name}: Invalid JSON - {e}")

    def test_all_schedules_have_event_patterns(self, all_schedules: list[dict]) -> None:
        """All schedules must have at least one event pattern."""
        for schedule in all_schedules:
            name = schedule.get("name", "unknown")
            patterns = schedule.get("event_patterns", [])
            assert len(patterns) > 0, f"Schedule '{name}' has no event_patterns"


# =============================================================================
# TEST: SCHEMA VALIDATION
# =============================================================================


class TestPatternSchemaValidation:
    """Test that all patterns pass schema validation."""

    def test_all_patterns_pass_validation(self, all_patterns: list[dict]) -> None:
        """All patterns must pass validate_event_pattern()."""
        for pattern_data in all_patterns:
            source = pattern_data.get("_source_schedule", "unknown")
            pattern_name = pattern_data.get("name", "unnamed")

            # Convert dict to EventPattern
            actions = [
                Action(**{k: v for k, v in a.items() if k != "_source_schedule"})
                for a in pattern_data.get("actions", [])
            ]
            pattern = EventPattern(
                pattern_id=pattern_data.get("pattern_id", ""),
                name=pattern_data.get("name", ""),
                description=pattern_data.get("description", ""),
                actions=actions,
                category=pattern_data.get("category", "user"),
                tags=pattern_data.get("tags", []),
            )

            valid, error = validate_event_pattern(pattern)
            assert valid, f"Pattern '{pattern_name}' from '{source}' failed: {error}"

    def test_all_schedules_pass_validation(self, all_schedules: list[dict]) -> None:
        """All schedules must pass validate_schedule()."""
        for schedule_data in all_schedules:
            schedule_name = schedule_data.get("name", "unnamed")

            schedule = Schedule.from_dict(schedule_data)
            valid, error = validate_schedule(schedule)
            assert valid, f"Schedule '{schedule_name}' failed validation: {error}"


# =============================================================================
# TEST: PATTERN UNIQUENESS
# =============================================================================


class TestPatternUniqueness:
    """Test that pattern IDs are unique across all schedules."""

    def test_pattern_ids_are_unique(self, all_patterns: list[dict]) -> None:
        """All pattern_ids must be unique."""
        pattern_ids = [p.get("pattern_id") for p in all_patterns]
        seen = set()
        duplicates = []
        for pid in pattern_ids:
            if pid in seen:
                duplicates.append(pid)
            seen.add(pid)

        assert not duplicates, f"Duplicate pattern IDs: {duplicates}"

    def test_pattern_names_are_descriptive(self, all_patterns: list[dict]) -> None:
        """All patterns must have non-empty names."""
        for pattern in all_patterns:
            name = pattern.get("name", "")
            assert name, f"Pattern {pattern.get('pattern_id')} has empty name"
            assert len(name) >= 3, f"Pattern name '{name}' is too short"


# =============================================================================
# TEST: ACTION VALIDATION
# =============================================================================


class TestActionValidation:
    """Test that all actions use valid types and names."""

    def test_all_action_types_are_valid(self, all_patterns: list[dict]) -> None:
        """All action_type values must be in ACTION_TYPE_SCRIPTS."""
        valid_types = set(ACTION_TYPE_SCRIPTS.keys())

        for pattern in all_patterns:
            pattern_name = pattern.get("name", "unnamed")
            for action in pattern.get("actions", []):
                action_type = action.get("action_type")
                assert action_type in valid_types, (
                    f"Pattern '{pattern_name}': invalid action_type '{action_type}'. "
                    f"Valid types: {valid_types}"
                )

    def test_all_action_names_are_valid(self, all_patterns: list[dict]) -> None:
        """All action_name values must be valid for their action_type."""
        for pattern in all_patterns:
            pattern_name = pattern.get("name", "unnamed")
            for action in pattern.get("actions", []):
                action_type = action.get("action_type")
                action_name = action.get("action_name")

                valid_names = ACTION_TYPE_SCRIPTS.get(action_type, {})
                assert action_name in valid_names, (
                    f"Pattern '{pattern_name}': invalid action_name '{action_name}' "
                    f"for type '{action_type}'. Valid names: {set(valid_names.keys())}"
                )

    def test_all_offsets_are_valid(self, all_patterns: list[dict]) -> None:
        """All offset_minutes must be 0-1440."""
        for pattern in all_patterns:
            pattern_name = pattern.get("name", "unnamed")
            for action in pattern.get("actions", []):
                offset = action.get("offset_minutes", 0)
                assert 0 <= offset <= 1440, (
                    f"Pattern '{pattern_name}': offset_minutes {offset} out of range [0, 1440]"
                )


# =============================================================================
# TEST: CATEGORY VALIDATION
# =============================================================================


class TestCategoryValidation:
    """Test that all built-in patterns have category 'built-in'."""

    def test_all_patterns_are_builtin_category(self, all_patterns: list[dict]) -> None:
        """All patterns must have category 'built-in'."""
        for pattern in all_patterns:
            pattern_name = pattern.get("name", "unnamed")
            category = pattern.get("category", "user")
            assert category == "built-in", (
                f"Pattern '{pattern_name}' has category '{category}', expected 'built-in'"
            )

    def test_category_is_valid(self, all_patterns: list[dict]) -> None:
        """All categories must be in PATTERN_CATEGORIES."""
        for pattern in all_patterns:
            category = pattern.get("category", "user")
            assert category in PATTERN_CATEGORIES, (
                f"Invalid category '{category}'. Valid: {PATTERN_CATEGORIES}"
            )


# =============================================================================
# TEST: REQUIRED PATTERNS (Issue #219)
# =============================================================================


class TestRequiredPatterns:
    """Test that all 5 required patterns exist (Issue #219 acceptance criteria)."""

    REQUIRED_PATTERNS = [
        "UV Capture Cycle",
        "Attract Session",
        "Flash Capture",
        "Dawn Transect",
        "Dusk Transect",
    ]

    def test_all_required_patterns_exist(self, all_patterns: list[dict]) -> None:
        """All 5 required patterns must exist by name."""
        pattern_names = {p.get("name") for p in all_patterns}

        missing = []
        for required in self.REQUIRED_PATTERNS:
            if required not in pattern_names:
                missing.append(required)

        assert not missing, f"Missing required patterns: {missing}"

    @pytest.mark.parametrize(
        "pattern_name,expected_actions,expected_tags,expected_duration",
        [
            ("UV Capture Cycle", ["attract_on", "takephoto", "attract_off"], None, None),
            ("Attract Session", None, None, 60),
            ("Flash Capture", ["flash_on", "takephoto", "flash_off"], None, None),
            ("Dawn Transect", None, ["dawn"], None),
            ("Dusk Transect", None, ["dusk"], None),
        ],
    )
    def test_required_pattern_configuration(
        self,
        all_patterns: list[dict],
        pattern_name: str,
        expected_actions: list[str] | None,
        expected_tags: list[str] | None,
        expected_duration: int | None,
    ) -> None:
        """Required patterns must exist with correct configuration."""
        pattern = next(
            (p for p in all_patterns if p.get("name") == pattern_name),
            None,
        )
        assert pattern is not None, f"{pattern_name} pattern not found"

        if expected_actions:
            action_names = [a.get("action_name") for a in pattern.get("actions", [])]
            for action in expected_actions:
                assert action in action_names, f"{pattern_name} missing {action}"

        if expected_tags:
            tags = pattern.get("tags", [])
            for tag in expected_tags:
                assert tag in tags, f"{pattern_name} missing '{tag}' tag"

        if expected_duration is not None:
            max_offset = max(a.get("offset_minutes", 0) for a in pattern.get("actions", []))
            assert max_offset == expected_duration, (
                f"{pattern_name} duration is {max_offset}, expected {expected_duration}"
            )


# =============================================================================
# TEST: PATTERN STRUCTURE
# =============================================================================


class TestPatternStructure:
    """Test pattern structural requirements."""

    def test_all_patterns_have_tags(self, all_patterns: list[dict]) -> None:
        """All patterns should have at least one tag for discoverability."""
        for pattern in all_patterns:
            pattern_name = pattern.get("name", "unnamed")
            tags = pattern.get("tags", [])
            assert len(tags) >= 1, f"Pattern '{pattern_name}' has no tags"

    def test_all_patterns_have_descriptions(self, all_patterns: list[dict]) -> None:
        """All patterns should have non-empty descriptions."""
        for pattern in all_patterns:
            pattern_name = pattern.get("name", "unnamed")
            description = pattern.get("description", "")
            assert description, f"Pattern '{pattern_name}' has no description"
            assert len(description) >= 20, (
                f"Pattern '{pattern_name}' description too short: '{description[:30]}...'"
            )

    def test_all_actions_have_descriptions(self, all_patterns: list[dict]) -> None:
        """All actions should have descriptions for clarity."""
        for pattern in all_patterns:
            pattern_name = pattern.get("name", "unnamed")
            for i, action in enumerate(pattern.get("actions", [])):
                description = action.get("description", "")
                assert description, f"Pattern '{pattern_name}' action {i + 1} has no description"

    def test_gpio_patterns_turn_off_lights(self, all_patterns: list[dict]) -> None:
        """Patterns that turn on lights should also turn them off."""
        for pattern in all_patterns:
            pattern_name = pattern.get("name", "unnamed")
            action_names = [a.get("action_name") for a in pattern.get("actions", [])]

            if "attract_on" in action_names:
                assert "attract_off" in action_names, (
                    f"Pattern '{pattern_name}' has attract_on but no attract_off"
                )

            if "flash_on" in action_names:
                assert "flash_off" in action_names, (
                    f"Pattern '{pattern_name}' has flash_on but no flash_off"
                )

    def test_actions_are_in_offset_order(self, all_patterns: list[dict]) -> None:
        """Actions should be ordered by offset_minutes for clarity."""
        for pattern in all_patterns:
            pattern_name = pattern.get("name", "unnamed")
            offsets = [a.get("offset_minutes", 0) for a in pattern.get("actions", [])]
            sorted_offsets = sorted(offsets)

            assert offsets == sorted_offsets, (
                f"Pattern '{pattern_name}' actions not in offset order: {offsets}"
            )

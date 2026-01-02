"""
Unit tests for validating JSON examples in scheduler API documentation.

Parses JSON code blocks from webui/docs/dev/api/scheduler.md and validates
them against the schedule_schema.py dataclasses and validators.

This ensures documentation examples stay in sync with the schema.

Issue #235 - Scheduler Documentation Validation Tests
"""

import json
import re
from pathlib import Path

import pytest

# Check if implementation exists for graceful skipping during TDD
try:
    from webui.backend.lib.schedule_schema import (
        # Dataclasses
        CronTrigger,
        FixedTimeTrigger,
        IntervalTrigger,
        MoonPhaseTrigger,
        Action,
        Routine,
        Schedule,
        SensorTrigger,
        SolarTrigger,
        TimeWindow,
        # Validation functions
        validate_cron_trigger,
        validate_fixed_time_trigger,
        validate_interval_trigger,
        validate_moon_phase_trigger,
        validate_action,
        validate_routine,
        validate_schedule,
        validate_sensor_trigger,
        validate_solar_trigger,
        validate_time_window,
    )

    IMPLEMENTATION_EXISTS = True
except ImportError:
    IMPLEMENTATION_EXISTS = False


# Skip all tests until documentation is updated to Schema 3.0
# Issue #300 updated the schema to use routines instead of event_patterns,
# but the documentation examples in scheduler.md still use Schema 2.0.
# These tests will be unskipped when docs are updated in Phase 5.
pytestmark = [
    pytest.mark.skipif(
        not IMPLEMENTATION_EXISTS,
        reason="schedule_schema.py not yet implemented",
    ),
    pytest.mark.skip(
        reason="Documentation examples need update to Schema 3.0 (Issue #300 - routines instead of event_patterns)"
    ),
]


# =============================================================================
# CONSTANTS
# =============================================================================

# Path to the scheduler API documentation
SCHEDULER_DOC_PATH = Path(__file__).parent.parent.parent / "webui" / "docs" / "dev" / "api" / "scheduler.md"

# Patterns that indicate a JSON block should be skipped
SKIP_PATTERNS = [
    r'\.\.\.',           # Ellipsis placeholder
    r'\[\.\.\.\]',       # Array ellipsis
    r'\{\.\.\.\}',       # Object ellipsis
    r'"UUID string"',    # Type placeholder
    r'\[EventPattern\]', # Type placeholder
    r'\[Action\]',# Type placeholder
    r'TimeWindow \| null',# Type placeholder
    r': number',         # Type placeholder (not in quotes)
    r': boolean',        # Type placeholder
    r': string',         # Type placeholder (bare)
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def extract_json_blocks(markdown_path: Path) -> list[tuple[int, str, dict | None]]:
    """
    Extract JSON code blocks from a markdown file.

    Args:
        markdown_path: Path to the markdown file

    Returns:
        List of (line_number, raw_json_string, parsed_dict_or_None) tuples.
        parsed_dict is None if JSON is invalid or contains skip patterns.
    """
    if not markdown_path.exists():
        return []

    content = markdown_path.read_text(encoding="utf-8")
    lines = content.split("\n")

    results = []
    in_json_block = False
    block_start_line = 0
    current_block = []

    for i, line in enumerate(lines, start=1):
        if line.strip().startswith("```json"):
            in_json_block = True
            block_start_line = i
            current_block = []
        elif line.strip() == "```" and in_json_block:
            in_json_block = False
            raw_json = "\n".join(current_block)

            # Check for skip patterns
            should_skip = False
            for pattern in SKIP_PATTERNS:
                if re.search(pattern, raw_json):
                    should_skip = True
                    break

            if should_skip:
                results.append((block_start_line, raw_json, None))
            else:
                # Try to parse JSON
                try:
                    parsed = json.loads(raw_json)
                    results.append((block_start_line, raw_json, parsed))
                except json.JSONDecodeError:
                    results.append((block_start_line, raw_json, None))
        elif in_json_block:
            current_block.append(line)

    return results


def identify_schema_type(json_obj: dict) -> str | None:
    """
    Identify which schema type a JSON object represents.

    Args:
        json_obj: Parsed JSON dictionary

    Returns:
        Schema type name or None if not a validatable schema object
    """
    if not isinstance(json_obj, dict):
        return None

    keys = set(json_obj.keys())

    # Error responses - skip
    if keys == {"error"}:
        return None

    # API response wrappers - skip the wrapper itself
    if "schedules" in keys and "total" in keys:
        return None
    if "patterns" in keys and "warnings" in keys:
        return None
    if "message" in keys and "schedule_id" in keys and "schedule" not in keys:
        return None  # Simple success message

    # Validation results - skip
    if "valid" in keys and ("conflicts" in keys or "pattern" in keys):
        return None

    # Preview results - skip
    if "executions" in keys and "preview_start" in keys:
        return None

    # Cron validation results - skip
    if "valid" in keys and "next_executions" in keys:
        return None
    if "valid" in keys and "expression" in keys:
        return None

    # Active schedule wrapper - skip
    if "active" in keys and "schedule" in keys:
        return None

    # Legacy cron job objects - skip
    if "command" in keys and "schedule" in keys and "enabled" in keys:
        return None
    if "cron_active" in keys:
        return None
    if "success" in keys and "command" in keys:
        return None
    if "jobs" in keys:
        return None

    # Schedule - most specific first
    # Can have schedule_id (responses) or not (create requests)
    if "trigger_type" in keys and "event_patterns" in keys:
        return "Schedule"

    # EventPattern - can have pattern_id (responses) or not (request bodies)
    # Must have actions array with Action-like objects
    if "actions" in keys and isinstance(json_obj.get("actions"), list):
        actions = json_obj["actions"]
        if len(actions) > 0:
            first_action = actions[0]
            # Has actions with action_type - it's an EventPattern
            # But exclude Schedule objects (which also have event_patterns)
            if (
                isinstance(first_action, dict)
                and "action_type" in first_action
                and "trigger_type" not in keys
            ):
                return "EventPattern"

    # Action
    if "action_type" in keys and "action_name" in keys:
        return "Action"

    # Triggers
    if "interval_minutes" in keys:
        return "IntervalTrigger"
    if "solar_event" in keys:
        return "SolarTrigger"
    if "phases" in keys and isinstance(json_obj.get("phases"), list):
        return "MoonPhaseTrigger"
    if "sensor_type" in keys and "threshold" in keys:
        return "SensorTrigger"
    if "cron_expression" in keys and len(keys) == 1:
        return "CronTrigger"

    # FixedTimeTrigger - has "time" but not action_type
    if "time" in keys and "action_type" not in keys and "action_name" not in keys:
        # Must look like HH:MM format
        time_val = json_obj.get("time", "")
        if isinstance(time_val, str) and re.match(r"^\d{2}:\d{2}$", time_val):
            return "FixedTimeTrigger"

    # TimeWindow
    if "start_time" in keys and "end_time" in keys:
        return "TimeWindow"

    return None


def validate_json_example(json_obj: dict, schema_type: str) -> tuple[bool, str | None]:
    """
    Validate a JSON object against its schema type.

    Args:
        json_obj: Parsed JSON dictionary
        schema_type: Schema type name from identify_schema_type()

    Returns:
        (True, None) if valid, (False, error_message) if invalid
    """
    try:
        if schema_type == "Schedule":
            schedule = Schedule.from_dict(json_obj)
            return validate_schedule(schedule)

        elif schema_type == "EventPattern":
            pattern = EventPattern.from_dict(json_obj)
            return validate_event_pattern(pattern)

        elif schema_type == "Action":
            action = Action.from_dict(json_obj)
            return validate_action(action)

        elif schema_type == "IntervalTrigger":
            trigger = IntervalTrigger.from_dict(json_obj)
            return validate_interval_trigger(trigger)

        elif schema_type == "SolarTrigger":
            trigger = SolarTrigger.from_dict(json_obj)
            return validate_solar_trigger(trigger)

        elif schema_type == "MoonPhaseTrigger":
            trigger = MoonPhaseTrigger.from_dict(json_obj)
            return validate_moon_phase_trigger(trigger)

        elif schema_type == "FixedTimeTrigger":
            trigger = FixedTimeTrigger.from_dict(json_obj)
            return validate_fixed_time_trigger(trigger)

        elif schema_type == "SensorTrigger":
            trigger = SensorTrigger.from_dict(json_obj)
            return validate_sensor_trigger(trigger)

        elif schema_type == "CronTrigger":
            trigger = CronTrigger.from_dict(json_obj)
            return validate_cron_trigger(trigger)

        elif schema_type == "TimeWindow":
            window = TimeWindow.from_dict(json_obj)
            return validate_time_window(window)

        else:
            return False, f"Unknown schema type: {schema_type}"

    except Exception as e:
        return False, f"Deserialization failed: {str(e)}"


def extract_nested_objects(json_obj: dict, line_num: int) -> list[tuple[int, dict, str]]:
    """
    Extract nested validatable objects from API response wrappers.

    For example, {"patterns": [...], "warnings": []} contains EventPattern objects.

    Args:
        json_obj: The wrapper object
        line_num: Line number of the wrapper

    Returns:
        List of (line_number, nested_obj, schema_type) tuples
    """
    results = []

    # Extract patterns from {"patterns": [...], "warnings": []}
    if "patterns" in json_obj and isinstance(json_obj["patterns"], list):
        for pattern in json_obj["patterns"]:
            if isinstance(pattern, dict):
                schema_type = identify_schema_type(pattern)
                if schema_type:
                    results.append((line_num, pattern, schema_type))

    # Extract schedules from {"schedules": [...], "total": N}
    if "schedules" in json_obj and isinstance(json_obj["schedules"], list):
        for schedule in json_obj["schedules"]:
            if isinstance(schedule, dict):
                schema_type = identify_schema_type(schedule)
                if schema_type:
                    results.append((line_num, schedule, schema_type))

    # Extract schedule from {"message": "...", "schedule": {...}}
    if "schedule" in json_obj and isinstance(json_obj["schedule"], dict):
        schedule = json_obj["schedule"]
        schema_type = identify_schema_type(schedule)
        if schema_type:
            results.append((line_num, schedule, schema_type))

    return results


def get_validatable_examples() -> list[tuple[int, dict, str]]:
    """
    Get all validatable JSON examples from the scheduler documentation.

    Returns:
        List of (line_number, json_obj, schema_type) tuples
    """
    blocks = extract_json_blocks(SCHEDULER_DOC_PATH)

    validatable = []
    for line_num, _raw_json, parsed in blocks:
        if parsed is None:
            continue

        schema_type = identify_schema_type(parsed)
        if schema_type is not None:
            validatable.append((line_num, parsed, schema_type))
        else:
            # Try to extract nested objects from wrappers
            nested = extract_nested_objects(parsed, line_num)
            validatable.extend(nested)

    return validatable


# =============================================================================
# TEST CLASSES
# =============================================================================


class TestDocExampleExtraction:
    """Tests for JSON extraction from markdown documentation."""

    def test_scheduler_doc_exists(self):
        """Scheduler API documentation file should exist."""
        assert SCHEDULER_DOC_PATH.exists(), f"Doc file not found: {SCHEDULER_DOC_PATH}"

    def test_extract_json_blocks_finds_blocks(self):
        """extract_json_blocks should find JSON code blocks."""
        blocks = extract_json_blocks(SCHEDULER_DOC_PATH)
        assert len(blocks) > 0, "No JSON blocks found in documentation"

    def test_extract_json_blocks_returns_line_numbers(self):
        """Each extracted block should have a line number."""
        blocks = extract_json_blocks(SCHEDULER_DOC_PATH)
        for line_num, _raw_json, _parsed in blocks:
            assert isinstance(line_num, int)
            assert line_num > 0

    def test_some_blocks_are_parseable(self):
        """At least some JSON blocks should be valid JSON."""
        blocks = extract_json_blocks(SCHEDULER_DOC_PATH)
        parsed_count = sum(1 for _, _, parsed in blocks if parsed is not None)
        assert parsed_count > 0, "No valid JSON blocks found"

    def test_skip_patterns_filter_type_placeholders(self):
        """Blocks with type placeholders should have parsed=None."""
        blocks = extract_json_blocks(SCHEDULER_DOC_PATH)

        # Find blocks that contain "UUID string" or similar
        for line_num, raw_json, parsed in blocks:
            if '"UUID string"' in raw_json:
                assert parsed is None, f"Line {line_num}: Should skip type placeholder blocks"


class TestSchemaTypeDetection:
    """Tests for identify_schema_type function."""

    def test_detect_schedule(self):
        """Should detect Schedule objects."""
        obj = {
            "schedule_id": "123",
            "trigger_type": "interval",
            "event_patterns": [],
            "name": "Test"
        }
        assert identify_schema_type(obj) == "Schedule"

    def test_detect_event_pattern(self):
        """Should detect EventPattern objects."""
        obj = {
            "pattern_id": "456",
            "name": "Test Pattern",
            "actions": [{"action_type": "gpio", "action_name": "attract_on"}]
        }
        assert identify_schema_type(obj) == "EventPattern"

    def test_detect_pattern_action(self):
        """Should detect Action objects."""
        obj = {
            "action_type": "gpio",
            "action_name": "attract_on",
            "offset_minutes": 0
        }
        assert identify_schema_type(obj) == "Action"

    def test_detect_interval_trigger(self):
        """Should detect IntervalTrigger objects."""
        obj = {
            "interval_minutes": 60,
            "time_window": {"start_time": "sunset", "end_time": "sunrise"}
        }
        assert identify_schema_type(obj) == "IntervalTrigger"

    def test_detect_solar_trigger(self):
        """Should detect SolarTrigger objects."""
        obj = {
            "solar_event": "sunset",
            "offset_minutes": 30
        }
        assert identify_schema_type(obj) == "SolarTrigger"

    def test_detect_moon_phase_trigger(self):
        """Should detect MoonPhaseTrigger objects."""
        obj = {
            "phases": ["new", "full"],
            "offset_days": 0
        }
        assert identify_schema_type(obj) == "MoonPhaseTrigger"

    def test_detect_fixed_time_trigger(self):
        """Should detect FixedTimeTrigger objects."""
        obj = {
            "time": "21:00",
            "days_of_week": [0, 1, 2, 3, 4]
        }
        assert identify_schema_type(obj) == "FixedTimeTrigger"

    def test_detect_sensor_trigger(self):
        """Should detect SensorTrigger objects."""
        obj = {
            "sensor_type": "motion",
            "threshold": 50,
            "comparison": "gt"
        }
        assert identify_schema_type(obj) == "SensorTrigger"

    def test_detect_cron_trigger(self):
        """Should detect CronTrigger objects."""
        obj = {"cron_expression": "0 * * * *"}
        assert identify_schema_type(obj) == "CronTrigger"

    def test_detect_time_window(self):
        """Should detect TimeWindow objects."""
        obj = {
            "start_time": "sunset",
            "end_time": "sunrise",
            "start_offset_minutes": 30,
            "end_offset_minutes": -30
        }
        assert identify_schema_type(obj) == "TimeWindow"

    def test_skip_error_response(self):
        """Should return None for error responses."""
        obj = {"error": "Schedule not found"}
        assert identify_schema_type(obj) is None

    def test_skip_api_wrapper(self):
        """Should return None for API response wrappers."""
        obj = {"schedules": [], "total": 0}
        assert identify_schema_type(obj) is None


class TestDocExampleValidation:
    """Tests that validate documentation examples against schemas."""

    def test_get_validatable_examples_returns_list(self):
        """get_validatable_examples should return a list."""
        examples = get_validatable_examples()
        assert isinstance(examples, list)

    def test_at_least_some_examples_found(self):
        """Should find at least some validatable examples."""
        examples = get_validatable_examples()
        assert len(examples) > 0, "No validatable examples found in documentation"

    def test_examples_have_required_fields(self):
        """Each example tuple should have line, json, and type."""
        examples = get_validatable_examples()
        for line_num, json_obj, schema_type in examples:
            assert isinstance(line_num, int)
            assert isinstance(json_obj, dict)
            assert isinstance(schema_type, str)


class TestAllDocExamples:
    """Parametrized tests for all documentation examples."""

    @pytest.fixture
    def all_examples(self):
        """Get all validatable examples."""
        return get_validatable_examples()

    def test_all_examples_validate(self, all_examples):
        """All documentation examples should pass schema validation."""
        failures = []

        for line_num, json_obj, schema_type in all_examples:
            valid, error = validate_json_example(json_obj, schema_type)
            if not valid:
                failures.append(f"Line {line_num} ({schema_type}): {error}")

        if failures:
            failure_report = "\n".join(failures)
            pytest.fail(f"Documentation examples failed validation:\n{failure_report}")

    def test_schedule_examples_validate(self, all_examples):
        """All Schedule examples should validate."""
        schedule_examples = [
            (ln, js, tp) for ln, js, tp in all_examples if tp == "Schedule"
        ]

        for line_num, json_obj, schema_type in schedule_examples:
            valid, error = validate_json_example(json_obj, schema_type)
            assert valid, f"Line {line_num}: Schedule validation failed: {error}"

    def test_event_pattern_examples_validate(self, all_examples):
        """All EventPattern examples should validate."""
        pattern_examples = [
            (ln, js, tp) for ln, js, tp in all_examples if tp == "EventPattern"
        ]

        for line_num, json_obj, schema_type in pattern_examples:
            valid, error = validate_json_example(json_obj, schema_type)
            assert valid, f"Line {line_num}: EventPattern validation failed: {error}"

    def test_trigger_examples_validate(self, all_examples):
        """All trigger examples should validate."""
        trigger_types = {"IntervalTrigger", "SolarTrigger", "MoonPhaseTrigger",
                         "FixedTimeTrigger", "SensorTrigger", "CronTrigger"}
        trigger_examples = [
            (ln, js, tp) for ln, js, tp in all_examples if tp in trigger_types
        ]

        for line_num, json_obj, schema_type in trigger_examples:
            valid, error = validate_json_example(json_obj, schema_type)
            assert valid, f"Line {line_num}: {schema_type} validation failed: {error}"

    def test_time_window_examples_validate(self, all_examples):
        """All TimeWindow examples should validate."""
        window_examples = [
            (ln, js, tp) for ln, js, tp in all_examples if tp == "TimeWindow"
        ]

        for line_num, json_obj, schema_type in window_examples:
            valid, error = validate_json_example(json_obj, schema_type)
            assert valid, f"Line {line_num}: TimeWindow validation failed: {error}"

    def test_pattern_action_examples_validate(self, all_examples):
        """All Action examples should validate."""
        action_examples = [
            (ln, js, tp) for ln, js, tp in all_examples if tp == "Action"
        ]

        for line_num, json_obj, schema_type in action_examples:
            valid, error = validate_json_example(json_obj, schema_type)
            assert valid, f"Line {line_num}: Action validation failed: {error}"


class TestValidationSummary:
    """Summary test that reports on documentation validation status."""

    def test_documentation_sync_report(self):
        """Generate a report of documentation example validation."""
        examples = get_validatable_examples()

        if not examples:
            pytest.skip("No validatable examples found")

        results_by_type: dict[str, list[tuple[int, bool, str | None]]] = {}

        for line_num, json_obj, schema_type in examples:
            valid, error = validate_json_example(json_obj, schema_type)

            if schema_type not in results_by_type:
                results_by_type[schema_type] = []
            results_by_type[schema_type].append((line_num, valid, error))

        # Build report
        total = len(examples)
        passed = sum(1 for _, _, t in examples
                     for line, valid, _ in results_by_type.get(t, [])
                     if valid)

        # Recalculate properly
        passed = 0
        failed = 0
        failures = []

        for schema_type, results in results_by_type.items():
            for line_num, valid, error in results:
                if valid:
                    passed += 1
                else:
                    failed += 1
                    failures.append(f"  Line {line_num} ({schema_type}): {error}")

        # Print summary (visible in pytest -v output)
        print("\n=== Documentation Validation Summary ===")
        print(f"Total examples: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")

        for schema_type, results in sorted(results_by_type.items()):
            type_passed = sum(1 for _, valid, _ in results if valid)
            type_total = len(results)
            print(f"  {schema_type}: {type_passed}/{type_total}")

        if failures:
            print("\nFailures:")
            for f in failures:
                print(f)

        assert failed == 0, f"{failed} documentation examples failed validation"

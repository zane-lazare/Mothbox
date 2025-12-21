"""
Unit tests for schedule storage library (Issue #209 - Subtask 1).

Tests schedule storage path utilities for CRUD operations on schedule JSON files.
These tests drive the implementation using TDD.

Coverage target: 85%+

Design Decisions:
- User schedules: CONFIG_DIR/schedules/{schedule_id}.json
- Built-in schedules: webui/backend/presets_builtin/schedules/{schedule_id}.json
- Precedence: User schedules override built-in schedules with same ID
- File locking: Atomic operations for concurrent safety
- Validation: Schema validation via schedule_schema.py
"""

import json

import pytest

# ============================================================================
# Expected Interface
# ============================================================================

try:
    from webui.backend.lib.schedule_storage import (
        BUILTIN_SCHEDULES_DIR,
        # Constants
        SCHEDULE_FILENAME_EXTENSION,
        SCHEDULES_DIR,
        cleanup_temp_files,
        # CRUD operations
        create_schedule,
        delete_schedule,
        find_schedule,
        # Built-in handling
        get_builtin_schedules,
        # Path utilities
        get_schedule_path,
        is_builtin_schedule,
        list_schedule_ids,
        # List operations
        list_schedules,
        read_schedule,
        schedule_exists,
        update_schedule,
    )
    IMPLEMENTATION_EXISTS = True
except ImportError:
    IMPLEMENTATION_EXISTS = False
    # Define stubs for test discovery
    get_schedule_path = None
    schedule_exists = None
    list_schedule_ids = None
    find_schedule = None
    create_schedule = None
    read_schedule = None
    update_schedule = None
    delete_schedule = None
    get_builtin_schedules = None
    is_builtin_schedule = None
    list_schedules = None
    cleanup_temp_files = None
    SCHEDULE_FILENAME_EXTENSION = None
    SCHEDULES_DIR = None
    BUILTIN_SCHEDULES_DIR = None

try:
    from webui.backend.lib.schedule_schema import ScheduleValidationError
except ImportError:
    ScheduleValidationError = None

# Skip all tests if implementation doesn't exist yet
pytestmark = pytest.mark.skipif(
    not IMPLEMENTATION_EXISTS,
    reason="schedule_storage.py not yet implemented"
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_schedules_dir(tmp_path, monkeypatch):
    """Create temp directory and mock SCHEDULES_DIR."""
    schedules_dir = tmp_path / "schedules"
    schedules_dir.mkdir()
    # Patch in both mothbox_paths (for get_schedule_path) and schedule_storage (for direct refs)
    monkeypatch.setattr('mothbox_paths.SCHEDULES_DIR', schedules_dir)
    monkeypatch.setattr('webui.backend.lib.schedule_storage.SCHEDULES_DIR', schedules_dir)
    return schedules_dir


@pytest.fixture
def temp_builtin_dir(tmp_path, monkeypatch):
    """Create temp directory and mock BUILTIN_SCHEDULES_DIR."""
    builtin_dir = tmp_path / "presets_builtin" / "schedules"
    builtin_dir.mkdir(parents=True)
    # Patch in both mothbox_paths (for get_schedule_path) and schedule_storage (for direct refs)
    monkeypatch.setattr('mothbox_paths.BUILTIN_SCHEDULES_DIR', builtin_dir)
    monkeypatch.setattr('webui.backend.lib.schedule_storage.BUILTIN_SCHEDULES_DIR', builtin_dir)
    return builtin_dir


@pytest.fixture
def sample_schedule_json():
    """Return valid schedule JSON string for testing."""
    return json.dumps({
        "schema_version": "2.0",
        "schedule_id": "test-schedule-123",
        "name": "Test Schedule",
        "description": "A test schedule",
        "event_patterns": [
            {
                "pattern_id": "pattern-1",
                "name": "Test Pattern",
                "description": "Test pattern description",
                "actions": [
                    {
                        "action_type": "gpio",
                        "action_name": "attract_on",
                        "offset_minutes": 0,
                        "parameters": {},
                        "description": "Turn on attract lights"
                    }
                ],
                "category": "user",
                "tags": []
            }
        ],
        "trigger_type": "interval",
        "interval_trigger": {
            "interval_minutes": 60,
            "time_window": {
                "start_time": "21:00",
                "end_time": "05:00",
                "start_offset_minutes": 0,
                "end_offset_minutes": 0
            },
            "days_of_week": None
        },
        "solar_trigger": None,
        "moon_phase_trigger": None,
        "fixed_time_trigger": None,
        "sensor_trigger": None,
        "start_date": None,
        "end_date": None,
        "deployment_id": None,
        "create_deployment": False,
        "enabled": True,
        "is_active": False,
        "created_at": "2024-01-01T12:00:00",
        "modified_at": "2024-01-01T12:00:00",
        "modified_by": None
    })


@pytest.fixture
def sample_schedule(sample_schedule_json):
    """Return valid Schedule object for testing."""
    try:
        from webui.backend.lib.schedule_schema import Schedule
        return Schedule.from_dict(json.loads(sample_schedule_json))
    except ImportError:
        return None


# ============================================================================
# Test Class: Path Utilities
# ============================================================================

class TestPathUtilities:
    """Tests for path resolution functions."""

    def test_get_schedule_path_user_returns_config_dir_path(self, temp_schedules_dir):
        """Verify user schedule path is CONFIG_DIR/schedules/{id}.json."""
        schedule_id = "test-schedule-123"

        path = get_schedule_path(schedule_id, is_builtin=False)

        assert path == temp_schedules_dir / f"{schedule_id}.json"
        assert path.parent == temp_schedules_dir

    def test_get_schedule_path_builtin_returns_presets_dir_path(self, temp_builtin_dir):
        """Verify built-in path is presets_builtin/schedules/{id}.json."""
        schedule_id = "nightly-survey"

        path = get_schedule_path(schedule_id, is_builtin=True)

        assert path == temp_builtin_dir / f"{schedule_id}.json"
        assert "presets_builtin" in str(path)
        assert "schedules" in str(path)

    def test_schedule_exists_true_when_file_exists(self, temp_schedules_dir, sample_schedule_json):
        """Check existence returns True for existing file."""
        schedule_id = "existing-schedule"
        schedule_file = temp_schedules_dir / f"{schedule_id}.json"
        schedule_file.write_text(sample_schedule_json)

        exists = schedule_exists(schedule_id, is_builtin=False)

        assert exists is True

    def test_schedule_exists_false_when_file_missing(self, temp_schedules_dir):
        """Check existence returns False for missing file."""
        schedule_id = "nonexistent-schedule"

        exists = schedule_exists(schedule_id, is_builtin=False)

        assert exists is False

    def test_list_schedule_ids_empty_directory(self, temp_schedules_dir):
        """List from empty directory returns empty list."""
        schedule_ids = list_schedule_ids(is_builtin=False)

        assert schedule_ids == []

    def test_list_schedule_ids_finds_json_files(self, temp_schedules_dir, sample_schedule_json):
        """List finds all .json files (excludes .bak, .lock)."""
        # Create valid schedule files
        (temp_schedules_dir / "schedule-1.json").write_text(sample_schedule_json)
        (temp_schedules_dir / "schedule-2.json").write_text(sample_schedule_json)
        (temp_schedules_dir / "schedule-3.json").write_text(sample_schedule_json)

        # Create files that should be excluded
        (temp_schedules_dir / "schedule-4.json.bak").write_text(sample_schedule_json)
        (temp_schedules_dir / "schedule-5.json.lock").write_text("")
        (temp_schedules_dir / "readme.txt").write_text("README")

        schedule_ids = list_schedule_ids(is_builtin=False)

        assert len(schedule_ids) == 3
        assert "schedule-1" in schedule_ids
        assert "schedule-2" in schedule_ids
        assert "schedule-3" in schedule_ids
        assert "schedule-4" not in schedule_ids  # .bak excluded
        assert "schedule-5" not in schedule_ids  # .lock excluded

    def test_find_schedule_user_takes_precedence(
        self,
        temp_schedules_dir,
        temp_builtin_dir,
        sample_schedule_json
    ):
        """When same ID exists in both, user takes precedence."""
        schedule_id = "duplicate-schedule"

        # Create built-in schedule
        builtin_file = temp_builtin_dir / f"{schedule_id}.json"
        builtin_file.write_text(sample_schedule_json)

        # Create user schedule with modified data
        user_schedule_data = json.loads(sample_schedule_json)
        user_schedule_data["name"] = "User Modified Schedule"
        user_file = temp_schedules_dir / f"{schedule_id}.json"
        user_file.write_text(json.dumps(user_schedule_data))

        # Find should return user path
        found_path, is_builtin = find_schedule(schedule_id)

        assert found_path == user_file
        assert is_builtin is False

    def test_find_schedule_returns_none_when_not_found(
        self,
        temp_schedules_dir,
        temp_builtin_dir
    ):
        """Returns None if not in user or built-in."""
        schedule_id = "nonexistent-schedule"

        result = find_schedule(schedule_id)

        assert result is None


# ============================================================================
# Test Class: CRUD Operations
# ============================================================================

class TestCRUDOperations:
    """Tests for create, read, update, delete operations."""

    def test_create_schedule_writes_json_file(self, temp_schedules_dir, sample_schedule):
        """Creating a schedule writes a JSON file."""
        result = create_schedule(sample_schedule)

        assert result is True

        # Verify file exists
        schedule_file = temp_schedules_dir / f"{sample_schedule.schedule_id}.json"
        assert schedule_file.exists()

        # Verify contents are valid JSON
        with open(schedule_file) as f:
            data = json.load(f)
        assert data["schedule_id"] == sample_schedule.schedule_id
        assert data["name"] == sample_schedule.name

    def test_create_schedule_validates_before_writing(self, temp_schedules_dir, sample_schedule):
        """Valid schedules are validated before write."""
        # Ensure the schedule is valid
        from webui.backend.lib.schedule_schema import validate_schedule
        valid, error = validate_schedule(sample_schedule)
        assert valid, f"Sample schedule should be valid: {error}"

        result = create_schedule(sample_schedule)

        assert result is True
        schedule_file = temp_schedules_dir / f"{sample_schedule.schedule_id}.json"
        assert schedule_file.exists()

    def test_create_schedule_raises_on_invalid_schedule(self, temp_schedules_dir):
        """Invalid schedules raise ScheduleValidationError."""
        from webui.backend.lib.schedule_schema import Schedule

        # Create invalid schedule (missing required trigger config)
        invalid_schedule = Schedule(
            schedule_id="invalid-schedule",
            name="Invalid Schedule",
            event_patterns=[],  # Empty patterns (invalid)
            trigger_type="interval",
            interval_trigger=None,  # Missing required trigger config
        )

        with pytest.raises(ScheduleValidationError):
            create_schedule(invalid_schedule)

    def test_create_schedule_creates_directory_if_missing(self, temp_schedules_dir, sample_schedule):
        """Auto-creates schedules directory if it doesn't exist."""
        # Remove the schedules directory
        import shutil
        shutil.rmtree(temp_schedules_dir)

        result = create_schedule(sample_schedule)

        assert result is True
        assert temp_schedules_dir.exists()
        schedule_file = temp_schedules_dir / f"{sample_schedule.schedule_id}.json"
        assert schedule_file.exists()

    def test_read_schedule_returns_schedule_object(self, temp_schedules_dir, sample_schedule):
        """Read returns deserialized Schedule object."""
        # First create a schedule
        create_schedule(sample_schedule)

        # Now read it back
        read_result = read_schedule(sample_schedule.schedule_id)

        assert read_result is not None
        from webui.backend.lib.schedule_schema import Schedule
        assert isinstance(read_result, Schedule)
        assert read_result.schedule_id == sample_schedule.schedule_id
        assert read_result.name == sample_schedule.name

    def test_read_schedule_returns_none_when_missing(self, temp_schedules_dir):
        """Read returns None for non-existent file."""
        schedule_id = "nonexistent-schedule"

        result = read_schedule(schedule_id)

        assert result is None

    def test_read_schedule_returns_none_on_corrupted_json(self, temp_schedules_dir):
        """Corrupted JSON returns None gracefully."""
        schedule_id = "corrupted-schedule"
        schedule_file = temp_schedules_dir / f"{schedule_id}.json"
        schedule_file.write_text("{ invalid json }")

        result = read_schedule(schedule_id)

        assert result is None

    def test_update_schedule_partial_fields(self, temp_schedules_dir, sample_schedule):
        """Update modifies only specified fields."""
        # First create a schedule
        create_schedule(sample_schedule)

        # Update only the name and description
        updates = {
            "name": "Updated Schedule Name",
            "description": "Updated description"
        }
        updated_schedule = update_schedule(sample_schedule.schedule_id, updates)

        assert updated_schedule is not None
        assert updated_schedule.name == "Updated Schedule Name"
        assert updated_schedule.description == "Updated description"
        # Original fields preserved
        assert updated_schedule.schedule_id == sample_schedule.schedule_id
        assert updated_schedule.enabled == sample_schedule.enabled

    def test_update_schedule_updates_modified_at(self, temp_schedules_dir, sample_schedule):
        """Update updates the modified_at timestamp."""
        import time
        from datetime import datetime

        # Create schedule with known timestamp
        create_schedule(sample_schedule)
        original_modified_at = sample_schedule.modified_at

        # Wait a bit to ensure timestamp difference
        time.sleep(0.1)

        # Update schedule
        updated_schedule = update_schedule(sample_schedule.schedule_id, {"name": "New Name"})

        assert updated_schedule is not None
        assert updated_schedule.modified_at != original_modified_at
        # Verify it's a valid ISO 8601 timestamp
        datetime.fromisoformat(updated_schedule.modified_at)

    def test_delete_schedule_removes_file(self, temp_schedules_dir, sample_schedule):
        """Delete removes the schedule file."""
        # First create a schedule
        create_schedule(sample_schedule)
        schedule_file = temp_schedules_dir / f"{sample_schedule.schedule_id}.json"
        assert schedule_file.exists()

        # Delete it
        result = delete_schedule(sample_schedule.schedule_id, backup=False)

        assert result is True
        assert not schedule_file.exists()

    def test_delete_schedule_creates_backup(self, temp_schedules_dir, sample_schedule):
        """Delete creates .bak before removing."""
        # First create a schedule
        create_schedule(sample_schedule)
        schedule_file = temp_schedules_dir / f"{sample_schedule.schedule_id}.json"
        original_content = schedule_file.read_text()

        # Delete with backup
        result = delete_schedule(sample_schedule.schedule_id, backup=True)

        assert result is True
        assert not schedule_file.exists()

        # Check backup exists
        backup_file = temp_schedules_dir / f"{sample_schedule.schedule_id}.json.bak"
        assert backup_file.exists()
        assert backup_file.read_text() == original_content

    def test_delete_schedule_returns_false_when_missing(self, temp_schedules_dir):
        """Delete returns False for non-existent file."""
        schedule_id = "nonexistent-schedule"

        result = delete_schedule(schedule_id)

        assert result is False


# ============================================================================
# Test Class: Built-in Schedules
# ============================================================================

class TestBuiltinSchedules:
    """Tests for built-in schedule handling and protection."""

    def test_get_builtin_schedules_returns_list(self, temp_builtin_dir, sample_schedule_json):
        """Get built-in schedules returns list of Schedule objects."""
        # Create some built-in schedules
        (temp_builtin_dir / "nightly-survey.json").write_text(sample_schedule_json)

        schedule_data = json.loads(sample_schedule_json)
        schedule_data["schedule_id"] = "hourly-capture"
        (temp_builtin_dir / "hourly-capture.json").write_text(json.dumps(schedule_data))

        builtin_schedules = get_builtin_schedules()

        assert isinstance(builtin_schedules, list)
        assert len(builtin_schedules) == 2

        from webui.backend.lib.schedule_schema import Schedule
        for schedule in builtin_schedules:
            assert isinstance(schedule, Schedule)

        # Check schedule IDs
        schedule_ids = [s.schedule_id for s in builtin_schedules]
        assert "nightly-survey" in schedule_ids
        assert "hourly-capture" in schedule_ids

    def test_delete_builtin_schedule_raises_error(self, temp_builtin_dir, sample_schedule_json):
        """Deleting a built-in schedule raises ValueError."""
        # Create a built-in schedule
        schedule_id = "nightly-survey"
        (temp_builtin_dir / f"{schedule_id}.json").write_text(sample_schedule_json)

        # Attempt to delete should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            delete_schedule(schedule_id, is_builtin=True)

        assert "built-in" in str(exc_info.value).lower()

        # Verify file still exists
        builtin_file = temp_builtin_dir / f"{schedule_id}.json"
        assert builtin_file.exists()

    def test_update_builtin_schedule_raises_error(self, temp_builtin_dir, sample_schedule_json):
        """Updating a built-in schedule raises ValueError."""
        # Create a built-in schedule
        schedule_id = "nightly-survey"
        (temp_builtin_dir / f"{schedule_id}.json").write_text(sample_schedule_json)

        # Attempt to update should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            update_schedule(schedule_id, {"name": "Modified Name"}, is_builtin=True)

        assert "built-in" in str(exc_info.value).lower()

    def test_is_builtin_schedule_correctly_identifies(
        self,
        temp_schedules_dir,
        temp_builtin_dir,
        sample_schedule_json
    ):
        """is_builtin_schedule() correctly identifies built-in vs user schedules."""
        # Create built-in schedule
        builtin_id = "nightly-survey"
        (temp_builtin_dir / f"{builtin_id}.json").write_text(sample_schedule_json)

        # Create user schedule
        user_schedule_data = json.loads(sample_schedule_json)
        user_schedule_data["schedule_id"] = "my-custom-schedule"
        user_id = "my-custom-schedule"
        (temp_schedules_dir / f"{user_id}.json").write_text(json.dumps(user_schedule_data))

        # Test identification
        assert is_builtin_schedule(builtin_id) is True
        assert is_builtin_schedule(user_id) is False
        assert is_builtin_schedule("nonexistent") is False


# ============================================================================
# Test Class: List Operations
# ============================================================================

class TestListOperations:
    """Tests for listing and combining schedules."""

    def test_list_schedules_combines_user_and_builtin(
        self,
        temp_schedules_dir,
        temp_builtin_dir,
        sample_schedule_json
    ):
        """list_schedules returns combined list with no duplicates."""
        # Create built-in schedules
        (temp_builtin_dir / "builtin-1.json").write_text(sample_schedule_json)

        schedule_data = json.loads(sample_schedule_json)
        schedule_data["schedule_id"] = "builtin-2"
        (temp_builtin_dir / "builtin-2.json").write_text(json.dumps(schedule_data))

        # Create user schedules
        schedule_data["schedule_id"] = "user-1"
        (temp_schedules_dir / "user-1.json").write_text(json.dumps(schedule_data))

        all_schedules = list_schedules(include_builtin=True)

        from webui.backend.lib.schedule_schema import Schedule
        assert isinstance(all_schedules, list)
        assert len(all_schedules) == 3

        for schedule in all_schedules:
            assert isinstance(schedule, Schedule)

        # Check all IDs present
        schedule_ids = [s.schedule_id for s in all_schedules]
        assert "builtin-1" in schedule_ids
        assert "builtin-2" in schedule_ids
        assert "user-1" in schedule_ids

    def test_list_schedules_user_overrides_builtin_same_id(
        self,
        temp_schedules_dir,
        temp_builtin_dir,
        sample_schedule_json
    ):
        """User schedule with same ID overrides built-in in list."""
        schedule_id = "duplicate-schedule"

        # Create built-in schedule
        builtin_data = json.loads(sample_schedule_json)
        builtin_data["schedule_id"] = schedule_id
        builtin_data["name"] = "Built-in Schedule"
        (temp_builtin_dir / f"{schedule_id}.json").write_text(json.dumps(builtin_data))

        # Create user schedule with same ID
        user_data = json.loads(sample_schedule_json)
        user_data["schedule_id"] = schedule_id
        user_data["name"] = "User Modified Schedule"
        (temp_schedules_dir / f"{schedule_id}.json").write_text(json.dumps(user_data))

        all_schedules = list_schedules(include_builtin=True)

        # Should only include one schedule with this ID (user version)
        matching = [s for s in all_schedules if s.schedule_id == schedule_id]
        assert len(matching) == 1
        assert matching[0].name == "User Modified Schedule"

    def test_cleanup_temp_files_removes_stale_locks(self, temp_schedules_dir):
        """cleanup_temp_files removes old .lock files."""
        import time

        # Create some .lock files
        old_lock = temp_schedules_dir / "old-schedule.json.lock"
        old_lock.write_text("")

        # Make it old by modifying timestamp
        old_time = time.time() - 7200  # 2 hours ago
        import os
        os.utime(old_lock, (old_time, old_time))

        # Create a recent .lock file
        recent_lock = temp_schedules_dir / "recent-schedule.json.lock"
        recent_lock.write_text("")

        # Cleanup files older than 1 hour (3600 seconds)
        removed_count = cleanup_temp_files(max_age_seconds=3600)

        # Should remove old lock but not recent one
        assert removed_count == 1
        assert not old_lock.exists()
        assert recent_lock.exists()


class TestEdgeCases:
    """Tests for edge cases and error handling paths."""

    def test_list_schedule_ids_excludes_backup_files(self, temp_schedules_dir, sample_schedule_json):
        """list_schedule_ids should exclude .bak files."""
        # Create valid schedule
        (temp_schedules_dir / "valid-schedule.json").write_text(sample_schedule_json)

        # Create backup file (should be excluded)
        (temp_schedules_dir / "valid-schedule.json.bak").write_text(sample_schedule_json)

        ids = list_schedule_ids(is_builtin=False)
        assert "valid-schedule" in ids
        # Backup should NOT appear
        assert "valid-schedule.json" not in ids

    def test_list_schedule_ids_excludes_lock_files(self, temp_schedules_dir, sample_schedule_json):
        """list_schedule_ids should exclude .lock files."""
        # Create valid schedule
        (temp_schedules_dir / "valid-schedule.json").write_text(sample_schedule_json)

        # Create lock file (should be excluded)
        (temp_schedules_dir / "valid-schedule.json.lock").write_text("")

        ids = list_schedule_ids(is_builtin=False)
        assert "valid-schedule" in ids
        assert len(ids) == 1  # Only the valid schedule

    def test_list_schedule_ids_nonexistent_directory(self, monkeypatch):
        """list_schedule_ids returns empty list for nonexistent directory."""
        from pathlib import Path

        import webui.backend.lib.schedule_storage as module

        # Point to nonexistent directory
        monkeypatch.setattr(module, "SCHEDULES_DIR", Path("/nonexistent/path"))

        ids = list_schedule_ids(is_builtin=False)
        assert ids == []

    def test_read_schedule_empty_file(self, temp_schedules_dir):
        """read_schedule returns None for empty file."""
        schedule_id = "empty-schedule"
        (temp_schedules_dir / f"{schedule_id}.json").write_text("")

        result = read_schedule(schedule_id)
        assert result is None

    def test_update_schedule_nonexistent(self, temp_schedules_dir):
        """update_schedule returns None for nonexistent schedule."""
        result = update_schedule("nonexistent-schedule", {"name": "New Name"})
        assert result is None

    def test_list_schedules_empty_directories(self, temp_schedules_dir, temp_builtin_dir):
        """list_schedules returns empty list when no schedules exist."""
        # Both directories exist but are empty
        schedules = list_schedules(include_builtin=True)
        assert schedules == []

    def test_list_schedules_user_only(self, temp_schedules_dir, temp_builtin_dir, sample_schedule_json):
        """list_schedules with include_builtin=False only returns user schedules."""
        # Create user schedule
        user_data = json.loads(sample_schedule_json)
        user_data["schedule_id"] = "user-only"
        (temp_schedules_dir / "user-only.json").write_text(json.dumps(user_data))

        # Create builtin schedule
        builtin_data = json.loads(sample_schedule_json)
        builtin_data["schedule_id"] = "builtin-only"
        (temp_builtin_dir / "builtin-only.json").write_text(json.dumps(builtin_data))

        # Get user schedules only
        schedules = list_schedules(include_builtin=False)
        schedule_ids = [s.schedule_id for s in schedules]

        assert "user-only" in schedule_ids
        assert "builtin-only" not in schedule_ids

    def test_cleanup_temp_files_empty_directory(self, temp_schedules_dir):
        """cleanup_temp_files handles empty directory."""
        removed = cleanup_temp_files(max_age_seconds=3600)
        assert removed == 0

    def test_update_schedule_with_validation_error(self, temp_schedules_dir, sample_schedule):
        """update_schedule raises ScheduleValidationError for invalid updates."""
        from webui.backend.lib.schedule_schema import ScheduleValidationError

        # Create valid schedule
        create_schedule(sample_schedule)

        # Try to update with invalid data (empty name)
        with pytest.raises(ScheduleValidationError):
            update_schedule(sample_schedule.schedule_id, {"name": ""})

    def test_builtin_cleanup_locks(self, temp_builtin_dir):
        """cleanup_temp_files also cleans built-in directory."""
        import os
        import time

        # Create old lock file in builtin directory
        old_lock = temp_builtin_dir / "old-builtin.json.lock"
        old_lock.write_text("")
        old_time = time.time() - 7200  # 2 hours ago
        os.utime(old_lock, (old_time, old_time))

        # Cleanup should find and remove it
        removed = cleanup_temp_files(max_age_seconds=3600)
        assert removed == 1
        assert not old_lock.exists()

    def test_list_schedules_skips_invalid_schedules(self, temp_schedules_dir, sample_schedule_json):
        """list_schedules skips schedules that fail validation."""
        import json

        # Create valid schedule
        valid_data = json.loads(sample_schedule_json)
        valid_data["schedule_id"] = "valid-schedule"
        (temp_schedules_dir / "valid-schedule.json").write_text(json.dumps(valid_data))

        # Create invalid schedule (empty event_patterns after initial parse)
        invalid_data = json.loads(sample_schedule_json)
        invalid_data["schedule_id"] = "invalid-schedule"
        invalid_data["event_patterns"] = []  # Invalid: no patterns
        (temp_schedules_dir / "invalid-schedule.json").write_text(json.dumps(invalid_data))

        # Only valid schedule should be returned
        schedules = list_schedules(include_builtin=False)
        assert len(schedules) == 1
        assert schedules[0].schedule_id == "valid-schedule"

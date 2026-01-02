"""Integration tests for schedule storage workflows (Issue #209).

Tests end-to-end schedule storage scenarios including:
- Complete CRUD workflow
- Concurrent access
- Persistence verification
- Error recovery
- Unicode support
- Built-in schedule protection

Run with: MOTHBOX_ENV=test pytest Tests/integration/test_schedule_storage_workflow.py -v -s

These tests are marked as @pytest.mark.integration but NOT @pytest.mark.hardware
since they test multi-layer integration without requiring Pi hardware.

Issue #209 - Scheduler Phase 1: Schedule Storage
"""

import json
import os
import shutil
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest


def _test_uuid(name: str) -> str:
    """Generate deterministic test UUID from name."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"test.integration.storage.{name}"))

# Mark all tests in this module as integration tests (but not hardware)
pytestmark = pytest.mark.integration

# Setup path
FIRMWARE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(FIRMWARE_DIR))
sys.path.insert(0, str(FIRMWARE_DIR / "webui" / "backend"))
os.environ.setdefault("MOTHBOX_ENV", "test")

from webui.backend.lib.schedule_schema import (
    Action,
    IntervalTrigger,
    Routine,
    Schedule,
    TimeWindow,
)
from webui.backend.lib.schedule_storage import (
    create_schedule,
    delete_schedule,
    is_builtin_schedule,
    list_schedules,
    read_schedule,
    update_schedule,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_schedules_env(tmp_path, monkeypatch):
    """Mock both SCHEDULES_DIR and BUILTIN_SCHEDULES_DIR."""
    # Create user schedules directory
    user_schedules_dir = tmp_path / "schedules"
    user_schedules_dir.mkdir()

    # Create built-in schedules directory
    builtin_schedules_dir = tmp_path / "presets_builtin" / "schedules"
    builtin_schedules_dir.mkdir(parents=True)

    # Patch in both mothbox_paths (for get_schedule_path) and schedule_storage (for direct refs)
    import webui.backend.lib.schedule_storage as ss

    monkeypatch.setattr('mothbox_paths.SCHEDULES_DIR', user_schedules_dir)
    monkeypatch.setattr('mothbox_paths.BUILTIN_SCHEDULES_DIR', builtin_schedules_dir)
    monkeypatch.setattr(ss, "SCHEDULES_DIR", user_schedules_dir)
    monkeypatch.setattr(ss, "BUILTIN_SCHEDULES_DIR", builtin_schedules_dir)

    return {
        "user_dir": user_schedules_dir,
        "builtin_dir": builtin_schedules_dir,
    }


@pytest.fixture
def sample_schedule_factory():
    """Factory function to create valid schedules with unique IDs (Schema 3.0)."""

    def _create_schedule(schedule_id="", name="Test Schedule", interval_minutes=60):
        """Create a valid schedule with specified parameters."""
        # Generate UUIDs if not provided
        if not schedule_id:
            schedule_id = _test_uuid(f"default-{name}")

        action = Action(
            action_type="gpio",
            action_name="attract_on",
            offset_minutes=0,
            description="Turn on attract lights",
        )

        window = TimeWindow(start_time="21:00", end_time="05:00")
        trigger = IntervalTrigger(interval_minutes=interval_minutes, time_window=window)

        routine = Routine(
            routine_id=_test_uuid(f"routine-{schedule_id}"),
            name="UV Capture Cycle",
            description="Test routine",
            trigger=trigger,
            actions=[action],
        )

        schedule = Schedule(
            schedule_id=schedule_id,
            name=name,
            description="A test schedule",
            routines=[routine],
            enabled=True,
            is_active=False,
        )

        return schedule

    return _create_schedule


# ============================================================================
# Test Full CRUD Workflow
# ============================================================================


class TestScheduleWorkflow:
    """Integration tests for schedule storage workflows."""

    def test_full_crud_workflow(self, temp_schedules_env, sample_schedule_factory):
        """Full lifecycle test: create -> read -> update -> delete."""
        user_dir = temp_schedules_env["user_dir"]

        # 1. CREATE - Create new schedule
        schedule = sample_schedule_factory(
            schedule_id=_test_uuid("workflow-test"),
            name="Workflow Test Schedule",
        )

        success = create_schedule(schedule)
        assert success is True, "Should successfully create schedule"

        # Verify file exists
        schedule_file = user_dir / f"{schedule.schedule_id}.json"
        assert schedule_file.exists(), "Schedule file should exist"

        # 2. READ - Read back schedule
        read_schedule_obj = read_schedule(schedule.schedule_id)
        assert read_schedule_obj is not None, "Should read schedule"
        assert read_schedule_obj.schedule_id == schedule.schedule_id
        assert read_schedule_obj.name == "Workflow Test Schedule"
        assert len(read_schedule_obj.routines) == 1

        # 3. UPDATE - Partial update
        original_modified_at = read_schedule_obj.modified_at
        time.sleep(0.1)  # Ensure timestamp difference

        updated_schedule = update_schedule(
            schedule.schedule_id,
            {"name": "Updated Workflow Schedule", "description": "Updated description"},
        )
        assert updated_schedule is not None, "Should update schedule"
        assert updated_schedule.name == "Updated Workflow Schedule"
        assert updated_schedule.description == "Updated description"
        # Original fields should be preserved
        assert updated_schedule.schedule_id == schedule.schedule_id
        assert len(updated_schedule.routines) == 1
        # Modified timestamp should be updated
        assert updated_schedule.modified_at != original_modified_at

        # 4. DELETE - Delete schedule
        delete_success = delete_schedule(schedule.schedule_id, backup=True)
        assert delete_success is True, "Should successfully delete schedule"

        # Verify file is gone
        assert not schedule_file.exists(), "Schedule file should be deleted"

        # Verify backup exists
        backup_file = user_dir / f"{schedule.schedule_id}.json.bak"
        assert backup_file.exists(), "Backup file should exist"

        # Verify read returns None after deletion
        final_read = read_schedule(schedule.schedule_id)
        assert final_read is None, "Should return None after deletion"

    def test_concurrent_reads_no_corruption(
        self, temp_schedules_env, sample_schedule_factory
    ):
        """Multiple threads reading same schedule should not corrupt data."""
        schedule = sample_schedule_factory(
            schedule_id=_test_uuid("concurrent-read-test"),
            name="Concurrent Read Test",
        )

        # Create schedule
        create_schedule(schedule)

        # Perform 50 concurrent reads
        read_count = 50
        read_results = []
        errors = []
        lock = threading.Lock()

        def reader():
            """Read schedule."""
            try:
                result = read_schedule(schedule.schedule_id)
                with lock:
                    read_results.append(result)
            except Exception as e:
                with lock:
                    errors.append(str(e))

        # Execute concurrent reads
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(reader) for _ in range(read_count)]
            for future in as_completed(futures, timeout=5.0):
                future.result()

        # Verify no errors
        assert len(errors) == 0, f"Should have no errors: {errors}"

        # Verify all reads succeeded
        assert len(read_results) == read_count

        # Verify all results are consistent
        for result in read_results:
            assert result is not None
            assert result.schedule_id == schedule.schedule_id
            assert result.name == "Concurrent Read Test"
            assert len(result.routines) == 1

    def test_schedule_persists_across_sessions(
        self, temp_schedules_env, sample_schedule_factory
    ):
        """Schedule should persist to disk and be readable after 'restart'."""
        user_dir = temp_schedules_env["user_dir"]

        # Create and write schedule
        schedule = sample_schedule_factory(
            schedule_id=_test_uuid("persistence-test"),
            name="Persistence Test Schedule",
        )

        create_schedule(schedule)

        # Simulate "session end" by reading file directly from disk
        schedule_file = user_dir / f"{schedule.schedule_id}.json"
        assert schedule_file.exists()

        with open(schedule_file) as f:
            disk_data = json.load(f)

        # Verify data structure
        assert disk_data["schedule_id"] == schedule.schedule_id
        assert disk_data["name"] == "Persistence Test Schedule"
        assert disk_data["schema_version"] == "3.0"

        # Simulate "new session" by reading schedule back
        read_schedule_obj = read_schedule(schedule.schedule_id)
        assert read_schedule_obj is not None
        assert read_schedule_obj.schedule_id == schedule.schedule_id
        assert read_schedule_obj.name == "Persistence Test Schedule"

    def test_corrupted_file_recovery(self, temp_schedules_env):
        """Gracefully handle corrupted JSON file."""
        user_dir = temp_schedules_env["user_dir"]

        # Create corrupted JSON file
        schedule_id = "corrupted-schedule"
        schedule_file = user_dir / f"{schedule_id}.json"
        schedule_file.write_text("{ invalid json, missing bracket")

        # Read should return None gracefully
        result = read_schedule(schedule_id)
        assert result is None, "Should return None for corrupted JSON"

        # Create another corrupted file with valid JSON but invalid schema
        schedule_id_2 = "invalid-schema"
        schedule_file_2 = user_dir / f"{schedule_id_2}.json"
        schedule_file_2.write_text(
            json.dumps(
                {
                    "schema_version": "3.0",
                    "schedule_id": schedule_id_2,
                    "name": "Invalid Schedule",
                    "routines": [],  # Empty routines (invalid)
                }
            )
        )

        # Read should return None for invalid schema
        result_2 = read_schedule(schedule_id_2)
        assert result_2 is None, "Should return None for invalid schema"

    def test_unicode_schedule_name(self, temp_schedules_env, sample_schedule_factory):
        """International characters in schedule names should work correctly."""
        # Test various Unicode characters
        unicode_schedules = [
            (_test_uuid("unicode-chinese"), "夜间飞蛾调查"),  # Chinese
            (_test_uuid("unicode-japanese"), "夜間調査スケジュール"),  # Japanese
            (_test_uuid("unicode-russian"), "Ночной график мотыльков"),  # Russian
            (_test_uuid("unicode-arabic"), "جدول دراسة الفراشات الليلية"),  # Arabic
            (_test_uuid("unicode-emoji"), "Night Survey 🦋🌙"),  # Emoji
        ]

        for schedule_id, unicode_name in unicode_schedules:
            # Create schedule with Unicode name
            schedule = sample_schedule_factory(
                schedule_id=schedule_id,
                name=unicode_name,
            )

            # Create and write
            success = create_schedule(schedule)
            assert success is True, f"Should create schedule with name: {unicode_name}"

            # Read back and verify
            read_schedule_obj = read_schedule(schedule_id)
            assert read_schedule_obj is not None
            assert (
                read_schedule_obj.name == unicode_name
            ), f"Unicode name should match: {unicode_name}"

            # Update with another Unicode string
            updated_name = f"{unicode_name} - Updated ✓"
            updated_schedule = update_schedule(schedule_id, {"name": updated_name})
            assert updated_schedule is not None
            assert updated_schedule.name == updated_name

    def test_max_routines_boundary(self, temp_schedules_env):
        """Schedule with exactly 10 routines (MAX_ROUTINES_PER_SCHEDULE) should work."""
        from webui.backend.lib.schedule_schema import MAX_ROUTINES_PER_SCHEDULE

        # Create schedule with MAX_ROUTINES_PER_SCHEDULE routines
        routines = []
        window = TimeWindow(start_time="21:00", end_time="05:00")

        for i in range(MAX_ROUTINES_PER_SCHEDULE):
            action = Action(
                action_type="gpio",
                action_name="attract_on",
                offset_minutes=0,
                description=f"Action {i + 1}",
            )
            trigger = IntervalTrigger(interval_minutes=60, time_window=window)
            routine = Routine(
                routine_id=_test_uuid(f"max-routine-{i + 1}"),
                name=f"Routine {i + 1}",
                description=f"Test routine {i + 1}",
                trigger=trigger,
                actions=[action],
            )
            routines.append(routine)

        schedule = Schedule(
            schedule_id=_test_uuid("max-routines-test"),
            name="Max Routines Test",
            routines=routines,
        )

        # Should successfully create schedule with max routines
        success = create_schedule(schedule)
        assert success is True

        # Read back and verify all routines
        read_schedule_obj = read_schedule(schedule.schedule_id)
        assert read_schedule_obj is not None
        assert len(read_schedule_obj.routines) == MAX_ROUTINES_PER_SCHEDULE

        # Verify each routine
        for i, routine in enumerate(read_schedule_obj.routines):
            assert routine.name == f"Routine {i + 1}"

    def test_backup_can_be_restored(self, temp_schedules_env, sample_schedule_factory):
        """After delete with backup, .bak file can restore schedule."""
        user_dir = temp_schedules_env["user_dir"]

        # Create schedule
        schedule = sample_schedule_factory(
            schedule_id=_test_uuid("backup-restore-test"),
            name="Backup Restore Test",
        )

        create_schedule(schedule)

        # Read original to verify
        original_schedule = read_schedule(schedule.schedule_id)
        assert original_schedule is not None

        # Delete with backup
        delete_success = delete_schedule(schedule.schedule_id, backup=True)
        assert delete_success is True

        # Verify original file is gone
        schedule_file = user_dir / f"{schedule.schedule_id}.json"
        assert not schedule_file.exists()

        # Verify backup exists
        backup_file = user_dir / f"{schedule.schedule_id}.json.bak"
        assert backup_file.exists()

        # "Restore" by renaming backup to original
        shutil.copy(backup_file, schedule_file)

        # Read restored schedule
        restored_schedule = read_schedule(schedule.schedule_id)
        assert restored_schedule is not None
        assert restored_schedule.schedule_id == original_schedule.schedule_id
        assert restored_schedule.name == original_schedule.name
        assert len(restored_schedule.routines) == len(original_schedule.routines)

    def test_builtin_immutability_in_workflow(
        self, temp_schedules_env, sample_schedule_factory
    ):
        """Verify built-in schedules cannot be modified in realistic workflow."""
        builtin_dir = temp_schedules_env["builtin_dir"]

        # Create a built-in schedule
        builtin_schedule = sample_schedule_factory(
            schedule_id=_test_uuid("builtin-protected"),
            name="Built-in Protected Schedule",
        )

        # Write directly to built-in directory (simulating shipped built-in)
        builtin_file = builtin_dir / f"{builtin_schedule.schedule_id}.json"
        builtin_file.write_text(json.dumps(builtin_schedule.to_dict(), indent=2))

        # Verify it's recognized as built-in
        assert is_builtin_schedule(builtin_schedule.schedule_id) is True

        # Attempt to update should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            update_schedule(builtin_schedule.schedule_id, {"name": "Hacked Name"})

        assert "built-in" in str(exc_info.value).lower()

        # Attempt to delete should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            delete_schedule(builtin_schedule.schedule_id)

        assert "built-in" in str(exc_info.value).lower()

        # Verify file still exists and unchanged
        assert builtin_file.exists()
        with open(builtin_file) as f:
            data = json.load(f)
        assert data["name"] == "Built-in Protected Schedule"

        # Verify built-in schedule is included in list_schedules
        all_schedules = list_schedules(include_builtin=True)
        builtin_found = any(
            s.schedule_id == builtin_schedule.schedule_id for s in all_schedules
        )
        assert builtin_found is True

        # User can "override" built-in by creating user schedule with same ID
        user_schedule = sample_schedule_factory(
            schedule_id=builtin_schedule.schedule_id,
            name="User Override Schedule",
        )

        create_success = create_schedule(user_schedule)
        assert create_success is True

        # Now the user version should take precedence
        read_schedule_obj = read_schedule(builtin_schedule.schedule_id)
        assert read_schedule_obj is not None
        assert read_schedule_obj.name == "User Override Schedule"

        # Update should now work (modifying user version, not built-in)
        updated_schedule = update_schedule(
            builtin_schedule.schedule_id,
            {"description": "User can update their override"},
        )
        assert updated_schedule is not None
        assert updated_schedule.description == "User can update their override"

        # Built-in file should remain unchanged
        with open(builtin_file) as f:
            data = json.load(f)
        assert data["name"] == "Built-in Protected Schedule"  # Original name unchanged

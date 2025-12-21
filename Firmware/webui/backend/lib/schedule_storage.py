"""
Schedule Storage Library for Mothbox Visual Scheduler.

Manages schedule JSON files with CRUD operations and file locking.
Each schedule is stored as a self-contained JSON file with embedded event patterns.

File Locations:
- User schedules: CONFIG_DIR/schedules/{schedule_id}.json
- Built-in schedules: webui/backend/presets_builtin/schedules/{schedule_id}.json

Features:
- Thread-safe operations: FileLock for atomic read-modify-write
- JSON storage: One file per schedule
- Built-in protection: Read-only access to built-in schedules
- Backup support: Create .bak file before overwriting/deleting
- Schema validation: Validate all schedules before writing
- Graceful errors: Return None/False for missing/corrupt files

Usage:
    from webui.backend.lib.schedule_storage import (
        create_schedule,
        read_schedule,
        update_schedule,
        delete_schedule,
        list_schedules,
    )

    # Create new schedule
    schedule = Schedule(
        schedule_id="",
        name="Nightly Survey",
        event_patterns=[...],
        trigger_type="interval",
        interval_trigger=IntervalTrigger(...),
    )
    create_schedule(schedule)

    # Read existing schedule
    schedule = read_schedule("nightly-survey")
    if schedule:
        print(f"Schedule: {schedule.name}")

    # Update schedule
    updated = update_schedule("nightly-survey", {"name": "Updated Name"})

    # Delete schedule
    delete_schedule("nightly-survey", backup=True)

    # List all schedules (user + built-in)
    schedules = list_schedules(include_builtin=True)

Issue #209 - Scheduler Phase 1: Schedule Storage
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path

from mothbox_paths import (
    BUILTIN_SCHEDULES_DIR,
    SCHEDULES_DIR,
    get_schedule_path,
)
from webui.backend.lib.schedule_schema import (
    Schedule,
    ScheduleValidationError,
    validate_schedule,
)
from webui.backend.lib.sidecar_metadata import FileLock

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

SCHEDULE_FILENAME_EXTENSION = ".json"
BACKUP_EXTENSION = ".bak"

def schedule_exists(schedule_id: str, is_builtin: bool = False) -> bool:
    """Check if schedule file exists.

    Args:
        schedule_id: Schedule identifier
        is_builtin: If True, check built-in directory, else user directory

    Returns:
        True if schedule file exists, False otherwise (also False for invalid IDs)

    Example:
        >>> schedule_exists("nightly-survey", is_builtin=False)
        True
    """
    schedule_path = get_schedule_path(schedule_id, is_builtin=is_builtin)
    if schedule_path is None:
        return False
    return schedule_path.exists()


def list_schedule_ids(is_builtin: bool = False) -> list[str]:
    """List all schedule IDs in directory.

    Only includes .json files (excludes .bak, .lock, etc.).

    Args:
        is_builtin: If True, list built-in schedules, else user schedules

    Returns:
        List of schedule IDs (sorted alphabetically)

    Example:
        >>> list_schedule_ids(is_builtin=False)
        ['nightly-survey', 'weekly-capture']
    """
    base_dir = BUILTIN_SCHEDULES_DIR if is_builtin else SCHEDULES_DIR

    if not base_dir.exists():
        return []

    schedule_ids = []
    for json_file in base_dir.glob(f"*{SCHEDULE_FILENAME_EXTENSION}"):
        # Skip backup and lock files
        if json_file.name.endswith(f"{SCHEDULE_FILENAME_EXTENSION}{BACKUP_EXTENSION}"):
            continue
        if json_file.name.endswith(f"{SCHEDULE_FILENAME_EXTENSION}.lock"):
            continue

        # Extract schedule ID (remove .json extension)
        schedule_id = json_file.stem
        schedule_ids.append(schedule_id)

    return sorted(schedule_ids)


def find_schedule(schedule_id: str) -> tuple[Path, bool] | None:
    """Find schedule file in user or built-in directories.

    User schedules take precedence over built-in schedules with the same ID.

    Args:
        schedule_id: Schedule identifier

    Returns:
        Tuple of (path, is_builtin) if found, None if not found

    Example:
        >>> find_schedule("nightly-survey")
        (PosixPath('/etc/mothbox/schedules/nightly-survey.json'), False)
        >>> find_schedule("nonexistent")
        None
    """
    # Check user directory first (precedence)
    user_path = get_schedule_path(schedule_id, is_builtin=False)
    if user_path is not None and user_path.exists():
        return (user_path, False)

    # Check built-in directory
    builtin_path = get_schedule_path(schedule_id, is_builtin=True)
    if builtin_path is not None and builtin_path.exists():
        return (builtin_path, True)

    return None


def is_builtin_schedule(schedule_id: str) -> bool:
    """Check if schedule is a built-in schedule.

    Returns False if schedule exists only in user directory or doesn't exist.

    Args:
        schedule_id: Schedule identifier

    Returns:
        True if schedule exists in built-in directory, False otherwise

    Example:
        >>> is_builtin_schedule("nightly-survey")
        True
        >>> is_builtin_schedule("my-custom-schedule")
        False
    """
    result = find_schedule(schedule_id)
    if result is None:
        return False

    _path, is_builtin = result
    return is_builtin


# =============================================================================
# CRUD OPERATIONS
# =============================================================================


def create_schedule(schedule: Schedule) -> bool:
    """Create new schedule file.

    Validates schedule before writing. Creates schedules directory if it doesn't exist.

    Args:
        schedule: Schedule object to write

    Returns:
        True if successful, False otherwise

    Raises:
        ScheduleValidationError: If schedule validation fails

    Example:
        >>> schedule = Schedule(schedule_id="test", name="Test Schedule", ...)
        >>> create_schedule(schedule)
        True
    """
    # Validate schedule first
    valid, error = validate_schedule(schedule)
    if not valid:
        raise ScheduleValidationError(error)

    schedule_path = get_schedule_path(schedule.schedule_id, is_builtin=False)
    if schedule_path is None:
        raise ValueError(f"Invalid schedule ID: {schedule.schedule_id}")

    try:
        # Ensure schedules directory exists
        SCHEDULES_DIR.mkdir(parents=True, exist_ok=True)

        # Write with file locking
        with FileLock(schedule_path, exclusive=True) as f:
            f.truncate()
            json.dump(schedule.to_dict(), f, indent=2)

        # Set file permissions
        try:
            schedule_path.chmod(0o644)
        except (OSError, PermissionError) as e:
            logger.debug(f"Could not set permissions on {schedule_path}: {e}")

        return True

    except Exception as e:
        logger.error(f"Failed to create schedule {schedule.schedule_id}: {e}")
        return False


def read_schedule(schedule_id: str) -> Schedule | None:
    """Read schedule from file.

    Gracefully handles missing, corrupted, or invalid schedules by returning None.

    Args:
        schedule_id: Schedule identifier

    Returns:
        Schedule object if valid file exists, None otherwise

    Example:
        >>> schedule = read_schedule("nightly-survey")
        >>> if schedule:
        ...     print(schedule.name)
        'Nightly Survey'
    """
    result = find_schedule(schedule_id)
    if result is None:
        return None

    schedule_path, _is_builtin = result

    try:
        # Read with shared lock (allows concurrent reads)
        with FileLock(schedule_path, exclusive=False) as f:
            content = f.read()
            if not content:
                return None

            f.seek(0)
            data = json.load(f)

        # Validate schema
        valid, error = validate_schedule(Schedule.from_dict(data))
        if not valid:
            logger.warning(f"Invalid schedule in {schedule_path}: {error}")
            return None

        return Schedule.from_dict(data)

    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
        logger.warning(f"Failed to read schedule {schedule_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error reading schedule {schedule_id}: {e}")
        return None


def update_schedule(
    schedule_id: str,
    updates: dict,
    is_builtin: bool = False
) -> Schedule | None:
    """Update existing schedule with partial field updates.

    Performs atomic read-modify-write with file locking.
    Updates modified_at timestamp automatically.

    Args:
        schedule_id: Schedule identifier
        updates: Dictionary of fields to update
        is_builtin: If True, raise error (built-in schedules are read-only)

    Returns:
        Updated Schedule object if successful, None if schedule doesn't exist

    Raises:
        ValueError: If attempting to update built-in schedule

    Example:
        >>> update_schedule("nightly-survey", {"name": "Updated Name"})
        Schedule(schedule_id='nightly-survey', name='Updated Name', ...)
    """
    # Protect built-in schedules
    if is_builtin or is_builtin_schedule(schedule_id):
        raise ValueError("Cannot modify built-in schedule")

    schedule_path = get_schedule_path(schedule_id, is_builtin=False)
    if schedule_path is None:
        raise ValueError(f"Invalid schedule ID: {schedule_id}")

    if not schedule_path.exists():
        return None

    try:
        # Atomic read-modify-write with exclusive lock
        with FileLock(schedule_path, exclusive=True) as f:
            # Read existing schedule
            content = f.read()
            if not content:
                return None

            f.seek(0)
            data = json.load(f)
            schedule = Schedule.from_dict(data)

            # Apply updates
            for key, value in updates.items():
                if hasattr(schedule, key):
                    setattr(schedule, key, value)

            # Update modified_at timestamp
            schedule.modified_at = datetime.now().isoformat()

            # Validate updated schedule
            valid, error = validate_schedule(schedule)
            if not valid:
                raise ScheduleValidationError(error)

            # Write atomically while holding lock
            f.seek(0)
            f.truncate()
            json.dump(schedule.to_dict(), f, indent=2)

        return schedule

    except ScheduleValidationError:
        raise
    except Exception as e:
        logger.error(f"Failed to update schedule {schedule_id}: {e}")
        return None


def delete_schedule(
    schedule_id: str,
    backup: bool = True,
    is_builtin: bool = False
) -> bool:
    """Delete schedule file.

    Creates backup file before deletion if requested.

    Args:
        schedule_id: Schedule identifier
        backup: If True, create .bak backup before deleting
        is_builtin: If True, raise error (built-in schedules are read-only)

    Returns:
        True if schedule was deleted, False if schedule didn't exist

    Raises:
        ValueError: If attempting to delete built-in schedule

    Example:
        >>> delete_schedule("nightly-survey", backup=True)
        True
    """
    # Protect built-in schedules
    if is_builtin or is_builtin_schedule(schedule_id):
        raise ValueError("Cannot delete built-in schedule")

    schedule_path = get_schedule_path(schedule_id, is_builtin=False)
    if schedule_path is None:
        raise ValueError(f"Invalid schedule ID: {schedule_id}")

    if not schedule_path.exists():
        return False

    try:
        # Create backup if requested
        if backup:
            backup_path = schedule_path.with_suffix(
                f"{SCHEDULE_FILENAME_EXTENSION}{BACKUP_EXTENSION}"
            )
            backup_path.write_text(schedule_path.read_text())

        # Delete schedule file
        schedule_path.unlink()
        return True

    except Exception as e:
        logger.error(f"Failed to delete schedule {schedule_id}: {e}")
        return False


# =============================================================================
# BUILT-IN SCHEDULES
# =============================================================================


def get_builtin_schedules() -> list[Schedule]:
    """Get all built-in schedules.

    Returns:
        List of built-in Schedule objects (empty list if none exist)

    Example:
        >>> builtin_schedules = get_builtin_schedules()
        >>> len(builtin_schedules)
        3
        >>> builtin_schedules[0].name
        'Nightly Moth Survey'
    """
    builtin_ids = list_schedule_ids(is_builtin=True)
    schedules = []

    for schedule_id in builtin_ids:
        schedule_path = get_schedule_path(schedule_id, is_builtin=True)
        if schedule_path is None:
            logger.warning(f"Invalid built-in schedule ID: {schedule_id}")
            continue

        try:
            with open(schedule_path) as f:
                data = json.load(f)

            # Override schedule_id from filename (built-in schedules may have been renamed)
            data["schedule_id"] = schedule_id

            # Validate and create schedule
            schedule = Schedule.from_dict(data)
            valid, error = validate_schedule(schedule)
            if valid:
                schedules.append(schedule)
            else:
                logger.warning(f"Invalid built-in schedule {schedule_id}: {error}")

        except Exception as e:
            logger.warning(f"Failed to load built-in schedule {schedule_id}: {e}")

    return schedules


# =============================================================================
# LIST OPERATIONS
# =============================================================================


def list_schedules(include_builtin: bool = True) -> list[Schedule]:
    """List all schedules (user and optionally built-in).

    User schedules with the same ID as built-in schedules override the built-in versions.

    Args:
        include_builtin: If True, include built-in schedules

    Returns:
        List of Schedule objects (sorted by schedule_id)

    Example:
        >>> schedules = list_schedules(include_builtin=True)
        >>> len(schedules)
        5
        >>> schedules[0].name
        'Hourly Capture'
    """
    schedules = []
    seen_ids = set()

    # Load user schedules first (they take precedence)
    user_ids = list_schedule_ids(is_builtin=False)
    for schedule_id in user_ids:
        schedule = read_schedule(schedule_id)
        if schedule:
            schedules.append(schedule)
            seen_ids.add(schedule_id)

    # Load built-in schedules (skip if user version exists)
    if include_builtin:
        builtin_schedules = get_builtin_schedules()
        for schedule in builtin_schedules:
            if schedule.schedule_id not in seen_ids:
                schedules.append(schedule)
                seen_ids.add(schedule.schedule_id)

    # Sort by schedule_id
    return sorted(schedules, key=lambda s: s.schedule_id)


# =============================================================================
# CLEANUP
# =============================================================================


def cleanup_temp_files(max_age_seconds: int = 3600) -> int:
    """Remove stale .lock files from schedules directories.

    Cleans up lock files older than max_age_seconds from both user and built-in directories.

    Args:
        max_age_seconds: Maximum age in seconds (default 1 hour)

    Returns:
        Number of lock files removed

    Example:
        >>> cleanup_temp_files(max_age_seconds=3600)
        2
    """
    removed_count = 0
    current_time = time.time()

    # Clean user schedules directory
    if SCHEDULES_DIR.exists():
        for lock_file in SCHEDULES_DIR.glob("*.lock"):
            try:
                file_age = current_time - lock_file.stat().st_mtime
                if file_age > max_age_seconds:
                    lock_file.unlink()
                    removed_count += 1
            except Exception as e:
                logger.debug(f"Failed to remove lock file {lock_file}: {e}")

    # Clean built-in schedules directory (shouldn't have locks, but clean anyway)
    if BUILTIN_SCHEDULES_DIR.exists():
        for lock_file in BUILTIN_SCHEDULES_DIR.glob("*.lock"):
            try:
                file_age = current_time - lock_file.stat().st_mtime
                if file_age > max_age_seconds:
                    lock_file.unlink()
                    removed_count += 1
            except Exception as e:
                logger.debug(f"Failed to remove lock file {lock_file}: {e}")

    return removed_count


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Constants
    "SCHEDULE_FILENAME_EXTENSION",
    "SCHEDULES_DIR",
    "BUILTIN_SCHEDULES_DIR",
    # Path utilities
    "get_schedule_path",
    "schedule_exists",
    "list_schedule_ids",
    "find_schedule",
    "is_builtin_schedule",
    # CRUD operations
    "create_schedule",
    "read_schedule",
    "update_schedule",
    "delete_schedule",
    # Built-in handling
    "get_builtin_schedules",
    # List operations
    "list_schedules",
    # Cleanup
    "cleanup_temp_files",
]

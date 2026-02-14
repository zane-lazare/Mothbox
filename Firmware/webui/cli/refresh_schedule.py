#!/usr/bin/env python3
"""Refresh cron entries for active schedule.

Regenerates date-specific cron entries (solar, moon, recurring) to prevent
60-day expiration. Called weekly via cron (0 2 * * 0).

Usage: systemd-cat -t mothbox /usr/bin/python3 /path/to/refresh_schedule.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

log_level = os.environ.get("MOTHBOX_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO), format="%(levelname)s: %(message)s"
)
logger = logging.getLogger("refresh_schedule")

EXIT_SUCCESS = 0
EXIT_FATAL = 1


def load_active_state() -> dict | None:
    """Load active_state.json from CONFIG_DIR with shared file lock.

    Returns the parsed dict, or None if no active state.
    """
    from webui.backend.lib.active_state import load_active_state as _load

    return _load()


def save_active_state(
    entries_update: list[dict[str, Any]], expected_schedule_id: str | None = None
) -> bool:
    """Merge updated entries into active_state.json under exclusive file lock.

    Re-reads the file under the exclusive lock to prevent clobbering
    concurrent modifications from other processes.

    Args:
        entries_update: New entries to write.
        expected_schedule_id: If provided, abort if the schedule_id in the
            state file has changed (another activation happened concurrently).

    Returns True on success, False on failure.
    """
    from mothbox_paths import CONFIG_DIR
    from webui.backend.lib.file_lock import FileLock

    state_file = CONFIG_DIR / "active_state.json"
    try:
        with FileLock(state_file, exclusive=True, timeout=10.0) as f:
            # Exclusive lock guarantees atomic check-and-write: no other process
            # can read or modify the file between the schedule_id check and the write.
            f.seek(0)
            current_state = json.load(f)
            if (
                expected_schedule_id is not None
                and current_state.get("schedule_id") != expected_schedule_id
            ):
                logger.warning("Schedule changed during refresh — aborting entry update")
                return False
            current_state["entries"] = entries_update
            f.seek(0)
            f.truncate()
            json.dump(current_state, f, indent=2)
        return True
    except (OSError, json.JSONDecodeError) as e:
        logger.error(f"Failed to write active_state.json: {e}")
        return False


def main() -> int:
    """Main entry point for cron refresh."""
    logger.info("Starting weekly cron entry refresh")

    # Load active state
    state = load_active_state()
    if state is None:
        return EXIT_SUCCESS

    schedule_id = state["schedule_id"]
    latitude = state.get("latitude")
    longitude = state.get("longitude")
    timezone_name = state.get("timezone_name", "UTC")

    # Fallback: derive coordinates from timezone (matches scheduler_service activation pattern)
    if latitude is None or longitude is None:
        from webui.backend.lib.timezone_coordinates import get_fallback_coordinates

        fb_lat, fb_lon, fb_source = get_fallback_coordinates()
        latitude = latitude if latitude is not None else fb_lat
        longitude = longitude if longitude is not None else fb_lon
        logger.warning(f"Coordinates missing from state — using timezone fallback ({fb_source})")

    logger.info(f"Refreshing cron entries for schedule: {schedule_id}")

    # Load the schedule from storage
    from webui.backend.lib.schedule_storage import read_schedule

    schedule = read_schedule(schedule_id)
    if schedule is None:
        logger.error(f"Schedule not found in storage: {schedule_id}")
        return EXIT_FATAL

    # Regenerate cron entries
    from webui.backend.lib.cron_bridge import (
        apply_to_system,
        expand_pattern_entries,
        schedule_to_cron,
    )

    try:
        result = schedule_to_cron(
            schedule,
            latitude=latitude,
            longitude=longitude,
            timezone_name=timezone_name,
        )
    except ValueError as e:
        logger.error(f"Cron generation failed: {e}")
        return EXIT_FATAL

    if result.errors:
        logger.error(f"Cron conversion errors: {'; '.join(result.errors)}")
        return EXIT_FATAL

    # Apply to system cron (replaces existing Mothbox entries)
    try:
        success = apply_to_system(
            entries=result.entries,
            schedule_id=schedule_id,
            set_rtc=True,
        )
    except (ValueError, OSError) as e:
        logger.error(f"Failed to apply cron entries: {e}")
        return EXIT_FATAL

    if not success:
        logger.error("apply_to_system returned False")
        return EXIT_FATAL

    logger.info(f"Applied {len(result.entries)} refreshed cron entries")

    # Expand entries and update active_state.json
    try:
        expanded = expand_pattern_entries(
            entries=result.entries,
            timezone_name=timezone_name,
        )
        if not save_active_state([e.to_dict() for e in expanded], expected_schedule_id=schedule_id):
            logger.warning("Failed to update active_state.json with new entries")
    except (ValueError, KeyError) as e:
        logger.warning(f"Failed to expand/persist entries (non-fatal): {e}")

    logger.info("Weekly cron refresh complete")
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())

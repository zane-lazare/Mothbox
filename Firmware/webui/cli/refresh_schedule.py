#!/usr/bin/env python3
"""Refresh cron entries for active schedule.

Regenerates date-specific cron entries (solar, moon, recurring) to prevent
60-day expiration. Called weekly via cron (0 2 * * 0).

Usage: systemd-cat -t mothbox /usr/bin/python3 /path/to/refresh_schedule.py
"""

from __future__ import annotations

import json
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("refresh_schedule")


def load_active_state() -> dict | None:
    """Load active_state.json from CONFIG_DIR with shared file lock.

    Returns the parsed dict, or None if no active state.
    """
    from mothbox_paths import CONFIG_DIR
    from webui.backend.lib.sidecar_metadata import FileLock

    state_file = CONFIG_DIR / "active_state.json"
    if not state_file.exists():
        logger.info("No active_state.json found — nothing to refresh")
        return None

    try:
        with FileLock(state_file, exclusive=False, timeout=10.0) as f:
            state = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Failed to read active_state.json: {e}")
        return None

    if not state.get("schedule_id"):
        logger.info("No active schedule in state file")
        return None

    return state


def save_active_state(entries_update: list[dict]) -> bool:
    """Merge updated entries into active_state.json under exclusive file lock.

    Re-reads the file under the exclusive lock to prevent clobbering
    concurrent modifications from other processes.

    Returns True on success, False on failure.
    """
    from mothbox_paths import CONFIG_DIR
    from webui.backend.lib.sidecar_metadata import FileLock

    state_file = CONFIG_DIR / "active_state.json"
    try:
        with FileLock(state_file, exclusive=True, timeout=10.0) as f:
            f.seek(0)
            current_state = json.load(f)
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
        return 0

    schedule_id = state["schedule_id"]
    latitude = state.get("latitude", 0.0)
    longitude = state.get("longitude", 0.0)
    timezone_name = state.get("timezone_name", "UTC")

    logger.info(f"Refreshing cron entries for schedule: {schedule_id}")

    # Load the schedule from storage
    from webui.backend.lib.schedule_storage import read_schedule

    schedule = read_schedule(schedule_id)
    if schedule is None:
        logger.error(f"Schedule not found in storage: {schedule_id}")
        return 1

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
    except Exception as e:
        logger.error(f"Cron generation failed: {e}")
        return 1

    if result.errors:
        logger.error(f"Cron conversion errors: {'; '.join(result.errors)}")
        return 1

    # Apply to system cron (replaces existing Mothbox entries)
    try:
        success = apply_to_system(
            entries=result.entries,
            schedule_id=schedule_id,
            set_rtc=True,
        )
    except Exception as e:
        logger.error(f"Failed to apply cron entries: {e}")
        return 1

    if not success:
        logger.error("apply_to_system returned False")
        return 1

    logger.info(f"Applied {len(result.entries)} refreshed cron entries")

    # Expand entries and update active_state.json
    try:
        expanded = expand_pattern_entries(
            entries=result.entries,
            timezone_name=timezone_name,
        )
        if not save_active_state([e.to_dict() for e in expanded]):
            logger.warning("Failed to update active_state.json with new entries")
    except Exception as e:
        logger.warning(f"Failed to expand/persist entries (non-fatal): {e}")

    logger.info("Weekly cron refresh complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())

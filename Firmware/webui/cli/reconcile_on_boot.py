#!/usr/bin/env python3
"""Reconcile GPIO state after boot.

Called via @reboot cron entry. Waits for GPIO daemon socket,
loads active schedule from active_state.json, runs reconciler.

Usage: systemd-cat -t mothbox /usr/bin/python3 /path/to/reconcile_on_boot.py
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("reconcile_on_boot")

# GPIO daemon socket path
GPIO_SOCKET = Path("/run/mothbox/gpio.sock")

# Backoff schedule: 0.5, 1, 2, 4, 8, 16 seconds (~31.5s total)
BACKOFF_DELAYS = [0.5, 1, 2, 4, 8, 16]


def wait_for_gpio_daemon() -> bool:
    """Poll for GPIO daemon socket with exponential backoff.

    Returns True if socket appeared, False if timeout.
    """
    for delay in BACKOFF_DELAYS:
        if GPIO_SOCKET.exists():
            logger.info("GPIO daemon socket found")
            return True
        logger.debug(f"Waiting {delay}s for GPIO daemon socket...")
        time.sleep(delay)

    # One final check
    if GPIO_SOCKET.exists():
        logger.info("GPIO daemon socket found")
        return True

    logger.warning("GPIO daemon socket not found after timeout")
    return False


def load_active_state() -> dict | None:
    """Load active_state.json from CONFIG_DIR with shared file lock.

    Returns the parsed dict, or None if no active state.
    """
    from mothbox_paths import CONFIG_DIR
    from webui.backend.lib.sidecar_metadata import FileLock

    state_file = CONFIG_DIR / "active_state.json"
    if not state_file.exists():
        logger.info("No active_state.json found — nothing to reconcile")
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


def main() -> int:
    """Main entry point for boot reconciliation."""
    logger.info("Starting boot GPIO reconciliation")

    # Wait for GPIO daemon
    if not wait_for_gpio_daemon():
        logger.warning("Proceeding without GPIO daemon — commands may fail")

    # Load active state
    state = load_active_state()
    if state is None:
        return 0

    schedule_id = state["schedule_id"]
    latitude = state.get("latitude", 0.0)
    longitude = state.get("longitude", 0.0)
    timezone_name = state.get("timezone_name", "UTC")

    logger.info(f"Reconciling schedule: {schedule_id}")

    # Load the schedule from storage
    from webui.backend.lib.schedule_storage import read_schedule

    schedule = read_schedule(schedule_id)
    if schedule is None:
        logger.error(f"Schedule not found in storage: {schedule_id}")
        return 1

    # Run reconciliation
    from webui.backend.lib.schedule_reconciler import (
        execute_reconciliation,
        reconcile_schedule,
    )

    try:
        actions = reconcile_schedule(schedule, latitude, longitude, timezone_name)
    except Exception as e:
        logger.error(f"Reconciliation computation failed: {e}")
        return 1

    if not actions:
        logger.info("No actions to reconcile")
        return 0

    logger.info(f"Executing {len(actions)} reconciled actions")
    results = execute_reconciliation(actions)

    failed = [r for r in results if not r["success"]]
    if failed:
        logger.warning(f"{len(failed)} actions failed: {failed}")
    else:
        logger.info("All reconciled actions executed successfully")

    return 0


if __name__ == "__main__":
    sys.exit(main())

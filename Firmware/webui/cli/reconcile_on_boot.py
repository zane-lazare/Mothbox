#!/usr/bin/env python3
"""Reconcile GPIO state after boot.

Called via @reboot cron entry. Waits for GPIO daemon socket,
loads active schedule from active_state.json, runs reconciler.

Usage: systemd-cat -t mothbox /usr/bin/python3 /path/to/reconcile_on_boot.py
"""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

from lib.gpio_protocol import SOCKET_PATH

log_level = os.environ.get("MOTHBOX_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO), format="%(levelname)s: %(message)s"
)
logger = logging.getLogger("reconcile_on_boot")

# GPIO daemon socket path (from shared protocol constants)
GPIO_SOCKET = Path(SOCKET_PATH)

# Backoff schedule: 0.5, 1, 2, 4, 8, 16, 32 seconds (~63.5s total)
BACKOFF_DELAYS = [0.5, 1, 2, 4, 8, 16, 32]

EXIT_SUCCESS = 0
EXIT_FATAL = 1
EXIT_PARTIAL = 2


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
    from webui.backend.lib.active_state import load_active_state as _load

    return _load()


def main() -> int:
    """Main entry point for boot reconciliation.

    Returns:
        EXIT_SUCCESS (0): Success (or no work to do)
        EXIT_FATAL (1): Fatal error (schedule not found, computation failed)
        EXIT_PARTIAL (2): Partial success (some actions failed, e.g. daemon unavailable)
    """
    logger.info("Starting boot GPIO reconciliation")

    # Wait for GPIO daemon
    daemon_ready = wait_for_gpio_daemon()
    if not daemon_ready:
        logger.warning("Proceeding without GPIO daemon — commands may fail")

    # Load active state
    state = load_active_state()
    if state is None:
        return EXIT_SUCCESS

    if not daemon_ready:
        logger.error("GPIO daemon unavailable — reconciliation actions will likely fail")

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

    logger.info(f"Reconciling schedule: {schedule_id}")

    # Load the schedule from storage
    from webui.backend.lib.schedule_storage import read_schedule

    schedule = read_schedule(schedule_id)
    if schedule is None:
        logger.error(f"Schedule not found in storage: {schedule_id}")
        return EXIT_FATAL

    # Run reconciliation
    from webui.backend.lib.schedule_reconciler import (
        execute_reconciliation,
        reconcile_schedule,
    )

    try:
        actions = reconcile_schedule(schedule, latitude, longitude, timezone_name)
    except (ValueError, TypeError) as e:
        logger.error(f"Reconciliation computation failed: {e}")
        return EXIT_FATAL

    if not actions:
        logger.info("No actions to reconcile")
        return EXIT_SUCCESS

    logger.info(f"Executing {len(actions)} reconciled actions")
    results = execute_reconciliation(actions)

    failed = [r for r in results if not r["success"]]
    if failed:
        logger.warning(f"{len(failed)} actions failed: {failed}")
        return EXIT_PARTIAL
    else:
        logger.info("All reconciled actions executed successfully")

    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())

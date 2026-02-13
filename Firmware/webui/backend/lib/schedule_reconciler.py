"""Schedule state reconciliation for GPIO catch-up.

When a schedule is activated after a solar trigger has already passed (e.g.,
activating an overnight survey after sunset), cron skips the past entries.
GPIO actions like turning on attract lamps never fire until the next day.

This module computes what GPIO state *should* be at the current time by
looking back through the schedule's trigger history, then executes the
most recent action for each GPIO resource.

Same logic handles Pi reboot recovery: GPIO resets on boot, so we
reconcile to restore the expected state.
"""

from __future__ import annotations

import logging
import shlex
import subprocess
from datetime import datetime, timedelta
from math import ceil
from typing import TypedDict

import pytz

from webui.backend.lib.cron_bridge import calculate_execution_times
from webui.backend.lib.cron_security import get_script_key_for_action, get_validated_command
from webui.backend.lib.schedule_schema import Schedule, SensorTrigger

logger = logging.getLogger(__name__)

# Actions that are safe to replay (idempotent GPIO toggles and GPS sync).
# Flash is included because the scheduled scripts (FlashOn.py/FlashOff.py) set
# sustained relay state, unlike the web UI flash endpoint which pulses momentarily.
RECONCILABLE_ACTIONS: set[str] = {
    "attract_on",
    "attract_off",
    "flash_on",
    "flash_off",
    "sync",  # gps_sync action uses action_name="sync"
}

# GPIO resource grouping: maps action names to their logical resource.
# gps_sync ("sync") is not included here because it has no on/off pairing —
# it's handled as a standalone resource in the grouping loop below.
_ACTION_RESOURCE: dict[str, str] = {
    "attract_on": "attract",
    "attract_off": "attract",
    "flash_on": "flash",
    "flash_off": "flash",
}


class ReconcileAction(TypedDict):
    action_type: str
    action_name: str
    source_time: datetime


class ReconcileResult(TypedDict):
    action_name: str
    success: bool
    error: str | None


# 48h covers two full solar cycles, ensuring we catch both "today's" and
# "yesterday's" triggers regardless of when reconciliation runs
LOOKBACK_HOURS: int = 48

# Timeout for reconciliation subprocess commands (seconds)
RECONCILE_TIMEOUT: int = 30


def reconcile_schedule(
    schedule: Schedule,
    latitude: float,
    longitude: float,
    timezone_name: str,
    now: datetime | None = None,
) -> list[ReconcileAction]:
    """Determine which GPIO/idempotent actions should be executed now.

    Looks back LOOKBACK_HOURS from ``now``, computes all trigger times for
    each routine, applies action offsets, then for each GPIO resource finds
    the most recent past action and returns it.

    Args:
        schedule: The active schedule to reconcile.
        latitude: Observer latitude for solar calculations.
        longitude: Observer longitude for solar calculations.
        timezone_name: IANA timezone name (e.g. "America/New_York").
        now: Current time. Must be timezone-aware. Defaults to now in
            the schedule's timezone.

    Returns:
        List of dicts with keys:
            - action_type (str): e.g. "gpio", "gps_sync"
            - action_name (str): e.g. "attract_on", "flash_off", "sync"
            - source_time (datetime): when this action should have fired
    """
    if now is None:
        try:
            tz = pytz.timezone(timezone_name)
        except pytz.exceptions.UnknownTimeZoneError as e:
            raise ValueError(f"Unknown timezone: {timezone_name!r}") from e
        now = datetime.now(tz)
    elif now.tzinfo is None:
        raise ValueError("now must be timezone-aware; got naive datetime")

    if not schedule.routines:
        return []

    lookback_start = now - timedelta(hours=LOOKBACK_HOURS)

    # Collect all (action_time, action_type, action_name) in the lookback window
    all_actions: list[tuple[datetime, str, str]] = []

    for routine in schedule.routines:
        # Skip sensor-only triggers (not schedulable)
        if isinstance(routine.trigger, SensorTrigger):
            continue

        try:
            # +1 day buffer ensures we capture all triggers in the lookback window
            # even when trigger times fall near end-of-day boundaries
            trigger_times = calculate_execution_times(
                trigger=routine.trigger,
                latitude=latitude,
                longitude=longitude,
                timezone_name=timezone_name,
                from_date=lookback_start.date(),
                days_ahead=ceil(LOOKBACK_HOURS / 24) + 1,
            )
        except (ValueError, TypeError) as e:
            logger.warning(f"Skipping routine {routine.routine_id} during reconciliation: {e}")
            continue

        for trigger_time in trigger_times:
            for action in routine.actions:
                if action.action_name not in RECONCILABLE_ACTIONS:
                    continue

                action_time = trigger_time + timedelta(minutes=action.offset_minutes)

                # Only past actions within the lookback window (strict upper bound)
                if lookback_start <= action_time < now:
                    all_actions.append((action_time, action.action_type, action.action_name))

    if not all_actions:
        return []

    # Group by resource, keep most recent per resource
    resource_latest: dict[str, tuple[datetime, str, str]] = {}

    for action_time, action_type, action_name in all_actions:
        if action_type == "gps_sync":
            # gps_sync is standalone — no on/off pairing
            resource_key = "gps_sync"
        else:
            resource_key = _ACTION_RESOURCE.get(action_name)
            if resource_key is None:
                continue

        existing = resource_latest.get(resource_key)
        if existing is None or action_time > existing[0]:
            resource_latest[resource_key] = (action_time, action_type, action_name)

    # Build result list
    results = []
    for _resource_key, (action_time, action_type, action_name) in resource_latest.items():
        results.append(
            {
                "action_type": action_type,
                "action_name": action_name,
                "source_time": action_time,
            }
        )

    return results


def execute_reconciliation(
    actions: list[ReconcileAction],
) -> list[ReconcileResult]:
    """Execute reconciled actions by running the corresponding scripts.

    Uses get_validated_command() from cron_security to get the safe command
    for each action. Runs via subprocess. Returns results list.

    Non-fatal: failures are logged but don't raise.

    Args:
        actions: List of action dicts from reconcile_schedule().

    Returns:
        List of result dicts with keys:
            - action_name (str)
            - success (bool)
            - error (str | None)
    """
    results = []

    for action in actions:
        action_type = action["action_type"]
        action_name = action["action_name"]

        script_key = get_script_key_for_action(action_type, action_name)
        if script_key is None:
            logger.warning(f"No script key for action {action_type}/{action_name}")
            results.append(
                {
                    "action_name": action_name,
                    "success": False,
                    "error": f"Unknown script key for {action_type}/{action_name}",
                }
            )
            continue

        try:
            command = get_validated_command(script_key)
        except ValueError as e:
            logger.warning(f"Invalid command for {script_key}: {e}")
            results.append({"action_name": action_name, "success": False, "error": str(e)})
            continue

        try:
            logger.info(f"Reconciling {action_name} (should have fired at {action['source_time']})")
            proc = subprocess.run(  # noqa: S603 - command from validated whitelist
                shlex.split(command),
                timeout=RECONCILE_TIMEOUT,
                check=False,
                capture_output=True,
            )
            if proc.returncode != 0:
                error_msg = (
                    proc.stderr.decode("utf-8", errors="replace").strip()
                    if proc.stderr
                    else f"exit code {proc.returncode}"
                )
                logger.warning(f"Reconciliation script failed: {action_name}: {error_msg}")
                results.append({"action_name": action_name, "success": False, "error": error_msg})
            else:
                results.append({"action_name": action_name, "success": True, "error": None})
        except subprocess.TimeoutExpired:
            error_msg = f"Command timed out after {RECONCILE_TIMEOUT}s"
            logger.warning(f"Reconciliation command timed out: {action_name}")
            results.append({"action_name": action_name, "success": False, "error": error_msg})
        except OSError as e:
            logger.warning(f"Reconciliation command failed: {action_name}: {e}")
            results.append({"action_name": action_name, "success": False, "error": str(e)})

    return results

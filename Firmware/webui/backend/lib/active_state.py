"""Shared helpers for reading active_state.json."""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)


def load_active_state() -> dict | None:
    """Load active_state.json from CONFIG_DIR with shared file lock.

    Returns the parsed dict, or None if no active state.
    """
    from mothbox_paths import CONFIG_DIR
    from webui.backend.lib.file_lock import FileLock

    state_file = CONFIG_DIR / "active_state.json"
    if not state_file.exists():
        logger.info("No active_state.json found")
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

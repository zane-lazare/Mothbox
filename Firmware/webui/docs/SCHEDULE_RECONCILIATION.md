# Schedule Reconciliation

> Related: [Scheduler User Guide](SCHEDULER_USER_GUIDE.md) | Issue #398

## Overview

When a Mothbox reboots or a schedule is activated after a trigger has already passed, GPIO state (attract lamps, flash) may not match what the schedule expects. For example, activating an overnight moth survey after sunset means the `attract_on` cron entry was missed — lamps stay off until the next evening.

**Schedule reconciliation** solves this by computing what GPIO state *should* be at the current time and executing the necessary catch-up actions.

---

## How It Works

### Boot Reconciliation (`reconcile_on_boot.py`)

Runs automatically via a `@reboot` cron entry installed when a schedule is activated.

1. Waits for the GPIO daemon socket (exponential backoff, ~63.5s timeout)
2. Loads the active schedule from `active_state.json`
3. Looks back 48 hours through the schedule's trigger history
4. For each GPIO resource (attract, flash), finds the most recent past action
5. Executes those actions to restore the expected state

### Weekly Cron Refresh (`refresh_schedule.py`)

Runs via `0 2 * * 0` (Sunday 2:00 AM) cron entry.

Solar, moon phase, and recurring-day triggers generate date-specific cron entries that expire after 60 days. The weekly refresh regenerates these entries so the schedule continues running indefinitely.

---

## What To Expect

### Normal Boot Sequence

After a reboot with an active schedule, you'll see messages like:

```
INFO: Starting boot GPIO reconciliation
INFO: GPIO daemon socket found
INFO: Reconciling schedule: summer-moth-survey
INFO: Executing 2 reconciled actions
INFO: Reconciling attract_on (should have fired at 2025-06-15 18:32:00-05:00)
INFO: Reconciling flash_on (should have fired at 2025-06-15 18:37:00-05:00)
INFO: All reconciled actions executed successfully
```

### No Actions Needed

If no triggers have fired in the past 48 hours (e.g., daytime reboot with a nighttime-only schedule):

```
INFO: Starting boot GPIO reconciliation
INFO: GPIO daemon socket found
INFO: Reconciling schedule: summer-moth-survey
INFO: No actions to reconcile
```

---

## Exit Codes

| Code | Meaning | Example |
|------|---------|---------|
| 0 | Success or no work to do | No active schedule, or all actions executed |
| 1 | Fatal error | Schedule not found, computation failed |
| 2 | Partial success (boot only) | Some GPIO actions failed (e.g., daemon unavailable) |

---

## Troubleshooting

### GPIO Daemon Unavailable

```
WARNING: GPIO daemon socket not found after timeout
WARNING: Proceeding without GPIO daemon — commands may fail
```

The GPIO daemon hasn't started within the ~63.5s timeout. Reconciliation proceeds but actions will likely fail (exit code 2). Check that the GPIO daemon service is enabled:

```bash
sudo systemctl status mothbox-gpio-daemon
sudo systemctl enable mothbox-gpio-daemon
```

### Schedule Not Found

```
ERROR: Schedule not found in storage: my-schedule-id
```

The schedule referenced in `active_state.json` no longer exists in storage. Re-activate a schedule from the web UI.

### Computation Failed

```
ERROR: Reconciliation computation failed: Invalid coordinates: ...
```

The stored coordinates are invalid. Re-activate the schedule with valid GPS coordinates, or ensure the Mothbox has a GPS fix.

### Viewing Logs

Boot reconciliation logs via systemd journal:

```bash
# Recent reconciliation logs
journalctl -t mothbox --since "1 hour ago"

# Follow live during boot
journalctl -t mothbox -f
```

### Adjusting Log Verbosity

Set the `MOTHBOX_LOG_LEVEL` environment variable to control log output:

```bash
# In crontab or systemd service override
MOTHBOX_LOG_LEVEL=DEBUG systemd-cat -t mothbox /usr/bin/python3 /path/to/reconcile_on_boot.py
```

Valid levels: `DEBUG`, `INFO` (default), `WARNING`, `ERROR`.

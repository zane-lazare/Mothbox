# GPS Auto-Update Design (Issue #382)

## Problem

When a schedule is activated without a GPS fix, the system falls back to timezone-based approximate coordinates for solar trigger calculations (sunrise/sunset). If GPS acquires a fix later, the schedule continues using stale coordinates — solar times may be off by minutes to hours depending on how far the device is from the timezone's reference longitude.

## Solution

Auto-detect GPS availability after timezone-based activation, update coordinates, and regenerate cron entries. Show the transition in the UI with minimal visual cues.

## Scope

- Scheduler service GPS polling and cron regeneration
- ActiveScheduleBanner and ActivationPanel UI updates
- **Out of scope**: Deployment sidecar sync (deferred — `create_deployment` activation flow doesn't exist yet)

## Architecture

### Three Independent Coordinate Systems (unchanged)

1. **Scheduler** — coordinates for solar trigger math, stored in `active_state.json`
2. **Deployment** — `deployment.json` location metadata for photo collections
3. **Photo EXIF** — `gps_exif_tagger.py` reads `controls.txt` live per-photo

This feature only touches system 1 (scheduler). Systems 2 and 3 already handle GPS updates independently.

---

## Backend

### GPS Polling in SchedulerService

New method `check_and_update_gps()` on `SchedulerService`:

- **Guard**: Only runs when `_active_coordinates_source == "timezone"`. No-op for `"gps"` or `"explicit"`.
- **Read**: Gets `lat`/`lon` from `controls.txt` via `get_control_values()`.
- **Validate**: Checks values are numeric and not `"n/a"`.
- **Update**: Sets `_active_latitude`, `_active_longitude`, `_active_coordinates_source = "gps"`.
- **Regenerate**: Calls `schedule_to_cron()` with new coordinates, then `apply_to_system()`.
- **Persist**: Writes updated state to `active_state.json`.
- **Return**: `{"updated": True, "latitude": ..., "longitude": ...}` or `{"updated": False}`.

### Polling Mechanism

A `threading.Timer` loop inside the service:

- **Start**: When a schedule is activated with `coordinates_source == "timezone"`.
- **Interval**: 60 seconds.
- **Stop conditions**: GPS acquired (one-shot success), schedule deactivated, or source already GPS/explicit.
- **Thread safety**: Uses existing `_activation_lock`.
- **Cleanup**: Timer cancelled on deactivation and service shutdown.

### API

No new endpoints. The existing `GET /api/scheduler/active` response already includes `coordinates_source`, `latitude`, `longitude`. The frontend detects transitions by polling this endpoint (already happens via `useActiveSchedule` with `refetchInterval`).

---

## Frontend

### ActiveScheduleBanner — Coordinate States

Three visual states based on `coordinates_source`:

1. **`"timezone"` (searching)**: Amber warning with subtle pulsing icon.
   - Icon: `SignalSlashIcon` (amber, CSS pulse animation)
   - Text: "Approximate location from timezone. Waiting for GPS..."
   - Pulse is subtle — icon only, not text.

2. **`"gps"` (nominal)**: Green, compact.
   - Icon: `SignalIcon` (green)
   - Text: "GPS: lat, lon"

3. **Transition (`timezone` -> `gps`)**: Toast notification.
   - `react-hot-toast`: "GPS fix acquired — solar times updated"
   - Banner re-renders from amber to green.
   - Uses `useRef` to track previous `coordinates_source` and detect change.

No new hooks or API calls — reacts to changes in existing polled `useActiveSchedule()` data.

### ActivationPanel — Coordinate Source Stat

One new row in the stats grid:

- `"timezone"`: small amber dot + "Approx. location"
- `"gps"`: small green dot + "GPS"
- `"explicit"`: small blue dot + "Manual"
- Uses existing muted text style (`text-xs text-gray-500`)

---

## Testing

### Backend (pytest)

- `test_scheduler_service_gps_polling.py`:
  - GPS check no-op when source is `"gps"` or `"explicit"`
  - GPS check updates coordinates when `controls.txt` has valid GPS
  - GPS check no-op when `controls.txt` still has `"n/a"`
  - Cron entries regenerated with new coordinates after GPS update
  - `active_state.json` persisted after update
  - Timer starts on timezone-based activation
  - Timer stops after GPS acquired
  - Timer stops on deactivation
  - Thread safety with concurrent activation/GPS check

### Frontend (vitest)

- `ActiveScheduleBanner.test.jsx`:
  - Renders amber state for timezone source with pulse class
  - Renders green state for GPS source without pulse
  - Toast fires on timezone->GPS transition
  - No toast on initial GPS render
- `ActivationPanel.test.jsx`:
  - Renders coordinate source stat for each source type

### Not tested

- E2E (requires real GPS hardware state changes)

---

## Follow-up Issues

- **Deployment sync**: When `create_deployment` activation flow is implemented, propagate GPS coordinate updates to auto-created `deployment.json`.
- **GPS quality indicator**: Could show satellite count or fix quality from `controls.txt` `gps_fix_mode` field.

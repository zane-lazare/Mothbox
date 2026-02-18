# GPS Auto-Update Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Auto-detect GPS availability after timezone-based schedule activation, update coordinates, regenerate cron entries, and show the transition in the UI.

**Architecture:** Add a `check_and_update_gps()` method and 60-second `threading.Timer` loop to `SchedulerService`. The timer starts when activation uses timezone fallback and stops once GPS is acquired or the schedule is deactivated. Frontend detects the `coordinates_source` change via existing polling and fires a toast notification.

**Tech Stack:** Python 3 (threading, pytest), React 18 (useRef, react-hot-toast), Tailwind CSS (animate-pulse), Heroicons (SignalIcon, SignalSlashIcon), Vitest + @testing-library/react

---

### Task 1: Add `check_and_update_gps()` method to SchedulerService

**Files:**
- Modify: `webui/backend/services/scheduler_service.py:917-948` (after `get_active_timezone_name`)
- Create: `Tests/unit/test_scheduler_service_gps_polling.py`

**Step 1: Write the failing tests**

Create `Tests/unit/test_scheduler_service_gps_polling.py`:

```python
"""
Unit tests for GPS auto-update in SchedulerService (Issue #382).

Tests the check_and_update_gps() method that detects GPS availability
after timezone-based activation and updates coordinates + cron entries.
"""

import json

import pytest

try:
    from webui.backend.lib.schedule_schema import (
        Action,
        IntervalTrigger,
        Routine,
        Schedule,
        TimeWindow,
    )
    from webui.backend.services.scheduler_service import SchedulerService

    IMPLEMENTATION_EXISTS = True
except ImportError:
    IMPLEMENTATION_EXISTS = False
    SchedulerService = None
    Schedule = None

pytestmark = pytest.mark.skipif(
    not IMPLEMENTATION_EXISTS, reason="Implementation not yet created"
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_schedules_dir(tmp_path, monkeypatch):
    """Create temp directory and mock SCHEDULES_DIR and ACTIVE_STATE_FILE."""
    schedules = tmp_path / "schedules"
    schedules.mkdir()
    monkeypatch.setattr("mothbox_paths.SCHEDULES_DIR", schedules)
    monkeypatch.setattr("webui.backend.lib.schedule_storage.SCHEDULES_DIR", schedules)
    active_state_file = tmp_path / "active_state.json"
    monkeypatch.setattr(
        "webui.backend.services.scheduler_service.ACTIVE_STATE_FILE", active_state_file
    )
    # Mock CONTROLS_FILE for GPS reads
    controls_file = tmp_path / "controls.txt"
    controls_file.write_text("lat=n/a\nlon=n/a\n")
    monkeypatch.setattr("mothbox_paths.CONTROLS_FILE", controls_file)
    return tmp_path


@pytest.fixture
def sample_schedule():
    """Create a valid Schedule object for testing."""
    actions = [
        Action(action_type="camera", action_name="takephoto", offset_minutes=0),
    ]
    time_window = TimeWindow(start_time="21:00", end_time="05:00")
    trigger = IntervalTrigger(interval_minutes=60, time_window=time_window)
    routine = Routine(
        routine_id="test-routine-1",
        name="Test Routine",
        trigger=trigger,
        actions=actions,
    )
    return Schedule(
        schedule_id="test-schedule-1",
        name="Test Schedule",
        routines=[routine],
        enabled=True,
    )


@pytest.fixture
def service(temp_schedules_dir):
    """Create a fresh SchedulerService for each test."""
    return SchedulerService(cache_ttl=300, max_cache_size=100)


# ============================================================================
# check_and_update_gps() Tests
# ============================================================================


class TestCheckAndUpdateGps:
    """Tests for the check_and_update_gps method."""

    def test_noop_when_source_is_gps(self, service):
        """Should return updated=False when coordinates already from GPS."""
        service._active_coordinates_source = "gps"
        service._active_schedule_id = "test-1"

        result = service.check_and_update_gps()

        assert result["updated"] is False

    def test_noop_when_source_is_explicit(self, service):
        """Should return updated=False when coordinates explicitly provided."""
        service._active_coordinates_source = "explicit"
        service._active_schedule_id = "test-1"

        result = service.check_and_update_gps()

        assert result["updated"] is False

    def test_noop_when_no_active_schedule(self, service):
        """Should return updated=False when no schedule is active."""
        service._active_schedule_id = None
        service._active_coordinates_source = None

        result = service.check_and_update_gps()

        assert result["updated"] is False

    def test_noop_when_gps_still_unavailable(self, service, temp_schedules_dir):
        """Should return updated=False when controls.txt still has n/a."""
        service._active_coordinates_source = "timezone"
        service._active_schedule_id = "test-1"
        # controls.txt already has lat=n/a, lon=n/a from fixture

        result = service.check_and_update_gps()

        assert result["updated"] is False
        assert service._active_coordinates_source == "timezone"

    def test_updates_when_gps_available(
        self, service, temp_schedules_dir, sample_schedule, monkeypatch
    ):
        """Should update coordinates and return updated=True when GPS available."""
        # Write GPS coordinates to controls.txt
        controls_file = temp_schedules_dir / "controls.txt"
        controls_file.write_text("lat=-41.2865\nlon=174.7762\n")

        # Set up active schedule with timezone source
        from webui.backend.lib.schedule_storage import create_schedule

        create_schedule(sample_schedule)
        service.set_enabled_schedule(sample_schedule.schedule_id)
        service._active_schedule_id = sample_schedule.schedule_id
        service._active_coordinates_source = "timezone"
        service._active_latitude = 0.0
        service._active_longitude = 0.0
        service._active_timezone_name = "Pacific/Auckland"

        # Mock cron bridge to avoid system cron changes
        monkeypatch.setattr(
            "webui.backend.services.scheduler_service.apply_to_system",
            lambda **kwargs: None,
        )

        result = service.check_and_update_gps()

        assert result["updated"] is True
        assert result["latitude"] == pytest.approx(-41.2865)
        assert result["longitude"] == pytest.approx(174.7762)
        assert result["previous_source"] == "timezone"
        assert service._active_coordinates_source == "gps"
        assert service._active_latitude == pytest.approx(-41.2865)
        assert service._active_longitude == pytest.approx(174.7762)

    def test_persists_state_after_update(
        self, service, temp_schedules_dir, sample_schedule, monkeypatch
    ):
        """Should write updated coordinates to active_state.json."""
        controls_file = temp_schedules_dir / "controls.txt"
        controls_file.write_text("lat=-41.2865\nlon=174.7762\n")

        from webui.backend.lib.schedule_storage import create_schedule

        create_schedule(sample_schedule)
        service.set_enabled_schedule(sample_schedule.schedule_id)
        service._active_schedule_id = sample_schedule.schedule_id
        service._active_coordinates_source = "timezone"
        service._active_latitude = 0.0
        service._active_longitude = 0.0
        service._active_timezone_name = "Pacific/Auckland"

        monkeypatch.setattr(
            "webui.backend.services.scheduler_service.apply_to_system",
            lambda **kwargs: None,
        )

        service.check_and_update_gps()

        # Verify active_state.json was updated
        state_file = temp_schedules_dir / "active_state.json"
        assert state_file.exists()
        state = json.loads(state_file.read_text())
        assert state["coordinates_source"] == "gps"
        assert state["latitude"] == pytest.approx(-41.2865)
        assert state["longitude"] == pytest.approx(174.7762)

    def test_ignores_invalid_gps_values(self, service, temp_schedules_dir):
        """Should return updated=False when controls.txt has non-numeric GPS."""
        controls_file = temp_schedules_dir / "controls.txt"
        controls_file.write_text("lat=invalid\nlon=bad\n")

        service._active_coordinates_source = "timezone"
        service._active_schedule_id = "test-1"

        result = service.check_and_update_gps()

        assert result["updated"] is False
        assert service._active_coordinates_source == "timezone"

    def test_regenerates_cron_entries(
        self, service, temp_schedules_dir, sample_schedule, monkeypatch
    ):
        """Should call schedule_to_cron and apply_to_system with new coords."""
        controls_file = temp_schedules_dir / "controls.txt"
        controls_file.write_text("lat=-41.2865\nlon=174.7762\n")

        from webui.backend.lib.schedule_storage import create_schedule

        create_schedule(sample_schedule)
        service.set_enabled_schedule(sample_schedule.schedule_id)
        service._active_schedule_id = sample_schedule.schedule_id
        service._active_coordinates_source = "timezone"
        service._active_latitude = 0.0
        service._active_longitude = 0.0
        service._active_timezone_name = "Pacific/Auckland"

        apply_calls = []
        monkeypatch.setattr(
            "webui.backend.services.scheduler_service.apply_to_system",
            lambda **kwargs: apply_calls.append(kwargs),
        )

        service.check_and_update_gps()

        assert len(apply_calls) == 1
        assert apply_calls[0]["schedule_id"] == sample_schedule.schedule_id
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/zane/projects/Mothbox/Firmware && python3 -m pytest Tests/unit/test_scheduler_service_gps_polling.py -v`
Expected: FAIL with `AttributeError: 'SchedulerService' object has no attribute 'check_and_update_gps'`

**Step 3: Implement `check_and_update_gps()`**

In `webui/backend/services/scheduler_service.py`, add a new import at the top (after line 43):

```python
from mothbox_paths import CONFIG_DIR, CONTROLS_FILE, get_control_values
```

Then add this method after `get_active_timezone_name()` (after line 948):

```python
    def check_and_update_gps(self) -> dict:
        """
        Check if GPS coordinates are available and update active schedule if needed (Issue #382).

        Only runs when the active schedule is using timezone-based coordinates.
        When GPS becomes available, updates coordinates, regenerates cron entries,
        and persists the new state.

        Returns:
            dict with "updated" (bool), and if updated: "latitude", "longitude",
            "previous_source" keys.
        """
        # Guard: only act when source is "timezone" and a schedule is active
        if self._active_coordinates_source != "timezone" or not self._active_schedule_id:
            return {"updated": False}

        # Read GPS from controls.txt
        control_values = get_control_values(CONTROLS_FILE)
        device_lat = control_values.get("lat", "n/a")
        device_lon = control_values.get("lon", "n/a")

        # Check if GPS is available (not "n/a" and numeric)
        if device_lat == "n/a" or device_lon == "n/a":
            return {"updated": False}

        try:
            latitude = float(device_lat)
            longitude = float(device_lon)
        except (ValueError, TypeError):
            return {"updated": False}

        # Validate coordinate ranges
        if latitude < -90 or latitude > 90 or longitude < -180 or longitude > 180:
            logger.warning(f"GPS coordinates out of range: {latitude}, {longitude}")
            return {"updated": False}

        # GPS available — update coordinates and regenerate cron
        with self._activation_lock:
            # Re-check source under lock (may have changed)
            if self._active_coordinates_source != "timezone":
                return {"updated": False}

            schedule_id = self._active_schedule_id
            timezone_name = self._active_timezone_name or "UTC"

            # Get the schedule for cron regeneration
            schedule = self.get_schedule(schedule_id)
            if not schedule:
                logger.error(f"GPS update: schedule not found: {schedule_id}")
                return {"updated": False}

            try:
                # Regenerate cron with new coordinates
                result = schedule_to_cron(
                    schedule,
                    latitude=latitude,
                    longitude=longitude,
                    timezone_name=timezone_name,
                )
                if result.errors:
                    logger.error(f"GPS update: cron conversion failed: {result.errors}")
                    return {"updated": False}

                # Apply new cron entries to system
                apply_to_system(
                    entries=result.entries,
                    schedule_id=schedule_id,
                    set_rtc=True,
                )

                # Expand entries for frontend
                expanded_entries = expand_pattern_entries(
                    entries=result.entries,
                    days_ahead=CRON_PREVIEW_DAYS_AHEAD,
                    timezone_name=timezone_name,
                )

                # Update in-memory state
                previous_source = self._active_coordinates_source
                with self._cache_lock:
                    self._active_coordinates_source = "gps"
                    self._active_latitude = latitude
                    self._active_longitude = longitude

                # Persist to disk
                self._save_active_state(entries=expanded_entries)

                logger.info(
                    f"GPS auto-update: coordinates updated from {previous_source} to GPS "
                    f"for schedule {schedule_id}"
                )

                return {
                    "updated": True,
                    "latitude": latitude,
                    "longitude": longitude,
                    "previous_source": previous_source,
                }

            except Exception as e:
                logger.error(f"GPS auto-update failed: {e}")
                return {"updated": False}
```

Note: `CONTROLS_FILE` is already importable from `mothbox_paths`. Check the existing import on line 43 — it currently imports `CONFIG_DIR`. Change line 43 to:

```python
from mothbox_paths import CONFIG_DIR, CONTROLS_FILE, get_control_values
```

**Step 4: Run tests to verify they pass**

Run: `cd /home/zane/projects/Mothbox/Firmware && python3 -m pytest Tests/unit/test_scheduler_service_gps_polling.py -v`
Expected: All 8 tests PASS

**Step 5: Run existing scheduler service tests to verify no regressions**

Run: `cd /home/zane/projects/Mothbox/Firmware && python3 -m pytest Tests/unit/test_scheduler_service.py -v`
Expected: All existing tests PASS

**Step 6: Commit**

```bash
git add Tests/unit/test_scheduler_service_gps_polling.py \
       webui/backend/services/scheduler_service.py
git commit -m "feat: add check_and_update_gps to SchedulerService (#382)"
```

---

### Task 2: Add GPS polling timer to SchedulerService

**Files:**
- Modify: `webui/backend/services/scheduler_service.py` (init, activate, deactivate, new start/stop methods)
- Modify: `Tests/unit/test_scheduler_service_gps_polling.py`

**Step 1: Write the failing tests**

Add to `Tests/unit/test_scheduler_service_gps_polling.py`:

```python
import threading
import time


class TestGpsPollingTimer:
    """Tests for the GPS polling timer lifecycle."""

    def test_timer_starts_on_timezone_activation(
        self, service, temp_schedules_dir, sample_schedule, monkeypatch
    ):
        """Timer should start when schedule activated with timezone source."""
        from webui.backend.lib.schedule_storage import create_schedule

        create_schedule(sample_schedule)
        service.set_enabled_schedule(sample_schedule.schedule_id)

        # Mock cron bridge
        monkeypatch.setattr(
            "webui.backend.services.scheduler_service.apply_to_system",
            lambda **kwargs: None,
        )
        monkeypatch.setattr(
            "webui.backend.services.scheduler_service.schedule_to_cron",
            lambda *args, **kwargs: type("R", (), {"entries": [], "errors": []})(),
        )
        monkeypatch.setattr(
            "webui.backend.services.scheduler_service.expand_pattern_entries",
            lambda **kwargs: [],
        )

        service.activate_schedule(
            schedule_id=sample_schedule.schedule_id,
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
            coordinates_source="timezone",
        )

        assert service._gps_poll_timer is not None
        # Clean up
        service.stop_gps_polling()

    def test_timer_does_not_start_on_gps_activation(
        self, service, temp_schedules_dir, sample_schedule, monkeypatch
    ):
        """Timer should NOT start when schedule activated with GPS source."""
        from webui.backend.lib.schedule_storage import create_schedule

        create_schedule(sample_schedule)
        service.set_enabled_schedule(sample_schedule.schedule_id)

        monkeypatch.setattr(
            "webui.backend.services.scheduler_service.apply_to_system",
            lambda **kwargs: None,
        )
        monkeypatch.setattr(
            "webui.backend.services.scheduler_service.schedule_to_cron",
            lambda *args, **kwargs: type("R", (), {"entries": [], "errors": []})(),
        )
        monkeypatch.setattr(
            "webui.backend.services.scheduler_service.expand_pattern_entries",
            lambda **kwargs: [],
        )

        service.activate_schedule(
            schedule_id=sample_schedule.schedule_id,
            latitude=-41.0,
            longitude=174.0,
            timezone_name="Pacific/Auckland",
            coordinates_source="gps",
        )

        assert service._gps_poll_timer is None

    def test_timer_stops_on_deactivation(
        self, service, temp_schedules_dir, sample_schedule, monkeypatch
    ):
        """Timer should stop when schedule is deactivated."""
        from webui.backend.lib.schedule_storage import create_schedule

        create_schedule(sample_schedule)
        service.set_enabled_schedule(sample_schedule.schedule_id)

        monkeypatch.setattr(
            "webui.backend.services.scheduler_service.apply_to_system",
            lambda **kwargs: None,
        )
        monkeypatch.setattr(
            "webui.backend.services.scheduler_service.schedule_to_cron",
            lambda *args, **kwargs: type("R", (), {"entries": [], "errors": []})(),
        )
        monkeypatch.setattr(
            "webui.backend.services.scheduler_service.expand_pattern_entries",
            lambda **kwargs: [],
        )
        monkeypatch.setattr(
            "webui.backend.services.scheduler_service.remove_from_system",
            lambda **kwargs: None,
        )

        service.activate_schedule(
            schedule_id=sample_schedule.schedule_id,
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
            coordinates_source="timezone",
        )
        assert service._gps_poll_timer is not None

        service.deactivate_schedule()
        assert service._gps_poll_timer is None

    def test_timer_stops_after_gps_acquired(
        self, service, temp_schedules_dir, sample_schedule, monkeypatch
    ):
        """Timer should stop after GPS coordinates are successfully acquired."""
        controls_file = temp_schedules_dir / "controls.txt"
        controls_file.write_text("lat=-41.2865\nlon=174.7762\n")

        from webui.backend.lib.schedule_storage import create_schedule

        create_schedule(sample_schedule)
        service.set_enabled_schedule(sample_schedule.schedule_id)
        service._active_schedule_id = sample_schedule.schedule_id
        service._active_coordinates_source = "timezone"
        service._active_latitude = 0.0
        service._active_longitude = 0.0
        service._active_timezone_name = "Pacific/Auckland"

        monkeypatch.setattr(
            "webui.backend.services.scheduler_service.apply_to_system",
            lambda **kwargs: None,
        )

        # Simulate timer firing by calling _gps_poll_tick directly
        service._gps_poll_tick()

        # Timer should be None after successful GPS acquisition
        assert service._gps_poll_timer is None

    def test_stop_gps_polling_is_safe_when_no_timer(self, service):
        """stop_gps_polling should be safe to call when no timer exists."""
        service._gps_poll_timer = None
        service.stop_gps_polling()  # Should not raise
        assert service._gps_poll_timer is None
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/zane/projects/Mothbox/Firmware && python3 -m pytest Tests/unit/test_scheduler_service_gps_polling.py::TestGpsPollingTimer -v`
Expected: FAIL with `AttributeError: 'SchedulerService' object has no attribute '_gps_poll_timer'`

**Step 3: Implement the timer**

In `webui/backend/services/scheduler_service.py`:

1. Add to `__init__` (after `self._activation_lock = RLock()` around line 219):

```python
        # GPS polling timer (Issue #382)
        # Starts when schedule is activated with timezone-based coordinates.
        # Polls controls.txt every 60s for GPS fix, then stops.
        self._gps_poll_timer: threading.Timer | None = None
```

Add `import threading` — it's not imported yet. Add at the top of the file (after `from threading import RLock` on line 41):

Actually, `threading` is partially imported. `RLock` comes from `from threading import RLock`. We need `threading.Timer`, so change line 41 from:

```python
from threading import RLock
```

to:

```python
import threading
from threading import RLock
```

2. Add `start_gps_polling()`, `stop_gps_polling()`, and `_gps_poll_tick()` methods after `check_and_update_gps()`:

```python
    # GPS polling interval in seconds (Issue #382)
    GPS_POLL_INTERVAL = 60

    def start_gps_polling(self) -> None:
        """
        Start periodic GPS polling (Issue #382).

        Schedules _gps_poll_tick to run every GPS_POLL_INTERVAL seconds.
        Only starts if coordinates_source is "timezone".
        """
        self.stop_gps_polling()  # Cancel any existing timer
        if self._active_coordinates_source != "timezone":
            return
        self._gps_poll_timer = threading.Timer(self.GPS_POLL_INTERVAL, self._gps_poll_tick)
        self._gps_poll_timer.daemon = True
        self._gps_poll_timer.start()
        logger.debug("GPS polling started")

    def stop_gps_polling(self) -> None:
        """
        Stop GPS polling timer (Issue #382).

        Safe to call even when no timer is running.
        """
        if self._gps_poll_timer is not None:
            self._gps_poll_timer.cancel()
            self._gps_poll_timer = None
            logger.debug("GPS polling stopped")

    def _gps_poll_tick(self) -> None:
        """
        Single GPS poll tick (Issue #382).

        Called by the timer. Checks GPS, and if not yet acquired,
        reschedules itself. If acquired, stops polling.
        """
        self._gps_poll_timer = None  # Timer has fired, clear reference

        result = self.check_and_update_gps()
        if result["updated"]:
            logger.info("GPS acquired — polling stopped")
            # Timer stays None (stopped)
        else:
            # GPS not yet available, schedule next check
            self.start_gps_polling()
```

3. In `activate_schedule()`, after the `_emit_progress(ACTIVATION_PHASE_COMPLETE, ...)` line (around line 1259), add:

```python
            # Start GPS polling if using timezone fallback (Issue #382)
            self.start_gps_polling()
```

4. In `deactivate_schedule()`, add at the start of the `with self._activation_lock:` block (after line 1279):

```python
            # Stop GPS polling (Issue #382)
            self.stop_gps_polling()
```

**Step 4: Run tests to verify they pass**

Run: `cd /home/zane/projects/Mothbox/Firmware && python3 -m pytest Tests/unit/test_scheduler_service_gps_polling.py -v`
Expected: All 13 tests PASS

**Step 5: Run existing scheduler service tests**

Run: `cd /home/zane/projects/Mothbox/Firmware && python3 -m pytest Tests/unit/test_scheduler_service.py -v`
Expected: All existing tests PASS

**Step 6: Commit**

```bash
git add webui/backend/services/scheduler_service.py \
       Tests/unit/test_scheduler_service_gps_polling.py
git commit -m "feat: add GPS polling timer to SchedulerService (#382)"
```

---

### Task 3: Redesign ActiveScheduleBanner coordinate display

**Files:**
- Modify: `webui/frontend/src/components/scheduler/ActiveScheduleBanner.jsx`
- Modify: `webui/frontend/src/components/scheduler/__tests__/ActiveScheduleBanner.test.jsx`

**Step 1: Write the failing tests**

Add to the end of `ActiveScheduleBanner.test.jsx` (inside the `describe('ActiveScheduleBanner')` block):

```jsx
  describe('GPS coordinate states (Issue #382)', () => {
    it('shows pulsing amber icon when coordinates source is timezone', () => {
      useActiveSchedule.mockReturnValue({
        data: {
          active_schedule: { id: 'sched-1', name: 'Test' },
          coordinates_source: 'timezone',
          timezone_name: 'Pacific/Auckland',
        },
        isLoading: false,
      })

      const { container } = render(<ActiveScheduleBanner />)

      const pulsingIcon = container.querySelector('.animate-pulse')
      expect(pulsingIcon).toBeInTheDocument()
      expect(screen.getByTestId('location-info')).toHaveTextContent(
        /Approximate location.*Waiting for GPS/
      )
    })

    it('shows green GPS icon when coordinates source is gps', () => {
      useActiveSchedule.mockReturnValue({
        data: {
          active_schedule: { id: 'sched-1', name: 'Test' },
          coordinates_source: 'gps',
          latitude: -41.287,
          longitude: 174.776,
        },
        isLoading: false,
      })

      const { container } = render(<ActiveScheduleBanner />)

      const pulsingIcon = container.querySelector('.animate-pulse')
      expect(pulsingIcon).not.toBeInTheDocument()
      expect(screen.getByTestId('location-info')).toHaveTextContent(/GPS/)
      expect(screen.getByTestId('location-info')).toHaveTextContent(/-41\.287/)
    })

    it('does not show pulse when coordinates source is explicit', () => {
      useActiveSchedule.mockReturnValue({
        data: {
          active_schedule: { id: 'sched-1', name: 'Test' },
          coordinates_source: 'explicit',
          latitude: -41.287,
          longitude: 174.776,
        },
        isLoading: false,
      })

      const { container } = render(<ActiveScheduleBanner />)

      const pulsingIcon = container.querySelector('.animate-pulse')
      expect(pulsingIcon).not.toBeInTheDocument()
    })

    it('does not show timezone warning when source is gps', () => {
      useActiveSchedule.mockReturnValue({
        data: {
          active_schedule: { id: 'sched-1', name: 'Test' },
          coordinates_source: 'gps',
          latitude: -41.287,
          longitude: 174.776,
        },
        isLoading: false,
      })

      render(<ActiveScheduleBanner />)

      expect(screen.queryByTestId('timezone-warning')).not.toBeInTheDocument()
    })
  })
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx vitest run src/components/scheduler/__tests__/ActiveScheduleBanner.test.jsx`
Expected: New tests FAIL (current code doesn't render pulse class or match new text patterns)

**Step 3: Implement the coordinate display redesign**

In `ActiveScheduleBanner.jsx`:

1. Add imports at the top (line 4, extend existing import):

Change line 4 from:
```jsx
import { CheckCircleIcon, ExclamationTriangleIcon, PlayIcon, InformationCircleIcon } from '@heroicons/react/24/solid'
```
to:
```jsx
import { CheckCircleIcon, ExclamationTriangleIcon, PlayIcon, InformationCircleIcon, SignalIcon, SignalSlashIcon } from '@heroicons/react/24/solid'
```

2. Replace the coordinate display section (lines 150-172) with:

```jsx
          {/* Coordinate source display (Issue #382) */}
          {coordinatesSource === 'timezone' && (
            <span data-testid="location-info" className="flex items-center gap-1 text-amber-700">
              <SignalSlashIcon className="h-4 w-4 animate-pulse" />
              Approximate location from timezone. Waiting for GPS...
            </span>
          )}
          {coordinatesSource === 'gps' && (
            <span data-testid="location-info" className="flex items-center gap-1 text-green-700">
              <SignalIcon className="h-4 w-4" />
              GPS: {latitude?.toFixed(3)}, {longitude?.toFixed(3)}
            </span>
          )}
          {coordinatesSource === 'explicit' && (
            <span data-testid="location-info" className="flex items-center gap-1">
              {latitude?.toFixed(3)}, {longitude?.toFixed(3)}
            </span>
          )}
```

3. Remove the old timezone warning block (the `{coordinatesSource === 'timezone' && (` block with `data-testid="timezone-warning"`, lines 160-172). The amber pulsing icon + text replaces the separate warning box.

**Step 4: Run tests to verify they pass**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx vitest run src/components/scheduler/__tests__/ActiveScheduleBanner.test.jsx`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add webui/frontend/src/components/scheduler/ActiveScheduleBanner.jsx \
       webui/frontend/src/components/scheduler/__tests__/ActiveScheduleBanner.test.jsx
git commit -m "feat: redesign ActiveScheduleBanner coordinate display (#382)"
```

---

### Task 4: Add GPS transition toast notification

**Files:**
- Modify: `webui/frontend/src/components/scheduler/ActiveScheduleBanner.jsx`
- Modify: `webui/frontend/src/components/scheduler/__tests__/ActiveScheduleBanner.test.jsx`

**Step 1: Write the failing tests**

Add to the GPS coordinate states describe block in `ActiveScheduleBanner.test.jsx`:

```jsx
    it('fires toast when coordinates source transitions from timezone to gps', () => {
      const toastSpy = vi.spyOn(toast, 'success')

      const { rerender } = render(<ActiveScheduleBanner />)

      // Initially timezone
      useActiveSchedule.mockReturnValue({
        data: {
          active_schedule: { id: 'sched-1', name: 'Test' },
          coordinates_source: 'timezone',
          timezone_name: 'Pacific/Auckland',
        },
        isLoading: false,
      })
      rerender(<ActiveScheduleBanner />)

      // Transition to GPS
      useActiveSchedule.mockReturnValue({
        data: {
          active_schedule: { id: 'sched-1', name: 'Test' },
          coordinates_source: 'gps',
          latitude: -41.287,
          longitude: 174.776,
        },
        isLoading: false,
      })
      rerender(<ActiveScheduleBanner />)

      expect(toastSpy).toHaveBeenCalledWith('GPS fix acquired — solar times updated')
      toastSpy.mockRestore()
    })

    it('does not fire toast on initial gps render', () => {
      const toastSpy = vi.spyOn(toast, 'success')

      useActiveSchedule.mockReturnValue({
        data: {
          active_schedule: { id: 'sched-1', name: 'Test' },
          coordinates_source: 'gps',
          latitude: -41.287,
          longitude: 174.776,
        },
        isLoading: false,
      })

      render(<ActiveScheduleBanner />)

      expect(toastSpy).not.toHaveBeenCalled()
      toastSpy.mockRestore()
    })
```

Also add the `toast` import to the test file (after line 3):

```jsx
import toast from 'react-hot-toast'
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx vitest run src/components/scheduler/__tests__/ActiveScheduleBanner.test.jsx`
Expected: New toast tests FAIL

**Step 3: Implement the transition detection**

In `ActiveScheduleBanner.jsx`:

1. Add `useRef` and `useEffect` to the React import (line 1):

Change:
```jsx
import { useState } from 'react'
```
to:
```jsx
import { useState, useRef, useEffect } from 'react'
```

2. Inside the `ActiveScheduleBanner` function, after the `const activeSchedule = data?.active_schedule` line (after line 59), add:

```jsx
  // Track previous coordinates source for transition detection (Issue #382)
  const prevCoordinatesSourceRef = useRef(data?.coordinates_source)
  useEffect(() => {
    const currentSource = data?.coordinates_source
    const prevSource = prevCoordinatesSourceRef.current
    if (prevSource === 'timezone' && currentSource === 'gps') {
      toast.success('GPS fix acquired — solar times updated')
    }
    prevCoordinatesSourceRef.current = currentSource
  }, [data?.coordinates_source])
```

3. The banner also needs `useActiveSchedule` to poll more frequently when source is timezone. Update the `useActiveSchedule` call (line 50):

Change:
```jsx
  const { data } = useActiveSchedule()
```
to:
```jsx
  const coordinatesSource = data?.coordinates_source
  const { data } = useActiveSchedule({
    refetchInterval: coordinatesSource === 'timezone' ? 30 * 1000 : undefined,
  })
```

Wait — this creates a circular reference since `data` is used to derive `coordinatesSource` which feeds back into `useActiveSchedule`. We need a different approach. Use a separate state or just pass the refetchInterval based on the last known source.

Simpler approach — always refetch every 60s when an active schedule exists (the nextActions already refetches every 60s anyway):

```jsx
  const { data } = useActiveSchedule({
    refetchInterval: activeSchedule ? 60 * 1000 : undefined,
  })
```

But `activeSchedule` also depends on `data`. Instead, just use a fixed 60s refetch interval — it's already within the pattern used by `useNextActions`:

```jsx
  const { data } = useActiveSchedule({
    refetchInterval: 60 * 1000,
  })
```

This is simple and correct. The 60s poll only fires API calls when the component is mounted (banner visible).

**Step 4: Run tests to verify they pass**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx vitest run src/components/scheduler/__tests__/ActiveScheduleBanner.test.jsx`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add webui/frontend/src/components/scheduler/ActiveScheduleBanner.jsx \
       webui/frontend/src/components/scheduler/__tests__/ActiveScheduleBanner.test.jsx
git commit -m "feat: add GPS transition toast to ActiveScheduleBanner (#382)"
```

---

### Task 5: Add coordinate source stat to ActivationPanel

**Files:**
- Modify: `webui/frontend/src/components/scheduler/ScheduleEditor/ActivationPanel.jsx`
- Create: `webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/ActivationPanel.test.jsx`

**Step 1: Write the failing tests**

Create `webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/ActivationPanel.test.jsx`:

```jsx
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import ActivationPanel from '../ActivationPanel'

// Mock hooks
vi.mock('../../../../hooks/useSchedules', () => ({
  useActiveSchedule: vi.fn(),
  useActivateSchedule: vi.fn(),
  useDeactivateSchedule: vi.fn(),
  useSchedulePreview: vi.fn(),
}))

vi.mock('../../ActivationProgress/ActivationProgress', () => ({
  default: vi.fn(() => <div data-testid="activation-progress" />),
}))

import {
  useActiveSchedule,
  useActivateSchedule,
  useDeactivateSchedule,
  useSchedulePreview,
} from '../../../../hooks/useSchedules'

describe('ActivationPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useActivateSchedule.mockReturnValue({ mutate: vi.fn() })
    useDeactivateSchedule.mockReturnValue({ mutate: vi.fn(), isPending: false })
    useSchedulePreview.mockReturnValue({ data: null })
  })

  describe('coordinate source stat (Issue #382)', () => {
    it('shows "Approx. location" with amber dot for timezone source', () => {
      useActiveSchedule.mockReturnValue({
        data: {
          active_schedule: { schedule_id: 'sched-1' },
          coordinates_source: 'timezone',
        },
        refetch: vi.fn(),
      })

      render(
        <ActivationPanel scheduleId="sched-1" routineCount={2} hasUnsavedChanges={false} />
      )

      const stat = screen.getByTestId('coord-source-stat')
      expect(stat).toHaveTextContent('Approx. location')
    })

    it('shows "GPS" with green dot for gps source', () => {
      useActiveSchedule.mockReturnValue({
        data: {
          active_schedule: { schedule_id: 'sched-1' },
          coordinates_source: 'gps',
        },
        refetch: vi.fn(),
      })

      render(
        <ActivationPanel scheduleId="sched-1" routineCount={2} hasUnsavedChanges={false} />
      )

      const stat = screen.getByTestId('coord-source-stat')
      expect(stat).toHaveTextContent('GPS')
    })

    it('shows "Manual" with blue dot for explicit source', () => {
      useActiveSchedule.mockReturnValue({
        data: {
          active_schedule: { schedule_id: 'sched-1' },
          coordinates_source: 'explicit',
        },
        refetch: vi.fn(),
      })

      render(
        <ActivationPanel scheduleId="sched-1" routineCount={2} hasUnsavedChanges={false} />
      )

      const stat = screen.getByTestId('coord-source-stat')
      expect(stat).toHaveTextContent('Manual')
    })

    it('does not show coordinate stat when schedule is inactive', () => {
      useActiveSchedule.mockReturnValue({
        data: { active_schedule: null },
        refetch: vi.fn(),
      })

      render(
        <ActivationPanel scheduleId="sched-1" routineCount={2} hasUnsavedChanges={false} />
      )

      expect(screen.queryByTestId('coord-source-stat')).not.toBeInTheDocument()
    })
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx vitest run src/components/scheduler/ScheduleEditor/__tests__/ActivationPanel.test.jsx`
Expected: FAIL (no `coord-source-stat` element exists)

**Step 3: Implement the coordinate source stat**

In `ActivationPanel.jsx`:

1. Extract `coordinates_source` from the active data. After line 46 (`const isActive = activeData?.active_schedule?.schedule_id === scheduleId`), add:

```jsx
  const coordinatesSource = isActive ? activeData?.coordinates_source : null
```

2. Add coordinate source display config (after `const nextTime` line, around line 116):

```jsx
  // Coordinate source display config (Issue #382)
  const coordSourceConfig = {
    timezone: { dot: 'bg-amber-500', label: 'Approx. location' },
    gps: { dot: 'bg-green-500', label: 'GPS' },
    explicit: { dot: 'bg-blue-500', label: 'Manual' },
  }
  const coordSource = coordinatesSource ? coordSourceConfig[coordinatesSource] : null
```

3. Add the stat row to the stats grid. Change the grid from `grid-cols-3` to `grid-cols-3` (keep same) but add a new row below the existing grid (after line 203, before the closing `</div>` of the stats section):

```jsx
          {/* Coordinate source stat (Issue #382) */}
          {coordSource && (
            <div className="col-span-3 flex items-center justify-center gap-1.5 pt-2" data-testid="coord-source-stat">
              <div className={`w-1.5 h-1.5 rounded-full ${coordSource.dot}`} />
              <span className="text-xs text-gray-500 dark:text-gray-400">{coordSource.label}</span>
            </div>
          )}
```

Insert this just before the closing `</div>` of the grid (after the "Next" stat div, still inside `{scheduleId && !hasUnsavedChanges && (` block).

**Step 4: Run tests to verify they pass**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx vitest run src/components/scheduler/ScheduleEditor/__tests__/ActivationPanel.test.jsx`
Expected: All 4 tests PASS

**Step 5: Commit**

```bash
git add webui/frontend/src/components/scheduler/ScheduleEditor/ActivationPanel.jsx \
       webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/ActivationPanel.test.jsx
git commit -m "feat: add coordinate source stat to ActivationPanel (#382)"
```

---

### Task 6: Run full test suites and lint

**Files:** None (verification only)

**Step 1: Run all backend GPS polling tests**

Run: `cd /home/zane/projects/Mothbox/Firmware && python3 -m pytest Tests/unit/test_scheduler_service_gps_polling.py Tests/unit/test_scheduler_service.py -v`
Expected: All tests PASS

**Step 2: Run all frontend scheduler tests**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx vitest run src/components/scheduler/`
Expected: All tests PASS

**Step 3: Run ESLint on modified frontend files**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx eslint src/components/scheduler/ActiveScheduleBanner.jsx src/components/scheduler/ScheduleEditor/ActivationPanel.jsx`
Expected: Clean (no errors or warnings)

**Step 4: Run Ruff on modified backend files**

Run: `cd /home/zane/projects/Mothbox/Firmware && ruff check webui/backend/services/scheduler_service.py`
Expected: Clean

**Step 5: Run Bandit on modified backend files**

Run: `cd /home/zane/projects/Mothbox/Firmware && bandit -c pyproject.toml webui/backend/services/scheduler_service.py`
Expected: No MEDIUM+ findings

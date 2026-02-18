# Tier 3 GPIO Daemon & WebSocket Infrastructure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add GPIO daemon integration tests and health monitoring, document RPi.GPIO coexistence, audit legacy scripts, migrate to gunicorn+eventlet for production, and add shared WebSocket context.

**Architecture:** Eight tasks in two groups: GPIO daemon hardening (#401-404) and WebSocket infrastructure (#376, #368). GPIO tasks add IPC-level integration tests, a HEALTH command, and clean up legacy scripts. WebSocket tasks replace Werkzeug with gunicorn+eventlet in production and consolidate three independent Socket.io connections into a shared React context.

**Tech Stack:** Python (gpiod, Flask, gunicorn, eventlet), React (Socket.io-client, Context API), Vitest/RTL (frontend tests), pytest (backend tests)

---

## Task 1: GPIO Daemon Integration Tests (#401)

**Files:**
- Create: `Tests/integration/test_gpio_daemon_integration.py`

The daemon already has 84 unit tests with mocked gpiod. These integration tests start a real daemon subprocess (with mock gpiod on non-Pi) and verify the full IPC path: client → socket → daemon → response.

**Step 1: Write integration tests**

Reference the existing daemon test pattern in `Tests/unit/test_gpio_daemon.py` — it uses a `running_daemon` fixture (lines 93-147) that starts the daemon in a background thread with mocked gpiod. The integration tests should use a similar approach but exercise the `gpio_client` public API instead of raw socket sends.

Read these files first:
- `lib/gpio_daemon.py` — understand the `run(stop_event)` function signature
- `lib/gpio_client.py` — understand the public API functions
- `lib/gpio_protocol.py` — socket path and constants
- `Tests/unit/test_gpio_daemon.py` — the `running_daemon` fixture pattern

```python
"""Integration tests for GPIO daemon ↔ client IPC.

Starts a real daemon subprocess (with mocked gpiod) and exercises
the full IPC path via the gpio_client public API.
"""

import json
import os
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def daemon_env():
    """Create temp directories for daemon state and socket."""
    with tempfile.TemporaryDirectory() as tmp:
        sock_path = os.path.join(tmp, "gpio.sock")
        state_file = os.path.join(tmp, "gpio_state.json")
        yield {
            "tmp_dir": tmp,
            "sock_path": sock_path,
            "state_file": state_file,
        }


@pytest.fixture
def mock_gpiod():
    """Mock gpiod v2 module for non-Pi environments."""
    mock_chip = MagicMock()
    mock_request = MagicMock()
    mock_chip.request_lines.return_value = mock_request

    # Make get_value return INACTIVE by default (switch not pressed)
    mock_value = MagicMock()
    mock_value.name = "INACTIVE"
    mock_request.get_value.return_value = mock_value

    mock_gpiod_module = MagicMock()
    mock_gpiod_module.Chip.return_value = mock_chip
    mock_gpiod_module.LineSettings.return_value = MagicMock()
    mock_gpiod_module.Value.ACTIVE = MagicMock(name="ACTIVE")
    mock_gpiod_module.Value.ACTIVE.name = "ACTIVE"
    mock_gpiod_module.Value.INACTIVE = MagicMock(name="INACTIVE")
    mock_gpiod_module.Value.INACTIVE.name = "INACTIVE"

    return mock_gpiod_module, mock_request


@pytest.fixture
def sample_pins():
    """Standard 5.x GPIO pin configuration."""
    return {"Relay_Ch1": 5, "Relay_Ch2": 19, "Relay_Ch3": 9}


@pytest.fixture
def sample_switch_pins():
    return {"off_pin": 16, "debug_pin": 12}


@pytest.fixture
def running_daemon(daemon_env, mock_gpiod, sample_pins, sample_switch_pins):
    """Start a real daemon in a background thread, yield when ready."""
    import sys

    mock_gpiod_module, mock_request = mock_gpiod
    stop_event = threading.Event()

    with (
        patch.dict(sys.modules, {"gpiod": mock_gpiod_module}),
        patch("lib.gpio_daemon.SOCKET_PATH", daemon_env["sock_path"]),
        patch("lib.gpio_daemon.STATE_FILE", Path(daemon_env["state_file"])),
        patch("lib.gpio_daemon._get_gpio_pins", return_value=sample_pins),
        patch("lib.gpio_daemon._get_switch_pins", return_value=sample_switch_pins),
        patch("lib.gpio_daemon._is_active_low", return_value=False),
        patch("lib.gpio_daemon._sd_notify"),
    ):
        from lib import gpio_daemon

        daemon_thread = threading.Thread(
            target=gpio_daemon.run, args=(stop_event,), daemon=True
        )
        daemon_thread.start()

        # Wait for socket to become available
        for _ in range(50):
            if os.path.exists(daemon_env["sock_path"]):
                break
            time.sleep(0.05)
        else:
            pytest.fail("Daemon socket did not appear within 2.5s")

        yield {
            "sock_path": daemon_env["sock_path"],
            "state_file": daemon_env["state_file"],
            "stop_event": stop_event,
            "mock_request": mock_request,
        }

        stop_event.set()
        daemon_thread.join(timeout=5)


def _send_raw(sock_path, command, timeout=2.0):
    """Send a raw command to the daemon and return the response."""
    import socket

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        s.connect(sock_path)
        s.sendall((command + "\n").encode())
        return s.recv(4096).decode().strip()


@pytest.mark.integration
class TestDaemonClientRoundtrip:
    """Test full IPC roundtrip: client → socket → daemon → response."""

    def test_ping_pong(self, running_daemon):
        response = _send_raw(running_daemon["sock_path"], "PING")
        assert response == "PONG"

    def test_set_and_get_relay(self, running_daemon):
        # SET attract on
        response = _send_raw(running_daemon["sock_path"], "SET attract on")
        assert response.startswith("OK")
        assert "attract" in response
        assert "on" in response

        # GET attract — should be on
        response = _send_raw(running_daemon["sock_path"], "GET attract")
        assert "attract" in response
        assert "on" in response

    def test_set_relay_off(self, running_daemon):
        _send_raw(running_daemon["sock_path"], "SET flash on")
        _send_raw(running_daemon["sock_path"], "SET flash off")
        response = _send_raw(running_daemon["sock_path"], "GET flash")
        assert "off" in response

    def test_status_all_relays(self, running_daemon):
        _send_raw(running_daemon["sock_path"], "SET attract on")
        _send_raw(running_daemon["sock_path"], "SET flash off")
        response = _send_raw(running_daemon["sock_path"], "STATUS")
        assert response.startswith("STATUS")
        assert "attract=on" in response
        assert "flash=off" in response

    def test_read_switch(self, running_daemon):
        response = _send_raw(running_daemon["sock_path"], "READ off_pin")
        assert response.startswith("VALUE")
        assert "off_pin" in response

    def test_invalid_command(self, running_daemon):
        response = _send_raw(running_daemon["sock_path"], "INVALID_CMD")
        assert response.startswith("ERR")


@pytest.mark.integration
class TestStatePersistence:
    """Test relay state survives daemon restart."""

    def test_state_persists_across_restart(self, daemon_env, mock_gpiod, sample_pins, sample_switch_pins):
        import sys

        mock_gpiod_module, mock_request = mock_gpiod
        state_file = Path(daemon_env["state_file"])

        # First daemon run: set attract on
        stop1 = threading.Event()
        with (
            patch.dict(sys.modules, {"gpiod": mock_gpiod_module}),
            patch("lib.gpio_daemon.SOCKET_PATH", daemon_env["sock_path"]),
            patch("lib.gpio_daemon.STATE_FILE", state_file),
            patch("lib.gpio_daemon._get_gpio_pins", return_value=sample_pins),
            patch("lib.gpio_daemon._get_switch_pins", return_value=sample_switch_pins),
            patch("lib.gpio_daemon._is_active_low", return_value=False),
            patch("lib.gpio_daemon._sd_notify"),
        ):
            from lib import gpio_daemon

            t1 = threading.Thread(target=gpio_daemon.run, args=(stop1,), daemon=True)
            t1.start()
            for _ in range(50):
                if os.path.exists(daemon_env["sock_path"]):
                    break
                time.sleep(0.05)

            _send_raw(daemon_env["sock_path"], "SET attract on")
            stop1.set()
            t1.join(timeout=5)

        # Verify state file was written
        assert state_file.exists()
        saved = json.loads(state_file.read_text())
        assert saved.get("attract") == "on"

        # Remove stale socket so second daemon can bind
        sock = Path(daemon_env["sock_path"])
        if sock.exists():
            sock.unlink()

        # Second daemon run: verify state restored
        stop2 = threading.Event()
        with (
            patch.dict(sys.modules, {"gpiod": mock_gpiod_module}),
            patch("lib.gpio_daemon.SOCKET_PATH", daemon_env["sock_path"]),
            patch("lib.gpio_daemon.STATE_FILE", state_file),
            patch("lib.gpio_daemon._get_gpio_pins", return_value=sample_pins),
            patch("lib.gpio_daemon._get_switch_pins", return_value=sample_switch_pins),
            patch("lib.gpio_daemon._is_active_low", return_value=False),
            patch("lib.gpio_daemon._sd_notify"),
        ):
            # Re-import to get fresh module state
            import importlib

            importlib.reload(gpio_daemon)

            t2 = threading.Thread(target=gpio_daemon.run, args=(stop2,), daemon=True)
            t2.start()
            for _ in range(50):
                if os.path.exists(daemon_env["sock_path"]):
                    break
                time.sleep(0.05)

            response = _send_raw(daemon_env["sock_path"], "GET attract")
            assert "on" in response

            stop2.set()
            t2.join(timeout=5)
```

**Step 2: Run tests**

Run: `cd /home/zane/projects/Mothbox/Firmware && python3 -m pytest Tests/integration/test_gpio_daemon_integration.py -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add Tests/integration/test_gpio_daemon_integration.py
git commit -m "test(gpio): add integration tests for daemon/client IPC (#401)"
```

---

## Task 2: GPIO Daemon HEALTH Command and API Endpoint (#402)

**Files:**
- Modify: `lib/gpio_protocol.py` — add HEALTH constant
- Modify: `lib/gpio_daemon.py` — add HEALTH handler
- Modify: `lib/gpio_client.py` — add `health()` function
- Modify: `webui/backend/routes/gpio.py` — add `/api/gpio/health` endpoint
- Modify: `Tests/unit/test_gpio_daemon.py` — add HEALTH test
- Modify: `Tests/unit/test_gpio_routes.py` — add health route test

Read these files first to understand existing patterns:
- `lib/gpio_protocol.py` — current constants
- `lib/gpio_daemon.py:243-297` — command handler pattern
- `lib/gpio_client.py:95-115` — `_send_command()` pattern
- `webui/backend/routes/gpio.py` — route patterns, how GPIODaemonError is caught

**Step 1: Add HEALTH protocol constant**

In `lib/gpio_protocol.py`, add after the existing constants:

```python
# Command names
CMD_HEALTH = "HEALTH"
```

**Step 2: Add HEALTH handler to daemon**

In `lib/gpio_daemon.py`, inside the `_handle_command` function (around line 282, before the STATUS handler), add a HEALTH case. The daemon should track `started_at` (set during initialization) and `last_command_at` (updated on each command). The HEALTH response should return:
- `uptime_seconds`: seconds since daemon started
- `managed_lines`: count of relay + switch lines
- `last_command_at`: ISO timestamp of last command (or "never")

The implementer should:
1. Add `started_at = time.time()` at daemon startup (around line 159)
2. Add `last_command_at = None` at daemon startup
3. Update `last_command_at = time.time()` at the start of `_handle_command`
4. Add the HEALTH handler that computes uptime and returns a space-separated response:
   `HEALTH uptime=<seconds> lines=<count> last_cmd=<iso_or_never>`

**Step 3: Add `health()` to gpio_client**

In `lib/gpio_client.py`, add a `health()` function that sends the HEALTH command and parses the response into a dict:

```python
def health():
    """Query daemon health status.

    Returns:
        dict: {"reachable": True, "uptime_seconds": float, "managed_lines": int, "last_command_at": str}

    Raises:
        GPIODaemonError: If daemon is not reachable
    """
    response = _send_command("HEALTH")
    # Parse "HEALTH uptime=123.4 lines=5 last_cmd=2026-02-18T14:00:00"
    result = {"reachable": True}
    for part in response.split():
        if "=" in part:
            key, value = part.split("=", 1)
            if key == "uptime":
                result["uptime_seconds"] = float(value)
            elif key == "lines":
                result["managed_lines"] = int(value)
            elif key == "last_cmd":
                result["last_command_at"] = value
    return result
```

**Step 4: Add `/api/gpio/health` endpoint**

In `webui/backend/routes/gpio.py`, add a new GET route following the existing pattern:

```python
@gpio_bp.route("/api/gpio/health", methods=["GET"])
def gpio_health():
    """Check GPIO daemon health status."""
    try:
        from lib.gpio_client import health

        status = health()
        return jsonify(status)
    except GPIODaemonError:
        return jsonify({"reachable": False, "error": "GPIO daemon not available"}), 503
    except Exception as e:
        return jsonify({"reachable": False, "error": str(e)}), 500
```

**Step 5: Add tests**

Add to `Tests/unit/test_gpio_daemon.py` — a test that sends HEALTH and verifies the response format.

Add to `Tests/unit/test_gpio_routes.py` — tests for the `/api/gpio/health` endpoint (daemon reachable, daemon unreachable returning 503).

**Step 6: Run tests**

Run: `cd /home/zane/projects/Mothbox/Firmware && python3 -m pytest Tests/unit/test_gpio_daemon.py Tests/unit/test_gpio_routes.py Tests/unit/test_gpio_client.py -v --tb=short 2>&1 | tail -20`
Expected: All tests PASS (existing + new)

**Step 7: Commit**

```bash
git add lib/gpio_protocol.py lib/gpio_daemon.py lib/gpio_client.py \
        webui/backend/routes/gpio.py \
        Tests/unit/test_gpio_daemon.py Tests/unit/test_gpio_routes.py
git commit -m "feat(gpio): add HEALTH command and /api/gpio/health endpoint (#402)"
```

---

## Task 3: GPIO Health Indicator on GPIO Page (#402)

**Files:**
- Modify: `webui/frontend/src/utils/api.js` — add `getGpioHealth()` function
- Modify: `webui/frontend/src/pages/GPIO.jsx` — add health indicator

Read first:
- `webui/frontend/src/utils/api.js` — understand how API functions are defined (axios-based)
- `webui/frontend/src/pages/GPIO.jsx` — current page structure (144 lines)
- `webui/frontend/src/utils/queryKeys.js` — query key patterns

**Step 1: Add API function**

In `webui/frontend/src/utils/api.js`, add:

```javascript
export const getGpioHealth = () => api.get('/api/gpio/health')
```

**Step 2: Add query key**

In `webui/frontend/src/utils/queryKeys.js`, add `GPIO_HEALTH: ['gpio', 'health']` to the QUERY_KEYS object.

**Step 3: Add health indicator to GPIO page**

In `GPIO.jsx`, add a `useQuery` for health data that polls every 10 seconds. Display a small status bar below the page heading showing:
- Green dot + "Daemon connected" + uptime when reachable
- Red dot + "Daemon offline" when health query returns error or `reachable: false`

The implementer should add this between the `<h2>` heading and the relay grid. Keep it simple — a single line with a colored dot, status text, and optional uptime.

Format uptime as human-readable (e.g., "2h 15m" or "3d 5h").

**Step 4: Run frontend tests**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx vitest run src/pages/__tests__/GPIO.test.jsx`
Expected: Existing tests PASS (may need minor mock updates for the new health query)

**Step 5: Commit**

```bash
git add webui/frontend/src/utils/api.js webui/frontend/src/utils/queryKeys.js \
        webui/frontend/src/pages/GPIO.jsx
git commit -m "feat(gpio): add daemon health indicator to GPIO page (#402)"
```

---

## Task 4: Document RPi.GPIO Coexistence (#403)

**Files:**
- Modify: `5.x/UpdateDisplay.py` — add clarifying comments

Read first:
- `5.x/UpdateDisplay.py:18,31` — the two GPIO-related imports

**Step 1: Add documentation comments**

In `5.x/UpdateDisplay.py`, add a comment block near the RPi.GPIO import (line 31) explaining the coexistence:

```python
# NOTE: RPi.GPIO is imported here for the Waveshare e-paper library (waveshare_epd),
# which uses it for SPI/display pin control (RST, DC, CS, BUSY).
# These pins do NOT overlap with the GPIO daemon's relay/switch pins.
# Switch reads (off_pin, debug_pin) use gpio_client via the daemon (line 18).
# See issue #403 for details on this coexistence decision.
import RPi.GPIO as GPIO
```

**Step 2: Commit**

```bash
git add 5.x/UpdateDisplay.py
git commit -m "docs(gpio): document RPi.GPIO coexistence for e-paper pins (#403)"
```

---

## Task 5: Audit and Clean Up Legacy Scripts (#404)

**Files:**
- Potentially move scripts in `5.x/scripts/` to `5.x/scripts/OldScripts/`

The exploration found that **no scripts in `5.x/scripts/` are called by TakePhoto.py or Scheduler.py** — all active scripts are at the 5.x top level and already migrated to `gpio_client`. The scripts in `5.x/scripts/` (FlashOn_ManPhoto_FlashOff.py, CheckFocus.py, ReadMuxAMuxB.py, etc.) are standalone utilities for manual/diagnostic use.

Read first:
- `5.x/TakePhoto.py` — confirm no subprocess calls to `scripts/`
- `5.x/Scheduler.py` — confirm no imports from `scripts/`
- `5.x/scripts/` — list files, identify which are active vs legacy

**Step 1: Verify no active callers**

The implementer should:
1. Grep `5.x/TakePhoto.py` and `5.x/Scheduler.py` for any references to files in `scripts/`
2. Grep `webui/backend/` for any references to `5.x/scripts/`
3. Confirm the only active scripts are top-level (Attract_On.py, Flash_On.py, etc. — already migrated)

**Step 2: Add deprecation header to unmigrated scripts**

For each script in `5.x/scripts/` that imports RPi.GPIO, add a comment header:

```python
# DEPRECATED: This script uses RPi.GPIO directly, which conflicts with the GPIO daemon.
# For relay control, use the gpio_client library instead: lib.gpio_client.relay_on/relay_off
# This script is retained for reference only. See issue #404.
```

Add this to: `Flash_On.py`, `Flash_Off.py`, `FlashOn_ManPhoto_FlashOff.py`, `CheckFocus.py`, `ReadMuxAMuxB.py`, `PlowmanAutofocus.py`, and any other scripts with `import RPi.GPIO`.

**Step 3: Commit**

```bash
git add 5.x/scripts/
git commit -m "refactor(gpio): add deprecation notices to legacy RPi.GPIO scripts (#404)"
```

---

## Task 6: Migrate to gunicorn+eventlet (#376)

**Files:**
- Modify: `installation-utils/requirements.txt` — add gunicorn, eventlet
- Create: `webui/backend/gunicorn.conf.py`
- Modify: `webui/backend/app.py` — change async_mode, conditional launch
- Modify: `webui/backend/websocket_handlers.py` — non-blocking disconnect handler
- Modify: `installation-utils/mothbox-webui.service.template` — gunicorn launch

Read first:
- `webui/backend/app.py:88-101` — current SocketIO config
- `webui/backend/app.py:469-512` — current `if __name__` block
- `webui/backend/websocket_handlers.py:104-108` — blocking disconnect handler
- `webui/backend/config.py` — how MOTHBOX_ENV is detected
- `installation-utils/mothbox-webui.service.template` — current service definition
- `installation-utils/requirements.txt` — current dependencies

**Step 1: Add dependencies**

In `installation-utils/requirements.txt`, add:

```
gunicorn>=21.2.0
eventlet>=0.36.0
```

**Step 2: Create gunicorn config**

Create `webui/backend/gunicorn.conf.py`:

```python
"""Gunicorn configuration for Mothbox Web UI.

Uses eventlet worker for proper WebSocket support.
Single worker since the camera can only be used by one process.
"""

import os

# Worker class: eventlet for async WebSocket handling
worker_class = "eventlet"

# Single worker — Picamera2 can only run one instance at a time
workers = 1

# Bind to all interfaces on port 5000
bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:5000")

# Timeout for worker startup and graceful shutdown
timeout = 120
graceful_timeout = 30

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")

# Disable worker recycling (camera state is long-lived)
max_requests = 0
```

**Step 3: Update app.py async_mode**

In `webui/backend/app.py`, change the SocketIO initialization (around line 93) to use eventlet:

```python
socketio = SocketIO(
    app,
    cors_allowed_origins=config.CORS_ORIGINS if config.CORS_ORIGINS else [],
    async_mode="eventlet",
    logger=False,
    engineio_logger=False,
    ping_timeout=60,
    ping_interval=25,
)
```

Update the `if __name__` block to keep Werkzeug for development:

```python
if __name__ == "__main__":
    if config.DEBUG and config.ENV_NAME == "development":
        # Development: use Werkzeug with auto-reload
        socketio.run(
            app,
            host=config.HOST,
            port=config.PORT,
            debug=True,
            allow_unsafe_werkzeug=True,
        )
    else:
        # Production: should be launched via gunicorn
        # gunicorn -c webui/backend/gunicorn.conf.py 'webui.backend.app:app'
        print("Production mode: launch via gunicorn instead of running app.py directly")
        print("  gunicorn -c webui/backend/gunicorn.conf.py 'webui.backend.app:app'")
        socketio.run(
            app,
            host=config.HOST,
            port=config.PORT,
            debug=False,
        )
```

**Important**: Add `import eventlet; eventlet.monkey_patch()` at the very top of `app.py` (before all other imports) to enable eventlet's cooperative threading. This is required for Flask-SocketIO's eventlet mode.

**Step 4: Non-blocking disconnect handler**

In `webui/backend/websocket_handlers.py`, change the disconnect handler (lines 104-108) to be non-blocking:

```python
@socketio.on("disconnect")
def handle_disconnect():
    """Handle client WebSocket disconnection.

    Runs stop_streaming in a background thread to avoid blocking
    the event loop and causing race conditions with HTTP responses.
    See issue #376.
    """
    print("Client disconnected - stopping live view if active")
    import threading

    threading.Thread(
        target=camera_streamer.stop_streaming, daemon=True
    ).start()
```

**Step 5: Update systemd service template**

In `installation-utils/mothbox-webui.service.template`, change ExecStart (line 11):

From:
```ini
ExecStart=/usr/bin/python3 __MOTHBOX_HOME__/webui/backend/app.py
```

To:
```ini
ExecStart=/usr/bin/gunicorn -c __MOTHBOX_HOME__/webui/backend/gunicorn.conf.py --chdir __MOTHBOX_HOME__/webui/backend app:app
```

Also update the TODO comment (line 45) to note it's been implemented.

**Step 6: Verify app starts in test mode**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/backend && MOTHBOX_ENV=test python3 -c "import app; print('OK')"`
Expected: No import errors

**Step 7: Commit**

```bash
git add installation-utils/requirements.txt webui/backend/gunicorn.conf.py \
        webui/backend/app.py webui/backend/websocket_handlers.py \
        installation-utils/mothbox-webui.service.template
git commit -m "feat(backend): migrate to gunicorn+eventlet for production (#376)"
```

---

## Task 7: Shared WebSocket Context and useSocket Hook (#368)

**Files:**
- Create: `webui/frontend/src/contexts/SocketContext.jsx`
- Create: `webui/frontend/src/hooks/useSocket.js`
- Modify: `webui/frontend/src/App.jsx` — wrap with SocketProvider
- Modify: `webui/frontend/src/pages/Camera.jsx` — use useSocket()
- Modify: `webui/frontend/src/pages/Settings.jsx` — use useSocket()
- Modify: `webui/frontend/src/components/scheduler/ActivationProgress/ActivationProgress.jsx` — use useSocket()

Read first:
- `webui/frontend/src/contexts/SelectionContext.jsx` — existing context pattern
- `webui/frontend/src/hooks/useSelection.js` — existing hook pattern
- `webui/frontend/src/App.jsx` — current provider nesting
- `webui/frontend/src/pages/Camera.jsx:251-427` — current socket useEffect
- `webui/frontend/src/pages/Settings.jsx:221-237` — current socket useEffect
- `webui/frontend/src/components/scheduler/ActivationProgress/ActivationProgress.jsx:70-124` — current socket useEffect

**Step 1: Create SocketContext**

```jsx
// webui/frontend/src/contexts/SocketContext.jsx
import { createContext, useContext, useEffect, useRef, useState } from 'react'
import { io } from 'socket.io-client'

const SocketContext = createContext(null)

export function useSocketContext() {
  return useContext(SocketContext)
}

export function SocketProvider({ children }) {
  const socketRef = useRef(null)
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    const wsUrl = window.location.origin
    const socket = io(wsUrl, {
      transports: ['websocket', 'polling'],
    })

    socket.on('connect', () => setConnected(true))
    socket.on('disconnect', () => setConnected(false))

    socketRef.current = socket

    return () => {
      socket.disconnect()
      socketRef.current = null
    }
  }, [])

  const value = {
    socket: socketRef.current,
    connected,
  }

  return (
    <SocketContext.Provider value={value}>
      {children}
    </SocketContext.Provider>
  )
}
```

**Step 2: Create useSocket hook**

```javascript
// webui/frontend/src/hooks/useSocket.js
import { useSocketContext } from '../contexts/SocketContext'

export default function useSocket() {
  const context = useSocketContext()
  if (!context) {
    throw new Error('useSocket must be used within SocketProvider')
  }
  return context
}
```

**Step 3: Add SocketProvider to App.jsx**

In `App.jsx`, import `SocketProvider` and wrap it inside `QueryClientProvider` but outside `Router`:

```jsx
import { SocketProvider } from './contexts/SocketContext'

// In App():
<ErrorBoundary>
  <QueryClientProvider client={queryClient}>
    <SocketProvider>
      <Toaster ... />
      <FilterProvider>
        <Router>
          <AppLayout />
        </Router>
      </FilterProvider>
    </SocketProvider>
  </QueryClientProvider>
</ErrorBoundary>
```

**Step 4: Refactor Camera.jsx**

Remove the socket creation useEffect (lines ~251-427). Replace with:

```jsx
import useSocket from '../hooks/useSocket'

// Inside the component:
const { socket, connected } = useSocket()

// Replace all socketRef.current references with socket
// Remove the connect/disconnect state management (use connected from hook)
// Keep all event handler registration in a useEffect that depends on [socket]
// The cleanup should remove event listeners but NOT disconnect the socket
```

Key changes:
- Remove `const socketRef = useRef(null)` and the `io()` connection setup
- Replace `socketRef.current` with `socket` throughout
- In the cleanup function, use `socket.off('event_name')` instead of `socket.disconnect()`
- Use `connected` from the hook instead of local `connected` state

**Step 5: Refactor Settings.jsx**

Remove the socket creation useEffect (lines ~221-237). Replace with:

```jsx
import useSocket from '../hooks/useSocket'

const { socket } = useSocket()

useEffect(() => {
  if (!socket) return

  const handleReloaded = () => {
    queryClient.invalidateQueries(QUERY_KEYS.WEBUI_SETTINGS)
  }

  socket.on('settings_reloaded', handleReloaded)
  return () => socket.off('settings_reloaded', handleReloaded)
}, [socket])
```

Update the mutation's `onSuccess` to use `socket` directly instead of `socketRef.current`.

**Step 6: Refactor ActivationProgress.jsx**

Remove the socket creation useEffect (lines ~70-124). Replace with:

```jsx
import useSocket from '../../../hooks/useSocket'

const { socket } = useSocket()

useEffect(() => {
  if (!socket) return

  const handleProgress = (data) => {
    if (data.schedule_id !== scheduleId) return
    setProgress(data.progress)
    setPhase(data.phase)
    if (data.phase === 'complete') {
      setState('complete')
      onCompleteRef.current?.()
    } else if (data.phase === 'failed') {
      setState('error')
      const msg = data.error || 'Activation failed'
      setErrorMessage(msg)
      onErrorRef.current?.(msg)
    }
  }

  const handleError = (error) => {
    console.error('WebSocket connection failed:', error)
    setState('error')
    setErrorMessage('Connection failed')
    onErrorRef.current?.('Connection failed')
  }

  socket.on('schedule:activation_progress', handleProgress)
  socket.on('connect_error', handleError)
  socket.on('error', handleError)

  return () => {
    socket.off('schedule:activation_progress', handleProgress)
    socket.off('connect_error', handleError)
    socket.off('error', handleError)
  }
}, [socket, scheduleId])
```

Remove the retry mechanism's socket recreation — the shared socket handles reconnection automatically. The retry button should just reset local state and re-trigger the activation API call.

**Step 7: Run all frontend tests**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx vitest run --reporter=verbose 2>&1 | tail -15`
Expected: All tests PASS. Some existing tests may need mock updates (mock useSocket instead of socket.io-client).

**Step 8: Commit**

```bash
git add webui/frontend/src/contexts/SocketContext.jsx \
        webui/frontend/src/hooks/useSocket.js \
        webui/frontend/src/App.jsx \
        webui/frontend/src/pages/Camera.jsx \
        webui/frontend/src/pages/Settings.jsx \
        webui/frontend/src/components/scheduler/ActivationProgress/ActivationProgress.jsx
git commit -m "refactor(frontend): add shared WebSocket context and useSocket hook (#368)"
```

---

## Task 8: Tests for SocketProvider and useSocket (#368)

**Files:**
- Create: `webui/frontend/src/contexts/__tests__/SocketContext.test.jsx`
- Create: `webui/frontend/src/hooks/__tests__/useSocket.test.jsx`

Follow the patterns from:
- `webui/frontend/src/hooks/__tests__/useSelection.test.jsx` — hook test pattern
- `webui/frontend/src/contexts/__tests__/SelectionContext.test.jsx` — context test pattern (if exists)

**Step 1: Write SocketContext tests**

```jsx
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { SocketProvider, useSocketContext } from '../SocketContext'

// Mock socket.io-client
vi.mock('socket.io-client', () => {
  const handlers = {}
  const mockSocket = {
    on: vi.fn((event, cb) => { handlers[event] = cb }),
    off: vi.fn(),
    disconnect: vi.fn(),
    _trigger: (event, data) => handlers[event]?.(data),
  }
  return { io: vi.fn(() => mockSocket), _mockSocket: mockSocket, _handlers: handlers }
})

import { _mockSocket, _handlers } from 'socket.io-client'

function TestConsumer() {
  const ctx = useSocketContext()
  return (
    <div>
      <span data-testid="connected">{String(ctx?.connected)}</span>
      <span data-testid="has-socket">{String(!!ctx?.socket)}</span>
    </div>
  )
}

describe('SocketProvider', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('provides socket and connected state', () => {
    render(
      <SocketProvider><TestConsumer /></SocketProvider>
    )
    expect(screen.getByTestId('has-socket')).toHaveTextContent('true')
    expect(screen.getByTestId('connected')).toHaveTextContent('false')
  })

  it('updates connected state on connect event', () => {
    render(
      <SocketProvider><TestConsumer /></SocketProvider>
    )
    act(() => { _mockSocket._trigger('connect') })
    expect(screen.getByTestId('connected')).toHaveTextContent('true')
  })

  it('updates connected state on disconnect event', () => {
    render(
      <SocketProvider><TestConsumer /></SocketProvider>
    )
    act(() => { _mockSocket._trigger('connect') })
    act(() => { _mockSocket._trigger('disconnect') })
    expect(screen.getByTestId('connected')).toHaveTextContent('false')
  })

  it('disconnects socket on unmount', () => {
    const { unmount } = render(
      <SocketProvider><TestConsumer /></SocketProvider>
    )
    unmount()
    expect(_mockSocket.disconnect).toHaveBeenCalled()
  })
})
```

**Step 2: Write useSocket tests**

```jsx
import { describe, it, expect, vi } from 'vitest'
import { renderHook } from '@testing-library/react'
import useSocket from '../useSocket'
import { SocketProvider } from '../../contexts/SocketContext'

vi.mock('socket.io-client', () => {
  const mockSocket = {
    on: vi.fn(),
    off: vi.fn(),
    disconnect: vi.fn(),
  }
  return { io: vi.fn(() => mockSocket) }
})

describe('useSocket', () => {
  it('throws when used outside SocketProvider', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => renderHook(() => useSocket())).toThrow(
      'useSocket must be used within SocketProvider'
    )
    spy.mockRestore()
  })

  it('returns context when inside SocketProvider', () => {
    const wrapper = ({ children }) => <SocketProvider>{children}</SocketProvider>
    const { result } = renderHook(() => useSocket(), { wrapper })
    expect(result.current).toBeDefined()
    expect(result.current).toHaveProperty('socket')
    expect(result.current).toHaveProperty('connected')
  })
})
```

**Step 3: Run tests**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx vitest run src/contexts/__tests__/SocketContext.test.jsx src/hooks/__tests__/useSocket.test.jsx`
Expected: All tests PASS

**Step 4: Run full frontend test suite**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx vitest run --reporter=verbose 2>&1 | tail -15`
Expected: All tests PASS, no regressions

**Step 5: Commit**

```bash
git add webui/frontend/src/contexts/__tests__/SocketContext.test.jsx \
        webui/frontend/src/hooks/__tests__/useSocket.test.jsx
git commit -m "test(frontend): add tests for SocketProvider and useSocket (#368)"
```

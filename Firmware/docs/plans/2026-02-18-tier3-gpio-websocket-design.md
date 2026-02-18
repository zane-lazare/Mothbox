# Tier 3 GPIO Daemon & WebSocket Infrastructure Design

**Date**: 2026-02-18
**Branch**: `feat/tier3-gpio-websocket`
**Issues**: #401, #402, #403, #404, #376, #368

---

## Issue #401: GPIO Daemon/Client Integration Tests

### Problem
PR #400 (GPIO daemon architecture) has 84 unit tests with mocked gpiod/sockets but no integration tests exercising the real daemon→client IPC path.

### Solution
~6 integration tests that start a real daemon subprocess with a mock gpiod fixture, send commands via `gpio_client`, and verify responses. Cover SET/GET/READ/STATUS/PING roundtrips and state persistence across daemon restart.

### Files
- `Tests/integration/test_gpio_daemon_integration.py` (new)

---

## Issue #402: GPIO Daemon Health Monitoring

### Problem
No way to monitor daemon health (reachability, uptime, stats) from the web UI.

### Solution
- Add `HEALTH` IPC command to daemon returning uptime, managed line count, last command timestamp
- Add `GET /api/gpio/health` endpoint that does PING + HEALTH check
- Add status indicator on GPIO page (green/red dot + uptime)

### Files
- `lib/gpio_daemon.py` — add HEALTH command handler
- `lib/gpio_protocol.py` — add HEALTH constant
- `lib/gpio_client.py` — add `health()` function
- `webui/backend/routes/gpio.py` — add `/api/gpio/health` endpoint
- `webui/frontend/src/pages/GPIO.jsx` — add health indicator
- `Tests/unit/test_gpio_daemon.py` — add HEALTH tests
- `Tests/unit/test_gpio_routes.py` — add health endpoint tests

---

## Issue #403: UpdateDisplay.py RPi.GPIO Coexistence

### Problem
5.x `UpdateDisplay.py` still imports RPi.GPIO for the Waveshare e-paper library's SPI/display pins.

### Solution
Accept coexistence. The e-paper pins (RST, DC, CS, BUSY) don't overlap with daemon-managed relay/switch pins. Add documenting comments, close the issue.

### Files
- `5.x/UpdateDisplay.py` — add clarifying comments

---

## Issue #404: Migrate Active Legacy Scripts

### Problem
Scripts in `5.x/scripts/` called by `TakePhoto.py` or `Scheduler.py` still use `RPi.GPIO` directly, conflicting with the daemon.

### Solution
Identify the ~5 active scripts and migrate them from `RPi.GPIO` to `gpio_client`. Leave unused utility scripts as-is.

### Files
- `5.x/scripts/` — migrate active scripts (identified during implementation)

---

## Issue #376: Flask-SocketIO Threading Race Condition

### Problem
`async_mode="threading"` with Werkzeug causes `AssertionError: write() before start_response` when a WebSocket disconnects during an HTTP request. The disconnect handler blocks for up to 2 seconds in `stop_streaming()`.

### Solution
Migrate to gunicorn + eventlet for production:
- Add `gunicorn` and `eventlet` dependencies
- Change `async_mode` to `"eventlet"` in app.py
- Add `gunicorn.conf.py` with eventlet worker, single worker process
- Update systemd service template to launch via gunicorn
- Keep Werkzeug for development (`MOTHBOX_ENV=development` runs `socketio.run()` directly)
- Apply non-blocking disconnect fix for dev mode too (background thread for `stop_streaming()`)
- Update `install_mothbox.sh` to install gunicorn+eventlet

### Files
- `webui/backend/app.py` — change async_mode, conditional launch
- `webui/backend/gunicorn.conf.py` (new)
- `webui/backend/websocket_handlers.py` — non-blocking disconnect handler
- `webui/backend/requirements.txt` — add gunicorn, eventlet
- `services/mothbox-webui.service.template` — gunicorn launch command
- `install_mothbox.sh` — install new dependencies

---

## Issue #368: Shared WebSocket Context

### Problem
Three frontend components (Camera, Settings, ActivationProgress) each create independent Socket.io connections. No shared connection management.

### Solution
- Create `SocketProvider` context at app level managing a single Socket.io connection
- Provide `useSocket()` hook returning the shared socket instance and connection status
- Refactor Camera.jsx, Settings.jsx, and ActivationProgress.jsx to use `useSocket()`

### Files
- `webui/frontend/src/contexts/SocketContext.jsx` (new)
- `webui/frontend/src/hooks/useSocket.js` (new)
- `webui/frontend/src/App.jsx` — wrap with SocketProvider
- `webui/frontend/src/pages/Camera.jsx` — use useSocket()
- `webui/frontend/src/pages/Settings.jsx` — use useSocket()
- `webui/frontend/src/components/scheduler/ActivationProgress/ActivationProgress.jsx` — use useSocket()
- `webui/frontend/src/contexts/__tests__/SocketContext.test.jsx` (new)
- `webui/frontend/src/hooks/__tests__/useSocket.test.jsx` (new)

---

## Branch Strategy

Single branch `feat/tier3-gpio-websocket`, ~8 commits:

1. `test(gpio): add integration tests for daemon/client IPC (#401)`
2. `feat(gpio): add HEALTH command and /api/gpio/health endpoint (#402)`
3. `feat(gpio): add daemon health indicator to GPIO page (#402)`
4. `docs(gpio): document RPi.GPIO coexistence for e-paper pins (#403)`
5. `refactor(gpio): migrate active legacy scripts to gpio_client (#404)`
6. `feat(backend): migrate to gunicorn+eventlet for production (#376)`
7. `refactor(frontend): add shared WebSocket context and useSocket hook (#368)`
8. `test(frontend): add tests for SocketProvider and useSocket (#368)`

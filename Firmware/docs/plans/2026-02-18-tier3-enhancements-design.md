# Tier 3 PR #430 Enhancement Design

**Date**: 2026-02-18
**Branch**: `feat/tier3-gpio-websocket` (amend existing branch)
**Context**: Follow-up enhancements from PR #430 code review

---

## Enhancement #1: Non-Daemon Cleanup Thread

### Problem
`websocket_handlers.py:115` uses `daemon=True` for the `stop_streaming()` background thread. Daemon threads are killed when the process exits, potentially interrupting camera cleanup.

### Solution
Change `daemon=True` to `daemon=False`. The thread completes naturally (<2s for camera release), so it won't block shutdown.

### Files
- `webui/backend/websocket_handlers.py` — change `daemon=True` to `daemon=False`
- `Tests/unit/test_websocket_handlers.py` — add test verifying thread is non-daemon

---

## Enhancement #2: GPIO Daemon recv Loop Wall-Clock Timeout

### Problem
`_recv_line()` reads byte-by-byte. While per-recv timeout is set (CONN_TIMEOUT on the connection), a slow client sending one byte every 1.9s could keep the connection open for up to MAX_MSG_LENGTH * CONN_TIMEOUT = 512 seconds, blocking the single-threaded accept loop.

### Solution
Track wall-clock elapsed time in `_recv_line()` and abort if total time exceeds a threshold (5 seconds). Add a `RECV_TOTAL_TIMEOUT` constant to `gpio_protocol.py`.

### Files
- `lib/gpio_protocol.py` — add `RECV_TOTAL_TIMEOUT = 5.0`
- `lib/gpio_daemon.py` — add wall-clock check in `_recv_line()`
- `Tests/unit/test_gpio_daemon.py` — add test for slow-send timeout

---

## Enhancement #3: SocketProvider Reconnection Config

### Problem
`SocketContext.jsx` creates the socket with no reconnection tuning. Default socket.io reconnection is enabled but unbounded (infinite retries). No UI feedback during reconnection attempts.

### Solution
- Add explicit reconnection config: 5 attempts, 1s initial delay, 5s max delay
- Expose `reconnecting` state in context via `reconnect_attempt` and `reconnect_failed` events
- Context value becomes `{ socket, connected, reconnecting }`

### Files
- `webui/frontend/src/contexts/SocketContext.jsx` — add reconnection config and `reconnecting` state
- `webui/frontend/src/hooks/useSocket.js` — expose `reconnecting` in return value
- `webui/frontend/src/contexts/__tests__/SocketContext.test.jsx` — add reconnection state tests

---

## Enhancement #4: HEALTH Command Additional Metrics

### Problem
HEALTH response only includes uptime, managed line count, and last command timestamp. No visibility into command throughput or errors.

### Solution
Add three fields to HEALTH response:
- `commands=<int>` — total commands processed since start
- `errors=<int>` — total ERR responses sent
- `memory_kb=<int>` — daemon RSS via `resource.getrusage()`

Update client parser and API route to pass through new fields.

### Files
- `lib/gpio_daemon.py` — add counters, include in HEALTH response
- `lib/gpio_client.py` — parse new HEALTH fields
- `webui/backend/routes/gpio.py` — pass through new fields
- `Tests/unit/test_gpio_daemon.py` — test new HEALTH fields
- `Tests/unit/test_gpio_client.py` — test parsing new fields

---

## Branch Strategy

Continue on `feat/tier3-gpio-websocket`, ~4 commits:

1. `fix(backend): use non-daemon thread for disconnect cleanup`
2. `fix(gpio): add wall-clock timeout to recv loop`
3. `feat(gpio): add command/error/memory metrics to HEALTH`
4. `feat(frontend): add reconnection config and state to SocketProvider`

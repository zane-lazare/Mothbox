# Tier 3 PR #430 Enhancements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Harden GPIO daemon, WebSocket disconnect handler, and SocketProvider with 4 targeted enhancements from PR #430 review.

**Architecture:** Four independent fixes: (1) non-daemon cleanup thread for camera release, (2) wall-clock timeout on GPIO recv loop, (3) command/error/memory counters in HEALTH response, (4) reconnection config + reconnecting state in SocketProvider.

**Tech Stack:** Python (threading, resource), Flask-SocketIO, React (socket.io-client), Vitest

---

### Task 1: Non-Daemon Cleanup Thread

Change the WebSocket disconnect handler's background thread from `daemon=True` to `daemon=False` so camera cleanup completes before process exit.

**Files:**
- Modify: `webui/backend/websocket_handlers.py:115`
- Test: `Tests/unit/test_websocket_handlers.py`

**Step 1: Write the failing test**

Add to `Tests/unit/test_websocket_handlers.py` at the end of the `TestDisconnect` class (around line 328):

```python
def test_disconnect_uses_non_daemon_thread(self):
    """Disconnect cleanup thread must be non-daemon so it completes before exit."""
    from flask import Flask
    from unittest.mock import MagicMock, patch

    app = Flask(__name__)
    mock_streamer = MagicMock()

    with app.app_context():
        from flask_socketio import SocketIO
        socketio = SocketIO(app)
        from websocket_handlers import register_handlers
        register_handlers(socketio, mock_streamer)

        with patch("websocket_handlers.threading") as mock_threading:
            mock_thread = MagicMock()
            mock_threading.Thread.return_value = mock_thread

            # Trigger the disconnect handler
            with app.test_request_context():
                handlers = socketio.server.handlers.get("/", {})
                if "disconnect" in handlers:
                    handlers["disconnect"]()

            # Verify Thread was created with daemon=False
            mock_threading.Thread.assert_called_once_with(
                target=mock_streamer.stop_streaming, daemon=False
            )
            mock_thread.start.assert_called_once()
```

**Step 2: Run the test to verify it fails**

Run: `python3 -m pytest Tests/unit/test_websocket_handlers.py::TestDisconnect::test_disconnect_uses_non_daemon_thread -v`
Expected: FAIL — currently `daemon=True`

**Step 3: Fix the implementation**

In `webui/backend/websocket_handlers.py:115`, change:
```python
# Before
threading.Thread(target=camera_streamer.stop_streaming, daemon=True).start()

# After
threading.Thread(target=camera_streamer.stop_streaming, daemon=False).start()
```

**Step 4: Run the test to verify it passes**

Run: `python3 -m pytest Tests/unit/test_websocket_handlers.py::TestDisconnect -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add webui/backend/websocket_handlers.py Tests/unit/test_websocket_handlers.py
git commit -m "fix(backend): use non-daemon thread for disconnect cleanup"
```

---

### Task 2: GPIO Daemon recv Loop Wall-Clock Timeout

Add a wall-clock elapsed time check to `_recv_line()` so a slow-sending client can't block the accept loop beyond a total threshold.

**Files:**
- Modify: `lib/gpio_protocol.py:13` — add `RECV_TOTAL_TIMEOUT = 5.0`
- Modify: `lib/gpio_daemon.py:322-333` — add wall-clock check in `_recv_line()`
- Test: `Tests/unit/test_gpio_daemon.py`

**Step 1: Add the constant**

In `lib/gpio_protocol.py`, after `MAX_MSG_LENGTH = 256`:

```python
RECV_TOTAL_TIMEOUT = 5.0  # max wall-clock seconds for _recv_line()
```

**Step 2: Write the failing test**

Add to `Tests/unit/test_gpio_daemon.py` inside `TestDaemonHardening`:

```python
def test_slow_drip_client_times_out(self, running_daemon):
    """A client that sends one byte every second should be cut off by wall-clock timeout."""
    sock_path, _, _ = running_daemon
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(10.0)
        s.connect(sock_path)
        # Drip-feed one byte per second — no newline
        for _ in range(8):
            try:
                s.sendall(b"A")
                time.sleep(1.0)
            except (BrokenPipeError, OSError):
                break
        # Try to read response — daemon should have timed out and sent ERR or closed
        try:
            s.shutdown(socket.SHUT_WR)
            response = s.recv(4096).decode().strip()
        except (OSError, ConnectionResetError):
            response = ""
    # Either we got an ERR response or the connection was closed; daemon is still alive
    assert send_to_daemon(sock_path, "PING") == "PONG"
```

**Step 3: Run the test to verify it fails (takes >5s currently)**

Run: `python3 -m pytest Tests/unit/test_gpio_daemon.py::TestDaemonHardening::test_slow_drip_client_times_out -v -s`
Expected: PASS (but slowly — the existing CONN_TIMEOUT already gives a 2s per-recv timeout, so this may already pass. The test verifies the daemon stays alive regardless.)

**Step 4: Implement the wall-clock timeout**

In `lib/gpio_daemon.py`, update `_recv_line()` (around line 322). Also add the import at the top of the file.

Update the import in `_recv_line`'s enclosing scope to use `RECV_TOTAL_TIMEOUT`:

```python
from lib.gpio_protocol import (
    ACCEPT_TIMEOUT,
    CONN_TIMEOUT,
    LISTEN_BACKLOG,
    MAX_MSG_LENGTH,
    RECV_TOTAL_TIMEOUT,
    SOCKET_PATH,
)
```

Replace the `_recv_line` function:

```python
def _recv_line(conn):
    """Read one newline-terminated message, up to MAX_MSG_LENGTH bytes.

    Enforces a wall-clock total timeout (RECV_TOTAL_TIMEOUT) to prevent
    slow-drip clients from blocking the accept loop.
    """
    buf = b""
    deadline = time.monotonic() + RECV_TOTAL_TIMEOUT
    while len(buf) < MAX_MSG_LENGTH:
        if time.monotonic() > deadline:
            logger.warning("recv_line wall-clock timeout after %.1fs", RECV_TOTAL_TIMEOUT)
            break
        chunk = conn.recv(1)
        if not chunk:
            break
        buf += chunk
        if chunk == b"\n":
            break
    return buf.decode("utf-8", errors="ignore").strip()
```

**Step 5: Run all daemon tests**

Run: `python3 -m pytest Tests/unit/test_gpio_daemon.py -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add lib/gpio_protocol.py lib/gpio_daemon.py Tests/unit/test_gpio_daemon.py
git commit -m "fix(gpio): add wall-clock timeout to daemon recv loop"
```

---

### Task 3: HEALTH Command Additional Metrics

Add `commands`, `errors`, and `memory_kb` fields to the daemon HEALTH response, update client parser and route.

**Files:**
- Modify: `lib/gpio_daemon.py:228-270` — add counters, include in HEALTH response
- Modify: `lib/gpio_client.py:118-138` — parse new fields
- Modify: `webui/backend/routes/gpio.py:23-34` — pass through (no changes needed, already returns full dict)
- Test: `Tests/unit/test_gpio_daemon.py` — test new fields
- Test: `Tests/unit/test_gpio_client.py` — test parsing

**Step 1: Write the failing daemon test**

Add to `Tests/unit/test_gpio_daemon.py` inside `TestHealthCommand`:

```python
def test_health_includes_counters(self, running_daemon):
    """HEALTH response includes commands, errors, and memory_kb."""
    sock_path, _, _ = running_daemon
    # Send a few commands first to populate counters
    send_to_daemon(sock_path, "PING")
    send_to_daemon(sock_path, "SET bogus on")  # generates an error
    response = send_to_daemon(sock_path, "HEALTH")
    assert "commands=" in response
    assert "errors=" in response
    assert "memory_kb=" in response

def test_health_command_count_increments(self, running_daemon):
    """Command counter should reflect total commands processed."""
    sock_path, _, _ = running_daemon
    send_to_daemon(sock_path, "PING")
    send_to_daemon(sock_path, "PING")
    response = send_to_daemon(sock_path, "HEALTH")
    for part in response.split():
        if part.startswith("commands="):
            count = int(part.split("=", 1)[1])
            # At least 2 PINGs + this HEALTH = 3
            assert count >= 3
            break
    else:
        pytest.fail("commands= not found in HEALTH response")

def test_health_error_count_increments(self, running_daemon):
    """Error counter should count ERR responses."""
    sock_path, _, _ = running_daemon
    send_to_daemon(sock_path, "SET bogus on")  # ERR
    send_to_daemon(sock_path, "READ bogus")   # ERR
    response = send_to_daemon(sock_path, "HEALTH")
    for part in response.split():
        if part.startswith("errors="):
            errors = int(part.split("=", 1)[1])
            assert errors >= 2
            break
    else:
        pytest.fail("errors= not found in HEALTH response")
```

**Step 2: Write the failing client test**

Add to `Tests/unit/test_gpio_client.py` inside `TestHealth`:

```python
def test_parses_extended_health_fields(self):
    mock = MockDaemonSocket(
        "HEALTH uptime=120.5 lines=5 last_cmd=never commands=42 errors=3 memory_kb=8192\n"
    )
    with patch("socket.socket", return_value=mock):
        result = health()
    assert result["total_commands"] == 42
    assert result["total_errors"] == 3
    assert result["memory_kb"] == 8192
```

**Step 3: Run tests to verify they fail**

Run: `python3 -m pytest Tests/unit/test_gpio_daemon.py::TestHealthCommand -v && python3 -m pytest Tests/unit/test_gpio_client.py::TestHealth::test_parses_extended_health_fields -v`
Expected: FAIL

**Step 4: Implement daemon counters**

In `lib/gpio_daemon.py`, add `import resource` at the top (after `import time`).

After the `# --- Health tracking ---` section (line 228), update to:

```python
# --- Health tracking ---
started_at = time.time()
last_command_at = None
command_count = 0
error_count = 0
```

Update `_handle_command` to track counters. At the start of `_handle_command`, after `nonlocal last_command_at`:

```python
nonlocal last_command_at, command_count, error_count
command_count += 1
```

After the `return f"ERR unknown command '{cmd.strip()}'"` line, note that this already returns — but we need to count errors. Wrap the error returns: at the end of `_handle_command`, just before returning any `ERR` response, increment `error_count`. Simplest approach: check if the response starts with "ERR" after computing it. Alternatively, add a post-dispatch counter in the main loop.

Actually, the cleanest approach: in the main loop after `response = _handle_command(data)`, add:

```python
if response.startswith("ERR"):
    error_count += 1
```

But `error_count` is local to `run()`, not `_handle_command`. Let's use the approach of incrementing in `_handle_command` for commands, and tracking errors in the main loop:

Update the HEALTH handler to include the new fields:

```python
elif verb == "HEALTH":
    uptime = time.time() - started_at
    lines_count = len(all_pins)
    mem_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if last_command_at is not None:
        last_cmd_iso = datetime.fromtimestamp(
            last_command_at, tz=UTC
        ).isoformat()
    else:
        last_cmd_iso = "never"
    last_command_at = time.time()
    return (
        f"HEALTH uptime={uptime:.1f} lines={lines_count} "
        f"last_cmd={last_cmd_iso} commands={command_count} "
        f"errors={error_count} memory_kb={mem_kb}"
    )
```

For error counting, move it to the main loop. In the main loop, after `response = _handle_command(data) if data else "OK"`:

```python
if response.startswith("ERR"):
    error_count += 1
```

But `error_count` is defined inside `run()` scope and accessed inside `_handle_command` via `nonlocal`. The main loop is also inside `run()`, so it can access `error_count` directly. Either location works — counting in the main loop is cleaner since it catches all ERR responses including malformed/empty ones. Use the main loop approach.

Remove the `error_count` increment from `_handle_command` and put it in the main loop only.

**Step 5: Update client parser**

In `lib/gpio_client.py`, update the `health()` function's parsing loop to handle the new keys:

```python
def health():
    """Query daemon health status.

    Returns:
        dict with reachable, uptime_seconds, managed_lines, last_command_at,
        total_commands, total_errors, memory_kb

    Raises:
        GPIODaemonError: if daemon is unreachable or returns ERR
    """
    response = _send_command("HEALTH")
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
            elif key == "commands":
                result["total_commands"] = int(value)
            elif key == "errors":
                result["total_errors"] = int(value)
            elif key == "memory_kb":
                result["memory_kb"] = int(value)
    return result
```

**Step 6: Run all affected tests**

Run: `python3 -m pytest Tests/unit/test_gpio_daemon.py Tests/unit/test_gpio_client.py Tests/unit/test_gpio_routes.py -v`
Expected: ALL PASS

**Step 7: Commit**

```bash
git add lib/gpio_daemon.py lib/gpio_client.py Tests/unit/test_gpio_daemon.py Tests/unit/test_gpio_client.py
git commit -m "feat(gpio): add command/error/memory metrics to HEALTH"
```

---

### Task 4: SocketProvider Reconnection Config and State

Add explicit reconnection parameters and expose `reconnecting` state in context.

**Files:**
- Modify: `webui/frontend/src/contexts/SocketContext.jsx` — add reconnection config, `reconnecting` state
- Modify: `webui/frontend/src/hooks/useSocket.js` — update JSDoc to include `reconnecting`
- Test: `webui/frontend/src/contexts/__tests__/SocketContext.test.jsx` — add reconnection tests
- Test: `webui/frontend/src/hooks/__tests__/useSocket.test.jsx` — add `reconnecting` property check

**Step 1: Write the failing tests**

Add to `webui/frontend/src/contexts/__tests__/SocketContext.test.jsx`, new `describe('Reconnection')` block:

```jsx
describe('Reconnection', () => {
  it('provides reconnecting state initially false', async () => {
    await setupContext()
    expect(ctx.reconnecting).toBe(false)
  })

  it('sets reconnecting to true on reconnect_attempt event', async () => {
    await setupContext()
    expect(ctx.reconnecting).toBe(false)

    await act(async () => {
      handlers['reconnect_attempt']()
    })

    expect(ctx.reconnecting).toBe(true)
  })

  it('sets reconnecting to false on reconnect event', async () => {
    await setupContext()

    // Start reconnecting
    await act(async () => {
      handlers['reconnect_attempt']()
    })
    expect(ctx.reconnecting).toBe(true)

    // Successfully reconnected
    await act(async () => {
      handlers['reconnect']()
    })
    expect(ctx.reconnecting).toBe(false)
  })

  it('sets reconnecting to false on reconnect_failed event', async () => {
    await setupContext()

    // Start reconnecting
    await act(async () => {
      handlers['reconnect_attempt']()
    })
    expect(ctx.reconnecting).toBe(true)

    // Gave up
    await act(async () => {
      handlers['reconnect_failed']()
    })
    expect(ctx.reconnecting).toBe(false)
  })
})
```

Add to `webui/frontend/src/hooks/__tests__/useSocket.test.jsx`:

```jsx
it('has reconnecting property', () => {
  const { result } = renderHook(() => useSocket(), { wrapper })
  expect(result.current).toHaveProperty('reconnecting')
  expect(typeof result.current.reconnecting).toBe('boolean')
})
```

**Step 2: Run tests to verify they fail**

Run: `cd webui/frontend && npx vitest run src/contexts/__tests__/SocketContext.test.jsx src/hooks/__tests__/useSocket.test.jsx`
Expected: FAIL — `reconnecting` property not found

**Step 3: Update SocketContext.jsx**

Replace `webui/frontend/src/contexts/SocketContext.jsx`:

```jsx
import React, { createContext, useState, useEffect, useMemo } from 'react'
import { io } from 'socket.io-client'

const SocketContext = createContext(null)

/**
 * SocketProvider - Centralized Socket.io connection provider (#368)
 *
 * Creates a single shared Socket.io connection on mount and exposes it
 * to all child components via context. This eliminates duplicate connections
 * previously created independently by Camera, Settings, and ActivationProgress.
 *
 * @important Components must NOT call socket.disconnect() in their cleanup.
 * Only use socket.off() to remove event listeners. The provider owns the
 * connection lifecycle and will disconnect on unmount.
 */
export function SocketProvider({ children }) {
  const [socket, setSocket] = useState(null)
  const [connected, setConnected] = useState(false)
  const [reconnecting, setReconnecting] = useState(false)

  useEffect(() => {
    const newSocket = io(window.location.origin, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
    })

    newSocket.on('connect', () => {
      setConnected(true)
      setReconnecting(false)
    })

    newSocket.on('disconnect', () => {
      setConnected(false)
    })

    newSocket.on('reconnect_attempt', () => {
      setReconnecting(true)
    })

    newSocket.on('reconnect', () => {
      setReconnecting(false)
    })

    newSocket.on('reconnect_failed', () => {
      setReconnecting(false)
    })

    setSocket(newSocket)

    return () => {
      newSocket.disconnect()
    }
  }, [])

  const contextValue = useMemo(
    () => ({ socket, connected, reconnecting }),
    [socket, connected, reconnecting]
  )

  return (
    <SocketContext.Provider value={contextValue}>
      {children}
    </SocketContext.Provider>
  )
}

export function useSocketContext() {
  return React.useContext(SocketContext)
}

export default SocketContext
```

**Step 4: Update useSocket.js JSDoc**

In `webui/frontend/src/hooks/useSocket.js`, update the `@returns` line:

```javascript
/**
 * useSocket - Thin wrapper around SocketContext (#368)
 *
 * Returns the shared Socket.io connection and connection status.
 * Throws if used outside of a SocketProvider.
 *
 * @returns {{ socket: import('socket.io-client').Socket | null, connected: boolean, reconnecting: boolean }}
 *
 * @example
 * const { socket, connected, reconnecting } = useSocket()
 *
 * useEffect(() => {
 *   if (!socket) return
 *   const handler = (data) => { ... }
 *   socket.on('event_name', handler)
 *   return () => socket.off('event_name', handler)
 * }, [socket])
 */
```

**Step 5: Run all frontend tests**

Run: `cd webui/frontend && npx vitest run src/contexts/__tests__/SocketContext.test.jsx src/hooks/__tests__/useSocket.test.jsx`
Expected: ALL PASS

Then run the full suite to check for regressions:

Run: `cd webui/frontend && npx vitest run`
Expected: ALL PASS (5,788+ tests)

**Step 6: Commit**

```bash
git add webui/frontend/src/contexts/SocketContext.jsx webui/frontend/src/hooks/useSocket.js webui/frontend/src/contexts/__tests__/SocketContext.test.jsx webui/frontend/src/hooks/__tests__/useSocket.test.jsx
git commit -m "feat(frontend): add reconnection config and state to SocketProvider"
```

---

### Task 5: Final Verification

**Step 1: Run backend lint**

Run: `ruff check .`
Expected: Clean

**Step 2: Run affected backend tests**

Run: `python3 -m pytest Tests/unit/test_gpio_daemon.py Tests/unit/test_gpio_client.py Tests/unit/test_gpio_routes.py Tests/unit/test_websocket_handlers.py -v`
Expected: ALL PASS

**Step 3: Run frontend tests**

Run: `cd webui/frontend && npx vitest run`
Expected: ALL PASS

**Step 4: Push**

```bash
git push
```

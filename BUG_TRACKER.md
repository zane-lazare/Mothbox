# Mothbox Bug Tracker
**Last Updated:** 2026-06-11  
**Session:** 011CUPZzHtMTxzhfJKWCYoBR

## Status Overview

| Severity | Open | Fixed | Total |
|----------|------|-------|-------|
| 🔴 Critical | 1 | 0 | 1 |
| 🟡 High | 3 | 0 | 3 |
| 🟢 Medium | 6 | 0 | 6 |
| 🟢 Low | 5 | 0 | 5 |
| **TOTAL** | **15** | **0** | **15** |

---

## 🔴 Critical Bugs

### BUG-001: DEBUG Mode Enabled in Production
**Status:** 🔴 Open  
**Severity:** Critical  
**Priority:** P0  
**Discovered:** 2026-06-11

**Location:** `webui/backend/config.py:53,58,74` + `app.py:506`

**Description:**
Flask DEBUG mode can be accidentally enabled in production if `MOTHBOX_ENV` is set to `development`. This enables:
- Interactive debugger accessible via browser
- Verbose logging with sensitive data
- Auto-reloader (performance impact)
- Code execution vulnerability

**Attack Vector:**
1. Set MOTHBOX_ENV=development in production (misconfiguration)
2. Trigger any exception
3. Access Werkzeug debugger console at error page
4. Execute arbitrary Python code

**Risk:** Remote code execution, information disclosure

**Fix:**
```python
# File: webui/backend/config.py
class ProductionConfig(Config):
    DEBUG = False
    
    def __init__(self):
        super().__init__()
        if os.environ.get('MOTHBOX_ENV') == 'production':
            if os.environ.get('FLASK_DEBUG') == '1' or self.DEBUG:
                raise RuntimeError("DEBUG mode not allowed in production!")
```

**Testing:**
```bash
# Verify fix works:
export MOTHBOX_ENV=production
export FLASK_DEBUG=1
python webui/backend/app.py
# Should raise RuntimeError
```

**Estimated Fix Time:** 5 minutes  
**Assignee:** Unassigned

---

## 🟡 High Severity Bugs

### BUG-002: Missing Rate Limit on Camera Calibration
**Status:** 🟡 Open  
**Severity:** High  
**Priority:** P0  
**Discovered:** 2026-06-11

**Location:** `webui/backend/routes/camera.py` (autocalibrate endpoint)

**Description:**
Camera calibration endpoint has no rate limiting. Operation is CPU-intensive with 30-second timeout. Attacker can spam requests to cause CPU exhaustion and DoS.

**Attack Vector:**
```python
# Spam calibration requests
for i in range(100):
    requests.post('http://mothbox:5000/api/camera/calibrate')
# CPU at 100%, device unresponsive
```

**Risk:** Denial of Service, device unusable during attack

**Fix:**
```python
# File: webui/backend/routes/camera.py
@camera_bp.route('/calibrate', methods=['POST'])
@limiter.limit("1 per minute")  # ← Add this line
def auto_calibrate():
    ...
```

**Estimated Fix Time:** 2 minutes  
**Assignee:** Unassigned

---

### BUG-003: Unbounded Error Message Length
**Status:** 🟡 Open  
**Severity:** High  
**Priority:** P1  
**Discovered:** 2026-06-11

**Location:** `webui/backend/routes/camera.py:74`

**Description:**
`ERROR_DETAILS_MAX_LENGTH = 500` is defined but not consistently enforced. Large stderr output from subprocess calls could:
- DOS logs (fill disk)
- DOS API responses (huge JSON payloads)
- Leak sensitive information from stack traces

**Risk:** Information disclosure, log exhaustion, DoS

**Fix:**
```python
# File: webui/backend/routes/camera.py
def truncate_error(stderr: str) -> str:
    """Truncate error messages to prevent log/response DOS"""
    if len(stderr) > ERROR_DETAILS_MAX_LENGTH:
        return stderr[:ERROR_DETAILS_MAX_LENGTH] + "... (truncated)"
    return stderr

# Use consistently:
error_msg = truncate_error(result.stderr)
return error_response(SERVER_ERROR, error_msg, 500)
```

**Estimated Fix Time:** 30 minutes (apply consistently)  
**Assignee:** Unassigned

---

### BUG-004: Camera Lock Has No Timeout
**Status:** 🟡 Open  
**Severity:** High  
**Priority:** P1  
**Discovered:** 2026-06-11

**Location:** `webui/backend/liveview_stream.py:97`

**Description:**
Global `CAMERA_OPERATION_LOCK = Lock()` has no timeout. If thread crashes while holding lock, all camera operations block indefinitely.

**Scenario:**
1. Thread A acquires lock
2. Thread A crashes/deadlocks before release
3. All camera operations block forever
4. Device requires restart

**Risk:** Device deadlock, requires physical restart

**Fix:**
```python
# File: webui/backend/liveview_stream.py
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

@contextmanager
def camera_lock(timeout=30, operation="unknown"):
    """Acquire camera lock with timeout and tracking"""
    acquired = CAMERA_OPERATION_LOCK.acquire(timeout=timeout)
    if not acquired:
        logger.error(f"Camera lock timeout after {timeout}s for: {operation}")
        raise TimeoutError(f"Camera lock timeout after {timeout}s for: {operation}")
    try:
        logger.debug(f"Camera lock acquired for: {operation}")
        yield
    finally:
        CAMERA_OPERATION_LOCK.release()
        logger.debug(f"Camera lock released for: {operation}")

# Usage:
with camera_lock(timeout=30, operation="photo_capture"):
    camera.capture_file(filename)
```

**Estimated Fix Time:** 2-4 hours (refactor all lock usages)  
**Assignee:** Unassigned

---

## 🟢 Medium Severity Bugs

### BUG-005: Exception Handling Too Broad
**Status:** 🟢 Open  
**Severity:** Medium  
**Priority:** P1  
**Discovered:** 2026-06-11

**Location:** Multiple files (25+ instances in `routes/camera.py`)

**Description:**
Broad `except Exception` catches `KeyboardInterrupt` and `SystemExit`, making graceful shutdown difficult. Best practice is to catch specific exceptions.

**Bad:**
```python
try:
    camera.start()
except Exception as e:  # Catches KeyboardInterrupt!
    logger.error(f"Error: {e}")
```

**Good:**
```python
try:
    camera.start()
except (RuntimeError, OSError, ValueError) as e:
    logger.error(f"Error: {e}")
```

**Risk:** Difficult process termination, swallowed keyboard interrupts

**Estimated Fix Time:** 4-8 hours  
**Assignee:** Unassigned

---

### BUG-006: Scheduler Activation Progress Race
**Status:** 🟢 Open  
**Severity:** Medium  
**Priority:** P2  
**Discovered:** 2026-06-11

**Location:** `webui/backend/services/scheduler_service.py:110-119`

**Description:**
WebSocket activation progress updates have no sequence numbers. Client may receive updates out of order:
```
Phase: APPLYING_CRON (60%)
Phase: GENERATING_CRON (30%)  ← Out of order!
```

**Risk:** Confusing UI progress indicators

**Fix:**
```python
def emit_progress(phase, progress, sequence_num):
    socketio.emit('activation_progress', {
        'phase': phase,
        'progress': progress,
        'sequence': sequence_num,
        'timestamp': time.time()
    })
```

**Estimated Fix Time:** 2 hours  
**Assignee:** Unassigned

---

### BUG-007: Metadata Cache TOCTOU Race
**Status:** 🟢 Open  
**Severity:** Medium  
**Priority:** P2  
**Discovered:** 2026-06-11

**Location:** `webui/backend/services/metadata_cache.py`

**Description:**
Code comment states "Note: _l2_lock must be held by caller to prevent TOCTOU bugs" but this is not enforced. If caller forgets to hold lock, race condition occurs.

**Risk:** Data corruption in cache during concurrent access

**Fix:**
```python
def requires_lock(lock_name):
    """Decorator to enforce lock is held"""
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            lock = getattr(self, lock_name)
            if not lock.locked():
                raise RuntimeError(f"{func.__name__} requires {lock_name} to be held")
            return func(self, *args, **kwargs)
        return wrapper
    return decorator

@requires_lock('_l2_lock')
def _evict_entry(self, key):
    # Now enforced at runtime
    ...
```

**Estimated Fix Time:** 2 hours  
**Assignee:** Unassigned

---

### BUG-008: Disconnect Handler Race
**Status:** 🟢 Open  
**Severity:** Medium  
**Priority:** P1  
**Discovered:** 2026-06-11

**Location:** `webui/backend/websocket_handlers.py:107-115`

**Description:**
WebSocket disconnect handler uses `daemon=False` thread without exception handling. If process terminates during camera cleanup, resource leak occurs.

**Current:**
```python
@socketio.on("disconnect")
def handle_disconnect():
    threading.Thread(target=camera_streamer.stop_streaming, daemon=False).start()
```

**Risk:** Resource leak, camera not released on crash

**Fix:**
```python
@socketio.on("disconnect")
def handle_disconnect():
    def cleanup_camera():
        try:
            camera_streamer.stop_streaming()
        except Exception as e:
            logger.error(f"Error during camera cleanup: {e}")
    
    threading.Thread(target=cleanup_camera, daemon=True).start()
```

**Estimated Fix Time:** 10 minutes  
**Assignee:** Unassigned

---

### BUG-009: WebSocket Error Logging
**Status:** 🟢 Open  
**Severity:** Medium  
**Priority:** P1  
**Discovered:** 2026-06-11

**Location:** `webui/backend/websocket_handlers.py:119-146`

**Description:**
WebSocket handlers use `print()` instead of `logger.error()`. Also, raw exception messages sent to client (information disclosure).

**Current:**
```python
except Exception as e:
    print(f"Error starting live view: {e}")  # Wrong
    emit("liveview_status", {"error": str(e)})  # Info disclosure
```

**Risk:** Missing logs, information disclosure to client

**Fix:**
```python
except Exception as e:
    logger.exception("Error starting live view")
    emit("liveview_status", {
        "streaming": False,
        "error": "Camera initialization failed"
    })
```

**Estimated Fix Time:** 10 minutes  
**Assignee:** Unassigned

---

### BUG-010: Navigation Component Duplication
**Status:** 🟢 Open  
**Severity:** Medium (Code Quality)  
**Priority:** P3  
**Discovered:** 2026-06-11

**Location:** `webui/frontend/src/App.jsx:46-128`

**Description:**
NavLink active styling repeated 8 times with identical logic. DRY violation.

**Risk:** Maintenance burden, styling inconsistencies

**Fix:**
```jsx
const NavItem = ({ to, children }) => (
  <NavLink
    to={to}
    className={({ isActive }) =>
      `inline-flex items-center px-3 py-2 text-sm font-medium ${
        isActive
          ? 'text-blue-600 border-b-2 border-blue-600'
          : 'text-gray-600 hover:text-gray-900'
      }`
    }
  >
    {children}
  </NavLink>
);
```

**Estimated Fix Time:** 30 minutes  
**Assignee:** Unassigned

---

## 🟢 Low Severity Bugs

### BUG-011: Duplicate Gallery Directories
**Status:** 🟢 Open  
**Severity:** Low  
**Priority:** P2  
**Discovered:** 2026-06-11

**Location:** `webui/frontend/src/components/`

**Description:**
Both `Gallery/` and `gallery/` directories exist. On Linux (case-sensitive), these are separate. On macOS/Windows (case-insensitive), causes confusion.

**Risk:** Cross-platform development issues, git checkout problems

**Fix:**
```bash
# Standardize on lowercase
git mv src/components/Gallery src/components/gallery_temp
git mv src/components/gallery_temp src/components/gallery
```

**Estimated Fix Time:** 5 minutes  
**Assignee:** Unassigned

---

### BUG-012: GPIO Validation Integer Overflow
**Status:** 🟢 Open  
**Severity:** Low  
**Priority:** P3  
**Discovered:** 2026-06-11

**Location:** `install_mothbox.sh:52-63`

**Description:**
Regex `^[0-9]+$` accepts arbitrarily large numbers like `999999999999999`. Bash integer comparison `-lt 2` could fail with very large numbers (integer overflow on 32-bit systems).

**Risk:** Installation script failure on edge case input

**Fix:**
```bash
if ! [[ "$pin" =~ ^[0-9]{1,2}$ ]]; then  # Max 2 digits
    echo "Error: GPIO pin must be 1-2 digit number (2-27)"
    return 1
fi
```

**Estimated Fix Time:** 2 minutes  
**Assignee:** Unassigned

---

### BUG-013: subprocess.run Missing check=False
**Status:** 🟢 Open  
**Severity:** Low  
**Priority:** P3  
**Discovered:** 2026-06-11

**Location:** `webui/backend/routes/gps_exif.py:138-144`

**Description:**
`subprocess.run()` for systemctl status check doesn't explicitly set `check=False`. Could raise `CalledProcessError` if service not found (though caught by outer try/except).

**Risk:** Unexpected exception if service doesn't exist

**Fix:**
```python
result = subprocess.run(
    ["systemctl", "is-active", "gps-exif-tagger"],
    capture_output=True,
    text=True,
    timeout=5,
    check=False,  # ← Add explicit check=False
)
```

**Estimated Fix Time:** 1 minute  
**Assignee:** Unassigned

---

### BUG-014: Preset Manager Type Cache Memory Leak
**Status:** 🟢 Open  
**Severity:** Low  
**Priority:** P3  
**Discovered:** 2026-06-11

**Location:** `webui/backend/preset_manager.py:47,72,126`

**Description:**
Type derivation cache (`_type_cache`) has no size limit or TTL. If dynamic settings are added at runtime, unbounded growth possible.

**Risk:** Memory leak over long runtime

**Fix:**
```python
from functools import lru_cache

@lru_cache(maxsize=256)
def _derive_type_cached(self, setting_type: str, key: str) -> type | None:
    # Use LRU cache with eviction instead of unbounded dict
    ...
```

**Estimated Fix Time:** 30 minutes  
**Assignee:** Unassigned

---

### BUG-015: Orphaned Temp Files
**Status:** 🟢 Open  
**Severity:** Low  
**Priority:** P3  
**Discovered:** 2026-06-11

**Location:** `webui/backend/services/sidecar_service.py`

**Description:**
Atomic write pattern uses temp files (`.json.tmp`). If process crashes between write and rename, orphaned `.tmp` files accumulate.

**Risk:** Disk space waste over time

**Fix:**
```python
def __init__(self, photos_dir):
    self.photos_dir = photos_dir
    self._cleanup_temp_files()

def _cleanup_temp_files(self):
    """Remove orphaned .tmp files older than 1 hour"""
    import time
    cutoff = time.time() - 3600
    for tmp_file in self.photos_dir.rglob("*.json.tmp"):
        if tmp_file.stat().st_mtime < cutoff:
            tmp_file.unlink(missing_ok=True)
```

**Estimated Fix Time:** 30 minutes  
**Assignee:** Unassigned

---

## Bug Statistics

### By Component

| Component | Critical | High | Medium | Low | Total |
|-----------|----------|------|--------|-----|-------|
| Backend/Config | 1 | 0 | 0 | 0 | 1 |
| Backend/Routes | 0 | 2 | 2 | 1 | 5 |
| Backend/Services | 0 | 0 | 3 | 2 | 5 |
| Backend/Streaming | 0 | 1 | 1 | 0 | 2 |
| Frontend/App | 0 | 0 | 1 | 1 | 2 |
| **TOTAL** | **1** | **3** | **6** | **5** | **15** |

### Estimated Fix Time

| Severity | Total Time |
|----------|------------|
| Critical | 5 minutes |
| High | 3-5 hours |
| Medium | 9-15 hours |
| Low | 2-3 hours |
| **TOTAL** | **14-23 hours** |

---

## Tracking

**Report Created:** 2026-06-11  
**Session ID:** 011CUPZzHtMTxzhfJKWCYoBR  
**Reviewer:** Claude (Sonnet 4.5)  
**Next Review:** After authentication implementation (Issue #19)

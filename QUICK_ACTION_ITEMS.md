# Quick Action Items - Mothbox Code Review
**Date:** 2026-06-11  
**Priority:** Immediate fixes that can be done in < 1 hour

---

## 🚨 5-Minute Fixes (Do Right Now)

### 1. Fix DEBUG Mode in Production (BUG-001) - 5 minutes
```python
# File: webui/backend/config.py
class ProductionConfig(Config):
    DEBUG = False
    
    def __init__(self):
        super().__init__()
        # CRITICAL: Prevent DEBUG in production
        if os.environ.get('MOTHBOX_ENV') == 'production':
            if os.environ.get('FLASK_DEBUG') == '1' or self.DEBUG:
                raise RuntimeError("🚨 DEBUG mode not allowed in production!")
```

**Test:**
```bash
export MOTHBOX_ENV=production
export FLASK_DEBUG=1
python webui/backend/app.py  # Should fail with RuntimeError
```

---

### 2. Add Calibration Rate Limit (BUG-002) - 2 minutes
```python
# File: webui/backend/routes/camera.py
# Find the autocalibrate function and add decorator:

@camera_bp.route('/calibrate', methods=['POST'])
@limiter.limit("1 per minute")  # ← ADD THIS LINE
def auto_calibrate():
    """Auto-calibrate camera (rate-limited to prevent DoS)"""
    ...
```

**Test:**
```bash
# Should allow 1 request, then block subsequent requests for 60 seconds
curl -X POST http://localhost:5000/api/camera/calibrate
curl -X POST http://localhost:5000/api/camera/calibrate  # Should be rate limited
```

---

### 3. Fix WebSocket Error Logging (BUG-009) - 1 minute
```python
# File: webui/backend/websocket_handlers.py
# Line ~133, change from:
except Exception as e:
    print(f"Error starting live view: {e}")
    emit("liveview_status", {"streaming": False, "error": str(e)})

# To:
except Exception as e:
    logger.exception("Error starting live view")  # ← Use logger
    emit("liveview_status", {
        "streaming": False, 
        "error": "Camera initialization failed"  # ← Generic message
    })
```

---

### 4. Fix GPIO Validation (BUG-012) - 2 minutes
```bash
# File: install_mothbox.sh
# Line ~53, change from:
if ! [[ "$pin" =~ ^[0-9]+$ ]]; then

# To:
if ! [[ "$pin" =~ ^[0-9]{1,2}$ ]]; then  # ← Max 2 digits
```

---

### 5. Fix Duplicate Gallery Directory (BUG-011) - 5 minutes
```bash
# In repository root:
cd webui/frontend/src/components/

# Check if both exist:
ls -ld Gallery gallery

# If both exist, standardize on lowercase:
git mv Gallery Gallery_old
git mv Gallery_old gallery
git commit -m "fix: standardize Gallery directory to lowercase"
```

---

## ⚡ 10-30 Minute Fixes (Do Today)

### 6. Fix Disconnect Handler (BUG-008) - 10 minutes
```python
# File: webui/backend/websocket_handlers.py
# Replace handle_disconnect with:

@socketio.on("disconnect")
def handle_disconnect():
    """Handle client disconnect with proper error handling"""
    def cleanup_camera():
        try:
            camera_streamer.stop_streaming()
        except Exception as e:
            logger.error(f"Error during camera cleanup: {e}")
    
    # Use daemon=True so thread dies with process
    threading.Thread(target=cleanup_camera, daemon=True).start()
```

---

### 7. Add subprocess check=False (BUG-013) - 1 minute
```python
# File: webui/backend/routes/gps_exif.py
# Line ~138, add check=False:

result = subprocess.run(
    ["systemctl", "is-active", "gps-exif-tagger"],
    capture_output=True,
    text=True,
    timeout=5,
    check=False,  # ← ADD THIS
)
```

---

### 8. Extract NavItem Component (BUG-010) - 30 minutes
```jsx
// File: webui/frontend/src/components/common/NavItem.jsx
// Create new file:

export const NavItem = ({ to, children }) => (
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

// File: webui/frontend/src/App.jsx
// Replace 8 NavLink blocks with:
import { NavItem } from './components/common/NavItem'

<NavItem to="/">Dashboard</NavItem>
<NavItem to="/gallery">Gallery</NavItem>
<NavItem to="/camera">Camera</NavItem>
// ... etc
```

---

## 📋 Verification Checklist

After applying fixes, verify:

- [ ] `export MOTHBOX_ENV=production && python app.py` → Should fail with DEBUG error
- [ ] Calibration endpoint rate-limited (test with curl)
- [ ] WebSocket errors logged (check logs, not stdout)
- [ ] GPIO validation rejects `999` as invalid
- [ ] Only one `gallery` directory exists (lowercase)
- [ ] WebSocket disconnect doesn't crash on cleanup error
- [ ] systemctl subprocess doesn't raise on missing service
- [ ] NavItem component used in 8 places

---

## 🎯 Today's Goal: 8/15 Bugs Fixed

**Time Required:** ~1 hour total  
**Impact:** Fixes critical security issue + 7 other bugs  
**Remaining:** 7 bugs (longer fixes for later)

---

## 📊 Progress Tracking

### Fixed Today
- [ ] BUG-001 (Critical) - DEBUG mode
- [ ] BUG-002 (High) - Calibration rate limit
- [ ] BUG-008 (Medium) - Disconnect handler
- [ ] BUG-009 (Medium) - WebSocket logging
- [ ] BUG-010 (Medium) - NavItem duplication
- [ ] BUG-011 (Low) - Gallery directory
- [ ] BUG-012 (Low) - GPIO validation
- [ ] BUG-013 (Low) - subprocess check

### Remaining (For Later Sprint)
- [ ] BUG-003 (High) - Error message truncation (30 min)
- [ ] BUG-004 (High) - Camera lock timeout (2-4 hours)
- [ ] BUG-005 (Medium) - Exception handling (4-8 hours)
- [ ] BUG-006 (Medium) - Progress race (2 hours)
- [ ] BUG-007 (Medium) - TOCTOU race (2 hours)
- [ ] BUG-014 (Low) - Type cache leak (30 min)
- [ ] BUG-015 (Low) - Temp file cleanup (30 min)

---

## 🔥 Critical Path Items (Beyond Bugs)

These are NOT bugs but missing features blocking production:

1. **Authentication System** (Issue #19)
   - HTTP Basic Auth minimum
   - Estimated: 40-80 hours
   - **PRODUCTION BLOCKER**

2. **HTTPS Enforcement**
   - Certificate management
   - Redirect HTTP → HTTPS
   - Estimated: 4-8 hours
   - **PRODUCTION BLOCKER**

3. **Complete TypeScript Migration**
   - api.js → api.ts priority
   - Estimated: 60-100 hours
   - Quality improvement

---

## 📝 Commit Message Template

```
fix(security): prevent DEBUG mode in production (BUG-001)

Add runtime check in ProductionConfig to raise RuntimeError if
DEBUG mode or FLASK_DEBUG=1 is set when MOTHBOX_ENV=production.

This prevents accidental exposure of the interactive debugger
which would allow arbitrary code execution.

Severity: Critical
Estimated fix time: 5 minutes
```

---

**Questions?** See full details in:
- `COMPREHENSIVE_CODE_REVIEW_2026-06-11.md` (20KB, complete analysis)
- `BUG_TRACKER.md` (15KB, detailed bug descriptions)

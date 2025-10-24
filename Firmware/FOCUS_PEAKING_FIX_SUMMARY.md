# Focus Peaking Hardware MJPEG Mode Fix

## Issue #50 Analysis and Resolution

### Problem Statement
Focus peaking overlay was not displaying when using hardware MJPEG encoding mode, despite the feature being fully implemented in the backend.

### Root Cause
The issue was in the **frontend frame handling**, not the backend implementation.

#### Backend Implementation (Correct ✅)
The backend correctly implements a **hybrid hardware MJPEG mode**:

1. **Hardware encoder thread**: Streams MJPEG frames at 10 fps (~10% CPU)
   - Emits frames with `focus_peaked: false`

2. **Overlay thread**: Captures raw frames, applies focus peaking, emits at 10 fps
   - Emits frames with `focus_peaked: true`
   - Configurable rate via `focus_peaking_overlay_fps` setting

**Total CPU**: ~10-15% (vs ~40-60% for software-only encoding)

#### Frontend Bug (Fixed ✅)
The frontend was **displaying ALL frames indiscriminately**:

**Before (Broken):**
```javascript
socketRef.current.on('camera_frame', (data) => {
  setCurrentFrame(data.image)  // ❌ Shows both peaked and non-peaked frames
})
```

**Result**: Frames alternated between:
- Hardware frames (no overlay)
- Overlay frames (with focus peaking)

This caused flickering or made the overlay appear intermittent/non-functional.

### Solution Implemented

**File**: `webui/frontend/src/pages/Camera.jsx:208-221`

```javascript
socketRef.current.on('camera_frame', (data) => {
  // When focus peaking is enabled, only display focus-peaked frames
  // to avoid flickering between overlaid and non-overlaid frames
  if (liveControls.focusPeakingEnabled) {
    // Only update with overlaid frames when focus peaking is active
    if (data.focus_peaked) {
      setCurrentFrame(data.image)
    }
    // Ignore non-peaked hardware frames when peaking is enabled
  } else {
    // Show all frames when focus peaking is disabled
    setCurrentFrame(data.image)
  }
})
```

**Logic**:
- **When focus peaking enabled**: Only display frames with `focus_peaked: true`
- **When focus peaking disabled**: Display all frames (normal behavior)

### Testing Instructions

1. **Enable hardware MJPEG mode**:
   - Settings → Stream Settings → Stream Mode: `mjpeg_hardware`

2. **Enable focus peaking**:
   - Camera page → Live Controls → Enable Focus Peaking checkbox
   - Adjust intensity/color/algorithm as desired

3. **Verify overlay appears**:
   - Point camera at object with sharp edges
   - Colored highlights should appear on focused edges
   - Overlay should update smoothly (~10 fps)
   - No flickering between peaked/non-peaked frames

### Expected Behavior

#### Focus Peaking OFF
- Stream shows pure hardware MJPEG frames
- CPU: ~10%
- Framerate: 10 fps
- No overlay visible

#### Focus Peaking ON
- Stream shows only overlay frames (with focus peaking applied)
- CPU: ~10-15%
- Overlay update rate: ~10 fps (configurable via `focus_peaking_overlay_fps`)
- Colored highlights visible on sharp edges
- Smooth, consistent display (no flickering)

### Performance Characteristics

| Mode | CPU Usage | Focus Peaking | Framerate |
|------|-----------|---------------|-----------|
| Hardware MJPEG (pure) | ~10% | ❌ No | 10 fps |
| **Hybrid (fixed)** | **~10-15%** | **✅ Yes** | **10 fps** |
| Software (simplejpeg) | ~40-60% | ✅ Yes | 10 fps |

**Efficiency gain**: 2-4x lower CPU than software encoding

### Related Commits

- `9607780` - feat(focus-peaking): implement real-time focus peaking overlay with 3 edge detection algorithms
- `aeea00e` - fix(focus-peaking): expose focus peaking settings in webui settings API endpoint
- `82997ec` - fix(tests): fix focus peaking integration test failures
- `2c48e64` - fix(focus-peaking): correct color mapping and invert intensity logic
- **[Current]** - fix(focus-peaking): filter frontend frames to display only focus-peaked frames in hybrid mode

### Files Modified

1. ✅ `webui/frontend/src/pages/Camera.jsx` (13 lines added)
   - Updated `camera_frame` event handler to filter frames based on `focus_peaked` flag

### Documentation References

- `FOCUS_PEAKING_CONFIGURATION_INTEGRATION.md` - Configuration system integration
- `Tests/HARDWARE_MJPEG_FOCUS_PEAKING_TEST_PLAN.md` - Comprehensive testing plan

### Additional Notes

#### Why Hybrid Mode?
- **Hardware MJPEG** is very CPU-efficient but provides pre-compressed frames (no raw access)
- **Focus peaking** requires raw frames for OpenCV edge detection
- **Hybrid approach** gets best of both worlds:
  - Main stream uses efficient hardware encoding
  - Overlay thread periodically processes raw frames
  - Total CPU still much lower than software-only encoding

#### Frame Tagging Architecture
All frames emitted via WebSocket include a `focus_peaked` flag:
```javascript
{
  image: "data:image/jpeg;base64,...",
  focus_peaked: true  // or false
}
```

This allows the frontend to intelligently choose which frames to display based on user settings.

### Status

- ✅ Backend implementation complete
- ✅ Frontend frame filtering fixed
- ⏳ Testing required on actual hardware
- ⏳ Issue #50 to be updated and closed after verification

### Next Steps

1. Test on actual Raspberry Pi with camera
2. Verify no flickering or frame drops
3. Confirm CPU usage stays <20%
4. Update issue #50 with resolution
5. Close issue #50 once verified working

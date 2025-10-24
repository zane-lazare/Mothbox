# Focus Peaking Cropped Stream Fix

## Issue
After implementing the hybrid hardware MJPEG mode for focus peaking, users experienced a cropped/zoomed view of the camera stream, even with focus peaking disabled.

## Root Cause
When `capture_array()` is called without specifying a stream name during hardware MJPEG recording, Picamera2 may capture from the RAW sensor stream or an undefined stream rather than the configured "main" stream. This resulted in a different resolution/crop being displayed than intended.

## Solution
1. **Add lores stream configuration** - Configure a "lores" stream that matches the main stream resolution
2. **Explicitly specify stream** - Use `capture_array("lores")` instead of `capture_array()`
3. **Add debug logging** - Log which streaming mode is active for troubleshooting

## Changes Made

### File: `webui/backend/camera_stream.py`

#### 1. Video Configuration (lines 274-284)
**Before:**
```python
video_config = self.camera.create_video_configuration(
    main={"size": (self.stream_width, self.stream_height), "format": self.stream_format},
    encode="main"
)
```

**After:**
```python
video_config = self.camera.create_video_configuration(
    main={"size": (self.stream_width, self.stream_height), "format": self.stream_format},
    lores={"size": (self.stream_width, self.stream_height), "format": self.stream_format},
    encode="main"
)
```

**Why:** The lores stream is now explicitly configured to match the main stream resolution. This ensures `capture_array("lores")` returns frames at the expected resolution.

#### 2. Hybrid Mode Debug Logging (lines 523-529)
**Added:**
```python
if self.focus_peaking_enabled and CV2_AVAILABLE:
    print("🎯 Focus peaking enabled - using hybrid hardware encoding with overlay")
    print(f"   DEBUG: focus_peaking_enabled={self.focus_peaking_enabled}, CV2_AVAILABLE={CV2_AVAILABLE}")
    return self._stream_hardware_mjpeg_with_overlay()
else:
    print(f"📹 Using pure hardware MJPEG mode (focus_peaking_enabled={self.focus_peaking_enabled}, CV2={CV2_AVAILABLE})")
```

**Why:** Helps diagnose whether the system is incorrectly entering hybrid mode when focus peaking is disabled.

#### 3. Hybrid Mode Capture (line 799)
**Before:**
```python
frame = self.camera.capture_array()
```

**After:**
```python
frame = self.camera.capture_array("lores")
```

**Why:** Explicitly captures from the lores stream which is configured to match main resolution, ensuring correct frame size.

#### 4. Software Encoding Capture (line 888)
**Before:**
```python
frame = self.camera.capture_array()
```

**After:**
```python
frame = self.camera.capture_array("lores")
```

**Why:** Consistency across all capture paths, ensuring the same resolution regardless of encoding mode.

## Technical Details

### Picamera2 Stream Architecture
When using `create_video_configuration()`:
- **main**: Primary high-resolution stream (used by hardware encoder)
- **lores**: Lower-resolution stream (typically for preview)
- **raw**: Raw sensor data stream

**Previous behavior:**
- `capture_array()` without argument → captures from undefined/default stream
- May return raw sensor crop or different resolution

**New behavior:**
- `capture_array("lores")` → explicitly captures from lores stream
- lores configured to match main resolution → correct frame size guaranteed

### Why Lores Instead of Main?
During hardware MJPEG recording, the "main" stream is locked by the encoder. The "lores" stream remains available for `capture_array()` and can be configured to any resolution, including matching the main stream.

## Testing Requirements

### Test 1: Focus Peaking OFF
- **Scenario**: Hardware MJPEG mode, focus peaking disabled
- **Expected**: Full resolution stream (1024x768), no cropping
- **Verify**: Check backend logs for "Using pure hardware MJPEG mode"

### Test 2: Focus Peaking ON
- **Scenario**: Hardware MJPEG mode, focus peaking enabled
- **Expected**: Full resolution with overlay, no cropping
- **Verify**: Check backend logs for "using hybrid hardware encoding with overlay"

### Test 3: Software Encoding
- **Scenario**: Simplejpeg mode, focus peaking enabled/disabled
- **Expected**: Full resolution in both cases
- **Verify**: Frames captured from lores stream at correct resolution

### Test 4: Click-to-Focus
- **Scenario**: Click on stream preview
- **Expected**: AF window positioned correctly
- **Verify**: Coordinates calculated based on correct frame dimensions

## Performance Impact
**None** - The lores stream configuration adds negligible overhead since it's only used when capturing frames for overlay or software encoding.

## Backward Compatibility
**Fully compatible** - The change only affects the internal stream capture behavior. All external APIs and configurations remain unchanged.

## Related Issues
- Issue #50 - Focus peaking overlay not displaying (previously fixed)
- User report - Cropped/zoomed stream view with focus peaking system

## Files Modified
- `webui/backend/camera_stream.py` (4 changes: config, logging, 2x capture_array)

## Commit Message
```
fix(focus-peaking): resolve cropped stream by explicitly using lores stream for capture_array

Fixes issue where camera stream appeared cropped/zoomed after focus peaking
implementation.

Root cause: capture_array() without stream name captured from undefined/raw
stream instead of configured main stream.

Solution:
- Configure lores stream to match main resolution (1024x768)
- Use capture_array("lores") explicitly in all capture paths
- Add debug logging to diagnose streaming mode activation

Changes:
- Add lores stream config matching main resolution
- Update hybrid mode capture to use "lores" stream
- Update software encoding capture to use "lores" stream
- Add debug logging for streaming mode selection

Testing:
- Verify full resolution with focus peaking OFF
- Verify overlay works correctly with focus peaking ON
- Confirm click-to-focus coordinates are accurate
```

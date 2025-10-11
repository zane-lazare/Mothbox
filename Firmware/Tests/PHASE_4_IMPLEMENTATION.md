# Phase 4.5 Implementation: Test Capture Endpoint

## Overview

Phase 4.5 implements the test capture endpoint, allowing users to capture full-resolution test photos using their current preview settings without affecting production `camera_settings.csv`.

## Implementation Details

### Backend

**File:** `Firmware/webui/backend/routes/camera.py`

**New Endpoint:** `POST /api/camera/test-capture`

**Features:**
- Loads current preview settings from `webui_settings.txt`
- Releases camera hardware if stream is active (prevents resource conflict)
- Applies preview controls to full-resolution capture (9152x6944)
- Captures test photo to `PHOTOS_DIR/test_captures/`
- Returns metadata (exposure, gain, lens position, color temperature)
- Automatically restarts camera stream after capture
- Comprehensive error handling with traceback

**Settings Applied:**
- Sharpness, Brightness, Contrast, Saturation
- Focus Mode, Speed, Range
- White Balance Enable/Mode

### Frontend

**Files:**
- `Firmware/webui/frontend/src/utils/api.js` - API client function
- `Firmware/webui/frontend/src/pages/Camera.jsx` - UI component

**Features:**
- Prominent "Test Capture" button on Camera page
- Loading state during capture
- Success/error result display with metadata
- Helpful tip about test_captures/ directory
- Indigo color scheme (distinct from other actions)

### Testing

**File:** `Firmware/Tests/unit/test_test_capture.py`

**Test Coverage:** 10 unit tests
1. Endpoint exists
2. Successful test capture
3. Preview settings applied correctly
4. test_captures/ directory created
5. Camera released if streaming
6. Graceful handling without picamera2
7. Metadata returned correctly
8. Defaults used when no settings file
9. AWB mode conditional logic
10. Settings validation

## User Workflow

1. **Adjust Settings** - Modify preview settings in Settings → Stream Settings
2. **Start Preview** - View live camera feed with settings applied
3. **Test Capture** - Click "Test Capture" button on Camera page
4. **Review Results** - Check test_captures/ directory for full-res photo
5. **Verify Metadata** - Review exposure, gain, focus values
6. **Apply to Production** - Use "Preview → Capture" to copy settings
7. **Production Capture** - Use "Capture Photo" for scheduled/manual captures

## API Documentation

### POST /api/camera/test-capture

Capture a full-resolution test photo using current preview settings.

**Request:**
```http
POST /api/camera/test-capture
Content-Type: application/json
```

**Response (Success):**
```json
{
  "success": true,
  "test_photo_path": "test_captures/test_capture_20251012_143022.jpg",
  "settings_used": {
    "Sharpness": 1.5,
    "Brightness": 0.0,
    "Contrast": 1.0,
    "Saturation": 1.0,
    "AfMode": 2,
    "AfSpeed": 0,
    "AfRange": 0,
    "AwbEnable": true
  },
  "metadata": {
    "exposure_time": 7234,
    "analogue_gain": 2.1,
    "lens_position": 7.84,
    "colour_temperature": 5200
  },
  "timestamp": 1728704422.123,
  "message": "Test capture saved to test_captures/test_capture_20251012_143022.jpg"
}
```

**Response (Error):**
```json
{
  "success": false,
  "error": "Error message",
  "traceback": "Full Python traceback..."
}
```

## File Structure

```
PHOTOS_DIR/
├── test_captures/                    # Test photos (Phase 4.5)
│   ├── test_capture_20251012_143022.jpg
│   ├── test_capture_20251012_143145.jpg
│   └── ...
├── YYYYMMDD/                        # Production captures
│   ├── YYYYMMDD_HHMMSS.jpg
│   └── ...
└── ...
```

## Safety Features

1. **Non-Destructive** - Does not modify `camera_settings.csv`
2. **Resource Management** - Properly releases/restarts camera stream
3. **Error Recovery** - Ensures camera stream restarts even on error
4. **Separate Directory** - Test photos isolated in test_captures/
5. **Metadata Tracking** - Full capture metadata for analysis

## Performance

- **Capture Time:** <5 seconds (includes camera init, stabilization, capture)
- **Resolution:** 9152x6944 (64MP full resolution)
- **Stream Restart:** Automatic after capture completion
- **Resource Cleanup:** Guaranteed via try/finally blocks

## Integration

### With Existing Features

- **Preview Settings:** Reads from `webui_settings.txt`
- **Camera Stream:** Releases hardware before capture, restarts after
- **Settings Copy:** Test photos help verify before copying preview→capture
- **Autofocus/Calibration:** Can use test capture to verify results

### With TakePhoto.py

- Test captures use **different settings** (preview) than TakePhoto.py (capture)
- Production `camera_settings.csv` remains unchanged
- No interference with scheduled captures
- Test directory separate from production photos

## Known Limitations

1. **Hardware Availability:** Requires picamera2 library
2. **Resolution:** Fixed at 9152x6944 (camera maximum)
3. **Format:** JPEG only (not configurable)
4. **Stream Interruption:** Camera preview pauses during test capture (~3-5 sec)

## Future Enhancements (Not in Phase 4.5)

1. Configurable test resolution
2. RAW format test captures
3. Comparison view (test vs production)
4. Test capture history/gallery
5. Apply test capture metadata to settings

## Success Criteria

✅ Test capture endpoint implemented and functional
✅ Preview settings correctly applied to full-res capture
✅ test_captures/ directory created automatically
✅ Production camera_settings.csv unaffected
✅ Camera stream auto-restarts after capture
✅ Comprehensive error handling and recovery
✅ 10 unit tests passing
✅ Frontend UI intuitive and informative
✅ Documentation complete

## Related Issues

- Issue #43 - Phase 4.5: Test Capture Endpoint
- Related to Phase 2.2 (Autofocus/Calibration endpoints)
- Related to Phase 3.3 (Camera page UI)

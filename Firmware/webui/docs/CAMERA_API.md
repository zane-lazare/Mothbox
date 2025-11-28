# Camera API Documentation

This document describes the camera-related API endpoints for the Mothbox web interface.

## Overview

The Mothbox camera system provides two distinct workflows:
1. **Live View Streaming**: Real-time camera preview with adjustable settings via WebSocket
2. **Photo Capture**: High-resolution photo capture with EXIF metadata and GPS tagging

## Camera Workflows

### Live View Workflow

The live view workflow provides a real-time camera preview at lower resolution (~1024x768) with interactive controls:

- **Purpose**: Preview and adjust camera settings in real-time
- **Transport**: WebSocket (Socket.IO) for low-latency streaming
- **Frame Rate**: ~10 FPS target
- **Controls**: Exposure, gain, focus, white balance, sharpness, etc.
- **Camera Instance**: Runs in-process via `LiveViewStreamer` class

**Important**: The camera can only be used by ONE workflow at a time.

### Photo Capture Workflow

The photo capture workflow creates high-resolution images with full metadata:

- **Purpose**: Production-quality photo capture
- **Resolution**: Up to 3840x2160 (4K) or 9152x6944 (64MP for Arducam OwlSight)
- **Process**: Spawns `TakePhoto.py` subprocess
- **Features**: HDR mode, focus bracketing, EXIF metadata, GPS tagging
- **Save Location**: `{PHOTOS_DIR}/` or `{PHOTOS_DIR}/test_captures/`

## API Endpoints

### Test Capture (Live View Settings)

Captures a 4K test photo using the **current live view camera settings**.

**Endpoint**: `POST /api/camera/test-capture-liveview`

**Request**: No body required

**Response**:
```json
{
  "success": true,
  "test_photo_path": "test_captures/test_2025_01_15__14_30_45_ABC123.jpg",
  "metadata": {
    "exposure_time": 10000,
    "analogue_gain": 8.0,
    "lens_position": 5.2,
    "colour_gains": [1.5, 1.3],
    "sharpness": 1.5,
    "brightness": 0.0,
    "contrast": 1.0,
    "saturation": 1.0,
    "noise_reduction_mode": 2,
    "ae_metering_mode": 0,
    "af_mode": 0,
    "af_range": 0,
    "af_speed": 0
  },
  "timestamp": 1737000000.123
}
```

**Use Case**: Test current live view settings at full resolution before committing to production capture.

**Filename Format**: `test_YYYY_MM_DD__HH_MM_SS_[serial].jpg`

**Save Location**: `{PHOTOS_DIR}/test_captures/`

**Settings Source**: Current `camera_streamer` instance state (live view controls)

**Error Responses**:
- `500`: Camera not available or capture failed
- `400`: Invalid request

---

### Instant Capture

Captures a quick snapshot photo from the live stream using **current camera settings** with full EXIF metadata.

**Endpoint**: `POST /api/camera/instant-capture`

**Request**: No body required (uses current `camera_streamer` settings)

**Response**:
```json
{
  "success": true,
  "photo_path": "test_captures/instant_2025_01_15__14_30_45_ABC123.jpg",
  "metadata": {
    "exposure_time": 10000,
    "analogue_gain": 8.0,
    "lens_position": 5.2,
    "colour_gains": [1.5, 1.3],
    "sharpness": 1.5,
    "brightness": 0.0,
    "contrast": 1.0,
    "saturation": 1.0
  },
  "exif_embedded": true,
  "gps_available": false,
  "timestamp": 1737000000.123,
  "message": "Instant capture saved: instant_2025_01_15__14_30_45_ABC123.jpg"
}
```

**Use Case**: Quick snapshot for testing, documentation, or debugging without interrupting live view.

**Filename Format**: `instant_YYYY_MM_DD__HH_MM_SS_[serial].jpg`

**Save Location**: `{PHOTOS_DIR}/test_captures/`

**Settings Source**: Current `camera_streamer` instance state (live view controls)

**EXIF Metadata**: Full camera metadata embedded in JPEG

**GPS Tagging**: GPS coordinates embedded in EXIF if GPS fix available

**Error Responses**:
- `500`: Camera not available or capture failed
- `400`: Invalid request

---

### Production Capture

Captures a production-quality photo using **saved settings from camera_settings.csv**.

**Endpoint**: `POST /api/camera/capture`

**Request**: No body required

**Response**:
```json
{
  "success": true,
  "latest_photo": "2025_01_15__14_30_45_ABC123.jpg",
  "capture_count": 1,
  "photos": [
    {
      "filename": "2025_01_15__14_30_45_ABC123.jpg",
      "path": "/var/lib/mothbox/photos/2025_01_15__14_30_45_ABC123.jpg",
      "timestamp": 1737000000.123
    }
  ]
}
```

**Use Case**: Production photo capture for monitoring and research.

**Filename Format**: `YYYY_MM_DD__HH_MM_SS_[serial].jpg`

**Save Location**: `{PHOTOS_DIR}/`

**Settings Source**: `camera_settings.csv` file (NOT live view settings)

**Features**:
- Full resolution (9152x6944 for Arducam OwlSight, 3840x2160 for others)
- HDR mode (if enabled in settings)
- Focus bracketing (if enabled in settings)
- GPS EXIF tagging (if GPS available)
- Subprocess-based capture (`TakePhoto.py`)

---

## Test Capture vs Instant Capture Comparison

| Feature | Test Capture | Instant Capture |
|---------|--------------|-----------------|
| **Resolution** | 3840x2160 (4K) | 3840x2160 (4K) |
| **Settings Source** | Live view controls | Live view controls |
| **EXIF Metadata** | Full metadata | Full metadata |
| **GPS Tagging** | Yes (if available) | Yes (if available) |
| **Save Location** | `test_captures/` | `test_captures/` |
| **Filename Prefix** | `test_` | `instant_` |
| **Use Case** | Test live settings at full res | Quick snapshot |
| **UI Location** | Test Capture overlay | Test Capture overlay |

**Both endpoints use identical settings from the live view stream** - the difference is primarily semantic (naming/purpose).

---

## Camera Settings Management

### Get Current Settings (Internal Method)

The `LiveViewStreamer.get_current_settings()` method exports the current camera state for test captures.

**Method**: `LiveViewStreamer.get_current_settings()`

**Returns**: Dictionary with snake_case keys
```python
{
    'exposure_time': 10000,          # microseconds
    'analogue_gain': 8.0,            # gain multiplier
    'lens_position': 5.2,            # diopters
    'colour_gains': (1.5, 1.3),      # (red, blue) gains
    'sharpness': 1.5,                # 0.0-2.0
    'brightness': 0.0,               # -1.0 to 1.0
    'contrast': 1.0,                 # 0.0-2.0
    'saturation': 1.0,               # 0.0-2.0
    'noise_reduction_mode': 2,       # 0=Off, 1=Fast, 2=High Quality
    'ae_metering_mode': 0,           # 0=Centre, 1=Spot, 2=Matrix
    'af_mode': 0,                    # 0=Manual, 1=Auto, 2=Continuous
    'af_range': 0,                   # 0=Normal, 1=Macro, 2=Full
    'af_speed': 0                    # 0=Normal, 1=Fast
}
```

**Use Case**: Called internally by test capture endpoints to get settings snapshot

**Error Handling**: Returns empty dict `{}` if camera not available

---

## Settings Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Live View Streaming                      │
│  (camera_streamer instance, WebSocket, ~10 FPS)            │
│                                                             │
│  User adjusts sliders → set_control() → Camera updates     │
│                                                             │
│  Current state: exposure=10ms, gain=8x, sharpness=1.5      │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ User clicks "Test Photo" or "Instant Capture"
                              ↓
                   get_current_settings()
                              │
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              Snapshot of Current Settings                   │
│  {exposure_time: 10000, analogue_gain: 8.0, ...}          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   Test/Instant Capture                      │
│  - Creates TakePhoto.py command with settings              │
│  - Captures at 4K resolution                               │
│  - Embeds EXIF metadata                                    │
│  - Saves to test_captures/                                 │
│  - Returns metadata and photo path                         │
└─────────────────────────────────────────────────────────────┘
```

**Key Point**: Test and instant captures use the **current live view state**, NOT the saved settings in `camera_settings.csv`.

---

## Common Use Cases

### 1. Adjusting Focus and Testing

**Workflow**:
1. Open live view in web UI
2. Adjust focus slider to desired position
3. Click "Test Photo" to capture at full resolution
4. Review captured image quality
5. Repeat until satisfied
6. Click "Capture Photo" for production capture (uses saved settings)

**Settings Used**:
- Test Photo: Uses live view focus position
- Capture Photo: Uses focus position from `camera_settings.csv`

### 2. Quick Documentation Snapshot

**Workflow**:
1. Open live view
2. Adjust camera to frame scene
3. Click "Instant Capture" for quick snapshot
4. Photo saved to test_captures/ with full metadata

**Use Case**: Document camera placement, field conditions, or troubleshooting

### 3. Comparing Settings

**Workflow**:
1. Set settings A in live view
2. Click "Test Photo" → saves test_ABC123.jpg
3. Change to settings B
4. Click "Test Photo" → saves test_DEF456.jpg
5. Compare photos to evaluate settings

---

## Error Handling

All endpoints return consistent error responses:

```json
{
  "error": "Camera not available"
}
```

**Common Errors**:
- **Camera busy**: Another process is using the camera
- **Camera not initialized**: `camera_streamer` not started
- **Capture failed**: Hardware error or file system issue
- **GPS unavailable**: GPS module not responding (non-fatal)

---

## Technical Notes

### Settings Persistence

- **Live View**: Settings stored in `camera_streamer` instance (in-memory)
- **Test Capture**: Uses current `camera_streamer` state
- **Instant Capture**: Uses current `camera_streamer` state
- **Production Capture**: Uses `camera_settings.csv` file

### Camera Resource Management

Only ONE workflow can use the camera at a time:
- Live view holds camera resource while streaming
- Test/instant captures temporarily borrow live view camera
- Production capture spawns separate subprocess (requires camera to be free)

### Performance

- **Test Capture**: <5 seconds for single capture
- **Instant Capture**: <5 seconds for single capture
- **Production Capture**: <5 seconds single, <30 seconds for 5-image focus bracket

---

## Developer API

### Backend (Python)

```python
from liveview_stream import LiveViewStreamer

# Get camera streamer instance
streamer = LiveViewStreamer()

# Get current settings snapshot
settings = streamer.get_current_settings()
# Returns: {'exposure_time': 10000, 'analogue_gain': 8.0, ...}

# Capture test photo with current settings
photo_path = streamer.capture_test_photo_from_liveview()
# Returns: 'test_captures/instant_2025_01_15__14_30_45_ABC123.jpg'
```

### Frontend (JavaScript/React)

```javascript
import { testCaptureLiveview, instantCapture } from '@/utils/api'

// Test capture
const response = await testCaptureLiveview()
console.log(response.data.test_photo_path)

// Instant capture
const response = await instantCapture()
console.log(response.data.photo_path)
```

---

## See Also

- **GPS EXIF Tagging**: See `webui/docs/GPS_EXIF_USER_GUIDE.md`
- **Camera Settings**: See `camera_settings.csv` documentation
- **Live View Streaming**: See `webui/backend/liveview_stream.py`
- **Photo Capture**: See `TakePhoto.py` documentation

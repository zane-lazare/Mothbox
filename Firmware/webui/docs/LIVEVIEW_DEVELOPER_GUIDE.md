# LiveView Developer Guide

Developer documentation for the Mothbox LiveView camera streaming system.

## Overview

The LiveView system provides real-time camera preview and control via WebSocket streaming. This guide covers the internal architecture, key methods, and integration patterns for developers working with the camera system.

## Architecture

### Components

1. **LiveViewStreamer** (`webui/backend/liveview_stream.py`)
   - Manages Picamera2 instance
   - Handles WebSocket frame streaming
   - Provides camera control API
   - Exports current camera state

2. **Camera Routes** (`webui/backend/routes/camera.py`)
   - Flask Blueprint for camera endpoints
   - Test capture endpoints
   - Instant capture endpoint
   - Integration with LiveViewStreamer

3. **Frontend** (`webui/frontend/src/`)
   - React components for camera controls
   - Socket.IO client for streaming
   - InstantCaptureButton component

### Camera Resource Management

**Critical**: The camera (Picamera2) can only be used by ONE process at a time.

**Workflows**:
- **Live View**: Holds camera in-process via `LiveViewStreamer`
- **Test Capture**: Borrows camera from `LiveViewStreamer` temporarily
- **Production Capture**: Spawns `TakePhoto.py` subprocess (requires camera to be free)

**Important**: Always release camera properly to avoid resource conflicts.

---

## LiveViewStreamer.get_current_settings()

### Purpose

Exports the current camera state for test capture workflows. This method provides a snapshot of all camera controls at the moment it's called.

### Signature

```python
def get_current_settings(self) -> Dict[str, Any]:
    """
    Get current camera settings for test capture.

    Returns a snapshot of all camera controls in snake_case format
    for use by test capture endpoints.

    Returns:
        dict: Current camera settings with keys:
            - exposure_time (int): Exposure in microseconds
            - analogue_gain (float): Gain multiplier
            - lens_position (float): Focus position in diopters (0.0-10.0)
            - colour_gains (tuple): (red_gain, blue_gain)
            - sharpness (float): 0.0-2.0
            - brightness (float): -1.0 to 1.0
            - contrast (float): 0.0-2.0
            - saturation (float): 0.0-2.0
            - noise_reduction_mode (int): 0=Off, 1=Fast, 2=High Quality
            - ae_metering_mode (int): 0=Centre, 1=Spot, 2=Matrix
            - af_mode (int): 0=Manual, 1=Auto, 2=Continuous
            - af_range (int): 0=Normal, 1=Macro, 2=Full
            - af_speed (int): 0=Normal, 1=Fast

        Returns empty dict {} if camera not available or error occurs.
    """
```

### Implementation Details

**Location**: `webui/backend/liveview_stream.py:1951-2027`

**Key Behaviors**:
1. Returns empty dict `{}` if camera not started or unavailable
2. Converts Picamera2 control names to snake_case
3. Handles missing/optional controls gracefully
4. Provides fallback values for unavailable controls
5. Thread-safe (uses instance attributes)

**Control Mapping**:
```python
# Picamera2 → snake_case
'ExposureTime' → 'exposure_time'
'AnalogueGain' → 'analogue_gain'
'LensPosition' → 'lens_position'
'ColourGains' → 'colour_gains'
'Sharpness' → 'sharpness'
# ... etc
```

### Usage Example

```python
from liveview_stream import LiveViewStreamer

# Initialize streamer
streamer = LiveViewStreamer()
streamer.start()

# Get current settings
settings = streamer.get_current_settings()

# Access settings
print(f"Exposure: {settings['exposure_time']}µs")
print(f"Gain: {settings['analogue_gain']}x")
print(f"Focus: {settings['lens_position']}D")

# Use for test capture
photo_path = capture_with_settings(settings)
```

### Error Handling

**Returns Empty Dict** when:
- Camera not started (`self.camera is None`)
- Exception occurs during control access
- Picamera2 not available

**Example**:
```python
settings = streamer.get_current_settings()
if not settings:
    # Camera not available
    return fallback_to_file_settings()
```

### Thread Safety

**Safe to call from**:
- Flask request handlers (main thread)
- WebSocket event handlers (Socket.IO thread)
- Background tasks (with proper locking)

**Note**: The method reads instance attributes which are updated atomically by Picamera2.

---

## Test Capture Integration

### Test Capture Liveview Endpoint

**Endpoint**: `POST /api/camera/test-capture-liveview`

**Implementation**: `webui/backend/routes/camera.py:1264-1352`

**Flow**:
1. Check if `camera_streamer` is available
2. Call `camera_streamer.get_current_settings()`
3. If settings available, use them for capture
4. If not available, fall back to `camera_settings.csv`
5. Spawn `TakePhoto.py` subprocess with settings
6. Return metadata and photo path

**Code Example**:
```python
from flask import Blueprint, jsonify, current_app

camera_bp = Blueprint('camera', __name__)

@camera_bp.route('/test-capture-liveview', methods=['POST'])
def test_capture_liveview():
    """Test capture using live view settings"""
    camera_streamer = current_app.config.get('CAMERA_STREAMER')

    if camera_streamer:
        # Get current settings from live view
        settings = camera_streamer.get_current_settings()

        if settings:
            # Use live view settings
            photo_path = capture_with_settings(settings)
            return jsonify({
                'success': True,
                'test_photo_path': photo_path,
                'metadata': settings
            })

    # Fallback to file settings
    return capture_from_file_settings()
```

---

## Instant Capture Integration

### Instant Capture Endpoint

**Endpoint**: `POST /api/camera/instant-capture`

**Implementation**: `webui/backend/routes/camera.py:1354-1442`

**Flow**:
1. Check if `camera_streamer` is available
2. Call `camera_streamer.capture_test_photo_from_liveview()`
   - Internally calls `get_current_settings()`
   - Captures photo with current settings
3. Return photo path, metadata, and EXIF info

**Code Example**:
```python
@camera_bp.route('/instant-capture', methods=['POST'])
def instant_capture():
    """Instant capture using live view settings"""
    camera_streamer = current_app.config.get('CAMERA_STREAMER')

    if not camera_streamer:
        return jsonify({'error': 'Camera not available'}), 500

    try:
        # Capture using current settings
        photo_path = camera_streamer.capture_test_photo_from_liveview()

        # Get metadata
        settings = camera_streamer.get_current_settings()

        return jsonify({
            'success': True,
            'photo_path': photo_path,
            'metadata': settings,
            'exif_embedded': True,
            'timestamp': time.time()
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

---

## Testing

### Unit Tests

**Test File**: `Tests/unit/test_liveview_current_settings.py`

**Coverage**:
- Returns dict with correct keys
- Returns correct types for all values
- Reflects instance values accurately
- Handles camera not started gracefully
- Handles missing controls gracefully
- Updates after control changes

**Example Test**:
```python
def test_get_current_settings_returns_dict(mock_camera_streamer):
    """Test that get_current_settings returns a dictionary"""
    settings = mock_camera_streamer.get_current_settings()
    assert isinstance(settings, dict)

def test_get_current_settings_returns_all_controls(mock_camera_streamer):
    """Test that all expected controls are present"""
    settings = mock_camera_streamer.get_current_settings()

    expected_keys = [
        'exposure_time', 'analogue_gain', 'lens_position',
        'colour_gains', 'sharpness', 'brightness', 'contrast',
        'saturation', 'noise_reduction_mode', 'ae_metering_mode',
        'af_mode', 'af_range', 'af_speed'
    ]

    for key in expected_keys:
        assert key in settings
```

### Integration Tests

**Test File**: `Tests/integration/test_liveview_test_capture_workflow.py`

**Scenarios**:
1. Slider adjustment → test capture → verify settings match
2. Manual focus preservation during instant capture
3. Instant capture vs test capture consistency
4. Exposure/gain from liveview to capture
5. Settings isolation between captures

**Example Test**:
```python
@pytest.mark.hardware
@pytest.mark.integration
def test_slider_adjustment_to_test_capture_settings_match():
    """Test that live view adjustments are used in test capture"""
    streamer = LiveViewStreamer()

    try:
        streamer.start()

        # Adjust sharpness
        streamer.set_control('Sharpness', 2.5)

        # Get current settings
        settings = streamer.get_current_settings()
        assert settings['sharpness'] == 2.5

        # Capture should use adjusted value
        photo_path = streamer.capture_test_photo_from_liveview()
        assert Path(photo_path).exists()

    finally:
        streamer.stop()
```

---

## Frontend Integration

### InstantCaptureButton Component

**File**: `webui/frontend/src/components/InstantCaptureButton.jsx`

**Features**:
- Camera icon button
- Loading state during capture
- Success/error toast notifications
- Prevents concurrent captures
- Disabled when camera not connected

**Usage in Camera.jsx**:
```jsx
import InstantCaptureButton from '@/components/InstantCaptureButton'

function CameraPage() {
  return (
    <div className="test-capture-overlay">
      <h3>Test Capture</h3>

      {/* Test Photo button */}
      <button onClick={handleTestCapture}>
        Test Photo
      </button>

      {/* Instant Capture button */}
      <InstantCaptureButton
        disabled={!connected}
        className="w-full"
      />
    </div>
  )
}
```

### API Integration

**File**: `webui/frontend/src/utils/api.js`

**API Function**:
```javascript
export const instantCapture = () => api.post('/camera/instant-capture')
```

**Usage**:
```javascript
import { instantCapture } from '@/utils/api'

async function handleInstantCapture() {
  try {
    const response = await instantCapture()
    const { photo_path, metadata } = response.data

    toast.success(`Captured: ${photo_path}`)
  } catch (error) {
    toast.error(error.response?.data?.error || 'Capture failed')
  }
}
```

---

## Best Practices

### 1. Always Check Camera Availability

```python
camera_streamer = current_app.config.get('CAMERA_STREAMER')
if not camera_streamer:
    return jsonify({'error': 'Camera not available'}), 500
```

### 2. Validate Settings Before Use

```python
settings = camera_streamer.get_current_settings()
if not settings:
    # Fallback to file settings
    settings = load_settings_from_file()
```

### 3. Handle Missing Controls Gracefully

```python
# get_current_settings() handles this internally
settings = camera_streamer.get_current_settings()
exposure = settings.get('exposure_time', 10000)  # Default fallback
```

### 4. Release Camera Resources Properly

```python
try:
    streamer = LiveViewStreamer()
    streamer.start()
    # ... use camera ...
finally:
    streamer.stop()
    time.sleep(1.0)  # Allow hardware reset
```

### 5. Use Context Managers for Tests

```python
@pytest.fixture
def camera_streamer():
    streamer = LiveViewStreamer()
    try:
        yield streamer
    finally:
        streamer.stop()
        time.sleep(1.0)
```

---

## Common Pitfalls

### 1. Camera Resource Conflicts

**Problem**: Multiple processes trying to use camera simultaneously

**Solution**:
```python
# Always check if camera is in use
if camera_streamer and camera_streamer.is_streaming():
    # Camera busy with live view
    return use_live_view_settings()
else:
    # Camera free for subprocess
    return spawn_takephoto_subprocess()
```

### 2. Settings Not Updating

**Problem**: Changes to controls not reflected in `get_current_settings()`

**Solution**:
```python
# Allow time for camera to apply control changes
streamer.set_control('Sharpness', 2.5)
time.sleep(0.1)  # Brief delay for hardware
settings = streamer.get_current_settings()
```

### 3. Missing LensPosition

**Problem**: `LensPosition` control not always available

**Solution**: `get_current_settings()` handles this internally with fallback:
```python
# Internal implementation
lens_position = self.camera.capture_metadata().get('LensPosition', 0.0)
if lens_position is None:
    lens_position = 0.0  # Fallback
```

### 4. Thread Safety Concerns

**Problem**: Accessing camera from multiple threads

**Solution**: Flask and Socket.IO already handle thread safety. `get_current_settings()` is safe to call from request handlers and WebSocket events.

---

## Performance Considerations

### get_current_settings() Performance

**Execution Time**: <1ms (reads instance attributes)

**Memory**: Negligible (returns small dict ~13 keys)

**Thread Blocking**: Non-blocking (no I/O operations)

**Recommendation**: Safe to call frequently (e.g., on every test capture)

### Streaming Performance

**Target**: 10 FPS sustained

**Bottlenecks**:
- JPEG encoding (use `simplejpeg` for 5-7x speedup)
- Network bandwidth (WebSocket compression helps)
- Camera hardware (frame capture time)

**Optimization**:
```python
# Use hardware MJPEG encoding for best performance
stream_mode = 'mjpeg_hardware'  # vs 'simplejpeg' (CPU)

# Reduce resolution for faster streaming
resolution = (1024, 768)  # vs (1920, 1080)

# Lower JPEG quality for smaller frames
jpeg_quality = 85  # vs 95
```

---

## Debugging

### Enable Debug Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('liveview_stream')
```

### Check Camera State

```python
# Is camera started?
if streamer.camera is None:
    print("Camera not initialized")

# Is streaming active?
if streamer.is_streaming():
    print("Streaming active")

# Get current controls
settings = streamer.get_current_settings()
print(f"Settings: {settings}")
```

### Diagnose Capture Failures

```bash
# Check camera device
ls -la /dev/video*

# Check camera usage
lsof /dev/video*

# View logs
journalctl -u mothbox-webui -f

# Test capture manually
python3 TakePhoto.py --test
```

---

## API Reference

### LiveViewStreamer Methods

```python
class LiveViewStreamer:
    def start(self) -> None:
        """Start camera and streaming"""

    def stop(self) -> None:
        """Stop camera and streaming"""

    def set_control(self, control: str, value: Any) -> None:
        """Set a camera control value"""

    def get_control_value(self, control: str) -> Any:
        """Get current value of a control"""

    def get_current_settings(self) -> Dict[str, Any]:
        """Get snapshot of all camera settings"""

    def capture_test_photo_from_liveview(self) -> str:
        """Capture test photo with current settings"""

    def is_streaming(self) -> bool:
        """Check if streaming is active"""
```

### Camera Routes

```python
# Test capture with live view settings
POST /api/camera/test-capture-liveview
→ {'test_photo_path': str, 'metadata': dict}

# Instant capture
POST /api/camera/instant-capture
→ {'photo_path': str, 'metadata': dict, 'exif_embedded': bool}

# Production capture
POST /api/camera/capture
→ {'latest_photo': str, 'photos': list}
```

---

## See Also

- **Camera API Documentation**: `webui/docs/CAMERA_API.md`
- **User Guide**: `webui/docs/CAMERA_USER_GUIDE.md`
- **Source Code**: `webui/backend/liveview_stream.py`
- **Tests**: `Tests/unit/test_liveview_current_settings.py`
- **Frontend Component**: `webui/frontend/src/components/InstantCaptureButton.jsx`

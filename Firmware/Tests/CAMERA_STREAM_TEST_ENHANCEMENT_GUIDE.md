# LiveViewStreamer Test Enhancement Implementation Guide

## Overview
This guide provides templates and step-by-step instructions for implementing comprehensive test coverage for `liveview_stream.py`. Follow the phases sequentially to build up coverage from ~40% to ~85%+.

**Total Scope:** 128 new tests, 4 new fixtures, ~2000 lines of code
**Estimated Time:** 9-10 hours total (can be done incrementally)

---

## Phase 1: Add Mocking Fixtures to conftest.py (~1.5 hours)

### 1.1 Add mock_opencv Fixture

**Location:** `Tests/conftest.py` (after existing fixtures, around line 1700)

```python
@pytest.fixture
def mock_opencv(monkeypatch):
    """
    Mock OpenCV (cv2) for focus peaking tests

    Simulates edge detection algorithms with realistic numpy array returns.
    All methods return arrays with correct shapes and dtypes.

    Usage:
        def test_focus_peaking(camera_streamer_func, mock_opencv):
            # OpenCV methods are mocked, return realistic arrays
            # Test focus peaking without OpenCV dependency
    """
    import numpy as np
    from unittest.mock import MagicMock

    mock_cv2 = MagicMock()

    # cvtColor: RGB → Grayscale
    def mock_cvtColor(frame, code):
        """Convert to grayscale (average across channels)"""
        if len(frame.shape) == 3:
            return np.mean(frame, axis=2).astype(np.uint8)
        return frame
    mock_cv2.cvtColor = mock_cvtColor

    # Laplacian: Edge detection (variance-based)
    def mock_Laplacian(src, ddepth, ksize=1):
        """Simulate Laplacian edge detection"""
        h, w = src.shape[:2]
        # Create edges with some randomness
        edges = np.random.rand(h, w) * 50  # Low intensity edges
        # Add some strong edges (simulate actual edges)
        edges[h//4:3*h//4, w//4:3*w//4] = 200  # Strong central edge
        return edges.astype(np.uint8)
    mock_cv2.Laplacian = mock_Laplacian

    # Sobel: Directional edge detection
    def mock_Sobel(src, ddepth, dx, dy, ksize=3):
        """Simulate Sobel edge detection"""
        h, w = src.shape[:2]
        edges = np.random.rand(h, w) * 40
        # Directional edges
        if dx > 0:  # Horizontal edges
            edges[:, w//2:] = 150
        if dy > 0:  # Vertical edges
            edges[h//2:, :] = 150
        return edges.astype(np.uint8)
    mock_cv2.Sobel = mock_Sobel

    # Canny: Two-threshold edge detection
    def mock_Canny(image, threshold1, threshold2):
        """Simulate Canny edge detection"""
        h, w = image.shape[:2]
        edges = np.zeros((h, w), dtype=np.uint8)
        # Binary edges (0 or 255)
        edges[h//4:3*h//4, w//4:3*w//4] = 255
        return edges
    mock_cv2.Canny = mock_Canny

    # getStructuringElement: For morphology
    def mock_getStructuringElement(shape, ksize):
        """Return structuring element for morphology"""
        return np.ones(ksize, dtype=np.uint8)
    mock_cv2.getStructuringElement = mock_getStructuringElement

    # morphologyEx: Morphological operations
    def mock_morphologyEx(src, op, kernel):
        """Dilate edges slightly"""
        return src  # Just return input for simplicity
    mock_cv2.morphologyEx = mock_morphologyEx

    # addWeighted: Blend overlay with frame
    def mock_addWeighted(src1, alpha, src2, beta, gamma):
        """Blend two images"""
        # Weighted average
        return (src1 * alpha + src2 * beta + gamma).astype(np.uint8)
    mock_cv2.addWeighted = mock_addWeighted

    # Constants
    mock_cv2.COLOR_RGB2GRAY = 6
    mock_cv2.CV_64F = 6
    mock_cv2.CV_8U = 0
    mock_cv2.MORPH_DILATE = 1
    mock_cv2.MORPH_RECT = 0

    # Inject into sys.modules
    import sys
    monkeypatch.setitem(sys.modules, 'cv2', mock_cv2)

    yield mock_cv2
```

### 1.2 Add mock_simplejpeg Fixture

```python
@pytest.fixture
def mock_simplejpeg(monkeypatch):
    """
    Mock simplejpeg for software JPEG encoding tests

    Returns realistic JPEG bytes with proper headers/trailers.
    Simulates encoding performance (quality affects size).

    Usage:
        def test_encoding(camera_streamer_func, mock_simplejpeg):
            # simplejpeg.encode_jpeg() is mocked
            # Returns JPEG bytes without needing actual library
    """
    from unittest.mock import MagicMock

    mock_sj = MagicMock()

    def mock_encode_jpeg(frame, quality=85, colorspace='RGB'):
        """
        Simulate JPEG encoding

        Returns realistic JPEG bytes:
        - FF D8: JPEG start marker
        - FF D9: JPEG end marker
        - Size varies with quality
        """
        h, w = frame.shape[:2]
        # Rough size estimate: quality affects compression
        base_size = h * w * 3  # RGB bytes
        compression = (100 - quality) / 100.0
        jpeg_size = int(base_size * (0.1 + compression * 0.9))

        # Generate realistic JPEG structure
        jpeg_bytes = b'\xff\xd8'  # SOI (Start of Image)
        jpeg_bytes += b'\xff\xe0'  # APP0 marker
        jpeg_bytes += b'\x00' * (jpeg_size - 4)  # Compressed data
        jpeg_bytes += b'\xff\xd9'  # EOI (End of Image)

        return jpeg_bytes

    mock_sj.encode_jpeg = mock_encode_jpeg

    # Inject into sys.modules
    import sys
    monkeypatch.setitem(sys.modules, 'simplejpeg', mock_sj)

    yield mock_sj
```

### 1.3 Add mock_mjpeg_encoder Fixture

```python
@pytest.fixture
def mock_mjpeg_encoder(monkeypatch):
    """
    Mock MJPEGEncoder and FileOutput for hardware encoding tests

    Simulates Picamera2's hardware MJPEG encoder with frame emission tracking.

    Usage:
        def test_hardware_encoding(camera_streamer_func, mock_mjpeg_encoder):
            # MJPEGEncoder and WebSocketOutput are mocked
            # Test hardware encoding path without actual encoder
    """
    from unittest.mock import MagicMock, Mock

    # Mock FileOutput base class
    class MockFileOutput:
        """Mock FileOutput base class"""
        def __init__(self):
            self.frames_written = 0

        def outputframe(self, frame, keyframe=True, timestamp=None):
            """Track frame outputs"""
            self.frames_written += 1

    # Mock MJPEGEncoder
    class MockMJPEGEncoder:
        """Mock hardware MJPEG encoder"""
        def __init__(self, qp=None):
            self.qp = qp  # Quality parameter (1-25, lower is higher quality)
            self.enabled = True

        def __repr__(self):
            return f"MockMJPEGEncoder(qp={self.qp})"

    # Patch into picamera2.outputs and picamera2.encoders
    monkeypatch.setattr('picamera2.outputs.FileOutput', MockFileOutput, raising=False)
    monkeypatch.setattr('picamera2.encoders.MJPEGEncoder', MockMJPEGEncoder, raising=False)

    yield {
        'FileOutput': MockFileOutput,
        'MJPEGEncoder': MockMJPEGEncoder
    }
```

### 1.4 Add mock_isp_tuning Fixture

```python
@pytest.fixture
def mock_isp_tuning(monkeypatch, tmp_path):
    """
    Mock ISP tuning loader for custom tuning file tests

    Creates fake tuning files and mocks tuning_loader functions.

    Usage:
        def test_custom_tuning(camera_streamer_func, mock_isp_tuning):
            # get_tuning_path() and apply_isp_controls() are mocked
            # Test ISP tuning without actual tuning files
    """
    from unittest.mock import MagicMock
    import json

    # Create fake tuning files
    arducam_tuning = tmp_path / "arducam_64mp.json"
    arducam_tuning.write_text(json.dumps({
        "version": 2.0,
        "target": "arducam_64mp",
        "algorithms": [
            {"name": "lens_shading", "enabled": True},
            {"name": "defect_correction", "enabled": True}
        ]
    }))

    imx477_tuning = tmp_path / "imx477.json"
    imx477_tuning.write_text(json.dumps({
        "version": 2.0,
        "target": "imx477",
        "algorithms": []
    }))

    # Mock tuning_loader functions
    def mock_get_tuning_path(tuning_name):
        """Return path to fake tuning file"""
        if "arducam" in tuning_name.lower():
            return str(arducam_tuning)
        elif "imx477" in tuning_name.lower():
            return str(imx477_tuning)
        return None

    def mock_apply_isp_controls(camera, settings):
        """Mock ISP control application (no-op)"""
        return True

    mock_loader = MagicMock()
    mock_loader.get_tuning_path = mock_get_tuning_path
    mock_loader.apply_isp_controls = mock_apply_isp_controls

    # Patch in liveview_stream module (if already loaded)
    import sys
    if 'liveview_stream' in sys.modules:
        monkeypatch.setattr('liveview_stream.get_tuning_path', mock_get_tuning_path, raising=False)
        monkeypatch.setattr('liveview_stream.apply_isp_controls', mock_apply_isp_controls, raising=False)

    yield mock_loader
```

### 1.5 Enhance mock_picamera2 Fixture

**Location:** Find existing `mock_picamera2` fixture in `conftest.py` (around line 658)

**Add these enhancements to the MockPicamera2 class:**

```python
# ADD to MockPicamera2.__init__ method:
self.scaler_crop_maximum = (0, 0, 4056, 3040)  # Arducam 64MP sensor size
self.control_history = []  # Track all set_controls calls

# ADD to MockPicamera2.camera_properties property:
@property
def camera_properties(self):
    """Camera properties including ScalerCropMaximum"""
    return {
        'ScalerCropMaximum': self.scaler_crop_maximum,
        'Model': 'Arducam 64MP',
        'UnitCellSize': (1120, 1120),  # 1.12µm pixels
        'PixelArraySize': (9248, 6944)
    }

# ADD new method to MockPicamera2:
def set_controls(self, controls):
    """
    Set camera controls with state validation

    Args:
        controls: Dict of control_name: value

    Raises:
        RuntimeError: If camera not in correct state
    """
    if self.state == 'stopped':
        raise RuntimeError("Camera not started")

    # Track control history
    self.control_history.append(controls.copy())

    # Update current controls
    self.current_controls.update(controls)

    # Emit controls_set for tracking
    if hasattr(self, 'controls_set'):
        self.controls_set.append(controls)

# ADD error simulation methods:
def simulate_camera_busy_error(self):
    """Make next operation raise 'camera busy' error"""
    self._simulate_busy = True

def simulate_already_started_error(self):
    """Make next start() raise 'already started' error"""
    self._simulate_already_started = True
```

---

## Phase 2: Rename Existing Test File (5 minutes)

```bash
cd Tests/unit
mv test_camera_stream.py test_camera_stream_encoding.py
```

Update any test discovery patterns if needed (pytest should auto-discover).

---

## Phase 3: Create test_camera_stream_unit.py

### File Header Template

```python
"""
Comprehensive unit tests for LiveViewStreamer class (Issue #78 - Camera Backend Testing)

Tests streaming functionality with comprehensive mocking for CI/CD compatibility.
Covers settings loading, camera initialization, streaming lifecycle, focus peaking,
digital zoom, AF window, ISP tuning, encoder selection, and error recovery.

Hardware tests are in test_camera_stream_encoding.py (marked @pytest.mark.hardware).

Coverage Target: 85%+ (liveview_stream.py is 1737 lines)
"""

import pytest
import json
import sys
import numpy as np
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from threading import Thread
import time

# Import LiveViewStreamer
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))
from liveview_stream import LiveViewStreamer


# ============================================================================
# Test Class 1: Settings Loading and Validation (15 tests)
# ============================================================================

class TestSettingsLoading:
    """Test settings file loading, parsing, and validation"""

    def test_load_defaults_when_file_missing(self, camera_streamer_func, temp_liveview_settings):
        """
        Test settings loader uses hardcoded defaults when file doesn't exist

        When liveview_settings.txt is missing or empty, LiveViewStreamer
        should use built-in default values for all settings.
        """
        # temp_liveview_settings creates empty file
        temp_liveview_settings.write_text("")

        # Create streamer (will load settings)
        streamer = camera_streamer_func
        streamer.load_stream_settings()

        # Verify defaults loaded
        assert streamer.stream_config['width'] == 1024  # Default width
        assert streamer.stream_config['height'] == 768  # Default height
        assert streamer.stream_config['fps'] == 10  # Default FPS
        assert streamer.stream_config['quality'] == 85  # Default quality

    def test_load_custom_settings_from_file(self, camera_streamer_func, temp_liveview_settings):
        """
        Test loading custom settings from liveview_settings.txt

        When file contains custom values, they should override defaults.
        """
        # Write custom settings
        temp_liveview_settings.write_text("""
width=1920
height=1080
fps=15
quality=90
sharpness=2.0
brightness=0.2
        """.strip())

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        # Verify custom values loaded
        assert streamer.stream_config['width'] == 1920
        assert streamer.stream_config['height'] == 1080
        assert streamer.stream_config['fps'] == 15
        assert streamer.stream_config['quality'] == 90
        assert streamer.controls['Sharpness'] == 2.0
        assert streamer.controls['Brightness'] == 0.2

    # TODO: Add 13 more tests following the pattern above
    # - test_type_conversion_integers
    # - test_type_conversion_floats
    # - test_type_conversion_booleans
    # - test_colour_gains_tuple_parsing
    # - test_invalid_value_handling
    # - test_all_image_quality_settings
    # - test_all_focus_settings
    # - test_all_exposure_settings
    # - test_all_white_balance_settings
    # - test_isp_settings
    # - test_focus_peaking_settings
    # - test_zoom_settings
    # - test_stream_config_settings


# ============================================================================
# Test Class 2: Camera Initialization (13 tests)
# ============================================================================

class TestCameraInitialization:
    """Test camera hardware initialization and configuration"""

    def test_initialize_camera_success_camera0(self, camera_streamer_func, mock_picamera2):
        """
        Test successful camera initialization with camera 0

        Should initialize Picamera2 with camera_num=0, create video
        configuration, apply controls, and capture ScalerCropMaximum.
        """
        streamer = camera_streamer_func

        # Initialize camera
        result = streamer.initialize_camera()

        # Verify success
        assert result is True
        assert streamer.camera is not None
        assert streamer.camera.camera_num == 0

        # Verify camera lifecycle
        assert streamer.camera.configure.called
        assert streamer.camera.start.called

        # Verify ScalerCropMaximum captured
        assert streamer.scaler_crop_maximum is not None
        assert len(streamer.scaler_crop_maximum) == 4  # (x, y, w, h)

    # TODO: Add 12 more tests
    # - test_initialize_camera_fallback_camera1
    # - test_initialize_sensor_mode_auto
    # - test_initialize_sensor_mode_4_3
    # - test_initialize_sensor_mode_16_9
    # - test_initialize_sensor_mode_full
    # - test_initialize_with_custom_isp_tuning
    # - test_initialize_isp_tuning_fallback
    # - test_initialize_applies_controls
    # - test_initialize_captures_scaler_crop_max
    # - test_initialize_picamera2_unavailable
    # - test_initialize_camera_busy_error
    # - test_reinitialize_releases_existing_camera


# ============================================================================
# Test Class 3-12: Templates for Remaining Classes
# ============================================================================

# Copy and adapt the pattern above for each test class:
# 3. TestStreamingLifecycle (8 tests)
# 4. TestFocusPeakingAlgorithms (12 tests)
# 5. TestDigitalZoomCalculations (15 tests)
# 6. TestAFWindowCoordinateTransformation (10 tests)
# 7. TestISPTuningApplication (7 tests)
# 8. TestEncoderSelection (10 tests)
# 9. TestStreamPerformance (9 tests)
# 10. TestErrorRecovery (9 tests)
# 11. TestControlApplication (11 tests)
# 12. TestResourceManagement (9 tests)
```

---

## Implementation Checklist

### Phase 1: Fixtures (Complete First)
- [ ] Add mock_opencv to conftest.py
- [ ] Add mock_simplejpeg to conftest.py
- [ ] Add mock_mjpeg_encoder to conftest.py
- [ ] Add mock_isp_tuning to conftest.py
- [ ] Enhance mock_picamera2 with state tracking
- [ ] Test fixtures work: `pytest Tests/unit/test_camera_stream_encoding.py -v`

### Phase 2: File Reorganization
- [ ] Rename test_camera_stream.py → test_camera_stream_encoding.py
- [ ] Verify existing tests still pass
- [ ] Update any documentation referencing old filename

### Phase 3A: Foundation Tests (Priority 1)
- [ ] TestSettingsLoading (15 tests)
- [ ] TestCameraInitialization (13 tests)
- [ ] TestStreamingLifecycle (8 tests)
- [ ] Run tests: `pytest Tests/unit/test_camera_stream_unit.py::TestSettingsLoading -v`
- [ ] Check coverage: `pytest Tests/unit/test_camera_stream_unit.py --cov=liveview_stream`

### Phase 3B: Advanced Features (Priority 2)
- [ ] TestDigitalZoomCalculations (15 tests)
- [ ] TestAFWindowCoordinateTransformation (10 tests)
- [ ] TestControlApplication (11 tests)

### Phase 3C: Algorithms & Encoding (Priority 3)
- [ ] TestFocusPeakingAlgorithms (12 tests)
- [ ] TestISPTuningApplication (7 tests)
- [ ] TestEncoderSelection (10 tests)

### Phase 3D: Resilience (Priority 4)
- [ ] TestErrorRecovery (9 tests)
- [ ] TestStreamPerformance (9 tests)
- [ ] TestResourceManagement (9 tests)

### Phase 4: Verification
- [ ] All 140 tests pass
- [ ] Coverage report shows 85%+
- [ ] CI/CD runs successfully
- [ ] No regressions in existing tests

---

## Quick Reference: Test Patterns

### Pattern 1: Settings Test
```python
def test_setting_name(self, camera_streamer_func, temp_liveview_settings):
    """Test description"""
    # Write settings to temp file
    temp_liveview_settings.write_text("setting=value\\n")

    # Load settings
    streamer = camera_streamer_func
    streamer.load_stream_settings()

    # Assert expected value
    assert streamer.controls['Setting'] == expected_value
```

### Pattern 2: Camera Operation Test
```python
def test_operation_name(self, camera_streamer_func, mock_picamera2):
    """Test description"""
    streamer = camera_streamer_func

    # Perform operation
    result = streamer.method_name(args)

    # Verify camera calls
    assert mock_picamera2.set_controls.called
    assert result == expected
```

### Pattern 3: Error Handling Test
```python
def test_error_condition(self, camera_streamer_func, mock_picamera2):
    """Test description"""
    streamer = camera_streamer_func

    # Simulate error
    mock_picamera2.simulate_error()

    # Verify graceful handling
    result = streamer.method_name()
    assert result is False  # Or appropriate error response
```

---

## Tips for Implementation

1. **Start with fixtures** - Get mocking working first before writing tests
2. **Test incrementally** - Run tests after every 2-3 additions
3. **Use realistic data** - Numpy arrays should have correct shapes (768, 1024, 3)
4. **Follow existing patterns** - Look at test_preferences_routes.py for style
5. **Document edge cases** - Explain WHY in docstrings, especially for complex logic
6. **Check coverage frequently** - Use `--cov=liveview_stream --cov-report=term-missing`

---

## Coverage Measurement Commands

```bash
# Test single class
pytest Tests/unit/test_camera_stream_unit.py::TestSettingsLoading -v

# Test with coverage
pytest Tests/unit/test_camera_stream_unit.py --cov=liveview_stream --cov-report=term-missing

# Test both files
pytest Tests/unit/test_camera_stream_*.py -v

# Full coverage report
pytest Tests/unit/test_camera_stream_unit.py --cov=webui.backend.liveview_stream --cov-report=html
# Open htmlcov/index.html to see detailed coverage
```

---

## Troubleshooting

### Issue: Mock not working
**Solution:** Check sys.modules patching, ensure module imported after mock

### Issue: Tests fail with "camera not configured"
**Solution:** mock_picamera2 state machine - ensure configure() called before start()

### Issue: Numpy array shape errors
**Solution:** All test frames should be (768, 1024, 3) for RGB

### Issue: Coverage not improving
**Solution:** Check if testing right paths - use `--cov-report=term-missing` to see gaps

---

## Next Steps After Completion

1. Run full test suite: `pytest Tests/unit/ -v`
2. Generate coverage report
3. Document any remaining gaps (acceptable <15%)
4. Update TESTING_GUIDE.md with new patterns
5. Add integration tests on hardware (separate task)

---

## Questions?

Refer back to the comprehensive plan in the Plan agent output for:
- Detailed test case descriptions
- Expected coverage per area
- Mocking strategies
- Implementation phases

Good luck with implementation! 🚀

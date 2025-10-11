# Mothbox Test Suite

Test suite for Phase 1.1-1.3 camera stream performance optimizations.

## Overview

This test suite validates:
- **Phase 1.1**: simplejpeg encoding (5-7x speedup vs PIL)
- **Phase 1.2**: Optimized default settings (Q=85 vs Q=95)
- **Phase 1.3**: Stream mode selection (simplejpeg/mjpeg_hardware)

**⚠️ IMPORTANT**: All tests must be run on Raspberry Pi hardware. Local execution is not supported due to dependencies on picamera2, simplejpeg, and hardware-specific features.

## Installation on Raspberry Pi

```bash
cd ~/Mothbox/Firmware
pip3 install -r Tests/requirements-test.txt
```

## Running Tests

### Quick Test (Automated Only)

```bash
# Run all automated tests
pytest Tests/ -v -s

# Run specific test suites
pytest Tests/unit/ -v -s                    # Unit tests only
pytest Tests/integration/ -v -s              # Integration tests only
```

### Full Test Suite (Including Manual)

```bash
# Run all tests including skipped manual tests
pytest Tests/ -v -s --tb=short

# View manual test instructions
pytest Tests/integration/test_manual_verification.py -v -s
```

### Performance Benchmarks

```bash
# Run performance tests with detailed output
pytest Tests/integration/test_stream_performance.py -v -s

# Run encoding speed comparison
pytest Tests/unit/test_camera_stream.py::TestSimpleJPEGEncoding::test_encoding_speed_comparison -v -s
```

## Test Structure

```
Tests/
├── __init__.py
├── README.md                    # This file
├── requirements-test.txt        # Test dependencies
├── unit/
│   ├── __init__.py
│   ├── test_camera_stream.py   # simplejpeg encoding tests
│   └── test_config_validation.py  # Settings validation tests
└── integration/
    ├── __init__.py
    ├── test_stream_performance.py  # Sustained performance tests
    └── test_manual_verification.py # Manual WebUI tests
```

## Test Categories

### Unit Tests

#### `test_camera_stream.py`
- **simplejpeg availability**: Verify v1.8.1 installed
- **Encoding speed**: Compare simplejpeg vs PIL (expect ≥3x speedup)
- **Quality comparison**: Verify similar file sizes at same quality
- **Performance budget**: Single frame < 50ms
- **Quality range**: Test Q=50-100

#### `test_config_validation.py`
- **Default values**: Verify jpeg_quality=85
- **Quality validation**: Range 50-100
- **Resolution validation**: 320x240 to 1920x1080
- **Frame rate validation**: 1-30 FPS
- **Stream mode validation**: simplejpeg/mjpeg_hardware
- **Settings persistence**: Save and load correctly

### Integration Tests

#### `test_stream_performance.py`
- **Sustained 10 FPS**: 100 frames without backlog
- **Resolution scaling**: VGA, Default (1024x768), Full HD
- **Stability over time**: 300 frames, check for degradation
- **Complex frames**: High-entropy vs low-entropy encoding

#### `test_manual_verification.py` (Manual)
- **Visual quality check**: Human verification of image quality
- **Lag measurement**: Hand wave test (<500ms target)
- **Settings UI**: Verify all controls functional
- **Performance comparison**: Q=85 vs Q=95
- **Resolution testing**: Test all presets
- **Stream mode switching**: Test mode changes

## Success Criteria

### Phase 1.1 - simplejpeg Encoding
- ✅ simplejpeg v1.8.1 available
- ✅ Encoding ≥3x faster than PIL
- ✅ File size within 15% of PIL at same quality
- ✅ Single frame encoding <50ms
- ✅ PIL fallback works

### Phase 1.2 - Default Settings
- ✅ Default JPEG quality = 85
- ✅ Quality validation 50-100
- ✅ Settings persist correctly
- ✅ All resolutions supported

### Phase 1.3 - Stream Mode Selection
- ✅ stream_mode defaults to 'simplejpeg'
- ✅ Mode validation works
- ✅ UI shows encoding mode dropdown
- ✅ Settings persist in config file

### Overall Performance
- ✅ Preview lag <500ms (down from 2-3s)
- ✅ Sustained 10 FPS without backlog
- ✅ No errors in console or logs

## Expected Test Output

### Successful Run

```
Tests/unit/test_camera_stream.py::TestSimpleJPEGEncoding::test_simplejpeg_available
✓ simplejpeg version: 1.8.1
PASSED

Tests/unit/test_camera_stream.py::TestSimpleJPEGEncoding::test_encoding_speed_comparison
📊 Encoding Performance (1024x768, Q=85):
   PIL (optimize=True): 187.3ms
   simplejpeg:          28.4ms
   Speedup:             6.6x
PASSED

Tests/integration/test_stream_performance.py::TestStreamingPerformance::test_sustained_10fps_no_backlog
📊 Sustained 100 frames @ 10 FPS:
   Avg encoding: 29.2ms
   Max encoding: 42.1ms
   Frame budget: 100ms
   Headroom: 70.8ms
PASSED

================================ 15 passed in 12.43s ================================
```

## Troubleshooting

### simplejpeg Import Error
```bash
# Install simplejpeg
pip3 install simplejpeg

# Verify installation
python3 -c "import simplejpeg; print(simplejpeg.__version__)"
```

### Flask Import Error in Config Tests
```bash
# Install Flask if missing
pip3 install flask flask-socketio
```

### Camera Not Available Errors
- Tests requiring camera hardware will fail on non-Pi systems
- This is expected - run on actual Pi hardware

### Performance Tests Failing
- Check CPU usage: `top` or `htop`
- Verify no other processes using camera
- Check thermal throttling: `vcgencmd measure_temp`

## Development Workflow

1. **Write tests first** (TDD approach)
2. **Implement features**
3. **Run unit tests** locally on Pi
4. **Run integration tests** for performance
5. **Manual verification** in WebUI
6. **Commit when all tests pass**

## Remote Testing

Since tests run only on Pi, recommended workflow:

```bash
# On development machine (WSL/local)
# 1. Make code changes
# 2. Commit to git

# On Raspberry Pi
# 3. Pull latest changes
cd ~/Mothbox
git pull

# 4. Run tests
pytest Firmware/Tests/ -v -s

# 5. Manual verification in WebUI
python3 Firmware/webui/backend/app.py
# Navigate to http://pi-ip:5000
```

## Coverage

```bash
# Run with coverage report
pytest Tests/ --cov=webui/backend --cov-report=term-missing -v

# Generate HTML coverage report
pytest Tests/ --cov=webui/backend --cov-report=html
# View in browser: htmlcov/index.html
```

## Next Steps

After Phase 1.1-1.3 completion:
- **Phase 2**: Expand camera controls (sharpness, brightness, contrast, etc.)
- **Phase 3**: Frontend UI enhancements
- **Phase 4**: Advanced features (autofocus, calibration, presets)

See [GitHub Issue #43](https://github.com/user/repo/issues/43) for full implementation plan.

---

**Last Updated**: 2025-01-11
**Test Suite Version**: 1.0.0
**Mothbox Version**: 5.x

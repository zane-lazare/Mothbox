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
├── README.md                     # This file
├── conftest.py                   # Shared fixtures
├── requirements-test.txt         # Test dependencies
├── unit/
│   ├── __init__.py
│   ├── test_camera_stream.py    # simplejpeg encoding tests
│   ├── test_config_validation.py # Settings validation tests
│   └── test_mothbox_paths_hardware.py  # Hardware configuration tests (Issue #13)
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

#### `test_mothbox_paths_hardware.py` *(NEW - Issue #13 Phase 1)*
Comprehensive tests for hardware configuration functions in `mothbox_paths.py`:

- **get_control_values()** (12 tests): Configuration file parser
  - Basic key=value parsing, comment handling, edge cases
  - Whitespace stripping (bug fix validation)
  - Unicode support, long lines, malformed input

- **get_gpio_pins()** (13 tests): Relay GPIO pin configuration
  - Default 4.x firmware pins (26/20/21)
  - Custom pin configuration from controls.txt
  - Partial configuration (some keys missing)
  - GPIO validation (BCM range 0-27)
  - I2C reserved pin warnings (GPIO 0, 1)

- **get_epaper_pins()** (9 tests): E-paper display pins
  - Waveshare 2.13" defaults (17/25/8/24/18)
  - Config key mapping (epaper_*_pin → *_PIN)
  - Partial and invalid configurations

- **get_mux_pins()** (10 tests): Multiplexer pins
  - CD74HC4067 defaults (31/29/33/13/12/15/36)
  - BOARD mode validation (physical pins 1-40)
  - Distinction from BCM numbering

- **get_hardware_config()** (15 tests): Complete hardware configuration (32 keys)
  - All 7 hardware modules (relay, INA260, e-paper, GPS, light sensor, PCA9536, mux)
  - Boolean parsing (case-insensitive)
  - Hex address parsing (0x40 → 64)
  - GPS adaptive timeouts (5 timeout keys)
  - Partial and missing configuration handling

**Coverage**: 97.8% for tested functions (270/276 lines)

**Run**:
```bash
# Run all hardware config tests
pytest Tests/unit/test_mothbox_paths_hardware.py -v

# With coverage report
pytest Tests/unit/test_mothbox_paths_hardware.py --cov=mothbox_paths --cov-report=term-missing
```

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

## Test Infrastructure

### Shared Fixtures (conftest.py)

The test suite uses shared pytest fixtures defined in `Tests/conftest.py`:

- **`camera_streamer`**: Module-scoped CameraStreamer instance with automatic cleanup
- **`camera_streamer_func`**: Function-scoped CameraStreamer for test isolation
- **`app`**: Flask app with CAMERA_STREAMER registered in app.config
- **`client`**: Flask test client for API testing

### Pytest Markers

- **`@pytest.mark.hardware`**: Marks tests requiring real Raspberry Pi hardware
  - Automatically applied to integration tests
  - Skipped if not running on Pi or camera unavailable

### Test Structure Update

```
Tests/
├── __init__.py
├── conftest.py                  # ← NEW: Shared fixtures
├── README.md                    # This file
├── requirements-test.txt
├── IMPLEMENTATION_SUMMARY.md    # Phase 1.1-1.3 summary
├── PHASE3_SUMMARY.md           # ← NEW: Phase 3 summary
├── unit/
│   ├── test_camera_stream.py
│   ├── test_config_validation.py
│   ├── test_preview_controls.py
│   ├── test_capture_settings.py
│   ├── test_test_capture.py
│   └── test_settings_copy.py   # ← NEW: Phase 3
└── integration/
    ├── test_stream_performance.py
    ├── test_camera_controls.py
    ├── test_image_quality.py
    ├── test_frontend_integration.py  # ← NEW: Phase 3
    └── test_manual_verification.py   # Updated with Phase 3
```

## Phase 3: Frontend Integration Tests

New test modules for Phase 3:

### Integration Tests

**`test_frontend_integration.py`** - UI/Backend integration:
- Camera page controls update preview settings
- Interactive buttons (Autofocus, Calibrate, Test Capture)
- Settings copy functionality end-to-end
- Real-time metadata display
- Error handling and user feedback
- Complete workflow testing

### Unit Tests

**`test_settings_copy.py`** - Settings copy logic:
- Copy preview → capture settings
- Copy capture → preview settings
- Compatible vs incompatible settings
- Validation and error handling
- File operations and backups

### Running Phase 3 Tests

```bash
# Run all Phase 3 tests
./Tests/run_tests.sh phase3

# Or directly with pytest
pytest Tests/integration/test_frontend_integration.py Tests/unit/test_settings_copy.py -v -s

# Run manual Phase 3 verification
pytest Tests/integration/test_manual_verification.py::TestPhase3ManualVerification -v -s
```

## CI/CD Integration (Issue #13 Phase 3)

### Overview

Automated testing runs on every push to `main`, `dev`, and `feature/**` branches via GitHub Actions.

**Workflow File**: `.github/workflows/test.yml`

### What Runs in CI/CD

**Backend Tests** (Python 3.13):
- Unit tests with coverage tracking
- Integration tests (non-hardware only)
- Coverage threshold enforcement (85%)

**Frontend Tests** (Node.js 20):
- Vitest component tests
- Coverage reports

**Total CI Time**: ~5-8 minutes per run

### Test Badges

[![Tests](https://github.com/zane-lazare/Mothbox/actions/workflows/test.yml/badge.svg)](https://github.com/zane-lazare/Mothbox/actions/workflows/test.yml)

### Running CI Tests Locally

Simulate the GitHub Actions workflow on your local machine:

```bash
# Run the same tests that run in CI/CD
./Tests/run_tests.sh ci

# This will:
# 1. Run unit tests with coverage (mothbox_paths.py, webui/backend)
# 2. Run integration tests (skipping hardware-dependent tests)
# 3. Check coverage threshold (must be ≥85%)
# 4. Generate HTML coverage report
```

**Coverage Reports**:
- **HTML**: `Firmware/htmlcov/index.html` (open in browser)
- **XML**: `Firmware/coverage.xml` (for CI/CD tools)
- **Terminal**: Displayed after test run

### Hardware vs CI Tests

**Hardware Tests** (marked with `@pytest.mark.hardware`):
- ✅ **On Raspberry Pi**: All tests run (unit + integration + hardware)
- ⚠️ **In CI (GitHub Actions)**: Hardware tests automatically skipped
- 🔧 **Local dev**: Hardware tests skipped on non-Pi systems

**Why Some Tests Are Skipped in CI**:
- CI runs on `ubuntu-latest` (no camera hardware)
- Hardware tests require: Picamera2, GPIO pins, sensors
- Automatic detection via `Tests/conftest.py` pytest hooks

### Coverage Requirements

**Enforced Thresholds**:
- **New code**: 85% coverage minimum (enforced in CI)
- **mothbox_paths.py**: 95%+ target
- **webui/backend**: 85%+ target

**Checking Coverage**:
```bash
# Run tests with coverage report
pytest Tests/unit/ --cov=mothbox_paths --cov=webui/backend --cov-report=term-missing

# Check if coverage meets threshold
coverage report --fail-under=85
```

### Workflow Triggers

**Automatic**:
- Push to `main`, `dev`, or `feature/**` branches
- Pull requests to `main` or `dev`
- Only when relevant files change (Python, tests, configs)

**Manual**:
- Go to Actions tab in GitHub
- Select "Mothbox Tests" workflow
- Click "Run workflow"

### Viewing CI Results

**GitHub Actions**:
1. Go to repository → Actions tab
2. Click on latest workflow run
3. View "Backend Tests" and "Frontend Tests" jobs
4. Download coverage artifacts (available for 7 days)

**Coverage Artifacts**:
- `coverage-report-python-3.13`: HTML coverage report
- `coverage-xml-python-3.13`: XML for external tools
- `frontend-coverage-node-20`: Frontend coverage

### Troubleshooting CI Failures

**Common Issues**:

1. **Coverage below 85%**:
   ```bash
   # Run locally to see what's missing
   ./Tests/run_tests.sh ci
   # Open htmlcov/index.html to see uncovered lines
   ```

2. **Hardware test failures in CI**:
   - Check if test is marked with `@pytest.mark.hardware`
   - Ensure test uses `-m "not hardware"` filter in CI

3. **Import errors**:
   - Verify `requirements-test.txt` is up to date
   - Check Python version compatibility (3.10+)

4. **Test timeouts**:
   - CI has 2-minute timeout per test (pytest-timeout)
   - Long-running tests should use `@pytest.mark.timeout(300)`

### Configuration Files

**pytest Configuration**: `Firmware/pyproject.toml`
- Test discovery patterns
- Coverage source paths
- Test markers (hardware, photo, stream, etc.)
- Excluded paths and lines

**GitHub Actions**: `.github/workflows/test.yml`
- Python version matrix (3.13)
- Node.js version (20.x)
- Coverage threshold (85%)
- Artifact retention (7 days)

### Next Steps

Completed Phases:
- **Phase 1.1-1.3**: ✅ Camera stream performance optimizations
- **Phase 2.1**: ✅ Expanded camera controls
- **Phase 2.2**: ✅ Interactive features (autofocus, calibration, metadata)
- **Phase 3**: ✅ Frontend integration tests
- **Issue #13 Phase 1**: ✅ Hardware configuration tests (mothbox_paths.py)
- **Issue #13 Phase 2**: ✅ Installer integration tests
- **Issue #13 Phase 3**: ✅ CI/CD integration with GitHub Actions

Future Phases:
- **Phase 4**: Advanced features (HDR, presets, profiles)

See [GitHub Issue #43](https://github.com/user/repo/issues/43) for full implementation plan.

---

**Last Updated**: 2025-10-30
**Test Suite Version**: 3.0.0 (Issue #13 Phase 3 - CI/CD Integration)
**Mothbox Version**: 5.x

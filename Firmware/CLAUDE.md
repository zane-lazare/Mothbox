# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mothbox is a Raspberry Pi-based automated camera trap system for photographing insects (especially moths). The firmware manages camera control, scheduling, hardware sensors, and provides a modern React web interface for monitoring and control.

**Key hardware**: Raspberry Pi (4 or 5), Arducam OwlSight 64MP camera, GPIO relays for lights, optional sensors (GPS, INA260 power monitor, e-paper display).

## Installation Types

The system supports three installation layouts:

1. **Production** (recommended): FHS-compliant with `/opt/mothbox` (application), `/etc/mothbox` (config), `/var/lib/mothbox` (data)
2. **Legacy**: All-in-one at `/home/pi/Desktop/Mothbox` for backward compatibility
3. **Custom**: User-defined via `MOTHBOX_HOME` environment variable
4. **Test**: Repository root when `MOTHBOX_ENV=test` or pytest detected

All code uses `mothbox_paths.py` for path resolution - never hardcode paths.

## Architecture

### Firmware Versions (4.x vs 5.x)

Two firmware versions exist with **identical functionality** but different GPIO pin mappings:
- **4.x**: GPIO pins 26/20/21 for relays (legacy hardware)
- **5.x**: GPIO pins 5/19/9 for relays (current hardware)

Both run on Pi 4 and Pi 5. Selection is based on physical wiring, not Pi model.

Core scripts in each version:
- `TakePhoto.py`: Main photo capture with EXIF metadata, GPS tagging, focus bracketing
- `Scheduler.py`: Cron-based task scheduling
- `GPS.py`: GPS data acquisition and time sync
- `UpdateDisplay.py`: E-paper display updates
- GPIO control scripts: `Attract_On.py`, `Attract_Off.py`, `FlashOn.py`, etc.

### Web UI (webui/)

**Backend** (`webui/backend/`):
- Flask 3.0 + Flask-SocketIO for REST API and WebSocket streaming
- CSRF protection on all state-changing endpoints
- Rate limiting for hardware endpoints
- Main file: `app.py` (initializes all routes and services)
- Routes organized by feature: `routes/camera.py`, `routes/gpio.py`, `routes/system.py`, etc.
- `liveview_stream.py`: Real-time camera streaming via WebSocket (~10 FPS)
- `preset_manager.py`: Camera preset system for saving/loading settings

**Frontend** (`webui/frontend/`):
- React 18 + Vite + Tailwind CSS
- TanStack Query for data fetching
- Socket.io-client for real-time camera preview
- Component-based architecture

### Path Resolution System

**Critical**: `mothbox_paths.py` provides centralized path management:
- Auto-detects installation type (production/legacy/custom/test)
- Exports: `MOTHBOX_HOME`, `CONFIG_DIR`, `DATA_DIR`, `PHOTOS_DIR`
- Hardware config functions: `get_gpio_pins()`, `get_hardware_config()`, `get_epaper_pins()`, `get_mux_pins()`
- Firmware detection: `get_firmware_version()`, `get_takephoto_script()`

**Always import paths from this module** - never construct paths manually.

### GPS EXIF Tagging System

**Overview**: Automatic GPS coordinate embedding in photo EXIF metadata for geotagging Mothbox captures.

**Architecture**:
- **Library**: `lib/gps_exif_lib.py` - Core GPS EXIF functionality (196 lines, 85%+ coverage)
  - `get_gps_data_from_controls()`: Read GPS data from controls.txt
  - `decimal_to_dms()`: Convert decimal coordinates to EXIF DMS format
  - `build_gps_ifd()`: Build GPS IFD (Image File Directory) structure
  - `embed_gps_exif()`: Embed GPS data into photo EXIF (preserves camera metadata)
  - `verify_gps_exif()`: Verify and extract GPS data from photos
  - `is_already_tagged()`: Check if photo already has GPS EXIF

- **CLI Tool**: `gps_exif_tagger.py` - Batch and watch mode processing
  - **Batch mode**: One-time processing of photo directory (default)
  - **Watch mode**: Continuous monitoring for new photos (`--watch`)
  - **Options**: `--dry-run`, `--backup`, `--force`, `--pattern`, `--interval`
  - **Performance**: >10 photos/sec throughput, <500ms per photo

- **Verification Tool**: `scripts/verify_gps_exif.py` - Inspect and verify GPS EXIF
  - Interactive photo inspection
  - Batch directory verification
  - CSV report generation
  - Timestamp extraction from Mothbox filenames

**Systemd Service** (optional):
- **Purpose**: Automatically tag new photos as they're captured
- **Implementation**: `gps_exif_tagger.py --mode immediate --watch --interval 10`
- **Service files**: `services/gps-exif-tagger.service` (production), `services/gps-exif-tagger-legacy.service` (legacy)
- **Installation**: Via `install_mothbox.sh --with-gps-exif-service`
- **Resource limits**: 256MB memory max, 25% CPU quota
- **Security**: Strict systemd hardening (ProtectSystem=strict, NoNewPrivileges, capability restrictions)

**Usage Examples**:
```bash
# Batch process entire photo directory
python3 gps_exif_tagger.py --directory /var/lib/mothbox/photos

# Watch mode with backup creation
python3 gps_exif_tagger.py --watch --backup --interval 5

# Dry run to test before modifying files
python3 gps_exif_tagger.py --dry-run --verbose

# Force re-tag all photos (even if already tagged)
python3 gps_exif_tagger.py --force --pattern "*.jpg"

# Verify GPS EXIF in photos
python3 scripts/verify_gps_exif.py /var/lib/mothbox/photos/photo.jpg

# Generate CSV report for all photos
python3 scripts/verify_gps_exif.py --directory /var/lib/mothbox/photos --csv gps_report.csv
```

**Service Management**:
```bash
# Start/stop/restart service
sudo systemctl start gps-exif-tagger.service
sudo systemctl stop gps-exif-tagger.service
sudo systemctl restart gps-exif-tagger.service

# View live logs
sudo journalctl -u gps-exif-tagger.service -f

# Check status and resource usage
sudo systemctl status gps-exif-tagger.service
```

**GPS Data Source**:
- Reads from `controls.txt` fields: `lat`, `lon`, `gps_fix_mode`, `alt`, `gpstime`, `gps_satellites_used`, `gps_hdop`, `gps_pdop`
- Requires `gps_fix_mode > 0` for valid GPS fix
- Altitude only embedded when `gps_fix_mode = 3` (3D fix)
- Coordinates stored as EXIF GPS IFD with DMS (Degrees, Minutes, Seconds) rational format

**Testing**:
- **Unit tests**: 70+ tests covering all functions, error handling, edge cases
  - `Tests/unit/test_gps_exif_lib.py`: Core library tests (38 tests)
  - `Tests/unit/test_gps_exif_tagger_cli.py`: CLI argument tests (22 tests)
  - `Tests/unit/test_gps_exif_lib_errors.py`: Error handling (30+ tests)
  - `Tests/unit/test_verify_gps_exif_tool.py`: Verification tool tests (20 tests)
- **Integration tests**: End-to-end workflows and cross-component tests
  - `Tests/integration/test_gps_exif_workflow.py`: E2E scenarios (11 tests)
  - `Tests/integration/test_gps_exif_systemd.py`: Service integration (10 tests)
- **Performance tests**: `Tests/performance/test_gps_exif_performance.py`
  - Single photo: <500ms, Batch: >10 photos/sec, Memory: <50MB for 1000 photos
- **Stress tests**: `Tests/stress/test_gps_exif_stress.py`
  - Large directories (1000+ photos), concurrent access, filesystem edge cases
- **Manual tests**: `Tests/manual/gps_exif_service/` - Service installation, monitoring, resource limits

**Performance Benchmarks**:
- Single photo processing: <500ms
- Batch throughput: >10 photos/sec (tested with 200 photos)
- Memory usage: <50MB for 100 photos, <10MB for single photo
- Service latency: <10 seconds from photo creation to GPS tagging

**Documentation**:
- `docs/GPS_EXIF_SERVICE.md`: Service setup, troubleshooting, configuration
- `docs/GPS_EXIF_USER_GUIDE.md`: User guide for GPS EXIF functionality
- `TESTING_PROCEDURE.md`: Manual testing procedures

**Important Notes**:
- GPS EXIF embedding preserves all existing camera EXIF metadata
- Photos are modified in-place (use `--backup` for safety)
- Idempotent: Can safely re-run on already-tagged photos (skips by default)
- Service auto-restarts on failure with exponential backoff
- Compatible with all Mothbox photo formats (.jpg, .jpeg, case-insensitive)

### Camera System

Two camera workflows:

1. **Photo Capture** (subprocess-based):
   - Spawns `TakePhoto.py` as subprocess
   - Handles: HDR mode, focus bracketing, EXIF metadata, GPS tagging
   - Focus bracketing: Captures multiple images at different focus distances for depth stacking

2. **Live Preview** (in-process streaming):
   - `liveview_stream.py`: Manages Picamera2 instance for WebSocket streaming
   - Streaming modes: `simplejpeg` (CPU encoding, 5-7x faster than PIL) or `mjpeg_hardware` (GPU encoding)
   - Camera controls: exposure, gain, white balance, zoom, autofocus window, noise reduction, metering modes
   - ISP tuning: Lens shading correction, defect pixel correction via JSON tuning files

**Important**: Camera can only be used by ONE workflow at a time. Tests/code must properly release camera between operations.

## Common Development Commands

### Testing

```bash
# Run all tests (requires Raspberry Pi hardware for integration tests)
pytest Tests/ -v -s

# Unit tests only (can run without hardware, uses mocking)
pytest Tests/unit/ -v

# Integration tests (requires real camera/GPIO/sensors)
pytest Tests/integration/ -v -s

# Run with coverage
pytest Tests/ --cov=mothbox_paths --cov=webui/backend --cov-report=html

# Run specific test categories
pytest -m hardware  # Hardware-dependent tests
pytest -m "not hardware"  # Skip hardware tests (for CI/CD)

# Check coverage threshold (85% minimum)
coverage report --fail-under=85
```

### Linting and Security

```bash
# Run Ruff linter (Python code quality)
ruff check .

# Auto-fix linting issues
ruff check --fix .

# Format code with Ruff
ruff format .

# Security scanning with Bandit (MEDIUM+ severity enforced in CI)
bandit -c pyproject.toml -r . --severity-level medium

# Generate security report
bandit -c pyproject.toml -r . --format json --output bandit-report.json
```

### Web UI Development

```bash
# Backend (Flask API server)
cd webui/backend
export MOTHBOX_ENV=development  # Enable debug mode
python3 app.py  # Runs on http://localhost:5000

# Frontend (React dev server)
cd webui/frontend
npm install
npm run dev  # Runs on http://localhost:5173

# Build frontend for production
npm run build  # Output: webui/frontend/dist/

# Run backend tests
pytest Tests/unit/test_*.py -v

# Run frontend tests
cd webui/frontend
npm test
```

### Installation/Update Scripts

```bash
# Interactive installation wizard
./install_mothbox.sh

# Production installation (CLI)
./install_mothbox.sh --type production --with-webui

# Quick install with defaults
./install_mothbox.sh --type legacy --quick

# Update existing installation
./update_mothbox.sh

# Uninstall with optional data preservation
./uninstall_mothbox.sh
```

### Running Single Test

```bash
# Run specific test file
pytest Tests/unit/test_mothbox_paths_hardware.py -v

# Run specific test class
pytest Tests/integration/test_autofocus_workflows.py::TestAutofocusSuccessScenarios -v

# Run specific test function
pytest Tests/unit/test_camera_stream.py::TestSimpleJPEGEncoding::test_encoding_speed_comparison -v -s
```

## Code Architecture Notes

### Configuration Files

Located in `CONFIG_DIR` (via `mothbox_paths.py`):
- `controls.txt`: Key=value hardware config (GPIO pins, I2C addresses, feature flags)
- `camera_settings.csv`: Camera parameters (resolution, exposure, focus, HDR settings)
- `schedule_settings.csv`: Cron scheduling configuration
- `wordlist.csv`: Device naming wordlist for display

Parser: `get_control_values()` in `mothbox_paths.py` handles comments, whitespace, Unicode.

### Hardware Configuration

`get_hardware_config()` returns dict with 32+ keys covering:
- **Relays**: GPIO pins for attract lights, flash, UV lights
- **INA260**: I2C power monitor (address, enable flag)
- **E-paper**: Waveshare 2.13" display pins (RST, DC, CS, BUSY, SCK)
- **GPS**: Serial port, baud rate, 5 adaptive timeout values
- **PCA9536**: I2C GPIO expander
- **Multiplexer**: CD74HC4067 pins (BOARD mode, physical pins 1-40)

Boolean parsing is case-insensitive. Hex addresses auto-converted (0x40 → 64).

### Test Infrastructure

**Markers** (defined in `pyproject.toml` and `Tests/conftest.py`):
- `@pytest.mark.hardware`: Requires real Pi hardware (camera/GPIO/sensors)
- `@pytest.mark.photo`: Uses photo capture workflow (TakePhoto.py subprocess)
- `@pytest.mark.stream`: Uses streaming workflow (LiveViewStreamer instance)
- `@pytest.mark.integration`: Multi-component integration tests
- `@pytest.mark.unit`: Isolated unit tests with mocking

**Fixtures** (from `Tests/conftest.py`):
- `camera_streamer`: Module-scoped LiveViewStreamer with cleanup
- `camera_streamer_func`: Function-scoped for test isolation
- `app`: Flask app with CAMERA_STREAMER registered
- `client`: Flask test client for API testing

**Coverage**: 85% minimum enforced. Configured in `pyproject.toml` with branch coverage enabled.

### Camera State Management

**Critical**: Picamera2 can only run one instance at a time. Common issues:

1. **Resource contention**: Photo capture subprocess blocks streaming
2. **Proper cleanup**: Always use context managers or try/finally for camera operations
3. **Release delays**: May need `time.sleep(1.0)` after camera.close() for hardware state reset
4. **Test isolation**: Function-scoped fixtures prevent state leakage between tests

See `Tests/tools/diagnose_workflow_failures.py` for analyzing camera state conflicts.

### Security Scanning

Bandit configuration in `pyproject.toml`:
- **CI enforcement**: MEDIUM and HIGH severity findings fail the build
- **Legitimate patterns**: Use `# nosec B603` comments with clear justifications
- **Excluded dirs**: Tests/, OldScripts/, vendor libraries, frontend code

Common false positives in embedded/IoT context:
- B603/B607: subprocess usage (required for GPIO/camera/system control)
- B103: File permissions 0o755 (standard for photo directories)
- B104: Bind to 0.0.0.0 (local network device with CSRF/CORS protection)

### WebSocket Camera Streaming

Flow: Frontend connects → Server starts camera → Continuous frame capture → JPEG encode → Base64 → Emit to client

Key parameters (in `liveview_settings.txt`):
- `target_fps`: 10 (default)
- `jpeg_quality`: 85 (balance of speed/quality)
- `stream_mode`: "simplejpeg" or "mjpeg_hardware"
- `resolution`: Width,Height (e.g., 1024,768)

Performance targets: <100ms per frame, sustained 10 FPS without backlog.

### Preset System

Camera presets save/load complete camera configurations:
- Built-in presets: `webui/backend/presets_builtin/` (e.g., night_photography.json, macro.json)
- User presets: Stored in `DATA_DIR/presets/`
- Managed by `preset_manager.py`
- Can be applied to photo capture or live preview settings

## Important Patterns

### Path Usage

```python
# CORRECT
from mothbox_paths import CONFIG_DIR, PHOTOS_DIR, get_gpio_pins
camera_settings = CONFIG_DIR / "camera_settings.csv"

# WRONG - Never hardcode paths
camera_settings = "/opt/mothbox/camera_settings.csv"
```

### GPIO Pin Access

```python
# CORRECT
from mothbox_paths import get_gpio_pins
pins = get_gpio_pins()
Relay_Ch1 = pins['Relay_Ch1']  # Auto-detects from controls.txt or uses firmware defaults

# WRONG - Never hardcode GPIO numbers
Relay_Ch1 = 26  # This breaks on 5.x firmware
```

### Camera Resource Management

```python
# CORRECT - Use context manager
from picamera2 import Picamera2
with Picamera2() as camera:
    camera.start()
    # ... operations ...
    camera.stop()
# Camera automatically closed

# For tests requiring cleanup
@pytest.fixture
def camera():
    cam = Picamera2()
    try:
        yield cam
    finally:
        cam.close()
        time.sleep(1.0)  # Allow hardware reset
```

### CSRF Protection (Web UI)

```python
# All POST/PUT/DELETE/PATCH routes require CSRF tokens
from flask_wtf.csrf import csrf_exempt

# Default: CSRF required (no decorator needed)
@app.route('/api/camera/capture', methods=['POST'])
def capture():
    # CSRF auto-validated by Flask-WTF
    pass

# Exempt only if absolutely necessary (e.g., WebSocket handshake)
@app.route('/api/websocket/connect', methods=['POST'])
@csrf_exempt
def ws_connect():
    pass
```

### GPS Coordinate Conversion

```python
# CORRECT - Use shared utilities from webui.lib
from webui.lib.gps_coordinates import decimal_to_dms, dms_to_decimal

# Convert decimal to DMS for EXIF embedding
lat_dms = decimal_to_dms(37.7749, is_latitude=True)
# Returns: (37, 46, 29.64, 'N')

# Convert DMS to decimal for API/storage
lat_decimal = dms_to_decimal(37, 46, 29.64, 'N')
# Returns: 37.7749

# BACKWARD COMPATIBLE - Can still import from utils (re-exported)
from webui.backend.utils import decimal_to_dms, dms_to_decimal

# WRONG - Don't implement conversion logic inline
# This leads to inconsistencies and bugs
```

```typescript
// CORRECT - Use shared utilities (frontend)
import { decimalToDMS, formatCoordinateDisplay } from '@/utils/gpsCoordinates';

const dms = decimalToDMS(37.7749, true);
// Returns: { degrees: 37, minutes: 46, seconds: 29.64, reference: 'N' }

const latDisplay = formatCoordinateDisplay(37.7749, true);
const lonDisplay = formatCoordinateDisplay(-122.4194, false);
// latDisplay: "37°46'29.64\"N", lonDisplay: "122°25'9.84\"W"
```

## Key Files Reference

- `mothbox_paths.py`: **Path resolution and hardware config** (276 lines, 97.8% coverage)
- `install_mothbox.sh`: Installation script with Pi detection and firmware selection
- `gps_exif_tagger.py`: Main GPS EXIF embedding tool (CLI and watch mode)
- `lib/gps_exif_lib.py`: GPS EXIF library (coordinate conversion, EXIF embedding, verification)
- `webui/lib/gps_coordinates.py`: **GPS coordinate utilities** (decimal ↔ DMS conversion, validation, formatting) - webui-shared library
- `webui/frontend/src/utils/gpsCoordinates.ts`: **GPS coordinate utilities (TypeScript)** (identical behavior to Python)
- `webui/backend/app.py`: Flask app initialization, CSRF, CORS, SocketIO setup
- `webui/backend/liveview_stream.py`: Camera streaming engine (2500+ lines)
- `webui/backend/routes/camera.py`: Camera control API (1270+ lines)
- `pyproject.toml`: pytest, coverage, bandit, and ruff configuration
- `Tests/README.md`: Comprehensive testing documentation
- `Tests/manual/gps_exif_service/`: GPS EXIF service manual testing procedures
- `docs/GPS_EXIF_SERVICE.md`: GPS EXIF service setup and troubleshooting guide
- `docs/GPS_COORDINATE_UTILITIES.md`: GPS coordinate conversion utilities documentation

## Development Workflow

1. **Never hardcode paths** - always use `mothbox_paths.py`
2. **Test camera code on real Pi** - unit tests mock hardware, integration tests require real camera
3. **Check coverage** - 85% minimum, use `pytest --cov` to verify
4. **Run security scan** - `bandit -c pyproject.toml -r .` before committing
5. **Proper camera cleanup** - use context managers, allow hardware reset delays
6. **Follow GPIO mapping** - use `get_gpio_pins()`, never assume pin numbers
7. **CSRF tokens required** - all state-changing web endpoints must validate CSRF

## Testing Philosophy

- **Unit tests**: Mock hardware, test logic in isolation (can run anywhere)
- **Integration tests**: Require real Pi hardware, marked with `@pytest.mark.hardware`
- **Hardware tests auto-skipped in CI** - GitHub Actions runs on Ubuntu without camera
- **Manual tests**: Documented in `TESTING_PROCEDURE.md` for visual/interactive verification

## Security Considerations

**Current state**: No authentication, binds to 0.0.0.0 - **ONLY for trusted local networks**

Protection layers:
- ✅ CSRF protection on all POST/PUT/DELETE/PATCH endpoints
- ✅ Input validation to prevent injection
- ✅ Path traversal protection
- ✅ Rate limiting on hardware endpoints
- ✅ CORS configuration for production

Planned (Issue #19): User authentication, configurable binding, production WSGI server (gunicorn).

## Common Issues

1. **Camera busy errors**: Another process using camera. Check `lsof /dev/video*`, ensure proper cleanup in tests.
2. **Import errors in tests**: May need hardware mocking. Check if `@pytest.mark.hardware` should be added.
3. **Coverage below threshold**: Run `pytest --cov --cov-report=html`, open `htmlcov/index.html` to see missing lines.
4. **CSRF validation failures**: Ensure X-CSRFToken header included in POST requests, get token from `/api/csrf-token`.
5. **Path resolution errors**: Verify `MOTHBOX_HOME` or installation marker file exists, check `python3 mothbox_paths.py` output.

## Performance Targets

- **Camera preview**: 10 FPS sustained, <100ms per frame
- **JPEG encoding**: <50ms per frame with simplejpeg
- **Photo capture**: <5 seconds for single capture, <30 seconds for 5-image focus bracket
- **Test suite**: <2 minutes for unit tests, <10 minutes for full integration suite

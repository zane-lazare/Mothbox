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

**Purpose**: Automatic GPS coordinate embedding in photo EXIF metadata for geotagging.

**Key Components**:
- `webui/backend/lib/gps_exif_lib.py`: Core library (`embed_gps_exif()`, `verify_gps_exif()`, `decimal_to_dms()`)
- `webui/cli/gps_exif_tagger.py`: CLI tool (batch/watch modes)
- `webui/cli/verify_gps_exif.py`: Verification and CSV reporting
- `webui/services/gps-exif-tagger.service`: Optional systemd service

**Documentation**: See `webui/docs/GPS_EXIF_SERVICE.md` (setup) and `webui/docs/GPS_EXIF_USER_GUIDE.md` (usage).

**Tests**: `Tests/unit/test_gps_exif_*.py` (90+ tests), `Tests/integration/test_gps_exif_*.py` (21 tests)

### Series Detection System (Issue #110)

**Purpose**: Automatic detection and grouping of HDR and Focus Bracket photo series.

**Key Components**:
- `webui/backend/lib/series_detection.py`: Pattern matching (`detect_series_type()`, `group_photos_into_series()`)
- `webui/backend/services/series_service.py`: Cached service layer with TTL

**Documentation**: See `webui/docs/dev/api/gallery.md` (Series Endpoints section).

**Tests**: `Tests/unit/test_series_*.py` (96 tests), `Tests/performance/test_series_detection_performance.py`

### Location Clustering System (Issue #115)

**Purpose**: Geographic clustering of photo locations using Haversine distance for map visualization.

**Key Components**:
- `webui/backend/lib/haversine.py`: Distance calculation (`haversine_distance()`, `validate_coordinates()`)
- `webui/backend/lib/geo_clustering.py`: Grid-based clustering (`cluster_locations()`, `calculate_centroid()`)
- `webui/backend/services/clustering_service.py`: Cached service layer
- Frontend: `useClusteredLocations` hook, `ClusterMarker` component

**Documentation**: See `webui/docs/dev/api/gallery.md` (Clustering Endpoints section).

**Tests**: `Tests/unit/test_*clustering*.py` (136 tests), `Tests/integration/test_clustering_workflow.py`

### Full-Text Search System (Issue #131)

**Purpose**: SQLite FTS5-based full-text search with field-specific queries, boolean operators, and BM25 ranking.

**Key Components**:
- `webui/backend/lib/search_engine.py`: FTS5 index management (`index_photo()`, `search()`, `rebuild_index()`)
- `webui/backend/lib/search_query_parser.py`: Query parsing (field:value, AND/OR/NOT, phrases, date ranges)
- `webui/backend/services/search_service.py`: Service layer with automatic index updates

**Documentation**: See `webui/docs/dev/api/search.md` for complete query syntax and API reference.

**Tests**: `Tests/unit/test_search_*.py` (140+ tests), `Tests/integration/test_search_workflow.py`

### Export Job Queue System (Issue #122)

**Purpose**: Async background job queue for photo exports with SQLite persistence and progress tracking.

**Key Components**:
- `webui/backend/lib/export_job_types.py`: Data structures (status, format, filter, progress)
- `webui/backend/lib/export_job_db.py`: SQLite persistence with file locking
- `webui/backend/services/export_job_service.py`: Queue management (single job concurrency, 10-min timeout)

**Formats**: Darwin Core (GBIF), iNaturalist (XMP/ZIP), JSON, CSV

**Design**: Jobs survive restarts, 1-hour TTL, 50-job history, rate-limited (5/min).

**Documentation**: See `webui/docs/dev/api/export-jobs.md` for complete API reference.

**Tests**: `Tests/unit/test_export_job_*.py` (180+ tests), `Tests/integration/test_export_job_workflow.py`

### Export Preset System (Issue #123)

**Purpose**: Reusable export configurations (format, filters, options) for common export scenarios.

**Key Components**:
- `webui/backend/lib/export_preset_types.py`: Data structures
- `webui/backend/export_preset_manager.py`: CRUD with file locking

**Built-in Presets**: `gbif_biodiversity`, `inaturalist_upload`, `simple_json`, `simple_csv`, `hdr_series`, `focus_bracket_series`

**Documentation**: See `webui/docs/dev/api/export-presets.md`.

**Tests**: `Tests/unit/test_export_preset_*.py` (93 tests)

### Cron Bridge System (Issue #215)

**Purpose**: Translates schedule configurations to cron expressions and RTC wakealarm settings.

**Key Components**:
- `webui/backend/lib/cron_bridge.py`: Trigger converters (fixed, interval, solar, moon phase)
- Integration with `scheduler_service.py` for schedule activation

**Documentation**: See `webui/docs/dev/api/cron-bridge.md`.

**Tests**: `Tests/unit/test_cron_bridge.py` (96 tests)

### Deployment Metadata Sidecar System (Issue #114)

**Purpose**: Directory-level metadata files (deployment.json) for photo collections with location, dates, and custom fields.

**Key Components**:
- `webui/backend/lib/deployment_schema.py`: Schema definition and validation
- `webui/backend/lib/deployment_sidecar.py`: CRUD with file locking and hierarchical discovery
- `webui/backend/services/deployment_service.py`: LRU-cached service layer

**Features**: Hierarchical discovery (walks up directory tree), JSON/YAML formats, automatic backups, custom fields (max 100 keys, depth 5).

**Documentation**: See `webui/docs/dev/api/deployment.md` (API) and `webui/docs/DEPLOYMENT_SIDECAR.md` (user guide).

**Tests**: `Tests/unit/test_deployment_*.py` (170+ tests), `Tests/integration/test_deployment_workflow.py`

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

### E2E Testing (Playwright)

Playwright tests run against a real Mothbox Pi server (Firefox, 50 tests).

```bash
cd webui/frontend
npm run test:e2e          # Run all tests
npm run test:e2e:ui       # Interactive UI mode
npm run test:e2e:headed   # Visible browser
```

**Documentation**: See `webui/docs/dev/testing/e2e-testing.md` for complete guide (page objects, rate limiting, adding tests).

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
# CORRECT - Use mothbox_paths module
from mothbox_paths import CONFIG_DIR, PHOTOS_DIR, get_gpio_pins
camera_settings = CONFIG_DIR / "camera_settings.csv"

# WRONG - Never hardcode paths
camera_settings = "/opt/mothbox/camera_settings.csv"
```

### GPIO Pin Access
```python
# CORRECT - Auto-detects firmware version
from mothbox_paths import get_gpio_pins
pins = get_gpio_pins()
Relay_Ch1 = pins['Relay_Ch1']

# WRONG - Breaks on 5.x firmware
Relay_Ch1 = 26
```

### Camera Resource Management
```python
# Use context manager for automatic cleanup
with Picamera2() as camera:
    camera.start()
    # ... operations ...
    camera.stop()

# In tests: use time.sleep(1.0) after close for hardware reset
```

### CSRF Protection
All POST/PUT/DELETE/PATCH routes require CSRF tokens (auto-validated by Flask-WTF). Use `@csrf_exempt` only for WebSocket handshakes.

### GPS Coordinates
Use `webui.shared.gps_coordinates` for decimal ↔ DMS conversion. See `webui/docs/GPS_COORDINATE_UTILITIES.md`.

## Key Files Reference

**Core**:
- `mothbox_paths.py`: Path resolution and hardware config
- `pyproject.toml`: pytest, coverage, bandit, ruff configuration

**Backend** (`webui/backend/`):
- `app.py`: Flask initialization, CSRF, CORS, SocketIO
- `liveview_stream.py`: Camera streaming engine
- `routes/`: API endpoints (camera, gallery, photos, deployment, export)
- `lib/`: Core libraries (search, series detection, clustering, deployment, export jobs)
- `services/`: Cached service layers

**Documentation** (`webui/docs/`):
- `dev/api/`: API reference docs (gallery, search, deployment, export-jobs, cron-bridge)
- User guides: GPS_EXIF, CAMERA_SETTINGS, EXPORT, PRESET_GUIDE, DEPLOYMENT_SIDECAR

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

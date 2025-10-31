"""
Shared pytest fixtures for Mothbox test suite

Provides module-scoped fixtures for camera resources and Flask app context
to prevent resource conflicts and ensure proper cleanup.

Usage:
    - Fixtures are automatically available to all test files
    - Use @pytest.mark.hardware for tests requiring real hardware
    - camera_streamer fixture handles proper resource cleanup
"""

import pytest
import sys
import gc
import time
import os
from pathlib import Path

# Setup path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'webui' / 'backend'))


# ============================================================================
# Test Environment Setup
# ============================================================================

@pytest.fixture(scope='session', autouse=True)
def setup_test_environment():
    """
    Set MOTHBOX_ENV=test for all test sessions

    This ensures mothbox_paths.py uses repository root as MOTHBOX_HOME
    instead of defaulting to /home/pi/Desktop/Mothbox or /opt/mothbox.

    The test mode uses legacy-style path layout where all directories
    (config, data, firmware) are under the repository root.

    Priority:
    1. Respects existing MOTHBOX_ENV if already set
    2. Sets MOTHBOX_ENV=test if not present
    3. Optionally sets MOTHBOX_HOME for clarity

    This fixture runs once per test session before any tests execute.
    """
    if 'MOTHBOX_ENV' not in os.environ:
        os.environ['MOTHBOX_ENV'] = 'test'

    # Also set MOTHBOX_HOME explicitly for clarity (optional, test mode uses __file__ parent)
    if 'MOTHBOX_HOME' not in os.environ:
        test_root = Path(__file__).parent.parent
        os.environ['MOTHBOX_HOME'] = str(test_root)
        print(f"\n🧪 Test Mode: MOTHBOX_HOME={test_root}")

    yield

    # Cleanup not needed - environment persists for entire session


# ============================================================================
# Pytest Markers
# ============================================================================

def pytest_configure(config):
    """Register custom pytest markers (Issue #46 Solution #5)"""
    config.addinivalue_line(
        "markers",
        "hardware: mark test as requiring real Raspberry Pi hardware (camera, GPIO)"
    )
    config.addinivalue_line(
        "markers",
        "photo: test uses photo workflow (subprocess/TakePhoto.py)"
    )
    config.addinivalue_line(
        "markers",
        "stream: test uses stream workflow (live CameraStreamer instance)"
    )
    config.addinivalue_line(
        "markers",
        "both: test uses both photo and stream workflows (needs splitting in Issue #45)"
    )
    config.addinivalue_line(
        "markers",
        "websocket: test uses WebSocket layer for real-time communication"
    )
    config.addinivalue_line(
        "markers",
        "performance: performance/benchmark test (CPU-bound, not hardware-dependent)"
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (multi-component interaction)"
    )
    config.addinivalue_line(
        "markers",
        "calibration: test calibration functionality (photo/stream autofocus and exposure)"
    )


# ============================================================================
# Camera Fixtures
# ============================================================================

@pytest.fixture(scope='module')
def camera_streamer():
    """
    Module-scoped camera streamer fixture

    Provides a single CameraStreamer instance shared across all tests in a module.
    Ensures proper cleanup after all tests complete.

    Usage:
        def test_something(camera_streamer):
            camera_streamer.initialize_camera()
            # ... test code ...
    """
    from liveview_stream import LiveViewStreamer

    class MockSocketIO:
        """Mock SocketIO for testing"""
        def emit(self, event, data, **kwargs):
            pass

    # Create streamer instance
    streamer = LiveViewStreamer(MockSocketIO())

    yield streamer

    # Cleanup after all tests in module complete
    print("\n🧹 Cleaning up camera resources...")
    try:
        streamer.cleanup()
    except Exception as e:
        print(f"⚠️  Warning: Cleanup error: {e}")


@pytest.fixture(scope='function')
def camera_streamer_func():
    """
    Function-scoped camera streamer fixture

    Provides a fresh CameraStreamer instance for each test.
    Use this when tests need complete isolation.

    Usage:
        def test_something(camera_streamer_func):
            camera_streamer_func.initialize_camera()
            # ... test code ...
    """
    from liveview_stream import LiveViewStreamer

    class MockSocketIO:
        """Mock SocketIO for testing"""
        def emit(self, event, data, **kwargs):
            pass

    # Create fresh streamer instance
    streamer = LiveViewStreamer(MockSocketIO())

    yield streamer

    # Cleanup after each test
    try:
        streamer.cleanup()
    except Exception as e:
        print(f"⚠️  Warning: Cleanup error: {e}")


# ============================================================================
# Flask App Fixtures
# ============================================================================

@pytest.fixture(scope='module')
def app():
    """
    Module-scoped Flask app fixture with proper context setup

    Provides a Flask app with:
    - Camera routes registered
    - Config routes registered
    - GPIO routes registered (Issue #78)
    - CAMERA_STREAMER in app.config (fixes test failures)
    - CSRF disabled for testing

    Usage:
        def test_something(app):
            with app.test_client() as client:
                response = client.post('/api/camera/autofocus')
    """
    from flask import Flask
    from routes.camera import camera_bp
    from routes.config import config_bp
    from routes.presets import presets_bp
    from routes.gpio import gpio_bp
    from routes.gps import gps_bp
    from liveview_stream import LiveViewStreamer

    # Create Flask app
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    # Register blueprints with /api prefix to match production
    app.register_blueprint(camera_bp, url_prefix='/api/camera')
    app.register_blueprint(config_bp, url_prefix='/api/config')
    app.register_blueprint(presets_bp, url_prefix='/api')
    app.register_blueprint(gpio_bp, url_prefix='/api/gpio')
    app.register_blueprint(gps_bp, url_prefix='/api/gps')

    # Create camera_streamer and register in app config
    # This is critical - many endpoints expect this
    class MockSocketIO:
        def emit(self, event, data, **kwargs):
            pass

    camera_streamer = LiveViewStreamer(MockSocketIO())
    app.config['CAMERA_STREAMER'] = camera_streamer

    yield app

    # Cleanup camera resources after all tests in module
    try:
        camera_streamer.cleanup()
    except Exception as e:
        print(f"⚠️  Warning: App cleanup error: {e}")


@pytest.fixture(scope='module')
def client(app):
    """
    Module-scoped Flask test client

    Provides a test client for making HTTP requests to the Flask app.

    Usage:
        def test_something(client):
            response = client.post('/api/camera/autofocus')
            assert response.status_code == 200
    """
    return app.test_client()


@pytest.fixture(scope='module')
def socketio_app():
    """
    Module-scoped Flask app with SocketIO and WebSocket handlers

    Provides complete Flask+SocketIO app for WebSocket testing with:
    - All HTTP blueprints registered
    - SocketIO instance configured
    - All WebSocket handlers registered (shared with production)
    - Camera streamer available

    Returns:
        tuple: (socketio, app) for creating test clients

    Usage:
        def test_websocket(socketio_app):
            socketio, app = socketio_app
            client = socketio.test_client(app, namespace='/')
            client.emit('set_af_window', {'x': 0.5, 'y': 0.5})
            received = client.get_received()
    """
    import os
    from flask import Flask
    from flask_socketio import SocketIO
    from routes.camera import camera_bp
    from routes.config import config_bp
    from liveview_stream import LiveViewStreamer
    from websocket_handlers import register_handlers

    # Set MOTHBOX_ENV to development for testing
    # This prevents config from requiring SECRET_KEY when handlers import it
    # Save original value for restoration
    original_env = os.environ.get('MOTHBOX_ENV')
    os.environ['MOTHBOX_ENV'] = 'development'

    try:
        # Create Flask app
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False

        # Create SocketIO
        socketio = SocketIO(app, cors_allowed_origins='*')

        # Register HTTP blueprints
        app.register_blueprint(camera_bp, url_prefix='/api/camera')
        app.register_blueprint(config_bp, url_prefix='/api/config')

        # Create camera streamer (uses real SocketIO for testing)
        class MockSocketIO:
            """Mock SocketIO for camera streamer initialization"""
            def emit(self, event, data, **kwargs):
                pass

        camera_streamer = LiveViewStreamer(MockSocketIO())
        app.config['CAMERA_STREAMER'] = camera_streamer

        # Register WebSocket handlers (same as production!)
        register_handlers(socketio, camera_streamer)

        yield socketio, app

    finally:
        # Cleanup camera resources
        try:
            camera_streamer.cleanup()
        except Exception as e:
            print(f"⚠️  Warning: SocketIO app cleanup error: {e}")

        # Restore original MOTHBOX_ENV value
        if original_env is not None:
            os.environ['MOTHBOX_ENV'] = original_env
        else:
            os.environ.pop('MOTHBOX_ENV', None)


# ============================================================================
# Test Isolation Fixtures (Issue #46 Phase 2)
# ============================================================================

@pytest.fixture
def mock_socketio():
    """
    Mock SocketIO for testing CameraStreamer

    Provides a minimal SocketIO interface for tests that instantiate
    CameraStreamer directly without needing a real WebSocket connection.

    Usage:
        def test_something(mock_socketio):
            streamer = CameraStreamer(mock_socketio)
            # ... test code ...
    """
    class MockSocketIO:
        """Mock SocketIO that silently accepts all emit() calls"""
        def emit(self, event, data, **kwargs):
            pass

    return MockSocketIO()


def patch_path_constant_everywhere(monkeypatch, constant_name, temp_path):
    """
    Helper to patch a path constant in mothbox_paths AND all modules that imported it.

    This solves the "import timing" problem where module-scoped fixtures (like app)
    import route modules BEFORE function-scoped path fixtures run. Those route modules
    capture the constant value at import time, so patching mothbox_paths alone has no effect.

    Args:
        monkeypatch: pytest's monkeypatch fixture
        constant_name: Name of the constant (e.g., 'LIVEVIEW_SETTINGS_FILE')
        temp_path: Temporary Path object to use instead

    Implementation:
        1. Patch the source module (mothbox_paths)
        2. Check sys.modules for already-loaded modules
        3. Patch the constant in each loaded module that has it

    Example:
        patch_path_constant_everywhere(monkeypatch, 'LIVEVIEW_SETTINGS_FILE', temp_file)
        # Now routes.config.LIVEVIEW_SETTINGS_FILE points to temp_file

    Related: Issue #13 Phase 1 - Path constant patching (73 affected tests)
    """
    import sys
    import mothbox_paths

    # Step 1: Patch the source module
    monkeypatch.setattr(mothbox_paths, constant_name, temp_path)

    # Step 2: Define modules that might have imported this constant
    # Map constant name to list of module paths that import it
    MODULE_IMPORT_MAP = {
        'LIVEVIEW_SETTINGS_FILE': [
            'routes.config',
            'routes.camera',
            'routes.presets',
            # Note: liveview_stream uses mothbox_paths.LIVEVIEW_SETTINGS_FILE (qualified)
            # so it doesn't need patching - it reads from source module
        ],
        'WEBUI_SETTINGS_FILE': [
            # WEBUI_SETTINGS_FILE is an alias for LIVEVIEW_SETTINGS_FILE
            # Same modules, handled together
            'routes.config',
            'routes.camera',
            'routes.presets',
        ],
        'CAMERA_SETTINGS_FILE': [
            'routes.config',
            'routes.camera',
            'routes.presets',
            'routes.system',
        ],
        'CONTROLS_FILE': [
            'routes.config',
            'routes.camera',
            'routes.gps',
            'routes.gpio',
            'routes.system',
        ],
        'DATA_DIR': [
            'routes.gpio',  # Issue #78 - GPIO state file
        ],
        'SCHEDULE_SETTINGS_FILE': [
            'routes.config',  # Issue #78 - Schedule settings
        ],
    }

    # Step 3: Get list of modules to patch for this constant
    modules_to_patch = MODULE_IMPORT_MAP.get(constant_name, [])

    # Step 4: Patch each module IF it's already loaded in sys.modules
    patched_count = 0
    for module_path in modules_to_patch:
        if module_path in sys.modules:
            module = sys.modules[module_path]
            # Check if module actually has this attribute (might not if import failed)
            if hasattr(module, constant_name):
                monkeypatch.setattr(module, constant_name, temp_path)
                patched_count += 1


@pytest.fixture
def temp_webui_settings(tmp_path, monkeypatch):
    """
    Temporary webui_settings.txt for isolated testing

    Creates a temporary settings file and patches BOTH mothbox_paths module
    AND any route modules that have already imported the constants.

    This ensures tests don't modify the real settings file, even when using
    the module-scoped app fixture (which imports routes before this fixture runs).

    Usage:
        def test_something(temp_webui_settings):
            # Write test settings
            with open(temp_webui_settings, 'w') as f:
                f.write("sharpness=2.0\\n")
            # ... test code ...

    Related: Issue #13 Phase 1 - Path constant patching fix
    """
    import mothbox_paths

    # Create temporary file
    temp_file = tmp_path / "webui_settings.txt"
    temp_file.touch()

    # Patch both aliases everywhere (WEBUI_SETTINGS_FILE and LIVEVIEW_SETTINGS_FILE are the same)
    patch_path_constant_everywhere(monkeypatch, 'WEBUI_SETTINGS_FILE', temp_file)
    patch_path_constant_everywhere(monkeypatch, 'LIVEVIEW_SETTINGS_FILE', temp_file)

    yield temp_file
    # Cleanup happens automatically with tmp_path and monkeypatch


@pytest.fixture
def temp_camera_settings(tmp_path, monkeypatch):
    """
    Temporary camera_settings.csv for isolated testing

    Creates a temporary settings file and patches BOTH mothbox_paths module
    AND any route modules that have already imported the constant.

    This ensures photo workflow tests don't modify real settings, even when
    using the module-scoped app fixture.

    Usage:
        def test_something(temp_camera_settings):
            # Write test settings
            with open(temp_camera_settings, 'w') as f:
                f.write("ExposureTime,500\\n")
            # ... test code ...

    Related: Issue #13 Phase 1 - Path constant patching fix
    """
    import mothbox_paths

    # Create temporary file with CSV header
    temp_file = tmp_path / "camera_settings.csv"
    temp_file.write_text("SETTING,VALUE,DETAILS\n")

    # Patch everywhere (source module + imported modules)
    patch_path_constant_everywhere(monkeypatch, 'CAMERA_SETTINGS_FILE', temp_file)

    yield temp_file
    # Cleanup happens automatically with tmp_path and monkeypatch


@pytest.fixture
def temp_schedule_settings(tmp_path, monkeypatch):
    """
    Temporary schedule_settings.csv for isolated testing

    Creates a temporary schedule settings file and patches BOTH mothbox_paths
    module AND any route modules that have already imported the constant.

    Usage:
        def test_something(temp_schedule_settings):
            # Write test settings
            temp_schedule_settings.write_text("weekdays,hours,minutes,runtime\\n1,8,0,60\\n")
            # ... test code ...

    Related: Issue #78 - Config routes testing
    """
    import mothbox_paths

    # Create temporary file with CSV header
    temp_file = tmp_path / "schedule_settings.csv"
    temp_file.write_text("weekdays,hours,minutes,runtime\n")

    # Patch everywhere (source module + imported modules)
    patch_path_constant_everywhere(monkeypatch, 'SCHEDULE_SETTINGS_FILE', temp_file)

    yield temp_file
    # Cleanup happens automatically with tmp_path and monkeypatch


# ============================================================================
# AF Window Test Fixtures (Click-to-Focus Feature)
# ============================================================================

@pytest.fixture
def af_window_test_positions():
    """
    Common test positions for AF window testing

    Provides standard positions for comprehensive AF window testing including
    corners, edges, and center positions.

    Returns:
        list: Tuples of (x, y, name) for testing

    Usage:
        def test_af_positions(camera_streamer, af_window_test_positions):
            for x, y, name in af_window_test_positions:
                camera_streamer.set_af_window(x, y)
    """
    return [
        (0.5, 0.5, "center"),
        (0.25, 0.25, "upper-left"),
        (0.75, 0.25, "upper-right"),
        (0.25, 0.75, "lower-left"),
        (0.75, 0.75, "lower-right"),
        (0.5, 0.0, "top-center"),
        (0.5, 1.0, "bottom-center"),
        (0.0, 0.5, "left-center"),
        (1.0, 0.5, "right-center"),
        (0.0, 0.0, "top-left-corner"),
        (1.0, 0.0, "top-right-corner"),
        (0.0, 1.0, "bottom-left-corner"),
        (1.0, 1.0, "bottom-right-corner"),
    ]


# ============================================================================
# Workflow-Specific Fixtures (Issue #46)
# ============================================================================

@pytest.fixture
def photo_ready(app):
    """
    Prepare for photo workflow tests (Issue #46 Solution #1)

    Ensures camera is released so subprocess (TakePhoto.py) can use it.
    Use this fixture for tests that call endpoints triggering subprocess operations:
    - /api/camera/calibrate-photo (future)
    - /api/camera/test-capture
    - Any endpoint that runs TakePhoto.py

    Usage:
        def test_photo_calibration(client, photo_ready):
            response = client.post('/api/camera/calibrate-photo')
    """
    camera_streamer = app.config.get('CAMERA_STREAMER')

    # BEFORE test: Release camera if held
    if camera_streamer and camera_streamer.camera:
        print("📸 Preparing for photo workflow - releasing camera...")
        camera_streamer.release_camera()
        time.sleep(2.0)  # Ensure hardware fully released

    yield

    # AFTER test: Ensure camera still released
    if camera_streamer and camera_streamer.camera:
        print("⚠️  Warning: Photo test left camera open - cleaning up...")
        camera_streamer.release_camera()
        time.sleep(2.0)


@pytest.fixture
def stream_ready(app):
    """
    Prepare for stream workflow tests (Issue #46 Solution #1)

    Ensures CameraStreamer is initialized and ready for streaming.
    Use this fixture for tests that use the live camera instance:
    - /api/camera/calibrate-stream (future)
    - /api/camera/autofocus (stream mode)
    - Live control updates

    Usage:
        def test_stream_calibration(client, stream_ready):
            response = client.post('/api/camera/calibrate-stream')
    """
    camera_streamer = app.config.get('CAMERA_STREAMER')

    if not camera_streamer:
        pytest.skip("Camera streamer not available")

    # BEFORE test: Initialize camera if needed
    if not camera_streamer.camera:
        print("📹 Preparing for stream workflow - initializing camera...")
        if not camera_streamer.initialize_camera():
            pytest.skip("Camera initialization failed - hardware may not be available")

    # Start streaming for tests that need it
    if not camera_streamer.streaming:
        camera_streamer.start_streaming()

    yield camera_streamer

    # AFTER test: Stop streaming but keep camera initialized
    if camera_streamer.streaming:
        camera_streamer.stop_streaming()


@pytest.fixture
def integration_ready(app):
    """
    Prepare for integration tests requiring exclusive camera access (Issue #46 Solution #6)

    Ensures camera is fully released before test starts, preventing "Pipeline handler
    in use by another process" errors when tests try to initialize the camera.

    Use this fixture for integration tests that:
    - Initialize camera directly (CameraStreamer.initialize_camera)
    - Use stream_ready fixture (which calls initialize_camera)
    - Need guaranteed exclusive hardware access

    Usage:
        @pytest.mark.hardware
        def test_camera_operation(client, integration_ready):
            response = client.post('/api/camera/autofocus')
    """
    camera_streamer = app.config.get('CAMERA_STREAMER')

    if not camera_streamer:
        pytest.skip("Camera streamer not available")

    # BEFORE test: Release camera to allow exclusive access
    if camera_streamer.camera or camera_streamer.streaming:
        print("\n📹 Integration setup: Ensuring camera fully released...")
        camera_streamer.release_camera()
        time.sleep(2.0)  # Match timing from routes/camera.py patterns
        print("   ✓ Camera released - ready for exclusive access")

    yield camera_streamer

    # AFTER test: Release again to prevent pollution
    if camera_streamer.camera or camera_streamer.streaming:
        print("\n🧹 Integration cleanup: Releasing camera...")
        camera_streamer.release_camera()
        time.sleep(1.0)


# ============================================================================
# Pytest Hooks
# ============================================================================

def pytest_collection_modifyitems(config, items):
    """
    Automatically mark tests requiring hardware

    Tests in integration/ directory are automatically marked with @pytest.mark.hardware
    unless they're:
    - manual verification tests
    - installer workflow tests (use mocks/tmp_path, no actual hardware needed)
    """
    for item in items:
        # Mark integration tests (except manual verification and installer) as hardware tests
        fspath_str = str(item.fspath)
        is_integration = 'integration' in fspath_str
        is_manual = 'manual_verification' in fspath_str
        is_installer = 'installer' in fspath_str  # installer_workflows or installer_helpers

        if is_integration and not is_manual and not is_installer:
            item.add_marker(pytest.mark.hardware)


@pytest.fixture(scope='session', autouse=True)
def camera_session_setup():
    """
    Session-level camera management for integration tests (Issue #46 Solution #6)

    Announces test session start/end and ensures proper cleanup.
    Actual camera release happens per-test in pytest_runtest_setup.
    """
    print("\n" + "="*70)
    print("🧪 Starting test session - camera will be released before integration tests")
    print("="*70)

    yield

    print("\n" + "="*70)
    print("🧹 Test session complete - all camera resources released")
    print("="*70)


def pytest_runtest_setup(item):
    """
    Setup before each test (Issue #46 Solution #6: Enhanced camera release)

    1. Skip hardware tests if not on Raspberry Pi
    2. Release camera before integration tests to prevent "Pipeline handler in use" errors
    3. Handles module-scoped camera_streamer conflicts
    """
    hardware_marker = item.get_closest_marker('hardware')
    if hardware_marker:
        # Check if running on Raspberry Pi
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
                if 'Raspberry Pi' not in cpuinfo:
                    pytest.skip("Hardware tests require Raspberry Pi")
        except FileNotFoundError:
            pytest.skip("Hardware tests require Raspberry Pi")

        # Camera availability check disabled - causes conflicts with test camera initialization
        # The global_camera_info() call creates internal libcamera state that prevents
        # tests from initializing their own camera instances.
        # Tests will fail naturally if camera is not available.

    # NEW: Release camera before tests using camera_streamer fixture
    # This handles both unit and integration tests with module-scoped camera_streamer
    if 'camera_streamer' in item.fixturenames:
        try:
            # Get camera_streamer fixture (works for both unit and integration tests)
            camera_streamer = item.getfixturevalue('camera_streamer')

            if camera_streamer and (camera_streamer.camera or camera_streamer.streaming):
                print(f"\n🔄 Pre-test setup: Releasing camera for {item.name}...")
                camera_streamer.release_camera()
                time.sleep(2.0)  # Ensure hardware fully released (Issue #46)
                print("   ✓ Camera released and ready")
        except Exception as e:
            # Fixture may not be available yet or camera not initialized - that's OK
            pass


@pytest.fixture(autouse=True)
def verify_camera_state(request):
    """
    Verify and enforce clean camera state before/after each test (Issue #46 Solution #2)

    This autouse fixture automatically runs for every test and ensures:
    - Photo tests start with camera released
    - Stream tests start with camera initialized
    - Tests clean up after themselves
    - State pollution is detected and logged

    Works with both integration tests (app fixture) and unit tests (camera_streamer fixture).
    """
    # Try to get camera_streamer from either app fixture or camera_streamer fixture
    camera_streamer = None

    # Integration tests: Get from app.config
    if 'app' in request.fixturenames:
        try:
            app = request.getfixturevalue('app')
            camera_streamer = app.config.get('CAMERA_STREAMER')
        except Exception:
            pass

    # Unit tests: Get camera_streamer fixture directly
    if not camera_streamer and 'camera_streamer' in request.fixturenames:
        try:
            camera_streamer = request.getfixturevalue('camera_streamer')
        except Exception:
            pass

    if not camera_streamer:
        yield
        return

    # BEFORE test: Prepare camera based on test markers
    photo_marker = request.node.get_closest_marker('photo')
    stream_marker = request.node.get_closest_marker('stream')

    if photo_marker:
        # Photo tests need clean slate
        if camera_streamer.camera:
            print(f"📸 Photo test {request.node.name} - releasing camera from previous test...")
            camera_streamer.release_camera()
            time.sleep(2.0)
    elif stream_marker:
        # Stream tests need initialized camera
        if not camera_streamer.camera:
            print(f"📹 Stream test {request.node.name} - initializing camera...")
            camera_streamer.initialize_camera()

    yield  # Run the test

    # AFTER test: Verify cleanup based on marker
    if photo_marker:
        # Photo tests should have released camera
        if camera_streamer.camera:
            print(f"⚠️  WARNING: Photo test {request.node.name} left camera open!")
            camera_streamer.release_camera()
            time.sleep(2.0)
    elif stream_marker:
        # Stream tests should stop streaming
        if camera_streamer.streaming:
            print(f"⚠️  WARNING: Stream test {request.node.name} left streaming active!")
            camera_streamer.stop_streaming()


@pytest.fixture
def temp_controls_file(tmp_path, monkeypatch):
    """
    Create temporary controls.txt for isolated testing.

    Creates a temporary controls file and patches BOTH mothbox_paths module
    AND any route modules that have already imported CONTROLS_FILE constant.

    This fixture ensures tests:
    - Don't modify real configuration files
    - Run in isolation (each test gets fresh file)
    - Work correctly with module-scoped app fixture
    - Work on any platform (no hardware dependencies)

    Usage:
        def test_something(temp_controls_file):
            temp_controls_file.write_text("Relay_Ch1=5\\n")
            # Test code using patched CONTROLS_FILE...

    Related: Issue #13 Phase 1 - Path constant patching fix
    """
    import mothbox_paths

    # Create temporary file
    temp_file = tmp_path / "controls.txt"
    temp_file.touch()

    # Patch everywhere (source module + imported modules)
    patch_path_constant_everywhere(monkeypatch, 'CONTROLS_FILE', temp_file)

    yield temp_file
    # Cleanup happens automatically with tmp_path and monkeypatch


@pytest.fixture
def controls_file_factory(tmp_path):
    """
    Factory fixture for creating controls.txt files with custom content.

    Allows creating multiple controls files in a single test for comparison.

    Usage:
        def test_multiple_configs(controls_file_factory):
            config1 = controls_file_factory("Relay_Ch1=5\\n")
            config2 = controls_file_factory("Relay_Ch1=10\\n")
            # Compare behaviors...

    Related: Issue #13 Phase 1 (hardware configuration testing)
    """
    def _create_controls(content: str) -> Path:
        """Create a controls file with the given content"""
        controls = tmp_path / f"controls_{id(content)}.txt"
        controls.write_text(content)
        return controls

    return _create_controls


@pytest.fixture
def assert_gpio_pins_equal():
    """
    Helper to compare GPIO pin dictionaries with clear error messages.

    Provides better error messages than direct dict comparison by checking
    each key individually and showing which pin mismatched.

    Usage:
        def test_pins(assert_gpio_pins_equal):
            actual = get_gpio_pins()
            expected = {'Relay_Ch1': 5, 'Relay_Ch2': 19, 'Relay_Ch3': 9}
            assert_gpio_pins_equal(actual, expected, "5.x firmware pins")

    Related: Issue #13 Phase 1 (hardware configuration testing)
    """
    def _assert_equal(actual, expected, message=""):
        """Compare two GPIO pin dictionaries with detailed error messages"""
        for key in expected:
            assert key in actual, f"{message}: Missing key {key}"
            assert actual[key] == expected[key], \
                f"{message}: {key} mismatch - expected {expected[key]}, got {actual[key]}"

    return _assert_equal


# ============================================================================
# Unit Test Mocking Fixtures (Issue #78 - Backend Route Testing)
# ============================================================================

@pytest.fixture
def temp_gpio_state_file(tmp_path, monkeypatch):
    """
    Temporary GPIO state file for isolated testing.

    Creates temporary gpio_state.json and patches DATA_DIR and STATE_FILE
    to ensure tests don't modify real GPIO state.

    Usage:
        def test_gpio_status(temp_gpio_state_file):
            # Test will use isolated state file
            response = client.get('/api/gpio/status')

    Related: Issue #78 - GPIO routes testing
    """
    # Create temporary state file with default state
    state_file = tmp_path / "gpio_state.json"
    state_file.write_text('{"Relay_Ch1": false, "Relay_Ch2": false, "Relay_Ch3": false}')

    # Patch DATA_DIR to point to tmp_path
    patch_path_constant_everywhere(monkeypatch, 'DATA_DIR', tmp_path)

    # Also directly patch STATE_FILE in routes.gpio if already loaded
    import sys
    if 'routes.gpio' in sys.modules:
        monkeypatch.setattr('routes.gpio.STATE_FILE', state_file)

    yield state_file
    # Cleanup automatic with tmp_path


@pytest.fixture
def mock_rpi_gpio(monkeypatch):
    """
    Mock RPi.GPIO module for GPIO tests without hardware.

    Provides MockGPIO class that tracks setup/output/cleanup calls
    for verification in tests.

    Usage:
        def test_gpio_control(mock_rpi_gpio):
            # GPIO module is mocked, calls tracked
            response = client.post('/api/gpio/control', json={...})
            assert mock_rpi_gpio.outputs[0] == (26, 1)

    Related: Issue #78 - GPIO routes testing
    """
    class MockGPIO:
        BCM = 'BCM'
        OUT = 'OUT'
        HIGH = 1
        LOW = 0

        setups = []  # Track setup() calls
        outputs = []  # Track output() calls
        cleanups = []  # Track cleanup() calls

        @classmethod
        def setmode(cls, mode):
            pass

        @classmethod
        def setwarnings(cls, enabled):
            pass

        @classmethod
        def setup(cls, pin, mode, initial=None):
            cls.setups.append((pin, mode, initial))

        @classmethod
        def output(cls, pin, value):
            cls.outputs.append((pin, value))

        @classmethod
        def cleanup(cls, pin=None):
            cls.cleanups.append(pin)

        @classmethod
        def reset_tracking(cls):
            cls.setups.clear()
            cls.outputs.clear()
            cls.cleanups.clear()

    # Inject mock into sys.modules and patch routes.gpio
    import sys
    sys.modules['RPi'] = type(sys)('RPi')
    sys.modules['RPi.GPIO'] = MockGPIO

    # Patch module-level constants in routes.gpio if already loaded
    if 'routes.gpio' in sys.modules:
        # Set GPIO attribute if it doesn't exist
        if not hasattr(sys.modules['routes.gpio'], 'GPIO'):
            setattr(sys.modules['routes.gpio'], 'GPIO', MockGPIO)
        else:
            monkeypatch.setattr('routes.gpio.GPIO', MockGPIO)

        monkeypatch.setattr('routes.gpio.GPIO_AVAILABLE', True)
        monkeypatch.setattr('routes.gpio.GPIO_PERMISSIONS_OK', True)

    yield MockGPIO

    # Cleanup
    MockGPIO.reset_tracking()
    if 'RPi' in sys.modules:
        del sys.modules['RPi']
    if 'RPi.GPIO' in sys.modules:
        del sys.modules['RPi.GPIO']


@pytest.fixture
def mock_picamera2_for_streamer():
    """
    Comprehensive Picamera2 mock for LiveViewStreamer tests.

    Simulates camera initialization, configuration, streaming,
    and control application without requiring hardware.

    Usage:
        def test_camera_init(mock_picamera2_for_streamer):
            with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer):
                streamer = LiveViewStreamer(mock_socketio())
                assert streamer.initialize_camera() == True

    Related: Issue #78 - LiveView streamer testing
    """
    class MockPicamera2:
        def __init__(self, camera_num=0, tuning=None):
            self.camera_num = camera_num
            self.tuning = tuning
            self.started = False
            self.streaming = False
            self.controls = {}
            self.sensor_modes = [
                {'size': (1920, 1080)},
                {'size': (2304, 1736)},
                {'size': (4608, 2592)}
            ]
            self.camera_properties = {
                'PixelArraySize': (4608, 2592),
                'ScalerCropMaximum': (0, 0, 4608, 2592)
            }

        def create_video_configuration(self, main=None, raw=None, encode=None):
            return {'main': main, 'raw': raw, 'encode': encode}

        def configure(self, config):
            self.config = config

        def camera_configuration(self):
            return self.config

        def start(self):
            if self.started:
                raise RuntimeError("Camera already started")
            self.started = True

        def stop(self):
            self.started = False

        def start_recording(self, encoder, output):
            self.streaming = True

        def stop_recording(self):
            self.streaming = False

        def capture_array(self):
            import numpy as np
            return np.zeros((768, 1024, 3), dtype=np.uint8)

        def capture_metadata(self):
            return {
                'AfState': 2,  # Focused
                'ExposureTime': 500,
                'AnalogueGain': 8.0,
                'LensPosition': 1.5
            }

        def capture_request(self):
            class MockRequest:
                def get_metadata(self):
                    return {
                        'AfState': 2,
                        'ExposureTime': 500
                    }
                def release(self):
                    pass
            return MockRequest()

        def set_controls(self, controls):
            self.controls.update(controls)

        def close(self):
            self.started = False
            self.streaming = False

    return MockPicamera2()


@pytest.fixture
def mock_file_locking(monkeypatch):
    """
    Mock fcntl.flock for file locking tests.

    Tracks lock acquisitions/releases and simulates
    blocking behavior for concurrency testing.

    Usage:
        def test_file_locking(mock_file_locking):
            # flock calls are tracked
            _get_state()
            assert len(mock_file_locking.locks_acquired) > 0

    Related: Issue #78 - Concurrency testing
    """
    try:
        import fcntl as real_fcntl
    except ImportError:
        # Not available on Windows - create stub
        class real_fcntl:
            LOCK_EX = 2
            LOCK_SH = 1
            LOCK_UN = 8
            LOCK_NB = 4

    class MockFlock:
        locks_acquired = []
        locks_released = []
        should_block = False

        @classmethod
        def flock(cls, fd, operation):
            if operation & real_fcntl.LOCK_EX:
                if cls.should_block:
                    raise BlockingIOError("Resource temporarily unavailable")
                cls.locks_acquired.append(('exclusive', fd))
            elif operation & real_fcntl.LOCK_SH:
                cls.locks_acquired.append(('shared', fd))
            elif operation & real_fcntl.LOCK_UN:
                cls.locks_released.append(fd)

        @classmethod
        def reset(cls):
            cls.locks_acquired.clear()
            cls.locks_released.clear()
            cls.should_block = False

    monkeypatch.setattr('fcntl.flock', MockFlock.flock)

    yield MockFlock

    MockFlock.reset()


def pytest_runtest_teardown(item, nextitem):
    """
    Force garbage collection after each test to prevent memory exhaustion

    Camera operations allocate CMA (Contiguous Memory Allocator) memory for
    image buffers. Explicit GC helps free these buffers between tests.

    Note: With adequate CMA allocation (256MB+), the delays are not needed.
    The GC calls are kept as defensive cleanup.
    """
    # Force garbage collection to free camera buffers
    # Multiple collections handle circular references in camera objects
    gc.collect()
    gc.collect()

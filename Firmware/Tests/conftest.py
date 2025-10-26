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
from pathlib import Path

# Setup path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'webui' / 'backend'))


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
    from camera_stream import CameraStreamer

    class MockSocketIO:
        """Mock SocketIO for testing"""
        def emit(self, event, data, **kwargs):
            pass

    # Create streamer instance
    streamer = CameraStreamer(MockSocketIO())

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
    from camera_stream import CameraStreamer

    class MockSocketIO:
        """Mock SocketIO for testing"""
        def emit(self, event, data, **kwargs):
            pass

    # Create fresh streamer instance
    streamer = CameraStreamer(MockSocketIO())

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
    from camera_stream import CameraStreamer

    # Create Flask app
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    # Register blueprints with /api prefix to match production
    app.register_blueprint(camera_bp, url_prefix='/api/camera')
    app.register_blueprint(config_bp, url_prefix='/api/config')
    app.register_blueprint(presets_bp, url_prefix='/api')

    # Create camera_streamer and register in app config
    # This is critical - many endpoints expect this
    class MockSocketIO:
        def emit(self, event, data, **kwargs):
            pass

    camera_streamer = CameraStreamer(MockSocketIO())
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
    from camera_stream import CameraStreamer
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

        camera_streamer = CameraStreamer(MockSocketIO())
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


@pytest.fixture
def temp_webui_settings(tmp_path, monkeypatch):
    """
    Temporary webui_settings.txt for isolated testing

    Creates a temporary settings file and patches mothbox_paths.WEBUI_SETTINGS_FILE
    to point to it. This ensures tests don't modify the real settings file.

    Usage:
        def test_something(temp_webui_settings):
            # Write test settings
            with open(temp_webui_settings, 'w') as f:
                f.write("sharpness=2.0\\n")
            # ... test code ...
    """
    import mothbox_paths

    # Create temporary file
    temp_file = tmp_path / "webui_settings.txt"
    temp_file.touch()

    # Patch the module-level constant (use Path object, not string)
    monkeypatch.setattr(mothbox_paths, 'WEBUI_SETTINGS_FILE', temp_file)

    yield temp_file
    # Cleanup happens automatically with tmp_path


@pytest.fixture
def temp_camera_settings(tmp_path, monkeypatch):
    """
    Temporary camera_settings.csv for isolated testing

    Creates a temporary settings file and patches mothbox_paths.CAMERA_SETTINGS_FILE
    to point to it. This ensures photo workflow tests don't modify real settings.

    Usage:
        def test_something(temp_camera_settings):
            # Write test settings
            with open(temp_camera_settings, 'w') as f:
                f.write("ExposureTime,500\\n")
            # ... test code ...
    """
    import mothbox_paths

    # Create temporary file
    temp_file = tmp_path / "camera_settings.csv"
    temp_file.touch()

    # Patch the module-level constant (use Path object, not string)
    monkeypatch.setattr(mothbox_paths, 'CAMERA_SETTINGS_FILE', temp_file)

    yield temp_file
    # Cleanup happens automatically with tmp_path


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
    unless they're manual verification tests.
    """
    for item in items:
        # Mark integration tests (except manual verification) as hardware tests
        if 'integration' in str(item.fspath) and 'manual_verification' not in str(item.fspath):
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

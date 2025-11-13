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
def camera_streamer_func(tmp_path, monkeypatch):
    """
    Function-scoped camera streamer fixture with isolated config

    Provides a fresh CameraStreamer instance for each test with
    temporary liveview_settings.txt for complete test isolation.

    This ensures tests don't depend on real liveview_settings.txt
    and get consistent hardcoded defaults in both dev and CI.

    Usage:
        def test_something(camera_streamer_func):
            camera_streamer_func.initialize_camera()
            # ... test code ...
    """
    from liveview_stream import LiveViewStreamer

    # Create temp config file (empty = use hardcoded defaults)
    temp_liveview = tmp_path / "liveview_settings.txt"
    temp_liveview.write_text("")  # Empty file

    # Patch path everywhere using established helper
    patch_path_constant_everywhere(monkeypatch, 'LIVEVIEW_SETTINGS_FILE', temp_liveview)

    class MockSocketIO:
        """Mock SocketIO for testing"""
        def emit(self, event, data, **kwargs):
            pass

    # Create fresh streamer instance (will use temp path)
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
    app.register_blueprint(presets_bp, url_prefix='/api/presets')
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
# Test Isolation Fixtures (Issue #46)
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

    Related: Issue #13 - Path constant patching (73 affected tests)
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
            'lib.gps_exif_lib',  # Issue #98 - GPS EXIF embedding
        ],
        'DATA_DIR': [
            'routes.gpio',  # Issue #78 - GPIO state file
        ],
        'SCHEDULE_SETTINGS_FILE': [
            'routes.config',  # Issue #78 - Schedule settings
        ],
        'PHOTOS_DIR': [
            'routes.camera',  # Issue #134 - Thumbnail cache testing
            'routes.gallery',  # Issue #134 - Thumbnail cache testing
            'routes.metadata',  # Issue #99 - Metadata API testing
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

    Related: Issue #13 - Path constant patching fix
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

    Related: Issue #13 - Path constant patching fix
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
def temp_liveview_settings(tmp_path, monkeypatch):
    """
    Temporary liveview_settings.txt for isolated testing

    Creates a temporary settings file and patches BOTH mothbox_paths module
    AND any route modules that have already imported the constant.

    This ensures liveview tests don't modify real settings, even when
    using the module-scoped app fixture.

    Usage:
        def test_something(temp_liveview_settings):
            # Write test settings
            with open(temp_liveview_settings, 'w') as f:
                f.write("sharpness=1.5\\n")
            # ... test code ...

    Related: Issue #78 - Test capture workflows
    """
    import mothbox_paths

    # Create temporary file (empty by default)
    temp_file = tmp_path / "liveview_settings.txt"
    temp_file.write_text("")

    # Patch everywhere (source module + imported modules)
    patch_path_constant_everywhere(monkeypatch, 'LIVEVIEW_SETTINGS_FILE', temp_file)

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


@pytest.fixture
def temp_preferences_file(tmp_path, monkeypatch):
    """
    Temporary user_preferences.json for isolated testing

    Creates a temporary preferences file and patches USER_PREFERENCES_FILE
    constant everywhere. Also recreates the global preferences_manager instance
    to use the temp file.

    This ensures preferences tests don't modify real user preferences.

    Usage:
        def test_something(temp_preferences_file):
            # preferences_manager now uses temp file
            # Write/read test preferences
            temp_preferences_file.write_text('{"default_capture_preset": "test"}')
            # ... test code ...

    Related: Issue #78 - User preferences testing
    """
    import json

    # Create temporary file with default preferences
    temp_file = tmp_path / "user_preferences.json"
    temp_file.write_text(json.dumps({
        "default_capture_preset": None,
        "default_preview_preset": None,
        "default_liveview_preset": None
    }, indent=2))

    # Patch the constant in mothbox_paths
    import mothbox_paths
    monkeypatch.setattr(mothbox_paths, 'USER_PREFERENCES_FILE', temp_file)

    # Recreate the global preferences_manager instance with temp path
    # This is needed because the manager was already instantiated at module import time
    from webui.backend import user_preferences
    from webui.backend.user_preferences import UserPreferencesManager

    new_manager = UserPreferencesManager(temp_file)
    monkeypatch.setattr(user_preferences, 'preferences_manager', new_manager)

    # Also patch in routes.preferences if already loaded
    import sys
    if 'routes.preferences' in sys.modules:
        monkeypatch.setattr('routes.preferences.preferences_manager', new_manager)

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
# Module-Level Instance Mocking Fixtures (Issue #78)
# ============================================================================

@pytest.fixture
def mock_picamera2():
    """
    Comprehensive mock for Picamera2 class with state tracking

    Mocks the entire Picamera2 API used by camera routes including:
    - Camera initialization and lifecycle (start/stop/close)
    - Configuration (preview, still, video)
    - Control setting (exposure, focus, white balance)
    - Capture operations (files, metadata, arrays)
    - Autofocus cycle
    - State transitions

    The mock tracks state to enable realistic testing:
    - camera_state: 'stopped' → 'configured' → 'started' → 'stopped'
    - controls: dict of currently applied controls
    - configurations: history of applied configurations

    Usage:
        def test_autofocus(client, mock_picamera2, monkeypatch):
            # Inject mock into sys.modules before import
            monkeypatch.setitem(sys.modules, 'picamera2', mock_picamera2)

            # Configure expected behavior
            mock_picamera2.Picamera2.return_value.autofocus_cycle.return_value = True
            mock_picamera2.Picamera2.return_value.capture_metadata.return_value = {
                'LensPosition': 5.5,
                'AfState': 2,  # Success
                'ExposureTime': 10000,
                'AnalogueGain': 1.5
            }

            # Make request (will use mocked Picamera2)
            response = client.post('/api/camera/autofocus')

            # Verify mock was called correctly
            assert mock_picamera2.Picamera2.called
            assert mock_picamera2.Picamera2.return_value.autofocus_cycle.called

    Pattern: This uses sys.modules injection (similar to RPi.GPIO mock) because
    Picamera2 is imported dynamically inside route functions with try/except.

    Related: Issue #78 - Camera testing infrastructure
    """
    from unittest.mock import MagicMock, Mock
    import sys

    # Create mock module
    mock_picamera2_module = MagicMock()

    # Create mock instance that will be returned by Picamera2()
    mock_instance = MagicMock()

    # Track camera state for realistic behavior
    mock_instance.camera_state = 'stopped'
    mock_instance.controls_history = []
    mock_instance.config_history = []

    # ========================================================================
    # Lifecycle methods with state tracking
    # ========================================================================

    def mock_configure(config):
        """Mock configure() - transitions to 'configured' state"""
        mock_instance.camera_state = 'configured'
        mock_instance.config_history.append(config)

    def mock_start():
        """Mock start() - transitions to 'started' state"""
        if mock_instance.camera_state != 'configured':
            raise RuntimeError("Camera must be configured before starting")
        mock_instance.camera_state = 'started'

    def mock_stop():
        """Mock stop() - transitions back to 'configured' state"""
        if mock_instance.camera_state != 'started':
            raise RuntimeError("Camera not started")
        mock_instance.camera_state = 'configured'

    def mock_close():
        """Mock close() - transitions to 'stopped' state"""
        mock_instance.camera_state = 'stopped'

    # Attach state-tracking methods
    mock_instance.configure.side_effect = mock_configure
    mock_instance.start.side_effect = mock_start
    mock_instance.stop.side_effect = mock_stop
    mock_instance.close.side_effect = mock_close

    # ========================================================================
    # Configuration builders
    # ========================================================================

    def mock_create_preview_configuration(**kwargs):
        """Mock create_preview_configuration() - returns mock config dict"""
        return {
            'type': 'preview',
            'main': kwargs.get('main', {}),
            'lores': kwargs.get('lores', {}),
            'raw': kwargs.get('raw', {})
        }

    def mock_create_still_configuration(**kwargs):
        """Mock create_still_configuration() - returns mock config dict"""
        return {
            'type': 'still',
            'main': kwargs.get('main', {}),
            'lores': kwargs.get('lores', {}),
            'raw': kwargs.get('raw', {})
        }

    def mock_create_video_configuration(**kwargs):
        """Mock create_video_configuration() - returns mock config dict"""
        return {
            'type': 'video',
            'main': kwargs.get('main', {}),
            'lores': kwargs.get('lores', {}),
            'raw': kwargs.get('raw', {})
        }

    mock_instance.create_preview_configuration.side_effect = mock_create_preview_configuration
    mock_instance.create_still_configuration.side_effect = mock_create_still_configuration
    mock_instance.create_video_configuration.side_effect = mock_create_video_configuration

    # ========================================================================
    # Control setting with history tracking
    # ========================================================================

    def mock_set_controls(controls):
        """Mock set_controls() - tracks control history"""
        mock_instance.controls_history.append(controls.copy())

    mock_instance.set_controls.side_effect = mock_set_controls

    # ========================================================================
    # Capture operations
    # ========================================================================

    # Default metadata for capture_metadata()
    mock_instance.capture_metadata.return_value = {
        'LensPosition': 5.0,
        'AfState': 2,  # Success
        'ExposureTime': 10000,
        'AnalogueGain': 1.0,
        'ColourTemperature': 5500,
        'Sharpness': 1.0,
        'Contrast': 1.0,
        'Brightness': 0.0,
        'Saturation': 1.0
    }

    # Default behavior for capture_file()
    def mock_capture_file(path, name='main', wait=True):
        """Mock capture_file() - creates empty file at path"""
        from pathlib import Path
        Path(path).touch()
        return path

    mock_instance.capture_file.side_effect = mock_capture_file

    # Default behavior for capture_array()
    def mock_capture_array(name='main'):
        """Mock capture_array() - returns dummy numpy array"""
        import numpy as np
        return np.zeros((1080, 1920, 3), dtype=np.uint8)

    mock_instance.capture_array.side_effect = mock_capture_array

    # ========================================================================
    # Autofocus
    # ========================================================================

    # Default autofocus_cycle() returns success
    mock_instance.autofocus_cycle.return_value = True

    # ========================================================================
    # Picamera2 class mock (returns instance)
    # ========================================================================

    def mock_picamera2_constructor(camera_num=0):
        """Mock Picamera2 constructor - can simulate 'busy' errors"""
        # Reset state for new instance
        mock_instance.camera_state = 'stopped'
        mock_instance.controls_history = []
        mock_instance.config_history = []
        return mock_instance

    mock_picamera2_module.Picamera2.side_effect = mock_picamera2_constructor

    # Also expose the mock instance for direct access in tests
    mock_picamera2_module._mock_instance = mock_instance

    yield mock_picamera2_module

    # Cleanup: remove from sys.modules if it was injected
    if 'picamera2' in sys.modules and sys.modules['picamera2'] == mock_picamera2_module:
        del sys.modules['picamera2']


@pytest.fixture
def mock_pi_version(monkeypatch, tmp_path):
    """
    Mock Pi version detection via /proc/cpuinfo

    Camera routes detect Pi 4 vs Pi 5 by reading /proc/cpuinfo and searching
    for "Pi 4" or "Pi 5" in the Model line (camera.py:244-251).

    This fixture creates a temporary cpuinfo file and patches the file path
    so tests can control which Pi version is detected.

    Usage:
        def test_capture_pi4(client, mock_pi_version):
            # Configure for Pi 4
            mock_pi_version('4')

            response = client.post('/api/camera/capture')
            # Will use Pi 4 code path (TakePhoto_HDR.py)

        def test_capture_pi5(client, mock_pi_version):
            # Configure for Pi 5
            mock_pi_version('5')

            response = client.post('/api/camera/capture')
            # Will use Pi 5 code path (TakePhoto.py with HDR support)

    Returns:
        function: Call with '4' or '5' to set Pi version

    Related: Issue #78 - Camera testing infrastructure
    """
    from pathlib import Path

    # Create temporary cpuinfo file
    cpuinfo_file = tmp_path / "cpuinfo"

    def set_pi_version(version):
        """
        Set the Pi version ('4' or '5')

        Args:
            version: str - '4' for Pi 4, '5' for Pi 5
        """
        if version == '4':
            content = """processor\t: 0
Model\t\t: Raspberry Pi 4 Model B Rev 1.5
BogoMIPS\t: 108.00
Features\t: fp asimd evtstrm crc32 cpuid
CPU implementer\t: 0x41
CPU architecture: 8
CPU variant\t: 0x0
CPU part\t: 0xd08
CPU revision\t: 3
"""
        elif version == '5':
            content = """processor\t: 0
Model\t\t: Raspberry Pi 5 Model B Rev 1.0
BogoMIPS\t: 108.00
Features\t: fp asimd evtstrm crc32 cpuid
CPU implementer\t: 0x41
CPU architecture: 8
CPU variant\t: 0x4
CPU part\t: 0xd0b
CPU revision\t: 1
"""
        else:
            raise ValueError(f"Invalid Pi version: {version}. Must be '4' or '5'")

        cpuinfo_file.write_text(content)

        # Patch the /proc/cpuinfo path
        # We need to patch the `open()` builtin when it's called with "/proc/cpuinfo"
        original_open = open

        def patched_open(file, *args, **kwargs):
            if str(file) == "/proc/cpuinfo":
                return original_open(cpuinfo_file, *args, **kwargs)
            return original_open(file, *args, **kwargs)

        monkeypatch.setattr('builtins.open', patched_open)

    # Return the setter function
    yield set_pi_version

    # Cleanup happens automatically with tmp_path and monkeypatch


@pytest.fixture
def mock_subprocess_run():
    """
    Factory fixture for mocking subprocess.run() with predefined responses

    Camera routes use subprocess.run() to execute TakePhoto.py, TakePhoto_HDR.py,
    and capture_focus_bracket.py scripts. This fixture provides a factory to
    create mocks for each script type with realistic return values.

    Usage:
        def test_capture_single(client, mock_subprocess_run, monkeypatch):
            # Create mock for TakePhoto.py success
            mock_run = mock_subprocess_run('TakePhoto.py', returncode=0)

            # Patch subprocess.run
            monkeypatch.setattr('subprocess.run', mock_run)

            response = client.post('/api/camera/capture')

            # Verify subprocess was called correctly
            assert mock_run.called
            assert 'TakePhoto.py' in mock_run.call_args[0][0]

    Factory parameters:
        script_name: str - Name of script ('TakePhoto.py', 'TakePhoto_HDR.py',
                          'capture_focus_bracket.py', 'run_calibration.py')
        returncode: int - Exit code (0 = success, non-zero = error)
        stdout: str - Optional custom stdout (defaults based on script)
        stderr: str - Optional custom stderr
        timeout: bool - If True, raises TimeoutExpired

    Related: Issue #78 - Camera testing infrastructure
    """
    from unittest.mock import MagicMock
    import subprocess

    def factory(script_name, returncode=0, stdout=None, stderr=None, timeout=False):
        """
        Create a mock subprocess.run function

        Args:
            script_name: str - Script being mocked
            returncode: int - Exit code
            stdout: str - Custom stdout (optional)
            stderr: str - Custom stderr (optional)
            timeout: bool - Whether to raise TimeoutExpired

        Returns:
            MagicMock configured to return subprocess.CompletedProcess
        """
        # Default outputs based on script type
        if stdout is None:
            if script_name == 'TakePhoto.py' or script_name == 'TakePhoto_HDR.py':
                stdout = "Photo captured successfully\nFilename: photo_001.jpg\n"
            elif script_name == 'capture_focus_bracket.py':
                stdout = "Focus bracket completed: 5 images captured\n"
            elif script_name == 'run_calibration.py':
                stdout = """Calibration started...
Autofocus completed: Success at 5.2 diopters
Running test exposures...
Optimal settings: ExposureTime=10000, AnalogueGain=1.5
Calibration complete!
"""
            else:
                stdout = f"{script_name} completed\n"

        if stderr is None:
            stderr = "" if returncode == 0 else f"Error in {script_name}\n"

        mock_run = MagicMock()

        if timeout:
            # Simulate timeout
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd=['python3', script_name],
                timeout=30
            )
        else:
            # Return CompletedProcess
            mock_run.return_value = subprocess.CompletedProcess(
                args=['python3', script_name],
                returncode=returncode,
                stdout=stdout,
                stderr=stderr
            )

        return mock_run

    yield factory


@pytest.fixture
def mock_camera_streamer(app):
    """
    Mock camera_streamer with operation lock tracking

    Camera routes coordinate with CameraStreamer via acquire_for_operation()
    context manager to prevent concurrent camera access. This fixture provides
    a mock that tracks lock acquisition/release.

    The mock is automatically registered in app.config['CAMERA_STREAMER'] so
    route code can find it via current_app.config.get('CAMERA_STREAMER').

    Usage:
        def test_capture_with_lock(client, mock_camera_streamer):
            response = client.post('/api/camera/capture')

            # Verify lock was acquired
            assert mock_camera_streamer.acquire_for_operation.called

            # Verify camera was released
            assert mock_camera_streamer.release_camera.called

    Tracked state:
        - lock_acquired: bool - Whether acquire_for_operation() was called
        - camera: MagicMock - Mock camera instance (or None)
        - streaming: bool - Whether streaming is active
        - release_count: int - Number of times release_camera() called

    Related: Issue #78 - Camera testing infrastructure
    """
    from unittest.mock import MagicMock
    from contextlib import contextmanager

    mock_streamer = MagicMock()

    # State tracking
    mock_streamer.camera = None  # No camera initially
    mock_streamer.streaming = False
    mock_streamer.lock_acquired = False
    mock_streamer.release_count = 0

    # Mock release_camera()
    def mock_release():
        mock_streamer.camera = None
        mock_streamer.streaming = False
        mock_streamer.release_count += 1

    mock_streamer.release_camera.side_effect = mock_release

    # Mock start_streaming()
    def mock_start_streaming():
        if not mock_streamer.camera:
            # Initialize mock camera
            mock_streamer.camera = MagicMock()
        mock_streamer.streaming = True
        return True

    mock_streamer.start_streaming.side_effect = mock_start_streaming

    # Mock stop_streaming()
    def mock_stop_streaming():
        mock_streamer.streaming = False

    mock_streamer.stop_streaming.side_effect = mock_stop_streaming

    # Mock acquire_for_operation() context manager
    @contextmanager
    def mock_acquire_for_operation():
        mock_streamer.lock_acquired = True
        try:
            yield
        finally:
            mock_streamer.lock_acquired = False

    mock_streamer.acquire_for_operation.side_effect = mock_acquire_for_operation

    # Mock set_manual_focus_mode()
    mock_streamer.set_manual_focus_mode.return_value = True

    # Register in app config (routes expect this)
    app.config['CAMERA_STREAMER'] = mock_streamer

    yield mock_streamer

    # Cleanup
    app.config.pop('CAMERA_STREAMER', None)


@pytest.fixture
def temp_photos_dir(tmp_path, monkeypatch):
    """
    Temporary PHOTOS_DIR for isolated camera testing

    Creates a temporary photos directory and patches mothbox_paths.PHOTOS_DIR
    to prevent tests from modifying real photo storage.

    Usage:
        def test_capture(client, temp_photos_dir):
            response = client.post('/api/camera/capture')

            # Photos go to temp_photos_dir, not real PHOTOS_DIR
            photos = list(temp_photos_dir.glob('*.jpg'))
            assert len(photos) == 1

    Returns:
        Path: Temporary photos directory

    Related: Issue #78 - Camera testing infrastructure
    """
    # Create temporary photos directory
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()

    # Patch PHOTOS_DIR everywhere
    patch_path_constant_everywhere(monkeypatch, 'PHOTOS_DIR', photos_dir)

    yield photos_dir

    # Cleanup happens automatically with tmp_path


@pytest.fixture
def mock_socketio_emit(app, monkeypatch):
    """
    Mock SocketIO emit() with call tracking

    Camera routes emit WebSocket events for progress updates (e.g.,
    calibration_progress). This fixture provides a mock that tracks
    all emitted events.

    The mock is registered in app.extensions['socketio'] so routes
    can find it via current_app.extensions.get('socketio').

    Usage:
        def test_calibration_progress(client, mock_socketio_emit):
            response = client.post('/api/camera/calibrate-photo')

            # Verify progress events were emitted
            assert mock_socketio_emit.called
            calls = mock_socketio_emit.call_args_list

            # Check for calibration_progress event
            progress_calls = [c for c in calls if c[0][0] == 'calibration_progress']
            assert len(progress_calls) > 0

    Tracked state:
        - call_args_list: List of all emit() calls
        - emit_history: List of (event, data) tuples

    Related: Issue #78 - Camera testing infrastructure
    """
    from unittest.mock import MagicMock

    # Create mock socketio instance
    mock_socketio = MagicMock()

    # Track emission history
    emit_history = []

    def mock_emit(event, data, **kwargs):
        """Track all emissions"""
        emit_history.append((event, data))

    mock_socketio.emit.side_effect = mock_emit
    mock_socketio.emit_history = emit_history

    # Register in app extensions
    app.extensions['socketio'] = mock_socketio

    yield mock_socketio

    # Cleanup
    app.extensions.pop('socketio', None)


@pytest.fixture
def mock_preset_manager(monkeypatch):
    """
    Mock the module-level preset_manager instance in routes.presets

    Problem: routes/presets.py line 21 instantiates preset_manager at module
    import time, before test patches can be applied:
        preset_manager = PresetManager(BUILTIN_PRESET_DIR, USER_PRESET_DIR)

    Solution: Use monkeypatch.setattr() to replace the instance after import.
    This fixture provides a pre-configured MagicMock with common return values.

    Usage:
        def test_list_presets(client, mock_preset_manager):
            # Configure mock behavior
            mock_preset_manager.list_presets.return_value = [
                {'name': 'test', 'workflow': 'both'}
            ]

            # Make request (will use mocked preset_manager)
            response = client.get('/api/presets')

    Pattern: This approach works for any module-level instance that can't be
    patched before import. Similar to how we mock RPi.GPIO via sys.modules,
    but simpler since we just replace the instance attribute.

    Related: Issue #78 - Preset route testing
    """
    from unittest.mock import MagicMock

    # Create mock instance
    mock_pm = MagicMock()

    # Set default return values (can be overridden in tests)
    mock_pm.list_presets.return_value = []
    mock_pm.get_preset_count.return_value = {'built-in': 0, 'user': 0, 'total': 0}
    mock_pm.get_preset.return_value = None
    mock_pm.create_preset.return_value = True
    mock_pm.delete_preset.return_value = True
    mock_pm.apply_preset.return_value = {'success': True}

    # Import routes.presets (already imported by app fixture, but safe to re-import)
    from routes import presets

    # Replace the module-level instance with our mock
    monkeypatch.setattr(presets, 'preset_manager', mock_pm)

    yield mock_pm

    # Cleanup happens automatically via monkeypatch


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
    - focus bracket integration tests (use mocks, no hardware)
    - gallery pagination integration tests (filesystem only, no Pi hardware needed)
    - GPS EXIF workflow tests (use mocks/PIL, no camera/GPIO needed)
    - GPS EXIF verification workflow tests (use subprocess/PIL, no camera/GPIO needed)
    - GPS EXIF batch tagging workflow tests (use subprocess/PIL, no camera/GPIO needed)
    """
    for item in items:
        # Mark integration tests (except manual verification and installer) as hardware tests
        fspath_str = str(item.fspath)
        is_integration = 'integration' in fspath_str
        is_manual = 'manual_verification' in fspath_str
        is_installer = 'installer' in fspath_str  # installer_workflows or installer_helpers
        is_focus_bracket_integration = 'test_focus_bracket_integration' in fspath_str  # Uses mocks only
        is_gallery_pagination = 'test_gallery_pagination' in fspath_str  # Filesystem only, no Pi hardware
        is_gps_exif_workflow = 'test_gps_exif_workflow' in fspath_str  # Uses mocks/PIL, no camera/GPIO
        is_verification_workflow = 'test_verification_workflow' in fspath_str  # Uses subprocess/PIL, no camera/GPIO
        is_batch_tagging_workflow = 'test_batch_tagging_workflow' in fspath_str  # Uses subprocess/PIL, no camera/GPIO

        if is_integration and not is_manual and not is_installer and not is_focus_bracket_integration and not is_gallery_pagination and not is_gps_exif_workflow and not is_verification_workflow and not is_batch_tagging_workflow:
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

    Related: Issue #13 - Path constant patching fix
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

    Related: Issue #13 (hardware configuration testing)
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

    Related: Issue #13 (hardware configuration testing)
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
def mock_opencv(monkeypatch):
    """
    Mock OpenCV (cv2) for focus peaking algorithm tests.

    Provides realistic numpy-based implementations of OpenCV functions
    used in focus peaking, using scipy convolution for accurate edge detection.
    Automatically injected into sys.modules for seamless 'import cv2' usage.

    All methods return arrays with correct shapes and dtypes matching real OpenCV.

    Usage:
        def test_focus_peaking(camera_streamer_func, mock_opencv):
            # OpenCV is automatically available via 'import cv2'
            # Or use mock_opencv directly for assertions
            result = streamer._apply_focus_peaking_laplacian(frame)

    Related: Issue #78 - Focus peaking algorithm testing
    """
    import numpy as np
    from unittest.mock import MagicMock

    mock_cv2 = MagicMock()

    # cvtColor: RGB ↔ Grayscale conversion
    def mock_cvtColor(frame, code):
        """Convert between color spaces using luminosity method"""
        if code in (6,):  # COLOR_RGB2GRAY, COLOR_BGR2GRAY
            if len(frame.shape) == 3:
                # Luminosity method (more realistic than simple averaging)
                return np.dot(frame[...,:3], [0.299, 0.587, 0.114]).astype(np.uint8)
            return frame
        elif code in (8,):  # COLOR_GRAY2RGB, COLOR_GRAY2BGR
            if len(frame.shape) == 2:
                return np.stack([frame, frame, frame], axis=2)
            return frame
        return frame
    mock_cv2.cvtColor = mock_cvtColor

    # Laplacian: Edge detection using convolution
    def mock_Laplacian(src, ddepth, ksize=1):
        """Laplacian edge detection with scipy convolution"""
        from scipy.ndimage import convolve

        # Standard Laplacian kernel
        kernel = np.array([[0, 1, 0],
                          [1, -4, 1],
                          [0, 1, 0]])

        # Apply convolution
        result = convolve(src.astype(float), kernel, mode='reflect')

        # Return absolute value as uint8
        return np.abs(result).astype(np.uint8)
    mock_cv2.Laplacian = mock_Laplacian

    # Sobel: Directional edge detection with convolution
    def mock_Sobel(src, ddepth, dx, dy, ksize=3):
        """Sobel edge detection with proper gradient kernels"""
        from scipy.ndimage import convolve

        if dx == 1 and dy == 0:
            # Horizontal gradient (Sobel X)
            kernel = np.array([[-1, 0, 1],
                              [-2, 0, 2],
                              [-1, 0, 1]])
        elif dx == 0 and dy == 1:
            # Vertical gradient (Sobel Y)
            kernel = np.array([[-1, -2, -1],
                              [0, 0, 0],
                              [1, 2, 1]])
        else:
            return np.zeros_like(src, dtype=np.int16)

        result = convolve(src.astype(float), kernel, mode='reflect')
        return result.astype(np.int16)  # Sobel returns signed int16
    mock_cv2.Sobel = mock_Sobel

    # Canny: Two-threshold edge detection
    def mock_Canny(image, threshold1, threshold2):
        """Canny edge detection using gradient magnitude"""
        from scipy.ndimage import convolve

        # Sobel kernels for gradient computation
        kernel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]])
        kernel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]])

        grad_x = convolve(image.astype(float), kernel_x, mode='reflect')
        grad_y = convolve(image.astype(float), kernel_y, mode='reflect')

        # Gradient magnitude
        magnitude = np.sqrt(grad_x**2 + grad_y**2)

        # Apply high threshold (simplified - no hysteresis)
        edges = np.zeros_like(image, dtype=np.uint8)
        edges[magnitude > threshold2] = 255

        return edges
    mock_cv2.Canny = mock_Canny

    # getStructuringElement: Morphological kernels
    def mock_getStructuringElement(shape, ksize):
        """Create morphological structuring element"""
        h, w = ksize
        if shape == 2:  # MORPH_ELLIPSE
            # Create elliptical kernel
            y, x = np.ogrid[-h//2:h//2+1, -w//2:w//2+1]
            kernel = ((x**2 / (w/2)**2) + (y**2 / (h/2)**2)) <= 1
            return kernel.astype(np.uint8)
        else:
            # Rectangular kernel
            return np.ones(ksize, dtype=np.uint8)
    mock_cv2.getStructuringElement = mock_getStructuringElement

    # morphologyEx: Morphological operations
    def mock_morphologyEx(src, op, kernel):
        """Morphological operations (closing)"""
        if op == 3:  # MORPH_CLOSE
            from scipy.ndimage import binary_dilation, binary_erosion
            dilated = binary_dilation(src > 0, structure=kernel)
            closed = binary_erosion(dilated, structure=kernel)
            return (closed * 255).astype(np.uint8)
        return src
    mock_cv2.morphologyEx = mock_morphologyEx

    # addWeighted: Blend overlay with frame
    def mock_addWeighted(src1, alpha, src2, beta, gamma):
        """Weighted blend of two images"""
        # Ensure proper type handling and clipping
        result = (src1.astype(np.float32) * alpha + src2.astype(np.float32) * beta + gamma)
        result = np.clip(result, 0, 255).astype(np.uint8)
        return result
    mock_cv2.addWeighted = mock_addWeighted

    # Constants
    mock_cv2.COLOR_RGB2GRAY = 6
    mock_cv2.COLOR_BGR2GRAY = 6  # Same as RGB in picamera2
    mock_cv2.COLOR_GRAY2RGB = 8
    mock_cv2.COLOR_GRAY2BGR = 8
    mock_cv2.CV_64F = 6
    mock_cv2.CV_8U = 0
    mock_cv2.MORPH_DILATE = 1
    mock_cv2.MORPH_RECT = 0
    mock_cv2.MORPH_ELLIPSE = 2
    mock_cv2.MORPH_CLOSE = 3

    # Inject into sys.modules for automatic availability
    import sys
    monkeypatch.setitem(sys.modules, 'cv2', mock_cv2)

    yield mock_cv2


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
        - Size varies with quality (higher quality = larger size)
        """
        h, w = frame.shape[:2]
        # Rough size estimate: quality affects compression
        # Higher quality = less compression = larger file
        base_size = h * w * 3  # RGB bytes
        compression_ratio = quality / 100.0  # 0.85 for Q85, 0.95 for Q95
        jpeg_size = int(base_size * (0.05 + compression_ratio * 0.25))  # 5-30% of original

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

    # Create mock picamera2 modules in sys.modules
    import sys

    # Mock picamera2.outputs module
    mock_outputs = type(sys)('picamera2.outputs')
    mock_outputs.FileOutput = MockFileOutput

    # Mock picamera2.encoders module
    mock_encoders = type(sys)('picamera2.encoders')
    mock_encoders.MJPEGEncoder = MockMJPEGEncoder

    # Inject into sys.modules
    monkeypatch.setitem(sys.modules, 'picamera2.outputs', mock_outputs)
    monkeypatch.setitem(sys.modules, 'picamera2.encoders', mock_encoders)

    yield {
        'FileOutput': MockFileOutput,
        'MJPEGEncoder': MockMJPEGEncoder
    }


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


@pytest.fixture(scope='function')
def mock_picamera2_for_streamer():
    """
    Comprehensive Picamera2 mock for LiveViewStreamer tests.

    Simulates camera initialization, configuration, streaming,
    and control application without requiring hardware.

    Architecture:
    - Custom class for properties and state tracking
    - MagicMock methods for test-level configuration
    - Function-scoped: Each test gets a fresh instance

    Usage - Default behavior:
        def test_with_defaults(mock_picamera2_for_streamer):
            mock_cam = mock_picamera2_for_streamer
            frame = mock_cam.capture_array()  # Returns default 768x1024 array

    Usage - Override return values:
        def test_with_override(mock_picamera2_for_streamer):
            mock_cam = mock_picamera2_for_streamer
            mock_cam.camera_configuration.return_value = {
                'raw': {'size': (4056, 3040)},
                'main': {'size': (1920, 1080)}
            }
            config = mock_cam.camera_configuration()  # Returns override

    Usage - Simulate errors:
        def test_error_handling(mock_picamera2_for_streamer):
            mock_cam = mock_picamera2_for_streamer
            mock_cam.stop.side_effect = RuntimeError("Stop failed")
            # Test error recovery...

    Usage - Verify calls:
        def test_call_verification(mock_picamera2_for_streamer):
            mock_cam = mock_picamera2_for_streamer
            mock_cam.start_recording(encoder, output)
            mock_cam.start_recording.assert_called_once()

    Related: Issue #78 - LiveView streamer testing, Issue #13 Phase 1
    """
    from unittest.mock import MagicMock
    import numpy as np

    class MockPicamera2:
        def __init__(self, camera_num=0, tuning=None):
            self.camera_num = camera_num
            self.tuning = tuning
            self.started = False
            self.streaming = False
            self.controls = {}
            self.current_controls = {}  # Track current control state
            self.control_history = []  # Track all set_controls calls
            self.config = None  # Initialized by configure()
            self.sensor_modes = [
                {'size': (1920, 1080)},
                {'size': (2304, 1736)},
                {'size': (4608, 2592)}
            ]
            self.scaler_crop_maximum = (0, 0, 4056, 3040)  # Arducam 64MP
            self._simulate_busy = False
            self._simulate_already_started = False

            # Internal storage for camera_properties (can be overridden by tests)
            self._camera_properties = None

            # Configure methods as MagicMocks with default behaviors
            self._setup_mock_methods()

        @property
        def state(self):
            """Current camera state"""
            if self.streaming:
                return 'streaming'
            elif self.started:
                return 'started'
            else:
                return 'stopped'

        @property
        def camera_controls(self):
            """Available camera controls"""
            return {
                'AfMode': (0, 2, 2),
                'AfSpeed': (0, 1, 0),
                'AfRange': (0, 2, 0),
                'AfMetering': (0, 1, 0),
                'AfWindows': [(0, 0, 0, 0)],
                'Sharpness': (0.0, 16.0, 1.0),
                'Brightness': (-1.0, 1.0, 0.0),
                'Contrast': (0.0, 32.0, 1.0),
                'Saturation': (0.0, 32.0, 1.0),
                'AwbEnable': (False, True, True),
                'AwbMode': (0, 7, 0),
                'AeEnable': (False, True, True),
                'AeMeteringMode': (0, 3, 0),
                'ExposureTime': (0, 1000000, 0),
                'AnalogueGain': (1.0, 16.0, 1.0),
                'ColourGains': (0.0, 32.0, 0.0),
                'NoiseReductionMode': (0, 4, 0)
            }

        @property
        def camera_properties(self):
            """Camera properties including ScalerCropMaximum"""
            # If test has overridden _camera_properties, use that
            if self._camera_properties is not None:
                return self._camera_properties
            # Otherwise, return dynamic properties based on scaler_crop_maximum
            return {
                'ScalerCropMaximum': self.scaler_crop_maximum,
                'Model': 'Arducam 64MP',
                'UnitCellSize': (1120, 1120),  # 1.12µm pixels
                'PixelArraySize': (9248, 6944)
            }

        @camera_properties.setter
        def camera_properties(self, value):
            """Allow tests to override camera_properties (merges with defaults)

            Args:
                value: Dict of properties to set. Merges with default properties.
                       Use None to reset to defaults.
                       Use {} to explicitly set empty dict (for testing missing properties).
            """
            if value is None:
                # Reset to defaults
                self._camera_properties = None
            elif value == {}:
                # Explicitly set to empty (for testing missing properties)
                self._camera_properties = {}
            else:
                # Merge with defaults
                defaults = {
                    'ScalerCropMaximum': self.scaler_crop_maximum,
                    'Model': 'Arducam 64MP',
                    'UnitCellSize': (1120, 1120),
                    'PixelArraySize': (9248, 6944)
                }
                self._camera_properties = {**defaults, **value}

        def _setup_mock_methods(self):
            """Configure all methods as MagicMocks with default behaviors"""

            # ----------------------------------------------------------------
            # Configuration methods
            # ----------------------------------------------------------------
            def default_create_video_configuration(main=None, raw=None, encode=None):
                if raw is None:
                    raw = {'size': (2304, 1736)}  # Default 4:3 mode
                return {'main': main, 'raw': raw, 'encode': encode}

            self.create_video_configuration = MagicMock(
                side_effect=default_create_video_configuration
            )

            def default_configure(config):
                self.config = config

            self.configure = MagicMock(side_effect=default_configure)

            # camera_configuration: Use a property-like approach
            # Note: Tests can override by setting both side_effect=None and return_value
            # or by updating self.config via configure()
            self.camera_configuration = MagicMock()
            # Wraps approach: call underlying function but allow override
            self._orig_camera_configuration = lambda: self.config

            def _camera_configuration_wrapper():
                return self.config

            # Use side_effect so it dynamically returns self.config
            self.camera_configuration.side_effect = _camera_configuration_wrapper

            # ----------------------------------------------------------------
            # Lifecycle methods
            # ----------------------------------------------------------------
            def default_start():
                if self._simulate_already_started:
                    self._simulate_already_started = False
                    raise RuntimeError("Camera already started")
                if self._simulate_busy:
                    self._simulate_busy = False
                    raise RuntimeError("Camera is busy")
                if not self.started:
                    self.started = True

            self.start = MagicMock(side_effect=default_start)

            def default_stop():
                self.started = False

            self.stop = MagicMock(side_effect=default_stop)

            def default_close():
                self.started = False
                self.streaming = False

            self.close = MagicMock(side_effect=default_close)

            # ----------------------------------------------------------------
            # Recording methods
            # ----------------------------------------------------------------
            def default_start_recording(encoder, output):
                self.streaming = True

            self.start_recording = MagicMock(
                side_effect=default_start_recording
            )

            def default_stop_recording():
                self.streaming = False

            self.stop_recording = MagicMock(
                side_effect=default_stop_recording
            )

            # ----------------------------------------------------------------
            # Capture methods
            # ----------------------------------------------------------------
            def default_capture_array():
                return np.zeros((768, 1024, 3), dtype=np.uint8)

            self.capture_array = MagicMock(
                side_effect=default_capture_array
            )

            def default_capture_metadata():
                return {
                    'AfState': 2,  # Focused
                    'ExposureTime': 500,
                    'AnalogueGain': 8.0,
                    'LensPosition': 1.5
                }

            self.capture_metadata = MagicMock(
                side_effect=default_capture_metadata
            )

            def default_capture_request():
                class MockRequest:
                    def get_metadata(self):
                        return {
                            'AfState': 2,
                            'ExposureTime': 500
                        }
                    def release(self):
                        pass
                return MockRequest()

            self.capture_request = MagicMock(
                side_effect=default_capture_request
            )

            # ----------------------------------------------------------------
            # Control methods
            # ----------------------------------------------------------------
            def default_set_controls(controls):
                if self.state == 'stopped':
                    raise RuntimeError("Camera not started")
                self.control_history.append(controls.copy())
                self.current_controls.update(controls)
                self.controls.update(controls)

            self.set_controls = MagicMock(
                side_effect=default_set_controls
            )

        def simulate_camera_busy_error(self):
            """Make next operation raise 'camera busy' error"""
            self._simulate_busy = True

        def simulate_already_started_error(self):
            """Make next start() raise 'already started' error"""
            self._simulate_already_started = True

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


@pytest.fixture(autouse=True)
def clear_gps_cache(request):
    """
    Clear GPS status cache before AND after each test to prevent cache pollution.

    The GPS status endpoint uses a 2-second cache. When tests run quickly
    (faster than the cache TTL), later tests can receive stale cached data
    from earlier tests, causing test failures.

    This fixture only clears the cache if the test module is testing GPS routes.
    """
    # Only clear cache for GPS route tests
    if 'test_gps_routes' in request.node.nodeid:
        try:
            from routes.gps import _gps_status_cache
            with _gps_status_cache['lock']:
                _gps_status_cache['data'] = None
                _gps_status_cache['timestamp'] = 0
        except (ImportError, KeyError):
            # Module not imported yet or cache structure changed - safe to ignore
            pass

    yield

    # Clear cache after test as well
    if 'test_gps_routes' in request.node.nodeid:
        try:
            from routes.gps import _gps_status_cache
            with _gps_status_cache['lock']:
                _gps_status_cache['data'] = None
                _gps_status_cache['timestamp'] = 0
        except (ImportError, KeyError):
            pass


@pytest.fixture(autouse=True)
def reset_pil_imports(request):
    """
    Reset PIL module imports after each test to prevent mock pollution (Issue #143).

    Some tests (test_gallery_routes.py) use patch.dict(sys.modules, {'PIL': ...})
    to mock PIL for testing. However, when patch.dict() exits its context, it
    doesn't fully restore PIL submodules that were already imported (like PIL.Image).

    This fixture ensures PIL is fully reset after each test, preventing mocked PIL
    from leaking into subsequent tests that need the real PIL (e.g., sample_photos fixture).

    NOTE: We do NOT reset services.* modules here because they are imported at module level
    by routes/gallery.py, and resetting them would cause exception type mismatches.

    EXCEPTION: Metadata tests (test_metadata_service.py, test_metadata_routes.py) are excluded
    from PIL reset because they use module-scoped fixtures that need real PIL for photo creation.
    These tests capture a reference to real PIL.Image at module level (_REAL_PIL_IMAGE) to avoid
    pollution from gallery test mocking.

    See: https://github.com/zane-lazare/Mothbox/pull/143
    """
    yield

    # Skip PIL reset for metadata tests (they need real PIL for module-scoped fixtures)
    if 'test_metadata' in request.node.nodeid:
        return

    # AFTER test: Force complete PIL reset
    # Remove ALL PIL modules from sys.modules to force fresh import
    pil_modules_to_remove = [key for key in sys.modules.keys() if key == 'PIL' or key.startswith('PIL.')]
    for key in pil_modules_to_remove:
        del sys.modules[key]


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


@pytest.fixture
def patch_cv2_for_focus_peaking(mock_opencv):
    """
    Context manager fixture to patch cv2 and numpy in liveview_stream module.

    Usage:
        def test_something(camera_streamer_func, patch_cv2_for_focus_peaking):
            with patch_cv2_for_focus_peaking():
                result = streamer._apply_focus_peaking_laplacian(frame)
    """
    from unittest.mock import patch
    from contextlib import contextmanager
    import numpy as np

    @contextmanager
    def patcher():
        import liveview_stream as ls_module
        with patch.object(ls_module, 'cv2', mock_opencv, create=True):
            with patch.object(ls_module, 'np', np, create=True):
                with patch.object(ls_module, 'CV2_AVAILABLE', True):
                    yield

    return patcher


# ============================================================================
# WebSocket Handler Testing Fixtures
# ============================================================================

@pytest.fixture
def mock_config_cors(monkeypatch):
    """
    Factory fixture for mocking config.CORS_ORIGINS

    Allows tests to configure CORS_ORIGINS to test origin validation logic.

    Usage:
        def test_cors(mock_config_cors):
            mock_config_cors(['http://localhost:3000'])
            # Test with configured CORS origins

    Args:
        cors_origins: str or list - CORS origins ('*' for wildcard, list for specific origins, None for production mode)

    Returns:
        function: Call with cors_origins to configure mock

    Related: Origin validation security tests
    """
    def set_cors_origins(cors_origins):
        """Set CORS_ORIGINS in config module"""
        import sys
        if 'config' in sys.modules:
            # Patch the module-level get_config function
            from unittest.mock import MagicMock
            mock_config = MagicMock()
            mock_config.CORS_ORIGINS = cors_origins

            original_get_config = sys.modules['config'].get_config

            def mock_get_config():
                return mock_config

            monkeypatch.setattr('config.get_config', mock_get_config)

            # Also patch in websocket_handlers if already loaded
            if 'websocket_handlers' in sys.modules:
                monkeypatch.setattr('websocket_handlers.get_config', mock_get_config)

        return cors_origins

    return set_cors_origins


@pytest.fixture
def mock_request_origin(monkeypatch):
    """
    Factory fixture for mocking Flask request headers (Origin, Host, is_secure)

    Allows tests to simulate requests from different origins to test CORS validation.

    Usage:
        def test_origin(mock_request_origin):
            mock_request_origin(origin='http://evil.com', host='localhost:5000', is_secure=False)
            # Test with mocked request headers

    Args:
        origin: str - Origin header value (None for no Origin header)
        host: str - Host header value
        is_secure: bool - Whether request is HTTPS

    Returns:
        function: Call with parameters to configure mock request

    Related: Origin validation security tests
    """
    def set_request_headers(origin=None, host='localhost:5000', is_secure=False, remote_addr='127.0.0.1'):
        """Set Flask request headers"""
        from unittest.mock import MagicMock
        import sys

        # Create mock request
        mock_request = MagicMock()
        mock_request.headers.get.side_effect = lambda key, default=None: {
            'Origin': origin,
            'Host': host
        }.get(key, default)
        mock_request.is_secure = is_secure
        mock_request.remote_addr = remote_addr

        # Patch flask.request
        if 'flask' in sys.modules:
            monkeypatch.setattr('flask.request', mock_request)

        return mock_request

    return set_request_headers

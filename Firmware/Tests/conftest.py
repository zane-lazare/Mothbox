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
from pathlib import Path

# Setup path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'webui' / 'backend'))


# ============================================================================
# Pytest Markers
# ============================================================================

def pytest_configure(config):
    """Register custom pytest markers"""
    config.addinivalue_line(
        "markers",
        "hardware: mark test as requiring real Raspberry Pi hardware (camera, GPIO)"
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
    from camera_stream import CameraStreamer

    # Create Flask app
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    # Register blueprints with /api prefix to match production
    app.register_blueprint(camera_bp, url_prefix='/api/camera')
    app.register_blueprint(config_bp, url_prefix='/api/config')

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


def pytest_runtest_setup(item):
    """
    Skip hardware tests if not on Raspberry Pi

    Tests marked with @pytest.mark.hardware will be skipped if:
    - Not running on Raspberry Pi hardware
    - Camera not available
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

        # Check if camera available
        try:
            from picamera2 import Picamera2
            # Quick check - don't actually initialize
            Picamera2.global_camera_info()
        except Exception as e:
            pytest.skip(f"Camera not available: {e}")

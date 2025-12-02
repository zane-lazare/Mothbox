"""
Unit tests for system routes (Issue #78 - Phase 1)

Tests system status and monitoring endpoints including:
- System status with caching
- Power monitoring
- System info
- Diagnostic endpoints

Coverage Target: 85%+ (system.py is 270 lines)
"""

import pytest
import json
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
from flask import Flask
import time

# Set test environment before importing modules that use config
os.environ.setdefault('MOTHBOX_ENV', 'development')

# Import the blueprint and cache functions
from routes.system import system_bp, _get_cached_photo_count, invalidate_photo_count_cache


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def system_app():
    """Flask app with system blueprint for testing"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(system_bp, url_prefix='/api/system')
    return app


@pytest.fixture
def system_client(system_app):
    """Test client for system routes"""
    return system_app.test_client()


@pytest.fixture
def mock_paths():
    """Mock mothbox_paths functions and constants"""
    with patch('routes.system.PHOTOS_DIR', Path('/tmp/photos')), \
         patch('routes.system.MOTHBOX_HOME', Path('/opt/mothbox')), \
         patch('routes.system.CONFIG_DIR', Path('/opt/mothbox/config')), \
         patch('routes.system.FIRMWARE_DIR', Path('/opt/mothbox/firmware')), \
         patch('routes.system.CONTROLS_FILE', Path('/opt/mothbox/config/controls.txt')), \
         patch('routes.system.CAMERA_SETTINGS_FILE', Path('/opt/mothbox/config/camera_settings.csv')), \
         patch('routes.system.SCHEDULE_SETTINGS_FILE', Path('/opt/mothbox/config/schedule_settings.csv')):
        yield


# ============================================================================
# Test System Status Endpoint
# ============================================================================

class TestSystemStatus:
    """Tests for GET /api/system/status"""

    def test_status_returns_cpu_temp(self, system_client, mock_paths):
        """GET /status returns CPU temperature from sysfs"""
        temp_file_mock = mock_open(read_data='55000\n')

        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', return_value='55000'), \
             patch('routes.system.shutil.disk_usage') as mock_disk, \
             patch('routes.system._get_cached_photo_count', return_value=42), \
             patch('routes.system.get_hardware_config', return_value={}), \
             patch('routes.system._get_cached_gps_status', return_value={
                 'enabled': False, 'latitude': None, 'longitude': None,
                 'gpstime': None, 'utc_offset': None, 'has_fix': False
             }):

            # Mock disk usage
            mock_disk.return_value = MagicMock(
                free=10 * (1024**3),  # 10 GB free
                total=100 * (1024**3),  # 100 GB total
                used=90 * (1024**3)   # 90 GB used
            )

            response = system_client.get('/api/system/status')

            assert response.status_code == 200
            data = json.loads(response.data)

            assert 'cpu_temp' in data
            assert data['cpu_temp'] == 55.0  # 55000 millidegrees -> 55.0 degrees

    def test_status_returns_disk_usage(self, system_client, mock_paths):
        """GET /status returns disk usage statistics"""
        with patch('pathlib.Path.exists', return_value=False), \
             patch('routes.system.shutil.disk_usage') as mock_disk, \
             patch('routes.system._get_cached_photo_count', return_value=0), \
             patch('routes.system.get_hardware_config', return_value={}), \
             patch('routes.system._get_cached_gps_status', return_value={
                 'enabled': False, 'latitude': None, 'longitude': None,
                 'gpstime': None, 'utc_offset': None, 'has_fix': False
             }):

            # Mock 500 GB disk with 100 GB free
            mock_disk.return_value = MagicMock(
                free=100 * (1024**3),
                total=500 * (1024**3),
                used=400 * (1024**3)
            )

            response = system_client.get('/api/system/status')

            assert response.status_code == 200
            data = json.loads(response.data)

            assert 'disk' in data
            assert data['disk']['free_gb'] == 100.0
            assert data['disk']['total_gb'] == 500.0
            assert data['disk']['used_percent'] == 80.0  # 400/500 = 80%

    def test_status_uses_cached_photo_count(self, system_client, mock_paths):
        """GET /status uses cached photo count for performance"""
        with patch('pathlib.Path.exists', return_value=False), \
             patch('routes.system.shutil.disk_usage') as mock_disk, \
             patch('routes.system._get_cached_photo_count', return_value=150) as mock_count, \
             patch('routes.system.get_hardware_config', return_value={}), \
             patch('routes.system._get_cached_gps_status', return_value={
                 'enabled': False, 'latitude': None, 'longitude': None,
                 'gpstime': None, 'utc_offset': None, 'has_fix': False
             }):

            mock_disk.return_value = MagicMock(
                free=10 * (1024**3), total=100 * (1024**3), used=90 * (1024**3)
            )

            response = system_client.get('/api/system/status')

            assert response.status_code == 200
            data = json.loads(response.data)

            assert data['photo_count'] == 150
            # Verify cache function was called
            mock_count.assert_called_once()

    def test_status_includes_gps_data(self, system_client, mock_paths):
        """GET /status includes GPS status from cached data"""
        with patch('pathlib.Path.exists', return_value=False), \
             patch('routes.system.shutil.disk_usage') as mock_disk, \
             patch('routes.system._get_cached_photo_count', return_value=0), \
             patch('routes.system.get_hardware_config', return_value={'gps_enabled': True}), \
             patch('routes.system._get_cached_gps_status', return_value={
                 'enabled': True,
                 'latitude': 37.7749,
                 'longitude': -122.4194,
                 'gpstime': '2024-01-01T12:00:00Z',
                 'utc_offset': -8,
                 'has_fix': True
             }):

            mock_disk.return_value = MagicMock(
                free=10 * (1024**3), total=100 * (1024**3), used=90 * (1024**3)
            )

            response = system_client.get('/api/system/status')

            assert response.status_code == 200
            data = json.loads(response.data)

            assert 'gps' in data
            assert data['gps']['enabled'] is True
            assert data['gps']['latitude'] == 37.7749
            assert data['gps']['longitude'] == -122.4194
            assert data['gps']['has_fix'] is True

    def test_status_includes_hardware_config(self, system_client, mock_paths):
        """GET /status includes hardware configuration"""
        with patch('pathlib.Path.exists', return_value=False), \
             patch('routes.system.shutil.disk_usage') as mock_disk, \
             patch('routes.system._get_cached_photo_count', return_value=0), \
             patch('routes.system.get_hardware_config', return_value={
                 'ina260_enabled': True,
                 'gps_enabled': True,
                 'epaper_enabled': False
             }), \
             patch('routes.system._get_cached_gps_status', return_value={
                 'enabled': False, 'latitude': None, 'longitude': None,
                 'gpstime': None, 'utc_offset': None, 'has_fix': False
             }):

            mock_disk.return_value = MagicMock(
                free=10 * (1024**3), total=100 * (1024**3), used=90 * (1024**3)
            )

            response = system_client.get('/api/system/status')

            assert response.status_code == 200
            data = json.loads(response.data)

            assert 'hardware' in data
            assert data['hardware']['ina260_enabled'] is True
            assert data['hardware']['gps_enabled'] is True
            assert data['hardware']['epaper_enabled'] is False

    def test_status_handles_error(self, system_client, mock_paths):
        """GET /status returns 500 on exception"""
        with patch('routes.system.shutil.disk_usage', side_effect=Exception("Disk error")):
            response = system_client.get('/api/system/status')

            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data


# ============================================================================
# Test Power Status Endpoint
# ============================================================================

class TestSystemPower:
    """Tests for GET /api/system/power"""

    def test_power_ina260_disabled(self, system_client, mock_paths):
        """GET /power returns disabled when INA260 is not enabled"""
        with patch('routes.system.get_hardware_config', return_value={'ina260_enabled': False}):
            response = system_client.get('/api/system/power')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['enabled'] is False

    def test_power_ina260_enabled_but_not_implemented(self, system_client, mock_paths):
        """GET /power returns TODO status when INA260 is enabled"""
        with patch('routes.system.get_hardware_config', return_value={'ina260_enabled': True}):
            response = system_client.get('/api/system/power')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['enabled'] is True
            # Implementation is TODO (issue #73)
            assert data['voltage'] is None
            assert data['current'] is None
            assert data['power'] is None

    def test_power_handles_error(self, system_client, mock_paths):
        """GET /power handles errors gracefully"""
        with patch('routes.system.get_hardware_config', side_effect=Exception("Config error")):
            response = system_client.get('/api/system/power')

            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data


# ============================================================================
# Test System Info Endpoint
# ============================================================================

class TestSystemInfo:
    """Tests for GET /api/system/info"""

    def test_info_returns_installation_type(self, system_client, mock_paths):
        """GET /info returns installation type"""
        with patch('routes.system._installation_type', 'docker'), \
             patch('routes.system.get_gpio_pins', return_value={}), \
             patch('routes.system.get_control_values', return_value={'softwareversion': 'v1.0.0'}):

            response = system_client.get('/api/system/info')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['installation_type'] == 'docker'

    def test_info_returns_gpio_pins(self, system_client, mock_paths):
        """GET /info returns GPIO pin configuration"""
        with patch('routes.system._installation_type', 'native'), \
             patch('routes.system.get_gpio_pins', return_value={
                 'relay_ch1': 17,
                 'relay_ch2': 27,
                 'relay_ch3': 22
             }), \
             patch('routes.system.get_control_values', return_value={
                 'softwareversion': 'v1.0.0',
                 'Relay_Ch1': '17',
                 'Relay_Ch2': '27',
                 'Relay_Ch3': '22'
             }):

            response = system_client.get('/api/system/info')

            assert response.status_code == 200
            data = json.loads(response.data)

            assert 'gpio_pins' in data
            assert data['gpio_pins']['relay_ch1'] == 17
            assert data['gpio_source'] == 'controls.txt'

    def test_info_returns_paths(self, system_client, mock_paths):
        """GET /info returns system path information"""
        with patch('routes.system._installation_type', 'native'), \
             patch('routes.system.get_gpio_pins', return_value={}), \
             patch('routes.system.get_control_values', return_value={'softwareversion': 'v1.0.0'}):

            response = system_client.get('/api/system/info')

            assert response.status_code == 200
            data = json.loads(response.data)

            assert 'mothbox_home' in data
            assert 'config_dir' in data
            assert 'firmware_dir' in data
            assert '/opt/mothbox' in data['mothbox_home']

    def test_info_no_traceback_in_error(self, system_client, mock_paths):
        """GET /info never includes traceback in error response (security)"""
        with patch('routes.system.get_gpio_pins', side_effect=Exception("GPIO error")):
            response = system_client.get('/api/system/info')

            assert response.status_code == 500
            data = json.loads(response.data)

            # Should have error message
            assert 'error' in data
            # Should never have traceback (information disclosure risk)
            assert 'traceback' not in data


# ============================================================================
# Test Diagnostic Endpoint
# ============================================================================

class TestSystemDiagnostic:
    """Tests for GET /api/system/diagnostic"""

    def test_diagnostic_never_includes_traceback(self, system_client, mock_paths):
        """GET /diagnostic never includes traceback (security - logged server-side only)"""
        # Test with DEBUG = False (production)
        with patch('routes.system.config.DEBUG', False), \
             patch('routes.system.get_control_values', side_effect=Exception("Test error")):

            response = system_client.get('/api/system/diagnostic')

            assert response.status_code == 500
            data = json.loads(response.data)

            assert 'error' in data
            # No traceback returned to client (security)
            assert 'traceback' not in data

        # Test with DEBUG = True (development) - still no traceback to client
        with patch('routes.system.config.DEBUG', True), \
             patch('routes.system.get_control_values', side_effect=Exception("Test error")):

            response = system_client.get('/api/system/diagnostic')

            assert response.status_code == 500
            data = json.loads(response.data)

            assert 'error' in data
            # Traceback NOT included even in debug mode (CodeQL security requirement)
            # Traceback is logged server-side instead
            assert 'traceback' not in data


# ============================================================================
# Test Photo Count Caching
# ============================================================================

class TestPhotoCountCache:
    """Tests for photo count caching functionality"""

    def test_photo_count_cache_hit(self, mock_paths):
        """Photo count cache returns cached value when fresh"""
        from routes.system import _get_cached_photo_count, _photo_count_cache

        # Set up a fresh cache entry
        with _photo_count_cache['lock']:
            _photo_count_cache['count'] = 100
            _photo_count_cache['timestamp'] = time.time()

        # Should return cached value without hitting filesystem
        count = _get_cached_photo_count()
        assert count == 100

    def test_photo_count_cache_miss_expired(self, mock_paths):
        """Photo count cache performs fresh count when expired"""
        from routes.system import _get_cached_photo_count, _photo_count_cache, PHOTO_COUNT_CACHE_TTL

        # Set up expired cache entry
        with _photo_count_cache['lock']:
            _photo_count_cache['count'] = 50
            _photo_count_cache['timestamp'] = time.time() - (PHOTO_COUNT_CACHE_TTL + 10)

        # Mock the filesystem to return 75 photos
        # Use side_effect to return photos only for first pattern (*.jpg)
        # since implementation iterates over PHOTO_PATTERNS
        def glob_side_effect(pattern):
            if '*.jpg' in pattern and 'JPG' not in pattern and 'jpeg' not in pattern:
                return ['photo.jpg'] * 75
            return []

        with patch('routes.system.PHOTOS_DIR') as mock_photos_dir:
            mock_photos_dir.exists.return_value = True
            mock_photos_dir.glob.side_effect = glob_side_effect

            count = _get_cached_photo_count()

            # Should perform fresh count and update cache
            assert count == 75
            assert _photo_count_cache['count'] == 75

    def test_photo_count_cache_miss_empty(self, mock_paths):
        """Photo count cache performs fresh count when empty"""
        from routes.system import _get_cached_photo_count, _photo_count_cache

        # Clear cache
        with _photo_count_cache['lock']:
            _photo_count_cache['count'] = None
            _photo_count_cache['timestamp'] = 0

        # Mock the filesystem
        # Use side_effect to return photos only for first pattern (*.jpg)
        # since implementation iterates over PHOTO_PATTERNS
        def glob_side_effect(pattern):
            if '*.jpg' in pattern and 'JPG' not in pattern and 'jpeg' not in pattern:
                return ['a.jpg', 'b.jpg', 'c.jpg']
            return []

        with patch('routes.system.PHOTOS_DIR') as mock_photos_dir:
            mock_photos_dir.exists.return_value = True
            mock_photos_dir.glob.side_effect = glob_side_effect

            count = _get_cached_photo_count()

            assert count == 3
            assert _photo_count_cache['count'] == 3

    def test_photo_count_handles_missing_dir(self, mock_paths):
        """Photo count returns 0 when photos directory missing"""
        from routes.system import _get_cached_photo_count, _photo_count_cache

        # Clear cache
        with _photo_count_cache['lock']:
            _photo_count_cache['count'] = None
            _photo_count_cache['timestamp'] = 0

        # Mock photos directory not existing
        with patch('routes.system.PHOTOS_DIR') as mock_photos_dir:
            mock_photos_dir.exists.return_value = False

            count = _get_cached_photo_count()

            assert count == 0
            assert _photo_count_cache['count'] == 0

    def test_photo_count_handles_error_with_cached_value(self, mock_paths):
        """Photo count returns cached value on error if available"""
        from routes.system import _get_cached_photo_count, _photo_count_cache, PHOTO_COUNT_CACHE_TTL

        # Set up expired cache with value
        with _photo_count_cache['lock']:
            _photo_count_cache['count'] = 42
            _photo_count_cache['timestamp'] = time.time() - (PHOTO_COUNT_CACHE_TTL + 10)

        # Mock filesystem error
        with patch('routes.system.PHOTOS_DIR') as mock_photos_dir:
            mock_photos_dir.exists.side_effect = PermissionError("Access denied")

            count = _get_cached_photo_count()

            # Should return stale cached value rather than failing
            assert count == 42

    def test_photo_count_handles_error_without_cached_value(self, mock_paths):
        """Photo count returns 0 on error when no cached value"""
        from routes.system import _get_cached_photo_count, _photo_count_cache

        # Clear cache completely
        with _photo_count_cache['lock']:
            _photo_count_cache['count'] = None
            _photo_count_cache['timestamp'] = 0

        # Mock filesystem error
        with patch('routes.system.PHOTOS_DIR') as mock_photos_dir:
            mock_photos_dir.exists.side_effect = OSError("Disk error")

            count = _get_cached_photo_count()

            # Should return 0 when no cached value available
            assert count == 0

    def test_invalidate_photo_count_cache(self, mock_paths):
        """invalidate_photo_count_cache forces cache refresh"""
        from routes.system import invalidate_photo_count_cache, _photo_count_cache

        # Set up fresh cache
        with _photo_count_cache['lock']:
            _photo_count_cache['count'] = 100
            _photo_count_cache['timestamp'] = time.time()

        # Invalidate
        invalidate_photo_count_cache()

        # Timestamp should be reset to force cache miss
        assert _photo_count_cache['timestamp'] == 0
        # Count should still exist (not cleared)
        assert _photo_count_cache['count'] == 100


# ============================================================================
# Test Diagnostic Endpoint - File Reading
# ============================================================================

class TestDiagnosticFileReading:
    """Tests for diagnostic endpoint file reading logic"""

    def test_diagnostic_reads_controls_file(self, system_client, mock_paths):
        """GET /diagnostic reads and reports controls.txt contents"""
        controls_content = "softwareversion:v1.2.3\nname:TestBox\nRelay_Ch1:17\n"

        with patch('routes.system.CONTROLS_FILE') as mock_controls, \
             patch('routes.system.get_control_values', return_value={
                 'softwareversion': 'v1.2.3',
                 'name': 'TestBox',
                 'Relay_Ch1': '17',
                 'Relay_Ch2': '27',
                 'Relay_Ch3': '22'
             }), \
             patch('routes.system.get_hardware_config', return_value={}), \
             patch('routes.system.get_gpio_pins', return_value={}), \
             patch('builtins.open', mock_open(read_data=controls_content)):

            mock_controls.exists.return_value = True
            mock_controls.stat.return_value.st_size = len(controls_content)

            response = system_client.get('/api/system/diagnostic')

            assert response.status_code == 200
            data = json.loads(response.data)

            assert 'controls_content' in data
            assert data['controls_content']['raw_lines'] == 3
            assert data['controls_content']['has_gpio_pins'] is True

    def test_diagnostic_handles_missing_controls_file(self, system_client, mock_paths):
        """GET /diagnostic handles missing controls.txt gracefully"""
        with patch('routes.system.CONTROLS_FILE') as mock_controls, \
             patch('routes.system.get_control_values', return_value={}), \
             patch('routes.system.get_hardware_config', return_value={}), \
             patch('routes.system.get_gpio_pins', return_value={}):

            mock_controls.exists.return_value = False
            mock_controls.stat.return_value.st_size = 0

            response = system_client.get('/api/system/diagnostic')

            assert response.status_code == 200
            data = json.loads(response.data)

            assert data['paths']['controls_file_exists'] is False
            assert data['paths']['controls_file_size'] == 0
            assert data['controls_content']['raw_lines'] == 0

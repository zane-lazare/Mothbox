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
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
from flask import Flask
import time

# Mock external dependencies before importing
sys.modules['config'] = MagicMock()

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

    def test_diagnostic_only_includes_traceback_in_debug(self, system_client, mock_paths):
        """GET /diagnostic only includes traceback in debug mode"""
        # Test with DEBUG = False (production)
        with patch('routes.system.config.DEBUG', False), \
             patch('routes.system.get_control_values', side_effect=Exception("Test error")):

            response = system_client.get('/api/system/diagnostic')

            assert response.status_code == 500
            data = json.loads(response.data)

            assert 'error' in data
            # No traceback in production (security)
            assert 'traceback' not in data

        # Test with DEBUG = True (development)
        with patch('routes.system.config.DEBUG', True), \
             patch('routes.system.get_control_values', side_effect=Exception("Test error")):

            response = system_client.get('/api/system/diagnostic')

            assert response.status_code == 500
            data = json.loads(response.data)

            assert 'error' in data
            # Traceback included in debug mode
            assert 'traceback' in data

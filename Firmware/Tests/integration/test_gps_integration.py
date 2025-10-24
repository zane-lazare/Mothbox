"""
Integration tests for GPS API endpoints
Tests the GPS WebUI integration (Issue #53)
"""
import pytest
import sys
from pathlib import Path

# Add webui backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "webui" / "backend"))

from app import app, limiter
from mothbox_paths import CONTROLS_FILE, get_control_values
import tempfile
import shutil


@pytest.fixture
def client():
    """Create test client with testing configuration"""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing

    # Disable rate limiting for tests
    limiter.enabled = False

    with app.test_client() as client:
        yield client


@pytest.fixture
def temp_controls_file():
    """Create temporary controls.txt for testing"""
    temp_dir = tempfile.mkdtemp()
    temp_controls = Path(temp_dir) / "controls.txt"

    # Create test controls file with GPS settings
    content = """# Test GPS Configuration
gps_enabled=true
gps_device=/dev/ttyAMA0
gps_baudrate=9600
gps_timeout=10
lat=n/a
lon=n/a
gpstime=0
UTCoff=0
"""
    temp_controls.write_text(content)

    # Temporarily replace CONTROLS_FILE
    original_file = CONTROLS_FILE
    import routes.gps as gps_module
    gps_module.CONTROLS_FILE = temp_controls

    yield temp_controls

    # Cleanup
    gps_module.CONTROLS_FILE = original_file
    shutil.rmtree(temp_dir)


class TestGPSStatusEndpoint:
    """Tests for GET /api/gps/status"""

    def test_get_gps_status_success(self, client):
        """Test getting GPS status returns correct structure"""
        response = client.get('/api/gps/status')

        assert response.status_code == 200
        data = response.get_json()

        # Verify response structure
        assert 'enabled' in data
        assert 'latitude' in data
        assert 'longitude' in data
        assert 'gpstime' in data
        assert 'utc_offset' in data
        assert 'has_fix' in data

        # Verify data types
        assert isinstance(data['enabled'], bool)
        assert isinstance(data['has_fix'], bool)
        assert isinstance(data['gpstime'], int)
        assert isinstance(data['utc_offset'], int)

    def test_gps_status_no_fix(self, client):
        """Test GPS status when no fix is available"""
        response = client.get('/api/gps/status')
        data = response.get_json()

        # With default n/a values, should report no fix
        if data['latitude'] == 'n/a' and data['longitude'] == 'n/a':
            assert data['has_fix'] is False


class TestGPSConfigEndpoint:
    """Tests for GET/PUT /api/gps/config"""

    def test_get_gps_config_success(self, client):
        """Test getting GPS configuration"""
        response = client.get('/api/gps/config')

        assert response.status_code == 200
        data = response.get_json()

        # Verify response structure
        assert 'enabled' in data
        assert 'device' in data
        assert 'baudrate' in data
        assert 'timeout' in data

        # Verify data types
        assert isinstance(data['enabled'], bool)
        assert isinstance(data['device'], str)
        assert isinstance(data['baudrate'], int)
        assert isinstance(data['timeout'], int)

    def test_update_gps_config_success(self, client, temp_controls_file):
        """Test updating GPS configuration"""
        new_config = {
            'gps_enabled': True,
            'gps_device': '/dev/ttyUSB0',
            'gps_baudrate': 19200,
            'gps_timeout': 30
        }

        response = client.put('/api/gps/config',
                            json=new_config,
                            content_type='application/json')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_update_gps_config_invalid_baudrate(self, client):
        """Test updating GPS config with invalid baudrate"""
        invalid_config = {
            'gps_baudrate': 12345  # Invalid baudrate
        }

        response = client.put('/api/gps/config',
                            json=invalid_config,
                            content_type='application/json')

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_update_gps_config_invalid_timeout(self, client):
        """Test updating GPS config with invalid timeout"""
        invalid_config = {
            'gps_timeout': 100  # Too high
        }

        response = client.put('/api/gps/config',
                            json=invalid_config,
                            content_type='application/json')

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_update_gps_config_invalid_device(self, client):
        """Test updating GPS config with invalid device path"""
        invalid_config = {
            'gps_device': '/etc/passwd'  # Not a /dev/ path
        }

        response = client.put('/api/gps/config',
                            json=invalid_config,
                            content_type='application/json')

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert '/dev/' in data['error']

    def test_update_gps_config_no_data(self, client):
        """Test updating GPS config with no data"""
        response = client.put('/api/gps/config',
                            json=None,
                            content_type='application/json')

        assert response.status_code == 400


class TestGPSSyncEndpoint:
    """Tests for POST /api/gps/sync"""

    def test_gps_sync_when_disabled(self, client):
        """Test GPS sync fails when GPS is disabled"""
        # First disable GPS
        client.put('/api/gps/config',
                   json={'gps_enabled': False},
                   content_type='application/json')

        # Try to sync
        response = client.post('/api/gps/sync')

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'disabled' in data['error'].lower()

    def test_gps_sync_response_structure(self, client):
        """Test GPS sync returns correct response structure"""
        # Enable GPS first
        client.put('/api/gps/config',
                   json={'gps_enabled': True},
                   content_type='application/json')

        # Note: This will likely timeout or fail without real GPS hardware
        # but we can check the response structure
        response = client.post('/api/gps/sync')

        # Could be 200 (success) or error status
        if response.status_code == 200:
            data = response.get_json()
            assert 'success' in data
            assert 'latitude' in data
            assert 'longitude' in data
        else:
            # Error response
            data = response.get_json()
            assert 'error' in data


class TestSystemStatusGPSIntegration:
    """Tests for GPS data in /api/system/status"""

    def test_system_status_includes_gps(self, client):
        """Test that system status includes GPS data"""
        response = client.get('/api/system/status')

        assert response.status_code == 200
        data = response.get_json()

        # Verify GPS section exists
        assert 'gps' in data

        # Verify GPS data structure
        assert 'enabled' in data['gps']
        assert 'latitude' in data['gps']
        assert 'longitude' in data['gps']
        assert 'last_sync' in data['gps']
        assert 'utc_offset' in data['gps']
        assert 'has_fix' in data['gps']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

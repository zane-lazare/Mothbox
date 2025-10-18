"""
Unit tests for extended metadata extraction from camera
Tests all 15+ new metadata fields being extracted from Picamera2
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add webui backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "webui" / "backend"))


class TestMetadataExtraction:
    """Test extraction of extended metadata fields from camera"""

    @pytest.fixture
    def mock_camera_streamer(self):
        """Create mock camera streamer with camera"""
        with patch('camera_stream.CameraStreamer') as mock_streamer:
            streamer = mock_streamer.return_value
            streamer.camera = Mock()
            streamer.streaming = True
            yield streamer

    @pytest.fixture
    def complete_metadata(self):
        """Complete metadata dict with all fields"""
        return {
            # Primary metadata (existing)
            'ExposureTime': 10000,
            'AnalogueGain': 2.5,
            'LensPosition': 3.14,
            'AfState': 2,  # Success
            'ColourTemperature': 5500,
            # Extended metadata (new)
            'DigitalGain': 1.25,
            'FocusFoM': 123.456,
            'SensorTimestamp': 1234567890,
            'ColourGains': (1.5, 1.8),
            'FrameDuration': 33333,
            'SensorBlackLevel': 4096,
            'SensorTemperature': 42.5,
            'ScalerCrop': (100, 100, 1920, 1080),
            'AeLocked': True,
            'AwbLocked': False,
            'Lux': 150,
            'Saturation': 1.2,
            'Contrast': 1.1,
            'Sharpness': 1.5,
            'Brightness': 0.1,
        }

    def test_extract_all_primary_metadata_fields(self, mock_camera_streamer, complete_metadata):
        """Test extraction of primary metadata fields"""
        # Setup mock camera to return metadata
        mock_request = Mock()
        mock_request.get_metadata.return_value = complete_metadata
        mock_camera_streamer.camera.capture_request.return_value = mock_request

        # Import app and create test client
        from app import app, socketio
        app.config['CAMERA_STREAMER'] = mock_camera_streamer
        client = socketio.test_client(app)

        # Request metadata
        client.emit('get_metadata')
        received = client.get_received()

        # Verify primary fields extracted correctly
        assert len(received) > 0
        metadata_event = next((r for r in received if r['name'] == 'metadata_update'), None)
        assert metadata_event is not None

        data = metadata_event['args'][0]
        assert data['exposure_time'] == 10000
        assert data['analogue_gain'] == 2.5
        assert data['lens_position'] == 3.14
        assert data['af_state'] == 'Success'
        assert data['colour_temperature'] == 5500

        # Cleanup
        mock_request.release.assert_called_once()
        client.disconnect()

    def test_extract_digital_gain(self, mock_camera_streamer, complete_metadata):
        """Test extraction of DigitalGain field"""
        mock_request = Mock()
        mock_request.get_metadata.return_value = complete_metadata
        mock_camera_streamer.camera.capture_request.return_value = mock_request

        from app import app, socketio
        app.config['CAMERA_STREAMER'] = mock_camera_streamer
        client = socketio.test_client(app)

        client.emit('get_metadata')
        received = client.get_received()

        metadata_event = next((r for r in received if r['name'] == 'metadata_update'), None)
        data = metadata_event['args'][0]

        assert 'digital_gain' in data
        assert data['digital_gain'] == 1.25

        mock_request.release.assert_called_once()
        client.disconnect()

    def test_extract_focus_fom(self, mock_camera_streamer, complete_metadata):
        """Test extraction of FocusFoM (Focus Figure of Merit) field"""
        mock_request = Mock()
        mock_request.get_metadata.return_value = complete_metadata
        mock_camera_streamer.camera.capture_request.return_value = mock_request

        from app import app, socketio
        app.config['CAMERA_STREAMER'] = mock_camera_streamer
        client = socketio.test_client(app)

        client.emit('get_metadata')
        received = client.get_received()

        metadata_event = next((r for r in received if r['name'] == 'metadata_update'), None)
        data = metadata_event['args'][0]

        assert 'focus_fom' in data
        # Should be rounded to 3 decimal places
        assert data['focus_fom'] == 123.456

        mock_request.release.assert_called_once()
        client.disconnect()

    def test_extract_sensor_timestamp(self, mock_camera_streamer, complete_metadata):
        """Test extraction of SensorTimestamp field"""
        mock_request = Mock()
        mock_request.get_metadata.return_value = complete_metadata
        mock_camera_streamer.camera.capture_request.return_value = mock_request

        from app import app, socketio
        app.config['CAMERA_STREAMER'] = mock_camera_streamer
        client = socketio.test_client(app)

        client.emit('get_metadata')
        received = client.get_received()

        metadata_event = next((r for r in received if r['name'] == 'metadata_update'), None)
        data = metadata_event['args'][0]

        assert 'sensor_timestamp' in data
        assert data['sensor_timestamp'] == 1234567890

        mock_request.release.assert_called_once()
        client.disconnect()

    def test_extract_colour_gains(self, mock_camera_streamer, complete_metadata):
        """Test extraction of ColourGains (red/blue gains) field"""
        mock_request = Mock()
        mock_request.get_metadata.return_value = complete_metadata
        mock_camera_streamer.camera.capture_request.return_value = mock_request

        from app import app, socketio
        app.config['CAMERA_STREAMER'] = mock_camera_streamer
        client = socketio.test_client(app)

        client.emit('get_metadata')
        received = client.get_received()

        metadata_event = next((r for r in received if r['name'] == 'metadata_update'), None)
        data = metadata_event['args'][0]

        assert 'colour_gains' in data
        # Should be tuple with 2 elements, rounded to 2 decimals
        assert len(data['colour_gains']) == 2
        assert data['colour_gains'][0] == 1.5
        assert data['colour_gains'][1] == 1.8

        mock_request.release.assert_called_once()
        client.disconnect()

    def test_extract_frame_duration(self, mock_camera_streamer, complete_metadata):
        """Test extraction of FrameDuration field"""
        mock_request = Mock()
        mock_request.get_metadata.return_value = complete_metadata
        mock_camera_streamer.camera.capture_request.return_value = mock_request

        from app import app, socketio
        app.config['CAMERA_STREAMER'] = mock_camera_streamer
        client = socketio.test_client(app)

        client.emit('get_metadata')
        received = client.get_received()

        metadata_event = next((r for r in received if r['name'] == 'metadata_update'), None)
        data = metadata_event['args'][0]

        assert 'frame_duration' in data
        assert data['frame_duration'] == 33333

        mock_request.release.assert_called_once()
        client.disconnect()

    def test_extract_sensor_black_level(self, mock_camera_streamer, complete_metadata):
        """Test extraction of SensorBlackLevel field"""
        mock_request = Mock()
        mock_request.get_metadata.return_value = complete_metadata
        mock_camera_streamer.camera.capture_request.return_value = mock_request

        from app import app, socketio
        app.config['CAMERA_STREAMER'] = mock_camera_streamer
        client = socketio.test_client(app)

        client.emit('get_metadata')
        received = client.get_received()

        metadata_event = next((r for r in received if r['name'] == 'metadata_update'), None)
        data = metadata_event['args'][0]

        assert 'sensor_black_level' in data
        assert data['sensor_black_level'] == 4096

        mock_request.release.assert_called_once()
        client.disconnect()

    def test_extract_sensor_temperature(self, mock_camera_streamer, complete_metadata):
        """Test extraction of SensorTemperature field (optional)"""
        mock_request = Mock()
        mock_request.get_metadata.return_value = complete_metadata
        mock_camera_streamer.camera.capture_request.return_value = mock_request

        from app import app, socketio
        app.config['CAMERA_STREAMER'] = mock_camera_streamer
        client = socketio.test_client(app)

        client.emit('get_metadata')
        received = client.get_received()

        metadata_event = next((r for r in received if r['name'] == 'metadata_update'), None)
        data = metadata_event['args'][0]

        assert 'sensor_temperature' in data
        # Should be rounded to 1 decimal
        assert data['sensor_temperature'] == 42.5

        mock_request.release.assert_called_once()
        client.disconnect()

    def test_extract_scaler_crop(self, mock_camera_streamer, complete_metadata):
        """Test extraction of ScalerCrop (digital zoom crop) field"""
        mock_request = Mock()
        mock_request.get_metadata.return_value = complete_metadata
        mock_camera_streamer.camera.capture_request.return_value = mock_request

        from app import app, socketio
        app.config['CAMERA_STREAMER'] = mock_camera_streamer
        client = socketio.test_client(app)

        client.emit('get_metadata')
        received = client.get_received()

        metadata_event = next((r for r in received if r['name'] == 'metadata_update'), None)
        data = metadata_event['args'][0]

        assert 'scaler_crop' in data
        assert data['scaler_crop'] == (100, 100, 1920, 1080)

        mock_request.release.assert_called_once()
        client.disconnect()

    def test_extract_ae_locked(self, mock_camera_streamer, complete_metadata):
        """Test extraction of AeLocked (auto-exposure lock) field"""
        mock_request = Mock()
        mock_request.get_metadata.return_value = complete_metadata
        mock_camera_streamer.camera.capture_request.return_value = mock_request

        from app import app, socketio
        app.config['CAMERA_STREAMER'] = mock_camera_streamer
        client = socketio.test_client(app)

        client.emit('get_metadata')
        received = client.get_received()

        metadata_event = next((r for r in received if r['name'] == 'metadata_update'), None)
        data = metadata_event['args'][0]

        assert 'ae_locked' in data
        assert data['ae_locked'] is True

        mock_request.release.assert_called_once()
        client.disconnect()

    def test_extract_awb_locked(self, mock_camera_streamer, complete_metadata):
        """Test extraction of AwbLocked (auto white balance lock) field"""
        mock_request = Mock()
        mock_request.get_metadata.return_value = complete_metadata
        mock_camera_streamer.camera.capture_request.return_value = mock_request

        from app import app, socketio
        app.config['CAMERA_STREAMER'] = mock_camera_streamer
        client = socketio.test_client(app)

        client.emit('get_metadata')
        received = client.get_received()

        metadata_event = next((r for r in received if r['name'] == 'metadata_update'), None)
        data = metadata_event['args'][0]

        assert 'awb_locked' in data
        assert data['awb_locked'] is False

        mock_request.release.assert_called_once()
        client.disconnect()

    def test_extract_lux(self, mock_camera_streamer, complete_metadata):
        """Test extraction of Lux (brightness) field"""
        mock_request = Mock()
        mock_request.get_metadata.return_value = complete_metadata
        mock_camera_streamer.camera.capture_request.return_value = mock_request

        from app import app, socketio
        app.config['CAMERA_STREAMER'] = mock_camera_streamer
        client = socketio.test_client(app)

        client.emit('get_metadata')
        received = client.get_received()

        metadata_event = next((r for r in received if r['name'] == 'metadata_update'), None)
        data = metadata_event['args'][0]

        assert 'lux' in data
        assert data['lux'] == 150

        mock_request.release.assert_called_once()
        client.disconnect()

    def test_extract_saturation(self, mock_camera_streamer, complete_metadata):
        """Test extraction of Saturation field"""
        mock_request = Mock()
        mock_request.get_metadata.return_value = complete_metadata
        mock_camera_streamer.camera.capture_request.return_value = mock_request

        from app import app, socketio
        app.config['CAMERA_STREAMER'] = mock_camera_streamer
        client = socketio.test_client(app)

        client.emit('get_metadata')
        received = client.get_received()

        metadata_event = next((r for r in received if r['name'] == 'metadata_update'), None)
        data = metadata_event['args'][0]

        assert 'saturation' in data
        assert data['saturation'] == 1.2

        mock_request.release.assert_called_once()
        client.disconnect()

    def test_extract_contrast(self, mock_camera_streamer, complete_metadata):
        """Test extraction of Contrast field"""
        mock_request = Mock()
        mock_request.get_metadata.return_value = complete_metadata
        mock_camera_streamer.camera.capture_request.return_value = mock_request

        from app import app, socketio
        app.config['CAMERA_STREAMER'] = mock_camera_streamer
        client = socketio.test_client(app)

        client.emit('get_metadata')
        received = client.get_received()

        metadata_event = next((r for r in received if r['name'] == 'metadata_update'), None)
        data = metadata_event['args'][0]

        assert 'contrast' in data
        assert data['contrast'] == 1.1

        mock_request.release.assert_called_once()
        client.disconnect()

    def test_extract_sharpness(self, mock_camera_streamer, complete_metadata):
        """Test extraction of Sharpness field"""
        mock_request = Mock()
        mock_request.get_metadata.return_value = complete_metadata
        mock_camera_streamer.camera.capture_request.return_value = mock_request

        from app import app, socketio
        app.config['CAMERA_STREAMER'] = mock_camera_streamer
        client = socketio.test_client(app)

        client.emit('get_metadata')
        received = client.get_received()

        metadata_event = next((r for r in received if r['name'] == 'metadata_update'), None)
        data = metadata_event['args'][0]

        assert 'sharpness' in data
        assert data['sharpness'] == 1.5

        mock_request.release.assert_called_once()
        client.disconnect()

    def test_extract_brightness(self, mock_camera_streamer, complete_metadata):
        """Test extraction of Brightness field"""
        mock_request = Mock()
        mock_request.get_metadata.return_value = complete_metadata
        mock_camera_streamer.camera.capture_request.return_value = mock_request

        from app import app, socketio
        app.config['CAMERA_STREAMER'] = mock_camera_streamer
        client = socketio.test_client(app)

        client.emit('get_metadata')
        received = client.get_received()

        metadata_event = next((r for r in received if r['name'] == 'metadata_update'), None)
        data = metadata_event['args'][0]

        assert 'brightness' in data
        assert data['brightness'] == 0.1

        mock_request.release.assert_called_once()
        client.disconnect()

    def test_missing_optional_fields_use_defaults(self, mock_camera_streamer):
        """Test that missing optional fields use sensible defaults"""
        # Metadata with only required fields
        minimal_metadata = {
            'ExposureTime': 10000,
            'AnalogueGain': 2.5,
            'LensPosition': 3.14,
            'AfState': 2,
            'ColourTemperature': 5500,
        }

        mock_request = Mock()
        mock_request.get_metadata.return_value = minimal_metadata
        mock_camera_streamer.camera.capture_request.return_value = mock_request

        from app import app, socketio
        app.config['CAMERA_STREAMER'] = mock_camera_streamer
        client = socketio.test_client(app)

        client.emit('get_metadata')
        received = client.get_received()

        metadata_event = next((r for r in received if r['name'] == 'metadata_update'), None)
        data = metadata_event['args'][0]

        # Verify defaults for missing fields
        assert data['digital_gain'] == 0.0
        assert data['focus_fom'] == 0
        assert data['sensor_timestamp'] == 0
        assert data['colour_gains'] == (0.0, 0.0)
        assert data['frame_duration'] == 0
        assert data['sensor_black_level'] == 0
        assert data['sensor_temperature'] is None
        assert data['scaler_crop'] == (0, 0, 0, 0)
        assert data['ae_locked'] is False
        assert data['awb_locked'] is False
        assert data['lux'] == 0
        assert data['saturation'] == 0.0
        assert data['contrast'] == 0.0
        assert data['sharpness'] == 0.0
        assert data['brightness'] == 0.0

        mock_request.release.assert_called_once()
        client.disconnect()

    def test_camera_not_streaming_returns_unavailable(self, mock_camera_streamer):
        """Test that metadata request returns 'unavailable' when camera not streaming"""
        mock_camera_streamer.streaming = False

        from app import app, socketio
        app.config['CAMERA_STREAMER'] = mock_camera_streamer
        client = socketio.test_client(app)

        client.emit('get_metadata')
        received = client.get_received()

        metadata_event = next((r for r in received if r['name'] == 'metadata_update'), None)
        data = metadata_event['args'][0]

        assert 'error' in data
        assert data['error'] == 'Camera not streaming'
        assert data['af_state'] == 'Unavailable'

        # All extended fields should be zero/false/none
        assert data['digital_gain'] == 0
        assert data['focus_fom'] == 0
        assert data['ae_locked'] is False
        assert data['awb_locked'] is False

        client.disconnect()

    def test_all_15_extended_fields_present(self, mock_camera_streamer, complete_metadata):
        """Integration test: verify all 15+ extended metadata fields are present"""
        mock_request = Mock()
        mock_request.get_metadata.return_value = complete_metadata
        mock_camera_streamer.camera.capture_request.return_value = mock_request

        from app import app, socketio
        app.config['CAMERA_STREAMER'] = mock_camera_streamer
        client = socketio.test_client(app)

        client.emit('get_metadata')
        received = client.get_received()

        metadata_event = next((r for r in received if r['name'] == 'metadata_update'), None)
        data = metadata_event['args'][0]

        # List of all expected extended metadata fields
        extended_fields = [
            'digital_gain',
            'focus_fom',
            'sensor_timestamp',
            'colour_gains',
            'frame_duration',
            'sensor_black_level',
            'sensor_temperature',
            'scaler_crop',
            'ae_locked',
            'awb_locked',
            'lux',
            'saturation',
            'contrast',
            'sharpness',
            'brightness',
        ]

        # Verify all fields present
        for field in extended_fields:
            assert field in data, f"Missing extended metadata field: {field}"

        # Count total: 5 primary + 15 extended = 20 metadata fields (plus timestamp and no error)
        assert len([k for k in data.keys() if k not in ['error', 'timestamp']]) >= 20

        mock_request.release.assert_called_once()
        client.disconnect()

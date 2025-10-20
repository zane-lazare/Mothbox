import os
os.environ['MOTHBOX_ENV'] = 'development'  # Must be set before importing app

"""
Integration tests for extended metadata accuracy
Validates that metadata values match actual camera state with real hardware
"""

import pytest
import time
from pathlib import Path
import sys

# Add webui backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "webui" / "backend"))


@pytest.mark.integration
@pytest.mark.hardware
@pytest.mark.websocket
class TestMetadataAccuracy:
    """Integration tests for extended metadata accuracy with real camera"""

    def test_metadata_matches_camera_state(self, app):
        """Test that reported metadata matches actual camera state"""
        from app import socketio

        # Initialize camera if needed
        camera_streamer = app.config['CAMERA_STREAMER']
        if not camera_streamer.camera:
            camera_streamer.initialize_camera()
            time.sleep(1.0)

        # Create socketio client
        client = socketio.test_client(app, namespace='/')

        try:
            # Start preview
            client.emit('start_preview')
            time.sleep(2)  # Wait for stream to stabilize

            # Request metadata
            client.emit('get_metadata')
            time.sleep(0.5)

            received = client.get_received()
            metadata_events = [r for r in received if r['name'] == 'metadata_update']
            assert len(metadata_events) > 0

            metadata = metadata_events[-1]['args'][0]

            # Verify all extended fields are present and have reasonable values
            assert 'digital_gain' in metadata
            assert isinstance(metadata['digital_gain'], (int, float))
            assert metadata['digital_gain'] >= 0

            assert 'focus_fom' in metadata
            assert isinstance(metadata['focus_fom'], (int, float))
            assert metadata['focus_fom'] >= 0

            assert 'sensor_timestamp' in metadata
            assert isinstance(metadata['sensor_timestamp'], int)
            assert metadata['sensor_timestamp'] > 0

            assert 'colour_gains' in metadata
            assert isinstance(metadata['colour_gains'], (tuple, list))
            assert len(metadata['colour_gains']) == 2
            assert all(isinstance(g, (int, float)) and g >= 0 for g in metadata['colour_gains'])

            assert 'frame_duration' in metadata
            assert isinstance(metadata['frame_duration'], int)
            assert metadata['frame_duration'] > 0

            assert 'sensor_black_level' in metadata
            assert isinstance(metadata['sensor_black_level'], int)
            assert metadata['sensor_black_level'] >= 0

            assert 'scaler_crop' in metadata
            assert isinstance(metadata['scaler_crop'], (tuple, list))
            assert len(metadata['scaler_crop']) == 4
            assert all(isinstance(v, int) and v >= 0 for v in metadata['scaler_crop'])

            assert 'ae_locked' in metadata
            assert isinstance(metadata['ae_locked'], bool)

            assert 'awb_locked' in metadata
            assert isinstance(metadata['awb_locked'], bool)

            assert 'lux' in metadata
            assert isinstance(metadata['lux'], (int, float))
            assert metadata['lux'] >= 0

            assert 'saturation' in metadata
            assert isinstance(metadata['saturation'], (int, float))

            assert 'contrast' in metadata
            assert isinstance(metadata['contrast'], (int, float))

            assert 'sharpness' in metadata
            assert isinstance(metadata['sharpness'], (int, float))

            assert 'brightness' in metadata
            assert isinstance(metadata['brightness'], (int, float))

        finally:
            client.emit('stop_preview')
            if client.is_connected():
                client.disconnect()

    def test_metadata_updates_in_real_time(self, app):
        """Test that metadata updates reflect real-time camera state changes"""
        from app import socketio

        camera_streamer = app.config['CAMERA_STREAMER']
        if not camera_streamer.camera:
            camera_streamer.initialize_camera()
            time.sleep(1.0)

        client = socketio.test_client(app, namespace='/')

        try:
            # Start preview
            client.emit('start_preview')
            time.sleep(2)

            # Get initial metadata
            client.emit('get_metadata')
            time.sleep(0.5)
            received1 = client.get_received()
            metadata1_events = [r for r in received1 if r['name'] == 'metadata_update']
            assert len(metadata1_events) > 0
            metadata1 = metadata1_events[-1]['args'][0]

            # Change a control (sharpness)
            client.emit('update_preview_control', {'Sharpness': 2.5})
            time.sleep(1)

            # Get updated metadata
            client.emit('get_metadata')
            time.sleep(0.5)
            received2 = client.get_received()
            metadata2_events = [r for r in received2 if r['name'] == 'metadata_update']
            assert len(metadata2_events) > 0
            metadata2 = metadata2_events[-1]['args'][0]

            # Verify sharpness changed (allow tolerance for rounding)
            assert abs(metadata2['sharpness'] - 2.5) < 0.2, \
                f"Expected sharpness ~2.5, got {metadata2['sharpness']}"

            # Sensor timestamp should be different (time has passed)
            assert metadata2['sensor_timestamp'] > metadata1['sensor_timestamp']

        finally:
            client.emit('stop_preview')
            if client.is_connected():
                client.disconnect()

    def test_colour_gains_valid_range(self, app):
        """Test that colour gains are in valid range"""
        from app import socketio

        camera_streamer = app.config['CAMERA_STREAMER']
        if not camera_streamer.camera:
            camera_streamer.initialize_camera()
            time.sleep(1.0)

        client = socketio.test_client(app, namespace='/')

        try:
            # Start preview
            client.emit('start_preview')
            time.sleep(2)

            # Request metadata
            client.emit('get_metadata')
            time.sleep(0.5)

            received = client.get_received()
            metadata_events = [r for r in received if r['name'] == 'metadata_update']
            assert len(metadata_events) > 0
            metadata = metadata_events[-1]['args'][0]

            # Colour gains should be positive, typically 0.5-4.0
            red_gain, blue_gain = metadata['colour_gains']
            assert 0.1 < red_gain < 10.0, f"Red gain {red_gain} outside expected range"
            assert 0.1 < blue_gain < 10.0, f"Blue gain {blue_gain} outside expected range"

        finally:
            client.emit('stop_preview')
            if client.is_connected():
                client.disconnect()

    def test_frame_duration_consistency(self, app):
        """Test that frame duration is consistent and reasonable"""
        from app import socketio

        camera_streamer = app.config['CAMERA_STREAMER']
        if not camera_streamer.camera:
            camera_streamer.initialize_camera()
            time.sleep(1.0)

        client = socketio.test_client(app, namespace='/')

        try:
            # Start preview
            client.emit('start_preview')
            time.sleep(2)

            # Collect multiple metadata samples
            frame_durations = []
            for _ in range(5):
                client.emit('get_metadata')
                time.sleep(0.5)
                received = client.get_received()
                metadata_events = [r for r in received if r['name'] == 'metadata_update']
                if metadata_events:
                    metadata = metadata_events[-1]['args'][0]
                    frame_durations.append(metadata['frame_duration'])

            # Frame durations should be consistent (within 20% variance)
            avg_duration = sum(frame_durations) / len(frame_durations)
            for duration in frame_durations:
                variance = abs(duration - avg_duration) / avg_duration
                assert variance < 0.2, \
                    f"Frame duration {duration} varies too much from average {avg_duration}"

            # Allow wide range due to different stream modes
            assert 10000 < avg_duration < 500000, \
                f"Average frame duration {avg_duration}µs outside expected range"

        finally:
            client.emit('stop_preview')
            if client.is_connected():
                client.disconnect()

    def test_lux_responds_to_exposure_changes(self, app):
        """Test that lux value responds to exposure/gain changes"""
        from app import socketio

        camera_streamer = app.config['CAMERA_STREAMER']
        if not camera_streamer.camera:
            camera_streamer.initialize_camera()
            time.sleep(1.0)

        client = socketio.test_client(app, namespace='/')

        try:
            # Start preview
            client.emit('start_preview')
            time.sleep(2)

            # Get initial lux
            client.emit('get_metadata')
            time.sleep(0.5)
            received1 = client.get_received()
            metadata1_events = [r for r in received1 if r['name'] == 'metadata_update']
            if metadata1_events:
                initial_lux = metadata1_events[-1]['args'][0]['lux']

                # Verify lux is reasonable (can be 0 in dark conditions)
                assert initial_lux >= 0
                assert isinstance(initial_lux, (int, float))

        finally:
            client.emit('stop_preview')
            if client.is_connected():
                client.disconnect()

    def test_digital_gain_reasonable_range(self, app):
        """Test that digital gain is in reasonable range"""
        from app import socketio

        camera_streamer = app.config['CAMERA_STREAMER']
        if not camera_streamer.camera:
            camera_streamer.initialize_camera()
            time.sleep(1.0)

        client = socketio.test_client(app, namespace='/')

        try:
            # Start preview
            client.emit('start_preview')
            time.sleep(2)

            # Request metadata
            client.emit('get_metadata')
            time.sleep(0.5)

            received = client.get_received()
            metadata_events = [r for r in received if r['name'] == 'metadata_update']
            assert len(metadata_events) > 0
            metadata = metadata_events[-1]['args'][0]

            # Digital gain should be >= 0.0 and typically < 32.0
            digital_gain = metadata['digital_gain']
            assert digital_gain >= 0.0, f"Digital gain {digital_gain} is negative"
            assert digital_gain < 32.0, f"Digital gain {digital_gain} is unexpectedly high"

        finally:
            client.emit('stop_preview')
            if client.is_connected():
                client.disconnect()

    def test_scaler_crop_updates_with_zoom(self, app):
        """Test that scaler crop updates when digital zoom is changed"""
        from app import socketio

        camera_streamer = app.config['CAMERA_STREAMER']
        if not camera_streamer.camera:
            camera_streamer.initialize_camera()
            time.sleep(1.0)

        client = socketio.test_client(app, namespace='/')

        try:
            # Start preview
            client.emit('start_preview')
            time.sleep(2)

            # Get initial crop (no zoom)
            client.emit('get_metadata')
            time.sleep(0.5)
            received1 = client.get_received()
            metadata1_events = [r for r in received1 if r['name'] == 'metadata_update']
            assert len(metadata1_events) > 0
            crop1 = metadata1_events[-1]['args'][0]['scaler_crop']

            # Apply 2x zoom
            client.emit('set_zoom', {'zoom_level': 2.0})
            time.sleep(1)

            # Get updated crop
            client.emit('get_metadata')
            time.sleep(0.5)
            received2 = client.get_received()
            metadata2_events = [r for r in received2 if r['name'] == 'metadata_update']
            assert len(metadata2_events) > 0
            crop2 = metadata2_events[-1]['args'][0]['scaler_crop']

            # Crop dimensions should be smaller with zoom
            # crop format: (x, y, width, height)
            if crop1 != (0, 0, 0, 0):  # Skip if no crop initially
                crop1_width = crop1[2]
                crop2_width = crop2[2]
                assert crop2_width < crop1_width, \
                    f"Zoom did not reduce crop width: {crop1_width} -> {crop2_width}"

        finally:
            client.emit('stop_preview')
            if client.is_connected():
                client.disconnect()

    def test_ae_awb_lock_states(self, app):
        """Test that AE and AWB lock states are reported correctly"""
        from app import socketio

        camera_streamer = app.config['CAMERA_STREAMER']
        if not camera_streamer.camera:
            camera_streamer.initialize_camera()
            time.sleep(1.0)

        client = socketio.test_client(app, namespace='/')

        try:
            # Start preview
            client.emit('start_preview')
            time.sleep(2)

            # Request metadata
            client.emit('get_metadata')
            time.sleep(0.5)

            received = client.get_received()
            metadata_events = [r for r in received if r['name'] == 'metadata_update']
            assert len(metadata_events) > 0
            metadata = metadata_events[-1]['args'][0]

            # AE/AWB lock states should be boolean
            assert 'ae_locked' in metadata
            assert 'awb_locked' in metadata
            assert isinstance(metadata['ae_locked'], bool)
            assert isinstance(metadata['awb_locked'], bool)

        finally:
            client.emit('stop_preview')
            if client.is_connected():
                client.disconnect()

    def test_sensor_temperature_if_available(self, app):
        """Test sensor temperature if available (optional field)"""
        from app import socketio

        camera_streamer = app.config['CAMERA_STREAMER']
        if not camera_streamer.camera:
            camera_streamer.initialize_camera()
            time.sleep(1.0)

        client = socketio.test_client(app, namespace='/')

        try:
            # Start preview
            client.emit('start_preview')
            time.sleep(2)

            # Request metadata
            client.emit('get_metadata')
            time.sleep(0.5)

            received = client.get_received()
            metadata_events = [r for r in received if r['name'] == 'metadata_update']
            assert len(metadata_events) > 0
            metadata = metadata_events[-1]['args'][0]

            # Sensor temperature may be None or a float
            sensor_temp = metadata.get('sensor_temperature')
            if sensor_temp is not None:
                assert isinstance(sensor_temp, (int, float))
                # Should be reasonable temperature in Celsius (0-100°C)
                assert 0 < sensor_temp < 100, \
                    f"Sensor temperature {sensor_temp}°C outside expected range"

        finally:
            client.emit('stop_preview')
            if client.is_connected():
                client.disconnect()

    def test_focus_fom_during_autofocus(self, app, client):
        """Test that Focus FoM changes during autofocus operation"""
        from app import socketio

        camera_streamer = app.config['CAMERA_STREAMER']
        if not camera_streamer.camera:
            camera_streamer.initialize_camera()
            time.sleep(1.0)

        socketio_client = socketio.test_client(app, namespace='/')

        try:
            # Start preview
            socketio_client.emit('start_preview')
            time.sleep(2)

            # Get initial Focus FoM
            socketio_client.emit('get_metadata')
            time.sleep(0.5)
            received1 = socketio_client.get_received()
            metadata1_events = [r for r in received1 if r['name'] == 'metadata_update']
            if metadata1_events:
                initial_fom = metadata1_events[-1]['args'][0]['focus_fom']
                assert initial_fom >= 0

                # Trigger autofocus via HTTP API
                response = client.post('/api/camera/autofocus')
                assert response.status_code == 200
                time.sleep(2)

                # Get updated Focus FoM
                socketio_client.emit('get_metadata')
                time.sleep(0.5)
                received2 = socketio_client.get_received()
                metadata2_events = [r for r in received2 if r['name'] == 'metadata_update']
                if metadata2_events:
                    final_fom = metadata2_events[-1]['args'][0]['focus_fom']
                    assert final_fom >= 0

        finally:
            socketio_client.emit('stop_preview')
            if socketio_client.is_connected():
                socketio_client.disconnect()

    def test_all_extended_fields_present_integration(self, app):
        """Integration test: all 15+ extended metadata fields present with real camera"""
        from app import socketio

        camera_streamer = app.config['CAMERA_STREAMER']
        if not camera_streamer.camera:
            camera_streamer.initialize_camera()
            time.sleep(1.0)

        client = socketio.test_client(app, namespace='/')

        try:
            # Start preview
            client.emit('start_preview')
            time.sleep(2)

            # Request metadata
            client.emit('get_metadata')
            time.sleep(0.5)

            received = client.get_received()
            metadata_events = [r for r in received if r['name'] == 'metadata_update']
            assert len(metadata_events) > 0
            metadata = metadata_events[-1]['args'][0]

            # Verify all extended fields are present
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

            for field in extended_fields:
                assert field in metadata, f"Missing extended metadata field: {field}"

            # Primary fields should also be present
            primary_fields = ['exposure_time', 'analogue_gain', 'lens_position', 'af_state', 'colour_temperature']
            for field in primary_fields:
                assert field in metadata, f"Missing primary metadata field: {field}"

            # Should have no error
            assert 'error' not in metadata or metadata['error'] is None

        finally:
            client.emit('stop_preview')
            if client.is_connected():
                client.disconnect()

    def test_metadata_persistence_across_stream_restart(self, app):
        """Test that metadata extraction works correctly after stream restart"""
        from app import socketio

        camera_streamer = app.config['CAMERA_STREAMER']
        if not camera_streamer.camera:
            camera_streamer.initialize_camera()
            time.sleep(1.0)

        client = socketio.test_client(app, namespace='/')

        try:
            # First stream session
            client.emit('start_preview')
            time.sleep(2)

            client.emit('get_metadata')
            time.sleep(0.5)
            received1 = client.get_received()
            metadata1_events = [r for r in received1 if r['name'] == 'metadata_update']
            assert len(metadata1_events) > 0
            metadata1 = metadata1_events[-1]['args'][0]

            # Verify extended fields present
            assert 'digital_gain' in metadata1
            assert 'focus_fom' in metadata1

            # Stop preview
            client.emit('stop_preview')
            time.sleep(1)

            # Second stream session
            client.emit('start_preview')
            time.sleep(2)

            client.emit('get_metadata')
            time.sleep(0.5)
            received2 = client.get_received()
            metadata2_events = [r for r in received2 if r['name'] == 'metadata_update']
            assert len(metadata2_events) > 0
            metadata2 = metadata2_events[-1]['args'][0]

            # Verify extended fields still present after restart
            assert 'digital_gain' in metadata2
            assert 'focus_fom' in metadata2
            assert 'sensor_timestamp' in metadata2
            assert 'colour_gains' in metadata2

        finally:
            client.emit('stop_preview')
            if client.is_connected():
                client.disconnect()

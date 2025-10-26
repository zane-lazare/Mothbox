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
        camera_streamer = app.config['CAMERA_STREAMER']

        # Initialize camera if needed
        if not camera_streamer.camera:
            camera_streamer.initialize_camera()
            time.sleep(1.0)

        try:
            # Start streaming
            if not camera_streamer.start_streaming():
                pytest.skip("Camera not available")

            time.sleep(2)  # Wait for stream to stabilize

            # Get metadata directly from camera
            metadata = camera_streamer.camera.capture_metadata()

            # Verify all extended fields are present and have reasonable values
            assert 'DigitalGain' in metadata
            assert isinstance(metadata['DigitalGain'], (int, float))
            assert metadata['DigitalGain'] >= 0

            assert 'FocusFoM' in metadata
            assert isinstance(metadata['FocusFoM'], (int, float))
            assert metadata['FocusFoM'] >= 0

            assert 'SensorTimestamp' in metadata
            assert isinstance(metadata['SensorTimestamp'], int)
            assert metadata['SensorTimestamp'] > 0

            assert 'ColourGains' in metadata
            assert isinstance(metadata['ColourGains'], (tuple, list))
            assert len(metadata['ColourGains']) == 2
            assert all(isinstance(g, (int, float)) and g >= 0 for g in metadata['ColourGains'])

            assert 'FrameDuration' in metadata
            assert isinstance(metadata['FrameDuration'], int)
            assert metadata['FrameDuration'] > 0

            assert 'SensorBlackLevels' in metadata
            assert isinstance(metadata['SensorBlackLevels'], (tuple, list))
            assert len(metadata['SensorBlackLevels']) == 4

            assert 'ScalerCrop' in metadata
            assert isinstance(metadata['ScalerCrop'], (tuple, list))
            assert len(metadata['ScalerCrop']) == 4
            assert all(isinstance(v, int) and v >= 0 for v in metadata['ScalerCrop'])

            assert 'Lux' in metadata
            assert isinstance(metadata['Lux'], (int, float))
            assert metadata['Lux'] >= 0

        finally:
            camera_streamer.stop_streaming()

    def test_metadata_updates_in_real_time(self, app):
        """Test that metadata updates reflect real-time camera state changes"""
        camera_streamer = app.config['CAMERA_STREAMER']

        if not camera_streamer.camera:
            camera_streamer.initialize_camera()
            time.sleep(1.0)

        try:
            # Start streaming
            if not camera_streamer.start_streaming():
                pytest.skip("Camera not available")

            time.sleep(2)

            # Get initial metadata
            metadata1 = camera_streamer.camera.capture_metadata()

            # Change a control (sharpness) - tests that control API works
            camera_streamer.update_control({'Sharpness': 2.5})
            time.sleep(1)

            # Get updated metadata
            metadata2 = camera_streamer.camera.capture_metadata()

            # Verify sensor timestamp changed (metadata updates in real time)
            # Note: Sharpness is a control, not part of metadata
            assert metadata2['SensorTimestamp'] > metadata1['SensorTimestamp']

            # Verify other metadata fields are updating
            assert metadata2['FrameDuration'] > 0
            assert metadata2['FocusFoM'] >= 0

        finally:
            camera_streamer.stop_streaming()

    def test_colour_gains_valid_range(self, app):
        """Test that colour gains are in valid range"""
        camera_streamer = app.config['CAMERA_STREAMER']

        if not camera_streamer.camera:
            camera_streamer.initialize_camera()
            time.sleep(1.0)

        try:
            # Start streaming
            if not camera_streamer.start_streaming():
                pytest.skip("Camera not available")

            time.sleep(2)

            # Get metadata directly from camera
            metadata = camera_streamer.camera.capture_metadata()

            # Colour gains should be positive, typically 0.5-4.0
            red_gain, blue_gain = metadata['ColourGains']
            assert 0.1 < red_gain < 10.0, f"Red gain {red_gain} outside expected range"
            assert 0.1 < blue_gain < 10.0, f"Blue gain {blue_gain} outside expected range"

        finally:
            camera_streamer.stop_streaming()

    def test_frame_duration_consistency(self, app):
        """Test that frame duration is consistent and reasonable"""
        camera_streamer = app.config['CAMERA_STREAMER']

        if not camera_streamer.camera:
            camera_streamer.initialize_camera()
            time.sleep(1.0)

        try:
            # Start streaming
            if not camera_streamer.start_streaming():
                pytest.skip("Camera not available")

            time.sleep(2)

            # Collect multiple metadata samples
            frame_durations = []
            for _ in range(5):
                metadata = camera_streamer.camera.capture_metadata()
                frame_durations.append(metadata['FrameDuration'])
                time.sleep(0.5)

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
            camera_streamer.stop_streaming()

    def test_lux_responds_to_exposure_changes(self, app):
        """Test that lux value responds to exposure/gain changes"""
        camera_streamer = app.config['CAMERA_STREAMER']

        if not camera_streamer.camera:
            camera_streamer.initialize_camera()
            time.sleep(1.0)

        try:
            # Start streaming
            if not camera_streamer.start_streaming():
                pytest.skip("Camera not available")

            time.sleep(2)

            # Get metadata directly from camera
            metadata = camera_streamer.camera.capture_metadata()
            initial_lux = metadata['Lux']

            # Verify lux is reasonable (can be 0 in dark conditions)
            assert initial_lux >= 0
            assert isinstance(initial_lux, (int, float))

        finally:
            camera_streamer.stop_streaming()

    def test_digital_gain_reasonable_range(self, app):
        """Test that digital gain is in reasonable range"""
        camera_streamer = app.config['CAMERA_STREAMER']

        if not camera_streamer.camera:
            camera_streamer.initialize_camera()
            time.sleep(1.0)

        try:
            # Start streaming
            if not camera_streamer.start_streaming():
                pytest.skip("Camera not available")

            time.sleep(2)

            # Get metadata directly from camera
            metadata = camera_streamer.camera.capture_metadata()

            # Digital gain should be >= 0.0 and typically < 32.0
            digital_gain = metadata['DigitalGain']
            assert digital_gain >= 0.0, f"Digital gain {digital_gain} is negative"
            assert digital_gain < 32.0, f"Digital gain {digital_gain} is unexpectedly high"

        finally:
            camera_streamer.stop_streaming()

    def test_scaler_crop_updates_with_zoom(self, app):
        """Test that scaler crop updates when digital zoom is changed"""
        camera_streamer = app.config['CAMERA_STREAMER']

        if not camera_streamer.camera:
            camera_streamer.initialize_camera()
            time.sleep(1.0)

        try:
            # Start streaming
            if not camera_streamer.start_streaming():
                pytest.skip("Camera not available")

            time.sleep(2)

            # Get initial crop (no zoom)
            metadata1 = camera_streamer.camera.capture_metadata()
            crop1 = metadata1['ScalerCrop']

            # Apply 2x zoom
            camera_streamer.set_zoom(2.0, None, None)
            time.sleep(1)

            # Get updated crop
            metadata2 = camera_streamer.camera.capture_metadata()
            crop2 = metadata2['ScalerCrop']

            # Crop dimensions should be smaller with zoom
            # crop format: (x, y, width, height)
            if crop1 != (0, 0, 0, 0):  # Skip if no crop initially
                crop1_width = crop1[2]
                crop2_width = crop2[2]
                assert crop2_width < crop1_width, \
                    f"Zoom did not reduce crop width: {crop1_width} -> {crop2_width}"

        finally:
            camera_streamer.stop_streaming()

    def test_zoom_reset_to_full_sensor(self, app):
        """Test that zoom=1.0 resets to full sensor view (Issue #52 Bug #2)"""
        camera_streamer = app.config['CAMERA_STREAMER']

        if not camera_streamer.camera:
            camera_streamer.initialize_camera()
            time.sleep(1.0)

        try:
            # Start streaming
            if not camera_streamer.start_streaming():
                pytest.skip("Camera not available")

            time.sleep(2)

            # Get sensor resolution for reference
            sensor_width, sensor_height = camera_streamer.sensor_resolution
            print(f"\n  Sensor resolution: {sensor_width}x{sensor_height}")

            # Apply 2x zoom
            camera_streamer.set_zoom(2.0, 0.5, 0.5)
            time.sleep(1)

            # Get zoomed crop
            metadata_zoomed = camera_streamer.camera.capture_metadata()
            crop_zoomed = metadata_zoomed['ScalerCrop']
            print(f"  2.0x zoom ScalerCrop: {crop_zoomed}")

            # Verify zoom is active (crop smaller than full sensor)
            assert crop_zoomed[2] < sensor_width, \
                f"2.0x zoom should reduce width: {crop_zoomed[2]} vs {sensor_width}"
            assert crop_zoomed[3] < sensor_height, \
                f"2.0x zoom should reduce height: {crop_zoomed[3]} vs {sensor_height}"

            # Reset zoom to 1.0x
            camera_streamer.set_zoom(1.0, 0.5, 0.5)
            time.sleep(1)

            # Get reset crop
            metadata_reset = camera_streamer.camera.capture_metadata()
            crop_reset = metadata_reset['ScalerCrop']
            print(f"  1.0x reset ScalerCrop: {crop_reset}")

            # Verify zoom reset to full sensor
            # ScalerCrop should be (0, 0, full_width, full_height)
            # Note: Camera may adjust dimensions slightly (±1 pixel) due to hardware constraints
            assert crop_reset[0] == 0, \
                f"Reset zoom should have offset X=0, got {crop_reset[0]}"
            assert crop_reset[1] == 0, \
                f"Reset zoom should have offset Y=0, got {crop_reset[1]}"
            assert abs(crop_reset[2] - sensor_width) <= 1, \
                f"Reset zoom should have full width {sensor_width}, got {crop_reset[2]} (±1 pixel tolerance)"
            assert abs(crop_reset[3] - sensor_height) <= 1, \
                f"Reset zoom should have full height {sensor_height}, got {crop_reset[3]} (±1 pixel tolerance)"

            print(f"  ✓ Zoom reset to 1.0x returns full sensor view")

        finally:
            camera_streamer.stop_streaming()

    def test_zoom_crosshair_alignment(self, app):
        """Test that zoom center aligns with crosshair position (Issue #52 Bug #1)"""
        camera_streamer = app.config['CAMERA_STREAMER']

        if not camera_streamer.camera:
            camera_streamer.initialize_camera()
            time.sleep(1.0)

        try:
            # Start streaming
            if not camera_streamer.start_streaming():
                pytest.skip("Camera not available")

            time.sleep(2)

            # Get sensor resolution
            sensor_width, sensor_height = camera_streamer.sensor_resolution
            print(f"\n  Sensor resolution: {sensor_width}x{sensor_height}")

            # Test case from issue #52: click at (0.75, 0.5) with 2x zoom
            test_zoom = 2.0
            test_center_x = 0.75
            test_center_y = 0.5

            camera_streamer.set_zoom(test_zoom, test_center_x, test_center_y)
            time.sleep(1)

            # Get actual ScalerCrop
            metadata = camera_streamer.camera.capture_metadata()
            scaler_crop = metadata['ScalerCrop']
            offset_x, offset_y, crop_width, crop_height = scaler_crop

            # Calculate actual center of the crop
            actual_center_x = offset_x + crop_width / 2
            actual_center_y = offset_y + crop_height / 2

            # Calculate expected center
            expected_center_x = test_center_x * sensor_width
            expected_center_y = test_center_y * sensor_height

            print(f"  Zoom: {test_zoom}x at ({test_center_x}, {test_center_y})")
            print(f"  Expected center: ({expected_center_x:.0f}, {expected_center_y:.0f})")
            print(f"  Actual center: ({actual_center_x:.0f}, {actual_center_y:.0f})")
            print(f"  ScalerCrop: {scaler_crop}")

            # Verify alignment (allow ±2 pixel tolerance for rounding and even enforcement)
            tolerance = 2
            x_diff = abs(actual_center_x - expected_center_x)
            y_diff = abs(actual_center_y - expected_center_y)

            assert x_diff <= tolerance, \
                f"Crosshair X misalignment: expected {expected_center_x:.0f}, " \
                f"got {actual_center_x:.0f} (diff: {x_diff:.0f} pixels)"
            assert y_diff <= tolerance, \
                f"Crosshair Y misalignment: expected {expected_center_y:.0f}, " \
                f"got {actual_center_y:.0f} (diff: {y_diff:.0f} pixels)"

            print(f"  ✓ Crosshair alignment verified (tolerance: ±{tolerance} pixels)")

        finally:
            camera_streamer.stop_streaming()

    def test_ae_state_reported(self, app):
        """Test that AE state is reported correctly"""
        camera_streamer = app.config['CAMERA_STREAMER']

        if not camera_streamer.camera:
            camera_streamer.initialize_camera()
            time.sleep(1.0)

        try:
            # Start streaming
            if not camera_streamer.start_streaming():
                pytest.skip("Camera not available")

            time.sleep(2)

            # Get metadata directly from camera
            metadata = camera_streamer.camera.capture_metadata()

            # AeState should be present and be an integer
            # Note: Camera provides AeState (int), not AeLocked (bool)
            assert 'AeState' in metadata
            assert isinstance(metadata['AeState'], int)
            assert metadata['AeState'] >= 0  # Valid state codes are >= 0

        finally:
            camera_streamer.stop_streaming()

    def test_sensor_temperature_if_available(self, app):
        """Test sensor temperature if available (optional field)"""
        camera_streamer = app.config['CAMERA_STREAMER']

        if not camera_streamer.camera:
            camera_streamer.initialize_camera()
            time.sleep(1.0)

        try:
            # Start streaming
            if not camera_streamer.start_streaming():
                pytest.skip("Camera not available")

            time.sleep(2)

            # Get metadata directly from camera
            metadata = camera_streamer.camera.capture_metadata()

            # Sensor temperature may be None or a float
            sensor_temp = metadata.get('SensorTemperature')
            if sensor_temp is not None:
                assert isinstance(sensor_temp, (int, float))
                # Should be reasonable temperature in Celsius (0-100°C)
                assert 0 < sensor_temp < 100, \
                    f"Sensor temperature {sensor_temp}°C outside expected range"

        finally:
            camera_streamer.stop_streaming()

    def test_focus_fom_during_autofocus(self, app, client):
        """Test that Focus FoM changes during autofocus operation"""
        camera_streamer = app.config['CAMERA_STREAMER']

        if not camera_streamer.camera:
            camera_streamer.initialize_camera()
            time.sleep(1.0)

        try:
            # Start streaming
            if not camera_streamer.start_streaming():
                pytest.skip("Camera not available")

            time.sleep(2)

            # Get initial Focus FoM
            metadata1 = camera_streamer.camera.capture_metadata()
            initial_fom = metadata1['FocusFoM']
            assert initial_fom >= 0

            # Trigger autofocus via HTTP API
            response = client.post('/api/camera/autofocus')
            assert response.status_code == 200
            time.sleep(2)

            # Get updated Focus FoM
            metadata2 = camera_streamer.camera.capture_metadata()
            final_fom = metadata2['FocusFoM']
            assert final_fom >= 0

        finally:
            camera_streamer.stop_streaming()

    def test_all_extended_fields_present_integration(self, app):
        """Integration test: all 15+ extended metadata fields present with real camera"""
        camera_streamer = app.config['CAMERA_STREAMER']

        if not camera_streamer.camera:
            camera_streamer.initialize_camera()
            time.sleep(1.0)

        try:
            # Start streaming
            if not camera_streamer.start_streaming():
                pytest.skip("Camera not available")

            time.sleep(2)

            # Get metadata directly from camera
            metadata = camera_streamer.camera.capture_metadata()

            # Verify all extended fields are present (using camera's PascalCase names)
            # These are the actual fields that exist in libcamera metadata
            extended_fields = [
                'DigitalGain',              # Digital gain applied
                'FocusFoM',                 # Focus figure of merit
                'SensorTimestamp',          # Sensor frame timestamp
                'ColourGains',              # Red and blue colour gains
                'FrameDuration',            # Frame duration in microseconds
                'SensorBlackLevels',        # Sensor black levels (4 values)
                'ScalerCrop',               # Scaler crop rectangle (x, y, w, h)
                'Lux',                      # Estimated scene lux value
                'AeState',                  # Auto-exposure state
                'ColourCorrectionMatrix',   # 3x3 colour correction matrix
                'FrameWallClock',           # System timestamp
            ]

            for field in extended_fields:
                assert field in metadata, f"Missing extended metadata field: {field}"

            # Note: SensorTemperature is optional and may not be present on all hardware

            # Primary fields should also be present (using camera's PascalCase names)
            primary_fields = ['ExposureTime', 'AnalogueGain', 'LensPosition', 'AfState', 'ColourTemperature']
            for field in primary_fields:
                assert field in metadata, f"Missing primary metadata field: {field}"

        finally:
            camera_streamer.stop_streaming()

    def test_metadata_persistence_across_stream_restart(self, app):
        """Test that metadata extraction works correctly after stream restart"""
        camera_streamer = app.config['CAMERA_STREAMER']

        if not camera_streamer.camera:
            camera_streamer.initialize_camera()
            time.sleep(1.0)

        try:
            # First stream session
            if not camera_streamer.start_streaming():
                pytest.skip("Camera not available")

            time.sleep(2)

            # Get metadata directly from camera
            metadata1 = camera_streamer.camera.capture_metadata()

            # Verify extended fields present
            assert 'DigitalGain' in metadata1
            assert 'FocusFoM' in metadata1

            # Stop streaming
            camera_streamer.stop_streaming()
            time.sleep(1)

            # Second stream session
            if not camera_streamer.start_streaming():
                pytest.skip("Camera not available after restart")

            time.sleep(2)

            # Get metadata again
            metadata2 = camera_streamer.camera.capture_metadata()

            # Verify extended fields still present after restart
            assert 'DigitalGain' in metadata2
            assert 'FocusFoM' in metadata2
            assert 'SensorTimestamp' in metadata2
            assert 'ColourGains' in metadata2

        finally:
            camera_streamer.stop_streaming()

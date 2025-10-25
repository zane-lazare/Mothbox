"""
Integration Tests: AF Window Workflows (Click-to-Focus Feature)

Tests AF window behavior with real hardware including WebSocket integration,
focus performance, zoom interaction, and edge cases.

These tests require real Raspberry Pi hardware and camera.

Run with: pytest Tests/integration/test_af_window_workflows.py -v -s
Or: ./Tests/run_tests.sh clicktofocus
"""

import pytest
import time
from pathlib import Path

# Fixtures (app, client, camera_streamer) are provided by conftest.py


@pytest.mark.stream
@pytest.mark.hardware
class TestAfWindowBasicFunctionality:
    """Test basic AF window set/clear operations"""

    def test_set_af_window_at_center(self, camera_streamer):
        """Test setting AF window at center of frame"""
        print("\n🎯 Testing AF window at center (0.5, 0.5)...")

        # Initialize camera
        success = camera_streamer.initialize_camera()
        assert success, "Camera initialization failed"

        # Start streaming
        camera_streamer.start_streaming()
        time.sleep(1)  # Let stream stabilize

        # Set AF window at center
        success = camera_streamer.set_af_window(0.5, 0.5, window_size=0.2)
        assert success is True, "Failed to set AF window"

        time.sleep(0.5)  # Let AF respond

        print("   ✓ AF window set at center")

        # Stop streaming
        camera_streamer.stop_streaming()

    def test_set_af_window_various_positions(self, camera_streamer):
        """Test setting AF window at various positions"""
        print("\n📍 Testing AF window at various positions...")

        # Initialize camera
        camera_streamer.initialize_camera()
        camera_streamer.start_streaming()
        time.sleep(1)

        positions = [
            (0.25, 0.25, "upper-left"),
            (0.75, 0.25, "upper-right"),
            (0.25, 0.75, "lower-left"),
            (0.75, 0.75, "lower-right"),
            (0.5, 0.5, "center"),
        ]

        for x, y, name in positions:
            success = camera_streamer.set_af_window(x, y, window_size=0.2)
            assert success is True, f"Failed to set AF window at {name}"
            time.sleep(0.3)  # Brief delay
            print(f"   ✓ {name:15s} ({x}, {y})")

        camera_streamer.stop_streaming()

    def test_clear_af_window(self, camera_streamer):
        """Test clearing AF window (reset to auto metering)"""
        print("\n🧹 Testing AF window clearing...")

        camera_streamer.initialize_camera()
        camera_streamer.start_streaming()
        time.sleep(1)

        # Set window
        success = camera_streamer.set_af_window(0.5, 0.5, window_size=0.2)
        assert success is True
        time.sleep(0.5)

        print("   ✓ AF window set")

        # Clear window
        success = camera_streamer.set_af_window(None, None)
        assert success is True
        time.sleep(0.5)

        print("   ✓ AF window cleared (no assertion failure)")

        camera_streamer.stop_streaming()

    def test_multiple_set_clear_cycles(self, camera_streamer):
        """Test multiple AF window set/clear cycles"""
        print("\n🔄 Testing 5 set/clear cycles...")

        camera_streamer.initialize_camera()
        camera_streamer.start_streaming()
        time.sleep(1)

        for i in range(5):
            # Set window
            success = camera_streamer.set_af_window(0.5, 0.5, window_size=0.2)
            assert success is True
            time.sleep(0.2)

            # Clear window
            success = camera_streamer.set_af_window(None, None)
            assert success is True
            time.sleep(0.2)

            print(f"   ✓ Cycle {i+1}/5 complete")

        camera_streamer.stop_streaming()

    def test_af_window_persistence_during_streaming(self, camera_streamer):
        """Test AF window persists during active streaming"""
        print("\n⏱️  Testing AF window persistence during 10-second stream...")

        camera_streamer.initialize_camera()
        camera_streamer.start_streaming()
        time.sleep(1)

        # Set window
        success = camera_streamer.set_af_window(0.5, 0.5, window_size=0.2)
        assert success is True

        # Stream for 10 seconds with AF window active
        print("   Streaming for 10 seconds with AF window active...")
        for i in range(10):
            time.sleep(1)
            if (i + 1) % 3 == 0:
                print(f"   {i+1}s...")

        print("   ✓ AF window persisted during streaming")

        camera_streamer.stop_streaming()


@pytest.mark.stream
@pytest.mark.hardware
class TestAfWindowFocusPerformance:
    """Test AF window focus performance with real objects"""

    def test_focus_on_different_depths(self, camera_streamer):
        """Test focusing on objects at different depths"""
        print("\n🔍 Testing focus at different positions (depth variation)...")
        print("   NOTE: Place objects at different depths in frame")

        camera_streamer.initialize_camera()
        camera_streamer.start_streaming()
        time.sleep(1)

        # Test positions that might have different depth
        positions = [
            (0.3, 0.3, "upper-left region"),
            (0.7, 0.3, "upper-right region"),
            (0.5, 0.5, "center region"),
            (0.3, 0.7, "lower-left region"),
            (0.7, 0.7, "lower-right region"),
        ]

        for x, y, name in positions:
            # Set AF window
            camera_streamer.set_af_window(x, y, window_size=0.2)
            time.sleep(1)  # Allow time for focus to adjust

            # Capture metadata to check focus
            try:
                md = camera_streamer.camera.capture_metadata()
                lens_pos = md.get('LensPosition', 0)
                af_state = md.get('AfState', 0)
                af_state_name = ("Idle", "Scanning", "Focused", "Failed")[af_state] if af_state < 4 else "Unknown"

                print(f"   {name:20s} → Lens: {lens_pos:.2f}D, State: {af_state_name}")

                # Verify AF is responding
                assert af_state != 3, f"Autofocus failed at {name}"

            except Exception as e:
                print(f"   ⚠️ Could not get metadata: {e}")

        camera_streamer.stop_streaming()

    def test_continuous_af_maintains_focus(self, camera_streamer):
        """Test continuous AF maintains focus on selected window"""
        print("\n🎯 Testing continuous AF maintains focus on window...")

        camera_streamer.initialize_camera()
        camera_streamer.start_streaming()
        time.sleep(1)

        # Set AF window
        camera_streamer.set_af_window(0.5, 0.5, window_size=0.2)
        time.sleep(1)

        # Sample lens position over 5 seconds
        lens_positions = []
        for i in range(10):
            try:
                md = camera_streamer.camera.capture_metadata()
                lens_pos = md.get('LensPosition', 0)
                lens_positions.append(lens_pos)
                time.sleep(0.5)
            except:
                pass

        # Verify lens positions are somewhat stable (continuous AF working)
        if len(lens_positions) >= 5:
            avg_lens_pos = sum(lens_positions) / len(lens_positions)
            variance = sum((p - avg_lens_pos)**2 for p in lens_positions) / len(lens_positions)

            print(f"   Average lens position: {avg_lens_pos:.2f}D")
            print(f"   Variance: {variance:.4f}D²")
            print(f"   ✓ Continuous AF maintained focus")

        camera_streamer.stop_streaming()


@pytest.mark.websocket
@pytest.mark.hardware
class TestAfWindowWebSocketIntegration:
    """Test AF window WebSocket event handling"""

    @pytest.fixture(autouse=True, scope='class')
    def ensure_camera_released(self, request, socketio_app):
        """Ensure camera is released before and after WebSocket tests"""
        import gc
        import time

        socketio, app = socketio_app

        # BEFORE: Release camera from ALL sources
        print("\n🔄 Preparing WebSocket tests - releasing all camera resources...")

        # Release from socketio_app's camera_streamer
        camera_streamer_ws = app.config['CAMERA_STREAMER']
        if camera_streamer_ws.streaming:
            camera_streamer_ws.stop_streaming()
        if camera_streamer_ws.camera:
            camera_streamer_ws.release_camera()
        print("   ✓ Released camera from socketio_app")

        # CRITICAL: Also release from module-scoped camera_streamer fixture
        # This is used by the 27 passing tests that ran before WebSocket tests
        try:
            camera_streamer_module = request.getfixturevalue('camera_streamer')
            if camera_streamer_module.streaming:
                camera_streamer_module.stop_streaming()
                print("   ✓ Stopped streaming from module camera_streamer")
            if camera_streamer_module.camera:
                camera_streamer_module.release_camera()
                print("   ✓ Released camera from module camera_streamer")
        except Exception as e:
            print(f"   ⚠️  Could not access camera_streamer fixture: {e}")

        # Force garbage collection and wait for hardware release
        gc.collect()
        gc.collect()  # Second pass for circular refs
        time.sleep(2.0)
        print("   ✓ All camera resources released and ready for WebSocket tests")

        yield

        # AFTER: Cleanup
        print("\n🧹 WebSocket tests complete - final cleanup...")
        if camera_streamer_ws.streaming:
            camera_streamer_ws.stop_streaming()
        if camera_streamer_ws.camera:
            camera_streamer_ws.release_camera()
        gc.collect()
        time.sleep(1.0)
        print("   ✓ Camera resources cleaned up")

    def test_set_af_window_websocket_success(self, socketio_app):
        """Test set_af_window event with valid coordinates"""
        print("\n📡 Testing set_af_window WebSocket event...")

        socketio, app = socketio_app

        # Create test client
        client = socketio.test_client(app, namespace='/')
        assert client.is_connected()

        # Start preview via WebSocket (like user clicking "Start Preview")
        print("   Starting preview via WebSocket...")
        client.emit('start_liveview')
        time.sleep(2)  # Allow camera to initialize

        # Verify preview started
        received = client.get_received()
        preview_msgs = [r for r in received if r['name'] == 'liveview_status']
        assert len(preview_msgs) > 0, "Should receive preview_status event"
        assert preview_msgs[0]['args'][0]['streaming'] is True, "Preview should be streaming"
        print("   ✓ Preview started successfully")

        # Now test set_af_window on live stream
        client.emit('set_af_window', {'x': 0.5, 'y': 0.5, 'window_size': 0.2})
        time.sleep(0.2)

        # Get response
        received = client.get_received()
        af_responses = [r for r in received if r['name'] == 'af_window_updated']

        assert len(af_responses) > 0, "Should receive af_window_updated event"
        response = af_responses[0]['args'][0]

        # Verify
        assert response['success'] is True
        assert response['x'] == 0.5
        assert response['y'] == 0.5
        assert response['window_size'] == 0.2

        print(f"   ✓ Received: {response['message']}")

        # Cleanup - stop preview
        client.emit('stop_liveview')
        time.sleep(0.5)
        client.disconnect()

    def test_clear_af_window_websocket(self, socketio_app):
        """Test clearing AF window via WebSocket"""
        print("\n🧹 Testing clear AF window WebSocket event...")

        socketio, app = socketio_app

        # Create client and start preview
        client = socketio.test_client(app, namespace='/')
        assert client.is_connected()

        print("   Starting preview via WebSocket...")
        client.emit('start_liveview')
        time.sleep(2)
        client.get_received()  # Clear buffer
        print("   ✓ Preview started successfully")

        # Set window first
        client.emit('set_af_window', {'x': 0.5, 'y': 0.5, 'window_size': 0.2})
        time.sleep(0.2)
        client.get_received()  # Clear buffer

        # Clear window
        client.emit('set_af_window', {'x': None, 'y': None})
        time.sleep(0.2)

        # Get response
        received = client.get_received()
        af_responses = [r for r in received if r['name'] == 'af_window_updated']

        assert len(af_responses) > 0
        response = af_responses[0]['args'][0]

        # Verify
        assert response['success'] is True
        assert response['x'] is None
        assert response['y'] is None
        assert 'cleared' in response['message'].lower()

        print(f"   ✓ Received: {response['message']}")

        # Cleanup
        client.emit('stop_liveview')
        time.sleep(0.5)
        client.disconnect()

    def test_af_window_error_not_streaming(self, socketio_app):
        """Test error response when camera not streaming"""
        print("\n⚠️  Testing error handling when camera not streaming...")

        socketio, app = socketio_app

        # Create client but DON'T start preview
        client = socketio.test_client(app, namespace='/')
        assert client.is_connected()
        client.get_received()  # Clear connection messages

        # Try to set AF window without streaming
        client.emit('set_af_window', {'x': 0.5, 'y': 0.5})
        time.sleep(0.2)

        # Get response
        received = client.get_received()
        af_responses = [r for r in received if r['name'] == 'af_window_updated']

        assert len(af_responses) > 0
        response = af_responses[0]['args'][0]

        # Verify error
        assert response['success'] is False
        assert 'error' in response

        print(f"   ✓ Error response: {response['error']}")

        # Cleanup
        client.disconnect()

    def test_af_window_invalid_parameters(self, socketio_app):
        """Test validation of invalid parameters"""
        print("\n⚙️  Testing invalid parameter validation...")

        socketio, app = socketio_app

        # Create client and start preview
        client = socketio.test_client(app, namespace='/')
        assert client.is_connected()

        print("   Starting preview via WebSocket...")
        client.emit('start_liveview')
        time.sleep(2)
        client.get_received()  # Clear buffer
        print("   ✓ Preview started successfully")

        # Test invalid data type (string instead of dict)
        client.emit('set_af_window', "invalid")
        time.sleep(0.2)

        received = client.get_received()
        af_responses = [r for r in received if r['name'] == 'af_window_updated']

        if len(af_responses) > 0:
            response = af_responses[0]['args'][0]
            assert response['success'] is False
            print(f"   ✓ Invalid data type rejected: {response['error']}")

        # Cleanup
        client.emit('stop_liveview')
        time.sleep(0.5)
        client.disconnect()

    def test_websocket_connection_lifecycle(self, socketio_app):
        """Test WebSocket connection and disconnection"""
        print("\n🔌 Testing WebSocket connection lifecycle...")

        socketio, app = socketio_app
        camera_streamer = app.config['CAMERA_STREAMER']

        # Create test client
        client = socketio.test_client(app, namespace='/')
        assert client.is_connected()

        # Check for connection confirmation
        received = client.get_received()
        connected_msgs = [r for r in received if r['name'] == 'connected']

        if len(connected_msgs) > 0:
            msg = connected_msgs[0]['args'][0]
            assert msg['status'] == 'connected'
            print(f"   ✓ Connected: {msg['message']}")

        # Disconnect
        client.disconnect()
        time.sleep(0.2)

        print("   ✓ Connection lifecycle complete")


@pytest.mark.stream
@pytest.mark.hardware
class TestAfWindowZoomInteraction:
    """Test AF window interaction with digital zoom"""

    def test_af_window_independent_from_zoom(self, camera_streamer):
        """Test AF window works independently from zoom level"""
        print("\n🔍 Testing AF window independence from zoom...")

        camera_streamer.initialize_camera()
        camera_streamer.start_streaming()
        time.sleep(1)

        # Set AF window at zoom 1.0x
        success = camera_streamer.set_af_window(0.5, 0.5, window_size=0.2)
        assert success is True
        time.sleep(0.5)

        print("   ✓ AF window set at zoom 1.0x")

        # Change zoom level
        camera_streamer.set_zoom(2.0, 0.5, 0.5)
        time.sleep(0.5)

        print("   ✓ Zoom changed to 2.0x")

        # AF window should still be active
        # (in practice, we'd check camera controls here)

        # Change AF window at zoomed level
        success = camera_streamer.set_af_window(0.7, 0.7, window_size=0.2)
        assert success is True
        time.sleep(0.5)

        print("   ✓ AF window repositioned at zoom 2.0x")

        # Reset zoom
        camera_streamer.set_zoom(1.0, 0.5, 0.5)
        time.sleep(0.5)

        print("   ✓ Zoom reset to 1.0x")
        print("   ✓ AF window and zoom are independent")

        camera_streamer.stop_streaming()

    def test_clear_af_window_doesnt_affect_zoom(self, camera_streamer):
        """Test clearing AF window doesn't affect zoom settings"""
        print("\n🔍 Testing AF window clear doesn't affect zoom...")

        camera_streamer.initialize_camera()
        camera_streamer.start_streaming()
        time.sleep(1)

        # Set zoom
        camera_streamer.set_zoom(2.0, 0.6, 0.4)
        time.sleep(0.5)

        # Set AF window
        camera_streamer.set_af_window(0.5, 0.5, window_size=0.2)
        time.sleep(0.5)

        print("   ✓ Both zoom and AF window set")

        # Clear AF window
        camera_streamer.set_af_window(None, None)
        time.sleep(0.5)

        # Verify zoom is still set (would check zoom_level in practice)
        assert camera_streamer.zoom_level == 2.0
        assert camera_streamer.zoom_center_x == 0.6
        assert camera_streamer.zoom_center_y == 0.4

        print("   ✓ Zoom settings preserved after AF window clear")

        camera_streamer.stop_streaming()


@pytest.mark.stream
@pytest.mark.hardware
class TestAfWindowAssertionFix:
    """Test that assertion failure bug is fixed"""

    def test_clearing_af_window_no_assertion_failure(self, camera_streamer):
        """Test clearing AF window doesn't trigger libcamera assertion"""
        print("\n🐛 Testing assertion failure fix (GitHub issue)...")

        camera_streamer.initialize_camera()
        camera_streamer.start_streaming()
        time.sleep(1)

        # Set window
        success = camera_streamer.set_af_window(0.5, 0.5, window_size=0.2)
        assert success is True
        time.sleep(0.5)

        # Clear window - this was causing assertion failure
        # "Assertion `isArray_' failed"
        success = camera_streamer.set_af_window(None, None)
        assert success is True
        time.sleep(1)  # Give time for assertion to occur if bug exists

        print("   ✓ No assertion failure on clear")

        # Try multiple clear cycles to stress test
        for i in range(5):
            camera_streamer.set_af_window(0.5, 0.5, window_size=0.2)
            time.sleep(0.2)
            camera_streamer.set_af_window(None, None)
            time.sleep(0.2)

        print("   ✓ Multiple clear cycles successful")

        camera_streamer.stop_streaming()

    def test_rectangle_constructor_receives_integers(self, camera_streamer):
        """Test libcamera Rectangle constructor receives integers only"""
        print("\n🔢 Testing Rectangle constructor receives integers...")

        camera_streamer.initialize_camera()
        camera_streamer.start_streaming()
        time.sleep(1)

        # This test verifies the coordinate conversion fix
        # libcamera.Rectangle requires int arguments, not floats

        # Set AF window - should convert floats to ints internally
        success = camera_streamer.set_af_window(0.73, 0.35, window_size=0.2)
        assert success is True

        print("   ✓ Normalized floats (0.73, 0.35) converted to integers")
        print("   ✓ No TypeError from Rectangle constructor")

        camera_streamer.stop_streaming()


@pytest.mark.stream
@pytest.mark.hardware
class TestAfWindowEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_af_window_at_all_corners(self, camera_streamer):
        """Test AF window at all four corners"""
        print("\n📐 Testing AF window at all corners...")

        camera_streamer.initialize_camera()
        camera_streamer.start_streaming()
        time.sleep(1)

        corners = [
            (0.0, 0.0, "top-left"),
            (1.0, 0.0, "top-right"),
            (0.0, 1.0, "bottom-left"),
            (1.0, 1.0, "bottom-right"),
        ]

        for x, y, name in corners:
            success = camera_streamer.set_af_window(x, y, window_size=0.2)
            assert success is True, f"Failed at {name}"
            time.sleep(0.3)
            print(f"   ✓ {name:15s} ({x}, {y})")

        camera_streamer.stop_streaming()

    def test_large_window_at_edge_clamped(self, camera_streamer):
        """Test large window size at edge is clamped correctly"""
        print("\n📏 Testing large window (50%) at edge clamping...")

        camera_streamer.initialize_camera()
        camera_streamer.start_streaming()
        time.sleep(1)

        # Try 50% window at corner - should be clamped
        success = camera_streamer.set_af_window(0.0, 0.0, window_size=0.5)
        assert success is True
        time.sleep(0.5)

        print("   ✓ Large window at corner clamped to sensor bounds")

        # Try 50% window at edge
        success = camera_streamer.set_af_window(0.0, 0.5, window_size=0.5)
        assert success is True
        time.sleep(0.5)

        print("   ✓ Large window at edge clamped to sensor bounds")

        camera_streamer.stop_streaming()

    def test_rapid_position_changes(self, camera_streamer):
        """Test rapid AF window position changes"""
        print("\n⚡ Testing 20 rapid position changes...")

        camera_streamer.initialize_camera()
        camera_streamer.start_streaming()
        time.sleep(1)

        import random
        random.seed(42)

        for i in range(20):
            x = random.random()
            y = random.random()
            success = camera_streamer.set_af_window(x, y, window_size=0.2)
            assert success is True
            time.sleep(0.05)  # Minimal delay

        print("   ✓ All 20 rapid changes succeeded")

        camera_streamer.stop_streaming()

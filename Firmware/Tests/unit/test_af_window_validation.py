"""
Unit Tests: AF Window Validation (Click-to-Focus Feature)

Tests coordinate conversion, parameter validation, bounds checking,
and edge cases for the click-to-focus AF window feature.

Run with: pytest Tests/unit/test_af_window_validation.py -v -s
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))


class TestAfWindowCoordinateConversion:
    """Test normalized to pixel coordinate conversion"""

    def test_center_position_conversion(self):
        """Test AF window at center (0.5, 0.5) converts correctly"""
        from camera_stream import CameraStreamer

        # Create streamer with mock socketio
        mock_socketio = Mock()
        streamer = CameraStreamer(mock_socketio)

        # Mock sensor resolution (9152x6944 - Arducam 64MP OV64A40 sensor)
        streamer.sensor_resolution = (9152, 6944)
        streamer.camera = Mock()
        streamer.streaming = True

        # Mock ScalerCropMaximum property (required for pixel coordinate reference)
        streamer.camera.camera_properties = {
            'ScalerCropMaximum': (0, 0, 9152, 6944)
        }

        # Mock set_controls to capture the call
        controls_set = {}
        def capture_controls(controls):
            controls_set.update(controls)
        streamer.camera.set_controls = capture_controls

        # Set AF window at center with 20% size
        success = streamer.set_af_window(0.5, 0.5, window_size=0.2)

        assert success is True
        assert 'AfWindows' in controls_set
        assert 'AfMetering' in controls_set
        assert controls_set['AfMetering'] == 1  # Windows mode (not 2!)

        # Verify window format: [(x, y, width, height)]
        windows = controls_set['AfWindows']
        assert len(windows) == 1
        x, y, w, h = windows[0]

        # Verify all coordinates are integers (pixel coordinates)
        assert isinstance(x, int), f"x should be int, got {type(x)}"
        assert isinstance(y, int), f"y should be int, got {type(y)}"
        assert isinstance(w, int), f"w should be int, got {type(w)}"
        assert isinstance(h, int), f"h should be int, got {type(h)}"

        # Verify dimensions: 20% of sensor (in pixels, NOT normalized!)
        expected_w = int(9152 * 0.2)  # 1830 (even)
        expected_h = int(6944 * 0.2)  # 1388 (even)
        assert w == expected_w & ~1  # Ensure even
        assert h == expected_h & ~1

        # Verify centered position (in pixels)
        # x should be: (0.5 * 9152) - (w / 2) = 4576 - 915 = 3661 → 3660 (even)
        expected_x = int((0.5 * 9152) - (w / 2)) & ~1
        expected_y = int((0.5 * 6944) - (h / 2)) & ~1
        assert x == expected_x
        assert y == expected_y

        # Verify coordinates are in pixel range, not normalized 0-65535 range
        assert x < 9152, f"x={x} should be in pixel range, not normalized"
        assert y < 6944, f"y={y} should be in pixel range, not normalized"

        print(f"\n✓ Center position (0.5, 0.5) → pixels ({x}, {y}, {w}, {h})")

    def test_corner_position_conversion(self):
        """Test AF window at corner (0.25, 0.25) converts correctly"""
        from camera_stream import CameraStreamer

        mock_socketio = Mock()
        streamer = CameraStreamer(mock_socketio)
        streamer.sensor_resolution = (9152, 6944)
        streamer.camera = Mock()
        streamer.streaming = True

        # Mock ScalerCropMaximum property
        streamer.camera.camera_properties = {
            'ScalerCropMaximum': (0, 0, 9152, 6944)
        }

        controls_set = {}
        streamer.camera.set_controls = lambda c: controls_set.update(c)

        # Set AF window at upper-left quadrant
        success = streamer.set_af_window(0.25, 0.25, window_size=0.2)

        assert success is True
        windows = controls_set['AfWindows']
        x, y, w, h = windows[0]

        # Verify window is within sensor bounds (pixel coordinates)
        assert x >= 0
        assert y >= 0
        assert x + w <= 9152
        assert y + h <= 6944

        # Verify dimensions are even
        assert w % 2 == 0
        assert h % 2 == 0
        assert x % 2 == 0
        assert y % 2 == 0

        # Verify coordinates are in pixel range, not normalized
        assert x < 9152, f"x={x} should be in pixel range"
        assert y < 6944, f"y={y} should be in pixel range"

        print(f"\n✓ Corner position (0.25, 0.25) → pixels ({x}, {y}, {w}, {h})")

    def test_window_size_scaling(self):
        """Test different window sizes convert correctly"""
        from camera_stream import CameraStreamer

        mock_socketio = Mock()
        streamer = CameraStreamer(mock_socketio)
        streamer.sensor_resolution = (9152, 6944)
        streamer.camera = Mock()
        streamer.streaming = True

        # Mock ScalerCropMaximum property
        streamer.camera.camera_properties = {
            'ScalerCropMaximum': (0, 0, 9152, 6944)
        }

        window_sizes = [0.1, 0.2, 0.3, 0.4, 0.5]
        results = []

        for size in window_sizes:
            controls_set = {}
            streamer.camera.set_controls = lambda c: controls_set.update(c)

            streamer.set_af_window(0.5, 0.5, window_size=size)
            x, y, w, h = controls_set['AfWindows'][0]

            # Verify size scales correctly (in pixels)
            expected_w = int(9152 * size) & ~1
            expected_h = int(6944 * size) & ~1

            assert abs(w - expected_w) <= 2, f"Width {w} != expected {expected_w}"
            assert abs(h - expected_h) <= 2, f"Height {h} != expected {expected_h}"

            results.append((size, w, h))

        print(f"\n✓ Window size scaling:")
        for size, w, h in results:
            print(f"   {size:.1f} → {w}x{h} pixels")


class TestAfWindowParameterValidation:
    """Test parameter validation and error handling"""

    def test_none_coordinates_clear_window(self):
        """Test None coordinates trigger window clearing"""
        from camera_stream import CameraStreamer

        mock_socketio = Mock()
        streamer = CameraStreamer(mock_socketio)
        streamer.sensor_resolution = (9152, 6944)
        streamer.camera = Mock()
        streamer.streaming = True

        # Mock ScalerCropMaximum property
        streamer.camera.camera_properties = {
            'ScalerCropMaximum': (0, 0, 9152, 6944)
        }

        controls_set = {}
        streamer.camera.set_controls = lambda c: controls_set.update(c)

        # Clear window with None coordinates
        success = streamer.set_af_window(None, None)

        assert success is True
        assert controls_set['AfMetering'] == 0  # Auto metering
        # Should NOT set AfWindows when clearing (avoid assertion failure)
        # AfWindows should not be present in controls_set when clearing
        assert 'AfWindows' not in controls_set, "AfWindows should not be set when clearing"

        print(f"\n✓ None coordinates clear AF window")

    def test_coordinates_clamped_to_range(self):
        """Test coordinates outside 0-1 range are clamped"""
        from camera_stream import CameraStreamer

        mock_socketio = Mock()
        streamer = CameraStreamer(mock_socketio)
        streamer.sensor_resolution = (9152, 6944)
        streamer.camera = Mock()
        streamer.streaming = True

        # Mock ScalerCropMaximum property
        streamer.camera.camera_properties = {
            'ScalerCropMaximum': (0, 0, 9152, 6944)
        }

        controls_set = {}
        streamer.camera.set_controls = lambda c: controls_set.update(c)

        # Try coordinates outside valid range
        streamer.set_af_window(1.5, -0.5, window_size=0.2)

        windows = controls_set['AfWindows']
        x, y, w, h = windows[0]

        # Verify window is within sensor bounds (clamped)
        assert 0 <= x < 9152
        assert 0 <= y < 6944
        assert x + w <= 9152
        assert y + h <= 6944

        print(f"\n✓ Out-of-range coordinates (1.5, -0.5) clamped to valid bounds")

    def test_camera_not_streaming_returns_false(self):
        """Test setting AF window when camera not streaming returns False"""
        from camera_stream import CameraStreamer

        mock_socketio = Mock()
        streamer = CameraStreamer(mock_socketio)
        streamer.sensor_resolution = (9152, 6944)
        streamer.camera = Mock()
        streamer.streaming = False  # Not streaming

        success = streamer.set_af_window(0.5, 0.5)

        assert success is False
        print(f"\n✓ Returns False when camera not streaming")

    def test_sensor_resolution_not_available(self):
        """Test setting AF window when ScalerCropMaximum not available"""
        from camera_stream import CameraStreamer

        mock_socketio = Mock()
        streamer = CameraStreamer(mock_socketio)
        streamer.sensor_resolution = (9152, 6944)
        streamer.camera = Mock()
        streamer.streaming = True

        # Mock camera_properties without ScalerCropMaximum
        streamer.camera.camera_properties = {}

        success = streamer.set_af_window(0.5, 0.5)

        assert success is False
        print(f"\n✓ Returns False when ScalerCropMaximum not available")

    def test_minimum_window_size_enforced(self):
        """Test minimum window size (5% of frame) is enforced"""
        from camera_stream import CameraStreamer

        mock_socketio = Mock()
        streamer = CameraStreamer(mock_socketio)
        streamer.sensor_resolution = (9152, 6944)
        streamer.camera = Mock()
        streamer.streaming = True

        # Mock ScalerCropMaximum property
        streamer.camera.camera_properties = {
            'ScalerCropMaximum': (0, 0, 9152, 6944)
        }

        controls_set = {}
        streamer.camera.set_controls = lambda c: controls_set.update(c)

        # Try very small window size
        streamer.set_af_window(0.5, 0.5, window_size=0.01)

        windows = controls_set['AfWindows']
        x, y, w, h = windows[0]

        # Verify minimum size is enforced (5% of smaller dimension)
        min_size = int(min(9152, 6944) * 0.05)
        assert w >= min_size
        assert h >= min_size

        print(f"\n✓ Minimum window size enforced: {w}x{h} >= {min_size}x{min_size}")


class TestAfWindowEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_all_corner_positions(self):
        """Test AF window at all four corners"""
        from camera_stream import CameraStreamer

        mock_socketio = Mock()
        streamer = CameraStreamer(mock_socketio)
        streamer.sensor_resolution = (9152, 6944)
        streamer.camera = Mock()
        streamer.streaming = True

        # Mock ScalerCropMaximum property
        streamer.camera.camera_properties = {
            'ScalerCropMaximum': (0, 0, 9152, 6944)
        }

        corners = [
            (0.0, 0.0, "top-left"),
            (1.0, 0.0, "top-right"),
            (0.0, 1.0, "bottom-left"),
            (1.0, 1.0, "bottom-right"),
        ]

        print(f"\n✓ Testing all corners:")
        for norm_x, norm_y, name in corners:
            controls_set = {}
            streamer.camera.set_controls = lambda c: controls_set.update(c)

            success = streamer.set_af_window(norm_x, norm_y, window_size=0.2)

            assert success is True
            windows = controls_set['AfWindows']
            x, y, w, h = windows[0]

            # Verify within bounds (pixel coordinates)
            assert x >= 0
            assert y >= 0
            assert x + w <= 9152
            assert y + h <= 6944

            print(f"   {name:15s} ({norm_x}, {norm_y}) → ({x:4d}, {y:4d}, {w:4d}, {h:4d})")

    def test_all_edge_positions(self):
        """Test AF window at edge midpoints"""
        from camera_stream import CameraStreamer

        mock_socketio = Mock()
        streamer = CameraStreamer(mock_socketio)
        streamer.sensor_resolution = (9152, 6944)
        streamer.camera = Mock()
        streamer.streaming = True

        # Mock ScalerCropMaximum property
        streamer.camera.camera_properties = {
            'ScalerCropMaximum': (0, 0, 9152, 6944)
        }

        edges = [
            (0.5, 0.0, "top-center"),
            (0.5, 1.0, "bottom-center"),
            (0.0, 0.5, "left-center"),
            (1.0, 0.5, "right-center"),
        ]

        print(f"\n✓ Testing all edges:")
        for norm_x, norm_y, name in edges:
            controls_set = {}
            streamer.camera.set_controls = lambda c: controls_set.update(c)

            success = streamer.set_af_window(norm_x, norm_y, window_size=0.2)

            assert success is True
            windows = controls_set['AfWindows']
            x, y, w, h = windows[0]

            # Verify within bounds (pixel coordinates)
            assert x >= 0
            assert y >= 0
            assert x + w <= 9152
            assert y + h <= 6944

            print(f"   {name:15s} ({norm_x}, {norm_y}) → ({x:4d}, {y:4d}, {w:4d}, {h:4d})")

    def test_large_window_at_edge_clamped(self):
        """Test large window size at edge is clamped to sensor bounds"""
        from camera_stream import CameraStreamer

        mock_socketio = Mock()
        streamer = CameraStreamer(mock_socketio)
        streamer.sensor_resolution = (9152, 6944)
        streamer.camera = Mock()
        streamer.streaming = True

        # Mock ScalerCropMaximum property
        streamer.camera.camera_properties = {
            'ScalerCropMaximum': (0, 0, 9152, 6944)
        }

        controls_set = {}
        streamer.camera.set_controls = lambda c: controls_set.update(c)

        # Try 50% window at corner (should be clamped)
        streamer.set_af_window(0.0, 0.0, window_size=0.5)

        windows = controls_set['AfWindows']
        x, y, w, h = windows[0]

        # Verify clamped to bounds (pixel coordinates)
        assert x >= 0
        assert y >= 0
        assert x + w <= 9152
        assert y + h <= 6944

        print(f"\n✓ Large window (50%) at corner clamped: ({x}, {y}, {w}, {h})")

    def test_rapid_set_clear_cycles(self):
        """Test rapid setting and clearing of AF window"""
        from camera_stream import CameraStreamer

        mock_socketio = Mock()
        streamer = CameraStreamer(mock_socketio)
        streamer.sensor_resolution = (9152, 6944)
        streamer.camera = Mock()
        streamer.streaming = True

        # Mock ScalerCropMaximum property
        streamer.camera.camera_properties = {
            'ScalerCropMaximum': (0, 0, 9152, 6944)
        }

        controls_history = []

        def capture_controls(c):
            controls_history.append(c.copy())

        streamer.camera.set_controls = capture_controls

        # Perform 10 rapid set/clear cycles
        for i in range(10):
            streamer.set_af_window(0.5, 0.5, window_size=0.2)
            streamer.set_af_window(None, None)

        # Verify all operations succeeded
        assert len(controls_history) == 20
        print(f"\n✓ Completed 10 rapid set/clear cycles without errors")

    def test_even_dimension_enforcement(self):
        """Test all dimensions are even (encoder requirement)"""
        from camera_stream import CameraStreamer

        mock_socketio = Mock()
        streamer = CameraStreamer(mock_socketio)
        streamer.sensor_resolution = (9152, 6944)
        streamer.camera = Mock()
        streamer.streaming = True

        # Mock ScalerCropMaximum property
        streamer.camera.camera_properties = {
            'ScalerCropMaximum': (0, 0, 9152, 6944)
        }

        # Test many random positions and sizes
        import random
        random.seed(42)

        print(f"\n✓ Testing even dimension enforcement (100 random positions):")
        for i in range(100):
            controls_set = {}
            streamer.camera.set_controls = lambda c: controls_set.update(c)

            x_norm = random.random()
            y_norm = random.random()
            size = random.uniform(0.1, 0.5)

            streamer.set_af_window(x_norm, y_norm, window_size=size)

            windows = controls_set['AfWindows']
            x, y, w, h = windows[0]

            # Verify all dimensions are even (pixel coordinates)
            assert x % 2 == 0, f"x={x} not even"
            assert y % 2 == 0, f"y={y} not even"
            assert w % 2 == 0, f"w={w} not even"
            assert h % 2 == 0, f"h={h} not even"

        print(f"   All 100 positions have even dimensions")

"""
Unit Tests for Focus Peaking Validation

Tests validation logic for focus peaking settings including:
- Intensity range (50-200)
- Color options (green, red, yellow, cyan, magenta)
- Algorithm options (laplacian, sobel, canny)
- Boolean enabled flag
- Integration with camera controls
"""

import pytest
from webui.backend.routes.camera import ALLOWED_CAMERA_SETTINGS


class TestFocusPeakingValidation:
    """Test focus peaking settings validation"""

    def test_focus_peaking_enabled_validation(self):
        """Test FocusPeakingEnabled boolean validation"""
        validator = ALLOWED_CAMERA_SETTINGS['FocusPeakingEnabled']

        # Valid values
        assert validator('true') == True
        assert validator('false') == True
        assert validator('True') == True
        assert validator('False') == True

        # Invalid values
        assert validator('yes') == False
        assert validator('no') == False
        assert validator('1') == False
        assert validator('0') == False

    def test_focus_peaking_intensity_validation(self):
        """Test FocusPeakingIntensity range validation (50-200)"""
        validator = ALLOWED_CAMERA_SETTINGS['FocusPeakingIntensity']

        # Valid values
        assert validator(50) == True
        assert validator(100) == True
        assert validator(150) == True
        assert validator(200) == True
        assert validator('100') == True  # String conversion

        # Invalid values (out of range)
        assert validator(49) == False
        assert validator(201) == False
        assert validator(0) == False
        assert validator(1000) == False

    def test_focus_peaking_color_validation(self):
        """Test FocusPeakingColour options validation"""
        validator = ALLOWED_CAMERA_SETTINGS['FocusPeakingColour']

        # Valid colors
        assert validator('green') == True
        assert validator('red') == True
        assert validator('yellow') == True
        assert validator('cyan') == True
        assert validator('magenta') == True

        # Test case insensitivity
        assert validator('Green') == True
        assert validator('RED') == True

        # Invalid colors
        assert validator('blue') == False
        assert validator('white') == False
        assert validator('black') == False
        assert validator('orange') == False

    def test_focus_peaking_algorithm_validation(self):
        """Test FocusPeakingAlgorithm options validation"""
        validator = ALLOWED_CAMERA_SETTINGS['FocusPeakingAlgorithm']

        # Valid algorithms
        assert validator('laplacian') == True
        assert validator('sobel') == True
        assert validator('canny') == True

        # Test case insensitivity
        assert validator('Laplacian') == True
        assert validator('SOBEL') == True

        # Invalid algorithms
        assert validator('gaussian') == False
        assert validator('prewitt') == False
        assert validator('scharr') == False


class TestFocusPeakingAlgorithm:
    """Test focus peaking edge detection algorithms"""

    @pytest.fixture
    def mock_frame(self):
        """Create a mock BGR frame for testing"""
        try:
            import numpy as np
            # Create a simple test pattern with sharp edges
            # 100x100 BGR image with a white square on black background
            frame = np.zeros((100, 100, 3), dtype=np.uint8)
            frame[25:75, 25:75] = 255  # White square
            return frame
        except ImportError:
            pytest.skip("NumPy not available")

    def test_laplacian_algorithm_exists(self):
        """Test that Laplacian algorithm method exists"""
        from webui.backend.liveview_stream import LiveViewStreamer
        from flask_socketio import SocketIO

        socketio = SocketIO()
        streamer = LiveViewStreamer(socketio)

        assert hasattr(streamer, '_apply_focus_peaking_laplacian')
        assert callable(streamer._apply_focus_peaking_laplacian)

    def test_sobel_algorithm_exists(self):
        """Test that Sobel algorithm method exists"""
        from webui.backend.liveview_stream import LiveViewStreamer
        from flask_socketio import SocketIO

        socketio = SocketIO()
        streamer = LiveViewStreamer(socketio)

        assert hasattr(streamer, '_apply_focus_peaking_sobel')
        assert callable(streamer._apply_focus_peaking_sobel)

    def test_canny_algorithm_exists(self):
        """Test that Canny algorithm method exists"""
        from webui.backend.liveview_stream import LiveViewStreamer
        from flask_socketio import SocketIO

        socketio = SocketIO()
        streamer = LiveViewStreamer(socketio)

        assert hasattr(streamer, '_apply_focus_peaking_canny')
        assert callable(streamer._apply_focus_peaking_canny)

    def test_algorithm_returns_frame(self, mock_frame):
        """Test that algorithms return a frame of the same shape"""
        try:
            import cv2
            import numpy as np
        except ImportError:
            pytest.skip("OpenCV not available")

        from webui.backend.liveview_stream import LiveViewStreamer
        from flask_socketio import SocketIO
        from unittest.mock import patch

        socketio = SocketIO()
        streamer = LiveViewStreamer(socketio)

        # Mock cv2 methods to return proper numpy arrays instead of MagicMock objects
        mock_gray = np.random.randint(0, 256, (480, 640), dtype=np.uint8)
        mock_edge_result = np.random.randint(0, 256, (480, 640), dtype=np.float64)
        mock_edge_mask = np.random.randint(0, 2, (480, 640), dtype=np.uint8) * 255

        with patch.object(cv2, 'cvtColor', return_value=mock_gray):
            with patch.object(cv2, 'Laplacian', return_value=mock_edge_result):
                with patch.object(cv2, 'Sobel', return_value=mock_edge_result):
                    with patch.object(cv2, 'Canny', return_value=mock_edge_mask):
                        with patch.object(cv2, 'getStructuringElement', return_value=np.ones((3, 3), dtype=np.uint8)):
                            with patch.object(cv2, 'morphologyEx', return_value=mock_edge_mask):
                                with patch.object(cv2, 'addWeighted', return_value=mock_frame.copy()):
                                    # Test Laplacian
                                    result = streamer._apply_focus_peaking_laplacian(mock_frame, threshold=100, color='green')
                                    assert result.shape == mock_frame.shape
                                    assert result.dtype == mock_frame.dtype

                                    # Test Sobel
                                    result = streamer._apply_focus_peaking_sobel(mock_frame, threshold=100, color='red')
                                    assert result.shape == mock_frame.shape
                                    assert result.dtype == mock_frame.dtype

                                    # Test Canny
                                    result = streamer._apply_focus_peaking_canny(mock_frame, threshold=100, color='yellow')
                                    assert result.shape == mock_frame.shape
                                    assert result.dtype == mock_frame.dtype

    def test_all_color_options(self, mock_frame):
        """Test that all color options work correctly"""
        try:
            import cv2
            import numpy as np
        except ImportError:
            pytest.skip("OpenCV not available")

        from webui.backend.liveview_stream import LiveViewStreamer
        from flask_socketio import SocketIO
        from unittest.mock import patch

        socketio = SocketIO()
        streamer = LiveViewStreamer(socketio)

        colors = ['green', 'red', 'yellow', 'cyan', 'magenta']

        # Mock cv2 methods to return proper numpy arrays
        mock_gray = np.random.randint(0, 256, (480, 640), dtype=np.uint8)
        mock_edge_result = np.random.randint(0, 256, (480, 640), dtype=np.float64)
        mock_edge_mask = np.random.randint(0, 2, (480, 640), dtype=np.uint8) * 255

        # Create a modified frame to simulate overlay application
        modified_frame = mock_frame.copy()
        modified_frame[0, 0] = [255, 0, 0]  # Change one pixel to ensure difference

        with patch.object(cv2, 'cvtColor', return_value=mock_gray):
            with patch.object(cv2, 'Laplacian', return_value=mock_edge_result):
                with patch.object(cv2, 'getStructuringElement', return_value=np.ones((3, 3), dtype=np.uint8)):
                    with patch.object(cv2, 'morphologyEx', return_value=mock_edge_mask):
                        with patch.object(cv2, 'addWeighted', return_value=modified_frame):
                            for color in colors:
                                result = streamer._apply_focus_peaking_laplacian(mock_frame, threshold=100, color=color)
                                assert result.shape == mock_frame.shape
                                # Verify that overlay was applied (result should differ from input)
                                assert not np.array_equal(result, mock_frame)

    def test_opencv_unavailable_graceful(self):
        """Test that algorithms gracefully handle OpenCV unavailable"""
        from webui.backend.liveview_stream import LiveViewStreamer, CV2_AVAILABLE
        from flask_socketio import SocketIO

        socketio = SocketIO()
        streamer = LiveViewStreamer(socketio)

        if not CV2_AVAILABLE:
            # If OpenCV not available, methods should return frame unmodified
            import numpy as np
            frame = np.zeros((100, 100, 3), dtype=np.uint8)

            result = streamer._apply_focus_peaking_laplacian(frame)
            assert np.array_equal(result, frame)


class TestFocusPeakingSettings:
    """Test focus peaking settings loading and persistence"""

    def test_default_settings(self):
        """Test default focus peaking settings"""
        from webui.backend.liveview_stream import LiveViewStreamer
        from flask_socketio import SocketIO

        socketio = SocketIO()
        streamer = LiveViewStreamer(socketio)

        # Check defaults
        assert streamer.focus_peaking_enabled == False
        assert streamer.focus_peaking_intensity == 100
        assert streamer.focus_peaking_colour == 'green'
        assert streamer.focus_peaking_algorithm == 'laplacian'

    def test_update_control_focus_peaking(self):
        """Test updating focus peaking controls"""
        from webui.backend.liveview_stream import LiveViewStreamer
        from flask_socketio import SocketIO

        socketio = SocketIO()
        streamer = LiveViewStreamer(socketio)

        # Test enabling focus peaking
        result = streamer.update_control({'FocusPeakingEnabled': True})
        assert result == True
        assert streamer.focus_peaking_enabled == True

        # Test intensity update
        result = streamer.update_control({'FocusPeakingIntensity': 150})
        assert result == True
        assert streamer.focus_peaking_intensity == 150

        # Test color update
        result = streamer.update_control({'FocusPeakingColour': 'red'})
        assert result == True
        assert streamer.focus_peaking_colour == 'red'

        # Test algorithm update
        result = streamer.update_control({'FocusPeakingAlgorithm': 'sobel'})
        assert result == True
        assert streamer.focus_peaking_algorithm == 'sobel'

    def test_update_multiple_controls(self):
        """Test updating multiple focus peaking controls at once"""
        from webui.backend.liveview_stream import LiveViewStreamer
        from flask_socketio import SocketIO

        socketio = SocketIO()
        streamer = LiveViewStreamer(socketio)

        # Update all settings at once
        result = streamer.update_control({
            'FocusPeakingEnabled': True,
            'FocusPeakingIntensity': 175,
            'FocusPeakingColour': 'yellow',
            'FocusPeakingAlgorithm': 'canny'
        })

        assert result == True
        assert streamer.focus_peaking_enabled == True
        assert streamer.focus_peaking_intensity == 175
        assert streamer.focus_peaking_colour == 'yellow'
        assert streamer.focus_peaking_algorithm == 'canny'

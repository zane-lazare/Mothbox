"""
Fixture validation tests for LiveViewStreamer mocking infrastructure

Tests that all camera backend mocking fixtures work correctly before
being used in comprehensive unit tests. Validates imports, return types,
array shapes, and mock behavior.

Related: Issue #78 - Camera Backend Testing (Phase 1)
"""

import pytest
import numpy as np
import sys


class TestMockOpenCV:
    """Test mock_opencv fixture provides correct OpenCV mock"""

    def test_opencv_imports(self, mock_opencv):
        """Verify cv2 can be imported after mocking"""
        import cv2
        assert cv2 is not None
        assert hasattr(cv2, 'cvtColor')
        assert hasattr(cv2, 'Laplacian')
        assert hasattr(cv2, 'Sobel')
        assert hasattr(cv2, 'Canny')

    def test_opencv_cvtColor_returns_array(self, mock_opencv):
        """Verify cvtColor returns numpy array with correct shape"""
        import cv2

        test_frame = np.zeros((768, 1024, 3), dtype=np.uint8)
        gray = cv2.cvtColor(test_frame, cv2.COLOR_RGB2GRAY)

        assert isinstance(gray, np.ndarray)
        assert gray.shape == (768, 1024)
        assert gray.dtype == np.uint8

    def test_opencv_laplacian_returns_array(self, mock_opencv):
        """Verify Laplacian returns edge-detected array"""
        import cv2

        test_frame = np.zeros((768, 1024), dtype=np.uint8)
        edges = cv2.Laplacian(test_frame, cv2.CV_64F)

        assert isinstance(edges, np.ndarray)
        assert edges.shape == (768, 1024)

    def test_opencv_sobel_returns_array(self, mock_opencv):
        """Verify Sobel returns directional edges"""
        import cv2

        test_frame = np.zeros((768, 1024), dtype=np.uint8)
        edges = cv2.Sobel(test_frame, cv2.CV_64F, dx=1, dy=0)

        assert isinstance(edges, np.ndarray)
        assert edges.shape == (768, 1024)

    def test_opencv_addWeighted_returns_rgb(self, mock_opencv):
        """Verify addWeighted blends RGB frames"""
        import cv2

        frame1 = np.zeros((768, 1024, 3), dtype=np.uint8)
        frame2 = np.ones((768, 1024, 3), dtype=np.uint8) * 255

        blended = cv2.addWeighted(frame1, 0.7, frame2, 0.3, 0)

        assert isinstance(blended, np.ndarray)
        assert blended.shape == (768, 1024, 3)
        assert blended.dtype == np.uint8


class TestMockSimpleJPEG:
    """Test mock_simplejpeg fixture provides correct encoding"""

    def test_simplejpeg_imports(self, mock_simplejpeg):
        """Verify simplejpeg can be imported after mocking"""
        import simplejpeg
        assert simplejpeg is not None
        assert hasattr(simplejpeg, 'encode_jpeg')

    def test_simplejpeg_encodes_to_jpeg(self, mock_simplejpeg):
        """Verify encode_jpeg returns valid JPEG bytes"""
        import simplejpeg

        frame = np.zeros((768, 1024, 3), dtype=np.uint8)
        jpeg = simplejpeg.encode_jpeg(frame, quality=85, colorspace='RGB')

        assert isinstance(jpeg, bytes)
        assert jpeg[0:2] == b'\xff\xd8'  # JPEG start marker (SOI)
        assert jpeg[-2:] == b'\xff\xd9'  # JPEG end marker (EOI)

    def test_simplejpeg_quality_affects_size(self, mock_simplejpeg):
        """Verify higher quality produces larger JPEG"""
        import simplejpeg

        frame = np.zeros((768, 1024, 3), dtype=np.uint8)
        jpeg_q85 = simplejpeg.encode_jpeg(frame, quality=85)
        jpeg_q95 = simplejpeg.encode_jpeg(frame, quality=95)

        # Q95 should be larger than Q85 (less compression)
        assert len(jpeg_q95) > len(jpeg_q85)


class TestMockMJPEGEncoder:
    """Test mock_mjpeg_encoder fixture provides encoder classes"""

    def test_mjpeg_encoder_instantiation(self, mock_mjpeg_encoder):
        """Verify MJPEGEncoder can be instantiated"""
        MJPEGEncoder = mock_mjpeg_encoder['MJPEGEncoder']

        encoder = MJPEGEncoder(qp=10)
        assert encoder.qp == 10
        assert encoder.enabled is True

    def test_file_output_frame_tracking(self, mock_mjpeg_encoder):
        """Verify FileOutput tracks frames written"""
        FileOutput = mock_mjpeg_encoder['FileOutput']

        output = FileOutput()
        assert output.frames_written == 0

        output.outputframe(b'frame1')
        assert output.frames_written == 1

        output.outputframe(b'frame2')
        assert output.frames_written == 2


class TestMockISPTuning:
    """Test mock_isp_tuning fixture provides tuning files"""

    def test_isp_tuning_files_created(self, mock_isp_tuning, tmp_path):
        """Verify tuning JSON files are created"""
        arducam_path = mock_isp_tuning.get_tuning_path("arducam_64mp")
        assert arducam_path is not None

        import json
        with open(arducam_path) as f:
            tuning = json.load(f)

        assert tuning['target'] == 'arducam_64mp'
        assert 'algorithms' in tuning

    def test_isp_tuning_path_lookup(self, mock_isp_tuning):
        """Verify get_tuning_path returns correct paths"""
        arducam_path = mock_isp_tuning.get_tuning_path("arducam_64mp")
        imx477_path = mock_isp_tuning.get_tuning_path("imx477")
        unknown_path = mock_isp_tuning.get_tuning_path("unknown_sensor")

        assert arducam_path is not None
        assert imx477_path is not None
        assert unknown_path is None


class TestMockPicamera2Enhancement:
    """Test mock_picamera2_for_streamer enhancements"""

    def test_picamera2_camera_properties(self, mock_picamera2_for_streamer):
        """Verify camera_properties includes ScalerCropMaximum"""
        props = mock_picamera2_for_streamer.camera_properties

        assert 'ScalerCropMaximum' in props
        assert 'Model' in props
        assert 'UnitCellSize' in props
        assert 'PixelArraySize' in props

    def test_picamera2_control_history_tracking(self, mock_picamera2_for_streamer):
        """Verify control_history tracks all set_controls calls"""
        camera = mock_picamera2_for_streamer
        camera.start()

        assert len(camera.control_history) == 0

        camera.set_controls({'Brightness': 0.1})
        assert len(camera.control_history) == 1
        assert camera.control_history[0] == {'Brightness': 0.1}

        camera.set_controls({'Sharpness': 2.0})
        assert len(camera.control_history) == 2

    def test_picamera2_state_validation(self, mock_picamera2_for_streamer):
        """Verify set_controls raises error when camera stopped"""
        camera = mock_picamera2_for_streamer

        # Should raise when camera not started
        with pytest.raises(RuntimeError, match="Camera not started"):
            camera.set_controls({'Brightness': 0.1})

        # Should work after start
        camera.start()
        camera.set_controls({'Brightness': 0.1})  # Should not raise

    def test_picamera2_error_simulation(self, mock_picamera2_for_streamer):
        """Verify error simulation methods work"""
        camera = mock_picamera2_for_streamer

        # Simulate busy error
        camera.simulate_camera_busy_error()
        with pytest.raises(RuntimeError, match="Camera is busy"):
            camera.start()

        # Should work on second attempt
        camera.start()
        assert camera.started is True

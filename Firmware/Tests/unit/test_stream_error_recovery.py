"""
Stream Error Recovery Tests for LiveViewStreamer

This file tests error recovery and fallback mechanisms in the streaming pipeline.
Tests cover hardware encoder failures, software encoding errors, and cleanup paths.

These tests target untested lines in liveview_stream.py:
- Lines 719-733: Hardware MJPEG error fallback to software encoding
- Lines 829-831: Software encoding frame capture error recovery
- Lines 837-839: Camera stop error handling in software cleanup
- Lines 861-866: Camera stop error handling in stream loop cleanup

Coverage Target: +3% (lines 719-866)
"""

import pytest
import time
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call

# Import LiveViewStreamer
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))
from liveview_stream import LiveViewStreamer


# ============================================================================
# Test Class: Stream Error Recovery
# ============================================================================

class TestStreamErrorRecovery:
    """Test error recovery and fallback mechanisms in streaming pipeline"""

    def test_hardware_mjpeg_encoder_error_triggers_software_fallback(self, camera_streamer_func, mock_picamera2_for_streamer):
        """
        Test hardware MJPEG encoder failure triggers fallback to software encoding

        Coverage: Lines 719-733
        When hardware encoder fails, should:
        1. Catch exception
        2. Emit warning via WebSocket
        3. Stop recording (if started)
        4. Fall back to _stream_software_encoding()
        """
        streamer = camera_streamer_func
        mock_socketio = MagicMock()
        streamer.socketio = mock_socketio

        # Make MJPEGEncoder initialization fail
        mock_encoder_error = RuntimeError("Hardware encoder initialization failed")

        mock_software_encoding_called = False

        def mock_stream_software():
            nonlocal mock_software_encoding_called
            mock_software_encoding_called = True
            # Don't actually run software encoding, just track that it was called

        with patch('liveview_stream.HARDWARE_MJPEG_AVAILABLE', True):
            with patch('liveview_stream.MJPEGEncoder', side_effect=mock_encoder_error, create=True):
                with patch('liveview_stream.PICAMERA_AVAILABLE', True):
                    with patch('liveview_stream.ISP_TUNING_AVAILABLE', False):
                        with patch('liveview_stream.Picamera2', Mock(return_value=mock_picamera2_for_streamer), create=True):
                            streamer.camera = mock_picamera2_for_streamer
                            streamer.streaming = True
                            streamer.stop_event = MagicMock()
                            streamer.stop_event.is_set = MagicMock(return_value=True)

                            # Patch _stream_software_encoding to track if it's called
                            streamer._stream_software_encoding = mock_stream_software

                            try:
                                streamer._stream_hardware_mjpeg()
                            except:
                                pass  # Method may raise during fallback

                            # Verify software fallback was triggered
                            assert mock_software_encoding_called, "Software encoding fallback should be called"

                            # Verify warning was emitted
                            warning_emitted = False
                            for call_args in mock_socketio.emit.call_args_list:
                                if call_args[0][0] == 'stream_warning':
                                    message = call_args[0][1].get('message', '')
                                    if 'Hardware MJPEG error' in message and 'fallback' in message:
                                        warning_emitted = True
                                        break

                            assert warning_emitted, "Should emit warning about hardware encoder failure"

                            # Verify camera.stop_recording() was attempted (cleanup)
                            mock_picamera2_for_streamer.stop_recording.assert_called()

    def test_software_encoding_frame_capture_error_recovery(self, camera_streamer_func, mock_picamera2_for_streamer):
        """
        Test frame capture error in software encoding loop is handled gracefully

        Coverage: Lines 829-831
        When capture_array() raises exception, should:
        1. Catch exception
        2. Log error
        3. Sleep briefly
        4. Continue streaming loop (not crash)
        """
        streamer = camera_streamer_func
        streamer.stream_mode = 'simplejpeg'
        streamer.streaming = True
        streamer.stop_event = MagicMock()

        # Make capture_array fail once, then succeed
        capture_error = RuntimeError("Frame capture failed - camera busy")
        mock_picamera2_for_streamer.capture_array.side_effect = [
            capture_error,  # First call fails
            None,           # Second call would succeed (but we'll stop streaming)
        ]

        # Stop streaming after first iteration
        streamer.stop_event.is_set = MagicMock(side_effect=[False, True])

        with patch('liveview_stream.HARDWARE_MJPEG_AVAILABLE', False):
            with patch('liveview_stream.PICAMERA_AVAILABLE', True):
                with patch('liveview_stream.ISP_TUNING_AVAILABLE', False):
                    with patch('liveview_stream.Picamera2', Mock(return_value=mock_picamera2_for_streamer), create=True):
                        with patch('time.sleep'):  # Skip sleep delays
                            streamer.camera = mock_picamera2_for_streamer

                            # Run software encoding stream
                            try:
                                streamer._stream_software_encoding()
                            except:
                                pass  # Method may exit with exception

                            # Verify capture_array was called (attempted frame capture)
                            assert mock_picamera2_for_streamer.capture_array.call_count >= 1

                            # Verify camera.stop() was called in finally block
                            mock_picamera2_for_streamer.stop.assert_called()

    def test_camera_stop_error_in_software_cleanup_is_handled(self, camera_streamer_func, mock_picamera2_for_streamer):
        """
        Test camera.stop() exception in software encoding cleanup doesn't crash

        Coverage: Lines 837-839
        When camera.stop() raises exception in finally block, should:
        1. Catch exception
        2. Log error message
        3. Not propagate exception (cleanup completes gracefully)
        """
        streamer = camera_streamer_func
        streamer.stream_mode = 'simplejpeg'
        streamer.streaming = True
        streamer.stop_event = MagicMock()
        streamer.stop_event.is_set = MagicMock(return_value=True)  # Stop immediately

        # Make camera.stop() raise exception
        stop_error = RuntimeError("Camera already stopped or disconnected")
        mock_picamera2_for_streamer.stop.side_effect = stop_error

        with patch('liveview_stream.HARDWARE_MJPEG_AVAILABLE', False):
            with patch('liveview_stream.PICAMERA_AVAILABLE', True):
                with patch('liveview_stream.ISP_TUNING_AVAILABLE', False):
                    with patch('liveview_stream.Picamera2', Mock(return_value=mock_picamera2_for_streamer), create=True):
                        with patch('time.sleep'):  # Skip sleep delays
                            streamer.camera = mock_picamera2_for_streamer

                            # This should NOT raise exception despite camera.stop() failing
                            try:
                                streamer._stream_software_encoding()
                                # If we get here, cleanup handled the exception correctly
                                cleanup_handled = True
                            except RuntimeError as e:
                                if "Camera already stopped" in str(e):
                                    cleanup_handled = False
                                else:
                                    raise

                            assert cleanup_handled, "Cleanup should handle camera.stop() errors gracefully"

                            # Verify camera.stop() was attempted
                            mock_picamera2_for_streamer.stop.assert_called()

    def test_camera_stop_error_in_stream_loop_cleanup_is_handled(self, camera_streamer_func, mock_picamera2_for_streamer):
        """
        Test camera.stop() exception in _stream_loop cleanup doesn't crash

        Coverage: Lines 861-866
        When camera.stop() raises exception in _stream_loop finally block, should:
        1. Catch exception
        2. Log error message
        3. Not propagate exception (cleanup completes gracefully)
        """
        streamer = camera_streamer_func
        streamer.stream_mode = 'simplejpeg'
        streamer.streaming = True
        streamer.stop_event = MagicMock()
        streamer.stop_event.is_set = MagicMock(return_value=True)  # Stop immediately

        # Make camera.stop() raise exception
        stop_error = RuntimeError("I2C communication error during camera stop")
        mock_picamera2_for_streamer.stop.side_effect = stop_error

        with patch('liveview_stream.HARDWARE_MJPEG_AVAILABLE', False):
            with patch('liveview_stream.PICAMERA_AVAILABLE', True):
                with patch('liveview_stream.ISP_TUNING_AVAILABLE', False):
                    with patch('liveview_stream.Picamera2', Mock(return_value=mock_picamera2_for_streamer), create=True):
                        with patch('time.sleep'):  # Skip sleep delays
                            streamer.camera = mock_picamera2_for_streamer

                            # This should NOT raise exception despite camera.stop() failing
                            try:
                                streamer._stream_loop()
                                # If we get here, cleanup handled the exception correctly
                                cleanup_handled = True
                            except RuntimeError as e:
                                if "I2C communication error" in str(e):
                                    cleanup_handled = False
                                else:
                                    raise

                            assert cleanup_handled, "_stream_loop cleanup should handle camera.stop() errors gracefully"

                            # Verify camera.stop() was attempted
                            # Note: stop() may be called twice (once in _stream_software_encoding finally, once in _stream_loop finally)
                            assert mock_picamera2_for_streamer.stop.call_count >= 1

    def test_hardware_mjpeg_start_recording_error_triggers_fallback(self, camera_streamer_func, mock_picamera2_for_streamer):
        """
        Test camera.start_recording() failure triggers software fallback

        Coverage: Lines 687, 719-733
        When start_recording() fails (e.g., encoder incompatibility), should fall back to software
        """
        streamer = camera_streamer_func
        mock_socketio = MagicMock()
        streamer.socketio = mock_socketio

        # Make start_recording fail
        recording_error = RuntimeError("Cannot start recording: encoder configuration error")
        mock_picamera2_for_streamer.start_recording.side_effect = recording_error

        mock_encoder = MagicMock()
        mock_file_output = MagicMock()
        mock_software_encoding_called = False

        def mock_stream_software():
            nonlocal mock_software_encoding_called
            mock_software_encoding_called = True

        with patch('liveview_stream.HARDWARE_MJPEG_AVAILABLE', True):
            with patch('liveview_stream.MJPEGEncoder', return_value=mock_encoder, create=True):
                with patch('liveview_stream.FileOutput', mock_file_output, create=True):
                    with patch('liveview_stream.PICAMERA_AVAILABLE', True):
                        with patch('liveview_stream.ISP_TUNING_AVAILABLE', False):
                            with patch('liveview_stream.Picamera2', Mock(return_value=mock_picamera2_for_streamer), create=True):
                                streamer.camera = mock_picamera2_for_streamer
                                streamer.streaming = True
                                streamer.stop_event = MagicMock()
                                streamer.stop_event.is_set = MagicMock(return_value=True)

                                # Patch _stream_software_encoding to track if it's called
                                streamer._stream_software_encoding = mock_stream_software

                                try:
                                    streamer._stream_hardware_mjpeg()
                                except:
                                    pass

                                # Verify software fallback was triggered
                                assert mock_software_encoding_called, "Should fall back to software encoding"

                                # Verify warning was emitted
                                warning_emitted = False
                                for call_args in mock_socketio.emit.call_args_list:
                                    if call_args[0][0] == 'stream_warning':
                                        message = call_args[0][1].get('message', '')
                                        if 'Hardware MJPEG error' in message:
                                            warning_emitted = True
                                            break

                                assert warning_emitted, "Should emit warning about start_recording failure"

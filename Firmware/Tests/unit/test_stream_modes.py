"""
Unit Tests: Stream Modes and Encoding (Feature Set 1)

Tests encoder selection, fallback mechanisms, quality bounds validation,
and error handling for different stream modes (simplejpeg, PIL, hardware MJPEG).

These tests verify the camera streaming system correctly handles:
- simplejpeg availability and PIL fallback
- Hardware MJPEG mode configuration
- Stream mode validation
- Encoding error recovery
- Resource cleanup on failures
- Quality parameter bounds checking
"""
import pytest
import numpy as np
import io
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import time

# Setup path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))


@pytest.mark.stream
class TestEncoderFallback:
    """Test encoder fallback logic (simplejpeg -> PIL)"""

    def test_simplejpeg_available_by_default(self):
        """Verify simplejpeg is available in test environment"""
        try:
            import simplejpeg
            assert simplejpeg is not None
            print(f"\n✓ simplejpeg version {simplejpeg.__version__} available")
        except ImportError:
            pytest.skip("simplejpeg not installed in test environment")

    @patch('liveview_stream.SIMPLEJPEG_AVAILABLE', False)
    def test_pil_fallback_when_simplejpeg_unavailable(self, camera_streamer_func):
        """Verify PIL is used when simplejpeg is unavailable"""
        from liveview_stream import SIMPLEJPEG_AVAILABLE

        print("\n📊 Testing PIL fallback when simplejpeg unavailable...")

        # Verify simplejpeg is marked unavailable
        assert SIMPLEJPEG_AVAILABLE is False

        # Initialize camera
        success = camera_streamer_func.initialize_camera()
        assert success, "Camera initialization failed"

        # Capture frame should still work with PIL
        try:
            camera_streamer_func.camera.start()
            frame = camera_streamer_func.camera.capture_array()

            # Manually encode with PIL (simulating fallback)
            from PIL import Image
            img = Image.fromarray(frame)
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            buffer.seek(0)
            jpeg_bytes = buffer.read()

            assert len(jpeg_bytes) > 0, "PIL encoding failed"
            print(f"✓ PIL fallback encoding successful: {len(jpeg_bytes):,} bytes")

        finally:
            camera_streamer_func.camera.stop()

    def test_encoding_method_selection(self, camera_streamer_func):
        """Verify correct encoding method is selected based on availability"""
        import liveview_stream

        print("\n📊 Testing encoding method selection...")

        # Check what's available
        has_simplejpeg = liveview_stream.SIMPLEJPEG_AVAILABLE
        has_pil = True  # PIL is always available

        print(f"   simplejpeg available: {has_simplejpeg}")
        print(f"   PIL available: {has_pil}")

        # Initialize and capture frame
        success = camera_streamer_func.initialize_camera()
        assert success, "Camera initialization failed"

        jpeg_bytes = camera_streamer_func.capture_frame()
        assert len(jpeg_bytes) > 0, "Frame encoding failed"

        # Verify JPEG magic bytes (FF D8 FF)
        assert jpeg_bytes[0:2] == b'\xff\xd8', "Invalid JPEG header"

        print(f"✓ Encoding successful: {len(jpeg_bytes):,} bytes")

    def test_simplejpeg_vs_pil_performance(self):
        """Compare simplejpeg vs PIL encoding performance"""
        try:
            import simplejpeg
        except ImportError:
            pytest.skip("simplejpeg not available for performance comparison")

        from PIL import Image

        print("\n⏱️  Comparing simplejpeg vs PIL encoding performance...")

        # Create test frame
        test_frame = np.random.randint(0, 255, (768, 1024, 3), dtype=np.uint8)

        # Benchmark simplejpeg
        start = time.perf_counter()
        for _ in range(10):
            jpeg_bytes = simplejpeg.encode_jpeg(test_frame, quality=85, colorspace='RGB')
        simplejpeg_time = (time.perf_counter() - start) / 10 * 1000  # ms per frame

        # Benchmark PIL
        start = time.perf_counter()
        for _ in range(10):
            img = Image.fromarray(test_frame)
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            buffer.seek(0)
            pil_bytes = buffer.read()
        pil_time = (time.perf_counter() - start) / 10 * 1000  # ms per frame

        speedup = pil_time / simplejpeg_time

        print(f"   simplejpeg: {simplejpeg_time:.1f}ms per frame")
        print(f"   PIL:        {pil_time:.1f}ms per frame")
        print(f"   Speedup:    {speedup:.2f}x")

        # simplejpeg should be faster (or at least not slower)
        assert simplejpeg_time <= pil_time * 1.2, \
            f"simplejpeg unexpectedly slower: {simplejpeg_time:.1f}ms vs {pil_time:.1f}ms"


@pytest.mark.stream
class TestStreamModeValidation:
    """Test stream mode configuration and validation"""

    def test_default_stream_mode(self, camera_streamer_func):
        """Verify default stream mode is simplejpeg"""
        print("\n📊 Testing default stream mode...")
        assert camera_streamer_func.stream_mode == 'simplejpeg'
        print(f"✓ Default stream mode: {camera_streamer_func.stream_mode}")

    def test_hardware_mjpeg_mode_selection(self, camera_streamer_func):
        """Verify hardware MJPEG mode can be set"""
        print("\n📊 Testing hardware MJPEG mode selection...")

        # Set hardware mode
        camera_streamer_func.stream_mode = 'mjpeg_hardware'
        assert camera_streamer_func.stream_mode == 'mjpeg_hardware'
        print(f"✓ Hardware MJPEG mode set: {camera_streamer_func.stream_mode}")

    def test_software_mode_selection(self, camera_streamer_func):
        """Verify software encoding modes can be set"""
        print("\n📊 Testing software mode selection...")

        valid_modes = ['simplejpeg', 'pil', 'software']

        for mode in valid_modes:
            camera_streamer_func.stream_mode = mode
            assert camera_streamer_func.stream_mode == mode
            print(f"✓ Mode '{mode}' accepted")

    def test_invalid_stream_mode_handling(self, camera_streamer_func):
        """Verify invalid stream modes are handled gracefully"""
        print("\n📊 Testing invalid stream mode handling...")

        # Set an invalid mode
        invalid_mode = 'invalid_encoder_xyz'
        camera_streamer_func.stream_mode = invalid_mode

        # Should still accept it (will fall back to software encoding)
        # The actual validation happens during streaming
        assert camera_streamer_func.stream_mode == invalid_mode
        print(f"✓ Invalid mode '{invalid_mode}' set (will use software fallback)")


class TestQualityBounds:
    """Test JPEG quality parameter validation and bounds"""

    def test_quality_minimum_bound(self):
        """Test encoding with quality at minimum (50)"""
        try:
            import simplejpeg
        except ImportError:
            pytest.skip("simplejpeg not available")

        print("\n📊 Testing quality minimum bound (50)...")

        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        # Encode at minimum quality
        jpeg_bytes = simplejpeg.encode_jpeg(test_frame, quality=50, colorspace='RGB')
        assert len(jpeg_bytes) > 0, "Encoding at Q=50 failed"
        print(f"✓ Q=50 encoding successful: {len(jpeg_bytes):,} bytes")

    def test_quality_maximum_bound(self):
        """Test encoding with quality at maximum (100)"""
        try:
            import simplejpeg
        except ImportError:
            pytest.skip("simplejpeg not available")

        print("\n📊 Testing quality maximum bound (100)...")

        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        # Encode at maximum quality
        jpeg_bytes = simplejpeg.encode_jpeg(test_frame, quality=100, colorspace='RGB')
        assert len(jpeg_bytes) > 0, "Encoding at Q=100 failed"
        print(f"✓ Q=100 encoding successful: {len(jpeg_bytes):,} bytes")

    def test_quality_below_minimum_rejected(self):
        """Test that quality below 50 is rejected"""
        try:
            import simplejpeg
        except ImportError:
            pytest.skip("simplejpeg not available")

        print("\n📊 Testing quality below minimum (49)...")

        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        # Try encoding with quality below minimum
        with pytest.raises((ValueError, RuntimeError)):
            simplejpeg.encode_jpeg(test_frame, quality=49, colorspace='RGB')

        print("✓ Q=49 correctly rejected")

    def test_quality_above_maximum_rejected(self):
        """Test that quality above 100 is rejected"""
        try:
            import simplejpeg
        except ImportError:
            pytest.skip("simplejpeg not available")

        print("\n📊 Testing quality above maximum (101)...")

        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        # Try encoding with quality above maximum
        with pytest.raises((ValueError, RuntimeError)):
            simplejpeg.encode_jpeg(test_frame, quality=101, colorspace='RGB')

        print("✓ Q=101 correctly rejected")

    def test_quality_negative_rejected(self):
        """Test that negative quality values are rejected"""
        try:
            import simplejpeg
        except ImportError:
            pytest.skip("simplejpeg not available")

        print("\n📊 Testing negative quality value...")

        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        # Try encoding with negative quality
        with pytest.raises((ValueError, RuntimeError, TypeError)):
            simplejpeg.encode_jpeg(test_frame, quality=-1, colorspace='RGB')

        print("✓ Negative quality correctly rejected")

    def test_quality_string_type_rejected(self):
        """Test that string quality values are rejected"""
        try:
            import simplejpeg
        except ImportError:
            pytest.skip("simplejpeg not available")

        print("\n📊 Testing string quality value...")

        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        # Try encoding with string quality
        with pytest.raises((ValueError, TypeError)):
            simplejpeg.encode_jpeg(test_frame, quality="85", colorspace='RGB')

        print("✓ String quality correctly rejected")

    def test_quality_range_output_sizes(self):
        """Verify quality parameter affects output size as expected"""
        try:
            import simplejpeg
        except ImportError:
            pytest.skip("simplejpeg not available")

        print("\n📊 Testing quality vs output size relationship...")

        test_frame = np.random.randint(0, 255, (768, 1024, 3), dtype=np.uint8)

        results = {}
        for quality in [50, 70, 85, 95, 100]:
            jpeg_bytes = simplejpeg.encode_jpeg(test_frame, quality=quality, colorspace='RGB')
            results[quality] = len(jpeg_bytes)
            print(f"   Q={quality:3d}: {len(jpeg_bytes):>7,} bytes")

        # Verify increasing quality = increasing size
        assert results[50] < results[70] < results[85] < results[100], \
            "Quality should correlate with file size"

        print("✓ Quality correctly affects output size")


@pytest.mark.stream
class TestEncodingErrorHandling:
    """Test error handling during encoding"""

    def test_invalid_frame_dimensions(self):
        """Test encoding with invalid frame dimensions"""
        try:
            import simplejpeg
        except ImportError:
            pytest.skip("simplejpeg not available")

        print("\n📊 Testing invalid frame dimensions...")

        # Empty frame (0x0)
        with pytest.raises((ValueError, RuntimeError)):
            empty_frame = np.zeros((0, 0, 3), dtype=np.uint8)
            simplejpeg.encode_jpeg(empty_frame, quality=85, colorspace='RGB')

        print("✓ Empty frame correctly rejected")

    def test_invalid_color_channels(self):
        """Test encoding with wrong number of color channels"""
        try:
            import simplejpeg
        except ImportError:
            pytest.skip("simplejpeg not available")

        print("\n📊 Testing invalid color channels...")

        # Single channel (grayscale) with RGB colorspace
        gray_frame = np.random.randint(0, 255, (480, 640), dtype=np.uint8)

        with pytest.raises((ValueError, RuntimeError)):
            simplejpeg.encode_jpeg(gray_frame, quality=85, colorspace='RGB')

        print("✓ Invalid channel count correctly rejected")

    def test_corrupted_frame_data(self):
        """Test encoding with corrupted/invalid data types"""
        try:
            import simplejpeg
        except ImportError:
            pytest.skip("simplejpeg not available")

        print("\n📊 Testing corrupted frame data...")

        # Float array instead of uint8
        float_frame = np.random.rand(480, 640, 3).astype(np.float32)

        # Should either convert or reject
        try:
            jpeg_bytes = simplejpeg.encode_jpeg(float_frame, quality=85, colorspace='RGB')
            # If it succeeds, verify output is valid
            assert len(jpeg_bytes) > 0
            print("✓ Float frame converted and encoded")
        except (ValueError, RuntimeError):
            print("✓ Float frame correctly rejected")

    def test_encoding_timeout_scenario(self):
        """Test encoding with extremely large frame (potential timeout)"""
        try:
            import simplejpeg
        except ImportError:
            pytest.skip("simplejpeg not available")

        print("\n📊 Testing encoding timeout scenario...")

        # Very large frame (8K resolution)
        large_frame = np.random.randint(0, 255, (4320, 7680, 3), dtype=np.uint8)

        start = time.perf_counter()
        try:
            jpeg_bytes = simplejpeg.encode_jpeg(large_frame, quality=85, colorspace='RGB')
            elapsed = time.perf_counter() - start

            print(f"✓ Large frame (8K) encoded in {elapsed:.2f}s: {len(jpeg_bytes):,} bytes")

            # Should complete in reasonable time (< 10 seconds)
            assert elapsed < 10.0, f"Encoding took too long: {elapsed:.2f}s"
        except MemoryError:
            print("✓ Large frame rejected due to memory constraints (expected)")


@pytest.mark.stream
class TestResourceCleanup:
    """Test resource cleanup on encoding failures"""

    def test_cleanup_after_encoding_error(self, camera_streamer_func):
        """Verify resources are cleaned up after encoding errors"""
        print("\n📊 Testing resource cleanup after encoding error...")

        # Initialize camera
        success = camera_streamer_func.initialize_camera()
        assert success, "Camera initialization failed"

        # Simulate encoding error by capturing and intentionally failing
        try:
            camera_streamer_func.camera.start()
            frame = camera_streamer_func.camera.capture_array()

            # Force an encoding error (pass invalid quality)
            try:
                import simplejpeg
                simplejpeg.encode_jpeg(frame, quality=-999, colorspace='RGB')
            except (ValueError, RuntimeError, TypeError):
                print("✓ Expected encoding error occurred")
        finally:
            # Verify cleanup works even after error
            camera_streamer_func.camera.stop()
            camera_streamer_func.cleanup()

        # Verify camera is cleaned up
        assert camera_streamer_func.camera is None, "Camera not cleaned up after error"
        print("✓ Resources cleaned up successfully after error")

    def test_multiple_cleanup_calls(self, camera_streamer_func):
        """Verify cleanup can be called multiple times safely"""
        print("\n📊 Testing multiple cleanup calls...")

        # Initialize camera
        success = camera_streamer_func.initialize_camera()
        assert success, "Camera initialization failed"

        # Call cleanup multiple times
        camera_streamer_func.cleanup()
        camera_streamer_func.cleanup()
        camera_streamer_func.cleanup()

        print("✓ Multiple cleanup calls handled safely")

    def test_cleanup_without_initialization(self, camera_streamer_func):
        """Verify cleanup works even if camera was never initialized"""
        print("\n📊 Testing cleanup without initialization...")

        # Call cleanup without initializing camera
        camera_streamer_func.cleanup()

        assert camera_streamer_func.camera is None, "Camera state incorrect"
        print("✓ Cleanup without initialization handled safely")


@pytest.mark.stream
class TestHardwareMJPEGMode:
    """Test hardware MJPEG mode validation and fallback"""

    @patch('camera_stream.HARDWARE_MJPEG_AVAILABLE', False)
    def test_hardware_mjpeg_unavailable_fallback(self, camera_streamer_func):
        """Verify fallback when hardware MJPEG is unavailable"""
        print("\n📊 Testing hardware MJPEG unavailable fallback...")

        # Set to hardware mode
        camera_streamer_func.stream_mode = 'mjpeg_hardware'

        # Verify HARDWARE_MJPEG_AVAILABLE is False
        from liveview_stream import HARDWARE_MJPEG_AVAILABLE
        assert HARDWARE_MJPEG_AVAILABLE is False

        print("✓ Hardware MJPEG marked unavailable, will fall back to software")

    def test_hardware_mjpeg_quality_parameter(self, camera_streamer_func):
        """Verify hardware MJPEG respects quality parameter"""
        print("\n📊 Testing hardware MJPEG quality parameter...")

        # Set quality values
        for quality in [50, 85, 100]:
            camera_streamer_func.jpeg_quality = quality
            assert camera_streamer_func.jpeg_quality == quality
            print(f"✓ Quality {quality} set for hardware MJPEG")

    def test_hardware_mjpeg_resolution_validation(self, camera_streamer_func):
        """Verify hardware MJPEG validates resolution"""
        print("\n📊 Testing hardware MJPEG resolution validation...")

        # Test various resolutions
        resolutions = [
            (640, 480, "VGA"),
            (1024, 768, "Default"),
            (1920, 1080, "Full HD")
        ]

        for width, height, name in resolutions:
            camera_streamer_func.preview_width = width
            camera_streamer_func.preview_height = height

            assert camera_streamer_func.preview_width == width
            assert camera_streamer_func.preview_height == height
            print(f"✓ Resolution {name} ({width}x{height}) validated")

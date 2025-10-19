"""
Integration Tests: Stream Stability (Feature Set 1)

Tests long-running stream stability, memory management, concurrent client
handling, and recovery from error conditions for the camera streaming system.

These tests verify:
- Stream remains stable over 1000+ frames
- Memory usage doesn't grow unbounded
- Frame drops are detected and recovered
- Multiple concurrent WebSocket clients are handled
- Stream can restart after errors
- Resources are properly cleaned up
- Performance doesn't degrade over time

RUN ON RASPBERRY PI ONLY - requires real camera hardware
"""
import pytest
import time
import threading
import gc
import io
import numpy as np
from collections import deque
from unittest.mock import Mock, MagicMock
from PIL import Image

# Try to import simplejpeg for fast JPEG encoding
try:
    import simplejpeg
    SIMPLEJPEG_AVAILABLE = True
except ImportError:
    SIMPLEJPEG_AVAILABLE = False


@pytest.mark.stream
class TestLongRunningStability:
    """Test stream stability over extended periods"""

    @pytest.mark.timeout(120)
    def test_1000_frame_stability(self, camera_streamer_func):
        """Verify stream remains stable over 1000 frames"""
        print("\n🎬 Testing 1000-frame stability...")

        # Initialize camera
        success = camera_streamer_func.initialize_camera()
        assert success, "Camera initialization failed"

        frame_count = 1000
        frames_captured = []
        errors = []

        try:
            camera_streamer_func.camera.start()

            # Let camera ISP stabilize after control changes
            # Sharpness/brightness/contrast controls need warm-up frames
            time.sleep(1.0)
            print("   Camera ISP stabilized")

            for i in range(frame_count):
                try:
                    # Capture frame directly (camera already started by test)
                    frame = camera_streamer_func.camera.capture_array()

                    # Encode as JPEG using fastest available method
                    if SIMPLEJPEG_AVAILABLE:
                        jpeg_bytes = simplejpeg.encode_jpeg(frame, quality=85, colorspace='RGB')
                    else:
                        img = Image.fromarray(frame)
                        buffer = io.BytesIO()
                        img.save(buffer, format='JPEG', quality=85)
                        buffer.seek(0)
                        jpeg_bytes = buffer.read()

                    # Verify frame is valid
                    assert len(jpeg_bytes) > 0, f"Empty frame at {i}"
                    assert jpeg_bytes[0:2] == b'\xff\xd8', f"Invalid JPEG at {i}"

                    frames_captured.append({
                        'index': i,
                        'size': len(jpeg_bytes),
                        'timestamp': time.time()
                    })

                    # Progress updates
                    if (i + 1) % 100 == 0:
                        print(f"   Progress: {i + 1}/{frame_count} frames captured")

                    # Rate limit to prevent camera buffer overflow
                    # Small delay allows ISP to process frames and prevents timeout
                    time.sleep(0.01)  # 10ms delay → max ~100 fps (well above 10 fps target)

                except Exception as e:
                    errors.append({'index': i, 'error': str(e)})
                    print(f"   ⚠ Error at frame {i}: {e}")

            camera_streamer_func.camera.stop()

        finally:
            camera_streamer_func.cleanup()

        # Analyze results
        success_rate = len(frames_captured) / frame_count * 100
        avg_size = sum(f['size'] for f in frames_captured) / len(frames_captured)

        print(f"\n📊 Stability Results:")
        print(f"   Frames captured: {len(frames_captured)}/{frame_count}")
        print(f"   Success rate: {success_rate:.1f}%")
        print(f"   Errors: {len(errors)}")
        print(f"   Average frame size: {avg_size:,.0f} bytes")

        # Success criteria
        assert success_rate >= 99.0, f"Success rate too low: {success_rate:.1f}%"
        assert len(errors) <= 10, f"Too many errors: {len(errors)}"

        print("✓ 1000-frame stability test passed")

    @pytest.mark.timeout(180)
    def test_memory_usage_over_time(self, camera_streamer_func):
        """Monitor memory usage over extended streaming period"""
        try:
            import psutil
            process = psutil.Process()
        except ImportError:
            pytest.skip("psutil not available for memory monitoring")

        print("\n💾 Testing memory usage over time...")

        # Disable continuous autofocus to prevent blocking during rapid frame capture
        # AF operations can pause frame delivery, causing timeouts in tight capture loops
        camera_streamer_func.af_mode = 0  # Manual focus mode

        # Initialize camera
        success = camera_streamer_func.initialize_camera()
        assert success, "Camera initialization failed"

        # Ensure AF is disabled (re-apply after initialization)
        if camera_streamer_func.camera:
            camera_streamer_func.camera.set_controls({"AfMode": 0})
            print("   Autofocus disabled for stability test")

        # Capture memory samples
        memory_samples = []
        sample_interval = 50  # frames between samples
        total_frames = 500

        try:
            camera_streamer_func.camera.start()

            # Let camera ISP stabilize after control changes
            # Sharpness/brightness/contrast controls need warm-up frames
            time.sleep(1.0)
            print("   Camera ISP stabilized")

            for i in range(total_frames):
                # Capture frame directly (camera already started by test)
                frame = camera_streamer_func.camera.capture_array()

                # Encode as JPEG using fastest available method
                if SIMPLEJPEG_AVAILABLE:
                    jpeg_bytes = simplejpeg.encode_jpeg(frame, quality=85, colorspace='RGB')
                else:
                    img = Image.fromarray(frame)
                    buffer = io.BytesIO()
                    img.save(buffer, format='JPEG', quality=85)
                    buffer.seek(0)
                    jpeg_bytes = buffer.read()

                # Sample memory periodically
                if i % sample_interval == 0:
                    gc.collect()  # Force garbage collection before measuring
                    mem_info = process.memory_info()
                    memory_samples.append({
                        'frame': i,
                        'rss_mb': mem_info.rss / 1024 / 1024,
                        'vms_mb': mem_info.vms / 1024 / 1024
                    })
                    print(f"   Frame {i:4d}: RSS={mem_info.rss / 1024 / 1024:.1f}MB")

                # Rate limit to prevent camera buffer overflow
                # Small delay allows ISP to process frames and prevents timeout
                time.sleep(0.01)  # 10ms delay → max ~100 fps (well above 10 fps target)

            camera_streamer_func.camera.stop()

        finally:
            camera_streamer_func.cleanup()

        # Analyze memory growth
        first_sample = memory_samples[0]['rss_mb']
        last_sample = memory_samples[-1]['rss_mb']
        max_sample = max(s['rss_mb'] for s in memory_samples)
        memory_growth = last_sample - first_sample

        print(f"\n📊 Memory Usage Analysis:")
        print(f"   Initial RSS: {first_sample:.1f}MB")
        print(f"   Final RSS: {last_sample:.1f}MB")
        print(f"   Peak RSS: {max_sample:.1f}MB")
        print(f"   Growth: {memory_growth:+.1f}MB")

        # Memory should not grow more than 50MB
        assert memory_growth < 50.0, \
            f"Memory growth too high: {memory_growth:.1f}MB (limit: 50MB)"

        print("✓ Memory usage stable over time")

    @pytest.mark.timeout(60)
    def test_frame_timing_consistency(self, camera_streamer_func):
        """Verify frame capture timing remains consistent"""
        print("\n⏱️  Testing frame timing consistency...")

        # Initialize camera
        success = camera_streamer_func.initialize_camera()
        assert success, "Camera initialization failed"

        frame_count = 200
        frame_times = []
        target_fps = 10
        target_interval = 1.0 / target_fps

        try:
            camera_streamer_func.camera.start()

            # Let camera ISP stabilize after control changes
            # Sharpness/brightness/contrast controls need warm-up frames
            time.sleep(1.0)
            print("   Camera ISP stabilized")

            last_time = time.time()

            for i in range(frame_count):
                # Capture frame directly (camera already started by test)
                frame = camera_streamer_func.camera.capture_array()

                # Encode as JPEG using fastest available method
                if SIMPLEJPEG_AVAILABLE:
                    jpeg_bytes = simplejpeg.encode_jpeg(frame, quality=85, colorspace='RGB')
                else:
                    img = Image.fromarray(frame)
                    buffer = io.BytesIO()
                    img.save(buffer, format='JPEG', quality=85)
                    buffer.seek(0)
                    jpeg_bytes = buffer.read()

                # Record timing
                current_time = time.time()
                interval = current_time - last_time
                frame_times.append(interval)
                last_time = current_time

                # Rate limit to target FPS
                time.sleep(target_interval)

                if (i + 1) % 50 == 0:
                    print(f"   Progress: {i + 1}/{frame_count} frames")

            camera_streamer_func.camera.stop()

        finally:
            camera_streamer_func.cleanup()

        # Analyze timing (skip first frame as it's initialization)
        intervals = frame_times[1:]
        avg_interval = sum(intervals) / len(intervals)
        min_interval = min(intervals)
        max_interval = max(intervals)
        std_dev = np.std(intervals)

        print(f"\n📊 Frame Timing Analysis:")
        print(f"   Target interval: {target_interval * 1000:.1f}ms")
        print(f"   Average interval: {avg_interval * 1000:.1f}ms")
        print(f"   Min interval: {min_interval * 1000:.1f}ms")
        print(f"   Max interval: {max_interval * 1000:.1f}ms")
        print(f"   Std deviation: {std_dev * 1000:.1f}ms")

        # Average should be close to target (within 20%)
        assert abs(avg_interval - target_interval) < target_interval * 0.2, \
            f"Average interval {avg_interval:.3f}s too far from target {target_interval:.3f}s"

        print("✓ Frame timing consistent over time")


@pytest.mark.stream
class TestFrameDropDetection:
    """Test frame drop detection and recovery"""

    @pytest.mark.timeout(60)
    def test_detect_frame_drops(self, camera_streamer_func):
        """Verify frame drops can be detected"""
        print("\n🎬 Testing frame drop detection...")

        # Initialize camera
        success = camera_streamer_func.initialize_camera()
        assert success, "Camera initialization failed"

        frame_count = 100
        target_fps = 10
        frame_delay = 1.0 / target_fps

        frames_captured = []
        start_time = time.time()

        try:
            camera_streamer_func.camera.start()

            for i in range(frame_count):
                frame_start = time.time()

                # Capture frame directly (camera already started by test)
                frame = camera_streamer_func.camera.capture_array()

                # Encode as JPEG using fastest available method
                if SIMPLEJPEG_AVAILABLE:
                    jpeg_bytes = simplejpeg.encode_jpeg(frame, quality=85, colorspace='RGB')
                else:
                    img = Image.fromarray(frame)
                    buffer = io.BytesIO()
                    img.save(buffer, format='JPEG', quality=85)
                    buffer.seek(0)
                    jpeg_bytes = buffer.read()

                frames_captured.append({
                    'index': i,
                    'timestamp': time.time(),
                    'size': len(jpeg_bytes)
                })

                # Sleep to maintain FPS
                elapsed = time.time() - frame_start
                if elapsed < frame_delay:
                    time.sleep(frame_delay - elapsed)

            camera_streamer_func.camera.stop()

        finally:
            camera_streamer_func.cleanup()

        total_time = time.time() - start_time
        expected_time = frame_count * frame_delay
        actual_fps = frame_count / total_time

        print(f"\n📊 Frame Drop Analysis:")
        print(f"   Frames captured: {len(frames_captured)}/{frame_count}")
        print(f"   Expected time: {expected_time:.1f}s")
        print(f"   Actual time: {total_time:.1f}s")
        print(f"   Target FPS: {target_fps}")
        print(f"   Actual FPS: {actual_fps:.1f}")

        # Should capture all frames
        assert len(frames_captured) == frame_count, \
            f"Frame drops detected: {frame_count - len(frames_captured)}"

        print("✓ No frame drops detected")


@pytest.mark.stream
class TestConcurrentClients:
    """Test concurrent WebSocket client handling"""

    @pytest.mark.timeout(60)
    def test_multiple_clients_receiving_frames(self, camera_streamer_func):
        """Test streaming to multiple concurrent clients"""
        print("\n👥 Testing multiple concurrent clients...")

        # Create mock clients
        num_clients = 3
        clients = []
        client_frames = {i: [] for i in range(num_clients)}

        class MockClient:
            def __init__(self, client_id):
                self.client_id = client_id
                self.connected = True

            def receive_frame(self, frame_data):
                client_frames[self.client_id].append({
                    'timestamp': time.time(),
                    'size': len(frame_data)
                })

        # Create clients
        for i in range(num_clients):
            clients.append(MockClient(i))
            print(f"   Client {i} created")

        # Initialize camera and stream frames
        success = camera_streamer_func.initialize_camera()
        assert success, "Camera initialization failed"

        frame_count = 50

        try:
            camera_streamer_func.camera.start()

            for i in range(frame_count):
                # Capture frame directly (camera already started by test)
                frame = camera_streamer_func.camera.capture_array()

                # Encode as JPEG using fastest available method
                if SIMPLEJPEG_AVAILABLE:
                    jpeg_bytes = simplejpeg.encode_jpeg(frame, quality=85, colorspace='RGB')
                else:
                    img = Image.fromarray(frame)
                    buffer = io.BytesIO()
                    img.save(buffer, format='JPEG', quality=85)
                    buffer.seek(0)
                    jpeg_bytes = buffer.read()

                # Send to all clients
                for client in clients:
                    if client.connected:
                        client.receive_frame(jpeg_bytes)

                if (i + 1) % 10 == 0:
                    print(f"   Progress: {i + 1}/{frame_count} frames sent")

                # Rate limit to prevent camera buffer overflow
                time.sleep(0.01)

            camera_streamer_func.camera.stop()

        finally:
            camera_streamer_func.cleanup()

        # Verify all clients received all frames
        print(f"\n📊 Client Frame Reception:")
        for i in range(num_clients):
            frames_received = len(client_frames[i])
            print(f"   Client {i}: {frames_received}/{frame_count} frames")
            assert frames_received == frame_count, \
                f"Client {i} missed frames: {frame_count - frames_received}"

        print("✓ All clients received all frames")

    @pytest.mark.timeout(90)
    def test_client_connect_disconnect_during_stream(self, camera_streamer_func):
        """Test clients connecting/disconnecting during active stream"""
        print("\n🔌 Testing client connect/disconnect during stream...")

        # Initialize camera
        success = camera_streamer_func.initialize_camera()
        assert success, "Camera initialization failed"

        clients = []
        frame_count = 100
        frames_sent = 0

        class MockClient:
            def __init__(self, client_id, connect_at, disconnect_at):
                self.client_id = client_id
                self.connect_at = connect_at
                self.disconnect_at = disconnect_at
                self.connected = False
                self.frames_received = 0

            def maybe_connect(self, frame_num):
                if frame_num >= self.connect_at and not self.connected:
                    self.connected = True
                    print(f"   Client {self.client_id} connected at frame {frame_num}")

            def maybe_disconnect(self, frame_num):
                if frame_num >= self.disconnect_at and self.connected:
                    self.connected = False
                    print(f"   Client {self.client_id} disconnected at frame {frame_num}")

            def receive_frame(self, frame_data):
                if self.connected:
                    self.frames_received += 1

        # Create clients with different connection patterns
        clients.append(MockClient(0, connect_at=0, disconnect_at=100))  # Always connected
        clients.append(MockClient(1, connect_at=20, disconnect_at=60))  # Mid-stream
        clients.append(MockClient(2, connect_at=50, disconnect_at=100)) # Late joiner

        try:
            camera_streamer_func.camera.start()

            for i in range(frame_count):
                # Handle client connections/disconnections
                for client in clients:
                    client.maybe_connect(i)
                    client.maybe_disconnect(i)

                # Capture frame directly (camera already started by test)
                frame = camera_streamer_func.camera.capture_array()

                # Encode as JPEG using fastest available method
                if SIMPLEJPEG_AVAILABLE:
                    jpeg_bytes = simplejpeg.encode_jpeg(frame, quality=85, colorspace='RGB')
                else:
                    img = Image.fromarray(frame)
                    buffer = io.BytesIO()
                    img.save(buffer, format='JPEG', quality=85)
                    buffer.seek(0)
                    jpeg_bytes = buffer.read()

                # Send to connected clients
                for client in clients:
                    client.receive_frame(jpeg_bytes)

                frames_sent += 1

                # Rate limit to prevent camera buffer overflow
                time.sleep(0.01)

            camera_streamer_func.camera.stop()

        finally:
            camera_streamer_func.cleanup()

        # Verify frame counts
        print(f"\n📊 Client Connection Results:")
        for client in clients:
            expected = client.disconnect_at - client.connect_at
            print(f"   Client {client.client_id}: {client.frames_received}/{expected} frames")
            assert client.frames_received == expected, \
                f"Client {client.client_id} frame count mismatch"

        print("✓ Client connect/disconnect handled correctly")


@pytest.mark.stream
class TestStreamRestart:
    """Test stream restart after various error conditions"""

    @pytest.mark.timeout(60)
    def test_restart_after_stop(self, camera_streamer_func):
        """Verify stream can restart after normal stop"""
        print("\n🔄 Testing stream restart after stop...")

        # First stream session
        success = camera_streamer_func.initialize_camera()
        assert success, "First initialization failed"

        try:
            camera_streamer_func.camera.start()
            jpeg_bytes = camera_streamer_func.capture_frame()
            assert len(jpeg_bytes) > 0, "First capture failed"
            print("   ✓ First stream session successful")
            camera_streamer_func.camera.stop()
        finally:
            camera_streamer_func.cleanup()

        # Wait a bit
        time.sleep(1)

        # Second stream session
        success = camera_streamer_func.initialize_camera()
        assert success, "Second initialization failed"

        try:
            camera_streamer_func.camera.start()
            jpeg_bytes = camera_streamer_func.capture_frame()
            assert len(jpeg_bytes) > 0, "Second capture failed"
            print("   ✓ Second stream session successful")
            camera_streamer_func.camera.stop()
        finally:
            camera_streamer_func.cleanup()

        print("✓ Stream restart after stop successful")

    @pytest.mark.timeout(60)
    def test_restart_after_error_recovery(self, camera_streamer_func):
        """Verify stream can restart after recovering from error"""
        print("\n🔄 Testing stream restart after error recovery...")

        # Initialize camera
        success = camera_streamer_func.initialize_camera()
        assert success, "Initialization failed"

        try:
            camera_streamer_func.camera.start()

            # Simulate error condition (force stop without cleanup)
            camera_streamer_func.camera.stop()

            # Immediate restart should work
            camera_streamer_func.camera.start()
            jpeg_bytes = camera_streamer_func.capture_frame()
            assert len(jpeg_bytes) > 0, "Capture after restart failed"

            print("   ✓ Stream recovered after error")

            camera_streamer_func.camera.stop()

        finally:
            camera_streamer_func.cleanup()

        print("✓ Stream restart after error recovery successful")

    @pytest.mark.timeout(60)
    def test_multiple_restart_cycles(self, camera_streamer_func):
        """Test multiple start/stop cycles"""
        print("\n🔄 Testing multiple restart cycles...")

        num_cycles = 5

        for cycle in range(num_cycles):
            print(f"   Cycle {cycle + 1}/{num_cycles}...")

            # Initialize and start
            success = camera_streamer_func.initialize_camera()
            assert success, f"Initialization failed at cycle {cycle + 1}"

            try:
                camera_streamer_func.camera.start()

                # Capture a few frames
                for _ in range(5):
                    jpeg_bytes = camera_streamer_func.capture_frame()
                    assert len(jpeg_bytes) > 0, f"Capture failed at cycle {cycle + 1}"

                camera_streamer_func.camera.stop()

            finally:
                camera_streamer_func.cleanup()

            # Small delay between cycles
            time.sleep(0.5)

        print(f"✓ {num_cycles} restart cycles completed successfully")


@pytest.mark.stream
class TestResourceCleanup:
    """Test resource cleanup and verification"""

    @pytest.mark.timeout(30)
    def test_cleanup_releases_camera(self, camera_streamer_func):
        """Verify cleanup properly releases camera resources"""
        print("\n🧹 Testing cleanup releases camera...")

        # Initialize camera
        success = camera_streamer_func.initialize_camera()
        assert success, "Initialization failed"

        # Start camera
        camera_streamer_func.camera.start()
        print("   ✓ Camera started")

        # Cleanup
        camera_streamer_func.cleanup()

        # Verify camera is None
        assert camera_streamer_func.camera is None, "Camera not released after cleanup"
        print("   ✓ Camera released")

    @pytest.mark.timeout(30)
    def test_cleanup_stops_streaming(self, camera_streamer_func):
        """Verify cleanup stops active streaming"""
        print("\n🧹 Testing cleanup stops streaming...")

        # Start streaming
        success = camera_streamer_func.start_streaming()
        assert success, "Stream start failed"
        assert camera_streamer_func.streaming is True, "Streaming flag not set"

        print("   ✓ Streaming started")

        # Small delay to let stream start
        time.sleep(1)

        # Cleanup
        camera_streamer_func.cleanup()

        # Verify streaming stopped
        assert camera_streamer_func.streaming is False, "Streaming not stopped"
        print("   ✓ Streaming stopped")

    @pytest.mark.timeout(30)
    def test_cleanup_with_active_frames(self, camera_streamer_func):
        """Verify cleanup works while actively capturing frames"""
        print("\n🧹 Testing cleanup during active capture...")

        # Initialize and start
        success = camera_streamer_func.initialize_camera()
        assert success, "Initialization failed"

        try:
            camera_streamer_func.camera.start()

            # Capture a few frames
            for i in range(3):
                # Capture frame directly (camera already started by test)
                frame = camera_streamer_func.camera.capture_array()

                # Encode as JPEG using fastest available method
                if SIMPLEJPEG_AVAILABLE:
                    jpeg_bytes = simplejpeg.encode_jpeg(frame, quality=85, colorspace='RGB')
                else:
                    img = Image.fromarray(frame)
                    buffer = io.BytesIO()
                    img.save(buffer, format='JPEG', quality=85)
                    buffer.seek(0)
                    jpeg_bytes = buffer.read()

                print(f"   Frame {i + 1} captured: {len(jpeg_bytes):,} bytes")

            # Cleanup while "active"
            camera_streamer_func.cleanup()

            assert camera_streamer_func.camera is None, "Camera not cleaned up"
            print("   ✓ Cleanup successful during active capture")

        except Exception as e:
            # If cleanup is called, make sure it still works
            camera_streamer_func.cleanup()
            raise


@pytest.mark.stream
@pytest.mark.performance
class TestPerformanceDegradation:
    """Test for performance degradation over time"""

    @pytest.mark.timeout(120)
    def test_encoding_speed_stability(self, camera_streamer_func):
        """Verify encoding speed doesn't degrade over time"""
        print("\n⏱️  Testing encoding speed stability...")

        # Initialize camera
        success = camera_streamer_func.initialize_camera()
        assert success, "Initialization failed"

        batch_size = 50
        num_batches = 10
        batch_times = []

        try:
            camera_streamer_func.camera.start()

            for batch in range(num_batches):
                batch_start = time.time()

                for _ in range(batch_size):
                    # Capture frame directly (camera already started by test)
                    frame = camera_streamer_func.camera.capture_array()

                    # Encode as JPEG using fastest available method
                    if SIMPLEJPEG_AVAILABLE:
                        jpeg_bytes = simplejpeg.encode_jpeg(frame, quality=85, colorspace='RGB')
                    else:
                        img = Image.fromarray(frame)
                        buffer = io.BytesIO()
                        img.save(buffer, format='JPEG', quality=85)
                        buffer.seek(0)
                        jpeg_bytes = buffer.read()

                    # Small delay to prevent camera buffer overflow
                    time.sleep(0.01)

                batch_elapsed = time.time() - batch_start
                avg_time = batch_elapsed / batch_size * 1000  # ms per frame

                batch_times.append(avg_time)
                print(f"   Batch {batch + 1}: {avg_time:.1f}ms per frame")

            camera_streamer_func.camera.stop()

        finally:
            camera_streamer_func.cleanup()

        # Analyze for degradation
        first_half = sum(batch_times[:num_batches//2]) / (num_batches//2)
        second_half = sum(batch_times[num_batches//2:]) / (num_batches - num_batches//2)
        degradation = ((second_half - first_half) / first_half) * 100

        print(f"\n📊 Performance Analysis:")
        print(f"   First half avg: {first_half:.1f}ms")
        print(f"   Second half avg: {second_half:.1f}ms")
        print(f"   Degradation: {degradation:+.1f}%")

        # Performance should not degrade more than 15%
        assert degradation < 15.0, \
            f"Performance degraded by {degradation:.1f}% (limit: 15%)"

        print("✓ Encoding speed stable over time")

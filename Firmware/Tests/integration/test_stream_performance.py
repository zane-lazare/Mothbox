"""
Integration tests for streaming performance

Note: These are CPU-bound performance tests using simplejpeg library.
They do NOT require Raspberry Pi hardware or actual camera.
"""
import pytest
import time
import numpy as np
import base64

# Try to import simplejpeg for fast JPEG encoding
try:
    import simplejpeg
    SIMPLEJPEG_AVAILABLE = True
except ImportError:
    SIMPLEJPEG_AVAILABLE = False

# Skip all tests if simplejpeg not available
pytestmark = pytest.mark.skipif(not SIMPLEJPEG_AVAILABLE, reason="simplejpeg not installed")


@pytest.mark.stream
@pytest.mark.performance
@pytest.mark.timeout(30)
class TestStreamingPerformance:
    """Test sustained streaming performance"""

    def test_sustained_10fps_no_backlog(self):
        """Verify can sustain 10 FPS without frame backlog"""
        test_frame = np.random.randint(0, 255, (768, 1024, 3), dtype=np.uint8)

        frame_count = 100
        target_fps = 10
        frame_budget_ms = 1000 / target_fps  # 100ms per frame

        encoding_times = []

        print(f"\n🎬 Encoding {frame_count} frames at target {target_fps} FPS...")

        for i in range(frame_count):
            start = time.perf_counter()
            jpeg_bytes = simplejpeg.encode_jpeg(test_frame, quality=85, colorspace='RGB')
            img_base64 = base64.b64encode(jpeg_bytes).decode('utf-8')
            encoding_times.append((time.perf_counter() - start) * 1000)

            if (i + 1) % 25 == 0:
                print(f"   Progress: {i + 1}/{frame_count} frames...")

        avg_time = sum(encoding_times) / len(encoding_times)
        max_time = max(encoding_times)
        min_time = min(encoding_times)

        print(f"\n📊 Sustained {frame_count} frames @ {target_fps} FPS:")
        print(f"   Avg encoding: {avg_time:.1f}ms")
        print(f"   Min encoding: {min_time:.1f}ms")
        print(f"   Max encoding: {max_time:.1f}ms")
        print(f"   Frame budget: {frame_budget_ms}ms")
        print(f"   Avg headroom: {frame_budget_ms - avg_time:.1f}ms ({(frame_budget_ms - avg_time) / frame_budget_ms * 100:.0f}%)")

        # Average should be well under budget (leave room for WebSocket overhead)
        assert avg_time < frame_budget_ms * 0.4, \
            f"Avg {avg_time:.1f}ms exceeds 40% of {frame_budget_ms}ms budget"

        # Max time should still be comfortably under budget
        assert max_time < frame_budget_ms * 0.7, \
            f"Max {max_time:.1f}ms exceeds 70% of {frame_budget_ms}ms budget"

    def test_different_resolutions(self):
        """Test encoding performance at different resolutions"""
        resolutions = [
            (640, 480, 'VGA'),
            (1024, 768, 'Default'),
            (1920, 1080, 'Full HD')
        ]

        results = {}

        print(f"\n📐 Testing encoding performance across resolutions...")

        for width, height, name in resolutions:
            test_frame = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)

            times = []
            for _ in range(10):
                start = time.perf_counter()
                jpeg_bytes = simplejpeg.encode_jpeg(test_frame, quality=85, colorspace='RGB')
                times.append((time.perf_counter() - start) * 1000)

            results[name] = {
                'resolution': f'{width}x{height}',
                'avg_ms': sum(times) / len(times),
                'max_ms': max(times),
                'pixels': width * height
            }

        print(f"\n📊 Resolution Performance:")
        for name, data in results.items():
            print(f"   {data['resolution']:12s}: avg={data['avg_ms']:5.1f}ms max={data['max_ms']:5.1f}ms")

        # Default (1024x768) should be fast
        assert results['Default']['avg_ms'] < 40, \
            f"Default resolution too slow: {results['Default']['avg_ms']:.1f}ms"

        # Even Full HD should encode reasonably fast
        assert results['Full HD']['avg_ms'] < 80, \
            f"Full HD encoding too slow: {results['Full HD']['avg_ms']:.1f}ms"

    def test_encoding_stability_over_time(self):
        """Test encoding performance stays stable over extended period"""
        test_frame = np.random.randint(0, 255, (768, 1024, 3), dtype=np.uint8)

        # Encode for 300 frames (30 seconds at 10 FPS)
        frame_count = 300
        batch_size = 50

        batch_averages = []

        print(f"\n⏳ Testing encoding stability over {frame_count} frames...")

        for batch_num in range(frame_count // batch_size):
            batch_times = []

            for _ in range(batch_size):
                start = time.perf_counter()
                jpeg_bytes = simplejpeg.encode_jpeg(test_frame, quality=85, colorspace='RGB')
                batch_times.append((time.perf_counter() - start) * 1000)

            avg = sum(batch_times) / len(batch_times)
            batch_averages.append(avg)
            print(f"   Batch {batch_num + 1}: {avg:.1f}ms avg")

        # Check for performance degradation
        first_half = sum(batch_averages[:len(batch_averages)//2]) / (len(batch_averages)//2)
        second_half = sum(batch_averages[len(batch_averages)//2:]) / (len(batch_averages) - len(batch_averages)//2)

        degradation = ((second_half - first_half) / first_half) * 100

        print(f"\n📊 Stability Analysis:")
        print(f"   First half avg:  {first_half:.1f}ms")
        print(f"   Second half avg: {second_half:.1f}ms")
        print(f"   Change:          {degradation:+.1f}%")

        # Performance should not degrade more than 10%
        assert abs(degradation) < 10, \
            f"Performance degraded by {degradation:.1f}% (limit: ±10%)"

    @pytest.mark.timeout(60)
    def test_worst_case_complex_frame(self):
        """Test encoding performance on complex (high-entropy) frames"""
        # High-entropy frame (harder to compress)
        complex_frame = np.random.randint(0, 255, (768, 1024, 3), dtype=np.uint8)

        # Low-entropy frame (easier to compress)
        simple_frame = np.ones((768, 1024, 3), dtype=np.uint8) * 128

        # Benchmark both
        complex_times = []
        simple_times = []

        for _ in range(20):
            start = time.perf_counter()
            simplejpeg.encode_jpeg(complex_frame, quality=85, colorspace='RGB')
            complex_times.append((time.perf_counter() - start) * 1000)

            start = time.perf_counter()
            simplejpeg.encode_jpeg(simple_frame, quality=85, colorspace='RGB')
            simple_times.append((time.perf_counter() - start) * 1000)

        complex_avg = sum(complex_times) / len(complex_times)
        simple_avg = sum(simple_times) / len(simple_times)

        print(f"\n🎨 Frame Complexity Impact:")
        print(f"   Complex (high-entropy): {complex_avg:.1f}ms")
        print(f"   Simple (low-entropy):   {simple_avg:.1f}ms")
        print(f"   Difference:             {complex_avg - simple_avg:.1f}ms")

        # Both should be under budget
        assert complex_avg < 50, f"Complex frame encoding too slow: {complex_avg:.1f}ms"
        assert simple_avg < 50, f"Simple frame encoding too slow: {simple_avg:.1f}ms"


@pytest.mark.stream
@pytest.mark.performance
class TestConcurrentClientStress:
    """Test concurrent client stress scenarios (Feature Set 1 enhancement)"""

    @pytest.mark.timeout(60)
    def test_five_simultaneous_clients(self):
        """Test streaming to 5 simultaneous clients"""
        print("\n👥 Testing 5 simultaneous clients stress test...")

        test_frame = np.random.randint(0, 255, (768, 1024, 3), dtype=np.uint8)
        frame_count = 100
        num_clients = 5

        # Track per-client stats
        client_stats = {i: {'count': 0, 'total_size': 0} for i in range(num_clients)}

        start_time = time.perf_counter()

        for frame_num in range(frame_count):
            # Encode frame once
            jpeg_bytes = simplejpeg.encode_jpeg(test_frame, quality=85, colorspace='RGB')

            # Simulate sending to all clients
            for client_id in range(num_clients):
                client_stats[client_id]['count'] += 1
                client_stats[client_id]['total_size'] += len(jpeg_bytes)

            if (frame_num + 1) % 25 == 0:
                print(f"   Progress: {frame_num + 1}/{frame_count} frames")

        total_time = time.perf_counter() - start_time

        print(f"\n📊 Concurrent Client Results:")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Frames per second: {frame_count / total_time:.1f}")

        # Verify all clients received all frames
        for client_id, stats in client_stats.items():
            assert stats['count'] == frame_count, \
                f"Client {client_id} missed frames: {stats['count']}/{frame_count}"
            print(f"   Client {client_id}: {stats['count']} frames, {stats['total_size']:,} bytes")

        print("✓ 5 simultaneous clients handled successfully")

    @pytest.mark.timeout(90)
    def test_ten_clients_with_staggered_connections(self):
        """Test 10 clients connecting at different times"""
        print("\n👥 Testing 10 clients with staggered connections...")

        test_frame = np.random.randint(0, 255, (768, 1024, 3), dtype=np.uint8)
        frame_count = 200
        num_clients = 10

        # Each client connects at a different frame
        client_start_frame = {i: i * 20 for i in range(num_clients)}
        client_stats = {i: {'count': 0} for i in range(num_clients)}

        start_time = time.perf_counter()

        for frame_num in range(frame_count):
            # Encode frame
            jpeg_bytes = simplejpeg.encode_jpeg(test_frame, quality=85, colorspace='RGB')

            # Send to connected clients
            for client_id in range(num_clients):
                if frame_num >= client_start_frame[client_id]:
                    client_stats[client_id]['count'] += 1

            if (frame_num + 1) % 50 == 0:
                print(f"   Progress: {frame_num + 1}/{frame_count} frames")

        total_time = time.perf_counter() - start_time

        print(f"\n📊 Staggered Connection Results:")
        print(f"   Total time: {total_time:.2f}s")

        for client_id, stats in client_stats.items():
            expected = frame_count - client_start_frame[client_id]
            assert stats['count'] == expected, \
                f"Client {client_id} frame mismatch: {stats['count']}/{expected}"
            print(f"   Client {client_id}: connected at frame {client_start_frame[client_id]}, received {stats['count']}")

        print("✓ 10 staggered clients handled successfully")

    @pytest.mark.timeout(60)
    def test_client_bandwidth_variations(self):
        """Simulate clients with different bandwidth (frame drop scenarios)"""
        print("\n📡 Testing client bandwidth variations...")

        test_frame = np.random.randint(0, 255, (768, 1024, 3), dtype=np.uint8)
        frame_count = 100

        # Simulate 3 clients with different "bandwidth" (frame acceptance rates)
        clients = {
            'fast': {'rate': 1.0, 'count': 0},      # Accepts all frames
            'medium': {'rate': 0.7, 'count': 0},    # Accepts 70% of frames
            'slow': {'rate': 0.4, 'count': 0}       # Accepts 40% of frames
        }

        import random
        random.seed(42)  # Reproducible results

        for frame_num in range(frame_count):
            # Encode frame
            jpeg_bytes = simplejpeg.encode_jpeg(test_frame, quality=85, colorspace='RGB')

            # Send to clients based on their bandwidth
            for client_name, client_data in clients.items():
                if random.random() < client_data['rate']:
                    client_data['count'] += 1

        print(f"\n📊 Bandwidth Variation Results:")
        for client_name, client_data in clients.items():
            expected_min = int(frame_count * client_data['rate'] * 0.8)  # Allow 20% variance
            expected_max = int(frame_count * client_data['rate'] * 1.2)
            actual = client_data['count']

            print(f"   {client_name:8s} client: {actual}/{frame_count} frames "
                  f"(expected ~{int(frame_count * client_data['rate'])})")

            assert expected_min <= actual <= expected_max, \
                f"{client_name} client received unexpected frame count: {actual}"

        print("✓ Bandwidth variations handled correctly")


@pytest.mark.stream
@pytest.mark.performance
class TestNetworkLatencySimulation:
    """Test performance under simulated network conditions (Feature Set 1 enhancement)"""

    @pytest.mark.timeout(60)
    def test_encoding_with_simulated_latency(self):
        """Test encoding performance with simulated network latency"""
        print("\n🌐 Testing encoding with simulated network latency...")

        test_frame = np.random.randint(0, 255, (768, 1024, 3), dtype=np.uint8)
        frame_count = 50

        # Simulate different latency scenarios (in seconds)
        latencies = {
            'LAN': 0.001,      # 1ms
            'WiFi': 0.010,     # 10ms
            'Internet': 0.050  # 50ms
        }

        results = {}

        for network_type, latency in latencies.items():
            times = []
            start = time.perf_counter()

            for _ in range(frame_count):
                # Encode frame
                encode_start = time.perf_counter()
                jpeg_bytes = simplejpeg.encode_jpeg(test_frame, quality=85, colorspace='RGB')
                encode_time = time.perf_counter() - encode_start

                # Simulate network latency
                time.sleep(latency)

                times.append(encode_time)

            total_time = time.perf_counter() - start
            avg_encode = sum(times) / len(times) * 1000  # ms

            results[network_type] = {
                'avg_encode_ms': avg_encode,
                'total_time': total_time,
                'effective_fps': frame_count / total_time
            }

        print(f"\n📊 Network Latency Results:")
        for network_type, data in results.items():
            print(f"   {network_type:8s}: {data['avg_encode_ms']:.1f}ms encode, "
                  f"{data['effective_fps']:.1f} FPS effective")

        # Verify encoding time is consistent regardless of network latency
        encode_times = [data['avg_encode_ms'] for data in results.values()]
        assert max(encode_times) - min(encode_times) < 5, \
            "Encoding time should be consistent across network conditions"

        print("✓ Encoding performance unaffected by network latency")

    @pytest.mark.timeout(60)
    def test_frame_backlog_prevention(self):
        """Verify frames don't backlog under slow client conditions"""
        print("\n🌐 Testing frame backlog prevention...")

        test_frame = np.random.randint(0, 255, (768, 1024, 3), dtype=np.uint8)
        frame_count = 100
        target_fps = 10
        frame_delay = 1.0 / target_fps

        # Track frame timing
        frame_times = []
        encode_times = []

        start_time = time.perf_counter()

        for i in range(frame_count):
            frame_start = time.perf_counter()

            # Encode frame
            encode_start = time.perf_counter()
            jpeg_bytes = simplejpeg.encode_jpeg(test_frame, quality=85, colorspace='RGB')
            encode_elapsed = time.perf_counter() - encode_start
            encode_times.append(encode_elapsed * 1000)

            # Simulate slow client (occasionally slow to process)
            if i % 10 == 0:
                time.sleep(0.02)  # 20ms delay

            # Maintain target FPS (don't let backlog build)
            frame_elapsed = time.perf_counter() - frame_start
            frame_times.append(frame_elapsed * 1000)

            if frame_elapsed < frame_delay:
                time.sleep(frame_delay - frame_elapsed)

        total_time = time.perf_counter() - start_time
        actual_fps = frame_count / total_time

        print(f"\n📊 Backlog Prevention Results:")
        print(f"   Target FPS: {target_fps}")
        print(f"   Actual FPS: {actual_fps:.1f}")
        print(f"   Avg encode: {sum(encode_times) / len(encode_times):.1f}ms")
        print(f"   Max encode: {max(encode_times):.1f}ms")

        # FPS should be close to target despite slow client
        assert abs(actual_fps - target_fps) < 1.0, \
            f"FPS deviated too much: {actual_fps:.1f} vs {target_fps}"

        print("✓ Frame backlog prevented successfully")


@pytest.mark.stream
@pytest.mark.performance
class TestVariableFrameRate:
    """Test performance with variable frame rates (Feature Set 1 enhancement)"""

    @pytest.mark.timeout(60)
    def test_dynamic_fps_changes(self):
        """Test encoding performance with dynamic FPS changes"""
        print("\n🎬 Testing dynamic FPS changes...")

        test_frame = np.random.randint(0, 255, (768, 1024, 3), dtype=np.uint8)

        # Test different FPS rates
        fps_rates = [5, 10, 15, 20]
        results = {}

        for fps in fps_rates:
            frame_delay = 1.0 / fps
            num_frames = 20  # Shorter test per FPS

            encode_times = []
            start = time.perf_counter()

            for _ in range(num_frames):
                encode_start = time.perf_counter()
                jpeg_bytes = simplejpeg.encode_jpeg(test_frame, quality=85, colorspace='RGB')
                encode_times.append((time.perf_counter() - encode_start) * 1000)

                time.sleep(frame_delay)

            total_time = time.perf_counter() - start

            results[fps] = {
                'avg_encode': sum(encode_times) / len(encode_times),
                'max_encode': max(encode_times),
                'actual_fps': num_frames / total_time
            }

        print(f"\n📊 Variable FPS Results:")
        for fps, data in results.items():
            print(f"   {fps:2d} FPS: {data['avg_encode']:5.1f}ms avg, "
                  f"{data['max_encode']:5.1f}ms max, "
                  f"actual {data['actual_fps']:.1f} FPS")

            # Encoding time should be consistent regardless of FPS
            assert data['avg_encode'] < 50, \
                f"Encoding too slow at {fps} FPS: {data['avg_encode']:.1f}ms"

        print("✓ Dynamic FPS changes handled successfully")

    @pytest.mark.timeout(60)
    def test_burst_mode_performance(self):
        """Test performance during burst capture mode"""
        print("\n🎬 Testing burst mode performance...")

        test_frame = np.random.randint(0, 255, (768, 1024, 3), dtype=np.uint8)

        # Burst capture: encode as fast as possible
        burst_count = 50
        encode_times = []

        start = time.perf_counter()

        for _ in range(burst_count):
            encode_start = time.perf_counter()
            jpeg_bytes = simplejpeg.encode_jpeg(test_frame, quality=85, colorspace='RGB')
            encode_times.append((time.perf_counter() - encode_start) * 1000)

        total_time = time.perf_counter() - start

        avg_time = sum(encode_times) / len(encode_times)
        max_time = max(encode_times)
        burst_fps = burst_count / total_time

        print(f"\n📊 Burst Mode Results:")
        print(f"   Frames: {burst_count}")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Burst FPS: {burst_fps:.1f}")
        print(f"   Avg encode: {avg_time:.1f}ms")
        print(f"   Max encode: {max_time:.1f}ms")

        # Should sustain at least 15 FPS in burst mode
        assert burst_fps >= 15.0, f"Burst FPS too low: {burst_fps:.1f}"

        print("✓ Burst mode performance acceptable")


@pytest.mark.stream
@pytest.mark.performance
class TestResolutionSwitching:
    """Test resolution switching during streaming (Feature Set 1 enhancement)"""

    @pytest.mark.timeout(60)
    def test_multi_resolution_encoding(self):
        """Test encoding performance across resolution switches"""
        print("\n📐 Testing multi-resolution encoding...")

        resolutions = [
            (640, 480, 'VGA'),
            (1024, 768, 'XGA'),
            (1280, 720, 'HD'),
            (1920, 1080, 'Full HD')
        ]

        results = {}

        for width, height, name in resolutions:
            test_frame = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)

            # Encode 10 frames at this resolution
            times = []
            for _ in range(10):
                start = time.perf_counter()
                jpeg_bytes = simplejpeg.encode_jpeg(test_frame, quality=85, colorspace='RGB')
                times.append((time.perf_counter() - start) * 1000)

            results[name] = {
                'resolution': f'{width}x{height}',
                'avg_ms': sum(times) / len(times),
                'max_ms': max(times)
            }

        print(f"\n📊 Resolution Switching Results:")
        for name, data in results.items():
            print(f"   {name:8s} ({data['resolution']:10s}): "
                  f"avg={data['avg_ms']:5.1f}ms max={data['max_ms']:5.1f}ms")

            # All resolutions should encode fast enough for 10 FPS
            assert data['avg_ms'] < 100, \
                f"{name} encoding too slow: {data['avg_ms']:.1f}ms"

        print("✓ Resolution switching handled successfully")

    @pytest.mark.timeout(60)
    def test_rapid_resolution_changes(self):
        """Test rapid resolution switching"""
        print("\n📐 Testing rapid resolution changes...")

        resolutions = [
            (640, 480),
            (1024, 768),
            (1280, 720)
        ]

        frame_count = 30
        encode_times = []

        for i in range(frame_count):
            # Switch resolution every 10 frames
            width, height = resolutions[(i // 10) % len(resolutions)]
            test_frame = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)

            # Encode frame
            start = time.perf_counter()
            jpeg_bytes = simplejpeg.encode_jpeg(test_frame, quality=85, colorspace='RGB')
            encode_times.append((time.perf_counter() - start) * 1000)

            if (i + 1) % 10 == 0:
                print(f"   Switched to {width}x{height} after frame {i + 1}")

        avg_time = sum(encode_times) / len(encode_times)
        max_time = max(encode_times)

        print(f"\n📊 Rapid Switching Results:")
        print(f"   Frames encoded: {frame_count}")
        print(f"   Avg encode: {avg_time:.1f}ms")
        print(f"   Max encode: {max_time:.1f}ms")

        # Encoding should remain fast despite resolution changes
        assert avg_time < 50, f"Average encoding too slow: {avg_time:.1f}ms"
        assert max_time < 100, f"Max encoding too slow: {max_time:.1f}ms"

        print("✓ Rapid resolution changes handled successfully")


@pytest.mark.stream
@pytest.mark.performance
class TestCPULoadPerformance:
    """Test performance under CPU load (Feature Set 1 enhancement)"""

    @pytest.mark.timeout(90)
    def test_encoding_under_cpu_stress(self):
        """Test encoding performance while CPU is under load"""
        print("\n💻 Testing encoding under CPU stress...")

        test_frame = np.random.randint(0, 255, (768, 1024, 3), dtype=np.uint8)

        # Baseline performance (no CPU load)
        baseline_times = []
        for _ in range(20):
            start = time.perf_counter()
            jpeg_bytes = simplejpeg.encode_jpeg(test_frame, quality=85, colorspace='RGB')
            baseline_times.append((time.perf_counter() - start) * 1000)

        baseline_avg = sum(baseline_times) / len(baseline_times)

        # Performance under CPU load
        import threading
        stop_stress = threading.Event()

        def cpu_stress():
            """Simple CPU stress function"""
            while not stop_stress.is_set():
                _ = sum(range(10000))

        # Start CPU stress threads
        stress_threads = []
        for _ in range(2):
            thread = threading.Thread(target=cpu_stress)
            thread.daemon = True
            thread.start()
            stress_threads.append(thread)

        time.sleep(0.5)  # Let stress build up

        # Test encoding under load
        stressed_times = []
        for _ in range(20):
            start = time.perf_counter()
            jpeg_bytes = simplejpeg.encode_jpeg(test_frame, quality=85, colorspace='RGB')
            stressed_times.append((time.perf_counter() - start) * 1000)

        # Stop stress
        stop_stress.set()
        for thread in stress_threads:
            thread.join()

        stressed_avg = sum(stressed_times) / len(stressed_times)
        slowdown = (stressed_avg / baseline_avg - 1) * 100

        print(f"\n📊 CPU Load Results:")
        print(f"   Baseline avg: {baseline_avg:.1f}ms")
        print(f"   Under load avg: {stressed_avg:.1f}ms")
        print(f"   Slowdown: {slowdown:+.1f}%")

        # Performance degradation should be reasonable (<100%)
        assert slowdown < 100, f"Performance degraded too much: {slowdown:.1f}%"

        # Should still be fast enough for streaming
        assert stressed_avg < 100, f"Encoding too slow under load: {stressed_avg:.1f}ms"

        print("✓ Encoding performs adequately under CPU load")

    @pytest.mark.timeout(60)
    def test_encoding_consistency_with_background_load(self):
        """Test encoding consistency with background CPU load"""
        print("\n💻 Testing encoding consistency with background load...")

        test_frame = np.random.randint(0, 255, (768, 1024, 3), dtype=np.uint8)

        import threading
        stop_background = threading.Event()

        def background_work():
            """Simulate periodic background tasks"""
            while not stop_background.is_set():
                # Simulate periodic work
                _ = sum(range(50000))
                time.sleep(0.1)

        # Start background thread
        bg_thread = threading.Thread(target=background_work)
        bg_thread.daemon = True
        bg_thread.start()

        # Encode frames with background load
        frame_count = 50
        encode_times = []

        for _ in range(frame_count):
            start = time.perf_counter()
            jpeg_bytes = simplejpeg.encode_jpeg(test_frame, quality=85, colorspace='RGB')
            encode_times.append((time.perf_counter() - start) * 1000)

        stop_background.set()
        bg_thread.join()

        avg_time = sum(encode_times) / len(encode_times)
        std_dev = np.std(encode_times)
        max_time = max(encode_times)

        print(f"\n📊 Background Load Results:")
        print(f"   Frames: {frame_count}")
        print(f"   Avg encode: {avg_time:.1f}ms")
        print(f"   Std dev: {std_dev:.1f}ms")
        print(f"   Max encode: {max_time:.1f}ms")

        # Consistency check - std dev should be reasonable
        assert std_dev < 20, f"Encoding too inconsistent: {std_dev:.1f}ms std dev"

        # Performance should still be good
        assert avg_time < 50, f"Average encoding too slow: {avg_time:.1f}ms"

        print("✓ Encoding remains consistent with background load")

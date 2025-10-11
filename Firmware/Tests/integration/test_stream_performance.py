"""
Integration tests for streaming performance

RUN ON RASPBERRY PI ONLY - tests sustained streaming performance
"""
import pytest
import time
import numpy as np
import simplejpeg
import base64


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

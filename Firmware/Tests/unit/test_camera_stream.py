"""
Unit tests for camera streaming module

RUN ON RASPBERRY PI ONLY - requires simplejpeg and numpy
"""
import pytest
import numpy as np
import time
import io
import base64
import simplejpeg
from PIL import Image


class TestSimpleJPEGEncoding:
    """Test simplejpeg encoding performance vs PIL"""

    def test_simplejpeg_available(self):
        """Verify simplejpeg is installed"""
        import simplejpeg
        assert simplejpeg.__version__ == '1.8.1'
        print(f"\n✓ simplejpeg version: {simplejpeg.__version__}")

    def test_encoding_speed_comparison(self):
        """Compare simplejpeg vs PIL encoding speed"""
        # Create realistic test frame (1024x768 RGB)
        test_frame = np.random.randint(0, 255, (768, 1024, 3), dtype=np.uint8)

        # Benchmark simplejpeg (10 iterations for stability)
        times_simplejpeg = []
        for _ in range(10):
            start = time.perf_counter()
            jpeg_bytes = simplejpeg.encode_jpeg(test_frame, quality=85, colorspace='RGB')
            times_simplejpeg.append(time.perf_counter() - start)
        avg_simplejpeg = sum(times_simplejpeg) / len(times_simplejpeg) * 1000  # ms

        # Benchmark PIL (old method with optimize=True)
        times_pil = []
        for _ in range(10):
            start = time.perf_counter()
            img = Image.fromarray(test_frame)
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=85, optimize=True)
            buffer.seek(0)
            pil_bytes = buffer.read()
            times_pil.append(time.perf_counter() - start)
        avg_pil = sum(times_pil) / len(times_pil) * 1000  # ms

        speedup = avg_pil / avg_simplejpeg

        print(f"\n📊 Encoding Performance (1024x768, Q=85):")
        print(f"   PIL (optimize=True): {avg_pil:.1f}ms")
        print(f"   simplejpeg:          {avg_simplejpeg:.1f}ms")
        print(f"   Speedup:             {speedup:.1f}x")

        # Verify at least 3x speedup
        assert speedup >= 3.0, f"Expected ≥3x speedup, got {speedup:.1f}x"

    def test_encoding_quality_similar(self):
        """Verify simplejpeg output quality similar to PIL"""
        test_frame = np.random.randint(0, 255, (768, 1024, 3), dtype=np.uint8)

        # Encode with both methods
        jpeg_simplejpeg = simplejpeg.encode_jpeg(test_frame, quality=85, colorspace='RGB')

        img = Image.fromarray(test_frame)
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=85)
        buffer.seek(0)
        jpeg_pil = buffer.read()

        # File sizes should be within 15% (both are quality=85)
        size_ratio = len(jpeg_simplejpeg) / len(jpeg_pil)
        print(f"\n📏 Size comparison:")
        print(f"   simplejpeg: {len(jpeg_simplejpeg):,} bytes")
        print(f"   PIL:        {len(jpeg_pil):,} bytes")
        print(f"   Ratio:      {size_ratio:.2f}")

        assert 0.85 <= size_ratio <= 1.15, f"Size ratio {size_ratio:.2f} outside expected range [0.85, 1.15]"

    def test_encoding_time_under_budget(self):
        """Verify single frame encodes in <50ms (for 10 FPS @ 100ms budget)"""
        test_frame = np.random.randint(0, 255, (768, 1024, 3), dtype=np.uint8)

        start = time.perf_counter()
        jpeg_bytes = simplejpeg.encode_jpeg(test_frame, quality=85, colorspace='RGB')
        img_base64 = base64.b64encode(jpeg_bytes).decode('utf-8')
        elapsed_ms = (time.perf_counter() - start) * 1000

        print(f"\n⏱️  Single frame encoding: {elapsed_ms:.1f}ms")
        print(f"   Frame budget (10 FPS): 100ms")
        print(f"   Encoding uses:         {elapsed_ms / 100 * 100:.1f}% of budget")

        assert elapsed_ms < 50, f"Encoding took {elapsed_ms:.1f}ms (target: <50ms for WebSocket overhead)"


class TestQualitySettings:
    """Test JPEG quality range"""

    def test_quality_range_50_to_100(self):
        """Test encoding across quality range"""
        test_frame = np.random.randint(0, 255, (768, 1024, 3), dtype=np.uint8)

        results = {}
        for quality in [50, 70, 85, 95, 100]:
            start = time.perf_counter()
            jpeg_bytes = simplejpeg.encode_jpeg(test_frame, quality=quality, colorspace='RGB')
            elapsed_ms = (time.perf_counter() - start) * 1000

            results[quality] = {
                'size': len(jpeg_bytes),
                'time_ms': elapsed_ms
            }

        print(f"\n📊 Quality vs Performance:")
        for q, data in results.items():
            print(f"   Q{q:3d}: {data['size']:>7,} bytes, {data['time_ms']:5.1f}ms")

        # Higher quality = larger size
        assert results[50]['size'] < results[85]['size'] < results[100]['size'], \
            "Higher quality should produce larger file sizes"

        # Even Q=100 should be reasonable (<100ms)
        assert results[100]['time_ms'] < 100, \
            f"Q=100 encoding too slow: {results[100]['time_ms']:.1f}ms"

    def test_quality_85_is_sweet_spot(self):
        """Verify Q=85 provides good balance"""
        test_frame = np.random.randint(0, 255, (768, 1024, 3), dtype=np.uint8)

        # Compare Q=85 vs Q=95 (old default)
        q85_bytes = simplejpeg.encode_jpeg(test_frame, quality=85, colorspace='RGB')
        q95_bytes = simplejpeg.encode_jpeg(test_frame, quality=95, colorspace='RGB')

        size_reduction = (1 - len(q85_bytes) / len(q95_bytes)) * 100

        print(f"\n💡 Quality 85 vs 95 comparison:")
        print(f"   Q=85: {len(q85_bytes):,} bytes")
        print(f"   Q=95: {len(q95_bytes):,} bytes")
        print(f"   Size reduction: {size_reduction:.1f}%")

        # Q=85 should be at least 20% smaller than Q=95
        assert size_reduction >= 20, \
            f"Expected ≥20% size reduction, got {size_reduction:.1f}%"

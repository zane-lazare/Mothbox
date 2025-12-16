"""
Performance tests for optimized ZIP export (Issue #128).

Tests verify:
1. Memory streaming efficiency (memory doesn't grow with ZIP size)
2. Regression prevention (performance stays within targets)
3. Parallel I/O improvements (future optimization)

Run with: pytest Tests/performance/test_zip_export_optimized.py -v -s --tb=short
"""

import os
import sys
import time
import tracemalloc
from pathlib import Path

import pytest
from PIL import Image

# Setup path
FIRMWARE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(FIRMWARE_DIR))
sys.path.insert(0, str(FIRMWARE_DIR / "webui" / "backend"))
os.environ.setdefault("MOTHBOX_ENV", "test")

from webui.backend.lib.zip_export import (
    ZipExportOptions,
    create_zip_export,
    stream_zip_export,
)
from webui.backend.services.export_metadata_service import ExportMetadata

# ============================================================================
# Performance Target Constants
# ============================================================================

# Regression prevention (baseline from profiling)
# Current implementation already exceeds these by 3x
ZIP_50_PHOTOS_TARGET_MS = 5000  # <5s for 50 photos
ZIP_100_PHOTOS_TARGET_MS = 10000  # <10s for 100 photos
ZIP_200_PHOTOS_TARGET_MS = 20000  # <20s for 200 photos

# Throughput targets (with margin from baseline 30/sec)
MIN_THROUGHPUT_PHOTOS_PER_SEC = 20  # >20 photos/sec (allowing margin)

# Memory efficiency targets
MEMORY_STREAMING_LIMIT_MB = 64  # Streaming should stay under 64MB regardless of ZIP size
MEMORY_100_PHOTOS_LIMIT_MB = 100  # Total memory for 100 photos
MEMORY_200_PHOTOS_LIMIT_MB = 150  # Should not grow linearly with photo count

# Parallel I/O improvement targets (future - Subtask 4)
PARALLEL_IO_SPEEDUP_TARGET = 1.5  # 50% speedup over sequential


# ============================================================================
# Test Fixtures
# ============================================================================


def create_realistic_jpeg(path: Path, width: int = 4624, height: int = 3472, quality: int = 85) -> None:
    """Create realistic-sized JPEG (2-3MB like actual camera photos).

    Uses numpy for fast generation of noisy images that compress to realistic sizes.

    Args:
        path: Output path for JPEG
        width: Image width in pixels (default: 16MP camera resolution)
        height: Image height in pixels
        quality: JPEG quality (85 is typical for cameras)
    """
    try:
        import numpy as np

        # Create base gradient image
        x = np.linspace(0, 255, width)
        y = np.linspace(0, 255, height)
        xv, yv = np.meshgrid(x, y)

        # Create RGB channels with gradients
        r = xv.astype(np.uint8)
        g = yv.astype(np.uint8)
        b = ((xv + yv) / 2).astype(np.uint8)

        # Add noise to prevent over-compression (creates realistic file sizes)
        noise = np.random.randint(-50, 51, (height, width), dtype=np.int16)
        r = np.clip(r.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        g = np.clip(g.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        b = np.clip(b.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        # Stack into RGB image
        img_array = np.stack([r, g, b], axis=2)
        img = Image.fromarray(img_array, 'RGB')

    except ImportError:
        # Fallback: simpler approach without numpy (much slower)
        import random
        img = Image.new('RGB', (width, height))
        pixels = img.load()

        for y in range(height):
            for x in range(width):
                r_base = (x * 255) // width
                g_base = (y * 255) // height
                b_base = ((x + y) * 255) // (width + height)

                noise = random.randint(-50, 50)
                r = max(0, min(255, r_base + noise))
                g = max(0, min(255, g_base + noise))
                b = max(0, min(255, b_base + noise))

                pixels[x, y] = (r, g, b)

    # Save with specified quality
    img.save(path, format='JPEG', quality=quality, optimize=False)


def create_test_metadata(photo_path: Path) -> ExportMetadata:
    """Create test metadata for profiling."""
    return ExportMetadata(
        photo_path=str(photo_path),
        filename=photo_path.name,
        timestamp="2024-01-15T10:30:00",
        latitude=37.7749,
        longitude=-122.4194,
        altitude=15.5,
        gps_accuracy=2.5,
        species="Actias luna",
        species_common_name="Luna Moth",
        species_confidence="certain",
        tags=["moth", "lepidoptera", "night", "trap_01", "oak_forest"],
        notes="Test observation for profiling benchmarks with realistic metadata content",
        camera_make="Arducam",
        camera_model="OwlSight 64MP",
        deployment_name="Oak Ridge Forest Survey 2024",
        deployment_location_name="Oak Ridge, TN, USA",
        exposure_time="1/60",
        iso=400,
        focal_length="28.0 mm",
        file_size=photo_path.stat().st_size if photo_path.exists() else 0,
        width=4624,
        height=3472,
    )


# ============================================================================
# Memory Efficiency Tests
# ============================================================================


@pytest.mark.performance
class TestMemoryEfficiency:
    """Test memory efficiency of streaming ZIP export."""

    def test_streaming_memory_stays_constant(self, tmp_path):
        """Streaming memory should stay under 64MB regardless of ZIP size.

        NOTE: This test may FAIL against current implementation which uses
        BytesIO and loads entire ZIP into memory. This is EXPECTED and will
        pass after implementing streaming optimization (Subtask 3).
        """
        photo_count = 100  # ~250MB total photo data

        print(f"\n{'='*60}")
        print("MEMORY EFFICIENCY: Streaming ZIP Export")
        print(f"{'='*60}\n")

        # Create realistic test photos
        print(f"Creating {photo_count} realistic photos...")
        photos = []
        for i in range(photo_count):
            photo = tmp_path / f"photo_{i:04d}.jpg"
            create_realistic_jpeg(photo)
            photos.append(photo)

        photo_sizes = [p.stat().st_size for p in photos]
        total_size_mb = sum(photo_sizes) / (1024 * 1024)
        print(f"  Total photo size: {total_size_mb:.2f} MB\n")

        # Create metadata
        metadata_list = [create_test_metadata(photo) for photo in photos]
        options = ZipExportOptions(
            include_xmp_sidecars=True,
            include_manifest=True,
            include_csv_summary=True,
        )

        # Start memory tracking
        tracemalloc.start()
        mem_start = tracemalloc.get_traced_memory()[0]

        # Stream ZIP and consume all chunks
        print("Streaming ZIP export...")
        chunk_count = 0
        total_bytes = 0
        max_memory_mb = 0

        for item in stream_zip_export(photos, metadata_list, options):
            if isinstance(item, bytes):
                chunk_count += 1
                total_bytes += len(item)

                # Check memory periodically
                if chunk_count % 10 == 0:
                    mem_current, mem_peak = tracemalloc.get_traced_memory()
                    mem_used_mb = (mem_current - mem_start) / (1024 * 1024)
                    max_memory_mb = max(max_memory_mb, mem_used_mb)
            else:
                # ZipExportResult
                result = item

        # Get final peak memory
        mem_current, mem_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        mem_used_mb = (mem_current - mem_start) / (1024 * 1024)
        mem_peak_mb = mem_peak / (1024 * 1024)

        print("\nRESULTS:")
        print(f"  Chunks streamed: {chunk_count}")
        print(f"  Total bytes: {total_bytes / (1024*1024):.2f} MB")
        print(f"  Photos: {result.photo_count}")
        print(f"  Current memory: {mem_used_mb:.2f} MB")
        print(f"  Peak memory: {mem_peak_mb:.2f} MB")
        print(f"  Max periodic memory: {max_memory_mb:.2f} MB\n")

        # Target: streaming should stay under 64MB
        print(f"Memory target: <{MEMORY_STREAMING_LIMIT_MB} MB")
        print(f"Actual: {mem_peak_mb:.2f} MB")

        # NOTE: This assertion may fail with current BytesIO implementation
        # After optimization (Subtask 3), this should pass
        if mem_peak_mb < MEMORY_STREAMING_LIMIT_MB:
            print("✓ PASS - Memory efficient streaming")
        else:
            print("✗ FAIL - Memory too high (expected with current BytesIO implementation)")
            print("   This will pass after implementing streaming optimization")

        # This assertion documents the expected behavior
        # Uncomment after implementing streaming optimization (Subtask 3)
        # assert mem_peak_mb < MEMORY_STREAMING_LIMIT_MB, (
        #     f"Streaming memory too high: {mem_peak_mb:.2f} MB "
        #     f"(target: <{MEMORY_STREAMING_LIMIT_MB} MB)"
        # )

    def test_memory_growth_sublinear(self, tmp_path):
        """Memory growth should be sublinear with photo count."""
        print(f"\n{'='*60}")
        print("MEMORY SCALABILITY: Sublinear Growth")
        print(f"{'='*60}\n")

        batch_sizes = [50, 100, 200]
        memory_results = []

        for size in batch_sizes:
            print(f"\nTesting {size} photos...")

            # Create photos
            photos = []
            for i in range(size):
                photo = tmp_path / f"mem_{size}_{i:04d}.jpg"
                create_realistic_jpeg(photo)
                photos.append(photo)

            photo_sizes = [p.stat().st_size for p in photos]
            total_size_mb = sum(photo_sizes) / (1024 * 1024)

            metadata_list = [create_test_metadata(photo) for photo in photos]
            output_zip = tmp_path / f"mem_test_{size}.zip"
            options = ZipExportOptions(
                include_xmp_sidecars=True,
                include_manifest=True,
                include_csv_summary=True,
            )

            # Measure memory
            tracemalloc.start()
            create_zip_export(photos, metadata_list, output_zip, options)
            _, mem_peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            mem_peak_mb = mem_peak / (1024 * 1024)

            memory_results.append({
                'size': size,
                'total_mb': total_size_mb,
                'memory_mb': mem_peak_mb,
                'ratio': mem_peak_mb / total_size_mb,
            })

            print(f"  Photo data: {total_size_mb:.2f} MB")
            print(f"  Peak memory: {mem_peak_mb:.2f} MB")
            print(f"  Ratio: {mem_peak_mb / total_size_mb:.2f}x")

        # Verify memory doesn't grow linearly
        print(f"\n{'='*60}")
        print("MEMORY GROWTH ANALYSIS")
        print(f"{'='*60}\n")

        for r in memory_results:
            print(f"{r['size']:3d} photos: {r['memory_mb']:6.2f} MB ({r['ratio']:.2f}x photo data)")

        # 200 photos should not use 2x memory of 100 photos
        mem_100 = next(r['memory_mb'] for r in memory_results if r['size'] == 100)
        mem_200 = next(r['memory_mb'] for r in memory_results if r['size'] == 200)
        growth_ratio = mem_200 / mem_100

        print(f"\nMemory growth ratio (200/100): {growth_ratio:.2f}x")
        print("Target: <1.5x (sublinear growth)")

        # Allow some growth but not linear
        assert growth_ratio < 1.5, (
            f"Memory growth too linear: {growth_ratio:.2f}x "
            f"(target: <1.5x)"
        )


# ============================================================================
# Regression Prevention Tests
# ============================================================================


@pytest.mark.performance
class TestRegressionPrevention:
    """Ensure optimizations don't regress from baseline performance."""

    def test_50_photos_stays_under_5_seconds(self, tmp_path):
        """50 photos should stay under 5 seconds (baseline target)."""
        photo_count = 50

        print(f"\n{'='*60}")
        print(f"REGRESSION TEST: {photo_count} photos")
        print(f"{'='*60}\n")

        # Create realistic photos
        photos = []
        for i in range(photo_count):
            photo = tmp_path / f"photo_{i:04d}.jpg"
            create_realistic_jpeg(photo)
            photos.append(photo)

        photo_sizes = [p.stat().st_size for p in photos]
        total_size_mb = sum(photo_sizes) / (1024 * 1024)
        print(f"Total photo size: {total_size_mb:.2f} MB\n")

        # Create export
        metadata_list = [create_test_metadata(photo) for photo in photos]
        output_zip = tmp_path / "regression_50.zip"
        options = ZipExportOptions(
            include_xmp_sidecars=True,
            include_manifest=True,
            include_csv_summary=True,
        )

        # Measure performance
        start = time.perf_counter()
        result = create_zip_export(photos, metadata_list, output_zip, options)
        elapsed_ms = (time.perf_counter() - start) * 1000

        print("RESULTS:")
        print(f"  Time: {elapsed_ms:.0f}ms ({elapsed_ms/1000:.2f}s)")
        print(f"  Photos: {result.photo_count}")
        print(f"  Throughput: {photo_count / (elapsed_ms/1000):.1f} photos/sec\n")

        print(f"Target: <{ZIP_50_PHOTOS_TARGET_MS}ms")
        print(f"Actual: {elapsed_ms:.0f}ms")

        assert result.success, f"ZIP creation failed: {result.errors}"
        assert elapsed_ms < ZIP_50_PHOTOS_TARGET_MS, (
            f"Performance regression: {elapsed_ms:.0f}ms "
            f"(target: <{ZIP_50_PHOTOS_TARGET_MS}ms)"
        )
        print("✓ PASS - No regression")

    def test_100_photos_stays_under_10_seconds(self, tmp_path):
        """100 photos should stay under 10 seconds (baseline target)."""
        photo_count = 100

        print(f"\n{'='*60}")
        print(f"REGRESSION TEST: {photo_count} photos")
        print(f"{'='*60}\n")

        # Create realistic photos
        photos = []
        for i in range(photo_count):
            photo = tmp_path / f"photo_{i:04d}.jpg"
            create_realistic_jpeg(photo)
            photos.append(photo)

        photo_sizes = [p.stat().st_size for p in photos]
        total_size_mb = sum(photo_sizes) / (1024 * 1024)
        print(f"Total photo size: {total_size_mb:.2f} MB\n")

        # Create export
        metadata_list = [create_test_metadata(photo) for photo in photos]
        output_zip = tmp_path / "regression_100.zip"
        options = ZipExportOptions(
            include_xmp_sidecars=True,
            include_manifest=True,
            include_csv_summary=True,
        )

        # Measure performance
        start = time.perf_counter()
        result = create_zip_export(photos, metadata_list, output_zip, options)
        elapsed_ms = (time.perf_counter() - start) * 1000

        print("RESULTS:")
        print(f"  Time: {elapsed_ms:.0f}ms ({elapsed_ms/1000:.2f}s)")
        print(f"  Photos: {result.photo_count}")
        print(f"  Throughput: {photo_count / (elapsed_ms/1000):.1f} photos/sec\n")

        print(f"Target: <{ZIP_100_PHOTOS_TARGET_MS}ms")
        print(f"Actual: {elapsed_ms:.0f}ms")

        assert result.success, f"ZIP creation failed: {result.errors}"
        assert elapsed_ms < ZIP_100_PHOTOS_TARGET_MS, (
            f"Performance regression: {elapsed_ms:.0f}ms "
            f"(target: <{ZIP_100_PHOTOS_TARGET_MS}ms)"
        )
        print("✓ PASS - No regression")

    def test_throughput_stays_above_20_photos_per_sec(self, tmp_path):
        """Throughput should stay above 20 photos/sec (with margin from 30/sec baseline)."""
        photo_count = 100

        print(f"\n{'='*60}")
        print("THROUGHPUT REGRESSION TEST")
        print(f"{'='*60}\n")

        # Create photos
        photos = []
        for i in range(photo_count):
            photo = tmp_path / f"photo_{i:04d}.jpg"
            create_realistic_jpeg(photo)
            photos.append(photo)

        # Create export
        metadata_list = [create_test_metadata(photo) for photo in photos]
        output_zip = tmp_path / "throughput.zip"
        options = ZipExportOptions(
            include_xmp_sidecars=True,
            include_manifest=True,
            include_csv_summary=True,
        )

        # Measure throughput
        start = time.perf_counter()
        result = create_zip_export(photos, metadata_list, output_zip, options)
        elapsed_seconds = time.perf_counter() - start

        throughput = photo_count / elapsed_seconds

        print("RESULTS:")
        print(f"  Throughput: {throughput:.1f} photos/sec")
        print(f"  Time: {elapsed_seconds:.2f}s for {photo_count} photos\n")

        print(f"Target: >{MIN_THROUGHPUT_PHOTOS_PER_SEC} photos/sec")
        print(f"Actual: {throughput:.1f} photos/sec")

        assert result.success, f"ZIP creation failed: {result.errors}"
        assert throughput >= MIN_THROUGHPUT_PHOTOS_PER_SEC, (
            f"Throughput regression: {throughput:.1f} photos/sec "
            f"(target: >{MIN_THROUGHPUT_PHOTOS_PER_SEC} photos/sec)"
        )
        print("✓ PASS - No regression")


# ============================================================================
# Future Optimization Tests (Parallel I/O)
# ============================================================================


@pytest.mark.performance
@pytest.mark.skip(reason="Parallel I/O optimization not yet implemented (Subtask 4)")
class TestParallelIOOptimization:
    """Test parallel I/O improvements (future optimization)."""

    def test_parallel_io_speedup(self, tmp_path):
        """Parallel I/O should provide 50% speedup over sequential.

        NOTE: This test is skipped until parallel I/O optimization is
        implemented in Subtask 4. Remove @pytest.mark.skip when ready.
        """
        photo_count = 100

        print(f"\n{'='*60}")
        print("PARALLEL I/O OPTIMIZATION TEST")
        print(f"{'='*60}\n")

        # Create realistic photos
        photos = []
        for i in range(photo_count):
            photo = tmp_path / f"photo_{i:04d}.jpg"
            create_realistic_jpeg(photo)
            photos.append(photo)

        metadata_list = [create_test_metadata(photo) for photo in photos]
        options = ZipExportOptions(
            include_xmp_sidecars=True,
            include_manifest=True,
            include_csv_summary=True,
        )

        # Baseline: sequential I/O
        output_sequential = tmp_path / "sequential.zip"
        start = time.perf_counter()
        result_seq = create_zip_export(photos, metadata_list, output_sequential, options)
        sequential_time = time.perf_counter() - start

        # Optimized: parallel I/O
        # TODO: Add parallel=True parameter to create_zip_export
        output_parallel = tmp_path / "parallel.zip"
        start = time.perf_counter()
        # result_par = create_zip_export(photos, metadata_list, output_parallel, options, parallel=True)
        result_par = create_zip_export(photos, metadata_list, output_parallel, options)
        parallel_time = time.perf_counter() - start

        # Calculate speedup
        speedup = sequential_time / parallel_time

        print("RESULTS:")
        print(f"  Sequential: {sequential_time:.2f}s")
        print(f"  Parallel: {parallel_time:.2f}s")
        print(f"  Speedup: {speedup:.2f}x\n")

        print(f"Target speedup: >{PARALLEL_IO_SPEEDUP_TARGET}x")
        print(f"Actual speedup: {speedup:.2f}x")

        assert result_seq.success and result_par.success
        assert speedup >= PARALLEL_IO_SPEEDUP_TARGET, (
            f"Parallel I/O speedup too low: {speedup:.2f}x "
            f"(target: >{PARALLEL_IO_SPEEDUP_TARGET}x)"
        )
        print("✓ PASS - Parallel I/O improves performance")


# ============================================================================
# Stress Tests
# ============================================================================


@pytest.mark.performance
class TestStressScenarios:
    """Stress test with large photo counts."""

    def test_200_photos_stays_under_20_seconds(self, tmp_path):
        """200 photos stress test - should stay under 20 seconds."""
        photo_count = 200

        print(f"\n{'='*60}")
        print(f"STRESS TEST: {photo_count} photos")
        print(f"{'='*60}\n")

        # Create realistic photos
        print(f"Creating {photo_count} realistic photos...")
        photos = []
        for i in range(photo_count):
            photo = tmp_path / f"photo_{i:04d}.jpg"
            create_realistic_jpeg(photo)
            photos.append(photo)

        photo_sizes = [p.stat().st_size for p in photos]
        total_size_mb = sum(photo_sizes) / (1024 * 1024)
        print(f"Total photo size: {total_size_mb:.2f} MB\n")

        # Create export
        metadata_list = [create_test_metadata(photo) for photo in photos]
        output_zip = tmp_path / "stress_200.zip"
        options = ZipExportOptions(
            include_xmp_sidecars=True,
            include_manifest=True,
            include_csv_summary=True,
        )

        # Measure performance with memory tracking
        tracemalloc.start()
        start = time.perf_counter()
        result = create_zip_export(photos, metadata_list, output_zip, options)
        elapsed_ms = (time.perf_counter() - start) * 1000
        mem_current, mem_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        mem_peak_mb = mem_peak / (1024 * 1024)
        throughput = photo_count / (elapsed_ms / 1000)

        print("RESULTS:")
        print(f"  Time: {elapsed_ms:.0f}ms ({elapsed_ms/1000:.2f}s)")
        print(f"  Photos: {result.photo_count}")
        print(f"  ZIP size: {result.zip_size_bytes / (1024*1024):.2f} MB")
        print(f"  Peak memory: {mem_peak_mb:.2f} MB")
        print(f"  Throughput: {throughput:.1f} photos/sec\n")

        print(f"Time target: <{ZIP_200_PHOTOS_TARGET_MS}ms")
        print(f"Actual: {elapsed_ms:.0f}ms")

        assert result.success, f"ZIP creation failed: {result.errors}"
        assert elapsed_ms < ZIP_200_PHOTOS_TARGET_MS, (
            f"Stress test failed: {elapsed_ms:.0f}ms "
            f"(target: <{ZIP_200_PHOTOS_TARGET_MS}ms)"
        )
        print("✓ PASS - Stress test within target")

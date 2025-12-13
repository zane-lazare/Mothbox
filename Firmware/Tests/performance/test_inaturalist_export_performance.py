"""
Performance tests for iNaturalist export (Issue #118).

Benchmarks:
- XMP generation: <10ms per photo
- ZIP creation: 50 photos <5 seconds
- Memory usage: <100MB for 100 photos

Run with: pytest Tests/performance/test_inaturalist_export_performance.py -v -s
"""

import os
import sys
import time
import tracemalloc
from pathlib import Path

from PIL import Image

# Setup path
FIRMWARE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(FIRMWARE_DIR))
sys.path.insert(0, str(FIRMWARE_DIR / "webui" / "backend"))
os.environ.setdefault("MOTHBOX_ENV", "test")

from webui.backend.lib.xmp_sidecar import generate_xmp_xml
from webui.backend.services.export_metadata_service import (
    ExportMetadata,
    ExportMetadataService,
)

# ============================================================================
# Performance Target Constants
# ============================================================================

# XMP Generation
SINGLE_XMP_GENERATION_TARGET_MS = 10  # <10ms per XMP
BATCH_XMP_100_TARGET_MS = 1000  # <1s for 100 XMP generations

# ZIP Creation
ZIP_50_PHOTOS_TARGET_MS = 5000  # <5s for 50 photos
ZIP_100_PHOTOS_TARGET_MS = 10000  # <10s for 100 photos

# Throughput
MIN_THROUGHPUT_PHOTOS_PER_SEC = 10  # >10 photos/sec

# Memory
MEMORY_100_PHOTOS_MB = 100  # <100MB for 100 photos


# ============================================================================
# Test Fixtures
# ============================================================================


def create_test_jpeg(path: Path, size: tuple[int, int] = (100, 100)) -> None:
    """Create minimal valid JPEG for testing.

    Uses PIL if available, falls back to raw bytes if JPEG encoder missing.
    """
    try:
        img = Image.new('RGB', size, color='green')
        img.save(path, format='JPEG', quality=85)
    except (KeyError, OSError):
        # Fallback: create minimal valid JPEG bytes
        # JPEG header + padding + footer
        header = b'\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
        footer = b'\xFF\xD9'
        padding_size = max(0, 2048 - len(header) - len(footer))
        padding = b'\x00' * padding_size
        path.write_bytes(header + padding + footer)


def create_test_metadata(photo_path: Path) -> ExportMetadata:
    """Create test metadata for a photo."""
    return ExportMetadata(
        photo_path=photo_path,
        filename=photo_path.name,
        timestamp="2024-01-15T10:30:00",
        latitude=37.7749,
        longitude=-122.4194,
        altitude=15.5,
        gps_accuracy=2.5,
        species="Actias luna",
        species_common_name="Luna Moth",
        species_confidence="certain",
        tags=["moth", "lepidoptera", "night"],
        notes="Test observation",
        camera_make="Arducam",
        camera_model="OwlSight 64MP",
        deployment_name="Test Deployment",
        deployment_location_name="San Francisco, CA",
    )


# ============================================================================
# XMP Generation Performance Tests
# ============================================================================


class TestXmpGenerationPerformance:
    """XMP generation performance benchmarks."""

    def test_single_xmp_under_10ms(self, tmp_path):
        """Single XMP generation should be under 10ms."""
        # Create test photo and metadata
        photo = tmp_path / "test_photo.jpg"
        create_test_jpeg(photo)
        metadata = create_test_metadata(photo)

        # Warm up
        generate_xmp_xml(metadata)

        # Measure
        times = []
        for _ in range(10):
            start = time.perf_counter()
            generate_xmp_xml(metadata)
            end = time.perf_counter()
            times.append((end - start) * 1000)

        avg_ms = sum(times) / len(times)
        min_ms = min(times)
        max_ms = max(times)

        print("\nXMP Generation Performance:")
        print(f"  Average: {avg_ms:.2f}ms")
        print(f"  Min: {min_ms:.2f}ms")
        print(f"  Max: {max_ms:.2f}ms")

        assert avg_ms < SINGLE_XMP_GENERATION_TARGET_MS, (
            f"XMP generation too slow: {avg_ms:.2f}ms (target: <{SINGLE_XMP_GENERATION_TARGET_MS}ms)"
        )

    def test_batch_xmp_100_photos(self, tmp_path):
        """100 XMP generations should complete in reasonable time."""
        # Create test photos
        photos = []
        for i in range(100):
            photo = tmp_path / f"photo_{i:04d}.jpg"
            create_test_jpeg(photo)
            photos.append(photo)

        # Create metadata list
        metadata_list = [create_test_metadata(photo) for photo in photos]

        # Measure batch generation
        start = time.perf_counter()
        for metadata in metadata_list:
            generate_xmp_xml(metadata)
        end = time.perf_counter()

        total_ms = (end - start) * 1000
        per_photo_ms = total_ms / 100

        print("\nBatch XMP Generation (100 photos):")
        print(f"  Total: {total_ms:.0f}ms")
        print(f"  Per photo: {per_photo_ms:.2f}ms")

        # Should be under 10ms per photo average
        assert per_photo_ms < SINGLE_XMP_GENERATION_TARGET_MS * 2, (
            f"Batch XMP generation too slow: {per_photo_ms:.2f}ms per photo "
            f"(target: <{SINGLE_XMP_GENERATION_TARGET_MS * 2}ms)"
        )


# ============================================================================
# ZIP Creation Performance Tests
# ============================================================================


class TestZipCreationPerformance:
    """ZIP creation performance benchmarks."""

    def test_zip_50_photos_under_5_seconds(self, tmp_path):
        """50 photos should export in under 5 seconds."""
        # Create test photos
        photos = []
        for i in range(50):
            photo = tmp_path / f"photo_{i:04d}.jpg"
            create_test_jpeg(photo, size=(1920, 1080))
            photos.append(photo)

        output_zip = tmp_path / "export_50.zip"

        service = ExportMetadataService(cache_ttl=0)

        start = time.perf_counter()
        result = service.transform_batch_to_inaturalist_zip(photos, output_path=output_zip)
        end = time.perf_counter()

        elapsed_ms = (end - start) * 1000

        print("\nZIP Creation (50 photos):")
        print(f"  Total: {elapsed_ms:.0f}ms ({elapsed_ms/1000:.2f}s)")
        print(f"  Per photo: {elapsed_ms/50:.0f}ms")
        print(f"  ZIP size: {result.zip_size_bytes / (1024*1024):.2f} MB")

        assert result.success, f"ZIP creation failed: {result.errors}"
        assert elapsed_ms < ZIP_50_PHOTOS_TARGET_MS, (
            f"ZIP creation too slow: {elapsed_ms:.0f}ms (target: <{ZIP_50_PHOTOS_TARGET_MS}ms)"
        )

    def test_zip_100_photos_under_10_seconds(self, tmp_path):
        """100 photos should export in under 10 seconds."""
        # Create test photos
        photos = []
        for i in range(100):
            photo = tmp_path / f"photo_{i:04d}.jpg"
            create_test_jpeg(photo, size=(1920, 1080))
            photos.append(photo)

        output_zip = tmp_path / "export_100.zip"

        service = ExportMetadataService(cache_ttl=0)

        start = time.perf_counter()
        result = service.transform_batch_to_inaturalist_zip(photos, output_path=output_zip)
        end = time.perf_counter()

        elapsed_ms = (end - start) * 1000

        print("\nZIP Creation (100 photos):")
        print(f"  Total: {elapsed_ms:.0f}ms ({elapsed_ms/1000:.2f}s)")
        print(f"  Per photo: {elapsed_ms/100:.0f}ms")
        print(f"  ZIP size: {result.zip_size_bytes / (1024*1024):.2f} MB")

        assert result.success, f"ZIP creation failed: {result.errors}"
        assert elapsed_ms < ZIP_100_PHOTOS_TARGET_MS, (
            f"ZIP creation too slow: {elapsed_ms:.0f}ms (target: <{ZIP_100_PHOTOS_TARGET_MS}ms)"
        )


# ============================================================================
# Throughput Tests
# ============================================================================


class TestThroughput:
    """Throughput benchmarks."""

    def test_export_throughput_photos_per_second(self, tmp_path):
        """Measure export throughput in photos per second."""
        # Create test photos
        photos = []
        for i in range(50):
            photo = tmp_path / f"photo_{i:04d}.jpg"
            create_test_jpeg(photo, size=(1920, 1080))
            photos.append(photo)

        output_zip = tmp_path / "throughput_test.zip"

        service = ExportMetadataService(cache_ttl=0)

        start = time.perf_counter()
        result = service.transform_batch_to_inaturalist_zip(photos, output_path=output_zip)
        end = time.perf_counter()

        elapsed_seconds = end - start
        photos_per_second = len(photos) / elapsed_seconds

        print("\nThroughput:")
        print(f"  Photos/sec: {photos_per_second:.1f}")
        print(f"  Time: {elapsed_seconds:.2f}s for {len(photos)} photos")

        assert result.success, f"ZIP creation failed: {result.errors}"
        assert photos_per_second >= MIN_THROUGHPUT_PHOTOS_PER_SEC, (
            f"Throughput too low: {photos_per_second:.1f} photos/sec "
            f"(target: >{MIN_THROUGHPUT_PHOTOS_PER_SEC} photos/sec)"
        )


# ============================================================================
# Memory Usage Tests
# ============================================================================


class TestMemoryUsage:
    """Memory usage benchmarks."""

    def test_memory_100_photos_under_100mb(self, tmp_path):
        """100 photos should use less than 100MB memory."""
        # Create test photos
        photos = []
        for i in range(100):
            photo = tmp_path / f"photo_{i:04d}.jpg"
            create_test_jpeg(photo, size=(1920, 1080))
            photos.append(photo)

        output_zip = tmp_path / "memory_test.zip"

        service = ExportMetadataService(cache_ttl=0)

        # Start memory tracking
        tracemalloc.start()

        # Run export
        result = service.transform_batch_to_inaturalist_zip(photos, output_path=output_zip)

        # Get peak memory usage
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / (1024 * 1024)

        print("\nMemory Usage (100 photos):")
        print(f"  Peak: {peak_mb:.2f} MB")
        print(f"  Current: {current / (1024 * 1024):.2f} MB")

        assert result.success, f"ZIP creation failed: {result.errors}"
        assert peak_mb < MEMORY_100_PHOTOS_MB, (
            f"Memory usage too high: {peak_mb:.2f} MB (target: <{MEMORY_100_PHOTOS_MB} MB)"
        )


# ============================================================================
# Scalability Tests
# ============================================================================


class TestScalability:
    """Test scalability with different batch sizes."""

    def test_linear_scaling(self, tmp_path):
        """Verify performance scales linearly with batch size."""
        batch_sizes = [10, 25, 50]
        results = []

        service = ExportMetadataService(cache_ttl=0)

        for size in batch_sizes:
            # Create test photos
            photos = []
            for i in range(size):
                photo = tmp_path / f"scale_{size}_{i:04d}.jpg"
                create_test_jpeg(photo, size=(1920, 1080))
                photos.append(photo)

            output_zip = tmp_path / f"scale_{size}.zip"

            # Measure
            start = time.perf_counter()
            result = service.transform_batch_to_inaturalist_zip(photos, output_path=output_zip)
            end = time.perf_counter()

            elapsed_ms = (end - start) * 1000
            per_photo_ms = elapsed_ms / size

            results.append({
                'size': size,
                'total_ms': elapsed_ms,
                'per_photo_ms': per_photo_ms,
            })

            print(f"\nScalability Test ({size} photos):")
            print(f"  Total: {elapsed_ms:.0f}ms")
            print(f"  Per photo: {per_photo_ms:.0f}ms")

            assert result.success, f"ZIP creation failed for size {size}: {result.errors}"

        # Verify roughly linear scaling (per-photo time should be relatively stable)
        per_photo_times = [r['per_photo_ms'] for r in results]
        avg_per_photo = sum(per_photo_times) / len(per_photo_times)
        max_deviation = max(abs(t - avg_per_photo) for t in per_photo_times)

        print("\nScalability Analysis:")
        print(f"  Average per-photo: {avg_per_photo:.0f}ms")
        print(f"  Max deviation: {max_deviation:.0f}ms")

        # Allow 50% deviation from average (linear scaling)
        assert max_deviation < avg_per_photo * 0.5, (
            f"Non-linear scaling detected: {max_deviation:.0f}ms deviation "
            f"from average {avg_per_photo:.0f}ms"
        )

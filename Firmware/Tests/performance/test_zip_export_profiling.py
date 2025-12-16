"""
Profiling tests for ZIP export performance (Issue #128).

Benchmarks the current implementation with realistic photo sizes to identify bottlenecks.

Measures:
- Photo file I/O (disk read)
- XMP generation time
- ZIP write time
- Total time
- Memory usage with tracemalloc

Baseline targets:
- 50 photos: <5 seconds
- 100 photos: <10 seconds
- 200 photos: <20 seconds

Run with: pytest Tests/performance/test_zip_export_profiling.py -v -s --tb=short
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

from webui.backend.lib.xmp_sidecar import generate_xmp_xml
from webui.backend.lib.zip_export import (
    ZipExportOptions,
    create_zip_export,
)
from webui.backend.services.export_metadata_service import ExportMetadata

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
# Profiling Helpers
# ============================================================================


class PhaseTimer:
    """Context manager for timing code phases."""

    def __init__(self, name: str):
        self.name = name
        self.start = 0.0
        self.end = 0.0
        self.elapsed_ms = 0.0

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.end = time.perf_counter()
        self.elapsed_ms = (self.end - self.start) * 1000


def profile_photo_io(photo_paths: list[Path]) -> dict:
    """Profile photo file I/O (reading from disk).

    Args:
        photo_paths: List of photo paths to read

    Returns:
        Dict with timing stats
    """
    times = []

    for path in photo_paths:
        with PhaseTimer("photo_read") as timer:
            # Simulate what ZIP does: stat + read
            _ = path.stat()
            _ = path.read_bytes()

        times.append(timer.elapsed_ms)

    return {
        'total_ms': sum(times),
        'avg_ms': sum(times) / len(times) if times else 0,
        'min_ms': min(times) if times else 0,
        'max_ms': max(times) if times else 0,
        'count': len(times),
    }


def profile_xmp_generation(metadata_list: list[ExportMetadata]) -> dict:
    """Profile XMP generation for all photos.

    Args:
        metadata_list: List of metadata to generate XMP for

    Returns:
        Dict with timing stats
    """
    times = []

    for metadata in metadata_list:
        with PhaseTimer("xmp_gen") as timer:
            _ = generate_xmp_xml(metadata)

        times.append(timer.elapsed_ms)

    return {
        'total_ms': sum(times),
        'avg_ms': sum(times) / len(times) if times else 0,
        'min_ms': min(times) if times else 0,
        'max_ms': max(times) if times else 0,
        'count': len(times),
    }


def profile_zip_write(
    photo_paths: list[Path],
    metadata_list: list[ExportMetadata],
    output_path: Path,
    options: ZipExportOptions,
) -> dict:
    """Profile complete ZIP write operation with phase breakdown.

    Args:
        photo_paths: List of photo paths
        metadata_list: List of metadata
        output_path: Output ZIP path
        options: ZIP export options

    Returns:
        Dict with timing breakdown and result
    """
    # Total time
    with PhaseTimer("total") as total_timer:
        result = create_zip_export(
            photo_paths=photo_paths,
            metadata_list=metadata_list,
            output_path=output_path,
            options=options,
        )

    return {
        'total_ms': total_timer.elapsed_ms,
        'result': result,
    }


# ============================================================================
# Baseline Profiling Tests
# ============================================================================


@pytest.mark.performance
class TestZipExportProfiling:
    """Profile ZIP export with realistic photo sizes."""

    def test_profile_50_photos_baseline(self, tmp_path):
        """Profile 50 photos (2-3MB each) - baseline measurement."""
        photo_count = 50

        print(f"\n{'='*60}")
        print(f"PROFILING: {photo_count} photos (realistic sizes)")
        print(f"{'='*60}\n")

        # Phase 1: Create realistic test photos
        print("Phase 1: Creating realistic test photos...")
        photos = []
        photo_create_start = time.perf_counter()
        for i in range(photo_count):
            photo = tmp_path / f"photo_{i:04d}.jpg"
            create_realistic_jpeg(photo)
            photos.append(photo)
        photo_create_time = (time.perf_counter() - photo_create_start) * 1000

        # Calculate average photo size
        photo_sizes = [p.stat().st_size for p in photos]
        avg_size_mb = sum(photo_sizes) / len(photo_sizes) / (1024 * 1024)
        total_size_mb = sum(photo_sizes) / (1024 * 1024)

        print(f"  Created {len(photos)} photos in {photo_create_time:.0f}ms")
        print(f"  Average photo size: {avg_size_mb:.2f} MB")
        print(f"  Total size: {total_size_mb:.2f} MB\n")

        # Phase 2: Profile photo I/O
        print("Phase 2: Profiling photo file I/O...")
        io_stats = profile_photo_io(photos)
        print(f"  Total I/O time: {io_stats['total_ms']:.0f}ms")
        print(f"  Average per photo: {io_stats['avg_ms']:.2f}ms")
        print(f"  Min/Max: {io_stats['min_ms']:.2f}ms / {io_stats['max_ms']:.2f}ms\n")

        # Phase 3: Create metadata and profile XMP generation
        print("Phase 3: Profiling XMP generation...")
        metadata_list = [create_test_metadata(photo) for photo in photos]
        xmp_stats = profile_xmp_generation(metadata_list)
        print(f"  Total XMP time: {xmp_stats['total_ms']:.0f}ms")
        print(f"  Average per photo: {xmp_stats['avg_ms']:.2f}ms")
        print(f"  Min/Max: {xmp_stats['min_ms']:.2f}ms / {xmp_stats['max_ms']:.2f}ms\n")

        # Phase 4: Profile ZIP write with memory tracking
        print("Phase 4: Profiling ZIP write with memory tracking...")
        output_zip = tmp_path / "export_profiling.zip"
        options = ZipExportOptions(
            include_xmp_sidecars=True,
            include_manifest=True,
            include_csv_summary=True,
        )

        # Start memory tracking
        tracemalloc.start()
        mem_start = tracemalloc.get_traced_memory()[0]

        # Profile ZIP write
        zip_stats = profile_zip_write(photos, metadata_list, output_zip, options)

        # Get peak memory
        mem_current, mem_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        mem_used_mb = (mem_current - mem_start) / (1024 * 1024)
        mem_peak_mb = mem_peak / (1024 * 1024)

        result = zip_stats['result']
        print(f"  ZIP write time: {zip_stats['total_ms']:.0f}ms")
        print(f"  Success: {result.success}")
        print(f"  Photos in ZIP: {result.photo_count}")
        print(f"  XMP sidecars: {result.xmp_count}")
        print(f"  ZIP size: {result.zip_size_bytes / (1024*1024):.2f} MB")
        print(f"  Memory used: {mem_used_mb:.2f} MB")
        print(f"  Peak memory: {mem_peak_mb:.2f} MB\n")

        # Phase 5: Calculate breakdown
        print("="*60)
        print("PERFORMANCE BREAKDOWN")
        print("="*60)

        # Note: ZIP write includes I/O + XMP + ZIP overhead
        # Estimate overhead by subtracting measured I/O and XMP
        overhead_ms = zip_stats['total_ms'] - io_stats['total_ms'] - xmp_stats['total_ms']

        print("\nPhase breakdown:")
        print(f"  Photo I/O:      {io_stats['total_ms']:>8.0f}ms ({io_stats['total_ms']/zip_stats['total_ms']*100:>5.1f}%)")
        print(f"  XMP generation: {xmp_stats['total_ms']:>8.0f}ms ({xmp_stats['total_ms']/zip_stats['total_ms']*100:>5.1f}%)")
        print(f"  ZIP overhead:   {overhead_ms:>8.0f}ms ({overhead_ms/zip_stats['total_ms']*100:>5.1f}%)")
        print(f"  Total ZIP:      {zip_stats['total_ms']:>8.0f}ms (100.0%)")

        throughput = photo_count / (zip_stats['total_ms'] / 1000)
        print(f"\nThroughput: {throughput:.1f} photos/sec")
        print(f"Per-photo average: {zip_stats['total_ms']/photo_count:.0f}ms")

        # Baseline target: 50 photos < 5000ms
        baseline_target_ms = 5000
        print(f"\nBaseline target: {photo_count} photos < {baseline_target_ms}ms")
        print(f"Actual: {zip_stats['total_ms']:.0f}ms")

        if zip_stats['total_ms'] < baseline_target_ms:
            print("✓ PASS - Within target")
        else:
            print(f"✗ SLOW - {zip_stats['total_ms'] - baseline_target_ms:.0f}ms over target")

        print()

        # Assertions
        assert result.success, f"ZIP creation failed: {result.errors}"
        assert result.photo_count == photo_count
        assert result.xmp_count == photo_count
        assert output_zip.exists()

    def test_profile_100_photos_baseline(self, tmp_path):
        """Profile 100 photos (2-3MB each) - baseline measurement."""
        photo_count = 100

        print(f"\n{'='*60}")
        print(f"PROFILING: {photo_count} photos (realistic sizes)")
        print(f"{'='*60}\n")

        # Create realistic test photos
        print("Creating realistic test photos...")
        photos = []
        for i in range(photo_count):
            photo = tmp_path / f"photo_{i:04d}.jpg"
            create_realistic_jpeg(photo)
            photos.append(photo)

        photo_sizes = [p.stat().st_size for p in photos]
        total_size_mb = sum(photo_sizes) / (1024 * 1024)
        print(f"  Total size: {total_size_mb:.2f} MB\n")

        # Profile complete flow
        metadata_list = [create_test_metadata(photo) for photo in photos]
        output_zip = tmp_path / "export_100.zip"
        options = ZipExportOptions(
            include_xmp_sidecars=True,
            include_manifest=True,
            include_csv_summary=True,
        )

        # Memory tracking
        tracemalloc.start()
        zip_stats = profile_zip_write(photos, metadata_list, output_zip, options)
        mem_current, mem_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        result = zip_stats['result']

        print("RESULTS:")
        print(f"  Total time: {zip_stats['total_ms']:.0f}ms ({zip_stats['total_ms']/1000:.2f}s)")
        print(f"  Photos: {result.photo_count}")
        print(f"  ZIP size: {result.zip_size_bytes / (1024*1024):.2f} MB")
        print(f"  Peak memory: {mem_peak / (1024*1024):.2f} MB")
        print(f"  Throughput: {photo_count / (zip_stats['total_ms']/1000):.1f} photos/sec")
        print(f"  Per-photo: {zip_stats['total_ms']/photo_count:.0f}ms\n")

        baseline_target_ms = 10000
        print(f"Baseline target: {photo_count} photos < {baseline_target_ms}ms")
        print(f"Actual: {zip_stats['total_ms']:.0f}ms")

        if zip_stats['total_ms'] < baseline_target_ms:
            print("✓ PASS - Within target")
        else:
            print(f"✗ SLOW - {zip_stats['total_ms'] - baseline_target_ms:.0f}ms over target")

        print()

        assert result.success, f"ZIP creation failed: {result.errors}"
        assert result.photo_count == photo_count

    def test_profile_200_photos_baseline(self, tmp_path):
        """Profile 200 photos (2-3MB each) - stress test baseline."""
        photo_count = 200

        print(f"\n{'='*60}")
        print(f"PROFILING: {photo_count} photos (realistic sizes)")
        print(f"{'='*60}\n")

        # Create realistic test photos
        print("Creating realistic test photos...")
        photos = []
        for i in range(photo_count):
            photo = tmp_path / f"photo_{i:04d}.jpg"
            create_realistic_jpeg(photo)
            photos.append(photo)

        photo_sizes = [p.stat().st_size for p in photos]
        total_size_mb = sum(photo_sizes) / (1024 * 1024)
        print(f"  Total size: {total_size_mb:.2f} MB\n")

        # Profile complete flow
        metadata_list = [create_test_metadata(photo) for photo in photos]
        output_zip = tmp_path / "export_200.zip"
        options = ZipExportOptions(
            include_xmp_sidecars=True,
            include_manifest=True,
            include_csv_summary=True,
        )

        # Memory tracking
        tracemalloc.start()
        zip_stats = profile_zip_write(photos, metadata_list, output_zip, options)
        mem_current, mem_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        result = zip_stats['result']

        print("RESULTS:")
        print(f"  Total time: {zip_stats['total_ms']:.0f}ms ({zip_stats['total_ms']/1000:.2f}s)")
        print(f"  Photos: {result.photo_count}")
        print(f"  ZIP size: {result.zip_size_bytes / (1024*1024):.2f} MB")
        print(f"  Peak memory: {mem_peak / (1024*1024):.2f} MB")
        print(f"  Throughput: {photo_count / (zip_stats['total_ms']/1000):.1f} photos/sec")
        print(f"  Per-photo: {zip_stats['total_ms']/photo_count:.0f}ms\n")

        baseline_target_ms = 20000
        print(f"Baseline target: {photo_count} photos < {baseline_target_ms}ms")
        print(f"Actual: {zip_stats['total_ms']:.0f}ms")

        if zip_stats['total_ms'] < baseline_target_ms:
            print("✓ PASS - Within target")
        else:
            print(f"✗ SLOW - {zip_stats['total_ms'] - baseline_target_ms:.0f}ms over target")

        print()

        assert result.success, f"ZIP creation failed: {result.errors}"
        assert result.photo_count == photo_count


# ============================================================================
# Component-Level Profiling
# ============================================================================


@pytest.mark.performance
class TestComponentProfiling:
    """Profile individual components in isolation."""

    def test_profile_photo_io_only(self, tmp_path):
        """Profile just photo I/O (disk read) performance."""
        photo_count = 100

        print(f"\n{'='*60}")
        print("COMPONENT PROFILING: Photo I/O Only")
        print(f"{'='*60}\n")

        # Create photos
        photos = []
        for i in range(photo_count):
            photo = tmp_path / f"photo_{i:04d}.jpg"
            create_realistic_jpeg(photo)
            photos.append(photo)

        photo_sizes = [p.stat().st_size for p in photos]
        total_size_mb = sum(photo_sizes) / (1024 * 1024)

        # Profile I/O
        io_stats = profile_photo_io(photos)

        print(f"Results ({photo_count} photos, {total_size_mb:.2f} MB total):")
        print(f"  Total I/O time: {io_stats['total_ms']:.0f}ms")
        print(f"  Average per photo: {io_stats['avg_ms']:.2f}ms")
        print(f"  Min/Max: {io_stats['min_ms']:.2f}ms / {io_stats['max_ms']:.2f}ms")
        print(f"  Throughput: {photo_count / (io_stats['total_ms']/1000):.1f} photos/sec")
        print(f"  Disk read speed: {total_size_mb / (io_stats['total_ms']/1000):.1f} MB/sec\n")

    def test_profile_xmp_generation_only(self, tmp_path):
        """Profile just XMP generation performance."""
        photo_count = 100

        print(f"\n{'='*60}")
        print("COMPONENT PROFILING: XMP Generation Only")
        print(f"{'='*60}\n")

        # Create photos (needed for metadata)
        photos = []
        for i in range(photo_count):
            photo = tmp_path / f"photo_{i:04d}.jpg"
            create_realistic_jpeg(photo)
            photos.append(photo)

        # Create metadata
        metadata_list = [create_test_metadata(photo) for photo in photos]

        # Profile XMP generation
        xmp_stats = profile_xmp_generation(metadata_list)

        # Calculate average XMP size
        xmp_sizes = [len(generate_xmp_xml(m)) for m in metadata_list[:5]]  # Sample 5
        avg_xmp_size_kb = sum(xmp_sizes) / len(xmp_sizes) / 1024

        print(f"Results ({photo_count} XMP files):")
        print(f"  Total XMP time: {xmp_stats['total_ms']:.0f}ms")
        print(f"  Average per XMP: {xmp_stats['avg_ms']:.2f}ms")
        print(f"  Min/Max: {xmp_stats['min_ms']:.2f}ms / {xmp_stats['max_ms']:.2f}ms")
        print(f"  Throughput: {photo_count / (xmp_stats['total_ms']/1000):.1f} XMP/sec")
        print(f"  Average XMP size: {avg_xmp_size_kb:.2f} KB\n")

    def test_profile_zip_compression_overhead(self, tmp_path):
        """Profile ZIP file structure overhead (without XMP/manifest)."""
        photo_count = 100

        print(f"\n{'='*60}")
        print("COMPONENT PROFILING: ZIP Compression Overhead")
        print(f"{'='*60}\n")

        # Create photos
        photos = []
        for i in range(photo_count):
            photo = tmp_path / f"photo_{i:04d}.jpg"
            create_realistic_jpeg(photo)
            photos.append(photo)

        metadata_list = [create_test_metadata(photo) for photo in photos]

        # Minimal options (no XMP, no extras)
        minimal_options = ZipExportOptions(
            include_xmp_sidecars=False,
            include_manifest=False,
            include_csv_summary=False,
        )

        # Full options
        full_options = ZipExportOptions(
            include_xmp_sidecars=True,
            include_manifest=True,
            include_csv_summary=True,
        )

        # Profile minimal ZIP
        output_minimal = tmp_path / "minimal.zip"
        minimal_stats = profile_zip_write(photos, metadata_list, output_minimal, minimal_options)

        # Profile full ZIP
        output_full = tmp_path / "full.zip"
        full_stats = profile_zip_write(photos, metadata_list, output_full, full_options)

        print("Minimal ZIP (photos only):")
        print(f"  Time: {minimal_stats['total_ms']:.0f}ms")
        print(f"  Size: {minimal_stats['result'].zip_size_bytes / (1024*1024):.2f} MB\n")

        print("Full ZIP (photos + XMP + manifest + CSV):")
        print(f"  Time: {full_stats['total_ms']:.0f}ms")
        print(f"  Size: {full_stats['result'].zip_size_bytes / (1024*1024):.2f} MB\n")

        overhead_ms = full_stats['total_ms'] - minimal_stats['total_ms']
        overhead_percent = (overhead_ms / minimal_stats['total_ms']) * 100

        print("XMP + Extras overhead:")
        print(f"  Time: {overhead_ms:.0f}ms ({overhead_percent:.1f}% increase)")
        print(f"  Size: {(full_stats['result'].zip_size_bytes - minimal_stats['result'].zip_size_bytes) / (1024*1024):.2f} MB\n")

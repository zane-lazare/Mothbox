"""
Performance tests for GPS EXIF functionality
Tests processing speed, throughput, and resource usage

Target performance benchmarks:
- Single photo processing: <500ms
- Batch throughput: >10 photos/sec
- Service latency: <10 seconds from photo creation to GPS tagging
- Memory usage: <50MB for 1000 photos
"""

import pytest
import time
import tempfile
from pathlib import Path
from PIL import Image
import psutil
import os

# Import modules under test
from lib.gps_exif_lib import embed_gps_exif, verify_gps_exif
import gps_exif_tagger


# Mark all tests in this file as performance tests
pytestmark = pytest.mark.performance


class TestSinglePhotoPerformance:
    """Test single photo processing performance."""

    def test_single_photo_processing_under_500ms(self):
        """Test that single photo processing completes in <500ms."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_path = Path(tmp.name)

            # Create test photo
            img = Image.new('RGB', (1920, 1080), color='blue')
            img.save(tmp_path, quality=95)

        try:
            # Create GPS data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as controls:
                controls.write("lat=40.7128\n")
                controls.write("lon=-74.0060\n")
                controls.write("gps_fix_mode=3\n")
                controls.write("alt=15.5\n")
                controls.write("gpstime=1642259445\n")
                controls.flush()
                controls_path = Path(controls.name)

            try:
                start_time = time.time()
                result = embed_gps_exif(tmp_path, controls_file=controls_path)
                elapsed = time.time() - start_time

                # Performance assertion
                assert elapsed < 0.5, f"Processing took {elapsed:.3f}s (target: <0.5s)"

                # Verify success
                assert result['success'] or result.get('skipped')
            finally:
                controls_path.unlink()
        finally:
            tmp_path.unlink()

    def test_verification_under_100ms(self):
        """Test that EXIF verification completes in <100ms."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_path = Path(tmp.name)

            # Create and tag photo
            img = Image.new('RGB', (1920, 1080), color='green')
            img.save(tmp_path, quality=95)

            # Tag it
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as controls:
                controls.write("lat=40.7128\n")
                controls.write("lon=-74.0060\n")
                controls.write("gps_fix_mode=3\n")
                controls.flush()
                controls_path = Path(controls.name)

            try:
                embed_gps_exif(tmp_path, controls_file=controls_path)

                # Now test verification speed
                start_time = time.time()
                result = verify_gps_exif(tmp_path)
                elapsed = time.time() - start_time

                # Performance assertion
                assert elapsed < 0.1, f"Verification took {elapsed:.3f}s (target: <0.1s)"

                # Verify correctness
                assert result.get('has_gps')
            finally:
                controls_path.unlink()
        finally:
            tmp_path.unlink()


class TestBatchThroughput:
    """Test batch processing throughput."""

    def test_batch_throughput_10_photos_per_second(self):
        """Test that batch processing achieves >10 photos/sec throughput."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create 50 test photos
            photo_count = 50
            for i in range(photo_count):
                photo_path = tmp_path / f'photo_{i:03d}.jpg'
                img = Image.new('RGB', (1920, 1080), color='red')
                img.save(photo_path, quality=85)

            # Create GPS data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as controls:
                controls.write("lat=40.7128\n")
                controls.write("lon=-74.0060\n")
                controls.write("gps_fix_mode=3\n")
                controls.write("alt=20.0\n")
                controls.flush()
                controls_path = Path(controls.name)

            try:
                from unittest.mock import Mock
                logger = Mock()

                # Measure batch processing time
                start_time = time.time()
                stats = gps_exif_tagger.batch_process_directory(
                    tmp_path,
                    logger,
                    pattern='*.jpg',
                    controls_file=controls_path
                )
                elapsed = time.time() - start_time

                # Calculate throughput
                throughput = photo_count / elapsed

                print(f"\nBatch processing:")
                print(f"  Photos: {photo_count}")
                print(f"  Time: {elapsed:.2f}s")
                print(f"  Throughput: {throughput:.1f} photos/sec")

                # Performance assertion
                assert throughput >= 10, f"Throughput was {throughput:.1f} photos/sec (target: ≥10)"

                # Verify completeness
                assert stats['total'] == photo_count
            finally:
                controls_path.unlink()

    def test_scaling_with_100_photos(self):
        """Test performance scaling with 100 photos."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create 100 test photos
            photo_count = 100
            print(f"\nCreating {photo_count} test photos...")
            for i in range(photo_count):
                photo_path = tmp_path / f'photo_{i:03d}.jpg'
                img = Image.new('RGB', (1920, 1080), color='yellow')
                img.save(photo_path, quality=85)

            # Create GPS data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as controls:
                controls.write("lat=40.7128\n")
                controls.write("lon=-74.0060\n")
                controls.write("gps_fix_mode=3\n")
                controls.flush()
                controls_path = Path(controls.name)

            try:
                from unittest.mock import Mock
                logger = Mock()

                # Measure processing time
                start_time = time.time()
                stats = gps_exif_tagger.batch_process_directory(
                    tmp_path,
                    logger,
                    pattern='*.jpg',
                    controls_file=controls_path
                )
                elapsed = time.time() - start_time

                throughput = photo_count / elapsed

                print(f"Batch processing (100 photos):")
                print(f"  Time: {elapsed:.2f}s")
                print(f"  Throughput: {throughput:.1f} photos/sec")
                print(f"  Avg per photo: {(elapsed/photo_count)*1000:.1f}ms")

                # Should maintain reasonable throughput
                assert throughput >= 5, f"Throughput dropped to {throughput:.1f} photos/sec"

                # Should complete in reasonable time
                assert elapsed < 30, f"Processing took {elapsed:.1f}s (target: <30s)"
            finally:
                controls_path.unlink()


class TestMemoryUsage:
    """Test memory consumption."""

    def test_batch_processing_memory_under_50mb(self):
        """Test that batch processing uses <50MB memory for 100 photos."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create 100 test photos
            photo_count = 100
            for i in range(photo_count):
                photo_path = tmp_path / f'photo_{i:03d}.jpg'
                img = Image.new('RGB', (1920, 1080), color='purple')
                img.save(photo_path, quality=85)

            # Create GPS data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as controls:
                controls.write("lat=40.7128\n")
                controls.write("lon=-74.0060\n")
                controls.write("gps_fix_mode=3\n")
                controls.flush()
                controls_path = Path(controls.name)

            try:
                from unittest.mock import Mock
                logger = Mock()

                # Measure memory before
                process = psutil.Process(os.getpid())
                mem_before = process.memory_info().rss / 1024 / 1024  # MB

                # Process photos
                stats = gps_exif_tagger.batch_process_directory(
                    tmp_path,
                    logger,
                    pattern='*.jpg',
                    controls_file=controls_path
                )

                # Measure memory after
                mem_after = process.memory_info().rss / 1024 / 1024  # MB
                mem_delta = mem_after - mem_before

                print(f"\nMemory usage:")
                print(f"  Before: {mem_before:.1f}MB")
                print(f"  After: {mem_after:.1f}MB")
                print(f"  Delta: {mem_delta:.1f}MB")

                # Performance assertion
                assert mem_delta < 50, f"Memory usage was {mem_delta:.1f}MB (target: <50MB)"
            finally:
                controls_path.unlink()

    def test_single_photo_minimal_memory(self):
        """Test that single photo processing has minimal memory footprint."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_path = Path(tmp.name)

            # Create test photo
            img = Image.new('RGB', (1920, 1080), color='orange')
            img.save(tmp_path, quality=95)

        try:
            # Create GPS data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as controls:
                controls.write("lat=40.7128\n")
                controls.write("lon=-74.0060\n")
                controls.write("gps_fix_mode=3\n")
                controls.flush()
                controls_path = Path(controls.name)

            try:
                process = psutil.Process(os.getpid())
                mem_before = process.memory_info().rss / 1024 / 1024

                result = embed_gps_exif(tmp_path, controls_file=controls_path)

                mem_after = process.memory_info().rss / 1024 / 1024
                mem_delta = mem_after - mem_before

                print(f"\nSingle photo memory delta: {mem_delta:.2f}MB")

                # Should use minimal memory
                assert mem_delta < 10, f"Memory delta was {mem_delta:.1f}MB"
            finally:
                controls_path.unlink()
        finally:
            tmp_path.unlink()


class TestCPUEfficiency:
    """Test CPU efficiency and utilization."""

    def test_batch_processing_cpu_time(self):
        """Test CPU time efficiency for batch processing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create 50 test photos
            photo_count = 50
            for i in range(photo_count):
                photo_path = tmp_path / f'photo_{i:03d}.jpg'
                img = Image.new('RGB', (1920, 1080), color='cyan')
                img.save(photo_path, quality=85)

            # Create GPS data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as controls:
                controls.write("lat=40.7128\n")
                controls.write("lon=-74.0060\n")
                controls.write("gps_fix_mode=3\n")
                controls.flush()
                controls_path = Path(controls.name)

            try:
                from unittest.mock import Mock
                logger = Mock()

                # Measure CPU time
                process = psutil.Process(os.getpid())
                cpu_before = process.cpu_times()

                start_time = time.time()
                stats = gps_exif_tagger.batch_process_directory(
                    tmp_path,
                    logger,
                    pattern='*.jpg',
                    controls_file=controls_path
                )
                wall_time = time.time() - start_time

                cpu_after = process.cpu_times()
                cpu_time = (cpu_after.user - cpu_before.user) + (cpu_after.system - cpu_before.system)

                cpu_efficiency = (cpu_time / wall_time) * 100 if wall_time > 0 else 0

                print(f"\nCPU efficiency:")
                print(f"  Wall time: {wall_time:.2f}s")
                print(f"  CPU time: {cpu_time:.2f}s")
                print(f"  Efficiency: {cpu_efficiency:.1f}%")

                # Should be reasonably efficient (allow for I/O wait)
                assert cpu_efficiency < 200, "CPU usage unexpectedly high"
            finally:
                controls_path.unlink()


class TestRealWorldScenarios:
    """Test realistic usage scenarios."""

    def test_daily_batch_scenario(self):
        """Simulate daily batch processing of night's photos."""
        # Simulate typical night: 200 photos over 8 hours
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            photo_count = 200
            print(f"\nSimulating daily batch: {photo_count} photos")

            # Create photos
            for i in range(photo_count):
                photo_path = tmp_path / f'20240115_{i:06d}.jpg'
                img = Image.new('RGB', (3840, 2160), color='black')  # 4K resolution
                img.save(photo_path, quality=90)

            # Create GPS data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as controls:
                controls.write("lat=40.7128\n")
                controls.write("lon=-74.0060\n")
                controls.write("gps_fix_mode=3\n")
                controls.write("alt=25.5\n")
                controls.flush()
                controls_path = Path(controls.name)

            try:
                from unittest.mock import Mock
                logger = Mock()

                start_time = time.time()
                stats = gps_exif_tagger.batch_process_directory(
                    tmp_path,
                    logger,
                    pattern='*.jpg',
                    controls_file=controls_path
                )
                elapsed = time.time() - start_time

                throughput = photo_count / elapsed

                print(f"Daily batch results:")
                print(f"  Photos: {photo_count}")
                print(f"  Time: {elapsed:.1f}s ({elapsed/60:.1f}min)")
                print(f"  Throughput: {throughput:.1f} photos/sec")
                print(f"  Tagged: {stats.get('tagged', 0)}")
                print(f"  Skipped: {stats.get('skipped', 0)}")
                print(f"  Errors: {stats.get('errors', 0)}")

                # Should complete in reasonable time (< 2 minutes for 200 photos)
                assert elapsed < 120, f"Daily batch took {elapsed:.1f}s (target: <120s)"

                # Should process all photos
                assert stats['total'] == photo_count
            finally:
                controls_path.unlink()


# Performance benchmarking utility
def benchmark_operation(operation_name, operation_func, iterations=10):
    """Utility function to benchmark an operation."""
    times = []

    for i in range(iterations):
        start = time.time()
        operation_func()
        elapsed = time.time() - start
        times.append(elapsed)

    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)

    print(f"\n{operation_name} benchmark ({iterations} iterations):")
    print(f"  Average: {avg_time*1000:.1f}ms")
    print(f"  Min: {min_time*1000:.1f}ms")
    print(f"  Max: {max_time*1000:.1f}ms")

    return {
        'avg': avg_time,
        'min': min_time,
        'max': max_time,
        'iterations': iterations
    }

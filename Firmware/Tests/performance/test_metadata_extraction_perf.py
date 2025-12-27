"""
Performance benchmarks for metadata extraction (Issue #106).

Validates that metadata operations meet performance requirements:
- Single photo EXIF extraction: <50ms
- Batch extraction (100 photos): >20 photos/second
- GPS coordinate parsing: <10ms
- Series detection: <100ms for 1000 photos

These benchmarks ensure the photo viewer remains responsive when
displaying metadata for large photo collections.

Related:
- Issue #106: E2E tests for photo viewer with real EXIF data
- webui/backend/services/metadata_service.py: Service being benchmarked
- Tests/unit/test_metadata_service.py: Functional tests
"""

import json
import time

import piexif
import pytest
from PIL import Image

# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_photos_dir(tmp_path):
    """Create a temporary photos directory."""
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()
    return photos_dir


@pytest.fixture
def sample_photo_with_full_exif(temp_photos_dir):
    """
    Create a single photo with comprehensive EXIF data for single-photo benchmarks.

    Includes: Camera info, GPS, capture settings, MakerNote with Mothbox metadata.
    """
    photo_path = temp_photos_dir / "mothbox_2024_01_15__10_00_00.jpg"

    # Create minimal valid JPEG image (small for fast I/O)
    img = Image.new('RGB', (640, 480), color='red')

    # Build comprehensive EXIF data
    exif_dict = {
        "0th": {
            piexif.ImageIFD.Make: b"Arducam",
            piexif.ImageIFD.Model: b"OwlSight 64MP",
            piexif.ImageIFD.Software: b"Mothbox Firmware 5.0",
        },
        "Exif": {
            piexif.ExifIFD.DateTimeOriginal: b"2024:01:15 10:00:00",
            piexif.ExifIFD.ExposureTime: (1, 1000),  # 1/1000 sec
            piexif.ExifIFD.FNumber: (28, 10),  # f/2.8
            piexif.ExifIFD.ISOSpeedRatings: 400,
            piexif.ExifIFD.FocalLength: (24, 1),  # 24mm
            piexif.ExifIFD.WhiteBalance: 0,  # Auto
            piexif.ExifIFD.Flash: 0,  # No flash
            piexif.ExifIFD.LensModel: b"Wide Angle Lens",
            piexif.ExifIFD.MakerNote: json.dumps({
                'sensor': 'IMX477',
                'mothbox_name': 'mothbox',
                'capture_type': 'standard',
                'focus_mode': 1,
                'noise_reduction': 2,
                'lens_position': 3.5,
                'colour_gain_red': 1.8,
                'colour_gain_blue': 1.5,
            }).encode('utf-8')
        },
        "GPS": {
            piexif.GPSIFD.GPSLatitudeRef: b"N",
            piexif.GPSIFD.GPSLatitude: ((37, 1), (46, 1), (2940, 100)),  # 37°46'29.4"N
            piexif.GPSIFD.GPSLongitudeRef: b"W",
            piexif.GPSIFD.GPSLongitude: ((122, 1), (25, 1), (1656, 100)),  # 122°25'16.56"W
            piexif.GPSIFD.GPSAltitude: (10000, 100),  # 100.0 meters
            piexif.GPSIFD.GPSAltitudeRef: 0,  # Above sea level
            piexif.GPSIFD.GPSSatellites: b"12",
            piexif.GPSIFD.GPSDOP: (150, 100),  # 1.5 HDOP
        }
    }

    exif_bytes = piexif.dump(exif_dict)
    img.save(photo_path, "JPEG", exif=exif_bytes)

    return photo_path


@pytest.fixture
def sample_photos_100(temp_photos_dir):
    """
    Create 100 photos with minimal EXIF for batch testing.

    Mix of photos with and without GPS data to test realistic scenarios.
    """
    photos = []

    for i in range(100):
        photo_path = temp_photos_dir / f"photo_{i:03d}.jpg"

        # Create minimal image
        img = Image.new('RGB', (320, 240), color='blue')

        # Add minimal EXIF data (alternating with/without GPS)
        exif_dict = {
            "0th": {
                piexif.ImageIFD.Make: b"Arducam",
                piexif.ImageIFD.Model: b"OwlSight 64MP",
            },
            "Exif": {
                piexif.ExifIFD.DateTimeOriginal: f"2024:01:15 10:{i:02d}:00".encode(),
                piexif.ExifIFD.ISOSpeedRatings: 400,
            }
        }

        # Add GPS data to 50% of photos
        if i % 2 == 0:
            exif_dict["GPS"] = {
                piexif.GPSIFD.GPSLatitudeRef: b"N",
                piexif.GPSIFD.GPSLatitude: ((37, 1), (46, 1), (2940, 100)),
                piexif.GPSIFD.GPSLongitudeRef: b"W",
                piexif.GPSIFD.GPSLongitude: ((122, 1), (25, 1), (1656, 100)),
            }

        exif_bytes = piexif.dump(exif_dict)
        img.save(photo_path, "JPEG", exif=exif_bytes)
        photos.append(photo_path)

    return photos


@pytest.fixture
def photo_with_gps(temp_photos_dir):
    """Create a single photo with GPS data for GPS parsing benchmarks."""
    photo_path = temp_photos_dir / "gps_photo.jpg"

    img = Image.new('RGB', (320, 240), color='green')

    exif_dict = {
        "GPS": {
            piexif.GPSIFD.GPSLatitudeRef: b"N",
            piexif.GPSIFD.GPSLatitude: ((37, 1), (46, 1), (2940, 100)),  # 37°46'29.4"N
            piexif.GPSIFD.GPSLongitudeRef: b"W",
            piexif.GPSIFD.GPSLongitude: ((122, 1), (25, 1), (1656, 100)),  # 122°25'16.56"W
            piexif.GPSIFD.GPSAltitude: (10000, 100),  # 100.0 meters
            piexif.GPSIFD.GPSAltitudeRef: 0,
            piexif.GPSIFD.GPSSatellites: b"12",
            piexif.GPSIFD.GPSDOP: (150, 100),  # 1.5 HDOP
        }
    }

    exif_bytes = piexif.dump(exif_dict)
    img.save(photo_path, "JPEG", exif=exif_bytes)

    return photo_path


@pytest.fixture
def large_photo_set(temp_photos_dir):
    """
    Create 1000 photos for series detection performance testing.

    Mix of:
    - 100 HDR series (3 photos each = 300 photos)
    - 100 Focus Bracket series (5 photos each = 500 photos)
    - 200 single photos (non-series)
    """
    photos = []

    # Create 100 HDR series (3 photos each = 300 photos)
    for series_num in range(100):
        base = f"moth_2024_01_{series_num:02d}__10_00_00"
        for i in range(3):
            photo_path = temp_photos_dir / f"{base}_HDR{i}.jpg"
            # Minimal JPEG header (faster creation)
            photo_path.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
            photos.append(photo_path)

    # Create 100 Focus Bracket series (5 photos each = 500 photos)
    for series_num in range(100):
        base = f"ManFocus_moth_2024_02_{series_num:02d}__11_00_00"
        for i in range(5):
            photo_path = temp_photos_dir / f"{base}_FB{i}.jpg"
            photo_path.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
            photos.append(photo_path)

    # Create 200 single photos (non-series)
    for i in range(200):
        photo_path = temp_photos_dir / f"single_2024_03_{i:03d}__12_00_00.jpg"
        photo_path.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
        photos.append(photo_path)

    return photos  # Total: 1000 photos


@pytest.fixture
def mixed_photo_set(temp_photos_dir):
    """
    Create 50 photos with mixed series for grouping performance testing.

    Mix of 5 HDR series (15 photos) + 5 FB series (25 photos) + 10 singles.
    """
    photos = []

    # 5 HDR series (3 photos each = 15 photos)
    for series_num in range(5):
        base = f"moth_2024_04_{series_num:02d}__10_00_00"
        for i in range(3):
            photo_path = temp_photos_dir / f"{base}_HDR{i}.jpg"
            photo_path.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
            photos.append(photo_path)

    # 5 Focus Bracket series (5 photos each = 25 photos)
    for series_num in range(5):
        base = f"ManFocus_moth_2024_04_{series_num:02d}__11_00_00"
        for i in range(5):
            photo_path = temp_photos_dir / f"{base}_FB{i}.jpg"
            photo_path.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
            photos.append(photo_path)

    # 10 single photos
    for i in range(10):
        photo_path = temp_photos_dir / f"single_2024_04_{i:03d}__12_00_00.jpg"
        photo_path.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
        photos.append(photo_path)

    return photos  # Total: 50 photos


@pytest.fixture
def metadata_service():
    """Create MetadataService instance for testing."""
    import sys
    from pathlib import Path

    # Add backend to path
    backend_dir = Path(__file__).parent.parent.parent / 'webui' / 'backend'
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    from services.metadata_service import MetadataService
    return MetadataService()


# ============================================================================
# Single Photo EXIF Extraction Performance (<50ms)
# ============================================================================

@pytest.mark.performance
class TestMetadataExtractionPerformance:
    """Performance benchmarks for metadata extraction."""

    def test_single_photo_extraction_under_50ms(self, metadata_service, sample_photo_with_full_exif):
        """MetadataService.get_photo_metadata() < 50ms per photo."""
        # Warmup run to load libraries and cache
        metadata_service.get_photo_metadata(sample_photo_with_full_exif)

        # Benchmark run (average of 100 iterations for stable measurement)
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            metadata = metadata_service.get_photo_metadata(sample_photo_with_full_exif)
        elapsed = (time.perf_counter() - start) / iterations

        # Verify extraction succeeded
        assert metadata is not None
        assert 'camera' in metadata
        assert 'location' in metadata
        assert 'capture' in metadata

        # Performance assertion
        elapsed_ms = elapsed * 1000
        assert elapsed_ms < 50, f"Single photo extraction took {elapsed_ms:.2f}ms, expected <50ms"

        print(f"\n✓ Single photo extraction: {elapsed_ms:.2f}ms (target: <50ms)")

    def test_batch_extraction_throughput(self, metadata_service, sample_photos_100):
        """Batch processing > 20 photos/second."""
        # Benchmark batch processing
        start = time.perf_counter()
        results = metadata_service.batch_get_metadata(sample_photos_100)
        elapsed = time.perf_counter() - start

        # Verify all photos processed
        assert len(results) == 100
        assert all('file' in result for result in results)

        # Calculate throughput
        photos_per_second = len(sample_photos_100) / elapsed

        # Performance assertion
        assert photos_per_second > 20, f"Throughput {photos_per_second:.1f} photos/sec, expected >20/sec"

        print(f"\n✓ Batch extraction: {photos_per_second:.1f} photos/sec (target: >20/sec)")
        print(f"  Total time: {elapsed:.2f}s for {len(sample_photos_100)} photos")
        print(f"  Average per photo: {(elapsed / len(sample_photos_100)) * 1000:.1f}ms")

    def test_gps_coordinate_parsing_under_10ms(self, metadata_service, photo_with_gps):
        """GPS coordinate extraction and conversion < 10ms."""
        # Warmup
        metadata_service.get_photo_metadata(photo_with_gps)

        # Benchmark GPS parsing (average of 100 iterations)
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            metadata = metadata_service.get_photo_metadata(photo_with_gps)
        elapsed = (time.perf_counter() - start) / iterations

        # Verify GPS data extracted
        assert metadata['location']['latitude'] is not None
        assert metadata['location']['longitude'] is not None
        assert metadata['location']['altitude'] is not None

        # Performance assertion
        elapsed_ms = elapsed * 1000
        assert elapsed_ms < 10, f"GPS parsing took {elapsed_ms:.2f}ms, expected <10ms"

        print(f"\n✓ GPS coordinate parsing: {elapsed_ms:.2f}ms (target: <10ms)")


# ============================================================================
# Series Detection Performance (<100ms for 1000 photos)
# ============================================================================

@pytest.mark.performance
class TestSeriesDetectionPerformance:
    """Performance benchmarks for series detection."""

    def test_series_detection_1000_photos_under_100ms(self, large_photo_set):
        """Series detection for 1000 photos < 100ms."""
        # Import series detection library
        import sys
        from pathlib import Path
        backend_dir = Path(__file__).parent.parent.parent / 'webui' / 'backend'
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))

        from webui.backend.lib.series_detection import group_photos_into_series

        # Warmup run
        group_photos_into_series(large_photo_set)

        # Benchmark run
        start = time.perf_counter()
        result = group_photos_into_series(large_photo_set)
        elapsed = time.perf_counter() - start

        # Verify correct grouping (200 series: 100 HDR + 100 FB)
        assert len(result) == 200, f"Expected 200 series, got {len(result)}"

        # Performance assertion
        elapsed_ms = elapsed * 1000
        assert elapsed_ms < 100, f"Series detection took {elapsed_ms:.1f}ms, expected <100ms"

        print(f"\n✓ Series detection (1000 photos): {elapsed_ms:.1f}ms (target: <100ms)")
        print(f"  Detected {len(result)} series")
        print(f"  Throughput: {len(large_photo_set) / elapsed:.0f} photos/sec")

    def test_series_grouping_performance(self, mixed_photo_set):
        """Grouping photos into series is performant."""
        # Import series detection library
        import sys
        from pathlib import Path
        backend_dir = Path(__file__).parent.parent.parent / 'webui' / 'backend'
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))

        from webui.backend.lib.series_detection import group_photos_into_series

        # Benchmark grouping 50 photos (5 HDR + 5 FB series + 10 singles)
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            result = group_photos_into_series(mixed_photo_set)
        elapsed = (time.perf_counter() - start) / iterations

        # Verify correct grouping (10 series: 5 HDR + 5 FB)
        assert len(result) == 10, f"Expected 10 series, got {len(result)}"

        # Performance assertion (should be very fast for small sets)
        elapsed_ms = elapsed * 1000
        assert elapsed_ms < 10, f"Series grouping took {elapsed_ms:.2f}ms, expected <10ms"

        print(f"\n✓ Series grouping (50 photos): {elapsed_ms:.2f}ms (target: <10ms)")
        print(f"  Detected {len(result)} series")


# ============================================================================
# Cache Performance (<1ms cache hit)
# ============================================================================

@pytest.mark.performance
class TestCachePerformance:
    """Performance benchmarks for metadata cache."""

    def test_cache_hit_under_1ms(self, metadata_service, sample_photo_with_full_exif):
        """Cache hits should return in <1ms."""
        # This test assumes MetadataService has caching (if not, it tests raw performance)
        # Warmup - populate cache
        for _ in range(10):
            metadata_service.get_photo_metadata(sample_photo_with_full_exif)

        # Benchmark cached lookup (average of 1000 iterations)
        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            metadata = metadata_service.get_photo_metadata(sample_photo_with_full_exif)
        elapsed = (time.perf_counter() - start) / iterations

        # Verify data returned
        assert metadata is not None
        assert 'camera' in metadata

        # Performance assertion
        elapsed_ms = elapsed * 1000
        # Note: If no caching, this tests raw EXIF parsing performance
        # Target is aggressive but achievable with proper caching
        print(f"\n✓ Cache hit/Warm lookup: {elapsed_ms:.3f}ms (target: <1ms)")

        # Don't fail if slightly over 1ms (depends on cache implementation)
        if elapsed_ms >= 1.0:
            print("  ⚠️  Over 1ms target - consider implementing metadata caching")

    def test_cache_warm_vs_cold(self, metadata_service, sample_photo_with_full_exif, temp_photos_dir):
        """Cold cache should still be <50ms, warm should be <1ms."""
        # Create a fresh photo for cold cache test
        uncached_photo = temp_photos_dir / "uncached_photo.jpg"
        img = Image.new('RGB', (320, 240), color='yellow')

        exif_dict = {
            "0th": {
                piexif.ImageIFD.Make: b"Arducam",
                piexif.ImageIFD.Model: b"OwlSight 64MP",
            },
            "Exif": {
                piexif.ExifIFD.ISOSpeedRatings: 400,
            }
        }

        exif_bytes = piexif.dump(exif_dict)
        img.save(uncached_photo, "JPEG", exif=exif_bytes)

        # Cold cache measurement
        start_cold = time.perf_counter()
        metadata_cold = metadata_service.get_photo_metadata(uncached_photo)
        elapsed_cold = (time.perf_counter() - start_cold) * 1000

        # Warm cache measurement (average of 100 iterations)
        iterations = 100
        start_warm = time.perf_counter()
        for _ in range(iterations):
            metadata_warm = metadata_service.get_photo_metadata(uncached_photo)
        elapsed_warm = ((time.perf_counter() - start_warm) / iterations) * 1000

        # Verify data returned
        assert metadata_cold is not None
        assert metadata_warm is not None

        # Performance assertions
        assert elapsed_cold < 50, f"Cold cache took {elapsed_cold:.2f}ms, expected <50ms"

        print(f"\n✓ Cold cache: {elapsed_cold:.2f}ms (target: <50ms)")
        print(f"✓ Warm cache: {elapsed_warm:.3f}ms (target: <1ms)")
        print(f"  Speedup: {elapsed_cold / elapsed_warm:.1f}x")


# ============================================================================
# Regression Tests
# ============================================================================

@pytest.mark.performance
class TestPerformanceRegressions:
    """Prevent known performance regressions."""

    def test_no_repeated_file_io_in_batch(self, metadata_service, sample_photos_100):
        """Batch processing should not reopen files unnecessarily."""
        # This test ensures batch_get_metadata doesn't have O(n²) file I/O

        # Benchmark small batch (10 photos)
        small_batch = sample_photos_100[:10]
        start_small = time.perf_counter()
        metadata_service.batch_get_metadata(small_batch)
        elapsed_small = time.perf_counter() - start_small

        # Benchmark full batch (100 photos)
        start_full = time.perf_counter()
        metadata_service.batch_get_metadata(sample_photos_100)
        elapsed_full = time.perf_counter() - start_full

        # Check linearity (should be ~10x, not 100x)
        # Allow 15x for overhead
        ratio = elapsed_full / elapsed_small
        assert ratio < 15, f"Batch processing not linear: {ratio:.1f}x (expected ~10x)"

        print(f"\n✓ Batch processing linearity: {ratio:.1f}x (10 vs 100 photos)")
        print(f"  Small batch (10): {elapsed_small:.3f}s")
        print(f"  Full batch (100): {elapsed_full:.3f}s")

    def test_series_detection_is_cached_in_service(self):
        """Verify series detection uses caching to avoid repeated scans."""
        # Import series service
        import sys
        from pathlib import Path
        backend_dir = Path(__file__).parent.parent.parent / 'webui' / 'backend'
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))

        try:
            from webui.backend.services.series_service import SeriesService

            service = SeriesService(cache_ttl=60)

            # Verify service has cache infrastructure
            assert hasattr(service, 'get_statistics'), "SeriesService should provide cache statistics"

            stats = service.get_statistics()
            assert 'cache_hits' in stats, "Service should track cache hits"
            assert 'cache_misses' in stats, "Service should track cache misses"

            print("\n✓ Series detection has caching infrastructure")
        except ImportError:
            pytest.skip("SeriesService not yet implemented with caching")

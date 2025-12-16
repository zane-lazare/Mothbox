"""
Unit tests for photo metadata aggregation library (Issue #200).

Tests the photo_aggregation module which aggregates metadata from multiple photos
for deployment form auto-fill functionality.

Architecture:
- Uses MetadataService for EXIF extraction
- Uses haversine_distance for GPS consistency checks
- Returns aggregated date range and GPS coordinates (if consistent)

Coverage target: 85%+
"""

import tempfile
from datetime import datetime
from pathlib import Path

import piexif
import pytest

# Explicitly import JPEG plugin to ensure it's loaded
from PIL import (
    Image,
    JpegImagePlugin,  # noqa: F401
)

from webui.backend.lib.photo_aggregation import (
    PhotoAggregation,
    aggregate_photo_metadata,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def temp_photo_dir():
    """Create temporary directory for test photos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def create_test_photo(
    path: Path,
    timestamp: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    altitude: float | None = None,
) -> Path:
    """
    Create a test JPEG photo with EXIF metadata.

    Args:
        path: Path for the photo file
        timestamp: ISO 8601 timestamp for DateTimeOriginal
        latitude: Decimal latitude
        longitude: Decimal longitude
        altitude: Altitude in meters

    Returns:
        Path to created photo
    """
    # Ensure PIL plugins are loaded (required for JPEG format)
    Image.init()

    # Create minimal JPEG image
    img = Image.new('RGB', (100, 100), color='red')

    # Build EXIF dictionary
    exif_dict = {
        '0th': {},
        'Exif': {},
        'GPS': {},
    }

    # Add timestamp if provided
    if timestamp:
        # Convert ISO 8601 to EXIF format (YYYY:MM:DD HH:MM:SS)
        dt = datetime.fromisoformat(timestamp)
        exif_time = dt.strftime('%Y:%m:%d %H:%M:%S')
        exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = exif_time.encode('ascii')

    # Add GPS if provided
    if latitude is not None and longitude is not None:
        # Use same GPS embedding logic as gps_exif_lib
        from webui.backend.lib.gps_exif_lib import decimal_to_dms

        # GPS version
        exif_dict['GPS'][piexif.GPSIFD.GPSVersionID] = (2, 3, 0, 0)

        # Latitude
        lat_dms, lat_ref = decimal_to_dms(latitude, is_latitude=True)
        exif_dict['GPS'][piexif.GPSIFD.GPSLatitude] = lat_dms
        exif_dict['GPS'][piexif.GPSIFD.GPSLatitudeRef] = lat_ref.encode('ascii')

        # Longitude
        lon_dms, lon_ref = decimal_to_dms(longitude, is_latitude=False)
        exif_dict['GPS'][piexif.GPSIFD.GPSLongitude] = lon_dms
        exif_dict['GPS'][piexif.GPSIFD.GPSLongitudeRef] = lon_ref.encode('ascii')

        # Altitude (if provided)
        if altitude is not None:
            altitude_abs = abs(altitude)
            altitude_rational = (int(round(altitude_abs * 100)), 100)
            exif_dict['GPS'][piexif.GPSIFD.GPSAltitude] = altitude_rational
            exif_dict['GPS'][piexif.GPSIFD.GPSAltitudeRef] = 1 if altitude < 0 else 0

    # Dump EXIF to bytes
    exif_bytes = piexif.dump(exif_dict)

    # Save image with EXIF
    img.save(path, 'JPEG', exif=exif_bytes)

    return path


# ============================================================================
# PhotoAggregation Dataclass Tests
# ============================================================================


def test_photo_aggregation_dataclass():
    """Test PhotoAggregation dataclass structure."""
    agg = PhotoAggregation(
        photo_count=5,
        date_start="2024-01-01",
        date_end="2024-01-31",
        latitude=37.7749,
        longitude=-122.4194,
        altitude=15.5,
        gps_consistent=True,
        gps_error=None,
        photos_with_gps=5,
        photos_with_timestamp=5,
    )

    assert agg.photo_count == 5
    assert agg.date_start == "2024-01-01"
    assert agg.date_end == "2024-01-31"
    assert agg.latitude == 37.7749
    assert agg.longitude == -122.4194
    assert agg.altitude == 15.5
    assert agg.gps_consistent is True
    assert agg.gps_error is None
    assert agg.photos_with_gps == 5
    assert agg.photos_with_timestamp == 5


# ============================================================================
# Empty and Edge Cases
# ============================================================================


def test_aggregate_empty_list():
    """Test aggregation of empty photo list."""
    result = aggregate_photo_metadata([])

    assert result.photo_count == 0
    assert result.date_start is None
    assert result.date_end is None
    assert result.latitude is None
    assert result.longitude is None
    assert result.altitude is None
    assert result.gps_consistent is False
    assert result.gps_error is None
    assert result.photos_with_gps == 0
    assert result.photos_with_timestamp == 0


def test_aggregate_nonexistent_photos():
    """Test aggregation with nonexistent photo paths."""
    fake_paths = [
        Path('/nonexistent/photo1.jpg'),
        Path('/nonexistent/photo2.jpg'),
    ]

    result = aggregate_photo_metadata(fake_paths)

    # Should return zero counts (graceful handling)
    assert result.photo_count == 0
    assert result.photos_with_gps == 0
    assert result.photos_with_timestamp == 0


# ============================================================================
# Single Photo Tests
# ============================================================================


def test_aggregate_single_photo_with_gps(temp_photo_dir):
    """Test aggregation of single photo with GPS metadata."""
    photo = create_test_photo(
        temp_photo_dir / "photo.jpg",
        timestamp="2024-01-15T12:30:00",
        latitude=37.7749,
        longitude=-122.4194,
        altitude=15.5,
    )

    result = aggregate_photo_metadata([photo])

    assert result.photo_count == 1
    assert result.date_start == "2024-01-15"
    assert result.date_end == "2024-01-15"
    assert result.latitude == pytest.approx(37.7749, abs=0.001)
    assert result.longitude == pytest.approx(-122.4194, abs=0.001)
    assert result.altitude == pytest.approx(15.5, abs=0.1)
    assert result.gps_consistent is True
    assert result.gps_error is None
    assert result.photos_with_gps == 1
    assert result.photos_with_timestamp == 1


def test_aggregate_single_photo_without_gps(temp_photo_dir):
    """Test aggregation of single photo without GPS metadata."""
    photo = create_test_photo(
        temp_photo_dir / "photo.jpg",
        timestamp="2024-01-15T12:30:00",
    )

    result = aggregate_photo_metadata([photo])

    assert result.photo_count == 1
    assert result.date_start == "2024-01-15"
    assert result.date_end == "2024-01-15"
    assert result.latitude is None
    assert result.longitude is None
    assert result.altitude is None
    assert result.gps_consistent is False
    assert result.gps_error is None
    assert result.photos_with_gps == 0
    assert result.photos_with_timestamp == 1


def test_aggregate_single_photo_without_timestamp(temp_photo_dir):
    """Test aggregation of single photo without timestamp."""
    photo = create_test_photo(
        temp_photo_dir / "photo.jpg",
        latitude=37.7749,
        longitude=-122.4194,
    )

    result = aggregate_photo_metadata([photo])

    assert result.photo_count == 1
    assert result.date_start is None
    assert result.date_end is None
    assert result.latitude == pytest.approx(37.7749, abs=0.001)
    assert result.longitude == pytest.approx(-122.4194, abs=0.001)
    assert result.gps_consistent is True
    assert result.photos_with_gps == 1
    assert result.photos_with_timestamp == 0


# ============================================================================
# GPS Consistency Tests
# ============================================================================


def test_aggregate_consistent_gps_within_tolerance(temp_photo_dir):
    """Test GPS consistency when all photos within tolerance (50m)."""
    # Create 3 photos within ~40m of each other
    # Using small coordinate changes that result in <50m distances
    photo1 = create_test_photo(
        temp_photo_dir / "photo1.jpg",
        timestamp="2024-01-15T12:00:00",
        latitude=37.7749,
        longitude=-122.4194,
        altitude=15.0,
    )
    photo2 = create_test_photo(
        temp_photo_dir / "photo2.jpg",
        timestamp="2024-01-15T12:15:00",
        latitude=37.7750,  # ~11m north
        longitude=-122.4194,
        altitude=15.5,
    )
    photo3 = create_test_photo(
        temp_photo_dir / "photo3.jpg",
        timestamp="2024-01-15T12:30:00",
        latitude=37.7751,  # ~22m north of first
        longitude=-122.4194,
        altitude=16.0,
    )

    result = aggregate_photo_metadata([photo1, photo2, photo3], tolerance_m=50.0)

    assert result.photo_count == 3
    assert result.gps_consistent is True
    assert result.gps_error is None
    assert result.latitude is not None
    assert result.longitude is not None
    assert result.altitude is not None  # Should use mean or median
    assert result.photos_with_gps == 3


def test_aggregate_inconsistent_gps_returns_error(temp_photo_dir):
    """Test GPS inconsistency when photos >50m apart returns error."""
    # Create photos far apart (>50m)
    photo1 = create_test_photo(
        temp_photo_dir / "photo1.jpg",
        timestamp="2024-01-15T12:00:00",
        latitude=37.7749,  # San Francisco
        longitude=-122.4194,
    )
    photo2 = create_test_photo(
        temp_photo_dir / "photo2.jpg",
        timestamp="2024-01-15T12:30:00",
        latitude=37.7800,  # ~550m north
        longitude=-122.4194,
    )

    result = aggregate_photo_metadata([photo1, photo2], tolerance_m=50.0)

    assert result.photo_count == 2
    assert result.gps_consistent is False
    assert result.gps_error is not None
    assert "inconsistent" in result.gps_error.lower() or "differ" in result.gps_error.lower()
    # GPS coordinates should be None when inconsistent
    assert result.latitude is None
    assert result.longitude is None
    assert result.altitude is None
    assert result.photos_with_gps == 2


def test_aggregate_custom_tolerance(temp_photo_dir):
    """Test custom GPS tolerance parameter."""
    # Create photos ~100m apart
    photo1 = create_test_photo(
        temp_photo_dir / "photo1.jpg",
        latitude=37.7749,
        longitude=-122.4194,
    )
    photo2 = create_test_photo(
        temp_photo_dir / "photo2.jpg",
        latitude=37.7758,  # ~100m north
        longitude=-122.4194,
    )

    # Should be consistent with 150m tolerance
    result_loose = aggregate_photo_metadata([photo1, photo2], tolerance_m=150.0)
    assert result_loose.gps_consistent is True
    assert result_loose.latitude is not None

    # Should be inconsistent with 50m tolerance
    result_strict = aggregate_photo_metadata([photo1, photo2], tolerance_m=50.0)
    assert result_strict.gps_consistent is False
    assert result_strict.latitude is None


# ============================================================================
# Date Range Tests
# ============================================================================


def test_aggregate_date_range_min_max(temp_photo_dir):
    """Test date range extraction (earliest and latest)."""
    photo1 = create_test_photo(
        temp_photo_dir / "photo1.jpg",
        timestamp="2024-01-15T12:00:00",
    )
    photo2 = create_test_photo(
        temp_photo_dir / "photo2.jpg",
        timestamp="2024-02-20T14:30:00",
    )
    photo3 = create_test_photo(
        temp_photo_dir / "photo3.jpg",
        timestamp="2024-01-10T08:00:00",  # Earliest
    )
    photo4 = create_test_photo(
        temp_photo_dir / "photo4.jpg",
        timestamp="2024-03-05T18:00:00",  # Latest
    )

    result = aggregate_photo_metadata([photo1, photo2, photo3, photo4])

    assert result.date_start == "2024-01-10"  # Earliest
    assert result.date_end == "2024-03-05"    # Latest
    assert result.photos_with_timestamp == 4


def test_aggregate_date_range_same_day(temp_photo_dir):
    """Test date range when all photos from same day."""
    photo1 = create_test_photo(
        temp_photo_dir / "photo1.jpg",
        timestamp="2024-01-15T08:00:00",
    )
    photo2 = create_test_photo(
        temp_photo_dir / "photo2.jpg",
        timestamp="2024-01-15T12:00:00",
    )
    photo3 = create_test_photo(
        temp_photo_dir / "photo3.jpg",
        timestamp="2024-01-15T18:00:00",
    )

    result = aggregate_photo_metadata([photo1, photo2, photo3])

    assert result.date_start == "2024-01-15"
    assert result.date_end == "2024-01-15"


# ============================================================================
# Mixed GPS Coverage Tests
# ============================================================================


def test_aggregate_mixed_gps_coverage(temp_photo_dir):
    """Test aggregation when some photos have GPS and some don't."""
    # 2 photos with GPS (consistent)
    photo1 = create_test_photo(
        temp_photo_dir / "photo1.jpg",
        timestamp="2024-01-15T12:00:00",
        latitude=37.7749,
        longitude=-122.4194,
    )
    photo2 = create_test_photo(
        temp_photo_dir / "photo2.jpg",
        timestamp="2024-01-15T12:30:00",
        latitude=37.7750,  # ~11m north
        longitude=-122.4194,
    )
    # 1 photo without GPS
    photo3 = create_test_photo(
        temp_photo_dir / "photo3.jpg",
        timestamp="2024-01-15T13:00:00",
    )

    result = aggregate_photo_metadata([photo1, photo2, photo3])

    assert result.photo_count == 3
    assert result.photos_with_gps == 2
    assert result.photos_with_timestamp == 3
    # GPS should be consistent among photos that have it
    assert result.gps_consistent is True
    assert result.latitude is not None
    assert result.longitude is not None


def test_aggregate_all_photos_missing_gps(temp_photo_dir):
    """Test aggregation when no photos have GPS."""
    photo1 = create_test_photo(
        temp_photo_dir / "photo1.jpg",
        timestamp="2024-01-15T12:00:00",
    )
    photo2 = create_test_photo(
        temp_photo_dir / "photo2.jpg",
        timestamp="2024-01-15T12:30:00",
    )

    result = aggregate_photo_metadata([photo1, photo2])

    assert result.photo_count == 2
    assert result.photos_with_gps == 0
    assert result.latitude is None
    assert result.longitude is None
    assert result.gps_consistent is False
    assert result.gps_error is None  # Not an error, just no GPS


# ============================================================================
# Missing Metadata Handling
# ============================================================================


def test_aggregate_handles_missing_metadata(temp_photo_dir):
    """Test graceful handling of photos with missing EXIF."""
    # Create photos with various missing metadata
    photo1 = create_test_photo(
        temp_photo_dir / "photo1.jpg",
        timestamp="2024-01-15T12:00:00",
        latitude=37.7749,
        longitude=-122.4194,
    )
    # Photo with no EXIF at all
    photo2 = temp_photo_dir / "photo2.jpg"
    img = Image.new('RGB', (100, 100), color='blue')
    img.save(photo2, 'JPEG')

    photo3 = create_test_photo(
        temp_photo_dir / "photo3.jpg",
        timestamp="2024-01-15T13:00:00",
    )

    result = aggregate_photo_metadata([photo1, photo2, photo3])

    # Should process all 3 photos
    assert result.photo_count == 3
    # Only 2 have timestamps
    assert result.photos_with_timestamp == 2
    # Only 1 has GPS
    assert result.photos_with_gps == 1


def test_aggregate_handles_corrupted_exif(temp_photo_dir):
    """Test graceful handling of photos with corrupted EXIF."""
    # Create photo with valid EXIF
    photo1 = create_test_photo(
        temp_photo_dir / "photo1.jpg",
        timestamp="2024-01-15T12:00:00",
        latitude=37.7749,
        longitude=-122.4194,
    )

    # Create photo with corrupted EXIF (manually write invalid data)
    photo2 = temp_photo_dir / "photo2.jpg"
    img = Image.new('RGB', (100, 100), color='green')
    img.save(photo2, 'JPEG')
    # Write invalid EXIF data
    with open(photo2, 'ab') as f:
        f.write(b'\xff\xe1\x00\x10Exif\x00\x00INVALID')

    # Should not crash, should handle gracefully
    result = aggregate_photo_metadata([photo1, photo2])

    # At least photo1 should be processed
    assert result.photo_count >= 1
    assert result.photos_with_gps >= 1


# ============================================================================
# Altitude Aggregation Tests
# ============================================================================


def test_aggregate_altitude_from_gps(temp_photo_dir):
    """Test altitude aggregation when photos have altitude."""
    photo1 = create_test_photo(
        temp_photo_dir / "photo1.jpg",
        latitude=37.7749,
        longitude=-122.4194,
        altitude=15.0,
    )
    photo2 = create_test_photo(
        temp_photo_dir / "photo2.jpg",
        latitude=37.7750,
        longitude=-122.4194,
        altitude=15.5,
    )
    photo3 = create_test_photo(
        temp_photo_dir / "photo3.jpg",
        latitude=37.7751,
        longitude=-122.4194,
        altitude=16.0,
    )

    result = aggregate_photo_metadata([photo1, photo2, photo3])

    # Should aggregate altitude (mean, median, or representative value)
    assert result.altitude is not None
    assert 15.0 <= result.altitude <= 16.0


def test_aggregate_mixed_altitude_coverage(temp_photo_dir):
    """Test altitude when some photos have it and some don't."""
    photo1 = create_test_photo(
        temp_photo_dir / "photo1.jpg",
        latitude=37.7749,
        longitude=-122.4194,
        altitude=15.0,
    )
    photo2 = create_test_photo(
        temp_photo_dir / "photo2.jpg",
        latitude=37.7750,
        longitude=-122.4194,
        # No altitude
    )

    result = aggregate_photo_metadata([photo1, photo2])

    # Should still return altitude from photo1
    assert result.altitude is not None


# ============================================================================
# Large Dataset Tests
# ============================================================================


def test_aggregate_large_dataset(temp_photo_dir):
    """Test aggregation performance with larger dataset."""
    photos = []

    # Create 50 photos with consistent GPS
    for i in range(50):
        photo = create_test_photo(
            temp_photo_dir / f"photo{i:03d}.jpg",
            timestamp=f"2024-01-{(i % 28) + 1:02d}T12:00:00",
            latitude=37.7749 + (i * 0.00001),  # Small GPS variations
            longitude=-122.4194,
            altitude=15.0 + (i * 0.1),
        )
        photos.append(photo)

    result = aggregate_photo_metadata(photos, tolerance_m=100.0)

    assert result.photo_count == 50
    assert result.photos_with_gps == 50
    assert result.photos_with_timestamp == 50
    assert result.gps_consistent is True
    assert result.latitude is not None
    assert result.longitude is not None
    assert result.altitude is not None


# ============================================================================
# Zero Tolerance Edge Case
# ============================================================================


def test_aggregate_zero_tolerance(temp_photo_dir):
    """Test zero tolerance (exact GPS match required)."""
    # Two photos with identical GPS
    photo1 = create_test_photo(
        temp_photo_dir / "photo1.jpg",
        latitude=37.7749,
        longitude=-122.4194,
    )
    photo2 = create_test_photo(
        temp_photo_dir / "photo2.jpg",
        latitude=37.7749,
        longitude=-122.4194,
    )

    result = aggregate_photo_metadata([photo1, photo2], tolerance_m=0.0)

    # Should be consistent (0m distance)
    assert result.gps_consistent is True
    assert result.latitude is not None


def test_aggregate_zero_tolerance_different_coords(temp_photo_dir):
    """Test zero tolerance with different coordinates."""
    photo1 = create_test_photo(
        temp_photo_dir / "photo1.jpg",
        latitude=37.7749,
        longitude=-122.4194,
    )
    photo2 = create_test_photo(
        temp_photo_dir / "photo2.jpg",
        latitude=37.7750,  # Different
        longitude=-122.4194,
    )

    result = aggregate_photo_metadata([photo1, photo2], tolerance_m=0.0)

    # Should be inconsistent (>0m distance)
    assert result.gps_consistent is False
    assert result.latitude is None

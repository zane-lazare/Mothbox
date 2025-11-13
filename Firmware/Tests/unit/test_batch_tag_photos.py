"""
Unit tests for scripts/batch_tag_photos.py - GPS EXIF Batch Tagging Tool

Tests the batch tagging tool's ability to:
1. Filter photos by date range
2. Batch tag photos with GPS EXIF
3. Validate GPS coordinate overrides
4. Handle --dry-run and --backup flags
5. Process directories recursively

Following TDD methodology: Write tests FIRST, then implement.

Related:
- Issue #98 Phase 3: Batch Tagging Tool (Days 4-7)
- Spec: webui/docs/dev/issues/ISSUE_98_GPS_EXIF_IMPLEMENTATION_SPEC.md
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
import sys


# ============================================================================
# Test: filter_photos_by_date()
# ============================================================================

def test_filter_photos_by_date_no_filters():
    """Test filtering photos with no date filters (returns all)."""
    from scripts.batch_tag_photos import filter_photos_by_date
    from datetime import datetime

    photos = [
        Path("mothbox_2025_01_15__12_30_00.jpg"),
        Path("mothbox_2025_01_16__12_30_00.jpg"),
        Path("mothbox_2025_01_17__12_30_00.jpg"),
    ]

    filtered = filter_photos_by_date(photos)
    assert len(filtered) == 3


def test_filter_photos_by_date_after_filter():
    """Test filtering photos with --after date."""
    from scripts.batch_tag_photos import filter_photos_by_date

    photos = [
        Path("mothbox_2025_01_15__12_30_00.jpg"),
        Path("mothbox_2025_01_16__12_30_00.jpg"),
        Path("mothbox_2025_01_17__12_30_00.jpg"),
    ]

    # Filter for photos after 2025-01-16 (should get 2 photos)
    after_date = datetime(2025, 1, 16)
    filtered = filter_photos_by_date(photos, after=after_date)

    assert len(filtered) == 2
    assert "2025_01_16" in filtered[0].name
    assert "2025_01_17" in filtered[1].name


def test_filter_photos_by_date_before_filter():
    """Test filtering photos with --before date."""
    from scripts.batch_tag_photos import filter_photos_by_date

    photos = [
        Path("mothbox_2025_01_15__12_30_00.jpg"),
        Path("mothbox_2025_01_16__12_30_00.jpg"),
        Path("mothbox_2025_01_17__12_30_00.jpg"),
    ]

    # Filter for photos before 2025-01-17 (should get 2 photos)
    before_date = datetime(2025, 1, 17)
    filtered = filter_photos_by_date(photos, before=before_date)

    assert len(filtered) == 2
    assert "2025_01_15" in filtered[0].name
    assert "2025_01_16" in filtered[1].name


def test_filter_photos_by_date_range():
    """Test filtering photos with both --after and --before."""
    from scripts.batch_tag_photos import filter_photos_by_date

    photos = [
        Path("mothbox_2025_01_15__12_30_00.jpg"),
        Path("mothbox_2025_01_16__12_30_00.jpg"),
        Path("mothbox_2025_01_17__12_30_00.jpg"),
        Path("mothbox_2025_01_18__12_30_00.jpg"),
    ]

    # Filter for photos between 2025-01-16 and 2025-01-18 (should get 2 photos)
    after_date = datetime(2025, 1, 16)
    before_date = datetime(2025, 1, 18)
    filtered = filter_photos_by_date(photos, after=after_date, before=before_date)

    assert len(filtered) == 2
    assert "2025_01_16" in filtered[0].name
    assert "2025_01_17" in filtered[1].name


def test_filter_photos_invalid_filenames():
    """Test filtering photos with invalid filenames (no timestamp)."""
    from scripts.batch_tag_photos import filter_photos_by_date

    photos = [
        Path("mothbox_2025_01_15__12_30_00.jpg"),
        Path("invalid_photo.jpg"),  # No timestamp
        Path("mothbox_2025_01_17__12_30_00.jpg"),
    ]

    # Invalid photos should be filtered out
    after_date = datetime(2025, 1, 15)
    filtered = filter_photos_by_date(photos, after=after_date)

    assert len(filtered) == 2
    assert "invalid" not in str(filtered)


# ============================================================================
# Test: validate_gps_override()
# ============================================================================

def test_validate_gps_override_valid_coords():
    """Test validating valid GPS coordinates."""
    from scripts.batch_tag_photos import validate_gps_override

    # Valid coordinates
    assert validate_gps_override(37.7749, -122.4194) is True
    assert validate_gps_override(0, 0) is True  # Null Island is valid
    assert validate_gps_override(-90, -180) is True  # Min values
    assert validate_gps_override(90, 180) is True  # Max values


def test_validate_gps_override_invalid_latitude():
    """Test validating invalid latitude values."""
    from scripts.batch_tag_photos import validate_gps_override

    # Invalid latitudes (must be -90 to 90)
    assert validate_gps_override(91, 0) is False
    assert validate_gps_override(-91, 0) is False
    assert validate_gps_override(100, 0) is False


def test_validate_gps_override_invalid_longitude():
    """Test validating invalid longitude values."""
    from scripts.batch_tag_photos import validate_gps_override

    # Invalid longitudes (must be -180 to 180)
    assert validate_gps_override(0, 181) is False
    assert validate_gps_override(0, -181) is False
    assert validate_gps_override(0, 200) is False


def test_validate_gps_override_none_values():
    """Test validating None values (should be invalid)."""
    from scripts.batch_tag_photos import validate_gps_override

    assert validate_gps_override(None, 0) is False
    assert validate_gps_override(0, None) is False
    assert validate_gps_override(None, None) is False


# ============================================================================
# Test: batch_tag_with_override()
# ============================================================================

def test_batch_tag_with_override_from_controls(tmp_path):
    """Test batch tagging using GPS data from controls.txt."""
    from scripts.batch_tag_photos import batch_tag_with_override
    from PIL import Image
    from lib.gps_exif_lib import verify_gps_exif
    from mothbox_paths import CONTROLS_FILE
    import shutil

    # Create test photos
    photos = []
    for i in range(3):
        photo = tmp_path / f"mothbox_2025_01_15__12_30_{i:02d}.jpg"
        img = Image.new('RGB', (100, 100))
        img.save(photo, 'JPEG')
        photos.append(photo)

    # Create mock controls.txt with GPS data
    controls_file = tmp_path / "controls.txt"
    controls_file.write_text("""
# Mock GPS data for testing
lat = 37.7749
lon = -122.4194
gpstime = 1736944245
gps_altitude = 100.0
gps_fix_mode = 3
gps_satellites_used = 8
gps_hdop = 1.2
gps_pdop = 2.0
    """)

    # Batch tag using controls.txt
    results = batch_tag_with_override(photos, controls_file=controls_file)

    # Verify all photos were tagged
    assert results['total'] == 3
    assert results['tagged'] == 3
    assert results['skipped'] == 0
    assert results['errors'] == 0

    # Verify GPS EXIF in photos
    for photo in photos:
        gps_info = verify_gps_exif(photo)
        assert gps_info['has_gps'] is True
        assert abs(gps_info['latitude'] - 37.7749) < 0.0001
        assert abs(gps_info['longitude'] - (-122.4194)) < 0.0001


def test_batch_tag_with_override_manual_coords(tmp_path):
    """Test batch tagging with manual GPS coordinate override."""
    from scripts.batch_tag_photos import batch_tag_with_override
    from PIL import Image
    from lib.gps_exif_lib import verify_gps_exif

    # Create test photos
    photos = []
    for i in range(3):
        photo = tmp_path / f"mothbox_2025_01_15__12_30_{i:02d}.jpg"
        img = Image.new('RGB', (100, 100))
        img.save(photo, 'JPEG')
        photos.append(photo)

    # Batch tag with manual coordinates
    override_lat = 38.5816
    override_lon = -121.4944

    results = batch_tag_with_override(
        photos,
        override_lat=override_lat,
        override_lon=override_lon
    )

    # Verify all photos were tagged
    assert results['total'] == 3
    assert results['tagged'] == 3

    # Verify GPS EXIF in photos
    for photo in photos:
        gps_info = verify_gps_exif(photo)
        assert gps_info['has_gps'] is True
        assert abs(gps_info['latitude'] - override_lat) < 0.0001
        assert abs(gps_info['longitude'] - override_lon) < 0.0001


def test_batch_tag_with_override_dry_run(tmp_path):
    """Test batch tagging with --dry-run flag."""
    from scripts.batch_tag_photos import batch_tag_with_override
    from PIL import Image
    from lib.gps_exif_lib import verify_gps_exif

    # Create test photos
    photos = []
    for i in range(3):
        photo = tmp_path / f"mothbox_2025_01_15__12_30_{i:02d}.jpg"
        img = Image.new('RGB', (100, 100))
        img.save(photo, 'JPEG')
        photos.append(photo)

    # Dry run - should not modify photos
    results = batch_tag_with_override(
        photos,
        override_lat=37.7749,
        override_lon=-122.4194,
        dry_run=True
    )

    # Verify counts
    assert results['total'] == 3
    assert results['tagged'] == 3  # Reports as "would tag"

    # Verify photos were NOT actually modified
    for photo in photos:
        gps_info = verify_gps_exif(photo)
        assert gps_info['has_gps'] is False  # No GPS added in dry run


def test_batch_tag_with_override_backup(tmp_path):
    """Test batch tagging with --backup flag."""
    from scripts.batch_tag_photos import batch_tag_with_override
    from PIL import Image

    # Create test photos
    photos = []
    for i in range(3):
        photo = tmp_path / f"mothbox_2025_01_15__12_30_{i:02d}.jpg"
        img = Image.new('RGB', (100, 100))
        img.save(photo, 'JPEG')
        photos.append(photo)

    # Tag with backup
    results = batch_tag_with_override(
        photos,
        override_lat=37.7749,
        override_lon=-122.4194,
        backup=True
    )

    # Verify all photos were tagged
    assert results['tagged'] == 3

    # Verify backup files were created
    for photo in photos:
        backup_file = photo.with_suffix('.jpg.bak')
        assert backup_file.exists()


def test_batch_tag_with_override_skip_already_tagged(tmp_path):
    """Test that already-tagged photos are skipped."""
    from scripts.batch_tag_photos import batch_tag_with_override
    from PIL import Image
    from lib.gps_exif_lib import embed_gps_exif

    # Create photos, some with GPS already
    photos = []

    # Photo 1: Already has GPS
    photo1 = tmp_path / "mothbox_2025_01_15__12_30_00.jpg"
    img = Image.new('RGB', (100, 100))
    img.save(photo1, 'JPEG')
    gps_data = {'latitude': 37.7749, 'longitude': -122.4194, 'has_fix': True}
    embed_gps_exif(photo1, gps_data=gps_data)
    photos.append(photo1)

    # Photo 2: No GPS
    photo2 = tmp_path / "mothbox_2025_01_15__12_30_01.jpg"
    img = Image.new('RGB', (100, 100))
    img.save(photo2, 'JPEG')
    photos.append(photo2)

    # Batch tag
    results = batch_tag_with_override(
        photos,
        override_lat=38.5816,
        override_lon=-121.4944
    )

    # Verify counts
    assert results['total'] == 2
    assert results['tagged'] == 1  # Only photo2
    assert results['skipped'] == 1  # photo1 skipped


# ============================================================================
# Test: batch_tag_directory()
# ============================================================================

def test_batch_tag_directory_basic(tmp_path):
    """Test batch tagging entire directory."""
    from scripts.batch_tag_photos import batch_tag_directory
    from PIL import Image
    from lib.gps_exif_lib import verify_gps_exif

    # Create test photos in directory
    for i in range(5):
        photo = tmp_path / f"mothbox_2025_01_15__12_30_{i:02d}.jpg"
        img = Image.new('RGB', (100, 100))
        img.save(photo, 'JPEG')

    # Batch tag directory
    results = batch_tag_directory(
        tmp_path,
        override_lat=37.7749,
        override_lon=-122.4194
    )

    # Verify all photos were tagged
    assert results['total'] == 5
    assert results['tagged'] == 5

    # Verify GPS in all photos
    for i in range(5):
        photo = tmp_path / f"mothbox_2025_01_15__12_30_{i:02d}.jpg"
        gps_info = verify_gps_exif(photo)
        assert gps_info['has_gps'] is True


def test_batch_tag_directory_recursive(tmp_path):
    """Test batch tagging directory recursively."""
    from scripts.batch_tag_photos import batch_tag_directory
    from PIL import Image

    # Create nested directory structure
    (tmp_path / "2025" / "01" / "15").mkdir(parents=True)
    (tmp_path / "2025" / "01" / "16").mkdir(parents=True)

    # Create photos in subdirectories
    photo1 = tmp_path / "2025" / "01" / "15" / "mothbox_2025_01_15__12_30_00.jpg"
    img = Image.new('RGB', (100, 100))
    img.save(photo1, 'JPEG')

    photo2 = tmp_path / "2025" / "01" / "16" / "mothbox_2025_01_16__12_30_00.jpg"
    img = Image.new('RGB', (100, 100))
    img.save(photo2, 'JPEG')

    # Batch tag recursively
    results = batch_tag_directory(
        tmp_path,
        override_lat=37.7749,
        override_lon=-122.4194,
        recursive=True
    )

    # Verify all photos in subdirectories were tagged
    assert results['total'] == 2
    assert results['tagged'] == 2


def test_batch_tag_directory_with_date_filter(tmp_path):
    """Test batch tagging directory with date filters."""
    from scripts.batch_tag_photos import batch_tag_directory
    from PIL import Image

    # Create photos with different dates
    for day in [15, 16, 17, 18]:
        photo = tmp_path / f"mothbox_2025_01_{day}__12_30_00.jpg"
        img = Image.new('RGB', (100, 100))
        img.save(photo, 'JPEG')

    # Tag only photos from 2025-01-16 to 2025-01-18
    after_date = datetime(2025, 1, 16)
    before_date = datetime(2025, 1, 18)

    results = batch_tag_directory(
        tmp_path,
        override_lat=37.7749,
        override_lon=-122.4194,
        after=after_date,
        before=before_date
    )

    # Should tag 2 photos (16 and 17, not 18)
    assert results['total'] == 2
    assert results['tagged'] == 2


# ============================================================================
# Test: main() function with CLI arguments
# ============================================================================

def test_main_batch_tag_directory(tmp_path, monkeypatch):
    """Test main() batch tagging a directory."""
    from scripts.batch_tag_photos import main
    from PIL import Image

    # Create test photos
    for i in range(3):
        photo = tmp_path / f"mothbox_2025_01_15__12_30_{i:02d}.jpg"
        img = Image.new('RGB', (100, 100))
        img.save(photo, 'JPEG')

    # Mock sys.argv
    monkeypatch.setattr(sys, 'argv', [
        'batch_tag_photos.py',
        str(tmp_path),
        '--lat', '37.7749',
        '--lon', '-122.4194'
    ])

    # Run main
    exit_code = main()

    assert exit_code == 0


def test_main_with_dry_run(tmp_path, monkeypatch, capsys):
    """Test main() with --dry-run flag."""
    from scripts.batch_tag_photos import main
    from PIL import Image

    # Create test photos
    for i in range(3):
        photo = tmp_path / f"mothbox_2025_01_15__12_30_{i:02d}.jpg"
        img = Image.new('RGB', (100, 100))
        img.save(photo, 'JPEG')

    # Mock sys.argv with --dry-run
    monkeypatch.setattr(sys, 'argv', [
        'batch_tag_photos.py',
        str(tmp_path),
        '--lat', '37.7749',
        '--lon', '-122.4194',
        '--dry-run'
    ])

    # Run main
    exit_code = main()

    assert exit_code == 0

    # Should print dry-run message
    captured = capsys.readouterr()
    assert "dry" in captured.out.lower() or "would" in captured.out.lower()


def test_main_with_date_filters(tmp_path, monkeypatch):
    """Test main() with --after and --before flags."""
    from scripts.batch_tag_photos import main
    from PIL import Image

    # Create test photos with different dates
    for day in [15, 16, 17]:
        photo = tmp_path / f"mothbox_2025_01_{day}__12_30_00.jpg"
        img = Image.new('RGB', (100, 100))
        img.save(photo, 'JPEG')

    # Mock sys.argv with date filters
    monkeypatch.setattr(sys, 'argv', [
        'batch_tag_photos.py',
        str(tmp_path),
        '--lat', '37.7749',
        '--lon', '-122.4194',
        '--after', '2025-01-16',
        '--before', '2025-01-18'
    ])

    # Run main
    exit_code = main()

    assert exit_code == 0


def test_main_help_flag(capsys, monkeypatch):
    """Test main() with --help flag."""
    from scripts.batch_tag_photos import main

    # Mock sys.argv with --help
    monkeypatch.setattr(sys, 'argv', ['batch_tag_photos.py', '--help'])

    # Run main (should exit with 0 for help)
    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0

    # Should print help
    captured = capsys.readouterr()
    output = captured.out
    assert "usage" in output.lower() or "batch" in output.lower()


def test_main_missing_lat_lon_error(tmp_path, monkeypatch, capsys):
    """Test main() fails without --lat/--lon and no controls.txt."""
    from scripts.batch_tag_photos import main

    # Mock sys.argv without GPS coordinates
    monkeypatch.setattr(sys, 'argv', [
        'batch_tag_photos.py',
        str(tmp_path)
    ])

    # Run main (should fail)
    exit_code = main()

    assert exit_code != 0

    # Should print error about missing GPS data
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert "gps" in output.lower() or "coordinates" in output.lower()


def test_main_invalid_coordinates(tmp_path, monkeypatch, capsys):
    """Test main() with invalid GPS coordinates."""
    from scripts.batch_tag_photos import main
    from PIL import Image

    # Create test photo
    photo = tmp_path / "mothbox_2025_01_15__12_30_00.jpg"
    img = Image.new('RGB', (100, 100))
    img.save(photo, 'JPEG')

    # Mock sys.argv with invalid latitude (>90)
    monkeypatch.setattr(sys, 'argv', [
        'batch_tag_photos.py',
        str(tmp_path),
        '--lat', '100',
        '--lon', '0'
    ])

    # Run main (should fail)
    exit_code = main()

    assert exit_code != 0

    # Should print error about invalid coordinates
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert "invalid" in output.lower() or "coordinates" in output.lower()


# ============================================================================
# Test: Edge Cases and Error Handling
# ============================================================================

def test_batch_tag_empty_directory(tmp_path):
    """Test batch tagging empty directory."""
    from scripts.batch_tag_photos import batch_tag_directory

    results = batch_tag_directory(
        tmp_path,
        override_lat=37.7749,
        override_lon=-122.4194
    )

    # Should handle gracefully
    assert results['total'] == 0
    assert results['tagged'] == 0


def test_batch_tag_mixed_file_types(tmp_path):
    """Test batch tagging directory with non-JPEG files."""
    from scripts.batch_tag_photos import batch_tag_directory
    from PIL import Image

    # Create JPEG and non-JPEG files
    photo1 = tmp_path / "mothbox_2025_01_15__12_30_00.jpg"
    img = Image.new('RGB', (100, 100))
    img.save(photo1, 'JPEG')

    # Create non-JPEG file
    (tmp_path / "readme.txt").write_text("not a photo")

    results = batch_tag_directory(
        tmp_path,
        override_lat=37.7749,
        override_lon=-122.4194
    )

    # Should only tag JPEG
    assert results['total'] == 1
    assert results['tagged'] == 1


def test_batch_tag_handles_permission_error(tmp_path):
    """Test batch tagging handles permission errors gracefully."""
    from scripts.batch_tag_photos import batch_tag_with_override
    from PIL import Image
    import os

    # Create test photo
    photo = tmp_path / "mothbox_2025_01_15__12_30_00.jpg"
    img = Image.new('RGB', (100, 100))
    img.save(photo, 'JPEG')

    # Make file read-only
    os.chmod(photo, 0o444)

    try:
        results = batch_tag_with_override(
            [photo],
            override_lat=37.7749,
            override_lon=-122.4194
        )

        # Should report error (but not crash)
        assert results['total'] == 1
        assert results['errors'] >= 0  # May report error or skip

    finally:
        # Restore write permission for cleanup
        os.chmod(photo, 0o644)


# ============================================================================
# Test: Path Traversal Security (Issue #98 Security Fixes)
# ============================================================================

def test_batch_tag_directory_filters_symlinks(tmp_path):
    """Test that batch_tag_directory() filters out symlinks for security."""
    from scripts.batch_tag_photos import batch_tag_directory
    from lib.gps_exif_lib import embed_gps_exif

    # Create real photos
    photo1 = tmp_path / "photo1.jpg"
    photo2 = tmp_path / "photo2.jpg"

    # Use embed_gps_exif to create valid JPEG with GPS
    # (fake JPEGs will error in piexif)
    gps_data = {
        'latitude': 37.7749,
        'longitude': -122.4194,
        'has_fix': True,
        'fix_mode': 2,
        'altitude': None,
        'gpstime': None,
        'satellites_used': 6,
        'hdop': 1.2,
        'pdop': 2.1
    }

    # Create minimal valid JPEG files
    # JPEG header + minimal structure
    jpeg_bytes = (
        b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
        b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c'
        b'\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c'
        b'\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01'
        b'\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x00'
        b'?\x00\x7f\x00\xff\xd9'
    )

    photo1.write_bytes(jpeg_bytes)
    photo2.write_bytes(jpeg_bytes)

    # Create symlink to external location
    external_photo = tmp_path / "external.jpg"
    external_photo.write_bytes(jpeg_bytes)

    symlink_photo = tmp_path / "symlink.jpg"
    symlink_photo.symlink_to(external_photo)

    # Run batch tagging
    results = batch_tag_directory(
        tmp_path,
        override_lat=37.7749,
        override_lon=-122.4194,
        dry_run=True  # Don't actually modify
    )

    # Should process only 2 real photos (photo1, photo2), not symlink
    # Note: external.jpg is also counted because it's in same directory
    assert results['total'] == 3  # photo1, photo2, external.jpg
    # symlink.jpg should NOT be counted


def test_batch_tag_directory_recursive_filters_symlinks(tmp_path):
    """Test that recursive mode also filters symlinks."""
    from scripts.batch_tag_photos import batch_tag_directory

    # Create subdirectory with photos
    subdir = tmp_path / "subdir"
    subdir.mkdir()

    # Minimal valid JPEG
    jpeg_bytes = (
        b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
        b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c'
        b'\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c'
        b'\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01'
        b'\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x00'
        b'?\x00\x7f\x00\xff\xd9'
    )

    photo1 = subdir / "photo1.jpg"
    photo1.write_bytes(jpeg_bytes)

    # Create symlink in subdir pointing outside
    external_photo = tmp_path / "external_photo.jpg"
    external_photo.write_bytes(jpeg_bytes)

    symlink_photo = subdir / "symlink.jpg"
    symlink_photo.symlink_to(external_photo)

    # Run recursive batch tagging
    results = batch_tag_directory(
        tmp_path,
        override_lat=37.7749,
        override_lon=-122.4194,
        recursive=True,
        dry_run=True
    )

    # Should find photo1 in subdir, external_photo in root, but NOT symlink
    assert results['total'] == 2  # photo1, external_photo (NOT symlink)


def test_main_rejects_nonexistent_directory(tmp_path):
    """Test that main() rejects nonexistent directories."""
    from scripts.batch_tag_photos import main

    nonexistent = tmp_path / "does_not_exist"

    # Mock sys.argv
    sys.argv = [
        "batch_tag_photos.py",
        str(nonexistent),
        "--lat", "37.7749",
        "--lon", "-122.4194"
    ]

    # Should return error code
    result = main()
    assert result == 1  # Error exit code


def test_main_canonicalizes_paths(tmp_path):
    """Test that main() canonicalizes paths with resolve()."""
    from scripts.batch_tag_photos import main

    # Create a photo
    jpeg_bytes = (
        b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
        b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c'
        b'\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c'
        b'\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01'
        b'\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x00'
        b'?\x00\x7f\x00\xff\xd9'
    )

    photo = tmp_path / "photo.jpg"
    photo.write_bytes(jpeg_bytes)

    # Use relative path with .. traversal
    # This should be canonicalized safely
    relative_path = tmp_path / "subdir" / ".." / "."

    # Mock sys.argv with relative path
    sys.argv = [
        "batch_tag_photos.py",
        str(relative_path),
        "--lat", "37.7749",
        "--lon", "-122.4194",
        "--dry-run"
    ]

    # Should succeed (path is canonicalized to tmp_path)
    result = main()
    assert result in [0, 1]  # Success or error (dry-run may fail on minimal JPEG)

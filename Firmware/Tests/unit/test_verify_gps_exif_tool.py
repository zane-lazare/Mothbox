"""
Unit tests for scripts/verify_gps_exif.py - GPS EXIF Verification Tool

Tests the verification tool's ability to:
1. Extract timestamps from Mothbox photo filenames
2. Print GPS information in human-readable format
3. Generate CSV reports of GPS EXIF data
4. Handle errors gracefully (missing files, corrupted EXIF)

Following TDD methodology: Write tests FIRST, then implement.

Related:
- Issue #98 Phase 3: Verification Tool (Days 1-3)
- Spec: webui/docs/dev/issues/ISSUE_98_GPS_EXIF_IMPLEMENTATION_SPEC.md
"""

import pytest
from pathlib import Path
from datetime import datetime
from io import StringIO
import sys
import tempfile


# ============================================================================
# Test: extract_timestamp_from_filename()
# ============================================================================

def test_extract_timestamp_from_standard_filename():
    """Test extracting timestamp from standard Mothbox filename format."""
    from scripts.verify_gps_exif import extract_timestamp_from_filename

    # Standard format: mothbox_YYYY_MM_DD__HH_MM_SS.jpg
    filename = "mothbox_2025_01_15__12_30_45.jpg"
    timestamp = extract_timestamp_from_filename(filename)

    assert timestamp is not None
    assert timestamp.year == 2025
    assert timestamp.month == 1
    assert timestamp.day == 15
    assert timestamp.hour == 12
    assert timestamp.minute == 30
    assert timestamp.second == 45


def test_extract_timestamp_from_path_object():
    """Test extracting timestamp from Path object."""
    from scripts.verify_gps_exif import extract_timestamp_from_filename

    photo_path = Path("/photos/mothbox_2025_01_15__12_30_45.jpg")
    timestamp = extract_timestamp_from_filename(photo_path)

    assert timestamp is not None
    assert timestamp.year == 2025


def test_extract_timestamp_with_directory_path():
    """Test extracting timestamp from full directory path."""
    from scripts.verify_gps_exif import extract_timestamp_from_filename

    filename = "/var/lib/mothbox/photos/2025/01/15/mothbox_2025_01_15__12_30_45.jpg"
    timestamp = extract_timestamp_from_filename(filename)

    assert timestamp is not None
    assert timestamp.year == 2025


def test_extract_timestamp_invalid_format():
    """Test that invalid filename format returns None."""
    from scripts.verify_gps_exif import extract_timestamp_from_filename

    # Invalid formats
    assert extract_timestamp_from_filename("photo.jpg") is None
    assert extract_timestamp_from_filename("mothbox_invalid.jpg") is None
    assert extract_timestamp_from_filename("2025_01_15.jpg") is None


def test_extract_timestamp_invalid_date_values():
    """Test that invalid date values return None."""
    from scripts.verify_gps_exif import extract_timestamp_from_filename

    # Invalid month
    assert extract_timestamp_from_filename("mothbox_2025_13_15__12_30_45.jpg") is None
    # Invalid day
    assert extract_timestamp_from_filename("mothbox_2025_01_32__12_30_45.jpg") is None
    # Invalid hour
    assert extract_timestamp_from_filename("mothbox_2025_01_15__25_30_45.jpg") is None


# ============================================================================
# Test: print_gps_info()
# ============================================================================

def test_print_gps_info_with_full_data(tmp_path, capsys):
    """Test printing GPS info for photo with complete GPS EXIF."""
    from scripts.verify_gps_exif import print_gps_info

    # Create test photo with GPS EXIF
    photo_path = tmp_path / "mothbox_2025_01_15__12_30_45.jpg"

    # Use lib to create photo with GPS
    from lib.gps_exif_lib import embed_gps_exif
    from PIL import Image

    # Create blank JPEG
    img = Image.new('RGB', (100, 100))
    img.save(photo_path, 'JPEG')

    # Embed GPS data
    gps_data = {
        'latitude': 37.7749,
        'longitude': -122.4194,
        'altitude': 100.5,
        'gpstime': 1736944245,  # 2025-01-15 12:30:45 UTC
        'satellites_used': 8,
        'hdop': 1.2,
        'has_fix': True
    }
    result = embed_gps_exif(photo_path, gps_data=gps_data)
    assert result['success']

    # Test print_gps_info
    print_gps_info(photo_path)

    captured = capsys.readouterr()
    output = captured.out

    # Verify output contains expected information
    assert "mothbox_2025_01_15__12_30_45.jpg" in output
    assert "37.7749" in output
    assert "-122.4194" in output
    assert "100.5" in output or "100.50" in output
    assert "8" in output  # satellites
    assert "1.2" in output or "1.20" in output  # HDOP


def test_print_gps_info_no_gps_data(tmp_path, capsys):
    """Test printing GPS info for photo without GPS EXIF."""
    from scripts.verify_gps_exif import print_gps_info
    from PIL import Image

    # Create photo without GPS
    photo_path = tmp_path / "mothbox_2025_01_15__12_30_45.jpg"
    img = Image.new('RGB', (100, 100))
    img.save(photo_path, 'JPEG')

    # Test print_gps_info
    print_gps_info(photo_path)

    captured = capsys.readouterr()
    output = captured.out

    # Should indicate no GPS data
    assert "mothbox_2025_01_15__12_30_45.jpg" in output
    assert "No GPS" in output or "no GPS" in output


def test_print_gps_info_missing_file(tmp_path, capsys):
    """Test printing GPS info for non-existent file."""
    from scripts.verify_gps_exif import print_gps_info

    photo_path = tmp_path / "nonexistent.jpg"

    # Should handle gracefully
    print_gps_info(photo_path)

    captured = capsys.readouterr()
    output = captured.out

    # Should indicate file not found
    assert "not found" in output.lower() or "does not exist" in output.lower()


# ============================================================================
# Test: generate_csv_report()
# ============================================================================

def test_generate_csv_report_basic(tmp_path):
    """Test generating CSV report from photos with GPS EXIF."""
    from scripts.verify_gps_exif import generate_csv_report
    from lib.gps_exif_lib import embed_gps_exif
    from PIL import Image

    # Create test photos with GPS
    photos = []
    for i in range(3):
        photo_path = tmp_path / f"mothbox_2025_01_15__12_30_{i:02d}.jpg"
        img = Image.new('RGB', (100, 100))
        img.save(photo_path, 'JPEG')

        gps_data = {
            'latitude': 37.7749 + i * 0.001,
            'longitude': -122.4194 - i * 0.001,
            'altitude': 100.0 + i * 10,
            'gpstime': 1736944245 + i,
            'satellites_used': 8 + i,
            'hdop': 1.2,
            'has_fix': True
        }
        embed_gps_exif(photo_path, gps_data=gps_data)
        photos.append(photo_path)

    # Generate CSV report
    csv_output = tmp_path / "gps_report.csv"
    generate_csv_report(photos, csv_output)

    # Verify CSV was created
    assert csv_output.exists()

    # Read and verify CSV content
    with open(csv_output, 'r') as f:
        lines = f.readlines()

    # Should have header + 3 data rows
    assert len(lines) == 4

    # Check header
    header = lines[0].strip()
    assert "filename" in header.lower()
    assert "latitude" in header.lower()
    assert "longitude" in header.lower()
    assert "altitude" in header.lower()

    # Check data rows contain expected values
    for i, line in enumerate(lines[1:], start=0):
        assert f"mothbox_2025_01_15__12_30_{i:02d}.jpg" in line
        assert "37.77" in line  # Latitude
        assert "-122.4" in line  # Longitude (partial match)


def test_generate_csv_report_mixed_photos(tmp_path):
    """Test CSV report with mix of photos (with GPS, without GPS, missing)."""
    from scripts.verify_gps_exif import generate_csv_report
    from lib.gps_exif_lib import embed_gps_exif
    from PIL import Image

    photos = []

    # Photo 1: Has GPS
    photo1 = tmp_path / "mothbox_2025_01_15__12_30_00.jpg"
    img = Image.new('RGB', (100, 100))
    img.save(photo1, 'JPEG')
    gps_data = {
        'latitude': 37.7749,
        'longitude': -122.4194,
        'has_fix': True
    }
    embed_gps_exif(photo1, gps_data=gps_data)
    photos.append(photo1)

    # Photo 2: No GPS
    photo2 = tmp_path / "mothbox_2025_01_15__12_30_01.jpg"
    img = Image.new('RGB', (100, 100))
    img.save(photo2, 'JPEG')
    photos.append(photo2)

    # Photo 3: Missing file
    photo3 = tmp_path / "mothbox_2025_01_15__12_30_02.jpg"
    photos.append(photo3)

    # Generate CSV
    csv_output = tmp_path / "gps_report.csv"
    generate_csv_report(photos, csv_output)

    # Verify CSV
    assert csv_output.exists()

    with open(csv_output, 'r') as f:
        lines = f.readlines()

    # Should have header + 3 rows
    assert len(lines) == 4

    # Photo 1 should have GPS data
    assert "37.7749" in lines[1] or "37.77" in lines[1]

    # Photo 2 should indicate no GPS
    assert "No GPS" in lines[2] or "N/A" in lines[2] or lines[2].count(",") >= 2

    # Photo 3 should indicate missing/error
    assert "not found" in lines[3].lower() or "missing" in lines[3].lower() or "error" in lines[3].lower()


def test_generate_csv_report_empty_list(tmp_path):
    """Test CSV report with empty photo list."""
    from scripts.verify_gps_exif import generate_csv_report

    csv_output = tmp_path / "gps_report.csv"
    generate_csv_report([], csv_output)

    # Should create CSV with just header
    assert csv_output.exists()

    with open(csv_output, 'r') as f:
        lines = f.readlines()

    assert len(lines) == 1  # Just header


def test_generate_csv_report_includes_timestamp_from_filename(tmp_path):
    """Test that CSV report includes timestamp extracted from filename."""
    from scripts.verify_gps_exif import generate_csv_report
    from PIL import Image

    # Create photo
    photo = tmp_path / "mothbox_2025_01_15__12_30_45.jpg"
    img = Image.new('RGB', (100, 100))
    img.save(photo, 'JPEG')

    # Generate CSV
    csv_output = tmp_path / "gps_report.csv"
    generate_csv_report([photo], csv_output)

    with open(csv_output, 'r') as f:
        content = f.read()

    # Should include timestamp from filename
    assert "2025" in content
    assert "01" in content
    assert "15" in content


# ============================================================================
# Test: main() function with CLI arguments
# ============================================================================

def test_main_single_photo(tmp_path, capsys, monkeypatch):
    """Test main() with single photo argument."""
    from scripts.verify_gps_exif import main
    from lib.gps_exif_lib import embed_gps_exif
    from PIL import Image

    # Create photo with GPS
    photo = tmp_path / "mothbox_2025_01_15__12_30_45.jpg"
    img = Image.new('RGB', (100, 100))
    img.save(photo, 'JPEG')

    gps_data = {
        'latitude': 37.7749,
        'longitude': -122.4194,
        'has_fix': True
    }
    embed_gps_exif(photo, gps_data=gps_data)

    # Mock sys.argv
    monkeypatch.setattr(sys, 'argv', ['verify_gps_exif.py', str(photo)])

    # Run main
    exit_code = main()

    # Should succeed
    assert exit_code == 0

    # Should print GPS info
    captured = capsys.readouterr()
    assert "37.7749" in captured.out


def test_main_directory_scan(tmp_path, monkeypatch):
    """Test main() scanning directory for photos."""
    from scripts.verify_gps_exif import main
    from lib.gps_exif_lib import embed_gps_exif
    from PIL import Image

    # Create multiple photos
    for i in range(3):
        photo = tmp_path / f"mothbox_2025_01_15__12_30_{i:02d}.jpg"
        img = Image.new('RGB', (100, 100))
        img.save(photo, 'JPEG')

        gps_data = {
            'latitude': 37.7749,
            'longitude': -122.4194,
            'has_fix': True
        }
        embed_gps_exif(photo, gps_data=gps_data)

    # Mock sys.argv to scan directory
    monkeypatch.setattr(sys, 'argv', ['verify_gps_exif.py', str(tmp_path)])

    # Run main
    exit_code = main()

    # Should succeed
    assert exit_code == 0


def test_main_csv_output(tmp_path, monkeypatch):
    """Test main() with --csv flag."""
    from scripts.verify_gps_exif import main
    from PIL import Image

    # Create photo
    photo = tmp_path / "mothbox_2025_01_15__12_30_45.jpg"
    img = Image.new('RGB', (100, 100))
    img.save(photo, 'JPEG')

    csv_output = tmp_path / "report.csv"

    # Mock sys.argv with --csv flag
    monkeypatch.setattr(sys, 'argv', [
        'verify_gps_exif.py',
        str(photo),
        '--csv', str(csv_output)
    ])

    # Run main
    exit_code = main()

    assert exit_code == 0
    assert csv_output.exists()


def test_main_no_arguments_shows_help(capsys, monkeypatch):
    """Test main() without arguments shows help message."""
    from scripts.verify_gps_exif import main

    # Mock sys.argv with no arguments
    monkeypatch.setattr(sys, 'argv', ['verify_gps_exif.py'])

    # Run main - argparse will raise SystemExit
    with pytest.raises(SystemExit) as exc_info:
        main()

    # Should fail with non-zero exit code
    assert exc_info.value.code != 0

    # Should print usage/help
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert "usage" in output.lower() or "required" in output.lower()


def test_main_help_flag(capsys, monkeypatch):
    """Test main() with --help flag."""
    from scripts.verify_gps_exif import main

    # Mock sys.argv with --help
    monkeypatch.setattr(sys, 'argv', ['verify_gps_exif.py', '--help'])

    # Run main (should exit with 0 for help)
    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0

    # Should print help
    captured = capsys.readouterr()
    output = captured.out
    assert "usage" in output.lower() or "verify" in output.lower()


def test_main_missing_file_error(tmp_path, capsys, monkeypatch):
    """Test main() with non-existent file."""
    from scripts.verify_gps_exif import main

    nonexistent = tmp_path / "nonexistent.jpg"

    # Mock sys.argv
    monkeypatch.setattr(sys, 'argv', ['verify_gps_exif.py', str(nonexistent)])

    # Run main
    exit_code = main()

    # Should handle gracefully (might succeed but show "not found" message)
    # or fail with non-zero exit code
    captured = capsys.readouterr()
    output = captured.out + captured.err

    # Should mention the file or indicate error
    assert str(nonexistent.name) in output or "not found" in output.lower()


# ============================================================================
# Test: Edge Cases and Error Handling
# ============================================================================

def test_extract_timestamp_with_focus_bracket_suffix():
    """Test extracting timestamp from focus bracket filename."""
    from scripts.verify_gps_exif import extract_timestamp_from_filename

    # Focus bracket format: mothbox_YYYY_MM_DD__HH_MM_SS_bracket_0.jpg
    filename = "mothbox_2025_01_15__12_30_45_bracket_0.jpg"
    timestamp = extract_timestamp_from_filename(filename)

    # Should still extract timestamp correctly
    assert timestamp is not None
    assert timestamp.year == 2025
    assert timestamp.month == 1
    assert timestamp.day == 15


def test_csv_report_handles_unicode_paths(tmp_path):
    """Test CSV report with unicode characters in paths."""
    from scripts.verify_gps_exif import generate_csv_report
    from PIL import Image

    # Create subdirectory with unicode
    unicode_dir = tmp_path / "photos_测试"
    unicode_dir.mkdir()

    photo = unicode_dir / "mothbox_2025_01_15__12_30_45.jpg"
    img = Image.new('RGB', (100, 100))
    img.save(photo, 'JPEG')

    csv_output = tmp_path / "report.csv"

    # Should handle unicode paths
    generate_csv_report([photo], csv_output)

    assert csv_output.exists()


def test_print_gps_info_with_partial_data(tmp_path, capsys):
    """Test printing GPS info when photo has minimal GPS data."""
    from scripts.verify_gps_exif import print_gps_info
    from lib.gps_exif_lib import embed_gps_exif
    from PIL import Image

    # Create photo with minimal GPS (no altitude, no satellites)
    photo = tmp_path / "mothbox_2025_01_15__12_30_45.jpg"
    img = Image.new('RGB', (100, 100))
    img.save(photo, 'JPEG')

    gps_data = {
        'latitude': 37.7749,
        'longitude': -122.4194,
        'has_fix': True
    }
    embed_gps_exif(photo, gps_data=gps_data)

    # Should handle gracefully
    print_gps_info(photo)

    captured = capsys.readouterr()
    output = captured.out

    # Should show coordinates
    assert "37.7749" in output
    assert "-122.4194" in output

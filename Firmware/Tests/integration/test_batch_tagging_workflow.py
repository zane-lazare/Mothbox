"""
Integration tests for GPS EXIF batch tagging workflow

Tests end-to-end batch tagging scenarios:
1. Batch tag directory with manual GPS override
2. Batch tag with date filters
3. Batch tag recursively
4. Dry-run and backup modes
5. Command-line interface integration

These tests create actual JPEG files and test the complete workflow
from command-line to GPS EXIF embedding.

Related:
- Issue #98 Phase 3: Batch Tagging Tool Integration Tests
- Spec: webui/docs/dev/issues/ISSUE_98_GPS_EXIF_IMPLEMENTATION_SPEC.md
- Unit tests: Tests/unit/test_batch_tag_photos.py
"""

import pytest
import subprocess
import sys
from pathlib import Path
from PIL import Image
from webui.backend.lib.gps_exif_lib import verify_gps_exif, embed_gps_exif
from datetime import datetime


# ============================================================================
# Integration Test: End-to-End Batch Tagging Workflow
# ============================================================================

def test_batch_tag_directory_manual_override(tmp_path):
    """Integration test: Batch tag directory with manual GPS override."""
    # Create test photos
    for i in range(5):
        photo = tmp_path / f"mothbox_2025_01_15__12_30_{i:02d}.jpg"
        img = Image.new('RGB', (100, 100))
        img.save(photo, 'JPEG')

    # Run batch tagging script
    script_path = Path(__file__).parent.parent.parent / "webui" / "cli" / "batch_tag_photos.py"
    result = subprocess.run(
        [
            sys.executable, str(script_path),
            str(tmp_path),
            '--lat', '37.7749',
            '--lon', '-122.4194'
        ],
        capture_output=True,
        text=True
    )

    # Verify success
    assert result.returncode == 0

    # Verify all photos have GPS
    for i in range(5):
        photo = tmp_path / f"mothbox_2025_01_15__12_30_{i:02d}.jpg"
        gps_info = verify_gps_exif(photo)
        assert gps_info['has_gps'] is True
        assert abs(gps_info['latitude'] - 37.7749) < 0.0001
        assert abs(gps_info['longitude'] - (-122.4194)) < 0.0001


def test_batch_tag_with_date_filters(tmp_path):
    """Integration test: Batch tag with --after and --before filters."""
    # Create photos with different dates
    dates = ['15', '16', '17', '18', '19']
    for day in dates:
        photo = tmp_path / f"mothbox_2025_01_{day}__12_30_00.jpg"
        img = Image.new('RGB', (100, 100))
        img.save(photo, 'JPEG')

    # Run batch tagging with date filter (only 16, 17, 18)
    script_path = Path(__file__).parent.parent.parent / "webui" / "cli" / "batch_tag_photos.py"
    result = subprocess.run(
        [
            sys.executable, str(script_path),
            str(tmp_path),
            '--lat', '37.7749',
            '--lon', '-122.4194',
            '--after', '2025-01-16',
            '--before', '2025-01-19'
        ],
        capture_output=True,
        text=True
    )

    # Verify success
    assert result.returncode == 0

    # Verify only filtered photos have GPS
    for day in ['16', '17', '18']:
        photo = tmp_path / f"mothbox_2025_01_{day}__12_30_00.jpg"
        gps_info = verify_gps_exif(photo)
        assert gps_info['has_gps'] is True

    # Photos outside range should NOT have GPS
    for day in ['15', '19']:
        photo = tmp_path / f"mothbox_2025_01_{day}__12_30_00.jpg"
        gps_info = verify_gps_exif(photo)
        assert gps_info['has_gps'] is False


def test_batch_tag_recursive(tmp_path):
    """Integration test: Batch tag recursively through subdirectories."""
    # Create nested directory structure
    (tmp_path / "2025" / "01" / "15").mkdir(parents=True)
    (tmp_path / "2025" / "01" / "16").mkdir(parents=True)

    # Create photos in subdirectories
    photos = [
        tmp_path / "2025" / "01" / "15" / "mothbox_2025_01_15__12_30_00.jpg",
        tmp_path / "2025" / "01" / "16" / "mothbox_2025_01_16__12_30_00.jpg",
    ]

    for photo in photos:
        img = Image.new('RGB', (100, 100))
        img.save(photo, 'JPEG')

    # Run batch tagging recursively
    script_path = Path(__file__).parent.parent.parent / "webui" / "cli" / "batch_tag_photos.py"
    result = subprocess.run(
        [
            sys.executable, str(script_path),
            str(tmp_path),
            '--lat', '37.7749',
            '--lon', '-122.4194',
            '--recursive'
        ],
        capture_output=True,
        text=True
    )

    # Verify success
    assert result.returncode == 0

    # Verify all photos in subdirectories have GPS
    for photo in photos:
        gps_info = verify_gps_exif(photo)
        assert gps_info['has_gps'] is True


def test_batch_tag_dry_run_mode(tmp_path):
    """Integration test: Dry-run mode doesn't modify photos."""
    # Create test photos
    for i in range(3):
        photo = tmp_path / f"mothbox_2025_01_15__12_30_{i:02d}.jpg"
        img = Image.new('RGB', (100, 100))
        img.save(photo, 'JPEG')

    # Run batch tagging in dry-run mode
    script_path = Path(__file__).parent.parent.parent / "webui" / "cli" / "batch_tag_photos.py"
    result = subprocess.run(
        [
            sys.executable, str(script_path),
            str(tmp_path),
            '--lat', '37.7749',
            '--lon', '-122.4194',
            '--dry-run'
        ],
        capture_output=True,
        text=True
    )

    # Verify success
    assert result.returncode == 0
    assert "DRY RUN" in result.stdout or "dry" in result.stdout.lower()

    # Verify photos were NOT modified
    for i in range(3):
        photo = tmp_path / f"mothbox_2025_01_15__12_30_{i:02d}.jpg"
        gps_info = verify_gps_exif(photo)
        assert gps_info['has_gps'] is False


def test_batch_tag_backup_mode(tmp_path):
    """Integration test: Backup mode creates .bak files."""
    # Create test photos
    for i in range(3):
        photo = tmp_path / f"mothbox_2025_01_15__12_30_{i:02d}.jpg"
        img = Image.new('RGB', (100, 100))
        img.save(photo, 'JPEG')

    # Run batch tagging with backup
    script_path = Path(__file__).parent.parent.parent / "webui" / "cli" / "batch_tag_photos.py"
    result = subprocess.run(
        [
            sys.executable, str(script_path),
            str(tmp_path),
            '--lat', '37.7749',
            '--lon', '-122.4194',
            '--backup'
        ],
        capture_output=True,
        text=True
    )

    # Verify success
    assert result.returncode == 0

    # Verify backup files created
    for i in range(3):
        backup_file = tmp_path / f"mothbox_2025_01_15__12_30_{i:02d}.jpg.bak"
        assert backup_file.exists()


def test_batch_tag_idempotent(tmp_path):
    """Integration test: Batch tagging is idempotent (skips already-tagged)."""
    # Create photos, some already tagged
    photos = []

    # Photo 1: Pre-tagged with different GPS
    photo1 = tmp_path / "mothbox_2025_01_15__12_30_00.jpg"
    img = Image.new('RGB', (100, 100))
    img.save(photo1, 'JPEG')
    gps_data = {'latitude': 38.5816, 'longitude': -121.4944, 'has_fix': True}
    embed_gps_exif(photo1, gps_data=gps_data)
    photos.append(photo1)

    # Photo 2: No GPS
    photo2 = tmp_path / "mothbox_2025_01_15__12_30_01.jpg"
    img = Image.new('RGB', (100, 100))
    img.save(photo2, 'JPEG')
    photos.append(photo2)

    # Run batch tagging
    script_path = Path(__file__).parent.parent.parent / "webui" / "cli" / "batch_tag_photos.py"
    result = subprocess.run(
        [
            sys.executable, str(script_path),
            str(tmp_path),
            '--lat', '37.7749',
            '--lon', '-122.4194'
        ],
        capture_output=True,
        text=True
    )

    # Verify success
    assert result.returncode == 0

    # Photo 1 should still have original GPS (skipped)
    gps_info1 = verify_gps_exif(photo1)
    assert gps_info1['has_gps'] is True
    assert abs(gps_info1['latitude'] - 38.5816) < 0.0001  # Original GPS preserved

    # Photo 2 should have new GPS
    gps_info2 = verify_gps_exif(photo2)
    assert gps_info2['has_gps'] is True
    assert abs(gps_info2['latitude'] - 37.7749) < 0.0001  # New GPS added


def test_batch_tag_error_handling(tmp_path):
    """Integration test: Batch tagging handles errors gracefully."""
    # Test with non-existent directory
    script_path = Path(__file__).parent.parent.parent / "webui" / "cli" / "batch_tag_photos.py"
    result = subprocess.run(
        [
            sys.executable, str(script_path),
            str(tmp_path / "nonexistent"),
            '--lat', '37.7749',
            '--lon', '-122.4194'
        ],
        capture_output=True,
        text=True
    )

    # Should fail gracefully
    assert result.returncode != 0
    assert "not exist" in result.stderr.lower() or "error" in result.stderr.lower()


def test_batch_tag_invalid_coordinates(tmp_path):
    """Integration test: Batch tagging rejects invalid coordinates."""
    # Create test photo
    photo = tmp_path / "mothbox_2025_01_15__12_30_00.jpg"
    img = Image.new('RGB', (100, 100))
    img.save(photo, 'JPEG')

    # Test with invalid latitude (>90)
    script_path = Path(__file__).parent.parent.parent / "webui" / "cli" / "batch_tag_photos.py"
    result = subprocess.run(
        [
            sys.executable, str(script_path),
            str(tmp_path),
            '--lat', '100',
            '--lon', '0'
        ],
        capture_output=True,
        text=True
    )

    # Should fail
    assert result.returncode != 0
    assert "invalid" in result.stderr.lower() or "coordinates" in result.stderr.lower()


def test_batch_tag_mixed_workflow(tmp_path):
    """Integration test: Complex workflow with multiple features."""
    # Create photos across multiple days
    (tmp_path / "2025" / "01" / "15").mkdir(parents=True)
    (tmp_path / "2025" / "01" / "16").mkdir(parents=True)

    for day in ['15', '16']:
        for i in range(3):
            photo = tmp_path / "2025" / "01" / day / f"mothbox_2025_01_{day}__12_30_{i:02d}.jpg"
            img = Image.new('RGB', (100, 100))
            img.save(photo, 'JPEG')

    # Batch tag with: recursive, date filter, backup
    script_path = Path(__file__).parent.parent.parent / "webui" / "cli" / "batch_tag_photos.py"
    result = subprocess.run(
        [
            sys.executable, str(script_path),
            str(tmp_path),
            '--lat', '37.7749',
            '--lon', '-122.4194',
            '--recursive',
            '--after', '2025-01-16',
            '--backup'
        ],
        capture_output=True,
        text=True
    )

    # Verify success
    assert result.returncode == 0

    # Only 2025-01-16 photos should be tagged
    for i in range(3):
        photo_15 = tmp_path / "2025" / "01" / "15" / f"mothbox_2025_01_15__12_30_{i:02d}.jpg"
        photo_16 = tmp_path / "2025" / "01" / "16" / f"mothbox_2025_01_16__12_30_{i:02d}.jpg"

        # Day 15 should NOT have GPS
        gps_info_15 = verify_gps_exif(photo_15)
        assert gps_info_15['has_gps'] is False

        # Day 16 should have GPS
        gps_info_16 = verify_gps_exif(photo_16)
        assert gps_info_16['has_gps'] is True

        # Backup file should exist for day 16
        backup_16 = photo_16.with_suffix('.jpg.bak')
        assert backup_16.exists()


def test_batch_tag_integration_with_verification(tmp_path):
    """Integration test: Batch tag + verify workflow."""
    # Create test photos
    for i in range(5):
        photo = tmp_path / f"mothbox_2025_01_15__12_30_{i:02d}.jpg"
        img = Image.new('RGB', (100, 100))
        img.save(photo, 'JPEG')

    # Step 1: Batch tag
    batch_script = Path(__file__).parent.parent.parent / "scripts" / "batch_tag_photos.py"
    result1 = subprocess.run(
        [
            sys.executable, str(batch_script),
            str(tmp_path),
            '--lat', '37.7749',
            '--lon', '-122.4194'
        ],
        capture_output=True,
        text=True
    )

    assert result1.returncode == 0

    # Step 2: Verify with verification script
    verify_script = Path(__file__).parent.parent.parent / "scripts" / "verify_gps_exif.py"
    csv_output = tmp_path / "verification_report.csv"

    result2 = subprocess.run(
        [
            sys.executable, str(verify_script),
            str(tmp_path),
            '--csv', str(csv_output)
        ],
        capture_output=True,
        text=True
    )

    assert result2.returncode == 0
    assert csv_output.exists()

    # Verify CSV shows all photos have GPS
    with open(csv_output, 'r') as f:
        lines = f.readlines()

    assert len(lines) == 6  # Header + 5 photos

    for line in lines[1:]:
        assert "37.7749" in line or "37.77" in line
        assert "OK" in line or "True" in line

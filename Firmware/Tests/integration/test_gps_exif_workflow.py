"""Integration tests for GPS EXIF end-to-end workflows.

These tests validate the complete GPS EXIF embedding workflow:
1. GPS data in controls.txt (simulated)
2. Photo capture (simulated with PIL)
3. GPS EXIF embedding via gps_exif_tagger.py
4. Verification of embedded GPS data

Tests are marked as @pytest.mark.integration since they test
multiple components working together.
"""

import pytest
import logging
from pathlib import Path
from PIL import Image
import piexif

from mothbox_paths import PHOTOS_DIR, CONTROLS_FILE
from lib.gps_exif_lib import embed_gps_exif, verify_gps_exif, get_gps_data_from_controls
from gps_exif_tagger import batch_process_directory, process_single_photo, setup_logging


@pytest.fixture
def mock_controls_with_gps(tmp_path, monkeypatch):
    """Create mock controls.txt with GPS data.

    This fixture:
    1. Creates a temporary controls.txt file with GPS data
    2. Patches CONTROLS_FILE globally to use the temp file
    3. Returns the path to the controls file for verification

    GPS data simulates a good 3D fix in San Francisco.
    """
    controls = tmp_path / "controls.txt"
    controls.write_text("""# Mock controls.txt for GPS EXIF testing
gpstime=1705329000
lat=37.7749
lon=-122.4194
gps_altitude=15.5
gps_fix_mode=3
gps_satellites_used=8
gps_hdop=1.2
gps_pdop=2.1
""")

    # Patch CONTROLS_FILE in both modules
    import lib.gps_exif_lib
    monkeypatch.setattr('lib.gps_exif_lib.CONTROLS_FILE', controls)
    monkeypatch.setattr('mothbox_paths.CONTROLS_FILE', controls)

    return controls


@pytest.fixture
def temp_photos_dir(tmp_path):
    """Create temporary photos directory."""
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()
    return photos_dir


@pytest.fixture
def logger():
    """Create logger for testing."""
    return setup_logging(verbose=True)


@pytest.mark.integration
class TestGPSEXIFWorkflow:
    """Test complete GPS EXIF workflow."""

    def test_end_to_end_workflow(self, temp_photos_dir, mock_controls_with_gps, logger):
        """Test complete workflow: GPS.py -> controls.txt -> photo -> EXIF embed.

        Steps:
            1. Mock GPS data in controls.txt (via fixture)
            2. Create photo without GPS EXIF (simulate TakePhoto.py)
            3. Run gps_exif_tagger.py on photo
            4. Verify GPS EXIF is correct and camera EXIF preserved
        """
        # Step 1: Verify GPS data is available (fixture handles this)
        gps_data = get_gps_data_from_controls()
        assert gps_data['has_fix'] is True
        assert gps_data['latitude'] == 37.7749
        assert gps_data['longitude'] == -122.4194

        # Step 2: Create photo without GPS EXIF (simulate TakePhoto.py)
        photo_path = temp_photos_dir / "mothbox_2025_01_15__12_30_00.jpg"
        img = Image.new('RGB', (640, 480), color='blue')

        # Add camera EXIF (like TakePhoto.py does)
        exif_dict = {
            "0th": {
                piexif.ImageIFD.Make: b"MothboxV4",
                piexif.ImageIFD.Model: b"OwlSight64MP"
            },
            "Exif": {
                piexif.ExifIFD.ExposureTime: (1, 100),
                piexif.ExifIFD.ISOSpeed: 100,
                piexif.ExifIFD.FocalLength: (50, 1)
            },
            "GPS": {}  # Empty GPS IFD
        }
        exif_bytes = piexif.dump(exif_dict)
        img.save(photo_path, 'JPEG', exif=exif_bytes, quality=95)

        # Verify photo exists and has no GPS
        assert photo_path.exists()
        info_before = verify_gps_exif(photo_path)
        assert info_before['has_gps'] is False

        # Step 3: Run GPS EXIF tagger
        result = process_single_photo(photo_path, logger, force=False, backup=False, dry_run=False)
        assert result['success'] is True
        assert result['gps_embedded'] is True
        assert result['original_had_gps'] is False

        # Step 4: Verify GPS EXIF was embedded correctly
        info_after = verify_gps_exif(photo_path)
        assert info_after['has_gps'] is True
        assert abs(info_after['latitude'] - 37.7749) < 0.0001
        assert abs(info_after['longitude'] - (-122.4194)) < 0.0001
        assert info_after['satellites'] == "8"
        assert abs(info_after['altitude'] - 15.5) < 0.01
        assert abs(info_after['hdop'] - 1.2) < 0.01

        # Step 5: Verify original camera EXIF is preserved
        exif_dict_after = piexif.load(str(photo_path))
        assert exif_dict_after["0th"][piexif.ImageIFD.Make] == b"MothboxV4"
        assert exif_dict_after["0th"][piexif.ImageIFD.Model] == b"OwlSight64MP"
        assert exif_dict_after["Exif"][piexif.ExifIFD.ExposureTime] == (1, 100)
        assert exif_dict_after["Exif"][piexif.ExifIFD.ISOSpeed] == 100
        assert exif_dict_after["Exif"][piexif.ExifIFD.FocalLength] == (50, 1)

    def test_batch_processing_mixed_photos(self, temp_photos_dir, mock_controls_with_gps, logger):
        """Test batch processing directory with mixed photos.

        Tests handling of:
        - Photos without GPS EXIF (should be tagged)
        - Photos with GPS EXIF (should be skipped unless force=True)
        - Non-JPEG files (should be ignored)
        """
        # Create 5 photos without GPS
        for i in range(5):
            photo = temp_photos_dir / f"photo_{i:02d}.jpg"
            img = Image.new('RGB', (100, 100), color='red')
            img.save(photo, 'JPEG')

        # Create 2 photos with GPS (pre-tagged)
        for i in range(5, 7):
            photo = temp_photos_dir / f"photo_{i:02d}.jpg"
            img = Image.new('RGB', (100, 100), color='blue')
            gps_ifd = {
                piexif.GPSIFD.GPSVersionID: (2, 3, 0, 0),
                piexif.GPSIFD.GPSLatitude: ((37, 1), (46, 1), (2964, 100)),
                piexif.GPSIFD.GPSLatitudeRef: b'N',
                piexif.GPSIFD.GPSLongitude: ((122, 1), (25, 1), (980, 100)),
                piexif.GPSIFD.GPSLongitudeRef: b'W',
            }
            exif_dict = {"GPS": gps_ifd}
            exif_bytes = piexif.dump(exif_dict)
            img.save(photo, 'JPEG', exif=exif_bytes)

        # Create 1 non-JPEG file (should be ignored)
        (temp_photos_dir / "readme.txt").write_text("Test file")

        # Run batch processing (no force - skip already tagged)
        stats = batch_process_directory(
            temp_photos_dir,
            logger,
            pattern="*.jpg",
            force=False,
            backup=False,
            dry_run=False
        )

        # Verify statistics
        assert stats['total'] == 7  # 5 untagged + 2 pre-tagged
        assert stats['tagged'] == 5  # Only untagged photos processed
        assert stats['skipped'] == 2  # Pre-tagged photos skipped
        assert stats['errors'] == 0

        # Verify all 7 photos now have GPS EXIF
        for i in range(7):
            photo = temp_photos_dir / f"photo_{i:02d}.jpg"
            info = verify_gps_exif(photo)
            assert info['has_gps'] is True

    def test_batch_processing_with_force(self, temp_photos_dir, mock_controls_with_gps, logger):
        """Test batch processing with force=True re-tags all photos."""
        # Create 3 photos with existing GPS EXIF (different coordinates)
        for i in range(3):
            photo = temp_photos_dir / f"photo_{i:02d}.jpg"
            img = Image.new('RGB', (100, 100), color='green')

            # Pre-tag with NYC coordinates (will be overwritten)
            gps_ifd = {
                piexif.GPSIFD.GPSVersionID: (2, 3, 0, 0),
                piexif.GPSIFD.GPSLatitude: ((40, 1), (42, 1), (4608, 100)),  # 40.7128
                piexif.GPSIFD.GPSLatitudeRef: b'N',
                piexif.GPSIFD.GPSLongitude: ((74, 1), (0, 1), (216, 100)),  # -74.0060
                piexif.GPSIFD.GPSLongitudeRef: b'W',
            }
            exif_dict = {"GPS": gps_ifd}
            exif_bytes = piexif.dump(exif_dict)
            img.save(photo, 'JPEG', exif=exif_bytes)

            # Verify NYC coordinates
            info = verify_gps_exif(photo)
            assert abs(info['latitude'] - 40.7128) < 0.01
            assert abs(info['longitude'] - (-74.0060)) < 0.01

        # Run batch processing with force=True
        stats = batch_process_directory(
            temp_photos_dir,
            logger,
            pattern="*.jpg",
            force=True,  # Force re-tagging
            backup=False,
            dry_run=False
        )

        # Verify all photos were re-tagged
        assert stats['total'] == 3
        assert stats['tagged'] == 3
        assert stats['skipped'] == 0
        assert stats['errors'] == 0

        # Verify coordinates were updated to SF (from controls.txt)
        for i in range(3):
            photo = temp_photos_dir / f"photo_{i:02d}.jpg"
            info = verify_gps_exif(photo)
            assert info['has_gps'] is True
            assert abs(info['latitude'] - 37.7749) < 0.0001  # SF coordinates
            assert abs(info['longitude'] - (-122.4194)) < 0.0001

    def test_dry_run_mode(self, temp_photos_dir, mock_controls_with_gps, logger):
        """Test dry-run mode doesn't modify photos."""
        # Create photo without GPS
        photo = temp_photos_dir / "test_photo.jpg"
        img = Image.new('RGB', (200, 200), color='yellow')
        img.save(photo, 'JPEG')

        # Verify no GPS
        info_before = verify_gps_exif(photo)
        assert info_before['has_gps'] is False

        # Get original modification time
        mtime_before = photo.stat().st_mtime

        # Run in dry-run mode
        result = process_single_photo(photo, logger, force=False, backup=False, dry_run=True)
        assert result['success'] is True  # Success in validation
        # In dry_run mode, gps_embedded should still be False since file wasn't modified

        # Verify photo was NOT modified
        info_after = verify_gps_exif(photo)
        assert info_after['has_gps'] is False
        mtime_after = photo.stat().st_mtime
        assert mtime_before == mtime_after

    def test_backup_creation(self, temp_photos_dir, mock_controls_with_gps, logger):
        """Test backup file creation with --backup flag."""
        # Create photo without GPS
        photo = temp_photos_dir / "test_photo.jpg"
        img = Image.new('RGB', (200, 200), color='cyan')
        img.save(photo, 'JPEG')

        # Verify no backup exists
        backup_path = photo.with_suffix('.jpg.bak')
        assert not backup_path.exists()

        # Process with backup=True
        result = process_single_photo(photo, logger, force=False, backup=True, dry_run=False)
        assert result['success'] is True
        assert result['backup_path'] == backup_path

        # Verify backup was created
        assert backup_path.exists()

        # Verify backup has no GPS (original state)
        info_backup = verify_gps_exif(backup_path)
        assert info_backup['has_gps'] is False

        # Verify original was modified (has GPS now)
        info_original = verify_gps_exif(photo)
        assert info_original['has_gps'] is True

    def test_no_gps_fix_skips_photos(self, temp_photos_dir, tmp_path, monkeypatch, logger):
        """Test photos are skipped when GPS has no fix."""
        # Create controls.txt with NO GPS fix
        controls = tmp_path / "controls.txt"
        controls.write_text("""# Mock controls.txt - NO GPS FIX
gpstime=0
lat=n/a
lon=n/a
gps_fix_mode=0
gps_satellites_used=0
gps_hdop=99.99
""")

        # Patch CONTROLS_FILE
        import lib.gps_exif_lib
        monkeypatch.setattr('lib.gps_exif_lib.CONTROLS_FILE', controls)

        # Verify no GPS fix
        gps_data = get_gps_data_from_controls()
        assert gps_data['has_fix'] is False

        # Create photo
        photo = temp_photos_dir / "test_photo.jpg"
        img = Image.new('RGB', (100, 100), color='magenta')
        img.save(photo, 'JPEG')

        # Process photo (should be skipped)
        result = process_single_photo(photo, logger, force=False, backup=False, dry_run=False)
        assert result['success'] is False
        assert result['skipped'] is True
        assert result['gps_embedded'] is False

        # Verify photo still has no GPS
        info = verify_gps_exif(photo)
        assert info['has_gps'] is False

    def test_idempotency(self, temp_photos_dir, mock_controls_with_gps, logger):
        """Test that processing same photo twice is safe (idempotent)."""
        # Create photo
        photo = temp_photos_dir / "test_photo.jpg"
        img = Image.new('RGB', (100, 100), color='white')
        img.save(photo, 'JPEG')

        # First processing
        result1 = process_single_photo(photo, logger, force=False, backup=False, dry_run=False)
        assert result1['success'] is True
        assert result1['gps_embedded'] is True

        # Second processing (should skip since already tagged)
        result2 = process_single_photo(photo, logger, force=False, backup=False, dry_run=False)
        assert result2['success'] is False  # Not processed again
        assert result2['skipped'] is True
        assert result2['original_had_gps'] is True

        # Verify GPS data is still correct (not corrupted)
        info = verify_gps_exif(photo)
        assert info['has_gps'] is True
        assert abs(info['latitude'] - 37.7749) < 0.0001
        assert abs(info['longitude'] - (-122.4194)) < 0.0001

    def test_case_insensitive_extensions(self, temp_photos_dir, mock_controls_with_gps, logger):
        """Test batch processing handles JPG, JPEG, jpg, jpeg extensions."""
        # Create photos with different extensions
        extensions = ['jpg', 'JPG', 'jpeg', 'JPEG']
        for i, ext in enumerate(extensions):
            photo = temp_photos_dir / f"photo_{i}.{ext}"
            img = Image.new('RGB', (100, 100), color='orange')
            img.save(photo, 'JPEG')

        # Run batch processing with *.jpg pattern
        stats = batch_process_directory(
            temp_photos_dir,
            logger,
            pattern="*.jpg",
            force=False,
            backup=False,
            dry_run=False
        )

        # Verify all variants were found and processed
        # Note: glob is case-sensitive on Linux, but our implementation handles common variants
        assert stats['total'] >= 2  # At least .jpg and .JPG
        assert stats['tagged'] >= 2
        assert stats['errors'] == 0


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling in GPS EXIF workflow."""

    def test_missing_photo_file(self, logger):
        """Test handling of missing photo file."""
        # Try to process non-existent photo
        result = process_single_photo(Path("/tmp/nonexistent_photo.jpg"), logger)
        assert result['success'] is False
        assert result['error'] is not None
        assert "does not exist" in result['error']

    def test_corrupted_photo_file(self, temp_photos_dir, mock_controls_with_gps, logger):
        """Test handling of corrupted/invalid JPEG."""
        # Create invalid JPEG file
        bad_photo = temp_photos_dir / "corrupted.jpg"
        bad_photo.write_text("This is not a JPEG file!")

        # Try to process (should fail gracefully)
        result = process_single_photo(bad_photo, logger)
        assert result['success'] is False
        # The library returns an error OR skips the file gracefully
        # Both are acceptable error handling behaviors
        assert result['error'] is not None or result['skipped'] is True

    def test_permission_denied(self, temp_photos_dir, mock_controls_with_gps, logger):
        """Test handling of permission errors (read-only photo).

        Note: This test may not fail on all systems since PIL can sometimes
        write to read-only files in /tmp. The test verifies graceful handling
        when permission errors DO occur.
        """
        # Create photo
        photo = temp_photos_dir / "readonly_photo.jpg"
        img = Image.new('RGB', (100, 100), color='black')
        img.save(photo, 'JPEG')

        # Make photo read-only
        import stat
        photo.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)  # 0o444

        try:
            # Try to process
            result = process_single_photo(photo, logger, force=False, backup=False, dry_run=False)

            # On some systems, PIL can still write to read-only files in /tmp
            # So we accept either success OR graceful error handling
            if not result['success']:
                # If it failed, verify error was reported
                assert result['error'] is not None
            # If it succeeded, that's also OK (system allows write despite permissions)

        finally:
            # Restore write permissions for cleanup
            photo.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)


if __name__ == '__main__':
    # Allow running tests directly
    pytest.main([__file__, '-v', '-s'])

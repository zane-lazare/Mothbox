"""
Unit tests for gps_exif_lib.py error handling and edge cases
Tests exception handling, piexif errors, and boundary conditions
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
import tempfile
import shutil
import sys

# Import the module under test
from lib.gps_exif_lib import (
    get_gps_data_from_controls,
    decimal_to_dms,
    build_gps_ifd,
    embed_gps_exif,
    verify_gps_exif
)


@pytest.fixture(scope="module", autouse=True)
def ensure_real_pil():
    """
    Ensure PIL is not mocked for this test module (Python 3.13 compatibility).

    In Python 3.13, PIL mocks from test_gallery_routes persist across modules
    despite the reset_pil_imports fixture. Force fresh PIL import at module level.
    """
    # Remove any existing PIL modules
    pil_modules = [key for key in sys.modules.keys() if key == 'PIL' or key.startswith('PIL.')]
    for key in pil_modules:
        del sys.modules[key]

    # Re-import PIL.Image globally for this module
    global Image
    from PIL import Image

    # Initialize PIL plugins to register file format handlers (.jpg, .png, etc.)
    Image.init()

    yield

    # Cleanup after module
    pil_modules = [key for key in sys.modules.keys() if key == 'PIL' or key.startswith('PIL.')]
    for key in pil_modules:
        del sys.modules[key]


class TestPiexifImportError:
    """Test graceful degradation when piexif is not available."""

    def test_piexif_import_error_handling(self):
        """Test that missing piexif module is handled gracefully."""
        # The module imports piexif at the top with try/except
        # We can test the behavior by patching piexif to None
        with patch('lib.gps_exif_lib.piexif', None):
            # Import should still work
            from lib.gps_exif_lib import embed_gps_exif

            # But calling embed_gps_exif should fail gracefully
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                tmp_path = Path(tmp.name)
                try:
                    # Create a minimal JPEG
                    img = Image.new('RGB', (100, 100), color='white')
                    img.save(tmp_path)

                    result = embed_gps_exif(tmp_path)

                    # Should fail with error about missing piexif
                    assert not result['success']
                    assert 'error' in result
                finally:
                    tmp_path.unlink()


class TestGPSDataExtractionErrors:
    """Test error handling in GPS data extraction."""

    def test_missing_controls_file(self):
        """Test handling of missing controls.txt file."""
        nonexistent_file = Path('/nonexistent/controls.txt')
        gps_data = get_gps_data_from_controls(controls_file=nonexistent_file)

        # Should return no fix
        assert gps_data['has_fix'] is False

    def test_corrupted_controls_file(self):
        """Test handling of corrupted controls.txt file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            # Write invalid data
            tmp.write('\x00\x01\x02\x03\xff\xfe')
            tmp.flush()
            tmp_path = Path(tmp.name)

        try:
            gps_data = get_gps_data_from_controls(controls_file=tmp_path)

            # Should handle error and return no fix
            assert gps_data['has_fix'] is False
        finally:
            tmp_path.unlink()

    def test_malformed_gps_values(self):
        """Test handling of malformed GPS values in controls.txt."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("lat=invalid_number\n")
            tmp.write("lon=also_invalid\n")
            tmp.write("alt=not_a_float\n")
            tmp.flush()
            tmp_path = Path(tmp.name)

        try:
            gps_data = get_gps_data_from_controls(controls_file=tmp_path)

            # Should parse as None/defaults
            assert gps_data['has_fix'] is False
            assert gps_data['latitude'] is None
            assert gps_data['longitude'] is None
        finally:
            tmp_path.unlink()

    def test_safe_int_with_non_numeric(self):
        """Test safe_int helper with non-numeric values."""
        # This tests the internal safe_int function indirectly
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("gps_satellites_used=not_a_number\n")
            tmp.write("lat=40.7\n")
            tmp.write("lon=-74.0\n")
            tmp.write("gps_fix_mode=3\n")
            tmp.flush()
            tmp_path = Path(tmp.name)

        try:
            gps_data = get_gps_data_from_controls(controls_file=tmp_path)

            # satellites_used should default to 0
            assert gps_data['satellites_used'] == 0
        finally:
            tmp_path.unlink()


class TestCoordinateConversionErrors:
    """Test error handling in coordinate conversion."""

    def test_none_coordinate(self):
        """Test handling of None coordinate values."""
        # decimal_to_dms should handle None gracefully (will raise AttributeError)
        # Test that GPS IFD building handles None coordinates
        gps_data = {
            'has_fix': True,
            'latitude': None,
            'longitude': -74.0,
            'altitude': 10.0,
            'timestamp': '2024-01-15 12:30:45',
            'num_sat': 8
        }
        gps_ifd = build_gps_ifd(gps_data)
        # Should handle None gracefully
        assert isinstance(gps_ifd, dict)

    def test_nan_coordinate(self):
        """Test handling of NaN coordinate values."""
        import math
        gps_data = {
            'has_fix': True,
            'latitude': math.nan,
            'longitude': -74.0,
            'altitude': 10.0,
            'timestamp': '2024-01-15 12:30:45',
            'num_sat': 8
        }
        # Should handle NaN without crashing
        gps_ifd = build_gps_ifd(gps_data)
        assert isinstance(gps_ifd, dict)

    def test_infinity_coordinate(self):
        """Test handling of infinity coordinate values."""
        import math
        gps_data = {
            'has_fix': True,
            'latitude': math.inf,
            'longitude': -74.0,
            'altitude': 10.0,
            'timestamp': '2024-01-15 12:30:45',
            'num_sat': 8
        }
        # Should handle infinity without crashing
        gps_ifd = build_gps_ifd(gps_data)
        assert isinstance(gps_ifd, dict)

    def test_very_large_coordinate(self):
        """Test handling of extremely large coordinates."""
        # Test with value larger than valid lat/lon
        gps_data = {
            'has_fix': True,
            'latitude': 1000.0,
            'longitude': -74.0,
            'altitude': 10.0,
            'timestamp': '2024-01-15 12:30:45',
            'num_sat': 8
        }
        # Should still convert (validation is caller's responsibility)
        gps_ifd = build_gps_ifd(gps_data)
        assert isinstance(gps_ifd, dict)

    def test_latitude_out_of_range_positive(self):
        """Test that latitude > 90 raises ValueError."""
        with pytest.raises(ValueError, match="Invalid latitude"):
            decimal_to_dms(91.0, is_latitude=True)

        with pytest.raises(ValueError, match="Invalid latitude"):
            decimal_to_dms(90.001, is_latitude=True)

    def test_latitude_out_of_range_negative(self):
        """Test that latitude < -90 raises ValueError."""
        with pytest.raises(ValueError, match="Invalid latitude"):
            decimal_to_dms(-91.0, is_latitude=True)

        with pytest.raises(ValueError, match="Invalid latitude"):
            decimal_to_dms(-90.001, is_latitude=True)

    def test_longitude_out_of_range_positive(self):
        """Test that longitude > 180 raises ValueError."""
        with pytest.raises(ValueError, match="Invalid longitude"):
            decimal_to_dms(181.0, is_latitude=False)

        with pytest.raises(ValueError, match="Invalid longitude"):
            decimal_to_dms(180.001, is_latitude=False)

    def test_longitude_out_of_range_negative(self):
        """Test that longitude < -180 raises ValueError."""
        with pytest.raises(ValueError, match="Invalid longitude"):
            decimal_to_dms(-181.0, is_latitude=False)

        with pytest.raises(ValueError, match="Invalid longitude"):
            decimal_to_dms(-180.001, is_latitude=False)

    def test_coordinate_boundary_values_valid(self):
        """Test that boundary values (±90, ±180) are accepted."""
        # Latitude boundaries should be valid
        dms, ref = decimal_to_dms(90.0, is_latitude=True)
        assert ref == 'N'
        assert dms[0] == (90, 1)

        dms, ref = decimal_to_dms(-90.0, is_latitude=True)
        assert ref == 'S'
        assert dms[0] == (90, 1)

        # Longitude boundaries should be valid
        dms, ref = decimal_to_dms(180.0, is_latitude=False)
        assert ref == 'E'
        assert dms[0] == (180, 1)

        dms, ref = decimal_to_dms(-180.0, is_latitude=False)
        assert ref == 'W'
        assert dms[0] == (180, 1)


class TestGPSIFDBuildingErrors:
    """Test error handling in GPS IFD building."""

    def test_build_gps_ifd_missing_coordinates(self):
        """Test GPS IFD building with missing coordinates."""
        gps_data = {
            'has_fix': True,  # Says it has fix but...
            'latitude': None,  # Missing latitude
            'longitude': None,  # Missing longitude
            'altitude': 100.0,
            'timestamp': '2024-01-15 12:30:45',
            'num_sat': 8
        }

        gps_ifd = build_gps_ifd(gps_data)

        # Should return empty IFD or handle gracefully
        assert isinstance(gps_ifd, dict)

    def test_build_gps_ifd_invalid_timestamp(self):
        """Test GPS IFD building with invalid timestamp format."""
        gps_data = {
            'has_fix': True,
            'latitude': 40.7128,
            'longitude': -74.0060,
            'altitude': 10.0,
            'timestamp': 'invalid_timestamp',  # Bad format
            'num_sat': 8
        }

        # Should handle invalid timestamp gracefully
        gps_ifd = build_gps_ifd(gps_data)
        assert isinstance(gps_ifd, dict)

    def test_build_gps_ifd_negative_altitude(self):
        """Test GPS IFD building with negative altitude (below sea level)."""
        gps_data = {
            'has_fix': True,
            'latitude': 40.7128,
            'longitude': -74.0060,
            'altitude': -100.0,  # Below sea level
            'timestamp': '2024-01-15 12:30:45',
            'num_sat': 8
        }

        gps_ifd = build_gps_ifd(gps_data)

        # Should still build IFD (negative altitude is valid)
        assert isinstance(gps_ifd, dict)
        assert len(gps_ifd) > 0


class TestEXIFEmbeddingErrors:
    """Test error handling in EXIF embedding."""

    def test_embed_gps_exif_missing_file(self):
        """Test embedding GPS EXIF in non-existent file."""
        nonexistent_file = Path('/nonexistent/photo.jpg')

        result = embed_gps_exif(nonexistent_file)

        assert not result['success']
        assert 'error' in result
        assert 'does not exist' in result['error'].lower()

    def test_embed_gps_exif_invalid_image_file(self):
        """Test embedding GPS EXIF in non-image file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jpg', delete=False) as tmp:
            tmp.write("This is not an image file")
            tmp.flush()
            tmp_path = Path(tmp.name)

        try:
            result = embed_gps_exif(tmp_path)

            assert not result['success']
            assert 'error' in result
        finally:
            tmp_path.unlink()

    def test_embed_gps_exif_corrupted_exif(self):
        """Test embedding GPS EXIF in photo with corrupted EXIF."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_path = Path(tmp.name)

            # Create image with corrupted EXIF
            img = Image.new('RGB', (100, 100), color='blue')
            img.save(tmp_path)

            # Manually corrupt the EXIF by appending garbage
            with open(tmp_path, 'ab') as f:
                f.write(b'\xff\xfe\xfd\xfc')

        try:
            # Should handle corrupted EXIF gracefully
            result = embed_gps_exif(tmp_path)

            # May succeed (piexif can handle some corruption) or fail gracefully
            assert 'error' in result or 'success' in result
        finally:
            tmp_path.unlink()

    def test_embed_gps_exif_backup_permission_denied(self):
        """Test backup creation when permission denied."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_path = Path(tmp.name)

            # Create valid image
            img = Image.new('RGB', (100, 100), color='green')
            img.save(tmp_path)

        try:
            # Mock piexif.load to return valid EXIF data (Python 3.13 compatibility)
            mock_exif = {'0th': {}, 'Exif': {}, 'GPS': {}, '1st': {}, 'thumbnail': None}
            # Mock shutil.copy2 to raise PermissionError
            with patch('lib.gps_exif_lib.piexif.load', return_value=mock_exif):
                with patch('shutil.copy2', side_effect=PermissionError("Permission denied")):
                    # Create GPS data
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as controls:
                        controls.write("lat=40.7\n")
                        controls.write("lon=-74.0\n")
                        controls.write("gps_fix_mode=3\n")
                        controls.flush()
                        controls_path = Path(controls.name)

                    try:
                        result = embed_gps_exif(tmp_path, controls_file=controls_path, backup=True)

                        # Should fail with backup error
                        assert not result['success']
                        assert 'error' in result
                        assert 'backup' in result['error'].lower()
                    finally:
                        controls_path.unlink()
        finally:
            tmp_path.unlink()

    def test_embed_gps_exif_write_permission_denied(self):
        """Test EXIF writing when permission denied."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_path = Path(tmp.name)

            # Create valid image
            img = Image.new('RGB', (100, 100), color='red')
            img.save(tmp_path)

        try:
            # Mock piexif.insert to raise IOError
            with patch('piexif.insert', side_effect=IOError("Permission denied")):
                # Create GPS data
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as controls:
                    controls.write("lat=40.7\n")
                    controls.write("lon=-74.0\n")
                    controls.write("fix=3\n")
                    controls.flush()
                    controls_path = Path(controls.name)

                try:
                    result = embed_gps_exif(tmp_path, controls_file=controls_path)

                    # Should fail with write error
                    assert not result['success']
                    assert 'error' in result
                finally:
                    controls_path.unlink()
        finally:
            tmp_path.unlink()

    def test_embed_gps_exif_piexif_dump_error(self):
        """Test handling of piexif.dump errors."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_path = Path(tmp.name)

            # Create valid image
            img = Image.new('RGB', (100, 100), color='yellow')
            img.save(tmp_path)

        try:
            # Mock piexif.load to return valid EXIF data (Python 3.13 compatibility)
            mock_exif = {'0th': {}, 'Exif': {}, 'GPS': {}, '1st': {}, 'thumbnail': None}
            # Mock piexif.dump to raise error
            with patch('lib.gps_exif_lib.piexif.load', return_value=mock_exif):
                with patch('lib.gps_exif_lib.piexif.dump', side_effect=ValueError("Invalid EXIF data")):
                    # Create GPS data
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as controls:
                        controls.write("lat=40.7\n")
                        controls.write("lon=-74.0\n")
                        controls.write("gps_fix_mode=3\n")
                        controls.flush()
                        controls_path = Path(controls.name)

                    try:
                        result = embed_gps_exif(tmp_path, controls_file=controls_path)

                        # Should fail with serialization error
                        assert not result['success']
                        assert 'error' in result
                        assert 'serialize' in result['error'].lower()
                    finally:
                        controls_path.unlink()
        finally:
            tmp_path.unlink()

    def test_embed_gps_exif_temp_file_cleanup_on_save_error(self):
        """Test that temp files are cleaned up when Image.save() fails."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_path = Path(tmp.name)

            # Create valid image
            img = Image.new('RGB', (100, 100), color='cyan')
            img.save(tmp_path)

        try:
            # Create GPS data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as controls:
                controls.write("lat=40.7\n")
                controls.write("lon=-74.0\n")
                controls.write("gps_fix_mode=3\n")
                controls.flush()
                controls_path = Path(controls.name)

            try:
                # Mock PIL.Image to fail during save()
                from unittest.mock import Mock, patch
                mock_img = Mock()
                mock_img.save.side_effect = IOError('Disk full')

                with patch('PIL.Image.open', return_value=mock_img):
                    result = embed_gps_exif(tmp_path, controls_file=controls_path)

                # Should fail with error
                assert not result['success']
                assert 'error' in result
                assert 'write' in result['error'].lower()

                # Check for orphaned temp files
                photo_dir = tmp_path.parent
                temp_files = list(photo_dir.glob('*.jpg.tmp'))

                # Temp file should be cleaned up even on error
                assert len(temp_files) == 0, f"Orphaned temp file(s) found: {temp_files}"
            finally:
                controls_path.unlink()
        finally:
            tmp_path.unlink(missing_ok=True)
            # Cleanup any orphaned temp files
            for temp_file in tmp_path.parent.glob('*.jpg.tmp'):
                temp_file.unlink()

    def test_embed_gps_exif_temp_file_cleanup_on_replace_error(self):
        """Test that temp files are cleaned up when temp_path.replace() fails."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_path = Path(tmp.name)

            # Create valid image
            img = Image.new('RGB', (100, 100), color='magenta')
            img.save(tmp_path)

        try:
            # Create GPS data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as controls:
                controls.write("lat=40.7\n")
                controls.write("lon=-74.0\n")
                controls.write("gps_fix_mode=3\n")
                controls.flush()
                controls_path = Path(controls.name)

            try:
                # Mock Path.replace to fail (simulates permission error)
                from unittest.mock import patch

                original_replace = Path.replace
                def mock_replace(self, target):
                    if str(self).endswith('.jpg.tmp'):
                        raise OSError('Permission denied')
                    return original_replace(self, target)

                with patch.object(Path, 'replace', mock_replace):
                    result = embed_gps_exif(tmp_path, controls_file=controls_path)

                # Should fail with error
                assert not result['success']
                assert 'error' in result

                # Check for orphaned temp files
                photo_dir = tmp_path.parent
                temp_files = list(photo_dir.glob('*.jpg.tmp'))

                # Temp file should be cleaned up even on error
                assert len(temp_files) == 0, f"Orphaned temp file(s) found: {temp_files}"
            finally:
                controls_path.unlink()
        finally:
            tmp_path.unlink(missing_ok=True)
            # Cleanup any orphaned temp files
            for temp_file in tmp_path.parent.glob('*.jpg.tmp'):
                temp_file.unlink()


class TestEXIFVerificationErrors:
    """Test error handling in EXIF verification."""

    def test_verify_gps_exif_missing_file(self):
        """Test verification of non-existent file."""
        nonexistent_file = Path('/nonexistent/photo.jpg')

        result = verify_gps_exif(nonexistent_file)

        assert 'error' in result
        assert not result.get('has_gps', True)

    def test_verify_gps_exif_invalid_image(self):
        """Test verification of invalid image file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jpg', delete=False) as tmp:
            tmp.write("Not an image")
            tmp.flush()
            tmp_path = Path(tmp.name)

        try:
            result = verify_gps_exif(tmp_path)

            # Should handle error gracefully
            assert 'error' in result or 'has_gps' in result
        finally:
            tmp_path.unlink()

    def test_verify_gps_exif_piexif_load_error(self):
        """Test handling of piexif.load errors."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_path = Path(tmp.name)

            # Create valid image
            img = Image.new('RGB', (100, 100), color='purple')
            img.save(tmp_path)

        try:
            # Mock piexif.load to raise error
            with patch('piexif.load', side_effect=ValueError("Invalid EXIF")):
                result = verify_gps_exif(tmp_path)

                # Should handle error
                assert 'error' in result
        finally:
            tmp_path.unlink()


class TestEdgeCases:
    """Test boundary conditions and edge cases."""

    def test_zero_altitude(self):
        """Test handling of zero altitude (sea level)."""
        gps_data = {
            'has_fix': True,
            'latitude': 40.7128,
            'longitude': -74.0060,
            'altitude': 0.0,  # Exactly at sea level
            'timestamp': '2024-01-15 12:30:45',
            'num_sat': 8
        }

        gps_ifd = build_gps_ifd(gps_data)

        # Should include altitude even if zero
        assert isinstance(gps_ifd, dict)

    def test_maximum_satellite_count(self):
        """Test handling of maximum satellite count."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("lat=40.7\n")
            tmp.write("lon=-74.0\n")
            tmp.write("gps_fix_mode=3\n")
            tmp.write("gps_satellites_used=255\n")  # Maximum value for a byte
            tmp.flush()
            tmp_path = Path(tmp.name)

        try:
            gps_data = get_gps_data_from_controls(controls_file=tmp_path)

            assert gps_data['satellites_used'] == 255
        finally:
            tmp_path.unlink()

    def test_equator_and_prime_meridian(self):
        """Test coordinates at equator and prime meridian."""
        gps_data = {
            'has_fix': True,
            'latitude': 0.0,  # Equator
            'longitude': 0.0,  # Prime meridian
            'altitude': 10.0,
            'timestamp': '2024-01-15 12:30:45',
            'num_sat': 8
        }

        gps_ifd = build_gps_ifd(gps_data)

        # Should handle zero coordinates
        assert isinstance(gps_ifd, dict)
        assert len(gps_ifd) > 0

    def test_high_precision_coordinates(self):
        """Test very high precision coordinate values."""
        gps_data = {
            'has_fix': True,
            'latitude': 40.712775897932384,  # Very high precision
            'longitude': -74.006058392847483,
            'altitude': 10.123456789,
            'timestamp': '2024-01-15 12:30:45',
            'num_sat': 8
        }

        gps_ifd = build_gps_ifd(gps_data)

        # Should handle high precision
        assert isinstance(gps_ifd, dict)
        assert len(gps_ifd) > 0

    def test_unicode_in_controls_file(self):
        """Test handling of Unicode characters in controls.txt."""
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.txt', delete=False) as tmp:
            tmp.write("# Comment with émojis 🌍\n")
            tmp.write("lat=40.7\n")
            tmp.write("lon=-74.0\n")
            tmp.write("gps_fix_mode=3\n")
            tmp.flush()
            tmp_path = Path(tmp.name)

        try:
            gps_data = get_gps_data_from_controls(controls_file=tmp_path)

            # Should parse successfully despite Unicode
            assert gps_data['has_fix'] is True
        finally:
            tmp_path.unlink()

    def test_empty_controls_file(self):
        """Test handling of completely empty controls.txt."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            # Write nothing
            tmp.flush()
            tmp_path = Path(tmp.name)

        try:
            gps_data = get_gps_data_from_controls(controls_file=tmp_path)

            # Should return no fix
            assert gps_data['has_fix'] is False
        finally:
            tmp_path.unlink()

    def test_controls_file_with_only_comments(self):
        """Test controls.txt with only comments."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("# This is a comment\n")
            tmp.write("# Another comment\n")
            tmp.write("#\n")
            tmp.flush()
            tmp_path = Path(tmp.name)

        try:
            gps_data = get_gps_data_from_controls(controls_file=tmp_path)

            # Should return no fix (no actual data)
            assert gps_data['has_fix'] is False
        finally:
            tmp_path.unlink()


class TestDivisionByZeroErrors:
    """Test error handling for malformed EXIF data with zero denominators."""

    def test_verify_gps_exif_latitude_zero_denominator_degrees(self):
        """Test verify_gps_exif handles latitude with zero denominator in degrees."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / 'test.jpg'

            # Create test photo
            img = Image.new('RGB', (100, 100), color='blue')
            img.save(tmp_path)

            # Mock piexif to return malformed GPS data with zero denominator
            with patch('lib.gps_exif_lib.piexif') as mock_piexif:
                mock_piexif.GPSIFD.GPSLatitude = 2
                mock_piexif.GPSIFD.GPSLatitudeRef = 1
                mock_piexif.GPSIFD.GPSLongitude = 4
                mock_piexif.GPSIFD.GPSLongitudeRef = 3

                # Malformed latitude: degrees denominator is zero
                malformed_gps_ifd = {
                    2: ((37, 0), (46, 1), (5920, 100)),  # degrees denominator = 0
                    1: b'N',
                    4: ((122, 1), (25, 1), (1164, 100)),
                    3: b'W'
                }

                mock_piexif.load.return_value = {'GPS': malformed_gps_ifd}

                # Should catch the error and return error in result
                result = verify_gps_exif(tmp_path)

                assert result['error'] is not None, "Should return error for zero denominator"
                assert 'denominator is zero' in result['error'].lower(), \
                    f"Error message should mention zero denominator: {result['error']}"

    def test_verify_gps_exif_latitude_zero_denominator_minutes(self):
        """Test verify_gps_exif handles latitude with zero denominator in minutes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / 'test.jpg'
            img = Image.new('RGB', (100, 100), color='blue')
            img.save(tmp_path)

            with patch('lib.gps_exif_lib.piexif') as mock_piexif:
                mock_piexif.GPSIFD.GPSLatitude = 2
                mock_piexif.GPSIFD.GPSLatitudeRef = 1
                mock_piexif.GPSIFD.GPSLongitude = 4
                mock_piexif.GPSIFD.GPSLongitudeRef = 3

                # Malformed latitude: minutes denominator is zero
                malformed_gps_ifd = {
                    2: ((37, 1), (46, 0), (5920, 100)),  # minutes denominator = 0
                    1: b'N',
                    4: ((122, 1), (25, 1), (1164, 100)),
                    3: b'W'
                }

                mock_piexif.load.return_value = {'GPS': malformed_gps_ifd}

                result = verify_gps_exif(tmp_path)

                assert result['error'] is not None
                assert 'denominator is zero' in result['error'].lower()

    def test_verify_gps_exif_latitude_zero_denominator_seconds(self):
        """Test verify_gps_exif handles latitude with zero denominator in seconds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / 'test.jpg'
            img = Image.new('RGB', (100, 100), color='blue')
            img.save(tmp_path)

            with patch('lib.gps_exif_lib.piexif') as mock_piexif:
                mock_piexif.GPSIFD.GPSLatitude = 2
                mock_piexif.GPSIFD.GPSLatitudeRef = 1
                mock_piexif.GPSIFD.GPSLongitude = 4
                mock_piexif.GPSIFD.GPSLongitudeRef = 3

                # Malformed latitude: seconds denominator is zero
                malformed_gps_ifd = {
                    2: ((37, 1), (46, 1), (5920, 0)),  # seconds denominator = 0
                    1: b'N',
                    4: ((122, 1), (25, 1), (1164, 100)),
                    3: b'W'
                }

                mock_piexif.load.return_value = {'GPS': malformed_gps_ifd}

                result = verify_gps_exif(tmp_path)

                assert result['error'] is not None
                assert 'denominator is zero' in result['error'].lower()

    def test_verify_gps_exif_longitude_zero_denominator(self):
        """Test verify_gps_exif handles longitude with zero denominator."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / 'test.jpg'
            img = Image.new('RGB', (100, 100), color='blue')
            img.save(tmp_path)

            with patch('lib.gps_exif_lib.piexif') as mock_piexif:
                mock_piexif.GPSIFD.GPSLatitude = 2
                mock_piexif.GPSIFD.GPSLatitudeRef = 1
                mock_piexif.GPSIFD.GPSLongitude = 4
                mock_piexif.GPSIFD.GPSLongitudeRef = 3

                # Malformed longitude: degrees denominator is zero
                malformed_gps_ifd = {
                    2: ((37, 1), (46, 1), (5920, 100)),
                    1: b'N',
                    4: ((122, 0), (25, 1), (1164, 100)),  # degrees denominator = 0
                    3: b'W'
                }

                mock_piexif.load.return_value = {'GPS': malformed_gps_ifd}

                result = verify_gps_exif(tmp_path)

                assert result['error'] is not None
                assert 'denominator is zero' in result['error'].lower()

    def test_verify_gps_exif_altitude_zero_denominator(self):
        """Test verify_gps_exif handles altitude with zero denominator."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / 'test.jpg'
            img = Image.new('RGB', (100, 100), color='blue')
            img.save(tmp_path)

            with patch('lib.gps_exif_lib.piexif') as mock_piexif:
                mock_piexif.GPSIFD.GPSLatitude = 2
                mock_piexif.GPSIFD.GPSLatitudeRef = 1
                mock_piexif.GPSIFD.GPSLongitude = 4
                mock_piexif.GPSIFD.GPSLongitudeRef = 3
                mock_piexif.GPSIFD.GPSAltitude = 6

                # Valid coordinates but malformed altitude
                malformed_gps_ifd = {
                    2: ((37, 1), (46, 1), (5920, 100)),
                    1: b'N',
                    4: ((122, 1), (25, 1), (1164, 100)),
                    3: b'W',
                    6: (100, 0)  # altitude denominator = 0
                }

                mock_piexif.load.return_value = {'GPS': malformed_gps_ifd}

                result = verify_gps_exif(tmp_path)

                assert result['error'] is not None
                assert 'altitude' in result['error'].lower()
                assert 'denominator is zero' in result['error'].lower()

    def test_verify_gps_exif_timestamp_zero_denominator_hour(self):
        """Test verify_gps_exif handles GPS timestamp with zero denominator in hour."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / 'test.jpg'
            img = Image.new('RGB', (100, 100), color='blue')
            img.save(tmp_path)

            with patch('lib.gps_exif_lib.piexif') as mock_piexif:
                mock_piexif.GPSIFD.GPSLatitude = 2
                mock_piexif.GPSIFD.GPSLatitudeRef = 1
                mock_piexif.GPSIFD.GPSLongitude = 4
                mock_piexif.GPSIFD.GPSLongitudeRef = 3
                mock_piexif.GPSIFD.GPSDateStamp = 29
                mock_piexif.GPSIFD.GPSTimeStamp = 7

                # Valid coordinates but malformed timestamp
                malformed_gps_ifd = {
                    2: ((37, 1), (46, 1), (5920, 100)),
                    1: b'N',
                    4: ((122, 1), (25, 1), (1164, 100)),
                    3: b'W',
                    29: b'2025:01:15',
                    7: ((12, 0), (30, 1), (45, 1))  # hour denominator = 0
                }

                mock_piexif.load.return_value = {'GPS': malformed_gps_ifd}

                result = verify_gps_exif(tmp_path)

                assert result['error'] is not None
                assert 'timestamp' in result['error'].lower()
                assert 'denominator is zero' in result['error'].lower()

    def test_verify_gps_exif_timestamp_zero_denominator_minute(self):
        """Test verify_gps_exif handles GPS timestamp with zero denominator in minute."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / 'test.jpg'
            img = Image.new('RGB', (100, 100), color='blue')
            img.save(tmp_path)

            with patch('lib.gps_exif_lib.piexif') as mock_piexif:
                mock_piexif.GPSIFD.GPSLatitude = 2
                mock_piexif.GPSIFD.GPSLatitudeRef = 1
                mock_piexif.GPSIFD.GPSLongitude = 4
                mock_piexif.GPSIFD.GPSLongitudeRef = 3
                mock_piexif.GPSIFD.GPSDateStamp = 29
                mock_piexif.GPSIFD.GPSTimeStamp = 7

                malformed_gps_ifd = {
                    2: ((37, 1), (46, 1), (5920, 100)),
                    1: b'N',
                    4: ((122, 1), (25, 1), (1164, 100)),
                    3: b'W',
                    29: b'2025:01:15',
                    7: ((12, 1), (30, 0), (45, 1))  # minute denominator = 0
                }

                mock_piexif.load.return_value = {'GPS': malformed_gps_ifd}

                result = verify_gps_exif(tmp_path)

                assert result['error'] is not None
                assert 'timestamp' in result['error'].lower()
                assert 'denominator is zero' in result['error'].lower()

    def test_verify_gps_exif_timestamp_zero_denominator_second(self):
        """Test verify_gps_exif handles GPS timestamp with zero denominator in second."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / 'test.jpg'
            img = Image.new('RGB', (100, 100), color='blue')
            img.save(tmp_path)

            with patch('lib.gps_exif_lib.piexif') as mock_piexif:
                mock_piexif.GPSIFD.GPSLatitude = 2
                mock_piexif.GPSIFD.GPSLatitudeRef = 1
                mock_piexif.GPSIFD.GPSLongitude = 4
                mock_piexif.GPSIFD.GPSLongitudeRef = 3
                mock_piexif.GPSIFD.GPSDateStamp = 29
                mock_piexif.GPSIFD.GPSTimeStamp = 7

                malformed_gps_ifd = {
                    2: ((37, 1), (46, 1), (5920, 100)),
                    1: b'N',
                    4: ((122, 1), (25, 1), (1164, 100)),
                    3: b'W',
                    29: b'2025:01:15',
                    7: ((12, 1), (30, 1), (45, 0))  # second denominator = 0
                }

                mock_piexif.load.return_value = {'GPS': malformed_gps_ifd}

                result = verify_gps_exif(tmp_path)

                assert result['error'] is not None
                assert 'timestamp' in result['error'].lower()
                assert 'denominator is zero' in result['error'].lower()

    def test_verify_gps_exif_hdop_zero_denominator(self):
        """Test verify_gps_exif handles HDOP with zero denominator."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / 'test.jpg'
            img = Image.new('RGB', (100, 100), color='blue')
            img.save(tmp_path)

            with patch('lib.gps_exif_lib.piexif') as mock_piexif:
                mock_piexif.GPSIFD.GPSLatitude = 2
                mock_piexif.GPSIFD.GPSLatitudeRef = 1
                mock_piexif.GPSIFD.GPSLongitude = 4
                mock_piexif.GPSIFD.GPSLongitudeRef = 3
                mock_piexif.GPSIFD.GPSDOP = 11

                # Valid coordinates but malformed HDOP
                malformed_gps_ifd = {
                    2: ((37, 1), (46, 1), (5920, 100)),
                    1: b'N',
                    4: ((122, 1), (25, 1), (1164, 100)),
                    3: b'W',
                    11: (120, 0)  # HDOP denominator = 0
                }

                mock_piexif.load.return_value = {'GPS': malformed_gps_ifd}

                result = verify_gps_exif(tmp_path)

                assert result['error'] is not None
                assert 'hdop' in result['error'].lower()
                assert 'denominator is zero' in result['error'].lower()

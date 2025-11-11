"""
Unit tests for GPS EXIF library (lib/gps_exif_lib.py).

This test module implements TDD for Issue #98 GPS EXIF embedding feature.
Tests are written FIRST before implementation to drive design and ensure
comprehensive coverage.

Test Coverage:
- get_gps_data_from_controls(): GPS data extraction from controls.txt (Day 1)
- decimal_to_dms(): Coordinate conversion (Day 2)
- build_gps_ifd(): EXIF GPS IFD builder (Day 2)
- embed_gps_exif(): GPS EXIF embedding (Day 3)
- verify_gps_exif(): GPS EXIF verification (Day 3)
- is_already_tagged(): GPS tag detection (Day 3)

Fixtures:
- temp_controls_file: Isolated controls.txt for testing (from conftest.py)
- sample_photo: Test JPEG photo with minimal EXIF (defined below)

Related:
- Issue #98: https://github.com/zane-lazare/Mothbox/issues/98
- Implementation spec: webui/docs/dev/issues/ISSUE_98_GPS_EXIF_IMPLEMENTATION_SPEC.md
- TDD workflow: webui/docs/dev/guides/TDD_WORKFLOW.md
"""

import pytest
import sys
from pathlib import Path

# Add backend to path (standard pattern from test_mothbox_paths_hardware.py)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))


# ============================================================================
# Day 1: GPS Data Extraction Tests
# ============================================================================

class TestGPSDataExtraction:
    """
    Test get_gps_data_from_controls() function.

    This function reads GPS data from controls.txt and returns a structured
    dictionary with GPS coordinates, timestamp, precision metrics, and fix status.

    Expected function signature (from spec lines 160-181):
        def get_gps_data_from_controls() -> Dict[str, Any]:
            Returns:
                dict: GPS data with keys:
                    - latitude (float or None): Decimal latitude
                    - longitude (float or None): Decimal longitude
                    - gpstime (int): Unix timestamp from GPS
                    - altitude (float or None): Altitude in meters (if available)
                    - fix_mode (int): 0=no fix, 2=2D, 3=3D
                    - satellites_used (int): Number of satellites in fix
                    - hdop (float): Horizontal dilution of precision
                    - pdop (float): Position dilution of precision
                    - has_fix (bool): Whether GPS has valid position
    """

    def test_read_valid_gps_data(self, temp_controls_file):
        """
        Test reading valid GPS data from controls.txt (spec lines 930-940).

        Scenario: GPS module has good 3D fix with all metrics available.
        Expected: All GPS fields parsed correctly with proper types.
        """
        # Arrange: Write controls.txt with valid GPS fix (from readiness report)
        temp_controls_file.write_text("""
gpstime=1705329000
lat=37.7749
lon=-122.4194
gps_fix_mode=3
gps_satellites_used=8
gps_hdop=1.2
gps_pdop=2.1
""")

        # Act: Import and call function (will fail - not implemented yet)
        from lib.gps_exif_lib import get_gps_data_from_controls
        gps_data = get_gps_data_from_controls(temp_controls_file)

        # Assert: Verify all fields parsed correctly
        assert gps_data['latitude'] == 37.7749, "Latitude should be parsed as float"
        assert gps_data['longitude'] == -122.4194, "Longitude should be parsed as float"
        assert gps_data['gpstime'] == 1705329000, "GPS time should be parsed as int"
        assert gps_data['fix_mode'] == 3, "Fix mode should be parsed as int (3D fix)"
        assert gps_data['satellites_used'] == 8, "Satellites used should be parsed as int"
        assert gps_data['hdop'] == 1.2, "HDOP should be parsed as float"
        assert gps_data['pdop'] == 2.1, "PDOP should be parsed as float"
        assert gps_data['has_fix'] is True, "Should indicate valid GPS fix"

        print("\n✓ Valid GPS data parsed correctly")

    def test_read_no_gps_fix(self, temp_controls_file):
        """
        Test reading controls.txt with no GPS fix (spec lines 942-957).

        Scenario: GPS module has no satellite lock (coordinates = n/a).
        Expected: Latitude/longitude are None, has_fix is False.
        """
        # Arrange: Write controls.txt with no GPS fix
        temp_controls_file.write_text("""
gpstime=0
lat=n/a
lon=n/a
gps_fix_mode=0
gps_satellites_used=0
gps_hdop=99.99
gps_pdop=99.99
""")

        # Act: Import and call function
        from lib.gps_exif_lib import get_gps_data_from_controls
        gps_data = get_gps_data_from_controls(temp_controls_file)

        # Assert: Verify graceful handling of no fix
        assert gps_data['latitude'] is None, "Latitude should be None when n/a"
        assert gps_data['longitude'] is None, "Longitude should be None when n/a"
        assert gps_data['has_fix'] is False, "Should indicate no GPS fix"
        assert gps_data['fix_mode'] == 0, "Fix mode should be 0 (no fix)"
        assert gps_data['satellites_used'] == 0, "No satellites used"

        print("✓ No GPS fix handled gracefully")

    def test_missing_gps_fields(self, temp_controls_file):
        """
        Test reading controls.txt with missing GPS fields.

        Scenario: controls.txt exists but GPS fields are missing.
        Expected: Return default values, has_fix is False.
        """
        # Arrange: Write controls.txt without GPS fields
        temp_controls_file.write_text("""
# Configuration file without GPS data
Relay_Ch1=5
Relay_Ch2=19
Relay_Ch3=9
""")

        # Act: Import and call function
        from lib.gps_exif_lib import get_gps_data_from_controls
        gps_data = get_gps_data_from_controls(temp_controls_file)

        # Assert: Verify defaults when fields missing
        assert gps_data['latitude'] is None, "Missing latitude defaults to None"
        assert gps_data['longitude'] is None, "Missing longitude defaults to None"
        assert gps_data['has_fix'] is False, "Missing data means no fix"
        assert gps_data['gpstime'] == 0, "Missing gpstime defaults to 0"
        assert gps_data['fix_mode'] == 0, "Missing fix_mode defaults to 0"

        print("✓ Missing GPS fields handled with defaults")

    def test_partial_gps_data(self, temp_controls_file):
        """
        Test reading controls.txt with partial GPS data (some fields missing).

        Scenario: GPS has coordinates but missing precision metrics.
        Expected: Parse available fields, use defaults for missing ones.
        """
        # Arrange: Write controls.txt with partial GPS data
        temp_controls_file.write_text("""
gpstime=1705329000
lat=37.7749
lon=-122.4194
gps_fix_mode=2
# Missing: satellites_used, hdop, pdop
""")

        # Act: Import and call function
        from lib.gps_exif_lib import get_gps_data_from_controls
        gps_data = get_gps_data_from_controls(temp_controls_file)

        # Assert: Verify partial data handling
        assert gps_data['latitude'] == 37.7749, "Available latitude parsed"
        assert gps_data['longitude'] == -122.4194, "Available longitude parsed"
        assert gps_data['has_fix'] is True, "Has fix with valid coordinates"
        assert gps_data['satellites_used'] == 0, "Missing satellites_used defaults to 0"
        assert gps_data['hdop'] == 99.99, "Missing HDOP defaults to 99.99 (poor)"
        assert gps_data['pdop'] == 99.99, "Missing PDOP defaults to 99.99 (poor)"

        print("✓ Partial GPS data handled correctly")

    def test_altitude_when_3d_fix(self, temp_controls_file):
        """
        Test altitude parsing with 3D GPS fix.

        Scenario: GPS has 3D fix with altitude data.
        Expected: Altitude parsed as float.
        """
        # Arrange: Write controls.txt with altitude
        temp_controls_file.write_text("""
gpstime=1705329000
lat=37.7749
lon=-122.4194
gps_altitude=15.2
gps_fix_mode=3
""")

        # Act: Import and call function
        from lib.gps_exif_lib import get_gps_data_from_controls
        gps_data = get_gps_data_from_controls(temp_controls_file)

        # Assert: Verify altitude parsed
        assert gps_data['altitude'] == 15.2, "Altitude should be parsed as float"
        assert gps_data['fix_mode'] == 3, "3D fix includes altitude"

        print("✓ Altitude parsed correctly")

    def test_altitude_missing_2d_fix(self, temp_controls_file):
        """
        Test altitude handling with 2D GPS fix (no altitude).

        Scenario: GPS has 2D fix (lat/lon only, no altitude).
        Expected: Altitude is None.
        """
        # Arrange: Write controls.txt with 2D fix (no altitude)
        temp_controls_file.write_text("""
gpstime=1705329000
lat=37.7749
lon=-122.4194
gps_fix_mode=2
# No altitude field
""")

        # Act: Import and call function
        from lib.gps_exif_lib import get_gps_data_from_controls
        gps_data = get_gps_data_from_controls(temp_controls_file)

        # Assert: Verify altitude is None
        assert gps_data['altitude'] is None, "2D fix should have no altitude"
        assert gps_data['fix_mode'] == 2, "2D fix confirmed"

        print("✓ 2D fix (no altitude) handled correctly")

    def test_negative_coordinates(self, temp_controls_file):
        """
        Test parsing negative coordinates (southern latitudes, western longitudes).

        Scenario: GPS location in southern/western hemisphere.
        Expected: Negative values parsed correctly as floats.
        """
        # Arrange: Write controls.txt with negative coordinates
        temp_controls_file.write_text("""
gpstime=1705329000
lat=-33.8688
lon=151.2093
gps_fix_mode=3
""")

        # Act: Import and call function
        from lib.gps_exif_lib import get_gps_data_from_controls
        gps_data = get_gps_data_from_controls(temp_controls_file)

        # Assert: Verify negative coordinates
        assert gps_data['latitude'] == -33.8688, "Negative latitude (southern hemisphere)"
        assert gps_data['longitude'] == 151.2093, "Positive longitude (eastern hemisphere)"
        assert gps_data['has_fix'] is True, "Valid fix with negative coordinates"

        print("✓ Negative coordinates parsed correctly")

    def test_whitespace_handling(self, temp_controls_file):
        """
        Test whitespace handling in controls.txt (Issue #13 bug fix pattern).

        Scenario: GPS fields have leading/trailing whitespace.
        Expected: Whitespace stripped, values parsed correctly.
        """
        # Arrange: Write controls.txt with whitespace
        temp_controls_file.write_text("""
gpstime = 1705329000
lat  =  37.7749
lon=-122.4194
gps_fix_mode=3
""")

        # Act: Import and call function
        from lib.gps_exif_lib import get_gps_data_from_controls
        gps_data = get_gps_data_from_controls(temp_controls_file)

        # Assert: Verify whitespace stripped
        assert gps_data['latitude'] == 37.7749, "Whitespace should be stripped"
        assert gps_data['longitude'] == -122.4194, "Whitespace should be stripped"

        print("✓ Whitespace handling correct (Issue #13 pattern)")

    def test_invalid_coordinate_format(self, temp_controls_file):
        """
        Test handling of invalid coordinate formats.

        Scenario: Coordinates are not valid floats.
        Expected: Return None for invalid values, has_fix is False.
        """
        # Arrange: Write controls.txt with invalid coordinates
        temp_controls_file.write_text("""
gpstime=1705329000
lat=invalid
lon=also_invalid
gps_fix_mode=0
""")

        # Act: Import and call function
        from lib.gps_exif_lib import get_gps_data_from_controls
        gps_data = get_gps_data_from_controls(temp_controls_file)

        # Assert: Verify graceful handling of invalid data
        assert gps_data['latitude'] is None, "Invalid latitude should be None"
        assert gps_data['longitude'] is None, "Invalid longitude should be None"
        assert gps_data['has_fix'] is False, "Invalid coordinates mean no fix"

        print("✓ Invalid coordinate format handled gracefully")

    def test_extreme_coordinates(self, temp_controls_file):
        """
        Test parsing extreme coordinates (near poles and date line).

        Scenario: GPS at near-pole locations and international date line.
        Expected: Extreme values parsed correctly.
        """
        # Arrange: Write controls.txt with extreme coordinates
        temp_controls_file.write_text("""
gpstime=1705329000
lat=89.9999
lon=179.9999
gps_fix_mode=3
""")

        # Act: Import and call function
        from lib.gps_exif_lib import get_gps_data_from_controls
        gps_data = get_gps_data_from_controls(temp_controls_file)

        # Assert: Verify extreme coordinates
        assert gps_data['latitude'] == 89.9999, "Near-pole latitude parsed"
        assert gps_data['longitude'] == 179.9999, "Near date line longitude parsed"
        assert gps_data['has_fix'] is True, "Valid fix at extreme coordinates"

        print("✓ Extreme coordinates parsed correctly")


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_photo(tmp_path):
    """
    Create a minimal test JPEG photo (for later tests).

    Uses PIL to create a valid JPEG file with basic EXIF.
    This fixture will be used in Day 2-3 tests for EXIF embedding.

    Returns:
        Path: Path to test photo
    """
    try:
        from PIL import Image
        import piexif
    except ImportError:
        pytest.skip("PIL and piexif required for photo tests")

    # Create minimal JPEG
    photo = tmp_path / "test_photo.jpg"
    img = Image.new('RGB', (100, 100), color='red')

    # Add basic EXIF (camera metadata)
    exif_dict = {
        "0th": {
            piexif.ImageIFD.Make: b"TestCamera",
            piexif.ImageIFD.Model: b"TestModel"
        },
        "Exif": {
            piexif.ExifIFD.ExposureTime: (1, 100),
            piexif.ExifIFD.ISOSpeed: 100
        },
        "GPS": {}  # Empty GPS IFD (will be filled by tests)
    }

    exif_bytes = piexif.dump(exif_dict)
    img.save(photo, 'JPEG', exif=exif_bytes)

    return photo

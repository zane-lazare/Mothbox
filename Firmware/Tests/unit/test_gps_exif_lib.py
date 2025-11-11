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


# ============================================================================
# Day 2: Coordinate Conversion Tests
# ============================================================================

class TestCoordinateConversion:
    """
    Test decimal_to_dms() function for coordinate conversion.

    Converts decimal degrees to EXIF GPS DMS (Degrees, Minutes, Seconds) format.
    EXIF standard uses rational numbers for precision.

    Expected function signature (from spec lines 184-206):
        def decimal_to_dms(decimal: float, is_latitude: bool) -> Tuple[Tuple, str]:
            Args:
                decimal: Decimal degrees (e.g., 37.7749 or -122.4194)
                is_latitude: True if latitude, False if longitude
            Returns:
                tuple: (dms_tuple, ref_string) where:
                    - dms_tuple: ((degrees, 1), (minutes, 1), (seconds, 100))
                    - ref_string: 'N'/'S' for latitude, 'E'/'W' for longitude

    EXIF DMS Format:
        - Degrees: (degrees, 1) - whole degrees as rational
        - Minutes: (minutes, 1) - whole minutes as rational
        - Seconds: (seconds*100, 100) - seconds with 2 decimal places
    """

    def test_positive_latitude(self):
        """
        Test conversion of positive latitude (Northern hemisphere).

        Scenario: San Francisco latitude 37.7749° N
        Expected: 37°46'29.64"N
        EXIF format: ((37, 1), (46, 1), (2964, 100)) 'N'
        """
        from lib.gps_exif_lib import decimal_to_dms

        # Act: Convert decimal latitude to DMS
        dms, ref = decimal_to_dms(37.7749, is_latitude=True)

        # Assert: Verify DMS conversion
        assert ref == 'N', "Positive latitude should be North"
        assert dms[0] == (37, 1), "Degrees should be 37"
        assert dms[1] == (46, 1), "Minutes should be 46"
        # 0.7749 * 60 = 46.494 minutes
        # 0.494 * 60 = 29.64 seconds
        # 29.64 * 100 = 2964
        assert dms[2] == (2964, 100), "Seconds should be 2964/100 (29.64)"

        print("\n✓ Positive latitude converted to DMS correctly")

    def test_negative_latitude(self):
        """
        Test conversion of negative latitude (Southern hemisphere).

        Scenario: Sydney latitude -33.8688° S
        Expected: 33°52'7.68"S
        EXIF format: ((33, 1), (52, 1), (768, 100)) 'S'
        """
        from lib.gps_exif_lib import decimal_to_dms

        # Act: Convert negative latitude to DMS
        dms, ref = decimal_to_dms(-33.8688, is_latitude=True)

        # Assert: Verify DMS conversion
        assert ref == 'S', "Negative latitude should be South"
        assert dms[0] == (33, 1), "Degrees should be 33 (absolute value)"
        assert dms[1] == (52, 1), "Minutes should be 52"
        # 0.8688 * 60 = 52.128 minutes
        # 0.128 * 60 = 7.68 seconds
        # 7.68 * 100 = 768
        assert dms[2] == (768, 100), "Seconds should be 768/100 (7.68)"

        print("✓ Negative latitude (Southern) converted correctly")

    def test_positive_longitude(self):
        """
        Test conversion of positive longitude (Eastern hemisphere).

        Scenario: Sydney longitude 151.2093° E
        Expected: 151°12'33.48"E
        EXIF format: ((151, 1), (12, 1), (3348, 100)) 'E'
        """
        from lib.gps_exif_lib import decimal_to_dms

        # Act: Convert positive longitude to DMS
        dms, ref = decimal_to_dms(151.2093, is_latitude=False)

        # Assert: Verify DMS conversion
        assert ref == 'E', "Positive longitude should be East"
        assert dms[0] == (151, 1), "Degrees should be 151"
        assert dms[1] == (12, 1), "Minutes should be 12"
        # 0.2093 * 60 = 12.558 minutes
        # 0.558 * 60 = 33.48 seconds
        # 33.48 * 100 = 3348
        assert dms[2] == (3348, 100), "Seconds should be 3348/100 (33.48)"

        print("✓ Positive longitude (Eastern) converted correctly")

    def test_negative_longitude(self):
        """
        Test conversion of negative longitude (Western hemisphere).

        Scenario: San Francisco longitude -122.4194° W
        Expected: 122°25'9.84"W
        EXIF format: ((122, 1), (25, 1), (984, 100)) 'W'
        """
        from lib.gps_exif_lib import decimal_to_dms

        # Act: Convert negative longitude to DMS
        dms, ref = decimal_to_dms(-122.4194, is_latitude=False)

        # Assert: Verify DMS conversion
        assert ref == 'W', "Negative longitude should be West"
        assert dms[0] == (122, 1), "Degrees should be 122 (absolute value)"
        assert dms[1] == (25, 1), "Minutes should be 25"
        # 0.4194 * 60 = 25.164 minutes
        # 0.164 * 60 = 9.84 seconds
        # 9.84 * 100 = 984
        assert dms[2] == (984, 100), "Seconds should be 984/100 (9.84)"

        print("✓ Negative longitude (Western) converted correctly")

    def test_zero_coordinates(self):
        """
        Test conversion of zero coordinates (Null Island, Gulf of Guinea).

        Scenario: 0.0° latitude and 0.0° longitude
        Expected: 0°0'0.0"N and 0°0'0.0"E
        """
        from lib.gps_exif_lib import decimal_to_dms

        # Act: Convert zero coordinates
        lat_dms, lat_ref = decimal_to_dms(0.0, is_latitude=True)
        lon_dms, lon_ref = decimal_to_dms(0.0, is_latitude=False)

        # Assert: Verify zero handling
        assert lat_ref == 'N', "Zero latitude defaults to North"
        assert lat_dms == ((0, 1), (0, 1), (0, 100)), "Zero latitude DMS"
        assert lon_ref == 'E', "Zero longitude defaults to East"
        assert lon_dms == ((0, 1), (0, 1), (0, 100)), "Zero longitude DMS"

        print("✓ Zero coordinates handled correctly")

    def test_extreme_latitudes(self):
        """
        Test conversion of extreme latitudes (near poles).

        Scenario: Near North/South poles (89.9999°, -89.9999°)
        Expected: Proper handling of extreme values
        """
        from lib.gps_exif_lib import decimal_to_dms

        # Act: Convert near-pole latitudes
        north_dms, north_ref = decimal_to_dms(89.9999, is_latitude=True)
        south_dms, south_ref = decimal_to_dms(-89.9999, is_latitude=True)

        # Assert: Verify extreme latitude handling
        assert north_ref == 'N', "Near north pole should be North"
        assert north_dms[0] == (89, 1), "Degrees should be 89"
        # 0.9999 * 60 = 59.994 minutes
        assert north_dms[1] == (59, 1), "Minutes should be 59"

        assert south_ref == 'S', "Near south pole should be South"
        assert south_dms[0] == (89, 1), "Degrees should be 89 (absolute)"

        print("✓ Extreme latitudes (near poles) handled correctly")

    def test_extreme_longitudes(self):
        """
        Test conversion of extreme longitudes (date line).

        Scenario: International date line (180°, -180°)
        Expected: Both map to 180° (E/W ambiguous but valid)
        """
        from lib.gps_exif_lib import decimal_to_dms

        # Act: Convert date line longitudes
        east_dms, east_ref = decimal_to_dms(180.0, is_latitude=False)
        west_dms, west_ref = decimal_to_dms(-180.0, is_latitude=False)

        # Assert: Verify date line handling
        assert east_dms[0] == (180, 1), "180° East degrees"
        assert east_ref == 'E', "Positive 180° is East"

        assert west_dms[0] == (180, 1), "180° West degrees (absolute)"
        assert west_ref == 'W', "Negative 180° is West"

        print("✓ Extreme longitudes (date line) handled correctly")


# ============================================================================
# Day 3: GPS IFD Building Tests
# ============================================================================

class TestGPSIFDBuilder:
    """
    Test build_gps_ifd() function for creating piexif GPS IFD dictionaries.

    Creates GPS Image File Directory (IFD) compatible with EXIF 2.3 standard
    for embedding in JPEG files. Includes GPS coordinates, timestamp, altitude,
    precision metrics, and satellite count.

    Expected function signature (from spec lines 209-238):
        def build_gps_ifd(gps_data: Dict[str, Any]) -> Dict:
            Args:
                gps_data: GPS data dictionary from get_gps_data_from_controls()
            Returns:
                dict: piexif GPS IFD dictionary ready for embedding

    EXIF GPS tags (from spec Appendix A):
        - GPSVersionID: (2, 3, 0, 0) - EXIF 2.3 standard
        - GPSLatitude: DMS tuple
        - GPSLatitudeRef: b'N' or b'S'
        - GPSLongitude: DMS tuple
        - GPSLongitudeRef: b'E' or b'W'
        - GPSAltitude: (altitude_meters * 100, 100) if available
        - GPSAltitudeRef: 0 (above sea level) or 1 (below)
        - GPSTimeStamp: ((hour, 1), (minute, 1), (second, 1)) - UTC
        - GPSDateStamp: b'YYYY:MM:DD' - UTC date
        - GPSDOP: (hdop * 100, 100) - Dilution of precision
        - GPSSatellites: b"8" - Number of satellites
    """

    def test_build_complete_gps_ifd(self):
        """
        Test building GPS IFD with complete GPS data (3D fix).

        Scenario: GPS has 3D fix with all metrics available.
        Expected: Complete GPS IFD with all tags populated.
        """
        try:
            import piexif
        except ImportError:
            pytest.skip("piexif required for GPS IFD tests")

        from lib.gps_exif_lib import build_gps_ifd

        # Arrange: Complete GPS data (3D fix with altitude)
        gps_data = {
            'latitude': 37.7749,
            'longitude': -122.4194,
            'gpstime': 1705329000,  # 2024-01-15 12:30:00 UTC
            'altitude': 15.2,
            'fix_mode': 3,
            'satellites_used': 8,
            'hdop': 1.2,
            'pdop': 2.1,
            'has_fix': True
        }

        # Act: Build GPS IFD
        gps_ifd = build_gps_ifd(gps_data)

        # Assert: Verify all GPS tags present
        assert piexif.GPSIFD.GPSVersionID in gps_ifd, "GPS version should be present"
        assert gps_ifd[piexif.GPSIFD.GPSVersionID] == (2, 3, 0, 0), "EXIF 2.3 version"

        assert piexif.GPSIFD.GPSLatitudeRef in gps_ifd, "Latitude ref should be present"
        assert gps_ifd[piexif.GPSIFD.GPSLatitudeRef] == b'N', "North latitude"

        assert piexif.GPSIFD.GPSLatitude in gps_ifd, "Latitude should be present"
        # 37.7749° = 37°46'29.64"
        lat_dms = gps_ifd[piexif.GPSIFD.GPSLatitude]
        assert lat_dms[0] == (37, 1), "Latitude degrees"
        assert lat_dms[1] == (46, 1), "Latitude minutes"
        assert lat_dms[2] == (2964, 100), "Latitude seconds"

        assert piexif.GPSIFD.GPSLongitudeRef in gps_ifd, "Longitude ref should be present"
        assert gps_ifd[piexif.GPSIFD.GPSLongitudeRef] == b'W', "West longitude"

        assert piexif.GPSIFD.GPSLongitude in gps_ifd, "Longitude should be present"
        # -122.4194° = 122°25'9.84"W
        lon_dms = gps_ifd[piexif.GPSIFD.GPSLongitude]
        assert lon_dms[0] == (122, 1), "Longitude degrees"
        assert lon_dms[1] == (25, 1), "Longitude minutes"
        assert lon_dms[2] == (984, 100), "Longitude seconds"

        assert piexif.GPSIFD.GPSAltitude in gps_ifd, "Altitude should be present"
        assert gps_ifd[piexif.GPSIFD.GPSAltitude] == (1520, 100), "Altitude 15.2m"

        assert piexif.GPSIFD.GPSAltitudeRef in gps_ifd, "Altitude ref should be present"
        assert gps_ifd[piexif.GPSIFD.GPSAltitudeRef] == 0, "Above sea level"

        assert piexif.GPSIFD.GPSDOP in gps_ifd, "DOP should be present"
        assert gps_ifd[piexif.GPSIFD.GPSDOP] == (120, 100), "HDOP 1.2"

        assert piexif.GPSIFD.GPSSatellites in gps_ifd, "Satellites should be present"
        assert gps_ifd[piexif.GPSIFD.GPSSatellites] == b'8', "8 satellites"

        print("\n✓ Complete GPS IFD built successfully")

    def test_build_gps_ifd_no_altitude(self):
        """
        Test building GPS IFD with 2D fix (no altitude).

        Scenario: GPS has 2D fix (lat/lon only, no altitude data).
        Expected: GPS IFD without altitude tags.
        """
        try:
            import piexif
        except ImportError:
            pytest.skip("piexif required for GPS IFD tests")

        from lib.gps_exif_lib import build_gps_ifd

        # Arrange: 2D GPS fix (no altitude)
        gps_data = {
            'latitude': 37.7749,
            'longitude': -122.4194,
            'gpstime': 1705329000,
            'altitude': None,  # No altitude in 2D fix
            'fix_mode': 2,
            'satellites_used': 6,
            'hdop': 2.5,
            'pdop': 3.2,
            'has_fix': True
        }

        # Act: Build GPS IFD
        gps_ifd = build_gps_ifd(gps_data)

        # Assert: Verify altitude tags absent
        assert piexif.GPSIFD.GPSLatitude in gps_ifd, "Latitude should be present"
        assert piexif.GPSIFD.GPSLongitude in gps_ifd, "Longitude should be present"
        assert piexif.GPSIFD.GPSAltitude not in gps_ifd, "Altitude should be absent (2D fix)"
        assert piexif.GPSIFD.GPSAltitudeRef not in gps_ifd, "Altitude ref should be absent"

        print("✓ 2D fix GPS IFD (no altitude) built correctly")

    def test_gps_timestamp_conversion(self):
        """
        Test GPS timestamp conversion from Unix time to EXIF format.

        Scenario: Convert Unix timestamp to EXIF GPS timestamp/datestamp.
        Expected: GPSTimeStamp and GPSDateStamp in correct format.
        """
        try:
            import piexif
        except ImportError:
            pytest.skip("piexif required for GPS IFD tests")

        from lib.gps_exif_lib import build_gps_ifd
        from datetime import datetime, timezone

        # Arrange: GPS data with specific timestamp
        # 1705329000 = 2024-01-15 12:30:00 UTC
        gps_data = {
            'latitude': 37.7749,
            'longitude': -122.4194,
            'gpstime': 1705329000,
            'altitude': None,
            'fix_mode': 2,
            'satellites_used': 6,
            'hdop': 1.2,
            'pdop': 2.1,
            'has_fix': True
        }

        # Act: Build GPS IFD
        gps_ifd = build_gps_ifd(gps_data)

        # Assert: Verify timestamp conversion
        # Expected: 2024-01-15 12:30:00 UTC
        utc_time = datetime.fromtimestamp(1705329000, tz=timezone.utc)
        expected_date = f"{utc_time.year:04d}:{utc_time.month:02d}:{utc_time.day:02d}".encode('ascii')
        expected_time = ((utc_time.hour, 1), (utc_time.minute, 1), (utc_time.second, 1))

        assert piexif.GPSIFD.GPSDateStamp in gps_ifd, "GPS date should be present"
        assert gps_ifd[piexif.GPSIFD.GPSDateStamp] == expected_date, "GPS date format YYYY:MM:DD"

        assert piexif.GPSIFD.GPSTimeStamp in gps_ifd, "GPS time should be present"
        assert gps_ifd[piexif.GPSIFD.GPSTimeStamp] == expected_time, "GPS time as rationals"

        print("✓ GPS timestamp conversion correct")

    def test_gps_precision_encoding(self):
        """
        Test GPS precision (HDOP/PDOP) encoding as rationals.

        Scenario: Encode HDOP as rational number.
        Expected: HDOP encoded as (hdop*100, 100) for 2 decimal precision.
        """
        try:
            import piexif
        except ImportError:
            pytest.skip("piexif required for GPS IFD tests")

        from lib.gps_exif_lib import build_gps_ifd

        # Arrange: GPS data with specific HDOP
        gps_data = {
            'latitude': 37.7749,
            'longitude': -122.4194,
            'gpstime': 1705329000,
            'altitude': None,
            'fix_mode': 2,
            'satellites_used': 6,
            'hdop': 1.25,  # Should encode as (125, 100)
            'pdop': 2.1,
            'has_fix': True
        }

        # Act: Build GPS IFD
        gps_ifd = build_gps_ifd(gps_data)

        # Assert: Verify HDOP encoding
        assert piexif.GPSIFD.GPSDOP in gps_ifd, "DOP should be present"
        assert gps_ifd[piexif.GPSIFD.GPSDOP] == (125, 100), "HDOP 1.25 encoded as rational"

        print("✓ GPS precision (HDOP) encoded correctly")

    def test_satellite_count(self):
        """
        Test satellite count encoding as ASCII string.

        Scenario: Encode satellite count as bytes string.
        Expected: Number of satellites as ASCII bytes (e.g., b'8').
        """
        try:
            import piexif
        except ImportError:
            pytest.skip("piexif required for GPS IFD tests")

        from lib.gps_exif_lib import build_gps_ifd

        # Arrange: GPS data with satellite count
        gps_data = {
            'latitude': 37.7749,
            'longitude': -122.4194,
            'gpstime': 1705329000,
            'altitude': None,
            'fix_mode': 2,
            'satellites_used': 12,  # Should encode as b'12'
            'hdop': 1.2,
            'pdop': 2.1,
            'has_fix': True
        }

        # Act: Build GPS IFD
        gps_ifd = build_gps_ifd(gps_data)

        # Assert: Verify satellite count encoding
        assert piexif.GPSIFD.GPSSatellites in gps_ifd, "Satellites should be present"
        assert gps_ifd[piexif.GPSIFD.GPSSatellites] == b'12', "Satellites as ASCII bytes"

        print("✓ Satellite count encoded correctly")

    def test_no_gps_fix_returns_empty_ifd(self):
        """
        Test that no GPS fix returns empty IFD.

        Scenario: GPS has no fix (has_fix=False).
        Expected: Empty GPS IFD dictionary.
        """
        from lib.gps_exif_lib import build_gps_ifd

        # Arrange: No GPS fix
        gps_data = {
            'latitude': None,
            'longitude': None,
            'gpstime': 0,
            'altitude': None,
            'fix_mode': 0,
            'satellites_used': 0,
            'hdop': 99.99,
            'pdop': 99.99,
            'has_fix': False
        }

        # Act: Build GPS IFD
        gps_ifd = build_gps_ifd(gps_data)

        # Assert: Verify empty IFD
        assert gps_ifd == {}, "No GPS fix should return empty IFD"

        print("✓ No GPS fix returns empty IFD correctly")

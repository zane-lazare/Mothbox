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
        # Ensure PIL plugins are loaded (fixes test failures when running multiple tests)
        Image.init()
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

    def test_seconds_rounding_overflow(self):
        """
        Test DMS conversion handles seconds rounding to 60.00 correctly.

        Scenario: Coordinate with fractional seconds near 60 (e.g., 59.999)
        Expected: Seconds should carry over to minutes (not store 60.00 seconds)

        Bug: 37.78333305... → 37° 46' 59.999'' → rounds to 37° 46' 60.00''
        Fix: Should produce 37° 47' 0.00'' (carry seconds to minutes)
        """
        from lib.gps_exif_lib import decimal_to_dms

        # Act: Test coordinate that produces seconds = 59.999...
        # 37 + (46/60) + (59.999/3600) = 37.78333305...
        test_coord = 37 + (46/60) + (59.999/3600)
        dms, ref = decimal_to_dms(test_coord, is_latitude=True)

        # Assert: Seconds should be < 60 (either 0.00 with minutes+1, or 59.99)
        seconds_value = dms[2][0] / dms[2][1]
        assert seconds_value < 60, f"Seconds {seconds_value} should be < 60"

        # Verify the result is valid DMS (either carry-over or truncation)
        if seconds_value < 1.0:  # Carry-over occurred
            assert dms[0] == (37, 1), "Degrees should be 37"
            assert dms[1] == (47, 1), "Minutes should be 47 (carried over)"
            assert dms[2][0] < 100, "Seconds should be ~0.00 (5999 or less)"
        else:  # Truncation/clamping
            assert dms[0] == (37, 1), "Degrees should be 37"
            assert dms[1] == (46, 1), "Minutes should be 46"
            assert dms[2][0] <= 5999, "Seconds should be <= 5999 (59.99)"

        print(f"✓ Seconds overflow handled: {dms[0][0]}° {dms[1][0]}' {seconds_value:.2f}''")


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


# ============================================================================
# Day 4: EXIF Embedding Tests
# ============================================================================

@pytest.fixture
def sample_photo_with_exif(tmp_path):
    """
    Create a JPEG with camera EXIF (like TakePhoto.py creates).

    This simulates a photo from TakePhoto.py with camera metadata but empty GPS IFD.
    Used for testing GPS EXIF embedding while preserving camera metadata.

    Returns:
        Path: Path to test photo with camera EXIF
    """
    try:
        from PIL import Image
        import piexif
        # Ensure PIL plugins are loaded (fixes test failures when running multiple tests)
        Image.init()
    except ImportError:
        pytest.skip("PIL and piexif required for photo tests")

    photo = tmp_path / "test_photo_with_exif.jpg"
    img = Image.new('RGB', (100, 100), color='blue')

    # Add camera EXIF like TakePhoto.py does (from 5.x/TakePhoto.py lines 606-633)
    exif_dict = {
        "0th": {
            piexif.ImageIFD.Make: b"MothboxV5"
        },
        "Exif": {
            piexif.ExifIFD.ExposureTime: (1, 100),
            piexif.ExifIFD.ISOSpeed: 100,
        },
        "GPS": {},  # Empty GPS IFD (will be filled by embed_gps_exif)
        "1st": {
            piexif.ImageIFD.Make: b"Arducam64mp"
        }
    }
    exif_bytes = piexif.dump(exif_dict)
    img.save(photo, 'JPEG', exif=exif_bytes)

    return photo


class TestEXIFEmbedding:
    """
    Test embed_gps_exif() function for writing GPS EXIF to JPEG photos.

    This is the main function that writes GPS EXIF data into JPEG files
    in-place, preserving existing camera EXIF metadata.

    Expected function signature (from spec lines 241-289):
        def embed_gps_exif(
            photo_path: Path,
            gps_data: Optional[Dict[str, Any]] = None,
            backup: bool = False,
            dry_run: bool = False
        ) -> Dict[str, Any]:
            Returns:
                dict: Operation result with keys:
                    - success (bool): True if GPS EXIF was embedded
                    - skipped (bool): True if no GPS fix available
                    - error (str or None): Error message if failed
                    - gps_embedded (bool): True if GPS tags were written
                    - original_had_gps (bool): True if photo already had GPS EXIF
                    - backup_path (Path or None): Path to backup file if created
    """

    def test_embed_gps_exif_success(self, sample_photo_with_exif, tmp_path):
        """
        Test successfully embedding GPS EXIF into photo (spec lines 959-1006).

        Scenario: Photo without GPS + valid GPS data = GPS EXIF embedded.
        Expected: GPS tags written, camera EXIF preserved, success result.
        """
        try:
            import piexif
        except ImportError:
            pytest.skip("piexif required for EXIF embedding tests")

        from lib.gps_exif_lib import embed_gps_exif

        # Arrange: GPS data with valid 3D fix
        gps_data = {
            'latitude': 37.7749,
            'longitude': -122.4194,
            'gpstime': 1705329000,
            'altitude': 15.2,
            'fix_mode': 3,
            'satellites_used': 8,
            'hdop': 1.2,
            'pdop': 2.1,
            'has_fix': True
        }

        # Act: Embed GPS EXIF into photo
        result = embed_gps_exif(sample_photo_with_exif, gps_data=gps_data)

        # Assert: Verify successful embedding
        assert result['success'] is True, "Should succeed with valid GPS data"
        assert result['skipped'] is False, "Should not skip when GPS fix available"
        assert result['error'] is None, "Should have no errors"
        assert result['gps_embedded'] is True, "GPS tags should be written"
        assert result['original_had_gps'] is False, "Photo originally had no GPS"
        assert result['backup_path'] is None, "No backup created (backup=False)"

        # Verify GPS EXIF was written to photo
        exif_dict = piexif.load(str(sample_photo_with_exif))
        assert piexif.GPSIFD.GPSLatitude in exif_dict['GPS'], "GPS latitude should be present"
        assert piexif.GPSIFD.GPSLongitude in exif_dict['GPS'], "GPS longitude should be present"

        # Verify camera EXIF preserved
        assert exif_dict['0th'][piexif.ImageIFD.Make] == b"MothboxV5", "Camera make preserved"
        assert exif_dict['Exif'][piexif.ExifIFD.ExposureTime] == (1, 100), "Exposure time preserved"

        print("\n✓ GPS EXIF embedded successfully")

    def test_embed_gps_exif_no_fix(self, sample_photo_with_exif):
        """
        Test skipping when no GPS fix available (spec lines 1008-1020).

        Scenario: GPS has no fix (has_fix=False).
        Expected: Skip embedding, return skipped=True, photo unchanged.
        """
        from lib.gps_exif_lib import embed_gps_exif

        # Arrange: GPS data with no fix
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

        # Act: Attempt to embed GPS EXIF
        result = embed_gps_exif(sample_photo_with_exif, gps_data=gps_data)

        # Assert: Verify skipped
        assert result['success'] is False, "Should not succeed without GPS fix"
        assert result['skipped'] is True, "Should skip when no GPS fix"
        assert result['gps_embedded'] is False, "No GPS tags written"

        print("✓ No GPS fix handled correctly (skipped)")

    def test_embed_gps_exif_idempotent(self, sample_photo_with_exif):
        """
        Test idempotency - safe to run multiple times (spec lines 1022-1040).

        Scenario: Run embed_gps_exif twice on same photo.
        Expected: Second run detects existing GPS, still succeeds but reports original_had_gps=True.
        """
        try:
            import piexif
        except ImportError:
            pytest.skip("piexif required for EXIF embedding tests")

        from lib.gps_exif_lib import embed_gps_exif

        # Arrange: GPS data
        gps_data = {
            'latitude': 37.7749,
            'longitude': -122.4194,
            'gpstime': 1705329000,
            'altitude': 15.2,
            'fix_mode': 3,
            'satellites_used': 8,
            'hdop': 1.2,
            'pdop': 2.1,
            'has_fix': True
        }

        # Act: Embed GPS EXIF first time
        result1 = embed_gps_exif(sample_photo_with_exif, gps_data=gps_data)

        # Verify first embedding
        assert result1['success'] is True, "First embedding should succeed"
        assert result1['original_had_gps'] is False, "Photo originally had no GPS"

        # Act: Embed GPS EXIF second time (idempotency test)
        result2 = embed_gps_exif(sample_photo_with_exif, gps_data=gps_data)

        # Assert: Second run detects existing GPS
        assert result2['success'] is True, "Second embedding should still succeed"
        assert result2['original_had_gps'] is True, "Photo now has GPS from first run"
        assert result2['gps_embedded'] is True, "GPS still written (updated)"

        # Verify GPS EXIF still present
        exif_dict = piexif.load(str(sample_photo_with_exif))
        assert piexif.GPSIFD.GPSLatitude in exif_dict['GPS'], "GPS latitude still present"

        print("✓ Idempotent - safe to run multiple times")

    def test_embed_gps_exif_with_backup(self, sample_photo_with_exif):
        """
        Test creating backup file before modifying (spec lines 1042-1055).

        Scenario: Run with backup=True.
        Expected: .bak file created, original modified, backup_path returned.
        """
        from lib.gps_exif_lib import embed_gps_exif

        # Arrange: GPS data
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

        # Act: Embed GPS EXIF with backup
        result = embed_gps_exif(sample_photo_with_exif, gps_data=gps_data, backup=True)

        # Assert: Verify backup created
        assert result['success'] is True, "Should succeed"
        assert result['backup_path'] is not None, "Backup path should be returned"
        assert result['backup_path'].exists(), "Backup file should exist"
        assert result['backup_path'].suffix == '.bak', "Backup should have .bak extension"

        # Verify original modified
        assert sample_photo_with_exif.exists(), "Original photo should still exist"

        print("✓ Backup file created successfully")

    def test_embed_gps_exif_dry_run(self, sample_photo_with_exif):
        """
        Test dry-run mode (validate but don't write) (spec lines 1057-1070).

        Scenario: Run with dry_run=True.
        Expected: Validation succeeds but photo unchanged.
        """
        try:
            import piexif
        except ImportError:
            pytest.skip("piexif required for EXIF embedding tests")

        from lib.gps_exif_lib import embed_gps_exif

        # Arrange: GPS data
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

        # Read original EXIF before dry-run
        original_exif = piexif.load(str(sample_photo_with_exif))

        # Act: Embed GPS EXIF in dry-run mode
        result = embed_gps_exif(sample_photo_with_exif, gps_data=gps_data, dry_run=True)

        # Assert: Verify dry-run succeeded but didn't modify photo
        assert result['success'] is True, "Dry-run should succeed"
        assert result['gps_embedded'] is False, "GPS not actually embedded in dry-run"

        # Verify photo unchanged
        current_exif = piexif.load(str(sample_photo_with_exif))
        assert current_exif['GPS'] == original_exif['GPS'], "GPS EXIF should be unchanged"

        print("✓ Dry-run mode validated without modifying photo")

    def test_embed_gps_exif_preserves_camera_exif(self, sample_photo_with_exif):
        """
        Test that camera EXIF metadata is preserved (spec requirement).

        Scenario: Photo has camera EXIF (Make, Model, ExposureTime, ISO).
        Expected: GPS EXIF added, camera EXIF preserved.
        """
        try:
            import piexif
        except ImportError:
            pytest.skip("piexif required for EXIF embedding tests")

        from lib.gps_exif_lib import embed_gps_exif

        # Arrange: GPS data
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

        # Read original camera EXIF
        original_exif = piexif.load(str(sample_photo_with_exif))

        # Act: Embed GPS EXIF
        result = embed_gps_exif(sample_photo_with_exif, gps_data=gps_data)

        # Assert: Verify camera EXIF preserved
        current_exif = piexif.load(str(sample_photo_with_exif))

        assert result['success'] is True, "Should succeed"

        # Check all camera EXIF preserved
        assert current_exif['0th'][piexif.ImageIFD.Make] == original_exif['0th'][piexif.ImageIFD.Make], "Camera make preserved"
        assert current_exif['Exif'][piexif.ExifIFD.ExposureTime] == original_exif['Exif'][piexif.ExifIFD.ExposureTime], "Exposure preserved"
        assert current_exif['Exif'][piexif.ExifIFD.ISOSpeed] == original_exif['Exif'][piexif.ExifIFD.ISOSpeed], "ISO preserved"
        # Note: 1st IFD (thumbnail) may be empty after save - PIL doesn't preserve it without actual thumbnail
        # This is acceptable behavior - main camera EXIF is preserved

        # Verify GPS was added
        assert piexif.GPSIFD.GPSLatitude in current_exif['GPS'], "GPS latitude added"
        assert piexif.GPSIFD.GPSLongitude in current_exif['GPS'], "GPS longitude added"

        print("✓ Camera EXIF preserved while adding GPS")

    def test_embed_gps_exif_invalid_file(self, tmp_path):
        """
        Test handling of non-existent or invalid files.

        Scenario: Photo path doesn't exist or is not a JPEG.
        Expected: Return error dict, don't crash.
        """
        from lib.gps_exif_lib import embed_gps_exif

        # Arrange: GPS data
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

        # Test 1: Non-existent file
        non_existent = tmp_path / "does_not_exist.jpg"
        result = embed_gps_exif(non_existent, gps_data=gps_data)

        assert result['success'] is False, "Should fail with non-existent file"
        assert result['error'] is not None, "Should return error message"
        assert 'exist' in result['error'].lower() or 'not found' in result['error'].lower(), "Error should mention file not found"

        # Test 2: Invalid file (not a JPEG)
        invalid_file = tmp_path / "invalid.txt"
        invalid_file.write_text("This is not a JPEG")

        result = embed_gps_exif(invalid_file, gps_data=gps_data)

        assert result['success'] is False, "Should fail with invalid file"
        assert result['error'] is not None, "Should return error message"

        print("✓ Invalid file errors handled gracefully")


# ============================================================================
# Day 5: GPS EXIF Verification Tests
# ============================================================================

class TestGPSEXIFVerification:
    """
    Test verify_gps_exif() and is_already_tagged() functions.

    These functions read GPS EXIF data from photos for verification,
    display, and idempotency checking.

    Expected function signatures:
        def verify_gps_exif(photo_path: Path) -> Dict[str, Any]:
            Returns:
                dict: GPS EXIF data with keys:
                    - has_gps (bool): True if GPS EXIF tags present
                    - latitude (float or None): Extracted latitude
                    - longitude (float or None): Extracted longitude
                    - timestamp (str or None): GPS timestamp
                    - altitude (float or None): Altitude in meters
                    - satellites (str or None): Number of satellites
                    - hdop (float or None): Horizontal DOP
                    - raw_gps_ifd (dict): Raw piexif GPS IFD

        def is_already_tagged(photo_path: Path) -> bool:
            Returns:
                bool: True if photo has GPSLatitude and GPSLongitude tags
    """

    def test_verify_gps_exif_with_gps(self, sample_photo_with_exif):
        """
        Test reading GPS EXIF from tagged photo.

        Scenario: Photo has GPS EXIF tags.
        Expected: Extract all GPS data correctly.
        """
        try:
            import piexif
        except ImportError:
            pytest.skip("piexif required for EXIF verification tests")

        from lib.gps_exif_lib import embed_gps_exif, verify_gps_exif

        # Arrange: Embed GPS EXIF first
        gps_data = {
            'latitude': 37.7749,
            'longitude': -122.4194,
            'gpstime': 1705329000,
            'altitude': 15.2,
            'fix_mode': 3,
            'satellites_used': 8,
            'hdop': 1.2,
            'pdop': 2.1,
            'has_fix': True
        }
        embed_gps_exif(sample_photo_with_exif, gps_data=gps_data)

        # Act: Verify GPS EXIF
        gps_info = verify_gps_exif(sample_photo_with_exif)

        # Assert: Verify extracted GPS data
        assert gps_info['has_gps'] is True, "Should detect GPS EXIF"
        assert gps_info['latitude'] is not None, "Latitude should be extracted"
        assert gps_info['longitude'] is not None, "Longitude should be extracted"
        assert abs(gps_info['latitude'] - 37.7749) < 0.0001, "Latitude should match (within DMS precision)"
        assert abs(gps_info['longitude'] - (-122.4194)) < 0.0001, "Longitude should match (within DMS precision)"
        assert gps_info['altitude'] is not None, "Altitude should be extracted"
        assert abs(gps_info['altitude'] - 15.2) < 0.01, "Altitude should match"
        assert gps_info['satellites'] == '8', "Satellite count should be extracted"
        assert gps_info['hdop'] is not None, "HDOP should be extracted"
        assert abs(gps_info['hdop'] - 1.2) < 0.01, "HDOP should match"
        assert gps_info['raw_gps_ifd'] is not None, "Raw GPS IFD should be included"

        print("\n✓ GPS EXIF verified from tagged photo")

    def test_verify_gps_exif_without_gps(self, sample_photo_with_exif):
        """
        Test reading GPS EXIF from photo without GPS tags.

        Scenario: Photo has no GPS EXIF.
        Expected: Return has_gps=False, all fields None.
        """
        from lib.gps_exif_lib import verify_gps_exif

        # Act: Verify GPS EXIF (photo has no GPS yet)
        gps_info = verify_gps_exif(sample_photo_with_exif)

        # Assert: Verify no GPS detected
        assert gps_info['has_gps'] is False, "Should detect no GPS EXIF"
        assert gps_info['latitude'] is None, "Latitude should be None"
        assert gps_info['longitude'] is None, "Longitude should be None"
        assert gps_info['altitude'] is None, "Altitude should be None"
        assert gps_info['satellites'] is None, "Satellites should be None"
        assert gps_info['hdop'] is None, "HDOP should be None"

        print("✓ No GPS EXIF detected correctly")

    def test_verify_gps_exif_extracts_coordinates(self, sample_photo_with_exif):
        """
        Test coordinate extraction accuracy.

        Scenario: Photo with GPS EXIF.
        Expected: Decimal coordinates extracted from DMS with <0.01° precision.
        """
        try:
            import piexif
        except ImportError:
            pytest.skip("piexif required for EXIF verification tests")

        from lib.gps_exif_lib import embed_gps_exif, verify_gps_exif

        # Arrange: Embed GPS with specific coordinates
        gps_data = {
            'latitude': -33.8688,  # Sydney (Southern hemisphere)
            'longitude': 151.2093,  # Sydney (Eastern hemisphere)
            'gpstime': 1705329000,
            'altitude': None,
            'fix_mode': 2,
            'satellites_used': 6,
            'hdop': 2.5,
            'pdop': 3.2,
            'has_fix': True
        }
        embed_gps_exif(sample_photo_with_exif, gps_data=gps_data)

        # Act: Verify GPS EXIF
        gps_info = verify_gps_exif(sample_photo_with_exif)

        # Assert: Verify coordinate extraction
        assert gps_info['has_gps'] is True, "Should detect GPS EXIF"
        assert abs(gps_info['latitude'] - (-33.8688)) < 0.0001, "Southern latitude extracted correctly"
        assert abs(gps_info['longitude'] - 151.2093) < 0.0001, "Eastern longitude extracted correctly"

        print("✓ Coordinates extracted with high precision")

    def test_is_already_tagged_true(self, sample_photo_with_exif):
        """
        Test detecting photo with GPS tags.

        Scenario: Photo has GPS EXIF.
        Expected: Return True.
        """
        try:
            import piexif
        except ImportError:
            pytest.skip("piexif required for EXIF verification tests")

        from lib.gps_exif_lib import embed_gps_exif, is_already_tagged

        # Arrange: Embed GPS EXIF first
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
        embed_gps_exif(sample_photo_with_exif, gps_data=gps_data)

        # Act: Check if tagged
        is_tagged = is_already_tagged(sample_photo_with_exif)

        # Assert: Should detect GPS tags
        assert is_tagged is True, "Should detect GPS tags"

        print("✓ Photo with GPS tags detected")

    def test_is_already_tagged_false(self, sample_photo_with_exif):
        """
        Test detecting photo without GPS tags.

        Scenario: Photo has no GPS EXIF.
        Expected: Return False.
        """
        from lib.gps_exif_lib import is_already_tagged

        # Act: Check if tagged (photo has no GPS yet)
        is_tagged = is_already_tagged(sample_photo_with_exif)

        # Assert: Should not detect GPS tags
        assert is_tagged is False, "Should not detect GPS tags"

        print("✓ Photo without GPS tags detected")

    def test_verify_gps_exif_invalid_file(self, tmp_path):
        """
        Test handling of invalid files.

        Scenario: File doesn't exist or is not a JPEG.
        Expected: Return has_gps=False, all fields None, no crash.
        """
        from lib.gps_exif_lib import verify_gps_exif

        # Test 1: Non-existent file
        non_existent = tmp_path / "does_not_exist.jpg"
        gps_info = verify_gps_exif(non_existent)

        assert gps_info['has_gps'] is False, "Non-existent file should have no GPS"
        assert gps_info['latitude'] is None, "Latitude should be None"

        # Test 2: Invalid file (not a JPEG)
        invalid_file = tmp_path / "invalid.txt"
        invalid_file.write_text("This is not a JPEG")

        gps_info = verify_gps_exif(invalid_file)

        assert gps_info['has_gps'] is False, "Invalid file should have no GPS"
        assert gps_info['latitude'] is None, "Latitude should be None"

        print("✓ Invalid file errors handled gracefully")

    def test_embed_gps_exif_reads_from_controls_txt(self, sample_photo_with_exif, temp_controls_file):
        """
        Test embed_gps_exif() reads GPS data from controls.txt when gps_data=None.

        Scenario: Call embed_gps_exif without providing gps_data parameter.
        Expected: Function reads GPS data from controls.txt automatically.
        """
        try:
            import piexif
        except ImportError:
            pytest.skip("piexif required for EXIF embedding tests")

        from lib.gps_exif_lib import embed_gps_exif

        # Arrange: Write GPS data to controls.txt
        temp_controls_file.write_text("""
gpstime=1705329000
lat=37.7749
lon=-122.4194
gps_fix_mode=3
gps_satellites_used=8
gps_hdop=1.2
gps_pdop=2.1
gps_altitude=15.2
""")

        # Act: Embed GPS EXIF without providing gps_data (should read from controls.txt)
        result = embed_gps_exif(sample_photo_with_exif, gps_data=None)

        # Assert: Should succeed by reading from controls.txt
        assert result['success'] is True, "Should succeed reading from controls.txt"
        assert result['gps_embedded'] is True, "GPS should be embedded"

        # Verify GPS EXIF was written
        exif_dict = piexif.load(str(sample_photo_with_exif))
        assert piexif.GPSIFD.GPSLatitude in exif_dict['GPS'], "GPS latitude should be present"

        print("✓ GPS data read from controls.txt automatically")

    def test_verify_gps_exif_timestamp_extraction(self, sample_photo_with_exif):
        """
        Test timestamp extraction from GPS EXIF.

        Scenario: Photo with GPS timestamp.
        Expected: Timestamp formatted correctly.
        """
        try:
            import piexif
        except ImportError:
            pytest.skip("piexif required for EXIF verification tests")

        from lib.gps_exif_lib import embed_gps_exif, verify_gps_exif

        # Arrange: Embed GPS with timestamp
        gps_data = {
            'latitude': 37.7749,
            'longitude': -122.4194,
            'gpstime': 1705329000,  # 2024-01-15 12:30:00 UTC
            'altitude': None,
            'fix_mode': 2,
            'satellites_used': 6,
            'hdop': 1.2,
            'pdop': 2.1,
            'has_fix': True
        }
        embed_gps_exif(sample_photo_with_exif, gps_data=gps_data)

        # Act: Verify GPS EXIF
        gps_info = verify_gps_exif(sample_photo_with_exif)

        # Assert: Timestamp should be extracted
        assert gps_info['timestamp'] is not None, "Timestamp should be extracted"
        assert '2024:01:15' in gps_info['timestamp'], "Date should be in timestamp"

        print("✓ GPS timestamp extracted correctly")

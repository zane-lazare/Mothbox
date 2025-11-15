"""
Unit tests for GPS coordinate utilities (webui/backend/utils/gps_coordinates.py).

This test module implements strict TDD for Phase 2 of GPS coordinate refactoring.
Tests are written FIRST before implementation to drive design and ensure
comprehensive coverage.

Test Coverage:
- decimal_to_dms(): Convert decimal degrees to DMS format
- dms_to_decimal(): Convert DMS format to decimal degrees
- validate_coordinate(): Validate coordinate ranges
- format_coordinate_display(): Format coordinates for display
- Round-trip accuracy: Decimal → DMS → Decimal

Test Data Sources:
- San Francisco: (37.7749, -122.4194) - from test_gps_exif_lib.py
- Sydney: (-33.8688, 151.2093) - from test_gps_exif_lib.py
- Dead Sea: (31.5, 35.5, -430.5m) - below sea level
- Mount Everest: (27.9881, 86.9250, 5364m) - high altitude
- North Pole: (90.0, 0.0)
- South Pole: (-90.0, 0.0)
- Date Line: (0.0, 180.0) and (0.0, -180.0)
- Null Island: (0.0, 0.0)

Related:
- Phase 2 Implementation Plan: Refactor GPS coordinate utilities
- Existing code: lib/gps_exif_lib.py (decimal_to_dms, nested dms_to_decimal)
- Target location: webui/backend/utils/gps_coordinates.py
"""

import pytest
import sys
from pathlib import Path

# Add backend to path (standard pattern from test_mothbox_paths_hardware.py)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))


# ============================================================================
# Test Data: Real-world coordinates
# ============================================================================

# Coordinates from existing tests (test_gps_exif_lib.py)
SAN_FRANCISCO = (37.7749, -122.4194)  # Northern, Western hemisphere
SYDNEY = (-33.8688, 151.2093)  # Southern, Eastern hemisphere
DEAD_SEA = (31.5, 35.5, -430.5)  # Below sea level (lat, lon, altitude)
MOUNT_EVEREST = (27.9881, 86.9250, 5364.0)  # High altitude
NULL_ISLAND = (0.0, 0.0)  # Equator and Prime Meridian
NORTH_POLE = (90.0, 0.0)
SOUTH_POLE = (-90.0, 0.0)
DATE_LINE_EAST = (0.0, 180.0)
DATE_LINE_WEST = (0.0, -180.0)


# ============================================================================
# TestDecimalToDMS: Test decimal to DMS conversion
# ============================================================================

class TestDecimalToDMS:
    """
    Test decimal_to_dms() function for coordinate conversion.

    Converts decimal degrees to DMS (Degrees, Minutes, Seconds) format.
    The function should NOT be EXIF-specific - it's a general coordinate utility.

    Expected function signature:
        def decimal_to_dms(decimal: float, is_latitude: bool) -> tuple[int, int, float, str]:
            Args:
                decimal: Decimal degrees (e.g., 37.7749 or -122.4194)
                is_latitude: True if latitude, False if longitude
            Returns:
                tuple: (degrees, minutes, seconds, ref) where:
                    - degrees: Whole degrees (int, always positive)
                    - minutes: Whole minutes (int, 0-59)
                    - seconds: Decimal seconds (float, 0.0-59.999...)
                    - ref: Hemisphere ('N'/'S' for latitude, 'E'/'W' for longitude)

    DMS Format:
        - Degrees: Integer whole degrees (absolute value)
        - Minutes: Integer whole minutes (0-59)
        - Seconds: Float decimal seconds (0.0-59.999...)
        - Reference: N/S/E/W hemisphere indicator
    """

    def test_positive_latitude_san_francisco(self):
        """
        Test conversion of positive latitude (Northern hemisphere).

        Scenario: San Francisco latitude 37.7749° N
        Expected: 37° 46' 29.64" N
        """
        from utils.gps_coordinates import decimal_to_dms

        # Act: Convert decimal latitude to DMS
        degrees, minutes, seconds, ref = decimal_to_dms(37.7749, is_latitude=True)

        # Assert: Verify DMS conversion
        assert ref == 'N', "Positive latitude should be North"
        assert degrees == 37, "Degrees should be 37"
        assert minutes == 46, "Minutes should be 46"
        # 0.7749 * 60 = 46.494 minutes
        # 0.494 * 60 = 29.64 seconds
        assert abs(seconds - 29.64) < 0.01, f"Seconds should be ~29.64, got {seconds}"

        print("\n✓ Positive latitude (San Francisco) converted to DMS correctly")

    def test_negative_latitude_sydney(self):
        """
        Test conversion of negative latitude (Southern hemisphere).

        Scenario: Sydney latitude -33.8688° S
        Expected: 33° 52' 7.68" S
        """
        from utils.gps_coordinates import decimal_to_dms

        # Act: Convert negative latitude to DMS
        degrees, minutes, seconds, ref = decimal_to_dms(-33.8688, is_latitude=True)

        # Assert: Verify DMS conversion
        assert ref == 'S', "Negative latitude should be South"
        assert degrees == 33, "Degrees should be 33 (absolute value)"
        assert minutes == 52, "Minutes should be 52"
        # 0.8688 * 60 = 52.128 minutes
        # 0.128 * 60 = 7.68 seconds
        assert abs(seconds - 7.68) < 0.01, f"Seconds should be ~7.68, got {seconds}"

        print("✓ Negative latitude (Sydney) converted correctly")

    def test_positive_longitude_sydney(self):
        """
        Test conversion of positive longitude (Eastern hemisphere).

        Scenario: Sydney longitude 151.2093° E
        Expected: 151° 12' 33.48" E
        """
        from utils.gps_coordinates import decimal_to_dms

        # Act: Convert positive longitude to DMS
        degrees, minutes, seconds, ref = decimal_to_dms(151.2093, is_latitude=False)

        # Assert: Verify DMS conversion
        assert ref == 'E', "Positive longitude should be East"
        assert degrees == 151, "Degrees should be 151"
        assert minutes == 12, "Minutes should be 12"
        # 0.2093 * 60 = 12.558 minutes
        # 0.558 * 60 = 33.48 seconds
        assert abs(seconds - 33.48) < 0.01, f"Seconds should be ~33.48, got {seconds}"

        print("✓ Positive longitude (Sydney) converted correctly")

    def test_negative_longitude_san_francisco(self):
        """
        Test conversion of negative longitude (Western hemisphere).

        Scenario: San Francisco longitude -122.4194° W
        Expected: 122° 25' 9.84" W
        """
        from utils.gps_coordinates import decimal_to_dms

        # Act: Convert negative longitude to DMS
        degrees, minutes, seconds, ref = decimal_to_dms(-122.4194, is_latitude=False)

        # Assert: Verify DMS conversion
        assert ref == 'W', "Negative longitude should be West"
        assert degrees == 122, "Degrees should be 122 (absolute value)"
        assert minutes == 25, "Minutes should be 25"
        # 0.4194 * 60 = 25.164 minutes
        # 0.164 * 60 = 9.84 seconds
        assert abs(seconds - 9.84) < 0.01, f"Seconds should be ~9.84, got {seconds}"

        print("✓ Negative longitude (San Francisco) converted correctly")

    def test_zero_latitude(self):
        """
        Test conversion of zero latitude (Equator).

        Scenario: 0.0° latitude
        Expected: 0° 0' 0.0" N (convention: zero defaults to North)
        """
        from utils.gps_coordinates import decimal_to_dms

        # Act: Convert zero latitude
        degrees, minutes, seconds, ref = decimal_to_dms(0.0, is_latitude=True)

        # Assert: Verify zero handling
        assert ref == 'N', "Zero latitude defaults to North"
        assert degrees == 0, "Degrees should be 0"
        assert minutes == 0, "Minutes should be 0"
        assert seconds == 0.0, "Seconds should be 0.0"

        print("✓ Zero latitude handled correctly")

    def test_zero_longitude(self):
        """
        Test conversion of zero longitude (Prime Meridian).

        Scenario: 0.0° longitude
        Expected: 0° 0' 0.0" E (convention: zero defaults to East)
        """
        from utils.gps_coordinates import decimal_to_dms

        # Act: Convert zero longitude
        degrees, minutes, seconds, ref = decimal_to_dms(0.0, is_latitude=False)

        # Assert: Verify zero handling
        assert ref == 'E', "Zero longitude defaults to East"
        assert degrees == 0, "Degrees should be 0"
        assert minutes == 0, "Minutes should be 0"
        assert seconds == 0.0, "Seconds should be 0.0"

        print("✓ Zero longitude handled correctly")

    def test_north_pole(self):
        """
        Test conversion of North Pole (90° N).

        Scenario: Maximum latitude 90.0° N
        Expected: 90° 0' 0.0" N
        """
        from utils.gps_coordinates import decimal_to_dms

        # Act: Convert north pole latitude
        degrees, minutes, seconds, ref = decimal_to_dms(90.0, is_latitude=True)

        # Assert: Verify extreme latitude
        assert ref == 'N', "90° should be North"
        assert degrees == 90, "Degrees should be 90"
        assert minutes == 0, "Minutes should be 0"
        assert seconds == 0.0, "Seconds should be 0.0"

        print("✓ North Pole (90°N) handled correctly")

    def test_south_pole(self):
        """
        Test conversion of South Pole (-90° S).

        Scenario: Minimum latitude -90.0° S
        Expected: 90° 0' 0.0" S
        """
        from utils.gps_coordinates import decimal_to_dms

        # Act: Convert south pole latitude
        degrees, minutes, seconds, ref = decimal_to_dms(-90.0, is_latitude=True)

        # Assert: Verify extreme latitude
        assert ref == 'S', "−90° should be South"
        assert degrees == 90, "Degrees should be 90 (absolute value)"
        assert minutes == 0, "Minutes should be 0"
        assert seconds == 0.0, "Seconds should be 0.0"

        print("✓ South Pole (−90°S) handled correctly")

    def test_date_line_east(self):
        """
        Test conversion of International Date Line (180° E).

        Scenario: Maximum longitude 180.0° E
        Expected: 180° 0' 0.0" E
        """
        from utils.gps_coordinates import decimal_to_dms

        # Act: Convert date line longitude (positive)
        degrees, minutes, seconds, ref = decimal_to_dms(180.0, is_latitude=False)

        # Assert: Verify date line handling
        assert ref == 'E', "180° should be East"
        assert degrees == 180, "Degrees should be 180"
        assert minutes == 0, "Minutes should be 0"
        assert seconds == 0.0, "Seconds should be 0.0"

        print("✓ Date Line (180°E) handled correctly")

    def test_date_line_west(self):
        """
        Test conversion of International Date Line (-180° W).

        Scenario: Minimum longitude -180.0° W
        Expected: 180° 0' 0.0" W
        """
        from utils.gps_coordinates import decimal_to_dms

        # Act: Convert date line longitude (negative)
        degrees, minutes, seconds, ref = decimal_to_dms(-180.0, is_latitude=False)

        # Assert: Verify date line handling
        assert ref == 'W', "−180° should be West"
        assert degrees == 180, "Degrees should be 180 (absolute value)"
        assert minutes == 0, "Minutes should be 0"
        assert seconds == 0.0, "Seconds should be 0.0"

        print("✓ Date Line (−180°W) handled correctly")

    def test_seconds_near_sixty(self):
        """
        Test DMS conversion with seconds near 60.0 (rounding overflow).

        Scenario: Coordinate with fractional seconds near 60 (e.g., 59.999)
        Expected: Seconds should carry over to minutes (not store 60.0 seconds)

        Bug pattern from existing code:
        37.78333305... → 37° 46' 59.999" → rounds to 37° 47' 0.00" (carry over)
        """
        from utils.gps_coordinates import decimal_to_dms

        # Act: Test coordinate that produces seconds = 59.999...
        # 37 + (46/60) + (59.999/3600) = 37.78333305...
        test_coord = 37 + (46/60) + (59.999/3600)
        degrees, minutes, seconds, ref = decimal_to_dms(test_coord, is_latitude=True)

        # Assert: Seconds should be < 60 (either carry-over or clamping)
        assert seconds < 60.0, f"Seconds {seconds} should be < 60"
        assert ref == 'N', "Should be North"
        assert degrees == 37, "Degrees should be 37"

        # Either carry-over occurred (minutes=47, seconds~0.0) or clamping (minutes=46, seconds<60)
        if seconds < 1.0:
            assert minutes == 47, "Minutes should be 47 (carried over from seconds)"
        else:
            assert minutes == 46, "Minutes should be 46 (seconds clamped)"
            assert seconds < 60.0, "Seconds should be < 60"

        print(f"✓ Seconds overflow handled: {degrees}° {minutes}' {seconds:.2f}\"")

    def test_invalid_latitude_too_high(self):
        """
        Test rejection of invalid latitude (> 90°).

        Scenario: Latitude 91.0° (invalid)
        Expected: Raise ValueError
        """
        from utils.gps_coordinates import decimal_to_dms

        # Act & Assert: Should raise ValueError
        with pytest.raises(ValueError, match="latitude.*range"):
            decimal_to_dms(91.0, is_latitude=True)

        print("✓ Invalid latitude (> 90°) rejected")

    def test_invalid_latitude_too_low(self):
        """
        Test rejection of invalid latitude (< -90°).

        Scenario: Latitude -91.0° (invalid)
        Expected: Raise ValueError
        """
        from utils.gps_coordinates import decimal_to_dms

        # Act & Assert: Should raise ValueError
        with pytest.raises(ValueError, match="latitude.*range"):
            decimal_to_dms(-91.0, is_latitude=True)

        print("✓ Invalid latitude (< −90°) rejected")

    def test_invalid_longitude_too_high(self):
        """
        Test rejection of invalid longitude (> 180°).

        Scenario: Longitude 181.0° (invalid)
        Expected: Raise ValueError
        """
        from utils.gps_coordinates import decimal_to_dms

        # Act & Assert: Should raise ValueError
        with pytest.raises(ValueError, match="longitude.*range"):
            decimal_to_dms(181.0, is_latitude=False)

        print("✓ Invalid longitude (> 180°) rejected")

    def test_invalid_longitude_too_low(self):
        """
        Test rejection of invalid longitude (< -180°).

        Scenario: Longitude -181.0° (invalid)
        Expected: Raise ValueError
        """
        from utils.gps_coordinates import decimal_to_dms

        # Act & Assert: Should raise ValueError
        with pytest.raises(ValueError, match="longitude.*range"):
            decimal_to_dms(-181.0, is_latitude=False)

        print("✓ Invalid longitude (< −180°) rejected")

    def test_invalid_nan(self):
        """
        Test rejection of NaN (Not a Number).

        Scenario: Coordinate is NaN
        Expected: Raise ValueError
        """
        from utils.gps_coordinates import decimal_to_dms

        # Act & Assert: Should raise ValueError
        with pytest.raises(ValueError, match="NaN"):
            decimal_to_dms(float('nan'), is_latitude=True)

        print("✓ NaN coordinate rejected")

    def test_invalid_infinity(self):
        """
        Test rejection of infinity.

        Scenario: Coordinate is infinity
        Expected: Raise ValueError
        """
        from utils.gps_coordinates import decimal_to_dms

        # Act & Assert: Should raise ValueError
        with pytest.raises(ValueError, match="infinity"):
            decimal_to_dms(float('inf'), is_latitude=True)

        print("✓ Infinity coordinate rejected")

    @pytest.mark.parametrize("decimal,is_latitude,expected_degrees,expected_ref", [
        (37.7749, True, 37, 'N'),  # San Francisco latitude
        (-33.8688, True, 33, 'S'),  # Sydney latitude
        (151.2093, False, 151, 'E'),  # Sydney longitude
        (-122.4194, False, 122, 'W'),  # San Francisco longitude
        (0.0, True, 0, 'N'),  # Equator
        (0.0, False, 0, 'E'),  # Prime Meridian
        (90.0, True, 90, 'N'),  # North Pole
        (-90.0, True, 90, 'S'),  # South Pole
        (180.0, False, 180, 'E'),  # Date Line East
        (-180.0, False, 180, 'W'),  # Date Line West
    ])
    def test_multiple_coordinates_parametrized(self, decimal, is_latitude, expected_degrees, expected_ref):
        """
        Parametrized test for multiple coordinate conversions.

        Tests a variety of real-world and edge-case coordinates.
        """
        from utils.gps_coordinates import decimal_to_dms

        # Act: Convert decimal to DMS
        degrees, minutes, seconds, ref = decimal_to_dms(decimal, is_latitude=is_latitude)

        # Assert: Verify degrees and reference
        assert degrees == expected_degrees, f"Degrees mismatch for {decimal}"
        assert ref == expected_ref, f"Reference mismatch for {decimal}"
        assert 0 <= minutes <= 59, f"Minutes {minutes} out of range"
        assert 0.0 <= seconds < 60.0, f"Seconds {seconds} out of range"

        print(f"✓ {decimal}° → {degrees}° {minutes}' {seconds:.2f}\" {ref}")


# ============================================================================
# TestDMSToDecimal: Test DMS to decimal conversion
# ============================================================================

class TestDMSToDecimal:
    """
    Test dms_to_decimal() function for reverse coordinate conversion.

    Converts DMS (Degrees, Minutes, Seconds) format to decimal degrees.
    This is the inverse of decimal_to_dms().

    Expected function signature:
        def dms_to_decimal(degrees: int, minutes: int, seconds: float, ref: str) -> float:
            Args:
                degrees: Whole degrees (int, always positive)
                minutes: Whole minutes (int, 0-59)
                seconds: Decimal seconds (float, 0.0-59.999...)
                ref: Hemisphere ('N'/'S' for latitude, 'E'/'W' for longitude)
            Returns:
                float: Decimal degrees (negative for S/W)
    """

    def test_north_latitude(self):
        """
        Test DMS to decimal conversion for Northern latitude.

        Scenario: 37° 46' 29.64" N (San Francisco)
        Expected: 37.7749°
        """
        from utils.gps_coordinates import dms_to_decimal

        # Act: Convert DMS to decimal
        decimal = dms_to_decimal(37, 46, 29.64, 'N')

        # Assert: Verify decimal conversion
        assert abs(decimal - 37.7749) < 0.0001, f"Expected ~37.7749, got {decimal}"

        print("\n✓ North latitude DMS → decimal conversion correct")

    def test_south_latitude(self):
        """
        Test DMS to decimal conversion for Southern latitude.

        Scenario: 33° 52' 7.68" S (Sydney)
        Expected: -33.8688°
        """
        from utils.gps_coordinates import dms_to_decimal

        # Act: Convert DMS to decimal
        decimal = dms_to_decimal(33, 52, 7.68, 'S')

        # Assert: Verify decimal conversion (negative for South)
        assert abs(decimal - (-33.8688)) < 0.0001, f"Expected ~-33.8688, got {decimal}"

        print("✓ South latitude DMS → decimal conversion correct")

    def test_east_longitude(self):
        """
        Test DMS to decimal conversion for Eastern longitude.

        Scenario: 151° 12' 33.48" E (Sydney)
        Expected: 151.2093°
        """
        from utils.gps_coordinates import dms_to_decimal

        # Act: Convert DMS to decimal
        decimal = dms_to_decimal(151, 12, 33.48, 'E')

        # Assert: Verify decimal conversion
        assert abs(decimal - 151.2093) < 0.0001, f"Expected ~151.2093, got {decimal}"

        print("✓ East longitude DMS → decimal conversion correct")

    def test_west_longitude(self):
        """
        Test DMS to decimal conversion for Western longitude.

        Scenario: 122° 25' 9.84" W (San Francisco)
        Expected: -122.4194°
        """
        from utils.gps_coordinates import dms_to_decimal

        # Act: Convert DMS to decimal
        decimal = dms_to_decimal(122, 25, 9.84, 'W')

        # Assert: Verify decimal conversion (negative for West)
        assert abs(decimal - (-122.4194)) < 0.0001, f"Expected ~-122.4194, got {decimal}"

        print("✓ West longitude DMS → decimal conversion correct")

    def test_zero_coordinates(self):
        """
        Test DMS to decimal conversion for zero coordinates.

        Scenario: 0° 0' 0.0" N/E
        Expected: 0.0°
        """
        from utils.gps_coordinates import dms_to_decimal

        # Act: Convert zero DMS to decimal
        lat_decimal = dms_to_decimal(0, 0, 0.0, 'N')
        lon_decimal = dms_to_decimal(0, 0, 0.0, 'E')

        # Assert: Verify zero handling
        assert lat_decimal == 0.0, "Zero latitude should be 0.0"
        assert lon_decimal == 0.0, "Zero longitude should be 0.0"

        print("✓ Zero coordinates DMS → decimal conversion correct")

    @pytest.mark.parametrize("degrees,minutes,seconds,ref,expected", [
        (37, 46, 29.64, 'N', 37.7749),  # San Francisco lat
        (33, 52, 7.68, 'S', -33.8688),  # Sydney lat
        (151, 12, 33.48, 'E', 151.2093),  # Sydney lon
        (122, 25, 9.84, 'W', -122.4194),  # San Francisco lon
        (0, 0, 0.0, 'N', 0.0),  # Zero north
        (0, 0, 0.0, 'E', 0.0),  # Zero east
        (90, 0, 0.0, 'N', 90.0),  # North Pole
        (90, 0, 0.0, 'S', -90.0),  # South Pole
        (180, 0, 0.0, 'E', 180.0),  # Date Line East
        (180, 0, 0.0, 'W', -180.0),  # Date Line West
    ])
    def test_multiple_dms_to_decimal(self, degrees, minutes, seconds, ref, expected):
        """
        Parametrized test for multiple DMS → decimal conversions.
        """
        from utils.gps_coordinates import dms_to_decimal

        # Act: Convert DMS to decimal
        decimal = dms_to_decimal(degrees, minutes, seconds, ref)

        # Assert: Verify conversion
        assert abs(decimal - expected) < 0.0001, f"Expected {expected}, got {decimal}"

        print(f"✓ {degrees}° {minutes}' {seconds:.2f}\" {ref} → {decimal}°")


# ============================================================================
# TestValidateCoordinate: Test coordinate validation
# ============================================================================

class TestValidateCoordinate:
    """
    Test validate_coordinate() function for coordinate range validation.

    Validates that coordinates are within valid ranges:
    - Latitude: -90 to 90 degrees
    - Longitude: -180 to 180 degrees

    Expected function signature:
        def validate_coordinate(decimal: float, is_latitude: bool) -> bool:
            Args:
                decimal: Decimal degrees
                is_latitude: True if latitude, False if longitude
            Returns:
                bool: True if valid, False otherwise
    """

    def test_valid_latitude_mid_range(self):
        """
        Test validation of mid-range latitude.

        Scenario: Latitude 37.7749° (San Francisco)
        Expected: Valid (True)
        """
        from utils.gps_coordinates import validate_coordinate

        # Act: Validate latitude
        is_valid = validate_coordinate(37.7749, is_latitude=True)

        # Assert: Should be valid
        assert is_valid is True, "Mid-range latitude should be valid"

        print("\n✓ Valid mid-range latitude accepted")

    def test_valid_longitude_mid_range(self):
        """
        Test validation of mid-range longitude.

        Scenario: Longitude -122.4194° (San Francisco)
        Expected: Valid (True)
        """
        from utils.gps_coordinates import validate_coordinate

        # Act: Validate longitude
        is_valid = validate_coordinate(-122.4194, is_latitude=False)

        # Assert: Should be valid
        assert is_valid is True, "Mid-range longitude should be valid"

        print("✓ Valid mid-range longitude accepted")

    def test_valid_latitude_boundaries(self):
        """
        Test validation of latitude boundaries (±90°).

        Scenario: Latitudes 90.0, -90.0
        Expected: Both valid (True)
        """
        from utils.gps_coordinates import validate_coordinate

        # Act: Validate boundary latitudes
        is_valid_north = validate_coordinate(90.0, is_latitude=True)
        is_valid_south = validate_coordinate(-90.0, is_latitude=True)

        # Assert: Both should be valid
        assert is_valid_north is True, "90° latitude should be valid"
        assert is_valid_south is True, "−90° latitude should be valid"

        print("✓ Latitude boundaries (±90°) accepted")

    def test_valid_longitude_boundaries(self):
        """
        Test validation of longitude boundaries (±180°).

        Scenario: Longitudes 180.0, -180.0
        Expected: Both valid (True)
        """
        from utils.gps_coordinates import validate_coordinate

        # Act: Validate boundary longitudes
        is_valid_east = validate_coordinate(180.0, is_latitude=False)
        is_valid_west = validate_coordinate(-180.0, is_latitude=False)

        # Assert: Both should be valid
        assert is_valid_east is True, "180° longitude should be valid"
        assert is_valid_west is True, "−180° longitude should be valid"

        print("✓ Longitude boundaries (±180°) accepted")

    def test_invalid_latitude_too_high(self):
        """
        Test rejection of latitude > 90°.

        Scenario: Latitude 91.0°
        Expected: Invalid (False)
        """
        from utils.gps_coordinates import validate_coordinate

        # Act: Validate invalid latitude
        is_valid = validate_coordinate(91.0, is_latitude=True)

        # Assert: Should be invalid
        assert is_valid is False, "Latitude > 90° should be invalid"

        print("✓ Invalid latitude (> 90°) rejected")

    def test_invalid_latitude_too_low(self):
        """
        Test rejection of latitude < -90°.

        Scenario: Latitude -91.0°
        Expected: Invalid (False)
        """
        from utils.gps_coordinates import validate_coordinate

        # Act: Validate invalid latitude
        is_valid = validate_coordinate(-91.0, is_latitude=True)

        # Assert: Should be invalid
        assert is_valid is False, "Latitude < −90° should be invalid"

        print("✓ Invalid latitude (< −90°) rejected")

    def test_invalid_longitude_too_high(self):
        """
        Test rejection of longitude > 180°.

        Scenario: Longitude 181.0°
        Expected: Invalid (False)
        """
        from utils.gps_coordinates import validate_coordinate

        # Act: Validate invalid longitude
        is_valid = validate_coordinate(181.0, is_latitude=False)

        # Assert: Should be invalid
        assert is_valid is False, "Longitude > 180° should be invalid"

        print("✓ Invalid longitude (> 180°) rejected")

    def test_invalid_longitude_too_low(self):
        """
        Test rejection of longitude < -180°.

        Scenario: Longitude -181.0°
        Expected: Invalid (False)
        """
        from utils.gps_coordinates import validate_coordinate

        # Act: Validate invalid longitude
        is_valid = validate_coordinate(-181.0, is_latitude=False)

        # Assert: Should be invalid
        assert is_valid is False, "Longitude < −180° should be invalid"

        print("✓ Invalid longitude (< −180°) rejected")

    def test_invalid_nan(self):
        """
        Test rejection of NaN coordinates.

        Scenario: Coordinate is NaN
        Expected: Invalid (False)
        """
        from utils.gps_coordinates import validate_coordinate

        # Act: Validate NaN
        is_valid = validate_coordinate(float('nan'), is_latitude=True)

        # Assert: Should be invalid
        assert is_valid is False, "NaN should be invalid"

        print("✓ NaN coordinate rejected")

    def test_invalid_infinity(self):
        """
        Test rejection of infinity coordinates.

        Scenario: Coordinate is infinity
        Expected: Invalid (False)
        """
        from utils.gps_coordinates import validate_coordinate

        # Act: Validate infinity
        is_valid = validate_coordinate(float('inf'), is_latitude=True)

        # Assert: Should be invalid
        assert is_valid is False, "Infinity should be invalid"

        print("✓ Infinity coordinate rejected")


# ============================================================================
# TestFormatCoordinateDisplay: Test coordinate formatting
# ============================================================================

class TestFormatCoordinateDisplay:
    """
    Test format_coordinate_display() function for user-friendly coordinate formatting.

    Formats coordinates for display in various formats:
    - DMS: "37°46'29.64\"N"
    - Decimal: "37.774900°N"
    - Short: "37.77°N"

    Expected function signature:
        def format_coordinate_display(
            decimal: float,
            is_latitude: bool,
            format: str = 'dms'
        ) -> str:
            Args:
                decimal: Decimal degrees
                is_latitude: True if latitude, False if longitude
                format: 'dms', 'decimal', or 'short'
            Returns:
                str: Formatted coordinate string
    """

    def test_format_dms_north_latitude(self):
        """
        Test DMS format for Northern latitude.

        Scenario: San Francisco latitude 37.7749° N
        Expected: "37°46'29.64\"N"
        """
        from utils.gps_coordinates import format_coordinate_display

        # Act: Format as DMS
        formatted = format_coordinate_display(37.7749, is_latitude=True, format='dms')

        # Assert: Verify DMS format
        assert '37°' in formatted, "Should contain degrees"
        assert '46\'' in formatted, "Should contain minutes"
        assert 'N' in formatted, "Should contain North reference"
        # Note: Exact seconds formatting may vary (29.64 vs 29.6)

        print(f"\n✓ DMS format: {formatted}")

    def test_format_decimal_north_latitude(self):
        """
        Test decimal format for Northern latitude.

        Scenario: San Francisco latitude 37.7749° N
        Expected: "37.774900°N" (6 decimal places)
        """
        from utils.gps_coordinates import format_coordinate_display

        # Act: Format as decimal
        formatted = format_coordinate_display(37.7749, is_latitude=True, format='decimal')

        # Assert: Verify decimal format
        assert '37.7749' in formatted, "Should contain decimal value"
        assert '°N' in formatted, "Should contain degree symbol and North"

        print(f"✓ Decimal format: {formatted}")

    def test_format_short_north_latitude(self):
        """
        Test short format for Northern latitude.

        Scenario: San Francisco latitude 37.7749° N
        Expected: "37.77°N" (2 decimal places)
        """
        from utils.gps_coordinates import format_coordinate_display

        # Act: Format as short
        formatted = format_coordinate_display(37.7749, is_latitude=True, format='short')

        # Assert: Verify short format
        assert '37.77' in formatted, "Should contain 2 decimal places"
        assert '°N' in formatted, "Should contain degree symbol and North"

        print(f"✓ Short format: {formatted}")

    def test_format_dms_west_longitude(self):
        """
        Test DMS format for Western longitude.

        Scenario: San Francisco longitude -122.4194° W
        Expected: "122°25'9.84\"W"
        """
        from utils.gps_coordinates import format_coordinate_display

        # Act: Format as DMS
        formatted = format_coordinate_display(-122.4194, is_latitude=False, format='dms')

        # Assert: Verify DMS format
        assert '122°' in formatted, "Should contain degrees"
        assert '25\'' in formatted, "Should contain minutes"
        assert 'W' in formatted, "Should contain West reference"

        print(f"✓ DMS format (longitude): {formatted}")

    def test_format_decimal_south_latitude(self):
        """
        Test decimal format for Southern latitude.

        Scenario: Sydney latitude -33.8688° S
        Expected: "33.868800°S" (absolute value with S reference)
        """
        from utils.gps_coordinates import format_coordinate_display

        # Act: Format as decimal
        formatted = format_coordinate_display(-33.8688, is_latitude=True, format='decimal')

        # Assert: Verify decimal format (should show absolute value with S)
        assert '33.8688' in formatted, "Should contain absolute decimal value"
        assert '°S' in formatted, "Should contain degree symbol and South"
        assert '-' not in formatted, "Should not contain negative sign (ref handles sign)"

        print(f"✓ Decimal format (Southern): {formatted}")

    def test_format_short_east_longitude(self):
        """
        Test short format for Eastern longitude.

        Scenario: Sydney longitude 151.2093° E
        Expected: "151.21°E"
        """
        from utils.gps_coordinates import format_coordinate_display

        # Act: Format as short
        formatted = format_coordinate_display(151.2093, is_latitude=False, format='short')

        # Assert: Verify short format
        assert '151.21' in formatted, "Should contain 2 decimal places"
        assert '°E' in formatted, "Should contain degree symbol and East"

        print(f"✓ Short format (Eastern longitude): {formatted}")


# ============================================================================
# TestRoundTripAccuracy: Test decimal ↔ DMS conversion accuracy
# ============================================================================

class TestRoundTripAccuracy:
    """
    Test round-trip accuracy: Decimal → DMS → Decimal.

    Ensures that converting from decimal to DMS and back to decimal
    produces a value very close to the original (within reasonable precision).

    Precision target: ±0.00001° (approximately 1 meter at equator)
    """

    @pytest.mark.parametrize("decimal,is_latitude", [
        (37.7749, True),  # San Francisco lat
        (-122.4194, False),  # San Francisco lon
        (-33.8688, True),  # Sydney lat
        (151.2093, False),  # Sydney lon
        (0.0, True),  # Equator
        (0.0, False),  # Prime Meridian
        (90.0, True),  # North Pole
        (-90.0, True),  # South Pole
        (180.0, False),  # Date Line East
        (-180.0, False),  # Date Line West
        (31.5, True),  # Dead Sea lat
        (35.5, False),  # Dead Sea lon
    ])
    def test_round_trip_accuracy(self, decimal, is_latitude):
        """
        Test round-trip conversion accuracy for various coordinates.

        Scenario: Decimal → DMS → Decimal
        Expected: Final decimal matches original within 0.00001°
        """
        from utils.gps_coordinates import decimal_to_dms, dms_to_decimal

        # Act: Convert decimal → DMS → decimal
        degrees, minutes, seconds, ref = decimal_to_dms(decimal, is_latitude=is_latitude)
        decimal_result = dms_to_decimal(degrees, minutes, seconds, ref)

        # Assert: Round-trip accuracy within 0.00001° (~1 meter at equator)
        precision = 0.00001
        assert abs(decimal_result - decimal) < precision, \
            f"Round-trip error too large: {decimal} → {decimal_result} (Δ{abs(decimal_result - decimal)})"

        coord_type = "lat" if is_latitude else "lon"
        print(f"✓ Round-trip {coord_type}: {decimal}° → {degrees}°{minutes}'{seconds:.2f}\"{ref} → {decimal_result}° (Δ{abs(decimal_result - decimal):.6f})")

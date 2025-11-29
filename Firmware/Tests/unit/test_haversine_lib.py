"""
Unit tests for Haversine distance calculation library.

Tests cover:
- Basic distance calculations with known values
- Edge cases (antipodal points, poles, dateline crossing)
- Coordinate validation
- Distance checking
- Longitude normalization
- Performance benchmarks
"""

import math
import time

import pytest

from webui.backend.lib.haversine import (
    EARTH_RADIUS_M,
    haversine_distance,
    is_within_distance,
    normalize_longitude,
    validate_coordinates,
)


class TestHaversineDistanceBasicCalculations:
    """Test basic distance calculations with known values."""

    def test_haversine_distance_new_york_to_london(self):
        """NYC (40.7128, -74.0060) to London (51.5074, -0.1278) ≈ 5,570 km."""
        # Known distance: approximately 5,570 km
        lat1, lon1 = 40.7128, -74.0060  # New York City
        lat2, lon2 = 51.5074, -0.1278   # London

        distance = haversine_distance(lat1, lon1, lat2, lon2)

        # Allow 1% tolerance for spherical Earth approximation
        expected = 5_570_000  # meters
        tolerance = expected * 0.01
        assert abs(distance - expected) < tolerance

    def test_haversine_distance_same_point(self):
        """Same point should return 0."""
        lat, lon = 37.7749, -122.4194  # San Francisco

        distance = haversine_distance(lat, lon, lat, lon)

        assert distance == 0.0

    def test_haversine_distance_short_distance(self):
        """Test 100m distance calculation accuracy."""
        # Two points approximately 100m apart
        lat1, lon1 = 37.7749, -122.4194
        # Move approximately 0.001 degrees north (~111m at this latitude)
        lat2, lon2 = 37.7759, -122.4194

        distance = haversine_distance(lat1, lon1, lat2, lon2)

        # Should be around 111 meters (1/90 of a degree at equator ≈ 111km)
        assert 100 < distance < 120

    def test_haversine_distance_equator(self):
        """Test distance calculation at equator."""
        # Two points on equator, 1 degree apart
        lat1, lon1 = 0.0, 0.0
        lat2, lon2 = 0.0, 1.0

        distance = haversine_distance(lat1, lon1, lat2, lon2)

        # 1 degree at equator ≈ 111.32 km
        expected = 111_320  # meters
        tolerance = expected * 0.01
        assert abs(distance - expected) < tolerance


class TestHaversineDistanceEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_haversine_distance_antipodal_points(self):
        """Points on opposite sides of Earth."""
        # North Pole and South Pole are antipodal
        lat1, lon1 = 90.0, 0.0   # North Pole
        lat2, lon2 = -90.0, 0.0  # South Pole

        distance = haversine_distance(lat1, lon1, lat2, lon2)

        # Half the circumference of Earth
        expected = math.pi * EARTH_RADIUS_M
        tolerance = expected * 0.01
        assert abs(distance - expected) < tolerance

    def test_haversine_distance_north_pole(self):
        """From North Pole to equator."""
        lat1, lon1 = 90.0, 0.0  # North Pole
        lat2, lon2 = 0.0, 0.0   # Equator at prime meridian

        distance = haversine_distance(lat1, lon1, lat2, lon2)

        # Quarter of Earth's circumference
        expected = (math.pi / 2) * EARTH_RADIUS_M
        tolerance = expected * 0.01
        assert abs(distance - expected) < tolerance

    def test_haversine_distance_south_pole(self):
        """From South Pole to equator."""
        lat1, lon1 = -90.0, 0.0  # South Pole
        lat2, lon2 = 0.0, 0.0    # Equator at prime meridian

        distance = haversine_distance(lat1, lon1, lat2, lon2)

        # Quarter of Earth's circumference
        expected = (math.pi / 2) * EARTH_RADIUS_M
        tolerance = expected * 0.01
        assert abs(distance - expected) < tolerance

    def test_haversine_distance_crosses_dateline(self):
        """Points crossing international dateline (-179 to 179 longitude)."""
        # Two points near dateline
        lat1, lon1 = 0.0, 179.0
        lat2, lon2 = 0.0, -179.0

        distance = haversine_distance(lat1, lon1, lat2, lon2)

        # Should be 2 degrees at equator ≈ 222.64 km
        expected = 222_640  # meters
        tolerance = expected * 0.01
        assert abs(distance - expected) < tolerance

    def test_haversine_distance_crosses_prime_meridian(self):
        """Points crossing prime meridian."""
        lat1, lon1 = 51.5, -1.0  # West of prime meridian
        lat2, lon2 = 51.5, 1.0   # East of prime meridian

        distance = haversine_distance(lat1, lon1, lat2, lon2)

        # 2 degrees at this latitude
        # At 51.5°N, 1 degree longitude ≈ 69.4 km
        expected = 138_800  # meters (approximately)
        tolerance = expected * 0.05  # 5% tolerance due to latitude
        assert abs(distance - expected) < tolerance


class TestValidateCoordinates:
    """Test coordinate validation."""

    def test_validate_coordinates_valid(self):
        """Valid coordinates should pass."""
        test_cases = [
            (0.0, 0.0),
            (90.0, 180.0),
            (-90.0, -180.0),
            (37.7749, -122.4194),  # San Francisco
            (51.5074, -0.1278),     # London
        ]

        for lat, lon in test_cases:
            is_valid, error = validate_coordinates(lat, lon)
            assert is_valid is True
            assert error is None

    def test_validate_coordinates_invalid_latitude_too_high(self):
        """Latitude > 90 should fail."""
        is_valid, error = validate_coordinates(91.0, 0.0)

        assert is_valid is False
        assert error is not None
        assert "latitude" in error.lower()

    def test_validate_coordinates_invalid_latitude_too_low(self):
        """Latitude < -90 should fail."""
        is_valid, error = validate_coordinates(-91.0, 0.0)

        assert is_valid is False
        assert error is not None
        assert "latitude" in error.lower()

    def test_validate_coordinates_invalid_longitude_too_high(self):
        """Longitude > 180 should fail."""
        is_valid, error = validate_coordinates(0.0, 181.0)

        assert is_valid is False
        assert error is not None
        assert "longitude" in error.lower()

    def test_validate_coordinates_invalid_longitude_too_low(self):
        """Longitude < -180 should fail."""
        is_valid, error = validate_coordinates(0.0, -181.0)

        assert is_valid is False
        assert error is not None
        assert "longitude" in error.lower()

    def test_validate_coordinates_none_latitude(self):
        """None latitude should fail."""
        is_valid, error = validate_coordinates(None, 0.0)

        assert is_valid is False
        assert error is not None

    def test_validate_coordinates_none_longitude(self):
        """None longitude should fail."""
        is_valid, error = validate_coordinates(0.0, None)

        assert is_valid is False
        assert error is not None

    def test_validate_coordinates_both_none(self):
        """Both None should fail."""
        is_valid, error = validate_coordinates(None, None)

        assert is_valid is False
        assert error is not None

    def test_validate_coordinates_nan_latitude(self):
        """NaN latitude should fail."""
        is_valid, error = validate_coordinates(float('nan'), 0.0)

        assert is_valid is False
        assert error is not None

    def test_validate_coordinates_nan_longitude(self):
        """NaN longitude should fail."""
        is_valid, error = validate_coordinates(0.0, float('nan'))

        assert is_valid is False
        assert error is not None

    def test_validate_coordinates_infinity_latitude(self):
        """Infinity latitude should fail."""
        is_valid, error = validate_coordinates(float('inf'), 0.0)

        assert is_valid is False
        assert error is not None

    def test_validate_coordinates_infinity_longitude(self):
        """Infinity longitude should fail."""
        is_valid, error = validate_coordinates(0.0, float('inf'))

        assert is_valid is False
        assert error is not None

    def test_validate_coordinates_non_numeric_latitude(self):
        """Non-numeric latitude (list) should fail with type error."""
        is_valid, error = validate_coordinates([1, 2, 3], 0.0)

        assert is_valid is False
        assert error is not None
        assert "numeric" in error.lower()

    def test_validate_coordinates_non_numeric_longitude(self):
        """Non-numeric longitude (dict) should fail with type error."""
        is_valid, error = validate_coordinates(0.0, {"invalid": True})

        assert is_valid is False
        assert error is not None
        assert "numeric" in error.lower()


class TestIsWithinDistance:
    """Test distance checking function."""

    def test_is_within_distance_true(self):
        """Points within distance should return True."""
        # Two points approximately 100m apart
        lat1, lon1 = 37.7749, -122.4194
        lat2, lon2 = 37.7759, -122.4194

        result = is_within_distance(lat1, lon1, lat2, lon2, 150)

        assert result is True

    def test_is_within_distance_false(self):
        """Points outside distance should return False."""
        # NYC to London (≈5,570 km)
        lat1, lon1 = 40.7128, -74.0060
        lat2, lon2 = 51.5074, -0.1278

        result = is_within_distance(lat1, lon1, lat2, lon2, 1000)

        assert result is False

    def test_is_within_distance_boundary_exact(self):
        """Points exactly at distance boundary."""
        # Same point - distance is 0
        lat, lon = 37.7749, -122.4194

        result = is_within_distance(lat, lon, lat, lon, 0)

        assert result is True

    def test_is_within_distance_boundary_close(self):
        """Points very close to distance boundary."""
        lat1, lon1 = 0.0, 0.0
        lat2, lon2 = 0.0, 0.001  # ~111 meters at equator

        # Test with threshold slightly above actual distance
        result_above = is_within_distance(lat1, lon1, lat2, lon2, 115)
        assert result_above is True

        # Test with threshold slightly below actual distance
        result_below = is_within_distance(lat1, lon1, lat2, lon2, 105)
        assert result_below is False

    def test_is_within_distance_zero_threshold(self):
        """Zero threshold should only match same point."""
        lat1, lon1 = 37.7749, -122.4194
        lat2, lon2 = 37.7750, -122.4194

        result = is_within_distance(lat1, lon1, lat2, lon2, 0)

        assert result is False

    def test_is_within_distance_large_threshold(self):
        """Very large threshold should match distant points."""
        lat1, lon1 = 40.7128, -74.0060  # NYC
        lat2, lon2 = 51.5074, -0.1278   # London

        # 10,000 km threshold
        result = is_within_distance(lat1, lon1, lat2, lon2, 10_000_000)

        assert result is True


class TestNormalizeLongitude:
    """Test longitude normalization."""

    def test_normalize_longitude_already_normal(self):
        """Normal range should return unchanged."""
        test_cases = [0.0, 45.0, -45.0, 90.0, -90.0, 180.0, -180.0]

        for lon in test_cases:
            result = normalize_longitude(lon)
            assert result == lon

    def test_normalize_longitude_over_180(self):
        """270 should become -90."""
        result = normalize_longitude(270.0)
        assert result == -90.0

    def test_normalize_longitude_under_minus_180(self):
        """-270 should become 90."""
        result = normalize_longitude(-270.0)
        assert result == 90.0

    def test_normalize_longitude_exactly_180(self):
        """180 should stay 180."""
        result = normalize_longitude(180.0)
        assert result == 180.0

    def test_normalize_longitude_exactly_minus_180(self):
        """-180 should stay -180."""
        result = normalize_longitude(-180.0)
        assert result == -180.0

    def test_normalize_longitude_full_rotation(self):
        """360 should become 0."""
        result = normalize_longitude(360.0)
        assert abs(result - 0.0) < 1e-10  # Account for floating point

    def test_normalize_longitude_minus_full_rotation(self):
        """-360 should become 0."""
        result = normalize_longitude(-360.0)
        assert abs(result - 0.0) < 1e-10  # Account for floating point

    def test_normalize_longitude_multiple_rotations(self):
        """720 should become 0."""
        result = normalize_longitude(720.0)
        assert abs(result - 0.0) < 1e-10  # Account for floating point

    def test_normalize_longitude_dateline_crossing_west(self):
        """190 should become -170."""
        result = normalize_longitude(190.0)
        assert result == -170.0

    def test_normalize_longitude_dateline_crossing_east(self):
        """-190 should become 170."""
        result = normalize_longitude(-190.0)
        assert result == 170.0


class TestHaversineDistanceValidation:
    """Test that haversine_distance validates inputs."""

    def test_haversine_distance_invalid_lat1(self):
        """Invalid first latitude should raise ValueError."""
        with pytest.raises(ValueError, match="(?i)latitude"):  # Case-insensitive
            haversine_distance(91.0, 0.0, 0.0, 0.0)

    def test_haversine_distance_invalid_lon1(self):
        """Invalid first longitude should raise ValueError."""
        with pytest.raises(ValueError, match="(?i)longitude"):  # Case-insensitive
            haversine_distance(0.0, 181.0, 0.0, 0.0)

    def test_haversine_distance_invalid_lat2(self):
        """Invalid second latitude should raise ValueError."""
        with pytest.raises(ValueError, match="(?i)latitude"):  # Case-insensitive
            haversine_distance(0.0, 0.0, -91.0, 0.0)

    def test_haversine_distance_invalid_lon2(self):
        """Invalid second longitude should raise ValueError."""
        with pytest.raises(ValueError, match="(?i)longitude"):  # Case-insensitive
            haversine_distance(0.0, 0.0, 0.0, -181.0)

    def test_haversine_distance_none_values(self):
        """None values should raise ValueError."""
        with pytest.raises(ValueError):
            haversine_distance(None, 0.0, 0.0, 0.0)

    def test_haversine_distance_nan_values(self):
        """NaN values should raise ValueError."""
        with pytest.raises(ValueError):
            haversine_distance(float('nan'), 0.0, 0.0, 0.0)


class TestIsWithinDistanceValidation:
    """Test that is_within_distance validates inputs."""

    def test_is_within_distance_invalid_coordinates(self):
        """Invalid coordinates should raise ValueError."""
        with pytest.raises(ValueError):
            is_within_distance(91.0, 0.0, 0.0, 0.0, 100)

    def test_is_within_distance_negative_distance(self):
        """Negative distance threshold should raise ValueError."""
        with pytest.raises(ValueError, match="(?i)distance"):  # Case-insensitive
            is_within_distance(0.0, 0.0, 0.0, 0.0, -100)


class TestHaversineDistancePerformance:
    """Test performance benchmarks."""

    def test_haversine_distance_performance(self):
        """1000 distance calculations should complete in <100ms."""
        # Test coordinates
        coords = [
            (40.7128, -74.0060),  # NYC
            (51.5074, -0.1278),   # London
            (35.6762, 139.6503),  # Tokyo
            (-33.8688, 151.2093), # Sydney
            (37.7749, -122.4194), # San Francisco
        ]

        start_time = time.time()

        # Perform 1000 calculations
        for _ in range(200):
            for i in range(len(coords)):
                for j in range(i + 1, len(coords)):
                    lat1, lon1 = coords[i]
                    lat2, lon2 = coords[j]
                    haversine_distance(lat1, lon1, lat2, lon2)

        elapsed = (time.time() - start_time) * 1000  # Convert to ms

        # Should complete in under 100ms
        assert elapsed < 100, f"Performance test failed: {elapsed:.2f}ms (expected <100ms)"

    def test_validate_coordinates_performance(self):
        """10000 validations should complete in <50ms."""
        start_time = time.time()

        for _ in range(10000):
            validate_coordinates(37.7749, -122.4194)

        elapsed = (time.time() - start_time) * 1000  # Convert to ms

        assert elapsed < 50, f"Validation performance test failed: {elapsed:.2f}ms (expected <50ms)"


class TestHaversineRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_clustering_photos_by_location(self):
        """Simulate clustering photos taken at nearby locations."""
        # Photos taken within 50m radius (typical Mothbox deployment)
        base_lat, base_lon = 37.7749, -122.4194
        photos = [
            (base_lat, base_lon),
            (base_lat + 0.0001, base_lon),  # ~11m north
            (base_lat, base_lon + 0.0001),  # ~9m east
            (base_lat - 0.0001, base_lon),  # ~11m south
        ]

        # All should be within 50m cluster
        cluster_radius = 50  # meters
        for lat, lon in photos[1:]:
            assert is_within_distance(base_lat, base_lon, lat, lon, cluster_radius)

    def test_filtering_distant_photos(self):
        """Simulate filtering photos from different deployments."""
        site_a = (37.7749, -122.4194)  # San Francisco
        site_b = (37.8044, -122.2712)  # Oakland (~13 km away)

        # Photos from site A
        lat1, lon1 = site_a

        # Photos from site B should be filtered out (>1km threshold)
        lat2, lon2 = site_b
        threshold = 1000  # 1 km

        assert not is_within_distance(lat1, lon1, lat2, lon2, threshold)

    def test_handling_gps_drift(self):
        """Simulate GPS coordinate drift in sequential photos."""
        # GPS can drift by ~5-10m between readings
        base_lat, base_lon = 37.7749, -122.4194
        drifted_lat, drifted_lon = 37.7749 + 0.00005, -122.4194 + 0.00005

        distance = haversine_distance(base_lat, base_lon, drifted_lat, drifted_lon)

        # Should be small distance (~7-8m)
        assert distance < 10

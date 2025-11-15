"""Performance benchmarks for GPS coordinate utilities.

Tests ensure all coordinate conversions complete in <1ms per operation,
suitable for real-time UI updates and batch processing.
"""

import pytest
import time
from webui.lib.gps_coordinates import (
    decimal_to_dms,
    dms_to_decimal,
    validate_coordinate,
    format_coordinate_display
)


class TestDecimalToDMSPerformance:
    """Performance tests for decimal_to_dms function."""

    def test_single_conversion_speed(self):
        """Single decimal to DMS conversion should complete in <1ms."""
        coordinate = 37.7749
        iterations = 100

        start = time.perf_counter()
        for _ in range(iterations):
            decimal_to_dms(coordinate, is_latitude=True)
        end = time.perf_counter()

        avg_time_ms = ((end - start) / iterations) * 1000
        print(f"\nDecimal to DMS (single): {avg_time_ms:.4f} ms per conversion")
        assert avg_time_ms < 1.0, f"Average time {avg_time_ms:.4f}ms exceeds 1ms target"

    def test_batch_conversion_speed(self):
        """Batch decimal to DMS conversions should average <1ms per conversion."""
        # Test with diverse coordinates
        coordinates = [
            37.7749,    # San Francisco
            -122.4194,  # San Francisco
            51.5074,    # London
            -0.1278,    # London
            0.0,        # Equator/Prime Meridian
            90.0,       # North Pole
            -90.0,      # South Pole
            180.0,      # Date Line
            -180.0,     # Date Line
            45.5,       # Mid-latitude
        ]
        iterations = 1000

        start = time.perf_counter()
        for _ in range(iterations):
            for coord in coordinates:
                is_lat = abs(coord) <= 90
                decimal_to_dms(coord, is_lat)
        end = time.perf_counter()

        total_conversions = iterations * len(coordinates)
        avg_time_ms = ((end - start) / total_conversions) * 1000

        print(f"\nDecimal to DMS (batch): {avg_time_ms:.4f} ms per conversion")
        print(f"  Total conversions: {total_conversions}")
        print(f"  Total time: {(end - start)*1000:.2f} ms")
        assert avg_time_ms < 1.0, f"Average time {avg_time_ms:.4f}ms exceeds 1ms target"

    def test_edge_case_conversion_speed(self):
        """Edge case conversions should not be significantly slower."""
        edge_cases = [
            (0.0, True),        # Zero latitude
            (0.0, False),       # Zero longitude
            (90.0, True),       # North Pole
            (-90.0, True),      # South Pole
            (180.0, False),     # Date Line East
            (-180.0, False),    # Date Line West
        ]
        iterations = 1000

        start = time.perf_counter()
        for _ in range(iterations):
            for coord, is_lat in edge_cases:
                decimal_to_dms(coord, is_lat)
        end = time.perf_counter()

        total_conversions = iterations * len(edge_cases)
        avg_time_ms = ((end - start) / total_conversions) * 1000

        print(f"\nDecimal to DMS (edge cases): {avg_time_ms:.4f} ms per conversion")
        assert avg_time_ms < 1.0, f"Average time {avg_time_ms:.4f}ms exceeds 1ms target"


class TestDMSToDecimalPerformance:
    """Performance tests for dms_to_decimal function."""

    def test_single_conversion_speed(self):
        """Single DMS to decimal conversion should complete in <1ms."""
        iterations = 100

        start = time.perf_counter()
        for _ in range(iterations):
            dms_to_decimal(37, 46, 29.64, 'N')
        end = time.perf_counter()

        avg_time_ms = ((end - start) / iterations) * 1000
        print(f"\nDMS to decimal (single): {avg_time_ms:.4f} ms per conversion")
        assert avg_time_ms < 1.0, f"Average time {avg_time_ms:.4f}ms exceeds 1ms target"

    def test_batch_conversion_speed(self):
        """Batch DMS to decimal conversions should average <1ms per conversion."""
        # Test with diverse DMS coordinates
        dms_coords = [
            (37, 46, 29.64, 'N'),   # San Francisco
            (122, 25, 9.84, 'W'),   # San Francisco
            (51, 30, 26.64, 'N'),   # London
            (0, 7, 40.08, 'W'),     # London
            (0, 0, 0.0, 'N'),       # Equator
            (0, 0, 0.0, 'E'),       # Prime Meridian
            (90, 0, 0.0, 'N'),      # North Pole
            (90, 0, 0.0, 'S'),      # South Pole
            (180, 0, 0.0, 'E'),     # Date Line
            (180, 0, 0.0, 'W'),     # Date Line
        ]
        iterations = 1000

        start = time.perf_counter()
        for _ in range(iterations):
            for deg, min, sec, ref in dms_coords:
                dms_to_decimal(deg, min, sec, ref)
        end = time.perf_counter()

        total_conversions = iterations * len(dms_coords)
        avg_time_ms = ((end - start) / total_conversions) * 1000

        print(f"\nDMS to decimal (batch): {avg_time_ms:.4f} ms per conversion")
        print(f"  Total conversions: {total_conversions}")
        print(f"  Total time: {(end - start)*1000:.2f} ms")
        assert avg_time_ms < 1.0, f"Average time {avg_time_ms:.4f}ms exceeds 1ms target"

    def test_all_reference_directions_speed(self):
        """All reference directions should have similar performance."""
        references = ['N', 'S', 'E', 'W']
        iterations = 1000

        start = time.perf_counter()
        for _ in range(iterations):
            for ref in references:
                dms_to_decimal(37, 46, 29.64, ref)
        end = time.perf_counter()

        total_conversions = iterations * len(references)
        avg_time_ms = ((end - start) / total_conversions) * 1000

        print(f"\nDMS to decimal (all references): {avg_time_ms:.4f} ms per conversion")
        assert avg_time_ms < 1.0, f"Average time {avg_time_ms:.4f}ms exceeds 1ms target"


class TestValidateCoordinatePerformance:
    """Performance tests for validate_coordinate function."""

    def test_single_validation_speed(self):
        """Single coordinate validation should complete in <1ms."""
        iterations = 100

        start = time.perf_counter()
        for _ in range(iterations):
            validate_coordinate(37.7749, is_latitude=True)
        end = time.perf_counter()

        avg_time_ms = ((end - start) / iterations) * 1000
        print(f"\nValidate coordinate (single): {avg_time_ms:.4f} ms per validation")
        assert avg_time_ms < 1.0, f"Average time {avg_time_ms:.4f}ms exceeds 1ms target"

    def test_batch_validation_speed(self):
        """Batch coordinate validations should average <1ms per validation."""
        # Mix of valid and invalid coordinates
        coordinates = [
            (37.7749, True),    # Valid latitude
            (-122.4194, False), # Valid longitude
            (91.0, True),       # Invalid latitude (too large)
            (-181.0, False),    # Invalid longitude (too small)
            (0.0, True),        # Valid zero
            (float('nan'), True),  # Invalid NaN
            (float('inf'), False), # Invalid Infinity
            (90.0, True),       # Valid pole
            (-180.0, False),    # Valid date line
        ]
        iterations = 1000

        start = time.perf_counter()
        for _ in range(iterations):
            for coord, is_lat in coordinates:
                validate_coordinate(coord, is_lat)
        end = time.perf_counter()

        total_validations = iterations * len(coordinates)
        avg_time_ms = ((end - start) / total_validations) * 1000

        print(f"\nValidate coordinate (batch): {avg_time_ms:.4f} ms per validation")
        print(f"  Total validations: {total_validations}")
        print(f"  Total time: {(end - start)*1000:.2f} ms")
        assert avg_time_ms < 1.0, f"Average time {avg_time_ms:.4f}ms exceeds 1ms target"

    def test_special_value_validation_speed(self):
        """Validation of special values should be fast."""
        special_values = [
            float('nan'),
            float('inf'),
            float('-inf'),
            0.0,
            -0.0,
        ]
        iterations = 1000

        start = time.perf_counter()
        for _ in range(iterations):
            for value in special_values:
                validate_coordinate(value, is_latitude=True)
                validate_coordinate(value, is_latitude=False)
        end = time.perf_counter()

        total_validations = iterations * len(special_values) * 2
        avg_time_ms = ((end - start) / total_validations) * 1000

        print(f"\nValidate coordinate (special values): {avg_time_ms:.4f} ms per validation")
        assert avg_time_ms < 1.0, f"Average time {avg_time_ms:.4f}ms exceeds 1ms target"


class TestFormatCoordinateDisplayPerformance:
    """Performance tests for format_coordinate_display function."""

    def test_single_format_speed(self):
        """Single coordinate formatting should complete in <1ms."""
        iterations = 100

        start = time.perf_counter()
        for _ in range(iterations):
            format_coordinate_display(37.7749, -122.4194)
        end = time.perf_counter()

        avg_time_ms = ((end - start) / iterations) * 1000
        print(f"\nFormat coordinate display (single): {avg_time_ms:.4f} ms per format")
        assert avg_time_ms < 1.0, f"Average time {avg_time_ms:.4f}ms exceeds 1ms target"

    def test_batch_format_speed(self):
        """Batch coordinate formatting should average <1ms per format."""
        # Test with diverse coordinate pairs
        coord_pairs = [
            (37.7749, -122.4194),   # San Francisco
            (51.5074, -0.1278),     # London
            (0.0, 0.0),             # Null Island
            (90.0, 180.0),          # North Pole, Date Line
            (-90.0, -180.0),        # South Pole, Date Line
            (45.5, 75.3),           # Mid-latitude
            (-33.9, 18.4),          # Cape Town
            (35.7, 139.7),          # Tokyo
        ]
        iterations = 1000

        start = time.perf_counter()
        for _ in range(iterations):
            for lat, lon in coord_pairs:
                format_coordinate_display(lat, lon)
        end = time.perf_counter()

        total_formats = iterations * len(coord_pairs)
        avg_time_ms = ((end - start) / total_formats) * 1000

        print(f"\nFormat coordinate display (batch): {avg_time_ms:.4f} ms per format")
        print(f"  Total formats: {total_formats}")
        print(f"  Total time: {(end - start)*1000:.2f} ms")
        assert avg_time_ms < 1.0, f"Average time {avg_time_ms:.4f}ms exceeds 1ms target"

    def test_edge_case_format_speed(self):
        """Edge case formatting should not be significantly slower."""
        edge_cases = [
            (0.0, 0.0),             # Zero coordinates
            (90.0, 180.0),          # Maximum values
            (-90.0, -180.0),        # Minimum values
            (0.0001, 0.0001),       # Very small values
            (89.9999, 179.9999),    # Near maximum
        ]
        iterations = 1000

        start = time.perf_counter()
        for _ in range(iterations):
            for lat, lon in edge_cases:
                format_coordinate_display(lat, lon)
        end = time.perf_counter()

        total_formats = iterations * len(edge_cases)
        avg_time_ms = ((end - start) / total_formats) * 1000

        print(f"\nFormat coordinate display (edge cases): {avg_time_ms:.4f} ms per format")
        assert avg_time_ms < 1.0, f"Average time {avg_time_ms:.4f}ms exceeds 1ms target"


class TestRoundTripPerformance:
    """Performance tests for round-trip conversions (decimal → DMS → decimal)."""

    def test_round_trip_conversion_speed(self):
        """Round-trip conversions should complete in <2ms total."""
        coordinates = [
            (37.7749, True),
            (-122.4194, False),
            (51.5074, True),
            (-0.1278, False),
            (0.0, True),
            (90.0, True),
            (-180.0, False),
        ]
        iterations = 1000

        start = time.perf_counter()
        for _ in range(iterations):
            for coord, is_lat in coordinates:
                # Decimal → DMS
                dms = decimal_to_dms(coord, is_lat)
                # DMS → Decimal
                result = dms_to_decimal(*dms)
                # Verify accuracy (not timed, just for correctness)
                assert round(coord, 6) == round(result, 6)
        end = time.perf_counter()

        total_round_trips = iterations * len(coordinates)
        avg_time_ms = ((end - start) / total_round_trips) * 1000

        print(f"\nRound-trip conversion: {avg_time_ms:.4f} ms per round-trip")
        print(f"  Total round-trips: {total_round_trips}")
        print(f"  Total time: {(end - start)*1000:.2f} ms")
        # Round-trip involves two conversions, so allow 2ms
        assert avg_time_ms < 2.0, f"Average time {avg_time_ms:.4f}ms exceeds 2ms target"


class TestBatchPhotoProcessingSimulation:
    """Simulate realistic batch photo processing scenarios."""

    def test_gps_exif_embedding_workflow(self):
        """Simulate GPS EXIF embedding workflow for batch photo processing."""
        # Simulate processing 100 photos with GPS coordinates
        num_photos = 100
        gps_coordinates = [
            (37.7749, -122.4194),   # San Francisco
            (51.5074, -0.1278),     # London
            (35.6762, 139.6503),    # Tokyo
            (-33.9249, 18.4241),    # Cape Town
            (40.7128, -74.0060),    # New York
        ]

        start = time.perf_counter()
        for i in range(num_photos):
            # Cycle through GPS coordinates
            lat, lon = gps_coordinates[i % len(gps_coordinates)]

            # Validate coordinates (as API would do)
            assert validate_coordinate(lat, is_latitude=True)
            assert validate_coordinate(lon, is_latitude=False)

            # Convert to DMS for EXIF embedding
            lat_dms = decimal_to_dms(lat, is_latitude=True)
            lon_dms = decimal_to_dms(lon, is_latitude=False)

            # Format for display (for UI/logging)
            display = format_coordinate_display(lat, lon)

        end = time.perf_counter()

        total_time_ms = (end - start) * 1000
        avg_time_per_photo = total_time_ms / num_photos

        print(f"\nGPS EXIF embedding workflow simulation:")
        print(f"  Photos processed: {num_photos}")
        print(f"  Total time: {total_time_ms:.2f} ms")
        print(f"  Average time per photo: {avg_time_per_photo:.2f} ms")
        print(f"  Throughput: {num_photos / (end - start):.1f} photos/second")

        # Target: Process at least 10 photos/second (100ms per photo)
        assert avg_time_per_photo < 100.0, \
            f"Average time {avg_time_per_photo:.2f}ms exceeds 100ms target"

    def test_ui_metadata_panel_workflow(self):
        """Simulate UI metadata panel displaying GPS coordinates."""
        # Simulate displaying 50 photos in a gallery with GPS metadata
        num_photos = 50
        gps_coordinates = [
            (37.7749, -122.4194),
            (51.5074, -0.1278),
            (35.6762, 139.6503),
            (-33.9249, 18.4241),
            (40.7128, -74.0060),
        ]

        start = time.perf_counter()
        for i in range(num_photos):
            lat, lon = gps_coordinates[i % len(gps_coordinates)]

            # Format for display (main operation in UI)
            display = format_coordinate_display(lat, lon)

            # Optional: Convert to DMS for detailed view
            lat_dms = decimal_to_dms(lat, is_latitude=True)
            lon_dms = decimal_to_dms(lon, is_latitude=False)

        end = time.perf_counter()

        total_time_ms = (end - start) * 1000
        avg_time_per_photo = total_time_ms / num_photos

        print(f"\nUI metadata panel workflow simulation:")
        print(f"  Photos displayed: {num_photos}")
        print(f"  Total time: {total_time_ms:.2f} ms")
        print(f"  Average time per photo: {avg_time_per_photo:.2f} ms")
        print(f"  Render time for 50-photo gallery: {total_time_ms:.2f} ms")

        # Target: Render 50 photos in <50ms (1ms per photo)
        assert avg_time_per_photo < 1.0, \
            f"Average time {avg_time_per_photo:.2f}ms exceeds 1ms target"


class TestPerformanceSummary:
    """Summary test to report all performance metrics."""

    def test_performance_summary(self):
        """Generate performance summary report."""
        print("\n" + "="*70)
        print("GPS COORDINATE UTILITIES - PERFORMANCE SUMMARY")
        print("="*70)

        # Test each function
        functions = [
            ("decimal_to_dms", lambda: decimal_to_dms(37.7749, True)),
            ("dms_to_decimal", lambda: dms_to_decimal(37, 46, 29.64, 'N')),
            ("validate_coordinate", lambda: validate_coordinate(37.7749, True)),
            ("format_coordinate_display", lambda: format_coordinate_display(37.7749, -122.4194)),
        ]

        iterations = 1000
        results = []

        for name, func in functions:
            start = time.perf_counter()
            for _ in range(iterations):
                func()
            end = time.perf_counter()

            avg_time_ms = ((end - start) / iterations) * 1000
            results.append((name, avg_time_ms))

        # Print results
        print("\nFunction                        | Avg Time (ms) | Target (ms) | Status")
        print("-" * 70)
        for name, avg_time in results:
            status = "✓ PASS" if avg_time < 1.0 else "✗ FAIL"
            print(f"{name:30} | {avg_time:13.4f} | {1.0:11.1f} | {status}")

        print("\n" + "="*70)
        print(f"All tests run with {iterations} iterations per function")
        print("="*70 + "\n")

        # Assert all pass
        for name, avg_time in results:
            assert avg_time < 1.0, f"{name} exceeded 1ms target: {avg_time:.4f}ms"


if __name__ == '__main__':
    # Run with verbose output to see performance metrics
    pytest.main([__file__, '-v', '-s'])

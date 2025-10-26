"""
Unit Tests: Zoom Coordinate Calculation Fix (Issue #52)

Tests the fixes for two critical zoom bugs:
1. Crosshair position mismatch - crosshair doesn't align with actual zoom center
2. Zoom doesn't reset - image remains zoomed when slider is at 1.0x

These are pure mathematical unit tests that don't require hardware.
We test the zoom calculation logic directly without importing the full module.

Run with: pytest Tests/unit/test_zoom_coordinate_fix.py -v
"""

import pytest


def calculate_scaler_crop(scaler_crop_max, zoom_level, zoom_center_x, zoom_center_y):
    """
    Pure function implementation of ScalerCrop calculation (extracted from liveview_stream.py)

    This allows testing the mathematical logic without hardware dependencies.

    Args:
        scaler_crop_max: (x_offset, y_offset, active_width, active_height) tuple
                         Defines the active sensor area in full sensor coordinates
        zoom_level: Zoom multiplier (1.0 = no zoom, 2.0 = 2x zoom, etc.)
        zoom_center_x: Normalized horizontal center (0-1)
        zoom_center_y: Normalized vertical center (0-1)

    Returns:
        (offset_x, offset_y, width, height) ScalerCrop in full sensor coordinates
    """
    if not scaler_crop_max:
        return None

    # Extract active area dimensions AND offset from ScalerCropMaximum
    x_offset, y_offset, sensor_width, sensor_height = scaler_crop_max

    # Special case: zoom=1.0 means full active area (no crop)
    if zoom_level == 1.0:
        return scaler_crop_max

    # Calculate cropped dimensions (inverse of zoom level)
    crop_width = int(sensor_width / zoom_level)
    crop_height = int(sensor_height / zoom_level)

    # Ensure even dimensions (required by some encoders)
    crop_width = crop_width & ~1
    crop_height = crop_height & ~1

    # Calculate position RELATIVE to active area
    offset_x_rel = int(zoom_center_x * sensor_width - crop_width / 2)
    offset_y_rel = int(zoom_center_y * sensor_height - crop_height / 2)

    # Clamp to valid range within active area
    offset_x_rel = max(0, min(offset_x_rel, sensor_width - crop_width))
    offset_y_rel = max(0, min(offset_y_rel, sensor_height - crop_height))

    # Ensure even offsets (required by some encoders)
    offset_x_rel = offset_x_rel & ~1
    offset_y_rel = offset_y_rel & ~1

    # Convert to FULL SENSOR coordinates by adding ScalerCropMaximum offset
    offset_x_pixels = x_offset + offset_x_rel
    offset_y_pixels = y_offset + offset_y_rel

    return (offset_x_pixels, offset_y_pixels, crop_width, crop_height)


class TestZoomResetBehavior:
    """Test zoom=1.0 reset behavior (Bug #2)"""

    def test_zoom_1_0_returns_full_active_area(self):
        """Test that zoom=1.0 returns full active area (ScalerCropMaximum)"""
        # Full sensor mode: offset is (0, 0)
        scaler_crop_max = (0, 0, 4056, 3040)

        scaler_crop = calculate_scaler_crop(scaler_crop_max, 1.0, 0.5, 0.5)

        assert scaler_crop == (0, 0, 4056, 3040), \
            f"zoom=1.0 should return full active area, got {scaler_crop}"

        print(f"✓ zoom=1.0 returns full active area: {scaler_crop}")

    def test_zoom_1_0_with_binned_mode(self):
        """Test that zoom=1.0 returns ScalerCropMaximum even with non-zero offset"""
        # Binned sensor mode (e.g., 1920x1080 on 64MP sensor)
        # ScalerCropMaximum has non-zero offset
        scaler_crop_max = (784, 1312, 7712, 4352)

        scaler_crop = calculate_scaler_crop(scaler_crop_max, 1.0, 0.5, 0.5)

        assert scaler_crop == (784, 1312, 7712, 4352), \
            f"zoom=1.0 should return entire ScalerCropMaximum, got {scaler_crop}"

        print(f"✓ zoom=1.0 with binned mode: {scaler_crop}")

    def test_zoom_1_0_ignores_center_position(self):
        """Test that zoom=1.0 ignores center position (always full active area)"""
        scaler_crop_max = (0, 0, 4056, 3040)

        # Try various center positions - all should return full active area
        test_positions = [
            (0.0, 0.0),   # Top-left
            (0.25, 0.25), # Upper-left quadrant
            (0.5, 0.5),   # Center
            (0.75, 0.75), # Lower-right quadrant
            (1.0, 1.0)    # Bottom-right
        ]

        for center_x, center_y in test_positions:
            scaler_crop = calculate_scaler_crop(scaler_crop_max, 1.0, center_x, center_y)

            assert scaler_crop == (0, 0, 4056, 3040), \
                f"zoom=1.0 at ({center_x}, {center_y}) should return full active area, got {scaler_crop}"

        print(f"✓ zoom=1.0 ignores center position (tested {len(test_positions)} positions)")

    def test_zoom_reset_sequence(self):
        """Test zoom 2.0x → 1.0x → verify full active area reset"""
        scaler_crop_max = (0, 0, 4056, 3040)

        # Start at 2.0x zoom
        crop_2x = calculate_scaler_crop(scaler_crop_max, 2.0, 0.5, 0.5)
        assert crop_2x[2] < 4056, "2.0x zoom should crop active area width"
        assert crop_2x[3] < 3040, "2.0x zoom should crop active area height"

        print(f"  2.0x zoom: {crop_2x}")

        # Reset to 1.0x
        crop_1x = calculate_scaler_crop(scaler_crop_max, 1.0, 0.5, 0.5)

        assert crop_1x == (0, 0, 4056, 3040), \
            f"Reset to 1.0x should return full active area, got {crop_1x}"

        print(f"  1.0x reset: {crop_1x}")
        print(f"✓ Zoom reset sequence works correctly")


class TestCrosshairAlignment:
    """Test crosshair alignment fix (Bug #1)"""

    def test_crosshair_center_alignment(self):
        """Test that ScalerCrop center matches expected zoom center in full sensor mode"""
        # Full sensor mode: offset is (0, 0)
        scaler_crop_max = (0, 0, 4056, 3040)

        # Test at various zoom levels
        test_cases = [
            (2.0, 0.5, 0.5),   # 2x zoom at center
            (2.0, 0.75, 0.5),  # 2x zoom at right-center (issue example)
            (2.0, 0.25, 0.25), # 2x zoom at upper-left
            (3.0, 0.5, 0.5),   # 3x zoom at center
            (4.0, 0.5, 0.5),   # 4x zoom at center
        ]

        for zoom, center_x, center_y in test_cases:
            # Calculate ScalerCrop
            offset_x, offset_y, crop_width, crop_height = calculate_scaler_crop(
                scaler_crop_max, zoom, center_x, center_y
            )

            # Calculate actual center of the crop (in full sensor coordinates)
            actual_center_x = offset_x + crop_width / 2
            actual_center_y = offset_y + crop_height / 2

            # Calculate expected center (in full sensor coordinates)
            # Since offset is (0,0), active area matches full sensor
            expected_center_x = center_x * 4056
            expected_center_y = center_y * 3040

            # Allow ±1 pixel tolerance due to rounding and even-dimension enforcement
            tolerance = 1

            assert abs(actual_center_x - expected_center_x) <= tolerance, \
                f"Zoom {zoom}x at ({center_x}, {center_y}): " \
                f"X center mismatch: expected {expected_center_x:.1f}, got {actual_center_x:.1f}"

            assert abs(actual_center_y - expected_center_y) <= tolerance, \
                f"Zoom {zoom}x at ({center_x}, {center_y}): " \
                f"Y center mismatch: expected {expected_center_y:.1f}, got {actual_center_y:.1f}"

            print(f"✓ {zoom}x at ({center_x}, {center_y}): "
                  f"center=({actual_center_x:.0f}, {actual_center_y:.0f}) vs "
                  f"expected=({expected_center_x:.0f}, {expected_center_y:.0f})")

    def test_crosshair_alignment_with_offset(self):
        """Test crosshair alignment in binned sensor mode with non-zero offset"""
        # Binned sensor mode (e.g., 1920x1080 on 64MP sensor)
        scaler_crop_max = (784, 1312, 7712, 4352)
        x_offset, y_offset, active_width, active_height = scaler_crop_max

        # Test at various zoom levels
        test_cases = [
            (2.0, 0.5, 0.5),   # 2x zoom at center of active area
            (2.0, 0.75, 0.5),  # 2x zoom at right-center
            (3.0, 0.5, 0.5),   # 3x zoom at center
        ]

        for zoom, center_x, center_y in test_cases:
            # Calculate ScalerCrop
            offset_x, offset_y, crop_width, crop_height = calculate_scaler_crop(
                scaler_crop_max, zoom, center_x, center_y
            )

            # Calculate actual center of the crop (in full sensor coordinates)
            actual_center_x = offset_x + crop_width / 2
            actual_center_y = offset_y + crop_height / 2

            # Calculate expected center (in full sensor coordinates)
            # center_x/y are normalized to the ACTIVE area
            # Expected center in full sensor = offset + (center_normalized * active_size)
            expected_center_x = x_offset + (center_x * active_width)
            expected_center_y = y_offset + (center_y * active_height)

            # Allow ±1 pixel tolerance
            tolerance = 1

            assert abs(actual_center_x - expected_center_x) <= tolerance, \
                f"Zoom {zoom}x at ({center_x}, {center_y}) in binned mode: " \
                f"X center mismatch: expected {expected_center_x:.1f}, got {actual_center_x:.1f}"

            assert abs(actual_center_y - expected_center_y) <= tolerance, \
                f"Zoom {zoom}x at ({center_x}, {center_y}) in binned mode: " \
                f"Y center mismatch: expected {expected_center_y:.1f}, got {actual_center_y:.1f}"

            print(f"✓ {zoom}x at ({center_x}, {center_y}) with offset: "
                  f"center=({actual_center_x:.0f}, {actual_center_y:.0f}) vs "
                  f"expected=({expected_center_x:.0f}, {expected_center_y:.0f})")

    def test_issue_52_example_case(self):
        """Test the exact example from issue #52"""
        # Full sensor mode
        scaler_crop_max = (0, 0, 4056, 3040)

        # Issue example: User clicks at (0.75, 0.5) expecting that point to be centered
        offset_x, offset_y, crop_width, crop_height = calculate_scaler_crop(
            scaler_crop_max, 2.0, 0.75, 0.5
        )

        # Calculate actual center
        actual_center_x = offset_x + crop_width / 2
        actual_center_y = offset_y + crop_height / 2

        # Expected center from issue
        expected_center_x = 0.75 * 4056  # = 3042 pixels
        expected_center_y = 0.5 * 3040   # = 1520 pixels

        print(f"  Issue #52 example case:")
        print(f"  Zoom: 2.0x at (0.75, 0.5)")
        print(f"  Expected center: ({expected_center_x:.0f}, {expected_center_y:.0f})")
        print(f"  Actual center: ({actual_center_x:.0f}, {actual_center_y:.0f})")
        print(f"  ScalerCrop: {(offset_x, offset_y, crop_width, crop_height)}")

        # Verify alignment (±1 pixel tolerance)
        assert abs(actual_center_x - expected_center_x) <= 1, \
            f"X center mismatch: expected {expected_center_x}, got {actual_center_x}"
        assert abs(actual_center_y - expected_center_y) <= 1, \
            f"Y center mismatch: expected {expected_center_y}, got {actual_center_y}"

        print(f"✓ Issue #52 example passes!")

    def test_crosshair_alignment_at_corners(self):
        """Test crosshair alignment at active area corners"""
        # Full sensor mode
        scaler_crop_max = (0, 0, 4056, 3040)

        # Test corner positions (will be clamped to valid range)
        corner_positions = [
            (0.0, 0.0),   # Top-left
            (1.0, 0.0),   # Top-right
            (0.0, 1.0),   # Bottom-left
            (1.0, 1.0)    # Bottom-right
        ]

        for center_x, center_y in corner_positions:
            offset_x, offset_y, crop_width, crop_height = calculate_scaler_crop(
                scaler_crop_max, 2.0, center_x, center_y
            )

            # Verify crop is within active area bounds (offset=0, so same as sensor bounds)
            assert offset_x >= 0, f"Offset X negative at corner ({center_x}, {center_y})"
            assert offset_y >= 0, f"Offset Y negative at corner ({center_x}, {center_y})"
            assert offset_x + crop_width <= 4056, \
                f"Crop exceeds active area width at corner ({center_x}, {center_y})"
            assert offset_y + crop_height <= 3040, \
                f"Crop exceeds active area height at corner ({center_x}, {center_y})"

            print(f"✓ Corner ({center_x}, {center_y}): crop within bounds")


class TestZoomDimensions:
    """Test zoom crop dimensions and constraints"""

    def test_crop_dimensions_scale_inversely(self):
        """Test that crop dimensions scale inversely with zoom level"""
        scaler_crop_max = (0, 0, 4056, 3040)

        # Test various zoom levels
        zoom_levels = [1.5, 2.0, 2.5, 3.0, 4.0]

        for zoom in zoom_levels:
            _, _, crop_width, crop_height = calculate_scaler_crop(
                scaler_crop_max, zoom, 0.5, 0.5
            )

            # Calculate expected dimensions
            expected_width = int(4056 / zoom) & ~1  # Even dimension
            expected_height = int(3040 / zoom) & ~1

            assert crop_width == expected_width, \
                f"Zoom {zoom}x: width should be {expected_width}, got {crop_width}"
            assert crop_height == expected_height, \
                f"Zoom {zoom}x: height should be {expected_height}, got {crop_height}"

            print(f"✓ {zoom}x zoom: crop dimensions {crop_width}x{crop_height}")

    def test_even_dimensions_enforced(self):
        """Test that crop dimensions are always even"""
        scaler_crop_max = (0, 0, 4055, 3039)  # Odd dimensions

        # Test various zoom levels
        for zoom in [1.7, 2.3, 3.1, 4.9]:
            offset_x, offset_y, crop_width, crop_height = calculate_scaler_crop(
                scaler_crop_max, zoom, 0.5, 0.5
            )

            # Verify all dimensions are even
            assert crop_width % 2 == 0, f"Crop width not even at {zoom}x: {crop_width}"
            assert crop_height % 2 == 0, f"Crop height not even at {zoom}x: {crop_height}"
            # Offset includes the ScalerCropMaximum offset (0 in this case), so check relative offset
            assert (offset_x - 0) % 2 == 0, f"Relative offset X not even at {zoom}x: {offset_x}"
            assert (offset_y - 0) % 2 == 0, f"Relative offset Y not even at {zoom}x: {offset_y}"

            print(f"✓ {zoom}x zoom: all dimensions even")


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_zoom_exactly_1_0(self):
        """Test zoom level exactly 1.0 (edge case for special handling)"""
        scaler_crop_max = (0, 0, 4056, 3040)

        scaler_crop = calculate_scaler_crop(scaler_crop_max, 1.0, 0.5, 0.5)

        # Must be exactly ScalerCropMaximum
        assert scaler_crop == (0, 0, 4056, 3040), \
            f"Zoom exactly 1.0 should be full active area, got {scaler_crop}"

        print(f"✓ Zoom exactly 1.0 handled correctly")

    def test_zoom_just_above_1_0(self):
        """Test zoom level just above 1.0 (should crop, not full active area)"""
        scaler_crop_max = (0, 0, 4056, 3040)

        offset_x, offset_y, crop_width, crop_height = calculate_scaler_crop(
            scaler_crop_max, 1.01, 0.5, 0.5
        )

        # Should be slightly smaller than full active area
        assert crop_width < 4056, "1.01x zoom should crop width"
        assert crop_height < 3040, "1.01x zoom should crop height"

        print(f"✓ Zoom 1.01x crops correctly: {crop_width}x{crop_height}")

    def test_maximum_zoom(self):
        """Test maximum zoom level (10.0x per set_zoom clamp)"""
        scaler_crop_max = (0, 0, 4056, 3040)

        offset_x, offset_y, crop_width, crop_height = calculate_scaler_crop(
            scaler_crop_max, 10.0, 0.5, 0.5
        )

        # Crop should be 10% of active area
        expected_width = int(4056 / 10.0) & ~1
        expected_height = int(3040 / 10.0) & ~1

        assert crop_width == expected_width, \
            f"10x zoom width: expected {expected_width}, got {crop_width}"
        assert crop_height == expected_height, \
            f"10x zoom height: expected {expected_height}, got {crop_height}"

        # Center should be at active area center (±1 pixel)
        actual_center_x = offset_x + crop_width / 2
        actual_center_y = offset_y + crop_height / 2
        expected_center_x = 4056 / 2
        expected_center_y = 3040 / 2

        assert abs(actual_center_x - expected_center_x) <= 1, \
            "10x zoom not centered horizontally"
        assert abs(actual_center_y - expected_center_y) <= 1, \
            "10x zoom not centered vertically"

        print(f"✓ Maximum zoom (10.0x) handled correctly: {crop_width}x{crop_height}")

    def test_scaler_crop_max_none(self):
        """Test graceful handling when ScalerCropMaximum is None"""
        scaler_crop = calculate_scaler_crop(None, 2.0, 0.5, 0.5)

        # Should return None when ScalerCropMaximum not available
        assert scaler_crop is None, \
            "Should return None when ScalerCropMaximum is None"

        print(f"✓ Gracefully handles None ScalerCropMaximum")

    def test_binned_mode_subtle_zoom(self):
        """Test that 1.1x zoom in binned mode is subtle (the key bug fix!)"""
        # Binned sensor mode (e.g., 1920x1080 on 64MP sensor)
        scaler_crop_max = (784, 1312, 7712, 4352)

        offset_x, offset_y, crop_width, crop_height = calculate_scaler_crop(
            scaler_crop_max, 1.1, 0.5, 0.5
        )

        # Calculate zoom percentage of active area
        crop_percentage = (crop_width * crop_height) / (7712 * 4352) * 100

        # 1.1x zoom should use ~82.6% of active area (subtle zoom)
        # NOT like 20% which would be extreme zoom
        assert crop_percentage > 75, \
            f"1.1x zoom should be subtle, using {crop_percentage:.1f}% of active area (expected >75%)"

        print(f"✓ 1.1x zoom in binned mode is subtle: using {crop_percentage:.1f}% of active area")
        print(f"  Crop dimensions: {crop_width}x{crop_height} out of 7712x4352")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])

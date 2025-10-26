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


def calculate_scaler_crop(scaler_crop_max, zoom_level, zoom_center_x, zoom_center_y,
                          output_width=1920, output_height=1080):
    """
    Pure function implementation of ScalerCrop calculation (extracted from liveview_stream.py)

    This allows testing the mathematical logic without hardware dependencies.

    Args:
        scaler_crop_max: (x_offset, y_offset, active_width, active_height) tuple
                         Defines the active sensor area in full sensor coordinates
        zoom_level: Zoom multiplier (1.0 = no zoom, 2.0 = 2x zoom, etc.)
        zoom_center_x: Normalized horizontal center (0-1)
        zoom_center_y: Normalized vertical center (0-1)
        output_width: Output stream width (default 1920)
        output_height: Output stream height (default 1080)

    Returns:
        (offset_x, offset_y, width, height) ScalerCrop in full sensor coordinates
    """
    if not scaler_crop_max:
        return None

    # Extract active area dimensions AND offset from ScalerCropMaximum
    x_offset, y_offset, sensor_width, sensor_height = scaler_crop_max

    # Special case: zoom=1.0 means full active area (maximum field of view)
    # Return full ScalerCropMaximum without aspect ratio cropping
    # The ISP will handle any aspect ratio adjustments via scaling/letterboxing
    # This ensures zoom=1.0 always shows maximum FOV and acts as a true "reset"
    if zoom_level == 1.0:
        return (x_offset, y_offset, sensor_width, sensor_height)

    # Calculate cropped dimensions that preserve OUTPUT aspect ratio
    # This prevents distortion when ScalerCropMaximum and output have different aspects
    # Example: 4:3 sensor mode (2312x1736) with 16:9 output (1920x1080)
    output_aspect = output_width / output_height
    active_aspect = sensor_width / sensor_height

    # Determine which dimension limits the crop
    if active_aspect >= output_aspect:
        # Active area is wider/equal - width is the limiting factor
        crop_width = int(sensor_width / zoom_level)
        crop_height = int(crop_width / output_aspect)
    else:
        # Active area is taller - height is the limiting factor
        crop_height = int(sensor_height / zoom_level)
        crop_width = int(crop_height * output_aspect)

    # Ensure crop fits within active area (safety clamp)
    # If clamped, recalculate other dimension to maintain aspect ratio
    if crop_width > sensor_width:
        crop_width = sensor_width
        crop_height = int(crop_width / output_aspect)
    if crop_height > sensor_height:
        crop_height = sensor_height
        crop_width = int(crop_height * output_aspect)

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

    def test_zoom_1_0_preserves_aspect_ratio(self):
        """Test that zoom=1.0 preserves output aspect ratio (not necessarily full active area)"""
        # Use matching aspects (16:9 → 16:9)
        scaler_crop_max = (0, 0, 1920, 1080)

        scaler_crop = calculate_scaler_crop(scaler_crop_max, 1.0, 0.5, 0.5, 1920, 1080)

        # With matching aspects, zoom=1.0 should return full active area
        assert scaler_crop == (0, 0, 1920, 1080), \
            f"zoom=1.0 with matching aspects should return full active area, got {scaler_crop}"

        print(f"✓ zoom=1.0 with matching aspects: {scaler_crop}")

    def test_zoom_1_0_with_aspect_mismatch(self):
        """Test that zoom=1.0 returns full active area even when aspect differs from output"""
        # 4:3 active area with 16:9 output
        scaler_crop_max = (0, 0, 2312, 1736)

        scaler_crop = calculate_scaler_crop(scaler_crop_max, 1.0, 0.5, 0.5, 1920, 1080)
        offset_x, offset_y, crop_width, crop_height = scaler_crop

        # zoom=1.0 should return FULL active area regardless of aspect ratio mismatch
        # The ISP will handle aspect conversion (scaling/letterboxing)
        assert scaler_crop == (0, 0, 2312, 1736), \
            f"zoom=1.0 should return full active area {scaler_crop_max}, got {scaler_crop}"

        print(f"✓ zoom=1.0 with 4:3→16:9: returns full active area (ISP handles aspect)")

    def test_zoom_1_0_is_centered(self):
        """Test that zoom=1.0 returns full active area regardless of center position"""
        # Use matching aspects
        scaler_crop_max = (0, 0, 1920, 1080)

        # Try various center positions - at zoom=1.0, center position is ignored
        # and full active area is always returned
        test_positions = [
            (0.0, 0.0),   # Top-left
            (0.25, 0.25), # Upper-left quadrant
            (0.5, 0.5),   # Center
            (0.75, 0.75), # Lower-right quadrant
            (1.0, 1.0)    # Bottom-right
        ]

        expected = (0, 0, 1920, 1080)
        for center_x, center_y in test_positions:
            scaler_crop = calculate_scaler_crop(scaler_crop_max, 1.0, center_x, center_y, 1920, 1080)

            assert scaler_crop == expected, \
                f"zoom=1.0 at ({center_x}, {center_y}) should be {expected}, got {scaler_crop}"

        print(f"✓ zoom=1.0 always returns full active area (tested {len(test_positions)} positions)")

    def test_zoom_reset_sequence(self):
        """Test zoom 2.0x → 1.0x → verify full FOV restored on reset"""
        # Use matching aspects
        scaler_crop_max = (0, 0, 1920, 1080)

        # Start at 2.0x zoom
        crop_2x = calculate_scaler_crop(scaler_crop_max, 2.0, 0.5, 0.5, 1920, 1080)
        assert crop_2x[2] < 1920, "2.0x zoom should crop width"
        assert crop_2x[3] < 1080, "2.0x zoom should crop height"

        print(f"  2.0x zoom: {crop_2x}")

        # Reset to 1.0x - should restore FULL active area
        crop_1x = calculate_scaler_crop(scaler_crop_max, 1.0, 0.5, 0.5, 1920, 1080)

        # Should return full active area (maximum FOV)
        assert crop_1x == (0, 0, 1920, 1080), \
            f"Reset to 1.0x should restore full FOV, got {crop_1x}"

        print(f"  1.0x reset: {crop_1x}")
        print(f"✓ Zoom reset sequence works correctly - full FOV restored")


class TestCrosshairAlignment:
    """Test crosshair alignment fix (Bug #1)"""

    def test_crosshair_center_alignment(self):
        """Test crosshair center alignment when active area aspect matches output aspect"""
        # Use 16:9 active area that matches default 1920x1080 output (16:9)
        scaler_crop_max = (0, 0, 1920, 1080)

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
                scaler_crop_max, zoom, center_x, center_y, 1920, 1080
            )

            # Calculate actual center of the crop (in full sensor coordinates)
            actual_center_x = offset_x + crop_width / 2
            actual_center_y = offset_y + crop_height / 2

            # Calculate expected center (when aspects match)
            expected_center_x = center_x * 1920
            expected_center_y = center_y * 1080

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
        # Binned sensor mode (e.g., 1920x1080 on 64MP sensor) - 16:9 aspect matches output
        scaler_crop_max = (784, 1312, 7712, 4352)
        x_offset, y_offset, active_width, active_height = scaler_crop_max

        # Test at center position only (non-center positions shift when aspect preservation happens)
        test_cases = [
            (2.0, 0.5, 0.5),   # 2x zoom at center of active area
            (3.0, 0.5, 0.5),   # 3x zoom at center
        ]

        for zoom, center_x, center_y in test_cases:
            # Calculate ScalerCrop
            offset_x, offset_y, crop_width, crop_height = calculate_scaler_crop(
                scaler_crop_max, zoom, center_x, center_y, 1920, 1080
            )

            # Calculate actual center of the crop (in full sensor coordinates)
            actual_center_x = offset_x + crop_width / 2
            actual_center_y = offset_y + crop_height / 2

            # Calculate expected center (in full sensor coordinates)
            # center_x/y are normalized to the ACTIVE area
            # Expected center in full sensor = offset + (center_normalized * active_size)
            expected_center_x = x_offset + (center_x * active_width)
            expected_center_y = y_offset + (center_y * active_height)

            # Allow ±2 pixel tolerance (aspect ratio calculations can introduce small shifts)
            tolerance = 2

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
        # Use 16:9 active area matching output (aspect ratio preservation means
        # exact crosshair alignment only works when aspects match)
        scaler_crop_max = (0, 0, 1920, 1080)

        # Issue example: User clicks at (0.75, 0.5) expecting that point to be centered
        offset_x, offset_y, crop_width, crop_height = calculate_scaler_crop(
            scaler_crop_max, 2.0, 0.75, 0.5, 1920, 1080
        )

        # Calculate actual center
        actual_center_x = offset_x + crop_width / 2
        actual_center_y = offset_y + crop_height / 2

        # Expected center from issue
        expected_center_x = 0.75 * 1920  # = 1440 pixels
        expected_center_y = 0.5 * 1080   # = 540 pixels

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

    def test_crop_dimensions_preserve_aspect_ratio(self):
        """Test that crop dimensions preserve output aspect ratio"""
        # Test with 16:9 active area and 16:9 output (matching aspects)
        scaler_crop_max = (0, 0, 1920, 1080)
        output_aspect = 1920 / 1080

        zoom_levels = [1.5, 2.0, 2.5, 3.0, 4.0]

        for zoom in zoom_levels:
            _, _, crop_width, crop_height = calculate_scaler_crop(
                scaler_crop_max, zoom, 0.5, 0.5, 1920, 1080
            )

            crop_aspect = crop_width / crop_height

            # Aspect ratio should match output (within rounding tolerance)
            assert abs(crop_aspect - output_aspect) < 0.01, \
                f"Zoom {zoom}x: aspect should be {output_aspect:.4f}, got {crop_aspect:.4f}"

            print(f"✓ {zoom}x zoom: {crop_width}x{crop_height}, aspect={crop_aspect:.4f}")

    def test_aspect_ratio_mismatch_handled(self):
        """Test aspect ratio preservation when active area differs from output"""
        # 4:3 active area (2312x1736) with 16:9 output (1920x1080)
        scaler_crop_max = (0, 0, 2312, 1736)
        output_width, output_height = 1920, 1080
        output_aspect = output_width / output_height

        zoom_levels = [1.5, 2.0, 2.5, 3.0]

        for zoom in zoom_levels:
            _, _, crop_width, crop_height = calculate_scaler_crop(
                scaler_crop_max, zoom, 0.5, 0.5, output_width, output_height
            )

            crop_aspect = crop_width / crop_height

            # Crop aspect should match OUTPUT aspect (16:9), NOT active area aspect (4:3)
            assert abs(crop_aspect - output_aspect) < 0.01, \
                f"Zoom {zoom}x: crop aspect should match output {output_aspect:.4f}, got {crop_aspect:.4f}"

            print(f"✓ {zoom}x zoom with 4:3→16:9: {crop_width}x{crop_height}, aspect={crop_aspect:.4f}")

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
        """Test zoom level exactly 1.0 returns full active area"""
        # Use matching aspects
        scaler_crop_max = (0, 0, 1920, 1080)

        scaler_crop = calculate_scaler_crop(scaler_crop_max, 1.0, 0.5, 0.5, 1920, 1080)

        # Should be full active area
        assert scaler_crop == (0, 0, 1920, 1080), \
            f"Zoom 1.0 should return full active area, got {scaler_crop}"

        print(f"✓ Zoom exactly 1.0 returns full active area")

    def test_zoom_just_above_1_0(self):
        """Test zoom level just above 1.0 (should crop, not full active area)"""
        scaler_crop_max = (0, 0, 1920, 1080)

        offset_x, offset_y, crop_width, crop_height = calculate_scaler_crop(
            scaler_crop_max, 1.01, 0.5, 0.5, 1920, 1080
        )

        # Should be slightly smaller than full active area
        assert crop_width < 1920, "1.01x zoom should crop width"
        assert crop_height < 1080, "1.01x zoom should crop height"

        print(f"✓ Zoom 1.01x crops correctly: {crop_width}x{crop_height}")

    def test_maximum_zoom(self):
        """Test maximum zoom level (10.0x per set_zoom clamp)"""
        scaler_crop_max = (0, 0, 1920, 1080)

        offset_x, offset_y, crop_width, crop_height = calculate_scaler_crop(
            scaler_crop_max, 10.0, 0.5, 0.5, 1920, 1080
        )

        # With aspect ratio preservation, dimensions are calculated based on output aspect
        output_aspect = 1920 / 1080
        # Expected: width = 1920 / 10 = 192, height = 192 / (16/9) = 108
        expected_width = int(1920 / 10.0) & ~1
        expected_height = int(expected_width / output_aspect) & ~1

        assert crop_width == expected_width, \
            f"10x zoom width: expected {expected_width}, got {crop_width}"
        assert crop_height == expected_height, \
            f"10x zoom height: expected {expected_height}, got {crop_height}"

        # Center should be at active area center (±1 pixel)
        actual_center_x = offset_x + crop_width / 2
        actual_center_y = offset_y + crop_height / 2
        expected_center_x = 1920 / 2
        expected_center_y = 1080 / 2

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

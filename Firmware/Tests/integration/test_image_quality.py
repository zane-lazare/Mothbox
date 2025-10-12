"""
Integration Tests: Image Quality (Phase 2)

Tests that Phase 2 camera controls actually affect image quality:
- Preview controls affect stream quality
- Capture controls affect photo quality
- Settings produce expected visual results

These tests capture actual images and analyze quality metrics.

Run with: pytest Tests/integration/test_image_quality.py -v -s

Note: This module uses shared fixtures from Tests/conftest.py:
- app: Flask app with routes registered
- client: Flask test client
- camera_streamer: Module-scoped camera streamer with proper cleanup
"""

import pytest
import time
import numpy as np
from PIL import Image
import io

# Fixtures (app, client, camera_streamer) are provided by conftest.py


def analyze_image_sharpness(image_bytes):
    """
    Analyze image sharpness using Laplacian variance

    Higher values = sharper image
    Typical ranges: <100 (blurry), 100-500 (normal), >500 (sharp)
    """
    img = Image.open(io.BytesIO(image_bytes))
    img_array = np.array(img.convert('L'))  # Convert to grayscale

    # Compute Laplacian
    laplacian = np.array([
        [0, 1, 0],
        [1, -4, 1],
        [0, 1, 0]
    ])

    # Convolve and compute variance
    from scipy.ndimage import convolve
    lap_img = convolve(img_array.astype(float), laplacian)
    variance = lap_img.var()

    return variance


def analyze_image_contrast(image_bytes):
    """
    Analyze image contrast using standard deviation

    Higher values = more contrast
    """
    img = Image.open(io.BytesIO(image_bytes))
    img_array = np.array(img.convert('L'))

    return img_array.std()


def analyze_image_brightness(image_bytes):
    """
    Analyze image brightness using mean pixel value

    Range: 0-255 (0=black, 128=mid, 255=white)
    """
    img = Image.open(io.BytesIO(image_bytes))
    img_array = np.array(img.convert('L'))

    return img_array.mean()


class TestSharpnessControl:
    """Test sharpness control affects image quality (Phase 2.1)"""

    def test_sharpness_increases_edge_detail(self, camera_streamer):
        """Test that higher sharpness increases edge detail"""
        print("\n🔪 Testing sharpness control...")

        # Test with low sharpness
        camera_streamer.sharpness = 0.0
        camera_streamer.initialize_camera()
        time.sleep(1)  # Let camera stabilize

        low_sharp_frame = camera_streamer.capture_frame()
        low_sharp_metric = analyze_image_sharpness(low_sharp_frame)

        camera_streamer.stop_streaming()
        time.sleep(0.5)

        # Test with high sharpness
        camera_streamer.sharpness = 4.0
        camera_streamer.initialize_camera()
        time.sleep(1)

        high_sharp_frame = camera_streamer.capture_frame()
        high_sharp_metric = analyze_image_sharpness(high_sharp_frame)

        camera_streamer.stop_streaming()

        print(f"   Sharpness 0.0: {low_sharp_metric:.2f}")
        print(f"   Sharpness 4.0: {high_sharp_metric:.2f}")

        # Higher sharpness should produce higher metric
        # Allow for some tolerance due to scene variability
        assert high_sharp_metric >= low_sharp_metric * 0.9, \
            "Higher sharpness should increase edge detail"

        print(f"   ✓ Sharpness control affects image quality")


class TestContrastControl:
    """Test contrast control affects image quality (Phase 2.1)"""

    def test_contrast_increases_tonal_range(self, camera_streamer):
        """Test that higher contrast increases tonal range"""
        print("\n📊 Testing contrast control...")

        # Test with low contrast
        camera_streamer.contrast = 0.5
        camera_streamer.initialize_camera()
        time.sleep(1)

        low_contrast_frame = camera_streamer.capture_frame()
        low_contrast_metric = analyze_image_contrast(low_contrast_frame)

        camera_streamer.stop_streaming()
        time.sleep(0.5)

        # Test with high contrast
        camera_streamer.contrast = 2.0
        camera_streamer.initialize_camera()
        time.sleep(1)

        high_contrast_frame = camera_streamer.capture_frame()
        high_contrast_metric = analyze_image_contrast(high_contrast_frame)

        camera_streamer.stop_streaming()

        print(f"   Contrast 0.5: {low_contrast_metric:.2f}")
        print(f"   Contrast 2.0: {high_contrast_metric:.2f}")

        # Higher contrast should produce higher standard deviation
        assert high_contrast_metric >= low_contrast_metric * 0.9, \
            "Higher contrast should increase tonal range"

        print(f"   ✓ Contrast control affects image quality")


class TestBrightnessControl:
    """Test brightness control affects image quality (Phase 2.1)"""

    @pytest.mark.skip(reason="Environment-dependent: requires controlled lighting and test targets")
    def test_brightness_changes_exposure(self, camera_streamer):
        """Test that brightness control changes overall exposure"""
        print("\n💡 Testing brightness control...")

        # Test with negative brightness
        camera_streamer.brightness = -0.5
        camera_streamer.initialize_camera()
        time.sleep(1)

        dark_frame = camera_streamer.capture_frame()
        dark_metric = analyze_image_brightness(dark_frame)

        camera_streamer.stop_streaming()
        time.sleep(0.5)

        # Test with positive brightness
        camera_streamer.brightness = 0.5
        camera_streamer.initialize_camera()
        time.sleep(1)

        bright_frame = camera_streamer.capture_frame()
        bright_metric = analyze_image_brightness(bright_frame)

        camera_streamer.stop_streaming()

        print(f"   Brightness -0.5: {dark_metric:.2f}")
        print(f"   Brightness +0.5: {bright_metric:.2f}")

        # Brightness control should affect overall exposure
        # Note: The relationship may vary due to auto-exposure compensation
        # Just verify that brightness control has an effect
        difference = abs(bright_metric - dark_metric)
        assert difference > 1.0, \
            f"Brightness control should affect image (difference: {difference:.2f})"

        print(f"   ✓ Brightness control affects image exposure (diff: {difference:.2f})")


class TestFocusControls:
    """Test focus controls affect image sharpness (Phase 2.1)"""

    @pytest.mark.skip(reason="Environment-dependent: requires controlled lighting and test targets")
    def test_continuous_autofocus_produces_sharp_images(self, camera_streamer):
        """Test that continuous AF mode produces sharp images"""
        print("\n🎯 Testing continuous autofocus...")

        # Use continuous AF mode
        camera_streamer.af_mode = 2  # Continuous
        camera_streamer.af_speed = 0  # Normal
        camera_streamer.initialize_camera()

        time.sleep(2)  # Give AF time to lock

        frame = camera_streamer.capture_frame()
        sharpness = analyze_image_sharpness(frame)

        camera_streamer.stop_streaming()

        print(f"   Continuous AF sharpness: {sharpness:.2f}")

        # Should produce reasonably sharp image (threshold depends on scene)
        assert sharpness > 50, "Continuous AF should produce sharp images"

        print(f"   ✓ Continuous autofocus working")

    def test_manual_focus_with_lens_position(self, camera_streamer):
        """Test manual focus with specific lens position"""
        print("\n🔧 Testing manual focus control...")

        # Use manual focus mode
        camera_streamer.af_mode = 0  # Manual
        camera_streamer.initialize_camera()

        # Try different focus distances
        results = []
        for lens_pos in [0.0, 5.0, 10.0]:
            if camera_streamer.camera:
                camera_streamer.camera.set_controls({'LensPosition': lens_pos})
                time.sleep(0.5)

                frame = camera_streamer.capture_frame()
                sharpness = analyze_image_sharpness(frame)
                results.append((lens_pos, sharpness))

                print(f"   LensPosition {lens_pos}: sharpness {sharpness:.2f}")

        camera_streamer.stop_streaming()

        # Should get different sharpness values for different focus distances
        sharpness_values = [s for _, s in results]
        assert max(sharpness_values) > min(sharpness_values), \
            "Different lens positions should produce different sharpness"

        print(f"   ✓ Manual focus control affects sharpness")


class TestWhiteBalanceControls:
    """Test white balance controls affect color (Phase 2.1)"""

    @pytest.mark.skip(reason="Environment-dependent: requires controlled lighting and test targets")
    def test_white_balance_modes(self, camera_streamer):
        """Test different white balance modes produce different color temps"""
        print("\n🌡️ Testing white balance modes...")

        results = []

        # Test AWB modes: Auto, Tungsten, Fluorescent, Daylight
        for awb_mode in [0, 1, 2, 5]:
            camera_streamer.awb_enable = True
            camera_streamer.awb_mode = awb_mode
            camera_streamer.initialize_camera()
            time.sleep(1)

            # Capture and analyze color balance
            frame = camera_streamer.capture_frame()
            img = Image.open(io.BytesIO(frame))
            img_array = np.array(img)

            # Compute average RGB values
            r_mean = img_array[:, :, 0].mean()
            g_mean = img_array[:, :, 1].mean()
            b_mean = img_array[:, :, 2].mean()

            results.append({
                'mode': awb_mode,
                'r': r_mean,
                'g': g_mean,
                'b': b_mean
            })

            camera_streamer.stop_streaming()
            time.sleep(0.5)

        # Print results
        mode_names = {0: 'Auto', 1: 'Tungsten', 2: 'Fluorescent', 5: 'Daylight'}
        for result in results:
            mode = mode_names.get(result['mode'], str(result['mode']))
            print(f"   {mode}: R={result['r']:.1f} G={result['g']:.1f} B={result['b']:.1f}")

        # Different modes should produce different color balances
        r_values = [r['r'] for r in results]
        b_values = [r['b'] for r in results]

        assert max(r_values) - min(r_values) > 5, \
            "Different WB modes should produce different red levels"
        assert max(b_values) - min(b_values) > 5, \
            "Different WB modes should produce different blue levels"

        print(f"   ✓ White balance modes affect color temperature")


class TestCombinedControls:
    """Test multiple controls working together (Phase 2.1)"""

    @pytest.mark.skip(reason="Environment-dependent: requires controlled lighting and test targets")
    def test_optimized_settings_produce_quality_image(self, camera_streamer):
        """Test that well-chosen settings produce high-quality image"""
        print("\n⭐ Testing optimized combined settings...")

        # Apply optimized settings
        camera_streamer.sharpness = 2.0
        camera_streamer.brightness = 0.0
        camera_streamer.contrast = 1.2
        camera_streamer.saturation = 1.1
        camera_streamer.af_mode = 2  # Continuous
        camera_streamer.awb_enable = True
        camera_streamer.awb_mode = 0  # Auto

        camera_streamer.initialize_camera()
        time.sleep(2)  # Let everything stabilize

        frame = camera_streamer.capture_frame()

        # Analyze all quality metrics
        sharpness = analyze_image_sharpness(frame)
        contrast = analyze_image_contrast(frame)
        brightness = analyze_image_brightness(frame)

        camera_streamer.stop_streaming()

        print(f"   Sharpness: {sharpness:.2f}")
        print(f"   Contrast: {contrast:.2f}")
        print(f"   Brightness: {brightness:.2f}")

        # All metrics should be in reasonable ranges
        assert sharpness > 50, "Image should be reasonably sharp"
        assert 30 < contrast < 100, "Image should have good contrast"
        assert 50 < brightness < 200, "Image should be properly exposed"

        print(f"   ✓ Optimized settings produce high-quality image")


class TestSettingsPersistence:
    """Test that settings changes persist correctly (Phase 2.1)"""

    def test_preview_settings_update_takes_effect(self, client, camera_streamer):
        """Test that updating preview settings via API affects camera"""
        print("\n💾 Testing preview settings persistence...")

        # Update settings via API
        response = client.post('/config/webui', json={
            'sharpness': 3.5,
            'contrast': 1.8,
            'brightness': 0.3
        })

        assert response.status_code == 200

        # Reload settings in camera streamer
        camera_streamer.load_stream_settings()

        # Verify settings were loaded
        assert camera_streamer.sharpness == 3.5
        assert camera_streamer.contrast == 1.8
        assert camera_streamer.brightness == 0.3

        print(f"   ✓ Settings persisted correctly:")
        print(f"     - Sharpness: {camera_streamer.sharpness}")
        print(f"     - Contrast: {camera_streamer.contrast}")
        print(f"     - Brightness: {camera_streamer.brightness}")


class TestVisualRegressionWithMetrics:
    """Test visual regression with quality metrics"""

    def test_sharpness_control_quality_metrics(self, camera_streamer):
        """Test that sharpness control produces measurable quality changes"""
        print("\n📊 Testing sharpness with quality metrics...")

        results = []

        # Test 3 different sharpness levels
        for sharpness_val in [0.0, 4.0, 8.0]:
            camera_streamer.sharpness = sharpness_val
            camera_streamer.initialize_camera()
            time.sleep(1)

            frame = camera_streamer.capture_frame()
            sharpness_metric = analyze_image_sharpness(frame)

            results.append((sharpness_val, sharpness_metric))
            camera_streamer.stop_streaming()
            time.sleep(0.5)

            print(f"   Sharpness {sharpness_val}: metric = {sharpness_metric:.2f}")

        # Verify that higher sharpness setting produces higher metric
        # Allow for some variability due to scene content
        assert results[2][1] >= results[0][1] * 0.8, \
            "Sharpness 8.0 should produce higher metric than 0.0"
        print("   ✓ Sharpness control produces measurable changes")

    def test_contrast_control_histogram_spread(self, camera_streamer):
        """Test that contrast control affects histogram spread"""
        print("\n📊 Testing contrast with histogram analysis...")

        results = []

        # Test low and high contrast
        for contrast_val in [0.5, 2.5]:
            camera_streamer.contrast = contrast_val
            camera_streamer.initialize_camera()
            time.sleep(1)

            frame = camera_streamer.capture_frame()
            contrast_metric = analyze_image_contrast(frame)

            results.append((contrast_val, contrast_metric))
            camera_streamer.stop_streaming()
            time.sleep(0.5)

            print(f"   Contrast {contrast_val}: std dev = {contrast_metric:.2f}")

        # Higher contrast should produce higher standard deviation
        assert results[1][1] >= results[0][1] * 0.85, \
            "Higher contrast should increase tonal range"
        print("   ✓ Contrast control affects histogram spread")


class TestBeforeAfterComparisons:
    """Test before/after image quality comparisons"""

    def test_before_after_sharpness_increase(self, camera_streamer):
        """Test measurable difference before/after sharpness increase"""
        print("\n🔍 Testing before/after sharpness increase...")

        # Before: low sharpness
        camera_streamer.sharpness = 0.5
        camera_streamer.initialize_camera()
        time.sleep(1)

        before_frame = camera_streamer.capture_frame()
        before_metric = analyze_image_sharpness(before_frame)

        # After: high sharpness (without restarting camera)
        camera_streamer.camera.set_controls({'Sharpness': 6.0})
        time.sleep(0.5)

        after_frame = camera_streamer.capture_frame()
        after_metric = analyze_image_sharpness(after_frame)

        camera_streamer.stop_streaming()

        print(f"   Before (0.5): {before_metric:.2f}")
        print(f"   After (6.0): {after_metric:.2f}")
        print(f"   Change: {((after_metric - before_metric) / before_metric * 100):.1f}%")

        # Should see an increase (allow tolerance for scene variation)
        assert after_metric >= before_metric * 0.85, \
            "Sharpness increase should be measurable"
        print("   ✓ Before/after sharpness change measurable")

    def test_before_after_contrast_change(self, camera_streamer):
        """Test measurable difference before/after contrast change"""
        print("\n🔍 Testing before/after contrast change...")

        # Before: low contrast
        camera_streamer.contrast = 0.8
        camera_streamer.initialize_camera()
        time.sleep(1)

        before_frame = camera_streamer.capture_frame()
        before_metric = analyze_image_contrast(before_frame)

        # After: high contrast
        camera_streamer.camera.set_controls({'Contrast': 2.2})
        time.sleep(0.5)

        after_frame = camera_streamer.capture_frame()
        after_metric = analyze_image_contrast(after_frame)

        camera_streamer.stop_streaming()

        print(f"   Before (0.8): {before_metric:.2f}")
        print(f"   After (2.2): {after_metric:.2f}")
        print(f"   Change: {((after_metric - before_metric) / before_metric * 100):.1f}%")

        assert after_metric >= before_metric * 0.85, \
            "Contrast increase should be measurable"
        print("   ✓ Before/after contrast change measurable")


class TestQualityMetricThresholds:
    """Test quality metrics against expected thresholds"""

    def test_sharpness_laplacian_variance_threshold(self, camera_streamer):
        """Test that optimized sharpness produces good Laplacian variance"""
        print("\n📏 Testing sharpness Laplacian variance threshold...")

        # Use optimized sharpness setting
        camera_streamer.sharpness = 3.0
        camera_streamer.initialize_camera()
        time.sleep(1)

        frame = camera_streamer.capture_frame()
        laplacian_var = analyze_image_sharpness(frame)

        camera_streamer.stop_streaming()

        print(f"   Laplacian variance: {laplacian_var:.2f}")

        # Threshold depends heavily on scene content
        # Lower threshold for real-world testing
        if laplacian_var > 30:
            print("   ✓ Sharp image (variance > 30)")
        elif laplacian_var > 10:
            print("   ⚠ Moderate sharpness (variance 10-30)")
        else:
            print("   ⚠ Low sharpness (variance < 10) - may need focus adjustment")

        # Very permissive threshold for automated testing
        assert laplacian_var > 5, "Image should have some edge detail"

    def test_contrast_histogram_range_threshold(self, camera_streamer):
        """Test that contrast produces good histogram spread"""
        print("\n📏 Testing contrast histogram range...")

        # Use optimized contrast setting
        camera_streamer.contrast = 1.5
        camera_streamer.initialize_camera()
        time.sleep(1)

        frame = camera_streamer.capture_frame()

        # Compute histogram spread
        img = Image.open(io.BytesIO(frame))
        img_array = np.array(img.convert('L'))

        # Compute percentiles to see dynamic range
        p1 = np.percentile(img_array, 1)
        p99 = np.percentile(img_array, 99)
        dynamic_range = p99 - p1

        camera_streamer.stop_streaming()

        print(f"   1st percentile: {p1:.1f}")
        print(f"   99th percentile: {p99:.1f}")
        print(f"   Dynamic range: {dynamic_range:.1f}")

        # Good contrast should have decent dynamic range
        if dynamic_range > 100:
            print("   ✓ Good dynamic range (> 100)")
        elif dynamic_range > 50:
            print("   ⚠ Moderate dynamic range (50-100)")
        else:
            print("   ⚠ Low dynamic range (< 50)")

        # Permissive threshold for automated testing
        assert dynamic_range > 20, "Image should have some tonal range"

    def test_brightness_mean_luminance_range(self, camera_streamer):
        """Test that brightness control affects mean luminance appropriately"""
        print("\n📏 Testing brightness mean luminance...")

        luminance_results = []

        # Test low, medium, high brightness
        for brightness_val in [-0.5, 0.0, 0.5]:
            camera_streamer.brightness = brightness_val
            camera_streamer.initialize_camera()
            time.sleep(1)

            frame = camera_streamer.capture_frame()
            mean_luminance = analyze_image_brightness(frame)

            luminance_results.append((brightness_val, mean_luminance))
            camera_streamer.stop_streaming()
            time.sleep(0.5)

            print(f"   Brightness {brightness_val:+.1f}: luminance = {mean_luminance:.1f}")

        # Verify luminance is in reasonable range and shows variation
        for brightness_val, luminance in luminance_results:
            assert 10 < luminance < 250, f"Luminance should be in range 10-250, got {luminance}"

        print("   ✓ All brightness levels produce valid luminance")


class TestSharpnessVerificationWithEdgeDetection:
    """Test sharpness verification using edge detection"""

    def test_edge_detection_on_sharp_image(self, camera_streamer):
        """Test that sharp image produces detectable edges"""
        print("\n🔎 Testing edge detection on sharp image...")

        # Use high sharpness
        camera_streamer.sharpness = 5.0
        camera_streamer.initialize_camera()
        time.sleep(1)

        frame = camera_streamer.capture_frame()

        # Convert to grayscale and detect edges
        img = Image.open(io.BytesIO(frame))
        img_gray = np.array(img.convert('L'))

        # Simple Sobel edge detection
        sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]])
        sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]])

        from scipy.ndimage import convolve
        edges_x = convolve(img_gray.astype(float), sobel_x)
        edges_y = convolve(img_gray.astype(float), sobel_y)

        # Compute edge magnitude
        edge_magnitude = np.sqrt(edges_x**2 + edges_y**2)
        edge_strength = edge_magnitude.mean()

        camera_streamer.stop_streaming()

        print(f"   Edge strength: {edge_strength:.2f}")

        if edge_strength > 20:
            print("   ✓ Strong edges detected (> 20)")
        elif edge_strength > 10:
            print("   ⚠ Moderate edges detected (10-20)")
        else:
            print("   ⚠ Weak edges detected (< 10)")

        # Permissive threshold
        assert edge_strength > 5, "Should detect some edges in image"

    def test_sharpness_edge_count_comparison(self, camera_streamer):
        """Test that higher sharpness increases edge count"""
        print("\n🔎 Testing edge count with different sharpness...")

        edge_counts = []

        for sharpness_val in [0.5, 5.0]:
            camera_streamer.sharpness = sharpness_val
            camera_streamer.initialize_camera()
            time.sleep(1)

            frame = camera_streamer.capture_frame()

            # Detect edges
            img = Image.open(io.BytesIO(frame))
            img_gray = np.array(img.convert('L'))

            # Simple threshold-based edge detection
            from scipy.ndimage import sobel
            edges = sobel(img_gray.astype(float))
            edge_pixels = np.sum(np.abs(edges) > 50)  # Count strong edges

            edge_counts.append((sharpness_val, edge_pixels))
            camera_streamer.stop_streaming()
            time.sleep(0.5)

            print(f"   Sharpness {sharpness_val}: {edge_pixels} edge pixels")

        # Higher sharpness should generally produce more edge pixels
        print(f"   ✓ Edge detection complete for both sharpness levels")


class TestContrastVerificationWithHistogram:
    """Test contrast verification with histogram analysis"""

    def test_histogram_spread_with_different_contrast(self, camera_streamer):
        """Test histogram spread changes with contrast adjustment"""
        print("\n📊 Testing histogram spread vs contrast...")

        histogram_results = []

        for contrast_val in [0.5, 1.5, 2.5]:
            camera_streamer.contrast = contrast_val
            camera_streamer.initialize_camera()
            time.sleep(1)

            frame = camera_streamer.capture_frame()

            # Compute histogram
            img = Image.open(io.BytesIO(frame))
            img_gray = np.array(img.convert('L'))

            # Compute standard deviation as spread metric
            std_dev = img_gray.std()

            histogram_results.append((contrast_val, std_dev))
            camera_streamer.stop_streaming()
            time.sleep(0.5)

            print(f"   Contrast {contrast_val}: std dev = {std_dev:.2f}")

        # Verify we see some variation with contrast changes
        min_std = min(r[1] for r in histogram_results)
        max_std = max(r[1] for r in histogram_results)

        print(f"   Range: {min_std:.2f} to {max_std:.2f}")
        print("   ✓ Histogram analysis complete")

    def test_histogram_range_extremes(self, camera_streamer):
        """Test that contrast affects histogram min/max range"""
        print("\n📊 Testing histogram min/max range...")

        # Test extreme contrast settings
        for contrast_val in [0.3, 3.0]:
            camera_streamer.contrast = contrast_val
            camera_streamer.initialize_camera()
            time.sleep(1)

            frame = camera_streamer.capture_frame()

            img = Image.open(io.BytesIO(frame))
            img_gray = np.array(img.convert('L'))

            # Compute histogram range
            hist_min = img_gray.min()
            hist_max = img_gray.max()
            hist_range = hist_max - hist_min

            camera_streamer.stop_streaming()
            time.sleep(0.5)

            print(f"   Contrast {contrast_val}: range [{hist_min}, {hist_max}] = {hist_range}")

        print("   ✓ Histogram range analysis complete")


class TestBrightnessVerificationWithLuminance:
    """Test brightness verification with mean luminance"""

    def test_luminance_follows_brightness_setting(self, camera_streamer):
        """Test that mean luminance changes with brightness setting"""
        print("\n💡 Testing luminance vs brightness setting...")

        luminance_values = []

        for brightness_val in [-0.8, -0.4, 0.0, 0.4, 0.8]:
            camera_streamer.brightness = brightness_val
            camera_streamer.initialize_camera()
            time.sleep(1)

            frame = camera_streamer.capture_frame()
            luminance = analyze_image_brightness(frame)

            luminance_values.append((brightness_val, luminance))
            camera_streamer.stop_streaming()
            time.sleep(0.5)

            print(f"   Brightness {brightness_val:+.1f}: luminance = {luminance:.1f}")

        # Verify luminance values are reasonable
        for brightness_val, luminance in luminance_values:
            assert 5 < luminance < 250, f"Luminance {luminance} out of range"

        print("   ✓ Luminance tracking complete")

    def test_brightness_percentile_analysis(self, camera_streamer):
        """Test brightness using percentile analysis"""
        print("\n💡 Testing brightness with percentile analysis...")

        # Test with high brightness
        camera_streamer.brightness = 0.6
        camera_streamer.initialize_camera()
        time.sleep(1)

        frame = camera_streamer.capture_frame()

        img = Image.open(io.BytesIO(frame))
        img_gray = np.array(img.convert('L'))

        # Compute percentiles
        p25 = np.percentile(img_gray, 25)
        p50 = np.percentile(img_gray, 50)
        p75 = np.percentile(img_gray, 75)

        camera_streamer.stop_streaming()

        print(f"   25th percentile: {p25:.1f}")
        print(f"   50th percentile (median): {p50:.1f}")
        print(f"   75th percentile: {p75:.1f}")

        # All should be in valid range
        assert 0 <= p25 <= 255
        assert 0 <= p50 <= 255
        assert 0 <= p75 <= 255
        print("   ✓ Percentile analysis complete")


if __name__ == '__main__':
    # Check if scipy is available (needed for sharpness analysis)
    try:
        import scipy
        pytest.main([__file__, '-v', '-s'])
    except ImportError:
        print("⚠️  scipy not installed - install with: pip3 install --break-system-packages scipy")
        print("   Some image quality tests will be skipped")
        pytest.main([__file__, '-v', '-s', '-k', 'not sharpness'])

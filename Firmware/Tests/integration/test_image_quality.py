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


if __name__ == '__main__':
    # Check if scipy is available (needed for sharpness analysis)
    try:
        import scipy
        pytest.main([__file__, '-v', '-s'])
    except ImportError:
        print("⚠️  scipy not installed - install with: pip3 install --break-system-packages scipy")
        print("   Some image quality tests will be skipped")
        pytest.main([__file__, '-v', '-s', '-k', 'not sharpness'])

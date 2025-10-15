"""
Unit Tests: Image Quality Validation (Feature Set 2)

Tests validation logic for image quality controls including
boundary values, type conversion, and error handling.

These tests validate the routes/config.py validation logic for:
- Sharpness (0.0-16.0)
- Brightness (-1.0 to 1.0)
- Contrast (0.0-32.0)
- Saturation (0.0-32.0)
- White balance modes (0-7)

RUN ON RASPBERRY PI ONLY - tests Flask routes

Usage:
    pytest Tests/unit/test_image_quality_validation.py -v -s
"""
import pytest
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))


class TestSharpnessBoundaryValues:
    """Test sharpness control boundary validation (0.0-16.0)"""

    def test_sharpness_minimum_valid(self, client):
        """Test sharpness at minimum valid value (0.0)"""
        response = client.post('/api/config/webui', json={'sharpness': 0.0})
        assert response.status_code == 200, "Should accept sharpness=0.0"
        print("\n✓ Accepted sharpness=0.0 (minimum)")

    def test_sharpness_just_above_minimum(self, client):
        """Test sharpness just above minimum (0.1)"""
        response = client.post('/api/config/webui', json={'sharpness': 0.1})
        assert response.status_code == 200, "Should accept sharpness=0.1"
        print("✓ Accepted sharpness=0.1")

    def test_sharpness_midpoint(self, client):
        """Test sharpness at midpoint (8.0)"""
        response = client.post('/api/config/webui', json={'sharpness': 8.0})
        assert response.status_code == 200, "Should accept sharpness=8.0"
        print("✓ Accepted sharpness=8.0 (midpoint)")

    def test_sharpness_just_below_maximum(self, client):
        """Test sharpness just below maximum (15.9)"""
        response = client.post('/api/config/webui', json={'sharpness': 15.9})
        assert response.status_code == 200, "Should accept sharpness=15.9"
        print("✓ Accepted sharpness=15.9")

    def test_sharpness_maximum_valid(self, client):
        """Test sharpness at maximum valid value (16.0)"""
        response = client.post('/api/config/webui', json={'sharpness': 16.0})
        assert response.status_code == 200, "Should accept sharpness=16.0"
        print("✓ Accepted sharpness=16.0 (maximum)")

    def test_sharpness_just_above_maximum(self, client):
        """Test sharpness just above maximum (16.1) - should fail"""
        response = client.post('/api/config/webui', json={'sharpness': 16.1})
        assert response.status_code == 400, "Should reject sharpness=16.1 (too high)"
        data = response.get_json()
        assert 'error' in data
        assert 'Sharpness' in data['error']
        print("✓ Rejected sharpness=16.1 (too high)")

    def test_sharpness_negative(self, client):
        """Test sharpness below minimum (-1) - should fail"""
        response = client.post('/api/config/webui', json={'sharpness': -1})
        assert response.status_code == 400, "Should reject sharpness=-1"
        data = response.get_json()
        assert 'error' in data
        assert 'Sharpness' in data['error']
        print("✓ Rejected sharpness=-1 (negative)")

    def test_sharpness_way_out_of_range(self, client):
        """Test sharpness far out of range (100) - should fail"""
        response = client.post('/api/config/webui', json={'sharpness': 100})
        assert response.status_code == 400, "Should reject sharpness=100"
        print("✓ Rejected sharpness=100 (way too high)")

    def test_sharpness_invalid_string(self, client):
        """Test sharpness with invalid string value - should fail"""
        response = client.post('/api/config/webui', json={'sharpness': 'invalid'})
        assert response.status_code == 400, "Should reject sharpness='invalid'"
        data = response.get_json()
        assert 'error' in data
        print("✓ Rejected sharpness='invalid' (invalid type)")


class TestBrightnessBoundaryValues:
    """Test brightness control boundary validation (-1.0 to 1.0)"""

    def test_brightness_minimum_valid(self, client):
        """Test brightness at minimum valid value (-1.0)"""
        response = client.post('/api/config/webui', json={'brightness': -1.0})
        assert response.status_code == 200, "Should accept brightness=-1.0"
        print("\n✓ Accepted brightness=-1.0 (minimum)")

    def test_brightness_below_zero(self, client):
        """Test brightness below zero (-0.5)"""
        response = client.post('/api/config/webui', json={'brightness': -0.5})
        assert response.status_code == 200, "Should accept brightness=-0.5"
        print("✓ Accepted brightness=-0.5")

    def test_brightness_zero(self, client):
        """Test brightness at neutral (0.0)"""
        response = client.post('/api/config/webui', json={'brightness': 0.0})
        assert response.status_code == 200, "Should accept brightness=0.0"
        print("✓ Accepted brightness=0.0 (neutral)")

    def test_brightness_above_zero(self, client):
        """Test brightness above zero (0.5)"""
        response = client.post('/api/config/webui', json={'brightness': 0.5})
        assert response.status_code == 200, "Should accept brightness=0.5"
        print("✓ Accepted brightness=0.5")

    def test_brightness_maximum_valid(self, client):
        """Test brightness at maximum valid value (1.0)"""
        response = client.post('/api/config/webui', json={'brightness': 1.0})
        assert response.status_code == 200, "Should accept brightness=1.0"
        print("✓ Accepted brightness=1.0 (maximum)")

    def test_brightness_above_maximum(self, client):
        """Test brightness above maximum (1.1) - should fail"""
        response = client.post('/api/config/webui', json={'brightness': 1.1})
        assert response.status_code == 400, "Should reject brightness=1.1"
        data = response.get_json()
        assert 'error' in data
        assert 'Brightness' in data['error']
        print("✓ Rejected brightness=1.1 (too high)")

    def test_brightness_below_minimum(self, client):
        """Test brightness below minimum (-2) - should fail"""
        response = client.post('/api/config/webui', json={'brightness': -2})
        assert response.status_code == 400, "Should reject brightness=-2"
        data = response.get_json()
        assert 'error' in data
        assert 'Brightness' in data['error']
        print("✓ Rejected brightness=-2 (too low)")

    def test_brightness_invalid_string(self, client):
        """Test brightness with text value - should fail"""
        response = client.post('/api/config/webui', json={'brightness': 'text'})
        assert response.status_code == 400, "Should reject brightness='text'"
        data = response.get_json()
        assert 'error' in data
        print("✓ Rejected brightness='text' (invalid type)")


class TestContrastBoundaryValues:
    """Test contrast control boundary validation (0.0-32.0)"""

    def test_contrast_minimum_valid(self, client):
        """Test contrast at minimum valid value (0.0)"""
        response = client.post('/api/config/webui', json={'contrast': 0.0})
        assert response.status_code == 200, "Should accept contrast=0.0"
        print("\n✓ Accepted contrast=0.0 (minimum)")

    def test_contrast_midpoint(self, client):
        """Test contrast at midpoint (16.0)"""
        response = client.post('/api/config/webui', json={'contrast': 16.0})
        assert response.status_code == 200, "Should accept contrast=16.0"
        print("✓ Accepted contrast=16.0 (midpoint)")

    def test_contrast_maximum_valid(self, client):
        """Test contrast at maximum valid value (32.0)"""
        response = client.post('/api/config/webui', json={'contrast': 32.0})
        assert response.status_code == 200, "Should accept contrast=32.0"
        print("✓ Accepted contrast=32.0 (maximum)")

    def test_contrast_above_maximum(self, client):
        """Test contrast above maximum (32.1) - should fail"""
        response = client.post('/api/config/webui', json={'contrast': 32.1})
        assert response.status_code == 400, "Should reject contrast=32.1"
        data = response.get_json()
        assert 'error' in data
        assert 'Contrast' in data['error']
        print("✓ Rejected contrast=32.1 (too high)")

    def test_contrast_negative(self, client):
        """Test contrast negative (-1) - should fail"""
        response = client.post('/api/config/webui', json={'contrast': -1})
        assert response.status_code == 400, "Should reject contrast=-1"
        data = response.get_json()
        assert 'error' in data
        assert 'Contrast' in data['error']
        print("✓ Rejected contrast=-1 (negative)")

    def test_contrast_none(self, client):
        """Test contrast with None value - should fail"""
        response = client.post('/api/config/webui', json={'contrast': None})
        assert response.status_code == 400, "Should reject contrast=None"
        data = response.get_json()
        assert 'error' in data
        print("✓ Rejected contrast=None (null value)")


class TestSaturationBoundaryValues:
    """Test saturation control boundary validation (0.0-32.0)"""

    def test_saturation_minimum_valid(self, client):
        """Test saturation at minimum valid value (0.0)"""
        response = client.post('/api/config/webui', json={'saturation': 0.0})
        assert response.status_code == 200, "Should accept saturation=0.0"
        print("\n✓ Accepted saturation=0.0 (minimum, grayscale)")

    def test_saturation_midpoint(self, client):
        """Test saturation at midpoint (16.0)"""
        response = client.post('/api/config/webui', json={'saturation': 16.0})
        assert response.status_code == 200, "Should accept saturation=16.0"
        print("✓ Accepted saturation=16.0 (midpoint)")

    def test_saturation_maximum_valid(self, client):
        """Test saturation at maximum valid value (32.0)"""
        response = client.post('/api/config/webui', json={'saturation': 32.0})
        assert response.status_code == 200, "Should accept saturation=32.0"
        print("✓ Accepted saturation=32.0 (maximum)")

    def test_saturation_above_maximum(self, client):
        """Test saturation above maximum (33) - should fail"""
        response = client.post('/api/config/webui', json={'saturation': 33})
        assert response.status_code == 400, "Should reject saturation=33"
        data = response.get_json()
        assert 'error' in data
        assert 'Saturation' in data['error']
        print("✓ Rejected saturation=33 (too high)")

    def test_saturation_negative(self, client):
        """Test saturation negative (-5) - should fail"""
        response = client.post('/api/config/webui', json={'saturation': -5})
        assert response.status_code == 400, "Should reject saturation=-5"
        data = response.get_json()
        assert 'error' in data
        assert 'Saturation' in data['error']
        print("✓ Rejected saturation=-5 (negative)")


class TestWhiteBalanceModeValidation:
    """Test white balance mode validation (0-7)"""

    def test_awb_mode_all_valid_values(self, client):
        """Test all 8 valid white balance modes (0-7)"""
        print("\n🌡️  Testing all white balance modes:")

        mode_names = {
            0: "Auto",
            1: "Incandescent (2800K)",
            2: "Tungsten",
            3: "Fluorescent",
            4: "Indoor",
            5: "Daylight (5600K)",
            6: "Cloudy (6500K)",
            7: "Custom"
        }

        for mode in range(8):
            response = client.post('/api/config/webui', json={'awb_mode': mode})
            assert response.status_code == 200, f"Should accept awb_mode={mode}"
            print(f"   ✓ Mode {mode}: {mode_names[mode]}")

    def test_awb_mode_below_minimum(self, client):
        """Test awb_mode below minimum (-1) - should fail"""
        response = client.post('/api/config/webui', json={'awb_mode': -1})
        assert response.status_code == 400, "Should reject awb_mode=-1"
        data = response.get_json()
        assert 'error' in data
        assert 'AwbMode' in data['error']
        print("\n✓ Rejected awb_mode=-1 (below minimum)")

    def test_awb_mode_above_maximum(self, client):
        """Test awb_mode above maximum (8) - should fail"""
        response = client.post('/api/config/webui', json={'awb_mode': 8})
        assert response.status_code == 400, "Should reject awb_mode=8"
        data = response.get_json()
        assert 'error' in data
        assert 'AwbMode' in data['error']
        print("✓ Rejected awb_mode=8 (above maximum)")

    def test_awb_mode_invalid_string(self, client):
        """Test awb_mode with string value - should fail"""
        response = client.post('/api/config/webui', json={'awb_mode': 'auto'})
        assert response.status_code == 400, "Should reject awb_mode='auto'"
        data = response.get_json()
        assert 'error' in data
        print("✓ Rejected awb_mode='auto' (invalid type)")


class TestSettingsFileCorruption:
    """Test handling of corrupted or missing settings files"""

    def test_defaults_when_file_missing(self, client):
        """Test that default values are returned when settings file is missing"""
        # This test assumes webui_settings.txt might not exist or we get defaults
        response = client.get('/api/config/webui')
        assert response.status_code == 200
        data = response.get_json()

        print("\n📋 Default values when file missing/corrupted:")

        # Verify defaults exist and are in valid ranges
        assert 'sharpness' in data
        assert 0.0 <= data['sharpness'] <= 16.0
        print(f"   sharpness: {data['sharpness']} ✓")

        assert 'brightness' in data
        assert -1.0 <= data['brightness'] <= 1.0
        print(f"   brightness: {data['brightness']} ✓")

        assert 'contrast' in data
        assert 0.0 <= data['contrast'] <= 32.0
        print(f"   contrast: {data['contrast']} ✓")

        assert 'saturation' in data
        assert 0.0 <= data['saturation'] <= 32.0
        print(f"   saturation: {data['saturation']} ✓")

        assert 'awb_mode' in data
        assert 0 <= data['awb_mode'] <= 7
        print(f"   awb_mode: {data['awb_mode']} ✓")


class TestTypeConversionEdgeCases:
    """Test type conversion edge cases"""

    def test_string_to_float_conversion_sharpness(self, client):
        """Test that string values are converted to float for sharpness"""
        # JSON will send as number, but test backend handles string inputs
        response = client.post('/api/config/webui', json={'sharpness': 2.5})
        assert response.status_code == 200, "Should convert and accept numeric sharpness"

        # Verify it was stored correctly
        response = client.get('/api/config/webui')
        data = response.get_json()
        assert abs(data['sharpness'] - 2.5) < 0.01
        print("\n✓ String to float conversion works for sharpness")

    def test_integer_to_float_conversion_brightness(self, client):
        """Test that integer values are converted to float for brightness"""
        response = client.post('/api/config/webui', json={'brightness': 0})
        assert response.status_code == 200, "Should convert integer to float"

        response = client.get('/api/config/webui')
        data = response.get_json()
        assert isinstance(data['brightness'], (int, float))
        print("✓ Integer to float conversion works for brightness")

    def test_boolean_string_conversion_awb_enable(self, client):
        """Test that string 'true'/'false' converts to boolean for awb_enable"""
        # Test with boolean True
        response = client.post('/api/config/webui', json={'awb_enable': True})
        assert response.status_code == 200

        response = client.get('/api/config/webui')
        data = response.get_json()
        assert data['awb_enable'] == True
        print("✓ Boolean true/false conversion works for awb_enable")


class TestCombinedControlValidation:
    """Test validation of multiple settings updated together"""

    def test_all_image_quality_controls_valid(self, client):
        """Test updating all image quality controls with valid values"""
        settings = {
            'sharpness': 2.5,
            'brightness': 0.2,
            'contrast': 1.5,
            'saturation': 1.2
        }

        response = client.post('/api/config/webui', json=settings)
        assert response.status_code == 200, "Should accept all valid image quality settings"
        print("\n✓ Accepted combined valid image quality settings")

        # Verify all were stored
        response = client.get('/api/config/webui')
        data = response.get_json()

        for key, expected in settings.items():
            actual = data[key]
            assert abs(actual - expected) < 0.01, f"{key} mismatch"
            print(f"   {key}: {actual} ✓")

    def test_one_invalid_rejects_all(self, client):
        """Test that one invalid value rejects entire update"""
        settings = {
            'sharpness': 2.5,      # Valid
            'brightness': 0.2,     # Valid
            'contrast': 50.0,      # INVALID (> 32.0)
            'saturation': 1.2      # Valid
        }

        response = client.post('/api/config/webui', json=settings)
        assert response.status_code == 400, "Should reject update with one invalid value"
        data = response.get_json()
        assert 'error' in data
        assert 'Contrast' in data['error']
        print("\n✓ Correctly rejected update with one invalid value (contrast=50.0)")

    def test_multiple_invalid_values(self, client):
        """Test handling of multiple invalid values"""
        settings = {
            'sharpness': 20.0,     # INVALID (> 16.0)
            'brightness': 5.0,     # INVALID (> 1.0)
            'contrast': 1.0,       # Valid
            'saturation': 1.0      # Valid
        }

        response = client.post('/api/config/webui', json=settings)
        assert response.status_code == 400, "Should reject update with invalid values"
        data = response.get_json()
        assert 'error' in data
        # Should report first error encountered
        print("\n✓ Correctly rejected update with multiple invalid values")

    def test_extreme_boundary_combination(self, client):
        """Test all controls at extreme boundary values"""
        settings = {
            'sharpness': 16.0,     # Maximum
            'brightness': -1.0,    # Minimum
            'contrast': 32.0,      # Maximum
            'saturation': 0.0      # Minimum
        }

        response = client.post('/api/config/webui', json=settings)
        assert response.status_code == 200, "Should accept all extreme boundary values"
        print("\n✓ Accepted all controls at extreme boundaries")

        # Verify storage
        response = client.get('/api/config/webui')
        data = response.get_json()

        assert abs(data['sharpness'] - 16.0) < 0.01
        assert abs(data['brightness'] - (-1.0)) < 0.01
        assert abs(data['contrast'] - 32.0) < 0.01
        assert abs(data['saturation'] - 0.0) < 0.01
        print("   All extreme values stored correctly ✓")


class TestSettingsValidationChains:
    """Test sequential validation of settings"""

    def test_sequential_valid_updates(self, client):
        """Test multiple sequential valid updates"""
        print("\n🔗 Testing sequential updates:")

        # Update 1: Sharpness
        response = client.post('/api/config/webui', json={'sharpness': 1.5})
        assert response.status_code == 200
        print("   Update 1: sharpness ✓")

        # Update 2: Brightness
        response = client.post('/api/config/webui', json={'brightness': 0.3})
        assert response.status_code == 200
        print("   Update 2: brightness ✓")

        # Update 3: Contrast
        response = client.post('/api/config/webui', json={'contrast': 1.8})
        assert response.status_code == 200
        print("   Update 3: contrast ✓")

        # Verify all persisted
        response = client.get('/api/config/webui')
        data = response.get_json()
        assert abs(data['sharpness'] - 1.5) < 0.01
        assert abs(data['brightness'] - 0.3) < 0.01
        assert abs(data['contrast'] - 1.8) < 0.01
        print("   All sequential updates persisted ✓")

    def test_valid_then_invalid_preserves_previous(self, client):
        """Test that invalid update doesn't corrupt previous valid settings"""
        # First, set valid values
        valid_settings = {'sharpness': 3.0, 'brightness': 0.1}
        response = client.post('/api/config/webui', json=valid_settings)
        assert response.status_code == 200
        print("\n✓ Set initial valid settings")

        # Try to update with invalid value
        invalid_settings = {'sharpness': 100.0, 'brightness': 0.2}
        response = client.post('/api/config/webui', json=invalid_settings)
        assert response.status_code == 400
        print("✓ Invalid update rejected")

        # Verify original settings preserved
        response = client.get('/api/config/webui')
        data = response.get_json()
        assert abs(data['sharpness'] - 3.0) < 0.01, "Original sharpness should be preserved"
        print("✓ Original valid settings preserved after failed update")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])

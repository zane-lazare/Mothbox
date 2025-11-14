"""
Unit Tests: Focus & Exposure Control Validation (Feature Set 3)

Tests validation logic for focus and exposure controls including:
- Focus mode validation (AfMode, AfSpeed, AfRange)
- Lens position bounds checking
- Exposure time and gain validation
- Type validation for all controls

These are unit tests that validate input ranges and types without
requiring actual camera hardware.

Run with: pytest Tests/unit/test_focus_control_validation.py -v
"""

import pytest
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))


class TestFocusModeValidation:
    """Test AfMode validation (0=Manual, 1=Single, 2=Continuous)"""

    def test_af_mode_valid_values(self):
        """Test AfMode accepts 0, 1, 2"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        validator = ALLOWED_CAMERA_SETTINGS['AfMode']

        # Valid modes
        assert validator(0) is True, "Should accept AfMode=0 (Manual)"
        assert validator(1) is True, "Should accept AfMode=1 (Single)"
        assert validator(2) is True, "Should accept AfMode=2 (Continuous)"
        print("\n✓ AfMode accepts valid values: 0 (Manual), 1 (Single), 2 (Continuous)")

    def test_af_mode_invalid_values(self):
        """Test AfMode rejects invalid values"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        validator = ALLOWED_CAMERA_SETTINGS['AfMode']

        # Invalid modes
        assert validator(-1) is False, "Should reject AfMode=-1"
        assert validator(3) is False, "Should reject AfMode=3"
        assert validator(10) is False, "Should reject AfMode=10"
        print("\n✓ AfMode rejects invalid values: -1, 3, 10")

    def test_af_mode_type_validation(self):
        """Test AfMode rejects non-integer types"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        validator = ALLOWED_CAMERA_SETTINGS['AfMode']

        # Type validation
        with pytest.raises((ValueError, TypeError)):
            validator("auto")
        with pytest.raises((ValueError, TypeError)):
            validator(1.5)
        with pytest.raises((ValueError, TypeError)):
            validator(None)
        print("\n✓ AfMode rejects non-integer types")


class TestAfSpeedValidation:
    """Test AfSpeed validation (0=Normal, 1=Fast)"""

    def test_af_speed_valid_values(self):
        """Test AfSpeed accepts 0 and 1"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        validator = ALLOWED_CAMERA_SETTINGS['AfSpeed']

        assert validator(0) is True, "Should accept AfSpeed=0 (Normal)"
        assert validator(1) is True, "Should accept AfSpeed=1 (Fast)"
        print("\n✓ AfSpeed accepts valid values: 0 (Normal), 1 (Fast)")

    def test_af_speed_invalid_values(self):
        """Test AfSpeed rejects invalid values"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        validator = ALLOWED_CAMERA_SETTINGS['AfSpeed']

        assert validator(-1) is False, "Should reject AfSpeed=-1"
        assert validator(2) is False, "Should reject AfSpeed=2"
        assert validator(10) is False, "Should reject AfSpeed=10"
        print("\n✓ AfSpeed rejects invalid values: -1, 2, 10")


class TestAfRangeValidation:
    """Test AfRange validation (0=Normal, 1=Macro, 2=Full)"""

    def test_af_range_valid_values(self):
        """Test AfRange accepts 0, 1, 2"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        validator = ALLOWED_CAMERA_SETTINGS['AfRange']

        assert validator(0) is True, "Should accept AfRange=0 (Normal)"
        assert validator(1) is True, "Should accept AfRange=1 (Macro)"
        assert validator(2) is True, "Should accept AfRange=2 (Full)"
        print("\n✓ AfRange accepts valid values: 0 (Normal), 1 (Macro), 2 (Full)")

    def test_af_range_invalid_values(self):
        """Test AfRange rejects invalid values"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        validator = ALLOWED_CAMERA_SETTINGS['AfRange']

        assert validator(-1) is False, "Should reject AfRange=-1"
        assert validator(3) is False, "Should reject AfRange=3"
        assert validator(10) is False, "Should reject AfRange=10"
        print("\n✓ AfRange rejects invalid values: -1, 3, 10")


class TestLensPositionValidation:
    """Test LensPosition bounds (0-10 diopters)"""

    def test_lens_position_valid_range(self):
        """Test LensPosition accepts 0.0 to 10.0 diopters"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        validator = ALLOWED_CAMERA_SETTINGS['LensPosition']

        # Boundary values
        assert validator(0.0) is True, "Should accept LensPosition=0.0"
        assert validator(10.0) is True, "Should accept LensPosition=10.0"

        # Mid-range values
        assert validator(5.0) is True, "Should accept LensPosition=5.0"
        assert validator(7.5) is True, "Should accept LensPosition=7.5"
        assert validator(0.1) is True, "Should accept LensPosition=0.1"
        assert validator(9.9) is True, "Should accept LensPosition=9.9"
        print("\n✓ LensPosition accepts 0.0-10.0 diopters")

    def test_lens_position_out_of_bounds(self):
        """Test LensPosition rejects out-of-bounds values"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        validator = ALLOWED_CAMERA_SETTINGS['LensPosition']

        # Too low
        assert validator(-0.1) is False, "Should reject LensPosition=-0.1"
        assert validator(-1.0) is False, "Should reject LensPosition=-1.0"

        # Too high
        assert validator(10.1) is False, "Should reject LensPosition=10.1"
        assert validator(15.0) is False, "Should reject LensPosition=15.0"
        assert validator(100.0) is False, "Should reject LensPosition=100.0"
        print("\n✓ LensPosition rejects out-of-bounds values")

    def test_lens_position_edge_cases(self):
        """Test LensPosition edge cases"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        validator = ALLOWED_CAMERA_SETTINGS['LensPosition']

        # Edge cases at boundaries
        assert validator(0.0) is True, "Exactly 0.0 should be valid"
        assert validator(10.0) is True, "Exactly 10.0 should be valid"

        # Just outside boundaries
        assert validator(-0.01) is False, "Just below 0.0 should be invalid"
        assert validator(10.01) is False, "Just above 10.0 should be invalid"
        print("\n✓ LensPosition edge cases validated")


class TestExposureTimeValidation:
    """Test ExposureTime bounds (microseconds)"""

    def test_exposure_time_valid_range(self):
        """Test ExposureTime accepts valid microsecond values"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        validator = ALLOWED_CAMERA_SETTINGS['ExposureTime']

        # Valid values
        assert validator(100) is True, "Should accept ExposureTime=100µs"
        assert validator(1000) is True, "Should accept ExposureTime=1000µs"
        assert validator(10000) is True, "Should accept ExposureTime=10000µs"
        assert validator(100000) is True, "Should accept ExposureTime=100000µs"
        assert validator(999999) is True, "Should accept ExposureTime=999999µs"
        print("\n✓ ExposureTime accepts valid microsecond values")

    def test_exposure_time_boundary_values(self):
        """Test ExposureTime boundary validation"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        validator = ALLOWED_CAMERA_SETTINGS['ExposureTime']

        # Near upper boundary (< 1000000µs = 1 second)
        assert validator(999999) is True, "Should accept 999999µs"
        assert validator(1000000) is False, "Should reject 1000000µs (>= 1s)"
        assert validator(1000001) is False, "Should reject 1000001µs"

        # Lower boundary (must be positive)
        assert validator(1) is True, "Should accept 1µs"
        assert validator(0) is False, "Should reject 0µs"
        assert validator(-100) is False, "Should reject negative values"
        print("\n✓ ExposureTime boundary values validated")

    def test_exposure_time_type_validation(self):
        """Test ExposureTime requires integer type"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        validator = ALLOWED_CAMERA_SETTINGS['ExposureTime']

        # Type validation - must be digit string or int
        # The validator checks str(v).isdigit()
        assert validator("1000") is True, "Should accept string digits"
        assert validator(1000) is True, "Should accept integer"

        # Invalid types
        with pytest.raises((ValueError, TypeError, AttributeError)):
            validator(None)
        print("\n✓ ExposureTime type validation works")


class TestAnalogueGainValidation:
    """Test AnalogueGain bounds (1.0-16.0)"""

    def test_analogue_gain_valid_range(self):
        """Test AnalogueGain accepts 1.0 to 16.0"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        validator = ALLOWED_CAMERA_SETTINGS['AnalogueGain']

        # Boundary values
        assert validator(1.0) is True, "Should accept AnalogueGain=1.0"
        assert validator(16.0) is True, "Should accept AnalogueGain=16.0"

        # Mid-range values
        assert validator(1.1) is True, "Should accept AnalogueGain=1.1"
        assert validator(2.5) is True, "Should accept AnalogueGain=2.5"
        assert validator(8.0) is True, "Should accept AnalogueGain=8.0"
        assert validator(15.9) is True, "Should accept AnalogueGain=15.9"
        print("\n✓ AnalogueGain accepts 1.0-16.0")

    def test_analogue_gain_out_of_bounds(self):
        """Test AnalogueGain rejects out-of-bounds values"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        validator = ALLOWED_CAMERA_SETTINGS['AnalogueGain']

        # Too low
        assert validator(0.9) is False, "Should reject AnalogueGain=0.9"
        assert validator(0.0) is False, "Should reject AnalogueGain=0.0"
        assert validator(-1.0) is False, "Should reject AnalogueGain=-1.0"

        # Too high
        assert validator(16.1) is False, "Should reject AnalogueGain=16.1"
        assert validator(20.0) is False, "Should reject AnalogueGain=20.0"
        assert validator(100.0) is False, "Should reject AnalogueGain=100.0"
        print("\n✓ AnalogueGain rejects out-of-bounds values")

    def test_analogue_gain_edge_cases(self):
        """Test AnalogueGain edge cases"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        validator = ALLOWED_CAMERA_SETTINGS['AnalogueGain']

        # Edge cases at boundaries
        assert validator(1.0) is True, "Exactly 1.0 should be valid"
        assert validator(16.0) is True, "Exactly 16.0 should be valid"

        # Just outside boundaries
        assert validator(0.99) is False, "Just below 1.0 should be invalid"
        assert validator(16.01) is False, "Just above 16.0 should be invalid"
        print("\n✓ AnalogueGain edge cases validated")


class TestFocusModeCombinations:
    """Test focus mode combinations with other settings"""

    def test_manual_focus_requires_lens_position(self):
        """Test Manual focus (AfMode=0) requires valid LensPosition"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        af_mode_validator = ALLOWED_CAMERA_SETTINGS['AfMode']
        lens_pos_validator = ALLOWED_CAMERA_SETTINGS['LensPosition']

        # Manual mode (0) should allow any valid lens position
        assert af_mode_validator(0) is True
        assert lens_pos_validator(5.0) is True
        assert lens_pos_validator(10.0) is True
        print("\n✓ Manual focus works with valid LensPosition")

    def test_auto_focus_modes_with_speed_range(self):
        """Test auto focus modes work with AfSpeed and AfRange"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        af_mode = ALLOWED_CAMERA_SETTINGS['AfMode']
        af_speed = ALLOWED_CAMERA_SETTINGS['AfSpeed']
        af_range = ALLOWED_CAMERA_SETTINGS['AfRange']

        # Single AF (1) with all speeds and ranges
        assert af_mode(1) is True
        assert af_speed(0) is True  # Normal speed
        assert af_speed(1) is True  # Fast speed
        assert af_range(0) is True  # Normal range
        assert af_range(1) is True  # Macro range
        assert af_range(2) is True  # Full range

        # Continuous AF (2) with all speeds and ranges
        assert af_mode(2) is True
        assert af_speed(0) is True
        assert af_speed(1) is True
        assert af_range(0) is True
        assert af_range(1) is True
        assert af_range(2) is True
        print("\n✓ Auto focus modes compatible with AfSpeed and AfRange")


class TestInvalidFocusModeCombinations:
    """Test invalid focus mode combinations"""

    def test_invalid_af_mode_with_valid_settings(self):
        """Test invalid AfMode fails even with valid other settings"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        af_mode = ALLOWED_CAMERA_SETTINGS['AfMode']
        af_speed = ALLOWED_CAMERA_SETTINGS['AfSpeed']
        af_range = ALLOWED_CAMERA_SETTINGS['AfRange']

        # Invalid AfMode should fail regardless of valid speed/range
        assert af_mode(99) is False
        assert af_speed(0) is True  # Valid speed doesn't fix invalid mode
        assert af_range(0) is True  # Valid range doesn't fix invalid mode
        print("\n✓ Invalid AfMode fails regardless of other valid settings")

    def test_valid_af_mode_with_invalid_settings(self):
        """Test valid AfMode with invalid speed/range fails"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        af_mode = ALLOWED_CAMERA_SETTINGS['AfMode']
        af_speed = ALLOWED_CAMERA_SETTINGS['AfSpeed']
        af_range = ALLOWED_CAMERA_SETTINGS['AfRange']

        # Valid mode doesn't fix invalid speed/range
        assert af_mode(1) is True
        assert af_speed(99) is False  # Invalid speed
        assert af_range(99) is False  # Invalid range
        print("\n✓ Valid AfMode doesn't validate invalid speed/range")


class TestExposureControlCombinations:
    """Test exposure control combinations"""

    def test_valid_exposure_and_gain_combination(self):
        """Test valid ExposureTime and AnalogueGain combination"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        exposure = ALLOWED_CAMERA_SETTINGS['ExposureTime']
        gain = ALLOWED_CAMERA_SETTINGS['AnalogueGain']

        # Valid combinations
        assert exposure(10000) is True
        assert gain(2.0) is True
        print("\n✓ Valid exposure/gain combinations accepted")

    def test_extreme_exposure_and_gain_values(self):
        """Test extreme but valid exposure/gain values"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        exposure = ALLOWED_CAMERA_SETTINGS['ExposureTime']
        gain = ALLOWED_CAMERA_SETTINGS['AnalogueGain']

        # Low exposure, high gain
        assert exposure(100) is True
        assert gain(16.0) is True

        # High exposure, low gain
        assert exposure(999999) is True
        assert gain(1.0) is True
        print("\n✓ Extreme exposure/gain combinations validated")


class TestAllControlsValidation:
    """Test validation for all focus and exposure controls together"""

    def test_complete_focus_settings_valid(self):
        """Test complete set of valid focus settings"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        # Complete valid focus configuration
        settings = {
            'AfMode': 1,
            'AfSpeed': 0,
            'AfRange': 2,
            'LensPosition': 7.5,
        }

        for key, value in settings.items():
            validator = ALLOWED_CAMERA_SETTINGS[key]
            assert validator(value) is True, f"{key}={value} should be valid"
        print("\n✓ Complete focus settings validated")

    def test_complete_exposure_settings_valid(self):
        """Test complete set of valid exposure settings"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        # Complete valid exposure configuration
        settings = {
            'ExposureTime': 10000,
            'AnalogueGain': 2.5,
        }

        for key, value in settings.items():
            validator = ALLOWED_CAMERA_SETTINGS[key]
            assert validator(value) is True, f"{key}={value} should be valid"
        print("\n✓ Complete exposure settings validated")

    def test_complete_focus_and_exposure_valid(self):
        """Test complete set of valid focus + exposure settings"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        # Complete valid configuration
        settings = {
            'AfMode': 0,
            'AfSpeed': 0,
            'AfRange': 0,
            'LensPosition': 5.0,
            'ExposureTime': 50000,
            'AnalogueGain': 4.0,
        }

        for key, value in settings.items():
            validator = ALLOWED_CAMERA_SETTINGS[key]
            assert validator(value) is True, f"{key}={value} should be valid"
        print("\n✓ Complete focus + exposure settings validated")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])

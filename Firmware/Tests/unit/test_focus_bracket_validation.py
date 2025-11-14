import os
os.environ['MOTHBOX_ENV'] = 'development'  # Must be set before importing config

"""
Unit tests for Focus Bracket settings validation

Tests the validation logic for FocusBracket, FocusBracket_Start, and FocusBracket_End settings
in webui/backend/routes/camera.py
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add webui backend to path
FIRMWARE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(FIRMWARE_DIR / "webui" / "backend"))


@pytest.fixture(scope="module", autouse=True)
def mock_hardware_dependencies():
    """
    Mock hardware dependencies for focus bracket validation tests.

    This fixture ensures hardware modules are mocked at module scope with proper
    cleanup to prevent sys.modules pollution across test files.

    IMPORTANT: Never mock at module level! Module-level mocking pollutes sys.modules
    across test files and breaks tests that need real modules.
    """
    # Save original state
    original_modules = {}
    modules_to_mock = ['cv2', 'picamera2', 'picamera2.picamera2', 'RPi', 'RPi.GPIO',
                       'PIL', 'PIL.Image', 'libcamera', 'libcamera.controls']

    for module_name in modules_to_mock:
        if module_name in sys.modules:
            original_modules[module_name] = sys.modules[module_name]
        sys.modules[module_name] = MagicMock()

    yield

    # Restore original state
    for module_name in modules_to_mock:
        if module_name in original_modules:
            sys.modules[module_name] = original_modules[module_name]
        elif module_name in sys.modules:
            del sys.modules[module_name]

from routes.camera import ALLOWED_CAMERA_SETTINGS


class TestFocusBracketValidation:
    """Test focus bracketing settings validation"""

    def test_focus_bracket_steps_valid(self):
        """Test valid FocusBracket step counts"""
        validator = ALLOWED_CAMERA_SETTINGS['FocusBracket']

        # Valid values (1-10)
        assert validator(1) == True
        assert validator(3) == True
        assert validator(5) == True
        assert validator(7) == True
        assert validator(10) == True
        assert validator('5') == True  # String should work too

    def test_focus_bracket_steps_invalid(self):
        """Test invalid FocusBracket step counts"""
        validator = ALLOWED_CAMERA_SETTINGS['FocusBracket']

        # Out of range
        assert validator(0) == False
        assert validator(-1) == False
        assert validator(11) == False
        assert validator(100) == False

    def test_focus_bracket_start_valid(self):
        """Test valid FocusBracket_Start positions"""
        validator = ALLOWED_CAMERA_SETTINGS['FocusBracket_Start']

        # Valid diopter values (0.0-10.0)
        assert validator(0.0) == True
        assert validator(2.0) == True
        assert validator(5.0) == True
        assert validator(8.0) == True
        assert validator(10.0) == True
        assert validator('5.5') == True  # String should work too

    def test_focus_bracket_start_invalid(self):
        """Test invalid FocusBracket_Start positions"""
        validator = ALLOWED_CAMERA_SETTINGS['FocusBracket_Start']

        # Out of range
        assert validator(-0.1) == False
        assert validator(-1.0) == False
        assert validator(10.1) == False
        assert validator(15.0) == False

    def test_focus_bracket_end_valid(self):
        """Test valid FocusBracket_End positions"""
        validator = ALLOWED_CAMERA_SETTINGS['FocusBracket_End']

        # Valid diopter values (0.0-10.0)
        assert validator(0.0) == True
        assert validator(2.0) == True
        assert validator(5.0) == True
        assert validator(8.0) == True
        assert validator(10.0) == True
        assert validator('7.5') == True  # String should work too

    def test_focus_bracket_end_invalid(self):
        """Test invalid FocusBracket_End positions"""
        validator = ALLOWED_CAMERA_SETTINGS['FocusBracket_End']

        # Out of range
        assert validator(-0.1) == False
        assert validator(-1.0) == False
        assert validator(10.1) == False
        assert validator(20.0) == False

    def test_focus_bracket_edge_cases(self):
        """Test edge cases for focus bracket validation"""
        steps_validator = ALLOWED_CAMERA_SETTINGS['FocusBracket']
        start_validator = ALLOWED_CAMERA_SETTINGS['FocusBracket_Start']
        end_validator = ALLOWED_CAMERA_SETTINGS['FocusBracket_End']

        # Boundary values
        assert steps_validator(1) == True   # Minimum
        assert steps_validator(10) == True  # Maximum
        assert start_validator(0.0) == True  # Minimum
        assert start_validator(10.0) == True # Maximum
        assert end_validator(0.0) == True    # Minimum
        assert end_validator(10.0) == True   # Maximum

    def test_focus_bracket_type_conversion(self):
        """Test that validators handle type conversion correctly"""
        steps_validator = ALLOWED_CAMERA_SETTINGS['FocusBracket']
        start_validator = ALLOWED_CAMERA_SETTINGS['FocusBracket_Start']
        end_validator = ALLOWED_CAMERA_SETTINGS['FocusBracket_End']

        # Should accept strings that can be converted
        assert steps_validator('5') == True
        assert start_validator('2.0') == True
        assert end_validator('8.0') == True

        # Should reject invalid types
        with pytest.raises((ValueError, TypeError)):
            steps_validator('invalid')

        with pytest.raises((ValueError, TypeError)):
            start_validator('not_a_number')

        with pytest.raises((ValueError, TypeError)):
            end_validator('abc')


class TestCalculateFocusPositions:
    """Test calculate_focus_positions() helper function"""

    def test_single_step_returns_start_only(self):
        """Test that single step returns only the start position"""
        from scripts.capture_focus_bracket import calculate_focus_positions

        positions = calculate_focus_positions(5.0, 8.0, 1)
        assert len(positions) == 1
        assert positions[0] == 5.0

    def test_evenly_spaced_positions(self):
        """Test that positions are evenly spaced"""
        from scripts.capture_focus_bracket import calculate_focus_positions

        positions = calculate_focus_positions(2.0, 8.0, 5)

        assert len(positions) == 5
        assert positions[0] == 2.0
        assert positions[-1] == 8.0

        # Check spacing is consistent
        expected_spacing = (8.0 - 2.0) / (5 - 1)  # = 1.5
        for i in range(len(positions) - 1):
            actual_spacing = positions[i + 1] - positions[i]
            assert abs(actual_spacing - expected_spacing) < 0.001

    def test_three_steps_correct_positions(self):
        """Test specific positions for 3-step bracket"""
        from scripts.capture_focus_bracket import calculate_focus_positions

        positions = calculate_focus_positions(0.0, 10.0, 3)

        assert len(positions) == 3
        assert positions[0] == 0.0
        assert positions[1] == 5.0
        assert positions[2] == 10.0

    def test_reverse_range(self):
        """Test that reverse range (start > end) works correctly"""
        from scripts.capture_focus_bracket import calculate_focus_positions

        positions = calculate_focus_positions(8.0, 2.0, 4)

        assert len(positions) == 4
        assert positions[0] == 8.0
        assert positions[-1] == 2.0

        # Positions should decrease
        for i in range(len(positions) - 1):
            assert positions[i] > positions[i + 1]

    def test_input_validation_raises_error_steps_out_of_range(self):
        """Test that invalid step count raises ValueError"""
        from scripts.capture_focus_bracket import calculate_focus_positions

        with pytest.raises(ValueError, match="Steps must be an integer between 1 and 10"):
            calculate_focus_positions(2.0, 8.0, 0)

        with pytest.raises(ValueError, match="Steps must be an integer between 1 and 10"):
            calculate_focus_positions(2.0, 8.0, 11)

        with pytest.raises(ValueError, match="Steps must be an integer between 1 and 10"):
            calculate_focus_positions(2.0, 8.0, -1)

    def test_input_validation_raises_error_start_out_of_range(self):
        """Test that invalid start position raises ValueError"""
        from scripts.capture_focus_bracket import calculate_focus_positions

        with pytest.raises(ValueError, match="Start position must be 0.0-10.0 diopters"):
            calculate_focus_positions(-0.5, 8.0, 5)

        with pytest.raises(ValueError, match="Start position must be 0.0-10.0 diopters"):
            calculate_focus_positions(10.5, 8.0, 5)

    def test_input_validation_raises_error_end_out_of_range(self):
        """Test that invalid end position raises ValueError"""
        from scripts.capture_focus_bracket import calculate_focus_positions

        with pytest.raises(ValueError, match="End position must be 0.0-10.0 diopters"):
            calculate_focus_positions(2.0, -1.0, 5)

        with pytest.raises(ValueError, match="End position must be 0.0-10.0 diopters"):
            calculate_focus_positions(2.0, 11.0, 5)

    def test_boundary_values(self):
        """Test boundary values for diopters (0 and 10)"""
        from scripts.capture_focus_bracket import calculate_focus_positions

        # Test 0 to 10 range
        positions = calculate_focus_positions(0.0, 10.0, 5)
        assert positions[0] == 0.0
        assert positions[-1] == 10.0

        # Test single position at boundary
        positions = calculate_focus_positions(0.0, 10.0, 1)
        assert positions[0] == 0.0

        positions = calculate_focus_positions(10.0, 0.0, 1)
        assert positions[0] == 10.0


class TestFlashTimingValidation:
    """Test flash timing settings validation"""

    def test_flash_delay_before_valid(self):
        """Test valid FlashDelay_BeforeCapture values"""
        validator = ALLOWED_CAMERA_SETTINGS['FlashDelay_BeforeCapture']

        assert validator(0) == True
        assert validator(50) == True
        assert validator(250) == True
        assert validator(500) == True
        assert validator('100') == True

    def test_flash_delay_before_invalid(self):
        """Test invalid FlashDelay_BeforeCapture values"""
        validator = ALLOWED_CAMERA_SETTINGS['FlashDelay_BeforeCapture']

        assert validator(-1) == False
        assert validator(501) == False
        assert validator(1000) == False

    def test_flash_delay_after_valid(self):
        """Test valid FlashDelay_AfterCapture values"""
        validator = ALLOWED_CAMERA_SETTINGS['FlashDelay_AfterCapture']

        assert validator(0) == True
        assert validator(100) == True
        assert validator(500) == True
        assert validator('250') == True

    def test_flash_delay_after_invalid(self):
        """Test invalid FlashDelay_AfterCapture values"""
        validator = ALLOWED_CAMERA_SETTINGS['FlashDelay_AfterCapture']

        assert validator(-1) == False
        assert validator(501) == False

    def test_settle_delay_valid(self):
        """Test valid FocusBracket_SettleDelay values"""
        validator = ALLOWED_CAMERA_SETTINGS['FocusBracket_SettleDelay']

        assert validator(100) == True
        assert validator(500) == True
        assert validator(1000) == True
        assert validator(2000) == True
        assert validator('750') == True

    def test_settle_delay_invalid(self):
        """Test invalid FocusBracket_SettleDelay values"""
        validator = ALLOWED_CAMERA_SETTINGS['FocusBracket_SettleDelay']

        assert validator(99) == False
        assert validator(0) == False
        assert validator(2001) == False
        assert validator(5000) == False


class TestColorGainsValidation:
    """Test color gains settings validation"""

    def test_lock_color_gains_valid(self):
        """Test valid FocusBracket_LockColorGains values"""
        validator = ALLOWED_CAMERA_SETTINGS['FocusBracket_LockColorGains']

        assert validator(0) == True
        assert validator(1) == True
        assert validator('0') == True
        assert validator('1') == True

    def test_lock_color_gains_invalid(self):
        """Test invalid FocusBracket_LockColorGains values"""
        validator = ALLOWED_CAMERA_SETTINGS['FocusBracket_LockColorGains']

        assert validator(2) == False
        assert validator(-1) == False
        assert validator(10) == False

    def test_color_gain_red_valid(self):
        """Test valid FocusBracket_ColorGainRed values"""
        validator = ALLOWED_CAMERA_SETTINGS['FocusBracket_ColorGainRed']

        assert validator(1.0) == True
        assert validator(2.0) == True
        assert validator(2.259) == True
        assert validator(4.0) == True
        assert validator('3.5') == True

    def test_color_gain_red_invalid(self):
        """Test invalid FocusBracket_ColorGainRed values"""
        validator = ALLOWED_CAMERA_SETTINGS['FocusBracket_ColorGainRed']

        assert validator(0.9) == False
        assert validator(4.1) == False
        assert validator(10.0) == False

    def test_color_gain_blue_valid(self):
        """Test valid FocusBracket_ColorGainBlue values"""
        validator = ALLOWED_CAMERA_SETTINGS['FocusBracket_ColorGainBlue']

        assert validator(1.0) == True
        assert validator(1.5) == True
        assert validator(2.0) == True
        assert validator(4.0) == True
        assert validator('2.5') == True

    def test_color_gain_blue_invalid(self):
        """Test invalid FocusBracket_ColorGainBlue values"""
        validator = ALLOWED_CAMERA_SETTINGS['FocusBracket_ColorGainBlue']

        assert validator(0.5) == False
        assert validator(4.5) == False
        assert validator(0.0) == False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

"""
import os
os.environ['MOTHBOX_ENV'] = 'development'  # Must be set before importing config

Unit tests for Focus Bracket settings validation

Tests the validation logic for FocusBracket, FocusBracket_Start, and FocusBracket_End settings
in webui/backend/routes/camera.py
"""

import pytest
import sys
from pathlib import Path

# Add webui backend to path
FIRMWARE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(FIRMWARE_DIR / "webui" / "backend"))

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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

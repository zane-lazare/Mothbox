"""
import os
os.environ['MOTHBOX_ENV'] = 'development'  # Must be set before importing config

Unit tests for AeMeteringMode validation

Tests that AeMeteringMode values are properly validated in camera.py
"""
import pytest
import sys
from pathlib import Path

# Add webui/backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))

from routes.camera import ALLOWED_CAMERA_SETTINGS


class TestMeteringValidation:
    """Test AeMeteringMode validation function"""

    def test_metering_mode_validation_exists(self):
        """AeMeteringMode should exist in ALLOWED_CAMERA_SETTINGS"""
        assert 'AeMeteringMode' in ALLOWED_CAMERA_SETTINGS, \
            "AeMeteringMode not found in ALLOWED_CAMERA_SETTINGS"

    def test_metering_mode_centre_weighted(self):
        """AeMeteringMode should accept 0 (Centre-Weighted)"""
        validator = ALLOWED_CAMERA_SETTINGS['AeMeteringMode']
        assert validator(0) is True, "Centre-Weighted mode (0) should be valid"
        assert validator('0') is True, "Centre-Weighted mode ('0') should be valid"

    def test_metering_mode_spot(self):
        """AeMeteringMode should accept 1 (Spot)"""
        validator = ALLOWED_CAMERA_SETTINGS['AeMeteringMode']
        assert validator(1) is True, "Spot mode (1) should be valid"
        assert validator('1') is True, "Spot mode ('1') should be valid"

    def test_metering_mode_matrix(self):
        """AeMeteringMode should accept 2 (Matrix/Average)"""
        validator = ALLOWED_CAMERA_SETTINGS['AeMeteringMode']
        assert validator(2) is True, "Matrix mode (2) should be valid"
        assert validator('2') is True, "Matrix mode ('2') should be valid"

    def test_metering_mode_rejects_invalid_values(self):
        """AeMeteringMode should reject values outside 0-2 range"""
        validator = ALLOWED_CAMERA_SETTINGS['AeMeteringMode']

        # Test negative values
        assert validator(-1) is False, "Negative values should be rejected"

        # Test values above 2
        assert validator(3) is False, "Value 3 should be rejected"
        assert validator(10) is False, "Value 10 should be rejected"

        # Test non-numeric strings
        with pytest.raises((ValueError, TypeError)):
            validator('invalid')

        # Test None
        with pytest.raises((ValueError, TypeError)):
            validator(None)

    def test_metering_mode_validator_type(self):
        """AeMeteringMode validator should be callable"""
        validator = ALLOWED_CAMERA_SETTINGS['AeMeteringMode']
        assert callable(validator), "Validator should be a callable function"

    def test_metering_mode_all_valid_modes(self):
        """Test all valid metering modes in a loop"""
        validator = ALLOWED_CAMERA_SETTINGS['AeMeteringMode']
        valid_modes = [0, 1, 2]

        for mode in valid_modes:
            assert validator(mode) is True, \
                f"Metering mode {mode} should be valid"

    def test_metering_mode_boundary_values(self):
        """Test boundary values around valid range"""
        validator = ALLOWED_CAMERA_SETTINGS['AeMeteringMode']

        # Just below valid range
        assert validator(-1) is False, "Value -1 should be rejected"

        # Lower boundary
        assert validator(0) is True, "Value 0 should be valid"

        # Upper boundary
        assert validator(2) is True, "Value 2 should be valid"

        # Just above valid range
        assert validator(3) is False, "Value 3 should be rejected"

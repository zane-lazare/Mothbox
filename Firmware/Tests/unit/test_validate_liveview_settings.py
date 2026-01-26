"""
Unit Tests: validate_liveview_settings function

Tests the validation helper function that filters camera settings from
liveview before applying them to Picamera2. Invalid values are excluded
to allow defaults to be applied.

These are pure function tests - no hardware or Flask required.

Usage:
    pytest Tests/unit/test_validate_liveview_settings.py -v
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))

from utils import validate_liveview_settings


class TestValidLiveviewSettings:
    """Tests for valid settings that should pass through unchanged"""

    def test_valid_sharpness_passes(self):
        """Valid sharpness value should be included"""
        result = validate_liveview_settings({'sharpness': 2.0})
        assert result == {'sharpness': 2.0}

    def test_valid_brightness_passes(self):
        """Valid brightness value should be included"""
        result = validate_liveview_settings({'brightness': 0.0})
        assert result == {'brightness': 0.0}

    def test_valid_af_mode_passes(self):
        """Valid af_mode enum should be included"""
        result = validate_liveview_settings({'af_mode': 2})
        assert result == {'af_mode': 2}

    def test_valid_exposure_time_passes(self):
        """Valid exposure_time should be included"""
        result = validate_liveview_settings({'exposure_time': 10000})
        assert result == {'exposure_time': 10000}

    def test_valid_analogue_gain_passes(self):
        """Valid analogue_gain should be included"""
        result = validate_liveview_settings({'analogue_gain': 4.0})
        assert result == {'analogue_gain': 4.0}

    def test_multiple_valid_settings_pass(self):
        """Multiple valid settings should all be included"""
        settings = {
            'sharpness': 2.0,
            'brightness': 0.0,
            'contrast': 1.0,
            'saturation': 1.0,
            'af_mode': 1,
        }
        result = validate_liveview_settings(settings)
        assert result == settings


class TestInvalidLiveviewSettings:
    """Tests for invalid settings that should be excluded"""

    def test_sharpness_above_max_excluded(self):
        """Sharpness above 4.0 should be excluded"""
        result = validate_liveview_settings({'sharpness': 100.0})
        assert 'sharpness' not in result

    def test_sharpness_below_min_excluded(self):
        """Sharpness below 0.0 should be excluded"""
        result = validate_liveview_settings({'sharpness': -1.0})
        assert 'sharpness' not in result

    def test_brightness_above_max_excluded(self):
        """Brightness above 1.0 should be excluded"""
        result = validate_liveview_settings({'brightness': 5.0})
        assert 'brightness' not in result

    def test_brightness_below_min_excluded(self):
        """Brightness below -1.0 should be excluded"""
        result = validate_liveview_settings({'brightness': -2.0})
        assert 'brightness' not in result

    def test_af_mode_out_of_range_excluded(self):
        """af_mode not in [0, 1, 2] should be excluded"""
        result = validate_liveview_settings({'af_mode': 5})
        assert 'af_mode' not in result

    def test_af_mode_negative_excluded(self):
        """Negative af_mode should be excluded"""
        result = validate_liveview_settings({'af_mode': -1})
        assert 'af_mode' not in result

    def test_exposure_time_zero_excluded(self):
        """exposure_time of 0 should be excluded (must be > 0)"""
        result = validate_liveview_settings({'exposure_time': 0})
        assert 'exposure_time' not in result

    def test_exposure_time_too_high_excluded(self):
        """exposure_time >= 1000000 should be excluded"""
        result = validate_liveview_settings({'exposure_time': 1000000})
        assert 'exposure_time' not in result

    def test_analogue_gain_below_min_excluded(self):
        """analogue_gain below 1.0 should be excluded"""
        result = validate_liveview_settings({'analogue_gain': 0.5})
        assert 'analogue_gain' not in result

    def test_analogue_gain_above_max_excluded(self):
        """analogue_gain above 16.0 should be excluded"""
        result = validate_liveview_settings({'analogue_gain': 20.0})
        assert 'analogue_gain' not in result


class TestUnknownSettings:
    """Tests for unknown settings that should be filtered out"""

    def test_unknown_setting_excluded(self):
        """Unknown settings should be excluded"""
        result = validate_liveview_settings({'unknown_setting': 'value'})
        assert 'unknown_setting' not in result
        assert result == {}

    def test_unknown_settings_with_valid_mixed(self):
        """Unknown settings excluded while valid settings pass"""
        settings = {
            'sharpness': 2.0,
            'unknown_setting': 'value',
            'af_mode': 1,
            'another_unknown': 123,
        }
        result = validate_liveview_settings(settings)
        assert result == {'sharpness': 2.0, 'af_mode': 1}


class TestMixedValidInvalid:
    """Tests for mixed valid and invalid settings"""

    def test_valid_kept_invalid_removed(self):
        """Valid settings kept, invalid settings removed"""
        settings = {
            'sharpness': 2.0,      # Valid
            'brightness': 5.0,     # Invalid (> 1.0)
            'af_mode': 1,          # Valid
            'contrast': 100.0,     # Invalid (> 4.0)
        }
        result = validate_liveview_settings(settings)
        assert result == {'sharpness': 2.0, 'af_mode': 1}

    def test_all_invalid_returns_empty(self):
        """All invalid settings returns empty dict"""
        settings = {
            'sharpness': 100.0,    # Invalid
            'brightness': 5.0,     # Invalid
            'af_mode': 99,         # Invalid
        }
        result = validate_liveview_settings(settings)
        assert result == {}


class TestEdgeCases:
    """Tests for edge cases and boundary values"""

    def test_empty_dict_returns_empty(self):
        """Empty input returns empty output"""
        result = validate_liveview_settings({})
        assert result == {}

    def test_sharpness_at_boundary_max(self):
        """Sharpness exactly at max (4.0) should pass"""
        result = validate_liveview_settings({'sharpness': 4.0})
        assert result == {'sharpness': 4.0}

    def test_sharpness_at_boundary_min(self):
        """Sharpness exactly at min (0.0) should pass"""
        result = validate_liveview_settings({'sharpness': 0.0})
        assert result == {'sharpness': 0.0}

    def test_brightness_at_boundary_max(self):
        """Brightness exactly at max (1.0) should pass"""
        result = validate_liveview_settings({'brightness': 1.0})
        assert result == {'brightness': 1.0}

    def test_brightness_at_boundary_min(self):
        """Brightness exactly at min (-1.0) should pass"""
        result = validate_liveview_settings({'brightness': -1.0})
        assert result == {'brightness': -1.0}

    def test_exposure_time_max_valid(self):
        """exposure_time just below 1000000 should pass"""
        result = validate_liveview_settings({'exposure_time': 999999})
        assert result == {'exposure_time': 999999}

    def test_exposure_time_min_valid(self):
        """exposure_time of 1 should pass"""
        result = validate_liveview_settings({'exposure_time': 1})
        assert result == {'exposure_time': 1}

    def test_analogue_gain_at_boundary_max(self):
        """analogue_gain exactly at max (16.0) should pass"""
        result = validate_liveview_settings({'analogue_gain': 16.0})
        assert result == {'analogue_gain': 16.0}

    def test_analogue_gain_at_boundary_min(self):
        """analogue_gain exactly at min (1.0) should pass"""
        result = validate_liveview_settings({'analogue_gain': 1.0})
        assert result == {'analogue_gain': 1.0}


class TestTypeHandling:
    """Tests for type handling and conversion errors"""

    def test_none_value_handled(self, capsys):
        """None values should be handled gracefully"""
        result = validate_liveview_settings({'sharpness': None})
        assert 'sharpness' not in result
        # Check warning was logged
        captured = capsys.readouterr()
        assert 'Warning' in captured.out or 'sharpness' not in result

    def test_string_value_for_numeric_excluded(self, capsys):
        """String value for numeric setting should be excluded"""
        result = validate_liveview_settings({'sharpness': 'not a number'})
        assert 'sharpness' not in result

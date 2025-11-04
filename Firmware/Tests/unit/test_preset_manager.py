"""
Unit tests for preset_manager.py module

Tests PresetManager type normalization, derivation, and conversion logic.
"""
import pytest
import sys
import inspect
from pathlib import Path
from unittest.mock import Mock, patch

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))


class TestTypeDerivation:
    """Test type derivation from validation functions"""

    def test_derive_type_from_int_validator(self, tmp_path):
        """Validator with int(v) should return int type"""
        from preset_manager import PresetManager

        # Create manager instance
        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Create a validator that uses int(v)
        validator = lambda v: int(v) in [0, 1, 2]

        # Derive type
        derived_type = manager._derive_type_from_validator('test_setting', validator, 'camera')

        assert derived_type == int

    def test_derive_type_from_float_validator(self, tmp_path):
        """Validator with float(v) should return float type"""
        from preset_manager import PresetManager

        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Create a validator that uses float(v) with decimal range
        validator = lambda v: 0.0 <= float(v) <= 16.0

        derived_type = manager._derive_type_from_validator('sharpness', validator, 'liveview')

        assert derived_type == float

    def test_derive_type_from_bool_validator(self, tmp_path):
        """Validator with .lower() in ['true', 'false'] should return bool"""
        from preset_manager import PresetManager

        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Create a validator for boolean
        validator = lambda v: str(v).lower() in ['true', 'false']

        derived_type = manager._derive_type_from_validator('auto_focus', validator, 'camera')

        assert derived_type == bool

    def test_derive_type_cache_mechanism(self, tmp_path):
        """Call _derive_type_from_validator() twice, verify caching works"""
        from preset_manager import PresetManager

        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Create a validator
        validator = lambda v: int(v) in [0, 1, 2]

        # First call - should cache
        type1 = manager._derive_type_from_validator('test_setting', validator, 'camera')

        # Second call - should use cache
        type2 = manager._derive_type_from_validator('test_setting', validator, 'camera')

        assert type1 == int
        assert type2 == int

        # Verify cache was used (both calls should return same type)
        cache_key = ('camera', 'test_setting')
        assert cache_key in manager._type_cache
        assert manager._type_cache[cache_key] == int

    def test_derive_type_handles_inspect_failure(self, tmp_path):
        """Use built-in function, should return None gracefully"""
        from preset_manager import PresetManager

        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Use built-in function (int) which can't be inspected for source
        validator = int

        derived_type = manager._derive_type_from_validator('test_setting', validator, 'camera')

        # Should return None gracefully when inspect fails
        assert derived_type is None


class TestTypeConversionEdgeCases:
    """Test type conversion edge cases"""

    def test_convert_value_handles_invalid_int_string(self, tmp_path):
        """'not-a-number' with int type should keep original"""
        from preset_manager import PresetManager
        from utils import ALLOWED_CAMERA_SETTINGS

        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Mock a setting that expects int
        with patch.dict(ALLOWED_CAMERA_SETTINGS, {'TestSetting': lambda v: int(v) in [0, 1, 2]}):
            result = manager._convert_value_type('TestSetting', 'not-a-number', 'camera')

            # Should keep original string when conversion fails
            assert result == 'not-a-number'
            assert isinstance(result, str)

    def test_convert_value_handles_invalid_float_string(self, tmp_path):
        """'abc.def' with float type should keep original"""
        from preset_manager import PresetManager
        from utils import ALLOWED_LIVEVIEW_SETTINGS

        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Mock a setting that expects float
        with patch.dict(ALLOWED_LIVEVIEW_SETTINGS, {'sharpness': lambda v: 0.0 <= float(v) <= 16.0}):
            result = manager._convert_value_type('sharpness', 'abc.def', 'liveview')

            # Should keep original string when conversion fails
            assert result == 'abc.def'
            assert isinstance(result, str)

    def test_convert_value_handles_empty_string_for_string_enum(self, tmp_path):
        """Empty string should be preserved"""
        from preset_manager import PresetManager
        from utils import ALLOWED_LIVEVIEW_SETTINGS

        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Mock a string enum setting
        with patch.dict(ALLOWED_LIVEVIEW_SETTINGS, {'focus_peaking_colour': lambda v: str(v).lower() in ['green', 'red', 'yellow']}):
            result = manager._convert_value_type('focus_peaking_colour', '', 'liveview')

            # Empty string should be preserved
            assert result == ''
            assert isinstance(result, str)


class TestTypeInferenceFallback:
    """Test type inference fallback logic"""

    def test_infer_type_distinguishes_zero_from_integer(self, tmp_path):
        """'0' → False, '1' → True, '2' → 2"""
        from preset_manager import PresetManager

        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Test '0' → False
        result0 = manager._infer_type('0')
        assert result0 is False
        assert isinstance(result0, bool)

        # Test '1' → True
        result1 = manager._infer_type('1')
        assert result1 is True
        assert isinstance(result1, bool)

        # Test '2' → 2 (integer, not boolean)
        result2 = manager._infer_type('2')
        assert result2 == 2
        assert isinstance(result2, int)

    def test_infer_type_handles_scientific_notation(self, tmp_path):
        """'1.5e-3' → 0.0015 (float)"""
        from preset_manager import PresetManager

        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        result = manager._infer_type('1.5e-3')

        assert result == 0.0015
        assert isinstance(result, float)

    def test_infer_type_handles_non_string_passthrough(self, tmp_path):
        """Already int/float/bool → no change"""
        from preset_manager import PresetManager

        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Test int passthrough
        result_int = manager._infer_type(42)
        assert result_int == 42
        assert isinstance(result_int, int)

        # Test float passthrough
        result_float = manager._infer_type(3.14)
        assert result_float == 3.14
        assert isinstance(result_float, float)

        # Test bool passthrough
        result_bool = manager._infer_type(True)
        assert result_bool is True
        assert isinstance(result_bool, bool)

    def test_infer_type_preserves_existing_types(self, tmp_path):
        """int(5) stays int(5), not converted"""
        from preset_manager import PresetManager

        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Test that existing types are preserved
        int_value = 5
        result = manager._infer_type(int_value)

        assert result == 5
        assert isinstance(result, int)
        assert result is int_value  # Should be the same object

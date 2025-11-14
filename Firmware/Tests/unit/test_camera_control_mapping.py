"""
Unit tests for camera_control_mapping module

Tests the centralized camera control naming convention mappings,
including conversions between snake_case, camelCase, and PascalCase,
as well as type conversion utilities.

Run with:
    pytest Tests/unit/test_camera_control_mapping.py -v

Or with coverage:
    pytest Tests/unit/test_camera_control_mapping.py -v \
        --cov=webui.backend.camera_control_mapping
"""

import unittest
import sys
import os

# Add parent directory to path to import webui modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from webui.backend.camera_control_mapping import (
    to_picamera_control,
    from_picamera_metadata,
    normalize_control_key,
    build_picamera_controls,
    handle_colour_gains,
    split_colour_gains,
    convert_to_picamera_type,
    convert_from_settings_file,
    convert_to_settings_file,
    SNAKE_TO_PASCAL,
    PASCAL_TO_SNAKE,
    CAMEL_TO_SNAKE,
    SNAKE_TO_CAMEL,
)


class TestMappingCompleteness(unittest.TestCase):
    """Test that all expected mappings are present"""

    def test_snake_to_pascal_completeness(self):
        """Verify all expected camera controls are mapped"""
        required_keys = [
            'sharpness', 'brightness', 'contrast', 'saturation',
            'af_mode', 'af_speed', 'af_range', 'lens_position',
            'ae_enable', 'ae_metering_mode', 'exposure_time', 'analogue_gain',
            'awb_enable', 'awb_mode', 'colour_gains', 'colour_gains_red', 'colour_gains_blue',
            'noise_reduction_mode'
        ]
        for key in required_keys:
            self.assertIn(key, SNAKE_TO_PASCAL, f"Missing mapping for {key}")

    def test_pascal_to_snake_reverse_mapping(self):
        """Verify reverse mapping is bidirectional"""
        for snake, pascal in SNAKE_TO_PASCAL.items():
            self.assertEqual(PASCAL_TO_SNAKE[pascal], snake,
                           f"Reverse mapping broken for {snake} → {pascal}")

    def test_camel_to_snake_frontend_mapping(self):
        """Verify frontend camelCase → snake_case"""
        test_cases = {
            'colourGainRed': 'colour_gains_red',
            'colourGainBlue': 'colour_gains_blue',
            'exposureTime': 'exposure_time',
            'analogueGain': 'analogue_gain',
            'aeMeteringMode': 'ae_metering_mode',
        }
        for camel, snake in test_cases.items():
            self.assertEqual(CAMEL_TO_SNAKE[camel], snake,
                           f"Frontend mapping wrong for {camel}")

    def test_snake_to_camel_reverse_mapping(self):
        """Verify snake → camel reverse mapping"""
        for camel, snake in CAMEL_TO_SNAKE.items():
            self.assertEqual(SNAKE_TO_CAMEL[snake], camel,
                           f"Reverse camel mapping broken for {snake} → {camel}")

    def test_no_duplicate_mappings(self):
        """Verify no duplicate values in mappings"""
        pascal_values = list(SNAKE_TO_PASCAL.values())
        self.assertEqual(len(pascal_values), len(set(pascal_values)),
                        "Duplicate PascalCase values found")


class TestNormalizeControlKey(unittest.TestCase):
    """Test normalize_control_key for dual naming support"""

    def test_accepts_pascalcase_directly(self):
        """Should accept PascalCase directly"""
        self.assertEqual(normalize_control_key('ColourGainRed'), 'ColourGainRed')
        self.assertEqual(normalize_control_key('ExposureTime'), 'ExposureTime')
        self.assertEqual(normalize_control_key('Sharpness'), 'Sharpness')

    def test_converts_snake_case_to_pascalcase(self):
        """Should convert snake_case → PascalCase"""
        self.assertEqual(normalize_control_key('colour_gains_red'), 'ColourGainRed')
        self.assertEqual(normalize_control_key('exposure_time'), 'ExposureTime')
        self.assertEqual(normalize_control_key('sharpness'), 'Sharpness')

    def test_converts_camelcase_to_pascalcase(self):
        """Should handle camelCase → PascalCase"""
        self.assertEqual(normalize_control_key('colourGainRed'), 'ColourGainRed')
        self.assertEqual(normalize_control_key('exposureTime'), 'ExposureTime')

    def test_unknown_keys_passthrough(self):
        """Should pass through unknown keys unchanged"""
        self.assertEqual(normalize_control_key('UnknownControl'), 'UnknownControl')
        self.assertEqual(normalize_control_key('random_key'), 'random_key')


class TestTypeConversion(unittest.TestCase):
    """Test type conversion utilities"""

    def test_bool_from_string_true_variants(self):
        """Test 'true' string → bool conversion"""
        for true_val in ['true', 'True', 'TRUE', '1', 'yes', 'on']:
            result = convert_from_settings_file('ae_enable', true_val)
            self.assertEqual(result, True, f"Failed to convert '{true_val}' to True")
            self.assertIsInstance(result, bool)

    def test_bool_from_string_false_variants(self):
        """Test 'false' string → bool conversion"""
        for false_val in ['false', 'False', 'FALSE', '0', 'no', 'off']:
            result = convert_from_settings_file('ae_enable', false_val)
            self.assertEqual(result, False, f"Failed to convert '{false_val}' to False")
            self.assertIsInstance(result, bool)

    def test_int_from_string(self):
        """Test string → int conversion"""
        result = convert_from_settings_file('exposure_time', '500')
        self.assertEqual(result, 500)
        self.assertIsInstance(result, int)

        result = convert_from_settings_file('af_mode', '2')
        self.assertEqual(result, 2)
        self.assertIsInstance(result, int)

    def test_float_from_string(self):
        """Test string → float conversion"""
        result = convert_from_settings_file('sharpness', '1.5')
        self.assertEqual(result, 1.5)
        self.assertIsInstance(result, float)

        result = convert_from_settings_file('analogue_gain', '8.0')
        self.assertEqual(result, 8.0)
        self.assertIsInstance(result, float)

    def test_already_typed_values_passthrough(self):
        """Test that already-typed values pass through unchanged"""
        self.assertEqual(convert_from_settings_file('ae_enable', True), True)
        self.assertEqual(convert_from_settings_file('exposure_time', 500), 500)
        self.assertEqual(convert_from_settings_file('sharpness', 1.5), 1.5)

    def test_type_conversion_to_string_bool(self):
        """Test Python bool → string for settings file"""
        self.assertEqual(convert_to_settings_file('ae_enable', True), 'true')
        self.assertEqual(convert_to_settings_file('ae_enable', False), 'false')
        self.assertEqual(convert_to_settings_file('awb_enable', True), 'true')

    def test_type_conversion_to_string_numeric(self):
        """Test Python numeric types → string"""
        self.assertEqual(convert_to_settings_file('exposure_time', 500), '500')
        self.assertEqual(convert_to_settings_file('sharpness', 1.5), '1.5')
        self.assertEqual(convert_to_settings_file('af_mode', 2), '2')

    def test_colour_gains_tuple_from_string(self):
        """Test colour_gains tuple parsing from string"""
        # Test with parentheses
        result = convert_from_settings_file('colour_gains', '(2.259, 1.5)')
        self.assertEqual(result, (2.259, 1.5))
        self.assertIsInstance(result, tuple)

        # Test without parentheses
        result = convert_from_settings_file('colour_gains', '2.259, 1.5')
        self.assertEqual(result, (2.259, 1.5))

        # Test without spaces
        result = convert_from_settings_file('colour_gains', '2.259,1.5')
        self.assertEqual(result, (2.259, 1.5))

    def test_colour_gains_tuple_to_string(self):
        """Test colour_gains tuple → string"""
        result = convert_to_settings_file('colour_gains', (2.259, 1.5))
        self.assertEqual(result, '(2.259, 1.5)')

        result = convert_to_settings_file('colour_gains', [2.5, 1.8])
        self.assertEqual(result, '(2.5, 1.8)')


class TestColourGainsHandling(unittest.TestCase):
    """Test special handling for colour gains"""

    def test_update_red_only(self):
        """Test updating only red component"""
        result = handle_colour_gains(red=2.5, current=(2.0, 1.5))
        self.assertEqual(result, {'ColourGains': (2.5, 1.5)})

    def test_update_blue_only(self):
        """Test updating only blue component"""
        result = handle_colour_gains(blue=1.8, current=(2.0, 1.5))
        self.assertEqual(result, {'ColourGains': (2.0, 1.8)})

    def test_update_both_components(self):
        """Test updating both red and blue"""
        result = handle_colour_gains(red=2.5, blue=1.8, current=(2.0, 1.5))
        self.assertEqual(result, {'ColourGains': (2.5, 1.8)})

    def test_update_neither_keeps_current(self):
        """Test that not specifying either keeps current values"""
        result = handle_colour_gains(current=(2.0, 1.5))
        self.assertEqual(result, {'ColourGains': (2.0, 1.5)})

    def test_split_colour_gains(self):
        """Test splitting tuple into separate components"""
        result = split_colour_gains((2.259, 1.5))
        self.assertEqual(result, {
            'colour_gains_red': 2.259,
            'colour_gains_blue': 1.5
        })


class TestToPicameraControl(unittest.TestCase):
    """Test individual control conversion"""

    def test_snake_case_conversion(self):
        """Test snake_case → PascalCase + type conversion"""
        key, value = to_picamera_control('exposure_time', 500)
        self.assertEqual(key, 'ExposureTime')
        self.assertEqual(value, 500)

        key, value = to_picamera_control('ae_enable', True)
        self.assertEqual(key, 'AeEnable')
        self.assertEqual(value, True)

    def test_string_type_conversion(self):
        """Test automatic type conversion from strings"""
        key, value = to_picamera_control('exposure_time', '500')
        self.assertEqual(key, 'ExposureTime')
        self.assertEqual(value, 500)
        self.assertIsInstance(value, int)

        key, value = to_picamera_control('ae_enable', 'true')
        self.assertEqual(key, 'AeEnable')
        self.assertEqual(value, True)
        self.assertIsInstance(value, bool)

    def test_camelcase_conversion(self):
        """Test camelCase → PascalCase"""
        key, value = to_picamera_control('exposureTime', 500)
        self.assertEqual(key, 'ExposureTime')
        self.assertEqual(value, 500)


class TestBuildPicameraControls(unittest.TestCase):
    """Test building complete controls dict"""

    def test_complete_dict_conversion(self):
        """Test building complete controls dict from settings"""
        settings = {
            'sharpness': 1.0,
            'brightness': 0.0,
            'exposure_time': 500,
            'ae_enable': True,
        }
        controls = build_picamera_controls(settings)

        self.assertEqual(controls['Sharpness'], 1.0)
        self.assertEqual(controls['Brightness'], 0.0)
        self.assertEqual(controls['ExposureTime'], 500)
        self.assertEqual(controls['AeEnable'], True)

    def test_with_type_conversion(self):
        """Test type conversion during build"""
        settings = {
            'exposure_time': '500',
            'ae_enable': 'true',
            'sharpness': '1.5',
        }
        controls = build_picamera_controls(settings, convert_types=True)

        self.assertEqual(controls['ExposureTime'], 500)
        self.assertIsInstance(controls['ExposureTime'], int)
        self.assertEqual(controls['AeEnable'], True)
        self.assertIsInstance(controls['AeEnable'], bool)
        self.assertEqual(controls['Sharpness'], 1.5)
        self.assertIsInstance(controls['Sharpness'], float)

    def test_without_type_conversion(self):
        """Test that convert_types=False preserves types"""
        settings = {
            'exposure_time': '500',
            'ae_enable': 'true',
        }
        controls = build_picamera_controls(settings, convert_types=False)

        self.assertEqual(controls['ExposureTime'], '500')
        self.assertIsInstance(controls['ExposureTime'], str)
        self.assertEqual(controls['AeEnable'], 'true')
        self.assertIsInstance(controls['AeEnable'], str)

    def test_unknown_keys_included(self):
        """Test that unknown keys are still processed"""
        settings = {
            'sharpness': 1.0,
            'unknown_key': 123,
        }
        controls = build_picamera_controls(settings)

        self.assertIn('Sharpness', controls)
        # Unknown key should pass through (may be lowercase)
        self.assertTrue('unknown_key' in controls or 'UnknownKey' in controls)


class TestFromPicameraMetadata(unittest.TestCase):
    """Test PascalCase metadata → snake_case for frontend"""

    def test_complete_metadata_conversion(self):
        """Test full metadata dict conversion"""
        metadata = {
            'ExposureTime': 500,
            'AnalogueGain': 8.0,
            'LensPosition': 3.0,
            'ColourGains': (2.259, 1.5),
            'AfState': 2,
            'Sharpness': 1.0,
        }
        result = from_picamera_metadata(metadata)

        self.assertEqual(result['exposure_time'], 500)
        self.assertEqual(result['analogue_gain'], 8.0)
        self.assertEqual(result['lens_position'], 3.0)
        self.assertEqual(result['colour_gains'], (2.259, 1.5))
        self.assertEqual(result['af_state'], 2)
        self.assertEqual(result['sharpness'], 1.0)

    def test_unknown_metadata_keys(self):
        """Test that unknown keys are converted to lowercase"""
        metadata = {
            'ExposureTime': 500,
            'UnknownControl': 123,
        }
        result = from_picamera_metadata(metadata)

        self.assertEqual(result['exposure_time'], 500)
        self.assertEqual(result['unknowncontrol'], 123)

    def test_preserves_types(self):
        """Test that value types are preserved"""
        metadata = {
            'ExposureTime': 500,
            'AnalogueGain': 8.0,
            'AeEnable': True,
            'ColourGains': (2.259, 1.5),
        }
        result = from_picamera_metadata(metadata)

        self.assertIsInstance(result['exposure_time'], int)
        self.assertIsInstance(result['analogue_gain'], float)
        self.assertIsInstance(result['ae_enable'], bool)
        self.assertIsInstance(result['colour_gains'], tuple)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""

    def test_empty_dicts(self):
        """Test handling of empty dicts"""
        self.assertEqual(build_picamera_controls({}), {})
        self.assertEqual(from_picamera_metadata({}), {})

    def test_none_values(self):
        """Test handling of None values"""
        settings = {
            'sharpness': None,
            'exposure_time': 500,
        }
        controls = build_picamera_controls(settings)
        self.assertIn('Sharpness', controls)
        self.assertIsNone(controls['Sharpness'])

    def test_case_sensitivity(self):
        """Test that mappings are case-sensitive"""
        # These should be different
        self.assertNotEqual(
            normalize_control_key('exposure_time'),
            'exposure_time'  # Should be 'ExposureTime'
        )
        self.assertEqual(
            normalize_control_key('exposure_time'),
            'ExposureTime'
        )

    def test_invalid_type_conversion_graceful(self):
        """Test that invalid conversions don't crash"""
        # Invalid int conversion
        result = convert_from_settings_file('exposure_time', 'not_a_number')
        self.assertEqual(result, 'not_a_number')  # Should pass through

        # Invalid float conversion
        result = convert_from_settings_file('sharpness', 'invalid')
        self.assertEqual(result, 'invalid')  # Should pass through


if __name__ == '__main__':
    unittest.main()

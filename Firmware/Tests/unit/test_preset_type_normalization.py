"""
Unit tests for preset type normalization

Tests the PresetManager's ability to normalize string values to proper types
when saving presets from different sources (CSV files, TXT files, frontend JSON).
"""

import pytest
import sys
from pathlib import Path
import tempfile
import shutil

# Setup path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "webui" / "backend"))

from preset_manager import PresetManager


class TestPresetTypeNormalization:
    """Test suite for preset type normalization"""

    @pytest.fixture
    def preset_manager(self):
        """Create a preset manager with temporary directories"""
        temp_dir = tempfile.mkdtemp()
        builtin_dir = Path(temp_dir) / "builtin"
        user_dir = Path(temp_dir) / "user"
        builtin_dir.mkdir()
        user_dir.mkdir()

        manager = PresetManager(builtin_dir, user_dir)

        yield manager

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_normalize_camera_integer_strings(self, preset_manager):
        """Test that string integers are converted to int for camera settings"""
        settings = {
            'camera': {
                'ExposureTime': '499',
                'AfMode': '1',
                'NoiseReductionMode': '2',
                'HDR': '3'
            }
        }

        normalized = preset_manager._normalize_setting_types(settings)

        assert isinstance(normalized['camera']['ExposureTime'], int)
        assert normalized['camera']['ExposureTime'] == 499
        assert isinstance(normalized['camera']['AfMode'], int)
        assert normalized['camera']['AfMode'] == 1
        assert isinstance(normalized['camera']['NoiseReductionMode'], int)
        assert normalized['camera']['NoiseReductionMode'] == 2
        assert isinstance(normalized['camera']['HDR'], int)
        assert normalized['camera']['HDR'] == 3

    def test_normalize_camera_float_strings(self, preset_manager):
        """Test that string floats are converted to float for camera settings"""
        settings = {
            'camera': {
                'AnalogueGain': '8.0',
                'Sharpness': '1.5',
                'Brightness': '0.0',
                'Contrast': '2.5',
                'Saturation': '1.0'
            }
        }

        normalized = preset_manager._normalize_setting_types(settings)

        assert isinstance(normalized['camera']['AnalogueGain'], float)
        assert normalized['camera']['AnalogueGain'] == 8.0
        assert isinstance(normalized['camera']['Sharpness'], float)
        assert normalized['camera']['Sharpness'] == 1.5
        assert isinstance(normalized['camera']['Brightness'], float)
        assert normalized['camera']['Brightness'] == 0.0

    def test_normalize_camera_boolean_strings(self, preset_manager):
        """Test that string booleans are converted to bool for camera settings"""
        settings = {
            'camera': {
                'AeEnable': 'True',
                'AwbEnable': 'true',
                'LensShadingEnable': 'False',
                'DefectCorrectionEnable': 'false',
                'UseCustomTuning': '1'
            }
        }

        normalized = preset_manager._normalize_setting_types(settings)

        assert isinstance(normalized['camera']['AeEnable'], bool)
        assert normalized['camera']['AeEnable'] is True
        assert isinstance(normalized['camera']['AwbEnable'], bool)
        assert normalized['camera']['AwbEnable'] is True
        assert isinstance(normalized['camera']['LensShadingEnable'], bool)
        assert normalized['camera']['LensShadingEnable'] is False
        assert isinstance(normalized['camera']['DefectCorrectionEnable'], bool)
        assert normalized['camera']['DefectCorrectionEnable'] is False
        assert isinstance(normalized['camera']['UseCustomTuning'], bool)
        assert normalized['camera']['UseCustomTuning'] is True

    def test_normalize_liveview_integer_strings(self, preset_manager):
        """Test that string integers are converted to int for liveview settings"""
        settings = {
            'liveview': {
                'noise_reduction_mode': '1',
                'awb_mode': '2',
                'stream_width': '1920',
                'stream_height': '1080',
                'stream_quality': '85'
            }
        }

        normalized = preset_manager._normalize_setting_types(settings)

        assert isinstance(normalized['liveview']['noise_reduction_mode'], int)
        assert normalized['liveview']['noise_reduction_mode'] == 1
        assert isinstance(normalized['liveview']['stream_width'], int)
        assert normalized['liveview']['stream_width'] == 1920
        assert isinstance(normalized['liveview']['stream_height'], int)
        assert normalized['liveview']['stream_height'] == 1080

    def test_normalize_liveview_float_strings(self, preset_manager):
        """Test that string floats are converted to float for liveview settings"""
        settings = {
            'liveview': {
                'sharpness': '1.0',
                'brightness': '0.5',
                'contrast': '1.5',
                'saturation': '1.0',
                'focus_peaking_intensity': '100.0'
            }
        }

        normalized = preset_manager._normalize_setting_types(settings)

        assert isinstance(normalized['liveview']['sharpness'], float)
        assert normalized['liveview']['sharpness'] == 1.0
        assert isinstance(normalized['liveview']['brightness'], float)
        assert normalized['liveview']['brightness'] == 0.5
        assert isinstance(normalized['liveview']['contrast'], float)
        assert normalized['liveview']['contrast'] == 1.5

    def test_normalize_liveview_boolean_strings(self, preset_manager):
        """Test that string booleans are converted to bool for liveview settings"""
        settings = {
            'liveview': {
                'focus_peaking_enabled': 'True',
                'awb_enable': 'true',
                'ae_enable': 'false'
            }
        }

        normalized = preset_manager._normalize_setting_types(settings)

        assert isinstance(normalized['liveview']['focus_peaking_enabled'], bool)
        assert normalized['liveview']['focus_peaking_enabled'] is True
        assert isinstance(normalized['liveview']['awb_enable'], bool)
        assert normalized['liveview']['awb_enable'] is True
        assert isinstance(normalized['liveview']['ae_enable'], bool)
        assert normalized['liveview']['ae_enable'] is False

    def test_normalize_string_fields_remain_strings(self, preset_manager):
        """Test that actual string fields remain as strings"""
        settings = {
            'camera': {
                'FocusPeakingColor': 'green',
                'FocusPeakingAlgorithm': 'laplacian'
            },
            'liveview': {
                'focus_peaking_color': 'RED',
                'focus_peaking_algorithm': 'SOBEL'
            }
        }

        normalized = preset_manager._normalize_setting_types(settings)

        assert isinstance(normalized['camera']['FocusPeakingColor'], str)
        assert normalized['camera']['FocusPeakingColor'] == 'green'
        assert isinstance(normalized['liveview']['focus_peaking_color'], str)
        assert normalized['liveview']['focus_peaking_color'] == 'red'  # Lowercased
        assert isinstance(normalized['liveview']['focus_peaking_algorithm'], str)
        assert normalized['liveview']['focus_peaking_algorithm'] == 'sobel'  # Lowercased

    def test_normalize_mixed_types(self, preset_manager):
        """Test normalization with mixed type settings"""
        settings = {
            'camera': {
                'ExposureTime': '500',          # String int
                'AnalogueGain': '8.0',          # String float
                'AeEnable': 'True',             # String bool
                'Sharpness': 1.5,               # Already float
                'AfMode': 1,                    # Already int
                'AwbEnable': True               # Already bool
            },
            'liveview': {
                'noise_reduction_mode': '2',   # String int
                'sharpness': '1.0',            # String float
                'focus_peaking_enabled': 'true', # String bool
                'brightness': 0.5,             # Already float
                'stream_width': 1920,          # Already int
                'awb_enable': False            # Already bool
            }
        }

        normalized = preset_manager._normalize_setting_types(settings)

        # Camera settings
        assert isinstance(normalized['camera']['ExposureTime'], int)
        assert normalized['camera']['ExposureTime'] == 500
        assert isinstance(normalized['camera']['AnalogueGain'], float)
        assert normalized['camera']['AnalogueGain'] == 8.0
        assert isinstance(normalized['camera']['AeEnable'], bool)
        assert normalized['camera']['AeEnable'] is True
        assert isinstance(normalized['camera']['Sharpness'], float)
        assert normalized['camera']['Sharpness'] == 1.5
        assert isinstance(normalized['camera']['AfMode'], int)
        assert normalized['camera']['AfMode'] == 1
        assert isinstance(normalized['camera']['AwbEnable'], bool)
        assert normalized['camera']['AwbEnable'] is True

        # Liveview settings
        assert isinstance(normalized['liveview']['noise_reduction_mode'], int)
        assert normalized['liveview']['noise_reduction_mode'] == 2
        assert isinstance(normalized['liveview']['sharpness'], float)
        assert normalized['liveview']['sharpness'] == 1.0
        assert isinstance(normalized['liveview']['focus_peaking_enabled'], bool)
        assert normalized['liveview']['focus_peaking_enabled'] is True
        assert isinstance(normalized['liveview']['brightness'], float)
        assert normalized['liveview']['brightness'] == 0.5
        assert isinstance(normalized['liveview']['stream_width'], int)
        assert normalized['liveview']['stream_width'] == 1920
        assert isinstance(normalized['liveview']['awb_enable'], bool)
        assert normalized['liveview']['awb_enable'] is False

    def test_normalize_unknown_fields_infer_type(self, preset_manager):
        """Test that unknown fields have their type inferred"""
        settings = {
            'camera': {
                'UnknownIntField': '42',
                'UnknownFloatField': '3.14',
                'UnknownBoolField': 'true',
                'UnknownStringField': 'custom_value'
            }
        }

        normalized = preset_manager._normalize_setting_types(settings)

        assert isinstance(normalized['camera']['UnknownIntField'], int)
        assert normalized['camera']['UnknownIntField'] == 42
        assert isinstance(normalized['camera']['UnknownFloatField'], float)
        assert normalized['camera']['UnknownFloatField'] == 3.14
        assert isinstance(normalized['camera']['UnknownBoolField'], bool)
        assert normalized['camera']['UnknownBoolField'] is True
        assert isinstance(normalized['camera']['UnknownStringField'], str)
        assert normalized['camera']['UnknownStringField'] == 'custom_value'

    def test_save_preset_normalizes_types(self, preset_manager):
        """Test that save_preset applies type normalization"""
        settings = {
            'camera': {
                'ExposureTime': '499',
                'AnalogueGain': '8.0',
                'AeEnable': 'True',
                'Sharpness': '1.5'
            },
            'liveview': {
                'noise_reduction_mode': '1',
                'sharpness': '1.0',
                'focus_peaking_enabled': 'true'
            }
        }

        success, message = preset_manager.save_preset(
            name='test_preset',
            settings=settings,
            description='Test preset with string types',
            workflow='both'
        )

        assert success is True

        # Load the preset and verify types
        loaded_preset = preset_manager.get_preset('test_preset')
        assert loaded_preset is not None

        camera_settings = loaded_preset['settings']['camera']
        assert isinstance(camera_settings['ExposureTime'], int)
        assert camera_settings['ExposureTime'] == 499
        assert isinstance(camera_settings['AnalogueGain'], float)
        assert camera_settings['AnalogueGain'] == 8.0
        assert isinstance(camera_settings['AeEnable'], bool)
        assert camera_settings['AeEnable'] is True
        assert isinstance(camera_settings['Sharpness'], float)
        assert camera_settings['Sharpness'] == 1.5

        liveview_settings = loaded_preset['settings']['liveview']
        assert isinstance(liveview_settings['noise_reduction_mode'], int)
        assert liveview_settings['noise_reduction_mode'] == 1
        assert isinstance(liveview_settings['sharpness'], float)
        assert liveview_settings['sharpness'] == 1.0
        assert isinstance(liveview_settings['focus_peaking_enabled'], bool)
        assert liveview_settings['focus_peaking_enabled'] is True

    def test_empty_settings_handled_gracefully(self, preset_manager):
        """Test that empty settings don't cause errors"""
        settings = {
            'camera': {},
            'liveview': {}
        }

        normalized = preset_manager._normalize_setting_types(settings)

        assert normalized['camera'] == {}
        assert normalized['liveview'] == {}

    def test_only_camera_settings(self, preset_manager):
        """Test normalization with only camera settings"""
        settings = {
            'camera': {
                'ExposureTime': '500',
                'Sharpness': '1.5'
            }
        }

        normalized = preset_manager._normalize_setting_types(settings)

        assert 'camera' in normalized
        assert 'liveview' not in normalized
        assert isinstance(normalized['camera']['ExposureTime'], int)
        assert isinstance(normalized['camera']['Sharpness'], float)

    def test_only_liveview_settings(self, preset_manager):
        """Test normalization with only liveview settings"""
        settings = {
            'liveview': {
                'sharpness': '1.0',
                'focus_peaking_enabled': 'true'
            }
        }

        normalized = preset_manager._normalize_setting_types(settings)

        assert 'liveview' in normalized
        assert 'camera' not in normalized
        assert isinstance(normalized['liveview']['sharpness'], float)
        assert isinstance(normalized['liveview']['focus_peaking_enabled'], bool)

    def test_infer_type_edge_cases(self, preset_manager):
        """Test edge cases in type inference"""
        # Test various boolean representations
        assert preset_manager._infer_type('true') is True
        assert preset_manager._infer_type('True') is True
        assert preset_manager._infer_type('TRUE') is True
        assert preset_manager._infer_type('false') is False
        assert preset_manager._infer_type('False') is False
        assert preset_manager._infer_type('FALSE') is False
        assert preset_manager._infer_type('yes') is True
        assert preset_manager._infer_type('no') is False
        assert preset_manager._infer_type('1') is True
        assert preset_manager._infer_type('0') is False

        # Test numeric edge cases
        assert isinstance(preset_manager._infer_type('42'), int)
        assert preset_manager._infer_type('42') == 42
        assert isinstance(preset_manager._infer_type('3.14'), float)
        assert preset_manager._infer_type('3.14') == 3.14
        assert isinstance(preset_manager._infer_type('0'), bool)  # '0' is bool False
        assert isinstance(preset_manager._infer_type('2'), int)  # '2' is int

        # Test string edge cases
        assert isinstance(preset_manager._infer_type('hello'), str)
        assert preset_manager._infer_type('hello') == 'hello'
        assert isinstance(preset_manager._infer_type(''), str)
        assert preset_manager._infer_type('') == ''

    def test_convert_value_type_already_correct(self, preset_manager):
        """Test that values with correct types are not modified"""
        # Camera settings
        assert preset_manager._convert_value_type('ExposureTime', 500, 'camera') == 500
        assert preset_manager._convert_value_type('Sharpness', 1.5, 'camera') == 1.5
        assert preset_manager._convert_value_type('AeEnable', True, 'camera') is True

        # Liveview settings
        assert preset_manager._convert_value_type('noise_reduction_mode', 2, 'liveview') == 2
        assert preset_manager._convert_value_type('sharpness', 1.0, 'liveview') == 1.0
        assert preset_manager._convert_value_type('focus_peaking_enabled', False, 'liveview') is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

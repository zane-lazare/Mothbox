"""
Unit tests for Phase 2.1 capture camera settings validation

Tests camera_settings.csv validation for full-resolution captures.

RUN ON RASPBERRY PI ONLY - tests Flask routes
"""
import pytest
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))


class TestCaptureSettingsValidation:
    """Test camera_settings.csv validation"""

    def test_lens_position_range(self):
        """Test LensPosition 0.0-10.0 diopters"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        # Valid values
        for lens_pos in [0.0, 0.5, 5.0, 7.84, 10.0]:
            assert ALLOWED_CAMERA_SETTINGS['LensPosition'](lens_pos), \
                f"Should accept LensPosition={lens_pos}"
            print(f"\n✓ Accepted LensPosition={lens_pos}")

        # Invalid values
        for invalid in [-0.1, 10.1, 20.0]:
            assert not ALLOWED_CAMERA_SETTINGS['LensPosition'](invalid), \
                f"Should reject LensPosition={invalid}"
            print(f"✓ Rejected LensPosition={invalid}")

    def test_af_controls_in_capture(self):
        """Test AfMode, AfSpeed, AfRange validation"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        print(f"\n🎯 Testing AfMode validation:")
        # AfMode: 0=Manual, 1=Auto Single, 2=Continuous
        for mode in [0, 1, 2]:
            assert ALLOWED_CAMERA_SETTINGS['AfMode'](mode), \
                f"Should accept AfMode={mode}"
            print(f"   {mode}: ✓")

        for invalid in [-1, 3, 10]:
            assert not ALLOWED_CAMERA_SETTINGS['AfMode'](invalid), \
                f"Should reject AfMode={invalid}"
            print(f"   {invalid}: ✗ (correctly rejected)")

        print(f"\n⚡ Testing AfSpeed validation:")
        # AfSpeed: 0=Normal, 1=Fast
        for speed in [0, 1]:
            assert ALLOWED_CAMERA_SETTINGS['AfSpeed'](speed), \
                f"Should accept AfSpeed={speed}"
            print(f"   {speed}: ✓")

        for invalid in [-1, 2]:
            assert not ALLOWED_CAMERA_SETTINGS['AfSpeed'](invalid), \
                f"Should reject AfSpeed={invalid}"
            print(f"   {invalid}: ✗ (correctly rejected)")

        print(f"\n📏 Testing AfRange validation:")
        # AfRange: 0=Normal, 1=Macro, 2=Full
        for range_val in [0, 1, 2]:
            assert ALLOWED_CAMERA_SETTINGS['AfRange'](range_val), \
                f"Should accept AfRange={range_val}"
            print(f"   {range_val}: ✓")

        for invalid in [-1, 3]:
            assert not ALLOWED_CAMERA_SETTINGS['AfRange'](invalid), \
                f"Should reject AfRange={invalid}"
            print(f"   {invalid}: ✗ (correctly rejected)")

        print(f"\n📐 Testing AfMetering validation:")
        # AfMetering: 0, 1, 2
        for metering in [0, 1, 2]:
            assert ALLOWED_CAMERA_SETTINGS['AfMetering'](metering), \
                f"Should accept AfMetering={metering}"
            print(f"   {metering}: ✓")

    def test_exposure_controls_validation(self):
        """Test ExposureTime, AnalogueGain, ExposureValue"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        print(f"\n📷 Testing ExposureTime validation:")
        # ExposureTime: 1-999999 microseconds (must be integer)
        for exp_time in [100, 499, 7000, 50000, 200000]:
            assert ALLOWED_CAMERA_SETTINGS['ExposureTime'](exp_time), \
                f"Should accept ExposureTime={exp_time}µs"
            print(f"   {exp_time}µs: ✓")

        # Test numeric out of range values
        for invalid in [0, -100, 1000000]:
            assert not ALLOWED_CAMERA_SETTINGS['ExposureTime'](invalid), \
                f"Should reject ExposureTime={invalid}"
            print(f"   {invalid}: ✗ (correctly rejected)")

        # Test invalid type raises exception
        try:
            ALLOWED_CAMERA_SETTINGS['ExposureTime']('abc')
            assert False, "Should raise ValueError for invalid type"
        except ValueError:
            print(f"   'abc': ✗ (correctly raised ValueError)")

        print(f"\n📊 Testing AnalogueGain (ISO) validation:")
        # AnalogueGain: 1.0-16.0
        for gain in [1.0, 1.5, 4.0, 8.0, 16.0]:
            assert ALLOWED_CAMERA_SETTINGS['AnalogueGain'](gain), \
                f"Should accept AnalogueGain={gain}"
            print(f"   {gain}: ✓")

        for invalid in [0.9, 16.1, -1.0]:
            assert not ALLOWED_CAMERA_SETTINGS['AnalogueGain'](invalid), \
                f"Should reject AnalogueGain={invalid}"
            print(f"   {invalid}: ✗ (correctly rejected)")

        print(f"\n☀️  Testing ExposureValue (EV compensation) validation:")
        # ExposureValue: -8.0 to +8.0
        for ev in [-8.0, -4.0, 0.0, 0.6, 4.0, 8.0]:
            assert ALLOWED_CAMERA_SETTINGS['ExposureValue'](ev), \
                f"Should accept ExposureValue={ev}"
            print(f"   {ev:+.1f}: ✓")

        for invalid in [-8.1, 8.1, -10.0]:
            assert not ALLOWED_CAMERA_SETTINGS['ExposureValue'](invalid), \
                f"Should reject ExposureValue={invalid}"
            print(f"   {invalid:+.1f}: ✗ (correctly rejected)")

    def test_ae_awb_enable_validation(self):
        """Test AeEnable and AwbEnable boolean validation"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        print(f"\n🔆 Testing AeEnable validation:")
        for valid in ['true', 'True', 'TRUE', 'false', 'False', 'FALSE']:
            assert ALLOWED_CAMERA_SETTINGS['AeEnable'](valid), \
                f"Should accept AeEnable={valid}"
            print(f"   {valid}: ✓")

        for invalid in ['yes', 'no', '1', '0', 'on', 'off']:
            assert not ALLOWED_CAMERA_SETTINGS['AeEnable'](invalid), \
                f"Should reject AeEnable={invalid}"
            print(f"   {invalid}: ✗ (correctly rejected)")

        print(f"\n🌡️  Testing AwbEnable validation:")
        for valid in ['true', 'True', 'false', 'False']:
            assert ALLOWED_CAMERA_SETTINGS['AwbEnable'](valid), \
                f"Should accept AwbEnable={valid}"
            print(f"   {valid}: ✓")

    @pytest.mark.skip(reason="HDR validators not yet implemented - TDD placeholder")
    def test_hdr_settings_validation(self):
        """Test HDR and HDR_width validation"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        print(f"\n📸 Testing HDR (bracket count) validation:")
        # HDR: 1, 3, 5, 7 exposures
        for hdr_count in [1, 3, 5, 7]:
            assert ALLOWED_CAMERA_SETTINGS['HDR'](hdr_count), \
                f"Should accept HDR={hdr_count}"
            print(f"   {hdr_count} exposures: ✓")

        for invalid in [0, 2, 4, 6, 9, -1]:
            assert not ALLOWED_CAMERA_SETTINGS['HDR'](invalid), \
                f"Should reject HDR={invalid}"
            print(f"   {invalid}: ✗ (correctly rejected)")

        print(f"\n📸 Testing HDR_width (bracket step) validation:")
        # HDR_width: 1000-50000 microseconds
        for width in [1000, 7000, 18000, 50000]:
            assert ALLOWED_CAMERA_SETTINGS['HDR_width'](width), \
                f"Should accept HDR_width={width}µs"
            print(f"   {width}µs: ✓")

        for invalid in [999, 50001, -1000]:
            assert not ALLOWED_CAMERA_SETTINGS['HDR_width'](invalid), \
                f"Should reject HDR_width={invalid}"
            print(f"   {invalid}µs: ✗ (correctly rejected)")


@pytest.mark.skip(reason="AutoCalibration validators not yet implemented - TDD placeholder")
class TestAutoCalibrationSettings:
    """Test auto-calibration settings validation"""

    def test_auto_calibration_enable(self):
        """Test AutoCalibration 0 or 1"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        print(f"\n🔧 Testing AutoCalibration validation:")
        for valid in [0, 1]:
            assert ALLOWED_CAMERA_SETTINGS['AutoCalibration'](valid), \
                f"Should accept AutoCalibration={valid}"
            print(f"   {valid} ({'Off' if valid == 0 else 'On'}): ✓")

        for invalid in [-1, 2, 10]:
            assert not ALLOWED_CAMERA_SETTINGS['AutoCalibration'](invalid), \
                f"Should reject AutoCalibration={invalid}"
            print(f"   {invalid}: ✗ (correctly rejected)")

    def test_calibration_period_range(self):
        """Test AutoCalibrationPeriod 1-10000"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        print(f"\n⏱️  Testing AutoCalibrationPeriod validation:")
        # Common values
        for period in [1, 10, 100, 600, 1000, 10000]:
            assert ALLOWED_CAMERA_SETTINGS['AutoCalibrationPeriod'](period), \
                f"Should accept AutoCalibrationPeriod={period}"
            print(f"   {period} photos: ✓")

        # Invalid values
        for invalid in [0, -1, 10001, 100000]:
            assert not ALLOWED_CAMERA_SETTINGS['AutoCalibrationPeriod'](invalid), \
                f"Should reject AutoCalibrationPeriod={invalid}"
            print(f"   {invalid}: ✗ (correctly rejected)")


@pytest.mark.skip(reason="ImageFormat validators not yet implemented - TDD placeholder")
class TestImageFormatSettings:
    """Test image format settings"""

    def test_image_file_type_validation(self):
        """Test ImageFileType 0 (JPEG), 1 (PNG), 2 (BMP)"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        print(f"\n🖼️  Testing ImageFileType validation:")
        formats = {
            0: "JPEG (fast, compressed)",
            1: "PNG (slow, lossless)",
            2: "BMP (huge, fast)"
        }

        for file_type, description in formats.items():
            assert ALLOWED_CAMERA_SETTINGS['ImageFileType'](file_type), \
                f"Should accept ImageFileType={file_type}"
            print(f"   {file_type} ({description}): ✓")

        for invalid in [-1, 3, 10]:
            assert not ALLOWED_CAMERA_SETTINGS['ImageFileType'](invalid), \
                f"Should reject ImageFileType={invalid}"
            print(f"   {invalid}: ✗ (correctly rejected)")

    def test_vertical_flip_validation(self):
        """Test VerticalFlip 0 or 1"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        print(f"\n🔄 Testing VerticalFlip validation:")
        for flip in [0, 1]:
            assert ALLOWED_CAMERA_SETTINGS['VerticalFlip'](flip), \
                f"Should accept VerticalFlip={flip}"
            print(f"   {flip} ({'No flip' if flip == 0 else 'Flip'}): ✓")

        for invalid in [-1, 2, 10]:
            assert not ALLOWED_CAMERA_SETTINGS['VerticalFlip'](invalid), \
                f"Should reject VerticalFlip={invalid}"
            print(f"   {invalid}: ✗ (correctly rejected)")


class TestWhiteBalanceSettings:
    """Test white balance settings for capture"""

    def test_awb_mode_all_presets(self):
        """Test all 8 AwbMode presets"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        print(f"\n🌡️  Testing all AwbMode presets:")
        awb_modes = {
            0: "Auto",
            1: "Incandescent (2800K)",
            2: "Tungsten",
            3: "Fluorescent",
            4: "Indoor",
            5: "Daylight (5600K)",
            6: "Cloudy (6500K)",
            7: "Custom"
        }

        for mode, description in awb_modes.items():
            assert ALLOWED_CAMERA_SETTINGS['AwbMode'](mode), \
                f"Should accept AwbMode={mode}"
            print(f"   {mode} ({description}): ✓")

        for invalid in [-1, 8, 10]:
            assert not ALLOWED_CAMERA_SETTINGS['AwbMode'](invalid), \
                f"Should reject AwbMode={invalid}"
            print(f"   {invalid}: ✗ (correctly rejected)")


class TestImageQualityControls:
    """Test image quality controls in capture settings"""

    def test_sharpness_range(self):
        """Test Sharpness 0.0-4.0 for capture (picamera2 typical range)"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        print(f"\n🔪 Testing Sharpness validation:")
        for sharpness in [0.0, 1.0, 1.5, 3.0, 4.0]:
            assert ALLOWED_CAMERA_SETTINGS['Sharpness'](sharpness), \
                f"Should accept Sharpness={sharpness}"
            print(f"   {sharpness}: ✓")

        for invalid in [-0.1, 4.1, 8.0, 16.0]:
            assert not ALLOWED_CAMERA_SETTINGS['Sharpness'](invalid), \
                f"Should reject Sharpness={invalid}"
            print(f"   {invalid}: ✗ (correctly rejected)")

    def test_brightness_contrast_saturation(self):
        """Test Brightness, Contrast, Saturation ranges"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        print(f"\n☀️  Testing Brightness validation:")
        # Brightness: -1.0 to 1.0 (only Brightness can be negative)
        for brightness in [-1.0, -0.5, 0.0, 0.5, 1.0]:
            assert ALLOWED_CAMERA_SETTINGS['Brightness'](brightness), \
                f"Should accept Brightness={brightness}"
            print(f"   {brightness:+.1f}: ✓")

        print(f"\n📊 Testing Contrast validation:")
        # Contrast: 0.0 to 4.0 (picamera2 typical range)
        for contrast in [0.0, 1.0, 2.0, 4.0]:
            assert ALLOWED_CAMERA_SETTINGS['Contrast'](contrast), \
                f"Should accept Contrast={contrast}"
            print(f"   {contrast}: ✓")

        # Negative contrast should be rejected
        for invalid in [-1.0, -0.5, 4.1]:
            assert not ALLOWED_CAMERA_SETTINGS['Contrast'](invalid), \
                f"Should reject Contrast={invalid}"
            print(f"   {invalid}: ✗ (correctly rejected)")

        print(f"\n🎨 Testing Saturation validation:")
        # Saturation: 0.0 to 4.0 (picamera2 typical range)
        for saturation in [0.0, 1.0, 2.0, 4.0]:
            assert ALLOWED_CAMERA_SETTINGS['Saturation'](saturation), \
                f"Should accept Saturation={saturation}"
            print(f"   {saturation}: ✓")

        # Negative saturation should be rejected
        for invalid in [-1.0, -0.5, 4.1]:
            assert not ALLOWED_CAMERA_SETTINGS['Saturation'](invalid), \
                f"Should reject Saturation={invalid}"
            print(f"   {invalid}: ✗ (correctly rejected)")


@pytest.mark.skip(reason="Some validators not yet implemented - TDD placeholder")
class TestComprehensiveValidation:
    """Test comprehensive validation scenarios"""

    def test_all_settings_have_validators(self):
        """Verify all Phase 2.1 settings have validators"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        expected_settings = [
            # Image quality
            'Sharpness', 'Brightness', 'Contrast', 'Saturation',
            # Exposure
            'ExposureTime', 'ExposureValue', 'AnalogueGain', 'AeEnable',
            # Focus
            'AfMode', 'AfSpeed', 'AfRange', 'AfMetering', 'LensPosition',
            # White balance
            'AwbEnable', 'AwbMode',
            # HDR
            'HDR', 'HDR_width',
            # Auto-calibration
            'AutoCalibration', 'AutoCalibrationPeriod',
            # Image format
            'ImageFileType', 'VerticalFlip'
        ]

        print(f"\n📋 Verifying all Phase 2.1 settings have validators:")
        missing = []
        for setting in expected_settings:
            if setting in ALLOWED_CAMERA_SETTINGS:
                print(f"   {setting}: ✓")
            else:
                print(f"   {setting}: ✗ MISSING")
                missing.append(setting)

        assert len(missing) == 0, f"Missing validators for: {missing}"
        print(f"\n✅ All {len(expected_settings)} Phase 2.1 settings have validators!")

    def test_realistic_capture_scenario(self):
        """Test realistic capture settings combination"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        # Realistic night capture with macro focus
        realistic_settings = {
            'ExposureTime': '50000',  # 50ms for insects at night
            'AnalogueGain': '4.0',  # Moderate ISO
            'Sharpness': '2.0',  # Extra sharp for detail
            'Contrast': '0.5',  # Slight contrast boost
            'AfMode': '0',  # Manual focus
            'LensPosition': '1.2',  # Close focus for insects
            'AfRange': '1',  # Macro range
            'HDR': '3',  # 3-exposure HDR
            'HDR_width': '10000',  # 10ms bracket steps
            'AutoCalibration': '1',  # Enable auto-cal
            'AutoCalibrationPeriod': '100',  # Every 100 photos
            'ImageFileType': '0',  # JPEG
            'VerticalFlip': '1'  # Flip for mounting
        }

        print(f"\n🦋 Testing realistic night insect capture scenario:")
        all_valid = True
        for setting, value in realistic_settings.items():
            validator = ALLOWED_CAMERA_SETTINGS.get(setting)
            if validator:
                is_valid = validator(value)
                print(f"   {setting}={value}: {'✓' if is_valid else '✗ FAILED'}")
                all_valid = all_valid and is_valid
            else:
                print(f"   {setting}: ✗ NO VALIDATOR")
                all_valid = False

        assert all_valid, "Realistic scenario should pass all validations"
        print(f"\n✅ Realistic capture scenario validated successfully!")

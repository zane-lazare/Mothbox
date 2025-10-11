"""
Unit tests for Phase 2.1 preview camera controls validation

Tests image quality, focus, and white balance controls for WebUI preview stream.

RUN ON RASPBERRY PI ONLY - tests Flask routes
"""
import pytest
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))


class TestImageQualityValidation:
    """Test image quality controls validation"""

    def test_sharpness_range_validation(self):
        """Test sharpness must be 0.0-16.0"""
        from routes.config import config_bp
        from flask import Flask

        app = Flask(__name__)
        app.register_blueprint(config_bp, url_prefix='/config')

        with app.test_client() as client:
            # Invalid: too low
            response = client.post('/config/webui', json={'sharpness': -0.1})
            assert response.status_code == 400, "Should reject sharpness < 0.0"
            print(f"\n✓ Rejected sharpness=-0.1 (too low)")

            # Invalid: too high
            response = client.post('/config/webui', json={'sharpness': 16.1})
            assert response.status_code == 400, "Should reject sharpness > 16.0"
            print(f"✓ Rejected sharpness=16.1 (too high)")

            # Valid: boundary values
            for sharpness in [0.0, 1.0, 8.0, 16.0]:
                response = client.post('/config/webui', json={'sharpness': sharpness})
                assert response.status_code == 200, \
                    f"Should accept sharpness={sharpness}"
                print(f"✓ Accepted sharpness={sharpness}")

    def test_brightness_range_validation(self):
        """Test brightness must be -1.0 to 1.0"""
        from routes.config import config_bp
        from flask import Flask

        app = Flask(__name__)
        app.register_blueprint(config_bp, url_prefix='/config')

        with app.test_client() as client:
            # Invalid: too low
            response = client.post('/config/webui', json={'brightness': -1.1})
            assert response.status_code == 400, "Should reject brightness < -1.0"
            print(f"\n✓ Rejected brightness=-1.1 (too low)")

            # Invalid: too high
            response = client.post('/config/webui', json={'brightness': 1.1})
            assert response.status_code == 400, "Should reject brightness > 1.0"
            print(f"✓ Rejected brightness=1.1 (too high)")

            # Valid: range including boundaries
            for brightness in [-1.0, -0.5, 0.0, 0.5, 1.0]:
                response = client.post('/config/webui', json={'brightness': brightness})
                assert response.status_code == 200, \
                    f"Should accept brightness={brightness}"
                print(f"✓ Accepted brightness={brightness}")

    def test_contrast_saturation_validation(self):
        """Test contrast and saturation 0.0-32.0"""
        from routes.config import config_bp
        from flask import Flask

        app = Flask(__name__)
        app.register_blueprint(config_bp, url_prefix='/config')

        with app.test_client() as client:
            print(f"\n📊 Testing contrast validation:")

            # Contrast: invalid values
            response = client.post('/config/webui', json={'contrast': -0.1})
            assert response.status_code == 400, "Should reject contrast < 0.0"
            print(f"   ✓ Rejected contrast=-0.1")

            response = client.post('/config/webui', json={'contrast': 32.1})
            assert response.status_code == 400, "Should reject contrast > 32.0"
            print(f"   ✓ Rejected contrast=32.1")

            # Contrast: valid values
            for contrast in [0.0, 1.0, 16.0, 32.0]:
                response = client.post('/config/webui', json={'contrast': contrast})
                assert response.status_code == 200, f"Should accept contrast={contrast}"
                print(f"   ✓ Accepted contrast={contrast}")

            print(f"\n📊 Testing saturation validation:")

            # Saturation: invalid values
            response = client.post('/config/webui', json={'saturation': -0.1})
            assert response.status_code == 400, "Should reject saturation < 0.0"
            print(f"   ✓ Rejected saturation=-0.1")

            response = client.post('/config/webui', json={'saturation': 32.1})
            assert response.status_code == 400, "Should reject saturation > 32.0"
            print(f"   ✓ Rejected saturation=32.1")

            # Saturation: valid values
            for saturation in [0.0, 1.0, 16.0, 32.0]:
                response = client.post('/config/webui', json={'saturation': saturation})
                assert response.status_code == 200, f"Should accept saturation={saturation}"
                print(f"   ✓ Accepted saturation={saturation}")


class TestFocusControlsValidation:
    """Test focus controls validation"""

    def test_af_mode_validation(self):
        """Test AfMode must be 0, 1, or 2"""
        from routes.config import config_bp
        from flask import Flask

        app = Flask(__name__)
        app.register_blueprint(config_bp, url_prefix='/config')

        with app.test_client() as client:
            # Invalid values
            for invalid in [-1, 3, 10, 'auto']:
                response = client.post('/config/webui', json={'af_mode': invalid})
                assert response.status_code == 400, f"Should reject af_mode={invalid}"
                print(f"\n✓ Rejected af_mode={invalid}")

            # Valid values
            af_modes = {
                0: "Manual",
                1: "Auto (Single)",
                2: "Auto (Continuous)"
            }

            print(f"\n🎯 Testing valid AfMode values:")
            for mode, description in af_modes.items():
                response = client.post('/config/webui', json={'af_mode': mode})
                assert response.status_code == 200, f"Should accept af_mode={mode}"
                print(f"   {mode} ({description}): ✓")

    def test_af_range_validation(self):
        """Test AfRange must be 0, 1, or 2"""
        from routes.config import config_bp
        from flask import Flask

        app = Flask(__name__)
        app.register_blueprint(config_bp, url_prefix='/config')

        with app.test_client() as client:
            # Invalid values
            response = client.post('/config/webui', json={'af_range': -1})
            assert response.status_code == 400, "Should reject af_range=-1"
            print(f"\n✓ Rejected af_range=-1")

            response = client.post('/config/webui', json={'af_range': 3})
            assert response.status_code == 400, "Should reject af_range=3"
            print(f"✓ Rejected af_range=3")

            # Valid values
            af_ranges = {
                0: "Normal (0.5m - infinity)",
                1: "Macro (10cm - 50cm)",
                2: "Full (10cm - infinity)"
            }

            print(f"\n📏 Testing valid AfRange values:")
            for range_val, description in af_ranges.items():
                response = client.post('/config/webui', json={'af_range': range_val})
                assert response.status_code == 200, f"Should accept af_range={range_val}"
                print(f"   {range_val} ({description}): ✓")

    def test_af_speed_validation(self):
        """Test AfSpeed must be 0 or 1"""
        from routes.config import config_bp
        from flask import Flask

        app = Flask(__name__)
        app.register_blueprint(config_bp, url_prefix='/config')

        with app.test_client() as client:
            # Invalid values
            for invalid in [-1, 2, 10]:
                response = client.post('/config/webui', json={'af_speed': invalid})
                assert response.status_code == 400, f"Should reject af_speed={invalid}"
                print(f"\n✓ Rejected af_speed={invalid}")

            # Valid values
            af_speeds = {
                0: "Normal (accurate)",
                1: "Fast (may hunt)"
            }

            print(f"\n⚡ Testing valid AfSpeed values:")
            for speed, description in af_speeds.items():
                response = client.post('/config/webui', json={'af_speed': speed})
                assert response.status_code == 200, f"Should accept af_speed={speed}"
                print(f"   {speed} ({description}): ✓")


class TestWhiteBalanceValidation:
    """Test white balance controls validation"""

    def test_awb_enable_validation(self):
        """Test AwbEnable must be boolean"""
        from routes.config import config_bp
        from flask import Flask

        app = Flask(__name__)
        app.register_blueprint(config_bp, url_prefix='/config')

        with app.test_client() as client:
            # Valid: boolean values
            print(f"\n🌡️  Testing AwbEnable validation:")
            for awb_enable in [True, False]:
                response = client.post('/config/webui', json={'awb_enable': awb_enable})
                assert response.status_code == 200, f"Should accept awb_enable={awb_enable}"
                print(f"   {awb_enable}: ✓")

    def test_awb_mode_validation(self):
        """Test AwbMode must be 0-7"""
        from routes.config import config_bp
        from flask import Flask

        app = Flask(__name__)
        app.register_blueprint(config_bp, url_prefix='/config')

        with app.test_client() as client:
            # Invalid values
            response = client.post('/config/webui', json={'awb_mode': -1})
            assert response.status_code == 400, "Should reject awb_mode=-1"
            print(f"\n✓ Rejected awb_mode=-1")

            response = client.post('/config/webui', json={'awb_mode': 8})
            assert response.status_code == 400, "Should reject awb_mode=8"
            print(f"✓ Rejected awb_mode=8")

            # Valid values: all 8 WB presets
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

            print(f"\n🌡️  Testing all AwbMode presets:")
            for mode, description in awb_modes.items():
                response = client.post('/config/webui', json={'awb_mode': mode})
                assert response.status_code == 200, f"Should accept awb_mode={mode}"
                print(f"   {mode} ({description}): ✓")


class TestPreviewControlsPersistence:
    """Test preview controls are saved/loaded correctly"""

    def test_image_quality_persistence(self):
        """Test sharpness, brightness, contrast, saturation persist"""
        from routes.config import config_bp
        from flask import Flask

        app = Flask(__name__)
        app.register_blueprint(config_bp, url_prefix='/config')

        test_settings = {
            'sharpness': 2.5,
            'brightness': 0.2,
            'contrast': 1.5,
            'saturation': 1.2
        }

        with app.test_client() as client:
            # Update settings
            response = client.post('/config/webui', json=test_settings)
            assert response.status_code == 200, "Should save image quality settings"

            # Retrieve settings
            response = client.get('/config/webui')
            assert response.status_code == 200
            data = response.get_json()

            # Verify all settings match
            print(f"\n💾 Image quality persistence test:")
            for key, expected_value in test_settings.items():
                actual_value = data.get(key)
                print(f"   {key}: {actual_value} {'✓' if abs(actual_value - expected_value) < 0.01 else '✗'}")
                assert abs(actual_value - expected_value) < 0.01, \
                    f"{key}: expected {expected_value}, got {actual_value}"

    def test_focus_controls_persistence(self):
        """Test focus settings persist across updates"""
        from routes.config import config_bp
        from flask import Flask

        app = Flask(__name__)
        app.register_blueprint(config_bp, url_prefix='/config')

        test_settings = {
            'af_mode': 1,  # Auto single
            'af_speed': 1,  # Fast
            'af_range': 1  # Macro
        }

        with app.test_client() as client:
            # Update settings
            response = client.post('/config/webui', json=test_settings)
            assert response.status_code == 200, "Should save focus settings"

            # Retrieve settings
            response = client.get('/config/webui')
            assert response.status_code == 200
            data = response.get_json()

            # Verify all settings match
            print(f"\n💾 Focus controls persistence test:")
            for key, expected_value in test_settings.items():
                actual_value = data.get(key)
                print(f"   {key}: {actual_value} {'✓' if actual_value == expected_value else '✗'}")
                assert actual_value == expected_value, \
                    f"{key}: expected {expected_value}, got {actual_value}"

    def test_white_balance_persistence(self):
        """Test white balance settings persist"""
        from routes.config import config_bp
        from flask import Flask

        app = Flask(__name__)
        app.register_blueprint(config_bp, url_prefix='/config')

        test_settings = {
            'awb_enable': False,
            'awb_mode': 5  # Daylight
        }

        with app.test_client() as client:
            # Update settings
            response = client.post('/config/webui', json=test_settings)
            assert response.status_code == 200, "Should save WB settings"

            # Retrieve settings
            response = client.get('/config/webui')
            assert response.status_code == 200
            data = response.get_json()

            # Verify all settings match
            print(f"\n💾 White balance persistence test:")
            for key, expected_value in test_settings.items():
                actual_value = data.get(key)
                print(f"   {key}: {actual_value} {'✓' if actual_value == expected_value else '✗'}")
                assert actual_value == expected_value, \
                    f"{key}: expected {expected_value}, got {actual_value}"

    def test_defaults_when_missing(self):
        """Test default values when webui_settings.txt missing"""
        from routes.config import config_bp
        from flask import Flask
        from mothbox_paths import WEBUI_SETTINGS_FILE

        app = Flask(__name__)
        app.register_blueprint(config_bp, url_prefix='/config')

        with app.test_client() as client:
            response = client.get('/config/webui')
            assert response.status_code == 200
            data = response.get_json()

            # Expected defaults for Phase 2.1 controls
            expected_defaults = {
                'sharpness': 1.0,
                'brightness': 0.0,
                'contrast': 1.0,
                'saturation': 1.0,
                'af_mode': 2,
                'af_speed': 0,
                'af_range': 0,
                'awb_enable': True,
                'awb_mode': 0
            }

            print(f"\n📋 Phase 2.1 default values:")
            if WEBUI_SETTINGS_FILE.exists():
                print(f"   Source: {WEBUI_SETTINGS_FILE} (existing config)")
                # Just verify values are in valid ranges
                assert 0.0 <= data.get('sharpness', 0) <= 16.0, "Sharpness out of range"
                assert -1.0 <= data.get('brightness', 0) <= 1.0, "Brightness out of range"
                assert 0.0 <= data.get('contrast', 0) <= 32.0, "Contrast out of range"
                assert 0.0 <= data.get('saturation', 0) <= 32.0, "Saturation out of range"
                assert data.get('af_mode', -1) in [0, 1, 2], "AfMode out of range"
                assert data.get('af_speed', -1) in [0, 1], "AfSpeed out of range"
                assert data.get('af_range', -1) in [0, 1, 2], "AfRange out of range"
                assert isinstance(data.get('awb_enable'), bool), "AwbEnable not boolean"
                assert 0 <= data.get('awb_mode', -1) <= 7, "AwbMode out of range"
                for key in expected_defaults:
                    print(f"   {key}: {data.get(key)} ✓")
            else:
                print(f"   Source: Defaults (no config file)")
                for key, expected_value in expected_defaults.items():
                    actual_value = data.get(key)
                    matches = actual_value == expected_value
                    print(f"   {key}: {actual_value} {'✓' if matches else '✗'}")
                    assert actual_value == expected_value, \
                        f"{key}: expected {expected_value}, got {actual_value}"


class TestCombinedSettings:
    """Test multiple settings updated together"""

    def test_update_all_preview_controls_at_once(self):
        """Test updating all Phase 2.1 controls in single request"""
        from routes.config import config_bp
        from flask import Flask

        app = Flask(__name__)
        app.register_blueprint(config_bp, url_prefix='/config')

        # Comprehensive settings update
        all_settings = {
            # Image quality
            'sharpness': 1.8,
            'brightness': 0.1,
            'contrast': 1.2,
            'saturation': 1.1,

            # Focus
            'af_mode': 1,
            'af_speed': 1,
            'af_range': 2,

            # White balance
            'awb_enable': False,
            'awb_mode': 6
        }

        with app.test_client() as client:
            # Update all settings
            response = client.post('/config/webui', json=all_settings)
            assert response.status_code == 200, "Should accept all controls together"
            print(f"\n✓ Accepted combined update of all Phase 2.1 controls")

            # Verify all persisted correctly
            response = client.get('/config/webui')
            data = response.get_json()

            print(f"\n📊 Verifying combined settings:")
            for key, expected in all_settings.items():
                actual = data.get(key)
                if isinstance(expected, float):
                    matches = abs(actual - expected) < 0.01
                else:
                    matches = actual == expected
                print(f"   {key}: {actual} {'✓' if matches else '✗'}")
                assert matches, f"{key} mismatch: expected {expected}, got {actual}"

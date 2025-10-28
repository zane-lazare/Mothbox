"""
Unit tests for preset management system

RUN ON RASPBERRY PI ONLY - tests Flask routes and preset manager
"""
import pytest
import sys
import json
import tempfile
import shutil
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))


class TestPresetManager:
    """Test PresetManager class functionality"""

    def setup_method(self):
        """Create temporary directories for testing"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.builtin_dir = self.test_dir / 'built-in'
        self.user_dir = self.test_dir / 'user'
        self.builtin_dir.mkdir(parents=True)
        self.user_dir.mkdir(parents=True)

        # Create test built-in preset
        self.test_builtin = {
            'name': 'test_builtin',
            'display_name': 'Test Built-in',
            'description': 'Test preset',
            'category': 'built-in',
            'version': '1.0',
            'settings': {
                'camera': {'ExposureTime': 5000, 'AnalogueGain': 2.0},
                'liveview': {'sharpness': 1.5}
            }
        }
        with open(self.builtin_dir / 'test_builtin.json', 'w') as f:
            json.dump(self.test_builtin, f)

    def teardown_method(self):
        """Clean up temporary directories"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_list_presets_includes_builtin(self):
        """Built-in presets should be listed"""
        from preset_manager import PresetManager

        manager = PresetManager(self.builtin_dir, self.user_dir)
        presets = manager.list_presets()

        assert len(presets) >= 1
        assert any(p['name'] == 'test_builtin' for p in presets)
        assert any(p['category'] == 'built-in' for p in presets)

    def test_get_preset_returns_data(self):
        """Getting a preset by name should return its data"""
        from preset_manager import PresetManager

        manager = PresetManager(self.builtin_dir, self.user_dir)
        preset = manager.get_preset('test_builtin')

        assert preset is not None
        assert preset['name'] == 'test_builtin'
        assert 'settings' in preset
        assert 'camera' in preset['settings']

    def test_get_nonexistent_preset_returns_none(self):
        """Getting a non-existent preset should return None"""
        from preset_manager import PresetManager

        manager = PresetManager(self.builtin_dir, self.user_dir)
        preset = manager.get_preset('does_not_exist')

        assert preset is None

    def test_save_user_preset(self):
        """Should be able to save a user preset"""
        from preset_manager import PresetManager

        manager = PresetManager(self.builtin_dir, self.user_dir)
        settings = {
            'camera': {'ExposureTime': 10000},
            'liveview': {'brightness': 0.5}
        }

        success, message = manager.save_preset('my_preset', settings, 'Test description')

        assert success is True
        assert 'successfully' in message.lower()
        assert (self.user_dir / 'my_preset.json').exists()

    def test_save_preset_invalid_name(self):
        """Should reject preset names with invalid characters"""
        from preset_manager import PresetManager

        manager = PresetManager(self.builtin_dir, self.user_dir)
        settings = {'camera': {}}

        success, message = manager.save_preset('invalid name!', settings)

        assert success is False
        assert 'alphanumeric' in message.lower() or 'underscore' in message.lower()

    def test_delete_user_preset(self):
        """Should be able to delete user presets"""
        from preset_manager import PresetManager

        manager = PresetManager(self.builtin_dir, self.user_dir)

        # Create a user preset
        settings = {'camera': {'ExposureTime': 5000}}
        manager.save_preset('to_delete', settings)

        # Delete it
        success, message = manager.delete_preset('to_delete')

        assert success is True
        assert not (self.user_dir / 'to_delete.json').exists()

    def test_cannot_delete_builtin_preset(self):
        """Built-in presets should be protected from deletion"""
        from preset_manager import PresetManager

        manager = PresetManager(self.builtin_dir, self.user_dir)
        success, message = manager.delete_preset('test_builtin')

        assert success is False
        assert 'built-in' in message.lower()

    def test_validate_preset_structure(self):
        """Should validate preset structure"""
        from preset_manager import PresetManager

        manager = PresetManager(self.builtin_dir, self.user_dir)

        # Valid preset
        valid_preset = {'camera': {'ExposureTime': 5000}}
        is_valid, msg = manager.validate_preset(valid_preset)
        assert is_valid is True

        # Invalid preset (no camera or liveview)
        invalid_preset = {'other': {}}
        is_valid, msg = manager.validate_preset(invalid_preset)
        assert is_valid is False

    def test_preset_counts(self):
        """Should return accurate preset counts"""
        from preset_manager import PresetManager

        manager = PresetManager(self.builtin_dir, self.user_dir)

        # Save a user preset
        manager.save_preset('user1', {'camera': {}})

        counts = manager.get_preset_count()

        assert counts['built_in'] == 1  # test_builtin
        assert counts['user'] == 1  # user1
        assert counts['total'] == 2

    def test_legacy_preview_key_migration(self):
        """Should migrate legacy 'preview' key to 'liveview'"""
        from preset_manager import PresetManager

        manager = PresetManager(self.builtin_dir, self.user_dir)

        # Create preset with legacy 'preview' key (old format)
        legacy_preset = {
            'name': 'legacy_test',
            'workflow': 'liveview',
            'settings': {
                'preview': {
                    'sharpness': 2.0,
                    'noise_reduction_mode': 1,
                    'brightness': 0.0
                }
            }
        }

        # Normalize should migrate 'preview' to 'liveview'
        normalized = manager.normalize_preset(legacy_preset)

        # Verify migration occurred
        assert 'liveview' in normalized['settings']
        assert 'preview' not in normalized['settings']
        assert normalized['settings']['liveview']['sharpness'] == 2.0
        assert normalized['settings']['liveview']['noise_reduction_mode'] == 1
        assert normalized['settings']['liveview']['brightness'] == 0.0

        # Verify validation passes after migration
        is_valid, msg = manager.validate_preset(normalized)
        assert is_valid is True, f"Validation failed: {msg}"

    def test_legacy_preview_preset_apply(self):
        """Should be able to load and apply preset with legacy 'preview' key"""
        from preset_manager import PresetManager
        import json

        manager = PresetManager(self.builtin_dir, self.user_dir)

        # Create a preset file with legacy 'preview' key
        legacy_preset = {
            'name': 'legacy_liveview',
            'display_name': 'Legacy Live View',
            'description': 'Old format preset',
            'workflow': 'liveview',
            'version': '1.0',
            'settings': {
                'preview': {
                    'sharpness': 1.5,
                    'brightness': 0.2,
                    'noise_reduction_mode': 2
                }
            }
        }

        # Save to user directory with legacy format
        with open(self.user_dir / 'legacy_liveview.json', 'w') as f:
            json.dump(legacy_preset, f)

        # Load preset - should auto-migrate
        loaded_preset = manager.get_preset('legacy_liveview')

        # Verify it was loaded and migrated
        assert loaded_preset is not None
        assert 'liveview' in loaded_preset['settings']
        assert 'preview' not in loaded_preset['settings']
        assert loaded_preset['settings']['liveview']['sharpness'] == 1.5
        assert loaded_preset['settings']['liveview']['noise_reduction_mode'] == 2


class TestPresetAPIEndpoints:
    """Test preset API routes"""

    def setup_method(self):
        """Setup Flask test client"""
        from flask import Flask
        from routes.presets import presets_bp

        self.app = Flask(__name__)
        self.app.register_blueprint(presets_bp, url_prefix='/presets')
        self.client = self.app.test_client()

    def test_list_presets_endpoint(self):
        """GET /presets should return preset list"""
        response = self.client.get('/presets')
        assert response.status_code == 200

        data = response.get_json()
        assert 'presets' in data
        assert 'counts' in data
        assert isinstance(data['presets'], list)

    def test_list_presets_includes_builtin(self):
        """Should include built-in presets in list"""
        response = self.client.get('/presets')
        data = response.get_json()

        # Should have at least some built-in presets (daylight, night, etc.)
        builtin_presets = [p for p in data['presets'] if p['category'] == 'built-in']
        assert len(builtin_presets) > 0

    def test_get_specific_preset(self):
        """GET /presets/:name should return preset details"""
        # First get list to find a valid preset name
        list_response = self.client.get('/presets')
        presets = list_response.get_json()['presets']

        if presets:
            preset_name = presets[0]['name']
            response = self.client.get(f'/presets/{preset_name}')

            if response.status_code == 200:
                data = response.get_json()
                assert 'name' in data
                assert 'settings' in data
            else:
                # If preset file doesn't exist, should return 404
                assert response.status_code == 404

    def test_get_nonexistent_preset(self):
        """GET /presets/:name should return 404 for non-existent preset"""
        response = self.client.get('/presets/does_not_exist_xyz')
        assert response.status_code == 404

    def test_create_preset_requires_name(self):
        """POST /presets should require preset name"""
        response = self.client.post('/presets',
                                    json={'description': 'Test'},
                                    content_type='application/json')

        # Should fail validation
        assert response.status_code in [400, 500]  # Bad request or server error

    def test_apply_preset_requires_valid_applyto(self):
        """POST /presets/:name/apply should validate apply_to parameter"""
        response = self.client.post('/presets/test/apply',
                                    json={'apply_to': 'invalid'},
                                    content_type='application/json')

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_delete_nonexistent_preset(self):
        """DELETE /presets/:name should handle non-existent presets"""
        response = self.client.delete('/presets/does_not_exist_xyz')
        assert response.status_code == 400  # Should return error


class TestBuiltInPresets:
    """Test built-in preset configurations"""

    def test_all_builtin_presets_exist(self):
        """All expected built-in presets should exist"""
        from preset_manager import PresetManager
        from pathlib import Path

        builtin_dir = Path(__file__).parent.parent.parent / 'webui' / 'backend' / 'presets_builtin'

        if not builtin_dir.exists():
            pytest.skip("Built-in presets directory not found")

        expected_presets = ['daylight', 'night', 'macro', 'high_speed', 'balanced']

        for preset_name in expected_presets:
            preset_file = builtin_dir / f'{preset_name}.json'
            assert preset_file.exists(), f"Missing built-in preset: {preset_name}"

    def test_builtin_presets_valid_json(self):
        """All built-in presets should be valid JSON"""
        from pathlib import Path

        builtin_dir = Path(__file__).parent.parent.parent / 'webui' / 'backend' / 'presets_builtin'

        if not builtin_dir.exists():
            pytest.skip("Built-in presets directory not found")

        for preset_file in builtin_dir.glob('*.json'):
            with open(preset_file, 'r') as f:
                data = json.load(f)  # Should not raise exception
                assert 'name' in data
                assert 'settings' in data
                print(f"✓ Valid JSON: {preset_file.name}")

    def test_builtin_presets_have_required_fields(self):
        """Built-in presets should have all required metadata"""
        from pathlib import Path

        builtin_dir = Path(__file__).parent.parent.parent / 'webui' / 'backend' / 'presets_builtin'

        if not builtin_dir.exists():
            pytest.skip("Built-in presets directory not found")

        required_fields = ['name', 'display_name', 'description', 'category', 'settings']

        for preset_file in builtin_dir.glob('*.json'):
            with open(preset_file, 'r') as f:
                data = json.load(f)

                for field in required_fields:
                    assert field in data, f"{preset_file.name} missing field: {field}"

                assert data['category'] == 'built-in'
                print(f"✓ Valid fields: {preset_file.name}")


class TestPresetSettingsValidation:
    """Test that preset settings are validated against camera settings rules"""

    def test_preset_camera_settings_validated(self):
        """Preset camera settings should be validated against ALLOWED_CAMERA_SETTINGS"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS
        from pathlib import Path

        builtin_dir = Path(__file__).parent.parent.parent / 'webui' / 'backend' / 'presets_builtin'

        if not builtin_dir.exists():
            pytest.skip("Built-in presets directory not found")

        for preset_file in builtin_dir.glob('*.json'):
            with open(preset_file, 'r') as f:
                data = json.load(f)

                if 'camera' in data.get('settings', {}):
                    camera_settings = data['settings']['camera']

                    for setting_name, setting_value in camera_settings.items():
                        assert setting_name in ALLOWED_CAMERA_SETTINGS, \
                            f"{preset_file.name}: Unknown setting '{setting_name}'"

                        # Validate the value
                        validator = ALLOWED_CAMERA_SETTINGS[setting_name]
                        try:
                            is_valid = validator(setting_value)
                            assert is_valid, \
                                f"{preset_file.name}: Invalid value for '{setting_name}': {setting_value}"
                        except Exception as e:
                            pytest.fail(
                                f"{preset_file.name}: Validation error for '{setting_name}={setting_value}': {e}"
                            )

                    print(f"✓ Camera settings validated: {preset_file.name}")

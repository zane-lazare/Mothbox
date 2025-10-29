"""
Unit tests for preset type normalization during load operations.

Tests that type normalization (string → int/float/bool conversion)
happens correctly when loading presets, not just when saving them.

This addresses issue #66: Preset validation happens too late
"""

import json
import pytest
import tempfile
import shutil
from pathlib import Path
import sys

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "webui" / "backend"))
from preset_manager import PresetManager


class TestPresetLoadNormalization:
    """Test that presets with string types are normalized on load"""

    @pytest.fixture
    def preset_manager(self):
        """Create a PresetManager with temporary directories"""
        with tempfile.TemporaryDirectory() as tmpdir:
            builtin_dir = Path(tmpdir) / "builtin"
            user_dir = Path(tmpdir) / "user"
            builtin_dir.mkdir()
            user_dir.mkdir()

            yield PresetManager(builtin_dir, user_dir)

    def test_load_preset_with_string_numeric_values(self, preset_manager):
        """Test that preset JSON with string numeric values gets normalized on load"""
        # Create a preset file with string values (simulating manual edit or legacy format)
        preset_data = {
            "name": "test_string_values",
            "display_name": "Test String Values",
            "description": "Preset with string numeric values",
            "version": "1.0",
            "workflow": "both",
            "category": "user",
            "settings": {
                "camera": {
                    "ExposureTime": "10000",  # String instead of int
                    "AnalogueGain": "2.5",    # String instead of float
                    "Sharpness": "1.2"        # String instead of float
                },
                "liveview": {
                    "sharpness": "1.5",       # String instead of float
                    "brightness": "0",        # String instead of int/float
                    "focus_peaking_enabled": "true"  # String instead of bool
                }
            }
        }

        # Save the preset with string values directly to file (bypassing save_preset)
        preset_path = preset_manager.user_dir / "test_string_values.json"
        with open(preset_path, 'w') as f:
            json.dump(preset_data, f)

        # Load the preset - should normalize types
        loaded_preset = preset_manager.get_preset("test_string_values")

        assert loaded_preset is not None, "Preset should load successfully"

        # Verify types are normalized
        camera = loaded_preset['settings']['camera']
        assert isinstance(camera['ExposureTime'], int), "ExposureTime should be normalized to int"
        assert camera['ExposureTime'] == 10000

        assert isinstance(camera['AnalogueGain'], float), "AnalogueGain should be normalized to float"
        assert camera['AnalogueGain'] == 2.5

        assert isinstance(camera['Sharpness'], float), "Sharpness should be normalized to float"
        assert camera['Sharpness'] == 1.2

        liveview = loaded_preset['settings']['liveview']
        assert isinstance(liveview['sharpness'], float), "liveview sharpness should be normalized to float"
        assert liveview['sharpness'] == 1.5

        assert isinstance(liveview['brightness'], (int, float)), "brightness should be normalized to numeric"
        assert liveview['brightness'] == 0

    def test_list_presets_with_string_values(self, preset_manager):
        """Test that list_presets() also normalizes types"""
        # Create multiple presets with string values
        for i in range(3):
            preset_data = {
                "name": f"test_preset_{i}",
                "display_name": f"Test Preset {i}",
                "description": f"Test preset {i}",
                "version": "1.0",
                "workflow": "both",
                "category": "builtin",
                "settings": {
                    "camera": {
                        "ExposureTime": str(10000 + i * 1000),  # String
                        "Sharpness": str(1.0 + i * 0.1)        # String
                    },
                    "liveview": {
                        "sharpness": str(1.5 + i * 0.1)        # String
                    }
                }
            }

            preset_path = preset_manager.builtin_dir / f"test_preset_{i}.json"
            with open(preset_path, 'w') as f:
                json.dump(preset_data, f)

        # List all presets - should normalize and validate each one
        presets = preset_manager.list_presets()

        assert len(presets) == 3, "All 3 presets should be listed"

        for preset in presets:
            assert preset['category'] == 'built-in', "Category should be 'built-in'"
            assert 'test_preset_' in preset['name']

    def test_load_preset_with_mixed_types(self, preset_manager):
        """Test preset with both proper types and string types"""
        preset_data = {
            "name": "mixed_types",
            "display_name": "Mixed Types",
            "description": "Preset with mixed proper and string types",
            "version": "1.0",
            "workflow": "photo",
            "category": "user",
            "settings": {
                "camera": {
                    "ExposureTime": 5000,        # Already int
                    "AnalogueGain": "2.0",       # String
                    "Sharpness": 1.5,            # Already float
                    "Brightness": "50"           # String
                }
            }
        }

        preset_path = preset_manager.user_dir / "mixed_types.json"
        with open(preset_path, 'w') as f:
            json.dump(preset_data, f)

        loaded_preset = preset_manager.get_preset("mixed_types")

        assert loaded_preset is not None
        camera = loaded_preset['settings']['camera']

        # All should now be proper types
        assert isinstance(camera['ExposureTime'], int)
        assert isinstance(camera['AnalogueGain'], float)
        assert isinstance(camera['Sharpness'], float)
        assert isinstance(camera['Brightness'], (int, float))

    def test_load_invalid_preset_fails_validation(self, preset_manager):
        """Test that truly invalid presets still fail validation"""
        # Create a preset with values that can't be converted
        preset_data = {
            "name": "invalid_preset",
            "display_name": "Invalid Preset",
            "description": "Preset with invalid values",
            "version": "1.0",
            "workflow": "photo",
            "category": "user",
            "settings": {
                "camera": {
                    "ExposureTime": "not_a_number",  # Can't convert to int
                }
            }
        }

        preset_path = preset_manager.user_dir / "invalid_preset.json"
        with open(preset_path, 'w') as f:
            json.dump(preset_data, f)

        # Should return None due to validation failure
        loaded_preset = preset_manager.get_preset("invalid_preset")

        # The normalization will keep it as string, validation should still pass
        # because validate_preset accepts float("not_a_number") which raises exception
        # Actually, this will be caught and logged, returning as string
        # Validation uses float() which will fail, so preset should be rejected
        assert loaded_preset is None, "Invalid preset should be rejected"

    def test_legacy_preview_migration_with_type_normalization(self, preset_manager):
        """Test that legacy 'preview' key migration works with type normalization"""
        preset_data = {
            "name": "legacy_with_preview",
            "display_name": "Legacy with Preview",
            "description": "Legacy preset with 'preview' key and string types",
            "version": "1.0",
            "workflow": "liveview",
            "category": "builtin",
            "settings": {
                "preview": {  # Legacy key name
                    "sharpness": "2.0",           # String
                    "brightness": "100",          # String
                    "focus_peaking_enabled": "false"  # String bool
                }
            }
        }

        preset_path = preset_manager.builtin_dir / "legacy_with_preview.json"
        with open(preset_path, 'w') as f:
            json.dump(preset_data, f)

        loaded_preset = preset_manager.get_preset("legacy_with_preview")

        assert loaded_preset is not None

        # Should have migrated 'preview' to 'liveview'
        assert 'liveview' in loaded_preset['settings']
        assert 'preview' not in loaded_preset['settings']

        # Types should be normalized
        liveview = loaded_preset['settings']['liveview']
        assert isinstance(liveview['sharpness'], float)
        assert liveview['sharpness'] == 2.0
        assert isinstance(liveview['brightness'], (int, float))
        assert liveview['brightness'] == 100

    def test_save_then_load_consistency(self, preset_manager):
        """Test that save and load operations produce consistent types"""
        # Save a preset using save_preset (which normalizes types)
        settings = {
            "camera": {
                "ExposureTime": "8000",  # String input (like from CSV)
                "Sharpness": "1.8"
            },
            "liveview": {
                "sharpness": "1.2",
                "brightness": "75"
            }
        }

        success, msg = preset_manager.save_preset(
            name="consistency_test",
            settings=settings,
            description="Test save/load consistency",
            workflow="both"
        )

        assert success, f"Save should succeed: {msg}"

        # Load the preset back
        loaded_preset = preset_manager.get_preset("consistency_test")

        assert loaded_preset is not None

        # Types should be consistent (normalized to proper types)
        camera = loaded_preset['settings']['camera']
        assert isinstance(camera['ExposureTime'], int)
        assert isinstance(camera['Sharpness'], float)

        liveview = loaded_preset['settings']['liveview']
        assert isinstance(liveview['sharpness'], float)
        assert isinstance(liveview['brightness'], (int, float))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

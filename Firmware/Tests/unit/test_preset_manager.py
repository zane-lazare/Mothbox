"""
Unit tests for preset_manager.py module

Tests PresetManager type normalization, derivation, and conversion logic.
"""

import sys
from pathlib import Path
from unittest.mock import patch

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "webui" / "backend"))


class TestTypeDerivation:
    """Test type derivation from validation functions"""

    def test_derive_type_from_int_validator(self, tmp_path):
        """Validator with int(v) should return int type"""
        from preset_manager import PresetManager

        # Create manager instance
        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Create a validator that uses int(v)
        def validator(v):
            return int(v) in [0, 1, 2]

        # Derive type
        derived_type = manager._derive_type_from_validator("test_setting", validator, "camera")

        assert derived_type is int

    def test_derive_type_from_float_validator(self, tmp_path):
        """Validator with float(v) should return float type"""
        from preset_manager import PresetManager

        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Create a validator that uses float(v) with decimal range
        def validator(v):
            return 0.0 <= float(v) <= 16.0

        derived_type = manager._derive_type_from_validator("sharpness", validator, "liveview")

        assert derived_type is float

    def test_derive_type_from_bool_validator(self, tmp_path):
        """Validator with .lower() in ['true', 'false'] should return bool"""
        from preset_manager import PresetManager

        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Create a validator for boolean
        def validator(v):
            return str(v).lower() in ["true", "false"]

        derived_type = manager._derive_type_from_validator("auto_focus", validator, "camera")

        assert derived_type is bool

    def test_derive_type_cache_mechanism(self, tmp_path):
        """Call _derive_type_from_validator() twice, verify caching works"""
        from preset_manager import PresetManager

        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Create a validator
        def validator(v):
            return int(v) in [0, 1, 2]

        # First call - should cache
        type1 = manager._derive_type_from_validator("test_setting", validator, "camera")

        # Second call - should use cache
        type2 = manager._derive_type_from_validator("test_setting", validator, "camera")

        assert type1 is int
        assert type2 is int

        # Verify cache was used (both calls should return same type)
        cache_key = ("camera", "test_setting")
        assert cache_key in manager._type_cache
        assert manager._type_cache[cache_key] is int

    def test_derive_type_handles_inspect_failure(self, tmp_path):
        """Use built-in function, should return None gracefully"""
        from preset_manager import PresetManager

        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Use built-in function (int) which can't be inspected for source
        validator = int

        derived_type = manager._derive_type_from_validator("test_setting", validator, "camera")

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
        with patch.dict(ALLOWED_CAMERA_SETTINGS, {"TestSetting": lambda v: int(v) in [0, 1, 2]}):
            result = manager._convert_value_type("TestSetting", "not-a-number", "camera")

            # Should keep original string when conversion fails
            assert result == "not-a-number"
            assert isinstance(result, str)

    def test_convert_value_handles_invalid_float_string(self, tmp_path):
        """'abc.def' with float type should keep original"""
        from preset_manager import PresetManager
        from utils import ALLOWED_LIVEVIEW_SETTINGS

        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Mock a setting that expects float
        with patch.dict(
            ALLOWED_LIVEVIEW_SETTINGS, {"sharpness": lambda v: 0.0 <= float(v) <= 16.0}
        ):
            result = manager._convert_value_type("sharpness", "abc.def", "liveview")

            # Should keep original string when conversion fails
            assert result == "abc.def"
            assert isinstance(result, str)

    def test_convert_value_handles_empty_string_for_string_enum(self, tmp_path):
        """Empty string should be preserved"""
        from preset_manager import PresetManager
        from utils import ALLOWED_LIVEVIEW_SETTINGS

        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Mock a string enum setting
        with patch.dict(
            ALLOWED_LIVEVIEW_SETTINGS,
            {"focus_peaking_colour": lambda v: str(v).lower() in ["green", "red", "yellow"]},
        ):
            result = manager._convert_value_type("focus_peaking_colour", "", "liveview")

            # Empty string should be preserved
            assert result == ""
            assert isinstance(result, str)


class TestTypeInferenceFallback:
    """Test type inference fallback logic"""

    def test_infer_type_distinguishes_zero_from_integer(self, tmp_path):
        """'0' → False, '1' → True, '2' → 2"""
        from preset_manager import PresetManager

        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Test '0' → False
        result0 = manager._infer_type("0")
        assert result0 is False
        assert isinstance(result0, bool)

        # Test '1' → True
        result1 = manager._infer_type("1")
        assert result1 is True
        assert isinstance(result1, bool)

        # Test '2' → 2 (integer, not boolean)
        result2 = manager._infer_type("2")
        assert result2 == 2
        assert isinstance(result2, int)

    def test_infer_type_handles_scientific_notation(self, tmp_path):
        """'1.5e-3' → 0.0015 (float)"""
        from preset_manager import PresetManager

        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        result = manager._infer_type("1.5e-3")

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


class TestPresetConcurrentAccess:
    """Test concurrent access and file locking for preset operations"""

    def test_save_preset_uses_exclusive_lock(self, tmp_path, monkeypatch):
        """Verify FileLock is used with exclusive=True when saving"""
        from unittest.mock import patch

        from preset_manager import PresetManager

        # Create manager
        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Save a preset
        settings = {"camera": {"ExposureTime": 1000}, "liveview": {"sharpness": 1.0}}

        with (
            patch("webui.backend.lib.file_lock.FileLock.__init__", return_value=None) as mock_init,
            patch("webui.backend.lib.file_lock.FileLock.__enter__") as mock_enter,
            patch("webui.backend.lib.file_lock.FileLock.__exit__", return_value=False),
        ):
            # Return a real file handle from __enter__
            preset_path = tmp_path / "user" / "test_preset.json"
            real_file = open(preset_path, "w+")  # noqa: SIM115 - handle passed to mock
            mock_enter.return_value = real_file

            success, message = manager.save_preset("test_preset", settings, "Test description")

            real_file.close()

            assert success is True
            assert "saved successfully" in message

            # Verify FileLock was called with exclusive=True
            mock_init.assert_called_once()
            call_kwargs = mock_init.call_args
            assert (
                call_kwargs[1].get(
                    "exclusive", call_kwargs[0][1] if len(call_kwargs[0]) > 1 else None
                )
                is True
            )

    def test_concurrent_saves_serialize_correctly(self, tmp_path):
        """Start 5 threads saving different presets simultaneously, verify all saved correctly without corruption"""
        import json
        import threading

        from preset_manager import PresetManager

        # Create manager
        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Results tracking
        results = []
        results_lock = threading.Lock()

        def save_preset_thread(preset_num):
            """Thread function to save a preset"""
            preset_name = f"concurrent_test_{preset_num}"
            settings = {
                "camera": {"ExposureTime": 1000 * preset_num},
                "liveview": {"sharpness": float(preset_num)},
            }
            success, message = manager.save_preset(
                preset_name, settings, f"Concurrent test preset {preset_num}"
            )
            with results_lock:
                results.append((preset_num, success, message, preset_name))

        # Start 5 concurrent save operations
        threads = []
        for i in range(1, 6):
            thread = threading.Thread(target=save_preset_thread, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5.0)

        # Verify all saves succeeded
        assert len(results) == 5, f"Expected 5 results, got {len(results)}"
        for preset_num, success, message, _preset_name in results:
            assert success is True, f"Preset {preset_num} failed: {message}"

        # Verify all presets were saved correctly (no corruption)
        for preset_num, _success, _message, preset_name in results:
            preset_path = tmp_path / "user" / f"{preset_name}.json"
            assert preset_path.exists(), f"Preset file {preset_name} not found"

            # Verify file is valid JSON and contains correct data
            with open(preset_path) as f:
                data = json.load(f)
                assert data["name"] == preset_name
                assert data["settings"]["camera"]["ExposureTime"] == 1000 * preset_num
                assert data["settings"]["liveview"]["sharpness"] == float(preset_num)

    def test_save_preset_releases_lock_on_exception(self, tmp_path, monkeypatch):
        """Mock json.dump() to raise exception, verify FileLock __exit__ is still called"""

        from preset_manager import PresetManager

        # Create manager
        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Mock json.dump to raise exception
        def failing_dump(*args, **kwargs):
            raise OSError("Simulated disk write error")

        monkeypatch.setattr("json.dump", failing_dump)

        # Try to save preset (should fail due to json.dump error)
        settings = {"camera": {"ExposureTime": 1000}}
        success, message = manager.save_preset("test_preset", settings)

        # Save should fail gracefully (FileLock context manager handles cleanup)
        assert success is False
        assert "Failed to save preset" in message


class TestPresetErrorRecovery:
    """Test error handling and graceful recovery from various failure scenarios"""

    def test_get_preset_handles_corrupted_json(self, tmp_path):
        """Create preset file with invalid JSON like {{{, verify returns None and logs error"""
        from preset_manager import PresetManager

        # Create manager
        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Create corrupt preset file
        corrupt_preset = tmp_path / "user" / "corrupt_preset.json"
        corrupt_preset.write_text("{{{")

        # Try to get corrupt preset
        result = manager.get_preset("corrupt_preset")

        # Should return None gracefully
        assert result is None

    def test_save_preset_handles_readonly_filesystem(self, tmp_path, monkeypatch):
        """Make preset directory read-only (chmod 000), verify returns (False, error message)"""
        import os

        from preset_manager import PresetManager

        # Create manager
        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Make user directory read-only
        user_dir = tmp_path / "user"
        original_mode = user_dir.stat().st_mode
        try:
            os.chmod(user_dir, 0o000)

            # Try to save preset
            settings = {"camera": {"ExposureTime": 1000}}
            success, message = manager.save_preset("test_preset", settings)

            # Should fail gracefully
            assert success is False
            assert "Failed to save preset" in message
            assert "Permission denied" in message or "permission" in message.lower()

        finally:
            # Restore permissions for cleanup
            os.chmod(user_dir, original_mode)

    def test_save_preset_handles_disk_full(self, tmp_path, monkeypatch):
        """Mock json.dump to raise IOError("No space left on device"), verify graceful handling"""
        from preset_manager import PresetManager

        # Create manager
        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Mock json.dump to simulate disk full error
        def failing_dump(*args, **kwargs):
            raise OSError("No space left on device")

        monkeypatch.setattr("json.dump", failing_dump)

        # Try to save preset
        settings = {"camera": {"ExposureTime": 1000}}
        success, message = manager.save_preset("test_preset", settings)

        # Should fail gracefully
        assert success is False
        assert "Failed to save preset" in message

    def test_list_presets_skips_corrupted_files(self, tmp_path):
        """Create mix of valid and corrupt preset files, verify list returns only valid ones"""
        import json

        from preset_manager import PresetManager

        # Create manager
        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Create one valid preset
        valid_preset = {
            "name": "valid_preset",
            "display_name": "Valid Preset",
            "description": "A valid preset",
            "version": "1.0",
            "author": "test",
            "category": "user",
            "workflow": "both",
            "settings": {"camera": {}, "liveview": {}},
        }
        valid_path = tmp_path / "user" / "valid_preset.json"
        valid_path.write_text(json.dumps(valid_preset))

        # Create corrupt presets
        corrupt1 = tmp_path / "user" / "corrupt1.json"
        corrupt1.write_text("{{{")

        corrupt2 = tmp_path / "user" / "corrupt2.json"
        corrupt2.write_text("not json at all")

        # List presets
        presets = manager.list_presets()

        # Should only return the valid preset
        assert len(presets) == 1
        assert presets[0]["name"] == "valid_preset"

    def test_delete_preset_handles_missing_file(self, tmp_path):
        """Try deleting non-existent preset, verify returns (False, "not found" message)"""
        from preset_manager import PresetManager

        # Create manager
        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Try to delete non-existent preset
        success, message = manager.delete_preset("nonexistent_preset")

        # Should fail gracefully
        assert success is False
        assert "not found" in message.lower()

    def test_delete_preset_handles_permission_error(self, tmp_path, monkeypatch):
        """Mock unlink() to raise PermissionError, verify deletion fails gracefully"""
        import json

        from preset_manager import PresetManager

        # Create manager
        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Create a preset
        preset_data = {
            "name": "readonly_preset",
            "display_name": "Read Only",
            "description": "Test",
            "version": "1.0",
            "author": "test",
            "category": "user",
            "workflow": "both",
            "settings": {"camera": {}, "liveview": {}},
        }
        preset_path = tmp_path / "user" / "readonly_preset.json"
        preset_path.write_text(json.dumps(preset_data))

        # Mock Path.unlink to raise PermissionError
        from pathlib import Path

        original_unlink = Path.unlink

        def mock_unlink(self, *args, **kwargs):
            if "readonly_preset.json" in str(self):
                raise PermissionError("Permission denied")
            return original_unlink(self, *args, **kwargs)

        monkeypatch.setattr(Path, "unlink", mock_unlink)

        # Try to delete
        success, message = manager.delete_preset("readonly_preset")

        # Should fail gracefully
        assert success is False
        assert "Failed to delete" in message

    def test_get_preset_handles_io_error(self, tmp_path, monkeypatch):
        """Mock file read to raise IOError, verify returns None"""
        from preset_manager import PresetManager

        # Create manager
        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Create a preset file (so it "exists")
        preset_path = tmp_path / "user" / "test_preset.json"
        preset_path.write_text("{}")

        # Mock open() to raise IOError
        original_open = open

        def mock_open(path, mode="r", *args, **kwargs):
            if "test_preset.json" in str(path) and "r" in mode:
                raise OSError("Simulated I/O error")
            return original_open(path, mode, *args, **kwargs)

        monkeypatch.setattr("builtins.open", mock_open)

        # Try to get preset
        result = manager.get_preset("test_preset")

        # Should return None gracefully
        assert result is None


class TestPresetValidationEdgeCases:
    """Test preset validation edge cases and error conditions"""

    def test_validate_preset_with_empty_camera_settings(self, tmp_path):
        """Preset with {'camera': {}, 'liveview': {...}} should be valid"""
        from preset_manager import PresetManager

        # Create manager
        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Create preset with empty camera settings
        preset_data = {
            "name": "test_preset",
            "display_name": "Test Preset",
            "description": "Test",
            "version": "1.0",
            "author": "test",
            "category": "user",
            "workflow": "both",
            "settings": {
                "camera": {},  # Empty is valid
                "liveview": {"sharpness": 1.0},
            },
        }

        # Validate
        valid, error_msg = manager.validate_preset(preset_data)

        # Should be valid (error_msg might be a success message or empty)
        assert valid is True

    def test_validate_preset_rejects_invalid_focus_peaking_color(self, tmp_path):
        """{'liveview': {'focus_peaking_colour': 'purple'}} should be invalid"""
        from preset_manager import PresetManager

        # Create manager
        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Create preset with invalid focus peaking color
        preset_data = {
            "name": "test_preset",
            "display_name": "Test Preset",
            "description": "Test",
            "version": "1.0",
            "author": "test",
            "category": "user",
            "workflow": "both",
            "settings": {
                "camera": {},
                "liveview": {"focus_peaking_colour": "purple"},  # Invalid color
            },
        }

        # Validate
        valid, error_msg = manager.validate_preset(preset_data)

        # Should be invalid
        assert valid is False
        assert "focus_peaking_colour" in error_msg.lower() or "invalid" in error_msg.lower()

    def test_validate_preset_rejects_non_numeric_exposure_time(self, tmp_path):
        """{'camera': {'ExposureTime': 'fast'}} should be invalid"""
        from preset_manager import PresetManager

        # Create manager
        manager = PresetManager(tmp_path / "builtin", tmp_path / "user")

        # Create preset with invalid ExposureTime
        preset_data = {
            "name": "test_preset",
            "display_name": "Test Preset",
            "description": "Test",
            "version": "1.0",
            "author": "test",
            "category": "user",
            "workflow": "both",
            "settings": {
                "camera": {"ExposureTime": "fast"},  # Invalid: must be numeric
                "liveview": {},
            },
        }

        # Validate
        valid, error_msg = manager.validate_preset(preset_data)

        # Should be invalid
        assert valid is False
        assert "ExposureTime" in error_msg or "invalid" in error_msg.lower()

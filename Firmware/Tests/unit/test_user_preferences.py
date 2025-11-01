"""
Unit tests for UserPreferencesManager (Issue #78 - Phase 1)

Tests the UserPreferencesManager class directly, covering file I/O,
JSON persistence, validation, and preset reference cleanup.

This complements test_preferences_routes.py which tests the REST API endpoints.

Coverage Target: 85%+ (user_preferences.py is 182 lines)
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# Import the manager class
from webui.backend.user_preferences import UserPreferencesManager, DEFAULT_PREFERENCES


# ============================================================================
# Test Class 1: Initialization & File Management (5 tests)
# ============================================================================

class TestUserPreferencesManagerInit:
    """Test manager initialization and file creation"""

    def test_creates_file_with_defaults_if_missing(self, tmp_path):
        """Manager creates preferences file with defaults if it doesn't exist"""
        prefs_file = tmp_path / "new_preferences.json"
        assert not prefs_file.exists()

        # Create manager
        manager = UserPreferencesManager(prefs_file)

        # Verify file was created
        assert prefs_file.exists()

        # Verify contents are defaults
        with open(prefs_file, 'r') as f:
            contents = json.load(f)
        assert contents == DEFAULT_PREFERENCES

    def test_creates_parent_directories_if_needed(self, tmp_path):
        """Manager creates parent directories if they don't exist"""
        nested_path = tmp_path / "config" / "mothbox" / "preferences.json"
        assert not nested_path.parent.exists()

        # Create manager
        manager = UserPreferencesManager(nested_path)

        # Verify parent directories were created
        assert nested_path.parent.exists()
        assert nested_path.exists()

    def test_loads_existing_file_correctly(self, tmp_path):
        """Manager loads existing preferences file"""
        prefs_file = tmp_path / "existing.json"
        existing_data = {
            "default_capture_preset": "wildlife",
            "default_preview_preset": "balanced",
            "default_liveview_preset": None
        }
        prefs_file.write_text(json.dumps(existing_data))

        # Create manager
        manager = UserPreferencesManager(prefs_file)

        # Get preferences
        prefs = manager.get_preferences()
        assert prefs["default_capture_preset"] == "wildlife"
        assert prefs["default_preview_preset"] == "balanced"

    def test_handles_empty_file(self, tmp_path):
        """Manager handles empty preferences file gracefully"""
        prefs_file = tmp_path / "empty.json"
        prefs_file.write_text("")

        # Create manager (should not crash)
        manager = UserPreferencesManager(prefs_file)

        # Should return defaults when file is empty
        prefs = manager.get_preferences()
        assert prefs == DEFAULT_PREFERENCES

    def test_handles_corrupted_json(self, tmp_path, capsys):
        """Manager handles corrupted JSON file and falls back to defaults"""
        prefs_file = tmp_path / "corrupted.json"
        prefs_file.write_text("{ invalid json here }")

        # Create manager (should not crash)
        manager = UserPreferencesManager(prefs_file)

        # Should return defaults when JSON is corrupted
        prefs = manager.get_preferences()
        assert prefs == DEFAULT_PREFERENCES

        # Should print warning message
        captured = capsys.readouterr()
        assert "Warning: Could not load preferences" in captured.out


# ============================================================================
# Test Class 2: get_preferences() Method (4 tests)
# ============================================================================

class TestUserPreferencesManagerGet:
    """Test get_preferences() method"""

    def test_returns_all_preferences_with_defaults_merged(self, tmp_path):
        """get_preferences() returns all preferences with defaults merged"""
        prefs_file = tmp_path / "prefs.json"
        # Only set one preference
        prefs_file.write_text(json.dumps({"default_capture_preset": "daylight"}))

        manager = UserPreferencesManager(prefs_file)
        prefs = manager.get_preferences()

        # Should have the set preference
        assert prefs["default_capture_preset"] == "daylight"
        # Should have defaults for missing keys
        assert prefs["default_preview_preset"] is None
        assert prefs["default_liveview_preset"] is None

    def test_handles_missing_keys_adds_defaults(self, tmp_path):
        """get_preferences() adds missing default keys to old preference files"""
        prefs_file = tmp_path / "old_prefs.json"
        # Simulate old file missing some keys
        prefs_file.write_text(json.dumps({"default_capture_preset": "test"}))

        manager = UserPreferencesManager(prefs_file)
        prefs = manager.get_preferences()

        # All default keys should be present
        for key in DEFAULT_PREFERENCES.keys():
            assert key in prefs

    def test_handles_extra_keys_preserves_them(self, tmp_path):
        """get_preferences() preserves extra keys not in defaults"""
        prefs_file = tmp_path / "extra.json"
        data = {
            **DEFAULT_PREFERENCES,
            "custom_key": "custom_value",
            "another_custom": 123
        }
        prefs_file.write_text(json.dumps(data))

        manager = UserPreferencesManager(prefs_file)
        prefs = manager.get_preferences()

        # Extra keys should be preserved
        assert prefs["custom_key"] == "custom_value"
        assert prefs["another_custom"] == 123

    def test_returns_copy_not_reference(self, tmp_path):
        """get_preferences() returns a copy, not a reference"""
        prefs_file = tmp_path / "prefs.json"
        manager = UserPreferencesManager(prefs_file)

        # Get preferences twice
        prefs1 = manager.get_preferences()
        prefs2 = manager.get_preferences()

        # Modify first dict
        prefs1["default_capture_preset"] = "modified"

        # Second dict should be unchanged
        assert prefs2["default_capture_preset"] is None


# ============================================================================
# Test Class 3: set_preference() Method (6 tests)
# ============================================================================

class TestUserPreferencesManagerSet:
    """Test set_preference() method"""

    def test_sets_valid_preference_and_persists_to_file(self, tmp_path):
        """set_preference() sets valid preference and persists to file"""
        prefs_file = tmp_path / "prefs.json"
        manager = UserPreferencesManager(prefs_file)

        # Set preference
        result = manager.set_preference("default_capture_preset", "wildlife")
        assert result is True

        # Verify in-memory
        prefs = manager.get_preferences()
        assert prefs["default_capture_preset"] == "wildlife"

        # Verify persisted to file
        with open(prefs_file, 'r') as f:
            file_contents = json.load(f)
        assert file_contents["default_capture_preset"] == "wildlife"

    def test_rejects_unknown_keys(self, tmp_path, capsys):
        """set_preference() rejects unknown keys and returns False"""
        prefs_file = tmp_path / "prefs.json"
        manager = UserPreferencesManager(prefs_file)

        # Try to set unknown key
        result = manager.set_preference("unknown_key", "value")
        assert result is False

        # Should print warning
        captured = capsys.readouterr()
        assert "Unknown preference key" in captured.out

        # File should not contain unknown key
        with open(prefs_file, 'r') as f:
            file_contents = json.load(f)
        assert "unknown_key" not in file_contents

    def test_accepts_all_default_keys(self, tmp_path):
        """set_preference() accepts all default preset keys"""
        prefs_file = tmp_path / "prefs.json"
        manager = UserPreferencesManager(prefs_file)

        # Test all default keys
        test_values = {
            "default_capture_preset": "test_capture",
            "default_preview_preset": "test_preview",
            "default_liveview_preset": "test_liveview"
        }

        for key, value in test_values.items():
            result = manager.set_preference(key, value)
            assert result is True, f"Failed to set {key}"

        # Verify all persisted
        prefs = manager.get_preferences()
        for key, value in test_values.items():
            assert prefs[key] == value

    def test_handles_none_values_correctly(self, tmp_path):
        """set_preference() handles None values correctly"""
        prefs_file = tmp_path / "prefs.json"
        manager = UserPreferencesManager(prefs_file)

        # Set to non-None first
        manager.set_preference("default_capture_preset", "wildlife")
        assert manager.get_preference("default_capture_preset") == "wildlife"

        # Set to None
        result = manager.set_preference("default_capture_preset", None)
        assert result is True

        # Verify None is stored
        prefs = manager.get_preferences()
        assert prefs["default_capture_preset"] is None

        # Verify persisted as null in JSON
        with open(prefs_file, 'r') as f:
            file_contents = json.load(f)
        assert file_contents["default_capture_preset"] is None

    def test_handles_all_valid_types(self, tmp_path):
        """set_preference() handles all valid JSON types"""
        prefs_file = tmp_path / "prefs.json"
        manager = UserPreferencesManager(prefs_file)

        # Test string, None (all that are actually used in preferences)
        test_cases = [
            ("default_capture_preset", "string_value"),
            ("default_preview_preset", None),
            ("default_liveview_preset", "another_string"),
        ]

        for key, value in test_cases:
            result = manager.set_preference(key, value)
            assert result is True
            assert manager.get_preference(key) == value

    def test_returns_false_on_write_permission_errors(self, tmp_path, monkeypatch, capsys):
        """set_preference() returns False on write permission errors"""
        prefs_file = tmp_path / "prefs.json"
        manager = UserPreferencesManager(prefs_file)

        # Mock open() to raise IOError on write
        original_open = open
        def mock_open(*args, **kwargs):
            if 'w' in str(kwargs.get('mode', args[1] if len(args) > 1 else '')):
                raise IOError("Permission denied")
            return original_open(*args, **kwargs)

        with patch('builtins.open', mock_open):
            result = manager.set_preference("default_capture_preset", "test")

        # Should return False
        assert result is False

        # Should print error message
        captured = capsys.readouterr()
        assert "Error: Could not save preference" in captured.out


# ============================================================================
# Test Class 4: reset_preferences() Method (3 tests)
# ============================================================================

class TestUserPreferencesManagerReset:
    """Test reset_preferences() method"""

    def test_clears_all_preferences_to_defaults(self, tmp_path):
        """reset_preferences() clears all preferences to defaults"""
        prefs_file = tmp_path / "prefs.json"
        manager = UserPreferencesManager(prefs_file)

        # Set custom preferences
        manager.set_preference("default_capture_preset", "custom1")
        manager.set_preference("default_preview_preset", "custom2")

        # Reset
        result = manager.reset_preferences()
        assert result is True

        # Verify back to defaults
        prefs = manager.get_preferences()
        assert prefs == DEFAULT_PREFERENCES

    def test_overwrites_existing_file_completely(self, tmp_path):
        """reset_preferences() overwrites file with only defaults"""
        prefs_file = tmp_path / "prefs.json"
        manager = UserPreferencesManager(prefs_file)

        # Set custom preferences including extra keys
        custom_data = {
            **DEFAULT_PREFERENCES,
            "custom_key": "should_be_removed"
        }
        prefs_file.write_text(json.dumps(custom_data))

        # Reset
        manager.reset_preferences()

        # Read file directly
        with open(prefs_file, 'r') as f:
            file_contents = json.load(f)

        # Should only have defaults, no extra keys
        assert file_contents == DEFAULT_PREFERENCES
        assert "custom_key" not in file_contents

    def test_creates_file_if_missing_on_reset(self, tmp_path):
        """reset_preferences() creates file if it was deleted"""
        prefs_file = tmp_path / "deleted.json"
        manager = UserPreferencesManager(prefs_file)

        # Delete the file
        prefs_file.unlink()
        assert not prefs_file.exists()

        # Reset should recreate it
        result = manager.reset_preferences()
        assert result is True
        assert prefs_file.exists()

        # Verify contents
        with open(prefs_file, 'r') as f:
            contents = json.load(f)
        assert contents == DEFAULT_PREFERENCES


# ============================================================================
# Test Class 5: validate_preset_references() Method (3 tests)
# ============================================================================

class TestUserPreferencesManagerValidate:
    """Test validate_preset_references() method"""

    def test_keeps_valid_preset_references_unchanged(self, tmp_path):
        """validate_preset_references() keeps valid refs unchanged"""
        prefs_file = tmp_path / "prefs.json"
        manager = UserPreferencesManager(prefs_file)

        # Set preferences with preset names
        manager.set_preference("default_capture_preset", "wildlife_daylight")
        manager.set_preference("default_preview_preset", "balanced")

        # Mock preset manager to return these presets as valid
        mock_preset_mgr = Mock()
        mock_preset_mgr.list_presets.return_value = [
            {"name": "wildlife_daylight"},
            {"name": "balanced"},
            {"name": "other_preset"}
        ]

        # Validate
        result = manager.validate_preset_references(mock_preset_mgr)

        # Should report no cleanup needed
        assert result["cleaned"] is False
        assert result["removed_references"] == []
        assert result["preferences"]["default_capture_preset"] == "wildlife_daylight"
        assert result["preferences"]["default_preview_preset"] == "balanced"

    def test_removes_invalid_preset_references(self, tmp_path, capsys):
        """validate_preset_references() removes invalid preset refs and sets to None"""
        prefs_file = tmp_path / "prefs.json"
        manager = UserPreferencesManager(prefs_file)

        # Set preferences with preset names
        manager.set_preference("default_capture_preset", "deleted_preset")
        manager.set_preference("default_preview_preset", "also_deleted")

        # Mock preset manager to return empty list (all presets deleted)
        mock_preset_mgr = Mock()
        mock_preset_mgr.list_presets.return_value = []

        # Validate
        result = manager.validate_preset_references(mock_preset_mgr)

        # Should report cleanup performed
        assert result["cleaned"] is True
        assert len(result["removed_references"]) == 2
        assert ("default_capture_preset", "deleted_preset") in result["removed_references"]
        assert ("default_preview_preset", "also_deleted") in result["removed_references"]

        # Invalid refs should be set to None
        assert result["preferences"]["default_capture_preset"] is None
        assert result["preferences"]["default_preview_preset"] is None

        # Should print warnings
        captured = capsys.readouterr()
        assert "Removed invalid preset reference" in captured.out

    def test_returns_cleanup_report_correctly(self, tmp_path):
        """validate_preset_references() returns correct cleanup report"""
        prefs_file = tmp_path / "prefs.json"
        manager = UserPreferencesManager(prefs_file)

        # Set mix of valid and invalid
        manager.set_preference("default_capture_preset", "valid_preset")
        manager.set_preference("default_preview_preset", "invalid_preset")
        manager.set_preference("default_liveview_preset", None)  # None is always valid

        # Mock preset manager
        mock_preset_mgr = Mock()
        mock_preset_mgr.list_presets.return_value = [
            {"name": "valid_preset"}  # Only this one exists
        ]

        # Validate
        result = manager.validate_preset_references(mock_preset_mgr)

        # Verify report structure
        assert "cleaned" in result
        assert "removed_references" in result
        assert "preferences" in result

        # One invalid reference removed
        assert result["cleaned"] is True
        assert len(result["removed_references"]) == 1
        assert result["removed_references"][0] == ("default_preview_preset", "invalid_preset")

        # Valid ones unchanged, invalid set to None
        assert result["preferences"]["default_capture_preset"] == "valid_preset"
        assert result["preferences"]["default_preview_preset"] is None
        assert result["preferences"]["default_liveview_preset"] is None


# ============================================================================
# Test Class 6: Edge Cases (2 tests)
# ============================================================================

class TestUserPreferencesManagerEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_very_long_string_values(self, tmp_path):
        """Manager handles very long string values (10KB+)"""
        prefs_file = tmp_path / "prefs.json"
        manager = UserPreferencesManager(prefs_file)

        # Create 10KB string
        long_value = "x" * (10 * 1024)

        # Set preference with long value
        result = manager.set_preference("default_capture_preset", long_value)
        assert result is True

        # Verify persisted correctly
        retrieved = manager.get_preference("default_capture_preset")
        assert retrieved == long_value
        assert len(retrieved) == 10 * 1024

        # Verify file is valid JSON
        with open(prefs_file, 'r') as f:
            contents = json.load(f)
        assert contents["default_capture_preset"] == long_value

    def test_unicode_and_special_characters_in_values(self, tmp_path):
        """Manager handles unicode and special characters correctly"""
        prefs_file = tmp_path / "prefs.json"
        manager = UserPreferencesManager(prefs_file)

        # Test various special characters
        test_values = [
            "preset_with_emoji_🦋🌸",
            "preset_with_unicode_αβγ",
            'preset_with_quotes_"test"',
            "preset_with_newline_\\n_escaped",
            "preset_with_slash_/path/to/preset",
            "preset_with_backslash_\\test",
        ]

        for value in test_values:
            # Set preference
            result = manager.set_preference("default_capture_preset", value)
            assert result is True, f"Failed to set value: {value}"

            # Verify retrieved correctly
            retrieved = manager.get_preference("default_capture_preset")
            assert retrieved == value, f"Value mismatch for: {value}"

            # Verify file is valid JSON
            with open(prefs_file, 'r') as f:
                contents = json.load(f)
            assert contents["default_capture_preset"] == value


# ============================================================================
# Test Class 7: get_preference() Single Key Method (Bonus)
# ============================================================================

class TestUserPreferencesManagerGetSingle:
    """Test get_preference() method for single key retrieval"""

    def test_get_single_preference_value(self, tmp_path):
        """get_preference() returns single preference value"""
        prefs_file = tmp_path / "prefs.json"
        manager = UserPreferencesManager(prefs_file)

        # Set a preference
        manager.set_preference("default_capture_preset", "test_value")

        # Get single preference
        value = manager.get_preference("default_capture_preset")
        assert value == "test_value"

    def test_get_nonexistent_preference_returns_none(self, tmp_path):
        """get_preference() returns None for nonexistent keys"""
        prefs_file = tmp_path / "prefs.json"
        manager = UserPreferencesManager(prefs_file)

        # Get non-existent key
        value = manager.get_preference("nonexistent_key")
        assert value is None

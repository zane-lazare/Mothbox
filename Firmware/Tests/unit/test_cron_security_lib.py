"""
Unit tests for cron_security library (Issue #207 - Phase 0)

Tests the cron security utilities that provide whitelist-based validation
for schedulable Mothbox scripts, preventing command injection attacks.

Coverage Target: 85%+
"""

from pathlib import Path
from unittest.mock import patch

import pytest

# Import library under test
from webui.backend.lib.cron_security import (
    ACTION_TYPE_SCRIPTS,
    ALLOWED_SCRIPTS,
    get_allowed_script_keys,
    get_script_filename,
    get_script_key_for_action,
    get_validated_command,
    get_validated_script_path,
    is_mothbox_command,
    validate_script_key,
)

# ============================================================================
# Test ALLOWED_SCRIPTS Constant
# ============================================================================


class TestAllowedScripts:
    """Tests for ALLOWED_SCRIPTS whitelist constant."""

    def test_all_scripts_end_with_py(self):
        """All script filenames in whitelist should end with .py."""
        for key, filename in ALLOWED_SCRIPTS.items():
            assert filename.endswith(".py"), f"Script '{filename}' for key '{key}' should end with .py"

    def test_keys_are_lowercase(self):
        """All script keys should be lowercase."""
        for key in ALLOWED_SCRIPTS:
            assert key == key.lower(), f"Key '{key}' should be lowercase"

    def test_contains_core_scripts(self):
        """Whitelist should contain core Mothbox scripts."""
        core_scripts = ["takephoto", "scheduler", "backup"]
        for script_key in core_scripts:
            assert script_key in ALLOWED_SCRIPTS, f"Core script '{script_key}' missing from whitelist"

    def test_contains_gpio_scripts(self):
        """Whitelist should contain GPIO control scripts."""
        gpio_scripts = ["attract_on", "attract_off", "flash_on", "flash_off"]
        for script_key in gpio_scripts:
            assert script_key in ALLOWED_SCRIPTS, f"GPIO script '{script_key}' missing from whitelist"

    def test_contains_extended_scripts(self):
        """Whitelist should contain extended scheduler scripts."""
        extended_scripts = ["gps_sync", "update_display", "debug_mode", "stop_cron", "start_cron"]
        for script_key in extended_scripts:
            assert script_key in ALLOWED_SCRIPTS, f"Extended script '{script_key}' missing from whitelist"

    def test_whitelist_has_minimum_count(self):
        """Whitelist should have at least 12 scripts (expanded from original 6)."""
        assert len(ALLOWED_SCRIPTS) >= 12, f"Expected at least 12 scripts, found {len(ALLOWED_SCRIPTS)}"


# ============================================================================
# Test ACTION_TYPE_SCRIPTS Constant
# ============================================================================


class TestActionTypeScripts:
    """Tests for ACTION_TYPE_SCRIPTS mapping."""

    def test_contains_gpio_action_type(self):
        """Should have 'gpio' action type with GPIO scripts."""
        assert "gpio" in ACTION_TYPE_SCRIPTS
        gpio_scripts = ACTION_TYPE_SCRIPTS["gpio"]
        assert "attract_on" in gpio_scripts
        assert "attract_off" in gpio_scripts
        assert "flash_on" in gpio_scripts
        assert "flash_off" in gpio_scripts

    def test_contains_camera_action_type(self):
        """Should have 'camera' action type with takephoto."""
        assert "camera" in ACTION_TYPE_SCRIPTS
        camera_scripts = ACTION_TYPE_SCRIPTS["camera"]
        assert "takephoto" in camera_scripts

    def test_contains_gps_sync_action_type(self):
        """Should have 'gps_sync' action type."""
        assert "gps_sync" in ACTION_TYPE_SCRIPTS
        gps_scripts = ACTION_TYPE_SCRIPTS["gps_sync"]
        assert "sync" in gps_scripts

    def test_contains_service_action_type(self):
        """Should have 'service' action type with backup and display."""
        assert "service" in ACTION_TYPE_SCRIPTS
        service_scripts = ACTION_TYPE_SCRIPTS["service"]
        assert "backup" in service_scripts
        assert "update_display" in service_scripts


# ============================================================================
# Test validate_script_key Function
# ============================================================================


class TestValidateScriptKey:
    """Tests for validate_script_key function."""

    def test_valid_keys_return_true_none(self):
        """Valid script keys should return (True, None)."""
        valid_keys = ["takephoto", "scheduler", "backup", "attract_on", "flash_on"]
        for key in valid_keys:
            valid, error = validate_script_key(key)
            assert valid is True, f"Key '{key}' should be valid"
            assert error is None, f"Key '{key}' should have no error message"

    def test_invalid_keys_return_false_error(self):
        """Invalid script keys should return (False, error_message)."""
        invalid_keys = ["evil_script", "rm_rf", "not_a_script", "system32"]
        for key in invalid_keys:
            valid, error = validate_script_key(key)
            assert valid is False, f"Key '{key}' should be invalid"
            assert error is not None, f"Key '{key}' should have error message"

    def test_empty_string_returns_false(self):
        """Empty string should return (False, error_message)."""
        valid, error = validate_script_key("")
        assert valid is False
        assert error is not None

    def test_none_returns_false(self):
        """None should return (False, error_message)."""
        valid, error = validate_script_key(None)
        assert valid is False
        assert error is not None

    def test_error_message_lists_allowed_keys(self):
        """Error message should list allowed script keys."""
        valid, error = validate_script_key("invalid_key")
        assert valid is False
        # Error message should mention at least one allowed key
        assert "takephoto" in error.lower() or "allowed" in error.lower()


# ============================================================================
# Test get_script_filename Function
# ============================================================================


class TestGetScriptFilename:
    """Tests for get_script_filename function."""

    def test_returns_filename_for_valid_key(self):
        """Should return correct filename for valid script key."""
        assert get_script_filename("takephoto") == "TakePhoto.py"
        assert get_script_filename("scheduler") == "Scheduler.py"
        assert get_script_filename("attract_on") == "Attract_On.py"

    def test_returns_none_for_invalid_key(self):
        """Should return None for invalid script key."""
        assert get_script_filename("not_a_script") is None
        assert get_script_filename("") is None
        assert get_script_filename(None) is None


# ============================================================================
# Test get_validated_script_path Function
# ============================================================================


class TestGetValidatedScriptPath:
    """Tests for get_validated_script_path function."""

    def test_returns_path_for_valid_key(self):
        """Should return full path string for valid script key."""
        with patch("webui.backend.lib.cron_security.get_script_path") as mock_get_path:
            mock_get_path.return_value = Path("/opt/mothbox/TakePhoto.py")

            result = get_validated_script_path("takephoto")

            assert result == "/opt/mothbox/TakePhoto.py"
            mock_get_path.assert_called_once_with("TakePhoto.py")

    def test_raises_valueerror_for_invalid_key(self):
        """Should raise ValueError for invalid script key."""
        with pytest.raises(ValueError) as exc_info:
            get_validated_script_path("evil_script")

        assert "invalid" in str(exc_info.value).lower() or "allowed" in str(exc_info.value).lower()


# ============================================================================
# Test get_validated_command Function
# ============================================================================


class TestGetValidatedCommand:
    """Tests for get_validated_command function."""

    def test_returns_python3_command_format(self):
        """Should return proper /usr/bin/python3 command format."""
        with patch("webui.backend.lib.cron_security.get_script_path") as mock_get_path:
            mock_get_path.return_value = Path("/opt/mothbox/TakePhoto.py")

            result = get_validated_command("takephoto")

            assert result == "/usr/bin/python3 /opt/mothbox/TakePhoto.py"

    def test_raises_valueerror_for_invalid_key(self):
        """Should raise ValueError for invalid script key."""
        with pytest.raises(ValueError):
            get_validated_command("not_valid")

    def test_command_contains_expected_components(self):
        """Command should contain python3 and script path."""
        with patch("webui.backend.lib.cron_security.get_script_path") as mock_get_path:
            mock_get_path.return_value = Path("/opt/mothbox/Scheduler.py")

            result = get_validated_command("scheduler")

            assert "/usr/bin/python3" in result
            assert "Scheduler.py" in result


# ============================================================================
# Test is_mothbox_command Function
# ============================================================================


class TestIsMothboxCommand:
    """Tests for is_mothbox_command function."""

    def test_recognizes_mothbox_keyword_case_insensitive(self):
        """Should recognize 'mothbox' keyword case-insensitively."""
        assert is_mothbox_command("/usr/bin/python3 /opt/mothbox/script.py") is True
        assert is_mothbox_command("/usr/bin/python3 /opt/MOTHBOX/script.py") is True
        assert is_mothbox_command("Mothbox_script.py") is True

    def test_recognizes_takephoto_keyword(self):
        """Should recognize 'TakePhoto' in command."""
        assert is_mothbox_command("/usr/bin/python3 /home/pi/TakePhoto.py") is True
        assert is_mothbox_command("TakePhoto.py") is True

    def test_recognizes_mothbox_home_path(self):
        """Should recognize commands with MOTHBOX_HOME path."""
        with patch("webui.backend.lib.cron_security.MOTHBOX_HOME", Path("/opt/mothbox")):
            assert is_mothbox_command("/usr/bin/python3 /opt/mothbox/Scheduler.py") is True

    def test_rejects_system_commands(self):
        """Should reject commands that don't look like Mothbox jobs."""
        system_commands = [
            "/usr/bin/apt-get update",
            "/bin/rm -rf /home",
            "reboot",
            "/usr/bin/logrotate",
            "journalctl --vacuum-time=7d",
        ]
        for cmd in system_commands:
            assert is_mothbox_command(cmd) is False, f"Should reject system command: {cmd}"

    def test_rejects_empty_command(self):
        """Should return False for empty command."""
        assert is_mothbox_command("") is False
        assert is_mothbox_command(None) is False


# ============================================================================
# Test get_script_key_for_action Function
# ============================================================================


class TestGetScriptKeyForAction:
    """Tests for get_script_key_for_action function."""

    def test_gpio_attract_on_returns_key(self):
        """Should return script key for GPIO attract_on action."""
        result = get_script_key_for_action("gpio", "attract_on")
        assert result == "attract_on"

    def test_gpio_flash_off_returns_key(self):
        """Should return script key for GPIO flash_off action."""
        result = get_script_key_for_action("gpio", "flash_off")
        assert result == "flash_off"

    def test_camera_takephoto_returns_key(self):
        """Should return script key for camera takephoto action."""
        result = get_script_key_for_action("camera", "takephoto")
        assert result == "takephoto"

    def test_gps_sync_returns_key(self):
        """Should return script key for gps_sync action."""
        result = get_script_key_for_action("gps_sync", "sync")
        assert result == "gps_sync"

    def test_service_backup_returns_key(self):
        """Should return script key for service backup action."""
        result = get_script_key_for_action("service", "backup")
        assert result == "backup"

    def test_unknown_action_type_returns_none(self):
        """Should return None for unknown action type."""
        result = get_script_key_for_action("unknown_type", "some_action")
        assert result is None

    def test_unknown_action_name_returns_none(self):
        """Should return None for unknown action name."""
        result = get_script_key_for_action("gpio", "unknown_action")
        assert result is None


# ============================================================================
# Test get_allowed_script_keys Function
# ============================================================================


class TestGetAllowedScriptKeys:
    """Tests for get_allowed_script_keys function."""

    def test_returns_list_of_all_keys(self):
        """Should return a list of all allowed script keys."""
        keys = get_allowed_script_keys()
        assert isinstance(keys, list)
        assert len(keys) >= 12  # Expanded whitelist

    def test_list_matches_allowed_scripts_dict(self):
        """Returned list should match ALLOWED_SCRIPTS dictionary keys."""
        keys = get_allowed_script_keys()
        assert set(keys) == set(ALLOWED_SCRIPTS.keys())

    def test_list_contains_core_keys(self):
        """Returned list should contain core script keys."""
        keys = get_allowed_script_keys()
        assert "takephoto" in keys
        assert "scheduler" in keys
        assert "backup" in keys

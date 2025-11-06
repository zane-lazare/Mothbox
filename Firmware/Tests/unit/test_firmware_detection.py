"""
Unit Tests: Firmware Version Detection (mothbox_paths.py)

Tests the firmware version detection and TakePhoto.py path resolution
functions added to support Issue #45 calibration architecture.

Key functionality tested:
- get_firmware_version(): Detects 4.x vs 5.x from controls.txt
- get_takephoto_script(): Returns correct TakePhoto.py path
- Fallback behavior when controls.txt missing or invalid
- Error messages include helpful firmware version context

Related: Issue #45, PR #55 - Camera Calibration Architecture

Run with: pytest Tests/unit/test_firmware_detection.py -v
"""

import pytest
from pathlib import Path
from unittest.mock import patch, mock_open


class TestFirmwareVersionDetection:
    """Unit tests for get_firmware_version() function"""

    def test_detects_4x_firmware(self, tmp_path, monkeypatch):
        """Test detection of 4.x firmware from controls.txt"""
        # Create mock controls.txt with 4.x version
        controls_file = tmp_path / "controls.txt"
        controls_file.write_text("softwareversion=4.0.0\n")

        # Patch mothbox_paths to use our test file
        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', controls_file)

        # Test
        from mothbox_paths import get_firmware_version
        version = get_firmware_version()

        assert version == "4", f"Expected '4', got '{version}'"
        print(f"   ✓ Detected firmware version: {version}.x")

    def test_detects_5x_firmware(self, tmp_path, monkeypatch):
        """Test detection of 5.x firmware from controls.txt"""
        # Create mock controls.txt with 5.x version
        controls_file = tmp_path / "controls.txt"
        controls_file.write_text("softwareversion=5.0.0\n")

        # Patch mothbox_paths to use our test file
        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', controls_file)

        # Test
        from mothbox_paths import get_firmware_version
        version = get_firmware_version()

        assert version == "5", f"Expected '5', got '{version}'"
        print(f"   ✓ Detected firmware version: {version}.x")

    def test_fallback_when_controls_txt_missing(self, tmp_path, monkeypatch):
        """Test fallback to 5.x when controls.txt doesn't exist"""
        # Point to non-existent file
        controls_file = tmp_path / "nonexistent_controls.txt"

        # Patch mothbox_paths
        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', controls_file)

        # Test
        from mothbox_paths import get_firmware_version
        version = get_firmware_version()

        assert version == "5", "Should fallback to '5' when controls.txt missing"
        print(f"   ✓ Fallback to {version}.x when controls.txt missing")

    def test_fallback_when_version_invalid(self, tmp_path, monkeypatch):
        """Test fallback to 5.x when version format is invalid"""
        # Create mock controls.txt with invalid version
        controls_file = tmp_path / "controls.txt"
        controls_file.write_text("softwareversion=99.0.0\n")

        # Patch mothbox_paths
        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', controls_file)

        # Test
        from mothbox_paths import get_firmware_version
        version = get_firmware_version()

        assert version == "5", "Should fallback to '5' for invalid version"
        print(f"   ✓ Fallback to {version}.x for invalid version 99.0.0")

    def test_fallback_when_softwareversion_key_missing(self, tmp_path, monkeypatch):
        """Test fallback to 5.x when softwareversion key is missing"""
        # Create mock controls.txt without softwareversion key
        controls_file = tmp_path / "controls.txt"
        controls_file.write_text("some_other_key=value\n")

        # Patch mothbox_paths
        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', controls_file)

        # Test
        from mothbox_paths import get_firmware_version
        version = get_firmware_version()

        assert version == "5", "Should fallback to '5' when key missing"
        print(f"   ✓ Fallback to {version}.x when softwareversion key missing")

    def test_handles_malformed_controls_txt(self, tmp_path, monkeypatch):
        """Test handles malformed controls.txt gracefully"""
        # Create mock controls.txt with malformed content
        controls_file = tmp_path / "controls.txt"
        controls_file.write_text("malformed content without equals signs\n")

        # Patch mothbox_paths
        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', controls_file)

        # Test
        from mothbox_paths import get_firmware_version
        version = get_firmware_version()

        assert version == "5", "Should fallback to '5' for malformed file"
        print(f"   ✓ Fallback to {version}.x for malformed controls.txt")

    def test_extracts_major_version_only(self, tmp_path, monkeypatch):
        """Test extracts major version from X.Y.Z format"""
        # Create mock controls.txt with full version
        controls_file = tmp_path / "controls.txt"
        controls_file.write_text("softwareversion=4.2.3\n")

        # Patch mothbox_paths
        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', controls_file)

        # Test
        from mothbox_paths import get_firmware_version
        version = get_firmware_version()

        assert version == "4", "Should extract major version only (4 from 4.2.3)"
        print(f"   ✓ Extracted major version {version} from 4.2.3")


class TestTakePhotoScriptResolution:
    """Unit tests for get_takephoto_script() function"""

    def test_returns_4x_path(self, tmp_path, monkeypatch):
        """Test returns correct path for 4.x firmware"""
        # Setup mock environment
        controls_file = tmp_path / "controls.txt"
        controls_file.write_text("softwareversion=4.0.0\n")

        mothbox_home = tmp_path / "mothbox"
        mothbox_home.mkdir()
        takephoto_dir = mothbox_home / "4.x"
        takephoto_dir.mkdir()
        takephoto_script = takephoto_dir / "TakePhoto.py"
        takephoto_script.write_text("# TakePhoto.py for 4.x\n")

        # Patch mothbox_paths
        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', controls_file)
        monkeypatch.setattr(mothbox_paths, 'MOTHBOX_HOME', mothbox_home)

        # Test
        from mothbox_paths import get_takephoto_script
        script_path = get_takephoto_script()

        assert script_path == takephoto_script, "Should return 4.x/TakePhoto.py path"
        assert script_path.exists(), "TakePhoto.py should exist"
        print(f"   ✓ Returned correct path: {script_path}")

    def test_returns_5x_path(self, tmp_path, monkeypatch):
        """Test returns correct path for 5.x firmware"""
        # Setup mock environment
        controls_file = tmp_path / "controls.txt"
        controls_file.write_text("softwareversion=5.0.0\n")

        mothbox_home = tmp_path / "mothbox"
        mothbox_home.mkdir()
        takephoto_dir = mothbox_home / "5.x"
        takephoto_dir.mkdir()
        takephoto_script = takephoto_dir / "TakePhoto.py"
        takephoto_script.write_text("# TakePhoto.py for 5.x\n")

        # Patch mothbox_paths
        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', controls_file)
        monkeypatch.setattr(mothbox_paths, 'MOTHBOX_HOME', mothbox_home)

        # Test
        from mothbox_paths import get_takephoto_script
        script_path = get_takephoto_script()

        assert script_path == takephoto_script, "Should return 5.x/TakePhoto.py path"
        assert script_path.exists(), "TakePhoto.py should exist"
        print(f"   ✓ Returned correct path: {script_path}")

    def test_raises_filenotfound_when_takephoto_missing(self, tmp_path, monkeypatch):
        """Test raises FileNotFoundError when TakePhoto.py doesn't exist"""
        # Setup mock environment WITHOUT TakePhoto.py
        controls_file = tmp_path / "controls.txt"
        controls_file.write_text("softwareversion=5.0.0\n")

        mothbox_home = tmp_path / "mothbox"
        mothbox_home.mkdir()
        # Create directory but NOT the TakePhoto.py file
        takephoto_dir = mothbox_home / "5.x"
        takephoto_dir.mkdir()

        # Patch mothbox_paths
        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', controls_file)
        monkeypatch.setattr(mothbox_paths, 'MOTHBOX_HOME', mothbox_home)

        # Test
        from mothbox_paths import get_takephoto_script

        with pytest.raises(FileNotFoundError) as exc_info:
            get_takephoto_script()

        print(f"   ✓ Raised FileNotFoundError: {exc_info.value}")

    def test_error_message_includes_firmware_version(self, tmp_path, monkeypatch):
        """Test error message includes detected firmware version"""
        # Setup mock environment
        controls_file = tmp_path / "controls.txt"
        controls_file.write_text("softwareversion=4.0.0\n")

        mothbox_home = tmp_path / "mothbox"
        mothbox_home.mkdir()

        # Patch mothbox_paths
        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', controls_file)
        monkeypatch.setattr(mothbox_paths, 'MOTHBOX_HOME', mothbox_home)

        # Test
        from mothbox_paths import get_takephoto_script

        with pytest.raises(FileNotFoundError) as exc_info:
            get_takephoto_script()

        error_msg = str(exc_info.value)
        assert "4.x" in error_msg, "Error message should include firmware version"
        assert "TakePhoto.py" in error_msg, "Error message should mention TakePhoto.py"
        print(f"   ✓ Error message includes firmware version: {error_msg[:100]}...")

    def test_error_message_includes_expected_path(self, tmp_path, monkeypatch):
        """Test error message includes expected file path"""
        # Setup mock environment
        controls_file = tmp_path / "controls.txt"
        controls_file.write_text("softwareversion=5.0.0\n")

        mothbox_home = tmp_path / "mothbox"
        mothbox_home.mkdir()

        # Patch mothbox_paths
        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', controls_file)
        monkeypatch.setattr(mothbox_paths, 'MOTHBOX_HOME', mothbox_home)

        # Test
        from mothbox_paths import get_takephoto_script

        with pytest.raises(FileNotFoundError) as exc_info:
            get_takephoto_script()

        error_msg = str(exc_info.value)
        expected_path = mothbox_home / "5.x" / "TakePhoto.py"
        assert str(expected_path) in error_msg, "Error should include expected path"
        print(f"   ✓ Error message includes path: {expected_path}")


class TestExceptionHandlers:
    """
    Unit tests for exception handling in mothbox_paths.py.

    Lines tested:
    - 183-185: Exception handler in get_firmware_version()
    - 262: Invalid GPIO mode validation in _validate_gpio_pin()
    - 440-444: Exception handler in get_hardware_config()
    """

    def test_get_firmware_version_handles_exception(self, tmp_path, monkeypatch, capfd):
        """Test that get_firmware_version handles exceptions and prints warning"""
        # Lines tested: 183-185
        import mothbox_paths
        from unittest.mock import Mock, patch

        # Mock get_control_values to raise an exception
        def mock_get_control_values(filename):
            raise RuntimeError("Unexpected error reading file")

        monkeypatch.setattr(mothbox_paths, 'get_control_values', mock_get_control_values)

        # Call function - should not raise exception
        from mothbox_paths import get_firmware_version
        version = get_firmware_version()

        # Should fallback to "5"
        assert version == "5", "Should fallback to '5' on exception"

        # Verify warning was printed to stderr
        captured = capfd.readouterr()
        assert "Warning: Could not detect firmware version" in captured.err
        assert "Defaulting to 5.x" in captured.err
        assert "Unexpected error reading file" in captured.err
        print("✓ Exception in get_firmware_version() handled with warning and fallback")

    def test_validate_gpio_pin_invalid_mode(self):
        """Test that _validate_gpio_pin raises ValueError for invalid mode"""
        # Lines tested: 262
        from mothbox_paths import _validate_gpio_pin

        # Test with invalid mode
        with pytest.raises(ValueError) as exc_info:
            _validate_gpio_pin(10, 'test_pin', mode='INVALID')

        error_msg = str(exc_info.value)
        assert "Invalid GPIO mode" in error_msg
        assert "INVALID" in error_msg
        assert "Must be 'BCM' or 'BOARD'" in error_msg
        print("✓ Invalid GPIO mode raises ValueError with helpful message")

    def test_get_hardware_config_exception_fallback(self, tmp_path, monkeypatch, capfd):
        """Test that get_hardware_config handles exceptions with defaults"""
        # Lines tested: 440-444
        import mothbox_paths
        from unittest.mock import Mock, patch

        # Mock get_control_values to raise an exception
        def mock_get_control_values(filename):
            raise KeyError("Missing configuration key")

        monkeypatch.setattr(mothbox_paths, 'get_control_values', mock_get_control_values)

        # Call function - should not raise exception
        from mothbox_paths import get_hardware_config
        hw_config = get_hardware_config()

        # Should return defaults
        assert hw_config is not None
        assert isinstance(hw_config, dict)

        # Verify default values (lines 444-477)
        assert hw_config['relay_enabled'] is True  # Relays enabled by default
        assert hw_config['ina260_enabled'] is False  # All other modules disabled
        assert hw_config['ina260_address'] == 0x40
        assert hw_config['epaper_enabled'] is False
        assert hw_config['epaper_rst_pin'] == 17
        assert hw_config['gps_enabled'] is False
        assert hw_config['gps_timeout'] == 60
        assert hw_config['gps_timeout_hot'] == 15
        assert hw_config['gps_timeout_warm'] == 60
        assert hw_config['gps_timeout_cold'] == 90
        assert hw_config['gps_timeout_almanac'] == 1200
        assert hw_config['light_sensor_enabled'] is False
        assert hw_config['pca9536_enabled'] is False
        assert hw_config['mux_enabled'] is False

        # Verify warning was printed to stderr
        captured = capfd.readouterr()
        assert "Warning: Could not load hardware configuration" in captured.err
        assert "Using defaults" in captured.err
        assert "Missing configuration key" in captured.err
        print("✓ Exception in get_hardware_config() handled with warning and default values")

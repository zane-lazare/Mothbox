"""
Unit tests for mothbox_paths.py debug utilities.

This test module covers the debug/diagnostic functions in mothbox_paths.py,
specifically the print_paths() function and __main__ block execution.

Test Coverage:
- print_paths() function (Lines 555-570: 16 lines)
- __main__ block (Lines 572-574: 3 lines)

The print_paths() function outputs all configured paths for debugging purposes.
These tests verify:
- All path constants are included in output
- Installation type is displayed
- Output formatting is correct
- __main__ block executes print_paths()

Testing approach:
- Use capfd to capture stdout output
- Use subprocess to test __main__ block execution
- Verify specific strings appear in output

Fixtures:
- capfd: Capture stdout/stderr for output verification

Related:
- Issue #13: https://github.com/zane-lazare/Mothbox/issues/13
- mothbox_paths.py: /home/zane/projects/Mothbox/Firmware/mothbox_paths.py
- Lines covered: 555-570, 572-574 (19 lines)
"""

import pytest
import subprocess
import sys
from pathlib import Path


class TestDebugUtilities:
    """
    Test print_paths() debug function and __main__ execution.

    Lines tested: 555-570 (print_paths function), 572-574 (__main__ block)

    The print_paths() function is a debug utility that outputs all configured
    paths to stdout. It's designed to help diagnose path configuration issues.
    """

    def test_print_paths_outputs_all_paths(self, capfd):
        """Test that print_paths() outputs all major path constants"""
        # Lines tested: 555-570 (entire print_paths function)
        import mothbox_paths

        # Call print_paths()
        mothbox_paths.print_paths()

        # Capture output
        captured = capfd.readouterr()
        output = captured.out

        # Verify header (lines 555-557)
        assert "=" * 60 in output
        assert "Mothbox Path Configuration" in output

        # Verify installation type is shown (line 558)
        assert "Installation Type:" in output
        assert mothbox_paths._installation_type in output

        # Verify all major paths are shown (lines 559-563)
        assert "MOTHBOX_HOME:" in output
        assert str(mothbox_paths.MOTHBOX_HOME) in output

        assert "CONFIG_DIR:" in output
        assert str(mothbox_paths.CONFIG_DIR) in output

        assert "DATA_DIR:" in output
        assert str(mothbox_paths.DATA_DIR) in output

        assert "FIRMWARE_DIR:" in output
        assert str(mothbox_paths.FIRMWARE_DIR) in output

        assert "PHOTOS_DIR:" in output
        assert str(mothbox_paths.PHOTOS_DIR) in output

        # Verify configuration files section (lines 564-569)
        assert "Configuration Files:" in output
        assert "Camera Settings:" in output
        assert str(mothbox_paths.CAMERA_SETTINGS_FILE) in output

        assert "Schedule:" in output
        assert str(mothbox_paths.SCHEDULE_SETTINGS_FILE) in output

        assert "Controls:" in output
        assert str(mothbox_paths.CONTROLS_FILE) in output

        assert "Wordlist:" in output
        assert str(mothbox_paths.WORDLIST_FILE) in output

        # Verify footer (line 570)
        assert output.count("=" * 60) >= 2  # Header and footer

        print("✓ print_paths() outputs all configured paths (lines 555-570)")

    def test_print_paths_shows_installation_type(self, capfd):
        """Test that print_paths() displays the installation type"""
        # Lines tested: 558 (installation type output)
        import mothbox_paths

        # Call print_paths()
        mothbox_paths.print_paths()

        # Capture output
        captured = capfd.readouterr()
        output = captured.out

        # Verify installation type is displayed
        assert "Installation Type:" in output

        # The installation type should be one of the valid types
        valid_types = ['test', 'production', 'legacy', 'custom']
        assert any(install_type in output for install_type in valid_types)

        # Verify it matches the actual installation type
        assert mothbox_paths._installation_type in output

        print(f"✓ Installation type '{mothbox_paths._installation_type}' shown (line 558)")

    def test_main_block_calls_print_paths(self):
        """Test that running module as script calls print_paths()"""
        # Lines tested: 572-574 (__main__ block)
        import mothbox_paths

        # Get path to mothbox_paths.py
        module_path = Path(mothbox_paths.__file__)

        # Run as script using subprocess
        result = subprocess.run(
            [sys.executable, str(module_path)],
            capture_output=True,
            text=True,
            timeout=5
        )

        # Should execute successfully
        assert result.returncode == 0, f"Script failed with stderr: {result.stderr}"

        # Should produce output
        assert len(result.stdout) > 0, "No output from script"

        # Output should contain path configuration (from print_paths)
        assert "Mothbox Path Configuration" in result.stdout
        assert "Installation Type:" in result.stdout
        assert "MOTHBOX_HOME:" in result.stdout
        assert "CONFIG_DIR:" in result.stdout
        assert "PHOTOS_DIR:" in result.stdout

        print("✓ __main__ block executes print_paths() (lines 572-574)")

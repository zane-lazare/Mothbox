"""
Unit Tests: Photo Calibration Wrapper Script

Tests the run_photo_calibration.py wrapper script that calls TakePhoto.py
via subprocess for photo calibration workflow.

Key functionality tested:
- Firmware version detection on import
- Error handling for missing TakePhoto.py
- Import error handling and messaging
- Helpful error messages with firmware context

Related: Issue #45, PR #55 - Camera Calibration Architecture

Run with: pytest Tests/unit/test_photo_calibration_wrapper.py -v
"""

import pytest
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestWrapperScriptBehavior:
    """Unit tests for run_photo_calibration.py wrapper script behavior"""

    def test_wrapper_detects_firmware_version(self, tmp_path, monkeypatch, capsys):
        """Test wrapper script detects firmware version on import"""
        # Setup mock environment
        controls_file = tmp_path / "controls.txt"
        controls_file.write_text("softwareversion=4.0.0\n")

        mothbox_home = tmp_path / "mothbox"
        mothbox_home.mkdir()

        # Create mock 4.x directory and TakePhoto.py
        takephoto_dir = mothbox_home / "4.x"
        takephoto_dir.mkdir()
        takephoto_script = takephoto_dir / "TakePhoto.py"
        takephoto_script.write_text("""
def run_calibration():
    print("Calibration completed")
""")

        # Patch environment variables
        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', controls_file)
        monkeypatch.setattr(mothbox_paths, 'MOTHBOX_HOME', mothbox_home)

        # Run wrapper script
        wrapper_script = Path(__file__).parent.parent.parent / 'webui' / 'backend' / 'scripts' / 'run_photo_calibration.py'

        result = subprocess.run(
            ['python3', str(wrapper_script)],
            capture_output=True,
            text=True,
            timeout=5
        )

        # Should print firmware version detection
        assert "4.x" in result.stdout or "firmware version: 4" in result.stdout.lower(), \
            "Wrapper should print detected firmware version"
        print(f"   ✓ Wrapper detected firmware version in output")

    def test_wrapper_handles_missing_takephoto(self, tmp_path, monkeypatch):
        """Test wrapper exits with error when TakePhoto.py missing"""
        # Setup mock environment WITHOUT TakePhoto.py
        controls_file = tmp_path / "controls.txt"
        controls_file.write_text("softwareversion=5.0.0\n")

        mothbox_home = tmp_path / "mothbox"
        mothbox_home.mkdir()

        # Patch environment
        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', controls_file)
        monkeypatch.setattr(mothbox_paths, 'MOTHBOX_HOME', mothbox_home)

        # Run wrapper script
        wrapper_script = Path(__file__).parent.parent.parent / 'webui' / 'backend' / 'scripts' / 'run_photo_calibration.py'

        result = subprocess.run(
            ['python3', str(wrapper_script)],
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode != 0, "Should exit with error code when TakePhoto.py missing"
        assert "TakePhoto.py" in result.stderr or "FileNotFoundError" in result.stderr, \
            "stderr should mention missing TakePhoto.py"
        print(f"   ✓ Wrapper exited with code {result.returncode}")
        print(f"   ✓ Error message: {result.stderr[:100]}...")

    def test_wrapper_error_includes_firmware_version(self, tmp_path, monkeypatch):
        """Test wrapper error messages include firmware version context"""
        # Setup mock environment
        controls_file = tmp_path / "controls.txt"
        controls_file.write_text("softwareversion=4.0.0\n")

        mothbox_home = tmp_path / "mothbox"
        mothbox_home.mkdir()

        # Patch environment
        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', controls_file)
        monkeypatch.setattr(mothbox_paths, 'MOTHBOX_HOME', mothbox_home)

        # Run wrapper script
        wrapper_script = Path(__file__).parent.parent.parent / 'webui' / 'backend' / 'scripts' / 'run_photo_calibration.py'

        result = subprocess.run(
            ['python3', str(wrapper_script)],
            capture_output=True,
            text=True,
            timeout=5
        )

        # Error should include firmware version context
        assert "4" in result.stderr or "4.x" in result.stderr, \
            "Error message should include detected firmware version"
        print(f"   ✓ Error includes firmware version context")

    def test_wrapper_handles_import_error_gracefully(self, tmp_path, monkeypatch):
        """Test wrapper handles TakePhoto.py import errors gracefully"""
        # Setup mock environment
        controls_file = tmp_path / "controls.txt"
        controls_file.write_text("softwareversion=5.0.0\n")

        mothbox_home = tmp_path / "mothbox"
        mothbox_home.mkdir()

        # Create mock 5.x directory with INVALID TakePhoto.py (syntax error)
        takephoto_dir = mothbox_home / "5.x"
        takephoto_dir.mkdir()
        takephoto_script = takephoto_dir / "TakePhoto.py"
        takephoto_script.write_text("invalid python syntax {{{")

        # Patch environment
        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', controls_file)
        monkeypatch.setattr(mothbox_paths, 'MOTHBOX_HOME', mothbox_home)

        # Run wrapper script
        wrapper_script = Path(__file__).parent.parent.parent / 'webui' / 'backend' / 'scripts' / 'run_photo_calibration.py'

        result = subprocess.run(
            ['python3', str(wrapper_script)],
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode != 0, "Should exit with error for import failure"
        assert "import" in result.stderr.lower() or "syntax" in result.stderr.lower(), \
            "stderr should indicate import/syntax error"
        print(f"   ✓ Wrapper handled import error")
        print(f"   ✓ Error: {result.stderr[:80]}...")


class TestWrapperErrorMessages:
    """Test wrapper script provides helpful error messages"""

    def test_filenotfound_error_message_helpful(self, tmp_path, monkeypatch):
        """Test FileNotFoundError message is helpful and actionable"""
        # Setup
        controls_file = tmp_path / "controls.txt"
        controls_file.write_text("softwareversion=5.0.0\n")

        mothbox_home = tmp_path / "mothbox"
        mothbox_home.mkdir()

        # Patch
        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', controls_file)
        monkeypatch.setattr(mothbox_paths, 'MOTHBOX_HOME', mothbox_home)

        # Run
        wrapper_script = Path(__file__).parent.parent.parent / 'webui' / 'backend' / 'scripts' / 'run_photo_calibration.py'

        result = subprocess.run(
            ['python3', str(wrapper_script)],
            capture_output=True,
            text=True,
            timeout=5
        )

        # Should have helpful error message
        assert "Expected TakePhoto.py at:" in result.stderr or "TakePhoto.py path:" in result.stderr, \
            "Error should show expected path"
        assert "Firmware version detected:" in result.stderr or "firmware version:" in result.stderr.lower(), \
            "Error should show detected firmware version"
        print(f"   ✓ Error message is helpful and includes context")

    def test_stderr_includes_traceback_for_debugging(self, tmp_path, monkeypatch):
        """Test stderr includes traceback for debugging unexpected errors"""
        # Setup mock environment with broken TakePhoto.py
        controls_file = tmp_path / "controls.txt"
        controls_file.write_text("softwareversion=5.0.0\n")

        mothbox_home = tmp_path / "mothbox"
        mothbox_home.mkdir()

        takephoto_dir = mothbox_home / "5.x"
        takephoto_dir.mkdir()
        takephoto_script = takephoto_dir / "TakePhoto.py"
        # Create TakePhoto.py that raises an exception
        takephoto_script.write_text("""
def run_calibration():
    raise RuntimeError("Test error for debugging")
""")

        # Patch
        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', controls_file)
        monkeypatch.setattr(mothbox_paths, 'MOTHBOX_HOME', mothbox_home)

        # Run
        wrapper_script = Path(__file__).parent.parent.parent / 'webui' / 'backend' / 'scripts' / 'run_photo_calibration.py'

        result = subprocess.run(
            ['python3', str(wrapper_script)],
            capture_output=True,
            text=True,
            timeout=5
        )

        # Should include traceback
        assert "Traceback" in result.stderr or "traceback" in result.stderr.lower(), \
            "stderr should include traceback for unexpected errors"
        assert "Test error for debugging" in result.stderr, \
            "stderr should include the actual error message"
        print(f"   ✓ Traceback included in stderr for debugging")

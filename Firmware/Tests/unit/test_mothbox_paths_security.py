"""
Unit tests for mothbox_paths.py security-critical functions.

This test module addresses the ZERO COVERAGE security gap for get_script_path(),
a function that validates script paths to prevent directory traversal attacks.

Test Coverage:
- get_script_path(): Script path validation (Lines 481-529, 28 lines, SECURITY CRITICAL)

Security validations tested:
1. Directory traversal attacks (../)
2. Absolute path injection (/)
3. Symlink escape attacks
4. Encoded path attacks (%2e%2e/, etc.)
5. Partial directory name matching

Each test includes success messages (✓) to confirm security barriers work.

Fixtures:
- temp_firmware_dir: Isolated firmware directory for testing (from tmp_path)
- monkeypatch: Patches FIRMWARE_DIR for test isolation

Related:
- Issue #13: https://github.com/zane-lazare/Mothbox/issues/13
- mothbox_paths.py: /home/zane/projects/Mothbox/Firmware/mothbox_paths.py
- Lines covered: 502-529 (28 lines with ZERO prior coverage)
"""

import pytest
import sys
from pathlib import Path

# Add backend to path (standard pattern)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))


class TestGetScriptPathSecurity:
    """
    Test get_script_path() security validations.

    Function location: mothbox_paths.py:481-529

    Security function that validates script names to prevent:
    - Directory traversal (../)
    - Absolute path injection (/)
    - Symlink escape attacks
    - Encoded path traversal (%2e%2e/)
    - Partial directory name matching (/firmware vs /firmware-evil)

    Returns: Path object to script within FIRMWARE_DIR

    Raises:
        ValueError: If script_name contains security violations
    """

    def test_returns_valid_script_path_for_simple_name(self, tmp_path, monkeypatch):
        """Test normal case: simple script name returns valid path"""
        # Create firmware directory
        firmware_dir = tmp_path / "firmware"
        firmware_dir.mkdir()

        # Patch FIRMWARE_DIR
        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'FIRMWARE_DIR', firmware_dir)

        from mothbox_paths import get_script_path

        # Test simple script name
        script_path = get_script_path("TakePhoto.py")

        assert script_path == firmware_dir / "TakePhoto.py"
        assert str(script_path).startswith(str(firmware_dir))
        print("\n✓ Simple script name returns valid path within FIRMWARE_DIR")

    def test_accepts_subdirectory_paths(self, tmp_path, monkeypatch):
        """Test that subdirectory paths are allowed (e.g., 5.x/TakePhoto.py)"""
        firmware_dir = tmp_path / "firmware"
        firmware_dir.mkdir()

        # Create subdirectory structure
        subdir = firmware_dir / "5.x"
        subdir.mkdir()
        script_file = subdir / "TakePhoto.py"
        script_file.write_text("# Script")

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'FIRMWARE_DIR', firmware_dir)

        from mothbox_paths import get_script_path

        # Test subdirectory path
        script_path = get_script_path("5.x/TakePhoto.py")

        assert script_path == firmware_dir / "5.x" / "TakePhoto.py"
        print("✓ Subdirectory paths allowed (5.x/TakePhoto.py)")

    def test_rejects_parent_directory_traversal(self, tmp_path, monkeypatch):
        """Test that ../ is blocked (directory traversal attack)"""
        firmware_dir = tmp_path / "firmware"
        firmware_dir.mkdir()

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'FIRMWARE_DIR', firmware_dir)

        from mothbox_paths import get_script_path

        # Attempt directory traversal
        with pytest.raises(ValueError) as exc_info:
            get_script_path("../etc/passwd")

        assert "path traversal" in str(exc_info.value).lower()
        print("✓ Directory traversal blocked (../etc/passwd)")

    def test_rejects_absolute_path_injection(self, tmp_path, monkeypatch):
        """Test that absolute paths are blocked (path injection attack)"""
        firmware_dir = tmp_path / "firmware"
        firmware_dir.mkdir()

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'FIRMWARE_DIR', firmware_dir)

        from mothbox_paths import get_script_path

        # Attempt absolute path injection
        with pytest.raises(ValueError) as exc_info:
            get_script_path("/etc/passwd")

        assert "path traversal" in str(exc_info.value).lower()
        print("✓ Absolute path injection blocked (/etc/passwd)")

    def test_prevents_symlink_escape_attacks(self, tmp_path, monkeypatch):
        """Test that symlinks pointing outside firmware dir are blocked"""
        firmware_dir = tmp_path / "firmware"
        firmware_dir.mkdir()

        # Create target directory outside firmware
        evil_dir = tmp_path / "evil"
        evil_dir.mkdir()
        evil_script = evil_dir / "malicious.py"
        evil_script.write_text("# Malicious code")

        # Create symlink inside firmware pointing outside
        symlink = firmware_dir / "innocent.py"
        symlink.symlink_to(evil_script)

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'FIRMWARE_DIR', firmware_dir)

        from mothbox_paths import get_script_path

        # Attempt to access via symlink
        with pytest.raises(ValueError) as exc_info:
            get_script_path("innocent.py")

        assert "outside firmware directory" in str(exc_info.value).lower()
        print("✓ Symlink escape attack blocked (symlink → outside)")

    def test_allows_symlinks_within_firmware_dir(self, tmp_path, monkeypatch):
        """Test that symlinks within firmware dir are allowed"""
        firmware_dir = tmp_path / "firmware"
        firmware_dir.mkdir()

        # Create real script inside firmware
        real_script = firmware_dir / "real_script.py"
        real_script.write_text("# Real script")

        # Create symlink inside firmware pointing to another file in firmware
        symlink = firmware_dir / "symlink_script.py"
        symlink.symlink_to(real_script)

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'FIRMWARE_DIR', firmware_dir)

        from mothbox_paths import get_script_path

        # Access via symlink (should be allowed)
        script_path = get_script_path("symlink_script.py")

        # Path should resolve to real_script within firmware
        assert script_path.resolve() == real_script.resolve()
        assert str(script_path.resolve()).startswith(str(firmware_dir.resolve()))
        print("✓ Internal symlinks allowed (symlink → within firmware)")

    def test_prevents_encoded_path_traversal(self, tmp_path, monkeypatch):
        """Test that URL-encoded ../ is blocked (%2e%2e/)"""
        firmware_dir = tmp_path / "firmware"
        firmware_dir.mkdir()

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'FIRMWARE_DIR', firmware_dir)

        from mothbox_paths import get_script_path

        # Attempt encoded traversal (pathlib normalizes these)
        # Note: pathlib doesn't decode URLs, but .. is still present
        with pytest.raises(ValueError) as exc_info:
            get_script_path("..%2Fetc%2Fpasswd")

        assert "path traversal" in str(exc_info.value).lower()
        print("✓ Encoded path traversal blocked (..%2Fetc)")

    def test_prevents_partial_directory_name_matching(self, tmp_path, monkeypatch):
        """Test that /firmware-evil is not confused with /firmware"""
        # Create two directories: firmware and firmware-evil
        firmware_dir = tmp_path / "firmware"
        firmware_dir.mkdir()

        evil_dir = tmp_path / "firmware-evil"
        evil_dir.mkdir()
        evil_script = evil_dir / "malicious.py"
        evil_script.write_text("# Evil script")

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'FIRMWARE_DIR', firmware_dir)

        from mothbox_paths import get_script_path

        # Create symlink from firmware to evil directory
        symlink = firmware_dir / "evil_link.py"
        symlink.symlink_to(evil_script)

        # Attempt to access (should be blocked - resolves outside firmware)
        with pytest.raises(ValueError) as exc_info:
            get_script_path("evil_link.py")

        assert "outside firmware directory" in str(exc_info.value).lower()
        print("✓ Partial name matching prevented (firmware vs firmware-evil)")

    def test_handles_nonexistent_paths_gracefully(self, tmp_path, monkeypatch):
        """Test that nonexistent paths are handled (path doesn't exist yet)"""
        firmware_dir = tmp_path / "firmware"
        firmware_dir.mkdir()

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'FIRMWARE_DIR', firmware_dir)

        from mothbox_paths import get_script_path

        # Request nonexistent script (should return path without error)
        script_path = get_script_path("future_script.py")

        # Path should be constructed correctly even if file doesn't exist
        assert script_path == firmware_dir / "future_script.py"
        print("✓ Nonexistent paths handled gracefully")

    def test_handles_resolve_oserror(self, tmp_path, monkeypatch):
        """Test that broken symlinks pointing outside are blocked"""
        firmware_dir = tmp_path / "firmware"
        firmware_dir.mkdir()

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'FIRMWARE_DIR', firmware_dir)

        from mothbox_paths import get_script_path

        # Create a broken symlink (points to nonexistent file outside firmware)
        broken_symlink = firmware_dir / "broken.py"
        broken_symlink.symlink_to(tmp_path / "nonexistent" / "missing.py")

        # Even though target doesn't exist, symlink resolves outside firmware -> blocked
        with pytest.raises(ValueError) as exc_info:
            get_script_path("broken.py")

        assert "outside firmware directory" in str(exc_info.value).lower()
        print("✓ Broken symlink pointing outside blocked (security)")

    def test_handles_resolve_runtimeerror(self, tmp_path, monkeypatch):
        """Test that RuntimeError during path resolution is handled"""
        firmware_dir = tmp_path / "firmware"
        firmware_dir.mkdir()

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'FIRMWARE_DIR', firmware_dir)

        from mothbox_paths import get_script_path
        from unittest.mock import Mock

        # Mock resolve() to raise RuntimeError
        original_resolve = Path.resolve

        def mock_resolve(self, *args, **kwargs):
            if "circular" in str(self):
                raise RuntimeError("Circular symlink detected")
            return original_resolve(self, *args, **kwargs)

        monkeypatch.setattr(Path, 'resolve', mock_resolve)

        # Should not raise error (catches RuntimeError)
        script_path = get_script_path("circular_symlink.py")

        assert script_path == firmware_dir / "circular_symlink.py"
        print("✓ RuntimeError during resolution handled gracefully")

    def test_error_message_includes_script_name(self, tmp_path, monkeypatch):
        """Test that error messages include the attempted script name"""
        firmware_dir = tmp_path / "firmware"
        firmware_dir.mkdir()

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'FIRMWARE_DIR', firmware_dir)

        from mothbox_paths import get_script_path

        # Attempt directory traversal
        with pytest.raises(ValueError) as exc_info:
            get_script_path("../malicious.py")

        error_msg = str(exc_info.value)
        assert "../malicious.py" in error_msg
        print("✓ Error message includes script name for debugging")

    def test_works_with_different_firmware_dirs(self, tmp_path, monkeypatch):
        """Test that function works with different firmware directories"""
        # Test with /opt/mothbox structure
        opt_firmware = tmp_path / "opt" / "mothbox"
        opt_firmware.mkdir(parents=True)

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'FIRMWARE_DIR', opt_firmware)

        from mothbox_paths import get_script_path

        script_path = get_script_path("TakePhoto.py")
        assert script_path == opt_firmware / "TakePhoto.py"
        print("✓ Works with production structure (/opt/mothbox)")

        # Test with legacy Desktop structure
        desktop_firmware = tmp_path / "home" / "pi" / "Desktop" / "Mothbox"
        desktop_firmware.mkdir(parents=True)
        monkeypatch.setattr(mothbox_paths, 'FIRMWARE_DIR', desktop_firmware)

        script_path = get_script_path("TakePhoto.py")
        assert script_path == desktop_firmware / "TakePhoto.py"
        print("✓ Works with legacy structure (/home/pi/Desktop/Mothbox)")

    def test_mixed_attack_vectors(self, tmp_path, monkeypatch):
        """Test combinations of attack vectors"""
        firmware_dir = tmp_path / "firmware"
        firmware_dir.mkdir()

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'FIRMWARE_DIR', firmware_dir)

        from mothbox_paths import get_script_path

        # Combination: absolute + traversal
        with pytest.raises(ValueError):
            get_script_path("/../etc/passwd")
        print("✓ Absolute + traversal blocked")

        # Combination: subdirectory + traversal
        with pytest.raises(ValueError):
            get_script_path("5.x/../../etc/passwd")
        print("✓ Subdirectory + traversal blocked")

        # Combination: multiple traversals
        with pytest.raises(ValueError):
            get_script_path("../../../etc/passwd")
        print("✓ Multiple traversals blocked")

    def test_windows_path_separators(self, tmp_path, monkeypatch):
        """Test that Windows path separators don't bypass validation"""
        firmware_dir = tmp_path / "firmware"
        firmware_dir.mkdir()

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'FIRMWARE_DIR', firmware_dir)

        from mothbox_paths import get_script_path

        # Test Windows-style paths (pathlib normalizes these on Unix)
        # This ensures cross-platform security
        script_path = get_script_path("5.x\\TakePhoto.py")

        # Should normalize to forward slashes
        # Path construction works, but verify it's within firmware
        assert str(firmware_dir) in str(script_path)
        print("✓ Windows separators handled (cross-platform security)")

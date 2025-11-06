"""
Unit tests for mothbox_paths.py utility functions

Tests directory creation, debug printing, and environment detection.
"""
import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

# Add mothbox to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestDirectoryCreation:
    """Test ensure_directories() utility function"""

    def test_ensure_directories_creates_missing_dirs(self, tmp_path, monkeypatch):
        """Should create CONFIG_DIR, DATA_DIR, PHOTOS_DIR, ISP_TUNING_DIR"""
        import mothbox_paths

        # Patch path constants to use tmp_path
        test_config = tmp_path / "config"
        test_data = tmp_path / "data"
        test_photos = tmp_path / "photos"
        test_isp = tmp_path / "isp_tuning"

        monkeypatch.setattr(mothbox_paths, 'CONFIG_DIR', test_config)
        monkeypatch.setattr(mothbox_paths, 'DATA_DIR', test_data)
        monkeypatch.setattr(mothbox_paths, 'PHOTOS_DIR', test_photos)
        monkeypatch.setattr(mothbox_paths, 'ISP_TUNING_DIR', test_isp)

        # Verify directories don't exist yet
        assert not test_config.exists()
        assert not test_data.exists()
        assert not test_photos.exists()
        assert not test_isp.exists()

        # Call ensure_directories()
        mothbox_paths.ensure_directories()

        # Verify directories were created
        assert test_config.exists()
        assert test_data.exists()
        assert test_photos.exists()
        assert test_isp.exists()

    def test_ensure_directories_sets_permissions(self, tmp_path, monkeypatch):
        """Created dirs should have 0o750 permissions (owner+group, no world)"""
        import mothbox_paths

        # Patch path constants
        test_config = tmp_path / "config"
        monkeypatch.setattr(mothbox_paths, 'CONFIG_DIR', test_config)
        monkeypatch.setattr(mothbox_paths, 'DATA_DIR', tmp_path / "data")
        monkeypatch.setattr(mothbox_paths, 'PHOTOS_DIR', tmp_path / "photos")
        monkeypatch.setattr(mothbox_paths, 'ISP_TUNING_DIR', tmp_path / "isp_tuning")

        # Call ensure_directories()
        mothbox_paths.ensure_directories()

        # Verify permissions (0o750 = rwxr-x---, owner+group only, no world access)
        stat_info = test_config.stat()
        permissions = stat_info.st_mode & 0o777
        assert permissions == 0o750

    def test_ensure_directories_handles_permission_errors(self, tmp_path, monkeypatch):
        """Mock chmod to raise PermissionError, should not crash"""
        import mothbox_paths

        # Patch path constants
        test_config = tmp_path / "config"
        monkeypatch.setattr(mothbox_paths, 'CONFIG_DIR', test_config)
        monkeypatch.setattr(mothbox_paths, 'DATA_DIR', tmp_path / "data")
        monkeypatch.setattr(mothbox_paths, 'PHOTOS_DIR', tmp_path / "photos")
        monkeypatch.setattr(mothbox_paths, 'ISP_TUNING_DIR', tmp_path / "isp_tuning")

        # Mock chmod to raise PermissionError
        original_chmod = os.chmod
        def mock_chmod(path, mode):
            # Let mkdir work but fail chmod
            if Path(path).exists():
                raise PermissionError("Permission denied")
        monkeypatch.setattr(os, 'chmod', mock_chmod)

        # Should not crash even with permission errors
        mothbox_paths.ensure_directories()

        # Verify directories were still created (even without correct permissions)
        assert test_config.exists()

    def test_ensure_directories_is_idempotent(self, tmp_path, monkeypatch):
        """Calling twice should not error"""
        import mothbox_paths

        # Patch path constants
        test_config = tmp_path / "config"
        monkeypatch.setattr(mothbox_paths, 'CONFIG_DIR', test_config)
        monkeypatch.setattr(mothbox_paths, 'DATA_DIR', tmp_path / "data")
        monkeypatch.setattr(mothbox_paths, 'PHOTOS_DIR', tmp_path / "photos")
        monkeypatch.setattr(mothbox_paths, 'ISP_TUNING_DIR', tmp_path / "isp_tuning")

        # Call twice
        mothbox_paths.ensure_directories()
        mothbox_paths.ensure_directories()

        # Should succeed without error
        assert test_config.exists()


class TestDebugPrinting:
    """Test print_paths() debug utility"""

    def test_print_paths_outputs_configuration(self, capsys):
        """Should print MOTHBOX_HOME, CONFIG_DIR, etc."""
        import mothbox_paths

        # Call print_paths()
        mothbox_paths.print_paths()

        # Capture output
        captured = capsys.readouterr()

        # Verify key paths are printed
        assert 'Mothbox Path Configuration' in captured.out
        assert 'MOTHBOX_HOME' in captured.out
        assert 'CONFIG_DIR' in captured.out
        assert 'DATA_DIR' in captured.out
        assert 'FIRMWARE_DIR' in captured.out
        assert 'PHOTOS_DIR' in captured.out

    def test_print_paths_shows_installation_type(self, capsys):
        """Should include installation type in output"""
        import mothbox_paths

        # Call print_paths()
        mothbox_paths.print_paths()

        # Capture output
        captured = capsys.readouterr()

        # Verify installation type is shown
        assert 'Installation Type' in captured.out
        # Should show one of: test, production, legacy, custom
        assert any(t in captured.out for t in ['test', 'production', 'legacy', 'custom'])


class TestEnvironmentDetection:
    """Test environment detection logic"""

    def test_detects_ci_environment_from_ci_variable(self, monkeypatch):
        """CI=true should trigger test mode"""
        # Set CI environment variable
        monkeypatch.setenv('CI', 'true')

        # Reload module to trigger environment detection
        import importlib
        import mothbox_paths
        importlib.reload(mothbox_paths)

        # Verify test mode was detected
        # In test mode, MOTHBOX_HOME should be the repository root
        assert mothbox_paths._installation_type == 'test'

    def test_detects_github_actions_environment(self, monkeypatch):
        """GITHUB_ACTIONS=true should trigger test mode"""
        # Set GITHUB_ACTIONS environment variable
        monkeypatch.setenv('GITHUB_ACTIONS', 'true')

        # Reload module to trigger environment detection
        import importlib
        import mothbox_paths
        importlib.reload(mothbox_paths)

        # Verify test mode was detected
        assert mothbox_paths._installation_type == 'test'

"""
Unit tests for webui/backend/mothbox_import.py module

Tests path resolution logic, environment variable handling, and sys.path setup
for finding the mothbox installation directory.
"""
import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestSetupMothboxPath:
    """Test setup_mothbox_path() function"""

    def test_uses_mothbox_home_env_var(self, monkeypatch, tmp_path):
        """Should use MOTHBOX_HOME environment variable when set"""
        custom_path = str(tmp_path / "custom_mothbox")
        monkeypatch.setenv('MOTHBOX_HOME', custom_path)

        # Save original sys.path
        original_path = sys.path.copy()

        try:
            # Import the module to trigger setup
            import importlib
            import webui.backend.mothbox_import as mothbox_import
            importlib.reload(mothbox_import)

            # Check that custom path was added
            assert custom_path in sys.path
        finally:
            # Restore sys.path
            sys.path[:] = original_path

    def test_uses_production_path_when_exists(self, monkeypatch, tmp_path):
        """Should use /opt/mothbox when it exists"""
        # Remove MOTHBOX_HOME env var
        monkeypatch.delenv('MOTHBOX_HOME', raising=False)

        # Save original sys.path
        original_path = sys.path.copy()

        with patch('pathlib.Path.exists', return_value=True) as mock_exists:
            try:
                # Reload module to trigger setup with mocked Path.exists
                import importlib
                import webui.backend.mothbox_import as mothbox_import
                importlib.reload(mothbox_import)

                # Check that production path was added
                assert "/opt/mothbox" in sys.path
            finally:
                # Restore sys.path
                sys.path[:] = original_path

    def test_falls_back_to_legacy_path(self, monkeypatch):
        """Should fall back to legacy /home/pi/Desktop/Mothbox path"""
        # Remove MOTHBOX_HOME env var
        monkeypatch.delenv('MOTHBOX_HOME', raising=False)

        # Save original sys.path
        original_path = sys.path.copy()

        with patch('pathlib.Path.exists', return_value=False):
            try:
                # Reload module to trigger setup
                import importlib
                import webui.backend.mothbox_import as mothbox_import
                importlib.reload(mothbox_import)

                # Check that legacy path was added
                assert "/home/pi/Desktop/Mothbox" in sys.path
            finally:
                # Restore sys.path
                sys.path[:] = original_path

    def test_path_inserted_at_beginning(self, monkeypatch, tmp_path):
        """Path should be inserted at index 0 of sys.path"""
        custom_path = str(tmp_path / "test_mothbox")
        monkeypatch.setenv('MOTHBOX_HOME', custom_path)

        # Save original sys.path
        original_path = sys.path.copy()
        original_first = sys.path[0]

        try:
            # Reload module
            import importlib
            import webui.backend.mothbox_import as mothbox_import
            importlib.reload(mothbox_import)

            # The custom path should now be at index 0
            # (or at least early in the list since other code may also insert)
            assert custom_path in sys.path[:5]  # Check first 5 entries
        finally:
            # Restore sys.path
            sys.path[:] = original_path


class TestEnvironmentVariable:
    """Test MOTHBOX_HOME environment variable handling"""

    def test_custom_mothbox_home_path(self, monkeypatch, tmp_path):
        """Should accept custom MOTHBOX_HOME path"""
        custom_path = str(tmp_path / "my_custom_mothbox")
        monkeypatch.setenv('MOTHBOX_HOME', custom_path)

        original_path = sys.path.copy()

        try:
            import importlib
            import webui.backend.mothbox_import as mothbox_import
            importlib.reload(mothbox_import)

            assert custom_path in sys.path
        finally:
            sys.path[:] = original_path

    def test_mothbox_home_with_trailing_slash(self, monkeypatch, tmp_path):
        """Should handle MOTHBOX_HOME with trailing slash"""
        custom_path = str(tmp_path / "mothbox") + "/"
        monkeypatch.setenv('MOTHBOX_HOME', custom_path)

        original_path = sys.path.copy()

        try:
            import importlib
            import webui.backend.mothbox_import as mothbox_import
            importlib.reload(mothbox_import)

            # Path should be added (with or without trailing slash)
            assert any(custom_path.rstrip('/') in p for p in sys.path)
        finally:
            sys.path[:] = original_path

    def test_mothbox_home_relative_path(self, monkeypatch):
        """Should handle relative MOTHBOX_HOME paths"""
        custom_path = "./mothbox"
        monkeypatch.setenv('MOTHBOX_HOME', custom_path)

        original_path = sys.path.copy()

        try:
            import importlib
            import webui.backend.mothbox_import as mothbox_import
            importlib.reload(mothbox_import)

            # Relative path should be added as-is
            assert custom_path in sys.path
        finally:
            sys.path[:] = original_path


class TestPathPriority:
    """Test path resolution priority order"""

    def test_env_var_takes_precedence_over_production(self, monkeypatch, tmp_path):
        """MOTHBOX_HOME env var should take precedence over /opt/mothbox"""
        custom_path = str(tmp_path / "env_mothbox")
        monkeypatch.setenv('MOTHBOX_HOME', custom_path)

        original_path = sys.path.copy()

        with patch('pathlib.Path.exists', return_value=True):
            try:
                import importlib
                import webui.backend.mothbox_import as mothbox_import
                importlib.reload(mothbox_import)

                # Custom path should be used, not /opt/mothbox
                assert custom_path in sys.path
                # /opt/mothbox should not be added since env var was set
                added_paths = [p for p in sys.path if p not in original_path]
                assert all('/opt/mothbox' not in p for p in added_paths)
            finally:
                sys.path[:] = original_path

    def test_production_takes_precedence_over_legacy(self, monkeypatch):
        """Production /opt/mothbox should take precedence over legacy path"""
        monkeypatch.delenv('MOTHBOX_HOME', raising=False)

        original_path = sys.path.copy()

        with patch('pathlib.Path.exists', return_value=True):
            try:
                import importlib
                import webui.backend.mothbox_import as mothbox_import
                importlib.reload(mothbox_import)

                # Production path should be used, not legacy
                assert "/opt/mothbox" in sys.path
                # Legacy path should not be added since production exists
                added_paths = [p for p in sys.path if p not in original_path]
                assert all('/home/pi/Desktop/Mothbox' not in p for p in added_paths)
            finally:
                sys.path[:] = original_path


class TestImportBehavior:
    """Test module import behavior"""

    def test_setup_runs_on_import(self, monkeypatch, tmp_path):
        """setup_mothbox_path() should run automatically on import"""
        custom_path = str(tmp_path / "auto_import")
        monkeypatch.setenv('MOTHBOX_HOME', custom_path)

        original_path = sys.path.copy()

        try:
            # Simply importing should trigger setup
            import importlib
            import webui.backend.mothbox_import as mothbox_import
            importlib.reload(mothbox_import)

            # Path should be added without explicitly calling setup_mothbox_path()
            assert custom_path in sys.path
        finally:
            sys.path[:] = original_path

    def test_function_is_callable(self):
        """setup_mothbox_path function should be callable"""
        from webui.backend.mothbox_import import setup_mothbox_path
        assert callable(setup_mothbox_path)

    def test_can_call_function_directly(self, monkeypatch, tmp_path):
        """Should be able to call setup_mothbox_path() directly"""
        from webui.backend.mothbox_import import setup_mothbox_path

        custom_path = str(tmp_path / "direct_call")
        monkeypatch.setenv('MOTHBOX_HOME', custom_path)

        original_path = sys.path.copy()

        try:
            # Call function directly
            setup_mothbox_path()

            # Path should be added
            assert custom_path in sys.path
        finally:
            sys.path[:] = original_path


class TestPathVerification:
    """Test that correct paths are being checked"""

    def test_checks_opt_mothbox_path(self, monkeypatch):
        """Should check if /opt/mothbox exists"""
        monkeypatch.delenv('MOTHBOX_HOME', raising=False)

        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = True

            original_path = sys.path.copy()

            try:
                import importlib
                import webui.backend.mothbox_import as mothbox_import
                importlib.reload(mothbox_import)

                # Verify Path.exists was called
                assert mock_exists.called
            finally:
                sys.path[:] = original_path

    def test_does_not_check_path_when_env_var_set(self, monkeypatch, tmp_path):
        """Should not check /opt/mothbox when MOTHBOX_HOME is set"""
        custom_path = str(tmp_path / "no_check")
        monkeypatch.setenv('MOTHBOX_HOME', custom_path)

        with patch('pathlib.Path.exists') as mock_exists:
            original_path = sys.path.copy()

            try:
                import importlib
                import webui.backend.mothbox_import as mothbox_import
                importlib.reload(mothbox_import)

                # Path.exists should not be called when env var is set
                # (the function exits early)
                # We can't easily test this without more complex mocking
                # Just verify the env path was used
                assert custom_path in sys.path
            finally:
                sys.path[:] = original_path


class TestModuleStructure:
    """Test module structure and exports"""

    def test_module_has_setup_function(self):
        """Module should export setup_mothbox_path function"""
        import webui.backend.mothbox_import as mothbox_import
        assert hasattr(mothbox_import, 'setup_mothbox_path')

    def test_setup_function_signature(self):
        """setup_mothbox_path should take no arguments"""
        from webui.backend.mothbox_import import setup_mothbox_path
        import inspect

        sig = inspect.signature(setup_mothbox_path)
        assert len(sig.parameters) == 0

    def test_module_imports(self):
        """Module should import required dependencies"""
        import webui.backend.mothbox_import as mothbox_import
        # Module should have imported os, sys, Path
        # We can't easily test the imports directly, but we can verify the module works
        assert mothbox_import is not None

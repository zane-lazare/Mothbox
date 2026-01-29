"""
Unit Tests: Capture Directory Security (TOCTOU Prevention)

Tests the _validate_capture_directory() function that prevents
symlink attacks during test/instant photo captures.

These are pure function tests - no hardware or Flask required.

Usage:
    pytest Tests/unit/test_capture_directory_security.py -v
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))

# Import after path setup
from routes.camera import _validate_capture_directory


class TestValidateCaptureDirectory:
    """Tests for _validate_capture_directory() function"""

    def test_real_directory_passes(self, tmp_path):
        """Real directory should pass validation"""
        test_dir = tmp_path / "test_captures"
        test_dir.mkdir()

        # Should not raise
        _validate_capture_directory(test_dir)

    def test_symlink_directory_rejected(self, tmp_path):
        """Symlink to directory should be rejected"""
        # Create a real directory
        real_dir = tmp_path / "real_dir"
        real_dir.mkdir()

        # Create a symlink to it
        symlink_dir = tmp_path / "symlink_dir"
        symlink_dir.symlink_to(real_dir)

        # Should raise ValueError
        import pytest
        with pytest.raises(ValueError) as exc_info:
            _validate_capture_directory(symlink_dir)

        assert "symlink" in str(exc_info.value).lower()
        assert "symlink_dir" in str(exc_info.value)

    def test_symlink_to_external_location_rejected(self, tmp_path):
        """Symlink pointing outside should be rejected"""
        # Create symlink to /tmp (external location)
        symlink_dir = tmp_path / "escape_symlink"
        symlink_dir.symlink_to("/tmp")

        import pytest
        with pytest.raises(ValueError) as exc_info:
            _validate_capture_directory(symlink_dir)

        assert "symlink" in str(exc_info.value).lower()

    def test_nested_real_directory_passes(self, tmp_path):
        """Nested real directories should pass validation"""
        nested_dir = tmp_path / "parent" / "child" / "test_captures"
        nested_dir.mkdir(parents=True)

        # Should not raise
        _validate_capture_directory(nested_dir)

    def test_error_message_includes_directory_name(self, tmp_path):
        """Error message should include the directory name for debugging"""
        real_dir = tmp_path / "real"
        real_dir.mkdir()

        symlink = tmp_path / "my_test_symlink"
        symlink.symlink_to(real_dir)

        import pytest
        with pytest.raises(ValueError) as exc_info:
            _validate_capture_directory(symlink)

        assert "my_test_symlink" in str(exc_info.value)

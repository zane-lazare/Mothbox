"""
Unit tests for security_utils.py

Tests path validation and error sanitization utilities.
"""

import logging
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from webui.backend.security_utils import validate_photo_path, sanitize_error_message


class TestValidatePhotoPath:
    """Tests for validate_photo_path function"""

    def test_valid_relative_path(self, tmp_path):
        """Valid relative path returns resolved Path"""
        base_dir = tmp_path / "photos"
        base_dir.mkdir()
        photo = base_dir / "photo.jpg"
        photo.write_text("photo content")

        result = validate_photo_path("photo.jpg", base_dir)

        assert result is not None
        assert result == photo.resolve()

    def test_valid_nested_path(self, tmp_path):
        """Valid nested path returns resolved Path"""
        base_dir = tmp_path / "photos"
        subdir = base_dir / "2024" / "11"
        subdir.mkdir(parents=True)
        photo = subdir / "photo.jpg"
        photo.write_text("photo content")

        result = validate_photo_path("2024/11/photo.jpg", base_dir)

        assert result is not None
        assert result == photo.resolve()

    def test_path_traversal_blocked(self, tmp_path):
        """Path traversal attempts return None"""
        base_dir = tmp_path / "photos"
        base_dir.mkdir()
        secret = tmp_path / "secret.txt"
        secret.write_text("secret")

        result = validate_photo_path("../secret.txt", base_dir)

        assert result is None

    def test_deep_path_traversal_blocked(self, tmp_path):
        """Deep path traversal attempts return None"""
        base_dir = tmp_path / "photos"
        base_dir.mkdir()

        result = validate_photo_path("../../etc/passwd", base_dir)

        assert result is None

    def test_absolute_path_blocked(self, tmp_path):
        """Absolute paths outside base return None"""
        base_dir = tmp_path / "photos"
        base_dir.mkdir()

        result = validate_photo_path("/etc/passwd", base_dir)

        assert result is None

    def test_nonexistent_file_returns_path(self, tmp_path):
        """Nonexistent but valid path returns resolved Path"""
        base_dir = tmp_path / "photos"
        base_dir.mkdir()

        # File doesn't exist but path is valid
        result = validate_photo_path("nonexistent.jpg", base_dir)

        # Should return the path (validation doesn't check existence)
        assert result is not None
        assert result == (base_dir / "nonexistent.jpg").resolve()

    # Symlink tests (covers lines 75-89)

    def test_symlink_within_base_is_valid(self, tmp_path):
        """Symlink pointing within base directory is allowed"""
        base_dir = tmp_path / "photos"
        base_dir.mkdir()
        real_file = base_dir / "real.jpg"
        real_file.write_text("photo content")

        symlink = base_dir / "link.jpg"
        symlink.symlink_to(real_file)

        result = validate_photo_path("link.jpg", base_dir)

        assert result is not None
        # Result should be the resolved symlink target
        assert result == real_file.resolve()

    def test_symlink_relative_within_base_is_valid(self, tmp_path):
        """Symlink with relative target within base is allowed"""
        base_dir = tmp_path / "photos"
        subdir = base_dir / "subdir"
        subdir.mkdir(parents=True)
        real_file = base_dir / "real.jpg"
        real_file.write_text("photo content")

        # Create symlink in subdir pointing relatively to parent
        symlink = subdir / "link.jpg"
        symlink.symlink_to(Path("../real.jpg"))

        result = validate_photo_path("subdir/link.jpg", base_dir)

        assert result is not None
        assert result == real_file.resolve()

    def test_symlink_absolute_outside_base_blocked(self, tmp_path):
        """Symlink to absolute path outside base returns None"""
        base_dir = tmp_path / "photos"
        base_dir.mkdir()
        outside_file = tmp_path / "secret.txt"
        outside_file.write_text("secret")

        symlink = base_dir / "link.jpg"
        symlink.symlink_to(outside_file.resolve())  # Absolute path outside

        result = validate_photo_path("link.jpg", base_dir)

        assert result is None

    def test_symlink_relative_escape_blocked(self, tmp_path):
        """Symlink with relative path escaping base returns None"""
        base_dir = tmp_path / "photos"
        base_dir.mkdir()
        outside_file = tmp_path / "secret.txt"
        outside_file.write_text("secret")

        symlink = base_dir / "link.jpg"
        symlink.symlink_to(Path("../secret.txt"))  # Relative escape

        result = validate_photo_path("link.jpg", base_dir)

        assert result is None

    def test_symlink_oserror_returns_none(self, tmp_path):
        """OSError during symlink resolution returns None"""
        base_dir = tmp_path / "photos"
        base_dir.mkdir()
        photo = base_dir / "photo.jpg"
        photo.write_text("photo content")

        # Create a broken symlink (target doesn't exist)
        symlink = base_dir / "broken_link.jpg"
        symlink.symlink_to(base_dir / "nonexistent.jpg")

        # Mock readlink to raise OSError
        with patch.object(Path, 'is_symlink', return_value=True):
            with patch.object(Path, 'readlink', side_effect=OSError("Permission denied")):
                result = validate_photo_path("photo.jpg", base_dir)

        assert result is None

    def test_symlink_valueerror_returns_none(self, tmp_path):
        """ValueError during symlink validation returns None"""
        base_dir = tmp_path / "photos"
        base_dir.mkdir()
        photo = base_dir / "photo.jpg"
        photo.write_text("photo content")

        # Mock to trigger ValueError in symlink validation
        with patch.object(Path, 'is_symlink', return_value=True):
            with patch.object(Path, 'readlink', return_value=Path("/outside/file")):
                with patch.object(Path, 'relative_to', side_effect=ValueError("Not relative")):
                    result = validate_photo_path("photo.jpg", base_dir)

        assert result is None

    def test_symlink_absolute_target_within_base(self, tmp_path):
        """Symlink with absolute target within base should pass (covers line 80-81)"""
        base_dir = tmp_path / "photos"
        base_dir.mkdir()
        real_file = base_dir / "real.jpg"
        real_file.write_text("photo content")

        # Mock to simulate absolute symlink target within base
        with patch.object(Path, 'is_symlink', return_value=True):
            with patch.object(Path, 'readlink', return_value=real_file.resolve()):
                result = validate_photo_path("photo.jpg", base_dir)

        # Should succeed since target is within base
        assert result is not None

    def test_symlink_relative_target_within_base(self, tmp_path):
        """Symlink with relative target within base should pass (covers line 82-85)"""
        base_dir = tmp_path / "photos"
        base_dir.mkdir()
        photo = base_dir / "photo.jpg"
        photo.write_text("photo content")

        # Mock to simulate relative symlink target within base
        with patch.object(Path, 'is_symlink', return_value=True):
            with patch.object(Path, 'readlink', return_value=Path("other.jpg")):
                result = validate_photo_path("photo.jpg", base_dir)

        # Should succeed since relative target resolves within base
        assert result is not None

    def test_outer_exception_valueerror(self, tmp_path):
        """ValueError in outer try block returns None (covers line 93-96)"""
        base_dir = tmp_path / "photos"
        base_dir.mkdir()

        # Mock resolve to raise ValueError
        with patch.object(Path, 'resolve', side_effect=ValueError("Invalid path")):
            result = validate_photo_path("photo.jpg", base_dir)

        assert result is None

    def test_outer_exception_runtimeerror(self, tmp_path):
        """RuntimeError in outer try block returns None (covers line 93-96)"""
        base_dir = tmp_path / "photos"
        base_dir.mkdir()

        # Mock resolve to raise RuntimeError (e.g., recursion limit)
        with patch.object(Path, 'resolve', side_effect=RuntimeError("Recursion limit")):
            result = validate_photo_path("photo.jpg", base_dir)

        assert result is None

    def test_outer_exception_oserror(self, tmp_path):
        """OSError in outer try block returns None (covers line 93-96)"""
        base_dir = tmp_path / "photos"
        base_dir.mkdir()

        # Mock resolve to raise OSError (e.g., permission denied)
        with patch.object(Path, 'resolve', side_effect=OSError("Permission denied")):
            result = validate_photo_path("photo.jpg", base_dir)

        assert result is None

    # Edge cases - these test the prefix validation failure path (lines 70-71)

    def test_empty_path_fails_prefix_check(self, tmp_path):
        """Empty path fails prefix validation (covers line 70-71)"""
        base_dir = tmp_path / "photos"
        base_dir.mkdir()

        result = validate_photo_path("", base_dir)

        # Empty string resolves to base_dir itself, which fails prefix check
        # because full_str doesn't start with base_str + os.sep
        assert result is None

    def test_dot_path_fails_prefix_check(self, tmp_path):
        """Single dot path fails prefix validation (covers line 70-71)"""
        base_dir = tmp_path / "photos"
        base_dir.mkdir()

        result = validate_photo_path(".", base_dir)

        # "." resolves to base_dir itself, which fails prefix check
        assert result is None


class TestSanitizeErrorMessage:
    """Tests for sanitize_error_message function"""

    def test_returns_generic_message(self):
        """Should return generic message, not exception details"""
        try:
            raise ValueError("Sensitive internal error details")
        except ValueError as e:
            result = sanitize_error_message(e, "File access error")

        assert result == "File access error"
        assert "Sensitive" not in result
        assert "internal" not in result

    def test_logs_full_error(self, caplog):
        """Should log full exception details"""
        with caplog.at_level(logging.ERROR):
            try:
                raise ValueError("Detailed error message")
            except ValueError as e:
                sanitize_error_message(e, "Generic error")

        # Check that the full error was logged
        assert "Generic error" in caplog.text
        assert "Detailed error message" in caplog.text

    def test_handles_different_exception_types(self):
        """Should handle various exception types"""
        exceptions = [
            ValueError("value error"),
            TypeError("type error"),
            RuntimeError("runtime error"),
            OSError("os error"),
        ]

        for exc in exceptions:
            result = sanitize_error_message(exc, "Generic message")
            assert result == "Generic message"

    def test_returns_exact_generic_message(self):
        """Should return exactly the generic message provided"""
        try:
            raise Exception("any error")
        except Exception as e:
            result = sanitize_error_message(e, "Exact message to return")

        assert result == "Exact message to return"

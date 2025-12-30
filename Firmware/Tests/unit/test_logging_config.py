"""
Unit tests for Mothbox Logging Configuration (Issue #37)

Tests centralized logging setup with:
- Log level configuration from controls.txt
- Rotating file handler with size limits
- Console output with coloredlogs
- Emoji stripping from log messages
- Thread-safe logging operations

Coverage Target: 85%+
"""

import logging
import os
import re
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import logging config module
try:
    from webui.backend.logging_config import (
        setup_mothbox_logging,
        strip_emojis,
        get_log_level_from_config,
        MOTHBOX_LOG_FORMAT,
        DEFAULT_LOG_LEVEL,
        DEFAULT_MAX_BYTES,
        DEFAULT_BACKUP_COUNT,
    )
    IMPLEMENTATION_EXISTS = True
except ImportError:
    IMPLEMENTATION_EXISTS = False
    setup_mothbox_logging = None
    strip_emojis = None
    get_log_level_from_config = None
    MOTHBOX_LOG_FORMAT = None
    DEFAULT_LOG_LEVEL = None
    DEFAULT_MAX_BYTES = None
    DEFAULT_BACKUP_COUNT = None

# Skip all tests if implementation doesn't exist yet
pytestmark = pytest.mark.skipif(
    not IMPLEMENTATION_EXISTS,
    reason="Implementation not yet created"
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_log_dir(tmp_path):
    """Create temporary directory for log files."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir


@pytest.fixture(autouse=True)
def cleanup_loggers():
    """Clean up any loggers created during tests."""
    yield
    # Remove all handlers from test loggers
    for name in list(logging.Logger.manager.loggerDict.keys()):
        if name.startswith("test_") or name.startswith("mothbox"):
            logger = logging.getLogger(name)
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)


# ============================================================================
# Tests: strip_emojis()
# ============================================================================

class TestStripEmojis:
    """Tests for emoji stripping utility function."""

    def test_strip_common_emojis(self):
        """Should remove common status emojis from messages."""
        assert strip_emojis("✓ Operation complete") == "Operation complete"
        assert strip_emojis("✗ Operation failed") == "Operation failed"
        assert strip_emojis("⚠️ Warning message") == "Warning message"
        assert strip_emojis("❌ Error occurred") == "Error occurred"
        assert strip_emojis("ℹ️ Info message") == "Info message"

    def test_strip_camera_emojis(self):
        """Should remove camera-related emojis from messages."""
        assert strip_emojis("🎥 Camera initialized") == "Camera initialized"
        assert strip_emojis("📸 Photo captured") == "Photo captured"
        assert strip_emojis("📷 Starting capture") == "Starting capture"

    def test_strip_multiple_emojis(self):
        """Should handle multiple emojis in same message."""
        assert strip_emojis("✓ 📸 Photo saved ✓") == "Photo saved"

    def test_preserve_non_emoji_text(self):
        """Should preserve regular text without emojis."""
        assert strip_emojis("Normal log message") == "Normal log message"
        assert strip_emojis("Value: 123.45") == "Value: 123.45"

    def test_empty_string(self):
        """Should handle empty strings."""
        assert strip_emojis("") == ""

    def test_only_emojis(self):
        """Should handle strings with only emojis."""
        result = strip_emojis("✓ ✗ ⚠️")
        assert result.strip() == ""

    def test_preserves_unicode_text(self):
        """Should preserve non-emoji unicode characters."""
        assert strip_emojis("Résumé: complete") == "Résumé: complete"
        assert strip_emojis("日本語テスト") == "日本語テスト"


# ============================================================================
# Tests: get_log_level_from_config()
# ============================================================================

class TestGetLogLevelFromConfig:
    """Tests for reading log level from controls.txt."""

    def test_reads_info_level(self):
        """Should read INFO level from controls.txt."""
        mock_controls = {"log_level": "INFO"}
        with patch("webui.backend.logging_config.get_control_values", return_value=mock_controls):
            level = get_log_level_from_config()
            assert level == logging.INFO

    def test_reads_debug_level(self):
        """Should read DEBUG level from controls.txt."""
        mock_controls = {"log_level": "DEBUG"}
        with patch("webui.backend.logging_config.get_control_values", return_value=mock_controls):
            level = get_log_level_from_config()
            assert level == logging.DEBUG

    def test_reads_warning_level(self):
        """Should read WARNING level from controls.txt."""
        mock_controls = {"log_level": "WARNING"}
        with patch("webui.backend.logging_config.get_control_values", return_value=mock_controls):
            level = get_log_level_from_config()
            assert level == logging.WARNING

    def test_reads_error_level(self):
        """Should read ERROR level from controls.txt."""
        mock_controls = {"log_level": "ERROR"}
        with patch("webui.backend.logging_config.get_control_values", return_value=mock_controls):
            level = get_log_level_from_config()
            assert level == logging.ERROR

    def test_case_insensitive(self):
        """Should handle case-insensitive level names."""
        mock_controls = {"log_level": "debug"}
        with patch("webui.backend.logging_config.get_control_values", return_value=mock_controls):
            level = get_log_level_from_config()
            assert level == logging.DEBUG

    def test_missing_config_returns_default(self):
        """Should return default level when controls.txt missing."""
        with patch("webui.backend.logging_config.get_control_values", side_effect=FileNotFoundError):
            level = get_log_level_from_config()
            assert level == logging.INFO  # Default

    def test_missing_key_returns_default(self):
        """Should return default level when log_level key missing."""
        mock_controls = {"other_key": "value"}
        with patch("webui.backend.logging_config.get_control_values", return_value=mock_controls):
            level = get_log_level_from_config()
            assert level == logging.INFO  # Default

    def test_invalid_level_returns_default(self):
        """Should return default level for invalid log level value."""
        mock_controls = {"log_level": "INVALID"}
        with patch("webui.backend.logging_config.get_control_values", return_value=mock_controls):
            level = get_log_level_from_config()
            assert level == logging.INFO  # Default

    def test_get_control_values_none(self):
        """Should return default when get_control_values is None."""
        with patch("webui.backend.logging_config.get_control_values", None):
            level = get_log_level_from_config()
            assert level == logging.INFO  # Default


# ============================================================================
# Tests: setup_mothbox_logging()
# ============================================================================

class TestSetupMothboxLogging:
    """Tests for main logging setup function."""

    def test_returns_logger(self, temp_log_dir):
        """Should return a logging.Logger instance."""
        logger = setup_mothbox_logging(
            name="test_logger_1",
            log_level="INFO",
            log_file=temp_log_dir / "test.log",
            console_output=False,
        )
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger_1"

    def test_sets_log_level(self, temp_log_dir):
        """Should set the specified log level."""
        logger = setup_mothbox_logging(
            name="test_logger_2",
            log_level="DEBUG",
            log_file=temp_log_dir / "test.log",
            console_output=False,
        )
        assert logger.level == logging.DEBUG

    def test_creates_log_file(self, temp_log_dir):
        """Should create log file and directory if needed."""
        log_file = temp_log_dir / "subdir" / "test.log"
        logger = setup_mothbox_logging(
            name="test_logger_3",
            log_level="INFO",
            log_file=log_file,
            console_output=False,
        )
        logger.info("Test message")
        # Flush handlers
        for handler in logger.handlers:
            handler.flush()
        assert log_file.exists()

    def test_log_format_includes_timestamp(self, temp_log_dir):
        """Should include timestamp in log format."""
        log_file = temp_log_dir / "test.log"
        logger = setup_mothbox_logging(
            name="test_logger_4",
            log_level="INFO",
            log_file=log_file,
            console_output=False,
        )
        logger.info("Test message")
        # Flush and close handlers
        for handler in logger.handlers:
            handler.flush()

        content = log_file.read_text()
        # Check for timestamp pattern (YYYY-MM-DD HH:MM:SS)
        assert re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", content)

    def test_log_format_includes_level(self, temp_log_dir):
        """Should include log level in format."""
        log_file = temp_log_dir / "test.log"
        logger = setup_mothbox_logging(
            name="test_logger_5",
            log_level="INFO",
            log_file=log_file,
            console_output=False,
        )
        logger.info("Test message")
        for handler in logger.handlers:
            handler.flush()

        content = log_file.read_text()
        assert "INFO" in content

    def test_log_format_includes_logger_name(self, temp_log_dir):
        """Should include logger name in format."""
        log_file = temp_log_dir / "test.log"
        logger = setup_mothbox_logging(
            name="test_logger_6",
            log_level="INFO",
            log_file=log_file,
            console_output=False,
        )
        logger.info("Test message")
        for handler in logger.handlers:
            handler.flush()

        content = log_file.read_text()
        assert "test_logger_6" in content

    def test_respects_log_level_filtering(self, temp_log_dir):
        """Should filter messages below log level."""
        log_file = temp_log_dir / "test.log"
        logger = setup_mothbox_logging(
            name="test_logger_7",
            log_level="WARNING",
            log_file=log_file,
            console_output=False,
        )
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        for handler in logger.handlers:
            handler.flush()

        content = log_file.read_text()
        assert "Debug message" not in content
        assert "Info message" not in content
        assert "Warning message" in content

    def test_multiple_calls_same_name(self, temp_log_dir):
        """Should reuse same logger for same name."""
        log_file = temp_log_dir / "test.log"
        logger1 = setup_mothbox_logging(
            name="test_logger_8",
            log_level="INFO",
            log_file=log_file,
            console_output=False,
        )
        logger2 = setup_mothbox_logging(
            name="test_logger_8",
            log_level="INFO",
            log_file=log_file,
            console_output=False,
        )
        assert logger1 is logger2


# ============================================================================
# Tests: Log Rotation
# ============================================================================

class TestLogRotation:
    """Tests for rotating file handler configuration."""

    def test_rotation_at_max_bytes(self, temp_log_dir):
        """Should rotate log file when max_bytes exceeded."""
        log_file = temp_log_dir / "test.log"
        max_bytes = 1024  # 1KB for fast rotation in test

        logger = setup_mothbox_logging(
            name="test_rotation_1",
            log_level="INFO",
            log_file=log_file,
            max_bytes=max_bytes,
            backup_count=3,
            console_output=False,
        )

        # Write enough to trigger rotation
        for i in range(100):
            logger.info(f"Message {i}: " + "x" * 50)

        for handler in logger.handlers:
            handler.flush()

        # Check backup files exist
        backup_files = list(temp_log_dir.glob("test.log.*"))
        assert len(backup_files) > 0, "Expected backup files after rotation"

    def test_respects_backup_count(self, temp_log_dir):
        """Should keep only backup_count backup files."""
        log_file = temp_log_dir / "test.log"
        max_bytes = 512  # Very small for fast rotation
        backup_count = 2

        logger = setup_mothbox_logging(
            name="test_rotation_2",
            log_level="INFO",
            log_file=log_file,
            max_bytes=max_bytes,
            backup_count=backup_count,
            console_output=False,
        )

        # Write lots of messages to force multiple rotations
        for i in range(200):
            logger.info(f"Message {i}: " + "x" * 50)

        for handler in logger.handlers:
            handler.flush()

        backup_files = list(temp_log_dir.glob("test.log.*"))
        assert len(backup_files) <= backup_count


# ============================================================================
# Tests: Thread Safety
# ============================================================================

class TestThreadSafety:
    """Tests for thread-safe logging operations."""

    def test_concurrent_logging(self, temp_log_dir):
        """Should handle concurrent logging from multiple threads."""
        log_file = temp_log_dir / "test.log"
        logger = setup_mothbox_logging(
            name="test_concurrent",
            log_level="INFO",
            log_file=log_file,
            console_output=False,
        )

        errors = []
        messages_per_thread = 50
        num_threads = 5

        def log_messages(thread_id):
            try:
                for i in range(messages_per_thread):
                    logger.info(f"Thread {thread_id} message {i}")
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=log_messages, args=(i,))
            for i in range(num_threads)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors during concurrent logging: {errors}"

        for handler in logger.handlers:
            handler.flush()

        # Verify all messages were logged
        content = log_file.read_text()
        for thread_id in range(num_threads):
            assert f"Thread {thread_id}" in content


# ============================================================================
# Tests: Console Output
# ============================================================================

class TestConsoleOutput:
    """Tests for console (stdout) logging output."""

    def test_console_output_enabled(self, temp_log_dir, capsys):
        """Should output to console when enabled."""
        logger = setup_mothbox_logging(
            name="test_console_1",
            log_level="INFO",
            log_file=temp_log_dir / "test.log",
            console_output=True,
        )
        logger.info("Console test message")

        # Flush handlers
        for handler in logger.handlers:
            handler.flush()

        # Note: coloredlogs may redirect to stderr
        captured = capsys.readouterr()
        assert "Console test message" in captured.out or "Console test message" in captured.err

    def test_console_output_disabled(self, temp_log_dir, capsys):
        """Should not output to console when disabled."""
        logger = setup_mothbox_logging(
            name="test_console_2",
            log_level="INFO",
            log_file=temp_log_dir / "test.log",
            console_output=False,
        )
        logger.info("Hidden message")

        for handler in logger.handlers:
            handler.flush()

        captured = capsys.readouterr()
        assert "Hidden message" not in captured.out


# ============================================================================
# Tests: Default Values
# ============================================================================

class TestDefaultValues:
    """Tests for default configuration values."""

    def test_default_log_level(self):
        """Should have INFO as default log level."""
        assert DEFAULT_LOG_LEVEL == "INFO"

    def test_default_max_bytes(self):
        """Should have 5MB as default max_bytes."""
        assert DEFAULT_MAX_BYTES == 5 * 1024 * 1024

    def test_default_backup_count(self):
        """Should have 5 as default backup_count."""
        assert DEFAULT_BACKUP_COUNT == 5

    def test_log_format_string(self):
        """Should have proper log format string."""
        assert "%(asctime)s" in MOTHBOX_LOG_FORMAT
        assert "%(name)s" in MOTHBOX_LOG_FORMAT
        assert "%(levelname)s" in MOTHBOX_LOG_FORMAT
        assert "%(message)s" in MOTHBOX_LOG_FORMAT


# ============================================================================
# Tests: Integration with controls.txt
# ============================================================================

class TestControlsTxtIntegration:
    """Tests for reading configuration from controls.txt."""

    def test_uses_controls_txt_level(self, temp_log_dir):
        """Should use log level from controls.txt when not specified."""
        mock_controls = {"log_level": "DEBUG"}

        with patch("webui.backend.logging_config.get_control_values", return_value=mock_controls):
            logger = setup_mothbox_logging(
                name="test_controls_1",
                log_file=temp_log_dir / "test.log",
                console_output=False,
            )
            assert logger.level == logging.DEBUG

    def test_explicit_level_overrides_controls(self, temp_log_dir):
        """Explicit log_level should override controls.txt value."""
        mock_controls = {"log_level": "DEBUG"}

        with patch("webui.backend.logging_config.get_control_values", return_value=mock_controls):
            logger = setup_mothbox_logging(
                name="test_controls_2",
                log_level="WARNING",  # Explicit override
                log_file=temp_log_dir / "test.log",
                console_output=False,
            )
            assert logger.level == logging.WARNING


# ============================================================================
# Tests: Error Handling
# ============================================================================

class TestErrorHandling:
    """Tests for error handling in logging setup."""

    def test_invalid_log_level_string(self, temp_log_dir):
        """Should fallback to INFO for invalid log level string."""
        logger = setup_mothbox_logging(
            name="test_error_1",
            log_level="INVALID_LEVEL",
            log_file=temp_log_dir / "test.log",
            console_output=False,
        )
        assert logger.level == logging.INFO

    def test_creates_log_directory(self, tmp_path):
        """Should create log directory if it doesn't exist."""
        log_file = tmp_path / "new_dir" / "subdir" / "test.log"
        logger = setup_mothbox_logging(
            name="test_error_2",
            log_level="INFO",
            log_file=log_file,
            console_output=False,
        )
        logger.info("Test")
        for handler in logger.handlers:
            handler.flush()

        assert log_file.parent.exists()

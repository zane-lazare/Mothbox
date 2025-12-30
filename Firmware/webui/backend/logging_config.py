"""
Mothbox Centralized Logging Configuration (Issue #37)

Provides centralized logging setup for the Mothbox application with:
- Configurable log levels via controls.txt
- Rotating file handler with size-based rotation
- Console output with coloredlogs for development
- Emoji stripping for clean log files
- Thread-safe logging operations

Usage:
    from logging_config import setup_mothbox_logging

    # Use default settings (reads from controls.txt)
    logger = setup_mothbox_logging(__name__)

    # Or specify explicit settings
    logger = setup_mothbox_logging(
        name="my_module",
        log_level="DEBUG",
        console_output=True,
    )

    logger.info("Application started")
    logger.debug("Debug details")
    logger.warning("Warning message")
    logger.error("Error occurred")
    logger.exception("Error with traceback")  # In except blocks
"""

import logging
import os
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Final

# Import mothbox paths for configuration
try:
    from mothbox_paths import CONFIG_DIR, DATA_DIR, get_control_values
except ImportError:
    # Fallback for testing or standalone use
    CONFIG_DIR = Path(__file__).parent.parent.parent
    DATA_DIR = CONFIG_DIR
    get_control_values = None

# Try to import coloredlogs for colored console output
try:
    import coloredlogs

    COLOREDLOGS_AVAILABLE = True
except ImportError:
    COLOREDLOGS_AVAILABLE = False


# ============================================================================
# Constants
# ============================================================================

DEFAULT_LOG_LEVEL: Final[str] = "INFO"
DEFAULT_MAX_BYTES: Final[int] = 5 * 1024 * 1024  # 5MB
DEFAULT_BACKUP_COUNT: Final[int] = 5
DEFAULT_LOG_RETENTION_DAYS: Final[int] = 7

MOTHBOX_LOG_FORMAT: Final[str] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
MOTHBOX_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"

# Emoji patterns to strip from log messages
# Note: Ranges are consolidated to avoid CodeQL warnings about overlapping character ranges
EMOJI_PATTERN = re.compile(
    "["
    "\U0001f300-\U0001f5ff"  # Symbols & pictographs
    "\U0001f600-\U0001f64f"  # Emoticons
    "\U0001f680-\U0001f6ff"  # Transport & map symbols
    "\U0001f700-\U0001f77f"  # Alchemical symbols
    "\U0001f780-\U0001f7ff"  # Geometric shapes extended
    "\U0001f800-\U0001f8ff"  # Supplemental arrows-C
    "\U0001f900-\U0001f9ff"  # Supplemental symbols and pictographs
    "\U0001fa00-\U0001fa6f"  # Chess symbols
    "\U0001fa70-\U0001faff"  # Symbols and pictographs extended-A
    "\U0001f1e0-\U0001f1ff"  # Flags
    "\U00002600-\U000026ff"  # Misc symbols (sun, stars, etc.)
    "\U00002700-\U000027bf"  # Dingbats (consolidated range)
    "\U0000fe00-\U0000fe0f"  # Variation selectors
    "\u2139"  # Info symbol
    "\u2611"  # Ballot box with check
    "\u2705"  # White heavy check mark
    "\u2714"  # Check mark
    "\u2716"  # X mark
    "\u2718"  # X mark heavy
    "\u26a0"  # Warning
    "\u274c"  # Cross mark
    "]+",
    flags=re.UNICODE,
)

# Valid log levels
VALID_LOG_LEVELS: Final[set[str]] = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

# Control character pattern for log injection protection
# Removes control chars except newline (\n, \x0a) and tab (\t, \x09)
CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]")


# ============================================================================
# Utility Functions
# ============================================================================


def sanitize_log_message(msg: str) -> str:
    """
    Remove control characters from a string to prevent log injection.

    Control characters can be used to forge log entries, corrupt log files,
    or exploit log viewers. This function removes all control characters
    except newline and tab which are legitimate in log messages.

    Args:
        msg: Input string potentially containing control characters

    Returns:
        String with control characters removed
    """
    if not msg:
        return msg
    return CONTROL_CHAR_PATTERN.sub("", msg)


def strip_emojis(text: str) -> str:
    """
    Remove emoji characters from a string.

    Used to clean log messages for file output while allowing
    emojis in console output during development.

    Args:
        text: Input string potentially containing emojis

    Returns:
        String with emojis removed and extra whitespace cleaned up
    """
    if not text:
        return text

    # Remove emojis
    cleaned = EMOJI_PATTERN.sub("", text)

    # Clean up any double spaces left behind
    cleaned = re.sub(r"\s+", " ", cleaned)

    # Strip leading/trailing whitespace
    return cleaned.strip()


def get_log_level_from_config() -> int:
    """
    Read log level from controls.txt configuration.

    Looks for 'log_level' key in controls.txt and maps it to
    a Python logging level constant.

    Returns:
        Logging level constant (logging.DEBUG, logging.INFO, etc.)
        Defaults to logging.INFO if not configured or invalid.
    """
    if get_control_values is None:
        return logging.INFO

    try:
        controls = get_control_values()
        level_str = controls.get("log_level", DEFAULT_LOG_LEVEL).upper()

        if level_str not in VALID_LOG_LEVELS:
            return logging.INFO

        return getattr(logging, level_str, logging.INFO)
    except Exception:
        return logging.INFO


def get_log_retention_days() -> int:
    """
    Read log retention days from controls.txt configuration.

    Returns:
        Number of days to retain log files. Defaults to 7.
    """
    if get_control_values is None:
        return DEFAULT_LOG_RETENTION_DAYS

    try:
        controls = get_control_values()
        days_str = controls.get("log_retention_days", str(DEFAULT_LOG_RETENTION_DAYS))
        days = int(days_str)
        return max(1, min(90, days))  # Clamp to 1-90 days
    except (ValueError, TypeError):
        return DEFAULT_LOG_RETENTION_DAYS


def get_default_log_file() -> Path:
    """
    Get the default log file path.

    Returns:
        Path to mothbox.log in DATA_DIR/logs/
    """
    log_dir = Path(DATA_DIR) / "logs"
    return log_dir / "mothbox.log"


# ============================================================================
# Emoji-Stripping Filter
# ============================================================================


class LogSanitizingFilter(logging.Filter):
    """
    Logging filter that sanitizes log messages for security and cleanliness.

    Applies two sanitization steps:
    1. Removes control characters to prevent log injection attacks
    2. Strips emojis for clean, parseable log files

    Used for file handlers while allowing raw output in console for development.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter the log record by sanitizing and stripping emojis from the message.

        Args:
            record: The log record to filter

        Returns:
            Always True (record is not filtered out, just modified)
        """
        if record.msg:
            msg = str(record.msg)
            # First sanitize control characters (security)
            msg = sanitize_log_message(msg)
            # Then strip emojis (cleanliness)
            msg = strip_emojis(msg)
            record.msg = msg
        return True


# Backwards compatibility alias
EmojiStrippingFilter = LogSanitizingFilter


# ============================================================================
# Main Setup Function
# ============================================================================


def setup_mothbox_logging(
    name: str = "mothbox",
    log_level: str | None = None,
    log_file: Path | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
    console_output: bool = True,
    _skip_path_validation: bool = False,
) -> logging.Logger:
    """
    Set up logging for a Mothbox module.

    Creates a configured logger with:
    - Rotating file handler (if log_file specified or using default)
    - Console handler with optional coloredlogs (if console_output=True)
    - Consistent formatting across all handlers
    - Emoji stripping for file output

    Args:
        name: Logger name (typically __name__ of the module)
        log_level: Log level string ("DEBUG", "INFO", etc.)
                   If None, reads from controls.txt
        log_file: Path to log file. If None, uses DATA_DIR/logs/mothbox.log
        max_bytes: Maximum size in bytes before rotation (default 5MB)
        backup_count: Number of backup files to keep (default 5)
        console_output: Whether to output to console (default True)
        _skip_path_validation: Skip DATA_DIR validation (for testing only)

    Returns:
        Configured logging.Logger instance

    Example:
        >>> logger = setup_mothbox_logging(__name__)
        >>> logger.info("Module initialized")
        >>> logger.debug("Detailed debug info")
    """
    # Get or create logger
    logger = logging.getLogger(name)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    # Determine log level
    if log_level is not None:
        level_str = log_level.upper()
        level = getattr(logging, level_str) if level_str in VALID_LOG_LEVELS else logging.INFO
    else:
        level = get_log_level_from_config()

    logger.setLevel(level)

    # Create formatter
    formatter = logging.Formatter(MOTHBOX_LOG_FORMAT, datefmt=MOTHBOX_DATE_FORMAT)

    # Add file handler
    if log_file is None:
        log_file = get_default_log_file()

    # Resolve path and validate against path traversal attacks
    log_file = Path(log_file).resolve()
    if not _skip_path_validation:
        data_dir_resolved = Path(DATA_DIR).resolve()
        if not str(log_file).startswith(str(data_dir_resolved)):
            raise ValueError(f"Log file must be within DATA_DIR: {data_dir_resolved}")

    # Ensure log directory exists with secure permissions
    log_file.parent.mkdir(parents=True, exist_ok=True, mode=0o755)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(LogSanitizingFilter())
    logger.addHandler(file_handler)

    # Set secure file permissions (owner read/write, others read-only)
    # nosec B103 - 0o644 is intentional: logs need to be readable for debugging
    if log_file.exists():
        os.chmod(log_file, 0o644)

    # Add console handler
    if console_output:
        if COLOREDLOGS_AVAILABLE:
            # Use coloredlogs for colored console output
            coloredlogs.install(
                level=level,
                logger=logger,
                fmt=MOTHBOX_LOG_FORMAT,
                datefmt=MOTHBOX_DATE_FORMAT,
                field_styles={
                    "asctime": {"color": "green"},
                    "levelname": {"bold": True},
                    "name": {"color": "blue"},
                },
                level_styles={
                    "debug": {"color": "cyan"},
                    "info": {"color": "green"},
                    "warning": {"color": "yellow", "bold": True},
                    "error": {"color": "red", "bold": True},
                    "critical": {"color": "red", "bold": True, "background": "white"},
                },
            )
        else:
            # Fallback to standard console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

    # Prevent propagation to root logger (avoid duplicate messages)
    logger.propagate = False

    return logger


# ============================================================================
# Module-level logger for this module
# ============================================================================

# Don't auto-initialize to avoid circular imports during module load
# Users should call setup_mothbox_logging() explicitly

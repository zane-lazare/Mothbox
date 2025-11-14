"""
Security utility functions for path validation and error handling (Issue #99)

Provides robust path validation to satisfy CodeQL static analysis and prevent
path traversal attacks with multiple layers of security checks.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def validate_photo_path(photo_path_str: str, base_dir: Path) -> Path | None:
    """
    Validate and resolve photo path with explicit security checks.

    Implements multiple layers of path traversal protection:
    1. Path resolution and relative_to() check
    2. Explicit string prefix validation (satisfies CodeQL)
    3. Symlink validation to prevent escaping base directory

    Args:
        photo_path_str: User-provided path (relative to base_dir)
        base_dir: Trusted base directory (e.g., PHOTOS_DIR)

    Returns:
        Resolved Path object if valid, None if invalid

    Security:
        - Prevents path traversal (../../etc/passwd)
        - Prevents absolute paths (/etc/passwd)
        - Validates symlinks stay within base_dir
        - Normalizes paths to prevent bypasses

    Examples:
        >>> validate_photo_path("photo.jpg", Path("/photos"))
        Path('/photos/photo.jpg')

        >>> validate_photo_path("../../etc/passwd", Path("/photos"))
        None

        >>> validate_photo_path("/etc/passwd", Path("/photos"))
        None
    """
    try:
        # Resolve both paths to absolute canonical form
        base_dir_resolved = base_dir.resolve()
        full_path = (base_dir / photo_path_str).resolve()

        # Security Check #1: Ensure path is within base directory
        # This raises ValueError if full_path is not relative to base_dir
        try:
            full_path.relative_to(base_dir_resolved)
        except ValueError:
            logger.warning(f"Path traversal attempt: {photo_path_str} outside {base_dir}")
            return None

        # Security Check #2: Explicit string prefix check (satisfies CodeQL)
        # This double-checks with string comparison that CodeQL recognizes
        base_str = str(base_dir_resolved)
        full_str = str(full_path)

        # Ensure base directory ends with separator for accurate prefix check
        if not base_str.endswith(os.sep):
            base_str += os.sep

        if not full_str.startswith(base_str):
            logger.warning(f"Path prefix validation failed: {photo_path_str}")
            return None

        # Security Check #3: Validate symlinks don't escape base directory
        if full_path.is_symlink():
            try:
                # Get symlink target
                target = full_path.readlink()

                # If target is absolute, verify it's within base_dir
                if target.is_absolute():
                    target.resolve().relative_to(base_dir_resolved)
                else:
                    # If relative, resolve from symlink's parent and validate
                    resolved_target = (full_path.parent / target).resolve()
                    resolved_target.relative_to(base_dir_resolved)

            except (ValueError, OSError) as e:
                logger.warning(f"Symlink validation failed for {photo_path_str}: {e}")
                return None

        return full_path

    except (ValueError, RuntimeError, OSError) as e:
        # Log the error but don't expose details to caller
        logger.warning(f"Path validation failed for {photo_path_str}: {e}")
        return None


def sanitize_error_message(error: Exception, generic_message: str) -> str:
    """
    Sanitize exception for user-facing error response.

    Logs full exception details server-side but returns generic message
    to prevent information disclosure through stack traces.

    Args:
        error: The exception that occurred
        generic_message: Generic message to return to user

    Returns:
        Sanitized error message safe for external users

    Examples:
        >>> try:
        ...     open('/etc/passwd')
        ... except Exception as e:
        ...     msg = sanitize_error_message(e, "File access error")
        >>> # Logs full error, returns "File access error"
    """
    # Log full details server-side (with stack trace)
    logger.error(f"{generic_message}: {error}", exc_info=True)

    # Return only generic message to user (prevents information disclosure)
    return generic_message

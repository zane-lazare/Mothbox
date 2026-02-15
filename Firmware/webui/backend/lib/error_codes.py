"""
Shared error codes and response helpers for the Mothbox API.

Provides standardized error code constants, message sanitization,
and a response helper to ensure consistent error JSON format across
all backend routes.

Usage:
    from webui.backend.lib.error_codes import (
        error_response, sanitize_message,
        VALIDATION_ERROR, NOT_FOUND, SERVER_ERROR,
    )

    return error_response(VALIDATION_ERROR, "Invalid input", 400)
    # Returns: (jsonify({"error": "Invalid input", "code": "VALIDATION_ERROR"}), 400)

Issue #388 - Standardize error codes across backend/frontend
"""

import re

from flask import jsonify

# ---------------------------------------------------------------------------
# Error code constants
# ---------------------------------------------------------------------------
# Each constant is its own string value, usable as both dict key and JSON value.

VALIDATION_ERROR = "VALIDATION_ERROR"
NOT_FOUND = "NOT_FOUND"
CONFLICT_ERROR = "CONFLICT_ERROR"
ACTIVATION_ERROR = "ACTIVATION_ERROR"
RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
HARDWARE_ERROR = "HARDWARE_ERROR"
STORAGE_ERROR = "STORAGE_ERROR"
PERMISSION_ERROR = "PERMISSION_ERROR"
SERVER_ERROR = "SERVER_ERROR"

# Convenience dict for iteration / membership checks
ERROR_CODES = {
    VALIDATION_ERROR: VALIDATION_ERROR,
    NOT_FOUND: NOT_FOUND,
    CONFLICT_ERROR: CONFLICT_ERROR,
    ACTIVATION_ERROR: ACTIVATION_ERROR,
    RATE_LIMIT_ERROR: RATE_LIMIT_ERROR,
    HARDWARE_ERROR: HARDWARE_ERROR,
    STORAGE_ERROR: STORAGE_ERROR,
    PERMISSION_ERROR: PERMISSION_ERROR,
    SERVER_ERROR: SERVER_ERROR,
}


# ---------------------------------------------------------------------------
# Message sanitization
# ---------------------------------------------------------------------------
# NOTE: This is distinct from security_utils.sanitize_error_message(), which
# takes an Exception and returns a generic message (hiding all details).
# This function sanitizes a *string* for safe display while preserving
# meaningful content: strips HTML tags, redacts internal file paths, truncates.

_HTML_TAG_RE = re.compile(r"<[^>]*>")
_INCOMPLETE_TAG_RE = re.compile(r"<[^>]*$")
_PATH_RE = re.compile(r"/(?:etc|var|home|opt|usr|tmp|root)/[^\s'\"]*")


def sanitize_message(message: str | None, max_length: int = 200) -> str:
    """
    Sanitize an error message string for safe display to users.

    Strips HTML tags (defense-in-depth against XSS), redacts internal
    file paths (prevents information disclosure), and truncates long messages.

    Args:
        message: Raw error message (may contain user input or internal details)
        max_length: Maximum length before truncation (default 200)

    Returns:
        Sanitized message safe for display, or "An error occurred" for empty input
    """
    if not message:
        return "An error occurred"

    msg = str(message)

    # Strip HTML tags iteratively (handles nested/malformed tags)
    # Cap iterations to prevent ReDoS on adversarial input
    prev_len = -1
    iterations = 0
    while len(msg) != prev_len and iterations < 10:
        iterations += 1
        prev_len = len(msg)
        msg = _HTML_TAG_RE.sub("", msg)
        msg = _INCOMPLETE_TAG_RE.sub("", msg)  # Incomplete tags

    # Redact internal file paths to prevent information disclosure
    msg = _PATH_RE.sub("[path]", msg)

    if len(msg) > max_length:
        msg = msg[: max_length - 3] + "..."

    return msg.strip() or "An error occurred"


# ---------------------------------------------------------------------------
# Response helper
# ---------------------------------------------------------------------------


def error_response(code: str, error_msg: str, status: int = 400, **extra) -> tuple:
    """
    Return a standardized JSON error response.

    Produces: ``(jsonify({"error": "<sanitized>", "code": "<CODE>", ...}), status)``

    Args:
        code: Error code constant (e.g., ``VALIDATION_ERROR``)
        error_msg: Human-readable error description (will be sanitized)
        status: HTTP status code (default 400)
        **extra: Additional fields to include in the response JSON
                 (e.g., ``message="detailed description"``, ``query="..."``).
                 Use ``message=`` to add a separate detail field to the
                 response while keeping the ``"error"`` field short.

    Returns:
        Tuple of (Flask Response, int) suitable for returning from a route

    Response field convention:
        ``"error"``   — short label (what went wrong)
        ``"code"``    — machine-readable constant (for programmatic handling)
        ``"message"`` — optional detailed description (for UI display)
    """
    body = {"error": sanitize_message(error_msg), "code": code, **extra}
    return jsonify(body), status

"""
API Key Authentication Library.

Provides secure API key authentication with:
- Environment variable and controls.txt configuration
- Constant-time comparison to prevent timing attacks
- Dual authentication support (CSRF OR API key)

Issue: #175 - API Key Authentication for Sidecar Metadata API

Usage:
    1. Set MOTHBOX_API_KEY environment variable (recommended) OR
       add api_key=your-key-here to controls.txt

    2. Apply @require_api_key_or_csrf decorator to protected routes:

       @sidecar_bp.route("/photos/<filename>", methods=["PATCH"])
       @require_api_key_or_csrf
       def update_photo_metadata(filename):
           ...

Security:
    - Uses hmac.compare_digest for constant-time comparison
    - Never logs API keys (even in debug mode)
    - Generic error messages to prevent information disclosure
    - Environment variable takes precedence over file config
"""

import hmac
import logging
import os
from functools import wraps

from flask import jsonify, request

# Import path utilities for loading controls.txt
from mothbox_paths import CONTROLS_FILE, get_control_values

logger = logging.getLogger(__name__)


def get_api_key_from_config() -> str | None:
    """
    Load API key from configuration sources.

    Priority order:
    1. MOTHBOX_API_KEY environment variable (recommended for production)
    2. api_key entry in controls.txt (fallback for device-local config)

    Returns:
        API key string if configured, None otherwise.
        Empty or whitespace-only keys are treated as not configured.
    """
    # 1. Check environment variable (preferred, never in git)
    env_key = os.environ.get("MOTHBOX_API_KEY", "").strip()
    if env_key:
        return env_key

    # 2. Fallback to controls.txt (device-local file)
    try:
        controls = get_control_values(CONTROLS_FILE)
        file_key = controls.get("api_key", "").strip()
        if file_key:
            return file_key
    except Exception:
        # If controls.txt doesn't exist or can't be read, treat as not configured
        pass

    return None


def validate_api_key(provided: str | None, expected: str | None) -> bool:
    """
    Validate API key using constant-time comparison.

    Uses hmac.compare_digest to prevent timing attacks where an attacker
    could deduce the correct key by measuring response times.

    Args:
        provided: The API key provided in the request header
        expected: The expected API key from configuration

    Returns:
        True if keys match, False otherwise
    """
    # Both keys must be non-empty strings
    if not provided or not expected:
        return False

    # Convert to bytes for hmac.compare_digest
    provided_bytes = provided.encode("utf-8")
    expected_bytes = expected.encode("utf-8")

    # Constant-time comparison (prevents timing attacks)
    return hmac.compare_digest(provided_bytes, expected_bytes)


def check_api_key_from_request() -> bool:
    """
    Check if the current request has a valid API key.

    Reads the X-API-Key header and validates against the configured key.

    Returns:
        True if:
        - API key is not configured (backwards compatible - allow all)
        - Valid API key is provided in X-API-Key header

        False if:
        - API key is configured but not provided or invalid
    """
    expected_key = get_api_key_from_config()

    # If no API key is configured, allow all requests (backwards compatible)
    if expected_key is None:
        return True

    provided_key = request.headers.get("X-API-Key")

    # Never log the actual key values
    is_valid = validate_api_key(provided_key, expected_key)

    if not is_valid and provided_key:
        # Log that validation failed, but never the key itself
        logger.debug("API key validation failed for request")

    return is_valid


def require_api_key_or_csrf(f):
    """
    Decorator that requires either valid CSRF token OR valid API key.

    This enables dual authentication:
    - Browser clients use CSRF tokens (from Flask-WTF)
    - Programmatic clients use API keys (X-API-Key header)

    Usage:
        @app.route("/api/resource", methods=["POST"])
        @require_api_key_or_csrf
        def create_resource():
            ...

    Returns:
        401 Unauthorized if neither valid CSRF nor API key is provided
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if API key authentication passes
        if check_api_key_from_request():
            return f(*args, **kwargs)

        # Check if CSRF token is valid
        # Flask-WTF automatically validates CSRF on POST/PUT/DELETE/PATCH
        # If we get here without raising, CSRF is either valid or not configured
        try:
            from flask_wtf.csrf import validate_csrf

            csrf_token = request.headers.get("X-CSRFToken")
            if csrf_token:
                validate_csrf(csrf_token)
                return f(*args, **kwargs)
        except Exception:
            # CSRF validation failed
            pass

        # Neither authentication method succeeded
        # Use generic error message to prevent information disclosure
        return jsonify({"error": "Authentication required"}), 401

    return decorated_function

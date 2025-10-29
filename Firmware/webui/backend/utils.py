"""
Mothbox Web UI - Shared Utility Functions

This module provides utilities shared across multiple route modules,
eliminating circular import issues and reducing code duplication.

Created to resolve issue #35: Refactor shared utility module to avoid circular imports
"""

from pathlib import Path
from typing import Callable, Dict, Any
import shutil
from datetime import datetime


# ============================================================================
# CSV Security
# ============================================================================

def sanitize_csv_value(value):
    """
    Sanitize value to prevent CSV injection attacks

    Prevents formula injection (=, +, -, @) and removes dangerous characters.
    Limits length to prevent DoS attacks.

    This function protects against CSV injection vulnerabilities where malicious
    users could inject formulas that execute when the CSV is opened in spreadsheet
    applications like Excel, LibreOffice Calc, or Google Sheets.

    Security measures:
    - Prefixes values starting with =, +, -, @, tab, or CR with single quote
    - Removes newlines and carriage returns (prevents multi-line injection)
    - Limits value length to 1000 characters (DoS prevention)

    Args:
        value: Value to sanitize (any type, will be converted to string)

    Returns:
        str: Sanitized string safe for CSV output

    Examples:
        >>> sanitize_csv_value("=SUM(A1:A10)")
        "'=SUM(A1:A10)"
        >>> sanitize_csv_value("Normal text")
        "Normal text"
        >>> sanitize_csv_value(42)
        "42"
        >>> sanitize_csv_value("Multi\\nLine\\nText")
        "Multi Line Text"
    """
    str_value = str(value)

    # Prevent CSV formula injection by prefixing with single quote if starts with dangerous chars
    if str_value.startswith(('=', '+', '-', '@', '\t', '\r')):
        str_value = "'" + str_value

    # Remove newlines and carriage returns to prevent multi-line injection
    str_value = str_value.replace('\n', ' ').replace('\r', ' ')

    # Limit length to prevent DoS
    if len(str_value) > 1000:
        str_value = str_value[:1000]

    return str_value

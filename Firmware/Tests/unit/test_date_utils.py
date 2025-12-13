"""Unit tests for date_utils module."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from webui.backend.lib.date_utils import (
    MOTHBOX_FILENAME_PATTERN,
    extract_date_from_filename,
    get_photo_date,
    parse_date_filter,
    validate_date_string,
)

# =============================================================================
# Tests for MOTHBOX_FILENAME_PATTERN
# =============================================================================


class TestMothboxFilenamePattern:
    """Tests for the filename pattern regex."""

    def test_pattern_matches_standard_filename(self):
        """Pattern matches standard Mothbox filename."""
        match = MOTHBOX_FILENAME_PATTERN.search("moth_2024_01_15__10_30_00.jpg")
        assert match is not None
        assert match.group('year') == '2024'
        assert match.group('month') == '01'
        assert match.group('day') == '15'
        assert match.group('hour') == '10'
        assert match.group('minute') == '30'
        assert match.group('second') == '00'

    def test_pattern_matches_hdr_filename(self):
        """Pattern matches HDR series filename."""
        match = MOTHBOX_FILENAME_PATTERN.search("moth_2024_06_20__14_00_00_HDR0.jpg")
        assert match is not None
        assert match.group('year') == '2024'
        assert match.group('month') == '06'
        assert match.group('day') == '20'

    def test_pattern_matches_focus_bracket_filename(self):
        """Pattern matches focus bracket filename."""
        match = MOTHBOX_FILENAME_PATTERN.search(
            "ManFocus_moth_2024_06_20__14_00_00_FB0.jpg"
        )
        assert match is not None
        assert match.group('year') == '2024'
        assert match.group('month') == '06'
        assert match.group('day') == '20'

    def test_pattern_no_match_for_random_filename(self):
        """Pattern doesn't match random filename."""
        match = MOTHBOX_FILENAME_PATTERN.search("random_photo.jpg")
        assert match is None

    def test_pattern_no_match_for_incomplete_timestamp(self):
        """Pattern doesn't match incomplete timestamp."""
        match = MOTHBOX_FILENAME_PATTERN.search("moth_2024_01_15.jpg")
        assert match is None


# =============================================================================
# Tests for extract_date_from_filename
# =============================================================================


class TestExtractDateFromFilename:
    """Tests for extract_date_from_filename function."""

    def test_standard_filename(self):
        """Test standard Mothbox filename."""
        result = extract_date_from_filename("moth_2024_01_15__10_30_00.jpg")
        assert result == date(2024, 1, 15)

    def test_hdr_filename(self):
        """Test HDR series filename."""
        result = extract_date_from_filename("moth_2024_01_15__10_30_00_HDR0.jpg")
        assert result == date(2024, 1, 15)

    def test_hdr_filename_higher_index(self):
        """Test HDR series with higher index."""
        result = extract_date_from_filename("moth_2024_01_15__10_30_00_HDR3.jpg")
        assert result == date(2024, 1, 15)

    def test_focus_bracket_filename(self):
        """Test focus bracket filename."""
        result = extract_date_from_filename(
            "ManFocus_moth_2024_01_15__10_30_00_FB0.jpg"
        )
        assert result == date(2024, 1, 15)

    def test_path_object(self):
        """Test with Path object."""
        result = extract_date_from_filename(
            Path("/photos/moth_2024_01_15__10_30_00.jpg")
        )
        assert result == date(2024, 1, 15)

    def test_no_match(self):
        """Test filename without timestamp."""
        result = extract_date_from_filename("random_photo.jpg")
        assert result is None

    def test_invalid_date_month(self):
        """Test invalid date values (month 13)."""
        result = extract_date_from_filename("moth_2024_13_15__10_30_00.jpg")
        assert result is None

    def test_invalid_date_day(self):
        """Test invalid date values (day 45)."""
        result = extract_date_from_filename("moth_2024_01_45__10_30_00.jpg")
        assert result is None

    def test_invalid_date_feb_30(self):
        """Test invalid date (Feb 30)."""
        result = extract_date_from_filename("moth_2024_02_30__10_30_00.jpg")
        assert result is None

    def test_jpeg_extension(self):
        """Test .jpeg extension."""
        result = extract_date_from_filename("moth_2024_06_20__14_00_00.jpeg")
        assert result == date(2024, 6, 20)

    def test_uppercase_extension(self):
        """Test .JPG extension."""
        result = extract_date_from_filename("moth_2024_06_20__14_00_00.JPG")
        assert result == date(2024, 6, 20)

    def test_complex_name_prefix(self):
        """Test filename with complex name prefix."""
        result = extract_date_from_filename(
            "forest_survey_site_A_2024_03_25__08_00_00.jpg"
        )
        assert result == date(2024, 3, 25)

    def test_leap_year_feb_29(self):
        """Test valid leap year date (Feb 29)."""
        result = extract_date_from_filename("moth_2024_02_29__10_00_00.jpg")
        assert result == date(2024, 2, 29)

    def test_non_leap_year_feb_29(self):
        """Test invalid non-leap year date (Feb 29, 2023)."""
        result = extract_date_from_filename("moth_2023_02_29__10_00_00.jpg")
        assert result is None


# =============================================================================
# Tests for get_photo_date
# =============================================================================


class TestGetPhotoDate:
    """Tests for get_photo_date function with mtime fallback."""

    def test_filename_priority(self, tmp_path):
        """Filename date takes priority over mtime."""
        photo = tmp_path / "moth_2024_01_15__10_30_00.jpg"
        photo.write_text("test")

        result = get_photo_date(photo)
        assert result == date(2024, 1, 15)

    def test_mtime_fallback(self, tmp_path):
        """Falls back to mtime when filename doesn't match."""
        photo = tmp_path / "unknown.jpg"
        photo.write_text("test")

        result = get_photo_date(photo)
        assert result is not None  # Should return today's date (mtime)
        assert result == date.today()

    def test_mtime_fallback_correct_date(self, tmp_path):
        """Mtime fallback returns correct date for today."""
        photo = tmp_path / "random_photo.jpg"
        photo.write_text("test")

        result = get_photo_date(photo)
        assert result == date.today()

    def test_nonexistent_file(self, tmp_path):
        """Returns None if file doesn't exist."""
        photo = tmp_path / "nonexistent.jpg"
        result = get_photo_date(photo)
        assert result is None

    def test_hdr_filename(self, tmp_path):
        """HDR filename extracts date correctly."""
        photo = tmp_path / "moth_2024_06_15__10_00_00_HDR0.jpg"
        photo.write_text("test")

        result = get_photo_date(photo)
        assert result == date(2024, 6, 15)

    def test_focus_bracket_filename(self, tmp_path):
        """Focus bracket filename extracts date correctly."""
        photo = tmp_path / "ManFocus_moth_2024_06_15__10_00_00_FB2.jpg"
        photo.write_text("test")

        result = get_photo_date(photo)
        assert result == date(2024, 6, 15)


# =============================================================================
# Tests for validate_date_string
# =============================================================================


class TestValidateDateString:
    """Tests for validate_date_string function."""

    def test_valid_date(self):
        """Test valid ISO 8601 date."""
        is_valid, error = validate_date_string("2024-01-15")
        assert is_valid is True
        assert error is None

    def test_valid_date_end_of_month(self):
        """Test valid end of month date."""
        is_valid, error = validate_date_string("2024-01-31")
        assert is_valid is True
        assert error is None

    def test_valid_date_leap_year(self):
        """Test valid leap year date."""
        is_valid, error = validate_date_string("2024-02-29")
        assert is_valid is True
        assert error is None

    def test_invalid_format_slashes(self):
        """Test invalid format with slashes."""
        is_valid, error = validate_date_string("01/15/2024")
        assert is_valid is False
        assert "YYYY-MM-DD" in error

    def test_compact_format_valid(self):
        """Test compact ISO 8601 format (YYYYMMDD) is valid in Python."""
        # Python's date.fromisoformat accepts compact format
        is_valid, error = validate_date_string("20240115")
        assert is_valid is True
        assert error is None

    def test_invalid_format_text(self):
        """Test invalid format with text."""
        is_valid, error = validate_date_string("January 15, 2024")
        assert is_valid is False
        assert "YYYY-MM-DD" in error

    def test_invalid_month(self):
        """Test invalid month (13)."""
        is_valid, error = validate_date_string("2024-13-01")
        assert is_valid is False
        assert error is not None

    def test_invalid_day(self):
        """Test invalid day (Feb 30)."""
        is_valid, error = validate_date_string("2024-02-30")
        assert is_valid is False
        assert error is not None

    def test_invalid_day_31(self):
        """Test invalid day (April 31)."""
        is_valid, error = validate_date_string("2024-04-31")
        assert is_valid is False
        assert error is not None

    def test_non_leap_year_feb_29(self):
        """Test invalid non-leap year Feb 29."""
        is_valid, error = validate_date_string("2023-02-29")
        assert is_valid is False
        assert error is not None

    def test_non_string_integer(self):
        """Test non-string input (integer)."""
        is_valid, error = validate_date_string(20240115)
        assert is_valid is False
        assert "string" in error

    def test_non_string_none(self):
        """Test non-string input (None)."""
        is_valid, error = validate_date_string(None)
        assert is_valid is False
        assert "string" in error

    def test_empty_string(self):
        """Test empty string."""
        is_valid, error = validate_date_string("")
        assert is_valid is False
        assert "YYYY-MM-DD" in error


# =============================================================================
# Tests for parse_date_filter
# =============================================================================


class TestParseDateFilter:
    """Tests for parse_date_filter function."""

    def test_valid_date(self):
        """Test parsing valid date."""
        result = parse_date_filter("2024-01-15")
        assert result == date(2024, 1, 15)

    def test_valid_date_end_of_year(self):
        """Test parsing end of year date."""
        result = parse_date_filter("2024-12-31")
        assert result == date(2024, 12, 31)

    def test_none_input(self):
        """Test None input returns None."""
        result = parse_date_filter(None)
        assert result is None

    def test_empty_string(self):
        """Test empty string returns None."""
        result = parse_date_filter("")
        assert result is None

    def test_invalid_format_raises(self):
        """Test invalid date format raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_date_filter("not-a-date")
        # Error message contains "Invalid date" prefix
        assert "Invalid date" in str(exc_info.value)

    def test_invalid_date_raises(self):
        """Test invalid date value raises ValueError."""
        with pytest.raises(ValueError):
            parse_date_filter("2024-02-30")

    def test_invalid_month_raises(self):
        """Test invalid month raises ValueError."""
        with pytest.raises(ValueError):
            parse_date_filter("2024-13-01")

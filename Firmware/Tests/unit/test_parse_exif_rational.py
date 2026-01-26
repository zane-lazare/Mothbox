"""
Unit Tests: EXIF Rational Tuple Parsing

Tests the _parse_exif_rational() function that validates and extracts
EXIF rational values (numerator/denominator tuples).

These are pure function tests - no hardware or Flask required.

Usage:
    pytest Tests/unit/test_parse_exif_rational.py -v
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))

from services.metadata_service import _parse_exif_rational


class TestValidRationalTuples:
    """Tests for valid EXIF rational tuples that should be parsed correctly"""

    def test_simple_fraction(self):
        """Simple valid fraction (1/100)"""
        result = _parse_exif_rational((1, 100))
        assert result == (1, 100)

    def test_whole_number_as_fraction(self):
        """Whole number represented as fraction (50/1)"""
        result = _parse_exif_rational((50, 1))
        assert result == (50, 1)

    def test_exposure_time_typical(self):
        """Typical exposure time (1/1000)"""
        result = _parse_exif_rational((1, 1000))
        assert result == (1, 1000)

    def test_focal_length_typical(self):
        """Typical focal length (4960/100 = 49.6mm)"""
        result = _parse_exif_rational((4960, 100))
        assert result == (4960, 100)

    def test_f_number_typical(self):
        """Typical f-number (28/10 = f/2.8)"""
        result = _parse_exif_rational((28, 10))
        assert result == (28, 10)

    def test_zero_numerator(self):
        """Zero numerator is valid (0/1 = 0)"""
        result = _parse_exif_rational((0, 1))
        assert result == (0, 1)

    def test_large_values(self):
        """Large values within int range"""
        result = _parse_exif_rational((1000000, 1000000))
        assert result == (1000000, 1000000)


class TestInvalidDenominators:
    """Tests for invalid denominators that should return None"""

    def test_zero_denominator(self):
        """Zero denominator should be rejected"""
        result = _parse_exif_rational((1, 0))
        assert result is None

    def test_negative_denominator(self):
        """Negative denominator should be rejected"""
        result = _parse_exif_rational((1, -100))
        assert result is None


class TestInvalidTypes:
    """Tests for invalid types that should return None"""

    def test_float_numerator(self):
        """Float numerator should be rejected"""
        result = _parse_exif_rational((1.5, 100))
        assert result is None

    def test_float_denominator(self):
        """Float denominator should be rejected"""
        result = _parse_exif_rational((1, 100.0))
        assert result is None

    def test_string_numerator(self):
        """String numerator should be rejected"""
        result = _parse_exif_rational(("1", 100))
        assert result is None

    def test_string_denominator(self):
        """String denominator should be rejected"""
        result = _parse_exif_rational((1, "100"))
        assert result is None

    def test_none_value(self):
        """None value should be rejected"""
        result = _parse_exif_rational(None)
        assert result is None

    def test_single_value(self):
        """Single value (not a tuple) should be rejected"""
        result = _parse_exif_rational(100)
        assert result is None

    def test_list_instead_of_tuple(self):
        """List instead of tuple should be rejected"""
        result = _parse_exif_rational([1, 100])
        assert result is None


class TestInvalidTupleStructure:
    """Tests for invalid tuple structures that should return None"""

    def test_empty_tuple(self):
        """Empty tuple should be rejected"""
        result = _parse_exif_rational(())
        assert result is None

    def test_single_element_tuple(self):
        """Single-element tuple should be rejected"""
        result = _parse_exif_rational((100,))
        assert result is None

    def test_three_element_tuple(self):
        """Three-element tuple should be rejected"""
        result = _parse_exif_rational((1, 100, 1000))
        assert result is None


class TestEdgeCases:
    """Tests for edge cases"""

    def test_negative_numerator(self):
        """Negative numerator is valid (for signed EXIF values like brightness)"""
        result = _parse_exif_rational((-5, 10))
        assert result == (-5, 10)

    def test_denominator_equals_one(self):
        """Denominator of 1 is valid"""
        result = _parse_exif_rational((100, 1))
        assert result == (100, 1)

    def test_very_small_fraction(self):
        """Very small fraction (1/1000000)"""
        result = _parse_exif_rational((1, 1000000))
        assert result == (1, 1000000)

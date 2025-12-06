"""
Unit tests for search_query_parser.py - User query to FTS5 query translation

Tests cover:
- Field-specific query parsing (tag:moth, species:actias, etc.)
- Boolean operators (AND, OR, NOT, minus shorthand)
- Phrase search (quoted strings)
- Prefix/wildcard search (luna*)
- Date filters (exact, range, comparison operators)
- Combined queries (multiple fields and operators)
- Edge cases (empty queries, special characters, malformed input)

Test-Driven Development (TDD) Protocol:
1. Write these tests FIRST
2. Run tests to confirm they FAIL
3. Implement code in search_query_parser.py
4. Refactor when tests pass
"""

import pytest
from webui.backend.lib.search_query_parser import (
    parse_query,
    ParsedQuery,
    DateFilter,
    FIELD_MAPPINGS,
)


class TestFieldSpecificQueries:
    """Test field-specific query parsing"""

    def test_tag_field_query(self):
        """tag:moth should become tags:moth"""
        result = parse_query("tag:moth")
        assert result.is_valid
        assert result.fts_query == "tags:moth"
        assert result.date_filter is None

    def test_tags_field_query(self):
        """tags:moth should stay tags:moth"""
        result = parse_query("tags:moth")
        assert result.is_valid
        assert result.fts_query == "tags:moth"

    def test_species_field_query(self):
        """species:actias should work"""
        result = parse_query("species:actias")
        assert result.is_valid
        assert result.fts_query == "species:actias"

    def test_common_name_field_query(self):
        """name:luna should map to species_common_name:luna"""
        result = parse_query("name:luna")
        assert result.is_valid
        assert result.fts_query == "species_common_name:luna"

    def test_notes_field_query(self):
        """notes:specimen should work"""
        result = parse_query("notes:specimen")
        assert result.is_valid
        assert result.fts_query == "notes:specimen"

    def test_note_field_alias(self):
        """note:specimen should map to notes:specimen"""
        result = parse_query("note:specimen")
        assert result.is_valid
        assert result.fts_query == "notes:specimen"

    def test_filename_field_query(self):
        """filename:IMG should work"""
        result = parse_query("filename:IMG")
        assert result.is_valid
        assert result.fts_query == "filename:IMG"

    def test_file_field_alias(self):
        """file:IMG should map to filename:IMG"""
        result = parse_query("file:IMG")
        assert result.is_valid
        assert result.fts_query == "filename:IMG"

    def test_case_insensitive_field_names(self):
        """TAG:moth should work same as tag:moth"""
        result = parse_query("TAG:moth")
        assert result.is_valid
        assert result.fts_query == "tags:moth"

    def test_mixed_case_field_names(self):
        """TaGs:moth should work same as tag:moth"""
        result = parse_query("TaGs:moth")
        assert result.is_valid
        assert result.fts_query == "tags:moth"

    def test_unknown_field_treated_as_text(self):
        """unknown:value should search all fields for 'unknown:value'"""
        result = parse_query("unknown:value")
        assert result.is_valid
        # Unknown fields should be treated as literal text search
        assert "unknown:value" in result.fts_query or "unknown" in result.fts_query


class TestBooleanOperators:
    """Test boolean operator parsing"""

    def test_and_operator_uppercase(self):
        """luna AND moth should preserve AND"""
        result = parse_query("luna AND moth")
        assert result.is_valid
        assert result.fts_query == "luna AND moth"

    def test_and_operator_lowercase(self):
        """luna and moth should convert to AND"""
        result = parse_query("luna and moth")
        assert result.is_valid
        assert result.fts_query == "luna AND moth"

    def test_or_operator_uppercase(self):
        """luna OR sphinx should preserve OR"""
        result = parse_query("luna OR sphinx")
        assert result.is_valid
        assert result.fts_query == "luna OR sphinx"

    def test_or_operator_lowercase(self):
        """luna or sphinx should convert to OR"""
        result = parse_query("luna or sphinx")
        assert result.is_valid
        assert result.fts_query == "luna OR sphinx"

    def test_not_operator_uppercase(self):
        """moth NOT luna should preserve NOT"""
        result = parse_query("moth NOT luna")
        assert result.is_valid
        assert result.fts_query == "moth NOT luna"

    def test_not_operator_lowercase(self):
        """moth not luna should convert to NOT"""
        result = parse_query("moth not luna")
        assert result.is_valid
        assert result.fts_query == "moth NOT luna"

    def test_minus_shorthand(self):
        """moth -luna should become moth NOT luna"""
        result = parse_query("moth -luna")
        assert result.is_valid
        assert result.fts_query == "moth NOT luna"

    def test_implicit_and(self):
        """luna moth (no operator) should become luna AND moth"""
        result = parse_query("luna moth")
        assert result.is_valid
        assert result.fts_query == "luna AND moth"

    def test_multiple_implicit_and(self):
        """Three terms should all be ANDed together"""
        result = parse_query("luna moth green")
        assert result.is_valid
        assert result.fts_query == "luna AND moth AND green"

    def test_explicit_and_with_not(self):
        """moth AND NOT luna should be preserved correctly"""
        result = parse_query("moth AND NOT luna")
        assert result.is_valid
        assert result.fts_query == "moth AND NOT luna"

    def test_or_with_not(self):
        """moth OR NOT luna should be preserved correctly"""
        result = parse_query("moth OR NOT luna")
        assert result.is_valid
        assert result.fts_query == "moth OR NOT luna"


class TestPhraseSearch:
    """Test quoted phrase search"""

    def test_double_quoted_phrase(self):
        """"luna moth" should preserve quotes"""
        result = parse_query('"luna moth"')
        assert result.is_valid
        assert result.fts_query == '"luna moth"'

    def test_phrase_with_field(self):
        """notes:"large specimen" should work"""
        result = parse_query('notes:"large specimen"')
        assert result.is_valid
        assert result.fts_query == 'notes:"large specimen"'

    def test_phrase_with_boolean(self):
        """"luna moth" AND nocturnal should work"""
        result = parse_query('"luna moth" AND nocturnal')
        assert result.is_valid
        assert result.fts_query == '"luna moth" AND nocturnal'

    def test_multiple_phrases(self):
        """"luna moth" OR "sphinx moth" should work"""
        result = parse_query('"luna moth" OR "sphinx moth"')
        assert result.is_valid
        assert result.fts_query == '"luna moth" OR "sphinx moth"'


class TestPrefixSearch:
    """Test prefix/wildcard search"""

    def test_asterisk_wildcard(self):
        """luna* should preserve asterisk"""
        result = parse_query("luna*")
        assert result.is_valid
        assert result.fts_query == "luna*"

    def test_prefix_with_field(self):
        """tag:noc* should work"""
        result = parse_query("tag:noc*")
        assert result.is_valid
        assert result.fts_query == "tags:noc*"

    def test_multiple_wildcards(self):
        """lun* AND mot* should work"""
        result = parse_query("lun* AND mot*")
        assert result.is_valid
        assert result.fts_query == "lun* AND mot*"


class TestDateFilters:
    """Test date filter parsing"""

    def test_date_exact_match(self):
        """date:2024-11-01 should match exact date"""
        result = parse_query("date:2024-11-01")
        assert result.is_valid
        # Exact date should be in FTS query or date filter
        assert result.fts_query == "date:2024-11-01" or (
            result.date_filter and
            result.date_filter.operator == 'eq' and
            result.date_filter.start_date == '2024-11-01'
        )

    def test_date_range(self):
        """date:2024-11-01..2024-11-06 should create DateFilter"""
        result = parse_query("date:2024-11-01..2024-11-06")
        assert result.is_valid
        assert result.date_filter is not None
        assert result.date_filter.operator == 'range'
        assert result.date_filter.start_date == '2024-11-01'
        assert result.date_filter.end_date == '2024-11-06'

    def test_date_greater_than(self):
        """date:>2024-01-01 should create DateFilter with gt operator"""
        result = parse_query("date:>2024-01-01")
        assert result.is_valid
        assert result.date_filter is not None
        assert result.date_filter.operator == 'gt'
        assert result.date_filter.start_date == '2024-01-01'

    def test_date_less_than(self):
        """date:<2024-12-31 should create DateFilter with lt operator"""
        result = parse_query("date:<2024-12-31")
        assert result.is_valid
        assert result.date_filter is not None
        assert result.date_filter.operator == 'lt'
        assert result.date_filter.end_date == '2024-12-31'

    def test_date_greater_than_or_equal(self):
        """date:>=2024-01-01 should create DateFilter"""
        result = parse_query("date:>=2024-01-01")
        assert result.is_valid
        assert result.date_filter is not None
        assert result.date_filter.operator == 'gte'
        assert result.date_filter.start_date == '2024-01-01'

    def test_date_less_than_or_equal(self):
        """date:<=2024-12-31 should create DateFilter"""
        result = parse_query("date:<=2024-12-31")
        assert result.is_valid
        assert result.date_filter is not None
        assert result.date_filter.operator == 'lte'
        assert result.date_filter.end_date == '2024-12-31'


class TestCombinedQueries:
    """Test complex queries with multiple features"""

    def test_multiple_field_queries(self):
        """tag:moth species:actias should combine with AND"""
        result = parse_query("tag:moth species:actias")
        assert result.is_valid
        assert result.fts_query == "tags:moth AND species:actias"

    def test_phrase_with_field_query(self):
        """"luna moth" tag:nocturnal should combine"""
        result = parse_query('"luna moth" tag:nocturnal')
        assert result.is_valid
        assert result.fts_query == '"luna moth" AND tags:nocturnal'

    def test_complex_boolean_query(self):
        """tag:moth OR tag:butterfly species:actias should work"""
        result = parse_query("tag:moth OR tag:butterfly species:actias")
        assert result.is_valid
        # Should have OR and AND operators
        assert "OR" in result.fts_query
        assert "AND" in result.fts_query or result.fts_query.endswith("species:actias")

    def test_field_with_wildcard_and_boolean(self):
        """tag:moth* AND species:act* should work"""
        result = parse_query("tag:moth* AND species:act*")
        assert result.is_valid
        assert result.fts_query == "tags:moth* AND species:act*"

    def test_date_with_text_search(self):
        """moth date:2024-11-01 should combine"""
        result = parse_query("moth date:2024-11-01")
        assert result.is_valid
        # Should have moth in FTS query
        assert "moth" in result.fts_query

    def test_date_range_with_tags(self):
        """tag:moth date:2024-11-01..2024-11-06 should work"""
        result = parse_query("tag:moth date:2024-11-01..2024-11-06")
        assert result.is_valid
        assert "tags:moth" in result.fts_query
        assert result.date_filter is not None
        assert result.date_filter.operator == 'range'


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_query(self):
        """Empty query should return error"""
        result = parse_query("")
        assert not result.is_valid
        assert result.error_message is not None
        assert "empty" in result.error_message.lower()

    def test_whitespace_only(self):
        """Whitespace-only query should return error"""
        result = parse_query("   ")
        assert not result.is_valid
        assert result.error_message is not None

    def test_special_characters_preserved(self):
        """Special characters should be handled"""
        result = parse_query("moth@night")
        assert result.is_valid
        # Should not crash, exact behavior depends on implementation

    def test_unbalanced_quotes_handled(self):
        """Unbalanced quotes should handle gracefully"""
        result = parse_query('"luna moth')
        # Should either auto-close quotes or return error
        assert isinstance(result, ParsedQuery)

    def test_field_with_no_value(self):
        """tag: with no value should handle gracefully"""
        result = parse_query("tag:")
        # Should either ignore or return error
        assert isinstance(result, ParsedQuery)

    def test_multiple_colons(self):
        """tag:value:extra should handle gracefully"""
        result = parse_query("tag:value:extra")
        assert isinstance(result, ParsedQuery)

    def test_only_operators(self):
        """Query with only operators should return error"""
        result = parse_query("AND OR NOT")
        # Should either treat as text or return error
        assert isinstance(result, ParsedQuery)

    def test_excessive_whitespace(self):
        """Extra whitespace should be normalized"""
        result = parse_query("moth    AND     luna")
        assert result.is_valid
        # Whitespace should be normalized
        assert result.fts_query == "moth AND luna"

    def test_parentheses_preserved(self):
        """Parentheses should be preserved for grouping"""
        result = parse_query("(moth OR butterfly) AND green")
        assert result.is_valid
        # Should preserve parentheses or handle grouping
        assert "(" in result.fts_query or "moth" in result.fts_query


class TestOriginalQueryPreservation:
    """Test that original query is always preserved"""

    def test_original_query_stored(self):
        """Original query should be stored in result"""
        original = "tag:moth AND species:actias"
        result = parse_query(original)
        assert result.original_query == original

    def test_original_query_stored_on_error(self):
        """Original query should be stored even on error"""
        original = ""
        result = parse_query(original)
        assert result.original_query == original


class TestFieldMappings:
    """Test that FIELD_MAPPINGS constant is correct"""

    def test_field_mappings_exist(self):
        """FIELD_MAPPINGS should be defined"""
        assert isinstance(FIELD_MAPPINGS, dict)

    def test_field_mappings_have_required_fields(self):
        """FIELD_MAPPINGS should have all required field aliases"""
        required_fields = ['tag', 'tags', 'species', 'notes', 'filename', 'date']
        for field in required_fields:
            assert field in FIELD_MAPPINGS

    def test_field_mappings_lowercase(self):
        """FIELD_MAPPINGS keys should be lowercase"""
        for key in FIELD_MAPPINGS:
            assert key == key.lower()

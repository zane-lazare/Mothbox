"""
Search Query Parser for Mothbox Photo Search (Issue #131 - Phase 1.2)

Translates user-friendly search queries into SQLite FTS5 syntax.

Features:
- Field-specific queries: tag:moth, species:actias, notes:specimen
- Boolean operators: AND, OR, NOT, - (minus shorthand)
- Phrase search: "luna moth"
- Prefix/wildcard: luna*, act*
- Date filters: date:2024-11-01, date:>2024-01-01, date:2024-11-01..2024-11-06
- Combined queries: tag:moth species:actias "luna moth"

Usage:
    from webui.backend.lib.search_query_parser import parse_query

    result = parse_query("tag:moth species:actias")
    if result.is_valid:
        # Use result.fts_query for FTS5 search
        # Use result.date_filter for WHERE clause filtering
        print(f"FTS Query: {result.fts_query}")
    else:
        print(f"Error: {result.error_message}")
"""

import re
from dataclasses import dataclass
from typing import Optional


# ============================================================================
# Constants
# ============================================================================

# Field name mappings (user-friendly → FTS5 column)
FIELD_MAPPINGS = {
    'tag': 'tags',
    'tags': 'tags',
    'species': 'species',
    'common_name': 'species_common_name',
    'name': 'species_common_name',
    'notes': 'notes',
    'note': 'notes',
    'filename': 'filename',
    'file': 'filename',
    'date': 'date',
}


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class DateFilter:
    """Date range filter for WHERE clause.

    Attributes:
        start_date: Start date in ISO format YYYY-MM-DD (or None)
        end_date: End date in ISO format YYYY-MM-DD (or None)
        operator: Filter operator ('range', 'gt', 'lt', 'eq', 'gte', 'lte')
    """
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    operator: str = 'eq'


@dataclass
class ParsedQuery:
    """Result of parsing a search query.

    Attributes:
        fts_query: FTS5 query string for full-text search
        date_filter: Date range filter (separate from FTS) or None
        original_query: Original user query string
        is_valid: Whether parsing succeeded
        error_message: Error description if parsing failed
    """
    fts_query: str
    date_filter: Optional[DateFilter]
    original_query: str
    is_valid: bool
    error_message: Optional[str] = None


# ============================================================================
# Query Parser
# ============================================================================

def parse_query(query: str) -> ParsedQuery:
    """Parse user query into FTS5 format.

    Translates user-friendly query syntax into SQLite FTS5 format.
    Handles field-specific queries, boolean operators, phrases, wildcards,
    and date filters.

    Args:
        query: User search query string

    Returns:
        ParsedQuery with FTS5 query, optional date filter, and validation status

    Examples:
        >>> result = parse_query("tag:moth species:actias")
        >>> result.fts_query
        'tags:moth AND species:actias'

        >>> result = parse_query("date:2024-11-01..2024-11-06")
        >>> result.date_filter.operator
        'range'

        >>> result = parse_query('"luna moth" AND nocturnal')
        >>> result.fts_query
        '"luna moth" AND nocturnal'
    """
    # Store original query
    original_query = query

    # Validate query is not empty
    if not query or not query.strip():
        return ParsedQuery(
            fts_query='',
            date_filter=None,
            original_query=original_query,
            is_valid=False,
            error_message='Query cannot be empty'
        )

    # Normalize whitespace
    query = ' '.join(query.split())

    # Extract date filters first (they need special handling)
    date_filter = None
    query, date_filter = _extract_date_filter(query)

    # Normalize boolean operators to uppercase
    query = _normalize_boolean_operators(query)

    # Convert minus shorthand to NOT operator
    query = _convert_minus_to_not(query)

    # Map field names to FTS5 column names
    query = _map_field_names(query)

    # Add implicit AND between terms
    query = _add_implicit_and(query)

    # Final cleanup
    query = ' '.join(query.split())

    return ParsedQuery(
        fts_query=query,
        date_filter=date_filter,
        original_query=original_query,
        is_valid=True,
        error_message=None
    )


# ============================================================================
# Helper Functions
# ============================================================================

def _extract_date_filter(query: str) -> tuple[str, Optional[DateFilter]]:
    """Extract date filter from query and return cleaned query.

    Args:
        query: User query string

    Returns:
        Tuple of (cleaned_query, date_filter or None)
    """
    # Pattern: date:YYYY-MM-DD..YYYY-MM-DD (range)
    range_pattern = r'date:(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})'
    match = re.search(range_pattern, query, re.IGNORECASE)
    if match:
        start_date = match.group(1)
        end_date = match.group(2)
        cleaned_query = re.sub(range_pattern, '', query, flags=re.IGNORECASE)
        return cleaned_query, DateFilter(
            start_date=start_date,
            end_date=end_date,
            operator='range'
        )

    # Pattern: date:>=YYYY-MM-DD
    gte_pattern = r'date:>=(\d{4}-\d{2}-\d{2})'
    match = re.search(gte_pattern, query, re.IGNORECASE)
    if match:
        start_date = match.group(1)
        cleaned_query = re.sub(gte_pattern, '', query, flags=re.IGNORECASE)
        return cleaned_query, DateFilter(
            start_date=start_date,
            operator='gte'
        )

    # Pattern: date:<=YYYY-MM-DD
    lte_pattern = r'date:<=(\d{4}-\d{2}-\d{2})'
    match = re.search(lte_pattern, query, re.IGNORECASE)
    if match:
        end_date = match.group(1)
        cleaned_query = re.sub(lte_pattern, '', query, flags=re.IGNORECASE)
        return cleaned_query, DateFilter(
            end_date=end_date,
            operator='lte'
        )

    # Pattern: date:>YYYY-MM-DD
    gt_pattern = r'date:>(\d{4}-\d{2}-\d{2})'
    match = re.search(gt_pattern, query, re.IGNORECASE)
    if match:
        start_date = match.group(1)
        cleaned_query = re.sub(gt_pattern, '', query, flags=re.IGNORECASE)
        return cleaned_query, DateFilter(
            start_date=start_date,
            operator='gt'
        )

    # Pattern: date:<YYYY-MM-DD
    lt_pattern = r'date:<(\d{4}-\d{2}-\d{2})'
    match = re.search(lt_pattern, query, re.IGNORECASE)
    if match:
        end_date = match.group(1)
        cleaned_query = re.sub(lt_pattern, '', query, flags=re.IGNORECASE)
        return cleaned_query, DateFilter(
            end_date=end_date,
            operator='lt'
        )

    # Pattern: date:YYYY-MM-DD (exact match - keep in FTS query)
    # Don't extract exact dates, let them go through FTS

    return query, None


def _normalize_boolean_operators(query: str) -> str:
    """Normalize boolean operators to uppercase.

    Args:
        query: Query string

    Returns:
        Query with AND, OR, NOT in uppercase
    """
    # Use word boundaries to avoid replacing within words
    # Replace case-insensitive AND, OR, NOT with uppercase versions
    query = re.sub(r'\band\b', 'AND', query, flags=re.IGNORECASE)
    query = re.sub(r'\bor\b', 'OR', query, flags=re.IGNORECASE)
    query = re.sub(r'\bnot\b', 'NOT', query, flags=re.IGNORECASE)
    return query


def _convert_minus_to_not(query: str) -> str:
    """Convert minus shorthand to NOT operator.

    Args:
        query: Query string

    Returns:
        Query with -term converted to NOT term
    """
    # Pattern: space followed by minus and word
    # Convert " -word" to " NOT word"
    query = re.sub(r'\s+-(\S+)', r' NOT \1', query)
    return query


def _map_field_names(query: str) -> str:
    """Map user-friendly field names to FTS5 column names.

    Args:
        query: Query string

    Returns:
        Query with field names mapped to FTS5 columns
    """
    # Pattern: field:value (with optional quotes around value)
    # Capture field name and everything after colon (including quoted strings)

    def replace_field(match):
        field = match.group(1).lower()
        value = match.group(2)

        # Map field name to FTS5 column (if known)
        if field in FIELD_MAPPINGS:
            fts_field = FIELD_MAPPINGS[field]
            return f'{fts_field}:{value}'
        else:
            # Unknown field - treat as literal text
            # Keep the original field:value as text search
            return match.group(0)

    # Pattern matches: field:"quoted value" or field:value or field:value*
    pattern = r'(\w+):((?:"[^"]*")|(?:\S+))'
    query = re.sub(pattern, replace_field, query)

    return query


def _add_implicit_and(query: str) -> str:
    """Add implicit AND between terms that don't have explicit operators.

    Args:
        query: Query string

    Returns:
        Query with implicit AND operators added
    """
    # Split by existing operators and quotes to identify term boundaries
    # This is a simplified approach - more complex queries may need better parsing

    # First, protect quoted strings by replacing them with placeholders
    quotes = []
    def save_quote(match):
        quotes.append(match.group(0))
        return f'__QUOTE_{len(quotes) - 1}__'

    query = re.sub(r'"[^"]*"', save_quote, query)

    # Split into tokens
    tokens = query.split()

    # Process tokens to add implicit AND
    result = []
    operators = {'AND', 'OR', 'NOT'}

    for i, token in enumerate(tokens):
        result.append(token)

        # Check if we need to add AND after this token
        if i < len(tokens) - 1:
            next_token = tokens[i + 1]

            # Don't add AND if current token is an operator
            if token in operators:
                continue

            # Don't add AND if next token is an operator (except NOT)
            if next_token in {'AND', 'OR'}:
                continue

            # Don't add AND if next token is NOT (it's already a binary operator position)
            # Actually, NOT can be unary, so we might need AND before it
            # Example: "moth NOT luna" is valid, but "moth luna" should be "moth AND luna"
            # Let's check if the previous token was an operator
            if i > 0 and result[-2] in {'AND', 'OR'}:
                # We already have an operator before this
                if next_token == 'NOT':
                    # This is a new clause: "moth AND NOT luna" - don't add another AND
                    continue
                else:
                    # Add AND before next term
                    result.append('AND')
            else:
                # No operator before, add AND (unless next is NOT in binary position)
                if next_token != 'NOT':
                    result.append('AND')

    # Restore quoted strings
    result_str = ' '.join(result)
    for i, quote in enumerate(quotes):
        result_str = result_str.replace(f'__QUOTE_{i}__', quote)

    return result_str


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    'parse_query',
    'ParsedQuery',
    'DateFilter',
    'FIELD_MAPPINGS',
]

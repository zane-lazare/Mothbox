"""
Search Query Parser for Mothbox Photo Search

Translates user-friendly search queries into SQLite FTS5 syntax.

Features:
- Field-specific queries: tag:moth, species:actias, notes:specimen
- EXIF camera settings: iso:3200, aperture:2.8, shutter:0.001
- Boolean operators: AND, OR, NOT, - (minus shorthand)
- Phrase search: "luna moth"
- Prefix/wildcard: luna*, act*
- Date filters: date:2024-11-01, date:>2024-01-01, date:2024-11-01..2024-11-06
- Combined queries: tag:moth species:actias "luna moth"

EXIF Range Queries:
    Range syntax (iso:100-3200, aperture:2.8-16, shutter:0.001-30) is accepted
    by the parser and passed through to FTS5. However, FTS5 stores EXIF values
    as text and does not support native numeric range filtering. For actual
    numeric range filtering, post-process search results in Python or use
    SQL WHERE clauses with CAST().

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

from __future__ import annotations

import re
from dataclasses import dataclass

# ============================================================================
# Constants
# ============================================================================

# Query validation limits (defense in depth)
MAX_QUERY_LENGTH = 500  # Max total query length (also in routes/search.py)
MAX_QUERY_TERMS = 20  # Max number of search terms
MAX_TERM_LENGTH = 100  # Max length of individual term
MAX_PHRASE_LENGTH = 200  # Max length of phrase in quotes
MAX_PARENTHESIS_DEPTH = 3  # Max nesting of parentheses

# Field name mappings (user-friendly → FTS5 column)
FIELD_MAPPINGS = {
    "tag": "tags",
    "tags": "tags",
    "species": "species",
    "common_name": "species_common_name",
    "name": "species_common_name",
    "notes": "notes",
    "note": "notes",
    "filename": "filename",
    "file": "filename",
    "date": "date",
    "ext": "file_ext",
    "extension": "file_ext",
    "filetype": "file_ext",
    "type": "file_ext",
    "iso": "exif_iso",
    "aperture": "exif_aperture",
    "fstop": "exif_aperture",
    "f": "exif_aperture",
    "shutter": "exif_shutter",
    "exposure": "exif_shutter",
    "shutterspeed": "exif_shutter",
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

    start_date: str | None = None
    end_date: str | None = None
    operator: str = "eq"


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
    date_filter: DateFilter | None
    original_query: str
    is_valid: bool
    error_message: str | None = None


# ============================================================================
# Query Validation
# ============================================================================


def validate_query(query: str) -> tuple[bool, str | None]:
    """Validate FTS5 query structure to prevent injection and DoS.

    Performs defense-in-depth validation of search queries:
    - Length limits (total query, individual terms, phrases)
    - Complexity limits (number of terms, nesting depth)
    - Structural validation (balanced parentheses)

    Args:
        query: Raw user query string

    Returns:
        Tuple of (is_valid, error_message or None)

    Examples:
        >>> validate_query("moth")
        (True, None)
        >>> validate_query("a" * 600)
        (False, "Query too long (max 500 chars)")
        >>> validate_query("((((moth))))")
        (False, "Query too complex (max nesting depth 3)")
    """
    if not query or not query.strip():
        return False, "Query cannot be empty"

    if len(query) > MAX_QUERY_LENGTH:
        return False, f"Query too long (max {MAX_QUERY_LENGTH} chars)"

    # Check phrase lengths first (before term count, since phrases count as single terms)
    phrases = re.findall(r'"([^"]*)"', query)
    for phrase in phrases:
        if len(phrase) > MAX_PHRASE_LENGTH:
            return False, f"Phrase too long (max {MAX_PHRASE_LENGTH} chars)"

    # Remove quoted phrases for term counting (they count as 1 term each)
    query_for_terms = re.sub(r'"[^"]*"', "__PHRASE__", query)

    # Count terms (split by whitespace, excluding operators)
    operators = {"AND", "OR", "NOT", "and", "or", "not"}
    terms = [t for t in query_for_terms.split() if t not in operators and not t.startswith("-")]
    if len(terms) > MAX_QUERY_TERMS:
        return False, f"Too many search terms (max {MAX_QUERY_TERMS})"

    # Check individual term lengths (use original query terms, not placeholders)
    original_terms = [t for t in query.split() if t not in operators and not t.startswith("-")]
    for term in original_terms:
        # Skip if this term is part of a quoted phrase (starts or ends with quote)
        if term.startswith('"') and not term.endswith('"'):
            continue  # Start of multi-word phrase
        if term.endswith('"') and not term.startswith('"'):
            continue  # End of multi-word phrase
        if not term.startswith('"') and not term.endswith('"'):
            # Check if we're inside a quote - find position and check
            pos = query.find(term)
            if pos > 0:
                # Check if there's an unclosed quote before this term
                before = query[:pos]
                if before.count('"') % 2 == 1:
                    continue  # Inside a quoted phrase
        clean_term = term
        # Remove field prefix if present
        if ":" in clean_term:
            clean_term = clean_term.split(":", 1)[1]
        # Remove quotes and parentheses
        clean_term = clean_term.strip('"()')
        if len(clean_term) > MAX_TERM_LENGTH:
            return False, f"Search term too long (max {MAX_TERM_LENGTH} chars)"

    # Check parenthesis nesting depth
    depth = 0
    max_depth = 0
    for char in query:
        if char == "(":
            depth += 1
            max_depth = max(max_depth, depth)
        elif char == ")":
            depth -= 1

    if depth != 0:
        return False, "Unbalanced parentheses"

    if max_depth > MAX_PARENTHESIS_DEPTH:
        return False, f"Query too complex (max nesting depth {MAX_PARENTHESIS_DEPTH})"

    return True, None


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

    # Validate query structure (defense in depth)
    is_valid, error_message = validate_query(query)
    if not is_valid:
        return ParsedQuery(
            fts_query="",
            date_filter=None,
            original_query=original_query,
            is_valid=False,
            error_message=error_message,
        )

    # Normalize whitespace
    query = " ".join(query.split())

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
    query = " ".join(query.split())

    return ParsedQuery(
        fts_query=query,
        date_filter=date_filter,
        original_query=original_query,
        is_valid=True,
        error_message=None,
    )


# ============================================================================
# Helper Functions
# ============================================================================


def _extract_date_filter(query: str) -> tuple[str, DateFilter | None]:
    """Extract date filter from query and return cleaned query.

    Args:
        query: User query string

    Returns:
        Tuple of (cleaned_query, date_filter or None)
    """
    # Pattern: date:YYYY-MM-DD..YYYY-MM-DD (range)
    range_pattern = r"date:(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})"
    match = re.search(range_pattern, query, re.IGNORECASE)
    if match:
        start_date = match.group(1)
        end_date = match.group(2)
        cleaned_query = re.sub(range_pattern, "", query, flags=re.IGNORECASE)
        return cleaned_query, DateFilter(start_date=start_date, end_date=end_date, operator="range")

    # Pattern: date:>=YYYY-MM-DD
    gte_pattern = r"date:>=(\d{4}-\d{2}-\d{2})"
    match = re.search(gte_pattern, query, re.IGNORECASE)
    if match:
        start_date = match.group(1)
        cleaned_query = re.sub(gte_pattern, "", query, flags=re.IGNORECASE)
        return cleaned_query, DateFilter(start_date=start_date, operator="gte")

    # Pattern: date:<=YYYY-MM-DD
    lte_pattern = r"date:<=(\d{4}-\d{2}-\d{2})"
    match = re.search(lte_pattern, query, re.IGNORECASE)
    if match:
        end_date = match.group(1)
        cleaned_query = re.sub(lte_pattern, "", query, flags=re.IGNORECASE)
        return cleaned_query, DateFilter(end_date=end_date, operator="lte")

    # Pattern: date:>YYYY-MM-DD
    gt_pattern = r"date:>(\d{4}-\d{2}-\d{2})"
    match = re.search(gt_pattern, query, re.IGNORECASE)
    if match:
        start_date = match.group(1)
        cleaned_query = re.sub(gt_pattern, "", query, flags=re.IGNORECASE)
        return cleaned_query, DateFilter(start_date=start_date, operator="gt")

    # Pattern: date:<YYYY-MM-DD
    lt_pattern = r"date:<(\d{4}-\d{2}-\d{2})"
    match = re.search(lt_pattern, query, re.IGNORECASE)
    if match:
        end_date = match.group(1)
        cleaned_query = re.sub(lt_pattern, "", query, flags=re.IGNORECASE)
        return cleaned_query, DateFilter(end_date=end_date, operator="lt")

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
    query = re.sub(r"\band\b", "AND", query, flags=re.IGNORECASE)
    query = re.sub(r"\bor\b", "OR", query, flags=re.IGNORECASE)
    query = re.sub(r"\bnot\b", "NOT", query, flags=re.IGNORECASE)
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
    query = re.sub(r"\s+-(\S+)", r" NOT \1", query)
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
            return f"{fts_field}:{value}"
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
        return f"__QUOTE_{len(quotes) - 1}__"

    query = re.sub(r'"[^"]*"', save_quote, query)

    # Split into tokens
    tokens = query.split()

    # Process tokens to add implicit AND
    result = []
    operators = {"AND", "OR", "NOT"}

    for i, token in enumerate(tokens):
        result.append(token)

        # Check if we need to add AND after this token
        if i < len(tokens) - 1:
            next_token = tokens[i + 1]

            # Don't add AND if current token is an operator
            if token in operators:
                continue

            # Don't add AND if next token is an operator (except NOT)
            if next_token in {"AND", "OR"}:
                continue

            # Don't add AND if next token is NOT (it's already a binary operator position)
            # Actually, NOT can be unary, so we might need AND before it
            # Example: "moth NOT luna" is valid, but "moth luna" should be "moth AND luna"
            # Let's check if the previous token was an operator
            if i > 0 and result[-2] in {"AND", "OR"}:
                # We already have an operator before this
                if next_token == "NOT":
                    # This is a new clause: "moth AND NOT luna" - don't add another AND
                    continue
                else:
                    # Add AND before next term
                    result.append("AND")
            else:
                # No operator before, add AND (unless next is NOT in binary position)
                if next_token != "NOT":
                    result.append("AND")

    # Restore quoted strings
    result_str = " ".join(result)
    for i, quote in enumerate(quotes):
        result_str = result_str.replace(f"__QUOTE_{i}__", quote)

    return result_str


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "parse_query",
    "validate_query",
    "ParsedQuery",
    "DateFilter",
    "FIELD_MAPPINGS",
    "MAX_QUERY_LENGTH",
    "MAX_QUERY_TERMS",
    "MAX_TERM_LENGTH",
    "MAX_PHRASE_LENGTH",
    "MAX_PARENTHESIS_DEPTH",
]

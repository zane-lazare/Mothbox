"""
Search Engine for Mothbox Photo Gallery (Issue #131 - Phase 1.1)

Provides full-text search over photo metadata using SQLite FTS5.
Indexes photo filenames, tags, species, notes, and custom fields.

Features:
- SQLite FTS5 full-text search with Porter stemming
- Prefix search (query*)
- Phrase search ("exact phrase")
- Case-insensitive search
- Date extraction from Mothbox filenames
- Thread-safe database operations
- Automatic schema creation and migration

Performance Target: <100ms for typical searches

Usage:
    from webui.backend.lib.search_engine import SearchEngine

    engine = SearchEngine(db_path)
    engine.index_photo(filepath, metadata)
    results = engine.search("moth", limit=20, offset=0)
    engine.close()

    # Or use as context manager
    with SearchEngine(db_path) as engine:
        results = engine.search("luna")
"""

import contextlib
import json
import logging
import re
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

# Mothbox filename pattern: name_YYYY_MM_DD__HH_MM_SS.jpg
MOTHBOX_FILENAME_PATTERN = re.compile(
    r'(?P<name>.+?)_(?P<year>\d{4})_(?P<month>\d{2})_(?P<day>\d{2})__'
    r'(?P<hour>\d{2})_(?P<minute>\d{2})_(?P<second>\d{2})'
)

# Default field weights for ranking (higher = more important)
DEFAULT_FIELD_WEIGHTS = {
    'tags': 2.0,           # User-assigned tags are most relevant
    'species': 1.8,        # Species identification important
    'species_common_name': 1.5,  # Common names slightly less
    'filename': 1.2,       # Filename matches useful
    'notes': 1.0,          # Notes are general context
    'custom_fields': 0.8,  # Custom fields lower priority
    'date': 0.5,           # Date rarely searched directly
}

# Match type multipliers for ranking
DEFAULT_MATCH_MULTIPLIERS = {
    'exact': 1.0,      # Exact term match
    'prefix': 0.9,     # Prefix match (luna*)
    'phrase': 1.1,     # Phrase match ("luna moth") - boost for precision
}


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class SearchMatch:
    """Single search result match.

    Attributes:
        filepath: Relative path from PHOTOS_DIR
        filename: Original filename
        score: Final weighted relevance score (higher = more relevant)
        matched_fields: List of field names that matched the query
        metadata: Full metadata dictionary for the photo
        bm25_score: Raw FTS5 BM25 score before field weighting
        match_type: Type of match ('exact', 'prefix', or 'phrase')
    """
    filepath: str
    filename: str
    score: float
    matched_fields: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)
    bm25_score: float = 0.0
    match_type: str = 'exact'


@dataclass
class SearchResult:
    """Search results container.

    Attributes:
        results: List of SearchMatch objects
        total: Total number of matching documents (before pagination)
        took_ms: Query execution time in milliseconds
    """
    results: list[SearchMatch]
    total: int
    took_ms: float


# ============================================================================
# Search Engine
# ============================================================================

class SearchEngine:
    """SQLite FTS5 search engine for photo metadata.

    Thread-safe search engine using SQLite FTS5 for full-text search.
    Automatically creates database and schema if they don't exist.

    Schema:
        - filename: Original filename
        - filepath: Relative path from PHOTOS_DIR
        - tags: Space-separated tags
        - species: Species scientific name
        - species_common_name: Species common name
        - notes: Full-text notes
        - custom_fields: JSON-serialized custom data
        - date: ISO date extracted from filename

    Example:
        >>> engine = SearchEngine(Path("/var/lib/mothbox/cache/search.db"))
        >>> engine.index_photo("photos/moth.jpg", {"tags": ["luna_moth"]})
        >>> results = engine.search("luna")
        >>> print(f"Found {results.total} photos in {results.took_ms}ms")
        >>> engine.close()
    """

    def __init__(
        self,
        db_path: Path,
        field_weights: dict = None,
        match_multipliers: dict = None
    ):
        """Initialize search engine and create database if needed.

        Args:
            db_path: Path to SQLite database file
            field_weights: Custom field weights for ranking (optional)
            match_multipliers: Custom match type multipliers for ranking (optional)

        Raises:
            sqlite3.Error: If database initialization fails
        """
        self.db_path = Path(db_path)
        self._lock = threading.RLock()

        # Initialize field weights and match multipliers
        self.field_weights = field_weights if field_weights is not None else DEFAULT_FIELD_WEIGHTS.copy()
        self.match_multipliers = match_multipliers if match_multipliers is not None else DEFAULT_MATCH_MULTIPLIERS.copy()

        # Create parent directories if they don't exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database connection and schema
        self._init_database()

        logger.debug(f"SearchEngine initialized with database: {self.db_path}")

    def _init_database(self):
        """Initialize database connection and create schema.

        Creates FTS5 table if it doesn't exist. Handles corrupted databases
        by recreating them.
        """
        try:
            # Try to connect and create schema
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self.create_index()

        except sqlite3.DatabaseError as e:
            # Database is corrupted, recreate it
            logger.warning(f"Database corrupted, recreating: {e}")
            self._conn.close()
            self.db_path.unlink(missing_ok=True)

            # Recreate database
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self.create_index()

    def create_index(self):
        """Create FTS5 virtual table if not exists.

        Uses Porter stemming and Unicode61 tokenizer for better search quality.
        Idempotent - safe to call multiple times.
        """
        with self._lock:
            cursor = self._conn.cursor()

            # Create FTS5 virtual table
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS photo_search USING fts5(
                    filename,
                    filepath UNINDEXED,
                    tags,
                    species,
                    species_common_name,
                    notes,
                    custom_fields,
                    date,
                    tokenize='porter unicode61'
                )
            """)

            self._conn.commit()
            logger.debug("FTS5 table created/verified")

    def index_photo(self, filepath: str, metadata: dict[str, Any]):
        """Add or update photo in search index.

        Extracts searchable fields from metadata and indexes them in FTS5.
        If filepath already exists, updates the existing entry.

        Args:
            filepath: Relative path from PHOTOS_DIR (used as unique key)
            metadata: Photo metadata dictionary with optional fields:
                - filename: str
                - tags: List[str] or None
                - species: str or None
                - species_common_name: str or None
                - notes: str or None
                - custom_fields: dict or None

        Example:
            >>> engine.index_photo("photos/moth.jpg", {
            ...     "filename": "moth.jpg",
            ...     "tags": ["luna_moth", "nocturnal"],
            ...     "species": "Actias luna",
            ...     "notes": "Beautiful green moth"
            ... })
        """
        with self._lock:
            cursor = self._conn.cursor()

            # Extract fields from metadata
            filename = metadata.get('filename', Path(filepath).name)
            tags = metadata.get('tags', [])
            species = metadata.get('species')
            species_common_name = metadata.get('species_common_name')
            notes = metadata.get('notes')
            custom_fields = metadata.get('custom_fields', {})

            # Convert tags list to space-separated string for FTS5
            tags_str = ' '.join(tags) if tags else ''

            # Serialize custom fields to JSON string
            custom_fields_str = json.dumps(custom_fields) if custom_fields else ''

            # Extract date from Mothbox filename pattern
            date_str = self._extract_date_from_filename(filename)

            # Delete existing entry for this filepath (if any)
            cursor.execute(
                "DELETE FROM photo_search WHERE filepath = ?",
                (filepath,)
            )

            # Insert new entry
            cursor.execute("""
                INSERT INTO photo_search (
                    filename, filepath, tags, species, species_common_name,
                    notes, custom_fields, date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                filename,
                filepath,
                tags_str,
                species or '',
                species_common_name or '',
                notes or '',
                custom_fields_str,
                date_str
            ))

            self._conn.commit()
            logger.debug(f"Indexed photo: {filepath}")

    def remove_photo(self, filepath: str):
        """Remove photo from search index.

        Idempotent - safe to call even if photo doesn't exist in index.

        Args:
            filepath: Relative path from PHOTOS_DIR

        Example:
            >>> engine.remove_photo("photos/moth.jpg")
        """
        with self._lock:
            cursor = self._conn.cursor()

            cursor.execute(
                "DELETE FROM photo_search WHERE filepath = ?",
                (filepath,)
            )

            self._conn.commit()
            logger.debug(f"Removed photo from index: {filepath}")

    def search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0
    ) -> SearchResult:
        """Search for photos matching query.

        Supports FTS5 query syntax:
        - Simple terms: "moth"
        - Prefix search: "lun*"
        - Phrase search: "luna moth"
        - Boolean operators: "moth AND night"

        Args:
            query: Search query string
            limit: Maximum number of results to return
            offset: Number of results to skip (for pagination)

        Returns:
            SearchResult with matches, total count, and timing

        Example:
            >>> results = engine.search("luna moth", limit=10)
            >>> for match in results.results:
            ...     print(f"{match.filename}: {match.score}")
        """
        start_time = time.time()

        # Handle empty query
        if not query or not query.strip():
            return SearchResult(results=[], total=0, took_ms=0.0)

        with self._lock:
            cursor = self._conn.cursor()

            try:
                # Detect match type from query
                match_type = self._detect_match_type(query)

                # Get total count (without pagination)
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM photo_search
                    WHERE photo_search MATCH ?
                """, (query,))

                total = cursor.fetchone()['count']

                # Get all results with BM25 score (we'll apply ranking and pagination after)
                # Note: FTS5 bm25() returns negative scores where lower = better match
                # We'll negate it to make higher = better for intuitive ranking
                cursor.execute("""
                    SELECT
                        filename,
                        filepath,
                        tags,
                        species,
                        species_common_name,
                        notes,
                        custom_fields,
                        date,
                        bm25(photo_search) as bm25_score
                    FROM photo_search
                    WHERE photo_search MATCH ?
                """, (query,))

                results = []
                for row in cursor.fetchall():
                    # Determine which fields matched
                    matched_fields = self._get_matched_fields(row, query)

                    # Parse custom fields JSON
                    custom_fields = {}
                    if row['custom_fields']:
                        with contextlib.suppress(json.JSONDecodeError):
                            custom_fields = json.loads(row['custom_fields'])

                    # Parse tags back to list
                    tags = row['tags'].split() if row['tags'] else []

                    # Build metadata dictionary
                    metadata = {
                        'filename': row['filename'],
                        'filepath': row['filepath'],
                        'tags': tags,
                        'species': row['species'] or None,
                        'species_common_name': row['species_common_name'] or None,
                        'notes': row['notes'] or None,
                        'custom_fields': custom_fields,
                        'date': row['date'] or None
                    }

                    # Get raw BM25 score (negate since FTS5 uses negative scores)
                    bm25_score = abs(float(row['bm25_score']))

                    # Calculate final weighted score
                    final_score = self._calculate_score(bm25_score, matched_fields, match_type)

                    match = SearchMatch(
                        filepath=row['filepath'],
                        filename=row['filename'],
                        score=final_score,
                        matched_fields=matched_fields,
                        metadata=metadata,
                        bm25_score=bm25_score,
                        match_type=match_type
                    )
                    results.append(match)

                # Sort by final score (descending - higher is better)
                results.sort(key=lambda x: x.score, reverse=True)

                # Apply pagination after sorting
                paginated_results = results[offset:offset + limit]

                took_ms = (time.time() - start_time) * 1000

                return SearchResult(
                    results=paginated_results,
                    total=total,
                    took_ms=took_ms
                )

            except sqlite3.OperationalError as e:
                # Handle FTS5 query syntax errors gracefully
                logger.warning(f"Invalid FTS5 query '{query}': {e}")
                took_ms = (time.time() - start_time) * 1000
                return SearchResult(results=[], total=0, took_ms=took_ms)

    def get_stats(self) -> dict[str, Any]:
        """Get index statistics.

        Returns:
            Dictionary with:
            - total_documents: Number of photos in index
            - db_path: Path to database file

        Example:
            >>> stats = engine.get_stats()
            >>> print(f"Index contains {stats['total_documents']} photos")
        """
        with self._lock:
            cursor = self._conn.cursor()

            cursor.execute("SELECT COUNT(*) as count FROM photo_search")
            total_documents = cursor.fetchone()['count']

            return {
                'total_documents': total_documents,
                'db_path': str(self.db_path)
            }

    def close(self):
        """Close database connection.

        Safe to call multiple times.

        Example:
            >>> engine.close()
        """
        with self._lock:
            if hasattr(self, '_conn'):
                self._conn.close()
                logger.debug("SearchEngine closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes database."""
        self.close()

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _detect_match_type(self, query: str) -> str:
        """Detect the type of match from the query string.

        Args:
            query: Search query string

        Returns:
            Match type: 'phrase', 'prefix', or 'exact'

        Example:
            >>> engine._detect_match_type('"luna moth"')
            'phrase'
            >>> engine._detect_match_type('luna*')
            'prefix'
            >>> engine._detect_match_type('luna')
            'exact'
        """
        # Check for phrase match (contains quotes)
        if '"' in query:
            return 'phrase'

        # Check for prefix match (contains asterisk)
        if '*' in query:
            return 'prefix'

        # Default to exact match
        return 'exact'

    def _calculate_score(
        self,
        bm25_score: float,
        matched_fields: list[str],
        match_type: str = 'exact'
    ) -> float:
        """Calculate final relevance score with field weighting.

        Applies field weights and match type multipliers to the raw BM25 score.

        Formula: final_score = bm25_score * avg_field_weight * match_type_multiplier

        Args:
            bm25_score: Raw FTS5 BM25 score
            matched_fields: List of field names that matched
            match_type: Type of match ('exact', 'prefix', 'phrase')

        Returns:
            Final weighted score (higher = more relevant)

        Example:
            >>> engine._calculate_score(1.5, ['tags', 'species'], 'exact')
            2.85  # 1.5 * ((2.0 + 1.8) / 2) * 1.0
        """
        # Get match type multiplier
        match_multiplier = self.match_multipliers.get(match_type, 1.0)

        # Calculate average field weight for matched fields
        if matched_fields:
            field_weights_sum = sum(
                self.field_weights.get(field, 1.0) for field in matched_fields
            )
            avg_field_weight = field_weights_sum / len(matched_fields)
        else:
            # No matched fields detected, use default weight
            avg_field_weight = 1.0

        # Calculate final score
        final_score = bm25_score * avg_field_weight * match_multiplier

        return final_score

    def _extract_date_from_filename(self, filename: str) -> str:
        """Extract ISO date from Mothbox filename pattern.

        Args:
            filename: Photo filename (e.g., "moth_2024_01_15__10_30_00.jpg")

        Returns:
            ISO date string (e.g., "2024-01-15") or empty string

        Example:
            >>> engine._extract_date_from_filename("moth_2024_01_15__10_30_00.jpg")
            '2024-01-15'
        """
        match = MOTHBOX_FILENAME_PATTERN.search(filename)
        if match:
            year = match.group('year')
            month = match.group('month')
            day = match.group('day')
            return f"{year}-{month}-{day}"
        return ''

    def _get_matched_fields(self, row: sqlite3.Row, query: str) -> list[str]:
        """Determine which fields matched the search query.

        Simple heuristic: check if query terms appear in each field.
        This is approximate - FTS5 doesn't expose per-field match info easily.

        Args:
            row: Database row with search result
            query: Original search query

        Returns:
            List of field names that likely matched

        Example:
            >>> engine._get_matched_fields(row, "luna moth")
            ['tags', 'species_common_name']
        """
        matched = []

        # Extract search terms (remove FTS5 operators)
        # Simple approach: split on whitespace and remove special chars
        terms = query.lower().replace('"', '').replace('*', '').split()

        # Check each field
        fields_to_check = [
            ('filename', row['filename']),
            ('tags', row['tags']),
            ('species', row['species']),
            ('species_common_name', row['species_common_name']),
            ('notes', row['notes']),
            ('custom_fields', row['custom_fields']),
            ('date', row['date'])
        ]

        for field_name, field_value in fields_to_check:
            if not field_value:
                continue

            field_lower = str(field_value).lower()

            # Check if any term appears in this field
            for term in terms:
                if term and term in field_lower:
                    matched.append(field_name)
                    break  # Only add field once

        return matched


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    'SearchEngine',
    'SearchResult',
    'SearchMatch',
    'DEFAULT_FIELD_WEIGHTS',
    'DEFAULT_MATCH_MULTIPLIERS',
]

"""
Search Engine for Mothbox Photo Gallery

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
    'file_ext': 0.5,       # Low priority - file type rarely primary search criteria
    'exif_iso': 0.3,       # EXIF ISO value
    'exif_aperture': 0.3,  # EXIF aperture (f-stop)
    'exif_shutter': 0.3,   # EXIF shutter speed
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
        highlights: Dict mapping field names to highlighted text with <mark> tags
    """
    filepath: str
    filename: str
    score: float
    matched_fields: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)
    bm25_score: float = 0.0
    match_type: str = 'exact'
    highlights: dict[str, str] = field(default_factory=dict)


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
        - file_ext: File extension (jpg, png, dng, mp4, etc.)
        - exif_iso: ISO value from EXIF (e.g., "3200")
        - exif_aperture: Aperture f-number from EXIF (e.g., "2.8")
        - exif_shutter: Shutter speed in seconds from EXIF (e.g., "0.001")

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
        """Create FTS5 virtual table and metadata tracking table if not exists.

        Uses Porter stemming and Unicode61 tokenizer for better search quality.
        Also creates a regular table for tracking index metadata (mtime, indexed_at)
        to support incremental updates.

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
                    file_ext,
                    exif_iso,
                    exif_aperture,
                    exif_shutter,
                    tokenize='porter unicode61'
                )
            """)

            # Create metadata tracking table for incremental sync
            # This tracks when each photo was indexed and the sidecar's mtime
            # to efficiently detect which photos need re-indexing
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS photo_index_metadata (
                    filepath TEXT PRIMARY KEY,
                    sidecar_mtime REAL,
                    indexed_at REAL
                )
            """)

            self._conn.commit()
            logger.debug("FTS5 table and metadata tracking table created/verified")


    def _extract_exif_from_photo(self, photo_path: Path) -> dict[str, str]:
        """Extract EXIF camera settings from photo file.

        Extracts ISO, aperture (f-number), and shutter speed from EXIF data.
        Returns empty strings if EXIF not available or extraction fails.

        Args:
            photo_path: Path to photo file

        Returns:
            Dictionary with keys 'iso', 'aperture', 'shutter' (all strings)

        Example:
            >>> exif = engine._extract_exif_from_photo(Path("photo.jpg"))
            >>> print(exif)
            {'iso': '3200', 'aperture': '2.8', 'shutter': '0.001'}
        """
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS

            with Image.open(photo_path) as img:
                exif_data = img._getexif()
                if not exif_data:
                    return {'iso': '', 'aperture': '', 'shutter': ''}

                result = {'iso': '', 'aperture': '', 'shutter': ''}

                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)

                    if tag == 'ISOSpeedRatings':
                        # ISO can be int or tuple
                        iso = value[0] if isinstance(value, (tuple, list)) else value
                        result['iso'] = str(iso)
                    elif tag == 'FNumber':
                        # FNumber is a ratio (e.g., (28, 10) for f/2.8)
                        if isinstance(value, tuple) and len(value) == 2:
                            result['aperture'] = str(float(value[0]) / float(value[1]))
                        elif hasattr(value, 'numerator') and hasattr(value, 'denominator'):
                            result['aperture'] = str(float(value.numerator) / float(value.denominator))
                        else:
                            result['aperture'] = str(value)
                    elif tag == 'ExposureTime':
                        # ExposureTime is a ratio (e.g., (1, 1000) for 1/1000s)
                        if isinstance(value, tuple) and len(value) == 2:
                            result['shutter'] = str(float(value[0]) / float(value[1]))
                        elif hasattr(value, 'numerator') and hasattr(value, 'denominator'):
                            result['shutter'] = str(float(value.numerator) / float(value.denominator))
                        else:
                            result['shutter'] = str(value)

                return result
        except Exception as e:
            logger.debug(f"Failed to extract EXIF from {photo_path}: {e}")
            return {'iso': '', 'aperture': '', 'shutter': ''}

    def index_photo(
        self,
        filepath: str,
        metadata: dict[str, Any],
        sidecar_mtime: float | None = None
    ):
        """Add or update photo in search index.

        Extracts searchable fields from metadata and indexes them in FTS5.
        If filepath already exists, updates the existing entry.
        Also updates the metadata tracking table for incremental sync support.

        Args:
            filepath: Relative path from PHOTOS_DIR (used as unique key)
            metadata: Photo metadata dictionary with optional fields:
                - filename: str
                - tags: List[str] or None
                - species: str or None
                - species_common_name: str or None
                - notes: str or None
                - custom_fields: dict or None
            sidecar_mtime: Optional mtime of the sidecar file (for incremental sync)

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

            # Extract date - prefer EXIF DateTimeOriginal, fall back to filename pattern
            date_str = metadata.get('exif_date')
            if not date_str:
                date_str = self._extract_date_from_filename(filename)

            # Extract file extension (lowercase, without dot)
            file_ext = Path(filename).suffix.lower().lstrip('.') if '.' in filename else ''

            # Delete existing entry for this filepath (if any)
            cursor.execute(
                "DELETE FROM photo_search WHERE filepath = ?",
                (filepath,)
            )

            # Extract EXIF camera settings from photo file
            from mothbox_paths import PHOTOS_DIR
            photo_path = PHOTOS_DIR / filepath
            exif_data = self._extract_exif_from_photo(photo_path)

            # Insert new entry
            cursor.execute("""
                INSERT INTO photo_search (
                    filename, filepath, tags, species, species_common_name,
                    notes, custom_fields, date, file_ext,
                    exif_iso, exif_aperture, exif_shutter
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                filename,
                filepath,
                tags_str,
                species or '',
                species_common_name or '',
                notes or '',
                custom_fields_str,
                date_str,
                file_ext,
                exif_data['iso'],
                exif_data['aperture'],
                exif_data['shutter']
            ))

            # Update metadata tracking table (for incremental sync)
            indexed_at = time.time()
            cursor.execute("""
                INSERT OR REPLACE INTO photo_index_metadata (filepath, sidecar_mtime, indexed_at)
                VALUES (?, ?, ?)
            """, (filepath, sidecar_mtime, indexed_at))

            self._conn.commit()
            logger.debug(f"Indexed photo: {filepath}")

    def remove_photo(self, filepath: str):
        """Remove photo from search index.

        Also removes the entry from the metadata tracking table.
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

            # Also remove from metadata tracking table
            cursor.execute(
                "DELETE FROM photo_index_metadata WHERE filepath = ?",
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

                # Get all results with BM25 score and highlights
                # Note: FTS5 bm25() returns negative scores where lower = better match
                # We'll negate it to make higher = better for intuitive ranking
                # Column indices for highlight(): 0=filename, 2=tags, 3=species,
                # 4=species_common_name, 5=notes, 8=file_ext, 9=exif_iso,
                # 10=exif_aperture, 11=exif_shutter (1=filepath is UNINDEXED)
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
                        file_ext,
                        exif_iso,
                        exif_aperture,
                        exif_shutter,
                        bm25(photo_search) as bm25_score,
                        highlight(photo_search, 0, '<mark>', '</mark>') as filename_hl,
                        highlight(photo_search, 2, '<mark>', '</mark>') as tags_hl,
                        highlight(photo_search, 3, '<mark>', '</mark>') as species_hl,
                        highlight(photo_search, 4, '<mark>', '</mark>') as species_common_name_hl,
                        highlight(photo_search, 5, '<mark>', '</mark>') as notes_hl,
                        highlight(photo_search, 8, '<mark>', '</mark>') as file_ext_hl,
                        highlight(photo_search, 9, '<mark>', '</mark>') as exif_iso_hl,
                        highlight(photo_search, 10, '<mark>', '</mark>') as exif_aperture_hl,
                        highlight(photo_search, 11, '<mark>', '</mark>') as exif_shutter_hl
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
                        try:
                            custom_fields = json.loads(row['custom_fields'])
                        except json.JSONDecodeError:
                            logger.debug(f"Failed to parse custom_fields JSON for {row['filepath']}")

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
                        'date': row['date'] or None,
                        'file_ext': row['file_ext'] or None
                    }

                    # Get raw BM25 score (negate since FTS5 uses negative scores)
                    bm25_score = abs(float(row['bm25_score']))

                    # Calculate final weighted score
                    final_score = self._calculate_score(bm25_score, matched_fields, match_type)

                    # Build highlights dict from FTS5 highlight() results
                    highlights = self._build_highlights(row)

                    match = SearchMatch(
                        filepath=row['filepath'],
                        filename=row['filename'],
                        score=final_score,
                        matched_fields=matched_fields,
                        metadata=metadata,
                        bm25_score=bm25_score,
                        match_type=match_type,
                        highlights=highlights
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

    def get_all_documents(self, limit: int = 1000, offset: int = 0) -> SearchResult:
        """Get all documents from the index.

        Used for date-only queries where we need to fetch all documents
        and apply date filtering in Python rather than FTS5.

        Args:
            limit: Maximum number of results to return
            offset: Number of results to skip (for pagination)

        Returns:
            SearchResult with all matches (no FTS scoring)

        Example:
            >>> all_docs = engine.get_all_documents(limit=100)
            >>> for match in all_docs.results:
            ...     print(f"{match.filename}: {match.metadata['date']}")
        """
        start_time = time.time()

        with self._lock:
            cursor = self._conn.cursor()

            # Get total count
            cursor.execute("SELECT COUNT(*) as count FROM photo_search")
            total = cursor.fetchone()['count']

            # Get all documents with pagination
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
                    file_ext
                FROM photo_search
                ORDER BY date DESC, filename ASC
                LIMIT ? OFFSET ?
            """, (limit, offset))

            results = []
            for row in cursor.fetchall():
                # Parse custom fields JSON
                custom_fields = {}
                if row['custom_fields']:
                    try:
                        custom_fields = json.loads(row['custom_fields'])
                    except json.JSONDecodeError:
                        logger.debug(f"Failed to parse custom_fields JSON for {row['filepath']}")

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
                    'date': row['date'] or None,
                    'file_ext': row['file_ext'] or None
                }

                match = SearchMatch(
                    filepath=row['filepath'],
                    filename=row['filename'],
                    score=1.0,  # No FTS scoring for date-only queries
                    matched_fields=['date'],
                    metadata=metadata,
                    bm25_score=0.0,
                    match_type='exact'
                )
                results.append(match)

            took_ms = (time.time() - start_time) * 1000

            return SearchResult(
                results=results,
                total=total,
                took_ms=took_ms
            )

    def search_with_date_filter(
        self,
        query: str | None,
        date_filter: dict | None,
        limit: int = 20,
        offset: int = 0
    ) -> SearchResult:
        """Search with optional FTS query and SQL date filter.

        This method combines FTS5 MATCH queries with SQL WHERE clauses for
        efficient date filtering directly in SQLite, avoiding Python-side
        filtering that doesn't scale well for large galleries.

        Args:
            query: FTS5 search query string (optional, can be None/empty for date-only)
            date_filter: Date filter specification with keys:
                - operator: 'range', 'gt', 'gte', 'lt', 'lte'
                - start_date: ISO date string for range start or comparison
                - end_date: ISO date string for range end (only for 'range')
            limit: Maximum number of results to return
            offset: Number of results to skip (for pagination)

        Returns:
            SearchResult with matches, total count, and timing

        Example:
            >>> # Date-only query (no FTS)
            >>> results = engine.search_with_date_filter(
            ...     query=None,
            ...     date_filter={'operator': 'range', 'start_date': '2024-01-01', 'end_date': '2024-01-31'},
            ...     limit=50
            ... )

            >>> # Combined FTS + date filter
            >>> results = engine.search_with_date_filter(
            ...     query='luna moth',
            ...     date_filter={'operator': 'gte', 'start_date': '2024-01-01'},
            ...     limit=20
            ... )
        """
        start_time = time.time()

        with self._lock:
            cursor = self._conn.cursor()

            try:
                where_clauses = []
                params = []
                has_fts_query = query and query.strip()

                # Build date WHERE clause
                if date_filter:
                    operator = date_filter.get('operator')
                    start_date = date_filter.get('start_date')
                    end_date = date_filter.get('end_date')

                    if operator == 'range' and start_date and end_date:
                        where_clauses.append("date BETWEEN ? AND ?")
                        params.extend([start_date, end_date])
                    elif operator == 'gt' and start_date:
                        where_clauses.append("date > ?")
                        params.append(start_date)
                    elif operator == 'gte' and start_date:
                        where_clauses.append("date >= ?")
                        params.append(start_date)
                    elif operator == 'lt' and start_date:
                        where_clauses.append("date < ?")
                        params.append(start_date)
                    elif operator == 'lte' and start_date:
                        where_clauses.append("date <= ?")
                        params.append(start_date)

                # Add FTS MATCH clause if query exists
                if has_fts_query:
                    where_clauses.append("photo_search MATCH ?")
                    params.append(query)

                # Build WHERE clause string
                where_sql = ""
                if where_clauses:
                    where_sql = "WHERE " + " AND ".join(where_clauses)

                # Get total count (where_sql contains only static SQL from controlled operators; user values are parameterized)
                count_sql = f"SELECT COUNT(*) as count FROM photo_search {where_sql}"  # nosec B608
                cursor.execute(count_sql, params)
                total = cursor.fetchone()['count']

                # Build SELECT query
                if has_fts_query:
                    # With FTS query - include BM25 scoring and highlights
                    # where_sql contains only static SQL from controlled operators; user values are parameterized
                    select_sql = (
                        f"SELECT "
                        f"filename, filepath, tags, species, species_common_name, notes, custom_fields, date, file_ext, "
                        f"bm25(photo_search) as bm25_score, "
                        f"highlight(photo_search, 0, '<mark>', '</mark>') as filename_hl, "
                        f"highlight(photo_search, 2, '<mark>', '</mark>') as tags_hl, "
                        f"highlight(photo_search, 3, '<mark>', '</mark>') as species_hl, "
                        f"highlight(photo_search, 4, '<mark>', '</mark>') as species_common_name_hl, "
                        f"highlight(photo_search, 5, '<mark>', '</mark>') as notes_hl, "
                        f"highlight(photo_search, 8, '<mark>', '</mark>') as file_ext_hl "
                        f"FROM photo_search {where_sql} "  # nosec B608
                        f"ORDER BY bm25(photo_search) LIMIT ? OFFSET ?"
                    )
                else:
                    # Date-only query - no FTS scoring, order by date
                    # where_sql contains only static SQL from controlled operators; user values are parameterized
                    select_sql = (
                        f"SELECT filename, filepath, tags, species, species_common_name, notes, "
                        f"custom_fields, date, file_ext FROM photo_search {where_sql} "  # nosec B608
                        f"ORDER BY date DESC, filename ASC LIMIT ? OFFSET ?"
                    )

                # Execute with pagination params
                cursor.execute(select_sql, params + [limit, offset])

                results = []
                match_type = self._detect_match_type(query) if has_fts_query else 'exact'

                for row in cursor.fetchall():
                    # Parse custom fields JSON
                    custom_fields = {}
                    if row['custom_fields']:
                        try:
                            custom_fields = json.loads(row['custom_fields'])
                        except json.JSONDecodeError:
                            logger.debug(f"Failed to parse custom_fields JSON for {row['filepath']}")

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
                        'date': row['date'] or None,
                        'file_ext': row['file_ext'] or None
                    }

                    if has_fts_query:
                        # FTS query - use BM25 scoring
                        bm25_score = abs(float(row['bm25_score']))
                        matched_fields = self._get_matched_fields(row, query)
                        final_score = self._calculate_score(bm25_score, matched_fields, match_type)
                        highlights = self._build_highlights(row)
                    else:
                        # Date-only query - no scoring
                        bm25_score = 0.0
                        matched_fields = ['date']
                        final_score = 1.0
                        highlights = {}

                    match = SearchMatch(
                        filepath=row['filepath'],
                        filename=row['filename'],
                        score=final_score,
                        matched_fields=matched_fields,
                        metadata=metadata,
                        bm25_score=bm25_score,
                        match_type=match_type,
                        highlights=highlights
                    )
                    results.append(match)

                # For FTS queries, we need to re-sort by our calculated score
                # (BM25 ordering is already applied by SQL, but we add field weights)
                if has_fts_query:
                    results.sort(key=lambda x: x.score, reverse=True)

                took_ms = (time.time() - start_time) * 1000

                return SearchResult(
                    results=results,
                    total=total,
                    took_ms=took_ms
                )

            except sqlite3.OperationalError as e:
                # Handle FTS5 query syntax errors gracefully
                logger.warning(f"Invalid query '{query}' with date filter: {e}")
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

    def get_indexed_metadata(self) -> dict[str, float]:
        """Get all indexed filepaths and their sidecar mtimes.

        Used by incremental sync to detect which files need re-indexing.

        Returns:
            Dictionary mapping filepath to sidecar_mtime

        Example:
            >>> indexed = engine.get_indexed_metadata()
            >>> print(indexed['photos/moth.jpg'])
            1704067200.123  # sidecar mtime
        """
        with self._lock:
            cursor = self._conn.cursor()

            cursor.execute("SELECT filepath, sidecar_mtime FROM photo_index_metadata")

            return {
                row['filepath']: row['sidecar_mtime']
                for row in cursor.fetchall()
            }

    def incremental_sync(
        self,
        photos: list[dict],
        index_photo_callback: callable = None
    ) -> dict:
        """Sync index with filesystem changes.

        Performs an incremental update of the search index:
        1. Removes stale entries (photos deleted from filesystem)
        2. Indexes new photos
        3. Re-indexes modified photos (based on sidecar mtime)
        4. Skips unchanged photos

        This is much more efficient than a full rebuild for large galleries
        where only a few files have changed.

        Args:
            photos: List of photo dictionaries with keys:
                - filepath: str (relative path from PHOTOS_DIR)
                - sidecar_mtime: float (os.stat().st_mtime of sidecar file)
                - metadata: dict (photo metadata to index)
            index_photo_callback: Optional callback function to index a single photo.
                Called with (filepath, metadata, sidecar_mtime).
                If not provided, uses self.index_photo directly.

        Returns:
            Statistics dictionary with:
            - indexed: Number of new photos indexed
            - updated: Number of modified photos re-indexed
            - deleted: Number of stale entries removed
            - unchanged: Number of photos skipped (no changes)
            - errors: Number of errors encountered
            - took_ms: Time taken in milliseconds

        Example:
            >>> photos = [
            ...     {'filepath': 'moth.jpg', 'sidecar_mtime': 1704067200.0,
            ...      'metadata': {'tags': ['luna']}},
            ... ]
            >>> stats = engine.incremental_sync(photos)
            >>> print(f"Synced: {stats['indexed']} new, {stats['updated']} updated")
        """
        start_time = time.time()
        stats = {
            'indexed': 0,
            'updated': 0,
            'deleted': 0,
            'unchanged': 0,
            'errors': 0
        }

        with self._lock:
            try:
                # Get currently indexed filepaths and their mtimes
                indexed = self.get_indexed_metadata()

                # Build set of current filesystem filepaths
                current_filepaths = {p['filepath'] for p in photos}

                # 1. Find and remove stale entries (in index but not in filesystem)
                stale_filepaths = set(indexed.keys()) - current_filepaths
                for filepath in stale_filepaths:
                    try:
                        self.remove_photo(filepath)
                        stats['deleted'] += 1
                    except Exception as e:
                        logger.warning(f"Error removing stale photo {filepath}: {e}")
                        stats['errors'] += 1

                # 2. Process each photo from filesystem
                for photo in photos:
                    filepath = photo['filepath']
                    sidecar_mtime = photo.get('sidecar_mtime')
                    metadata = photo.get('metadata', {})

                    try:
                        if filepath not in indexed:
                            # NEW photo - not in index
                            self.index_photo(filepath, metadata, sidecar_mtime)
                            stats['indexed'] += 1
                        elif sidecar_mtime and indexed[filepath] and sidecar_mtime > indexed[filepath]:
                            # MODIFIED photo - sidecar mtime is newer
                            self.index_photo(filepath, metadata, sidecar_mtime)
                            stats['updated'] += 1
                        else:
                            # UNCHANGED photo - skip
                            stats['unchanged'] += 1
                    except Exception as e:
                        logger.warning(f"Error syncing photo {filepath}: {e}")
                        stats['errors'] += 1

                self._conn.commit()

            except Exception as e:
                logger.error(f"Incremental sync failed: {e}")
                stats['errors'] += 1

        stats['took_ms'] = (time.time() - start_time) * 1000
        logger.info(
            f"Incremental sync complete: {stats['indexed']} new, "
            f"{stats['updated']} updated, {stats['deleted']} deleted, "
            f"{stats['unchanged']} unchanged, {stats['errors']} errors, "
            f"{stats['took_ms']:.1f}ms"
        )

        return stats

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

    def _build_highlights(self, row: sqlite3.Row) -> dict[str, str]:
        """Build highlights dictionary from FTS5 highlight() results.

        Only includes fields where the highlighted text contains <mark> tags,
        indicating that a match was found in that field.

        Args:
            row: Database row with highlight columns (*_hl)

        Returns:
            Dictionary mapping field names to highlighted text with <mark> tags

        Example:
            >>> highlights = engine._build_highlights(row)
            >>> print(highlights)
            {'tags': 'nocturnal <mark>luna</mark> moth', 'species': 'Actias <mark>luna</mark>'}
        """
        highlights = {}

        # Map of highlight column names to field names
        highlight_fields = [
            ('filename_hl', 'filename'),
            ('tags_hl', 'tags'),
            ('species_hl', 'species'),
            ('species_common_name_hl', 'species_common_name'),
            ('notes_hl', 'notes'),
            ('file_ext_hl', 'file_ext'),
        ]

        for hl_column, field_name in highlight_fields:
            hl_value = row[hl_column]
            # Only include if the field has highlighted content
            if hl_value and '<mark>' in hl_value:
                highlights[field_name] = hl_value

        return highlights

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

        KNOWN LIMITATION: This uses a simple heuristic that checks if query
        terms appear in each field's text. SQLite FTS5 does not expose
        per-field match information directly, so this is an approximation.

        The heuristic may:
        - Report false positives if a term appears in a field but wasn't
          actually matched by FTS5 (e.g., due to stemming differences)
        - Miss matches that FTS5 found through advanced tokenization
        - Not correctly identify matches for complex queries with operators

        For most common search queries (simple terms, phrases), this provides
        accurate results. The limitation mainly affects edge cases with
        Porter stemming or complex boolean expressions.

        Args:
            row: Database row with search result
            query: Original search query

        Returns:
            List of field names that likely matched (approximate)

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
            ('date', row['date']),
            ('file_ext', row['file_ext'])
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

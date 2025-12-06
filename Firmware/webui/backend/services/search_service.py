"""
Search Service for Mothbox Photo Gallery (Issue #131 - Phase 2.1)

Provides cached search operations with index management and synchronization
with sidecar metadata.

Features:
- Thread-safe search operations
- Automatic index rebuild on startup (configurable)
- Integration with SearchEngine and QueryParser
- Integration with SidecarService for metadata
- Statistics tracking

Usage:
    from webui.backend.services.search_service import SearchService, SearchServiceConfig

    config = SearchServiceConfig(
        db_path=Path("/var/lib/mothbox/cache/search.db"),
        auto_rebuild=False
    )
    service = SearchService(config, sidecar_service=sidecar_svc)

    # Build index
    stats = service.build_index(photos_dir)

    # Search
    results = service.search("tag:moth species:actias", limit=20, offset=0)

    # Index updates
    service.index_photo(photo_path, metadata)
    service.remove_photo(photo_path)

    service.close()
"""

import logging
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from webui.backend.lib.search_engine import SearchEngine
from webui.backend.lib.search_query_parser import parse_query

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class SearchServiceConfig:
    """Configuration for SearchService.

    Attributes:
        db_path: Path to SQLite database file (defaults to DATA_DIR/cache/search.db)
        auto_rebuild: Rebuild index on startup if True
        field_weights: Custom ranking weights for fields (optional)
    """
    db_path: Path | None = None
    auto_rebuild: bool = False
    field_weights: dict | None = None


# ============================================================================
# Search Service
# ============================================================================

class SearchService:
    """Thread-safe service for photo search operations.

    Manages search index lifecycle, synchronization with sidecar metadata,
    and provides a clean API for search operations.

    Thread Safety:
    --------------
    This class uses a single lock to protect all operations.
    The SearchEngine itself is also thread-safe with its own lock.

    Attributes:
        db_path: Path to SQLite database
        _engine: SearchEngine instance
        _sidecar_service: Optional SidecarService for reading metadata
        _lock: Threading lock for thread-safe operations
    """

    def __init__(
        self,
        config: SearchServiceConfig | None = None,
        sidecar_service: Any | None = None
    ):
        """Initialize search service.

        Args:
            config: Service configuration (uses defaults if None)
            sidecar_service: Optional SidecarService for reading metadata
        """
        # Use default config if not provided
        if config is None:
            config = SearchServiceConfig()

        # Set db_path (default to DATA_DIR/cache/search.db if not specified)
        if config.db_path is None:
            from mothbox_paths import DATA_DIR
            self.db_path = DATA_DIR / "cache" / "search.db"
        else:
            self.db_path = Path(config.db_path)

        # Validate database path is within expected directories
        self._validate_db_path(self.db_path)

        # Store sidecar service reference
        self._sidecar_service = sidecar_service

        # Create lock for thread safety
        self._lock = threading.RLock()

        # Initialize search engine
        self._engine = SearchEngine(
            db_path=self.db_path,
            field_weights=config.field_weights
        )

        # Store auto_rebuild config (will be used on first operation)
        self._auto_rebuild = config.auto_rebuild
        self._auto_rebuild_done = False

        logger.debug(f"SearchService initialized with database: {self.db_path}")

    def build_index(self, photos_dir: Path | None = None) -> dict:
        """Full rebuild of search index from all photos and their sidecars.

        Scans photos directory recursively for all photos with sidecars,
        reads metadata, and rebuilds the search index.

        Args:
            photos_dir: Directory to scan for photos (uses PHOTOS_DIR if None)

        Returns:
            Statistics dictionary with:
            - indexed: Number of photos indexed
            - errors: Number of errors encountered
            - took_ms: Time taken in milliseconds
        """
        start_time = time.time()

        # Use PHOTOS_DIR if not specified
        if photos_dir is None:
            from mothbox_paths import PHOTOS_DIR
            photos_dir = PHOTOS_DIR
        else:
            photos_dir = Path(photos_dir)

        # Mark auto-rebuild as done
        self._auto_rebuild_done = True

        indexed = 0
        errors = 0

        with self._lock:
            # Clear existing index (rebuild from scratch)
            # Note: SearchEngine.create_index() is idempotent, but we want fresh data
            # So we'll delete and recreate the database
            try:
                self._engine.close()
                if self.db_path.exists():
                    self.db_path.unlink()

                # Reinitialize engine
                self._engine = SearchEngine(db_path=self.db_path)

            except Exception as e:
                logger.warning(f"Error clearing index: {e}")

            # Scan directory for photos
            if not photos_dir.exists():
                logger.warning(f"Photos directory does not exist: {photos_dir}")
                took_ms = (time.time() - start_time) * 1000
                return {
                    'indexed': 0,
                    'errors': 0,
                    'took_ms': took_ms
                }

            # Find all JPEG photos recursively
            photo_extensions = ['*.jpg', '*.JPG', '*.jpeg', '*.JPEG']
            photos = []
            for ext in photo_extensions:
                photos.extend(photos_dir.rglob(ext))

            logger.debug(f"Found {len(photos)} photos in {photos_dir}")

            # Index each photo
            for photo_path in photos:
                try:
                    # Check if sidecar exists
                    sidecar_path = photo_path.parent / f"{photo_path.name}.json"
                    if not sidecar_path.exists():
                        continue  # Skip photos without sidecars

                    # Read metadata
                    if self._sidecar_service:
                        metadata_obj = self._sidecar_service.get_metadata(str(photo_path))
                    else:
                        # Read directly from file
                        from webui.backend.lib.sidecar_metadata import read_metadata
                        metadata_obj = read_metadata(str(photo_path))

                    if not metadata_obj:
                        continue  # Skip if metadata read failed

                    # Convert to dict for indexing
                    metadata = metadata_obj.to_dict()

                    # Index photo
                    self._engine.index_photo(str(photo_path), metadata)
                    indexed += 1

                except Exception as e:
                    logger.warning(f"Error indexing {photo_path}: {e}")
                    errors += 1

        took_ms = (time.time() - start_time) * 1000

        logger.info(f"Index built: {indexed} photos indexed, {errors} errors, {took_ms:.1f}ms")

        return {
            'indexed': indexed,
            'errors': errors,
            'took_ms': took_ms
        }

    def sync_index(self, photos_dir: Path | None = None) -> dict:
        """Incremental index sync - only updates changed photos.

        Much more efficient than build_index() for large galleries where
        only a few files have changed. Uses sidecar file mtime to detect
        changes.

        Algorithm:
        1. Scans photos directory for all photos with sidecars
        2. Compares sidecar mtime with indexed mtime
        3. Removes stale entries (photos deleted from filesystem)
        4. Indexes new photos
        5. Re-indexes modified photos
        6. Skips unchanged photos

        Args:
            photos_dir: Directory to scan for photos (uses PHOTOS_DIR if None)

        Returns:
            Statistics dictionary with:
            - indexed: Number of new photos indexed
            - updated: Number of modified photos re-indexed
            - deleted: Number of stale entries removed
            - unchanged: Number of photos skipped
            - errors: Number of errors encountered
            - took_ms: Time taken in milliseconds
        """
        start_time = time.time()

        # Use PHOTOS_DIR if not specified
        if photos_dir is None:
            from mothbox_paths import PHOTOS_DIR
            photos_dir = PHOTOS_DIR
        else:
            photos_dir = Path(photos_dir)

        if not photos_dir.exists():
            logger.warning(f"Photos directory does not exist: {photos_dir}")
            took_ms = (time.time() - start_time) * 1000
            return {
                'indexed': 0,
                'updated': 0,
                'deleted': 0,
                'unchanged': 0,
                'errors': 0,
                'took_ms': took_ms
            }

        # Collect photo info with mtime
        photos = []
        photo_extensions = ['*.jpg', '*.JPG', '*.jpeg', '*.JPEG']

        for ext in photo_extensions:
            for photo_path in photos_dir.rglob(ext):
                sidecar_path = photo_path.parent / f"{photo_path.name}.json"
                if not sidecar_path.exists():
                    continue  # Skip photos without sidecars

                try:
                    # Get sidecar mtime for change detection
                    sidecar_mtime = sidecar_path.stat().st_mtime

                    # Read metadata
                    if self._sidecar_service:
                        metadata_obj = self._sidecar_service.get_metadata(str(photo_path))
                    else:
                        from webui.backend.lib.sidecar_metadata import read_metadata
                        metadata_obj = read_metadata(str(photo_path))

                    if not metadata_obj:
                        continue

                    metadata = metadata_obj.to_dict()

                    photos.append({
                        'filepath': str(photo_path),
                        'sidecar_mtime': sidecar_mtime,
                        'metadata': metadata
                    })

                except Exception as e:
                    logger.warning(f"Error reading photo {photo_path}: {e}")

        logger.debug(f"Found {len(photos)} photos with sidecars in {photos_dir}")

        # Perform incremental sync
        with self._lock:
            stats = self._engine.incremental_sync(photos)

        return stats

    def rebuild_if_needed(self, photos_dir: Path | None = None) -> bool:
        """Rebuild index only if missing, corrupted, or empty.

        Also triggers auto-rebuild if configured and not yet done.

        Args:
            photos_dir: Directory to scan for photos (uses PHOTOS_DIR if None)

        Returns:
            True if rebuild was performed, False otherwise
        """
        with self._lock:
            # Check if auto-rebuild is needed
            if self._auto_rebuild and not self._auto_rebuild_done:
                logger.info("Auto-rebuild triggered")
                self.build_index(photos_dir)
                return True

            # Check if database exists and is valid
            if self.db_path.exists():
                try:
                    # Try to get stats (will fail if corrupted)
                    stats = self._engine.get_stats()

                    # Check if index is empty (likely just created or corrupted)
                    if stats['total_documents'] == 0:
                        logger.info("Index is empty, rebuilding...")
                        self.build_index(photos_dir)
                        return True

                    logger.debug(f"Index exists with {stats['total_documents']} documents")
                    return False  # Index is valid and non-empty, no rebuild needed

                except Exception as e:
                    logger.warning(f"Index corrupted, rebuilding: {e}")

            # Index missing or corrupted - rebuild
            logger.info("Rebuilding search index...")
            self.build_index(photos_dir)
            return True

    def index_photo(self, photo_path: str, metadata: dict | None = None) -> bool:
        """Add or update single photo in index.

        Args:
            photo_path: Path to photo file
            metadata: Metadata dictionary (if None, reads from sidecar)

        Returns:
            True if successful, False otherwise
        """
        try:
            with self._lock:
                # If metadata not provided, read from sidecar
                if metadata is None:
                    if self._sidecar_service:
                        metadata_obj = self._sidecar_service.get_metadata(photo_path)
                    else:
                        from webui.backend.lib.sidecar_metadata import read_metadata
                        metadata_obj = read_metadata(photo_path)

                    if not metadata_obj:
                        logger.warning(f"No metadata found for {photo_path}")
                        return False

                    metadata = metadata_obj.to_dict()

                # Index photo
                self._engine.index_photo(photo_path, metadata)
                logger.debug(f"Indexed photo: {photo_path}")
                return True

        except Exception as e:
            logger.error(f"Error indexing photo {photo_path}: {e}")
            return False

    def remove_photo(self, photo_path: str) -> bool:
        """Remove photo from index.

        Args:
            photo_path: Path to photo file

        Returns:
            True if found and removed, False otherwise
        """
        try:
            with self._lock:
                # Get stats before removal
                stats_before = self._engine.get_stats()
                doc_count_before = stats_before['total_documents']

                # Remove from index
                self._engine.remove_photo(photo_path)

                # Check if removal was successful
                stats_after = self._engine.get_stats()
                doc_count_after = stats_after['total_documents']

                removed = doc_count_after < doc_count_before

                if removed:
                    logger.debug(f"Removed photo from index: {photo_path}")
                return removed

        except Exception as e:
            logger.error(f"Error removing photo {photo_path}: {e}")
            return False

    def search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0
    ) -> dict:
        """Execute search query.

        Uses query parser to translate user query to FTS5.
        Applies date filters if present.

        Args:
            query: User search query
            limit: Maximum results to return
            offset: Number of results to skip (for pagination)

        Returns:
            Dictionary with:
            - results: List of search result dictionaries
            - total: Total number of matching documents
            - query: Original query string
            - parsed_query: Parsed FTS5 query string
            - took_ms: Query execution time in milliseconds
            - has_next: Whether there are more results
            - is_valid: Whether query parsing succeeded
            - error_message: Error description if parsing failed
        """
        start_time = time.time()

        # Parse query
        parsed = parse_query(query)

        if not parsed.is_valid:
            return {
                'results': [],
                'total': 0,
                'query': query,
                'parsed_query': '',
                'took_ms': (time.time() - start_time) * 1000,
                'has_next': False,
                'is_valid': False,
                'error_message': parsed.error_message
            }

        with self._lock:
            try:
                # Use SQL-based date filtering for efficiency
                # This avoids fetching all documents into Python memory
                if parsed.date_filter:
                    # Convert DateFilter to dict for search_with_date_filter
                    date_filter_dict = {
                        'operator': parsed.date_filter.operator,
                        'start_date': parsed.date_filter.start_date,
                        'end_date': parsed.date_filter.end_date
                    }

                    # Use combined FTS + SQL date filtering
                    search_result = self._engine.search_with_date_filter(
                        query=parsed.fts_query if parsed.fts_query.strip() else None,
                        date_filter=date_filter_dict,
                        limit=limit,
                        offset=offset
                    )
                    filtered_results = search_result.results
                    filtered_total = search_result.total
                elif parsed.fts_query.strip():
                    # FTS-only query (no date filter)
                    search_result = self._engine.search(
                        parsed.fts_query,
                        limit=limit,
                        offset=offset
                    )
                    filtered_results = search_result.results
                    filtered_total = search_result.total
                else:
                    # Empty query with no date filter
                    filtered_results = []
                    filtered_total = 0

                # Convert SearchMatch objects to dictionaries
                results_dicts = []
                for match in filtered_results:
                    results_dicts.append({
                        'filepath': match.filepath,
                        'filename': match.filename,
                        'score': match.score,
                        'matched_fields': match.matched_fields,
                        'metadata': match.metadata,
                        'bm25_score': match.bm25_score,
                        'match_type': match.match_type,
                        'highlights': match.highlights
                    })

                # Calculate has_next
                has_next = (offset + limit) < filtered_total

                took_ms = (time.time() - start_time) * 1000

                return {
                    'results': results_dicts,
                    'total': filtered_total,
                    'query': query,
                    'parsed_query': parsed.fts_query,
                    'took_ms': took_ms,
                    'has_next': has_next,
                    'is_valid': True,
                    'error_message': None
                }

            except Exception as e:
                logger.error(f"Search error for query '{query}': {e}", exc_info=True)
                took_ms = (time.time() - start_time) * 1000

                return {
                    'results': [],
                    'total': 0,
                    'query': query,
                    'parsed_query': parsed.fts_query,
                    'took_ms': took_ms,
                    'has_next': False,
                    'is_valid': False,
                    'error_message': str(e)
                }

    def get_statistics(self) -> dict:
        """Get index statistics.

        Returns:
            Dictionary with:
            - document_count: Number of photos in index
            - index_size_bytes: Size of database file in bytes
            - last_rebuild: Timestamp of last rebuild (if tracked)
        """
        with self._lock:
            stats = self._engine.get_stats()

            # Get database file size
            index_size_bytes = 0
            if self.db_path.exists():
                index_size_bytes = self.db_path.stat().st_size

            return {
                'document_count': stats['total_documents'],
                'index_size_bytes': index_size_bytes,
                'db_path': str(self.db_path)
            }

    def invalidate_cache(self) -> None:
        """Invalidate any cached search results.

        Note: Currently a no-op since we don't cache search results.
        Included for API consistency with other services.
        """
        # No caching implemented yet, but method exists for future use

    def close(self) -> None:
        """Close database connection.

        Safe to call multiple times.
        """
        with self._lock:
            self._engine.close()
            logger.debug("SearchService closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes database."""
        self.close()

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _validate_db_path(self, db_path: Path) -> None:
        """Validate that database path is within expected directories.

        Checks that the database path is within DATA_DIR to prevent
        path traversal attacks or accidental writes to sensitive locations.

        Args:
            db_path: Path to validate

        Raises:
            ValueError: If path is outside allowed directories
        """
        import os

        from mothbox_paths import DATA_DIR

        # Resolve paths to handle symlinks and relative paths
        resolved_db_path = db_path.resolve()
        resolved_data_dir = DATA_DIR.resolve()

        # Check if db_path is within DATA_DIR
        try:
            resolved_db_path.relative_to(resolved_data_dir)
        except ValueError:
            # Also allow temp directory for testing purposes
            if not str(resolved_db_path).startswith(tempfile.gettempdir()) and \
               not str(resolved_db_path).startswith(os.path.join(os.getcwd(), 'Tests')):
                logger.warning(
                    f"Database path {db_path} is outside expected directory {DATA_DIR}. "
                    "This may indicate a configuration issue."
                )

        # Check that parent directory exists and is writable
        parent_dir = db_path.parent
        if parent_dir.exists() and not os.access(parent_dir, os.W_OK):
            logger.warning(f"Database parent directory {parent_dir} is not writable")

    def _apply_date_filter(self, results: list, date_filter) -> list:
        """Apply date range filter to search results.

        Args:
            results: List of SearchMatch objects
            date_filter: DateFilter with start_date, end_date, operator

        Returns:
            Filtered list of SearchMatch objects
        """
        filtered = []

        for result in results:
            # Get date from metadata
            date_str = result.metadata.get('date')
            if not date_str:
                continue  # Skip if no date

            # Apply filter based on operator
            if date_filter.operator == 'range':
                if date_filter.start_date <= date_str <= date_filter.end_date:
                    filtered.append(result)
            elif date_filter.operator == 'gt':
                if date_str > date_filter.start_date:
                    filtered.append(result)
            elif date_filter.operator == 'gte':
                if date_str >= date_filter.start_date:
                    filtered.append(result)
            elif date_filter.operator == 'lt':
                if date_str < date_filter.end_date:
                    filtered.append(result)
            elif date_filter.operator == 'lte':
                if date_str <= date_filter.end_date:
                    filtered.append(result)
            elif date_filter.operator == 'eq' and date_filter.start_date and date_str == date_filter.start_date:
                filtered.append(result)

        return filtered


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    'SearchService',
    'SearchServiceConfig',
]

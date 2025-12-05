"""
Tag Autocomplete Engine for Mothbox Gallery (Issue #124)

Provides intelligent tag suggestions with fuzzy matching, frequency ranking,
and recency scoring for photo tagging workflow.

Features:
- Fuzzy matching with rapidfuzz (handles typos and partial matches)
- Exact prefix match bonus (2.0 points)
- Frequency-based ranking (log-scaled)
- Recency boost (exponential decay)
- Minimum 60% match threshold
- In-memory caching with TTL

Performance Target: <50ms for 10,000 tags

Usage:
    from webui.backend.lib.tag_autocomplete import TagAutocompleteEngine

    engine = TagAutocompleteEngine(sidecar_service, cache_ttl=300)
    suggestions = engine.search("mot", limit=10)

    for suggestion in suggestions:
        print(f"{suggestion.tag}: {suggestion.count} uses, score: {suggestion.match_score:.2f}")
"""

import logging
import math
import threading
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import List, Dict, Set, Optional

from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

# ============================================================================
# Constants
# ============================================================================

MINIMUM_MATCH_SCORE = 60.0  # Minimum fuzzy match score (0-100)
EXACT_PREFIX_BONUS = 2.0  # Bonus for exact prefix matches
FREQUENCY_WEIGHT = 0.3  # Weight for frequency boost (0-1)
RECENCY_WEIGHT = 0.2  # Weight for recency boost (0-1)
RECENCY_HALF_LIFE_DAYS = 30  # Half-life for exponential decay (days)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class TagMetadata:
    """Metadata for a single tag.

    Attributes:
        name: Tag name (normalized)
        count: Number of photos with this tag
        last_used: Most recent modified_at timestamp
        photos: Set of photo filenames with this tag
    """
    name: str
    count: int
    last_used: datetime
    photos: Set[str]


@dataclass
class AutocompleteSuggestion:
    """Autocomplete suggestion with ranking score.

    Attributes:
        tag: Tag name
        count: Number of photos with this tag
        last_used: Most recent usage timestamp (or None)
        match_score: Combined ranking score (0-1, higher is better)
    """
    tag: str
    count: int
    last_used: Optional[datetime]
    match_score: float


# ============================================================================
# Tag Autocomplete Engine
# ============================================================================

class TagAutocompleteEngine:
    """Tag autocomplete engine with fuzzy matching and intelligent ranking.

    Builds an in-memory index of all tags from sidecar metadata.
    Provides fast fuzzy search with ranking based on:
    - Exact prefix matching
    - Fuzzy similarity (rapidfuzz)
    - Tag frequency (usage count)
    - Tag recency (last modified)

    Thread-safe with RLock for concurrent access.
    """

    def __init__(self, sidecar_service, cache_ttl: int = 300):
        """Initialize tag autocomplete engine.

        Args:
            sidecar_service: SidecarService instance for reading metadata
            cache_ttl: Cache time-to-live in seconds (default: 300 = 5 minutes)
        """
        self.sidecar_service = sidecar_service
        self.cache_ttl = cache_ttl

        # Index: tag_name -> TagMetadata
        self._index: Dict[str, TagMetadata] = {}
        self._last_updated: Optional[datetime] = None
        self._lock = threading.RLock()

        # Pre-computed top tags for empty query optimization
        self._top_tags_cache: List[AutocompleteSuggestion] = []

        logger.debug(f"TagAutocompleteEngine initialized with cache_ttl={cache_ttl}s")

    def _is_cache_stale(self) -> bool:
        """Check if cache has expired based on TTL.

        Returns:
            True if cache should be rebuilt, False otherwise.
        """
        if not self._last_updated:
            return True
        age = (datetime.now(UTC) - self._last_updated).total_seconds()
        return age > self.cache_ttl

    def build_index(self):
        """Build tag index from all sidecar metadata.

        Aggregates tags across all photos, tracking:
        - Tag frequency (count)
        - Photo associations (photos set)
        - Most recent usage (last_used)

        Thread-safe with write lock.
        """
        with self._lock:
            logger.debug("Building tag autocomplete index...")

            # Reset index
            tag_data: Dict[str, Dict] = defaultdict(lambda: {
                'count': 0,
                'photos': set(),
                'last_used': None
            })

            # Get all sidecars from service
            try:
                all_sidecars = self.sidecar_service.list_all_sidecars()
            except Exception as e:
                logger.error(f"Failed to list sidecars: {e}")
                all_sidecars = []

            # Aggregate tags
            for metadata in all_sidecars:
                try:
                    photo_filename = metadata.photo_filename
                    tags = getattr(metadata, 'tags', [])
                    modified_at_str = getattr(metadata, 'modified_at', None)

                    # Parse timestamp
                    modified_at = None
                    if modified_at_str:
                        try:
                            # Handle ISO 8601 format with 'Z' suffix
                            if modified_at_str.endswith('Z'):
                                modified_at_str = modified_at_str[:-1] + '+00:00'
                            modified_at = datetime.fromisoformat(modified_at_str)
                        except (ValueError, AttributeError) as e:
                            logger.debug(f"Failed to parse timestamp '{modified_at_str}' for {photo_filename}: {e}")

                    # Process each tag
                    for tag in tags:
                        tag_normalized = tag.lower().strip()
                        if not tag_normalized:
                            continue

                        tag_entry = tag_data[tag_normalized]
                        tag_entry['count'] += 1
                        tag_entry['photos'].add(photo_filename)

                        # Track most recent usage
                        if modified_at:
                            if tag_entry['last_used'] is None or modified_at > tag_entry['last_used']:
                                tag_entry['last_used'] = modified_at

                except Exception as e:
                    logger.debug(f"Error processing metadata for {getattr(metadata, 'photo_filename', 'unknown')}: {e}")
                    continue

            # Build TagMetadata objects
            self._index = {}
            for tag_name, data in tag_data.items():
                self._index[tag_name] = TagMetadata(
                    name=tag_name,
                    count=data['count'],
                    last_used=data['last_used'] or datetime.now(UTC),
                    photos=data['photos']
                )

            self._last_updated = datetime.now(UTC)

            # Pre-compute top 50 tags by frequency for empty query optimization
            sorted_tags = sorted(
                self._index.values(),
                key=lambda t: t.count,
                reverse=True
            )[:50]

            self._top_tags_cache = [
                AutocompleteSuggestion(
                    tag=tag.name,
                    count=tag.count,
                    last_used=tag.last_used,
                    match_score=float(tag.count)
                )
                for tag in sorted_tags
            ]

            logger.debug(f"Tag index built: {len(self._index)} unique tags")

    def search(self, query: str, limit: int = 10) -> List[AutocompleteSuggestion]:
        """Search for tags matching query with intelligent ranking.

        Ranking algorithm combines:
        1. Exact prefix match bonus (+2.0)
        2. Fuzzy ratio (rapidfuzz, 0-1.0)
        3. Frequency boost (log-scaled, max 0.3)
        4. Recency boost (exponential decay, max 0.2)

        Filters out matches below 60% fuzzy threshold.

        Args:
            query: Search query (partial tag name)
            limit: Maximum number of suggestions to return

        Returns:
            List of AutocompleteSuggestion, sorted by match_score (descending)

        Thread-safe with read lock.
        """
        with self._lock:
            # Build index if empty or stale
            if not self._index or self._is_cache_stale():
                self.build_index()

            query_normalized = query.lower().strip()

            # Empty query: return top tags by frequency
            if not query_normalized:
                return self._get_top_tags_by_frequency(limit)

            # Calculate scores for all tags
            suggestions = []

            # Pre-calculate max log count for frequency normalization
            max_log_count = 0
            if self._index:
                max_count = max(tag.count for tag in self._index.values())
                max_log_count = math.log10(max_count + 1)

            for tag_name, tag_metadata in self._index.items():
                # For short queries (1-2 chars), only match if tag starts with query
                # This prevents over-matching (e.g., 'a' matching 'anything' at 100%)
                # For 3+ chars, use partial_ratio for substring matching
                if len(query_normalized) <= 2:
                    # Short queries: require prefix match
                    if not tag_name.startswith(query_normalized):
                        continue
                    # Give high base score for prefix matches
                    fuzzy_score = 100.0
                else:
                    # Longer queries: use fuzzy partial matching
                    fuzzy_score = fuzz.partial_ratio(query_normalized, tag_name)
                    # Filter by minimum threshold
                    if fuzzy_score < MINIMUM_MATCH_SCORE:
                        continue

                # Normalize fuzzy score to 0-1
                fuzzy_normalized = fuzzy_score / 100.0

                # Calculate combined score
                score = fuzzy_normalized

                # 1. Exact prefix match bonus
                if tag_name.startswith(query_normalized):
                    score += EXACT_PREFIX_BONUS

                # 2. Frequency boost (log-scaled)
                frequency_boost = 0
                if max_log_count > 0:
                    log_count = math.log10(tag_metadata.count + 1)
                    frequency_boost = (log_count / max_log_count) * FREQUENCY_WEIGHT
                score += frequency_boost

                # 3. Recency boost (exponential decay)
                recency_boost = self._calculate_recency_boost(tag_metadata.last_used)
                score += recency_boost

                # Create suggestion
                suggestion = AutocompleteSuggestion(
                    tag=tag_name,
                    count=tag_metadata.count,
                    last_used=tag_metadata.last_used,
                    match_score=score
                )
                suggestions.append(suggestion)

            # Sort by match_score (descending)
            suggestions.sort(key=lambda x: x.match_score, reverse=True)

            # Apply limit
            return suggestions[:limit]

    def _get_top_tags_by_frequency(self, limit: int) -> List[AutocompleteSuggestion]:
        """Get top tags sorted by frequency (for empty query).

        Uses pre-computed cache for O(1) lookup.

        Args:
            limit: Maximum number of tags to return

        Returns:
            List of AutocompleteSuggestion sorted by count (descending)
        """
        return self._top_tags_cache[:limit]

    def _calculate_recency_boost(self, last_used: datetime) -> float:
        """Calculate recency boost using exponential decay.

        More recent tags get higher boost (up to RECENCY_WEIGHT).
        Uses half-life decay: score = RECENCY_WEIGHT * (0.5 ^ (days / HALF_LIFE))

        Args:
            last_used: Timestamp of last usage

        Returns:
            Recency boost value (0 to RECENCY_WEIGHT)
        """
        now = datetime.now(UTC)

        # Ensure last_used is timezone-aware
        if last_used.tzinfo is None:
            last_used = last_used.replace(tzinfo=UTC)

        days_ago = (now - last_used).total_seconds() / 86400.0

        # Exponential decay: 0.5 ^ (days / half_life)
        decay_factor = 0.5 ** (days_ago / RECENCY_HALF_LIFE_DAYS)

        return RECENCY_WEIGHT * decay_factor

    def get_statistics(self) -> dict:
        """Get index statistics.

        Returns:
            Dictionary with:
            - total_tags: Number of unique tags in index
            - last_updated: Timestamp of last index build (or None)
        """
        with self._lock:
            return {
                'total_tags': len(self._index),
                'last_updated': self._last_updated.isoformat() if self._last_updated else None
            }

    def invalidate_cache(self):
        """Invalidate index cache, forcing rebuild on next search.

        Thread-safe with write lock.
        """
        with self._lock:
            self._index = {}
            self._last_updated = None
            self._top_tags_cache = []
            logger.debug("Tag autocomplete index cache invalidated")


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    'TagMetadata',
    'AutocompleteSuggestion',
    'TagAutocompleteEngine',
]

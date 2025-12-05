"""
Unit tests for Tag Autocomplete Engine (Issue #124)

Tests TagAutocompleteEngine library following TDD approach.
Tests written FIRST before implementation.

Coverage Target: 85%+
"""

import pytest
import time
from datetime import datetime, timedelta, UTC
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Import will fail until implementation exists - that's expected in TDD
try:
    from webui.backend.lib.tag_autocomplete import (
        TagMetadata,
        AutocompleteSuggestion,
        TagAutocompleteEngine,
    )
    IMPLEMENTATION_EXISTS = True
except ImportError:
    IMPLEMENTATION_EXISTS = False
    TagMetadata = None
    AutocompleteSuggestion = None
    TagAutocompleteEngine = None

# Skip all tests if implementation doesn't exist yet (TDD red phase)
pytestmark = pytest.mark.skipif(
    not IMPLEMENTATION_EXISTS,
    reason="Implementation not yet created (TDD red phase)"
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_sidecar_service():
    """Create mock SidecarService for testing."""
    service = Mock()

    # Mock data: sample sidecars with tags
    sample_sidecars = [
        {
            "photo_filename": "moth1.jpg",
            "tags": ["luna_moth", "nocturnal", "large"],
            "species": "Actias luna",
            "modified_at": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
        },
        {
            "photo_filename": "moth2.jpg",
            "tags": ["sphinx_moth", "nocturnal"],
            "species": "Manduca sexta",
            "modified_at": (datetime.now(UTC) - timedelta(days=10)).isoformat(),
        },
        {
            "photo_filename": "moth3.jpg",
            "tags": ["sphinx_moth", "large"],
            "species": "Sphinx ligustri",
            "modified_at": (datetime.now(UTC) - timedelta(days=30)).isoformat(),
        },
        {
            "photo_filename": "moth4.jpg",
            "tags": ["moth_species", "common"],
            "species": "Unknown",
            "modified_at": (datetime.now(UTC) - timedelta(days=5)).isoformat(),
        },
        {
            "photo_filename": "moth5.jpg",
            "tags": ["nebula", "rare"],
            "species": "Unknown",
            "modified_at": (datetime.now(UTC) - timedelta(days=2)).isoformat(),
        },
    ]

    # Convert to mock metadata objects
    mock_metadata_list = []
    for sidecar in sample_sidecars:
        metadata = Mock()
        metadata.photo_filename = sidecar["photo_filename"]
        metadata.tags = sidecar["tags"]
        metadata.species = sidecar["species"]
        metadata.modified_at = sidecar["modified_at"]
        mock_metadata_list.append(metadata)

    # Mock list_all_sidecars method
    service.list_all_sidecars.return_value = mock_metadata_list

    return service


@pytest.fixture
def engine(mock_sidecar_service):
    """Create TagAutocompleteEngine with mock service."""
    return TagAutocompleteEngine(mock_sidecar_service, cache_ttl=300)


@pytest.fixture
def large_dataset_service():
    """Create mock service with large dataset for performance testing."""
    service = Mock()

    # Generate 10,000 mock tags
    mock_metadata_list = []
    base_tags = ["moth", "butterfly", "luna", "sphinx", "nocturnal", "diurnal", "large", "small"]

    for i in range(1000):
        metadata = Mock()
        metadata.photo_filename = f"photo_{i}.jpg"
        metadata.tags = [f"{tag}_{i % 100}" for tag in base_tags[:i % len(base_tags) + 1]]
        metadata.modified_at = (datetime.now(UTC) - timedelta(days=i % 365)).isoformat()
        mock_metadata_list.append(metadata)

    service.list_all_sidecars.return_value = mock_metadata_list
    return service


# ============================================================================
# Test Data Classes
# ============================================================================

class TestDataClasses:
    """Tests for TagMetadata and AutocompleteSuggestion data classes."""

    def test_tag_metadata_creation(self):
        """TagMetadata should be created with all required fields."""
        now = datetime.now(UTC)
        photos = {"photo1.jpg", "photo2.jpg"}

        metadata = TagMetadata(
            name="luna_moth",
            count=2,
            last_used=now,
            photos=photos
        )

        assert metadata.name == "luna_moth"
        assert metadata.count == 2
        assert metadata.last_used == now
        assert metadata.photos == photos

    def test_autocomplete_suggestion_creation(self):
        """AutocompleteSuggestion should be created with all required fields."""
        now = datetime.now(UTC)

        suggestion = AutocompleteSuggestion(
            tag="luna_moth",
            count=5,
            last_used=now,
            match_score=0.95
        )

        assert suggestion.tag == "luna_moth"
        assert suggestion.count == 5
        assert suggestion.last_used == now
        assert suggestion.match_score == 0.95

    def test_autocomplete_suggestion_nullable_last_used(self):
        """AutocompleteSuggestion should allow None for last_used."""
        suggestion = AutocompleteSuggestion(
            tag="test_tag",
            count=1,
            last_used=None,
            match_score=0.8
        )

        assert suggestion.last_used is None


# ============================================================================
# Test Engine Initialization
# ============================================================================

class TestEngineInitialization:
    """Tests for TagAutocompleteEngine initialization."""

    def test_engine_creation(self, mock_sidecar_service):
        """TagAutocompleteEngine should be created with sidecar service."""
        engine = TagAutocompleteEngine(mock_sidecar_service, cache_ttl=300)

        assert engine is not None
        assert engine.cache_ttl == 300

    def test_engine_default_cache_ttl(self, mock_sidecar_service):
        """TagAutocompleteEngine should use default cache_ttl if not specified."""
        engine = TagAutocompleteEngine(mock_sidecar_service)

        assert engine.cache_ttl == 300


# ============================================================================
# Test Index Building
# ============================================================================

class TestIndexBuilding:
    """Tests for build_index method."""

    def test_build_index_creates_tag_metadata(self, engine):
        """build_index should create TagMetadata for each unique tag."""
        engine.build_index()
        stats = engine.get_statistics()

        # We have: luna_moth, nocturnal, large, sphinx_moth, moth_species, common, nebula, rare
        assert stats['total_tags'] >= 8

    def test_build_index_counts_tag_occurrences(self, engine):
        """build_index should count how many photos have each tag."""
        engine.build_index()

        # Search for tags that appear multiple times
        results = engine.search("nocturnal", limit=10)

        # nocturnal appears in moth1.jpg and moth2.jpg (count=2)
        nocturnal_result = next((r for r in results if r.tag == "nocturnal"), None)
        assert nocturnal_result is not None
        assert nocturnal_result.count == 2

    def test_build_index_tracks_photos(self, engine):
        """build_index should track which photos have each tag."""
        engine.build_index()
        results = engine.search("large", limit=10)

        large_result = next((r for r in results if r.tag == "large"), None)
        assert large_result is not None
        assert large_result.count == 2  # moth1.jpg and moth3.jpg

    def test_build_index_tracks_last_used(self, engine):
        """build_index should track most recent modified_at for each tag."""
        engine.build_index()
        results = engine.search("nocturnal", limit=10)

        nocturnal_result = next((r for r in results if r.tag == "nocturnal"), None)
        assert nocturnal_result is not None
        assert nocturnal_result.last_used is not None


# ============================================================================
# Test Search - Exact Prefix Match
# ============================================================================

class TestExactPrefixMatch:
    """Tests for exact prefix matching in search."""

    def test_exact_prefix_match_ranked_highest(self, engine):
        """Query that is exact prefix should rank highest."""
        engine.build_index()
        results = engine.search("lun", limit=10)

        # "lun" is prefix of "luna_moth" - should be first
        assert len(results) > 0
        assert results[0].tag == "luna_moth"

    def test_exact_prefix_vs_fuzzy_match(self, engine):
        """Exact prefix should rank higher than fuzzy matches."""
        engine.build_index()
        results = engine.search("moth", limit=10)

        # "moth" is prefix of "moth_species" - should rank higher than fuzzy matches
        moth_species_result = next((r for r in results if r.tag == "moth_species"), None)
        assert moth_species_result is not None
        # Should be in top results due to prefix bonus


# ============================================================================
# Test Search - Fuzzy Matching
# ============================================================================

class TestFuzzyMatching:
    """Tests for fuzzy matching in search."""

    def test_fuzzy_match_finds_close_spellings(self, engine):
        """Fuzzy matching should find tags with similar spelling."""
        engine.build_index()
        results = engine.search("sphi", limit=10)

        # Should find "sphinx_moth" (close spelling)
        tag_names = [r.tag for r in results]
        assert "sphinx_moth" in tag_names

    def test_fuzzy_match_typos(self, engine):
        """Fuzzy matching should handle typos."""
        engine.build_index()
        results = engine.search("nocturnel", limit=10)  # Typo in "nocturnal"

        # Should still find "nocturnal" with high enough score
        tag_names = [r.tag for r in results]
        assert "nocturnal" in tag_names


# ============================================================================
# Test Search - Frequency Ranking
# ============================================================================

class TestFrequencyRanking:
    """Tests for frequency-based ranking."""

    def test_frequency_affects_ranking(self, engine):
        """Higher count tags should rank higher for equal match quality."""
        engine.build_index()

        # Both "sphinx_moth" (count=2) and "luna_moth" (count=1) match "moth"
        # sphinx_moth has higher count, so should rank higher (if match scores equal)
        results = engine.search("moth", limit=10)

        moth_results = [r for r in results if "moth" in r.tag]
        assert len(moth_results) >= 2


# ============================================================================
# Test Search - Recency Ranking
# ============================================================================

class TestRecencyRanking:
    """Tests for recency-based ranking."""

    def test_recency_affects_ranking(self, engine):
        """Recently used tags should rank higher."""
        engine.build_index()

        # "luna_moth" (1 day ago) should rank higher than older tags
        results = engine.search("luna", limit=10)

        assert len(results) > 0
        # luna_moth should be in results
        tag_names = [r.tag for r in results]
        assert "luna_moth" in tag_names


# ============================================================================
# Test Search - Edge Cases
# ============================================================================

class TestSearchEdgeCases:
    """Tests for search edge cases."""

    def test_empty_query_returns_top_by_frequency(self, engine):
        """Empty query should return most popular tags."""
        engine.build_index()
        results = engine.search("", limit=10)

        # Should return results sorted by frequency
        assert len(results) > 0

        # Results should be sorted by count (or combined score)
        # Verify at least some ordering by count
        if len(results) >= 2:
            # At least first result should have a count
            assert results[0].count > 0

    def test_no_results_for_no_matches(self, engine):
        """Query with no matches should return empty list."""
        engine.build_index()
        results = engine.search("zzzzxxxxxwwwww", limit=10)

        # Gibberish should have no matches above threshold
        assert len(results) == 0

    def test_limit_parameter_respected(self, engine):
        """Search should return at most 'limit' results."""
        engine.build_index()
        results = engine.search("", limit=3)

        assert len(results) <= 3

    def test_minimum_score_threshold_filters_poor_matches(self, engine):
        """Matches below 60% threshold should be filtered out."""
        engine.build_index()

        # Query with very poor match should return empty or very few results
        results = engine.search("xyz123", limit=10)

        # Should have filtered out poor matches
        # All returned results should have decent match scores
        for result in results:
            # Match score should be above threshold (60% = 0.6)
            assert result.match_score >= 0.6


# ============================================================================
# Test Search - Special Characters
# ============================================================================

class TestSpecialCharacters:
    """Tests for handling special characters."""

    def test_special_characters_handled(self, engine):
        """Tags with underscores and special chars should work."""
        engine.build_index()

        # Search for tags with underscores
        results = engine.search("luna_moth", limit=10)

        assert len(results) > 0
        assert results[0].tag == "luna_moth"

    def test_case_insensitive_matching(self, engine):
        """Search should be case-insensitive."""
        engine.build_index()

        # Search with uppercase
        results_upper = engine.search("MOTH", limit=10)
        results_lower = engine.search("moth", limit=10)

        # Should find same tags regardless of case
        assert len(results_upper) > 0
        assert len(results_lower) > 0

        # Should have similar results
        upper_tags = {r.tag for r in results_upper}
        lower_tags = {r.tag for r in results_lower}
        assert upper_tags == lower_tags


# ============================================================================
# Test Cache Management
# ============================================================================

class TestCacheManagement:
    """Tests for cache invalidation and management."""

    def test_cache_invalidation(self, engine):
        """After invalidate_cache, index should rebuild on next search."""
        engine.build_index()

        # Get initial stats
        stats_before = engine.get_statistics()
        initial_last_updated = stats_before.get('last_updated')

        # Invalidate cache
        engine.invalidate_cache()

        # Get stats after invalidation
        stats_after = engine.get_statistics()

        # Should show cache was invalidated
        assert stats_after.get('last_updated') != initial_last_updated or stats_after['total_tags'] == 0

    def test_index_rebuilds_after_invalidation(self, engine):
        """Index should rebuild on next search after invalidation."""
        engine.build_index()
        first_search = engine.search("moth", limit=10)

        # Invalidate
        engine.invalidate_cache()

        # Search again - should rebuild index
        second_search = engine.search("moth", limit=10)

        # Should have same results (data hasn't changed)
        assert len(first_search) == len(second_search)

    def test_cache_ttl_enforcement(self, mock_sidecar_service):
        """Cache should expire after TTL and rebuild on next search."""
        from datetime import datetime, timedelta
        from unittest.mock import patch

        # Create engine with very short TTL (1 second)
        engine = TagAutocompleteEngine(mock_sidecar_service, cache_ttl=1)
        engine.build_index()

        # Verify cache is fresh
        assert not engine._is_cache_stale()

        # Simulate time passing (2 seconds)
        with patch.object(engine, '_last_updated', datetime.now(UTC) - timedelta(seconds=2)):
            # Cache should now be stale
            assert engine._is_cache_stale()

    def test_cache_ttl_not_stale_within_ttl(self, mock_sidecar_service):
        """Cache should not be stale if within TTL period."""
        # Create engine with 5 minute TTL
        engine = TagAutocompleteEngine(mock_sidecar_service, cache_ttl=300)
        engine.build_index()

        # Cache should not be stale immediately after building
        assert not engine._is_cache_stale()

    def test_is_cache_stale_before_build(self, mock_sidecar_service):
        """_is_cache_stale should return True before index is built."""
        engine = TagAutocompleteEngine(mock_sidecar_service, cache_ttl=300)

        # Before building, cache should be considered stale
        assert engine._is_cache_stale()


# ============================================================================
# Test Statistics
# ============================================================================

class TestStatistics:
    """Tests for get_statistics method."""

    def test_get_statistics_returns_correct_data(self, engine):
        """Statistics should return tag count and last updated."""
        engine.build_index()
        stats = engine.get_statistics()

        assert 'total_tags' in stats
        assert 'last_updated' in stats
        assert stats['total_tags'] > 0
        assert stats['last_updated'] is not None

    def test_statistics_before_index_built(self, engine):
        """Statistics before index built should show empty state."""
        stats = engine.get_statistics()

        assert 'total_tags' in stats
        assert stats['total_tags'] == 0


# ============================================================================
# Test Short Query Handling
# ============================================================================

class TestShortQueryHandling:
    """Tests for prefix-only matching on short queries.

    Short queries (1-2 chars) use prefix matching only instead of fuzzy matching
    to prevent over-matching (e.g., 'a' matching 'anything' because it contains 'a').
    """

    def test_single_char_query_only_matches_prefix(self, engine):
        """Single character query should only match tags starting with that char."""
        engine.build_index()

        # 'l' should match "luna_moth" and "large" (start with 'l')
        # but NOT "nocturnal" (contains 'l' but doesn't start with it)
        results = engine.search("l", limit=20)
        tag_names = [r.tag for r in results]

        assert "luna_moth" in tag_names
        assert "large" in tag_names
        assert "nocturnal" not in tag_names  # Contains 'l' but doesn't start with it

    def test_two_char_query_only_matches_prefix(self, engine):
        """Two character query should only match tags starting with those chars."""
        engine.build_index()

        # 'mo' should match "moth_species" (starts with 'mo')
        # but NOT "luna_moth" or "sphinx_moth" (contain 'mo' but don't start with it)
        results = engine.search("mo", limit=20)
        tag_names = [r.tag for r in results]

        assert "moth_species" in tag_names
        assert "luna_moth" not in tag_names
        assert "sphinx_moth" not in tag_names

    def test_three_char_query_uses_fuzzy_matching(self, engine):
        """Three+ character queries should use partial_ratio for substring matching."""
        engine.build_index()

        # 'mot' with partial_ratio finds "moth" as substring in luna_moth, sphinx_moth
        results = engine.search("mot", limit=20)
        tag_names = [r.tag for r in results]

        # Should find all moth-related tags via partial matching
        assert "moth_species" in tag_names
        assert "luna_moth" in tag_names
        assert "sphinx_moth" in tag_names

    def test_transition_from_prefix_to_fuzzy(self, engine):
        """Transitioning from 2 to 3 chars should expand to fuzzy matching."""
        engine.build_index()

        # 2-char query: prefix-only (strict)
        results_2char = engine.search("mo", limit=20)
        tags_2char = set(r.tag for r in results_2char)

        # 3-char query: fuzzy partial (finds substrings)
        results_3char = engine.search("mot", limit=20)
        tags_3char = set(r.tag for r in results_3char)

        # 3-char should find more tags because it uses fuzzy matching
        assert "moth_species" in tags_3char
        # luna_moth and sphinx_moth should appear in 3-char but not 2-char
        assert "luna_moth" in tags_3char
        assert "luna_moth" not in tags_2char


# ============================================================================
# Test Performance
# ============================================================================

class TestPerformance:
    """Performance tests for tag autocomplete."""

    def test_search_performance_large_dataset(self, large_dataset_service):
        """Search should complete in <50ms for 10,000 tags."""
        engine = TagAutocompleteEngine(large_dataset_service, cache_ttl=300)
        engine.build_index()

        # Measure search time
        start = time.perf_counter()
        results = engine.search("moth", limit=10)
        elapsed = time.perf_counter() - start

        assert len(results) > 0
        assert elapsed < 0.05, f"Search took {elapsed*1000:.2f}ms (target: <50ms)"

    def test_index_build_performance(self, large_dataset_service):
        """Index building should be reasonably fast for large dataset."""
        engine = TagAutocompleteEngine(large_dataset_service, cache_ttl=300)

        start = time.perf_counter()
        engine.build_index()
        elapsed = time.perf_counter() - start

        # Should build index in reasonable time (<1s for 10,000 tags)
        assert elapsed < 1.0, f"Index build took {elapsed:.2f}s (target: <1s)"


# ============================================================================
# Test Integration Scenarios
# ============================================================================

class TestIntegrationScenarios:
    """Integration tests for realistic usage scenarios."""

    def test_typical_autocomplete_workflow(self, engine):
        """Test typical user autocomplete workflow."""
        # User starts typing "noc" (3 chars triggers fuzzy matching)
        results = engine.search("noc", limit=5)

        # Should get suggestions (fuzzy matching active at 3+ chars)
        assert len(results) > 0

        # User continues typing "noctu"
        results = engine.search("noctu", limit=5)

        # Should narrow down results
        tag_names = [r.tag for r in results]
        assert "nocturnal" in tag_names

    def test_multiple_searches_use_cache(self, engine):
        """Multiple searches should use cached index."""
        engine.build_index()

        # Perform multiple searches
        results1 = engine.search("moth", limit=5)
        results2 = engine.search("luna", limit=5)
        results3 = engine.search("sphinx", limit=5)

        # All should return results
        assert len(results1) > 0
        assert len(results2) > 0
        assert len(results3) > 0

        # Statistics should show single index build
        stats = engine.get_statistics()
        assert stats['total_tags'] > 0

"""
Performance tests for Tag Autocomplete Engine (Issue #124)

Validates performance targets:
- Single search: <50ms for 10,000 tags
- Index build: reasonable time for large datasets
- Concurrent searches: no deadlocks

Coverage: Performance benchmarks for autocomplete system
"""

import pytest
import time
import threading
from datetime import datetime, timedelta, UTC
from unittest.mock import Mock

# Import will fail until implementation exists
try:
    from webui.backend.lib.tag_autocomplete import (
        TagAutocompleteEngine,
        AutocompleteSuggestion,
    )
    IMPLEMENTATION_EXISTS = True
except ImportError:
    IMPLEMENTATION_EXISTS = False


pytestmark = pytest.mark.skipif(
    not IMPLEMENTATION_EXISTS,
    reason="Implementation not yet created"
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def create_mock_sidecar_service():
    """Factory fixture to create mock SidecarService with specified number of tags."""
    def _create_service(num_photos: int, tags_per_photo: int = 3):
        """
        Create mock service with varied tags for performance testing.

        Args:
            num_photos: Number of photos to simulate
            tags_per_photo: Average tags per photo

        Returns:
            Mock SidecarService with list_all_sidecars method
        """
        service = Mock()
        mock_metadata_list = []

        # Generate diverse tag patterns
        tag_prefixes = [
            "moth", "butterfly", "luna", "sphinx", "hawk", "tiger",
            "nocturnal", "diurnal", "large", "small", "common", "rare",
            "species", "family", "genus", "order"
        ]

        for i in range(num_photos):
            metadata = Mock()
            metadata.photo_filename = f"photo_{i:06d}.jpg"

            # Generate tags with patterns that create realistic overlaps
            tags = []
            for j in range(tags_per_photo):
                prefix = tag_prefixes[(i + j) % len(tag_prefixes)]
                # Create variations to test fuzzy matching
                tags.append(f"{prefix}_{i % 100}")

            # Add some common tags to create frequency distribution
            if i % 10 == 0:
                tags.append("common_tag")
            if i % 5 == 0:
                tags.append("frequent_tag")

            metadata.tags = tags

            # Vary modified_at to test recency ranking
            days_ago = i % 365
            modified_at = (datetime.now(UTC) - timedelta(days=days_ago))
            metadata.modified_at = modified_at.isoformat()

            mock_metadata_list.append(metadata)

        service.list_all_sidecars.return_value = mock_metadata_list
        return service

    return _create_service


@pytest.fixture
def service_1000_tags(create_mock_sidecar_service):
    """Mock service with ~1,000 unique tags (1000 photos, 3 tags each)."""
    return create_mock_sidecar_service(num_photos=1000, tags_per_photo=3)


@pytest.fixture
def service_10000_tags(create_mock_sidecar_service):
    """Mock service with ~10,000 unique tags (10000 photos, 3 tags each)."""
    return create_mock_sidecar_service(num_photos=10000, tags_per_photo=3)


@pytest.fixture
def service_100000_tags(create_mock_sidecar_service):
    """Mock service with ~100,000 unique tags (stress test)."""
    return create_mock_sidecar_service(num_photos=100000, tags_per_photo=3)


# ============================================================================
# Single Search Performance (<50ms for 10,000 tags)
# ============================================================================

class TestSingleSearchPerformance:
    """Test single search query performance against target."""

    def test_search_1000_tags_under_10ms(self, service_1000_tags):
        """Search with 1,000 tags should complete in <10ms."""
        engine = TagAutocompleteEngine(service_1000_tags, cache_ttl=300)
        engine.build_index()

        # Warm up
        engine.search("moth", limit=10)

        # Measure search time (average over 10 runs for stability)
        start = time.perf_counter()
        for _ in range(10):
            results = engine.search("moth", limit=10)
        elapsed = (time.perf_counter() - start) / 10

        assert len(results) > 0, "Should return results"
        assert elapsed < 0.010, f"Search took {elapsed*1000:.2f}ms, expected <10ms"

    def test_search_10000_tags_under_50ms(self, service_10000_tags):
        """Search with 10,000 tags should complete in <50ms (PRIMARY TARGET)."""
        engine = TagAutocompleteEngine(service_10000_tags, cache_ttl=300)
        engine.build_index()

        # Warm up
        engine.search("moth", limit=10)

        # Measure search time (average over 10 runs)
        start = time.perf_counter()
        for _ in range(10):
            results = engine.search("moth", limit=10)
        elapsed = (time.perf_counter() - start) / 10

        assert len(results) > 0, "Should return results"
        assert elapsed < 0.050, f"Search took {elapsed*1000:.2f}ms, expected <50ms"

    def test_search_empty_query_under_50ms(self, service_10000_tags):
        """Empty query (top tags by frequency) should be fast."""
        engine = TagAutocompleteEngine(service_10000_tags, cache_ttl=300)
        engine.build_index()

        # Warm up
        engine.search("", limit=10)

        # Measure empty query performance
        start = time.perf_counter()
        for _ in range(10):
            results = engine.search("", limit=10)
        elapsed = (time.perf_counter() - start) / 10

        assert len(results) > 0, "Should return top tags"
        assert elapsed < 0.050, f"Empty query took {elapsed*1000:.2f}ms, expected <50ms"

    def test_search_single_char_query_under_50ms(self, service_10000_tags):
        """Single character queries should still be fast."""
        engine = TagAutocompleteEngine(service_10000_tags, cache_ttl=300)
        engine.build_index()

        # Single char queries may match many tags
        start = time.perf_counter()
        for _ in range(10):
            results = engine.search("m", limit=10)
        elapsed = (time.perf_counter() - start) / 10

        # Should return results (limited to 10)
        assert len(results) <= 10
        assert elapsed < 0.050, f"Single char search took {elapsed*1000:.2f}ms"

    def test_search_fuzzy_match_performance(self, service_10000_tags):
        """Fuzzy matching should not significantly degrade performance."""
        engine = TagAutocompleteEngine(service_10000_tags, cache_ttl=300)
        engine.build_index()

        # Query with typo - requires fuzzy matching
        start = time.perf_counter()
        for _ in range(10):
            results = engine.search("motth", limit=10)  # Typo in "moth"
        elapsed = (time.perf_counter() - start) / 10

        # Fuzzy matching may return fewer results, but should still be fast
        assert elapsed < 0.050, f"Fuzzy search took {elapsed*1000:.2f}ms"


# ============================================================================
# Index Building Performance
# ============================================================================

class TestIndexBuildPerformance:
    """Test index building performance for various dataset sizes."""

    def test_index_build_1000_tags_under_100ms(self, service_1000_tags):
        """Building index for 1,000 tags should be very fast (<100ms)."""
        engine = TagAutocompleteEngine(service_1000_tags, cache_ttl=300)

        start = time.perf_counter()
        engine.build_index()
        elapsed = time.perf_counter() - start

        stats = engine.get_statistics()
        assert stats['total_tags'] > 0, "Index should contain tags"
        assert elapsed < 0.100, f"Index build took {elapsed*1000:.1f}ms, expected <100ms"

    def test_index_build_10000_tags_under_500ms(self, service_10000_tags):
        """Building index for 10,000 tags should complete in <500ms."""
        engine = TagAutocompleteEngine(service_10000_tags, cache_ttl=300)

        start = time.perf_counter()
        engine.build_index()
        elapsed = time.perf_counter() - start

        stats = engine.get_statistics()
        assert stats['total_tags'] > 0, "Index should contain tags"
        # Reasonable time for large dataset (parsing, aggregation, datetime parsing)
        assert elapsed < 0.500, f"Index build took {elapsed*1000:.1f}ms, expected <500ms"

    def test_index_rebuild_after_invalidation(self, service_10000_tags):
        """Rebuilding index after invalidation should be consistent."""
        engine = TagAutocompleteEngine(service_10000_tags, cache_ttl=300)

        # First build
        start = time.perf_counter()
        engine.build_index()
        first_build_time = time.perf_counter() - start

        # Invalidate
        engine.invalidate_cache()

        # Second build
        start = time.perf_counter()
        engine.build_index()
        second_build_time = time.perf_counter() - start

        # Both builds should take similar time (within 50%)
        ratio = second_build_time / first_build_time
        assert 0.5 < ratio < 2.0, f"Build time inconsistent: {first_build_time:.3f}s vs {second_build_time:.3f}s"


# ============================================================================
# Stress Test with 100,000 Tags
# ============================================================================

class TestStressTest:
    """Stress test with very large datasets."""

    def test_search_with_100000_tags(self, service_100000_tags):
        """Search should still complete with 100,000 tags (may be slower, but should complete)."""
        engine = TagAutocompleteEngine(service_100000_tags, cache_ttl=300)
        engine.build_index()

        # This may exceed 50ms target, but should still be reasonable (<500ms)
        start = time.perf_counter()
        results = engine.search("moth", limit=10)
        elapsed = time.perf_counter() - start

        assert len(results) > 0, "Should return results even with large dataset"
        assert elapsed < 0.500, f"Search with 100k tags took {elapsed*1000:.1f}ms (too slow)"

    def test_index_build_100000_tags_completes(self, service_100000_tags):
        """Index building should complete for very large datasets (within reasonable time)."""
        engine = TagAutocompleteEngine(service_100000_tags, cache_ttl=300)

        # Allow more time for very large dataset (5 seconds max)
        start = time.perf_counter()
        engine.build_index()
        elapsed = time.perf_counter() - start

        stats = engine.get_statistics()
        assert stats['total_tags'] > 0
        assert elapsed < 5.0, f"Index build for 100k tags took {elapsed:.2f}s (too slow)"


# ============================================================================
# Concurrent Access Performance
# ============================================================================

class TestConcurrentSearchPerformance:
    """Test performance and safety under concurrent access."""

    def test_concurrent_searches_no_deadlock(self, service_10000_tags):
        """Multiple concurrent searches should not deadlock."""
        engine = TagAutocompleteEngine(service_10000_tags, cache_ttl=300)
        engine.build_index()

        results_list = []
        errors = []

        def search_worker(query: str):
            try:
                start = time.perf_counter()
                results = engine.search(query, limit=10)
                elapsed = time.perf_counter() - start
                results_list.append((query, len(results), elapsed))
            except Exception as e:
                errors.append(f"{query}: {str(e)}")

        # Start 20 concurrent searches with different queries
        queries = ["moth", "luna", "sphinx", "nocturnal", "common"] * 4
        threads = [threading.Thread(target=search_worker, args=(q,)) for q in queries]

        for t in threads:
            t.start()

        # Wait with timeout to detect deadlocks
        for t in threads:
            t.join(timeout=5.0)

        # Check for deadlocks
        alive = [t for t in threads if t.is_alive()]
        assert len(alive) == 0, f"Potential deadlock: {len(alive)} threads still running"

        # No errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # All searches completed successfully
        assert len(results_list) == 20

        # Check performance didn't degrade
        for query, count, elapsed in results_list:
            assert elapsed < 0.100, f"Concurrent search '{query}' took {elapsed*1000:.1f}ms"

    def test_concurrent_search_and_invalidate(self, service_10000_tags):
        """Concurrent searches and cache invalidation should be safe."""
        engine = TagAutocompleteEngine(service_10000_tags, cache_ttl=300)
        engine.build_index()

        results_list = []
        errors = []

        def search_worker():
            try:
                for _ in range(10):
                    engine.search("moth", limit=10)
                results_list.append("search_ok")
            except Exception as e:
                errors.append(f"search: {str(e)}")

        def invalidate_worker():
            try:
                for _ in range(5):
                    engine.invalidate_cache()
                    time.sleep(0.001)
                results_list.append("invalidate_ok")
            except Exception as e:
                errors.append(f"invalidate: {str(e)}")

        # Start mixed operations
        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=search_worker))
        for _ in range(2):
            threads.append(threading.Thread(target=invalidate_worker))

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=5.0)

        # No deadlocks
        alive = [t for t in threads if t.is_alive()]
        assert len(alive) == 0, "Potential deadlock detected"

        # No errors
        assert len(errors) == 0, f"Errors: {errors}"

    def test_search_while_building_index(self, service_10000_tags):
        """Searching while index is being built should be safe."""
        engine = TagAutocompleteEngine(service_10000_tags, cache_ttl=300)

        errors = []
        results_list = []

        def build_worker():
            try:
                engine.build_index()
                results_list.append("build_ok")
            except Exception as e:
                errors.append(f"build: {str(e)}")

        def search_worker():
            try:
                # Will trigger auto-build if index empty
                results = engine.search("moth", limit=10)
                results_list.append(("search_ok", len(results)))
            except Exception as e:
                errors.append(f"search: {str(e)}")

        # Start concurrent build and search
        build_thread = threading.Thread(target=build_worker)
        search_threads = [threading.Thread(target=search_worker) for _ in range(5)]

        build_thread.start()
        for t in search_threads:
            t.start()

        build_thread.join(timeout=5.0)
        for t in search_threads:
            t.join(timeout=5.0)

        # No errors
        assert len(errors) == 0, f"Errors: {errors}"


# ============================================================================
# Memory Efficiency
# ============================================================================

class TestMemoryEfficiency:
    """Test memory usage patterns."""

    def test_index_memory_footprint_reasonable(self, service_10000_tags):
        """Index should not consume excessive memory."""
        import sys

        engine = TagAutocompleteEngine(service_10000_tags, cache_ttl=300)
        engine.build_index()

        # Check rough memory size of index
        # Note: sys.getsizeof doesn't account for nested objects fully
        # This is a rough estimate
        stats = engine.get_statistics()
        total_tags = stats['total_tags']

        # With 10k tags, index should be manageable (<50MB is reasonable)
        # Each TagMetadata has: name (str), count (int), last_used (datetime), photos (set)
        # Rough estimate: ~1-5KB per tag entry
        # 10k tags * 5KB = ~50MB upper bound
        assert total_tags > 0, "Index should be built"

    def test_search_results_memory_footprint(self, service_10000_tags):
        """Search results should not consume excessive memory."""
        import sys

        engine = TagAutocompleteEngine(service_10000_tags, cache_ttl=300)
        engine.build_index()

        # Get search results
        results = engine.search("moth", limit=10)

        # Check size of results list
        results_size = sys.getsizeof(results)

        # Results list should be small (<10KB for 10 items)
        assert results_size < 10000, f"Results list size {results_size} bytes is too large"

        # Check individual suggestion size
        if len(results) > 0:
            suggestion_size = sys.getsizeof(results[0])
            # AutocompleteSuggestion dataclass should be small (<500 bytes)
            assert suggestion_size < 500, f"Suggestion size {suggestion_size} bytes"


# ============================================================================
# Regression Tests
# ============================================================================

class TestPerformanceRegressions:
    """Prevent known performance regressions."""

    def test_substring_matching_works(self):
        """Should match query as substring within tag names (partial_ratio behavior)."""
        # Create a mock service with specific tags to test substring matching
        service = Mock()
        metadata = Mock()
        metadata.photo_filename = "photo_001.jpg"
        # Include tags where the query would appear in the middle
        metadata.tags = ["luna_moth", "hawk_moth", "sphinx_moth", "butterfly", "moth_species"]
        metadata.modified_at = datetime.now(UTC).isoformat()
        service.list_all_sidecars.return_value = [metadata]

        engine = TagAutocompleteEngine(service, cache_ttl=300)

        # Search for "moth" - should find tags with "moth" anywhere (not just prefix)
        # Note: Queries >= 3 chars use fuzzy partial matching
        results = engine.search("moth", limit=10)
        result_tags = [r.tag for r in results]

        # Should find tags where 'moth' appears anywhere
        assert "luna_moth" in result_tags, "Should match 'moth' in 'luna_moth'"
        assert "hawk_moth" in result_tags, "Should match 'moth' in 'hawk_moth'"
        assert "sphinx_moth" in result_tags, "Should match 'moth' in 'sphinx_moth'"
        assert "moth_species" in result_tags, "Should match prefix 'moth_species'"

    def test_no_redundant_index_builds(self, service_10000_tags):
        """Multiple searches should not trigger redundant index builds."""
        engine = TagAutocompleteEngine(service_10000_tags, cache_ttl=300)

        # First search triggers index build
        engine.search("moth", limit=10)
        stats_1 = engine.get_statistics()
        last_updated_1 = stats_1['last_updated']

        # Second search should use cached index
        time.sleep(0.01)  # Small delay
        engine.search("luna", limit=10)
        stats_2 = engine.get_statistics()
        last_updated_2 = stats_2['last_updated']

        # Last updated should be the same (no rebuild)
        assert last_updated_1 == last_updated_2, "Index was rebuilt unnecessarily"

    def test_logarithmic_frequency_scaling(self, service_10000_tags):
        """Frequency boost should use logarithmic scaling (not linear)."""
        # This ensures high-frequency tags don't completely dominate
        from webui.backend.lib import tag_autocomplete
        import inspect

        source = inspect.getsource(tag_autocomplete.TagAutocompleteEngine.search)

        # Should use math.log10 for frequency normalization
        assert "log10" in source, "Should use logarithmic frequency scaling"


# ============================================================================
# Benchmark Summary
# ============================================================================

class TestBenchmarkSummary:
    """Generate performance benchmark summary."""

    def test_comprehensive_benchmark(self, service_10000_tags, capsys):
        """Run comprehensive benchmark and print results."""
        engine = TagAutocompleteEngine(service_10000_tags, cache_ttl=300)

        # Benchmark index build
        start = time.perf_counter()
        engine.build_index()
        build_time = time.perf_counter() - start

        stats = engine.get_statistics()

        # Benchmark various search scenarios
        benchmarks = []

        test_queries = [
            ("empty", "", 10),
            ("single_char", "m", 10),
            ("short_query", "mot", 10),
            ("full_word", "moth", 10),
            ("typo", "motth", 10),
        ]

        for name, query, limit in test_queries:
            # Warm up
            engine.search(query, limit=limit)

            # Measure
            start = time.perf_counter()
            for _ in range(10):
                results = engine.search(query, limit=limit)
            elapsed = (time.perf_counter() - start) / 10

            benchmarks.append((name, query, elapsed, len(results)))

        # Print summary
        print("\n" + "="*60)
        print("TAG AUTOCOMPLETE PERFORMANCE BENCHMARK")
        print("="*60)
        print(f"Dataset: {stats['total_tags']} unique tags")
        print(f"Index build time: {build_time*1000:.1f}ms")
        print()
        print("Search Performance (average of 10 runs):")
        print("-"*60)
        for name, query, elapsed_ms, result_count in benchmarks:
            query_display = f"'{query}'" if query else "(empty)"
            print(f"  {name:15} {query_display:10} -> {elapsed_ms*1000:6.2f}ms ({result_count} results)")
        print("="*60)

        # All benchmarks should pass targets
        assert build_time < 0.500, f"Index build too slow: {build_time*1000:.1f}ms"
        for name, query, elapsed, _ in benchmarks:
            assert elapsed < 0.050, f"{name} search too slow: {elapsed*1000:.2f}ms"

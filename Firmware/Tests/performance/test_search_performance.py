"""
Performance tests for Full-Text Search System (Issue #131).

These tests verify that the search system meets performance targets:
- Query parsing: <10ms
- Single photo indexing: <50ms
- 1,000 photos search: <50ms
- 10,000 photos search: <200ms (primary target)
- 50,000 photos search: <500ms

Run with: MOTHBOX_ENV=test pytest Tests/performance/test_search_performance.py -v -s
"""

import os
import sys
import time
import random
import string
import tracemalloc
from pathlib import Path

import pytest

# Setup path
FIRMWARE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(FIRMWARE_DIR))
sys.path.insert(0, str(FIRMWARE_DIR / "webui" / "backend"))
os.environ.setdefault("MOTHBOX_ENV", "test")

from webui.backend.lib.search_engine import SearchEngine
from webui.backend.lib.search_query_parser import parse_query
from webui.backend.services.search_service import SearchService, SearchServiceConfig


# ============================================================================
# Test Data Generators
# ============================================================================

def generate_random_metadata(index: int, tag_pool: list, species_list: list) -> dict:
    """Generate realistic random metadata for a photo.

    Args:
        index: Photo index
        tag_pool: List of available tags
        species_list: List of available species names

    Returns:
        Metadata dictionary
    """
    num_tags = random.randint(1, 5)
    tags = random.sample(tag_pool, min(num_tags, len(tag_pool)))

    return {
        'filename': f'photo_{index:05d}.jpg',
        'tags': tags,
        'species': random.choice(species_list),
        'species_common_name': f'{random.choice(species_list)} (common)',
        'notes': f'Photo {index}: {" ".join(random.choices(string.ascii_lowercase + " ", k=50))}',
        'custom_fields': {
            'location': f'Site {index % 10}',
            'weather': random.choice(['clear', 'cloudy', 'rainy']),
        }
    }


def generate_test_dataset(count: int, tmp_path: Path) -> tuple[Path, list]:
    """Generate test dataset with realistic distribution.

    Args:
        count: Number of photos to generate
        tmp_path: Temporary directory for database

    Returns:
        Tuple of (db_path, list of (filepath, metadata) tuples)
    """
    db_path = tmp_path / "search.db"

    # Create realistic tag and species pools
    tag_pool = [
        'moth', 'nocturnal', 'luna_moth', 'saturniidae', 'lepidoptera',
        'antennae', 'wingspan', 'cocoon', 'caterpillar', 'adult',
        'male', 'female', 'specimen', 'field_photo', 'lab_photo'
    ]

    # Extend tag pool for larger datasets
    if count > 1000:
        tag_pool.extend([f'tag_{i}' for i in range(100)])

    species_list = [
        'Actias luna', 'Hyalophora cecropia', 'Automeris io',
        'Antheraea polyphemus', 'Eacles imperialis', 'Citheronia regalis',
        'Sphinx chersis', 'Manduca sexta', 'Hyles lineata',
        'Deilephila elpenor'
    ]

    # Extend species list for larger datasets
    if count > 1000:
        species_list.extend([f'Species_{i}' for i in range(100)])

    # Generate photo metadata
    photos = []
    for i in range(count):
        filepath = f'photos/2024-{(i % 12) + 1:02d}/photo_{i:05d}.jpg'
        metadata = generate_random_metadata(i, tag_pool, species_list)
        photos.append((filepath, metadata))

    return db_path, photos


# ============================================================================
# Query Parser Performance Tests
# ============================================================================

class TestQueryParserPerformance:
    """Query parser should be <10ms per query"""

    def test_simple_query_parsing(self):
        """Simple queries should parse in <10ms"""
        queries = [
            "moth",
            "luna moth",
            "tag:moth",
            "species:actias"
        ]

        # Warm up
        for q in queries:
            parse_query(q)

        start = time.perf_counter()
        iterations = 1000
        for _ in range(iterations):
            for q in queries:
                parse_query(q)
        elapsed = (time.perf_counter() - start) * 1000 / (iterations * len(queries))  # ms per query

        print(f"\n  Simple query parsing: {elapsed:.4f}ms per query")
        assert elapsed < 10, f"Query parsing took {elapsed:.2f}ms (target: <10ms)"

    def test_complex_query_parsing(self):
        """Complex queries should parse in <10ms"""
        queries = [
            'tag:moth AND species:actias OR notes:"large specimen"',
            'date:2024-01-01..2024-12-31 tag:nocturnal -butterfly',
            '"luna moth" tag:saturniidae* species:actias',
            'tag:moth OR tag:butterfly AND NOT tag:damaged',
            'species:Actias* date:>=2024-01-01 tag:specimen'
        ]

        # Warm up
        for q in queries:
            parse_query(q)

        start = time.perf_counter()
        iterations = 1000
        for _ in range(iterations):
            for q in queries:
                parse_query(q)
        elapsed = (time.perf_counter() - start) * 1000 / (iterations * len(queries))

        print(f"\n  Complex query parsing: {elapsed:.4f}ms per query")
        assert elapsed < 10, f"Complex query parsing took {elapsed:.2f}ms (target: <10ms)"

    def test_date_filter_parsing(self):
        """Date filter parsing should be <10ms"""
        queries = [
            'date:2024-11-01',
            'date:2024-11-01..2024-11-06',
            'date:>2024-01-01',
            'date:>=2024-01-01',
            'date:<2024-12-31',
            'date:<=2024-12-31'
        ]

        start = time.perf_counter()
        iterations = 1000
        for _ in range(iterations):
            for q in queries:
                parse_query(q)
        elapsed = (time.perf_counter() - start) * 1000 / (iterations * len(queries))

        print(f"\n  Date filter parsing: {elapsed:.4f}ms per query")
        assert elapsed < 10, f"Date filter parsing took {elapsed:.2f}ms (target: <10ms)"


# ============================================================================
# Search Engine Indexing Performance Tests
# ============================================================================

class TestIndexingPerformance:
    """Test photo indexing performance"""

    def test_single_photo_indexing_under_50ms(self, tmp_path):
        """Single photo indexing should be <50ms"""
        db_path = tmp_path / "search.db"
        engine = SearchEngine(db_path)

        # Prepare metadata
        metadata = {
            'filename': 'test_photo.jpg',
            'tags': ['moth', 'nocturnal', 'luna_moth'],
            'species': 'Actias luna',
            'species_common_name': 'Luna Moth',
            'notes': 'Beautiful green moth photographed at night'
        }

        # Warm up
        for i in range(10):
            engine.index_photo(f'photos/warmup_{i}.jpg', metadata)

        # Measure indexing time
        times = []
        for i in range(100):
            filepath = f'photos/photo_{i}.jpg'

            start = time.perf_counter()
            engine.index_photo(filepath, metadata)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        engine.close()

        avg_time = sum(times) / len(times)
        max_time = max(times)
        p95_time = sorted(times)[94]  # 95th percentile

        print(f"\n  Single photo indexing:")
        print(f"    Average: {avg_time:.2f}ms")
        print(f"    Max: {max_time:.2f}ms")
        print(f"    P95: {p95_time:.2f}ms")

        assert avg_time < 50, f"Avg indexing time: {avg_time:.2f}ms (target: <50ms)"
        assert p95_time < 100, f"P95 indexing time: {p95_time:.2f}ms (target: <100ms)"

    def test_bulk_indexing_1000_photos(self, tmp_path):
        """Bulk indexing 1000 photos should be efficient"""
        db_path, photos = generate_test_dataset(1000, tmp_path)
        engine = SearchEngine(db_path)

        start = time.perf_counter()
        for filepath, metadata in photos:
            engine.index_photo(filepath, metadata)
        elapsed = time.perf_counter() - start

        engine.close()

        photos_per_sec = 1000 / elapsed

        print(f"\n  Bulk indexing 1000 photos:")
        print(f"    Total time: {elapsed:.2f}s")
        print(f"    Throughput: {photos_per_sec:.0f} photos/sec")

        # Should index at least 50 photos/sec (20ms per photo avg)
        assert photos_per_sec >= 50, f"Throughput: {photos_per_sec:.0f} photos/sec (target: >=50)"


# ============================================================================
# Search Performance Tests (Core Targets)
# ============================================================================

class TestSearchPerformance:
    """Test search query performance across dataset sizes"""

    @pytest.fixture
    def engine_100(self, tmp_path):
        """Engine with 100 photos"""
        db_path, photos = generate_test_dataset(100, tmp_path)
        engine = SearchEngine(db_path)
        for filepath, metadata in photos:
            engine.index_photo(filepath, metadata)
        yield engine
        engine.close()

    @pytest.fixture
    def engine_1k(self, tmp_path):
        """Engine with 1,000 photos"""
        db_path, photos = generate_test_dataset(1000, tmp_path)
        engine = SearchEngine(db_path)
        for filepath, metadata in photos:
            engine.index_photo(filepath, metadata)
        yield engine
        engine.close()

    @pytest.fixture
    def engine_10k(self, tmp_path):
        """Engine with 10,000 photos (primary target)"""
        db_path, photos = generate_test_dataset(10000, tmp_path)
        engine = SearchEngine(db_path)
        for filepath, metadata in photos:
            engine.index_photo(filepath, metadata)
        yield engine
        engine.close()

    def test_100_photos_search_under_20ms(self, engine_100):
        """Search 100 photos should be <20ms"""
        queries = ["moth", "luna", "species:Actias", "tag:nocturnal"]

        # Warm up
        for q in queries:
            engine_100.search(q)

        times = []
        for q in queries:
            start = time.perf_counter()
            result = engine_100.search(q)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        max_time = max(times)

        print(f"\n  100 photos search:")
        print(f"    Average: {avg_time:.2f}ms")
        print(f"    Max: {max_time:.2f}ms")

        assert max_time < 20, f"Max search time: {max_time:.2f}ms (target: <20ms)"

    def test_1k_photos_search_under_50ms(self, engine_1k):
        """Search 1,000 photos should be <50ms"""
        queries = [
            "moth",
            "luna",
            "species:Actias",
            "tag:nocturnal",
            "luna*",
            '"luna moth"'
        ]

        # Warm up
        for q in queries:
            engine_1k.search(q)

        times = []
        for q in queries:
            start = time.perf_counter()
            result = engine_1k.search(q)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        max_time = max(times)

        print(f"\n  1,000 photos search:")
        print(f"    Average: {avg_time:.2f}ms")
        print(f"    Max: {max_time:.2f}ms")

        assert max_time < 50, f"Max search time: {max_time:.2f}ms (target: <50ms)"

    def test_10k_photos_search_under_200ms(self, engine_10k):
        """Search 10,000 photos should be <200ms (PRIMARY TARGET)"""
        queries = [
            "moth",
            "luna",
            "species:Actias",
            "tag:nocturnal",
            "luna*",
            '"luna moth"',
            "tag:moth AND species:Actias"
        ]

        # Warm up
        for q in queries:
            engine_10k.search(q)

        times = []
        for q in queries:
            start = time.perf_counter()
            result = engine_10k.search(q)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

            print(f"    Query: '{q}' -> {result.total} results in {elapsed:.2f}ms")

        avg_time = sum(times) / len(times)
        max_time = max(times)

        print(f"\n  10,000 photos search:")
        print(f"    Average: {avg_time:.2f}ms")
        print(f"    Max: {max_time:.2f}ms")

        assert max_time < 200, f"Max search time: {max_time:.2f}ms (target: <200ms)"
        print(f"\n  ✓ PRIMARY TARGET MET: 10K photos search in <200ms")

    @pytest.mark.performance
    def test_50k_photos_search_under_500ms(self, tmp_path):
        """Search 50,000 photos should be <500ms (stretch goal)"""
        print("\n  Generating 50,000 photos dataset (this may take a minute)...")
        db_path, photos = generate_test_dataset(50000, tmp_path)
        engine = SearchEngine(db_path)

        # Index all photos
        start_index = time.perf_counter()
        for filepath, metadata in photos:
            engine.index_photo(filepath, metadata)
        index_time = time.perf_counter() - start_index
        print(f"  Indexed 50,000 photos in {index_time:.2f}s")

        queries = [
            "moth",
            "species:Actias",
            "tag:nocturnal",
            "luna*"
        ]

        times = []
        for q in queries:
            start = time.perf_counter()
            result = engine.search(q)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
            print(f"    Query: '{q}' -> {result.total} results in {elapsed:.2f}ms")

        engine.close()

        avg_time = sum(times) / len(times)
        max_time = max(times)

        print(f"\n  50,000 photos search:")
        print(f"    Average: {avg_time:.2f}ms")
        print(f"    Max: {max_time:.2f}ms")

        assert max_time < 500, f"Max search time: {max_time:.2f}ms (target: <500ms)"


# ============================================================================
# Search Service Performance Tests (End-to-End)
# ============================================================================

class TestSearchServicePerformance:
    """Test SearchService performance (includes query parsing + search)"""

    @pytest.fixture
    def service_10k(self, tmp_path):
        """SearchService with 10,000 photos"""
        db_path = tmp_path / "cache" / "search.db"
        config = SearchServiceConfig(db_path=db_path)
        service = SearchService(config)

        # Generate and index photos
        _, photos = generate_test_dataset(10000, tmp_path)
        for filepath, metadata in photos:
            service.index_photo(filepath, metadata)

        yield service
        service.close()

    def test_full_search_pipeline_10k_under_200ms(self, service_10k):
        """Full search pipeline (parse + search) for 10K photos should be <200ms"""
        queries = [
            "moth",
            "tag:luna",
            "species:Actias*",
            'tag:moth AND species:Actias',
            'tag:nocturnal OR tag:specimen',
            '"luna moth"',
            'tag:moth -damaged'
        ]

        # Warm up
        for q in queries:
            service_10k.search(q)

        times = []
        for q in queries:
            start = time.perf_counter()
            result = service_10k.search(q)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

            # Verify search worked
            assert result.get('is_valid', True), f"Query failed: {result.get('error_message')}"

            print(f"    Query: '{q}' -> {result['total']} results in {elapsed:.2f}ms")

        avg_time = sum(times) / len(times)
        max_time = max(times)

        print(f"\n  Full search pipeline (10K photos):")
        print(f"    Average: {avg_time:.2f}ms")
        print(f"    Max: {max_time:.2f}ms")

        assert max_time < 200, f"Max search time: {max_time:.2f}ms (target: <200ms)"

    def test_pagination_performance(self, service_10k):
        """Paginated searches should maintain performance"""
        query = "moth"
        page_size = 20

        times = []
        for page in range(10):  # Test 10 pages
            offset = page * page_size

            start = time.perf_counter()
            result = service_10k.search(query, limit=page_size, offset=offset)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        max_time = max(times)

        print(f"\n  Pagination performance (10 pages):")
        print(f"    Average: {avg_time:.2f}ms")
        print(f"    Max: {max_time:.2f}ms")

        assert max_time < 250, f"Max pagination time: {max_time:.2f}ms (target: <250ms)"


# ============================================================================
# Memory Usage Tests
# ============================================================================

class TestMemoryUsage:
    """Test memory usage during search operations"""

    def test_1k_photos_memory_under_20mb(self, tmp_path):
        """Indexing and searching 1,000 photos should use <20MB peak memory"""
        db_path, photos = generate_test_dataset(1000, tmp_path)

        tracemalloc.start()

        engine = SearchEngine(db_path)
        for filepath, metadata in photos:
            engine.index_photo(filepath, metadata)

        # Perform some searches
        for _ in range(10):
            engine.search("moth")

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        engine.close()

        peak_mb = peak / 1024 / 1024

        print(f"\n  1,000 photos memory:")
        print(f"    Peak: {peak_mb:.2f}MB")

        assert peak_mb < 20, f"Peak memory: {peak_mb:.2f}MB (target: <20MB)"

    def test_10k_photos_memory_under_100mb(self, tmp_path):
        """Indexing and searching 10,000 photos should use <100MB peak memory"""
        db_path, photos = generate_test_dataset(10000, tmp_path)

        tracemalloc.start()

        engine = SearchEngine(db_path)
        for filepath, metadata in photos:
            engine.index_photo(filepath, metadata)

        # Perform some searches
        for _ in range(10):
            engine.search("moth")

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        engine.close()

        peak_mb = peak / 1024 / 1024

        print(f"\n  10,000 photos memory:")
        print(f"    Peak: {peak_mb:.2f}MB")

        assert peak_mb < 100, f"Peak memory: {peak_mb:.2f}MB (target: <100MB)"


# ============================================================================
# Query Type Performance Tests
# ============================================================================

class TestQueryTypePerformance:
    """Test performance across different query types"""

    @pytest.fixture
    def engine_10k_for_query_types(self, tmp_path):
        """Engine with 10K photos for query type testing"""
        db_path, photos = generate_test_dataset(10000, tmp_path)
        engine = SearchEngine(db_path)
        for filepath, metadata in photos:
            engine.index_photo(filepath, metadata)
        yield engine
        engine.close()

    def test_simple_term_search(self, engine_10k_for_query_types):
        """Simple term searches should be fast"""
        queries = ["moth", "luna", "nocturnal", "specimen"]

        times = []
        for q in queries:
            start = time.perf_counter()
            result = engine_10k_for_query_types.search(q)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        print(f"\n  Simple term searches: {avg_time:.2f}ms avg")
        assert avg_time < 150, f"Avg time: {avg_time:.2f}ms (target: <150ms)"

    def test_field_specific_search(self, engine_10k_for_query_types):
        """Field-specific searches should be fast"""
        queries = [
            "tag:moth",
            "species:Actias",
            "notes:specimen",
            "filename:photo"
        ]

        times = []
        for q in queries:
            start = time.perf_counter()
            result = engine_10k_for_query_types.search(q)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        print(f"\n  Field-specific searches: {avg_time:.2f}ms avg")
        assert avg_time < 150, f"Avg time: {avg_time:.2f}ms (target: <150ms)"

    def test_boolean_search(self, engine_10k_for_query_types):
        """Boolean searches should maintain performance"""
        queries = [
            "tag:moth AND species:Actias",
            "tag:moth OR tag:butterfly",
            "moth NOT damaged",
            "tag:nocturnal AND NOT tag:butterfly"
        ]

        times = []
        for q in queries:
            start = time.perf_counter()
            result = engine_10k_for_query_types.search(q)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        print(f"\n  Boolean searches: {avg_time:.2f}ms avg")
        assert avg_time < 200, f"Avg time: {avg_time:.2f}ms (target: <200ms)"

    def test_prefix_search(self, engine_10k_for_query_types):
        """Prefix searches should be fast"""
        queries = ["lun*", "act*", "moth*", "spec*"]

        times = []
        for q in queries:
            start = time.perf_counter()
            result = engine_10k_for_query_types.search(q)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        print(f"\n  Prefix searches: {avg_time:.2f}ms avg")
        assert avg_time < 200, f"Avg time: {avg_time:.2f}ms (target: <200ms)"

    def test_phrase_search(self, engine_10k_for_query_types):
        """Phrase searches should be reasonably fast"""
        queries = ['"luna moth"', '"field photo"', '"large specimen"']

        times = []
        for q in queries:
            start = time.perf_counter()
            result = engine_10k_for_query_types.search(q)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        print(f"\n  Phrase searches: {avg_time:.2f}ms avg")
        assert avg_time < 250, f"Avg time: {avg_time:.2f}ms (target: <250ms)"


# ============================================================================
# Stress Tests
# ============================================================================

class TestStressConditions:
    """Test performance under stress conditions"""

    def test_rapid_sequential_searches(self, tmp_path):
        """Handle rapid sequential search requests"""
        db_path, photos = generate_test_dataset(1000, tmp_path)
        engine = SearchEngine(db_path)

        for filepath, metadata in photos:
            engine.index_photo(filepath, metadata)

        query = "moth"
        times = []

        for _ in range(100):  # 100 rapid searches
            start = time.perf_counter()
            result = engine.search(query)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        engine.close()

        avg_time = sum(times) / len(times)
        max_time = max(times)

        print(f"\n  100 sequential searches:")
        print(f"    Average: {avg_time:.2f}ms")
        print(f"    Max: {max_time:.2f}ms")

        assert avg_time < 100, f"Avg time: {avg_time:.2f}ms (target: <100ms)"

    def test_mixed_operations(self, tmp_path):
        """Handle mixed index and search operations"""
        db_path = tmp_path / "search.db"
        engine = SearchEngine(db_path)

        # Pre-index 500 photos
        _, photos = generate_test_dataset(500, tmp_path)
        for filepath, metadata in photos[:500]:
            engine.index_photo(filepath, metadata)

        # Mix of searches and indexing
        times = []
        for i in range(50):
            # Index a photo
            start = time.perf_counter()
            engine.index_photo(f'photos/new_{i}.jpg', photos[i][1])

            # Search
            result = engine.search("moth")

            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        engine.close()

        avg_time = sum(times) / len(times)
        print(f"\n  Mixed operations: {avg_time:.2f}ms avg")
        assert avg_time < 150, f"Avg time: {avg_time:.2f}ms (target: <150ms)"


# ============================================================================
# Benchmark Summary
# ============================================================================

class TestBenchmarkSummary:
    """Generate comprehensive benchmark report"""

    def test_generate_benchmark_report(self, tmp_path):
        """Generate comprehensive benchmark report"""
        print("\n" + "=" * 70)
        print("FULL-TEXT SEARCH PERFORMANCE BENCHMARK REPORT")
        print("=" * 70)

        # Query parsing benchmarks
        print("\nQuery Parsing:")
        queries = ["moth", "tag:moth species:actias", '"luna moth" AND nocturnal']

        times = []
        for q in queries:
            start = time.perf_counter()
            for _ in range(1000):
                parse_query(q)
            elapsed = (time.perf_counter() - start) * 1000 / 1000
            times.append(elapsed)
            print(f"  '{q}': {elapsed:.4f}ms")

        # Indexing benchmarks
        print("\nIndexing Performance:")
        for count in [100, 500, 1000]:
            db_path, photos = generate_test_dataset(count, tmp_path / f"bench_{count}")
            engine = SearchEngine(db_path)

            start = time.perf_counter()
            for filepath, metadata in photos:
                engine.index_photo(filepath, metadata)
            elapsed = time.perf_counter() - start

            engine.close()

            photos_per_sec = count / elapsed
            print(f"  {count:>5} photos: {elapsed:>6.2f}s ({photos_per_sec:>5.0f} photos/sec)")

        # Search benchmarks
        print("\nSearch Performance (target: <200ms for 10K):")
        for count in [100, 500, 1000, 5000, 10000]:
            db_path, photos = generate_test_dataset(count, tmp_path / f"search_{count}")
            engine = SearchEngine(db_path)

            for filepath, metadata in photos:
                engine.index_photo(filepath, metadata)

            # Test queries
            test_queries = ["moth", "tag:nocturnal", "species:Actias*"]
            search_times = []

            for q in test_queries:
                start = time.perf_counter()
                result = engine.search(q)
                elapsed = (time.perf_counter() - start) * 1000
                search_times.append(elapsed)

            engine.close()

            avg_time = sum(search_times) / len(search_times)
            max_time = max(search_times)

            status = "✓" if max_time < 200 else "✗"
            print(f"  {count:>5} photos: avg {avg_time:>6.2f}ms, max {max_time:>6.2f}ms {status}")

        # Memory benchmarks
        print("\nMemory Usage:")
        for count in [1000, 5000, 10000]:
            db_path, photos = generate_test_dataset(count, tmp_path / f"mem_{count}")

            tracemalloc.start()
            engine = SearchEngine(db_path)

            for filepath, metadata in photos:
                engine.index_photo(filepath, metadata)

            # Perform searches
            for _ in range(5):
                engine.search("moth")

            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            engine.close()

            peak_mb = peak / 1024 / 1024
            print(f"  {count:>5} photos: {peak_mb:>6.2f}MB peak")

        print("\n" + "=" * 70)
        print("PRIMARY TARGET: 10,000 photos search in <200ms")
        print("All benchmarks completed successfully!")
        print("=" * 70)


# ============================================================================
# Run if executed directly
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])

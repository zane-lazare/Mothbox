"""
Performance tests for metadata cache (Issue #100).

Validates that the two-level cache meets performance targets:
- L1 cache hit: <10ms
- L2 cache hit: <50ms
- Overall cache hit rate: >70%
- Cached endpoint response: <100ms
"""

import pytest
import time
from pathlib import Path
import random


@pytest.fixture
def cache_dir(tmp_path):
    """Temporary cache directory for performance testing"""
    cache_path = tmp_path / "perf_cache"
    cache_path.mkdir()
    return cache_path


@pytest.fixture
def metadata_cache(cache_dir):
    """Metadata cache for performance testing"""
    from webui.backend.services.metadata_cache import MetadataCache
    return MetadataCache(cache_dir, l1_max_size=1000, l2_max_size=10000)


@pytest.fixture
def sample_metadata():
    """Sample metadata for performance testing"""
    return {
        "camera": {
            "make": "Arducam",
            "model": "OwlSight 64MP",
            "iso": 100,
            "exposure_time": "1/100",
            "f_number": 2.8
        },
        "location": {
            "latitude": 34.0522,
            "longitude": -118.2437,
            "altitude": 100.5
        },
        "capture": {
            "timestamp": "2024-01-15T22:30:45"
        },
        "deployment": {
            "mothbox_id": "mothbox-perf-test"
        },
        "file": {
            "path": "/photos/perf_test.jpg",
            "size": 1024000
        }
    }


@pytest.mark.performance
class TestMetadataCacheL1Performance:
    """Performance benchmarks for L1 memory cache"""

    def test_l1_cache_latency_single_item(self, metadata_cache, sample_metadata):
        """L1 cache hits are <10ms (single item, cold cache)"""
        photo_path = "/photos/test.jpg"
        metadata_cache.set(photo_path, sample_metadata)

        # Warmup
        for _ in range(10):
            metadata_cache.get(photo_path)

        # Benchmark 1000 accesses
        start = time.time()
        for _ in range(1000):
            result = metadata_cache.get(photo_path)
            assert result is not None
        elapsed = time.time() - start

        avg_latency_ms = (elapsed / 1000) * 1000
        print(f"\nL1 single item latency: {avg_latency_ms:.3f}ms per access")

        assert avg_latency_ms < 10, f"L1 latency {avg_latency_ms:.2f}ms exceeds 10ms target"

    def test_l1_cache_latency_hot_cache(self, metadata_cache, sample_metadata):
        """L1 cache with 100 items maintains <10ms access time"""
        # Fill cache with 100 items
        for i in range(100):
            photo_path = f"/photos/photo_{i}.jpg"
            metadata_cache.set(photo_path, sample_metadata)

        # Warmup
        for i in range(10):
            metadata_cache.get(f"/photos/photo_{i}.jpg")

        # Benchmark random access pattern
        start = time.time()
        for _ in range(1000):
            i = random.randint(0, 99)
            result = metadata_cache.get(f"/photos/photo_{i}.jpg")
            assert result is not None
        elapsed = time.time() - start

        avg_latency_ms = (elapsed / 1000) * 1000
        print(f"\nL1 hot cache (100 items) latency: {avg_latency_ms:.3f}ms per access")

        assert avg_latency_ms < 10, f"L1 latency {avg_latency_ms:.2f}ms exceeds 10ms target"


@pytest.mark.performance
class TestMetadataCacheL2Performance:
    """Performance benchmarks for L2 file cache"""

    def test_l2_cache_latency(self, cache_dir, sample_metadata):
        """L2 cache hits are <50ms"""
        from webui.backend.services.metadata_cache import MetadataCache

        photo_path = "/photos/test.jpg"

        # Create cache with small L1 to force L2 access
        cache = MetadataCache(cache_dir, l1_max_size=1, l2_max_size=10000)
        cache.set(photo_path, sample_metadata)

        # Evict from L1 by adding another item
        cache.set("/photos/other.jpg", sample_metadata)

        # Warmup L2 access
        for _ in range(5):
            result = cache.get(photo_path)
            # Evict from L1 again
            cache._l1_cache.clear()
            cache._l1_access_order.clear()

        # Benchmark L2 access (clearing L1 each time)
        latencies = []
        for _ in range(50):
            # Clear L1 to force L2 access
            cache._l1_cache.clear()
            cache._l1_access_order.clear()

            start = time.time()
            result = cache.get(photo_path)
            elapsed = (time.time() - start) * 1000
            latencies.append(elapsed)
            assert result is not None

        avg_latency_ms = sum(latencies) / len(latencies)
        max_latency_ms = max(latencies)
        print(f"\nL2 cache latency: avg={avg_latency_ms:.2f}ms, max={max_latency_ms:.2f}ms")

        assert avg_latency_ms < 50, f"L2 avg latency {avg_latency_ms:.2f}ms exceeds 50ms target"

    def test_l2_cache_persistence_performance(self, cache_dir, sample_metadata):
        """L2 cache persists and retrieves 100 items efficiently"""
        from webui.backend.services.metadata_cache import MetadataCache

        # Benchmark writing 100 items
        cache1 = MetadataCache(cache_dir, l1_max_size=10, l2_max_size=10000)

        start = time.time()
        for i in range(100):
            photo_path = f"/photos/photo_{i}.jpg"
            cache1.set(photo_path, sample_metadata)
        write_time = time.time() - start

        print(f"\nL2 write time for 100 items: {write_time:.3f}s ({write_time*10:.1f}ms per item)")

        # Benchmark reading from new cache instance (L2 only)
        cache2 = MetadataCache(cache_dir, l1_max_size=10, l2_max_size=10000)

        start = time.time()
        hits = 0
        for i in range(100):
            photo_path = f"/photos/photo_{i}.jpg"
            result = cache2.get(photo_path)
            if result:
                hits += 1
        read_time = time.time() - start

        print(f"L2 read time for 100 items: {read_time:.3f}s ({read_time*10:.1f}ms per item)")
        print(f"L2 hit rate: {hits}/100")

        assert hits == 100, f"Expected 100 L2 hits, got {hits}"
        assert read_time < 10.0, f"L2 read time {read_time:.2f}s exceeds 10s for 100 items"


@pytest.mark.performance
class TestMetadataCacheHitRate:
    """Test cache hit rate under realistic workloads"""

    def test_cache_hit_rate_zipf_distribution(self, metadata_cache, sample_metadata):
        """Cache achieves >70% hit rate under Zipf-distributed access (realistic gallery browsing)"""
        # Simulate 200 unique photos
        num_photos = 200
        for i in range(num_photos):
            photo_path = f"/photos/photo_{i:04d}.jpg"
            metadata_cache.set(photo_path, sample_metadata)

        # Clear L1 to start fresh
        metadata_cache._l1_cache.clear()
        metadata_cache._l1_access_order.clear()

        # Reset statistics
        with metadata_cache._stats_lock:
            metadata_cache._l1_hits = 0
            metadata_cache._l1_misses = 0
            metadata_cache._l2_hits = 0
            metadata_cache._l2_misses = 0

        # Simulate Zipf distribution (20% of photos get 80% of views)
        # This mimics real gallery usage: users focus on recent photos
        popular_photos = 40  # Top 20%
        total_requests = 1000

        for _ in range(total_requests):
            # 80% chance to access popular photos, 20% chance for others
            if random.random() < 0.8:
                i = random.randint(0, popular_photos - 1)
            else:
                i = random.randint(popular_photos, num_photos - 1)

            photo_path = f"/photos/photo_{i:04d}.jpg"
            result = metadata_cache.get(photo_path)
            assert result is not None

        # Check statistics
        stats = metadata_cache.get_statistics()
        print(f"\nZipf distribution cache performance:")
        print(f"  Total requests: {total_requests}")
        print(f"  L1 hits: {stats.l1_hits} ({stats.l1_hits/total_requests*100:.1f}%)")
        print(f"  L2 hits: {stats.l2_hits} ({stats.l2_hits/total_requests*100:.1f}%)")
        print(f"  Total misses: {stats.total_misses} ({stats.total_misses/total_requests*100:.1f}%)")
        print(f"  Overall hit rate: {stats.hit_ratio*100:.1f}%")
        print(f"  Avg response time: {stats.avg_response_time_ms:.2f}ms")

        # Validate performance targets
        assert stats.hit_ratio > 0.70, f"Hit rate {stats.hit_ratio*100:.1f}% below 70% target"
        assert stats.avg_response_time_ms < 100, f"Avg response time {stats.avg_response_time_ms:.2f}ms exceeds 100ms"

    def test_cache_hit_rate_sequential_access(self, metadata_cache, sample_metadata):
        """Cache handles sequential access (pagination) efficiently"""
        # Simulate 100 photos
        num_photos = 100
        for i in range(num_photos):
            photo_path = f"/photos/photo_{i:04d}.jpg"
            metadata_cache.set(photo_path, sample_metadata)

        # Clear L1 only to start fresh (keep L2 populated)
        metadata_cache._l1_cache.clear()
        metadata_cache._l1_access_order.clear()

        # Reset statistics
        with metadata_cache._stats_lock:
            metadata_cache._l1_hits = 0
            metadata_cache._l1_misses = 0
            metadata_cache._l2_hits = 0
            metadata_cache._l2_misses = 0

        # Simulate pagination: user views photos in pages of 10
        page_size = 10
        num_pages = num_photos // page_size

        # First pass: L2 hits (L1 empty, L2 populated)
        for page in range(num_pages):
            for i in range(page * page_size, (page + 1) * page_size):
                photo_path = f"/photos/photo_{i:04d}.jpg"
                result = metadata_cache.get(photo_path)
                assert result is not None  # Should hit L2

        # Second pass: should hit L1 (promoted from L2)
        for page in range(num_pages):
            for i in range(page * page_size, (page + 1) * page_size):
                photo_path = f"/photos/photo_{i:04d}.jpg"
                result = metadata_cache.get(photo_path)
                assert result is not None

        stats = metadata_cache.get_statistics()
        print(f"\nSequential access performance:")
        print(f"  Total requests: {num_photos * 2}")
        print(f"  L1 hits: {stats.l1_hits} ({stats.l1_hits/(num_photos*2)*100:.1f}%)")
        print(f"  L2 hits: {stats.l2_hits} ({stats.l2_hits/(num_photos*2)*100:.1f}%)")
        print(f"  Hit rate: {stats.hit_ratio*100:.1f}%")
        print(f"  Avg response time: {stats.avg_response_time_ms:.2f}ms")

        # Should have 100% hit rate (first pass L2, second pass L1)
        assert stats.hit_ratio > 0.95, f"Hit rate {stats.hit_ratio*100:.1f}% unexpectedly low"


@pytest.mark.performance
class TestMetadataCacheThroughput:
    """Test cache throughput and scalability"""

    def test_cache_throughput_mixed_operations(self, metadata_cache, sample_metadata):
        """Cache handles mixed read/write operations efficiently"""
        num_operations = 1000

        start = time.time()
        for i in range(num_operations):
            photo_path = f"/photos/photo_{i % 100}.jpg"

            # 80% reads, 20% writes (typical workload)
            if random.random() < 0.8:
                result = metadata_cache.get(photo_path)
            else:
                metadata_cache.set(photo_path, sample_metadata)

        elapsed = time.time() - start
        ops_per_second = num_operations / elapsed

        print(f"\nMixed operations throughput:")
        print(f"  Total operations: {num_operations}")
        print(f"  Time: {elapsed:.3f}s")
        print(f"  Throughput: {ops_per_second:.1f} ops/sec")

        # Should handle >1000 ops/sec easily
        assert ops_per_second > 1000, f"Throughput {ops_per_second:.1f} ops/sec below 1000 target"

    def test_cache_memory_efficiency(self, cache_dir, sample_metadata):
        """Cache memory usage stays reasonable under load"""
        from webui.backend.services.metadata_cache import MetadataCache
        import sys

        # Create cache with moderate L1 size
        cache = MetadataCache(cache_dir, l1_max_size=100, l2_max_size=10000)

        # Measure L1 cache memory before loading
        cache_size_before = sys.getsizeof(cache._l1_cache)

        # Fill L1 to capacity
        for i in range(100):
            photo_path = f"/photos/photo_{i}.jpg"
            cache.set(photo_path, sample_metadata)

        # Measure L1 cache memory after loading
        cache_size_after = sys.getsizeof(cache._l1_cache)
        cache_size_mb = (cache_size_after - cache_size_before) / (1024 * 1024)

        print(f"\nL1 cache memory usage:")
        print(f"  Items: 100")
        print(f"  Memory: {cache_size_mb:.2f}MB")
        print(f"  Per item: {cache_size_mb/100*1024:.1f}KB")

        # L1 should use <10MB for 100 items
        assert cache_size_mb < 10, f"L1 memory {cache_size_mb:.2f}MB exceeds 10MB target"


@pytest.mark.performance
class TestEndToEndPerformance:
    """End-to-end performance tests simulating real API usage"""

    def test_api_response_time_cached(self, tmp_path, monkeypatch, sample_metadata):
        """Cached API responses are <100ms"""
        from flask import Flask
        from unittest.mock import patch, MagicMock
        import sys

        # Setup test environment
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))

        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'PHOTOS_DIR', photos_dir)
        monkeypatch.setattr(mothbox_paths, 'DATA_DIR', data_dir)

        # Import after patching
        from webui.backend.routes.gallery import gallery_bp, _reset_cache
        import webui.backend.routes.gallery as gallery_module
        monkeypatch.setattr(gallery_module, 'PHOTOS_DIR', photos_dir)
        monkeypatch.setattr(gallery_module, 'DATA_DIR', data_dir)

        _reset_cache()

        # Create Flask app
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(gallery_bp)
        client = app.test_client()

        # Create test photo
        from PIL import Image
        photo_path = photos_dir / "test.jpg"
        img = Image.new('RGB', (100, 100), color='red')
        img.save(photo_path, "JPEG")

        # Mock MetadataService
        with patch('webui.backend.routes.gallery.MetadataService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_photo_metadata.return_value = sample_metadata
            mock_service.return_value = mock_instance

            # Warmup: populate cache
            for _ in range(3):
                client.get('/api/gallery/photos/test.jpg/metadata')

            # Benchmark cached responses
            latencies = []
            for _ in range(20):
                start = time.time()
                response = client.get('/api/gallery/photos/test.jpg/metadata')
                elapsed = (time.time() - start) * 1000
                latencies.append(elapsed)

                assert response.status_code == 200
                data = response.get_json()
                assert data['cache_info']['cached'] is True

            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            min_latency = min(latencies)

            print(f"\nCached API response times:")
            print(f"  Average: {avg_latency:.2f}ms")
            print(f"  Min: {min_latency:.2f}ms")
            print(f"  Max: {max_latency:.2f}ms")

            assert avg_latency < 100, f"Avg response time {avg_latency:.2f}ms exceeds 100ms target"

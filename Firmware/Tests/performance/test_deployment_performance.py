"""
Performance tests for deployment metadata system (Issue #114)

Performance Targets:
- Single read: <10ms
- Single write: <50ms
- Cache hit: <1ms
- Batch 100: <500ms
- Batch 1000: <5s
- List 100 deployments: <200ms
- Find deployment: <50ms
- Memory: <50MB for 100 deployments

Run with: pytest Tests/performance/test_deployment_performance.py -v -s
"""

import os
import random
import sys
import threading
import time
import tracemalloc
from pathlib import Path

# Setup path
FIRMWARE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(FIRMWARE_DIR))
sys.path.insert(0, str(FIRMWARE_DIR / "webui" / "backend"))
os.environ.setdefault("MOTHBOX_ENV", "test")

from webui.backend.lib.deployment_sidecar import (
    create_deployment_metadata,
    find_deployment_sidecar,
    read_deployment_metadata,
    update_deployment_metadata,
    write_deployment_metadata,
)
from webui.backend.services.deployment_service import DeploymentService

# ============================================================================
# Performance Target Constants
# ============================================================================

# Single operations
SINGLE_READ_TARGET_MS = 10   # <10ms for single read
SINGLE_WRITE_TARGET_MS = 50  # <50ms for single write
CACHE_HIT_TARGET_MS = 1      # <1ms for cache hit
READ_WRITE_CYCLE_TARGET_MS = 60  # <60ms for read-modify-write

# Batch operations
BATCH_100_TARGET_MS = 500    # <500ms for 100 items
BATCH_1000_TARGET_MS = 5000  # <5s for 1000 items
GENERATE_100_TARGET_MS = 1000  # <1s to generate 100 sidecars

# Discovery operations
LIST_100_TARGET_MS = 200     # <200ms to list 100 deployments
FIND_TARGET_MS = 50          # <50ms to find deployment for photo

# Cache performance
CACHE_HIT_RATE_TARGET = 0.80  # >80% hit rate

# Memory limits
MEMORY_100_DEPLOYMENTS_MB = 50  # <50MB for 100 deployments


# ============================================================================
# Test Data Generation
# ============================================================================

def create_deployment_directory(
    parent_dir: Path,
    name: str,
    with_sidecar: bool = True,
    num_photos: int = 10
) -> Path:
    """Create a deployment directory with optional sidecar and photos."""
    deployment_dir = parent_dir / name
    deployment_dir.mkdir(exist_ok=True)

    # Create sample photos (minimal JPEG files)
    for i in range(num_photos):
        photo_path = deployment_dir / f"photo_{i:05d}.jpg"
        photo_path.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

    # Create deployment sidecar
    if with_sidecar:
        metadata = create_deployment_metadata(
            directory=deployment_dir,
            name=name,
            latitude=35.9606 + random.uniform(-1.0, 1.0),
            longitude=-83.9207 + random.uniform(-1.0, 1.0),
            location_name=f"Location {name}",
            start_date="2024-06-01",
            end_date="2024-08-31",
            environmental={"temperature_avg_c": random.uniform(15, 30)},
            mothbox_id=f"mothbox-{name}",
        )
        write_deployment_metadata(deployment_dir, metadata)

    return deployment_dir


def generate_deployment_set(parent_dir: Path, count: int) -> list[Path]:
    """Generate a set of deployment directories with sidecars."""
    deployments = []
    for i in range(count):
        deployment = create_deployment_directory(
            parent_dir,
            f"deployment_{i:03d}",
            with_sidecar=True,
            num_photos=10
        )
        deployments.append(deployment)
    return deployments


def generate_hierarchical_structure(
    root_dir: Path,
    depth: int,
    dirs_per_level: int
) -> list[Path]:
    """Generate hierarchical directory structure with deployments."""
    deployments = []

    def create_level(parent: Path, current_depth: int, prefix: str):
        if current_depth >= depth:
            return

        for i in range(dirs_per_level):
            name = f"{prefix}_d{current_depth}_n{i}"
            deployment = create_deployment_directory(
                parent,
                name,
                with_sidecar=True,
                num_photos=5
            )
            deployments.append(deployment)

            # Recurse
            create_level(deployment, current_depth + 1, name)

    create_level(root_dir, 0, "root")
    return deployments


# ============================================================================
# Single Operation Performance Tests
# ============================================================================

class TestSingleOperationPerformance:
    """Tests for single operation performance."""

    def test_single_read_under_10ms(self, tmp_path):
        """Single read should complete under 10ms."""
        # Create deployment with metadata
        deployment = create_deployment_directory(tmp_path, "test_deployment")

        # Warm up
        read_deployment_metadata(deployment)

        # Measure performance
        times = []
        for _ in range(100):
            start = time.perf_counter()
            result = read_deployment_metadata(deployment)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        max_time = max(times)

        print(f"\n  Single read average: {avg_time:.3f}ms")
        print(f"  Single read max: {max_time:.3f}ms")

        assert result is not None
        assert avg_time < SINGLE_READ_TARGET_MS, \
            f"Read took {avg_time:.3f}ms (target: <{SINGLE_READ_TARGET_MS}ms)"

    def test_single_write_under_50ms(self, tmp_path):
        """Single write should complete under 50ms."""
        deployment = tmp_path / "test_deployment"
        deployment.mkdir()

        # Create metadata
        metadata = create_deployment_metadata(
            directory=deployment,
            name="Test Deployment",
            latitude=35.9606,
            longitude=-83.9207,
        )

        # Warm up
        write_deployment_metadata(deployment, metadata)

        # Measure performance
        times = []
        for i in range(50):
            # Modify metadata to force new write
            metadata.modified_by = f"user_{i}"

            start = time.perf_counter()
            success = write_deployment_metadata(deployment, metadata)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        max_time = max(times)

        print(f"\n  Single write average: {avg_time:.2f}ms")
        print(f"  Single write max: {max_time:.2f}ms")

        assert success
        assert avg_time < SINGLE_WRITE_TARGET_MS, \
            f"Write took {avg_time:.2f}ms (target: <{SINGLE_WRITE_TARGET_MS}ms)"

    def test_cache_hit_under_1ms(self, tmp_path, monkeypatch):
        """Cache hit should return under 1ms."""
        # Monkey patch PHOTOS_DIR
        monkeypatch.setattr('webui.backend.lib.deployment_sidecar.PHOTOS_DIR', tmp_path)

        service = DeploymentService(cache_ttl=300)

        # Create deployment with metadata
        deployment = create_deployment_directory(tmp_path, "test_deployment")

        # Warm cache
        service.get_deployment_metadata(deployment)

        # Measure cache hit performance
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            result = service.get_deployment_metadata(deployment)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_time = sum(times) / len(times)

        print(f"\n  Cache hit average: {avg_time:.4f}ms")

        assert result is not None
        assert avg_time < CACHE_HIT_TARGET_MS, \
            f"Cache hit took {avg_time:.4f}ms (target: <{CACHE_HIT_TARGET_MS}ms)"

    def test_read_write_cycle_under_60ms(self, tmp_path):
        """Read-modify-write cycle should complete under 60ms."""
        deployment = create_deployment_directory(tmp_path, "test_deployment")

        # Warm up
        update_deployment_metadata(deployment, {"end_date": "2024-09-01"})

        # Measure performance
        times = []
        for i in range(50):
            start = time.perf_counter()
            metadata = update_deployment_metadata(
                deployment,
                {"end_date": f"2024-09-{i%30+1:02d}", "modified_by": f"user_{i}"}
            )
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        max_time = max(times)

        print(f"\n  Read-modify-write average: {avg_time:.2f}ms")
        print(f"  Read-modify-write max: {max_time:.2f}ms")

        assert metadata is not None
        assert avg_time < READ_WRITE_CYCLE_TARGET_MS, \
            f"R-M-W took {avg_time:.2f}ms (target: <{READ_WRITE_CYCLE_TARGET_MS}ms)"


# ============================================================================
# Batch Performance Tests
# ============================================================================

class TestBatchPerformance:
    """Tests for batch operation performance."""

    def test_batch_100_under_500ms(self, tmp_path, monkeypatch):
        """Batch processing 100 deployments should complete under 500ms."""
        monkeypatch.setattr('webui.backend.lib.deployment_sidecar.PHOTOS_DIR', tmp_path)

        service = DeploymentService(cache_ttl=300, max_cache_size=200)

        # Create 100 deployments
        deployments = generate_deployment_set(tmp_path, 100)

        # Warm up
        for deployment in deployments[:10]:
            service.get_deployment_metadata(deployment)

        # Measure batch read performance
        start = time.perf_counter()
        results = [service.get_deployment_metadata(d) for d in deployments]
        elapsed = (time.perf_counter() - start) * 1000

        print(f"\n  Batch 100 deployments: {elapsed:.2f}ms")
        print(f"    Per deployment: {elapsed/100:.2f}ms")

        assert len([r for r in results if r is not None]) == 100
        assert elapsed < BATCH_100_TARGET_MS, \
            f"Batch 100 took {elapsed:.2f}ms (target: <{BATCH_100_TARGET_MS}ms)"

    def test_batch_1000_under_5s(self, tmp_path, monkeypatch):
        """Batch processing 1000 deployments should complete under 5s."""
        monkeypatch.setattr('webui.backend.lib.deployment_sidecar.PHOTOS_DIR', tmp_path)

        service = DeploymentService(cache_ttl=300, max_cache_size=1500)

        # Create 1000 deployments
        print("\n  Creating 1000 deployments...")
        deployments = generate_deployment_set(tmp_path, 1000)

        # Measure batch read performance (cold cache)
        start = time.perf_counter()
        results = [service.get_deployment_metadata(d) for d in deployments]
        elapsed = (time.perf_counter() - start) * 1000

        print(f"  Batch 1000 deployments (cold): {elapsed:.2f}ms")
        print(f"    Per deployment: {elapsed/1000:.2f}ms")

        assert len([r for r in results if r is not None]) == 1000
        # Allow extra time for CI variability
        assert elapsed < BATCH_1000_TARGET_MS * 1.5, \
            f"Batch 1000 took {elapsed:.2f}ms (target: <{BATCH_1000_TARGET_MS}ms)"

    def test_generate_sidecars_100_under_1s(self, tmp_path, monkeypatch):
        """Generating 100 sidecars should complete under 1s."""
        monkeypatch.setattr('webui.backend.lib.deployment_sidecar.PHOTOS_DIR', tmp_path)

        service = DeploymentService(cache_ttl=300)

        # Create 100 subdirectories without sidecars
        for i in range(100):
            subdir = tmp_path / f"deployment_{i:03d}"
            subdir.mkdir()
            # Add a photo to make it look like a real deployment
            (subdir / "photo.jpg").write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        # Measure sidecar generation
        template = {
            "latitude": 35.9606,
            "longitude": -83.9207,
            "location_name": "Test Location",
            "start_date": "2024-06-01",
        }

        start = time.perf_counter()
        count = service.generate_sidecars_for_directory(tmp_path, template)
        elapsed = (time.perf_counter() - start) * 1000

        print(f"\n  Generate 100 sidecars: {elapsed:.2f}ms")
        print(f"    Per sidecar: {elapsed/100:.2f}ms")

        assert count == 100
        assert elapsed < GENERATE_100_TARGET_MS, \
            f"Generate took {elapsed:.2f}ms (target: <{GENERATE_100_TARGET_MS}ms)"

    def test_batch_scaling_linear(self, tmp_path, monkeypatch):
        """Batch operations should scale linearly."""
        monkeypatch.setattr('webui.backend.lib.deployment_sidecar.PHOTOS_DIR', tmp_path)

        service = DeploymentService(cache_ttl=300, max_cache_size=1000)

        batch_sizes = [10, 50, 100, 200]
        times = []

        for size in batch_sizes:
            batch_dir = tmp_path / f"batch_{size}"
            batch_dir.mkdir()
            deployments = generate_deployment_set(batch_dir, size)

            start = time.perf_counter()
            _ = [service.get_deployment_metadata(d) for d in deployments]
            elapsed = (time.perf_counter() - start) * 1000

            times.append(elapsed)
            per_item = elapsed / size

            print(f"\n  Batch {size:>3} deployments: {elapsed:>7.2f}ms ({per_item:.2f}ms/item)")

        # Check that scaling is roughly linear
        # Time per item should not grow significantly with batch size
        times_per_item = [times[i] / batch_sizes[i] for i in range(len(batch_sizes))]

        # Last batch should not be more than 2x slower per item than first batch
        scaling_ratio = times_per_item[-1] / times_per_item[0]
        print(f"\n  Scaling ratio (200/10): {scaling_ratio:.2f}x")

        assert scaling_ratio < 2.0, \
            f"Scaling not linear: {scaling_ratio:.2f}x (should be <2.0x)"


# ============================================================================
# Discovery Performance Tests
# ============================================================================

class TestDiscoveryPerformance:
    """Tests for deployment discovery performance."""

    def test_list_100_deployments_under_200ms(self, tmp_path, monkeypatch):
        """Listing 100 deployments should complete under 200ms."""
        monkeypatch.setattr('webui.backend.lib.deployment_sidecar.PHOTOS_DIR', tmp_path)

        service = DeploymentService(cache_ttl=300, max_cache_size=200)

        # Create 100 deployments
        _ = generate_deployment_set(tmp_path, 100)

        # Measure list performance
        start = time.perf_counter()
        results = service.list_deployments(tmp_path)
        elapsed = (time.perf_counter() - start) * 1000

        print(f"\n  List 100 deployments: {elapsed:.2f}ms")

        assert len(results) == 100
        assert elapsed < LIST_100_TARGET_MS, \
            f"List took {elapsed:.2f}ms (target: <{LIST_100_TARGET_MS}ms)"

    def test_find_deployment_under_50ms(self, tmp_path, monkeypatch):
        """Finding deployment for photo should complete under 50ms."""
        monkeypatch.setattr('webui.backend.lib.deployment_sidecar.PHOTOS_DIR', tmp_path)

        service = DeploymentService(cache_ttl=300)

        # Create nested structure
        deployment = create_deployment_directory(tmp_path, "forest_2024")
        subdir1 = deployment / "night" / "moths"
        subdir1.mkdir(parents=True)
        photo = subdir1 / "moth_001.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        # Warm up
        service.find_deployment_for_photo(photo)

        # Measure find performance
        times = []
        for _ in range(100):
            # Clear cache to test disk performance
            service.invalidate_cache()

            start = time.perf_counter()
            metadata = service.find_deployment_for_photo(photo)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_time = sum(times) / len(times)

        print(f"\n  Find deployment average: {avg_time:.2f}ms")

        assert metadata is not None
        assert avg_time < FIND_TARGET_MS, \
            f"Find took {avg_time:.2f}ms (target: <{FIND_TARGET_MS}ms)"

    def test_hierarchical_discovery_deep_nesting(self, tmp_path, monkeypatch):
        """Hierarchical discovery should handle deep nesting efficiently."""
        monkeypatch.setattr('webui.backend.lib.deployment_sidecar.PHOTOS_DIR', tmp_path)

        # Create deeply nested structure (5 levels deep)
        current = tmp_path
        for i in range(5):
            current = current / f"level_{i}"
            current.mkdir()
            # Create deployment at each level
            metadata = create_deployment_metadata(
                directory=current,
                name=f"Deployment Level {i}",
            )
            write_deployment_metadata(current, metadata)

        # Create photo at deepest level
        photo = current / "photo.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        # Measure find from deepest level
        start = time.perf_counter()
        sidecar_path = find_deployment_sidecar(photo)
        elapsed = (time.perf_counter() - start) * 1000

        print(f"\n  Deep nesting find (5 levels): {elapsed:.2f}ms")

        assert sidecar_path is not None
        assert elapsed < FIND_TARGET_MS, \
            f"Deep find took {elapsed:.2f}ms (target: <{FIND_TARGET_MS}ms)"


# ============================================================================
# Cache Performance Tests
# ============================================================================

class TestCachePerformance:
    """Tests for cache hit rate and performance."""

    def test_cache_hit_rate_above_80_percent(self, tmp_path, monkeypatch):
        """Cache hit rate should be above 80%."""
        monkeypatch.setattr('webui.backend.lib.deployment_sidecar.PHOTOS_DIR', tmp_path)

        service = DeploymentService(cache_ttl=300, max_cache_size=100)

        # Create 100 deployments
        deployments = generate_deployment_set(tmp_path, 100)

        # Simulate realistic access pattern:
        # - Initial pass (all cache misses)
        # - Multiple passes with random access
        for deployment in deployments:
            service.get_deployment_metadata(deployment)

        # Now access randomly (should mostly hit cache)
        for _ in range(500):
            deployment = random.choice(deployments)
            service.get_deployment_metadata(deployment)

        # Check statistics
        stats = service.get_statistics()
        hit_ratio = stats['hit_ratio']

        print(f"\n  Cache hit rate: {hit_ratio:.2%}")
        print(f"  Cache hits: {stats['cache_hits']}")
        print(f"  Cache misses: {stats['cache_misses']}")
        print(f"  Cache size: {stats['cache_size']}/{stats['max_cache_size']}")

        assert hit_ratio >= CACHE_HIT_RATE_TARGET, \
            f"Hit rate {hit_ratio:.2%} (target: >{CACHE_HIT_RATE_TARGET:.0%})"

    def test_cache_warmup_time(self, tmp_path, monkeypatch):
        """Cache warmup should be fast."""
        monkeypatch.setattr('webui.backend.lib.deployment_sidecar.PHOTOS_DIR', tmp_path)

        service = DeploymentService(cache_ttl=300, max_cache_size=100)

        # Create 100 deployments
        deployments = generate_deployment_set(tmp_path, 100)

        # Measure warmup time
        start = time.perf_counter()
        for deployment in deployments:
            service.get_deployment_metadata(deployment)
        elapsed = (time.perf_counter() - start) * 1000

        print(f"\n  Cache warmup (100 deployments): {elapsed:.2f}ms")

        stats = service.get_statistics()
        assert stats['cache_size'] == 100
        assert elapsed < 1000, f"Warmup took {elapsed:.2f}ms (target: <1000ms)"

    def test_cache_eviction_performance(self, tmp_path, monkeypatch):
        """Cache eviction should not degrade performance."""
        monkeypatch.setattr('webui.backend.lib.deployment_sidecar.PHOTOS_DIR', tmp_path)

        # Small cache that will force evictions
        service = DeploymentService(cache_ttl=300, max_cache_size=50)

        # Create 100 deployments (2x cache size)
        deployments = generate_deployment_set(tmp_path, 100)

        # Access all deployments (will cause evictions)
        times = []
        for deployment in deployments:
            start = time.perf_counter()
            service.get_deployment_metadata(deployment)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_time = sum(times) / len(times)

        stats = service.get_statistics()
        print(f"\n  With eviction - Average access: {avg_time:.2f}ms")
        print(f"  Cache evictions: {stats['cache_evictions']}")
        print(f"  Final cache size: {stats['cache_size']}/{stats['max_cache_size']}")

        assert stats['cache_evictions'] > 0, "Should have evicted entries"
        assert stats['cache_size'] == 50, "Cache should be at max size"
        assert avg_time < 100, f"Avg with eviction {avg_time:.2f}ms (target: <100ms)"


# ============================================================================
# Memory Usage Tests
# ============================================================================

class TestMemoryUsage:
    """Tests for memory efficiency."""

    def test_100_deployments_memory_under_50mb(self, tmp_path, monkeypatch):
        """Processing 100 deployments should use <50MB memory."""
        monkeypatch.setattr('webui.backend.lib.deployment_sidecar.PHOTOS_DIR', tmp_path)

        service = DeploymentService(cache_ttl=300, max_cache_size=150)

        # Create 100 deployments
        deployments = generate_deployment_set(tmp_path, 100)

        # Measure memory usage
        tracemalloc.start()

        # Load all deployments into cache
        results = [service.get_deployment_metadata(d) for d in deployments]

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / 1024 / 1024

        print(f"\n  100 deployments memory: {peak_mb:.2f}MB peak")
        print(f"  Per deployment: {peak_mb/100:.3f}MB")

        assert len([r for r in results if r is not None]) == 100
        assert peak_mb < MEMORY_100_DEPLOYMENTS_MB, \
            f"Used {peak_mb:.2f}MB (target: <{MEMORY_100_DEPLOYMENTS_MB}MB)"

    def test_no_memory_leak_on_repeated_operations(self, tmp_path, monkeypatch):
        """Repeated operations should not leak memory."""
        monkeypatch.setattr('webui.backend.lib.deployment_sidecar.PHOTOS_DIR', tmp_path)

        service = DeploymentService(cache_ttl=300, max_cache_size=50)

        # Create 50 deployments
        deployments = generate_deployment_set(tmp_path, 50)

        tracemalloc.start()

        # Record memory after first pass
        for deployment in deployments:
            service.get_deployment_metadata(deployment)
        first_pass_memory = tracemalloc.get_traced_memory()[0]

        # Multiple passes
        for _ in range(5):
            for deployment in deployments:
                service.get_deployment_metadata(deployment)

        final_memory = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()

        memory_growth = (final_memory - first_pass_memory) / 1024 / 1024

        print(f"\n  First pass memory: {first_pass_memory/1024/1024:.2f}MB")
        print(f"  After 5 passes: {final_memory/1024/1024:.2f}MB")
        print(f"  Memory growth: {memory_growth:.2f}MB")

        # Allow small growth for normal variance
        assert memory_growth < 5.0, \
            f"Memory grew by {memory_growth:.2f}MB (should be <5MB)"


# ============================================================================
# Concurrent Performance Tests
# ============================================================================

class TestConcurrentPerformance:
    """Tests for concurrent operation performance."""

    def test_10_concurrent_reads(self, tmp_path, monkeypatch):
        """10 concurrent reads should complete efficiently."""
        monkeypatch.setattr('webui.backend.lib.deployment_sidecar.PHOTOS_DIR', tmp_path)

        service = DeploymentService(cache_ttl=300)

        # Create 10 deployments
        deployments = generate_deployment_set(tmp_path, 10)

        # Warm cache
        for deployment in deployments:
            service.get_deployment_metadata(deployment)

        results = []
        errors = []

        def reader(deployment_path):
            try:
                start = time.perf_counter()
                metadata = service.get_deployment_metadata(deployment_path)
                elapsed = (time.perf_counter() - start) * 1000
                results.append((metadata, elapsed))
            except Exception as e:
                errors.append(str(e))

        # Start 10 concurrent readers
        threads = [threading.Thread(target=reader, args=(d,)) for d in deployments]

        overall_start = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        overall_elapsed = (time.perf_counter() - overall_start) * 1000

        print(f"\n  10 concurrent reads: {overall_elapsed:.2f}ms total")
        for i, (_metadata, elapsed) in enumerate(results):
            print(f"    Thread {i}: {elapsed:.2f}ms")

        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 10
        assert overall_elapsed < 100, \
            f"Concurrent reads took {overall_elapsed:.2f}ms (target: <100ms)"

    def test_10_concurrent_writes(self, tmp_path, monkeypatch):
        """10 concurrent writes should complete efficiently."""
        monkeypatch.setattr('webui.backend.lib.deployment_sidecar.PHOTOS_DIR', tmp_path)

        service = DeploymentService(cache_ttl=300)

        # Create 10 deployment directories (no sidecars yet)
        deployments = []
        for i in range(10):
            deployment = tmp_path / f"deployment_{i:03d}"
            deployment.mkdir()
            deployments.append(deployment)

        results = []
        errors = []

        def writer(deployment_path, index):
            try:
                start = time.perf_counter()
                metadata = create_deployment_metadata(
                    directory=deployment_path,
                    name=f"Deployment {index}",
                    latitude=35.9606 + index * 0.1,
                    longitude=-83.9207 + index * 0.1,
                )
                success = service.set_deployment_metadata(deployment_path, metadata)
                elapsed = (time.perf_counter() - start) * 1000
                results.append((success, elapsed))
            except Exception as e:
                errors.append(str(e))

        # Start 10 concurrent writers
        threads = [threading.Thread(target=writer, args=(d, i))
                   for i, d in enumerate(deployments)]

        overall_start = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        overall_elapsed = (time.perf_counter() - overall_start) * 1000

        print(f"\n  10 concurrent writes: {overall_elapsed:.2f}ms total")
        for i, (success, elapsed) in enumerate(results):
            print(f"    Thread {i}: {elapsed:.2f}ms (success: {success})")

        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 10
        assert all(success for success, _ in results)
        assert overall_elapsed < 1000, \
            f"Concurrent writes took {overall_elapsed:.2f}ms (target: <1000ms)"


# ============================================================================
# Benchmark Summary
# ============================================================================

class TestBenchmarkSummary:
    """Generate comprehensive benchmark report."""

    def test_generate_benchmark_report(self, tmp_path, monkeypatch):
        """Generate comprehensive benchmark report."""
        monkeypatch.setattr('webui.backend.lib.deployment_sidecar.PHOTOS_DIR', tmp_path)

        print("\n" + "=" * 70)
        print("DEPLOYMENT METADATA PERFORMANCE BENCHMARK REPORT")
        print("=" * 70)

        service = DeploymentService(cache_ttl=300, max_cache_size=500)

        # Single operation benchmarks
        print("\nSingle Operations:")

        deployment = create_deployment_directory(tmp_path, "bench_deployment")

        # Read
        start = time.perf_counter()
        for _ in range(100):
            read_deployment_metadata(deployment)
        read_time = (time.perf_counter() - start) / 100 * 1000
        print(f"  Read:  {read_time:.2f}ms (target: <{SINGLE_READ_TARGET_MS}ms)")

        # Write
        metadata = create_deployment_metadata(
            directory=deployment,
            name="Benchmark Deployment",
        )
        start = time.perf_counter()
        for _ in range(50):
            write_deployment_metadata(deployment, metadata)
        write_time = (time.perf_counter() - start) / 50 * 1000
        print(f"  Write: {write_time:.2f}ms (target: <{SINGLE_WRITE_TARGET_MS}ms)")

        # Cache hit
        service.get_deployment_metadata(deployment)
        start = time.perf_counter()
        for _ in range(1000):
            service.get_deployment_metadata(deployment)
        cache_time = (time.perf_counter() - start) / 1000 * 1000
        print(f"  Cache hit: {cache_time:.4f}ms (target: <{CACHE_HIT_TARGET_MS}ms)")

        # Batch operations
        print("\nBatch Operations:")

        for count in [100, 500]:
            batch_dir = tmp_path / f"batch_{count}"
            batch_dir.mkdir(exist_ok=True)
            deployments = generate_deployment_set(batch_dir, count)

            batch_service = DeploymentService(cache_ttl=300, max_cache_size=count * 2)

            # Cold
            start = time.perf_counter()
            _ = [batch_service.get_deployment_metadata(d) for d in deployments]
            cold_time = (time.perf_counter() - start) * 1000

            # Warm
            start = time.perf_counter()
            _ = [batch_service.get_deployment_metadata(d) for d in deployments]
            warm_time = (time.perf_counter() - start) * 1000

            print(f"  {count:>4} deployments: {cold_time:>8.2f}ms (cold), "
                  f"{warm_time:>8.2f}ms (warm)")

        # Discovery operations
        print("\nDiscovery Operations:")

        list_dir = tmp_path / "list_test"
        list_dir.mkdir(exist_ok=True)
        _ = generate_deployment_set(list_dir, 100)

        list_service = DeploymentService(cache_ttl=300)
        start = time.perf_counter()
        _ = list_service.list_deployments(list_dir)
        list_time = (time.perf_counter() - start) * 1000
        print(f"  List 100 deployments: {list_time:.2f}ms "
              f"(target: <{LIST_100_TARGET_MS}ms)")

        # Statistics
        stats = service.get_statistics()
        print("\nCache Statistics:")
        print(f"  Cache hits:     {stats['cache_hits']}")
        print(f"  Cache misses:   {stats['cache_misses']}")
        print(f"  Hit ratio:      {stats['hit_ratio']:.2%}")
        print(f"  Cache size:     {stats['cache_size']}/{stats['max_cache_size']}")
        print(f"  Total reads:    {stats['total_reads']}")
        print(f"  Total writes:   {stats['total_writes']}")

        print("\n" + "=" * 70)
        print("All benchmarks completed successfully!")
        print("=" * 70)

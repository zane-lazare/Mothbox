"""
Integration tests for deployment metadata workflow.

Tests end-to-end functionality across library, service, and API layers.
Covers CRUD operations, format conversion, hierarchical discovery, batch operations,
concurrent access, and cache integration.

Run with: MOTHBOX_ENV=test pytest Tests/integration/test_deployment_workflow.py -v -s

These tests are marked as @pytest.mark.integration but NOT @pytest.mark.hardware
since they test multi-layer integration without requiring Pi hardware.
"""

import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest

# Mark all tests in this module as integration tests (but not hardware)
pytestmark = pytest.mark.integration

# Setup path
FIRMWARE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(FIRMWARE_DIR))
sys.path.insert(0, str(FIRMWARE_DIR / "webui" / "backend"))
os.environ.setdefault("MOTHBOX_ENV", "test")

from webui.backend.lib.deployment_schema import DeploymentMetadata, ValidationError
from webui.backend.lib.deployment_sidecar import (
    create_deployment_metadata,
    delete_deployment_metadata,
    deployment_has_sidecar,
    find_deployment_sidecar,
    read_deployment_metadata,
    update_deployment_metadata,
    write_deployment_metadata,
    YAML_AVAILABLE,
)
from webui.backend.services.deployment_service import DeploymentService


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_photos_dir(tmp_path, monkeypatch):
    """Create temp photos directory structure with subdirectories and sample photos."""
    photos = tmp_path / "photos"
    photos.mkdir()

    # Create subdirectories with sample photos
    for name in ["forest_2024", "meadow_2024", "river_2024"]:
        subdir = photos / name
        subdir.mkdir()
        # Create sample photos
        for i in range(3):
            (subdir / f"photo_{i}.jpg").touch()

    # Patch PHOTOS_DIR to use temp directory
    import mothbox_paths
    monkeypatch.setattr(mothbox_paths, 'PHOTOS_DIR', photos)

    # Also patch in deployment_sidecar module
    import webui.backend.lib.deployment_sidecar as ds
    monkeypatch.setattr(ds, 'PHOTOS_DIR', photos)

    return photos


@pytest.fixture
def deployment_service():
    """Fresh DeploymentService for each test."""
    return DeploymentService(cache_ttl=300, max_cache_size=100)


# ============================================================================
# Test Full CRUD Workflow
# ============================================================================

class TestFullCRUDWorkflow:
    """Test complete Create-Read-Update-Delete lifecycle."""

    def test_create_read_update_delete_workflow(self, temp_photos_dir, deployment_service):
        """Full lifecycle test: create -> read -> update -> delete."""
        directory = temp_photos_dir / "forest_2024"

        # 1. CREATE - Create new deployment metadata
        metadata = create_deployment_metadata(
            directory=directory,
            name="Forest Survey 2024",
            latitude=35.9606,
            longitude=-83.9207,
            location_name="Oak Ridge, TN, USA",
            start_date="2024-06-01",
        )

        # Write to disk via service
        success = deployment_service.set_deployment_metadata(directory, metadata)
        assert success is True, "Should successfully write metadata"

        # Verify file exists
        sidecar_path = directory / "deployment.json"
        assert sidecar_path.exists(), "Sidecar file should exist"

        # 2. READ - Read back metadata
        read_metadata = deployment_service.get_deployment_metadata(directory)
        assert read_metadata is not None, "Should read metadata"
        assert read_metadata.deployment_name == "Forest Survey 2024"
        assert read_metadata.latitude == 35.9606
        assert read_metadata.longitude == -83.9207
        assert read_metadata.location_name == "Oak Ridge, TN, USA"
        assert read_metadata.start_date == "2024-06-01"

        # 3. UPDATE - Partial update
        updated_metadata = deployment_service.update_deployment_metadata(
            directory,
            {"end_date": "2024-08-31", "location_name": "Updated Location"}
        )
        assert updated_metadata is not None, "Should update metadata"
        assert updated_metadata.end_date == "2024-08-31"
        assert updated_metadata.location_name == "Updated Location"
        # Original fields should be preserved
        assert updated_metadata.deployment_name == "Forest Survey 2024"
        assert updated_metadata.latitude == 35.9606

        # 4. DELETE - Delete metadata
        delete_success = deployment_service.delete_deployment_metadata(directory)
        assert delete_success is True, "Should successfully delete metadata"

        # Verify file is gone
        assert not sidecar_path.exists(), "Sidecar file should be deleted"

        # Verify cache is invalidated
        final_read = deployment_service.get_deployment_metadata(directory)
        assert final_read is None, "Should return None after deletion"

    def test_create_with_all_fields(self, temp_photos_dir, deployment_service):
        """Create deployment with all optional fields populated."""
        directory = temp_photos_dir / "meadow_2024"

        metadata = create_deployment_metadata(
            directory=directory,
            name="Meadow Survey 2024",
            latitude=36.1234,
            longitude=-84.5678,
            altitude=450.5,
            location_name="Great Smoky Mountains, TN, USA",
            start_date="2024-05-01",
            end_date="2024-09-30",
            environmental={"temperature": 22.5, "humidity": 65, "weather": "clear"},
            mothbox_id="mothbox-meadow-001",
            firmware_version="5.2.1",
            custom={"researcher": "Dr. Jane Smith", "project_id": "NSF-12345"},
            modified_by="user123",
        )

        # Write via service
        success = deployment_service.set_deployment_metadata(directory, metadata)
        assert success is True

        # Read back and verify all fields
        read_metadata = deployment_service.get_deployment_metadata(directory)
        assert read_metadata is not None
        assert read_metadata.deployment_name == "Meadow Survey 2024"
        assert read_metadata.latitude == 36.1234
        assert read_metadata.longitude == -84.5678
        assert read_metadata.altitude == 450.5
        assert read_metadata.location_name == "Great Smoky Mountains, TN, USA"
        assert read_metadata.start_date == "2024-05-01"
        assert read_metadata.end_date == "2024-09-30"
        assert read_metadata.environmental == {"temperature": 22.5, "humidity": 65, "weather": "clear"}
        assert read_metadata.mothbox_id == "mothbox-meadow-001"
        assert read_metadata.firmware_version == "5.2.1"
        assert read_metadata.custom == {"researcher": "Dr. Jane Smith", "project_id": "NSF-12345"}
        assert read_metadata.modified_by == "user123"
        assert read_metadata.version == "1.0"
        assert read_metadata.created_at is not None
        assert read_metadata.modified_at is not None

    def test_update_preserves_unmodified_fields(self, temp_photos_dir, deployment_service):
        """Update should only modify specified fields, preserving all others."""
        directory = temp_photos_dir / "river_2024"

        # Create with multiple fields
        metadata = create_deployment_metadata(
            directory=directory,
            name="River Survey 2024",
            latitude=35.5,
            longitude=-83.5,
            location_name="River Valley",
            start_date="2024-07-01",
            environmental={"temperature": 20.0},
            mothbox_id="mothbox-river-001",
            custom={"site_code": "RV-001"},
        )
        deployment_service.set_deployment_metadata(directory, metadata)

        # Update only end_date
        updated = deployment_service.update_deployment_metadata(
            directory,
            {"end_date": "2024-08-15"}
        )

        # Verify only end_date changed
        assert updated.end_date == "2024-08-15"
        # All other fields should be preserved
        assert updated.deployment_name == "River Survey 2024"
        assert updated.latitude == 35.5
        assert updated.longitude == -83.5
        assert updated.location_name == "River Valley"
        assert updated.start_date == "2024-07-01"
        assert updated.environmental == {"temperature": 20.0}
        assert updated.mothbox_id == "mothbox-river-001"
        assert updated.custom == {"site_code": "RV-001"}


# ============================================================================
# Test Format Support
# ============================================================================

class TestFormatSupport:
    """Test JSON and YAML format support."""

    @pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
    def test_json_to_yaml_conversion(self, temp_photos_dir, deployment_service):
        """Create JSON deployment, read it, write as YAML, verify equivalence."""
        directory = temp_photos_dir / "forest_2024"

        # Create and write as JSON
        metadata_json = create_deployment_metadata(
            directory=directory,
            name="Forest Survey",
            latitude=35.9606,
            longitude=-83.9207,
        )
        deployment_service.set_deployment_metadata(directory, metadata_json, format="json")

        # Read back
        read_json = deployment_service.get_deployment_metadata(directory)

        # Write as YAML (delete JSON first to avoid confusion)
        json_path = directory / "deployment.json"
        json_path.unlink()
        deployment_service.invalidate_cache(directory)

        deployment_service.set_deployment_metadata(directory, read_json, format="yaml")

        # Read YAML
        read_yaml = deployment_service.get_deployment_metadata(directory)

        # Verify data is equivalent
        assert read_yaml is not None
        assert read_yaml.deployment_name == metadata_json.deployment_name
        assert read_yaml.latitude == metadata_json.latitude
        assert read_yaml.longitude == metadata_json.longitude

    @pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
    def test_yaml_to_json_conversion(self, temp_photos_dir, deployment_service):
        """Create YAML deployment, read it, write as JSON, verify equivalence."""
        directory = temp_photos_dir / "meadow_2024"

        # Create and write as YAML
        metadata_yaml = create_deployment_metadata(
            directory=directory,
            name="Meadow Survey",
            latitude=36.1234,
            longitude=-84.5678,
        )
        deployment_service.set_deployment_metadata(directory, metadata_yaml, format="yaml")

        # Read back
        read_yaml = deployment_service.get_deployment_metadata(directory)

        # Write as JSON (delete YAML first)
        yaml_path = directory / "deployment.yaml"
        yaml_path.unlink()
        deployment_service.invalidate_cache(directory)

        deployment_service.set_deployment_metadata(directory, read_yaml, format="json")

        # Read JSON
        read_json = deployment_service.get_deployment_metadata(directory)

        # Verify data is equivalent
        assert read_json is not None
        assert read_json.deployment_name == metadata_yaml.deployment_name
        assert read_json.latitude == metadata_yaml.latitude
        assert read_json.longitude == metadata_yaml.longitude

    def test_both_formats_produce_same_data(self, temp_photos_dir):
        """JSON and YAML should produce identical data structures when read."""
        if not YAML_AVAILABLE:
            pytest.skip("PyYAML not installed")

        dir_json = temp_photos_dir / "test_json"
        dir_yaml = temp_photos_dir / "test_yaml"
        dir_json.mkdir()
        dir_yaml.mkdir()

        # Create identical metadata
        test_data = {
            "name": "Test Survey",
            "latitude": 35.5,
            "longitude": -83.5,
            "location_name": "Test Location",
            "start_date": "2024-01-01",
            "environmental": {"temp": 20.5},
            "custom": {"key": "value"},
        }

        # Write as JSON
        metadata_json = create_deployment_metadata(directory=dir_json, **test_data)
        write_deployment_metadata(dir_json, metadata_json, format="json")

        # Write as YAML
        metadata_yaml = create_deployment_metadata(directory=dir_yaml, **test_data)
        write_deployment_metadata(dir_yaml, metadata_yaml, format="yaml")

        # Read both
        read_json = read_deployment_metadata(dir_json)
        read_yaml = read_deployment_metadata(dir_yaml)

        # Verify identical (ignoring timestamps which may differ slightly)
        assert read_json.deployment_name == read_yaml.deployment_name
        assert read_json.latitude == read_yaml.latitude
        assert read_json.longitude == read_yaml.longitude
        assert read_json.location_name == read_yaml.location_name
        assert read_json.start_date == read_yaml.start_date
        assert read_json.environmental == read_yaml.environmental
        assert read_json.custom == read_yaml.custom


# ============================================================================
# Test Hierarchical Discovery
# ============================================================================

class TestHierarchicalDiscovery:
    """Test hierarchical directory discovery for deployment metadata."""

    def test_auto_discover_deployment_for_photos(self, temp_photos_dir, deployment_service):
        """Photos should automatically find deployment metadata in parent directory."""
        directory = temp_photos_dir / "forest_2024"
        photo_path = directory / "photo_0.jpg"

        # Create deployment metadata
        metadata = create_deployment_metadata(
            directory=directory,
            name="Forest Survey",
            latitude=35.9606,
            longitude=-83.9207,
        )
        deployment_service.set_deployment_metadata(directory, metadata)

        # Find deployment for photo
        found_metadata = deployment_service.find_deployment_for_photo(photo_path)

        assert found_metadata is not None, "Should find deployment for photo"
        assert found_metadata.deployment_name == "Forest Survey"
        assert found_metadata.latitude == 35.9606

    def test_nested_directories_find_parent_deployment(self, temp_photos_dir, deployment_service):
        """Nested subdirectories should find deployment metadata by walking up tree."""
        # Create nested structure
        root_dir = temp_photos_dir / "forest_2024"
        nested_dir = root_dir / "week1" / "day1"
        nested_dir.mkdir(parents=True)
        photo_path = nested_dir / "photo.jpg"
        photo_path.touch()

        # Create deployment metadata at root level
        metadata = create_deployment_metadata(
            directory=root_dir,
            name="Forest Survey",
            latitude=35.9606,
            longitude=-83.9207,
        )
        deployment_service.set_deployment_metadata(root_dir, metadata)

        # Find deployment for deeply nested photo
        found_metadata = deployment_service.find_deployment_for_photo(photo_path)

        assert found_metadata is not None, "Should find deployment by walking up tree"
        assert found_metadata.deployment_name == "Forest Survey"

        # Verify sidecar was found at correct level
        sidecar_path = find_deployment_sidecar(photo_path)
        assert sidecar_path is not None
        assert sidecar_path.parent == root_dir, "Sidecar should be at root level"

    def test_subdirectory_deployment_overrides_parent(self, temp_photos_dir, deployment_service):
        """Subdirectory deployment should take precedence over parent deployment."""
        # Create parent deployment
        parent_dir = temp_photos_dir / "forest_2024"
        parent_metadata = create_deployment_metadata(
            directory=parent_dir,
            name="Parent Survey",
            latitude=35.0,
            longitude=-83.0,
        )
        deployment_service.set_deployment_metadata(parent_dir, parent_metadata)

        # Create subdirectory deployment
        subdir = parent_dir / "special_area"
        subdir.mkdir()
        subdir_photo = subdir / "photo.jpg"
        subdir_photo.touch()

        subdir_metadata = create_deployment_metadata(
            directory=subdir,
            name="Subdirectory Survey",
            latitude=36.0,
            longitude=-84.0,
        )
        deployment_service.set_deployment_metadata(subdir, subdir_metadata)

        # Photo in parent should find parent deployment
        parent_photo = parent_dir / "photo_0.jpg"
        found_parent = deployment_service.find_deployment_for_photo(parent_photo)
        assert found_parent.deployment_name == "Parent Survey"

        # Photo in subdirectory should find subdirectory deployment (not parent)
        found_subdir = deployment_service.find_deployment_for_photo(subdir_photo)
        assert found_subdir.deployment_name == "Subdirectory Survey"
        assert found_subdir.latitude == 36.0  # Verify it's the subdir metadata


# ============================================================================
# Test Batch Workflow
# ============================================================================

class TestBatchWorkflow:
    """Test batch operations on multiple deployments."""

    def test_batch_create_deployments_multiple_directories(self, temp_photos_dir, deployment_service):
        """Create deployments for multiple directories in batch."""
        directories = [
            temp_photos_dir / "forest_2024",
            temp_photos_dir / "meadow_2024",
            temp_photos_dir / "river_2024",
        ]

        # Create metadata for each directory
        for i, directory in enumerate(directories):
            metadata = create_deployment_metadata(
                directory=directory,
                name=f"Survey {directory.name}",
                latitude=35.0 + i,
                longitude=-83.0 - i,
            )
            deployment_service.set_deployment_metadata(directory, metadata)

        # Verify all were created
        for i, directory in enumerate(directories):
            read_metadata = deployment_service.get_deployment_metadata(directory)
            assert read_metadata is not None
            assert read_metadata.deployment_name == f"Survey {directory.name}"
            assert read_metadata.latitude == 35.0 + i

    def test_batch_update_all_deployments(self, temp_photos_dir, deployment_service):
        """Update multiple deployments using batch_update_deployments."""
        # Create initial deployments
        directories = [
            temp_photos_dir / "forest_2024",
            temp_photos_dir / "meadow_2024",
            temp_photos_dir / "river_2024",
        ]

        for directory in directories:
            metadata = create_deployment_metadata(
                directory=directory,
                name=f"Survey {directory.name}",
                start_date="2024-06-01",
            )
            deployment_service.set_deployment_metadata(directory, metadata)

        # Batch update all deployments
        updates = [
            (directories[0], {"end_date": "2024-08-31", "modified_by": "user1"}),
            (directories[1], {"end_date": "2024-09-15", "modified_by": "user2"}),
            (directories[2], {"end_date": "2024-09-30", "modified_by": "user3"}),
        ]

        result = deployment_service.batch_update_deployments(updates)

        # Verify batch results
        assert result["total"] == 3
        assert result["successful"] == 3
        assert result["failed_count"] == 0
        assert len(result["success"]) == 3
        assert len(result["failed"]) == 0

        # Verify updates were applied
        for i, directory in enumerate(directories):
            read_metadata = deployment_service.get_deployment_metadata(directory)
            assert read_metadata.end_date == ["2024-08-31", "2024-09-15", "2024-09-30"][i]
            assert read_metadata.modified_by == [f"user{j+1}" for j in range(3)][i]

    def test_generate_sidecars_for_subdirectories(self, temp_photos_dir, deployment_service):
        """Generate deployment sidecars for all subdirectories using template."""
        # Create some additional subdirectories
        base_dir = temp_photos_dir / "surveys_2024"
        base_dir.mkdir()

        subdirs = ["site_a", "site_b", "site_c"]
        for subdir_name in subdirs:
            subdir = base_dir / subdir_name
            subdir.mkdir()
            # Create sample photos
            for i in range(2):
                (subdir / f"photo_{i}.jpg").touch()

        # Generate sidecars using template
        template = {
            "location_name": "Survey Region",
            "latitude": 35.5,
            "longitude": -83.5,
            "start_date": "2024-06-01",
            "mothbox_id": "mothbox-survey-001",
        }

        generated_count = deployment_service.generate_sidecars_for_directory(
            base_dir,
            template
        )

        # Verify sidecars were generated
        assert generated_count == 3, f"Should generate 3 sidecars, got {generated_count}"

        # Verify each subdirectory has deployment metadata
        for subdir_name in subdirs:
            subdir = base_dir / subdir_name
            assert deployment_has_sidecar(subdir), f"{subdir_name} should have sidecar"

            metadata = deployment_service.get_deployment_metadata(subdir)
            assert metadata is not None
            # Deployment name should be subdirectory name (since not in template)
            assert metadata.deployment_name == subdir_name
            # Template fields should be applied
            assert metadata.location_name == "Survey Region"
            assert metadata.latitude == 35.5
            assert metadata.longitude == -83.5
            assert metadata.start_date == "2024-06-01"
            assert metadata.mothbox_id == "mothbox-survey-001"


# ============================================================================
# Test Concurrent Access
# ============================================================================

class TestConcurrentAccess:
    """Test thread-safe concurrent operations."""

    def test_concurrent_reads_safe(self, temp_photos_dir, deployment_service):
        """Multiple concurrent reads should be safe and consistent."""
        directory = temp_photos_dir / "forest_2024"

        # Create deployment
        metadata = create_deployment_metadata(
            directory=directory,
            name="Forest Survey",
            latitude=35.9606,
            longitude=-83.9207,
        )
        deployment_service.set_deployment_metadata(directory, metadata)

        # Perform 50 concurrent reads
        read_count = 50
        read_results = []
        errors = []
        lock = threading.Lock()

        def reader():
            """Read metadata."""
            try:
                result = deployment_service.get_deployment_metadata(directory)
                with lock:
                    read_results.append(result)
            except Exception as e:
                with lock:
                    errors.append(str(e))

        # Execute concurrent reads
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(reader) for _ in range(read_count)]
            for future in as_completed(futures, timeout=5.0):
                future.result()

        # Verify no errors
        assert len(errors) == 0, f"Should have no errors: {errors}"

        # Verify all reads succeeded
        assert len(read_results) == read_count

        # Verify all results are consistent
        for result in read_results:
            assert result is not None
            assert result.deployment_name == "Forest Survey"
            assert result.latitude == 35.9606

    def test_concurrent_writes_atomic(self, temp_photos_dir, deployment_service):
        """Concurrent writes to same deployment should be atomic (no corruption)."""
        directory = temp_photos_dir / "forest_2024"

        # Create initial deployment
        metadata = create_deployment_metadata(
            directory=directory,
            name="Forest Survey",
            latitude=35.9606,
            longitude=-83.9207,
        )
        deployment_service.set_deployment_metadata(directory, metadata)

        # Track results
        update_results = []
        errors = []
        lock = threading.Lock()

        def update_field(field_value):
            """Update a specific field."""
            try:
                result = deployment_service.update_deployment_metadata(
                    directory,
                    {"modified_by": f"user_{field_value}"}
                )
                with lock:
                    update_results.append(result is not None)
            except Exception as e:
                with lock:
                    errors.append(str(e))

        # Perform 10 concurrent updates
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(update_field, i) for i in range(10)]
            for future in as_completed(futures, timeout=5.0):
                future.result()

        # Verify no errors
        assert len(errors) == 0, f"Should have no errors: {errors}"

        # Verify all updates succeeded
        assert all(update_results), "All updates should succeed"

        # Final metadata should be valid (not corrupted)
        time.sleep(0.1)  # Small delay for any pending operations
        final = deployment_service.get_deployment_metadata(directory)
        assert final is not None
        assert final.deployment_name == "Forest Survey"  # Original field preserved
        assert final.latitude == 35.9606  # Original field preserved
        assert final.modified_by.startswith("user_")  # Modified field updated

    def test_concurrent_mixed_operations(self, temp_photos_dir, deployment_service):
        """Mix of concurrent reads, writes, and updates should not deadlock."""
        directory = temp_photos_dir / "meadow_2024"

        # Create initial deployment
        metadata = create_deployment_metadata(
            directory=directory,
            name="Meadow Survey",
            latitude=36.0,
            longitude=-84.0,
        )
        deployment_service.set_deployment_metadata(directory, metadata)

        operation_results = {"reads": 0, "updates": 0, "errors": 0}
        lock = threading.Lock()

        def mixed_operations(thread_id):
            """Perform mixed read/update operations."""
            try:
                # Read
                result = deployment_service.get_deployment_metadata(directory)
                if result is not None:
                    with lock:
                        operation_results["reads"] += 1

                # Update
                updated = deployment_service.update_deployment_metadata(
                    directory,
                    {"modified_by": f"thread_{thread_id}"}
                )
                if updated is not None:
                    with lock:
                        operation_results["updates"] += 1

                # Read again
                result = deployment_service.get_deployment_metadata(directory)
                if result is not None:
                    with lock:
                        operation_results["reads"] += 1

            except Exception as e:
                with lock:
                    operation_results["errors"] += 1

        # Run 10 threads doing mixed operations
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(mixed_operations, i) for i in range(10)]
            for future in as_completed(futures, timeout=5.0):
                future.result()

        elapsed = time.time() - start_time

        # Verify minimal errors
        assert operation_results["errors"] < 3, f"Too many errors: {operation_results['errors']}"

        # Verify operations completed
        assert operation_results["reads"] >= 10, "Should have many reads"
        assert operation_results["updates"] >= 5, "Should have some updates"

        # Should complete quickly (no deadlock)
        assert elapsed < 5.0, f"Operations took too long: {elapsed}s"

        # Final metadata should be valid
        time.sleep(0.1)
        final = deployment_service.get_deployment_metadata(directory)
        assert final is not None
        assert final.deployment_name == "Meadow Survey"


# ============================================================================
# Test Cache Integration
# ============================================================================

class TestCacheIntegration:
    """Test cache behavior in service layer."""

    def test_cache_hit_on_repeated_reads(self, temp_photos_dir, deployment_service):
        """Repeated reads should hit cache, improving performance."""
        directory = temp_photos_dir / "forest_2024"

        # Create deployment
        metadata = create_deployment_metadata(
            directory=directory,
            name="Forest Survey",
            latitude=35.9606,
            longitude=-83.9207,
        )
        deployment_service.set_deployment_metadata(directory, metadata)

        # Get initial stats
        stats_before = deployment_service.get_statistics()
        initial_hits = stats_before["cache_hits"]

        # Perform multiple reads
        for _ in range(10):
            result = deployment_service.get_deployment_metadata(directory)
            assert result is not None

        # Get stats after reads
        stats_after = deployment_service.get_statistics()

        # Most reads should be cache hits (at least 8 out of 10)
        cache_hits_gained = stats_after["cache_hits"] - initial_hits
        assert cache_hits_gained >= 8, \
            f"Expected at least 8 cache hits, got {cache_hits_gained}"

        # Hit ratio should be high
        assert stats_after["hit_ratio"] > 0.5, \
            f"Cache hit ratio should be > 0.5, got {stats_after['hit_ratio']}"

    def test_cache_invalidation_on_update(self, temp_photos_dir, deployment_service):
        """Update should invalidate cache, forcing fresh read from disk."""
        directory = temp_photos_dir / "meadow_2024"

        # Create deployment
        metadata = create_deployment_metadata(
            directory=directory,
            name="Meadow Survey",
            latitude=36.0,
            longitude=-84.0,
        )
        deployment_service.set_deployment_metadata(directory, metadata)

        # Read to populate cache
        read1 = deployment_service.get_deployment_metadata(directory)
        assert read1.deployment_name == "Meadow Survey"

        # Update deployment
        updated = deployment_service.update_deployment_metadata(
            directory,
            {"end_date": "2024-09-15"}
        )
        assert updated.end_date == "2024-09-15"

        # Read again - should get updated value (cache was invalidated/updated)
        read2 = deployment_service.get_deployment_metadata(directory)
        assert read2.end_date == "2024-09-15"

        # Verify cache contains updated value
        stats = deployment_service.get_statistics()
        assert stats["cache_size"] >= 1, "Cache should contain at least 1 entry"

    def test_cache_statistics_tracking(self, temp_photos_dir, deployment_service):
        """Cache statistics should accurately track operations."""
        directory1 = temp_photos_dir / "forest_2024"
        directory2 = temp_photos_dir / "meadow_2024"

        # Get initial stats
        stats_initial = deployment_service.get_statistics()
        initial_writes = stats_initial["total_writes"]
        initial_reads = stats_initial["total_reads"]

        # Perform operations
        # 2 writes
        metadata1 = create_deployment_metadata(directory=directory1, name="Forest")
        metadata2 = create_deployment_metadata(directory=directory2, name="Meadow")
        deployment_service.set_deployment_metadata(directory1, metadata1)
        deployment_service.set_deployment_metadata(directory2, metadata2)

        # 4 reads (first read is miss, subsequent are hits for same directory)
        deployment_service.get_deployment_metadata(directory1)  # miss
        deployment_service.get_deployment_metadata(directory1)  # hit
        deployment_service.get_deployment_metadata(directory2)  # miss
        deployment_service.get_deployment_metadata(directory2)  # hit

        # Get final stats
        stats_final = deployment_service.get_statistics()

        # Verify write count increased by 2
        writes_gained = stats_final["total_writes"] - initial_writes
        assert writes_gained == 2, f"Expected 2 writes, got {writes_gained}"

        # Verify read count increased by 4
        reads_gained = stats_final["total_reads"] - initial_reads
        assert reads_gained == 4, f"Expected 4 reads, got {reads_gained}"

        # Verify cache has 2 entries
        assert stats_final["cache_size"] == 2, \
            f"Expected cache size 2, got {stats_final['cache_size']}"

    def test_manual_cache_invalidation(self, temp_photos_dir, deployment_service):
        """Manual cache invalidation should force re-read from disk."""
        directory = temp_photos_dir / "river_2024"

        # Create deployment
        metadata = create_deployment_metadata(
            directory=directory,
            name="River Survey",
            latitude=35.5,
            longitude=-83.5,
        )
        deployment_service.set_deployment_metadata(directory, metadata)

        # Read to populate cache
        read1 = deployment_service.get_deployment_metadata(directory)
        assert read1 is not None

        # Manually modify file on disk (bypassing service)
        sidecar_path = directory / "deployment.json"
        with open(sidecar_path, 'r') as f:
            data = json.load(f)
        data['end_date'] = "2024-12-31"
        with open(sidecar_path, 'w') as f:
            json.dump(data, f, indent=2)

        # Read again - should get cached value (doesn't see disk change)
        read2 = deployment_service.get_deployment_metadata(directory)
        assert read2.end_date is None  # Still cached old value

        # Invalidate cache
        deployment_service.invalidate_cache(directory)

        # Read again - should get updated value from disk
        read3 = deployment_service.get_deployment_metadata(directory)
        assert read3.end_date == "2024-12-31"  # Fresh read from disk

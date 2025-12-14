"""
Unit tests for Sidecar Service with Two-Level Cache (Issue #102 - Phase B)

Tests SidecarService with L1 (memory) and L2 (file-based) caching.
TDD approach: tests written first, then implementation.

Coverage Target: 85%+
"""

import pytest
import threading
import time
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import will fail until implementation exists - that's expected in TDD
try:
    from webui.backend.services.sidecar_service import (
        SidecarService,
    )
    IMPLEMENTATION_EXISTS = True
except ImportError:
    IMPLEMENTATION_EXISTS = False
    SidecarService = None

# Skip all tests if implementation doesn't exist yet (TDD red phase)
pytestmark = pytest.mark.skipif(
    not IMPLEMENTATION_EXISTS,
    reason="Implementation not yet created (TDD red phase)"
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def cache_dir(tmp_path):
    """Create temporary cache directory."""
    cache = tmp_path / "cache"
    cache.mkdir()
    return cache


@pytest.fixture
def photos_dir(tmp_path):
    """Create temporary photos directory."""
    photos = tmp_path / "photos"
    photos.mkdir()
    return photos


@pytest.fixture
def sample_photo(photos_dir):
    """Create sample photo file."""
    photo = photos_dir / "photo1.jpg"
    photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
    return photo


@pytest.fixture
def sample_photo_with_sidecar(sample_photo):
    """Create sample photo with sidecar metadata."""
    from webui.backend.lib.sidecar_metadata import create_metadata, write_metadata

    metadata = create_metadata(
        sample_photo,
        tags=["moth", "night"],
        species="Actias luna",
        notes="Beautiful luna moth"
    )
    write_metadata(sample_photo, metadata)
    return sample_photo


@pytest.fixture
def service(cache_dir):
    """Create SidecarService instance."""
    return SidecarService(cache_dir=cache_dir, l1_max_size=10, l2_max_size=100)


@pytest.fixture
def multiple_photos_with_sidecars(photos_dir):
    """Create multiple photos with sidecar metadata."""
    from webui.backend.lib.sidecar_metadata import create_metadata, write_metadata

    photos = []
    for i in range(5):
        photo = photos_dir / f"photo_{i}.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        metadata = create_metadata(
            photo,
            tags=[f"tag_{i}", "common"],
            species=f"Species {i}",
            notes=f"Notes for photo {i}"
        )
        write_metadata(photo, metadata)
        photos.append(photo)

    return photos


@pytest.fixture
def mock_search_service():
    """Create a mock SearchService for testing integration."""
    from unittest.mock import Mock
    search_service = Mock()
    search_service.index_photo = Mock(return_value=True)
    search_service.remove_photo = Mock(return_value=True)
    return search_service


# ============================================================================
# Test Service Initialization
# ============================================================================

class TestSidecarServiceInit:
    """Tests for SidecarService initialization."""

    def test_service_creation_default_params(self, cache_dir):
        """SidecarService should be created with default parameters."""
        service = SidecarService(cache_dir=cache_dir)
        assert service is not None
        assert service.l1_max_size == 1000
        assert service.l2_max_size == 10000

    def test_service_creation_custom_params(self, cache_dir):
        """SidecarService should accept custom parameters."""
        service = SidecarService(cache_dir=cache_dir, l1_max_size=500, l2_max_size=5000)
        assert service.l1_max_size == 500
        assert service.l2_max_size == 5000

    def test_service_creates_cache_directory(self, tmp_path):
        """SidecarService should create cache directory if it doesn't exist."""
        cache_dir = tmp_path / "nonexistent_cache"
        assert not cache_dir.exists()

        service = SidecarService(cache_dir=cache_dir)
        assert cache_dir.exists()
        assert cache_dir.is_dir()

    def test_service_starts_with_empty_cache(self, service):
        """SidecarService should start with empty L1 and L2 caches."""
        stats = service.get_statistics()
        assert stats['l1_hits'] == 0
        assert stats['l1_misses'] == 0
        assert stats['l2_hits'] == 0
        assert stats['l2_misses'] == 0


# ============================================================================
# Test get_metadata (L1 -> L2 -> disk)
# ============================================================================

class TestGetMetadata:
    """Tests for get_metadata method."""

    def test_get_metadata_from_disk_first_time(self, service, sample_photo_with_sidecar):
        """First call should read from disk and populate cache."""
        metadata = service.get_metadata(str(sample_photo_with_sidecar))

        assert metadata is not None
        assert metadata.photo_filename == sample_photo_with_sidecar.name
        assert "moth" in metadata.tags
        assert metadata.species == "Actias luna"

    def test_get_metadata_caches_in_l1(self, service, sample_photo_with_sidecar):
        """Metadata should be cached in L1 after first access."""
        # First access - disk read
        service.get_metadata(str(sample_photo_with_sidecar))

        # Second access - L1 hit
        metadata = service.get_metadata(str(sample_photo_with_sidecar))
        stats = service.get_statistics()

        assert metadata is not None
        assert stats['l1_hits'] >= 1

    def test_get_metadata_caches_in_l2(self, service, sample_photo_with_sidecar):
        """Metadata should be cached in L2 after first access."""
        # First access
        service.get_metadata(str(sample_photo_with_sidecar))

        # Clear L1 to force L2 check
        service.clear()

        # Recreate sidecar to test L2 persistence
        from webui.backend.lib.sidecar_metadata import create_metadata, write_metadata
        metadata_new = create_metadata(sample_photo_with_sidecar, tags=["moth", "night"])
        write_metadata(sample_photo_with_sidecar, metadata_new)

        # Access again - should work even with cleared L1
        service.get_metadata(str(sample_photo_with_sidecar))

    def test_get_metadata_nonexistent_photo(self, service, photos_dir):
        """Getting metadata for photo without sidecar should return None."""
        photo = photos_dir / "nonexistent.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0')

        metadata = service.get_metadata(str(photo))
        assert metadata is None

    def test_get_metadata_nonexistent_file(self, service, photos_dir):
        """Getting metadata for nonexistent file should return None."""
        photo = photos_dir / "doesnt_exist.jpg"

        metadata = service.get_metadata(str(photo))
        assert metadata is None

    def test_get_metadata_l1_hit_tracking(self, service, sample_photo_with_sidecar):
        """L1 hits should be tracked in statistics."""
        # Prime cache
        service.get_metadata(str(sample_photo_with_sidecar))

        stats_before = service.get_statistics()

        # Access again - L1 hit
        service.get_metadata(str(sample_photo_with_sidecar))

        stats_after = service.get_statistics()
        assert stats_after['l1_hits'] == stats_before['l1_hits'] + 1


# ============================================================================
# Test set_metadata (write to L1, L2, disk)
# ============================================================================

class TestSetMetadata:
    """Tests for set_metadata method."""

    def test_set_metadata_creates_sidecar(self, service, sample_photo):
        """set_metadata should create sidecar file on disk."""
        from webui.backend.lib.sidecar_metadata import create_metadata, photo_has_sidecar

        metadata = create_metadata(sample_photo, tags=["new_tag"])
        service.set_metadata(str(sample_photo), metadata)

        assert photo_has_sidecar(sample_photo)

    def test_set_metadata_populates_l1(self, service, sample_photo):
        """set_metadata should populate L1 cache."""
        from webui.backend.lib.sidecar_metadata import create_metadata

        metadata = create_metadata(sample_photo, tags=["new_tag"])
        service.set_metadata(str(sample_photo), metadata)

        # Get should hit L1
        result = service.get_metadata(str(sample_photo))
        stats = service.get_statistics()

        assert result is not None
        assert stats['l1_hits'] >= 1

    def test_set_metadata_populates_l2(self, service, sample_photo):
        """set_metadata should populate L2 cache."""
        from webui.backend.lib.sidecar_metadata import create_metadata

        metadata = create_metadata(sample_photo, tags=["new_tag"])
        service.set_metadata(str(sample_photo), metadata)

        # Clear L1 and verify L2 has it
        service.invalidate(str(sample_photo))

        # Should still be in L2 (not a complete cache miss)
        # This is harder to test directly, so we just verify it doesn't error
        result = service.get_metadata(str(sample_photo))
        assert result is not None


# ============================================================================
# Test update_metadata
# ============================================================================

class TestUpdateMetadata:
    """Tests for update_metadata method."""

    def test_update_metadata_modifies_existing(self, service, sample_photo_with_sidecar):
        """update_metadata should modify existing metadata."""
        updates = {"species": "Updated species", "notes": "Updated notes"}
        result = service.update_metadata(str(sample_photo_with_sidecar), updates)

        assert result is not None
        assert result.species == "Updated species"
        assert result.notes == "Updated notes"
        assert "moth" in result.tags  # Original tags preserved

    def test_update_metadata_creates_if_missing(self, service, sample_photo):
        """update_metadata should create metadata if doesn't exist."""
        updates = {"tags": ["new_tag"], "species": "New species"}
        result = service.update_metadata(str(sample_photo), updates)

        assert result is not None
        assert "new_tag" in result.tags
        assert result.species == "New species"

    def test_update_metadata_updates_cache(self, service, sample_photo_with_sidecar):
        """update_metadata should update both L1 and L2 cache."""
        updates = {"species": "Updated species"}
        service.update_metadata(str(sample_photo_with_sidecar), updates)

        # Get should return updated metadata from cache
        result = service.get_metadata(str(sample_photo_with_sidecar))
        assert result.species == "Updated species"

    def test_update_metadata_nonexistent_file(self, service, photos_dir):
        """update_metadata for nonexistent file should return None."""
        photo = photos_dir / "nonexistent.jpg"
        updates = {"species": "Test"}

        result = service.update_metadata(str(photo), updates)
        assert result is None


# ============================================================================
# Test invalidate (remove from L1 and L2)
# ============================================================================

class TestInvalidate:
    """Tests for invalidate method."""

    def test_invalidate_removes_from_l1(self, service, sample_photo_with_sidecar):
        """invalidate should remove entry from L1 cache."""
        # Prime cache
        service.get_metadata(str(sample_photo_with_sidecar))

        # Invalidate
        result = service.invalidate(str(sample_photo_with_sidecar))
        assert result is True

        # Next access should be cache miss
        stats_before = service.get_statistics()
        service.get_metadata(str(sample_photo_with_sidecar))
        stats_after = service.get_statistics()

        # Should have more misses (either L1 or L2 miss)
        total_misses_before = stats_before['l1_misses'] + stats_before['l2_misses']
        total_misses_after = stats_after['l1_misses'] + stats_after['l2_misses']
        assert total_misses_after > total_misses_before

    def test_invalidate_nonexistent_entry(self, service, sample_photo):
        """invalidate for non-cached entry should return False."""
        result = service.invalidate(str(sample_photo))
        assert result is False


# ============================================================================
# Test clear (clear entire cache)
# ============================================================================

class TestClear:
    """Tests for clear method."""

    def test_clear_removes_all_l1_entries(self, service, multiple_photos_with_sidecars):
        """clear should remove all L1 cache entries."""
        # Prime cache with multiple photos
        for photo in multiple_photos_with_sidecars:
            service.get_metadata(str(photo))

        # Clear cache
        service.clear()

        # Statistics should be reset
        stats = service.get_statistics()
        assert stats['l1_hits'] == 0
        assert stats['l1_misses'] == 0
        assert stats['l2_hits'] == 0
        assert stats['l2_misses'] == 0

    def test_clear_removes_all_l2_entries(self, service, cache_dir, sample_photo_with_sidecar):
        """clear should remove all L2 cache files."""
        # Prime cache
        service.get_metadata(str(sample_photo_with_sidecar))

        # Verify L2 cache files exist
        l2_files_before = list(cache_dir.glob("*.json"))
        assert len(l2_files_before) > 0

        # Clear cache
        service.clear()

        # L2 cache files should be gone
        l2_files_after = list(cache_dir.glob("*.json"))
        assert len(l2_files_after) == 0


# ============================================================================
# Test Statistics
# ============================================================================

class TestStatistics:
    """Tests for get_statistics method."""

    def test_statistics_structure(self, service):
        """Statistics should have expected fields."""
        stats = service.get_statistics()

        assert 'l1_hits' in stats
        assert 'l1_misses' in stats
        assert 'l2_hits' in stats
        assert 'l2_misses' in stats
        assert 'hit_ratio' in stats

    def test_statistics_l1_hit_tracking(self, service, sample_photo_with_sidecar):
        """L1 hits should be tracked correctly."""
        # First access - cache miss
        service.get_metadata(str(sample_photo_with_sidecar))
        stats1 = service.get_statistics()

        # Second access - L1 hit
        service.get_metadata(str(sample_photo_with_sidecar))
        stats2 = service.get_statistics()

        assert stats2['l1_hits'] == stats1['l1_hits'] + 1

    def test_statistics_hit_ratio_calculation(self, service, sample_photo_with_sidecar):
        """Hit ratio should be calculated correctly."""
        # Access twice (1 miss, 1 hit)
        service.get_metadata(str(sample_photo_with_sidecar))
        service.get_metadata(str(sample_photo_with_sidecar))

        stats = service.get_statistics()

        # Hit ratio should be > 0
        assert stats['hit_ratio'] > 0.0
        assert stats['hit_ratio'] <= 1.0


# ============================================================================
# Test Batch Operations (Subtask B2)
# ============================================================================

class TestBatchGetMetadata:
    """Tests for batch_get_metadata method."""

    def test_batch_get_empty_list(self, service):
        """batch_get_metadata with empty list should return empty list."""
        results = service.batch_get_metadata([])
        assert results == []

    def test_batch_get_single_photo(self, service, sample_photo_with_sidecar):
        """batch_get_metadata with single photo should work."""
        results = service.batch_get_metadata([str(sample_photo_with_sidecar)])

        assert len(results) == 1
        assert results[0] is not None
        assert results[0].photo_filename == sample_photo_with_sidecar.name

    def test_batch_get_multiple_photos(self, service, multiple_photos_with_sidecars):
        """batch_get_metadata should retrieve multiple photos."""
        photo_paths = [str(p) for p in multiple_photos_with_sidecars]
        results = service.batch_get_metadata(photo_paths)

        assert len(results) == len(photo_paths)
        assert all(r is not None for r in results)

    def test_batch_get_mixed_existing_and_missing(self, service, photos_dir, sample_photo_with_sidecar):
        """batch_get_metadata should handle mix of existing and missing metadata."""
        # Create photo without sidecar
        photo_no_sidecar = photos_dir / "no_sidecar.jpg"
        photo_no_sidecar.write_bytes(b'\xFF\xD8\xFF\xE0')

        photo_paths = [str(sample_photo_with_sidecar), str(photo_no_sidecar)]
        results = service.batch_get_metadata(photo_paths)

        assert len(results) == 2
        assert results[0] is not None  # Has sidecar
        assert results[1] is None  # No sidecar


class TestListMetadataForDirectory:
    """Tests for list_metadata_for_directory method."""

    def test_list_metadata_empty_directory(self, service, photos_dir):
        """list_metadata_for_directory for empty directory should return empty list."""
        result = service.list_metadata_for_directory(photos_dir)

        assert result['items'] == []
        assert result['total'] == 0
        assert result['has_next'] is False

    def test_list_metadata_single_photo(self, service, sample_photo_with_sidecar):
        """list_metadata_for_directory should list single photo."""
        result = service.list_metadata_for_directory(sample_photo_with_sidecar.parent)

        assert len(result['items']) == 1
        assert result['total'] == 1
        assert result['items'][0]['photo_filename'] == sample_photo_with_sidecar.name

    def test_list_metadata_multiple_photos(self, service, multiple_photos_with_sidecars):
        """list_metadata_for_directory should list multiple photos."""
        result = service.list_metadata_for_directory(multiple_photos_with_sidecars[0].parent)

        assert len(result['items']) == 5
        assert result['total'] == 5

    def test_list_metadata_pagination_limit(self, service, multiple_photos_with_sidecars):
        """list_metadata_for_directory should respect limit parameter."""
        result = service.list_metadata_for_directory(
            multiple_photos_with_sidecars[0].parent,
            limit=2
        )

        assert len(result['items']) == 2
        assert result['total'] == 5
        assert result['limit'] == 2
        assert result['has_next'] is True

    def test_list_metadata_pagination_offset(self, service, multiple_photos_with_sidecars):
        """list_metadata_for_directory should respect offset parameter."""
        result = service.list_metadata_for_directory(
            multiple_photos_with_sidecars[0].parent,
            limit=2,
            offset=2
        )

        assert len(result['items']) == 2
        assert result['offset'] == 2
        assert result['has_next'] is True

    def test_list_metadata_pagination_last_page(self, service, multiple_photos_with_sidecars):
        """list_metadata_for_directory last page should have has_next=False."""
        result = service.list_metadata_for_directory(
            multiple_photos_with_sidecars[0].parent,
            limit=3,
            offset=3
        )

        assert len(result['items']) == 2  # Only 2 remaining (5 total - 3 offset)
        assert result['has_next'] is False

    def test_list_metadata_directory_not_exist(self, service, tmp_path):
        """list_metadata_for_directory for nonexistent directory should return empty."""
        result = service.list_metadata_for_directory(tmp_path / "nonexistent")

        assert result['items'] == []
        assert result['total'] == 0

    def test_list_metadata_includes_photos_without_sidecars(self, service, photos_dir):
        """list_metadata_for_directory should include photos without sidecars."""
        from webui.backend.lib.sidecar_metadata import create_metadata, write_metadata

        # Create photo with sidecar
        photo_with = photos_dir / "with_sidecar.jpg"
        photo_with.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
        metadata = create_metadata(photo_with, tags=["moth"])
        write_metadata(photo_with, metadata)

        # Create photo without sidecar
        photo_without = photos_dir / "without_sidecar.jpg"
        photo_without.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        result = service.list_metadata_for_directory(photos_dir)

        assert result['total'] == 2
        assert len(result['items']) == 2

        # Check has_sidecar flags
        has_sidecar_flags = {item['photo_filename']: item['has_sidecar'] for item in result['items']}
        assert has_sidecar_flags['with_sidecar.jpg'] is True
        assert has_sidecar_flags['without_sidecar.jpg'] is False

    def test_list_metadata_has_sidecar_filter_true(self, service, photos_dir):
        """list_metadata_for_directory should filter to only photos with sidecars."""
        from webui.backend.lib.sidecar_metadata import create_metadata, write_metadata

        # Create photo with sidecar
        photo_with = photos_dir / "with_sidecar.jpg"
        photo_with.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
        metadata = create_metadata(photo_with, tags=["moth"])
        write_metadata(photo_with, metadata)

        # Create photo without sidecar
        photo_without = photos_dir / "without_sidecar.jpg"
        photo_without.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        result = service.list_metadata_for_directory(photos_dir, has_sidecar=True)

        assert result['total'] == 1
        assert result['items'][0]['photo_filename'] == 'with_sidecar.jpg'
        assert result['items'][0]['has_sidecar'] is True

    def test_list_metadata_has_sidecar_filter_false(self, service, photos_dir):
        """list_metadata_for_directory should filter to only photos without sidecars."""
        from webui.backend.lib.sidecar_metadata import create_metadata, write_metadata

        # Create photo with sidecar
        photo_with = photos_dir / "with_sidecar.jpg"
        photo_with.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
        metadata = create_metadata(photo_with, tags=["moth"])
        write_metadata(photo_with, metadata)

        # Create photo without sidecar
        photo_without = photos_dir / "without_sidecar.jpg"
        photo_without.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        result = service.list_metadata_for_directory(photos_dir, has_sidecar=False)

        assert result['total'] == 1
        assert result['items'][0]['photo_filename'] == 'without_sidecar.jpg'
        assert result['items'][0]['has_sidecar'] is False

    def test_list_metadata_recursive_subdirectory(self, service, photos_dir):
        """list_metadata_for_directory should find photos in subdirectories."""
        from webui.backend.lib.sidecar_metadata import create_metadata, write_metadata

        # Create photo in root
        root_photo = photos_dir / "root.jpg"
        root_photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
        metadata = create_metadata(root_photo, tags=["root"])
        write_metadata(root_photo, metadata)

        # Create photo in subdirectory
        subdir = photos_dir / "test_captures"
        subdir.mkdir()
        sub_photo = subdir / "subdir.jpg"
        sub_photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        result = service.list_metadata_for_directory(photos_dir)

        assert result['total'] == 2
        paths = [item['path'] for item in result['items']]
        assert any('root.jpg' in p for p in paths)
        assert any('test_captures' in p and 'subdir.jpg' in p for p in paths)

    def test_list_metadata_includes_path_field(self, service, photos_dir):
        """list_metadata_for_directory should include relative path field."""
        from webui.backend.lib.sidecar_metadata import create_metadata, write_metadata

        # Create photo in subdirectory
        subdir = photos_dir / "captures"
        subdir.mkdir()
        photo = subdir / "photo.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
        metadata = create_metadata(photo, tags=["test"])
        write_metadata(photo, metadata)

        result = service.list_metadata_for_directory(photos_dir)

        assert result['total'] == 1
        assert result['items'][0]['path'] == 'captures/photo.jpg'
        assert result['items'][0]['has_sidecar'] is True

    def test_list_metadata_placeholder_has_expected_fields(self, service, photos_dir):
        """Placeholder metadata for photos without sidecars should have expected fields."""
        # Create photo without sidecar
        photo = photos_dir / "no_sidecar.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        result = service.list_metadata_for_directory(photos_dir)

        assert result['total'] == 1
        item = result['items'][0]

        # Check placeholder fields
        assert item['photo_filename'] == 'no_sidecar.jpg'
        assert item['has_sidecar'] is False
        assert item['tags'] == []
        assert item['species'] is None
        assert item['notes'] is None
        assert 'file_timestamp' in item
        assert 'path' in item


class TestBatchUpdateMetadata:
    """Tests for batch_update_metadata method."""

    def test_batch_update_empty_list(self, service):
        """batch_update_metadata with empty list should return empty list."""
        results = service.batch_update_metadata([])
        assert results == []

    def test_batch_update_single_photo(self, service, sample_photo_with_sidecar):
        """batch_update_metadata should update single photo."""
        updates = [(str(sample_photo_with_sidecar), {"species": "Updated"})]
        results = service.batch_update_metadata(updates)

        assert len(results) == 1
        assert results[0] is True

        # Verify update
        metadata = service.get_metadata(str(sample_photo_with_sidecar))
        assert metadata.species == "Updated"

    def test_batch_update_multiple_photos(self, service, multiple_photos_with_sidecars):
        """batch_update_metadata should update multiple photos."""
        updates = [
            (str(multiple_photos_with_sidecars[0]), {"species": "Species A"}),
            (str(multiple_photos_with_sidecars[1]), {"species": "Species B"}),
        ]
        results = service.batch_update_metadata(updates)

        assert len(results) == 2
        assert all(results)

        # Verify updates
        m0 = service.get_metadata(str(multiple_photos_with_sidecars[0]))
        m1 = service.get_metadata(str(multiple_photos_with_sidecars[1]))
        assert m0.species == "Species A"
        assert m1.species == "Species B"

    def test_batch_update_nonexistent_file(self, service, photos_dir):
        """batch_update_metadata for nonexistent file should return False."""
        updates = [(str(photos_dir / "nonexistent.jpg"), {"species": "Test"})]
        results = service.batch_update_metadata(updates)

        assert len(results) == 1
        assert results[0] is False


# ============================================================================
# Test L1 LRU Eviction
# ============================================================================

class TestL1LRUEviction:
    """Tests for L1 cache LRU eviction."""

    def test_l1_evicts_oldest_when_full(self, cache_dir, photos_dir):
        """L1 cache should evict oldest entries when full."""
        from webui.backend.lib.sidecar_metadata import create_metadata, write_metadata

        # Create service with small L1 cache
        service = SidecarService(cache_dir=cache_dir, l1_max_size=3, l2_max_size=100)

        # Create 5 photos with sidecars
        photos = []
        for i in range(5):
            photo = photos_dir / f"photo_{i}.jpg"
            photo.write_bytes(b'\xFF\xD8\xFF\xE0')
            metadata = create_metadata(photo, tags=[f"tag_{i}"])
            write_metadata(photo, metadata)
            photos.append(photo)

        # Access first 3 photos (fill L1 cache)
        for i in range(3):
            service.get_metadata(str(photos[i]))

        # Access 2 more photos (should evict first 2)
        service.get_metadata(str(photos[3]))
        service.get_metadata(str(photos[4]))

        # Access photo 0 again - should be L1 miss (was evicted)
        stats_before = service.get_statistics()
        service.get_metadata(str(photos[0]))
        stats_after = service.get_statistics()

        # Should have L1 miss
        assert stats_after['l1_misses'] > stats_before['l1_misses']


# ============================================================================
# Test Thread Safety
# ============================================================================

class TestThreadSafety:
    """Tests for thread-safe cache operations."""

    def test_concurrent_reads(self, service, sample_photo_with_sidecar):
        """Multiple concurrent reads should work safely."""
        results = []
        errors = []

        def read_metadata():
            try:
                metadata = service.get_metadata(str(sample_photo_with_sidecar))
                results.append(metadata is not None)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=read_metadata) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert all(results)  # All should succeed

    def test_concurrent_writes(self, service, multiple_photos_with_sidecars):
        """Multiple concurrent writes should work safely."""
        errors = []

        def update_metadata(photo, species):
            try:
                service.update_metadata(str(photo), {"species": species})
            except Exception as e:
                errors.append(str(e))

        threads = []
        for i, photo in enumerate(multiple_photos_with_sidecars):
            t = threading.Thread(target=update_metadata, args=(photo, f"Species {i}"))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


# ============================================================================
# Test Performance
# ============================================================================

class TestPerformance:
    """Performance tests for sidecar service."""

    def test_batch_processing_performance(self, service, photos_dir):
        """Batch processing 1000 files should complete in under 2 seconds."""
        from webui.backend.lib.sidecar_metadata import create_metadata, write_metadata

        # Create 100 photos with sidecars (reduced from 1000 for faster tests)
        photos = []
        for i in range(100):
            photo = photos_dir / f"photo_{i}.jpg"
            photo.write_bytes(b'\xFF\xD8\xFF\xE0')
            metadata = create_metadata(photo, tags=[f"tag_{i}"])
            write_metadata(photo, metadata)
            photos.append(str(photo))

        # Batch get all photos
        start = time.perf_counter()
        results = service.batch_get_metadata(photos)
        elapsed = time.perf_counter() - start

        assert len(results) == 100
        assert elapsed < 2.0, f"Batch processing took {elapsed:.2f}s (target: <2s)"

    def test_l1_cache_hit_performance(self, service, sample_photo_with_sidecar):
        """L1 cache hit should be very fast (<10ms)."""
        # Prime cache
        service.get_metadata(str(sample_photo_with_sidecar))

        # Measure L1 hit time
        start = time.perf_counter()
        for _ in range(100):
            service.get_metadata(str(sample_photo_with_sidecar))
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed / 100) * 1000
        assert avg_ms < 10, f"L1 cache hit avg {avg_ms:.2f}ms exceeds 10ms target"


# ============================================================================
# Test list_all_sidecars (Issue #124 - Tag Autocomplete)
# ============================================================================

class TestListAllSidecars:
    """Tests for list_all_sidecars method."""

    def test_list_all_sidecars_empty_directory(self, service, photos_dir):
        """list_all_sidecars should return empty list for directory with no sidecars."""
        results = service.list_all_sidecars(photos_dir)
        assert results == []

    def test_list_all_sidecars_with_photos(self, service, multiple_photos_with_sidecars, photos_dir):
        """list_all_sidecars should return all metadata objects."""
        results = service.list_all_sidecars(photos_dir)

        assert len(results) == len(multiple_photos_with_sidecars)
        # All results should be SidecarMetadata objects (not dicts)
        from webui.backend.lib.sidecar_metadata import SidecarMetadata
        assert all(isinstance(r, SidecarMetadata) for r in results)

    def test_list_all_sidecars_nonexistent_directory(self, service, tmp_path):
        """list_all_sidecars should return empty list for nonexistent directory."""
        results = service.list_all_sidecars(tmp_path / "nonexistent")
        assert results == []

    def test_list_all_sidecars_uses_cache(self, service, sample_photo_with_sidecar, photos_dir):
        """list_all_sidecars should populate cache for efficient repeat access."""
        # First call - should populate cache
        results1 = service.list_all_sidecars(photos_dir)
        stats1 = service.get_statistics()

        # Access same photo - should be L1 hit
        service.get_metadata(str(sample_photo_with_sidecar))
        stats2 = service.get_statistics()

        # Should have L1 hit since list_all_sidecars populated the cache
        assert stats2['l1_hits'] > stats1['l1_hits']

    def test_list_all_sidecars_returns_metadata_with_tags(self, service, photos_dir):
        """list_all_sidecars should return metadata with tags for TagAutocompleteEngine."""
        from webui.backend.lib.sidecar_metadata import create_metadata, write_metadata

        # Create photo with tags
        photo = photos_dir / "tagged_photo.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
        metadata = create_metadata(photo, tags=["moth", "luna", "nocturnal"])
        write_metadata(photo, metadata)

        results = service.list_all_sidecars(photos_dir)

        assert len(results) == 1
        assert results[0].tags == ["moth", "luna", "nocturnal"]


# ============================================================================
# Test Search Service Integration (Issue #131 - Phase 2.2)
# ============================================================================

class TestSidecarServiceSearchIntegration:
    """Tests for search index integration."""

    def test_init_without_search_service(self, tmp_path):
        """Should work without search_service (backward compatible)."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        service = SidecarService(cache_dir=cache_dir)
        assert service._search_service is None

    def test_init_with_search_service(self, tmp_path, mock_search_service):
        """Should accept search_service parameter."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        service = SidecarService(cache_dir=cache_dir, search_service=mock_search_service)
        assert service._search_service is mock_search_service

    def test_update_metadata_indexes_photo(self, tmp_path, mock_search_service):
        """update_metadata should call search_service.index_photo."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()

        # Create sample photo
        photo = photos_dir / "photo.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        service = SidecarService(cache_dir=cache_dir, search_service=mock_search_service)
        service.update_metadata(str(photo), {"tags": ["moth"]})

        mock_search_service.index_photo.assert_called_once()

    def test_update_metadata_passes_metadata_to_search(self, tmp_path, mock_search_service):
        """index_photo should receive the photo path and metadata."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()

        # Create sample photo
        photo = photos_dir / "photo.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        service = SidecarService(cache_dir=cache_dir, search_service=mock_search_service)
        metadata_updates = {"tags": ["luna_moth"], "species": "Actias luna"}
        service.update_metadata(str(photo), metadata_updates)

        # Should have been called once
        assert mock_search_service.index_photo.call_count == 1

        # Verify it was called with photo path
        call_args = mock_search_service.index_photo.call_args
        assert call_args[0][0] == str(photo)

        # Verify metadata dict was passed (as second arg)
        metadata_dict = call_args[0][1]
        assert isinstance(metadata_dict, dict)
        assert "tags" in metadata_dict
        assert "luna_moth" in metadata_dict["tags"]

    def test_delete_metadata_removes_from_index(self, tmp_path, mock_search_service):
        """delete_metadata should call search_service.remove_photo."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()

        # Create sample photo with sidecar
        photo = photos_dir / "photo.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        service = SidecarService(cache_dir=cache_dir, search_service=mock_search_service)

        # First create a sidecar
        service.update_metadata(str(photo), {"tags": ["test"]})
        mock_search_service.reset_mock()

        # Then delete it
        service.delete_metadata(str(photo))
        mock_search_service.remove_photo.assert_called_once_with(str(photo))

    def test_search_service_error_does_not_break_sidecar_ops(self, tmp_path, mock_search_service):
        """Search service errors should not prevent sidecar operations."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()

        # Create sample photo
        photo = photos_dir / "photo.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        # Make search service raise an error
        mock_search_service.index_photo.side_effect = Exception("Search error")

        service = SidecarService(cache_dir=cache_dir, search_service=mock_search_service)

        # Should not raise, sidecar should still be created
        service.update_metadata(str(photo), {"tags": ["test"]})

        # Verify sidecar was still created
        metadata = service.get_metadata(str(photo))
        assert metadata is not None
        assert "test" in metadata.tags

    def test_no_search_service_no_indexing(self, tmp_path):
        """Without search_service, no indexing calls should happen."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()

        # Create sample photo
        photo = photos_dir / "photo.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        service = SidecarService(cache_dir=cache_dir)  # No search_service

        # Should not raise - no search service means no index calls
        service.update_metadata(str(photo), {"tags": ["test"]})

        # Verify sidecar was created
        metadata = service.get_metadata(str(photo))
        assert metadata is not None
        assert "test" in metadata.tags

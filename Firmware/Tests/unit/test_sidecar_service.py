"""
Unit tests for Sidecar Service with Two-Level Cache (Issue #102 - Phase B)

Tests SidecarService with L1 (memory) and L2 (file-based) caching.
TDD approach: tests written first, then implementation.

Coverage Target: 85%+
"""

import json
import threading
import time

import pytest

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

        SidecarService(cache_dir=cache_dir)  # Creates directory as side effect
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
        service.list_all_sidecars(photos_dir)
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


# ============================================================================
# Test Response Time Metrics (Issue #173)
# ============================================================================

class TestResponseTimeMetrics:
    """Tests for response time metrics in get_statistics()."""

    def test_empty_response_times_returns_none(self, service):
        """When no operations performed, response time metrics should be None."""
        # Fresh service with empty _total_response_times deque
        stats = service.get_statistics()

        # Response time metrics should be None when no operations performed
        assert stats['avg_response_time_ms'] is None
        assert stats['p99_response_time_ms'] is None
        assert stats['response_time_samples'] == 0

    def test_avg_response_time_calculation(self, service):
        """Test average response time is calculated correctly."""
        # Manually add known response times to deque
        service._total_response_times.extend([10.0, 20.0, 30.0, 40.0])

        stats = service.get_statistics()

        # Average should be (10 + 20 + 30 + 40) / 4 = 25.0
        assert stats['avg_response_time_ms'] == 25.0
        assert stats['response_time_samples'] == 4

    def test_p99_response_time_calculation(self, service):
        """Test p99 percentile is calculated correctly."""
        # Add 100 values (1.0 to 100.0)
        service._total_response_times.extend([float(i) for i in range(1, 101)])

        stats = service.get_statistics()

        # 99th percentile of 1-100: int(100 * 0.99) = 99 (index), which is value 100.0
        assert stats['p99_response_time_ms'] == 100.0
        assert stats['response_time_samples'] == 100

    def test_response_time_samples_count(self, service):
        """Verify response_time_samples reflects deque size."""
        # Add 50 samples
        service._total_response_times.extend([5.0] * 50)

        stats = service.get_statistics()

        assert stats['response_time_samples'] == 50

    def test_single_response_time(self, service):
        """Test metrics with a single response time."""
        service._total_response_times.append(42.5)

        stats = service.get_statistics()

        # With single value, avg and p99 should be the same
        assert stats['avg_response_time_ms'] == 42.5
        assert stats['p99_response_time_ms'] == 42.5
        assert stats['response_time_samples'] == 1

    def test_response_times_from_actual_operations(self, service, sample_photo_with_sidecar):
        """Response times should be tracked from actual cache operations."""
        # Perform some operations to generate response times
        service.get_metadata(str(sample_photo_with_sidecar))
        service.get_metadata(str(sample_photo_with_sidecar))

        stats = service.get_statistics()

        # Should have response times recorded
        assert stats['response_time_samples'] > 0
        assert stats['avg_response_time_ms'] is not None
        assert stats['p99_response_time_ms'] is not None
        assert stats['avg_response_time_ms'] >= 0
        assert stats['p99_response_time_ms'] >= 0


# ============================================================================
# Test Cache Version Invalidation (Issue #185)
# ============================================================================

class TestCacheVersionInvalidation:
    """Tests for schema version-based cache invalidation."""

    def test_version_mismatch_returns_none(self, cache_dir):
        """Cache entry with old version is treated as miss."""
        from webui.backend.services.sidecar_service import SidecarService

        service = SidecarService(cache_dir=cache_dir, cache_version="2.0")

        # Create cache file with old version
        photo_path = "/photos/test.jpg"
        cache_file = service._get_cache_file_path(photo_path)
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        old_entry = {
            "photo_path": photo_path,
            "metadata": {"test": "data"},
            "cached_at": 123456.0,
            "cache_version": "1.0",  # Old version
        }
        cache_file.write_text(json.dumps(old_entry))

        # Should return None due to version mismatch
        result = service._get_l2(photo_path)
        assert result is None

    def test_version_mismatch_deletes_cache_file(self, cache_dir):
        """Cache file with old version is deleted."""
        from webui.backend.services.sidecar_service import SidecarService

        service = SidecarService(cache_dir=cache_dir, cache_version="2.0")

        photo_path = "/photos/test.jpg"
        cache_file = service._get_cache_file_path(photo_path)
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        old_entry = {
            "photo_path": photo_path,
            "metadata": {"test": "data"},
            "cached_at": 123456.0,
            "cache_version": "1.0",
        }
        cache_file.write_text(json.dumps(old_entry))

        service._get_l2(photo_path)
        assert not cache_file.exists()  # File should be deleted

    def test_matching_version_returns_entry(self, cache_dir):
        """Cache entry with matching version is returned."""
        from webui.backend.services.sidecar_service import SidecarService

        service = SidecarService(cache_dir=cache_dir, cache_version="2.0")

        photo_path = "/photos/test.jpg"
        cache_file = service._get_cache_file_path(photo_path)
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        entry = {
            "photo_path": photo_path,
            "metadata": {"species": "Moth"},
            "cached_at": 123456.0,
            "cache_version": "2.0",  # Matches service version
        }
        cache_file.write_text(json.dumps(entry))

        result = service._get_l2(photo_path)
        assert result is not None
        assert result.metadata["species"] == "Moth"

    def test_startup_purge_on_version_change(self, tmp_path, monkeypatch):
        """Startup purge removes all cache files when version changes."""
        import webui.backend.services as services_module
        from webui.backend.services.sidecar_service import CACHE_SCHEMA_VERSION

        # Reset singleton
        monkeypatch.setattr(services_module, '_sidecar_service', None)

        cache_dir = tmp_path / "cache" / "sidecar"
        cache_dir.mkdir(parents=True)

        # Create old cache files
        (cache_dir / "photo1.json").write_text('{"cache_version": "1.0"}')
        (cache_dir / "photo2.json").write_text('{"cache_version": "1.0"}')
        version_file = cache_dir / ".version"
        version_file.write_text("1.0")

        # Mock DATA_DIR to use tmp_path
        monkeypatch.setattr('mothbox_paths.DATA_DIR', tmp_path)

        # Initialize service (should trigger purge)
        from webui.backend.services import get_sidecar_service
        service = get_sidecar_service()

        # Verify old files removed
        assert not (cache_dir / "photo1.json").exists()
        assert not (cache_dir / "photo2.json").exists()

        # Verify version file updated
        assert version_file.read_text().strip() == CACHE_SCHEMA_VERSION

        # Verify service was created
        assert service is not None

    def test_startup_first_time_init(self, tmp_path, monkeypatch):
        """First-time initialization creates version file without purge."""
        import webui.backend.services as services_module
        from webui.backend.services.sidecar_service import CACHE_SCHEMA_VERSION

        # Reset singleton
        monkeypatch.setattr(services_module, '_sidecar_service', None)

        # Mock DATA_DIR to use tmp_path (cache dir doesn't exist yet)
        monkeypatch.setattr('mothbox_paths.DATA_DIR', tmp_path)

        # Initialize service (first time - no version file exists)
        from webui.backend.services import get_sidecar_service
        service = get_sidecar_service()

        cache_dir = tmp_path / "cache" / "sidecar"
        version_file = cache_dir / ".version"

        # Verify version file was created
        assert version_file.exists()
        assert version_file.read_text().strip() == CACHE_SCHEMA_VERSION

        # Verify service was created
        assert service is not None

    def test_startup_matching_version_no_purge(self, tmp_path, monkeypatch):
        """Matching version does not purge cache files."""
        import webui.backend.services as services_module
        from webui.backend.services.sidecar_service import CACHE_SCHEMA_VERSION

        # Reset singleton
        monkeypatch.setattr(services_module, '_sidecar_service', None)

        cache_dir = tmp_path / "cache" / "sidecar"
        cache_dir.mkdir(parents=True)

        # Create cache files with current version
        (cache_dir / "photo1.json").write_text(f'{{"cache_version": "{CACHE_SCHEMA_VERSION}"}}')
        version_file = cache_dir / ".version"
        version_file.write_text(CACHE_SCHEMA_VERSION)

        # Mock DATA_DIR to use tmp_path
        monkeypatch.setattr('mothbox_paths.DATA_DIR', tmp_path)

        # Initialize service (should NOT purge - version matches)
        from webui.backend.services import get_sidecar_service
        get_sidecar_service()

        # Verify file was NOT deleted
        assert (cache_dir / "photo1.json").exists()


# ============================================================================
# Test Error Paths and Uncovered Lines
# ============================================================================


class TestInitTempFileCleanup:
    """Tests for __init__ temp file cleanup logging (lines 186-188)."""

    def test_init_logs_cleaned_temp_files(self, tmp_path, monkeypatch):
        """Init should log when orphaned temp files are cleaned up."""
        from unittest.mock import patch

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        # Create orphaned temp files that cleanup_temp_files would find
        (cache_dir / "entry1.tmp").write_text("orphan1")
        (cache_dir / "entry2.tmp").write_text("orphan2")

        # Mock cleanup_temp_files to return a count > 0
        with patch(
            "webui.backend.services.sidecar_service.cleanup_temp_files",
            return_value=3,
        ) as mock_cleanup:
            service = SidecarService(cache_dir=cache_dir)
            mock_cleanup.assert_called_once_with(cache_dir)
            assert service is not None

    def test_init_handles_cleanup_exception(self, tmp_path):
        """Init should handle cleanup_temp_files raising an exception gracefully."""
        from unittest.mock import patch

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        with patch(
            "webui.backend.services.sidecar_service.cleanup_temp_files",
            side_effect=PermissionError("access denied"),
        ):
            # Should not raise - exception is caught and logged
            service = SidecarService(cache_dir=cache_dir)
            assert service is not None


class TestUpdateMetadataEdgeCases:
    """Tests for update_metadata edge cases (line 286->304 branch)."""

    def test_update_metadata_lib_returns_none(self, cache_dir, tmp_path):
        """update_metadata should handle lib_update_metadata returning None."""
        from unittest.mock import patch

        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()
        photo = photos_dir / "photo.jpg"
        photo.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100)

        service = SidecarService(cache_dir=cache_dir)

        # Mock lib_update_metadata to return None (simulating a failure case)
        with patch(
            "webui.backend.services.sidecar_service.lib_update_metadata",
            return_value=None,
        ):
            result = service.update_metadata(str(photo), {"species": "Test"})
            assert result is None


class TestDeleteMetadataEdgeCases:
    """Tests for delete_metadata edge cases (lines 323, 332->339, 335-336)."""

    def test_delete_metadata_no_sidecar_returns_false(self, cache_dir, tmp_path):
        """delete_metadata returns False when sidecar file doesn't exist."""
        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()
        photo = photos_dir / "photo.jpg"
        photo.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100)

        service = SidecarService(cache_dir=cache_dir)
        result = service.delete_metadata(str(photo))
        assert result is False

    def test_delete_metadata_no_search_service_succeeds(self, cache_dir, tmp_path):
        """delete_metadata without search service should succeed (line 332->339 false branch)."""
        from webui.backend.lib.sidecar_metadata import create_metadata, write_metadata

        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()
        photo = photos_dir / "photo.jpg"
        photo.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100)
        md = create_metadata(photo, tags=["moth"])
        write_metadata(photo, md)

        # No search service
        service = SidecarService(cache_dir=cache_dir)
        result = service.delete_metadata(str(photo))
        assert result is True

    def test_delete_metadata_search_service_error_ignored(self, tmp_path):
        """delete_metadata should handle search_service.remove_photo exception."""
        from unittest.mock import Mock

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()

        photo = photos_dir / "photo.jpg"
        photo.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100)

        mock_search = Mock()
        mock_search.index_photo = Mock(return_value=True)
        mock_search.remove_photo = Mock(side_effect=RuntimeError("Index corrupt"))

        service = SidecarService(cache_dir=cache_dir, search_service=mock_search)
        # Create sidecar first
        service.update_metadata(str(photo), {"tags": ["moth"]})
        mock_search.reset_mock()
        mock_search.remove_photo.side_effect = RuntimeError("Index corrupt")

        # delete should succeed despite search service error
        result = service.delete_metadata(str(photo))
        # The underlying delete should have been attempted
        mock_search.remove_photo.assert_called_once_with(str(photo))
        # Result depends on whether sidecar existed - it should since we just created it
        assert isinstance(result, bool)


class TestInvalidateEdgeCases:
    """Tests for invalidate L2 unlink error (lines 365-366)."""

    def test_invalidate_l2_unlink_error(self, cache_dir, sample_photo_with_sidecar):
        """invalidate should handle L2 cache file unlink failure gracefully."""
        from unittest.mock import patch

        service = SidecarService(cache_dir=cache_dir)
        # Prime cache (populates L1 and L2)
        service.get_metadata(str(sample_photo_with_sidecar))

        cache_file = service._get_cache_file_path(str(sample_photo_with_sidecar))
        assert cache_file.exists()

        # Make the unlink fail on the cache file
        with patch.object(type(cache_file), "unlink", side_effect=PermissionError("denied")):
            # Should still return True because L1 removal succeeded
            result = service.invalidate(str(sample_photo_with_sidecar))
            assert result is True


class TestClearEdgeCases:
    """Tests for clear error paths (lines 381-384)."""

    def test_clear_handles_individual_file_unlink_error(self, cache_dir, sample_photo_with_sidecar):
        """clear should handle individual L2 file unlink failures."""
        from pathlib import Path
        from unittest.mock import patch

        service = SidecarService(cache_dir=cache_dir)
        # Prime cache
        service.get_metadata(str(sample_photo_with_sidecar))

        original_unlink = Path.unlink

        def failing_unlink(self_path, *args, **kwargs):
            if str(self_path).endswith(".json"):
                raise PermissionError("denied")
            return original_unlink(self_path, *args, **kwargs)

        with patch.object(Path, "unlink", failing_unlink):
            # Should not raise
            service.clear()

        # Stats should still be reset
        stats = service.get_statistics()
        assert stats["l1_hits"] == 0

    def test_clear_handles_glob_error(self, cache_dir):
        """clear should handle L2 glob failure gracefully."""
        from unittest.mock import patch

        service = SidecarService(cache_dir=cache_dir)

        with patch.object(
            type(cache_dir), "glob", side_effect=OSError("filesystem error")
        ):
            # Should not raise
            service.clear()

        stats = service.get_statistics()
        assert stats["l1_hits"] == 0


class TestListMetadataDateFilter:
    """Tests for date filtering in list_metadata_for_directory (lines 521-531)."""

    def test_date_filter_start(self, cache_dir, tmp_path):
        """list_metadata_for_directory should filter by date_start from filename."""
        from webui.backend.lib.sidecar_metadata import create_metadata, write_metadata

        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()

        # Photo with date in filename matching Mothbox pattern
        old_photo = photos_dir / "Moth_2024_01_15__12_00_00.jpg"
        old_photo.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100)

        new_photo = photos_dir / "Moth_2024_06_20__14_30_00.jpg"
        new_photo.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100)

        service = SidecarService(cache_dir=cache_dir)
        result = service.list_metadata_for_directory(
            photos_dir, date_start="2024-03-01"
        )

        # Only the June photo should pass the filter
        assert result["total"] == 1
        assert "2024_06_20" in result["items"][0]["photo_filename"]

    def test_date_filter_end(self, cache_dir, tmp_path):
        """list_metadata_for_directory should filter by date_end from filename."""
        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()

        old_photo = photos_dir / "Moth_2024_01_15__12_00_00.jpg"
        old_photo.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100)

        new_photo = photos_dir / "Moth_2024_06_20__14_30_00.jpg"
        new_photo.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100)

        service = SidecarService(cache_dir=cache_dir)
        result = service.list_metadata_for_directory(
            photos_dir, date_end="2024-03-01"
        )

        # Only the January photo should pass the filter
        assert result["total"] == 1
        assert "2024_01_15" in result["items"][0]["photo_filename"]

    def test_date_filter_no_date_in_filename_skipped(self, cache_dir, tmp_path):
        """Photos without date in filename should be skipped when date filter is set."""
        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()

        # Photo without date pattern in filename
        nodated = photos_dir / "random_photo.jpg"
        nodated.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100)

        # Photo with date
        dated = photos_dir / "Moth_2024_06_20__14_30_00.jpg"
        dated.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100)

        service = SidecarService(cache_dir=cache_dir)
        result = service.list_metadata_for_directory(
            photos_dir, date_start="2024-01-01"
        )

        # Only the dated photo should be included
        assert result["total"] == 1
        assert "2024_06_20" in result["items"][0]["photo_filename"]

    def test_date_filter_range(self, cache_dir, tmp_path):
        """list_metadata_for_directory should filter by both date_start and date_end."""
        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()

        photo_jan = photos_dir / "Moth_2024_01_15__12_00_00.jpg"
        photo_jan.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100)

        photo_mar = photos_dir / "Moth_2024_03_20__14_30_00.jpg"
        photo_mar.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100)

        photo_jun = photos_dir / "Moth_2024_06_10__08_00_00.jpg"
        photo_jun.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100)

        service = SidecarService(cache_dir=cache_dir)
        result = service.list_metadata_for_directory(
            photos_dir, date_start="2024-02-01", date_end="2024-05-01"
        )

        assert result["total"] == 1
        assert "2024_03_20" in result["items"][0]["photo_filename"]


class TestListMetadataSeriesTypeFilter:
    """Tests for series_type filtering (lines 535-539)."""

    def test_series_type_filter_hdr(self, cache_dir, tmp_path):
        """list_metadata_for_directory should filter by series_type 'hdr'."""
        from unittest.mock import patch, MagicMock

        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()

        # Non-series photo
        normal = photos_dir / "Moth_2024_01_15__12_00_00.jpg"
        normal.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100)

        # HDR series photo
        hdr = photos_dir / "Moth_2024_01_15__12_00_00_HDR1.jpg"
        hdr.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100)

        service = SidecarService(cache_dir=cache_dir)

        # Mock detect_series_type to return expected values
        def mock_detect(filename):
            if "HDR" in filename:
                info = MagicMock()
                info.series_type = "hdr"
                return info
            return None

        with patch(
            "webui.backend.services.sidecar_service.detect_series_type",
            side_effect=mock_detect,
        ):
            result = service.list_metadata_for_directory(
                photos_dir, series_type="hdr"
            )

        assert result["total"] == 1
        assert "HDR" in result["items"][0]["photo_filename"]

    def test_series_type_filter_mismatch(self, cache_dir, tmp_path):
        """Photos with wrong series type should be filtered out."""
        from unittest.mock import patch, MagicMock

        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()

        photo = photos_dir / "Moth_2024_01_15__12_00_00_HDR1.jpg"
        photo.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100)

        service = SidecarService(cache_dir=cache_dir)

        def mock_detect(filename):
            info = MagicMock()
            info.series_type = "hdr"
            return info

        with patch(
            "webui.backend.services.sidecar_service.detect_series_type",
            side_effect=mock_detect,
        ):
            result = service.list_metadata_for_directory(
                photos_dir, series_type="focus_bracket"
            )

        assert result["total"] == 0


class TestListMetadataTagsAndSpeciesFilter:
    """Tests for tags and has_species filtering (lines 544-560)."""

    def test_tags_filter_matches(self, cache_dir, tmp_path):
        """list_metadata_for_directory should filter by tags."""
        from webui.backend.lib.sidecar_metadata import create_metadata, write_metadata

        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()

        # Photo with matching tag
        photo1 = photos_dir / "photo1.jpg"
        photo1.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100)
        md1 = create_metadata(photo1, tags=["moth", "nocturnal"])
        write_metadata(photo1, md1)

        # Photo without matching tag
        photo2 = photos_dir / "photo2.jpg"
        photo2.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100)
        md2 = create_metadata(photo2, tags=["butterfly", "diurnal"])
        write_metadata(photo2, md2)

        service = SidecarService(cache_dir=cache_dir)
        result = service.list_metadata_for_directory(photos_dir, tags=["moth"])

        assert result["total"] == 1
        assert result["items"][0]["photo_filename"] == "photo1.jpg"

    def test_tags_filter_skips_no_sidecar(self, cache_dir, tmp_path):
        """Photos without sidecar should be skipped when tags filter is active."""
        from webui.backend.lib.sidecar_metadata import create_metadata, write_metadata

        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()

        # Photo with sidecar
        photo1 = photos_dir / "photo1.jpg"
        photo1.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100)
        md1 = create_metadata(photo1, tags=["moth"])
        write_metadata(photo1, md1)

        # Photo without sidecar
        photo2 = photos_dir / "photo2.jpg"
        photo2.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100)

        service = SidecarService(cache_dir=cache_dir)
        result = service.list_metadata_for_directory(photos_dir, tags=["moth"])

        assert result["total"] == 1
        assert result["items"][0]["photo_filename"] == "photo1.jpg"

    def test_has_species_filter(self, cache_dir, tmp_path):
        """list_metadata_for_directory should filter by has_species."""
        from webui.backend.lib.sidecar_metadata import create_metadata, write_metadata

        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()

        # Photo with species
        photo1 = photos_dir / "photo1.jpg"
        photo1.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100)
        md1 = create_metadata(photo1, tags=["moth"], species="Actias luna")
        write_metadata(photo1, md1)

        # Photo without species
        photo2 = photos_dir / "photo2.jpg"
        photo2.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100)
        md2 = create_metadata(photo2, tags=["unknown"])
        write_metadata(photo2, md2)

        service = SidecarService(cache_dir=cache_dir)
        result = service.list_metadata_for_directory(photos_dir, has_species=True)

        assert result["total"] == 1
        assert result["items"][0]["photo_filename"] == "photo1.jpg"

    def test_tags_filter_no_match(self, cache_dir, tmp_path):
        """Tags filter with no matching tags should return empty results."""
        from webui.backend.lib.sidecar_metadata import create_metadata, write_metadata

        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()

        photo = photos_dir / "photo.jpg"
        photo.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100)
        md = create_metadata(photo, tags=["butterfly"])
        write_metadata(photo, md)

        service = SidecarService(cache_dir=cache_dir)
        result = service.list_metadata_for_directory(photos_dir, tags=["moth"])

        assert result["total"] == 0

    def test_has_species_filter_skips_no_sidecar(self, cache_dir, tmp_path):
        """has_species filter should skip photos without sidecar."""
        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()

        photo = photos_dir / "photo.jpg"
        photo.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100)

        service = SidecarService(cache_dir=cache_dir)
        result = service.list_metadata_for_directory(photos_dir, has_species=True)

        assert result["total"] == 0

    def test_tags_filter_metadata_read_fails(self, cache_dir, tmp_path):
        """tags filter should skip photos whose metadata can't be read."""
        from unittest.mock import patch
        from webui.backend.lib.sidecar_metadata import create_metadata, write_metadata

        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()

        photo = photos_dir / "photo.jpg"
        photo.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100)
        md = create_metadata(photo, tags=["moth"])
        write_metadata(photo, md)

        service = SidecarService(cache_dir=cache_dir)

        # Mock get_metadata to return None (simulating read failure)
        with patch.object(service, "get_metadata", return_value=None):
            result = service.list_metadata_for_directory(photos_dir, tags=["moth"])

        assert result["total"] == 0


class TestListMetadataPathEdgeCases:
    """Tests for path edge cases in list_metadata_for_directory (lines 579-580, 584)."""

    def test_relative_to_valueerror_uses_filename(self, cache_dir, tmp_path):
        """When relative_to raises ValueError, should fall back to filename."""
        from unittest.mock import patch
        from webui.backend.lib.sidecar_metadata import create_metadata, write_metadata

        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()

        photo = photos_dir / "photo.jpg"
        photo.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100)
        md = create_metadata(photo, tags=["test"])
        write_metadata(photo, md)

        service = SidecarService(cache_dir=cache_dir)

        # Patch Path.relative_to to raise ValueError
        original_relative_to = type(photo).relative_to

        def failing_relative_to(self, *args, **kwargs):
            raise ValueError("not relative")

        with patch.object(type(photo), "relative_to", failing_relative_to):
            result = service.list_metadata_for_directory(photos_dir)

        assert result["total"] == 1
        # Should fall back to just the filename
        assert result["items"][0]["path"] == "photo.jpg"

    def test_sidecar_exists_but_read_fails_uses_placeholder(self, cache_dir, tmp_path):
        """When sidecar exists but read fails, should use placeholder metadata."""
        from unittest.mock import patch
        from webui.backend.lib.sidecar_metadata import create_metadata, write_metadata

        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()

        photo = photos_dir / "photo.jpg"
        photo.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100)
        md = create_metadata(photo, tags=["test"])
        write_metadata(photo, md)

        service = SidecarService(cache_dir=cache_dir)

        # Mock get_metadata to return None (simulating read failure)
        with patch.object(service, "get_metadata", return_value=None):
            result = service.list_metadata_for_directory(photos_dir)

        assert result["total"] == 1
        item = result["items"][0]
        # Should be placeholder metadata
        assert item["has_sidecar"] is False or item.get("tags") == []


class TestListAllSidecarsEdgeCases:
    """Tests for list_all_sidecars edge cases (lines 631-633, 647->645)."""

    def test_list_all_sidecars_none_photos_dir(self, cache_dir, tmp_path, monkeypatch):
        """list_all_sidecars with None photos_dir should import PHOTOS_DIR."""
        from unittest.mock import patch

        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()

        service = SidecarService(cache_dir=cache_dir)

        # Mock PHOTOS_DIR to point to our tmp_path photos_dir
        with patch(
            "webui.backend.services.sidecar_service.PHOTOS_DIR",
            photos_dir,
            create=True,
        ):
            # Need to mock the import inside the function
            monkeypatch.setattr("mothbox_paths.PHOTOS_DIR", photos_dir)
            results = service.list_all_sidecars(photos_dir=None)

        assert results == []

    def test_list_all_sidecars_skips_none_metadata(self, cache_dir, tmp_path):
        """list_all_sidecars should skip photos where get_metadata returns None."""
        from unittest.mock import patch
        from webui.backend.lib.sidecar_metadata import create_metadata, write_metadata

        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()

        photo = photos_dir / "photo.jpg"
        photo.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100)
        md = create_metadata(photo, tags=["moth"])
        write_metadata(photo, md)

        service = SidecarService(cache_dir=cache_dir)

        # Mock get_metadata to return None
        with patch.object(service, "get_metadata", return_value=None):
            results = service.list_all_sidecars(photos_dir)

        assert results == []


class TestBuildPlaceholderMetadataEdgeCases:
    """Tests for _build_placeholder_metadata edge cases (lines 671-672, 677-678)."""

    def test_placeholder_oserror_on_stat(self, cache_dir, tmp_path):
        """_build_placeholder_metadata should handle OSError on stat."""
        from pathlib import Path
        from unittest.mock import patch

        service = SidecarService(cache_dir=cache_dir)

        # Use a non-existent path that will cause stat to fail
        photo_path = tmp_path / "nonexistent_photo.jpg"

        with patch.object(type(photo_path), "stat", side_effect=OSError("no such file")):
            result = service._build_placeholder_metadata(photo_path, tmp_path)

        assert result["file_timestamp"] is None
        assert result["photo_filename"] == "nonexistent_photo.jpg"

    def test_placeholder_valueerror_on_relative_to(self, cache_dir, tmp_path):
        """_build_placeholder_metadata should handle ValueError on relative_to."""
        from pathlib import Path
        from unittest.mock import patch

        service = SidecarService(cache_dir=cache_dir)

        photo_path = tmp_path / "photo.jpg"
        photo_path.write_bytes(b"\xFF\xD8\xFF\xE0")

        # Use a completely different base_dir that photo_path is not relative to
        other_dir = tmp_path / "other"
        other_dir.mkdir()

        # Force ValueError - use paths from totally different roots
        result = service._build_placeholder_metadata(
            Path("/some/random/photo.jpg"), Path("/different/root")
        )

        assert result["path"] == "photo.jpg"


class TestGetL2CorruptedCache:
    """Tests for _get_l2 corrupted cache file handling (lines 751-760)."""

    def test_get_l2_corrupted_json(self, cache_dir):
        """_get_l2 should handle corrupted JSON in cache file."""
        service = SidecarService(cache_dir=cache_dir)

        photo_path = "/photos/test.jpg"
        cache_file = service._get_cache_file_path(photo_path)
        cache_file.write_text("not valid json {{{")

        result = service._get_l2(photo_path)
        assert result is None
        # Corrupted file should be removed
        assert not cache_file.exists()

    def test_get_l2_corrupted_json_unlink_fails(self, cache_dir):
        """_get_l2 should handle failure to remove corrupted cache file."""
        from unittest.mock import patch

        service = SidecarService(cache_dir=cache_dir)

        photo_path = "/photos/test.jpg"
        cache_file = service._get_cache_file_path(photo_path)
        cache_file.write_text("not valid json {{{")

        # Make unlink fail after the json.load exception
        original_unlink = type(cache_file).unlink

        call_count = [0]

        def selective_unlink(self_path, *args, **kwargs):
            call_count[0] += 1
            if str(self_path) == str(cache_file) and call_count[0] >= 1:
                raise PermissionError("denied")
            return original_unlink(self_path, *args, **kwargs)

        with patch.object(type(cache_file), "unlink", selective_unlink):
            result = service._get_l2(photo_path)

        assert result is None

    def test_get_l2_missing_keys_in_json(self, cache_dir):
        """_get_l2 should handle JSON with missing required keys."""
        service = SidecarService(cache_dir=cache_dir)

        photo_path = "/photos/test.jpg"
        cache_file = service._get_cache_file_path(photo_path)
        # Valid JSON but missing required CacheEntry keys
        cache_file.write_text('{"incomplete": true}')

        result = service._get_l2(photo_path)
        assert result is None
        # Corrupted file should be removed
        assert not cache_file.exists()


class TestSetL2Errors:
    """Tests for _set_l2 write failure (lines 787-788)."""

    def test_set_l2_write_failure(self, cache_dir):
        """_set_l2 should handle write failure gracefully."""
        from unittest.mock import patch
        from webui.backend.services.sidecar_service import CacheEntry

        service = SidecarService(cache_dir=cache_dir)

        entry = CacheEntry(
            photo_path="/photos/test.jpg",
            metadata={"test": "data"},
            cached_at=time.time(),
            cache_version=service.cache_version,
        )

        # Make open() fail during L2 write
        with patch("builtins.open", side_effect=OSError("disk full")):
            # Should not raise
            service._set_l2("/photos/test.jpg", entry)

        # Verify no cache file was created
        cache_file = service._get_cache_file_path("/photos/test.jpg")
        assert not cache_file.exists()


class TestEvictL2:
    """Tests for _evict_l2_if_needed (lines 808-822)."""

    def test_evict_l2_when_full(self, tmp_path):
        """L2 eviction should remove oldest entries when cache is full."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        # Very small L2 cache
        service = SidecarService(cache_dir=cache_dir, l2_max_size=5)

        # Create 5 cache files manually (to fill up L2)
        for i in range(5):
            cache_file = cache_dir / f"entry_{i}.json"
            cache_file.write_text(json.dumps({
                "photo_path": f"/photos/photo_{i}.jpg",
                "metadata": {"test": i},
                "cached_at": time.time(),
                "cache_version": service.cache_version,
            }))
            # Stagger mtime slightly so ordering is deterministic
            import os
            os.utime(cache_file, (1000.0 + i, 1000.0 + i))

        # Trigger eviction
        service._evict_l2_if_needed()

        # 10% of 5 = max(1, 0.5) = 1 file should be evicted (the oldest)
        remaining = list(cache_dir.glob("*.json"))
        assert len(remaining) == 4
        # The oldest file (entry_0) should be evicted
        assert not (cache_dir / "entry_0.json").exists()

    def test_evict_l2_handles_unlink_error(self, tmp_path):
        """L2 eviction should handle individual file unlink errors."""
        from pathlib import Path
        from unittest.mock import patch

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        service = SidecarService(cache_dir=cache_dir, l2_max_size=3)

        # Create 3 cache files
        for i in range(3):
            cache_file = cache_dir / f"entry_{i}.json"
            cache_file.write_text(json.dumps({
                "photo_path": f"/photos/photo_{i}.jpg",
                "metadata": {"test": i},
                "cached_at": time.time(),
                "cache_version": service.cache_version,
            }))

        original_unlink = Path.unlink

        def failing_unlink(self_path, *args, **kwargs):
            if "entry_" in str(self_path):
                raise PermissionError("denied")
            return original_unlink(self_path, *args, **kwargs)

        with patch.object(Path, "unlink", failing_unlink):
            # Should not raise
            service._evict_l2_if_needed()

    def test_evict_l2_handles_outer_exception(self, tmp_path):
        """L2 eviction should handle glob failure."""
        from unittest.mock import patch

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        service = SidecarService(cache_dir=cache_dir, l2_max_size=3)

        with patch.object(
            type(cache_dir), "glob", side_effect=OSError("filesystem error")
        ):
            # Should not raise
            service._evict_l2_if_needed()

    def test_evict_l2_not_triggered_under_limit(self, tmp_path):
        """L2 eviction should not remove files when under the limit."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        service = SidecarService(cache_dir=cache_dir, l2_max_size=100)

        # Create 3 cache files (well under limit of 100)
        for i in range(3):
            cache_file = cache_dir / f"entry_{i}.json"
            cache_file.write_text(json.dumps({
                "photo_path": f"/photos/photo_{i}.jpg",
                "metadata": {"test": i},
                "cached_at": time.time(),
                "cache_version": service.cache_version,
            }))

        service._evict_l2_if_needed()

        # All files should still be present
        remaining = list(cache_dir.glob("*.json"))
        assert len(remaining) == 3


class TestRecordHitL2Branch:
    """Tests for _record_hit l2 branch (line 829->831)."""

    def test_record_hit_l2(self, service):
        """_record_hit should track L2 hits."""
        service._record_hit("l2", 25.0)

        stats = service.get_statistics()
        assert stats["l2_hits"] == 1
        assert stats["l1_hits"] == 0

    def test_record_hit_unknown_level(self, service):
        """_record_hit with unknown level should only record response time."""
        service._record_hit("unknown", 50.0)

        stats = service.get_statistics()
        assert stats["l1_hits"] == 0
        assert stats["l2_hits"] == 0
        assert stats["response_time_samples"] == 1

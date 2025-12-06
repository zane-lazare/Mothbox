"""
Integration test demonstrating SidecarService + SearchService integration.

This test shows how updates to sidecar metadata automatically update the search index.

Run with: MOTHBOX_ENV=test pytest Tests/integration/test_sidecar_search_integration.py -v
"""

import os
import sys
import pytest
from pathlib import Path

# Setup path
FIRMWARE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(FIRMWARE_DIR))
sys.path.insert(0, str(FIRMWARE_DIR / "webui" / "backend"))
os.environ.setdefault("MOTHBOX_ENV", "test")

from webui.backend.services.sidecar_service import SidecarService
from webui.backend.services.search_service import SearchService, SearchServiceConfig


pytestmark = pytest.mark.unit  # Mark as unit tests to avoid hardware skip


@pytest.fixture
def test_env(tmp_path):
    """Create test environment with photos and search database."""
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    search_db = tmp_path / "search.db"

    return {
        'photos_dir': photos_dir,
        'cache_dir': cache_dir,
        'search_db': search_db
    }


@pytest.fixture
def services(test_env):
    """Create integrated SidecarService and SearchService."""
    # Create search service
    config = SearchServiceConfig(
        db_path=test_env['search_db'],
        auto_rebuild=False
    )
    search_service = SearchService(config=config)

    # Create sidecar service with search integration
    sidecar_service = SidecarService(
        cache_dir=test_env['cache_dir'],
        search_service=search_service
    )

    yield {
        'sidecar': sidecar_service,
        'search': search_service
    }

    # Cleanup
    search_service.close()


def test_update_metadata_automatically_indexes_photo(test_env, services):
    """Updating sidecar metadata should automatically update search index."""
    # Create a photo
    photo = test_env['photos_dir'] / "luna_moth.jpg"
    photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

    # Update metadata (should trigger search indexing)
    services['sidecar'].update_metadata(str(photo), {
        'tags': ['moth', 'luna_moth'],
        'species': 'Actias luna',
        'notes': 'Beautiful green moth with long tails'
    })

    # Search should now find this photo
    results = services['search'].search('luna', limit=10)

    assert results['total'] == 1
    assert results['results'][0]['filename'] == 'luna_moth.jpg'
    assert 'luna_moth' in results['results'][0]['metadata']['tags']


def test_delete_metadata_automatically_removes_from_index(test_env, services):
    """Deleting sidecar metadata should automatically remove from search index."""
    # Create a photo with metadata
    photo = test_env['photos_dir'] / "test_moth.jpg"
    photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

    # Add metadata
    services['sidecar'].update_metadata(str(photo), {
        'tags': ['test'],
        'species': 'Test species'
    })

    # Verify it's in the search index
    results = services['search'].search('test', limit=10)
    assert results['total'] == 1

    # Delete the metadata
    services['sidecar'].delete_metadata(str(photo))

    # Should no longer be in search index
    results = services['search'].search('test', limit=10)
    assert results['total'] == 0


def test_multiple_updates_maintain_search_index_consistency(test_env, services):
    """Multiple metadata updates should keep search index in sync."""
    # Create a photo
    photo = test_env['photos_dir'] / "polyphemus.jpg"
    photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

    # Initial metadata
    services['sidecar'].update_metadata(str(photo), {
        'tags': ['moth'],
        'species': 'Unknown'
    })

    # Update metadata (species correction)
    services['sidecar'].update_metadata(str(photo), {
        'species': 'Antheraea polyphemus'
    })

    # Search by new species name
    results = services['search'].search('polyphemus', limit=10)

    assert results['total'] == 1
    assert results['results'][0]['metadata']['species'] == 'Antheraea polyphemus'
    assert 'moth' in results['results'][0]['metadata']['tags']


def test_search_service_failure_does_not_break_sidecar_operations(test_env):
    """Search service errors should not prevent sidecar metadata updates."""
    from unittest.mock import Mock

    # Create sidecar service with mock search service that raises errors
    mock_search = Mock()
    mock_search.index_photo.side_effect = Exception("Database connection lost")

    sidecar_service = SidecarService(
        cache_dir=test_env['cache_dir'],
        search_service=mock_search
    )

    # Create a photo
    photo = test_env['photos_dir'] / "test.jpg"
    photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

    # Update should succeed despite search service error
    metadata = sidecar_service.update_metadata(str(photo), {
        'tags': ['resilient'],
        'species': 'Test'
    })

    assert metadata is not None
    assert 'resilient' in metadata.tags

    # Verify the mock was called (error was caught and logged)
    mock_search.index_photo.assert_called_once()


def test_backward_compatibility_without_search_service(test_env):
    """SidecarService should work without search_service (backward compatible)."""
    # Create sidecar service without search integration
    sidecar_service = SidecarService(cache_dir=test_env['cache_dir'])

    # Create a photo
    photo = test_env['photos_dir'] / "test.jpg"
    photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

    # Should work normally
    metadata = sidecar_service.update_metadata(str(photo), {
        'tags': ['test'],
        'species': 'Test species'
    })

    assert metadata is not None
    assert 'test' in metadata.tags

    # Delete should also work
    success = sidecar_service.delete_metadata(str(photo))
    assert success is True

"""
Integration tests for the search workflow (Issue #131 - Phase 5.2)

Tests the complete search pipeline from API to results, including:
- End-to-end search workflow
- Integration with sidecar metadata
- Query parsing and execution
- Pagination and result formatting
- Error handling
- Performance characteristics

Run with: MOTHBOX_ENV=test pytest Tests/integration/test_search_workflow.py -v -s
"""

import os
import sys
import json
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

# Setup path
FIRMWARE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(FIRMWARE_DIR))
sys.path.insert(0, str(FIRMWARE_DIR / "webui" / "backend"))
os.environ.setdefault("MOTHBOX_ENV", "test")

from flask import Flask
from webui.backend.routes.search import search_bp
from webui.backend.services.search_service import SearchService, SearchServiceConfig
from webui.backend.services.sidecar_service import SidecarService

pytestmark = [pytest.mark.integration]


class TestSearchWorkflowE2E:
    """End-to-end search workflow tests"""

    @pytest.fixture
    def app_with_search(self, tmp_path, monkeypatch):
        """Create Flask app with search service configured"""
        # Setup test directories
        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        # Monkeypatch PHOTOS_DIR for search service
        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'PHOTOS_DIR', photos_dir)

        # Create test photos with sidecars
        for i in range(10):
            photo = photos_dir / f"moth_{i:02d}.jpg"
            photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)  # Minimal JPEG

            sidecar = photos_dir / f"moth_{i:02d}.jpg.json"
            sidecar.write_text(json.dumps({
                "version": "1.0",
                "photo_filename": f"moth_{i:02d}.jpg",
                "created_at": f"2024-01-{15+i:02d}T10:00:00Z",
                "modified_at": f"2024-01-{15+i:02d}T10:00:00Z",
                "tags": ["moth", f"tag{i}"],
                "species": "Actias luna" if i < 5 else "Papilio glaucus",
                "notes": f"Test photo {i}",
                "date": f"2024-01-{15+i:02d}",
                "custom": {}
            }))

        # Configure services
        db_path = cache_dir / "search.db"
        config = SearchServiceConfig(db_path=db_path, auto_rebuild=False)
        search_service = SearchService(config)

        # Build index
        search_service.build_index(photos_dir)

        # Create app
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SEARCH_SERVICE'] = search_service
        app.config['PHOTOS_DIR'] = photos_dir

        # Register routes
        app.register_blueprint(search_bp)

        yield app

        search_service.close()

    @pytest.fixture
    def client(self, app_with_search):
        return app_with_search.test_client()

    def test_search_finds_all_moths(self, client):
        """Search for 'moth' should find all 10 photos"""
        response = client.get('/api/photos/search?q=moth')

        assert response.status_code == 200
        data = response.get_json()

        assert data['total'] == 10
        assert len(data['results']) == 10

    def test_search_filters_by_species(self, client):
        """Search for species should filter correctly"""
        response = client.get('/api/photos/search?q=species:Actias')

        assert response.status_code == 200
        data = response.get_json()

        assert data['total'] == 5
        for result in data['results']:
            assert 'Actias' in result.get('metadata', {}).get('species', '')

    def test_search_returns_thumbnail_urls(self, client):
        """Results should include valid thumbnail URLs"""
        response = client.get('/api/photos/search?q=moth')

        data = response.get_json()

        for result in data['results']:
            assert 'thumbnail_url' in result
            assert result['thumbnail_url'].startswith('/api/gallery/thumbnail/')

    def test_search_pagination(self, client):
        """Pagination should work correctly"""
        # Get first page
        response1 = client.get('/api/photos/search?q=moth&limit=5&offset=0')
        data1 = response1.get_json()

        assert len(data1['results']) == 5
        assert data1['pagination']['has_next'] is True
        assert data1['pagination']['has_prev'] is False

        # Get second page
        response2 = client.get('/api/photos/search?q=moth&limit=5&offset=5')
        data2 = response2.get_json()

        assert len(data2['results']) == 5
        assert data2['pagination']['has_next'] is False
        assert data2['pagination']['has_prev'] is True

        # Results should be different
        filenames1 = [r['filename'] for r in data1['results']]
        filenames2 = [r['filename'] for r in data2['results']]
        assert len(set(filenames1) & set(filenames2)) == 0  # No overlap

    def test_search_stats_endpoint(self, client):
        """Stats endpoint should return index info"""
        response = client.get('/api/photos/search/stats')

        assert response.status_code == 200
        data = response.get_json()

        assert 'document_count' in data
        assert data['document_count'] == 10

    def test_search_returns_performance_metrics(self, client):
        """Results should include timing information"""
        response = client.get('/api/photos/search?q=moth')

        data = response.get_json()

        assert 'took_ms' in data
        assert isinstance(data['took_ms'], (int, float))
        assert data['took_ms'] >= 0

    def test_search_rebuild_endpoint(self, client):
        """Rebuild endpoint should trigger index rebuild"""
        response = client.post('/api/photos/search/rebuild')

        assert response.status_code == 200
        data = response.get_json()

        assert 'indexed' in data
        assert data['indexed'] == 10
        assert 'message' in data


class TestSearchAfterMetadataUpdate:
    """Test that search index updates when sidecars change"""

    @pytest.fixture
    def services(self, tmp_path):
        """Create connected search and sidecar services"""
        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        # Create test photo
        photo = photos_dir / "test.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        # Setup services
        db_path = cache_dir / "search.db"
        config = SearchServiceConfig(db_path=db_path, auto_rebuild=False)
        search_service = SearchService(config)
        sidecar_service = SidecarService(
            cache_dir=cache_dir,
            search_service=search_service
        )

        yield {
            'search': search_service,
            'sidecar': sidecar_service,
            'photos_dir': photos_dir
        }

        search_service.close()

    def test_new_photo_becomes_searchable(self, services):
        """New photo with sidecar should be immediately searchable"""
        # Add metadata via sidecar service
        services['sidecar'].update_metadata(
            str(services['photos_dir'] / "test.jpg"),
            {"tags": ["luna_moth"], "species": "Actias luna"}
        )

        # Search should find it
        result = services['search'].search("luna_moth")

        assert result['total'] == 1
        assert result['results'][0]['filename'] == 'test.jpg'

    def test_updated_tags_searchable(self, services):
        """Updated tags should be immediately searchable"""
        photo_path = str(services['photos_dir'] / "test.jpg")

        # Initial metadata
        services['sidecar'].update_metadata(photo_path, {"tags": ["moth"]})

        # Verify searchable
        assert services['search'].search("moth")['total'] == 1
        assert services['search'].search("butterfly")['total'] == 0

        # Update tags
        services['sidecar'].update_metadata(photo_path, {"tags": ["butterfly"]})

        # New tag should be searchable
        assert services['search'].search("butterfly")['total'] == 1

    def test_deleted_photo_removed_from_search(self, services):
        """Deleted sidecar should remove photo from search index"""
        photo_path = str(services['photos_dir'] / "test.jpg")

        # Add and verify
        services['sidecar'].update_metadata(photo_path, {"tags": ["moth"]})
        assert services['search'].search("moth")['total'] == 1

        # Delete
        services['sidecar'].delete_metadata(photo_path)

        # Should no longer be searchable
        assert services['search'].search("moth")['total'] == 0


class TestSearchQueryTypes:
    """Test all query syntax types work end-to-end"""

    @pytest.fixture
    def search_service(self, tmp_path):
        """Create search service with test data"""
        db_path = tmp_path / "cache" / "search.db"
        db_path.parent.mkdir(parents=True)

        config = SearchServiceConfig(db_path=db_path, auto_rebuild=False)
        service = SearchService(config)

        # Index test photos
        service.index_photo("luna_moth.jpg", {
            "filename": "luna_moth.jpg",
            "tags": ["moth", "luna_moth", "nocturnal"],
            "species": "Actias luna",
            "notes": "Large green moth seen at night",
            "date": "2024-01-15"
        })

        service.index_photo("swallowtail.jpg", {
            "filename": "swallowtail.jpg",
            "tags": ["butterfly", "swallowtail"],
            "species": "Papilio glaucus",
            "notes": "Yellow butterfly during day",
            "date": "2024-01-16"
        })

        service.index_photo("sphinx_moth.jpg", {
            "filename": "sphinx_moth.jpg",
            "tags": ["moth", "sphinx", "nocturnal"],
            "species": "Manduca sexta",
            "notes": "Hawk moth at dusk",
            "date": "2024-01-17"
        })

        yield service
        service.close()

    def test_simple_term(self, search_service):
        """Simple term search works"""
        result = search_service.search("moth")
        assert result['total'] == 2  # luna and sphinx

    def test_field_specific_tag(self, search_service):
        """tag: prefix works"""
        result = search_service.search("tag:nocturnal")
        assert result['total'] == 2

    def test_field_specific_species(self, search_service):
        """species: prefix works"""
        result = search_service.search("species:Actias")
        assert result['total'] == 1
        assert result['results'][0]['filename'] == 'luna_moth.jpg'

    def test_phrase_search(self, search_service):
        """Phrase search with quotes works"""
        result = search_service.search('"green moth"')
        assert result['total'] == 1

    def test_boolean_and(self, search_service):
        """AND operator works"""
        result = search_service.search("moth AND nocturnal")
        assert result['total'] == 2

    def test_boolean_or(self, search_service):
        """OR operator works"""
        result = search_service.search("moth OR butterfly")
        assert result['total'] == 3

    def test_not_operator(self, search_service):
        """NOT operator works"""
        result = search_service.search("moth NOT luna")
        assert result['total'] == 1
        assert result['results'][0]['filename'] == 'sphinx_moth.jpg'

    def test_prefix_wildcard(self, search_service):
        """Prefix wildcard works"""
        result = search_service.search("luna*")
        assert result['total'] == 1


class TestSearchErrorHandling:
    """Test error handling in search workflow"""

    @pytest.fixture
    def client(self, tmp_path):
        """Create minimal test client"""
        app = Flask(__name__)
        app.config['TESTING'] = True

        db_path = tmp_path / "cache" / "search.db"
        db_path.parent.mkdir(parents=True)
        config = SearchServiceConfig(db_path=db_path, auto_rebuild=False)
        app.config['SEARCH_SERVICE'] = SearchService(config)

        app.register_blueprint(search_bp)

        return app.test_client()

    def test_empty_query_returns_error(self, client):
        """Empty query should return 400"""
        response = client.get('/api/photos/search?q=')

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_missing_query_returns_error(self, client):
        """Missing q parameter should return 400"""
        response = client.get('/api/photos/search')

        assert response.status_code == 400

    def test_invalid_offset_returns_error(self, client):
        """Negative offset should return 400"""
        response = client.get('/api/photos/search?q=test&offset=-1')

        assert response.status_code == 400

    def test_non_numeric_limit(self, client):
        """Non-numeric limit should return 400"""
        response = client.get('/api/photos/search?q=test&limit=abc')

        assert response.status_code == 400

    def test_non_numeric_offset(self, client):
        """Non-numeric offset should return 400"""
        response = client.get('/api/photos/search?q=test&offset=xyz')

        assert response.status_code == 400


class TestSearchResultFormatting:
    """Test that search results are properly formatted for API response"""

    @pytest.fixture
    def app_with_data(self, tmp_path):
        """Create app with test data in subdirectory structure"""
        photos_dir = tmp_path / "photos"
        date_dir = photos_dir / "2024-01-15"
        date_dir.mkdir(parents=True)
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        # Create photo in date subdirectory
        photo = date_dir / "luna_moth.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        sidecar = date_dir / "luna_moth.jpg.json"
        sidecar.write_text(json.dumps({
            "version": "1.0",
            "photo_filename": "luna_moth.jpg",
            "created_at": "2024-01-15T10:00:00Z",
            "modified_at": "2024-01-15T10:00:00Z",
            "tags": ["moth"],
            "species": "Actias luna",
            "notes": "Test photo",
            "custom": {}
        }))

        # Setup search service
        db_path = cache_dir / "search.db"
        config = SearchServiceConfig(db_path=db_path, auto_rebuild=False)
        search_service = SearchService(config)

        # Build index
        search_service.build_index(photos_dir)

        # Create app
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SEARCH_SERVICE'] = search_service

        app.register_blueprint(search_bp)

        yield app

        search_service.close()

    def test_results_include_all_expected_fields(self, app_with_data):
        """Results should include all expected fields"""
        client = app_with_data.test_client()
        response = client.get('/api/photos/search?q=moth')

        data = response.get_json()
        result = data['results'][0]

        # Check all expected fields are present
        assert 'filename' in result
        assert 'path' in result
        assert 'thumbnail_url' in result
        assert 'metadata' in result
        assert 'score' in result
        assert 'matched_fields' in result

    def test_thumbnail_url_includes_path(self, app_with_data):
        """Thumbnail URL should include subdirectory path"""
        client = app_with_data.test_client()
        response = client.get('/api/photos/search?q=moth')

        data = response.get_json()
        result = data['results'][0]

        # Should include date directory in path
        assert '2024-01-15' in result['path']
        assert '2024-01-15' in result['thumbnail_url']

    def test_metadata_preserved_in_results(self, app_with_data):
        """Metadata should be preserved in search results"""
        client = app_with_data.test_client()
        response = client.get('/api/photos/search?q=moth')

        data = response.get_json()
        result = data['results'][0]

        # Check metadata is complete
        assert result['metadata']['species'] == 'Actias luna'
        assert 'moth' in result['metadata']['tags']
        assert result['metadata']['notes'] == 'Test photo'


class TestSearchPerformance:
    """Test search performance characteristics"""

    @pytest.fixture
    def large_index(self, tmp_path):
        """Create search service with large dataset"""
        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        # Create 100 test photos
        for i in range(100):
            photo = photos_dir / f"photo_{i:03d}.jpg"
            photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

            sidecar = photos_dir / f"photo_{i:03d}.jpg.json"
            sidecar.write_text(json.dumps({
                "version": "1.0",
                "photo_filename": f"photo_{i:03d}.jpg",
                "created_at": "2024-01-15T10:00:00Z",
                "modified_at": "2024-01-15T10:00:00Z",
                "tags": ["photo", f"tag{i % 10}"],
                "species": f"Species {i % 20}",
                "notes": f"Test photo number {i}",
                "custom": {}
            }))

        # Setup search service
        db_path = cache_dir / "search.db"
        config = SearchServiceConfig(db_path=db_path, auto_rebuild=False)
        service = SearchService(config)

        # Build index
        service.build_index(photos_dir)

        yield service
        service.close()

    def test_search_completes_quickly(self, large_index):
        """Search should complete in reasonable time"""
        result = large_index.search("photo", limit=20)

        # Should complete in under 100ms for 100 photos
        assert result['took_ms'] < 100
        assert result['total'] == 100

    def test_pagination_does_not_slow_down(self, large_index):
        """Pagination should not significantly impact performance"""
        # First page
        result1 = large_index.search("photo", limit=10, offset=0)
        time1 = result1['took_ms']

        # Last page
        result2 = large_index.search("photo", limit=10, offset=90)
        time2 = result2['took_ms']

        # Times should be comparable (within 2x)
        assert time2 < time1 * 2


class TestSearchEdgeCases:
    """Test edge cases in search workflow"""

    @pytest.fixture
    def empty_index(self, tmp_path):
        """Create search service with empty index"""
        db_path = tmp_path / "cache" / "search.db"
        db_path.parent.mkdir(parents=True)

        config = SearchServiceConfig(db_path=db_path, auto_rebuild=False)
        service = SearchService(config)

        yield service
        service.close()

    def test_search_empty_index(self, empty_index):
        """Search on empty index returns no results"""
        result = empty_index.search("anything")

        assert result['total'] == 0
        assert len(result['results']) == 0
        assert result['is_valid'] is True

    def test_search_with_special_characters(self, empty_index):
        """Search with special characters should not crash"""
        result = empty_index.search("test@#$%^&*()")

        assert result['is_valid'] is True
        assert result['total'] == 0

    def test_very_long_query(self, empty_index):
        """Very long query should be rejected if it exceeds term limits"""
        long_query = "moth " * 100  # 100 terms, exceeds MAX_QUERY_TERMS=20

        result = empty_index.search(long_query)

        # Query should be rejected due to exceeding term limit (DoS protection)
        assert result['is_valid'] is False
        assert 'too many' in result.get('error_message', '').lower()

    def test_unicode_query(self, empty_index):
        """Unicode characters in query should work"""
        result = empty_index.search("papillon 🦋")

        assert result['is_valid'] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

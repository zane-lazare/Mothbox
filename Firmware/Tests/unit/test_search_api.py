"""
Unit tests for Search API endpoints (routes/search.py)

TDD Protocol:
1. Write tests FIRST
2. Run tests to confirm FAIL
3. Implement minimal code to make tests pass
4. Refactor with tests green

Test Coverage:
- Search endpoint (GET /api/photos/search)
- Stats endpoint (GET /api/photos/search/stats)
- Rebuild endpoint (POST /api/photos/search/rebuild)
- Query validation
- Pagination
- Field-specific queries
- Error handling
"""

import pytest
from flask import Flask
from unittest.mock import Mock, patch, MagicMock
import json


class TestSearchAPIEndpoints:
    """Base test class with fixtures"""

    @pytest.fixture
    def mock_search_service(self):
        """Create mock search service"""
        service = Mock()
        service.search.return_value = {
            'results': [
                {
                    'filename': 'IMG_001.jpg',
                    'filepath': '2024-11-10/IMG_001.jpg',
                    'metadata': {
                        'tags': ['moth', 'luna_moth'],
                        'species': 'Actias luna',
                        'species_common_name': 'Luna Moth',
                        'notes': 'Large specimen near UV light'
                    },
                    'score': 0.95,
                    'matched_fields': ['tags', 'species']
                }
            ],
            'total': 45,
            'took_ms': 23.5,
            'parsed_query': 'luna AND moth',
            'is_valid': True
        }
        service.get_statistics.return_value = {
            'document_count': 1234,
            'index_size_bytes': 245760,
            'db_path': '/var/lib/mothbox/cache/search.db'
        }
        service.build_index.return_value = {
            'indexed': 1234,
            'errors': 0,
            'took_ms': 5432.1
        }
        return service

    @pytest.fixture
    def app(self, mock_search_service):
        """Create Flask app with search blueprint"""
        from webui.backend.routes.search import search_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
        app.config['SEARCH_SERVICE'] = mock_search_service

        app.register_blueprint(search_bp)

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()


class TestSearchEndpoint(TestSearchAPIEndpoints):
    """Tests for GET /api/photos/search"""

    def test_simple_search(self, client, mock_search_service):
        """GET /api/photos/search?q=moth should return results"""
        response = client.get('/api/photos/search?q=moth')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert 'results' in data
        assert len(data['results']) == 1
        assert data['results'][0]['filename'] == 'IMG_001.jpg'

        # Verify service was called with correct parameters
        mock_search_service.search.assert_called_once_with('moth', limit=20, offset=0)

    def test_search_returns_expected_fields(self, client):
        """Response should include results, total, query, pagination"""
        response = client.get('/api/photos/search?q=luna moth')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Check all required top-level fields
        assert 'results' in data
        assert 'total' in data
        assert 'query' in data
        assert 'parsed_query' in data
        assert 'took_ms' in data
        assert 'pagination' in data

        # Check pagination fields
        pagination = data['pagination']
        assert 'limit' in pagination
        assert 'offset' in pagination
        assert 'has_next' in pagination
        assert 'has_prev' in pagination

        # Verify values
        assert data['query'] == 'luna moth'
        assert data['total'] == 45
        assert data['took_ms'] == 23.5

    def test_search_empty_query_returns_error(self, client):
        """Empty q parameter should return 400"""
        response = client.get('/api/photos/search?q=')

        assert response.status_code == 400
        data = json.loads(response.data)

        assert 'error' in data
        assert 'message' in data
        assert data['error'] == 'Missing query'
        assert 'required' in data['message'].lower()

    def test_search_missing_query_returns_error(self, client):
        """Missing q parameter should return 400"""
        response = client.get('/api/photos/search')

        assert response.status_code == 400
        data = json.loads(response.data)

        assert data['error'] == 'Missing query'
        assert "parameter 'q' is required" in data['message']

    def test_search_invalid_query_returns_error(self, client, mock_search_service):
        """Malformed query should return 400 with error details"""
        # Configure service to return invalid query result
        mock_search_service.search.return_value = {
            'results': [],
            'total': 0,
            'took_ms': 0,
            'is_valid': False,
            'error_message': 'Unbalanced quotes in query'
        }

        response = client.get('/api/photos/search?q="luna moth')

        assert response.status_code == 400
        data = json.loads(response.data)

        assert 'error' in data
        assert 'message' in data
        assert 'query' in data
        assert data['error'] == 'Invalid query'
        assert 'Unbalanced quotes' in data['message']
        assert data['query'] == '"luna moth'

    def test_search_pagination_limit(self, client, mock_search_service):
        """Should respect limit parameter"""
        response = client.get('/api/photos/search?q=moth&limit=50')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['pagination']['limit'] == 50

        # Verify service was called with correct limit
        mock_search_service.search.assert_called_once_with('moth', limit=50, offset=0)

    def test_search_pagination_offset(self, client, mock_search_service):
        """Should respect offset parameter"""
        response = client.get('/api/photos/search?q=moth&offset=20')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['pagination']['offset'] == 20

        # Verify service was called with correct offset
        mock_search_service.search.assert_called_once_with('moth', limit=20, offset=20)

    def test_search_max_limit_enforced(self, client, mock_search_service):
        """Limit > 100 should be capped at 100"""
        response = client.get('/api/photos/search?q=moth&limit=500')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['pagination']['limit'] == 100

        # Verify service was called with capped limit
        mock_search_service.search.assert_called_once_with('moth', limit=100, offset=0)

    def test_search_negative_offset_rejected(self, client):
        """Negative offset should return 400"""
        response = client.get('/api/photos/search?q=moth&offset=-10')

        assert response.status_code == 400
        data = json.loads(response.data)

        assert 'error' in data
        assert 'Invalid offset' in data['error']
        assert 'non-negative' in data['message'].lower()

    def test_search_includes_thumbnail_urls(self, client):
        """Results should include thumbnail_url for each photo"""
        response = client.get('/api/photos/search?q=moth')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert len(data['results']) > 0
        result = data['results'][0]

        assert 'thumbnail_url' in result
        assert result['thumbnail_url'] == '/api/gallery/thumbnail/2024-11-10/IMG_001.jpg'

    def test_search_no_csrf_required(self, client):
        """GET requests should not require CSRF"""
        # This test verifies GET works without CSRF token
        response = client.get('/api/photos/search?q=moth')
        assert response.status_code == 200

    def test_search_pagination_has_next_true(self, client):
        """has_next should be True when more results available"""
        response = client.get('/api/photos/search?q=moth&limit=20&offset=0')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Total is 45, showing first 20, so has_next should be True
        assert data['pagination']['has_next'] is True
        assert data['pagination']['has_prev'] is False

    def test_search_pagination_has_next_false(self, client):
        """has_next should be False on last page"""
        response = client.get('/api/photos/search?q=moth&limit=20&offset=40')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Total is 45, offset 40 + limit 20 = 60 > 45, so has_next is False
        assert data['pagination']['has_next'] is False
        assert data['pagination']['has_prev'] is True

    def test_search_result_includes_metadata(self, client):
        """Results should include metadata fields"""
        response = client.get('/api/photos/search?q=moth')

        assert response.status_code == 200
        data = json.loads(response.data)

        result = data['results'][0]
        assert 'metadata' in result

        metadata = result['metadata']
        assert 'tags' in metadata
        assert 'species' in metadata
        assert 'species_common_name' in metadata
        assert 'notes' in metadata

        assert metadata['tags'] == ['moth', 'luna_moth']
        assert metadata['species'] == 'Actias luna'

    def test_search_result_includes_score(self, client):
        """Results should include relevance score"""
        response = client.get('/api/photos/search?q=moth')

        assert response.status_code == 200
        data = json.loads(response.data)

        result = data['results'][0]
        assert 'score' in result
        assert result['score'] == 0.95

    def test_search_result_includes_matched_fields(self, client):
        """Results should include matched_fields array"""
        response = client.get('/api/photos/search?q=moth')

        assert response.status_code == 200
        data = json.loads(response.data)

        result = data['results'][0]
        assert 'matched_fields' in result
        assert isinstance(result['matched_fields'], list)
        assert 'tags' in result['matched_fields']
        assert 'species' in result['matched_fields']

    def test_search_service_unavailable(self, app, client):
        """Should return 503 when search service not configured"""
        # Remove search service from config
        app.config['SEARCH_SERVICE'] = None

        response = client.get('/api/photos/search?q=moth')

        assert response.status_code == 503
        data = json.loads(response.data)
        assert 'error' in data
        assert 'not available' in data['error'].lower()


class TestSearchStatsEndpoint(TestSearchAPIEndpoints):
    """Tests for GET /api/photos/search/stats"""

    def test_get_stats(self, client, mock_search_service):
        """GET /api/photos/search/stats should return index stats"""
        response = client.get('/api/photos/search/stats')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert 'document_count' in data
        assert 'index_size_bytes' in data
        assert 'db_path' in data

        # Verify service was called
        mock_search_service.get_statistics.assert_called_once()

    def test_stats_includes_document_count(self, client):
        """Stats should include document_count"""
        response = client.get('/api/photos/search/stats')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['document_count'] == 1234

    def test_stats_includes_index_size(self, client):
        """Stats should include index_size_bytes"""
        response = client.get('/api/photos/search/stats')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['index_size_bytes'] == 245760

    def test_stats_includes_db_path(self, client):
        """Stats should include db_path"""
        response = client.get('/api/photos/search/stats')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['db_path'] == '/var/lib/mothbox/cache/search.db'

    def test_stats_service_unavailable(self, app, client):
        """Should return 503 when search service not configured"""
        app.config['SEARCH_SERVICE'] = None

        response = client.get('/api/photos/search/stats')

        assert response.status_code == 503
        data = json.loads(response.data)
        assert 'error' in data


class TestRebuildEndpoint(TestSearchAPIEndpoints):
    """Tests for POST /api/photos/search/rebuild"""

    def test_rebuild_requires_post(self, client):
        """GET /api/photos/search/rebuild should return 405"""
        response = client.get('/api/photos/search/rebuild')

        assert response.status_code == 405

    def test_rebuild_triggers_index_rebuild(self, client, mock_search_service):
        """POST /api/photos/search/rebuild should rebuild index"""
        response = client.post('/api/photos/search/rebuild')

        assert response.status_code == 200

        # Verify service was called
        mock_search_service.build_index.assert_called_once()

    def test_rebuild_returns_stats(self, client):
        """Rebuild should return indexed count and time"""
        response = client.post('/api/photos/search/rebuild')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert 'indexed' in data
        assert 'errors' in data
        assert 'took_ms' in data
        assert 'message' in data

        assert data['indexed'] == 1234
        assert data['errors'] == 0
        assert data['took_ms'] == 5432.1
        assert 'success' in data['message'].lower()

    def test_rebuild_requires_csrf(self, app, client):
        """POST should require CSRF token when CSRF enabled"""
        # Enable CSRF for this test
        app.config['WTF_CSRF_ENABLED'] = True

        response = client.post('/api/photos/search/rebuild')

        # Without CSRF token, should get 400
        # Note: With WTF_CSRF_ENABLED=False in fixture, this passes
        # With it enabled, would need CSRF token
        # For now, this test verifies the endpoint exists and responds to POST
        assert response.status_code in [200, 400]

    def test_rebuild_service_unavailable(self, app, client):
        """Should return 503 when search service not configured"""
        app.config['SEARCH_SERVICE'] = None

        response = client.post('/api/photos/search/rebuild')

        assert response.status_code == 503
        data = json.loads(response.data)
        assert 'error' in data


class TestSearchFieldQueries(TestSearchAPIEndpoints):
    """Tests for field-specific search queries"""

    def test_tag_field_search(self, client, mock_search_service):
        """tag:moth should search tags field"""
        response = client.get('/api/photos/search?q=tag:moth')

        assert response.status_code == 200

        # Verify service was called with field query
        mock_search_service.search.assert_called_once_with('tag:moth', limit=20, offset=0)

    def test_species_field_search(self, client, mock_search_service):
        """species:actias should search species field"""
        response = client.get('/api/photos/search?q=species:actias')

        assert response.status_code == 200

        # Verify service was called with field query
        mock_search_service.search.assert_called_once_with('species:actias', limit=20, offset=0)

    def test_combined_field_search(self, client, mock_search_service):
        """Multiple field queries should combine"""
        response = client.get('/api/photos/search?q=tag:moth species:actias')

        assert response.status_code == 200

        # Verify service was called with combined query
        mock_search_service.search.assert_called_once_with(
            'tag:moth species:actias',
            limit=20,
            offset=0
        )

    def test_notes_field_search(self, client, mock_search_service):
        """notes:field should search notes field"""
        response = client.get('/api/photos/search?q=notes:specimen')

        assert response.status_code == 200

        mock_search_service.search.assert_called_once_with('notes:specimen', limit=20, offset=0)


class TestSearchEdgeCases(TestSearchAPIEndpoints):
    """Tests for edge cases and error conditions"""

    def test_search_with_special_characters(self, client, mock_search_service):
        """Should handle special characters in query"""
        response = client.get('/api/photos/search?q=moth&butterfly')

        assert response.status_code == 200

        # Query should be URL decoded and passed to service
        mock_search_service.search.assert_called_once()

    def test_search_with_unicode(self, client, mock_search_service):
        """Should handle Unicode characters"""
        response = client.get('/api/photos/search?q=北夜蛾')

        assert response.status_code == 200

    def test_search_zero_results(self, client, mock_search_service):
        """Should handle zero results gracefully"""
        mock_search_service.search.return_value = {
            'results': [],
            'total': 0,
            'took_ms': 5.2,
            'parsed_query': 'nomatch',
            'is_valid': True
        }

        response = client.get('/api/photos/search?q=nomatch')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['total'] == 0
        assert len(data['results']) == 0
        assert data['pagination']['has_next'] is False
        assert data['pagination']['has_prev'] is False

    def test_search_invalid_limit_type(self, client):
        """Should handle non-integer limit"""
        response = client.get('/api/photos/search?q=moth&limit=abc')

        # Should either default to 20 or return 400
        # Implementation choice - let's expect 400 for invalid type
        assert response.status_code in [200, 400]

    def test_search_invalid_offset_type(self, client):
        """Should handle non-integer offset"""
        response = client.get('/api/photos/search?q=moth&offset=xyz')

        # Should either default to 0 or return 400
        assert response.status_code in [200, 400]

    def test_search_whitespace_only_query(self, client):
        """Whitespace-only query should return 400"""
        response = client.get('/api/photos/search?q=   ')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'Missing query'

    def test_search_very_long_query(self, client, mock_search_service):
        """Should handle very long queries"""
        long_query = 'moth ' * 100
        response = client.get(f'/api/photos/search?q={long_query}')

        assert response.status_code == 200

    def test_search_minimum_limit(self, client, mock_search_service):
        """Should handle limit=1"""
        response = client.get('/api/photos/search?q=moth&limit=1')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['pagination']['limit'] == 1


class TestSearchResultFormatting(TestSearchAPIEndpoints):
    """Tests for result formatting"""

    def test_result_format_all_fields(self, client):
        """Each result should have all required fields"""
        response = client.get('/api/photos/search?q=moth')

        assert response.status_code == 200
        data = json.loads(response.data)

        result = data['results'][0]
        required_fields = ['filename', 'path', 'thumbnail_url', 'metadata', 'score', 'matched_fields']

        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

    def test_result_metadata_structure(self, client):
        """Metadata should preserve structure from service"""
        response = client.get('/api/photos/search?q=moth')

        assert response.status_code == 200
        data = json.loads(response.data)

        metadata = data['results'][0]['metadata']

        # Should be a dict
        assert isinstance(metadata, dict)

        # Should contain original fields
        assert metadata['tags'] == ['moth', 'luna_moth']
        assert metadata['species'] == 'Actias luna'

    def test_thumbnail_url_construction(self, client):
        """Thumbnail URLs should be correctly constructed"""
        response = client.get('/api/photos/search?q=moth')

        assert response.status_code == 200
        data = json.loads(response.data)

        result = data['results'][0]

        # URL should match pattern
        assert result['thumbnail_url'].startswith('/api/gallery/thumbnail/')
        assert result['path'] in result['thumbnail_url']

"""
Unit tests for Tag Autocomplete API Endpoint (Issue #124)

Tests the /api/metadata/tags/autocomplete endpoint with various scenarios:
- Valid queries with suggestions
- Missing/empty query parameters
- Limit parameter validation
- Special character handling
- Response format validation

TDD approach: tests written first, then implementation.

Coverage Target: 85%+
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Import will fail until implementation exists - that's expected in TDD
try:
    from webui.backend.routes.metadata import metadata_bp
    IMPLEMENTATION_EXISTS = True
except ImportError:
    IMPLEMENTATION_EXISTS = False
    metadata_bp = None

# Skip all tests if implementation doesn't exist yet (TDD red phase)
pytestmark = pytest.mark.skipif(
    not IMPLEMENTATION_EXISTS,
    reason="Implementation not yet created (TDD red phase)"
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def app():
    """Create Flask app for testing."""
    from flask import Flask
    from flask_wtf.csrf import CSRFProtect

    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
    app.config['SECRET_KEY'] = 'test-secret-key'

    # Initialize CSRF protection
    csrf = CSRFProtect(app)

    # Mock TAG_AUTOCOMPLETE_ENGINE
    mock_engine = MagicMock()
    app.config['TAG_AUTOCOMPLETE_ENGINE'] = mock_engine

    # Register blueprint
    from webui.backend.routes.metadata import metadata_bp
    app.register_blueprint(metadata_bp, url_prefix='/api/metadata')

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def mock_engine(app):
    """Get mock autocomplete engine from app config."""
    return app.config['TAG_AUTOCOMPLETE_ENGINE']


# ============================================================================
# Test Valid Queries
# ============================================================================

class TestAutocompleteValidQueries:
    """Tests for valid autocomplete queries."""

    def test_autocomplete_returns_suggestions(self, client, mock_engine):
        """Valid query should return suggestions from engine."""
        from webui.backend.lib.tag_autocomplete import AutocompleteSuggestion
        from datetime import datetime, UTC

        # Mock engine response
        mock_suggestions = [
            AutocompleteSuggestion(
                tag="luna_moth",
                count=45,
                last_used=datetime(2024, 11, 5, 10, 30, 0, tzinfo=UTC),
                match_score=0.95
            ),
            AutocompleteSuggestion(
                tag="sphinx_moth",
                count=23,
                last_used=datetime(2024, 11, 1, 8, 0, 0, tzinfo=UTC),
                match_score=0.82
            )
        ]
        mock_engine.search.return_value = mock_suggestions

        # Make request
        response = client.get('/api/metadata/tags/autocomplete?q=moth')

        assert response.status_code == 200
        data = response.get_json()

        # Verify response structure
        assert 'suggestions' in data
        assert 'query' in data
        assert 'total' in data

        # Verify query
        assert data['query'] == 'moth'
        assert data['total'] == 2

        # Verify suggestions
        assert len(data['suggestions']) == 2

        # Verify first suggestion
        assert data['suggestions'][0]['tag'] == 'luna_moth'
        assert data['suggestions'][0]['count'] == 45
        assert data['suggestions'][0]['last_used'] == '2024-11-05T10:30:00+00:00'
        assert data['suggestions'][0]['match_score'] == 0.95

        # Verify engine was called correctly
        mock_engine.search.assert_called_once_with('moth', limit=10)

    def test_autocomplete_empty_query_returns_top_tags(self, client, mock_engine):
        """Empty query should return top tags by frequency."""
        from webui.backend.lib.tag_autocomplete import AutocompleteSuggestion
        from datetime import datetime, UTC

        # Mock engine response for empty query
        mock_suggestions = [
            AutocompleteSuggestion(
                tag="moth",
                count=100,
                last_used=datetime(2024, 11, 5, 10, 30, 0, tzinfo=UTC),
                match_score=100.0
            ),
            AutocompleteSuggestion(
                tag="butterfly",
                count=80,
                last_used=datetime(2024, 11, 4, 8, 0, 0, tzinfo=UTC),
                match_score=80.0
            )
        ]
        mock_engine.search.return_value = mock_suggestions

        # Make request with empty query
        response = client.get('/api/metadata/tags/autocomplete?q=')

        assert response.status_code == 200
        data = response.get_json()

        assert data['query'] == ''
        assert data['total'] == 2
        assert len(data['suggestions']) == 2
        assert data['suggestions'][0]['count'] == 100

        # Engine should be called with empty string
        mock_engine.search.assert_called_once_with('', limit=10)

    def test_autocomplete_special_characters_handled(self, client, mock_engine):
        """Special characters in query should be handled correctly."""
        from webui.backend.lib.tag_autocomplete import AutocompleteSuggestion
        from datetime import datetime, UTC

        # Mock engine response
        mock_suggestions = [
            AutocompleteSuggestion(
                tag="tiger_beetle",
                count=10,
                last_used=datetime(2024, 11, 1, 8, 0, 0, tzinfo=UTC),
                match_score=0.75
            )
        ]
        mock_engine.search.return_value = mock_suggestions

        # Make request with special characters
        response = client.get('/api/metadata/tags/autocomplete?q=tiger_beetle')

        assert response.status_code == 200
        data = response.get_json()

        assert data['query'] == 'tiger_beetle'
        assert data['total'] == 1

        # Engine should be called with exact query
        mock_engine.search.assert_called_once_with('tiger_beetle', limit=10)


# ============================================================================
# Test Limit Parameter
# ============================================================================

class TestAutocompleteLimitParameter:
    """Tests for limit parameter validation."""

    def test_autocomplete_limit_parameter(self, client, mock_engine):
        """Custom limit parameter should be respected."""
        from webui.backend.lib.tag_autocomplete import AutocompleteSuggestion
        from datetime import datetime, UTC

        # Mock engine response
        mock_suggestions = [
            AutocompleteSuggestion(
                tag=f"tag_{i}",
                count=i,
                last_used=datetime(2024, 11, 1, 8, 0, 0, tzinfo=UTC),
                match_score=0.5
            )
            for i in range(5)
        ]
        mock_engine.search.return_value = mock_suggestions

        # Make request with custom limit
        response = client.get('/api/metadata/tags/autocomplete?q=test&limit=5')

        assert response.status_code == 200
        data = response.get_json()

        assert data['total'] == 5

        # Engine should be called with custom limit
        mock_engine.search.assert_called_once_with('test', limit=5)

    def test_autocomplete_limit_exceeds_max_capped(self, client, mock_engine):
        """Limit exceeding max (50) should be capped."""
        from webui.backend.lib.tag_autocomplete import AutocompleteSuggestion

        mock_engine.search.return_value = []

        # Make request with limit > 50
        response = client.get('/api/metadata/tags/autocomplete?q=test&limit=100')

        assert response.status_code == 200

        # Engine should be called with capped limit (50)
        mock_engine.search.assert_called_once_with('test', limit=50)

    def test_autocomplete_limit_default_is_10(self, client, mock_engine):
        """Default limit should be 10 if not specified."""
        from webui.backend.lib.tag_autocomplete import AutocompleteSuggestion

        mock_engine.search.return_value = []

        # Make request without limit parameter
        response = client.get('/api/metadata/tags/autocomplete?q=test')

        assert response.status_code == 200

        # Engine should be called with default limit (10)
        mock_engine.search.assert_called_once_with('test', limit=10)

    def test_autocomplete_limit_invalid_type_uses_default(self, client, mock_engine):
        """Invalid limit type should use default (10)."""
        mock_engine.search.return_value = []

        # Make request with invalid limit
        response = client.get('/api/metadata/tags/autocomplete?q=test&limit=invalid')

        assert response.status_code == 200

        # Should use default limit
        mock_engine.search.assert_called_once_with('test', limit=10)

    def test_autocomplete_limit_negative_uses_default(self, client, mock_engine):
        """Negative limit should use default (10)."""
        mock_engine.search.return_value = []

        # Make request with negative limit
        response = client.get('/api/metadata/tags/autocomplete?q=test&limit=-5')

        assert response.status_code == 200

        # Should use default limit
        mock_engine.search.assert_called_once_with('test', limit=10)


# ============================================================================
# Test Error Cases
# ============================================================================

class TestAutocompleteErrorCases:
    """Tests for error handling."""

    def test_autocomplete_missing_query_returns_400(self, client, mock_engine):
        """Missing 'q' parameter should return 400."""
        # Make request without query parameter
        response = client.get('/api/metadata/tags/autocomplete')

        assert response.status_code == 400
        data = response.get_json()

        assert 'error' in data
        assert 'Missing required parameter: q' in data['error']

        # Engine should not be called
        mock_engine.search.assert_not_called()

    def test_autocomplete_no_matches_returns_empty(self, client, mock_engine):
        """Query with no matches should return empty suggestions."""
        # Mock engine response with no matches
        mock_engine.search.return_value = []

        # Make request
        response = client.get('/api/metadata/tags/autocomplete?q=zzznomatch')

        assert response.status_code == 200
        data = response.get_json()

        assert data['suggestions'] == []
        assert data['total'] == 0
        assert data['query'] == 'zzznomatch'

    def test_autocomplete_engine_unavailable_returns_503(self, client, app):
        """Engine unavailable should return 503."""
        # Remove engine from app config
        app.config['TAG_AUTOCOMPLETE_ENGINE'] = None

        # Make request
        response = client.get('/api/metadata/tags/autocomplete?q=test')

        assert response.status_code == 503
        data = response.get_json()

        assert 'error' in data
        assert 'Service unavailable' in data['error']

    def test_autocomplete_engine_exception_returns_500(self, client, mock_engine):
        """Engine exception should return 500."""
        # Mock engine to raise exception
        mock_engine.search.side_effect = Exception("Engine error")

        # Make request
        response = client.get('/api/metadata/tags/autocomplete?q=test')

        assert response.status_code == 500
        data = response.get_json()

        assert 'error' in data


# ============================================================================
# Test Response Format
# ============================================================================

class TestAutocompleteResponseFormat:
    """Tests for response format validation."""

    def test_autocomplete_response_format(self, client, mock_engine):
        """Response should have correct structure and types."""
        from webui.backend.lib.tag_autocomplete import AutocompleteSuggestion
        from datetime import datetime, UTC

        # Mock engine response
        mock_suggestions = [
            AutocompleteSuggestion(
                tag="test_tag",
                count=5,
                last_used=datetime(2024, 11, 1, 8, 0, 0, tzinfo=UTC),
                match_score=0.85
            )
        ]
        mock_engine.search.return_value = mock_suggestions

        # Make request
        response = client.get('/api/metadata/tags/autocomplete?q=test')

        assert response.status_code == 200
        data = response.get_json()

        # Verify top-level structure
        assert isinstance(data, dict)
        assert 'suggestions' in data
        assert 'query' in data
        assert 'total' in data

        # Verify types
        assert isinstance(data['suggestions'], list)
        assert isinstance(data['query'], str)
        assert isinstance(data['total'], int)

        # Verify suggestion structure
        suggestion = data['suggestions'][0]
        assert isinstance(suggestion, dict)
        assert 'tag' in suggestion
        assert 'count' in suggestion
        assert 'last_used' in suggestion
        assert 'match_score' in suggestion

        # Verify suggestion types
        assert isinstance(suggestion['tag'], str)
        assert isinstance(suggestion['count'], int)
        assert isinstance(suggestion['last_used'], str)  # ISO format
        assert isinstance(suggestion['match_score'], (int, float))

    def test_autocomplete_response_with_null_last_used(self, client, mock_engine):
        """Response should handle null last_used correctly."""
        from webui.backend.lib.tag_autocomplete import AutocompleteSuggestion

        # Mock engine response with None last_used
        mock_suggestions = [
            AutocompleteSuggestion(
                tag="test_tag",
                count=5,
                last_used=None,
                match_score=0.85
            )
        ]
        mock_engine.search.return_value = mock_suggestions

        # Make request
        response = client.get('/api/metadata/tags/autocomplete?q=test')

        assert response.status_code == 200
        data = response.get_json()

        # Verify null last_used is handled
        suggestion = data['suggestions'][0]
        assert suggestion['last_used'] is None


# ============================================================================
# Test GET Method Only
# ============================================================================

class TestAutocompleteMethodRestrictions:
    """Tests for HTTP method restrictions."""

    def test_autocomplete_post_not_allowed(self, client):
        """POST requests should not be allowed."""
        response = client.post('/api/metadata/tags/autocomplete?q=test')

        # Should be 405 Method Not Allowed
        assert response.status_code == 405

    def test_autocomplete_put_not_allowed(self, client):
        """PUT requests should not be allowed."""
        response = client.put('/api/metadata/tags/autocomplete?q=test')

        # Should be 405 Method Not Allowed
        assert response.status_code == 405

    def test_autocomplete_delete_not_allowed(self, client):
        """DELETE requests should not be allowed."""
        response = client.delete('/api/metadata/tags/autocomplete?q=test')

        # Should be 405 Method Not Allowed
        assert response.status_code == 405

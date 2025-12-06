"""
Search API Routes

Provides REST endpoints for photo search functionality.

Endpoints:
- GET /api/photos/search - Search photos by query
- GET /api/photos/search/stats - Get search index statistics
- POST /api/photos/search/rebuild - Rebuild search index

Author: Mothbox Team
Date: 2024-12-06
"""

from flask import Blueprint, request, jsonify, current_app
from typing import Dict, Any, List

# Create blueprint
search_bp = Blueprint('search', __name__, url_prefix='/api/photos/search')

# Constants
MAX_LIMIT = 100
DEFAULT_LIMIT = 20
DEFAULT_OFFSET = 0


@search_bp.route('', methods=['GET'])
def search_photos():
    """
    Search photos by query string.

    Query Parameters:
        q (str, required): Search query
        limit (int, optional): Results per page (default: 20, max: 100)
        offset (int, optional): Skip N results (default: 0)

    Returns:
        200: Search results with pagination
        400: Invalid query or parameters
        503: Search service unavailable

    Example:
        GET /api/photos/search?q=moth&limit=20&offset=0

    Response:
        {
            "results": [...],
            "total": 45,
            "query": "moth",
            "parsed_query": "moth",
            "took_ms": 23.5,
            "pagination": {
                "limit": 20,
                "offset": 0,
                "has_next": true,
                "has_prev": false
            }
        }
    """
    # Get and validate query parameter
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({
            'error': 'Missing query',
            'message': "Query parameter 'q' is required"
        }), 400

    # Parse and validate limit parameter
    try:
        limit = int(request.args.get('limit', DEFAULT_LIMIT))
        # Cap at maximum
        limit = min(limit, MAX_LIMIT)
    except (ValueError, TypeError):
        return jsonify({
            'error': 'Invalid limit',
            'message': 'Limit must be an integer'
        }), 400

    # Parse and validate offset parameter
    try:
        offset = int(request.args.get('offset', DEFAULT_OFFSET))
        if offset < 0:
            return jsonify({
                'error': 'Invalid offset',
                'message': 'Offset must be non-negative'
            }), 400
    except (ValueError, TypeError):
        return jsonify({
            'error': 'Invalid offset',
            'message': 'Offset must be an integer'
        }), 400

    # Get search service from app context
    search_service = current_app.config.get('SEARCH_SERVICE')
    if not search_service:
        return jsonify({
            'error': 'Search service not available'
        }), 503

    # Execute search
    try:
        result = search_service.search(query, limit=limit, offset=offset)
    except Exception as e:
        return jsonify({
            'error': 'Search failed',
            'message': str(e)
        }), 500

    # Check if query was valid
    if not result.get('is_valid', True):
        return jsonify({
            'error': 'Invalid query',
            'message': result.get('error_message', 'Query parsing failed'),
            'query': query
        }), 400

    # Format results for API response
    formatted_results = _format_results(result.get('results', []))

    # Build response
    total = result.get('total', 0)
    response = {
        'results': formatted_results,
        'total': total,
        'query': query,
        'parsed_query': result.get('parsed_query', query),
        'took_ms': result.get('took_ms', 0),
        'pagination': {
            'limit': limit,
            'offset': offset,
            'has_next': offset + limit < total,
            'has_prev': offset > 0
        }
    }

    return jsonify(response), 200


@search_bp.route('/stats', methods=['GET'])
def search_stats():
    """
    Get search index statistics.

    Returns:
        200: Index statistics
        503: Search service unavailable

    Example:
        GET /api/photos/search/stats

    Response:
        {
            "document_count": 1234,
            "index_size_bytes": 245760,
            "db_path": "/var/lib/mothbox/cache/search.db"
        }
    """
    # Get search service from app context
    search_service = current_app.config.get('SEARCH_SERVICE')
    if not search_service:
        return jsonify({
            'error': 'Search service not available'
        }), 503

    try:
        stats = search_service.get_statistics()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({
            'error': 'Failed to get statistics',
            'message': str(e)
        }), 500


@search_bp.route('/rebuild', methods=['POST'])
def rebuild_index():
    """
    Rebuild the search index.

    This endpoint triggers a complete rebuild of the search index,
    scanning all photos and their metadata.

    Returns:
        200: Index rebuilt successfully
        503: Search service unavailable

    Example:
        POST /api/photos/search/rebuild

    Response:
        {
            "indexed": 1234,
            "errors": 0,
            "took_ms": 5432.1,
            "message": "Index rebuilt successfully"
        }
    """
    # Get search service from app context
    search_service = current_app.config.get('SEARCH_SERVICE')
    if not search_service:
        return jsonify({
            'error': 'Search service not available'
        }), 503

    try:
        stats = search_service.build_index()

        response = {
            'indexed': stats.get('indexed', 0),
            'errors': stats.get('errors', 0),
            'took_ms': stats.get('took_ms', 0),
            'message': 'Index rebuilt successfully'
        }

        return jsonify(response), 200
    except Exception as e:
        return jsonify({
            'error': 'Index rebuild failed',
            'message': str(e)
        }), 500


def _format_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Format search results for API response.

    Transforms internal search result format to API response format,
    adding thumbnail URLs and organizing metadata.

    Args:
        results: Raw search results from search service

    Returns:
        Formatted results with thumbnail URLs and metadata

    Example:
        Input: [{'filename': 'IMG_001.jpg', 'filepath': '2024-11-10/IMG_001.jpg', ...}]
        Output: [{'filename': 'IMG_001.jpg', 'path': '2024-11-10/IMG_001.jpg',
                  'thumbnail_url': '/api/gallery/thumbnail/2024-11-10/IMG_001.jpg', ...}]
    """
    formatted = []

    for result in results:
        filepath = result.get('filepath', '')

        formatted.append({
            'filename': result.get('filename', ''),
            'path': filepath,
            'thumbnail_url': f'/api/gallery/thumbnail/{filepath}',
            'metadata': result.get('metadata', {}),
            'score': result.get('score', 0),
            'matched_fields': result.get('matched_fields', [])
        })

    return formatted

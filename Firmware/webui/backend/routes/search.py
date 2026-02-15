"""
Search API Routes

Provides REST endpoints for photo search functionality.

Endpoints:
- GET /api/photos/search - Search photos by query
- GET /api/photos/search/stats - Get search index statistics
- POST /api/photos/search/rebuild - Full rebuild of search index
- POST /api/photos/search/sync - Incremental sync of search index
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

from flask import Blueprint, current_app, jsonify, request

from webui.backend.lib.error_codes import (
    HARDWARE_ERROR,
    SERVER_ERROR,
    VALIDATION_ERROR,
    error_response,
)

# Rate limiter setup (follows pattern from gallery.py)
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address)
except ImportError:
    # Stub for testing without flask_limiter
    class LimiterStub:
        def limit(self, *args, **kwargs):
            def decorator(f):
                return f

            return decorator

    limiter = LimiterStub()

# Create blueprint
search_bp = Blueprint("search", __name__, url_prefix="/api/photos/search")

# Constants
MAX_LIMIT = 100
DEFAULT_LIMIT = 20
DEFAULT_OFFSET = 0
MAX_QUERY_LENGTH = 500  # Prevent abuse with excessively long queries


@search_bp.route("", methods=["GET"])
@limiter.limit("60 per minute")  # Rate limit search queries
def search_photos():
    """
    Search photos by query string.

    Query Parameters:
        q (str, required): Search query (max 500 chars)
        limit (int, optional): Results per page (default: 20, max: 100)
        offset (int, optional): Skip N results (default: 0)

    Returns:
        200: Search results with pagination
        400: Invalid query or parameters
        429: Rate limit exceeded
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
    query = request.args.get("q", "").strip()
    if not query:
        return error_response(
            VALIDATION_ERROR, "Missing query", message="Query parameter 'q' is required"
        )

    # Validate query length to prevent abuse
    if len(query) > MAX_QUERY_LENGTH:
        return error_response(
            VALIDATION_ERROR,
            "Query too long",
            message=f"Query must be {MAX_QUERY_LENGTH} characters or less",
        )

    # Parse and validate limit parameter
    try:
        limit = int(request.args.get("limit", DEFAULT_LIMIT))
        # Cap at maximum
        limit = min(limit, MAX_LIMIT)
    except (ValueError, TypeError):
        return error_response(VALIDATION_ERROR, "Invalid limit", message="Limit must be an integer")

    # Parse and validate offset parameter
    try:
        offset = int(request.args.get("offset", DEFAULT_OFFSET))
        if offset < 0:
            return error_response(
                VALIDATION_ERROR, "Invalid offset", message="Offset must be a non-negative integer"
            )
    except (ValueError, TypeError):
        return error_response(
            VALIDATION_ERROR, "Invalid offset", message="Offset must be a non-negative integer"
        )

    # Get search service from app context
    search_service = current_app.config.get("SEARCH_SERVICE")
    if not search_service:
        return error_response(HARDWARE_ERROR, "Search service not available", 503)

    # Execute search
    try:
        result = search_service.search(query, limit=limit, offset=offset)
    except Exception:
        logger.exception("Search failed")
        return error_response(SERVER_ERROR, "Search failed", 500)

    # Check if query was valid
    if not result.get("is_valid", True):
        return error_response(
            VALIDATION_ERROR,
            "Invalid query",
            message=result.get("error_message", "Invalid query syntax"),
            query=query,
        )

    # Format results for API response
    formatted_results = _format_results(result.get("results", []))

    # Build response
    total = result.get("total", 0)
    response = {
        "results": formatted_results,
        "total": total,
        "query": query,
        "parsed_query": result.get("parsed_query", query),
        "took_ms": result.get("took_ms", 0),
        "pagination": {
            "limit": limit,
            "offset": offset,
            "has_next": offset + limit < total,
            "has_prev": offset > 0,
        },
    }

    return jsonify(response), 200


@search_bp.route("/stats", methods=["GET"])
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
    search_service = current_app.config.get("SEARCH_SERVICE")
    if not search_service:
        return error_response(HARDWARE_ERROR, "Search service not available", 503)

    try:
        stats = search_service.get_statistics()
        return jsonify(stats), 200
    except Exception:
        logger.exception("Failed to get search statistics")
        return error_response(SERVER_ERROR, "Failed to get statistics", 500)


@search_bp.route("/rebuild", methods=["POST"])
@limiter.limit("5 per minute")  # Rate limit expensive rebuild operation
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
    search_service = current_app.config.get("SEARCH_SERVICE")
    if not search_service:
        return error_response(HARDWARE_ERROR, "Search service not available", 503)

    try:
        stats = search_service.build_index()

        response = {
            "indexed": stats.get("indexed", 0),
            "errors": stats.get("errors", 0),
            "took_ms": stats.get("took_ms", 0),
            "message": "Index rebuilt successfully",
        }

        return jsonify(response), 200
    except Exception:
        logger.exception("Index rebuild failed")
        return error_response(SERVER_ERROR, "Index rebuild failed", 500)


@search_bp.route("/sync", methods=["POST"])
@limiter.limit("10 per minute")  # Rate limit sync operation
def sync_index():
    """
    Incrementally sync the search index.

    This endpoint performs an incremental update of the search index,
    only re-indexing photos that have changed since the last sync.
    Much more efficient than rebuild for large galleries.

    Returns:
        200: Index synced successfully
        503: Search service unavailable

    Example:
        POST /api/photos/search/sync

    Response:
        {
            "indexed": 5,
            "updated": 3,
            "deleted": 1,
            "unchanged": 1226,
            "errors": 0,
            "took_ms": 432.1,
            "message": "Index synced successfully"
        }
    """
    # Get search service from app context
    search_service = current_app.config.get("SEARCH_SERVICE")
    if not search_service:
        return error_response(HARDWARE_ERROR, "Search service not available", 503)

    try:
        stats = search_service.sync_index()

        response = {
            "indexed": stats.get("indexed", 0),
            "updated": stats.get("updated", 0),
            "deleted": stats.get("deleted", 0),
            "unchanged": stats.get("unchanged", 0),
            "errors": stats.get("errors", 0),
            "took_ms": stats.get("took_ms", 0),
            "message": "Index synced successfully",
        }

        return jsonify(response), 200
    except Exception:
        logger.exception("Index sync failed")
        return error_response(SERVER_ERROR, "Index sync failed", 500)


def _format_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Format search results for API response.

    Transforms internal search result format to API response format,
    adding thumbnail URLs and organizing metadata.

    Args:
        results: Raw search results from search service

    Returns:
        Formatted results with thumbnail URLs, metadata, and highlights

    Example:
        Input: [{'filename': 'IMG_001.jpg', 'filepath': '2024-11-10/IMG_001.jpg', ...}]
        Output: [{'filename': 'IMG_001.jpg', 'path': '2024-11-10/IMG_001.jpg',
                  'thumbnail_url': '/api/gallery/thumbnail/2024-11-10/IMG_001.jpg',
                  'highlights': {'tags': '<mark>luna</mark> moth'}, ...}]
    """
    formatted = []

    for result in results:
        filepath = result.get("filepath", "")

        formatted.append(
            {
                "filename": result.get("filename", ""),
                "path": filepath,
                "thumbnail_url": f"/api/gallery/thumbnail/{filepath}",
                "metadata": result.get("metadata", {}),
                "score": result.get("score", 0),
                "matched_fields": result.get("matched_fields", []),
                "highlights": result.get("highlights", {}),
            }
        )

    return formatted

# Metadata API Documentation

**Last Updated**: 2024-12-05
**Version**: Issue #124
**Base URL**: `/api/metadata`

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Error Responses](#error-responses)
4. [Tag Autocomplete](#tag-autocomplete)

---

## Overview

The Metadata API provides endpoints for tag management and metadata operations. This API is designed to support the photo tagging workflow in the Mothbox Gallery.

**Key Features**:
- Intelligent tag autocomplete with fuzzy matching
- Frequency-based ranking (commonly used tags appear first)
- Recency boost (recently used tags score higher)
- In-memory caching for fast responses

**Implementation**: `webui/backend/routes/metadata.py`

---

## Authentication

**Current Status**: No authentication required

**Security Measures**:
- CSRF tokens required for state-changing operations (POST/PUT/DELETE)
- Rate limiting: 60 requests per minute for autocomplete endpoint
- Input validation on all parameters

---

## Error Responses

### Standard Error Format

All error responses follow this JSON structure:

```json
{
  "error": "Human-readable error message"
}
```

### HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful request |
| 400 | Bad Request | Missing required parameter |
| 500 | Internal Server Error | Unexpected server error |
| 503 | Service Unavailable | Autocomplete engine not initialized |

---

## Tag Autocomplete

### Get Tag Suggestions

**Endpoint**: `GET /api/metadata/tags/autocomplete`

Returns intelligent tag suggestions based on fuzzy matching and frequency ranking.

#### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `q` | string | Yes | - | Search query (partial tag name) |
| `limit` | integer | No | 10 | Maximum suggestions to return (max: 50) |
| `exclude_tags` | string | No | - | Comma-separated tags to exclude from results |

#### Response Format

```json
{
  "suggestions": [
    {
      "tag": "luna_moth",
      "count": 45,
      "last_used": "2024-11-05T10:30:00Z",
      "match_score": 0.95
    },
    {
      "tag": "sphinx_moth",
      "count": 23,
      "last_used": "2024-11-01T08:00:00Z",
      "match_score": 0.82
    }
  ],
  "query": "moth",
  "total": 2
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `suggestions` | array | List of tag suggestions |
| `suggestions[].tag` | string | Tag name |
| `suggestions[].count` | integer | Number of photos with this tag |
| `suggestions[].last_used` | string | ISO 8601 timestamp of most recent use |
| `suggestions[].match_score` | float | Combined ranking score (0-1, higher is better) |
| `query` | string | The search query |
| `total` | integer | Number of suggestions returned |

#### Ranking Algorithm

The `match_score` combines multiple factors:

1. **Fuzzy Match** (0-1.0): Uses `rapidfuzz.fuzz.partial_ratio` for substring matching
2. **Exact Prefix Bonus** (+2.0): Tags starting with the query get a boost
3. **Frequency Boost** (0-0.3): Log-scaled based on usage count
4. **Recency Boost** (0-0.2): Exponential decay with 30-day half-life

#### Example Requests

**Basic search:**
```bash
curl "http://localhost:5000/api/metadata/tags/autocomplete?q=moth"
```

**With limit and exclusions:**
```bash
curl "http://localhost:5000/api/metadata/tags/autocomplete?q=moth&limit=5&exclude_tags=luna_moth,hawk_moth"
```

**Empty query (returns top tags by frequency):**
```bash
curl "http://localhost:5000/api/metadata/tags/autocomplete?q="
```

#### Performance

- **Target**: <50ms for 10,000 tags
- **Caching**: In-memory index with 5-minute TTL
- **Rate Limiting**: 60 requests per minute

#### Error Examples

**Missing query parameter:**
```json
{
  "error": "Missing required parameter: q"
}
```

**Service unavailable:**
```json
{
  "error": "Tag autocomplete service is not available"
}
```

---

## Related Documentation

- [Sidecar Metadata API](./sidecar-metadata.md) - CRUD operations for photo metadata
- [Gallery API](./gallery.md) - Photo listing and serving

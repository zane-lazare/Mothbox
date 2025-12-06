# Search API

Full-text photo search API using SQLite FTS5.

## Overview

The Search API provides full-text search capabilities for photos in the Mothbox gallery. It supports:

- Simple text search across all metadata fields
- Field-specific queries (tags, species, notes, filename)
- Boolean operators (AND, OR, NOT)
- Phrase search with quotes
- Prefix/wildcard search
- Date range filtering
- Relevance-based ranking

## Performance

- **Target**: <200ms for 10,000 photos
- **Actual**: ~30ms for 10,000 photos (6x faster than target)
- **Query parsing**: <0.02ms

## Endpoints

### Search Photos

```
GET /api/photos/search
```

Search photos by query string.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| q | string | Yes | - | Search query |
| limit | integer | No | 20 | Results per page (max: 100) |
| offset | integer | No | 0 | Results to skip |

**Example Request:**
```bash
curl "http://localhost:5000/api/photos/search?q=tag:moth&limit=20"
```

**Example Response:**
```json
{
  "results": [
    {
      "filename": "moth_2024_11_10__10_30_00.jpg",
      "path": "2024-11/moth_2024_11_10__10_30_00.jpg",
      "thumbnail_url": "/api/gallery/thumbnail/2024-11/moth_2024_11_10__10_30_00.jpg",
      "metadata": {
        "tags": ["moth", "luna_moth", "nocturnal"],
        "species": "Actias luna",
        "species_common_name": "Luna Moth",
        "notes": "Large specimen near UV light"
      },
      "score": 2.45,
      "matched_fields": ["tags", "species"]
    }
  ],
  "total": 45,
  "query": "tag:moth",
  "parsed_query": "tags:moth",
  "took_ms": 23.5,
  "pagination": {
    "limit": 20,
    "offset": 0,
    "has_next": true,
    "has_prev": false
  }
}
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 400 | Invalid query or missing parameters |
| 503 | Search service unavailable |

### Get Search Statistics

```
GET /api/photos/search/stats
```

Returns search index statistics.

**Example Response:**
```json
{
  "document_count": 1234,
  "index_size_bytes": 245760,
  "db_path": "/var/lib/mothbox/cache/search.db"
}
```

### Rebuild Search Index

```
POST /api/photos/search/rebuild
```

Rebuilds the search index from all photos with sidecars.

**Example Response:**
```json
{
  "indexed": 1234,
  "errors": 0,
  "took_ms": 5432.1,
  "message": "Index rebuilt successfully"
}
```

## Query Syntax

### Simple Search
```
moth                    # Search all fields for "moth"
luna moth               # Search for "luna" AND "moth"
```

### Field-Specific Search
```
tag:moth                # Search tags field
tags:moth               # Same as tag:
species:actias          # Search species field
notes:specimen          # Search notes field
filename:IMG            # Search filename
name:luna               # Search common name
```

### Boolean Operators
```
moth AND butterfly      # Both terms required
moth OR butterfly       # Either term
moth NOT butterfly      # Exclude term
moth -butterfly         # Same as NOT (shorthand)
```

### Phrase Search
```
"luna moth"             # Exact phrase
species:"Actias luna"   # Phrase in specific field
```

### Prefix/Wildcard
```
luna*                   # Prefix match
tag:noc*                # Prefix in field
```

### Date Range
```
date:2024-11-01                    # Exact date
date:2024-11-01..2024-11-06        # Date range
date:>2024-01-01                   # After date
date:<2024-12-31                   # Before date
```

### Complex Queries
```
tag:moth AND species:actias
"luna moth" tag:nocturnal
tag:moth OR tag:butterfly species:papilio
date:>2024-01-01 tag:nocturnal -butterfly
```

## Ranking

Results are ranked by relevance using:

1. **BM25 score** from SQLite FTS5
2. **Field weights:**
   - tags: 2.0 (highest priority)
   - species: 1.8
   - species_common_name: 1.5
   - filename: 1.2
   - notes: 1.0
   - custom_fields: 0.8
   - date: 0.5

3. **Match type multipliers:**
   - phrase: 1.1 (boost for exact phrases)
   - exact: 1.0
   - prefix: 0.9

## Frontend Usage

### React Hook

```jsx
import { usePhotoSearch } from '@/hooks/usePhotoSearch'

function Gallery() {
  const [query, setQuery] = useState('')

  const {
    results,
    total,
    isLoading,
    tookMs,
    pagination
  } = usePhotoSearch(query, {
    limit: 20,
    debounceMs: 300
  })

  return (
    <div>
      <input
        value={query}
        onChange={e => setQuery(e.target.value)}
      />
      {isLoading ? 'Searching...' : `${total} results in ${tookMs}ms`}
      {results.map(photo => (
        <img key={photo.path} src={photo.thumbnail_url} />
      ))}
    </div>
  )
}
```

### SearchBar Component

```jsx
import { SearchBar } from '@/components/gallery/SearchBar'

<SearchBar
  value={query}
  onChange={setQuery}
  onSearch={(q) => console.log('Search:', q)}
  onClear={() => setQuery('')}
  isLoading={isLoading}
/>
```

### Advanced Search Builder

```jsx
import { AdvancedSearchBuilder } from '@/components/gallery/AdvancedSearchBuilder'

<AdvancedSearchBuilder
  onQueryChange={(q) => setQuery(q)}
  onClose={() => setShowBuilder(false)}
  initialQuery={query}
/>
```

## Index Management

### Automatic Updates

The search index automatically updates when:
- Metadata is created via SidecarService
- Metadata is updated
- Metadata is deleted

### Manual Rebuild

Rebuild the index via API:
```bash
curl -X POST http://localhost:5000/api/photos/search/rebuild
```

Or programmatically:
```python
from webui.backend.services.search_service import SearchService

service = SearchService()
stats = service.build_index()
print(f"Indexed {stats['indexed']} photos")
```

## Configuration

### Index Location

Default: `DATA_DIR/cache/search.db`

Configure via `SearchServiceConfig`:
```python
from webui.backend.services.search_service import SearchService, SearchServiceConfig

config = SearchServiceConfig(
    db_path=Path("/custom/path/search.db"),
    auto_rebuild=False,
    field_weights={'tags': 3.0}  # Custom weights
)
service = SearchService(config)
```

## Testing

```bash
# Unit tests
MOTHBOX_ENV=test pytest Tests/unit/test_search_engine.py -v
MOTHBOX_ENV=test pytest Tests/unit/test_search_query_parser.py -v
MOTHBOX_ENV=test pytest Tests/unit/test_search_service.py -v
MOTHBOX_ENV=test pytest Tests/unit/test_search_api.py -v

# Integration tests
MOTHBOX_ENV=test pytest Tests/integration/test_search_workflow.py -v

# Performance tests
MOTHBOX_ENV=test pytest Tests/performance/test_search_performance.py -v -s
```

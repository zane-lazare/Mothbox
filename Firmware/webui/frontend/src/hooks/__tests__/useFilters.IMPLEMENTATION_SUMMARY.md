# useFilters Hook Implementation Summary

## Files Created

### 1. Hook Implementation
**File**: `/home/zane/projects/Mothbox/Firmware/webui/frontend/src/hooks/useFilters.js`
- **Lines**: 203
- **Size**: 5.2KB

### 2. Test Suite
**File**: `/home/zane/projects/Mothbox/Firmware/webui/frontend/src/hooks/__tests__/useFilters.test.jsx`
- **Lines**: 521
- **Size**: 17KB

## Hook Features

### `useFilters()`
Main hook that provides comprehensive filter management:

#### Returned Values:
1. **All context state** (spread from FilterContext):
   - `dateRange`, `tags`, `species`, `fileTypes`, `cameraSettings`, `notes`, `customFields`
   - `setDateRange()`, `setTags()`, `setSpecies()`, etc.
   - `clearAllFilters()`

2. **Computed values** (memoized):
   - `searchQuery` - FTS5 query string for search API
   - `hasFilters` - Boolean indicating if any filters are active
   - `activeFilterCount` - Number of active filter types
   - `filterSummaries` - Array of filter summaries for display chips

3. **Utility functions**:
   - `isFilterActive(filterType)` - Check if specific filter type is active

#### Filter Types Supported:
- `dateRange` - Preset or custom date ranges
- `tags` - Tag selection with match mode (any/all)
- `species` - Species selection + includeUnidentified
- `fileTypes` - File type filters (jpg, png, etc.)
- `cameraSettings` - ISO, aperture, shutter speed ranges
- `notes` - Has notes flag + keyword search
- `customFields` - Key-value custom metadata

### `useDebouncedFilters(delay = 300)`
Debounced version for performance optimization:

#### Parameters:
- `delay` - Debounce delay in milliseconds (default: 300)

#### Returned Values:
- `debouncedQuery` - Debounced search query string
- `hasFilters` - Boolean (immediate, not debounced)
- `activeFilterCount` - Number (immediate, not debounced)
- `isDebouncing` - Boolean indicating if query is still debouncing

#### Use Cases:
- Prevent excessive API calls during rapid filter adjustments
- Show loading state while debouncing (`isDebouncing`)
- Maintain UI responsiveness with immediate filter counts

## Test Coverage

### Test Suites:
1. **Basic Functionality** (5 tests)
   - Context value propagation
   - Computed value generation
   - Query builder integration

2. **isFilterActive** (20 tests)
   - All filter types (date, tags, species, fileTypes, camera, notes, custom)
   - Active/inactive detection
   - Edge cases (empty values, null handling)
   - Unknown filter types

3. **Reactivity** (4 tests)
   - Recomputation on filter changes
   - Memoization behavior

4. **useDebouncedFilters** (6 tests)
   - Default delay (300ms)
   - Custom delay
   - Debounce cancellation
   - Timer behavior
   - State maintenance during debounce

### Total Tests: 35

## Integration Points

### Dependencies:
1. **FilterContext** (to be created):
   ```javascript
   import { useFilterContext } from '../contexts/FilterContext'
   ```

2. **filterQueryBuilder utilities** (existing):
   ```javascript
   import {
     buildFilterQuery,
     hasActiveFilters,
     countActiveFilters,
     getActiveFilterSummaries,
   } from '../utils/filterQueryBuilder'
   ```

### Usage Example:

```javascript
import { useFilters, useDebouncedFilters } from '@/hooks/useFilters'

function FilterDrawer() {
  const {
    // State
    tags,
    dateRange,
    species,

    // Actions
    setTags,
    clearAllFilters,

    // Computed
    searchQuery,
    hasFilters,
    activeFilterCount,
    filterSummaries,

    // Utils
    isFilterActive,
  } = useFilters()

  return (
    <div>
      <h2>Filters ({activeFilterCount})</h2>

      {filterSummaries.map(summary => (
        <Chip key={summary.type} label={summary.label} value={summary.value} />
      ))}

      {hasFilters && (
        <button onClick={clearAllFilters}>Clear All</button>
      )}
    </div>
  )
}

function SearchBar() {
  const { debouncedQuery, isDebouncing } = useDebouncedFilters(500)

  useEffect(() => {
    if (!isDebouncing && debouncedQuery) {
      // Perform API search
      searchPhotos(debouncedQuery)
    }
  }, [debouncedQuery, isDebouncing])

  return isDebouncing ? <Spinner /> : <SearchResults />
}
```

## Implementation Notes

1. **Memoization Strategy**:
   - All computed values use `useMemo` with proper dependencies
   - Prevents unnecessary recalculations
   - Optimized for React rendering performance

2. **Type Safety**:
   - All filter types validated in `isFilterActive()`
   - Null/undefined handling throughout
   - Empty value checks for customFields

3. **Debounce Pattern**:
   - Uses `useState` + `useEffect` + `setTimeout`
   - Cleanup function prevents memory leaks
   - Timer cancellation on unmount or dependency change

4. **Test Strategy**:
   - Mock FilterContext at module level
   - Spy on filterQueryBuilder functions (not full mock)
   - Use `vi.useFakeTimers()` for debounce testing
   - Comprehensive edge case coverage

## Next Steps

To complete the filter drawer feature:

1. **Create FilterContext** (`src/contexts/FilterContext.jsx`):
   - State management for all filter types
   - Action creators (setters)
   - `clearAllFilters()` implementation
   - Context provider wrapper

2. **Create Filter UI Components**:
   - `FilterDrawer.jsx` - Main drawer component
   - `DateRangeFilter.jsx` - Date selection
   - `TagFilter.jsx` - Tag multi-select
   - `SpeciesFilter.jsx` - Species multi-select
   - `CameraSettingsFilter.jsx` - Range sliders
   - `NotesFilter.jsx` - Has notes toggle + keyword input
   - `FilterChips.jsx` - Active filter display

3. **Integrate with Gallery**:
   - Wrap Gallery with FilterProvider
   - Connect search API with debounced query
   - Add drawer toggle button
   - Handle URL query params for shareable filters

## Performance Considerations

- **Memoization**: Prevents expensive recalculations
- **Debouncing**: Reduces API calls (default 300ms)
- **Selective dependency arrays**: Only recompute when relevant state changes
- **Spread operator efficiency**: Context spreading is shallow (fast)

## Browser Compatibility

- React 18+ required (`useMemo`, `useEffect`)
- ES6+ syntax (arrow functions, spread operator, template literals)
- Modern timer APIs (`setTimeout`, `clearTimeout`)

## File Locations

```
webui/frontend/src/
├── hooks/
│   ├── useFilters.js                           # Main implementation
│   └── __tests__/
│       ├── useFilters.test.jsx                  # Test suite
│       └── useFilters.IMPLEMENTATION_SUMMARY.md # This file
├── contexts/
│   └── FilterContext.jsx                        # TODO: Create
├── utils/
│   └── filterQueryBuilder.js                    # Already exists
└── components/
    └── filters/                                 # TODO: Create
        ├── FilterDrawer.jsx
        ├── DateRangeFilter.jsx
        ├── TagFilter.jsx
        └── ...
```

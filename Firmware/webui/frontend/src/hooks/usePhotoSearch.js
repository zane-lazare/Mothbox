import { useQuery } from '@tanstack/react-query'
import { useState, useEffect, useMemo } from 'react'
import { searchPhotos } from '../utils/api'

const DEFAULT_DEBOUNCE_MS = 300
const DEFAULT_LIMIT = 20

/**
 * Custom hook for searching photos with debouncing and caching
 *
 * Provides full-text search of photos with automatic debouncing to reduce
 * API calls during typing, intelligent caching, and pagination support.
 *
 * @param {string} query - Search query string
 * @param {Object} options - Configuration options
 * @param {number} [options.limit=20] - Results per page
 * @param {number} [options.offset=0] - Results offset for pagination
 * @param {number} [options.debounceMs=300] - Debounce delay in milliseconds
 * @param {boolean} [options.enabled=true] - Enable/disable the hook
 * @returns {Object} Search state and helpers
 *   - results: Array of search result objects
 *   - total: Total number of matching photos
 *   - tookMs: Query execution time in milliseconds
 *   - parsedQuery: Parsed FTS5 query
 *   - pagination: Pagination state (limit, offset, hasNext, hasPrev)
 *   - isLoading: Boolean indicating if query is loading
 *   - isError: Boolean indicating if error occurred
 *   - error: Error object if error occurred
 *   - isFetching: Boolean indicating if query is fetching
 *   - refetch: Function to force refetch
 *
 * @example
 * const { results, total, isLoading } = usePhotoSearch('moth')
 *
 * @example
 * // With custom options
 * const { results, pagination } = usePhotoSearch('luna moth', {
 *   limit: 10,
 *   offset: 0,
 *   debounceMs: 500,
 *   enabled: isInputFocused
 * })
 */
export function usePhotoSearch(query, options = {}) {
  const {
    limit = DEFAULT_LIMIT,
    offset = 0,
    debounceMs = DEFAULT_DEBOUNCE_MS,
    enabled = true
  } = options

  // Debounced query value
  const [debouncedQuery, setDebouncedQuery] = useState(query)

  // Debounce the query input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query)
    }, debounceMs)

    return () => clearTimeout(timer)
  }, [query, debounceMs])

  // Only enable query when we have content
  const shouldFetch = useMemo(() => {
    return enabled && debouncedQuery.trim().length > 0
  }, [enabled, debouncedQuery])

  // Fetch search results
  const { data, isLoading, isError, error, isFetching, refetch } = useQuery({
    // Query key: unique identifier for this query in the cache
    queryKey: ['photoSearch', debouncedQuery, limit, offset],

    // Query function: fetches the search results from the API
    queryFn: () => searchPhotos(debouncedQuery, { limit, offset }),

    // Only fetch if query meets requirements
    enabled: shouldFetch,

    // Cache configuration
    staleTime: 30000, // Cache for 30 seconds
    gcTime: 5 * 60 * 1000, // Keep in cache for 5 minutes
  })

  return useMemo(() => ({
    results: data?.results ?? [],
    total: data?.total ?? 0,
    tookMs: data?.took_ms ?? 0,
    parsedQuery: data?.parsed_query ?? '',
    pagination: {
      limit: data?.pagination?.limit ?? limit,
      offset: data?.pagination?.offset ?? offset,
      hasNext: data?.pagination?.has_next ?? false,
      hasPrev: data?.pagination?.has_prev ?? false
    },
    isLoading,
    isError,
    error,
    isFetching,
    refetch
  }), [data, limit, offset, isLoading, isError, error, isFetching, refetch])
}

import { useQuery, UseQueryResult } from '@tanstack/react-query'
import { useState, useEffect, useMemo } from 'react'
import { searchPhotos } from '../utils/api'

const DEFAULT_DEBOUNCE_MS = 300
const DEFAULT_LIMIT = 20

interface SearchResult {
  path: string
  filename: string
  score: number
  snippet?: string
}

interface SearchPagination {
  limit: number
  offset: number
  has_next: boolean
  has_prev: boolean
}

interface SearchData {
  results: SearchResult[]
  total: number
  took_ms: number
  parsed_query: string
  pagination: SearchPagination
}

export interface PhotoSearchOptions {
  limit?: number
  offset?: number
  debounceMs?: number
  enabled?: boolean
}

export interface UsePhotoSearchResult {
  results: SearchResult[]
  total: number
  tookMs: number
  parsedQuery: string
  pagination: SearchPagination
  isLoading: boolean
  isError: boolean
  error: Error | null
  isFetching: boolean
  refetch: () => void
}

/**
 * Custom hook for searching photos with debouncing and caching
 *
 * Provides full-text search of photos with automatic debouncing to reduce
 * API calls during typing, intelligent caching, and pagination support.
 *
 * @param query - Search query string
 * @param options - Configuration options
 * @param options.limit - Results per page
 * @param options.offset - Results offset for pagination
 * @param options.debounceMs - Debounce delay in milliseconds
 * @param options.enabled - Enable/disable the hook
 * @returns Search state and helpers
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
export function usePhotoSearch(
  query: string,
  options: PhotoSearchOptions = {}
): UsePhotoSearchResult {
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
  const { data, isLoading, isError, error, isFetching, refetch }: UseQueryResult<SearchData, Error> = useQuery({
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

import { useQuery } from '@tanstack/react-query'
import { useState, useEffect, useMemo } from 'react'
import { getTagAutocomplete } from '../utils/api'
import { TAG_AUTOCOMPLETE_CONFIG } from '../constants/config'

/**
 * Custom hook for tag autocomplete suggestions
 *
 * Fetches tag suggestions from the backend with debouncing, minimum character
 * requirements, and caching. Returns suggestions based on fuzzy matching.
 *
 * @param {string} query - The search query string
 * @param {Object} options - Configuration options
 * @param {number} [options.limit=10] - Maximum number of suggestions to return
 * @param {number} [options.minChars=2] - Minimum characters before fetching
 * @param {number} [options.debounceMs=200] - Debounce delay in milliseconds
 * @param {boolean} [options.enabled=true] - Enable/disable the hook
 * @returns {Object} TanStack Query result object containing:
 *   - suggestions: Array of suggestion objects { tag, count, last_used, match_score }
 *   - isLoading: Boolean indicating if the query is currently loading
 *   - isError: Boolean indicating if an error occurred
 *   - error: Error object if an error occurred, null otherwise
 *
 * @example
 * const { suggestions, isLoading, isError } = useTagAutocomplete('moth')
 *
 * if (isLoading) return <div>Loading suggestions...</div>
 * if (isError) return <div>Error loading suggestions</div>
 * if (suggestions.length > 0) {
 *   return (
 *     <ul>
 *       {suggestions.map(({ tag, count }) => (
 *         <li key={tag}>{tag} ({count})</li>
 *       ))}
 *     </ul>
 *   )
 * }
 *
 * @example
 * // With custom options
 * const { suggestions } = useTagAutocomplete('mo', {
 *   limit: 5,
 *   minChars: 3,
 *   debounceMs: 300,
 *   enabled: isInputFocused
 * })
 */
export default function useTagAutocomplete(query, options = {}) {
  const {
    limit = TAG_AUTOCOMPLETE_CONFIG.MAX_SUGGESTIONS,
    minChars = TAG_AUTOCOMPLETE_CONFIG.MIN_CHARS,
    debounceMs = TAG_AUTOCOMPLETE_CONFIG.DEBOUNCE_MS,
    enabled = true,
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

  // Check if query meets minimum character requirement
  const shouldFetch = useMemo(() => {
    return enabled && debouncedQuery.length >= minChars
  }, [enabled, debouncedQuery, minChars])

  // Fetch autocomplete suggestions
  const queryResult = useQuery({
    // Query key: unique identifier for this query in the cache
    queryKey: ['tagAutocomplete', debouncedQuery, limit],

    // Query function: fetches the suggestions from the API
    queryFn: async () => {
      const response = await getTagAutocomplete(debouncedQuery, limit)
      return response.data
    },

    // Only fetch if query meets minimum character requirement
    enabled: shouldFetch,

    // Cache configuration (from centralized config)
    staleTime: TAG_AUTOCOMPLETE_CONFIG.CACHE_STALE_TIME,
    gcTime: TAG_AUTOCOMPLETE_CONFIG.CACHE_GC_TIME,
  })

  // Return normalized result with empty array as default for suggestions
  // Defensively handle both array data and object with suggestions property
  return {
    suggestions: queryResult.data?.suggestions || queryResult.data || [],
    isLoading: queryResult.isLoading,
    isError: queryResult.isError,
    error: queryResult.error,
  }
}

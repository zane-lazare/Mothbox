import { useQuery } from '@tanstack/react-query'
import { useState, useEffect, useMemo } from 'react'
import { getTagAutocomplete } from '../utils/api'
import { TAG_AUTOCOMPLETE_CONFIG } from '../constants/config'

/**
 * Tag suggestion object returned by the hook
 */
export interface TagSuggestion {
  /** Tag name */
  name: string
  /** Number of times this tag appears in photos */
  count: number
  /** Match score from fuzzy matching (higher = better match) */
  score: number
}

/**
 * Raw API response suggestion object
 */
interface ApiTagSuggestion {
  /** Tag name from API */
  tag: string
  /** Usage count */
  count: number
  /** Match score */
  match_score: number
}

/**
 * API response structure
 */
interface TagAutocompleteResponse {
  suggestions: ApiTagSuggestion[]
  query: string
  total: number
}

/**
 * Hook configuration options
 */
export interface UseTagAutocompleteOptions {
  /** Maximum number of suggestions to return (default: 10) */
  limit?: number
  /** Minimum characters before fetching (default: 2) */
  minChars?: number
  /** Debounce delay in milliseconds (default: 200) */
  debounceMs?: number
  /** Enable/disable the hook (default: true) */
  enabled?: boolean
}

/**
 * Hook return type
 */
export interface UseTagAutocompleteResult {
  /** Array of normalized tag suggestions */
  suggestions: TagSuggestion[]
  /** Whether the query is currently loading */
  isLoading: boolean
  /** Whether an error occurred */
  isError: boolean
  /** Error object if an error occurred, null otherwise */
  error: Error | null
}

/**
 * Custom hook for tag autocomplete suggestions
 *
 * Fetches tag suggestions from the backend with debouncing, minimum character
 * requirements, and caching. Returns suggestions based on fuzzy matching.
 *
 * The hook normalizes API responses to use consistent property names:
 * - API returns: { tag, count, last_used, match_score }
 * - Hook returns: { name, count, score } (compatible with component expectations)
 *
 * @param query - The search query string
 * @param options - Configuration options
 * @param options.limit - Maximum number of suggestions to return (default: 10)
 * @param options.minChars - Minimum characters before fetching (default: 2)
 * @param options.debounceMs - Debounce delay in milliseconds (default: 200)
 * @param options.enabled - Enable/disable the hook (default: true)
 * @returns TanStack Query result object containing:
 *   - suggestions: Array of suggestion objects { name, count, score }
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
 *       {suggestions.map(({ name, count }) => (
 *         <li key={name}>{name} ({count})</li>
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
export default function useTagAutocomplete(
  query: string,
  options: UseTagAutocompleteOptions = {}
): UseTagAutocompleteResult {
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
      return response.data as TagAutocompleteResponse
    },

    // Only fetch if query meets minimum character requirement
    enabled: shouldFetch,

    // Cache configuration (from centralized config)
    staleTime: TAG_AUTOCOMPLETE_CONFIG.CACHE_STALE_TIME,
    gcTime: TAG_AUTOCOMPLETE_CONFIG.CACHE_GC_TIME,
  })

  // Normalize API response: { tag, count, match_score } -> { name, count, score }
  // This aligns with component expectations and the deprecated tags prop format
  const rawSuggestions = queryResult.data?.suggestions ?? []
  const normalizedSuggestions: TagSuggestion[] = rawSuggestions.map((s) => ({
    name: s.tag,
    count: s.count,
    score: s.match_score,
  }))

  return {
    suggestions: normalizedSuggestions,
    isLoading: queryResult.isLoading,
    isError: queryResult.isError,
    error: queryResult.error,
  }
}

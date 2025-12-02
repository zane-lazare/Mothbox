import { useQuery } from '@tanstack/react-query'
import { getAllTags } from '../utils/api'

/**
 * Custom hook for fetching all tags from sidecar metadata
 *
 * Fetches a list of all tags from the sidecar API with optional sorting,
 * ordering, and limiting. The hook uses TanStack Query for caching,
 * loading states, and error handling.
 *
 * @param {Object} params - Query parameters
 * @param {string} [params.sort] - Sort field ('name' or 'count')
 * @param {string} [params.order] - Sort order ('asc' or 'desc')
 * @param {number} [params.limit] - Maximum tags to return
 * @returns {Object} TanStack Query result object containing:
 *   - data: Tags data object with tags array and total count
 *   - isLoading: Boolean indicating if the query is currently loading
 *   - isError: Boolean indicating if an error occurred
 *   - isSuccess: Boolean indicating if the query was successful
 *   - error: Error object if an error occurred, null otherwise
 *   - refetch: Function to manually trigger a refetch
 *
 * @example
 * const { data, isLoading, isError, error, refetch } = useTags()
 *
 * if (isLoading) return <div>Loading tags...</div>
 * if (isError) return <div>Error: {error.message}</div>
 * if (data) {
 *   return (
 *     <ul>
 *       {data.tags.map(tag => (
 *         <li key={tag.name}>{tag.name} ({tag.count})</li>
 *       ))}
 *     </ul>
 *   )
 * }
 *
 * @example
 * // With sorting
 * const { data } = useTags({ sort: 'count', order: 'desc', limit: 10 })
 * // Returns top 10 tags sorted by count in descending order
 */
export default function useTags(params = {}) {
  // Normalize query key to ensure consistent cache keys regardless of
  // property order in params object (e.g., { sort, order } vs { order, sort })
  const normalizedParams = {
    sort: params?.sort,
    order: params?.order,
    limit: params?.limit,
  }

  return useQuery({
    // Query key: unique identifier for this query in the cache
    // Format: ['tags', normalizedParams] - explicitly ordered for cache consistency
    queryKey: ['tags', normalizedParams],

    // Query function: fetches the tags from the API
    queryFn: async () => {
      // Fetch tags from backend using centralized API client
      // This automatically includes CSRF tokens, base URL, and error handling
      const response = await getAllTags(params)

      // Return the data from axios response
      return response.data
    },

    // Cache configuration
    // staleTime: How long data is considered fresh (5 minutes)
    // After this time, data is marked as stale and will be refetched in the background
    staleTime: 5 * 60 * 1000, // 5 minutes in milliseconds

    // gcTime: How long inactive data stays in cache (10 minutes)
    // After this time, unused cached data is garbage collected
    gcTime: 10 * 60 * 1000, // 10 minutes in milliseconds
  })
}

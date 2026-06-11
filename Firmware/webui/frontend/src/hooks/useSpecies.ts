import { useMemo } from 'react'
import { useQuery, UseQueryResult } from '@tanstack/react-query'
import { getAllSpecies } from '../utils/api'

export interface Species {
  name: string
  count: number
}

export interface SpeciesData {
  species: Species[]
  total: number
}

export interface SpeciesParams {
  sort?: 'name' | 'count'
  order?: 'asc' | 'desc'
  limit?: number
}

export interface UseSpeciesResult {
  species: Species[]
  isLoading: boolean
  isError: boolean
  error: Error | null
  refetch: () => void
  filteredSpecies: (searchTerm: string) => Species[]
}

/**
 * Custom hook for fetching all species from sidecar metadata
 *
 * Fetches a list of all species from the sidecar API with optional sorting,
 * ordering, and limiting. The hook uses TanStack Query for caching,
 * loading states, and error handling.
 *
 * @param params - Query parameters
 * @param params.sort - Sort field ('name' or 'count')
 * @param params.order - Sort order ('asc' or 'desc')
 * @param params.limit - Maximum species to return
 * @returns Enhanced query result object
 *
 * @example
 * const { species, isLoading, isError, error, refetch, filteredSpecies } = useSpecies()
 *
 * if (isLoading) return <div>Loading species...</div>
 * if (isError) return <div>Error: {error.message}</div>
 *
 * return (
 *   <ul>
 *     {species.map(s => (
 *       <li key={s.name}>{s.name} ({s.count})</li>
 *     ))}
 *   </ul>
 * )
 *
 * @example
 * // With filtering
 * const { species, filteredSpecies } = useSpecies()
 * const moonMoths = filteredSpecies('luna') // Case-insensitive partial match
 *
 * @example
 * // With sorting
 * const { species } = useSpecies({ sort: 'count', order: 'desc', limit: 10 })
 * // Returns top 10 species sorted by count in descending order
 */
export default function useSpecies(params: SpeciesParams = {}): UseSpeciesResult {
  // Normalize query key to ensure consistent cache keys regardless of
  // property order in params object (e.g., { sort, order } vs { order, sort })
  const normalizedParams = {
    sort: params?.sort,
    order: params?.order,
    limit: params?.limit,
  }

  const query: UseQueryResult<SpeciesData, Error> = useQuery({
    // Query key: unique identifier for this query in the cache
    // Format: ['species', normalizedParams] - explicitly ordered for cache consistency
    queryKey: ['species', normalizedParams],

    // Query function: fetches the species from the API
    queryFn: async () => {
      // Fetch species from backend using centralized API client
      // This automatically includes CSRF tokens, base URL, and error handling
      const response = await getAllSpecies(params)

      // Return the data from axios response
      return response.data
    },

    // Cache configuration
    // staleTime: How long data is considered fresh (60 seconds)
    // After this time, data is marked as stale and will be refetched in the background
    staleTime: 60 * 1000, // 60 seconds in milliseconds

    // gcTime: How long inactive data stays in cache (5 minutes)
    // After this time, unused cached data is garbage collected
    gcTime: 5 * 60 * 1000, // 5 minutes in milliseconds
  })

  // Extract species array from data or provide empty array while loading
  const species = useMemo(() => {
    return query.data?.species || []
  }, [query.data])

  // Helper function to filter species by search term (case-insensitive, partial match)
  const filteredSpecies = useMemo(() => {
    return (searchTerm: string): Species[] => {
      if (!searchTerm || searchTerm.trim() === '') {
        return species
      }

      const normalizedSearch = searchTerm.toLowerCase().trim()
      return species.filter(s =>
        s.name.toLowerCase().includes(normalizedSearch)
      )
    }
  }, [species])

  return {
    species,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
    filteredSpecies,
  }
}

/**
 * Type declarations for useSpecies.js
 *
 * Provides TypeScript types during the gradual migration.
 * IMPORTANT: Keep in sync with useSpecies.js.
 */

interface SpeciesData {
  name: string
  count: number
}

interface UseSpeciesParams {
  sort?: string
  order?: string
  limit?: number
}

interface UseSpeciesResult {
  species: SpeciesData[]
  isLoading: boolean
  isError: boolean
  error: Error | null
  refetch: () => void
  filteredSpecies: (searchTerm: string) => SpeciesData[]
}

declare function useSpecies(params?: UseSpeciesParams): UseSpeciesResult
export default useSpecies

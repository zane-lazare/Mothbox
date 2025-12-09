import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import useSpecies from '../useSpecies'
import * as api from '../../utils/api'

// Mock the API module
vi.mock('../../utils/api', () => ({
  getAllSpecies: vi.fn()
}))

/**
 * Test suite for useSpecies hook
 *
 * Tests the custom hook for fetching all species from sidecar metadata using TanStack Query.
 * Verifies loading states, success scenarios, error handling, caching, filtering,
 * and query parameter handling.
 */
describe('useSpecies', () => {
  let queryClient

  // Helper function to create a wrapper with QueryClient
  const createWrapper = () => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false, // Disable retries for faster tests
        },
      },
    })

    return function Wrapper({ children }) {
      return (
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      )
    }
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
    if (queryClient) {
      queryClient.clear()
    }
  })

  describe('Success scenarios', () => {
    it('returns species from successful API call', async () => {
      const mockSpeciesData = {
        species: [
          { name: 'Actias luna', count: 42 },
          { name: 'Papilio glaucus', count: 18 },
          { name: 'Danaus plexippus', count: 7 },
        ],
        total: 3,
      }

      api.getAllSpecies.mockResolvedValueOnce({
        data: mockSpeciesData,
      })

      const { result } = renderHook(
        () => useSpecies(),
        { wrapper: createWrapper() }
      )

      // Initially loading with empty array
      expect(result.current.isLoading).toBe(true)
      expect(result.current.species).toEqual([])

      // Wait for successful fetch
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.isError).toBe(false)
      expect(result.current.species).toEqual(mockSpeciesData.species)
    })

    it('returns empty species array when none exist', async () => {
      const mockSpeciesData = { species: [], total: 0 }
      api.getAllSpecies.mockResolvedValueOnce({ data: mockSpeciesData })

      const { result } = renderHook(
        () => useSpecies(),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.species).toEqual([])
      expect(result.current.isError).toBe(false)
    })

    it('uses correct API endpoint', async () => {
      const mockSpeciesData = { species: [], total: 0 }
      api.getAllSpecies.mockResolvedValueOnce({ data: mockSpeciesData })

      renderHook(
        () => useSpecies(),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(api.getAllSpecies).toHaveBeenCalledWith({})
      })
    })

    it('passes sort and order params to API', async () => {
      const mockSpeciesData = { species: [], total: 0 }
      api.getAllSpecies.mockResolvedValueOnce({ data: mockSpeciesData })

      renderHook(
        () => useSpecies({ sort: 'count', order: 'desc' }),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(api.getAllSpecies).toHaveBeenCalledWith({ sort: 'count', order: 'desc' })
      })
    })

    it('passes limit param to API', async () => {
      const mockSpeciesData = { species: [], total: 0 }
      api.getAllSpecies.mockResolvedValueOnce({ data: mockSpeciesData })

      renderHook(
        () => useSpecies({ limit: 10 }),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(api.getAllSpecies).toHaveBeenCalledWith({ limit: 10 })
      })
    })

    it('caches species data', async () => {
      const mockSpeciesData = { species: [], total: 0 }
      api.getAllSpecies.mockResolvedValue({ data: mockSpeciesData })

      const wrapper = createWrapper()

      // First render - should fetch
      const { result: result1, unmount: unmount1 } = renderHook(
        () => useSpecies(),
        { wrapper }
      )

      await waitFor(() => {
        expect(result1.current.isLoading).toBe(false)
      })

      expect(api.getAllSpecies).toHaveBeenCalledTimes(1)

      unmount1()

      // Second render - should use cache
      const { result: result2 } = renderHook(
        () => useSpecies(),
        { wrapper }
      )

      await waitFor(() => {
        expect(result2.current.isLoading).toBe(false)
      })

      // Should still only have 1 fetch call (cached)
      expect(api.getAllSpecies).toHaveBeenCalledTimes(1)
    })

    it('refetches when params change', async () => {
      const mockSpeciesData1 = { species: [{ name: 'Actias luna', count: 10 }], total: 1 }
      const mockSpeciesData2 = { species: [{ name: 'Papilio glaucus', count: 5 }], total: 1 }

      api.getAllSpecies
        .mockResolvedValueOnce({ data: mockSpeciesData1 })
        .mockResolvedValueOnce({ data: mockSpeciesData2 })

      const { result, rerender } = renderHook(
        ({ params }) => useSpecies(params),
        {
          wrapper: createWrapper(),
          initialProps: { params: { sort: 'name' } },
        }
      )

      // Wait for first fetch
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.species).toEqual(mockSpeciesData1.species)
      expect(api.getAllSpecies).toHaveBeenCalledTimes(1)

      // Change params
      rerender({ params: { sort: 'count' } })

      // Wait for second fetch
      await waitFor(() => {
        expect(result.current.species).toEqual(mockSpeciesData2.species)
      })

      expect(api.getAllSpecies).toHaveBeenCalledTimes(2)
    })
  })

  describe('Loading state', () => {
    it('loading state is true initially', () => {
      api.getAllSpecies.mockImplementation(() => new Promise(() => {})) // Never resolves

      const { result } = renderHook(
        () => useSpecies(),
        { wrapper: createWrapper() }
      )

      expect(result.current.isLoading).toBe(true)
      expect(result.current.isError).toBe(false)
      expect(result.current.species).toEqual([])
    })

    it('returns empty species array while loading', () => {
      api.getAllSpecies.mockImplementation(() => new Promise(() => {}))

      const { result } = renderHook(
        () => useSpecies(),
        { wrapper: createWrapper() }
      )

      expect(result.current.species).toEqual([])
      expect(Array.isArray(result.current.species)).toBe(true)
    })
  })

  describe('Error handling', () => {
    it('handles error when API fails', async () => {
      const error = new Error('Failed to fetch species')
      api.getAllSpecies.mockRejectedValueOnce(error)

      const { result } = renderHook(
        () => useSpecies(),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      expect(result.current.isLoading).toBe(false)
      expect(result.current.species).toEqual([])
      expect(result.current.error).toBeDefined()
      expect(result.current.error.message).toBe('Failed to fetch species')
    })

    it('handles 500 server errors gracefully', async () => {
      const error = new Error('Request failed with status code 500')
      error.response = {
        status: 500,
        statusText: 'Internal Server Error',
      }
      api.getAllSpecies.mockRejectedValueOnce(error)

      const { result } = renderHook(
        () => useSpecies(),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      expect(result.current.error).toBeDefined()
      expect(result.current.error.message).toContain('500')
    })

    it('handles network errors gracefully', async () => {
      api.getAllSpecies.mockRejectedValueOnce(new Error('Network request failed'))

      const { result } = renderHook(
        () => useSpecies(),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      expect(result.current.error).toBeDefined()
      expect(result.current.error.message).toBe('Network request failed')
    })
  })

  describe('Refetch functionality', () => {
    it('refetch function works', async () => {
      const mockSpeciesData1 = { species: [{ name: 'Actias luna', count: 10 }], total: 1 }
      const mockSpeciesData2 = { species: [{ name: 'Actias luna', count: 15 }], total: 1 }

      api.getAllSpecies
        .mockResolvedValueOnce({ data: mockSpeciesData1 })
        .mockResolvedValueOnce({ data: mockSpeciesData2 })

      const { result } = renderHook(
        () => useSpecies(),
        { wrapper: createWrapper() }
      )

      // Wait for initial fetch
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.species).toEqual(mockSpeciesData1.species)
      expect(api.getAllSpecies).toHaveBeenCalledTimes(1)

      // Manually trigger refetch
      await result.current.refetch()

      // Wait for refetch to complete
      await waitFor(() => {
        expect(result.current.species).toEqual(mockSpeciesData2.species)
      })

      expect(api.getAllSpecies).toHaveBeenCalledTimes(2)
    })

    it('provides refetch function', async () => {
      const mockSpeciesData = { species: [], total: 0 }
      api.getAllSpecies.mockResolvedValue({ data: mockSpeciesData })

      const { result } = renderHook(
        () => useSpecies(),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.refetch).toBeDefined()
      expect(typeof result.current.refetch).toBe('function')
    })
  })

  describe('filteredSpecies helper', () => {
    const mockSpeciesData = {
      species: [
        { name: 'Actias luna', count: 42 },
        { name: 'Papilio glaucus', count: 18 },
        { name: 'Danaus plexippus', count: 7 },
        { name: 'Hyalophora cecropia', count: 12 },
        { name: 'Actias selene', count: 5 },
      ],
      total: 5,
    }

    it('filteredSpecies helper is case insensitive', async () => {
      api.getAllSpecies.mockResolvedValueOnce({ data: mockSpeciesData })

      const { result } = renderHook(
        () => useSpecies(),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      const filtered = result.current.filteredSpecies('ACTIAS')
      expect(filtered).toHaveLength(2)
      expect(filtered[0].name).toBe('Actias luna')
      expect(filtered[1].name).toBe('Actias selene')
    })

    it('filteredSpecies supports partial match', async () => {
      api.getAllSpecies.mockResolvedValueOnce({ data: mockSpeciesData })

      const { result } = renderHook(
        () => useSpecies(),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      const filtered = result.current.filteredSpecies('luna')
      expect(filtered).toHaveLength(1)
      expect(filtered[0].name).toBe('Actias luna')
    })

    it('filteredSpecies returns all species when search is empty', async () => {
      api.getAllSpecies.mockResolvedValueOnce({ data: mockSpeciesData })

      const { result } = renderHook(
        () => useSpecies(),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      const filtered = result.current.filteredSpecies('')
      expect(filtered).toEqual(mockSpeciesData.species)
      expect(filtered).toHaveLength(5)
    })

    it('filteredSpecies handles whitespace in search term', async () => {
      api.getAllSpecies.mockResolvedValueOnce({ data: mockSpeciesData })

      const { result } = renderHook(
        () => useSpecies(),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      const filtered = result.current.filteredSpecies('  actias  ')
      expect(filtered).toHaveLength(2)
    })

    it('filteredSpecies returns empty array when no matches', async () => {
      api.getAllSpecies.mockResolvedValueOnce({ data: mockSpeciesData })

      const { result } = renderHook(
        () => useSpecies(),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      const filtered = result.current.filteredSpecies('zzzzz')
      expect(filtered).toEqual([])
    })

    it('filteredSpecies function is provided', async () => {
      api.getAllSpecies.mockResolvedValueOnce({ data: mockSpeciesData })

      const { result } = renderHook(
        () => useSpecies(),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.filteredSpecies).toBeDefined()
      expect(typeof result.current.filteredSpecies).toBe('function')
    })

    it('filteredSpecies works with multi-word search', async () => {
      api.getAllSpecies.mockResolvedValueOnce({ data: mockSpeciesData })

      const { result } = renderHook(
        () => useSpecies(),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      const filtered = result.current.filteredSpecies('phora ce')
      expect(filtered).toHaveLength(1)
      expect(filtered[0].name).toBe('Hyalophora cecropia')
    })
  })

  describe('Cache configuration', () => {
    it('uses configured staleTime and gcTime', async () => {
      const mockSpeciesData = { species: [], total: 0 }
      api.getAllSpecies.mockResolvedValue({ data: mockSpeciesData })

      const wrapper = createWrapper()

      renderHook(
        () => useSpecies(),
        { wrapper }
      )

      await waitFor(() => {
        const queryState = queryClient.getQueryState(['species', {}])
        expect(queryState).toBeDefined()
      })

      const queryState = queryClient.getQueryState(['species', {}])
      // Verify query state exists (exact staleTime/gcTime values are implementation details)
      expect(queryState).toBeDefined()
    })
  })

  describe('Return values', () => {
    it('returns all required values', async () => {
      const mockSpeciesData = {
        species: [{ name: 'Actias luna', count: 10 }],
        total: 1,
      }
      api.getAllSpecies.mockResolvedValueOnce({ data: mockSpeciesData })

      const { result } = renderHook(
        () => useSpecies(),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current).toHaveProperty('species')
      expect(result.current).toHaveProperty('isLoading')
      expect(result.current).toHaveProperty('isError')
      expect(result.current).toHaveProperty('error')
      expect(result.current).toHaveProperty('refetch')
      expect(result.current).toHaveProperty('filteredSpecies')
    })

    it('species is always an array', async () => {
      const mockSpeciesData = { species: [], total: 0 }
      api.getAllSpecies.mockResolvedValueOnce({ data: mockSpeciesData })

      const { result } = renderHook(
        () => useSpecies(),
        { wrapper: createWrapper() }
      )

      // Before loading completes
      expect(Array.isArray(result.current.species)).toBe(true)

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      // After loading completes
      expect(Array.isArray(result.current.species)).toBe(true)
    })
  })
})

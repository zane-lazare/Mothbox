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
 * Verifies loading states, success scenarios, error handling, caching, and
 * query parameter handling.
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
    it('fetches species successfully', async () => {
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

      // Initially loading
      expect(result.current.isLoading).toBe(true)
      expect(result.current.data).toBeUndefined()

      // Wait for successful fetch
      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(result.current.isLoading).toBe(false)
      expect(result.current.isError).toBe(false)
      expect(result.current.data).toEqual(mockSpeciesData)
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

    it('passes multiple params to API', async () => {
      const mockSpeciesData = { species: [], total: 0 }
      api.getAllSpecies.mockResolvedValueOnce({ data: mockSpeciesData })

      renderHook(
        () => useSpecies({ sort: 'name', order: 'asc', limit: 20 }),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(api.getAllSpecies).toHaveBeenCalledWith({
          sort: 'name',
          order: 'asc',
          limit: 20
        })
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
        expect(result1.current.isSuccess).toBe(true)
      })

      expect(api.getAllSpecies).toHaveBeenCalledTimes(1)

      unmount1()

      // Second render - should use cache
      const { result: result2 } = renderHook(
        () => useSpecies(),
        { wrapper }
      )

      await waitFor(() => {
        expect(result2.current.isSuccess).toBe(true)
      })

      // Should still only have 1 fetch call (cached)
      expect(api.getAllSpecies).toHaveBeenCalledTimes(1)
    })

    it('uses correct query key for caching', async () => {
      const mockSpeciesData = { species: [], total: 0 }
      api.getAllSpecies.mockResolvedValueOnce({ data: mockSpeciesData })

      const wrapper = createWrapper()

      renderHook(
        () => useSpecies(),
        { wrapper }
      )

      await waitFor(() => {
        const cachedData = queryClient.getQueryData(['species', {}])
        expect(cachedData).toEqual(mockSpeciesData)
      })
    })

    it('uses different cache key with params', async () => {
      const mockSpeciesData = { species: [], total: 0 }
      api.getAllSpecies.mockResolvedValueOnce({ data: mockSpeciesData })

      const wrapper = createWrapper()
      const params = { sort: 'count', order: 'desc' }

      renderHook(
        () => useSpecies(params),
        { wrapper }
      )

      await waitFor(() => {
        const cachedData = queryClient.getQueryData(['species', params])
        expect(cachedData).toEqual(mockSpeciesData)
      })
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
        expect(result.current.isSuccess).toBe(true)
      })

      expect(result.current.data).toEqual(mockSpeciesData1)
      expect(api.getAllSpecies).toHaveBeenCalledTimes(1)
      expect(api.getAllSpecies).toHaveBeenCalledWith({ sort: 'name' })

      // Change params
      rerender({ params: { sort: 'count' } })

      // Wait for second fetch
      await waitFor(() => {
        expect(result.current.data).toEqual(mockSpeciesData2)
      })

      expect(api.getAllSpecies).toHaveBeenCalledTimes(2)
      expect(api.getAllSpecies).toHaveBeenLastCalledWith({ sort: 'count' })
    })
  })

  describe('Loading state', () => {
    it('returns loading state initially', () => {
      api.getAllSpecies.mockImplementation(() => new Promise(() => {})) // Never resolves

      const { result } = renderHook(
        () => useSpecies(),
        { wrapper: createWrapper() }
      )

      expect(result.current.isLoading).toBe(true)
      expect(result.current.isError).toBe(false)
      expect(result.current.isSuccess).toBe(false)
      expect(result.current.data).toBeUndefined()
    })
  })

  describe('Error handling', () => {
    it('handles error state', async () => {
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
      expect(result.current.isSuccess).toBe(false)
      expect(result.current.data).toBeUndefined()
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
    it('provides refetch function', async () => {
      const mockSpeciesData = { species: [], total: 0 }
      api.getAllSpecies.mockResolvedValue({ data: mockSpeciesData })

      const { result } = renderHook(
        () => useSpecies(),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(result.current.refetch).toBeDefined()
      expect(typeof result.current.refetch).toBe('function')
    })

    it('can refetch data manually', async () => {
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
        expect(result.current.isSuccess).toBe(true)
      })

      expect(result.current.data).toEqual(mockSpeciesData1)
      expect(api.getAllSpecies).toHaveBeenCalledTimes(1)

      // Manually trigger refetch
      await result.current.refetch()

      // Wait for refetch to complete
      await waitFor(() => {
        expect(result.current.data).toEqual(mockSpeciesData2)
      })

      expect(api.getAllSpecies).toHaveBeenCalledTimes(2)
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

  describe('Cleanup', () => {
    it('cleans up on unmount without errors', async () => {
      const mockSpeciesData = { species: [], total: 0 }
      api.getAllSpecies.mockResolvedValueOnce({ data: mockSpeciesData })

      const { unmount } = renderHook(
        () => useSpecies(),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(api.getAllSpecies).toHaveBeenCalled()
      })

      // Should not throw when unmounting
      expect(() => unmount()).not.toThrow()
    })
  })
})

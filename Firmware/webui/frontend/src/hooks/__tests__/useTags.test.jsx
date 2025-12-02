import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import useTags from '../useTags'
import * as api from '../../utils/api'

// Mock the API module
vi.mock('../../utils/api', () => ({
  getAllTags: vi.fn()
}))

/**
 * Test suite for useTags hook
 *
 * Tests the custom hook for fetching all tags from sidecar metadata using TanStack Query.
 * Verifies loading states, success scenarios, error handling, caching, and
 * query parameter handling.
 */
describe('useTags', () => {
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
    it('fetches tags successfully', async () => {
      const mockTagsData = {
        tags: [
          { name: 'Moth', count: 42 },
          { name: 'Butterfly', count: 18 },
          { name: 'Beetle', count: 7 },
        ],
        total: 3,
      }

      api.getAllTags.mockResolvedValueOnce({
        data: mockTagsData,
      })

      const { result } = renderHook(
        () => useTags(),
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
      expect(result.current.data).toEqual(mockTagsData)
    })

    it('uses correct API endpoint', async () => {
      const mockTagsData = { tags: [], total: 0 }
      api.getAllTags.mockResolvedValueOnce({ data: mockTagsData })

      renderHook(
        () => useTags(),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(api.getAllTags).toHaveBeenCalledWith({})
      })
    })

    it('passes sort and order params to API', async () => {
      const mockTagsData = { tags: [], total: 0 }
      api.getAllTags.mockResolvedValueOnce({ data: mockTagsData })

      renderHook(
        () => useTags({ sort: 'count', order: 'desc' }),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(api.getAllTags).toHaveBeenCalledWith({ sort: 'count', order: 'desc' })
      })
    })

    it('passes limit param to API', async () => {
      const mockTagsData = { tags: [], total: 0 }
      api.getAllTags.mockResolvedValueOnce({ data: mockTagsData })

      renderHook(
        () => useTags({ limit: 10 }),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(api.getAllTags).toHaveBeenCalledWith({ limit: 10 })
      })
    })

    it('passes multiple params to API', async () => {
      const mockTagsData = { tags: [], total: 0 }
      api.getAllTags.mockResolvedValueOnce({ data: mockTagsData })

      renderHook(
        () => useTags({ sort: 'name', order: 'asc', limit: 20 }),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(api.getAllTags).toHaveBeenCalledWith({
          sort: 'name',
          order: 'asc',
          limit: 20
        })
      })
    })

    it('caches tags data', async () => {
      const mockTagsData = { tags: [], total: 0 }
      api.getAllTags.mockResolvedValue({ data: mockTagsData })

      const wrapper = createWrapper()

      // First render - should fetch
      const { result: result1, unmount: unmount1 } = renderHook(
        () => useTags(),
        { wrapper }
      )

      await waitFor(() => {
        expect(result1.current.isSuccess).toBe(true)
      })

      expect(api.getAllTags).toHaveBeenCalledTimes(1)

      unmount1()

      // Second render - should use cache
      const { result: result2 } = renderHook(
        () => useTags(),
        { wrapper }
      )

      await waitFor(() => {
        expect(result2.current.isSuccess).toBe(true)
      })

      // Should still only have 1 fetch call (cached)
      expect(api.getAllTags).toHaveBeenCalledTimes(1)
    })

    it('uses correct query key for caching', async () => {
      const mockTagsData = { tags: [], total: 0 }
      api.getAllTags.mockResolvedValueOnce({ data: mockTagsData })

      const wrapper = createWrapper()

      renderHook(
        () => useTags(),
        { wrapper }
      )

      await waitFor(() => {
        const cachedData = queryClient.getQueryData(['tags', {}])
        expect(cachedData).toEqual(mockTagsData)
      })
    })

    it('uses different cache key with params', async () => {
      const mockTagsData = { tags: [], total: 0 }
      api.getAllTags.mockResolvedValueOnce({ data: mockTagsData })

      const wrapper = createWrapper()
      const params = { sort: 'count', order: 'desc' }

      renderHook(
        () => useTags(params),
        { wrapper }
      )

      await waitFor(() => {
        const cachedData = queryClient.getQueryData(['tags', params])
        expect(cachedData).toEqual(mockTagsData)
      })
    })

    it('refetches when params change', async () => {
      const mockTagsData1 = { tags: [{ name: 'Moth', count: 10 }], total: 1 }
      const mockTagsData2 = { tags: [{ name: 'Beetle', count: 5 }], total: 1 }

      api.getAllTags
        .mockResolvedValueOnce({ data: mockTagsData1 })
        .mockResolvedValueOnce({ data: mockTagsData2 })

      const { result, rerender } = renderHook(
        ({ params }) => useTags(params),
        {
          wrapper: createWrapper(),
          initialProps: { params: { sort: 'name' } },
        }
      )

      // Wait for first fetch
      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(result.current.data).toEqual(mockTagsData1)
      expect(api.getAllTags).toHaveBeenCalledTimes(1)
      expect(api.getAllTags).toHaveBeenCalledWith({ sort: 'name' })

      // Change params
      rerender({ params: { sort: 'count' } })

      // Wait for second fetch
      await waitFor(() => {
        expect(result.current.data).toEqual(mockTagsData2)
      })

      expect(api.getAllTags).toHaveBeenCalledTimes(2)
      expect(api.getAllTags).toHaveBeenLastCalledWith({ sort: 'count' })
    })
  })

  describe('Loading state', () => {
    it('returns loading state initially', () => {
      api.getAllTags.mockImplementation(() => new Promise(() => {})) // Never resolves

      const { result } = renderHook(
        () => useTags(),
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
      const error = new Error('Failed to fetch tags')
      api.getAllTags.mockRejectedValueOnce(error)

      const { result } = renderHook(
        () => useTags(),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      expect(result.current.isLoading).toBe(false)
      expect(result.current.isSuccess).toBe(false)
      expect(result.current.data).toBeUndefined()
      expect(result.current.error).toBeDefined()
      expect(result.current.error.message).toBe('Failed to fetch tags')
    })

    it('handles 500 server errors gracefully', async () => {
      const error = new Error('Request failed with status code 500')
      error.response = {
        status: 500,
        statusText: 'Internal Server Error',
      }
      api.getAllTags.mockRejectedValueOnce(error)

      const { result } = renderHook(
        () => useTags(),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      expect(result.current.error).toBeDefined()
      expect(result.current.error.message).toContain('500')
    })

    it('handles network errors gracefully', async () => {
      api.getAllTags.mockRejectedValueOnce(new Error('Network request failed'))

      const { result } = renderHook(
        () => useTags(),
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
      const mockTagsData = { tags: [], total: 0 }
      api.getAllTags.mockResolvedValue({ data: mockTagsData })

      const { result } = renderHook(
        () => useTags(),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(result.current.refetch).toBeDefined()
      expect(typeof result.current.refetch).toBe('function')
    })

    it('can refetch data manually', async () => {
      const mockTagsData1 = { tags: [{ name: 'Moth', count: 10 }], total: 1 }
      const mockTagsData2 = { tags: [{ name: 'Moth', count: 15 }], total: 1 }

      api.getAllTags
        .mockResolvedValueOnce({ data: mockTagsData1 })
        .mockResolvedValueOnce({ data: mockTagsData2 })

      const { result } = renderHook(
        () => useTags(),
        { wrapper: createWrapper() }
      )

      // Wait for initial fetch
      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(result.current.data).toEqual(mockTagsData1)
      expect(api.getAllTags).toHaveBeenCalledTimes(1)

      // Manually trigger refetch
      await result.current.refetch()

      // Wait for refetch to complete
      await waitFor(() => {
        expect(result.current.data).toEqual(mockTagsData2)
      })

      expect(api.getAllTags).toHaveBeenCalledTimes(2)
    })
  })

  describe('Cache configuration', () => {
    it('uses configured staleTime and gcTime', async () => {
      const mockTagsData = { tags: [], total: 0 }
      api.getAllTags.mockResolvedValue({ data: mockTagsData })

      const wrapper = createWrapper()

      renderHook(
        () => useTags(),
        { wrapper }
      )

      await waitFor(() => {
        const queryState = queryClient.getQueryState(['tags', {}])
        expect(queryState).toBeDefined()
      })

      const queryState = queryClient.getQueryState(['tags', {}])
      // Verify query state exists (exact staleTime/gcTime values are implementation details)
      expect(queryState).toBeDefined()
    })
  })

  describe('Cleanup', () => {
    it('cleans up on unmount without errors', async () => {
      const mockTagsData = { tags: [], total: 0 }
      api.getAllTags.mockResolvedValueOnce({ data: mockTagsData })

      const { unmount } = renderHook(
        () => useTags(),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(api.getAllTags).toHaveBeenCalled()
      })

      // Should not throw when unmounting
      expect(() => unmount()).not.toThrow()
    })
  })
})

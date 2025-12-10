import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { usePhotoSearch } from '../usePhotoSearch'
import * as api from '../../utils/api'

// Mock the API module
vi.mock('../../utils/api', () => ({
  searchPhotos: vi.fn()
}))

/**
 * Test suite for usePhotoSearch hook
 *
 * Tests the custom hook for searching photos with debouncing, caching,
 * and pagination support.
 */
describe('usePhotoSearch', () => {
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

  describe('debouncing', () => {
    it('should eventually call search after debounce', async () => {
      const mockResponse = {
        results: [
          {
            filename: 'moth_2024_01_15__10_30_00.jpg',
            path: '2024-11-10/moth_2024_01_15__10_30_00.jpg',
            thumbnail_url: '/api/gallery/thumbnail/2024-11-10/moth_2024_01_15__10_30_00.jpg',
            metadata: { tags: ['moth'] },
            score: 1.0,
            matched_fields: ['tags']
          }
        ],
        total: 1,
        query: 'moth',
        parsed_query: 'moth',
        took_ms: 23.5,
        pagination: {
          limit: 20,
          offset: 0,
          has_next: false,
          has_prev: false
        }
      }

      api.searchPhotos.mockResolvedValueOnce(mockResponse)

      const { result } = renderHook(
        () => usePhotoSearch('moth', { debounceMs: 100 }),
        { wrapper: createWrapper() }
      )

      // Initially empty before debounce completes
      expect(result.current.results).toEqual([])

      // Wait for debounce and query to complete
      await waitFor(() => {
        expect(api.searchPhotos).toHaveBeenCalledWith('moth', { limit: 20, offset: 0 })
      }, { timeout: 1000 })

      await waitFor(() => {
        expect(result.current.results).toEqual(mockResponse.results)
      })
    })

    it('should work with custom debounceMs', async () => {
      const mockResponse = {
        results: [],
        total: 0,
        query: 'moth',
        parsed_query: 'moth',
        took_ms: 5,
        pagination: { limit: 20, offset: 0, has_next: false, has_prev: false }
      }

      api.searchPhotos.mockResolvedValueOnce(mockResponse)

      renderHook(
        () => usePhotoSearch('moth', { debounceMs: 150 }),
        { wrapper: createWrapper() }
      )

      // Should eventually call after custom debounce
      await waitFor(() => {
        expect(api.searchPhotos).toHaveBeenCalled()
      }, { timeout: 1000 })
    })

    it('should cancel pending debounce on query change', async () => {
      const mockResponse = {
        results: [],
        total: 0,
        query: 'moths',
        parsed_query: 'moths',
        took_ms: 5,
        pagination: { limit: 20, offset: 0, has_next: false, has_prev: false }
      }

      api.searchPhotos.mockResolvedValue(mockResponse)

      const { rerender } = renderHook(
        ({ query }) => usePhotoSearch(query, { debounceMs: 100 }),
        {
          wrapper: createWrapper(),
          initialProps: { query: '' } // Start with empty to avoid initial query
        }
      )

      // Type quickly to cancel previous debounces
      await act(async () => {
        rerender({ query: 'mo' })
        await new Promise(resolve => setTimeout(resolve, 20))
        rerender({ query: 'mot' })
        await new Promise(resolve => setTimeout(resolve, 20))
        rerender({ query: 'moth' })
        await new Promise(resolve => setTimeout(resolve, 20))
        rerender({ query: 'moths' })
      })

      // Wait for final query
      await waitFor(() => {
        expect(api.searchPhotos).toHaveBeenCalledWith('moths', { limit: 20, offset: 0 })
      }, { timeout: 1000 })

      // Should only call once with final query
      expect(api.searchPhotos).toHaveBeenCalledTimes(1)
    })
  })

  describe('query behavior', () => {
    it('should not search when query is empty', async () => {
      const { result } = renderHook(
        () => usePhotoSearch('', { debounceMs: 10 }),
        { wrapper: createWrapper() }
      )

      // Wait a bit to ensure no call
      await new Promise(resolve => setTimeout(resolve, 100))

      // Empty query should not trigger API call
      expect(api.searchPhotos).not.toHaveBeenCalled()
      expect(result.current.results).toEqual([])
    })

    it('should not search when query is whitespace only', async () => {
      const { result } = renderHook(
        () => usePhotoSearch('   ', { debounceMs: 10 }),
        { wrapper: createWrapper() }
      )

      // Wait a bit to ensure no call
      await new Promise(resolve => setTimeout(resolve, 100))

      expect(api.searchPhotos).not.toHaveBeenCalled()
      expect(result.current.results).toEqual([])
    })

    it('should not search when enabled is false', async () => {
      const { result } = renderHook(
        () => usePhotoSearch('moth', { enabled: false, debounceMs: 10 }),
        { wrapper: createWrapper() }
      )

      // Wait a bit to ensure no call
      await new Promise(resolve => setTimeout(resolve, 100))

      // Disabled query should not trigger API call
      expect(api.searchPhotos).not.toHaveBeenCalled()
      expect(result.current.results).toEqual([])
    })

    it('should search when query has content', async () => {
      const mockResponse = {
        results: [],
        total: 0,
        query: 'moth',
        parsed_query: 'moth',
        took_ms: 5,
        pagination: { limit: 20, offset: 0, has_next: false, has_prev: false }
      }

      api.searchPhotos.mockResolvedValueOnce(mockResponse)

      renderHook(
        () => usePhotoSearch('moth', { debounceMs: 10 }),
        { wrapper: createWrapper() }
      )

      // Non-empty query should trigger API call
      await waitFor(() => {
        expect(api.searchPhotos).toHaveBeenCalledWith('moth', { limit: 20, offset: 0 })
      })
    })
  })

  describe('results', () => {
    it('should return results from API', async () => {
      const mockResponse = {
        results: [
          {
            filename: 'moth1.jpg',
            path: '2024-11-10/moth1.jpg',
            thumbnail_url: '/api/gallery/thumbnail/2024-11-10/moth1.jpg',
            metadata: { tags: ['moth'] },
            score: 1.0,
            matched_fields: ['tags']
          },
          {
            filename: 'moth2.jpg',
            path: '2024-11-10/moth2.jpg',
            thumbnail_url: '/api/gallery/thumbnail/2024-11-10/moth2.jpg',
            metadata: { tags: ['moth', 'luna'] },
            score: 0.8,
            matched_fields: ['tags']
          }
        ],
        total: 2,
        query: 'moth',
        parsed_query: 'moth',
        took_ms: 23.5,
        pagination: { limit: 20, offset: 0, has_next: false, has_prev: false }
      }

      api.searchPhotos.mockResolvedValueOnce(mockResponse)

      const { result } = renderHook(
        () => usePhotoSearch('moth', { debounceMs: 10 }),
        { wrapper: createWrapper() }
      )

      // Verify results match response
      await waitFor(() => {
        expect(result.current.results).toEqual(mockResponse.results)
      })
    })

    it('should include total count', async () => {
      const mockResponse = {
        results: [],
        total: 45,
        query: 'moth',
        parsed_query: 'moth',
        took_ms: 10,
        pagination: { limit: 20, offset: 0, has_next: true, has_prev: false }
      }

      api.searchPhotos.mockResolvedValueOnce(mockResponse)

      const { result } = renderHook(
        () => usePhotoSearch('moth', { debounceMs: 10 }),
        { wrapper: createWrapper() }
      )

      // Verify total is returned
      await waitFor(() => {
        expect(result.current.total).toBe(45)
      })
    })

    it('should include tookMs', async () => {
      const mockResponse = {
        results: [],
        total: 0,
        query: 'moth',
        parsed_query: 'moth',
        took_ms: 23.5,
        pagination: { limit: 20, offset: 0, has_next: false, has_prev: false }
      }

      api.searchPhotos.mockResolvedValueOnce(mockResponse)

      const { result } = renderHook(
        () => usePhotoSearch('moth', { debounceMs: 10 }),
        { wrapper: createWrapper() }
      )

      // Verify query time is returned
      await waitFor(() => {
        expect(result.current.tookMs).toBe(23.5)
      })
    })

    it('should include parsedQuery', async () => {
      const mockResponse = {
        results: [],
        total: 0,
        query: 'luna moth',
        parsed_query: 'luna AND moth',
        took_ms: 5,
        pagination: { limit: 20, offset: 0, has_next: false, has_prev: false }
      }

      api.searchPhotos.mockResolvedValueOnce(mockResponse)

      const { result } = renderHook(
        () => usePhotoSearch('luna moth', { debounceMs: 10 }),
        { wrapper: createWrapper() }
      )

      // Verify parsed query is returned
      await waitFor(() => {
        expect(result.current.parsedQuery).toBe('luna AND moth')
      })
    })
  })

  describe('pagination', () => {
    it('should return pagination state', async () => {
      const mockResponse = {
        results: [],
        total: 100,
        query: 'moth',
        parsed_query: 'moth',
        took_ms: 5,
        pagination: {
          limit: 20,
          offset: 40,
          has_next: true,
          has_prev: true
        }
      }

      api.searchPhotos.mockResolvedValueOnce(mockResponse)

      const { result } = renderHook(
        () => usePhotoSearch('moth', { limit: 20, offset: 40, debounceMs: 10 }),
        { wrapper: createWrapper() }
      )

      // Verify limit, offset, hasNext, hasPrev
      await waitFor(() => {
        expect(result.current.pagination).toEqual({
          limit: 20,
          offset: 40,
          hasNext: true,
          hasPrev: true
        })
      })
    })

    it('should respect limit option', async () => {
      const mockResponse = {
        results: [],
        total: 50,
        query: 'moth',
        parsed_query: 'moth',
        took_ms: 5,
        pagination: { limit: 10, offset: 0, has_next: true, has_prev: false }
      }

      api.searchPhotos.mockResolvedValueOnce(mockResponse)

      renderHook(
        () => usePhotoSearch('moth', { limit: 10, debounceMs: 10 }),
        { wrapper: createWrapper() }
      )

      // Custom limit should be used
      await waitFor(() => {
        expect(api.searchPhotos).toHaveBeenCalledWith('moth', { limit: 10, offset: 0 })
      })
    })

    it('should use default limit of 20', async () => {
      const mockResponse = {
        results: [],
        total: 0,
        query: 'moth',
        parsed_query: 'moth',
        took_ms: 5,
        pagination: { limit: 20, offset: 0, has_next: false, has_prev: false }
      }

      api.searchPhotos.mockResolvedValueOnce(mockResponse)

      renderHook(
        () => usePhotoSearch('moth', { debounceMs: 10 }),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(api.searchPhotos).toHaveBeenCalledWith('moth', { limit: 20, offset: 0 })
      })
    })
  })

  describe('loading states', () => {
    it('should set isLoading while fetching', async () => {
      api.searchPhotos.mockImplementation(() => new Promise(() => {})) // Never resolves

      const { result } = renderHook(
        () => usePhotoSearch('moth', { debounceMs: 10 }),
        { wrapper: createWrapper() }
      )

      // Verify loading state during fetch
      await waitFor(() => {
        expect(result.current.isLoading).toBe(true)
      })

      expect(result.current.results).toEqual([])
    })

    it('should set isError on failure', async () => {
      const error = new Error('Search failed')
      api.searchPhotos.mockRejectedValueOnce(error)

      const { result } = renderHook(
        () => usePhotoSearch('moth', { debounceMs: 10 }),
        { wrapper: createWrapper() }
      )

      // Verify error state
      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      expect(result.current.error).toBeDefined()
      expect(result.current.error.message).toBe('Search failed')
    })

    it('should clear loading state on success', async () => {
      const mockResponse = {
        results: [],
        total: 0,
        query: 'moth',
        parsed_query: 'moth',
        took_ms: 5,
        pagination: { limit: 20, offset: 0, has_next: false, has_prev: false }
      }

      api.searchPhotos.mockResolvedValueOnce(mockResponse)

      const { result } = renderHook(
        () => usePhotoSearch('moth', { debounceMs: 10 }),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.isError).toBe(false)
    })
  })

  describe('refetch', () => {
    it('should provide refetch function', async () => {
      const mockResponse = {
        results: [],
        total: 0,
        query: 'moth',
        parsed_query: 'moth',
        took_ms: 5,
        pagination: { limit: 20, offset: 0, has_next: false, has_prev: false }
      }

      api.searchPhotos.mockResolvedValue(mockResponse)

      const { result } = renderHook(
        () => usePhotoSearch('moth', { debounceMs: 10 }),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(api.searchPhotos).toHaveBeenCalledTimes(1)
      })

      // Verify refetch triggers new API call
      await act(async () => {
        await result.current.refetch()
      })

      await waitFor(() => {
        expect(api.searchPhotos).toHaveBeenCalledTimes(2)
      })
    })
  })

  describe('caching', () => {
    it('should cache same query', async () => {
      const mockResponse = {
        results: [],
        total: 0,
        query: 'moth',
        parsed_query: 'moth',
        took_ms: 5,
        pagination: { limit: 20, offset: 0, has_next: false, has_prev: false }
      }

      api.searchPhotos.mockResolvedValue(mockResponse)

      const wrapper = createWrapper()

      // First render
      const { unmount: unmount1 } = renderHook(
        () => usePhotoSearch('moth', { debounceMs: 10 }),
        { wrapper }
      )

      await waitFor(() => {
        expect(api.searchPhotos).toHaveBeenCalledTimes(1)
      })

      unmount1()

      // Second render - should use cache
      const { result: result2 } = renderHook(
        () => usePhotoSearch('moth', { debounceMs: 10 }),
        { wrapper }
      )

      await waitFor(() => {
        expect(result2.current.results).toEqual(mockResponse.results)
      })

      // Should still only have 1 API call (cached)
      expect(api.searchPhotos).toHaveBeenCalledTimes(1)
    })
  })

  describe('default values', () => {
    it('should return empty results before fetch', () => {
      const { result } = renderHook(
        () => usePhotoSearch('', { debounceMs: 10 }),
        { wrapper: createWrapper() }
      )

      expect(result.current.results).toEqual([])
      expect(result.current.total).toBe(0)
      expect(result.current.tookMs).toBe(0)
      expect(result.current.parsedQuery).toBe('')
      expect(result.current.pagination).toEqual({
        limit: 20,
        offset: 0,
        hasNext: false,
        hasPrev: false
      })
    })
  })
})

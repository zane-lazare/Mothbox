import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { usePhotoLocations } from '../usePhotoLocations'
import { getPhotoLocations } from '../../utils/api'

// Mock the API module
vi.mock('../../utils/api', () => ({
  getPhotoLocations: vi.fn(),
}))

/**
 * Test suite for usePhotoLocations hook
 *
 * Tests the custom hook for fetching photo location data for map display.
 * Verifies loading states, success scenarios, error handling, and parameter passing.
 */
describe('usePhotoLocations', () => {
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

  describe('Loading state', () => {
    it('returns empty locations array when loading', () => {
      // Never resolves to keep loading state
      getPhotoLocations.mockImplementation(() => new Promise(() => {}))

      const { result } = renderHook(
        () => usePhotoLocations(),
        { wrapper: createWrapper() }
      )

      expect(result.current.isLoading).toBe(true)
      expect(result.current.isError).toBe(false)
      expect(result.current.locations).toEqual([])
      expect(result.current.totalWithGps).toBe(0)
      expect(result.current.totalWithoutGps).toBe(0)
    })
  })

  describe('Success scenarios', () => {
    it('returns locations array on success', async () => {
      const mockLocationData = {
        locations: [
          {
            filename: 'moth_2024_01_15__10_00_00.jpg',
            path: '/photos/moth_2024_01_15__10_00_00.jpg',
            latitude: 37.7749,
            longitude: -122.4194,
            timestamp: '2024-01-15T10:00:00Z',
          },
          {
            filename: 'moth_2024_01_15__11_00_00.jpg',
            path: '/photos/moth_2024_01_15__11_00_00.jpg',
            latitude: 37.7750,
            longitude: -122.4195,
            timestamp: '2024-01-15T11:00:00Z',
          },
        ],
        total_with_gps: 2,
        total_without_gps: 5,
      }

      getPhotoLocations.mockResolvedValueOnce(mockLocationData)

      const { result } = renderHook(
        () => usePhotoLocations(),
        { wrapper: createWrapper() }
      )

      // Initially loading
      expect(result.current.isLoading).toBe(true)
      expect(result.current.locations).toEqual([])

      // Wait for successful fetch
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.isError).toBe(false)
      expect(result.current.locations).toEqual(mockLocationData.locations)
      expect(result.current.totalWithGps).toBe(2)
      expect(result.current.totalWithoutGps).toBe(5)
    })

    it('uses correct API endpoint', async () => {
      const mockData = { locations: [], total_with_gps: 0, total_without_gps: 0 }
      getPhotoLocations.mockResolvedValueOnce(mockData)

      renderHook(
        () => usePhotoLocations(),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(getPhotoLocations).toHaveBeenCalledWith({})
      })
    })

    it('respects limit parameter', async () => {
      const mockData = { locations: [], total_with_gps: 0, total_without_gps: 0 }
      getPhotoLocations.mockResolvedValueOnce(mockData)

      renderHook(
        () => usePhotoLocations({ limit: 500 }),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(getPhotoLocations).toHaveBeenCalledWith({ limit: 500 })
      })
    })

    it('returns totalWithGps and totalWithoutGps counts', async () => {
      const mockData = {
        locations: [
          { filename: 'photo1.jpg', latitude: 1.0, longitude: 2.0 },
        ],
        total_with_gps: 10,
        total_without_gps: 25,
      }
      getPhotoLocations.mockResolvedValueOnce(mockData)

      const { result } = renderHook(
        () => usePhotoLocations(),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.totalWithGps).toBe(10)
      expect(result.current.totalWithoutGps).toBe(25)
    })

    it('caches location data', async () => {
      const mockData = { locations: [], total_with_gps: 0, total_without_gps: 0 }
      getPhotoLocations.mockResolvedValue(mockData)

      const wrapper = createWrapper()

      // First render - should fetch
      const { result: result1, unmount: unmount1 } = renderHook(
        () => usePhotoLocations(),
        { wrapper }
      )

      await waitFor(() => {
        expect(result1.current.isLoading).toBe(false)
      })

      expect(getPhotoLocations).toHaveBeenCalledTimes(1)

      unmount1()

      // Second render - should use cache
      const { result: result2 } = renderHook(
        () => usePhotoLocations(),
        { wrapper }
      )

      await waitFor(() => {
        expect(result2.current.isLoading).toBe(false)
      })

      // Should still only have 1 fetch call (cached)
      expect(getPhotoLocations).toHaveBeenCalledTimes(1)
    })

    it('uses correct query key format', async () => {
      const mockData = { locations: [], total_with_gps: 0, total_without_gps: 0 }
      getPhotoLocations.mockResolvedValueOnce(mockData)

      const wrapper = createWrapper()

      renderHook(
        () => usePhotoLocations(),
        { wrapper }
      )

      await waitFor(() => {
        const cachedData = queryClient.getQueryData(['photo-locations'])
        expect(cachedData).toEqual(mockData)
      })
    })

    it('uses different cache key with params', async () => {
      const mockData = { locations: [], total_with_gps: 0, total_without_gps: 0 }
      getPhotoLocations.mockResolvedValueOnce(mockData)

      const wrapper = createWrapper()

      renderHook(
        () => usePhotoLocations({ limit: 100 }),
        { wrapper }
      )

      await waitFor(() => {
        const cachedData = queryClient.getQueryData(['photo-locations', { limit: 100 }])
        expect(cachedData).toEqual(mockData)
      })
    })

    it('provides refetch function', async () => {
      const mockData = { locations: [], total_with_gps: 0, total_without_gps: 0 }
      getPhotoLocations.mockResolvedValue(mockData)

      const { result } = renderHook(
        () => usePhotoLocations(),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(getPhotoLocations).toHaveBeenCalledTimes(1)
      expect(typeof result.current.refetch).toBe('function')

      // Call refetch
      await result.current.refetch()

      // Should have made another API call
      expect(getPhotoLocations).toHaveBeenCalledTimes(2)
    })
  })

  describe('Error handling', () => {
    it('handles API errors gracefully', async () => {
      const error = new Error('Request failed with status code 500')
      error.response = { status: 500, statusText: 'Internal Server Error' }
      getPhotoLocations.mockRejectedValueOnce(error)

      const { result } = renderHook(
        () => usePhotoLocations(),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      expect(result.current.isLoading).toBe(false)
      expect(result.current.locations).toEqual([])
      expect(result.current.error).toBeDefined()
      expect(result.current.totalWithGps).toBe(0)
      expect(result.current.totalWithoutGps).toBe(0)
    })

    it('handles 404 errors gracefully', async () => {
      const error = new Error('Request failed with status code 404')
      error.response = { status: 404, statusText: 'Not Found' }
      getPhotoLocations.mockRejectedValueOnce(error)

      const { result } = renderHook(
        () => usePhotoLocations(),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      expect(result.current.locations).toEqual([])
      expect(result.current.error).toBeDefined()
    })

    it('handles network errors gracefully', async () => {
      getPhotoLocations.mockRejectedValueOnce(new Error('Network request failed'))

      const { result } = renderHook(
        () => usePhotoLocations(),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      expect(result.current.error.message).toBe('Network request failed')
      expect(result.current.locations).toEqual([])
    })
  })

  describe('Enabled option', () => {
    it('does not fetch when enabled is false', () => {
      const { result } = renderHook(
        () => usePhotoLocations({}, { enabled: false }),
        { wrapper: createWrapper() }
      )

      expect(result.current.isLoading).toBe(false)
      expect(result.current.isError).toBe(false)
      expect(result.current.locations).toEqual([])
      expect(getPhotoLocations).not.toHaveBeenCalled()
    })

    it('fetches when enabled changes from false to true', async () => {
      const mockData = { locations: [], total_with_gps: 0, total_without_gps: 0 }
      getPhotoLocations.mockResolvedValueOnce(mockData)

      const { result, rerender } = renderHook(
        ({ enabled }) => usePhotoLocations({}, { enabled }),
        {
          wrapper: createWrapper(),
          initialProps: { enabled: false },
        }
      )

      // Initially should not fetch
      expect(result.current.isLoading).toBe(false)
      expect(getPhotoLocations).not.toHaveBeenCalled()

      // Enable fetching
      rerender({ enabled: true })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(getPhotoLocations).toHaveBeenCalledTimes(1)
    })
  })

  describe('Cleanup', () => {
    it('cleans up on unmount without errors', async () => {
      const mockData = { locations: [], total_with_gps: 0, total_without_gps: 0 }
      getPhotoLocations.mockResolvedValueOnce(mockData)

      const { unmount } = renderHook(
        () => usePhotoLocations(),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(getPhotoLocations).toHaveBeenCalled()
      })

      expect(() => unmount()).not.toThrow()
    })
  })
})

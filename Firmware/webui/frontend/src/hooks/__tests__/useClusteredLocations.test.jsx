import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { useClusteredLocations } from '../useClusteredLocations'
import { getClusteredLocations } from '../../utils/api'

// Mock the API module
vi.mock('../../utils/api', () => ({
  getClusteredLocations: vi.fn(),
}))

/**
 * Test suite for useClusteredLocations hook
 *
 * Tests the custom hook for fetching clustered photo location data.
 * Verifies loading states, success scenarios, error handling, localStorage persistence,
 * and clustering settings management.
 */
describe('useClusteredLocations', () => {
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
      return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    }
  }

  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  afterEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    if (queryClient) {
      queryClient.clear()
    }
  })

  describe('Loading state', () => {
    it('returns empty clusters and unclustered arrays when loading', () => {
      // Never resolves to keep loading state
      getClusteredLocations.mockImplementation(() => new Promise(() => {}))

      const { result } = renderHook(() => useClusteredLocations(), {
        wrapper: createWrapper(),
      })

      expect(result.current.isLoading).toBe(true)
      expect(result.current.clusters).toEqual([])
      expect(result.current.unclustered).toEqual([])
      expect(result.current.metadata).toEqual({})
    })
  })

  describe('Success scenarios', () => {
    it('returns clusters and unclustered photos on success', async () => {
      const mockClusteredData = {
        clusters: [
          {
            cluster_id: 'cluster_1',
            count: 3,
            center: { lat: 37.7749, lon: -122.4194 },
            date_range: {
              earliest: '2024-01-15',
              latest: '2024-01-16',
            },
            photos: [
              { photo_id: 'photo1.jpg', lat: 37.7749, lon: -122.4194 },
              { photo_id: 'photo2.jpg', lat: 37.7750, lon: -122.4195 },
              { photo_id: 'photo3.jpg', lat: 37.7751, lon: -122.4196 },
            ],
          },
        ],
        unclustered: [
          {
            filename: 'photo4.jpg',
            latitude: 38.0,
            longitude: -123.0,
          },
        ],
        metadata: {
          total_photos: 4,
          total_clusters: 1,
          total_in_clusters: 3,
          total_unclustered: 1,
        },
      }

      getClusteredLocations.mockResolvedValueOnce(mockClusteredData)

      const { result } = renderHook(() => useClusteredLocations(), {
        wrapper: createWrapper(),
      })

      // Initially loading
      expect(result.current.isLoading).toBe(true)

      // Wait for successful fetch
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.clusters).toEqual(mockClusteredData.clusters)
      expect(result.current.unclustered).toEqual(mockClusteredData.unclustered)
      expect(result.current.metadata).toEqual(mockClusteredData.metadata)
    })

    it('uses default settings on first load', async () => {
      const mockData = {
        clusters: [],
        unclustered: [],
        metadata: {},
      }
      getClusteredLocations.mockResolvedValueOnce(mockData)

      renderHook(() => useClusteredLocations(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(getClusteredLocations).toHaveBeenCalledWith({
          enabled: 'true',
          radius: '100',
          min_size: '2',
        })
      })
    })

    it('loads saved settings from localStorage', async () => {
      // Pre-populate localStorage with custom settings
      localStorage.setItem(
        'mothbox_clustering_settings',
        JSON.stringify({
          enabled: false,
          radius: 500,
          minSize: 3,
        })
      )

      const mockData = {
        clusters: [],
        unclustered: [],
        metadata: {},
      }
      getClusteredLocations.mockResolvedValueOnce(mockData)

      renderHook(() => useClusteredLocations(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(getClusteredLocations).toHaveBeenCalledWith({
          enabled: 'false',
          radius: '500',
          min_size: '3',
        })
      })
    })
  })

  describe('Settings management', () => {
    it('provides setEnabled function', async () => {
      const mockData = {
        clusters: [],
        unclustered: [],
        metadata: {},
      }
      getClusteredLocations.mockResolvedValue(mockData)

      const { result } = renderHook(() => useClusteredLocations(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      // Initial state
      expect(result.current.settings.enabled).toBe(true)

      // Toggle enabled
      act(() => {
        result.current.setEnabled(false)
      })

      expect(result.current.settings.enabled).toBe(false)
    })

    it('provides setRadius function', async () => {
      const mockData = {
        clusters: [],
        unclustered: [],
        metadata: {},
      }
      getClusteredLocations.mockResolvedValue(mockData)

      const { result } = renderHook(() => useClusteredLocations(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      // Initial radius
      expect(result.current.settings.radius).toBe(100)

      // Change radius
      act(() => {
        result.current.setRadius(250)
      })

      expect(result.current.settings.radius).toBe(250)
    })

    it('provides setMinSize function', async () => {
      const mockData = {
        clusters: [],
        unclustered: [],
        metadata: {},
      }
      getClusteredLocations.mockResolvedValue(mockData)

      const { result } = renderHook(() => useClusteredLocations(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      // Initial minSize
      expect(result.current.settings.minSize).toBe(2)

      // Change minSize
      act(() => {
        result.current.setMinSize(5)
      })

      expect(result.current.settings.minSize).toBe(5)
    })

    it('refetches data when settings change', async () => {
      const mockData = {
        clusters: [],
        unclustered: [],
        metadata: {},
      }
      getClusteredLocations.mockResolvedValue(mockData)

      const { result } = renderHook(() => useClusteredLocations(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(getClusteredLocations).toHaveBeenCalledTimes(1)

      // Change radius
      act(() => {
        result.current.setRadius(500)
      })

      await waitFor(() => {
        expect(getClusteredLocations).toHaveBeenCalledTimes(2)
        expect(getClusteredLocations).toHaveBeenCalledWith({
          enabled: 'true',
          radius: '500',
          min_size: '2',
        })
      })
    })
  })

  describe('localStorage persistence', () => {
    it('saves settings to localStorage when changed', async () => {
      const mockData = {
        clusters: [],
        unclustered: [],
        metadata: {},
      }
      getClusteredLocations.mockResolvedValue(mockData)

      const { result } = renderHook(() => useClusteredLocations(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      act(() => {
        result.current.setRadius(750)
      })

      await waitFor(() => {
        const saved = JSON.parse(
          localStorage.getItem('mothbox_clustering_settings')
        )
        expect(saved.radius).toBe(750)
      })
    })

    it('handles corrupt localStorage gracefully', async () => {
      localStorage.setItem('mothbox_clustering_settings', 'invalid json')

      const mockData = {
        clusters: [],
        unclustered: [],
        metadata: {},
      }
      getClusteredLocations.mockResolvedValueOnce(mockData)

      const { result } = renderHook(() => useClusteredLocations(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      // Should fall back to defaults
      expect(result.current.settings.radius).toBe(100)
      expect(result.current.settings.enabled).toBe(true)
    })
  })

  describe('Error handling', () => {
    it('handles API errors gracefully', async () => {
      const error = new Error('Request failed with status code 500')
      error.response = { status: 500, statusText: 'Internal Server Error' }
      getClusteredLocations.mockRejectedValueOnce(error)

      const { result } = renderHook(() => useClusteredLocations(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.error).toBeDefined()
      expect(result.current.clusters).toEqual([])
      expect(result.current.unclustered).toEqual([])
      expect(result.current.metadata).toEqual({})
    })

    it('handles network errors gracefully', async () => {
      const error = new Error('Network request failed')
      getClusteredLocations.mockRejectedValueOnce(error)

      const { result } = renderHook(() => useClusteredLocations(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.error).toBeDefined()
      expect(result.current.error.message).toBe('Network request failed')
      expect(result.current.clusters).toEqual([])
    })
  })

  describe('Refetch functionality', () => {
    it('provides refetch function', async () => {
      const mockData = {
        clusters: [],
        unclustered: [],
        metadata: {},
      }
      getClusteredLocations.mockResolvedValue(mockData)

      const { result } = renderHook(() => useClusteredLocations(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(getClusteredLocations).toHaveBeenCalledTimes(1)
      expect(typeof result.current.refetch).toBe('function')

      // Call refetch
      await act(async () => {
        await result.current.refetch()
      })

      // Should have made another API call
      expect(getClusteredLocations).toHaveBeenCalledTimes(2)
    })
  })

  describe('Cleanup', () => {
    it('cleans up on unmount without errors', async () => {
      const mockData = {
        clusters: [],
        unclustered: [],
        metadata: {},
      }
      getClusteredLocations.mockResolvedValueOnce(mockData)

      const { unmount } = renderHook(() => useClusteredLocations(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(getClusteredLocations).toHaveBeenCalled()
      })

      expect(() => unmount()).not.toThrow()
    })
  })
})

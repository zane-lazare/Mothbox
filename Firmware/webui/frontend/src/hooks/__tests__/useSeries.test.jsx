import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { useSeries, useSeriesById } from '../useSeries'
import { api } from '../../utils/api'

// Mock the API module
vi.mock('../../utils/api', () => ({
  api: {
    get: vi.fn(),
  },
}))

/**
 * Test suite for useSeries hooks
 *
 * Tests the custom hooks for fetching photo series data using TanStack Query.
 * Verifies loading states, success scenarios, error handling, caching, and
 * conditional fetching behavior.
 */
describe('useSeries', () => {
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

  describe('useSeries hook', () => {
    describe('Success scenarios', () => {
      it('fetches series list successfully', async () => {
        const mockSeriesData = {
          series: [
            {
              series_id: 'hdr_moth_2024_01_15__10_00_00',
              series_type: 'hdr',
              photos: [
                '/photos/moth_2024_01_15__10_00_00_HDR0.jpg',
                '/photos/moth_2024_01_15__10_00_00_HDR1.jpg',
                '/photos/moth_2024_01_15__10_00_00_HDR2.jpg',
              ],
              count: 3,
              cover_photo: '/photos/moth_2024_01_15__10_00_00_HDR0.jpg',
            },
          ],
          total: 1,
          pagination: {
            offset: 0,
            limit: 50,
            has_next: false,
          },
        }

        api.get.mockResolvedValueOnce({ data: mockSeriesData })

        const { result } = renderHook(
          () => useSeries(),
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
        expect(result.current.data).toEqual(mockSeriesData)
      })

      it('uses correct API endpoint', async () => {
        const mockSeriesData = { series: [], total: 0 }
        api.get.mockResolvedValueOnce({ data: mockSeriesData })

        renderHook(
          () => useSeries(),
          { wrapper: createWrapper() }
        )

        await waitFor(() => {
          expect(api.get).toHaveBeenCalledWith('/gallery/series', { params: {} })
        })
      })

      it('passes query params to API', async () => {
        const mockSeriesData = { series: [], total: 0 }
        api.get.mockResolvedValueOnce({ data: mockSeriesData })

        renderHook(
          () => useSeries({ limit: 20, offset: 10, type: 'hdr' }),
          { wrapper: createWrapper() }
        )

        await waitFor(() => {
          expect(api.get).toHaveBeenCalledWith('/gallery/series', {
            params: { limit: 20, offset: 10, type: 'hdr' },
          })
        })
      })

      it('caches series data', async () => {
        const mockSeriesData = { series: [], total: 0 }
        api.get.mockResolvedValue({ data: mockSeriesData })

        const wrapper = createWrapper()

        // First render - should fetch
        const { result: result1, unmount: unmount1 } = renderHook(
          () => useSeries(),
          { wrapper }
        )

        await waitFor(() => {
          expect(result1.current.isSuccess).toBe(true)
        })

        expect(api.get).toHaveBeenCalledTimes(1)

        unmount1()

        // Second render - should use cache
        const { result: result2 } = renderHook(
          () => useSeries(),
          { wrapper }
        )

        await waitFor(() => {
          expect(result2.current.isSuccess).toBe(true)
        })

        // Should still only have 1 fetch call (cached)
        expect(api.get).toHaveBeenCalledTimes(1)
      })

      it('uses correct query key format', async () => {
        const mockSeriesData = { series: [], total: 0 }
        api.get.mockResolvedValueOnce({ data: mockSeriesData })

        const wrapper = createWrapper()

        renderHook(
          () => useSeries(),
          { wrapper }
        )

        await waitFor(() => {
          const cachedData = queryClient.getQueryData(['series'])
          expect(cachedData).toEqual(mockSeriesData)
        })
      })

      it('uses different cache key with params', async () => {
        const mockSeriesData = { series: [], total: 0 }
        api.get.mockResolvedValueOnce({ data: mockSeriesData })

        const wrapper = createWrapper()

        renderHook(
          () => useSeries({ type: 'hdr' }),
          { wrapper }
        )

        await waitFor(() => {
          const cachedData = queryClient.getQueryData(['series', { type: 'hdr' }])
          expect(cachedData).toEqual(mockSeriesData)
        })
      })
    })

    describe('Loading state', () => {
      it('returns loading state initially', () => {
        api.get.mockImplementation(() => new Promise(() => {})) // Never resolves

        const { result } = renderHook(
          () => useSeries(),
          { wrapper: createWrapper() }
        )

        expect(result.current.isLoading).toBe(true)
        expect(result.current.isError).toBe(false)
        expect(result.current.isSuccess).toBe(false)
        expect(result.current.data).toBeUndefined()
      })
    })

    describe('Error handling', () => {
      it('handles 404 errors gracefully', async () => {
        const error = new Error('Request failed with status code 404')
        error.response = { status: 404, statusText: 'Not Found' }
        api.get.mockRejectedValueOnce(error)

        const { result } = renderHook(
          () => useSeries(),
          { wrapper: createWrapper() }
        )

        await waitFor(() => {
          expect(result.current.isError).toBe(true)
        })

        expect(result.current.isLoading).toBe(false)
        expect(result.current.isSuccess).toBe(false)
        expect(result.current.data).toBeUndefined()
        expect(result.current.error).toBeDefined()
      })

      it('handles 500 server errors gracefully', async () => {
        const error = new Error('Request failed with status code 500')
        error.response = { status: 500, statusText: 'Internal Server Error' }
        api.get.mockRejectedValueOnce(error)

        const { result } = renderHook(
          () => useSeries(),
          { wrapper: createWrapper() }
        )

        await waitFor(() => {
          expect(result.current.isError).toBe(true)
        })

        expect(result.current.error).toBeDefined()
      })

      it('handles network errors gracefully', async () => {
        api.get.mockRejectedValueOnce(new Error('Network request failed'))

        const { result } = renderHook(
          () => useSeries(),
          { wrapper: createWrapper() }
        )

        await waitFor(() => {
          expect(result.current.isError).toBe(true)
        })

        expect(result.current.error.message).toBe('Network request failed')
      })
    })

    describe('Enabled option', () => {
      it('does not fetch when enabled is false', () => {
        const { result } = renderHook(
          () => useSeries({}, { enabled: false }),
          { wrapper: createWrapper() }
        )

        expect(result.current.isLoading).toBe(false)
        expect(result.current.isError).toBe(false)
        expect(result.current.isSuccess).toBe(false)
        expect(api.get).not.toHaveBeenCalled()
      })

      it('fetches when enabled changes from false to true', async () => {
        const mockSeriesData = { series: [], total: 0 }
        api.get.mockResolvedValueOnce({ data: mockSeriesData })

        const { result, rerender } = renderHook(
          ({ enabled }) => useSeries({}, { enabled }),
          {
            wrapper: createWrapper(),
            initialProps: { enabled: false },
          }
        )

        // Initially should not fetch
        expect(result.current.isLoading).toBe(false)
        expect(api.get).not.toHaveBeenCalled()

        // Enable fetching
        rerender({ enabled: true })

        await waitFor(() => {
          expect(result.current.isSuccess).toBe(true)
        })

        expect(api.get).toHaveBeenCalledTimes(1)
      })
    })
  })

  describe('useSeriesById hook', () => {
    describe('Success scenarios', () => {
      it('fetches single series successfully', async () => {
        const mockSeries = {
          series_id: 'hdr_moth_2024_01_15__10_00_00',
          series_type: 'hdr',
          photos: [
            {
              path: '/photos/moth_2024_01_15__10_00_00_HDR0.jpg',
              filename: 'moth_2024_01_15__10_00_00_HDR0.jpg',
              date: '2024-01-15T10:00:00Z',
            },
            {
              path: '/photos/moth_2024_01_15__10_00_00_HDR1.jpg',
              filename: 'moth_2024_01_15__10_00_00_HDR1.jpg',
              date: '2024-01-15T10:00:00Z',
            },
          ],
          count: 2,
          cover_photo: '/photos/moth_2024_01_15__10_00_00_HDR0.jpg',
        }

        api.get.mockResolvedValueOnce({ data: mockSeries })

        const { result } = renderHook(
          () => useSeriesById('hdr_moth_2024_01_15__10_00_00'),
          { wrapper: createWrapper() }
        )

        // Initially loading
        expect(result.current.isLoading).toBe(true)

        await waitFor(() => {
          expect(result.current.isSuccess).toBe(true)
        })

        expect(result.current.data).toEqual(mockSeries)
      })

      it('uses correct API endpoint', async () => {
        const mockSeries = { series_id: 'test_series' }
        api.get.mockResolvedValueOnce({ data: mockSeries })

        renderHook(
          () => useSeriesById('test_series'),
          { wrapper: createWrapper() }
        )

        await waitFor(() => {
          expect(api.get).toHaveBeenCalledWith('/gallery/series/test_series')
        })
      })

      it('URL encodes series ID', async () => {
        const mockSeries = { series_id: 'series with spaces' }
        api.get.mockResolvedValueOnce({ data: mockSeries })

        renderHook(
          () => useSeriesById('series with spaces'),
          { wrapper: createWrapper() }
        )

        await waitFor(() => {
          expect(api.get).toHaveBeenCalledWith(
            `/gallery/series/${encodeURIComponent('series with spaces')}`
          )
        })
      })

      it('caches series by ID', async () => {
        const seriesId = 'cached_series'
        const mockSeries = { series_id: seriesId }
        api.get.mockResolvedValue({ data: mockSeries })

        const wrapper = createWrapper()

        // First render - should fetch
        const { result: result1, unmount: unmount1 } = renderHook(
          () => useSeriesById(seriesId),
          { wrapper }
        )

        await waitFor(() => {
          expect(result1.current.isSuccess).toBe(true)
        })

        expect(api.get).toHaveBeenCalledTimes(1)

        unmount1()

        // Second render - should use cache
        const { result: result2 } = renderHook(
          () => useSeriesById(seriesId),
          { wrapper }
        )

        await waitFor(() => {
          expect(result2.current.isSuccess).toBe(true)
        })

        expect(api.get).toHaveBeenCalledTimes(1)
        expect(result2.current.data).toEqual(mockSeries)
      })

      it('uses correct query key format', async () => {
        const seriesId = 'test_series_123'
        const mockSeries = { series_id: seriesId }
        api.get.mockResolvedValueOnce({ data: mockSeries })

        const wrapper = createWrapper()

        renderHook(
          () => useSeriesById(seriesId),
          { wrapper }
        )

        await waitFor(() => {
          const cachedData = queryClient.getQueryData(['series', seriesId])
          expect(cachedData).toEqual(mockSeries)
        })
      })
    })

    describe('Conditional fetching', () => {
      it('does not fetch when seriesId is null', () => {
        const { result } = renderHook(
          () => useSeriesById(null),
          { wrapper: createWrapper() }
        )

        expect(result.current.isLoading).toBe(false)
        expect(result.current.isError).toBe(false)
        expect(result.current.isSuccess).toBe(false)
        expect(api.get).not.toHaveBeenCalled()
      })

      it('does not fetch when seriesId is undefined', () => {
        const { result } = renderHook(
          () => useSeriesById(undefined),
          { wrapper: createWrapper() }
        )

        expect(result.current.isLoading).toBe(false)
        expect(api.get).not.toHaveBeenCalled()
      })

      it('does not fetch when seriesId is empty string', () => {
        const { result } = renderHook(
          () => useSeriesById(''),
          { wrapper: createWrapper() }
        )

        expect(result.current.isLoading).toBe(false)
        expect(api.get).not.toHaveBeenCalled()
      })

      it('fetches when seriesId changes from null to valid', async () => {
        const mockSeries = { series_id: 'new_series' }
        api.get.mockResolvedValueOnce({ data: mockSeries })

        const { result, rerender } = renderHook(
          ({ id }) => useSeriesById(id),
          {
            wrapper: createWrapper(),
            initialProps: { id: null },
          }
        )

        expect(result.current.isLoading).toBe(false)
        expect(api.get).not.toHaveBeenCalled()

        rerender({ id: 'new_series' })

        await waitFor(() => {
          expect(result.current.isSuccess).toBe(true)
        })

        expect(api.get).toHaveBeenCalledTimes(1)
        expect(result.current.data).toEqual(mockSeries)
      })
    })

    describe('Error handling', () => {
      it('handles 404 for non-existent series', async () => {
        const error = new Error('Request failed with status code 404')
        error.response = { status: 404, statusText: 'Not Found' }
        api.get.mockRejectedValueOnce(error)

        const { result } = renderHook(
          () => useSeriesById('nonexistent'),
          { wrapper: createWrapper() }
        )

        await waitFor(() => {
          expect(result.current.isError).toBe(true)
        })

        expect(result.current.data).toBeUndefined()
        expect(result.current.error).toBeDefined()
      })

      it('handles network errors', async () => {
        api.get.mockRejectedValueOnce(new Error('Network request failed'))

        const { result } = renderHook(
          () => useSeriesById('some_series'),
          { wrapper: createWrapper() }
        )

        await waitFor(() => {
          expect(result.current.isError).toBe(true)
        })

        expect(result.current.error.message).toBe('Network request failed')
      })
    })

    describe('Data updates', () => {
      it('fetches new series when seriesId changes', async () => {
        const series1 = { series_id: 'series_1' }
        const series2 = { series_id: 'series_2' }

        api.get
          .mockResolvedValueOnce({ data: series1 })
          .mockResolvedValueOnce({ data: series2 })

        const { result, rerender } = renderHook(
          ({ id }) => useSeriesById(id),
          {
            wrapper: createWrapper(),
            initialProps: { id: 'series_1' },
          }
        )

        await waitFor(() => {
          expect(result.current.isSuccess).toBe(true)
        })

        expect(result.current.data).toEqual(series1)
        expect(api.get).toHaveBeenCalledTimes(1)

        rerender({ id: 'series_2' })

        await waitFor(() => {
          expect(result.current.data).toEqual(series2)
        })

        expect(api.get).toHaveBeenCalledTimes(2)
      })
    })

    describe('Cleanup', () => {
      it('cleans up on unmount without errors', async () => {
        const mockSeries = { series_id: 'cleanup_test' }
        api.get.mockResolvedValueOnce({ data: mockSeries })

        const { unmount } = renderHook(
          () => useSeriesById('cleanup_test'),
          { wrapper: createWrapper() }
        )

        await waitFor(() => {
          expect(api.get).toHaveBeenCalled()
        })

        expect(() => unmount()).not.toThrow()
      })
    })
  })
})

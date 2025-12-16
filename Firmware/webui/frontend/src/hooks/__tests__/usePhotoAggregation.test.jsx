import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { usePhotoAggregation } from '../usePhotoAggregation'
import { api } from '../../utils/api'

// Mock the api module
vi.mock('../../utils/api', () => ({
  api: {
    post: vi.fn()
  }
}))

describe('usePhotoAggregation', () => {
  let queryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false }
      }
    })
    vi.clearAllMocks()
  })

  const wrapper = ({ children }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )

  it('should aggregate photo metadata successfully', async () => {
    const mockResponse = {
      data: {
        photo_count: 10,
        date_start: '2024-01-15',
        date_end: '2024-01-31',
        latitude: 37.7749,
        longitude: -122.4194,
        altitude: 15.5,
        gps_consistent: true,
        gps_error: null,
        photos_with_gps: 8,
        photos_with_timestamp: 10
      }
    }

    api.post.mockResolvedValue(mockResponse)

    const { result } = renderHook(() => usePhotoAggregation(), { wrapper })

    result.current.mutate({
      filter: { date_start: '2024-01-01' },
      tolerance_m: 50.0
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(api.post).toHaveBeenCalledWith('/export/aggregate', {
      filter: { date_start: '2024-01-01' },
      tolerance_m: 50.0
    })

    expect(result.current.data).toEqual(mockResponse.data)
  })

  it('should use default tolerance when not provided', async () => {
    const mockResponse = {
      data: {
        photo_count: 5,
        date_start: '2024-02-01',
        date_end: '2024-02-15',
        gps_consistent: false,
        gps_error: 'GPS coordinates differ by more than 50.0m',
        latitude: null,
        longitude: null,
        altitude: null,
        photos_with_gps: 3,
        photos_with_timestamp: 5
      }
    }

    api.post.mockResolvedValue(mockResponse)

    const { result } = renderHook(() => usePhotoAggregation(), { wrapper })

    result.current.mutate({
      filter: { deployment: '/photos/test' }
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(api.post).toHaveBeenCalledWith('/export/aggregate', {
      filter: { deployment: '/photos/test' },
      tolerance_m: 50.0 // Default value
    })
  })

  it('should handle GPS inconsistency', async () => {
    const mockResponse = {
      data: {
        photo_count: 20,
        date_start: '2024-03-01',
        date_end: '2024-03-31',
        latitude: null,
        longitude: null,
        altitude: null,
        gps_consistent: false,
        gps_error: 'GPS coordinates differ by more than 50.0m (max distance: 1523.4m)',
        photos_with_gps: 15,
        photos_with_timestamp: 20
      }
    }

    api.post.mockResolvedValue(mockResponse)

    const { result } = renderHook(() => usePhotoAggregation(), { wrapper })

    result.current.mutate({
      filter: {},
      tolerance_m: 50.0
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data.gps_consistent).toBe(false)
    expect(result.current.data.gps_error).toContain('1523.4m')
    expect(result.current.data.latitude).toBeNull()
    expect(result.current.data.longitude).toBeNull()
  })

  it('should handle API errors', async () => {
    const mockError = {
      response: {
        data: {
          error: 'No photos found matching filter'
        }
      }
    }

    api.post.mockRejectedValue(mockError)

    const { result } = renderHook(() => usePhotoAggregation(), { wrapper })

    result.current.mutate({
      filter: { date_start: '2025-01-01' },
      tolerance_m: 100.0
    })

    await waitFor(() => expect(result.current.isError).toBe(true))

    expect(result.current.error).toBeDefined()
  })

  it('should handle custom tolerance values', async () => {
    const mockResponse = {
      data: {
        photo_count: 7,
        date_start: '2024-04-01',
        date_end: '2024-04-10',
        latitude: 35.9606,
        longitude: -83.9207,
        altitude: 350.5,
        gps_consistent: true,
        gps_error: null,
        photos_with_gps: 7,
        photos_with_timestamp: 7
      }
    }

    api.post.mockResolvedValue(mockResponse)

    const { result } = renderHook(() => usePhotoAggregation(), { wrapper })

    result.current.mutate({
      filter: { tags: ['moth'] },
      tolerance_m: 100.0
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(api.post).toHaveBeenCalledWith('/export/aggregate', {
      filter: { tags: ['moth'] },
      tolerance_m: 100.0
    })
  })

  it('should handle empty filter', async () => {
    const mockResponse = {
      data: {
        photo_count: 100,
        date_start: '2024-01-01',
        date_end: '2024-12-31',
        latitude: 37.7749,
        longitude: -122.4194,
        altitude: null,
        gps_consistent: true,
        gps_error: null,
        photos_with_gps: 85,
        photos_with_timestamp: 100
      }
    }

    api.post.mockResolvedValue(mockResponse)

    const { result } = renderHook(() => usePhotoAggregation(), { wrapper })

    result.current.mutate({
      filter: {},
      tolerance_m: 50.0
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data.photo_count).toBe(100)
  })
})

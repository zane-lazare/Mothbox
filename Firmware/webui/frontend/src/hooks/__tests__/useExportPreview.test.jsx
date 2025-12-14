import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import useExportPreview from '../useExportPreview'
import { api } from '../../utils/api'

// Mock the API
vi.mock('../../utils/api', () => ({
  api: {
    get: vi.fn()
  }
}))

describe('useExportPreview', () => {
  let queryClient

  // Create wrapper with QueryClientProvider
  const createWrapper = () => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
          gcTime: 0
        }
      }
    })

    return ({ children }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    )
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns loading state initially', () => {
    api.get.mockResolvedValue({ data: { photos: [] } })

    const { result } = renderHook(
      () => useExportPreview({
        format: 'json',
        filter: {},
        selectedFields: ['filename', 'tags']
      }),
      { wrapper: createWrapper() }
    )

    expect(result.current.isLoading).toBe(true)
    expect(result.current.previewData).toBeUndefined()
  })

  it('fetches sample photos based on filter', async () => {
    const mockPhotos = [
      {
        photo_path: '/photos/photo1.jpg',
        filename: 'photo1.jpg',
        tags: ['moth', 'night'],
        latitude: 37.7749,
        longitude: -122.4194
      },
      {
        photo_path: '/photos/photo2.jpg',
        filename: 'photo2.jpg',
        tags: ['butterfly'],
        latitude: 37.7750,
        longitude: -122.4195
      }
    ]

    api.get.mockResolvedValue({
      data: {
        photos: mockPhotos,
        total: 2
      }
    })

    const filter = {
      date_start: '2024-01-01',
      date_end: '2024-12-31',
      tags: ['moth']
    }

    const { result } = renderHook(
      () => useExportPreview({
        format: 'json',
        filter,
        selectedFields: ['filename', 'tags']
      }),
      { wrapper: createWrapper() }
    )

    await waitFor(() => expect(result.current.isLoading).toBe(false))

    // Check API was called with correct parameters
    expect(api.get).toHaveBeenCalledWith('/sidecar/photos', {
      params: expect.objectContaining({
        limit: 3,
        date_start: '2024-01-01',
        date_end: '2024-12-31',
        tags: 'moth'
      })
    })

    expect(result.current.previewData).toBeDefined()
    expect(result.current.error).toBeNull()
  })

  it('transforms data to JSON format with selected fields only', async () => {
    const mockPhotos = [
      {
        photo_path: '/photos/photo1.jpg',
        filename: 'photo1.jpg',
        tags: ['moth', 'night'],
        latitude: 37.7749,
        longitude: -122.4194,
        altitude: 100,
        notes: 'Test note'
      }
    ]

    api.get.mockResolvedValue({
      data: { photos: mockPhotos }
    })

    const { result } = renderHook(
      () => useExportPreview({
        format: 'json',
        filter: {},
        selectedFields: ['filename', 'tags', 'latitude']
      }),
      { wrapper: createWrapper() }
    )

    await waitFor(() => expect(result.current.isLoading).toBe(false))

    const preview = result.current.previewData
    expect(preview).toBeDefined()
    expect(preview.format).toBe('json')

    // Check that only selected fields are included
    const firstPhoto = preview.data[0]
    expect(firstPhoto).toHaveProperty('filename')
    expect(firstPhoto).toHaveProperty('tags')
    expect(firstPhoto).toHaveProperty('latitude')
    expect(firstPhoto).not.toHaveProperty('longitude')
    expect(firstPhoto).not.toHaveProperty('altitude')
    expect(firstPhoto).not.toHaveProperty('notes')
  })

  it('transforms data to CSV format', async () => {
    const mockPhotos = [
      {
        photo_path: '/photos/photo1.jpg',
        filename: 'photo1.jpg',
        tags: ['moth'],
        latitude: 37.7749
      }
    ]

    api.get.mockResolvedValue({
      data: { photos: mockPhotos }
    })

    const selectedFields = ['filename', 'tags', 'latitude']
    const { result } = renderHook(
      () => useExportPreview({
        format: 'csv',
        filter: {},
        selectedFields
      }),
      { wrapper: createWrapper() }
    )

    await waitFor(() => expect(result.current.isLoading).toBe(false))

    const preview = result.current.previewData
    expect(preview.format).toBe('csv')
    expect(preview.data).toBeDefined()
    // Headers should match selectedFields
    expect(preview.headers).toEqual(expect.arrayContaining(selectedFields))
    expect(preview.headers.length).toBe(selectedFields.length)
  })

  it('handles empty results', async () => {
    api.get.mockResolvedValue({
      data: { photos: [] }
    })

    const { result } = renderHook(
      () => useExportPreview({
        format: 'json',
        filter: {},
        selectedFields: ['filename']
      }),
      { wrapper: createWrapper() }
    )

    await waitFor(() => expect(result.current.isLoading).toBe(false))

    expect(result.current.previewData).toBeDefined()
    expect(result.current.previewData.data).toEqual([])
    expect(result.current.error).toBeNull()
  })

  it('handles API errors', async () => {
    api.get.mockRejectedValue(new Error('Network error'))

    const { result } = renderHook(
      () => useExportPreview({
        format: 'json',
        filter: {},
        selectedFields: ['filename']
      }),
      { wrapper: createWrapper() }
    )

    await waitFor(() => expect(result.current.isError).toBe(true))

    expect(result.current.error).toBeDefined()
    expect(result.current.previewData).toBeUndefined()
  })

  it('uses staleTime for debouncing behavior', async () => {
    api.get.mockResolvedValue({
      data: { photos: [] }
    })

    const { result } = renderHook(
      () => useExportPreview({
        format: 'json',
        filter: {},
        selectedFields: ['filename']
      }),
      { wrapper: createWrapper() }
    )

    await waitFor(() => expect(result.current.isLoading).toBe(false))

    // Should have been called once
    expect(api.get).toHaveBeenCalledTimes(1)
  })

  it('includes deployment data when available', async () => {
    const mockPhotos = [
      {
        photo_path: '/photos/photo1.jpg',
        filename: 'photo1.jpg',
        deployment_name: 'Forest Survey 2024',
        mothbox_id: 'mothbox-001'
      }
    ]

    api.get.mockResolvedValue({
      data: { photos: mockPhotos }
    })

    const { result } = renderHook(
      () => useExportPreview({
        format: 'json',
        filter: {},
        selectedFields: ['filename', 'deployment_name', 'mothbox_id']
      }),
      { wrapper: createWrapper() }
    )

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    }, { timeout: 3000 })

    expect(result.current.previewData).toBeDefined()
    const firstPhoto = result.current.previewData.data[0]
    expect(firstPhoto.deployment_name).toBe('Forest Survey 2024')
    expect(firstPhoto.mothbox_id).toBe('mothbox-001')
  })

  it('limits results to 3 photos', async () => {
    const mockPhotos = Array.from({ length: 10 }, (_, i) => ({
      photo_path: `/photos/photo${i}.jpg`,
      filename: `photo${i}.jpg`
    }))

    api.get.mockResolvedValue({
      data: { photos: mockPhotos }
    })

    const { result } = renderHook(
      () => useExportPreview({
        format: 'json',
        filter: {},
        selectedFields: ['filename']
      }),
      { wrapper: createWrapper() }
    )

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    }, { timeout: 3000 })

    // API should request limit of 3
    expect(api.get).toHaveBeenCalledWith('/sidecar/photos', {
      params: expect.objectContaining({
        limit: 3
      })
    })
  })

  it('refetches when format changes', async () => {
    api.get.mockResolvedValue({
      data: { photos: [] }
    })

    const { rerender } = renderHook(
      ({ format }) => useExportPreview({
        format,
        filter: {},
        selectedFields: ['filename']
      }),
      {
        wrapper: createWrapper(),
        initialProps: { format: 'json' }
      }
    )

    await waitFor(() => {
      expect(api.get).toHaveBeenCalledTimes(1)
    }, { timeout: 3000 })

    // Change format
    rerender({ format: 'csv' })

    await waitFor(() => {
      // Should trigger another fetch (new query key)
      expect(api.get).toHaveBeenCalledTimes(2)
    }, { timeout: 3000 })
  })
})

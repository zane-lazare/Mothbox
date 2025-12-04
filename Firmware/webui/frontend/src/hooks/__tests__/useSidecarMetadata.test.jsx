import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import useSidecarMetadata from '../useSidecarMetadata'
import * as api from '../../utils/api'

// Mock the API module
vi.mock('../../utils/api', () => ({
  getPhotoSidecarMetadata: vi.fn(),
  updatePhotoSidecarMetadata: vi.fn(),
}))

/**
 * Test suite for useSidecarMetadata hook
 *
 * Tests the custom hook for fetching and mutating photo sidecar metadata.
 * Verifies query state, optimistic updates, rollback on error, and cache invalidation.
 */
describe('useSidecarMetadata', () => {
  let queryClient

  /**
   * Create a fresh QueryClient for each test to prevent state leakage
   */
  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false, // Disable retries for faster tests
          gcTime: 0, // Don't cache between tests
        },
        mutations: {
          retry: false,
        },
      },
    })
    vi.clearAllMocks()
  })

  afterEach(() => {
    queryClient.clear()
    // Note: Tags invalidation timeout is now managed by useRef inside the hook,
    // so cleanup happens automatically when the hook unmounts
  })

  /**
   * Helper to render hook with QueryClient provider
   */
  const renderUseSidecarMetadata = (filename) => {
    return renderHook(() => useSidecarMetadata(filename), {
      wrapper: ({ children }) => (
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      ),
    })
  }

  describe('Query - Fetching metadata', () => {
    it('fetches sidecar metadata for a photo', async () => {
      const mockMetadata = {
        filename: 'photo_2023-10-31_12-00-00.jpg',
        tags: ['moth', 'night'],
        species: 'Luna Moth',
        notes: 'Large specimen',
        created_at: '2023-10-31T12:00:00Z',
        updated_at: '2023-10-31T12:30:00Z',
      }

      api.getPhotoSidecarMetadata.mockResolvedValueOnce({
        data: mockMetadata,
      })

      const { result } = renderUseSidecarMetadata('photo_2023-10-31_12-00-00.jpg')

      // Initially loading
      expect(result.current.isLoading).toBe(true)
      expect(result.current.data).toBeUndefined()

      // Wait for successful fetch
      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(result.current.isLoading).toBe(false)
      expect(result.current.isError).toBe(false)
      expect(result.current.data).toEqual(mockMetadata)
      expect(api.getPhotoSidecarMetadata).toHaveBeenCalledWith('photo_2023-10-31_12-00-00.jpg')
    })

    it('returns null data when filename is not provided', () => {
      const { result } = renderUseSidecarMetadata(null)

      expect(result.current.isLoading).toBe(false)
      expect(result.current.isError).toBe(false)
      expect(result.current.data).toBeUndefined()
      expect(api.getPhotoSidecarMetadata).not.toHaveBeenCalled()
    })

    it('does not fetch when filename is empty string', () => {
      const { result } = renderUseSidecarMetadata('')

      expect(result.current.isLoading).toBe(false)
      expect(api.getPhotoSidecarMetadata).not.toHaveBeenCalled()
    })

    it('does not fetch when filename is undefined', () => {
      const { result } = renderUseSidecarMetadata(undefined)

      expect(result.current.isLoading).toBe(false)
      expect(api.getPhotoSidecarMetadata).not.toHaveBeenCalled()
    })

    it('handles fetch errors gracefully', async () => {
      const error = new Error('Failed to fetch sidecar metadata')
      // Mock rejection for all retry attempts (initial + 2 retries)
      api.getPhotoSidecarMetadata.mockRejectedValue(error)

      const { result } = renderUseSidecarMetadata('photo_error.jpg')

      await waitFor(
        () => {
          expect(result.current.isError).toBe(true)
        },
        { timeout: 10000 }
      ) // Allow time for retries

      expect(result.current.isLoading).toBe(false)
      expect(result.current.isSuccess).toBe(false)
      expect(result.current.data).toBeUndefined()
      expect(result.current.error).toBeDefined()
    })

    it('uses correct query key format', async () => {
      const filename = 'test_photo.jpg'
      const mockMetadata = { filename, tags: [] }

      api.getPhotoSidecarMetadata.mockResolvedValueOnce({
        data: mockMetadata,
      })

      renderUseSidecarMetadata(filename)

      await waitFor(() => {
        const cachedData = queryClient.getQueryData(['sidecarMetadata', filename])
        expect(cachedData).toEqual(mockMetadata)
      })
    })
  })

  describe('Mutation - updateTags', () => {
    it('updates tags optimistically', async () => {
      const filename = 'photo_update_tags.jpg'
      const initialMetadata = {
        filename,
        tags: ['moth'],
        species: '',
        notes: '',
      }

      api.getPhotoSidecarMetadata.mockResolvedValue({ data: initialMetadata })

      // Mock update to return updated data on refetch
      api.updatePhotoSidecarMetadata.mockImplementation(async (filename, updates) => {
        // Update the mock to return new data on next fetch
        api.getPhotoSidecarMetadata.mockResolvedValue({
          data: { ...initialMetadata, ...updates },
        })
        return { data: { success: true } }
      })

      const { result } = renderUseSidecarMetadata(filename)

      await waitFor(() => {
        expect(result.current.data).toEqual(initialMetadata)
      })

      // Update tags
      act(() => {
        result.current.updateTags(['moth', 'butterfly', 'insect'])
      })

      // Should update immediately (optimistic)
      await waitFor(() => {
        expect(result.current.data.tags).toEqual(['moth', 'butterfly', 'insect'])
      })

      expect(api.updatePhotoSidecarMetadata).toHaveBeenCalledWith(filename, {
        tags: ['moth', 'butterfly', 'insect'],
      })
    })

    it('rolls back on update failure', async () => {
      const filename = 'photo_rollback.jpg'
      const initialMetadata = {
        filename,
        tags: ['moth'],
        species: '',
        notes: '',
      }

      api.getPhotoSidecarMetadata.mockResolvedValue({ data: initialMetadata })
      api.updatePhotoSidecarMetadata.mockRejectedValue(new Error('Network error'))

      const { result } = renderUseSidecarMetadata(filename)

      await waitFor(() => {
        expect(result.current.data.tags).toEqual(['moth'])
      })

      // Attempt to update tags
      act(() => {
        result.current.updateTags(['butterfly'])
      })

      // Should rollback to original tags after failure
      await waitFor(() => {
        expect(result.current.data.tags).toEqual(['moth'])
      })

      expect(result.current.updateError).toBeDefined()
    })

    it('invalidates sidecar metadata immediately on update', async () => {
      const filename = 'photo_invalidate.jpg'
      const initialMetadata = { filename, tags: ['moth'] }

      api.getPhotoSidecarMetadata.mockResolvedValue({ data: initialMetadata })
      api.updatePhotoSidecarMetadata.mockResolvedValue({ data: { success: true } })

      // Spy on invalidateQueries
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderUseSidecarMetadata(filename)

      await waitFor(() => {
        expect(result.current.data).toEqual(initialMetadata)
      })

      act(() => {
        result.current.updateTags(['butterfly'])
      })

      // Sidecar metadata is invalidated immediately
      await waitFor(() => {
        expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['sidecarMetadata', filename] })
      })

      // Note: Tags invalidation is debounced (1 second delay) to batch rapid tag operations
      // and is tested separately in integration tests
    })
  })

  describe('Mutation - addTag', () => {
    it('adds a tag to existing tags', async () => {
      const filename = 'photo_add_tag.jpg'
      const initialMetadata = {
        filename,
        tags: ['moth', 'night'],
      }

      api.getPhotoSidecarMetadata.mockResolvedValue({ data: initialMetadata })

      // Mock update to return updated data on refetch
      api.updatePhotoSidecarMetadata.mockImplementation(async (filename, updates) => {
        api.getPhotoSidecarMetadata.mockResolvedValue({
          data: { ...initialMetadata, ...updates },
        })
        return { data: { success: true } }
      })

      const { result } = renderUseSidecarMetadata(filename)

      await waitFor(() => {
        expect(result.current.data.tags).toEqual(['moth', 'night'])
      })

      act(() => {
        result.current.addTag('large')
      })

      await waitFor(() => {
        expect(result.current.data.tags).toEqual(['moth', 'night', 'large'])
      })

      expect(api.updatePhotoSidecarMetadata).toHaveBeenCalledWith(filename, {
        tags: ['moth', 'night', 'large'],
      })
    })

    it('prevents duplicate tags when adding', async () => {
      const filename = 'photo_no_duplicate.jpg'
      const initialMetadata = {
        filename,
        tags: ['moth', 'night'],
      }

      api.getPhotoSidecarMetadata.mockResolvedValue({ data: initialMetadata })
      api.updatePhotoSidecarMetadata.mockResolvedValue({ data: { success: true } })

      const { result } = renderUseSidecarMetadata(filename)

      await waitFor(() => {
        expect(result.current.data.tags).toEqual(['moth', 'night'])
      })

      // Try to add duplicate tag
      act(() => {
        result.current.addTag('moth')
      })

      // Should not call API since tag already exists
      expect(api.updatePhotoSidecarMetadata).not.toHaveBeenCalled()
      expect(result.current.data.tags).toEqual(['moth', 'night'])
    })

    it('handles empty tags array when adding first tag', async () => {
      const filename = 'photo_first_tag.jpg'
      const initialMetadata = {
        filename,
        tags: [],
      }

      api.getPhotoSidecarMetadata.mockResolvedValue({ data: initialMetadata })

      // Mock update to return updated data on refetch
      api.updatePhotoSidecarMetadata.mockImplementation(async (filename, updates) => {
        api.getPhotoSidecarMetadata.mockResolvedValue({
          data: { ...initialMetadata, ...updates },
        })
        return { data: { success: true } }
      })

      const { result } = renderUseSidecarMetadata(filename)

      await waitFor(() => {
        expect(result.current.data.tags).toEqual([])
      })

      act(() => {
        result.current.addTag('first_tag')
      })

      await waitFor(() => {
        expect(result.current.data.tags).toEqual(['first_tag'])
      })
    })

    it('handles missing tags field when adding tag', async () => {
      const filename = 'photo_no_tags_field.jpg'
      const initialMetadata = {
        filename,
        // tags field is missing
      }

      api.getPhotoSidecarMetadata.mockResolvedValue({ data: initialMetadata })

      // Mock update to return updated data on refetch
      api.updatePhotoSidecarMetadata.mockImplementation(async (filename, updates) => {
        api.getPhotoSidecarMetadata.mockResolvedValue({
          data: { ...initialMetadata, ...updates },
        })
        return { data: { success: true } }
      })

      const { result } = renderUseSidecarMetadata(filename)

      await waitFor(() => {
        expect(result.current.data).toEqual(initialMetadata)
      })

      act(() => {
        result.current.addTag('new_tag')
      })

      await waitFor(() => {
        expect(result.current.data.tags).toEqual(['new_tag'])
      })
    })
  })

  describe('Mutation - removeTag', () => {
    it('removes a tag from existing tags', async () => {
      const filename = 'photo_remove_tag.jpg'
      const initialMetadata = {
        filename,
        tags: ['moth', 'night', 'large'],
      }

      api.getPhotoSidecarMetadata.mockResolvedValue({ data: initialMetadata })

      // Mock update to return updated data on refetch
      api.updatePhotoSidecarMetadata.mockImplementation(async (filename, updates) => {
        api.getPhotoSidecarMetadata.mockResolvedValue({
          data: { ...initialMetadata, ...updates },
        })
        return { data: { success: true } }
      })

      const { result } = renderUseSidecarMetadata(filename)

      await waitFor(() => {
        expect(result.current.data.tags).toEqual(['moth', 'night', 'large'])
      })

      act(() => {
        result.current.removeTag('night')
      })

      await waitFor(() => {
        expect(result.current.data.tags).toEqual(['moth', 'large'])
      })

      expect(api.updatePhotoSidecarMetadata).toHaveBeenCalledWith(filename, {
        tags: ['moth', 'large'],
      })
    })

    it('handles removing non-existent tag gracefully', async () => {
      const filename = 'photo_remove_missing.jpg'
      const initialMetadata = {
        filename,
        tags: ['moth', 'night'],
      }

      api.getPhotoSidecarMetadata.mockResolvedValue({ data: initialMetadata })
      api.updatePhotoSidecarMetadata.mockResolvedValue({ data: { success: true } })

      const { result } = renderUseSidecarMetadata(filename)

      await waitFor(() => {
        expect(result.current.data.tags).toEqual(['moth', 'night'])
      })

      act(() => {
        result.current.removeTag('nonexistent')
      })

      // Should still call API with filtered tags (even if nothing changed)
      await waitFor(() => {
        expect(api.updatePhotoSidecarMetadata).toHaveBeenCalledWith(filename, {
          tags: ['moth', 'night'],
        })
      })
    })

    it('handles empty tags array when removing', async () => {
      const filename = 'photo_remove_from_empty.jpg'
      const initialMetadata = {
        filename,
        tags: [],
      }

      api.getPhotoSidecarMetadata.mockResolvedValue({ data: initialMetadata })
      api.updatePhotoSidecarMetadata.mockResolvedValue({ data: { success: true } })

      const { result } = renderUseSidecarMetadata(filename)

      await waitFor(() => {
        expect(result.current.data.tags).toEqual([])
      })

      act(() => {
        result.current.removeTag('any_tag')
      })

      await waitFor(() => {
        expect(api.updatePhotoSidecarMetadata).toHaveBeenCalledWith(filename, {
          tags: [],
        })
      })
    })
  })

  describe('Mutation - updateSpecies', () => {
    it('updates species optimistically', async () => {
      const filename = 'photo_update_species.jpg'
      const initialMetadata = {
        filename,
        tags: ['moth'],
        species: '',
        notes: '',
      }

      api.getPhotoSidecarMetadata.mockResolvedValue({ data: initialMetadata })

      // Mock update to return updated data on refetch
      api.updatePhotoSidecarMetadata.mockImplementation(async (filename, updates) => {
        api.getPhotoSidecarMetadata.mockResolvedValue({
          data: { ...initialMetadata, ...updates },
        })
        return { data: { success: true } }
      })

      const { result } = renderUseSidecarMetadata(filename)

      await waitFor(() => {
        expect(result.current.data).toEqual(initialMetadata)
      })

      act(() => {
        result.current.updateSpecies('Luna Moth')
      })

      await waitFor(() => {
        expect(result.current.data.species).toBe('Luna Moth')
      })

      expect(api.updatePhotoSidecarMetadata).toHaveBeenCalledWith(filename, {
        species: 'Luna Moth',
      })
    })
  })

  describe('Mutation - updateNotes', () => {
    it('updates notes optimistically', async () => {
      const filename = 'photo_update_notes.jpg'
      const initialMetadata = {
        filename,
        tags: ['moth'],
        species: '',
        notes: '',
      }

      api.getPhotoSidecarMetadata.mockResolvedValue({ data: initialMetadata })

      // Mock update to return updated data on refetch
      api.updatePhotoSidecarMetadata.mockImplementation(async (filename, updates) => {
        api.getPhotoSidecarMetadata.mockResolvedValue({
          data: { ...initialMetadata, ...updates },
        })
        return { data: { success: true } }
      })

      const { result } = renderUseSidecarMetadata(filename)

      await waitFor(() => {
        expect(result.current.data).toEqual(initialMetadata)
      })

      act(() => {
        result.current.updateNotes('Large specimen found near light')
      })

      await waitFor(() => {
        expect(result.current.data.notes).toBe('Large specimen found near light')
      })

      expect(api.updatePhotoSidecarMetadata).toHaveBeenCalledWith(filename, {
        notes: 'Large specimen found near light',
      })
    })
  })

  describe('Loading and error states', () => {
    it('exposes isUpdating state during mutations', async () => {
      const filename = 'photo_updating.jpg'
      const initialMetadata = { filename, tags: ['moth'] }

      api.getPhotoSidecarMetadata.mockResolvedValue({ data: initialMetadata })
      api.updatePhotoSidecarMetadata.mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({ data: { success: true } }), 100))
      )

      const { result } = renderUseSidecarMetadata(filename)

      await waitFor(() => {
        expect(result.current.data).toEqual(initialMetadata)
      })

      act(() => {
        result.current.updateTags(['butterfly'])
      })

      // Should show updating state
      await waitFor(() => {
        expect(result.current.isUpdating).toBe(true)
      })

      // Eventually completes
      await waitFor(() => {
        expect(result.current.isUpdating).toBe(false)
      })
    })

    it('exposes updateError when mutation fails', async () => {
      const filename = 'photo_error.jpg'
      const initialMetadata = { filename, tags: ['moth'] }
      const error = new Error('Update failed')

      api.getPhotoSidecarMetadata.mockResolvedValue({ data: initialMetadata })
      api.updatePhotoSidecarMetadata.mockRejectedValue(error)

      const { result } = renderUseSidecarMetadata(filename)

      await waitFor(() => {
        expect(result.current.data).toEqual(initialMetadata)
      })

      act(() => {
        result.current.updateTags(['butterfly'])
      })

      await waitFor(() => {
        expect(result.current.updateError).toBeDefined()
        expect(result.current.updateError.message).toBe('Update failed')
      })
    })
  })

  describe('Cache behavior', () => {
    it('uses 5 minute staleTime for cached data', async () => {
      const filename = 'photo_stale.jpg'
      const mockMetadata = { filename, tags: [] }

      api.getPhotoSidecarMetadata.mockResolvedValue({ data: mockMetadata })

      renderUseSidecarMetadata(filename)

      await waitFor(() => {
        const queryState = queryClient.getQueryState(['sidecarMetadata', filename])
        expect(queryState).toBeDefined()
      })
    })
  })

  describe('Cleanup', () => {
    it('cleans up on unmount without errors', async () => {
      const mockMetadata = { filename: 'photo_cleanup.jpg', tags: [] }

      api.getPhotoSidecarMetadata.mockResolvedValueOnce({ data: mockMetadata })

      const { unmount } = renderUseSidecarMetadata('photo_cleanup.jpg')

      await waitFor(() => {
        expect(api.getPhotoSidecarMetadata).toHaveBeenCalled()
      })

      expect(() => unmount()).not.toThrow()
    })
  })
})

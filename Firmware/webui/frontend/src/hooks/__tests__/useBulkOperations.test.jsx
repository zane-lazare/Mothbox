import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import useBulkOperations from '../useBulkOperations'
import { api, getBulkSidecarMetadata } from '../../utils/api'

// Mock the API
vi.mock('../../utils/api', () => ({
  api: {
    post: vi.fn(),
    delete: vi.fn(),
    get: vi.fn(),
  },
  getBulkSidecarMetadata: vi.fn(),
}))

describe('useBulkOperations', () => {
  let queryClient

  // Helper to wrap hook with QueryClient provider
  const wrapper = ({ children }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })
    vi.clearAllMocks()
  })

  afterEach(() => {
    queryClient.clear()
  })

  describe('bulkAddTags', () => {
    it('calls API with mode=append', async () => {
      const filenames = ['photo1.jpg', 'photo2.jpg']
      const tags = ['moth', 'night']

      // Mock bulk GET for fetching previous state
      getBulkSidecarMetadata.mockResolvedValue({
        data: {
          success: {
            'photo1.jpg': { tags: ['old_tag'] },
            'photo2.jpg': { tags: ['old_tag'] },
          },
          failed: [],
          errors: {},
        }
      })

      api.post.mockResolvedValue({
        data: {
          success: filenames,
          failed: [],
          errors: {},
        }
      })

      const { result } = renderHook(() => useBulkOperations(), { wrapper })

      const response = await result.current.bulkAddTags(filenames, tags)

      expect(api.post).toHaveBeenCalledWith('/sidecar/bulk', {
        filenames,
        updates: { tags },
        mode: 'append'
      })
      expect(response.success).toEqual(filenames)
      expect(response.failed).toEqual([])
    })

    it('returns success and failed results', async () => {
      const filenames = ['photo1.jpg', 'photo2.jpg', 'photo3.jpg']
      const tags = ['moth']

      // Mock bulk GET for fetching previous state
      getBulkSidecarMetadata.mockResolvedValue({
        data: {
          success: {
            'photo1.jpg': { tags: ['old_tag'] },
            'photo2.jpg': { tags: ['old_tag'] },
            'photo3.jpg': { tags: ['old_tag'] },
          },
          failed: [],
          errors: {},
        }
      })

      api.post.mockResolvedValue({
        data: {
          success: ['photo1.jpg', 'photo3.jpg'],
          failed: ['photo2.jpg'],
          errors: { 'photo2.jpg': 'Photo not found' },
        }
      })

      const { result } = renderHook(() => useBulkOperations(), { wrapper })

      const response = await result.current.bulkAddTags(filenames, tags)

      expect(response.success).toEqual(['photo1.jpg', 'photo3.jpg'])
      expect(response.failed).toEqual(['photo2.jpg'])
      expect(response.errors).toEqual({ 'photo2.jpg': 'Photo not found' })
    })
  })

  describe('bulkReplaceTags', () => {
    it('calls API with mode=replace', async () => {
      const filenames = ['photo1.jpg']
      const tags = ['new_tag']

      // Mock bulk GET for fetching previous state
      getBulkSidecarMetadata.mockResolvedValue({
        data: {
          success: {
            'photo1.jpg': { tags: ['old_tag'] },
          },
          failed: [],
          errors: {},
        }
      })

      api.post.mockResolvedValue({
        data: {
          success: filenames,
          failed: [],
          errors: {},
        }
      })

      const { result } = renderHook(() => useBulkOperations(), { wrapper })

      await result.current.bulkReplaceTags(filenames, tags)

      expect(api.post).toHaveBeenCalledWith('/sidecar/bulk', {
        filenames,
        updates: { tags },
        mode: 'replace'
      })
    })
  })

  describe('bulkRemoveTags', () => {
    it('fetches existing tags and removes specified tags', async () => {
      const filenames = ['photo1.jpg', 'photo2.jpg']
      const tagsToRemove = ['night']

      // Mock bulk GET for fetching previous state (which also provides current tags)
      getBulkSidecarMetadata.mockResolvedValue({
        data: {
          success: {
            'photo1.jpg': { tags: ['moth', 'night', 'outdoor'] },
            'photo2.jpg': { tags: ['night', 'luna'] },
          },
          failed: [],
          errors: {},
        }
      })

      api.post.mockResolvedValue({
        data: {
          success: filenames,
          failed: [],
          errors: {},
        }
      })

      const { result } = renderHook(() => useBulkOperations(), { wrapper })

      const response = await result.current.bulkRemoveTags(filenames, tagsToRemove)

      // Should fetch metadata via bulk endpoint
      expect(getBulkSidecarMetadata).toHaveBeenCalledWith(filenames)

      // Should update with filtered tags
      expect(api.post).toHaveBeenCalledWith('/sidecar/bulk', {
        filenames,
        updates: {
          'photo1.jpg': { tags: ['moth', 'outdoor'] },
          'photo2.jpg': { tags: ['luna'] }
        },
        mode: 'individual'
      })

      expect(response.success).toEqual(filenames)
    })

    it('handles photos that already have no tags', async () => {
      const filenames = ['photo1.jpg']
      const tagsToRemove = ['night']

      getBulkSidecarMetadata.mockResolvedValue({
        data: {
          success: {
            'photo1.jpg': { tags: [] },
          },
          failed: [],
          errors: {},
        }
      })

      api.post.mockResolvedValue({
        data: {
          success: filenames,
          failed: [],
          errors: {},
        }
      })

      const { result } = renderHook(() => useBulkOperations(), { wrapper })

      const response = await result.current.bulkRemoveTags(filenames, tagsToRemove)

      expect(api.post).toHaveBeenCalledWith('/sidecar/bulk', {
        filenames,
        updates: {
          'photo1.jpg': { tags: [] }
        },
        mode: 'individual'
      })
    })

    it('handles errors when fetching existing metadata', async () => {
      const filenames = ['photo1.jpg', 'photo2.jpg']
      const tagsToRemove = ['night']

      // Mock photo1 success, photo2 missing from bulk response
      getBulkSidecarMetadata.mockResolvedValue({
        data: {
          success: {
            'photo1.jpg': { tags: ['moth', 'night'] },
          },
          failed: ['photo2.jpg'],
          errors: { 'photo2.jpg': 'Photo not found' },
        }
      })

      api.post.mockResolvedValue({
        data: {
          success: ['photo1.jpg'],
          failed: [],
          errors: {},
        }
      })

      const { result } = renderHook(() => useBulkOperations(), { wrapper })

      const response = await result.current.bulkRemoveTags(filenames, tagsToRemove)

      // Should only update photo1 (photo2 failed to fetch)
      expect(api.post).toHaveBeenCalledWith('/sidecar/bulk', {
        filenames: ['photo1.jpg'],
        updates: {
          'photo1.jpg': { tags: ['moth'] }
        },
        mode: 'individual'
      })

      expect(response.failed).toContain('photo2.jpg')
      expect(response.errors['photo2.jpg']).toBeDefined()
    })
  })

  describe('bulkUpdateSpecies', () => {
    it('calls API with species data', async () => {
      const filenames = ['photo1.jpg', 'photo2.jpg']
      const species = 'Actias luna'

      // Mock bulk GET for fetching previous state
      getBulkSidecarMetadata.mockResolvedValue({
        data: {
          success: {
            'photo1.jpg': { species: 'Unknown' },
            'photo2.jpg': { species: 'Unknown' },
          },
          failed: [],
          errors: {},
        }
      })

      api.post.mockResolvedValue({
        data: {
          success: filenames,
          failed: [],
          errors: {},
        }
      })

      const { result } = renderHook(() => useBulkOperations(), { wrapper })

      await result.current.bulkUpdateSpecies(filenames, species)

      expect(api.post).toHaveBeenCalledWith('/sidecar/bulk', {
        filenames,
        updates: { species },
        mode: 'replace'
      })
    })
  })

  describe('bulkDelete', () => {
    it('calls DELETE endpoint', async () => {
      const filenames = ['photo1.jpg', 'photo2.jpg']

      api.delete.mockResolvedValue({
        data: {
          success: filenames,
          failed: [],
          errors: {},
        }
      })

      const { result } = renderHook(() => useBulkOperations(), { wrapper })

      const response = await result.current.bulkDelete(filenames)

      expect(api.delete).toHaveBeenCalledWith('/gallery/photos/bulk', {
        data: { filenames }
      })
      expect(response.success).toEqual(filenames)
    })

    it('returns success and failed results', async () => {
      const filenames = ['photo1.jpg', 'photo2.jpg']

      api.delete.mockResolvedValue({
        data: {
          success: ['photo1.jpg'],
          failed: ['photo2.jpg'],
          errors: { 'photo2.jpg': 'File not found' },
        }
      })

      const { result } = renderHook(() => useBulkOperations(), { wrapper })

      const response = await result.current.bulkDelete(filenames)

      expect(response.success).toEqual(['photo1.jpg'])
      expect(response.failed).toEqual(['photo2.jpg'])
    })
  })

  describe('Batching', () => {
    it('splits >100 photos into batches', async () => {
      // Create 250 filenames
      const filenames = Array.from({ length: 250 }, (_, i) => `photo${i}.jpg`)
      const tags = ['moth']

      // Mock bulk GET for fetching previous state
      const successObj = {}
      filenames.forEach(f => { successObj[f] = { tags: ['old_tag'] } })
      getBulkSidecarMetadata.mockResolvedValue({
        data: {
          success: successObj,
          failed: [],
          errors: {},
        }
      })

      // Mock each batch call
      api.post.mockResolvedValue({
        data: {
          success: [],
          failed: [],
          errors: {},
        }
      })

      const { result } = renderHook(() => useBulkOperations(), { wrapper })

      await result.current.bulkAddTags(filenames, tags)

      // Should make 3 API calls (100, 100, 50)
      expect(api.post).toHaveBeenCalledTimes(3)

      // Check first batch
      expect(api.post).toHaveBeenNthCalledWith(1, '/sidecar/bulk', {
        filenames: filenames.slice(0, 100),
        updates: { tags },
        mode: 'append'
      })

      // Check second batch
      expect(api.post).toHaveBeenNthCalledWith(2, '/sidecar/bulk', {
        filenames: filenames.slice(100, 200),
        updates: { tags },
        mode: 'append'
      })

      // Check third batch
      expect(api.post).toHaveBeenNthCalledWith(3, '/sidecar/bulk', {
        filenames: filenames.slice(200, 250),
        updates: { tags },
        mode: 'append'
      })
    })

    it('fires progress callback per batch', async () => {
      const filenames = Array.from({ length: 250 }, (_, i) => `photo${i}.jpg`)
      const tags = ['moth']
      const onProgress = vi.fn()

      // Mock bulk GET for fetching previous state
      const successObj = {}
      filenames.forEach(f => { successObj[f] = { tags: ['old_tag'] } })
      getBulkSidecarMetadata.mockResolvedValue({
        data: {
          success: successObj,
          failed: [],
          errors: {},
        }
      })

      api.post.mockResolvedValue({
        data: {
          success: [],
          failed: [],
          errors: {},
        }
      })

      const { result } = renderHook(() => useBulkOperations(), { wrapper })

      await result.current.bulkAddTags(filenames, tags, onProgress)

      // Should call progress 3 times
      expect(onProgress).toHaveBeenCalledTimes(3)

      // Check progress values
      expect(onProgress).toHaveBeenNthCalledWith(1, {
        currentBatch: 1,
        totalBatches: 3,
        processedCount: 0,
        totalCount: 250
      })

      expect(onProgress).toHaveBeenNthCalledWith(2, {
        currentBatch: 2,
        totalBatches: 3,
        processedCount: 100,
        totalCount: 250
      })

      expect(onProgress).toHaveBeenNthCalledWith(3, {
        currentBatch: 3,
        totalBatches: 3,
        processedCount: 200,
        totalCount: 250
      })
    })

    it('aggregates results from all batches', async () => {
      const filenames = Array.from({ length: 250 }, (_, i) => `photo${i}.jpg`)
      const tags = ['moth']

      // Mock bulk GET for fetching previous state
      const successObj = {}
      filenames.forEach(f => { successObj[f] = { tags: ['old_tag'] } })
      getBulkSidecarMetadata.mockResolvedValue({
        data: {
          success: successObj,
          failed: [],
          errors: {},
        }
      })

      // Mock different results per batch
      api.post
        .mockResolvedValueOnce({
          data: {
            success: filenames.slice(0, 95),
            failed: filenames.slice(95, 100),
            errors: {
              [filenames[95]]: 'Error 1',
              [filenames[96]]: 'Error 2',
              [filenames[97]]: 'Error 3',
              [filenames[98]]: 'Error 4',
              [filenames[99]]: 'Error 5',
            }
          }
        })
        .mockResolvedValueOnce({
          data: {
            success: filenames.slice(100, 198),
            failed: filenames.slice(198, 200),
            errors: {
              [filenames[198]]: 'Error 6',
              [filenames[199]]: 'Error 7',
            }
          }
        })
        .mockResolvedValueOnce({
          data: {
            success: filenames.slice(200, 250),
            failed: [],
            errors: {}
          }
        })

      const { result } = renderHook(() => useBulkOperations(), { wrapper })

      const response = await result.current.bulkAddTags(filenames, tags)

      // Check aggregated results
      expect(response.success.length).toBe(243) // 95 + 98 + 50
      expect(response.failed.length).toBe(7) // 5 + 2 + 0
      expect(Object.keys(response.errors).length).toBe(7)
    })
  })

  describe('State', () => {
    it('isProcessing is true during operation', async () => {
      const filenames = ['photo1.jpg']
      const tags = ['moth']

      // Mock delayed response
      api.post.mockImplementation(() => {
        return new Promise((resolve) => {
          setTimeout(() => {
            resolve({
              data: {
                success: filenames,
                failed: [],
                errors: {},
              }
            })
          }, 50)
        })
      })

      const { result } = renderHook(() => useBulkOperations(), { wrapper })

      expect(result.current.isProcessing).toBe(false)

      const promise = result.current.bulkAddTags(filenames, tags)

      // Should be true while processing
      await waitFor(() => {
        expect(result.current.isProcessing).toBe(true)
      })

      await promise

      // Should be false after completion
      await waitFor(() => {
        expect(result.current.isProcessing).toBe(false)
      })
    })

    it('isProcessing is false after completion', async () => {
      const filenames = ['photo1.jpg']
      const tags = ['moth']

      api.post.mockResolvedValue({
        data: {
          success: filenames,
          failed: [],
          errors: {},
        }
      })

      const { result } = renderHook(() => useBulkOperations(), { wrapper })

      await result.current.bulkAddTags(filenames, tags)

      await waitFor(() => {
        expect(result.current.isProcessing).toBe(false)
      })
    })

    it('isProcessing is false after error', async () => {
      const filenames = ['photo1.jpg']
      const tags = ['moth']

      api.post.mockRejectedValue(new Error('API error'))

      const { result } = renderHook(() => useBulkOperations(), { wrapper })

      await expect(result.current.bulkAddTags(filenames, tags)).rejects.toThrow()

      await waitFor(() => {
        expect(result.current.isProcessing).toBe(false)
      })
    })
  })

  describe('Undo Support', () => {
    it('returns previous state for tag operations', async () => {
      const filenames = ['photo1.jpg', 'photo2.jpg']
      const tags = ['new_tag']

      // Mock bulk fetching existing metadata for undo
      getBulkSidecarMetadata.mockResolvedValue({
        data: {
          success: {
            'photo1.jpg': { tags: ['old_tag1', 'old_tag2'] },
            'photo2.jpg': { tags: ['old_tag3'] },
          },
          failed: [],
          errors: {},
        }
      })

      api.post.mockResolvedValue({
        data: {
          success: filenames,
          failed: [],
          errors: {},
        }
      })

      const { result } = renderHook(() => useBulkOperations(), { wrapper })

      const response = await result.current.bulkAddTags(filenames, tags)

      // Should return previous tags for undo
      expect(response.previousState).toBeDefined()
      expect(response.previousState['photo1.jpg']).toEqual({
        tags: ['old_tag1', 'old_tag2']
      })
      expect(response.previousState['photo2.jpg']).toEqual({
        tags: ['old_tag3']
      })
    })

    it('returns previous state for species update', async () => {
      const filenames = ['photo1.jpg', 'photo2.jpg']
      const species = 'Actias luna'

      getBulkSidecarMetadata.mockResolvedValue({
        data: {
          success: {
            'photo1.jpg': { species: 'Unknown' },
            'photo2.jpg': { species: '' },
          },
          failed: [],
          errors: {},
        }
      })

      api.post.mockResolvedValue({
        data: {
          success: filenames,
          failed: [],
          errors: {},
        }
      })

      const { result } = renderHook(() => useBulkOperations(), { wrapper })

      const response = await result.current.bulkUpdateSpecies(filenames, species)

      expect(response.previousState).toBeDefined()
      expect(response.previousState['photo1.jpg']).toEqual({
        species: 'Unknown'
      })
      expect(response.previousState['photo2.jpg']).toEqual({
        species: ''
      })
    })

    it('handles partial failures when fetching previous state', async () => {
      const filenames = ['photo1.jpg', 'photo2.jpg']
      const tags = ['new_tag']

      // photo1 succeeds, photo2 failed in bulk response
      getBulkSidecarMetadata.mockResolvedValue({
        data: {
          success: {
            'photo1.jpg': { tags: ['old_tag'] },
          },
          failed: ['photo2.jpg'],
          errors: { 'photo2.jpg': 'Fetch failed' },
        }
      })

      api.post.mockResolvedValue({
        data: {
          success: filenames,
          failed: [],
          errors: {},
        }
      })

      const { result } = renderHook(() => useBulkOperations(), { wrapper })

      const response = await result.current.bulkAddTags(filenames, tags)

      // Should have previous state for photo1 only
      expect(response.previousState['photo1.jpg']).toBeDefined()
      expect(response.previousState['photo2.jpg']).toBeUndefined()
    })
  })

  describe('Cache Invalidation', () => {
    it('invalidates sidecar metadata queries after successful update', async () => {
      const filenames = ['photo1.jpg']
      const tags = ['moth']

      api.post.mockResolvedValue({
        data: {
          success: filenames,
          failed: [],
          errors: {},
        }
      })

      const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => useBulkOperations(), { wrapper })

      await result.current.bulkAddTags(filenames, tags)

      await waitFor(() => {
        expect(invalidateQueriesSpy).toHaveBeenCalledWith({
          queryKey: ['sidecarMetadata']
        })
      })
    })

    it('invalidates tags queries after successful tag operation', async () => {
      const filenames = ['photo1.jpg']
      const tags = ['moth']

      api.post.mockResolvedValue({
        data: {
          success: filenames,
          failed: [],
          errors: {},
        }
      })

      const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => useBulkOperations(), { wrapper })

      await result.current.bulkAddTags(filenames, tags)

      await waitFor(() => {
        expect(invalidateQueriesSpy).toHaveBeenCalledWith({
          queryKey: ['tags']
        })
      })
    })

    it('invalidates photos query after successful delete', async () => {
      const filenames = ['photo1.jpg']

      api.delete.mockResolvedValue({
        data: {
          success: filenames,
          failed: [],
          errors: {},
        }
      })

      const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => useBulkOperations(), { wrapper })

      await result.current.bulkDelete(filenames)

      await waitFor(() => {
        expect(invalidateQueriesSpy).toHaveBeenCalledWith({
          queryKey: ['photos']
        })
      })
    })
  })
})

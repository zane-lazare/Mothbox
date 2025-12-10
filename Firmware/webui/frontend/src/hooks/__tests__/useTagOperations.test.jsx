import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import useTagOperations from '../useTagOperations'
import * as api from '../../utils/api'

// Mock the API
vi.mock('../../utils/api', () => ({
  getPhotoSidecarMetadata: vi.fn(),
  updatePhotoSidecarMetadata: vi.fn(),
}))

// Mock react-hot-toast
vi.mock('react-hot-toast', () => {
  const toast = vi.fn()
  toast.success = vi.fn()
  toast.error = vi.fn()
  toast.dismiss = vi.fn()
  return { default: toast }
})

describe('useTagOperations', () => {
  let queryClient

  const createWrapper = () => {
    const Wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )
    return Wrapper
  }

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

  describe('addTag', () => {
    it('should add a tag and show success toast', async () => {
      const filename = 'photo.jpg'
      const mockData = { tags: ['existing'], species: '', notes: '' }

      api.getPhotoSidecarMetadata.mockResolvedValue({ data: mockData })
      api.updatePhotoSidecarMetadata.mockResolvedValue({
        data: { ...mockData, tags: ['existing', 'new'] },
      })

      const { result } = renderHook(() => useTagOperations(filename), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      // Add a tag
      result.current.addTag('new')

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalledWith('Added tag "new"', {
          duration: 3000,
        })
      })
    })

    it('should not add duplicate tag and show info toast', async () => {
      const filename = 'photo.jpg'
      const mockData = { tags: ['existing'], species: '', notes: '' }

      api.getPhotoSidecarMetadata.mockResolvedValue({ data: mockData })

      const { result } = renderHook(() => useTagOperations(filename), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      // Try to add existing tag
      result.current.addTag('existing')

      expect(toast).toHaveBeenCalledWith('Tag already exists', {
        duration: 3000,
        icon: 'ℹ️',
      })
    })

    it('should show error toast when mutation fails', async () => {
      const filename = 'photo.jpg'
      const mockData = { tags: ['existing'], species: '', notes: '' }

      api.getPhotoSidecarMetadata.mockResolvedValue({ data: mockData })
      api.updatePhotoSidecarMetadata.mockRejectedValue(new Error('Network error'))

      const { result } = renderHook(() => useTagOperations(filename), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      // Add a tag
      result.current.addTag('new')

      await waitFor(() => {
        expect(result.current.updateError).toBeTruthy()
      })

      // Error toast should be shown
      await waitFor(() => {
        expect(toast.error).toHaveBeenCalled()
      })
    })
  })

  describe('removeTag', () => {
    it('should remove a tag and show success toast', async () => {
      const filename = 'photo.jpg'
      const mockData = { tags: ['tag1', 'tag2'], species: '', notes: '' }

      api.getPhotoSidecarMetadata.mockResolvedValue({ data: mockData })
      api.updatePhotoSidecarMetadata.mockResolvedValue({
        data: { ...mockData, tags: ['tag1'] },
      })

      const { result } = renderHook(() => useTagOperations(filename), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      // Remove a tag
      result.current.removeTag('tag2')

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalledWith('Removed tag "tag2"', {
          duration: 3000,
        })
      })
    })

    it('should not remove non-existent tag and show info toast', async () => {
      const filename = 'photo.jpg'
      const mockData = { tags: ['existing'], species: '', notes: '' }

      api.getPhotoSidecarMetadata.mockResolvedValue({ data: mockData })

      const { result } = renderHook(() => useTagOperations(filename), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      // Try to remove non-existent tag
      result.current.removeTag('nonexistent')

      expect(toast).toHaveBeenCalledWith('Tag not found', {
        duration: 3000,
        icon: 'ℹ️',
      })
    })

    it('should show error toast when mutation fails', async () => {
      const filename = 'photo.jpg'
      const mockData = { tags: ['tag1', 'tag2'], species: '', notes: '' }

      api.getPhotoSidecarMetadata.mockResolvedValue({ data: mockData })
      api.updatePhotoSidecarMetadata.mockRejectedValue(new Error('Network error'))

      const { result } = renderHook(() => useTagOperations(filename), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      // Remove a tag
      result.current.removeTag('tag2')

      await waitFor(() => {
        expect(result.current.updateError).toBeTruthy()
      })

      // Error toast should be shown
      await waitFor(() => {
        expect(toast.error).toHaveBeenCalled()
      })
    })
  })

  describe('pass-through functions', () => {
    it('should pass through updateTags without toast', async () => {
      const filename = 'photo.jpg'
      const mockData = { tags: ['tag1'], species: '', notes: '' }

      api.getPhotoSidecarMetadata.mockResolvedValue({ data: mockData })
      api.updatePhotoSidecarMetadata.mockResolvedValue({
        data: { ...mockData, tags: ['tag1', 'tag2', 'tag3'] },
      })

      const { result } = renderHook(() => useTagOperations(filename), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      // Update tags directly
      result.current.updateTags(['tag1', 'tag2', 'tag3'])

      // Should NOT show toast
      expect(toast.success).not.toHaveBeenCalled()
    })

    it('should pass through updateSpecies without toast', async () => {
      const filename = 'photo.jpg'
      const mockData = { tags: [], species: '', notes: '' }

      api.getPhotoSidecarMetadata.mockResolvedValue({ data: mockData })
      api.updatePhotoSidecarMetadata.mockResolvedValue({
        data: { ...mockData, species: 'Luna Moth' },
      })

      const { result } = renderHook(() => useTagOperations(filename), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      // Update species
      result.current.updateSpecies('Luna Moth')

      // Should NOT show toast
      expect(toast.success).not.toHaveBeenCalled()
    })

    it('should pass through updateNotes without toast', async () => {
      const filename = 'photo.jpg'
      const mockData = { tags: [], species: '', notes: '' }

      api.getPhotoSidecarMetadata.mockResolvedValue({ data: mockData })
      api.updatePhotoSidecarMetadata.mockResolvedValue({
        data: { ...mockData, notes: 'Some notes' },
      })

      const { result } = renderHook(() => useTagOperations(filename), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      // Update notes
      result.current.updateNotes('Some notes')

      // Should NOT show toast
      expect(toast.success).not.toHaveBeenCalled()
    })
  })

  describe('query state', () => {
    it('should expose query loading state', async () => {
      const filename = 'photo.jpg'

      api.getPhotoSidecarMetadata.mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      )

      const { result } = renderHook(() => useTagOperations(filename), {
        wrapper: createWrapper(),
      })

      expect(result.current.isLoading).toBe(true)
    })

    it('should expose query data', async () => {
      const filename = 'photo.jpg'
      const mockData = { tags: ['tag1', 'tag2'], species: 'Luna Moth', notes: 'Test notes' }

      api.getPhotoSidecarMetadata.mockResolvedValue({ data: mockData })

      const { result } = renderHook(() => useTagOperations(filename), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      expect(result.current.data).toEqual(mockData)
    })

    it('should expose mutation updating state', async () => {
      const filename = 'photo.jpg'
      const mockData = { tags: ['tag1'], species: '', notes: '' }

      api.getPhotoSidecarMetadata.mockResolvedValue({ data: mockData })
      api.updatePhotoSidecarMetadata.mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      )

      const { result } = renderHook(() => useTagOperations(filename), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      result.current.addTag('tag2')

      await waitFor(() => {
        expect(result.current.isUpdating).toBe(true)
      })
    })
  })
})

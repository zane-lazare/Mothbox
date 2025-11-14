import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import * as api from '../../utils/api'
import { GALLERY_CONFIG } from '../../constants/config'
import {
  createMockPhotos,
  createTestQueryClient,
  setupIntersectionObserver,
  renderGallery,
} from './gallery-test-helpers.jsx'
import toast from 'react-hot-toast'

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(() => 'toast-id'),
    dismiss: vi.fn(),
  },
}))

// Mock the API module
vi.mock('../../utils/api', () => ({
  getPhotosPaginated: vi.fn(),
  getThumbnailUrl: vi.fn((path) => `/api/gallery/thumbnail/${path}`),
  getPhotoUrl: vi.fn((path) => `/api/gallery/photo/${path}`),
}))

describe('Gallery - Infinite Scroll - Error Handling', () => {
  let queryClient
  let observerMocks

  beforeEach(() => {
    queryClient = createTestQueryClient()
    observerMocks = setupIntersectionObserver()
    vi.clearAllMocks()
  })

  afterEach(() => {
    queryClient.clear()
  })

  // Helper to get the current observer callback
  const getObserverCallback = () => observerMocks.getObserverCallback()

  describe('Error Handling', () => {
    it('displays error message when initial load fails', async () => {
      api.getPhotosPaginated.mockRejectedValue(new Error('Network error'))

      renderGallery(queryClient)

      await waitFor(() => {
        expect(screen.getByText(/error/i)).toBeInTheDocument()
      })
    })

    it('handles pagination errors gracefully', async () => {
      // First page succeeds
      api.getPhotosPaginated.mockResolvedValueOnce({
        data: {
          photos: createMockPhotos(1, GALLERY_CONFIG.PAGE_SIZE),
          pagination: { limit: GALLERY_CONFIG.PAGE_SIZE, offset: 0, total: GALLERY_CONFIG.PAGE_SIZE * 2, has_next: true, has_previous: false },
        },
      })

      // Second page fails
      api.getPhotosPaginated.mockRejectedValueOnce(new Error('Network error'))

      renderGallery(queryClient)

      await waitFor(() => {
        expect(screen.getAllByRole('img')).toHaveLength(GALLERY_CONFIG.PAGE_SIZE)
      })

      // Trigger next page load
      const observerCallback = getObserverCallback()
      observerCallback([{ isIntersecting: true }])

      // Should show error but keep first page visible
      await waitFor(() => {
        const errorMessages = screen.getAllByText(/error.*loading.*photos/i)
        expect(errorMessages.length).toBeGreaterThan(0)
      })

      // First page photos should still be visible
      const photos = screen.getAllByAltText('photo_1.jpg')
      expect(photos.length).toBeGreaterThan(0)
      expect(photos[0]).toBeInTheDocument()
    })
  })

  describe('Retry Functionality', () => {
    it('displays retry button when initial load fails', async () => {
      api.getPhotosPaginated.mockRejectedValue(new Error('Network error'))

      renderGallery(queryClient)

      await waitFor(() => {
        expect(screen.getByText(/error/i)).toBeInTheDocument()
      })

      // Retry button should be present
      const retryButton = screen.getByRole('button', { name: /retry/i })
      expect(retryButton).toBeInTheDocument()
      expect(retryButton).toHaveTextContent('Retry')
    })

    it('retries initial load when retry button is clicked', async () => {
      const user = userEvent.setup()

      // First call fails
      api.getPhotosPaginated.mockRejectedValueOnce(new Error('Network error'))

      // Second call (after retry) succeeds
      api.getPhotosPaginated.mockResolvedValueOnce({
        data: {
          photos: createMockPhotos(1, GALLERY_CONFIG.PAGE_SIZE),
          pagination: { limit: GALLERY_CONFIG.PAGE_SIZE, offset: 0, total: GALLERY_CONFIG.PAGE_SIZE, has_next: false, has_previous: false },
        },
      })

      renderGallery(queryClient)

      // Wait for error to appear
      await waitFor(() => {
        expect(screen.getByText(/error/i)).toBeInTheDocument()
      })

      // Click retry button
      const retryButton = screen.getByRole('button', { name: /retry/i })
      await user.click(retryButton)

      // Should eventually show photos
      await waitFor(() => {
        expect(screen.getAllByRole('img')).toHaveLength(GALLERY_CONFIG.PAGE_SIZE)
      })

      // Error should be gone
      expect(screen.queryByText(/error/i)).not.toBeInTheDocument()
    })

  })

  describe('Toast Notifications', () => {
    beforeEach(() => {
      // Clear toast mock calls before each test
      toast.success.mockClear()
      toast.error.mockClear()
      toast.loading.mockClear()
      toast.dismiss.mockClear()
    })

    it('shows error toast when initial load fails', async () => {
      api.getPhotosPaginated.mockRejectedValue(new Error('Network error'))

      renderGallery(queryClient)

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(
          expect.stringContaining('Error'),
          expect.objectContaining({ duration: 6000 })
        )
      })
    })

    it('shows error toast when pagination fails', async () => {
      // First page succeeds
      api.getPhotosPaginated.mockResolvedValueOnce({
        data: {
          photos: createMockPhotos(1, GALLERY_CONFIG.PAGE_SIZE),
          pagination: { limit: GALLERY_CONFIG.PAGE_SIZE, offset: 0, total: GALLERY_CONFIG.PAGE_SIZE * 2, has_next: true, has_previous: false },
        },
      })

      // Second page fails
      api.getPhotosPaginated.mockRejectedValueOnce(new Error('Network error'))

      renderGallery(queryClient)

      await waitFor(() => {
        expect(screen.getAllByRole('img')).toHaveLength(GALLERY_CONFIG.PAGE_SIZE)
      })

      // Clear initial toast calls
      toast.error.mockClear()

      // Trigger next page load
      const observerCallback = getObserverCallback()
      observerCallback([{ isIntersecting: true }])

      // Should show pagination error toast
      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(
          expect.stringContaining('Error'),
          expect.objectContaining({ duration: 6000 })
        )
      })
    })

    it('shows both toast and inline error for pagination failures', async () => {
      // First page succeeds
      api.getPhotosPaginated.mockResolvedValueOnce({
        data: {
          photos: createMockPhotos(1, GALLERY_CONFIG.PAGE_SIZE),
          pagination: { limit: GALLERY_CONFIG.PAGE_SIZE, offset: 0, total: GALLERY_CONFIG.PAGE_SIZE * 2, has_next: true, has_previous: false },
        },
      })

      // Second page fails
      api.getPhotosPaginated.mockRejectedValueOnce(new Error('Network error'))

      renderGallery(queryClient)

      await waitFor(() => {
        expect(screen.getAllByRole('img')).toHaveLength(GALLERY_CONFIG.PAGE_SIZE)
      })

      // Trigger pagination failure
      const observerCallback = getObserverCallback()
      observerCallback([{ isIntersecting: true }])

      await waitFor(() => {
        // Toast should be shown
        expect(toast.error).toHaveBeenCalled()

        // Inline error should still be visible
        const errorMessages = screen.getAllByText(/error.*loading.*photos/i)
        expect(errorMessages.length).toBeGreaterThan(0)
      })
    })

    it('does not show duplicate toasts for the same error', async () => {
      api.getPhotosPaginated.mockRejectedValue(new Error('Network error'))

      renderGallery(queryClient)

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalled()
      })

      // Get initial call count
      const initialCallCount = toast.error.mock.calls.length

      // Wait a bit more to ensure no duplicate toasts
      await new Promise(resolve => setTimeout(resolve, 100))

      // Should not have been called again
      expect(toast.error).toHaveBeenCalledTimes(initialCallCount)
    })
  })
})

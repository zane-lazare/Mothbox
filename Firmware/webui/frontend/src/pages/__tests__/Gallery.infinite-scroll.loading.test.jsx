import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import * as api from '../../utils/api'
import { GALLERY_CONFIG } from '../../constants/config'
import {
  createMockPhotos,
  createTestQueryClient,
  setupIntersectionObserver,
  renderGallery,
} from './gallery-test-helpers.jsx'

// Mock the API module
vi.mock('../../utils/api', () => ({
  getPhotosPaginated: vi.fn(),
  getThumbnailUrl: vi.fn((path) => `/api/gallery/thumbnail/${path}`),
  getPhotoUrl: vi.fn((path) => `/api/gallery/photo/${path}`),
}))

describe('Gallery - Infinite Scroll - Loading & Pagination', () => {
  let queryClient
  let observerMocks
  let observerCallback

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

  describe('Initial Load', () => {
    it('renders loading state initially', () => {
      api.getPhotosPaginated.mockImplementation(() => new Promise(() => {}))
      renderGallery(queryClient)
      expect(screen.getByText(/Loading gallery.../i)).toBeInTheDocument()
    })

    it('loads and displays initial page of photos', async () => {
      const mockPhotos = createMockPhotos(1, GALLERY_CONFIG.PAGE_SIZE)
      api.getPhotosPaginated.mockResolvedValue({
        data: {
          photos: mockPhotos,
          pagination: {
            limit: GALLERY_CONFIG.PAGE_SIZE,
            offset: 0,
            total: 27,
            has_next: true,
            has_previous: false,
          },
        },
      })

      renderGallery(queryClient)

      await waitFor(() => {
        const images = screen.getAllByRole('img')
        expect(images).toHaveLength(GALLERY_CONFIG.PAGE_SIZE)
      })

      // Verify first photo is rendered
      expect(screen.getByAltText('photo_1.jpg')).toBeInTheDocument()
    })

    it('displays empty state when no photos exist', async () => {
      api.getPhotosPaginated.mockResolvedValue({
        data: {
          photos: [],
          pagination: {
            limit: GALLERY_CONFIG.PAGE_SIZE,
            offset: 0,
            total: 0,
            has_next: false,
            has_previous: false,
          },
        },
      })

      renderGallery(queryClient)

      await waitFor(() => {
        expect(screen.getByText(/No photos yet/i)).toBeInTheDocument()
      })
    })

    it('passes correct parameters to getPhotosPaginated for initial load', async () => {
      api.getPhotosPaginated.mockResolvedValue({
        data: {
          photos: createMockPhotos(1, GALLERY_CONFIG.PAGE_SIZE),
          pagination: {
            limit: GALLERY_CONFIG.PAGE_SIZE,
            offset: 0,
            total: GALLERY_CONFIG.PAGE_SIZE,
            has_next: false,
            has_previous: false,
          },
        },
      })

      renderGallery(queryClient)

      await waitFor(() => {
        expect(api.getPhotosPaginated).toHaveBeenCalledWith({
          limit: GALLERY_CONFIG.PAGE_SIZE,
          offset: 0,
          sort: 'date_desc',
        })
      })
    })
  })

  describe('Infinite Scroll Behavior', () => {
    it('loads next page when scrolling to bottom', async () => {
      // First page
      api.getPhotosPaginated.mockResolvedValueOnce({
        data: {
          photos: createMockPhotos(1, GALLERY_CONFIG.PAGE_SIZE),
          pagination: {
            limit: GALLERY_CONFIG.PAGE_SIZE,
            offset: 0,
            total: GALLERY_CONFIG.PAGE_SIZE * 2,
            has_next: true,
            has_previous: false,
          },
        },
      })

      // Second page
      api.getPhotosPaginated.mockResolvedValueOnce({
        data: {
          photos: createMockPhotos(GALLERY_CONFIG.PAGE_SIZE + 1, GALLERY_CONFIG.PAGE_SIZE),
          pagination: {
            limit: GALLERY_CONFIG.PAGE_SIZE,
            offset: GALLERY_CONFIG.PAGE_SIZE,
            total: GALLERY_CONFIG.PAGE_SIZE * 2,
            has_next: false,
            has_previous: true,
          },
        },
      })

      renderGallery(queryClient)

      // Wait for initial load
      await waitFor(() => {
        expect(screen.getAllByRole('img')).toHaveLength(GALLERY_CONFIG.PAGE_SIZE)
      })

      // Simulate scroll to bottom (trigger intersection)
      observerCallback = getObserverCallback()
      observerCallback([{ isIntersecting: true }])

      // Wait for second page to load
      await waitFor(() => {
        const images = screen.getAllByRole('img')
        expect(images).toHaveLength(GALLERY_CONFIG.PAGE_SIZE * 2)
      })

      // Verify both pages are rendered
      expect(screen.getByAltText('photo_1.jpg')).toBeInTheDocument()
      expect(screen.getByAltText('photo_10.jpg')).toBeInTheDocument()
    })

    it('displays skeleton cards while loading next page', async () => {
      // First page loads
      api.getPhotosPaginated.mockResolvedValueOnce({
        data: {
          photos: createMockPhotos(1, GALLERY_CONFIG.PAGE_SIZE),
          pagination: {
            limit: GALLERY_CONFIG.PAGE_SIZE,
            offset: 0,
            total: GALLERY_CONFIG.PAGE_SIZE * 2,
            has_next: true,
            has_previous: false,
          },
        },
      })

      // Second page takes time to load
      api.getPhotosPaginated.mockImplementationOnce(() => new Promise(resolve => {
        setTimeout(() => {
          resolve({
            data: {
              photos: createMockPhotos(GALLERY_CONFIG.PAGE_SIZE + 1, GALLERY_CONFIG.PAGE_SIZE),
              pagination: {
                limit: GALLERY_CONFIG.PAGE_SIZE,
                offset: GALLERY_CONFIG.PAGE_SIZE,
                total: GALLERY_CONFIG.PAGE_SIZE * 2,
                has_next: false,
                has_previous: true,
              },
            },
          })
        }, 100)
      }))

      renderGallery(queryClient)

      // Wait for initial load
      await waitFor(() => {
        expect(screen.getAllByRole('img')).toHaveLength(GALLERY_CONFIG.PAGE_SIZE)
      })

      // Trigger loading next page
      observerCallback = getObserverCallback()
      observerCallback([{ isIntersecting: true }])

      // Should show skeleton cards
      await waitFor(() => {
        expect(screen.getAllByTestId('photo-skeleton')).toHaveLength(GALLERY_CONFIG.SKELETON_COUNT)
      })
    })

    it('does not load more photos when has_next is false', async () => {
      api.getPhotosPaginated.mockResolvedValue({
        data: {
          photos: createMockPhotos(1, GALLERY_CONFIG.PAGE_SIZE),
          pagination: {
            limit: GALLERY_CONFIG.PAGE_SIZE,
            offset: 0,
            total: GALLERY_CONFIG.PAGE_SIZE,
            has_next: false,
            has_previous: false,
          },
        },
      })

      renderGallery(queryClient)

      await waitFor(() => {
        expect(screen.getAllByRole('img')).toHaveLength(GALLERY_CONFIG.PAGE_SIZE)
      })

      // Clear the mock calls from initial load
      api.getPhotosPaginated.mockClear()

      // Try to trigger loading more
      observerCallback = getObserverCallback()
      observerCallback([{ isIntersecting: true }])

      // Should not make another API call
      await new Promise(resolve => setTimeout(resolve, 100))
      expect(api.getPhotosPaginated).not.toHaveBeenCalled()
    })

    it('loads multiple pages sequentially', async () => {
      const totalPhotos = GALLERY_CONFIG.PAGE_SIZE * 3

      // Page 1
      api.getPhotosPaginated.mockResolvedValueOnce({
        data: {
          photos: createMockPhotos(1, GALLERY_CONFIG.PAGE_SIZE),
          pagination: { limit: GALLERY_CONFIG.PAGE_SIZE, offset: 0, total: totalPhotos, has_next: true, has_previous: false },
        },
      })

      // Page 2
      api.getPhotosPaginated.mockResolvedValueOnce({
        data: {
          photos: createMockPhotos(GALLERY_CONFIG.PAGE_SIZE + 1, GALLERY_CONFIG.PAGE_SIZE),
          pagination: { limit: GALLERY_CONFIG.PAGE_SIZE, offset: GALLERY_CONFIG.PAGE_SIZE, total: totalPhotos, has_next: true, has_previous: true },
        },
      })

      // Page 3
      api.getPhotosPaginated.mockResolvedValueOnce({
        data: {
          photos: createMockPhotos(GALLERY_CONFIG.PAGE_SIZE * 2 + 1, GALLERY_CONFIG.PAGE_SIZE),
          pagination: { limit: GALLERY_CONFIG.PAGE_SIZE, offset: GALLERY_CONFIG.PAGE_SIZE * 2, total: totalPhotos, has_next: false, has_previous: true },
        },
      })

      renderGallery(queryClient)

      // Load page 1
      await waitFor(() => {
        expect(screen.getAllByRole('img')).toHaveLength(GALLERY_CONFIG.PAGE_SIZE)
      })

      // Load page 2
      observerCallback = getObserverCallback()
      observerCallback([{ isIntersecting: true }])
      await waitFor(() => {
        expect(screen.getAllByRole('img')).toHaveLength(GALLERY_CONFIG.PAGE_SIZE * 2)
      })

      // Load page 3
      observerCallback([{ isIntersecting: true }])
      await waitFor(() => {
        expect(screen.getAllByRole('img')).toHaveLength(GALLERY_CONFIG.PAGE_SIZE * 3)
      })

      expect(screen.getByAltText('photo_1.jpg')).toBeInTheDocument()
      expect(screen.getByAltText(`photo_${GALLERY_CONFIG.PAGE_SIZE + 1}.jpg`)).toBeInTheDocument()
      expect(screen.getByAltText(`photo_${GALLERY_CONFIG.PAGE_SIZE * 2 + 1}.jpg`)).toBeInTheDocument()
    })
  })

  describe('Intersection Observer Integration', () => {
    it('sets up intersection observer on mount', () => {
      api.getPhotosPaginated.mockResolvedValue({
        data: {
          photos: createMockPhotos(1, GALLERY_CONFIG.PAGE_SIZE),
          pagination: { limit: GALLERY_CONFIG.PAGE_SIZE, offset: 0, total: GALLERY_CONFIG.PAGE_SIZE, has_next: true, has_previous: false },
        },
      })

      renderGallery(queryClient)

      expect(observerMocks.IntersectionObserverMock).toHaveBeenCalled()
    })

    it('cleans up intersection observer on unmount', async () => {
      api.getPhotosPaginated.mockResolvedValue({
        data: {
          photos: createMockPhotos(1, GALLERY_CONFIG.PAGE_SIZE),
          pagination: { limit: GALLERY_CONFIG.PAGE_SIZE, offset: 0, total: GALLERY_CONFIG.PAGE_SIZE, has_next: true, has_previous: false },
        },
      })

      const { unmount } = renderGallery(queryClient)

      await waitFor(() => {
        expect(screen.getAllByRole('img')).toHaveLength(GALLERY_CONFIG.PAGE_SIZE)
      })

      unmount()

      expect(observerMocks.disconnectMock).toHaveBeenCalled()
    })
  })
})

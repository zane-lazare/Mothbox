import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Gallery from '../Gallery'
import * as api from '../../utils/api'

// Mock the API module
vi.mock('../../utils/api', () => ({
  getPhotosPaginated: vi.fn(),
  getThumbnailUrl: vi.fn((path) => `/api/gallery/thumbnail/${path}`),
  getPhotoUrl: vi.fn((path) => `/api/gallery/photo/${path}`),
}))

describe('Gallery - Infinite Scroll', () => {
  let queryClient
  let observeMock
  let unobserveMock
  let disconnectMock
  let observerCallback
  let IntersectionObserverMock

  // Helper to create mock photo data
  const createMockPhotos = (start, count) => {
    return Array.from({ length: count }, (_, i) => ({
      path: `photo_${start + i}.jpg`,
      filename: `photo_${start + i}.jpg`,
      date: new Date(2023, 10, start + i).toISOString(),
      size: 1024 * 1024 * (start + i),
    }))
  }

  beforeEach(() => {
    // Create QueryClient for testing
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    })

    // Create IntersectionObserver mock
    observeMock = vi.fn()
    unobserveMock = vi.fn()
    disconnectMock = vi.fn()

    IntersectionObserverMock = vi.fn((callback, options) => {
      observerCallback = callback
      return {
        observe: observeMock,
        unobserve: unobserveMock,
        disconnect: disconnectMock,
      }
    })

    global.IntersectionObserver = IntersectionObserverMock

    vi.clearAllMocks()
  })

  afterEach(() => {
    queryClient.clear()
  })

  const renderComponent = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <Gallery />
      </QueryClientProvider>
    )
  }

  describe('Initial Load', () => {
    it('renders loading state initially', () => {
      api.getPhotosPaginated.mockImplementation(() => new Promise(() => {}))
      renderComponent()
      expect(screen.getByText(/Loading gallery.../i)).toBeInTheDocument()
    })

    it('loads and displays initial 9 photos', async () => {
      const mockPhotos = createMockPhotos(1, 9)
      api.getPhotosPaginated.mockResolvedValue({
        data: {
          photos: mockPhotos,
          pagination: {
            limit: 9,
            offset: 0,
            total: 27,
            has_next: true,
            has_previous: false,
          },
        },
      })

      renderComponent()

      await waitFor(() => {
        const images = screen.getAllByRole('img')
        expect(images).toHaveLength(9)
      })

      // Verify first photo is rendered
      expect(screen.getByAltText('photo_1.jpg')).toBeInTheDocument()
    })

    it('displays empty state when no photos exist', async () => {
      api.getPhotosPaginated.mockResolvedValue({
        data: {
          photos: [],
          pagination: {
            limit: 9,
            offset: 0,
            total: 0,
            has_next: false,
            has_previous: false,
          },
        },
      })

      renderComponent()

      await waitFor(() => {
        expect(screen.getByText(/No photos yet/i)).toBeInTheDocument()
      })
    })

    it('passes correct parameters to getPhotosPaginated for initial load', async () => {
      api.getPhotosPaginated.mockResolvedValue({
        data: {
          photos: createMockPhotos(1, 9),
          pagination: {
            limit: 9,
            offset: 0,
            total: 9,
            has_next: false,
            has_previous: false,
          },
        },
      })

      renderComponent()

      await waitFor(() => {
        expect(api.getPhotosPaginated).toHaveBeenCalledWith({
          limit: 9,
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
          photos: createMockPhotos(1, 9),
          pagination: {
            limit: 9,
            offset: 0,
            total: 18,
            has_next: true,
            has_previous: false,
          },
        },
      })

      // Second page
      api.getPhotosPaginated.mockResolvedValueOnce({
        data: {
          photos: createMockPhotos(10, 9),
          pagination: {
            limit: 9,
            offset: 9,
            total: 18,
            has_next: false,
            has_previous: true,
          },
        },
      })

      renderComponent()

      // Wait for initial load
      await waitFor(() => {
        expect(screen.getAllByRole('img')).toHaveLength(9)
      })

      // Simulate scroll to bottom (trigger intersection)
      observerCallback([{ isIntersecting: true }])

      // Wait for second page to load
      await waitFor(() => {
        const images = screen.getAllByRole('img')
        expect(images).toHaveLength(18)
      })

      // Verify both pages are rendered
      expect(screen.getByAltText('photo_1.jpg')).toBeInTheDocument()
      expect(screen.getByAltText('photo_10.jpg')).toBeInTheDocument()
    })

    it('displays skeleton cards while loading next page', async () => {
      // First page loads
      api.getPhotosPaginated.mockResolvedValueOnce({
        data: {
          photos: createMockPhotos(1, 9),
          pagination: {
            limit: 9,
            offset: 0,
            total: 18,
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
              photos: createMockPhotos(10, 9),
              pagination: {
                limit: 9,
                offset: 9,
                total: 18,
                has_next: false,
                has_previous: true,
              },
            },
          })
        }, 100)
      }))

      renderComponent()

      // Wait for initial load
      await waitFor(() => {
        expect(screen.getAllByRole('img')).toHaveLength(9)
      })

      // Trigger loading next page
      observerCallback([{ isIntersecting: true }])

      // Should show skeleton cards
      await waitFor(() => {
        expect(screen.getAllByTestId('photo-skeleton')).toHaveLength(9)
      })
    })

    it('does not load more photos when has_next is false', async () => {
      api.getPhotosPaginated.mockResolvedValue({
        data: {
          photos: createMockPhotos(1, 9),
          pagination: {
            limit: 9,
            offset: 0,
            total: 9,
            has_next: false,
            has_previous: false,
          },
        },
      })

      renderComponent()

      await waitFor(() => {
        expect(screen.getAllByRole('img')).toHaveLength(9)
      })

      // Clear the mock calls from initial load
      api.getPhotosPaginated.mockClear()

      // Try to trigger loading more
      observerCallback([{ isIntersecting: true }])

      // Should not make another API call
      await new Promise(resolve => setTimeout(resolve, 100))
      expect(api.getPhotosPaginated).not.toHaveBeenCalled()
    })

    it('loads multiple pages sequentially', async () => {
      // Page 1
      api.getPhotosPaginated.mockResolvedValueOnce({
        data: {
          photos: createMockPhotos(1, 9),
          pagination: { limit: 9, offset: 0, total: 27, has_next: true, has_previous: false },
        },
      })

      // Page 2
      api.getPhotosPaginated.mockResolvedValueOnce({
        data: {
          photos: createMockPhotos(10, 9),
          pagination: { limit: 9, offset: 9, total: 27, has_next: true, has_previous: true },
        },
      })

      // Page 3
      api.getPhotosPaginated.mockResolvedValueOnce({
        data: {
          photos: createMockPhotos(19, 9),
          pagination: { limit: 9, offset: 18, total: 27, has_next: false, has_previous: true },
        },
      })

      renderComponent()

      // Load page 1
      await waitFor(() => {
        expect(screen.getAllByRole('img')).toHaveLength(9)
      })

      // Load page 2
      observerCallback([{ isIntersecting: true }])
      await waitFor(() => {
        expect(screen.getAllByRole('img')).toHaveLength(18)
      })

      // Load page 3
      observerCallback([{ isIntersecting: true }])
      await waitFor(() => {
        expect(screen.getAllByRole('img')).toHaveLength(27)
      })

      expect(screen.getByAltText('photo_1.jpg')).toBeInTheDocument()
      expect(screen.getByAltText('photo_10.jpg')).toBeInTheDocument()
      expect(screen.getByAltText('photo_19.jpg')).toBeInTheDocument()
    })
  })

  describe('Lightbox Integration', () => {
    it('opens lightbox when photo is clicked', async () => {
      api.getPhotosPaginated.mockResolvedValue({
        data: {
          photos: createMockPhotos(1, 9),
          pagination: {
            limit: 9,
            offset: 0,
            total: 9,
            has_next: false,
            has_previous: false,
          },
        },
      })

      const user = userEvent.setup()
      renderComponent()

      await waitFor(() => {
        expect(screen.getAllByRole('img')).toHaveLength(9)
      })

      // Click first photo (thumbnail)
      const photos = screen.getAllByAltText('photo_1.jpg')
      await user.click(photos[0])

      // Lightbox should open with full-size image
      await waitFor(() => {
        const lightboxImage = screen.getAllByAltText('photo_1.jpg')[1]
        expect(lightboxImage).toBeInTheDocument()
        expect(lightboxImage).toHaveAttribute('src', '/api/gallery/photo/photo_1.jpg')
      })
    })

    it('closes lightbox when clicking background', async () => {
      api.getPhotosPaginated.mockResolvedValue({
        data: {
          photos: createMockPhotos(1, 9),
          pagination: { limit: 9, offset: 0, total: 9, has_next: false, has_previous: false },
        },
      })

      const user = userEvent.setup()
      renderComponent()

      await waitFor(() => {
        expect(screen.getAllByRole('img')).toHaveLength(9)
      })

      // Open lightbox
      const photos = screen.getAllByAltText('photo_1.jpg')
      await user.click(photos[0])

      await waitFor(() => {
        const lightboxImages = screen.getAllByAltText('photo_1.jpg')
        expect(lightboxImages).toHaveLength(2) // thumbnail + lightbox
      })

      // Click lightbox background
      const lightboxImages = screen.getAllByAltText('photo_1.jpg')
      const lightbox = lightboxImages[1].closest('[class*="fixed"]')
      await user.click(lightbox)

      // Lightbox should close
      await waitFor(() => {
        const remainingImages = screen.getAllByAltText('photo_1.jpg')
        expect(remainingImages).toHaveLength(1) // only thumbnail remains
      })
    })

    it('displays photo metadata in lightbox', async () => {
      api.getPhotosPaginated.mockResolvedValue({
        data: {
          photos: [{
            path: 'test_photo.jpg',
            filename: 'test_photo.jpg',
            date: '2023-11-15T14:30:00Z',
            size: 2 * 1024 * 1024, // 2 MB
          }],
          pagination: { limit: 9, offset: 0, total: 1, has_next: false, has_previous: false },
        },
      })

      const user = userEvent.setup()
      renderComponent()

      await waitFor(() => {
        expect(screen.getByAltText('test_photo.jpg')).toBeInTheDocument()
      })

      // Click photo to open lightbox
      await user.click(screen.getByAltText('test_photo.jpg'))

      // Check metadata is displayed
      await waitFor(() => {
        expect(screen.getByText('test_photo.jpg')).toBeInTheDocument()
        expect(screen.getByText('2.00 MB')).toBeInTheDocument()
      })
    })
  })

  describe('Error Handling', () => {
    it('displays error message when initial load fails', async () => {
      api.getPhotosPaginated.mockRejectedValue(new Error('Network error'))

      renderComponent()

      await waitFor(() => {
        expect(screen.getByText(/error/i)).toBeInTheDocument()
      })
    })

    it('handles pagination errors gracefully', async () => {
      // First page succeeds
      api.getPhotosPaginated.mockResolvedValueOnce({
        data: {
          photos: createMockPhotos(1, 9),
          pagination: { limit: 9, offset: 0, total: 18, has_next: true, has_previous: false },
        },
      })

      // Second page fails
      api.getPhotosPaginated.mockRejectedValueOnce(new Error('Network error'))

      renderComponent()

      await waitFor(() => {
        expect(screen.getAllByRole('img')).toHaveLength(9)
      })

      // Trigger next page load
      observerCallback([{ isIntersecting: true }])

      // Should show error but keep first page visible
      await waitFor(() => {
        expect(screen.getByText(/error/i)).toBeInTheDocument()
      })

      // First page photos should still be visible
      const photos = screen.getAllByAltText('photo_1.jpg')
      expect(photos.length).toBeGreaterThan(0)
      expect(photos[0]).toBeInTheDocument()
    })
  })

  describe('Photo Grid Layout', () => {
    it('renders photos in correct grid format', async () => {
      api.getPhotosPaginated.mockResolvedValue({
        data: {
          photos: createMockPhotos(1, 9),
          pagination: { limit: 9, offset: 0, total: 9, has_next: false, has_previous: false },
        },
      })

      renderComponent()

      await waitFor(() => {
        expect(screen.getAllByRole('img')).toHaveLength(9)
      })

      // Check grid has grid class
      const gridElement = screen.getAllByRole('img')[0].closest('[class*="grid"]')
      expect(gridElement).toHaveClass('grid')
    })

    it('uses thumbnail URLs for grid images', async () => {
      api.getPhotosPaginated.mockResolvedValue({
        data: {
          photos: [createMockPhotos(1, 1)[0]],
          pagination: { limit: 9, offset: 0, total: 1, has_next: false, has_previous: false },
        },
      })

      renderComponent()

      await waitFor(() => {
        const img = screen.getByAltText('photo_1.jpg')
        expect(img).toHaveAttribute('src', '/api/gallery/thumbnail/photo_1.jpg')
      })
    })
  })

  describe('Intersection Observer Integration', () => {
    it('sets up intersection observer on mount', () => {
      api.getPhotosPaginated.mockResolvedValue({
        data: {
          photos: createMockPhotos(1, 9),
          pagination: { limit: 9, offset: 0, total: 9, has_next: true, has_previous: false },
        },
      })

      renderComponent()

      expect(IntersectionObserverMock).toHaveBeenCalled()
    })

    it('cleans up intersection observer on unmount', async () => {
      api.getPhotosPaginated.mockResolvedValue({
        data: {
          photos: createMockPhotos(1, 9),
          pagination: { limit: 9, offset: 0, total: 9, has_next: true, has_previous: false },
        },
      })

      const { unmount } = renderComponent()

      await waitFor(() => {
        expect(screen.getAllByRole('img')).toHaveLength(9)
      })

      unmount()

      expect(disconnectMock).toHaveBeenCalled()
    })
  })
})

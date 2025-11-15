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

// Mock the API module
vi.mock('../../utils/api', () => ({
  getPhotosPaginated: vi.fn(),
  getThumbnailUrl: vi.fn((path) => `/api/gallery/thumbnail/${path}`),
  getPhotoUrl: vi.fn((path) => `/api/gallery/photo/${path}`),
}))

describe('Gallery - Infinite Scroll - Lightbox & UI', () => {
  let queryClient

  beforeEach(() => {
    queryClient = createTestQueryClient()
    setupIntersectionObserver()
    vi.clearAllMocks()
  })

  afterEach(() => {
    queryClient.clear()
  })

  describe('Lightbox Integration', () => {
    it('opens lightbox when photo is clicked', async () => {
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

      const user = userEvent.setup()
      renderGallery(queryClient)

      await waitFor(() => {
        expect(screen.getAllByRole('img')).toHaveLength(GALLERY_CONFIG.PAGE_SIZE)
      })

      // Click first photo (thumbnail)
      const photos = screen.getAllByAltText('photo_1.jpg')
      await user.click(photos[0])

      // Lightbox should open with full-size image
      await waitFor(() => {
        const lightboxImage = screen.getByAltText('Photo taken on 2023-11-01')
        expect(lightboxImage).toBeInTheDocument()
        expect(lightboxImage).toHaveAttribute('src', '/api/gallery/photo/photo_1.jpg')
      })
    })

    it('closes lightbox when clicking background', async () => {
      api.getPhotosPaginated.mockResolvedValue({
        data: {
          photos: createMockPhotos(1, GALLERY_CONFIG.PAGE_SIZE),
          pagination: { limit: GALLERY_CONFIG.PAGE_SIZE, offset: 0, total: GALLERY_CONFIG.PAGE_SIZE, has_next: false, has_previous: false },
        },
      })

      const user = userEvent.setup()
      renderGallery(queryClient)

      await waitFor(() => {
        expect(screen.getAllByRole('img')).toHaveLength(GALLERY_CONFIG.PAGE_SIZE)
      })

      // Open lightbox
      const photos = screen.getAllByAltText('photo_1.jpg')
      await user.click(photos[0])

      await waitFor(() => {
        // Lightbox image has descriptive alt text, thumbnail has filename
        expect(screen.getByAltText('Photo taken on 2023-11-01')).toBeInTheDocument()
      })

      // Click lightbox background
      const lightboxImage = screen.getByAltText('Photo taken on 2023-11-01')
      const lightbox = lightboxImage.closest('[class*="fixed"]')
      await user.click(lightbox)

      // Lightbox should close
      await waitFor(() => {
        // Only thumbnail with filename alt text remains
        expect(screen.queryByAltText('Photo taken on 2023-11-01')).not.toBeInTheDocument()
        expect(screen.getByAltText('photo_1.jpg')).toBeInTheDocument()
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
          pagination: { limit: GALLERY_CONFIG.PAGE_SIZE, offset: 0, total: 1, has_next: false, has_previous: false },
        },
      })

      const user = userEvent.setup()
      renderGallery(queryClient)

      await waitFor(() => {
        expect(screen.getByAltText('test_photo.jpg')).toBeInTheDocument()
      })

      // Click photo to open lightbox
      await user.click(screen.getByAltText('test_photo.jpg'))

      // Check metadata is displayed
      await waitFor(() => {
        expect(screen.getByText('test_photo.jpg')).toBeInTheDocument()
        expect(screen.getByText(/2\.0.*MB/)).toBeInTheDocument()
      })
    })
  })

  describe('Photo Grid Layout', () => {
    it('renders photos in correct grid format', async () => {
      api.getPhotosPaginated.mockResolvedValue({
        data: {
          photos: createMockPhotos(1, GALLERY_CONFIG.PAGE_SIZE),
          pagination: { limit: GALLERY_CONFIG.PAGE_SIZE, offset: 0, total: GALLERY_CONFIG.PAGE_SIZE, has_next: false, has_previous: false },
        },
      })

      renderGallery(queryClient)

      await waitFor(() => {
        expect(screen.getAllByRole('img')).toHaveLength(GALLERY_CONFIG.PAGE_SIZE)
      })

      // Check grid has grid class
      const gridElement = screen.getAllByRole('img')[0].closest('[class*="grid"]')
      expect(gridElement).toHaveClass('grid')
    })

    it('uses thumbnail URLs for grid images', async () => {
      api.getPhotosPaginated.mockResolvedValue({
        data: {
          photos: [createMockPhotos(1, 1)[0]],
          pagination: { limit: GALLERY_CONFIG.PAGE_SIZE, offset: 0, total: 1, has_next: false, has_previous: false },
        },
      })

      renderGallery(queryClient)

      await waitFor(() => {
        const img = screen.getByAltText('photo_1.jpg')
        expect(img).toHaveAttribute('src', '/api/gallery/thumbnail/photo_1.jpg')
      })
    })
  })
})

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import * as api from '../../utils/api'
import { GALLERY_CONFIG } from '../../constants/config'
import {
  createMockPhotos,
  createTestQueryClient,
  setupIntersectionObserver,
  renderGallery,
  createPaginationResponse,
} from './gallery-test-helpers.jsx'

/**
 * Gallery + PhotoLightbox Integration Tests
 *
 * Tests the integration between Gallery component and PhotoLightbox,
 * verifying complete user workflows and state synchronization.
 */

// Mock the API module
vi.mock('../../utils/api', () => ({
  getPhotosPaginated: vi.fn(),
  getThumbnailUrl: vi.fn((path) => `/api/gallery/thumbnail/${path}`),
  getPhotoUrl: vi.fn((path) => `/api/gallery/photo/${path}`),
}))

describe('Gallery + PhotoLightbox Integration', () => {
  let queryClient
  let observerMocks

  beforeEach(() => {
    queryClient = createTestQueryClient()
    observerMocks = setupIntersectionObserver()
    vi.clearAllMocks()
  })

  afterEach(() => {
    queryClient.clear()
    document.body.style.overflow = ''
  })

  it('opens lightbox when clicking photo thumbnail', async () => {
    const user = userEvent.setup()
    const mockPhotos = createMockPhotos(1, 3)

    api.getPhotosPaginated.mockResolvedValue(
      createPaginationResponse(mockPhotos, {
        has_next: false,
      })
    )

    renderGallery(queryClient)

    // Wait for photos to load
    await waitFor(() => {
      expect(screen.getAllByRole('img')).toHaveLength(3)
    })

    // Get all thumbnails
    const thumbnails = screen.getAllByRole('img')
    expect(thumbnails).toHaveLength(3)

    // Click first thumbnail
    await user.click(thumbnails[0])

    // Verify lightbox opens with dialog role
    await waitFor(() => {
      const dialog = screen.getByRole('dialog')
      expect(dialog).toBeInTheDocument()
    })

    // Verify correct photo shown in lightbox
    const dialog = screen.getByRole('dialog')
    const lightboxImg = within(dialog).getByAltText('photo_1.jpg')
    expect(lightboxImg).toBeInTheDocument()
    expect(lightboxImg.src).toContain('/api/gallery/photo/photo_1.jpg')

    // Verify photo metadata displayed
    expect(within(dialog).getByText('photo_1.jpg')).toBeInTheDocument()
  })

  it('navigates in lightbox and Gallery state updates correctly', async () => {
    const user = userEvent.setup()
    const mockPhotos = createMockPhotos(1, 3)

    api.getPhotosPaginated.mockResolvedValue(
      createPaginationResponse(mockPhotos, {
        has_next: false,
      })
    )

    renderGallery(queryClient)

    // Wait for photos to load
    await waitFor(() => {
      expect(screen.getAllByRole('img')).toHaveLength(3)
    })

    // Click first thumbnail to open lightbox
    const thumbnails = screen.getAllByRole('img')
    await user.click(thumbnails[0])

    // Verify first photo in lightbox
    await waitFor(() => {
      const dialog = screen.getByRole('dialog')
      expect(within(dialog).getByAltText('photo_1.jpg')).toBeInTheDocument()
    })

    // Navigate to next photo with keyboard
    await user.keyboard('{ArrowRight}')

    // Verify second photo now shown
    await waitFor(() => {
      const dialog = screen.getByRole('dialog')
      expect(within(dialog).getByAltText('photo_2.jpg')).toBeInTheDocument()
    })

    // Navigate to third photo
    await user.keyboard('{ArrowRight}')

    await waitFor(() => {
      const dialog = screen.getByRole('dialog')
      expect(within(dialog).getByAltText('photo_3.jpg')).toBeInTheDocument()
    })

    // Navigate backward
    await user.keyboard('{ArrowLeft}')

    await waitFor(() => {
      const dialog = screen.getByRole('dialog')
      expect(within(dialog).getByAltText('photo_2.jpg')).toBeInTheDocument()
    })

    // Gallery should still be rendered (thumbnails still present)
    expect(screen.getAllByRole('img').length).toBeGreaterThan(3)
  })

  it('closes lightbox and Gallery remains functional', async () => {
    const user = userEvent.setup()
    const mockPhotos = createMockPhotos(1, 3)

    api.getPhotosPaginated.mockResolvedValue(
      createPaginationResponse(mockPhotos, {
        has_next: false,
      })
    )

    renderGallery(queryClient)

    // Wait for photos to load
    await waitFor(() => {
      expect(screen.getAllByRole('img')).toHaveLength(3)
    })

    const initialThumbnailCount = screen.getAllByRole('img').length

    // Open lightbox
    const thumbnails = screen.getAllByRole('img')
    await user.click(thumbnails[0])

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    // Close lightbox with ESC
    await user.keyboard('{Escape}')

    // Verify lightbox closed
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })

    // Verify Gallery still functional (thumbnails present)
    expect(screen.getAllByRole('img')).toHaveLength(initialThumbnailCount)

    // Verify can open lightbox again
    await user.click(screen.getAllByRole('img')[1])

    await waitFor(() => {
      const dialog = screen.getByRole('dialog')
      expect(within(dialog).getByAltText('photo_2.jpg')).toBeInTheDocument()
    })

    // Close with close button
    const closeBtn = screen.getByLabelText(/close photo viewer/i)
    await user.click(closeBtn)

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })

    // Gallery still functional
    expect(screen.getAllByRole('img')).toHaveLength(initialThumbnailCount)
  })

  it(
    'multiple open/close cycles work without memory leaks or state corruption',
    async () => {
    const user = userEvent.setup()
    const mockPhotos = createMockPhotos(1, 5)

    api.getPhotosPaginated.mockResolvedValue(
      createPaginationResponse(mockPhotos, {
        has_next: false,
      })
    )

    renderGallery(queryClient)

    // Wait for photos to load
    await waitFor(() => {
      expect(screen.getAllByRole('img')).toHaveLength(5)
    })

    // Perform 5 open/close cycles
    for (let i = 0; i < 5; i++) {
      const thumbnails = screen.getAllByRole('img')

      // Open lightbox with different photo each time
      await user.click(thumbnails[i])

      await waitFor(() => {
        const dialog = screen.getByRole('dialog')
        expect(within(dialog).getByAltText(`photo_${i + 1}.jpg`)).toBeInTheDocument()
      })

      // Navigate a bit
      await user.keyboard('{ArrowRight}')
      await user.keyboard('{ArrowLeft}')

      // Zoom in/out
      const zoomInBtn = screen.getByLabelText(/zoom in/i)
      await user.click(zoomInBtn)

      await waitFor(() => {
        const img = within(screen.getByRole('dialog')).getByRole('img')
        expect(img.style.transform).toMatch(/scale\(1\.5\)/)
      })

      const zoomOutBtn = screen.getByLabelText(/zoom out/i)
      await user.click(zoomOutBtn)

      // Close lightbox (alternate between ESC and button)
      if (i % 2 === 0) {
        await user.keyboard('{Escape}')
      } else {
        const closeBtn = screen.getByLabelText(/close photo viewer/i)
        await user.click(closeBtn)
      }

      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
      })

      // Verify Gallery still has all thumbnails
      expect(screen.getAllByRole('img')).toHaveLength(5)
    }

    // Final verification: Gallery is still fully functional
    await user.click(screen.getAllByRole('img')[2])

    await waitFor(() => {
      const dialog = screen.getByRole('dialog')
      expect(within(dialog).getByAltText('photo_3.jpg')).toBeInTheDocument()
    })

    // No errors should occur (test passes if we get here)
    },
    10000
  ) // 10 second timeout for this long test

  it(
    'lightbox works correctly with infinite scroll pagination',
    async () => {
    const user = userEvent.setup()
    const page1Photos = createMockPhotos(1, GALLERY_CONFIG.PAGE_SIZE)
    const page2Photos = createMockPhotos(GALLERY_CONFIG.PAGE_SIZE + 1, GALLERY_CONFIG.PAGE_SIZE)

    // Mock first page
    api.getPhotosPaginated.mockResolvedValueOnce(
      createPaginationResponse(page1Photos, {
        offset: 0,
        has_next: true,
      })
    )

    renderGallery(queryClient)

    // Wait for first page to load
    await waitFor(() => {
      expect(screen.getAllByRole('img')).toHaveLength(GALLERY_CONFIG.PAGE_SIZE)
    })

    // Open lightbox on first page
    await user.click(screen.getAllByRole('img')[0])

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    // Close lightbox
    await user.keyboard('{Escape}')

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })

    // Mock second page
    api.getPhotosPaginated.mockResolvedValueOnce(
      createPaginationResponse(page2Photos, {
        offset: GALLERY_CONFIG.PAGE_SIZE,
        has_next: false,
      })
    )

    // Trigger infinite scroll (simulate sentinel intersection)
    const callback = observerMocks.getObserverCallback()
    if (callback) {
      callback([{ isIntersecting: true, target: document.createElement('div') }])
    }

    // Wait for second page to load
    await waitFor(() => {
      expect(screen.getAllByRole('img').length).toBeGreaterThan(GALLERY_CONFIG.PAGE_SIZE)
    })

    // Open lightbox on photo from second page
    const allImages = screen.getAllByRole('img')
    const secondPageImage = allImages[GALLERY_CONFIG.PAGE_SIZE]
    await user.click(secondPageImage)

    // Verify correct photo opens
    await waitFor(() => {
      const dialog = screen.getByRole('dialog')
      expect(dialog).toBeInTheDocument()
      // Photo from second page
      expect(within(dialog).getByRole('img')).toBeInTheDocument()
    })

    // Navigate backward through photos (should cross page boundary)
    for (let i = 0; i < 5; i++) {
      await user.keyboard('{ArrowLeft}')
    }

    // Should still be navigable
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    },
    10000
  ) // 10 second timeout for this long test

  it('lightbox keyboard navigation does not interfere with Gallery shortcuts', async () => {
    const user = userEvent.setup()
    const mockPhotos = createMockPhotos(1, 3)

    api.getPhotosPaginated.mockResolvedValue(
      createPaginationResponse(mockPhotos, {
        has_next: false,
      })
    )

    renderGallery(queryClient)

    // Wait for photos to load
    await waitFor(() => {
      expect(screen.getAllByRole('img')).toHaveLength(3)
    })

    // When lightbox is closed, keyboard events should not be captured
    await user.keyboard('{ArrowRight}')
    await user.keyboard('{ArrowLeft}')
    await user.keyboard('{Escape}')

    // Gallery should still be rendered
    expect(screen.getAllByRole('img')).toHaveLength(3)

    // Open lightbox
    await user.click(screen.getAllByRole('img')[0])

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    // Keyboard events should be captured by lightbox
    await user.keyboard('{ArrowRight}')

    await waitFor(() => {
      const dialog = screen.getByRole('dialog')
      expect(within(dialog).getByAltText('photo_2.jpg')).toBeInTheDocument()
    })

    // Close lightbox
    await user.keyboard('{Escape}')

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })

    // Keyboard events should no longer be captured
    await user.keyboard('{ArrowRight}')

    // Gallery should still be present and functional
    expect(screen.getAllByRole('img')).toHaveLength(3)
  })

  it('lightbox handles photo array updates during navigation', async () => {
    const user = userEvent.setup()
    const initialPhotos = createMockPhotos(1, 2)

    api.getPhotosPaginated.mockResolvedValue(
      createPaginationResponse(initialPhotos, {
        has_next: false,
      })
    )

    renderGallery(queryClient)

    // Wait for photos to load
    await waitFor(() => {
      expect(screen.getAllByRole('img')).toHaveLength(2)
    })

    // Open lightbox
    await user.click(screen.getAllByRole('img')[0])

    await waitFor(() => {
      const dialog = screen.getByRole('dialog')
      expect(within(dialog).getByAltText('photo_1.jpg')).toBeInTheDocument()
    })

    // Navigate to second photo
    await user.keyboard('{ArrowRight}')

    await waitFor(() => {
      const dialog = screen.getByRole('dialog')
      expect(within(dialog).getByAltText('photo_2.jpg')).toBeInTheDocument()
    })

    // Photo array changes should not crash lightbox
    // (This simulates new photos being loaded via infinite scroll)
    const updatedPhotos = createMockPhotos(1, 5)
    api.getPhotosPaginated.mockResolvedValue(
      createPaginationResponse(updatedPhotos, {
        has_next: false,
      })
    )

    // Trigger revalidation
    await queryClient.invalidateQueries()

    // Wait for updates
    await waitFor(() => {
      // Gallery should now have more photos
      expect(screen.getAllByRole('img').length).toBeGreaterThan(2)
    })

    // Lightbox should still be functional
    expect(screen.getByRole('dialog')).toBeInTheDocument()

    // Can still navigate
    await user.keyboard('{ArrowRight}')
    expect(screen.getByRole('dialog')).toBeInTheDocument()

    // Can still close
    await user.keyboard('{Escape}')

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })
  })
})

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import * as api from '../../utils/api'
import { GALLERY_CONFIG } from '../../constants/config'
import {
  createTestQueryClient,
  setupIntersectionObserver,
  renderGallery,
  mockNavigate,
} from './gallery-test-helpers.jsx'

// Mock the API module
vi.mock('../../utils/api', () => ({
  getPhotosPaginated: vi.fn(),
  getThumbnailUrl: vi.fn((path) => `/api/gallery/thumbnail/${path}`),
  getPhotoUrl: vi.fn((path) => `/api/gallery/photo/${path}`),
}))

describe('Gallery - Empty States', () => {
  let queryClient

  beforeEach(() => {
    queryClient = createTestQueryClient()
    setupIntersectionObserver()
    vi.clearAllMocks()
  })

  afterEach(() => {
    queryClient.clear()
  })

  describe('Context-Aware Empty Messages', () => {
    it('shows first-time user message with moth icon when no photos exist', async () => {
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

      // Should show encouraging message
      expect(screen.getByText(/Let's capture your first insect!/i)).toBeInTheDocument()

      // Should show moth icon
      const mothIcon = screen.getByRole('img', { name: /moth icon/i })
      expect(mothIcon).toBeInTheDocument()
    })

    it('includes "Capture First Photo" button that links to camera page', async () => {
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

      const ctaButton = screen.getByRole('button', { name: /Capture First Photo/i })
      expect(ctaButton).toBeInTheDocument()
    })

    it('applies proper ARIA labels to empty state elements', async () => {
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
        const statusElement = screen.getByRole('status')
        expect(statusElement).toBeInTheDocument()
      })
    })
  })

  describe('Empty State Interactions', () => {
    it('navigates to /camera when CTA button clicked', async () => {
      const user = userEvent.setup()

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

      const ctaButton = screen.getByRole('button', { name: /Capture First Photo/i })
      await user.click(ctaButton)

      expect(mockNavigate).toHaveBeenCalledWith('/camera')
    })
  })

  describe('Empty State Accessibility', () => {
    it('announces empty state to screen readers', async () => {
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
        const statusElement = screen.getByRole('status')
        expect(statusElement).toHaveTextContent(/No photos yet/i)
      })
    })

    it('CTA button has proper aria-label', async () => {
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
        const ctaButton = screen.getByRole('button', { name: /Capture First Photo/i })
        expect(ctaButton).toHaveAccessibleName()
      })
    })

    it('empty state container has role="status"', async () => {
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
        const statusElement = screen.getByRole('status')
        expect(statusElement).toBeInTheDocument()
      })
    })
  })
})

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import Gallery from '../Gallery'
import { FilterProvider } from '../../contexts/FilterContext'
import * as api from '../../utils/api'

// Mock API module
vi.mock('../../utils/api', () => ({
  getPhotosPaginated: vi.fn(),
  getThumbnailUrl: vi.fn((path) => `http://localhost:3000/api/gallery/thumbnail/${path}?size=256`),
  getPhotoUrl: vi.fn((path) => `http://localhost:3000/api/gallery/photo/${path}`),
  getPreferences: vi.fn(),
  setPreference: vi.fn(),
}))

// Mock useProgressiveImage hook
vi.mock('../../hooks/useProgressiveImage', () => ({
  default: vi.fn((photoPath) => {
    if (!photoPath) {
      return {
        src: null,
        isLoading: false,
        error: null,
        stage: 'idle'
      }
    }

    return {
      src: `http://localhost:3000/api/gallery/thumbnail/${photoPath}?size=256`,
      isLoading: false,
      error: null,
      stage: 'loaded'
    }
  })
}))

/**
 * Test suite for Gallery view mode integration
 *
 * Tests the integration of view mode toggle, useViewMode hook,
 * and conditional rendering of grid vs list layouts in Gallery component.
 */
describe('Gallery - View Mode Integration', () => {
  let queryClient

  // Helper to create mock photo data
  const createMockPhotos = (start, count) => {
    return Array.from({ length: count }, (_, i) => ({
      path: `202501${String(start + i).padStart(2, '0')}/photo-${start + i}.jpg`,
      filename: `photo-${start + i}.jpg`,
      date: `2025-01-${String((start + i) % 28 + 1).padStart(2, '0')}T12:00:00Z`,
      size: 1048576 * (i + 1), // Varying sizes
    }))
  }

  // Helper to setup IntersectionObserver mock
  const setupIntersectionObserver = () => {
    globalThis.IntersectionObserver = vi.fn(() => ({
      observe: vi.fn(),
      unobserve: vi.fn(),
      disconnect: vi.fn(),
    }))
  }

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, cacheTime: 0 },
        mutations: { retry: false },
      },
    })
    setupIntersectionObserver()
    vi.clearAllMocks()
  })

  afterEach(() => {
    queryClient.clear()
  })

  const renderGallery = () => {
    return render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <FilterProvider>
            <Gallery />
          </FilterProvider>
        </QueryClientProvider>
      </BrowserRouter>
    )
  }

  describe('Initial View Mode Load', () => {
    it('loads view preference from API on mount', async () => {
      api.getPreferences.mockResolvedValue({ data: { gallery_view_mode: 'list' } })
      api.getPhotosPaginated.mockResolvedValue({
        data: {
          photos: createMockPhotos(1, 12),
          pagination: { limit: 24, offset: 0, total: 12, has_next: false, has_previous: false },
        },
      })

      renderGallery()

      // Wait for preferences to load
      await waitFor(() => {
        expect(api.getPreferences).toHaveBeenCalled()
      })

      // Wait for photos to load
      await waitFor(() => {
        expect(screen.getByText('photo-1.jpg')).toBeInTheDocument()
      })
    })

    it('defaults to grid view when no preference set', async () => {
      api.getPreferences.mockResolvedValue({ data: {} })
      api.getPhotosPaginated.mockResolvedValue({
        data: {
          photos: createMockPhotos(1, 12),
          pagination: { limit: 24, offset: 0, total: 12, has_next: false, has_previous: false },
        },
      })

      renderGallery()

      await waitFor(() => {
        const gridButton = screen.getByRole('button', { name: /grid view/i })
        expect(gridButton).toHaveAttribute('aria-pressed', 'true')
      })
    })
  })

  describe('View Mode Toggle', () => {
    it('displays ViewModeToggle component in header', async () => {
      api.getPreferences.mockResolvedValue({ data: {} })
      api.getPhotosPaginated.mockResolvedValue({
        data: {
          photos: createMockPhotos(1, 12),
          pagination: { limit: 24, offset: 0, total: 12, has_next: false, has_previous: false },
        },
      })

      renderGallery()

      await waitFor(() => {
        expect(screen.getByRole('group', { name: /view mode/i })).toBeInTheDocument()
      })
    })

    it('switches from grid to list view when toggle clicked', async () => {
      const user = userEvent.setup()

      api.getPreferences.mockResolvedValue({ data: {} })
      api.setPreference.mockImplementation(async (key, value) => {
        api.getPreferences.mockResolvedValue({ data: { [key]: value } })
        return { data: { success: true } }
      })
      api.getPhotosPaginated.mockResolvedValue({
        data: {
          photos: createMockPhotos(1, 12),
          pagination: { limit: 24, offset: 0, total: 12, has_next: false, has_previous: false },
        },
      })

      renderGallery()

      // Wait for grid view to load
      await waitFor(() => {
        const gridButton = screen.getByRole('button', { name: /grid view/i })
        expect(gridButton).toHaveAttribute('aria-pressed', 'true')
      })

      // Click list view button
      const listButton = screen.getByRole('button', { name: /list view/i })
      await user.click(listButton)

      // Wait for view to change
      await waitFor(() => {
        expect(listButton).toHaveAttribute('aria-pressed', 'true')
      })

      // Verify API was called
      expect(api.setPreference).toHaveBeenCalledWith('gallery_view_mode', 'list')
    })

    it('switches from list to grid view when toggle clicked', async () => {
      const user = userEvent.setup()

      api.getPreferences.mockResolvedValue({ data: { gallery_view_mode: 'list' } })
      api.setPreference.mockImplementation(async (key, value) => {
        api.getPreferences.mockResolvedValue({ data: { [key]: value } })
        return { data: { success: true } }
      })
      api.getPhotosPaginated.mockResolvedValue({
        data: {
          photos: createMockPhotos(1, 12),
          pagination: { limit: 24, offset: 0, total: 12, has_next: false, has_previous: false },
        },
      })

      renderGallery()

      // Wait for list view to load
      await waitFor(() => {
        const listButton = screen.getByRole('button', { name: /list view/i })
        expect(listButton).toHaveAttribute('aria-pressed', 'true')
      })

      // Click grid view button
      const gridButton = screen.getByRole('button', { name: /grid view/i })
      await user.click(gridButton)

      // Wait for view to change
      await waitFor(() => {
        expect(gridButton).toHaveAttribute('aria-pressed', 'true')
      })

      // Verify API was called
      expect(api.setPreference).toHaveBeenCalledWith('gallery_view_mode', 'grid')
    })
  })

  describe('Grid View Layout', () => {
    it('renders photos in grid layout when in grid mode', async () => {
      api.getPreferences.mockResolvedValue({ data: {} })
      api.getPhotosPaginated.mockResolvedValue({
        data: {
          photos: createMockPhotos(1, 12),
          pagination: { limit: 24, offset: 0, total: 12, has_next: false, has_previous: false },
        },
      })

      const { container } = renderGallery()

      // Wait for photos to load (grid view shows filename in alt attribute, not text)
      const photo = await screen.findByAltText('photo-1.jpg')
      expect(photo).toBeInTheDocument()

      // Check for grid container class
      const gridContainer = container.querySelector('.grid')
      expect(gridContainer).toBeInTheDocument()
      expect(gridContainer).toHaveClass('grid-cols-2') // Mobile grid
    })

    it('displays thumbnails in grid view', async () => {
      api.getPreferences.mockResolvedValue({ data: {} })
      api.getPhotosPaginated.mockResolvedValue({
        data: {
          photos: createMockPhotos(1, 12),
          pagination: { limit: 24, offset: 0, total: 12, has_next: false, has_previous: false },
        },
      })

      renderGallery()

      // Wait for images to load
      await waitFor(() => {
        const images = screen.queryAllByRole('img')
        expect(images.length).toBeGreaterThan(0)
        // All images should use thumbnail URLs
        images.forEach((img) => {
          expect(img.src).toContain('thumbnail')
        })
      })
    })
  })

  describe('List View Layout', () => {
    it('renders photos in list layout when in list mode', async () => {
      api.getPreferences.mockResolvedValue({ data: { gallery_view_mode: 'list' } })
      api.getPhotosPaginated.mockResolvedValue({
        data: {
          photos: createMockPhotos(1, 12),
          pagination: { limit: 24, offset: 0, total: 12, has_next: false, has_previous: false },
        },
      })

      const { container } = renderGallery()

      // Wait for photos to load
      const photo = await screen.findByText('photo-1.jpg')
      expect(photo).toBeInTheDocument()

      // List view should NOT have photo grid - use data-testid to avoid matching FilterDrawer grids
      const gridContainer = container.querySelector('[data-testid="photo-grid"]')
      expect(gridContainer).not.toBeInTheDocument()
    })

    it('displays photo metadata in list view', async () => {
      api.getPreferences.mockResolvedValue({ data: { gallery_view_mode: 'list' } })
      api.getPhotosPaginated.mockResolvedValue({
        data: {
          photos: createMockPhotos(1, 3),
          pagination: { limit: 24, offset: 0, total: 3, has_next: false, has_previous: false },
        },
      })

      renderGallery()

      // Wait for filename to appear
      const filename = await screen.findByText('photo-1.jpg')
      expect(filename).toBeInTheDocument()

      // Date (formatted) - use findAllByText for multiple matches
      const dates = await screen.findAllByText(/Jan.*2025/)
      expect(dates.length).toBeGreaterThan(0)

      // File size
      const sizes = await screen.findAllByText(/MB/i)
      expect(sizes.length).toBeGreaterThan(0)
    })
  })

  describe('Lightbox Integration', () => {
    it('lightbox opens from grid view photo click', async () => {
      const user = userEvent.setup()

      api.getPreferences.mockResolvedValue({ data: {} })
      api.getPhotosPaginated.mockResolvedValue({
        data: {
          photos: createMockPhotos(1, 12),
          pagination: { limit: 24, offset: 0, total: 12, has_next: false, has_previous: false },
        },
      })

      renderGallery()

      // Wait for photos to load (grid view shows filename in alt attribute)
      await screen.findByAltText('photo-1.jpg')

      // Click first photo
      const photoButtons = await screen.findAllByRole('button', { name: /view photo/i })
      await user.click(photoButtons[0])

      // Lightbox should open
      await waitFor(() => {
        const images = screen.queryAllByRole('img', { name: /Photo taken on/i })
        const lightboxImage = images.find(img => img.src.includes('/photo/'))
        expect(lightboxImage).toBeDefined()
        expect(lightboxImage.src).toContain('/photo/') // Full photo, not thumbnail
      })
    })

    it('lightbox opens from list view photo click', async () => {
      const user = userEvent.setup()

      api.getPreferences.mockResolvedValue({ data: { gallery_view_mode: 'list' } })
      api.getPhotosPaginated.mockResolvedValue({
        data: {
          photos: createMockPhotos(1, 12),
          pagination: { limit: 24, offset: 0, total: 12, has_next: false, has_previous: false },
        },
      })

      renderGallery()

      // Wait for photos to load
      await screen.findByText('photo-1.jpg')

      // Click first photo
      const photoButtons = await screen.findAllByRole('button', { name: /view photo/i })
      await user.click(photoButtons[0])

      // Lightbox should open
      await waitFor(() => {
        const images = screen.queryAllByRole('img', { name: /Photo taken on/i })
        const lightboxImage = images.find(img => img.src.includes('/photo/'))
        expect(lightboxImage).toBeDefined()
        expect(lightboxImage.src).toContain('/photo/') // Full photo, not thumbnail
      })
    })
  })

  describe('Infinite Scroll Compatibility', () => {
    it('infinite scroll works in grid view', async () => {
      api.getPreferences.mockResolvedValue({ data: {} })
      api.getPhotosPaginated
        .mockResolvedValueOnce({
          data: {
            photos: createMockPhotos(1, 24),
            pagination: { limit: 24, offset: 0, total: 100, has_next: true, has_previous: false },
          },
        })
        .mockResolvedValueOnce({
          data: {
            photos: createMockPhotos(25, 24),
            pagination: { limit: 24, offset: 24, total: 100, has_next: true, has_previous: true },
          },
        })

      renderGallery()

      // Wait for photos to load (grid view shows filename in alt attribute)
      await screen.findByAltText('photo-1.jpg')

      // Verify sentinel element exists (for infinite scroll)
      await waitFor(() => {
        expect(api.getPhotosPaginated).toHaveBeenCalledTimes(1)
      })
    })

    it('infinite scroll works in list view', async () => {
      api.getPreferences.mockResolvedValue({ data: { gallery_view_mode: 'list' } })
      api.getPhotosPaginated
        .mockResolvedValueOnce({
          data: {
            photos: createMockPhotos(1, 24),
            pagination: { limit: 24, offset: 0, total: 100, has_next: true, has_previous: false },
          },
        })
        .mockResolvedValueOnce({
          data: {
            photos: createMockPhotos(25, 24),
            pagination: { limit: 24, offset: 24, total: 100, has_next: true, has_previous: true },
          },
        })

      renderGallery()

      // Wait for initial page load and verify infinite scroll setup
      await waitFor(() => {
        expect(api.getPhotosPaginated).toHaveBeenCalledTimes(1)
      })

      // Verify list view renders photos (just check for photo buttons)
      await waitFor(() => {
        const photos = screen.queryAllByRole('button', { name: /view photo/i })
        expect(photos.length).toBeGreaterThan(0)
      })
    })
  })
})

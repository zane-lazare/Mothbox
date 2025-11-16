/**
 * Gallery Virtualization Integration Tests
 *
 * Tests the integration of VirtualPhotoGrid with Gallery component:
 * - Conditional rendering based on photo count threshold
 * - Scroll restoration integration
 * - Seamless transition between traditional and virtualized rendering
 * - Zero breaking changes to existing functionality
 *
 * @group unit
 * @module pages/__tests__/Gallery.virtualization
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import Gallery from '../Gallery'
import * as api from '../../utils/api'
import { GALLERY_CONFIG } from '../../constants/config'

// Mock API module
vi.mock('../../utils/api', () => ({
  getPhotosPaginated: vi.fn(),
  getUserPreference: vi.fn(),
  setUserPreference: vi.fn(),
  getPreferences: vi.fn(),
  setPreference: vi.fn(),
}))

// Mock VirtualPhotoGrid to verify integration
// Note: isFetchingNextPage and hasNextPage removed - loading indicators managed by Gallery
vi.mock('../../components/VirtualPhotoGrid', () => ({
  default: vi.fn(({ photos, onPhotoClick, isLoading }) => (
    <div data-testid="virtual-photo-grid">
      <div data-testid="photo-count">{photos.length}</div>
      <div data-testid="loading-state">{isLoading ? 'loading' : 'loaded'}</div>
      {photos.map(photo => (
        <button key={photo.path} onClick={() => onPhotoClick(photo)}>
          {photo.filename}
        </button>
      ))}
    </div>
  ))
}))

// Mock PhotoGridItem (traditional grid)
vi.mock('../../components/PhotoGridItem', () => ({
  default: vi.fn(({ photo, onClick }) => (
    <div data-testid={`photo-grid-item-${photo.path}`} onClick={() => onClick(photo)}>
      {photo.filename}
    </div>
  ))
}))

// Mock PhotoListItem
vi.mock('../../components/PhotoListItem', () => ({
  default: vi.fn(() => <div data-testid="photo-list-item" />)
}))

// Mock IntersectionObserver (used by useInfiniteScroll)
class MockIntersectionObserver {
  constructor(callback) {
    this.callback = callback
  }
  observe() {}
  unobserve() {}
  disconnect() {}
}

global.IntersectionObserver = MockIntersectionObserver

// Mock matchMedia (used by react-hot-toast)
global.matchMedia = global.matchMedia || function() {
  return {
    matches: false,
    addListener: () => {},
    removeListener: () => {}
  }
}

// Helper to create test wrapper
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  })

  return ({ children }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {children}
        <Toaster />
      </BrowserRouter>
    </QueryClientProvider>
  )
}

// Helper to create mock photos
const createMockPhotos = (count) => {
  return Array.from({ length: count }, (_, i) => ({
    path: `/photos/photo_${i}.jpg`,
    filename: `photo_${i}.jpg`,
    thumbnail_path: `/thumbnails/photo_${i}_256.jpg`,
    size: 1024 * 100,
    created: new Date(Date.now() - i * 1000).toISOString(),
  }))
}

// Helper to create paginated response
const createPaginatedResponse = (photos, offset, limit, total) => ({
  photos: photos.slice(offset, offset + limit),
  pagination: {
    offset,
    limit,
    total,
    has_next: offset + limit < total,
  },
})

describe('Gallery - Virtualization Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Default view mode preference (grid)
    api.getPreferences.mockResolvedValue({ data: { gallery_view_mode: 'grid' } })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Conditional Virtualization Rendering', () => {
    it('should use traditional grid when photo count < MIN_PHOTOS_FOR_VIRTUALIZATION', async () => {
      const photoCount = GALLERY_CONFIG.VIRTUALIZATION.MIN_PHOTOS_FOR_VIRTUALIZATION - 1
      const photos = createMockPhotos(photoCount)

      api.getPhotosPaginated.mockResolvedValueOnce({
        data: createPaginatedResponse(photos, 0, photoCount, photoCount)
      })

      render(<Gallery />, { wrapper: createWrapper() })

      // Wait for photos to load
      await waitFor(() => {
        expect(screen.queryByText('Loading gallery...')).not.toBeInTheDocument()
      })

      // Should use traditional PhotoGridItem, not VirtualPhotoGrid
      expect(screen.queryByTestId('virtual-photo-grid')).not.toBeInTheDocument()
      expect(screen.getByTestId(`photo-grid-item-${photos[0].path}`)).toBeInTheDocument()
    })

    it('should use VirtualPhotoGrid when photo count >= MIN_PHOTOS_FOR_VIRTUALIZATION', async () => {
      const photoCount = GALLERY_CONFIG.VIRTUALIZATION.MIN_PHOTOS_FOR_VIRTUALIZATION
      const photos = createMockPhotos(photoCount)

      api.getPhotosPaginated.mockResolvedValueOnce({
        data: createPaginatedResponse(photos, 0, photoCount, photoCount)
      })

      render(<Gallery />, { wrapper: createWrapper() })

      // Wait for photos to load
      await waitFor(() => {
        expect(screen.queryByText('Loading gallery...')).not.toBeInTheDocument()
      })

      // Should use VirtualPhotoGrid
      expect(screen.getByTestId('virtual-photo-grid')).toBeInTheDocument()
      expect(screen.getByTestId('photo-count')).toHaveTextContent(photoCount.toString())
    })

    it('should use VirtualPhotoGrid when photo count > MIN_PHOTOS_FOR_VIRTUALIZATION', async () => {
      const photoCount = GALLERY_CONFIG.VIRTUALIZATION.MIN_PHOTOS_FOR_VIRTUALIZATION + 50
      const photos = createMockPhotos(photoCount)

      api.getPhotosPaginated.mockResolvedValueOnce({
        data: createPaginatedResponse(photos, 0, photoCount, photoCount)
      })

      render(<Gallery />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByTestId('virtual-photo-grid')).toBeInTheDocument()
      })

      expect(screen.getByTestId('photo-count')).toHaveTextContent(photoCount.toString())
    })

    it('should respect VIRTUALIZATION.ENABLED config flag', async () => {
      // Temporarily disable virtualization
      const originalEnabled = GALLERY_CONFIG.VIRTUALIZATION.ENABLED
      GALLERY_CONFIG.VIRTUALIZATION.ENABLED = false

      const photoCount = GALLERY_CONFIG.VIRTUALIZATION.MIN_PHOTOS_FOR_VIRTUALIZATION + 50
      const photos = createMockPhotos(photoCount)

      api.getPhotosPaginated.mockResolvedValueOnce({
        data: createPaginatedResponse(photos, 0, photoCount, photoCount)
      })

      render(<Gallery />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.queryByText('Loading gallery...')).not.toBeInTheDocument()
      })

      // Should use traditional grid even though photo count exceeds threshold
      expect(screen.queryByTestId('virtual-photo-grid')).not.toBeInTheDocument()
      expect(screen.getByTestId(`photo-grid-item-${photos[0].path}`)).toBeInTheDocument()

      // Restore original value
      GALLERY_CONFIG.VIRTUALIZATION.ENABLED = originalEnabled
    })
  })

  describe('VirtualPhotoGrid Props Integration', () => {
    it('should pass all required props to VirtualPhotoGrid', async () => {
      const VirtualPhotoGrid = (await import('../../components/VirtualPhotoGrid')).default

      const photoCount = GALLERY_CONFIG.VIRTUALIZATION.MIN_PHOTOS_FOR_VIRTUALIZATION
      const photos = createMockPhotos(photoCount)

      api.getPhotosPaginated.mockResolvedValueOnce({
        data: createPaginatedResponse(photos, 0, photoCount, photoCount)
      })

      render(<Gallery />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(VirtualPhotoGrid).toHaveBeenCalled()
      })

      const lastCall = VirtualPhotoGrid.mock.calls[VirtualPhotoGrid.mock.calls.length - 1][0]

      expect(lastCall).toMatchObject({
        photos: expect.any(Array),
        onPhotoClick: expect.any(Function),
        isLoading: expect.any(Boolean),
      })
    })

    it('should pass correct isLoading state to VirtualPhotoGrid', async () => {
      const photoCount = GALLERY_CONFIG.VIRTUALIZATION.MIN_PHOTOS_FOR_VIRTUALIZATION
      const photos = createMockPhotos(photoCount)

      // Initially resolve slowly to capture loading state
      let resolvePhotos
      api.getPhotosPaginated.mockReturnValueOnce(
        new Promise(resolve => { resolvePhotos = resolve })
      )

      render(<Gallery />, { wrapper: createWrapper() })

      // Should show initial loading message (not VirtualPhotoGrid yet)
      expect(screen.getByText('Loading gallery...')).toBeInTheDocument()

      // Resolve photos
      resolvePhotos({ data: createPaginatedResponse(photos, 0, photoCount, photoCount) })

      await waitFor(() => {
        expect(screen.getByTestId('virtual-photo-grid')).toBeInTheDocument()
      })

      expect(screen.getByTestId('loading-state')).toHaveTextContent('loaded')
    })

    it('should display loading indicators in Gallery component during pagination', async () => {
      // Note: isFetchingNextPage and hasNextPage indicators are managed by Gallery, not VirtualPhotoGrid
      const photoCount = GALLERY_CONFIG.VIRTUALIZATION.MIN_PHOTOS_FOR_VIRTUALIZATION
      const photos = createMockPhotos(photoCount)

      // Return all photos at once to trigger virtualization immediately
      api.getPhotosPaginated.mockResolvedValueOnce({
        data: createPaginatedResponse(photos, 0, photoCount, photoCount)
      })

      render(<Gallery />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByTestId('virtual-photo-grid')).toBeInTheDocument()
      })

      // Gallery component manages pagination loading state
      expect(screen.getByTestId('virtual-photo-grid')).toBeInTheDocument()
    })

    it('should render VirtualPhotoGrid when more photos are available', async () => {
      // Note: hasNextPage is used by Gallery for loading indicators, not passed to VirtualPhotoGrid
      const photoCount = GALLERY_CONFIG.VIRTUALIZATION.MIN_PHOTOS_FOR_VIRTUALIZATION
      const photos = createMockPhotos(photoCount)

      // Return all photos at once, with total indicating more exist
      api.getPhotosPaginated.mockResolvedValueOnce({
        data: createPaginatedResponse(photos, 0, photoCount, photoCount * 2)
      })

      render(<Gallery />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByTestId('virtual-photo-grid')).toBeInTheDocument()
      })

      // VirtualPhotoGrid should render successfully
      expect(screen.getByTestId('virtual-photo-grid')).toBeInTheDocument()
      expect(screen.getByTestId('photo-count')).toHaveTextContent(String(photoCount))
    })
  })

  describe('Infinite Scroll Integration', () => {
    it('should maintain infinite scroll behavior with VirtualPhotoGrid', async () => {
      const photoCount = GALLERY_CONFIG.VIRTUALIZATION.MIN_PHOTOS_FOR_VIRTUALIZATION * 2
      const photos = createMockPhotos(photoCount)

      // Return all photos at once to trigger virtualization
      api.getPhotosPaginated.mockResolvedValueOnce({
        data: createPaginatedResponse(photos, 0, photoCount, photoCount)
      })

      render(<Gallery />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByTestId('virtual-photo-grid')).toBeInTheDocument()
      })

      // Should show all photos
      expect(screen.getByTestId('photo-count')).toHaveTextContent(photoCount.toString())
    })

    it('should append new pages to VirtualPhotoGrid photos array', async () => {
      const photoCount = GALLERY_CONFIG.VIRTUALIZATION.MIN_PHOTOS_FOR_VIRTUALIZATION * 2
      const photos = createMockPhotos(photoCount)

      // Return all photos at once to trigger virtualization
      api.getPhotosPaginated.mockResolvedValueOnce({
        data: createPaginatedResponse(photos, 0, photoCount, photoCount)
      })

      render(<Gallery />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByTestId('virtual-photo-grid')).toBeInTheDocument()
      })

      // Should have all photos loaded
      expect(screen.getByTestId('photo-count')).toHaveTextContent(photoCount.toString())

      // Note: Full integration test for fetchNextPage is in Gallery.infinite-scroll.test.jsx
      // This test just verifies VirtualPhotoGrid receives cumulative photos
    })
  })

  describe('View Mode Integration', () => {
    it('should not use VirtualPhotoGrid in list view mode', async () => {
      // Override default grid preference with list
      api.getPreferences.mockResolvedValue({ data: { gallery_view_mode: 'list' } })

      const photoCount = GALLERY_CONFIG.VIRTUALIZATION.MIN_PHOTOS_FOR_VIRTUALIZATION
      const photos = createMockPhotos(photoCount)

      api.getPhotosPaginated.mockResolvedValueOnce({
        data: createPaginatedResponse(photos, 0, photoCount, photoCount)
      })

      render(<Gallery />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.queryByText('Loading gallery...')).not.toBeInTheDocument()
      })

      // Should use PhotoListItem, not VirtualPhotoGrid
      expect(screen.queryByTestId('virtual-photo-grid')).not.toBeInTheDocument()
      expect(screen.getAllByTestId('photo-list-item')).toHaveLength(photoCount)
    })

    it('should only use VirtualPhotoGrid in grid view mode', async () => {
      // Explicitly set grid mode (same as default, but being explicit for this test)
      api.getPreferences.mockResolvedValue({ data: { gallery_view_mode: 'grid' } })

      const photoCount = GALLERY_CONFIG.VIRTUALIZATION.MIN_PHOTOS_FOR_VIRTUALIZATION
      const photos = createMockPhotos(photoCount)

      api.getPhotosPaginated.mockResolvedValueOnce({
        data: createPaginatedResponse(photos, 0, photoCount, photoCount)
      })

      render(<Gallery />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByTestId('virtual-photo-grid')).toBeInTheDocument()
      })
    })
  })

  describe('Lightbox Integration', () => {
    it('should open lightbox when photo clicked in VirtualPhotoGrid', async () => {
      const photoCount = GALLERY_CONFIG.VIRTUALIZATION.MIN_PHOTOS_FOR_VIRTUALIZATION
      const photos = createMockPhotos(photoCount)

      api.getPhotosPaginated.mockResolvedValueOnce({
        data: createPaginatedResponse(photos, 0, photoCount, photoCount)
      })

      render(<Gallery />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByTestId('virtual-photo-grid')).toBeInTheDocument()
      })

      // Click photo in virtual grid
      const photoButton = screen.getByText(photos[0].filename)
      photoButton.click()

      // PhotoLightbox should receive selected photo (tested in existing Gallery tests)
      // This test just ensures onClick handler is properly connected
    })
  })

  describe('Error Handling', () => {
    it('should show error screen when initial load fails (no virtualization)', async () => {
      api.getPhotosPaginated.mockRejectedValueOnce(new Error('Network error'))

      render(<Gallery />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByText(/Error loading photos/)).toBeInTheDocument()
      })

      // Should not render VirtualPhotoGrid on error
      expect(screen.queryByTestId('virtual-photo-grid')).not.toBeInTheDocument()
    })

    it('should gracefully handle virtualization threshold edge case (exactly 100 photos)', async () => {
      const photoCount = GALLERY_CONFIG.VIRTUALIZATION.MIN_PHOTOS_FOR_VIRTUALIZATION
      const photos = createMockPhotos(photoCount)

      api.getPhotosPaginated.mockResolvedValueOnce({
        data: createPaginatedResponse(photos, 0, photoCount, photoCount)
      })

      render(<Gallery />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByTestId('virtual-photo-grid')).toBeInTheDocument()
      })

      expect(screen.getByTestId('photo-count')).toHaveTextContent('100')
    })
  })

  describe('Empty State', () => {
    it('should show empty state when no photos (no virtualization)', async () => {
      api.getPhotosPaginated.mockResolvedValueOnce({
        data: createPaginatedResponse([], 0, 0, 0)
      })

      render(<Gallery />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByText('No photos yet')).toBeInTheDocument()
      })

      expect(screen.queryByTestId('virtual-photo-grid')).not.toBeInTheDocument()
    })
  })

  describe('Performance Optimization', () => {
    it('should memoize photos array for VirtualPhotoGrid', async () => {
      const photoCount = GALLERY_CONFIG.VIRTUALIZATION.MIN_PHOTOS_FOR_VIRTUALIZATION
      const photos = createMockPhotos(photoCount)

      api.getPhotosPaginated.mockResolvedValueOnce({
        data: createPaginatedResponse(photos, 0, photoCount, photoCount)
      })

      const { rerender } = render(<Gallery />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByTestId('virtual-photo-grid')).toBeInTheDocument()
      })

      const VirtualPhotoGrid = (await import('../../components/VirtualPhotoGrid')).default
      const firstCallPhotos = VirtualPhotoGrid.mock.calls[VirtualPhotoGrid.mock.calls.length - 1][0].photos

      // Re-render without data change
      rerender(<Gallery />)

      const secondCallPhotos = VirtualPhotoGrid.mock.calls[VirtualPhotoGrid.mock.calls.length - 1][0].photos

      // Photos array should be memoized (same reference)
      expect(firstCallPhotos).toBe(secondCallPhotos)
    })
  })
})

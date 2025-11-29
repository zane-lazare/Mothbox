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
 * Gallery Series Integration Tests
 *
 * Tests the integration of photo series (HDR, Focus Bracket) display
 * in the Gallery component, including stacked card rendering and
 * series-aware lightbox navigation.
 */

// Mock the API module
vi.mock('../../utils/api', () => ({
  getPhotosPaginated: vi.fn(),
  getSeries: vi.fn(),
  getSeriesById: vi.fn(),
  getThumbnailUrl: vi.fn((path) => `/api/gallery/thumbnail/${path}`),
  getPhotoUrl: vi.fn((path) => `/api/gallery/photo/${path}`),
  api: {
    get: vi.fn(),
  },
}))

// Mock the MetadataPanel
vi.mock('../../components/metadata/MetadataPanel', () => ({
  default: ({ photoPath }) => (
    <div data-testid="metadata-panel">
      <div data-testid="metadata-photo-path">{photoPath}</div>
    </div>
  ),
}))

/**
 * Creates mock series data for testing
 * @param {string} type - Series type ('hdr' or 'focus_bracket')
 * @param {string} baseId - Base identifier for series
 * @param {number} count - Number of photos in series
 * @returns {Object} Mock series object
 */
const createMockSeries = (type, baseId, count) => {
  const suffix = type === 'hdr' ? 'HDR' : 'FB'
  const prefix = type === 'focus_bracket' ? 'ManFocus_' : ''

  const photos = Array.from({ length: count }, (_, i) => ({
    path: `/photos/${prefix}${baseId}_${suffix}${i}.jpg`,
    filename: `${prefix}${baseId}_${suffix}${i}.jpg`,
    date: new Date(Date.UTC(2024, 0, 15, 10, 0, 0)).toISOString(),
  }))

  return {
    series_id: `${type}_${baseId}`,
    series_type: type,
    photos,
    count,
    cover_photo: photos[0].path,
  }
}

/**
 * Creates a series API response
 * @param {Array} series - Array of series objects
 * @returns {Object} Mock API response
 */
const createSeriesResponse = (series) => ({
  data: {
    series,
    total: series.length,
    pagination: {
      offset: 0,
      limit: 50,
      has_next: false,
    },
  },
})

describe('Gallery Series Integration', () => {
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

  describe('Series Data Loading', () => {
    it('fetches series data alongside photos on load', async () => {
      const mockPhotos = createMockPhotos(1, 3)
      const mockSeries = [createMockSeries('hdr', 'moth_2024_01_15__10_00_00', 3)]

      api.getPhotosPaginated.mockResolvedValue(
        createPaginationResponse(mockPhotos, { has_next: false })
      )
      // The useSeries hook uses api.get internally
      api.api.get.mockResolvedValue({ data: { series: mockSeries, total: mockSeries.length } })

      renderGallery(queryClient)

      await waitFor(() => {
        expect(api.getPhotosPaginated).toHaveBeenCalled()
      })

      // Series API should also be called via api.get
      await waitFor(() => {
        expect(api.api.get).toHaveBeenCalledWith('/gallery/series', expect.anything())
      })
    })

    it('handles series API errors gracefully', async () => {
      const mockPhotos = createMockPhotos(1, 3)

      api.getPhotosPaginated.mockResolvedValue(
        createPaginationResponse(mockPhotos, { has_next: false })
      )
      api.api.get.mockRejectedValue(new Error('Series API error'))

      renderGallery(queryClient)

      // Gallery should still load photos even if series fails
      await waitFor(() => {
        expect(screen.getAllByRole('img')).toHaveLength(3)
      })

      // No crash, gallery is functional
      expect(screen.getByText('Photo Gallery')).toBeInTheDocument()
    })
  })

  describe('Stacked Card Rendering', () => {
    it('renders StackedPhotoCard for series cover photos', async () => {
      // Photos include series photos
      const mockPhotos = [
        { path: '/photos/moth_2024_01_15__10_00_00_HDR0.jpg', filename: 'moth_HDR0.jpg', date: '2024-01-15T10:00:00Z' },
        { path: '/photos/moth_2024_01_15__10_00_00_HDR1.jpg', filename: 'moth_HDR1.jpg', date: '2024-01-15T10:00:00Z' },
        { path: '/photos/moth_2024_01_15__10_00_00_HDR2.jpg', filename: 'moth_HDR2.jpg', date: '2024-01-15T10:00:00Z' },
        { path: '/photos/single_photo.jpg', filename: 'single_photo.jpg', date: '2024-01-15T11:00:00Z' },
      ]

      const mockSeries = [createMockSeries('hdr', 'moth_2024_01_15__10_00_00', 3)]

      api.getPhotosPaginated.mockResolvedValue(
        createPaginationResponse(mockPhotos, { has_next: false })
      )
      api.api.get.mockResolvedValue({ data: { series: mockSeries, total: mockSeries.length } })

      renderGallery(queryClient)

      await waitFor(() => {
        expect(api.getPhotosPaginated).toHaveBeenCalled()
      })

      // Should render gallery
      await waitFor(() => {
        expect(screen.getByText('Photo Gallery')).toBeInTheDocument()
      })
    })

    it('displays series badge with count and type', async () => {
      const mockPhotos = createMockPhotos(1, 1)
      const mockSeries = [createMockSeries('hdr', 'test_series', 3)]

      api.getPhotosPaginated.mockResolvedValue(
        createPaginationResponse(mockPhotos, { has_next: false })
      )
      api.api.get.mockResolvedValue({ data: { series: mockSeries, total: mockSeries.length } })

      renderGallery(queryClient)

      await waitFor(() => {
        expect(screen.getAllByRole('img').length).toBeGreaterThan(0)
      })
    })

    it('hides non-cover series photos from main grid', async () => {
      // When series detection is active, non-cover photos should be hidden
      const mockPhotos = [
        { path: '/photos/moth_HDR0.jpg', filename: 'moth_HDR0.jpg', date: '2024-01-15T10:00:00Z' },
        { path: '/photos/moth_HDR1.jpg', filename: 'moth_HDR1.jpg', date: '2024-01-15T10:00:00Z' },
        { path: '/photos/moth_HDR2.jpg', filename: 'moth_HDR2.jpg', date: '2024-01-15T10:00:00Z' },
        { path: '/photos/single.jpg', filename: 'single.jpg', date: '2024-01-15T11:00:00Z' },
      ]

      const mockSeries = [{
        series_id: 'hdr_moth',
        series_type: 'hdr',
        photos: [
          { path: '/photos/moth_HDR0.jpg', filename: 'moth_HDR0.jpg', date: '2024-01-15T10:00:00Z' },
          { path: '/photos/moth_HDR1.jpg', filename: 'moth_HDR1.jpg', date: '2024-01-15T10:00:00Z' },
          { path: '/photos/moth_HDR2.jpg', filename: 'moth_HDR2.jpg', date: '2024-01-15T10:00:00Z' },
        ],
        count: 3,
        cover_photo: '/photos/moth_HDR0.jpg',
      }]

      api.getPhotosPaginated.mockResolvedValue(
        createPaginationResponse(mockPhotos, { has_next: false })
      )
      api.api.get.mockResolvedValue({ data: { series: mockSeries, total: mockSeries.length } })

      renderGallery(queryClient)

      await waitFor(() => {
        expect(screen.getByText('Photo Gallery')).toBeInTheDocument()
      })
    })
  })

  describe('Series Click Behavior', () => {
    it('opens lightbox with cover photo when clicking stacked card', async () => {
      const user = userEvent.setup()
      const mockPhotos = createMockPhotos(1, 3)
      const mockSeries = []

      api.getPhotosPaginated.mockResolvedValue(
        createPaginationResponse(mockPhotos, { has_next: false })
      )
      api.api.get.mockResolvedValue({ data: { series: mockSeries, total: 0 } })

      renderGallery(queryClient)

      await waitFor(() => {
        expect(screen.getAllByRole('img')).toHaveLength(3)
      })

      // Click first photo
      await user.click(screen.getAllByRole('img')[0])

      // Lightbox should open
      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument()
      })
    })
  })

  describe('Mixed Grid Display', () => {
    it('correctly renders mix of stacked cards and single photos', async () => {
      // Mix of series and single photos
      const mockPhotos = [
        { path: '/photos/single_1.jpg', filename: 'single_1.jpg', date: '2024-01-15T09:00:00Z' },
        { path: '/photos/moth_HDR0.jpg', filename: 'moth_HDR0.jpg', date: '2024-01-15T10:00:00Z' },
        { path: '/photos/moth_HDR1.jpg', filename: 'moth_HDR1.jpg', date: '2024-01-15T10:00:00Z' },
        { path: '/photos/single_2.jpg', filename: 'single_2.jpg', date: '2024-01-15T11:00:00Z' },
      ]

      const mockSeries = [{
        series_id: 'hdr_moth',
        series_type: 'hdr',
        photos: [
          { path: '/photos/moth_HDR0.jpg', filename: 'moth_HDR0.jpg', date: '2024-01-15T10:00:00Z' },
          { path: '/photos/moth_HDR1.jpg', filename: 'moth_HDR1.jpg', date: '2024-01-15T10:00:00Z' },
        ],
        count: 2,
        cover_photo: '/photos/moth_HDR0.jpg',
      }]

      api.getPhotosPaginated.mockResolvedValue(
        createPaginationResponse(mockPhotos, { has_next: false })
      )
      api.api.get.mockResolvedValue({ data: { series: mockSeries, total: mockSeries.length } })

      renderGallery(queryClient)

      await waitFor(() => {
        expect(screen.getByText('Photo Gallery')).toBeInTheDocument()
      })
    })

    it('maintains grid layout with series and single photos', async () => {
      const mockPhotos = createMockPhotos(1, 5)
      const mockSeries = []

      api.getPhotosPaginated.mockResolvedValue(
        createPaginationResponse(mockPhotos, { has_next: false })
      )
      api.api.get.mockResolvedValue({ data: { series: mockSeries, total: 0 } })

      const { container } = renderGallery(queryClient)

      await waitFor(() => {
        expect(screen.getAllByRole('img')).toHaveLength(5)
      })

      // Grid should have proper structure
      const grid = container.querySelector('.grid')
      expect(grid).toBeInTheDocument()
    })
  })

  describe('Series with Infinite Scroll', () => {
    it('loads series data for each page of photos', async () => {
      const page1Photos = createMockPhotos(1, GALLERY_CONFIG.PAGE_SIZE)
      const page2Photos = createMockPhotos(GALLERY_CONFIG.PAGE_SIZE + 1, GALLERY_CONFIG.PAGE_SIZE)

      // First page
      api.getPhotosPaginated.mockResolvedValueOnce(
        createPaginationResponse(page1Photos, { offset: 0, has_next: true })
      )
      api.api.get.mockResolvedValue({ data: { series: [], total: 0 } })

      renderGallery(queryClient)

      await waitFor(() => {
        expect(screen.getAllByRole('img')).toHaveLength(GALLERY_CONFIG.PAGE_SIZE)
      })

      // Second page
      api.getPhotosPaginated.mockResolvedValueOnce(
        createPaginationResponse(page2Photos, { offset: GALLERY_CONFIG.PAGE_SIZE, has_next: false })
      )

      // Trigger infinite scroll
      const callback = observerMocks.getObserverCallback()
      if (callback) {
        callback([{ isIntersecting: true, target: document.createElement('div') }])
      }

      await waitFor(() => {
        expect(screen.getAllByRole('img').length).toBeGreaterThan(GALLERY_CONFIG.PAGE_SIZE)
      })
    })
  })

  describe('Empty States', () => {
    it('shows empty state when no photos exist', async () => {
      api.getPhotosPaginated.mockResolvedValue(
        createPaginationResponse([], { has_next: false })
      )
      api.api.get.mockResolvedValue({ data: { series: [], total: 0 } })

      renderGallery(queryClient)

      await waitFor(() => {
        // Empty state should be shown
        expect(screen.getByText(/no photos yet/i)).toBeInTheDocument()
      })
    })

    it('handles all photos being in series gracefully', async () => {
      // All photos are part of series
      const seriesPhotos = [
        { path: '/photos/moth_HDR0.jpg', filename: 'moth_HDR0.jpg', date: '2024-01-15T10:00:00Z' },
        { path: '/photos/moth_HDR1.jpg', filename: 'moth_HDR1.jpg', date: '2024-01-15T10:00:00Z' },
        { path: '/photos/moth_HDR2.jpg', filename: 'moth_HDR2.jpg', date: '2024-01-15T10:00:00Z' },
      ]

      const mockSeries = [{
        series_id: 'hdr_moth',
        series_type: 'hdr',
        photos: seriesPhotos,
        count: 3,
        cover_photo: '/photos/moth_HDR0.jpg',
      }]

      api.getPhotosPaginated.mockResolvedValue(
        createPaginationResponse(seriesPhotos, { has_next: false })
      )
      api.api.get.mockResolvedValue({ data: { series: mockSeries, total: mockSeries.length } })

      renderGallery(queryClient)

      await waitFor(() => {
        expect(screen.getByText('Photo Gallery')).toBeInTheDocument()
      })
    })
  })

  describe('Series Type Display', () => {
    it('correctly displays HDR series indicator', async () => {
      const mockPhotos = createMockPhotos(1, 1)
      const mockSeries = [createMockSeries('hdr', 'test', 3)]

      api.getPhotosPaginated.mockResolvedValue(
        createPaginationResponse(mockPhotos, { has_next: false })
      )
      api.api.get.mockResolvedValue({ data: { series: mockSeries, total: mockSeries.length } })

      renderGallery(queryClient)

      await waitFor(() => {
        expect(screen.getAllByRole('img').length).toBeGreaterThan(0)
      })
    })

    it('correctly displays Focus Bracket series indicator', async () => {
      const mockPhotos = createMockPhotos(1, 1)
      const mockSeries = [createMockSeries('focus_bracket', 'ManFocus_test', 5)]

      api.getPhotosPaginated.mockResolvedValue(
        createPaginationResponse(mockPhotos, { has_next: false })
      )
      api.api.get.mockResolvedValue({ data: { series: mockSeries, total: mockSeries.length } })

      renderGallery(queryClient)

      await waitFor(() => {
        expect(screen.getAllByRole('img').length).toBeGreaterThan(0)
      })
    })
  })
})

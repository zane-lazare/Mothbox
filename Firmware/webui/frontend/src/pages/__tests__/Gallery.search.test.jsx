import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import * as api from '../../utils/api'
import {
  createMockPhotos,
  createTestQueryClient,
  setupIntersectionObserver,
  renderGallery,
  createPaginationResponse,
} from './gallery-test-helpers.jsx'

/**
 * Gallery Search Integration Tests
 *
 * Tests the integration of search functionality into the Gallery page,
 * verifying SearchBar visibility, search execution, result display,
 * and advanced search builder integration.
 */

// Mock the API module
vi.mock('../../utils/api', () => ({
  getPhotosPaginated: vi.fn(),
  searchPhotos: vi.fn(),
  getThumbnailUrl: vi.fn((path) => `/api/gallery/thumbnail/${path}`),
  getPhotoUrl: vi.fn((path) => `/api/gallery/photo/${path}`),
}))

// Mock the MetadataPanel to avoid API dependencies in these tests
vi.mock('../../components/metadata/MetadataPanel', () => ({
  default: ({ photoPath }) => (
    <div data-testid="metadata-panel">
      <div>Camera</div>
      <div>Location</div>
      <div data-testid="metadata-photo-path">{photoPath}</div>
    </div>
  ),
}))

describe('Gallery Search Integration', () => {
  let queryClient
  let observerMocks

  beforeEach(() => {
    queryClient = createTestQueryClient()
    observerMocks = setupIntersectionObserver()
    vi.clearAllMocks()

    // Setup default API responses
    api.getPhotosPaginated.mockResolvedValue(
      createPaginationResponse([], { total: 0 })
    )
  })

  afterEach(() => {
    queryClient.clear()
  })

  describe('SearchBar visibility', () => {
    it('should render SearchBar in gallery', async () => {
      renderGallery(queryClient)

      await waitFor(() => {
        expect(screen.getByRole('searchbox')).toBeInTheDocument()
      })
    })

    it('should show search placeholder', async () => {
      renderGallery(queryClient)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/search/i)).toBeInTheDocument()
      })
    })
  })

  describe('search functionality', () => {
    it('should call search API when typing', async () => {
      const user = userEvent.setup()
      api.searchPhotos.mockResolvedValue({
        results: [],
        total: 0,
        query: 'moth',
        parsed_query: 'moth',
        took_ms: 10,
        pagination: { limit: 20, offset: 0, has_next: false, has_prev: false }
      })

      renderGallery(queryClient)

      const searchInput = await screen.findByRole('searchbox')
      await user.type(searchInput, 'moth')

      // Wait for debounce + API call (usePhotoSearch has 300ms debounce)
      await waitFor(() => {
        expect(api.searchPhotos).toHaveBeenCalledWith('moth', expect.any(Object))
      }, { timeout: 1000 })
    })

    it('should display search results', async () => {
      const user = userEvent.setup()
      api.searchPhotos.mockResolvedValue({
        results: [
          {
            filename: 'moth1.jpg',
            path: '2024-11/moth1.jpg',
            thumbnail_url: '/api/gallery/thumbnail/2024-11/moth1.jpg',
            metadata: { tags: ['moth', 'luna'] },
            score: 0.95,
            matched_fields: ['tags'],
            date: new Date(Date.UTC(2024, 10, 1)).toISOString(),
            size: 1024 * 1024,
          }
        ],
        total: 1,
        query: 'moth',
        parsed_query: 'moth',
        took_ms: 10,
        pagination: { limit: 20, offset: 0, has_next: false, has_prev: false }
      })

      renderGallery(queryClient)

      const searchInput = await screen.findByRole('searchbox')
      await user.type(searchInput, 'moth')

      // Wait for results to display - check for result count message
      await waitFor(() => {
        expect(screen.getByText(/1 result/i)).toBeInTheDocument()
      }, { timeout: 1000 })

      // Verify the photo is rendered (as an image)
      const images = screen.getAllByRole('img')
      expect(images.length).toBeGreaterThan(0)
    })

    it('should show result count', async () => {
      const user = userEvent.setup()
      api.searchPhotos.mockResolvedValue({
        results: [],
        total: 45,
        query: 'moth',
        parsed_query: 'moth',
        took_ms: 10,
        pagination: { limit: 20, offset: 0, has_next: true, has_prev: false }
      })

      renderGallery(queryClient)

      const searchInput = await screen.findByRole('searchbox')
      await user.type(searchInput, 'moth')

      await waitFor(() => {
        expect(screen.getByText(/45 results/i)).toBeInTheDocument()
      }, { timeout: 1000 })
    })

    it('should show no results message', async () => {
      const user = userEvent.setup()
      api.searchPhotos.mockResolvedValue({
        results: [],
        total: 0,
        query: 'nonexistent',
        parsed_query: 'nonexistent',
        took_ms: 10,
        pagination: { limit: 20, offset: 0, has_next: false, has_prev: false }
      })

      renderGallery(queryClient)

      const searchInput = await screen.findByRole('searchbox')
      await user.type(searchInput, 'nonexistent')

      await waitFor(() => {
        expect(screen.getByText(/no results/i)).toBeInTheDocument()
      }, { timeout: 1000 })
    })
  })

  describe('clearing search', () => {
    it('should restore gallery when search cleared', async () => {
      const user = userEvent.setup()
      const mockGalleryPhotos = createMockPhotos(1, 3)

      // Mock search results
      api.searchPhotos.mockResolvedValue({
        results: [
          {
            filename: 'moth1.jpg',
            path: 'moth1.jpg',
            date: new Date(Date.UTC(2024, 10, 1)).toISOString(),
            size: 1024 * 1024,
          }
        ],
        total: 1,
        query: 'moth',
        parsed_query: 'moth',
        took_ms: 10,
        pagination: { limit: 20, offset: 0, has_next: false, has_prev: false }
      })

      // Mock gallery photos
      api.getPhotosPaginated.mockResolvedValue(
        createPaginationResponse(mockGalleryPhotos, { has_next: false })
      )

      renderGallery(queryClient)

      // Perform search
      const searchInput = await screen.findByRole('searchbox')
      await user.type(searchInput, 'moth')

      // Wait for search results (check for result count message)
      await waitFor(() => {
        expect(screen.getByText(/1 result/i)).toBeInTheDocument()
      }, { timeout: 1000 })

      // Clear search (use specific label to avoid matching "Clear all filters" in FilterDrawer)
      const clearButton = await screen.findByLabelText(/clear search/i)
      await user.click(clearButton)

      // Should restore regular gallery view - verify gallery photos are shown
      await waitFor(() => {
        // Gallery should show all 3 photos
        const images = screen.getAllByRole('img')
        expect(images.length).toBe(3)
      })
    })
  })

  describe('advanced search', () => {
    it('should show advanced search button', async () => {
      renderGallery(queryClient)

      await waitFor(() => {
        expect(screen.getByLabelText(/advanced/i)).toBeInTheDocument()
      })
    })

    it('should open advanced search builder', async () => {
      const user = userEvent.setup()
      renderGallery(queryClient)

      const advancedButton = await screen.findByLabelText(/advanced/i)
      await user.click(advancedButton)

      expect(screen.getByText(/advanced search/i)).toBeInTheDocument()
    })

    it('should apply advanced search query', async () => {
      const user = userEvent.setup()
      api.searchPhotos.mockResolvedValue({
        results: [],
        total: 0,
        query: 'tag:moth',
        parsed_query: 'tag:moth',
        took_ms: 10,
        pagination: { limit: 20, offset: 0, has_next: false, has_prev: false }
      })

      renderGallery(queryClient)

      // Open advanced search
      const advancedButton = await screen.findByLabelText(/advanced/i)
      await user.click(advancedButton)

      // Fill in condition
      const valueInput = screen.getByLabelText(/value/i)
      await user.type(valueInput, 'moth')

      // Apply search
      const applyButton = screen.getByText(/apply search/i)
      await user.click(applyButton)

      // Wait for search to execute
      await waitFor(() => {
        expect(api.searchPhotos).toHaveBeenCalledWith('tag:moth', expect.any(Object))
      }, { timeout: 1000 })
    })
  })

  describe('loading states', () => {
    it('should show loading indicator during search', async () => {
      const user = userEvent.setup()
      // Mock search to never resolve (simulate long-running search)
      api.searchPhotos.mockImplementation(() => new Promise(() => {}))

      renderGallery(queryClient)

      const searchInput = await screen.findByRole('searchbox')
      await user.type(searchInput, 'moth')

      // Wait for loading indicator to appear
      await waitFor(() => {
        expect(screen.getByTestId('search-loading')).toBeInTheDocument()
      }, { timeout: 1000 })
    })
  })

  describe('search mode vs normal gallery mode', () => {
    it('should hide infinite scroll when search is active', async () => {
      const user = userEvent.setup()
      const mockGalleryPhotos = createMockPhotos(1, 30)

      // Mock gallery with pagination
      api.getPhotosPaginated.mockResolvedValue(
        createPaginationResponse(mockGalleryPhotos, { has_next: true })
      )

      // Mock search results
      api.searchPhotos.mockResolvedValue({
        results: [
          {
            filename: 'moth1.jpg',
            path: 'moth1.jpg',
            date: new Date(Date.UTC(2024, 10, 1)).toISOString(),
            size: 1024 * 1024,
          }
        ],
        total: 1,
        query: 'moth',
        parsed_query: 'moth',
        took_ms: 10,
        pagination: { limit: 20, offset: 0, has_next: false, has_prev: false }
      })

      renderGallery(queryClient)

      // Wait for initial gallery to load
      await waitFor(() => {
        expect(screen.getAllByRole('img').length).toBeGreaterThan(0)
      })

      // Perform search
      const searchInput = await screen.findByRole('searchbox')
      await user.type(searchInput, 'moth')

      // Wait for search results
      await waitFor(() => {
        expect(screen.getByText(/1 result/i)).toBeInTheDocument()
      }, { timeout: 1000 })

      // Should not show "All photos loaded" message from infinite scroll
      expect(screen.queryByText(/all photos loaded/i)).not.toBeInTheDocument()
    })

    it('should show normal gallery after clearing search', async () => {
      const user = userEvent.setup()
      const mockGalleryPhotos = createMockPhotos(1, 5)

      // Mock search results
      api.searchPhotos.mockResolvedValue({
        results: [
          {
            filename: 'moth1.jpg',
            path: 'moth1.jpg',
            date: new Date(Date.UTC(2024, 10, 1)).toISOString(),
            size: 1024 * 1024,
          }
        ],
        total: 1,
        query: 'moth',
        parsed_query: 'moth',
        took_ms: 10,
        pagination: { limit: 20, offset: 0, has_next: false, has_prev: false }
      })

      // Mock gallery photos
      api.getPhotosPaginated.mockResolvedValue(
        createPaginationResponse(mockGalleryPhotos, { has_next: false })
      )

      renderGallery(queryClient)

      // Perform search
      const searchInput = await screen.findByRole('searchbox')
      await user.type(searchInput, 'moth')

      // Wait for search results
      await waitFor(() => {
        expect(screen.getByText(/1 result/i)).toBeInTheDocument()
      }, { timeout: 1000 })

      // Clear search (use specific label to avoid matching "Clear all filters" in FilterDrawer)
      const clearButton = await screen.findByLabelText(/clear search/i)
      await user.click(clearButton)

      // Should show all 5 gallery photos
      await waitFor(() => {
        expect(screen.getAllByRole('img').length).toBe(5)
      })
    })
  })
})

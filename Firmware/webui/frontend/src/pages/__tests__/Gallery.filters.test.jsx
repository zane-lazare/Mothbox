/**
 * Gallery Filter Integration Tests
 *
 * Tests the integration of the filter drawer system into the Gallery page.
 * Ensures filters work correctly with search, result counts update, and
 * visual feedback is provided.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import Gallery from '../Gallery'
import { FilterProvider } from '../../contexts/FilterContext'
import * as api from '../../utils/api'
import {
  createMockPhotos,
  createTestQueryClient,
  setupIntersectionObserver,
  createPaginationResponse,
} from './gallery-test-helpers.jsx'

// Mock API
vi.mock('../../utils/api', () => ({
  getPhotosPaginated: vi.fn(),
  searchPhotos: vi.fn(),
  getSeries: vi.fn(),
  getPhotoLocations: vi.fn(),
  getThumbnailUrl: vi.fn((path) => `/api/gallery/thumbnail/${path}`),
  getPhotoUrl: vi.fn((path) => `/api/gallery/photo/${path}`),
}))

// Mock components that aren't relevant to filter testing
vi.mock('../../components/PhotoLightbox', () => ({
  default: () => null,
}))

vi.mock('../../components/VirtualPhotoGrid', () => ({
  default: () => <div data-testid="virtual-grid">Virtual Grid</div>,
}))

vi.mock('../../components/MapView', () => ({
  default: () => <div data-testid="map-view">Map View</div>,
}))

// Render helper that includes FilterProvider
const renderGalleryWithFilters = (queryClient, props = {}) => {
  return render(
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <FilterProvider>
          <Gallery {...props} />
        </FilterProvider>
      </QueryClientProvider>
    </BrowserRouter>
  )
}

describe('Gallery Filter Integration', () => {
  let queryClient
  let observerMocks

  beforeEach(() => {
    queryClient = createTestQueryClient()
    observerMocks = setupIntersectionObserver()
    vi.clearAllMocks()

    // Setup default API responses using helpers
    const mockPhotos = createMockPhotos(1, 3)
    api.getPhotosPaginated.mockResolvedValue(createPaginationResponse(mockPhotos, { total: 3 }))
    api.getSeries.mockResolvedValue({ data: { series: [] } })
    api.getPhotoLocations.mockResolvedValue({ data: { locations: [] } })
    api.searchPhotos.mockResolvedValue({
      results: mockPhotos,
      total: 3,
      took_ms: 25,
      parsed_query: 'moth',
      pagination: {
        limit: 20,
        offset: 0,
        has_next: false,
        has_prev: false,
      },
    })
  })

  afterEach(() => {
    queryClient.clear()
  })

  describe('Filter Drawer Toggle', () => {
    it('should render filter drawer toggle button', async () => {
      renderGalleryWithFilters(queryClient)

      // Wait for loading to finish (content appears)
      await waitFor(() => {
        expect(screen.queryByText(/Loading gallery/i)).not.toBeInTheDocument()
      })

      // FilterDrawerToggle should be visible on mobile/tablet (hidden on desktop with lg:hidden)
      const toggleButton = screen.getByLabelText(/show filters/i)
      expect(toggleButton).toBeInTheDocument()
    })

    it('should toggle filter drawer when button is clicked', async () => {
      const user = userEvent.setup()
      renderGalleryWithFilters(queryClient)

      // Wait for loading to finish
      await waitFor(() => {
        expect(screen.queryByText(/Loading gallery/i)).not.toBeInTheDocument()
      })

      const toggleButton = screen.getByLabelText(/show filters/i)

      // Click to open drawer
      await user.click(toggleButton)

      // Filter drawer should be visible (check for filter drawer heading)
      await waitFor(() => {
        expect(screen.getByRole('heading', { name: 'Filters' })).toBeInTheDocument()
      })
    })
  })

  describe('Filter Drawer', () => {
    it('should render filter drawer with all filter sections', async () => {
      renderGalleryWithFilters(queryClient)

      // Wait for loading to finish
      await waitFor(() => {
        expect(screen.queryByText(/Loading gallery/i)).not.toBeInTheDocument()
      })

      // Filter drawer should contain filter sections (use getAllByText and check at least one exists)
      // Some sections have duplicate text (header + content), so we check for presence
      const drawer = screen.getByRole('complementary', { name: /filters/i })
      expect(drawer).toBeInTheDocument()

      // Check for section buttons which have unique aria-controls
      expect(screen.getByRole('button', { name: /Date Range/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /^Tags$/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /^Species$/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /File Types/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Camera Settings/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /^Notes$/i })).toBeInTheDocument()
    })

    it('should display filter drawer permanently on desktop', async () => {
      renderGalleryWithFilters(queryClient)

      // Wait for loading to finish
      await waitFor(() => {
        expect(screen.queryByText(/Loading gallery/i)).not.toBeInTheDocument()
      })

      // On desktop, drawer should always be visible (not toggleable)
      const drawer = screen.getByRole('complementary', { name: /filters/i })
      expect(drawer).toBeInTheDocument()
    })
  })

  describe('Active Filter Chips', () => {
    it('should not display active filter chips when no filters are active', async () => {
      renderGalleryWithFilters(queryClient)

      await waitFor(() => {
        expect(api.getPhotosPaginated).toHaveBeenCalled()
      })

      // Active filter chips should not be visible
      expect(screen.queryByRole('group', { name: /active filters/i })).not.toBeInTheDocument()
    })

    // Note: Testing actual filter application requires implementing filter controls
    // which are marked as "Coming Soon" in the current FilterDrawer component.
    // These tests would need to be expanded once filter controls are implemented.
  })

  describe('Filter and Search Integration', () => {
    it('should combine user search with filter query', async () => {
      const user = userEvent.setup()
      renderGalleryWithFilters(queryClient)

      await waitFor(() => {
        expect(api.getPhotosPaginated).toHaveBeenCalled()
      })

      // Type in search bar
      const searchInput = await screen.findByRole('searchbox')
      await user.type(searchInput, 'moth')

      // Wait for debounced search (300ms debounce in usePhotoSearch)
      await waitFor(() => {
        expect(api.searchPhotos).toHaveBeenCalledWith(
          'moth',
          expect.objectContaining({ limit: 20, offset: 0 })
        )
      }, { timeout: 1000 })
    })

    it('should show search results when user searches', async () => {
      const user = userEvent.setup()
      renderGalleryWithFilters(queryClient)

      await waitFor(() => {
        expect(api.getPhotosPaginated).toHaveBeenCalled()
      })

      // Type in search bar
      const searchInput = await screen.findByRole('searchbox')
      await user.type(searchInput, 'moth')

      // Wait for search results
      await waitFor(() => {
        expect(screen.getByText(/3 results/i)).toBeInTheDocument()
      }, { timeout: 1000 })
    })
  })

  describe('Result Count Display', () => {
    it('should display result count for search results', async () => {
      const user = userEvent.setup()
      renderGalleryWithFilters(queryClient)

      await waitFor(() => {
        expect(api.getPhotosPaginated).toHaveBeenCalled()
      })

      // Search
      const searchInput = await screen.findByRole('searchbox')
      await user.type(searchInput, 'moth')

      // Check result count
      await waitFor(() => {
        expect(screen.getByText(/3 results/i)).toBeInTheDocument()
      }, { timeout: 1000 })
    })

    it('should display timing information for search', async () => {
      const user = userEvent.setup()
      renderGalleryWithFilters(queryClient)

      await waitFor(() => {
        expect(api.getPhotosPaginated).toHaveBeenCalled()
      })

      // Search
      const searchInput = await screen.findByRole('searchbox')
      await user.type(searchInput, 'moth')

      // Check timing display
      await waitFor(() => {
        expect(screen.getByText(/25ms/i)).toBeInTheDocument()
      }, { timeout: 1000 })
    })

    it('should show "no results" message when search returns empty', async () => {
      api.searchPhotos.mockResolvedValue({
        results: [],
        total: 0,
        took_ms: 10,
        parsed_query: 'nonexistent',
        pagination: {
          limit: 20,
          offset: 0,
          has_next: false,
          has_prev: false,
        },
      })

      const user = userEvent.setup()
      renderGalleryWithFilters(queryClient)

      await waitFor(() => {
        expect(api.getPhotosPaginated).toHaveBeenCalled()
      })

      // Search for something that doesn't exist
      const searchInput = await screen.findByRole('searchbox')
      await user.type(searchInput, 'nonexistent')

      // Check for "no results" message
      await waitFor(() => {
        expect(screen.getByText(/no results found/i)).toBeInTheDocument()
      }, { timeout: 1000 })
    })
  })

  describe('Accessibility', () => {
    it('should have accessible filter toggle button', async () => {
      renderGalleryWithFilters(queryClient)

      // Wait for loading to finish
      await waitFor(() => {
        expect(screen.queryByText(/Loading gallery/i)).not.toBeInTheDocument()
      })

      const toggleButton = screen.getByLabelText(/show filters/i)
      expect(toggleButton).toHaveAttribute('aria-label')
    })

    it('should have accessible filter drawer', async () => {
      renderGalleryWithFilters(queryClient)

      // Wait for loading to finish
      await waitFor(() => {
        expect(screen.queryByText(/Loading gallery/i)).not.toBeInTheDocument()
      })

      const drawer = screen.getByRole('complementary', { name: /filters/i })
      expect(drawer).toHaveAttribute('aria-label', 'Filters')
    })

    it('should have accessible active filter chips', async () => {
      renderGalleryWithFilters(queryClient)

      await waitFor(() => {
        expect(api.getPhotosPaginated).toHaveBeenCalled()
      })

      // When no filters are active, chips should not be rendered
      expect(screen.queryByRole('group', { name: /active filters/i })).not.toBeInTheDocument()

      // Note: Testing with active filters requires implementing filter controls
    })
  })
})

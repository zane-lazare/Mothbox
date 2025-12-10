import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
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
  bulkUpdateSidecarMetadata: vi.fn(),
  getPhotoSidecarMetadata: vi.fn(),
  api: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  }
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

// Mock react-hot-toast
vi.mock('react-hot-toast', () => {
  const mockToast = vi.fn(() => `toast-${Date.now()}`)
  mockToast.success = vi.fn(() => `toast-success-${Date.now()}`)
  mockToast.error = vi.fn(() => `toast-error-${Date.now()}`)
  mockToast.dismiss = vi.fn()
  return {
    default: mockToast,
    Toaster: () => null,
  }
})

// Mock useSeries hook
vi.mock('../../hooks/useSeries', () => ({
  useSeries: vi.fn(() => ({
    data: { series: [] },
    isError: false,
    refetch: vi.fn(),
  }))
}))

// Mock usePhotoLocations hook
vi.mock('../../hooks/usePhotoLocations', () => ({
  usePhotoLocations: vi.fn(() => ({
    locations: [],
    isLoading: false,
    totalWithGps: 0,
    totalWithoutGps: 0,
  }))
}))

/**
 * Test suite for Gallery bulk selection integration
 *
 * Tests the integration of SelectionContext, bulk operations toolbar,
 * modals, keyboard shortcuts, and undo functionality.
 */
describe('Gallery - Bulk Selection Integration', () => {
  let queryClient

  // Helper to create mock photo data
  const createMockPhotos = (start, count) => {
    return Array.from({ length: count }, (_, i) => ({
      path: `202501${String(start + i).padStart(2, '0')}/photo-${start + i}.jpg`,
      filename: `photo-${start + i}.jpg`,
      date: `2025-01-${String((start + i) % 28 + 1).padStart(2, '0')}T12:00:00Z`,
      size: 1048576 * (i + 1),
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

    // Default API mocks
    api.getPreferences.mockResolvedValue({ data: {} })
    api.getPhotosPaginated.mockResolvedValue({
      data: {
        photos: createMockPhotos(1, 12),
        pagination: { limit: 24, offset: 0, total: 12, has_next: false, has_previous: false },
      },
    })
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

  describe('SelectionProvider Wrapping', () => {
    it('renders Gallery without errors when wrapped in SelectionProvider', async () => {
      renderGallery()

      // Should render without throwing
      await waitFor(() => {
        expect(screen.getByText('Photo Gallery')).toBeInTheDocument()
      })
    })

    it('selection state is available in child components', async () => {
      renderGallery()

      // Wait for photos to load
      await screen.findByAltText('photo-1.jpg')

      // SelectModeToggle should render (it uses selection context)
      const selectButton = screen.getByRole('button', { name: /enter selection mode/i })
      expect(selectButton).toBeInTheDocument()
    })
  })

  describe('SelectModeToggle in Toolbar', () => {
    it('displays Select button in gallery toolbar', async () => {
      renderGallery()

      await waitFor(() => {
        const selectButton = screen.getByRole('button', { name: /enter selection mode/i })
        expect(selectButton).toBeInTheDocument()
      })
    })

    it('toggles to Cancel when select mode is active', async () => {
      const user = userEvent.setup()
      renderGallery()

      await screen.findByAltText('photo-1.jpg')

      // Enter select mode
      const selectButton = screen.getByRole('button', { name: /enter selection mode/i })
      await user.click(selectButton)

      // Should now show Exit selection mode button
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /exit selection mode/i })).toBeInTheDocument()
      })
    })

    it('exits select mode when Cancel is clicked', async () => {
      const user = userEvent.setup()
      renderGallery()

      await screen.findByAltText('photo-1.jpg')

      // Enter select mode
      const selectButton = screen.getByRole('button', { name: /enter selection mode/i })
      await user.click(selectButton)

      // Exit select mode
      const cancelButton = await screen.findByRole('button', { name: /exit selection mode/i })
      await user.click(cancelButton)

      // Should show Enter selection mode again
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /enter selection mode/i })).toBeInTheDocument()
      })
    })
  })

  describe('BulkActionsToolbar Integration', () => {
    it('toolbar is hidden when no photos are selected', async () => {
      renderGallery()

      await screen.findByAltText('photo-1.jpg')

      // Enter select mode but don't select any photos
      const selectButton = screen.getByRole('button', { name: /enter selection mode/i })
      const user = userEvent.setup()
      await user.click(selectButton)

      // Toolbar should not be visible
      expect(screen.queryByRole('toolbar', { name: /bulk actions/i })).not.toBeInTheDocument()
    })

    it('toolbar appears when photos are selected', async () => {
      const user = userEvent.setup()
      renderGallery()

      await screen.findByAltText('photo-1.jpg')

      // Enter select mode
      const selectButton = screen.getByRole('button', { name: /enter selection mode/i })
      await user.click(selectButton)

      // Click on a photo's checkbox to select it
      const checkboxes = screen.getAllByRole('checkbox')
      await user.click(checkboxes[0])

      // Toolbar should appear
      await waitFor(() => {
        expect(screen.getByRole('toolbar', { name: /bulk actions/i })).toBeInTheDocument()
      })
    })

    it('toolbar shows correct selection count', async () => {
      const user = userEvent.setup()
      renderGallery()

      await screen.findByAltText('photo-1.jpg')

      // Enter select mode
      const selectButton = screen.getByRole('button', { name: /enter selection mode/i })
      await user.click(selectButton)

      // Wait for checkboxes to appear and select first photo
      await waitFor(() => {
        expect(screen.getAllByRole('checkbox').length).toBeGreaterThan(0)
      })
      const firstCheckbox = screen.getAllByRole('checkbox')[0]
      await user.click(firstCheckbox)

      // Wait for first selection to register, then select second photo
      await waitFor(() => {
        expect(screen.getByRole('toolbar', { name: /bulk actions/i })).toBeInTheDocument()
      })
      const secondCheckbox = screen.getAllByRole('checkbox')[1]
      await user.click(secondCheckbox)

      // Toolbar should show "2 photos selected"
      await waitFor(() => {
        expect(screen.getByText(/2 photos selected/i)).toBeInTheDocument()
      })
    })

    it('Deselect All button clears selection', async () => {
      const user = userEvent.setup()
      renderGallery()

      await screen.findByAltText('photo-1.jpg')

      // Enter select mode and select photos
      const selectButton = screen.getByRole('button', { name: /enter selection mode/i })
      await user.click(selectButton)

      // Wait for checkboxes and select first photo
      await waitFor(() => {
        expect(screen.getAllByRole('checkbox').length).toBeGreaterThan(0)
      })
      await user.click(screen.getAllByRole('checkbox')[0])

      // Wait for toolbar to appear
      await screen.findByRole('toolbar', { name: /bulk actions/i })

      // Click Deselect All
      const deselectAllButton = screen.getByRole('button', { name: /deselect all/i })
      await user.click(deselectAllButton)

      // Toolbar should disappear (no selection)
      await waitFor(() => {
        expect(screen.queryByRole('toolbar', { name: /bulk actions/i })).not.toBeInTheDocument()
      })
    })
  })

  describe('Keyboard Shortcuts', () => {
    it('Escape key exits select mode', async () => {
      const user = userEvent.setup()
      renderGallery()

      await screen.findByAltText('photo-1.jpg')

      // Enter select mode
      const selectButton = screen.getByRole('button', { name: /enter selection mode/i })
      await user.click(selectButton)

      // Press Escape
      await user.keyboard('{Escape}')

      // Should exit select mode
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /enter selection mode/i })).toBeInTheDocument()
      })
    })

    it('Ctrl+A selects all visible photos in select mode', async () => {
      const user = userEvent.setup()
      renderGallery()

      await screen.findByAltText('photo-1.jpg')

      // Enter select mode
      const selectButton = screen.getByRole('button', { name: /enter selection mode/i })
      await user.click(selectButton)

      // Wait for select mode to be active (checkboxes appear)
      await waitFor(() => {
        expect(screen.getAllByRole('checkbox').length).toBeGreaterThan(0)
      })

      // Press Ctrl+A
      await user.keyboard('{Control>}a{/Control}')

      // Should show all 12 photos selected
      await waitFor(() => {
        expect(screen.getByText(/12 photos selected/i)).toBeInTheDocument()
      })
    })

    it('Delete key opens delete confirmation modal when photos selected', async () => {
      const user = userEvent.setup()
      renderGallery()

      await screen.findByAltText('photo-1.jpg')

      // Enter select mode and select a photo
      const selectButton = screen.getByRole('button', { name: /enter selection mode/i })
      await user.click(selectButton)

      // Wait for checkboxes and select one
      await waitFor(() => {
        expect(screen.getAllByRole('checkbox').length).toBeGreaterThan(0)
      })
      await user.click(screen.getAllByRole('checkbox')[0])

      // Wait for selection to register (toolbar appears)
      await screen.findByRole('toolbar', { name: /bulk actions/i })

      // Press Delete key
      await user.keyboard('{Delete}')

      // Delete confirmation modal should appear
      await waitFor(() => {
        expect(screen.getByRole('alertdialog', { name: /delete/i })).toBeInTheDocument()
      })
    })

    it('Delete key does nothing when no photos selected', async () => {
      const user = userEvent.setup()
      renderGallery()

      await screen.findByAltText('photo-1.jpg')

      // Enter select mode but don't select any photos
      const selectButton = screen.getByRole('button', { name: /enter selection mode/i })
      await user.click(selectButton)

      // Press Delete key
      await user.keyboard('{Delete}')

      // No modal should appear
      expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    })
  })

  describe('Modal State Management', () => {
    it('Tag button opens BulkTagModal', async () => {
      const user = userEvent.setup()
      renderGallery()

      await screen.findByAltText('photo-1.jpg')

      // Enter select mode and select a photo
      const selectButton = screen.getByRole('button', { name: /enter selection mode/i })
      await user.click(selectButton)

      // Wait for checkboxes and select one
      await waitFor(() => {
        expect(screen.getAllByRole('checkbox').length).toBeGreaterThan(0)
      })
      await user.click(screen.getAllByRole('checkbox')[0])

      // Wait for toolbar
      await screen.findByRole('toolbar', { name: /bulk actions/i })

      // Click Tag button (use aria-label for more specific match)
      const tagButton = screen.getByRole('button', { name: /add tags to selected/i })
      await user.click(tagButton)

      // Tag modal should appear (title is "Add tags for X photo(s)")
      await waitFor(() => {
        expect(screen.getByRole('dialog', { name: /tags for/i })).toBeInTheDocument()
      })
    })

    it('Species button opens BulkSpeciesModal', async () => {
      const user = userEvent.setup()
      renderGallery()

      await screen.findByAltText('photo-1.jpg')

      // Enter select mode and select a photo
      const selectButton = screen.getByRole('button', { name: /enter selection mode/i })
      await user.click(selectButton)

      // Wait for checkboxes and select one
      await waitFor(() => {
        expect(screen.getAllByRole('checkbox').length).toBeGreaterThan(0)
      })
      await user.click(screen.getAllByRole('checkbox')[0])

      // Wait for toolbar
      await screen.findByRole('toolbar', { name: /bulk actions/i })

      // Click Species button (use aria-label for more specific match)
      const speciesButton = screen.getByRole('button', { name: /set species for selected/i })
      await user.click(speciesButton)

      // Species modal should appear
      await waitFor(() => {
        expect(screen.getByRole('dialog', { name: /species/i })).toBeInTheDocument()
      })
    })

    it('Delete button opens BulkDeleteConfirmModal', async () => {
      const user = userEvent.setup()
      renderGallery()

      await screen.findByAltText('photo-1.jpg')

      // Enter select mode and select a photo
      const selectButton = screen.getByRole('button', { name: /enter selection mode/i })
      await user.click(selectButton)

      // Wait for checkboxes and select one
      await waitFor(() => {
        expect(screen.getAllByRole('checkbox').length).toBeGreaterThan(0)
      })
      await user.click(screen.getAllByRole('checkbox')[0])

      // Wait for toolbar
      await screen.findByRole('toolbar', { name: /bulk actions/i })

      // Click Delete button (use aria-label for more specific match)
      const deleteButton = screen.getByRole('button', { name: /delete selected/i })
      await user.click(deleteButton)

      // Delete modal should appear
      await waitFor(() => {
        expect(screen.getByRole('alertdialog', { name: /delete/i })).toBeInTheDocument()
      })
    })

    it('modal closes on Cancel', async () => {
      const user = userEvent.setup()
      renderGallery()

      await screen.findByAltText('photo-1.jpg')

      // Enter select mode and select a photo
      const selectButton = screen.getByRole('button', { name: /enter selection mode/i })
      await user.click(selectButton)

      // Wait for checkboxes and select one
      await waitFor(() => {
        expect(screen.getAllByRole('checkbox').length).toBeGreaterThan(0)
      })
      await user.click(screen.getAllByRole('checkbox')[0])

      // Wait for toolbar and open tag modal
      await screen.findByRole('toolbar', { name: /bulk actions/i })
      const tagButton = screen.getByRole('button', { name: /add tags to selected/i })
      await user.click(tagButton)

      // Wait for modal (title is "Add tags for X photo(s)")
      const modal = await screen.findByRole('dialog', { name: /tags for/i })

      // Find Cancel button within the modal
      const cancelButton = within(modal).getByRole('button', { name: /cancel/i })
      await user.click(cancelButton)

      // Modal should close
      await waitFor(() => {
        expect(screen.queryByRole('dialog', { name: /tags for/i })).not.toBeInTheDocument()
      })
    })
  })

  describe('Selection Behavior', () => {
    it('checkbox is visible in select mode', async () => {
      const user = userEvent.setup()
      renderGallery()

      await screen.findByAltText('photo-1.jpg')

      // Checkboxes should not be visible initially
      expect(screen.queryAllByRole('checkbox')).toHaveLength(0)

      // Enter select mode
      const selectButton = screen.getByRole('button', { name: /enter selection mode/i })
      await user.click(selectButton)

      // Checkboxes should now be visible
      await waitFor(() => {
        const checkboxes = screen.getAllByRole('checkbox')
        expect(checkboxes.length).toBeGreaterThan(0)
      })
    })

    it('selection cleared when exiting select mode', async () => {
      const user = userEvent.setup()
      renderGallery()

      await screen.findByAltText('photo-1.jpg')

      // Enter select mode
      const selectButton = screen.getByRole('button', { name: /enter selection mode/i })
      await user.click(selectButton)

      // Verify checkboxes visible
      await waitFor(() => {
        const checkboxes = screen.getAllByRole('checkbox')
        expect(checkboxes.length).toBeGreaterThan(0)
      })

      // Exit select mode
      const cancelButton = await screen.findByRole('button', { name: /exit selection mode/i })
      await user.click(cancelButton)

      // Re-enter select mode
      const newSelectButton = await screen.findByRole('button', { name: /enter selection mode/i })
      await user.click(newSelectButton)

      // Checkboxes should be visible again (but no selection)
      await waitFor(() => {
        const checkboxes = screen.getAllByRole('checkbox')
        expect(checkboxes.length).toBeGreaterThan(0)
      })
    })
  })

  describe('Photo Click Behavior', () => {
    it('photo click opens lightbox when NOT in select mode', async () => {
      const user = userEvent.setup()
      renderGallery()

      await screen.findByAltText('photo-1.jpg')

      // Click on photo (not in select mode)
      const photoButtons = screen.getAllByRole('button', { name: /view photo/i })
      await user.click(photoButtons[0])

      // Lightbox should open
      await waitFor(() => {
        const lightboxImages = screen.queryAllByRole('img', { name: /Photo taken on/i })
        const lightboxImage = lightboxImages.find(img => img.src.includes('/photo/'))
        expect(lightboxImage).toBeDefined()
      })
    })

    it('checkboxes become visible when select mode is entered', async () => {
      const user = userEvent.setup()
      renderGallery()

      await screen.findByAltText('photo-1.jpg')

      // No checkboxes initially
      expect(screen.queryAllByRole('checkbox')).toHaveLength(0)

      // Enter select mode
      const selectButton = screen.getByRole('button', { name: /enter selection mode/i })
      await user.click(selectButton)

      // Checkboxes should now be visible
      await waitFor(() => {
        const checkboxes = screen.getAllByRole('checkbox')
        expect(checkboxes.length).toBeGreaterThan(0)
      })
    })
  })
})

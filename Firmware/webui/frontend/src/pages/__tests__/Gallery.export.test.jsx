/**
 * Gallery Export Integration Tests
 *
 * Tests the integration of export functionality across Gallery components:
 * - PhotoGridItem context menu → PhotoContextMenu → ExportOptionsMenu
 * - PhotoLightbox export button → ExportOptionsMenu
 *
 * These tests verify that the export workflow works correctly end-to-end.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Import components to test
import PhotoGridItem from '../../components/PhotoGridItem'
import PhotoLightbox from '../../components/PhotoLightbox'
import { SelectionProvider } from '../../contexts/SelectionContext'

// Mock ProgressiveImage to avoid image loading complexity
vi.mock('../../components/ProgressiveImage', () => ({
  default: vi.fn(({ src, alt, className }) => (
    <img
      src={src}
      alt={alt}
      className={className}
      data-testid="progressive-image"
    />
  )),
}))

// Mock useSinglePhotoExport
vi.mock('../../hooks/useSinglePhotoExport', () => ({
  useSinglePhotoExport: vi.fn(() => ({
    exportPhoto: vi.fn(),
    isExporting: false,
    progress: null,
    error: null,
    reset: vi.fn(),
  })),
}))

import { useSinglePhotoExport } from '../../hooks/useSinglePhotoExport'

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(() => 'toast-id'),
    dismiss: vi.fn(),
  }
}))

// Test data
const mockPhoto = {
  path: '/photos/moth_with_metadata.jpg',
  filename: 'moth_with_metadata.jpg',
  thumbnail: '/thumbnails/moth_with_metadata.jpg',
}

const mockPhotoNoGps = {
  path: '/photos/moth_no_gps.jpg',
  filename: 'moth_no_gps.jpg',
  thumbnail: '/thumbnails/moth_no_gps.jpg',
}

const mockPhotoMinimal = {
  path: '/photos/moth_minimal.jpg',
  filename: 'moth_minimal.jpg',
  thumbnail: '/thumbnails/moth_minimal.jpg',
}

describe('Gallery Export Integration Tests', () => {
  let queryClient
  let mockExportPhoto

  const createWrapper = () => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    })

    return ({ children }) => (
      <QueryClientProvider client={queryClient}>
        <SelectionProvider>
          {children}
        </SelectionProvider>
      </QueryClientProvider>
    )
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockExportPhoto = vi.fn()
    useSinglePhotoExport.mockReturnValue({
      exportPhoto: mockExportPhoto,
      isExporting: false,
      progress: null,
      error: null,
      reset: vi.fn(),
    })
  })

  afterEach(() => {
    queryClient?.clear()
  })

  describe('PhotoGridItem Context Menu Integration', () => {
    const renderPhotoGridItem = (photo = mockPhoto) => {
      return render(
        <PhotoGridItem
          photo={photo}
          onClick={vi.fn()}
          onLoad={vi.fn()}
        />,
        { wrapper: createWrapper() }
      )
    }

    it('opens context menu on right-click and shows export option', async () => {
      renderPhotoGridItem()

      // Find the photo container and right-click (use the image's parent container)
      const image = screen.getByTestId('progressive-image')
      const photoElement = image.closest('div[class*="relative"]')
      fireEvent.contextMenu(photoElement, { clientX: 100, clientY: 100 })

      // Verify context menu appears with Export option
      await waitFor(() => {
        expect(screen.getByRole('menu')).toBeInTheDocument()
        expect(screen.getByRole('menuitem', { name: /export/i })).toBeInTheDocument()
      })
    })

    it('opens export submenu when hovering on Export option', async () => {
      const user = userEvent.setup()
      renderPhotoGridItem()

      // Right-click to open context menu
      const image = screen.getByTestId('progressive-image')
      const photoElement = image.closest('div[class*="relative"]')
      fireEvent.contextMenu(photoElement, { clientX: 100, clientY: 100 })

      // Wait for context menu
      await waitFor(() => {
        expect(screen.getByRole('menuitem', { name: /export/i })).toBeInTheDocument()
      })

      // Hover on Export to open submenu
      const exportOption = screen.getByRole('menuitem', { name: /export/i })
      await user.hover(exportOption)

      // Verify export options submenu appears
      await waitFor(() => {
        expect(screen.getByText('Export Photo')).toBeInTheDocument()
        expect(screen.getByText('Darwin Core')).toBeInTheDocument()
        expect(screen.getByText('iNaturalist')).toBeInTheDocument()
        expect(screen.getByText('JSON')).toBeInTheDocument()
        expect(screen.getByText('CSV')).toBeInTheDocument()
      })
    })

    it('shows export submenu formats when Export option is hovered', async () => {
      const user = userEvent.setup()
      renderPhotoGridItem()

      // Right-click to open context menu
      const image = screen.getByTestId('progressive-image')
      const photoElement = image.closest('div[class*="relative"]')
      fireEvent.contextMenu(photoElement, { clientX: 100, clientY: 100 })

      // Hover on Export
      await waitFor(() => {
        expect(screen.getByRole('menuitem', { name: /export/i })).toBeInTheDocument()
      })
      const exportOption = screen.getByRole('menuitem', { name: /export/i })
      await user.hover(exportOption)

      // Verify all export formats are shown
      await waitFor(() => {
        expect(screen.getByText('JSON')).toBeInTheDocument()
        expect(screen.getByText('CSV')).toBeInTheDocument()
        expect(screen.getByText('Darwin Core')).toBeInTheDocument()
        expect(screen.getByText('iNaturalist')).toBeInTheDocument()
      })
    })

    it('closes context menu on escape key', async () => {
      renderPhotoGridItem()

      // Right-click to open context menu
      const image = screen.getByTestId('progressive-image')
      const photoElement = image.closest('div[class*="relative"]')
      fireEvent.contextMenu(photoElement, { clientX: 100, clientY: 100 })

      await waitFor(() => {
        expect(screen.getByRole('menu')).toBeInTheDocument()
      })

      // Press Escape
      fireEvent.keyDown(document, { key: 'Escape' })

      // Menu should close
      await waitFor(() => {
        expect(screen.queryByRole('menu')).not.toBeInTheDocument()
      })
    })

    it('context menu works with photos that have minimal metadata', async () => {
      renderPhotoGridItem(mockPhotoMinimal)

      // Right-click to open context menu
      const image = screen.getByTestId('progressive-image')
      const photoElement = image.closest('div[class*="relative"]')
      fireEvent.contextMenu(photoElement, { clientX: 100, clientY: 100 })

      // Verify context menu appears
      await waitFor(() => {
        expect(screen.getByRole('menu')).toBeInTheDocument()
        expect(screen.getByRole('menuitem', { name: /export/i })).toBeInTheDocument()
      })
    })
  })

  describe('PhotoLightbox Export Button Integration', () => {
    const renderLightbox = (photo = mockPhoto, photos = [mockPhoto]) => {
      return render(
        <PhotoLightbox
          photo={photo}
          photos={photos}
          onClose={vi.fn()}
          onNavigate={vi.fn()}
        />,
        { wrapper: createWrapper() }
      )
    }

    it('renders export button in lightbox controls', () => {
      renderLightbox()

      const exportButton = screen.getByRole('button', { name: /export photo/i })
      expect(exportButton).toBeInTheDocument()
    })

    it('opens export menu when export button is clicked', async () => {
      const user = userEvent.setup()
      renderLightbox()

      const exportButton = screen.getByRole('button', { name: /export photo/i })
      await user.click(exportButton)

      // Verify export options menu appears
      await waitFor(() => {
        expect(screen.getByText('Export Photo')).toBeInTheDocument()
        expect(screen.getByText('Darwin Core')).toBeInTheDocument()
        expect(screen.getByText('JSON')).toBeInTheDocument()
      })
    })

    it('triggers export when format is selected from lightbox', async () => {
      const user = userEvent.setup()
      renderLightbox()

      // Click export button
      const exportButton = screen.getByRole('button', { name: /export photo/i })
      await user.click(exportButton)

      // Click Darwin Core format
      await waitFor(() => {
        expect(screen.getByText('Darwin Core')).toBeInTheDocument()
      })
      await user.click(screen.getByText('Darwin Core'))

      // Verify export was triggered
      expect(mockExportPhoto).toHaveBeenCalledWith(mockPhoto.path, 'darwin_core')
    })

    it('export button has correct aria-label for accessibility', async () => {
      renderLightbox()

      // Find export button by its aria-label
      const exportButton = screen.getByRole('button', { name: /export photo/i })
      expect(exportButton).toBeInTheDocument()
      expect(exportButton).toHaveAttribute('aria-label', 'Export photo')
    })

    it('closes export menu on escape', async () => {
      const user = userEvent.setup()
      renderLightbox()

      // Open export menu
      const exportButton = screen.getByRole('button', { name: /export photo/i })
      await user.click(exportButton)

      await waitFor(() => {
        expect(screen.getByText('Export Photo')).toBeInTheDocument()
      })

      // Press Escape
      await user.keyboard('{Escape}')

      // Menu should close (header "Export Photo" should not be visible)
      await waitFor(() => {
        expect(screen.queryByText('Export Photo')).not.toBeInTheDocument()
      })
    })

    it('works with photos without GPS data', async () => {
      const user = userEvent.setup()
      renderLightbox(mockPhotoNoGps, [mockPhotoNoGps])

      // Click export button
      const exportButton = screen.getByRole('button', { name: /export photo/i })
      await user.click(exportButton)

      // Click iNaturalist format
      await waitFor(() => {
        expect(screen.getByText('iNaturalist')).toBeInTheDocument()
      })
      await user.click(screen.getByText('iNaturalist'))

      // Verify export was triggered with photo without GPS
      expect(mockExportPhoto).toHaveBeenCalledWith(mockPhotoNoGps.path, 'inaturalist')
    })
  })

  describe('Export Formats via Lightbox', () => {
    const renderLightbox = (photo = mockPhoto, photos = [mockPhoto]) => {
      return render(
        <PhotoLightbox
          photo={photo}
          photos={photos}
          onClose={vi.fn()}
          onNavigate={vi.fn()}
        />,
        { wrapper: createWrapper() }
      )
    }

    it.each([
      ['Darwin Core', 'darwin_core'],
      ['iNaturalist', 'inaturalist'],
      ['JSON', 'json'],
      ['CSV', 'csv'],
    ])('supports %s export format via lightbox', async (formatName, formatId) => {
      const user = userEvent.setup()
      renderLightbox()

      // Open export menu
      const exportButton = screen.getByRole('button', { name: /export photo/i })
      await user.click(exportButton)

      // Wait for export menu and click the format
      await waitFor(() => {
        expect(screen.getByText(formatName)).toBeInTheDocument()
      })
      // Click the button containing the format name
      const formatButton = screen.getByText(formatName).closest('button')
      await user.click(formatButton)

      // Verify correct format ID was passed
      expect(mockExportPhoto).toHaveBeenCalledWith(mockPhoto.path, formatId)
    })
  })

  describe('Loading States', () => {
    it('shows loading state in export menu while exporting', async () => {
      const user = userEvent.setup()

      // Set isExporting to true
      useSinglePhotoExport.mockReturnValue({
        exportPhoto: mockExportPhoto,
        isExporting: true,
        progress: { percent: 50, phase: 'exporting' },
        error: null,
        reset: vi.fn(),
      })

      render(
        <PhotoLightbox
          photo={mockPhoto}
          photos={[mockPhoto]}
          onClose={vi.fn()}
          onNavigate={vi.fn()}
        />,
        { wrapper: createWrapper() }
      )

      // Open export menu
      const exportButton = screen.getByRole('button', { name: /export photo/i })
      await user.click(exportButton)

      // Verify loading indicator appears
      await waitFor(() => {
        expect(screen.getByText('Exporting...')).toBeInTheDocument()
      })
    })
  })

  describe('Accessibility', () => {
    it('context menu has proper ARIA roles', async () => {
      render(
        <PhotoGridItem
          photo={mockPhoto}
          onClick={vi.fn()}
          onLoad={vi.fn()}
        />,
        { wrapper: createWrapper() }
      )

      // Right-click to open context menu
      const image = screen.getByTestId('progressive-image')
      const photoElement = image.closest('div[class*="relative"]')
      fireEvent.contextMenu(photoElement, { clientX: 100, clientY: 100 })

      await waitFor(() => {
        expect(screen.getByRole('menu')).toBeInTheDocument()
        expect(screen.getByRole('menuitem', { name: /export/i })).toBeInTheDocument()
      })
    })

    it('export options menu has proper ARIA roles', async () => {
      const user = userEvent.setup()

      render(
        <PhotoLightbox
          photo={mockPhoto}
          photos={[mockPhoto]}
          onClose={vi.fn()}
          onNavigate={vi.fn()}
        />,
        { wrapper: createWrapper() }
      )

      // Open export menu
      const exportButton = screen.getByRole('button', { name: /export photo/i })
      await user.click(exportButton)

      await waitFor(() => {
        // Export options menu should have menu role
        const menus = screen.getAllByRole('menu')
        expect(menus.length).toBeGreaterThan(0)

        // Format options should have menuitem roles
        const menuitems = screen.getAllByRole('menuitem')
        expect(menuitems.length).toBeGreaterThanOrEqual(4) // 4 export formats
      })
    })

    it('export menu supports keyboard navigation', async () => {
      const user = userEvent.setup()

      render(
        <PhotoLightbox
          photo={mockPhoto}
          photos={[mockPhoto]}
          onClose={vi.fn()}
          onNavigate={vi.fn()}
        />,
        { wrapper: createWrapper() }
      )

      // Open export menu
      const exportButton = screen.getByRole('button', { name: /export photo/i })
      await user.click(exportButton)

      await waitFor(() => {
        expect(screen.getByText('Darwin Core')).toBeInTheDocument()
      })

      // Use arrow key to navigate
      await user.keyboard('{ArrowDown}')

      // First item should be highlighted
      const darwinCoreOption = screen.getByText('Darwin Core').closest('button')
      expect(darwinCoreOption).toHaveClass('ring-2')
    })
  })
})

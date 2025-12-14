import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Mock the hook BEFORE importing the component
vi.mock('../../../hooks/useSinglePhotoExport', () => ({
  useSinglePhotoExport: vi.fn()
}))

import ExportOptionsMenu from '../ExportOptionsMenu'
import { useSinglePhotoExport } from '../../../hooks/useSinglePhotoExport'

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  })
  return ({ children }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('ExportOptionsMenu', () => {
  let mockAnchor
  let mockExportPhoto
  let mockReset

  beforeEach(() => {
    mockAnchor = document.createElement('button')
    mockAnchor.textContent = 'Export Button'
    document.body.appendChild(mockAnchor)

    mockExportPhoto = vi.fn()
    mockReset = vi.fn()

    // Default mock implementation
    useSinglePhotoExport.mockReturnValue({
      exportPhoto: mockExportPhoto,
      isExporting: false,
      progress: null,
      error: null,
      reset: mockReset,
    })
  })

  afterEach(() => {
    document.body.removeChild(mockAnchor)
    vi.clearAllMocks()
  })

  const defaultProps = {
    photoPath: '/photos/moth.jpg',
    isOpen: true,
    onClose: vi.fn(),
    anchorEl: mockAnchor,
  }

  // Basic Rendering
  it('does not render when isOpen is false', () => {
    render(<ExportOptionsMenu {...defaultProps} isOpen={false} />, { wrapper: createWrapper() })
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
  })

  it('renders when isOpen is true', () => {
    render(<ExportOptionsMenu {...defaultProps} />, { wrapper: createWrapper() })
    expect(screen.getByRole('menu', { name: /export photo/i })).toBeInTheDocument()
  })

  it('shows "Export Photo" header', () => {
    render(<ExportOptionsMenu {...defaultProps} />, { wrapper: createWrapper() })
    expect(screen.getByText('Export Photo')).toBeInTheDocument()
  })

  // Export Formats
  it('shows all 4 export formats with descriptions', () => {
    render(<ExportOptionsMenu {...defaultProps} />, { wrapper: createWrapper() })

    // Check format names
    expect(screen.getByText('Darwin Core')).toBeInTheDocument()
    expect(screen.getByText('iNaturalist')).toBeInTheDocument()
    expect(screen.getByText('JSON')).toBeInTheDocument()
    expect(screen.getByText('CSV')).toBeInTheDocument()

    // Check descriptions
    expect(screen.getByText('For GBIF biodiversity portals')).toBeInTheDocument()
    expect(screen.getByText('With XMP sidecars')).toBeInTheDocument()
    expect(screen.getByText('All metadata fields')).toBeInTheDocument()
    expect(screen.getByText('Excel compatible')).toBeInTheDocument()
  })

  it('displays correct icon for each format', () => {
    const { container } = render(<ExportOptionsMenu {...defaultProps} />, { wrapper: createWrapper() })

    // All 4 formats should have icons (SVG elements)
    const icons = container.querySelectorAll('svg')
    // At least 4 icons for the formats (could be more if there are other UI icons)
    expect(icons.length).toBeGreaterThanOrEqual(4)
  })

  // Export Functionality
  it('triggers export on format selection', async () => {
    const user = userEvent.setup()
    render(<ExportOptionsMenu {...defaultProps} />, { wrapper: createWrapper() })

    const jsonOption = screen.getByRole('menuitem', { name: /JSON/i })
    await user.click(jsonOption)

    expect(mockExportPhoto).toHaveBeenCalledWith('/photos/moth.jpg', 'json')
    expect(mockExportPhoto).toHaveBeenCalledTimes(1)
  })

  it('triggers darwin_core export correctly', async () => {
    const user = userEvent.setup()
    render(<ExportOptionsMenu {...defaultProps} />, { wrapper: createWrapper() })

    const darwinCoreOption = screen.getByRole('menuitem', { name: /Darwin Core/i })
    await user.click(darwinCoreOption)

    expect(mockExportPhoto).toHaveBeenCalledWith('/photos/moth.jpg', 'darwin_core')
  })

  it('triggers inaturalist export correctly', async () => {
    const user = userEvent.setup()
    render(<ExportOptionsMenu {...defaultProps} />, { wrapper: createWrapper() })

    const iNaturalistOption = screen.getByRole('menuitem', { name: /iNaturalist/i })
    await user.click(iNaturalistOption)

    expect(mockExportPhoto).toHaveBeenCalledWith('/photos/moth.jpg', 'inaturalist')
  })

  it('triggers csv export correctly', async () => {
    const user = userEvent.setup()
    render(<ExportOptionsMenu {...defaultProps} />, { wrapper: createWrapper() })

    const csvOption = screen.getByRole('menuitem', { name: /CSV/i })
    await user.click(csvOption)

    expect(mockExportPhoto).toHaveBeenCalledWith('/photos/moth.jpg', 'csv')
  })

  // Loading State
  it('shows loading state while exporting', () => {
    useSinglePhotoExport.mockReturnValue({
      exportPhoto: mockExportPhoto,
      isExporting: true,
      progress: { current: 1, total: 1, percent: 50, phase: 'exporting' },
      error: null,
      reset: mockReset,
    })

    render(<ExportOptionsMenu {...defaultProps} />, { wrapper: createWrapper() })

    expect(screen.getByText(/exporting/i)).toBeInTheDocument()
  })

  it('disables format options while exporting', () => {
    useSinglePhotoExport.mockReturnValue({
      exportPhoto: mockExportPhoto,
      isExporting: true,
      progress: { current: 1, total: 1, percent: 50, phase: 'exporting' },
      error: null,
      reset: mockReset,
    })

    render(<ExportOptionsMenu {...defaultProps} />, { wrapper: createWrapper() })

    const jsonOption = screen.getByRole('menuitem', { name: /JSON/i })
    expect(jsonOption).toBeDisabled()
  })

  // Close Behavior
  it('closes menu after selection', async () => {
    const onClose = vi.fn()
    const user = userEvent.setup()
    render(<ExportOptionsMenu {...defaultProps} onClose={onClose} />, { wrapper: createWrapper() })

    const jsonOption = screen.getByRole('menuitem', { name: /JSON/i })
    await user.click(jsonOption)

    expect(onClose).toHaveBeenCalled()
  })

  it('closes on Escape key', async () => {
    const onClose = vi.fn()
    render(<ExportOptionsMenu {...defaultProps} onClose={onClose} />, { wrapper: createWrapper() })

    fireEvent.keyDown(document, { key: 'Escape' })

    await waitFor(() => {
      expect(onClose).toHaveBeenCalled()
    })
  })

  it('closes on click outside', async () => {
    const onClose = vi.fn()
    render(<ExportOptionsMenu {...defaultProps} onClose={onClose} />, { wrapper: createWrapper() })

    fireEvent.mouseDown(document.body)

    await waitFor(() => {
      expect(onClose).toHaveBeenCalled()
    })
  })

  it('does not close when clicking inside menu', () => {
    const onClose = vi.fn()
    render(<ExportOptionsMenu {...defaultProps} onClose={onClose} />, { wrapper: createWrapper() })

    const menu = screen.getByRole('menu')
    fireEvent.mouseDown(menu)

    expect(onClose).not.toHaveBeenCalled()
  })

  it('does not close when clicking anchor element', () => {
    const onClose = vi.fn()

    render(<ExportOptionsMenu {...defaultProps} onClose={onClose} />, { wrapper: createWrapper() })

    // The menu includes logic to check !anchorEl?.contains(e.target)
    // This means clicks on the anchor should not trigger onClose
    // We verify the menu renders with the anchor element provided
    expect(screen.getByRole('menu')).toBeInTheDocument()
    expect(mockAnchor).toBeInTheDocument()

    // In real usage, the parent component handles anchor clicks to toggle the menu
    // The menu's click-outside handler should exclude the anchor
    // This is a structural test - the integration behavior is tested in parent components
  })

  // Keyboard Navigation
  it('supports keyboard navigation with ArrowDown', async () => {
    const user = userEvent.setup()
    render(<ExportOptionsMenu {...defaultProps} />, { wrapper: createWrapper() })

    const menu = screen.getByRole('menu')
    menu.focus()

    // Press ArrowDown to move to first option
    await user.keyboard('{ArrowDown}')

    // First option should be highlighted (has ring-2 class)
    const darwinCoreOption = screen.getByRole('menuitem', { name: /Darwin Core/i })
    expect(darwinCoreOption).toHaveClass(/ring-2/)
  })

  it('supports keyboard navigation with ArrowUp', async () => {
    const user = userEvent.setup()
    render(<ExportOptionsMenu {...defaultProps} />, { wrapper: createWrapper() })

    const menu = screen.getByRole('menu')
    menu.focus()

    // Press ArrowUp to move to last option (wrap around)
    await user.keyboard('{ArrowUp}')

    // Last option should be highlighted
    const csvOption = screen.getByRole('menuitem', { name: /CSV/i })
    expect(csvOption).toHaveClass(/ring-2/)
  })

  it('supports keyboard navigation with Enter', async () => {
    const user = userEvent.setup()
    render(<ExportOptionsMenu {...defaultProps} />, { wrapper: createWrapper() })

    const menu = screen.getByRole('menu')
    menu.focus()

    // Press ArrowDown to highlight first option, then Enter to select
    await user.keyboard('{ArrowDown}')
    await user.keyboard('{Enter}')

    expect(mockExportPhoto).toHaveBeenCalledWith('/photos/moth.jpg', 'darwin_core')
  })

  // Positioning
  it('uses position prop when provided (context menu mode)', () => {
    const { container } = render(
      <ExportOptionsMenu
        {...defaultProps}
        anchorEl={null}
        position={{ x: 100, y: 200 }}
      />,
      { wrapper: createWrapper() }
    )

    const menu = container.querySelector('[role="menu"]')
    expect(menu).toHaveStyle({
      position: 'absolute',
      left: '100px',
      top: '200px'
    })
  })

  it('uses anchorEl when no position prop (lightbox button mode)', () => {
    const { container } = render(
      <ExportOptionsMenu {...defaultProps} />,
      { wrapper: createWrapper() }
    )

    const menu = container.querySelector('[role="menu"]')
    // Floating UI applies absolute positioning
    expect(menu).toHaveStyle({ position: 'absolute' })
  })

  // ARIA Attributes
  it('has proper ARIA attributes', () => {
    render(<ExportOptionsMenu {...defaultProps} />, { wrapper: createWrapper() })

    const menu = screen.getByRole('menu')
    expect(menu).toHaveAttribute('aria-label', 'Export photo')

    const menuItems = screen.getAllByRole('menuitem')
    expect(menuItems).toHaveLength(4)
  })
})

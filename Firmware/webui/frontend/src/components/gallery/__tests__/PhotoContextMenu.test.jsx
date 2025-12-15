import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import PhotoContextMenu from '../PhotoContextMenu'

// Mock ExportOptionsMenu to simplify testing
vi.mock('../../export/ExportOptionsMenu', () => ({
  default: vi.fn(({ isOpen, photoPath, onClose }) =>
    isOpen ? (
      <div data-testid="export-options-menu" data-photo-path={photoPath}>
        Export Menu
        <button onClick={onClose}>Close Export Menu</button>
      </div>
    ) : null
  ),
}))

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return ({ children }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('PhotoContextMenu', () => {
  let mockOnClose
  const mockPhoto = {
    path: '/photos/moth_2024_01_15__10_30_00.jpg',
    filename: 'moth_2024_01_15__10_30_00.jpg',
  }
  const mockPosition = { x: 100, y: 200 }

  beforeEach(() => {
    mockOnClose = vi.fn()
  })

  describe('Rendering', () => {
    it('does not render when isOpen is false', () => {
      const { container } = render(
        <PhotoContextMenu
          photo={mockPhoto}
          isOpen={false}
          onClose={mockOnClose}
          position={mockPosition}
        />,
        { wrapper: createWrapper() }
      )

      expect(container.firstChild).toBeNull()
    })

    it('renders at provided mouse position', () => {
      const { container } = render(
        <PhotoContextMenu
          photo={mockPhoto}
          isOpen={true}
          onClose={mockOnClose}
          position={mockPosition}
        />,
        { wrapper: createWrapper() }
      )

      const menu = container.querySelector('[role="menu"]')
      expect(menu).toBeInTheDocument()
      expect(menu).toHaveStyle({
        position: 'absolute',
        left: '100px',
        top: '200px',
      })
    })

    it('has role="menu" for accessibility', () => {
      render(
        <PhotoContextMenu
          photo={mockPhoto}
          isOpen={true}
          onClose={mockOnClose}
          position={mockPosition}
        />,
        { wrapper: createWrapper() }
      )

      expect(screen.getByRole('menu')).toBeInTheDocument()
    })

    it('shows Export menu item with ArrowRightIcon indicator', () => {
      render(
        <PhotoContextMenu
          photo={mockPhoto}
          isOpen={true}
          onClose={mockOnClose}
          position={mockPosition}
        />,
        { wrapper: createWrapper() }
      )

      const exportItem = screen.getByRole('menuitem', { name: /export/i })
      expect(exportItem).toBeInTheDocument()

      // Check for arrow icon (using test ID or class check)
      const svg = exportItem.querySelector('svg')
      expect(svg).toBeInTheDocument()
    })

    it('Export item has role="menuitem"', () => {
      render(
        <PhotoContextMenu
          photo={mockPhoto}
          isOpen={true}
          onClose={mockOnClose}
          position={mockPosition}
        />,
        { wrapper: createWrapper() }
      )

      const exportItem = screen.getByRole('menuitem', { name: /export/i })
      expect(exportItem).toHaveAttribute('role', 'menuitem')
    })
  })

  describe('ExportOptionsMenu Integration', () => {
    it('opens ExportOptionsMenu on Export click', async () => {
      render(
        <PhotoContextMenu
          photo={mockPhoto}
          isOpen={true}
          onClose={mockOnClose}
          position={mockPosition}
        />,
        { wrapper: createWrapper() }
      )

      const exportItem = screen.getByRole('menuitem', { name: /export/i })
      fireEvent.click(exportItem)

      await waitFor(() => {
        expect(screen.getByTestId('export-options-menu')).toBeInTheDocument()
      })
    })

    it('opens ExportOptionsMenu on Export mouseenter (hover)', async () => {
      render(
        <PhotoContextMenu
          photo={mockPhoto}
          isOpen={true}
          onClose={mockOnClose}
          position={mockPosition}
        />,
        { wrapper: createWrapper() }
      )

      const exportItem = screen.getByRole('menuitem', { name: /export/i })
      fireEvent.mouseEnter(exportItem)

      await waitFor(() => {
        expect(screen.getByTestId('export-options-menu')).toBeInTheDocument()
      })
    })

    it('closes ExportOptionsMenu on Export mouseleave', async () => {
      render(
        <PhotoContextMenu
          photo={mockPhoto}
          isOpen={true}
          onClose={mockOnClose}
          position={mockPosition}
        />,
        { wrapper: createWrapper() }
      )

      const exportItem = screen.getByRole('menuitem', { name: /export/i })

      // Open submenu
      fireEvent.mouseEnter(exportItem)
      await waitFor(() => {
        expect(screen.getByTestId('export-options-menu')).toBeInTheDocument()
      })

      // Close submenu
      fireEvent.mouseLeave(exportItem)
      await waitFor(() => {
        expect(screen.queryByTestId('export-options-menu')).not.toBeInTheDocument()
      })
    })

    it('passes correct photo.path to ExportOptionsMenu', async () => {
      render(
        <PhotoContextMenu
          photo={mockPhoto}
          isOpen={true}
          onClose={mockOnClose}
          position={mockPosition}
        />,
        { wrapper: createWrapper() }
      )

      const exportItem = screen.getByRole('menuitem', { name: /export/i })
      fireEvent.click(exportItem)

      await waitFor(() => {
        const exportMenu = screen.getByTestId('export-options-menu')
        expect(exportMenu).toHaveAttribute('data-photo-path', mockPhoto.path)
      })
    })
  })

  describe('Keyboard Navigation', () => {
    it('closes entire menu on Escape key', async () => {
      render(
        <PhotoContextMenu
          photo={mockPhoto}
          isOpen={true}
          onClose={mockOnClose}
          position={mockPosition}
        />,
        { wrapper: createWrapper() }
      )

      fireEvent.keyDown(document, { key: 'Escape' })

      await waitFor(() => {
        expect(mockOnClose).toHaveBeenCalled()
      })
    })

    it('opens submenu on Enter key when Export is focused', async () => {
      render(
        <PhotoContextMenu
          photo={mockPhoto}
          isOpen={true}
          onClose={mockOnClose}
          position={mockPosition}
        />,
        { wrapper: createWrapper() }
      )

      const exportItem = screen.getByRole('menuitem', { name: /export/i })
      exportItem.focus()
      fireEvent.keyDown(exportItem, { key: 'Enter' })

      await waitFor(() => {
        expect(screen.getByTestId('export-options-menu')).toBeInTheDocument()
      })
    })
  })

  describe('Click Outside', () => {
    it('closes on click outside', async () => {
      render(
        <div>
          <div data-testid="outside">Outside element</div>
          <PhotoContextMenu
            photo={mockPhoto}
            isOpen={true}
            onClose={mockOnClose}
            position={mockPosition}
          />
        </div>,
        { wrapper: createWrapper() }
      )

      const outsideElement = screen.getByTestId('outside')
      fireEvent.mouseDown(outsideElement)

      await waitFor(() => {
        expect(mockOnClose).toHaveBeenCalled()
      })
    })

    it('does not close when clicking inside menu', async () => {
      render(
        <PhotoContextMenu
          photo={mockPhoto}
          isOpen={true}
          onClose={mockOnClose}
          position={mockPosition}
        />,
        { wrapper: createWrapper() }
      )

      const menu = screen.getByRole('menu')
      fireEvent.mouseDown(menu)

      // Wait a bit to ensure onClose is not called
      await new Promise((resolve) => setTimeout(resolve, 50))
      expect(mockOnClose).not.toHaveBeenCalled()
    })
  })

  describe('Viewport Edge Handling', () => {
    const originalInnerWidth = window.innerWidth
    const originalInnerHeight = window.innerHeight

    beforeEach(() => {
      // Mock window dimensions
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 1024,
      })
      Object.defineProperty(window, 'innerHeight', {
        writable: true,
        configurable: true,
        value: 768,
      })
    })

    afterEach(() => {
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: originalInnerWidth,
      })
      Object.defineProperty(window, 'innerHeight', {
        writable: true,
        configurable: true,
        value: originalInnerHeight,
      })
    })

    it('repositions if near right viewport edge (flip to left side)', () => {
      // Position near right edge (menu width ~200px, will overflow)
      const rightEdgePosition = { x: 950, y: 200 }

      const { container } = render(
        <PhotoContextMenu
          photo={mockPhoto}
          isOpen={true}
          onClose={mockOnClose}
          position={rightEdgePosition}
        />,
        { wrapper: createWrapper() }
      )

      const menu = container.querySelector('[role="menu"]')
      const leftValue = parseInt(menu.style.left)

      // Should be adjusted to prevent overflow
      expect(leftValue).toBeLessThan(rightEdgePosition.x)
    })

    it('repositions if near bottom viewport edge (flip to top)', () => {
      // Position near bottom edge (menu height ~100px, will overflow)
      const bottomEdgePosition = { x: 200, y: 700 }

      const { container } = render(
        <PhotoContextMenu
          photo={mockPhoto}
          isOpen={true}
          onClose={mockOnClose}
          position={bottomEdgePosition}
        />,
        { wrapper: createWrapper() }
      )

      const menu = container.querySelector('[role="menu"]')
      const topValue = parseInt(menu.style.top)

      // Should be adjusted to prevent overflow
      expect(topValue).toBeLessThan(bottomEdgePosition.y)
    })
  })

  describe('Submenu Closing', () => {
    it('closes submenu when parent menu closes', async () => {
      const { rerender } = render(
        <PhotoContextMenu
          photo={mockPhoto}
          isOpen={true}
          onClose={mockOnClose}
          position={mockPosition}
        />,
        { wrapper: createWrapper() }
      )

      // Open submenu
      const exportItem = screen.getByRole('menuitem', { name: /export/i })
      fireEvent.click(exportItem)

      await waitFor(() => {
        expect(screen.getByTestId('export-options-menu')).toBeInTheDocument()
      })

      // Close parent menu
      rerender(
        <PhotoContextMenu
          photo={mockPhoto}
          isOpen={false}
          onClose={mockOnClose}
          position={mockPosition}
        />
      )

      expect(screen.queryByTestId('export-options-menu')).not.toBeInTheDocument()
    })
  })
})

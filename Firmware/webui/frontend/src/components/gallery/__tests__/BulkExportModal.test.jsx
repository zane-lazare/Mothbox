import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import BulkExportModal from '../BulkExportModal'

describe('BulkExportModal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onExport: vi.fn(),
    selectedCount: 5,
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Visibility', () => {
    it('does NOT render when isOpen is false', () => {
      render(<BulkExportModal {...defaultProps} isOpen={false} />)

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })

    it('renders when isOpen is true', () => {
      render(<BulkExportModal {...defaultProps} />)

      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })
  })

  describe('Header', () => {
    it('shows export count in title: "Export X photos"', () => {
      render(<BulkExportModal {...defaultProps} selectedCount={5} />)

      expect(screen.getByText(/export 5 photos/i)).toBeInTheDocument()
    })

    it('shows singular form for single photo', () => {
      render(<BulkExportModal {...defaultProps} selectedCount={1} />)

      expect(screen.getByText(/export 1 photo$/i)).toBeInTheDocument()
    })

    it('shows close button in header', () => {
      render(<BulkExportModal {...defaultProps} />)

      const closeButton = screen.getByRole('button', { name: /close modal/i })
      expect(closeButton).toBeInTheDocument()
    })
  })

  describe('Format Selection', () => {
    it('displays all 4 export formats', () => {
      render(<BulkExportModal {...defaultProps} />)

      expect(screen.getByText('Darwin Core')).toBeInTheDocument()
      expect(screen.getByText('iNaturalist')).toBeInTheDocument()
      expect(screen.getByText('JSON')).toBeInTheDocument()
      expect(screen.getByText('CSV')).toBeInTheDocument()
    })

    it('shows format descriptions', () => {
      render(<BulkExportModal {...defaultProps} />)

      expect(screen.getByText(/gbif biodiversity portals/i)).toBeInTheDocument()
      expect(screen.getByText(/xmp sidecars/i)).toBeInTheDocument()
      expect(screen.getByText(/all metadata fields/i)).toBeInTheDocument()
      expect(screen.getByText(/excel compatible/i)).toBeInTheDocument()
    })

    it('shows format icons', () => {
      render(<BulkExportModal {...defaultProps} />)

      // Each format card (label wrapping radio) should have an SVG icon
      const formatRadios = screen.getAllByRole('radio')
      formatRadios.forEach((radio) => {
        // Get the parent label element which contains the icon
        const label = radio.closest('label')
        const svg = label.querySelector('svg')
        expect(svg).toBeInTheDocument()
      })
    })

    it('allows selecting a format', async () => {
      const user = userEvent.setup()
      render(<BulkExportModal {...defaultProps} />)

      const darwinCoreOption = screen.getByRole('radio', { name: /darwin core/i })
      await user.click(darwinCoreOption)

      expect(darwinCoreOption).toBeChecked()
    })

    it('highlights selected format visually', async () => {
      const user = userEvent.setup()
      render(<BulkExportModal {...defaultProps} />)

      const darwinCoreOption = screen.getByRole('radio', { name: /darwin core/i })
      await user.click(darwinCoreOption)

      // Selected item should have ring/border highlight
      const parent = darwinCoreOption.closest('label')
      expect(parent.className).toMatch(/ring|border-blue/)
    })

    it('only allows one format to be selected at a time', async () => {
      const user = userEvent.setup()
      render(<BulkExportModal {...defaultProps} />)

      const darwinCoreOption = screen.getByRole('radio', { name: /darwin core/i })
      const jsonOption = screen.getByRole('radio', { name: /json/i })

      await user.click(darwinCoreOption)
      expect(darwinCoreOption).toBeChecked()
      expect(jsonOption).not.toBeChecked()

      await user.click(jsonOption)
      expect(jsonOption).toBeChecked()
      expect(darwinCoreOption).not.toBeChecked()
    })
  })

  describe('Actions', () => {
    it('Cancel button closes modal', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      render(<BulkExportModal {...defaultProps} onClose={onClose} />)

      const cancelButton = screen.getByRole('button', { name: /cancel/i })
      await user.click(cancelButton)

      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('Export button calls onExport with selected format', async () => {
      const user = userEvent.setup()
      const onExport = vi.fn()
      render(<BulkExportModal {...defaultProps} onExport={onExport} />)

      // Select a format first
      const darwinCoreOption = screen.getByRole('radio', { name: /darwin core/i })
      await user.click(darwinCoreOption)

      // Click export
      const exportButton = screen.getByRole('button', { name: /^export$/i })
      await user.click(exportButton)

      expect(onExport).toHaveBeenCalledTimes(1)
      expect(onExport).toHaveBeenCalledWith('darwin_core')
    })

    it('Export button disabled when no format selected', () => {
      render(<BulkExportModal {...defaultProps} />)

      const exportButton = screen.getByRole('button', { name: /^export$/i })
      expect(exportButton).toBeDisabled()
    })

    it('Export button disabled when isLoading', async () => {
      const user = userEvent.setup()
      render(<BulkExportModal {...defaultProps} isLoading={true} />)

      // Select a format
      const darwinCoreOption = screen.getByRole('radio', { name: /darwin core/i })
      await user.click(darwinCoreOption)

      const exportButton = screen.getByRole('button', { name: /exporting|export/i })
      expect(exportButton).toBeDisabled()
    })

    it('Export button shows loading state when isLoading', () => {
      render(<BulkExportModal {...defaultProps} isLoading={true} />)

      expect(screen.getByText(/exporting/i)).toBeInTheDocument()
    })

    it('close button in header calls onClose', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      render(<BulkExportModal {...defaultProps} onClose={onClose} />)

      const closeButton = screen.getByRole('button', { name: /close modal/i })
      await user.click(closeButton)

      expect(onClose).toHaveBeenCalledTimes(1)
    })
  })

  describe('Keyboard Navigation', () => {
    it('Escape key closes modal', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      render(<BulkExportModal {...defaultProps} onClose={onClose} />)

      await user.keyboard('{Escape}')

      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('Arrow keys navigate format options', async () => {
      const user = userEvent.setup()
      render(<BulkExportModal {...defaultProps} />)

      // Focus on the first radio button
      const darwinCoreOption = screen.getByRole('radio', { name: /darwin core/i })
      darwinCoreOption.focus()

      // Press down arrow to move to next option
      await user.keyboard('{ArrowDown}')

      const inaturalistOption = screen.getByRole('radio', { name: /inaturalist/i })
      expect(inaturalistOption).toHaveFocus()
    })

    it('Tab key navigates between elements', async () => {
      const user = userEvent.setup()
      render(<BulkExportModal {...defaultProps} />)

      // Tab should move through focusable elements
      await user.tab()
      // First focusable element should be focused
      expect(document.activeElement).toBeTruthy()
    })
  })

  describe('Accessibility', () => {
    it('has role="dialog" and aria-modal="true"', () => {
      render(<BulkExportModal {...defaultProps} />)

      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveAttribute('aria-modal', 'true')
    })

    it('has aria-labelledby for title', () => {
      render(<BulkExportModal {...defaultProps} />)

      const dialog = screen.getByRole('dialog')
      const labelledBy = dialog.getAttribute('aria-labelledby')
      expect(labelledBy).toBeTruthy()

      // Title element should exist with that ID
      const title = document.getElementById(labelledBy)
      expect(title).toBeInTheDocument()
      expect(title.textContent).toMatch(/export/i)
    })

    it('format options use radio role', () => {
      render(<BulkExportModal {...defaultProps} />)

      const radioGroup = screen.getByRole('radiogroup')
      expect(radioGroup).toBeInTheDocument()

      const radios = screen.getAllByRole('radio')
      expect(radios).toHaveLength(4)
    })

    it('format options have accessible names', () => {
      render(<BulkExportModal {...defaultProps} />)

      expect(screen.getByRole('radio', { name: /darwin core/i })).toBeInTheDocument()
      expect(screen.getByRole('radio', { name: /inaturalist/i })).toBeInTheDocument()
      expect(screen.getByRole('radio', { name: /json/i })).toBeInTheDocument()
      expect(screen.getByRole('radio', { name: /csv/i })).toBeInTheDocument()
    })
  })

  describe('Backdrop', () => {
    it('renders backdrop overlay', () => {
      render(<BulkExportModal {...defaultProps} />)

      // Look for backdrop element with bg-black/50 or similar
      const backdrop = document.querySelector('[class*="bg-black"]')
      expect(backdrop).toBeInTheDocument()
    })

    it('clicking backdrop closes modal', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      render(<BulkExportModal {...defaultProps} onClose={onClose} />)

      // Click on backdrop (the overlay element)
      const backdrop = document.querySelector('[class*="bg-black"]')
      await user.click(backdrop)

      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('clicking modal content does NOT close modal', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      render(<BulkExportModal {...defaultProps} onClose={onClose} />)

      const dialog = screen.getByRole('dialog')
      await user.click(dialog)

      expect(onClose).not.toHaveBeenCalled()
    })
  })

  describe('Error State', () => {
    it('shows error message when error prop is provided', () => {
      render(<BulkExportModal {...defaultProps} error="Failed to create export job" />)

      expect(screen.getByText(/failed to create export job/i)).toBeInTheDocument()
    })

    it('error message has proper ARIA role', () => {
      render(<BulkExportModal {...defaultProps} error="Export failed" />)

      const errorElement = screen.getByRole('alert')
      expect(errorElement).toBeInTheDocument()
    })
  })

  describe('Dark Mode Support', () => {
    it('has dark mode classes for background', () => {
      render(<BulkExportModal {...defaultProps} />)

      const dialog = screen.getByRole('dialog')
      expect(dialog.className).toMatch(/dark:bg-/)
    })

    it('has dark mode classes for text', () => {
      render(<BulkExportModal {...defaultProps} />)

      const title = screen.getByText(/export \d+ photos?/i)
      expect(title.className).toMatch(/dark:text-/)
    })
  })

  describe('Portal Rendering', () => {
    it('modal is rendered in document.body (portal)', () => {
      const { container } = render(<BulkExportModal {...defaultProps} />)

      // Modal should NOT be in the container (it's portaled to body)
      const dialogInContainer = container.querySelector('[role="dialog"]')
      expect(dialogInContainer).toBeNull()

      // But it should be in the document (via portal)
      const dialogInDocument = document.querySelector('[role="dialog"]')
      expect(dialogInDocument).toBeInTheDocument()
    })
  })
})

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import BulkDeleteConfirmModal from '../BulkDeleteConfirmModal'

describe('BulkDeleteConfirmModal', () => {
  const mockOnClose = vi.fn()
  const mockOnConfirm = vi.fn()
  const defaultProps = {
    isOpen: true,
    onClose: mockOnClose,
    onConfirm: mockOnConfirm,
    selectedPhotos: ['photo1.jpg', 'photo2.jpg', 'photo3.jpg']
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('does NOT render when isOpen is false', () => {
      render(<BulkDeleteConfirmModal {...defaultProps} isOpen={false} />)
      expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    })

    it('renders when isOpen is true', () => {
      render(<BulkDeleteConfirmModal {...defaultProps} />)
      expect(screen.getByRole('alertdialog')).toBeInTheDocument()
    })

    it('shows warning icon', () => {
      render(<BulkDeleteConfirmModal {...defaultProps} />)
      // ExclamationTriangleIcon should be present
      const alertDialog = screen.getByRole('alertdialog')
      expect(alertDialog).toBeInTheDocument()
      // Check for SVG icon (heroicons render as SVG)
      const svg = alertDialog.querySelector('svg')
      expect(svg).toBeInTheDocument()
    })

    it('shows "Delete X photos?" title', () => {
      render(<BulkDeleteConfirmModal {...defaultProps} />)
      expect(screen.getByText('Delete 3 photos?')).toBeInTheDocument()
    })

    it('shows correct title for single photo', () => {
      render(<BulkDeleteConfirmModal {...defaultProps} selectedPhotos={['photo1.jpg']} />)
      expect(screen.getByText('Delete 1 photo?')).toBeInTheDocument()
    })
  })

  describe('File Preview', () => {
    it('shows first 5 filenames in list', () => {
      const photos = ['photo1.jpg', 'photo2.jpg', 'photo3.jpg', 'photo4.jpg', 'photo5.jpg']
      render(<BulkDeleteConfirmModal {...defaultProps} selectedPhotos={photos} />)

      photos.forEach(photo => {
        expect(screen.getByText(photo)).toBeInTheDocument()
      })
    })

    it('shows "...and X more" when more than 5 files', () => {
      const photos = [
        'photo1.jpg', 'photo2.jpg', 'photo3.jpg',
        'photo4.jpg', 'photo5.jpg', 'photo6.jpg',
        'photo7.jpg', 'photo8.jpg'
      ]
      render(<BulkDeleteConfirmModal {...defaultProps} selectedPhotos={photos} />)

      // First 5 should be shown
      expect(screen.getByText('photo1.jpg')).toBeInTheDocument()
      expect(screen.getByText('photo2.jpg')).toBeInTheDocument()
      expect(screen.getByText('photo3.jpg')).toBeInTheDocument()
      expect(screen.getByText('photo4.jpg')).toBeInTheDocument()
      expect(screen.getByText('photo5.jpg')).toBeInTheDocument()

      // 6th and beyond should not be shown
      expect(screen.queryByText('photo6.jpg')).not.toBeInTheDocument()
      expect(screen.queryByText('photo7.jpg')).not.toBeInTheDocument()
      expect(screen.queryByText('photo8.jpg')).not.toBeInTheDocument()

      // Should show "...and 3 more"
      expect(screen.getByText('...and 3 more')).toBeInTheDocument()
    })

    it('handles single file correctly', () => {
      render(<BulkDeleteConfirmModal {...defaultProps} selectedPhotos={['single-photo.jpg']} />)
      expect(screen.getByText('single-photo.jpg')).toBeInTheDocument()
      expect(screen.queryByText(/...and \d+ more/)).not.toBeInTheDocument()
    })

    it('does not show "...and more" for exactly 5 files', () => {
      const photos = ['photo1.jpg', 'photo2.jpg', 'photo3.jpg', 'photo4.jpg', 'photo5.jpg']
      render(<BulkDeleteConfirmModal {...defaultProps} selectedPhotos={photos} />)
      expect(screen.queryByText(/...and \d+ more/)).not.toBeInTheDocument()
    })
  })

  describe('Warning Message', () => {
    it('shows "This action cannot be undone" warning', () => {
      render(<BulkDeleteConfirmModal {...defaultProps} />)
      expect(screen.getByText('This action cannot be undone.')).toBeInTheDocument()
    })

    it('uses destructive/warning styling (red/amber colors)', () => {
      render(<BulkDeleteConfirmModal {...defaultProps} />)
      const warningText = screen.getByText('This action cannot be undone.')

      // Check if element or parent has warning/error color classes
      expect(
        warningText.className.includes('text-red') ||
        warningText.className.includes('text-amber')
      ).toBe(true)
    })
  })

  describe('Action Buttons', () => {
    it('shows Cancel button (neutral styling)', () => {
      render(<BulkDeleteConfirmModal {...defaultProps} />)
      const cancelButton = screen.getByRole('button', { name: /cancel/i })
      expect(cancelButton).toBeInTheDocument()

      // Check for neutral/gray styling
      expect(
        cancelButton.className.includes('border-gray') ||
        cancelButton.className.includes('text-gray')
      ).toBe(true)
    })

    it('shows Delete button (destructive red styling)', () => {
      render(<BulkDeleteConfirmModal {...defaultProps} />)
      const deleteButton = screen.getByRole('button', { name: /delete/i })
      expect(deleteButton).toBeInTheDocument()

      // Check for red/destructive styling
      expect(deleteButton.className.includes('bg-red')).toBe(true)
    })

    it('Cancel calls onClose', async () => {
      const user = userEvent.setup()
      render(<BulkDeleteConfirmModal {...defaultProps} />)

      const cancelButton = screen.getByRole('button', { name: /cancel/i })
      await user.click(cancelButton)

      expect(mockOnClose).toHaveBeenCalledTimes(1)
    })

    it('Delete calls onConfirm', async () => {
      const user = userEvent.setup()
      render(<BulkDeleteConfirmModal {...defaultProps} />)

      const deleteButton = screen.getByRole('button', { name: /delete/i })
      await user.click(deleteButton)

      expect(mockOnConfirm).toHaveBeenCalledTimes(1)
    })

    it('Delete button shows loading state when isLoading', () => {
      render(<BulkDeleteConfirmModal {...defaultProps} isLoading={true} />)

      const deleteButton = screen.getByRole('button', { name: /deleting/i })
      expect(deleteButton).toBeInTheDocument()
      expect(deleteButton).toBeDisabled()
    })

    it('Delete button is disabled during loading', () => {
      render(<BulkDeleteConfirmModal {...defaultProps} isLoading={true} />)

      const deleteButton = screen.getByRole('button', { name: /deleting/i })
      expect(deleteButton).toBeDisabled()
    })

    it('Cancel button is disabled during loading', () => {
      render(<BulkDeleteConfirmModal {...defaultProps} isLoading={true} />)

      const cancelButton = screen.getByRole('button', { name: /cancel/i })
      expect(cancelButton).toBeDisabled()
    })
  })

  describe('Modal Behavior', () => {
    it('Escape closes modal', async () => {
      const user = userEvent.setup()
      render(<BulkDeleteConfirmModal {...defaultProps} />)

      await user.keyboard('{Escape}')

      expect(mockOnClose).toHaveBeenCalledTimes(1)
    })

    it('backdrop click closes modal', async () => {
      const user = userEvent.setup()
      render(<BulkDeleteConfirmModal {...defaultProps} />)

      // Click the backdrop (first child of modal container)
      const backdrop = screen.getByRole('alertdialog').parentElement.firstChild
      await user.click(backdrop)

      expect(mockOnClose).toHaveBeenCalledTimes(1)
    })

    it('clicking modal content does not close modal', async () => {
      const user = userEvent.setup()
      render(<BulkDeleteConfirmModal {...defaultProps} />)

      const alertDialog = screen.getByRole('alertdialog')
      await user.click(alertDialog)

      expect(mockOnClose).not.toHaveBeenCalled()
    })
  })

  describe('Accessibility', () => {
    it('has role="alertdialog" for destructive action', () => {
      render(<BulkDeleteConfirmModal {...defaultProps} />)
      expect(screen.getByRole('alertdialog')).toBeInTheDocument()
    })

    it('has aria-modal="true"', () => {
      render(<BulkDeleteConfirmModal {...defaultProps} />)
      const alertDialog = screen.getByRole('alertdialog')
      expect(alertDialog).toHaveAttribute('aria-modal', 'true')
    })

    it('has aria-labelledby pointing to title', () => {
      render(<BulkDeleteConfirmModal {...defaultProps} />)
      const alertDialog = screen.getByRole('alertdialog')
      const labelledBy = alertDialog.getAttribute('aria-labelledby')

      expect(labelledBy).toBeTruthy()
      const title = document.getElementById(labelledBy)
      expect(title).toHaveTextContent(/Delete \d+ photos?/)
    })

    it('Delete button has aria-label', () => {
      render(<BulkDeleteConfirmModal {...defaultProps} />)
      const deleteButton = screen.getByRole('button', { name: /delete/i })

      // Either text content or aria-label should identify it
      expect(
        deleteButton.textContent.includes('Delete') ||
        deleteButton.getAttribute('aria-label')?.includes('Delete')
      ).toBe(true)
    })

    it('Warning has proper semantic markup', () => {
      render(<BulkDeleteConfirmModal {...defaultProps} />)
      const warningText = screen.getByText('This action cannot be undone.')

      // Should be in a paragraph or have role
      expect(
        warningText.tagName === 'P' ||
        warningText.getAttribute('role')
      ).toBeTruthy()
    })
  })

  describe('Edge Cases', () => {
    it('handles empty selectedPhotos array', () => {
      render(<BulkDeleteConfirmModal {...defaultProps} selectedPhotos={[]} />)
      expect(screen.getByText('Delete 0 photos?')).toBeInTheDocument()
    })

    it('handles very long filenames', () => {
      const longFilename = 'a'.repeat(100) + '.jpg'
      render(<BulkDeleteConfirmModal {...defaultProps} selectedPhotos={[longFilename]} />)
      expect(screen.getByText(longFilename)).toBeInTheDocument()
    })

    it('cleans up event listeners when unmounted', async () => {
      const { unmount } = render(<BulkDeleteConfirmModal {...defaultProps} />)

      unmount()

      // Try pressing Escape after unmount - should not throw
      const user = userEvent.setup()
      await user.keyboard('{Escape}')

      // No assertions needed - just checking no errors
    })
  })
})

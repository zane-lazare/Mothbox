import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ConfirmDialog from '../ConfirmDialog'

describe('ConfirmDialog', () => {
  const mockOnClose = vi.fn()
  const mockOnConfirm = vi.fn()
  const defaultProps = {
    isOpen: true,
    onClose: mockOnClose,
    onConfirm: mockOnConfirm,
    title: 'Confirm Action',
    message: 'Are you sure you want to proceed?'
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('does NOT render when isOpen is false', () => {
      render(<ConfirmDialog {...defaultProps} isOpen={false} />)
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })

    it('renders when isOpen is true', () => {
      render(<ConfirmDialog {...defaultProps} />)
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    it('displays the title', () => {
      render(<ConfirmDialog {...defaultProps} />)
      expect(screen.getByText('Confirm Action')).toBeInTheDocument()
    })

    it('displays the message', () => {
      render(<ConfirmDialog {...defaultProps} />)
      expect(screen.getByText('Are you sure you want to proceed?')).toBeInTheDocument()
    })

    it('uses default button labels', () => {
      render(<ConfirmDialog {...defaultProps} />)
      expect(screen.getByRole('button', { name: /confirm/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
    })

    it('uses custom button labels', () => {
      render(
        <ConfirmDialog
          {...defaultProps}
          confirmLabel="Yes, delete"
          cancelLabel="No, keep it"
        />
      )
      expect(screen.getByRole('button', { name: /yes, delete/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /no, keep it/i })).toBeInTheDocument()
    })
  })

  describe('Variants', () => {
    it('default variant uses dialog role', () => {
      render(<ConfirmDialog {...defaultProps} variant="default" />)
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    it('danger variant uses alertdialog role', () => {
      render(<ConfirmDialog {...defaultProps} variant="danger" />)
      expect(screen.getByRole('alertdialog')).toBeInTheDocument()
    })

    it('danger variant shows warning icon', () => {
      render(<ConfirmDialog {...defaultProps} variant="danger" />)
      const modal = screen.getByRole('alertdialog')
      const svg = modal.querySelector('svg')
      expect(svg).toBeInTheDocument()
    })

    it('warning variant shows warning icon', () => {
      render(<ConfirmDialog {...defaultProps} variant="warning" />)
      const modal = screen.getByRole('dialog')
      const svg = modal.querySelector('svg')
      expect(svg).toBeInTheDocument()
    })

    it('default variant does not show warning icon', () => {
      render(<ConfirmDialog {...defaultProps} variant="default" />)
      const modal = screen.getByRole('dialog')
      const svg = modal.querySelector('svg')
      expect(svg).not.toBeInTheDocument()
    })

    it('danger variant has red confirm button', () => {
      render(<ConfirmDialog {...defaultProps} variant="danger" />)
      const confirmButton = screen.getByRole('button', { name: /confirm/i })
      expect(confirmButton.className).toContain('bg-red')
    })

    it('warning variant has amber confirm button', () => {
      render(<ConfirmDialog {...defaultProps} variant="warning" />)
      const confirmButton = screen.getByRole('button', { name: /confirm/i })
      expect(confirmButton.className).toContain('bg-amber')
    })

    it('default variant has blue confirm button', () => {
      render(<ConfirmDialog {...defaultProps} variant="default" />)
      const confirmButton = screen.getByRole('button', { name: /confirm/i })
      expect(confirmButton.className).toContain('bg-blue')
    })
  })

  describe('User Interactions', () => {
    it('Cancel button calls onClose', async () => {
      const user = userEvent.setup()
      render(<ConfirmDialog {...defaultProps} />)

      await user.click(screen.getByRole('button', { name: /cancel/i }))

      expect(mockOnClose).toHaveBeenCalledTimes(1)
      expect(mockOnConfirm).not.toHaveBeenCalled()
    })

    it('Confirm button calls onConfirm', async () => {
      const user = userEvent.setup()
      render(<ConfirmDialog {...defaultProps} />)

      await user.click(screen.getByRole('button', { name: /confirm/i }))

      expect(mockOnConfirm).toHaveBeenCalledTimes(1)
    })

    it('Escape key closes dialog', async () => {
      const user = userEvent.setup()
      render(<ConfirmDialog {...defaultProps} />)

      await user.keyboard('{Escape}')

      expect(mockOnClose).toHaveBeenCalledTimes(1)
    })

    it('backdrop click closes dialog', async () => {
      const user = userEvent.setup()
      render(<ConfirmDialog {...defaultProps} />)

      const backdrop = screen.getByTestId('confirm-dialog-backdrop')
      await user.click(backdrop)

      expect(mockOnClose).toHaveBeenCalledTimes(1)
    })

    it('clicking modal content does not close dialog', async () => {
      const user = userEvent.setup()
      render(<ConfirmDialog {...defaultProps} />)

      const dialog = screen.getByRole('dialog')
      await user.click(dialog)

      expect(mockOnClose).not.toHaveBeenCalled()
    })
  })

  describe('Loading State', () => {
    it('shows loading text on confirm button when isLoading', () => {
      render(<ConfirmDialog {...defaultProps} isLoading={true} />)
      expect(screen.getByRole('button', { name: /loading/i })).toBeInTheDocument()
    })

    it('disables confirm button when isLoading', () => {
      render(<ConfirmDialog {...defaultProps} isLoading={true} />)
      const confirmButton = screen.getByRole('button', { name: /loading/i })
      expect(confirmButton).toBeDisabled()
    })

    it('disables cancel button when isLoading', () => {
      render(<ConfirmDialog {...defaultProps} isLoading={true} />)
      const cancelButton = screen.getByRole('button', { name: /cancel/i })
      expect(cancelButton).toBeDisabled()
    })

    it('Escape key does not close when isLoading', async () => {
      const user = userEvent.setup()
      render(<ConfirmDialog {...defaultProps} isLoading={true} />)

      await user.keyboard('{Escape}')

      expect(mockOnClose).not.toHaveBeenCalled()
    })

    it('backdrop click does not close when isLoading', async () => {
      const user = userEvent.setup()
      render(<ConfirmDialog {...defaultProps} isLoading={true} />)

      const backdrop = screen.getByTestId('confirm-dialog-backdrop')
      await user.click(backdrop)

      expect(mockOnClose).not.toHaveBeenCalled()
    })
  })

  describe('Accessibility', () => {
    it('has aria-modal="true"', () => {
      render(<ConfirmDialog {...defaultProps} />)
      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveAttribute('aria-modal', 'true')
    })

    it('has aria-labelledby pointing to title', () => {
      render(<ConfirmDialog {...defaultProps} />)
      const dialog = screen.getByRole('dialog')
      const labelledBy = dialog.getAttribute('aria-labelledby')

      expect(labelledBy).toBeTruthy()
      const title = document.getElementById(labelledBy)
      expect(title).toHaveTextContent('Confirm Action')
    })

    it('has aria-describedby pointing to message', () => {
      render(<ConfirmDialog {...defaultProps} />)
      const dialog = screen.getByRole('dialog')
      const describedBy = dialog.getAttribute('aria-describedby')

      expect(describedBy).toBeTruthy()
      const message = document.getElementById(describedBy)
      expect(message).toHaveTextContent('Are you sure you want to proceed?')
    })

    it('focuses confirm button on open', () => {
      render(<ConfirmDialog {...defaultProps} />)
      const confirmButton = screen.getByRole('button', { name: /confirm/i })
      expect(document.activeElement).toBe(confirmButton)
    })

    it('warning icon has aria-hidden', () => {
      render(<ConfirmDialog {...defaultProps} variant="danger" />)
      const modal = screen.getByRole('alertdialog')
      const svg = modal.querySelector('svg')
      expect(svg).toHaveAttribute('aria-hidden', 'true')
    })
  })

  describe('Edge Cases', () => {
    it('handles empty title', () => {
      render(<ConfirmDialog {...defaultProps} title="" />)
      // Should still render without crashing
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    it('handles empty message', () => {
      render(<ConfirmDialog {...defaultProps} message="" />)
      // Should still render without crashing
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    it('handles long title text', () => {
      const longTitle = 'A'.repeat(200)
      render(<ConfirmDialog {...defaultProps} title={longTitle} />)
      expect(screen.getByText(longTitle)).toBeInTheDocument()
    })

    it('handles long message text', () => {
      const longMessage = 'B'.repeat(500)
      render(<ConfirmDialog {...defaultProps} message={longMessage} />)
      expect(screen.getByText(longMessage)).toBeInTheDocument()
    })

    it('cleans up event listeners when unmounted', async () => {
      const { unmount } = render(<ConfirmDialog {...defaultProps} />)

      unmount()

      // Try pressing Escape after unmount - should not throw
      const user = userEvent.setup()
      await user.keyboard('{Escape}')

      // Component unmounted successfully without errors
      expect(mockOnClose).not.toHaveBeenCalled()
    })

    it('cleans up event listeners when isOpen changes to false', async () => {
      const { rerender } = render(<ConfirmDialog {...defaultProps} />)

      // Close the dialog
      rerender(<ConfirmDialog {...defaultProps} isOpen={false} />)

      // Try pressing Escape after close - should not call onClose
      const user = userEvent.setup()
      await user.keyboard('{Escape}')

      expect(mockOnClose).not.toHaveBeenCalled()
    })
  })
})

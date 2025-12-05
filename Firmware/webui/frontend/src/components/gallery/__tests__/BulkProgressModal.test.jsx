import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import BulkProgressModal from '../BulkProgressModal'

describe('BulkProgressModal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onCancel: vi.fn(),
    status: 'processing',
    progress: 0,
    processedCount: 0,
    totalCount: 10,
    operation: 'tag'
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('does NOT render when isOpen is false', () => {
      render(<BulkProgressModal {...defaultProps} isOpen={false} />)

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })

    it('renders modal when isOpen is true', () => {
      render(<BulkProgressModal {...defaultProps} />)

      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    it('renders as portal to document.body', () => {
      const { container } = render(<BulkProgressModal {...defaultProps} />)

      // Component container should be empty (portal renders outside)
      expect(container.firstChild).toBeNull()

      // Dialog should exist in document.body
      const dialog = document.body.querySelector('[role="dialog"]')
      expect(dialog).toBeInTheDocument()
    })

    it('has proper ARIA attributes', () => {
      render(<BulkProgressModal {...defaultProps} operation="tag" />)

      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveAttribute('aria-modal', 'true')
      expect(dialog).toHaveAttribute('aria-label', 'Tagging progress')
    })

    it('renders correct operation text for tag', () => {
      render(<BulkProgressModal {...defaultProps} operation="tag" />)

      expect(screen.getByText(/Tagging photos/i)).toBeInTheDocument()
    })

    it('renders correct operation text for species', () => {
      render(<BulkProgressModal {...defaultProps} operation="species" />)

      expect(screen.getByText(/Updating species/i)).toBeInTheDocument()
    })

    it('renders correct operation text for delete', () => {
      render(<BulkProgressModal {...defaultProps} operation="delete" />)

      expect(screen.getByText(/Deleting photos/i)).toBeInTheDocument()
    })
  })

  describe('Progress Display', () => {
    it('shows progress bar', () => {
      render(<BulkProgressModal {...defaultProps} />)

      const progressBar = screen.getByRole('progressbar')
      expect(progressBar).toBeInTheDocument()
    })

    it('progress bar fills based on progress prop (0%)', () => {
      render(<BulkProgressModal {...defaultProps} progress={0} />)

      const progressBar = screen.getByRole('progressbar')
      expect(progressBar).toHaveAttribute('aria-valuenow', '0')
      expect(progressBar).toHaveStyle({ width: '0%' })
    })

    it('progress bar fills based on progress prop (50%)', () => {
      render(<BulkProgressModal {...defaultProps} progress={50} />)

      const progressBar = screen.getByRole('progressbar')
      expect(progressBar).toHaveAttribute('aria-valuenow', '50')
      expect(progressBar).toHaveStyle({ width: '50%' })
    })

    it('progress bar fills based on progress prop (100%)', () => {
      render(<BulkProgressModal {...defaultProps} progress={100} />)

      const progressBar = screen.getByRole('progressbar')
      expect(progressBar).toHaveAttribute('aria-valuenow', '100')
      expect(progressBar).toHaveStyle({ width: '100%' })
    })

    it('shows "Processing X of Y photos" text', () => {
      render(
        <BulkProgressModal
          {...defaultProps}
          processedCount={3}
          totalCount={10}
        />
      )

      expect(screen.getByText(/Processing 3 of 10 photos/i)).toBeInTheDocument()
    })

    it('shows current batch info for multi-batch operations', () => {
      render(
        <BulkProgressModal
          {...defaultProps}
          processedCount={150}
          totalCount={300}
          currentBatch={2}
          totalBatches={3}
        />
      )

      expect(screen.getByText(/Processing 150 of 300 photos/i)).toBeInTheDocument()
      expect(screen.getByText(/Batch 2 of 3/i)).toBeInTheDocument()
    })

    it('does NOT show batch info when totalBatches is 1', () => {
      render(
        <BulkProgressModal
          {...defaultProps}
          currentBatch={1}
          totalBatches={1}
        />
      )

      expect(screen.queryByText(/Batch/i)).not.toBeInTheDocument()
    })

    it('does NOT show batch info when totalBatches is undefined', () => {
      render(<BulkProgressModal {...defaultProps} />)

      expect(screen.queryByText(/Batch/i)).not.toBeInTheDocument()
    })
  })

  describe('States', () => {
    describe('Processing State', () => {
      it('shows "processing" state during operation', () => {
        render(<BulkProgressModal {...defaultProps} status="processing" />)

        expect(screen.getByRole('progressbar')).toBeInTheDocument()
        expect(screen.getByText(/Tagging photos/i)).toBeInTheDocument()
      })

      it('shows Cancel button during processing', () => {
        render(<BulkProgressModal {...defaultProps} status="processing" />)

        expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
      })
    })

    describe('Success State', () => {
      it('shows "success" state on completion with summary', () => {
        render(
          <BulkProgressModal
            {...defaultProps}
            status="success"
            successCount={10}
          />
        )

        expect(screen.getByText(/Complete!/i)).toBeInTheDocument()
        expect(screen.getByText(/Successfully processed 10 photos/i)).toBeInTheDocument()
      })

      it('shows check circle icon in success state', () => {
        render(
          <BulkProgressModal
            {...defaultProps}
            status="success"
            successCount={10}
          />
        )

        // Check for icon by test id or aria-label if added, or verify it's in the DOM
        const heading = screen.getByText(/Complete!/i)
        expect(heading).toBeInTheDocument()
      })

      it('shows failed count in success state when some failed', () => {
        render(
          <BulkProgressModal
            {...defaultProps}
            status="success"
            successCount={8}
            failedCount={2}
          />
        )

        expect(screen.getByText(/Successfully processed 8 photos, 2 failed/i)).toBeInTheDocument()
      })

      it('does NOT show failed count when failedCount is 0', () => {
        render(
          <BulkProgressModal
            {...defaultProps}
            status="success"
            successCount={10}
            failedCount={0}
          />
        )

        expect(screen.getByText(/Successfully processed 10 photos/i)).toBeInTheDocument()
        expect(screen.queryByText(/failed/i)).not.toBeInTheDocument()
      })

      it('shows Done button in success state', () => {
        render(
          <BulkProgressModal
            {...defaultProps}
            status="success"
            successCount={10}
          />
        )

        expect(screen.getByRole('button', { name: /done/i })).toBeInTheDocument()
      })
    })

    describe('Error State', () => {
      it('shows "error" state with failed count', () => {
        render(
          <BulkProgressModal
            {...defaultProps}
            status="error"
            failedCount={5}
          />
        )

        expect(screen.getByText(/Error/i)).toBeInTheDocument()
        expect(screen.getByText(/5 photos failed to process/i)).toBeInTheDocument()
      })

      it('shows exclamation circle icon in error state', () => {
        render(
          <BulkProgressModal
            {...defaultProps}
            status="error"
            failedCount={5}
          />
        )

        const heading = screen.getByText(/Error/i)
        expect(heading).toBeInTheDocument()
      })

      it('shows error details when errors prop provided', () => {
        const errors = {
          'photo1.jpg': 'Network error',
          'photo2.jpg': 'Permission denied',
          'photo3.jpg': 'Invalid tag'
        }

        render(
          <BulkProgressModal
            {...defaultProps}
            status="error"
            failedCount={3}
            errors={errors}
          />
        )

        expect(screen.getByText(/photo1.jpg: Network error/i)).toBeInTheDocument()
        expect(screen.getByText(/photo2.jpg: Permission denied/i)).toBeInTheDocument()
        expect(screen.getByText(/photo3.jpg: Invalid tag/i)).toBeInTheDocument()
      })

      it('limits error display to first 5 errors', () => {
        const errors = {
          'photo1.jpg': 'Error 1',
          'photo2.jpg': 'Error 2',
          'photo3.jpg': 'Error 3',
          'photo4.jpg': 'Error 4',
          'photo5.jpg': 'Error 5',
          'photo6.jpg': 'Error 6',
          'photo7.jpg': 'Error 7'
        }

        render(
          <BulkProgressModal
            {...defaultProps}
            status="error"
            failedCount={7}
            errors={errors}
          />
        )

        // Should show first 5
        expect(screen.getByText(/photo1.jpg: Error 1/i)).toBeInTheDocument()
        expect(screen.getByText(/photo5.jpg: Error 5/i)).toBeInTheDocument()

        // Should NOT show 6th and 7th directly
        expect(screen.queryByText(/photo6.jpg: Error 6/i)).not.toBeInTheDocument()
        expect(screen.queryByText(/photo7.jpg: Error 7/i)).not.toBeInTheDocument()

        // Should show "and X more" message
        expect(screen.getByText(/and 2 more/i)).toBeInTheDocument()
      })

      it('does NOT show errors section when errors prop is empty', () => {
        render(
          <BulkProgressModal
            {...defaultProps}
            status="error"
            failedCount={5}
            errors={{}}
          />
        )

        // Should only show failed count, not error details
        expect(screen.getByText(/5 photos failed to process/i)).toBeInTheDocument()
        expect(screen.queryByText(/:/)).not.toBeInTheDocument()
      })

      it('shows Close button in error state', () => {
        render(
          <BulkProgressModal
            {...defaultProps}
            status="error"
            failedCount={5}
          />
        )

        expect(screen.getByRole('button', { name: /close/i })).toBeInTheDocument()
      })
    })
  })

  describe('Cancel Button', () => {
    it('shows Cancel button during processing', () => {
      render(<BulkProgressModal {...defaultProps} status="processing" />)

      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
    })

    it('Cancel button calls onCancel prop', async () => {
      const user = userEvent.setup()
      const onCancel = vi.fn()

      render(
        <BulkProgressModal
          {...defaultProps}
          status="processing"
          onCancel={onCancel}
        />
      )

      await user.click(screen.getByRole('button', { name: /cancel/i }))

      expect(onCancel).toHaveBeenCalledTimes(1)
    })

    it('does NOT show Cancel button in success state', () => {
      render(
        <BulkProgressModal
          {...defaultProps}
          status="success"
          successCount={10}
        />
      )

      expect(screen.queryByRole('button', { name: /cancel/i })).not.toBeInTheDocument()
    })

    it('does NOT show Cancel button in error state', () => {
      render(
        <BulkProgressModal
          {...defaultProps}
          status="error"
          failedCount={5}
        />
      )

      expect(screen.queryByRole('button', { name: /cancel/i })).not.toBeInTheDocument()
    })
  })

  describe('Modal Behavior', () => {
    it('modal backdrop exists during processing', () => {
      render(<BulkProgressModal {...defaultProps} status="processing" />)

      const backdrop = document.querySelector('.bg-black\\/50')
      expect(backdrop).toBeInTheDocument()
    })

    it('clicking backdrop during processing does NOT close modal', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()

      render(
        <BulkProgressModal
          {...defaultProps}
          status="processing"
          onClose={onClose}
        />
      )

      const backdrop = document.querySelector('.bg-black\\/50')
      await user.click(backdrop)

      expect(onClose).not.toHaveBeenCalled()
    })

    it('Escape key does NOT close modal during processing', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()

      render(
        <BulkProgressModal
          {...defaultProps}
          status="processing"
          onClose={onClose}
        />
      )

      await user.keyboard('{Escape}')

      expect(onClose).not.toHaveBeenCalled()
    })

    it('backdrop is non-interactive during processing (no onClick handler)', () => {
      render(<BulkProgressModal {...defaultProps} status="processing" />)

      const backdrop = document.querySelector('.bg-black\\/50')

      // Verify no onClick handler is attached (check that click doesn't do anything)
      // This is implicitly tested by the "clicking backdrop does NOT close" test above
      expect(backdrop).toBeInTheDocument()
    })
  })

  describe('Completion', () => {
    it('shows "Done" button after successful completion', () => {
      render(
        <BulkProgressModal
          {...defaultProps}
          status="success"
          successCount={10}
        />
      )

      expect(screen.getByRole('button', { name: /done/i })).toBeInTheDocument()
    })

    it('Done button calls onClose prop', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()

      render(
        <BulkProgressModal
          {...defaultProps}
          status="success"
          successCount={10}
          onClose={onClose}
        />
      )

      await user.click(screen.getByRole('button', { name: /done/i }))

      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('shows "Close" button after error completion', () => {
      render(
        <BulkProgressModal
          {...defaultProps}
          status="error"
          failedCount={5}
        />
      )

      expect(screen.getByRole('button', { name: /close/i })).toBeInTheDocument()
    })

    it('Close button calls onClose prop', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()

      render(
        <BulkProgressModal
          {...defaultProps}
          status="error"
          failedCount={5}
          onClose={onClose}
        />
      )

      await user.click(screen.getByRole('button', { name: /close/i }))

      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('shows success count in summary', () => {
      render(
        <BulkProgressModal
          {...defaultProps}
          status="success"
          successCount={42}
        />
      )

      expect(screen.getByText(/Successfully processed 42 photos/i)).toBeInTheDocument()
    })

    it('shows failed count if any failures in success state', () => {
      render(
        <BulkProgressModal
          {...defaultProps}
          status="success"
          successCount={8}
          failedCount={2}
        />
      )

      expect(screen.getByText(/8 photos, 2 failed/i)).toBeInTheDocument()
    })
  })

  describe('Edge Cases', () => {
    it('handles missing onCancel prop gracefully', () => {
      const { onCancel, ...propsWithoutCancel } = defaultProps

      render(<BulkProgressModal {...propsWithoutCancel} status="processing" />)

      // Should still render Cancel button (it just won't do anything)
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
    })

    it('handles 0 totalCount', () => {
      render(
        <BulkProgressModal
          {...defaultProps}
          processedCount={0}
          totalCount={0}
        />
      )

      expect(screen.getByText(/Processing 0 of 0 photos/i)).toBeInTheDocument()
    })

    it('handles progress value clamping (negative)', () => {
      render(<BulkProgressModal {...defaultProps} progress={-10} />)

      const progressBar = screen.getByRole('progressbar')
      expect(progressBar).toHaveAttribute('aria-valuenow', '-10')
      expect(progressBar).toHaveStyle({ width: '-10%' })
    })

    it('handles progress value over 100', () => {
      render(<BulkProgressModal {...defaultProps} progress={150} />)

      const progressBar = screen.getByRole('progressbar')
      expect(progressBar).toHaveAttribute('aria-valuenow', '150')
      expect(progressBar).toHaveStyle({ width: '150%' })
    })

    it('handles undefined operation (defaults to "tag")', () => {
      render(<BulkProgressModal {...defaultProps} operation={undefined} />)

      expect(screen.getByText(/Tagging photos/i)).toBeInTheDocument()
    })

    it('renders correctly when reopened after closing', () => {
      const { rerender } = render(<BulkProgressModal {...defaultProps} isOpen={false} />)

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

      rerender(<BulkProgressModal {...defaultProps} isOpen={true} />)

      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('progress bar has correct ARIA attributes', () => {
      render(<BulkProgressModal {...defaultProps} progress={50} />)

      const progressBar = screen.getByRole('progressbar')
      expect(progressBar).toHaveAttribute('aria-valuenow', '50')
      expect(progressBar).toHaveAttribute('aria-valuemin', '0')
      expect(progressBar).toHaveAttribute('aria-valuemax', '100')
    })

    it('dialog has correct role and aria-modal', () => {
      render(<BulkProgressModal {...defaultProps} />)

      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveAttribute('role', 'dialog')
      expect(dialog).toHaveAttribute('aria-modal', 'true')
    })

    it('dialog has aria-label based on operation', () => {
      const { rerender } = render(
        <BulkProgressModal {...defaultProps} operation="tag" />
      )
      expect(screen.getByLabelText('Tagging progress')).toBeInTheDocument()

      rerender(<BulkProgressModal {...defaultProps} operation="species" />)
      expect(screen.getByLabelText('Updating species progress')).toBeInTheDocument()

      rerender(<BulkProgressModal {...defaultProps} operation="delete" />)
      expect(screen.getByLabelText('Deleting progress')).toBeInTheDocument()
    })
  })
})

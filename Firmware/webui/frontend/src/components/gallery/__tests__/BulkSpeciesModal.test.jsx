import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import BulkSpeciesModal from '../BulkSpeciesModal'

describe('BulkSpeciesModal', () => {
  const mockOnClose = vi.fn()
  const mockOnApply = vi.fn()

  const defaultProps = {
    isOpen: true,
    onClose: mockOnClose,
    onApply: mockOnApply,
    selectedCount: 5,
    isLoading: false,
    error: null,
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('does NOT render when isOpen is false', () => {
      render(<BulkSpeciesModal {...defaultProps} isOpen={false} />)

      // Modal should not be in DOM
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })

    it('renders when isOpen is true', () => {
      render(<BulkSpeciesModal {...defaultProps} />)

      // Modal dialog should be visible
      expect(screen.getByRole('dialog')).toBeInTheDocument()
      expect(screen.getByLabelText(/close modal/i)).toBeInTheDocument()
    })

    it('shows "Set species for X photos" title', () => {
      render(<BulkSpeciesModal {...defaultProps} selectedCount={5} />)

      expect(screen.getByText(/Set species for 5 photos/i)).toBeInTheDocument()
    })

    it('shows "Set species for 1 photo" title for single photo', () => {
      render(<BulkSpeciesModal {...defaultProps} selectedCount={1} />)

      expect(screen.getByText(/Set species for 1 photo$/i)).toBeInTheDocument()
    })
  })

  describe('Form Fields', () => {
    it('shows species name input (required)', () => {
      render(<BulkSpeciesModal {...defaultProps} />)

      const input = screen.getByLabelText(/species name/i)
      expect(input).toBeInTheDocument()
      expect(input).toHaveAttribute('required')
    })

    it('shows common name input (optional)', () => {
      render(<BulkSpeciesModal {...defaultProps} />)

      const input = screen.getByLabelText(/common name/i)
      expect(input).toBeInTheDocument()
      expect(input).not.toHaveAttribute('required')
    })

    it('shows confidence dropdown with options: Certain, Probable, Possible, Unknown', () => {
      render(<BulkSpeciesModal {...defaultProps} />)

      const select = screen.getByLabelText(/confidence/i)
      expect(select).toBeInTheDocument()

      // Check all options are present
      expect(screen.getByRole('option', { name: 'Certain' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'Probable' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'Possible' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'Unknown' })).toBeInTheDocument()
    })

    it('confidence defaults to "Probable"', () => {
      render(<BulkSpeciesModal {...defaultProps} />)

      const select = screen.getByLabelText(/confidence/i)
      expect(select).toHaveValue('probable')
    })
  })

  describe('Validation', () => {
    it('Apply button disabled when species name is empty', () => {
      render(<BulkSpeciesModal {...defaultProps} />)

      const applyButton = screen.getByRole('button', { name: /apply/i })
      expect(applyButton).toBeDisabled()
    })

    it('Apply button enabled when species name provided', async () => {
      const user = userEvent.setup()
      render(<BulkSpeciesModal {...defaultProps} />)

      const speciesInput = screen.getByLabelText(/species name/i)
      await user.type(speciesInput, 'Danaus plexippus')

      const applyButton = screen.getByRole('button', { name: /apply/i })
      expect(applyButton).toBeEnabled()
    })

    it('trims whitespace from inputs', async () => {
      const user = userEvent.setup()
      render(<BulkSpeciesModal {...defaultProps} />)

      const speciesInput = screen.getByLabelText(/species name/i)
      const commonNameInput = screen.getByLabelText(/common name/i)

      await user.type(speciesInput, '  Danaus plexippus  ')
      await user.type(commonNameInput, '  Monarch Butterfly  ')

      const applyButton = screen.getByRole('button', { name: /apply/i })
      await user.click(applyButton)

      // Uses snake_case field names to match backend schema
      expect(mockOnApply).toHaveBeenCalledWith({
        species: 'Danaus plexippus',
        species_common_name: 'Monarch Butterfly',
        species_confidence: 'probable',
      })
    })

    it('does not send species_common_name if only whitespace', async () => {
      const user = userEvent.setup()
      render(<BulkSpeciesModal {...defaultProps} />)

      const speciesInput = screen.getByLabelText(/species name/i)
      const commonNameInput = screen.getByLabelText(/common name/i)

      await user.type(speciesInput, 'Danaus plexippus')
      await user.type(commonNameInput, '   ')

      const applyButton = screen.getByRole('button', { name: /apply/i })
      await user.click(applyButton)

      // Uses snake_case field names to match backend schema
      expect(mockOnApply).toHaveBeenCalledWith({
        species: 'Danaus plexippus',
        species_confidence: 'probable',
      })
    })
  })

  describe('Action Buttons', () => {
    it('Cancel button closes modal', async () => {
      const user = userEvent.setup()
      render(<BulkSpeciesModal {...defaultProps} />)

      const cancelButton = screen.getByRole('button', { name: /cancel/i })
      await user.click(cancelButton)

      expect(mockOnClose).toHaveBeenCalledTimes(1)
    })

    it('Apply button calls onApply with species data', async () => {
      const user = userEvent.setup()
      render(<BulkSpeciesModal {...defaultProps} />)

      const speciesInput = screen.getByLabelText(/species name/i)
      const commonNameInput = screen.getByLabelText(/common name/i)
      const confidenceSelect = screen.getByLabelText(/confidence/i)

      await user.type(speciesInput, 'Danaus plexippus')
      await user.type(commonNameInput, 'Monarch Butterfly')
      await user.selectOptions(confidenceSelect, 'certain')

      const applyButton = screen.getByRole('button', { name: /apply/i })
      await user.click(applyButton)

      // Uses snake_case field names to match backend schema
      expect(mockOnApply).toHaveBeenCalledWith({
        species: 'Danaus plexippus',
        species_common_name: 'Monarch Butterfly',
        species_confidence: 'certain',
      })
    })

    it('Apply button shows "Applying..." when loading', () => {
      render(<BulkSpeciesModal {...defaultProps} isLoading={true} />)

      expect(screen.getByText('Applying...')).toBeInTheDocument()
    })

    it('Cancel button disabled when loading', () => {
      render(<BulkSpeciesModal {...defaultProps} isLoading={true} />)

      const cancelButton = screen.getByRole('button', { name: /cancel/i })
      expect(cancelButton).toBeDisabled()
    })
  })

  describe('Modal Behavior', () => {
    it('Escape closes modal', () => {
      render(<BulkSpeciesModal {...defaultProps} />)

      fireEvent.keyDown(document, { key: 'Escape' })

      expect(mockOnClose).toHaveBeenCalledTimes(1)
    })

    it('backdrop click closes modal', async () => {
      const user = userEvent.setup()
      render(<BulkSpeciesModal {...defaultProps} />)

      // Click the backdrop (not the modal content)
      const backdrop = screen.getByRole('dialog').parentElement.firstChild
      await user.click(backdrop)

      expect(mockOnClose).toHaveBeenCalledTimes(1)
    })

    it('clicking modal content does NOT close modal', async () => {
      const user = userEvent.setup()
      render(<BulkSpeciesModal {...defaultProps} />)

      const dialog = screen.getByRole('dialog')
      await user.click(dialog)

      expect(mockOnClose).not.toHaveBeenCalled()
    })

    it('state resets on reopen', async () => {
      const user = userEvent.setup()
      const { rerender } = render(<BulkSpeciesModal {...defaultProps} />)

      // Enter data
      const speciesInput = screen.getByLabelText(/species name/i)
      const commonNameInput = screen.getByLabelText(/common name/i)
      const confidenceSelect = screen.getByLabelText(/confidence/i)

      await user.type(speciesInput, 'Danaus plexippus')
      await user.type(commonNameInput, 'Monarch Butterfly')
      await user.selectOptions(confidenceSelect, 'certain')

      // Close modal
      rerender(<BulkSpeciesModal {...defaultProps} isOpen={false} />)

      // Reopen modal
      rerender(<BulkSpeciesModal {...defaultProps} isOpen={true} />)

      // Fields should be reset
      expect(screen.getByLabelText(/species name/i)).toHaveValue('')
      expect(screen.getByLabelText(/common name/i)).toHaveValue('')
      expect(screen.getByLabelText(/confidence/i)).toHaveValue('probable')
    })
  })

  describe('Error Handling', () => {
    it('displays error message when provided', () => {
      render(<BulkSpeciesModal {...defaultProps} error="Failed to apply species" />)

      expect(screen.getByText('Failed to apply species')).toBeInTheDocument()
    })

    it('does not display error when null', () => {
      render(<BulkSpeciesModal {...defaultProps} error={null} />)

      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA attributes', () => {
      render(<BulkSpeciesModal {...defaultProps} />)

      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveAttribute('aria-modal', 'true')
      expect(dialog).toHaveAttribute('aria-labelledby')
    })

    it('close button has accessible label', () => {
      render(<BulkSpeciesModal {...defaultProps} />)

      const closeButton = screen.getByLabelText(/close modal/i)
      expect(closeButton).toBeInTheDocument()
    })

    it('all form inputs have labels', () => {
      render(<BulkSpeciesModal {...defaultProps} />)

      expect(screen.getByLabelText(/species name/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/common name/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/confidence/i)).toBeInTheDocument()
    })
  })
})

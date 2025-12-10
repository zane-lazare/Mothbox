import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'
import SavePresetModal from '../SavePresetModal'

describe('SavePresetModal', () => {
  let mockOnClose
  let mockOnSave

  beforeEach(() => {
    mockOnClose = vi.fn()
    mockOnSave = vi.fn()
  })

  describe('Rendering', () => {
    it('renders when open', () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      expect(screen.getByRole('dialog')).toBeInTheDocument()
      expect(screen.getByText('Save Filter Preset')).toBeInTheDocument()
    })

    it('is hidden when closed', () => {
      render(
        <SavePresetModal
          isOpen={false}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })

    it('renders preset name input', () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const input = screen.getByLabelText('Preset Name')
      expect(input).toBeInTheDocument()
      expect(input).toHaveAttribute('type', 'text')
      expect(input).toHaveAttribute('placeholder', 'Enter preset name...')
    })

    it('renders Save and Cancel buttons', () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument()
    })

    it('renders close button', () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      expect(screen.getByRole('button', { name: 'Close modal' })).toBeInTheDocument()
    })

    it('renders character counter', () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      expect(screen.getByText('0/50 characters')).toBeInTheDocument()
    })
  })

  describe('Input Focus', () => {
    it('focuses input on open', async () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const input = screen.getByLabelText('Preset Name')
      await waitFor(() => {
        expect(input).toHaveFocus()
      })
    })

    it('does not focus input when closed', () => {
      render(
        <SavePresetModal
          isOpen={false}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const input = screen.queryByLabelText('Preset Name')
      expect(input).not.toBeInTheDocument()
    })
  })

  describe('Save Button Behavior', () => {
    it('calls onSave with name when Save clicked', () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const input = screen.getByLabelText('Preset Name')
      const saveButton = screen.getByRole('button', { name: 'Save' })

      fireEvent.change(input, { target: { value: 'My Preset' } })
      fireEvent.click(saveButton)

      expect(mockOnSave).toHaveBeenCalledWith('My Preset')
      expect(mockOnSave).toHaveBeenCalledTimes(1)
    })

    it('trims whitespace from name before saving', () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const input = screen.getByLabelText('Preset Name')
      const saveButton = screen.getByRole('button', { name: 'Save' })

      fireEvent.change(input, { target: { value: '  My Preset  ' } })
      fireEvent.click(saveButton)

      expect(mockOnSave).toHaveBeenCalledWith('My Preset')
    })

    it('does not call onSave when name is empty', () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const saveButton = screen.getByRole('button', { name: 'Save' })
      fireEvent.click(saveButton)

      expect(mockOnSave).not.toHaveBeenCalled()
    })

    it('does not call onSave when name is whitespace only', () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const input = screen.getByLabelText('Preset Name')
      const saveButton = screen.getByRole('button', { name: 'Save' })

      fireEvent.change(input, { target: { value: '   ' } })
      fireEvent.click(saveButton)

      expect(mockOnSave).not.toHaveBeenCalled()
    })
  })

  describe('Cancel Button Behavior', () => {
    it('calls onClose when Cancel clicked', () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const cancelButton = screen.getByRole('button', { name: 'Cancel' })
      fireEvent.click(cancelButton)

      expect(mockOnClose).toHaveBeenCalledTimes(1)
      expect(mockOnSave).not.toHaveBeenCalled()
    })

    it('resets input when Cancel clicked', () => {
      const { rerender } = render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const input = screen.getByLabelText('Preset Name')
      fireEvent.change(input, { target: { value: 'Test' } })

      const cancelButton = screen.getByRole('button', { name: 'Cancel' })
      fireEvent.click(cancelButton)

      // Simulate modal closing and reopening
      rerender(
        <SavePresetModal
          isOpen={false}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      rerender(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const newInput = screen.getByLabelText('Preset Name')
      expect(newInput).toHaveValue('')
    })
  })

  describe('Keyboard Shortcuts', () => {
    it('submits form on Enter key', () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const input = screen.getByLabelText('Preset Name')
      fireEvent.change(input, { target: { value: 'My Preset' } })
      fireEvent.keyPress(input, { key: 'Enter', code: 'Enter', charCode: 13 })

      expect(mockOnSave).toHaveBeenCalledWith('My Preset')
    })

    it('closes modal on Escape key', () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      fireEvent.keyDown(document, { key: 'Escape', code: 'Escape' })

      expect(mockOnClose).toHaveBeenCalledTimes(1)
    })

    it('does not close on Escape when modal is closed', () => {
      render(
        <SavePresetModal
          isOpen={false}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      fireEvent.keyDown(document, { key: 'Escape', code: 'Escape' })

      expect(mockOnClose).not.toHaveBeenCalled()
    })
  })

  describe('Backdrop Click', () => {
    it('closes modal when backdrop is clicked', () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const backdrop = screen.getByTestId('modal-backdrop')
      fireEvent.click(backdrop)

      expect(mockOnClose).toHaveBeenCalledTimes(1)
    })

    it('does not close when modal content is clicked', () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const dialog = screen.getByRole('dialog')
      fireEvent.click(dialog)

      expect(mockOnClose).not.toHaveBeenCalled()
    })

    it('resets input when backdrop is clicked', () => {
      const { rerender } = render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const input = screen.getByLabelText('Preset Name')
      fireEvent.change(input, { target: { value: 'Test' } })

      const backdrop = screen.getByTestId('modal-backdrop')
      fireEvent.click(backdrop)

      // Simulate modal closing and reopening
      rerender(
        <SavePresetModal
          isOpen={false}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      rerender(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const newInput = screen.getByLabelText('Preset Name')
      expect(newInput).toHaveValue('')
    })
  })

  describe('Validation', () => {
    it('shows error for empty name', () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const input = screen.getByLabelText('Preset Name')

      // Trigger validation by typing then clearing
      fireEvent.change(input, { target: { value: 'test' } })
      fireEvent.change(input, { target: { value: '' } })

      expect(screen.getByRole('alert')).toHaveTextContent('Preset name is required')
    })

    it('shows error when name exceeds 50 characters', () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const input = screen.getByLabelText('Preset Name')
      const longName = 'a'.repeat(51)

      fireEvent.change(input, { target: { value: longName } })

      expect(screen.getByRole('alert')).toHaveTextContent('Name must be 50 characters or less')
    })

    it('disables Save button when name is empty', () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const saveButton = screen.getByRole('button', { name: 'Save' })
      expect(saveButton).toBeDisabled()
    })

    it('disables Save button when name is whitespace', () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const input = screen.getByLabelText('Preset Name')
      fireEvent.change(input, { target: { value: '   ' } })

      const saveButton = screen.getByRole('button', { name: 'Save' })
      expect(saveButton).toBeDisabled()
    })

    it('disables Save button when validation error exists', () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const input = screen.getByLabelText('Preset Name')
      fireEvent.change(input, { target: { value: 'a'.repeat(51) } })

      const saveButton = screen.getByRole('button', { name: 'Save' })
      expect(saveButton).toBeDisabled()
    })

    it('enables Save button when name is valid', () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const input = screen.getByLabelText('Preset Name')
      fireEvent.change(input, { target: { value: 'Valid Name' } })

      const saveButton = screen.getByRole('button', { name: 'Save' })
      expect(saveButton).not.toBeDisabled()
    })
  })

  describe('Max Length Enforcement', () => {
    it('enforces 50 character max length on input', () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const input = screen.getByLabelText('Preset Name')
      expect(input).toHaveAttribute('maxLength', '50')
    })

    it('updates character counter as user types', () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const input = screen.getByLabelText('Preset Name')

      fireEvent.change(input, { target: { value: 'Test' } })
      expect(screen.getByText('4/50 characters')).toBeInTheDocument()

      fireEvent.change(input, { target: { value: 'Test Preset' } })
      expect(screen.getByText('11/50 characters')).toBeInTheDocument()
    })
  })

  describe('Default Name', () => {
    it('populates input with defaultName prop', async () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
          defaultName="Default Preset"
        />
      )

      const input = screen.getByLabelText('Preset Name')
      await waitFor(() => {
        expect(input).toHaveValue('Default Preset')
      })
    })

    it('updates input when defaultName changes', async () => {
      const { rerender } = render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
          defaultName="First"
        />
      )

      const input = screen.getByLabelText('Preset Name')
      await waitFor(() => {
        expect(input).toHaveValue('First')
      })

      rerender(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
          defaultName="Second"
        />
      )

      await waitFor(() => {
        expect(input).toHaveValue('Second')
      })
    })

    it('resets to defaultName when modal reopens', async () => {
      const { rerender } = render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
          defaultName="Default"
        />
      )

      const input = screen.getByLabelText('Preset Name')
      fireEvent.change(input, { target: { value: 'Modified' } })

      // Close modal
      rerender(
        <SavePresetModal
          isOpen={false}
          onClose={mockOnClose}
          onSave={mockOnSave}
          defaultName="Default"
        />
      )

      // Reopen modal
      rerender(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
          defaultName="Default"
        />
      )

      await waitFor(() => {
        const newInput = screen.getByLabelText('Preset Name')
        expect(newInput).toHaveValue('Default')
      })
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA attributes', () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveAttribute('aria-modal', 'true')
      expect(dialog).toHaveAttribute('aria-labelledby', 'save-preset-title')
    })

    it('associates label with input', () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const input = screen.getByLabelText('Preset Name')
      expect(input).toHaveAttribute('id', 'preset-name')
    })

    it('marks input as invalid when error exists', () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const input = screen.getByLabelText('Preset Name')
      fireEvent.change(input, { target: { value: 'a'.repeat(51) } })

      expect(input).toHaveAttribute('aria-invalid', 'true')
    })

    it('associates error message with input', () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const input = screen.getByLabelText('Preset Name')
      fireEvent.change(input, { target: { value: 'a'.repeat(51) } })

      expect(input).toHaveAttribute('aria-describedby', 'name-error')
      expect(screen.getByRole('alert')).toHaveAttribute('id', 'name-error')
    })

    it('has accessible close button', () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const closeButton = screen.getByRole('button', { name: 'Close modal' })
      expect(closeButton).toHaveAttribute('aria-label', 'Close modal')
    })
  })

  describe('Styling', () => {
    it('applies dark mode classes', () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveClass('dark:bg-gray-800')

      const input = screen.getByLabelText('Preset Name')
      expect(input).toHaveClass('dark:bg-gray-700', 'dark:text-gray-100')
    })

    it('applies error styling to input when validation fails', () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const input = screen.getByLabelText('Preset Name')
      fireEvent.change(input, { target: { value: 'a'.repeat(51) } })

      expect(input).toHaveClass('border-red-500', 'dark:border-red-500')
    })

    it('applies normal border when no error', () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const input = screen.getByLabelText('Preset Name')
      fireEvent.change(input, { target: { value: 'Valid' } })

      expect(input).toHaveClass('border-gray-300', 'dark:border-gray-600')
    })

    it('applies disabled styles to Save button', () => {
      render(
        <SavePresetModal
          isOpen={true}
          onClose={mockOnClose}
          onSave={mockOnSave}
        />
      )

      const saveButton = screen.getByRole('button', { name: 'Save' })
      expect(saveButton).toHaveClass('disabled:opacity-50', 'disabled:cursor-not-allowed')
    })
  })
})

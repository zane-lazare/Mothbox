import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { SavePresetModal } from '../SavePresetModal'

const defaultProps = {
  isOpen: true,
  onClose: vi.fn(),
  onSave: vi.fn(),
}

function renderModal(overrides = {}) {
  return render(<SavePresetModal {...defaultProps} {...overrides} />)
}

describe('SavePresetModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders modal when open', () => {
      renderModal()

      expect(screen.getByRole('dialog')).toBeInTheDocument()
      expect(screen.getByText('Save Filter Preset')).toBeInTheDocument()
      expect(screen.getByLabelText('Preset Name *')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Save Preset' })).toBeInTheDocument()
    })

    it('renders nothing when closed', () => {
      renderModal({ isOpen: false })

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })

    it('renders close button', () => {
      renderModal()

      expect(screen.getByRole('button', { name: 'Close modal' })).toBeInTheDocument()
    })

    it('renders character counter', () => {
      renderModal()

      expect(screen.getByText('0/50 characters')).toBeInTheDocument()
    })

    it('updates character counter as user types', async () => {
      const user = userEvent.setup()
      renderModal()

      const input = screen.getByLabelText('Preset Name *')
      await user.type(input, 'Test')

      expect(screen.getByText('4/50 characters')).toBeInTheDocument()
    })

    it('shows saving state', () => {
      renderModal({ isSaving: true })

      expect(screen.getByText('Saving...')).toBeInTheDocument()
      expect(screen.getByLabelText('Preset Name *')).toBeDisabled()
    })
  })

  describe('Validation', () => {
    it('shows error for empty name on blur', async () => {
      const user = userEvent.setup()
      renderModal()

      const input = screen.getByLabelText('Preset Name *')
      await user.click(input)
      await user.type(input, 'a')
      await user.clear(input)
      await user.tab()

      expect(await screen.findByRole('alert')).toHaveTextContent('Preset name is required')
    })

    it('shows error for name shorter than 3 characters on blur', async () => {
      const user = userEvent.setup()
      renderModal()

      const input = screen.getByLabelText('Preset Name *')
      await user.type(input, 'ab')
      await user.tab()

      expect(await screen.findByRole('alert')).toHaveTextContent(
        'Name must be at least 3 characters'
      )
    })

    it('shows error for name exceeding 50 characters on blur', async () => {
      const user = userEvent.setup()
      renderModal()

      const input = screen.getByLabelText('Preset Name *')
      await user.type(input, 'a'.repeat(51))
      await user.tab()

      expect(await screen.findByRole('alert')).toHaveTextContent(
        'Name must be less than 50 characters'
      )
    })

    it('shows no error for valid name', async () => {
      const user = userEvent.setup()
      renderModal()

      const input = screen.getByLabelText('Preset Name *')
      await user.type(input, 'Valid Preset Name')
      await user.tab()

      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    })

    it('clears error after correcting input', async () => {
      const user = userEvent.setup()
      renderModal()

      const input = screen.getByLabelText('Preset Name *')
      // Type too-short name and blur to trigger error
      await user.type(input, 'ab')
      await user.tab()
      expect(await screen.findByRole('alert')).toBeInTheDocument()

      // Fix the name and blur again
      await user.click(input)
      await user.type(input, 'cde')
      await user.tab()

      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    })
  })

  describe('Save flow', () => {
    it('calls onSave with trimmed name on submit', async () => {
      const user = userEvent.setup()
      const onSave = vi.fn()
      renderModal({ onSave })

      const input = screen.getByLabelText('Preset Name *')
      await user.type(input, '  My Preset  ')
      await user.tab()
      await user.click(screen.getByRole('button', { name: 'Save Preset' }))

      expect(onSave).toHaveBeenCalledWith('My Preset')
      expect(onSave).toHaveBeenCalledTimes(1)
    })

    it('does not call onSave when form is empty', async () => {
      const user = userEvent.setup()
      const onSave = vi.fn()
      renderModal({ onSave })

      // Button disabled when nothing typed (not dirty)
      const saveButton = screen.getByRole('button', { name: 'Save Preset' })
      expect(saveButton).toBeDisabled()
      await user.click(saveButton)

      expect(onSave).not.toHaveBeenCalled()
    })

    it('shows validation error when submitting invalid name via Enter', async () => {
      const user = userEvent.setup()
      const onSave = vi.fn()
      renderModal({ onSave })

      const input = screen.getByLabelText('Preset Name *')
      await user.type(input, 'ab')
      await user.type(input, '{Enter}')

      expect(await screen.findByRole('alert')).toBeInTheDocument()
      expect(onSave).not.toHaveBeenCalled()
    })

    it('calls onClose after successful save', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      const onSave = vi.fn()
      renderModal({ onClose, onSave })

      const input = screen.getByLabelText('Preset Name *')
      await user.type(input, 'My Preset')
      await user.tab()
      await user.click(screen.getByRole('button', { name: 'Save Preset' }))

      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('keeps modal open when onSave throws', async () => {
      const user = userEvent.setup()
      const onSave = vi.fn().mockRejectedValue(new Error('save failed'))
      const onClose = vi.fn()
      renderModal({ onSave, onClose })

      const input = screen.getByLabelText('Preset Name *')
      await user.type(input, 'My Preset')
      await user.tab()
      await user.click(screen.getByRole('button', { name: 'Save Preset' }))

      expect(onClose).not.toHaveBeenCalled()
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })
  })

  describe('Cancel and close', () => {
    it('calls onClose when Cancel is clicked', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      renderModal({ onClose })

      await user.click(screen.getByRole('button', { name: 'Cancel' }))

      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('calls onClose when close (X) button is clicked', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      renderModal({ onClose })

      await user.click(screen.getByRole('button', { name: 'Close modal' }))

      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('calls onClose when backdrop is clicked', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      renderModal({ onClose })

      await user.click(screen.getByTestId('modal-backdrop'))

      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('does not close modal on backdrop click while saving', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      renderModal({ isSaving: true, onClose })

      await user.click(screen.getByTestId('modal-backdrop'))

      expect(onClose).not.toHaveBeenCalled()
    })
  })

  describe('Keyboard shortcuts', () => {
    it('submits form on Enter key with valid input', async () => {
      const user = userEvent.setup()
      const onSave = vi.fn()
      renderModal({ onSave })

      const input = screen.getByLabelText('Preset Name *')
      await user.type(input, 'My Preset')
      await user.type(input, '{Enter}')

      expect(onSave).toHaveBeenCalledWith('My Preset')
    })

    it('closes modal on Escape key from any focused element', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      renderModal({ onClose })

      // Tab past input to a button, then press Escape
      await user.tab()
      await user.tab()
      await user.keyboard('{Escape}')

      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('does not close modal on Escape key while saving', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      renderModal({ isSaving: true, onClose })

      await user.keyboard('{Escape}')

      expect(onClose).not.toHaveBeenCalled()
    })
  })

  describe('Disabled states', () => {
    it('disables save button when input is empty', () => {
      renderModal()

      expect(screen.getByRole('button', { name: 'Save Preset' })).toBeDisabled()
    })

    it('disables save button when validation error exists', async () => {
      const user = userEvent.setup()
      renderModal()

      const input = screen.getByLabelText('Preset Name *')
      await user.type(input, 'ab')
      await user.tab()

      await screen.findByRole('alert')
      expect(screen.getByRole('button', { name: 'Save Preset' })).toBeDisabled()
    })

    it('disables save button and input when isSaving is true', () => {
      renderModal({ isSaving: true })

      expect(screen.getByLabelText('Preset Name *')).toBeDisabled()
      expect(screen.getByRole('button', { name: /saving/i })).toBeDisabled()
    })
  })

  describe('Default name', () => {
    it('populates input with defaultName prop', () => {
      renderModal({ defaultName: 'Default Preset' })

      expect(screen.getByLabelText('Preset Name *')).toHaveValue('Default Preset')
    })

    it('resets to defaultName when modal reopens', async () => {
      const user = userEvent.setup()
      const { rerender } = renderModal({ defaultName: 'Default' })

      // Modify the input
      const input = screen.getByLabelText('Preset Name *')
      await user.clear(input)
      await user.type(input, 'Modified')

      // Close modal
      rerender(<SavePresetModal {...defaultProps} isOpen={false} defaultName="Default" />)
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

      // Reopen modal — should reset to defaultName
      rerender(<SavePresetModal {...defaultProps} isOpen={true} defaultName="Default" />)
      expect(screen.getByLabelText('Preset Name *')).toHaveValue('Default')
    })

    it('allows saving with defaultName unchanged', async () => {
      const user = userEvent.setup()
      const onSave = vi.fn()
      renderModal({ defaultName: 'Default Preset', onSave })

      const input = screen.getByLabelText('Preset Name *')
      // Blur the input to trigger validation without changing the value
      await user.click(input)
      await user.tab()

      const saveButton = screen.getByRole('button', { name: 'Save Preset' })
      expect(saveButton).not.toBeDisabled()
      await user.click(saveButton)

      expect(onSave).toHaveBeenCalledWith('Default Preset')
    })

    it('marks form as dirty when defaultName is modified', async () => {
      const user = userEvent.setup()
      renderModal({ defaultName: 'Default' })

      const input = screen.getByLabelText('Preset Name *')
      await user.clear(input)
      await user.type(input, 'Modified')
      await user.tab()

      // Save button should be enabled (dirty + valid)
      expect(screen.getByRole('button', { name: 'Save Preset' })).not.toBeDisabled()
    })
  })

  describe('Accessibility', () => {
    it('has correct dialog aria attributes', () => {
      renderModal()

      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveAttribute('aria-modal', 'true')
      expect(dialog).toHaveAttribute('aria-labelledby', 'save-preset-title')
    })

    it('marks input as aria-required', () => {
      renderModal()

      expect(screen.getByLabelText('Preset Name *')).toHaveAttribute('aria-required', 'true')
    })

    it('sets aria-invalid and aria-describedby on errored input', async () => {
      const user = userEvent.setup()
      renderModal()

      const input = screen.getByLabelText('Preset Name *')
      await user.type(input, 'ab')
      await user.tab()

      await screen.findByRole('alert')
      expect(input).toHaveAttribute('aria-invalid', 'true')
      expect(input).toHaveAttribute('aria-describedby', 'name-error')
    })
  })

  describe('Form reset', () => {
    it('resets form state and errors when modal reopens', async () => {
      const user = userEvent.setup()
      const { rerender } = renderModal()

      // Trigger a validation error
      const input = screen.getByLabelText('Preset Name *')
      await user.type(input, 'ab')
      await user.tab()
      expect(await screen.findByRole('alert')).toBeInTheDocument()

      // Close modal
      rerender(
        <SavePresetModal {...defaultProps} isOpen={false} />
      )
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

      // Reopen modal — form and errors should be reset
      rerender(
        <SavePresetModal {...defaultProps} isOpen={true} />
      )
      const newInput = screen.getByLabelText('Preset Name *')
      expect(newInput).toHaveValue('')
      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    })
  })
})

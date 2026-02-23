import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SavePresetModal } from '../SavePresetModal'
import { validatePresetSettings } from '../../utils/presetValidation'

vi.mock('../../utils/presetValidation', () => ({
  validatePresetSettings: vi.fn(() => []),
}))

const mockedValidate = vi.mocked(validatePresetSettings)

describe('SavePresetModal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onSave: vi.fn().mockResolvedValue(undefined),
    isSaving: false,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockedValidate.mockReturnValue([])
  })

  const renderModal = (props = {}) =>
    render(<SavePresetModal {...defaultProps} {...props} />)

  describe('Rendering', () => {
    it('returns null when isOpen is false', () => {
      const { container } = renderModal({ isOpen: false })
      expect(container.innerHTML).toBe('')
    })

    it('renders modal when open with title, inputs, and buttons', () => {
      renderModal()
      expect(screen.getByText('Save Current Settings as Preset')).toBeInTheDocument()
      expect(screen.getByPlaceholderText('e.g., my_field_setup')).toBeInTheDocument()
      expect(screen.getByPlaceholderText('Describe when to use this preset...')).toBeInTheDocument()
      expect(screen.getByText('Cancel')).toBeInTheDocument()
      expect(screen.getByText('Save Preset')).toBeInTheDocument()
    })
  })

  describe('Name validation', () => {
    it('shows error for empty name after clearing', async () => {
      const user = userEvent.setup()
      renderModal()
      const input = screen.getByPlaceholderText('e.g., my_field_setup')
      await user.type(input, 'a')
      await user.clear(input)
      expect(await screen.findByRole('alert')).toHaveTextContent('Preset name is required')
    })

    it('shows error for name shorter than 3 characters', async () => {
      const user = userEvent.setup()
      renderModal()
      const input = screen.getByPlaceholderText('e.g., my_field_setup')
      await user.type(input, 'ab')
      expect(await screen.findByText('Name must be at least 3 characters')).toBeInTheDocument()
    })

    it('shows error for invalid characters', async () => {
      const user = userEvent.setup()
      renderModal()
      const input = screen.getByPlaceholderText('e.g., my_field_setup')
      await user.type(input, 'my preset!')
      expect(
        await screen.findByText('Name can only contain letters, numbers, and underscores')
      ).toBeInTheDocument()
    })

    it('clears error when valid name is entered', async () => {
      const user = userEvent.setup()
      renderModal()
      const input = screen.getByPlaceholderText('e.g., my_field_setup')
      await user.type(input, 'ab')
      expect(await screen.findByText('Name must be at least 3 characters')).toBeInTheDocument()
      await user.type(input, 'c')
      await waitFor(() => {
        expect(screen.queryByText('Name must be at least 3 characters')).not.toBeInTheDocument()
      })
    })
  })

  describe('Description', () => {
    it('displays character counter', () => {
      renderModal()
      expect(screen.getByText('0/200 characters')).toBeInTheDocument()
    })

    it('updates character counter as user types', async () => {
      const user = userEvent.setup()
      renderModal()
      const textarea = screen.getByPlaceholderText('Describe when to use this preset...')
      await user.type(textarea, 'Hello')
      expect(screen.getByText('5/200 characters')).toBeInTheDocument()
    })
  })

  describe('Workflow selection', () => {
    it('defaults to "both" workflow', () => {
      renderModal()
      const bothRadio = screen.getByRole('radio', { name: /Both/i })
      expect(bothRadio).toBeChecked()
    })

    it('selects photo workflow', async () => {
      const user = userEvent.setup()
      renderModal()
      const photoRadio = screen.getByRole('radio', { name: /Photo.*Capture only/i })
      await user.click(photoRadio)
      expect(photoRadio).toBeChecked()
    })

    it('uses defaultWorkflow prop', () => {
      renderModal({ defaultWorkflow: 'photo' })
      const photoRadio = screen.getByRole('radio', { name: /Photo.*Capture only/i })
      expect(photoRadio).toBeChecked()
    })
  })

  describe('Settings validation', () => {
    it('skips settings validation for photo-only workflow', async () => {
      const user = userEvent.setup()
      renderModal({ currentSettings: { sharpness: 99 } })
      const photoRadio = screen.getByRole('radio', { name: /Photo.*Capture only/i })
      await user.click(photoRadio)
      const input = screen.getByPlaceholderText('e.g., my_field_setup')
      await user.type(input, 'photo_only')
      await user.click(screen.getByText('Save Preset'))
      expect(mockedValidate).not.toHaveBeenCalled()
      expect(defaultProps.onSave).toHaveBeenCalled()
    })

    it('validates settings for non-photo workflow', async () => {
      const user = userEvent.setup()
      const settings = { sharpness: 2.0 }
      renderModal({ currentSettings: settings })
      const input = screen.getByPlaceholderText('e.g., my_field_setup')
      await user.type(input, 'both_preset')
      await user.click(screen.getByText('Save Preset'))
      expect(mockedValidate).toHaveBeenCalledWith(settings)
    })

    it('shows settings errors and blocks save', async () => {
      const user = userEvent.setup()
      mockedValidate.mockReturnValue([
        { key: 'sharpness', value: 99, message: 'Sharpness must be between 0.0 and 4.0' },
      ])
      renderModal({ currentSettings: { sharpness: 99 } })
      const input = screen.getByPlaceholderText('e.g., my_field_setup')
      await user.type(input, 'bad_settings')
      await user.click(screen.getByText('Save Preset'))
      expect(defaultProps.onSave).not.toHaveBeenCalled()
      const alert = screen.getByRole('alert')
      expect(alert).toBeInTheDocument()
      expect(screen.getByText('sharpness')).toBeInTheDocument()
      expect(screen.getByText('99')).toBeInTheDocument()
      expect(screen.getByText('Sharpness must be between 0.0 and 4.0')).toBeInTheDocument()
    })

    it('truncates settings errors after 5 and shows count', async () => {
      const user = userEvent.setup()
      const errors = Array.from({ length: 7 }, (_, i) => ({
        key: `setting_${i}`,
        value: i,
        message: `Error ${i}`,
      }))
      mockedValidate.mockReturnValue(errors)
      renderModal({ currentSettings: {} })
      const input = screen.getByPlaceholderText('e.g., my_field_setup')
      await user.type(input, 'many_errors')
      await user.click(screen.getByText('Save Preset'))
      expect(screen.getByText(/and 2 more/)).toBeInTheDocument()
      expect(screen.queryByText('setting_5')).not.toBeInTheDocument()
    })
  })

  describe('Save flow', () => {
    it('calls onSave with correct payload', async () => {
      const user = userEvent.setup()
      renderModal()
      const nameInput = screen.getByPlaceholderText('e.g., my_field_setup')
      await user.type(nameInput, 'test_preset')
      const descInput = screen.getByPlaceholderText('Describe when to use this preset...')
      await user.type(descInput, 'A test description')
      await user.click(screen.getByText('Save Preset'))
      expect(defaultProps.onSave).toHaveBeenCalledWith({
        name: 'test_preset',
        description: 'A test description',
        workflow: 'both',
        from_current: true,
      })
    })

    it('trims description whitespace on save', async () => {
      const user = userEvent.setup()
      renderModal()
      const nameInput = screen.getByPlaceholderText('e.g., my_field_setup')
      await user.type(nameInput, 'test_preset')
      const descInput = screen.getByPlaceholderText('Describe when to use this preset...')
      await user.type(descInput, '  padded  ')
      await user.click(screen.getByText('Save Preset'))
      expect(defaultProps.onSave).toHaveBeenCalledWith(
        expect.objectContaining({ description: 'padded' })
      )
    })

    it('resets form after successful save', async () => {
      const user = userEvent.setup()
      renderModal()
      const nameInput = screen.getByPlaceholderText('e.g., my_field_setup')
      await user.type(nameInput, 'test_preset')
      await user.click(screen.getByText('Save Preset'))
      await waitFor(() => {
        expect(nameInput).toHaveValue('')
      })
    })
  })

  describe('Cancel and close', () => {
    it('calls onClose when cancel is clicked', async () => {
      const user = userEvent.setup()
      renderModal()
      await user.click(screen.getByText('Cancel'))
      expect(defaultProps.onClose).toHaveBeenCalledTimes(1)
    })

    it('calls onClose on Escape key', async () => {
      const user = userEvent.setup()
      renderModal()
      await user.keyboard('{Escape}')
      expect(defaultProps.onClose).toHaveBeenCalledTimes(1)
    })

    it('calls onClose on backdrop click', async () => {
      const user = userEvent.setup()
      renderModal()
      const backdrop = screen.getByTestId('modal-backdrop')
      await user.click(backdrop)
      expect(defaultProps.onClose).toHaveBeenCalledTimes(1)
    })

    it('does not close on Escape when saving', async () => {
      const user = userEvent.setup()
      renderModal({ isSaving: true })
      await user.keyboard('{Escape}')
      expect(defaultProps.onClose).not.toHaveBeenCalled()
    })
  })

  describe('Disabled states', () => {
    it('disables save button when name is empty', () => {
      renderModal()
      expect(screen.getByText('Save Preset')).toBeDisabled()
    })

    it('disables all inputs and buttons when saving', () => {
      renderModal({ isSaving: true })
      expect(screen.getByPlaceholderText('e.g., my_field_setup')).toBeDisabled()
      expect(screen.getByPlaceholderText('Describe when to use this preset...')).toBeDisabled()
      expect(screen.getByText('Cancel')).toBeDisabled()
      expect(screen.getByText('Saving...')).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has dialog role and aria-modal', () => {
      renderModal()
      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveAttribute('aria-modal', 'true')
    })

    it('sets aria-invalid on name input when invalid', async () => {
      const user = userEvent.setup()
      renderModal()
      const input = screen.getByPlaceholderText('e.g., my_field_setup')
      await user.type(input, 'a')
      await user.clear(input)
      await screen.findByRole('alert')
      expect(input).toHaveAttribute('aria-invalid', 'true')
    })

    it('sets aria-required on name input', () => {
      renderModal()
      const input = screen.getByPlaceholderText('e.g., my_field_setup')
      expect(input).toHaveAttribute('aria-required', 'true')
    })

    it('has aria-describedby linking to counter', () => {
      renderModal()
      const input = screen.getByPlaceholderText('e.g., my_field_setup')
      const describedBy = input.getAttribute('aria-describedby') || ''
      expect(describedBy).toContain('name-counter')
    })
  })

  describe('Keyboard', () => {
    it('submits form on Enter key in name input', async () => {
      const user = userEvent.setup()
      renderModal()
      const input = screen.getByPlaceholderText('e.g., my_field_setup')
      await user.type(input, 'enter_test')
      await user.keyboard('{Enter}')
      expect(defaultProps.onSave).toHaveBeenCalled()
    })
  })
})

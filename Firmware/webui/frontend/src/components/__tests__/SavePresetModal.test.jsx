import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SavePresetModal from '../SavePresetModal'
import { validatePresetSettings } from '../../utils/presetValidation'

// Mock the preset validation module
vi.mock('../../utils/presetValidation', () => ({
  validatePresetSettings: vi.fn(() => []),
}))

describe('SavePresetModal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onSave: vi.fn().mockResolvedValue(undefined),
    isSaving: false,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    validatePresetSettings.mockReturnValue([])
  })

  const renderModal = (props = {}) => {
    return render(<SavePresetModal {...defaultProps} {...props} />)
  }

  it('returns null when isOpen is false', () => {
    const { container } = renderModal({ isOpen: false })
    expect(container.innerHTML).toBe('')
  })

  it('renders modal when open with title, inputs, and buttons', () => {
    renderModal()

    expect(screen.getByText(/Save Current Settings as Preset/i)).toBeInTheDocument()
    expect(screen.getByPlaceholderText('e.g., my_field_setup')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Describe when to use this preset...')).toBeInTheDocument()
    expect(screen.getByText('Cancel')).toBeInTheDocument()
    expect(screen.getByText('Save Preset')).toBeInTheDocument()
  })

  it('shows validation error for short name (< 3 chars)', async () => {
    const user = userEvent.setup()
    renderModal()

    const nameInput = screen.getByPlaceholderText('e.g., my_field_setup')
    await user.type(nameInput, 'ab')

    expect(screen.getByText('Name must be at least 3 characters')).toBeInTheDocument()
  })

  it('shows validation error for invalid characters', async () => {
    const user = userEvent.setup()
    renderModal()

    const nameInput = screen.getByPlaceholderText('e.g., my_field_setup')
    await user.type(nameInput, 'my preset!')

    expect(screen.getByText('Name can only contain letters, numbers, and underscores')).toBeInTheDocument()
  })

  it('accepts valid name without showing validation errors', async () => {
    const user = userEvent.setup()
    renderModal()

    const nameInput = screen.getByPlaceholderText('e.g., my_field_setup')
    await user.type(nameInput, 'my_valid_preset')

    expect(screen.queryByText('Name must be at least 3 characters')).not.toBeInTheDocument()
    expect(screen.queryByText('Name can only contain letters, numbers, and underscores')).not.toBeInTheDocument()
    expect(screen.queryByText('Preset name is required')).not.toBeInTheDocument()
  })

  it('disables save button when name is empty', () => {
    renderModal()

    const saveButton = screen.getByText('Save Preset')
    expect(saveButton).toBeDisabled()
  })

  it('enables save button with valid name', async () => {
    const user = userEvent.setup()
    renderModal()

    const nameInput = screen.getByPlaceholderText('e.g., my_field_setup')
    await user.type(nameInput, 'valid_name')

    const saveButton = screen.getByText('Save Preset')
    expect(saveButton).not.toBeDisabled()
  })

  it('calls onSave with correct data (name, description, workflow, from_current)', async () => {
    const user = userEvent.setup()
    renderModal()

    const nameInput = screen.getByPlaceholderText('e.g., my_field_setup')
    await user.type(nameInput, 'test_preset')

    const descInput = screen.getByPlaceholderText('Describe when to use this preset...')
    await user.type(descInput, 'A test description')

    const saveButton = screen.getByText('Save Preset')
    await user.click(saveButton)

    expect(defaultProps.onSave).toHaveBeenCalledWith({
      name: 'test_preset',
      description: 'A test description',
      workflow: 'both',
      from_current: true,
    })
  })

  it('selects photo workflow correctly', async () => {
    const user = userEvent.setup()
    renderModal()

    // Select photo workflow — use exact label text to avoid matching "Both (Photo & Live View)"
    const photoRadio = screen.getByRole('radio', { name: /Photo.*Capture only/i })
    await user.click(photoRadio)
    expect(photoRadio).toBeChecked()

    // Fill in name and save
    const nameInput = screen.getByPlaceholderText('e.g., my_field_setup')
    await user.type(nameInput, 'photo_preset')

    const saveButton = screen.getByText('Save Preset')
    await user.click(saveButton)

    expect(defaultProps.onSave).toHaveBeenCalledWith(
      expect.objectContaining({ workflow: 'photo' })
    )
  })

  it('skips settings validation for photo-only workflow', async () => {
    const user = userEvent.setup()
    renderModal({ currentSettings: { sharpness: 99 } })

    // Select photo workflow — use exact label text to avoid matching "Both (Photo & Live View)"
    const photoRadio = screen.getByRole('radio', { name: /Photo.*Capture only/i })
    await user.click(photoRadio)

    // Fill in name and save
    const nameInput = screen.getByPlaceholderText('e.g., my_field_setup')
    await user.type(nameInput, 'photo_only')

    const saveButton = screen.getByText('Save Preset')
    await user.click(saveButton)

    expect(validatePresetSettings).not.toHaveBeenCalled()
    expect(defaultProps.onSave).toHaveBeenCalled()
  })

  it('validates settings for non-photo workflow', async () => {
    const user = userEvent.setup()
    const settings = { sharpness: 2.0 }
    renderModal({ currentSettings: settings })

    // Default workflow is 'both' (non-photo), fill name and save
    const nameInput = screen.getByPlaceholderText('e.g., my_field_setup')
    await user.type(nameInput, 'both_preset')

    const saveButton = screen.getByText('Save Preset')
    await user.click(saveButton)

    expect(validatePresetSettings).toHaveBeenCalledWith(settings)
  })

  it('displays validation errors from validatePresetSettings with role="alert"', async () => {
    const user = userEvent.setup()
    validatePresetSettings.mockReturnValue([
      { key: 'sharpness', value: 99, message: 'Sharpness must be between 0.0 and 4.0' },
    ])

    renderModal({ currentSettings: { sharpness: 99 } })

    const nameInput = screen.getByPlaceholderText('e.g., my_field_setup')
    await user.type(nameInput, 'bad_settings')

    const saveButton = screen.getByText('Save Preset')
    await user.click(saveButton)

    // Should NOT call onSave
    expect(defaultProps.onSave).not.toHaveBeenCalled()

    // Should display validation errors in an alert role
    const alert = screen.getByRole('alert')
    expect(alert).toBeInTheDocument()
    expect(screen.getByText('sharpness')).toBeInTheDocument()
    expect(screen.getByText('99')).toBeInTheDocument()
    expect(screen.getByText('Sharpness must be between 0.0 and 4.0')).toBeInTheDocument()
  })

  it('calls onClose when cancel button is clicked', async () => {
    const user = userEvent.setup()
    renderModal()

    const cancelButton = screen.getByText('Cancel')
    await user.click(cancelButton)

    expect(defaultProps.onClose).toHaveBeenCalledTimes(1)
  })

  it('shows saving state with "Saving..." text and disabled inputs', () => {
    renderModal({ isSaving: true })

    expect(screen.getByText('Saving...')).toBeInTheDocument()

    const nameInput = screen.getByPlaceholderText('e.g., my_field_setup')
    expect(nameInput).toBeDisabled()

    const descInput = screen.getByPlaceholderText('Describe when to use this preset...')
    expect(descInput).toBeDisabled()

    const cancelButton = screen.getByText('Cancel')
    expect(cancelButton).toBeDisabled()
  })
})

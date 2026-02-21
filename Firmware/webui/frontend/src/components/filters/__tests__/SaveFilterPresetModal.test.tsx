import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { SaveFilterPresetModal } from '../SaveFilterPresetModal'

const defaultProps = {
  isOpen: true,
  onClose: vi.fn(),
  onSave: vi.fn(),
}

function renderModal(overrides = {}) {
  return render(<SaveFilterPresetModal {...defaultProps} {...overrides} />)
}

describe('SaveFilterPresetModal', () => {
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
})

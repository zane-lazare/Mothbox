import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import BulkTagModal from '../BulkTagModal'

// Mock useTags hook to provide test tag data
vi.mock('../../../hooks/useTags', () => ({
  default: () => ({
    data: {
      tags: [
        { name: 'moth', count: 10 },
        { name: 'nocturnal', count: 5 },
        { name: 'insect', count: 8 }
      ]
    },
    isLoading: false,
    error: null
  })
}))

// Create QueryClient for tests
const createTestQueryClient = () => new QueryClient({
  defaultOptions: { queries: { retry: false } }
})

const renderModal = (props = {}) => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onApply: vi.fn(),
    selectedCount: 5
  }

  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <BulkTagModal {...defaultProps} {...props} />
    </QueryClientProvider>
  )
}

describe('BulkTagModal', () => {
  describe('Rendering', () => {
    it('does NOT render when isOpen is false', () => {
      renderModal({ isOpen: false })
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })

    it('renders modal when isOpen is true', () => {
      renderModal()
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    it('shows photo count in title - multiple photos', () => {
      renderModal({ selectedCount: 5 })
      expect(screen.getByText(/Add tags for 5 photos/i)).toBeInTheDocument()
    })

    it('shows photo count in title - single photo', () => {
      renderModal({ selectedCount: 1 })
      expect(screen.getByText(/Add tags for 1 photo$/i)).toBeInTheDocument()
    })

    it('renders as portal to document.body', () => {
      renderModal()
      const modal = screen.getByRole('dialog')
      // Modal should be inside a container that's a child of body
      // (createPortal creates a wrapper div inside body)
      expect(document.body.contains(modal)).toBe(true)
    })
  })

  describe('Mode Selector', () => {
    it('shows three mode options: Add, Replace, Remove', () => {
      renderModal()
      const radioGroup = screen.getByRole('radiogroup')
      const radios = within(radioGroup).getAllByRole('radio')

      expect(radios).toHaveLength(3)
      expect(within(radioGroup).getByLabelText(/Add tags/i)).toBeInTheDocument()
      expect(within(radioGroup).getByLabelText(/Replace tags/i)).toBeInTheDocument()
      expect(within(radioGroup).getByLabelText(/Remove tags/i)).toBeInTheDocument()
    })

    it('"Add" mode is selected by default', () => {
      renderModal()
      const radioGroup = screen.getByRole('radiogroup')
      const addRadio = within(radioGroup).getByLabelText(/Add tags/i)
      expect(addRadio).toBeChecked()
    })

    it('clicking mode option selects it', async () => {
      const user = userEvent.setup()
      renderModal()

      const radioGroup = screen.getByRole('radiogroup')
      const replaceRadio = within(radioGroup).getByLabelText(/Replace tags/i)
      await user.click(replaceRadio)

      expect(replaceRadio).toBeChecked()
      expect(within(radioGroup).getByLabelText(/Add tags/i)).not.toBeChecked()
    })

    it('"Add" shows description "Add to existing tags"', () => {
      renderModal()
      expect(screen.getByText(/Add to existing tags/i)).toBeInTheDocument()
    })

    it('"Replace" shows warning "Replace all existing tags"', () => {
      renderModal()
      expect(screen.getByText(/Replace all existing tags/i)).toBeInTheDocument()
    })

    it('"Remove" shows description "Remove these tags from photos"', () => {
      renderModal()
      expect(screen.getByText(/Remove these tags from photos/i)).toBeInTheDocument()
    })

    it('title updates when mode changes', async () => {
      const user = userEvent.setup()
      renderModal({ selectedCount: 5 })

      // Default: Add
      expect(screen.getByText(/Add tags for 5 photos/i)).toBeInTheDocument()

      // Change to Replace
      const radioGroup = screen.getByRole('radiogroup')
      await user.click(within(radioGroup).getByLabelText(/Replace tags/i))
      expect(screen.getByText(/Replace tags for 5 photos/i)).toBeInTheDocument()

      // Change to Remove
      await user.click(within(radioGroup).getByLabelText(/Remove tags/i))
      expect(screen.getByText(/Remove tags for 5 photos/i)).toBeInTheDocument()
    })
  })

  describe('Tag Input', () => {
    it('shows tag input field', () => {
      renderModal()
      expect(screen.getByPlaceholderText(/Type to search or create tags/i)).toBeInTheDocument()
    })

    it('can add tags by typing and pressing Enter', async () => {
      const user = userEvent.setup()
      renderModal()

      const input = screen.getByPlaceholderText(/Type to search or create tags/i)
      await user.type(input, 'moth{Enter}')

      // Tag should be displayed as chip
      expect(screen.getByText('moth')).toBeInTheDocument()
    })

    it('shows selected tags as removable chips', async () => {
      const user = userEvent.setup()
      renderModal()

      const input = screen.getByPlaceholderText(/Type to search or create tags/i)
      await user.type(input, 'moth{Enter}')
      await user.type(input, 'nocturnal{Enter}')

      expect(screen.getByText('moth')).toBeInTheDocument()
      expect(screen.getByText('nocturnal')).toBeInTheDocument()
    })

    it('can remove tags by clicking X on chip', async () => {
      const user = userEvent.setup()
      renderModal()

      const input = screen.getByPlaceholderText(/Type to search or create tags/i)
      await user.type(input, 'moth{Enter}')

      expect(screen.getByText('moth')).toBeInTheDocument()

      // Click remove button
      const removeButton = screen.getByLabelText(/Remove tag moth/i)
      await user.click(removeButton)

      expect(screen.queryByText('moth')).not.toBeInTheDocument()
    })

    it('prevents duplicate tags (case-insensitive)', async () => {
      const user = userEvent.setup()
      renderModal()

      const input = screen.getByPlaceholderText(/Type to search or create tags/i)
      await user.type(input, 'moth{Enter}')
      await user.type(input, 'MOTH{Enter}')

      // Should only have one "moth" tag (case-insensitive duplicate rejected)
      const mothTags = screen.getAllByText('moth')
      expect(mothTags).toHaveLength(1)
    })

    it('shows existing tags in dropdown when typing', async () => {
      const user = userEvent.setup()
      renderModal()

      const input = screen.getByPlaceholderText(/Type to search or create tags/i)
      await user.type(input, 'mo')

      // Wait for dropdown to appear with filtered suggestions
      await waitFor(() => {
        expect(screen.getByText('(10)')).toBeInTheDocument() // moth count
      })
    })
  })

  describe('Action Buttons', () => {
    it('shows Cancel button', () => {
      renderModal()
      expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument()
    })

    it('shows Apply button', () => {
      renderModal()
      expect(screen.getByRole('button', { name: /Apply/i })).toBeInTheDocument()
    })

    it('Apply button is disabled when no tags selected', () => {
      renderModal()
      const applyButton = screen.getByRole('button', { name: /Apply/i })
      expect(applyButton).toBeDisabled()
    })

    it('Apply button is enabled when tags are selected', async () => {
      const user = userEvent.setup()
      renderModal()

      const input = screen.getByPlaceholderText(/Type to search or create tags/i)
      await user.type(input, 'moth{Enter}')

      const applyButton = screen.getByRole('button', { name: /Apply/i })
      expect(applyButton).toBeEnabled()
    })

    it('Cancel button calls onClose prop', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      renderModal({ onClose })

      const cancelButton = screen.getByRole('button', { name: /Cancel/i })
      await user.click(cancelButton)

      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('Apply button calls onApply with { tags, mode } in Add mode', async () => {
      const user = userEvent.setup()
      const onApply = vi.fn()
      renderModal({ onApply })

      const input = screen.getByPlaceholderText(/Type to search or create tags/i)
      await user.type(input, 'moth{Enter}')
      await user.type(input, 'nocturnal{Enter}')

      const applyButton = screen.getByRole('button', { name: /Apply/i })
      await user.click(applyButton)

      expect(onApply).toHaveBeenCalledWith({
        tags: ['moth', 'nocturnal'],
        mode: 'add'
      })
    })

    it('Apply button calls onApply with Replace mode', async () => {
      const user = userEvent.setup()
      const onApply = vi.fn()
      renderModal({ onApply })

      // Change to Replace mode
      const radioGroup = screen.getByRole('radiogroup')
      await user.click(within(radioGroup).getByLabelText(/Replace tags/i))

      const input = screen.getByPlaceholderText(/Type to search or create tags/i)
      await user.type(input, 'new-tag{Enter}')

      const applyButton = screen.getByRole('button', { name: /Apply/i })
      await user.click(applyButton)

      expect(onApply).toHaveBeenCalledWith({
        tags: ['new-tag'],
        mode: 'replace'
      })
    })

    it('Apply button calls onApply with Remove mode', async () => {
      const user = userEvent.setup()
      const onApply = vi.fn()
      renderModal({ onApply })

      // Change to Remove mode
      const radioGroup = screen.getByRole('radiogroup')
      await user.click(within(radioGroup).getByLabelText(/Remove tags/i))

      const input = screen.getByPlaceholderText(/Type to search or create tags/i)
      await user.type(input, 'unwanted-tag{Enter}')

      const applyButton = screen.getByRole('button', { name: /Apply/i })
      await user.click(applyButton)

      expect(onApply).toHaveBeenCalledWith({
        tags: ['unwanted-tag'],
        mode: 'remove'
      })
    })
  })

  describe('Modal Behavior', () => {
    it('Escape key closes modal', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      renderModal({ onClose })

      await user.keyboard('{Escape}')

      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('clicking backdrop closes modal', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      renderModal({ onClose })

      // Click the backdrop (not the modal content)
      // The backdrop is the parent div with bg-black/50 class
      const modal = screen.getByRole('dialog')
      const container = modal.parentElement
      const backdrop = container.querySelector('.bg-black\\/50')
      await user.click(backdrop)

      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('clicking modal content does NOT close modal', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      renderModal({ onClose })

      const modal = screen.getByRole('dialog')
      await user.click(modal)

      expect(onClose).not.toHaveBeenCalled()
    })

    it('clicking Cancel closes modal', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      renderModal({ onClose })

      const cancelButton = screen.getByRole('button', { name: /Cancel/i })
      await user.click(cancelButton)

      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('modal resets state when closed and reopened', async () => {
      const user = userEvent.setup()
      const { rerender } = renderModal({ isOpen: true })

      // Add tags
      const input = screen.getByPlaceholderText(/Type to search or create tags/i)
      await user.type(input, 'moth{Enter}')

      // Change mode
      const radioGroup = screen.getByRole('radiogroup')
      await user.click(within(radioGroup).getByLabelText(/Replace tags/i))

      expect(screen.getByText('moth')).toBeInTheDocument()
      expect(within(radioGroup).getByLabelText(/Replace tags/i)).toBeChecked()

      // Close modal
      rerender(
        <QueryClientProvider client={createTestQueryClient()}>
          <BulkTagModal isOpen={false} onClose={vi.fn()} onApply={vi.fn()} selectedCount={5} />
        </QueryClientProvider>
      )

      // Reopen modal
      rerender(
        <QueryClientProvider client={createTestQueryClient()}>
          <BulkTagModal isOpen={true} onClose={vi.fn()} onApply={vi.fn()} selectedCount={5} />
        </QueryClientProvider>
      )

      // State should be reset
      expect(screen.queryByText('moth')).not.toBeInTheDocument()
      const newRadioGroup = screen.getByRole('radiogroup')
      expect(within(newRadioGroup).getByLabelText(/Add tags/i)).toBeChecked()
    })
  })

  describe('Loading/Error States', () => {
    it('shows loading state when isLoading prop is true', () => {
      renderModal({ isLoading: true })
      expect(screen.getByText(/Applying.../i)).toBeInTheDocument()
    })

    it('Apply button disabled during loading', async () => {
      const user = userEvent.setup()
      renderModal({ isLoading: true })

      // Even if we have tags, button should be disabled
      const input = screen.getByPlaceholderText(/Type to search or create tags/i)
      await user.type(input, 'moth{Enter}')

      const applyButton = screen.getByRole('button', { name: /Applying.../i })
      expect(applyButton).toBeDisabled()
    })

    it('Cancel button disabled during loading', () => {
      renderModal({ isLoading: true })
      const cancelButton = screen.getByRole('button', { name: /Cancel/i })
      expect(cancelButton).toBeDisabled()
    })

    it('shows error message when error prop provided', () => {
      renderModal({ error: 'Failed to apply tags' })
      expect(screen.getByText('Failed to apply tags')).toBeInTheDocument()
    })

    it('error message has proper ARIA role', () => {
      renderModal({ error: 'Failed to apply tags' })
      const errorMessage = screen.getByText('Failed to apply tags')
      expect(errorMessage).toHaveClass('text-red-600')
    })
  })

  describe('Accessibility', () => {
    it('has role="dialog" and aria-modal', () => {
      renderModal()
      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveAttribute('aria-modal', 'true')
    })

    it('has aria-labelledby for title', () => {
      renderModal()
      const dialog = screen.getByRole('dialog')
      const titleId = dialog.getAttribute('aria-labelledby')
      expect(titleId).toBeTruthy()
      expect(document.getElementById(titleId)).toBeInTheDocument()
    })

    it('mode options are radio buttons with proper ARIA', () => {
      renderModal()
      const radioGroup = screen.getByRole('radiogroup')
      expect(radioGroup).toHaveAttribute('aria-label', 'Tag operation mode')

      const radios = within(radioGroup).getAllByRole('radio')
      expect(radios).toHaveLength(3)
      radios.forEach(radio => {
        expect(radio).toHaveAttribute('name', 'tag-mode')
      })
    })

    it('close button has aria-label', () => {
      renderModal()
      const closeButton = screen.getByLabelText(/Close modal/i)
      expect(closeButton).toBeInTheDocument()
    })

    it('tags label is properly displayed', () => {
      renderModal()
      const label = screen.getByText('Tags')
      expect(label).toHaveClass('block')
    })
  })
})

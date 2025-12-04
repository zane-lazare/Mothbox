import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import MetadataTags from '../MetadataTags'

// Mock useTags hook
vi.mock('../../../hooks/useTags', () => ({
  default: vi.fn(() => ({
    data: {
      tags: [
        { name: 'moth', count: 15 },
        { name: 'butterfly', count: 8 },
        { name: 'beetle', count: 12 },
      ],
    },
    isLoading: false,
    isError: false,
  })),
}))

// Test wrapper with QueryClient
function TestWrapper({ children }) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

describe('MetadataTags', () => {
  const defaultProps = {
    tags: ['existing-tag', 'another-tag'],
    onAddTag: vi.fn(),
    onRemoveTag: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders existing tags as chips', () => {
      render(<MetadataTags {...defaultProps} />, { wrapper: TestWrapper })

      expect(screen.getByText('existing-tag')).toBeInTheDocument()
      expect(screen.getByText('another-tag')).toBeInTheDocument()
    })

    it('displays tag chips with remove button', () => {
      render(<MetadataTags {...defaultProps} />, { wrapper: TestWrapper })

      const removeButtons = screen.getAllByRole('button', { name: /Remove tag/i })
      expect(removeButtons).toHaveLength(2)
    })

    it('renders autocomplete input field', () => {
      render(<MetadataTags {...defaultProps} />, { wrapper: TestWrapper })

      const input = screen.getByPlaceholderText(/Type to add tags/i)
      expect(input).toBeInTheDocument()
      expect(input).toHaveAttribute('type', 'text')
    })

    it('shows placeholder when no tags exist', () => {
      render(<MetadataTags {...defaultProps} tags={[]} />, { wrapper: TestWrapper })

      expect(screen.getByText('Add tags...')).toBeInTheDocument()
    })
  })

  describe('Tag Removal', () => {
    it('calls onRemoveTag when clicking remove button', async () => {
      const user = userEvent.setup()
      render(<MetadataTags {...defaultProps} />, { wrapper: TestWrapper })

      const removeButton = screen.getByRole('button', { name: 'Remove tag existing-tag' })
      await user.click(removeButton)

      expect(defaultProps.onRemoveTag).toHaveBeenCalledWith('existing-tag')
      expect(defaultProps.onRemoveTag).toHaveBeenCalledTimes(1)
    })

    it('does not call onRemoveTag when disabled', async () => {
      const user = userEvent.setup()
      render(<MetadataTags {...defaultProps} disabled />, { wrapper: TestWrapper })

      const removeButton = screen.getByRole('button', { name: 'Remove tag existing-tag' })
      await user.click(removeButton)

      expect(defaultProps.onRemoveTag).not.toHaveBeenCalled()
    })
  })

  describe('Autocomplete', () => {
    it('shows suggestions dropdown when typing', async () => {
      const user = userEvent.setup()
      render(<MetadataTags {...defaultProps} />, { wrapper: TestWrapper })

      const input = screen.getByPlaceholderText(/Type to add tags/i)
      await user.type(input, 'moth')

      await waitFor(() => {
        expect(screen.getByText(/moth/)).toBeInTheDocument()
      })
    })

    it('displays suggestion counts', async () => {
      const user = userEvent.setup()
      render(<MetadataTags {...defaultProps} />, { wrapper: TestWrapper })

      const input = screen.getByPlaceholderText(/Type to add tags/i)
      await user.type(input, 'moth')

      await waitFor(() => {
        expect(screen.getByText('(15)')).toBeInTheDocument()
      })
    })

    it('filters suggestions based on input', async () => {
      const user = userEvent.setup()
      render(<MetadataTags {...defaultProps} />, { wrapper: TestWrapper })

      const input = screen.getByPlaceholderText(/Type to add tags/i)
      await user.type(input, 'bee')

      await waitFor(() => {
        expect(screen.getByText(/beetle/)).toBeInTheDocument()
        expect(screen.queryByText(/moth/)).not.toBeInTheDocument()
      })
    })

    it('excludes already selected tags from suggestions', async () => {
      const user = userEvent.setup()
      render(
        <MetadataTags {...defaultProps} tags={['moth']} />,
        { wrapper: TestWrapper }
      )

      const input = screen.getByPlaceholderText(/Type to add tags/i)
      await user.type(input, 'moth')

      await waitFor(() => {
        // Should not show moth in suggestions since it's already selected
        const suggestions = screen.queryAllByText('moth')
        // Only one instance: the existing chip, not in suggestions
        expect(suggestions).toHaveLength(1)
      })
    })

    it('adds tag when clicking suggestion', async () => {
      const user = userEvent.setup()
      render(<MetadataTags {...defaultProps} />, { wrapper: TestWrapper })

      const input = screen.getByPlaceholderText(/Type to add tags/i)
      await user.type(input, 'moth')

      await waitFor(() => {
        expect(screen.getByText(/moth/)).toBeInTheDocument()
      })

      const suggestion = screen.getByText('moth')
      await user.click(suggestion)

      expect(defaultProps.onAddTag).toHaveBeenCalledWith('moth')
    })
  })

  describe('Keyboard Interaction', () => {
    it('adds tag when pressing Enter', async () => {
      const user = userEvent.setup()
      render(<MetadataTags {...defaultProps} />, { wrapper: TestWrapper })

      const input = screen.getByPlaceholderText(/Type to add tags/i)
      await user.type(input, 'new-tag{Enter}')

      expect(defaultProps.onAddTag).toHaveBeenCalledWith('new-tag')
    })

    it('adds tag when typing comma', async () => {
      const user = userEvent.setup()
      render(<MetadataTags {...defaultProps} />, { wrapper: TestWrapper })

      const input = screen.getByPlaceholderText(/Type to add tags/i)
      await user.type(input, 'new-tag,')

      expect(defaultProps.onAddTag).toHaveBeenCalledWith('new-tag')
    })

    it('clears input after adding tag with Enter', async () => {
      const user = userEvent.setup()
      render(<MetadataTags {...defaultProps} />, { wrapper: TestWrapper })

      const input = screen.getByPlaceholderText(/Type to add tags/i)
      await user.type(input, 'new-tag{Enter}')

      expect(input.value).toBe('')
    })

    it('clears input after adding tag with comma', async () => {
      const user = userEvent.setup()
      render(<MetadataTags {...defaultProps} />, { wrapper: TestWrapper })

      const input = screen.getByPlaceholderText(/Type to add tags/i)
      await user.type(input, 'new-tag,')

      expect(input.value).toBe('')
    })
  })

  describe('Duplicate Prevention', () => {
    it('prevents adding duplicate tags (case-insensitive)', async () => {
      const user = userEvent.setup()
      render(<MetadataTags {...defaultProps} />, { wrapper: TestWrapper })

      const input = screen.getByPlaceholderText(/Type to add tags/i)
      await user.type(input, 'EXISTING-TAG{Enter}')

      expect(defaultProps.onAddTag).not.toHaveBeenCalled()
    })

    it('prevents adding empty tags', async () => {
      const user = userEvent.setup()
      render(<MetadataTags {...defaultProps} />, { wrapper: TestWrapper })

      const input = screen.getByPlaceholderText(/Type to add tags/i)
      await user.type(input, '{Enter}')

      expect(defaultProps.onAddTag).not.toHaveBeenCalled()
    })

    it('trims whitespace before adding', async () => {
      const user = userEvent.setup()
      render(<MetadataTags {...defaultProps} />, { wrapper: TestWrapper })

      const input = screen.getByPlaceholderText(/Type to add tags/i)
      await user.type(input, '  trimmed-tag  {Enter}')

      expect(defaultProps.onAddTag).toHaveBeenCalledWith('trimmed-tag')
    })

    it('prevents adding whitespace-only tags', async () => {
      const user = userEvent.setup()
      render(<MetadataTags {...defaultProps} />, { wrapper: TestWrapper })

      const input = screen.getByPlaceholderText(/Type to add tags/i)
      await user.type(input, '   {Enter}')

      expect(defaultProps.onAddTag).not.toHaveBeenCalled()
    })
  })

  describe('Copy to Next Photo', () => {
    it('renders copy button when onCopyToNext provided', () => {
      const onCopyToNext = vi.fn()
      render(
        <MetadataTags {...defaultProps} onCopyToNext={onCopyToNext} />,
        { wrapper: TestWrapper }
      )

      expect(screen.getByText(/Copy tags to next photo/i)).toBeInTheDocument()
    })

    it('does not render copy button when onCopyToNext not provided', () => {
      render(<MetadataTags {...defaultProps} />, { wrapper: TestWrapper })

      expect(screen.queryByText(/Copy tags to next photo/i)).not.toBeInTheDocument()
    })

    it('calls onCopyToNext when clicking copy button', async () => {
      const user = userEvent.setup()
      const onCopyToNext = vi.fn()
      render(
        <MetadataTags {...defaultProps} onCopyToNext={onCopyToNext} />,
        { wrapper: TestWrapper }
      )

      const copyButton = screen.getByText(/Copy tags to next photo/i)
      await user.click(copyButton)

      expect(onCopyToNext).toHaveBeenCalledTimes(1)
    })

    it('disables copy button when no tags exist', () => {
      const onCopyToNext = vi.fn()
      render(
        <MetadataTags {...defaultProps} tags={[]} onCopyToNext={onCopyToNext} />,
        { wrapper: TestWrapper }
      )

      const copyButton = screen.getByText(/Copy tags to next photo/i)
      expect(copyButton.closest('button')).toBeDisabled()
    })

    it('disables copy button when component is disabled', () => {
      const onCopyToNext = vi.fn()
      render(
        <MetadataTags {...defaultProps} onCopyToNext={onCopyToNext} disabled />,
        { wrapper: TestWrapper }
      )

      const copyButton = screen.getByText(/Copy tags to next photo/i)
      expect(copyButton.closest('button')).toBeDisabled()
    })
  })

  describe('Disabled State', () => {
    it('disables input when disabled prop is true', () => {
      render(<MetadataTags {...defaultProps} disabled />, { wrapper: TestWrapper })

      const input = screen.getByPlaceholderText(/Type to add tags/i)
      expect(input).toBeDisabled()
    })

    it('disables remove buttons when disabled', () => {
      render(<MetadataTags {...defaultProps} disabled />, { wrapper: TestWrapper })

      const removeButtons = screen.getAllByRole('button', { name: /Remove tag/i })
      removeButtons.forEach(button => {
        expect(button).toBeDisabled()
      })
    })

    it('does not show suggestions when disabled', async () => {
      const user = userEvent.setup()
      render(<MetadataTags {...defaultProps} disabled />, { wrapper: TestWrapper })

      const input = screen.getByPlaceholderText(/Type to add tags/i)

      // Try to type (won't work because input is disabled)
      await user.click(input)

      expect(screen.queryByText(/moth/)).not.toBeInTheDocument()
    })
  })
})

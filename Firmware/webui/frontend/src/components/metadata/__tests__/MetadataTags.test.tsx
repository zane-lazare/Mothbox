import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useForm, type Resolver } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import MetadataTags from '../MetadataTags'
import { metadataFormSchema, type MetadataFormData } from '../../../schemas/metadata'

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

const DEFAULT_VALUES: MetadataFormData = {
  tags: [],
  species: '',
  commonName: '',
  confidence: 'unknown',
  referenceUrl: '',
  notes: '',
  custom: [],
}

function renderTags(
  overrides: Partial<MetadataFormData> = {},
  opts: { onCopyToNext?: () => void; disabled?: boolean } = {},
) {
  function Wrapper() {
    // zodResolver's Zod 4 overload expects $ZodType<Output, FieldValues> but
    // Zod 4's public ZodType uses `unknown` for its input parameter. The cast
    // through `unknown` is safe because the schema validates the same shape at
    // runtime. TODO: Remove when @hookform/resolvers aligns with Zod 4 generics.
    const resolver = zodResolver(
      metadataFormSchema as unknown as Parameters<typeof zodResolver>[0],
    ) as unknown as Resolver<MetadataFormData>

    const { control, setValue } = useForm<MetadataFormData>({
      resolver,
      defaultValues: { ...DEFAULT_VALUES, ...overrides },
      mode: 'onBlur',
    })

    return (
      <QueryClientProvider
        client={
          new QueryClient({
            defaultOptions: { queries: { retry: false } },
          })
        }
      >
        <MetadataTags
          control={control}
          setValue={setValue}
          onCopyToNext={opts.onCopyToNext}
          disabled={opts.disabled}
        />
      </QueryClientProvider>
    )
  }

  return render(<Wrapper />)
}

describe('MetadataTags', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders existing tags as chips', () => {
      renderTags({ tags: ['existing-tag', 'another-tag'] })

      expect(screen.getByText('existing-tag')).toBeInTheDocument()
      expect(screen.getByText('another-tag')).toBeInTheDocument()
    })

    it('displays tag chips with remove button', () => {
      renderTags({ tags: ['existing-tag', 'another-tag'] })

      const removeButtons = screen.getAllByRole('button', { name: /Remove tag/i })
      expect(removeButtons).toHaveLength(2)
    })

    it('renders autocomplete input field', () => {
      renderTags({ tags: ['existing-tag', 'another-tag'] })

      const input = screen.getByPlaceholderText(/Type to add tags/i)
      expect(input).toBeInTheDocument()
      expect(input).toHaveAttribute('type', 'text')
    })

    it('shows placeholder when no tags exist', () => {
      renderTags({ tags: [] })

      expect(screen.getByText('Add tags...')).toBeInTheDocument()
    })
  })

  describe('Tag Removal', () => {
    it('removes tag chip when clicking remove button', async () => {
      const user = userEvent.setup()
      renderTags({ tags: ['existing-tag', 'another-tag'] })

      const removeButton = screen.getByRole('button', { name: 'Remove tag existing-tag' })
      await user.click(removeButton)

      await waitFor(() => {
        expect(screen.queryByText('existing-tag')).not.toBeInTheDocument()
      })
      expect(screen.getByText('another-tag')).toBeInTheDocument()
    })

    it('does not remove tag when disabled', async () => {
      const user = userEvent.setup()
      renderTags({ tags: ['existing-tag', 'another-tag'] }, { disabled: true })

      const removeButton = screen.getByRole('button', { name: 'Remove tag existing-tag' })
      await user.click(removeButton)

      // Tag should still be present because button is disabled
      expect(screen.getByText('existing-tag')).toBeInTheDocument()
    })
  })

  describe('Autocomplete', () => {
    it('shows suggestions dropdown when typing', async () => {
      const user = userEvent.setup()
      renderTags()

      const input = screen.getByPlaceholderText(/Type to add tags/i)
      await user.type(input, 'moth')

      await waitFor(() => {
        expect(screen.getByText(/moth/)).toBeInTheDocument()
      })
    })

    it('displays suggestion counts', async () => {
      const user = userEvent.setup()
      renderTags()

      const input = screen.getByPlaceholderText(/Type to add tags/i)
      await user.type(input, 'moth')

      await waitFor(() => {
        expect(screen.getByText('(15)')).toBeInTheDocument()
      })
    })

    it('filters suggestions based on input', async () => {
      const user = userEvent.setup()
      renderTags()

      const input = screen.getByPlaceholderText(/Type to add tags/i)
      await user.type(input, 'bee')

      await waitFor(() => {
        expect(screen.getByText(/beetle/)).toBeInTheDocument()
        expect(screen.queryByText(/moth/)).not.toBeInTheDocument()
      })
    })

    it('excludes already selected tags from suggestions', async () => {
      const user = userEvent.setup()
      renderTags({ tags: ['moth'] })

      const input = screen.getByPlaceholderText(/Type to add tags/i)
      await user.type(input, 'moth')

      await waitFor(() => {
        // Should not show moth in suggestions since it's already selected
        const moths = screen.queryAllByText('moth')
        // Only one instance: the existing chip, not in suggestions
        expect(moths).toHaveLength(1)
      })
    })

    it('adds tag when clicking suggestion', async () => {
      const user = userEvent.setup()
      renderTags()

      const input = screen.getByPlaceholderText(/Type to add tags/i)
      await user.type(input, 'moth')

      await waitFor(() => {
        expect(screen.getByText(/moth/)).toBeInTheDocument()
      })

      const suggestion = screen.getByText('moth')
      await user.click(suggestion)

      // Tag should now appear as a chip
      await waitFor(() => {
        expect(screen.getByText('moth')).toBeInTheDocument()
        expect(screen.getByRole('button', { name: 'Remove tag moth' })).toBeInTheDocument()
      })
    })
  })

  describe('Keyboard Interaction', () => {
    it('adds tag when pressing Enter', async () => {
      const user = userEvent.setup()
      renderTags()

      const input = screen.getByPlaceholderText(/Type to add tags/i)
      await user.type(input, 'new-tag{Enter}')

      await waitFor(() => {
        expect(screen.getByText('new-tag')).toBeInTheDocument()
        expect(screen.getByRole('button', { name: 'Remove tag new-tag' })).toBeInTheDocument()
      })
    })

    it('adds tag when typing comma', async () => {
      const user = userEvent.setup()
      renderTags()

      const input = screen.getByPlaceholderText(/Type to add tags/i)
      await user.type(input, 'new-tag,')

      await waitFor(() => {
        expect(screen.getByText('new-tag')).toBeInTheDocument()
        expect(screen.getByRole('button', { name: 'Remove tag new-tag' })).toBeInTheDocument()
      })
    })

    it('clears input after adding tag with Enter', async () => {
      const user = userEvent.setup()
      renderTags()

      const input = screen.getByPlaceholderText(/Type to add tags/i)
      await user.type(input, 'new-tag{Enter}')

      expect(input).toHaveValue('')
    })

    it('clears input after adding tag with comma', async () => {
      const user = userEvent.setup()
      renderTags()

      const input = screen.getByPlaceholderText(/Type to add tags/i)
      await user.type(input, 'new-tag,')

      expect(input).toHaveValue('')
    })
  })

  describe('Duplicate Prevention', () => {
    it('prevents adding duplicate tags (case-insensitive)', async () => {
      const user = userEvent.setup()
      renderTags({ tags: ['existing-tag'] })

      const input = screen.getByPlaceholderText(/Type to add tags/i)
      await user.type(input, 'EXISTING-TAG{Enter}')

      // Should still only have one tag chip for existing-tag
      const chips = screen.getAllByText('existing-tag')
      expect(chips).toHaveLength(1)
    })

    it('prevents adding empty tags', async () => {
      const user = userEvent.setup()
      renderTags()

      const input = screen.getByPlaceholderText(/Type to add tags/i)
      await user.type(input, '{Enter}')

      // No new tags should appear; placeholder should still be visible
      expect(screen.getByText('Add tags...')).toBeInTheDocument()
    })

    it('trims whitespace before adding', async () => {
      const user = userEvent.setup()
      renderTags()

      const input = screen.getByPlaceholderText(/Type to add tags/i)
      await user.type(input, '  trimmed-tag  {Enter}')

      await waitFor(() => {
        expect(screen.getByText('trimmed-tag')).toBeInTheDocument()
      })
    })

    it('prevents adding whitespace-only tags', async () => {
      const user = userEvent.setup()
      renderTags()

      const input = screen.getByPlaceholderText(/Type to add tags/i)
      await user.type(input, '   {Enter}')

      // No new tags should appear; placeholder should still be visible
      expect(screen.getByText('Add tags...')).toBeInTheDocument()
    })
  })

  describe('Copy to Next Photo', () => {
    it('renders copy button when onCopyToNext provided', () => {
      const onCopyToNext = vi.fn()
      renderTags({ tags: ['existing-tag'] }, { onCopyToNext })

      expect(screen.getByText(/Copy tags to next photo/i)).toBeInTheDocument()
    })

    it('does not render copy button when onCopyToNext not provided', () => {
      renderTags({ tags: ['existing-tag'] })

      expect(screen.queryByText(/Copy tags to next photo/i)).not.toBeInTheDocument()
    })

    it('calls onCopyToNext when clicking copy button', async () => {
      const user = userEvent.setup()
      const onCopyToNext = vi.fn()
      renderTags({ tags: ['existing-tag'] }, { onCopyToNext })

      const copyButton = screen.getByText(/Copy tags to next photo/i)
      await user.click(copyButton)

      expect(onCopyToNext).toHaveBeenCalledTimes(1)
    })

    it('disables copy button when no tags exist', () => {
      const onCopyToNext = vi.fn()
      renderTags({ tags: [] }, { onCopyToNext })

      const copyButton = screen.getByText(/Copy tags to next photo/i)
      expect(copyButton.closest('button')).toBeDisabled()
    })

    it('disables copy button when component is disabled', () => {
      const onCopyToNext = vi.fn()
      renderTags({ tags: ['existing-tag'] }, { onCopyToNext, disabled: true })

      const copyButton = screen.getByText(/Copy tags to next photo/i)
      expect(copyButton.closest('button')).toBeDisabled()
    })
  })

  describe('Disabled State', () => {
    it('disables input when disabled prop is true', () => {
      renderTags({ tags: ['existing-tag'] }, { disabled: true })

      const input = screen.getByPlaceholderText(/Type to add tags/i)
      expect(input).toBeDisabled()
    })

    it('disables remove buttons when disabled', () => {
      renderTags({ tags: ['existing-tag', 'another-tag'] }, { disabled: true })

      const removeButtons = screen.getAllByRole('button', { name: /Remove tag/i })
      removeButtons.forEach(button => {
        expect(button).toBeDisabled()
      })
    })

    it('does not show suggestions when disabled', async () => {
      const user = userEvent.setup()
      renderTags({ tags: ['existing-tag'] }, { disabled: true })

      const input = screen.getByPlaceholderText(/Type to add tags/i)

      // Try to type (won't work because input is disabled)
      await user.click(input)

      expect(screen.queryByText(/moth/)).not.toBeInTheDocument()
    })
  })
})

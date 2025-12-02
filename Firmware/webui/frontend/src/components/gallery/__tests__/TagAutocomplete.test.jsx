import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TagAutocomplete from '../TagAutocomplete'

const mockTags = [
  { name: 'moth', count: 15 },
  { name: 'butterfly', count: 8 },
  { name: 'beetle', count: 12 },
  { name: 'large-moth', count: 5 },
  { name: 'nocturnal', count: 20 },
]

describe('TagAutocomplete', () => {
  const defaultProps = {
    tags: mockTags,
    selectedTags: [],
    onSelect: vi.fn(),
    onCreate: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllTimers()
  })

  // Rendering
  describe('Rendering', () => {
    it('renders input field', () => {
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')
      expect(input).toBeInTheDocument()
    })

    it('renders placeholder text', () => {
      render(<TagAutocomplete {...defaultProps} placeholder="Type to search..." />)
      expect(screen.getByPlaceholderText('Type to search...')).toBeInTheDocument()
    })

    it('renders default placeholder when none provided', () => {
      render(<TagAutocomplete {...defaultProps} />)
      expect(screen.getByPlaceholderText('Search or create tags...')).toBeInTheDocument()
    })

    it('shows dropdown when input is focused and has text', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'm')

      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument()
      })
    })

    it('hides dropdown when input loses focus', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'moth')
      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument()
      })

      await user.tab()

      await waitFor(() => {
        expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
      })
    })

    it('does not show dropdown when input is empty', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      await user.click(input)

      expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
    })
  })

  // Filtering
  describe('Filtering', () => {
    it('filters tags based on input (case-insensitive)', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'moth')

      await waitFor(() => {
        expect(screen.getByText('moth')).toBeInTheDocument()
        expect(screen.getByText('large-moth')).toBeInTheDocument()
        expect(screen.queryByText('butterfly')).not.toBeInTheDocument()
        expect(screen.queryByText('beetle')).not.toBeInTheDocument()
      })
    })

    it('filters tags case-insensitively', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'MOTH')

      await waitFor(() => {
        expect(screen.getByText('moth')).toBeInTheDocument()
        expect(screen.getByText('large-moth')).toBeInTheDocument()
      })
    })

    it('shows all matching tags in dropdown', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'e')

      await waitFor(() => {
        const options = screen.getAllByRole('option')
        // Should show: beetle, large-moth, and potentially "Create" option
        expect(options.length).toBeGreaterThanOrEqual(2)
      })
    })

    it('shows "Create tag" option when no exact match', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'newtagname')

      await waitFor(() => {
        expect(screen.getByText('+ Create')).toBeInTheDocument()
        expect(screen.getByText('"newtagname"')).toBeInTheDocument()
      })
    })

    it('does not show create option when exact match exists', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'moth')

      await waitFor(() => {
        expect(screen.getByText('moth')).toBeInTheDocument()
        expect(screen.queryByText('+ Create')).not.toBeInTheDocument()
      })
    })

    it('does not show already selected tags', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} selectedTags={['moth']} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'moth')

      await waitFor(() => {
        const options = screen.getAllByRole('option')
        const mothOption = options.find(opt => opt.textContent.includes('moth') && !opt.textContent.includes('large-moth'))
        expect(mothOption).toBeUndefined()
      })
    })

    it('shows tag counts in suggestions', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'moth')

      await waitFor(() => {
        expect(screen.getByText('(15)')).toBeInTheDocument()
        expect(screen.getByText('(5)')).toBeInTheDocument()
      })
    })
  })

  // Selection
  describe('Selection', () => {
    it('calls onSelect when clicking a tag', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'moth')

      await waitFor(() => {
        expect(screen.getByText('moth')).toBeInTheDocument()
      })

      const mothOption = screen.getAllByRole('option').find(opt =>
        opt.textContent.includes('moth') && opt.textContent.includes('(15)')
      )
      await user.click(mothOption)

      expect(defaultProps.onSelect).toHaveBeenCalledWith('moth')
    })

    it('clears input after selection', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'moth')
      await waitFor(() => {
        expect(screen.getByText('moth')).toBeInTheDocument()
      })

      const mothOption = screen.getAllByRole('option').find(opt =>
        opt.textContent.includes('moth') && opt.textContent.includes('(15)')
      )
      await user.click(mothOption)

      expect(input.value).toBe('')
    })

    it('closes dropdown after selection', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'moth')
      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument()
      })

      const mothOption = screen.getAllByRole('option').find(opt =>
        opt.textContent.includes('moth') && opt.textContent.includes('(15)')
      )
      await user.click(mothOption)

      await waitFor(() => {
        expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
      })
    })

    it('refocuses input after selection', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'moth')
      await waitFor(() => {
        expect(screen.getByText('moth')).toBeInTheDocument()
      })

      const mothOption = screen.getAllByRole('option').find(opt =>
        opt.textContent.includes('moth') && opt.textContent.includes('(15)')
      )
      await user.click(mothOption)

      await waitFor(() => {
        expect(document.activeElement).toBe(input)
      })
    })
  })

  // Tag creation
  describe('Tag Creation', () => {
    it('calls onCreate when Enter pressed with no exact match', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'newtagname{Enter}')

      expect(defaultProps.onCreate).toHaveBeenCalledWith('newtagname')
    })

    it('calls onCreate when clicking "Create tag" option', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'newtagname')

      await waitFor(() => {
        expect(screen.getByText('+ Create')).toBeInTheDocument()
      })

      const createOption = screen.getByText('+ Create').closest('li')
      await user.click(createOption)

      expect(defaultProps.onCreate).toHaveBeenCalledWith('newtagname')
    })

    it('does not allow creating duplicate tags', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} selectedTags={['existingtag']} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'existingtag{Enter}')

      expect(defaultProps.onCreate).not.toHaveBeenCalled()
    })

    it('trims whitespace when creating tags', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      await user.type(input, '  spacytag  {Enter}')

      expect(defaultProps.onCreate).toHaveBeenCalledWith('spacytag')
    })

    it('does not create empty tags', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      await user.type(input, '   {Enter}')

      expect(defaultProps.onCreate).not.toHaveBeenCalled()
    })

    it('clears input after creating tag', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'newtagname{Enter}')

      expect(input.value).toBe('')
    })
  })

  // Keyboard navigation
  describe('Keyboard Navigation', () => {
    it('navigates down with Arrow Down', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'm')
      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument()
      })

      await user.keyboard('{ArrowDown}')

      await waitFor(() => {
        const options = screen.getAllByRole('option')
        expect(options[0]).toHaveAttribute('aria-selected', 'true')
      })
    })

    it('navigates up with Arrow Up', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'm')
      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument()
      })

      await user.keyboard('{ArrowDown}')
      await user.keyboard('{ArrowDown}')
      await user.keyboard('{ArrowUp}')

      await waitFor(() => {
        const options = screen.getAllByRole('option')
        expect(options[0]).toHaveAttribute('aria-selected', 'true')
      })
    })

    it('selects highlighted tag with Enter', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'moth')
      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument()
      })

      await user.keyboard('{ArrowDown}')
      await user.keyboard('{Enter}')

      expect(defaultProps.onSelect).toHaveBeenCalled()
    })

    it('closes dropdown with Escape', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'moth')
      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument()
      })

      await user.keyboard('{Escape}')

      await waitFor(() => {
        expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
      })
    })

    it('wraps around when navigating past end', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'm')
      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument()
      })

      const optionCount = screen.getAllByRole('option').length

      // Navigate past the end to trigger wrapping
      // Start at -1, go through all items (0, 1, 2, ...), then one more to wrap to 0
      for (let i = 0; i <= optionCount; i++) {
        await user.keyboard('{ArrowDown}')
      }

      // Should wrap to first
      await waitFor(() => {
        const options = screen.getAllByRole('option')
        expect(options[0]).toHaveAttribute('aria-selected', 'true')
      })
    })

    it('wraps around when navigating up from first item', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'm')
      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument()
      })

      // Navigate up from initial position (should wrap to last)
      await user.keyboard('{ArrowUp}')

      await waitFor(() => {
        const options = screen.getAllByRole('option')
        expect(options[options.length - 1]).toHaveAttribute('aria-selected', 'true')
      })
    })

    it('opens dropdown with ArrowDown when closed', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'moth')
      await user.keyboard('{Escape}')

      await waitFor(() => {
        expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
      })

      await user.keyboard('{ArrowDown}')

      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument()
      })
    })
  })

  // Accessibility
  describe('Accessibility', () => {
    it('has combobox role', () => {
      render(<TagAutocomplete {...defaultProps} />)
      expect(screen.getByRole('combobox')).toBeInTheDocument()
    })

    it('has aria-expanded when open', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      expect(input).toHaveAttribute('aria-expanded', 'false')

      await user.type(input, 'moth')

      await waitFor(() => {
        expect(input).toHaveAttribute('aria-expanded', 'true')
      })
    })

    it('has aria-activedescendant for highlighted item', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'moth')
      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument()
      })

      await user.keyboard('{ArrowDown}')

      await waitFor(() => {
        expect(input).toHaveAttribute('aria-activedescendant', 'tag-option-0')
      })
    })

    it('has aria-autocomplete list', () => {
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')
      expect(input).toHaveAttribute('aria-autocomplete', 'list')
    })

    it('has aria-controls pointing to listbox', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'moth')

      await waitFor(() => {
        expect(input).toHaveAttribute('aria-controls', 'tag-listbox')
        expect(screen.getByRole('listbox')).toHaveAttribute('id', 'tag-listbox')
      })
    })

    it('announces highlighted item to screen readers', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'moth')
      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument()
      })

      await user.keyboard('{ArrowDown}')

      await waitFor(() => {
        const options = screen.getAllByRole('option')
        expect(options[0]).toHaveAttribute('aria-selected', 'true')
      })
    })
  })

  // Edge cases
  describe('Edge Cases', () => {
    it('handles empty tags list', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} tags={[]} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'anything')

      await waitFor(() => {
        expect(screen.getByText('+ Create')).toBeInTheDocument()
      })
    })

    it('handles disabled state', () => {
      render(<TagAutocomplete {...defaultProps} disabled />)
      const input = screen.getByRole('combobox')
      expect(input).toBeDisabled()
    })

    it('does not open dropdown when disabled', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} disabled />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'moth')

      expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
    })

    it('handles custom className', () => {
      const { container } = render(<TagAutocomplete {...defaultProps} className="custom-class" />)
      expect(container.querySelector('.custom-class')).toBeInTheDocument()
    })

    it('handles tags with special characters', async () => {
      const user = userEvent.setup()
      const specialTags = [{ name: 'tag-with-dash', count: 5 }, { name: 'tag_with_underscore', count: 3 }]
      render(<TagAutocomplete {...defaultProps} tags={specialTags} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'tag')

      await waitFor(() => {
        expect(screen.getByText('tag-with-dash')).toBeInTheDocument()
        expect(screen.getByText('tag_with_underscore')).toBeInTheDocument()
      })
    })

    it('handles no results', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'xyz123notfound')

      await waitFor(() => {
        expect(screen.getByText('+ Create')).toBeInTheDocument()
        const options = screen.getAllByRole('option')
        expect(options).toHaveLength(1) // Only create option
      })
    })

    it('handles mouse hover changing highlight', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'm')
      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument()
      })

      await user.keyboard('{ArrowDown}')
      const options = screen.getAllByRole('option')

      // Hover over second option
      fireEvent.mouseEnter(options[1])

      await waitFor(() => {
        expect(options[1]).toHaveAttribute('aria-selected', 'true')
      })
    })

    it('clears highlighted index when input changes', async () => {
      const user = userEvent.setup()
      render(<TagAutocomplete {...defaultProps} />)
      const input = screen.getByRole('combobox')

      await user.type(input, 'moth')
      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument()
      })

      await user.keyboard('{ArrowDown}')

      const options = screen.getAllByRole('option')
      expect(options[0]).toHaveAttribute('aria-selected', 'true')

      await user.type(input, 'x')

      await waitFor(() => {
        expect(input).not.toHaveAttribute('aria-activedescendant')
      })
    })
  })
})

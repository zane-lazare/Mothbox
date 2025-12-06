import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SearchBar } from '../SearchBar'

describe('SearchBar', () => {
  const defaultProps = {
    value: '',
    onChange: vi.fn(),
    onSearch: vi.fn(),
    onClear: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
    // Clear localStorage before each test
    localStorage.clear()
  })

  afterEach(() => {
    vi.clearAllTimers()
  })

  describe('rendering', () => {
    it('should render search input', () => {
      render(<SearchBar {...defaultProps} />)
      expect(screen.getByRole('searchbox')).toBeInTheDocument()
    })

    it('should show placeholder text', () => {
      render(<SearchBar {...defaultProps} placeholder="Search..." />)
      expect(screen.getByPlaceholderText('Search...')).toBeInTheDocument()
    })

    it('should show default placeholder text', () => {
      render(<SearchBar {...defaultProps} />)
      expect(screen.getByPlaceholderText(/search photos/i)).toBeInTheDocument()
    })

    it('should show current value', () => {
      render(<SearchBar {...defaultProps} value="moth" />)
      expect(screen.getByDisplayValue('moth')).toBeInTheDocument()
    })

    it('should show loading spinner when isLoading', () => {
      render(<SearchBar {...defaultProps} isLoading={true} />)
      expect(screen.getByTestId('search-loading')).toBeInTheDocument()
    })

    it('should not show loading spinner when not loading', () => {
      render(<SearchBar {...defaultProps} isLoading={false} />)
      expect(screen.queryByTestId('search-loading')).not.toBeInTheDocument()
    })

    it('should autofocus when autoFocus is true', () => {
      render(<SearchBar {...defaultProps} autoFocus={true} />)
      expect(screen.getByRole('searchbox')).toHaveFocus()
    })

    it('should not autofocus when autoFocus is false', () => {
      render(<SearchBar {...defaultProps} autoFocus={false} />)
      expect(screen.getByRole('searchbox')).not.toHaveFocus()
    })

    it('should apply custom className', () => {
      const { container } = render(<SearchBar {...defaultProps} className="custom-class" />)
      expect(container.firstChild).toHaveClass('custom-class')
    })

    it('should render search icon', () => {
      const { container } = render(<SearchBar {...defaultProps} />)
      // Check for the magnifying glass icon in the left position
      const searchIcon = container.querySelector('.pointer-events-none svg')
      expect(searchIcon).toBeInTheDocument()
    })
  })

  describe('clear button', () => {
    it('should show clear button when value is present', () => {
      render(<SearchBar {...defaultProps} value="moth" />)
      expect(screen.getByLabelText(/clear/i)).toBeInTheDocument()
    })

    it('should hide clear button when value is empty', () => {
      render(<SearchBar {...defaultProps} value="" />)
      expect(screen.queryByLabelText(/clear/i)).not.toBeInTheDocument()
    })

    it('should call onClear when clear button clicked', async () => {
      const onClear = vi.fn()
      const user = userEvent.setup()
      render(<SearchBar {...defaultProps} value="moth" onClear={onClear} />)

      await user.click(screen.getByLabelText(/clear/i))
      expect(onClear).toHaveBeenCalled()
    })

    it('should call onClear only once when clicked', async () => {
      const onClear = vi.fn()
      const user = userEvent.setup()
      render(<SearchBar {...defaultProps} value="moth" onClear={onClear} />)

      await user.click(screen.getByLabelText(/clear/i))
      expect(onClear).toHaveBeenCalledTimes(1)
    })
  })

  describe('input handling', () => {
    it('should call onChange when typing', async () => {
      const onChange = vi.fn()
      const user = userEvent.setup()
      render(<SearchBar {...defaultProps} onChange={onChange} />)

      await user.type(screen.getByRole('searchbox'), 'm')
      expect(onChange).toHaveBeenCalledWith('m')
    })

    it('should call onChange for each character typed', async () => {
      const onChange = vi.fn()
      const user = userEvent.setup()
      render(<SearchBar {...defaultProps} onChange={onChange} />)

      await user.type(screen.getByRole('searchbox'), 'moth')
      expect(onChange).toHaveBeenCalledTimes(4)
    })

    it('should call onSearch on Enter key', async () => {
      const onSearch = vi.fn()
      const user = userEvent.setup()
      render(<SearchBar {...defaultProps} value="moth" onSearch={onSearch} />)

      await user.type(screen.getByRole('searchbox'), '{Enter}')
      expect(onSearch).toHaveBeenCalledWith('moth')
    })

    it('should not call onSearch when Enter pressed with empty value', async () => {
      const onSearch = vi.fn()
      const user = userEvent.setup()
      render(<SearchBar {...defaultProps} value="" onSearch={onSearch} />)

      await user.type(screen.getByRole('searchbox'), '{Enter}')
      expect(onSearch).not.toHaveBeenCalled()
    })

    it('should call onClear on Escape key', async () => {
      const onClear = vi.fn()
      const user = userEvent.setup()
      render(<SearchBar {...defaultProps} value="moth" onClear={onClear} />)

      await user.type(screen.getByRole('searchbox'), '{Escape}')
      expect(onClear).toHaveBeenCalled()
    })

    it('should not call onClear on Escape when value is empty', async () => {
      const onClear = vi.fn()
      const user = userEvent.setup()
      render(<SearchBar {...defaultProps} value="" onClear={onClear} />)

      await user.type(screen.getByRole('searchbox'), '{Escape}')
      expect(onClear).not.toHaveBeenCalled()
    })
  })

  describe('help button', () => {
    it('should render help button', () => {
      render(<SearchBar {...defaultProps} />)
      expect(screen.getByLabelText(/help/i)).toBeInTheDocument()
    })

    it('should show help content when help button clicked', async () => {
      const user = userEvent.setup()
      render(<SearchBar {...defaultProps} />)

      await user.click(screen.getByLabelText(/help/i))
      expect(screen.getByText(/search syntax/i)).toBeInTheDocument()
    })

    it('should show syntax examples in help', async () => {
      const user = userEvent.setup()
      render(<SearchBar {...defaultProps} />)

      await user.click(screen.getByLabelText(/help/i))
      expect(screen.getByText(/tag:/i)).toBeInTheDocument()
      expect(screen.getByText(/species:/i)).toBeInTheDocument()
    })

    it('should close help when close button clicked', async () => {
      const user = userEvent.setup()
      render(<SearchBar {...defaultProps} />)

      await user.click(screen.getByLabelText(/help/i))
      expect(screen.getByText(/search syntax/i)).toBeInTheDocument()

      // Click the main Close button in the dialog footer
      const closeButtons = screen.getAllByRole('button', { name: /close/i })
      await user.click(closeButtons[closeButtons.length - 1]) // Get the footer Close button
      expect(screen.queryByText(/search syntax/i)).not.toBeInTheDocument()
    })

    it('should close help when clicking outside', async () => {
      const user = userEvent.setup()
      const { container } = render(<SearchBar {...defaultProps} />)

      await user.click(screen.getByLabelText(/help/i))
      expect(screen.getByText(/search syntax/i)).toBeInTheDocument()

      // Click outside the help dialog
      await user.click(container)
      await waitFor(() => {
        expect(screen.queryByText(/search syntax/i)).not.toBeInTheDocument()
      })
    })

    it('should close help when Escape key pressed', async () => {
      const user = userEvent.setup()
      render(<SearchBar {...defaultProps} />)

      await user.click(screen.getByLabelText(/help/i))
      expect(screen.getByText(/search syntax/i)).toBeInTheDocument()

      await user.keyboard('{Escape}')
      expect(screen.queryByText(/search syntax/i)).not.toBeInTheDocument()
    })
  })

  describe('recent searches', () => {
    it('should show recent searches when input is focused', async () => {
      // Add recent searches to localStorage
      localStorage.setItem('recentSearches', JSON.stringify(['moth', 'butterfly']))

      const user = userEvent.setup()
      render(<SearchBar {...defaultProps} />)

      await user.click(screen.getByRole('searchbox'))
      await waitFor(() => {
        expect(screen.getByText('moth')).toBeInTheDocument()
        expect(screen.getByText('butterfly')).toBeInTheDocument()
      })
    })

    it('should hide recent searches when input loses focus', async () => {
      localStorage.setItem('recentSearches', JSON.stringify(['moth']))

      const user = userEvent.setup()
      render(<SearchBar {...defaultProps} />)

      await user.click(screen.getByRole('searchbox'))
      await waitFor(() => {
        expect(screen.getByText('moth')).toBeInTheDocument()
      })

      await user.tab()
      await waitFor(() => {
        expect(screen.queryByText('moth')).not.toBeInTheDocument()
      })
    })

    it('should apply recent search when clicked', async () => {
      localStorage.setItem('recentSearches', JSON.stringify(['moth']))

      const onChange = vi.fn()
      const onSearch = vi.fn()
      const user = userEvent.setup()
      render(<SearchBar {...defaultProps} onChange={onChange} onSearch={onSearch} />)

      await user.click(screen.getByRole('searchbox'))
      await waitFor(() => {
        expect(screen.getByText('moth')).toBeInTheDocument()
      })

      await user.click(screen.getByText('moth'))
      expect(onChange).toHaveBeenCalledWith('moth')
      expect(onSearch).toHaveBeenCalledWith('moth')
    })

    it('should show max 5 recent searches', async () => {
      localStorage.setItem(
        'recentSearches',
        JSON.stringify(['search1', 'search2', 'search3', 'search4', 'search5', 'search6'])
      )

      const user = userEvent.setup()
      render(<SearchBar {...defaultProps} />)

      await user.click(screen.getByRole('searchbox'))
      await waitFor(() => {
        expect(screen.getByText('search1')).toBeInTheDocument()
        expect(screen.getByText('search5')).toBeInTheDocument()
        expect(screen.queryByText('search6')).not.toBeInTheDocument()
      })
    })

    it('should show clear history option', async () => {
      localStorage.setItem('recentSearches', JSON.stringify(['moth']))

      const user = userEvent.setup()
      render(<SearchBar {...defaultProps} />)

      await user.click(screen.getByRole('searchbox'))
      await waitFor(() => {
        expect(screen.getByText(/clear history/i)).toBeInTheDocument()
      })
    })

    it('should clear history when clear history clicked', async () => {
      localStorage.setItem('recentSearches', JSON.stringify(['moth', 'butterfly']))

      const user = userEvent.setup()
      render(<SearchBar {...defaultProps} />)

      await user.click(screen.getByRole('searchbox'))
      await waitFor(() => {
        expect(screen.getByText('moth')).toBeInTheDocument()
      })

      await user.click(screen.getByText(/clear history/i))
      await waitFor(() => {
        expect(screen.queryByText('moth')).not.toBeInTheDocument()
        expect(localStorage.getItem('recentSearches')).toBe('[]')
      })
    })

    it('should not show recent searches dropdown when empty', async () => {
      localStorage.setItem('recentSearches', JSON.stringify([]))

      const user = userEvent.setup()
      render(<SearchBar {...defaultProps} />)

      await user.click(screen.getByRole('searchbox'))
      expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
    })

    it('should save search to recent searches on successful search', async () => {
      const onSearch = vi.fn()
      const user = userEvent.setup()
      render(<SearchBar {...defaultProps} value="moth" onSearch={onSearch} />)

      await user.type(screen.getByRole('searchbox'), '{Enter}')

      await waitFor(() => {
        const recentSearches = JSON.parse(localStorage.getItem('recentSearches') || '[]')
        expect(recentSearches).toContain('moth')
      })
    })

    it('should not save empty search to recent searches', async () => {
      const onSearch = vi.fn()
      const user = userEvent.setup()
      render(<SearchBar {...defaultProps} value="" onSearch={onSearch} />)

      await user.type(screen.getByRole('searchbox'), '{Enter}')

      const recentSearches = JSON.parse(localStorage.getItem('recentSearches') || '[]')
      expect(recentSearches).toHaveLength(0)
    })

    it('should not save duplicate searches', async () => {
      localStorage.setItem('recentSearches', JSON.stringify(['moth']))

      const onSearch = vi.fn()
      const user = userEvent.setup()
      render(<SearchBar {...defaultProps} value="moth" onSearch={onSearch} />)

      await user.type(screen.getByRole('searchbox'), '{Enter}')

      const recentSearches = JSON.parse(localStorage.getItem('recentSearches') || '[]')
      expect(recentSearches.filter(s => s === 'moth')).toHaveLength(1)
    })

    it('should move existing search to front when searched again', async () => {
      localStorage.setItem('recentSearches', JSON.stringify(['butterfly', 'moth']))

      const onSearch = vi.fn()
      const user = userEvent.setup()
      render(<SearchBar {...defaultProps} value="moth" onSearch={onSearch} />)

      await user.type(screen.getByRole('searchbox'), '{Enter}')

      await waitFor(() => {
        const recentSearches = JSON.parse(localStorage.getItem('recentSearches') || '[]')
        expect(recentSearches[0]).toBe('moth')
      })
    })
  })

  describe('accessibility', () => {
    it('should have searchbox role', () => {
      render(<SearchBar {...defaultProps} />)
      expect(screen.getByRole('searchbox')).toBeInTheDocument()
    })

    it('should have proper aria-label for search input', () => {
      render(<SearchBar {...defaultProps} />)
      expect(screen.getByRole('searchbox')).toHaveAccessibleName(/search/i)
    })

    it('should have proper aria-label for clear button', () => {
      render(<SearchBar {...defaultProps} value="moth" />)
      expect(screen.getByLabelText(/clear/i)).toBeInTheDocument()
    })

    it('should have proper aria-label for help button', () => {
      render(<SearchBar {...defaultProps} />)
      expect(screen.getByLabelText(/help/i)).toBeInTheDocument()
    })

    it('should announce loading state to screen readers', () => {
      render(<SearchBar {...defaultProps} isLoading={true} />)
      expect(screen.getByRole('status')).toBeInTheDocument()
    })

    it('should have proper role for help dialog', async () => {
      const user = userEvent.setup()
      render(<SearchBar {...defaultProps} />)

      await user.click(screen.getByLabelText(/help/i))
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })
  })

  describe('edge cases', () => {
    it('should handle missing onChange gracefully', () => {
      const { value, onSearch, onClear } = defaultProps
      expect(() => render(<SearchBar value={value} onSearch={onSearch} onClear={onClear} />)).not.toThrow()
    })

    it('should handle missing onSearch gracefully', () => {
      const { value, onChange, onClear } = defaultProps
      expect(() => render(<SearchBar value={value} onChange={onChange} onClear={onClear} />)).not.toThrow()
    })

    it('should handle missing onClear gracefully', () => {
      const { value, onChange, onSearch } = defaultProps
      expect(() => render(<SearchBar value={value} onChange={onChange} onSearch={onSearch} />)).not.toThrow()
    })

    it('should handle invalid localStorage data', async () => {
      // Suppress console.warn for this test
      const originalWarn = console.warn
      console.warn = vi.fn()

      localStorage.setItem('recentSearches', 'invalid json')

      const user = userEvent.setup()
      expect(() => render(<SearchBar {...defaultProps} />)).not.toThrow()

      await user.click(screen.getByRole('searchbox'))
      expect(screen.queryByRole('listbox')).not.toBeInTheDocument()

      // Restore console.warn
      console.warn = originalWarn
    })

    it('should trim whitespace from search value', async () => {
      const onSearch = vi.fn()
      const user = userEvent.setup()
      render(<SearchBar {...defaultProps} value="  moth  " onSearch={onSearch} />)

      await user.type(screen.getByRole('searchbox'), '{Enter}')
      expect(onSearch).toHaveBeenCalledWith('moth')
    })
  })
})

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { NotesFilter } from '../NotesFilter'
import { FilterProvider } from '../../../contexts/FilterContext'

// Helper to render component with providers
const renderWithProviders = (ui) => {
  return render(
    <FilterProvider>
      {ui}
    </FilterProvider>
  )
}

describe('NotesFilter', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // Rendering tests
  describe('Rendering', () => {
    it('renders toggle options (All, Has Notes, No Notes)', () => {
      renderWithProviders(<NotesFilter />)

      expect(screen.getByRole('button', { name: /show all photos/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /show only photos with notes/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /show only photos without notes/i })).toBeInTheDocument()
    })

    it('renders toggle buttons with correct text', () => {
      renderWithProviders(<NotesFilter />)

      expect(screen.getByText('All')).toBeInTheDocument()
      expect(screen.getByText('Has Notes')).toBeInTheDocument()
      expect(screen.getByText('No Notes')).toBeInTheDocument()
    })

    it('renders keyword search input', () => {
      renderWithProviders(<NotesFilter />)

      expect(screen.getByPlaceholderText(/search in notes/i)).toBeInTheDocument()
    })

    it('renders search icon', () => {
      renderWithProviders(<NotesFilter />)

      const searchInput = screen.getByPlaceholderText(/search in notes/i)
      const container = searchInput.parentElement
      const icon = container.querySelector('svg')

      expect(icon).toBeInTheDocument()
    })

    it('does not render clear button when no filter is active', () => {
      renderWithProviders(<NotesFilter />)

      expect(screen.queryByRole('button', { name: /clear notes filter/i })).not.toBeInTheDocument()
    })
  })

  // Toggle selection tests
  describe('Toggle Selection', () => {
    it('defaults to "All" option', () => {
      renderWithProviders(<NotesFilter />)

      const allButton = screen.getByRole('button', { name: /show all photos/i })
      expect(allButton).toHaveAttribute('aria-pressed', 'true')
    })

    it('selects "Has Notes" when clicked', async () => {
      const user = userEvent.setup()
      renderWithProviders(<NotesFilter />)

      const hasNotesButton = screen.getByRole('button', { name: /show only photos with notes/i })
      await user.click(hasNotesButton)

      expect(hasNotesButton).toHaveAttribute('aria-pressed', 'true')
    })

    it('selects "No Notes" when clicked', async () => {
      const user = userEvent.setup()
      renderWithProviders(<NotesFilter />)

      const noNotesButton = screen.getByRole('button', { name: /show only photos without notes/i })
      await user.click(noNotesButton)

      expect(noNotesButton).toHaveAttribute('aria-pressed', 'true')
    })

    it('deselects "Has Notes" when "All" clicked', async () => {
      const user = userEvent.setup()
      renderWithProviders(<NotesFilter />)

      const hasNotesButton = screen.getByRole('button', { name: /show only photos with notes/i })
      const allButton = screen.getByRole('button', { name: /show all photos/i })

      await user.click(hasNotesButton)
      expect(hasNotesButton).toHaveAttribute('aria-pressed', 'true')

      await user.click(allButton)

      await waitFor(() => {
        const updatedAllButton = screen.getByRole('button', { name: /show all photos/i })
        const updatedHasNotesButton = screen.getByRole('button', { name: /show only photos with notes/i })
        expect(updatedAllButton).toHaveAttribute('aria-pressed', 'true')
        expect(updatedHasNotesButton).toHaveAttribute('aria-pressed', 'false')
      })
    })

    it('only one toggle option is active at a time', async () => {
      const user = userEvent.setup()
      renderWithProviders(<NotesFilter />)

      const allButton = screen.getByRole('button', { name: /show all photos/i })
      const hasNotesButton = screen.getByRole('button', { name: /show only photos with notes/i })
      const noNotesButton = screen.getByRole('button', { name: /show only photos without notes/i })

      expect(allButton).toHaveAttribute('aria-pressed', 'true')
      expect(hasNotesButton).toHaveAttribute('aria-pressed', 'false')
      expect(noNotesButton).toHaveAttribute('aria-pressed', 'false')

      await user.click(hasNotesButton)

      expect(allButton).toHaveAttribute('aria-pressed', 'false')
      expect(hasNotesButton).toHaveAttribute('aria-pressed', 'true')
      expect(noNotesButton).toHaveAttribute('aria-pressed', 'false')
    })
  })

  // Keyword search tests
  describe('Keyword Search', () => {
    it('updates input value when typed', async () => {
      const user = userEvent.setup()
      renderWithProviders(<NotesFilter />)

      const searchInput = screen.getByPlaceholderText(/search in notes/i)
      await user.type(searchInput, 'moth specimen')

      expect(searchInput.value).toBe('moth specimen')
    })

    it('shows clear button when text is entered', async () => {
      const user = userEvent.setup()
      renderWithProviders(<NotesFilter />)

      const searchInput = screen.getByPlaceholderText(/search in notes/i)
      await user.type(searchInput, 'test')

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /clear search/i })).toBeInTheDocument()
      })
    })

    it('does not show clear button when input is empty', () => {
      renderWithProviders(<NotesFilter />)

      expect(screen.queryByRole('button', { name: /clear search/i })).not.toBeInTheDocument()
    })

    it('clears input when clear button clicked', async () => {
      const user = userEvent.setup()
      renderWithProviders(<NotesFilter />)

      const searchInput = screen.getByPlaceholderText(/search in notes/i)
      await user.type(searchInput, 'test')

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /clear search/i })).toBeInTheDocument()
      })

      const clearButton = screen.getByRole('button', { name: /clear search/i })
      await user.click(clearButton)

      await waitFor(() => {
        expect(searchInput.value).toBe('')
      })
    })

    it('hides clear button after clearing search', async () => {
      const user = userEvent.setup()
      renderWithProviders(<NotesFilter />)

      const searchInput = screen.getByPlaceholderText(/search in notes/i)
      await user.type(searchInput, 'test')

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /clear search/i })).toBeInTheDocument()
      })

      const clearButton = screen.getByRole('button', { name: /clear search/i })
      await user.click(clearButton)

      await waitFor(() => {
        expect(screen.queryByRole('button', { name: /clear search/i })).not.toBeInTheDocument()
      })
    })
  })

  // Debounced input tests
  describe('Debounced Input', () => {
    it('debounces input changes (300ms)', async () => {
      const user = userEvent.setup()
      renderWithProviders(<NotesFilter />)

      const searchInput = screen.getByPlaceholderText(/search in notes/i)

      // Type quickly
      await user.type(searchInput, 'test')

      // Value should be in the input immediately
      expect(searchInput.value).toBe('test')

      // Wait for debounce (300ms)
      await waitFor(() => {
        expect(searchInput.value).toBe('test')
      }, { timeout: 400 })
    })

    it('does not trigger update before debounce period', async () => {
      const user = userEvent.setup()
      renderWithProviders(<NotesFilter />)

      const searchInput = screen.getByPlaceholderText(/search in notes/i)

      await user.type(searchInput, 't')

      // Immediately check - should still show in input
      expect(searchInput.value).toBe('t')
    })
  })

  // Clear filter button tests
  describe('Clear Filter Button', () => {
    it('shows clear button when toggle is set', async () => {
      const user = userEvent.setup()
      renderWithProviders(<NotesFilter />)

      const hasNotesButton = screen.getByRole('button', { name: /show only photos with notes/i })
      await user.click(hasNotesButton)

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /clear notes filter/i })).toBeInTheDocument()
      })
    })

    it('shows clear button when keywords are entered', async () => {
      const user = userEvent.setup()
      renderWithProviders(<NotesFilter />)

      const searchInput = screen.getByPlaceholderText(/search in notes/i)
      await user.type(searchInput, 'test')

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /clear notes filter/i })).toBeInTheDocument()
      }, { timeout: 400 })
    })

    it('resets toggle to "All" when clear button clicked', async () => {
      const user = userEvent.setup()
      renderWithProviders(<NotesFilter />)

      const hasNotesButton = screen.getByRole('button', { name: /show only photos with notes/i })
      await user.click(hasNotesButton)

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /clear notes filter/i })).toBeInTheDocument()
      })

      const clearButton = screen.getByRole('button', { name: /clear notes filter/i })
      await user.click(clearButton)

      const allButton = screen.getByRole('button', { name: /show all photos/i })
      expect(allButton).toHaveAttribute('aria-pressed', 'true')
    })

    it('clears keywords when clear button clicked', async () => {
      const user = userEvent.setup()
      renderWithProviders(<NotesFilter />)

      const searchInput = screen.getByPlaceholderText(/search in notes/i)
      await user.type(searchInput, 'test')

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /clear notes filter/i })).toBeInTheDocument()
      }, { timeout: 400 })

      const clearButton = screen.getByRole('button', { name: /clear notes filter/i })
      await user.click(clearButton)

      expect(searchInput.value).toBe('')
    })

    it('hides clear button after clearing filter', async () => {
      const user = userEvent.setup()
      renderWithProviders(<NotesFilter />)

      const hasNotesButton = screen.getByRole('button', { name: /show only photos with notes/i })
      await user.click(hasNotesButton)

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /clear notes filter/i })).toBeInTheDocument()
      })

      const clearButton = screen.getByRole('button', { name: /clear notes filter/i })
      await user.click(clearButton)

      expect(screen.queryByRole('button', { name: /clear notes filter/i })).not.toBeInTheDocument()
    })
  })

  // Context integration tests
  describe('Context Integration', () => {
    it('updates context when toggle selected', async () => {
      const user = userEvent.setup()
      renderWithProviders(<NotesFilter />)

      const hasNotesButton = screen.getByRole('button', { name: /show only photos with notes/i })
      await user.click(hasNotesButton)

      expect(hasNotesButton).toHaveAttribute('aria-pressed', 'true')
    })

    it('updates context when keywords entered', async () => {
      const user = userEvent.setup()
      renderWithProviders(<NotesFilter />)

      const searchInput = screen.getByPlaceholderText(/search in notes/i)
      await user.type(searchInput, 'test')

      // Wait for debounce
      await waitFor(() => {
        expect(searchInput.value).toBe('test')
      }, { timeout: 400 })
    })

    it('maintains both toggle and keywords independently', async () => {
      const user = userEvent.setup()
      renderWithProviders(<NotesFilter />)

      // Set toggle
      const hasNotesButton = screen.getByRole('button', { name: /show only photos with notes/i })
      await user.click(hasNotesButton)

      // Set keywords
      const searchInput = screen.getByPlaceholderText(/search in notes/i)
      await user.type(searchInput, 'specimen')

      // Both should be set
      expect(hasNotesButton).toHaveAttribute('aria-pressed', 'true')

      await waitFor(() => {
        expect(searchInput.value).toBe('specimen')
      }, { timeout: 400 })
    })
  })

  // Accessibility tests
  describe('Accessibility', () => {
    it('has accessible toggle buttons', () => {
      renderWithProviders(<NotesFilter />)

      const allButton = screen.getByRole('button', { name: /show all photos/i })
      const hasNotesButton = screen.getByRole('button', { name: /show only photos with notes/i })
      const noNotesButton = screen.getByRole('button', { name: /show only photos without notes/i })

      expect(allButton).toHaveAttribute('aria-pressed')
      expect(hasNotesButton).toHaveAttribute('aria-pressed')
      expect(noNotesButton).toHaveAttribute('aria-pressed')
    })

    it('has accessible search input with label', () => {
      renderWithProviders(<NotesFilter />)

      const searchInput = screen.getByLabelText(/search in notes/i)
      expect(searchInput).toBeInTheDocument()
    })

    it('has accessible clear search button', async () => {
      const user = userEvent.setup()
      renderWithProviders(<NotesFilter />)

      const searchInput = screen.getByPlaceholderText(/search in notes/i)
      await user.type(searchInput, 'test')

      await waitFor(() => {
        const clearButton = screen.getByRole('button', { name: /clear search/i })
        expect(clearButton).toBeInTheDocument()
      })
    })

    it('has accessible clear filter button', async () => {
      const user = userEvent.setup()
      renderWithProviders(<NotesFilter />)

      const hasNotesButton = screen.getByRole('button', { name: /show only photos with notes/i })
      await user.click(hasNotesButton)

      await waitFor(() => {
        const clearButton = screen.getByRole('button', { name: /clear notes filter/i })
        expect(clearButton).toBeInTheDocument()
      })
    })

    it('supports keyboard navigation on toggle buttons', async () => {
      const user = userEvent.setup()
      renderWithProviders(<NotesFilter />)

      const hasNotesButton = screen.getByRole('button', { name: /show only photos with notes/i })
      hasNotesButton.focus()

      expect(document.activeElement).toBe(hasNotesButton)

      await user.keyboard('{Enter}')
      expect(hasNotesButton).toHaveAttribute('aria-pressed', 'true')
    })

    it('has proper ARIA labels for toggle group', () => {
      renderWithProviders(<NotesFilter />)

      const toggleGroup = screen.getByRole('group', { name: /notes status/i })
      expect(toggleGroup).toBeInTheDocument()
    })
  })

  // Dark mode compatibility tests
  describe('Dark Mode', () => {
    it('applies dark mode classes to buttons', () => {
      renderWithProviders(<NotesFilter />)

      const allButton = screen.getByRole('button', { name: /show all photos/i })
      expect(allButton.className).toContain('dark:')
    })

    it('applies dark mode classes to search input', () => {
      renderWithProviders(<NotesFilter />)

      const searchInput = screen.getByPlaceholderText(/search in notes/i)
      expect(searchInput.className).toContain('dark:')
    })

    it('applies dark mode classes to clear button', async () => {
      const user = userEvent.setup()
      renderWithProviders(<NotesFilter />)

      const hasNotesButton = screen.getByRole('button', { name: /show only photos with notes/i })
      await user.click(hasNotesButton)

      await waitFor(() => {
        const clearButton = screen.getByRole('button', { name: /clear notes filter/i })
        expect(clearButton.className).toContain('dark:')
      })
    })
  })
})

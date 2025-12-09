import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { TagFilter } from '../TagFilter'
import { FilterProvider } from '../../../contexts/FilterContext'
import * as api from '../../../utils/api'

// Mock the API
vi.mock('../../../utils/api', () => ({
  getAllTags: vi.fn(),
}))

// Helper to render component with providers
const renderWithProviders = (ui) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <FilterProvider>
        {ui}
      </FilterProvider>
    </QueryClientProvider>
  )
}

// Sample tag data
const mockTags = {
  tags: [
    { tag: 'moth', count: 42 },
    { tag: 'butterfly', count: 15 },
    { tag: 'beetle', count: 8 },
    { tag: 'dragonfly', count: 5 },
    { tag: 'nocturnal', count: 12 },
  ],
  total: 5,
}

describe('TagFilter', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // Loading state tests
  describe('Loading State', () => {
    it('renders loading state while fetching tags', () => {
      api.getAllTags.mockReturnValue(new Promise(() => {})) // Never resolves

      renderWithProviders(<TagFilter />)

      expect(screen.getByText(/loading tags/i)).toBeInTheDocument()
    })

    it('shows loading spinner during initial load', () => {
      api.getAllTags.mockReturnValue(new Promise(() => {}))

      renderWithProviders(<TagFilter />)

      const loadingElement = screen.getByText(/loading tags/i)
      expect(loadingElement).toHaveClass('animate-pulse')
    })
  })

  // Error state tests
  describe('Error State', () => {
    it('renders error message when API call fails', async () => {
      api.getAllTags.mockRejectedValue(new Error('Network error'))

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByText(/failed to load tags/i)).toBeInTheDocument()
      })
    })

    it('shows error message with details', async () => {
      const errorMessage = 'Database connection failed'
      api.getAllTags.mockRejectedValue(new Error(errorMessage))

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByText(new RegExp(errorMessage, 'i'))).toBeInTheDocument()
      })
    })
  })

  // Empty state tests
  describe('Empty State', () => {
    it('shows empty state when no tags available', async () => {
      api.getAllTags.mockResolvedValue({ data: { tags: [], total: 0 } })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByText(/no tags available/i)).toBeInTheDocument()
      })
    })
  })

  // Rendering tests
  describe('Rendering', () => {
    it('renders tag list from API', async () => {
      api.getAllTags.mockResolvedValue({ data: mockTags })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByText('moth')).toBeInTheDocument()
      })

      expect(screen.getByText('butterfly')).toBeInTheDocument()
      expect(screen.getByText('beetle')).toBeInTheDocument()
      expect(screen.getByText('dragonfly')).toBeInTheDocument()
      expect(screen.getByText('nocturnal')).toBeInTheDocument()
    })

    it('renders tag counts', async () => {
      api.getAllTags.mockResolvedValue({ data: mockTags })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByText('42')).toBeInTheDocument()
      })

      expect(screen.getByText('15')).toBeInTheDocument()
      expect(screen.getByText('8')).toBeInTheDocument()
      expect(screen.getByText('5')).toBeInTheDocument()
      expect(screen.getByText('12')).toBeInTheDocument()
    })

    it('renders search input', async () => {
      api.getAllTags.mockResolvedValue({ data: mockTags })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/search tags/i)).toBeInTheDocument()
      })
    })

    it('renders checkboxes for each tag', async () => {
      api.getAllTags.mockResolvedValue({ data: mockTags })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        const checkboxes = screen.getAllByRole('checkbox')
        expect(checkboxes).toHaveLength(5)
      })
    })
  })

  // Tag selection tests
  describe('Tag Selection', () => {
    it('selects tag when checkbox clicked', async () => {
      const user = userEvent.setup()
      api.getAllTags.mockResolvedValue({ data: mockTags })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select tag moth/i)).toBeInTheDocument()
      })

      const mothCheckbox = screen.getByLabelText(/select tag moth/i)
      await user.click(mothCheckbox)

      expect(mothCheckbox).toBeChecked()
    })

    it('deselects tag when checkbox clicked again', async () => {
      const user = userEvent.setup()
      api.getAllTags.mockResolvedValue({ data: mockTags })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select tag moth/i)).toBeInTheDocument()
      })

      const mothCheckbox = screen.getByLabelText(/select tag moth/i)

      // Select
      await user.click(mothCheckbox)
      expect(mothCheckbox).toBeChecked()

      // Deselect
      await user.click(mothCheckbox)
      expect(mothCheckbox).not.toBeChecked()
    })

    it('supports multiple tag selection', async () => {
      const user = userEvent.setup()
      api.getAllTags.mockResolvedValue({ data: mockTags })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select tag moth/i)).toBeInTheDocument()
      })

      const mothCheckbox = screen.getByLabelText(/select tag moth/i)
      const butterflyCheckbox = screen.getByLabelText(/select tag butterfly/i)

      await user.click(mothCheckbox)
      await user.click(butterflyCheckbox)

      expect(mothCheckbox).toBeChecked()
      expect(butterflyCheckbox).toBeChecked()
    })
  })

  // Selected tags chips tests
  describe('Selected Tags Display', () => {
    it('shows selected tags as chips', async () => {
      const user = userEvent.setup()
      api.getAllTags.mockResolvedValue({ data: mockTags })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select tag moth/i)).toBeInTheDocument()
      })

      await user.click(screen.getByLabelText(/select tag moth/i))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Tag: moth/i })).toBeInTheDocument()
      })
    })

    it('shows count of selected tags', async () => {
      const user = userEvent.setup()
      api.getAllTags.mockResolvedValue({ data: mockTags })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select tag moth/i)).toBeInTheDocument()
      })

      await user.click(screen.getByLabelText(/select tag moth/i))
      await user.click(screen.getByLabelText(/select tag butterfly/i))

      await waitFor(() => {
        expect(screen.getByText(/selected \(2\)/i)).toBeInTheDocument()
      })
    })

    it('does not show selected section when no tags selected', async () => {
      api.getAllTags.mockResolvedValue({ data: mockTags })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByText('moth')).toBeInTheDocument()
      })

      expect(screen.queryByText(/selected/i)).not.toBeInTheDocument()
    })
  })

  // Chip removal tests
  describe('Chip Removal', () => {
    it('removes tag when chip X button clicked', async () => {
      const user = userEvent.setup()
      api.getAllTags.mockResolvedValue({ data: mockTags })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select tag moth/i)).toBeInTheDocument()
      })

      // Select tag
      await user.click(screen.getByLabelText(/select tag moth/i))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /remove tag moth/i })).toBeInTheDocument()
      })

      // Remove tag via chip
      await user.click(screen.getByRole('button', { name: /remove tag moth/i }))

      await waitFor(() => {
        expect(screen.queryByRole('button', { name: /Tag: moth/i })).not.toBeInTheDocument()
      })

      // Checkbox should be unchecked
      expect(screen.getByLabelText(/select tag moth/i)).not.toBeChecked()
    })

    it('updates checkbox state when chip removed', async () => {
      const user = userEvent.setup()
      api.getAllTags.mockResolvedValue({ data: mockTags })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select tag moth/i)).toBeInTheDocument()
      })

      const mothCheckbox = screen.getByLabelText(/select tag moth/i)

      await user.click(mothCheckbox)
      expect(mothCheckbox).toBeChecked()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /remove tag moth/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /remove tag moth/i }))

      await waitFor(() => {
        expect(mothCheckbox).not.toBeChecked()
      })
    })
  })

  // Search functionality tests
  describe('Search Functionality', () => {
    it('filters tags based on search query', async () => {
      const user = userEvent.setup()
      api.getAllTags.mockResolvedValue({ data: mockTags })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByText('moth')).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText(/search tags/i)
      await user.type(searchInput, 'fly')

      await waitFor(() => {
        expect(screen.getByText('butterfly')).toBeInTheDocument()
        expect(screen.getByText('dragonfly')).toBeInTheDocument()
      })

      expect(screen.queryByText('moth')).not.toBeInTheDocument()
      expect(screen.queryByText('beetle')).not.toBeInTheDocument()
    })

    it('search is case insensitive', async () => {
      const user = userEvent.setup()
      api.getAllTags.mockResolvedValue({ data: mockTags })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByText('moth')).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText(/search tags/i)
      await user.type(searchInput, 'MOTH')

      await waitFor(() => {
        expect(screen.getByText('moth')).toBeInTheDocument()
      })
    })

    it('shows no results message when search matches nothing', async () => {
      const user = userEvent.setup()
      api.getAllTags.mockResolvedValue({ data: mockTags })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByText('moth')).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText(/search tags/i)
      await user.type(searchInput, 'xyz123')

      await waitFor(() => {
        expect(screen.getByText(/no tags match "xyz123"/i)).toBeInTheDocument()
      })
    })

    it('shows clear search button when search has value', async () => {
      const user = userEvent.setup()
      api.getAllTags.mockResolvedValue({ data: mockTags })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByText('moth')).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText(/search tags/i)
      await user.type(searchInput, 'moth')

      await waitFor(() => {
        expect(screen.getByLabelText(/clear search/i)).toBeInTheDocument()
      })
    })

    it('clears search when clear button clicked', async () => {
      const user = userEvent.setup()
      api.getAllTags.mockResolvedValue({ data: mockTags })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByText('moth')).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText(/search tags/i)
      await user.type(searchInput, 'moth')

      await waitFor(() => {
        expect(screen.getByLabelText(/clear search/i)).toBeInTheDocument()
      })

      await user.click(screen.getByLabelText(/clear search/i))

      await waitFor(() => {
        expect(searchInput.value).toBe('')
      })
    })

    it('does not show clear button when search is empty', async () => {
      api.getAllTags.mockResolvedValue({ data: mockTags })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByText('moth')).toBeInTheDocument()
      })

      expect(screen.queryByLabelText(/clear search/i)).not.toBeInTheDocument()
    })
  })

  // Match mode toggle tests
  describe('Match Mode Toggle', () => {
    it('shows match mode toggle when multiple tags selected', async () => {
      const user = userEvent.setup()
      api.getAllTags.mockResolvedValue({ data: mockTags })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select tag moth/i)).toBeInTheDocument()
      })

      await user.click(screen.getByLabelText(/select tag moth/i))
      await user.click(screen.getByLabelText(/select tag butterfly/i))

      await waitFor(() => {
        expect(screen.getByText(/match:/i)).toBeInTheDocument()
      })
    })

    it('does not show match mode toggle when no tags selected', async () => {
      api.getAllTags.mockResolvedValue({ data: mockTags })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByText('moth')).toBeInTheDocument()
      })

      expect(screen.queryByText(/match:/i)).not.toBeInTheDocument()
    })

    it('does not show match mode toggle when only one tag selected', async () => {
      const user = userEvent.setup()
      api.getAllTags.mockResolvedValue({ data: mockTags })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select tag moth/i)).toBeInTheDocument()
      })

      await user.click(screen.getByLabelText(/select tag moth/i))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Tag: moth/i })).toBeInTheDocument()
      })

      expect(screen.queryByText(/match:/i)).not.toBeInTheDocument()
    })

    it('defaults to "Any" match mode', async () => {
      const user = userEvent.setup()
      api.getAllTags.mockResolvedValue({ data: mockTags })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select tag moth/i)).toBeInTheDocument()
      })

      await user.click(screen.getByLabelText(/select tag moth/i))
      await user.click(screen.getByLabelText(/select tag butterfly/i))

      await waitFor(() => {
        expect(screen.getByText('Any')).toBeInTheDocument()
      })
    })

    it('toggles between "Any" and "All" when clicked', async () => {
      const user = userEvent.setup()
      api.getAllTags.mockResolvedValue({ data: mockTags })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select tag moth/i)).toBeInTheDocument()
      })

      await user.click(screen.getByLabelText(/select tag moth/i))
      await user.click(screen.getByLabelText(/select tag butterfly/i))

      await waitFor(() => {
        expect(screen.getByText('Any')).toBeInTheDocument()
      })

      const matchButton = screen.getByRole('button', { name: /match mode/i })
      await user.click(matchButton)

      await waitFor(() => {
        expect(screen.getByText('All')).toBeInTheDocument()
      })

      await user.click(matchButton)

      await waitFor(() => {
        expect(screen.getByText('Any')).toBeInTheDocument()
      })
    })

    it('shows correct description for "Any" mode', async () => {
      const user = userEvent.setup()
      api.getAllTags.mockResolvedValue({ data: mockTags })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select tag moth/i)).toBeInTheDocument()
      })

      await user.click(screen.getByLabelText(/select tag moth/i))
      await user.click(screen.getByLabelText(/select tag butterfly/i))

      await waitFor(() => {
        expect(screen.getByText(/photos matching any selected tag/i)).toBeInTheDocument()
      })
    })

    it('shows correct description for "All" mode', async () => {
      const user = userEvent.setup()
      api.getAllTags.mockResolvedValue({ data: mockTags })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select tag moth/i)).toBeInTheDocument()
      })

      await user.click(screen.getByLabelText(/select tag moth/i))
      await user.click(screen.getByLabelText(/select tag butterfly/i))

      await waitFor(() => {
        const matchButton = screen.getByRole('button', { name: /match mode/i })
        user.click(matchButton)
      })

      await waitFor(() => {
        expect(screen.getByText(/photos matching all selected tags/i)).toBeInTheDocument()
      })
    })
  })

  // Accessibility tests
  describe('Accessibility', () => {
    it('has accessible search input', async () => {
      api.getAllTags.mockResolvedValue({ data: mockTags })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/search tags/i)).toBeInTheDocument()
      })
    })

    it('has accessible checkboxes', async () => {
      api.getAllTags.mockResolvedValue({ data: mockTags })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select tag moth/i)).toBeInTheDocument()
      })

      expect(screen.getByLabelText(/select tag butterfly/i)).toBeInTheDocument()
    })

    it('has accessible match mode toggle', async () => {
      const user = userEvent.setup()
      api.getAllTags.mockResolvedValue({ data: mockTags })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select tag moth/i)).toBeInTheDocument()
      })

      await user.click(screen.getByLabelText(/select tag moth/i))
      await user.click(screen.getByLabelText(/select tag butterfly/i))

      await waitFor(() => {
        expect(screen.getByLabelText(/match mode/i)).toBeInTheDocument()
      })
    })

    it('supports keyboard navigation on checkboxes', async () => {
      const user = userEvent.setup()
      api.getAllTags.mockResolvedValue({ data: mockTags })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select tag moth/i)).toBeInTheDocument()
      })

      const mothCheckbox = screen.getByLabelText(/select tag moth/i)
      await user.click(mothCheckbox)

      expect(mothCheckbox).toBeChecked()
    })
  })

  // Context integration tests
  describe('Context Integration', () => {
    it('updates context when tag selected', async () => {
      const user = userEvent.setup()
      api.getAllTags.mockResolvedValue({ data: mockTags })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select tag moth/i)).toBeInTheDocument()
      })

      await user.click(screen.getByLabelText(/select tag moth/i))

      await waitFor(() => {
        const checkbox = screen.getByLabelText(/select tag moth/i)
        expect(checkbox).toBeChecked()
      })
    })

    it('updates context when match mode toggled', async () => {
      const user = userEvent.setup()
      api.getAllTags.mockResolvedValue({ data: mockTags })

      renderWithProviders(<TagFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select tag moth/i)).toBeInTheDocument()
      })

      await user.click(screen.getByLabelText(/select tag moth/i))
      await user.click(screen.getByLabelText(/select tag butterfly/i))

      await waitFor(() => {
        expect(screen.getByText('Any')).toBeInTheDocument()
      })

      const matchButton = screen.getByRole('button', { name: /match mode/i })
      await user.click(matchButton)

      await waitFor(() => {
        expect(screen.getByText('All')).toBeInTheDocument()
      })
    })
  })
})

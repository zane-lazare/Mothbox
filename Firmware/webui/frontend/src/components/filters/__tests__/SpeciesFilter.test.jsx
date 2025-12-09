import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { SpeciesFilter } from '../SpeciesFilter'
import { FilterProvider } from '../../../contexts/FilterContext'
import * as api from '../../../utils/api'

// Mock the API
vi.mock('../../../utils/api', () => ({
  getAllSpecies: vi.fn(),
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

// Sample species data
const mockSpecies = {
  species: [
    { name: 'Actias luna', count: 42 },
    { name: 'Danaus plexippus', count: 15 },
    { name: 'Papilio glaucus', count: 8 },
    { name: 'Hyalophora cecropia', count: 5 },
    { name: 'Vanessa cardui', count: 12 },
  ],
  total: 5,
}

describe('SpeciesFilter', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // Loading state tests
  describe('Loading State', () => {
    it('renders loading state while fetching species', () => {
      api.getAllSpecies.mockReturnValue(new Promise(() => {})) // Never resolves

      renderWithProviders(<SpeciesFilter />)

      expect(screen.getByText(/loading species/i)).toBeInTheDocument()
    })

    it('shows loading spinner during initial load', () => {
      api.getAllSpecies.mockReturnValue(new Promise(() => {}))

      renderWithProviders(<SpeciesFilter />)

      const loadingElement = screen.getByText(/loading species/i)
      expect(loadingElement).toHaveClass('animate-pulse')
    })
  })

  // Error state tests
  describe('Error State', () => {
    it('renders error message when API call fails', async () => {
      api.getAllSpecies.mockRejectedValue(new Error('Network error'))

      renderWithProviders(<SpeciesFilter />)

      await waitFor(() => {
        expect(screen.getByText(/failed to load species/i)).toBeInTheDocument()
      })
    })

    it('shows error message with details', async () => {
      const errorMessage = 'Database connection failed'
      api.getAllSpecies.mockRejectedValue(new Error(errorMessage))

      renderWithProviders(<SpeciesFilter />)

      await waitFor(() => {
        expect(screen.getByText(new RegExp(errorMessage, 'i'))).toBeInTheDocument()
      })
    })
  })

  // Empty state tests
  describe('Empty State', () => {
    it('shows empty state when no species available', async () => {
      api.getAllSpecies.mockResolvedValue({ data: { species: [], total: 0 } })

      renderWithProviders(<SpeciesFilter />)

      await waitFor(() => {
        expect(screen.getByText(/no species available/i)).toBeInTheDocument()
      })
    })
  })

  // Rendering tests
  describe('Rendering', () => {
    it('renders species list from API', async () => {
      api.getAllSpecies.mockResolvedValue({ data: mockSpecies })

      renderWithProviders(<SpeciesFilter />)

      await waitFor(() => {
        expect(screen.getByText('Actias luna')).toBeInTheDocument()
      })

      expect(screen.getByText('Danaus plexippus')).toBeInTheDocument()
      expect(screen.getByText('Papilio glaucus')).toBeInTheDocument()
      expect(screen.getByText('Hyalophora cecropia')).toBeInTheDocument()
      expect(screen.getByText('Vanessa cardui')).toBeInTheDocument()
    })

    it('renders species counts', async () => {
      api.getAllSpecies.mockResolvedValue({ data: mockSpecies })

      renderWithProviders(<SpeciesFilter />)

      await waitFor(() => {
        expect(screen.getByText('42')).toBeInTheDocument()
      })

      expect(screen.getByText('15')).toBeInTheDocument()
      expect(screen.getByText('8')).toBeInTheDocument()
      expect(screen.getByText('5')).toBeInTheDocument()
      expect(screen.getByText('12')).toBeInTheDocument()
    })

    it('renders search input', async () => {
      api.getAllSpecies.mockResolvedValue({ data: mockSpecies })

      renderWithProviders(<SpeciesFilter />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/search species/i)).toBeInTheDocument()
      })
    })

    it('renders checkboxes for each species', async () => {
      api.getAllSpecies.mockResolvedValue({ data: mockSpecies })

      renderWithProviders(<SpeciesFilter />)

      await waitFor(() => {
        // 5 species + 1 unidentified checkbox = 6 total
        const checkboxes = screen.getAllByRole('checkbox')
        expect(checkboxes).toHaveLength(6)
      })
    })

    it('renders include unidentified checkbox', async () => {
      api.getAllSpecies.mockResolvedValue({ data: mockSpecies })

      renderWithProviders(<SpeciesFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/include unidentified photos/i)).toBeInTheDocument()
      })
    })
  })

  // Species selection tests
  describe('Species Selection', () => {
    it('selects species when checkbox clicked', async () => {
      const user = userEvent.setup()
      api.getAllSpecies.mockResolvedValue({ data: mockSpecies })

      renderWithProviders(<SpeciesFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select species actias luna/i)).toBeInTheDocument()
      })

      const lunaCheckbox = screen.getByLabelText(/select species actias luna/i)
      await user.click(lunaCheckbox)

      expect(lunaCheckbox).toBeChecked()
    })

    it('deselects species when checkbox clicked again', async () => {
      const user = userEvent.setup()
      api.getAllSpecies.mockResolvedValue({ data: mockSpecies })

      renderWithProviders(<SpeciesFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select species actias luna/i)).toBeInTheDocument()
      })

      const lunaCheckbox = screen.getByLabelText(/select species actias luna/i)

      // Select
      await user.click(lunaCheckbox)
      expect(lunaCheckbox).toBeChecked()

      // Deselect
      await user.click(lunaCheckbox)
      expect(lunaCheckbox).not.toBeChecked()
    })

    it('supports multiple species selection', async () => {
      const user = userEvent.setup()
      api.getAllSpecies.mockResolvedValue({ data: mockSpecies })

      renderWithProviders(<SpeciesFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select species actias luna/i)).toBeInTheDocument()
      })

      const lunaCheckbox = screen.getByLabelText(/select species actias luna/i)
      const monarchCheckbox = screen.getByLabelText(/select species danaus plexippus/i)

      await user.click(lunaCheckbox)
      await user.click(monarchCheckbox)

      expect(lunaCheckbox).toBeChecked()
      expect(monarchCheckbox).toBeChecked()
    })
  })

  // Selected species chips tests
  describe('Selected Species Display', () => {
    it('shows selected species as chips', async () => {
      const user = userEvent.setup()
      api.getAllSpecies.mockResolvedValue({ data: mockSpecies })

      renderWithProviders(<SpeciesFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select species actias luna/i)).toBeInTheDocument()
      })

      await user.click(screen.getByLabelText(/select species actias luna/i))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Tag: Actias luna/i })).toBeInTheDocument()
      })
    })

    it('shows count of selected species', async () => {
      const user = userEvent.setup()
      api.getAllSpecies.mockResolvedValue({ data: mockSpecies })

      renderWithProviders(<SpeciesFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select species actias luna/i)).toBeInTheDocument()
      })

      await user.click(screen.getByLabelText(/select species actias luna/i))
      await user.click(screen.getByLabelText(/select species danaus plexippus/i))

      await waitFor(() => {
        expect(screen.getByText(/selected \(2\)/i)).toBeInTheDocument()
      })
    })

    it('does not show selected section when no species selected', async () => {
      api.getAllSpecies.mockResolvedValue({ data: mockSpecies })

      renderWithProviders(<SpeciesFilter />)

      await waitFor(() => {
        expect(screen.getByText('Actias luna')).toBeInTheDocument()
      })

      expect(screen.queryByText(/selected/i)).not.toBeInTheDocument()
    })
  })

  // Chip removal tests
  describe('Chip Removal', () => {
    it('removes species when chip X button clicked', async () => {
      const user = userEvent.setup()
      api.getAllSpecies.mockResolvedValue({ data: mockSpecies })

      renderWithProviders(<SpeciesFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select species actias luna/i)).toBeInTheDocument()
      })

      // Select species
      await user.click(screen.getByLabelText(/select species actias luna/i))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /remove tag actias luna/i })).toBeInTheDocument()
      })

      // Remove species via chip
      await user.click(screen.getByRole('button', { name: /remove tag actias luna/i }))

      await waitFor(() => {
        expect(screen.queryByRole('button', { name: /Tag: Actias luna/i })).not.toBeInTheDocument()
      })

      // Checkbox should be unchecked
      expect(screen.getByLabelText(/select species actias luna/i)).not.toBeChecked()
    })

    it('updates checkbox state when chip removed', async () => {
      const user = userEvent.setup()
      api.getAllSpecies.mockResolvedValue({ data: mockSpecies })

      renderWithProviders(<SpeciesFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select species actias luna/i)).toBeInTheDocument()
      })

      const lunaCheckbox = screen.getByLabelText(/select species actias luna/i)

      await user.click(lunaCheckbox)
      expect(lunaCheckbox).toBeChecked()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /remove tag actias luna/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /remove tag actias luna/i }))

      await waitFor(() => {
        expect(lunaCheckbox).not.toBeChecked()
      })
    })
  })

  // Search functionality tests
  describe('Search Functionality', () => {
    it('filters species based on search query', async () => {
      const user = userEvent.setup()
      api.getAllSpecies.mockResolvedValue({ data: mockSpecies })

      renderWithProviders(<SpeciesFilter />)

      await waitFor(() => {
        expect(screen.getByText('Actias luna')).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText(/search species/i)
      await user.type(searchInput, 'luna')

      await waitFor(() => {
        expect(screen.getByText('Actias luna')).toBeInTheDocument()
      })

      expect(screen.queryByText('Danaus plexippus')).not.toBeInTheDocument()
      expect(screen.queryByText('Papilio glaucus')).not.toBeInTheDocument()
    })

    it('search is case insensitive', async () => {
      const user = userEvent.setup()
      api.getAllSpecies.mockResolvedValue({ data: mockSpecies })

      renderWithProviders(<SpeciesFilter />)

      await waitFor(() => {
        expect(screen.getByText('Actias luna')).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText(/search species/i)
      await user.type(searchInput, 'ACTIAS')

      await waitFor(() => {
        expect(screen.getByText('Actias luna')).toBeInTheDocument()
      })
    })

    it('shows no results message when search matches nothing', async () => {
      const user = userEvent.setup()
      api.getAllSpecies.mockResolvedValue({ data: mockSpecies })

      renderWithProviders(<SpeciesFilter />)

      await waitFor(() => {
        expect(screen.getByText('Actias luna')).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText(/search species/i)
      await user.type(searchInput, 'xyz123')

      await waitFor(() => {
        expect(screen.getByText(/no species match "xyz123"/i)).toBeInTheDocument()
      })
    })

    it('shows clear search button when search has value', async () => {
      const user = userEvent.setup()
      api.getAllSpecies.mockResolvedValue({ data: mockSpecies })

      renderWithProviders(<SpeciesFilter />)

      await waitFor(() => {
        expect(screen.getByText('Actias luna')).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText(/search species/i)
      await user.type(searchInput, 'luna')

      await waitFor(() => {
        expect(screen.getByLabelText(/clear search/i)).toBeInTheDocument()
      })
    })

    it('clears search when clear button clicked', async () => {
      const user = userEvent.setup()
      api.getAllSpecies.mockResolvedValue({ data: mockSpecies })

      renderWithProviders(<SpeciesFilter />)

      await waitFor(() => {
        expect(screen.getByText('Actias luna')).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText(/search species/i)
      await user.type(searchInput, 'luna')

      await waitFor(() => {
        expect(screen.getByLabelText(/clear search/i)).toBeInTheDocument()
      })

      await user.click(screen.getByLabelText(/clear search/i))

      await waitFor(() => {
        expect(searchInput.value).toBe('')
      })
    })

    it('does not show clear button when search is empty', async () => {
      api.getAllSpecies.mockResolvedValue({ data: mockSpecies })

      renderWithProviders(<SpeciesFilter />)

      await waitFor(() => {
        expect(screen.getByText('Actias luna')).toBeInTheDocument()
      })

      expect(screen.queryByLabelText(/clear search/i)).not.toBeInTheDocument()
    })
  })

  // Include unidentified toggle tests
  describe('Include Unidentified Toggle', () => {
    it('renders include unidentified checkbox unchecked by default', async () => {
      api.getAllSpecies.mockResolvedValue({ data: mockSpecies })

      renderWithProviders(<SpeciesFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/include unidentified photos/i)).toBeInTheDocument()
      })

      const unidentifiedCheckbox = screen.getByLabelText(/include unidentified photos/i)
      expect(unidentifiedCheckbox).not.toBeChecked()
    })

    it('toggles include unidentified when checkbox clicked', async () => {
      const user = userEvent.setup()
      api.getAllSpecies.mockResolvedValue({ data: mockSpecies })

      renderWithProviders(<SpeciesFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/include unidentified photos/i)).toBeInTheDocument()
      })

      const unidentifiedCheckbox = screen.getByLabelText(/include unidentified photos/i)

      await user.click(unidentifiedCheckbox)
      expect(unidentifiedCheckbox).toBeChecked()

      await user.click(unidentifiedCheckbox)
      expect(unidentifiedCheckbox).not.toBeChecked()
    })

    it('maintains include unidentified state when selecting species', async () => {
      const user = userEvent.setup()
      api.getAllSpecies.mockResolvedValue({ data: mockSpecies })

      renderWithProviders(<SpeciesFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/include unidentified photos/i)).toBeInTheDocument()
      })

      const unidentifiedCheckbox = screen.getByLabelText(/include unidentified photos/i)
      await user.click(unidentifiedCheckbox)
      expect(unidentifiedCheckbox).toBeChecked()

      // Select a species
      await user.click(screen.getByLabelText(/select species actias luna/i))

      // Unidentified should still be checked
      expect(unidentifiedCheckbox).toBeChecked()
    })
  })

  // Accessibility tests
  describe('Accessibility', () => {
    it('has accessible search input', async () => {
      api.getAllSpecies.mockResolvedValue({ data: mockSpecies })

      renderWithProviders(<SpeciesFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/search species/i)).toBeInTheDocument()
      })
    })

    it('has accessible checkboxes', async () => {
      api.getAllSpecies.mockResolvedValue({ data: mockSpecies })

      renderWithProviders(<SpeciesFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select species actias luna/i)).toBeInTheDocument()
      })

      expect(screen.getByLabelText(/select species danaus plexippus/i)).toBeInTheDocument()
    })

    it('has accessible include unidentified checkbox', async () => {
      api.getAllSpecies.mockResolvedValue({ data: mockSpecies })

      renderWithProviders(<SpeciesFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/include.*unidentified/i)).toBeInTheDocument()
      })
    })

    it('supports keyboard navigation on checkboxes', async () => {
      const user = userEvent.setup()
      api.getAllSpecies.mockResolvedValue({ data: mockSpecies })

      renderWithProviders(<SpeciesFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select species actias luna/i)).toBeInTheDocument()
      })

      const lunaCheckbox = screen.getByLabelText(/select species actias luna/i)
      await user.click(lunaCheckbox)

      expect(lunaCheckbox).toBeChecked()
    })
  })

  // Context integration tests
  describe('Context Integration', () => {
    it('updates context when species selected', async () => {
      const user = userEvent.setup()
      api.getAllSpecies.mockResolvedValue({ data: mockSpecies })

      renderWithProviders(<SpeciesFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select species actias luna/i)).toBeInTheDocument()
      })

      await user.click(screen.getByLabelText(/select species actias luna/i))

      await waitFor(() => {
        const checkbox = screen.getByLabelText(/select species actias luna/i)
        expect(checkbox).toBeChecked()
      })
    })

    it('updates context when include unidentified toggled', async () => {
      const user = userEvent.setup()
      api.getAllSpecies.mockResolvedValue({ data: mockSpecies })

      renderWithProviders(<SpeciesFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/include unidentified photos/i)).toBeInTheDocument()
      })

      const unidentifiedCheckbox = screen.getByLabelText(/include unidentified photos/i)
      await user.click(unidentifiedCheckbox)

      await waitFor(() => {
        expect(unidentifiedCheckbox).toBeChecked()
      })
    })
  })
})

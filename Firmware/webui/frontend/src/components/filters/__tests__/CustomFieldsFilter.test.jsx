import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { CustomFieldsFilter } from '../CustomFieldsFilter'
import { FilterProvider } from '../../../contexts/FilterContext'
import { api } from '../../../utils/api'

// Mock the API
vi.mock('../../../utils/api', () => ({
  api: {
    get: vi.fn(),
  },
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

// Sample custom fields data
const mockTextFields = {
  fields: [
    { name: 'location', type: 'text', values: ['Forest', 'Meadow', 'Garden', 'Wetland'] },
    { name: 'observer', type: 'text', values: ['Alice', 'Bob', 'Charlie'] },
  ],
}

const mockNumberFields = {
  fields: [
    { name: 'temperature', type: 'number', min: -10, max: 40 },
    { name: 'humidity', type: 'number', min: 0, max: 100 },
  ],
}

const mockSelectFields = {
  fields: [
    { name: 'weather', type: 'select', options: ['Sunny', 'Cloudy', 'Rainy', 'Snowy'] },
    { name: 'moon_phase', type: 'select', options: ['New', 'Waxing', 'Full', 'Waning'] },
  ],
}

const mockMixedFields = {
  fields: [
    { name: 'location', type: 'text', values: ['Forest', 'Meadow', 'Garden'] },
    { name: 'temperature', type: 'number', min: -10, max: 40 },
    { name: 'weather', type: 'select', options: ['Sunny', 'Cloudy', 'Rainy'] },
  ],
}

describe('CustomFieldsFilter', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // Loading state tests
  describe('Loading State', () => {
    it('renders loading state while fetching custom fields', () => {
      api.get.mockReturnValue(new Promise(() => {})) // Never resolves

      renderWithProviders(<CustomFieldsFilter />)

      expect(screen.getByText(/loading custom fields/i)).toBeInTheDocument()
    })

    it('shows loading spinner during initial load', () => {
      api.get.mockReturnValue(new Promise(() => {}))

      renderWithProviders(<CustomFieldsFilter />)

      const loadingElement = screen.getByText(/loading custom fields/i)
      expect(loadingElement).toHaveClass('animate-pulse')
    })
  })

  // Error state tests
  describe('Error State', () => {
    it('renders error message when API call fails', async () => {
      api.get.mockRejectedValue(new Error('Network error'))

      renderWithProviders(<CustomFieldsFilter />)

      await waitFor(() => {
        expect(screen.getByText(/failed to load custom fields/i)).toBeInTheDocument()
      })
    })

    it('shows error message with details', async () => {
      const errorMessage = 'Database connection failed'
      api.get.mockRejectedValue(new Error(errorMessage))

      renderWithProviders(<CustomFieldsFilter />)

      await waitFor(() => {
        expect(screen.getByText(new RegExp(errorMessage, 'i'))).toBeInTheDocument()
      })
    })
  })

  // Empty state tests
  describe('Empty State', () => {
    it('shows empty state when no custom fields available', async () => {
      api.get.mockResolvedValue({ data: { fields: [] } })

      renderWithProviders(<CustomFieldsFilter />)

      await waitFor(() => {
        expect(screen.getByText(/no custom fields available/i)).toBeInTheDocument()
      })
    })
  })

  // Text field tests
  describe('Text Field Rendering', () => {
    it('renders text fields with search input', async () => {
      api.get.mockResolvedValue({ data: mockTextFields })

      renderWithProviders(<CustomFieldsFilter />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/search location/i)).toBeInTheDocument()
      })

      expect(screen.getByPlaceholderText(/search observer/i)).toBeInTheDocument()
    })

    it('renders text field values as clickable options', async () => {
      api.get.mockResolvedValue({ data: mockTextFields })

      renderWithProviders(<CustomFieldsFilter />)

      await waitFor(() => {
        expect(screen.getByText('Forest')).toBeInTheDocument()
      })

      expect(screen.getByText('Meadow')).toBeInTheDocument()
      expect(screen.getByText('Garden')).toBeInTheDocument()
      expect(screen.getByText('Wetland')).toBeInTheDocument()
    })

    it('filters text field values based on search query', async () => {
      const user = userEvent.setup()
      api.get.mockResolvedValue({ data: mockTextFields })

      renderWithProviders(<CustomFieldsFilter />)

      await waitFor(() => {
        expect(screen.getByText('Forest')).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText(/search location/i)
      await user.type(searchInput, 'for')

      await waitFor(() => {
        expect(screen.getByText('Forest')).toBeInTheDocument()
      })

      expect(screen.queryByText('Meadow')).not.toBeInTheDocument()
      expect(screen.queryByText('Garden')).not.toBeInTheDocument()
    })

    it('shows no results message when search matches nothing', async () => {
      const user = userEvent.setup()
      api.get.mockResolvedValue({ data: mockTextFields })

      renderWithProviders(<CustomFieldsFilter />)

      await waitFor(() => {
        expect(screen.getByText('Forest')).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText(/search location/i)
      await user.type(searchInput, 'xyz123')

      await waitFor(() => {
        expect(screen.getByText(/no values match "xyz123"/i)).toBeInTheDocument()
      })
    })

    it('text field search is case insensitive', async () => {
      const user = userEvent.setup()
      api.get.mockResolvedValue({ data: mockTextFields })

      renderWithProviders(<CustomFieldsFilter />)

      await waitFor(() => {
        expect(screen.getByText('Forest')).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText(/search location/i)
      await user.type(searchInput, 'FOREST')

      await waitFor(() => {
        expect(screen.getByText('Forest')).toBeInTheDocument()
      })
    })
  })

  // Text field interaction tests
  describe('Text Field Interactions', () => {
    it('selects text field value when clicked', async () => {
      const user = userEvent.setup()
      api.get.mockResolvedValue({ data: mockTextFields })

      renderWithProviders(<CustomFieldsFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select forest for location/i)).toBeInTheDocument()
      })

      const forestButton = screen.getByLabelText(/select forest for location/i)
      await user.click(forestButton)

      await waitFor(() => {
        expect(forestButton).toHaveAttribute('aria-pressed', 'true')
      })
    })

    it('deselects text field value when clicked again', async () => {
      const user = userEvent.setup()
      api.get.mockResolvedValue({ data: mockTextFields })

      renderWithProviders(<CustomFieldsFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select forest for location/i)).toBeInTheDocument()
      })

      const forestButton = screen.getByLabelText(/select forest for location/i)

      // Select
      await user.click(forestButton)
      await waitFor(() => {
        expect(forestButton).toHaveAttribute('aria-pressed', 'true')
      })

      // Deselect
      await user.click(forestButton)
      await waitFor(() => {
        expect(forestButton).toHaveAttribute('aria-pressed', 'false')
      })
    })

    it('highlights selected text field value', async () => {
      const user = userEvent.setup()
      api.get.mockResolvedValue({ data: mockTextFields })

      renderWithProviders(<CustomFieldsFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select forest for location/i)).toBeInTheDocument()
      })

      const forestButton = screen.getByLabelText(/select forest for location/i)
      await user.click(forestButton)

      await waitFor(() => {
        expect(forestButton).toHaveClass('bg-blue-50', 'dark:bg-blue-900/30')
      })
    })
  })

  // Number field tests
  describe('Number Field Rendering', () => {
    it('renders number fields with numeric input', async () => {
      api.get.mockResolvedValue({ data: mockNumberFields })

      renderWithProviders(<CustomFieldsFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/enter temperature/i)).toBeInTheDocument()
      })

      expect(screen.getByLabelText(/enter humidity/i)).toBeInTheDocument()
    })

    it('displays number field range information', async () => {
      api.get.mockResolvedValue({ data: mockNumberFields })

      renderWithProviders(<CustomFieldsFilter />)

      await waitFor(() => {
        expect(screen.getByText(/range: -10 to 40/i)).toBeInTheDocument()
      })

      expect(screen.getByText(/range: 0 to 100/i)).toBeInTheDocument()
    })

    it('accepts numeric input in number fields', async () => {
      const user = userEvent.setup()
      api.get.mockResolvedValue({ data: mockNumberFields })

      renderWithProviders(<CustomFieldsFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/enter temperature/i)).toBeInTheDocument()
      })

      const tempInput = screen.getByLabelText(/enter temperature/i)
      await user.type(tempInput, '25')

      await waitFor(() => {
        expect(tempInput).toHaveValue(25)
      })
    })
  })

  // Select field tests
  describe('Select Field Rendering', () => {
    it('renders select fields with dropdown', async () => {
      api.get.mockResolvedValue({ data: mockSelectFields })

      renderWithProviders(<CustomFieldsFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select weather/i)).toBeInTheDocument()
      })

      expect(screen.getByLabelText(/select moon_phase/i)).toBeInTheDocument()
    })

    it('renders select field options', async () => {
      api.get.mockResolvedValue({ data: mockSelectFields })

      renderWithProviders(<CustomFieldsFilter />)

      await waitFor(() => {
        const weatherSelect = screen.getByLabelText(/select weather/i)
        expect(weatherSelect).toBeInTheDocument()
      })

      const weatherSelect = screen.getByLabelText(/select weather/i)
      const options = Array.from(weatherSelect.querySelectorAll('option'))
      const optionTexts = options.map(opt => opt.textContent)

      expect(optionTexts).toContain('Sunny')
      expect(optionTexts).toContain('Cloudy')
      expect(optionTexts).toContain('Rainy')
      expect(optionTexts).toContain('Snowy')
    })

    it('selects option in select field', async () => {
      const user = userEvent.setup()
      api.get.mockResolvedValue({ data: mockSelectFields })

      renderWithProviders(<CustomFieldsFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select weather/i)).toBeInTheDocument()
      })

      const weatherSelect = screen.getByLabelText(/select weather/i)
      await user.selectOptions(weatherSelect, 'Sunny')

      await waitFor(() => {
        expect(weatherSelect).toHaveValue('Sunny')
      })
    })
  })

  // Mixed field types tests
  describe('Mixed Field Types', () => {
    it('renders multiple field types correctly', async () => {
      api.get.mockResolvedValue({ data: mockMixedFields })

      renderWithProviders(<CustomFieldsFilter />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/search location/i)).toBeInTheDocument()
        expect(screen.getByLabelText(/enter temperature/i)).toBeInTheDocument()
        expect(screen.getByLabelText(/select weather/i)).toBeInTheDocument()
      })
    })

    it('renders field labels', async () => {
      api.get.mockResolvedValue({ data: mockMixedFields })

      renderWithProviders(<CustomFieldsFilter />)

      await waitFor(() => {
        expect(screen.getByText('location')).toBeInTheDocument()
      })

      expect(screen.getByText('temperature')).toBeInTheDocument()
      expect(screen.getByText('weather')).toBeInTheDocument()
    })
  })

  // Context integration tests
  describe('Context Integration', () => {
    it('updates context when text field value selected', async () => {
      const user = userEvent.setup()
      api.get.mockResolvedValue({ data: mockTextFields })

      renderWithProviders(<CustomFieldsFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select forest for location/i)).toBeInTheDocument()
      })

      const forestButton = screen.getByLabelText(/select forest for location/i)
      await user.click(forestButton)

      await waitFor(() => {
        expect(forestButton).toHaveAttribute('aria-pressed', 'true')
      })
    })

    it('updates context when number field value entered', async () => {
      const user = userEvent.setup()
      api.get.mockResolvedValue({ data: mockNumberFields })

      renderWithProviders(<CustomFieldsFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/enter temperature/i)).toBeInTheDocument()
      })

      const tempInput = screen.getByLabelText(/enter temperature/i)
      await user.type(tempInput, '25')

      await waitFor(() => {
        expect(tempInput).toHaveValue(25)
      })
    })

    it('updates context when select field option chosen', async () => {
      const user = userEvent.setup()
      api.get.mockResolvedValue({ data: mockSelectFields })

      renderWithProviders(<CustomFieldsFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select weather/i)).toBeInTheDocument()
      })

      const weatherSelect = screen.getByLabelText(/select weather/i)
      await user.selectOptions(weatherSelect, 'Sunny')

      await waitFor(() => {
        expect(weatherSelect).toHaveValue('Sunny')
      })
    })
  })

  // Accessibility tests
  describe('Accessibility', () => {
    it('has accessible labels for text field search inputs', async () => {
      api.get.mockResolvedValue({ data: mockTextFields })

      renderWithProviders(<CustomFieldsFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/search location/i)).toBeInTheDocument()
      })

      expect(screen.getByLabelText(/search observer/i)).toBeInTheDocument()
    })

    it('has accessible labels for number field inputs', async () => {
      api.get.mockResolvedValue({ data: mockNumberFields })

      renderWithProviders(<CustomFieldsFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/enter temperature/i)).toBeInTheDocument()
      })

      expect(screen.getByLabelText(/enter humidity/i)).toBeInTheDocument()
    })

    it('has accessible labels for select field dropdowns', async () => {
      api.get.mockResolvedValue({ data: mockSelectFields })

      renderWithProviders(<CustomFieldsFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select weather/i)).toBeInTheDocument()
      })

      expect(screen.getByLabelText(/select moon_phase/i)).toBeInTheDocument()
    })

    it('has accessible labels for text field value buttons', async () => {
      api.get.mockResolvedValue({ data: mockTextFields })

      renderWithProviders(<CustomFieldsFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select forest for location/i)).toBeInTheDocument()
      })

      expect(screen.getByLabelText(/select meadow for location/i)).toBeInTheDocument()
    })

    it('uses aria-pressed for text field value buttons', async () => {
      const user = userEvent.setup()
      api.get.mockResolvedValue({ data: mockTextFields })

      renderWithProviders(<CustomFieldsFilter />)

      await waitFor(() => {
        expect(screen.getByLabelText(/select forest for location/i)).toBeInTheDocument()
      })

      const forestButton = screen.getByLabelText(/select forest for location/i)
      expect(forestButton).toHaveAttribute('aria-pressed', 'false')

      await user.click(forestButton)

      await waitFor(() => {
        expect(forestButton).toHaveAttribute('aria-pressed', 'true')
      })
    })
  })

  // Styling tests
  describe('Styling', () => {
    it('applies dark mode classes to text field search inputs', async () => {
      api.get.mockResolvedValue({ data: mockTextFields })

      renderWithProviders(<CustomFieldsFilter />)

      await waitFor(() => {
        const searchInput = screen.getByPlaceholderText(/search location/i)
        expect(searchInput).toHaveClass('dark:bg-gray-800', 'dark:text-gray-100')
      })
    })

    it('applies dark mode classes to number field inputs', async () => {
      api.get.mockResolvedValue({ data: mockNumberFields })

      renderWithProviders(<CustomFieldsFilter />)

      await waitFor(() => {
        const tempInput = screen.getByLabelText(/enter temperature/i)
        expect(tempInput).toHaveClass('dark:bg-gray-800', 'dark:text-gray-100')
      })
    })

    it('applies dark mode classes to select field dropdowns', async () => {
      api.get.mockResolvedValue({ data: mockSelectFields })

      renderWithProviders(<CustomFieldsFilter />)

      await waitFor(() => {
        const weatherSelect = screen.getByLabelText(/select weather/i)
        expect(weatherSelect).toHaveClass('dark:bg-gray-800', 'dark:text-gray-100')
      })
    })

    it('applies focus ring styles to inputs', async () => {
      api.get.mockResolvedValue({ data: mockMixedFields })

      renderWithProviders(<CustomFieldsFilter />)

      await waitFor(() => {
        const searchInput = screen.getByPlaceholderText(/search location/i)
        expect(searchInput).toHaveClass('focus:outline-none', 'focus:ring-2', 'focus:ring-blue-500')
      })
    })
  })
})

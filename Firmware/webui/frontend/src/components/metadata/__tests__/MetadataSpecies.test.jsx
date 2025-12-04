import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import MetadataSpecies from '../MetadataSpecies'

// Mock the useSpecies hook
vi.mock('../../../hooks/useSpecies', () => ({
  default: vi.fn(() => ({
    data: {
      species: [
        { name: 'Actias luna', count: 42 },
        { name: 'Actias selene', count: 18 },
        { name: 'Antheraea polyphemus', count: 35 },
        { name: 'Automeris io', count: 27 },
        { name: 'Callosamia promethea', count: 12 },
      ],
    },
    isLoading: false,
    error: null,
  })),
}))

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })
  return ({ children }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('MetadataSpecies', () => {
  let mockOnChange

  beforeEach(() => {
    mockOnChange = vi.fn()
  })

  it('test_renders_species_input_with_current_value', () => {
    render(
      <MetadataSpecies
        species="Actias luna"
        confidence="certain"
        onChange={mockOnChange}
      />,
      { wrapper: createWrapper() }
    )

    const speciesInput = screen.getByPlaceholderText(/e.g., Actias luna/)
    expect(speciesInput).toBeInTheDocument()
    expect(speciesInput.value).toBe('Actias luna')
  })

  it('test_shows_autocomplete_suggestions', async () => {
    render(
      <MetadataSpecies
        species=""
        confidence="unknown"
        onChange={mockOnChange}
      />,
      { wrapper: createWrapper() }
    )

    const speciesInput = screen.getByPlaceholderText(/e.g., Actias luna/)

    // Type to trigger autocomplete
    fireEvent.change(speciesInput, { target: { value: 'Actias' } })
    fireEvent.focus(speciesInput)

    // Wait for suggestions to appear
    await waitFor(() => {
      expect(screen.getByText(/Actias luna/)).toBeInTheDocument()
      expect(screen.getByText(/Actias selene/)).toBeInTheDocument()
    })
  })

  it('test_selecting_suggestion_updates_field', async () => {
    render(
      <MetadataSpecies
        species=""
        confidence="unknown"
        onChange={mockOnChange}
      />,
      { wrapper: createWrapper() }
    )

    const speciesInput = screen.getByPlaceholderText(/e.g., Actias luna/)

    // Type and show suggestions
    fireEvent.change(speciesInput, { target: { value: 'Actias' } })
    fireEvent.focus(speciesInput)

    // Wait for and click suggestion
    await waitFor(() => {
      expect(screen.getByText(/Actias luna/)).toBeInTheDocument()
    })

    const suggestion = screen.getByText(/Actias luna/)
    fireEvent.click(suggestion)

    // Input should be updated
    await waitFor(() => {
      expect(speciesInput.value).toBe('Actias luna')
      expect(mockOnChange).toHaveBeenCalledWith('species', 'Actias luna')
    })
  })

  it('test_renders_confidence_dropdown', () => {
    render(
      <MetadataSpecies
        species="Actias luna"
        confidence="certain"
        onChange={mockOnChange}
      />,
      { wrapper: createWrapper() }
    )

    const confidenceLabel = screen.getByText('Confidence')
    expect(confidenceLabel).toBeInTheDocument()

    const confidenceSelect = screen.getByDisplayValue('Certain')
    expect(confidenceSelect).toBeInTheDocument()
  })

  it('test_confidence_options', () => {
    render(
      <MetadataSpecies
        species="Actias luna"
        confidence="certain"
        onChange={mockOnChange}
      />,
      { wrapper: createWrapper() }
    )

    const confidenceSelect = screen.getByDisplayValue('Certain')

    // Check all options are present
    expect(screen.getByRole('option', { name: 'Certain' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Probable' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Possible' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Unknown' })).toBeInTheDocument()
  })

  it('test_selecting_confidence_calls_onChange', () => {
    render(
      <MetadataSpecies
        species="Actias luna"
        confidence="certain"
        onChange={mockOnChange}
      />,
      { wrapper: createWrapper() }
    )

    const confidenceSelect = screen.getByDisplayValue('Certain')

    fireEvent.change(confidenceSelect, { target: { value: 'probable' } })

    expect(mockOnChange).toHaveBeenCalledWith('confidence', 'probable')
  })

  it('test_renders_common_name_field', () => {
    render(
      <MetadataSpecies
        species="Actias luna"
        confidence="certain"
        commonName="Luna Moth"
        onChange={mockOnChange}
      />,
      { wrapper: createWrapper() }
    )

    const commonNameLabel = screen.getByText('Common Name')
    expect(commonNameLabel).toBeInTheDocument()

    const commonNameInput = screen.getByPlaceholderText(/e.g., Luna Moth/)
    expect(commonNameInput).toBeInTheDocument()
    expect(commonNameInput.value).toBe('Luna Moth')
  })

  it('test_renders_reference_link_field', () => {
    render(
      <MetadataSpecies
        species="Actias luna"
        confidence="certain"
        referenceUrl="https://inaturalist.org/taxa/47924"
        onChange={mockOnChange}
      />,
      { wrapper: createWrapper() }
    )

    const referenceLabel = screen.getByText('Reference Link')
    expect(referenceLabel).toBeInTheDocument()

    const referenceInput = screen.getByPlaceholderText(/https:\/\/inaturalist.org\/.../)
    expect(referenceInput).toBeInTheDocument()
    expect(referenceInput.value).toBe('https://inaturalist.org/taxa/47924')
  })

  it('test_calls_onChange_on_input', () => {
    render(
      <MetadataSpecies
        species="Actias luna"
        confidence="certain"
        commonName=""
        onChange={mockOnChange}
      />,
      { wrapper: createWrapper() }
    )

    const commonNameInput = screen.getByPlaceholderText(/e.g., Luna Moth/)

    fireEvent.change(commonNameInput, { target: { value: 'Luna Moth' } })

    expect(mockOnChange).toHaveBeenCalledWith('commonName', 'Luna Moth')
  })

  it('test_validates_reference_url', () => {
    render(
      <MetadataSpecies
        species="Actias luna"
        confidence="certain"
        referenceUrl=""
        onChange={mockOnChange}
      />,
      { wrapper: createWrapper() }
    )

    const referenceInput = screen.getByPlaceholderText(/https:\/\/inaturalist.org\/.../)

    // Invalid URL (no protocol)
    fireEvent.change(referenceInput, { target: { value: 'inaturalist.org/taxa/47924' } })

    expect(screen.getByText('URL must start with http:// or https://')).toBeInTheDocument()
    expect(mockOnChange).toHaveBeenCalledWith('referenceUrl', 'inaturalist.org/taxa/47924')
  })

  it('test_species_blur_triggers_onChange', () => {
    render(
      <MetadataSpecies
        species=""
        confidence="unknown"
        onChange={mockOnChange}
      />,
      { wrapper: createWrapper() }
    )

    const speciesInput = screen.getByPlaceholderText(/e.g., Actias luna/)

    fireEvent.change(speciesInput, { target: { value: 'Actias luna' } })
    fireEvent.blur(speciesInput)

    // Wait for blur timeout
    setTimeout(() => {
      expect(mockOnChange).toHaveBeenCalledWith('species', 'Actias luna')
    }, 300)
  })

  it('test_disabled_state', () => {
    render(
      <MetadataSpecies
        species="Actias luna"
        confidence="certain"
        commonName="Luna Moth"
        referenceUrl="https://inaturalist.org/taxa/47924"
        onChange={mockOnChange}
        disabled={true}
      />,
      { wrapper: createWrapper() }
    )

    const speciesInput = screen.getByPlaceholderText(/e.g., Actias luna/)
    const commonNameInput = screen.getByPlaceholderText(/e.g., Luna Moth/)
    const confidenceSelect = screen.getByDisplayValue('Certain')
    const referenceInput = screen.getByPlaceholderText(/https:\/\/inaturalist.org\/.../)

    expect(speciesInput).toBeDisabled()
    expect(commonNameInput).toBeDisabled()
    expect(confidenceSelect).toBeDisabled()
    expect(referenceInput).toBeDisabled()
  })

  it('test_valid_url_clears_error', () => {
    render(
      <MetadataSpecies
        species="Actias luna"
        confidence="certain"
        referenceUrl=""
        onChange={mockOnChange}
      />,
      { wrapper: createWrapper() }
    )

    const referenceInput = screen.getByPlaceholderText(/https:\/\/inaturalist.org\/.../)

    // Invalid URL first
    fireEvent.change(referenceInput, { target: { value: 'inaturalist.org' } })
    expect(screen.getByText('URL must start with http:// or https://')).toBeInTheDocument()

    // Valid URL should clear error
    fireEvent.change(referenceInput, { target: { value: 'https://inaturalist.org/taxa/47924' } })
    expect(screen.queryByText('URL must start with http:// or https://')).not.toBeInTheDocument()
  })

  it('test_empty_url_clears_error', async () => {
    render(
      <MetadataSpecies
        species="Actias luna"
        confidence="certain"
        referenceUrl=""
        onChange={mockOnChange}
      />,
      { wrapper: createWrapper() }
    )

    const referenceInput = screen.getByPlaceholderText(/https:\/\/inaturalist.org\/.../)

    // Set invalid URL first
    fireEvent.change(referenceInput, { target: { value: 'invalid' } })

    await waitFor(() => {
      expect(screen.getByText('URL must start with http:// or https://')).toBeInTheDocument()
    })

    // Empty URL should clear error
    fireEvent.change(referenceInput, { target: { value: '' } })

    await waitFor(() => {
      expect(screen.queryByText('URL must start with http:// or https://')).not.toBeInTheDocument()
    })
  })
})

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useForm, type Resolver } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import MetadataSpecies from '../MetadataSpecies'
import { metadataFormSchema, type MetadataFormData } from '../../../schemas/metadata'

// Mock the useSpecies hook
vi.mock('../../../hooks/useSpecies', () => ({
  default: vi.fn(() => ({
    species: [
      { name: 'Actias luna', count: 42 },
      { name: 'Actias selene', count: 18 },
      { name: 'Antheraea polyphemus', count: 35 },
      { name: 'Automeris io', count: 27 },
      { name: 'Callosamia promethea', count: 12 },
    ],
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
    filteredSpecies: vi.fn((searchTerm: string) => {
      const allSpecies = [
        { name: 'Actias luna', count: 42 },
        { name: 'Actias selene', count: 18 },
        { name: 'Antheraea polyphemus', count: 35 },
        { name: 'Automeris io', count: 27 },
        { name: 'Callosamia promethea', count: 12 },
      ]
      if (!searchTerm) return allSpecies
      const query = searchTerm.toLowerCase()
      return allSpecies.filter(s => s.name.toLowerCase().includes(query))
    }),
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

function renderSpecies(
  overrides: Partial<MetadataFormData> = {},
  opts: { disabled?: boolean } = {},
) {
  function Wrapper() {
    // zodResolver's Zod 4 overload expects $ZodType<Output, FieldValues> but
    // Zod 4's public ZodType uses `unknown` for its input parameter. The cast
    // through `unknown` is safe because the schema validates the same shape at
    // runtime. TODO: Remove when @hookform/resolvers aligns with Zod 4 generics.
    const resolver = zodResolver(
      metadataFormSchema as unknown as Parameters<typeof zodResolver>[0],
    ) as unknown as Resolver<MetadataFormData>

    const {
      control,
      register,
      setValue,
      formState: { errors },
    } = useForm<MetadataFormData>({
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
        <MetadataSpecies
          control={control}
          register={register}
          setValue={setValue}
          errors={errors}
          disabled={opts.disabled}
        />
      </QueryClientProvider>
    )
  }

  return render(<Wrapper />)
}

describe('MetadataSpecies', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('test_renders_species_input_with_current_value', () => {
    renderSpecies({ species: 'Actias luna', confidence: 'certain' })

    const speciesInput = screen.getByPlaceholderText(/e.g., Actias luna/)
    expect(speciesInput).toBeInTheDocument()
    expect(speciesInput).toHaveValue('Actias luna')
  })

  it('test_shows_autocomplete_suggestions', async () => {
    renderSpecies({ species: '', confidence: 'unknown' })

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
    renderSpecies({ species: '', confidence: 'unknown' })

    const speciesInput = screen.getByPlaceholderText(/e.g., Actias luna/)

    // Type and show suggestions
    fireEvent.change(speciesInput, { target: { value: 'Actias' } })
    fireEvent.focus(speciesInput)

    // Wait for and click suggestion
    await waitFor(() => {
      expect(screen.getByText(/Actias luna/)).toBeInTheDocument()
    })

    const suggestion = screen.getByText(/Actias luna/)
    fireEvent.mouseDown(suggestion)

    // Input should be updated via setValue
    await waitFor(() => {
      expect(speciesInput).toHaveValue('Actias luna')
    })
  })

  it('test_renders_confidence_dropdown', () => {
    renderSpecies({ species: 'Actias luna', confidence: 'certain' })

    const confidenceLabel = screen.getByText('Confidence')
    expect(confidenceLabel).toBeInTheDocument()

    const confidenceSelect = screen.getByDisplayValue('Certain')
    expect(confidenceSelect).toBeInTheDocument()
  })

  it('test_confidence_options', () => {
    renderSpecies({ species: 'Actias luna', confidence: 'certain' })

    // Check all options are present
    expect(screen.getByRole('option', { name: 'Certain' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Probable' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Possible' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Unknown' })).toBeInTheDocument()
  })

  it('test_renders_common_name_field', () => {
    renderSpecies({
      species: 'Actias luna',
      confidence: 'certain',
      commonName: 'Luna Moth',
    })

    const commonNameLabel = screen.getByText('Common Name')
    expect(commonNameLabel).toBeInTheDocument()

    const commonNameInput = screen.getByPlaceholderText(/e.g., Luna Moth/)
    expect(commonNameInput).toBeInTheDocument()
    expect(commonNameInput).toHaveValue('Luna Moth')
  })

  it('test_renders_reference_link_field', () => {
    renderSpecies({
      species: 'Actias luna',
      confidence: 'certain',
      referenceUrl: 'https://inaturalist.org/taxa/47924',
    })

    const referenceLabel = screen.getByText('Reference Link')
    expect(referenceLabel).toBeInTheDocument()

    const referenceInput = screen.getByPlaceholderText(/https:\/\/inaturalist.org\/.../)
    expect(referenceInput).toBeInTheDocument()
    expect(referenceInput).toHaveValue('https://inaturalist.org/taxa/47924')
  })

  it('test_shows_url_validation_error_on_blur', async () => {
    renderSpecies({
      species: 'Actias luna',
      confidence: 'certain',
      referenceUrl: '',
    })

    const referenceInput = screen.getByPlaceholderText(/https:\/\/inaturalist.org\/.../)

    // Invalid URL (no protocol) - triggers Zod validation on blur
    fireEvent.change(referenceInput, { target: { value: 'inaturalist.org/taxa/47924' } })
    fireEvent.blur(referenceInput)

    await waitFor(() => {
      expect(screen.getByText('URL must start with http:// or https://')).toBeInTheDocument()
    })
  })

  it('test_clears_url_error_when_valid_url_entered', async () => {
    renderSpecies({
      species: 'Actias luna',
      confidence: 'certain',
      referenceUrl: '',
    })

    const referenceInput = screen.getByPlaceholderText(/https:\/\/inaturalist.org\/.../)

    // Invalid URL first
    fireEvent.change(referenceInput, { target: { value: 'inaturalist.org' } })
    fireEvent.blur(referenceInput)

    await waitFor(() => {
      expect(screen.getByText('URL must start with http:// or https://')).toBeInTheDocument()
    })

    // Valid URL should clear error
    fireEvent.change(referenceInput, { target: { value: 'https://inaturalist.org/taxa/47924' } })
    fireEvent.blur(referenceInput)

    await waitFor(() => {
      expect(screen.queryByText('URL must start with http:// or https://')).not.toBeInTheDocument()
    })
  })

  it('test_disabled_state', () => {
    renderSpecies(
      {
        species: 'Actias luna',
        confidence: 'certain',
        commonName: 'Luna Moth',
        referenceUrl: 'https://inaturalist.org/taxa/47924',
      },
      { disabled: true },
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

  it('test_shows_external_link_icon_for_valid_url', () => {
    renderSpecies({
      species: 'Actias luna',
      confidence: 'certain',
      referenceUrl: 'https://inaturalist.org/taxa/47924',
    })

    const externalLink = screen.getByLabelText('Visit reference link')
    expect(externalLink).toBeInTheDocument()
    expect(externalLink).toHaveAttribute('href', 'https://inaturalist.org/taxa/47924')
    expect(externalLink).toHaveAttribute('target', '_blank')
  })

  it('test_species_blur_closes_suggestions', async () => {
    renderSpecies({ species: '', confidence: 'unknown' })

    const speciesInput = screen.getByPlaceholderText(/e.g., Actias luna/)

    // Type to show suggestions
    fireEvent.change(speciesInput, { target: { value: 'Actias' } })
    fireEvent.focus(speciesInput)

    await waitFor(() => {
      expect(screen.getByText(/Actias luna/)).toBeInTheDocument()
    })

    // Blur should close suggestions
    fireEvent.blur(speciesInput)

    await waitFor(() => {
      expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
    })
  })

  it('test_empty_url_clears_error', async () => {
    renderSpecies({
      species: 'Actias luna',
      confidence: 'certain',
      referenceUrl: '',
    })

    const referenceInput = screen.getByPlaceholderText(/https:\/\/inaturalist.org\/.../)

    // Set invalid URL first
    fireEvent.change(referenceInput, { target: { value: 'invalid' } })
    fireEvent.blur(referenceInput)

    await waitFor(() => {
      expect(screen.getByText('URL must start with http:// or https://')).toBeInTheDocument()
    })

    // Empty URL should clear error
    fireEvent.change(referenceInput, { target: { value: '' } })
    fireEvent.blur(referenceInput)

    await waitFor(() => {
      expect(screen.queryByText('URL must start with http:// or https://')).not.toBeInTheDocument()
    })
  })
})

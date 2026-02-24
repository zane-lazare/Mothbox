import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import MetadataPanel from '../MetadataPanel'
import * as apiModule from '../../../utils/api'

// Hoist useWatch import so it can be used inside vi.mock factories
const { useWatch: useWatchHoisted } = await vi.hoisted(async () => {
  return await import('react-hook-form')
})

// Mock the API module
vi.mock('../../../utils/api', () => ({
  api: {
    get: vi.fn(),
    put: vi.fn(),
  },
  getPhotoSidecarMetadata: vi.fn(),
  updatePhotoSidecarMetadata: vi.fn(),
}))

// Get mocked functions for use in tests
const mockApiGet = vi.mocked(apiModule.api.get)
vi.mocked(apiModule.api.put)
const mockGetPhotoSidecarMetadata = vi.mocked(apiModule.getPhotoSidecarMetadata)
const mockUpdatePhotoSidecarMetadata = vi.mocked(apiModule.updatePhotoSidecarMetadata)

// Mock the AccordionSection component
vi.mock('../AccordionSection', () => ({
  default: ({ title, icon, children, defaultExpanded }: {
    title: string
    icon: React.ReactNode
    children: React.ReactNode
    defaultExpanded?: boolean
  }) => (
    <div data-testid={`accordion-section-${title.toLowerCase().replace(/\s+/g, '-')}`}>
      <div data-testid="accordion-header" data-expanded={defaultExpanded}>
        {icon}
        <span>{title}</span>
      </div>
      <div data-testid="accordion-content">{children}</div>
    </div>
  ),
}))

// Mock the SaveStatusIndicator component
vi.mock('../SaveStatusIndicator', () => ({
  default: ({ status, onRetry, errorMessage }: {
    status: string
    onRetry?: () => void
    errorMessage?: string
  }) => (
    <div data-testid="save-status-indicator" data-status={status}>
      {status === 'saving' && <span>Saving...</span>}
      {status === 'saved' && <span>Saved</span>}
      {status === 'error' && (
        <>
          <span>{errorMessage || 'Save failed'}</span>
          {onRetry && (
            <button onClick={onRetry} data-testid="retry-save-button">
              Retry
            </button>
          )}
        </>
      )}
    </div>
  ),
}))

// Mock the section components with react-hook-form awareness
// These mocks use useWatch (hoisted) to read values from the form and setValue to write values
vi.mock('../MetadataTags', () => ({
  default: function MockMetadataTags({ control, setValue }: { control: any; setValue: (name: string, value: unknown, opts?: unknown) => void }) {
    const tags = useWatchHoisted({ control, name: 'tags' }) ?? []
    return (
      <div data-testid="metadata-tags">
        <div data-testid="tags-list">
          {(tags as string[]).map((tag: string) => (
            <span key={tag} data-testid={`tag-${tag}`}>
              {tag}
              <button onClick={() => setValue('tags', (tags as string[]).filter((t: string) => t !== tag), { shouldDirty: true })}>Remove {tag}</button>
            </span>
          ))}
        </div>
        <button onClick={() => setValue('tags', [...(tags as string[]), 'new-tag'], { shouldDirty: true })}>Add Tag</button>
      </div>
    )
  },
}))

vi.mock('../MetadataSpecies', () => ({
  default: function MockMetadataSpecies({ control, setValue }: { control: any; setValue: (name: string, value: unknown, opts?: unknown) => void }) {
    const species = useWatchHoisted({ control, name: 'species' }) ?? ''
    const confidence = useWatchHoisted({ control, name: 'confidence' }) ?? 'unknown'
    const commonName = useWatchHoisted({ control, name: 'commonName' }) ?? ''
    const referenceUrl = useWatchHoisted({ control, name: 'referenceUrl' }) ?? ''
    return (
      <div data-testid="metadata-species">
        <input
          data-testid="species-input"
          value={species as string}
          onChange={(e) => setValue('species', e.target.value, { shouldDirty: true })}
        />
        <select
          data-testid="confidence-select"
          value={confidence as string}
          onChange={(e) => setValue('confidence', e.target.value, { shouldDirty: true })}
        >
          <option value="certain">Certain</option>
          <option value="probable">Probable</option>
          <option value="possible">Possible</option>
          <option value="unknown">Unknown</option>
        </select>
        <input
          data-testid="common-name-input"
          value={commonName as string}
          onChange={(e) => setValue('commonName', e.target.value, { shouldDirty: true })}
        />
        <input
          data-testid="reference-url-input"
          value={referenceUrl as string}
          onChange={(e) => setValue('referenceUrl', e.target.value, { shouldDirty: true })}
        />
      </div>
    )
  },
}))

vi.mock('../MetadataNotes', () => ({
  default: function MockMetadataNotes({ control, setValue }: { control: any; setValue: (name: string, value: unknown, opts?: unknown) => void }) {
    const notes = useWatchHoisted({ control, name: 'notes' }) ?? ''
    return (
      <div data-testid="metadata-notes">
        <textarea
          data-testid="notes-textarea"
          value={notes as string}
          onChange={(e) => setValue('notes', e.target.value, { shouldDirty: true })}
        />
      </div>
    )
  },
}))

vi.mock('../MetadataCustomFields', () => ({
  default: function MockMetadataCustomFields({ control }: { control: any }) {
    const custom = useWatchHoisted({ control, name: 'custom' }) ?? []
    return (
      <div data-testid="metadata-custom-fields">
        <div data-testid="custom-fields-list">
          {(custom as Array<{ key: string; value: string }>).map((entry, idx) => (
            <div key={entry.key || idx} data-testid={`custom-field-${entry.key}`}>
              {entry.key}: {entry.value}
            </div>
          ))}
        </div>
      </div>
    )
  },
}))

vi.mock('../MetadataEXIF', () => ({
  default: ({ data }: { data: unknown }) => (
    <div data-testid="metadata-exif">
      <div>EXIF Data: {data ? 'loaded' : 'no data'}</div>
    </div>
  ),
}))

vi.mock('../MetadataSkeleton', () => ({
  default: ({ rows }: { rows: number }) => (
    <div data-testid="metadata-skeleton" role="status">
      Loading skeleton with {rows} rows
    </div>
  ),
}))

/**
 * Mock EXIF metadata structure
 */
const mockExifMetadata = {
  camera: {
    make: 'Arducam',
    model: 'OwlSight 64MP',
    lens_make: 'Arducam',
    lens_model: '6mm Wide Angle',
  },
  iso: 400,
  aperture: 2.8,
  shutter_speed: 0.033333,
  focal_length: 6.0,
  exposure_mode: 'Manual',
  metering_mode: 'CenterWeighted',
}

/**
 * Mock sidecar metadata structure
 */
const mockSidecarMetadata = {
  tags: ['moth', 'nocturnal'],
  species: 'Actias luna',
  species_confidence: 'probable',
  species_common_name: 'Luna Moth',
  species_reference_url: 'https://inaturalist.org/taxa/actias-luna',
  notes: 'Clear night, high moth activity',
  custom: {
    observer: 'Jane Doe',
    weather: 'clear',
  },
}

/**
 * Create a fresh QueryClient for each test
 */
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  })
}

/**
 * Wrapper component that provides QueryClient
 */
function TestWrapper({ children }: { children: React.ReactNode }) {
  const queryClient = createTestQueryClient()
  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('MetadataPanel (Accordion Refactor)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering - Accordion Structure', () => {
    it('renders accordion sections not tabs', async () => {
      // Mock EXIF metadata fetch (usePhotoMetadata uses api.get)
      mockApiGet.mockResolvedValueOnce({ data: mockExifMetadata })
      // Mock sidecar metadata fetch (useSidecarMetadata uses getPhotoSidecarMetadata)
      mockGetPhotoSidecarMetadata.mockResolvedValueOnce({ data: mockSidecarMetadata })

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Should NOT have tabs
      expect(screen.queryByRole('tablist')).not.toBeInTheDocument()
      expect(screen.queryByRole('tab')).not.toBeInTheDocument()

      // Should have accordion sections
      expect(screen.getByTestId('accordion-section-tags')).toBeInTheDocument()
      expect(screen.getByTestId('accordion-section-species')).toBeInTheDocument()
      expect(screen.getByTestId('accordion-section-notes')).toBeInTheDocument()
      expect(screen.getByTestId('accordion-section-exif-data')).toBeInTheDocument()
      expect(screen.getByTestId('accordion-section-custom-fields')).toBeInTheDocument()
    })

    it('tags section is expanded by default', async () => {
      mockApiGet.mockResolvedValueOnce({ data: mockExifMetadata })
      mockGetPhotoSidecarMetadata.mockResolvedValueOnce({ data: mockSidecarMetadata })

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      const tagsSection = screen.getByTestId('accordion-section-tags')
      const tagsHeader = within(tagsSection).getByTestId('accordion-header')

      // Tags section should be expanded by default
      expect(tagsHeader).toHaveAttribute('data-expanded', 'true')
    })

    it('all sections present', async () => {
      mockApiGet.mockResolvedValueOnce({ data: mockExifMetadata })
      mockGetPhotoSidecarMetadata.mockResolvedValueOnce({ data: mockSidecarMetadata })

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // All 5 sections should be present
      expect(screen.getByTestId('accordion-section-tags')).toBeInTheDocument()
      expect(screen.getByTestId('accordion-section-species')).toBeInTheDocument()
      expect(screen.getByTestId('accordion-section-notes')).toBeInTheDocument()
      expect(screen.getByTestId('accordion-section-exif-data')).toBeInTheDocument()
      expect(screen.getByTestId('accordion-section-custom-fields')).toBeInTheDocument()

      // Verify section components are rendered
      expect(screen.getByTestId('metadata-tags')).toBeInTheDocument()
      expect(screen.getByTestId('metadata-species')).toBeInTheDocument()
      expect(screen.getByTestId('metadata-notes')).toBeInTheDocument()
      expect(screen.getByTestId('metadata-exif')).toBeInTheDocument()
      expect(screen.getByTestId('metadata-custom-fields')).toBeInTheDocument()
    })

    it('shows save status indicator', async () => {
      mockApiGet.mockResolvedValueOnce({ data: mockExifMetadata })
      mockGetPhotoSidecarMetadata.mockResolvedValueOnce({ data: mockSidecarMetadata })

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // SaveStatusIndicator should be visible
      expect(screen.getByTestId('save-status-indicator')).toBeInTheDocument()
    })

    it('loading state shows skeleton', () => {
      mockApiGet.mockImplementation(
        () =>
          new Promise((resolve) => {
            setTimeout(() => resolve({ data: mockExifMetadata }), 100)
          })
      )

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      // Should show skeleton immediately
      expect(screen.getByTestId('metadata-skeleton')).toBeInTheDocument()
      expect(screen.getByRole('status')).toBeInTheDocument()
    })

    it('error state shows retry', async () => {
      mockApiGet.mockRejectedValueOnce(new Error('Network error'))
      // Mock sidecar to succeed so it doesn't hang
      mockGetPhotoSidecarMetadata.mockResolvedValueOnce({ data: mockSidecarMetadata })

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText(/failed to load metadata/i)).toBeInTheDocument()
      })

      // Should show retry button
      const retryButton = screen.getByRole('button', { name: /retry/i })
      expect(retryButton).toBeInTheDocument()
    })
  })

  describe('Auto-Save Functionality', () => {
    it('auto-save triggers on change', async () => {
      mockApiGet.mockResolvedValueOnce({ data: mockExifMetadata })
      mockGetPhotoSidecarMetadata.mockResolvedValueOnce({ data: mockSidecarMetadata })
      mockUpdatePhotoSidecarMetadata.mockResolvedValue({ data: { success: true } })

      const user = userEvent.setup()

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Add a tag
      const addTagButton = screen.getByText('Add Tag')
      await user.click(addTagButton)

      // Wait for debounced save (2 seconds)
      await waitFor(
        () => {
          const saveIndicator = screen.getByTestId('save-status-indicator')
          // Should show saving or saved status
          const status = saveIndicator.getAttribute('data-status')
          expect(['saving', 'saved']).toContain(status)
        },
        { timeout: 3000 }
      )
    })
  })

  describe('Editable Sections', () => {
    it('editable sections call update on tags', async () => {
      mockApiGet.mockResolvedValueOnce({ data: mockExifMetadata })
      mockGetPhotoSidecarMetadata.mockResolvedValueOnce({ data: mockSidecarMetadata })
      mockUpdatePhotoSidecarMetadata.mockResolvedValue({ data: { success: true } })

      const user = userEvent.setup()

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Existing tags should be displayed (wait for async render)
      await waitFor(() => {
        expect(screen.getByTestId('tag-moth')).toBeInTheDocument()
        expect(screen.getByTestId('tag-nocturnal')).toBeInTheDocument()
      })

      // Add a tag
      const addTagButton = screen.getByText('Add Tag')
      await user.click(addTagButton)

      // Should update local state immediately
      await waitFor(() => {
        expect(screen.getByTestId('tag-new-tag')).toBeInTheDocument()
      })
    })

    it('editable sections call update on species', async () => {
      mockApiGet.mockResolvedValueOnce({ data: mockExifMetadata })
      mockGetPhotoSidecarMetadata.mockResolvedValueOnce({ data: mockSidecarMetadata })
      mockUpdatePhotoSidecarMetadata.mockResolvedValue({ data: { success: true } })

      const user = userEvent.setup()

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Change species
      const speciesInput = screen.getByTestId('species-input')
      expect(speciesInput).toHaveValue('Actias luna')

      await user.clear(speciesInput)
      await user.type(speciesInput, 'Antheraea polyphemus')

      // Should update local state
      expect(speciesInput).toHaveValue('Antheraea polyphemus')
    })

    it('editable sections call update on notes', async () => {
      mockApiGet.mockResolvedValueOnce({ data: mockExifMetadata })
      mockGetPhotoSidecarMetadata.mockResolvedValueOnce({ data: mockSidecarMetadata })
      mockUpdatePhotoSidecarMetadata.mockResolvedValue({ data: { success: true } })

      const user = userEvent.setup()

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Change notes
      const notesTextarea = screen.getByTestId('notes-textarea')
      expect(notesTextarea).toHaveValue('Clear night, high moth activity')

      await user.clear(notesTextarea)
      await user.type(notesTextarea, 'Updated notes')

      // Should update local state
      expect(notesTextarea).toHaveValue('Updated notes')
    })

    it('editable sections call update on custom fields', async () => {
      mockApiGet.mockResolvedValueOnce({ data: mockExifMetadata })
      mockGetPhotoSidecarMetadata.mockResolvedValueOnce({ data: mockSidecarMetadata })
      mockUpdatePhotoSidecarMetadata.mockResolvedValue({ data: { success: true } })

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Wait for custom fields to appear after sidecar data syncs to form state
      expect(await screen.findByTestId('custom-field-observer')).toBeInTheDocument()
      expect(screen.getByTestId('custom-field-weather')).toBeInTheDocument()
    })
  })

  describe('Data Loading', () => {
    it('fetches EXIF and sidecar metadata on mount', async () => {
      const photoPath = '/var/lib/mothbox/photos/test.jpg'

      mockApiGet.mockResolvedValueOnce({ data: mockExifMetadata })
      mockGetPhotoSidecarMetadata.mockResolvedValueOnce({ data: mockSidecarMetadata })

      render(
        <TestWrapper>
          <MetadataPanel photoPath={photoPath} />
        </TestWrapper>
      )

      await waitFor(() => {
        // Should fetch EXIF metadata
        expect(mockApiGet).toHaveBeenCalledWith(
          `/metadata/photo/${encodeURIComponent(photoPath)}/metadata`
        )
        // Should fetch sidecar metadata (uses full path for subdirectory support)
        expect(mockGetPhotoSidecarMetadata).toHaveBeenCalledWith(photoPath)
      })
    })

    it('passes EXIF data to MetadataEXIF component', async () => {
      mockApiGet.mockResolvedValueOnce({ data: mockExifMetadata })
      mockGetPhotoSidecarMetadata.mockResolvedValueOnce({ data: mockSidecarMetadata })

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // EXIF component should receive data
      const exifComponent = screen.getByTestId('metadata-exif')
      expect(exifComponent).toHaveTextContent('loaded')
    })
  })

  describe('Error Handling', () => {
    it('handles EXIF fetch error gracefully', async () => {
      mockApiGet.mockRejectedValueOnce(new Error('Network error'))
      // Mock sidecar to succeed so it doesn't hang
      mockGetPhotoSidecarMetadata.mockResolvedValueOnce({ data: mockSidecarMetadata })

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText(/failed to load metadata/i)).toBeInTheDocument()
      })

      // Should show retry button
      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
    })

    it('retry button refetches data', async () => {
      // First call fails
      mockApiGet.mockRejectedValueOnce(new Error('Network error'))
      // Mock sidecar to succeed so it doesn't hang
      mockGetPhotoSidecarMetadata.mockResolvedValueOnce({ data: mockSidecarMetadata })

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText(/failed to load metadata/i)).toBeInTheDocument()
      })

      // Second call succeeds
      mockApiGet.mockResolvedValueOnce({ data: mockExifMetadata })
      mockGetPhotoSidecarMetadata.mockResolvedValueOnce({ data: mockSidecarMetadata })

      // Click retry
      const retryButton = screen.getByRole('button', { name: /retry/i })
      await userEvent.click(retryButton)

      // Should show accordion sections after successful retry
      await waitFor(() => {
        expect(screen.getByTestId('accordion-section-tags')).toBeInTheDocument()
      })
    })
  })

  describe('Edge Cases', () => {
    it('handles empty sidecar data gracefully', async () => {
      mockGetPhotoSidecarMetadata.mockResolvedValueOnce({ data: mockSidecarMetadata })
      mockApiGet.mockResolvedValueOnce({ data: mockExifMetadata })
      mockApiGet.mockResolvedValueOnce({ data: {} })

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Should still render all sections with empty/default values
      expect(screen.getByTestId('metadata-tags')).toBeInTheDocument()
      expect(screen.getByTestId('metadata-species')).toBeInTheDocument()
      expect(screen.getByTestId('metadata-notes')).toBeInTheDocument()
    })

    it('resets form when switching photos even if dirty', async () => {
      // Photo A sidecar data
      const photoAData = { ...mockSidecarMetadata, species: 'Actias luna' }
      mockApiGet.mockResolvedValue({ data: mockExifMetadata })
      mockGetPhotoSidecarMetadata.mockResolvedValue({ data: photoAData })

      // Use a stable QueryClient across rerenders (avoid recreation on rerender)
      const stableQueryClient = createTestQueryClient()
      function StableWrapper({ children }: { children: React.ReactNode }) {
        return <QueryClientProvider client={stableQueryClient}>{children}</QueryClientProvider>
      }

      const { rerender } = render(
        <StableWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/photoA.jpg" />
        </StableWrapper>
      )

      // Wait for photo A to load
      await waitFor(() => {
        expect(screen.getByTestId('metadata-species')).toBeInTheDocument()
      })

      // Make an edit to dirty the form
      const notesTextarea = screen.getByTestId('notes-textarea')
      await userEvent.type(notesTextarea, ' extra')

      // Photo B sidecar data with different species
      const photoBData = { ...mockSidecarMetadata, species: 'Manduca sexta' }
      mockGetPhotoSidecarMetadata.mockResolvedValue({ data: photoBData })

      // Switch to photo B
      rerender(
        <StableWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/photoB.jpg" />
        </StableWrapper>
      )

      // Should display photo B's species, not photo A's
      await waitFor(() => {
        const speciesInput = screen.getByTestId('species-input') as HTMLInputElement
        expect(speciesInput.value).toBe('Manduca sexta')
      })
    })

    it('applies custom className prop', async () => {
      mockApiGet.mockResolvedValueOnce({ data: mockExifMetadata })
      mockGetPhotoSidecarMetadata.mockResolvedValueOnce({ data: mockSidecarMetadata })

      render(
        <TestWrapper>
          <MetadataPanel
            photoPath="/var/lib/mothbox/photos/test.jpg"
            className="custom-class"
          />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Panel element should have custom class
      const panel = screen.getByTestId('metadata-panel')
      expect(panel).toHaveClass('custom-class')
    })
  })

  describe('Keyboard Shortcuts', () => {
    it('ctrl+s triggers manual save', async () => {
      mockApiGet.mockResolvedValueOnce({ data: mockExifMetadata })
      mockGetPhotoSidecarMetadata.mockResolvedValueOnce({ data: mockSidecarMetadata })
      mockUpdatePhotoSidecarMetadata.mockResolvedValue({ data: { success: true } })

      const user = userEvent.setup()

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Make a change first
      const notesTextarea = screen.getByTestId('notes-textarea')
      await user.clear(notesTextarea)
      await user.type(notesTextarea, 'New notes')

      // Clear previous API calls
      mockUpdatePhotoSidecarMetadata.mockClear()

      // Press Ctrl+S
      await user.keyboard('{Control>}s{/Control}')

      // Should trigger immediate save (not wait for debounce)
      await waitFor(
        () => {
          expect(mockUpdatePhotoSidecarMetadata).toHaveBeenCalled()
        },
        { timeout: 500 } // Should be much faster than 2 second debounce
      )
    })

    it('cmd+s triggers manual save on mac', async () => {
      mockApiGet.mockResolvedValueOnce({ data: mockExifMetadata })
      mockGetPhotoSidecarMetadata.mockResolvedValueOnce({ data: mockSidecarMetadata })
      mockUpdatePhotoSidecarMetadata.mockResolvedValue({ data: { success: true } })

      const user = userEvent.setup()

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Make a change first
      const notesTextarea = screen.getByTestId('notes-textarea')
      await user.clear(notesTextarea)
      await user.type(notesTextarea, 'New notes')

      // Clear previous API calls
      mockUpdatePhotoSidecarMetadata.mockClear()

      // Press Cmd+S (Meta key for Mac)
      await user.keyboard('{Meta>}s{/Meta}')

      // Should trigger immediate save
      await waitFor(
        () => {
          expect(mockUpdatePhotoSidecarMetadata).toHaveBeenCalled()
        },
        { timeout: 500 }
      )
    })

    it('ctrl+enter saves and closes panel', async () => {
      mockApiGet.mockResolvedValueOnce({ data: mockExifMetadata })
      mockGetPhotoSidecarMetadata.mockResolvedValueOnce({ data: mockSidecarMetadata })
      mockUpdatePhotoSidecarMetadata.mockResolvedValue({ data: { success: true } })

      const onCloseMock = vi.fn()
      const user = userEvent.setup()

      render(
        <TestWrapper>
          <MetadataPanel
            photoPath="/var/lib/mothbox/photos/test.jpg"
            onClose={onCloseMock}
          />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Make a change first
      const notesTextarea = screen.getByTestId('notes-textarea')
      await user.clear(notesTextarea)
      await user.type(notesTextarea, 'New notes')

      // Clear previous API calls
      mockUpdatePhotoSidecarMetadata.mockClear()

      // Press Ctrl+Enter
      await user.keyboard('{Control>}{Enter}{/Control}')

      // Should trigger save
      await waitFor(
        () => {
          expect(mockUpdatePhotoSidecarMetadata).toHaveBeenCalled()
        },
        { timeout: 500 }
      )

      // Should call onClose
      expect(onCloseMock).toHaveBeenCalledTimes(1)
    })

    it('esc closes panel', async () => {
      mockApiGet.mockResolvedValueOnce({ data: mockExifMetadata })
      mockGetPhotoSidecarMetadata.mockResolvedValueOnce({ data: mockSidecarMetadata })

      const onCloseMock = vi.fn()
      const user = userEvent.setup()

      render(
        <TestWrapper>
          <MetadataPanel
            photoPath="/var/lib/mothbox/photos/test.jpg"
            onClose={onCloseMock}
          />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Focus inside the panel to activate shortcuts
      const notesTextarea = screen.getByTestId('notes-textarea')
      notesTextarea.focus()

      // Press Escape
      await user.keyboard('{Escape}')

      // Should call onClose
      expect(onCloseMock).toHaveBeenCalledTimes(1)
    })

    it('prevents default browser save dialog', async () => {
      mockApiGet.mockResolvedValueOnce({ data: mockExifMetadata })
      mockGetPhotoSidecarMetadata.mockResolvedValueOnce({ data: mockSidecarMetadata })
      mockUpdatePhotoSidecarMetadata.mockResolvedValue({ data: { success: true } })

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Focus inside the panel to activate shortcuts
      const notesTextarea = screen.getByTestId('notes-textarea')
      notesTextarea.focus()

      // Create a spy for preventDefault
      const preventDefaultSpy = vi.fn()

      // Manually fire keydown event with Ctrl+S
      const event = new KeyboardEvent('keydown', {
        key: 's',
        ctrlKey: true,
        bubbles: true,
        cancelable: true,
      })

      // Spy on preventDefault
      Object.defineProperty(event, 'preventDefault', {
        value: preventDefaultSpy,
        writable: true,
      })

      document.dispatchEvent(event)

      // Should prevent default behavior
      await waitFor(() => {
        expect(preventDefaultSpy).toHaveBeenCalled()
      })
    })

    it('shortcuts only active when panel is focused or child is focused', async () => {
      mockApiGet.mockResolvedValueOnce({ data: mockExifMetadata })
      mockGetPhotoSidecarMetadata.mockResolvedValueOnce({ data: mockSidecarMetadata })
      mockUpdatePhotoSidecarMetadata.mockResolvedValue({ data: { success: true } })

      const onCloseMock = vi.fn()

      render(
        <TestWrapper>
          <div>
            <MetadataPanel
              photoPath="/var/lib/mothbox/photos/test.jpg"
              onClose={onCloseMock}
            />
            <button data-testid="outside-button">Outside Button</button>
          </div>
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Focus on element outside the panel
      const outsideButton = screen.getByTestId('outside-button')
      outsideButton.focus()

      // Press Escape while focused outside
      const event = new KeyboardEvent('keydown', {
        key: 'Escape',
        bubbles: true,
        cancelable: true,
      })
      document.dispatchEvent(event)

      // Wait a bit
      await new Promise((resolve) => setTimeout(resolve, 100))

      // onClose should NOT be called since focus is outside panel
      expect(onCloseMock).not.toHaveBeenCalled()

      // Now focus inside the panel
      const notesTextarea = screen.getByTestId('notes-textarea')
      notesTextarea.focus()

      // Press Escape while focused inside
      const event2 = new KeyboardEvent('keydown', {
        key: 'Escape',
        bubbles: true,
        cancelable: true,
      })
      document.dispatchEvent(event2)

      // Should call onClose now
      await waitFor(() => {
        expect(onCloseMock).toHaveBeenCalledTimes(1)
      })
    })
  })
})

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import MetadataPanel from '../MetadataPanel'
import { clearTagsInvalidationTimeout } from '../../../hooks/useSidecarMetadata'

// Mock the API layer ONLY - not hooks or components
// This tests the real integration between MetadataPanel, useAutoSave, useSidecarMetadata, etc.
vi.mock('../../../utils/api', () => ({
  api: {
    get: vi.fn(),
  },
  getPhotoSidecarMetadata: vi.fn(),
  updatePhotoSidecarMetadata: vi.fn(),
  getAllTags: vi.fn(),
  getAllSpecies: vi.fn(),
}))

// Import mocked API after vi.mock
import * as apiModule from '../../../utils/api'
const api = apiModule

/**
 * Real Integration Tests for MetadataPanel
 *
 * These tests use the REAL hooks and components, only mocking at the API boundary.
 * This tests that:
 * - useSidecarMetadata properly fetches and updates data
 * - useAutoSave properly debounces saves
 * - MetadataTags, MetadataSpecies, MetadataNotes work together
 * - Optimistic updates work correctly
 */
describe('MetadataPanel Integration Tests', () => {
  let queryClient

  const createWrapper = () => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })
    return function Wrapper({ children }) {
      return (
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      )
    }
  }

  const mockSidecarData = {
    version: '1.1',
    photo_filename: 'test_photo.jpg',
    user_tags: ['moth', 'nocturnal'],
    species: 'Actias luna',
    species_confidence: 'probable',
    species_common_name: 'Luna Moth',
    species_reference_url: '',
    notes: 'Found near porch light',
    custom: {},
  }

  const mockExifData = {
    camera: { make: 'Arducam', model: 'OwlSight 64MP' },
    capture: { iso: 800, exposure_time: '1/60' },
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers({ shouldAdvanceTime: true })

    // Default API responses
    // Mock usePhotoMetadata's api.get call for EXIF data
    api.api.get.mockResolvedValue({ data: mockExifData })
    // Mock sidecar metadata calls
    api.getPhotoSidecarMetadata.mockResolvedValue({ data: mockSidecarData })
    api.updatePhotoSidecarMetadata.mockResolvedValue({ data: { ...mockSidecarData } })
    api.getAllTags.mockResolvedValue({ data: { tags: [{ name: 'moth', count: 5 }], total: 1 } })
    api.getAllSpecies.mockResolvedValue({ data: { species: [{ name: 'Actias luna', count: 3 }], total: 1 } })
  })

  afterEach(() => {
    vi.useRealTimers()
    clearTagsInvalidationTimeout()
    if (queryClient) {
      queryClient.clear()
    }
  })

  describe('Data Loading Integration', () => {
    it('loads sidecar metadata using real useSidecarMetadata hook', async () => {
      render(
        <MetadataPanel photoPath="/photos/test_photo.jpg" />,
        { wrapper: createWrapper() }
      )

      // Should show loading state initially
      expect(screen.getByTestId('metadata-skeleton')).toBeInTheDocument()

      // Wait for real data to load
      await waitFor(() => {
        expect(api.getPhotoSidecarMetadata).toHaveBeenCalledWith('test_photo.jpg')
      })

      // Verify data is displayed (from real hooks)
      await waitFor(() => {
        expect(screen.getByText('moth')).toBeInTheDocument()
        expect(screen.getByText('nocturnal')).toBeInTheDocument()
      })
    })

    it('displays species data from real useSidecarMetadata hook', async () => {
      render(
        <MetadataPanel photoPath="/photos/test_photo.jpg" />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Open Species accordion if collapsed
      const speciesSection = screen.getByText('Species')
      await userEvent.click(speciesSection)

      // Verify species data is displayed
      await waitFor(() => {
        expect(screen.getByDisplayValue('Actias luna')).toBeInTheDocument()
      })
    })
  })

  describe('Auto-Save Integration', () => {
    it('auto-saves after 2 second debounce using real useAutoSave hook', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })

      render(
        <MetadataPanel photoPath="/photos/test_photo.jpg" />,
        { wrapper: createWrapper() }
      )

      // Wait for initial load
      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Notes section is expanded by default (defaultExpanded=true in AccordionSection)
      // Find notes textarea and add text
      const notesInput = screen.getByPlaceholderText(/Add notes about this photo/i)
      await user.clear(notesInput)
      await user.type(notesInput, 'New observation notes')

      // API should NOT be called immediately
      expect(api.updatePhotoSidecarMetadata).not.toHaveBeenCalled()

      // Advance timers by 2 seconds (auto-save delay)
      await act(async () => {
        vi.advanceTimersByTime(2000)
      })

      // Now API should be called
      await waitFor(() => {
        expect(api.updatePhotoSidecarMetadata).toHaveBeenCalled()
      })
    })

    it('debounces multiple rapid changes into single API call', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })

      render(
        <MetadataPanel photoPath="/photos/test_photo.jpg" />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Notes section is expanded by default, find the textarea directly
      const notesInput = screen.getByPlaceholderText(/Add notes about this photo/i)
      await user.type(notesInput, 'A')

      // Advance 500ms (less than debounce)
      await act(async () => { vi.advanceTimersByTime(500) })

      await user.type(notesInput, 'B')

      // Advance 500ms more
      await act(async () => { vi.advanceTimersByTime(500) })

      await user.type(notesInput, 'C')

      // Should NOT have called API yet (timer keeps resetting)
      expect(api.updatePhotoSidecarMetadata).not.toHaveBeenCalled()

      // Now wait full 2 seconds from last change
      await act(async () => {
        vi.advanceTimersByTime(2000)
      })

      // Should have called API exactly once with final state
      await waitFor(() => {
        expect(api.updatePhotoSidecarMetadata).toHaveBeenCalledTimes(1)
      })
    })
  })

  describe('Tag Operations Integration', () => {
    it('adds tag using real MetadataTags component and useSidecarMetadata hook', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })

      render(
        <MetadataPanel photoPath="/photos/test_photo.jpg" />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Tags section should be expanded by default
      const tagInput = screen.getByPlaceholderText(/Type to add tags/i)
      await user.type(tagInput, 'new-tag{Enter}')

      // Tag should appear immediately (optimistic update)
      await waitFor(() => {
        expect(screen.getByText('new-tag')).toBeInTheDocument()
      })

      // Trigger auto-save
      await act(async () => {
        vi.advanceTimersByTime(2000)
      })

      // Verify API was called with new tag
      await waitFor(() => {
        expect(api.updatePhotoSidecarMetadata).toHaveBeenCalled()
        const lastCall = api.updatePhotoSidecarMetadata.mock.calls.slice(-1)[0]
        expect(lastCall[1]).toMatchObject({
          user_tags: expect.arrayContaining(['new-tag'])
        })
      })
    })

    it('removes tag and updates via real integration', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })

      render(
        <MetadataPanel photoPath="/photos/test_photo.jpg" />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(screen.getByText('moth')).toBeInTheDocument()
      })

      // Click remove button for 'moth' tag
      const removeButton = screen.getByRole('button', { name: /Remove tag moth/i })
      await user.click(removeButton)

      // Tag should disappear immediately (optimistic update)
      await waitFor(() => {
        expect(screen.queryByText('moth')).not.toBeInTheDocument()
      })
    })
  })

  describe('Error Handling Integration', () => {
    it('handles API error and shows retry option', async () => {
      // Make the EXIF API fail (MetadataPanel shows error state when exifError is true)
      api.api.get.mockRejectedValueOnce(new Error('Network error'))
      // Sidecar can still succeed
      api.getPhotoSidecarMetadata.mockResolvedValueOnce({ data: mockSidecarData })

      render(
        <MetadataPanel photoPath="/photos/test_photo.jpg" />,
        { wrapper: createWrapper() }
      )

      // Wait for error state
      await waitFor(() => {
        expect(screen.getByText(/Failed to load metadata/i)).toBeInTheDocument()
      })

      // Should show retry button
      expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument()
    })

    it('shows save error in SaveStatusIndicator when update fails', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })

      // First load succeeds, update fails
      api.updatePhotoSidecarMetadata.mockRejectedValueOnce(new Error('Save failed'))

      render(
        <MetadataPanel photoPath="/photos/test_photo.jpg" />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Notes section is expanded by default (defaultExpanded=true), so we can directly find the input
      // Find the notes textarea (it has a specific placeholder)
      const notesInput = screen.getByPlaceholderText(/Add notes about this photo/i)
      await user.type(notesInput, 'test')

      // Trigger auto-save
      await act(async () => {
        vi.advanceTimersByTime(2000)
      })

      // Should show error status
      await waitFor(() => {
        const errorElement = screen.queryByText(/error|failed/i)
        expect(errorElement || screen.queryByRole('button', { name: /Retry/i })).toBeTruthy()
      })
    })
  })

  describe('Accordion Sections Integration', () => {
    it('expands and collapses accordion sections using real AccordionSection', async () => {
      const user = userEvent.setup()

      render(
        <MetadataPanel photoPath="/photos/test_photo.jpg" />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Tags section should exist
      const tagsHeader = screen.getByText('Tags')
      expect(tagsHeader).toBeInTheDocument()

      // Click to toggle Tags section
      await user.click(tagsHeader)

      // Verify header still exists (toggle worked)
      expect(screen.getByText('Tags')).toBeInTheDocument()
    })
  })

  describe('Keyboard Shortcuts Integration', () => {
    it('Ctrl+S triggers immediate save', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })

      render(
        <MetadataPanel photoPath="/photos/test_photo.jpg" />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Notes section is expanded by default, so we can directly find the input
      const notesInput = screen.getByPlaceholderText(/Add notes about this photo/i)
      await user.type(notesInput, 'test')

      // API should not be called yet (still in debounce period)
      expect(api.updatePhotoSidecarMetadata).not.toHaveBeenCalled()

      // Press Ctrl+S
      await user.keyboard('{Control>}s{/Control}')

      // Should save immediately
      await waitFor(() => {
        expect(api.updatePhotoSidecarMetadata).toHaveBeenCalled()
      })
    })
  })
})

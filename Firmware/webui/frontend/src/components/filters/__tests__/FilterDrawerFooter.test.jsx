import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { FilterDrawerFooter } from '../FilterDrawerFooter'
import { FilterProvider } from '../../../contexts/FilterContext'

// Mock the useFilterPresets hook
vi.mock('../../../hooks/useFilterPresets', () => ({
  useFilterPresets: vi.fn(),
}))

// Import after mock
import { useFilterPresets } from '../../../hooks/useFilterPresets'

/**
 * Helper to render component with FilterProvider
 */
function renderWithProvider(ui) {
  return render(<FilterProvider>{ui}</FilterProvider>)
}

describe('FilterDrawerFooter', () => {
  let mockSavePreset
  let mockLoadPreset
  let mockDeletePreset

  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear()

    // Create fresh mock functions
    mockSavePreset = vi.fn()
    mockLoadPreset = vi.fn()
    mockDeletePreset = vi.fn()

    // Setup default mock implementation
    useFilterPresets.mockReturnValue({
      presets: [],
      savePreset: mockSavePreset,
      loadPreset: mockLoadPreset,
      deletePreset: mockDeletePreset,
      isLoading: false,
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders FilterPresetManager component', () => {
      renderWithProvider(<FilterDrawerFooter />)

      // FilterPresetManager should render its content
      expect(screen.getByText('Save as Preset')).toBeInTheDocument()
    })

    it('renders without errors', () => {
      expect(() => {
        renderWithProvider(<FilterDrawerFooter />)
      }).not.toThrow()
    })

    it('renders in empty state when no presets exist', () => {
      renderWithProvider(<FilterDrawerFooter />)

      expect(screen.getByText('No saved presets yet')).toBeInTheDocument()
      expect(screen.getByText('Save as Preset')).toBeInTheDocument()
    })

    it('renders preset list when presets exist', () => {
      const mockPresets = [
        {
          id: 'preset_1',
          name: 'Test Preset 1',
          filters: {},
          createdAt: '2024-01-01T00:00:00Z',
        },
        {
          id: 'preset_2',
          name: 'Test Preset 2',
          filters: {},
          createdAt: '2024-01-02T00:00:00Z',
        },
      ]

      useFilterPresets.mockReturnValue({
        presets: mockPresets,
        savePreset: mockSavePreset,
        loadPreset: mockLoadPreset,
        deletePreset: mockDeletePreset,
        isLoading: false,
      })

      renderWithProvider(<FilterDrawerFooter />)

      expect(screen.getByText('Test Preset 1')).toBeInTheDocument()
      expect(screen.getByText('Test Preset 2')).toBeInTheDocument()
      expect(screen.getByText('Saved Presets')).toBeInTheDocument()
    })

    it('renders loading state when presets are loading', () => {
      useFilterPresets.mockReturnValue({
        presets: [],
        savePreset: mockSavePreset,
        loadPreset: mockLoadPreset,
        deletePreset: mockDeletePreset,
        isLoading: true,
      })

      renderWithProvider(<FilterDrawerFooter />)

      expect(screen.getByText('Loading presets...')).toBeInTheDocument()
    })
  })

  describe('Integration with FilterPresetManager', () => {
    it('shows Save as Preset button from FilterPresetManager', () => {
      renderWithProvider(<FilterDrawerFooter />)

      const saveButton = screen.getByText('Save as Preset')
      expect(saveButton).toBeInTheDocument()
      expect(saveButton.tagName).toBe('BUTTON')
    })

    it('shows No saved presets yet message when no presets exist', () => {
      renderWithProvider(<FilterDrawerFooter />)

      const emptyMessage = screen.getByText('No saved presets yet')
      expect(emptyMessage).toBeInTheDocument()
    })

    it('shows saved preset chips when presets exist', () => {
      const mockPresets = [
        {
          id: 'preset_1',
          name: 'Moths Only',
          filters: { tags: { selected: ['moth'], matchMode: 'any' } },
          createdAt: '2024-01-01T00:00:00Z',
        },
        {
          id: 'preset_2',
          name: 'Night Photos',
          filters: { dateRange: '7days' },
          createdAt: '2024-01-02T00:00:00Z',
        },
      ]

      useFilterPresets.mockReturnValue({
        presets: mockPresets,
        savePreset: mockSavePreset,
        loadPreset: mockLoadPreset,
        deletePreset: mockDeletePreset,
        isLoading: false,
      })

      renderWithProvider(<FilterDrawerFooter />)

      // Should show preset names
      expect(screen.getByText('Moths Only')).toBeInTheDocument()
      expect(screen.getByText('Night Photos')).toBeInTheDocument()

      // Should show Saved Presets header
      expect(screen.getByText('Saved Presets')).toBeInTheDocument()
    })

    it('shows delete buttons on preset chips', () => {
      const mockPresets = [
        {
          id: 'preset_1',
          name: 'Test Preset',
          filters: {},
          createdAt: '2024-01-01T00:00:00Z',
        },
      ]

      useFilterPresets.mockReturnValue({
        presets: mockPresets,
        savePreset: mockSavePreset,
        loadPreset: mockLoadPreset,
        deletePreset: mockDeletePreset,
        isLoading: false,
      })

      renderWithProvider(<FilterDrawerFooter />)

      // Delete button should be present (with opacity-0 class for hover effect)
      const deleteButton = screen.getByLabelText('Delete preset: Test Preset')
      expect(deleteButton).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA labels from FilterPresetManager', () => {
      renderWithProvider(<FilterDrawerFooter />)

      // Save button should have aria-label
      const saveButton = screen.getByLabelText('Save current filters as preset')
      expect(saveButton).toBeInTheDocument()
    })

    it('has proper ARIA labels for preset buttons', () => {
      const mockPresets = [
        {
          id: 'preset_1',
          name: 'Test Preset',
          filters: {},
          createdAt: '2024-01-01T00:00:00Z',
        },
      ]

      useFilterPresets.mockReturnValue({
        presets: mockPresets,
        savePreset: mockSavePreset,
        loadPreset: mockLoadPreset,
        deletePreset: mockDeletePreset,
        isLoading: false,
      })

      renderWithProvider(<FilterDrawerFooter />)

      expect(screen.getByLabelText('Load preset: Test Preset')).toBeInTheDocument()
      expect(screen.getByLabelText('Delete preset: Test Preset')).toBeInTheDocument()
    })

    it('has keyboard navigable buttons', () => {
      const mockPresets = [
        {
          id: 'preset_1',
          name: 'Test Preset',
          filters: {},
          createdAt: '2024-01-01T00:00:00Z',
        },
      ]

      useFilterPresets.mockReturnValue({
        presets: mockPresets,
        savePreset: mockSavePreset,
        loadPreset: mockLoadPreset,
        deletePreset: mockDeletePreset,
        isLoading: false,
      })

      renderWithProvider(<FilterDrawerFooter />)

      // All buttons should be focusable
      const loadButton = screen.getByLabelText('Load preset: Test Preset')
      expect(loadButton.tabIndex).toBeGreaterThanOrEqual(0)

      const saveButton = screen.getByLabelText('Save current filters as preset')
      expect(saveButton.tabIndex).toBeGreaterThanOrEqual(0)
    })
  })

  describe('Dark Mode Support', () => {
    it('renders FilterPresetManager with dark mode support', () => {
      const mockPresets = [
        {
          id: 'preset_1',
          name: 'Test Preset',
          filters: {},
          createdAt: '2024-01-01T00:00:00Z',
        },
      ]

      useFilterPresets.mockReturnValue({
        presets: mockPresets,
        savePreset: mockSavePreset,
        loadPreset: mockLoadPreset,
        deletePreset: mockDeletePreset,
        isLoading: false,
      })

      const { container } = renderWithProvider(<FilterDrawerFooter />)

      // FilterPresetManager should have buttons with hover states
      const presetButtons = container.querySelectorAll('button')
      expect(presetButtons.length).toBeGreaterThan(0)

      // Check that buttons have some hover styling
      const hasHoverStyles = Array.from(presetButtons).some(button =>
        button.className.includes('hover:')
      )
      expect(hasHoverStyles).toBe(true)
    })

    it('save button has dark mode styling', () => {
      renderWithProvider(<FilterDrawerFooter />)

      const saveButton = screen.getByText('Save as Preset')
      // Save button should have dark mode disabled state styling
      expect(saveButton).toHaveClass('dark:disabled:bg-gray-700')
    })
  })

  describe('Edge Cases', () => {
    it('handles empty preset list gracefully', () => {
      useFilterPresets.mockReturnValue({
        presets: [],
        savePreset: mockSavePreset,
        loadPreset: mockLoadPreset,
        deletePreset: mockDeletePreset,
        isLoading: false,
      })

      renderWithProvider(<FilterDrawerFooter />)

      expect(screen.getByText('No saved presets yet')).toBeInTheDocument()
      expect(screen.queryByText('Saved Presets')).not.toBeInTheDocument()
    })

    it('handles multiple presets correctly', () => {
      const mockPresets = Array.from({ length: 5 }, (_, i) => ({
        id: `preset_${i + 1}`,
        name: `Preset ${i + 1}`,
        filters: {},
        createdAt: `2024-01-0${i + 1}T00:00:00Z`,
      }))

      useFilterPresets.mockReturnValue({
        presets: mockPresets,
        savePreset: mockSavePreset,
        loadPreset: mockLoadPreset,
        deletePreset: mockDeletePreset,
        isLoading: false,
      })

      renderWithProvider(<FilterDrawerFooter />)

      mockPresets.forEach((preset) => {
        expect(screen.getByText(preset.name)).toBeInTheDocument()
      })
    })

    it('handles very long preset names with truncation', () => {
      const mockPresets = [
        {
          id: 'preset_1',
          name: 'This is a very long preset name that should be truncated in the UI',
          filters: {},
          createdAt: '2024-01-01T00:00:00Z',
        },
      ]

      useFilterPresets.mockReturnValue({
        presets: mockPresets,
        savePreset: mockSavePreset,
        loadPreset: mockLoadPreset,
        deletePreset: mockDeletePreset,
        isLoading: false,
      })

      renderWithProvider(<FilterDrawerFooter />)

      const presetName = screen.getByText(
        'This is a very long preset name that should be truncated in the UI'
      )
      expect(presetName).toHaveClass('truncate')
    })

    it('handles rapid re-renders without errors', () => {
      const { rerender } = renderWithProvider(<FilterDrawerFooter />)

      // Re-render multiple times
      rerender(
        <FilterProvider>
          <FilterDrawerFooter />
        </FilterProvider>
      )

      rerender(
        <FilterProvider>
          <FilterDrawerFooter />
        </FilterProvider>
      )

      expect(screen.getByText('Save as Preset')).toBeInTheDocument()
    })
  })

  describe('Component Structure', () => {
    it('renders as a wrapper for FilterPresetManager', () => {
      const { container } = renderWithProvider(<FilterDrawerFooter />)

      // Component should exist and contain FilterPresetManager content
      expect(container.querySelector('button')).toBeInTheDocument()
    })

    it('preserves FilterPresetManager functionality', () => {
      const mockPresets = [
        {
          id: 'preset_1',
          name: 'Test Preset',
          filters: { tags: { selected: ['moth'], matchMode: 'any' } },
          createdAt: '2024-01-01T00:00:00Z',
        },
      ]

      useFilterPresets.mockReturnValue({
        presets: mockPresets,
        savePreset: mockSavePreset,
        loadPreset: mockLoadPreset,
        deletePreset: mockDeletePreset,
        isLoading: false,
      })

      renderWithProvider(<FilterDrawerFooter />)

      // All FilterPresetManager elements should be present
      expect(screen.getByLabelText('Load preset: Test Preset')).toBeInTheDocument()
      expect(screen.getByLabelText('Delete preset: Test Preset')).toBeInTheDocument()
      expect(screen.getByLabelText('Save current filters as preset')).toBeInTheDocument()
    })
  })
})

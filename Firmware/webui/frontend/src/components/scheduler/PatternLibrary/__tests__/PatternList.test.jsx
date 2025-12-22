import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import PatternList from '../PatternList'
import { useBuiltinPatterns } from '../../../../hooks/useEventPatterns'

// Mock the hook
vi.mock('../../../../hooks/useEventPatterns', () => ({
  useBuiltinPatterns: vi.fn()
}))

// Mock child components
vi.mock('../PatternCard', () => ({
  default: ({ pattern, onClick, onSelect, isSelected }) => (
    <div
      data-testid={`pattern-card-${pattern.pattern_id}`}
      data-selected={isSelected}
    >
      <h3>{pattern.name}</h3>
      <p>{pattern.description}</p>
      <button onClick={() => onClick?.()}>View Details</button>
      <button onClick={() => onSelect?.()}>Use Pattern</button>
    </div>
  )
}))

vi.mock('../PatternFilters', () => ({
  default: ({
    category,
    onCategoryChange,
    viewMode,
    onViewModeChange,
    searchQuery,
    onSearchChange,
    selectedTags,
    onTagsChange,
    availableTags,
    showViewToggle
  }) => (
    <div data-testid="pattern-filters">
      <button onClick={() => onCategoryChange('all')}>All</button>
      <button onClick={() => onCategoryChange('built-in')}>Built-in</button>
      <button onClick={() => onCategoryChange('user')}>User</button>
      {showViewToggle && (
        <>
          <button onClick={() => onViewModeChange('grid')}>Grid</button>
          <button onClick={() => onViewModeChange('list')}>List</button>
          <input
            placeholder="Search..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
          />
          {availableTags.map(({ tag, count }) => (
            <button
              key={tag}
              onClick={() => {
                const newTags = selectedTags.includes(tag)
                  ? selectedTags.filter(t => t !== tag)
                  : [...selectedTags, tag]
                onTagsChange(newTags)
              }}
              data-testid={`tag-${tag}`}
            >
              {tag} ({count})
            </button>
          ))}
        </>
      )}
    </div>
  )
}))

vi.mock('../PatternDetailsDrawer', () => ({
  default: ({ isOpen, pattern, onClose, onSelect }) => (
    isOpen && pattern ? (
      <div role="dialog" data-testid="pattern-details-drawer">
        <h2>{pattern.name}</h2>
        <button onClick={onClose}>Close</button>
        <button onClick={() => onSelect?.(pattern)}>Use This Pattern</button>
      </div>
    ) : null
  )
}))

describe('PatternList', () => {
  const mockPatterns = [
    {
      pattern_id: 'uv_capture_cycle',
      name: 'UV Capture Cycle',
      description: 'Turn on UV lights, capture photo, turn off',
      actions: [{ type: 'gpio_on', pin: 'Relay_Ch1' }],
      category: 'built-in',
      tags: ['uv', 'capture'],
      duration_minutes: 15
    },
    {
      pattern_id: 'night_timelapse',
      name: 'Night Timelapse',
      description: 'Capture photos throughout the night',
      actions: [{ type: 'take_photo' }],
      category: 'built-in',
      tags: ['timelapse', 'capture'],
      duration_minutes: 480
    },
    {
      pattern_id: 'custom_pattern',
      name: 'Custom Pattern',
      description: 'User-created pattern',
      actions: [],
      category: 'user',
      tags: ['custom'],
      duration_minutes: 10
    }
  ]

  const mockHookReturn = {
    data: {
      patterns: mockPatterns,
      total: 3,
      warnings: []
    },
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn()
  }

  beforeEach(() => {
    vi.clearAllMocks()
    useBuiltinPatterns.mockReturnValue(mockHookReturn)
  })

  describe('Data Fetching Tests', () => {
    it('shows loading skeleton while isLoading=true', () => {
      useBuiltinPatterns.mockReturnValue({
        ...mockHookReturn,
        isLoading: true,
        data: null
      })

      render(<PatternList onPatternSelect={vi.fn()} />)

      expect(screen.getByTestId('loading-skeleton')).toBeInTheDocument()
      expect(screen.queryByTestId('pattern-filters')).not.toBeInTheDocument()
    })

    it('renders PatternCard for each pattern after loading', () => {
      render(<PatternList onPatternSelect={vi.fn()} />)

      expect(screen.getByTestId('pattern-card-uv_capture_cycle')).toBeInTheDocument()
      expect(screen.getByTestId('pattern-card-night_timelapse')).toBeInTheDocument()
      expect(screen.getByTestId('pattern-card-custom_pattern')).toBeInTheDocument()
    })

    it('shows error message when isError=true', () => {
      useBuiltinPatterns.mockReturnValue({
        ...mockHookReturn,
        isLoading: false,
        isError: true,
        error: { message: 'Failed to load patterns' },
        data: null
      })

      render(<PatternList onPatternSelect={vi.fn()} />)

      expect(screen.getByRole('heading', { name: /Failed to load patterns/i })).toBeInTheDocument()
    })

    it('shows retry button on error', () => {
      useBuiltinPatterns.mockReturnValue({
        ...mockHookReturn,
        isLoading: false,
        isError: true,
        error: { message: 'Network error' },
        data: null
      })

      render(<PatternList onPatternSelect={vi.fn()} />)

      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
    })

    it('retry button calls refetch', async () => {
      const user = userEvent.setup()
      const mockRefetch = vi.fn()

      useBuiltinPatterns.mockReturnValue({
        ...mockHookReturn,
        isLoading: false,
        isError: true,
        error: { message: 'Network error' },
        data: null,
        refetch: mockRefetch
      })

      render(<PatternList onPatternSelect={vi.fn()} />)

      const retryButton = screen.getByRole('button', { name: /retry/i })
      await user.click(retryButton)

      expect(mockRefetch).toHaveBeenCalledOnce()
    })

    it('shows empty state when patterns array is empty', () => {
      useBuiltinPatterns.mockReturnValue({
        ...mockHookReturn,
        data: {
          patterns: [],
          total: 0,
          warnings: []
        }
      })

      render(<PatternList onPatternSelect={vi.fn()} />)

      expect(screen.getByText(/no patterns available/i)).toBeInTheDocument()
    })

    it('shows warning banner if data.warnings has items', () => {
      useBuiltinPatterns.mockReturnValue({
        ...mockHookReturn,
        data: {
          ...mockHookReturn.data,
          warnings: ['Some patterns could not be loaded']
        }
      })

      render(<PatternList onPatternSelect={vi.fn()} />)

      expect(screen.getByText(/Some patterns could not be loaded/i)).toBeInTheDocument()
    })
  })

  describe('Grid View Tests', () => {
    it('renders patterns in grid layout by default', () => {
      render(<PatternList onPatternSelect={vi.fn()} />)

      const grid = screen.getByTestId('pattern-grid')
      expect(grid).toBeInTheDocument()
      expect(grid).toHaveClass('grid')
    })

    it('grid has responsive columns (1 on mobile, 2 on tablet, 3 on desktop)', () => {
      render(<PatternList onPatternSelect={vi.fn()} />)

      const grid = screen.getByTestId('pattern-grid')
      expect(grid).toHaveClass('grid-cols-1')
      expect(grid).toHaveClass('md:grid-cols-2')
      expect(grid).toHaveClass('lg:grid-cols-3')
    })

    it('each pattern rendered with PatternCard', () => {
      render(<PatternList onPatternSelect={vi.fn()} />)

      mockPatterns.forEach(pattern => {
        expect(screen.getByTestId(`pattern-card-${pattern.pattern_id}`)).toBeInTheDocument()
      })
    })

    it('cards are properly spaced with gap', () => {
      render(<PatternList onPatternSelect={vi.fn()} />)

      const grid = screen.getByTestId('pattern-grid')
      expect(grid).toHaveClass('gap-4')
    })
  })

  describe('List View Tests', () => {
    it('renders patterns in list layout when viewMode=list', async () => {
      const user = userEvent.setup()
      render(<PatternList onPatternSelect={vi.fn()} mode="standalone" />)

      const listButton = screen.getByRole('button', { name: 'List' })
      await user.click(listButton)

      const list = screen.getByTestId('pattern-list')
      expect(list).toBeInTheDocument()
      expect(list).toHaveClass('flex')
      expect(list).toHaveClass('flex-col')
    })

    it('list items are stacked vertically', async () => {
      const user = userEvent.setup()
      render(<PatternList onPatternSelect={vi.fn()} mode="standalone" />)

      const listButton = screen.getByRole('button', { name: 'List' })
      await user.click(listButton)

      const list = screen.getByTestId('pattern-list')
      expect(list).toHaveClass('flex-col')
    })

    it('each item has full width', async () => {
      const user = userEvent.setup()
      render(<PatternList onPatternSelect={vi.fn()} mode="standalone" />)

      const listButton = screen.getByRole('button', { name: 'List' })
      await user.click(listButton)

      const list = screen.getByTestId('pattern-list')
      expect(list).toHaveClass('space-y-4')
    })
  })

  describe('Filtering Tests (Standalone Mode)', () => {
    it('filters by category correctly (built-in/user/all)', async () => {
      const user = userEvent.setup()
      render(<PatternList onPatternSelect={vi.fn()} mode="standalone" />)

      // Initially shows all patterns
      expect(screen.getByTestId('pattern-card-uv_capture_cycle')).toBeInTheDocument()
      expect(screen.getByTestId('pattern-card-custom_pattern')).toBeInTheDocument()

      // Filter by built-in
      const builtinButton = screen.getByRole('button', { name: 'Built-in' })
      await user.click(builtinButton)

      expect(screen.getByTestId('pattern-card-uv_capture_cycle')).toBeInTheDocument()
      expect(screen.queryByTestId('pattern-card-custom_pattern')).not.toBeInTheDocument()

      // Filter by user
      const userButton = screen.getByRole('button', { name: 'User' })
      await user.click(userButton)

      expect(screen.queryByTestId('pattern-card-uv_capture_cycle')).not.toBeInTheDocument()
      expect(screen.getByTestId('pattern-card-custom_pattern')).toBeInTheDocument()

      // Back to all
      const allButton = screen.getByRole('button', { name: 'All' })
      await user.click(allButton)

      expect(screen.getByTestId('pattern-card-uv_capture_cycle')).toBeInTheDocument()
      expect(screen.getByTestId('pattern-card-custom_pattern')).toBeInTheDocument()
    })

    it('filters by selected tags (any match)', async () => {
      const user = userEvent.setup()
      render(<PatternList onPatternSelect={vi.fn()} mode="standalone" />)

      // Click 'capture' tag
      const captureTag = screen.getByTestId('tag-capture')
      await user.click(captureTag)

      // Should show patterns with 'capture' tag
      expect(screen.getByTestId('pattern-card-uv_capture_cycle')).toBeInTheDocument()
      expect(screen.getByTestId('pattern-card-night_timelapse')).toBeInTheDocument()
      expect(screen.queryByTestId('pattern-card-custom_pattern')).not.toBeInTheDocument()

      // Click 'custom' tag as well
      const customTag = screen.getByTestId('tag-custom')
      await user.click(customTag)

      // Should show patterns with 'capture' OR 'custom' tag
      expect(screen.getByTestId('pattern-card-uv_capture_cycle')).toBeInTheDocument()
      expect(screen.getByTestId('pattern-card-night_timelapse')).toBeInTheDocument()
      expect(screen.getByTestId('pattern-card-custom_pattern')).toBeInTheDocument()
    })

    it('filters by search query (matches name or description)', async () => {
      const user = userEvent.setup()
      render(<PatternList onPatternSelect={vi.fn()} mode="standalone" />)

      const searchInput = screen.getByPlaceholderText('Search...')
      await user.type(searchInput, 'timelapse')

      expect(screen.queryByTestId('pattern-card-uv_capture_cycle')).not.toBeInTheDocument()
      expect(screen.getByTestId('pattern-card-night_timelapse')).toBeInTheDocument()
      expect(screen.queryByTestId('pattern-card-custom_pattern')).not.toBeInTheDocument()
    })

    it('shows "No patterns match your filters" when filters yield no results', async () => {
      const user = userEvent.setup()
      render(<PatternList onPatternSelect={vi.fn()} mode="standalone" />)

      const searchInput = screen.getByPlaceholderText('Search...')
      await user.type(searchInput, 'nonexistent')

      expect(screen.getByText(/no patterns match your filters/i)).toBeInTheDocument()
      expect(screen.queryByTestId('pattern-card-uv_capture_cycle')).not.toBeInTheDocument()
    })

    it('reset button clears all filters', async () => {
      const user = userEvent.setup()
      render(<PatternList onPatternSelect={vi.fn()} mode="standalone" />)

      // Apply filters
      const builtinButton = screen.getByRole('button', { name: 'Built-in' })
      await user.click(builtinButton)

      const searchInput = screen.getByPlaceholderText('Search...')
      await user.type(searchInput, 'UV')

      expect(screen.getByTestId('pattern-card-uv_capture_cycle')).toBeInTheDocument()
      expect(screen.queryByTestId('pattern-card-night_timelapse')).not.toBeInTheDocument()

      // Reset filters
      const resetButton = screen.getByRole('button', { name: /reset/i })
      await user.click(resetButton)

      // Should show all patterns again
      expect(screen.getByTestId('pattern-card-uv_capture_cycle')).toBeInTheDocument()
      expect(screen.getByTestId('pattern-card-night_timelapse')).toBeInTheDocument()
      expect(screen.getByTestId('pattern-card-custom_pattern')).toBeInTheDocument()
    })

    it('filtered count displayed (e.g., "Showing 3 of 10 patterns")', () => {
      render(<PatternList onPatternSelect={vi.fn()} mode="standalone" />)

      expect(screen.getByText(/Showing 3 of 3 patterns/i)).toBeInTheDocument()
    })

    it('filtered count updates when filters applied', async () => {
      const user = userEvent.setup()
      render(<PatternList onPatternSelect={vi.fn()} mode="standalone" />)

      expect(screen.getByText(/Showing 3 of 3 patterns/i)).toBeInTheDocument()

      const builtinButton = screen.getByRole('button', { name: 'Built-in' })
      await user.click(builtinButton)

      expect(screen.getByText(/Showing 2 of 3 patterns/i)).toBeInTheDocument()
    })
  })

  describe('Selection Tests', () => {
    it('pattern card click opens details drawer (standalone mode)', async () => {
      const user = userEvent.setup()
      render(<PatternList onPatternSelect={vi.fn()} mode="standalone" />)

      const card = screen.getByTestId('pattern-card-uv_capture_cycle')
      const viewDetailsButton = within(card).getByRole('button', { name: 'View Details' })

      await user.click(viewDetailsButton)

      await waitFor(() => {
        expect(screen.getByTestId('pattern-details-drawer')).toBeInTheDocument()
      })
    })

    it('pattern card click calls onPatternSelect (embedded mode - no drawer)', async () => {
      const user = userEvent.setup()
      const onPatternSelect = vi.fn()
      render(<PatternList onPatternSelect={onPatternSelect} mode="embedded" />)

      const card = screen.getByTestId('pattern-card-uv_capture_cycle')
      const viewDetailsButton = within(card).getByRole('button', { name: 'View Details' })

      await user.click(viewDetailsButton)

      expect(onPatternSelect).toHaveBeenCalledWith(mockPatterns[0])
      expect(screen.queryByTestId('pattern-details-drawer')).not.toBeInTheDocument()
    })

    it('"Use Pattern" button click calls onPatternSelect with pattern', async () => {
      const user = userEvent.setup()
      const onPatternSelect = vi.fn()
      render(<PatternList onPatternSelect={onPatternSelect} />)

      const card = screen.getByTestId('pattern-card-uv_capture_cycle')
      const usePatternButton = within(card).getByRole('button', { name: 'Use Pattern' })

      await user.click(usePatternButton)

      expect(onPatternSelect).toHaveBeenCalledWith(mockPatterns[0])
    })

    it('selected pattern (matching selectedPatternId) shows isSelected=true', () => {
      render(
        <PatternList
          onPatternSelect={vi.fn()}
          selectedPatternId="uv_capture_cycle"
        />
      )

      const selectedCard = screen.getByTestId('pattern-card-uv_capture_cycle')
      expect(selectedCard).toHaveAttribute('data-selected', 'true')

      const unselectedCard = screen.getByTestId('pattern-card-night_timelapse')
      expect(unselectedCard).toHaveAttribute('data-selected', 'false')
    })
  })

  describe('Mode Tests', () => {
    it('standalone mode: Shows PatternFilters with all options', () => {
      render(<PatternList onPatternSelect={vi.fn()} mode="standalone" />)

      expect(screen.getByTestId('pattern-filters')).toBeInTheDocument()
      expect(screen.getByPlaceholderText('Search...')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Grid' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'List' })).toBeInTheDocument()
    })

    it('standalone mode: Opens PatternDetailsDrawer on card click', async () => {
      const user = userEvent.setup()
      render(<PatternList onPatternSelect={vi.fn()} mode="standalone" />)

      const card = screen.getByTestId('pattern-card-uv_capture_cycle')
      const viewDetailsButton = within(card).getByRole('button', { name: 'View Details' })

      await user.click(viewDetailsButton)

      await waitFor(() => {
        expect(screen.getByTestId('pattern-details-drawer')).toBeInTheDocument()
      })
    })

    it('embedded mode: Shows only category filter, no view toggle', () => {
      render(<PatternList onPatternSelect={vi.fn()} mode="embedded" />)

      expect(screen.getByTestId('pattern-filters')).toBeInTheDocument()
      expect(screen.queryByPlaceholderText('Search...')).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: 'Grid' })).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: 'List' })).not.toBeInTheDocument()
    })

    it('embedded mode: No drawer, card click calls onPatternSelect directly', async () => {
      const user = userEvent.setup()
      const onPatternSelect = vi.fn()
      render(<PatternList onPatternSelect={onPatternSelect} mode="embedded" />)

      const card = screen.getByTestId('pattern-card-uv_capture_cycle')
      const viewDetailsButton = within(card).getByRole('button', { name: 'View Details' })

      await user.click(viewDetailsButton)

      expect(onPatternSelect).toHaveBeenCalledWith(mockPatterns[0])
      expect(screen.queryByTestId('pattern-details-drawer')).not.toBeInTheDocument()
    })
  })

  describe('Integration Tests', () => {
    it('uses useBuiltinPatterns() hook correctly', () => {
      render(<PatternList onPatternSelect={vi.fn()} />)

      expect(useBuiltinPatterns).toHaveBeenCalled()
    })

    it('state persists across filter changes (drawer stays open)', async () => {
      const user = userEvent.setup()
      render(<PatternList onPatternSelect={vi.fn()} mode="standalone" />)

      // Open drawer
      const card = screen.getByTestId('pattern-card-uv_capture_cycle')
      const viewDetailsButton = within(card).getByRole('button', { name: 'View Details' })
      await user.click(viewDetailsButton)

      await waitFor(() => {
        expect(screen.getByTestId('pattern-details-drawer')).toBeInTheDocument()
      })

      // Change filter
      const builtinButton = screen.getByRole('button', { name: 'Built-in' })
      await user.click(builtinButton)

      // Drawer should still be open
      expect(screen.getByTestId('pattern-details-drawer')).toBeInTheDocument()
    })
  })

  describe('Available Tags Computation', () => {
    it('computes available tags from patterns', () => {
      render(<PatternList onPatternSelect={vi.fn()} mode="standalone" />)

      // Tags should be rendered - check for data-testid tag buttons
      const tagButtons = screen.getAllByRole('button').filter(btn =>
        btn.getAttribute('data-testid')?.startsWith('tag-')
      )

      // Should have tags from all patterns
      expect(tagButtons.length).toBeGreaterThan(0)
    })
  })

  describe('Drawer Integration', () => {
    it('opens drawer when card is clicked in standalone mode', async () => {
      const user = userEvent.setup()
      render(<PatternList onPatternSelect={vi.fn()} mode="standalone" />)

      // Click on View Details button in pattern card (triggers onClick)
      const viewDetailsButton = within(screen.getByTestId('pattern-card-uv_capture_cycle'))
        .getByRole('button', { name: 'View Details' })
      await user.click(viewDetailsButton)

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument()
      })
    })
  })
})

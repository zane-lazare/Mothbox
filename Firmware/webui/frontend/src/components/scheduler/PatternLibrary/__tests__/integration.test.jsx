/**
 * Integration tests for Pattern Library components (Issue #225)
 *
 * Tests the interaction between PatternList, PatternCard,
 * PatternFilters, and PatternDetailsDrawer components.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { PatternList, PatternCard, PatternDetailsDrawer, PatternFilters } from '../index'
import { useBuiltinPatterns } from '../../../../hooks/useEventPatterns'

// Mock the hook
vi.mock('../../../../hooks/useEventPatterns', () => ({
  useBuiltinPatterns: vi.fn(),
}))

// Test data
const mockPatterns = [
  {
    pattern_id: 'uv_capture_cycle',
    name: 'UV Capture Cycle',
    description: 'Turn on UV lights, wait 5 minutes, capture photo, turn off lights',
    actions: [
      { action_type: 'gpio', action_name: 'attract_on', offset_minutes: 0, description: 'Turn on UV' },
      { action_type: 'camera', action_name: 'takephoto', offset_minutes: 5, description: 'Capture' },
      { action_type: 'gpio', action_name: 'attract_off', offset_minutes: 15, description: 'Turn off UV' },
    ],
    category: 'built-in',
    tags: ['uv', 'capture', 'moth'],
    duration_minutes: 15,
    source_schedule: 'nightly_moth_survey',
  },
  {
    pattern_id: 'simple_photo',
    name: 'Simple Photo',
    description: 'Just capture a photo',
    actions: [
      { action_type: 'camera', action_name: 'takephoto', offset_minutes: 0, description: 'Take photo' },
    ],
    category: 'user',
    tags: ['photo', 'simple'],
    duration_minutes: 0,
  },
  {
    pattern_id: 'dawn_capture',
    name: 'Dawn Capture',
    description: 'Capture at dawn with flash',
    actions: [
      { action_type: 'gpio', action_name: 'flash_on', offset_minutes: 0 },
      { action_type: 'camera', action_name: 'takephoto', offset_minutes: 1 },
      { action_type: 'gpio', action_name: 'flash_off', offset_minutes: 2 },
    ],
    category: 'built-in',
    tags: ['dawn', 'flash'],
    duration_minutes: 2,
  },
]

// Helper to create QueryClient wrapper
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
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

describe('Pattern Library Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useBuiltinPatterns.mockReturnValue({
      data: { patterns: mockPatterns, total: 3, warnings: [] },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    })
  })

  describe('Module Exports', () => {
    it('exports PatternList component', () => {
      expect(PatternList).toBeDefined()
      expect(typeof PatternList).toBe('function')
    })

    it('exports PatternCard component', () => {
      expect(PatternCard).toBeDefined()
    })

    it('exports PatternDetailsDrawer component', () => {
      expect(PatternDetailsDrawer).toBeDefined()
    })

    it('exports PatternFilters component', () => {
      expect(PatternFilters).toBeDefined()
    })
  })

  describe('Full User Workflow - Standalone Mode', () => {
    it('loads and displays patterns', async () => {
      render(
        <PatternList onPatternSelect={vi.fn()} />,
        { wrapper: createWrapper() }
      )

      // Wait for patterns to load
      await waitFor(() => {
        expect(screen.getByText('UV Capture Cycle')).toBeInTheDocument()
      })

      // Verify all patterns rendered
      expect(screen.getByText('Simple Photo')).toBeInTheDocument()
      expect(screen.getByText('Dawn Capture')).toBeInTheDocument()
    })

    it('filters by category', async () => {
      const user = userEvent.setup()

      render(
        <PatternList onPatternSelect={vi.fn()} />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(screen.getByText('UV Capture Cycle')).toBeInTheDocument()
      })

      // Filter by category - click "Built-in"
      await user.click(screen.getByRole('button', { name: /built-in/i }))

      // Simple Photo (user category) should be filtered out
      await waitFor(() => {
        expect(screen.queryByText('Simple Photo')).not.toBeInTheDocument()
      })

      // UV Capture Cycle and Dawn Capture should remain
      expect(screen.getByText('UV Capture Cycle')).toBeInTheDocument()
      expect(screen.getByText('Dawn Capture')).toBeInTheDocument()
    })

    it('opens drawer on card click and allows selecting pattern', async () => {
      const user = userEvent.setup()
      const onPatternSelect = vi.fn()

      render(
        <PatternList onPatternSelect={onPatternSelect} />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(screen.getByText('UV Capture Cycle')).toBeInTheDocument()
      })

      // Find and click on the UV Capture Cycle card
      const uvCardHeading = screen.getByText('UV Capture Cycle')
      const uvCard = uvCardHeading.closest('article') || uvCardHeading.closest('div[role="button"]')
      await user.click(uvCard)

      // Drawer should open
      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument()
      })

      // Click "Use This Pattern" in drawer
      const usePatternButton = screen.getByRole('button', { name: /use this pattern/i })
      await user.click(usePatternButton)

      // Verify callback was called
      expect(onPatternSelect).toHaveBeenCalledTimes(1)
      expect(onPatternSelect).toHaveBeenCalledWith(
        expect.objectContaining({
          pattern_id: 'uv_capture_cycle',
          name: 'UV Capture Cycle',
        })
      )
    })

    it('shows pattern count', async () => {
      render(
        <PatternList onPatternSelect={vi.fn()} />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(screen.getByText(/showing 3 of 3 patterns/i)).toBeInTheDocument()
      })
    })
  })

  describe('Embedded Mode Workflow', () => {
    it('directly selects pattern without opening drawer', async () => {
      const user = userEvent.setup()
      const onPatternSelect = vi.fn()

      render(
        <PatternList
          mode="embedded"
          onPatternSelect={onPatternSelect}
        />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(screen.getByText('UV Capture Cycle')).toBeInTheDocument()
      })

      // Find and click on pattern card
      const uvCardHeading = screen.getByText('UV Capture Cycle')
      const uvCard = uvCardHeading.closest('article') || uvCardHeading.closest('div[role="button"]')
      await user.click(uvCard)

      // In embedded mode, drawer should NOT open
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

      // onPatternSelect should be called directly
      expect(onPatternSelect).toHaveBeenCalledWith(
        expect.objectContaining({
          pattern_id: 'uv_capture_cycle',
        })
      )
    })

    it('hides view toggle in embedded mode', async () => {
      render(
        <PatternList mode="embedded" onPatternSelect={vi.fn()} />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(screen.getByText('UV Capture Cycle')).toBeInTheDocument()
      })

      // View toggle should NOT be visible in embedded mode
      expect(screen.queryByRole('button', { name: /grid view/i })).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /list view/i })).not.toBeInTheDocument()
    })
  })

  describe('Selected Pattern Highlighting', () => {
    it('highlights the selected pattern', async () => {
      render(
        <PatternList selectedPatternId="simple_photo" onPatternSelect={vi.fn()} />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(screen.getByText('Simple Photo')).toBeInTheDocument()
      })

      // The Simple Photo card should have selection styling
      const simplePhotoHeading = screen.getByText('Simple Photo')
      const simplePhotoCard = simplePhotoHeading.closest('article') || simplePhotoHeading.closest('div[role="button"]')

      // Check for selection indicator (ring class)
      expect(simplePhotoCard.className).toMatch(/ring/i)
    })
  })

  describe('Error Recovery', () => {
    it('shows error state and allows retry', async () => {
      const refetchMock = vi.fn()
      useBuiltinPatterns.mockReturnValue({
        data: null,
        isLoading: false,
        isError: true,
        error: new Error('Network error'),
        refetch: refetchMock,
      })

      const user = userEvent.setup()

      render(<PatternList onPatternSelect={vi.fn()} />, { wrapper: createWrapper() })

      // Error message should be visible
      expect(screen.getByText(/failed to load patterns/i)).toBeInTheDocument()

      // Retry button should be visible
      const retryButton = screen.getByRole('button', { name: /retry/i })
      await user.click(retryButton)

      // refetch should be called
      expect(refetchMock).toHaveBeenCalled()
    })
  })

  describe('Loading State', () => {
    it('shows loading skeleton while fetching', () => {
      useBuiltinPatterns.mockReturnValue({
        data: null,
        isLoading: true,
        isError: false,
        error: null,
        refetch: vi.fn(),
      })

      render(<PatternList onPatternSelect={vi.fn()} />, { wrapper: createWrapper() })

      // Should show loading skeleton
      expect(screen.getByTestId('loading-skeleton')).toBeInTheDocument()
    })
  })

  describe('Empty State', () => {
    it('shows empty message when no patterns exist', () => {
      useBuiltinPatterns.mockReturnValue({
        data: { patterns: [], total: 0, warnings: [] },
        isLoading: false,
        isError: false,
        error: null,
        refetch: vi.fn(),
      })

      render(<PatternList onPatternSelect={vi.fn()} />, { wrapper: createWrapper() })

      expect(screen.getByText('No patterns available')).toBeInTheDocument()
    })
  })
})

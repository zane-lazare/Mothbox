/**
 * Tests for ConflictList component (Issue #229)
 *
 * TDD: Tests written first to define expected behavior
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ConflictList from '../ConflictList'

// Test fixtures matching backend Conflict.to_dict() output
const mockErrorConflict1 = {
  conflict_type: 'resource_contention',
  severity: 'error',
  event1_id: 'pattern-1',
  event1_name: 'UV Capture',
  event2_id: 'pattern-2',
  event2_name: 'Flash Photo',
  start_time: '2024-06-15T21:30:00Z',
  end_time: '2024-06-15T21:45:00Z',
  resource: 'camera',
  message: 'Camera resource conflict',
  suggested_resolution: 'Adjust timing',
}

const mockErrorConflict2 = {
  conflict_type: 'gpio_state_conflict',
  severity: 'error',
  event1_id: 'pattern-3',
  event1_name: 'Attract On',
  event2_id: 'pattern-4',
  event2_name: 'Attract Off',
  start_time: '2024-06-15T22:00:00Z',
  end_time: '2024-06-15T22:05:00Z',
  resource: 'attract',
  message: 'GPIO state conflict',
  suggested_resolution: 'Add delay',
}

const mockWarningConflict1 = {
  conflict_type: 'time_overlap',
  severity: 'warning',
  event1_id: 'pattern-5',
  event1_name: 'Morning Survey',
  event2_id: 'pattern-6',
  event2_name: 'Dawn Capture',
  start_time: '2024-06-15T05:00:00Z',
  end_time: '2024-06-15T05:15:00Z',
  resource: '',
  message: 'Patterns overlap',
  suggested_resolution: 'Adjust offsets',
}

const mockWarningConflict2 = {
  conflict_type: 'time_overlap',
  severity: 'warning',
  event1_id: 'pattern-7',
  event1_name: 'Night Survey',
  event2_id: 'pattern-8',
  event2_name: 'Evening Capture',
  start_time: '2024-06-15T20:00:00Z',
  end_time: '2024-06-15T20:30:00Z',
  resource: '',
  message: 'Patterns overlap at evening',
  suggested_resolution: 'Increase interval',
}

// Mixed conflicts for testing grouping
const mixedConflicts = [
  mockWarningConflict1, // warning first to test sorting
  mockErrorConflict1,
  mockWarningConflict2,
  mockErrorConflict2,
]

describe('ConflictList', () => {
  describe('Rendering', () => {
    it('renders nothing when conflicts is empty', () => {
      const { container } = render(<ConflictList conflicts={[]} />)

      expect(container.firstChild).toBeNull()
    })

    it('renders nothing when conflicts is null', () => {
      const { container } = render(<ConflictList conflicts={null} />)

      expect(container.firstChild).toBeNull()
    })

    it('renders nothing when conflicts is undefined', () => {
      const { container } = render(<ConflictList />)

      expect(container.firstChild).toBeNull()
    })

    it('renders list of conflicts', () => {
      render(<ConflictList conflicts={[mockErrorConflict1]} />)

      expect(screen.getByText(/Camera resource conflict/)).toBeInTheDocument()
    })

    it('renders heading with conflict count', () => {
      render(<ConflictList conflicts={mixedConflicts} />)

      // Should show total count
      expect(screen.getByText(/4 conflict/i)).toBeInTheDocument()
    })

    it('renders blocking conflict count when present', () => {
      render(<ConflictList conflicts={mixedConflicts} />)

      // Should indicate blocking conflicts
      expect(screen.getByText(/2 blocking/i)).toBeInTheDocument()
    })
  })

  describe('Grouping', () => {
    it('groups error conflicts before warning conflicts', () => {
      const { container } = render(<ConflictList conflicts={mixedConflicts} />)

      // Get all list items
      const listItems = container.querySelectorAll('li')

      // Should have 4 items
      expect(listItems.length).toBe(4)

      // First two should be errors (red styling)
      expect(listItems[0].className).toMatch(/red/)
      expect(listItems[1].className).toMatch(/red/)

      // Last two should be warnings (amber styling)
      expect(listItems[2].className).toMatch(/amber/)
      expect(listItems[3].className).toMatch(/amber/)
    })

    it('renders error section header when errors exist', () => {
      render(<ConflictList conflicts={mixedConflicts} />)

      expect(screen.getByText(/Blocking Conflicts/i)).toBeInTheDocument()
    })

    it('renders warning section header when warnings exist', () => {
      render(<ConflictList conflicts={mixedConflicts} />)

      expect(screen.getByText(/Warnings/i)).toBeInTheDocument()
    })

    it('does not render warning header when only errors exist', () => {
      render(<ConflictList conflicts={[mockErrorConflict1, mockErrorConflict2]} />)

      expect(screen.queryByText(/Warnings/i)).not.toBeInTheDocument()
    })

    it('does not render error header when only warnings exist', () => {
      render(<ConflictList conflicts={[mockWarningConflict1, mockWarningConflict2]} />)

      expect(screen.queryByText(/Blocking Conflicts/i)).not.toBeInTheDocument()
    })
  })

  describe('ConflictItem Integration', () => {
    it('renders ConflictItem for each conflict', () => {
      render(<ConflictList conflicts={mixedConflicts} />)

      // Check that all conflict messages are rendered
      expect(screen.getByText(/Camera resource conflict/)).toBeInTheDocument()
      expect(screen.getByText(/GPIO state conflict/)).toBeInTheDocument()
      // Use getAllByText for "Patterns overlap" since it's a substring of both warning messages
      const overlapTexts = screen.getAllByText(/Patterns overlap/)
      expect(overlapTexts.length).toBe(2)
    })

    it('renders correct number of list items', () => {
      const { container } = render(<ConflictList conflicts={mixedConflicts} />)

      const listItems = container.querySelectorAll('li')
      expect(listItems.length).toBe(4)
    })
  })

  describe('Accessibility', () => {
    it('has role="list" on container', () => {
      render(<ConflictList conflicts={[mockErrorConflict1]} />)

      expect(screen.getByRole('list')).toBeInTheDocument()
    })

    it('has aria-label describing conflict list', () => {
      render(<ConflictList conflicts={[mockErrorConflict1]} />)

      const list = screen.getByRole('list')
      expect(list).toHaveAttribute('aria-label')
    })
  })

  describe('Compact Mode', () => {
    it('renders all conflicts by default (not compact)', () => {
      const { container } = render(<ConflictList conflicts={mixedConflicts} />)

      const listItems = container.querySelectorAll('li')
      expect(listItems.length).toBe(4)
    })

    it('limits visible conflicts to 3 in compact mode', () => {
      const { container } = render(<ConflictList conflicts={mixedConflicts} compact />)

      // Should only show 3 items
      const listItems = container.querySelectorAll('li')
      expect(listItems.length).toBe(3)
    })

    it('shows "+N more" when more conflicts exist in compact mode', () => {
      render(<ConflictList conflicts={mixedConflicts} compact onViewAll={() => {}} />)

      // 4 conflicts - 3 shown = 1 more
      expect(screen.getByText(/\+1 more/i)).toBeInTheDocument()
    })

    it('does not show "+N more" button when onViewAll is not provided', () => {
      render(<ConflictList conflicts={mixedConflicts} compact />)

      // Even though there are hidden conflicts, button should not render without callback
      expect(screen.queryByText(/\+\d+ more/i)).not.toBeInTheDocument()
    })

    it('does not show "+N more" when all conflicts fit in compact mode', () => {
      render(<ConflictList conflicts={[mockErrorConflict1, mockErrorConflict2]} compact />)

      // Only 2 conflicts, fits in 3
      expect(screen.queryByText(/\+\d+ more/i)).not.toBeInTheDocument()
    })

    it('calls onViewAll when "+N more" is clicked', async () => {
      const user = userEvent.setup()
      const handleViewAll = vi.fn()

      render(
        <ConflictList conflicts={mixedConflicts} compact onViewAll={handleViewAll} />
      )

      const moreButton = screen.getByText(/\+1 more/i)
      await user.click(moreButton)

      expect(handleViewAll).toHaveBeenCalled()
    })

    it('respects custom compactLimit prop', () => {
      const { container } = render(
        <ConflictList conflicts={mixedConflicts} compact compactLimit={2} onViewAll={() => {}} />
      )

      // Should only show 2 items with custom limit
      const listItems = container.querySelectorAll('li')
      expect(listItems.length).toBe(2)

      // 4 conflicts - 2 shown = 2 more
      expect(screen.getByText(/\+2 more/i)).toBeInTheDocument()
    })

    it('shows all conflicts when compactLimit exceeds conflict count', () => {
      const { container } = render(
        <ConflictList conflicts={mixedConflicts} compact compactLimit={10} />
      )

      // Should show all 4 items since limit is higher
      const listItems = container.querySelectorAll('li')
      expect(listItems.length).toBe(4)

      // No "+N more" since all are shown
      expect(screen.queryByText(/\+\d+ more/i)).not.toBeInTheDocument()
    })
  })

  describe('Dark Mode', () => {
    it('has dark mode classes on container', () => {
      const { container } = render(<ConflictList conflicts={[mockErrorConflict1]} />)

      // Container should have dark mode support
      const wrapper = container.firstChild
      expect(wrapper.className).toMatch(/dark:/)
    })
  })
})

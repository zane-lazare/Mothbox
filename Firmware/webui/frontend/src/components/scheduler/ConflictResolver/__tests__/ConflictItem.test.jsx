/**
 * Tests for ConflictItem component (Issue #229)
 *
 * TDD: Tests written first to define expected behavior
 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ConflictItem from '../ConflictItem'

// Test fixtures matching backend Conflict.to_dict() output
const mockErrorConflict = {
  conflict_type: 'resource_contention',
  severity: 'error',
  event1_id: 'pattern-1',
  event1_name: 'UV Capture',
  event2_id: 'pattern-2',
  event2_name: 'Flash Photo',
  start_time: '2024-06-15T21:30:00Z',
  end_time: '2024-06-15T21:45:00Z',
  resource: 'camera',
  message: 'Camera resource conflict: both patterns use takephoto at the same time',
  suggested_resolution: 'Adjust action timing so camera is not used simultaneously',
}

const mockWarningConflict = {
  conflict_type: 'time_overlap',
  severity: 'warning',
  event1_id: 'pattern-1',
  event1_name: 'Morning Survey',
  event2_id: 'pattern-2',
  event2_name: 'Dawn Capture',
  start_time: '2024-06-15T05:00:00Z',
  end_time: '2024-06-15T05:15:00Z',
  resource: '',
  message: "Patterns 'Morning Survey' and 'Dawn Capture' overlap from 05:00:00 to 05:15:00",
  suggested_resolution: 'Adjust pattern offsets or increase interval between triggers',
}

const mockGpioConflict = {
  conflict_type: 'gpio_state_conflict',
  severity: 'error',
  event1_id: 'pattern-1',
  event1_name: 'Attract On',
  event2_id: 'pattern-2',
  event2_name: 'Attract Off',
  start_time: '2024-06-15T22:00:00Z',
  end_time: '2024-06-15T22:05:00Z',
  resource: 'attract',
  message: 'GPIO state conflict: attract_on and attract_off cannot be active simultaneously',
  suggested_resolution: 'Ensure attract state changes don\'t overlap: add delay between attract_on and attract_off',
}

describe('ConflictItem', () => {
  describe('Rendering', () => {
    it('renders conflict message', () => {
      render(<ConflictItem conflict={mockErrorConflict} />)

      expect(screen.getByText(/Camera resource conflict/)).toBeInTheDocument()
    })

    it('renders event names', () => {
      render(<ConflictItem conflict={mockErrorConflict} />)

      expect(screen.getByText(/UV Capture/)).toBeInTheDocument()
      expect(screen.getByText(/Flash Photo/)).toBeInTheDocument()
    })

    it('renders suggested resolution', () => {
      render(<ConflictItem conflict={mockErrorConflict} />)

      expect(screen.getByText(/Adjust action timing/)).toBeInTheDocument()
    })

    it('renders time range', () => {
      const { container } = render(<ConflictItem conflict={mockErrorConflict} />)

      // Should display formatted time (may vary by locale/timezone)
      // Check that a time range element exists with the expected format
      const timeRange = container.querySelector('.text-xs.opacity-75.mb-2')
      expect(timeRange).toBeInTheDocument()
      expect(timeRange.textContent).toMatch(/\d{2}:\d{2}/)
      expect(timeRange.textContent).toMatch(/–/)
    })

    it('renders resource name when provided', () => {
      const { container } = render(<ConflictItem conflict={mockErrorConflict} />)

      // Resource is shown in parentheses
      const resourceSpan = container.querySelector('.text-xs.opacity-75')
      expect(resourceSpan).toBeInTheDocument()
      expect(resourceSpan.textContent).toContain('camera')
    })

    it('handles missing resource gracefully', () => {
      const { container } = render(<ConflictItem conflict={mockWarningConflict} />)

      // Should not crash, should still render the message
      const message = container.querySelector('p.text-sm')
      expect(message).toBeInTheDocument()
      expect(message.textContent).toMatch(/overlap/i)
    })
  })

  describe('Severity Styling', () => {
    it('renders error styling for severity="error"', () => {
      const { container } = render(<ConflictItem conflict={mockErrorConflict} />)

      // Check for red-related classes
      const item = container.firstChild
      expect(item.className).toMatch(/red/)
    })

    it('renders warning styling for severity="warning"', () => {
      const { container } = render(<ConflictItem conflict={mockWarningConflict} />)

      // Check for amber-related classes
      const item = container.firstChild
      expect(item.className).toMatch(/amber/)
    })

    it('shows appropriate icon for error severity', () => {
      const { container } = render(<ConflictItem conflict={mockErrorConflict} />)

      // Should have an SVG icon
      const icon = container.querySelector('svg')
      expect(icon).toBeInTheDocument()
    })

    it('shows appropriate icon for warning severity', () => {
      const { container } = render(<ConflictItem conflict={mockWarningConflict} />)

      // Should have an SVG icon
      const icon = container.querySelector('svg')
      expect(icon).toBeInTheDocument()
    })
  })

  describe('Conflict Types', () => {
    it('renders label for time_overlap', () => {
      render(<ConflictItem conflict={mockWarningConflict} />)

      // Use getAllByText since label appears in badge
      expect(screen.getAllByText(/Time Overlap/i).length).toBeGreaterThan(0)
    })

    it('renders label for resource_contention', () => {
      render(<ConflictItem conflict={mockErrorConflict} />)

      // Use getAllByText since label appears in badge
      expect(screen.getAllByText(/Resource Conflict/i).length).toBeGreaterThan(0)
    })

    it('renders label for gpio_state_conflict', () => {
      render(<ConflictItem conflict={mockGpioConflict} />)

      // Use getAllByText since label appears in badge
      expect(screen.getAllByText(/GPIO State Conflict/i).length).toBeGreaterThan(0)
    })
  })

  describe('Accessibility', () => {
    it('has appropriate role="listitem"', () => {
      render(<ConflictItem conflict={mockErrorConflict} />)

      expect(screen.getByRole('listitem')).toBeInTheDocument()
    })

    it('has aria-label describing the conflict', () => {
      render(<ConflictItem conflict={mockErrorConflict} />)

      const item = screen.getByRole('listitem')
      expect(item).toHaveAttribute('aria-label')
    })
  })

  describe('Dark Mode', () => {
    it('has dark mode classes for error variant', () => {
      const { container } = render(<ConflictItem conflict={mockErrorConflict} />)

      const item = container.firstChild
      expect(item.className).toMatch(/dark:/)
    })

    it('has dark mode classes for warning variant', () => {
      const { container } = render(<ConflictItem conflict={mockWarningConflict} />)

      const item = container.firstChild
      expect(item.className).toMatch(/dark:/)
    })
  })
})

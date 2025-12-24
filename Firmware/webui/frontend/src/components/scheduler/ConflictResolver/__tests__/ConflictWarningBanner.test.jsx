/**
 * Tests for ConflictWarningBanner component (Issue #229)
 *
 * TDD: Tests written first to define expected behavior
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ConflictWarningBanner from '../ConflictWarningBanner'

// Test fixtures
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
  message: 'Camera resource conflict',
  suggested_resolution: 'Adjust timing',
}

const mockWarningConflict = {
  conflict_type: 'time_overlap',
  severity: 'warning',
  event1_id: 'pattern-3',
  event1_name: 'Morning Survey',
  event2_id: 'pattern-4',
  event2_name: 'Dawn Capture',
  start_time: '2024-06-15T05:00:00Z',
  end_time: '2024-06-15T05:15:00Z',
  resource: '',
  message: 'Patterns overlap',
  suggested_resolution: 'Adjust offsets',
}

const blockingConflicts = [mockErrorConflict]
const warningConflicts = [mockWarningConflict]
const mixedConflicts = [mockErrorConflict, mockWarningConflict]

describe('ConflictWarningBanner', () => {
  describe('Visibility', () => {
    it('renders nothing when conflicts is empty', () => {
      const { container } = render(<ConflictWarningBanner conflicts={[]} />)

      expect(container.firstChild).toBeNull()
    })

    it('renders nothing when conflicts is null', () => {
      const { container } = render(<ConflictWarningBanner conflicts={null} />)

      expect(container.firstChild).toBeNull()
    })

    it('renders nothing when conflicts is undefined', () => {
      const { container } = render(<ConflictWarningBanner />)

      expect(container.firstChild).toBeNull()
    })

    it('renders banner when conflicts exist', () => {
      render(<ConflictWarningBanner conflicts={blockingConflicts} />)

      // Should render some content
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })

  describe('Severity Variants', () => {
    it('renders error banner when hasBlockingConflicts is true', () => {
      const { container } = render(
        <ConflictWarningBanner conflicts={blockingConflicts} hasBlockingConflicts />
      )

      // Check for red styling
      const banner = container.firstChild
      expect(banner.className).toMatch(/red/)
    })

    it('renders warning banner when only warnings exist', () => {
      const { container } = render(
        <ConflictWarningBanner conflicts={warningConflicts} />
      )

      // Check for amber styling
      const banner = container.firstChild
      expect(banner.className).toMatch(/amber/)
    })

    it('uses error icon for blocking conflicts', () => {
      const { container } = render(
        <ConflictWarningBanner conflicts={blockingConflicts} hasBlockingConflicts />
      )

      // Should have an SVG icon
      const icon = container.querySelector('svg')
      expect(icon).toBeInTheDocument()
    })

    it('uses warning icon for warnings only', () => {
      const { container } = render(
        <ConflictWarningBanner conflicts={warningConflicts} />
      )

      // Should have an SVG icon
      const icon = container.querySelector('svg')
      expect(icon).toBeInTheDocument()
    })
  })

  describe('Content', () => {
    it('displays blocking conflict count', () => {
      render(
        <ConflictWarningBanner
          conflicts={mixedConflicts}
          hasBlockingConflicts
          blockingCount={1}
          warningCount={1}
        />
      )

      expect(screen.getByText(/1 blocking/i)).toBeInTheDocument()
    })

    it('displays warning count', () => {
      render(
        <ConflictWarningBanner
          conflicts={mixedConflicts}
          hasBlockingConflicts
          blockingCount={1}
          warningCount={1}
        />
      )

      expect(screen.getByText(/1 warning/i)).toBeInTheDocument()
    })

    it('displays total conflict count', () => {
      render(
        <ConflictWarningBanner
          conflicts={mixedConflicts}
          hasBlockingConflicts
          blockingCount={1}
          warningCount={1}
        />
      )

      expect(screen.getByText(/2 conflict/i)).toBeInTheDocument()
    })

    it('displays appropriate message for blocking conflicts', () => {
      render(
        <ConflictWarningBanner
          conflicts={blockingConflicts}
          hasBlockingConflicts
          blockingCount={1}
        />
      )

      expect(screen.getByText(/cannot activate/i)).toBeInTheDocument()
    })

    it('displays appropriate message for warnings only', () => {
      render(
        <ConflictWarningBanner conflicts={warningConflicts} warningCount={1} />
      )

      expect(screen.getByText(/potential/i)).toBeInTheDocument()
    })
  })

  describe('Actions', () => {
    it('renders "View Details" button', () => {
      render(<ConflictWarningBanner conflicts={blockingConflicts} />)

      expect(screen.getByRole('button', { name: /view details/i })).toBeInTheDocument()
    })

    it('calls onViewDetails when button clicked', async () => {
      const user = userEvent.setup()
      const handleViewDetails = vi.fn()

      render(
        <ConflictWarningBanner
          conflicts={blockingConflicts}
          onViewDetails={handleViewDetails}
        />
      )

      await user.click(screen.getByRole('button', { name: /view details/i }))
      expect(handleViewDetails).toHaveBeenCalled()
    })

    it('renders "Dismiss" button for warnings only', () => {
      render(
        <ConflictWarningBanner
          conflicts={warningConflicts}
          onDismiss={() => {}}
        />
      )

      expect(screen.getByRole('button', { name: /dismiss/i })).toBeInTheDocument()
    })

    it('calls onDismiss when dismiss button clicked', async () => {
      const user = userEvent.setup()
      const handleDismiss = vi.fn()

      render(
        <ConflictWarningBanner
          conflicts={warningConflicts}
          onDismiss={handleDismiss}
        />
      )

      await user.click(screen.getByRole('button', { name: /dismiss/i }))
      expect(handleDismiss).toHaveBeenCalled()
    })

    it('does not render dismiss for blocking conflicts', () => {
      render(
        <ConflictWarningBanner
          conflicts={blockingConflicts}
          hasBlockingConflicts
          onDismiss={() => {}}
        />
      )

      expect(screen.queryByRole('button', { name: /dismiss/i })).not.toBeInTheDocument()
    })
  })

  describe('Expanded State', () => {
    it('toggles ConflictList visibility on "View Details" click', async () => {
      const user = userEvent.setup()

      render(<ConflictWarningBanner conflicts={blockingConflicts} />)

      // Initially, detailed conflict list should not be visible
      expect(screen.queryByRole('list')).not.toBeInTheDocument()

      // Click View Details
      await user.click(screen.getByRole('button', { name: /view details/i }))

      // Now conflict list should be visible
      expect(screen.getByRole('list')).toBeInTheDocument()

      // Click again to hide
      await user.click(screen.getByRole('button', { name: /hide details/i }))

      // List should be hidden again
      expect(screen.queryByRole('list')).not.toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has role="alert" for blocking conflicts', () => {
      render(
        <ConflictWarningBanner conflicts={blockingConflicts} hasBlockingConflicts />
      )

      expect(screen.getByRole('alert')).toBeInTheDocument()
    })

    it('has role="status" for warnings only', () => {
      render(<ConflictWarningBanner conflicts={warningConflicts} />)

      expect(screen.getByRole('status')).toBeInTheDocument()
    })

    it('has aria-live="assertive" for blocking conflicts', () => {
      render(
        <ConflictWarningBanner conflicts={blockingConflicts} hasBlockingConflicts />
      )

      const banner = screen.getByRole('alert')
      expect(banner).toHaveAttribute('aria-live', 'assertive')
    })

    it('has aria-live="polite" for warnings', () => {
      render(<ConflictWarningBanner conflicts={warningConflicts} />)

      const banner = screen.getByRole('status')
      expect(banner).toHaveAttribute('aria-live', 'polite')
    })
  })

  describe('Dark Mode', () => {
    it('has dark mode classes for error variant', () => {
      const { container } = render(
        <ConflictWarningBanner conflicts={blockingConflicts} hasBlockingConflicts />
      )

      const banner = container.firstChild
      expect(banner.className).toMatch(/dark:/)
    })

    it('has dark mode classes for warning variant', () => {
      const { container } = render(
        <ConflictWarningBanner conflicts={warningConflicts} />
      )

      const banner = container.firstChild
      expect(banner.className).toMatch(/dark:/)
    })
  })
})

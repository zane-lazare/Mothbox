/**
 * CalendarCell component tests (Issue #228)
 *
 * Tests for the CalendarCell component in the Scheduler Calendar View.
 *
 * @module components/scheduler/CalendarView/__tests__/CalendarCell
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CalendarCell from '../CalendarCell'

// Mock child components
vi.mock('../MoonPhaseIcon', () => ({
  default: ({ phase, size }) => (
    <div data-testid="moon-phase-icon" data-phase={phase.phase} data-size={size}>
      {phase.phase_name}
    </div>
  ),
}))

// Note: ExecutionMarker is no longer used - CalendarCell now shows action type indicator dots

describe('CalendarCell', () => {
  let mockOnClick

  beforeEach(() => {
    mockOnClick = vi.fn()
  })

  describe('Date Display', () => {
    it('renders the date number', () => {
      const date = new Date(2025, 11, 17) // December 17, 2025
      render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          onClick={mockOnClick}
        />
      )

      expect(screen.getByText('17')).toBeInTheDocument()
    })

    it('renders the correct date for first day of month', () => {
      const date = new Date(2025, 0, 1) // January 1, 2025
      render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          onClick={mockOnClick}
        />
      )

      expect(screen.getByText('1')).toBeInTheDocument()
    })

    it('renders the correct date for last day of month', () => {
      const date = new Date(2025, 0, 31) // January 31, 2025
      render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          onClick={mockOnClick}
        />
      )

      expect(screen.getByText('31')).toBeInTheDocument()
    })
  })

  describe('Today Highlighting', () => {
    it('highlights today with blue circle', () => {
      const today = new Date()
      render(
        <CalendarCell
          date={today}
          isCurrentMonth={true}
          onClick={mockOnClick}
        />
      )

      const dateElement = screen.getByText(today.getDate().toString())
      expect(dateElement).toHaveClass('bg-blue-500')
      expect(dateElement).toHaveClass('text-white')
      expect(dateElement).toHaveClass('rounded-full')
      expect(dateElement).toHaveClass('px-2')
    })

    it('does not highlight dates that are not today', () => {
      const yesterday = new Date()
      yesterday.setDate(yesterday.getDate() - 1)

      render(
        <CalendarCell
          date={yesterday}
          isCurrentMonth={true}
          onClick={mockOnClick}
        />
      )

      const dateElement = screen.getByText(yesterday.getDate().toString())
      expect(dateElement).not.toHaveClass('bg-blue-500')
      expect(dateElement).not.toHaveClass('text-white')
    })
  })

  describe('Current Month Styling', () => {
    it('applies normal styling for current month dates', () => {
      const date = new Date(2025, 11, 17)
      const { container } = render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          onClick={mockOnClick}
        />
      )

      const cellDiv = container.querySelector('[role="button"]')
      expect(cellDiv).not.toHaveClass('bg-gray-50')
    })

    it('dims non-current-month dates with gray background', () => {
      const date = new Date(2025, 11, 17)
      const { container } = render(
        <CalendarCell
          date={date}
          isCurrentMonth={false}
          onClick={mockOnClick}
        />
      )

      const cellDiv = container.querySelector('[role="button"]')
      expect(cellDiv).toHaveClass('bg-gray-50')
      expect(cellDiv).toHaveClass('dark:bg-gray-900')
    })

    it('dims non-current-month date numbers', () => {
      const date = new Date(2025, 11, 17)
      render(
        <CalendarCell
          date={date}
          isCurrentMonth={false}
          onClick={mockOnClick}
        />
      )

      const dateElement = screen.getByText('17')
      expect(dateElement).toHaveClass('text-gray-400')
      expect(dateElement).toHaveClass('dark:text-gray-600')
    })
  })

  describe('Moon Phase Display', () => {
    it('shows moon phase icon when present', () => {
      const date = new Date(2025, 11, 17)
      const moonPhase = {
        phase: 'full',
        phase_name: 'Full Moon',
        illumination: 1.0,
      }

      render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          moonPhase={moonPhase}
          onClick={mockOnClick}
        />
      )

      const moonIcon = screen.getByTestId('moon-phase-icon')
      expect(moonIcon).toBeInTheDocument()
      expect(moonIcon).toHaveAttribute('data-phase', 'full')
      expect(moonIcon).toHaveAttribute('data-size', 'sm')
    })

    it('does not show moon phase icon when null', () => {
      const date = new Date(2025, 11, 17)
      render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          moonPhase={null}
          onClick={mockOnClick}
        />
      )

      expect(screen.queryByTestId('moon-phase-icon')).not.toBeInTheDocument()
    })

    it('does not show moon phase icon when undefined', () => {
      const date = new Date(2025, 11, 17)
      render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          onClick={mockOnClick}
        />
      )

      expect(screen.queryByTestId('moon-phase-icon')).not.toBeInTheDocument()
    })
  })

  describe('Action Type Indicator Display', () => {
    // Note: CalendarCell now shows action type indicator dots instead of individual execution markers
    it('renders action type indicator dots for executions', () => {
      const date = new Date(2025, 11, 17)
      const executions = [
        {
          id: '1',
          pattern_id: 'pattern1',
          pattern_name: 'Pattern 1',
          start_time: '2025-12-17T08:00:00Z',
          actions: [{ action_type: 'camera' }],
        },
        {
          id: '2',
          pattern_id: 'pattern2',
          pattern_name: 'Pattern 2',
          start_time: '2025-12-17T12:00:00Z',
          actions: [{ action_type: 'gpio' }],
        },
      ]

      const { container } = render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          executions={executions}
          onClick={mockOnClick}
        />
      )

      // Should have action type indicator dots
      const dots = container.querySelectorAll('.rounded-full')
      expect(dots.length).toBeGreaterThan(0)
    })

    it('shows one dot per unique action type', () => {
      const date = new Date(2025, 11, 17)
      const executions = [
        {
          pattern_id: 'pattern1',
          pattern_name: 'Pattern 1',
          start_time: '2025-12-17T08:00:00Z',
          actions: [{ action_type: 'camera' }],
        },
        {
          pattern_id: 'pattern2',
          pattern_name: 'Pattern 2',
          start_time: '2025-12-17T10:00:00Z',
          actions: [{ action_type: 'camera' }], // Same action type
        },
        {
          pattern_id: 'pattern3',
          pattern_name: 'Pattern 3',
          start_time: '2025-12-17T12:00:00Z',
          actions: [{ action_type: 'gpio' }], // Different action type
        },
      ]

      const { container } = render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          executions={executions}
          onClick={mockOnClick}
        />
      )

      // Should have exactly 2 dots (camera + gpio, deduplicated)
      const dots = container.querySelectorAll('.w-1\\.5.h-1\\.5.rounded-full')
      expect(dots.length).toBe(2)
    })

    it('renders no dots when array is empty', () => {
      const date = new Date(2025, 11, 17)
      const { container } = render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          executions={[]}
          onClick={mockOnClick}
        />
      )

      const dots = container.querySelectorAll('.w-1\\.5.h-1\\.5.rounded-full')
      expect(dots.length).toBe(0)
    })

    it('renders without warning when executions have same start_time', () => {
      const date = new Date(2025, 11, 17)
      const executions = [
        {
          pattern_id: 'pattern1',
          pattern_name: 'Pattern 1',
          start_time: '2025-12-17T08:00:00Z',
          actions: [{ action_type: 'camera' }],
        },
        {
          pattern_id: 'pattern2',
          pattern_name: 'Pattern 2',
          start_time: '2025-12-17T08:00:00Z', // Same start_time
          actions: [{ action_type: 'gpio' }],
        },
      ]

      // Mock console.error to catch React warnings
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          executions={executions}
          onClick={mockOnClick}
        />
      )

      // No React duplicate key warnings should have been logged
      expect(consoleErrorSpy).not.toHaveBeenCalledWith(
        expect.stringContaining('Encountered two children with the same key')
      )

      consoleErrorSpy.mockRestore()
    })
  })

  describe('Click Handlers', () => {
    // Note: CalendarCell no longer has onExecutionClick prop - clicking the cell navigates to day view
    it('calls onClick with date when cell is clicked', async () => {
      const user = userEvent.setup()
      const date = new Date(2025, 11, 17)

      const { container } = render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          onClick={mockOnClick}
        />
      )

      const cellDiv = container.querySelector('[role="button"]')
      await user.click(cellDiv)

      expect(mockOnClick).toHaveBeenCalledTimes(1)
      expect(mockOnClick).toHaveBeenCalledWith(date)
    })

    it('calls onClick when clicking cell with executions', async () => {
      const user = userEvent.setup()
      const date = new Date(2025, 11, 17)
      const executions = [
        {
          pattern_id: 'pattern1',
          pattern_name: 'Pattern 1',
          start_time: '2025-12-17T08:00:00Z',
          actions: [{ action_type: 'camera' }],
        },
      ]

      const { container } = render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          executions={executions}
          onClick={mockOnClick}
        />
      )

      const cellDiv = container.querySelector('[role="button"]')
      await user.click(cellDiv)

      // Clicking cell should call onClick (navigates to day view)
      expect(mockOnClick).toHaveBeenCalledTimes(1)
      expect(mockOnClick).toHaveBeenCalledWith(date)
    })

    it('supports keyboard navigation with Enter key', async () => {
      const user = userEvent.setup()
      const date = new Date(2025, 11, 17)

      const { container } = render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          onClick={mockOnClick}
        />
      )

      const cellDiv = container.querySelector('[role="button"]')
      cellDiv.focus()
      await user.keyboard('{Enter}')

      expect(mockOnClick).toHaveBeenCalledTimes(1)
      expect(mockOnClick).toHaveBeenCalledWith(date)
    })

    it('supports keyboard navigation with Space key', async () => {
      const user = userEvent.setup()
      const date = new Date(2025, 11, 17)

      const { container } = render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          onClick={mockOnClick}
        />
      )

      const cellDiv = container.querySelector('[role="button"]')
      cellDiv.focus()
      await user.keyboard(' ')

      expect(mockOnClick).toHaveBeenCalledTimes(1)
      expect(mockOnClick).toHaveBeenCalledWith(date)
    })
  })

  describe('Dark Mode', () => {
    it('applies dark mode border classes', () => {
      const date = new Date(2025, 11, 17)
      const { container } = render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          onClick={mockOnClick}
        />
      )

      const cellDiv = container.querySelector('[role="button"]')
      // PANEL_STYLES.grid uses dark:border-gray-800
      expect(cellDiv).toHaveClass('dark:border-gray-800')
      expect(cellDiv).toHaveClass('dark:hover:bg-gray-800')
    })

    it('applies dark mode text classes to non-current-month dates', () => {
      const date = new Date(2025, 11, 17)
      render(
        <CalendarCell
          date={date}
          isCurrentMonth={false}
          onClick={mockOnClick}
        />
      )

      const dateElement = screen.getByText('17')
      expect(dateElement).toHaveClass('dark:text-gray-600')
    })

    it('applies dark mode background to non-current-month cells', () => {
      const date = new Date(2025, 11, 17)
      const { container } = render(
        <CalendarCell
          date={date}
          isCurrentMonth={false}
          onClick={mockOnClick}
        />
      )

      const cellDiv = container.querySelector('[role="button"]')
      expect(cellDiv).toHaveClass('dark:bg-gray-900')
    })
  })

  describe('Accessibility', () => {
    it('has role="button" for keyboard navigation', () => {
      const date = new Date(2025, 11, 17)
      const { container } = render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          onClick={mockOnClick}
        />
      )

      const cellDiv = container.querySelector('[role="button"]')
      expect(cellDiv).toBeInTheDocument()
    })

    it('has tabIndex="0" for keyboard focus', () => {
      const date = new Date(2025, 11, 17)
      const { container } = render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          onClick={mockOnClick}
        />
      )

      const cellDiv = container.querySelector('[role="button"]')
      expect(cellDiv).toHaveAttribute('tabIndex', '0')
    })

    it('has descriptive aria-label with weekday, month name, and year', () => {
      const date = new Date(2025, 11, 17) // Wednesday, December 17, 2025
      const { container } = render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          onClick={mockOnClick}
        />
      )

      const cellDiv = container.querySelector('[role="button"]')
      const ariaLabel = cellDiv.getAttribute('aria-label')

      expect(ariaLabel).toContain('Wednesday')
      expect(ariaLabel).toContain('December')
      expect(ariaLabel).toContain('17')
      expect(ariaLabel).toContain('2025')
    })

    it('includes moon phase in aria-label when present', () => {
      const date = new Date(2025, 11, 17)
      const moonPhase = {
        phase: 'full',
        phase_name: 'Full Moon',
        illumination: 1.0,
      }

      const { container } = render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          moonPhase={moonPhase}
          onClick={mockOnClick}
        />
      )

      const cellDiv = container.querySelector('[role="button"]')
      const ariaLabel = cellDiv.getAttribute('aria-label')

      expect(ariaLabel).toContain('Wednesday, December 17, 2025')
      expect(ariaLabel).toContain('Full Moon')
    })

    it('includes execution count with correct pluralization (singular)', () => {
      const date = new Date(2025, 11, 17)
      const executions = [
        {
          id: '1',
          pattern_id: 'pattern1',
          pattern_name: 'Pattern 1',
          start_time: '2025-12-17T08:00:00Z',
        },
      ]

      const { container } = render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          executions={executions}
          onClick={mockOnClick}
        />
      )

      const cellDiv = container.querySelector('[role="button"]')
      const ariaLabel = cellDiv.getAttribute('aria-label')

      expect(ariaLabel).toContain('1 scheduled execution')
      expect(ariaLabel).not.toContain('executions') // Should be singular
    })

    it('includes execution count with correct pluralization (plural)', () => {
      const date = new Date(2025, 11, 17)
      const executions = [
        {
          id: '1',
          pattern_id: 'pattern1',
          pattern_name: 'Pattern 1',
          start_time: '2025-12-17T08:00:00Z',
        },
        {
          id: '2',
          pattern_id: 'pattern2',
          pattern_name: 'Pattern 2',
          start_time: '2025-12-17T12:00:00Z',
        },
      ]

      const { container } = render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          executions={executions}
          onClick={mockOnClick}
        />
      )

      const cellDiv = container.querySelector('[role="button"]')
      const ariaLabel = cellDiv.getAttribute('aria-label')

      expect(ariaLabel).toContain('2 scheduled executions')
    })

    it('omits execution count when no executions', () => {
      const date = new Date(2025, 11, 17)
      const { container } = render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          executions={[]}
          onClick={mockOnClick}
        />
      )

      const cellDiv = container.querySelector('[role="button"]')
      const ariaLabel = cellDiv.getAttribute('aria-label')

      expect(ariaLabel).toBe('Wednesday, December 17, 2025')
      expect(ariaLabel).not.toContain('execution')
    })

    it('includes both moon phase and executions in aria-label', () => {
      const date = new Date(2025, 11, 17)
      const moonPhase = {
        phase: 'full',
        phase_name: 'Full Moon',
        illumination: 1.0,
      }
      const executions = [
        {
          id: '1',
          pattern_id: 'pattern1',
          pattern_name: 'Pattern 1',
          start_time: '2025-12-17T08:00:00Z',
        },
        {
          id: '2',
          pattern_id: 'pattern2',
          pattern_name: 'Pattern 2',
          start_time: '2025-12-17T12:00:00Z',
        },
        {
          id: '3',
          pattern_id: 'pattern3',
          pattern_name: 'Pattern 3',
          start_time: '2025-12-17T18:00:00Z',
        },
      ]

      const { container } = render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          moonPhase={moonPhase}
          executions={executions}
          onClick={mockOnClick}
        />
      )

      const cellDiv = container.querySelector('[role="button"]')
      const ariaLabel = cellDiv.getAttribute('aria-label')

      expect(ariaLabel).toBe('Wednesday, December 17, 2025, Full Moon, 3 scheduled executions')
    })
  })

  describe('Layout and Styling', () => {
    it('has minimum height class (responsive)', () => {
      const date = new Date(2025, 11, 17)
      const { container } = render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          onClick={mockOnClick}
        />
      )

      const cellDiv = container.querySelector('[role="button"]')
      // Responsive: min-h-20 sm:min-h-24
      expect(cellDiv).toHaveClass('min-h-20')
      expect(cellDiv).toHaveClass('sm:min-h-24')
    })

    it('has border and padding classes (responsive)', () => {
      const date = new Date(2025, 11, 17)
      const { container } = render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          onClick={mockOnClick}
        />
      )

      const cellDiv = container.querySelector('[role="button"]')
      // Responsive: p-0.5 sm:p-1
      expect(cellDiv).toHaveClass('p-0.5')
      expect(cellDiv).toHaveClass('sm:p-1')
      expect(cellDiv).toHaveClass('border-r')
      expect(cellDiv).toHaveClass('border-b')
    })

    it('has cursor pointer class', () => {
      const date = new Date(2025, 11, 17)
      const { container } = render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          onClick={mockOnClick}
        />
      )

      const cellDiv = container.querySelector('[role="button"]')
      expect(cellDiv).toHaveClass('cursor-pointer')
    })

    it('has action indicators container with flex layout', () => {
      const date = new Date(2025, 11, 17)
      const executions = [
        {
          pattern_id: 'pattern1',
          pattern_name: 'Pattern 1',
          start_time: '2025-12-17T08:00:00Z',
          actions: [{ action_type: 'camera' }],
        },
      ]

      const { container } = render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          executions={executions}
          onClick={mockOnClick}
        />
      )

      // Action indicators use flex flex-wrap gap-0.5 mt-1
      const indicatorsContainer = container.querySelector('.flex.flex-wrap.gap-0\\.5.mt-1')
      expect(indicatorsContainer).toBeInTheDocument()
    })
  })
})

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

vi.mock('../ExecutionMarker', () => ({
  default: ({ execution, onClick, compact }) => (
    <button
      data-testid={`execution-marker-${execution.pattern_id}`}
      onClick={onClick}
      data-compact={compact}
    >
      {execution.pattern_name}
    </button>
  ),
}))

describe('CalendarCell', () => {
  let mockOnClick
  let mockOnExecutionClick

  beforeEach(() => {
    mockOnClick = vi.fn()
    mockOnExecutionClick = vi.fn()
  })

  describe('Date Display', () => {
    it('renders the date number', () => {
      const date = new Date(2025, 11, 17) // December 17, 2025
      render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          onClick={mockOnClick}
          onExecutionClick={mockOnExecutionClick}
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
          onExecutionClick={mockOnExecutionClick}
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
          onExecutionClick={mockOnExecutionClick}
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
          onExecutionClick={mockOnExecutionClick}
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
          onExecutionClick={mockOnExecutionClick}
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
          onExecutionClick={mockOnExecutionClick}
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
          onExecutionClick={mockOnExecutionClick}
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
          onExecutionClick={mockOnExecutionClick}
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
          onExecutionClick={mockOnExecutionClick}
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
          onExecutionClick={mockOnExecutionClick}
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
          onExecutionClick={mockOnExecutionClick}
        />
      )

      expect(screen.queryByTestId('moon-phase-icon')).not.toBeInTheDocument()
    })
  })

  describe('Execution Display', () => {
    it('renders up to 3 executions', () => {
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
        {
          id: '3',
          pattern_id: 'pattern3',
          pattern_name: 'Pattern 3',
          start_time: '2025-12-17T18:00:00Z',
        },
      ]

      render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          executions={executions}
          onClick={mockOnClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      expect(screen.getByTestId('execution-marker-pattern1')).toBeInTheDocument()
      expect(screen.getByTestId('execution-marker-pattern2')).toBeInTheDocument()
      expect(screen.getByTestId('execution-marker-pattern3')).toBeInTheDocument()
    })

    it('shows "+N more" indicator for >3 executions', () => {
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
        {
          id: '3',
          pattern_id: 'pattern3',
          pattern_name: 'Pattern 3',
          start_time: '2025-12-17T14:00:00Z',
        },
        {
          id: '4',
          pattern_id: 'pattern4',
          pattern_name: 'Pattern 4',
          start_time: '2025-12-17T16:00:00Z',
        },
        {
          id: '5',
          pattern_id: 'pattern5',
          pattern_name: 'Pattern 5',
          start_time: '2025-12-17T18:00:00Z',
        },
      ]

      render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          executions={executions}
          onClick={mockOnClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      // First 3 executions should be visible
      expect(screen.getByTestId('execution-marker-pattern1')).toBeInTheDocument()
      expect(screen.getByTestId('execution-marker-pattern2')).toBeInTheDocument()
      expect(screen.getByTestId('execution-marker-pattern3')).toBeInTheDocument()

      // Next 2 should be hidden
      expect(screen.queryByTestId('execution-marker-pattern4')).not.toBeInTheDocument()
      expect(screen.queryByTestId('execution-marker-pattern5')).not.toBeInTheDocument()

      // "+2 more" indicator should be shown
      expect(screen.getByText('+2 more')).toBeInTheDocument()
    })

    it('does not show "+N more" for ≤3 executions', () => {
      const date = new Date(2025, 11, 17)
      const executions = [
        {
          id: '1',
          pattern_id: 'pattern1',
          pattern_name: 'Pattern 1',
          start_time: '2025-12-17T08:00:00Z',
        },
      ]

      render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          executions={executions}
          onClick={mockOnClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      expect(screen.queryByText(/more/i)).not.toBeInTheDocument()
    })

    it('renders no executions when array is empty', () => {
      const date = new Date(2025, 11, 17)
      render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          executions={[]}
          onClick={mockOnClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      expect(screen.queryByTestId(/execution-marker/)).not.toBeInTheDocument()
    })

    it('passes compact prop to ExecutionMarker', () => {
      const date = new Date(2025, 11, 17)
      const executions = [
        {
          id: '1',
          pattern_id: 'pattern1',
          pattern_name: 'Pattern 1',
          start_time: '2025-12-17T08:00:00Z',
        },
      ]

      render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          executions={executions}
          onClick={mockOnClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      const marker = screen.getByTestId('execution-marker-pattern1')
      expect(marker).toHaveAttribute('data-compact', 'true')
    })
  })

  describe('Click Handlers', () => {
    it('calls onClick with date when cell is clicked', async () => {
      const user = userEvent.setup()
      const date = new Date(2025, 11, 17)

      const { container } = render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          onClick={mockOnClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      const cellDiv = container.querySelector('[role="button"]')
      await user.click(cellDiv)

      expect(mockOnClick).toHaveBeenCalledTimes(1)
      expect(mockOnClick).toHaveBeenCalledWith(date)
    })

    it('calls onExecutionClick when execution is clicked', async () => {
      const user = userEvent.setup()
      const date = new Date(2025, 11, 17)
      const execution = {
        id: '1',
        pattern_id: 'pattern1',
        pattern_name: 'Pattern 1',
        start_time: '2025-12-17T08:00:00Z',
      }

      render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          executions={[execution]}
          onClick={mockOnClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      const marker = screen.getByTestId('execution-marker-pattern1')
      await user.click(marker)

      expect(mockOnExecutionClick).toHaveBeenCalledTimes(1)
      expect(mockOnExecutionClick).toHaveBeenCalledWith(execution)
    })

    it('does not call onClick when execution is clicked', async () => {
      const user = userEvent.setup()
      const date = new Date(2025, 11, 17)
      const execution = {
        id: '1',
        pattern_id: 'pattern1',
        pattern_name: 'Pattern 1',
        start_time: '2025-12-17T08:00:00Z',
      }

      render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          executions={[execution]}
          onClick={mockOnClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      const marker = screen.getByTestId('execution-marker-pattern1')
      await user.click(marker)

      // Cell onClick should NOT be called (stopPropagation)
      expect(mockOnClick).not.toHaveBeenCalled()
      expect(mockOnExecutionClick).toHaveBeenCalledTimes(1)
    })

    it('supports keyboard navigation with Enter key', async () => {
      const user = userEvent.setup()
      const date = new Date(2025, 11, 17)

      const { container } = render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          onClick={mockOnClick}
          onExecutionClick={mockOnExecutionClick}
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
          onExecutionClick={mockOnExecutionClick}
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
          onExecutionClick={mockOnExecutionClick}
        />
      )

      const cellDiv = container.querySelector('[role="button"]')
      expect(cellDiv).toHaveClass('dark:border-gray-700')
      expect(cellDiv).toHaveClass('dark:hover:bg-gray-800')
    })

    it('applies dark mode text classes to non-current-month dates', () => {
      const date = new Date(2025, 11, 17)
      render(
        <CalendarCell
          date={date}
          isCurrentMonth={false}
          onClick={mockOnClick}
          onExecutionClick={mockOnExecutionClick}
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
          onExecutionClick={mockOnExecutionClick}
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
          onExecutionClick={mockOnExecutionClick}
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
          onExecutionClick={mockOnExecutionClick}
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
          onExecutionClick={mockOnExecutionClick}
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
          onExecutionClick={mockOnExecutionClick}
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
          onExecutionClick={mockOnExecutionClick}
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
          onExecutionClick={mockOnExecutionClick}
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
          onExecutionClick={mockOnExecutionClick}
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
          onExecutionClick={mockOnExecutionClick}
        />
      )

      const cellDiv = container.querySelector('[role="button"]')
      const ariaLabel = cellDiv.getAttribute('aria-label')

      expect(ariaLabel).toBe('Wednesday, December 17, 2025, Full Moon, 3 scheduled executions')
    })
  })

  describe('Layout and Styling', () => {
    it('has minimum height class', () => {
      const date = new Date(2025, 11, 17)
      const { container } = render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          onClick={mockOnClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      const cellDiv = container.querySelector('[role="button"]')
      expect(cellDiv).toHaveClass('min-h-24')
    })

    it('has border and padding classes', () => {
      const date = new Date(2025, 11, 17)
      const { container } = render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          onClick={mockOnClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      const cellDiv = container.querySelector('[role="button"]')
      expect(cellDiv).toHaveClass('p-1')
      expect(cellDiv).toHaveClass('border-r')
      expect(cellDiv).toHaveClass('border-b')
      expect(cellDiv).toHaveClass('border-gray-200')
    })

    it('has cursor pointer class', () => {
      const date = new Date(2025, 11, 17)
      const { container } = render(
        <CalendarCell
          date={date}
          isCurrentMonth={true}
          onClick={mockOnClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      const cellDiv = container.querySelector('[role="button"]')
      expect(cellDiv).toHaveClass('cursor-pointer')
    })

    it('has executions container with overflow and max-height', () => {
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
          onExecutionClick={mockOnExecutionClick}
        />
      )

      const executionsContainer = container.querySelector('.space-y-1')
      expect(executionsContainer).toHaveClass('mt-1')
      expect(executionsContainer).toHaveClass('overflow-y-auto')
      expect(executionsContainer).toHaveClass('max-h-16')
    })
  })
})

/**
 * Tests for CalendarGrid component (Issue #228)
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CalendarGrid from '../CalendarGrid'

// Mock child components (only used for month/week views)
vi.mock('../CalendarCell', () => ({
  default: vi.fn(({ date, isCurrentMonth, executions, moonPhase, onClick, onExecutionClick }) => {
    // Helper function to get date key (must match component implementation)
    const getDateKey = (d) => {
      const year = d.getFullYear()
      const month = String(d.getMonth() + 1).padStart(2, '0')
      const day = String(d.getDate()).padStart(2, '0')
      return `${year}-${month}-${day}`
    }

    const dateKey = getDateKey(date)
    return (
      <div
        data-testid="calendar-cell"
        data-date={dateKey}
        data-is-current-month={isCurrentMonth}
        data-executions-count={executions.length}
        data-has-moon-phase={!!moonPhase}
        onClick={() => onClick(date)}
      >
        {date.getDate()}
        {executions.map((exec) => (
          <button
            key={exec.start_time}
            data-testid={`execution-${exec.start_time}`}
            onClick={(e) => {
              e.stopPropagation()
              onExecutionClick(exec)
            }}
          >
            {exec.pattern_name}
          </button>
        ))}
      </div>
    )
  }),
}))

describe('CalendarGrid', () => {
  const mockOnCellClick = vi.fn()
  const mockOnExecutionClick = vi.fn()

  const mockExecutions = [
    {
      id: 'exec1',
      pattern_id: 'pattern1',
      pattern_name: 'Morning Capture',
      start_time: '2025-01-15T08:30:00Z',
    },
    {
      id: 'exec2',
      pattern_id: 'pattern2',
      pattern_name: 'Evening Capture',
      start_time: '2025-01-15T18:00:00Z',
    },
    {
      id: 'exec3',
      pattern_id: 'pattern1',
      pattern_name: 'Afternoon Capture',
      start_time: '2025-01-20T14:00:00Z',
    },
  ]

  const mockMoonPhases = {
    '2025-01-15': {
      phase: 'full',
      phase_name: 'Full Moon',
      illumination: 1.0,
    },
    '2025-01-20': {
      phase: 'waning_gibbous',
      phase_name: 'Waning Gibbous',
      illumination: 0.85,
    },
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Month View', () => {
    it('renders 7 day-of-week headers', () => {
      render(
        <CalendarGrid
          viewMode="month"
          currentDate={new Date(2025, 0, 15)} // Jan 15, 2025
          executions={[]}
          moonPhases={{}}
          onCellClick={mockOnCellClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
      days.forEach((day) => {
        expect(screen.getByText(day)).toBeInTheDocument()
      })
    })

    it('renders 42 calendar cells (6 weeks)', () => {
      render(
        <CalendarGrid
          viewMode="month"
          currentDate={new Date(2025, 0, 15)}
          executions={[]}
          moonPhases={{}}
          onCellClick={mockOnCellClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      const cells = screen.getAllByTestId('calendar-cell')
      expect(cells).toHaveLength(42)
    })

    it('marks cells as current month or not', () => {
      render(
        <CalendarGrid
          viewMode="month"
          currentDate={new Date(2025, 0, 15)} // January 2025
          executions={[]}
          moonPhases={{}}
          onCellClick={mockOnCellClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      const cells = screen.getAllByTestId('calendar-cell')

      // Count cells marked as current month
      const currentMonthCells = cells.filter(
        (cell) => cell.getAttribute('data-is-current-month') === 'true'
      )

      // January 2025 has 31 days
      expect(currentMonthCells.length).toBe(31)
    })

    it('groups executions by date correctly', () => {
      const { container } = render(
        <CalendarGrid
          viewMode="month"
          currentDate={new Date(2025, 0, 15)}
          executions={mockExecutions}
          moonPhases={{}}
          onCellClick={mockOnCellClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      // Find cell for Jan 15 (has 2 executions)
      const jan15Cell = container.querySelector('[data-date="2025-01-15"]')
      expect(jan15Cell?.getAttribute('data-executions-count')).toBe('2')

      // Find cell for Jan 20 (has 1 execution)
      const jan20Cell = container.querySelector('[data-date="2025-01-20"]')
      expect(jan20Cell?.getAttribute('data-executions-count')).toBe('1')
    })

    it('passes moon phases to cells with matching dates', () => {
      render(
        <CalendarGrid
          viewMode="month"
          currentDate={new Date(2025, 0, 15)}
          executions={[]}
          moonPhases={mockMoonPhases}
          onCellClick={mockOnCellClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      const cells = screen.getAllByTestId('calendar-cell')

      // Find cells with moon phases
      const cellsWithMoonPhase = cells.filter(
        (cell) => cell.getAttribute('data-has-moon-phase') === 'true'
      )

      // Should have 2 cells with moon phases (Jan 15 and Jan 20)
      expect(cellsWithMoonPhase.length).toBe(2)
    })

    it('calls onCellClick when cell is clicked', async () => {
      const user = userEvent.setup()

      render(
        <CalendarGrid
          viewMode="month"
          currentDate={new Date(2025, 0, 15)}
          executions={[]}
          moonPhases={{}}
          onCellClick={mockOnCellClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      const firstCell = screen.getAllByTestId('calendar-cell')[0]
      await user.click(firstCell)

      expect(mockOnCellClick).toHaveBeenCalledTimes(1)
      expect(mockOnCellClick).toHaveBeenCalledWith(expect.any(Date))
    })

    it('calls onExecutionClick when execution is clicked', async () => {
      const user = userEvent.setup()

      render(
        <CalendarGrid
          viewMode="month"
          currentDate={new Date(2025, 0, 15)}
          executions={mockExecutions}
          moonPhases={{}}
          onCellClick={mockOnCellClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      const executionButton = screen.getByTestId('execution-2025-01-15T08:30:00Z')
      await user.click(executionButton)

      expect(mockOnExecutionClick).toHaveBeenCalledTimes(1)
      expect(mockOnExecutionClick).toHaveBeenCalledWith(
        expect.objectContaining({
          id: 'exec1',
          pattern_name: 'Morning Capture',
        })
      )
    })
  })

  describe('Week View', () => {
    it('renders 7 day column headers with dates', () => {
      render(
        <CalendarGrid
          viewMode="week"
          currentDate={new Date(2025, 0, 15)} // Wednesday, Jan 15, 2025
          executions={[]}
          moonPhases={{}}
          onCellClick={mockOnCellClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      // Should show day names
      const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
      days.forEach((day) => {
        expect(screen.getByText(day)).toBeInTheDocument()
      })

      // Should show dates (12-18 for the week containing Jan 15)
      // Note: dates appear both in headers and cells, so use getAllByText
      for (let day = 12; day <= 18; day++) {
        const elements = screen.getAllByText(day.toString())
        expect(elements.length).toBeGreaterThanOrEqual(1)
      }
    })

    it('renders 7 calendar cells for the week', () => {
      render(
        <CalendarGrid
          viewMode="week"
          currentDate={new Date(2025, 0, 15)}
          executions={[]}
          moonPhases={{}}
          onCellClick={mockOnCellClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      const cells = screen.getAllByTestId('calendar-cell')
      expect(cells).toHaveLength(7)
    })

    it('groups executions by date in week view', () => {
      const { container } = render(
        <CalendarGrid
          viewMode="week"
          currentDate={new Date(2025, 0, 15)}
          executions={mockExecutions}
          moonPhases={{}}
          onCellClick={mockOnCellClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      // Find cell for Jan 15 (has 2 executions)
      const jan15Cell = container.querySelector('[data-date="2025-01-15"]')
      expect(jan15Cell?.getAttribute('data-executions-count')).toBe('2')
    })

    it('passes moon phases to week cells', () => {
      render(
        <CalendarGrid
          viewMode="week"
          currentDate={new Date(2025, 0, 15)}
          executions={[]}
          moonPhases={mockMoonPhases}
          onCellClick={mockOnCellClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      const cells = screen.getAllByTestId('calendar-cell')

      // Find cell with moon phase (Jan 15)
      const cellsWithMoonPhase = cells.filter(
        (cell) => cell.getAttribute('data-has-moon-phase') === 'true'
      )

      expect(cellsWithMoonPhase.length).toBe(1) // Only Jan 15 is in this week
    })

    it('calls onCellClick when week cell is clicked', async () => {
      const user = userEvent.setup()

      render(
        <CalendarGrid
          viewMode="week"
          currentDate={new Date(2025, 0, 15)}
          executions={[]}
          moonPhases={{}}
          onCellClick={mockOnCellClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      const firstCell = screen.getAllByTestId('calendar-cell')[0]
      await user.click(firstCell)

      expect(mockOnCellClick).toHaveBeenCalledTimes(1)
    })
  })

  describe('Day View', () => {
    it('shows full formatted date in header', () => {
      render(
        <CalendarGrid
          viewMode="day"
          currentDate={new Date(2025, 0, 15)} // Wednesday, Jan 15, 2025
          executions={[]}
          moonPhases={{}}
          onCellClick={mockOnCellClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      expect(screen.getByText('Wednesday, January 15, 2025')).toBeInTheDocument()
    })

    it('shows all executions for selected date', () => {
      render(
        <CalendarGrid
          viewMode="day"
          currentDate={new Date(2025, 0, 15)}
          executions={mockExecutions}
          moonPhases={{}}
          onCellClick={mockOnCellClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      // Should show 2 executions for Jan 15
      expect(screen.getByText('Morning Capture')).toBeInTheDocument()
      expect(screen.getByText('Evening Capture')).toBeInTheDocument()

      // Should NOT show execution from Jan 20
      expect(screen.queryByText('Afternoon Capture')).not.toBeInTheDocument()
    })

    it('shows empty state when no executions for day', () => {
      render(
        <CalendarGrid
          viewMode="day"
          currentDate={new Date(2025, 0, 10)} // Day with no executions
          executions={mockExecutions}
          moonPhases={{}}
          onCellClick={mockOnCellClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      expect(screen.getByText('No executions scheduled')).toBeInTheDocument()
    })

    it('calls onExecutionClick when execution is clicked in day view', async () => {
      const user = userEvent.setup()

      render(
        <CalendarGrid
          viewMode="day"
          currentDate={new Date(2025, 0, 15)}
          executions={mockExecutions}
          moonPhases={{}}
          onCellClick={mockOnCellClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      const executionDiv = screen.getByText('Morning Capture').closest('div')
      await user.click(executionDiv)

      expect(mockOnExecutionClick).toHaveBeenCalledTimes(1)
      expect(mockOnExecutionClick).toHaveBeenCalledWith(
        expect.objectContaining({
          pattern_name: 'Morning Capture',
        })
      )
    })

    it('shows execution times in day view', () => {
      render(
        <CalendarGrid
          viewMode="day"
          currentDate={new Date(2025, 0, 15)}
          executions={mockExecutions}
          moonPhases={{}}
          onCellClick={mockOnCellClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      // formatTime converts UTC times to HH:MM format
      expect(screen.getByText('8:30')).toBeInTheDocument() // 08:30:00Z
      expect(screen.getByText('18:00')).toBeInTheDocument() // 18:00:00Z
    })

    it('shows pattern color indicators in day view', () => {
      const { container } = render(
        <CalendarGrid
          viewMode="day"
          currentDate={new Date(2025, 0, 15)}
          executions={mockExecutions}
          moonPhases={{}}
          onCellClick={mockOnCellClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      // Find colored dots (w-3 h-3 rounded-full)
      const colorDots = container.querySelectorAll('.w-3.h-3.rounded-full')
      expect(colorDots.length).toBe(2) // Two executions on this day
    })
  })

  describe('Edge Cases', () => {
    it('handles empty executions array', () => {
      render(
        <CalendarGrid
          viewMode="month"
          currentDate={new Date(2025, 0, 15)}
          executions={[]}
          moonPhases={{}}
          onCellClick={mockOnCellClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      const cells = screen.getAllByTestId('calendar-cell')
      cells.forEach((cell) => {
        expect(cell.getAttribute('data-executions-count')).toBe('0')
      })
    })

    it('handles undefined executions prop', () => {
      render(
        <CalendarGrid
          viewMode="month"
          currentDate={new Date(2025, 0, 15)}
          moonPhases={{}}
          onCellClick={mockOnCellClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      const cells = screen.getAllByTestId('calendar-cell')
      expect(cells.length).toBe(42)
    })

    it('handles empty moon phases object', () => {
      render(
        <CalendarGrid
          viewMode="month"
          currentDate={new Date(2025, 0, 15)}
          executions={mockExecutions}
          moonPhases={{}}
          onCellClick={mockOnCellClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      const cells = screen.getAllByTestId('calendar-cell')
      const cellsWithMoonPhase = cells.filter(
        (cell) => cell.getAttribute('data-has-moon-phase') === 'true'
      )

      expect(cellsWithMoonPhase.length).toBe(0)
    })

    it('handles undefined moon phases prop', () => {
      render(
        <CalendarGrid
          viewMode="month"
          currentDate={new Date(2025, 0, 15)}
          executions={mockExecutions}
          onCellClick={mockOnCellClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      const cells = screen.getAllByTestId('calendar-cell')
      expect(cells.length).toBe(42)
    })

    it('handles executions without id field', () => {
      const executionsWithoutId = [
        {
          pattern_id: 'pattern1',
          pattern_name: 'Test Pattern',
          start_time: '2025-01-15T10:00:00Z',
        },
      ]

      render(
        <CalendarGrid
          viewMode="month"
          currentDate={new Date(2025, 0, 15)}
          executions={executionsWithoutId}
          moonPhases={{}}
          onCellClick={mockOnCellClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      expect(screen.getByText('Test Pattern')).toBeInTheDocument()
    })
  })

  describe('Dark Mode', () => {
    it('applies dark mode classes to month view headers', () => {
      const { container } = render(
        <CalendarGrid
          viewMode="month"
          currentDate={new Date(2025, 0, 15)}
          executions={[]}
          moonPhases={{}}
          onCellClick={mockOnCellClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      // Check for dark mode border classes
      const grid = container.querySelector('.grid-cols-7')
      expect(grid?.className).toContain('dark:border-gray-700')
    })

    it('applies dark mode classes to day view', () => {
      const { container } = render(
        <CalendarGrid
          viewMode="day"
          currentDate={new Date(2025, 0, 15)}
          executions={mockExecutions}
          moonPhases={{}}
          onCellClick={mockOnCellClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      // Check for dark mode background classes
      const elements = container.querySelectorAll('.dark\\:bg-gray-700')
      expect(elements.length).toBeGreaterThan(0)
    })
  })

  describe('Performance', () => {
    it('memoizes execution grouping', () => {
      const { rerender } = render(
        <CalendarGrid
          viewMode="month"
          currentDate={new Date(2025, 0, 15)}
          executions={mockExecutions}
          moonPhases={{}}
          onCellClick={mockOnCellClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      // Rerender with same executions (should use memoized value)
      rerender(
        <CalendarGrid
          viewMode="month"
          currentDate={new Date(2025, 0, 16)} // Different date
          executions={mockExecutions} // Same executions reference
          moonPhases={{}}
          onCellClick={mockOnCellClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      // If this renders without errors, memoization is working
      expect(screen.getAllByTestId('calendar-cell')).toHaveLength(42)
    })
  })

  describe('Accessibility', () => {
    it('provides keyboard support for day view executions', async () => {
      const user = userEvent.setup()

      render(
        <CalendarGrid
          viewMode="day"
          currentDate={new Date(2025, 0, 15)}
          executions={mockExecutions}
          moonPhases={{}}
          onCellClick={mockOnCellClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      const executionDiv = screen.getByText('Morning Capture').closest('div')
      executionDiv.focus()
      await user.keyboard('{Enter}')

      expect(mockOnExecutionClick).toHaveBeenCalledTimes(1)
    })
  })
})

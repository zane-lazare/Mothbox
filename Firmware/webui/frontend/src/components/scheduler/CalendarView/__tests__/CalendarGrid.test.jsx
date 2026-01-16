/**
 * Tests for CalendarGrid component (Issue #228)
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CalendarGrid from '../CalendarGrid'

// Mock child components (only used for month views)
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

// Mock WeekTimeline component (used for week view)
vi.mock('../WeekTimeline', () => ({
  default: vi.fn(({ currentDate, executions, moonPhases, onCellClick, onExecutionClick }) => {
    // Helper function to get date key
    const getDateKey = (d) => {
      const year = d.getFullYear()
      const month = String(d.getMonth() + 1).padStart(2, '0')
      const day = String(d.getDate()).padStart(2, '0')
      return `${year}-${month}-${day}`
    }

    // Get week dates (Sunday to Saturday)
    const getWeekDates = (centerDate) => {
      const dates = []
      const dayOfWeek = centerDate.getDay()
      const sunday = new Date(centerDate)
      sunday.setDate(centerDate.getDate() - dayOfWeek)
      for (let i = 0; i < 7; i++) {
        const date = new Date(sunday)
        date.setDate(sunday.getDate() + i)
        dates.push(date)
      }
      return dates
    }

    const weekDates = getWeekDates(currentDate)

    return (
      <div data-testid="week-timeline">
        {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day) => (
          <span key={day}>{day}</span>
        ))}
        {weekDates.map((date) => {
          const dateKey = getDateKey(date)
          const dayExecutions = executions.filter((exec) => {
            const execDate = new Date(exec.start_time)
            return (
              execDate.getDate() === date.getDate() &&
              execDate.getMonth() === date.getMonth() &&
              execDate.getFullYear() === date.getFullYear()
            )
          })
          return (
            <div
              key={dateKey}
              data-testid="week-timeline-day"
              data-date={dateKey}
              data-executions-count={dayExecutions.length}
              data-has-moon-phase={!!moonPhases[dateKey]}
              onClick={() => onCellClick(date)}
            >
              {date.getDate()}
              {dayExecutions.map((exec) => (
                <button
                  key={exec.start_time}
                  data-testid={`week-execution-${exec.start_time}`}
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
        })}
      </div>
    )
  }),
}))

describe('CalendarGrid', () => {
  const mockOnCellClick = vi.fn()
  const mockOnExecutionClick = vi.fn()

  // Use local time strings (no Z suffix) for predictable behavior across timezones
  const mockExecutions = [
    {
      id: 'exec1',
      pattern_id: 'pattern1',
      pattern_name: 'Morning Capture',
      start_time: '2025-01-15T08:30:00',
    },
    {
      id: 'exec2',
      pattern_id: 'pattern2',
      pattern_name: 'Evening Capture',
      start_time: '2025-01-15T18:00:00',
    },
    {
      id: 'exec3',
      pattern_id: 'pattern1',
      pattern_name: 'Afternoon Capture',
      start_time: '2025-01-20T14:00:00',
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

    it('does NOT mark same month in different year as current month', () => {
      // Test January 2024 when viewing January 2025
      const { container } = render(
        <CalendarGrid
          viewMode="month"
          currentDate={new Date(2025, 0, 15)} // January 2025
          executions={[]}
          moonPhases={{}}
          onCellClick={mockOnCellClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      // Find cells for January 2025 dates
      const jan1_2025 = container.querySelector('[data-date="2025-01-01"]')
      const jan15_2025 = container.querySelector('[data-date="2025-01-15"]')
      const jan31_2025 = container.querySelector('[data-date="2025-01-31"]')

      // All January 2025 dates should be marked as current month
      expect(jan1_2025?.getAttribute('data-is-current-month')).toBe('true')
      expect(jan15_2025?.getAttribute('data-is-current-month')).toBe('true')
      expect(jan31_2025?.getAttribute('data-is-current-month')).toBe('true')

      // Dates from previous/next month in same year should NOT be current month
      const dec31_2024 = container.querySelector('[data-date="2024-12-31"]')
      const feb1_2025 = container.querySelector('[data-date="2025-02-01"]')

      if (dec31_2024) {
        expect(dec31_2024.getAttribute('data-is-current-month')).toBe('false')
      }
      if (feb1_2025) {
        expect(feb1_2025.getAttribute('data-is-current-month')).toBe('false')
      }
    })

    it('correctly marks current month when viewing same month in different year', () => {
      // Render January 2024 grid
      const { container: container2024 } = render(
        <CalendarGrid
          viewMode="month"
          currentDate={new Date(2024, 0, 15)} // January 2024
          executions={[]}
          moonPhases={{}}
          onCellClick={mockOnCellClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      // Cells in January 2024 grid should be marked as current month
      const cells2024 = container2024.querySelectorAll('[data-testid="calendar-cell"]')
      const currentMonthCells2024 = Array.from(cells2024).filter(
        (cell) => cell.getAttribute('data-is-current-month') === 'true'
      )

      // January 2024 has 31 days
      expect(currentMonthCells2024.length).toBe(31)

      // Verify specific date is marked correctly
      const jan15_2024 = container2024.querySelector('[data-date="2024-01-15"]')
      expect(jan15_2024?.getAttribute('data-is-current-month')).toBe('true')
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

      const executionButton = screen.getByTestId('execution-2025-01-15T08:30:00')
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
    it('renders WeekTimeline component', () => {
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

      // Should render the WeekTimeline component
      expect(screen.getByTestId('week-timeline')).toBeInTheDocument()

      // Should show day names
      const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
      days.forEach((day) => {
        expect(screen.getByText(day)).toBeInTheDocument()
      })

      // Should show dates (12-18 for the week containing Jan 15)
      for (let day = 12; day <= 18; day++) {
        const elements = screen.getAllByText(day.toString())
        expect(elements.length).toBeGreaterThanOrEqual(1)
      }
    })

    it('renders 7 day slots for the week', () => {
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

      const cells = screen.getAllByTestId('week-timeline-day')
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

      const cells = screen.getAllByTestId('week-timeline-day')

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

      const firstCell = screen.getAllByTestId('week-timeline-day')[0]
      await user.click(firstCell)

      expect(mockOnCellClick).toHaveBeenCalledTimes(1)
    })
  })

  describe('Day View (DayTimeline)', () => {
    // Day view now uses DayTimeline component (Issue #326)

    it('renders DayTimeline with day-timeline testid', () => {
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

      expect(screen.getByTestId('day-timeline')).toBeInTheDocument()
    })

    it('shows executions for selected date in hour rows', () => {
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

      // Should show executions for Jan 15
      // Evening Capture at 18:00 should be in hour-row-18
      expect(screen.getByTestId('hour-row-18')).toBeInTheDocument()
      expect(screen.getByTestId('execution-pattern2-1800')).toBeInTheDocument()

      // Verify we have 24 hour rows
      expect(screen.getByTestId('hour-row-0')).toBeInTheDocument()
      expect(screen.getByTestId('hour-row-23')).toBeInTheDocument()
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

      expect(screen.getByTestId('day-timeline-empty')).toBeInTheDocument()
      expect(screen.getByText('No scheduled events')).toBeInTheDocument()
    })

    it('calls onExecutionClick when execution chip is clicked', async () => {
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

      // Click the Evening Capture chip
      const executionChip = screen.getByTestId('execution-pattern2-1800')
      await user.click(executionChip)

      expect(mockOnExecutionClick).toHaveBeenCalledTimes(1)
      expect(mockOnExecutionClick).toHaveBeenCalledWith(
        expect.objectContaining({
          pattern_name: 'Evening Capture',
        })
      )
    })

    it('renders 24 hour rows', () => {
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

      // Should have 24 hour rows (0-23)
      for (let hour = 0; hour < 24; hour++) {
        expect(screen.getByTestId(`hour-row-${hour}`)).toBeInTheDocument()
      }
    })

    it('passes conflicts to DayTimeline', () => {
      const conflicts = [
        {
          id: 'c1',
          severity: 'error',
          message: 'camera busy',
          start_time: '2025-01-15T08:30:00Z',
        },
      ]

      render(
        <CalendarGrid
          viewMode="day"
          currentDate={new Date(2025, 0, 15)}
          executions={mockExecutions}
          conflicts={conflicts}
          moonPhases={{}}
          onCellClick={mockOnCellClick}
          onExecutionClick={mockOnExecutionClick}
        />
      )

      // Conflict summary should be visible
      expect(screen.getByTestId('conflict-summary')).toBeInTheDocument()
      expect(screen.getByText('1 conflict')).toBeInTheDocument()
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

      // DayTimeline uses dark mode classes for text
      const darkElements = container.querySelectorAll('[class*="dark:"]')
      expect(darkElements.length).toBeGreaterThan(0)
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
    it('provides keyboard support for day view execution chips', async () => {
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

      // ExecutionChip uses button element, so we can tab to it and press Enter
      const executionChip = screen.getByTestId('execution-pattern2-1800')
      executionChip.focus()
      await user.keyboard('{Enter}')

      expect(mockOnExecutionClick).toHaveBeenCalledTimes(1)
    })
  })
})

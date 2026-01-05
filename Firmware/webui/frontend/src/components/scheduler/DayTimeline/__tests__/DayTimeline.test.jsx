/**
 * Tests for DayTimeline component (Issue #326)
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, within } from '@testing-library/react'
import DayTimeline from '../DayTimeline'

describe('DayTimeline', () => {
  const mockDate = '2025-12-17'

  const mockExecutions = [
    {
      pattern_id: 'routine-1',
      pattern_name: 'Photo Capture',
      start_time: '2025-12-17T18:00:00Z',
      actions: [{ action_name: 'Take Photo', action_type: 'camera' }],
    },
    {
      pattern_id: 'routine-2',
      pattern_name: 'Attract On',
      start_time: '2025-12-17T18:15:00Z',
      actions: [{ action_name: 'Attract On', action_type: 'gpio' }],
    },
    {
      pattern_id: 'routine-3',
      pattern_name: 'Evening Photo',
      start_time: '2025-12-17T19:00:00Z',
      actions: [{ action_name: 'Take Photo', action_type: 'camera' }],
    },
    {
      pattern_id: 'routine-4',
      pattern_name: 'HDR Shot',
      start_time: '2025-12-17T19:00:00Z',
      actions: [{ action_name: 'HDR Bracket', action_type: 'camera' }],
    },
  ]

  const mockConflicts = [
    {
      id: 'c1',
      conflict_type: 'time_overlap',
      severity: 'error',
      event1_id: 'routine-3',
      event1_name: 'Evening Photo',
      event2_id: 'routine-4',
      event2_name: 'HDR Shot',
      start_time: '2025-12-17T19:00:00Z',
      end_time: '2025-12-17T19:15:00Z',
      message: 'camera busy',
    },
  ]

  describe('Rendering', () => {
    it('renders with correct data-testid', () => {
      render(<DayTimeline date={mockDate} executions={mockExecutions} />)
      expect(screen.getByTestId('day-timeline')).toBeInTheDocument()
    })

    it('renders 24 hour rows', () => {
      render(<DayTimeline date={mockDate} executions={mockExecutions} />)
      for (let hour = 0; hour < 24; hour++) {
        expect(screen.getByTestId(`hour-row-${hour}`)).toBeInTheDocument()
      }
    })

    it('renders executions in correct hour rows', () => {
      render(<DayTimeline date={mockDate} executions={mockExecutions} />)

      // Hour 18 should have 2 executions
      const row18 = screen.getByTestId('hour-row-18')
      expect(within(row18).getByTestId('execution-routine-1-1800')).toBeInTheDocument()
      expect(within(row18).getByTestId('execution-routine-2-1815')).toBeInTheDocument()

      // Hour 19 should have 2 executions
      const row19 = screen.getByTestId('hour-row-19')
      expect(within(row19).getByTestId('execution-routine-3-1900')).toBeInTheDocument()
      expect(within(row19).getByTestId('execution-routine-4-1900')).toBeInTheDocument()
    })

    it('shows empty state when no executions', () => {
      render(<DayTimeline date={mockDate} executions={[]} />)
      expect(screen.getByTestId('day-timeline-empty')).toBeInTheDocument()
      expect(screen.getByText('No scheduled events')).toBeInTheDocument()
    })

    it('shows empty state when executions is undefined', () => {
      render(<DayTimeline date={mockDate} />)
      expect(screen.getByTestId('day-timeline-empty')).toBeInTheDocument()
    })

    it('has correct aria-label', () => {
      render(<DayTimeline date={mockDate} executions={mockExecutions} />)
      expect(screen.getByTestId('day-timeline')).toHaveAttribute(
        'aria-label',
        'Day timeline for 2025-12-17'
      )
    })
  })

  describe('Legend', () => {
    it('renders legend with Camera label', () => {
      render(<DayTimeline date={mockDate} executions={mockExecutions} />)
      expect(screen.getByText('Camera')).toBeInTheDocument()
    })

    it('renders legend with GPIO label', () => {
      render(<DayTimeline date={mockDate} executions={mockExecutions} />)
      expect(screen.getByText('GPIO')).toBeInTheDocument()
    })

    it('renders legend with Collision label', () => {
      render(<DayTimeline date={mockDate} executions={mockExecutions} />)
      expect(screen.getByText('Collision')).toBeInTheDocument()
    })

    it('renders legend with Warning label', () => {
      render(<DayTimeline date={mockDate} executions={mockExecutions} />)
      expect(screen.getByText('Warning')).toBeInTheDocument()
    })
  })

  describe('Conflict Summary', () => {
    it('shows conflict summary when conflicts exist', () => {
      render(
        <DayTimeline
          date={mockDate}
          executions={mockExecutions}
          conflicts={mockConflicts}
        />
      )
      expect(screen.getByTestId('conflict-summary')).toBeInTheDocument()
    })

    it('does not show conflict summary when no conflicts', () => {
      render(
        <DayTimeline date={mockDate} executions={mockExecutions} conflicts={[]} />
      )
      expect(screen.queryByTestId('conflict-summary')).not.toBeInTheDocument()
    })

    it('shows correct conflict count', () => {
      render(
        <DayTimeline
          date={mockDate}
          executions={mockExecutions}
          conflicts={mockConflicts}
        />
      )
      expect(screen.getByText('1 conflict')).toBeInTheDocument()
    })
  })

  describe('Conflict Highlighting', () => {
    it('applies red background to hour with error conflict', () => {
      render(
        <DayTimeline
          date={mockDate}
          executions={mockExecutions}
          conflicts={mockConflicts}
        />
      )
      const row19 = screen.getByTestId('hour-row-19')
      expect(row19).toHaveClass('bg-red-950/20')
    })

    it('shows conflict message in affected hour row', () => {
      render(
        <DayTimeline
          date={mockDate}
          executions={mockExecutions}
          conflicts={mockConflicts}
        />
      )
      expect(screen.getByText('camera busy')).toBeInTheDocument()
    })

    it('applies red ring to conflicting execution chips', () => {
      render(
        <DayTimeline
          date={mockDate}
          executions={mockExecutions}
          conflicts={mockConflicts}
        />
      )
      const chip = screen.getByTestId('execution-routine-3-1900')
      expect(chip).toHaveClass('ring-1')
      expect(chip).toHaveClass('ring-red-400')
    })

    it('does not highlight non-conflicting executions', () => {
      render(
        <DayTimeline
          date={mockDate}
          executions={mockExecutions}
          conflicts={mockConflicts}
        />
      )
      const chip = screen.getByTestId('execution-routine-1-1800')
      expect(chip).not.toHaveClass('ring-1')
    })

    it('applies yellow highlighting for warning conflicts', () => {
      const warningConflict = [
        {
          id: 'c2',
          conflict_type: 'gpio_state_conflict',
          severity: 'warning',
          event1_id: 'routine-2',
          start_time: '2025-12-17T18:15:00Z',
          message: 'unexpected',
        },
      ]
      render(
        <DayTimeline
          date={mockDate}
          executions={mockExecutions}
          conflicts={warningConflict}
        />
      )
      const row18 = screen.getByTestId('hour-row-18')
      expect(row18).toHaveClass('bg-yellow-950/20')
    })
  })

  describe('Interaction', () => {
    it('calls onExecutionClick when chip is clicked', () => {
      const handleClick = vi.fn()
      render(
        <DayTimeline
          date={mockDate}
          executions={mockExecutions}
          onExecutionClick={handleClick}
        />
      )
      fireEvent.click(screen.getByTestId('execution-routine-1-1800'))
      expect(handleClick).toHaveBeenCalledTimes(1)
      expect(handleClick).toHaveBeenCalledWith(mockExecutions[0])
    })

    it('does not throw when onExecutionClick is not provided', () => {
      render(<DayTimeline date={mockDate} executions={mockExecutions} />)
      expect(() => {
        fireEvent.click(screen.getByTestId('execution-routine-1-1800'))
      }).not.toThrow()
    })
  })

  describe('Date Filtering', () => {
    it('only shows executions for the specified date', () => {
      const mixedDateExecutions = [
        ...mockExecutions,
        {
          pattern_id: 'routine-5',
          pattern_name: 'Tomorrow Photo',
          start_time: '2025-12-18T18:00:00Z',
          actions: [{ action_name: 'Take Photo', action_type: 'camera' }],
        },
      ]
      render(<DayTimeline date={mockDate} executions={mixedDateExecutions} />)

      // Should have executions from 2025-12-17
      expect(screen.getByTestId('execution-routine-1-1800')).toBeInTheDocument()

      // Should not have execution from 2025-12-18
      expect(screen.queryByTestId('execution-routine-5-1800')).not.toBeInTheDocument()
    })
  })

  describe('Timeline Grid Styling', () => {
    it('has border around timeline grid', () => {
      render(<DayTimeline date={mockDate} executions={mockExecutions} />)
      // Find the grid container (parent of hour rows)
      const row0 = screen.getByTestId('hour-row-0')
      const grid = row0.parentElement
      expect(grid).toHaveClass('border')
      expect(grid).toHaveClass('border-gray-800')
      expect(grid).toHaveClass('rounded-lg')
    })

    it('has dividers between hours', () => {
      render(<DayTimeline date={mockDate} executions={mockExecutions} />)
      const row0 = screen.getByTestId('hour-row-0')
      const grid = row0.parentElement
      expect(grid).toHaveClass('divide-y')
      expect(grid).toHaveClass('divide-gray-800')
    })
  })
})

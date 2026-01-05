/**
 * Tests for DayTimeline component (Issue #326)
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import DayTimeline from '../DayTimeline'
import {
  mockDate,
  mockExecutions,
  mockConflicts,
  mockErrorConflict,
  mockWarningConflict,
} from './testFixtures'

describe('DayTimeline', () => {

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
      render(
        <DayTimeline
          date={mockDate}
          executions={mockExecutions}
          conflicts={[mockWarningConflict]}
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

  describe('Complete Conflict Flow (Integration)', () => {
    it('displays complete conflict visualization flow', () => {
      render(
        <DayTimeline
          date={mockDate}
          executions={mockExecutions}
          conflicts={mockConflicts}
        />
      )

      // 1. Conflict summary displayed
      expect(screen.getByTestId('conflict-summary')).toBeInTheDocument()

      // 2. Hour row highlighted with red background
      const hourRow = screen.getByTestId('hour-row-19')
      expect(hourRow).toHaveClass('bg-red-950/20')

      // 3. Execution chip has red ring
      const chip = screen.getByTestId('execution-routine-3-1900')
      expect(chip).toHaveClass('ring-1')
      expect(chip).toHaveClass('ring-red-400')

      // 4. Conflict message displayed
      expect(screen.getByText('camera busy')).toBeInTheDocument()
    })

    it('displays complete warning conflict visualization flow', () => {
      render(
        <DayTimeline
          date={mockDate}
          executions={mockExecutions}
          conflicts={[mockWarningConflict]}
        />
      )

      // 1. Conflict summary displayed
      expect(screen.getByTestId('conflict-summary')).toBeInTheDocument()

      // 2. Hour row highlighted with yellow background
      const hourRow = screen.getByTestId('hour-row-18')
      expect(hourRow).toHaveClass('bg-yellow-950/20')

      // 3. Execution chip has yellow ring
      const chip = screen.getByTestId('execution-routine-2-1815')
      expect(chip).toHaveClass('ring-1')
      expect(chip).toHaveClass('ring-yellow-400')

      // 4. Conflict message displayed
      expect(screen.getByText('unexpected GPIO state')).toBeInTheDocument()
    })

    it('handles mixed error and warning conflicts', () => {
      render(
        <DayTimeline
          date={mockDate}
          executions={mockExecutions}
          conflicts={[mockErrorConflict, mockWarningConflict]}
        />
      )

      // Both conflict types should be visible
      expect(screen.getByTestId('hour-row-19')).toHaveClass('bg-red-950/20')
      expect(screen.getByTestId('hour-row-18')).toHaveClass('bg-yellow-950/20')

      // Conflict summary should show 2 conflicts
      expect(screen.getByText('2 conflicts')).toBeInTheDocument()
    })
  })

  describe('Keyboard Navigation', () => {
    it('allows focus on execution chips', () => {
      render(<DayTimeline date={mockDate} executions={mockExecutions} />)

      const chip1 = screen.getByTestId('execution-routine-1-1800')
      chip1.focus()
      expect(chip1).toHaveFocus()
    })

    it('supports Enter key to activate chip', () => {
      const handleClick = vi.fn()
      render(
        <DayTimeline
          date={mockDate}
          executions={mockExecutions}
          onExecutionClick={handleClick}
        />
      )

      const chip = screen.getByTestId('execution-routine-1-1800')
      chip.focus()
      fireEvent.keyDown(chip, { key: 'Enter' })

      expect(handleClick).toHaveBeenCalledWith(mockExecutions[0])
    })

    it('supports Space key to activate chip', () => {
      const handleClick = vi.fn()
      render(
        <DayTimeline
          date={mockDate}
          executions={mockExecutions}
          onExecutionClick={handleClick}
        />
      )

      const chip = screen.getByTestId('execution-routine-1-1800')
      chip.focus()
      fireEvent.keyDown(chip, { key: ' ' })

      expect(handleClick).toHaveBeenCalledWith(mockExecutions[0])
    })

    it('allows tab navigation between execution chips', async () => {
      const user = userEvent.setup()
      render(<DayTimeline date={mockDate} executions={mockExecutions} />)

      const chip1 = screen.getByTestId('execution-routine-1-1800')
      const chip2 = screen.getByTestId('execution-routine-2-1815')

      // Focus first chip and tab to next
      chip1.focus()
      expect(chip1).toHaveFocus()

      await user.tab()
      expect(chip2).toHaveFocus()
    })

    it('execution chips are focusable buttons', () => {
      render(<DayTimeline date={mockDate} executions={mockExecutions} />)

      const chip = screen.getByTestId('execution-routine-1-1800')
      expect(chip.tagName).toBe('BUTTON')
      expect(chip).toHaveAttribute('type', 'button')
    })
  })
})

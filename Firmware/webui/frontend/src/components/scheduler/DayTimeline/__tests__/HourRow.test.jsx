/**
 * Tests for HourRow component (Issue #326)
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import HourRow from '../HourRow'
import {
  mockExecutions,
  mockErrorConflict,
  mockWarningConflict,
} from './testFixtures'

describe('HourRow', () => {
  // Use first two executions from fixtures for hour row tests
  const hourExecutions = mockExecutions.slice(0, 2)

  describe('Rendering', () => {
    it('renders with correct data-testid', () => {
      render(<HourRow hour={18} />)
      expect(screen.getByTestId('hour-row-18')).toBeInTheDocument()
    })

    it('displays hour label in HH:00 format', () => {
      render(<HourRow hour={18} />)
      expect(screen.getByText('18:00')).toBeInTheDocument()
    })

    it('displays hour 0 as 0:00', () => {
      render(<HourRow hour={0} />)
      expect(screen.getByText('0:00')).toBeInTheDocument()
    })

    it('displays hour 23 as 23:00', () => {
      render(<HourRow hour={23} />)
      expect(screen.getByText('23:00')).toBeInTheDocument()
    })

    it('renders ExecutionChip for each execution', () => {
      render(<HourRow hour={18} executions={hourExecutions} />)
      expect(screen.getByTestId('execution-routine-1-1800')).toBeInTheDocument()
      expect(screen.getByTestId('execution-routine-2-1815')).toBeInTheDocument()
    })

    it('shows "no executions" for empty hours', () => {
      render(<HourRow hour={18} executions={[]} />)
      expect(screen.getByText('no executions')).toBeInTheDocument()
    })

    it('shows "no executions" when executions prop is undefined', () => {
      render(<HourRow hour={18} />)
      expect(screen.getByText('no executions')).toBeInTheDocument()
    })
  })

  describe('Conflict Highlighting', () => {
    it('applies red background for error conflict', () => {
      render(<HourRow hour={19} executions={hourExecutions} conflict={mockErrorConflict} />)
      const row = screen.getByTestId('hour-row-19')
      expect(row).toHaveClass('bg-red-950/20')
    })

    it('applies yellow background for warning conflict', () => {
      render(<HourRow hour={21} executions={hourExecutions} conflict={mockWarningConflict} />)
      const row = screen.getByTestId('hour-row-21')
      expect(row).toHaveClass('bg-yellow-950/20')
    })

    it('changes hour label color for error conflict', () => {
      render(<HourRow hour={19} executions={hourExecutions} conflict={mockErrorConflict} />)
      const label = screen.getByText('19:00')
      expect(label).toHaveClass('text-red-400')
    })

    it('changes hour label color for warning conflict', () => {
      render(<HourRow hour={21} executions={hourExecutions} conflict={mockWarningConflict} />)
      const label = screen.getByText('21:00')
      expect(label).toHaveClass('text-yellow-400')
    })

    it('displays inline conflict message', () => {
      render(<HourRow hour={19} executions={hourExecutions} conflict={mockErrorConflict} />)
      expect(screen.getByText('camera busy')).toBeInTheDocument()
    })

    it('has conflict data-testid', () => {
      render(<HourRow hour={19} executions={hourExecutions} conflict={mockErrorConflict} />)
      expect(screen.getByTestId('conflict-c1')).toBeInTheDocument()
    })

    it('uses hour as fallback for conflict testid', () => {
      const conflictNoId = { severity: 'error', message: 'test' }
      render(<HourRow hour={19} executions={hourExecutions} conflict={conflictNoId} />)
      expect(screen.getByTestId('conflict-19')).toBeInTheDocument()
    })
  })

  describe('Execution Conflict Highlighting', () => {
    it('passes conflict severity to ExecutionChip', () => {
      const executionConflicts = {
        'routine-1': { severity: 'error' },
      }
      render(
        <HourRow
          hour={18}
          executions={hourExecutions}
          executionConflicts={executionConflicts}
        />
      )
      // The chip should have the ring class from conflict
      const chip = screen.getByTestId('execution-routine-1-1800')
      expect(chip).toHaveClass('ring-1')
      expect(chip).toHaveClass('ring-red-400')
    })

    it('does not add conflict styling to unaffected chips', () => {
      const executionConflicts = {
        'routine-1': { severity: 'error' },
      }
      render(
        <HourRow
          hour={18}
          executions={hourExecutions}
          executionConflicts={executionConflicts}
        />
      )
      const chip = screen.getByTestId('execution-routine-2-1815')
      expect(chip).not.toHaveClass('ring-1')
    })
  })

  describe('Interaction', () => {
    it('calls onExecutionClick with execution when chip is clicked', () => {
      const handleClick = vi.fn()
      render(
        <HourRow
          hour={18}
          executions={hourExecutions}
          onExecutionClick={handleClick}
        />
      )
      fireEvent.click(screen.getByTestId('execution-routine-1-1800'))
      expect(handleClick).toHaveBeenCalledTimes(1)
      expect(handleClick).toHaveBeenCalledWith(hourExecutions[0])
    })

    it('does not throw when onExecutionClick is not provided', () => {
      render(<HourRow hour={18} executions={hourExecutions} />)
      expect(() => {
        fireEvent.click(screen.getByTestId('execution-routine-1-1800'))
      }).not.toThrow()
    })
  })

  describe('Styling', () => {
    it('has correct base row styling', () => {
      render(<HourRow hour={18} />)
      const row = screen.getByTestId('hour-row-18')
      expect(row).toHaveClass('flex')
      expect(row).toHaveClass('p-3')
    })

    it('has fixed width for hour label', () => {
      render(<HourRow hour={18} />)
      const label = screen.getByText('18:00')
      expect(label).toHaveClass('w-12')
    })

    it('has default gray color for normal hour label', () => {
      render(<HourRow hour={18} />)
      const label = screen.getByText('18:00')
      expect(label).toHaveClass('text-gray-600')
    })
  })
})

/**
 * Tests for HourRow component (Issue #326)
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import HourRow from '../HourRow'

describe('HourRow', () => {
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
  ]

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
      render(<HourRow hour={18} executions={mockExecutions} />)
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
    const errorConflict = {
      id: 'c1',
      severity: 'error',
      message: 'camera busy',
      conflict_type: 'time_overlap',
    }

    const warningConflict = {
      id: 'c2',
      severity: 'warning',
      message: 'unexpected',
      conflict_type: 'gpio_state_conflict',
    }

    it('applies red background for error conflict', () => {
      render(<HourRow hour={19} executions={mockExecutions} conflict={errorConflict} />)
      const row = screen.getByTestId('hour-row-19')
      expect(row).toHaveClass('bg-red-950/20')
    })

    it('applies yellow background for warning conflict', () => {
      render(<HourRow hour={21} executions={mockExecutions} conflict={warningConflict} />)
      const row = screen.getByTestId('hour-row-21')
      expect(row).toHaveClass('bg-yellow-950/20')
    })

    it('changes hour label color for error conflict', () => {
      render(<HourRow hour={19} executions={mockExecutions} conflict={errorConflict} />)
      const label = screen.getByText('19:00')
      expect(label).toHaveClass('text-red-400')
    })

    it('changes hour label color for warning conflict', () => {
      render(<HourRow hour={21} executions={mockExecutions} conflict={warningConflict} />)
      const label = screen.getByText('21:00')
      expect(label).toHaveClass('text-yellow-400')
    })

    it('displays inline conflict message', () => {
      render(<HourRow hour={19} executions={mockExecutions} conflict={errorConflict} />)
      expect(screen.getByText('camera busy')).toBeInTheDocument()
    })

    it('has conflict data-testid', () => {
      render(<HourRow hour={19} executions={mockExecutions} conflict={errorConflict} />)
      expect(screen.getByTestId('conflict-c1')).toBeInTheDocument()
    })

    it('uses hour as fallback for conflict testid', () => {
      const conflictNoId = { severity: 'error', message: 'test' }
      render(<HourRow hour={19} executions={mockExecutions} conflict={conflictNoId} />)
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
          executions={mockExecutions}
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
          executions={mockExecutions}
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
          executions={mockExecutions}
          onExecutionClick={handleClick}
        />
      )
      fireEvent.click(screen.getByTestId('execution-routine-1-1800'))
      expect(handleClick).toHaveBeenCalledTimes(1)
      expect(handleClick).toHaveBeenCalledWith(mockExecutions[0])
    })

    it('does not throw when onExecutionClick is not provided', () => {
      render(<HourRow hour={18} executions={mockExecutions} />)
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

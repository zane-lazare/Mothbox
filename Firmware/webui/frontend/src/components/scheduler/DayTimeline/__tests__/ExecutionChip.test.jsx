/**
 * Tests for ExecutionChip component (Issue #326)
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ExecutionChip from '../ExecutionChip'

describe('ExecutionChip', () => {
  const mockExecution = {
    pattern_id: 'routine-1',
    pattern_name: 'Photo Capture',
    start_time: '2025-12-17T18:30:00Z',
    actions: [
      {
        time: '2025-12-17T18:30:00Z',
        action_name: 'Take Photo',
        action_type: 'camera',
        offset_minutes: 0,
      },
    ],
  }

  describe('Rendering', () => {
    it('renders with correct data-testid', () => {
      render(<ExecutionChip execution={mockExecution} />)
      expect(screen.getByTestId('execution-routine-1-1830')).toBeInTheDocument()
    })

    it('displays time and action name', () => {
      render(<ExecutionChip execution={mockExecution} />)
      const chip = screen.getByRole('button')
      expect(chip).toHaveTextContent('18:30')
      expect(chip).toHaveTextContent('Take Photo')
    })

    it('displays pattern name when no actions', () => {
      const execution = {
        pattern_id: 'routine-1',
        pattern_name: 'Photo Capture',
        start_time: '2025-12-17T18:30:00Z',
      }
      render(<ExecutionChip execution={execution} />)
      const chip = screen.getByRole('button')
      expect(chip).toHaveTextContent('18:30')
      expect(chip).toHaveTextContent('Photo Capture')
    })

    it('has correct aria-label', () => {
      render(<ExecutionChip execution={mockExecution} />)
      const chip = screen.getByRole('button')
      expect(chip).toHaveAttribute('aria-label', 'Photo Capture at 18:30')
    })

    it('has correct title attribute', () => {
      render(<ExecutionChip execution={mockExecution} />)
      const chip = screen.getByRole('button')
      expect(chip).toHaveAttribute('title', 'Photo Capture at 18:30')
    })
  })

  describe('Action Type Colors', () => {
    it('applies camera colors for camera type', () => {
      render(<ExecutionChip execution={mockExecution} />)
      const chip = screen.getByRole('button')
      expect(chip).toHaveClass('bg-blue-500/20')
      expect(chip).toHaveClass('text-blue-400')
    })

    it('applies gpio colors for gpio type', () => {
      const gpioExecution = {
        ...mockExecution,
        actions: [
          {
            action_name: 'Attract On',
            action_type: 'gpio',
          },
        ],
      }
      render(<ExecutionChip execution={gpioExecution} />)
      const chip = screen.getByRole('button')
      expect(chip).toHaveClass('bg-orange-500/20')
      expect(chip).toHaveClass('text-orange-400')
    })

    it('applies hdr colors for HDR action names', () => {
      const hdrExecution = {
        ...mockExecution,
        actions: [
          {
            action_name: 'HDR Bracket',
            action_type: 'camera',
          },
        ],
      }
      render(<ExecutionChip execution={hdrExecution} />)
      const chip = screen.getByRole('button')
      expect(chip).toHaveClass('bg-purple-500/20')
      expect(chip).toHaveClass('text-purple-400')
    })
  })

  describe('Conflict Highlighting', () => {
    it('applies red ring for error conflict', () => {
      render(<ExecutionChip execution={mockExecution} conflictSeverity="error" />)
      const chip = screen.getByRole('button')
      expect(chip).toHaveClass('ring-1')
      expect(chip).toHaveClass('ring-red-400')
    })

    it('applies yellow ring for warning conflict', () => {
      render(<ExecutionChip execution={mockExecution} conflictSeverity="warning" />)
      const chip = screen.getByRole('button')
      expect(chip).toHaveClass('ring-1')
      expect(chip).toHaveClass('ring-yellow-400')
    })

    it('has no ring when no conflict', () => {
      render(<ExecutionChip execution={mockExecution} />)
      const chip = screen.getByRole('button')
      expect(chip).not.toHaveClass('ring-1')
    })

    it('includes conflict in aria-label', () => {
      render(<ExecutionChip execution={mockExecution} conflictSeverity="error" />)
      const chip = screen.getByRole('button')
      expect(chip).toHaveAttribute(
        'aria-label',
        'Photo Capture at 18:30 - error conflict'
      )
    })
  })

  describe('Interaction', () => {
    it('calls onClick when clicked', () => {
      const handleClick = vi.fn()
      render(<ExecutionChip execution={mockExecution} onClick={handleClick} />)
      fireEvent.click(screen.getByRole('button'))
      expect(handleClick).toHaveBeenCalledTimes(1)
    })

    it('calls onClick on Enter key', () => {
      const handleClick = vi.fn()
      render(<ExecutionChip execution={mockExecution} onClick={handleClick} />)
      fireEvent.keyDown(screen.getByRole('button'), { key: 'Enter' })
      expect(handleClick).toHaveBeenCalledTimes(1)
    })

    it('calls onClick on Space key', () => {
      const handleClick = vi.fn()
      render(<ExecutionChip execution={mockExecution} onClick={handleClick} />)
      fireEvent.keyDown(screen.getByRole('button'), { key: ' ' })
      expect(handleClick).toHaveBeenCalledTimes(1)
    })

    it('does not throw when onClick is not provided', () => {
      render(<ExecutionChip execution={mockExecution} />)
      expect(() => {
        fireEvent.click(screen.getByRole('button'))
      }).not.toThrow()
    })

    it('has cursor-pointer when onClick is provided', () => {
      const handleClick = vi.fn()
      render(<ExecutionChip execution={mockExecution} onClick={handleClick} />)
      const chip = screen.getByRole('button')
      expect(chip).toHaveClass('cursor-pointer')
    })
  })

  describe('Accessibility', () => {
    it('is focusable', () => {
      render(<ExecutionChip execution={mockExecution} />)
      const chip = screen.getByRole('button')
      chip.focus()
      expect(chip).toHaveFocus()
    })

    it('has focus ring styles', () => {
      render(<ExecutionChip execution={mockExecution} />)
      const chip = screen.getByRole('button')
      expect(chip).toHaveClass('focus:outline-none')
      expect(chip).toHaveClass('focus:ring-2')
    })
  })
})

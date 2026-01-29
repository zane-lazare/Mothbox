import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ExecutionMarker from '../ExecutionMarker'

describe('ExecutionMarker', () => {
  const mockExecution = {
    pattern_id: 'test-pattern-1',
    pattern_name: 'Night Photography Session',
    start_time: '2025-12-17T20:30:00Z',
    end_time: '2025-12-17T21:30:00Z',
    trigger_info: 'Solar: sunset',
    actions: [
      { action_type: 'camera', action_name: 'capture', offset_minutes: 0 },
      { action_type: 'gpio', action_name: 'flash_on', offset_minutes: 5 },
    ],
  }

  const mockOnClick = vi.fn()

  beforeEach(() => {
    mockOnClick.mockClear()
  })

  describe('Rendering Tests', () => {
    it('renders as a small colored dot (no visible text)', () => {
      const { container } = render(
        <ExecutionMarker execution={mockExecution} onClick={mockOnClick} />
      )
      const button = container.querySelector('button')
      // Should be a small dot with no text content
      expect(button).toBeEmptyDOMElement()
      expect(button).toHaveClass('w-1.5')
      expect(button).toHaveClass('h-1.5')
      expect(button).toHaveClass('rounded-full')
    })

    it('has pattern name in title attribute', () => {
      render(<ExecutionMarker execution={mockExecution} onClick={mockOnClick} />)
      const button = screen.getByRole('button')
      expect(button.getAttribute('title')).toContain('Night Photography Session')
    })

    it('has time in title attribute', () => {
      render(<ExecutionMarker execution={mockExecution} onClick={mockOnClick} />)
      const button = screen.getByRole('button')
      // formatTime should convert to local time format
      expect(button.getAttribute('title')).toMatch(/\d{1,2}:\d{2}/)
    })

    it('applies camera color (blue) for camera action type', () => {
      const { container } = render(
        <ExecutionMarker execution={mockExecution} onClick={mockOnClick} />
      )
      const button = container.querySelector('button')
      expect(button).toHaveClass('bg-blue-400')
    })

    it('applies gpio color (orange) for gpio action type', () => {
      const gpioExecution = {
        ...mockExecution,
        actions: [{ action_type: 'gpio', action_name: 'attract_on' }],
      }
      const { container } = render(
        <ExecutionMarker execution={gpioExecution} onClick={mockOnClick} />
      )
      const button = container.querySelector('button')
      expect(button).toHaveClass('bg-orange-400')
    })

    it('applies default color when no actions', () => {
      const noActionsExecution = {
        ...mockExecution,
        actions: undefined,
      }
      const { container } = render(
        <ExecutionMarker execution={noActionsExecution} onClick={mockOnClick} />
      )
      const button = container.querySelector('button')
      // Default to gray when no actions
      expect(button).toHaveClass('bg-gray-400')
    })
  })

  describe('Interaction Tests', () => {
    it('calls onClick when clicked', async () => {
      const user = userEvent.setup()
      render(<ExecutionMarker execution={mockExecution} onClick={mockOnClick} />)

      const button = screen.getByRole('button')
      await user.click(button)

      expect(mockOnClick).toHaveBeenCalledTimes(1)
    })

    it('calls onClick when Enter key pressed', async () => {
      const user = userEvent.setup()
      render(<ExecutionMarker execution={mockExecution} onClick={mockOnClick} />)

      const button = screen.getByRole('button')
      button.focus()
      await user.keyboard('{Enter}')

      expect(mockOnClick).toHaveBeenCalledTimes(1)
    })

    it('calls onClick when Space key pressed', async () => {
      const user = userEvent.setup()
      render(<ExecutionMarker execution={mockExecution} onClick={mockOnClick} />)

      const button = screen.getByRole('button')
      button.focus()
      await user.keyboard(' ')

      expect(mockOnClick).toHaveBeenCalledTimes(1)
    })

    it('is focusable', () => {
      render(<ExecutionMarker execution={mockExecution} onClick={mockOnClick} />)
      const button = screen.getByRole('button')
      button.focus()
      expect(button).toHaveFocus()
    })
  })

  describe('Visual State Tests', () => {
    it('has hover state classes', () => {
      const { container } = render(
        <ExecutionMarker execution={mockExecution} onClick={mockOnClick} />
      )
      const button = container.querySelector('button')
      expect(button).toHaveClass('hover:brightness-110')
    })

    it('has cursor-pointer class', () => {
      const { container } = render(
        <ExecutionMarker execution={mockExecution} onClick={mockOnClick} />
      )
      const button = container.querySelector('button')
      expect(button).toHaveClass('cursor-pointer')
    })

    it('has transition classes for smooth animations', () => {
      const { container } = render(
        <ExecutionMarker execution={mockExecution} onClick={mockOnClick} />
      )
      const button = container.querySelector('button')
      expect(button).toHaveClass('transition-all')
    })
  })

  describe('Accessibility Tests', () => {
    it('has accessible label with pattern name and time', () => {
      render(<ExecutionMarker execution={mockExecution} onClick={mockOnClick} />)
      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('aria-label')
      expect(button.getAttribute('aria-label')).toContain('Night Photography Session')
    })

    it('has title attribute for tooltip', () => {
      render(<ExecutionMarker execution={mockExecution} onClick={mockOnClick} />)
      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('title')
      expect(button.getAttribute('title')).toContain('Night Photography Session')
    })

    it('has focus ring classes', () => {
      const { container } = render(
        <ExecutionMarker execution={mockExecution} onClick={mockOnClick} />
      )
      const button = container.querySelector('button')
      expect(button).toHaveClass('focus:outline-none')
      expect(button).toHaveClass('focus:ring-2')
    })

    it('is a button element', () => {
      render(<ExecutionMarker execution={mockExecution} onClick={mockOnClick} />)
      const button = screen.getByRole('button')
      expect(button.tagName).toBe('BUTTON')
      expect(button).toHaveAttribute('type', 'button')
    })
  })

  describe('Conflict Highlighting (Issue #229)', () => {
    it('shows red ring for error severity conflict', () => {
      const { container } = render(
        <ExecutionMarker
          execution={mockExecution}
          onClick={mockOnClick}
          conflictSeverity="error"
        />
      )
      const button = container.querySelector('button')
      expect(button.className).toMatch(/ring-red/)
    })

    it('shows amber ring for warning severity conflict', () => {
      const { container } = render(
        <ExecutionMarker
          execution={mockExecution}
          onClick={mockOnClick}
          conflictSeverity="warning"
        />
      )
      const button = container.querySelector('button')
      expect(button.className).toMatch(/ring-amber/)
    })

    it('shows no conflict ring when conflictSeverity is null', () => {
      const { container } = render(
        <ExecutionMarker
          execution={mockExecution}
          onClick={mockOnClick}
          conflictSeverity={null}
        />
      )
      const button = container.querySelector('button')
      // Should not have conflict ring classes (ring-red or ring-amber)
      expect(button.className).not.toMatch(/ring-red/)
      expect(button.className).not.toMatch(/ring-amber/)
    })

    it('includes conflict message in title when provided', () => {
      render(
        <ExecutionMarker
          execution={mockExecution}
          onClick={mockOnClick}
          conflictSeverity="error"
          conflictMessage="Camera resource conflict"
        />
      )
      const button = screen.getByRole('button')
      expect(button.getAttribute('title')).toContain('Camera resource conflict')
    })

    it('includes conflict message in aria-label when provided', () => {
      render(
        <ExecutionMarker
          execution={mockExecution}
          onClick={mockOnClick}
          conflictSeverity="error"
          conflictMessage="Camera resource conflict"
        />
      )
      const button = screen.getByRole('button')
      expect(button.getAttribute('aria-label')).toContain('conflict')
    })

    it('has dark mode classes for conflict ring', () => {
      const { container } = render(
        <ExecutionMarker
          execution={mockExecution}
          onClick={mockOnClick}
          conflictSeverity="error"
        />
      )
      const button = container.querySelector('button')
      expect(button.className).toMatch(/dark:ring-red/)
    })
  })

  describe('Edge Cases', () => {
    it('handles missing optional fields gracefully', () => {
      const minimalExecution = {
        pattern_id: 'minimal',
        pattern_name: 'Minimal',
        start_time: '2025-12-17T12:00:00Z',
      }

      const { container } = render(
        <ExecutionMarker execution={minimalExecution} onClick={mockOnClick} />
      )
      const button = container.querySelector('button')
      expect(button).toHaveClass('w-1.5')
      expect(button).toHaveClass('h-1.5')
      expect(button).toHaveClass('rounded-full')
    })

    it('handles very short pattern names', () => {
      const shortExecution = {
        ...mockExecution,
        pattern_name: 'A',
      }

      render(<ExecutionMarker execution={shortExecution} onClick={mockOnClick} />)
      const button = screen.getByRole('button')
      expect(button.getAttribute('title')).toContain('A')
    })

    it('handles pattern names with special characters', () => {
      const specialExecution = {
        ...mockExecution,
        pattern_name: 'Test & Debug [2024]',
      }

      render(<ExecutionMarker execution={specialExecution} onClick={mockOnClick} />)
      const button = screen.getByRole('button')
      expect(button.getAttribute('title')).toContain('Test & Debug [2024]')
    })
  })
})

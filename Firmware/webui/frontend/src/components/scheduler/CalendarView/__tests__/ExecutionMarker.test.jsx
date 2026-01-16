import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ExecutionMarker from '../ExecutionMarker'

// Mock the calendarUtils module
vi.mock('../calendarUtils', async () => {
  const actual = await vi.importActual('../calendarUtils')
  return {
    ...actual,
    getPatternColor: vi.fn((patternId) => {
      // Return consistent colors for testing
      const colors = ['bg-blue-500', 'bg-green-500', 'bg-purple-500']
      let hash = 0
      for (let i = 0; i < patternId.length; i++) {
        hash = ((hash << 5) - hash) + patternId.charCodeAt(i)
        hash = hash & hash
      }
      return colors[Math.abs(hash) % colors.length]
    }),
  }
})

describe('ExecutionMarker', () => {
  const mockExecution = {
    pattern_id: 'test-pattern-1',
    pattern_name: 'Night Photography Session',
    start_time: '2025-12-17T20:30:00Z',
    end_time: '2025-12-17T21:30:00Z',
    trigger_info: 'Solar: sunset',
    actions: [
      { action_type: 'camera.capture', offset_minutes: 0 },
      { action_type: 'gpio.on', offset_minutes: 5 },
    ],
  }

  const mockOnClick = vi.fn()

  beforeEach(() => {
    mockOnClick.mockClear()
  })

  describe('Rendering Tests', () => {
    it('displays pattern name', () => {
      render(<ExecutionMarker execution={mockExecution} onClick={mockOnClick} />)
      expect(screen.getByText('Night Photography Session')).toBeInTheDocument()
    })

    it('displays execution time when not compact', () => {
      render(<ExecutionMarker execution={mockExecution} onClick={mockOnClick} />)
      // formatTime should convert to local time format
      const timeElement = screen.getByText(/\d{1,2}:\d{2}/)
      expect(timeElement).toBeInTheDocument()
    })

    it('displays time in compact mode (smaller size)', () => {
      render(<ExecutionMarker execution={mockExecution} onClick={mockOnClick} compact />)
      // In compact mode, time is displayed with smaller text
      const timeElement = screen.getByText(/\d{1,2}:\d{2}/)
      expect(timeElement).toBeInTheDocument()
      expect(timeElement).toHaveClass('text-[10px]')
    })

    it('assigns consistent color based on pattern_id', () => {
      const { container } = render(<ExecutionMarker execution={mockExecution} onClick={mockOnClick} />)
      const button = container.querySelector('button')

      // Should have a bg-color class
      expect(button.className).toMatch(/bg-(blue|green|purple|orange|pink|cyan)-500/)
    })

    it('assigns same color for same pattern_id', () => {
      const { container: container1 } = render(
        <ExecutionMarker execution={mockExecution} onClick={mockOnClick} />
      )
      const { container: container2 } = render(
        <ExecutionMarker execution={mockExecution} onClick={mockOnClick} />
      )

      const button1 = container1.querySelector('button')
      const button2 = container2.querySelector('button')

      // Extract color classes
      const colorClass1 = button1.className.match(/bg-\w+-\d+/)[0]
      const colorClass2 = button2.className.match(/bg-\w+-\d+/)[0]

      expect(colorClass1).toBe(colorClass2)
    })

    it('truncates long pattern names', () => {
      const longExecution = {
        ...mockExecution,
        pattern_name: 'This is an extremely long pattern name that should definitely be truncated',
      }

      render(<ExecutionMarker execution={longExecution} onClick={mockOnClick} />)
      const nameElement = screen.getByText(/This is an extremely/)
      expect(nameElement).toBeInTheDocument()
    })

    it('uses CSS truncation in compact mode', () => {
      const longExecution = {
        ...mockExecution,
        pattern_name: 'Very Long Pattern Name',
      }

      render(<ExecutionMarker execution={longExecution} onClick={mockOnClick} compact />)
      // In compact mode, CSS handles truncation via max-width and truncate class
      const text = screen.getByText('Very Long Pattern Name')
      expect(text).toHaveClass('truncate')
      expect(text).toHaveClass('max-w-[60px]')
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
      const { container } = render(<ExecutionMarker execution={mockExecution} onClick={mockOnClick} />)
      const button = container.querySelector('button')
      expect(button).toHaveClass('hover:brightness-110')
      expect(button).toHaveClass('hover:scale-105')
    })

    it('has cursor-pointer class', () => {
      const { container } = render(<ExecutionMarker execution={mockExecution} onClick={mockOnClick} />)
      const button = container.querySelector('button')
      expect(button).toHaveClass('cursor-pointer')
    })

    it('has transition classes for smooth animations', () => {
      const { container } = render(<ExecutionMarker execution={mockExecution} onClick={mockOnClick} />)
      const button = container.querySelector('button')
      expect(button).toHaveClass('transition-all')
    })

    it('has dark mode classes', () => {
      const { container } = render(<ExecutionMarker execution={mockExecution} onClick={mockOnClick} />)
      const button = container.querySelector('button')
      // Should have dark mode variant
      expect(button.className).toMatch(/dark:bg-\w+-\d+/)
    })

    it('has white text for contrast', () => {
      const { container } = render(<ExecutionMarker execution={mockExecution} onClick={mockOnClick} />)
      const button = container.querySelector('button')
      expect(button).toHaveClass('text-white')
    })

    it('has rounded-full class for pill shape', () => {
      const { container } = render(<ExecutionMarker execution={mockExecution} onClick={mockOnClick} />)
      const button = container.querySelector('button')
      expect(button).toHaveClass('rounded-full')
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
      const { container } = render(<ExecutionMarker execution={mockExecution} onClick={mockOnClick} />)
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

  describe('Compact Mode Tests', () => {
    it('applies compact-specific text sizing', () => {
      const { container } = render(<ExecutionMarker execution={mockExecution} onClick={mockOnClick} compact />)
      // Compact mode uses text-[10px] for both time and name
      const textElement = container.querySelector('.text-\\[10px\\]')
      expect(textElement).toBeInTheDocument()
    })

    it('applies full mode text sizing when not compact', () => {
      const { container } = render(<ExecutionMarker execution={mockExecution} onClick={mockOnClick} />)
      // Full mode uses text-sm for name and text-xs for time
      const textElement = container.querySelector('.text-sm')
      expect(textElement).toBeInTheDocument()
    })

    it('has different max-width in compact mode', () => {
      const { container: compactContainer } = render(
        <ExecutionMarker execution={mockExecution} onClick={mockOnClick} compact />
      )
      const { container: fullContainer } = render(
        <ExecutionMarker execution={mockExecution} onClick={mockOnClick} />
      )

      // Compact: max-w-[60px], Full: max-w-[180px]
      const compactText = compactContainer.querySelector('.max-w-\\[60px\\]')
      const fullText = fullContainer.querySelector('.max-w-\\[180px\\]')

      expect(compactText).toBeInTheDocument()
      expect(fullText).toBeInTheDocument()
    })
  })

  describe('Static Color Class Mapping', () => {
    it('uses static dark mode classes (Tailwind JIT compatible)', () => {
      const { container } = render(<ExecutionMarker execution={mockExecution} onClick={mockOnClick} />)
      const button = container.querySelector('button')
      // Should have one of the static dark mode classes from COLOR_CLASS_MAP
      const validDarkClasses = [
        'dark:bg-blue-600',
        'dark:bg-green-600',
        'dark:bg-purple-600',
        'dark:bg-orange-600',
        'dark:bg-pink-600',
        'dark:bg-cyan-600',
      ]
      const hasDarkClass = validDarkClasses.some((cls) => button.classList.contains(cls))
      expect(hasDarkClass).toBe(true)
    })

    it('uses static focus ring classes (Tailwind JIT compatible)', () => {
      const { container } = render(<ExecutionMarker execution={mockExecution} onClick={mockOnClick} />)
      const button = container.querySelector('button')
      // Should have one of the static focus ring classes from COLOR_CLASS_MAP
      const validRingClasses = [
        'focus:ring-blue-400',
        'focus:ring-green-400',
        'focus:ring-purple-400',
        'focus:ring-orange-400',
        'focus:ring-pink-400',
        'focus:ring-cyan-400',
      ]
      const hasRingClass = validRingClasses.some((cls) => button.classList.contains(cls))
      expect(hasRingClass).toBe(true)
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

      render(<ExecutionMarker execution={minimalExecution} onClick={mockOnClick} />)
      expect(screen.getByText('Minimal')).toBeInTheDocument()
    })

    it('handles very short pattern names', () => {
      const shortExecution = {
        ...mockExecution,
        pattern_name: 'A',
      }

      render(<ExecutionMarker execution={shortExecution} onClick={mockOnClick} />)
      expect(screen.getByText('A')).toBeInTheDocument()
    })

    it('handles pattern names with special characters', () => {
      const specialExecution = {
        ...mockExecution,
        pattern_name: 'Test & Debug [2024]',
      }

      render(<ExecutionMarker execution={specialExecution} onClick={mockOnClick} />)
      expect(screen.getByText('Test & Debug [2024]')).toBeInTheDocument()
    })
  })
})

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ExpertModeToggle from '../ExpertModeToggle'

describe('ExpertModeToggle', () => {
  let mockOnChange

  beforeEach(() => {
    mockOnChange = vi.fn()
  })

  describe('Rendering', () => {
    it('renders with visual mode selected by default', () => {
      render(<ExpertModeToggle mode="visual" onChange={mockOnChange} />)

      const visualButton = screen.getByLabelText('Switch to Visual mode')
      const expertButton = screen.getByLabelText('Switch to Expert mode')

      expect(visualButton).toBeInTheDocument()
      expect(expertButton).toBeInTheDocument()
      expect(visualButton).toHaveAttribute('aria-pressed', 'true')
      expect(expertButton).toHaveAttribute('aria-pressed', 'false')
    })

    it('toggles to expert mode on click', () => {
      render(<ExpertModeToggle mode="visual" onChange={mockOnChange} />)

      const expertButton = screen.getByLabelText('Switch to Expert mode')
      fireEvent.click(expertButton)

      expect(mockOnChange).toHaveBeenCalledWith('expert')
    })

    it('calls onChange with new mode value', () => {
      const { rerender } = render(<ExpertModeToggle mode="visual" onChange={mockOnChange} />)

      const expertButton = screen.getByLabelText('Switch to Expert mode')
      fireEvent.click(expertButton)

      expect(mockOnChange).toHaveBeenCalledWith('expert')

      // Test switching back to visual
      rerender(<ExpertModeToggle mode="expert" onChange={mockOnChange} />)

      const visualButton = screen.getByLabelText('Switch to Visual mode')
      fireEvent.click(visualButton)

      expect(mockOnChange).toHaveBeenCalledWith('visual')
    })

    it('displays correct labels', () => {
      render(<ExpertModeToggle mode="visual" onChange={mockOnChange} />)

      expect(screen.getByText('Visual')).toBeInTheDocument()
      expect(screen.getByText('Expert')).toBeInTheDocument()
    })

    it('applies active styling to selected mode', () => {
      const { rerender } = render(<ExpertModeToggle mode="visual" onChange={mockOnChange} />)

      const visualButton = screen.getByLabelText('Switch to Visual mode')
      const expertButton = screen.getByLabelText('Switch to Expert mode')

      // Visual mode selected
      expect(visualButton).toHaveClass('bg-blue-500', 'text-white')
      expect(expertButton).toHaveClass('bg-white', 'text-gray-700')

      // Expert mode selected
      rerender(<ExpertModeToggle mode="expert" onChange={mockOnChange} />)

      expect(expertButton).toHaveClass('bg-blue-500', 'text-white')
      expect(visualButton).toHaveClass('bg-white', 'text-gray-700')
    })
  })

  describe('Interaction', () => {
    it('switches mode when clicking non-selected button', () => {
      render(<ExpertModeToggle mode="visual" onChange={mockOnChange} />)

      const expertButton = screen.getByLabelText('Switch to Expert mode')
      fireEvent.click(expertButton)

      expect(mockOnChange).toHaveBeenCalledTimes(1)
      expect(mockOnChange).toHaveBeenCalledWith('expert')
    })

    it('allows clicking already selected button', () => {
      render(<ExpertModeToggle mode="visual" onChange={mockOnChange} />)

      const visualButton = screen.getByLabelText('Switch to Visual mode')
      fireEvent.click(visualButton)

      // Should still call onChange even if already selected
      expect(mockOnChange).toHaveBeenCalledWith('visual')
    })
  })

  describe('Styling', () => {
    it('applies rounded corners to first button', () => {
      render(<ExpertModeToggle mode="visual" onChange={mockOnChange} />)

      const visualButton = screen.getByLabelText('Switch to Visual mode')
      expect(visualButton).toHaveClass('rounded-l-md')
    })

    it('applies rounded corners to last button', () => {
      render(<ExpertModeToggle mode="visual" onChange={mockOnChange} />)

      const expertButton = screen.getByLabelText('Switch to Expert mode')
      expect(expertButton).toHaveClass('rounded-r-md')
    })

    it('applies dark mode classes', () => {
      render(<ExpertModeToggle mode="visual" onChange={mockOnChange} />)

      const expertButton = screen.getByLabelText('Switch to Expert mode')
      expect(expertButton).toHaveClass('dark:bg-gray-800', 'dark:text-gray-300')
    })
  })

  describe('Accessibility', () => {
    it('has role group with aria-label', () => {
      render(<ExpertModeToggle mode="visual" onChange={mockOnChange} />)

      const group = screen.getByRole('group', { name: 'Mode selector' })
      expect(group).toBeInTheDocument()
    })

    it('sets aria-pressed correctly for selected mode', () => {
      render(<ExpertModeToggle mode="expert" onChange={mockOnChange} />)

      const visualButton = screen.getByLabelText('Switch to Visual mode')
      const expertButton = screen.getByLabelText('Switch to Expert mode')

      expect(visualButton).toHaveAttribute('aria-pressed', 'false')
      expect(expertButton).toHaveAttribute('aria-pressed', 'true')
    })

    it('has descriptive aria-labels', () => {
      render(<ExpertModeToggle mode="visual" onChange={mockOnChange} />)

      expect(screen.getByLabelText('Switch to Visual mode')).toBeInTheDocument()
      expect(screen.getByLabelText('Switch to Expert mode')).toBeInTheDocument()
    })
  })

  describe('Focus Management', () => {
    it('applies focus ring styles', () => {
      render(<ExpertModeToggle mode="visual" onChange={mockOnChange} />)

      const visualButton = screen.getByLabelText('Switch to Visual mode')
      expect(visualButton).toHaveClass('focus:ring-2', 'focus:ring-blue-500', 'focus:outline-none')
    })
  })
})

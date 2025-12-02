import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TagChip from '../TagChip'

describe('TagChip', () => {
  // Rendering tests
  describe('Rendering', () => {
    it('renders tag name', () => {
      render(<TagChip tag="moth" />)
      expect(screen.getByText('moth')).toBeInTheDocument()
    })

    it('renders count when provided', () => {
      render(<TagChip tag="nocturnal" count={5} />)
      expect(screen.getByText('nocturnal')).toBeInTheDocument()
      expect(screen.getByText('(5)')).toBeInTheDocument()
    })

    it('does not render count when not provided', () => {
      const { container } = render(<TagChip tag="moth" />)
      expect(container.textContent).not.toContain('(')
      expect(container.textContent).not.toContain(')')
    })

    it('renders with custom className', () => {
      const { container } = render(<TagChip tag="moth" className="custom-class" />)
      expect(container.firstChild).toHaveClass('custom-class')
    })
  })

  // Interaction tests
  describe('Interactions', () => {
    it('calls onClick when clicked', async () => {
      const user = userEvent.setup()
      const handleClick = vi.fn()
      render(<TagChip tag="moth" onClick={handleClick} />)

      await user.click(screen.getByRole('button', { name: /Tag: moth/i }))
      expect(handleClick).toHaveBeenCalledTimes(1)
    })

    it('calls onRemove when remove button clicked', async () => {
      const user = userEvent.setup()
      const handleRemove = vi.fn()
      render(<TagChip tag="moth" removable onRemove={handleRemove} />)

      await user.click(screen.getByRole('button', { name: /Remove tag moth/i }))
      expect(handleRemove).toHaveBeenCalledTimes(1)
    })

    it('does not call onClick when remove button clicked', async () => {
      const user = userEvent.setup()
      const handleClick = vi.fn()
      const handleRemove = vi.fn()
      render(<TagChip tag="moth" removable onClick={handleClick} onRemove={handleRemove} />)

      await user.click(screen.getByRole('button', { name: /Remove tag moth/i }))
      expect(handleRemove).toHaveBeenCalledTimes(1)
      expect(handleClick).not.toHaveBeenCalled()
    })

    it('shows remove button only when removable is true', () => {
      const { rerender } = render(<TagChip tag="moth" removable />)
      expect(screen.getByRole('button', { name: /Remove tag moth/i })).toBeInTheDocument()

      rerender(<TagChip tag="moth" removable={false} />)
      expect(screen.queryByRole('button', { name: /Remove tag moth/i })).not.toBeInTheDocument()
    })

    it('handles keyboard interaction on remove button', async () => {
      const user = userEvent.setup()
      const handleRemove = vi.fn()
      render(<TagChip tag="moth" removable onRemove={handleRemove} />)

      const removeButton = screen.getByRole('button', { name: /Remove tag moth/i })
      removeButton.focus()
      await user.keyboard('{Enter}')
      expect(handleRemove).toHaveBeenCalledTimes(1)
    })
  })

  // Visual states
  describe('Visual States', () => {
    it('applies selected styles when selected', () => {
      render(<TagChip tag="moth" selected />)
      const button = screen.getByRole('button', { name: /Tag: moth/i })
      expect(button).toHaveClass('bg-blue-500', 'text-white')
    })

    it('applies default styles when not selected', () => {
      render(<TagChip tag="moth" selected={false} />)
      const button = screen.getByRole('button', { name: /Tag: moth/i })
      expect(button).toHaveClass('bg-blue-100', 'text-blue-800')
    })

    it('applies correct size classes for sm variant', () => {
      render(<TagChip tag="moth" size="sm" />)
      const button = screen.getByRole('button', { name: /Tag: moth/i })
      expect(button).toHaveClass('text-xs', 'px-2', 'py-0.5')
    })

    it('applies correct size classes for md variant', () => {
      render(<TagChip tag="moth" size="md" />)
      const button = screen.getByRole('button', { name: /Tag: moth/i })
      expect(button).toHaveClass('text-sm', 'px-3', 'py-1')
    })

    it('defaults to sm size when not specified', () => {
      render(<TagChip tag="moth" />)
      const button = screen.getByRole('button', { name: /Tag: moth/i })
      expect(button).toHaveClass('text-xs', 'px-2', 'py-0.5')
    })
  })

  // Accessibility
  describe('Accessibility', () => {
    it('has correct aria-pressed when selected', () => {
      const { rerender } = render(<TagChip tag="moth" selected />)
      expect(screen.getByRole('button', { name: /Tag: moth/i })).toHaveAttribute('aria-pressed', 'true')

      rerender(<TagChip tag="moth" selected={false} />)
      expect(screen.getByRole('button', { name: /Tag: moth/i })).toHaveAttribute('aria-pressed', 'false')
    })

    it('has accessible name for tag button', () => {
      render(<TagChip tag="moth" />)
      expect(screen.getByRole('button', { name: 'Tag: moth' })).toBeInTheDocument()
    })

    it('has accessible name for tag button with count', () => {
      render(<TagChip tag="moth" count={5} />)
      expect(screen.getByRole('button', { name: 'Tag: moth, used 5 times' })).toBeInTheDocument()
    })

    it('has accessible name for remove button', () => {
      render(<TagChip tag="moth" removable />)
      expect(screen.getByRole('button', { name: 'Remove tag moth' })).toBeInTheDocument()
    })

    it('is keyboard accessible', async () => {
      const user = userEvent.setup()
      const handleClick = vi.fn()
      render(<TagChip tag="moth" onClick={handleClick} />)

      const button = screen.getByRole('button', { name: /Tag: moth/i })
      button.focus()
      await user.keyboard('{Enter}')
      expect(handleClick).toHaveBeenCalled()
    })
  })

  // Edge cases
  describe('Edge Cases', () => {
    it('handles tag with special characters', () => {
      render(<TagChip tag="moth & butterfly" />)
      expect(screen.getByText('moth & butterfly')).toBeInTheDocument()
    })

    it('handles zero count', () => {
      render(<TagChip tag="moth" count={0} />)
      expect(screen.getByText('(0)')).toBeInTheDocument()
    })

    it('handles undefined onClick gracefully', async () => {
      const user = userEvent.setup()
      render(<TagChip tag="moth" />)

      // Should not throw error
      const button = screen.getByRole('button', { name: /Tag: moth/i })
      await expect(user.click(button)).resolves.not.toThrow()
    })

    it('handles undefined onRemove gracefully', async () => {
      const user = userEvent.setup()
      render(<TagChip tag="moth" removable />)

      // Should not throw error
      const removeButton = screen.getByRole('button', { name: /Remove tag moth/i })
      await expect(user.click(removeButton)).resolves.not.toThrow()
    })
  })
})

import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import FilterErrorFallback from '../FilterErrorFallback'

describe('FilterErrorFallback', () => {
  describe('Rendering', () => {
    it('renders the error fallback UI', () => {
      const onRetry = vi.fn()
      render(<FilterErrorFallback onRetry={onRetry} />)

      expect(screen.getByText('Filter Error')).toBeInTheDocument()
      expect(screen.getByText('Unable to load filters')).toBeInTheDocument()
    })

    it('renders with complementary role', () => {
      const onRetry = vi.fn()
      render(<FilterErrorFallback onRetry={onRetry} />)

      expect(screen.getByRole('complementary')).toBeInTheDocument()
    })

    it('has correct aria-label', () => {
      const onRetry = vi.fn()
      render(<FilterErrorFallback onRetry={onRetry} />)

      expect(screen.getByLabelText('Filter error')).toBeInTheDocument()
    })

    it('renders the error icon', () => {
      const onRetry = vi.fn()
      const { container } = render(<FilterErrorFallback onRetry={onRetry} />)

      const svg = container.querySelector('svg')
      expect(svg).toBeInTheDocument()
      expect(svg).toHaveAttribute('aria-hidden', 'true')
    })

    it('renders the Try Again button', () => {
      const onRetry = vi.fn()
      render(<FilterErrorFallback onRetry={onRetry} />)

      expect(screen.getByRole('button', { name: 'Try Again' })).toBeInTheDocument()
    })
  })

  describe('Error Display', () => {
    it('displays error message when provided', () => {
      const onRetry = vi.fn()
      const error = new Error('Failed to fetch tags')
      render(<FilterErrorFallback error={error} onRetry={onRetry} />)

      expect(screen.getByText('Failed to fetch tags')).toBeInTheDocument()
    })

    it('displays default message when no error provided', () => {
      const onRetry = vi.fn()
      render(<FilterErrorFallback onRetry={onRetry} />)

      expect(screen.getByText('Unable to load filters')).toBeInTheDocument()
    })

    it('displays default message when error has no message', () => {
      const onRetry = vi.fn()
      const error = new Error()
      render(<FilterErrorFallback error={error} onRetry={onRetry} />)

      expect(screen.getByText('Unable to load filters')).toBeInTheDocument()
    })
  })

  describe('Retry Functionality', () => {
    it('calls onRetry when Try Again button is clicked', () => {
      const onRetry = vi.fn()
      render(<FilterErrorFallback onRetry={onRetry} />)

      const button = screen.getByRole('button', { name: 'Try Again' })
      fireEvent.click(button)

      expect(onRetry).toHaveBeenCalledTimes(1)
    })

    it('passes error object to handler when retrying', () => {
      const onRetry = vi.fn()
      const error = new Error('Test error')
      render(<FilterErrorFallback error={error} onRetry={onRetry} />)

      const button = screen.getByRole('button', { name: 'Try Again' })
      fireEvent.click(button)

      expect(onRetry).toHaveBeenCalledTimes(1)
    })
  })

  describe('Technical Details (Development Mode)', () => {
    it('shows technical details in development mode when error has stack', () => {
      // In vitest, import.meta.env.DEV is true by default
      const onRetry = vi.fn()
      const error = new Error('Test error')
      error.stack = 'Error: Test error\n    at TestComponent'
      render(<FilterErrorFallback error={error} onRetry={onRetry} />)

      expect(screen.getByText('Show technical details')).toBeInTheDocument()
    })

    it('can expand technical details', () => {
      const onRetry = vi.fn()
      const error = new Error('Test error')
      error.stack = 'Error: Test error\n    at TestComponent'
      render(<FilterErrorFallback error={error} onRetry={onRetry} />)

      const details = screen.getByText('Show technical details')
      fireEvent.click(details)

      expect(screen.getByText(/at TestComponent/)).toBeInTheDocument()
    })

    it('does not show technical details when error has no stack', () => {
      const onRetry = vi.fn()
      const error = new Error('Test error')
      delete error.stack
      render(<FilterErrorFallback error={error} onRetry={onRetry} />)

      expect(screen.queryByText('Show technical details')).not.toBeInTheDocument()
    })
  })

  describe('Styling', () => {
    it('applies correct positioning classes', () => {
      const onRetry = vi.fn()
      render(<FilterErrorFallback onRetry={onRetry} />)

      const aside = screen.getByRole('complementary')
      expect(aside).toHaveClass('fixed', 'z-40')
    })

    it('applies dark mode classes', () => {
      const onRetry = vi.fn()
      render(<FilterErrorFallback onRetry={onRetry} />)

      const aside = screen.getByRole('complementary')
      expect(aside).toHaveClass('dark:bg-gray-800')
    })

    it('applies correct width classes for desktop and tablet', () => {
      const onRetry = vi.fn()
      render(<FilterErrorFallback onRetry={onRetry} />)

      const aside = screen.getByRole('complementary')
      expect(aside).toHaveClass('lg:w-80', 'md:w-72')
    })

    it('applies button styling', () => {
      const onRetry = vi.fn()
      render(<FilterErrorFallback onRetry={onRetry} />)

      const button = screen.getByRole('button', { name: 'Try Again' })
      expect(button).toHaveClass('bg-blue-600', 'text-white', 'rounded-lg')
    })

    it('applies hover and focus styles to button', () => {
      const onRetry = vi.fn()
      render(<FilterErrorFallback onRetry={onRetry} />)

      const button = screen.getByRole('button', { name: 'Try Again' })
      expect(button).toHaveClass('hover:bg-blue-700', 'focus:outline-none', 'focus:ring-2')
    })
  })

  describe('Accessibility', () => {
    it('button is focusable', () => {
      const onRetry = vi.fn()
      render(<FilterErrorFallback onRetry={onRetry} />)

      const button = screen.getByRole('button', { name: 'Try Again' })
      button.focus()
      expect(document.activeElement).toBe(button)
    })

    it('activates button on Enter key', () => {
      const onRetry = vi.fn()
      render(<FilterErrorFallback onRetry={onRetry} />)

      const button = screen.getByRole('button', { name: 'Try Again' })
      fireEvent.keyDown(button, { key: 'Enter', code: 'Enter' })
      fireEvent.click(button)

      expect(onRetry).toHaveBeenCalled()
    })

    it('error icon is hidden from screen readers', () => {
      const onRetry = vi.fn()
      const { container } = render(<FilterErrorFallback onRetry={onRetry} />)

      const svg = container.querySelector('svg')
      expect(svg).toHaveAttribute('aria-hidden', 'true')
    })
  })
})

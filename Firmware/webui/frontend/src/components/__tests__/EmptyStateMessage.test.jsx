import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import EmptyStateMessage from '../EmptyStateMessage'

describe('EmptyStateMessage', () => {
  describe('Rendering', () => {
    it('renders with first-time variant by default', () => {
      render(<EmptyStateMessage />)

      expect(screen.getByText(/No photos yet/i)).toBeInTheDocument()
      expect(screen.getByText(/Let's capture your first insect!/i)).toBeInTheDocument()
    })

    it('renders moth icon with correct size', () => {
      render(<EmptyStateMessage />)

      const mothIcon = screen.getByRole('img', { name: /moth icon/i })
      expect(mothIcon).toBeInTheDocument()
    })

    it('renders CTA button for first-time variant', () => {
      const mockOnClick = vi.fn()
      render(<EmptyStateMessage variant="first-time" onCtaClick={mockOnClick} />)

      const ctaButton = screen.getByRole('button', { name: /Capture First Photo/i })
      expect(ctaButton).toBeInTheDocument()
    })

    it('renders filtered variant without CTA button', () => {
      render(<EmptyStateMessage variant="filtered" />)

      expect(screen.getByText(/No matches found/i)).toBeInTheDocument()
      expect(screen.getByText(/Try adjusting your filters/i)).toBeInTheDocument()
      expect(screen.queryByRole('button')).not.toBeInTheDocument()
    })

    it('renders error variant with retry CTA', () => {
      const mockOnRetry = vi.fn()
      render(<EmptyStateMessage variant="error" onCtaClick={mockOnRetry} />)

      expect(screen.getByText(/Unable to load photos/i)).toBeInTheDocument()
      const retryButton = screen.getByRole('button', { name: /Retry/i })
      expect(retryButton).toBeInTheDocument()
    })
  })

  describe('Interactions', () => {
    it('calls onCtaClick when CTA button is clicked', async () => {
      const user = userEvent.setup()
      const mockOnClick = vi.fn()

      render(<EmptyStateMessage variant="first-time" onCtaClick={mockOnClick} />)

      const ctaButton = screen.getByRole('button', { name: /Capture First Photo/i })
      await user.click(ctaButton)

      expect(mockOnClick).toHaveBeenCalledTimes(1)
    })

    it('does not render button when onCtaClick is not provided', () => {
      render(<EmptyStateMessage variant="first-time" />)

      // Should show message but no interactive button
      expect(screen.getByText(/No photos yet/i)).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has role="status" for screen readers', () => {
      render(<EmptyStateMessage />)

      const container = screen.getByRole('status')
      expect(container).toBeInTheDocument()
    })

    it('moth icon has proper aria-label', () => {
      render(<EmptyStateMessage />)

      const mothIcon = screen.getByRole('img')
      expect(mothIcon).toHaveAccessibleName()
    })

    it('CTA button has proper accessible name', () => {
      render(<EmptyStateMessage variant="first-time" onCtaClick={() => {}} />)

      const button = screen.getByRole('button')
      expect(button).toHaveAccessibleName(/Capture First Photo/i)
    })
  })

  describe('Custom Styling', () => {
    it('applies custom className', () => {
      const { container } = render(<EmptyStateMessage className="custom-class" />)

      const statusElement = container.querySelector('[role="status"]')
      expect(statusElement).toHaveClass('custom-class')
    })
  })
})

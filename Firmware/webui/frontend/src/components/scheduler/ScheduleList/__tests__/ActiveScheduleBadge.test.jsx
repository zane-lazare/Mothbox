/**
 * Tests for ActiveScheduleBadge component (Issue #266)
 *
 * ActiveScheduleBadge displays a small badge indicating that a schedule
 * is currently active. It renders nothing when not active.
 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ActiveScheduleBadge from '../ActiveScheduleBadge'

describe('ActiveScheduleBadge', () => {
  // ==========================================================================
  // Rendering Tests
  // ==========================================================================

  describe('Rendering', () => {
    it('renders nothing when isActive is false', () => {
      const { container } = render(<ActiveScheduleBadge isActive={false} />)
      expect(container).toBeEmptyDOMElement()
    })

    it('renders nothing when isActive is undefined', () => {
      const { container } = render(<ActiveScheduleBadge />)
      expect(container).toBeEmptyDOMElement()
    })

    it('renders badge when isActive is true', () => {
      render(<ActiveScheduleBadge isActive={true} />)
      expect(screen.getByText('Active')).toBeInTheDocument()
    })

    it('renders CheckCircleIcon when active', () => {
      render(<ActiveScheduleBadge isActive={true} />)
      // CheckCircleIcon renders as an SVG
      const badge = screen.getByText('Active').closest('span')
      const svg = badge.querySelector('svg')
      expect(svg).toBeInTheDocument()
    })
  })

  // ==========================================================================
  // Styling Tests
  // ==========================================================================

  describe('Styling', () => {
    it('applies green styling for active state', () => {
      render(<ActiveScheduleBadge isActive={true} />)
      const badge = screen.getByText('Active').closest('span')
      expect(badge).toHaveClass('bg-green-100')
      expect(badge).toHaveClass('text-green-700')
    })

    it('has pill/rounded styling', () => {
      render(<ActiveScheduleBadge isActive={true} />)
      const badge = screen.getByText('Active').closest('span')
      expect(badge).toHaveClass('rounded-full')
    })

    it('uses small text size', () => {
      render(<ActiveScheduleBadge isActive={true} />)
      const badge = screen.getByText('Active').closest('span')
      expect(badge).toHaveClass('text-xs')
    })

    it('applies dark mode classes', () => {
      render(<ActiveScheduleBadge isActive={true} />)
      const badge = screen.getByText('Active').closest('span')
      // Check for dark mode variants
      expect(badge.className).toContain('dark:')
    })
  })

  // ==========================================================================
  // Accessibility Tests
  // ==========================================================================

  describe('Accessibility', () => {
    it('has aria-label indicating active status', () => {
      render(<ActiveScheduleBadge isActive={true} />)
      const badge = screen.getByText('Active').closest('span')
      expect(badge).toHaveAttribute('aria-label', 'Schedule is active')
    })

    it('has role="status" for screen readers', () => {
      render(<ActiveScheduleBadge isActive={true} />)
      expect(screen.getByRole('status')).toBeInTheDocument()
    })
  })
})

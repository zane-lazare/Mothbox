import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import MetadataSkeleton from '../MetadataSkeleton'

describe('MetadataSkeleton', () => {
  describe('Rendering', () => {
    it('renders skeleton with pulse animation', () => {
      const { container } = render(<MetadataSkeleton />)

      // Should have animate-pulse class
      const skeleton = container.querySelector('.animate-pulse')
      expect(skeleton).toBeInTheDocument()
    })

    it('renders default number of rows (6)', () => {
      const { container } = render(<MetadataSkeleton />)

      // Count the number of skeleton rows
      const rows = container.querySelectorAll('[data-testid="skeleton-row"]')
      expect(rows).toHaveLength(6)
    })

    it('renders custom number of rows', () => {
      const { container } = render(<MetadataSkeleton rows={3} />)

      const rows = container.querySelectorAll('[data-testid="skeleton-row"]')
      expect(rows).toHaveLength(3)
    })

    it('renders custom number of rows (10)', () => {
      const { container } = render(<MetadataSkeleton rows={10} />)

      const rows = container.querySelectorAll('[data-testid="skeleton-row"]')
      expect(rows).toHaveLength(10)
    })

    it('renders accessible loading indicator', () => {
      render(<MetadataSkeleton />)

      const skeleton = screen.getByRole('status')
      expect(skeleton).toBeInTheDocument()
    })

    it('has proper aria-label for screen readers', () => {
      render(<MetadataSkeleton />)

      const skeleton = screen.getByRole('status')
      expect(skeleton).toHaveAccessibleName(/loading/i)
    })
  })

  describe('Custom Styling', () => {
    it('applies custom className', () => {
      const { container } = render(<MetadataSkeleton className="custom-skeleton" />)

      const skeleton = container.querySelector('.custom-skeleton')
      expect(skeleton).toBeInTheDocument()
    })

    it('combines custom className with default classes', () => {
      const { container } = render(<MetadataSkeleton className="mt-4 p-2" />)

      const skeleton = container.querySelector('.mt-4.p-2')
      expect(skeleton).toBeInTheDocument()
    })
  })

  describe('Edge Cases', () => {
    it('handles rows=0 gracefully', () => {
      const { container } = render(<MetadataSkeleton rows={0} />)

      const rows = container.querySelectorAll('[data-testid="skeleton-row"]')
      expect(rows).toHaveLength(0)
    })

    it('handles rows=1', () => {
      const { container } = render(<MetadataSkeleton rows={1} />)

      const rows = container.querySelectorAll('[data-testid="skeleton-row"]')
      expect(rows).toHaveLength(1)
    })

    it('handles large number of rows', () => {
      const { container } = render(<MetadataSkeleton rows={50} />)

      const rows = container.querySelectorAll('[data-testid="skeleton-row"]')
      expect(rows).toHaveLength(50)
    })
  })

  describe('Accessibility', () => {
    it('has role="status" for assistive technology', () => {
      const { container } = render(<MetadataSkeleton />)

      const status = container.querySelector('[role="status"]')
      expect(status).toBeInTheDocument()
    })

    it('includes aria-label describing the loading state', () => {
      render(<MetadataSkeleton />)

      const skeleton = screen.getByLabelText(/loading.*metadata/i)
      expect(skeleton).toBeInTheDocument()
    })

    it('is not focusable', () => {
      const { container } = render(<MetadataSkeleton />)

      const skeleton = container.querySelector('[role="status"]')
      expect(skeleton).not.toHaveAttribute('tabIndex')
    })
  })

  describe('Layout', () => {
    it('renders each row with consistent styling', () => {
      const { container } = render(<MetadataSkeleton rows={3} />)

      const rows = container.querySelectorAll('[data-testid="skeleton-row"]')
      rows.forEach(row => {
        // Each row should have background and rounded styling
        expect(row.className).toMatch(/bg-/)
        expect(row.className).toMatch(/rounded/)
      })
    })

    it('renders rows with different widths for visual variety', () => {
      const { container } = render(<MetadataSkeleton rows={5} />)

      const rows = container.querySelectorAll('[data-testid="skeleton-row"]')
      const widths = Array.from(rows).map(row => row.style.width)

      // Should have some variation in widths (not all the same)
      const uniqueWidths = new Set(widths)
      expect(uniqueWidths.size).toBeGreaterThan(1)
    })
  })
})

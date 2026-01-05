/**
 * Tests for ConflictSummary component (Issue #326)
 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ConflictSummary from '../ConflictSummary'

describe('ConflictSummary', () => {
  describe('Rendering', () => {
    it('renders with correct data-testid', () => {
      const conflicts = [{ severity: 'error' }]
      render(<ConflictSummary conflicts={conflicts} />)
      expect(screen.getByTestId('conflict-summary')).toBeInTheDocument()
    })

    it('does not render when conflicts array is empty', () => {
      render(<ConflictSummary conflicts={[]} />)
      expect(screen.queryByTestId('conflict-summary')).not.toBeInTheDocument()
    })

    it('displays total conflict count', () => {
      const conflicts = [
        { severity: 'error' },
        { severity: 'warning' },
        { severity: 'error' },
      ]
      render(<ConflictSummary conflicts={conflicts} />)
      expect(screen.getByText('3 conflicts')).toBeInTheDocument()
    })

    it('uses singular form for single conflict', () => {
      const conflicts = [{ severity: 'error' }]
      render(<ConflictSummary conflicts={conflicts} />)
      expect(screen.getByText('1 conflict')).toBeInTheDocument()
    })
  })

  describe('Breakdown Display', () => {
    it('shows collision count', () => {
      const conflicts = [{ severity: 'error' }, { severity: 'error' }]
      render(<ConflictSummary conflicts={conflicts} />)
      expect(screen.getByText('2 collisions')).toBeInTheDocument()
    })

    it('shows warning count', () => {
      const conflicts = [{ severity: 'warning' }, { severity: 'warning' }]
      render(<ConflictSummary conflicts={conflicts} />)
      expect(screen.getByText('2 warnings')).toBeInTheDocument()
    })

    it('shows both collision and warning counts', () => {
      const conflicts = [
        { severity: 'error' },
        { severity: 'warning' },
        { severity: 'warning' },
      ]
      render(<ConflictSummary conflicts={conflicts} />)
      expect(screen.getByText(/1 collision/)).toBeInTheDocument()
      expect(screen.getByText(/2 warnings/)).toBeInTheDocument()
    })

    it('uses singular form for single collision', () => {
      const conflicts = [{ severity: 'error' }]
      render(<ConflictSummary conflicts={conflicts} />)
      expect(screen.getByText('1 collision')).toBeInTheDocument()
    })

    it('uses singular form for single warning', () => {
      const conflicts = [{ severity: 'warning' }]
      render(<ConflictSummary conflicts={conflicts} />)
      expect(screen.getByText('1 warning')).toBeInTheDocument()
    })
  })

  describe('Styling', () => {
    it('has red border styling', () => {
      const conflicts = [{ severity: 'error' }]
      render(<ConflictSummary conflicts={conflicts} />)
      const banner = screen.getByTestId('conflict-summary')
      expect(banner).toHaveClass('border')
      expect(banner).toHaveClass('border-red-900/50')
    })

    it('has red text for total count', () => {
      const conflicts = [{ severity: 'error' }]
      render(<ConflictSummary conflicts={conflicts} />)
      const totalText = screen.getByText('1 conflict')
      expect(totalText).toHaveClass('text-red-400')
    })

    it('has gray text for breakdown', () => {
      const conflicts = [{ severity: 'error' }]
      render(<ConflictSummary conflicts={conflicts} />)
      const breakdownText = screen.getByText('1 collision')
      expect(breakdownText).toHaveClass('text-gray-500')
    })
  })

  describe('Accessibility', () => {
    it('has role="status"', () => {
      const conflicts = [{ severity: 'error' }]
      render(<ConflictSummary conflicts={conflicts} />)
      expect(screen.getByRole('status')).toBeInTheDocument()
    })

    it('has descriptive aria-label', () => {
      const conflicts = [
        { severity: 'error' },
        { severity: 'warning' },
      ]
      render(<ConflictSummary conflicts={conflicts} />)
      const banner = screen.getByRole('status')
      expect(banner).toHaveAttribute(
        'aria-label',
        '2 conflicts: 1 collision, 1 warning'
      )
    })
  })
})

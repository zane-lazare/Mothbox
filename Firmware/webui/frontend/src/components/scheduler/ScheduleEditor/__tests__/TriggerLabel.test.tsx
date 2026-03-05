import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import TriggerLabel from '../TriggerLabel'
import type { Trigger } from '../scheduler-types'

// TriggerLabel only reads trigger_type, so partial objects are fine at runtime.
// Use type assertions to satisfy the discriminated union.
describe('TriggerLabel', () => {
  describe('rendering', () => {
    it('renders interval label', () => {
      render(<TriggerLabel trigger={{ trigger_type: 'interval' } as Trigger} />)
      expect(screen.getByText('Interval')).toBeInTheDocument()
    })

    it('renders solar label', () => {
      render(<TriggerLabel trigger={{ trigger_type: 'solar' } as Trigger} />)
      expect(screen.getByText('Solar')).toBeInTheDocument()
    })

    it('renders fixed_time label', () => {
      render(<TriggerLabel trigger={{ trigger_type: 'fixed_time' } as Trigger} />)
      expect(screen.getByText('Fixed')).toBeInTheDocument()
    })

    it('renders moon_phase label', () => {
      render(<TriggerLabel trigger={{ trigger_type: 'moon_phase' } as Trigger} />)
      expect(screen.getByText('Moon')).toBeInTheDocument()
    })

    it('renders recurring_days label', () => {
      render(<TriggerLabel trigger={{ trigger_type: 'recurring_days' } as Trigger} />)
      expect(screen.getByText('Days')).toBeInTheDocument()
    })

    it('renders cron label', () => {
      render(<TriggerLabel trigger={{ trigger_type: 'cron' } as Trigger} />)
      expect(screen.getByText('Cron')).toBeInTheDocument()
    })
  })

  describe('null/undefined handling', () => {
    it('returns null for null trigger', () => {
      const { container } = render(<TriggerLabel trigger={null} />)
      expect(container.firstChild).toBeNull()
    })

    it('returns null for undefined trigger', () => {
      const { container } = render(<TriggerLabel trigger={undefined} />)
      expect(container.firstChild).toBeNull()
    })

    it('returns null for empty trigger object', () => {
      const { container } = render(<TriggerLabel trigger={{} as Trigger} />)
      expect(container.firstChild).toBeNull()
    })
  })

  describe('styling', () => {
    it('has correct text styling', () => {
      render(<TriggerLabel trigger={{ trigger_type: 'interval' } as Trigger} />)
      const label = screen.getByText('Interval')
      expect(label).toHaveClass('text-xs')
      expect(label).toHaveClass('text-gray-600')
    })

    it('has dark mode styling', () => {
      render(<TriggerLabel trigger={{ trigger_type: 'solar' } as Trigger} />)
      const label = screen.getByText('Solar')
      expect(label).toHaveClass('dark:text-gray-500')
    })
  })

  describe('data-testid', () => {
    it('has correct data-testid for compatibility', () => {
      render(<TriggerLabel trigger={{ trigger_type: 'interval' } as Trigger} />)
      expect(screen.getByTestId('trigger-badge')).toBeInTheDocument()
    })
  })
})

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import TriggerLabel from '../TriggerLabel'

describe('TriggerLabel', () => {
  describe('rendering', () => {
    it('renders interval label', () => {
      render(<TriggerLabel trigger={{ trigger_type: 'interval' }} />)
      expect(screen.getByText('Interval')).toBeInTheDocument()
    })

    it('renders solar label', () => {
      render(<TriggerLabel trigger={{ trigger_type: 'solar' }} />)
      expect(screen.getByText('Solar')).toBeInTheDocument()
    })

    it('renders fixed_time label', () => {
      render(<TriggerLabel trigger={{ trigger_type: 'fixed_time' }} />)
      expect(screen.getByText('Fixed')).toBeInTheDocument()
    })

    it('renders moon_phase label', () => {
      render(<TriggerLabel trigger={{ trigger_type: 'moon_phase' }} />)
      expect(screen.getByText('Moon')).toBeInTheDocument()
    })

    it('renders recurring_days label', () => {
      render(<TriggerLabel trigger={{ trigger_type: 'recurring_days' }} />)
      expect(screen.getByText('Days')).toBeInTheDocument()
    })

    it('renders cron label', () => {
      render(<TriggerLabel trigger={{ trigger_type: 'cron' }} />)
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
      const { container } = render(<TriggerLabel trigger={{}} />)
      expect(container.firstChild).toBeNull()
    })
  })

  describe('styling', () => {
    it('has correct text styling', () => {
      render(<TriggerLabel trigger={{ trigger_type: 'interval' }} />)
      const label = screen.getByText('Interval')
      expect(label).toHaveClass('text-xs')
      expect(label).toHaveClass('text-gray-600')
    })

    it('has dark mode styling', () => {
      render(<TriggerLabel trigger={{ trigger_type: 'solar' }} />)
      const label = screen.getByText('Solar')
      expect(label).toHaveClass('dark:text-gray-500')
    })
  })

  describe('data-testid', () => {
    it('has correct data-testid for compatibility', () => {
      render(<TriggerLabel trigger={{ trigger_type: 'interval' }} />)
      expect(screen.getByTestId('trigger-badge')).toBeInTheDocument()
    })
  })
})

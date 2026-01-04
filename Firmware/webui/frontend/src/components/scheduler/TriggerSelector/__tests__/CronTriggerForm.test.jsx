import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CronTriggerForm from '../CronTriggerForm'

describe('CronTriggerForm', () => {
  const mockOnChange = vi.fn()
  const defaultTrigger = {
    trigger_type: 'cron',
    cron_expression: '*/15 18-6 * * *',
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders cron expression input', () => {
      render(<CronTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      expect(screen.getByTestId('cron-trigger-form')).toBeInTheDocument()
      expect(screen.getByTestId('cron-expression')).toHaveValue('*/15 18-6 * * *')
    })

    it('shows advanced badge', () => {
      render(<CronTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      expect(screen.getByText('advanced')).toBeInTheDocument()
    })

    it('shows cron description', () => {
      render(<CronTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      expect(screen.getByTestId('cron-description')).toBeInTheDocument()
    })

    it('has monospace font on input', () => {
      render(<CronTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      const input = screen.getByTestId('cron-expression')
      expect(input).toHaveClass('font-mono')
    })
  })

  describe('Expression Changes', () => {
    it('updates cron_expression when value changes', async () => {
      const user = userEvent.setup()
      render(<CronTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      const input = screen.getByTestId('cron-expression')
      await user.clear(input)
      await user.type(input, '0 21 * * *')

      // Verify onChange was called with cron_expression property
      expect(mockOnChange).toHaveBeenCalled()
      const lastCall = mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0]
      expect(lastCall).toHaveProperty('cron_expression')
      expect(typeof lastCall.cron_expression).toBe('string')
    })
  })

  describe('Description Parsing', () => {
    it('describes interval pattern', () => {
      render(
        <CronTriggerForm
          trigger={{ ...defaultTrigger, cron_expression: '*/15 * * * *' }}
          onChange={mockOnChange}
        />
      )

      expect(screen.getByTestId('cron-description')).toHaveTextContent(/every 15 minutes/i)
    })

    it('describes interval with time range', () => {
      render(
        <CronTriggerForm
          trigger={{ ...defaultTrigger, cron_expression: '*/15 18-6 * * *' }}
          onChange={mockOnChange}
        />
      )

      expect(screen.getByTestId('cron-description')).toHaveTextContent(/every 15 minutes.*18.*6/i)
    })

    it('describes daily pattern', () => {
      render(
        <CronTriggerForm
          trigger={{ ...defaultTrigger, cron_expression: '0 21 * * *' }}
          onChange={mockOnChange}
        />
      )

      expect(screen.getByTestId('cron-description')).toHaveTextContent(/daily.*9pm/i)
    })

    it('shows custom schedule for complex patterns', () => {
      render(
        <CronTriggerForm
          trigger={{ ...defaultTrigger, cron_expression: '30 4 1,15 * *' }}
          onChange={mockOnChange}
        />
      )

      expect(screen.getByTestId('cron-description')).toHaveTextContent(/custom schedule/i)
    })
  })

  describe('Disabled State', () => {
    it('disables input when disabled prop is true', () => {
      render(<CronTriggerForm trigger={defaultTrigger} onChange={mockOnChange} disabled />)

      expect(screen.getByTestId('cron-expression')).toBeDisabled()
    })
  })

  describe('data-testid attributes', () => {
    it('has cron-trigger-form on container', () => {
      render(<CronTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      expect(screen.getByTestId('cron-trigger-form')).toBeInTheDocument()
    })

    it('has cron-expression on input', () => {
      render(<CronTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      expect(screen.getByTestId('cron-expression')).toBeInTheDocument()
    })

    it('has cron-description on description text', () => {
      render(<CronTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      expect(screen.getByTestId('cron-description')).toBeInTheDocument()
    })
  })
})

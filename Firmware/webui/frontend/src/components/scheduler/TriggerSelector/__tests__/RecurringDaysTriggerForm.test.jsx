import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import RecurringDaysTriggerForm from '../RecurringDaysTriggerForm'
import { DAYS_OF_WEEK } from '../constants'

describe('RecurringDaysTriggerForm', () => {
  const mockOnChange = vi.fn()
  const defaultTrigger = {
    trigger_type: 'recurring_days',
    days: [0, 5, 6],
    time: '20:00',
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders day selection grid with 7 buttons', () => {
      render(<RecurringDaysTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      expect(screen.getByTestId('recurring-days-trigger-form')).toBeInTheDocument()
      expect(screen.getByTestId('recurring-days-grid')).toBeInTheDocument()

      DAYS_OF_WEEK.forEach((day) => {
        expect(screen.getByTestId(`day-${day.value}`)).toBeInTheDocument()
      })
    })

    it('shows correct days as selected', () => {
      render(<RecurringDaysTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      // Sunday (0), Friday (5), Saturday (6) are selected
      expect(screen.getByTestId('day-0')).toHaveAttribute('aria-pressed', 'true')
      expect(screen.getByTestId('day-5')).toHaveAttribute('aria-pressed', 'true')
      expect(screen.getByTestId('day-6')).toHaveAttribute('aria-pressed', 'true')

      // Monday-Thursday are not selected
      expect(screen.getByTestId('day-1')).toHaveAttribute('aria-pressed', 'false')
      expect(screen.getByTestId('day-2')).toHaveAttribute('aria-pressed', 'false')
      expect(screen.getByTestId('day-3')).toHaveAttribute('aria-pressed', 'false')
      expect(screen.getByTestId('day-4')).toHaveAttribute('aria-pressed', 'false')
    })

    it('renders time input with value', () => {
      render(<RecurringDaysTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      expect(screen.getByTestId('trigger-time')).toHaveValue('20:00')
    })

    it('displays day labels', () => {
      render(<RecurringDaysTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      // S, M, T, W, T, F, S
      expect(screen.getAllByText('S')).toHaveLength(2) // Sunday and Saturday
      expect(screen.getByText('M')).toBeInTheDocument()
      expect(screen.getAllByText('T')).toHaveLength(2) // Tuesday and Thursday
      expect(screen.getByText('W')).toBeInTheDocument()
      expect(screen.getByText('F')).toBeInTheDocument()
    })
  })

  describe('Day Selection', () => {
    it('adds day when unselected day clicked', async () => {
      const user = userEvent.setup()
      render(<RecurringDaysTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      await user.click(screen.getByTestId('day-1')) // Monday

      expect(mockOnChange).toHaveBeenCalledWith({
        ...defaultTrigger,
        days: [0, 1, 5, 6], // Sorted order
      })
    })

    it('removes day when selected day clicked (multiple days)', async () => {
      const user = userEvent.setup()
      render(<RecurringDaysTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      await user.click(screen.getByTestId('day-5')) // Friday

      expect(mockOnChange).toHaveBeenCalledWith({
        ...defaultTrigger,
        days: [0, 6],
      })
    })

    it('prevents removing last day', async () => {
      const user = userEvent.setup()
      render(
        <RecurringDaysTriggerForm
          trigger={{ ...defaultTrigger, days: [0] }}
          onChange={mockOnChange}
        />
      )

      await user.click(screen.getByTestId('day-0'))

      // Should not call onChange - can't remove last day
      expect(mockOnChange).not.toHaveBeenCalled()
    })

    it('maintains sorted order when adding days', async () => {
      const user = userEvent.setup()
      render(
        <RecurringDaysTriggerForm
          trigger={{ ...defaultTrigger, days: [6] }}
          onChange={mockOnChange}
        />
      )

      await user.click(screen.getByTestId('day-1'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...defaultTrigger,
        days: [1, 6],
      })
    })
  })

  describe('Time Changes', () => {
    it('updates time when changed', async () => {
      const user = userEvent.setup()
      render(<RecurringDaysTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      const input = screen.getByTestId('trigger-time')
      // For time inputs, we test that onChange is called when input changes
      await user.clear(input)
      await user.type(input, '21:30')

      // Verify onChange was called with time property
      expect(mockOnChange).toHaveBeenCalled()
      const lastCall = mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0]
      expect(lastCall).toHaveProperty('time')
      expect(typeof lastCall.time).toBe('string')
    })
  })

  describe('Disabled State', () => {
    it('disables all inputs when disabled prop is true', () => {
      render(<RecurringDaysTriggerForm trigger={defaultTrigger} onChange={mockOnChange} disabled />)

      DAYS_OF_WEEK.forEach((day) => {
        expect(screen.getByTestId(`day-${day.value}`)).toBeDisabled()
      })
      expect(screen.getByTestId('trigger-time')).toBeDisabled()
    })
  })

  describe('Accessibility', () => {
    it('has aria-pressed attribute on day buttons', () => {
      render(<RecurringDaysTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      DAYS_OF_WEEK.forEach((day) => {
        const button = screen.getByTestId(`day-${day.value}`)
        expect(button).toHaveAttribute('aria-pressed')
      })
    })

    it('has aria-label with full day name', () => {
      render(<RecurringDaysTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      DAYS_OF_WEEK.forEach((day) => {
        const button = screen.getByTestId(`day-${day.value}`)
        expect(button).toHaveAttribute('aria-label', day.label)
      })
    })
  })

  describe('data-testid attributes', () => {
    it('has recurring-days-trigger-form on container', () => {
      render(<RecurringDaysTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      expect(screen.getByTestId('recurring-days-trigger-form')).toBeInTheDocument()
    })

    it('has recurring-days-grid on grid container', () => {
      render(<RecurringDaysTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      expect(screen.getByTestId('recurring-days-grid')).toBeInTheDocument()
    })

    it('has trigger-time on time input', () => {
      render(<RecurringDaysTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      expect(screen.getByTestId('trigger-time')).toBeInTheDocument()
    })
  })
})

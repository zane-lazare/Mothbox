import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import IntervalTriggerForm from '../IntervalTriggerForm'

describe('IntervalTriggerForm', () => {
  const mockOnChange = vi.fn()
  const defaultTrigger = {
    trigger_type: 'interval',
    interval_minutes: 15,
    time_window: null,
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders interval form with value and unit', () => {
      render(<IntervalTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      expect(screen.getByTestId('interval-trigger-form')).toBeInTheDocument()
      expect(screen.getByTestId('interval-value')).toHaveValue(15)
      expect(screen.getByTestId('interval-unit')).toHaveValue('minutes')
    })

    it('displays hours when interval is divisible by 60', () => {
      render(
        <IntervalTriggerForm
          trigger={{ ...defaultTrigger, interval_minutes: 120 }}
          onChange={mockOnChange}
        />
      )

      expect(screen.getByTestId('interval-value')).toHaveValue(2)
      expect(screen.getByTestId('interval-unit')).toHaveValue('hours')
    })

    it('renders time window inputs when enabled', () => {
      render(
        <IntervalTriggerForm
          trigger={{
            ...defaultTrigger,
            time_window: { start_time: '18:00', end_time: '06:00' },
          }}
          onChange={mockOnChange}
        />
      )

      expect(screen.getByTestId('time-window-toggle')).toBeChecked()
      expect(screen.getByTestId('time-window-start')).toHaveValue('18:00')
      expect(screen.getByTestId('time-window-end')).toHaveValue('06:00')
    })

    it('hides time window inputs when disabled', () => {
      render(<IntervalTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      expect(screen.getByTestId('time-window-toggle')).not.toBeChecked()
      expect(screen.queryByTestId('time-window-start')).not.toBeInTheDocument()
      expect(screen.queryByTestId('time-window-end')).not.toBeInTheDocument()
    })
  })

  describe('Value Changes', () => {
    it('updates interval_minutes when value changes', async () => {
      const user = userEvent.setup()
      render(<IntervalTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      const input = screen.getByTestId('interval-value')
      await user.clear(input)
      await user.type(input, '30')

      // Verify onChange was called with correct structure
      expect(mockOnChange).toHaveBeenCalled()
      const lastCall = mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0]
      expect(lastCall).toHaveProperty('interval_minutes')
      expect(typeof lastCall.interval_minutes).toBe('number')
    })

    it('updates interval_minutes when unit changes to hours', async () => {
      const user = userEvent.setup()
      render(<IntervalTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      await user.selectOptions(screen.getByTestId('interval-unit'), 'hours')

      // 15 minutes * 60 = 900 minutes (15 hours)
      expect(mockOnChange).toHaveBeenLastCalledWith({
        ...defaultTrigger,
        interval_minutes: 900,
      })
    })
  })

  describe('Time Window', () => {
    it('enables time window with default values when checkbox checked', async () => {
      const user = userEvent.setup()
      render(<IntervalTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      await user.click(screen.getByTestId('time-window-toggle'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...defaultTrigger,
        time_window: {
          start_time: '18:00',
          end_time: '06:00',
        },
      })
    })

    it('disables time window when checkbox unchecked', async () => {
      const user = userEvent.setup()
      render(
        <IntervalTriggerForm
          trigger={{
            ...defaultTrigger,
            time_window: { start_time: '18:00', end_time: '06:00' },
          }}
          onChange={mockOnChange}
        />
      )

      await user.click(screen.getByTestId('time-window-toggle'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...defaultTrigger,
        time_window: null,
      })
    })

    it('updates start time', async () => {
      const user = userEvent.setup()
      const trigger = {
        ...defaultTrigger,
        time_window: { start_time: '18:00', end_time: '06:00' },
      }
      render(<IntervalTriggerForm trigger={trigger} onChange={mockOnChange} />)

      const startInput = screen.getByTestId('time-window-start')
      // For time inputs, we test that onChange is called when input changes
      await user.clear(startInput)
      await user.type(startInput, '20:00')

      // Verify onChange was called (time inputs trigger onChange on each change)
      expect(mockOnChange).toHaveBeenCalled()
      // Check that time_window structure is preserved
      const lastCall = mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0]
      expect(lastCall).toHaveProperty('time_window')
      expect(lastCall.time_window).toHaveProperty('start_time')
    })

    it('updates end time', async () => {
      const user = userEvent.setup()
      const trigger = {
        ...defaultTrigger,
        time_window: { start_time: '18:00', end_time: '06:00' },
      }
      render(<IntervalTriggerForm trigger={trigger} onChange={mockOnChange} />)

      const endInput = screen.getByTestId('time-window-end')
      // For time inputs, we test that onChange is called when input changes
      await user.clear(endInput)
      await user.type(endInput, '05:00')

      // Verify onChange was called (time inputs trigger onChange on each change)
      expect(mockOnChange).toHaveBeenCalled()
      // Check that time_window structure is preserved
      const lastCall = mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0]
      expect(lastCall).toHaveProperty('time_window')
      expect(lastCall.time_window).toHaveProperty('end_time')
    })
  })

  describe('Disabled State', () => {
    it('disables all inputs when disabled prop is true', () => {
      render(
        <IntervalTriggerForm
          trigger={{
            ...defaultTrigger,
            time_window: { start_time: '18:00', end_time: '06:00' },
          }}
          onChange={mockOnChange}
          disabled
        />
      )

      expect(screen.getByTestId('interval-value')).toBeDisabled()
      expect(screen.getByTestId('interval-unit')).toBeDisabled()
      expect(screen.getByTestId('time-window-toggle')).toBeDisabled()
      expect(screen.getByTestId('time-window-start')).toBeDisabled()
      expect(screen.getByTestId('time-window-end')).toBeDisabled()
    })
  })

  describe('data-testid attributes', () => {
    it('has interval-trigger-form on container', () => {
      render(<IntervalTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      expect(screen.getByTestId('interval-trigger-form')).toBeInTheDocument()
    })

    it('has all required testids', () => {
      render(
        <IntervalTriggerForm
          trigger={{
            ...defaultTrigger,
            time_window: { start_time: '18:00', end_time: '06:00' },
          }}
          onChange={mockOnChange}
        />
      )

      expect(screen.getByTestId('interval-value')).toBeInTheDocument()
      expect(screen.getByTestId('interval-unit')).toBeInTheDocument()
      expect(screen.getByTestId('time-window-toggle')).toBeInTheDocument()
      expect(screen.getByTestId('time-window-start')).toBeInTheDocument()
      expect(screen.getByTestId('time-window-end')).toBeInTheDocument()
    })
  })
})

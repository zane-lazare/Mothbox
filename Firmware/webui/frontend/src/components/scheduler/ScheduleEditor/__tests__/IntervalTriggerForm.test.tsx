import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import IntervalTriggerForm from '../IntervalTriggerForm'
import { SCHEDULE_LIMITS } from '../constants'

// ── Mock child components ──────────────────────────────────────────────

vi.mock('../TimeWindowInput', () => ({
  default: ({
    value,
    onChange,
    disabled,
    errors,
  }: {
    value: { start_time: string; end_time: string }
    onChange: (v: Record<string, string>) => void
    disabled: boolean
    errors: Record<string, string>
  }) => (
    <div data-testid="time-window-input">
      <input
        data-testid="time-window-start"
        value={value.start_time}
        onChange={(e) => onChange({ ...value, start_time: e.target.value })}
        disabled={disabled}
      />
      <input
        data-testid="time-window-end"
        value={value.end_time}
        onChange={(e) => onChange({ ...value, end_time: e.target.value })}
        disabled={disabled}
      />
      {errors.start_time && (
        <span data-testid="error-start">{errors.start_time}</span>
      )}
      {errors.end_time && <span data-testid="error-end">{errors.end_time}</span>}
    </div>
  ),
}))

vi.mock('../DaysOfWeekSelector', () => ({
  default: ({
    value,
    onChange,
    disabled,
  }: {
    value: number[] | null
    onChange: (v: number[] | null) => void
    disabled: boolean
  }) => (
    <div data-testid="days-of-week-selector">
      <button
        data-testid="toggle-monday"
        onClick={() => {
          const currentDays = value || [0, 1, 2, 3, 4, 5, 6]
          const newDays = currentDays.includes(0)
            ? currentDays.filter((d) => d !== 0)
            : [...currentDays, 0].sort((a, b) => a - b)
          onChange(newDays.length === 7 ? null : newDays)
        }}
        disabled={disabled}
      >
        Monday
      </button>
      <button
        data-testid="toggle-all-days"
        onClick={() => onChange(null)}
        disabled={disabled}
      >
        All Days
      </button>
    </div>
  ),
}))

// ── Helpers ────────────────────────────────────────────────────────────

const defaultValue = {
  interval_minutes: 60,
  time_window: {
    start_time: '21:00',
    end_time: '05:00',
    start_offset_minutes: 0,
    end_offset_minutes: 0,
  },
  days_of_week: null as number[] | null,
}

// ── Tests ──────────────────────────────────────────────────────────────

describe('IntervalTriggerForm', () => {
  type IntervalTriggerValue = {
    interval_minutes: number
    time_window: { start_time: string; end_time: string; start_offset_minutes?: number; end_offset_minutes?: number }
    days_of_week: number[] | null
  }

  let mockOnChange: ReturnType<typeof vi.fn<(value: IntervalTriggerValue) => void>>

  beforeEach(() => {
    mockOnChange = vi.fn<(value: IntervalTriggerValue) => void>()
  })

  describe('Rendering', () => {
    it('renders with default values', () => {
      render(<IntervalTriggerForm onChange={mockOnChange} />)

      expect(screen.getByText('Interval Configuration')).toBeInTheDocument()
      expect(screen.getByLabelText('Interval in minutes')).toBeInTheDocument()
      expect(screen.getByText('Quick presets:')).toBeInTheDocument()
      expect(screen.getByText('Time Window:')).toBeInTheDocument()
      expect(screen.getByText('Preview:')).toBeInTheDocument()
    })

    it('renders with provided value', () => {
      const value = {
        interval_minutes: 120,
        time_window: {
          start_time: '21:00',
          end_time: '05:00',
          start_offset_minutes: 0,
          end_offset_minutes: 0,
        },
        days_of_week: [0, 1, 2],
      }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      const intervalInput = screen.getByLabelText('Interval in minutes')
      expect(intervalInput).toHaveValue(120)
    })

    it('renders all quick preset buttons', () => {
      render(<IntervalTriggerForm onChange={mockOnChange} />)

      expect(screen.getByLabelText('Set interval to 15 min')).toBeInTheDocument()
      expect(screen.getByLabelText('Set interval to 30 min')).toBeInTheDocument()
      expect(screen.getByLabelText('Set interval to 60 min')).toBeInTheDocument()
      expect(screen.getByLabelText('Set interval to 2 hours')).toBeInTheDocument()
      expect(screen.getByLabelText('Set interval to 4 hours')).toBeInTheDocument()
    })

    it('renders TimeWindowInput component', () => {
      render(<IntervalTriggerForm onChange={mockOnChange} />)
      expect(screen.getByTestId('time-window-input')).toBeInTheDocument()
    })

    it('renders DaysOfWeekSelector component', () => {
      render(<IntervalTriggerForm onChange={mockOnChange} />)
      expect(screen.getByTestId('days-of-week-selector')).toBeInTheDocument()
    })
  })

  describe('Interval Input (react-hook-form + Zod)', () => {
    it('propagates valid interval change to parent', async () => {
      const user = userEvent.setup()
      const value = { ...defaultValue, interval_minutes: 60 }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      const input = screen.getByLabelText('Interval in minutes')
      await user.clear(input)
      await user.type(input, '90')

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({ interval_minutes: 90 }),
        )
      })
    })

    it('respects min and max interval attributes', () => {
      render(<IntervalTriggerForm onChange={mockOnChange} />)

      const intervalInput = screen.getByLabelText('Interval in minutes')
      expect(intervalInput).toHaveAttribute(
        'min',
        String(SCHEDULE_LIMITS.MIN_INTERVAL_MINUTES),
      )
      expect(intervalInput).toHaveAttribute(
        'max',
        String(SCHEDULE_LIMITS.MAX_INTERVAL_MINUTES),
      )
    })

    it('shows Zod error for out-of-range value', async () => {
      const user = userEvent.setup()

      render(
        <IntervalTriggerForm
          value={defaultValue}
          onChange={mockOnChange}
        />,
      )

      const input = screen.getByLabelText('Interval in minutes')
      await user.clear(input)
      await user.type(input, '0')

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })
    })

    it('does not propagate invalid values to parent', async () => {
      const user = userEvent.setup()

      render(
        <IntervalTriggerForm
          value={defaultValue}
          onChange={mockOnChange}
        />,
      )

      const input = screen.getByLabelText('Interval in minutes')
      await user.clear(input)
      await user.type(input, '0')

      // onChange should not be called with an invalid value
      await waitFor(() => {
        const calls = mockOnChange.mock.calls
        const invalidCall = calls.find(
          (c: [{ interval_minutes: number }]) => c[0].interval_minutes === 0,
        )
        expect(invalidCall).toBeUndefined()
      })
    })

    it('shows parent-provided error message', () => {
      const errors = {
        interval_minutes: 'Server validation failed',
      }

      render(
        <IntervalTriggerForm
          onChange={mockOnChange}
          errors={errors}
        />,
      )

      expect(screen.getByText('Server validation failed')).toBeInTheDocument()
    })

    it('accepts boundary value MIN_INTERVAL_MINUTES', async () => {
      const user = userEvent.setup()
      const value = { ...defaultValue, interval_minutes: 60 }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      const input = screen.getByLabelText('Interval in minutes')
      await user.clear(input)
      await user.type(input, String(SCHEDULE_LIMITS.MIN_INTERVAL_MINUTES))

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({
            interval_minutes: SCHEDULE_LIMITS.MIN_INTERVAL_MINUTES,
          }),
        )
      })
    })

    it('accepts boundary value MAX_INTERVAL_MINUTES', async () => {
      const user = userEvent.setup()
      const value = { ...defaultValue, interval_minutes: 60 }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      const input = screen.getByLabelText('Interval in minutes')
      await user.clear(input)
      await user.type(input, String(SCHEDULE_LIMITS.MAX_INTERVAL_MINUTES))

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({
            interval_minutes: SCHEDULE_LIMITS.MAX_INTERVAL_MINUTES,
          }),
        )
      })
    })
  })

  describe('Quick Preset Buttons', () => {
    it('sets interval to 15 minutes when 15 min preset clicked', () => {
      const value = { ...defaultValue, interval_minutes: 60 }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      fireEvent.click(screen.getByLabelText('Set interval to 15 min'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        interval_minutes: 15,
      })
    })

    it('sets interval to 30 minutes when 30 min preset clicked', () => {
      const value = { ...defaultValue, interval_minutes: 60 }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      fireEvent.click(screen.getByLabelText('Set interval to 30 min'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        interval_minutes: 30,
      })
    })

    it('sets interval to 60 minutes when 60 min preset clicked', () => {
      const value = { ...defaultValue, interval_minutes: 30 }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      fireEvent.click(screen.getByLabelText('Set interval to 60 min'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        interval_minutes: 60,
      })
    })

    it('sets interval to 120 minutes when 2 hours preset clicked', () => {
      const value = { ...defaultValue, interval_minutes: 60 }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      fireEvent.click(screen.getByLabelText('Set interval to 2 hours'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        interval_minutes: 120,
      })
    })

    it('sets interval to 240 minutes when 4 hours preset clicked', () => {
      const value = { ...defaultValue, interval_minutes: 60 }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      fireEvent.click(screen.getByLabelText('Set interval to 4 hours'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        interval_minutes: 240,
      })
    })

    it('highlights selected preset', () => {
      const value = { ...defaultValue, interval_minutes: 60 }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      const preset60 = screen.getByLabelText('Set interval to 60 min')
      expect(preset60).toHaveClass('bg-blue-500')
    })
  })

  describe('TimeWindowInput Integration', () => {
    it('passes time_window value to TimeWindowInput', () => {
      const value = {
        interval_minutes: 60,
        time_window: {
          start_time: '21:00',
          end_time: '05:00',
          start_offset_minutes: 30,
          end_offset_minutes: -15,
        },
        days_of_week: null,
      }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(screen.getByTestId('time-window-start')).toHaveValue('21:00')
      expect(screen.getByTestId('time-window-end')).toHaveValue('05:00')
    })

    it('calls onChange when TimeWindowInput changes', () => {
      const value = {
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      fireEvent.change(screen.getByTestId('time-window-start'), {
        target: { value: '20:00' },
      })

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        time_window: { ...value.time_window, start_time: '20:00' },
      })
    })

    it('passes errors to TimeWindowInput', () => {
      const errors = {
        time_window: {
          start_time: 'Invalid start time',
          end_time: 'Invalid end time',
        },
      }

      render(
        <IntervalTriggerForm onChange={mockOnChange} errors={errors} />,
      )

      expect(screen.getByTestId('error-start')).toHaveTextContent(
        'Invalid start time',
      )
      expect(screen.getByTestId('error-end')).toHaveTextContent(
        'Invalid end time',
      )
    })

    it('passes disabled state to TimeWindowInput', () => {
      render(
        <IntervalTriggerForm onChange={mockOnChange} disabled={true} />,
      )

      expect(screen.getByTestId('time-window-start')).toBeDisabled()
      expect(screen.getByTestId('time-window-end')).toBeDisabled()
    })
  })

  describe('DaysOfWeekSelector Integration', () => {
    it('passes days_of_week value to DaysOfWeekSelector', () => {
      const value = {
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: [0, 2, 4],
      }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(screen.getByTestId('days-of-week-selector')).toBeInTheDocument()
    })

    it('calls onChange when DaysOfWeekSelector changes', () => {
      const value = {
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      fireEvent.click(screen.getByTestId('toggle-monday'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        days_of_week: [1, 2, 3, 4, 5, 6],
      })
    })

    it('passes disabled state to DaysOfWeekSelector', () => {
      render(
        <IntervalTriggerForm onChange={mockOnChange} disabled={true} />,
      )

      expect(screen.getByTestId('toggle-monday')).toBeDisabled()
    })
  })

  describe('Preview Text Generation', () => {
    it('generates preview for minutes interval with fixed time window', () => {
      const value = {
        interval_minutes: 30,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText('Every 30 minutes from 21:00 to 05:00'),
      ).toBeInTheDocument()
    })

    it('generates preview for hour interval', () => {
      const value = {
        interval_minutes: 120,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText('Every 2 hours from 21:00 to 05:00'),
      ).toBeInTheDocument()
    })

    it('generates preview with solar events', () => {
      const value = {
        interval_minutes: 60,
        time_window: {
          start_time: 'sunset',
          end_time: 'sunrise',
          start_offset_minutes: 30,
          end_offset_minutes: -15,
        },
        days_of_week: null,
      }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText('Every 1 hour from sunset+30 to sunrise-15'),
      ).toBeInTheDocument()
    })

    it('generates preview with specific days', () => {
      const value = {
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: [0, 2, 4],
      }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText(
          'Every 1 hour from 21:00 to 05:00 on Mon, Wed, Fri',
        ),
      ).toBeInTheDocument()
    })

    it('generates preview without days when all days selected', () => {
      const value = {
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText('Every 1 hour from 21:00 to 05:00'),
      ).toBeInTheDocument()
    })

    it('handles singular "minute" in preview', () => {
      const value = {
        interval_minutes: 1,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText('Every 1 minute from 21:00 to 05:00'),
      ).toBeInTheDocument()
    })

    it('formats mixed hours and minutes in preview', () => {
      const value = {
        interval_minutes: 90,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText('Every 1h 30m from 21:00 to 05:00'),
      ).toBeInTheDocument()
    })
  })

  describe('Disabled State', () => {
    it('disables interval input when disabled prop is true', () => {
      render(
        <IntervalTriggerForm onChange={mockOnChange} disabled={true} />,
      )

      expect(screen.getByLabelText('Interval in minutes')).toBeDisabled()
    })

    it('disables preset buttons when disabled prop is true', () => {
      render(
        <IntervalTriggerForm onChange={mockOnChange} disabled={true} />,
      )

      expect(screen.getByLabelText('Set interval to 15 min')).toBeDisabled()
      expect(screen.getByLabelText('Set interval to 30 min')).toBeDisabled()
    })

    it('does not disable inputs when disabled prop is false', () => {
      render(
        <IntervalTriggerForm onChange={mockOnChange} disabled={false} />,
      )

      expect(screen.getByLabelText('Interval in minutes')).not.toBeDisabled()
    })
  })

  describe('Dark Mode Styling', () => {
    it('applies dark mode classes to interval input', () => {
      render(<IntervalTriggerForm onChange={mockOnChange} />)

      const intervalInput = screen.getByLabelText('Interval in minutes')
      expect(intervalInput).toHaveClass(
        'dark:bg-gray-800',
        'dark:text-white',
        'dark:border-gray-600',
      )
    })

    it('applies dark mode classes to preset buttons', () => {
      render(<IntervalTriggerForm onChange={mockOnChange} />)

      const preset15 = screen.getByLabelText('Set interval to 15 min')
      expect(preset15).toHaveClass('dark:bg-gray-700', 'dark:text-gray-300')
    })

    it('applies dark mode classes to labels', () => {
      render(<IntervalTriggerForm onChange={mockOnChange} />)

      expect(screen.getByText('Interval Configuration')).toHaveClass(
        'dark:text-white',
      )
    })

    it('applies dark mode classes to preview text', () => {
      const value = {
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      const previewText = screen.getByText(
        'Every 1 hour from 21:00 to 05:00',
      )
      expect(previewText).toHaveClass('dark:text-gray-300', 'dark:bg-gray-800')
    })
  })

  describe('onChange Callback', () => {
    it('calls onChange with complete trigger object when time window changes', () => {
      const value = {
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      fireEvent.change(screen.getByTestId('time-window-start'), {
        target: { value: '20:00' },
      })

      expect(mockOnChange).toHaveBeenCalledWith({
        interval_minutes: 60,
        time_window: { start_time: '20:00', end_time: '05:00' },
        days_of_week: null,
      })
    })

    it('calls onChange with complete trigger object when days change', () => {
      const value = {
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      fireEvent.click(screen.getByTestId('toggle-all-days'))

      expect(mockOnChange).toHaveBeenCalledWith({
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      })
    })
  })

  describe('Prop sync (external value changes)', () => {
    it('updates input when value prop changes externally', () => {
      const value = { ...defaultValue, interval_minutes: 60 }

      const { rerender } = render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      rerender(
        <IntervalTriggerForm
          value={{ ...value, interval_minutes: 120 }}
          onChange={mockOnChange}
        />,
      )

      const input = screen.getByLabelText('Interval in minutes')
      expect(input).toHaveValue(120)
    })
  })
})

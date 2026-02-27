import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SolarTriggerForm from '../SolarTriggerForm'
import type { SolarTriggerValue } from '../SolarTriggerForm'
import { SOLAR_EVENTS, SCHEDULE_LIMITS } from '../constants'

// ── Mock child components ──────────────────────────────────────────────

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

const defaultValue: SolarTriggerValue = {
  solar_event: 'sunset',
  offset_minutes: 0,
  days_of_week: null,
}

// ── Tests ──────────────────────────────────────────────────────────────

describe('SolarTriggerForm', () => {
  let mockOnChange: ReturnType<typeof vi.fn<(value: SolarTriggerValue) => void>>

  beforeEach(() => {
    mockOnChange = vi.fn<(value: SolarTriggerValue) => void>()
  })

  describe('Rendering', () => {
    it('renders with default values', () => {
      render(<SolarTriggerForm onChange={mockOnChange} />)

      expect(screen.getByText('Solar Event Configuration')).toBeInTheDocument()
      expect(screen.getByLabelText(/solar event/i)).toBeInTheDocument()
      expect(screen.getByLabelText('Offset in minutes')).toBeInTheDocument()
      expect(screen.getByText('Preview:')).toBeInTheDocument()
    })

    it('renders with provided value', () => {
      const value: SolarTriggerValue = {
        solar_event: 'sunrise',
        offset_minutes: 30,
        days_of_week: [0, 1, 2],
      }

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />)

      const solarEventSelect = screen.getByLabelText(/solar event/i)
      expect(solarEventSelect).toHaveValue('sunrise')

      const offsetInput = screen.getByLabelText('Offset in minutes')
      expect(offsetInput).toHaveValue(30)
    })

    it('renders all solar events in dropdown', () => {
      render(<SolarTriggerForm onChange={mockOnChange} />)

      const solarEventSelect = screen.getByLabelText(
        /solar event/i,
      ) as HTMLSelectElement
      const options = Array.from(solarEventSelect.options).map(
        (opt) => opt.value,
      )

      SOLAR_EVENTS.forEach((event) => {
        expect(options).toContain(event.value)
      })
    })

    it('renders DaysOfWeekSelector component', () => {
      render(<SolarTriggerForm onChange={mockOnChange} />)

      expect(screen.getByTestId('days-of-week-selector')).toBeInTheDocument()
    })
  })

  describe('Solar Event Selection', () => {
    it('updates solar_event on selection change', () => {
      render(
        <SolarTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const solarEventSelect = screen.getByLabelText(/solar event/i)
      fireEvent.change(solarEventSelect, { target: { value: 'sunrise' } })

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({ solar_event: 'sunrise' }),
      )
    })

    it('shows description for selected solar event', () => {
      render(
        <SolarTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const sunsetEvent = SOLAR_EVENTS.find((e) => e.value === 'sunset')!
      expect(screen.getByText(sunsetEvent.description)).toBeInTheDocument()
    })

    it('updates description when solar event changes via props', () => {
      const { rerender } = render(
        <SolarTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const sunsetEvent = SOLAR_EVENTS.find((e) => e.value === 'sunset')!
      expect(screen.getByText(sunsetEvent.description)).toBeInTheDocument()

      const newValue = { ...defaultValue, solar_event: 'sunrise' }
      rerender(
        <SolarTriggerForm value={newValue} onChange={mockOnChange} />,
      )

      const sunriseEvent = SOLAR_EVENTS.find((e) => e.value === 'sunrise')!
      expect(screen.getByText(sunriseEvent.description)).toBeInTheDocument()
    })
  })

  describe('Offset Input', () => {
    it('updates offset_minutes on input change', async () => {
      const user = userEvent.setup()
      render(
        <SolarTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const offsetInput = screen.getByLabelText('Offset in minutes')
      await user.clear(offsetInput)
      await user.type(offsetInput, '30')

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({ offset_minutes: 30 }),
        )
      })
    })

    it('allows negative offset values', async () => {
      const user = userEvent.setup()
      render(
        <SolarTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const offsetInput = screen.getByLabelText('Offset in minutes')
      await user.clear(offsetInput)
      await user.type(offsetInput, '-30')

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({ offset_minutes: -30 }),
        )
      })
    })

    it('has min and max offset attributes', () => {
      render(<SolarTriggerForm onChange={mockOnChange} />)

      const offsetInput = screen.getByLabelText('Offset in minutes')
      expect(offsetInput).toHaveAttribute(
        'min',
        String(-SCHEDULE_LIMITS.MAX_OFFSET_MINUTES),
      )
      expect(offsetInput).toHaveAttribute(
        'max',
        String(SCHEDULE_LIMITS.MAX_OFFSET_MINUTES),
      )
    })

    it('shows error message for invalid offset', async () => {
      const user = userEvent.setup()
      render(
        <SolarTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const offsetInput = screen.getByLabelText('Offset in minutes')
      await user.clear(offsetInput)
      await user.type(offsetInput, '1441')

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })
    })

    it('shows parent error when provided', () => {
      const errors = {
        offset_minutes: 'Server error: offset out of range',
      }

      render(
        <SolarTriggerForm
          onChange={mockOnChange}
          errors={errors}
        />,
      )

      expect(screen.getByText(errors.offset_minutes)).toBeInTheDocument()
    })

    it('does not propagate invalid offset to parent', async () => {
      const user = userEvent.setup()
      render(
        <SolarTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const offsetInput = screen.getByLabelText('Offset in minutes')
      await user.clear(offsetInput)
      await user.type(offsetInput, '1441')

      // Wait for validation to process (error message appears)
      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })

      // Then assert no invalid call was made (outside waitFor to avoid false positive)
      expect(mockOnChange).not.toHaveBeenCalledWith(
        expect.objectContaining({ offset_minutes: 1441 }),
      )
    })

    it('shows error and does not propagate when input is cleared', async () => {
      const user = userEvent.setup()
      render(
        <SolarTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const offsetInput = screen.getByLabelText('Offset in minutes')
      await user.clear(offsetInput)

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })

      expect(mockOnChange).not.toHaveBeenCalledWith(
        expect.objectContaining({ offset_minutes: NaN }),
      )
    })
  })

  describe('Quick Offset Presets', () => {
    it('renders quick offset preset buttons', () => {
      render(<SolarTriggerForm onChange={mockOnChange} />)

      expect(
        screen.getByLabelText('Set offset to -60 minutes'),
      ).toBeInTheDocument()
      expect(
        screen.getByLabelText('Set offset to -30 minutes'),
      ).toBeInTheDocument()
      expect(
        screen.getByLabelText('Set offset to 0 minutes'),
      ).toBeInTheDocument()
      expect(
        screen.getByLabelText('Set offset to +30 minutes'),
      ).toBeInTheDocument()
      expect(
        screen.getByLabelText('Set offset to +60 minutes'),
      ).toBeInTheDocument()
    })

    it('sets offset to -60 when -1h preset clicked', () => {
      render(
        <SolarTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      fireEvent.click(screen.getByLabelText('Set offset to -60 minutes'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...defaultValue,
        offset_minutes: -60,
      })
    })

    it('sets offset to 0 when "No offset" preset clicked', () => {
      const value = { ...defaultValue, offset_minutes: 30 }

      render(
        <SolarTriggerForm value={value} onChange={mockOnChange} />,
      )

      fireEvent.click(screen.getByLabelText('Set offset to 0 minutes'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        offset_minutes: 0,
      })
    })

    it('sets offset to +30 when +30m preset clicked', () => {
      render(
        <SolarTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      fireEvent.click(screen.getByLabelText('Set offset to +30 minutes'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...defaultValue,
        offset_minutes: 30,
      })
    })

    it('highlights selected preset', () => {
      const value = { ...defaultValue, offset_minutes: 30 }

      render(
        <SolarTriggerForm value={value} onChange={mockOnChange} />,
      )

      const presetPos30 = screen.getByLabelText('Set offset to +30 minutes')
      expect(presetPos30).toHaveClass('bg-blue-500')
    })
  })

  describe('DaysOfWeekSelector Integration', () => {
    it('passes days_of_week value to DaysOfWeekSelector', () => {
      const value: SolarTriggerValue = {
        solar_event: 'sunset',
        offset_minutes: 0,
        days_of_week: [0, 2, 4],
      }

      render(
        <SolarTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(screen.getByTestId('days-of-week-selector')).toBeInTheDocument()
    })

    it('calls onChange when DaysOfWeekSelector changes', () => {
      render(
        <SolarTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      fireEvent.click(screen.getByTestId('toggle-monday'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...defaultValue,
        days_of_week: [1, 2, 3, 4, 5, 6],
      })
    })

    it('passes disabled state to DaysOfWeekSelector', () => {
      render(
        <SolarTriggerForm onChange={mockOnChange} disabled={true} />,
      )

      expect(screen.getByTestId('toggle-monday')).toBeDisabled()
    })
  })

  describe('Preview Text Generation', () => {
    it('generates preview for solar event without offset', () => {
      render(
        <SolarTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      expect(screen.getByText('At sunset')).toBeInTheDocument()
    })

    it('generates preview with positive offset', () => {
      const value = { ...defaultValue, offset_minutes: 30 }

      render(
        <SolarTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(screen.getByText('30 minutes after sunset')).toBeInTheDocument()
    })

    it('generates preview with negative offset', () => {
      const value = { ...defaultValue, offset_minutes: -30 }

      render(
        <SolarTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(screen.getByText('30 minutes before sunset')).toBeInTheDocument()
    })

    it('generates preview with specific days', () => {
      const value: SolarTriggerValue = {
        solar_event: 'sunset',
        offset_minutes: 0,
        days_of_week: [0, 2, 4],
      }

      render(
        <SolarTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText('At sunset on Mon, Wed, Fri'),
      ).toBeInTheDocument()
    })

    it('generates preview with offset and days', () => {
      const value: SolarTriggerValue = {
        solar_event: 'sunrise',
        offset_minutes: -15,
        days_of_week: [5, 6],
      }

      render(
        <SolarTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText('15 minutes before sunrise on Sat, Sun'),
      ).toBeInTheDocument()
    })

    it('handles large offsets in hours format', () => {
      const value = { ...defaultValue, offset_minutes: 120 }

      render(
        <SolarTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(screen.getByText('2 hours after sunset')).toBeInTheDocument()
    })

    it('handles mixed hours and minutes in preview', () => {
      const value = { ...defaultValue, offset_minutes: 90 }

      render(
        <SolarTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(screen.getByText('1h 30m after sunset')).toBeInTheDocument()
    })
  })

  describe('Disabled State', () => {
    it('disables solar event select when disabled prop is true', () => {
      render(
        <SolarTriggerForm onChange={mockOnChange} disabled={true} />,
      )

      expect(screen.getByLabelText(/solar event/i)).toBeDisabled()
    })

    it('disables offset input when disabled prop is true', () => {
      render(
        <SolarTriggerForm onChange={mockOnChange} disabled={true} />,
      )

      expect(screen.getByLabelText('Offset in minutes')).toBeDisabled()
    })

    it('disables preset buttons when disabled prop is true', () => {
      render(
        <SolarTriggerForm onChange={mockOnChange} disabled={true} />,
      )

      expect(
        screen.getByLabelText('Set offset to 0 minutes'),
      ).toBeDisabled()
    })

    it('does not disable inputs when disabled prop is false', () => {
      render(
        <SolarTriggerForm onChange={mockOnChange} disabled={false} />,
      )

      expect(screen.getByLabelText(/solar event/i)).not.toBeDisabled()
      expect(screen.getByLabelText('Offset in minutes')).not.toBeDisabled()
    })
  })

  describe('Prop Sync', () => {
    it('updates form when value prop changes externally', () => {
      const value: SolarTriggerValue = {
        solar_event: 'sunset',
        offset_minutes: 0,
        days_of_week: null,
      }

      const { rerender } = render(
        <SolarTriggerForm value={value} onChange={mockOnChange} />,
      )

      const newValue: SolarTriggerValue = {
        solar_event: 'sunrise',
        offset_minutes: 30,
        days_of_week: null,
      }
      rerender(
        <SolarTriggerForm value={newValue} onChange={mockOnChange} />,
      )

      expect(screen.getByLabelText(/solar event/i)).toHaveValue('sunrise')
      expect(screen.getByLabelText('Offset in minutes')).toHaveValue(30)
    })

    it('does not reset form when value prop is unchanged', async () => {
      const user = userEvent.setup()
      const value: SolarTriggerValue = {
        solar_event: 'sunset',
        offset_minutes: 60,
        days_of_week: null,
      }

      const { rerender } = render(
        <SolarTriggerForm value={value} onChange={mockOnChange} />,
      )

      // User types a new offset
      const offsetInput = screen.getByLabelText('Offset in minutes')
      await user.clear(offsetInput)
      await user.type(offsetInput, '90')

      // Wait for propagation to settle so lastPropagatedRef is updated
      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({ offset_minutes: 90 }),
        )
      })

      // Re-render with same value (e.g., parent re-renders for unrelated reason)
      rerender(
        <SolarTriggerForm value={value} onChange={mockOnChange} />,
      )

      // The form should still show the user's typed value, not reset to 60
      expect(offsetInput).toHaveValue(90)
    })
  })

  describe('onChange Callback', () => {
    it('calls onChange with complete trigger object when event changes', () => {
      const value: SolarTriggerValue = {
        solar_event: 'sunset',
        offset_minutes: 30,
        days_of_week: [0, 1, 2],
      }

      render(
        <SolarTriggerForm value={value} onChange={mockOnChange} />,
      )

      fireEvent.change(screen.getByLabelText(/solar event/i), {
        target: { value: 'sunrise' },
      })

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          solar_event: 'sunrise',
          offset_minutes: 30,
          days_of_week: [0, 1, 2],
        }),
      )
    })

    it('calls onChange with complete trigger object when days change', () => {
      render(
        <SolarTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      fireEvent.click(screen.getByTestId('toggle-all-days'))

      expect(mockOnChange).toHaveBeenCalledWith({
        solar_event: 'sunset',
        offset_minutes: 0,
        days_of_week: null,
      })
    })
  })

  describe('Accessibility', () => {
    it('links parent error to offset input via aria-describedby', () => {
      const errors = {
        offset_minutes: 'Server error: offset out of range',
      }

      render(
        <SolarTriggerForm onChange={mockOnChange} errors={errors} />,
      )

      const offsetInput = screen.getByLabelText('Offset in minutes')
      expect(offsetInput).toHaveAttribute('aria-invalid', 'true')
      expect(offsetInput).toHaveAttribute(
        'aria-describedby',
        'offset_minutes-error',
      )
    })

    it('links error message to offset input via aria-describedby', async () => {
      const user = userEvent.setup()
      render(
        <SolarTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const offsetInput = screen.getByLabelText('Offset in minutes')
      await user.clear(offsetInput)
      await user.type(offsetInput, '1441')

      await waitFor(() => {
        expect(offsetInput).toHaveAttribute('aria-invalid', 'true')
        expect(offsetInput).toHaveAttribute(
          'aria-describedby',
          'offset_minutes-error',
        )
      })
    })
  })
})

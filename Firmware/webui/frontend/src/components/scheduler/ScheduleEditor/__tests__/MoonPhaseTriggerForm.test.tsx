import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MoonPhaseTriggerForm from '../MoonPhaseTriggerForm'
import type { MoonPhaseTriggerValue } from '../MoonPhaseTriggerForm'
import { MOON_PHASES, SCHEDULE_LIMITS } from '../constants'

// ── Helpers ────────────────────────────────────────────────────────────

const defaultValue: MoonPhaseTriggerValue = {
  moon_phase: 'full',
  time_of_day: '20:00',
  offset_days: 0,
}

// ── Tests ──────────────────────────────────────────────────────────────

describe('MoonPhaseTriggerForm', () => {
  let mockOnChange: ReturnType<typeof vi.fn<(value: MoonPhaseTriggerValue) => void>>

  beforeEach(() => {
    mockOnChange = vi.fn<(value: MoonPhaseTriggerValue) => void>()
  })

  describe('Rendering', () => {
    it('renders with default values', () => {
      render(<MoonPhaseTriggerForm onChange={mockOnChange} />)

      expect(screen.getByText('Moon Phase Configuration')).toBeInTheDocument()
      expect(screen.getByLabelText(/moon phase/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/time of day/i)).toBeInTheDocument()
      expect(screen.getByLabelText('Offset in days')).toBeInTheDocument()
      expect(screen.getByText('Preview:')).toBeInTheDocument()
    })

    it('renders with provided value', () => {
      const value: MoonPhaseTriggerValue = {
        moon_phase: 'new',
        time_of_day: '21:30',
        offset_days: 2,
      }

      render(<MoonPhaseTriggerForm value={value} onChange={mockOnChange} />)

      expect(screen.getByLabelText(/moon phase/i)).toHaveValue('new')
      expect(screen.getByLabelText(/time of day/i)).toHaveValue('21:30')
      expect(screen.getByLabelText('Offset in days')).toHaveValue(2)
    })

    it('renders all moon phases in dropdown', () => {
      render(<MoonPhaseTriggerForm onChange={mockOnChange} />)

      const select = screen.getByLabelText(/moon phase/i) as HTMLSelectElement
      const options = Array.from(select.options).map((opt) => opt.value)

      MOON_PHASES.forEach((phase) => {
        expect(options).toContain(phase.value)
      })
    })
  })

  describe('Moon Phase Selection', () => {
    it('updates moon_phase on selection change', () => {
      render(
        <MoonPhaseTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      fireEvent.change(screen.getByLabelText(/moon phase/i), {
        target: { value: 'new' },
      })

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({ moon_phase: 'new' }),
      )
    })

    it('shows label for selected moon phase', () => {
      render(
        <MoonPhaseTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const fullMoonPhase = MOON_PHASES.find((p) => p.value === 'full')!
      expect(
        screen.getByRole('option', { name: fullMoonPhase.label }),
      ).toBeInTheDocument()
    })
  })

  describe('Time of Day Input', () => {
    it('updates time_of_day on input change', () => {
      render(
        <MoonPhaseTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      fireEvent.change(screen.getByLabelText(/time of day/i), {
        target: { value: '22:30' },
      })

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({ time_of_day: '22:30' }),
      )
    })

    it('has time input type', () => {
      render(<MoonPhaseTriggerForm onChange={mockOnChange} />)

      expect(screen.getByLabelText(/time of day/i)).toHaveAttribute(
        'type',
        'time',
      )
    })

    it('shows parent error when provided', () => {
      const errors = { time_of_day: 'Time must be in HH:MM format' }

      render(
        <MoonPhaseTriggerForm onChange={mockOnChange} errors={errors} />,
      )

      expect(screen.getByText(errors.time_of_day)).toBeInTheDocument()
    })
  })

  describe('Offset Days Input', () => {
    it('updates offset_days on input change', async () => {
      const user = userEvent.setup()
      render(
        <MoonPhaseTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const offsetInput = screen.getByLabelText('Offset in days')
      await user.clear(offsetInput)
      await user.type(offsetInput, '3')

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({ offset_days: 3 }),
        )
      })
    })

    it('allows negative offset values', async () => {
      const user = userEvent.setup()
      render(
        <MoonPhaseTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const offsetInput = screen.getByLabelText('Offset in days')
      await user.clear(offsetInput)
      await user.type(offsetInput, '-3')

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({ offset_days: -3 }),
        )
      })
    })

    it('has min and max offset attributes', () => {
      render(<MoonPhaseTriggerForm onChange={mockOnChange} />)

      const offsetInput = screen.getByLabelText('Offset in days')
      expect(offsetInput).toHaveAttribute(
        'min',
        String(-SCHEDULE_LIMITS.MAX_OFFSET_DAYS),
      )
      expect(offsetInput).toHaveAttribute(
        'max',
        String(SCHEDULE_LIMITS.MAX_OFFSET_DAYS),
      )
    })

    it('shows error message for invalid offset', async () => {
      const user = userEvent.setup()
      render(
        <MoonPhaseTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const offsetInput = screen.getByLabelText('Offset in days')
      await user.clear(offsetInput)
      await user.type(offsetInput, '8')

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })
    })

    it('shows parent error when provided', () => {
      const errors = { offset_days: 'Offset must be between -7 and 7 days' }

      render(
        <MoonPhaseTriggerForm onChange={mockOnChange} errors={errors} />,
      )

      expect(screen.getByText(errors.offset_days)).toBeInTheDocument()
    })

    it('does not propagate invalid offset to parent', async () => {
      const user = userEvent.setup()
      render(
        <MoonPhaseTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const offsetInput = screen.getByLabelText('Offset in days')
      await user.clear(offsetInput)
      await user.type(offsetInput, '8')

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })

      expect(mockOnChange).not.toHaveBeenCalledWith(
        expect.objectContaining({ offset_days: 8 }),
      )
    })

    it('shows error and does not propagate when input is cleared', async () => {
      const user = userEvent.setup()
      render(
        <MoonPhaseTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const offsetInput = screen.getByLabelText('Offset in days')
      await user.clear(offsetInput)

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })

      expect(mockOnChange).not.toHaveBeenCalledWith(
        expect.objectContaining({ offset_days: NaN }),
      )
    })
  })

  describe('Quick Offset Presets', () => {
    it('renders quick offset preset buttons', () => {
      render(<MoonPhaseTriggerForm onChange={mockOnChange} />)

      expect(screen.getByLabelText('Set offset to -1 day')).toBeInTheDocument()
      expect(screen.getByLabelText('Set offset to 0 days')).toBeInTheDocument()
      expect(screen.getByLabelText('Set offset to 1 day')).toBeInTheDocument()
    })

    it('sets offset to -1 when -1 day preset clicked', () => {
      render(
        <MoonPhaseTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      fireEvent.click(screen.getByLabelText('Set offset to -1 day'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...defaultValue,
        offset_days: -1,
      })
    })

    it('sets offset to 0 when "No offset" preset clicked', () => {
      const value = { ...defaultValue, offset_days: 2 }

      render(
        <MoonPhaseTriggerForm value={value} onChange={mockOnChange} />,
      )

      fireEvent.click(screen.getByLabelText('Set offset to 0 days'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        offset_days: 0,
      })
    })

    it('sets offset to +1 when +1 day preset clicked', () => {
      render(
        <MoonPhaseTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      fireEvent.click(screen.getByLabelText('Set offset to 1 day'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...defaultValue,
        offset_days: 1,
      })
    })

    it('highlights selected preset', () => {
      const value = { ...defaultValue, offset_days: 1 }

      render(
        <MoonPhaseTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(screen.getByLabelText('Set offset to 1 day')).toHaveClass(
        'bg-blue-500',
      )
    })
  })

  describe('Preview Text Generation', () => {
    it('generates preview for moon phase without offset', () => {
      render(
        <MoonPhaseTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      expect(screen.getByText('On Full Moon at 20:00')).toBeInTheDocument()
    })

    it('generates preview with positive offset', () => {
      const value = { ...defaultValue, offset_days: 2 }

      render(
        <MoonPhaseTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText('2 days after Full Moon at 20:00'),
      ).toBeInTheDocument()
    })

    it('generates preview with negative offset', () => {
      const value = { ...defaultValue, offset_days: -3 }

      render(
        <MoonPhaseTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText('3 days before Full Moon at 20:00'),
      ).toBeInTheDocument()
    })

    it('generates preview with singular day offset', () => {
      const value: MoonPhaseTriggerValue = {
        moon_phase: 'new',
        time_of_day: '22:00',
        offset_days: 1,
      }

      render(
        <MoonPhaseTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText('1 day after New Moon at 22:00'),
      ).toBeInTheDocument()
    })

    it('generates preview for different moon phases', () => {
      const value: MoonPhaseTriggerValue = {
        moon_phase: 'waxing_crescent',
        time_of_day: '19:30',
        offset_days: 0,
      }

      render(
        <MoonPhaseTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText('On Waxing Crescent at 19:30'),
      ).toBeInTheDocument()
    })
  })

  describe('Disabled State', () => {
    it('disables moon phase select when disabled prop is true', () => {
      render(
        <MoonPhaseTriggerForm onChange={mockOnChange} disabled={true} />,
      )

      expect(screen.getByLabelText(/moon phase/i)).toBeDisabled()
    })

    it('disables time input when disabled prop is true', () => {
      render(
        <MoonPhaseTriggerForm onChange={mockOnChange} disabled={true} />,
      )

      expect(screen.getByLabelText(/time of day/i)).toBeDisabled()
    })

    it('disables offset input when disabled prop is true', () => {
      render(
        <MoonPhaseTriggerForm onChange={mockOnChange} disabled={true} />,
      )

      expect(screen.getByLabelText('Offset in days')).toBeDisabled()
    })

    it('disables preset buttons when disabled prop is true', () => {
      render(
        <MoonPhaseTriggerForm onChange={mockOnChange} disabled={true} />,
      )

      expect(screen.getByLabelText('Set offset to 0 days')).toBeDisabled()
    })

    it('does not disable inputs when disabled prop is false', () => {
      render(
        <MoonPhaseTriggerForm onChange={mockOnChange} disabled={false} />,
      )

      expect(screen.getByLabelText(/moon phase/i)).not.toBeDisabled()
      expect(screen.getByLabelText(/time of day/i)).not.toBeDisabled()
      expect(screen.getByLabelText('Offset in days')).not.toBeDisabled()
    })
  })

  describe('Prop Sync', () => {
    it('updates form when value prop changes externally', () => {
      const { rerender } = render(
        <MoonPhaseTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const newValue: MoonPhaseTriggerValue = {
        moon_phase: 'new',
        time_of_day: '22:00',
        offset_days: 3,
      }
      rerender(
        <MoonPhaseTriggerForm value={newValue} onChange={mockOnChange} />,
      )

      expect(screen.getByLabelText(/moon phase/i)).toHaveValue('new')
      expect(screen.getByLabelText(/time of day/i)).toHaveValue('22:00')
      expect(screen.getByLabelText('Offset in days')).toHaveValue(3)
    })

    it('does not reset form when value prop is unchanged', async () => {
      const user = userEvent.setup()
      const value: MoonPhaseTriggerValue = {
        moon_phase: 'full',
        time_of_day: '20:00',
        offset_days: 3,
      }

      const { rerender } = render(
        <MoonPhaseTriggerForm value={value} onChange={mockOnChange} />,
      )

      const offsetInput = screen.getByLabelText('Offset in days')
      await user.clear(offsetInput)
      await user.type(offsetInput, '5')

      // Wait for propagation to settle so lastPropagatedRef is updated
      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({ offset_days: 5 }),
        )
      })

      // Re-render with same value (e.g., parent re-renders for unrelated reason)
      rerender(
        <MoonPhaseTriggerForm value={value} onChange={mockOnChange} />,
      )

      // The form should still show the user's typed value, not reset to 3
      expect(offsetInput).toHaveValue(5)
    })
  })

  describe('onChange Callback', () => {
    it('calls onChange with complete trigger object when moon phase changes', () => {
      const value: MoonPhaseTriggerValue = {
        moon_phase: 'full',
        time_of_day: '20:00',
        offset_days: 2,
      }

      render(
        <MoonPhaseTriggerForm value={value} onChange={mockOnChange} />,
      )

      fireEvent.change(screen.getByLabelText(/moon phase/i), {
        target: { value: 'new' },
      })

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          moon_phase: 'new',
          time_of_day: '20:00',
          offset_days: 2,
        }),
      )
    })

    it('calls onChange with complete trigger object when time changes', () => {
      render(
        <MoonPhaseTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      fireEvent.change(screen.getByLabelText(/time of day/i), {
        target: { value: '23:45' },
      })

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          moon_phase: 'full',
          time_of_day: '23:45',
          offset_days: 0,
        }),
      )
    })
  })

  describe('Accessibility', () => {
    it('links parent error to offset input via aria-describedby', () => {
      const errors = { offset_days: 'Server error: offset out of range' }

      render(
        <MoonPhaseTriggerForm onChange={mockOnChange} errors={errors} />,
      )

      const offsetInput = screen.getByLabelText('Offset in days')
      expect(offsetInput).toHaveAttribute('aria-invalid', 'true')
      expect(offsetInput).toHaveAttribute(
        'aria-describedby',
        'offset_days-error',
      )
    })

    it('links parent error to time input via aria-describedby', () => {
      const errors = { time_of_day: 'Invalid time' }

      render(
        <MoonPhaseTriggerForm onChange={mockOnChange} errors={errors} />,
      )

      const timeInput = screen.getByLabelText(/time of day/i)
      expect(timeInput).toHaveAttribute('aria-invalid', 'true')
      expect(timeInput).toHaveAttribute(
        'aria-describedby',
        'time_of_day-error',
      )
    })

    it('links parent error to moon phase select via aria-describedby', () => {
      const errors = { moon_phase: 'Server error: invalid phase' }

      render(
        <MoonPhaseTriggerForm onChange={mockOnChange} errors={errors} />,
      )

      const select = screen.getByLabelText(/moon phase/i)
      expect(select).toHaveAttribute('aria-invalid', 'true')
      expect(select).toHaveAttribute(
        'aria-describedby',
        'moon_phase-error',
      )
    })

    it('links error message to offset input via aria-describedby', async () => {
      const user = userEvent.setup()
      render(
        <MoonPhaseTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const offsetInput = screen.getByLabelText('Offset in days')
      await user.clear(offsetInput)
      await user.type(offsetInput, '8')

      await waitFor(() => {
        expect(offsetInput).toHaveAttribute('aria-invalid', 'true')
        expect(offsetInput).toHaveAttribute(
          'aria-describedby',
          'offset_days-error',
        )
      })
    })
  })
})

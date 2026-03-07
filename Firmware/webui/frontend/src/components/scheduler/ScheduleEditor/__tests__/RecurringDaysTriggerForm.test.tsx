import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import RecurringDaysTriggerForm from '../RecurringDaysTriggerForm'
import type { RecurringDaysTriggerValue } from '../RecurringDaysTriggerForm'

// -- Helpers ----------------------------------------------------------------

const defaultValue: RecurringDaysTriggerValue = {
  days: [0, 5, 6],
  time: '20:00',
}

// -- Tests ------------------------------------------------------------------

describe('RecurringDaysTriggerForm', () => {
  let mockOnChange: ReturnType<typeof vi.fn<(value: RecurringDaysTriggerValue) => void>>

  beforeEach(() => {
    mockOnChange = vi.fn<(value: RecurringDaysTriggerValue) => void>()
  })

  describe('Rendering', () => {
    it('renders with default values', () => {
      render(<RecurringDaysTriggerForm onChange={mockOnChange} />)

      expect(screen.getByText('Recurring Days Configuration')).toBeInTheDocument()
      expect(screen.getByLabelText(/time of day/i)).toBeInTheDocument()
      expect(screen.getByText('Preview:')).toBeInTheDocument()
    })

    it('renders with provided value', () => {
      const value: RecurringDaysTriggerValue = {
        days: [1, 3],
        time: '18:30',
      }

      render(<RecurringDaysTriggerForm value={value} onChange={mockOnChange} />)

      const timeInput = screen.getByLabelText(/time of day/i)
      expect(timeInput).toHaveValue('18:30')
    })

    it('renders all seven day buttons', () => {
      render(<RecurringDaysTriggerForm onChange={mockOnChange} />)

      expect(screen.getByLabelText('Monday')).toBeInTheDocument()
      expect(screen.getByLabelText('Tuesday')).toBeInTheDocument()
      expect(screen.getByLabelText('Wednesday')).toBeInTheDocument()
      expect(screen.getByLabelText('Thursday')).toBeInTheDocument()
      expect(screen.getByLabelText('Friday')).toBeInTheDocument()
      expect(screen.getByLabelText('Saturday')).toBeInTheDocument()
      expect(screen.getByLabelText('Sunday')).toBeInTheDocument()
    })

    it('highlights selected days', () => {
      const value: RecurringDaysTriggerValue = {
        days: [0, 5],
        time: '20:00',
      }

      render(<RecurringDaysTriggerForm value={value} onChange={mockOnChange} />)

      const monday = screen.getByLabelText('Monday')
      const saturday = screen.getByLabelText('Saturday')
      const tuesday = screen.getByLabelText('Tuesday')

      expect(monday).toHaveClass('bg-blue-500')
      expect(saturday).toHaveClass('bg-blue-500')
      expect(tuesday).not.toHaveClass('bg-blue-500')
    })
  })

  describe('Day Toggle', () => {
    it('adds a day when unselected day is clicked', () => {
      const value: RecurringDaysTriggerValue = {
        days: [0, 5],
        time: '20:00',
      }

      render(<RecurringDaysTriggerForm value={value} onChange={mockOnChange} />)

      const wednesday = screen.getByLabelText('Wednesday')
      fireEvent.click(wednesday)

      expect(mockOnChange).toHaveBeenCalledWith({
        days: [0, 2, 5],
        time: '20:00',
      })
    })

    it('removes a day when selected day is clicked', () => {
      const value: RecurringDaysTriggerValue = {
        days: [0, 5, 6],
        time: '20:00',
      }

      render(<RecurringDaysTriggerForm value={value} onChange={mockOnChange} />)

      const saturday = screen.getByLabelText('Saturday')
      fireEvent.click(saturday)

      expect(mockOnChange).toHaveBeenCalledWith({
        days: [0, 6],
        time: '20:00',
      })
    })

    it('does not remove the last selected day', () => {
      const value: RecurringDaysTriggerValue = {
        days: [3],
        time: '20:00',
      }

      render(<RecurringDaysTriggerForm value={value} onChange={mockOnChange} />)

      const thursday = screen.getByLabelText('Thursday')
      fireEvent.click(thursday)

      expect(mockOnChange).not.toHaveBeenCalled()
    })

    it('disables the last remaining selected day button', () => {
      const value: RecurringDaysTriggerValue = {
        days: [3],
        time: '20:00',
      }

      render(<RecurringDaysTriggerForm value={value} onChange={mockOnChange} />)

      const thursday = screen.getByLabelText('Thursday')
      expect(thursday).toBeDisabled()
    })
  })

  describe('Time Input (react-hook-form + Zod)', () => {
    it('propagates valid time change to parent', async () => {
      const value: RecurringDaysTriggerValue = {
        days: [0, 5, 6],
        time: '20:00',
      }

      render(<RecurringDaysTriggerForm value={value} onChange={mockOnChange} />)

      const timeInput = screen.getByLabelText(/time of day/i)
      fireEvent.change(timeInput, { target: { value: '18:30' } })

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith({
          ...value,
          time: '18:30',
        })
      })
    })

    it('accepts midnight (00:00)', async () => {
      const value: RecurringDaysTriggerValue = {
        days: [0],
        time: '20:00',
      }

      render(<RecurringDaysTriggerForm value={value} onChange={mockOnChange} />)

      const timeInput = screen.getByLabelText(/time of day/i)
      fireEvent.change(timeInput, { target: { value: '00:00' } })

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith({
          ...value,
          time: '00:00',
        })
      })
    })

    it('shows Zod error for invalid time format', async () => {
      const user = userEvent.setup()

      render(
        <RecurringDaysTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const timeInput = screen.getByLabelText(/time of day/i)
      await user.clear(timeInput)
      await user.type(timeInput, 'invalid')

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })
    })

    it('does not propagate invalid values to parent', async () => {
      const user = userEvent.setup()

      render(
        <RecurringDaysTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const timeInput = screen.getByLabelText(/time of day/i)
      await user.clear(timeInput)
      await user.type(timeInput, 'bad')

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })

      expect(mockOnChange).not.toHaveBeenCalledWith(
        expect.objectContaining({ time: 'bad' }),
      )
    })

    it('shows parent-provided error message for time', () => {
      const errors = {
        time: 'Time must be in HH:MM format',
      }

      render(
        <RecurringDaysTriggerForm onChange={mockOnChange} errors={errors} />,
      )

      expect(screen.getByText(errors.time)).toBeInTheDocument()
    })

    it('shows parent-provided error message for days', () => {
      const errors = {
        days: 'At least one day is required',
      }

      render(
        <RecurringDaysTriggerForm onChange={mockOnChange} errors={errors} />,
      )

      expect(screen.getByText(errors.days)).toBeInTheDocument()
    })
  })

  describe('Quick Time Presets', () => {
    it('renders quick time preset buttons', () => {
      render(<RecurringDaysTriggerForm onChange={mockOnChange} />)

      expect(screen.getByLabelText('Set time to 06:00')).toBeInTheDocument()
      expect(screen.getByLabelText('Set time to 20:00')).toBeInTheDocument()
      expect(screen.getByLabelText('Set time to 21:00')).toBeInTheDocument()
      expect(screen.getByLabelText('Set time to 22:00')).toBeInTheDocument()
    })

    it('sets time when preset clicked', () => {
      const value: RecurringDaysTriggerValue = {
        days: [0, 5, 6],
        time: '20:00',
      }

      render(<RecurringDaysTriggerForm value={value} onChange={mockOnChange} />)

      const preset6AM = screen.getByLabelText('Set time to 06:00')
      fireEvent.click(preset6AM)

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        time: '06:00',
      })
    })

    it('highlights selected preset', () => {
      const value: RecurringDaysTriggerValue = {
        days: [0],
        time: '20:00',
      }

      render(<RecurringDaysTriggerForm value={value} onChange={mockOnChange} />)

      const preset8PM = screen.getByLabelText('Set time to 20:00')
      expect(preset8PM).toHaveClass('bg-blue-500')
    })

    it('does not highlight non-selected presets', () => {
      const value: RecurringDaysTriggerValue = {
        days: [0],
        time: '20:00',
      }

      render(<RecurringDaysTriggerForm value={value} onChange={mockOnChange} />)

      const preset6AM = screen.getByLabelText('Set time to 06:00')
      expect(preset6AM).toHaveClass('bg-gray-100')
      expect(preset6AM).not.toHaveClass('bg-blue-500')
    })
  })

  describe('Preview Text Generation', () => {
    it('generates preview with days and time', () => {
      const value: RecurringDaysTriggerValue = {
        days: [0, 5, 6],
        time: '20:00',
      }

      render(<RecurringDaysTriggerForm value={value} onChange={mockOnChange} />)

      expect(screen.getByText('At 20:00 on Mon, Sat, Sun')).toBeInTheDocument()
    })

    it('generates preview for all days', () => {
      const value: RecurringDaysTriggerValue = {
        days: [0, 1, 2, 3, 4, 5, 6],
        time: '08:00',
      }

      render(<RecurringDaysTriggerForm value={value} onChange={mockOnChange} />)

      expect(screen.getByText('At 08:00 on every day')).toBeInTheDocument()
    })

    it('generates preview for single day', () => {
      const value: RecurringDaysTriggerValue = {
        days: [4],
        time: '21:00',
      }

      render(<RecurringDaysTriggerForm value={value} onChange={mockOnChange} />)

      expect(screen.getByText('At 21:00 on Fri')).toBeInTheDocument()
    })
  })

  describe('Disabled State', () => {
    it('disables time input when disabled prop is true', () => {
      render(<RecurringDaysTriggerForm onChange={mockOnChange} disabled={true} />)

      const timeInput = screen.getByLabelText(/time of day/i)
      expect(timeInput).toBeDisabled()
    })

    it('disables day buttons when disabled prop is true', () => {
      render(<RecurringDaysTriggerForm onChange={mockOnChange} disabled={true} />)

      const monday = screen.getByLabelText('Monday')
      expect(monday).toBeDisabled()
    })

    it('disables preset buttons when disabled prop is true', () => {
      render(<RecurringDaysTriggerForm onChange={mockOnChange} disabled={true} />)

      const preset8PM = screen.getByLabelText('Set time to 20:00')
      expect(preset8PM).toBeDisabled()
    })

    it('does not disable inputs when disabled prop is false', () => {
      render(<RecurringDaysTriggerForm onChange={mockOnChange} disabled={false} />)

      const timeInput = screen.getByLabelText(/time of day/i)
      expect(timeInput).not.toBeDisabled()
    })
  })

  describe('Dark Mode Styling', () => {
    it('applies dark mode classes to time input', () => {
      render(<RecurringDaysTriggerForm onChange={mockOnChange} />)

      const timeInput = screen.getByLabelText(/time of day/i)
      expect(timeInput).toHaveClass('dark:bg-gray-800', 'dark:text-white', 'dark:border-gray-600')
    })

    it('applies dark mode classes to header', () => {
      render(<RecurringDaysTriggerForm onChange={mockOnChange} />)

      const header = screen.getByText('Recurring Days Configuration')
      expect(header).toHaveClass('dark:text-white')
    })

    it('applies dark mode classes to non-selected preset buttons', () => {
      render(<RecurringDaysTriggerForm onChange={mockOnChange} />)

      const preset6AM = screen.getByLabelText('Set time to 06:00')
      expect(preset6AM).toHaveClass('dark:bg-gray-700', 'dark:text-gray-300')
    })

    it('applies dark mode classes to preview text', () => {
      const value: RecurringDaysTriggerValue = {
        days: [0, 5, 6],
        time: '20:00',
      }

      render(<RecurringDaysTriggerForm value={value} onChange={mockOnChange} />)

      const previewText = screen.getByText('At 20:00 on Mon, Sat, Sun')
      expect(previewText).toHaveClass('dark:text-gray-300', 'dark:bg-gray-800')
    })
  })

  describe('onChange Callback', () => {
    it('calls onChange with complete value when time changes', async () => {
      const value: RecurringDaysTriggerValue = {
        days: [0, 1, 2],
        time: '12:00',
      }

      render(<RecurringDaysTriggerForm value={value} onChange={mockOnChange} />)

      const timeInput = screen.getByLabelText(/time of day/i)
      fireEvent.change(timeInput, { target: { value: '18:30' } })

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith({
          days: [0, 1, 2],
          time: '18:30',
        })
      })
    })

    it('calls onChange with complete value when preset clicked', () => {
      const value: RecurringDaysTriggerValue = {
        days: [0, 5, 6],
        time: '20:00',
      }

      render(<RecurringDaysTriggerForm value={value} onChange={mockOnChange} />)

      const preset6AM = screen.getByLabelText('Set time to 06:00')
      fireEvent.click(preset6AM)

      expect(mockOnChange).toHaveBeenCalledWith({
        days: [0, 5, 6],
        time: '06:00',
      })
    })

    it('calls onChange with complete value when day toggled', () => {
      const value: RecurringDaysTriggerValue = {
        days: [0, 5],
        time: '20:00',
      }

      render(<RecurringDaysTriggerForm value={value} onChange={mockOnChange} />)

      const wednesday = screen.getByLabelText('Wednesday')
      fireEvent.click(wednesday)

      expect(mockOnChange).toHaveBeenCalledWith({
        days: [0, 2, 5],
        time: '20:00',
      })
    })
  })

  describe('Prop sync (external value changes)', () => {
    it('updates input when value prop changes externally', () => {
      const value: RecurringDaysTriggerValue = { ...defaultValue, time: '12:00' }

      const { rerender } = render(
        <RecurringDaysTriggerForm value={value} onChange={mockOnChange} />,
      )

      rerender(
        <RecurringDaysTriggerForm
          value={{ ...value, time: '18:00' }}
          onChange={mockOnChange}
        />,
      )

      const input = screen.getByLabelText(/time of day/i)
      expect(input).toHaveValue('18:00')
    })
  })
})

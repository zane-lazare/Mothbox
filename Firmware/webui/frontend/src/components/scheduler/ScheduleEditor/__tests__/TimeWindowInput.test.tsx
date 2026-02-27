import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TimeWindowInput from '../TimeWindowInput'
import type { TimeWindowValue } from '../TimeWindowInput'
import { SOLAR_EVENTS } from '../constants'

describe('TimeWindowInput', () => {
  let mockOnChange: ReturnType<typeof vi.fn<(value: TimeWindowValue) => void>>

  const defaultValue: TimeWindowValue = {
    start_time: '21:00',
    end_time: '05:00',
    start_offset_minutes: 0,
    end_offset_minutes: 0,
  }

  beforeEach(() => {
    mockOnChange = vi.fn<(value: TimeWindowValue) => void>()
  })

  /**
   * Build props with the current mockOnChange.
   * Must be called inside a test (after beforeEach has run).
   */
  function props(overrides?: {
    value?: TimeWindowValue
    showSolarEvents?: boolean
    disabled?: boolean
    errors?: Record<string, string>
  }) {
    return {
      value: defaultValue,
      onChange: mockOnChange,
      ...overrides,
    }
  }

  describe('Rendering', () => {
    it('should render with fixed time values', () => {
      render(<TimeWindowInput {...props()} />)

      expect(screen.getByLabelText(/start time \(fixed\)/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/end time \(fixed\)/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/start time \(fixed\)/i)).toHaveValue('21:00')
      expect(screen.getByLabelText(/end time \(fixed\)/i)).toHaveValue('05:00')
    })

    it('should render with solar event values', () => {
      render(
        <TimeWindowInput
          {...props({
            value: {
              start_time: 'sunset',
              end_time: 'sunrise',
              start_offset_minutes: 30,
              end_offset_minutes: -30,
            },
          })}
        />,
      )

      expect(screen.getByLabelText(/start time \(solar event\)/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/end time \(solar event\)/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/start time \(solar event\)/i)).toHaveValue('sunset')
      expect(screen.getByLabelText(/end time \(solar event\)/i)).toHaveValue('sunrise')
    })

    it('should render solar event type toggles when showSolarEvents is true', () => {
      render(<TimeWindowInput {...props({ showSolarEvents: true })} />)

      const radios = screen.getAllByRole('radio')
      expect(radios.length).toBeGreaterThan(0)
      expect(screen.getAllByText(/fixed time/i)).toHaveLength(2)
      expect(screen.getAllByText(/solar event/i)).toHaveLength(2)
    })

    it('should not render solar event type toggles when showSolarEvents is false', () => {
      render(<TimeWindowInput {...props({ showSolarEvents: false })} />)

      expect(screen.queryByText(/solar event/i)).not.toBeInTheDocument()
      // Should only show time inputs without type selection
      expect(screen.getByLabelText(/start time \(fixed\)/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/end time \(fixed\)/i)).toBeInTheDocument()
    })

    it('should show preview text for solar events', () => {
      render(
        <TimeWindowInput
          {...props({
            value: {
              start_time: 'sunset',
              end_time: 'sunrise',
              start_offset_minutes: 30,
              end_offset_minutes: -30,
            },
          })}
        />,
      )

      expect(screen.getByText(/30 minutes after sunset/i)).toBeInTheDocument()
      expect(screen.getByText(/30 minutes before sunrise/i)).toBeInTheDocument()
    })

    it('should show "at" preview for zero offset', () => {
      render(
        <TimeWindowInput
          {...props({
            value: {
              start_time: 'sunset',
              end_time: 'sunrise',
              start_offset_minutes: 0,
              end_offset_minutes: 0,
            },
          })}
        />,
      )

      expect(screen.getByText(/at sunset/i)).toBeInTheDocument()
      expect(screen.getByText(/at sunrise/i)).toBeInTheDocument()
    })

    it('should show error messages when provided', () => {
      render(
        <TimeWindowInput
          {...props({
            errors: {
              start_time: 'Start time is required',
              end_time: 'End time is required',
              general: 'Invalid time window',
            },
          })}
        />,
      )

      expect(screen.getByText('Start time is required')).toBeInTheDocument()
      expect(screen.getByText('End time is required')).toBeInTheDocument()
      expect(screen.getByText('Invalid time window')).toBeInTheDocument()
    })

    it('should respect disabled state', () => {
      render(<TimeWindowInput {...props({ disabled: true })} />)

      const startTimeInput = screen.getByLabelText(/start time \(fixed\)/i)
      const endTimeInput = screen.getByLabelText(/end time \(fixed\)/i)

      expect(startTimeInput).toBeDisabled()
      expect(endTimeInput).toBeDisabled()
    })

    it('should apply dark mode styling', () => {
      document.documentElement.classList.add('dark')
      render(<TimeWindowInput {...props()} />)

      const startTimeInput = screen.getByLabelText(/start time \(fixed\)/i)
      expect(startTimeInput).toHaveClass('dark:bg-gray-800')

      document.documentElement.classList.remove('dark')
    })
  })

  describe('Time Type Switching', () => {
    it('should switch from fixed time to solar event for start time', async () => {
      const user = userEvent.setup()
      render(<TimeWindowInput {...props()} />)

      // Initially fixed time
      expect(screen.getByLabelText(/start time \(fixed\)/i)).toBeInTheDocument()

      // Click solar event radio
      const radios = screen.getAllByRole('radio')
      const startSolarRadio = radios.find(
        (radio) =>
          !(radio as HTMLInputElement).checked &&
          radio.parentElement?.textContent?.includes('Solar Event'),
      )
      await user.click(startSolarRadio!)

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({
            start_time: SOLAR_EVENTS[0].value,
            start_offset_minutes: 0,
          }),
        )
      })
    })

    it('should switch from solar event to fixed time for start time', async () => {
      const user = userEvent.setup()
      render(
        <TimeWindowInput
          {...props({
            value: {
              start_time: 'sunset',
              end_time: '05:00',
              start_offset_minutes: 30,
              end_offset_minutes: 0,
            },
          })}
        />,
      )

      // Initially solar event
      expect(screen.getByLabelText(/start time \(solar event\)/i)).toBeInTheDocument()

      // Click fixed time radio for start
      const radios = screen.getAllByRole('radio')
      const startFixedRadio = radios[0] // First radio is start fixed time
      await user.click(startFixedRadio)

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({
            start_time: '',
            start_offset_minutes: 0,
          }),
        )
      })
    })

    it('should switch from fixed time to solar event for end time', async () => {
      const user = userEvent.setup()
      render(<TimeWindowInput {...props()} />)

      // Click solar event radio for end time
      const radios = screen.getAllByRole('radio')
      // End time solar radio is the 4th radio (start fixed, start solar, end fixed, end solar)
      const endSolarRadio = radios[3]
      await user.click(endSolarRadio)

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({
            end_time: SOLAR_EVENTS[0].value,
            end_offset_minutes: 0,
          }),
        )
      })
    })

    it('should switch from solar event to fixed time for end time', async () => {
      const user = userEvent.setup()
      render(
        <TimeWindowInput
          {...props({
            value: {
              start_time: '21:00',
              end_time: 'sunrise',
              start_offset_minutes: 0,
              end_offset_minutes: -30,
            },
          })}
        />,
      )

      // Click fixed time radio for end
      const radios = screen.getAllByRole('radio')
      const endFixedRadio = radios[2] // Third radio is end fixed time
      await user.click(endFixedRadio)

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({
            end_time: '',
            end_offset_minutes: 0,
          }),
        )
      })
    })
  })

  describe('Fixed Time Input', () => {
    it('should update start_time on change', async () => {
      const user = userEvent.setup()
      render(<TimeWindowInput {...props()} />)

      const startTimeInput = screen.getByLabelText(/start time \(fixed\)/i)

      // Click and type to update (testing library behavior varies by browser)
      await user.click(startTimeInput)
      await user.keyboard('{Control>}a{/Control}') // Select all
      await user.keyboard('22:30')

      // RHF validates async — use waitFor for onChange
      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalled()
        const calls = mockOnChange.mock.calls
        const hasTimeUpdate = calls.some(
          ([value]: [TimeWindowValue]) =>
            value.start_time && value.start_time !== defaultValue.start_time,
        )
        expect(hasTimeUpdate).toBe(true)
      })
    })

    it('should update end_time on change', async () => {
      const user = userEvent.setup()
      render(<TimeWindowInput {...props()} />)

      const endTimeInput = screen.getByLabelText(/end time \(fixed\)/i)

      // Click and type to update (testing library behavior varies by browser)
      await user.click(endTimeInput)
      await user.keyboard('{Control>}a{/Control}') // Select all
      await user.keyboard('06:30')

      // RHF validates async — use waitFor for onChange
      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalled()
        const calls = mockOnChange.mock.calls
        const hasTimeUpdate = calls.some(
          ([value]: [TimeWindowValue]) =>
            value.end_time && value.end_time !== defaultValue.end_time,
        )
        expect(hasTimeUpdate).toBe(true)
      })
    })

    it('should validate TIME_FORMAT_REGEX for fixed times', () => {
      const { rerender } = render(
        <TimeWindowInput
          {...props({
            value: {
              start_time: '23:59',
              end_time: '00:00',
              start_offset_minutes: 0,
              end_offset_minutes: 0,
            },
          })}
        />,
      )

      // Should show fixed time inputs for valid HH:MM format
      expect(screen.getByLabelText(/start time \(fixed\)/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/end time \(fixed\)/i)).toBeInTheDocument()

      // Invalid format should be treated as solar event
      rerender(
        <TimeWindowInput
          {...props({
            value: {
              start_time: 'sunset',
              end_time: '25:00', // Invalid hours
              start_offset_minutes: 0,
              end_offset_minutes: 0,
            },
          })}
        />,
      )

      // Should show solar event input for start (not HH:MM format)
      expect(screen.getByLabelText(/start time \(solar event\)/i)).toBeInTheDocument()
    })
  })

  describe('Solar Event Input', () => {
    const solarValue: TimeWindowValue = {
      start_time: 'sunset',
      end_time: 'sunrise',
      start_offset_minutes: 30,
      end_offset_minutes: -30,
    }

    it('should update start solar event on change', async () => {
      const user = userEvent.setup()
      render(<TimeWindowInput {...props({ value: solarValue })} />)

      const startEventSelect = screen.getByLabelText(/start time \(solar event\)/i)
      await user.selectOptions(startEventSelect, 'civil_dusk')

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({
            start_time: 'civil_dusk',
          }),
        )
      })
    })

    it('should update end solar event on change', async () => {
      const user = userEvent.setup()
      render(<TimeWindowInput {...props({ value: solarValue })} />)

      const endEventSelect = screen.getByLabelText(/end time \(solar event\)/i)
      await user.selectOptions(endEventSelect, 'civil_dawn')

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({
            end_time: 'civil_dawn',
          }),
        )
      })
    })

    it('should update start offset value', async () => {
      const user = userEvent.setup()

      render(
        <TimeWindowInput
          {...props({
            value: {
              start_time: 'sunset',
              end_time: 'sunrise',
              start_offset_minutes: 0,
              end_offset_minutes: 0,
            },
          })}
        />,
      )

      const startOffsetInput = screen.getByLabelText(/start time offset/i)

      // Use fireEvent for more predictable input behavior
      await user.click(startOffsetInput)
      await user.keyboard('{Control>}a{/Control}') // Select all
      await user.keyboard('60')

      // Check that onChange was called and offset was updated
      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalled()
        // Check that at least one call has the offset set to a number
        const calls = mockOnChange.mock.calls
        const hasOffsetUpdate = calls.some(
          ([value]: [TimeWindowValue]) =>
            typeof value.start_offset_minutes === 'number' &&
            value.start_offset_minutes !== 0,
        )
        expect(hasOffsetUpdate).toBe(true)
      })
    })

    it('should update end offset value', async () => {
      const user = userEvent.setup()

      render(
        <TimeWindowInput
          {...props({
            value: {
              start_time: 'sunset',
              end_time: 'sunrise',
              start_offset_minutes: 0,
              end_offset_minutes: 0,
            },
          })}
        />,
      )

      const endOffsetInput = screen.getByLabelText(/end time offset/i)

      // Use keyboard for more predictable input behavior
      await user.click(endOffsetInput)
      await user.keyboard('{Control>}a{/Control}') // Select all
      await user.keyboard('-60')

      // Check that onChange was called and offset was updated
      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalled()
        // Check that at least one call has the offset set to a negative number
        const calls = mockOnChange.mock.calls
        const hasOffsetUpdate = calls.some(
          ([value]: [TimeWindowValue]) =>
            typeof value.end_offset_minutes === 'number' &&
            value.end_offset_minutes !== 0,
        )
        expect(hasOffsetUpdate).toBe(true)
      })
    })

    it('should enforce offset range -120 to +120', () => {
      render(<TimeWindowInput {...props({ value: solarValue })} />)

      const startOffsetInput = screen.getByLabelText(/start time offset/i)
      const endOffsetInput = screen.getByLabelText(/end time offset/i)

      expect(startOffsetInput).toHaveAttribute('min', '-120')
      expect(startOffsetInput).toHaveAttribute('max', '120')
      expect(endOffsetInput).toHaveAttribute('min', '-120')
      expect(endOffsetInput).toHaveAttribute('max', '120')
    })

    it('should display all solar events in dropdown', () => {
      render(<TimeWindowInput {...props({ value: solarValue })} />)

      const startEventSelect = screen.getByLabelText(
        /start time \(solar event\)/i,
      ) as HTMLSelectElement
      const options = Array.from(startEventSelect.options).map((opt) => opt.value)

      SOLAR_EVENTS.forEach((event) => {
        expect(options).toContain(event.value)
      })
    })

    it('should show preview with singular "minute"', () => {
      render(
        <TimeWindowInput
          {...props({
            value: {
              start_time: 'sunset',
              end_time: 'sunrise',
              start_offset_minutes: 1,
              end_offset_minutes: -1,
            },
          })}
        />,
      )

      expect(screen.getByText(/1 minute after sunset/i)).toBeInTheDocument()
      expect(screen.getByText(/1 minute before sunrise/i)).toBeInTheDocument()
    })

    it('should show preview with plural "minutes"', () => {
      render(
        <TimeWindowInput
          {...props({
            value: {
              start_time: 'sunset',
              end_time: 'sunrise',
              start_offset_minutes: 45,
              end_offset_minutes: -45,
            },
          })}
        />,
      )

      expect(screen.getByText(/45 minutes after sunset/i)).toBeInTheDocument()
      expect(screen.getByText(/45 minutes before sunrise/i)).toBeInTheDocument()
    })
  })

  describe('Default Values', () => {
    it('should handle missing value prop gracefully', () => {
      render(<TimeWindowInput onChange={mockOnChange} />)

      expect(screen.getByLabelText(/start time \(fixed\)/i)).toHaveValue('')
      expect(screen.getByLabelText(/end time \(fixed\)/i)).toHaveValue('')
    })

    it('should default offset to 0 if not provided', () => {
      render(
        <TimeWindowInput
          {...props({
            value: {
              start_time: 'sunset',
              end_time: 'sunrise',
              start_offset_minutes: 0,
              end_offset_minutes: 0,
            },
          })}
        />,
      )

      const startOffsetInput = screen.getByLabelText(/start time offset/i)
      const endOffsetInput = screen.getByLabelText(/end time offset/i)

      expect(startOffsetInput).toHaveValue(0)
      expect(endOffsetInput).toHaveValue(0)
    })

    it('should default disabled to false', () => {
      render(<TimeWindowInput {...props()} />)

      const startTimeInput = screen.getByLabelText(/start time \(fixed\)/i)
      expect(startTimeInput).not.toBeDisabled()
    })

    it('should default showSolarEvents to true', () => {
      render(<TimeWindowInput {...props()} />)

      expect(screen.getAllByText(/solar event/i)).toHaveLength(2)
    })

    it('should default errors to empty object', () => {
      render(<TimeWindowInput {...props()} />)

      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA labels for time inputs', () => {
      render(<TimeWindowInput {...props()} />)

      expect(screen.getByLabelText(/start time \(fixed\)/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/end time \(fixed\)/i)).toBeInTheDocument()
    })

    it('should have proper ARIA labels for offset inputs', () => {
      render(
        <TimeWindowInput
          {...props({
            value: {
              start_time: 'sunset',
              end_time: 'sunrise',
              start_offset_minutes: 0,
              end_offset_minutes: 0,
            },
          })}
        />,
      )

      expect(screen.getByLabelText(/start time offset \(minutes\)/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/end time offset \(minutes\)/i)).toBeInTheDocument()
    })

    it('should associate labels with inputs', () => {
      render(
        <TimeWindowInput
          {...props({
            value: {
              start_time: 'sunset',
              end_time: 'sunrise',
              start_offset_minutes: 0,
              end_offset_minutes: 0,
            },
          })}
        />,
      )

      const startOffsetInput = screen.getByLabelText(/start time offset/i)
      const endOffsetInput = screen.getByLabelText(/end time offset/i)

      expect(startOffsetInput).toHaveAttribute('id', 'start_offset')
      expect(endOffsetInput).toHaveAttribute('id', 'end_offset')
    })
  })

  describe('Edge Cases', () => {
    it('should handle empty start_time gracefully', () => {
      render(
        <TimeWindowInput
          {...props({
            value: {
              start_time: '',
              end_time: '05:00',
              start_offset_minutes: 0,
              end_offset_minutes: 0,
            },
          })}
        />,
      )

      expect(screen.getByLabelText(/start time \(fixed\)/i)).toHaveValue('')
    })

    it('should handle empty end_time gracefully', () => {
      render(
        <TimeWindowInput
          {...props({
            value: {
              start_time: '21:00',
              end_time: '',
              start_offset_minutes: 0,
              end_offset_minutes: 0,
            },
          })}
        />,
      )

      expect(screen.getByLabelText(/end time \(fixed\)/i)).toHaveValue('')
    })

    it('should handle negative offset correctly', () => {
      render(
        <TimeWindowInput
          {...props({
            value: {
              start_time: 'sunset',
              end_time: 'sunrise',
              start_offset_minutes: -90,
              end_offset_minutes: -45,
            },
          })}
        />,
      )

      expect(screen.getByText(/90 minutes before sunset/i)).toBeInTheDocument()
      expect(screen.getByText(/45 minutes before sunrise/i)).toBeInTheDocument()
    })

    it('should handle positive offset correctly', () => {
      render(
        <TimeWindowInput
          {...props({
            value: {
              start_time: 'sunset',
              end_time: 'sunrise',
              start_offset_minutes: 90,
              end_offset_minutes: 45,
            },
          })}
        />,
      )

      expect(screen.getByText(/90 minutes after sunset/i)).toBeInTheDocument()
      expect(screen.getByText(/45 minutes after sunrise/i)).toBeInTheDocument()
    })
  })

  describe('Solar Event Validation', () => {
    it('should warn for invalid start_time solar event value', () => {
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

      render(
        <TimeWindowInput
          {...props({
            value: {
              start_time: 'invalid_solar_event',
              end_time: 'sunrise',
              start_offset_minutes: 0,
              end_offset_minutes: 0,
            },
          })}
        />,
      )

      expect(warnSpy).toHaveBeenCalledWith(
        expect.stringMatching(/invalid solar event.*invalid_solar_event/i),
      )

      warnSpy.mockRestore()
    })

    it('should warn for invalid end_time solar event value', () => {
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

      render(
        <TimeWindowInput
          {...props({
            value: {
              start_time: 'sunset',
              end_time: 'not_a_real_event',
              start_offset_minutes: 0,
              end_offset_minutes: 0,
            },
          })}
        />,
      )

      expect(warnSpy).toHaveBeenCalledWith(
        expect.stringMatching(/invalid solar event.*not_a_real_event/i),
      )

      warnSpy.mockRestore()
    })

    it('should not warn for valid solar event values', () => {
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

      render(
        <TimeWindowInput
          {...props({
            value: {
              start_time: 'sunset',
              end_time: 'sunrise',
              start_offset_minutes: 0,
              end_offset_minutes: 0,
            },
          })}
        />,
      )

      expect(warnSpy).not.toHaveBeenCalled()

      warnSpy.mockRestore()
    })

    it('should not warn for fixed time values', () => {
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

      render(
        <TimeWindowInput
          {...props({
            value: {
              start_time: '21:00',
              end_time: '05:00',
              start_offset_minutes: 0,
              end_offset_minutes: 0,
            },
          })}
        />,
      )

      expect(warnSpy).not.toHaveBeenCalled()

      warnSpy.mockRestore()
    })

    it('should not warn for empty time values', () => {
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

      render(
        <TimeWindowInput
          {...props({
            value: {
              start_time: '',
              end_time: '',
              start_offset_minutes: 0,
              end_offset_minutes: 0,
            },
          })}
        />,
      )

      expect(warnSpy).not.toHaveBeenCalled()

      warnSpy.mockRestore()
    })
  })

  describe('Parent Error Wiring (RHF)', () => {
    it('wires parentErrors.start_time to start time input via aria', () => {
      const errors = { start_time: 'Server error: invalid start time' }
      render(<TimeWindowInput {...props({ errors })} />)
      const input = screen.getByLabelText(/start time \(fixed\)/i)
      expect(input).toHaveAttribute('aria-invalid', 'true')
      expect(input).toHaveAttribute('aria-describedby', 'start_time-error')
      expect(screen.getByText(errors.start_time)).toBeInTheDocument()
    })

    it('wires parentErrors.end_time to end time input via aria', () => {
      const errors = { end_time: 'Server error: invalid end time' }
      render(<TimeWindowInput {...props({ errors })} />)
      const input = screen.getByLabelText(/end time \(fixed\)/i)
      expect(input).toHaveAttribute('aria-invalid', 'true')
      expect(input).toHaveAttribute('aria-describedby', 'end_time-error')
      expect(screen.getByText(errors.end_time)).toBeInTheDocument()
    })

    it('wires parentErrors.general to general error display', () => {
      const errors = { general: 'Invalid time window' }
      render(<TimeWindowInput {...props({ errors })} />)
      expect(screen.getByText(errors.general)).toBeInTheDocument()
    })
  })

  describe('Prop Sync', () => {
    it('updates form when value prop changes externally', async () => {
      const { rerender } = render(<TimeWindowInput {...props()} />)
      const newValue: TimeWindowValue = {
        start_time: '22:00',
        end_time: '06:00',
        start_offset_minutes: 0,
        end_offset_minutes: 0,
      }
      rerender(<TimeWindowInput value={newValue} onChange={mockOnChange} />)

      await waitFor(() => {
        expect(screen.getByLabelText(/start time \(fixed\)/i)).toHaveValue('22:00')
        expect(screen.getByLabelText(/end time \(fixed\)/i)).toHaveValue('06:00')
      })
    })
  })
})

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import PreConditionForm from '../PreConditionForm'
import type { PreConditionValue } from '../PreConditionForm'
import { TIME_WINDOW_SAME_ERROR } from '../../../../schemas/scheduler/pre-condition'

describe('PreConditionForm', () => {
  let mockOnChange: ReturnType<typeof vi.fn<(value: PreConditionValue | null) => void>>

  beforeEach(() => {
    mockOnChange = vi.fn<(value: PreConditionValue | null) => void>()
  })

  /**
   * Build props with the current mockOnChange.
   * Must be called inside a test (after beforeEach has run).
   */
  function props(
    overrides: Partial<{
      preCondition: PreConditionValue | null
      onChange: (value: PreConditionValue | null) => void
      routineIndex: number
      disabled: boolean
      errors: Record<string, string>
    }> = {},
  ) {
    return {
      preCondition: null as PreConditionValue | null,
      onChange: mockOnChange as (value: PreConditionValue | null) => void,
      routineIndex: 0,
      ...overrides,
    }
  }

  describe('Toggle behavior', () => {
    it('renders toggle unchecked when preCondition is null', () => {
      render(<PreConditionForm {...props()} />)

      const toggle = screen.getByTestId('pre-condition-toggle-0')
      expect(toggle).not.toBeChecked()
    })

    it('renders toggle checked when preCondition has value', () => {
      const preCondition: PreConditionValue = {
        trigger_type: 'sensor',
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      render(<PreConditionForm {...props({ preCondition })} />)

      const toggle = screen.getByTestId('pre-condition-toggle-0')
      expect(toggle).toBeChecked()
    })

    it('shows conditional fields only when enabled', async () => {
      const { rerender } = render(<PreConditionForm {...props()} />)

      // Fields should not be visible when disabled
      expect(screen.queryByTestId('pre-condition-sensor-0')).not.toBeInTheDocument()
      expect(screen.queryByTestId('pre-condition-op-0')).not.toBeInTheDocument()
      expect(screen.queryByTestId('pre-condition-threshold-0')).not.toBeInTheDocument()

      // Re-render with preCondition enabled
      const preCondition: PreConditionValue = {
        trigger_type: 'sensor',
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }
      rerender(<PreConditionForm {...props({ preCondition })} />)

      // Fields should be visible when enabled
      await waitFor(() => {
        expect(screen.getByTestId('pre-condition-sensor-0')).toBeInTheDocument()
        expect(screen.getByTestId('pre-condition-op-0')).toBeInTheDocument()
        expect(screen.getByTestId('pre-condition-threshold-0')).toBeInTheDocument()
      })
    })

    it('enables form and calls onChange with default values when toggled on', async () => {
      render(<PreConditionForm {...props()} />)

      const toggle = screen.getByTestId('pre-condition-toggle-0')
      fireEvent.click(toggle)

      // Toggle handler bypasses RHF - synchronous, but use waitFor for safety
      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith({
          trigger_type: 'sensor',
          sensor_type: 'light',
          comparison: 'lt',
          threshold: 100,
          cooldown_minutes: 5,
        })
      })
    })

    it('disables form and calls onChange with null when toggled off', async () => {
      const preCondition: PreConditionValue = {
        trigger_type: 'sensor',
        sensor_type: 'temperature',
        comparison: 'gt',
        threshold: 25,
        cooldown_minutes: 5,
      }

      render(<PreConditionForm {...props({ preCondition })} />)

      const toggle = screen.getByTestId('pre-condition-toggle-0')
      fireEvent.click(toggle)

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(null)
      })
    })
  })

  describe('Field updates', () => {
    const defaultPreCondition: PreConditionValue = {
      trigger_type: 'sensor',
      sensor_type: 'light',
      comparison: 'lt',
      threshold: 100,
      cooldown_minutes: 5,
    }

    it('updates sensor type correctly', async () => {
      render(<PreConditionForm {...props({ preCondition: defaultPreCondition })} />)

      const sensorSelect = screen.getByTestId('pre-condition-sensor-0')
      fireEvent.change(sensorSelect, { target: { value: 'temperature' } })

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalled()
      })
      const lastCall =
        mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0] as PreConditionValue
      expect(lastCall).toHaveProperty('sensor_type', 'temperature')
    })

    it('updates condition operator correctly', async () => {
      render(<PreConditionForm {...props({ preCondition: defaultPreCondition })} />)

      const opSelect = screen.getByTestId('pre-condition-op-0')
      fireEvent.change(opSelect, { target: { value: 'gt' } })

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalled()
      })
      const lastCall =
        mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0] as PreConditionValue
      expect(lastCall).toHaveProperty('comparison', 'gt')
    })

    it('updates threshold value correctly', async () => {
      render(<PreConditionForm {...props({ preCondition: defaultPreCondition })} />)

      const thresholdInput = screen.getByTestId('pre-condition-threshold-0')
      fireEvent.change(thresholdInput, { target: { value: '50' } })

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalled()
      })
      const lastCall =
        mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0] as PreConditionValue
      expect(lastCall).toHaveProperty('threshold', 50)
    })

    it('shows validation error for empty threshold input', async () => {
      render(<PreConditionForm {...props({ preCondition: defaultPreCondition })} />)

      const thresholdInput = screen.getByTestId('pre-condition-threshold-0')
      fireEvent.change(thresholdInput, { target: { value: '' } })

      // Wait for RHF async validation to show error
      await waitFor(() => {
        expect(screen.getByTestId('pre-condition-error-0')).toBeInTheDocument()
      })
      // onChange should NOT have been called with invalid value
      expect(mockOnChange).not.toHaveBeenCalled()
    })

    it('shows validation error for negative threshold', async () => {
      render(<PreConditionForm {...props({ preCondition: defaultPreCondition })} />)

      const thresholdInput = screen.getByTestId('pre-condition-threshold-0')
      fireEvent.change(thresholdInput, { target: { value: '-10' } })

      await waitFor(() => {
        expect(screen.getByTestId('pre-condition-error-0')).toBeInTheDocument()
      })
      expect(mockOnChange).not.toHaveBeenCalled()
    })

    it('clears validation error when valid value entered', async () => {
      render(<PreConditionForm {...props({ preCondition: defaultPreCondition })} />)

      const thresholdInput = screen.getByTestId('pre-condition-threshold-0')

      // First enter invalid value
      fireEvent.change(thresholdInput, { target: { value: '' } })
      await waitFor(() => {
        expect(screen.getByTestId('pre-condition-error-0')).toBeInTheDocument()
      })

      // Then enter valid value
      fireEvent.change(thresholdInput, { target: { value: '50' } })
      await waitFor(() => {
        expect(screen.queryByTestId('pre-condition-error-0')).not.toBeInTheDocument()
      })
    })

    it('clears validation error when toggling off and back on', async () => {
      const { rerender } = render(
        <PreConditionForm {...props({ preCondition: defaultPreCondition })} />,
      )

      // 1. Enter invalid value -> error shows
      const thresholdInput = screen.getByTestId('pre-condition-threshold-0')
      fireEvent.change(thresholdInput, { target: { value: '' } })
      await waitFor(() => {
        expect(screen.getByTestId('pre-condition-error-0')).toBeInTheDocument()
      })

      // 2. Toggle off -> parent sets preCondition to null
      fireEvent.click(screen.getByTestId('pre-condition-toggle-0'))

      // 3. Simulate parent setting preCondition to null (as it would after onChange(null))
      rerender(<PreConditionForm {...props({ preCondition: null })} />)

      // Fields are hidden when null
      await waitFor(() => {
        expect(screen.queryByTestId('pre-condition-error-0')).not.toBeInTheDocument()
      })

      // 4. Toggle on -> parent gets default preCondition callback
      fireEvent.click(screen.getByTestId('pre-condition-toggle-0'))

      // 5. Simulate parent setting preCondition to default (as it would after onChange(default))
      rerender(<PreConditionForm {...props({ preCondition: defaultPreCondition })} />)

      // 6. Verify error is gone after re-enabling with fresh defaults
      await waitFor(() => {
        expect(screen.queryByTestId('pre-condition-error-0')).not.toBeInTheDocument()
      })
    })
  })

  describe('Disabled state', () => {
    it('prevents toggle interaction when disabled', () => {
      render(<PreConditionForm {...props({ disabled: true })} />)

      const toggle = screen.getByTestId('pre-condition-toggle-0')
      expect(toggle).toBeDisabled()
    })

    it('prevents field interaction when disabled', () => {
      const preCondition: PreConditionValue = {
        trigger_type: 'sensor',
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      render(<PreConditionForm {...props({ preCondition, disabled: true })} />)

      expect(screen.getByTestId('pre-condition-sensor-0')).toBeDisabled()
      expect(screen.getByTestId('pre-condition-op-0')).toBeDisabled()
      expect(screen.getByTestId('pre-condition-threshold-0')).toBeDisabled()
      expect(screen.getByTestId('pre-condition-cooldown-0')).toBeDisabled()
      expect(screen.getByTestId('pre-condition-time-window-toggle-0')).toBeDisabled()
    })

    it('prevents time window input interaction when disabled', () => {
      const preCondition: PreConditionValue = {
        trigger_type: 'sensor',
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
        time_window: { start_time: '21:00', end_time: '06:00' },
      }

      render(<PreConditionForm {...props({ preCondition, disabled: true })} />)

      expect(screen.getByTestId('pre-condition-tw-start-0')).toBeDisabled()
      expect(screen.getByTestId('pre-condition-tw-end-0')).toBeDisabled()
    })
  })

  describe('data-testid attributes', () => {
    it('has correct toggle testid with routineIndex', () => {
      render(<PreConditionForm {...props({ routineIndex: 5 })} />)

      expect(screen.getByTestId('pre-condition-toggle-5')).toBeInTheDocument()
    })

    it('has all required field testids', () => {
      const preCondition: PreConditionValue = {
        trigger_type: 'sensor',
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      render(<PreConditionForm {...props({ preCondition })} />)

      expect(screen.getByTestId('pre-condition-toggle-0')).toBeInTheDocument()
      expect(screen.getByTestId('pre-condition-sensor-0')).toBeInTheDocument()
      expect(screen.getByTestId('pre-condition-op-0')).toBeInTheDocument()
      expect(screen.getByTestId('pre-condition-threshold-0')).toBeInTheDocument()
    })
  })

  describe('Sensor type options', () => {
    it('shows light and temperature options (not motion per issue spec)', () => {
      const preCondition: PreConditionValue = {
        trigger_type: 'sensor',
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      render(<PreConditionForm {...props({ preCondition })} />)

      const sensorSelect = screen.getByTestId('pre-condition-sensor-0') as HTMLSelectElement
      const options = sensorSelect.querySelectorAll('option')
      const optionValues = Array.from(options).map((o) => (o as HTMLOptionElement).value)

      expect(optionValues).toContain('light')
      expect(optionValues).toContain('temperature')
      expect(optionValues).not.toContain('motion')
    })
  })

  describe('Operator options', () => {
    it('shows only lt/gt/eq operators per issue #325 spec (not gte/lte)', () => {
      const preCondition: PreConditionValue = {
        trigger_type: 'sensor',
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      render(<PreConditionForm {...props({ preCondition })} />)

      const opSelect = screen.getByTestId('pre-condition-op-0') as HTMLSelectElement
      const options = opSelect.querySelectorAll('option')
      const optionValues = Array.from(options).map((o) => (o as HTMLOptionElement).value)

      expect(optionValues).toContain('lt')
      expect(optionValues).toContain('gt')
      expect(optionValues).toContain('eq')
      expect(optionValues).not.toContain('gte')
      expect(optionValues).not.toContain('lte')
      expect(optionValues).toHaveLength(3)
    })

    it('shows correct human-readable labels', () => {
      const preCondition: PreConditionValue = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      render(<PreConditionForm {...props({ preCondition })} />)

      const opSelect = screen.getByTestId('pre-condition-op-0')

      expect(opSelect).toHaveTextContent('is below')
      expect(opSelect).toHaveTextContent('is above')
      expect(opSelect).toHaveTextContent('equals')
    })
  })

  describe('Label and accessibility', () => {
    it('renders label with correct text', () => {
      render(<PreConditionForm {...props()} />)

      expect(screen.getByText('Only run if sensor condition met')).toBeInTheDocument()
    })

    it('label is associated with toggle via htmlFor', () => {
      render(<PreConditionForm {...props()} />)

      const toggle = screen.getByTestId('pre-condition-toggle-0')
      const label = screen.getByText('Only run if sensor condition met')

      expect(label).toHaveAttribute('for', 'pre-condition-toggle-0')
      expect(toggle).toHaveAttribute('id', 'pre-condition-toggle-0')
    })
  })

  describe('useEffect sync behavior', () => {
    it('syncs internal enabled state when preCondition prop changes externally', async () => {
      const { rerender } = render(<PreConditionForm {...props()} />)

      // Initially unchecked
      expect(screen.getByTestId('pre-condition-toggle-0')).not.toBeChecked()

      // Parent provides preCondition - toggle should sync to checked
      rerender(
        <PreConditionForm
          {...props({
            preCondition: {
              sensor_type: 'light',
              comparison: 'lt',
              threshold: 50,
              cooldown_minutes: 5,
            },
          })}
        />,
      )
      await waitFor(() => {
        expect(screen.getByTestId('pre-condition-toggle-0')).toBeChecked()
      })

      // Parent removes preCondition - toggle should sync to unchecked
      rerender(<PreConditionForm {...props()} />)
      await waitFor(() => {
        expect(screen.getByTestId('pre-condition-toggle-0')).not.toBeChecked()
      })
    })
  })

  describe('Multiple instances', () => {
    it('multiple instances with different routineIndex do not conflict', async () => {
      const preCondition1: PreConditionValue = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }
      const preCondition2: PreConditionValue = {
        sensor_type: 'temperature',
        comparison: 'gt',
        threshold: 25,
        cooldown_minutes: 5,
      }
      const onChange1 = vi.fn()
      const onChange2 = vi.fn()

      render(
        <>
          <PreConditionForm
            preCondition={preCondition1}
            onChange={onChange1}
            routineIndex={0}
          />
          <PreConditionForm
            preCondition={preCondition2}
            onChange={onChange2}
            routineIndex={1}
          />
        </>,
      )

      // Both toggles should be present with unique IDs
      expect(screen.getByTestId('pre-condition-toggle-0')).toBeInTheDocument()
      expect(screen.getByTestId('pre-condition-toggle-1')).toBeInTheDocument()

      // Changing one should not affect the other
      const toggle0 = screen.getByTestId('pre-condition-toggle-0')
      fireEvent.click(toggle0)

      await waitFor(() => {
        expect(onChange1).toHaveBeenCalledWith(null)
      })
      expect(onChange2).not.toHaveBeenCalled()
    })
  })

  describe('Edge cases', () => {
    it('handles invalid sensor_type gracefully by falling back to first option', () => {
      const preCondition = {
        sensor_type: 'invalid_sensor',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      } as PreConditionValue

      render(<PreConditionForm {...props({ preCondition })} />)

      // HTML select falls back to first valid option when value doesn't match
      const sensorSelect = screen.getByTestId('pre-condition-sensor-0') as HTMLSelectElement
      expect(sensorSelect).toBeInTheDocument()
      expect(sensorSelect.value).toBe('light')
    })

    it('accepts decimal threshold values', async () => {
      const preCondition: PreConditionValue = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }
      render(<PreConditionForm {...props({ preCondition })} />)

      const thresholdInput = screen.getByTestId('pre-condition-threshold-0')
      fireEvent.change(thresholdInput, { target: { value: '50.5' } })

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalled()
      })
      const lastCall =
        mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0] as PreConditionValue
      expect(lastCall).toHaveProperty('threshold', 50.5)
      expect(screen.queryByTestId('pre-condition-error-0')).not.toBeInTheDocument()
    })

    it('accepts zero as valid threshold value', async () => {
      const preCondition: PreConditionValue = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }
      render(<PreConditionForm {...props({ preCondition })} />)

      const thresholdInput = screen.getByTestId('pre-condition-threshold-0')
      fireEvent.change(thresholdInput, { target: { value: '0' } })

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalled()
      })
      const lastCall =
        mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0] as PreConditionValue
      expect(lastCall).toHaveProperty('threshold', 0)
      expect(screen.queryByTestId('pre-condition-error-0')).not.toBeInTheDocument()
    })

    it('handles very large threshold values', async () => {
      const preCondition: PreConditionValue = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }
      render(<PreConditionForm {...props({ preCondition })} />)

      const thresholdInput = screen.getByTestId('pre-condition-threshold-0')
      fireEvent.change(thresholdInput, { target: { value: '999999' } })

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalled()
      })
      const lastCall =
        mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0] as PreConditionValue
      expect(lastCall).toHaveProperty('threshold', 999999)
      expect(screen.queryByTestId('pre-condition-error-0')).not.toBeInTheDocument()
    })

    it('shows validation error for whitespace-only threshold input', async () => {
      const preCondition: PreConditionValue = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }
      render(<PreConditionForm {...props({ preCondition })} />)

      const thresholdInput = screen.getByTestId('pre-condition-threshold-0')
      fireEvent.change(thresholdInput, { target: { value: '   ' } })

      // Wait for RHF async validation
      await waitFor(() => {
        expect(screen.getByTestId('pre-condition-error-0')).toBeInTheDocument()
      })
      expect(mockOnChange).not.toHaveBeenCalled()
    })

    it('shows validation error for non-numeric threshold input', async () => {
      const preCondition: PreConditionValue = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }
      render(<PreConditionForm {...props({ preCondition })} />)

      const thresholdInput = screen.getByTestId('pre-condition-threshold-0')
      fireEvent.change(thresholdInput, { target: { value: 'abc' } })

      await waitFor(() => {
        expect(screen.getByTestId('pre-condition-error-0')).toBeInTheDocument()
      })
      expect(mockOnChange).not.toHaveBeenCalled()
    })
  })

  describe('Cooldown', () => {
    const preConditionWithCooldown: PreConditionValue = {
      trigger_type: 'sensor',
      sensor_type: 'light',
      comparison: 'lt',
      threshold: 100,
      cooldown_minutes: 5,
    }

    it('renders cooldown input when enabled', () => {
      render(<PreConditionForm {...props({ preCondition: preConditionWithCooldown })} />)
      expect(screen.getByTestId('pre-condition-cooldown-0')).toBeInTheDocument()
      expect(screen.getByTestId('pre-condition-cooldown-0')).toHaveValue(5)
    })

    it('does not render cooldown when disabled', () => {
      render(<PreConditionForm {...props()} />)
      expect(screen.queryByTestId('pre-condition-cooldown-0')).not.toBeInTheDocument()
    })

    it('updates cooldown value', async () => {
      render(<PreConditionForm {...props({ preCondition: preConditionWithCooldown })} />)
      const cooldownInput = screen.getByTestId('pre-condition-cooldown-0')
      fireEvent.change(cooldownInput, { target: { value: '15' } })

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalled()
      })
      const lastCall =
        mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0] as PreConditionValue
      expect(lastCall).toHaveProperty('cooldown_minutes', 15)
    })

    it('shows error for cooldown below 1', async () => {
      render(<PreConditionForm {...props({ preCondition: preConditionWithCooldown })} />)
      const cooldownInput = screen.getByTestId('pre-condition-cooldown-0')
      fireEvent.change(cooldownInput, { target: { value: '0' } })

      await waitFor(() => {
        expect(screen.getByTestId('pre-condition-cooldown-error-0')).toBeInTheDocument()
      })
      expect(mockOnChange).not.toHaveBeenCalled()
    })

    it('shows error for cooldown above 60', async () => {
      render(<PreConditionForm {...props({ preCondition: preConditionWithCooldown })} />)
      const cooldownInput = screen.getByTestId('pre-condition-cooldown-0')
      fireEvent.change(cooldownInput, { target: { value: '61' } })

      await waitFor(() => {
        expect(screen.getByTestId('pre-condition-cooldown-error-0')).toBeInTheDocument()
      })
      expect(mockOnChange).not.toHaveBeenCalled()
    })

    it('includes cooldown_minutes in default pre-condition', async () => {
      render(<PreConditionForm {...props()} />)
      const toggle = screen.getByTestId('pre-condition-toggle-0')
      fireEvent.click(toggle)

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({ cooldown_minutes: 5 }),
        )
      })
    })

    it('shows error for non-numeric cooldown input', async () => {
      render(<PreConditionForm {...props({ preCondition: preConditionWithCooldown })} />)
      const cooldownInput = screen.getByTestId('pre-condition-cooldown-0')
      fireEvent.change(cooldownInput, { target: { value: 'abc' } })

      await waitFor(() => {
        expect(screen.getByTestId('pre-condition-cooldown-error-0')).toBeInTheDocument()
      })
      expect(mockOnChange).not.toHaveBeenCalled()
    })

    it('shows error for empty cooldown input', async () => {
      render(<PreConditionForm {...props({ preCondition: preConditionWithCooldown })} />)
      const cooldownInput = screen.getByTestId('pre-condition-cooldown-0')
      fireEvent.change(cooldownInput, { target: { value: '' } })

      await waitFor(() => {
        expect(screen.getByTestId('pre-condition-cooldown-error-0')).toBeInTheDocument()
      })
      expect(mockOnChange).not.toHaveBeenCalled()
    })

    it('accepts decimal cooldown values within range', async () => {
      render(<PreConditionForm {...props({ preCondition: preConditionWithCooldown })} />)
      const cooldownInput = screen.getByTestId('pre-condition-cooldown-0')
      fireEvent.change(cooldownInput, { target: { value: '5.5' } })

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalled()
      })
      const lastCall =
        mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0] as PreConditionValue
      expect(lastCall).toHaveProperty('cooldown_minutes', 5.5)
      expect(screen.queryByTestId('pre-condition-cooldown-error-0')).not.toBeInTheDocument()
    })
  })

  describe('Time window', () => {
    const preConditionBase: PreConditionValue = {
      trigger_type: 'sensor',
      sensor_type: 'light',
      comparison: 'lt',
      threshold: 100,
      cooldown_minutes: 5,
    }

    it('renders time window toggle when pre-condition is enabled', () => {
      render(<PreConditionForm {...props({ preCondition: preConditionBase })} />)
      expect(screen.getByTestId('pre-condition-time-window-toggle-0')).toBeInTheDocument()
      expect(screen.getByTestId('pre-condition-time-window-toggle-0')).not.toBeChecked()
    })

    it('shows time inputs when time window toggle is checked', () => {
      const withTimeWindow: PreConditionValue = {
        ...preConditionBase,
        time_window: { start_time: '21:00', end_time: '06:00' },
      }
      render(<PreConditionForm {...props({ preCondition: withTimeWindow })} />)
      expect(screen.getByTestId('pre-condition-time-window-toggle-0')).toBeChecked()
      expect(screen.getByTestId('pre-condition-tw-start-0')).toHaveValue('21:00')
      expect(screen.getByTestId('pre-condition-tw-end-0')).toHaveValue('06:00')
    })

    it('hides time inputs when time window is null', () => {
      render(<PreConditionForm {...props({ preCondition: preConditionBase })} />)
      expect(screen.queryByTestId('pre-condition-tw-start-0')).not.toBeInTheDocument()
      expect(screen.queryByTestId('pre-condition-tw-end-0')).not.toBeInTheDocument()
    })

    it('enables time window with defaults when toggle checked', async () => {
      render(<PreConditionForm {...props({ preCondition: preConditionBase })} />)
      const toggle = screen.getByTestId('pre-condition-time-window-toggle-0')
      fireEvent.click(toggle)

      // Time window toggle bypasses RHF - synchronous
      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith({
          ...preConditionBase,
          time_window: { start_time: '21:00', end_time: '06:00' },
        })
      })
    })

    it('removes time window when toggle unchecked', async () => {
      const withTimeWindow: PreConditionValue = {
        ...preConditionBase,
        time_window: { start_time: '21:00', end_time: '06:00' },
      }
      render(<PreConditionForm {...props({ preCondition: withTimeWindow })} />)
      const toggle = screen.getByTestId('pre-condition-time-window-toggle-0')
      fireEvent.click(toggle)

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith({
          ...preConditionBase,
          time_window: null,
        })
      })
    })

    it('updates start time', async () => {
      const withTimeWindow: PreConditionValue = {
        ...preConditionBase,
        time_window: { start_time: '21:00', end_time: '06:00' },
      }
      render(<PreConditionForm {...props({ preCondition: withTimeWindow })} />)
      const startInput = screen.getByTestId('pre-condition-tw-start-0')
      fireEvent.change(startInput, { target: { value: '22:30' } })

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalled()
      })
      const lastCall =
        mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0] as PreConditionValue
      expect(lastCall.time_window).toEqual(
        expect.objectContaining({ start_time: '22:30' }),
      )
    })

    it('updates end time', async () => {
      const withTimeWindow: PreConditionValue = {
        ...preConditionBase,
        time_window: { start_time: '21:00', end_time: '06:00' },
      }
      render(<PreConditionForm {...props({ preCondition: withTimeWindow })} />)
      const endInput = screen.getByTestId('pre-condition-tw-end-0')
      fireEvent.change(endInput, { target: { value: '07:00' } })

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalled()
      })
      const lastCall =
        mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0] as PreConditionValue
      expect(lastCall.time_window).toEqual(
        expect.objectContaining({ end_time: '07:00' }),
      )
    })

    it('shows error when start and end times are the same', async () => {
      const withTimeWindow: PreConditionValue = {
        ...preConditionBase,
        time_window: { start_time: '21:00', end_time: '21:00' },
      }
      render(<PreConditionForm {...props({ preCondition: withTimeWindow })} />)
      await waitFor(() => {
        expect(screen.getByTestId('pre-condition-tw-error-0')).toHaveTextContent(
          TIME_WINDOW_SAME_ERROR,
        )
      })
    })

    it('clears error when times are changed to be different', async () => {
      const withSameTime: PreConditionValue = {
        ...preConditionBase,
        time_window: { start_time: '21:00', end_time: '21:00' },
      }
      const { rerender } = render(
        <PreConditionForm {...props({ preCondition: withSameTime })} />,
      )
      await waitFor(() => {
        expect(screen.getByTestId('pre-condition-tw-error-0')).toBeInTheDocument()
      })

      rerender(
        <PreConditionForm
          {...props({
            preCondition: {
              ...preConditionBase,
              time_window: { start_time: '21:00', end_time: '06:00' },
            },
          })}
        />,
      )
      await waitFor(() => {
        expect(screen.queryByTestId('pre-condition-tw-error-0')).not.toBeInTheDocument()
      })
    })

    // Empty times are a transient editing state (user toggled time window on
    // but hasn't typed values yet). This should not show a cross-field error.
    it('renders time window with empty times without error', async () => {
      const withEmptyTimes: PreConditionValue = {
        ...preConditionBase,
        time_window: { start_time: '', end_time: '' },
      }
      render(<PreConditionForm {...props({ preCondition: withEmptyTimes })} />)
      expect(screen.getByTestId('pre-condition-tw-start-0')).toBeInTheDocument()
      expect(screen.getByTestId('pre-condition-tw-end-0')).toBeInTheDocument()
      await waitFor(() => {
        expect(screen.queryByTestId('pre-condition-tw-error-0')).not.toBeInTheDocument()
      })
    })
  })

  describe('Unit labels', () => {
    it('shows "lux" unit when sensor type is light', () => {
      const preCondition: PreConditionValue = {
        trigger_type: 'sensor',
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }
      render(<PreConditionForm {...props({ preCondition })} />)
      expect(screen.getByText('lux')).toBeInTheDocument()
    })

    it('shows "\u00B0C" unit when sensor type is temperature', () => {
      const preCondition: PreConditionValue = {
        trigger_type: 'sensor',
        sensor_type: 'temperature',
        comparison: 'gt',
        threshold: 25,
        cooldown_minutes: 5,
      }
      render(<PreConditionForm {...props({ preCondition })} />)
      expect(screen.getByText('\u00B0C')).toBeInTheDocument()
    })

    it('updates unit label when sensor type changes', async () => {
      const preCondition: PreConditionValue = {
        trigger_type: 'sensor',
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }
      const { rerender } = render(
        <PreConditionForm {...props({ preCondition })} />,
      )
      expect(screen.getByText('lux')).toBeInTheDocument()

      rerender(
        <PreConditionForm
          {...props({ preCondition: { ...preCondition, sensor_type: 'temperature' } })}
        />,
      )
      await waitFor(() => {
        expect(screen.getByText('\u00B0C')).toBeInTheDocument()
        expect(screen.queryByText('lux')).not.toBeInTheDocument()
      })
    })
  })

  describe('Parent error wiring (RHF)', () => {
    const preCondition: PreConditionValue = {
      trigger_type: 'sensor',
      sensor_type: 'light',
      comparison: 'lt',
      threshold: 100,
      cooldown_minutes: 5,
    }

    it('wires parentErrors.threshold to threshold input via aria', () => {
      render(
        <PreConditionForm
          {...props({
            preCondition,
            errors: { threshold: 'Bad value' },
          })}
        />,
      )

      const input = screen.getByTestId('pre-condition-threshold-0')
      expect(input).toHaveAttribute('aria-invalid', 'true')
      expect(input).toHaveAttribute('aria-describedby', 'threshold-error-0')
      expect(screen.getByText('Bad value')).toBeInTheDocument()
    })

    it('wires parentErrors.cooldown_minutes to cooldown input via aria', () => {
      render(
        <PreConditionForm
          {...props({
            preCondition,
            errors: { cooldown_minutes: 'Bad cooldown' },
          })}
        />,
      )

      const input = screen.getByTestId('pre-condition-cooldown-0')
      expect(input).toHaveAttribute('aria-invalid', 'true')
      expect(input).toHaveAttribute('aria-describedby', 'cooldown_minutes-error-0')
      expect(screen.getByText('Bad cooldown')).toBeInTheDocument()
    })

    it('wires parentErrors.sensor_type to sensor select via aria', () => {
      render(
        <PreConditionForm
          {...props({
            preCondition,
            errors: { sensor_type: 'Invalid sensor' },
          })}
        />,
      )

      const input = screen.getByTestId('pre-condition-sensor-0')
      expect(input).toHaveAttribute('aria-invalid', 'true')
      expect(input).toHaveAttribute('aria-describedby', 'sensor_type-error-0')
    })

    it('wires parentErrors.comparison to comparison select via aria', () => {
      render(
        <PreConditionForm
          {...props({
            preCondition,
            errors: { comparison: 'Invalid op' },
          })}
        />,
      )

      const input = screen.getByTestId('pre-condition-op-0')
      expect(input).toHaveAttribute('aria-invalid', 'true')
      expect(input).toHaveAttribute('aria-describedby', 'comparison-error-0')
    })
  })

  describe('trigger_type preservation', () => {
    it('preserves trigger_type when form fields change', async () => {
      const preCondition: PreConditionValue = {
        trigger_type: 'sensor',
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      render(<PreConditionForm {...props({ preCondition })} />)

      const thresholdInput = screen.getByTestId('pre-condition-threshold-0')
      fireEvent.change(thresholdInput, { target: { value: '50' } })

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalled()
      })
      const lastCall =
        mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0] as PreConditionValue
      expect(lastCall).toHaveProperty('trigger_type', 'sensor')
      expect(lastCall).toHaveProperty('threshold', 50)
    })

    it('preserves trigger_type when sensor_type changes', async () => {
      const preCondition: PreConditionValue = {
        trigger_type: 'sensor',
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      render(<PreConditionForm {...props({ preCondition })} />)

      const sensorSelect = screen.getByTestId('pre-condition-sensor-0')
      fireEvent.change(sensorSelect, { target: { value: 'temperature' } })

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalled()
      })
      const lastCall =
        mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0] as PreConditionValue
      expect(lastCall).toHaveProperty('trigger_type', 'sensor')
      expect(lastCall).toHaveProperty('sensor_type', 'temperature')
    })
  })

  describe('Prop sync', () => {
    it('updates form when preCondition prop changes externally', async () => {
      const initial: PreConditionValue = {
        trigger_type: 'sensor',
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }
      const { rerender } = render(
        <PreConditionForm {...props({ preCondition: initial })} />,
      )

      expect(screen.getByTestId('pre-condition-threshold-0')).toHaveValue(100)

      const updated: PreConditionValue = {
        ...initial,
        sensor_type: 'temperature',
        threshold: 25,
      }
      rerender(<PreConditionForm {...props({ preCondition: updated })} />)

      await waitFor(() => {
        expect(screen.getByTestId('pre-condition-threshold-0')).toHaveValue(25)
        expect(
          (screen.getByTestId('pre-condition-sensor-0') as HTMLSelectElement).value,
        ).toBe('temperature')
      })
    })
  })
})

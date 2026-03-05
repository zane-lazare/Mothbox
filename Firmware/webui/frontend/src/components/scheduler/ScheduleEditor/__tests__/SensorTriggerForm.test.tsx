import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SensorTriggerForm from '../SensorTriggerForm'
import type { SensorTriggerValue } from '../SensorTriggerForm'
import { SENSOR_TYPES, SENSOR_COMPARISONS, SCHEDULE_LIMITS } from '../constants'

// -- Helpers ----------------------------------------------------------------

const defaultValue: SensorTriggerValue = {
  sensor_type: 'light',
  comparison: 'lt',
  threshold: 100,
  cooldown_minutes: 5,
}

// -- Tests ------------------------------------------------------------------

describe('SensorTriggerForm', () => {
  let mockOnChange: ReturnType<typeof vi.fn<(value: SensorTriggerValue) => void>>

  beforeEach(() => {
    mockOnChange = vi.fn<(value: SensorTriggerValue) => void>()
  })

  describe('Rendering', () => {
    it('renders with default values', () => {
      render(<SensorTriggerForm onChange={mockOnChange} />)

      expect(screen.getByText('Sensor Configuration')).toBeInTheDocument()
      expect(screen.getByLabelText(/sensor type/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/comparison/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/threshold/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/cooldown.*minutes/i)).toBeInTheDocument()
      expect(screen.getByText('Preview:')).toBeInTheDocument()
    })

    it('renders with provided value', () => {
      const value: SensorTriggerValue = {
        sensor_type: 'temperature',
        comparison: 'gte',
        threshold: 25,
        cooldown_minutes: 10,
      }

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />)

      const sensorTypeSelect = screen.getByLabelText(/sensor type/i)
      expect(sensorTypeSelect).toHaveValue('temperature')

      const comparisonSelect = screen.getByLabelText(/comparison/i)
      expect(comparisonSelect).toHaveValue('gte')

      const thresholdInput = screen.getByLabelText(/threshold/i)
      expect(thresholdInput).toHaveValue(25)

      const cooldownInput = screen.getByLabelText(/cooldown.*minutes/i)
      expect(cooldownInput).toHaveValue(10)
    })

    it('renders all sensor types in dropdown', () => {
      render(<SensorTriggerForm onChange={mockOnChange} />)

      const sensorTypeSelect = screen.getByLabelText(
        /sensor type/i,
      ) as HTMLSelectElement
      const options = Array.from(sensorTypeSelect.options).map(
        (opt) => opt.value,
      )

      SENSOR_TYPES.forEach((type) => {
        expect(options).toContain(type.value)
      })
    })

    it('renders all comparison operators in dropdown', () => {
      render(<SensorTriggerForm onChange={mockOnChange} />)

      const comparisonSelect = screen.getByLabelText(
        /comparison/i,
      ) as HTMLSelectElement
      const options = Array.from(comparisonSelect.options).map(
        (opt) => opt.value,
      )

      SENSOR_COMPARISONS.forEach((comp) => {
        expect(options).toContain(comp.value)
      })
    })
  })

  describe('Sensor Type Selection', () => {
    it('updates sensor_type on selection change', async () => {
      const value: SensorTriggerValue = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />)

      const sensorTypeSelect = screen.getByLabelText(/sensor type/i)
      fireEvent.change(sensorTypeSelect, { target: { value: 'temperature' } })

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith({
          ...value,
          sensor_type: 'temperature',
        })
      })
    })

    it('shows description for selected sensor type', () => {
      const value: SensorTriggerValue = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />)

      const lightSensor = SENSOR_TYPES.find((s) => s.value === 'light')!
      expect(screen.getByText(lightSensor.description)).toBeInTheDocument()
    })

    it('updates description when sensor type changes', () => {
      const value: SensorTriggerValue = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      const { rerender } = render(
        <SensorTriggerForm value={value} onChange={mockOnChange} />,
      )

      // Verify light description shows
      const lightSensor = SENSOR_TYPES.find((s) => s.value === 'light')!
      expect(screen.getByText(lightSensor.description)).toBeInTheDocument()

      // Change to temperature
      const newValue = { ...value, sensor_type: 'temperature' }
      rerender(
        <SensorTriggerForm value={newValue} onChange={mockOnChange} />,
      )

      // Verify temperature description shows
      const tempSensor = SENSOR_TYPES.find(
        (s) => s.value === 'temperature',
      )!
      expect(screen.getByText(tempSensor.description)).toBeInTheDocument()
    })
  })

  describe('Comparison Selection', () => {
    it('updates comparison on selection change', async () => {
      const value: SensorTriggerValue = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />)

      const comparisonSelect = screen.getByLabelText(/comparison/i)
      fireEvent.change(comparisonSelect, { target: { value: 'gte' } })

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith({
          ...value,
          comparison: 'gte',
        })
      })
    })

    it('shows comparison symbol in option labels', () => {
      render(<SensorTriggerForm onChange={mockOnChange} />)

      const comparisonSelect = screen.getByLabelText(
        /comparison/i,
      ) as HTMLSelectElement

      SENSOR_COMPARISONS.forEach((comp) => {
        const option = Array.from(comparisonSelect.options).find(
          (opt) => opt.value === comp.value,
        )
        expect(option!.textContent).toContain(comp.symbol)
      })
    })
  })

  describe('Threshold Input (react-hook-form + Zod)', () => {
    it('propagates valid threshold change to parent', async () => {
      const value: SensorTriggerValue = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />)

      const thresholdInput = screen.getByLabelText(/threshold/i)
      fireEvent.change(thresholdInput, { target: { value: '50' } })

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith({
          ...value,
          threshold: 50,
        })
      })
    })

    it('converts threshold to number', async () => {
      const value: SensorTriggerValue = {
        sensor_type: 'temperature',
        comparison: 'gte',
        threshold: 20,
        cooldown_minutes: 5,
      }

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />)

      const thresholdInput = screen.getByLabelText(/threshold/i)
      fireEvent.change(thresholdInput, { target: { value: '25' } })

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith({
          ...value,
          threshold: 25,
        })
      })

      expect(typeof mockOnChange.mock.calls[0][0].threshold).toBe('number')
    })

    it('does not propagate invalid threshold (empty input) to parent', async () => {
      const value: SensorTriggerValue = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />)

      const thresholdInput = screen.getByLabelText(/threshold/i)
      fireEvent.change(thresholdInput, { target: { value: '' } })

      // Wait for Zod validation to produce error
      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })

      expect(mockOnChange).not.toHaveBeenCalled()
    })

    it('does not propagate negative threshold to parent', async () => {
      const value: SensorTriggerValue = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />)

      const thresholdInput = screen.getByLabelText(/threshold/i)
      fireEvent.change(thresholdInput, { target: { value: '-10' } })

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })

      expect(mockOnChange).not.toHaveBeenCalled()
    })

    it('accepts zero as valid threshold', async () => {
      const value: SensorTriggerValue = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />)

      const thresholdInput = screen.getByLabelText(/threshold/i)
      fireEvent.change(thresholdInput, { target: { value: '0' } })

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith({
          ...value,
          threshold: 0,
        })
      })
    })

    it('accepts valid threshold input', async () => {
      const value: SensorTriggerValue = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />)

      const thresholdInput = screen.getByLabelText(/threshold/i)
      fireEvent.change(thresholdInput, { target: { value: '250' } })

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith({
          ...value,
          threshold: 250,
        })
      })
    })

    it('shows Zod error for negative threshold', async () => {
      render(
        <SensorTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const thresholdInput = screen.getByLabelText(/threshold/i)
      fireEvent.change(thresholdInput, { target: { value: '-5' } })

      await waitFor(() => {
        const alert = screen.getByRole('alert')
        expect(alert).toBeInTheDocument()
        expect(alert.textContent).toMatch(/0 or greater/i)
      })
    })

    it('shows parent-provided threshold error', () => {
      const errors = { threshold: 'Threshold is invalid' }

      render(
        <SensorTriggerForm
          value={defaultValue}
          onChange={mockOnChange}
          errors={errors}
        />,
      )

      expect(screen.getByText('Threshold is invalid')).toBeInTheDocument()
    })
  })

  describe('Cooldown Input (react-hook-form + Zod)', () => {
    it('propagates valid cooldown change to parent', async () => {
      const value: SensorTriggerValue = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />)

      const cooldownInput = screen.getByLabelText(/cooldown.*minutes/i)
      fireEvent.change(cooldownInput, { target: { value: '10' } })

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith({
          ...value,
          cooldown_minutes: 10,
        })
      })
    })

    it('respects cooldown limits on input attributes', () => {
      render(<SensorTriggerForm onChange={mockOnChange} />)

      const cooldownInput = screen.getByLabelText(/cooldown.*minutes/i)
      expect(cooldownInput).toHaveAttribute('min', '1')
      expect(cooldownInput).toHaveAttribute(
        'max',
        String(SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES),
      )
    })

    it('converts cooldown to number', async () => {
      const value: SensorTriggerValue = {
        sensor_type: 'motion',
        comparison: 'eq',
        threshold: 1,
        cooldown_minutes: 5,
      }

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />)

      const cooldownInput = screen.getByLabelText(/cooldown.*minutes/i)
      fireEvent.change(cooldownInput, { target: { value: '15' } })

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith({
          ...value,
          cooldown_minutes: 15,
        })
      })

      expect(typeof mockOnChange.mock.calls[0][0].cooldown_minutes).toBe(
        'number',
      )
    })

    it('does not propagate invalid cooldown (empty input) to parent', async () => {
      const value: SensorTriggerValue = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />)

      const cooldownInput = screen.getByLabelText(/cooldown.*minutes/i)
      fireEvent.change(cooldownInput, { target: { value: '' } })

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })

      expect(mockOnChange).not.toHaveBeenCalled()
    })

    it('does not propagate negative cooldown to parent', async () => {
      const value: SensorTriggerValue = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />)

      const cooldownInput = screen.getByLabelText(/cooldown.*minutes/i)
      fireEvent.change(cooldownInput, { target: { value: '-5' } })

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })

      expect(mockOnChange).not.toHaveBeenCalled()
    })

    it('does not propagate cooldown exceeding max', async () => {
      const value: SensorTriggerValue = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />)

      const cooldownInput = screen.getByLabelText(/cooldown.*minutes/i)
      fireEvent.change(cooldownInput, {
        target: {
          value: String(SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES + 1),
        },
      })

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })

      expect(mockOnChange).not.toHaveBeenCalled()
    })

    it('accepts max cooldown value', async () => {
      const value: SensorTriggerValue = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />)

      const cooldownInput = screen.getByLabelText(/cooldown.*minutes/i)
      fireEvent.change(cooldownInput, {
        target: {
          value: String(SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES),
        },
      })

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith({
          ...value,
          cooldown_minutes: SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES,
        })
      })
    })

    it('shows Zod error for cooldown exceeding max', async () => {
      render(
        <SensorTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const cooldownInput = screen.getByLabelText(/cooldown.*minutes/i)
      fireEvent.change(cooldownInput, {
        target: {
          value: String(SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES + 1),
        },
      })

      await waitFor(() => {
        const alert = screen.getByRole('alert')
        expect(alert).toBeInTheDocument()
        expect(alert.textContent).toMatch(/cannot exceed/i)
      })
    })

    it('shows parent-provided cooldown error', () => {
      const errors = { cooldown_minutes: 'Cooldown is too low' }

      render(
        <SensorTriggerForm
          value={defaultValue}
          onChange={mockOnChange}
          errors={errors}
        />,
      )

      expect(screen.getByText('Cooldown is too low')).toBeInTheDocument()
    })
  })

  describe('Preview Text Generation', () => {
    it('generates preview for light sensor with less than comparison', () => {
      const value: SensorTriggerValue = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />)

      expect(
        screen.getByText(/When light < 100 lux, cooldown: 5 min/i),
      ).toBeInTheDocument()
    })

    it('generates preview for temperature sensor with greater than or equal comparison', () => {
      const value: SensorTriggerValue = {
        sensor_type: 'temperature',
        comparison: 'gte',
        threshold: 25,
        cooldown_minutes: 10,
      }

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />)

      expect(
        screen.getByText(/When temperature ≥ 25 °C, cooldown: 10 min/i),
      ).toBeInTheDocument()
    })

    it('generates preview for motion sensor with equal comparison', () => {
      const value: SensorTriggerValue = {
        sensor_type: 'motion',
        comparison: 'eq',
        threshold: 1,
        cooldown_minutes: 2,
      }

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />)

      expect(
        screen.getByText(/When motion = 1, cooldown: 2 min/i),
      ).toBeInTheDocument()
    })

    it('generates preview with greater than comparison', () => {
      const value: SensorTriggerValue = {
        sensor_type: 'light',
        comparison: 'gt',
        threshold: 500,
        cooldown_minutes: 3,
      }

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />)

      expect(
        screen.getByText(/When light > 500 lux, cooldown: 3 min/i),
      ).toBeInTheDocument()
    })

    it('generates preview with less than or equal comparison', () => {
      const value: SensorTriggerValue = {
        sensor_type: 'temperature',
        comparison: 'lte',
        threshold: 15,
        cooldown_minutes: 7,
      }

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />)

      expect(
        screen.getByText(/When temperature ≤ 15 °C, cooldown: 7 min/i),
      ).toBeInTheDocument()
    })

    it('updates preview when sensor type changes', () => {
      const value: SensorTriggerValue = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      const { rerender } = render(
        <SensorTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText(/When light < 100 lux, cooldown: 5 min/i),
      ).toBeInTheDocument()

      const newValue = { ...value, sensor_type: 'temperature' }
      rerender(
        <SensorTriggerForm value={newValue} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText(/When temperature < 100 °C, cooldown: 5 min/i),
      ).toBeInTheDocument()
    })

    it('updates preview when comparison changes', () => {
      const value: SensorTriggerValue = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      const { rerender } = render(
        <SensorTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText(/When light < 100 lux, cooldown: 5 min/i),
      ).toBeInTheDocument()

      const newValue = { ...value, comparison: 'gte' }
      rerender(
        <SensorTriggerForm value={newValue} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText(/When light ≥ 100 lux, cooldown: 5 min/i),
      ).toBeInTheDocument()
    })

    it('updates preview when threshold changes', () => {
      const value: SensorTriggerValue = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      const { rerender } = render(
        <SensorTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText(/When light < 100 lux, cooldown: 5 min/i),
      ).toBeInTheDocument()

      const newValue = { ...value, threshold: 200 }
      rerender(
        <SensorTriggerForm value={newValue} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText(/When light < 200 lux, cooldown: 5 min/i),
      ).toBeInTheDocument()
    })

    it('updates preview when cooldown changes', () => {
      const value: SensorTriggerValue = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      const { rerender } = render(
        <SensorTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText(/When light < 100 lux, cooldown: 5 min/i),
      ).toBeInTheDocument()

      const newValue = { ...value, cooldown_minutes: 15 }
      rerender(
        <SensorTriggerForm value={newValue} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText(/When light < 100 lux, cooldown: 15 min/i),
      ).toBeInTheDocument()
    })
  })

  describe('Disabled State', () => {
    it('disables sensor type select when disabled prop is true', () => {
      render(
        <SensorTriggerForm onChange={mockOnChange} disabled={true} />,
      )

      const sensorTypeSelect = screen.getByLabelText(/sensor type/i)
      expect(sensorTypeSelect).toBeDisabled()
    })

    it('disables comparison select when disabled prop is true', () => {
      render(
        <SensorTriggerForm onChange={mockOnChange} disabled={true} />,
      )

      const comparisonSelect = screen.getByLabelText(/comparison/i)
      expect(comparisonSelect).toBeDisabled()
    })

    it('disables threshold input when disabled prop is true', () => {
      render(
        <SensorTriggerForm onChange={mockOnChange} disabled={true} />,
      )

      const thresholdInput = screen.getByLabelText(/threshold/i)
      expect(thresholdInput).toBeDisabled()
    })

    it('disables cooldown input when disabled prop is true', () => {
      render(
        <SensorTriggerForm onChange={mockOnChange} disabled={true} />,
      )

      const cooldownInput = screen.getByLabelText(/cooldown.*minutes/i)
      expect(cooldownInput).toBeDisabled()
    })

    it('does not disable inputs when disabled prop is false', () => {
      render(
        <SensorTriggerForm onChange={mockOnChange} disabled={false} />,
      )

      const sensorTypeSelect = screen.getByLabelText(/sensor type/i)
      const comparisonSelect = screen.getByLabelText(/comparison/i)
      const thresholdInput = screen.getByLabelText(/threshold/i)
      const cooldownInput = screen.getByLabelText(/cooldown.*minutes/i)

      expect(sensorTypeSelect).not.toBeDisabled()
      expect(comparisonSelect).not.toBeDisabled()
      expect(thresholdInput).not.toBeDisabled()
      expect(cooldownInput).not.toBeDisabled()
    })
  })

  describe('Dark Mode Styling', () => {
    it('applies dark mode classes to sensor type select', () => {
      render(<SensorTriggerForm onChange={mockOnChange} />)

      const sensorTypeSelect = screen.getByLabelText(/sensor type/i)
      expect(sensorTypeSelect).toHaveClass(
        'dark:bg-gray-800',
        'dark:text-white',
        'dark:border-gray-600',
      )
    })

    it('applies dark mode classes to comparison select', () => {
      render(<SensorTriggerForm onChange={mockOnChange} />)

      const comparisonSelect = screen.getByLabelText(/comparison/i)
      expect(comparisonSelect).toHaveClass(
        'dark:bg-gray-800',
        'dark:text-white',
        'dark:border-gray-600',
      )
    })

    it('applies dark mode classes to threshold input', () => {
      render(<SensorTriggerForm onChange={mockOnChange} />)

      const thresholdInput = screen.getByLabelText(/threshold/i)
      expect(thresholdInput).toHaveClass(
        'dark:bg-gray-800',
        'dark:text-white',
        'dark:border-gray-600',
      )
    })

    it('applies dark mode classes to cooldown input', () => {
      render(<SensorTriggerForm onChange={mockOnChange} />)

      const cooldownInput = screen.getByLabelText(/cooldown.*minutes/i)
      expect(cooldownInput).toHaveClass(
        'dark:bg-gray-800',
        'dark:text-white',
        'dark:border-gray-600',
      )
    })

    it('applies dark mode classes to labels', () => {
      render(<SensorTriggerForm onChange={mockOnChange} />)

      const header = screen.getByText('Sensor Configuration')
      expect(header).toHaveClass('dark:text-white')
    })

    it('applies dark mode classes to preview text', () => {
      const value: SensorTriggerValue = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />)

      const previewText = screen.getByText(
        /When light < 100 lux, cooldown: 5 min/i,
      )
      expect(previewText).toHaveClass(
        'dark:text-gray-300',
        'dark:bg-gray-800',
      )
    })
  })

  describe('onChange Callback', () => {
    it('calls onChange with complete trigger object when sensor type changes', async () => {
      const value: SensorTriggerValue = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />)

      const sensorTypeSelect = screen.getByLabelText(/sensor type/i)
      fireEvent.change(sensorTypeSelect, {
        target: { value: 'temperature' },
      })

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith({
          sensor_type: 'temperature',
          comparison: 'lt',
          threshold: 100,
          cooldown_minutes: 5,
        })
      })
    })

    it('calls onChange with complete trigger object when comparison changes', async () => {
      const value: SensorTriggerValue = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />)

      const comparisonSelect = screen.getByLabelText(/comparison/i)
      fireEvent.change(comparisonSelect, { target: { value: 'gte' } })

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith({
          sensor_type: 'light',
          comparison: 'gte',
          threshold: 100,
          cooldown_minutes: 5,
        })
      })
    })

    it('calls onChange with complete trigger object when threshold changes', async () => {
      const value: SensorTriggerValue = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />)

      const thresholdInput = screen.getByLabelText(/threshold/i)
      fireEvent.change(thresholdInput, { target: { value: '200' } })

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith({
          sensor_type: 'light',
          comparison: 'lt',
          threshold: 200,
          cooldown_minutes: 5,
        })
      })
    })

    it('calls onChange with complete trigger object when cooldown changes', async () => {
      const value: SensorTriggerValue = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      }

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />)

      const cooldownInput = screen.getByLabelText(/cooldown.*minutes/i)
      fireEvent.change(cooldownInput, { target: { value: '10' } })

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith({
          sensor_type: 'light',
          comparison: 'lt',
          threshold: 100,
          cooldown_minutes: 10,
        })
      })
    })
  })

  describe('Prop sync (external value changes)', () => {
    it('updates inputs when value prop changes externally', () => {
      const value: SensorTriggerValue = { ...defaultValue }

      const { rerender } = render(
        <SensorTriggerForm value={value} onChange={mockOnChange} />,
      )

      rerender(
        <SensorTriggerForm
          value={{
            ...value,
            sensor_type: 'temperature',
            threshold: 50,
          }}
          onChange={mockOnChange}
        />,
      )

      const sensorTypeSelect = screen.getByLabelText(/sensor type/i)
      expect(sensorTypeSelect).toHaveValue('temperature')

      const thresholdInput = screen.getByLabelText(/threshold/i)
      expect(thresholdInput).toHaveValue(50)
    })

    it('does not reset form when value prop is unchanged', async () => {
      const user = userEvent.setup()
      const value: SensorTriggerValue = { ...defaultValue }

      const { rerender } = render(
        <SensorTriggerForm value={value} onChange={mockOnChange} />,
      )

      // User modifies threshold
      const thresholdInput = screen.getByLabelText(/threshold/i)
      await user.clear(thresholdInput)
      await user.type(thresholdInput, '250')

      // Parent re-renders with same value (e.g. unrelated state change)
      rerender(
        <SensorTriggerForm value={value} onChange={mockOnChange} />,
      )

      // User's in-progress edit should NOT be overwritten
      expect(thresholdInput).toHaveValue(250)
    })
  })
})

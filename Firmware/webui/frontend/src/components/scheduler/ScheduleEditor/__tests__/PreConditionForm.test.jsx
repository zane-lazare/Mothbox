import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import PreConditionForm from '../PreConditionForm'

describe('PreConditionForm', () => {
  let mockOnChange

  beforeEach(() => {
    mockOnChange = vi.fn()
  })

  describe('Toggle behavior', () => {
    it('renders toggle unchecked when preCondition is null', () => {
      render(
        <PreConditionForm preCondition={null} onChange={mockOnChange} routineIndex={0} />
      )

      const toggle = screen.getByTestId('pre-condition-toggle-0')
      expect(toggle).not.toBeChecked()
    })

    it('renders toggle checked when preCondition has value', () => {
      const preCondition = {
        trigger_type: 'sensor',
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
      }

      render(
        <PreConditionForm preCondition={preCondition} onChange={mockOnChange} routineIndex={0} />
      )

      const toggle = screen.getByTestId('pre-condition-toggle-0')
      expect(toggle).toBeChecked()
    })

    it('shows conditional fields only when enabled', () => {
      const { rerender } = render(
        <PreConditionForm preCondition={null} onChange={mockOnChange} routineIndex={0} />
      )

      // Fields should not be visible when disabled
      expect(screen.queryByTestId('pre-condition-sensor')).not.toBeInTheDocument()
      expect(screen.queryByTestId('pre-condition-op')).not.toBeInTheDocument()
      expect(screen.queryByTestId('pre-condition-threshold')).not.toBeInTheDocument()

      // Re-render with preCondition enabled
      const preCondition = {
        trigger_type: 'sensor',
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
      }
      rerender(
        <PreConditionForm preCondition={preCondition} onChange={mockOnChange} routineIndex={0} />
      )

      // Fields should be visible when enabled
      expect(screen.getByTestId('pre-condition-sensor')).toBeInTheDocument()
      expect(screen.getByTestId('pre-condition-op')).toBeInTheDocument()
      expect(screen.getByTestId('pre-condition-threshold')).toBeInTheDocument()
    })

    it('enables form and calls onChange with default values when toggled on', () => {
      render(
        <PreConditionForm preCondition={null} onChange={mockOnChange} routineIndex={0} />
      )

      const toggle = screen.getByTestId('pre-condition-toggle-0')
      fireEvent.click(toggle)

      expect(mockOnChange).toHaveBeenCalledWith({
        trigger_type: 'sensor',
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
      })
    })

    it('disables form and calls onChange with null when toggled off', () => {
      const preCondition = {
        trigger_type: 'sensor',
        sensor_type: 'temperature',
        comparison: 'gt',
        threshold: 25,
      }

      render(
        <PreConditionForm preCondition={preCondition} onChange={mockOnChange} routineIndex={0} />
      )

      const toggle = screen.getByTestId('pre-condition-toggle-0')
      fireEvent.click(toggle)

      expect(mockOnChange).toHaveBeenCalledWith(null)
    })
  })

  describe('Field updates', () => {
    const defaultPreCondition = {
      trigger_type: 'sensor',
      sensor_type: 'light',
      comparison: 'lt',
      threshold: 100,
    }

    it('updates sensor type correctly', () => {
      render(
        <PreConditionForm
          preCondition={defaultPreCondition}
          onChange={mockOnChange}
          routineIndex={0}
        />
      )

      const sensorSelect = screen.getByTestId('pre-condition-sensor')
      fireEvent.change(sensorSelect, { target: { value: 'temperature' } })

      expect(mockOnChange).toHaveBeenCalledWith({
        ...defaultPreCondition,
        sensor_type: 'temperature',
      })
    })

    it('updates condition operator correctly', () => {
      render(
        <PreConditionForm
          preCondition={defaultPreCondition}
          onChange={mockOnChange}
          routineIndex={0}
        />
      )

      const opSelect = screen.getByTestId('pre-condition-op')
      fireEvent.change(opSelect, { target: { value: 'gt' } })

      expect(mockOnChange).toHaveBeenCalledWith({
        ...defaultPreCondition,
        comparison: 'gt',
      })
    })

    it('updates threshold value correctly', () => {
      render(
        <PreConditionForm
          preCondition={defaultPreCondition}
          onChange={mockOnChange}
          routineIndex={0}
        />
      )

      const thresholdInput = screen.getByTestId('pre-condition-threshold')
      fireEvent.change(thresholdInput, { target: { value: '50' } })

      expect(mockOnChange).toHaveBeenCalledWith({
        ...defaultPreCondition,
        threshold: 50,
      })
    })

    it('shows validation error for empty threshold input', () => {
      render(
        <PreConditionForm
          preCondition={defaultPreCondition}
          onChange={mockOnChange}
          routineIndex={0}
        />
      )

      const thresholdInput = screen.getByTestId('pre-condition-threshold')
      fireEvent.change(thresholdInput, { target: { value: '' } })

      // Should show error and NOT call onChange
      expect(screen.getByTestId('pre-condition-error')).toBeInTheDocument()
      expect(screen.getByTestId('pre-condition-error')).toHaveTextContent(
        'Threshold must be a positive number'
      )
      expect(mockOnChange).not.toHaveBeenCalled()
    })

    it('shows validation error for negative threshold', () => {
      render(
        <PreConditionForm
          preCondition={defaultPreCondition}
          onChange={mockOnChange}
          routineIndex={0}
        />
      )

      const thresholdInput = screen.getByTestId('pre-condition-threshold')
      fireEvent.change(thresholdInput, { target: { value: '-10' } })

      // Should show error and NOT call onChange
      expect(screen.getByTestId('pre-condition-error')).toBeInTheDocument()
      expect(mockOnChange).not.toHaveBeenCalled()
    })

    it('clears validation error when valid value entered', () => {
      render(
        <PreConditionForm
          preCondition={defaultPreCondition}
          onChange={mockOnChange}
          routineIndex={0}
        />
      )

      const thresholdInput = screen.getByTestId('pre-condition-threshold')

      // First enter invalid value
      fireEvent.change(thresholdInput, { target: { value: '' } })
      expect(screen.getByTestId('pre-condition-error')).toBeInTheDocument()

      // Then enter valid value
      fireEvent.change(thresholdInput, { target: { value: '50' } })
      expect(screen.queryByTestId('pre-condition-error')).not.toBeInTheDocument()
    })

    it('clears validation error when toggling off and back on', () => {
      const { rerender } = render(
        <PreConditionForm
          preCondition={defaultPreCondition}
          onChange={mockOnChange}
          routineIndex={0}
        />
      )

      // 1. Enter invalid value -> error shows
      const thresholdInput = screen.getByTestId('pre-condition-threshold')
      fireEvent.change(thresholdInput, { target: { value: '' } })
      expect(screen.getByTestId('pre-condition-error')).toBeInTheDocument()

      // 2. Toggle off
      const toggle = screen.getByTestId('pre-condition-toggle-0')
      fireEvent.click(toggle)

      // 3. Toggle on (simulate parent passing new preCondition after toggle)
      rerender(
        <PreConditionForm
          preCondition={defaultPreCondition}
          onChange={mockOnChange}
          routineIndex={0}
        />
      )
      fireEvent.click(screen.getByTestId('pre-condition-toggle-0'))

      // 4. Verify error is gone after re-enabling
      expect(screen.queryByTestId('pre-condition-error')).not.toBeInTheDocument()
    })
  })

  describe('Disabled state', () => {
    it('prevents toggle interaction when disabled', () => {
      render(
        <PreConditionForm
          preCondition={null}
          onChange={mockOnChange}
          routineIndex={0}
          disabled={true}
        />
      )

      const toggle = screen.getByTestId('pre-condition-toggle-0')
      expect(toggle).toBeDisabled()
    })

    it('prevents field interaction when disabled', () => {
      const preCondition = {
        trigger_type: 'sensor',
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
      }

      render(
        <PreConditionForm
          preCondition={preCondition}
          onChange={mockOnChange}
          routineIndex={0}
          disabled={true}
        />
      )

      expect(screen.getByTestId('pre-condition-sensor')).toBeDisabled()
      expect(screen.getByTestId('pre-condition-op')).toBeDisabled()
      expect(screen.getByTestId('pre-condition-threshold')).toBeDisabled()
    })
  })

  describe('data-testid attributes', () => {
    it('has correct toggle testid with routineIndex', () => {
      render(
        <PreConditionForm preCondition={null} onChange={mockOnChange} routineIndex={5} />
      )

      expect(screen.getByTestId('pre-condition-toggle-5')).toBeInTheDocument()
    })

    it('has all required field testids', () => {
      const preCondition = {
        trigger_type: 'sensor',
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
      }

      render(
        <PreConditionForm preCondition={preCondition} onChange={mockOnChange} routineIndex={0} />
      )

      expect(screen.getByTestId('pre-condition-toggle-0')).toBeInTheDocument()
      expect(screen.getByTestId('pre-condition-sensor')).toBeInTheDocument()
      expect(screen.getByTestId('pre-condition-op')).toBeInTheDocument()
      expect(screen.getByTestId('pre-condition-threshold')).toBeInTheDocument()
    })
  })

  describe('Sensor type options', () => {
    it('shows light and temperature options (not motion per issue spec)', () => {
      const preCondition = {
        trigger_type: 'sensor',
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
      }

      render(
        <PreConditionForm preCondition={preCondition} onChange={mockOnChange} routineIndex={0} />
      )

      const sensorSelect = screen.getByTestId('pre-condition-sensor')
      const options = sensorSelect.querySelectorAll('option')
      const optionValues = Array.from(options).map((o) => o.value)

      expect(optionValues).toContain('light')
      expect(optionValues).toContain('temperature')
      expect(optionValues).not.toContain('motion')
    })
  })

  describe('Operator options', () => {
    it('shows only lt/gt/eq operators per issue #325 spec (not gte/lte)', () => {
      const preCondition = {
        trigger_type: 'sensor',
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
      }

      render(
        <PreConditionForm preCondition={preCondition} onChange={mockOnChange} routineIndex={0} />
      )

      const opSelect = screen.getByTestId('pre-condition-op')
      const options = opSelect.querySelectorAll('option')
      const optionValues = Array.from(options).map((o) => o.value)

      expect(optionValues).toContain('lt')
      expect(optionValues).toContain('gt')
      expect(optionValues).toContain('eq')
      expect(optionValues).not.toContain('gte')
      expect(optionValues).not.toContain('lte')
      expect(optionValues).toHaveLength(3)
    })

    it('shows correct human-readable labels', () => {
      const preCondition = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
      }

      render(
        <PreConditionForm preCondition={preCondition} onChange={mockOnChange} routineIndex={0} />
      )

      const opSelect = screen.getByTestId('pre-condition-op')

      expect(opSelect).toHaveTextContent('is below')
      expect(opSelect).toHaveTextContent('is above')
      expect(opSelect).toHaveTextContent('equals')
    })
  })

  describe('Label and accessibility', () => {
    it('renders label with correct text', () => {
      render(
        <PreConditionForm preCondition={null} onChange={mockOnChange} routineIndex={0} />
      )

      expect(screen.getByText('Only run if sensor condition met')).toBeInTheDocument()
    })

    it('label is associated with toggle via htmlFor', () => {
      render(
        <PreConditionForm preCondition={null} onChange={mockOnChange} routineIndex={0} />
      )

      const toggle = screen.getByTestId('pre-condition-toggle-0')
      const label = screen.getByText('Only run if sensor condition met')

      expect(label).toHaveAttribute('for', 'pre-condition-toggle-0')
      expect(toggle).toHaveAttribute('id', 'pre-condition-toggle-0')
    })
  })

  describe('useEffect sync behavior', () => {
    it('syncs internal enabled state when preCondition prop changes externally', () => {
      const { rerender } = render(
        <PreConditionForm preCondition={null} onChange={mockOnChange} routineIndex={0} />
      )

      // Initially unchecked
      expect(screen.getByTestId('pre-condition-toggle-0')).not.toBeChecked()

      // Parent provides preCondition - toggle should sync to checked
      rerender(
        <PreConditionForm
          preCondition={{ sensor_type: 'light', comparison: 'lt', threshold: 50 }}
          onChange={mockOnChange}
          routineIndex={0}
        />
      )
      expect(screen.getByTestId('pre-condition-toggle-0')).toBeChecked()

      // Parent removes preCondition - toggle should sync to unchecked
      rerender(
        <PreConditionForm preCondition={null} onChange={mockOnChange} routineIndex={0} />
      )
      expect(screen.getByTestId('pre-condition-toggle-0')).not.toBeChecked()
    })
  })

  describe('Multiple instances', () => {
    it('multiple instances with different routineIndex do not conflict', () => {
      const preCondition1 = { sensor_type: 'light', comparison: 'lt', threshold: 100 }
      const preCondition2 = { sensor_type: 'temperature', comparison: 'gt', threshold: 25 }
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
        </>
      )

      // Both toggles should be present with unique IDs
      expect(screen.getByTestId('pre-condition-toggle-0')).toBeInTheDocument()
      expect(screen.getByTestId('pre-condition-toggle-1')).toBeInTheDocument()

      // Changing one should not affect the other
      const toggle0 = screen.getByTestId('pre-condition-toggle-0')
      fireEvent.click(toggle0)

      expect(onChange1).toHaveBeenCalledWith(null)
      expect(onChange2).not.toHaveBeenCalled()
    })
  })

  describe('Edge cases', () => {
    it('handles invalid sensor_type gracefully by falling back to first option', () => {
      const preCondition = {
        sensor_type: 'invalid_sensor',
        comparison: 'lt',
        threshold: 100,
      }
      render(
        <PreConditionForm preCondition={preCondition} onChange={mockOnChange} routineIndex={0} />
      )

      // HTML select falls back to first valid option when value doesn't match
      const sensorSelect = screen.getByTestId('pre-condition-sensor')
      expect(sensorSelect).toBeInTheDocument()
      expect(sensorSelect.value).toBe('light')
    })

    it('accepts decimal threshold values', () => {
      const preCondition = { sensor_type: 'light', comparison: 'lt', threshold: 100 }
      render(
        <PreConditionForm preCondition={preCondition} onChange={mockOnChange} routineIndex={0} />
      )

      const thresholdInput = screen.getByTestId('pre-condition-threshold')
      fireEvent.change(thresholdInput, { target: { value: '50.5' } })

      expect(mockOnChange).toHaveBeenCalledWith({
        ...preCondition,
        threshold: 50.5,
      })
      expect(screen.queryByTestId('pre-condition-error')).not.toBeInTheDocument()
    })

    it('accepts zero as valid threshold value', () => {
      const preCondition = { sensor_type: 'light', comparison: 'lt', threshold: 100 }
      render(
        <PreConditionForm preCondition={preCondition} onChange={mockOnChange} routineIndex={0} />
      )

      const thresholdInput = screen.getByTestId('pre-condition-threshold')
      fireEvent.change(thresholdInput, { target: { value: '0' } })

      expect(mockOnChange).toHaveBeenCalledWith({
        ...preCondition,
        threshold: 0,
      })
      expect(screen.queryByTestId('pre-condition-error')).not.toBeInTheDocument()
    })
  })
})

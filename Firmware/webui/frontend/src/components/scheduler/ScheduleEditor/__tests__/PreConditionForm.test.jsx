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

    it('handles empty threshold input gracefully', () => {
      render(
        <PreConditionForm
          preCondition={defaultPreCondition}
          onChange={mockOnChange}
          routineIndex={0}
        />
      )

      const thresholdInput = screen.getByTestId('pre-condition-threshold')
      fireEvent.change(thresholdInput, { target: { value: '' } })

      expect(mockOnChange).toHaveBeenCalledWith({
        ...defaultPreCondition,
        threshold: 0,
      })
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
    it('shows all three operator options with correct labels', () => {
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
})

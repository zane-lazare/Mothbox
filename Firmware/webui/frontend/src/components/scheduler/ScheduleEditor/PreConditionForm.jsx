import { useState, useEffect } from 'react'
import PropTypes from 'prop-types'
import { SENSOR_TYPES } from './constants'

/**
 * PreConditionForm - Optional sensor condition toggle with configuration
 *
 * Pre-conditions gate routine execution based on sensor readings.
 * When enabled, actions only run if the sensor condition is met.
 *
 * @component
 * @param {Object} props
 * @param {Object|null} props.preCondition - Current pre-condition config or null if disabled
 * @param {Function} props.onChange - Callback when pre-condition changes
 * @param {number} props.routineIndex - Index of the routine (for unique test IDs)
 * @param {boolean} [props.disabled=false] - Whether the form is disabled
 */
function PreConditionForm({ preCondition, onChange, routineIndex, disabled = false }) {
  const [enabled, setEnabled] = useState(!!preCondition)

  // Sync internal state with prop changes
  useEffect(() => {
    setEnabled(!!preCondition)
  }, [preCondition])

  /**
   * Handle toggle change - enable/disable pre-condition
   */
  const handleToggle = (e) => {
    const isEnabled = e.target.checked
    setEnabled(isEnabled)
    if (!isEnabled) {
      onChange(null)
    } else {
      // Default pre-condition
      onChange({
        trigger_type: 'sensor',
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
      })
    }
  }

  /**
   * Handle field change - update specific field in pre-condition
   */
  const handleFieldChange = (field, value) => {
    onChange({ ...preCondition, [field]: value })
  }

  return (
    <div className="space-y-3">
      {/* Toggle */}
      <div className="flex items-center gap-3 text-sm">
        <input
          type="checkbox"
          id={`pre-condition-toggle-${routineIndex}`}
          checked={enabled}
          onChange={handleToggle}
          disabled={disabled}
          className="rounded border-gray-600 disabled:opacity-50"
          data-testid={`pre-condition-toggle-${routineIndex}`}
        />
        <label
          htmlFor={`pre-condition-toggle-${routineIndex}`}
          className="text-gray-400 cursor-pointer"
        >
          Only run if sensor condition met
        </label>
      </div>

      {/* Conditional fields */}
      {enabled && preCondition && (
        <div className="pl-6 space-y-3">
          <div className="flex items-center gap-3 text-sm flex-wrap">
            {/* Sensor type */}
            <select
              value={preCondition.sensor_type || 'light'}
              onChange={(e) => handleFieldChange('sensor_type', e.target.value)}
              disabled={disabled}
              className="bg-transparent border border-gray-800 rounded px-2 py-1 text-white
                         focus:border-gray-600 focus:outline-none
                         disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="pre-condition-sensor"
            >
              {SENSOR_TYPES.filter((s) => s.value !== 'motion').map((sensor) => (
                <option key={sensor.value} value={sensor.value}>
                  {sensor.label}
                </option>
              ))}
            </select>

            {/* Operator */}
            <select
              value={preCondition.comparison || 'lt'}
              onChange={(e) => handleFieldChange('comparison', e.target.value)}
              disabled={disabled}
              className="bg-transparent border border-gray-800 rounded px-2 py-1 text-white
                         focus:border-gray-600 focus:outline-none
                         disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="pre-condition-op"
            >
              <option value="lt">is below</option>
              <option value="gt">is above</option>
              <option value="eq">equals</option>
            </select>

            {/* Threshold */}
            <input
              type="number"
              value={preCondition.threshold ?? 100}
              onChange={(e) => handleFieldChange('threshold', parseFloat(e.target.value) || 0)}
              disabled={disabled}
              className="w-20 bg-transparent border border-gray-800 rounded px-2 py-1 text-white text-center
                         focus:border-gray-600 focus:outline-none
                         disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="pre-condition-threshold"
            />
          </div>
        </div>
      )}
    </div>
  )
}

PreConditionForm.propTypes = {
  /** Pre-condition config or null if disabled */
  preCondition: PropTypes.shape({
    trigger_type: PropTypes.string,
    sensor_type: PropTypes.string,
    comparison: PropTypes.string,
    threshold: PropTypes.number,
  }),
  /** Callback when pre-condition changes */
  onChange: PropTypes.func.isRequired,
  /** Index of the routine for unique test IDs */
  routineIndex: PropTypes.number.isRequired,
  /** Whether the form is disabled */
  disabled: PropTypes.bool,
}

export default PreConditionForm

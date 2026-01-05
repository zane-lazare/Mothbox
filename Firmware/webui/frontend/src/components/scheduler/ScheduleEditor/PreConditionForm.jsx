import { useState, useEffect } from 'react'
import PropTypes from 'prop-types'
import { SENSOR_TYPES, validateNumericInput } from './constants'
import { NUMERIC_ERRORS } from './errorMessages'

/** Default pre-condition when enabled */
const DEFAULT_PRE_CONDITION = {
  trigger_type: 'sensor',
  sensor_type: 'light',
  comparison: 'lt',
  threshold: 100,
}

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
  const [thresholdError, setThresholdError] = useState(null)

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
    setThresholdError(null)
    if (!isEnabled) {
      onChange(null)
    } else {
      onChange(DEFAULT_PRE_CONDITION)
    }
  }

  /**
   * Handle field change - update specific field in pre-condition
   */
  const handleFieldChange = (field, value) => {
    onChange({ ...preCondition, [field]: value })
  }

  /**
   * Handle threshold change with validation
   * Uses validateNumericInput for consistent validation across scheduler forms
   */
  const handleThresholdChange = (newThreshold) => {
    const validated = validateNumericInput(newThreshold, 0)
    if (validated === null) {
      setThresholdError(NUMERIC_ERRORS.INVALID_THRESHOLD)
      return
    }
    setThresholdError(null)
    onChange({ ...preCondition, threshold: validated })
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
            {/* Sensor type - filtered to light/temperature per issue #325 */}
            <select
              value={preCondition?.sensor_type ?? 'light'}
              onChange={(e) => handleFieldChange('sensor_type', e.target.value)}
              disabled={disabled}
              aria-label="Sensor type"
              className="rounded-md border border-gray-300 dark:border-gray-600
                         bg-white dark:bg-gray-800 px-2 py-1 text-gray-900 dark:text-white
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent
                         disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="pre-condition-sensor"
            >
              {SENSOR_TYPES.filter((s) => s.value !== 'motion').map((sensor) => (
                <option key={sensor.value} value={sensor.value}>
                  {sensor.label}
                </option>
              ))}
            </select>

            {/*
             * Comparison operator - only lt/gt/eq per issue #325 spec.
             * SENSOR_COMPARISONS in constants.js also has gte/lte, but
             * pre-conditions only need basic comparisons.
             */}
            <select
              value={preCondition?.comparison ?? 'lt'}
              onChange={(e) => handleFieldChange('comparison', e.target.value)}
              disabled={disabled}
              aria-label="Comparison operator"
              className="rounded-md border border-gray-300 dark:border-gray-600
                         bg-white dark:bg-gray-800 px-2 py-1 text-gray-900 dark:text-white
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent
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
              min={0}
              value={preCondition?.threshold ?? 100}
              onChange={(e) => handleThresholdChange(e.target.value)}
              disabled={disabled}
              aria-label="Threshold value"
              className="w-20 rounded-md border border-gray-300 dark:border-gray-600
                         bg-white dark:bg-gray-800 px-2 py-1 text-gray-900 dark:text-white text-center
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent
                         disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="pre-condition-threshold"
            />
          </div>
          {/* Threshold validation error */}
          {thresholdError && (
            <p className="text-sm text-red-600 dark:text-red-400" data-testid="pre-condition-error">
              {thresholdError}
            </p>
          )}
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

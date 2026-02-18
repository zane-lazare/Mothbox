import { useState, useEffect } from 'react'
import PropTypes from 'prop-types'
import { SENSOR_TYPES, SCHEDULE_LIMITS, validateNumericInput } from './constants'
import { NUMERIC_ERRORS, TIME_ERRORS } from './errorMessages'

/** Default pre-condition when enabled */
const DEFAULT_PRE_CONDITION = {
  trigger_type: 'sensor',
  sensor_type: 'light',
  comparison: 'lt',
  threshold: 100,
  cooldown_minutes: 5,
}

/** Unit labels for sensor types */
const SENSOR_UNITS = {
  light: 'lux',
  temperature: '°C',
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
  const [cooldownError, setCooldownError] = useState(null)

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
    setCooldownError(null)
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

  /**
   * Handle time window toggle - enable/disable time window restriction
   */
  const handleTimeWindowToggle = (e) => {
    const isEnabled = e.target.checked
    if (isEnabled) {
      onChange({ ...preCondition, time_window: { start_time: '21:00', end_time: '06:00' } })
    } else {
      onChange({ ...preCondition, time_window: null })
    }
  }

  /**
   * Handle time window field change (start_time or end_time)
   */
  const handleTimeWindowChange = (field, value) => {
    onChange({
      ...preCondition,
      time_window: { ...preCondition.time_window, [field]: value },
    })
  }

  /**
   * Handle cooldown change with validation (1-60 minutes)
   */
  const handleCooldownChange = (newCooldown) => {
    const validated = validateNumericInput(newCooldown, 1, SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES)
    if (validated === null) {
      setCooldownError(NUMERIC_ERRORS.INVALID_COOLDOWN(SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES))
      return
    }
    setCooldownError(null)
    onChange({ ...preCondition, cooldown_minutes: validated })
  }

  // Validate same start/end time (computed from props, not state)
  const timeWindowError =
    preCondition?.time_window?.start_time &&
    preCondition?.time_window?.end_time &&
    preCondition.time_window.start_time === preCondition.time_window.end_time
      ? TIME_ERRORS.SAME_START_END
      : null

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
            <span className="text-xs text-gray-500 dark:text-gray-400" data-testid="pre-condition-unit">
              {SENSOR_UNITS[preCondition?.sensor_type] || ''}
            </span>
          </div>
          {/* Threshold validation error */}
          {thresholdError && (
            <p className="text-sm text-red-600 dark:text-red-400" data-testid="pre-condition-error">
              {thresholdError}
            </p>
          )}
          {/* Cooldown */}
          <div className="flex items-center gap-2 text-sm">
            <span className="text-gray-400">Cooldown:</span>
            <input
              type="number"
              min={1}
              max={60}
              value={preCondition?.cooldown_minutes ?? 5}
              onChange={(e) => handleCooldownChange(e.target.value)}
              disabled={disabled}
              aria-label="Cooldown minutes"
              className="w-16 rounded-md border border-gray-300 dark:border-gray-600
                         bg-white dark:bg-gray-800 px-2 py-1 text-gray-900 dark:text-white text-center
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent
                         disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="pre-condition-cooldown"
            />
            <span className="text-xs text-gray-500 dark:text-gray-400">minutes</span>
          </div>
          {cooldownError && (
            <p className="text-sm text-red-600 dark:text-red-400" data-testid="pre-condition-cooldown-error">
              {cooldownError}
            </p>
          )}
          {/* Time window toggle */}
          <div className="flex items-center gap-3 text-sm">
            <input
              type="checkbox"
              id={`pre-condition-tw-toggle-${routineIndex}`}
              checked={!!preCondition?.time_window}
              onChange={handleTimeWindowToggle}
              disabled={disabled}
              className="rounded border-gray-600 disabled:opacity-50"
              data-testid="pre-condition-time-window-toggle"
            />
            <label
              htmlFor={`pre-condition-tw-toggle-${routineIndex}`}
              className="text-gray-400 cursor-pointer"
            >
              Restrict to time window
            </label>
          </div>

          {/* Time window fields */}
          {preCondition?.time_window && (
            <div className="pl-6 flex items-center gap-2 text-sm">
              <input
                type="time"
                value={preCondition.time_window.start_time || '21:00'}
                onChange={(e) => handleTimeWindowChange('start_time', e.target.value)}
                disabled={disabled}
                aria-label="Time window start"
                className="rounded-md border border-gray-300 dark:border-gray-600
                           bg-white dark:bg-gray-800 px-2 py-1 text-gray-900 dark:text-white
                           focus:ring-2 focus:ring-blue-500 focus:border-transparent
                           disabled:opacity-50 disabled:cursor-not-allowed"
                data-testid="pre-condition-tw-start"
              />
              <span className="text-gray-400">to</span>
              <input
                type="time"
                value={preCondition.time_window.end_time || '06:00'}
                onChange={(e) => handleTimeWindowChange('end_time', e.target.value)}
                disabled={disabled}
                aria-label="Time window end"
                className="rounded-md border border-gray-300 dark:border-gray-600
                           bg-white dark:bg-gray-800 px-2 py-1 text-gray-900 dark:text-white
                           focus:ring-2 focus:ring-blue-500 focus:border-transparent
                           disabled:opacity-50 disabled:cursor-not-allowed"
                data-testid="pre-condition-tw-end"
              />
            </div>
          )}
          {/* Time window validation error */}
          {timeWindowError && (
            <p className="pl-6 text-sm text-red-600 dark:text-red-400" data-testid="pre-condition-tw-error">
              {timeWindowError}
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
    cooldown_minutes: PropTypes.number,
    time_window: PropTypes.shape({
      start_time: PropTypes.string,
      end_time: PropTypes.string,
    }),
  }),
  /** Callback when pre-condition changes */
  onChange: PropTypes.func.isRequired,
  /** Index of the routine for unique test IDs */
  routineIndex: PropTypes.number.isRequired,
  /** Whether the form is disabled */
  disabled: PropTypes.bool,
}

export default PreConditionForm

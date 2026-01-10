import PropTypes from 'prop-types'
import { INTERVAL_UNITS } from './constants'

// Maximum interval values
const MAX_MINUTES = 1440 // 24 hours
const MAX_HOURS = 24

/**
 * IntervalTriggerForm Component
 *
 * Form for configuring interval-based triggers with optional time window.
 *
 * @component
 */
function IntervalTriggerForm({ trigger, onChange, disabled = false, error = null }) {
  const intervalMinutes = trigger?.interval_minutes || 15
  const timeWindow = trigger?.time_window || null

  // Derive display unit from interval_minutes (syncs with parent updates)
  const displayUnit = (intervalMinutes >= 60 && intervalMinutes % 60 === 0)
    ? 'hours'
    : 'minutes'

  const displayValue = displayUnit === 'hours'
    ? intervalMinutes / 60
    : intervalMinutes

  // Check if time window spans overnight (start > end)
  const isOvernightWindow = timeWindow &&
    timeWindow.start_time &&
    timeWindow.end_time &&
    timeWindow.start_time > timeWindow.end_time

  /**
   * Handle value change with min/max validation
   */
  const handleValueChange = (e) => {
    const parsed = parseInt(e.target.value, 10)
    const maxValue = displayUnit === 'hours' ? MAX_HOURS : MAX_MINUTES
    const value = isNaN(parsed) ? 1 : Math.max(1, Math.min(parsed, maxValue))
    const multiplier = INTERVAL_UNITS.find(u => u.value === displayUnit)?.multiplier || 1
    const newIntervalMinutes = value * multiplier
    onChange({
      ...trigger,
      interval_minutes: newIntervalMinutes,
    })
  }

  /**
   * Handle unit change - converts value to new unit
   */
  const handleUnitChange = (e) => {
    const newUnit = e.target.value
    // When switching to hours, round up to nearest hour (minimum 1 hour = 60 min)
    // When switching to minutes, keep same interval
    if (newUnit === 'hours') {
      const hours = Math.max(1, Math.min(Math.ceil(intervalMinutes / 60), MAX_HOURS))
      onChange({
        ...trigger,
        interval_minutes: hours * 60,
      })
    } else {
      // Switching to minutes - keep same interval but ensure within bounds
      onChange({
        ...trigger,
        interval_minutes: Math.max(1, Math.min(intervalMinutes, MAX_MINUTES)),
      })
    }
  }

  /**
   * Handle time window toggle
   */
  const handleTimeWindowToggle = (e) => {
    if (e.target.checked) {
      onChange({
        ...trigger,
        time_window: {
          start_time: '18:00',
          end_time: '06:00',
        },
      })
    } else {
      onChange({
        ...trigger,
        time_window: null,
      })
    }
  }

  /**
   * Handle time window start change
   */
  const handleStartTimeChange = (e) => {
    onChange({
      ...trigger,
      time_window: {
        ...timeWindow,
        start_time: e.target.value,
      },
    })
  }

  /**
   * Handle time window end change
   */
  const handleEndTimeChange = (e) => {
    onChange({
      ...trigger,
      time_window: {
        ...timeWindow,
        end_time: e.target.value,
      },
    })
  }

  return (
    <div className="border border-gray-800 rounded-lg p-4" data-testid="interval-trigger-form">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-sm text-white">Interval</span>
        <span className="text-xs text-gray-600">repeat at fixed intervals</span>
      </div>

      <div className="space-y-4">
        {/* Interval Value and Unit */}
        <div className="flex items-center gap-3 text-sm">
          <span className="text-gray-500">Every</span>
          <input
            type="number"
            min="1"
            max={displayUnit === 'hours' ? MAX_HOURS : MAX_MINUTES}
            value={displayValue}
            onChange={handleValueChange}
            disabled={disabled}
            className={`w-16 bg-transparent border rounded px-2 py-1 text-white text-center
                       focus:outline-none
                       disabled:opacity-50 disabled:cursor-not-allowed
                       ${error ? 'border-red-500 focus:border-red-400' : 'border-gray-800 focus:border-gray-600'}`}
            data-testid="interval-minutes"
          />
          <select
            value={displayUnit}
            onChange={handleUnitChange}
            disabled={disabled}
            className="bg-transparent border border-gray-800 rounded px-2 py-1 text-white
                       focus:border-gray-600 focus:outline-none
                       disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="interval-unit"
          >
            {INTERVAL_UNITS.map((unit) => (
              <option key={unit.value} value={unit.value}>
                {unit.label}
              </option>
            ))}
          </select>
        </div>

        {/* Error message */}
        {error && (
          <div className="text-xs text-red-400" data-testid="interval-error">
            {error}
          </div>
        )}

        {/* Time Window Toggle */}
        <div className="flex items-center gap-3 text-sm">
          <input
            type="checkbox"
            id="time-window-toggle"
            checked={timeWindow !== null}
            onChange={handleTimeWindowToggle}
            disabled={disabled}
            className="rounded border-gray-600
                       disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="time-window-toggle"
          />
          <label htmlFor="time-window-toggle" className="text-gray-400">
            Limit to time window
          </label>
        </div>

        {/* Time Window Inputs */}
        {timeWindow && (
          <div className="space-y-2 pl-6">
            <div className="flex items-center gap-3 text-sm">
              <input
                type="time"
                value={timeWindow.start_time || '18:00'}
                onChange={handleStartTimeChange}
                disabled={disabled}
                className="bg-transparent border border-gray-800 rounded px-2 py-1 text-white
                           focus:border-gray-600 focus:outline-none
                           disabled:opacity-50 disabled:cursor-not-allowed"
                data-testid="time-window-start"
              />
              <span className="text-gray-600">to</span>
              <input
                type="time"
                value={timeWindow.end_time || '06:00'}
                onChange={handleEndTimeChange}
                disabled={disabled}
                className="bg-transparent border border-gray-800 rounded px-2 py-1 text-white
                           focus:border-gray-600 focus:outline-none
                           disabled:opacity-50 disabled:cursor-not-allowed"
                data-testid="time-window-end"
              />
            </div>
            {/* Overnight window indicator */}
            {isOvernightWindow && (
              <div className="text-xs text-gray-500" data-testid="overnight-indicator">
                Overnight window active (spans midnight)
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

IntervalTriggerForm.propTypes = {
  trigger: PropTypes.shape({
    trigger_type: PropTypes.string,
    interval_minutes: PropTypes.number,
    time_window: PropTypes.shape({
      start_time: PropTypes.string,
      end_time: PropTypes.string,
    }),
  }),
  onChange: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
  error: PropTypes.string,
}

export default IntervalTriggerForm

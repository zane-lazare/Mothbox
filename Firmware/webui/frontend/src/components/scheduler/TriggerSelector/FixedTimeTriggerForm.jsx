import PropTypes from 'prop-types'
import { TRIGGER_FORM_BORDER } from './constants'

/**
 * Generate a unique ID for time entries
 */
const generateId = () => `time-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`

/**
 * Normalize times to ensure they have IDs
 * Handles both old format (string[]) and new format ({ id, value }[])
 */
const normalizeTimes = (times) => {
  if (!times || times.length === 0) {
    return [{ id: generateId(), value: '08:00' }]
  }
  return times.map((time) => {
    if (typeof time === 'string') {
      return { id: generateId(), value: time }
    }
    return time
  })
}

/**
 * FixedTimeTriggerForm Component
 *
 * Form for configuring fixed time triggers with multiple time entries.
 * Uses unique IDs for stable React keys.
 *
 * @component
 */
function FixedTimeTriggerForm({ trigger, onChange, disabled = false, error = null }) {
  const times = normalizeTimes(trigger?.times)

  /**
   * Handle time change at specific index
   */
  const handleTimeChange = (id, value) => {
    const newTimes = times.map((time) =>
      time.id === id ? { ...time, value } : time
    )
    onChange({
      ...trigger,
      times: newTimes,
    })
  }

  /**
   * Handle adding a new time
   */
  const handleAddTime = () => {
    onChange({
      ...trigger,
      times: [...times, { id: generateId(), value: '12:00' }],
    })
  }

  /**
   * Handle removing a time by ID
   */
  const handleRemoveTime = (id) => {
    if (times.length <= 1) return // Keep at least one time
    const newTimes = times.filter((time) => time.id !== id)
    onChange({
      ...trigger,
      times: newTimes,
    })
  }

  const hasError = error || times.length === 0

  return (
    <div className={TRIGGER_FORM_BORDER} data-testid="fixed-time-trigger-form">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-sm text-gray-900 dark:text-white">Fixed Time</span>
        <span className="text-xs text-gray-500 dark:text-gray-600">run at specific times</span>
      </div>

      <div className="space-y-3" data-testid="fixed-time-list">
        {times.map((time, index) => (
          <div key={time.id} className="flex items-center gap-2">
            <input
              type="time"
              value={time.value}
              onChange={(e) => handleTimeChange(time.id, e.target.value)}
              disabled={disabled}
              className={`bg-transparent border rounded px-2 py-1 text-sm text-gray-900 dark:text-white
                         focus:outline-none
                         disabled:opacity-50 disabled:cursor-not-allowed
                         ${hasError ? 'border-red-500 focus:border-red-400' : 'border-gray-300 dark:border-gray-800 focus:border-gray-500 dark:focus:border-gray-600'}`}
              data-testid={`fixed-time-input-${index}`}
            />
            {times.length > 1 && (
              <button
                type="button"
                onClick={() => handleRemoveTime(time.id)}
                disabled={disabled}
                className="text-gray-600 hover:text-red-400 text-sm
                           disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label={`Remove time ${time.value}`}
                data-testid={`fixed-time-remove-${index}`}
              >
                &times;
              </button>
            )}
          </div>
        ))}

        <button
          type="button"
          onClick={handleAddTime}
          disabled={disabled}
          className="text-xs text-gray-500 hover:text-gray-300
                     disabled:opacity-50 disabled:cursor-not-allowed"
          data-testid="fixed-time-add"
        >
          + Add time
        </button>

        {/* Error message */}
        {error && (
          <div className="text-xs text-red-400" data-testid="fixed-time-error">
            {error}
          </div>
        )}
      </div>
    </div>
  )
}

FixedTimeTriggerForm.propTypes = {
  trigger: PropTypes.shape({
    trigger_type: PropTypes.string,
    times: PropTypes.oneOfType([
      PropTypes.arrayOf(PropTypes.string),
      PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.string,
          value: PropTypes.string,
        })
      ),
    ]),
  }),
  onChange: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
  error: PropTypes.string,
}

export default FixedTimeTriggerForm

import PropTypes from 'prop-types'

/**
 * FixedTimeTriggerForm Component
 *
 * Form for configuring fixed time triggers with multiple time entries.
 *
 * @component
 */
function FixedTimeTriggerForm({ trigger, onChange, disabled = false }) {
  const times = trigger?.times || ['08:00']

  /**
   * Handle time change at specific index
   */
  const handleTimeChange = (index, value) => {
    const newTimes = [...times]
    newTimes[index] = value
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
      times: [...times, '12:00'],
    })
  }

  /**
   * Handle removing a time at specific index
   */
  const handleRemoveTime = (index) => {
    if (times.length <= 1) return // Keep at least one time
    const newTimes = times.filter((_, i) => i !== index)
    onChange({
      ...trigger,
      times: newTimes,
    })
  }

  return (
    <div className="border border-gray-800 rounded-lg p-4" data-testid="fixed-time-trigger-form">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-sm text-white">Fixed Time</span>
        <span className="text-xs text-gray-600">run at specific times</span>
      </div>

      <div className="space-y-3" data-testid="fixed-time-list">
        {times.map((time, index) => (
          <div key={index} className="flex items-center gap-2">
            <input
              type="time"
              value={time}
              onChange={(e) => handleTimeChange(index, e.target.value)}
              disabled={disabled}
              className="bg-transparent border border-gray-800 rounded px-2 py-1 text-sm text-white
                         focus:border-gray-600 focus:outline-none
                         disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid={`fixed-time-input-${index}`}
            />
            {times.length > 1 && (
              <button
                type="button"
                onClick={() => handleRemoveTime(index)}
                disabled={disabled}
                className="text-gray-600 hover:text-red-400 text-sm
                           disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label={`Remove time ${time}`}
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
      </div>
    </div>
  )
}

FixedTimeTriggerForm.propTypes = {
  trigger: PropTypes.shape({
    trigger_type: PropTypes.string,
    times: PropTypes.arrayOf(PropTypes.string),
  }),
  onChange: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
}

export default FixedTimeTriggerForm

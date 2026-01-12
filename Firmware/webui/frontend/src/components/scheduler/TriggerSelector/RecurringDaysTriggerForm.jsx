import PropTypes from 'prop-types'
import { DAYS_OF_WEEK } from './constants'

/**
 * RecurringDaysTriggerForm Component
 *
 * Form for configuring weekly recurring triggers with day selection.
 *
 * @component
 */
function RecurringDaysTriggerForm({ trigger, onChange, disabled = false, error = null }) {
  const selectedDays = trigger?.days || [0, 5, 6]
  const time = trigger?.time || '20:00'
  const hasError = error || selectedDays.length === 0

  /**
   * Handle day toggle
   */
  const handleDayToggle = (dayValue) => {
    const isSelected = selectedDays.includes(dayValue)
    let newDays

    if (isSelected) {
      // Remove day (but keep at least one)
      if (selectedDays.length <= 1) return
      newDays = selectedDays.filter(d => d !== dayValue)
    } else {
      // Add day and sort
      newDays = [...selectedDays, dayValue].sort((a, b) => a - b)
    }

    onChange({
      ...trigger,
      days: newDays,
    })
  }

  /**
   * Handle time change
   */
  const handleTimeChange = (e) => {
    onChange({
      ...trigger,
      time: e.target.value,
    })
  }

  return (
    <div className="border border-gray-800 rounded-lg p-4" data-testid="recurring-days-trigger-form">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-sm text-gray-900 dark:text-white">Recurring Days</span>
        <span className="text-xs text-gray-500 dark:text-gray-600">weekly schedule</span>
      </div>

      <div className="space-y-4">
        {/* Day Selection Grid */}
        <div
          className={`flex gap-1 ${hasError ? 'ring-1 ring-red-500 rounded p-1' : ''}`}
          data-testid="recurring-days-grid"
        >
          {DAYS_OF_WEEK.map((day) => {
            const isSelected = selectedDays.includes(day.value)
            const isLastSelected = isSelected && selectedDays.length === 1
            return (
              <button
                key={day.value}
                type="button"
                onClick={() => handleDayToggle(day.value)}
                disabled={disabled}
                title={isLastSelected ? 'At least one day required' : undefined}
                className={`
                  w-8 h-8 text-xs border rounded
                  ${isSelected
                    ? 'border-gray-700 bg-gray-800 text-white'
                    : 'border-gray-800 text-gray-500 hover:border-gray-600'
                  }
                  ${isLastSelected ? 'opacity-60 cursor-not-allowed' : ''}
                  disabled:opacity-50 disabled:cursor-not-allowed
                `}
                aria-pressed={isSelected}
                aria-label={day.label}
                data-testid={`day-${day.value}`}
              >
                {day.short}
              </button>
            )
          })}
        </div>

        {/* Error message */}
        {error && (
          <div className="text-xs text-red-400" data-testid="recurring-days-error">
            {error}
          </div>
        )}

        {/* Time Input */}
        <div className="flex items-center gap-3 text-sm">
          <span className="text-gray-500">At</span>
          <input
            type="time"
            value={time}
            onChange={handleTimeChange}
            disabled={disabled}
            className="bg-transparent border border-gray-300 dark:border-gray-800 rounded px-2 py-1 text-gray-900 dark:text-white
                       focus:border-gray-500 dark:focus:border-gray-600 focus:outline-none
                       disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="trigger-time"
          />
        </div>
      </div>
    </div>
  )
}

RecurringDaysTriggerForm.propTypes = {
  trigger: PropTypes.shape({
    trigger_type: PropTypes.string,
    days: PropTypes.arrayOf(PropTypes.number),
    time: PropTypes.string,
  }),
  onChange: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
  error: PropTypes.string,
}

export default RecurringDaysTriggerForm

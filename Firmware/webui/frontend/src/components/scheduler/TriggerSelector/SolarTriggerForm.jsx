import PropTypes from 'prop-types'
import { SOLAR_EVENTS } from './constants'

/**
 * SolarTriggerForm Component
 *
 * Form for configuring solar event triggers with offset.
 *
 * @component
 */
function SolarTriggerForm({ trigger, onChange, disabled = false }) {
  const solarEvent = trigger?.solar_event || 'sunset'
  const offsetMinutes = trigger?.offset_minutes ?? 0

  /**
   * Handle solar event change
   */
  const handleEventChange = (e) => {
    onChange({
      ...trigger,
      solar_event: e.target.value,
    })
  }

  /**
   * Handle offset change
   */
  const handleOffsetChange = (e) => {
    const value = parseInt(e.target.value, 10)
    onChange({
      ...trigger,
      offset_minutes: isNaN(value) ? 0 : value,
    })
  }

  return (
    <div className="border border-gray-800 rounded-lg p-4" data-testid="solar-trigger-form">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-sm text-white">Solar Event</span>
        <span className="text-xs text-gray-600">based on sun position</span>
      </div>

      <div className="space-y-4">
        {/* Solar Event Select */}
        <select
          value={solarEvent}
          onChange={handleEventChange}
          disabled={disabled}
          className="w-full bg-transparent border border-gray-800 rounded px-3 py-2 text-sm text-white
                     focus:border-gray-600 focus:outline-none
                     disabled:opacity-50 disabled:cursor-not-allowed"
          data-testid="solar-event"
        >
          {SOLAR_EVENTS.map((event) => (
            <option key={event.value} value={event.value}>
              {event.label}
            </option>
          ))}
        </select>

        {/* Offset Input */}
        <div className="flex items-center gap-3 text-sm">
          <span className="text-gray-500">Offset</span>
          <input
            type="number"
            value={offsetMinutes}
            onChange={handleOffsetChange}
            disabled={disabled}
            className="w-16 bg-transparent border border-gray-800 rounded px-2 py-1 text-white text-center
                       focus:border-gray-600 focus:outline-none
                       disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="solar-offset"
          />
          <span className="text-gray-500">minutes</span>
        </div>

        {/* Preview */}
        <div className="text-xs text-gray-600" data-testid="solar-preview">
          Today: ~17:23
        </div>
      </div>
    </div>
  )
}

SolarTriggerForm.propTypes = {
  trigger: PropTypes.shape({
    trigger_type: PropTypes.string,
    solar_event: PropTypes.string,
    offset_minutes: PropTypes.number,
  }),
  onChange: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
}

export default SolarTriggerForm

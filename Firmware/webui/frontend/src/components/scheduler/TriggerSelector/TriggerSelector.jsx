import PropTypes from 'prop-types'
import { TRIGGER_TYPE_OPTIONS, createDefaultTrigger } from './constants'
import IntervalTriggerForm from './IntervalTriggerForm'
import FixedTimeTriggerForm from './FixedTimeTriggerForm'
import SolarTriggerForm from './SolarTriggerForm'
import MoonPhaseTriggerForm from './MoonPhaseTriggerForm'
import RecurringDaysTriggerForm from './RecurringDaysTriggerForm'
import CronTriggerForm from './CronTriggerForm'

/**
 * TriggerSelector Component
 *
 * A composite component for selecting trigger type and configuring
 * trigger-specific options. Renders a type dropdown and the appropriate
 * form based on the selected type.
 *
 * @component
 * @example
 * <TriggerSelector
 *   trigger={{ trigger_type: 'interval', interval_minutes: 15 }}
 *   onChange={(newTrigger) => console.log(newTrigger)}
 * />
 */
function TriggerSelector({ trigger, onChange, disabled = false, error }) {
  const triggerType = trigger?.trigger_type || 'interval'

  /**
   * Handle trigger type change
   * Creates a new default trigger for the selected type
   */
  const handleTypeChange = (e) => {
    const newType = e.target.value
    onChange(createDefaultTrigger(newType))
  }

  /**
   * Render the appropriate trigger form based on type
   */
  const renderTriggerForm = () => {
    const commonProps = {
      trigger,
      onChange,
      disabled,
    }

    switch (triggerType) {
      case 'interval':
        return <IntervalTriggerForm {...commonProps} />
      case 'fixed_time':
        return <FixedTimeTriggerForm {...commonProps} />
      case 'solar':
        return <SolarTriggerForm {...commonProps} />
      case 'moon_phase':
        return <MoonPhaseTriggerForm {...commonProps} />
      case 'recurring_days':
        return <RecurringDaysTriggerForm {...commonProps} />
      case 'cron':
        return <CronTriggerForm {...commonProps} />
      default:
        return <IntervalTriggerForm {...commonProps} />
    }
  }

  return (
    <div className="space-y-4" data-testid="trigger-selector">
      {/* Type Selection Dropdown */}
      <div>
        <label
          htmlFor="trigger-type"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
        >
          When to run
        </label>
        <select
          id="trigger-type"
          value={triggerType}
          onChange={handleTypeChange}
          disabled={disabled}
          className={`
            w-full bg-transparent border rounded px-3 py-2 text-sm
            text-gray-900 dark:text-white
            focus:ring-2 focus:ring-blue-500 focus:border-transparent
            disabled:opacity-50 disabled:cursor-not-allowed
            ${error
              ? 'border-red-500 dark:border-red-400'
              : 'border-gray-300 dark:border-gray-800'
            }
          `}
          data-testid="trigger-type"
          aria-invalid={!!error}
          aria-describedby={error ? 'trigger-error' : undefined}
        >
          {TRIGGER_TYPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {error && (
          <p id="trigger-error" className="mt-1 text-sm text-red-600 dark:text-red-400">
            {error}
          </p>
        )}
      </div>

      {/* Trigger-Specific Form */}
      {renderTriggerForm()}
    </div>
  )
}

TriggerSelector.propTypes = {
  /** Current trigger configuration */
  trigger: PropTypes.shape({
    trigger_type: PropTypes.oneOf([
      'interval',
      'fixed_time',
      'solar',
      'moon_phase',
      'recurring_days',
      'cron',
    ]),
    // Interval fields
    interval_minutes: PropTypes.number,
    time_window: PropTypes.shape({
      start_time: PropTypes.string,
      end_time: PropTypes.string,
    }),
    // Fixed time fields
    times: PropTypes.arrayOf(PropTypes.string),
    // Solar fields
    solar_event: PropTypes.string,
    offset_minutes: PropTypes.number,
    // Moon phase fields
    phases: PropTypes.arrayOf(PropTypes.string),
    // Recurring days fields
    days: PropTypes.arrayOf(PropTypes.number),
    time: PropTypes.string,
    // Cron fields
    cron_expression: PropTypes.string,
  }),
  /** Callback when trigger changes */
  onChange: PropTypes.func.isRequired,
  /** Whether the form is disabled */
  disabled: PropTypes.bool,
  /** Error message to display */
  error: PropTypes.string,
}

export default TriggerSelector

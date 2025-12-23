import PropTypes from 'prop-types';
import { MOON_PHASES, SCHEDULE_LIMITS, validateNumericInput } from './constants';

/**
 * MoonPhaseTriggerForm Component
 *
 * A form for configuring moon phase-based triggers that execute patterns
 * at specific moon phases with optional offset days and time of day.
 *
 * @component
 * @example
 * <MoonPhaseTriggerForm
 *   value={{
 *     moon_phase: "full",
 *     time_of_day: "20:00",
 *     offset_days: 0
 *   }}
 *   onChange={(newValue) => console.log(newValue)}
 * />
 */
const MoonPhaseTriggerForm = ({
  value = {
    moon_phase: 'full',
    time_of_day: '20:00',
    offset_days: 0,
  },
  onChange,
  disabled = false,
  errors = {},
}) => {
  /**
   * Quick preset offsets in days
   */
  const OFFSET_PRESETS = [
    { label: '-1 day', value: -1 },
    { label: 'No offset', value: 0 },
    { label: '+1 day', value: 1 },
  ];

  /**
   * Handle moon phase change
   */
  const handleMoonPhaseChange = (newPhase) => {
    onChange({
      ...value,
      moon_phase: newPhase,
    });
  };

  /**
   * Handle time of day change
   */
  const handleTimeChange = (newTime) => {
    onChange({
      ...value,
      time_of_day: newTime,
    });
  };

  /**
   * Handle offset days change with validation
   */
  const handleOffsetChange = (newOffset) => {
    const validated = validateNumericInput(
      newOffset,
      -SCHEDULE_LIMITS.MAX_OFFSET_DAYS,
      SCHEDULE_LIMITS.MAX_OFFSET_DAYS
    );
    if (validated === null) return;
    onChange({
      ...value,
      offset_days: validated,
    });
  };

  /**
   * Handle preset button click
   */
  const handlePresetClick = (presetValue) => {
    onChange({
      ...value,
      offset_days: presetValue,
    });
  };

  /**
   * Get label for the selected moon phase
   * @returns {string} Label text
   */
  const getMoonPhaseLabel = () => {
    const phase = MOON_PHASES.find((p) => p.value === value.moon_phase);
    return phase ? phase.label : value.moon_phase;
  };

  /**
   * Format offset for display
   * @param {number} days - Offset in days
   * @returns {string} Formatted offset
   */
  const formatOffset = (days) => {
    if (days === 0) return '';
    const absDays = Math.abs(days);
    return `${absDays} day${absDays !== 1 ? 's' : ''}`;
  };

  /**
   * Generate preview text
   * @returns {string} Human-readable preview
   */
  const getPreviewText = () => {
    const phaseLabel = getMoonPhaseLabel();
    const offsetText = formatOffset(value.offset_days);
    const time = value.time_of_day;

    let preview;
    if (value.offset_days === 0) {
      preview = `On ${phaseLabel} at ${time}`;
    } else if (value.offset_days > 0) {
      preview = `${offsetText} after ${phaseLabel} at ${time}`;
    } else {
      preview = `${offsetText} before ${phaseLabel} at ${time}`;
    }

    return preview;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
        Moon Phase Configuration
      </h3>

      {/* Moon Phase Selection */}
      <div>
        <label
          htmlFor="moon_phase"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Moon Phase:
        </label>
        <select
          id="moon_phase"
          value={value.moon_phase}
          onChange={(e) => handleMoonPhaseChange(e.target.value)}
          disabled={disabled}
          className="w-full rounded-md border border-gray-300 dark:border-gray-600
                   bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                   focus:ring-2 focus:ring-blue-500 focus:border-transparent
                   disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Moon phase"
        >
          {MOON_PHASES.map((phase) => (
            <option key={phase.value} value={phase.value}>
              {phase.label}
            </option>
          ))}
        </select>
      </div>

      {/* Time of Day Input */}
      <div>
        <label
          htmlFor="time_of_day"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Time of Day:
        </label>
        <input
          id="time_of_day"
          type="time"
          pattern="[0-9]{2}:[0-9]{2}"
          value={value.time_of_day}
          onChange={(e) => handleTimeChange(e.target.value)}
          disabled={disabled}
          className="w-full rounded-md border border-gray-300 dark:border-gray-600
                   bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                   focus:ring-2 focus:ring-blue-500 focus:border-transparent
                   disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Time of day"
        />
        {errors.time_of_day && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">
            {errors.time_of_day}
          </p>
        )}
      </div>

      {/* Offset Days Input */}
      <div>
        <label
          htmlFor="offset_days"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Offset (days):
        </label>
        <div className="flex items-center gap-2">
          <input
            id="offset_days"
            type="number"
            min={-SCHEDULE_LIMITS.MAX_OFFSET_DAYS}
            max={SCHEDULE_LIMITS.MAX_OFFSET_DAYS}
            value={value.offset_days}
            onChange={(e) => handleOffsetChange(e.target.value)}
            disabled={disabled}
            className="w-32 rounded-md border border-gray-300 dark:border-gray-600
                     bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                     focus:ring-2 focus:ring-blue-500 focus:border-transparent
                     disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Offset in days"
          />
          <span className="text-sm text-gray-700 dark:text-gray-300">days</span>
        </div>
        {errors.offset_days && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">
            {errors.offset_days}
          </p>
        )}
      </div>

      {/* Quick Offset Presets */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Quick presets:
        </label>
        <div className="flex flex-wrap gap-2">
          {OFFSET_PRESETS.map((preset) => (
            <button
              key={preset.value}
              type="button"
              onClick={() => handlePresetClick(preset.value)}
              disabled={disabled}
              className={`
                px-4 py-2 rounded-md text-sm font-medium
                transition-colors duration-150
                focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
                dark:focus:ring-offset-gray-800
                ${
                  value.offset_days === preset.value
                    ? 'bg-blue-500 text-white hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
                }
                ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              `}
              aria-label={`Set offset to ${preset.value} days`}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      {/* Preview */}
      <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Preview:
        </label>
        <p className="text-sm text-gray-600 dark:text-gray-300 italic bg-gray-50 dark:bg-gray-800 p-3 rounded-md">
          {getPreviewText()}
        </p>
      </div>
    </div>
  );
};

MoonPhaseTriggerForm.propTypes = {
  /** Moon phase trigger configuration containing moon_phase, time_of_day, and offset_days */
  value: PropTypes.shape({
    moon_phase: PropTypes.string.isRequired,
    time_of_day: PropTypes.string.isRequired,
    offset_days: PropTypes.number.isRequired,
  }),
  /** Callback when moon phase trigger configuration changes */
  onChange: PropTypes.func.isRequired,
  /** Whether the form is disabled */
  disabled: PropTypes.bool,
  /** Validation errors for moon phase trigger fields */
  errors: PropTypes.shape({
    moon_phase: PropTypes.string,
    time_of_day: PropTypes.string,
    offset_days: PropTypes.string,
  }),
};

export default MoonPhaseTriggerForm;

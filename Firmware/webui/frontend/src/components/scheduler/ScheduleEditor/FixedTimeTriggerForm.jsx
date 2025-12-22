import PropTypes from 'prop-types';
import { DAYS_OF_WEEK } from './constants';
import DaysOfWeekSelector from './DaysOfWeekSelector';

/**
 * FixedTimeTriggerForm Component
 *
 * A form for configuring fixed time-based triggers that execute patterns
 * at specific times of day on selected days.
 *
 * @component
 * @example
 * <FixedTimeTriggerForm
 *   value={{
 *     time_of_day: "21:00",
 *     days_of_week: [0, 1, 2, 3, 4]
 *   }}
 *   onChange={(newValue) => console.log(newValue)}
 * />
 */
const FixedTimeTriggerForm = ({
  value = {
    time_of_day: '12:00',
    days_of_week: null,
  },
  onChange,
  disabled = false,
  errors = {},
}) => {
  /**
   * Quick preset times for common scenarios
   */
  const TIME_PRESETS = [
    { label: '6 AM', value: '06:00' },
    { label: '12 PM', value: '12:00' },
    { label: '6 PM', value: '18:00' },
    { label: '9 PM', value: '21:00' },
  ];

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
   * Handle preset button click
   */
  const handlePresetClick = (presetValue) => {
    onChange({
      ...value,
      time_of_day: presetValue,
    });
  };

  /**
   * Handle days of week change
   */
  const handleDaysChange = (newDays) => {
    onChange({
      ...value,
      days_of_week: newDays,
    });
  };

  /**
   * Format days of week for display
   * @param {Array<number>|null} days - Days array or null for all days
   * @returns {string} Formatted days
   */
  const formatDays = (days) => {
    if (days === null || days === undefined) {
      return '';
    }

    if (!Array.isArray(days) || days.length === 0) {
      return '';
    }

    if (days.length === 7) {
      return '';
    }

    const dayLabels = days
      .sort((a, b) => a - b)
      .map((dayValue) => {
        const day = DAYS_OF_WEEK.find((d) => d.value === dayValue);
        return day ? day.shortLabel : '';
      })
      .filter(Boolean);

    return dayLabels.join(', ');
  };

  /**
   * Generate preview text
   * @returns {string} Human-readable preview
   */
  const getPreviewText = () => {
    const daysText = formatDays(value.days_of_week);

    let preview = `At ${value.time_of_day}`;

    if (daysText) {
      preview += ` on ${daysText}`;
    }

    return preview;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
        Fixed Time Configuration
      </h3>

      {/* Time of Day Input */}
      <div>
        <label
          htmlFor="time_of_day"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Time of day:
        </label>
        <input
          id="time_of_day"
          type="time"
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

      {/* Quick Time Presets */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Quick presets:
        </label>
        <div className="flex flex-wrap gap-2">
          {TIME_PRESETS.map((preset) => (
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
                  value.time_of_day === preset.value
                    ? 'bg-blue-500 text-white hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
                }
                ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              `}
              aria-label={`Set time to ${preset.value}`}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      {/* Days of Week */}
      <DaysOfWeekSelector
        value={value.days_of_week}
        onChange={handleDaysChange}
        disabled={disabled}
      />

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

FixedTimeTriggerForm.propTypes = {
  value: PropTypes.shape({
    time_of_day: PropTypes.string.isRequired,
    days_of_week: PropTypes.arrayOf(PropTypes.number),
  }),
  onChange: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
  errors: PropTypes.shape({
    time_of_day: PropTypes.string,
    days_of_week: PropTypes.string,
  }),
};

export default FixedTimeTriggerForm;

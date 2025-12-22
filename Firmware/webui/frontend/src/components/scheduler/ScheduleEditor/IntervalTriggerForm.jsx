import PropTypes from 'prop-types';
import { SCHEDULE_LIMITS, DAYS_OF_WEEK } from './constants';
import TimeWindowInput from './TimeWindowInput';
import DaysOfWeekSelector from './DaysOfWeekSelector';

/**
 * IntervalTriggerForm Component
 *
 * A form for configuring interval-based triggers that execute patterns
 * at regular intervals within a time window.
 *
 * @component
 * @example
 * <IntervalTriggerForm
 *   value={{
 *     interval_minutes: 60,
 *     time_window: {
 *       start_time: "21:00",
 *       end_time: "05:00"
 *     },
 *     days_of_week: [0, 1, 2, 3, 4]
 *   }}
 *   onChange={(newValue) => console.log(newValue)}
 * />
 */
const IntervalTriggerForm = ({
  value = {
    interval_minutes: 60,
    time_window: {
      start_time: '',
      end_time: '',
      start_offset_minutes: 0,
      end_offset_minutes: 0,
    },
    days_of_week: null,
  },
  onChange,
  disabled = false,
  errors = {},
}) => {
  /**
   * Quick preset intervals in minutes
   */
  const QUICK_PRESETS = [
    { label: '15 min', value: 15 },
    { label: '30 min', value: 30 },
    { label: '60 min', value: 60 },
    { label: '2 hours', value: 120 },
    { label: '4 hours', value: 240 },
  ];

  /**
   * Handle interval minutes change
   */
  const handleIntervalChange = (newInterval) => {
    const numInterval = Number(newInterval);
    onChange({
      ...value,
      interval_minutes: numInterval,
    });
  };

  /**
   * Handle preset button click
   */
  const handlePresetClick = (presetValue) => {
    onChange({
      ...value,
      interval_minutes: presetValue,
    });
  };

  /**
   * Handle time window change
   */
  const handleTimeWindowChange = (newTimeWindow) => {
    onChange({
      ...value,
      time_window: newTimeWindow,
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
   * Format interval for display
   * @param {number} minutes - Interval in minutes
   * @returns {string} Formatted interval (e.g., "Every 60 minutes", "Every 2 hours")
   */
  const formatInterval = (minutes) => {
    if (!minutes) return 'Every';

    if (minutes < 60) {
      return `Every ${minutes} minute${minutes !== 1 ? 's' : ''}`;
    } else if (minutes % 60 === 0) {
      const hours = minutes / 60;
      return `Every ${hours} hour${hours !== 1 ? 's' : ''}`;
    } else {
      const hours = Math.floor(minutes / 60);
      const mins = minutes % 60;
      return `Every ${hours}h ${mins}m`;
    }
  };

  /**
   * Format time window for display
   * @param {Object} timeWindow - Time window object
   * @returns {string} Formatted time window
   */
  const formatTimeWindow = (timeWindow) => {
    if (!timeWindow || !timeWindow.start_time || !timeWindow.end_time) {
      return '';
    }

    const formatTime = (time, offset) => {
      // Check if it's a solar event (not HH:MM format)
      if (!/^\d{2}:\d{2}$/.test(time)) {
        const formattedEvent = time.replace(/_/g, ' ');
        if (offset && offset !== 0) {
          const sign = offset > 0 ? '+' : '';
          return `${formattedEvent}${sign}${offset}`;
        }
        return formattedEvent;
      }
      return time;
    };

    const startText = formatTime(timeWindow.start_time, timeWindow.start_offset_minutes);
    const endText = formatTime(timeWindow.end_time, timeWindow.end_offset_minutes);

    return `from ${startText} to ${endText}`;
  };

  /**
   * Format days of week for display
   * @param {Array<number>|null} days - Days array or null for all days
   * @returns {string} Formatted days (e.g., "Mon, Wed, Fri")
   */
  const formatDays = (days) => {
    if (days === null || days === undefined) {
      return ''; // All days - don't show
    }

    if (!Array.isArray(days) || days.length === 0) {
      return '';
    }

    if (days.length === 7) {
      return ''; // All days selected - don't show
    }

    // Map day values to short labels
    const dayLabels = days
      .sort((a, b) => a - b)
      .map(dayValue => {
        const day = DAYS_OF_WEEK.find(d => d.value === dayValue);
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
    const intervalText = formatInterval(value.interval_minutes);
    const windowText = formatTimeWindow(value.time_window);
    const daysText = formatDays(value.days_of_week);

    let preview = intervalText;
    if (windowText) {
      preview += ` ${windowText}`;
    }
    if (daysText) {
      preview += ` on ${daysText}`;
    }

    return preview;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
        Interval Configuration
      </h3>

      {/* Interval Input */}
      <div>
        <label
          htmlFor="interval_minutes"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Repeat every:
        </label>
        <div className="flex items-center gap-2">
          <input
            id="interval_minutes"
            type="number"
            min={SCHEDULE_LIMITS.MIN_INTERVAL_MINUTES}
            max={SCHEDULE_LIMITS.MAX_INTERVAL_MINUTES}
            value={value.interval_minutes}
            onChange={(e) => handleIntervalChange(e.target.value)}
            disabled={disabled}
            className="w-32 rounded-md border border-gray-300 dark:border-gray-600
                     bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                     focus:ring-2 focus:ring-blue-500 focus:border-transparent
                     disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Interval in minutes"
          />
          <span className="text-sm text-gray-700 dark:text-gray-300">minutes</span>
        </div>
        {errors.interval_minutes && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">
            {errors.interval_minutes}
          </p>
        )}
      </div>

      {/* Quick Presets */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Quick presets:
        </label>
        <div className="flex flex-wrap gap-2">
          {QUICK_PRESETS.map((preset) => (
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
                  value.interval_minutes === preset.value
                    ? 'bg-blue-500 text-white hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
                }
                ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              `}
              aria-label={`Set interval to ${preset.label}`}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      {/* Time Window */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
          Time Window:
        </label>
        <TimeWindowInput
          value={value.time_window}
          onChange={handleTimeWindowChange}
          disabled={disabled}
          showSolarEvents={true}
          errors={errors.time_window || {}}
        />
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
        <p className="text-sm text-gray-600 dark:text-gray-400 italic bg-gray-50 dark:bg-gray-800 p-3 rounded-md">
          {getPreviewText()}
        </p>
      </div>
    </div>
  );
};

IntervalTriggerForm.propTypes = {
  value: PropTypes.shape({
    interval_minutes: PropTypes.number.isRequired,
    time_window: PropTypes.shape({
      start_time: PropTypes.string.isRequired,
      end_time: PropTypes.string.isRequired,
      start_offset_minutes: PropTypes.number,
      end_offset_minutes: PropTypes.number,
    }).isRequired,
    days_of_week: PropTypes.arrayOf(PropTypes.number), // null = all days
  }),
  onChange: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
  errors: PropTypes.shape({
    interval_minutes: PropTypes.string,
    time_window: PropTypes.object,
    days_of_week: PropTypes.string,
  }),
};

export default IntervalTriggerForm;

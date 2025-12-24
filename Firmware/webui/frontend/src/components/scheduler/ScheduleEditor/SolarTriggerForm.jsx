import { useMemo, useCallback } from 'react';
import PropTypes from 'prop-types';
import { SOLAR_EVENTS, SCHEDULE_LIMITS, DAYS_OF_WEEK, validateNumericInput } from './constants';
import DaysOfWeekSelector from './DaysOfWeekSelector';

/**
 * SolarTriggerForm Component
 *
 * A form for configuring solar event-based triggers that execute patterns
 * at specific solar events (sunrise, sunset, etc.) with optional offset.
 *
 * @component
 * @example
 * <SolarTriggerForm
 *   value={{
 *     solar_event: "sunset",
 *     offset_minutes: 30,
 *     days_of_week: [0, 1, 2, 3, 4]
 *   }}
 *   onChange={(newValue) => console.log(newValue)}
 * />
 */
const SolarTriggerForm = ({
  value = {
    solar_event: 'sunset',
    offset_minutes: 0,
    days_of_week: null,
  },
  onChange,
  disabled = false,
  errors = {},
}) => {
  /**
   * Quick preset offsets in minutes
   */
  const OFFSET_PRESETS = [
    { label: '-1h', value: -60 },
    { label: '-30m', value: -30 },
    { label: 'No offset', value: 0 },
    { label: '+30m', value: 30 },
    { label: '+1h', value: 60 },
  ];

  /**
   * Handle solar event change
   */
  const handleSolarEventChange = (newEvent) => {
    onChange({
      ...value,
      solar_event: newEvent,
    });
  };

  /**
   * Handle offset minutes change with validation
   */
  const handleOffsetChange = (newOffset) => {
    const validated = validateNumericInput(
      newOffset,
      -SCHEDULE_LIMITS.MAX_OFFSET_MINUTES,
      SCHEDULE_LIMITS.MAX_OFFSET_MINUTES
    );
    if (validated === null) return;
    onChange({
      ...value,
      offset_minutes: validated,
    });
  };

  /**
   * Handle preset button click
   */
  const handlePresetClick = (presetValue) => {
    onChange({
      ...value,
      offset_minutes: presetValue,
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
   * Get description for the selected solar event
   * @returns {string} Description text
   */
  const getEventDescription = () => {
    const event = SOLAR_EVENTS.find((e) => e.value === value.solar_event);
    return event ? event.description : '';
  };

  /**
   * Get label for the selected solar event
   * @returns {string} Label text
   */
  const getEventLabel = useCallback(() => {
    const event = SOLAR_EVENTS.find((e) => e.value === value.solar_event);
    return event ? event.label.toLowerCase() : value.solar_event;
  }, [value.solar_event]);

  /**
   * Format offset for display
   * @param {number} minutes - Offset in minutes
   * @returns {string} Formatted offset
   */
  const formatOffset = (minutes) => {
    if (minutes === 0) return '';

    const absMinutes = Math.abs(minutes);

    if (absMinutes < 60) {
      return `${absMinutes} minute${absMinutes !== 1 ? 's' : ''}`;
    } else if (absMinutes % 60 === 0) {
      const hours = absMinutes / 60;
      return `${hours} hour${hours !== 1 ? 's' : ''}`;
    } else {
      const hours = Math.floor(absMinutes / 60);
      const mins = absMinutes % 60;
      return `${hours}h ${mins}m`;
    }
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
   * Memoized preview text to prevent recalculation on every render
   */
  const previewText = useMemo(() => {
    const eventLabel = getEventLabel();
    const offsetText = formatOffset(value.offset_minutes);
    const daysText = formatDays(value.days_of_week);

    let preview;
    if (value.offset_minutes === 0) {
      preview = `At ${eventLabel}`;
    } else if (value.offset_minutes > 0) {
      preview = `${offsetText} after ${eventLabel}`;
    } else {
      preview = `${offsetText} before ${eventLabel}`;
    }

    if (daysText) {
      preview += ` on ${daysText}`;
    }

    return preview;
  }, [getEventLabel, value.offset_minutes, value.days_of_week]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
        Solar Event Configuration
      </h3>

      {/* Solar Event Selection */}
      <div>
        <label
          htmlFor="solar_event"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Solar Event:
        </label>
        <select
          id="solar_event"
          value={value.solar_event}
          onChange={(e) => handleSolarEventChange(e.target.value)}
          disabled={disabled}
          className="w-full rounded-md border border-gray-300 dark:border-gray-600
                   bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                   focus:ring-2 focus:ring-blue-500 focus:border-transparent
                   disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Solar event"
        >
          {SOLAR_EVENTS.map((event) => (
            <option key={event.value} value={event.value}>
              {event.label}
            </option>
          ))}
        </select>
        {/* Event Description */}
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-300">
          {getEventDescription()}
        </p>
      </div>

      {/* Offset Input */}
      <div>
        <label
          htmlFor="offset_minutes"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Offset (minutes):
        </label>
        <div className="flex items-center gap-2">
          <input
            id="offset_minutes"
            type="number"
            min={-SCHEDULE_LIMITS.MAX_OFFSET_MINUTES}
            max={SCHEDULE_LIMITS.MAX_OFFSET_MINUTES}
            value={value.offset_minutes}
            onChange={(e) => handleOffsetChange(e.target.value)}
            disabled={disabled}
            className="w-32 rounded-md border border-gray-300 dark:border-gray-600
                     bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                     focus:ring-2 focus:ring-blue-500 focus:border-transparent
                     disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Offset in minutes"
          />
          <span className="text-sm text-gray-700 dark:text-gray-300">minutes</span>
        </div>
        {errors.offset_minutes && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">
            {errors.offset_minutes}
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
                  value.offset_minutes === preset.value
                    ? 'bg-blue-500 text-white hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
                }
                ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              `}
              aria-label={`Set offset to ${preset.value > 0 ? '+' : ''}${preset.value} minutes`}
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
          {previewText}
        </p>
      </div>
    </div>
  );
};

SolarTriggerForm.propTypes = {
  /** Solar trigger configuration containing solar_event, offset_minutes, and optional days_of_week */
  value: PropTypes.shape({
    solar_event: PropTypes.string.isRequired,
    offset_minutes: PropTypes.number.isRequired,
    days_of_week: PropTypes.arrayOf(PropTypes.number),
  }),
  /** Callback when solar trigger configuration changes */
  onChange: PropTypes.func.isRequired,
  /** Whether the form is disabled */
  disabled: PropTypes.bool,
  /** Validation errors for solar trigger fields */
  errors: PropTypes.shape({
    solar_event: PropTypes.string,
    offset_minutes: PropTypes.string,
    days_of_week: PropTypes.string,
  }),
};

export default SolarTriggerForm;

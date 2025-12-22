import { useEffect } from 'react';
import PropTypes from 'prop-types';
import { DAYS_OF_WEEK } from './constants';

/**
 * DaysOfWeekSelector Component
 *
 * A reusable component for selecting which days of the week a schedule should run.
 * Shows 7 toggle buttons (Monday-Sunday) and an "All Days" quick-select button.
 *
 * @component
 * @example
 * // Select specific days
 * <DaysOfWeekSelector
 *   value={[0, 1, 2, 3, 4]} // Mon-Fri
 *   onChange={handleChange}
 * />
 *
 * @example
 * // All days (null value)
 * <DaysOfWeekSelector
 *   value={null} // All days
 *   onChange={handleChange}
 * />
 *
 * @example
 * // Compact mode with single-letter labels
 * <DaysOfWeekSelector
 *   value={[5, 6]} // Weekend
 *   onChange={handleChange}
 *   compact
 * />
 */
const DaysOfWeekSelector = ({
  value,
  onChange,
  disabled = false,
  allowEmpty = false,
  compact = false,
}) => {
  /**
   * Initialize to valid state when allowEmpty=false and value is empty array
   * This handles the edge case where value={[]} is passed but allowEmpty={false}
   */
  useEffect(() => {
    if (!allowEmpty && Array.isArray(value) && value.length === 0) {
      onChange([0]); // Default to Monday
    }
  }, [allowEmpty, value, onChange]);

  /**
   * Handle toggling a specific day of the week
   * @param {number} dayValue - Day value (0=Monday, 6=Sunday)
   */
  const handleDayToggle = (dayValue) => {
    if (disabled) return;

    // Convert null/undefined (all days) to explicit array [0,1,2,3,4,5,6]
    const currentDays = value ?? [0, 1, 2, 3, 4, 5, 6];

    // Ensure currentDays is an array
    const daysArray = Array.isArray(currentDays) ? currentDays : [0, 1, 2, 3, 4, 5, 6];

    if (daysArray.includes(dayValue)) {
      // Deselect day
      const newDays = daysArray.filter((d) => d !== dayValue);

      // Prevent empty array if !allowEmpty
      if (newDays.length === 0 && !allowEmpty) return;

      onChange(newDays.length === 0 ? [] : newDays);
    } else {
      // Select day
      const newDays = [...daysArray, dayValue].sort((a, b) => a - b);

      // If all 7 selected, convert to null (all days)
      onChange(newDays.length === 7 ? null : newDays);
    }
  };

  /**
   * Handle "All Days" button click
   */
  const handleAllDaysClick = () => {
    if (disabled) return;
    onChange(null); // null = all days
  };

  /**
   * Check if a specific day is selected
   * @param {number} dayValue - Day value to check
   * @returns {boolean}
   */
  const isDaySelected = (dayValue) => {
    if (value === null || value === undefined) return true; // null/undefined = all days selected
    return Array.isArray(value) && value.includes(dayValue);
  };

  /**
   * Check if all days are selected
   * @returns {boolean}
   */
  const isAllDaysSelected = () => {
    return (
      value === null ||
      value === undefined ||
      (Array.isArray(value) && value.length === 7)
    );
  };

  /**
   * Get button label for a day
   * @param {Object} day - Day object from DAYS_OF_WEEK
   * @returns {string}
   */
  const getDayLabel = (day) => {
    if (compact) {
      // Single letter: M, T, W, T, F, S, S
      return day.shortLabel.charAt(0);
    }
    return day.shortLabel;
  };

  return (
    <div className="space-y-3">
      {/* Label */}
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
        Days of Week
      </label>

      {/* Day buttons */}
      <div className="flex flex-wrap gap-2">
        {DAYS_OF_WEEK.map((day) => {
          const selected = isDaySelected(day.value);
          return (
            <button
              key={day.value}
              type="button"
              onClick={() => handleDayToggle(day.value)}
              disabled={disabled}
              aria-pressed={selected}
              aria-label={day.label}
              className={`
                px-3 py-2 rounded-md text-sm font-medium
                transition-colors duration-150
                focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
                dark:focus:ring-offset-gray-800
                ${
                  selected
                    ? 'bg-blue-500 text-white hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
                }
                ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                ${compact ? 'min-w-[2.5rem]' : 'min-w-[3.5rem]'}
              `}
            >
              {getDayLabel(day)}
            </button>
          );
        })}
      </div>

      {/* All Days button */}
      <div>
        <button
          type="button"
          onClick={handleAllDaysClick}
          disabled={disabled}
          aria-pressed={isAllDaysSelected()}
          className={`
            px-4 py-2 rounded-md text-sm font-medium
            transition-colors duration-150
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
            dark:focus:ring-offset-gray-800
            ${
              isAllDaysSelected()
                ? 'bg-blue-500 text-white hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
            }
            ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
          `}
        >
          All Days
        </button>
      </div>
    </div>
  );
};

DaysOfWeekSelector.propTypes = {
  /** Array of selected day values [0-6] where 0=Monday, 6=Sunday. null = all days */
  value: PropTypes.arrayOf(PropTypes.number),
  /** Callback when selection changes */
  onChange: PropTypes.func.isRequired,
  /** Whether the selector is disabled */
  disabled: PropTypes.bool,
  /** Whether to allow deselecting all days (default false) */
  allowEmpty: PropTypes.bool,
  /** Show single-letter labels (M, T, W, T, F, S, S) instead of short labels */
  compact: PropTypes.bool,
};

export default DaysOfWeekSelector;

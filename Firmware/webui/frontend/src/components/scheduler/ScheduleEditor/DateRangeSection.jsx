import { useMemo } from 'react';
import PropTypes from 'prop-types';
import { MAX_DATE_RANGE_DAYS } from './constants';

/**
 * DateRangeSection Component
 *
 * A reusable component for setting optional start_date and end_date for a schedule.
 * Uses native HTML5 date inputs for consistency with existing codebase patterns.
 *
 * @component
 * @example
 * // Basic usage
 * <DateRangeSection
 *   value={{ start_date: '2024-01-01', end_date: '2024-12-31' }}
 *   onChange={handleChange}
 * />
 *
 * @example
 * // With validation errors
 * <DateRangeSection
 *   value={{ start_date: '2024-12-31', end_date: '2024-01-01' }}
 *   onChange={handleChange}
 *   errors={{ start_date: 'Required' }}
 * />
 *
 * @example
 * // Disabled state
 * <DateRangeSection
 *   value={{ start_date: null, end_date: null }}
 *   onChange={handleChange}
 *   disabled
 * />
 */
const DateRangeSection = ({
  value = { start_date: null, end_date: null },
  onChange,
  disabled = false,
  errors = {},
}) => {
  const { start_date, end_date } = value || {};

  /**
   * Validate date range (client-side)
   * - Checks for valid date format (not NaN)
   * - Checks that end_date >= start_date
   * - Checks that range doesn't exceed MAX_DATE_RANGE_DAYS (10 years)
   *
   * NOTE: Backend validation is also performed in schedule_schema.py:
   * - _validate_date_string() validates ISO 8601 format (YYYY-MM-DD)
   * - validate_schedule() checks start_date <= end_date
   * - DATE_FORMAT_REGEX enforces format pattern
   * - datetime.strptime validates actual date validity (e.g., rejects Feb 30)
   *
   * Both client and server validation use the same rules to ensure consistency.
   *
   * @returns {string|null} Error message or null if valid
   */
  const validateDateRange = () => {
    // Only validate when both dates are provided
    if (!start_date || !end_date) return null;

    const startDateObj = new Date(start_date);
    const endDateObj = new Date(end_date);

    // Check for invalid date format (NaN)
    if (isNaN(startDateObj.getTime()) || isNaN(endDateObj.getTime())) {
      return 'Invalid date format';
    }

    // Check ordering (must check this before range to give better error message)
    if (endDateObj < startDateObj) {
      return 'End date must be greater than or equal to start date';
    }

    // Check reasonable range (max 10 years = 3650 days)
    const daysDiff = (endDateObj - startDateObj) / (1000 * 60 * 60 * 24);
    if (daysDiff > MAX_DATE_RANGE_DAYS) {
      return 'Date range cannot exceed 10 years';
    }

    return null;
  };

  /**
   * Handle start date change
   * @param {Event} e - Input change event
   */
  const handleStartDateChange = (e) => {
    const newValue = e.target.value || null;
    onChange({
      start_date: newValue,
      end_date,
    });
  };

  /**
   * Handle end date change
   * @param {Event} e - Input change event
   */
  const handleEndDateChange = (e) => {
    const newValue = e.target.value || null;
    onChange({
      start_date,
      end_date: newValue,
    });
  };

  /**
   * Clear start date
   */
  const handleClearStartDate = () => {
    onChange({
      start_date: null,
      end_date,
    });
  };

  /**
   * Clear end date
   */
  const handleClearEndDate = () => {
    onChange({
      start_date,
      end_date: null,
    });
  };

  // Memoize validation to avoid recalculating on every render
  const validationError = useMemo(
    () => validateDateRange(),
    [start_date, end_date]
  );

  return (
    <div className="space-y-4">
      {/* Section Label */}
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
        Date Range (Optional)
      </label>

      {/* Start Date Input */}
      <div>
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <label
              htmlFor="start-date"
              className="block text-xs text-gray-600 dark:text-gray-300 mb-1"
            >
              Start Date
            </label>
            <input
              id="start-date"
              type="date"
              value={start_date || ''}
              onChange={handleStartDateChange}
              disabled={disabled}
              aria-label="Start date"
              className={`
                w-full px-3 py-2 text-sm border rounded
                bg-white dark:bg-gray-800
                text-gray-900 dark:text-gray-100
                border-gray-300 dark:border-gray-600
                focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                dark:focus:ring-blue-400
                ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
                ${errors.start_date ? 'border-red-500 dark:border-red-500' : ''}
              `}
            />
            {errors.start_date && (
              <p className="mt-1 text-xs text-red-600 dark:text-red-400">
                {errors.start_date}
              </p>
            )}
          </div>
          {start_date && (
            <button
              type="button"
              onClick={handleClearStartDate}
              disabled={disabled}
              aria-label="Clear start date"
              className={`
                px-3 py-2 text-sm font-medium rounded
                bg-gray-100 dark:bg-gray-700
                text-gray-700 dark:text-gray-300
                hover:bg-gray-200 dark:hover:bg-gray-600
                border border-gray-300 dark:border-gray-600
                focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
                dark:focus:ring-offset-gray-800
                transition-colors duration-150
                ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              `}
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* End Date Input */}
      <div>
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <label
              htmlFor="end-date"
              className="block text-xs text-gray-600 dark:text-gray-300 mb-1"
            >
              End Date
            </label>
            <input
              id="end-date"
              type="date"
              value={end_date || ''}
              onChange={handleEndDateChange}
              disabled={disabled}
              aria-label="End date"
              className={`
                w-full px-3 py-2 text-sm border rounded
                bg-white dark:bg-gray-800
                text-gray-900 dark:text-gray-100
                border-gray-300 dark:border-gray-600
                focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                dark:focus:ring-blue-400
                ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
                ${errors.end_date ? 'border-red-500 dark:border-red-500' : ''}
              `}
            />
            {errors.end_date && (
              <p className="mt-1 text-xs text-red-600 dark:text-red-400">
                {errors.end_date}
              </p>
            )}
          </div>
          {end_date && (
            <button
              type="button"
              onClick={handleClearEndDate}
              disabled={disabled}
              aria-label="Clear end date"
              className={`
                px-3 py-2 text-sm font-medium rounded
                bg-gray-100 dark:bg-gray-700
                text-gray-700 dark:text-gray-300
                hover:bg-gray-200 dark:hover:bg-gray-600
                border border-gray-300 dark:border-gray-600
                focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
                dark:focus:ring-offset-gray-800
                transition-colors duration-150
                ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              `}
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Validation Error */}
      {validationError && (
        <p className="text-sm text-red-600 dark:text-red-400">
          {validationError}
        </p>
      )}
    </div>
  );
};

DateRangeSection.propTypes = {
  /** Date range value with start_date and end_date (ISO 8601 format: YYYY-MM-DD) */
  value: PropTypes.shape({
    start_date: PropTypes.string,
    end_date: PropTypes.string,
  }),
  /** Callback when date range changes */
  onChange: PropTypes.func.isRequired,
  /** Whether the inputs are disabled */
  disabled: PropTypes.bool,
  /** Error messages for start_date and end_date fields */
  errors: PropTypes.shape({
    start_date: PropTypes.string,
    end_date: PropTypes.string,
  }),
};

export default DateRangeSection;

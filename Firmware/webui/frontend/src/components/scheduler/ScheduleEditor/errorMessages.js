/**
 * Centralized error messages for ScheduleEditor components.
 *
 * Provides consistent, user-friendly error messages across all scheduler forms.
 * Messages are designed to be clear and actionable.
 *
 * @module ScheduleEditor/errorMessages
 */

/**
 * Error messages for network and server communication issues.
 */
export const NETWORK_ERRORS = {
  NETWORK_ERROR: 'Unable to save. Please check your connection.',
  SERVER_ERROR: 'Server error. Please try again later.',
  TIMEOUT_ERROR: 'Request timed out. Please try again.',
};

/**
 * Error messages for form validation failures.
 */
export const VALIDATION_ERRORS = {
  GENERAL: 'Please fix the errors above.',
  REQUIRED_FIELD: 'This field is required.',
};

/**
 * Error message generators for numeric input validation.
 * Functions accept bounds and return appropriate error strings.
 */
export const NUMERIC_ERRORS = {
  /**
   * Generate error message for interval validation.
   * @param {number} min - Minimum allowed value
   * @param {number} max - Maximum allowed value
   * @returns {string} Error message
   */
  INVALID_INTERVAL: (min, max) => `Interval must be between ${min} and ${max} minutes`,

  /**
   * Generate error message for cooldown validation.
   * @param {number} min - Minimum allowed value
   * @param {number} max - Maximum allowed value
   * @returns {string} Error message
   */
  INVALID_COOLDOWN: (min, max) => `Cooldown must be between ${min} and ${max} minutes`,

  /**
   * Error message for invalid threshold values.
   */
  INVALID_THRESHOLD: 'Threshold must be a non-negative number',

  /**
   * Generate generic range error message.
   * @param {number} min - Minimum allowed value
   * @param {number} max - Maximum allowed value
   * @returns {string} Error message
   */
  OUT_OF_RANGE: (min, max) => `Value must be between ${min} and ${max}`,
};

/**
 * Error messages for date range validation.
 */
export const DATE_ERRORS = {
  DATE_RANGE_INVALID: 'End date must be after start date',
  DATE_RANGE_TOO_LONG: 'Date range cannot exceed 10 years',
  INVALID_DATE_FORMAT: 'Invalid date format',
};

/**
 * Error messages for day-of-week selection.
 */
export const DAY_SELECTION_ERRORS = {
  AT_LEAST_ONE_DAY: 'At least one day must be selected',
};

/**
 * Error messages for time input validation.
 */
export const TIME_ERRORS = {
  INVALID_TIME_FORMAT: 'Invalid time format',
  START_AFTER_END: 'Start time must be before end time',
  SAME_START_END: 'Start and end times cannot be the same',
};

/**
 * Combined error messages object for convenience imports.
 * @deprecated Prefer importing specific error categories for better tree-shaking.
 */
export const SCHEDULER_ERROR_MESSAGES = {
  ...NETWORK_ERRORS,
  ...VALIDATION_ERRORS,
  ...NUMERIC_ERRORS,
  ...DATE_ERRORS,
  ...DAY_SELECTION_ERRORS,
  ...TIME_ERRORS,
};

export default SCHEDULER_ERROR_MESSAGES;

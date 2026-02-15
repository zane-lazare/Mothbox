/**
 * Shared error codes and message mapping for the Mothbox API.
 *
 * Mirrors backend error codes from webui/backend/lib/error_codes.py.
 * Use getErrorMessage() to extract user-friendly messages from API errors.
 *
 * Issue #388 - Standardize error codes across backend/frontend
 *
 * @module utils/errorCodes
 */

/**
 * Error code constants matching the backend.
 * Used for programmatic error handling (e.g., switch statements).
 */
export const ERROR_CODES = {
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  NOT_FOUND: 'NOT_FOUND',
  CONFLICT_ERROR: 'CONFLICT_ERROR',
  ACTIVATION_ERROR: 'ACTIVATION_ERROR',
  RATE_LIMIT_ERROR: 'RATE_LIMIT_ERROR',
  HARDWARE_ERROR: 'HARDWARE_ERROR',
  STORAGE_ERROR: 'STORAGE_ERROR',
  PERMISSION_ERROR: 'PERMISSION_ERROR',
  SERVER_ERROR: 'SERVER_ERROR',
  // Client-side only (no backend equivalent)
  NETWORK_ERROR: 'NETWORK_ERROR',
  TIMEOUT_ERROR: 'TIMEOUT_ERROR',
};

/**
 * User-friendly messages for each error code.
 * These are shown to the user when an API error occurs.
 */
export const ERROR_MESSAGES = {
  [ERROR_CODES.VALIDATION_ERROR]: 'Please fix the errors above.',
  [ERROR_CODES.NOT_FOUND]: 'Resource not found. It may have been deleted.',
  [ERROR_CODES.CONFLICT_ERROR]: 'Schedule has conflicts that must be resolved.',
  [ERROR_CODES.ACTIVATION_ERROR]: 'Failed to activate schedule.',
  [ERROR_CODES.RATE_LIMIT_ERROR]: 'Too many requests. Please wait a moment.',
  [ERROR_CODES.HARDWARE_ERROR]: 'Hardware unavailable. Please check connections.',
  [ERROR_CODES.STORAGE_ERROR]: 'Storage error. Check available disk space.',
  [ERROR_CODES.PERMISSION_ERROR]: 'Permission denied.',
  [ERROR_CODES.SERVER_ERROR]: 'Server error. Please try again later.',
  [ERROR_CODES.NETWORK_ERROR]: 'Unable to save. Please check your connection.',
  [ERROR_CODES.TIMEOUT_ERROR]: 'Request timed out. Please try again.',
};

/**
 * Sanitize an error message string for safe display.
 *
 * Strips HTML tags (defense-in-depth — React escapes by default)
 * and truncates long messages.
 *
 * @param {string} message - Raw error message
 * @param {number} [maxLength=200] - Maximum message length
 * @returns {string} Sanitized message
 */
export function sanitizeMessage(message, maxLength = 200) {
  if (!message) return 'An unexpected error occurred.';
  let msg = String(message);

  // Strip HTML tags iteratively (handles incomplete/malformed tags)
  let previousLength;
  do {
    previousLength = msg.length;
    msg = msg.replace(/<[^>]*>?/g, '');
  } while (msg.length < previousLength);

  return msg.length > maxLength ? msg.slice(0, maxLength) + '...' : msg;
}

/**
 * Extract a user-friendly error message from an API error.
 *
 * Checks for known error codes first (from API response or error object),
 * then falls back to the server-provided error message (sanitized),
 * then to a generic fallback.
 *
 * @param {Error|Object} error - Axios error or error-like object
 * @param {string} [fallback='An unexpected error occurred.'] - Fallback message
 * @returns {string} User-friendly error message
 */
export function getErrorMessage(error, fallback = 'An unexpected error occurred.') {
  // Check for known error code from API response (axios pattern)
  const apiCode = error?.response?.data?.code;
  if (apiCode && ERROR_MESSAGES[apiCode]) {
    return ERROR_MESSAGES[apiCode];
  }

  // Check for known error code on the error object itself
  if (error?.code && ERROR_MESSAGES[error.code]) {
    return ERROR_MESSAGES[error.code];
  }

  // Fall back to server-provided message, sanitized
  const rawMessage = error?.response?.data?.error || error?.message;
  if (rawMessage) {
    return sanitizeMessage(rawMessage);
  }

  return fallback;
}

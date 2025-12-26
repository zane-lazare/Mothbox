import PropTypes from 'prop-types'
import { useCronValidation } from '../../../hooks/useCronValidation'
import { CRON_PRESETS, CRON_HELP } from './constants'

/**
 * CronExpressionInput Component (Issue #233)
 *
 * A component for entering and validating cron expressions with real-time feedback.
 * Provides preset buttons, validation status, human-readable descriptions, and
 * next execution time previews.
 *
 * Features:
 * - Real-time validation with debounced API calls
 * - Quick preset buttons for common patterns
 * - Visual success/error indicators
 * - Human-readable description of cron expression
 * - Next N execution times preview
 * - Format help text
 * - Dark mode support
 *
 * @component
 * @example
 * <CronExpressionInput
 *   value="0 21 * * *"
 *   onChange={(newExpression) => console.log(newExpression)}
 *   disabled={false}
 * />
 */
const CronExpressionInput = ({ value = '', onChange, disabled = false }) => {
  // Validate the expression with debouncing
  const { data: validation, isLoading, errorMessage } = useCronValidation(value)

  /**
   * Handle input change
   */
  const handleChange = (e) => {
    onChange(e.target.value)
  }

  /**
   * Handle preset button click
   */
  const handlePresetClick = (expression) => {
    onChange(expression)
  }

  /**
   * Format execution time for display
   * @param {string} isoTime - ISO 8601 timestamp
   * @returns {string} Formatted time
   */
  const formatExecutionTime = (isoTime) => {
    try {
      const date = new Date(isoTime)
      return date.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return isoTime
    }
  }

  // Determine validation state
  const isValid = validation?.valid === true
  const isInvalid = validation?.valid === false
  const showValidation = value.trim() && validation && !isLoading

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <label
          htmlFor="cron-expression"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Cron Expression
        </label>

        {/* Input field with validation styling */}
        <div className="relative">
          <input
            id="cron-expression"
            type="text"
            value={value}
            onChange={handleChange}
            disabled={disabled}
            placeholder="e.g., 0 21 * * *"
            className={`
              w-full rounded-md border px-3 py-2 font-mono text-sm
              bg-white dark:bg-gray-800 text-gray-900 dark:text-white
              focus:ring-2 focus:ring-blue-500 focus:border-transparent
              disabled:opacity-50 disabled:cursor-not-allowed
              ${
                showValidation
                  ? isValid
                    ? 'border-green-500 dark:border-green-400'
                    : 'border-red-500 dark:border-red-400'
                  : 'border-gray-300 dark:border-gray-600'
              }
            `}
            aria-label="Cron expression input"
            aria-invalid={isInvalid}
            aria-describedby="cron-help cron-validation"
          />

          {/* Validation status icon */}
          {showValidation && !isLoading && (
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
              {isValid ? (
                <svg
                  className="h-5 w-5 text-green-500 dark:text-green-400"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                  aria-label="Valid expression"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clipRule="evenodd"
                  />
                </svg>
              ) : (
                <svg
                  className="h-5 w-5 text-red-500 dark:text-red-400"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                  aria-label="Invalid expression"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
            </div>
          )}

          {/* Loading indicator */}
          {isLoading && (
            <div
              className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none"
              aria-label="Validating"
            >
              <svg
                className="animate-spin h-5 w-5 text-gray-400 dark:text-gray-500"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            </div>
          )}
        </div>

        {/* Format help text */}
        <p
          id="cron-help"
          className="mt-1 text-xs text-gray-500 dark:text-gray-400 font-mono"
        >
          Format: {CRON_HELP.format} • {CRON_HELP.special}
        </p>
      </div>

      {/* Validation message */}
      {showValidation && (
        <div id="cron-validation">
          {isValid ? (
            <div className="space-y-2">
              {/* Human-readable description */}
              <p className="text-sm text-green-600 dark:text-green-400 font-medium">
                {validation.description}
              </p>

              {/* Next execution times */}
              {validation.next_executions && validation.next_executions.length > 0 && (
                <div>
                  <p className="text-xs text-gray-700 dark:text-gray-300 font-medium mb-1">
                    Next executions:
                  </p>
                  <ul className="space-y-1">
                    {validation.next_executions.map((time) => (
                      <li
                        key={time}
                        className="text-xs text-gray-600 dark:text-gray-400 font-mono"
                      >
                        {formatExecutionTime(time)}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-red-600 dark:text-red-400">
              {errorMessage}
            </p>
          )}
        </div>
      )}

      {/* Preset buttons */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Quick presets:
        </label>
        <div className="flex flex-wrap gap-2">
          {CRON_PRESETS.map((preset) => (
            <button
              key={preset.expression}
              type="button"
              onClick={() => handlePresetClick(preset.expression)}
              disabled={disabled}
              className={`
                px-3 py-1.5 rounded-md text-xs font-medium
                transition-colors duration-150
                focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
                dark:focus:ring-offset-gray-800
                ${
                  value === preset.expression
                    ? 'bg-blue-500 text-white hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
                }
                ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              `}
              aria-label={`Set expression to ${preset.label}`}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      {/* Field reference */}
      <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
        <p className="text-xs text-gray-700 dark:text-gray-300 font-medium mb-2">
          Field reference:
        </p>
        <div className="grid grid-cols-2 gap-2">
          {CRON_HELP.fields.map((field) => (
            <div key={field.name} className="text-xs">
              <span className="font-medium text-gray-700 dark:text-gray-300">
                {field.name}:
              </span>{' '}
              <span className="text-gray-600 dark:text-gray-400 font-mono">
                {field.range}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

CronExpressionInput.propTypes = {
  /** Current cron expression value */
  value: PropTypes.string,
  /** Callback when expression changes */
  onChange: PropTypes.func.isRequired,
  /** Whether the input is disabled */
  disabled: PropTypes.bool,
}

export default CronExpressionInput

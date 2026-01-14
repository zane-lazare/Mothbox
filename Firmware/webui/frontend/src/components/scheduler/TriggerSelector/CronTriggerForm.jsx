import PropTypes from 'prop-types'
import cronstrue from 'cronstrue'

/**
 * CronTriggerForm Component
 *
 * Form for configuring cron expression triggers (expert mode).
 *
 * @component
 */
function CronTriggerForm({ trigger, onChange, disabled = false, error = null }) {
  const cronExpression = trigger?.cron_expression || '0 20 * * *'

  /**
   * Handle cron expression change
   */
  const handleExpressionChange = (e) => {
    onChange({
      ...trigger,
      cron_expression: e.target.value,
    })
  }

  /**
   * Parse cron expression and return human-readable description using cronstrue library
   */
  const describeCron = (expression) => {
    if (!expression) return ''

    try {
      return cronstrue.toString(expression, { use24HourTimeFormat: false })
    } catch {
      return 'Invalid cron expression'
    }
  }

  const isValidCron = (expression) => {
    if (!expression) return false
    try {
      cronstrue.toString(expression)
      return true
    } catch {
      return false
    }
  }

  const hasError = error || !isValidCron(cronExpression)

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4" data-testid="cron-trigger-form">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-sm text-gray-900 dark:text-white">Cron Expression</span>
        <span className="text-xs text-yellow-600 dark:text-yellow-500">advanced</span>
      </div>

      <div className="space-y-4">
        {/* Cron Input */}
        <input
          type="text"
          value={cronExpression}
          onChange={handleExpressionChange}
          disabled={disabled}
          placeholder="0 20 * * *"
          className={`w-full bg-transparent border rounded px-3 py-2 text-sm text-gray-900 dark:text-white font-mono
                     focus:outline-none
                     disabled:opacity-50 disabled:cursor-not-allowed
                     ${hasError ? 'border-red-500 focus:border-red-400' : 'border-gray-300 dark:border-gray-800 focus:border-gray-500 dark:focus:border-gray-600'}`}
          data-testid="cron-expression"
        />

        {/* Description */}
        <div
          className={`text-xs ${hasError ? 'text-red-400' : 'text-gray-600'}`}
          data-testid="cron-description"
        >
          {describeCron(cronExpression)}
        </div>

        {/* Error message */}
        {error && (
          <div className="text-xs text-red-400" data-testid="cron-error">
            {error}
          </div>
        )}

        {/* Help Link */}
        <a
          href="https://crontab.guru/"
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-blue-400 hover:text-blue-300"
          data-testid="cron-help-link"
        >
          Cron syntax reference ↗
        </a>
      </div>
    </div>
  )
}

CronTriggerForm.propTypes = {
  trigger: PropTypes.shape({
    trigger_type: PropTypes.string,
    cron_expression: PropTypes.string,
  }),
  onChange: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
  error: PropTypes.string,
}

export default CronTriggerForm

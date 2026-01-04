import PropTypes from 'prop-types'

/**
 * CronTriggerForm Component
 *
 * Form for configuring cron expression triggers (expert mode).
 *
 * @component
 */
function CronTriggerForm({ trigger, onChange, disabled = false }) {
  const cronExpression = trigger?.cron_expression || '*/15 * * * *'

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
   * Parse cron expression and return human-readable description
   * This is a simple implementation - can be enhanced later
   */
  const describeCron = (expression) => {
    if (!expression) return ''

    const parts = expression.trim().split(/\s+/)
    if (parts.length < 5) return 'Invalid expression'

    const [minute, hour] = parts

    // Handle some common patterns
    if (minute.startsWith('*/')) {
      const interval = minute.slice(2)
      if (hour.includes('-')) {
        const [start, end] = hour.split('-')
        return `Every ${interval} minutes, ${start}:00-${end}:00`
      }
      return `Every ${interval} minutes`
    }

    if (minute === '0' && !hour.includes('*') && !hour.includes('/')) {
      const hourNum = parseInt(hour, 10)
      const period = hourNum >= 12 ? 'pm' : 'am'
      const displayHour = hourNum > 12 ? hourNum - 12 : hourNum === 0 ? 12 : hourNum
      return `Daily at ${displayHour}${period}`
    }

    return 'Custom schedule'
  }

  return (
    <div className="border border-gray-800 rounded-lg p-4" data-testid="cron-trigger-form">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-sm text-white">Cron Expression</span>
        <span className="text-xs text-yellow-500">advanced</span>
      </div>

      <div className="space-y-4">
        {/* Cron Input */}
        <input
          type="text"
          value={cronExpression}
          onChange={handleExpressionChange}
          disabled={disabled}
          placeholder="*/15 * * * *"
          className="w-full bg-transparent border border-gray-800 rounded px-3 py-2 text-sm text-white font-mono
                     focus:border-gray-600 focus:outline-none
                     disabled:opacity-50 disabled:cursor-not-allowed"
          data-testid="cron-expression"
        />

        {/* Description */}
        <div className="text-xs text-gray-600" data-testid="cron-description">
          {describeCron(cronExpression)}
        </div>

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
}

export default CronTriggerForm

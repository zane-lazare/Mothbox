/**
 * Constants for Expert Mode Cron Expression Editor (Issue #233)
 *
 * Provides cron presets and help text for the cron expression input component.
 */

/**
 * Quick preset cron expressions for common scheduling patterns
 *
 * These presets help users quickly set up common scheduling scenarios
 * without needing to understand cron syntax.
 */
export const CRON_PRESETS = [
  { label: 'Every hour', expression: '0 * * * *' },
  { label: 'Every 5 min', expression: '*/5 * * * *' },
  { label: 'Every 15 min', expression: '*/15 * * * *' },
  { label: 'Daily midnight', expression: '0 0 * * *' },
  { label: 'Daily 9 PM', expression: '0 21 * * *' },
  { label: 'Weekdays 9 PM', expression: '0 21 * * 1-5' },
]

/**
 * Help text for cron expression format
 *
 * Provides format documentation and special character explanations
 * to assist users in writing their own cron expressions.
 */
export const CRON_HELP = {
  format: 'minute hour day month weekday',
  fields: [
    { name: 'minute', range: '0-59' },
    { name: 'hour', range: '0-23' },
    { name: 'day', range: '1-31' },
    { name: 'month', range: '1-12' },
    { name: 'weekday', range: '0-6 (Sun-Sat)' },
  ],
  special: '* = any, */N = every N, N-M = range, N,M = list',
}

/**
 * Constants for Expert Mode Cron Expression Editor (Issue #233)
 */

export interface CronPreset {
  readonly label: string
  readonly expression: string
}

export interface CronFieldHelp {
  readonly name: string
  readonly range: string
}

export interface CronHelp {
  readonly format: string
  readonly fields: readonly CronFieldHelp[]
  readonly special: string
}

/** Quick preset cron expressions for common scheduling patterns */
export const CRON_PRESETS: readonly CronPreset[] = [
  { label: 'Every hour', expression: '0 * * * *' },
  { label: 'Every 5 min', expression: '*/5 * * * *' },
  { label: 'Every 15 min', expression: '*/15 * * * *' },
  { label: 'Daily midnight', expression: '0 0 * * *' },
  { label: 'Daily 9 PM', expression: '0 21 * * *' },
  { label: 'Weekdays 9 PM', expression: '0 21 * * 1-5' },
] as const

/** Help text for cron expression format */
export const CRON_HELP: CronHelp = {
  format: 'minute hour day month weekday',
  fields: [
    { name: 'minute', range: '0-59' },
    { name: 'hour', range: '0-23' },
    { name: 'day', range: '1-31' },
    { name: 'month', range: '1-12' },
    { name: 'weekday', range: '0-6 (Sun-Sat)' },
  ],
  special: '* = any, */N = every N, N-M = range, N,M = list',
} as const

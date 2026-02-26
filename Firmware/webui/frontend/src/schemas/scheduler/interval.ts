import { z } from 'zod'
import { SCHEDULE_LIMITS } from '../../components/scheduler/ScheduleEditor/constants'

/**
 * Schema for the interval_minutes field owned by IntervalTriggerForm.
 *
 * TimeWindowInput and DaysOfWeekSelector have their own schemas
 * (scheduler/time-window.ts, future) and are pass-through here.
 */
export const intervalTriggerSchema = z.object({
  interval_minutes: z
    .number({ error: 'Interval must be a number' })
    .int('Interval must be a whole number')
    .min(
      SCHEDULE_LIMITS.MIN_INTERVAL_MINUTES,
      `Interval must be at least ${SCHEDULE_LIMITS.MIN_INTERVAL_MINUTES} minute${SCHEDULE_LIMITS.MIN_INTERVAL_MINUTES !== 1 ? 's' : ''}`,
    )
    .max(
      SCHEDULE_LIMITS.MAX_INTERVAL_MINUTES,
      `Interval cannot exceed ${SCHEDULE_LIMITS.MAX_INTERVAL_MINUTES} minutes`,
    ),
})

export type IntervalTriggerFormData = z.infer<typeof intervalTriggerSchema>

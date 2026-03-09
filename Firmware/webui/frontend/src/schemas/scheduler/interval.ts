import { z } from 'zod'
import { SCHEDULE_LIMITS } from '../../components/scheduler/ScheduleEditor/constants'
import { TYPE, RANGE } from '../../constants/errorMessages'

/**
 * Schema for the interval_minutes field owned by IntervalTriggerForm.
 *
 * TimeWindowInput and DaysOfWeekSelector have their own schemas
 * (scheduler/time-window.ts, future) and are pass-through here.
 */
export const intervalTriggerSchema = z.object({
  interval_minutes: z
    .number({ error: TYPE.number('Interval') })
    .int(TYPE.integer('Interval'))
    .min(
      SCHEDULE_LIMITS.MIN_INTERVAL_MINUTES,
      RANGE.min(SCHEDULE_LIMITS.MIN_INTERVAL_MINUTES, `minute${SCHEDULE_LIMITS.MIN_INTERVAL_MINUTES !== 1 ? 's' : ''}`),
    )
    .max(
      SCHEDULE_LIMITS.MAX_INTERVAL_MINUTES,
      RANGE.max(SCHEDULE_LIMITS.MAX_INTERVAL_MINUTES, 'minutes'),
    ),
})

export type IntervalTriggerFormData = z.infer<typeof intervalTriggerSchema>

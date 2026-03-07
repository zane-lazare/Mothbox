import { z } from 'zod'
import { TIME_FORMAT_REGEX } from '../../components/scheduler/ScheduleEditor/constants'

/**
 * Schema for fields owned by RecurringDaysTriggerForm: days + time.
 *
 * days: array of day-of-week integers (0-6), at least 1 required.
 * time: HH:MM string.
 */
export const recurringDaysTriggerSchema = z.object({
  days: z
    .array(
      z
        .number({ error: 'Day must be a number' })
        .int('Day must be a whole number')
        .min(0, 'Day must be between 0 and 6')
        .max(6, 'Day must be between 0 and 6'),
    )
    .min(1, 'At least one day must be selected'),
  time: z
    .string()
    .regex(TIME_FORMAT_REGEX, 'Must be a valid time in HH:MM format'),
})

export type RecurringDaysTriggerFormData = z.infer<typeof recurringDaysTriggerSchema>

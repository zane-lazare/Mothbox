import { z } from 'zod'
import { TIME_FORMAT_REGEX } from '../../components/scheduler/ScheduleEditor/constants'

/**
 * Schema for the time_of_day field owned by FixedTimeTriggerForm.
 *
 * DaysOfWeekSelector has its own schema (future migration) and is
 * pass-through here.
 */
export const fixedTimeTriggerSchema = z.object({
  time_of_day: z
    .string()
    .regex(TIME_FORMAT_REGEX, 'Must be a valid time in HH:MM format'),
})

export type FixedTimeTriggerFormData = z.infer<typeof fixedTimeTriggerSchema>

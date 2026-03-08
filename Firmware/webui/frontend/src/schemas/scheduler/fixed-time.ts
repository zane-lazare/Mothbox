import { z } from 'zod'
import { TIME_FORMAT_REGEX } from '../../components/scheduler/ScheduleEditor/constants'
import { FORMAT } from '../../constants/errorMessages'

/**
 * Schema for the time_of_day field owned by FixedTimeTriggerForm.
 *
 * DaysOfWeekSelector has its own schema (future migration) and is
 * pass-through here.
 */
export const fixedTimeTriggerSchema = z.object({
  time_of_day: z
    .string()
    .regex(TIME_FORMAT_REGEX, FORMAT.validTime),
})

export type FixedTimeTriggerFormData = z.infer<typeof fixedTimeTriggerSchema>

import { z } from 'zod'
import { SCHEDULE_LIMITS } from '../../components/scheduler/ScheduleEditor/constants'

/**
 * Schema for the schedule-level fields owned by ScheduleEditor's useForm.
 *
 * Validates only `name` and `description` -- the top-level fields that live
 * outside any routine/trigger sub-form.
 */
export const scheduleSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, 'Schedule name is required')
    .max(
      SCHEDULE_LIMITS.NAME_MAX_LENGTH,
      `Name must be ${SCHEDULE_LIMITS.NAME_MAX_LENGTH} characters or less`,
    ),
  description: z
    .string()
    .max(
      SCHEDULE_LIMITS.DESCRIPTION_MAX_LENGTH,
      `Description must be ${SCHEDULE_LIMITS.DESCRIPTION_MAX_LENGTH} characters or less`,
    )
    .default(''),
})

export type ScheduleFormData = z.infer<typeof scheduleSchema>

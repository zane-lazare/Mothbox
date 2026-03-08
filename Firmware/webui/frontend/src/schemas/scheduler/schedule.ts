import { z } from 'zod'
import { SCHEDULE_LIMITS } from '../../components/scheduler/ScheduleEditor/constants'
import { REQUIRED, LENGTH } from '../../constants/errorMessages'

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
    .min(1, REQUIRED.field('Schedule name'))
    .max(
      SCHEDULE_LIMITS.NAME_MAX_LENGTH,
      LENGTH.max(SCHEDULE_LIMITS.NAME_MAX_LENGTH),
    ),
  description: z
    .string()
    .max(
      SCHEDULE_LIMITS.DESCRIPTION_MAX_LENGTH,
      LENGTH.max(SCHEDULE_LIMITS.DESCRIPTION_MAX_LENGTH),
    )
    .default(''),
})

export type ScheduleFormData = z.infer<typeof scheduleSchema>

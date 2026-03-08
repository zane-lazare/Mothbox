import { z } from 'zod'
import {
  SCHEDULE_LIMITS,
  MOON_PHASES,
  type MoonPhaseValue,
} from '../../components/scheduler/ScheduleEditor/constants'
import { REQUIRED, TYPE, RANGE, FORMAT, SCHEDULER } from '../../constants/errorMessages'

/**
 * Schema for fields owned by MoonPhaseTriggerForm:
 * moon_phase + time_of_day + offset_days.
 */

const moonPhaseValues = MOON_PHASES.map((p) => p.value) as [
  MoonPhaseValue,
  ...MoonPhaseValue[],
]

export const moonPhaseTriggerSchema = z.object({
  moon_phase: z.enum(moonPhaseValues, {
    error: SCHEDULER.invalidMoonPhase,
  }),
  time_of_day: z
    .string({ error: REQUIRED.field('Time') })
    .regex(/^([01]\d|2[0-3]):[0-5]\d$/, FORMAT.timeRequired),
  offset_days: z
    .number({ error: TYPE.number('Offset') })
    .int(TYPE.integer('Offset'))
    .min(
      -SCHEDULE_LIMITS.MAX_OFFSET_DAYS,
      RANGE.min(-SCHEDULE_LIMITS.MAX_OFFSET_DAYS, 'days'),
    )
    .max(
      SCHEDULE_LIMITS.MAX_OFFSET_DAYS,
      RANGE.max(SCHEDULE_LIMITS.MAX_OFFSET_DAYS, 'days'),
    ),
})

export type MoonPhaseTriggerFormData = z.infer<typeof moonPhaseTriggerSchema>

import { z } from 'zod'
import {
  SENSOR_TYPES,
  SENSOR_COMPARISONS,
  SCHEDULE_LIMITS,
} from '../../components/scheduler/ScheduleEditor/constants'
import { TYPE, RANGE, SCHEDULER } from '../../constants/errorMessages'

/**
 * Schema for fields owned by SensorTriggerForm:
 * sensor_type + comparison + threshold + cooldown_minutes.
 */

// z.enum requires a non-empty tuple — guard against empty constants
const sensorTypeValues = SENSOR_TYPES.map((s) => s.value) as [string, ...string[]]
if (sensorTypeValues.length === 0) throw new Error('SENSOR_TYPES must not be empty')
const comparisonValues = SENSOR_COMPARISONS.map((c) => c.value) as [string, ...string[]]
if (comparisonValues.length === 0) throw new Error('SENSOR_COMPARISONS must not be empty')

export const sensorTriggerSchema = z.object({
  sensor_type: z.enum(sensorTypeValues, { error: SCHEDULER.invalidSensorType }),
  comparison: z.enum(comparisonValues, { error: SCHEDULER.invalidComparison }),
  threshold: z
    .number({ error: TYPE.number('Threshold') })
    .min(0, 'Threshold must be 0 or greater'),
  cooldown_minutes: z
    .number({ error: TYPE.number('Cooldown') })
    .int(TYPE.integer('Cooldown'))
    .min(1, RANGE.min(1, 'minute'))
    .max(
      SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES,
      RANGE.max(SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES, 'minutes'),
    ),
})

export type SensorTriggerFormData = z.infer<typeof sensorTriggerSchema>

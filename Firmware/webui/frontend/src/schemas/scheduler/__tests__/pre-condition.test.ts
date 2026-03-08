import { describe, it, expect } from 'vitest'
import {
  preConditionSchema,
  preConditionTimeWindowSchema,
  TIME_WINDOW_SAME_ERROR,
} from '../pre-condition'
import { SCHEDULE_LIMITS } from '../../../components/scheduler/ScheduleEditor/constants'
import { REQUIRED, TYPE, RANGE, FORMAT, SCHEDULER } from '../../../constants/errorMessages'

/** Return the first Zod issue message from a failed parse, or null. */
function firstError(
  result: { success: boolean; error?: { issues: { message: string }[] } },
): string | null {
  if (result.success) return null
  return result.error?.issues[0]?.message ?? null
}

const VALID_INPUT = {
  sensor_type: 'light',
  comparison: 'lt',
  threshold: 100,
  cooldown_minutes: 5,
  time_window: null,
} as const

describe('preConditionSchema', () => {
  // ── sensor_type ─────────────────────────────────────────────────────
  describe('sensor_type field', () => {
    it('accepts light', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        sensor_type: 'light',
      })
      expect(result.success).toBe(true)
    })

    it('accepts temperature', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        sensor_type: 'temperature',
      })
      expect(result.success).toBe(true)
    })

    it('rejects motion (not in pre-condition enum)', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        sensor_type: 'motion',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(SCHEDULER.invalidSensorType)
    })

    it('rejects arbitrary string', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        sensor_type: 'humidity',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(SCHEDULER.invalidSensorType)
    })
  })

  // ── comparison ──────────────────────────────────────────────────────
  describe('comparison field', () => {
    it('accepts lt, gt, and eq', () => {
      for (const op of ['lt', 'gt', 'eq']) {
        const result = preConditionSchema.safeParse({
          ...VALID_INPUT,
          comparison: op,
        })
        expect(result.success).toBe(true)
      }
    })

    it('rejects gte', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        comparison: 'gte',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(SCHEDULER.invalidComparison)
    })

    it('rejects lte', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        comparison: 'lte',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(SCHEDULER.invalidComparison)
    })
  })

  // ── threshold ───────────────────────────────────────────────────────
  describe('threshold field', () => {
    it('accepts zero', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        threshold: 0,
      })
      expect(result.success).toBe(true)
    })

    it('accepts positive integer', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        threshold: 500,
      })
      expect(result.success).toBe(true)
    })

    it('accepts decimal value', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        threshold: 25.5,
      })
      expect(result.success).toBe(true)
    })

    it('rejects negative value', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        threshold: -1,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Threshold must be non-negative')
    })

    it('rejects non-number (string)', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        threshold: '100',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(TYPE.number('Threshold'))
    })

    it('rejects NaN', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        threshold: NaN,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(TYPE.number('Threshold'))
    })
  })

  // ── cooldown_minutes ────────────────────────────────────────────────
  describe('cooldown_minutes field', () => {
    it('accepts minimum (1)', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        cooldown_minutes: SCHEDULE_LIMITS.MIN_COOLDOWN_MINUTES,
      })
      expect(result.success).toBe(true)
    })

    it('accepts maximum (60)', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        cooldown_minutes: SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES,
      })
      expect(result.success).toBe(true)
    })

    it('accepts decimal within range', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        cooldown_minutes: 5.5,
      })
      expect(result.success).toBe(true)
    })

    it('rejects zero (below minimum)', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        cooldown_minutes: 0,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(
        RANGE.min(SCHEDULE_LIMITS.MIN_COOLDOWN_MINUTES, 'minutes'),
      )
    })

    it('rejects 61 (above maximum)', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        cooldown_minutes: SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES + 1,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(
        RANGE.max(SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES, 'minutes'),
      )
    })

    it('rejects non-number (string)', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        cooldown_minutes: '5',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(TYPE.number('Cooldown'))
    })

    it('rejects NaN', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        cooldown_minutes: NaN,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(TYPE.number('Cooldown'))
    })
  })

  // ── time_window ─────────────────────────────────────────────────────
  describe('time_window field', () => {
    it('accepts null', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        time_window: null,
      })
      expect(result.success).toBe(true)
    })

    it('defaults to null when omitted', () => {
      const { time_window: _, ...rest } = VALID_INPUT
      const result = preConditionSchema.safeParse(rest)
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.time_window).toBeNull()
      }
    })

    it('accepts valid time window', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        time_window: { start_time: '08:00', end_time: '18:00' },
      })
      expect(result.success).toBe(true)
    })

    it('rejects same start and end times', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        time_window: { start_time: '12:00', end_time: '12:00' },
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(TIME_WINDOW_SAME_ERROR)
    })
  })
})

// ── preConditionTimeWindowSchema (standalone) ─────────────────────────
describe('preConditionTimeWindowSchema', () => {
  it('accepts valid start and end times', () => {
    const result = preConditionTimeWindowSchema.safeParse({
      start_time: '06:00',
      end_time: '22:30',
    })
    expect(result.success).toBe(true)
  })

  it('accepts boundary times (00:00 and 23:59)', () => {
    const result = preConditionTimeWindowSchema.safeParse({
      start_time: '00:00',
      end_time: '23:59',
    })
    expect(result.success).toBe(true)
  })

  it('rejects invalid start_time format', () => {
    const result = preConditionTimeWindowSchema.safeParse({
      start_time: '25:00',
      end_time: '18:00',
    })
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe(FORMAT.timeRequired)
  })

  it('rejects invalid end_time format', () => {
    const result = preConditionTimeWindowSchema.safeParse({
      start_time: '08:00',
      end_time: '12:60',
    })
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe(FORMAT.timeRequired)
  })

  it('rejects empty string for start_time', () => {
    const result = preConditionTimeWindowSchema.safeParse({
      start_time: '',
      end_time: '18:00',
    })
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe(FORMAT.timeRequired)
  })

  it('rejects non-string start_time', () => {
    const result = preConditionTimeWindowSchema.safeParse({
      start_time: 800,
      end_time: '18:00',
    })
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe(REQUIRED.field('Start time'))
  })

  it('rejects same start and end times', () => {
    const result = preConditionTimeWindowSchema.safeParse({
      start_time: '14:00',
      end_time: '14:00',
    })
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe(TIME_WINDOW_SAME_ERROR)
  })

  it('rejects empty object (both fields missing)', () => {
    const result = preConditionTimeWindowSchema.safeParse({})
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe(REQUIRED.field('Start time'))
  })

  it('rejects missing end_time', () => {
    const result = preConditionTimeWindowSchema.safeParse({
      start_time: '06:00',
    })
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe(REQUIRED.field('End time'))
  })
})

// ── Drift guard ──────────────────────────────────────────────────────────
describe('error message consistency', () => {
  it('TIME_WINDOW_SAME_ERROR matches SCHEDULER.sameStartEnd', () => {
    expect(TIME_WINDOW_SAME_ERROR).toBe(SCHEDULER.sameStartEnd)
  })
})

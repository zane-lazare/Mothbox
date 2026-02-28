# PreConditionForm Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate PreConditionForm from manual useState/useEffect validation to react-hook-form + Zod, converting .jsx to .tsx.

**Architecture:** Pattern 2 (Controlled) — parent owns state, component fires `onChange` on validated changes. Internal RHF form provides field-level Zod validation. Toggle is outside the form and sends `null` to parent when disabled. Time window is a nullable nested sub-schema with cross-field `.refine()`.

**Tech Stack:** React 19, react-hook-form, Zod, zodResolver, Vitest, @testing-library/react

---

## Reference Files

Before starting, read these for patterns and context:

- **Migration pattern:** `src/components/scheduler/ScheduleEditor/MoonPhaseTriggerForm.tsx` (ref for useForm, Controller, prop sync, propagation, number input, parent error wiring)
- **Schema pattern:** `src/schemas/scheduler/moon-phase.ts` (ref for schema structure and naming)
- **Schema test pattern:** `src/schemas/scheduler/__tests__/moon-phase.test.ts` (ref for `firstError` helper, test structure)
- **Constants:** `src/components/scheduler/ScheduleEditor/constants.js` (SCHEDULE_LIMITS, SENSOR_TYPES, TIME_FORMAT_REGEX)
- **Error messages:** `src/components/scheduler/ScheduleEditor/errorMessages.js` (NUMERIC_ERRORS, TIME_ERRORS)
- **Original component:** `src/components/scheduler/ScheduleEditor/PreConditionForm.jsx`
- **Original tests:** `src/components/scheduler/ScheduleEditor/__tests__/PreConditionForm.test.jsx`

## Important Conventions

- All commands run from `webui/frontend/`
- Number inputs use: `raw === '' ? NaN : Number(raw)` for onChange, `Number.isNaN(field.value) ? '' : field.value` for display
- zodResolver cast: `zodResolver(schema as unknown as Parameters<typeof zodResolver>[0]) as unknown as Resolver<FormData>`
- Prop sync uses `valueRef`, `onChangeRef`, `lastPropagatedRef` refs
- Propagation effect uses `safeParse()` to gate before calling parent `onChange`
- All existing `data-testid` attributes must be preserved exactly

---

### Task 1: Zod Schema + Schema Tests

**Files:**
- Create: `src/schemas/scheduler/pre-condition.ts`
- Create: `src/schemas/scheduler/__tests__/pre-condition.test.ts`

**Step 1: Write the schema**

Create `src/schemas/scheduler/pre-condition.ts`:

```typescript
import { z } from 'zod'
import {
  SCHEDULE_LIMITS,
  TIME_FORMAT_REGEX,
} from '../../components/scheduler/ScheduleEditor/constants'

/**
 * Schema for the optional time window nested inside a pre-condition.
 * Simple HH:MM-only times (no solar events, no offsets).
 * Cross-field: start_time !== end_time.
 */
export const preConditionTimeWindowSchema = z
  .object({
    start_time: z
      .string({ error: 'Start time is required' })
      .regex(TIME_FORMAT_REGEX, 'Time must be in HH:MM format'),
    end_time: z
      .string({ error: 'End time is required' })
      .regex(TIME_FORMAT_REGEX, 'Time must be in HH:MM format'),
  })
  .refine((data) => data.start_time !== data.end_time, {
    message: 'Start and end times cannot be the same',
    path: ['end_time'],
  })

/**
 * Schema for fields owned by PreConditionForm.
 * The enable/disable toggle is component-level state, not validated here.
 */
export const preConditionSchema = z.object({
  sensor_type: z.enum(['light', 'temperature'], {
    error: 'Invalid sensor type',
  }),
  comparison: z.enum(['lt', 'gt', 'eq'], {
    error: 'Invalid comparison operator',
  }),
  threshold: z
    .number({ error: 'Threshold must be a number' })
    .min(0, 'Threshold must be non-negative'),
  cooldown_minutes: z
    .number({ error: 'Cooldown must be a number' })
    .min(
      SCHEDULE_LIMITS.MIN_COOLDOWN_MINUTES,
      `Cooldown must be at least ${SCHEDULE_LIMITS.MIN_COOLDOWN_MINUTES} minutes`,
    )
    .max(
      SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES,
      `Cooldown cannot exceed ${SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES} minutes`,
    ),
  time_window: preConditionTimeWindowSchema.nullable().default(null),
})

export type PreConditionFormData = z.infer<typeof preConditionSchema>
```

**Step 2: Write the schema tests**

Create `src/schemas/scheduler/__tests__/pre-condition.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import {
  preConditionSchema,
  preConditionTimeWindowSchema,
} from '../pre-condition'
import { SCHEDULE_LIMITS } from '../../../components/scheduler/ScheduleEditor/constants'

/** Return the first Zod issue message from a failed parse, or null. */
function firstError(
  result: { success: boolean; error?: { issues: { message: string }[] } },
): string | null {
  if (result.success) return null
  return result.error?.issues[0]?.message ?? null
}

const VALID_INPUT = {
  sensor_type: 'light' as const,
  comparison: 'lt' as const,
  threshold: 100,
  cooldown_minutes: 5,
  time_window: null,
}

describe('preConditionSchema', () => {
  describe('sensor_type field', () => {
    it('accepts light', () => {
      const result = preConditionSchema.safeParse(VALID_INPUT)
      expect(result.success).toBe(true)
    })

    it('accepts temperature', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        sensor_type: 'temperature',
      })
      expect(result.success).toBe(true)
    })

    it('rejects motion (excluded per issue #325)', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        sensor_type: 'motion',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Invalid sensor type')
    })

    it('rejects invalid string', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        sensor_type: 'humidity',
      })
      expect(result.success).toBe(false)
    })
  })

  describe('comparison field', () => {
    it('accepts lt, gt, eq', () => {
      for (const op of ['lt', 'gt', 'eq']) {
        const result = preConditionSchema.safeParse({
          ...VALID_INPUT,
          comparison: op,
        })
        expect(result.success).toBe(true)
      }
    })

    it('rejects gte (excluded per issue #325)', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        comparison: 'gte',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Invalid comparison operator')
    })

    it('rejects lte (excluded per issue #325)', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        comparison: 'lte',
      })
      expect(result.success).toBe(false)
    })
  })

  describe('threshold field', () => {
    it('accepts zero', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        threshold: 0,
      })
      expect(result.success).toBe(true)
    })

    it('accepts positive integers', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        threshold: 999999,
      })
      expect(result.success).toBe(true)
    })

    it('accepts decimals', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        threshold: 50.5,
      })
      expect(result.success).toBe(true)
    })

    it('rejects negative values', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        threshold: -1,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Threshold must be non-negative')
    })

    it('rejects non-number', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        threshold: 'abc',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Threshold must be a number')
    })

    it('rejects NaN', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        threshold: NaN,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Threshold must be a number')
    })
  })

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

    it('accepts decimals within range', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        cooldown_minutes: 5.5,
      })
      expect(result.success).toBe(true)
    })

    it('rejects below minimum', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        cooldown_minutes: 0,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(
        `Cooldown must be at least ${SCHEDULE_LIMITS.MIN_COOLDOWN_MINUTES} minutes`,
      )
    })

    it('rejects above maximum', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        cooldown_minutes: 61,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(
        `Cooldown cannot exceed ${SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES} minutes`,
      )
    })

    it('rejects non-number', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        cooldown_minutes: 'abc',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Cooldown must be a number')
    })

    it('rejects NaN', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        cooldown_minutes: NaN,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Cooldown must be a number')
    })
  })

  describe('time_window field', () => {
    it('accepts null (time window disabled)', () => {
      const result = preConditionSchema.safeParse(VALID_INPUT)
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
        time_window: { start_time: '21:00', end_time: '06:00' },
      })
      expect(result.success).toBe(true)
    })

    it('rejects same start and end time', () => {
      const result = preConditionSchema.safeParse({
        ...VALID_INPUT,
        time_window: { start_time: '21:00', end_time: '21:00' },
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(
        'Start and end times cannot be the same',
      )
    })
  })
})

describe('preConditionTimeWindowSchema', () => {
  it('accepts valid times', () => {
    const result = preConditionTimeWindowSchema.safeParse({
      start_time: '21:00',
      end_time: '06:00',
    })
    expect(result.success).toBe(true)
  })

  it('rejects invalid start_time format', () => {
    const result = preConditionTimeWindowSchema.safeParse({
      start_time: '25:00',
      end_time: '06:00',
    })
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe('Time must be in HH:MM format')
  })

  it('rejects invalid end_time format', () => {
    const result = preConditionTimeWindowSchema.safeParse({
      start_time: '21:00',
      end_time: 'bad',
    })
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe('Time must be in HH:MM format')
  })

  it('rejects empty strings', () => {
    const result = preConditionTimeWindowSchema.safeParse({
      start_time: '',
      end_time: '',
    })
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe('Time must be in HH:MM format')
  })

  it('rejects same start and end', () => {
    const result = preConditionTimeWindowSchema.safeParse({
      start_time: '12:00',
      end_time: '12:00',
    })
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe(
      'Start and end times cannot be the same',
    )
  })
})
```

**Step 3: Run schema tests to verify they pass**

Run: `cd webui/frontend && npx vitest run src/schemas/scheduler/__tests__/pre-condition.test.ts`
Expected: All tests PASS (~25 tests)

**Step 4: Commit**

```bash
git add src/schemas/scheduler/pre-condition.ts src/schemas/scheduler/__tests__/pre-condition.test.ts
git commit -m "feat(#450): add Zod schema and tests for PreConditionForm"
```

---

### Task 2: Component Migration (.jsx → .tsx)

**Files:**
- Create: `src/components/scheduler/ScheduleEditor/PreConditionForm.tsx`
- Delete: `src/components/scheduler/ScheduleEditor/PreConditionForm.jsx`

**Context:** The component has a unique pattern among our migrations: an enable/disable toggle that sends `null` to the parent. The toggle stays outside RHF — it's component-level state derived from the `preCondition` prop. When enabled, the RHF form manages the fields. When the toggle turns off, it calls `onChange(null)` directly. The time window nested toggle also bypasses RHF (like preset buttons in MoonPhaseTriggerForm).

**Step 1: Create the .tsx component**

Create `src/components/scheduler/ScheduleEditor/PreConditionForm.tsx`:

```typescript
import { useEffect, useRef } from 'react'
import { useForm, Controller, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import type { Resolver } from 'react-hook-form'
import {
  preConditionSchema,
  type PreConditionFormData,
} from '../../../schemas/scheduler/pre-condition'
import { SENSOR_TYPES, SCHEDULE_LIMITS } from './constants'

// ── Types ──────────────────────────────────────────────────────────────

export interface PreConditionValue {
  trigger_type?: string
  sensor_type: string
  comparison: string
  threshold: number
  cooldown_minutes: number
  time_window?: {
    start_time: string
    end_time: string
  } | null
}

interface PreConditionFormProps {
  preCondition: PreConditionValue | null
  onChange: (value: PreConditionValue | null) => void
  routineIndex: number
  disabled?: boolean
  errors?: Record<string, string>
}

// ── Constants ──────────────────────────────────────────────────────────

const DEFAULT_PRE_CONDITION: PreConditionValue = {
  trigger_type: 'sensor',
  sensor_type: 'light',
  comparison: 'lt',
  threshold: 100,
  cooldown_minutes: 5,
}

/** Unit labels for sensor types */
const SENSOR_UNITS: Record<string, string> = {
  light: 'lux',
  temperature: '°C',
}

// ── Resolver cast (Zod 4 + @hookform/resolvers workaround) ────────────

const resolver = zodResolver(
  preConditionSchema as unknown as Parameters<typeof zodResolver>[0],
) as unknown as Resolver<PreConditionFormData>

// ── Component ──────────────────────────────────────────────────────────

export default function PreConditionForm({
  preCondition,
  onChange,
  routineIndex,
  disabled = false,
  errors: parentErrors = {},
}: PreConditionFormProps) {
  const enabled = !!preCondition

  // Stable callback ref
  const onChangeRef = useRef(onChange)
  onChangeRef.current = onChange

  // Stable ref for current prop value
  const valueRef = useRef(preCondition)
  valueRef.current = preCondition

  // Track last propagated values to avoid cycles
  const lastPropagatedRef = useRef<PreConditionFormData | null>(
    preCondition
      ? {
          sensor_type: preCondition.sensor_type as PreConditionFormData['sensor_type'],
          comparison: preCondition.comparison as PreConditionFormData['comparison'],
          threshold: preCondition.threshold,
          cooldown_minutes: preCondition.cooldown_minutes,
          time_window: preCondition.time_window ?? null,
        }
      : null,
  )

  const {
    control,
    reset,
    formState: { errors },
  } = useForm<PreConditionFormData>({
    resolver,
    defaultValues: preCondition
      ? {
          sensor_type: preCondition.sensor_type as PreConditionFormData['sensor_type'],
          comparison: preCondition.comparison as PreConditionFormData['comparison'],
          threshold: preCondition.threshold,
          cooldown_minutes: preCondition.cooldown_minutes,
          time_window: preCondition.time_window ?? null,
        }
      : {
          sensor_type: 'light',
          comparison: 'lt',
          threshold: 100,
          cooldown_minutes: 5,
          time_window: null,
        },
    mode: 'onChange',
  })

  // Prop sync: reset form when preCondition changes externally
  useEffect(() => {
    if (!preCondition) return
    const last = lastPropagatedRef.current
    if (
      !last ||
      preCondition.sensor_type !== last.sensor_type ||
      preCondition.comparison !== last.comparison ||
      preCondition.threshold !== last.threshold ||
      preCondition.cooldown_minutes !== last.cooldown_minutes ||
      JSON.stringify(preCondition.time_window ?? null) !==
        JSON.stringify(last.time_window)
    ) {
      const formData: PreConditionFormData = {
        sensor_type: preCondition.sensor_type as PreConditionFormData['sensor_type'],
        comparison: preCondition.comparison as PreConditionFormData['comparison'],
        threshold: preCondition.threshold,
        cooldown_minutes: preCondition.cooldown_minutes,
        time_window: preCondition.time_window ?? null,
      }
      lastPropagatedRef.current = formData
      reset(formData)
    }
  }, [
    preCondition?.sensor_type,
    preCondition?.comparison,
    preCondition?.threshold,
    preCondition?.cooldown_minutes,
    // eslint-disable-next-line react-hooks/exhaustive-deps
    JSON.stringify(preCondition?.time_window ?? null),
    reset,
  ])

  // Propagate validated form changes → parent
  const watchedSensorType = useWatch({ control, name: 'sensor_type' })
  const watchedComparison = useWatch({ control, name: 'comparison' })
  const watchedThreshold = useWatch({ control, name: 'threshold' })
  const watchedCooldown = useWatch({ control, name: 'cooldown_minutes' })
  const watchedTimeWindow = useWatch({ control, name: 'time_window' })

  useEffect(() => {
    if (
      watchedSensorType === undefined ||
      watchedComparison === undefined ||
      watchedThreshold === undefined ||
      watchedCooldown === undefined
    )
      return

    // Skip if parent is null (toggled off)
    if (!valueRef.current) return

    // Build candidate
    const candidate: PreConditionFormData = {
      sensor_type: watchedSensorType,
      comparison: watchedComparison,
      threshold: watchedThreshold,
      cooldown_minutes: watchedCooldown,
      time_window: watchedTimeWindow ?? null,
    }

    // Skip if values match current prop (avoids cycle)
    const current = valueRef.current
    if (
      watchedSensorType === current.sensor_type &&
      watchedComparison === current.comparison &&
      watchedThreshold === current.threshold &&
      watchedCooldown === current.cooldown_minutes &&
      JSON.stringify(candidate.time_window) ===
        JSON.stringify(current.time_window ?? null)
    )
      return

    // Only propagate valid values
    const result = preConditionSchema.safeParse(candidate)
    if (!result.success) return

    lastPropagatedRef.current = candidate
    onChangeRef.current({
      ...current,
      ...candidate,
    })
  }, [watchedSensorType, watchedComparison, watchedThreshold, watchedCooldown, watchedTimeWindow])

  // ── Toggle handlers (bypass RHF) ──────────────────────────────────

  const handleToggle = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      const defaults = { ...DEFAULT_PRE_CONDITION }
      onChangeRef.current(defaults)
    } else {
      onChangeRef.current(null)
    }
  }

  const handleTimeWindowToggle = (e: React.ChangeEvent<HTMLInputElement>) => {
    const current = valueRef.current
    if (!current) return
    if (e.target.checked) {
      onChangeRef.current({
        ...current,
        time_window: { start_time: '21:00', end_time: '06:00' },
      })
    } else {
      onChangeRef.current({
        ...current,
        time_window: null,
      })
    }
  }

  // ── Derived state ─────────────────────────────────────────────────

  // Cross-field time window error (computed from watched values)
  const timeWindowError =
    watchedTimeWindow?.start_time &&
    watchedTimeWindow?.end_time &&
    watchedTimeWindow.start_time === watchedTimeWindow.end_time
      ? 'Start and end times cannot be the same'
      : null

  return (
    <div className="space-y-3">
      {/* Toggle */}
      <div className="flex items-center gap-3 text-sm">
        <input
          type="checkbox"
          id={`pre-condition-toggle-${routineIndex}`}
          checked={enabled}
          onChange={handleToggle}
          disabled={disabled}
          className="rounded border-gray-600 disabled:opacity-50"
          data-testid={`pre-condition-toggle-${routineIndex}`}
        />
        <label
          htmlFor={`pre-condition-toggle-${routineIndex}`}
          className="text-gray-400 cursor-pointer"
        >
          Only run if sensor condition met
        </label>
      </div>

      {/* Conditional fields */}
      {enabled && preCondition && (
        <div className="pl-6 space-y-3">
          <div className="flex items-center gap-3 text-sm flex-wrap">
            {/* Sensor type */}
            <Controller
              name="sensor_type"
              control={control}
              render={({ field }) => (
                <select
                  value={field.value}
                  onChange={(e) => field.onChange(e.target.value)}
                  onBlur={field.onBlur}
                  ref={field.ref}
                  disabled={disabled}
                  aria-label="Sensor type"
                  aria-invalid={!!(errors.sensor_type || parentErrors.sensor_type)}
                  aria-describedby={
                    (errors.sensor_type || parentErrors.sensor_type)
                      ? 'sensor_type-error'
                      : undefined
                  }
                  className="rounded-md border border-gray-300 dark:border-gray-600
                             bg-white dark:bg-gray-800 px-2 py-1 text-gray-900 dark:text-white
                             focus:ring-2 focus:ring-blue-500 focus:border-transparent
                             disabled:opacity-50 disabled:cursor-not-allowed"
                  data-testid="pre-condition-sensor"
                >
                  {SENSOR_TYPES.filter((s: { value: string }) => s.value !== 'motion').map(
                    (sensor: { value: string; label: string }) => (
                      <option key={sensor.value} value={sensor.value}>
                        {sensor.label}
                      </option>
                    ),
                  )}
                </select>
              )}
            />

            {/* Comparison operator */}
            <Controller
              name="comparison"
              control={control}
              render={({ field }) => (
                <select
                  value={field.value}
                  onChange={(e) => field.onChange(e.target.value)}
                  onBlur={field.onBlur}
                  ref={field.ref}
                  disabled={disabled}
                  aria-label="Comparison operator"
                  aria-invalid={!!(errors.comparison || parentErrors.comparison)}
                  aria-describedby={
                    (errors.comparison || parentErrors.comparison)
                      ? 'comparison-error'
                      : undefined
                  }
                  className="rounded-md border border-gray-300 dark:border-gray-600
                             bg-white dark:bg-gray-800 px-2 py-1 text-gray-900 dark:text-white
                             focus:ring-2 focus:ring-blue-500 focus:border-transparent
                             disabled:opacity-50 disabled:cursor-not-allowed"
                  data-testid="pre-condition-op"
                >
                  <option value="lt">is below</option>
                  <option value="gt">is above</option>
                  <option value="eq">equals</option>
                </select>
              )}
            />

            {/* Threshold */}
            <Controller
              name="threshold"
              control={control}
              render={({ field }) => (
                <input
                  type="number"
                  min={0}
                  value={Number.isNaN(field.value) ? '' : field.value}
                  onChange={(e) => {
                    const raw = e.target.value
                    field.onChange(raw === '' ? NaN : Number(raw))
                  }}
                  onBlur={field.onBlur}
                  ref={field.ref}
                  disabled={disabled}
                  aria-label="Threshold value"
                  aria-invalid={!!(errors.threshold || parentErrors.threshold)}
                  aria-describedby={
                    (errors.threshold || parentErrors.threshold)
                      ? 'threshold-error'
                      : undefined
                  }
                  className="w-20 rounded-md border border-gray-300 dark:border-gray-600
                             bg-white dark:bg-gray-800 px-2 py-1 text-gray-900 dark:text-white text-center
                             focus:ring-2 focus:ring-blue-500 focus:border-transparent
                             disabled:opacity-50 disabled:cursor-not-allowed"
                  data-testid="pre-condition-threshold"
                />
              )}
            />
            <span
              className="text-xs text-gray-500 dark:text-gray-400"
              data-testid="pre-condition-unit"
            >
              {SENSOR_UNITS[watchedSensorType] || ''}
            </span>
          </div>

          {/* Threshold validation error */}
          {(errors.threshold?.message || parentErrors.threshold) && (
            <p
              id="threshold-error"
              role="alert"
              className="text-sm text-red-600 dark:text-red-400"
              data-testid="pre-condition-error"
            >
              {errors.threshold?.message || parentErrors.threshold}
            </p>
          )}

          {/* Cooldown */}
          <div className="flex items-center gap-2 text-sm">
            <span className="text-gray-400">Cooldown:</span>
            <Controller
              name="cooldown_minutes"
              control={control}
              render={({ field }) => (
                <input
                  type="number"
                  min={SCHEDULE_LIMITS.MIN_COOLDOWN_MINUTES}
                  max={SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES}
                  value={Number.isNaN(field.value) ? '' : field.value}
                  onChange={(e) => {
                    const raw = e.target.value
                    field.onChange(raw === '' ? NaN : Number(raw))
                  }}
                  onBlur={field.onBlur}
                  ref={field.ref}
                  disabled={disabled}
                  aria-label="Cooldown minutes"
                  aria-invalid={
                    !!(errors.cooldown_minutes || parentErrors.cooldown_minutes)
                  }
                  aria-describedby={
                    (errors.cooldown_minutes || parentErrors.cooldown_minutes)
                      ? 'cooldown-error'
                      : undefined
                  }
                  className="w-16 rounded-md border border-gray-300 dark:border-gray-600
                             bg-white dark:bg-gray-800 px-2 py-1 text-gray-900 dark:text-white text-center
                             focus:ring-2 focus:ring-blue-500 focus:border-transparent
                             disabled:opacity-50 disabled:cursor-not-allowed"
                  data-testid="pre-condition-cooldown"
                />
              )}
            />
            <span className="text-xs text-gray-500 dark:text-gray-400">
              minutes
            </span>
          </div>
          {(errors.cooldown_minutes?.message ||
            parentErrors.cooldown_minutes) && (
            <p
              id="cooldown-error"
              role="alert"
              className="text-sm text-red-600 dark:text-red-400"
              data-testid="pre-condition-cooldown-error"
            >
              {errors.cooldown_minutes?.message ||
                parentErrors.cooldown_minutes}
            </p>
          )}

          {/* Time window toggle */}
          <div className="flex items-center gap-3 text-sm">
            <input
              type="checkbox"
              id={`pre-condition-tw-toggle-${routineIndex}`}
              checked={!!preCondition?.time_window}
              onChange={handleTimeWindowToggle}
              disabled={disabled}
              className="rounded border-gray-600 disabled:opacity-50"
              data-testid="pre-condition-time-window-toggle"
            />
            <label
              htmlFor={`pre-condition-tw-toggle-${routineIndex}`}
              className="text-gray-400 cursor-pointer"
            >
              Restrict to time window
            </label>
          </div>

          {/* Time window fields */}
          {preCondition?.time_window && (
            <div className="pl-6 flex items-center gap-2 text-sm">
              <Controller
                name="time_window.start_time"
                control={control}
                render={({ field }) => (
                  <input
                    type="time"
                    value={field.value || '21:00'}
                    onChange={(e) => field.onChange(e.target.value)}
                    onBlur={field.onBlur}
                    ref={field.ref}
                    disabled={disabled}
                    aria-label="Time window start"
                    className="rounded-md border border-gray-300 dark:border-gray-600
                               bg-white dark:bg-gray-800 px-2 py-1 text-gray-900 dark:text-white
                               focus:ring-2 focus:ring-blue-500 focus:border-transparent
                               disabled:opacity-50 disabled:cursor-not-allowed"
                    data-testid="pre-condition-tw-start"
                  />
                )}
              />
              <span className="text-gray-400">to</span>
              <Controller
                name="time_window.end_time"
                control={control}
                render={({ field }) => (
                  <input
                    type="time"
                    value={field.value || '06:00'}
                    onChange={(e) => field.onChange(e.target.value)}
                    onBlur={field.onBlur}
                    ref={field.ref}
                    disabled={disabled}
                    aria-label="Time window end"
                    className="rounded-md border border-gray-300 dark:border-gray-600
                               bg-white dark:bg-gray-800 px-2 py-1 text-gray-900 dark:text-white
                               focus:ring-2 focus:ring-blue-500 focus:border-transparent
                               disabled:opacity-50 disabled:cursor-not-allowed"
                    data-testid="pre-condition-tw-end"
                  />
                )}
              />
            </div>
          )}
          {/* Time window validation error */}
          {timeWindowError && (
            <p
              className="pl-6 text-sm text-red-600 dark:text-red-400"
              data-testid="pre-condition-tw-error"
            >
              {timeWindowError}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
```

**Step 2: Delete the .jsx file**

```bash
rm src/components/scheduler/ScheduleEditor/PreConditionForm.jsx
```

**Step 3: Verify TypeScript compiles**

Run: `cd webui/frontend && npx tsc --noEmit`
Expected: No errors (the barrel export in `index.js` will resolve `.tsx` automatically)

**Step 4: Run existing tests to check basic compatibility**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ScheduleEditor/__tests__/PreConditionForm`
Expected: Some tests may fail due to async RHF propagation (will be fixed in Task 3). Note which tests fail.

**Step 5: Commit**

```bash
git add -A src/components/scheduler/ScheduleEditor/PreConditionForm.tsx
git add -A src/components/scheduler/ScheduleEditor/PreConditionForm.jsx
git commit -m "feat(#450): migrate PreConditionForm to TypeScript with RHF + Zod"
```

---

### Task 3: Test Migration (.test.jsx → .test.tsx)

**Files:**
- Create: `src/components/scheduler/ScheduleEditor/__tests__/PreConditionForm.test.tsx`
- Delete: `src/components/scheduler/ScheduleEditor/__tests__/PreConditionForm.test.jsx`

**Context:** The original tests use `fireEvent.change` with direct `mockOnChange` assertions. With RHF, validation is async — `onChange` propagation happens after `safeParse()` succeeds in a `useEffect`. Tests need `waitFor()` wrappers around `onChange` assertions. Also, the toggle bypasses RHF and calls onChange synchronously — those tests don't need `waitFor`.

Key changes from original tests:
1. Import `waitFor` from `@testing-library/react`
2. Wrap `onChange` assertions for field changes in `waitFor()` (RHF is async)
3. Toggle on/off assertions stay synchronous (bypass RHF)
4. Time window toggle assertions stay synchronous (bypass RHF)
5. Validation error assertions use `waitFor()` since RHF validates async
6. Add `props()` factory function pattern (consistent with TimeWindowInput tests)
7. Add ~4 new tests: parent error wiring (threshold, cooldown, general), prop sync

**Step 1: Create the migrated test file**

Create `src/components/scheduler/ScheduleEditor/__tests__/PreConditionForm.test.tsx`. Migrate all 60+ existing tests, adapting for async RHF behavior. Key patterns:

- **Toggle on/off tests**: Keep synchronous — toggle handlers call `onChangeRef.current()` directly
- **Field change tests** (sensor_type, comparison, threshold, cooldown): Wrap `expect(mockOnChange).toHaveBeenCalledWith(...)` in `await waitFor(() => { ... })`
- **Validation error tests**: Use `await waitFor(() => { expect(screen.getByTestId('pre-condition-error')).toBeInTheDocument() })`
- **Time window toggle/changes**: Time window toggle is synchronous (bypasses RHF). Time input changes need `waitFor()`.
- **New tests**: Parent error wiring for threshold, cooldown, and general errors + prop sync

The test file should follow the `props()` factory function pattern:

```typescript
function props(overrides: Partial<Parameters<typeof PreConditionForm>[0]> = {}) {
  return {
    preCondition: null as PreConditionValue | null,
    onChange: vi.fn(),
    routineIndex: 0,
    ...overrides,
  }
}
```

**Step 2: Delete the .test.jsx file**

```bash
rm src/components/scheduler/ScheduleEditor/__tests__/PreConditionForm.test.jsx
```

**Step 3: Run migrated tests**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ScheduleEditor/__tests__/PreConditionForm.test.tsx`
Expected: All tests pass (60+ migrated + ~4 new)

**Step 4: Commit**

```bash
git add -A src/components/scheduler/ScheduleEditor/__tests__/PreConditionForm.test.tsx
git add -A src/components/scheduler/ScheduleEditor/__tests__/PreConditionForm.test.jsx
git commit -m "test(#450): migrate PreConditionForm tests to TypeScript"
```

---

### Task 4: Verification & Consumer Compatibility

**Files:**
- Possibly modify: `src/components/scheduler/ScheduleEditor/__tests__/RoutineCard.test.jsx` (if it references PreConditionForm)
- Possibly modify: `src/components/scheduler/ScheduleEditor/__tests__/NewRoutineCard.test.jsx`

**Step 1: Run full scheduler test suite**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/`
Expected: All tests pass. If consumer tests fail (RoutineCard, NewRoutineCard), fix them by adding `waitFor()` wrappers where needed.

**Step 2: TypeScript check**

Run: `cd webui/frontend && npx tsc --noEmit`
Expected: Clean, no errors

**Step 3: ESLint check**

Run: `cd webui/frontend && npx eslint src/components/scheduler/ScheduleEditor/PreConditionForm.tsx src/schemas/scheduler/pre-condition.ts`
Expected: Clean, no errors

**Step 4: Fix any consumer test failures**

If RoutineCard or NewRoutineCard tests fail due to async RHF propagation in PreConditionForm, add `waitFor()` wrappers and `start_offset_minutes`/`end_offset_minutes` fields if needed.

**Step 5: Commit fixes if any**

```bash
git add -A
git commit -m "fix(#450): fix consumer test compatibility for PreConditionForm migration"
```

**Step 6: Run full frontend test suite**

Run: `cd webui/frontend && npx vitest run`
Expected: All tests pass (1600+ tests, 0 failures)

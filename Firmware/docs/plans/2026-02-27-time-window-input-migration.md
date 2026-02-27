# TimeWindowInput Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate `TimeWindowInput.jsx` → TypeScript with react-hook-form + Zod validation, following the Controlled (Pattern 2) migration pattern.

**Architecture:** Internal RHF form owns local validation via `timeWindowSchema`. Parent passes `value`/`onChange`. Cycle prevention via `valueRef`/`onChangeRef`/`lastPropagatedRef` refs. Mode (fixed vs solar) derived from watched field values — no `useState`.

**Tech Stack:** React 19, react-hook-form, Zod 4, zodResolver, TypeScript, Vitest, Testing Library

**Design doc:** `docs/plans/2026-02-27-time-window-input-migration-design.md`

---

### Task 1: Create time-window schema and tests

**Files:**
- Create: `webui/frontend/src/schemas/scheduler/time-window.ts`
- Create: `webui/frontend/src/schemas/scheduler/__tests__/time-window.test.ts`

**Context:** This schema validates 4 fields: `start_time` (string — HH:MM or solar event), `end_time` (same), `start_offset_minutes` (integer ±120), `end_offset_minutes` (same). No cross-field `.refine()` — each field validated independently.

**Reference:** `webui/frontend/src/schemas/scheduler/moon-phase.ts` and `webui/frontend/src/schemas/scheduler/__tests__/moon-phase.test.ts` for the established patterns.

**Step 1: Write the failing schema tests**

Create `webui/frontend/src/schemas/scheduler/__tests__/time-window.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { timeWindowSchema } from '../time-window'
import {
  SOLAR_EVENTS,
} from '../../../components/scheduler/ScheduleEditor/constants'

/** Return the first Zod issue message from a failed parse, or null. */
function firstError(
  result: { success: boolean; error?: { issues: { message: string }[] } },
): string | null {
  if (result.success) return null
  return result.error?.issues[0]?.message ?? null
}

const VALID_FIXED: {
  start_time: string
  end_time: string
  start_offset_minutes: number
  end_offset_minutes: number
} = {
  start_time: '21:00',
  end_time: '05:00',
  start_offset_minutes: 0,
  end_offset_minutes: 0,
}

const VALID_SOLAR: typeof VALID_FIXED = {
  start_time: 'sunset',
  end_time: 'sunrise',
  start_offset_minutes: 30,
  end_offset_minutes: -30,
}

describe('timeWindowSchema', () => {
  describe('start_time / end_time — valid values', () => {
    it('accepts valid HH:MM fixed times', () => {
      for (const time of ['00:00', '12:30', '23:59', '09:05']) {
        const result = timeWindowSchema.safeParse({
          ...VALID_FIXED,
          start_time: time,
        })
        expect(result.success).toBe(true)
      }
    })

    it('accepts all valid solar events for start_time', () => {
      for (const event of SOLAR_EVENTS) {
        const result = timeWindowSchema.safeParse({
          ...VALID_FIXED,
          start_time: event.value,
        })
        expect(result.success).toBe(true)
      }
    })

    it('accepts all valid solar events for end_time', () => {
      for (const event of SOLAR_EVENTS) {
        const result = timeWindowSchema.safeParse({
          ...VALID_FIXED,
          end_time: event.value,
        })
        expect(result.success).toBe(true)
      }
    })

    it('accepts mixed fixed + solar', () => {
      const result = timeWindowSchema.safeParse({
        start_time: '21:00',
        end_time: 'sunrise',
        start_offset_minutes: 0,
        end_offset_minutes: -30,
      })
      expect(result.success).toBe(true)
    })
  })

  describe('start_time / end_time — invalid values', () => {
    it('rejects empty string', () => {
      const result = timeWindowSchema.safeParse({
        ...VALID_FIXED,
        start_time: '',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(
        'Must be valid HH:MM time or solar event',
      )
    })

    it('rejects invalid time format (25:00)', () => {
      const result = timeWindowSchema.safeParse({
        ...VALID_FIXED,
        start_time: '25:00',
      })
      expect(result.success).toBe(false)
    })

    it('rejects invalid time format (1:30)', () => {
      const result = timeWindowSchema.safeParse({
        ...VALID_FIXED,
        end_time: '1:30',
      })
      expect(result.success).toBe(false)
    })

    it('rejects arbitrary string', () => {
      const result = timeWindowSchema.safeParse({
        ...VALID_FIXED,
        start_time: 'not_a_solar_event',
      })
      expect(result.success).toBe(false)
    })

    it('rejects non-string type', () => {
      const result = timeWindowSchema.safeParse({
        ...VALID_FIXED,
        start_time: 123,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Time is required')
    })

    it('rejects undefined start_time', () => {
      const { start_time: _, ...rest } = VALID_FIXED
      const result = timeWindowSchema.safeParse(rest)
      expect(result.success).toBe(false)
    })

    it('rejects undefined end_time', () => {
      const { end_time: _, ...rest } = VALID_FIXED
      const result = timeWindowSchema.safeParse(rest)
      expect(result.success).toBe(false)
    })
  })

  describe('offset fields — valid values', () => {
    it('accepts zero offsets', () => {
      const result = timeWindowSchema.safeParse(VALID_FIXED)
      expect(result.success).toBe(true)
    })

    it('accepts positive offset within range', () => {
      const result = timeWindowSchema.safeParse({
        ...VALID_SOLAR,
        start_offset_minutes: 120,
      })
      expect(result.success).toBe(true)
    })

    it('accepts negative offset within range', () => {
      const result = timeWindowSchema.safeParse({
        ...VALID_SOLAR,
        end_offset_minutes: -120,
      })
      expect(result.success).toBe(true)
    })

    it('defaults offset to 0 when omitted', () => {
      const result = timeWindowSchema.safeParse({
        start_time: '21:00',
        end_time: '05:00',
      })
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.start_offset_minutes).toBe(0)
        expect(result.data.end_offset_minutes).toBe(0)
      }
    })
  })

  describe('offset fields — boundary rejection', () => {
    it('rejects start_offset_minutes above 120', () => {
      const result = timeWindowSchema.safeParse({
        ...VALID_SOLAR,
        start_offset_minutes: 121,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Offset cannot exceed 120 minutes')
    })

    it('rejects start_offset_minutes below -120', () => {
      const result = timeWindowSchema.safeParse({
        ...VALID_SOLAR,
        start_offset_minutes: -121,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Offset must be at least -120 minutes')
    })

    it('rejects end_offset_minutes above 120', () => {
      const result = timeWindowSchema.safeParse({
        ...VALID_SOLAR,
        end_offset_minutes: 121,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Offset cannot exceed 120 minutes')
    })

    it('rejects end_offset_minutes below -120', () => {
      const result = timeWindowSchema.safeParse({
        ...VALID_SOLAR,
        end_offset_minutes: -121,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Offset must be at least -120 minutes')
    })
  })

  describe('offset fields — type rejection', () => {
    it('rejects float values', () => {
      const result = timeWindowSchema.safeParse({
        ...VALID_SOLAR,
        start_offset_minutes: 2.5,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Offset must be a whole number')
    })

    it('rejects string values', () => {
      const result = timeWindowSchema.safeParse({
        ...VALID_SOLAR,
        start_offset_minutes: '30',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Offset must be a number')
    })

    it('rejects NaN', () => {
      const result = timeWindowSchema.safeParse({
        ...VALID_SOLAR,
        end_offset_minutes: NaN,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Offset must be a number')
    })
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd webui/frontend && npx vitest run src/schemas/scheduler/__tests__/time-window.test.ts`
Expected: FAIL — `time-window.ts` does not exist yet.

**Step 3: Write the schema**

Create `webui/frontend/src/schemas/scheduler/time-window.ts`:

```typescript
import { z } from 'zod'
import {
  SOLAR_EVENTS,
  TIME_FORMAT_REGEX,
} from '../../components/scheduler/ScheduleEditor/constants'

/**
 * Schema for fields owned by TimeWindowInput:
 * start_time + end_time + start_offset_minutes + end_offset_minutes.
 *
 * Each time field accepts either HH:MM format or a valid solar event string.
 * No cross-field validation — mixed time warning is UI-only.
 */

const TIME_WINDOW_MAX_OFFSET_MINUTES = 120

const solarEventValues = SOLAR_EVENTS.map((e) => e.value) as [
  string,
  ...string[],
]

const timeValue = z
  .string({ error: 'Time is required' })
  .refine(
    (v) => TIME_FORMAT_REGEX.test(v) || solarEventValues.includes(v),
    'Must be valid HH:MM time or solar event',
  )

export const timeWindowSchema = z.object({
  start_time: timeValue,
  end_time: timeValue,
  start_offset_minutes: z
    .number({ error: 'Offset must be a number' })
    .int('Offset must be a whole number')
    .min(
      -TIME_WINDOW_MAX_OFFSET_MINUTES,
      `Offset must be at least ${-TIME_WINDOW_MAX_OFFSET_MINUTES} minutes`,
    )
    .max(
      TIME_WINDOW_MAX_OFFSET_MINUTES,
      `Offset cannot exceed ${TIME_WINDOW_MAX_OFFSET_MINUTES} minutes`,
    )
    .default(0),
  end_offset_minutes: z
    .number({ error: 'Offset must be a number' })
    .int('Offset must be a whole number')
    .min(
      -TIME_WINDOW_MAX_OFFSET_MINUTES,
      `Offset must be at least ${-TIME_WINDOW_MAX_OFFSET_MINUTES} minutes`,
    )
    .max(
      TIME_WINDOW_MAX_OFFSET_MINUTES,
      `Offset cannot exceed ${TIME_WINDOW_MAX_OFFSET_MINUTES} minutes`,
    )
    .default(0),
})

export type TimeWindowFormData = z.infer<typeof timeWindowSchema>
```

**Step 4: Run tests to verify they pass**

Run: `cd webui/frontend && npx vitest run src/schemas/scheduler/__tests__/time-window.test.ts`
Expected: All tests PASS.

**Step 5: Commit**

```bash
git add webui/frontend/src/schemas/scheduler/time-window.ts \
       webui/frontend/src/schemas/scheduler/__tests__/time-window.test.ts
git commit -m "feat(#449): add time-window Zod schema with tests"
```

---

### Task 2: Migrate TimeWindowInput component (JSX → TSX)

**Files:**
- Create: `webui/frontend/src/components/scheduler/ScheduleEditor/TimeWindowInput.tsx`
- Reference: `webui/frontend/src/components/scheduler/ScheduleEditor/TimeWindowInput.jsx` (original)
- Reference: `webui/frontend/src/components/scheduler/ScheduleEditor/MoonPhaseTriggerForm.tsx` (pattern template)

**Context:** TimeWindowInput is a controlled component (Pattern 2) used as a sub-component by IntervalTriggerForm. It has 4 form fields, dual-mode rendering (fixed time vs solar event per endpoint), and mode switching via radio buttons. The mode is **derived** from `watch('start_time')` / `watch('end_time')` — NOT stored as form fields.

**Key behavioral differences from MoonPhaseTriggerForm:**
1. Two time fields with mode-dependent rendering (time input OR select+offset)
2. Radio buttons for mode switching — bypass form (like presets), call `onChangeRef.current()` directly
3. `showSolarEvents` prop controls radio toggle visibility
4. Solar preview text per endpoint
5. Mixed time warning (UI-only, computed from derived mode)
6. Console.warn for invalid solar event values
7. `data-testid` attributes on time inputs
8. `errors` prop has `start_time`, `end_time`, `general` keys (not field-level like MoonPhase)
9. No header element — this is a sub-component, not a top-level form

**Mode derivation logic:**
```typescript
// Empty string → fixed mode (matches original useState(true) default)
// HH:MM format → fixed mode
// Solar event string → solar mode
const startIsFixedTime = !startTime || TIME_FORMAT_REGEX.test(startTime)
const endIsFixedTime = !endTime || TIME_FORMAT_REGEX.test(endTime)
```

**Mode switching handler pattern (bypass form, like presets):**
```typescript
const handleStartTypeChange = (isFixed: boolean) => {
  const newValue = {
    ...valueRef.current,
    start_time: isFixed ? '' : SOLAR_EVENTS[0].value,
    start_offset_minutes: 0,
  }
  lastPropagatedRef.current = newValue
  onChangeRef.current(newValue)
}
```

Note: We update `lastPropagatedRef` immediately to prevent the prop-sync effect from detecting a "change" when the parent passes the same values back.

**Step 1: Create the TSX component**

Create `webui/frontend/src/components/scheduler/ScheduleEditor/TimeWindowInput.tsx` with the following structure (adapt from the original JSX + MoonPhaseTriggerForm pattern):

```typescript
import { useEffect, useRef } from 'react'
import { useForm, Controller, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import type { Resolver } from 'react-hook-form'
import {
  timeWindowSchema,
  type TimeWindowFormData,
} from '../../../schemas/scheduler/time-window'
import { SOLAR_EVENTS, TIME_FORMAT_REGEX, isValidSolarEvent } from './constants'

// ── Types ──────────────────────────────────────────────────────────────

export interface TimeWindowValue {
  start_time: string
  end_time: string
  start_offset_minutes: number
  end_offset_minutes: number
}

interface TimeWindowInputProps {
  value?: TimeWindowValue
  onChange: (value: TimeWindowValue) => void
  disabled?: boolean
  showSolarEvents?: boolean
  errors?: Record<string, string>
}

// ── Constants ──────────────────────────────────────────────────────────

const DEFAULT_VALUE: TimeWindowValue = {
  start_time: '',
  end_time: '',
  start_offset_minutes: 0,
  end_offset_minutes: 0,
}

// ── Formatting helpers ─────────────────────────────────────────────────

function getSolarEventLabel(eventValue: string): string {
  const event = SOLAR_EVENTS.find((e) => e.value === eventValue)
  return event ? event.label : eventValue
}

function getSolarPreviewText(
  eventValue: string,
  offsetMinutes: number,
): string | null {
  if (!eventValue || TIME_FORMAT_REGEX.test(eventValue)) return null
  const label = getSolarEventLabel(eventValue)
  const offset = offsetMinutes || 0
  if (offset === 0) return `At ${label.toLowerCase()}`
  if (offset > 0)
    return `${offset} minute${offset !== 1 ? 's' : ''} after ${label.toLowerCase()}`
  return `${Math.abs(offset)} minute${Math.abs(offset) !== 1 ? 's' : ''} before ${label.toLowerCase()}`
}

function getMixedTimeWindowWarning(
  startIsFixed: boolean,
  endIsFixed: boolean,
): string | null {
  if (startIsFixed === endIsFixed) return null
  return 'Note: Mixing fixed time with solar event may result in time windows that vary with sunrise/sunset times.'
}

// ── Component ──────────────────────────────────────────────────────────

// Zod 4 + @hookform/resolvers type workaround (@hookform/resolvers@3.x + zod@4.x)
// TODO(#449): remove cast when resolvers#800 is fixed
// Upstream: https://github.com/react-hook-form/resolvers/issues/800
const resolver = zodResolver(
  timeWindowSchema as unknown as Parameters<typeof zodResolver>[0],
) as unknown as Resolver<TimeWindowFormData>

export default function TimeWindowInput({
  value = DEFAULT_VALUE,
  onChange,
  disabled = false,
  showSolarEvents = true,
  errors: parentErrors = {},
}: TimeWindowInputProps) {
  const onChangeRef = useRef(onChange)
  onChangeRef.current = onChange

  const valueRef = useRef(value)
  valueRef.current = value

  const lastPropagatedRef = useRef({
    start_time: value.start_time,
    end_time: value.end_time,
    start_offset_minutes: value.start_offset_minutes,
    end_offset_minutes: value.end_offset_minutes,
  })

  const {
    control,
    reset,
    formState: { errors },
    watch,
  } = useForm<TimeWindowFormData>({
    resolver,
    defaultValues: {
      start_time: value.start_time,
      end_time: value.end_time,
      start_offset_minutes: value.start_offset_minutes,
      end_offset_minutes: value.end_offset_minutes,
    },
    mode: 'onChange',
  })

  // Derive mode from watched values — no useState
  const startTime = watch('start_time')
  const endTime = watch('end_time')
  const startIsFixedTime = !startTime || TIME_FORMAT_REGEX.test(startTime)
  const endIsFixedTime = !endTime || TIME_FORMAT_REGEX.test(endTime)

  // Console.warn for invalid solar event values (preserves original behavior)
  useEffect(() => {
    if (value.start_time && !TIME_FORMAT_REGEX.test(value.start_time) && !isValidSolarEvent(value.start_time)) {
      console.warn(`Invalid solar event: ${value.start_time}`)
    }
    if (value.end_time && !TIME_FORMAT_REGEX.test(value.end_time) && !isValidSolarEvent(value.end_time)) {
      console.warn(`Invalid solar event: ${value.end_time}`)
    }
  }, [value.start_time, value.end_time])

  // Prop-sync: reset form when value changes externally
  useEffect(() => {
    const last = lastPropagatedRef.current
    if (
      value.start_time !== last.start_time ||
      value.end_time !== last.end_time ||
      value.start_offset_minutes !== last.start_offset_minutes ||
      value.end_offset_minutes !== last.end_offset_minutes
    ) {
      lastPropagatedRef.current = {
        start_time: value.start_time,
        end_time: value.end_time,
        start_offset_minutes: value.start_offset_minutes,
        end_offset_minutes: value.end_offset_minutes,
      }
      reset({
        start_time: value.start_time,
        end_time: value.end_time,
        start_offset_minutes: value.start_offset_minutes,
        end_offset_minutes: value.end_offset_minutes,
      })
    }
  }, [
    value.start_time,
    value.end_time,
    value.start_offset_minutes,
    value.end_offset_minutes,
    reset,
  ])

  // Propagate validated form changes → parent
  const watchedStartTime = useWatch({ control, name: 'start_time' })
  const watchedEndTime = useWatch({ control, name: 'end_time' })
  const watchedStartOffset = useWatch({ control, name: 'start_offset_minutes' })
  const watchedEndOffset = useWatch({ control, name: 'end_offset_minutes' })
  useEffect(() => {
    if (
      watchedStartTime === undefined ||
      watchedEndTime === undefined ||
      watchedStartOffset === undefined ||
      watchedEndOffset === undefined
    )
      return
    const current = valueRef.current
    if (
      watchedStartTime === current.start_time &&
      watchedEndTime === current.end_time &&
      watchedStartOffset === current.start_offset_minutes &&
      watchedEndOffset === current.end_offset_minutes
    )
      return
    const result = timeWindowSchema.safeParse({
      start_time: watchedStartTime,
      end_time: watchedEndTime,
      start_offset_minutes: watchedStartOffset,
      end_offset_minutes: watchedEndOffset,
    })
    if (!result.success) return
    lastPropagatedRef.current = {
      start_time: watchedStartTime,
      end_time: watchedEndTime,
      start_offset_minutes: watchedStartOffset,
      end_offset_minutes: watchedEndOffset,
    }
    onChangeRef.current({
      start_time: watchedStartTime,
      end_time: watchedEndTime,
      start_offset_minutes: watchedStartOffset,
      end_offset_minutes: watchedEndOffset,
    })
  }, [watchedStartTime, watchedEndTime, watchedStartOffset, watchedEndOffset])

  // Mode switching — bypass form, call onChange directly (like presets)
  const handleStartTypeChange = (isFixed: boolean) => {
    const newValue = {
      ...valueRef.current,
      start_time: isFixed ? '' : SOLAR_EVENTS[0].value,
      start_offset_minutes: 0,
    }
    lastPropagatedRef.current = newValue
    onChangeRef.current(newValue)
  }

  const handleEndTypeChange = (isFixed: boolean) => {
    const newValue = {
      ...valueRef.current,
      end_time: isFixed ? '' : SOLAR_EVENTS[0].value,
      end_offset_minutes: 0,
    }
    lastPropagatedRef.current = newValue
    onChangeRef.current(newValue)
  }

  const mixedTimeWarning = getMixedTimeWindowWarning(
    startIsFixedTime,
    endIsFixedTime,
  )

  return (
    <div className="space-y-6">
      {/* Start Time */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Start Time
        </label>

        {showSolarEvents && (
          <div className="mb-3 flex gap-4">
            <label className="flex items-center">
              <input
                type="radio"
                checked={startIsFixedTime}
                onChange={() => handleStartTypeChange(true)}
                disabled={disabled}
                className="mr-2 focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Fixed Time
              </span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                checked={!startIsFixedTime}
                onChange={() => handleStartTypeChange(false)}
                disabled={disabled}
                className="mr-2 focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Solar Event
              </span>
            </label>
          </div>
        )}

        {startIsFixedTime ? (
          <div>
            <Controller
              name="start_time"
              control={control}
              render={({ field }) => (
                <input
                  type="time"
                  value={field.value}
                  onChange={(e) => field.onChange(e.target.value)}
                  onBlur={field.onBlur}
                  ref={field.ref}
                  disabled={disabled}
                  className="w-full rounded-md border border-gray-300 dark:border-gray-600
                           bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                           focus:ring-2 focus:ring-blue-500 focus:border-transparent
                           disabled:opacity-50 disabled:cursor-not-allowed"
                  aria-label="Start time (fixed)"
                  data-testid="time-window-start"
                  aria-invalid={
                    !!(errors.start_time || parentErrors.start_time)
                  }
                  aria-describedby={
                    errors.start_time || parentErrors.start_time
                      ? 'start_time-error'
                      : undefined
                  }
                />
              )}
            />
          </div>
        ) : (
          <div className="space-y-2">
            <div className="flex gap-2">
              <Controller
                name="start_time"
                control={control}
                render={({ field }) => (
                  <select
                    value={field.value}
                    onChange={(e) => field.onChange(e.target.value)}
                    onBlur={field.onBlur}
                    ref={field.ref}
                    disabled={disabled}
                    className="flex-1 rounded-md border border-gray-300 dark:border-gray-600
                             bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                             focus:ring-2 focus:ring-blue-500 focus:border-transparent
                             disabled:opacity-50 disabled:cursor-not-allowed"
                    aria-label="Start time (solar event)"
                    aria-invalid={
                      !!(errors.start_time || parentErrors.start_time)
                    }
                    aria-describedby={
                      errors.start_time || parentErrors.start_time
                        ? 'start_time-error'
                        : undefined
                    }
                  >
                    {SOLAR_EVENTS.map((event) => (
                      <option key={event.value} value={event.value}>
                        {event.label}
                      </option>
                    ))}
                  </select>
                )}
              />

              <div className="flex items-center gap-2">
                <label
                  htmlFor="start_offset"
                  className="text-sm text-gray-700 dark:text-gray-300 whitespace-nowrap"
                >
                  Offset:
                </label>
                <Controller
                  name="start_offset_minutes"
                  control={control}
                  render={({ field }) => (
                    <input
                      id="start_offset"
                      type="number"
                      min={-120}
                      max={120}
                      value={Number.isNaN(field.value) ? '' : field.value}
                      onChange={(e) => {
                        const raw = e.target.value
                        field.onChange(raw === '' ? NaN : Number(raw))
                      }}
                      onBlur={field.onBlur}
                      ref={field.ref}
                      disabled={disabled}
                      className="w-20 rounded-md border border-gray-300 dark:border-gray-600
                               bg-white dark:bg-gray-800 px-2 py-2 text-gray-900 dark:text-white
                               focus:ring-2 focus:ring-blue-500 focus:border-transparent
                               disabled:opacity-50 disabled:cursor-not-allowed"
                      aria-label="Start time offset (minutes)"
                    />
                  )}
                />
                <span className="text-sm text-gray-500 dark:text-gray-300">
                  min
                </span>
              </div>
            </div>

            {startTime && (
              <p className="text-sm text-gray-600 dark:text-gray-300 italic">
                {getSolarPreviewText(startTime, value.start_offset_minutes)}
              </p>
            )}
          </div>
        )}

        {(errors.start_time?.message || parentErrors.start_time) && (
          <p
            id="start_time-error"
            role="alert"
            className="mt-1 text-sm text-red-600 dark:text-red-400"
          >
            {errors.start_time?.message || parentErrors.start_time}
          </p>
        )}
      </div>

      {/* End Time — mirrors start time structure exactly */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          End Time
        </label>

        {showSolarEvents && (
          <div className="mb-3 flex gap-4">
            <label className="flex items-center">
              <input
                type="radio"
                checked={endIsFixedTime}
                onChange={() => handleEndTypeChange(true)}
                disabled={disabled}
                className="mr-2 focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Fixed Time
              </span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                checked={!endIsFixedTime}
                onChange={() => handleEndTypeChange(false)}
                disabled={disabled}
                className="mr-2 focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Solar Event
              </span>
            </label>
          </div>
        )}

        {endIsFixedTime ? (
          <div>
            <Controller
              name="end_time"
              control={control}
              render={({ field }) => (
                <input
                  type="time"
                  value={field.value}
                  onChange={(e) => field.onChange(e.target.value)}
                  onBlur={field.onBlur}
                  ref={field.ref}
                  disabled={disabled}
                  className="w-full rounded-md border border-gray-300 dark:border-gray-600
                           bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                           focus:ring-2 focus:ring-blue-500 focus:border-transparent
                           disabled:opacity-50 disabled:cursor-not-allowed"
                  aria-label="End time (fixed)"
                  data-testid="time-window-end"
                  aria-invalid={
                    !!(errors.end_time || parentErrors.end_time)
                  }
                  aria-describedby={
                    errors.end_time || parentErrors.end_time
                      ? 'end_time-error'
                      : undefined
                  }
                />
              )}
            />
          </div>
        ) : (
          <div className="space-y-2">
            <div className="flex gap-2">
              <Controller
                name="end_time"
                control={control}
                render={({ field }) => (
                  <select
                    value={field.value}
                    onChange={(e) => field.onChange(e.target.value)}
                    onBlur={field.onBlur}
                    ref={field.ref}
                    disabled={disabled}
                    className="flex-1 rounded-md border border-gray-300 dark:border-gray-600
                             bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                             focus:ring-2 focus:ring-blue-500 focus:border-transparent
                             disabled:opacity-50 disabled:cursor-not-allowed"
                    aria-label="End time (solar event)"
                    aria-invalid={
                      !!(errors.end_time || parentErrors.end_time)
                    }
                    aria-describedby={
                      errors.end_time || parentErrors.end_time
                        ? 'end_time-error'
                        : undefined
                    }
                  >
                    {SOLAR_EVENTS.map((event) => (
                      <option key={event.value} value={event.value}>
                        {event.label}
                      </option>
                    ))}
                  </select>
                )}
              />

              <div className="flex items-center gap-2">
                <label
                  htmlFor="end_offset"
                  className="text-sm text-gray-700 dark:text-gray-300 whitespace-nowrap"
                >
                  Offset:
                </label>
                <Controller
                  name="end_offset_minutes"
                  control={control}
                  render={({ field }) => (
                    <input
                      id="end_offset"
                      type="number"
                      min={-120}
                      max={120}
                      value={Number.isNaN(field.value) ? '' : field.value}
                      onChange={(e) => {
                        const raw = e.target.value
                        field.onChange(raw === '' ? NaN : Number(raw))
                      }}
                      onBlur={field.onBlur}
                      ref={field.ref}
                      disabled={disabled}
                      className="w-20 rounded-md border border-gray-300 dark:border-gray-600
                               bg-white dark:bg-gray-800 px-2 py-2 text-gray-900 dark:text-white
                               focus:ring-2 focus:ring-blue-500 focus:border-transparent
                               disabled:opacity-50 disabled:cursor-not-allowed"
                      aria-label="End time offset (minutes)"
                    />
                  )}
                />
                <span className="text-sm text-gray-500 dark:text-gray-300">
                  min
                </span>
              </div>
            </div>

            {endTime && (
              <p className="text-sm text-gray-600 dark:text-gray-300 italic">
                {getSolarPreviewText(endTime, value.end_offset_minutes)}
              </p>
            )}
          </div>
        )}

        {(errors.end_time?.message || parentErrors.end_time) && (
          <p
            id="end_time-error"
            role="alert"
            className="mt-1 text-sm text-red-600 dark:text-red-400"
          >
            {errors.end_time?.message || parentErrors.end_time}
          </p>
        )}
      </div>

      {/* Mixed Time Window Warning */}
      {mixedTimeWarning && (
        <p className="text-sm text-amber-600 dark:text-amber-400">
          {mixedTimeWarning}
        </p>
      )}

      {/* General Errors */}
      {parentErrors.general && (
        <p
          id="general-error"
          role="alert"
          className="text-sm text-red-600 dark:text-red-400"
        >
          {parentErrors.general}
        </p>
      )}
    </div>
  )
}
```

**Key implementation notes for the implementer:**
- **Mode derivation:** `!startTime || TIME_FORMAT_REGEX.test(startTime)` — empty string = fixed (matches original `useState(true)` default)
- **Mode switch handlers** bypass the form (call `onChangeRef.current()` directly, update `lastPropagatedRef`)
- **Radio buttons** are NOT Controller-wrapped — they control mode, not form fields
- **Console.warn** runs in a separate `useEffect` from prop-sync (avoids coupling)
- **Error display** uses `errors.field?.message || parentErrors.field` pattern (learning from #448)
- **General errors** use `parentErrors.general` — Zod never produces general errors (no `.refine()`)
- **Solar preview text** reads from `value.start_offset_minutes` (prop), not from watched offset, to show the committed value
- **Number input onChange:** Uses `raw === '' ? NaN : Number(raw)` pattern (from MoonPhaseTriggerForm)
- **Number input display:** Uses `Number.isNaN(field.value) ? '' : field.value` to handle cleared inputs

**Step 2: Delete the old JSX file**

Delete `webui/frontend/src/components/scheduler/ScheduleEditor/TimeWindowInput.jsx`.

**Step 3: Delete the .d.ts file**

Delete `webui/frontend/src/components/scheduler/ScheduleEditor/TimeWindowInput.d.ts`.

The `TimeWindowValue` type is now exported from `TimeWindowInput.tsx`. The barrel export in `index.js` auto-resolves to `.tsx`.

**Step 4: Verify TypeScript compiles**

Run: `cd webui/frontend && npx tsc --noEmit`
Expected: Clean — no errors.

**Step 5: Commit**

```bash
git add -A webui/frontend/src/components/scheduler/ScheduleEditor/TimeWindowInput.*
git commit -m "feat(#449): migrate TimeWindowInput to TypeScript with RHF + Zod"
```

---

### Task 3: Migrate TimeWindowInput tests (JSX → TSX)

**Files:**
- Create: `webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/TimeWindowInput.test.tsx`
- Delete: `webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/TimeWindowInput.test.jsx`
- Reference: `webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/MoonPhaseTriggerForm.test.tsx` (pattern template)

**Context:** Migrate all 41 existing tests + add tests for new RHF-specific behavior (parent error wiring, prop-sync, propagation). The migrated test file should import `TimeWindowValue` from the component (not from `.d.ts` which was deleted).

**Important behavioral changes in tests:**
1. **onChange propagation with Zod validation:** The migrated component only calls `onChange` when all fields pass schema validation. Tests that check `onChange` calls must provide values that pass the schema (valid HH:MM or solar event for times, integer ±120 for offsets).
2. **Mode switching calls onChange directly:** Radio button clicks trigger the mode switch handler, which calls `onChange` immediately (bypasses form validation). Tests for mode switching should still pass as-is.
3. **Error rendering now uses `role="alert"`:** The original JSX didn't use `role="alert"`. The TSX version does. Tests checking `errors.general` should look for the `role="alert"` element.
4. **Error display checks `errors.field?.message || parentErrors.field`:** Parent errors are shown via the `errors` prop (renamed to `parentErrors` internally).

**Step 1: Write the migrated test file**

Create `webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/TimeWindowInput.test.tsx`.

Start from the existing 41 tests in `TimeWindowInput.test.jsx` but:

1. Change imports:
   ```typescript
   import TimeWindowInput from '../TimeWindowInput'
   import type { TimeWindowValue } from '../TimeWindowInput'
   ```

2. Type the mock:
   ```typescript
   let mockOnChange: ReturnType<typeof vi.fn<(value: TimeWindowValue) => void>>
   ```

3. Add new tests for parent error wiring:
   ```typescript
   describe('Parent Error Wiring', () => {
     it('wires parentErrors.start_time to start time input via aria', () => {
       const errors = { start_time: 'Server error: invalid start time' }
       render(
         <TimeWindowInput
           {...defaultProps}
           errors={errors}
         />,
       )
       const input = screen.getByLabelText(/start time \(fixed\)/i)
       expect(input).toHaveAttribute('aria-invalid', 'true')
       expect(input).toHaveAttribute('aria-describedby', 'start_time-error')
       expect(screen.getByText(errors.start_time)).toBeInTheDocument()
     })

     it('wires parentErrors.end_time to end time input via aria', () => {
       const errors = { end_time: 'Server error: invalid end time' }
       render(
         <TimeWindowInput
           {...defaultProps}
           errors={errors}
         />,
       )
       const input = screen.getByLabelText(/end time \(fixed\)/i)
       expect(input).toHaveAttribute('aria-invalid', 'true')
       expect(input).toHaveAttribute('aria-describedby', 'end_time-error')
       expect(screen.getByText(errors.end_time)).toBeInTheDocument()
     })

     it('wires parentErrors.general to general error display', () => {
       const errors = { general: 'Invalid time window' }
       render(
         <TimeWindowInput
           {...defaultProps}
           errors={errors}
         />,
       )
       expect(screen.getByText(errors.general)).toBeInTheDocument()
     })
   })
   ```

4. Add prop-sync test:
   ```typescript
   describe('Prop Sync', () => {
     it('updates form when value prop changes externally', () => {
       const { rerender } = render(
         <TimeWindowInput {...defaultProps} />,
       )
       const newValue: TimeWindowValue = {
         start_time: '22:00',
         end_time: '06:00',
         start_offset_minutes: 0,
         end_offset_minutes: 0,
       }
       rerender(
         <TimeWindowInput
           value={newValue}
           onChange={mockOnChange}
         />,
       )
       expect(screen.getByLabelText(/start time \(fixed\)/i)).toHaveValue('22:00')
       expect(screen.getByLabelText(/end time \(fixed\)/i)).toHaveValue('06:00')
     })
   })
   ```

5. Existing tests that check `errors.general` rendering need to pass `errors={{ general: 'Invalid time window' }}` — these should still work since the component renders `parentErrors.general`. The test at line 105–120 of the original test file checks `errors.start_time`, `errors.end_time`, and `errors.general` — these all map to `parentErrors` in the migrated component.

6. The "Default Values" test at line 530–534 (`expect(screen.queryByRole('alert')).not.toBeInTheDocument()`) should still pass — no parent errors = no alert elements.

**Step 2: Delete old test file**

Delete `webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/TimeWindowInput.test.jsx`.

**Step 3: Run the migrated tests**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ScheduleEditor/__tests__/TimeWindowInput.test.tsx`
Expected: All tests PASS.

**Step 4: Commit**

```bash
git add -A webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/TimeWindowInput.test.*
git commit -m "test(#449): migrate TimeWindowInput tests to TypeScript"
```

---

### Task 4: Verification

**Step 1: Run full frontend test suite for scheduler components**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ src/schemas/scheduler/`
Expected: All tests pass (TimeWindowInput + IntervalTriggerForm + SolarTriggerForm + MoonPhaseTriggerForm + schema tests).

**Step 2: TypeScript check**

Run: `cd webui/frontend && npx tsc --noEmit`
Expected: Clean — no errors. Verify IntervalTriggerForm.tsx still compiles (it imports `TimeWindowValue` from `./TimeWindowInput`).

**Step 3: ESLint check**

Run: `cd webui/frontend && npx eslint src/components/scheduler/ScheduleEditor/TimeWindowInput.tsx src/schemas/scheduler/time-window.ts`
Expected: Clean — no errors.

**Step 4: Commit (if any fixes needed)**

Only if previous steps revealed issues that required changes.

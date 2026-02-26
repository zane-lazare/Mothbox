# Migrate SolarTriggerForm Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate SolarTriggerForm from PropTypes + manual validation to react-hook-form + Zod + TypeScript, following the controlled pattern established by IntervalTriggerForm (#446).

**Architecture:** Two validated fields (`solar_event` enum + `offset_minutes` number) in a Zod schema. `useForm` with `zodResolver` and `mode: 'onChange'` for live feedback. `useWatch` + `useEffect` propagates validated changes to the parent. DaysOfWeekSelector remains a pass-through child. Presets bypass the form and call `onChange` directly.

**Tech Stack:** React 19, react-hook-form, Zod 4, TypeScript, Vitest, @testing-library/react

---

## Reference Files

Before starting, read these files to understand the patterns:

- **Sibling component (your template):** `webui/frontend/src/components/scheduler/ScheduleEditor/IntervalTriggerForm.tsx`
- **Sibling schema:** `webui/frontend/src/schemas/scheduler/interval.ts`
- **Sibling schema tests:** `webui/frontend/src/schemas/scheduler/__tests__/interval.test.ts`
- **Sibling component tests:** `webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/IntervalTriggerForm.test.tsx`
- **Current component to migrate:** `webui/frontend/src/components/scheduler/ScheduleEditor/SolarTriggerForm.jsx`
- **Current tests to migrate:** `webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/SolarTriggerForm.test.jsx`
- **Constants (types declared):** `webui/frontend/src/components/scheduler/ScheduleEditor/constants.d.ts`
- **Design doc:** `docs/plans/2026-02-26-migrate-solar-trigger-form-design.md`

## Important Notes

- All paths below are relative to `webui/frontend/src/` unless stated otherwise.
- Run all commands from `webui/frontend/`.
- The Zod 4 + `@hookform/resolvers@3.x` type workaround requires a double `as unknown as` cast on the resolver. This is documented with a TODO and upstream issue link. Copy the exact pattern from `IntervalTriggerForm.tsx`.
- `SOLAR_EVENTS` has **15 entries** (astronomical_dawn through astronomical_dusk).
- `SCHEDULE_LIMITS.MAX_OFFSET_MINUTES` is **1440** (24 hours). The offset range is symmetric: -1440 to +1440.
- The `NaN` sentinel pattern: when the user clears the number input, pass `NaN` to `field.onChange` (not `undefined` — RHF treats `undefined` as "reset to defaultValues"). Display guard: `Number.isNaN(field.value) ? '' : field.value`.

---

### Task 1: Create the Zod Schema

**Files:**
- Create: `schemas/scheduler/solar.ts`

**Step 1: Write the schema file**

```typescript
import { z } from 'zod'
import {
  SCHEDULE_LIMITS,
  SOLAR_EVENTS,
} from '../../components/scheduler/ScheduleEditor/constants'

/**
 * Schema for fields owned by SolarTriggerForm: solar_event + offset_minutes.
 *
 * DaysOfWeekSelector has its own schema (future migration) and is
 * pass-through here.
 */

const solarEventValues = SOLAR_EVENTS.map((e) => e.value) as [string, ...string[]]

export const solarTriggerSchema = z.object({
  solar_event: z.enum(solarEventValues, {
    error: 'Invalid solar event',
  }),
  offset_minutes: z
    .number({ error: 'Offset must be a number' })
    .int('Offset must be a whole number')
    .min(
      -SCHEDULE_LIMITS.MAX_OFFSET_MINUTES,
      `Offset must be at least ${-SCHEDULE_LIMITS.MAX_OFFSET_MINUTES} minutes`,
    )
    .max(
      SCHEDULE_LIMITS.MAX_OFFSET_MINUTES,
      `Offset cannot exceed ${SCHEDULE_LIMITS.MAX_OFFSET_MINUTES} minutes`,
    ),
})

export type SolarTriggerFormData = z.infer<typeof solarTriggerSchema>
```

**Step 2: Verify typecheck passes**

Run: `npx tsc --noEmit`
Expected: No errors (exit 0).

**Step 3: Commit**

```bash
git add src/schemas/scheduler/solar.ts
git commit -m "feat(#447): add Zod schema for SolarTriggerForm"
```

---

### Task 2: Write Schema Tests

**Files:**
- Create: `schemas/scheduler/__tests__/solar.test.ts`

**Step 1: Write the schema test file**

Follow the same structure as `interval.test.ts`. Test both fields.

```typescript
import { describe, it, expect } from 'vitest'
import { solarTriggerSchema } from '../solar'
import {
  SCHEDULE_LIMITS,
  SOLAR_EVENTS,
} from '../../../components/scheduler/ScheduleEditor/constants'

/** Return the first Zod issue message from a failed parse, or null. */
function firstError(
  result: { success: boolean; error?: { issues: { message: string }[] } },
): string | null {
  if (result.success) return null
  return result.error?.issues[0]?.message ?? null
}

describe('solarTriggerSchema', () => {
  describe('solar_event field', () => {
    it('accepts all valid solar events', () => {
      for (const event of SOLAR_EVENTS) {
        const result = solarTriggerSchema.safeParse({
          solar_event: event.value,
          offset_minutes: 0,
        })
        expect(result.success).toBe(true)
      }
    })

    it('rejects an invalid solar event string', () => {
      const result = solarTriggerSchema.safeParse({
        solar_event: 'invalid_event',
        offset_minutes: 0,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Invalid solar event')
    })

    it('rejects a numeric solar event', () => {
      const result = solarTriggerSchema.safeParse({
        solar_event: 123,
        offset_minutes: 0,
      })
      expect(result.success).toBe(false)
    })

    it('rejects undefined solar event', () => {
      const result = solarTriggerSchema.safeParse({ offset_minutes: 0 })
      expect(result.success).toBe(false)
    })
  })

  describe('offset_minutes — valid values', () => {
    it('accepts zero offset', () => {
      const result = solarTriggerSchema.safeParse({
        solar_event: 'sunset',
        offset_minutes: 0,
      })
      expect(result.success).toBe(true)
    })

    it('accepts positive offset within range', () => {
      const result = solarTriggerSchema.safeParse({
        solar_event: 'sunset',
        offset_minutes: 30,
      })
      expect(result.success).toBe(true)
    })

    it('accepts negative offset within range', () => {
      const result = solarTriggerSchema.safeParse({
        solar_event: 'sunset',
        offset_minutes: -30,
      })
      expect(result.success).toBe(true)
    })

    it('accepts maximum offset (1440)', () => {
      const result = solarTriggerSchema.safeParse({
        solar_event: 'sunset',
        offset_minutes: SCHEDULE_LIMITS.MAX_OFFSET_MINUTES,
      })
      expect(result.success).toBe(true)
    })

    it('accepts minimum offset (-1440)', () => {
      const result = solarTriggerSchema.safeParse({
        solar_event: 'sunset',
        offset_minutes: -SCHEDULE_LIMITS.MAX_OFFSET_MINUTES,
      })
      expect(result.success).toBe(true)
    })

    it('accepts typical preset values', () => {
      for (const offset of [-60, -30, 0, 30, 60]) {
        const result = solarTriggerSchema.safeParse({
          solar_event: 'sunset',
          offset_minutes: offset,
        })
        expect(result.success).toBe(true)
      }
    })
  })

  describe('offset_minutes — boundary rejection', () => {
    it('rejects 1441 (above maximum)', () => {
      const result = solarTriggerSchema.safeParse({
        solar_event: 'sunset',
        offset_minutes: SCHEDULE_LIMITS.MAX_OFFSET_MINUTES + 1,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(
        `Offset cannot exceed ${SCHEDULE_LIMITS.MAX_OFFSET_MINUTES} minutes`,
      )
    })

    it('rejects -1441 (below minimum)', () => {
      const result = solarTriggerSchema.safeParse({
        solar_event: 'sunset',
        offset_minutes: -(SCHEDULE_LIMITS.MAX_OFFSET_MINUTES + 1),
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(
        `Offset must be at least ${-SCHEDULE_LIMITS.MAX_OFFSET_MINUTES} minutes`,
      )
    })
  })

  describe('offset_minutes — type rejection', () => {
    it('rejects float values', () => {
      const result = solarTriggerSchema.safeParse({
        solar_event: 'sunset',
        offset_minutes: 30.5,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Offset must be a whole number')
    })

    it('rejects string values', () => {
      const result = solarTriggerSchema.safeParse({
        solar_event: 'sunset',
        offset_minutes: '30',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Offset must be a number')
    })

    it('rejects NaN', () => {
      const result = solarTriggerSchema.safeParse({
        solar_event: 'sunset',
        offset_minutes: NaN,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Offset must be a number')
    })

    it('rejects undefined offset', () => {
      const result = solarTriggerSchema.safeParse({ solar_event: 'sunset' })
      expect(result.success).toBe(false)
    })

    it('rejects null offset', () => {
      const result = solarTriggerSchema.safeParse({
        solar_event: 'sunset',
        offset_minutes: null,
      })
      expect(result.success).toBe(false)
    })
  })
})
```

**Step 2: Run tests to verify they pass**

Run: `npx vitest run src/schemas/scheduler/__tests__/solar.test.ts`
Expected: All tests pass (should be ~18 tests).

**Step 3: Commit**

```bash
git add src/schemas/scheduler/__tests__/solar.test.ts
git commit -m "test(#447): add schema tests for solarTriggerSchema"
```

---

### Task 3: Migrate the Component (.jsx → .tsx)

**Files:**
- Delete: `components/scheduler/ScheduleEditor/SolarTriggerForm.jsx`
- Create: `components/scheduler/ScheduleEditor/SolarTriggerForm.tsx`

This is the main migration. The new file replaces the old one entirely. Use `IntervalTriggerForm.tsx` as the structural template, adapting for two `Controller` fields (`solar_event` + `offset_minutes`) instead of one.

**Step 1: Create the new `.tsx` file**

Key differences from the old `.jsx`:
- Import `useForm`, `Controller`, `useWatch` from `react-hook-form`, `zodResolver` from `@hookform/resolvers/zod`
- Import the schema + type from `schemas/scheduler/solar`
- Replace `validateNumericInput` with Zod validation via the schema
- Add `valueRef`, `onChangeRef`, `lastPropagatedRef` refs
- Add prop-sync `useEffect` that resets form when value changes externally
- Add propagation `useEffect` that fires `onChange` with validated values
- Promote `OFFSET_PRESETS` to module scope `as const`
- Export `SolarTriggerValue` interface
- Remove `PropTypes` block
- Add `aria-invalid`, `aria-describedby`, `role="alert"` for accessibility
- Add `step={1}` to the number input
- Use `NaN` sentinel for cleared offset input

```typescript
import { useEffect, useMemo, useCallback, useRef } from 'react'
import { useForm, Controller, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import type { Resolver } from 'react-hook-form'
import {
  solarTriggerSchema,
  type SolarTriggerFormData,
} from '../../../schemas/scheduler/solar'
import { SOLAR_EVENTS, SCHEDULE_LIMITS, DAYS_OF_WEEK } from './constants'
import DaysOfWeekSelector from './DaysOfWeekSelector'

// ── Types ──────────────────────────────────────────────────────────────

export interface SolarTriggerValue {
  solar_event: string
  offset_minutes: number
  days_of_week: number[] | null
}

interface SolarTriggerFormProps {
  value?: SolarTriggerValue
  onChange: (value: SolarTriggerValue) => void
  disabled?: boolean
  errors?: Record<string, string>
}

// ── Constants ──────────────────────────────────────────────────────────

const DEFAULT_VALUE: SolarTriggerValue = {
  solar_event: 'sunset',
  offset_minutes: 0,
  days_of_week: null,
}

const OFFSET_PRESETS = [
  { label: '-1h', value: -60 },
  { label: '-30m', value: -30 },
  { label: 'No offset', value: 0 },
  { label: '+30m', value: 30 },
  { label: '+1h', value: 60 },
] as const

// ── Formatting helpers (pure functions, no React state) ────────────────

function formatOffset(minutes: number): string {
  if (minutes === 0) return ''

  const absMinutes = Math.abs(minutes)

  if (absMinutes < 60) {
    return `${absMinutes} minute${absMinutes !== 1 ? 's' : ''}`
  } else if (absMinutes % 60 === 0) {
    const hours = absMinutes / 60
    return `${hours} hour${hours !== 1 ? 's' : ''}`
  }
  const hours = Math.floor(absMinutes / 60)
  const mins = absMinutes % 60
  return `${hours}h ${mins}m`
}

function formatDays(days: number[] | null | undefined): string {
  if (days === null || days === undefined) return ''
  if (!Array.isArray(days) || days.length === 0) return ''
  if (days.length === 7) return ''

  const dayLabels = days
    .slice()
    .sort((a, b) => a - b)
    .map((dayValue) => {
      const day = DAYS_OF_WEEK.find((d) => d.value === dayValue)
      return day ? day.shortLabel : ''
    })
    .filter(Boolean)

  return dayLabels.join(', ')
}

// ── Component ──────────────────────────────────────────────────────────

// Zod 4 + @hookform/resolvers type workaround (@hookform/resolvers@3.x + zod@4.x)
// TODO(#447): remove cast when resolvers#800 is fixed
// Upstream: https://github.com/react-hook-form/resolvers/issues/800
const resolver = zodResolver(
  solarTriggerSchema as unknown as Parameters<typeof zodResolver>[0],
) as unknown as Resolver<SolarTriggerFormData>

export default function SolarTriggerForm({
  value = DEFAULT_VALUE,
  onChange,
  disabled = false,
  errors: parentErrors = {},
}: SolarTriggerFormProps) {
  // Stable callback ref — prevents useWatch effect from re-running when
  // parent passes an inline arrow function as onChange.
  const onChangeRef = useRef(onChange)
  onChangeRef.current = onChange

  // Stable ref for the full value prop — lets the propagation effect read
  // current days_of_week without adding `value` to its deps.
  const valueRef = useRef(value)
  valueRef.current = value

  // Initialized to current prop so prop-sync skips the first render
  // (no external change to detect yet).
  const lastPropagatedRef = useRef({
    solar_event: value.solar_event,
    offset_minutes: value.offset_minutes,
  })

  const {
    control,
    reset,
    formState: { errors },
  } = useForm<SolarTriggerFormData>({
    resolver,
    defaultValues: {
      solar_event: value.solar_event as SolarTriggerFormData['solar_event'],
      offset_minutes: value.offset_minutes,
    },
    mode: 'onChange',
  })

  // Prop sync: reset form when solar_event or offset_minutes changes externally
  // (e.g., preset button click, parent state change)
  useEffect(() => {
    const lastProp = lastPropagatedRef.current
    if (
      value.solar_event !== lastProp.solar_event ||
      value.offset_minutes !== lastProp.offset_minutes
    ) {
      lastPropagatedRef.current = {
        solar_event: value.solar_event,
        offset_minutes: value.offset_minutes,
      }
      reset({
        solar_event: value.solar_event as SolarTriggerFormData['solar_event'],
        offset_minutes: value.offset_minutes,
      })
    }
  }, [value.solar_event, value.offset_minutes, reset])

  // Propagate validated form changes → parent
  const watchedSolarEvent = useWatch({ control, name: 'solar_event' })
  const watchedOffset = useWatch({ control, name: 'offset_minutes' })
  useEffect(() => {
    if (watchedSolarEvent === undefined || watchedOffset === undefined) return
    // Skip if values match props (avoids cycle from prop sync)
    const current = valueRef.current
    if (
      watchedSolarEvent === current.solar_event &&
      watchedOffset === current.offset_minutes
    ) return
    // Only propagate valid values
    const result = solarTriggerSchema.safeParse({
      solar_event: watchedSolarEvent,
      offset_minutes: watchedOffset,
    })
    if (!result.success) return
    lastPropagatedRef.current = {
      solar_event: watchedSolarEvent,
      offset_minutes: watchedOffset,
    }
    onChangeRef.current({
      ...valueRef.current,
      solar_event: watchedSolarEvent,
      offset_minutes: watchedOffset,
    })
  }, [watchedSolarEvent, watchedOffset])

  // Preset buttons bypass the form — call onChange directly
  const handlePresetClick = (presetValue: number) => {
    onChangeRef.current({ ...valueRef.current, offset_minutes: presetValue })
  }

  const handleDaysChange = (newDays: number[] | null) => {
    onChangeRef.current({ ...valueRef.current, days_of_week: newDays })
  }

  /**
   * Get description for the selected solar event
   */
  const getEventDescription = (): string => {
    const event = SOLAR_EVENTS.find((e) => e.value === value.solar_event)
    return event ? event.description : ''
  }

  /**
   * Get label for the selected solar event
   */
  const getEventLabel = useCallback((): string => {
    const event = SOLAR_EVENTS.find((e) => e.value === value.solar_event)
    return event ? event.label.toLowerCase() : value.solar_event
  }, [value.solar_event])

  const previewText = useMemo(() => {
    const eventLabel = getEventLabel()
    const offsetText = formatOffset(value.offset_minutes)
    const daysText = formatDays(value.days_of_week)

    let preview: string
    if (value.offset_minutes === 0) {
      preview = `At ${eventLabel}`
    } else if (value.offset_minutes > 0) {
      preview = `${offsetText} after ${eventLabel}`
    } else {
      preview = `${offsetText} before ${eventLabel}`
    }

    if (daysText) {
      preview += ` on ${daysText}`
    }

    return preview
  }, [getEventLabel, value.offset_minutes, value.days_of_week])

  return (
    <div className="space-y-6">
      {/* Header */}
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
        Solar Event Configuration
      </h3>

      {/* Solar Event Selection */}
      <div>
        <label
          htmlFor="solar_event"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Solar Event:
        </label>
        <Controller
          name="solar_event"
          control={control}
          render={({ field }) => (
            <select
              id="solar_event"
              value={field.value}
              onChange={(e) => field.onChange(e.target.value)}
              onBlur={field.onBlur}
              ref={field.ref}
              disabled={disabled}
              className="w-full rounded-md border border-gray-300 dark:border-gray-600
                       bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                       focus:ring-2 focus:ring-blue-500 focus:border-transparent
                       disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Solar event"
              aria-invalid={!!errors.solar_event}
              aria-describedby={
                errors.solar_event ? 'solar_event-error' : undefined
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
        {errors.solar_event?.message && (
          <p
            id="solar_event-error"
            role="alert"
            className="mt-1 text-sm text-red-600 dark:text-red-400"
          >
            {errors.solar_event.message}
          </p>
        )}
        {/* Event Description */}
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-300">
          {getEventDescription()}
        </p>
      </div>

      {/* Offset Input */}
      <div>
        <label
          htmlFor="offset_minutes"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Offset (minutes):
        </label>
        <div className="flex items-center gap-2">
          <Controller
            name="offset_minutes"
            control={control}
            render={({ field }) => (
              <input
                id="offset_minutes"
                type="number"
                min={-SCHEDULE_LIMITS.MAX_OFFSET_MINUTES}
                max={SCHEDULE_LIMITS.MAX_OFFSET_MINUTES}
                step={1}
                value={Number.isNaN(field.value) ? '' : field.value}
                onChange={(e) => {
                  const raw = e.target.value
                  field.onChange(raw === '' ? NaN : Number(raw))
                }}
                onBlur={field.onBlur}
                ref={field.ref}
                disabled={disabled}
                className="w-32 rounded-md border border-gray-300 dark:border-gray-600
                         bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent
                         disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label="Offset in minutes"
                aria-invalid={!!errors.offset_minutes}
                aria-describedby={
                  errors.offset_minutes ? 'offset_minutes-error' : undefined
                }
              />
            )}
          />
          <span className="text-sm text-gray-700 dark:text-gray-300">minutes</span>
        </div>
        {(errors.offset_minutes?.message ||
          parentErrors.offset_minutes) && (
          <p
            id="offset_minutes-error"
            role="alert"
            className="mt-1 text-sm text-red-600 dark:text-red-400"
          >
            {errors.offset_minutes?.message || parentErrors.offset_minutes}
          </p>
        )}
      </div>

      {/* Quick Offset Presets */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Quick presets:
        </label>
        <div className="flex flex-wrap gap-2">
          {OFFSET_PRESETS.map((preset) => (
            <button
              key={preset.value}
              type="button"
              onClick={() => handlePresetClick(preset.value)}
              disabled={disabled}
              className={`
                px-4 py-2 rounded-md text-sm font-medium
                transition-colors duration-150
                focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
                dark:focus:ring-offset-gray-800
                ${
                  value.offset_minutes === preset.value
                    ? 'bg-blue-500 text-white hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
                }
                ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              `}
              aria-label={`Set offset to ${preset.value > 0 ? '+' : ''}${preset.value} minutes`}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      {/* Days of Week */}
      <DaysOfWeekSelector
        value={value.days_of_week}
        onChange={handleDaysChange}
        disabled={disabled}
      />

      {/* Preview */}
      <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Preview:
        </label>
        <p className="text-sm text-gray-600 dark:text-gray-300 italic bg-gray-50 dark:bg-gray-800 p-3 rounded-md">
          {previewText}
        </p>
      </div>
    </div>
  )
}
```

**Step 2: Delete the old `.jsx` file**

```bash
git rm src/components/scheduler/ScheduleEditor/SolarTriggerForm.jsx
```

**Step 3: Verify typecheck passes**

Run: `npx tsc --noEmit`
Expected: No errors.

**Step 4: Commit**

```bash
git add src/components/scheduler/ScheduleEditor/SolarTriggerForm.tsx
git commit -m "feat(#447): migrate SolarTriggerForm to react-hook-form + Zod + TypeScript"
```

---

### Task 4: Migrate Component Tests (.test.jsx → .test.tsx)

**Files:**
- Delete: `components/scheduler/ScheduleEditor/__tests__/SolarTriggerForm.test.jsx`
- Create: `components/scheduler/ScheduleEditor/__tests__/SolarTriggerForm.test.tsx`

The test file migrates the existing 30+ tests from the `.jsx` file, adapting for the new react-hook-form architecture:

- Import `SolarTriggerValue` from the component (no local type duplication)
- Type `mockOnChange` with the correct signature
- Replace `fireEvent.change` with `userEvent` for offset input interactions (RHF needs real user events)
- Keep `fireEvent.change` for the `<select>` element (select changes work fine with fireEvent)
- Add new tests: validation error display, cleared input NaN, prop-sync, negative assertion (does not propagate invalid)
- Remove tests that tested `validateNumericInput` behavior directly (replaced by Zod)
- Use `waitFor` for async react-hook-form validation timing

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SolarTriggerForm from '../SolarTriggerForm'
import type { SolarTriggerValue } from '../SolarTriggerForm'
import { SOLAR_EVENTS, SCHEDULE_LIMITS } from '../constants'

// ── Mock child components ──────────────────────────────────────────────

vi.mock('../DaysOfWeekSelector', () => ({
  default: ({
    value,
    onChange,
    disabled,
  }: {
    value: number[] | null
    onChange: (v: number[] | null) => void
    disabled: boolean
  }) => (
    <div data-testid="days-of-week-selector">
      <button
        data-testid="toggle-monday"
        onClick={() => {
          const currentDays = value || [0, 1, 2, 3, 4, 5, 6]
          const newDays = currentDays.includes(0)
            ? currentDays.filter((d) => d !== 0)
            : [...currentDays, 0].sort((a, b) => a - b)
          onChange(newDays.length === 7 ? null : newDays)
        }}
        disabled={disabled}
      >
        Monday
      </button>
      <button
        data-testid="toggle-all-days"
        onClick={() => onChange(null)}
        disabled={disabled}
      >
        All Days
      </button>
    </div>
  ),
}))

// ── Helpers ────────────────────────────────────────────────────────────

const defaultValue: SolarTriggerValue = {
  solar_event: 'sunset',
  offset_minutes: 0,
  days_of_week: null,
}

// ── Tests ──────────────────────────────────────────────────────────────

describe('SolarTriggerForm', () => {
  let mockOnChange: ReturnType<typeof vi.fn<(value: SolarTriggerValue) => void>>

  beforeEach(() => {
    mockOnChange = vi.fn<(value: SolarTriggerValue) => void>()
  })

  describe('Rendering', () => {
    it('renders with default values', () => {
      render(<SolarTriggerForm onChange={mockOnChange} />)

      expect(screen.getByText('Solar Event Configuration')).toBeInTheDocument()
      expect(screen.getByLabelText(/solar event/i)).toBeInTheDocument()
      expect(screen.getByLabelText('Offset in minutes')).toBeInTheDocument()
      expect(screen.getByText('Preview:')).toBeInTheDocument()
    })

    it('renders with provided value', () => {
      const value: SolarTriggerValue = {
        solar_event: 'sunrise',
        offset_minutes: 30,
        days_of_week: [0, 1, 2],
      }

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />)

      const solarEventSelect = screen.getByLabelText(/solar event/i)
      expect(solarEventSelect).toHaveValue('sunrise')

      const offsetInput = screen.getByLabelText('Offset in minutes')
      expect(offsetInput).toHaveValue(30)
    })

    it('renders all solar events in dropdown', () => {
      render(<SolarTriggerForm onChange={mockOnChange} />)

      const solarEventSelect = screen.getByLabelText(
        /solar event/i,
      ) as HTMLSelectElement
      const options = Array.from(solarEventSelect.options).map(
        (opt) => opt.value,
      )

      SOLAR_EVENTS.forEach((event) => {
        expect(options).toContain(event.value)
      })
    })

    it('renders DaysOfWeekSelector component', () => {
      render(<SolarTriggerForm onChange={mockOnChange} />)

      expect(screen.getByTestId('days-of-week-selector')).toBeInTheDocument()
    })
  })

  describe('Solar Event Selection', () => {
    it('updates solar_event on selection change', () => {
      render(
        <SolarTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const solarEventSelect = screen.getByLabelText(/solar event/i)
      fireEvent.change(solarEventSelect, { target: { value: 'sunrise' } })

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({ solar_event: 'sunrise' }),
      )
    })

    it('shows description for selected solar event', () => {
      render(
        <SolarTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const sunsetEvent = SOLAR_EVENTS.find((e) => e.value === 'sunset')!
      expect(screen.getByText(sunsetEvent.description)).toBeInTheDocument()
    })

    it('updates description when solar event changes via props', () => {
      const { rerender } = render(
        <SolarTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const sunsetEvent = SOLAR_EVENTS.find((e) => e.value === 'sunset')!
      expect(screen.getByText(sunsetEvent.description)).toBeInTheDocument()

      const newValue = { ...defaultValue, solar_event: 'sunrise' }
      rerender(
        <SolarTriggerForm value={newValue} onChange={mockOnChange} />,
      )

      const sunriseEvent = SOLAR_EVENTS.find((e) => e.value === 'sunrise')!
      expect(screen.getByText(sunriseEvent.description)).toBeInTheDocument()
    })
  })

  describe('Offset Input', () => {
    it('updates offset_minutes on input change', async () => {
      const user = userEvent.setup()
      render(
        <SolarTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const offsetInput = screen.getByLabelText('Offset in minutes')
      await user.clear(offsetInput)
      await user.type(offsetInput, '30')

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({ offset_minutes: 30 }),
        )
      })
    })

    it('allows negative offset values', async () => {
      const user = userEvent.setup()
      render(
        <SolarTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const offsetInput = screen.getByLabelText('Offset in minutes')
      await user.clear(offsetInput)
      await user.type(offsetInput, '-30')

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({ offset_minutes: -30 }),
        )
      })
    })

    it('has min and max offset attributes', () => {
      render(<SolarTriggerForm onChange={mockOnChange} />)

      const offsetInput = screen.getByLabelText('Offset in minutes')
      expect(offsetInput).toHaveAttribute(
        'min',
        String(-SCHEDULE_LIMITS.MAX_OFFSET_MINUTES),
      )
      expect(offsetInput).toHaveAttribute(
        'max',
        String(SCHEDULE_LIMITS.MAX_OFFSET_MINUTES),
      )
    })

    it('shows error message for invalid offset', async () => {
      const user = userEvent.setup()
      render(
        <SolarTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const offsetInput = screen.getByLabelText('Offset in minutes')
      await user.clear(offsetInput)
      await user.type(offsetInput, '1441')

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })
    })

    it('shows parent error when provided', () => {
      const errors = {
        offset_minutes: 'Server error: offset out of range',
      }

      render(
        <SolarTriggerForm
          onChange={mockOnChange}
          errors={errors}
        />,
      )

      expect(screen.getByText(errors.offset_minutes)).toBeInTheDocument()
    })

    it('does not propagate invalid offset to parent', async () => {
      const user = userEvent.setup()
      render(
        <SolarTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const offsetInput = screen.getByLabelText('Offset in minutes')
      await user.clear(offsetInput)
      await user.type(offsetInput, '1441')

      // Wait for validation to process (error message appears)
      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })

      // Then assert no invalid call was made (outside waitFor to avoid false positive)
      expect(mockOnChange).not.toHaveBeenCalledWith(
        expect.objectContaining({ offset_minutes: 1441 }),
      )
    })

    it('shows error and does not propagate when input is cleared', async () => {
      const user = userEvent.setup()
      render(
        <SolarTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const offsetInput = screen.getByLabelText('Offset in minutes')
      await user.clear(offsetInput)

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })

      expect(mockOnChange).not.toHaveBeenCalledWith(
        expect.objectContaining({ offset_minutes: NaN }),
      )
    })
  })

  describe('Quick Offset Presets', () => {
    it('renders quick offset preset buttons', () => {
      render(<SolarTriggerForm onChange={mockOnChange} />)

      expect(
        screen.getByLabelText('Set offset to -60 minutes'),
      ).toBeInTheDocument()
      expect(
        screen.getByLabelText('Set offset to -30 minutes'),
      ).toBeInTheDocument()
      expect(
        screen.getByLabelText('Set offset to 0 minutes'),
      ).toBeInTheDocument()
      expect(
        screen.getByLabelText('Set offset to +30 minutes'),
      ).toBeInTheDocument()
      expect(
        screen.getByLabelText('Set offset to +60 minutes'),
      ).toBeInTheDocument()
    })

    it('sets offset to -60 when -1h preset clicked', () => {
      render(
        <SolarTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      fireEvent.click(screen.getByLabelText('Set offset to -60 minutes'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...defaultValue,
        offset_minutes: -60,
      })
    })

    it('sets offset to 0 when "No offset" preset clicked', () => {
      const value = { ...defaultValue, offset_minutes: 30 }

      render(
        <SolarTriggerForm value={value} onChange={mockOnChange} />,
      )

      fireEvent.click(screen.getByLabelText('Set offset to 0 minutes'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        offset_minutes: 0,
      })
    })

    it('sets offset to +30 when +30m preset clicked', () => {
      render(
        <SolarTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      fireEvent.click(screen.getByLabelText('Set offset to +30 minutes'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...defaultValue,
        offset_minutes: 30,
      })
    })

    it('highlights selected preset', () => {
      const value = { ...defaultValue, offset_minutes: 30 }

      render(
        <SolarTriggerForm value={value} onChange={mockOnChange} />,
      )

      const presetPos30 = screen.getByLabelText('Set offset to +30 minutes')
      expect(presetPos30).toHaveClass('bg-blue-500')
    })
  })

  describe('DaysOfWeekSelector Integration', () => {
    it('passes days_of_week value to DaysOfWeekSelector', () => {
      const value: SolarTriggerValue = {
        solar_event: 'sunset',
        offset_minutes: 0,
        days_of_week: [0, 2, 4],
      }

      render(
        <SolarTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(screen.getByTestId('days-of-week-selector')).toBeInTheDocument()
    })

    it('calls onChange when DaysOfWeekSelector changes', () => {
      render(
        <SolarTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      fireEvent.click(screen.getByTestId('toggle-monday'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...defaultValue,
        days_of_week: [1, 2, 3, 4, 5, 6],
      })
    })

    it('passes disabled state to DaysOfWeekSelector', () => {
      render(
        <SolarTriggerForm onChange={mockOnChange} disabled={true} />,
      )

      expect(screen.getByTestId('toggle-monday')).toBeDisabled()
    })
  })

  describe('Preview Text Generation', () => {
    it('generates preview for solar event without offset', () => {
      render(
        <SolarTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      expect(screen.getByText('At sunset')).toBeInTheDocument()
    })

    it('generates preview with positive offset', () => {
      const value = { ...defaultValue, offset_minutes: 30 }

      render(
        <SolarTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(screen.getByText('30 minutes after sunset')).toBeInTheDocument()
    })

    it('generates preview with negative offset', () => {
      const value = { ...defaultValue, offset_minutes: -30 }

      render(
        <SolarTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(screen.getByText('30 minutes before sunset')).toBeInTheDocument()
    })

    it('generates preview with specific days', () => {
      const value: SolarTriggerValue = {
        solar_event: 'sunset',
        offset_minutes: 0,
        days_of_week: [0, 2, 4],
      }

      render(
        <SolarTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText('At sunset on Mon, Wed, Fri'),
      ).toBeInTheDocument()
    })

    it('generates preview with offset and days', () => {
      const value: SolarTriggerValue = {
        solar_event: 'sunrise',
        offset_minutes: -15,
        days_of_week: [5, 6],
      }

      render(
        <SolarTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText('15 minutes before sunrise on Sat, Sun'),
      ).toBeInTheDocument()
    })

    it('handles large offsets in hours format', () => {
      const value = { ...defaultValue, offset_minutes: 120 }

      render(
        <SolarTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(screen.getByText('2 hours after sunset')).toBeInTheDocument()
    })

    it('handles mixed hours and minutes in preview', () => {
      const value = { ...defaultValue, offset_minutes: 90 }

      render(
        <SolarTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(screen.getByText('1h 30m after sunset')).toBeInTheDocument()
    })
  })

  describe('Disabled State', () => {
    it('disables solar event select when disabled prop is true', () => {
      render(
        <SolarTriggerForm onChange={mockOnChange} disabled={true} />,
      )

      expect(screen.getByLabelText(/solar event/i)).toBeDisabled()
    })

    it('disables offset input when disabled prop is true', () => {
      render(
        <SolarTriggerForm onChange={mockOnChange} disabled={true} />,
      )

      expect(screen.getByLabelText('Offset in minutes')).toBeDisabled()
    })

    it('disables preset buttons when disabled prop is true', () => {
      render(
        <SolarTriggerForm onChange={mockOnChange} disabled={true} />,
      )

      expect(
        screen.getByLabelText('Set offset to 0 minutes'),
      ).toBeDisabled()
    })

    it('does not disable inputs when disabled prop is false', () => {
      render(
        <SolarTriggerForm onChange={mockOnChange} disabled={false} />,
      )

      expect(screen.getByLabelText(/solar event/i)).not.toBeDisabled()
      expect(screen.getByLabelText('Offset in minutes')).not.toBeDisabled()
    })
  })

  describe('Prop Sync', () => {
    it('updates form when value prop changes externally', () => {
      const value: SolarTriggerValue = {
        solar_event: 'sunset',
        offset_minutes: 0,
        days_of_week: null,
      }

      const { rerender } = render(
        <SolarTriggerForm value={value} onChange={mockOnChange} />,
      )

      const newValue: SolarTriggerValue = {
        solar_event: 'sunrise',
        offset_minutes: 30,
        days_of_week: null,
      }
      rerender(
        <SolarTriggerForm value={newValue} onChange={mockOnChange} />,
      )

      expect(screen.getByLabelText(/solar event/i)).toHaveValue('sunrise')
      expect(screen.getByLabelText('Offset in minutes')).toHaveValue(30)
    })

    it('does not reset form when value prop is unchanged', async () => {
      const user = userEvent.setup()
      const value: SolarTriggerValue = {
        solar_event: 'sunset',
        offset_minutes: 60,
        days_of_week: null,
      }

      const { rerender } = render(
        <SolarTriggerForm value={value} onChange={mockOnChange} />,
      )

      // User types a new offset
      const offsetInput = screen.getByLabelText('Offset in minutes')
      await user.clear(offsetInput)
      await user.type(offsetInput, '90')

      // Re-render with same value (e.g., parent re-renders for unrelated reason)
      rerender(
        <SolarTriggerForm value={value} onChange={mockOnChange} />,
      )

      // The form should still show the user's typed value, not reset to 60
      expect(offsetInput).toHaveValue(90)
    })
  })

  describe('onChange Callback', () => {
    it('calls onChange with complete trigger object when event changes', () => {
      const value: SolarTriggerValue = {
        solar_event: 'sunset',
        offset_minutes: 30,
        days_of_week: [0, 1, 2],
      }

      render(
        <SolarTriggerForm value={value} onChange={mockOnChange} />,
      )

      fireEvent.change(screen.getByLabelText(/solar event/i), {
        target: { value: 'sunrise' },
      })

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          solar_event: 'sunrise',
          offset_minutes: 30,
          days_of_week: [0, 1, 2],
        }),
      )
    })

    it('calls onChange with complete trigger object when days change', () => {
      render(
        <SolarTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      fireEvent.click(screen.getByTestId('toggle-all-days'))

      expect(mockOnChange).toHaveBeenCalledWith({
        solar_event: 'sunset',
        offset_minutes: 0,
        days_of_week: null,
      })
    })
  })

  describe('Accessibility', () => {
    it('links error message to offset input via aria-describedby', async () => {
      const user = userEvent.setup()
      render(
        <SolarTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const offsetInput = screen.getByLabelText('Offset in minutes')
      await user.clear(offsetInput)
      await user.type(offsetInput, '1441')

      await waitFor(() => {
        expect(offsetInput).toHaveAttribute('aria-invalid', 'true')
        expect(offsetInput).toHaveAttribute(
          'aria-describedby',
          'offset_minutes-error',
        )
      })
    })
  })
})
```

**Step 2: Delete the old `.test.jsx` file**

```bash
git rm src/components/scheduler/ScheduleEditor/__tests__/SolarTriggerForm.test.jsx
```

**Step 3: Run all tests to verify they pass**

Run: `npx vitest run src/schemas/scheduler/__tests__/solar.test.ts src/components/scheduler/ScheduleEditor/__tests__/SolarTriggerForm.test.tsx`
Expected: All tests pass.

**Step 4: Run typecheck**

Run: `npx tsc --noEmit`
Expected: No errors.

**Step 5: Commit**

```bash
git add src/components/scheduler/ScheduleEditor/__tests__/SolarTriggerForm.test.tsx
git commit -m "test(#447): migrate SolarTriggerForm tests to TypeScript"
```

---

### Task 5: Verify No Regressions

**Step 1: Run the full frontend test suite**

Run: `npx vitest run`
Expected: All tests pass. No regressions in other components.

**Step 2: Run typecheck on entire project**

Run: `npx tsc --noEmit`
Expected: No errors.

**Step 3: Run linter**

Run: `npx eslint src/components/scheduler/ScheduleEditor/SolarTriggerForm.tsx src/schemas/scheduler/solar.ts`
Expected: No errors.

**Step 4: Commit if any fixups needed, otherwise skip**

---

### Task 6: Create PR

**Step 1: Create feature branch (if not already on one)**

```bash
git checkout -b feat/447-solar-trigger-migration dev
```

**Step 2: Push and create PR**

```bash
git push -u origin feat/447-solar-trigger-migration
gh pr create --base dev --title "feat(#447): migrate SolarTriggerForm to react-hook-form + Zod + TypeScript" --body "$(cat <<'EOF'
## Summary

Migrates SolarTriggerForm from PropTypes + manual `validateNumericInput` to react-hook-form + Zod + TypeScript, following the controlled pattern established by #446 (IntervalTriggerForm).

### Changes
- **New schema:** `src/schemas/scheduler/solar.ts` — validates `solar_event` (enum) + `offset_minutes` (number, ±1440)
- **Component:** `.jsx` → `.tsx` with `useForm`, `Controller`, `useWatch`, `valueRef`/`onChangeRef`/`lastPropagatedRef` pattern
- **Tests:** `.test.jsx` → `.test.tsx` with schema tests + migrated component tests
- **Removed:** `validateNumericInput` import, `PropTypes` block, manual validation

### What's preserved
- All CSS classes and layout
- Preview text logic (formatOffset, formatDays, getEventLabel)
- DaysOfWeekSelector pass-through
- Parent contract (onChange with complete value object)
- Preset button behavior

### Testing
- Schema tests: ~18 pure Zod tests (boundaries, type rejection, error messages)
- Component tests: ~35 tests (rendering, selection, offset, presets, days, preview, disabled, prop-sync, accessibility)

Closes #447

## Test plan
- [ ] All schema tests pass
- [ ] All component tests pass
- [ ] Full frontend test suite passes (no regressions)
- [ ] `tsc --noEmit` passes
- [ ] ESLint passes
EOF
)"
```

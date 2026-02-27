# MoonPhaseTriggerForm Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate MoonPhaseTriggerForm from JSX + PropTypes + `validateNumericInput()` to TSX + react-hook-form + Zod, matching the established pattern from IntervalTriggerForm (#446) and SolarTriggerForm (#447).

**Architecture:** Pattern 2 (Controlled) — parent owns state, component fires `onChange` on validated changes. Three form-managed Controller fields (`moon_phase`, `time_of_day`, `offset_days`) with `valueRef`/`onChangeRef`/`lastPropagatedRef` cycle prevention. Preset buttons bypass the form and call `onChange` directly.

**Tech Stack:** React 19, react-hook-form, Zod 4, zodResolver, TypeScript, Vitest + Testing Library

**Design doc:** `docs/plans/2026-02-27-migrate-moon-phase-trigger-form-design.md`

---

### Task 1: Create Zod Schema

**Files:**
- Create: `webui/frontend/src/schemas/scheduler/moon-phase.ts`

**Step 1: Write the schema**

```typescript
import { z } from 'zod'
import {
  SCHEDULE_LIMITS,
  MOON_PHASES,
} from '../../components/scheduler/ScheduleEditor/constants'

/**
 * Schema for fields owned by MoonPhaseTriggerForm:
 * moon_phase + time_of_day + offset_days.
 */

const moonPhaseValues = MOON_PHASES.map((p) => p.value) as [string, ...string[]]

export const moonPhaseTriggerSchema = z.object({
  moon_phase: z.enum(moonPhaseValues, {
    error: 'Invalid moon phase',
  }),
  time_of_day: z
    .string({ error: 'Time is required' })
    .regex(/^([01]\d|2[0-3]):[0-5]\d$/, 'Time must be in HH:MM format'),
  offset_days: z
    .number({ error: 'Offset must be a number' })
    .int('Offset must be a whole number')
    .min(
      -SCHEDULE_LIMITS.MAX_OFFSET_DAYS,
      `Offset must be at least ${-SCHEDULE_LIMITS.MAX_OFFSET_DAYS} days`,
    )
    .max(
      SCHEDULE_LIMITS.MAX_OFFSET_DAYS,
      `Offset cannot exceed ${SCHEDULE_LIMITS.MAX_OFFSET_DAYS} days`,
    ),
})

export type MoonPhaseTriggerFormData = z.infer<typeof moonPhaseTriggerSchema>
```

**Step 2: Verify it compiles**

Run: `cd webui/frontend && npx tsc --noEmit`
Expected: no errors related to `moon-phase.ts`

**Step 3: Commit**

```
git add webui/frontend/src/schemas/scheduler/moon-phase.ts
git commit -m "feat(#448): add Zod schema for MoonPhaseTriggerForm"
```

---

### Task 2: Write Schema Tests

**Files:**
- Create: `webui/frontend/src/schemas/scheduler/__tests__/moon-phase.test.ts`

**Step 1: Write the tests**

```typescript
import { describe, it, expect } from 'vitest'
import { moonPhaseTriggerSchema } from '../moon-phase'
import {
  SCHEDULE_LIMITS,
  MOON_PHASES,
} from '../../../components/scheduler/ScheduleEditor/constants'

/** Return the first Zod issue message from a failed parse, or null. */
function firstError(
  result: { success: boolean; error?: { issues: { message: string }[] } },
): string | null {
  if (result.success) return null
  return result.error?.issues[0]?.message ?? null
}

const VALID_INPUT = {
  moon_phase: 'full',
  time_of_day: '20:00',
  offset_days: 0,
}

describe('moonPhaseTriggerSchema', () => {
  describe('moon_phase field', () => {
    it('accepts all valid moon phases', () => {
      for (const phase of MOON_PHASES) {
        const result = moonPhaseTriggerSchema.safeParse({
          ...VALID_INPUT,
          moon_phase: phase.value,
        })
        expect(result.success).toBe(true)
      }
    })

    it('rejects an invalid moon phase string', () => {
      const result = moonPhaseTriggerSchema.safeParse({
        ...VALID_INPUT,
        moon_phase: 'invalid_phase',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Invalid moon phase')
    })

    it('rejects a numeric moon phase', () => {
      const result = moonPhaseTriggerSchema.safeParse({
        ...VALID_INPUT,
        moon_phase: 123,
      })
      expect(result.success).toBe(false)
    })

    it('rejects undefined moon phase', () => {
      const { moon_phase: _, ...rest } = VALID_INPUT
      const result = moonPhaseTriggerSchema.safeParse(rest)
      expect(result.success).toBe(false)
    })
  })

  describe('time_of_day field', () => {
    it('accepts valid HH:MM times', () => {
      for (const time of ['00:00', '12:30', '23:59', '09:05']) {
        const result = moonPhaseTriggerSchema.safeParse({
          ...VALID_INPUT,
          time_of_day: time,
        })
        expect(result.success).toBe(true)
      }
    })

    it('rejects invalid time formats', () => {
      for (const time of ['25:00', '12:60', '1:30', '12:5', 'abc', '']) {
        const result = moonPhaseTriggerSchema.safeParse({
          ...VALID_INPUT,
          time_of_day: time,
        })
        expect(result.success).toBe(false)
        if (time === '') {
          expect(firstError(result)).toBe('Time must be in HH:MM format')
        }
      }
    })

    it('rejects non-string time', () => {
      const result = moonPhaseTriggerSchema.safeParse({
        ...VALID_INPUT,
        time_of_day: 1200,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Time is required')
    })

    it('rejects undefined time', () => {
      const { time_of_day: _, ...rest } = VALID_INPUT
      const result = moonPhaseTriggerSchema.safeParse(rest)
      expect(result.success).toBe(false)
    })
  })

  describe('offset_days — valid values', () => {
    it('accepts zero offset', () => {
      const result = moonPhaseTriggerSchema.safeParse(VALID_INPUT)
      expect(result.success).toBe(true)
    })

    it('accepts positive offset within range', () => {
      const result = moonPhaseTriggerSchema.safeParse({
        ...VALID_INPUT,
        offset_days: 3,
      })
      expect(result.success).toBe(true)
    })

    it('accepts negative offset within range', () => {
      const result = moonPhaseTriggerSchema.safeParse({
        ...VALID_INPUT,
        offset_days: -3,
      })
      expect(result.success).toBe(true)
    })

    it('accepts maximum offset (7)', () => {
      const result = moonPhaseTriggerSchema.safeParse({
        ...VALID_INPUT,
        offset_days: SCHEDULE_LIMITS.MAX_OFFSET_DAYS,
      })
      expect(result.success).toBe(true)
    })

    it('accepts minimum offset (-7)', () => {
      const result = moonPhaseTriggerSchema.safeParse({
        ...VALID_INPUT,
        offset_days: -SCHEDULE_LIMITS.MAX_OFFSET_DAYS,
      })
      expect(result.success).toBe(true)
    })
  })

  describe('offset_days — boundary rejection', () => {
    it('rejects 8 (above maximum)', () => {
      const result = moonPhaseTriggerSchema.safeParse({
        ...VALID_INPUT,
        offset_days: SCHEDULE_LIMITS.MAX_OFFSET_DAYS + 1,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(
        `Offset cannot exceed ${SCHEDULE_LIMITS.MAX_OFFSET_DAYS} days`,
      )
    })

    it('rejects -8 (below minimum)', () => {
      const result = moonPhaseTriggerSchema.safeParse({
        ...VALID_INPUT,
        offset_days: -(SCHEDULE_LIMITS.MAX_OFFSET_DAYS + 1),
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(
        `Offset must be at least ${-SCHEDULE_LIMITS.MAX_OFFSET_DAYS} days`,
      )
    })
  })

  describe('offset_days — type rejection', () => {
    it('rejects float values', () => {
      const result = moonPhaseTriggerSchema.safeParse({
        ...VALID_INPUT,
        offset_days: 2.5,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Offset must be a whole number')
    })

    it('rejects string values', () => {
      const result = moonPhaseTriggerSchema.safeParse({
        ...VALID_INPUT,
        offset_days: '3',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Offset must be a number')
    })

    it('rejects NaN', () => {
      const result = moonPhaseTriggerSchema.safeParse({
        ...VALID_INPUT,
        offset_days: NaN,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Offset must be a number')
    })

    it('rejects undefined offset', () => {
      const { offset_days: _, ...rest } = VALID_INPUT
      const result = moonPhaseTriggerSchema.safeParse(rest)
      expect(result.success).toBe(false)
    })

    it('rejects null offset', () => {
      const result = moonPhaseTriggerSchema.safeParse({
        ...VALID_INPUT,
        offset_days: null,
      })
      expect(result.success).toBe(false)
    })
  })
})
```

**Step 2: Run tests**

Run: `cd webui/frontend && npx vitest run src/schemas/scheduler/__tests__/moon-phase.test.ts`
Expected: all tests pass

**Step 3: Commit**

```
git add webui/frontend/src/schemas/scheduler/__tests__/moon-phase.test.ts
git commit -m "test(#448): add schema tests for moonPhaseTriggerSchema"
```

---

### Task 3: Migrate Component to TypeScript

**Files:**
- Delete: `webui/frontend/src/components/scheduler/ScheduleEditor/MoonPhaseTriggerForm.jsx`
- Create: `webui/frontend/src/components/scheduler/ScheduleEditor/MoonPhaseTriggerForm.tsx`

**Step 1: Delete the old JSX file and create the new TSX file**

```typescript
import { useEffect, useMemo, useRef } from 'react'
import { useForm, Controller, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import type { Resolver } from 'react-hook-form'
import {
  moonPhaseTriggerSchema,
  type MoonPhaseTriggerFormData,
} from '../../../schemas/scheduler/moon-phase'
import { MOON_PHASES, SCHEDULE_LIMITS } from './constants'

// ── Types ──────────────────────────────────────────────────────────────

export interface MoonPhaseTriggerValue {
  moon_phase: string
  time_of_day: string
  offset_days: number
}

interface MoonPhaseTriggerFormProps {
  value?: MoonPhaseTriggerValue
  onChange: (value: MoonPhaseTriggerValue) => void
  disabled?: boolean
  errors?: Record<string, string>
}

// ── Constants ──────────────────────────────────────────────────────────

const DEFAULT_VALUE: MoonPhaseTriggerValue = {
  moon_phase: 'full',
  time_of_day: '20:00',
  offset_days: 0,
}

const OFFSET_PRESETS = [
  { label: '-1 day', value: -1 },
  { label: 'No offset', value: 0 },
  { label: '+1 day', value: 1 },
] as const

// ── Formatting helpers (pure functions, no React state) ────────────────

function formatOffset(days: number): string {
  if (days === 0) return ''
  const absDays = Math.abs(days)
  return `${absDays} day${absDays !== 1 ? 's' : ''}`
}

// ── Component ──────────────────────────────────────────────────────────

// Zod 4 + @hookform/resolvers type workaround (@hookform/resolvers@3.x + zod@4.x)
// TODO(#448): remove cast when resolvers#800 is fixed
// Upstream: https://github.com/react-hook-form/resolvers/issues/800
const resolver = zodResolver(
  moonPhaseTriggerSchema as unknown as Parameters<typeof zodResolver>[0],
) as unknown as Resolver<MoonPhaseTriggerFormData>

export default function MoonPhaseTriggerForm({
  value = DEFAULT_VALUE,
  onChange,
  disabled = false,
  errors: parentErrors = {},
}: MoonPhaseTriggerFormProps) {
  // Stable callback ref — prevents useWatch effect from re-running when
  // parent passes an inline arrow function as onChange.
  const onChangeRef = useRef(onChange)
  onChangeRef.current = onChange

  // Stable ref for the full value prop — lets the propagation effect read
  // current value without adding `value` to its deps.
  const valueRef = useRef(value)
  valueRef.current = value

  // Initialized to current prop so prop-sync skips the first render
  // (no external change to detect yet).
  const lastPropagatedRef = useRef({
    moon_phase: value.moon_phase,
    time_of_day: value.time_of_day,
    offset_days: value.offset_days,
  })

  const {
    control,
    reset,
    formState: { errors },
  } = useForm<MoonPhaseTriggerFormData>({
    resolver,
    defaultValues: {
      moon_phase: value.moon_phase as MoonPhaseTriggerFormData['moon_phase'],
      time_of_day: value.time_of_day,
      offset_days: value.offset_days,
    },
    mode: 'onChange',
  })

  // Prop sync: reset form when any field changes externally
  // (e.g., preset button click, parent state change)
  useEffect(() => {
    const last = lastPropagatedRef.current
    if (
      value.moon_phase !== last.moon_phase ||
      value.time_of_day !== last.time_of_day ||
      value.offset_days !== last.offset_days
    ) {
      lastPropagatedRef.current = {
        moon_phase: value.moon_phase,
        time_of_day: value.time_of_day,
        offset_days: value.offset_days,
      }
      reset({
        moon_phase: value.moon_phase as MoonPhaseTriggerFormData['moon_phase'],
        time_of_day: value.time_of_day,
        offset_days: value.offset_days,
      })
    }
  }, [value.moon_phase, value.time_of_day, value.offset_days, reset])

  // Propagate validated form changes → parent
  const watchedMoonPhase = useWatch({ control, name: 'moon_phase' })
  const watchedTimeOfDay = useWatch({ control, name: 'time_of_day' })
  const watchedOffset = useWatch({ control, name: 'offset_days' })
  useEffect(() => {
    if (
      watchedMoonPhase === undefined ||
      watchedTimeOfDay === undefined ||
      watchedOffset === undefined
    ) return
    // Skip if values match props (avoids cycle from prop sync)
    const current = valueRef.current
    if (
      watchedMoonPhase === current.moon_phase &&
      watchedTimeOfDay === current.time_of_day &&
      watchedOffset === current.offset_days
    ) return
    // Only propagate valid values
    const result = moonPhaseTriggerSchema.safeParse({
      moon_phase: watchedMoonPhase,
      time_of_day: watchedTimeOfDay,
      offset_days: watchedOffset,
    })
    if (!result.success) return
    lastPropagatedRef.current = {
      moon_phase: watchedMoonPhase,
      time_of_day: watchedTimeOfDay,
      offset_days: watchedOffset,
    }
    onChangeRef.current({
      moon_phase: watchedMoonPhase,
      time_of_day: watchedTimeOfDay,
      offset_days: watchedOffset,
    })
  }, [watchedMoonPhase, watchedTimeOfDay, watchedOffset])

  // Preset buttons bypass the form — call onChange directly
  const handlePresetClick = (presetValue: number) => {
    onChangeRef.current({ ...valueRef.current, offset_days: presetValue })
  }

  const previewText = useMemo(() => {
    const phase = MOON_PHASES.find((p) => p.value === value.moon_phase)
    const phaseLabel = phase ? phase.label : value.moon_phase
    const offsetText = formatOffset(value.offset_days)
    const time = value.time_of_day

    if (value.offset_days === 0) {
      return `On ${phaseLabel} at ${time}`
    } else if (value.offset_days > 0) {
      return `${offsetText} after ${phaseLabel} at ${time}`
    } else {
      return `${offsetText} before ${phaseLabel} at ${time}`
    }
  }, [value.moon_phase, value.time_of_day, value.offset_days])

  return (
    <div className="space-y-6">
      {/* Header */}
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
        Moon Phase Configuration
      </h3>

      {/* Moon Phase Selection */}
      <div>
        <label
          htmlFor="moon_phase"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Moon Phase:
        </label>
        <Controller
          name="moon_phase"
          control={control}
          render={({ field }) => (
            <select
              id="moon_phase"
              value={field.value}
              onChange={(e) => field.onChange(e.target.value)}
              onBlur={field.onBlur}
              ref={field.ref}
              disabled={disabled}
              className="w-full rounded-md border border-gray-300 dark:border-gray-600
                       bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                       focus:ring-2 focus:ring-blue-500 focus:border-transparent
                       disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Moon phase"
              aria-invalid={!!errors.moon_phase}
              aria-describedby={
                errors.moon_phase ? 'moon_phase-error' : undefined
              }
            >
              {MOON_PHASES.map((phase) => (
                <option key={phase.value} value={phase.value}>
                  {phase.label}
                </option>
              ))}
            </select>
          )}
        />
        {errors.moon_phase?.message && (
          <p
            id="moon_phase-error"
            role="alert"
            className="mt-1 text-sm text-red-600 dark:text-red-400"
          >
            {errors.moon_phase.message}
          </p>
        )}
      </div>

      {/* Time of Day Input */}
      <div>
        <label
          htmlFor="time_of_day"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Time of Day:
        </label>
        <Controller
          name="time_of_day"
          control={control}
          render={({ field }) => (
            <input
              id="time_of_day"
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
              aria-label="Time of day"
              aria-invalid={!!(errors.time_of_day || parentErrors.time_of_day)}
              aria-describedby={
                (errors.time_of_day || parentErrors.time_of_day)
                  ? 'time_of_day-error'
                  : undefined
              }
            />
          )}
        />
        {(errors.time_of_day?.message || parentErrors.time_of_day) && (
          <p
            id="time_of_day-error"
            role="alert"
            className="mt-1 text-sm text-red-600 dark:text-red-400"
          >
            {errors.time_of_day?.message || parentErrors.time_of_day}
          </p>
        )}
      </div>

      {/* Offset Days Input */}
      <div>
        <label
          htmlFor="offset_days"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Offset (days):
        </label>
        <div className="flex items-center gap-2">
          <Controller
            name="offset_days"
            control={control}
            render={({ field }) => (
              <input
                id="offset_days"
                type="number"
                min={-SCHEDULE_LIMITS.MAX_OFFSET_DAYS}
                max={SCHEDULE_LIMITS.MAX_OFFSET_DAYS}
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
                aria-label="Offset in days"
                aria-invalid={!!(errors.offset_days || parentErrors.offset_days)}
                aria-describedby={
                  (errors.offset_days || parentErrors.offset_days)
                    ? 'offset_days-error'
                    : undefined
                }
              />
            )}
          />
          <span className="text-sm text-gray-700 dark:text-gray-300">days</span>
        </div>
        {(errors.offset_days?.message || parentErrors.offset_days) && (
          <p
            id="offset_days-error"
            role="alert"
            className="mt-1 text-sm text-red-600 dark:text-red-400"
          >
            {errors.offset_days?.message || parentErrors.offset_days}
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
                  value.offset_days === preset.value
                    ? 'bg-blue-500 text-white hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
                }
                ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              `}
              aria-label={`Set offset to ${preset.value} days`}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

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

**Step 2: Verify it compiles**

Run: `cd webui/frontend && npx tsc --noEmit`
Expected: no errors

**Step 3: Commit**

```
git rm webui/frontend/src/components/scheduler/ScheduleEditor/MoonPhaseTriggerForm.jsx
git add webui/frontend/src/components/scheduler/ScheduleEditor/MoonPhaseTriggerForm.tsx
git commit -m "feat(#448): migrate MoonPhaseTriggerForm to react-hook-form + Zod + TypeScript"
```

---

### Task 4: Migrate Tests to TypeScript

**Files:**
- Delete: `webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/MoonPhaseTriggerForm.test.jsx`
- Create: `webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/MoonPhaseTriggerForm.test.tsx`

**Step 1: Delete the old test file and create the new one**

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MoonPhaseTriggerForm from '../MoonPhaseTriggerForm'
import type { MoonPhaseTriggerValue } from '../MoonPhaseTriggerForm'
import { MOON_PHASES, SCHEDULE_LIMITS } from '../constants'

// ── Helpers ────────────────────────────────────────────────────────────

const defaultValue: MoonPhaseTriggerValue = {
  moon_phase: 'full',
  time_of_day: '20:00',
  offset_days: 0,
}

// ── Tests ──────────────────────────────────────────────────────────────

describe('MoonPhaseTriggerForm', () => {
  let mockOnChange: ReturnType<typeof vi.fn<(value: MoonPhaseTriggerValue) => void>>

  beforeEach(() => {
    mockOnChange = vi.fn<(value: MoonPhaseTriggerValue) => void>()
  })

  describe('Rendering', () => {
    it('renders with default values', () => {
      render(<MoonPhaseTriggerForm onChange={mockOnChange} />)

      expect(screen.getByText('Moon Phase Configuration')).toBeInTheDocument()
      expect(screen.getByLabelText(/moon phase/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/time of day/i)).toBeInTheDocument()
      expect(screen.getByLabelText('Offset in days')).toBeInTheDocument()
      expect(screen.getByText('Preview:')).toBeInTheDocument()
    })

    it('renders with provided value', () => {
      const value: MoonPhaseTriggerValue = {
        moon_phase: 'new',
        time_of_day: '21:30',
        offset_days: 2,
      }

      render(<MoonPhaseTriggerForm value={value} onChange={mockOnChange} />)

      expect(screen.getByLabelText(/moon phase/i)).toHaveValue('new')
      expect(screen.getByLabelText(/time of day/i)).toHaveValue('21:30')
      expect(screen.getByLabelText('Offset in days')).toHaveValue(2)
    })

    it('renders all moon phases in dropdown', () => {
      render(<MoonPhaseTriggerForm onChange={mockOnChange} />)

      const select = screen.getByLabelText(/moon phase/i) as HTMLSelectElement
      const options = Array.from(select.options).map((opt) => opt.value)

      MOON_PHASES.forEach((phase) => {
        expect(options).toContain(phase.value)
      })
    })
  })

  describe('Moon Phase Selection', () => {
    it('updates moon_phase on selection change', () => {
      render(
        <MoonPhaseTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      fireEvent.change(screen.getByLabelText(/moon phase/i), {
        target: { value: 'new' },
      })

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({ moon_phase: 'new' }),
      )
    })

    it('shows label for selected moon phase', () => {
      render(
        <MoonPhaseTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const fullMoonPhase = MOON_PHASES.find((p) => p.value === 'full')!
      expect(
        screen.getByRole('option', { name: fullMoonPhase.label }),
      ).toBeInTheDocument()
    })
  })

  describe('Time of Day Input', () => {
    it('updates time_of_day on input change', () => {
      render(
        <MoonPhaseTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      fireEvent.change(screen.getByLabelText(/time of day/i), {
        target: { value: '22:30' },
      })

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({ time_of_day: '22:30' }),
      )
    })

    it('has time input type', () => {
      render(<MoonPhaseTriggerForm onChange={mockOnChange} />)

      expect(screen.getByLabelText(/time of day/i)).toHaveAttribute(
        'type',
        'time',
      )
    })

    it('shows parent error when provided', () => {
      const errors = { time_of_day: 'Time must be in HH:MM format' }

      render(
        <MoonPhaseTriggerForm onChange={mockOnChange} errors={errors} />,
      )

      expect(screen.getByText(errors.time_of_day)).toBeInTheDocument()
    })
  })

  describe('Offset Days Input', () => {
    it('updates offset_days on input change', async () => {
      const user = userEvent.setup()
      render(
        <MoonPhaseTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const offsetInput = screen.getByLabelText('Offset in days')
      await user.clear(offsetInput)
      await user.type(offsetInput, '3')

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({ offset_days: 3 }),
        )
      })
    })

    it('allows negative offset values', async () => {
      const user = userEvent.setup()
      render(
        <MoonPhaseTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const offsetInput = screen.getByLabelText('Offset in days')
      await user.clear(offsetInput)
      await user.type(offsetInput, '-3')

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({ offset_days: -3 }),
        )
      })
    })

    it('has min and max offset attributes', () => {
      render(<MoonPhaseTriggerForm onChange={mockOnChange} />)

      const offsetInput = screen.getByLabelText('Offset in days')
      expect(offsetInput).toHaveAttribute(
        'min',
        String(-SCHEDULE_LIMITS.MAX_OFFSET_DAYS),
      )
      expect(offsetInput).toHaveAttribute(
        'max',
        String(SCHEDULE_LIMITS.MAX_OFFSET_DAYS),
      )
    })

    it('shows error message for invalid offset', async () => {
      const user = userEvent.setup()
      render(
        <MoonPhaseTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const offsetInput = screen.getByLabelText('Offset in days')
      await user.clear(offsetInput)
      await user.type(offsetInput, '8')

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })
    })

    it('shows parent error when provided', () => {
      const errors = { offset_days: 'Offset must be between -7 and 7 days' }

      render(
        <MoonPhaseTriggerForm onChange={mockOnChange} errors={errors} />,
      )

      expect(screen.getByText(errors.offset_days)).toBeInTheDocument()
    })

    it('does not propagate invalid offset to parent', async () => {
      const user = userEvent.setup()
      render(
        <MoonPhaseTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const offsetInput = screen.getByLabelText('Offset in days')
      await user.clear(offsetInput)
      await user.type(offsetInput, '8')

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })

      expect(mockOnChange).not.toHaveBeenCalledWith(
        expect.objectContaining({ offset_days: 8 }),
      )
    })

    it('shows error and does not propagate when input is cleared', async () => {
      const user = userEvent.setup()
      render(
        <MoonPhaseTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const offsetInput = screen.getByLabelText('Offset in days')
      await user.clear(offsetInput)

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })

      expect(mockOnChange).not.toHaveBeenCalledWith(
        expect.objectContaining({ offset_days: NaN }),
      )
    })
  })

  describe('Quick Offset Presets', () => {
    it('renders quick offset preset buttons', () => {
      render(<MoonPhaseTriggerForm onChange={mockOnChange} />)

      expect(screen.getByLabelText('Set offset to -1 days')).toBeInTheDocument()
      expect(screen.getByLabelText('Set offset to 0 days')).toBeInTheDocument()
      expect(screen.getByLabelText('Set offset to 1 days')).toBeInTheDocument()
    })

    it('sets offset to -1 when -1 day preset clicked', () => {
      render(
        <MoonPhaseTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      fireEvent.click(screen.getByLabelText('Set offset to -1 days'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...defaultValue,
        offset_days: -1,
      })
    })

    it('sets offset to 0 when "No offset" preset clicked', () => {
      const value = { ...defaultValue, offset_days: 2 }

      render(
        <MoonPhaseTriggerForm value={value} onChange={mockOnChange} />,
      )

      fireEvent.click(screen.getByLabelText('Set offset to 0 days'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        offset_days: 0,
      })
    })

    it('sets offset to +1 when +1 day preset clicked', () => {
      render(
        <MoonPhaseTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      fireEvent.click(screen.getByLabelText('Set offset to 1 days'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...defaultValue,
        offset_days: 1,
      })
    })

    it('highlights selected preset', () => {
      const value = { ...defaultValue, offset_days: 1 }

      render(
        <MoonPhaseTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(screen.getByLabelText('Set offset to 1 days')).toHaveClass(
        'bg-blue-500',
      )
    })
  })

  describe('Preview Text Generation', () => {
    it('generates preview for moon phase without offset', () => {
      render(
        <MoonPhaseTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      expect(screen.getByText('On Full Moon at 20:00')).toBeInTheDocument()
    })

    it('generates preview with positive offset', () => {
      const value = { ...defaultValue, offset_days: 2 }

      render(
        <MoonPhaseTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText('2 days after Full Moon at 20:00'),
      ).toBeInTheDocument()
    })

    it('generates preview with negative offset', () => {
      const value = { ...defaultValue, offset_days: -3 }

      render(
        <MoonPhaseTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText('3 days before Full Moon at 20:00'),
      ).toBeInTheDocument()
    })

    it('generates preview with singular day offset', () => {
      const value: MoonPhaseTriggerValue = {
        moon_phase: 'new',
        time_of_day: '22:00',
        offset_days: 1,
      }

      render(
        <MoonPhaseTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText('1 day after New Moon at 22:00'),
      ).toBeInTheDocument()
    })

    it('generates preview for different moon phases', () => {
      const value: MoonPhaseTriggerValue = {
        moon_phase: 'waxing_crescent',
        time_of_day: '19:30',
        offset_days: 0,
      }

      render(
        <MoonPhaseTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText('On Waxing Crescent at 19:30'),
      ).toBeInTheDocument()
    })
  })

  describe('Disabled State', () => {
    it('disables moon phase select when disabled prop is true', () => {
      render(
        <MoonPhaseTriggerForm onChange={mockOnChange} disabled={true} />,
      )

      expect(screen.getByLabelText(/moon phase/i)).toBeDisabled()
    })

    it('disables time input when disabled prop is true', () => {
      render(
        <MoonPhaseTriggerForm onChange={mockOnChange} disabled={true} />,
      )

      expect(screen.getByLabelText(/time of day/i)).toBeDisabled()
    })

    it('disables offset input when disabled prop is true', () => {
      render(
        <MoonPhaseTriggerForm onChange={mockOnChange} disabled={true} />,
      )

      expect(screen.getByLabelText('Offset in days')).toBeDisabled()
    })

    it('disables preset buttons when disabled prop is true', () => {
      render(
        <MoonPhaseTriggerForm onChange={mockOnChange} disabled={true} />,
      )

      expect(screen.getByLabelText('Set offset to 0 days')).toBeDisabled()
    })

    it('does not disable inputs when disabled prop is false', () => {
      render(
        <MoonPhaseTriggerForm onChange={mockOnChange} disabled={false} />,
      )

      expect(screen.getByLabelText(/moon phase/i)).not.toBeDisabled()
      expect(screen.getByLabelText(/time of day/i)).not.toBeDisabled()
      expect(screen.getByLabelText('Offset in days')).not.toBeDisabled()
    })
  })

  describe('Prop Sync', () => {
    it('updates form when value prop changes externally', () => {
      const { rerender } = render(
        <MoonPhaseTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const newValue: MoonPhaseTriggerValue = {
        moon_phase: 'new',
        time_of_day: '22:00',
        offset_days: 3,
      }
      rerender(
        <MoonPhaseTriggerForm value={newValue} onChange={mockOnChange} />,
      )

      expect(screen.getByLabelText(/moon phase/i)).toHaveValue('new')
      expect(screen.getByLabelText(/time of day/i)).toHaveValue('22:00')
      expect(screen.getByLabelText('Offset in days')).toHaveValue(3)
    })

    it('does not reset form when value prop is unchanged', async () => {
      const user = userEvent.setup()
      const value: MoonPhaseTriggerValue = {
        moon_phase: 'full',
        time_of_day: '20:00',
        offset_days: 3,
      }

      const { rerender } = render(
        <MoonPhaseTriggerForm value={value} onChange={mockOnChange} />,
      )

      const offsetInput = screen.getByLabelText('Offset in days')
      await user.clear(offsetInput)
      await user.type(offsetInput, '5')

      // Wait for propagation to settle so lastPropagatedRef is updated
      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({ offset_days: 5 }),
        )
      })

      // Re-render with same value (e.g., parent re-renders for unrelated reason)
      rerender(
        <MoonPhaseTriggerForm value={value} onChange={mockOnChange} />,
      )

      // The form should still show the user's typed value, not reset to 3
      expect(offsetInput).toHaveValue(5)
    })
  })

  describe('onChange Callback', () => {
    it('calls onChange with complete trigger object when moon phase changes', () => {
      const value: MoonPhaseTriggerValue = {
        moon_phase: 'full',
        time_of_day: '20:00',
        offset_days: 2,
      }

      render(
        <MoonPhaseTriggerForm value={value} onChange={mockOnChange} />,
      )

      fireEvent.change(screen.getByLabelText(/moon phase/i), {
        target: { value: 'new' },
      })

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          moon_phase: 'new',
          time_of_day: '20:00',
          offset_days: 2,
        }),
      )
    })

    it('calls onChange with complete trigger object when time changes', () => {
      render(
        <MoonPhaseTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      fireEvent.change(screen.getByLabelText(/time of day/i), {
        target: { value: '23:45' },
      })

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          moon_phase: 'full',
          time_of_day: '23:45',
          offset_days: 0,
        }),
      )
    })
  })

  describe('Accessibility', () => {
    it('links parent error to offset input via aria-describedby', () => {
      const errors = { offset_days: 'Server error: offset out of range' }

      render(
        <MoonPhaseTriggerForm onChange={mockOnChange} errors={errors} />,
      )

      const offsetInput = screen.getByLabelText('Offset in days')
      expect(offsetInput).toHaveAttribute('aria-invalid', 'true')
      expect(offsetInput).toHaveAttribute(
        'aria-describedby',
        'offset_days-error',
      )
    })

    it('links parent error to time input via aria-describedby', () => {
      const errors = { time_of_day: 'Invalid time' }

      render(
        <MoonPhaseTriggerForm onChange={mockOnChange} errors={errors} />,
      )

      const timeInput = screen.getByLabelText(/time of day/i)
      expect(timeInput).toHaveAttribute('aria-invalid', 'true')
      expect(timeInput).toHaveAttribute(
        'aria-describedby',
        'time_of_day-error',
      )
    })

    it('links error message to offset input via aria-describedby', async () => {
      const user = userEvent.setup()
      render(
        <MoonPhaseTriggerForm value={defaultValue} onChange={mockOnChange} />,
      )

      const offsetInput = screen.getByLabelText('Offset in days')
      await user.clear(offsetInput)
      await user.type(offsetInput, '8')

      await waitFor(() => {
        expect(offsetInput).toHaveAttribute('aria-invalid', 'true')
        expect(offsetInput).toHaveAttribute(
          'aria-describedby',
          'offset_days-error',
        )
      })
    })
  })
})
```

**Step 2: Run tests**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ScheduleEditor/__tests__/MoonPhaseTriggerForm.test.tsx`
Expected: all tests pass

**Step 3: Commit**

```
git rm webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/MoonPhaseTriggerForm.test.jsx
git add webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/MoonPhaseTriggerForm.test.tsx
git commit -m "test(#448): migrate MoonPhaseTriggerForm tests to TypeScript"
```

---

### Task 5: Verify No Regressions

**Step 1: Run full frontend test suite**

Run: `cd webui/frontend && npx vitest run`
Expected: all tests pass, 0 failures

**Step 2: Run typecheck**

Run: `cd webui/frontend && npx tsc --noEmit`
Expected: no errors

**Step 3: Run linter**

Run: `cd webui/frontend && npx eslint src/schemas/scheduler/moon-phase.ts src/components/scheduler/ScheduleEditor/MoonPhaseTriggerForm.tsx`
Expected: no errors

---

### Task 6: Create PR

**Step 1: Push branch and create PR**

```
git push -u origin feat/448-moon-phase-trigger-migration
gh pr create --base dev --title "feat(#448): migrate MoonPhaseTriggerForm to react-hook-form + Zod + TypeScript" --body "$(cat <<'EOF'
## Summary
- Migrate MoonPhaseTriggerForm from JSX + PropTypes to TSX + react-hook-form + Zod
- Add Zod schema with enum validation for moon phases, HH:MM regex for time_of_day, ±7 integer range for offset_days
- Apply established Pattern 2 (Controlled) with valueRef/onChangeRef/lastPropagatedRef cycle prevention
- Wire aria-invalid + aria-describedby for both Zod and parent errors (accessibility improvement)
- Drop 6 dark mode styling tests (not tested in siblings, low value)

Closes #448

## Test plan
- [ ] Schema tests pass (moon-phase.test.ts)
- [ ] Component tests pass (MoonPhaseTriggerForm.test.tsx)
- [ ] Full frontend suite passes with 0 regressions
- [ ] TypeScript compiles cleanly
- [ ] ESLint passes
EOF
)"
```

# Migrate IntervalTriggerForm Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate IntervalTriggerForm from manual useState validation to react-hook-form + Zod with TypeScript (Pattern 2: Controlled).

**Architecture:** Zod schema validates only `interval_minutes` (the one field this component owns). TimeWindowInput and DaysOfWeekSelector remain pass-through child components. `useForm` with `zodResolver` and `mode: 'onChange'` provides live validation. `useWatch` + `useEffect` propagates validated changes back to parent via `onChange`. Prop sync resets form when external values change (e.g., preset clicks).

**Tech Stack:** React 19, react-hook-form, Zod 4, @hookform/resolvers, TypeScript, Vitest, @testing-library/react, @testing-library/user-event

---

### Task 1: Create the interval trigger schema

**Files:**
- Create: `webui/frontend/src/schemas/scheduler/interval.ts`

**Step 1: Create the scheduler schema directory**

```bash
mkdir -p webui/frontend/src/schemas/scheduler
```

**Step 2: Create the schema file**

Create `webui/frontend/src/schemas/scheduler/interval.ts`:

```typescript
import { z } from 'zod'
import { SCHEDULE_LIMITS } from '../../components/scheduler/ScheduleEditor/constants'

/**
 * Schema for the interval_minutes field owned by IntervalTriggerForm.
 *
 * TimeWindowInput and DaysOfWeekSelector have their own schemas
 * (scheduler/time-window.ts, future) and are pass-through here.
 */
export const intervalTriggerSchema = z.object({
  interval_minutes: z
    .number({ invalid_type_error: 'Interval must be a number' })
    .int('Interval must be a whole number')
    .min(
      SCHEDULE_LIMITS.MIN_INTERVAL_MINUTES,
      `Interval must be at least ${SCHEDULE_LIMITS.MIN_INTERVAL_MINUTES} minute`,
    )
    .max(
      SCHEDULE_LIMITS.MAX_INTERVAL_MINUTES,
      `Interval cannot exceed ${SCHEDULE_LIMITS.MAX_INTERVAL_MINUTES} minutes`,
    ),
})

export type IntervalTriggerFormData = z.infer<typeof intervalTriggerSchema>
```

**Step 3: Commit**

```bash
git add webui/frontend/src/schemas/scheduler/interval.ts
git commit -m "feat(#446): create interval trigger Zod schema"
```

---

### Task 2: Write schema tests

**Files:**
- Create: `webui/frontend/src/schemas/scheduler/__tests__/interval.test.ts`

**Step 1: Create the test directory**

```bash
mkdir -p webui/frontend/src/schemas/scheduler/__tests__
```

**Step 2: Write the schema tests**

Create `webui/frontend/src/schemas/scheduler/__tests__/interval.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { intervalTriggerSchema } from '../interval'
import { SCHEDULE_LIMITS } from '../../../components/scheduler/ScheduleEditor/constants'

/** Return the first Zod issue message from a failed parse, or null. */
function firstError(
  result: { success: boolean; error?: { issues: { message: string }[] } },
): string | null {
  if (result.success) return null
  return result.error?.issues[0]?.message ?? null
}

describe('intervalTriggerSchema', () => {
  describe('valid values', () => {
    it('accepts minimum interval (1)', () => {
      const result = intervalTriggerSchema.safeParse({ interval_minutes: 1 })
      expect(result.success).toBe(true)
    })

    it('accepts default interval (60)', () => {
      const result = intervalTriggerSchema.safeParse({ interval_minutes: 60 })
      expect(result.success).toBe(true)
    })

    it('accepts maximum interval (10080)', () => {
      const result = intervalTriggerSchema.safeParse({ interval_minutes: 10080 })
      expect(result.success).toBe(true)
    })

    it('accepts typical preset values', () => {
      for (const minutes of [15, 30, 60, 120, 240]) {
        const result = intervalTriggerSchema.safeParse({ interval_minutes: minutes })
        expect(result.success).toBe(true)
      }
    })
  })

  describe('boundary rejection', () => {
    it('rejects 0 (below minimum)', () => {
      const result = intervalTriggerSchema.safeParse({ interval_minutes: 0 })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(
        `Interval must be at least ${SCHEDULE_LIMITS.MIN_INTERVAL_MINUTES} minute`,
      )
    })

    it('rejects negative values', () => {
      const result = intervalTriggerSchema.safeParse({ interval_minutes: -10 })
      expect(result.success).toBe(false)
    })

    it('rejects 10081 (above maximum)', () => {
      const result = intervalTriggerSchema.safeParse({ interval_minutes: 10081 })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(
        `Interval cannot exceed ${SCHEDULE_LIMITS.MAX_INTERVAL_MINUTES} minutes`,
      )
    })
  })

  describe('type rejection', () => {
    it('rejects float values', () => {
      const result = intervalTriggerSchema.safeParse({ interval_minutes: 30.5 })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Interval must be a whole number')
    })

    it('rejects string values', () => {
      const result = intervalTriggerSchema.safeParse({ interval_minutes: '60' })
      expect(result.success).toBe(false)
    })

    it('rejects NaN', () => {
      const result = intervalTriggerSchema.safeParse({ interval_minutes: NaN })
      expect(result.success).toBe(false)
    })

    it('rejects undefined', () => {
      const result = intervalTriggerSchema.safeParse({})
      expect(result.success).toBe(false)
    })

    it('rejects null', () => {
      const result = intervalTriggerSchema.safeParse({ interval_minutes: null })
      expect(result.success).toBe(false)
    })
  })
})
```

**Step 3: Run tests to verify they pass**

```bash
cd webui/frontend && npx vitest run src/schemas/scheduler/__tests__/interval.test.ts
```

Expected: All tests PASS.

**Step 4: Commit**

```bash
git add webui/frontend/src/schemas/scheduler/__tests__/interval.test.ts
git commit -m "test(#446): add interval trigger schema tests"
```

---

### Task 3: Migrate the component to TypeScript + react-hook-form

**Files:**
- Delete: `webui/frontend/src/components/scheduler/ScheduleEditor/IntervalTriggerForm.jsx`
- Create: `webui/frontend/src/components/scheduler/ScheduleEditor/IntervalTriggerForm.tsx`

**Step 1: Create IntervalTriggerForm.tsx**

Delete the old `.jsx` and create `webui/frontend/src/components/scheduler/ScheduleEditor/IntervalTriggerForm.tsx`:

```tsx
import { useEffect, useMemo, useRef } from 'react'
import { useForm, Controller, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import type { Resolver } from 'react-hook-form'
import {
  intervalTriggerSchema,
  type IntervalTriggerFormData,
} from '../../../schemas/scheduler/interval'
import { SCHEDULE_LIMITS, DAYS_OF_WEEK } from './constants'
import TimeWindowInput from './TimeWindowInput'
import DaysOfWeekSelector from './DaysOfWeekSelector'

// ── Types ──────────────────────────────────────────────────────────────

interface TimeWindow {
  start_time: string
  end_time: string
  start_offset_minutes?: number
  end_offset_minutes?: number
}

interface IntervalTriggerValue {
  interval_minutes: number
  time_window: TimeWindow
  days_of_week: number[] | null
}

interface IntervalTriggerFormProps {
  value?: IntervalTriggerValue
  onChange: (value: IntervalTriggerValue) => void
  disabled?: boolean
  errors?: Record<string, string | Record<string, string>>
}

// ── Constants ──────────────────────────────────────────────────────────

const DEFAULT_VALUE: IntervalTriggerValue = {
  interval_minutes: 60,
  time_window: {
    start_time: '',
    end_time: '',
    start_offset_minutes: 0,
    end_offset_minutes: 0,
  },
  days_of_week: null,
}

const QUICK_PRESETS = [
  { label: '15 min', value: 15 },
  { label: '30 min', value: 30 },
  { label: '60 min', value: 60 },
  { label: '2 hours', value: 120 },
  { label: '4 hours', value: 240 },
] as const

// ── Formatting helpers (pure functions, no React state) ────────────────

function formatInterval(minutes: number): string {
  if (!minutes) return 'Every'
  if (minutes < 60) {
    return `Every ${minutes} minute${minutes !== 1 ? 's' : ''}`
  } else if (minutes % 60 === 0) {
    const hours = minutes / 60
    return `Every ${hours} hour${hours !== 1 ? 's' : ''}`
  }
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return `Every ${hours}h ${mins}m`
}

function formatTimeWindow(
  timeWindow: TimeWindow | undefined,
): string {
  if (!timeWindow || !timeWindow.start_time || !timeWindow.end_time) return ''

  const formatTime = (time: string, offset?: number): string => {
    if (!/^\d{2}:\d{2}$/.test(time)) {
      const formattedEvent = time.replace(/_/g, ' ')
      if (offset && offset !== 0) {
        const sign = offset > 0 ? '+' : ''
        return `${formattedEvent}${sign}${offset}`
      }
      return formattedEvent
    }
    return time
  }

  const startText = formatTime(timeWindow.start_time, timeWindow.start_offset_minutes)
  const endText = formatTime(timeWindow.end_time, timeWindow.end_offset_minutes)
  return `from ${startText} to ${endText}`
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

// Zod 4 + @hookform/resolvers type workaround
// TODO: remove cast when resolvers#800 is fixed
// Upstream: https://github.com/react-hook-form/resolvers/issues/800
const resolver = zodResolver(
  intervalTriggerSchema as unknown as Parameters<typeof zodResolver>[0],
) as unknown as Resolver<IntervalTriggerFormData>

export default function IntervalTriggerForm({
  value = DEFAULT_VALUE,
  onChange,
  disabled = false,
  errors: parentErrors = {},
}: IntervalTriggerFormProps) {
  // Stable callback ref — prevents useWatch effect from re-running when
  // parent passes an inline arrow function as onChange.
  const onChangeRef = useRef(onChange)
  onChangeRef.current = onChange

  // Track last interval propagated to parent, so prop-sync can distinguish
  // "our own update echoing back" from "external update" (e.g., preset click).
  const lastPropagatedRef = useRef(value.interval_minutes)

  const {
    control,
    reset,
    formState: { errors },
  } = useForm<IntervalTriggerFormData>({
    resolver,
    defaultValues: { interval_minutes: value.interval_minutes },
    mode: 'onChange',
  })

  // Prop sync: reset form when interval_minutes changes externally
  // (e.g., preset button click, parent state change)
  useEffect(() => {
    if (value.interval_minutes !== lastPropagatedRef.current) {
      lastPropagatedRef.current = value.interval_minutes
      reset({ interval_minutes: value.interval_minutes })
    }
  }, [value.interval_minutes, reset])

  // Propagate validated form changes → parent
  const watched = useWatch({ control })
  useEffect(() => {
    const current = watched.interval_minutes
    if (current === undefined) return
    // Skip if value matches props (avoids cycle from prop sync)
    if (current === value.interval_minutes) return
    // Only propagate valid values
    const result = intervalTriggerSchema.safeParse({ interval_minutes: current })
    if (!result.success) return
    lastPropagatedRef.current = current
    onChangeRef.current({ ...value, interval_minutes: current })
  }, [watched.interval_minutes, value])

  // Preset buttons bypass the form — call onChange directly
  const handlePresetClick = (presetValue: number) => {
    onChangeRef.current({ ...value, interval_minutes: presetValue })
  }

  const handleTimeWindowChange = (newTimeWindow: TimeWindow) => {
    onChangeRef.current({ ...value, time_window: newTimeWindow })
  }

  const handleDaysChange = (newDays: number[] | null) => {
    onChangeRef.current({ ...value, days_of_week: newDays })
  }

  const previewText = useMemo(() => {
    const intervalText = formatInterval(value.interval_minutes)
    const windowText = formatTimeWindow(value.time_window)
    const daysText = formatDays(value.days_of_week)

    let preview = intervalText
    if (windowText) preview += ` ${windowText}`
    if (daysText) preview += ` on ${daysText}`
    return preview
  }, [value.interval_minutes, value.time_window, value.days_of_week])

  return (
    <div className="space-y-6">
      {/* Header */}
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
        Interval Configuration
      </h3>

      {/* Interval Input */}
      <div>
        <label
          htmlFor="interval_minutes"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Repeat every:
        </label>
        <div className="flex items-center gap-2">
          <Controller
            name="interval_minutes"
            control={control}
            render={({ field }) => (
              <input
                id="interval_minutes"
                type="number"
                min={SCHEDULE_LIMITS.MIN_INTERVAL_MINUTES}
                max={SCHEDULE_LIMITS.MAX_INTERVAL_MINUTES}
                value={field.value}
                onChange={(e) => {
                  const raw = e.target.value
                  field.onChange(raw === '' ? '' : Number(raw))
                }}
                onBlur={field.onBlur}
                ref={field.ref}
                disabled={disabled}
                className="w-32 rounded-md border border-gray-300 dark:border-gray-600
                         bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent
                         disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label="Interval in minutes"
                aria-invalid={!!errors.interval_minutes}
                aria-describedby={
                  errors.interval_minutes ? 'interval_minutes-error' : undefined
                }
              />
            )}
          />
          <span className="text-sm text-gray-700 dark:text-gray-300">minutes</span>
        </div>
        {(errors.interval_minutes?.message ||
          (parentErrors.interval_minutes &&
            typeof parentErrors.interval_minutes === 'string')) && (
          <p
            id="interval_minutes-error"
            role="alert"
            className="mt-1 text-sm text-red-600 dark:text-red-400"
          >
            {errors.interval_minutes?.message ||
              (parentErrors.interval_minutes as string)}
          </p>
        )}
      </div>

      {/* Quick Presets */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Quick presets:
        </label>
        <div className="flex flex-wrap gap-2">
          {QUICK_PRESETS.map((preset) => (
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
                  value.interval_minutes === preset.value
                    ? 'bg-blue-500 text-white hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
                }
                ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              `}
              aria-label={`Set interval to ${preset.label}`}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      {/* Time Window */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
          Time Window:
        </label>
        <TimeWindowInput
          value={value.time_window}
          onChange={handleTimeWindowChange}
          disabled={disabled}
          showSolarEvents={true}
          errors={(parentErrors.time_window as Record<string, string>) || {}}
        />
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

**Step 2: Delete the old .jsx file**

```bash
rm webui/frontend/src/components/scheduler/ScheduleEditor/IntervalTriggerForm.jsx
```

**Step 3: Run tsc to verify no type errors**

```bash
cd webui/frontend && npx tsc --noEmit
```

Expected: No errors (or only pre-existing errors unrelated to this file).

**Step 4: Commit**

```bash
git add -A webui/frontend/src/components/scheduler/ScheduleEditor/IntervalTriggerForm.tsx
git add webui/frontend/src/components/scheduler/ScheduleEditor/IntervalTriggerForm.jsx
git commit -m "feat(#446): migrate IntervalTriggerForm to react-hook-form + Zod + TypeScript"
```

---

### Task 4: Migrate the component tests

**Files:**
- Delete: `webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/IntervalTriggerForm.test.jsx`
- Create: `webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/IntervalTriggerForm.test.tsx`

**Step 1: Create IntervalTriggerForm.test.tsx**

Delete the old `.test.jsx` and create `webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/IntervalTriggerForm.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import IntervalTriggerForm from '../IntervalTriggerForm'
import { SCHEDULE_LIMITS } from '../constants'

// ── Mock child components ──────────────────────────────────────────────

vi.mock('../TimeWindowInput', () => ({
  default: ({
    value,
    onChange,
    disabled,
    errors,
  }: {
    value: { start_time: string; end_time: string }
    onChange: (v: Record<string, string>) => void
    disabled: boolean
    errors: Record<string, string>
  }) => (
    <div data-testid="time-window-input">
      <input
        data-testid="time-window-start"
        value={value.start_time}
        onChange={(e) => onChange({ ...value, start_time: e.target.value })}
        disabled={disabled}
      />
      <input
        data-testid="time-window-end"
        value={value.end_time}
        onChange={(e) => onChange({ ...value, end_time: e.target.value })}
        disabled={disabled}
      />
      {errors.start_time && (
        <span data-testid="error-start">{errors.start_time}</span>
      )}
      {errors.end_time && <span data-testid="error-end">{errors.end_time}</span>}
    </div>
  ),
}))

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

const defaultValue = {
  interval_minutes: 60,
  time_window: {
    start_time: '21:00',
    end_time: '05:00',
    start_offset_minutes: 0,
    end_offset_minutes: 0,
  },
  days_of_week: null as number[] | null,
}

// ── Tests ──────────────────────────────────────────────────────────────

describe('IntervalTriggerForm', () => {
  let mockOnChange: ReturnType<typeof vi.fn>

  beforeEach(() => {
    mockOnChange = vi.fn()
  })

  describe('Rendering', () => {
    it('renders with default values', () => {
      render(<IntervalTriggerForm onChange={mockOnChange} />)

      expect(screen.getByText('Interval Configuration')).toBeInTheDocument()
      expect(screen.getByLabelText('Interval in minutes')).toBeInTheDocument()
      expect(screen.getByText('Quick presets:')).toBeInTheDocument()
      expect(screen.getByText('Time Window:')).toBeInTheDocument()
      expect(screen.getByText('Preview:')).toBeInTheDocument()
    })

    it('renders with provided value', () => {
      const value = {
        interval_minutes: 120,
        time_window: {
          start_time: '21:00',
          end_time: '05:00',
          start_offset_minutes: 0,
          end_offset_minutes: 0,
        },
        days_of_week: [0, 1, 2],
      }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      const intervalInput = screen.getByLabelText('Interval in minutes')
      expect(intervalInput).toHaveValue(120)
    })

    it('renders all quick preset buttons', () => {
      render(<IntervalTriggerForm onChange={mockOnChange} />)

      expect(screen.getByLabelText('Set interval to 15 min')).toBeInTheDocument()
      expect(screen.getByLabelText('Set interval to 30 min')).toBeInTheDocument()
      expect(screen.getByLabelText('Set interval to 60 min')).toBeInTheDocument()
      expect(screen.getByLabelText('Set interval to 2 hours')).toBeInTheDocument()
      expect(screen.getByLabelText('Set interval to 4 hours')).toBeInTheDocument()
    })

    it('renders TimeWindowInput component', () => {
      render(<IntervalTriggerForm onChange={mockOnChange} />)
      expect(screen.getByTestId('time-window-input')).toBeInTheDocument()
    })

    it('renders DaysOfWeekSelector component', () => {
      render(<IntervalTriggerForm onChange={mockOnChange} />)
      expect(screen.getByTestId('days-of-week-selector')).toBeInTheDocument()
    })
  })

  describe('Interval Input (react-hook-form + Zod)', () => {
    it('propagates valid interval change to parent', async () => {
      const user = userEvent.setup()
      const value = { ...defaultValue, interval_minutes: 60 }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      const input = screen.getByLabelText('Interval in minutes')
      await user.clear(input)
      await user.type(input, '90')

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({ interval_minutes: 90 }),
        )
      })
    })

    it('respects min and max interval attributes', () => {
      render(<IntervalTriggerForm onChange={mockOnChange} />)

      const intervalInput = screen.getByLabelText('Interval in minutes')
      expect(intervalInput).toHaveAttribute(
        'min',
        String(SCHEDULE_LIMITS.MIN_INTERVAL_MINUTES),
      )
      expect(intervalInput).toHaveAttribute(
        'max',
        String(SCHEDULE_LIMITS.MAX_INTERVAL_MINUTES),
      )
    })

    it('shows Zod error for out-of-range value', async () => {
      const user = userEvent.setup()

      render(
        <IntervalTriggerForm
          value={defaultValue}
          onChange={mockOnChange}
        />,
      )

      const input = screen.getByLabelText('Interval in minutes')
      await user.clear(input)
      await user.type(input, '0')

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })
    })

    it('does not propagate invalid values to parent', async () => {
      const user = userEvent.setup()

      render(
        <IntervalTriggerForm
          value={defaultValue}
          onChange={mockOnChange}
        />,
      )

      const input = screen.getByLabelText('Interval in minutes')
      await user.clear(input)
      await user.type(input, '0')

      // onChange should not be called with an invalid value
      await waitFor(() => {
        const calls = mockOnChange.mock.calls
        const invalidCall = calls.find(
          (c: [{ interval_minutes: number }]) => c[0].interval_minutes === 0,
        )
        expect(invalidCall).toBeUndefined()
      })
    })

    it('shows parent-provided error message', () => {
      const errors = {
        interval_minutes: 'Server validation failed',
      }

      render(
        <IntervalTriggerForm
          onChange={mockOnChange}
          errors={errors}
        />,
      )

      expect(screen.getByText('Server validation failed')).toBeInTheDocument()
    })

    it('accepts boundary value MIN_INTERVAL_MINUTES', async () => {
      const user = userEvent.setup()
      const value = { ...defaultValue, interval_minutes: 60 }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      const input = screen.getByLabelText('Interval in minutes')
      await user.clear(input)
      await user.type(input, String(SCHEDULE_LIMITS.MIN_INTERVAL_MINUTES))

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({
            interval_minutes: SCHEDULE_LIMITS.MIN_INTERVAL_MINUTES,
          }),
        )
      })
    })

    it('accepts boundary value MAX_INTERVAL_MINUTES', async () => {
      const user = userEvent.setup()
      const value = { ...defaultValue, interval_minutes: 60 }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      const input = screen.getByLabelText('Interval in minutes')
      await user.clear(input)
      await user.type(input, String(SCHEDULE_LIMITS.MAX_INTERVAL_MINUTES))

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({
            interval_minutes: SCHEDULE_LIMITS.MAX_INTERVAL_MINUTES,
          }),
        )
      })
    })
  })

  describe('Quick Preset Buttons', () => {
    it('sets interval to 15 minutes when 15 min preset clicked', () => {
      const value = { ...defaultValue, interval_minutes: 60 }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      fireEvent.click(screen.getByLabelText('Set interval to 15 min'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        interval_minutes: 15,
      })
    })

    it('sets interval to 30 minutes when 30 min preset clicked', () => {
      const value = { ...defaultValue, interval_minutes: 60 }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      fireEvent.click(screen.getByLabelText('Set interval to 30 min'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        interval_minutes: 30,
      })
    })

    it('sets interval to 60 minutes when 60 min preset clicked', () => {
      const value = { ...defaultValue, interval_minutes: 30 }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      fireEvent.click(screen.getByLabelText('Set interval to 60 min'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        interval_minutes: 60,
      })
    })

    it('sets interval to 120 minutes when 2 hours preset clicked', () => {
      const value = { ...defaultValue, interval_minutes: 60 }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      fireEvent.click(screen.getByLabelText('Set interval to 2 hours'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        interval_minutes: 120,
      })
    })

    it('sets interval to 240 minutes when 4 hours preset clicked', () => {
      const value = { ...defaultValue, interval_minutes: 60 }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      fireEvent.click(screen.getByLabelText('Set interval to 4 hours'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        interval_minutes: 240,
      })
    })

    it('highlights selected preset', () => {
      const value = { ...defaultValue, interval_minutes: 60 }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      const preset60 = screen.getByLabelText('Set interval to 60 min')
      expect(preset60).toHaveClass('bg-blue-500')
    })
  })

  describe('TimeWindowInput Integration', () => {
    it('passes time_window value to TimeWindowInput', () => {
      const value = {
        interval_minutes: 60,
        time_window: {
          start_time: '21:00',
          end_time: '05:00',
          start_offset_minutes: 30,
          end_offset_minutes: -15,
        },
        days_of_week: null,
      }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(screen.getByTestId('time-window-start')).toHaveValue('21:00')
      expect(screen.getByTestId('time-window-end')).toHaveValue('05:00')
    })

    it('calls onChange when TimeWindowInput changes', () => {
      const value = {
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      fireEvent.change(screen.getByTestId('time-window-start'), {
        target: { value: '20:00' },
      })

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        time_window: { ...value.time_window, start_time: '20:00' },
      })
    })

    it('passes errors to TimeWindowInput', () => {
      const errors = {
        time_window: {
          start_time: 'Invalid start time',
          end_time: 'Invalid end time',
        },
      }

      render(
        <IntervalTriggerForm onChange={mockOnChange} errors={errors} />,
      )

      expect(screen.getByTestId('error-start')).toHaveTextContent(
        'Invalid start time',
      )
      expect(screen.getByTestId('error-end')).toHaveTextContent(
        'Invalid end time',
      )
    })

    it('passes disabled state to TimeWindowInput', () => {
      render(
        <IntervalTriggerForm onChange={mockOnChange} disabled={true} />,
      )

      expect(screen.getByTestId('time-window-start')).toBeDisabled()
      expect(screen.getByTestId('time-window-end')).toBeDisabled()
    })
  })

  describe('DaysOfWeekSelector Integration', () => {
    it('passes days_of_week value to DaysOfWeekSelector', () => {
      const value = {
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: [0, 2, 4],
      }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(screen.getByTestId('days-of-week-selector')).toBeInTheDocument()
    })

    it('calls onChange when DaysOfWeekSelector changes', () => {
      const value = {
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      fireEvent.click(screen.getByTestId('toggle-monday'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        days_of_week: [1, 2, 3, 4, 5, 6],
      })
    })

    it('passes disabled state to DaysOfWeekSelector', () => {
      render(
        <IntervalTriggerForm onChange={mockOnChange} disabled={true} />,
      )

      expect(screen.getByTestId('toggle-monday')).toBeDisabled()
    })
  })

  describe('Preview Text Generation', () => {
    it('generates preview for minutes interval with fixed time window', () => {
      const value = {
        interval_minutes: 30,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText('Every 30 minutes from 21:00 to 05:00'),
      ).toBeInTheDocument()
    })

    it('generates preview for hour interval', () => {
      const value = {
        interval_minutes: 120,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText('Every 2 hours from 21:00 to 05:00'),
      ).toBeInTheDocument()
    })

    it('generates preview with solar events', () => {
      const value = {
        interval_minutes: 60,
        time_window: {
          start_time: 'sunset',
          end_time: 'sunrise',
          start_offset_minutes: 30,
          end_offset_minutes: -15,
        },
        days_of_week: null,
      }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText('Every 1 hour from sunset+30 to sunrise-15'),
      ).toBeInTheDocument()
    })

    it('generates preview with specific days', () => {
      const value = {
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: [0, 2, 4],
      }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText(
          'Every 1 hour from 21:00 to 05:00 on Mon, Wed, Fri',
        ),
      ).toBeInTheDocument()
    })

    it('generates preview without days when all days selected', () => {
      const value = {
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText('Every 1 hour from 21:00 to 05:00'),
      ).toBeInTheDocument()
    })

    it('handles singular "minute" in preview', () => {
      const value = {
        interval_minutes: 1,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText('Every 1 minute from 21:00 to 05:00'),
      ).toBeInTheDocument()
    })

    it('formats mixed hours and minutes in preview', () => {
      const value = {
        interval_minutes: 90,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      expect(
        screen.getByText('Every 1h 30m from 21:00 to 05:00'),
      ).toBeInTheDocument()
    })
  })

  describe('Disabled State', () => {
    it('disables interval input when disabled prop is true', () => {
      render(
        <IntervalTriggerForm onChange={mockOnChange} disabled={true} />,
      )

      expect(screen.getByLabelText('Interval in minutes')).toBeDisabled()
    })

    it('disables preset buttons when disabled prop is true', () => {
      render(
        <IntervalTriggerForm onChange={mockOnChange} disabled={true} />,
      )

      expect(screen.getByLabelText('Set interval to 15 min')).toBeDisabled()
      expect(screen.getByLabelText('Set interval to 30 min')).toBeDisabled()
    })

    it('does not disable inputs when disabled prop is false', () => {
      render(
        <IntervalTriggerForm onChange={mockOnChange} disabled={false} />,
      )

      expect(screen.getByLabelText('Interval in minutes')).not.toBeDisabled()
    })
  })

  describe('Dark Mode Styling', () => {
    it('applies dark mode classes to interval input', () => {
      render(<IntervalTriggerForm onChange={mockOnChange} />)

      const intervalInput = screen.getByLabelText('Interval in minutes')
      expect(intervalInput).toHaveClass(
        'dark:bg-gray-800',
        'dark:text-white',
        'dark:border-gray-600',
      )
    })

    it('applies dark mode classes to preset buttons', () => {
      render(<IntervalTriggerForm onChange={mockOnChange} />)

      const preset15 = screen.getByLabelText('Set interval to 15 min')
      expect(preset15).toHaveClass('dark:bg-gray-700', 'dark:text-gray-300')
    })

    it('applies dark mode classes to labels', () => {
      render(<IntervalTriggerForm onChange={mockOnChange} />)

      expect(screen.getByText('Interval Configuration')).toHaveClass(
        'dark:text-white',
      )
    })

    it('applies dark mode classes to preview text', () => {
      const value = {
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      const previewText = screen.getByText(
        'Every 1 hour from 21:00 to 05:00',
      )
      expect(previewText).toHaveClass('dark:text-gray-300', 'dark:bg-gray-800')
    })
  })

  describe('onChange Callback', () => {
    it('calls onChange with complete trigger object when time window changes', () => {
      const value = {
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      fireEvent.change(screen.getByTestId('time-window-start'), {
        target: { value: '20:00' },
      })

      expect(mockOnChange).toHaveBeenCalledWith({
        interval_minutes: 60,
        time_window: { start_time: '20:00', end_time: '05:00' },
        days_of_week: null,
      })
    })

    it('calls onChange with complete trigger object when days change', () => {
      const value = {
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      }

      render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      fireEvent.click(screen.getByTestId('toggle-all-days'))

      expect(mockOnChange).toHaveBeenCalledWith({
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      })
    })
  })

  describe('Prop sync (external value changes)', () => {
    it('updates input when value prop changes externally', () => {
      const value = { ...defaultValue, interval_minutes: 60 }

      const { rerender } = render(
        <IntervalTriggerForm value={value} onChange={mockOnChange} />,
      )

      // Simulate parent changing value (e.g., from a preset in parent)
      rerender(
        <IntervalTriggerForm
          value={{ ...value, interval_minutes: 120 }}
          onChange={mockOnChange}
        />,
      )

      const input = screen.getByLabelText('Interval in minutes')
      expect(input).toHaveValue(120)
    })
  })
})
```

**Step 2: Delete the old test file**

```bash
rm webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/IntervalTriggerForm.test.jsx
```

**Step 3: Run the tests**

```bash
cd webui/frontend && npx vitest run src/components/scheduler/ScheduleEditor/__tests__/IntervalTriggerForm.test.tsx
```

Expected: All tests PASS. Some tests may need minor adjustments due to async react-hook-form behavior — fix any failures before committing.

**Step 4: Commit**

```bash
git add -A webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/IntervalTriggerForm.test.tsx
git add webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/IntervalTriggerForm.test.jsx
git commit -m "test(#446): migrate IntervalTriggerForm tests to TypeScript"
```

---

### Task 5: Update schema index and run full test suite

**Files:**
- Modify: `webui/frontend/src/schemas/index.ts`

**Step 1: Add interval schema re-export to index.ts**

Add to the end of `webui/frontend/src/schemas/index.ts`:

```typescript
export { intervalTriggerSchema } from './scheduler/interval'
export type { IntervalTriggerFormData } from './scheduler/interval'
```

**Step 2: Run tsc**

```bash
cd webui/frontend && npx tsc --noEmit
```

Expected: No type errors.

**Step 3: Run the full affected test files**

```bash
cd webui/frontend && npx vitest run src/schemas/scheduler/__tests__/interval.test.ts src/components/scheduler/ScheduleEditor/__tests__/IntervalTriggerForm.test.tsx
```

Expected: All tests PASS.

**Step 4: Commit**

```bash
git add webui/frontend/src/schemas/index.ts
git commit -m "feat(#446): re-export interval trigger schema from index"
```

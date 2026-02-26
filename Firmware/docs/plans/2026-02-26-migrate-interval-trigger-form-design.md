# Migrate IntervalTriggerForm Design

**Issue**: #446
**Date**: 2026-02-26
**Status**: Design approved

## Decision Summary

| Decision | Choice |
|---|---|
| Pattern | Pattern 2: Controlled (parent-owned state) |
| Schema scope | `interval_minutes` only — TimeWindowInput/DaysOfWeekSelector are pass-through |
| Schema file | `src/schemas/scheduler/interval.ts` |
| Validation mode | `onChange` (live feedback, matches current UX) |
| Prop sync | `useEffect` resets form when `value.interval_minutes` changes externally |
| Presets | Bypass form, call `onChange` directly; prop-sync resets form |
| Sub-components | TimeWindowInput/DaysOfWeekSelector unchanged (own migrations: #449, future) |

## Schema: `src/schemas/scheduler/interval.ts`

Minimal schema — validates only the field this component owns:

```typescript
import { z } from 'zod'
import { SCHEDULE_LIMITS } from '../../components/scheduler/ScheduleEditor/constants'

export const intervalTriggerSchema = z.object({
  interval_minutes: z
    .number({ invalid_type_error: 'Interval must be a number' })
    .int('Interval must be a whole number')
    .min(SCHEDULE_LIMITS.MIN_INTERVAL_MINUTES,
      `Interval must be at least ${SCHEDULE_LIMITS.MIN_INTERVAL_MINUTES} minute`)
    .max(SCHEDULE_LIMITS.MAX_INTERVAL_MINUTES,
      `Interval cannot exceed ${SCHEDULE_LIMITS.MAX_INTERVAL_MINUTES} minutes`),
})

export type IntervalTriggerFormData = z.infer<typeof intervalTriggerSchema>
```

Constants imported from existing `constants.js` — no duplication.

## Component: `IntervalTriggerForm.tsx`

### TypeScript interfaces (replaces PropTypes)

```typescript
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
  value: IntervalTriggerValue
  onChange: (value: IntervalTriggerValue) => void
  disabled?: boolean
  errors?: Record<string, string | Record<string, string>>
}
```

### react-hook-form integration

- `useForm<IntervalTriggerFormData>` with `zodResolver`, `mode: 'onChange'`, `defaultValues: { interval_minutes: value.interval_minutes }`
- `Controller` for `interval_minutes` input (string↔number coercion)
- `useWatch` + `useEffect` propagates validated changes to parent via `onChange`
- Prop sync: `useEffect` resets form when `value.interval_minutes` changes externally

### Preset buttons

Presets call `onChange({ ...value, interval_minutes: presetValue })` directly. The prop-sync effect resets the form to match — no need to route through react-hook-form.

### Preserved unchanged

- TimeWindowInput and DaysOfWeekSelector — pass-through child components
- Preview text logic (formatInterval, formatTimeWindow, formatDays)
- All CSS classes and layout
- Parent contract (onChange called with complete value object)

### Removed

- `useState` for `intervalError`
- `validateNumericInput()` import
- `NUMERIC_ERRORS` import
- `PropTypes` block
- Manual error display logic (replaced by `formState.errors`)

## Testing

### Schema tests (`src/schemas/scheduler/__tests__/interval.test.ts`)

Pure Zod tests — no React rendering:
- Valid values: 1 (min), 60 (default), 10080 (max)
- Boundary values: 0 (below min), 10081 (above max)
- Type rejection: NaN, float, string, undefined
- Error message assertions

### Component tests (`__tests__/IntervalTriggerForm.test.tsx`)

Migrated from existing `.test.jsx`:
- Same mock strategy for TimeWindowInput and DaysOfWeekSelector
- Validation: type invalid value → assert error message appears
- Presets: click preset → assert onChange called with correct interval_minutes
- Prop sync: re-render with new value prop → assert form input updates
- `user.type()` replaces `fireEvent.change()` where appropriate
- Remove tests for manual validateNumericInput logic (replaced by Zod)

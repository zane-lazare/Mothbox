# Migrate SolarTriggerForm Design

**Issue**: #447
**Date**: 2026-02-26
**Status**: Design approved

## Decision Summary

| Decision | Choice |
|---|---|
| Pattern | Pattern 2: Controlled (parent-owned state) |
| Schema scope | `solar_event` + `offset_minutes` — DaysOfWeekSelector is pass-through |
| Schema file | `src/schemas/scheduler/solar.ts` |
| Validation mode | `onChange` (live feedback, matches current UX) |
| Prop sync | `useEffect` resets form when value changes externally |
| Presets | Bypass form, call `onChange` directly; prop-sync resets form |
| Sub-components | DaysOfWeekSelector unchanged (own migration: future) |

## Schema: `src/schemas/scheduler/solar.ts`

Two validated fields — solar event enum + offset number:

```typescript
import { z } from 'zod'
import { SCHEDULE_LIMITS, SOLAR_EVENTS } from '../../components/scheduler/ScheduleEditor/constants'

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

Constants imported from existing `constants.js` — no duplication.

## Component: `SolarTriggerForm.tsx`

### TypeScript interfaces (replaces PropTypes)

```typescript
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
```

### react-hook-form integration

- `useForm<SolarTriggerFormData>` with `zodResolver`, `mode: 'onChange'`, `defaultValues: { solar_event: value.solar_event, offset_minutes: value.offset_minutes }`
- `Controller` for `solar_event` (select element) and `offset_minutes` (number input)
- `useWatch` + `useEffect` propagates validated changes to parent via `onChange`
- Prop sync: `useEffect` resets form when value changes externally
- `valueRef` + `onChangeRef` + `lastPropagatedRef` pattern (same as IntervalTriggerForm)

### Preset buttons

Presets call `onChange({ ...valueRef.current, offset_minutes: presetValue })` directly. The prop-sync effect resets the form to match.

### Preserved unchanged

- DaysOfWeekSelector — pass-through child component
- Preview text logic (formatOffset, formatDays, getEventLabel, getEventDescription)
- OFFSET_PRESETS (promoted to module scope `as const`)
- All CSS classes and layout
- Parent contract (onChange called with complete value object)

### Removed

- `validateNumericInput` import and usage
- `PropTypes` block
- Manual validation in `handleOffsetChange`

## Testing

### Schema tests (`src/schemas/scheduler/__tests__/solar.test.ts`)

Pure Zod tests — no React rendering:
- Valid solar events: all 14 values from SOLAR_EVENTS
- Invalid solar event: arbitrary string
- Offset boundaries: ±1440 valid, ±1441 rejected, 0 valid
- Type rejection: NaN, float, string for offset_minutes
- Error message assertions

### Component tests (`__tests__/SolarTriggerForm.test.tsx`)

Migrated from existing `.test.jsx`:
- Same mock strategy for DaysOfWeekSelector
- Validation: type invalid offset → assert error message appears
- Presets: click preset → assert onChange called with correct offset_minutes
- Prop sync: re-render with new value prop → assert form inputs update
- `userEvent` replaces `fireEvent` where appropriate
- Remove tests for manual validateNumericInput logic (replaced by Zod)
- Import `SolarTriggerValue` from component (no local type duplication)

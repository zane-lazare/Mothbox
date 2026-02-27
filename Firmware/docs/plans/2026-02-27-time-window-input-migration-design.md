# TimeWindowInput Migration Design (#449)

## Overview

Migrate `TimeWindowInput.jsx` to TypeScript with react-hook-form + Zod validation, following the Controlled (Pattern 2) migration pattern established by SolarTriggerForm (#447) and MoonPhaseTriggerForm (#448).

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Cross-field validation | Warning only (no `.refine()`) | Overnight windows are valid; mixed mode (fixed + solar) can't be compared; solar-solar needs ephemeris data frontend lacks |
| Offset range | ±120 minutes | Matches existing component behavior; `SCHEDULE_LIMITS.MAX_OFFSET_MINUTES` (1440) is for standalone solar triggers |
| Schema shape | Flat `z.object()` with custom time validators | Matches `TimeWindowValue` interface exactly; consistent with `solar.ts` and `moon-phase.ts` patterns |
| Mode derivation | Computed from `watch()`, not stored | `startIsFixedTime = TIME_FORMAT_REGEX.test(watch('start_time'))` — no useState, no form fields for mode |

## Schema (`src/schemas/scheduler/time-window.ts`)

```typescript
import { z } from 'zod/v4'
import {
  TIME_FORMAT_REGEX,
  SOLAR_EVENTS,
} from '../../components/scheduler/ScheduleEditor/constants'

const TIME_WINDOW_MAX_OFFSET_MINUTES = 120

const solarEventValues = SOLAR_EVENTS.map((e) => e.value) as [string, ...string[]]

const timeValue = z
  .string({ error: 'Time is required' })
  .refine(
    (v) => TIME_FORMAT_REGEX.test(v) || solarEventValues.includes(v),
    'Must be valid HH:MM time or solar event'
  )

export const timeWindowSchema = z.object({
  start_time: timeValue,
  end_time: timeValue,
  start_offset_minutes: z
    .number({ error: 'Offset must be a number' })
    .int('Offset must be a whole number')
    .min(
      -TIME_WINDOW_MAX_OFFSET_MINUTES,
      `Offset must be at least ${-TIME_WINDOW_MAX_OFFSET_MINUTES} minutes`
    )
    .max(
      TIME_WINDOW_MAX_OFFSET_MINUTES,
      `Offset cannot exceed ${TIME_WINDOW_MAX_OFFSET_MINUTES} minutes`
    )
    .default(0),
  end_offset_minutes: z
    .number({ error: 'Offset must be a number' })
    .int('Offset must be a whole number')
    .min(
      -TIME_WINDOW_MAX_OFFSET_MINUTES,
      `Offset must be at least ${-TIME_WINDOW_MAX_OFFSET_MINUTES} minutes`
    )
    .max(
      TIME_WINDOW_MAX_OFFSET_MINUTES,
      `Offset cannot exceed ${TIME_WINDOW_MAX_OFFSET_MINUTES} minutes`
    )
    .default(0),
})

export type TimeWindowValue = z.infer<typeof timeWindowSchema>
```

**Key points:**
- `timeValue` uses `.refine()` to accept either `HH:MM` format or valid solar event strings
- Offsets always present with `default(0)`, validated ±120 in both modes
- `TIME_WINDOW_MAX_OFFSET_MINUTES` is a local constant (120), distinct from `SCHEDULE_LIMITS.MAX_OFFSET_MINUTES` (1440)
- `TimeWindowValue` type replaces the existing `TimeWindowInput.d.ts` declaration

## Component (`TimeWindowInput.tsx`)

### Internal form setup

```typescript
const { control, reset, trigger, formState: { errors }, watch, setValue } = useForm({
  resolver: zodResolver(timeWindowSchema),
  mode: 'onChange',
  defaultValues: value ?? { start_time: '', end_time: '', start_offset_minutes: 0, end_offset_minutes: 0 },
})
```

### Mode derivation (replaces useState)

```typescript
const startTime = watch('start_time')
const endTime = watch('end_time')
const startIsFixedTime = TIME_FORMAT_REGEX.test(startTime)
const endIsFixedTime = TIME_FORMAT_REGEX.test(endTime)
```

No `useState` for mode — computed directly from watched values.

### Cycle prevention

Same `valueRef` / `onChangeRef` / `lastPropagatedRef` pattern as MoonPhaseTriggerForm:

1. **Prop-sync effect:** When incoming `value` differs from `lastPropagatedRef`, `reset()` the form
2. **Propagation effect:** `useWatch` all 4 fields → `trigger()` → if valid, call `onChangeRef.current(data)` and update `lastPropagatedRef`

### Mode switching

When user clicks radio to switch modes:
- Fixed → Solar: `setValue('start_time', SOLAR_EVENTS[0].value)` (resets to first solar event)
- Solar → Fixed: `setValue('start_time', '18:00')` (resets to default time)

This triggers the watch → propagation pipeline naturally.

### Mixed time warning

Kept as UI-only computed value:
```typescript
const mixedWarning = getMixedTimeWindowWarning(startIsFixedTime, endIsFixedTime)
```

No Zod `.refine()` — displayed as an informational message, not a validation error.

### Error display

Wire both Zod errors AND `parentErrors` for all fields:
- `parentErrors.start_time` → `aria-invalid` + `aria-describedby` on start time input
- `parentErrors.end_time` → `aria-invalid` + `aria-describedby` on end time input
- `parentErrors.general` → general error display area

Learning from #448 review: always check `errors.field || parentErrors.field` for aria attributes.

### Preserved behaviors

- Radio toggles (only when `showSolarEvents={true}`)
- Solar preview text (`getSolarPreviewText()`)
- All `aria-label` values unchanged
- `data-testid="time-window-start"` / `data-testid="time-window-end"`
- `id="start_offset"` / `id="end_offset"`
- HTML `min=-120` / `max=120` on offset inputs
- `disabled` prop disables all inputs

## Tests

### Schema tests (`src/schemas/scheduler/__tests__/time-window.test.ts`)

- Valid fixed times (HH:MM format): `"00:00"`, `"12:30"`, `"23:59"`
- Valid solar events: all 15 from `SOLAR_EVENTS`
- Invalid time strings: `"25:00"`, `"abc"`, empty string
- Offset validation: within ±120, rejects ±121, rejects non-integers
- Default values: offsets default to 0

### Component tests (`TimeWindowInput.test.tsx`)

Migrate all 41 existing tests. Add:
- Parent error wiring: `parentErrors.start_time`, `parentErrors.end_time`, `parentErrors.general` with `aria-invalid` and `aria-describedby`
- Prop-sync cycle prevention
- onChange propagation with valid data

## Cleanup

- Delete `TimeWindowInput.d.ts` — type now exported from schema
- Delete `TimeWindowInput.jsx` — replaced by `.tsx`
- Delete `TimeWindowInput.test.jsx` — replaced by `.test.tsx`
- Update barrel export in `ScheduleEditor/index.js` if needed

## Consumers

Two components import TimeWindowInput:

1. **`IntervalTriggerForm.tsx`** (already migrated) — passes `value.time_window` and casts `parentErrors.time_window` to `Record<string, string>`. No changes needed.
2. **`TriggerSelector/IntervalTriggerForm.jsx`** (not yet migrated) — uses TimeWindowInput without errors prop. No changes needed (JSX can import TSX).

## References

- MoonPhaseTriggerForm (#448): Best reference for the controlled-component RHF pattern
- SolarTriggerForm (#447): Schema pattern for solar event enum + offset validation
- IntervalTriggerForm (#444): Consumer that documents the `time-window.ts` schema expectation

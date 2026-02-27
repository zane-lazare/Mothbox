# PreConditionForm Migration Design

**Issue:** #450
**Parent:** #197 (Standardize form validation with react-hook-form + Zod)
**Date:** 2026-02-28

## Goal

Migrate PreConditionForm from manual useState/useEffect validation to react-hook-form + Zod, converting .jsx to .tsx. Follow the established Pattern 2 (Controlled) migration pattern.

## Current State

- **File:** `src/components/scheduler/ScheduleEditor/PreConditionForm.jsx` (319 lines)
- **Tests:** `__tests__/PreConditionForm.test.jsx` (872 lines, 60+ tests)
- **Fields:** sensor_type, comparison, threshold, cooldown_minutes, plus optional nested time_window (start_time, end_time)
- **Toggle:** Component has an enable/disable toggle that sends `null` to parent when off
- **Consumers:** RoutineCard.jsx, NewRoutineCard.jsx

## Design Decisions

1. **Keep inline time inputs** — The pre-condition's time window uses simple HH:MM-only inputs (no solar events, no offsets). Reusing TimeWindowInput would add unused UI.

2. **Fields-only schema** — The enable/disable toggle is component-level state, not a form field. Schema validates only the enabled fields. Toggle sends `null` to parent directly.

3. **Match current decimal behavior** — Threshold allows floats (min 0, no max). Cooldown allows floats (1-60 range). Preserves backward compatibility.

4. **Flat schema with `.refine()`** — Cross-field validation (`start_time !== end_time`) uses `.refine()` on the nested time_window sub-schema.

## Schema

```typescript
// src/schemas/scheduler/pre-condition.ts

const preConditionTimeWindowSchema = z.object({
  start_time: z.string({ error: 'Start time is required' })
    .regex(TIME_FORMAT_REGEX, 'Time must be in HH:MM format'),
  end_time: z.string({ error: 'End time is required' })
    .regex(TIME_FORMAT_REGEX, 'Time must be in HH:MM format'),
}).refine(
  (data) => data.start_time !== data.end_time,
  { message: 'Start and end times cannot be the same', path: ['end_time'] }
)

export const preConditionSchema = z.object({
  sensor_type: z.enum(['light', 'temperature'], { error: 'Invalid sensor type' }),
  comparison: z.enum(['lt', 'gt', 'eq'], { error: 'Invalid comparison' }),
  threshold: z.number({ error: 'Threshold must be a number' })
    .min(0, 'Threshold must be non-negative'),
  cooldown_minutes: z.number({ error: 'Cooldown must be a number' })
    .min(SCHEDULE_LIMITS.MIN_COOLDOWN_MINUTES, ...)
    .max(SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES, ...),
  time_window: preConditionTimeWindowSchema.nullable().default(null),
})
```

## Component Architecture

- **Toggle** outside form: Derived from `preCondition !== null`. Toggling off calls `onChange(null)` directly.
- **RHF form** with `zodResolver`, `mode: 'onChange'`, Controller-wrapped inputs.
- **Prop sync**: `valueRef` / `onChangeRef` / `lastPropagatedRef` pattern.
- **Propagation effect**: Watches all fields, `safeParse()` gates propagation.
- **Time window toggle**: Nested toggle inside form, bypasses RHF (like preset buttons).
- **Number input pattern**: `raw === '' ? NaN : Number(raw)` for onChange, `Number.isNaN(field.value) ? '' : field.value` for display.
- **All data-testid attributes preserved** with `routineIndex` suffix.
- **Parent error wiring**: `aria-invalid` and `aria-describedby`.

## Files

- **Create:** `src/schemas/scheduler/pre-condition.ts`
- **Create:** `src/schemas/scheduler/__tests__/pre-condition.test.ts`
- **Create:** `src/components/scheduler/ScheduleEditor/PreConditionForm.tsx` (replaces .jsx)
- **Create:** `src/components/scheduler/ScheduleEditor/__tests__/PreConditionForm.test.tsx` (replaces .test.jsx)
- **Delete:** `PreConditionForm.jsx`, `PreConditionForm.test.jsx`

## Testing

- Schema tests: ~25 tests covering all field validations, boundaries, cross-field refine
- Component tests: Migrate all 60+ existing tests to .tsx, add ~4 new for parent error wiring and prop sync

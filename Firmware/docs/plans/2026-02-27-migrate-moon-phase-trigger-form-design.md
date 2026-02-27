# Design: Migrate MoonPhaseTriggerForm (#448)

**Issue:** #448
**Parent:** #197
**Pattern:** Controlled (parent-owned state)
**Siblings:** IntervalTriggerForm (#446), SolarTriggerForm (#447)

## Current State

- **File:** `src/components/scheduler/ScheduleEditor/MoonPhaseTriggerForm.jsx`
- **Fields:** `moon_phase` (select, 8 options), `time_of_day` (HH:MM time input), `offset_days` (number, ±7)
- **Validation:** `validateNumericInput()` gates offset — silently rejects invalid/OOB values
- **Presets:** 3 offset buttons (-1, 0, +1 days)
- **Tests:** 48 existing (including 6 dark mode styling tests)

## Schema (`src/schemas/scheduler/moon-phase.ts`)

Three fields:

| Field | Zod Type | Constraints |
|-------|----------|-------------|
| `moon_phase` | `z.enum()` | 8 values from `MOON_PHASES` constant |
| `time_of_day` | `z.string().regex()` | HH:MM format via `TIME_FORMAT_REGEX` pattern |
| `offset_days` | `z.number().int().min(-MAX).max(MAX)` | ±`SCHEDULE_LIMITS.MAX_OFFSET_DAYS` (7) |

Same `as [string, ...string[]]` cast on enum as SolarTriggerForm.

Exports: `moonPhaseTriggerSchema`, `MoonPhaseTriggerFormData`.

## Component Architecture

### Form Management

All three fields managed by react-hook-form Controllers:

- `moon_phase` — `<select>` with enum options
- `time_of_day` — `<input type="time">`, `field.onChange` receives string directly
- `offset_days` — `<input type="number">`, NaN sentinel for cleared input (same as siblings)

### Cycle Prevention

Same `valueRef` / `onChangeRef` / `lastPropagatedRef` pattern as siblings.

`lastPropagatedRef` stores `{ moon_phase, time_of_day, offset_days }` — all three form-managed fields (no bypassed fields like `days_of_week` in SolarTriggerForm).

### Prop-Sync Effect

Resets form when any of the three fields change externally (preset click, parent state change). Compares all three fields against `lastPropagatedRef`.

### Propagation Effect

Watches all three fields via `useWatch`. Validates with `safeParse`. Only propagates valid values.

### Preset Buttons

Bypass form state — call `onChangeRef.current()` directly. Same pattern as siblings. Only 3 presets: `-1 day`, `No offset`, `+1 day`.

### Resolver Workaround

Same Zod 4 + `@hookform/resolvers` double cast with `TODO(#448)` linking resolvers#800.

## Accessibility Improvements

Over the original JSX:

- `aria-invalid` on all inputs (both Zod and parent errors)
- `aria-describedby` linking error `<p>` elements to inputs
- `role="alert"` on error messages
- `id` attributes on error elements (`moon_phase-error`, `time_of_day-error`, `offset_days-error`)

## Types

```typescript
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
```

`moon_phase: string` (not enum union) — intentional, matches SolarTriggerForm pattern. Parent may hold values from older configs.

## Module-Level Constants and Helpers

```typescript
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

function formatOffset(days: number): string { ... }
```

Preview text computed via `useMemo` — inlined, not a separate function.

## Test Plan

### Schema Tests (~15)

- Enum validation (valid phases, invalid values)
- Time format (valid HH:MM, invalid formats, empty string)
- Offset boundaries (±7, ±8, zero, non-integer)
- Error messages

### Component Tests (~40)

Same categories as existing tests, minus dark mode styling (low value, not tested in siblings):

- Rendering (default values, provided values, all phases in dropdown)
- Moon Phase Selection (change, label display)
- Time of Day Input (change, format, error display, validation)
- Offset Days Input (change, negative values, limits, errors, NaN/empty handling)
- Quick Offset Presets (render, click, highlight)
- Preview Text Generation (no offset, positive, negative, singular day, different phases)
- Disabled State (all inputs, presets)
- Prop Sync (external changes, unchanged value preservation)
- onChange Callback (complete object on each field change)
- Accessibility (aria-describedby, aria-invalid for Zod and parent errors)

Dark mode styling tests (6 in original) are dropped — they test Tailwind class presence, which is brittle and not tested in IntervalTriggerForm or SolarTriggerForm.

## Differences from SolarTriggerForm

| Aspect | SolarTriggerForm | MoonPhaseTriggerForm |
|--------|------------------|----------------------|
| Form fields | 2 (solar_event, offset_minutes) | 3 (moon_phase, time_of_day, offset_days) |
| `lastPropagatedRef` shape | `{ solar_event, offset_minutes }` | `{ moon_phase, time_of_day, offset_days }` |
| Bypassed fields | `days_of_week` | None |
| Time input | — | `<input type="time">` with regex validation |
| DaysOfWeekSelector | Yes | No |
| Offset range | ±1440 minutes | ±7 days |
| Presets | 5 | 3 |

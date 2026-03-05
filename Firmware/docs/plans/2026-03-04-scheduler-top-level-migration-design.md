# Migrate Scheduler Top-Level to react-hook-form + Zod

**Issue:** #455
**Date:** 2026-03-04
**Status:** Design approved
**Parent:** #197 (Form Validation Migration)
**Blocked by:** #446, #447, #448, #449, #450, #475 (all closed)

## Quick Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Composition strategy | Independent forms | Sub-forms keep own `useForm`; top-level gets its own for name/description only. Matches established pattern, minimal refactoring. |
| Routines state | `useState` (not in form) | Complex nested objects with add/delete/update callbacks. `useFieldArray` would conflict with independent sub-form validation. |
| TSX conversion scope | Full | All remaining JSX files in ScheduleEditor/ converted to TSX. |
| PropTypes replacement | TypeScript interfaces | Delete `propTypes.js`, create `scheduler-types.ts` with shared interfaces. |
| Top-level schema scope | Name + description only | Routines structure validated manually on save (at least one routine, each has trigger + actions). |

## Architecture

### Form Composition Model

```
ScheduleEditor.tsx (useForm: name, description)
  ├── RoutineList.tsx (receives routines[] as prop)
  │   ├── RoutineCard.tsx (receives single routine as prop)
  │   │   ├── TriggerForm.tsx (router, passes to sub-forms)
  │   │   │   ├── IntervalTriggerForm.tsx (own useForm) ✅ done
  │   │   │   ├── SolarTriggerForm.tsx (own useForm) ✅ done
  │   │   │   ├── MoonPhaseTriggerForm.tsx (own useForm) ✅ done
  │   │   │   ├── FixedTimeTriggerForm.tsx → migrate to useForm
  │   │   │   ├── SensorTriggerForm.tsx → migrate to useForm
  │   │   │   └── CronExpressionInput (existing)
  │   │   └── PreConditionForm.tsx (own useForm) ✅ done
  │   └── NewRoutineCard.tsx
  ├── ActivationPanel.tsx
  ├── ConflictPanel.tsx
  └── CronLimitWarning.tsx
```

Each sub-form validates its own fields independently via Zod. The top-level ScheduleEditor validates only what it owns (name, description) and performs structural checks on routines at save time.

### Top-Level Zod Schema

```typescript
// schemas/scheduler/schedule.ts
import { z } from 'zod';
import { SCHEDULE_LIMITS } from '@/components/scheduler/ScheduleEditor/constants';

export const scheduleSchema = z.object({
  name: z.string()
    .trim()
    .min(1, 'Schedule name is required')
    .max(SCHEDULE_LIMITS.NAME_MAX_LENGTH,
      `Name must be ${SCHEDULE_LIMITS.NAME_MAX_LENGTH} characters or less`),
  description: z.string()
    .max(SCHEDULE_LIMITS.DESCRIPTION_MAX_LENGTH,
      `Description must be ${SCHEDULE_LIMITS.DESCRIPTION_MAX_LENGTH} characters or less`)
    .default(''),
});

export type ScheduleFormData = z.infer<typeof scheduleSchema>;
```

Routines validation stays manual (on save):
- At least one routine required
- Each routine must have a trigger and at least one action

### New Sub-Form Schemas

**FixedTimeTriggerForm** (`schemas/scheduler/fixed-time.ts`):
```typescript
export const fixedTimeTriggerSchema = z.object({
  time_of_day: z.string().regex(TIME_FORMAT_REGEX, 'Invalid time format (HH:MM)'),
});
```

**SensorTriggerForm** (`schemas/scheduler/sensor.ts`):
```typescript
export const sensorTriggerSchema = z.object({
  sensor_type: z.enum([...SENSOR_TYPES.map(s => s.value)]),
  comparison: z.enum([...SENSOR_COMPARISONS.map(c => c.value)]),
  threshold: z.number().min(0),
  cooldown_minutes: z.number().int().min(1).max(SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES),
});
```

## Shared TypeScript Types

Replace `propTypes.js` with `scheduler-types.ts`:

```typescript
// components/scheduler/ScheduleEditor/scheduler-types.ts

export interface TimeWindow {
  start_time: string;
  end_time: string;
  start_offset_minutes?: number;
  end_offset_minutes?: number;
}

export type TriggerType =
  | 'interval' | 'solar' | 'moon_phase'
  | 'fixed_time' | 'sensor' | 'cron' | 'recurring_days';

export interface BaseTrigger {
  trigger_type: TriggerType;
  days_of_week?: number[] | null;
}

export interface IntervalTrigger extends BaseTrigger {
  trigger_type: 'interval';
  interval_minutes: number;
  time_window?: TimeWindow | null;
}

export interface SolarTrigger extends BaseTrigger {
  trigger_type: 'solar';
  solar_event: SolarEventValue;
  offset_minutes: number;
}

export interface MoonPhaseTrigger extends BaseTrigger {
  trigger_type: 'moon_phase';
  moon_phase: MoonPhaseValue;
  phases?: string[];
  time_of_day?: string;
  offset_days?: number;
}

export interface FixedTimeTrigger extends BaseTrigger {
  trigger_type: 'fixed_time';
  time_of_day: string;
  times?: string[];
}

export interface SensorTrigger extends BaseTrigger {
  trigger_type: 'sensor';
  sensor_type: string;
  comparison: string;
  threshold: number;
  cooldown_minutes: number;
}

export interface CronTrigger extends BaseTrigger {
  trigger_type: 'cron';
  cron_expression: string;
}

export type Trigger =
  | IntervalTrigger | SolarTrigger | MoonPhaseTrigger
  | FixedTimeTrigger | SensorTrigger | CronTrigger;

export interface RoutineAction {
  id: string;
  action_type: string;
  action_name: string;
  offset_minutes?: number;
}

export interface PreCondition {
  trigger_type: string;
  sensor_type: string;
  comparison: string;
  threshold: number;
  cooldown_minutes: number;
  time_window?: TimeWindow | null;
}

export interface Routine {
  routine_id: string;
  name?: string;
  trigger: Trigger;
  actions: RoutineAction[];
  pre_condition?: PreCondition | null;
}

export interface Schedule {
  schedule_id: string;
  name: string;
  description: string;
  routines: Routine[];
  is_active?: boolean;
  is_builtin?: boolean;
  use_seconds_timing?: boolean;
  enabled?: boolean;
  created_at?: string;
  updated_at?: string;
  modified_at?: string;
}
```

### Error Types

```typescript
export interface TimeWindowErrors {
  start_time?: string;
  end_time?: string;
  general?: string;
}

export interface TriggerErrors {
  trigger_type?: string;
  interval_minutes?: string;
  solar_event?: string;
  offset_minutes?: string;
  moon_phase?: string;
  time_of_day?: string;
  sensor_type?: string;
  comparison?: string;
  threshold?: string;
  cooldown_minutes?: string;
  cron_expression?: string;
  time_window?: TimeWindowErrors;
  days_of_week?: string;
}
```

## ScheduleEditor Migration Details

### What Changes

| Aspect | Before | After |
|--------|--------|-------|
| Name/description state | `useState` | `useForm` with `register()` |
| Name/description validation | Manual in `validate()` | Zod schema via `zodResolver` |
| Error display | `errors.name` from manual state | `formState.errors.name?.message` |
| Routines validation | Manual in `validate()` | Manual check in `onSubmit` handler |
| Save handler | `handleSave()` calls `validate()` | `handleSubmit(onSubmit)` + routines check |
| Type safety | PropTypes | TypeScript interfaces |
| File extension | `.jsx` | `.tsx` |

### What Stays the Same

- Routines managed via `useState` + callbacks
- Sub-forms use independent `useForm` instances
- Conflict detection via `useValidateDraft` hook (API call)
- View mode / edit mode toggle
- Drawer open/close behavior
- Body scroll lock, focus management, keyboard handling

## Files Changed

| Category | Files |
|----------|-------|
| **New** | `schemas/scheduler/schedule.ts`, `schemas/scheduler/fixed-time.ts`, `schemas/scheduler/sensor.ts`, `ScheduleEditor/scheduler-types.ts` |
| **Major** | `ScheduleEditor.jsx→.tsx` (useForm), `FixedTimeTriggerForm.jsx→.tsx` (useForm), `SensorTriggerForm.jsx→.tsx` (useForm) |
| **TSX + types** | `SchedulerUI.jsx→.tsx`, `TriggerForm.jsx→.tsx`, `RoutineList.jsx→.tsx`, `RoutineCard.jsx→.tsx`, `NewRoutineCard.jsx→.tsx`, `DaysOfWeekSelector.jsx→.tsx`, `TriggerLabel.jsx→.tsx`, `ActivationPanel.jsx→.tsx`, `ConflictPanel.jsx→.tsx`, `CronLimitWarning.jsx→.tsx` |
| **Deleted** | `propTypes.js` |
| **Tests** | All corresponding test files renamed `.test.jsx→.test.tsx` + imports updated |

## Test Strategy

- **Schema tests**: New tests for `scheduleSchema`, `fixedTimeTriggerSchema`, `sensorTriggerSchema` validation
- **ScheduleEditor tests**: Update for react-hook-form async validation (`waitFor` patterns)
- **FixedTimeTriggerForm/SensorTriggerForm tests**: Rewrite to match RHF patterns from IntervalTriggerForm.test.tsx
- **Pure TSX conversions**: Rename test files, update imports, no behavioral changes
- **All existing tests must pass** after migration

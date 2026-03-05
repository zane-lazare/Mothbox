# Scheduler Top-Level Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate the ScheduleEditor and all remaining scheduler JSX components to react-hook-form + Zod + TypeScript, replacing PropTypes with shared TS interfaces.

**Architecture:** Independent forms — ScheduleEditor gets its own `useForm` for name/description. Sub-forms keep their own `useForm` instances. Routines stay as `useState`. All JSX files in ScheduleEditor/ convert to TSX with typed props.

**Tech Stack:** React 19, react-hook-form 7, Zod 4, TypeScript, Vitest, React Testing Library

**Design doc:** `docs/plans/2026-03-04-scheduler-top-level-migration-design.md`

---

### Task 1: Create Shared TypeScript Types (`scheduler-types.ts`)

**Files:**
- Create: `webui/frontend/src/components/scheduler/ScheduleEditor/scheduler-types.ts`

**Context:** This file replaces `propTypes.js` with TypeScript interfaces. All scheduler components will import types from here. Reference the existing `propTypes.js` at the same directory for the shape definitions. Import `SolarEventValue` and `MoonPhaseValue` from `./constants`.

**Step 1: Create the types file**

```typescript
// webui/frontend/src/components/scheduler/ScheduleEditor/scheduler-types.ts
import type { SolarEventValue, MoonPhaseValue } from './constants';

// ── Time Window ──────────────────────────────────────────────
export interface TimeWindow {
  start_time: string;
  end_time: string;
  start_offset_minutes?: number;
  end_offset_minutes?: number;
}

export interface TimeWindowErrors {
  start_time?: string;
  end_time?: string;
  general?: string;
}

// ── Triggers ─────────────────────────────────────────────────
export type TriggerType =
  | 'interval'
  | 'solar'
  | 'moon_phase'
  | 'fixed_time'
  | 'sensor'
  | 'cron'
  | 'recurring_days';

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

export interface RecurringDaysTrigger extends BaseTrigger {
  trigger_type: 'recurring_days';
  days?: number[];
  time?: string;
}

export type Trigger =
  | IntervalTrigger
  | SolarTrigger
  | MoonPhaseTrigger
  | FixedTimeTrigger
  | SensorTrigger
  | CronTrigger
  | RecurringDaysTrigger;

export interface TriggerErrors {
  trigger_type?: string;
  interval_minutes?: string;
  solar_event?: string;
  offset_minutes?: string;
  moon_phase?: string;
  time_of_day?: string;
  offset_days?: string;
  sensor_type?: string;
  comparison?: string;
  threshold?: string;
  cooldown_minutes?: string;
  cron_expression?: string;
  time_window?: TimeWindowErrors;
  days_of_week?: string;
}

// ── Actions ──────────────────────────────────────────────────
export interface RoutineAction {
  id: string;
  action_type: string;
  action_name: string;
  offset_minutes?: number;
}

// ── Pre-condition ────────────────────────────────────────────
export interface PreCondition {
  trigger_type: string;
  sensor_type: string;
  comparison: string;
  threshold: number;
  cooldown_minutes: number;
  time_window?: TimeWindow | null;
}

// ── Routine ──────────────────────────────────────────────────
export interface Routine {
  routine_id: string;
  name?: string;
  trigger: Trigger;
  actions: RoutineAction[];
  pre_condition?: PreCondition | null;
}

// ── Schedule ─────────────────────────────────────────────────
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

// ── Conflict Report ──────────────────────────────────────────
export interface ConflictReport {
  valid?: boolean;
  has_warnings?: boolean;
  has_blocking_conflicts?: boolean;
  conflicts?: Array<{
    type: string;
    message: string;
    severity?: string;
  }>;
  total_conflicts?: number;
  blocking_conflicts?: number;
}
```

**Step 2: Verify TypeScript compiles**

Run: `cd webui/frontend && npx tsc --noEmit --pretty 2>&1 | head -20`
Expected: No errors related to `scheduler-types.ts`

**Step 3: Commit**

```bash
git add webui/frontend/src/components/scheduler/ScheduleEditor/scheduler-types.ts
git commit -m "feat(#455): add shared TypeScript types for scheduler components"
```

---

### Task 2: Create Schedule Top-Level Zod Schema

**Files:**
- Create: `webui/frontend/src/schemas/scheduler/schedule.ts`
- Create: `webui/frontend/src/schemas/scheduler/__tests__/schedule.test.ts`

**Context:** This schema validates only `name` and `description` — the fields owned by ScheduleEditor's `useForm`. Look at `webui/frontend/src/schemas/scheduler/interval.ts` as a pattern reference for schema structure. Import `SCHEDULE_LIMITS` from `@/components/scheduler/ScheduleEditor/constants`.

**Step 1: Write the failing test**

```typescript
// webui/frontend/src/schemas/scheduler/__tests__/schedule.test.ts
import { describe, it, expect } from 'vitest';
import { scheduleSchema, type ScheduleFormData } from '../schedule';
import { SCHEDULE_LIMITS } from '@/components/scheduler/ScheduleEditor/constants';

describe('scheduleSchema', () => {
  describe('name field', () => {
    it('accepts a valid name', () => {
      const result = scheduleSchema.safeParse({ name: 'My Schedule', description: '' });
      expect(result.success).toBe(true);
    });

    it('rejects empty name', () => {
      const result = scheduleSchema.safeParse({ name: '', description: '' });
      expect(result.success).toBe(false);
    });

    it('rejects whitespace-only name', () => {
      const result = scheduleSchema.safeParse({ name: '   ', description: '' });
      expect(result.success).toBe(false);
    });

    it('rejects name exceeding max length', () => {
      const longName = 'a'.repeat(SCHEDULE_LIMITS.NAME_MAX_LENGTH + 1);
      const result = scheduleSchema.safeParse({ name: longName, description: '' });
      expect(result.success).toBe(false);
    });

    it('accepts name at max length', () => {
      const maxName = 'a'.repeat(SCHEDULE_LIMITS.NAME_MAX_LENGTH);
      const result = scheduleSchema.safeParse({ name: maxName, description: '' });
      expect(result.success).toBe(true);
    });

    it('trims whitespace from name', () => {
      const result = scheduleSchema.safeParse({ name: '  My Schedule  ', description: '' });
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.name).toBe('My Schedule');
      }
    });
  });

  describe('description field', () => {
    it('accepts empty description', () => {
      const result = scheduleSchema.safeParse({ name: 'Test', description: '' });
      expect(result.success).toBe(true);
    });

    it('defaults description to empty string when omitted', () => {
      const result = scheduleSchema.safeParse({ name: 'Test' });
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.description).toBe('');
      }
    });

    it('rejects description exceeding max length', () => {
      const longDesc = 'a'.repeat(SCHEDULE_LIMITS.DESCRIPTION_MAX_LENGTH + 1);
      const result = scheduleSchema.safeParse({ name: 'Test', description: longDesc });
      expect(result.success).toBe(false);
    });

    it('accepts description at max length', () => {
      const maxDesc = 'a'.repeat(SCHEDULE_LIMITS.DESCRIPTION_MAX_LENGTH);
      const result = scheduleSchema.safeParse({ name: 'Test', description: maxDesc });
      expect(result.success).toBe(true);
    });
  });

  describe('type inference', () => {
    it('inferred type matches expected shape', () => {
      const data: ScheduleFormData = { name: 'Test', description: 'desc' };
      expect(data.name).toBe('Test');
      expect(data.description).toBe('desc');
    });
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd webui/frontend && npx vitest run src/schemas/scheduler/__tests__/schedule.test.ts 2>&1 | tail -20`
Expected: FAIL — cannot resolve `../schedule`

**Step 3: Write the schema**

```typescript
// webui/frontend/src/schemas/scheduler/schedule.ts
import { z } from 'zod';
import { SCHEDULE_LIMITS } from '@/components/scheduler/ScheduleEditor/constants';

export const scheduleSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, 'Schedule name is required')
    .max(
      SCHEDULE_LIMITS.NAME_MAX_LENGTH,
      `Name must be ${SCHEDULE_LIMITS.NAME_MAX_LENGTH} characters or less`,
    ),
  description: z
    .string()
    .max(
      SCHEDULE_LIMITS.DESCRIPTION_MAX_LENGTH,
      `Description must be ${SCHEDULE_LIMITS.DESCRIPTION_MAX_LENGTH} characters or less`,
    )
    .default(''),
});

export type ScheduleFormData = z.infer<typeof scheduleSchema>;
```

**Step 4: Run test to verify it passes**

Run: `cd webui/frontend && npx vitest run src/schemas/scheduler/__tests__/schedule.test.ts 2>&1 | tail -20`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add webui/frontend/src/schemas/scheduler/schedule.ts webui/frontend/src/schemas/scheduler/__tests__/schedule.test.ts
git commit -m "feat(#455): add schedule top-level Zod schema with tests"
```

---

### Task 3: Create Fixed-Time and Sensor Zod Schemas

**Files:**
- Create: `webui/frontend/src/schemas/scheduler/fixed-time.ts`
- Create: `webui/frontend/src/schemas/scheduler/sensor.ts`
- Create: `webui/frontend/src/schemas/scheduler/__tests__/fixed-time.test.ts`
- Create: `webui/frontend/src/schemas/scheduler/__tests__/sensor.test.ts`

**Context:** These schemas follow the same pattern as `interval.ts` and `solar.ts` in the same directory. Import constants from `@/components/scheduler/ScheduleEditor/constants`. Check the existing schemas for the exact import style and Zod API usage.

**Step 1: Write fixed-time test**

```typescript
// webui/frontend/src/schemas/scheduler/__tests__/fixed-time.test.ts
import { describe, it, expect } from 'vitest';
import { fixedTimeTriggerSchema, type FixedTimeTriggerFormData } from '../fixed-time';

describe('fixedTimeTriggerSchema', () => {
  it('accepts valid HH:MM time', () => {
    const result = fixedTimeTriggerSchema.safeParse({ time_of_day: '14:30' });
    expect(result.success).toBe(true);
  });

  it('accepts midnight', () => {
    const result = fixedTimeTriggerSchema.safeParse({ time_of_day: '00:00' });
    expect(result.success).toBe(true);
  });

  it('accepts 23:59', () => {
    const result = fixedTimeTriggerSchema.safeParse({ time_of_day: '23:59' });
    expect(result.success).toBe(true);
  });

  it('rejects invalid time format', () => {
    const result = fixedTimeTriggerSchema.safeParse({ time_of_day: '25:00' });
    expect(result.success).toBe(false);
  });

  it('rejects empty string', () => {
    const result = fixedTimeTriggerSchema.safeParse({ time_of_day: '' });
    expect(result.success).toBe(false);
  });

  it('rejects non-time string', () => {
    const result = fixedTimeTriggerSchema.safeParse({ time_of_day: 'noon' });
    expect(result.success).toBe(false);
  });

  it('inferred type matches expected shape', () => {
    const data: FixedTimeTriggerFormData = { time_of_day: '12:00' };
    expect(data.time_of_day).toBe('12:00');
  });
});
```

**Step 2: Write sensor test**

```typescript
// webui/frontend/src/schemas/scheduler/__tests__/sensor.test.ts
import { describe, it, expect } from 'vitest';
import { sensorTriggerSchema, type SensorTriggerFormData } from '../sensor';
import { SCHEDULE_LIMITS } from '@/components/scheduler/ScheduleEditor/constants';

describe('sensorTriggerSchema', () => {
  const validSensor = {
    sensor_type: 'motion',
    comparison: 'gt',
    threshold: 50,
    cooldown_minutes: 5,
  };

  it('accepts valid sensor config', () => {
    const result = sensorTriggerSchema.safeParse(validSensor);
    expect(result.success).toBe(true);
  });

  it('rejects invalid sensor_type', () => {
    const result = sensorTriggerSchema.safeParse({ ...validSensor, sensor_type: 'invalid' });
    expect(result.success).toBe(false);
  });

  it('rejects invalid comparison', () => {
    const result = sensorTriggerSchema.safeParse({ ...validSensor, comparison: 'invalid' });
    expect(result.success).toBe(false);
  });

  it('rejects negative threshold', () => {
    const result = sensorTriggerSchema.safeParse({ ...validSensor, threshold: -1 });
    expect(result.success).toBe(false);
  });

  it('rejects cooldown below 1', () => {
    const result = sensorTriggerSchema.safeParse({ ...validSensor, cooldown_minutes: 0 });
    expect(result.success).toBe(false);
  });

  it('rejects cooldown exceeding max', () => {
    const result = sensorTriggerSchema.safeParse({
      ...validSensor,
      cooldown_minutes: SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES + 1,
    });
    expect(result.success).toBe(false);
  });

  it('accepts cooldown at max', () => {
    const result = sensorTriggerSchema.safeParse({
      ...validSensor,
      cooldown_minutes: SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES,
    });
    expect(result.success).toBe(true);
  });

  it('rejects non-integer cooldown', () => {
    const result = sensorTriggerSchema.safeParse({ ...validSensor, cooldown_minutes: 5.5 });
    expect(result.success).toBe(false);
  });

  it('inferred type matches expected shape', () => {
    const data: SensorTriggerFormData = validSensor;
    expect(data.sensor_type).toBe('motion');
  });
});
```

**Step 3: Run tests to verify they fail**

Run: `cd webui/frontend && npx vitest run src/schemas/scheduler/__tests__/fixed-time.test.ts src/schemas/scheduler/__tests__/sensor.test.ts 2>&1 | tail -20`
Expected: FAIL — cannot resolve modules

**Step 4: Write the schemas**

```typescript
// webui/frontend/src/schemas/scheduler/fixed-time.ts
import { z } from 'zod';
import { TIME_FORMAT_REGEX } from '@/components/scheduler/ScheduleEditor/constants';

export const fixedTimeTriggerSchema = z.object({
  time_of_day: z
    .string()
    .regex(TIME_FORMAT_REGEX, 'Must be a valid time in HH:MM format'),
});

export type FixedTimeTriggerFormData = z.infer<typeof fixedTimeTriggerSchema>;
```

```typescript
// webui/frontend/src/schemas/scheduler/sensor.ts
import { z } from 'zod';
import {
  SENSOR_TYPES,
  SENSOR_COMPARISONS,
  SCHEDULE_LIMITS,
} from '@/components/scheduler/ScheduleEditor/constants';

const sensorTypeValues = SENSOR_TYPES.map((s) => s.value) as [string, ...string[]];
const comparisonValues = SENSOR_COMPARISONS.map((c) => c.value) as [string, ...string[]];

export const sensorTriggerSchema = z.object({
  sensor_type: z.enum(sensorTypeValues, { error: 'Invalid sensor type' }),
  comparison: z.enum(comparisonValues, { error: 'Invalid comparison operator' }),
  threshold: z
    .number({ error: 'Threshold must be a number' })
    .min(0, 'Threshold must be 0 or greater'),
  cooldown_minutes: z
    .number({ error: 'Cooldown must be a number' })
    .int('Cooldown must be a whole number')
    .min(1, 'Cooldown must be at least 1 minute')
    .max(
      SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES,
      `Cooldown cannot exceed ${SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES} minutes`,
    ),
});

export type SensorTriggerFormData = z.infer<typeof sensorTriggerSchema>;
```

**Step 5: Run tests to verify they pass**

Run: `cd webui/frontend && npx vitest run src/schemas/scheduler/__tests__/fixed-time.test.ts src/schemas/scheduler/__tests__/sensor.test.ts 2>&1 | tail -20`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add webui/frontend/src/schemas/scheduler/fixed-time.ts webui/frontend/src/schemas/scheduler/sensor.ts webui/frontend/src/schemas/scheduler/__tests__/
git commit -m "feat(#455): add fixed-time and sensor Zod schemas with tests"
```

---

### Task 4: Migrate FixedTimeTriggerForm to RHF + Zod + TSX

**Files:**
- Rename: `webui/frontend/src/components/scheduler/ScheduleEditor/FixedTimeTriggerForm.jsx` → `.tsx`
- Modify: test file for FixedTimeTriggerForm
- Reference: `IntervalTriggerForm.tsx` (lines 1-316) for the controlled form pattern

**Context:** This component currently uses plain `onChange` callbacks with no form library. Migrate to the controlled pattern established by IntervalTriggerForm.tsx:
1. `useForm` with `zodResolver` for the `time_of_day` field
2. `useWatch` + `useEffect` to propagate validated changes to parent via `onChange`
3. `useRef` for stable callback/value refs
4. `Controller` to wrap the time input
5. Use the Zod 4 type workaround: `zodResolver(schema as unknown as Parameters<typeof zodResolver>[0]) as unknown as Resolver<FormData>`

The component receives `value` (with `time_of_day` and `days_of_week`) and `onChange` as props. Only `time_of_day` goes through `useForm`; `days_of_week` passes through to DaysOfWeekSelector via direct `onChange` callback.

Read the current `FixedTimeTriggerForm.jsx` fully before making changes. Keep the same rendering structure (time input, quick presets, DaysOfWeekSelector, preview text). Replace PropTypes with a typed props interface importing from `./scheduler-types`.

**Step 1: Rename file and add RHF + Zod imports**

Rename `.jsx` → `.tsx`. Add:
```typescript
import { useForm, Controller, useWatch } from 'react-hook-form';
import type { Resolver } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  fixedTimeTriggerSchema,
  type FixedTimeTriggerFormData,
} from '../../../schemas/scheduler/fixed-time';
import type { TimeWindow, TriggerErrors } from './scheduler-types';
```

Remove `import PropTypes from 'prop-types'` and the `FixedTimeTriggerForm.propTypes = { ... }` block at the bottom.

**Step 2: Add typed props interface and useForm setup**

```typescript
export interface FixedTimeTriggerValue {
  time_of_day: string;
  days_of_week: number[] | null;
}

interface FixedTimeTriggerFormProps {
  value: FixedTimeTriggerValue;
  onChange: (value: FixedTimeTriggerValue) => void;
  disabled?: boolean;
  errors?: TriggerErrors;
}
```

Add `useForm` setup inside the component following the IntervalTriggerForm pattern:
- `const resolver = zodResolver(fixedTimeTriggerSchema as unknown as ...)` with the type workaround
- `useForm<FixedTimeTriggerFormData>` with `resolver`, `defaultValues: { time_of_day: value.time_of_day }`, `mode: 'onChange'`
- `useRef` for `onChangeRef`, `valueRef`, `lastPropagatedRef`
- Prop sync `useEffect` for `value.time_of_day`
- Propagation `useEffect` with `useWatch` + `safeParse`

**Step 3: Wrap time input with Controller**

Replace the direct `<input type="time">` with a `Controller` render prop. Keep the quick preset buttons calling `field.onChange()` instead of the old direct `onChange`.

**Step 4: Update DaysOfWeekSelector passthrough**

Keep DaysOfWeekSelector as a direct callback (not in form):
```typescript
const handleDaysChange = useCallback(
  (days: number[] | null) => {
    onChangeRef.current({ ...valueRef.current, days_of_week: days });
  },
  [],
);
```

**Step 5: Update tests**

Rename test file `.test.jsx` → `.test.tsx`. Update imports. Add `waitFor` for async validation. Test that invalid times show Zod error messages. Test prop sync behavior.

**Step 6: Run tests**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ScheduleEditor/__tests__/FixedTimeTriggerForm.test.tsx 2>&1 | tail -30`
Expected: All tests PASS

**Step 7: Commit**

```bash
git add -A webui/frontend/src/components/scheduler/ScheduleEditor/FixedTimeTriggerForm*
git commit -m "feat(#455): migrate FixedTimeTriggerForm to react-hook-form + Zod + TSX"
```

---

### Task 5: Migrate SensorTriggerForm to RHF + Zod + TSX

**Files:**
- Rename: `webui/frontend/src/components/scheduler/ScheduleEditor/SensorTriggerForm.jsx` → `.tsx`
- Modify: test file for SensorTriggerForm
- Reference: `IntervalTriggerForm.tsx` for the controlled pattern

**Context:** This component currently uses `useState` for `thresholdError` and `cooldownError` with manual `validateNumericInput()`. Migrate all four fields (`sensor_type`, `comparison`, `threshold`, `cooldown_minutes`) to `useForm` with `zodResolver(sensorTriggerSchema)`.

Read the current `SensorTriggerForm.jsx` fully before making changes. The component has:
- Two `<select>` elements (sensor_type, comparison)
- Two `<input type="number">` elements (threshold, cooldown_minutes)
- Preview text generation
- Local error state for validation

Replace local error state with `formState.errors`. Replace `validateNumericInput()` with Zod schema validation. Use `Controller` for all four fields. Keep preview text generation. Replace PropTypes with typed interface.

**Step 1: Rename file and add RHF + Zod imports**

Same pattern as Task 4. Import from `../../../schemas/scheduler/sensor`.

**Step 2: Add typed props and useForm**

```typescript
export interface SensorTriggerValue {
  sensor_type: string;
  comparison: string;
  threshold: number;
  cooldown_minutes: number;
}

interface SensorTriggerFormProps {
  value: SensorTriggerValue;
  onChange: (value: SensorTriggerValue) => void;
  disabled?: boolean;
  errors?: TriggerErrors;
}
```

Set up `useForm<SensorTriggerFormData>` with all four fields in `defaultValues`. Use `useWatch` to watch all four fields and propagate validated changes to parent.

**Step 3: Replace local error state with form errors**

Remove `useState` for `thresholdError` and `cooldownError`. Remove calls to `validateNumericInput()`. Let Zod handle all validation through the form's `formState.errors`.

**Step 4: Wrap inputs with Controller**

Use `Controller` for each of the four fields. For `<select>` elements, `field.onChange(e.target.value)`. For number inputs, `field.onChange(raw === '' ? NaN : Number(raw))` (same pattern as IntervalTriggerForm).

**Step 5: Update tests**

Rename test file `.test.jsx` → `.test.tsx`. Update for async validation with `waitFor`. Remove tests for manual `validateNumericInput` behavior, replace with Zod validation tests.

**Step 6: Run tests**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ScheduleEditor/__tests__/SensorTriggerForm.test.tsx 2>&1 | tail -30`
Expected: All tests PASS

**Step 7: Commit**

```bash
git add -A webui/frontend/src/components/scheduler/ScheduleEditor/SensorTriggerForm*
git commit -m "feat(#455): migrate SensorTriggerForm to react-hook-form + Zod + TSX"
```

---

### Task 6: Convert Leaf Components to TSX

**Files:**
- Rename: `TriggerLabel.jsx` → `.tsx`
- Rename: `CronLimitWarning.jsx` → `.tsx`
- Rename: `ConflictPanel.jsx` → `.tsx`
- Rename: `DaysOfWeekSelector.jsx` → `.tsx`
- Rename corresponding test files `.test.jsx` → `.test.tsx`

**Context:** These are leaf components with no form logic. The migration is mechanical: rename, add typed props, remove PropTypes. Reference `scheduler-types.ts` for shared types. These components have no dependencies on each other, so they can all be converted in one batch.

**For each component:**

1. Rename `.jsx` → `.tsx`
2. Remove `import PropTypes from 'prop-types'`
3. Add a typed props interface above the component
4. Remove the `.propTypes = { ... }` block at the bottom
5. Add TypeScript annotations to `useState`, `useCallback`, etc. where needed
6. For `memo()` wrapped components, use `memo<Props>(function Component({ ... }: Props) { ... })`

**Prop interfaces to create:**

```typescript
// TriggerLabel.tsx
import type { Trigger } from './scheduler-types';
interface TriggerLabelProps {
  trigger?: Trigger;
}

// CronLimitWarning.tsx
interface CronLimitWarningProps {
  estimatedEntries?: number;
}

// ConflictPanel.tsx
import type { ConflictReport } from './scheduler-types';
interface ConflictPanelProps {
  conflictReport?: ConflictReport | null;
  isValidating?: boolean;
  isError?: boolean;
  error?: { message?: string } | null;
}

// DaysOfWeekSelector.tsx
interface DaysOfWeekSelectorProps {
  value: number[] | null;
  onChange: (value: number[] | null) => void;
  disabled?: boolean;
  allowEmpty?: boolean;
  compact?: boolean;
}
```

**Step 1: Convert all four leaf components**

Apply the mechanical changes to each file. Keep all existing logic, JSX, and styles unchanged.

**Step 2: Rename test files and update imports**

Rename `.test.jsx` → `.test.tsx`. Update imports to point to new `.tsx` file names. No test logic changes needed.

**Step 3: Run tests**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ScheduleEditor/__tests__/TriggerLabel.test.tsx src/components/scheduler/ScheduleEditor/__tests__/CronLimitWarning.test.tsx src/components/scheduler/ScheduleEditor/__tests__/ConflictPanel.test.tsx src/components/scheduler/ScheduleEditor/__tests__/DaysOfWeekSelector.test.tsx 2>&1 | tail -30`
Expected: All tests PASS

**Step 4: Commit**

```bash
git add -A webui/frontend/src/components/scheduler/ScheduleEditor/TriggerLabel.* webui/frontend/src/components/scheduler/ScheduleEditor/CronLimitWarning.* webui/frontend/src/components/scheduler/ScheduleEditor/ConflictPanel.* webui/frontend/src/components/scheduler/ScheduleEditor/DaysOfWeekSelector.*
git commit -m "refactor(#455): convert leaf scheduler components to TSX with typed props"
```

---

### Task 7: Convert Container Components to TSX

**Files:**
- Rename: `TriggerForm.jsx` → `.tsx`
- Rename: `RoutineCard.jsx` → `.tsx`
- Rename: `RoutineList.jsx` → `.tsx`
- Rename: `NewRoutineCard.jsx` → `.tsx`
- Rename: `ActivationPanel.jsx` → `.tsx`
- Rename corresponding test files

**Context:** These are container/orchestration components that pass data to child components. They import from `propTypes.js` — replace those imports with types from `scheduler-types.ts`. These are more complex than leaf components because they have callbacks, state, and child component interactions.

**For each component:**

Same mechanical process as Task 6, but with richer prop interfaces.

**Prop interfaces to create:**

```typescript
// TriggerForm.tsx
import type { Trigger, TriggerErrors } from './scheduler-types';
interface TriggerFormProps {
  value: Trigger;
  onChange: (value: Trigger) => void;
  disabled?: boolean;
  errors?: TriggerErrors;
}

// RoutineCard.tsx
import type { Routine } from './scheduler-types';
interface RoutineCardProps {
  routine: Routine;
  index: number;
  onUpdate: (routine: Routine) => void;
  onDelete: (routineId: string) => void;
  disabled?: boolean;
  defaultExpanded?: boolean;
  useSecondsTiming?: boolean;
}

// RoutineList.tsx
import type { Routine } from './scheduler-types';
interface RoutineListProps {
  routines: Routine[];
  onRoutineUpdate: (routine: Routine) => void;
  onRoutineDelete: (routineId: string) => void;
  onRoutineAdd: (routine: Routine) => void;
  isAddingRoutine?: boolean;
  onStartAddRoutine: () => void;
  onCancelAddRoutine: () => void;
  disabled?: boolean;
  useSecondsTiming?: boolean;
}

// NewRoutineCard.tsx
import type { Routine } from './scheduler-types';
interface NewRoutineCardProps {
  onComplete: (routine: Routine) => void;
  onCancel: () => void;
  disabled?: boolean;
  useSecondsTiming?: boolean;
}

// ActivationPanel.tsx
interface ActivationPanelProps {
  scheduleId?: string | null;
  routineCount: number;
  hasUnsavedChanges: boolean;
}
```

**Step 1: Convert all five container components**

Apply mechanical changes. For `memo()` components (RoutineCard, RoutineList, NewRoutineCard), annotate the generic: `memo<RoutineCardProps>(...)`. Remove all `import { ...PropType } from './propTypes'` lines. Remove all `.propTypes = { ... }` blocks.

**Step 2: Rename test files and update imports**

**Step 3: Run tests**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ScheduleEditor/__tests__/TriggerForm.test.tsx src/components/scheduler/ScheduleEditor/__tests__/RoutineCard.test.tsx src/components/scheduler/ScheduleEditor/__tests__/RoutineList.test.tsx src/components/scheduler/ScheduleEditor/__tests__/NewRoutineCard.test.tsx src/components/scheduler/ScheduleEditor/__tests__/ActivationPanel.test.tsx 2>&1 | tail -30`
Expected: All tests PASS

**Step 4: Commit**

```bash
git add -A webui/frontend/src/components/scheduler/ScheduleEditor/TriggerForm.* webui/frontend/src/components/scheduler/ScheduleEditor/RoutineCard.* webui/frontend/src/components/scheduler/ScheduleEditor/RoutineList.* webui/frontend/src/components/scheduler/ScheduleEditor/NewRoutineCard.* webui/frontend/src/components/scheduler/ScheduleEditor/ActivationPanel.*
git commit -m "refactor(#455): convert container scheduler components to TSX with typed props"
```

---

### Task 8: Migrate ScheduleEditor to react-hook-form + Zod + TSX

**Files:**
- Rename: `webui/frontend/src/components/scheduler/ScheduleEditor/ScheduleEditor.jsx` → `.tsx`
- Modify: `webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/ScheduleEditor.test.jsx` → `.tsx`
- Reference: `scheduleSchema` from `webui/frontend/src/schemas/scheduler/schedule.ts`

**Context:** This is the core migration — the 775-line ScheduleEditor component. Read the full file before making changes.

**What changes:**
- `useState` for `name` and `description` → `useForm<ScheduleFormData>` with `register()`
- Manual `validate()` → Zod schema validation via `handleSubmit()` + manual routines check
- `errors` state for name → `formState.errors.name?.message`
- `errors` state for routines → keep as manual state (not in form)
- `handleNameChange` / `handleDescriptionChange` → removed (handled by `register()`)
- Import PropTypes → import typed interfaces

**What stays the same:**
- `useState` for `routines`, `useSecondsTiming`, `isSaving`, `isViewMode`, `showDeleteConfirm`, `isAddingRoutine`
- All routine management callbacks
- Drawer open/close, body scroll lock, focus management
- `useValidateDraft` hook for conflict detection
- View mode / edit mode toggle
- All JSX rendering structure

**Step 1: Rename and add imports**

```typescript
import { useForm } from 'react-hook-form';
import type { Resolver } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { scheduleSchema, type ScheduleFormData } from '../../../schemas/scheduler/schedule';
import type { Schedule, Routine } from './scheduler-types';
```

**Step 2: Add typed props interface**

```typescript
interface ScheduleEditorProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (schedule: Schedule) => Promise<void>;
  onDelete?: (scheduleId: string) => Promise<void>;
  onClone?: (scheduleId: string) => Promise<void>;
  schedule?: Schedule | null;
}
```

**Step 3: Replace name/description state with useForm**

Remove:
```typescript
const [name, setName] = useState('');
const [description, setDescription] = useState('');
```

Add:
```typescript
const resolver = zodResolver(
  scheduleSchema as unknown as Parameters<typeof zodResolver>[0],
) as unknown as Resolver<ScheduleFormData>;

const {
  register,
  handleSubmit,
  reset: resetForm,
  formState: { errors: formErrors },
} = useForm<ScheduleFormData>({
  resolver,
  defaultValues: { name: '', description: '' },
  mode: 'onChange',
});
```

**Step 4: Update initialization effects**

When schedule data loads (existing `useEffect` that sets name/description from fetched schedule), replace `setName(...)` / `setDescription(...)` with `resetForm({ name: ..., description: ... })`.

When the drawer opens for a new schedule, call `resetForm({ name: '', description: '' })`.

**Step 5: Replace save handler**

Replace the old `handleSave` with a two-part approach:

```typescript
const [routineError, setRoutineError] = useState<string | null>(null);

const onSubmit = useCallback(async (formData: ScheduleFormData) => {
  // Manual routines validation (not in Zod schema)
  if (routines.length === 0) {
    setRoutineError('At least one routine is required');
    return;
  }
  if (routines.some((r) => !r.trigger || !r.actions || r.actions.length === 0)) {
    setRoutineError('All routines must have a trigger and at least one action');
    return;
  }
  setRoutineError(null);

  setIsSaving(true);
  try {
    const scheduleData = {
      schedule_id: schedule?.schedule_id || generateUUID(),
      name: formData.name,
      description: formData.description,
      routines,
      use_seconds_timing: useSecondsTiming,
    };
    await onSave(scheduleData);
  } catch (error) {
    setSaveError(getErrorMessage(error, 'Failed to save schedule'));
  } finally {
    setIsSaving(false);
  }
}, [routines, schedule, useSecondsTiming, onSave]);
```

Wire up the save button: `onClick={handleSubmit(onSubmit)}`.

**Step 6: Update JSX for name field**

Replace manual input handling:
```tsx
{/* Before */}
<input value={name} onChange={handleNameChange} />
{errors.name && <p>{errors.name}</p>}

{/* After */}
<input {...register('name')} disabled={isViewMode} />
{formErrors.name && <p>{formErrors.name.message}</p>}
```

**Step 7: Update JSX for description field**

```tsx
<textarea {...register('description')} disabled={isViewMode} />
```

**Step 8: Update error clearing for routines**

Keep the existing `useEffect` that clears routine errors when routines change, but update to use `setRoutineError(null)`.

**Step 9: Update tests**

Rename test file to `.tsx`. Key test changes:
- Name/description validation is now async (Zod) — wrap assertions in `waitFor`
- Form submission uses `handleSubmit` — may need to `await` user interactions
- Error messages come from Zod schema, not manual strings (verify exact messages match)
- Add test: submitting with empty name shows Zod validation error
- Add test: submitting with no routines shows manual routine error

**Step 10: Run tests**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ScheduleEditor/__tests__/ScheduleEditor.test.tsx 2>&1 | tail -40`
Expected: All tests PASS

**Step 11: Commit**

```bash
git add -A webui/frontend/src/components/scheduler/ScheduleEditor/ScheduleEditor.*
git commit -m "feat(#455): migrate ScheduleEditor to react-hook-form + Zod + TSX"
```

---

### Task 9: Convert SchedulerUI to TSX

**Files:**
- Rename: `webui/frontend/src/pages/SchedulerUI.jsx` → `.tsx`

**Context:** SchedulerUI is the page-level wrapper. It uses React Query mutations and passes callbacks to ScheduleEditor. The migration is mechanical: rename, add typed props (none — it's a page component), remove any PropTypes, add type annotations to state and callbacks.

**Step 1: Rename and update types**

```typescript
// Add type annotation to state
const [editingSchedule, setEditingSchedule] = useState<Schedule | null>(null);
const [editorOpen, setEditorOpen] = useState(false);
```

Import `Schedule` from the scheduler-types or from the hook's return type. Update callback parameter types.

**Step 2: Run the page's tests (if any)**

Run: `cd webui/frontend && npx vitest run --reporter=verbose 2>&1 | grep -i "schedulerui" | head -10`

Check if SchedulerUI has tests. If so, rename and update. If not, just verify the build.

**Step 3: Verify build**

Run: `cd webui/frontend && npx tsc --noEmit --pretty 2>&1 | head -30`
Expected: No TypeScript errors

**Step 4: Commit**

```bash
git add -A webui/frontend/src/pages/SchedulerUI.*
git commit -m "refactor(#455): convert SchedulerUI page to TSX"
```

---

### Task 10: Delete propTypes.js and Final Cleanup

**Files:**
- Delete: `webui/frontend/src/components/scheduler/ScheduleEditor/propTypes.js`
- Verify: No remaining imports of `propTypes.js` anywhere

**Step 1: Search for remaining propTypes imports**

Run: `cd webui/frontend && grep -r "from.*propTypes" src/components/scheduler/ --include="*.tsx" --include="*.ts" --include="*.jsx" --include="*.js"`
Expected: No results (all imports should have been removed in previous tasks)

Also check:
Run: `cd webui/frontend && grep -r "import PropTypes" src/components/scheduler/ --include="*.tsx" --include="*.ts"`
Expected: No results

**Step 2: Delete propTypes.js**

```bash
git rm webui/frontend/src/components/scheduler/ScheduleEditor/propTypes.js
```

**Step 3: Verify no remaining JSX files in ScheduleEditor/**

Run: `ls webui/frontend/src/components/scheduler/ScheduleEditor/*.jsx 2>&1`
Expected: "No such file or directory" (all converted to .tsx)

**Step 4: Run full scheduler test suite**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ src/schemas/scheduler/ src/pages/SchedulerUI* 2>&1 | tail -40`
Expected: All tests PASS

**Step 5: Run TypeScript check**

Run: `cd webui/frontend && npx tsc --noEmit --pretty 2>&1 | tail -20`
Expected: No errors

**Step 6: Run build**

Run: `cd webui/frontend && npm run build 2>&1 | tail -10`
Expected: Build succeeds

**Step 7: Commit**

```bash
git rm webui/frontend/src/components/scheduler/ScheduleEditor/propTypes.js
git add -A
git commit -m "refactor(#455): delete propTypes.js, complete scheduler TSX migration"
```

---

### Task 11: Final Verification

**Step 1: Run full frontend test suite**

Run: `cd webui/frontend && npx vitest run 2>&1 | tail -30`
Expected: All tests PASS, no regressions

**Step 2: Run linter**

Run: `cd webui/frontend && npx eslint src/components/scheduler/ src/pages/SchedulerUI.tsx src/schemas/scheduler/ 2>&1 | tail -20`
Expected: No errors (warnings OK)

**Step 3: Verify no leftover .jsx files in scope**

Run: `ls webui/frontend/src/components/scheduler/ScheduleEditor/*.jsx webui/frontend/src/pages/SchedulerUI.jsx 2>&1`
Expected: All "No such file" — everything converted

**Step 4: Summary check**

Verify acceptance criteria from issue #455:
- [ ] Top-level schedule schema composes sub-schemas
- [ ] FormProvider wraps scheduler (N/A — chose independent forms per design)
- [ ] Cross-routine validation (conflicts) preserved
- [ ] SchedulerUI: .jsx → .tsx
- [ ] Relevant scheduler sub-components: .jsx → .tsx
- [ ] Tests updated
- [ ] All tests pass

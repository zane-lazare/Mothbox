# Scheduler Type Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove `as any` casts from TriggerForm, migrate routineUtils to TypeScript, and convert ScheduleCard to TSX — closing #490 and #491.

**Architecture:** Three independent commits in one PR. Task 1 replaces `as any` with discriminated-union narrowing and specific type casts. Task 2 renames routineUtils.js → .ts with type annotations and removes `@ts-expect-error` from TSX consumers. Task 3 converts ScheduleCard.jsx → .tsx, replacing PropTypes with a TypeScript interface.

**Tech Stack:** TypeScript, React, Vitest

---

### Task 1: TriggerForm type narrowing (#490)

**Files:**
- Modify: `webui/frontend/src/components/scheduler/ScheduleEditor/TriggerForm.tsx:150-171`

**Context:**

The `renderTriggerForm()` switch statement (lines 150-171) uses `as any` on `value`, `onChange`, and `errors` for all 5 cases plus default. Each sub-form expects its own value/onChange/errors types:

| Case | Value type | onChange type | Errors type |
|------|-----------|--------------|-------------|
| `interval` | `IntervalTriggerValue` | `(v: IntervalTriggerValue) => void` | `Record<string, string \| Record<string, string>>` |
| `solar` | `SolarTriggerValue` | `(v: SolarTriggerValue) => void` | `Record<string, string>` |
| `moon_phase` | `MoonPhaseTriggerValue` | `(v: MoonPhaseTriggerValue) => void` | `Record<string, string>` |
| `fixed_time` | `FixedTimeTriggerValue` | `(v: FixedTimeTriggerValue) => void` | `TriggerErrors` |
| `sensor` | `SensorTriggerValue` | `(v: SensorTriggerValue) => void` | `TriggerErrors` |

The `handleTriggerValueChange` is typed `(newValue: Trigger) => void`. Sub-forms call onChange with their specific value type (e.g., `IntervalTriggerValue`), which is NOT assignable to `Trigger`. So `onChange` needs a double cast: `as unknown as (v: XxxValue) => void`.

For `value`, each sub-form expects `value?: XxxValue`. Since the switch narrows `triggerType`, we can cast `value as IntervalTrigger` etc., which is structurally compatible with each `XxxValue` (they share the same fields minus `trigger_type` and `days_of_week`).

For `errors`, `TriggerErrors` is a superset of all sub-form error types, so a single cast suffices.

**Step 1: Add value type imports**

Add imports for the sub-form value types at the top of TriggerForm.tsx (after line 8):

```typescript
import type { IntervalTriggerValue } from './IntervalTriggerForm';
import type { SolarTriggerValue } from './SolarTriggerForm';
import type { MoonPhaseTriggerValue } from './MoonPhaseTriggerForm';
import type { FixedTimeTriggerValue } from './FixedTimeTriggerForm';
import type { SensorTriggerValue } from './SensorTriggerForm';
```

Also add imports for the specific trigger interfaces from scheduler-types:

```typescript
import type { Trigger, TriggerErrors, TriggerType, IntervalTrigger, SolarTrigger, MoonPhaseTrigger, FixedTimeTrigger, SensorTrigger } from './scheduler-types';
```

(Merge with existing import on line 3.)

**Step 2: Replace the switch statement**

Replace lines 150-171 with narrowed casts:

```tsx
  const renderTriggerForm = () => {
    switch (triggerType) {
      case 'interval':
        return <IntervalTriggerForm value={value as IntervalTrigger as IntervalTriggerValue} onChange={handleTriggerValueChange as unknown as (v: IntervalTriggerValue) => void} disabled={disabled} errors={errors as Record<string, string | Record<string, string>>} />;
      case 'solar':
        return <SolarTriggerForm value={value as SolarTrigger as SolarTriggerValue} onChange={handleTriggerValueChange as unknown as (v: SolarTriggerValue) => void} disabled={disabled} errors={errors as Record<string, string>} />;
      case 'moon_phase':
        return <MoonPhaseTriggerForm value={value as MoonPhaseTrigger as MoonPhaseTriggerValue} onChange={handleTriggerValueChange as unknown as (v: MoonPhaseTriggerValue) => void} disabled={disabled} errors={errors as Record<string, string>} />;
      case 'fixed_time':
        return <FixedTimeTriggerForm value={value as FixedTimeTrigger as FixedTimeTriggerValue} onChange={handleTriggerValueChange as unknown as (v: FixedTimeTriggerValue) => void} disabled={disabled} errors={errors} />;
      case 'sensor':
        return <SensorTriggerForm value={value as SensorTrigger as SensorTriggerValue} onChange={handleTriggerValueChange as unknown as (v: SensorTriggerValue) => void} disabled={disabled} errors={errors} />;
      default:
        return <IntervalTriggerForm value={value as IntervalTrigger as IntervalTriggerValue} onChange={handleTriggerValueChange as unknown as (v: IntervalTriggerValue) => void} disabled={disabled} errors={errors as Record<string, string | Record<string, string>>} />;
    }
  };
```

Key changes:
- Remove the `eslint-disable` / `eslint-enable` block
- Remove the comment block above the switch (lines 151-154)
- `value as IntervalTrigger as IntervalTriggerValue` — double cast through the specific trigger type
- `handleTriggerValueChange as unknown as (v: XxxValue) => void` — bridges `(Trigger) => void` to sub-form's specific callback
- `errors` passes through unchanged for `fixed_time`/`sensor` (they already accept `TriggerErrors`), cast for others
- Default case uses same casts as `interval`

**Step 3: Run type check**

Run: `cd webui/frontend && npx tsc --noEmit 2>&1 | head -30`
Expected: No errors in TriggerForm.tsx

**Step 4: Run existing tests**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ScheduleEditor/__tests__/TriggerForm.test.tsx 2>&1 | tail -20`
Expected: All existing tests pass (this is a type-only change, no runtime behavior changes)

**Step 5: Commit**

```bash
git add webui/frontend/src/components/scheduler/ScheduleEditor/TriggerForm.tsx
git commit -m "$(cat <<'EOF'
fix(#490): replace as-any casts with discriminated-union narrowing in TriggerForm

Switch cases now use specific trigger type casts (e.g., `value as IntervalTrigger`)
and double-cast onChange callbacks through `unknown` to each sub-form's value type.
Removes eslint-disable block for @typescript-eslint/no-explicit-any.
EOF
)"
```

---

### Task 2: Migrate routineUtils.js to TypeScript

**Files:**
- Rename: `webui/frontend/src/utils/routineUtils.js` → `webui/frontend/src/utils/routineUtils.ts`
- Rename: `webui/frontend/src/utils/__tests__/routineUtils.test.js` → `webui/frontend/src/utils/__tests__/routineUtils.test.ts`
- Modify: `webui/frontend/src/components/scheduler/ScheduleEditor/RoutineCard.tsx:19-20` (remove `@ts-expect-error`)
- Modify: `webui/frontend/src/components/scheduler/ScheduleEditor/TriggerLabel.tsx:11-12` (remove `@ts-expect-error`)

**Context:**

`routineUtils.js` (248 lines) exports pure display utilities:
- `getTriggerLabel(trigger)` — returns human-readable trigger label
- `getActionColor(actionType)` — returns Tailwind color class
- `getPrimaryActionColor(actions)` — returns color for first action
- `summarizeActions(actions)` — returns summary string
- `describeTrigger(trigger)` — returns full trigger description
- `generateRoutineName(routine)` — generates display name from trigger + actions
- `generateScheduleDescription(schedule)` — generates schedule description from routines

Constants: `TRIGGER_LABELS`, `ACTION_COLORS`, `ACTION_NAME_MAP`, `ACTION_SHORT_LABELS`, `SOLAR_EVENT_MAP`

6 consumers (3 .tsx, 3 .jsx):
- `RoutineCard.tsx` — imports `generateRoutineName`, `getActionColor` (has `@ts-expect-error`)
- `TriggerLabel.tsx` — imports `getTriggerLabel` (has `@ts-expect-error`)
- `ScheduleCard.jsx` — imports `getActionColor`, `generateRoutineName`, `generateScheduleDescription`
- `ExecutionMarker.jsx` — imports `getActionColor`
- `CalendarCell.jsx` — imports `getActionColor`
- `ExecutionChip.jsx` — imports `getActionColor`

The .jsx consumers don't need changes (they don't use `@ts-expect-error`). The 2 .tsx consumers each have a `// @ts-expect-error -- .js module` line that must be removed.

Types needed from `scheduler-types.ts`: `Trigger`, `RoutineAction`, `Routine`, `Schedule`. Also imports from `@/components/scheduler/constants` (already .ts).

**Step 1: Rename files**

```bash
cd webui/frontend
git mv src/utils/routineUtils.js src/utils/routineUtils.ts
git mv src/utils/__tests__/routineUtils.test.js src/utils/__tests__/routineUtils.test.ts
```

**Step 2: Add type annotations to routineUtils.ts**

Add import at top:

```typescript
import type { Trigger, RoutineAction, Routine, Schedule } from '@/components/scheduler/ScheduleEditor/scheduler-types'
```

Add types to constants:

```typescript
export const TRIGGER_LABELS: Record<string, string> = { ... }
export const ACTION_COLORS: Record<string, string> = { ... }
export const ACTION_NAME_MAP: Record<string, string> = { ... }
export const ACTION_SHORT_LABELS: Record<string, string> = { ... }
export const SOLAR_EVENT_MAP: Record<string, string> = { ... }
```

Add function signatures:

```typescript
export function getTriggerLabel(trigger: Trigger | undefined | null): string
export function getActionColor(actionType: string): string
export function getPrimaryActionColor(actions: RoutineAction[] | undefined | null): string
export function summarizeActions(actions: RoutineAction[] | undefined | null): string
export function describeTrigger(trigger: Trigger | undefined | null): string
export function generateRoutineName(routine: Routine | undefined | null): string
export function generateScheduleDescription(schedule: Schedule | undefined | null): string
```

Note: Check the actual function bodies for null/undefined handling. The functions likely use optional chaining or fallback values. Add `| undefined | null` to params that have guard clauses. Add minimal internal type annotations only where tsc complains (e.g., loop variables, destructured params).

**Step 3: Remove @ts-expect-error from TSX consumers**

In `RoutineCard.tsx`, remove line 19 (`// @ts-expect-error -- .js module`) so line 20's import stands alone:
```typescript
import { generateRoutineName, getActionColor } from '@/utils/routineUtils'
```

In `TriggerLabel.tsx`, remove line 11 (`// @ts-expect-error -- .js module`) so line 12's import stands alone:
```typescript
import { getTriggerLabel } from '@/utils/routineUtils'
```

**Step 4: Run type check**

Run: `cd webui/frontend && npx tsc --noEmit 2>&1 | head -40`
Expected: No errors in routineUtils.ts or its consumers

**Step 5: Run tests**

Run: `cd webui/frontend && npx vitest run src/utils/__tests__/routineUtils.test.ts 2>&1 | tail -20`
Expected: All existing tests pass (rename only, no logic changes)

**Step 6: Commit**

```bash
git add -A webui/frontend/src/utils/routineUtils.ts webui/frontend/src/utils/routineUtils.js \
  webui/frontend/src/utils/__tests__/routineUtils.test.ts webui/frontend/src/utils/__tests__/routineUtils.test.js \
  webui/frontend/src/components/scheduler/ScheduleEditor/RoutineCard.tsx \
  webui/frontend/src/components/scheduler/ScheduleEditor/TriggerLabel.tsx
git commit -m "$(cat <<'EOF'
refactor: migrate routineUtils.js to TypeScript

Add type annotations using Trigger, RoutineAction, Routine, Schedule types
from scheduler-types.ts. Remove @ts-expect-error from RoutineCard.tsx and
TriggerLabel.tsx consumers. Rename test file to .test.ts.
EOF
)"
```

---

### Task 3: Convert ScheduleCard.jsx to TSX (#491)

**Files:**
- Rename: `webui/frontend/src/components/scheduler/ScheduleList/ScheduleCard.jsx` → `ScheduleCard.tsx`
- Rename: `webui/frontend/src/components/scheduler/ScheduleList/__tests__/ScheduleCard.test.jsx` → `ScheduleCard.test.tsx`
- Modify: `ScheduleCard.tsx` (replace PropTypes with interface, add type imports)

**Context:**

ScheduleCard.jsx (187 lines) is a `memo`-wrapped component with these props (from PropTypes on lines 174-185):

```typescript
interface ScheduleCardProps {
  schedule: Schedule
  isActive?: boolean
  onView: (scheduleId: string) => void
  onToggleEnabled?: (scheduleId: string, enabled: boolean) => void
  isTogglingEnabled?: boolean
}
```

The component accesses:
- `schedule.schedule_id`, `.name`, `.description`, `.enabled`, `.routines`
- `routine.routine_id`, `.actions` (via `routines` array)

Imports from `routineUtils` (now .ts after Task 2): `getActionColor`, `generateRoutineName`, `generateScheduleDescription`.

The `Schedule` type from `scheduler-types.ts` already has all the fields used. The `.enabled` field is `enabled?: boolean` in the type.

**Step 1: Rename files**

```bash
cd webui/frontend
git mv src/components/scheduler/ScheduleList/ScheduleCard.jsx src/components/scheduler/ScheduleList/ScheduleCard.tsx
git mv src/components/scheduler/ScheduleList/__tests__/ScheduleCard.test.jsx src/components/scheduler/ScheduleList/__tests__/ScheduleCard.test.tsx
```

**Step 2: Replace PropTypes with TypeScript interface**

In ScheduleCard.tsx:

1. Remove `import PropTypes from 'prop-types'` (line 18)

2. Add type imports:
```typescript
import type { Schedule } from '../../ScheduleEditor/scheduler-types'
```

3. Add interface before the component (replace lines 28-40 area):
```typescript
interface ScheduleCardProps {
  schedule: Schedule
  isActive?: boolean
  onView: (scheduleId: string) => void
  onToggleEnabled?: (scheduleId: string, enabled: boolean) => void
  isTogglingEnabled?: boolean
}
```

4. Type the component parameter:
```typescript
const ScheduleCard = ({ schedule, isActive = false, onView, onToggleEnabled, isTogglingEnabled = false }: ScheduleCardProps) => {
```

5. Remove the PropTypes block (lines 173-185) including the TODO comment on line 173.

6. Update the `import` path for routineUtils — change `'../../../utils/routineUtils'` to `'@/utils/routineUtils'` for consistency with the .tsx consumers (RoutineCard.tsx uses `@/utils/routineUtils`).

7. Check for any inline type issues: the `useCallback` for `handleViewClick` and `handleToggleClick` may need explicit return types or parameter types if tsc complains. Add them only if needed.

**Step 3: Run type check**

Run: `cd webui/frontend && npx tsc --noEmit 2>&1 | head -40`
Expected: No errors in ScheduleCard.tsx

**Step 4: Run tests**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ScheduleList/__tests__/ScheduleCard.test.tsx 2>&1 | tail -30`
Expected: All 714 lines of existing tests pass (rename + type-only changes)

**Step 5: Commit**

```bash
git add -A webui/frontend/src/components/scheduler/ScheduleList/ScheduleCard.tsx \
  webui/frontend/src/components/scheduler/ScheduleList/ScheduleCard.jsx \
  webui/frontend/src/components/scheduler/ScheduleList/__tests__/ScheduleCard.test.tsx \
  webui/frontend/src/components/scheduler/ScheduleList/__tests__/ScheduleCard.test.jsx
git commit -m "$(cat <<'EOF'
refactor(#491): convert ScheduleCard to TSX with typed props

Replace PropTypes with ScheduleCardProps interface using Schedule type
from scheduler-types.ts. Remove prop-types import. Rename test file
to .test.tsx.
EOF
)"
```

---

### Task 4: Final verification and PR

**Step 1: Run full type check**

Run: `cd webui/frontend && npx tsc --noEmit 2>&1 | tail -10`
Expected: No errors

**Step 2: Run ESLint**

Run: `cd webui/frontend && npx eslint src/components/scheduler/ScheduleEditor/TriggerForm.tsx src/utils/routineUtils.ts src/components/scheduler/ScheduleList/ScheduleCard.tsx 2>&1 | tail -10`
Expected: No errors or warnings

**Step 3: Run all affected tests**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ScheduleEditor/__tests__/TriggerForm.test.tsx src/utils/__tests__/routineUtils.test.ts src/components/scheduler/ScheduleList/__tests__/ScheduleCard.test.tsx 2>&1 | tail -20`
Expected: All tests pass

**Step 4: Push and create PR**

```bash
git push -u origin HEAD
gh pr create --title "refactor(#490,#491): scheduler type cleanup" --body "$(cat <<'EOF'
## Summary
- **TriggerForm (#490)**: Replace `as any` casts with discriminated-union narrowing — specific trigger type casts and double-cast onChange callbacks
- **routineUtils**: Migrate .js → .ts with type annotations, remove `@ts-expect-error` from 2 TSX consumers
- **ScheduleCard (#491)**: Convert .jsx → .tsx, replace PropTypes with TypeScript interface using `Schedule` type

## Test plan
- [ ] `npx tsc --noEmit` passes with no errors
- [ ] `npx eslint` passes on all modified files
- [ ] TriggerForm tests pass
- [ ] routineUtils tests pass
- [ ] ScheduleCard tests pass
- [ ] CI passes (lint, typecheck, test)

Closes #490
Closes #491
EOF
)"
```

# Consolidate Scheduler Components Design

**Issue**: #197 (parent), new issues TBD
**Date**: 2026-03-07
**Status**: Design approved, pending implementation

## Problem

The Zod + React Hook Form migration (Phases 1-3) created new `.tsx` trigger forms inside `ScheduleEditor/` but left the original `TriggerSelector/` `.jsx` forms in place. The migrated `RoutineCard.tsx` and `NewRoutineCard.tsx` still import the old `.jsx` components with `@ts-expect-error` suppressions:

```typescript
// RoutineCard.tsx, NewRoutineCard.tsx — current state
// @ts-expect-error -- .js module
import TriggerSelector from '../TriggerSelector'
// @ts-expect-error -- .jsx module
import ActionList from '../RoutineEditor/ActionList'
// @ts-expect-error -- .js module
import { createDefaultTrigger, validateTrigger } from '../TriggerSelector/constants'
```

Additionally, `RoutineEditor.jsx`, `ActionForm.jsx`, and `OffsetTimeline.jsx` have no production consumers — only their own tests import them. They are dead code from an earlier UI that was superseded by `ScheduleEditor/`.

### Component Dependency Graph (Current)

```
ScheduleEditor.tsx
  └── RoutineList.tsx
        ├── RoutineCard.tsx ──────────┬── TriggerSelector.jsx (.jsx, @ts-expect-error)
        │                             │     ├── IntervalTriggerForm.jsx
        │                             │     ├── SolarTriggerForm.jsx
        │                             │     ├── MoonPhaseTriggerForm.jsx
        │                             │     ├── FixedTimeTriggerForm.jsx
        │                             │     ├── RecurringDaysTriggerForm.jsx
        │                             │     └── CronTriggerForm.jsx
        │                             └── ActionList.jsx (.jsx, @ts-expect-error)
        │                                   └── InlineActionRow.jsx
        └── NewRoutineCard.tsx ───────┬── TriggerSelector.jsx (same)
                                      ├── ActionList.jsx (same)
                                      └── constants.js (createDefaultTrigger, validateTrigger)

TriggerForm.tsx (ORPHANED — tested but unused in production)
  ├── IntervalTriggerForm.tsx (ScheduleEditor/)
  ├── SolarTriggerForm.tsx (ScheduleEditor/)
  ├── MoonPhaseTriggerForm.tsx (ScheduleEditor/)
  ├── FixedTimeTriggerForm.tsx (ScheduleEditor/)
  └── SensorTriggerForm.tsx (ScheduleEditor/)

RoutineEditor.jsx (DEAD — only imported in RoutineEditor.test.jsx)
ActionForm.jsx (DEAD — only imported in ActionForm.test.jsx)
OffsetTimeline.jsx (DEAD — only imported in OffsetTimeline.test.jsx)
```

### Parallel Implementations

Two complete sets of trigger forms exist:

| Trigger Type | TriggerSelector/ (.jsx) | ScheduleEditor/ (.tsx) |
|---|---|---|
| Interval | IntervalTriggerForm.jsx | IntervalTriggerForm.tsx |
| Solar | SolarTriggerForm.jsx | SolarTriggerForm.tsx |
| Moon Phase | MoonPhaseTriggerForm.jsx | MoonPhaseTriggerForm.tsx |
| Fixed Time | FixedTimeTriggerForm.jsx | FixedTimeTriggerForm.tsx |
| Sensor | — | SensorTriggerForm.tsx |
| Cron | CronTriggerForm.jsx | CronExpressionInput.tsx |
| Recurring Days | RecurringDaysTriggerForm.jsx | — |

The `.tsx` versions use react-hook-form + Zod. The `.jsx` versions use PropTypes + manual validation via `TriggerSelector/constants.js::validateTrigger()`.

Two dispatcher components exist:
- `TriggerSelector.jsx`: Used by `RoutineCard`/`NewRoutineCard`, dispatches to `.jsx` sub-forms
- `TriggerForm.tsx`: Dispatches to `.tsx` sub-forms, but is **not imported by any production code** — only by `TriggerForm.test.tsx`

## Solution

### Phase A: Delete Dead Code

Remove components with no production consumers:
- `RoutineEditor/RoutineEditor.jsx` + test
- `RoutineEditor/ActionForm.jsx` + test
- `RoutineEditor/OffsetTimeline.jsx` + test

### Phase B: Replace TriggerSelector with TriggerForm

Rewire `RoutineCard.tsx` and `NewRoutineCard.tsx` to use the existing `TriggerForm.tsx` instead of `TriggerSelector.jsx`.

**Prop interface difference:**
- `TriggerSelector`: `trigger` / `onChange` / `disabled` / `error`
- `TriggerForm`: `value` / `onChange` / `disabled` / `errors`

This is a rename (`trigger` → `value`, `error` → `errors`) plus the `TriggerForm` version accepts structured `TriggerErrors` instead of a single string.

**`validateTrigger()` replacement:** `NewRoutineCard` calls `validateTrigger(trigger)` from `TriggerSelector/constants.js` to validate before save. This can be replaced by parsing the trigger through the appropriate Zod schema from `src/schemas/scheduler/`.

**`createDefaultTrigger()` replacement:** `NewRoutineCard` calls `createDefaultTrigger('interval')` for initial state. `TriggerForm` uses `TRIGGER_DEFAULTS` from `ScheduleEditor/constants.ts`. The `NewRoutineCard` can import and use these directly.

**`recurring_days` gap:** `TriggerSelector` supports `recurring_days` trigger type. `TriggerForm.tsx` does not have a `RecurringDaysTriggerForm.tsx` equivalent — it falls through to the default (interval) case. Either:
1. The `recurring_days` case must be added to `TriggerForm.tsx`, OR
2. `RecurringDaysTriggerForm.jsx` must be converted to `.tsx` and added to `TriggerForm`

Option 2 is the correct approach since `recurring_days` is a valid backend trigger type.

### Phase C: Migrate ActionList + InlineActionRow to .tsx

Convert `ActionList.jsx` and `InlineActionRow.jsx` to TypeScript. These are simple controlled components — no react-hook-form needed. Move them into `ScheduleEditor/` since that's their only consumer.

### Phase D: Delete TriggerSelector/

After Phases B and C, delete the entire `TriggerSelector/` directory (7 `.jsx` files + 7 test files + `constants.js`).

### Target Component Graph (After)

```
ScheduleEditor.tsx
  └── RoutineList.tsx
        ├── RoutineCard.tsx ──── TriggerForm.tsx (.tsx, no @ts-expect-error)
        │                         ├── IntervalTriggerForm.tsx
        │                         ├── SolarTriggerForm.tsx
        │                         ├── MoonPhaseTriggerForm.tsx
        │                         ├── FixedTimeTriggerForm.tsx
        │                         ├── SensorTriggerForm.tsx
        │                         ├── RecurringDaysTriggerForm.tsx (NEW)
        │                         └── CronExpressionInput.tsx
        │                   ──── ActionList.tsx (.tsx, moved from RoutineEditor/)
        │                         └── InlineActionRow.tsx (.tsx)
        └── NewRoutineCard.tsx ── (same as RoutineCard)
```

## Issue Breakdown

### Issue 1: Remove dead RoutineEditor components

**Scope:** Delete `RoutineEditor.jsx`, `ActionForm.jsx`, `OffsetTimeline.jsx` and their test files. Keep `ActionList.jsx`, `InlineActionRow.jsx`, and `constants.js` (still have production consumers).

**Files deleted:**
- `scheduler/RoutineEditor/RoutineEditor.jsx`
- `scheduler/RoutineEditor/ActionForm.jsx`
- `scheduler/RoutineEditor/OffsetTimeline.jsx`
- `scheduler/RoutineEditor/__tests__/RoutineEditor.test.jsx`
- `scheduler/RoutineEditor/__tests__/ActionForm.test.jsx`
- `scheduler/RoutineEditor/__tests__/OffsetTimeline.test.jsx`

**Verification:** `grep -r "RoutineEditor\|ActionForm\|OffsetTimeline"` finds only the deleted files and internal references within the deleted tests. No production imports break.

### Issue 2: Create RecurringDaysTriggerForm.tsx in ScheduleEditor

**Scope:** Convert `TriggerSelector/RecurringDaysTriggerForm.jsx` to a `.tsx` version in `ScheduleEditor/` following the established pattern (TypeScript interfaces, no react-hook-form — matches how it's used as a controlled sub-form). Create Zod schema `src/schemas/scheduler/recurring-days.ts`. Add to `TriggerForm.tsx`'s switch statement.

**Files created:**
- `scheduler/ScheduleEditor/RecurringDaysTriggerForm.tsx`
- `scheduler/ScheduleEditor/__tests__/RecurringDaysTriggerForm.test.tsx`
- `src/schemas/scheduler/recurring-days.ts`
- `src/schemas/scheduler/__tests__/recurring-days.test.ts`

**Files modified:**
- `scheduler/ScheduleEditor/TriggerForm.tsx` (add `recurring_days` case)
- `scheduler/ScheduleEditor/scheduler-types.ts` (already has `RecurringDaysTrigger` — no change needed)

### Issue 3: Replace TriggerSelector with TriggerForm in RoutineCard/NewRoutineCard

**Scope:** Rewire `RoutineCard.tsx` and `NewRoutineCard.tsx` to import `TriggerForm` instead of `TriggerSelector`. Replace `validateTrigger()` with Zod schema parsing. Replace `createDefaultTrigger()` with `TRIGGER_DEFAULTS` from `ScheduleEditor/constants.ts`. Remove all `@ts-expect-error` comments for TriggerSelector and constants imports.

**Files modified:**
- `scheduler/ScheduleEditor/RoutineCard.tsx`
- `scheduler/ScheduleEditor/NewRoutineCard.tsx`

**Blocked by:** Issue 2 (RecurringDaysTriggerForm.tsx must exist before TriggerForm can handle all trigger types)

### Issue 4: Migrate ActionList and InlineActionRow to TypeScript

**Scope:** Convert `ActionList.jsx` → `ActionList.tsx` and `InlineActionRow.jsx` → `InlineActionRow.tsx`. Move into `ScheduleEditor/` directory. Replace PropTypes with TypeScript interfaces using existing `RoutineAction` type from `scheduler-types.ts`. Migrate tests from `.test.jsx` to `.test.tsx`. Update imports in `RoutineCard.tsx` and `NewRoutineCard.tsx`. Move `RoutineEditor/constants.js` → `ScheduleEditor/action-constants.ts` (or merge into existing `ScheduleEditor/constants.ts`).

**Files created:**
- `scheduler/ScheduleEditor/ActionList.tsx`
- `scheduler/ScheduleEditor/InlineActionRow.tsx`
- `scheduler/ScheduleEditor/__tests__/ActionList.test.tsx`
- `scheduler/ScheduleEditor/__tests__/InlineActionRow.test.tsx`

**Files deleted (after move):**
- `scheduler/RoutineEditor/ActionList.jsx`
- `scheduler/RoutineEditor/InlineActionRow.jsx`
- `scheduler/RoutineEditor/__tests__/ActionList.test.jsx`
- `scheduler/RoutineEditor/__tests__/InlineActionRow.test.jsx` (if exists)

**Files modified:**
- `scheduler/ScheduleEditor/RoutineCard.tsx` (update import path, remove `@ts-expect-error`)
- `scheduler/ScheduleEditor/NewRoutineCard.tsx` (update import path, remove `@ts-expect-error`)

### Issue 5: Delete TriggerSelector directory and remaining RoutineEditor files

**Scope:** Delete the entire `TriggerSelector/` directory and remaining `RoutineEditor/` files/directory. This is the cleanup step after all consumers have been rewired.

**Files deleted:**
- `scheduler/TriggerSelector/` (entire directory: 7 `.jsx` components, `constants.js`, 7 test files, `index.js` if present)
- `scheduler/RoutineEditor/constants.js` (consumers migrated to ScheduleEditor constants)
- `scheduler/RoutineEditor/` directory (should be empty after Issues 1 and 4)

**Blocked by:** Issues 3 and 4 (all consumers must be rewired first)

**Verification:** `grep -rn "TriggerSelector\|RoutineEditor" src/components/scheduler/` returns zero hits outside test mocks and the deleted directory.

## Dependency Graph

```
Issue 1 (delete dead code) ─────────────────────────────────┐
                                                             │
Issue 2 (RecurringDaysTriggerForm.tsx) ──┐                   │
                                         ├── Issue 3 ───┐   │
                                         │   (rewire     │   │
                                         │   TriggerForm)│   │
                                         │              ├── Issue 5 (delete TriggerSelector/)
Issue 4 (ActionList.tsx) ───────────────┘               │
                                                        │
                                                        └──────────────────────────────────
```

Issue 1 is independent. Issues 2 and 4 are independent of each other. Issue 3 depends on 2. Issue 5 depends on 3 and 4.

## Risk Assessment

**Low risk:**
- Issue 1: Pure deletion of unused code
- Issue 5: Pure deletion after all consumers rewired

**Medium risk:**
- Issue 2: New component, but follows established pattern from 5 existing `.tsx` trigger forms
- Issue 4: Mechanical `.jsx` → `.tsx` conversion of simple controlled components

**Higher risk:**
- Issue 3: Changes rendering logic in `RoutineCard`/`NewRoutineCard`. Prop interface difference (`trigger`→`value`, `error`→`errors`) requires careful testing. `TriggerForm.tsx` includes expert mode toggle and visual/cron switching that `TriggerSelector` doesn't have — may need UI adjustment to fit the compact RoutineCard context.

### Mitigation for Issue 3

`TriggerForm.tsx` renders a header ("Trigger Configuration"), expert mode toggle, and type description that are appropriate for the full ScheduleEditor drawer but too heavy for the inline RoutineCard. Options:
1. Add props to `TriggerForm` to hide header/expert-mode (`compact` or `showHeader` flag)
2. Have RoutineCard render the type selector directly and use individual trigger forms (bypass TriggerForm entirely)

Option 1 is simpler and keeps the single dispatcher pattern. A `compact?: boolean` prop that hides header, expert toggle, and description.

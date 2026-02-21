# Form Validation Standardization Design

**Issue**: #197
**Date**: 2026-02-21
**Status**: Design approved, pending implementation planning

## Decision Summary

| Decision | Choice |
|---|---|
| Libraries | react-hook-form + Zod + @hookform/resolvers |
| Migration strategy | Foundation first, then one PR per form |
| Issue granularity | One issue per form |
| Old utilities | Replace entirely, delete in cleanup phase |
| New files | All `.ts`/`.tsx` |
| Migrated forms | `.jsx` → `.tsx` |
| Test files | `.test.jsx` → `.test.tsx` |
| TS tooling | Separate Phase 0 issue (prerequisite) |
| Error display | Shared `FormField` component with aria attributes |
| Validation mode | `onBlur` default, `onChange` where current UX requires it |
| Form patterns | Three: modal (uncontrolled), controlled (scheduler), hybrid (prop-synced) |

## Problem

The frontend has 18 forms using 5 different validation patterns:

1. **useState with utility functions** (GPSSettings)
2. **Inline validation functions** (SavePresetModal)
3. **useEffect-based validation** (DeploymentEditor)
4. **Button disable logic only** (BulkSpeciesModal)
5. **HTML required attributes only** (Scheduler)

Validation utilities return inconsistent types: `{ valid, error }` vs error arrays vs validation objects. Error display, accessibility, and dirty tracking are ad-hoc per form.

## Architecture

### New File Structure

```
src/
├── schemas/                          # Zod validation schemas (.ts)
│   ├── preset.ts                     # SavePresetModal, SaveFilterPresetModal
│   ├── tag.ts                        # BulkTagModal
│   ├── species.ts                    # BulkSpeciesModal, MetadataSpecies
│   ├── coordinates.ts                # CoordinateInput (replaces gpsCoordinates.ts)
│   ├── gps-settings.ts              # GPSSettings (replaces gpsValidation.js)
│   ├── deployment.ts                 # DeploymentEditor
│   ├── export-options.ts            # FormatOptionsPanel
│   ├── camera-preset.ts             # SavePresetModal (camera)
│   ├── search.ts                     # AdvancedSearchBuilder
│   ├── scheduler/                    # Scheduler sub-schemas
│   │   ├── interval.ts
│   │   ├── solar.ts
│   │   ├── moon-phase.ts
│   │   ├── time-window.ts
│   │   ├── cron.ts
│   │   └── pre-condition.ts
│   └── index.ts                      # Re-exports
├── hooks/
│   ├── useFormField.ts              # Shared controlled-field hook (wraps useController)
│   └── useCronValidation.ts         # Existing hook, migrated to .ts
├── components/
│   └── form/                         # Shared form primitives (.tsx)
│       ├── FormField.tsx             # Label + input + error message wrapper
│       ├── FormSelect.tsx            # Select with validation
│       └── FormNumberInput.tsx       # Number input with min/max from schema
```

### Schema Pattern

Every schema follows this pattern — Zod schema as single source of truth for validation rules and TypeScript types:

```typescript
// src/schemas/species.ts
import { z } from 'zod';
import { METADATA_VALIDATION, SPECIES_CONFIG } from '../constants/config';

export const speciesSchema = z.object({
  species: z.string().max(METADATA_VALIDATION.MAX_SPECIES_LENGTH).optional(),
  commonName: z.string().max(METADATA_VALIDATION.MAX_COMMON_NAME_LENGTH).optional(),
  confidence: z.enum(['certain', 'probable', 'possible', 'unknown']),
  referenceUrl: z.string().url().max(METADATA_VALIDATION.MAX_REFERENCE_URL_LENGTH)
    .optional().or(z.literal('')),
});

export type SpeciesFormData = z.infer<typeof speciesSchema>;
```

Schemas import existing constants from `config.js` — no duplication of validation limits.

### Three Form Integration Patterns

#### Pattern 1: Modal (Uncontrolled)

For forms that own their state and call parent only on submit.

**Used by**: SavePresetModal, SaveFilterPresetModal, BulkSpeciesModal, BulkTagModal, AdvancedSearchBuilder.

```tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { speciesSchema, type SpeciesFormData } from '../schemas/species';

function BulkSpeciesModal({ onApply, onClose }) {
  const { register, handleSubmit, formState: { errors, isDirty } } = useForm<SpeciesFormData>({
    resolver: zodResolver(speciesSchema),
    defaultValues: { confidence: 'unknown' },
    mode: 'onBlur',
  });

  return (
    <form onSubmit={handleSubmit(onApply)}>
      <FormField name="species" error={errors.species}>
        <input {...register('species')} />
      </FormField>
      <button type="submit" disabled={!isDirty}>Apply</button>
    </form>
  );
}
```

#### Pattern 2: Controlled (Parent-Owned State)

For scheduler sub-forms where the parent owns state and expects updates on every change.

**Used by**: IntervalTriggerForm, SolarTriggerForm, MoonPhaseTriggerForm, TimeWindowInput, PreConditionForm, CronExpressionInput, FormatOptionsPanel.

```tsx
import { useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

function IntervalTriggerForm({ value, onChange, errors: parentErrors }) {
  const { control, formState: { errors } } = useForm({
    resolver: zodResolver(intervalSchema),
    defaultValues: value,
    mode: 'onChange', // Validate on every change for live feedback
  });

  // Sync form changes back to parent
  const watched = useWatch({ control });
  useEffect(() => {
    onChange(watched);
  }, [watched, onChange]);

  return (
    <FormField name="interval_minutes" error={errors.interval_minutes}>
      <Controller name="interval_minutes" control={control}
        render={({ field }) => <input type="number" {...field} />}
      />
    </FormField>
  );
}
```

#### Pattern 3: Hybrid (Prop-Synced)

For forms with local state that syncs with async data (query results, parent prop changes).

**Used by**: MetadataSpecies, CoordinateInput, GPSSettings, DeploymentEditor.

```tsx
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

function GPSSettings() {
  const { data: gpsConfig } = useQuery({ queryKey: ['gps-config'], ... });
  const { control, reset, formState: { errors, isDirty } } = useForm({
    resolver: zodResolver(gpsSettingsSchema),
    mode: 'onBlur',
  });

  // Sync query data to form — only when user hasn't made edits
  useEffect(() => {
    if (gpsConfig && !isDirty) {
      reset(gpsConfig);
    }
  }, [gpsConfig, isDirty, reset]);

  // ...
}
```

### Shared FormField Component

Standardizes error display and accessibility across all forms:

```tsx
// src/components/form/FormField.tsx
interface FormFieldProps {
  name: string;
  label?: string;
  error?: { message?: string };
  helperText?: string;
  children: React.ReactNode;
}

function FormField({ name, label, error, helperText, children }: FormFieldProps) {
  return (
    <div>
      {label && <label htmlFor={name}>{label}</label>}
      {React.cloneElement(children, {
        id: name,
        'aria-invalid': !!error,
        'aria-describedby': error ? `${name}-error` : helperText ? `${name}-help` : undefined,
      })}
      {error?.message && (
        <p id={`${name}-error`} role="alert" className="text-red-500 text-sm mt-1">
          {error.message}
        </p>
      )}
      {!error && helperText && (
        <p id={`${name}-help`} className="text-gray-500 text-sm mt-1">{helperText}</p>
      )}
    </div>
  );
}
```

## Testing Strategy

### Schema Tests (Pure Unit Tests)

No React rendering needed — test Zod schemas directly:

```typescript
// src/schemas/__tests__/species.test.ts
import { speciesSchema } from '../species';

describe('speciesSchema', () => {
  it('accepts valid data', () => {
    const result = speciesSchema.safeParse({
      species: 'Manduca sexta',
      confidence: 'certain',
    });
    expect(result.success).toBe(true);
  });

  it('rejects invalid confidence', () => {
    const result = speciesSchema.safeParse({ confidence: 'maybe' });
    expect(result.success).toBe(false);
  });
});
```

### Form Component Tests

Testing shifts from manual state manipulation to form interaction:

```tsx
// Before: manual state testing
fireEvent.change(nameInput, { target: { value: '' } });
expect(screen.getByText('Name is required')).toBeInTheDocument();

// After: form submission / blur testing
await user.clear(nameInput);
await user.tab(); // trigger onBlur validation
expect(screen.getByText('Name is required')).toBeInTheDocument();
```

### Test Utilities (Created in Phase 0)

```tsx
// src/test-utils/renderWithForm.tsx
function renderWithForm<T>(ui: ReactElement, formOptions?: UseFormProps<T>) {
  // Wraps component in FormProvider for testing nested form components
}
```

### Validation Mode

- Default: `mode: 'onBlur'` — validates when user leaves a field
- Scheduler sub-forms: `mode: 'onChange'` — validates on every keystroke (matches current UX)
- Coverage: each migration must maintain or improve existing test coverage

## Error Handling & Accessibility

### Error Message Sources (Priority Order)

1. Zod schema messages — defined via `.message()` or `.refine()`
2. react-hook-form defaults
3. Scheduler `errorMessages.js` trimmed to only non-validation messages (network/API errors)

### Async Errors

- Server-side validation (cron API): surfaced via `setError()` into `formState.errors`
- Mutation failures (GPS aggregation): field-related errors → `setError()`, non-field feedback → toast
- Toast remains for success messages and non-field operational feedback

### Accessibility (Automatic via FormField)

- `aria-invalid="true"` on fields with errors
- `aria-describedby` linking input to error/helper text
- `role="alert"` on error messages for screen reader announcement
- `shouldFocusError: true` (react-hook-form default) — focus moves to first invalid field on submit

## Known Incompatibilities & Mitigations

### GPSSettings: Polling Overwrites User Edits (HIGH)

**Problem**: GPS status polls every 15s. A `useEffect` syncs query data to local state, overwriting mid-edit keystrokes.

**Mitigation**: Use `isDirty` guard — `reset()` only when the user has no pending edits. This is actually an improvement over current behavior which silently overwrites.

**Explicit in issue**: The GPSSettings migration issue must include this state architecture change.

### FormatOptionsPanel: Conditional Schemas (MEDIUM)

**Problem**: Different fields render based on selected export format.

**Mitigation**: Zod discriminated union keyed on `format`. Use `watch('format')` to conditionally render fields. Well-supported by both Zod and react-hook-form.

### DeploymentEditor: Toast-Only Errors (MEDIUM)

**Problem**: Some errors (GPS aggregation) are shown only via toast, not inline.

**Mitigation**: Split errors — field validation → `formState.errors` (inline via FormField), async operation feedback → toast. Each error gets one display channel, not both.

### CronExpressionInput: Debounced Async Validation (MEDIUM)

**Problem**: Current `useCronValidation` hook debounces at 300ms and validates via API on every keystroke. react-hook-form's async validation runs on blur/submit.

**Mitigation**: Hybrid approach — keep `useCronValidation` for real-time preview/description display alongside the form. Zod schema handles format validation synchronously. Server validation runs on blur via async `refine`.

## Phasing

### Phase 0: Foundation (2 issues)

**Issue 0a: TypeScript Tooling Setup**
- Create `tsconfig.json` with strict mode
- Add `typescript`, `@typescript-eslint/parser`, `@typescript-eslint/eslint-plugin` as dev dependencies
- Update `eslint.config.js` to lint `.ts`/`.tsx` files
- Add `tsc --noEmit` npm script
- Add `@deprecated` JSDoc to `gpsValidation.js`, `presetValidation.js`, `gpsCoordinates.ts`
- Add ESLint `no-restricted-imports` rule warning on deprecated utility imports

**Issue 0b: Form Validation Foundation** (blocked by 0a)
- Install `react-hook-form`, `zod`, `@hookform/resolvers`
- Create `src/schemas/` directory with `preset.ts` as first schema
- Create shared `FormField.tsx`, `FormSelect.tsx`, `FormNumberInput.tsx`
- Create `useFormField.ts` hook
- Create `src/test-utils/renderWithForm.tsx`
- Schema and component tests

### Phase 1: Simple Forms (6 issues)

Each issue: create/reuse schema (.ts) + migrate component (.jsx → .tsx) + migrate test (.test.jsx → .test.tsx) + remove prop-types.

| # | Form | Schema | Fields |
|---|------|--------|--------|
| 1 | SaveFilterPresetModal | `preset.ts` | 1 (name) |
| 2 | SavePresetModal (filters) | reuses `preset.ts` | 1 (name) |
| 3 | BulkTagModal | `tag.ts` | 1 (tag) |
| 4 | BulkSpeciesModal | `species.ts` | 3 |
| 5 | FormatOptionsPanel | `export-options.ts` | 2-3 (conditional) |
| 6 | SavePresetModal (camera) | `camera-preset.ts` | 3 |

### Phase 2: Medium Forms (7 issues)

| # | Form | Schema | Notes |
|---|------|--------|-------|
| 7 | MetadataSpecies | reuses `species.ts` | Autocomplete + prop sync |
| 8 | CoordinateInput | `coordinates.ts` | Replaces gpsCoordinates.ts validation |
| 9 | IntervalTriggerForm | `scheduler/interval.ts` | Controlled pattern |
| 10 | SolarTriggerForm | `scheduler/solar.ts` | Controlled pattern |
| 11 | MoonPhaseTriggerForm | `scheduler/moon-phase.ts` | Controlled pattern |
| 12 | TimeWindowInput | `scheduler/time-window.ts` | Cross-field (start < end) |
| 13 | PreConditionForm | `scheduler/pre-condition.ts` | Sensor thresholds |

### Phase 3: Complex Forms (5 issues)

| # | Form | Schema | Notes |
|---|------|--------|-------|
| 14 | CronExpressionInput | `scheduler/cron.ts` | Async validation hybrid |
| 15 | AdvancedSearchBuilder | `search.ts` | Dynamic field array |
| 16 | GPSSettings | `gps-settings.ts` | State architecture change, replaces gpsValidation.js |
| 17 | DeploymentEditor | `deployment.ts` | Two field arrays, toast split, replaces prop sync |
| 18 | Scheduler (top-level) | composes sub-schemas | Blocked by #9-13 |

### Phase 4: Cleanup (4 issues)

| # | Task | Deletes | Blocked by |
|---|------|---------|------------|
| 19 | Remove `gpsValidation.js` | `src/utils/gpsValidation.js` + all imports | #16 (GPSSettings) |
| 20 | Remove `presetValidation.js` | `src/utils/presetValidation.js` + all imports | #6 (SavePresetModal camera) |
| 21 | Remove `gpsCoordinates.ts` | `src/utils/gpsCoordinates.ts` + all imports | #8 (CoordinateInput), #16 (GPSSettings) |
| 22 | Update docs & close #197 | Update CLAUDE.md, remove stale references | All above |

### Dependency Graph

```
Phase 0a (TS tooling)
  └── Phase 0b (form foundation)
        ├── Phase 1: #1-6 (independent, any order)
        │     └── #4 (species.ts) blocks #7 (MetadataSpecies)
        │     └── #6 blocks #20 (remove presetValidation.js)
        ├── Phase 2: #7-13 (independent except #7 blocked by #4)
        │     └── #8 blocks #21 (remove gpsCoordinates.ts)
        │     └── #9-13 block #18 (top-level Scheduler)
        ├── Phase 3: #14-18 (independent except #18 blocked by #9-13)
        │     └── #16 blocks #19, #21
        └── Phase 4: #19-22 (each blocked by specific consumers)
```

## Risk Mitigation

### React 19 Compatibility

react-hook-form v7.54+ supports React 19. Phase 0b pins `react-hook-form@^7.54` minimum. First migrated form (SaveFilterPresetModal) validates compatibility before touching 17 more.

### Schema/Utility Duplication During Transition

Between Phase 1 and Phase 4, both old utilities and new schemas coexist. Mitigations:
- New code never imports from old utilities — only from `src/schemas/`
- Old utilities marked `@deprecated` in Phase 0a
- ESLint `no-restricted-imports` warns on deprecated utility imports
- Phase 4 cleanup issues explicitly blocked by all consumers being migrated

### Scheduler Complexity

Scheduler has 6+ sub-form components that compose together. All sub-forms (#9-13) must migrate before top-level scheduler (#18). Each sub-schema is independently testable.

### Large Test Surface

100+ frontend test files exist. Only tests for the 18 migrated forms change. Each conversion is scoped to its own issue/PR. Phase 0b includes `renderWithForm` test utility.

### Controlled Form Parent Contract

Scheduler sub-forms currently fire `onChange` on every keystroke with the complete value object. The controlled pattern (Pattern 2) preserves this contract via `useWatch` + `useEffect`, so parent components don't need changes.

## Constraints (All PRs)

- No PR introduces a new `.js`/`.jsx` file — all new files are `.ts`/`.tsx`
- No PR leaves dead imports or unused validation code
- Every PR includes the form's test file migration — no form ships without tests
- Every PR is independently deployable — the app works with a mix of old and new forms
- prop-types removed from each migrated component (TypeScript interfaces replace them)

## Total Scope

- **~25 issues** across 5 phases (0-4)
- **~4,600 LOC** directly affected
- **3 new runtime dependencies**: react-hook-form, zod, @hookform/resolvers
- **3-4 new dev dependencies**: typescript, @typescript-eslint/parser, @typescript-eslint/eslint-plugin (+ possibly typescript-eslint)
- **18 forms** migrated from `.jsx` → `.tsx`
- **18 test files** migrated from `.test.jsx` → `.test.tsx`
- **3 utility files** deleted in cleanup

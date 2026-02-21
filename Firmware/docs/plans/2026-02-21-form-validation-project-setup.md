# Form Validation Project Setup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create the GitHub project, milestones, and ~25 issues for the form validation standardization effort (issue #197).

**Architecture:** GitHub Project (board view) with 5 milestones (Phase 0-4), ~25 issues with labels, descriptions, blocking relationships, and sub-issue hierarchy under #197.

**Tech Stack:** GitHub CLI (`gh`), GitHub Projects V2

---

### Task 1: Create GitHub Project

**Step 1: Create the project**

```bash
gh project create --owner zane-lazare --title "Form Validation Standardization" --format json
```

Note the project number from output for subsequent commands.

**Step 2: Verify project created**

```bash
gh project list --owner zane-lazare
```

Expected: Project "Form Validation Standardization" appears in list.

**Step 3: Commit checkpoint**

No files changed — project is on GitHub. Continue.

---

### Task 2: Create Milestones

Create 5 milestones corresponding to the phases.

**Step 1: Create all milestones**

```bash
gh api repos/{owner}/{repo}/milestones --method POST -f title="Form Validation: Phase 0 - Foundation" -f description="TypeScript tooling setup and form validation infrastructure (react-hook-form + Zod + shared components)."

gh api repos/{owner}/{repo}/milestones --method POST -f title="Form Validation: Phase 1 - Simple Forms" -f description="Migrate 6 simple modal/component forms to react-hook-form + Zod with TypeScript."

gh api repos/{owner}/{repo}/milestones --method POST -f title="Form Validation: Phase 2 - Medium Forms" -f description="Migrate 7 medium-complexity forms including scheduler sub-forms and autocomplete components."

gh api repos/{owner}/{repo}/milestones --method POST -f title="Form Validation: Phase 3 - Complex Forms" -f description="Migrate 5 complex forms with state architecture changes, dynamic field arrays, and async validation."

gh api repos/{owner}/{repo}/milestones --method POST -f title="Form Validation: Phase 4 - Cleanup" -f description="Remove deprecated validation utilities, update documentation, close parent issue #197."
```

**Step 2: Verify milestones**

```bash
gh api repos/{owner}/{repo}/milestones --jq '.[] | "\(.number): \(.title)"'
```

Expected: 5 milestones listed.

---

### Task 3: Create Phase 0 Issues (Foundation)

**Step 1: Create issue 0a — TypeScript Tooling Setup**

```bash
gh issue create \
  --title "Set up TypeScript tooling for frontend" \
  --label "foundation,frontend,type: refactor" \
  --milestone "Form Validation: Phase 0 - Foundation" \
  --body "$(cat <<'EOF'
## Summary

Set up TypeScript tooling infrastructure as prerequisite for the form validation migration. The frontend currently has passive TS support (Vite transpiles `.ts` files) but no active tooling (no `tsconfig.json`, ESLint ignores `.ts`/`.tsx` files).

**Parent issue:** #197
**Design doc:** `docs/plans/2026-02-21-form-validation-design.md`

## Acceptance Criteria

- [ ] `tsconfig.json` created with strict mode enabled
- [ ] `typescript` added as dev dependency (explicit, not just transitive)
- [ ] `@typescript-eslint/parser` and `@typescript-eslint/eslint-plugin` added as dev dependencies
- [ ] `eslint.config.js` updated to lint `.ts`/`.tsx` files
- [ ] `tsc --noEmit` npm script added (`npm run typecheck`)
- [ ] `@deprecated` JSDoc added to `src/utils/gpsValidation.js`, `src/utils/presetValidation.js`, `src/utils/gpsCoordinates.ts`
- [ ] ESLint `no-restricted-imports` rule warns on imports from deprecated utilities
- [ ] Existing `gpsCoordinates.ts` passes type checking
- [ ] All existing tests still pass
- [ ] CI pipeline updated if applicable

## Context

- Existing TS file: `src/utils/gpsCoordinates.ts` (374 LOC) — works via Vite transpilation but is ignored by ESLint
- TypeScript 5.9.3 already installed as transitive dependency
- `@types/react`, `@types/react-dom`, `@types/leaflet` already in devDependencies
- ESLint 9.36.0 (flat config format) — config at `eslint.config.js`

## Files to Create/Modify

- **Create:** `tsconfig.json`
- **Modify:** `eslint.config.js` (add TS file support)
- **Modify:** `package.json` (add deps + typecheck script)
- **Modify:** `src/utils/gpsValidation.js` (add @deprecated JSDoc)
- **Modify:** `src/utils/presetValidation.js` (add @deprecated JSDoc)
- **Modify:** `src/utils/gpsCoordinates.ts` (add @deprecated JSDoc)

## Blocks

This issue blocks all other Form Validation issues.
EOF
)"
```

**Step 2: Create issue 0b — Form Validation Foundation**

```bash
gh issue create \
  --title "Install form validation libraries and create shared infrastructure" \
  --label "foundation,frontend,form,validation,type: feature" \
  --milestone "Form Validation: Phase 0 - Foundation" \
  --body "$(cat <<'EOF'
## Summary

Install react-hook-form + Zod + @hookform/resolvers and create the shared form infrastructure (schemas, components, hooks, test utilities) that all form migrations will use.

**Parent issue:** #197
**Blocked by:** TypeScript tooling setup issue
**Design doc:** `docs/plans/2026-02-21-form-validation-design.md`

## Acceptance Criteria

- [ ] `react-hook-form@^7.54`, `zod`, `@hookform/resolvers` installed as dependencies
- [ ] `src/schemas/preset.ts` created as first schema (name validation for preset modals)
- [ ] `src/schemas/__tests__/preset.test.ts` with comprehensive schema unit tests
- [ ] `src/schemas/index.ts` created with re-exports
- [ ] `src/components/form/FormField.tsx` created — label + input + error + aria attributes
- [ ] `src/components/form/FormSelect.tsx` created — select with validation
- [ ] `src/components/form/FormNumberInput.tsx` created — number input with min/max
- [ ] `src/components/form/__tests__/FormField.test.tsx` with accessibility tests
- [ ] `src/hooks/useFormField.ts` created — shared controlled-field hook wrapping useController
- [ ] `src/test-utils/renderWithForm.tsx` created — FormProvider wrapper for testing
- [ ] All new files are `.ts`/`.tsx`
- [ ] All tests pass including new schema and component tests

## Technical Notes

### Three form patterns to support

1. **Modal (uncontrolled):** Form owns state, calls parent on submit via `handleSubmit`
2. **Controlled:** Parent owns state via props, form syncs back via `useWatch` + `useEffect`
3. **Hybrid:** Local form state synced with async data via `reset()` with `isDirty` guard

### FormField component spec

```tsx
interface FormFieldProps {
  name: string;
  label?: string;
  error?: { message?: string };
  helperText?: string;
  children: React.ReactNode;
}
```

Must provide: `aria-invalid`, `aria-describedby`, `role="alert"` on error messages, `id` generation.

## Files to Create

- `src/schemas/preset.ts`
- `src/schemas/index.ts`
- `src/schemas/__tests__/preset.test.ts`
- `src/components/form/FormField.tsx`
- `src/components/form/FormSelect.tsx`
- `src/components/form/FormNumberInput.tsx`
- `src/components/form/__tests__/FormField.test.tsx`
- `src/hooks/useFormField.ts`
- `src/test-utils/renderWithForm.tsx`

## Files to Modify

- `package.json` (add dependencies)
EOF
)"
```

**Step 3: Note both issue numbers for blocking relationships**

---

### Task 4: Create Phase 1 Issues (Simple Forms)

Create 6 issues for simple form migrations. Each follows the same template.

**Step 1: Create all 6 issues**

```bash
gh issue create \
  --title "Migrate SaveFilterPresetModal to react-hook-form + Zod" \
  --label "form,validation,frontend,type: refactor" \
  --milestone "Form Validation: Phase 1 - Simple Forms" \
  --body "$(cat <<'EOF'
## Summary

Migrate SaveFilterPresetModal from manual useState validation to react-hook-form + Zod. Convert from `.jsx` to `.tsx`.

**Parent issue:** #197
**Blocked by:** Form validation foundation issue
**Design doc:** `docs/plans/2026-02-21-form-validation-design.md`
**Pattern:** Modal (uncontrolled) — form owns state, calls parent `onSave` on submit

## Current State

- **File:** `src/components/filters/SaveFilterPresetModal.jsx` (191 LOC)
- **Fields:** 1 (name)
- **Validation:** useState + inline validation
- **Test:** `src/components/filters/__tests__/SavePresetModal.test.jsx`
- **Prop-types:** Yes

## Acceptance Criteria

- [ ] Schema: reuse `src/schemas/preset.ts` (created in foundation)
- [ ] Component: `SaveFilterPresetModal.jsx` → `SaveFilterPresetModal.tsx`
- [ ] Uses `useForm` with `zodResolver(presetSchema)`
- [ ] Uses shared `FormField` component for error display
- [ ] Validation mode: `onBlur`
- [ ] Test: `SavePresetModal.test.jsx` → `SavePresetModal.test.tsx`
- [ ] prop-types removed, TypeScript interfaces used instead
- [ ] No dead validation code remains
- [ ] All tests pass
- [ ] React 19 compatibility validated (this is the first migrated form)

## Notes

This is the simplest form and the first migration — it validates the entire pattern works with React 19 before we touch 17 more forms.
EOF
)"

gh issue create \
  --title "Migrate SavePresetModal (filters) to react-hook-form + Zod" \
  --label "form,validation,frontend,type: refactor" \
  --milestone "Form Validation: Phase 1 - Simple Forms" \
  --body "$(cat <<'EOF'
## Summary

Migrate the filters SavePresetModal from manual useState validation to react-hook-form + Zod. Convert from `.jsx` to `.tsx`.

**Parent issue:** #197
**Blocked by:** Form validation foundation issue
**Design doc:** `docs/plans/2026-02-21-form-validation-design.md`
**Pattern:** Modal (uncontrolled)

## Current State

- **File:** `src/components/filters/SavePresetModal.jsx`
- **Fields:** 1 (name)
- **Validation:** useState + inline
- **Test:** `src/components/filters/__tests__/SavePresetModal.test.jsx`
- **Prop-types:** Yes

## Acceptance Criteria

- [ ] Schema: reuse `src/schemas/preset.ts`
- [ ] Component: `.jsx` → `.tsx`
- [ ] Uses `useForm` with `zodResolver(presetSchema)`
- [ ] Uses shared `FormField` component
- [ ] Validation mode: `onBlur`
- [ ] Test: `.test.jsx` → `.test.tsx`
- [ ] prop-types removed
- [ ] No dead validation code
- [ ] All tests pass

## Notes

Demonstrates schema reuse — same `preset.ts` schema as SaveFilterPresetModal.
EOF
)"

gh issue create \
  --title "Migrate BulkTagModal to react-hook-form + Zod" \
  --label "form,validation,frontend,type: refactor" \
  --milestone "Form Validation: Phase 1 - Simple Forms" \
  --body "$(cat <<'EOF'
## Summary

Migrate BulkTagModal from manual useState validation to react-hook-form + Zod. Convert from `.jsx` to `.tsx`.

**Parent issue:** #197
**Blocked by:** Form validation foundation issue
**Design doc:** `docs/plans/2026-02-21-form-validation-design.md`
**Pattern:** Modal (uncontrolled)

## Current State

- **File:** `src/components/gallery/BulkTagModal.jsx` (225 LOC)
- **Fields:** 1 (tag) + mode selector
- **Validation:** useState + inline
- **Test:** `src/components/gallery/__tests__/BulkTagModal.test.jsx`
- **Prop-types:** Yes (complete with JSDoc)
- **Special:** Uses `useTags` hook for autocomplete suggestions

## Acceptance Criteria

- [ ] Schema: create `src/schemas/tag.ts`
- [ ] Schema tests: `src/schemas/__tests__/tag.test.ts`
- [ ] Component: `.jsx` → `.tsx`
- [ ] Uses `useForm` with `zodResolver(tagSchema)`
- [ ] Uses shared `FormField` component
- [ ] `useTags` autocomplete integration preserved (suggestions are read-only data, not form-controlled)
- [ ] Validation mode: `onBlur`
- [ ] Test: `.test.jsx` → `.test.tsx`
- [ ] prop-types removed
- [ ] All tests pass
EOF
)"

gh issue create \
  --title "Migrate BulkSpeciesModal to react-hook-form + Zod" \
  --label "form,validation,frontend,type: refactor" \
  --milestone "Form Validation: Phase 1 - Simple Forms" \
  --body "$(cat <<'EOF'
## Summary

Migrate BulkSpeciesModal from manual useState validation to react-hook-form + Zod. Convert from `.jsx` to `.tsx`.

**Parent issue:** #197
**Blocked by:** Form validation foundation issue
**Design doc:** `docs/plans/2026-02-21-form-validation-design.md`
**Pattern:** Modal (uncontrolled)

## Current State

- **File:** `src/components/gallery/BulkSpeciesModal.jsx` (225 LOC)
- **Fields:** 3 (species, commonName, confidence)
- **Validation:** useState + button disable logic
- **Test:** `src/components/gallery/__tests__/BulkSpeciesModal.test.jsx`
- **Prop-types:** Yes (complete with JSDoc)

## Acceptance Criteria

- [ ] Schema: create `src/schemas/species.ts` (reused by MetadataSpecies in Phase 2)
- [ ] Schema tests: `src/schemas/__tests__/species.test.ts`
- [ ] Component: `.jsx` → `.tsx`
- [ ] Uses `useForm` with `zodResolver(speciesSchema)`
- [ ] Uses shared `FormField` and `FormSelect` components
- [ ] Confidence dropdown uses enum validation
- [ ] Validation mode: `onBlur`
- [ ] Test: `.test.jsx` → `.test.tsx`
- [ ] prop-types removed
- [ ] All tests pass

## Notes

Creates `species.ts` schema which is reused by MetadataSpecies (Phase 2, issue #7).
EOF
)"

gh issue create \
  --title "Migrate FormatOptionsPanel to react-hook-form + Zod" \
  --label "form,validation,frontend,export,type: refactor" \
  --milestone "Form Validation: Phase 1 - Simple Forms" \
  --body "$(cat <<'EOF'
## Summary

Migrate FormatOptionsPanel from manual useState to react-hook-form + Zod. Convert from `.jsx` to `.tsx`.

**Parent issue:** #197
**Blocked by:** Form validation foundation issue
**Design doc:** `docs/plans/2026-02-21-form-validation-design.md`
**Pattern:** Controlled (parent-owned state) — parent passes format + options, onChange on every change

## Current State

- **File:** `src/components/export/FormatOptionsPanel.jsx`
- **Fields:** 2-3 (varies by format — conditional rendering)
- **Validation:** useState
- **Test:** `src/components/export/__tests__/FormatOptionsPanel.test.jsx`
- **Prop-types:** Yes (loose — `PropTypes.object`)

## Acceptance Criteria

- [ ] Schema: create `src/schemas/export-options.ts` with Zod discriminated union keyed on `format`
- [ ] Schema covers all 4 formats: darwin_core, inaturalist, json, csv
- [ ] Schema tests: `src/schemas/__tests__/export-options.test.ts`
- [ ] Component: `.jsx` → `.tsx`
- [ ] Uses `useForm` with `zodResolver`
- [ ] Uses `watch('format')` for conditional field rendering
- [ ] Validation mode: `onChange` (controlled pattern)
- [ ] Test: `.test.jsx` → `.test.tsx`
- [ ] prop-types removed
- [ ] All tests pass

## Known Complexity

**Conditional schemas:** Fields change based on selected export format. Zod discriminated union handles this:

```typescript
z.discriminatedUnion('format', [
  z.object({ format: z.literal('darwin_core'), validate: z.boolean().optional(), ... }),
  z.object({ format: z.literal('inaturalist'), include_xmp_sidecars: z.boolean().optional(), ... }),
  // ...
])
```
EOF
)"

gh issue create \
  --title "Migrate SavePresetModal (camera) to react-hook-form + Zod" \
  --label "form,validation,frontend,camera,type: refactor" \
  --milestone "Form Validation: Phase 1 - Simple Forms" \
  --body "$(cat <<'EOF'
## Summary

Migrate the camera SavePresetModal from manual useState + utility validation to react-hook-form + Zod. Convert from `.jsx` to `.tsx`.

**Parent issue:** #197
**Blocked by:** Form validation foundation issue
**Design doc:** `docs/plans/2026-02-21-form-validation-design.md`
**Pattern:** Modal (uncontrolled)

## Current State

- **File:** `src/components/SavePresetModal.jsx` (287 LOC)
- **Fields:** 3 (name, description, workflow)
- **Validation:** useState + `presetValidation.js` utility (31 validation rules)
- **Test:** `src/components/__tests__/SavePresetModal.test.jsx`
- **Prop-types:** No

## Acceptance Criteria

- [ ] Schema: create `src/schemas/camera-preset.ts` incorporating rules from `presetValidation.js`
- [ ] Schema tests: `src/schemas/__tests__/camera-preset.test.ts`
- [ ] Component: `.jsx` → `.tsx`
- [ ] Uses `useForm` with `zodResolver(cameraPresetSchema)`
- [ ] Uses shared `FormField` component
- [ ] Validation mode: `onBlur`
- [ ] Test: `.test.jsx` → `.test.tsx`
- [ ] TypeScript interfaces added (no existing prop-types to remove)
- [ ] All tests pass

## Notes

This is the last consumer of `presetValidation.js`. Once migrated, the cleanup issue can delete that utility.

**Important:** The 31 validation rules in `presetValidation.js` (boolean controls, integer enums, float ranges, etc.) must be accurately ported to the Zod schema. Cross-reference with `src/utils/presetValidation.js` during implementation.
EOF
)"
```

**Step 2: Verify all 6 issues created**

```bash
gh issue list --milestone "Form Validation: Phase 1 - Simple Forms" --json number,title --jq '.[] | "#\(.number): \(.title)"'
```

---

### Task 5: Create Phase 2 Issues (Medium Forms)

Create 7 issues for medium-complexity form migrations.

**Step 1: Create all 7 issues**

```bash
gh issue create \
  --title "Migrate MetadataSpecies to react-hook-form + Zod" \
  --label "form,validation,frontend,metadata,type: refactor" \
  --milestone "Form Validation: Phase 2 - Medium Forms" \
  --body "$(cat <<'EOF'
## Summary

Migrate MetadataSpecies from manual useState + useEffect validation to react-hook-form + Zod. Convert from `.jsx` to `.tsx`.

**Parent issue:** #197
**Blocked by:** BulkSpeciesModal issue (creates `species.ts` schema)
**Design doc:** `docs/plans/2026-02-21-form-validation-design.md`
**Pattern:** Hybrid (prop-synced) — local state synced with parent props via useEffect

## Current State

- **File:** `src/components/metadata/MetadataSpecies.jsx` (227 LOC)
- **Fields:** 4 (species, commonName, confidence, referenceUrl)
- **Validation:** useState + inline URL validation + `useSpecies` hook for autocomplete
- **Test:** `src/components/metadata/__tests__/MetadataSpecies.test.jsx`
- **Prop-types:** Yes (complete)
- **Special:** Two-way prop sync via useEffect (lines 28-34), autocomplete suggestions

## Acceptance Criteria

- [ ] Schema: reuse `src/schemas/species.ts` (created in BulkSpeciesModal issue)
- [ ] Component: `.jsx` → `.tsx`
- [ ] Uses `Controller` for species field (autocomplete integration)
- [ ] Uses `reset()` for prop sync (replaces useEffect prop → state sync)
- [ ] `useSpecies` autocomplete preserved alongside form
- [ ] Validation mode: `onBlur`
- [ ] Test: `.test.jsx` → `.test.tsx`
- [ ] prop-types removed
- [ ] All tests pass

## Notes

Demonstrates schema reuse — same `species.ts` as BulkSpeciesModal but different UI (inline editing vs modal).
EOF
)"

gh issue create \
  --title "Migrate CoordinateInput to react-hook-form + Zod" \
  --label "form,validation,frontend,gps,type: refactor" \
  --milestone "Form Validation: Phase 2 - Medium Forms" \
  --body "$(cat <<'EOF'
## Summary

Migrate CoordinateInput from manual useState validation to react-hook-form + Zod. Convert from `.jsx` to `.tsx`. Create `coordinates.ts` schema that replaces validation logic from `gpsCoordinates.ts`.

**Parent issue:** #197
**Blocked by:** Form validation foundation issue
**Design doc:** `docs/plans/2026-02-21-form-validation-design.md`
**Pattern:** Hybrid (prop-synced) — syncs latitude/longitude with parent props via useEffect

## Current State

- **File:** `src/components/export/CoordinateInput.jsx` (230 LOC)
- **Fields:** 2 (latitude, longitude)
- **Validation:** useState + inline + imports from `gpsCoordinates.ts`
- **Test:** `src/components/export/__tests__/CoordinateInput.test.jsx`
- **Prop-types:** Yes (complete)

## Acceptance Criteria

- [ ] Schema: create `src/schemas/coordinates.ts` with lat/lng range validation
- [ ] Schema tests: `src/schemas/__tests__/coordinates.test.ts`
- [ ] Component: `.jsx` → `.tsx`
- [ ] Uses `useForm` with `zodResolver(coordinatesSchema)`
- [ ] Latitude: -90 to 90, Longitude: -180 to 180
- [ ] Uses `reset()` for prop sync with `isDirty` guard
- [ ] Validation mode: `onBlur`
- [ ] Test: `.test.jsx` → `.test.tsx`
- [ ] prop-types removed
- [ ] All tests pass

## Notes

This is one of two consumers of `gpsCoordinates.ts` (the other is GPSSettings). The cleanup issue to delete `gpsCoordinates.ts` is blocked by both this and the GPSSettings migration.
EOF
)"

gh issue create \
  --title "Migrate IntervalTriggerForm to react-hook-form + Zod" \
  --label "form,validation,frontend,scheduler,type: refactor" \
  --milestone "Form Validation: Phase 2 - Medium Forms" \
  --body "$(cat <<'EOF'
## Summary

Migrate IntervalTriggerForm from manual useState to react-hook-form + Zod. Convert from `.jsx` to `.tsx`. This is the first scheduler sub-form migration and establishes the controlled pattern for the remaining scheduler forms.

**Parent issue:** #197
**Blocked by:** Form validation foundation issue
**Design doc:** `docs/plans/2026-02-21-form-validation-design.md`
**Pattern:** Controlled (parent-owned state) — parent passes `value` prop, form fires `onChange` on every field change

## Current State

- **File:** `src/components/scheduler/ScheduleEditor/IntervalTriggerForm.jsx`
- **Fields:** 3-4 (interval_minutes, time window, days)
- **Validation:** useState + inline
- **Prop-types:** Yes (complete with JSDoc)

## Acceptance Criteria

- [ ] Schema: create `src/schemas/scheduler/interval.ts`
- [ ] Schema tests: `src/schemas/scheduler/__tests__/interval.test.ts`
- [ ] Component: `.jsx` → `.tsx`
- [ ] Uses `useForm` with `zodResolver` + `useWatch` to sync changes back to parent via `onChange`
- [ ] Validation mode: `onChange` (matches current keystroke-by-keystroke behavior)
- [ ] Test: update or create `.test.tsx`
- [ ] prop-types removed
- [ ] Parent contract preserved (onChange called with complete value object)
- [ ] All tests pass

## Notes

**First scheduler sub-form.** This proves the controlled pattern (Pattern 2 from design doc) works with the scheduler's parent-owned state model. If this pattern works, the remaining 4 scheduler sub-forms follow the same template.
EOF
)"

gh issue create \
  --title "Migrate SolarTriggerForm to react-hook-form + Zod" \
  --label "form,validation,frontend,scheduler,type: refactor" \
  --milestone "Form Validation: Phase 2 - Medium Forms" \
  --body "$(cat <<'EOF'
## Summary

Migrate SolarTriggerForm to react-hook-form + Zod. Convert from `.jsx` to `.tsx`.

**Parent issue:** #197
**Blocked by:** Form validation foundation issue
**Design doc:** `docs/plans/2026-02-21-form-validation-design.md`
**Pattern:** Controlled (parent-owned state)

## Current State

- **File:** `src/components/scheduler/ScheduleEditor/SolarTriggerForm.jsx`
- **Fields:** 3-4 (solar_event, offset_minutes, days_of_week)
- **Validation:** useState + inline
- **Prop-types:** Yes (complete with JSDoc)

## Acceptance Criteria

- [ ] Schema: create `src/schemas/scheduler/solar.ts`
- [ ] Schema tests: `src/schemas/scheduler/__tests__/solar.test.ts`
- [ ] Component: `.jsx` → `.tsx`
- [ ] Controlled pattern: `useWatch` + `onChange` sync
- [ ] Validation mode: `onChange`
- [ ] Test: `.test.tsx`
- [ ] prop-types removed
- [ ] All tests pass

## Notes

Follows same controlled pattern as IntervalTriggerForm.
EOF
)"

gh issue create \
  --title "Migrate MoonPhaseTriggerForm to react-hook-form + Zod" \
  --label "form,validation,frontend,scheduler,type: refactor" \
  --milestone "Form Validation: Phase 2 - Medium Forms" \
  --body "$(cat <<'EOF'
## Summary

Migrate MoonPhaseTriggerForm to react-hook-form + Zod. Convert from `.jsx` to `.tsx`.

**Parent issue:** #197
**Blocked by:** Form validation foundation issue
**Design doc:** `docs/plans/2026-02-21-form-validation-design.md`
**Pattern:** Controlled (parent-owned state)

## Current State

- **File:** `src/components/scheduler/ScheduleEditor/MoonPhaseTriggerForm.jsx`
- **Fields:** 2-3 (moon_phase, tolerance)
- **Validation:** useState + inline
- **Prop-types:** Yes (complete with JSDoc)

## Acceptance Criteria

- [ ] Schema: create `src/schemas/scheduler/moon-phase.ts`
- [ ] Schema tests: `src/schemas/scheduler/__tests__/moon-phase.test.ts`
- [ ] Component: `.jsx` → `.tsx`
- [ ] Controlled pattern: `useWatch` + `onChange` sync
- [ ] Validation mode: `onChange`
- [ ] Test: `.test.tsx`
- [ ] prop-types removed
- [ ] All tests pass

## Notes

Follows same controlled pattern as IntervalTriggerForm.
EOF
)"

gh issue create \
  --title "Migrate TimeWindowInput to react-hook-form + Zod" \
  --label "form,validation,frontend,scheduler,type: refactor" \
  --milestone "Form Validation: Phase 2 - Medium Forms" \
  --body "$(cat <<'EOF'
## Summary

Migrate TimeWindowInput from manual useState + useEffect to react-hook-form + Zod. Convert from `.jsx` to `.tsx`.

**Parent issue:** #197
**Blocked by:** Form validation foundation issue
**Design doc:** `docs/plans/2026-02-21-form-validation-design.md`
**Pattern:** Controlled (parent-owned state)

## Current State

- **File:** `src/components/scheduler/ScheduleEditor/TimeWindowInput.jsx`
- **Fields:** 2 (start time, end time) + time type detection
- **Validation:** useState + useEffect for time type detection + cross-field validation (start < end)
- **Prop-types:** Yes (complete with JSDoc)
- **Special:** Mixed time window warning (fixed time + solar events)

## Acceptance Criteria

- [ ] Schema: create `src/schemas/scheduler/time-window.ts` with cross-field validation (start < end)
- [ ] Cross-field validation via Zod `.refine()`: start time must be before end time
- [ ] Schema tests: `src/schemas/scheduler/__tests__/time-window.test.ts`
- [ ] Component: `.jsx` → `.tsx`
- [ ] Controlled pattern: `useWatch` + `onChange` sync
- [ ] Mixed time warning preserved
- [ ] Validation mode: `onChange`
- [ ] Test: `.test.tsx`
- [ ] prop-types removed
- [ ] All tests pass

## Notes

First scheduler form with cross-field validation — validates the `.refine()` pattern for dependent fields.
EOF
)"

gh issue create \
  --title "Migrate PreConditionForm to react-hook-form + Zod" \
  --label "form,validation,frontend,scheduler,sensors,type: refactor" \
  --milestone "Form Validation: Phase 2 - Medium Forms" \
  --body "$(cat <<'EOF'
## Summary

Migrate PreConditionForm from manual useState + useEffect to react-hook-form + Zod. Convert from `.jsx` to `.tsx`.

**Parent issue:** #197
**Blocked by:** Form validation foundation issue
**Design doc:** `docs/plans/2026-02-21-form-validation-design.md`
**Pattern:** Controlled (parent-owned state) with prop sync for enabled state

## Current State

- **File:** `src/components/scheduler/ScheduleEditor/PreConditionForm.jsx`
- **Fields:** 3-4 (sensor type, threshold, operator, enabled)
- **Validation:** useState + inline with data-testid attributes
- **Prop-types:** Yes (complete with JSDoc)

## Acceptance Criteria

- [ ] Schema: create `src/schemas/scheduler/pre-condition.ts`
- [ ] Schema tests: `src/schemas/scheduler/__tests__/pre-condition.test.ts`
- [ ] Component: `.jsx` → `.tsx`
- [ ] Controlled pattern: `useWatch` + `onChange` sync
- [ ] Validation mode: `onChange`
- [ ] data-testid attributes preserved for test compatibility
- [ ] Test: `.test.tsx`
- [ ] prop-types removed
- [ ] All tests pass
EOF
)"
```

**Step 2: Verify all 7 issues created**

```bash
gh issue list --milestone "Form Validation: Phase 2 - Medium Forms" --json number,title --jq '.[] | "#\(.number): \(.title)"'
```

---

### Task 6: Create Phase 3 Issues (Complex Forms)

Create 5 issues for complex form migrations.

**Step 1: Create all 5 issues**

```bash
gh issue create \
  --title "Migrate CronExpressionInput to react-hook-form + Zod" \
  --label "form,validation,frontend,scheduler,type: refactor" \
  --milestone "Form Validation: Phase 3 - Complex Forms" \
  --body "$(cat <<'EOF'
## Summary

Migrate CronExpressionInput to react-hook-form + Zod. Convert from `.jsx` to `.tsx`. Migrate `useCronValidation.js` to `.ts`.

**Parent issue:** #197
**Blocked by:** Form validation foundation issue
**Design doc:** `docs/plans/2026-02-21-form-validation-design.md`
**Pattern:** Controlled (parent-owned state) with async server-side validation

## Current State

- **File:** `src/components/scheduler/ExpertMode/CronExpressionInput.jsx`
- **Fields:** 1 (cron expression)
- **Validation:** `useCronValidation` hook with 300ms debounce + API validation
- **Prop-types:** Yes (basic)
- **Special:** Real-time validation via API, success/error icons, next execution display

## Acceptance Criteria

- [ ] Schema: create `src/schemas/scheduler/cron.ts` with sync format validation
- [ ] Schema tests: `src/schemas/scheduler/__tests__/cron.test.ts`
- [ ] Migrate `src/hooks/useCronValidation.js` → `src/hooks/useCronValidation.ts`
- [ ] Component: `.jsx` → `.tsx`
- [ ] Hybrid validation: Zod for sync format checks, `useCronValidation` for async API validation
- [ ] Keep `useCronValidation` for real-time preview/description display
- [ ] Server validation on blur via async `refine` or `setError`
- [ ] Test: `.test.tsx`
- [ ] prop-types removed
- [ ] All tests pass

## Known Complexity

**Async validation conflict:** Current hook debounces at 300ms and validates on every keystroke. react-hook-form's async validation runs on blur/submit.

**Solution:** Hybrid approach:
- Zod schema handles sync format validation (basic pattern matching)
- `useCronValidation` hook retained alongside form for live preview and description
- Server-side validation result fed into form via `setError` on blur
EOF
)"

gh issue create \
  --title "Migrate AdvancedSearchBuilder to react-hook-form + Zod" \
  --label "form,validation,frontend,type: refactor" \
  --milestone "Form Validation: Phase 3 - Complex Forms" \
  --body "$(cat <<'EOF'
## Summary

Migrate AdvancedSearchBuilder from manual useState to react-hook-form + Zod. Convert from `.jsx` to `.tsx`.

**Parent issue:** #197
**Blocked by:** Form validation foundation issue
**Design doc:** `docs/plans/2026-02-21-form-validation-design.md`
**Pattern:** Modal (uncontrolled) with dynamic field array

## Current State

- **File:** `src/components/gallery/AdvancedSearchBuilder.jsx`
- **Fields:** 5+ (dynamic conditions array, boolean operator, date range)
- **Validation:** useState + inline
- **Test:** `src/components/gallery/__tests__/AdvancedSearchBuilder.test.jsx`
- **Prop-types:** Yes (complete with JSDoc)
- **Special:** Dynamic conditions list (add/remove), query preview generation

## Acceptance Criteria

- [ ] Schema: create `src/schemas/search.ts`
- [ ] Schema tests: `src/schemas/__tests__/search.test.ts`
- [ ] Component: `.jsx` → `.tsx`
- [ ] Uses `useFieldArray` for dynamic conditions list
- [ ] Uses `useForm` with `zodResolver(searchSchema)`
- [ ] Query preview generation preserved
- [ ] Validation mode: `onBlur`
- [ ] Test: `.test.jsx` → `.test.tsx`
- [ ] prop-types removed
- [ ] All tests pass

## Notes

Uses react-hook-form's `useFieldArray` for add/remove condition rows — replaces manual array state management.
EOF
)"

gh issue create \
  --title "Migrate GPSSettings to react-hook-form + Zod" \
  --label "form,validation,frontend,gps,type: refactor" \
  --milestone "Form Validation: Phase 3 - Complex Forms" \
  --body "$(cat <<'EOF'
## Summary

Migrate GPSSettings from manual useState + useEffect + utility validation to react-hook-form + Zod. Convert from `.jsx` to `.tsx`. Includes state architecture change to fix polling overwrite bug.

**Parent issue:** #197
**Blocked by:** Form validation foundation issue
**Design doc:** `docs/plans/2026-02-21-form-validation-design.md`
**Pattern:** Hybrid (prop-synced) with TanStack Query mutation

## Current State

- **File:** `src/components/GPSSettings.jsx` (753 LOC)
- **Fields:** 10+ (device, baudrate, timeouts, precision, source selection, etc.)
- **Validation:** useState + `gpsValidation.js` utility + inline
- **Test:** `src/components/__tests__/GPSSettings.test.jsx`
- **Prop-types:** No
- **Special:** TanStack Query polling (15s), mutation for saves, toast notifications, debounced status

## Acceptance Criteria

- [ ] Schema: create `src/schemas/gps-settings.ts` (replaces all rules from `gpsValidation.js`)
- [ ] Schema tests: `src/schemas/__tests__/gps-settings.test.ts`
- [ ] Port all validators: `validateDevicePath`, `validateBaudrate`, `validateTimeout`, `validateGpsConfig`
- [ ] Component: `.jsx` → `.tsx`
- [ ] Uses `useForm` with `zodResolver(gpsSettingsSchema)`
- [ ] `reset()` with `isDirty` guard for query sync (fixes polling overwrite bug)
- [ ] Field validation errors in `formState.errors` (inline), operational feedback via toast
- [ ] Validation mode: `onBlur`
- [ ] Test: `.test.jsx` → `.test.tsx`
- [ ] TypeScript interfaces added
- [ ] All tests pass

## Known Complexity

**Polling overwrite bug (HIGH):** GPS status polls every 15s. useEffect syncs query data → local state, silently overwriting mid-edit keystrokes.

**Fix:** Use `isDirty` guard — `reset(gpsConfig)` only when `!isDirty`. This is an improvement over current behavior.

**State architecture change:** Multiple useEffects (prop sync, debounced polling, source sync) replaced by:
- `useForm` manages field state
- `reset()` loads query data (only when clean)
- `handleSubmit` triggers mutation

## Blocks

This issue blocks:
- Remove `gpsValidation.js` (Phase 4)
- Remove `gpsCoordinates.ts` (Phase 4) — if GPSSettings imports from it
EOF
)"

gh issue create \
  --title "Migrate DeploymentEditor to react-hook-form + Zod" \
  --label "form,validation,frontend,export,type: refactor" \
  --milestone "Form Validation: Phase 3 - Complex Forms" \
  --body "$(cat <<'EOF'
## Summary

Migrate DeploymentEditor from manual useState + useEffect validation to react-hook-form + Zod. Convert from `.jsx` to `.tsx`.

**Parent issue:** #197
**Blocked by:** Form validation foundation issue
**Design doc:** `docs/plans/2026-02-21-form-validation-design.md`
**Pattern:** Hybrid (prop-synced) with dynamic field arrays

## Current State

- **File:** `src/components/export/DeploymentEditor.jsx` (742 LOC)
- **Fields:** 15+ (name, location, dates, coordinates, environmental fields, custom fields)
- **Validation:** useEffect-based + form-level validate() function + date range logic
- **Test:** `src/components/export/__tests__/DeploymentEditor.test.jsx`
- **Prop-types:** Yes (complete with JSDoc)
- **Special:** Two dynamic field arrays (environmental, custom), photo aggregation auto-fill, unsaved changes confirm dialog

## Acceptance Criteria

- [ ] Schema: create `src/schemas/deployment.ts`
- [ ] Cross-field validation: end date >= start date via `.refine()`
- [ ] Dynamic arrays: `z.array(z.object({ key, value }))` for environmental and custom fields
- [ ] Schema tests: `src/schemas/__tests__/deployment.test.ts`
- [ ] Component: `.jsx` → `.tsx`
- [ ] Uses `useForm` with `zodResolver(deploymentSchema)`
- [ ] Uses two `useFieldArray` instances (environmental, custom)
- [ ] `reset()` with `isDirty` guard for prop sync
- [ ] Field errors in `formState.errors` (inline), async aggregation feedback via toast
- [ ] Unsaved changes dialog uses `isDirty` from react-hook-form
- [ ] Validation mode: `onBlur`
- [ ] Test: `.test.jsx` → `.test.tsx`
- [ ] prop-types removed
- [ ] All tests pass

## Known Complexity

**Toast-only errors:** Some errors (GPS aggregation) currently shown only via toast. Migration splits: field validation → `formState.errors`, async operation feedback → toast.

**Two field arrays:** Environmental fields and custom fields each need a `useFieldArray` instance. Custom fields have a 50-item limit (enforce in schema).

**Auto-fill:** Photo aggregation mutation auto-fills coordinates and dates. Use `setValue()` to populate fields without triggering full reset.
EOF
)"

gh issue create \
  --title "Migrate Scheduler top-level to react-hook-form + Zod" \
  --label "form,validation,frontend,scheduler,type: refactor" \
  --milestone "Form Validation: Phase 3 - Complex Forms" \
  --body "$(cat <<'EOF'
## Summary

Migrate the top-level Scheduler form orchestration to compose sub-form schemas into a unified validation layer. Convert relevant files from `.jsx` to `.tsx`.

**Parent issue:** #197
**Blocked by:** All scheduler sub-form issues (IntervalTriggerForm, SolarTriggerForm, MoonPhaseTriggerForm, TimeWindowInput, PreConditionForm)
**Design doc:** `docs/plans/2026-02-21-form-validation-design.md`
**Pattern:** Composite — orchestrates multiple sub-form schemas

## Current State

- **File:** `src/pages/SchedulerUI.jsx` (161 LOC) + `src/components/scheduler/ScheduleEditor/` sub-components
- **Fields:** 20+ (composed from sub-forms)
- **Validation:** Distributed across sub-components
- **Special:** Schedule/routine lifecycle, conflict detection, activation flow

## Acceptance Criteria

- [ ] Top-level schedule schema composes sub-schemas: `interval.ts`, `solar.ts`, `moon-phase.ts`, `time-window.ts`, `cron.ts`, `pre-condition.ts`
- [ ] `FormProvider` wraps scheduler so sub-forms can use `useFormContext`
- [ ] Cross-routine validation (conflicts) preserved
- [ ] SchedulerUI: `.jsx` → `.tsx`
- [ ] Relevant scheduler sub-components: `.jsx` → `.tsx`
- [ ] Tests updated
- [ ] All tests pass

## Notes

This is the capstone scheduler issue. All 5 sub-form migrations must be complete first — each sub-schema is independently tested before composition.

**Requires brainstorming:** The composition strategy (FormProvider vs independent useForm per sub-form) needs investigation during implementation planning.
EOF
)"
```

**Step 2: Verify all 5 issues created**

```bash
gh issue list --milestone "Form Validation: Phase 3 - Complex Forms" --json number,title --jq '.[] | "#\(.number): \(.title)"'
```

---

### Task 7: Create Phase 4 Issues (Cleanup)

Create 4 cleanup issues.

**Step 1: Create all 4 issues**

```bash
gh issue create \
  --title "Remove deprecated gpsValidation.js" \
  --label "validation,utilities,frontend,type: refactor" \
  --milestone "Form Validation: Phase 4 - Cleanup" \
  --body "$(cat <<'EOF'
## Summary

Delete `src/utils/gpsValidation.js` and remove all imports. All validation rules have been migrated to `src/schemas/gps-settings.ts`.

**Parent issue:** #197
**Blocked by:** GPSSettings migration issue
**Design doc:** `docs/plans/2026-02-21-form-validation-design.md`

## Acceptance Criteria

- [ ] `src/utils/gpsValidation.js` deleted
- [ ] All imports of `gpsValidation` removed from codebase
- [ ] ESLint `no-restricted-imports` rule for this file removed (no longer needed)
- [ ] No remaining references in any file
- [ ] All tests pass
EOF
)"

gh issue create \
  --title "Remove deprecated presetValidation.js" \
  --label "validation,utilities,frontend,type: refactor" \
  --milestone "Form Validation: Phase 4 - Cleanup" \
  --body "$(cat <<'EOF'
## Summary

Delete `src/utils/presetValidation.js` and remove all imports. All 31 validation rules have been migrated to `src/schemas/camera-preset.ts`.

**Parent issue:** #197
**Blocked by:** SavePresetModal (camera) migration issue
**Design doc:** `docs/plans/2026-02-21-form-validation-design.md`

## Acceptance Criteria

- [ ] `src/utils/presetValidation.js` deleted
- [ ] All imports of `presetValidation` removed from codebase
- [ ] ESLint `no-restricted-imports` rule for this file removed
- [ ] No remaining references in any file
- [ ] All tests pass
EOF
)"

gh issue create \
  --title "Remove deprecated gpsCoordinates.ts" \
  --label "validation,utilities,frontend,gps,type: refactor" \
  --milestone "Form Validation: Phase 4 - Cleanup" \
  --body "$(cat <<'EOF'
## Summary

Delete `src/utils/gpsCoordinates.ts` and its test file. Validation and conversion logic migrated to `src/schemas/coordinates.ts`.

**Parent issue:** #197
**Blocked by:** CoordinateInput migration AND GPSSettings migration
**Design doc:** `docs/plans/2026-02-21-form-validation-design.md`

## Acceptance Criteria

- [ ] `src/utils/gpsCoordinates.ts` deleted
- [ ] `src/utils/__tests__/gpsCoordinates.test.ts` deleted
- [ ] All imports of `gpsCoordinates` removed from codebase
- [ ] ESLint `no-restricted-imports` rule for this file removed
- [ ] Coordinate conversion functions preserved in `src/schemas/coordinates.ts` (not just validation — also `decimalToDMS`, `formatCoordinateDisplay`, etc.)
- [ ] No remaining references in any file
- [ ] All tests pass

## Notes

`gpsCoordinates.ts` contains both validation AND conversion utilities (374 LOC). Ensure all non-validation exports (coordinate formatting, DMS conversion) are either migrated to `schemas/coordinates.ts` or a separate `utils/coordinates.ts` if they don't belong in a schema file.
EOF
)"

gh issue create \
  --title "Update documentation and close parent issue #197" \
  --label "documentation,frontend,type: docs" \
  --milestone "Form Validation: Phase 4 - Cleanup" \
  --body "$(cat <<'EOF'
## Summary

Final cleanup: update CLAUDE.md with new form validation patterns, remove stale references, verify all migrations complete, close parent issue #197.

**Parent issue:** #197
**Blocked by:** All other Form Validation issues
**Design doc:** `docs/plans/2026-02-21-form-validation-design.md`

## Acceptance Criteria

- [ ] `CLAUDE.md` updated: add Form Validation System section documenting schemas, patterns, shared components
- [ ] `CLAUDE.md` updated: remove references to old validation utilities
- [ ] Remove ESLint `no-restricted-imports` rules for deleted utilities (all gone now)
- [ ] Verify no `.jsx` form files remain for migrated components
- [ ] Verify no `.test.jsx` test files remain for migrated components
- [ ] Verify `src/schemas/index.ts` re-exports all schemas
- [ ] Design doc status updated to "Complete"
- [ ] Close parent issue #197

## CLAUDE.md Section to Add

```markdown
### Form Validation System (Issue #197)

**Purpose**: Standardized form validation using react-hook-form + Zod with TypeScript.

**Key Components**:
- `src/schemas/`: Zod validation schemas (single source of truth for validation + types)
- `src/components/form/`: Shared form primitives (FormField, FormSelect, FormNumberInput)
- `src/hooks/useFormField.ts`: Shared controlled-field hook

**Patterns**: Modal (uncontrolled), Controlled (scheduler), Hybrid (prop-synced).
See `docs/plans/2026-02-21-form-validation-design.md` for full architecture.
```
EOF
)"
```

**Step 2: Verify all 4 issues created**

```bash
gh issue list --milestone "Form Validation: Phase 4 - Cleanup" --json number,title --jq '.[] | "#\(.number): \(.title)"'
```

---

### Task 8: Set Up Blocking Relationships and Sub-Issues

After all issues are created, set up the dependency graph using GitHub sub-issues (parent/child).

**Step 1: Make all issues sub-issues of #197**

For each created issue number, run:

```bash
# Get all issue numbers from the milestones
ISSUES=$(gh issue list --milestone "Form Validation: Phase 0 - Foundation" --milestone "Form Validation: Phase 1 - Simple Forms" --milestone "Form Validation: Phase 2 - Medium Forms" --milestone "Form Validation: Phase 3 - Complex Forms" --milestone "Form Validation: Phase 4 - Cleanup" --json number --jq '.[].number' | sort -n)

# For each issue, add as sub-issue of #197
for num in $ISSUES; do
  gh issue edit $num --add-parent 197
done
```

Note: If `--add-parent` is not supported by your `gh` version, use the API:

```bash
for num in $ISSUES; do
  gh api graphql -f query='
    mutation {
      addSubIssue(input: {
        issueId: "<ISSUE_NODE_ID>",
        parentIssueId: "<197_NODE_ID>"
      }) { issue { number } }
    }'
done
```

**Step 2: Set up specific blocking relationships in issue bodies**

The blocking relationships are documented in each issue body's "Blocked by" field. GitHub doesn't have native blocking — these serve as documentation for the project board.

**Step 3: Add status labels for blocked items**

```bash
# Phase 0b is blocked by 0a
gh issue edit <0b_number> --add-label "status: blocked"

# Phase 2 #7 (MetadataSpecies) blocked by Phase 1 #4 (BulkSpeciesModal)
gh issue edit <7_number> --add-label "status: blocked"

# Phase 3 #18 (Scheduler top-level) blocked by Phase 2 #9-13
gh issue edit <18_number> --add-label "status: blocked"

# All Phase 4 issues blocked
gh issue list --milestone "Form Validation: Phase 4 - Cleanup" --json number --jq '.[].number' | while read num; do
  gh issue edit $num --add-label "status: blocked"
done
```

---

### Task 9: Add Issues to GitHub Project

**Step 1: Get project ID**

```bash
PROJECT_NUM=<number from Task 1>
```

**Step 2: Add all issues to the project**

```bash
REPO="zane-lazare/Mothbox"
for num in $(gh issue list -R $REPO --milestone "Form Validation: Phase 0 - Foundation" --json number --jq '.[].number'; \
             gh issue list -R $REPO --milestone "Form Validation: Phase 1 - Simple Forms" --json number --jq '.[].number'; \
             gh issue list -R $REPO --milestone "Form Validation: Phase 2 - Medium Forms" --json number --jq '.[].number'; \
             gh issue list -R $REPO --milestone "Form Validation: Phase 3 - Complex Forms" --json number --jq '.[].number'; \
             gh issue list -R $REPO --milestone "Form Validation: Phase 4 - Cleanup" --json number --jq '.[].number'); do
  gh project item-add $PROJECT_NUM --owner zane-lazare --url "https://github.com/$REPO/issues/$num"
done
```

**Step 3: Add parent issue #197 to the project**

```bash
gh project item-add $PROJECT_NUM --owner zane-lazare --url "https://github.com/$REPO/issues/197"
```

**Step 4: Verify project board**

```bash
gh project item-list $PROJECT_NUM --owner zane-lazare --format json --jq '.items[] | "#\(.content.number): \(.content.title)"' | head -30
```

---

### Task 10: Final Verification

**Step 1: Verify issue counts per milestone**

```bash
echo "=== Phase 0 ===" && gh issue list --milestone "Form Validation: Phase 0 - Foundation" --json number,title --jq '.[] | "#\(.number): \(.title)"'
echo "=== Phase 1 ===" && gh issue list --milestone "Form Validation: Phase 1 - Simple Forms" --json number,title --jq '.[] | "#\(.number): \(.title)"'
echo "=== Phase 2 ===" && gh issue list --milestone "Form Validation: Phase 2 - Medium Forms" --json number,title --jq '.[] | "#\(.number): \(.title)"'
echo "=== Phase 3 ===" && gh issue list --milestone "Form Validation: Phase 3 - Complex Forms" --json number,title --jq '.[] | "#\(.number): \(.title)"'
echo "=== Phase 4 ===" && gh issue list --milestone "Form Validation: Phase 4 - Cleanup" --json number,title --jq '.[] | "#\(.number): \(.title)"'
```

Expected counts: Phase 0: 2, Phase 1: 6, Phase 2: 7, Phase 3: 5, Phase 4: 4 = **24 total**

**Step 2: Verify all are sub-issues of #197**

```bash
gh issue view 197 --json body
```

**Step 3: Verify project board has all items**

```bash
gh project item-list $PROJECT_NUM --owner zane-lazare --format json --jq '.totalCount'
```

Expected: 25 (24 issues + parent #197)

---

## Summary

| Phase | Milestone | Issues | Purpose |
|-------|-----------|--------|---------|
| 0 | Foundation | 2 | TS tooling + form validation infra |
| 1 | Simple Forms | 6 | 1-3 field modal migrations |
| 2 | Medium Forms | 7 | Scheduler sub-forms + autocomplete |
| 3 | Complex Forms | 5 | State architecture changes + composition |
| 4 | Cleanup | 4 | Delete deprecated code + update docs |
| **Total** | | **24** | |

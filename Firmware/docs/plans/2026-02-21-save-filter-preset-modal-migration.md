# SaveFilterPresetModal Migration Design

**Issue**: #438
**Date**: 2026-02-21
**Status**: Approved
**Parent**: #197 (Form Validation Standardization)
**Blocked by**: #437 (Form Validation Foundation) — completed

## Summary

Migrate `SaveFilterPresetModal` from manual `useState` validation to `react-hook-form` + Zod. Convert `.jsx` to `.tsx`. Write new tests (no existing test file for this component).

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Validation mode | `onBlur` | Design doc default; cleaner UX for single-field modal |
| Reset strategy | Remount on open | Early return `if (!isOpen) return null` gives fresh `useForm` each open |
| Test source | Write from scratch | Existing `SavePresetModal.test.jsx` tests a different component |
| Form pattern | Modal (Uncontrolled) | Form owns state, calls parent `onSave` on submit |

## Issue Correction

The issue references `SavePresetModal.test.jsx` as the test file, but that file imports and tests `SavePresetModal.jsx` — a **different component** with different props (`defaultName`), features (close button, character counter, portal rendering), and validation rules. `SaveFilterPresetModal.jsx` has no existing tests. New tests are written from scratch.

## Component Structure

The migrated `SaveFilterPresetModal.tsx`:

- Early return `if (!isOpen) return null` stays — provides free remount-on-open behavior
- `useForm<FilterPresetNameData>` with `zodResolver(filterPresetNameSchema)`, mode `onBlur`
- `register('name')` spread on the input (plain text input, no Controller needed)
- `handleSubmit` wraps save callback, calling `onSave(data.name)` — Zod `.trim()` handles whitespace
- `FormField` wraps input for label, error display, and aria attributes
- Save button disabled when `!isValid || !isDirty`
- Keyboard: Enter triggers `handleSubmit`, Escape calls `onClose`

Props interface unchanged: `{ isOpen, onClose, onSave, isSaving? }`. Consumer (`FilterPresetManager`) needs zero changes.

## What Changes vs What Stays

### Removed

- `useState` for `presetName` and `nameError`
- `validateName()` function
- `handleNameChange()` handler
- `PropTypes` import and block
- Manual error `<p>` rendering (replaced by FormField)

### Kept

- Modal shell (backdrop, dialog, header, info box, action buttons layout)
- All Tailwind classes and dark mode styling
- `Z_INDEX.MODAL` import
- Keyboard handling (Enter to submit, Escape to close)
- `isSaving` prop for disabled state during save
- `onSave` receives a trimmed string

### Changed

- `.jsx` → `.tsx`
- Props: TypeScript interface instead of PropTypes
- Input: `register('name')` + FormField instead of manual onChange/value
- Save disabled: `!isValid || !isDirty` instead of `!!nameError || !presetName.trim()`
- Error display: FormField's `role="alert"` + `aria-describedby` pattern
- Label: rendered by FormField (keep `*` required indicator via helperText or inline)

## Test Plan

New file: `__tests__/SaveFilterPresetModal.test.tsx` (~20 tests)

| Group | Tests | What's covered |
|---|---|---|
| Rendering | 3 | Open/closed states, input/buttons present |
| Validation | 5 | Empty on blur, too short, too long, valid clears error, error clears after fix |
| Save flow | 3 | Calls onSave with trimmed name, blocks invalid save, resets on reopen |
| Cancel/close | 2 | Cancel calls onClose, form resets on reopen |
| Keyboard | 2 | Enter submits, Escape closes |
| Disabled states | 3 | Empty, errors, isSaving |
| Accessibility | 2 | Dialog aria attrs, input aria-invalid/describedby on error |

Uses `@testing-library/react` + `userEvent` (not `fireEvent`) for proper blur/tab simulation.

## File Changes

| File | Action |
|---|---|
| `src/components/filters/SaveFilterPresetModal.jsx` | Delete |
| `src/components/filters/SaveFilterPresetModal.tsx` | Create |
| `src/components/filters/__tests__/SaveFilterPresetModal.test.tsx` | Create |
| `src/components/filters/FilterPresetManager.jsx` | No changes |
| `src/schemas/preset.ts` | No changes |

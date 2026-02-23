# Migrate SavePresetModal (camera) to react-hook-form + Zod

**Issue:** #443
**Parent:** #197 (Form Validation Standardization)
**Date:** 2026-02-23
**Pattern:** Modal (uncontrolled)

## Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Settings validation | Standalone runtime function | Settings are read-only context, not form fields |
| presetValidation.js | Port to TypeScript | Last consumer; typed validation catches bugs during migration |
| Schema location | New `camera-preset.ts` | Keeps camera-specific schema separate from filter preset schema |
| Validation mode | `onBlur` | Consistent with all other migrated forms |

## Architecture

Two distinct validation layers:

1. **Form fields** (name, description, workflow) — Zod schema + react-hook-form zodResolver
2. **Camera settings** (26 liveview rules) — standalone TypeScript validator called at submit time

Settings are read-only context passed as a `currentSettings` prop. They are not fields the user edits in this modal. The Zod schema covers only user-editable fields.

## Files

| File | Action |
|------|--------|
| `src/schemas/camera-preset.ts` | New — Zod schema for name + description + workflow |
| `src/schemas/__tests__/camera-preset.test.ts` | New — schema unit tests |
| `src/schemas/index.ts` | Edit — re-export new schema and type |
| `src/utils/presetValidation.js` → `.ts` | Rename + add types, keep logic |
| `src/components/SavePresetModal.jsx` → `.tsx` | Rewrite with useForm + zodResolver + FormField |
| `src/components/__tests__/SavePresetModal.test.jsx` → `.tsx` | Rewrite with TypeScript + userEvent + a11y |

## Schema (`camera-preset.ts`)

```typescript
import { z } from 'zod'

export const WORKFLOW_VALUES = ['photo', 'liveview', 'both'] as const

export const cameraPresetFormSchema = z.object({
  name: z.string()
    .trim()
    .min(1, 'Preset name is required')
    .min(3, 'Name must be at least 3 characters')
    .regex(/^[a-zA-Z0-9_]+$/, 'Name can only contain letters, numbers, and underscores')
    .max(50, 'Name must be 50 characters or less'),
  description: z.string().max(200, 'Description must be 200 characters or less').default(''),
  workflow: z.enum(WORKFLOW_VALUES).default('both'),
})

export type CameraPresetFormData = z.infer<typeof cameraPresetFormSchema>
```

Same name rules as `cameraPresetNameSchema` in `preset.ts`, composed into a full form schema with description and workflow.

## Component (`SavePresetModal.tsx`)

### Props

```typescript
interface SavePresetModalProps {
  isOpen: boolean
  onClose: () => void
  onSave: (data: {
    name: string
    description: string
    workflow: string
    from_current: boolean
  }) => Promise<void>
  isSaving?: boolean
  defaultWorkflow?: 'photo' | 'liveview' | 'both'
  currentSettings?: Record<string, unknown>
}
```

### Form setup

`useForm<CameraPresetFormData>` with `zodResolver(cameraPresetFormSchema)`, `mode: 'onBlur'`.

### Submit flow

1. react-hook-form validates name/description/workflow via Zod
2. If workflow !== 'photo', call `validatePresetSettings(currentSettings)`
3. If settings errors exist, set local state and block save
4. Otherwise call `onSave({ ...data, from_current: true })`

### Preserved behaviors

- Form reset on open via `useEffect` + `reset()`
- Enter submits, Escape closes
- Description character counter with `aria-describedby`
- Settings errors displayed as key=value list (first 5, "+N more")
- Save button disabled when `isSaving || !isValid || !name`

## presetValidation.ts

Rename from `.js` to `.ts`. Add:

- `ValidationError` interface: `{ key: string; value: unknown; message: string }`
- Typed validator factory functions (`createBooleanValidator`, `createRangeValidator`, etc.)
- Export types for consumer use

No logic changes — the 26 validation rules stay exactly as they are.

## Test Coverage

### Schema tests (`camera-preset.test.ts`)

- Valid names, empty/short/long names, invalid characters
- Description max length, default empty
- Workflow enum values, default 'both'
- Trim behavior on name

### Component tests (`SavePresetModal.test.tsx`)

- **Rendering**: open/closed states
- **Name validation**: blur-triggered errors, error clearing on valid input
- **Description**: character counter, max length
- **Workflow selection**: radio/select interaction
- **Settings validation**: only when workflow includes liveview, skipped for photo-only
- **Settings error display**: key=value format, truncation at 5, "+N more" message
- **Save flow**: correct payload shape, form reset on success
- **Cancel/close**: backdrop click, Escape key, disabled during save
- **Disabled states**: isSaving prop disables all inputs and buttons
- **Accessibility**: aria-invalid, aria-describedby, role="alert", aria-required

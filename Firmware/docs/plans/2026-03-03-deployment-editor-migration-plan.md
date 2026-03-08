# DeploymentEditor Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate DeploymentEditor from JSX with manual useState validation to TypeScript with react-hook-form + Zod.

**Architecture:** Hybrid (prop-synced) pattern — `useForm` with `zodResolver`, mode `onBlur`. Two `useFieldArray` instances for environmental and custom dynamic arrays. CoordinateInput stays as self-contained sub-form synced via props/onChange. Photo aggregation auto-fill uses `setValue()` per field.

**Tech Stack:** TypeScript, react-hook-form, Zod, @hookform/resolvers, Vitest, @testing-library/react

**Design doc:** `docs/plans/2026-03-03-deployment-editor-migration-design.md`

**Base branch:** `dev`

---

### Task 1: Create Zod Schema and Defaults

**Files:**
- Create: `webui/frontend/src/schemas/deployment.ts`

**Step 1: Create the schema file**

```typescript
import { z } from 'zod'

/** A key-value pair for useFieldArray (environmental or custom fields). */
export const deploymentFieldEntrySchema = z.object({
  key: z.string(),
  value: z.string(),
})

export const deploymentSchema = z.object({
  deployment_name: z.string()
    .min(1, 'Deployment name is required')
    .max(200, 'Must be 200 characters or less'),
  location_name: z.string().max(500, 'Must be 500 characters or less').optional().or(z.literal('')),
  latitude: z.number().min(-90, 'Must be between -90 and 90').max(90, 'Must be between -90 and 90').nullable(),
  longitude: z.number().min(-180, 'Must be between -180 and 180').max(180, 'Must be between -180 and 180').nullable(),
  altitude: z.coerce.number().nullable(),
  start_date: z.string().optional().or(z.literal('')),
  end_date: z.string().optional().or(z.literal('')),
  environmental: z.array(deploymentFieldEntrySchema),
  custom: z.array(deploymentFieldEntrySchema).max(50, 'Maximum 50 custom fields'),
  mothbox_id: z.string().optional().or(z.literal('')),
  firmware_version: z.string().optional().or(z.literal('')),
}).refine(
  (d) => {
    if (!d.start_date || !d.end_date) return true
    return d.start_date <= d.end_date
  },
  { message: 'End date must be on or after start date', path: ['end_date'] }
)

export type DeploymentFormData = z.infer<typeof deploymentSchema>

export const DEPLOYMENT_DEFAULTS: DeploymentFormData = {
  deployment_name: '',
  location_name: '',
  latitude: null,
  longitude: null,
  altitude: null,
  start_date: '',
  end_date: '',
  environmental: [],
  custom: [],
  mothbox_id: '',
  firmware_version: '',
}
```

**Step 2: Commit**

```bash
git add webui/frontend/src/schemas/deployment.ts
git commit -m "feat(#454): add Zod schema for deployment editor"
```

---

### Task 2: Add Schema Tests

**Files:**
- Create: `webui/frontend/src/schemas/__tests__/deployment.test.ts`

**Step 1: Write schema tests**

Cover: required fields, max lengths, coordinate ranges, date cross-validation, array limits, coercion, defaults round-trip.

```typescript
import { describe, it, expect } from 'vitest'
import {
  deploymentSchema,
  deploymentFieldEntrySchema,
  DEPLOYMENT_DEFAULTS,
  type DeploymentFormData,
} from '../deployment'

/** Helper: create valid deployment, overriding specific fields. */
function validDeployment(overrides: Partial<DeploymentFormData> = {}): DeploymentFormData {
  return { ...DEPLOYMENT_DEFAULTS, deployment_name: 'Test Deployment', ...overrides }
}

describe('deploymentSchema', () => {
  // --- deployment_name ---
  describe('deployment_name', () => {
    it('accepts valid name', () => {
      expect(deploymentSchema.safeParse(validDeployment()).success).toBe(true)
    })

    it('rejects empty name', () => {
      const result = deploymentSchema.safeParse(validDeployment({ deployment_name: '' }))
      expect(result.success).toBe(false)
    })

    it('rejects name over 200 chars', () => {
      const result = deploymentSchema.safeParse(validDeployment({ deployment_name: 'a'.repeat(201) }))
      expect(result.success).toBe(false)
    })

    it('accepts exactly 200 chars', () => {
      expect(deploymentSchema.safeParse(validDeployment({ deployment_name: 'a'.repeat(200) })).success).toBe(true)
    })
  })

  // --- location_name ---
  describe('location_name', () => {
    it('accepts empty string', () => {
      expect(deploymentSchema.safeParse(validDeployment({ location_name: '' })).success).toBe(true)
    })

    it('rejects over 500 chars', () => {
      const result = deploymentSchema.safeParse(validDeployment({ location_name: 'a'.repeat(501) }))
      expect(result.success).toBe(false)
    })

    it('accepts exactly 500 chars', () => {
      expect(deploymentSchema.safeParse(validDeployment({ location_name: 'a'.repeat(500) })).success).toBe(true)
    })
  })

  // --- coordinates ---
  describe('coordinates', () => {
    it('accepts null latitude and longitude', () => {
      expect(deploymentSchema.safeParse(validDeployment({ latitude: null, longitude: null })).success).toBe(true)
    })

    it('accepts valid coordinates', () => {
      expect(deploymentSchema.safeParse(validDeployment({ latitude: 35.96, longitude: -83.92 })).success).toBe(true)
    })

    it('rejects latitude below -90', () => {
      expect(deploymentSchema.safeParse(validDeployment({ latitude: -91 })).success).toBe(false)
    })

    it('rejects latitude above 90', () => {
      expect(deploymentSchema.safeParse(validDeployment({ latitude: 91 })).success).toBe(false)
    })

    it('rejects longitude below -180', () => {
      expect(deploymentSchema.safeParse(validDeployment({ longitude: -181 })).success).toBe(false)
    })

    it('rejects longitude above 180', () => {
      expect(deploymentSchema.safeParse(validDeployment({ longitude: 181 })).success).toBe(false)
    })

    it('accepts boundary values (-90, 90, -180, 180)', () => {
      expect(deploymentSchema.safeParse(validDeployment({ latitude: -90, longitude: -180 })).success).toBe(true)
      expect(deploymentSchema.safeParse(validDeployment({ latitude: 90, longitude: 180 })).success).toBe(true)
    })
  })

  // --- altitude ---
  describe('altitude', () => {
    it('accepts null altitude', () => {
      expect(deploymentSchema.safeParse(validDeployment({ altitude: null })).success).toBe(true)
    })

    it('accepts numeric altitude', () => {
      expect(deploymentSchema.safeParse(validDeployment({ altitude: 350.5 })).success).toBe(true)
    })

    it('accepts negative altitude (below sea level)', () => {
      expect(deploymentSchema.safeParse(validDeployment({ altitude: -42 })).success).toBe(true)
    })
  })

  // --- date cross-validation ---
  describe('date range', () => {
    it('accepts both dates empty', () => {
      expect(deploymentSchema.safeParse(validDeployment({ start_date: '', end_date: '' })).success).toBe(true)
    })

    it('accepts start_date only', () => {
      expect(deploymentSchema.safeParse(validDeployment({ start_date: '2024-06-01', end_date: '' })).success).toBe(true)
    })

    it('accepts end_date only', () => {
      expect(deploymentSchema.safeParse(validDeployment({ start_date: '', end_date: '2024-08-31' })).success).toBe(true)
    })

    it('accepts valid range (start <= end)', () => {
      expect(deploymentSchema.safeParse(validDeployment({ start_date: '2024-06-01', end_date: '2024-08-31' })).success).toBe(true)
    })

    it('accepts same start and end date', () => {
      expect(deploymentSchema.safeParse(validDeployment({ start_date: '2024-06-01', end_date: '2024-06-01' })).success).toBe(true)
    })

    it('rejects end before start', () => {
      const result = deploymentSchema.safeParse(validDeployment({ start_date: '2024-12-01', end_date: '2024-11-01' }))
      expect(result.success).toBe(false)
    })
  })

  // --- dynamic arrays ---
  describe('environmental', () => {
    it('accepts empty array', () => {
      expect(deploymentSchema.safeParse(validDeployment({ environmental: [] })).success).toBe(true)
    })

    it('accepts key-value pairs', () => {
      const result = deploymentSchema.safeParse(validDeployment({
        environmental: [{ key: 'temperature', value: '20°C' }]
      }))
      expect(result.success).toBe(true)
    })
  })

  describe('custom', () => {
    it('accepts empty array', () => {
      expect(deploymentSchema.safeParse(validDeployment({ custom: [] })).success).toBe(true)
    })

    it('accepts up to 50 entries', () => {
      const custom = Array.from({ length: 50 }, (_, i) => ({ key: `key${i}`, value: `val${i}` }))
      expect(deploymentSchema.safeParse(validDeployment({ custom })).success).toBe(true)
    })

    it('rejects over 50 entries', () => {
      const custom = Array.from({ length: 51 }, (_, i) => ({ key: `key${i}`, value: `val${i}` }))
      expect(deploymentSchema.safeParse(validDeployment({ custom })).success).toBe(false)
    })
  })

  // --- defaults round-trip ---
  describe('DEPLOYMENT_DEFAULTS', () => {
    it('fails validation (deployment_name is empty)', () => {
      expect(deploymentSchema.safeParse(DEPLOYMENT_DEFAULTS).success).toBe(false)
    })

    it('passes with a name added', () => {
      expect(deploymentSchema.safeParse({ ...DEPLOYMENT_DEFAULTS, deployment_name: 'Test' }).success).toBe(true)
    })
  })
})

describe('deploymentFieldEntrySchema', () => {
  it('accepts key-value pair', () => {
    expect(deploymentFieldEntrySchema.safeParse({ key: 'temp', value: '20°C' }).success).toBe(true)
  })

  it('accepts empty strings', () => {
    expect(deploymentFieldEntrySchema.safeParse({ key: '', value: '' }).success).toBe(true)
  })
})
```

**Step 2: Run tests to verify they pass**

```bash
cd webui/frontend && npx vitest run src/schemas/__tests__/deployment.test.ts
```

Expected: all pass.

**Step 3: Commit**

```bash
git add webui/frontend/src/schemas/__tests__/deployment.test.ts
git commit -m "test(#454): add deployment schema tests"
```

---

### Task 3: Export Schema from Barrel

**Files:**
- Modify: `webui/frontend/src/schemas/index.ts`

**Step 1: Add deployment exports to barrel file**

Add at the end of `schemas/index.ts`:

```typescript
export { deploymentSchema, deploymentFieldEntrySchema, DEPLOYMENT_DEFAULTS } from './deployment';
export type { DeploymentFormData } from './deployment';
```

**Step 2: Commit**

```bash
git add webui/frontend/src/schemas/index.ts
git commit -m "feat(#454): export deployment schema from barrel"
```

---

### Task 4: Migrate DeploymentEditor to TypeScript + RHF

**Files:**
- Delete: `webui/frontend/src/components/export/DeploymentEditor.jsx`
- Create: `webui/frontend/src/components/export/DeploymentEditor.tsx`

This is the main migration task. Key changes:

1. Replace 10+ `useState` hooks with `useForm` + 2 `useFieldArray`
2. Replace manual `validate()` + `useEffect` with Zod resolver
3. Replace `hasChanges` with `isDirty` from formState
4. Replace prop-types with TypeScript interface
5. Keep all UI structure, dark mode, collapsible sections identical
6. Array-to-object conversion in submit handler (same as before)
7. Photo aggregation auto-fill uses `setValue()` per field
8. CoordinateInput synced via `watch()` and `setValue()`

**Step 1: Create the TypeScript component**

The new component structure:

```typescript
import { useEffect, useState } from 'react'
import { useForm, useFieldArray } from 'react-hook-form'
import type { Resolver } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { ChevronDownIcon, ChevronRightIcon, PlusIcon, XMarkIcon, SparklesIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import CoordinateInput from './CoordinateInput'
// @ts-expect-error — ConfirmDialog.jsx has no type declarations (pre-migration)
import ConfirmDialog from '../common/ConfirmDialog'
import { usePhotoAggregation } from '../../hooks/usePhotoAggregation'
import {
  deploymentSchema,
  DEPLOYMENT_DEFAULTS,
  type DeploymentFormData,
} from '../../schemas/deployment'

interface DeploymentEditorProps {
  deployment?: {
    deployment_name?: string
    location_name?: string
    latitude?: number | null
    longitude?: number | null
    altitude?: number | null
    start_date?: string | null
    end_date?: string | null
    environmental?: Record<string, string>
    mothbox_id?: string
    firmware_version?: string
    custom?: Record<string, string>
  } | null
  directory: string
  filter?: Record<string, unknown>
  onSave: (data: Record<string, unknown>) => void
  onCancel: () => void
  isLoading?: boolean
  error?: string | null
}
```

Key patterns to follow:

- **useForm setup**: Same zodResolver double-cast as GPSSettings (TODO #485)
- **useFieldArray**: Two instances — `{ fields: envFields, append: appendEnv, remove: removeEnv }` for environmental, `{ fields: customFieldEntries, append: appendCustom, remove: removeCustom }` for custom
- **Prop sync**: `useEffect` with `isDirty` guard — convert deployment prop's object fields `{ key: value }` to array form `[{ key, value }]` before calling `reset()`
- **CoordinateInput**: `watch(['latitude', 'longitude'])` for props, `setValue` in onChange callback
- **Photo auto-fill**: `setValue('start_date', ...)`, `setValue('latitude', ...)` etc. with `{ shouldDirty: true }`
- **Submit handler**: `handleSubmit(onValid)` where `onValid` converts arrays back to objects and calls `onSave`
- **Unsaved changes**: `formState.isDirty` replaces `hasChanges`
- **Save button**: `disabled={isLoading}` only — let `handleSubmit` validate on click (same fix as GPSSettings to avoid mode: onBlur + isValid issue)

**Step 2: Delete the old JSX file**

```bash
git rm webui/frontend/src/components/export/DeploymentEditor.jsx
```

**Step 3: Run ESLint**

```bash
cd webui/frontend && npx eslint src/components/export/DeploymentEditor.tsx
```

Expected: 0 errors (warnings for pre-existing `@ts-expect-error` on ConfirmDialog are ok).

**Step 4: Commit**

```bash
git add webui/frontend/src/components/export/DeploymentEditor.tsx
git commit -m "refactor(#454): migrate DeploymentEditor to TypeScript + RHF + Zod"
```

---

### Task 5: Migrate Tests to TypeScript

**Files:**
- Delete: `webui/frontend/src/components/export/__tests__/DeploymentEditor.test.jsx`
- Create: `webui/frontend/src/components/export/__tests__/DeploymentEditor.test.tsx`

**Step 1: Migrate test file**

Key changes:
- File extension `.jsx` → `.tsx`
- Add type annotations to wrapper component (`{ children }: { children: React.ReactNode }`)
- Use `vi.hoisted()` for any mock references (match GPSSettings pattern)
- All 20+ existing test cases preserved
- Update test expectations if behavioral changes exist (e.g., Save button no longer disabled for validation — uses `handleSubmit`)

Important behavioral difference: The old component disabled Save when validation failed. The new component lets `handleSubmit` run validation on click (same as GPSSettings fix). Tests that assert `saveButton.toBeDisabled()` for validation errors need updating — Save is only disabled when `isLoading` is true.

Tests to update:
- "validates deployment_name is required" — Save button is no longer disabled when name is empty; instead clicking Save triggers validation and errors appear inline
- "disables Save when form is invalid" — Same: Save is only disabled during `isLoading`

**Step 2: Run tests**

```bash
cd webui/frontend && npx vitest run src/components/export/__tests__/DeploymentEditor.test.tsx
```

Expected: all pass.

**Step 3: Delete old test file**

```bash
git rm webui/frontend/src/components/export/__tests__/DeploymentEditor.test.jsx
```

**Step 4: Commit**

```bash
git add webui/frontend/src/components/export/__tests__/DeploymentEditor.test.tsx
git commit -m "test(#454): migrate DeploymentEditor tests to TypeScript"
```

---

### Task 6: Final Verification

**Step 1: Run full frontend test suite (sharded)**

```bash
cd webui/frontend && npx vitest run
```

Expected: all pass, no regressions.

**Step 2: Run ESLint on all changed files**

```bash
cd webui/frontend && npx eslint src/schemas/deployment.ts src/components/export/DeploymentEditor.tsx
```

Expected: 0 errors.

**Step 3: Run TypeScript check**

```bash
cd webui/frontend && npx tsc --noEmit
```

Expected: 0 errors.

**Step 4: Verify no dead code**

Confirm `DeploymentEditor.jsx` and `DeploymentEditor.test.jsx` are deleted from the tree. No remaining imports reference the old `.jsx` paths.

```bash
grep -r "DeploymentEditor.jsx" webui/frontend/src/ || echo "No stale imports"
```

Expected: "No stale imports"

---

### Task Summary

| Task | Description | Estimated steps |
|------|-------------|-----------------|
| 1 | Create Zod schema + defaults | 2 |
| 2 | Add schema tests | 3 |
| 3 | Export from barrel | 2 |
| 4 | Migrate component to TSX + RHF | 4 |
| 5 | Migrate tests to TSX | 4 |
| 6 | Final verification | 4 |

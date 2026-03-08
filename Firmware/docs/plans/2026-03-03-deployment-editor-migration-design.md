# DeploymentEditor Migration Design (#454)

**Issue**: #454 — Migrate DeploymentEditor to react-hook-form + Zod
**Parent**: #197 — Standardize form validation with react-hook-form + Zod
**Phase**: 3 (Complex Forms)
**Date**: 2026-03-03

## Architecture

**Pattern**: Hybrid (prop-synced) — `useForm` with `zodResolver`, synced to parent-provided `deployment` prop via `reset()` with `isDirty` guard.

**Validation mode**: `onBlur`

### Form management

- Single `useForm<DeploymentFormData>` replaces 10+ `useState` hooks
- Two `useFieldArray` instances for `environmental` and `custom` dynamic arrays
- Manual `validate()` + `useEffect` replaced by Zod schema + resolver
- Manual `hasChanges` boolean replaced by `formState.isDirty`

### CoordinateInput integration

CoordinateInput stays as a self-contained sub-form with its own internal `useForm` + `zodResolver`. DeploymentEditor passes lat/lng as props via `watch()` and receives changes via `onChange` callback that calls `setValue('latitude', ...)` / `setValue('longitude', ...)`.

### Photo aggregation auto-fill

Uses `setValue()` per field with `{ shouldDirty: true }` — not `reset()` — so dirty tracking works without clearing user edits to other fields. GPS fields filled only when `gps_consistent=true`. Dates always filled.

### Error display

- Field validation errors: inline via `formState.errors` with `aria-invalid` and `aria-describedby`
- Aggregation mutation errors: toast (async, not field-level)

## Schema

**File**: `src/schemas/deployment.ts`

```typescript
const deploymentSchema = z.object({
  deployment_name: z.string().min(1, 'Deployment name is required').max(200, 'Maximum 200 characters'),
  location_name: z.string().max(500, 'Maximum 500 characters').optional().or(z.literal('')),
  latitude: z.number().min(-90).max(90).nullable(),
  longitude: z.number().min(-180).max(180).nullable(),
  altitude: z.number().nullable(),
  start_date: z.string().nullable(),
  end_date: z.string().nullable(),
  environmental: z.array(z.object({ key: z.string(), value: z.string() })),
  custom: z.array(z.object({ key: z.string(), value: z.string() }))
    .max(50, 'Maximum 50 custom fields'),
  mothbox_id: z.string().optional().or(z.literal('')),
  firmware_version: z.string().optional().or(z.literal('')),
}).refine(
  (d) => !d.start_date || !d.end_date || d.start_date <= d.end_date,
  { message: 'End date must be on or after start date', path: ['end_date'] }
);
```

### Defaults

```typescript
const DEPLOYMENT_DEFAULTS: DeploymentFormData = {
  deployment_name: '',
  location_name: '',
  latitude: null,
  longitude: null,
  altitude: null,
  start_date: null,
  end_date: null,
  environmental: [],
  custom: [],
  mothbox_id: '',
  firmware_version: '',
};
```

## What changes

| Before | After |
|--------|-------|
| `DeploymentEditor.jsx` | `DeploymentEditor.tsx` |
| 10+ `useState` hooks for fields | Single `useForm` + 2 `useFieldArray` |
| Manual `validate()` + `useEffect` | Zod schema + `zodResolver` |
| Manual `hasChanges` boolean | `formState.isDirty` |
| `prop-types` | TypeScript interface |
| `DeploymentEditor.test.jsx` | `DeploymentEditor.test.tsx` |

## What stays the same

- All UI structure (sections, collapsibles, dark mode, Heroicons)
- Props interface: `deployment`, `directory`, `filter`, `onSave`, `onCancel`, `isLoading`, `error`
- CoordinateInput as self-contained sub-component
- Photo aggregation auto-fill behavior and UX
- `onSave` data shape (arrays converted to objects before callback)
- Test coverage targets

## Data flow

```
Export.jsx
  ├─ useDeployment(directory) → deployment prop
  └─ DeploymentEditor.tsx
       ├─ useForm({ resolver: zodResolver(deploymentSchema) })
       ├─ useFieldArray('environmental')
       ├─ useFieldArray('custom')
       ├─ reset(deployment) when !isDirty
       ├─ CoordinateInput (sub-form, synced via props/onChange)
       └─ usePhotoAggregation → setValue() per field
           └─ onSave → convert arrays to objects → parent callback
```

## Key risks

1. **zodResolver double-cast**: Same Zod 4 workaround as GPSSettings (TODO #485)
2. **CoordinateInput sync cycles**: Use `lastPropagatedRef` pattern (already implemented in CoordinateInput)
3. **Array-to-object conversion**: Must happen in submit handler, not schema — backend expects `{ key: value }` objects, form uses `[{ key, value }]` arrays

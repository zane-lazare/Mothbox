# CoordinateInput Migration Design

**Issue**: #445
**Date**: 2026-02-25
**Parent**: #197 (Form Validation Standardization)
**Pattern**: Hybrid (prop-synced) — Pattern 3 from design doc

## Decision Summary

| Decision | Choice |
|---|---|
| Schema file | `src/schemas/coordinates.ts` |
| Form pattern | Hybrid — self-contained `useForm`, prop sync via `reset()` |
| Validation mode | `onBlur` |
| DMS toggle | Local `useState`, not part of form data |
| `gpsCoordinates.ts` | Keep import for `formatCoordinateDisplay` (cleanup blocked until #453 GPSSettings migrates) |

## Schema

```typescript
// src/schemas/coordinates.ts
import { z } from 'zod'

export const coordinatesSchema = z.object({
  latitude: z.number().min(-90, 'Latitude must be between -90 and 90')
    .max(90, 'Latitude must be between -90 and 90').nullable(),
  longitude: z.number().min(-180, 'Longitude must be between -180 and 180')
    .max(180, 'Longitude must be between -180 and 180').nullable(),
})

export type CoordinatesFormData = z.infer<typeof coordinatesSchema>
```

No cross-field refinement needed — latitude and longitude are independently valid. Both nullable to match current optional behavior.

## Component Changes

### Before (CoordinateInput.jsx)
- `useState` for `latValue`, `lonValue`, `latError`, `lonError`, `showDMS`
- Two `useEffect` hooks syncing props → local state
- Manual `validateCoordinate()` calls on every keystroke
- Manual `onChange` callback with raw values
- PropTypes

### After (CoordinateInput.tsx)
- `useForm<CoordinatesFormData>` with `zodResolver(coordinatesSchema)`, mode `onBlur`
- `useEffect` + `reset()` with `isDirty` guard for prop sync
- `useWatch` + `useEffect` to propagate validated changes to parent `onChange`
- `FormField` wrapper for each input (standardized error/aria)
- `useState` only for `showDMS` toggle (UI-only state)
- TypeScript interface replaces PropTypes

### Props Interface

```typescript
interface CoordinateInputProps {
  latitude: number | null
  longitude: number | null
  onChange: (coords: { latitude: number | null; longitude: number | null }) => void
  error?: string | null
  disabled?: boolean
}
```

Same contract as today — no parent changes required.

## Test Plan

### Schema tests (`src/schemas/__tests__/coordinates.test.ts`)
- Valid coordinates (boundary values: -90, 90, -180, 180, 0)
- Invalid ranges (e.g., latitude 91, longitude -181)
- Nullable fields (null latitude, null longitude)
- Non-number rejection (NaN, strings)

### Component tests (`CoordinateInput.test.tsx`)
- Migrate existing test file from `.test.jsx` to `.test.tsx`
- Switch validation triggers from `fireEvent.change` to `user.clear` + `user.tab` (blur)
- Preserve all existing test cases: rendering, validation, DMS toggle, disabled state, accessibility, prop sync

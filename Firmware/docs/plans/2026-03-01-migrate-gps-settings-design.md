# GPSSettings Migration Design

**Issue**: #453
**Date**: 2026-03-01
**Status**: Design approved

## Goal

Migrate GPSSettings from manual `useState` + `gpsValidation.js` + `.jsx` to `react-hook-form` + Zod + TypeScript (`.tsx`), using the Hybrid (prop-synced) pattern with `isDirty` guard to fix the polling overwrite bug.

## Architecture

**Pattern**: Hybrid (prop-synced) — form owns editable config state, `reset()` syncs from TanStack Query only when `!isDirty`. Non-form UI (status display, sync, EXIF config, precision) stays as local state or query-derived values.

**Approach**: Replace `localConfig` useState + `validationErrors` useState with `useForm` + `zodResolver`. GPS config fields become registered form fields. TanStack Query polling continues unchanged; the `isDirty` guard prevents overwriting mid-edit keystrokes.

## Schema (`src/schemas/gps-settings.ts`)

Replaces all validation rules from `gpsValidation.js`.

```typescript
import { z } from 'zod'

export const BAUDRATE_VALUES = [4800, 9600, 19200, 38400, 57600, 115200] as const

const DEVICE_PATH_PATTERN = /^\/dev\/(ttyAMA\d+|ttyS\d+|ttyUSB\d+|serial\d+)$/

export const gpsSettingsSchema = z.object({
  enabled: z.boolean(),
  device: z.string()
    .min(1, 'Device path is required')
    .regex(DEVICE_PATH_PATTERN, 'Must be a valid serial device path (e.g., /dev/ttyAMA0)'),
  baudrate: z.coerce.number().refine(
    (v) => (BAUDRATE_VALUES as readonly number[]).includes(v),
    'Invalid baudrate'
  ),
  timeout_hot: z.coerce.number().min(5).max(60),
  timeout_warm: z.coerce.number().min(30).max(180),
  timeout_cold: z.coerce.number().min(60).max(300),
  timeout_almanac: z.coerce.number().min(5).max(30),
})

export type GpsSettingsFormData = z.infer<typeof gpsSettingsSchema>
```

Intentionally uses `z.coerce.number()` for timeout sliders and baudrate select, which produce string values from HTML elements.

## Component Changes (`GPSSettings.tsx`)

### State management replacement

| Before (useState) | After (react-hook-form) |
|---|---|
| `useState(null)` (localConfig) | `useForm<GpsSettingsFormData>` |
| `useState({})` (validationErrors) | `formState.errors` |
| `setLocalConfig({...localConfig, [key]: val})` | `register('field')` |
| `validateDevicePath()` / `validateBaudrate()` | Zod schema via resolver |
| `useEffect` syncs gpsConfig → localConfig | `useEffect` calls `reset()` when `!isDirty` |

### State that stays as local useState

- `isCollapsed`, `timeoutsCollapsed`, `exifSectionOpen` — UI collapse toggles
- `syncing` — GPS sync operation flag
- `gpsPrecision` — display precision (localStorage-backed)
- `selectedSource` — EXIF source selection
- `showRestartConfirm` — confirmation dialog state

### Query sync (fixes polling overwrite bug)

```typescript
useEffect(() => {
  if (gpsConfig && !isDirty) {
    reset(mapConfigToForm(gpsConfig))
  }
}, [gpsConfig, isDirty, reset])
```

### Helper function

`mapConfigToForm(gpsConfig): GpsSettingsFormData` — maps API response shape to form field names. Keeps the mapping explicit and testable.

### Props interface

None — GPSSettings is a self-contained component with no props.

## Test Changes (`GPSSettings.test.tsx`)

- Rename `.test.jsx` → `.test.tsx`
- Add type imports
- All existing tests preserved (behavior unchanged)
- No new validation error tests (no new UX)

## Barrel export update (`src/schemas/index.ts`)

Add:
```typescript
export { gpsSettingsSchema, BAUDRATE_VALUES } from './gps-settings';
export type { GpsSettingsFormData } from './gps-settings';
```

## What stays the same

- All TanStack Query usage (config fetch, status polling, mutation)
- CollapsibleCard UI structure and all Tailwind styling
- GPS status display section (fix type, satellites, coordinates)
- Sync button with toast progress
- EXIF configuration section
- Precision selector
- Confirm dialog for service restart
- Toast notifications for success/error
- All existing test assertions

## Files

| Action | Path |
|---|---|
| Create | `src/schemas/gps-settings.ts` |
| Create | `src/schemas/__tests__/gps-settings.test.ts` |
| Rename+Rewrite | `src/components/GPSSettings.jsx` → `.tsx` |
| Rename+Rewrite | `src/components/__tests__/GPSSettings.test.jsx` → `.test.tsx` |
| Modify | `src/schemas/index.ts` (add exports) |

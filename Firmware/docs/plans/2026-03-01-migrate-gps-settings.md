# GPSSettings Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate GPSSettings from manual useState + gpsValidation.js + .jsx to react-hook-form + Zod + TypeScript (.tsx), fixing the polling overwrite bug with isDirty guard.

**Architecture:** Hybrid (prop-synced) pattern. useForm owns editable config fields; reset() syncs from TanStack Query only when !isDirty. Non-form UI (status display, sync, EXIF, precision) stays as local state. z.coerce.number() handles string values from HTML range/select inputs.

**Tech Stack:** react-hook-form, zod, @hookform/resolvers, TypeScript, Vitest, React Testing Library

---

### Task 1: Create Zod schema and tests

**Files:**
- Create: `src/schemas/gps-settings.ts`
- Create: `src/schemas/__tests__/gps-settings.test.ts`

**Context:** The schema replaces all validation rules from `src/utils/gpsValidation.js`. The component stores all timeout values in seconds. The `timeout_almanac` slider range is 300-1800 seconds (displayed as 5-30 minutes in the UI). A legacy `timeout` field passes through for API compatibility.

**Step 1: Create the schema file**

Create `src/schemas/gps-settings.ts`:

```typescript
import { z } from 'zod'

export const BAUDRATE_VALUES = [4800, 9600, 19200, 38400, 57600, 115200] as const

const DEVICE_PATH_PATTERN = /^\/dev\/(ttyAMA\d+|ttyS\d+|ttyUSB\d+|serial\d+)$/

export const gpsSettingsSchema = z.object({
  enabled: z.boolean(),
  device: z.string()
    .min(1, 'Device path is required')
    .regex(DEVICE_PATH_PATTERN, 'Invalid device path format. Expected /dev/ttyAMA0, /dev/ttyUSB0, etc.'),
  baudrate: z.coerce.number().refine(
    (v) => (BAUDRATE_VALUES as readonly number[]).includes(v),
    'Invalid baudrate',
  ),
  timeout: z.coerce.number(),
  timeout_hot: z.coerce.number().min(5, 'Must be at least 5s').max(60, 'Cannot exceed 60s'),
  timeout_warm: z.coerce.number().min(30, 'Must be at least 30s').max(180, 'Cannot exceed 180s'),
  timeout_cold: z.coerce.number().min(60, 'Must be at least 60s').max(300, 'Cannot exceed 300s'),
  timeout_almanac: z.coerce.number().min(300, 'Must be at least 300s').max(1800, 'Cannot exceed 1800s'),
})

export type GpsSettingsFormData = z.infer<typeof gpsSettingsSchema>

export const GPS_SETTINGS_DEFAULTS: GpsSettingsFormData = {
  enabled: false,
  device: '/dev/ttyAMA0',
  baudrate: 9600,
  timeout: 10,
  timeout_hot: 15,
  timeout_warm: 60,
  timeout_cold: 90,
  timeout_almanac: 1200,
}
```

**Step 2: Create the schema test file**

Create `src/schemas/__tests__/gps-settings.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import {
  gpsSettingsSchema,
  BAUDRATE_VALUES,
  GPS_SETTINGS_DEFAULTS,
  type GpsSettingsFormData,
} from '../gps-settings'

// Helper to get first error message from a failed parse
function firstError(result: { success: false; error: { issues: Array<{ message: string }> } }): string {
  return result.error.issues[0]?.message ?? ''
}

const validConfig: GpsSettingsFormData = {
  enabled: true,
  device: '/dev/ttyAMA0',
  baudrate: 9600,
  timeout: 10,
  timeout_hot: 15,
  timeout_warm: 60,
  timeout_cold: 90,
  timeout_almanac: 1200,
}

describe('BAUDRATE_VALUES', () => {
  it('contains standard GPS baudrates', () => {
    expect(BAUDRATE_VALUES).toEqual([4800, 9600, 19200, 38400, 57600, 115200])
  })
})

describe('GPS_SETTINGS_DEFAULTS', () => {
  it('passes schema validation', () => {
    expect(gpsSettingsSchema.safeParse(GPS_SETTINGS_DEFAULTS).success).toBe(true)
  })
})

describe('gpsSettingsSchema', () => {
  it('accepts valid config', () => {
    expect(gpsSettingsSchema.safeParse(validConfig).success).toBe(true)
  })

  // Device path validation
  describe('device', () => {
    it.each(['/dev/ttyAMA0', '/dev/ttyS0', '/dev/ttyUSB0', '/dev/serial0'])(
      'accepts valid device path: %s',
      (device) => {
        expect(gpsSettingsSchema.safeParse({ ...validConfig, device }).success).toBe(true)
      },
    )

    it('rejects empty device path', () => {
      const result = gpsSettingsSchema.safeParse({ ...validConfig, device: '' })
      expect(result.success).toBe(false)
    })

    it('rejects device path not starting with /dev/', () => {
      const result = gpsSettingsSchema.safeParse({ ...validConfig, device: '/tmp/ttyAMA0' })
      expect(result.success).toBe(false)
    })

    it('rejects invalid device path format', () => {
      const result = gpsSettingsSchema.safeParse({ ...validConfig, device: '/dev/sda1' })
      expect(result.success).toBe(false)
      if (!result.success) {
        expect(firstError(result)).toMatch(/invalid device path/i)
      }
    })
  })

  // Baudrate validation
  describe('baudrate', () => {
    it.each(BAUDRATE_VALUES)('accepts valid baudrate: %d', (baudrate) => {
      expect(gpsSettingsSchema.safeParse({ ...validConfig, baudrate }).success).toBe(true)
    })

    it('coerces string baudrate to number', () => {
      const result = gpsSettingsSchema.safeParse({ ...validConfig, baudrate: '9600' })
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.baudrate).toBe(9600)
      }
    })

    it('rejects invalid baudrate', () => {
      const result = gpsSettingsSchema.safeParse({ ...validConfig, baudrate: 12345 })
      expect(result.success).toBe(false)
    })
  })

  // Timeout validation
  describe('timeout_hot', () => {
    it('accepts value in range 5-60', () => {
      expect(gpsSettingsSchema.safeParse({ ...validConfig, timeout_hot: 5 }).success).toBe(true)
      expect(gpsSettingsSchema.safeParse({ ...validConfig, timeout_hot: 60 }).success).toBe(true)
    })

    it('rejects value below 5', () => {
      const result = gpsSettingsSchema.safeParse({ ...validConfig, timeout_hot: 4 })
      expect(result.success).toBe(false)
    })

    it('rejects value above 60', () => {
      const result = gpsSettingsSchema.safeParse({ ...validConfig, timeout_hot: 61 })
      expect(result.success).toBe(false)
    })

    it('coerces string to number', () => {
      const result = gpsSettingsSchema.safeParse({ ...validConfig, timeout_hot: '30' })
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.timeout_hot).toBe(30)
      }
    })
  })

  describe('timeout_warm', () => {
    it('accepts value in range 30-180', () => {
      expect(gpsSettingsSchema.safeParse({ ...validConfig, timeout_warm: 30 }).success).toBe(true)
      expect(gpsSettingsSchema.safeParse({ ...validConfig, timeout_warm: 180 }).success).toBe(true)
    })

    it('rejects value below 30', () => {
      expect(gpsSettingsSchema.safeParse({ ...validConfig, timeout_warm: 29 }).success).toBe(false)
    })

    it('rejects value above 180', () => {
      expect(gpsSettingsSchema.safeParse({ ...validConfig, timeout_warm: 181 }).success).toBe(false)
    })
  })

  describe('timeout_cold', () => {
    it('accepts value in range 60-300', () => {
      expect(gpsSettingsSchema.safeParse({ ...validConfig, timeout_cold: 60 }).success).toBe(true)
      expect(gpsSettingsSchema.safeParse({ ...validConfig, timeout_cold: 300 }).success).toBe(true)
    })

    it('rejects value below 60', () => {
      expect(gpsSettingsSchema.safeParse({ ...validConfig, timeout_cold: 59 }).success).toBe(false)
    })

    it('rejects value above 300', () => {
      expect(gpsSettingsSchema.safeParse({ ...validConfig, timeout_cold: 301 }).success).toBe(false)
    })
  })

  describe('timeout_almanac', () => {
    it('accepts value in range 300-1800 (seconds)', () => {
      expect(gpsSettingsSchema.safeParse({ ...validConfig, timeout_almanac: 300 }).success).toBe(true)
      expect(gpsSettingsSchema.safeParse({ ...validConfig, timeout_almanac: 1800 }).success).toBe(true)
    })

    it('rejects value below 300', () => {
      expect(gpsSettingsSchema.safeParse({ ...validConfig, timeout_almanac: 299 }).success).toBe(false)
    })

    it('rejects value above 1800', () => {
      expect(gpsSettingsSchema.safeParse({ ...validConfig, timeout_almanac: 1801 }).success).toBe(false)
    })
  })

  // Missing required fields
  describe('required fields', () => {
    it('rejects missing enabled', () => {
      const { enabled: _enabled, ...rest } = validConfig
      expect(gpsSettingsSchema.safeParse(rest).success).toBe(false)
    })

    it('rejects missing device', () => {
      const { device: _device, ...rest } = validConfig
      expect(gpsSettingsSchema.safeParse(rest).success).toBe(false)
    })

    it('rejects missing baudrate', () => {
      const { baudrate: _baudrate, ...rest } = validConfig
      expect(gpsSettingsSchema.safeParse(rest).success).toBe(false)
    })
  })
})
```

**Step 3: Run tests to verify they pass**

Run: `cd webui/frontend && npx vitest run src/schemas/__tests__/gps-settings.test.ts`
Expected: All tests pass.

**Step 4: Commit**

```bash
git add src/schemas/gps-settings.ts src/schemas/__tests__/gps-settings.test.ts
git commit -m "feat(#453): add Zod schema and tests for GPS settings"
```

---

### Task 2: Add barrel exports

**Files:**
- Modify: `src/schemas/index.ts`

**Context:** Follow the existing barrel export pattern. All other schema modules are re-exported from `src/schemas/index.ts` with semicolons at line endings.

**Step 1: Add exports to barrel file**

Append to `src/schemas/index.ts`:

```typescript
export { gpsSettingsSchema, BAUDRATE_VALUES, GPS_SETTINGS_DEFAULTS } from './gps-settings';
export type { GpsSettingsFormData } from './gps-settings';
```

**Step 2: Verify TypeScript compiles**

Run: `cd webui/frontend && npx tsc --noEmit`
Expected: No errors.

**Step 3: Commit**

```bash
git add src/schemas/index.ts
git commit -m "refactor(#453): add GPS settings schema to barrel exports"
```

---

### Task 3: Migrate component to TypeScript with RHF

**Files:**
- Rename+Rewrite: `src/components/GPSSettings.jsx` → `src/components/GPSSettings.tsx`

**Context:** This is a 753-LOC component. The migration replaces `localConfig` useState + `validationErrors` useState with `useForm`. All other state (collapse toggles, syncing, precision, EXIF source, restart confirm) stays as useState. The `useEffect` that syncs query data adds an `isDirty` guard to fix the polling overwrite bug.

Key behavior to preserve:
- TanStack Query for GPS config (fetch) and status (15s polling)
- useMutation for config saves with toast notifications
- Conditional rendering when GPS is disabled
- Timeout slider inputs (range elements produce string values — `z.coerce.number()` handles this)
- Restart confirmation dialog when device/baudrate changes
- GPS sync with progress toast recreation every 20s
- EXIF tagging section (separate from the main form)
- Precision selector (localStorage-backed, not part of form)

**Step 1: Rename file and update imports**

Rename `GPSSettings.jsx` → `GPSSettings.tsx`.

Replace the imports at the top:

```typescript
import { useEffect, useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getGpsConfig, updateGpsConfig, getGpsStatus, syncGps } from '../utils/api'
import { formatTimestamp } from '../utils/helpers'
import { formatCoordinateDisplay } from '../utils/gpsCoordinates'
import { GPS_PRECISION_OPTIONS, getGpsPrecision, setGpsPrecision } from '../utils/gpsPrecision'
import { QUERY_KEYS } from '../utils/queryKeys'
import toast from 'react-hot-toast'
import CollapsibleCard from './CollapsibleCard'
import ConfirmDialog from './common/ConfirmDialog'
import { useGpsExifStatus, useGpsExifConfig, useUpdateGpsExifConfig } from '../hooks/useGpsExif'
import {
  gpsSettingsSchema,
  GPS_SETTINGS_DEFAULTS,
  type GpsSettingsFormData,
} from '../schemas/gps-settings'
```

Remove these imports (no longer needed):
- `validateDevicePath`, `validateBaudrate` from `gpsValidation`

**Step 2: Replace state management**

Remove these useState calls:
```typescript
// REMOVE:
const [localConfig, setLocalConfig] = useState(null)
const [validationErrors, setValidationErrors] = useState({})
```

Add useForm:
```typescript
const { register, reset, watch, getValues, formState: { errors, isDirty } } = useForm<GpsSettingsFormData>({
  resolver: zodResolver(gpsSettingsSchema),
  defaultValues: GPS_SETTINGS_DEFAULTS,
  mode: 'onBlur',
})
```

Keep all other useState calls unchanged:
```typescript
const [isCollapsed, setIsCollapsed] = useState(false)
const [timeoutsCollapsed, setTimeoutsCollapsed] = useState(true)
const [syncing, setSyncing] = useState(false)
const [showRestartConfirm, setShowRestartConfirm] = useState(false)
const [gpsPrecision, setGpsPrecisionState] = useState(() => getGpsPrecision())
const [exifSectionOpen, setExifSectionOpen] = useState(false)
const [selectedSource, setSelectedSource] = useState('deployment,gps')
```

**Step 3: Replace the query sync useEffect**

Replace:
```typescript
useEffect(() => {
  if (gpsConfig) {
    setLocalConfig(gpsConfig)
  }
}, [gpsConfig])
```

With (isDirty guard fixes the polling overwrite bug):
```typescript
useEffect(() => {
  if (gpsConfig && !isDirty) {
    reset(gpsConfig)
  }
}, [gpsConfig, isDirty, reset])
```

**Step 4: Remove manual validation handlers**

Remove `handleDeviceChange`, `handleBaudrateChange`, and `isFormValid` functions entirely. RHF + Zod handles validation.

**Step 5: Update handleSaveConfig and doSaveConfig**

Replace `handleSaveConfig`:
```typescript
const handleSaveConfig = () => {
  const values = getValues()

  // Check if device or baudrate changed (requires gpsd restart)
  const deviceChanged = values.device !== gpsConfig.device
  const baudrateChanged = values.baudrate !== gpsConfig.baudrate

  if (deviceChanged || baudrateChanged) {
    setShowRestartConfirm(true)
    return
  }

  doSaveConfig()
}
```

Replace `doSaveConfig`:
```typescript
const doSaveConfig = () => {
  const values = getValues()
  setShowRestartConfirm(false)
  updateConfigMutation.mutate({
    gps_enabled: values.enabled,
    gps_device: values.device,
    gps_baudrate: values.baudrate,
    gps_timeout: values.timeout,
    gps_timeout_hot: values.timeout_hot,
    gps_timeout_warm: values.timeout_warm,
    gps_timeout_cold: values.timeout_cold,
    gps_timeout_almanac: values.timeout_almanac,
  })
}
```

**Step 6: Update handleSyncGPS**

Replace `localConfig` references with `getValues()`:
```typescript
const handleSyncGPS = async () => {
  const values = getValues()
  if (!values.enabled) {
    toast.error('GPS is disabled. Enable it first.')
    return
  }
  // ... rest stays the same, but replace:
  // localConfig?.timeout_hot → values.timeout_hot
  // localConfig?.timeout_warm → values.timeout_warm
  // localConfig?.timeout_cold → values.timeout_cold
  // localConfig?.timeout_almanac → values.timeout_almanac
  // localConfig?.timeout → values.timeout
```

**Step 7: Update the enable/disable toggle**

Replace:
```tsx
<input
  type="checkbox"
  checked={localConfig?.enabled || false}
  onChange={(e) => setLocalConfig({...localConfig, enabled: e.target.checked})}
  className="sr-only peer"
/>
```

With:
```tsx
<input
  type="checkbox"
  {...register('enabled')}
  className="sr-only peer"
/>
```

Note: For the conditional rendering `{localConfig?.enabled && (...)}`, replace with `{watch('enabled') && (...)}`.

**Step 8: Update device path input**

Replace:
```tsx
<input
  type="text"
  value={localConfig?.device || ''}
  onChange={(e) => handleDeviceChange(e.target.value)}
  placeholder="/dev/ttyAMA0"
  aria-label="GPS Device Path"
  className={`...${validationErrors.device ? 'border-red-300...' : ...}`}
/>
```

With:
```tsx
<input
  type="text"
  {...register('device')}
  placeholder="/dev/ttyAMA0"
  aria-label="GPS Device Path"
  className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${
    errors.device
      ? 'border-red-300 focus:ring-red-500 bg-red-50'
      : watch('device')
      ? 'border-green-300 focus:ring-green-500 bg-green-50'
      : 'border-gray-300 focus:ring-blue-500'
  }`}
/>
```

Update the validation indicator in the label:
```tsx
{errors.device && (
  <span className="ml-2 text-red-600 text-xs">✗</span>
)}
{!errors.device && watch('device') && (
  <span className="ml-2 text-green-600 text-xs">✓</span>
)}
```

Update the error message below:
```tsx
{errors.device ? (
  <p className="text-xs text-red-600 mt-1">
    ⚠️ {errors.device.message}
  </p>
) : (
  <p className="text-xs text-gray-500 mt-1">
    UART device path (typically /dev/ttyAMA0 for Pi GPIO UART)
  </p>
)}
```

**Step 9: Update baudrate select**

Replace:
```tsx
<select
  value={localConfig?.baudrate || 9600}
  onChange={(e) => handleBaudrateChange(parseInt(e.target.value))}
  aria-label="Baud Rate"
  ...
>
```

With:
```tsx
<select
  {...register('baudrate')}
  aria-label="Baud Rate"
  className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${
    errors.baudrate
      ? 'border-red-300 focus:ring-red-500 bg-red-50'
      : 'border-green-300 focus:ring-green-500 bg-green-50'
  }`}
>
```

Update the error display below:
```tsx
{errors.baudrate ? (
  <p className="text-xs text-red-600 mt-1">
    ⚠️ {errors.baudrate.message}
  </p>
) : (
  <p className="text-xs text-gray-500 mt-1">
    Serial communication speed (9600 is default for NEO-M8N)
  </p>
)}
```

**Step 10: Update timeout sliders**

For each timeout slider, replace `localConfig?.timeout_X` with `watch('timeout_X')` in the label display, and replace `setLocalConfig({...localConfig, timeout_X: ...})` with `{...register('timeout_X')}`.

Example for hot start:
```tsx
<label className="block text-xs font-medium text-gray-700 mb-1">
  🟢 Hot Start (&lt;4 hours): {watch('timeout_hot')}s
</label>
<input
  type="range"
  min="5"
  max="60"
  step="5"
  {...register('timeout_hot')}
  className="w-full"
/>
```

For almanac timeout, the display shows minutes:
```tsx
<label className="block text-xs font-medium text-gray-700 mb-1">
  🔴 Almanac Expired (&gt;28d): {Math.floor(watch('timeout_almanac') / 60)}m
</label>
<input
  type="range"
  min="300"
  max="1800"
  step="60"
  {...register('timeout_almanac')}
  className="w-full"
/>
```

**Step 11: Update Reset to Defaults button**

Replace:
```tsx
<button
  onClick={() => setLocalConfig({
    ...localConfig,
    timeout_hot: 15,
    timeout_warm: 60,
    timeout_cold: 90,
    timeout_almanac: 1200
  })}
  ...
>
```

With:
```tsx
<button
  onClick={() => {
    const current = getValues()
    reset({
      ...current,
      timeout_hot: GPS_SETTINGS_DEFAULTS.timeout_hot,
      timeout_warm: GPS_SETTINGS_DEFAULTS.timeout_warm,
      timeout_cold: GPS_SETTINGS_DEFAULTS.timeout_cold,
      timeout_almanac: GPS_SETTINGS_DEFAULTS.timeout_almanac,
    })
  }}
  ...
>
```

**Step 12: Update Save button disabled state**

Replace:
```tsx
disabled={updateConfigMutation.isLoading || !isFormValid()}
title={!isFormValid() ? 'Please fix validation errors' : ''}
```

With:
```tsx
disabled={updateConfigMutation.isPending || Object.keys(errors).length > 0}
title={Object.keys(errors).length > 0 ? 'Please fix validation errors' : ''}
```

Note: `isLoading` → `isPending` follows TanStack Query v5 naming (already used elsewhere in the file for `updateExifConfig.isPending`).

**Step 13: Verify**

Run: `cd webui/frontend && npx tsc --noEmit`
Expected: No errors.

Run: `cd webui/frontend && npx vitest run src/components/__tests__/GPSSettings.test`
Expected: All existing tests pass.

**Step 14: Commit**

```bash
git add src/components/GPSSettings.tsx
git commit -m "refactor(#453): migrate GPSSettings to TypeScript with RHF + Zod"
```

Delete stale file if git didn't handle the rename:
```bash
git rm src/components/GPSSettings.jsx 2>/dev/null || true
```

---

### Task 4: Migrate tests to TypeScript

**Files:**
- Rename: `src/components/__tests__/GPSSettings.test.jsx` → `src/components/__tests__/GPSSettings.test.tsx`

**Context:** The test file is 290 lines. It should need minimal changes — primarily the file rename and import path update to `.tsx`. The test behavior assertions should all work with the new RHF-based component since the external behavior is unchanged.

**Step 1: Rename the test file**

```bash
git mv src/components/__tests__/GPSSettings.test.jsx src/components/__tests__/GPSSettings.test.tsx
```

**Step 2: Run tests to verify they pass**

Run: `cd webui/frontend && npx vitest run src/components/__tests__/GPSSettings.test.tsx`
Expected: All tests pass without code changes.

If any tests fail due to timing (RHF is async), wrap assertions in `waitFor`:
```typescript
await waitFor(() => {
  expect(input).toHaveValue('/dev/ttyUSB0')
})
```

**Step 3: Commit**

```bash
git add src/components/__tests__/GPSSettings.test.tsx
git commit -m "test(#453): migrate GPSSettings tests to TypeScript"
```

---

### Task 5: Final verification

**No files changed — verification only.**

**Step 1: TypeScript compilation**

Run: `cd webui/frontend && npx tsc --noEmit`
Expected: Clean, no errors.

**Step 2: ESLint**

Run: `cd webui/frontend && npx eslint src/schemas/gps-settings.ts src/schemas/__tests__/gps-settings.test.ts src/components/GPSSettings.tsx src/components/__tests__/GPSSettings.test.tsx`
Expected: No errors (warnings about deprecated imports in other files are fine).

**Step 3: Related tests**

Run: `cd webui/frontend && npx vitest run src/schemas/__tests__/gps-settings.test.ts src/components/__tests__/GPSSettings.test.tsx`
Expected: All tests pass.

**Step 4: Full test suite**

Run: `cd webui/frontend && npx vitest run`
Expected: All ~6200 tests pass. No regressions.

**Step 5: Verify no stale files**

Run: `ls src/components/GPSSettings.jsx src/components/__tests__/GPSSettings.test.jsx 2>&1`
Expected: "No such file or directory" for both — old .jsx files should not exist.

# Remove Deprecated Validation Utilities Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Delete three deprecated validation utility files (#456, #457, #458) and migrate their remaining consumers to schema-based or standalone replacements.

**Architecture:** gpsValidation.js is orphaned — delete directly. presetValidation.ts has liveview validation rules not covered by the camera-preset schema — relocate to a new `liveview-settings.ts` schema. gpsCoordinates.ts has formatting utilities not covered by the coordinates schema — relocate `formatCoordinateDisplay` (and its dependencies) to a new `utils/coordinateFormat.ts` module.

**Tech Stack:** TypeScript, Zod, Vitest, React

**Issues:** #456 (gpsValidation.js), #457 (presetValidation.ts), #458 (gpsCoordinates.ts)

**Branch:** `feat/456-457-458-remove-deprecated-validation`

---

## Task 1: Delete orphaned gpsValidation.js (#456)

**Files:**
- Delete: `webui/frontend/src/utils/gpsValidation.js`
- Delete: `webui/frontend/src/utils/__tests__/gpsValidation.test.js`

This file has zero imports anywhere in the codebase. Its validation logic was replaced by `src/schemas/gps-settings.ts`.

**Step 1: Verify no imports exist**

Run: `cd webui/frontend && npx grep -r "gpsValidation" src/ --include="*.{js,jsx,ts,tsx}" | grep -v __tests__/gpsValidation`
Expected: No output (zero imports)

**Step 2: Delete the files**

```bash
cd webui/frontend
rm src/utils/gpsValidation.js
rm src/utils/__tests__/gpsValidation.test.js
```

**Step 3: Run tests to confirm nothing breaks**

Run: `cd webui/frontend && npx vitest run --reporter=verbose 2>&1 | tail -20`
Expected: All tests pass, no import errors

**Step 4: Commit**

```bash
git add -A
git commit -m "fix(#456): delete orphaned gpsValidation.js and its tests

The gpsValidation.js utility had zero active imports. All GPS config
validation is now handled by schemas/gps-settings.ts (Zod schema)."
```

---

## Task 2: Create liveview-settings schema (#457)

**Files:**
- Create: `webui/frontend/src/schemas/liveview-settings.ts`
- Create: `webui/frontend/src/schemas/__tests__/liveview-settings.test.ts`

The existing `presetValidation.ts` contains 31 liveview setting validation rules that mirror backend `ALLOWED_LIVEVIEW_SETTINGS`. The replacement schema `camera-preset.ts` only covers preset metadata (name, description, workflow). We need a new Zod schema for the liveview rules, plus wrapper functions that match the existing API (`validatePresetSettings`, `formatValidationErrors`).

**Step 1: Write the failing test**

Create `webui/frontend/src/schemas/__tests__/liveview-settings.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import {
  liveviewSettingsSchema,
  validateLiveviewSettings,
  formatLiveviewValidationErrors,
  type LiveviewValidationError,
} from '../liveview-settings'

describe('liveviewSettingsSchema', () => {
  describe('boolean fields', () => {
    it('accepts actual booleans', () => {
      const result = liveviewSettingsSchema.safeParse({ focus_peaking_enabled: true })
      expect(result.success).toBe(true)
    })

    it('accepts string "true"/"false"', () => {
      const result = liveviewSettingsSchema.safeParse({ awb_enable: 'true' })
      expect(result.success).toBe(true)
    })

    it('rejects invalid boolean strings', () => {
      const result = liveviewSettingsSchema.safeParse({ ae_enable: 'yes' })
      expect(result.success).toBe(false)
    })
  })

  describe('enum fields', () => {
    it('accepts valid af_mode values (0, 1, 2)', () => {
      expect(liveviewSettingsSchema.safeParse({ af_mode: 0 }).success).toBe(true)
      expect(liveviewSettingsSchema.safeParse({ af_mode: 2 }).success).toBe(true)
    })

    it('accepts string-encoded integers', () => {
      expect(liveviewSettingsSchema.safeParse({ af_mode: '1' }).success).toBe(true)
    })

    it('rejects out-of-range enum values', () => {
      expect(liveviewSettingsSchema.safeParse({ af_mode: 5 }).success).toBe(false)
    })
  })

  describe('range fields', () => {
    it('accepts sharpness within range (0.0 - 4.0)', () => {
      expect(liveviewSettingsSchema.safeParse({ sharpness: 2.5 }).success).toBe(true)
    })

    it('rejects sharpness out of range', () => {
      expect(liveviewSettingsSchema.safeParse({ sharpness: 5.0 }).success).toBe(false)
    })

    it('accepts brightness at boundaries (-1.0 to 1.0)', () => {
      expect(liveviewSettingsSchema.safeParse({ brightness: -1.0 }).success).toBe(true)
      expect(liveviewSettingsSchema.safeParse({ brightness: 1.0 }).success).toBe(true)
    })

    it('accepts exposure_time integer (1 to 999999)', () => {
      expect(liveviewSettingsSchema.safeParse({ exposure_time: 50000 }).success).toBe(true)
    })

    it('rejects exposure_time at 0', () => {
      expect(liveviewSettingsSchema.safeParse({ exposure_time: 0 }).success).toBe(false)
    })
  })

  describe('string enum fields', () => {
    it('accepts valid focus_peaking_colour', () => {
      expect(liveviewSettingsSchema.safeParse({ focus_peaking_colour: 'green' }).success).toBe(true)
    })

    it('rejects invalid focus_peaking_colour', () => {
      expect(liveviewSettingsSchema.safeParse({ focus_peaking_colour: 'purple' }).success).toBe(false)
    })

    it('accepts valid focus_peaking_algorithm', () => {
      expect(liveviewSettingsSchema.safeParse({ focus_peaking_algorithm: 'sobel' }).success).toBe(true)
    })
  })

  describe('passthrough for unknown keys', () => {
    it('passes through keys not in the schema', () => {
      const result = liveviewSettingsSchema.safeParse({ unknown_key: 'value', sharpness: 1.0 })
      expect(result.success).toBe(true)
    })
  })
})

describe('validateLiveviewSettings', () => {
  it('returns empty array for valid settings', () => {
    const errors = validateLiveviewSettings({ sharpness: 2.0, brightness: 0.5 })
    expect(errors).toEqual([])
  })

  it('returns errors for invalid settings', () => {
    const errors = validateLiveviewSettings({ sharpness: 5.0, brightness: 2.0 })
    expect(errors).toHaveLength(2)
    expect(errors[0]).toMatchObject({ key: 'sharpness' })
    expect(errors[1]).toMatchObject({ key: 'brightness' })
  })

  it('handles camelCase keys via toBackendKey conversion', () => {
    const errors = validateLiveviewSettings({ colourGainsRed: 0.5 })
    expect(errors).toHaveLength(1)
    expect(errors[0].key).toBe('colour_gains_red')
  })
})

describe('formatLiveviewValidationErrors', () => {
  it('returns empty string for no errors', () => {
    expect(formatLiveviewValidationErrors([])).toBe('')
  })

  it('formats errors with count header', () => {
    const errors: LiveviewValidationError[] = [
      { key: 'sharpness', value: 5.0, message: 'Sharpness must be between 0.0 and 4.0' },
    ]
    const result = formatLiveviewValidationErrors(errors)
    expect(result).toContain('1 error')
    expect(result).toContain('sharpness')
  })

  it('truncates at maxErrors', () => {
    const errors: LiveviewValidationError[] = Array.from({ length: 10 }, (_, i) => ({
      key: `key_${i}`,
      value: i,
      message: `Error ${i}`,
    }))
    const result = formatLiveviewValidationErrors(errors, 3)
    expect(result).toContain('and 7 more')
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd webui/frontend && npx vitest run src/schemas/__tests__/liveview-settings.test.ts --reporter=verbose 2>&1 | tail -10`
Expected: FAIL — module `../liveview-settings` not found

**Step 3: Write the liveview-settings schema**

Create `webui/frontend/src/schemas/liveview-settings.ts`:

```typescript
/**
 * Liveview settings validation schema.
 *
 * Mirrors backend ALLOWED_LIVEVIEW_SETTINGS from webui/backend/utils.py.
 * Replaces the imperative validators in utils/presetValidation.ts with Zod.
 *
 * All fields are optional because consumers validate partial settings objects
 * (only the keys present in the current preset/form). Unknown keys pass through.
 */
import { z } from 'zod'
import { toBackendKey } from '../utils/cameraControlMapping'

// ---------------------------------------------------------------------------
// Helpers — coerce string-encoded values from backend CSV storage
// ---------------------------------------------------------------------------

/** Accept boolean or string "true"/"false" (case-insensitive). */
const booleanish = z.union([
  z.boolean(),
  z.string().refine(
    (v) => v.toLowerCase() === 'true' || v.toLowerCase() === 'false',
    { message: 'Must be "true" or "false"' },
  ),
])

/** Accept number or string-encoded integer, then validate against allowed values. */
const intEnum = (allowed: number[], label: string) =>
  z.preprocess(
    (v) => (typeof v === 'string' ? parseInt(v, 10) : v),
    z.number({ message: `${label} must be a number` })
      .int(`${label} must be an integer`)
      .refine((n) => allowed.includes(n), {
        message: `${label} must be one of: ${allowed.join(', ')}`,
      }),
  )

/** Accept number or string-encoded float, then validate range. */
const floatRange = (min: number, max: number, label: string) =>
  z.preprocess(
    (v) => (typeof v === 'string' ? parseFloat(v) : v),
    z.number({ message: `${label} must be a number` })
      .min(min, `${label} must be at least ${min}`)
      .max(max, `${label} must be at most ${max}`),
  )

/** Accept number or string-encoded integer, then validate range (exclusive/inclusive as needed). */
const intRange = (min: number, max: number, label: string, { minExclusive = false } = {}) =>
  z.preprocess(
    (v) => (typeof v === 'string' ? parseInt(v, 10) : v),
    z.number({ message: `${label} must be a number` })
      .int(`${label} must be a whole number`)
      .refine((n) => (minExclusive ? n > min : n >= min), {
        message: `${label} must be ${minExclusive ? 'greater than' : 'at least'} ${min}`,
      })
      .max(max, `${label} must be at most ${max}`),
  )

const stringEnum = (allowed: string[], label: string) =>
  z.string().refine(
    (v) => allowed.includes(v.toLowerCase()),
    { message: `${label} must be one of: ${allowed.join(', ')}` },
  )

// ---------------------------------------------------------------------------
// Schema
// ---------------------------------------------------------------------------

export const liveviewSettingsSchema = z.object({
  // Boolean controls
  focus_peaking_enabled: booleanish.optional(),
  awb_enable: booleanish.optional(),
  ae_enable: booleanish.optional(),
  lens_shading_enable: booleanish.optional(),
  defect_correction_enable: booleanish.optional(),
  use_custom_tuning: booleanish.optional(),

  // Integer enum controls
  af_mode: intEnum([0, 1, 2], 'AF mode').optional(),
  af_speed: intEnum([0, 1], 'AF speed').optional(),
  af_range: intEnum([0, 1, 2], 'AF range').optional(),
  awb_mode: intEnum([0, 1, 2, 3, 4, 5, 6, 7], 'AWB mode').optional(),
  noise_reduction_mode: intEnum([0, 1, 2], 'Noise reduction mode').optional(),
  ae_metering_mode: intEnum([0, 1, 2], 'AE metering mode').optional(),

  // Float range controls
  sharpness: floatRange(0.0, 4.0, 'Sharpness').optional(),
  brightness: floatRange(-1.0, 1.0, 'Brightness').optional(),
  contrast: floatRange(0.0, 4.0, 'Contrast').optional(),
  saturation: floatRange(0.0, 4.0, 'Saturation').optional(),
  lens_position: floatRange(0.0, 10.0, 'Lens position').optional(),
  exposure_value: floatRange(-8.0, 8.0, 'Exposure value').optional(),
  analogue_gain: floatRange(1.0, 16.0, 'Analogue gain').optional(),
  colour_gains_red: floatRange(1.0, 4.0, 'Red colour gain').optional(),
  colour_gains_blue: floatRange(1.0, 4.0, 'Blue colour gain').optional(),

  // Integer range controls
  exposure_time: intRange(0, 999999, 'Exposure time', { minExclusive: true }).optional(),
  focus_peaking_intensity: intRange(50, 200, 'Focus peaking intensity').optional(),

  // String enum controls
  focus_peaking_colour: stringEnum(['green', 'red', 'yellow', 'cyan', 'magenta'], 'Focus peaking colour').optional(),
  focus_peaking_color: stringEnum(['green', 'red', 'yellow', 'cyan', 'magenta'], 'Focus peaking color').optional(),
  focus_peaking_algorithm: stringEnum(['laplacian', 'sobel', 'canny'], 'Focus peaking algorithm').optional(),
}).passthrough()

export type LiveviewSettingsData = z.infer<typeof liveviewSettingsSchema>

// ---------------------------------------------------------------------------
// Compatibility wrappers — drop-in replacements for presetValidation.ts API
// ---------------------------------------------------------------------------

export interface LiveviewValidationError {
  key: string
  value: unknown
  message: string
}

/**
 * Validate a settings object. Converts camelCase keys to snake_case before
 * checking. Returns an array of per-field errors (empty if valid).
 *
 * Drop-in replacement for `validatePresetSettings` from presetValidation.ts.
 */
export function validateLiveviewSettings(
  settings: Record<string, unknown>,
): LiveviewValidationError[] {
  // Convert camelCase keys to snake_case
  const converted: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(settings)) {
    converted[toBackendKey(key)] = value
  }

  const result = liveviewSettingsSchema.safeParse(converted)
  if (result.success) return []

  return result.error.issues.map((issue) => ({
    key: String(issue.path[0] ?? ''),
    value: converted[String(issue.path[0] ?? '')] ?? null,
    message: issue.message,
  }))
}

/**
 * Format validation errors into a user-friendly message.
 *
 * Drop-in replacement for `formatValidationErrors` from presetValidation.ts.
 */
export function formatLiveviewValidationErrors(
  errors: LiveviewValidationError[],
  maxErrors = 5,
): string {
  if (errors.length === 0) return ''

  const count = errors.length
  const shown = errors.slice(0, maxErrors)

  let msg = `Invalid preset settings (${count} error${count > 1 ? 's' : ''}):\n\n`
  shown.forEach((e, i) => {
    msg += `${i + 1}. ${e.key} = ${e.value}\n   ${e.message}\n`
  })

  if (count > maxErrors) {
    msg += `\n... and ${count - maxErrors} more error${count - maxErrors > 1 ? 's' : ''}`
  }

  return msg.trim()
}
```

**Step 4: Run test to verify it passes**

Run: `cd webui/frontend && npx vitest run src/schemas/__tests__/liveview-settings.test.ts --reporter=verbose 2>&1 | tail -20`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add -A
git commit -m "feat(#457): add liveview-settings Zod schema

Replaces the imperative validators in utils/presetValidation.ts with a
Zod schema that mirrors backend ALLOWED_LIVEVIEW_SETTINGS. Provides
drop-in wrapper functions (validateLiveviewSettings,
formatLiveviewValidationErrors) for consumer migration."
```

---

## Task 3: Migrate presetValidation consumers and delete (#457)

**Files:**
- Modify: `webui/frontend/src/pages/Camera.jsx:10,1147-1150,1204-1210`
- Modify: `webui/frontend/src/pages/Settings.jsx:11,540-543,571-575`
- Modify: `webui/frontend/src/components/SavePresetModal.tsx:8,33,59`
- Modify: `webui/frontend/src/components/__tests__/SavePresetModal.test.tsx:6`
- Modify: `webui/frontend/src/schemas/index.ts` (add re-export)
- Delete: `webui/frontend/src/utils/presetValidation.ts`
- Delete: `webui/frontend/src/utils/__tests__/presetValidation.test.ts`

**Step 1: Update Camera.jsx**

Change line 10 from:
```javascript
import { validatePresetSettings, formatValidationErrors } from '../utils/presetValidation'
```
to:
```javascript
import { validateLiveviewSettings, formatLiveviewValidationErrors } from '../schemas/liveview-settings'
```

Then find-and-replace in the file:
- `validatePresetSettings(` → `validateLiveviewSettings(`
- `formatValidationErrors(` → `formatLiveviewValidationErrors(`

There are 2 call sites for each (lines ~1147 and ~1205).

**Step 2: Update Settings.jsx**

Change line 11 from:
```javascript
import { validatePresetSettings, formatValidationErrors } from '../utils/presetValidation'
```
to:
```javascript
import { validateLiveviewSettings, formatLiveviewValidationErrors } from '../schemas/liveview-settings'
```

Then find-and-replace:
- `validatePresetSettings(` → `validateLiveviewSettings(`  (2 call sites: ~540, ~571)
- `formatValidationErrors(` → `formatLiveviewValidationErrors(`  (2 call sites: ~542, ~573)

Also update the comment on line ~1204 (Camera.jsx) that references `presetValidation.js`:
```javascript
// Both use validateLiveviewSettings() from schemas/liveview-settings.ts for consistency.
```

**Step 3: Update SavePresetModal.tsx**

Change line 8 from:
```typescript
import { validatePresetSettings, type SettingsValidationError } from '../utils/presetValidation'
```
to:
```typescript
import { validateLiveviewSettings, type LiveviewValidationError } from '../schemas/liveview-settings'
```

Change line 33 from:
```typescript
const [settingsErrors, setSettingsErrors] = useState<SettingsValidationError[]>([])
```
to:
```typescript
const [settingsErrors, setSettingsErrors] = useState<LiveviewValidationError[]>([])
```

Change line 59 from:
```typescript
const settingsValidationErrors = validatePresetSettings(currentSettings)
```
to:
```typescript
const settingsValidationErrors = validateLiveviewSettings(currentSettings)
```

**Step 4: Update SavePresetModal.test.tsx**

Change line 6 from:
```typescript
import { validatePresetSettings } from '../../utils/presetValidation'
```
to:
```typescript
import { validateLiveviewSettings } from '../../schemas/liveview-settings'
```

Update all references to `validatePresetSettings` in the test file to `validateLiveviewSettings`.

**Step 5: Add re-export to schemas/index.ts**

Add after line 20 (after the coordinates export):
```typescript
export { liveviewSettingsSchema, validateLiveviewSettings, formatLiveviewValidationErrors } from './liveview-settings'
export type { LiveviewSettingsData, LiveviewValidationError } from './liveview-settings'
```

**Step 6: Delete deprecated files**

```bash
cd webui/frontend
rm src/utils/presetValidation.ts
rm src/utils/__tests__/presetValidation.test.ts
```

**Step 7: Run tests**

Run: `cd webui/frontend && npx vitest run --reporter=verbose 2>&1 | tail -30`
Expected: All tests pass. No imports of `presetValidation` remain.

**Step 8: Verify no remaining references**

Run: `cd webui/frontend && grep -r "presetValidation" src/ --include="*.{js,jsx,ts,tsx}"`
Expected: No output

**Step 9: Commit**

```bash
git add -A
git commit -m "fix(#457): migrate consumers and delete presetValidation.ts

Replaced all 4 import sites (Camera.jsx, Settings.jsx, SavePresetModal.tsx,
SavePresetModal.test.tsx) with the new liveview-settings Zod schema.
Deleted the deprecated presetValidation.ts and its tests."
```

---

## Task 4: Create coordinateFormat utility (#458)

**Files:**
- Create: `webui/frontend/src/utils/coordinateFormat.ts`
- Create: `webui/frontend/src/utils/__tests__/coordinateFormat.test.ts`

The existing `gpsCoordinates.ts` mixes validation (replaced by `schemas/coordinates.ts`) with formatting/conversion utilities. Only `formatCoordinateDisplay` is still imported by consumers. We extract it (and its dependency `decimalToDMS`) into a new focused module.

**Step 1: Write the failing test**

Create `webui/frontend/src/utils/__tests__/coordinateFormat.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { formatCoordinateDisplay, decimalToDMS } from '../coordinateFormat'

describe('decimalToDMS', () => {
  it('converts positive latitude', () => {
    const result = decimalToDMS(37.7749, true)
    expect(result.degrees).toBe(37)
    expect(result.minutes).toBe(46)
    expect(result.reference).toBe('N')
  })

  it('converts negative longitude', () => {
    const result = decimalToDMS(-122.4194, false)
    expect(result.degrees).toBe(122)
    expect(result.reference).toBe('W')
  })

  it('respects secondsPrecision', () => {
    const result = decimalToDMS(37.7749, true, 4)
    expect(result.seconds.toFixed(4)).toBe('29.6400')
  })

  it('throws for NaN', () => {
    expect(() => decimalToDMS(NaN, true)).toThrow('NaN')
  })

  it('throws for out-of-range latitude', () => {
    expect(() => decimalToDMS(91, true)).toThrow('Invalid latitude')
  })
})

describe('formatCoordinateDisplay', () => {
  it('formats DMS (default)', () => {
    const result = formatCoordinateDisplay(37.7749, true)
    expect(result).toMatch(/37°46'.*"N/)
  })

  it('formats decimal', () => {
    const result = formatCoordinateDisplay(37.7749, true, 'decimal')
    expect(result).toContain('°N')
    expect(result).toMatch(/37\.774900/)
  })

  it('formats short', () => {
    const result = formatCoordinateDisplay(37.7749, true, 'short')
    expect(result).toBe('37.77°N')
  })

  it('throws for invalid format', () => {
    // @ts-expect-error testing invalid input
    expect(() => formatCoordinateDisplay(37.7749, true, 'invalid')).toThrow('Invalid format')
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd webui/frontend && npx vitest run src/utils/__tests__/coordinateFormat.test.ts --reporter=verbose 2>&1 | tail -10`
Expected: FAIL — module `../coordinateFormat` not found

**Step 3: Write the coordinateFormat utility**

Create `webui/frontend/src/utils/coordinateFormat.ts`:

```typescript
/**
 * GPS coordinate formatting and conversion utilities.
 *
 * Pure display utilities extracted from the deprecated gpsCoordinates.ts.
 * For validation, use schemas/coordinates.ts (Zod schema).
 */

export interface DMSCoordinate {
  degrees: number
  minutes: number
  seconds: number
  reference: 'N' | 'S' | 'E' | 'W'
}

export type CoordinateFormat = 'dms' | 'decimal' | 'short'

/**
 * Convert decimal degrees to DMS (Degrees, Minutes, Seconds) format.
 */
export function decimalToDMS(
  decimal: number,
  isLatitude: boolean,
  secondsPrecision: number = 2,
): DMSCoordinate {
  if (!Number.isInteger(secondsPrecision) || secondsPrecision < 0 || secondsPrecision > 6) {
    throw new Error(`Invalid secondsPrecision: ${secondsPrecision} (must be integer in range [0, 6])`)
  }
  if (decimal === null || decimal === undefined) {
    throw new Error('Coordinate cannot be null or undefined')
  }
  if (Number.isNaN(decimal)) {
    throw new Error('Coordinate cannot be NaN')
  }
  if (!Number.isFinite(decimal)) {
    throw new Error('Coordinate cannot be infinity')
  }
  if (isLatitude && (decimal < -90 || decimal > 90)) {
    throw new Error(`Invalid latitude: ${decimal} (must be in range [-90, 90])`)
  }
  if (!isLatitude && (decimal < -180 || decimal > 180)) {
    throw new Error(`Invalid longitude: ${decimal} (must be in range [-180, 180])`)
  }

  const reference: 'N' | 'S' | 'E' | 'W' = isLatitude
    ? (decimal >= 0 ? 'N' : 'S')
    : (decimal >= 0 ? 'E' : 'W')

  const decimalAbs = Math.abs(decimal)
  let degrees = Math.floor(decimalAbs)
  const minutesDecimal = (decimalAbs - degrees) * 60
  let minutes = Math.floor(minutesDecimal)
  const multiplier = Math.pow(10, secondsPrecision)
  let seconds = Math.round((minutesDecimal - minutes) * 60 * multiplier) / multiplier

  if (seconds >= 60.0) {
    minutes += 1
    seconds = 0.0
  }
  if (minutes >= 60) {
    degrees += 1
    minutes = 0
  }

  return { degrees, minutes, seconds, reference }
}

/**
 * Format a coordinate for display.
 *
 * @param decimal - Decimal degrees
 * @param isLatitude - True if latitude, false if longitude
 * @param format - 'dms' (37°46'29.64"N), 'decimal' (37.774900°N), or 'short' (37.77°N)
 * @param secondsPrecision - Decimal places for seconds in DMS format (0-6, default 2)
 */
export function formatCoordinateDisplay(
  decimal: number,
  isLatitude: boolean,
  format: CoordinateFormat = 'dms',
  secondsPrecision: number = 2,
): string {
  if (format === 'dms') {
    const { degrees, minutes, seconds, reference } = decimalToDMS(decimal, isLatitude, secondsPrecision)
    return `${degrees}°${minutes}'${seconds.toFixed(secondsPrecision)}"${reference}`
  } else if (format === 'decimal') {
    const reference = isLatitude ? (decimal >= 0 ? 'N' : 'S') : (decimal >= 0 ? 'E' : 'W')
    return `${Math.abs(decimal).toFixed(6)}°${reference}`
  } else if (format === 'short') {
    const reference = isLatitude ? (decimal >= 0 ? 'N' : 'S') : (decimal >= 0 ? 'E' : 'W')
    return `${Math.abs(decimal).toFixed(2)}°${reference}`
  } else {
    throw new Error(`Invalid format: ${format} (must be 'dms', 'decimal', or 'short')`)
  }
}
```

**Step 4: Run test to verify it passes**

Run: `cd webui/frontend && npx vitest run src/utils/__tests__/coordinateFormat.test.ts --reporter=verbose 2>&1 | tail -20`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add -A
git commit -m "feat(#458): add coordinateFormat.ts display utility

Extracts formatCoordinateDisplay and decimalToDMS from the deprecated
gpsCoordinates.ts into a focused display-only module."
```

---

## Task 5: Migrate gpsCoordinates consumers and delete (#458)

**Files:**
- Modify: `webui/frontend/src/components/GPSSettings.tsx:6`
- Modify: `webui/frontend/src/components/PhotoLightbox.jsx:13`
- Modify: `webui/frontend/src/components/export/CoordinateInput.tsx:5`
- Delete: `webui/frontend/src/utils/gpsCoordinates.ts`
- Delete: `webui/frontend/src/utils/__tests__/gpsCoordinates.test.ts`

**Step 1: Update GPSSettings.tsx**

Change line 6 from:
```typescript
import { formatCoordinateDisplay } from '../utils/gpsCoordinates'
```
to:
```typescript
import { formatCoordinateDisplay } from '../utils/coordinateFormat'
```

**Step 2: Update PhotoLightbox.jsx**

Change line 13 from:
```javascript
import { formatCoordinateDisplay } from '../utils/gpsCoordinates'
```
to:
```javascript
import { formatCoordinateDisplay } from '../utils/coordinateFormat'
```

**Step 3: Update CoordinateInput.tsx**

Change line 5 from:
```typescript
import { formatCoordinateDisplay } from '../../utils/gpsCoordinates'
```
to:
```typescript
import { formatCoordinateDisplay } from '../../utils/coordinateFormat'
```

**Step 4: Delete deprecated files**

```bash
cd webui/frontend
rm src/utils/gpsCoordinates.ts
rm src/utils/__tests__/gpsCoordinates.test.ts
```

**Step 5: Run tests**

Run: `cd webui/frontend && npx vitest run --reporter=verbose 2>&1 | tail -30`
Expected: All tests pass

**Step 6: Verify no remaining references**

Run: `cd webui/frontend && grep -r "gpsCoordinates" src/ --include="*.{js,jsx,ts,tsx}"`
Expected: No output

**Step 7: Commit**

```bash
git add -A
git commit -m "fix(#458): migrate consumers and delete gpsCoordinates.ts

Replaced all 3 import sites (GPSSettings.tsx, PhotoLightbox.jsx,
CoordinateInput.tsx) with the new utils/coordinateFormat.ts module.
Deleted the deprecated gpsCoordinates.ts and its tests."
```

---

## Task 6: Remove ESLint deprecation warnings and final verification

**Files:**
- Modify: `webui/frontend/eslint.config.js:68-80`

**Step 1: Remove the no-restricted-imports block**

Delete lines 68-80 of `eslint.config.js` (the entire block):
```javascript
  {
    // Deprecated validation utilities — warn on new imports (#197)
    files: ['**/*.{js,jsx,ts,tsx}'],
    rules: {
      'no-restricted-imports': ['warn', {
        patterns: [
          { group: ['**/utils/gpsValidation'], message: 'Deprecated: will be replaced by schemas/gps-settings.ts in Phase 1 (#197)' },
          { group: ['**/utils/presetValidation'], message: 'Deprecated: will be replaced by schemas/camera-preset.ts in Phase 1 (#197)' },
          { group: ['**/utils/gpsCoordinates'], message: 'Deprecated: will be replaced by schemas/coordinates.ts in Phase 1 (#197)' },
        ],
      }],
    },
  },
```

**Step 2: Run ESLint to verify no issues**

Run: `cd webui/frontend && npx eslint src/ 2>&1 | tail -10`
Expected: No errors related to deprecated imports

**Step 3: Run full test suite**

Run: `cd webui/frontend && npx vitest run --reporter=verbose 2>&1 | tail -30`
Expected: All tests pass

**Step 4: Run TypeScript type check**

Run: `cd webui/frontend && npx tsc --noEmit 2>&1 | tail -20`
Expected: No new errors (existing errors from untyped .jsx modules may remain)

**Step 5: Verify all three deprecated files are gone**

Run: `ls webui/frontend/src/utils/gpsValidation.js webui/frontend/src/utils/presetValidation.ts webui/frontend/src/utils/gpsCoordinates.ts 2>&1`
Expected: "No such file or directory" for all three

**Step 6: Commit**

```bash
git add -A
git commit -m "chore(#456,#457,#458): remove deprecated import lint rules

All three deprecated validation utilities have been deleted and their
consumers migrated. The ESLint no-restricted-imports rules are no longer
needed."
```

---

## Summary

| Task | Issue | Action | Files Changed |
|------|-------|--------|---------------|
| 1 | #456 | Delete orphaned gpsValidation.js | -2 files |
| 2 | #457 | Create liveview-settings Zod schema | +2 files |
| 3 | #457 | Migrate 4 consumers, delete presetValidation.ts | 5 modified, -2 deleted |
| 4 | #458 | Create coordinateFormat utility | +2 files |
| 5 | #458 | Migrate 3 consumers, delete gpsCoordinates.ts | 3 modified, -2 deleted |
| 6 | All | Remove ESLint deprecation rules, verify | 1 modified |

**Net result:** 3 deprecated files deleted, 2 focused replacements created, 7 consumer files updated, 1 ESLint config cleaned up.

# Integrate Zod Schemas with Centralized errorMessages Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace all inline error strings in Zod schemas with imports from a single centralized `errorMessages.ts`, then delete the legacy `errorMessages.js`.

**Architecture:** Create `src/constants/errorMessages.ts` with generic message concepts (REQUIRED, RANGE, LENGTH, TYPE, FORMAT) and domain-specific groups (GPS, DEPLOYMENT, COORDINATES, etc.). Update all 17 schema files with inline strings to import from it. Migrate the one legacy consumer, then delete the old file.

**Tech Stack:** TypeScript, Zod 4, Vitest

**Key insight:** `liveview-settings.ts` uses parameterized helper functions (`intEnum`, `floatRange`, `intRange`, `stringEnum`) that are already DRY within that file. These helpers generate messages with field-specific labels passed at call sites. Centralizing the template patterns (e.g., `${label} must be a number`) would require passing labels through an extra layer for zero benefit. **Leave `liveview-settings.ts` as-is.**

---

### Task 1: Create errorMessages.ts with generic concepts

**Files:**
- Create: `webui/frontend/src/constants/errorMessages.ts`
- Test: `webui/frontend/src/constants/__tests__/errorMessages.test.ts`

**Step 1: Write the test file**

```typescript
// webui/frontend/src/constants/__tests__/errorMessages.test.ts
import { describe, it, expect } from 'vitest'
import {
  REQUIRED,
  RANGE,
  LENGTH,
  TYPE,
  FORMAT,
  COORDINATES,
  GPS,
  DEPLOYMENT,
  SCHEDULER,
  CRON,
  PRESET,
  TAG,
  SPECIES,
  METADATA,
  NETWORK,
  VALIDATION,
} from '../errorMessages'

describe('errorMessages', () => {
  describe('REQUIRED', () => {
    it('generates field-required message', () => {
      expect(REQUIRED.field('Device path')).toBe('Device path is required')
    })

    it('generates selection-required message', () => {
      expect(REQUIRED.selection('Moon phase')).toBe('Moon phase must be selected')
    })
  })

  describe('RANGE', () => {
    it('generates min message without unit', () => {
      expect(RANGE.min(5)).toBe('Must be at least 5')
    })

    it('generates min message with unit', () => {
      expect(RANGE.min(1, 'minute')).toBe('Must be at least 1 minute')
    })

    it('generates max message without unit', () => {
      expect(RANGE.max(100)).toBe('Cannot exceed 100')
    })

    it('generates max message with unit', () => {
      expect(RANGE.max(10080, 'minutes')).toBe('Cannot exceed 10080 minutes')
    })

    it('generates between message without unit', () => {
      expect(RANGE.between(-90, 90)).toBe('Must be between -90 and 90')
    })

    it('generates between message with unit', () => {
      expect(RANGE.between(1, 60, 'minutes')).toBe('Must be between 1 and 60 minutes')
    })
  })

  describe('LENGTH', () => {
    it('generates min-length message', () => {
      expect(LENGTH.min(3)).toBe('Must be at least 3 characters')
    })

    it('generates max-length message', () => {
      expect(LENGTH.max(200)).toBe('Must be 200 characters or less')
    })
  })

  describe('TYPE', () => {
    it('generates number message with label', () => {
      expect(TYPE.number('Interval')).toBe('Interval must be a number')
    })

    it('generates number message without label', () => {
      expect(TYPE.number()).toBe('Value must be a number')
    })

    it('generates integer message with label', () => {
      expect(TYPE.integer('Offset')).toBe('Offset must be a whole number')
    })

    it('generates integer message without label', () => {
      expect(TYPE.integer()).toBe('Value must be a whole number')
    })

    it('generates string message with label', () => {
      expect(TYPE.string('Cron expression')).toBe('Cron expression must be a string')
    })
  })

  describe('FORMAT', () => {
    it('has time format message', () => {
      expect(FORMAT.time).toBe('Must be in HH:MM format')
    })

    it('has valid time format message', () => {
      expect(FORMAT.validTime).toBe('Must be a valid time in HH:MM format')
    })

    it('has time or solar message', () => {
      expect(FORMAT.timeOrSolar).toBe('Must be valid HH:MM time or solar event')
    })

    it('has url format message', () => {
      expect(FORMAT.url).toBe('Please enter a valid URL (e.g., https://example.com)')
    })
  })

  describe('COORDINATES', () => {
    it('has latitude message', () => {
      expect(COORDINATES.latitude).toBe('Latitude must be between -90 and 90')
    })

    it('has longitude message', () => {
      expect(COORDINATES.longitude).toBe('Longitude must be between -180 and 180')
    })
  })

  describe('GPS', () => {
    it('has invalid path message', () => {
      expect(GPS.invalidPath).toBe(
        'Invalid device path format. Expected /dev/ttyAMA0, /dev/ttyUSB0, etc.',
      )
    })

    it('has invalid baudrate message', () => {
      expect(GPS.invalidBaudrate).toBe('Invalid baudrate')
    })
  })

  describe('DEPLOYMENT', () => {
    it('has end-before-start message', () => {
      expect(DEPLOYMENT.endBeforeStart).toBe('End date must be on or after start date')
    })

    it('generates max custom fields message', () => {
      expect(DEPLOYMENT.maxCustomFields(50)).toBe('Maximum 50 custom fields')
    })
  })

  describe('SCHEDULER', () => {
    it('has same-start-end message', () => {
      expect(SCHEDULER.sameStartEnd).toBe('Start and end times cannot be the same')
    })

    it('has invalid solar event message', () => {
      expect(SCHEDULER.invalidSolarEvent).toBe('Invalid solar event')
    })

    it('has invalid moon phase message', () => {
      expect(SCHEDULER.invalidMoonPhase).toBe('Invalid moon phase')
    })

    it('has invalid sensor type message', () => {
      expect(SCHEDULER.invalidSensorType).toBe('Invalid sensor type')
    })

    it('has invalid comparison message', () => {
      expect(SCHEDULER.invalidComparison).toBe('Invalid comparison operator')
    })
  })

  describe('CRON', () => {
    it('has format message', () => {
      expect(CRON.format).toBe('Must be 5 space-separated cron fields')
    })
  })

  describe('PRESET', () => {
    it('has alphanumeric-only message', () => {
      expect(PRESET.alphanumericOnly).toBe(
        'Name can only contain letters, numbers, and underscores',
      )
    })
  })

  describe('TAG', () => {
    it('has empty message', () => {
      expect(TAG.empty).toBe('Tag cannot be empty')
    })

    it('has too long message', () => {
      expect(TAG.tooLong).toBe('Tag is too long')
    })

    it('has min required message', () => {
      expect(TAG.minRequired).toBe('At least one tag is required')
    })

    it('has too many message', () => {
      expect(TAG.tooMany).toBe('Too many tags')
    })
  })

  describe('SPECIES', () => {
    it('has species too long message', () => {
      expect(SPECIES.nameTooLong).toBe('Species name is too long')
    })

    it('has common name too long message', () => {
      expect(SPECIES.commonNameTooLong).toBe('Common name is too long')
    })

    it('has url too long message', () => {
      expect(SPECIES.urlTooLong).toBe('URL is too long')
    })
  })

  describe('METADATA', () => {
    it('generates duplicate key message', () => {
      expect(METADATA.duplicateKey('myField')).toBe('Duplicate key: "myField"')
    })
  })

  describe('NETWORK', () => {
    it('has network error message', () => {
      expect(NETWORK.connectionError).toBe('Unable to save. Please check your connection.')
    })

    it('has server error message', () => {
      expect(NETWORK.serverError).toBe('Server error. Please try again later.')
    })

    it('has timeout message', () => {
      expect(NETWORK.timeout).toBe('Request timed out. Please try again.')
    })
  })

  describe('VALIDATION', () => {
    it('has general message', () => {
      expect(VALIDATION.general).toBe('Please fix the errors above.')
    })

    it('has required field message', () => {
      expect(VALIDATION.requiredField).toBe('This field is required.')
    })
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd webui/frontend && npx vitest run src/constants/__tests__/errorMessages.test.ts`
Expected: FAIL — module not found

**Step 3: Write the implementation**

```typescript
// webui/frontend/src/constants/errorMessages.ts

// ---------------------------------------------------------------------------
// Generic messages (by concept)
// ---------------------------------------------------------------------------

/** Required field/selection messages. */
export const REQUIRED = {
  field: (name: string) => `${name} is required`,
  selection: (name: string) => `${name} must be selected`,
} as const

/** Numeric range validation messages. */
export const RANGE = {
  min: (val: number, unit?: string) =>
    `Must be at least ${val}${unit ? ` ${unit}` : ''}`,
  max: (val: number, unit?: string) =>
    `Cannot exceed ${val}${unit ? ` ${unit}` : ''}`,
  between: (min: number, max: number, unit?: string) =>
    `Must be between ${min} and ${max}${unit ? ` ${unit}` : ''}`,
} as const

/** String length validation messages. */
export const LENGTH = {
  min: (val: number) => `Must be at least ${val} characters`,
  max: (val: number) => `Must be ${val} characters or less`,
} as const

/** Type constraint messages. */
export const TYPE = {
  number: (label?: string) => `${label ?? 'Value'} must be a number`,
  integer: (label?: string) => `${label ?? 'Value'} must be a whole number`,
  string: (label?: string) => `${label ?? 'Value'} must be a string`,
} as const

/** Format pattern messages. */
export const FORMAT = {
  time: 'Must be in HH:MM format',
  validTime: 'Must be a valid time in HH:MM format',
  timeOrSolar: 'Must be valid HH:MM time or solar event',
  url: 'Please enter a valid URL (e.g., https://example.com)',
} as const

// ---------------------------------------------------------------------------
// Domain-specific messages
// ---------------------------------------------------------------------------

/** Coordinate validation messages. */
export const COORDINATES = {
  latitude: 'Latitude must be between -90 and 90',
  longitude: 'Longitude must be between -180 and 180',
} as const

/** GPS settings messages. */
export const GPS = {
  invalidPath:
    'Invalid device path format. Expected /dev/ttyAMA0, /dev/ttyUSB0, etc.',
  invalidBaudrate: 'Invalid baudrate',
} as const

/** Deployment form messages. */
export const DEPLOYMENT = {
  endBeforeStart: 'End date must be on or after start date',
  maxCustomFields: (max: number) => `Maximum ${max} custom fields`,
} as const

/** Scheduler-specific messages (triggers, pre-conditions). */
export const SCHEDULER = {
  sameStartEnd: 'Start and end times cannot be the same',
  invalidSolarEvent: 'Invalid solar event',
  invalidMoonPhase: 'Invalid moon phase',
  invalidSensorType: 'Invalid sensor type',
  invalidComparison: 'Invalid comparison operator',
} as const

/** Cron expression messages. */
export const CRON = {
  format: 'Must be 5 space-separated cron fields',
} as const

/** Preset name messages. */
export const PRESET = {
  alphanumericOnly: 'Name can only contain letters, numbers, and underscores',
} as const

/** Tag validation messages. */
export const TAG = {
  empty: 'Tag cannot be empty',
  tooLong: 'Tag is too long',
  minRequired: 'At least one tag is required',
  tooMany: 'Too many tags',
} as const

/** Species form messages. */
export const SPECIES = {
  nameTooLong: 'Species name is too long',
  commonNameTooLong: 'Common name is too long',
  urlTooLong: 'URL is too long',
} as const

/** Metadata form messages. */
export const METADATA = {
  duplicateKey: (key: string) => `Duplicate key: "${key}"`,
} as const

/** Network/server communication messages (from legacy errorMessages.js). */
export const NETWORK = {
  connectionError: 'Unable to save. Please check your connection.',
  serverError: 'Server error. Please try again later.',
  timeout: 'Request timed out. Please try again.',
} as const

/** General form validation messages (from legacy errorMessages.js). */
export const VALIDATION = {
  general: 'Please fix the errors above.',
  requiredField: 'This field is required.',
} as const
```

**Step 4: Run test to verify it passes**

Run: `cd webui/frontend && npx vitest run src/constants/__tests__/errorMessages.test.ts`
Expected: all PASS

**Step 5: Commit**

```bash
git add webui/frontend/src/constants/errorMessages.ts webui/frontend/src/constants/__tests__/errorMessages.test.ts
git commit -m "feat(#472): add centralized errorMessages.ts with generic and domain-specific messages"
```

---

### Task 2: Migrate coordinates.ts

**Files:**
- Modify: `webui/frontend/src/schemas/coordinates.ts`
- Test: `webui/frontend/src/schemas/__tests__/coordinates.test.ts` (has hardcoded strings)

**Step 1: Update the schema**

Replace the full contents of `webui/frontend/src/schemas/coordinates.ts`:

```typescript
import { z } from 'zod'
import { COORDINATES } from '../constants/errorMessages'

export const coordinatesSchema = z.object({
  latitude: z.number()
    .min(-90, COORDINATES.latitude)
    .max(90, COORDINATES.latitude)
    .nullable(),
  longitude: z.number()
    .min(-180, COORDINATES.longitude)
    .max(180, COORDINATES.longitude)
    .nullable(),
})

export type CoordinatesFormData = z.infer<typeof coordinatesSchema>
```

**Step 2: Update the test to import from errorMessages**

In `webui/frontend/src/schemas/__tests__/coordinates.test.ts`, add import and replace hardcoded strings:

```typescript
import { COORDINATES } from '../../constants/errorMessages'
```

Replace all `'Latitude must be between -90 and 90'` → `COORDINATES.latitude`
Replace all `'Longitude must be between -180 and 180'` → `COORDINATES.longitude`

**Step 3: Run tests**

Run: `cd webui/frontend && npx vitest run src/schemas/__tests__/coordinates.test.ts`
Expected: all PASS

**Step 4: Commit**

```bash
git add webui/frontend/src/schemas/coordinates.ts webui/frontend/src/schemas/__tests__/coordinates.test.ts
git commit -m "refactor(#472): migrate coordinates.ts to centralized errorMessages"
```

---

### Task 3: Migrate tag.ts

**Files:**
- Modify: `webui/frontend/src/schemas/tag.ts`
- Test: `webui/frontend/src/schemas/__tests__/tag.test.ts` (has hardcoded strings)

**Step 1: Update the schema**

Replace inline strings in `webui/frontend/src/schemas/tag.ts`:

```typescript
import { z } from 'zod';
import { TAG } from '../constants/errorMessages';

export const TAG_MODES = ['add', 'replace', 'remove'] as const;
export const TAG_MAX_LENGTH = 100;
export const TAG_MAX_COUNT = 50;

export const bulkTagSchema = z.object({
  tags: z.array(
    z.object({ value: z.string().trim().min(1, TAG.empty).max(TAG_MAX_LENGTH, TAG.tooLong) })
  ).min(1, TAG.minRequired).max(TAG_MAX_COUNT, TAG.tooMany),
  mode: z.enum(TAG_MODES),
});

export type BulkTagFormData = z.infer<typeof bulkTagSchema>;
```

**Step 2: Update the test to import from errorMessages**

In `webui/frontend/src/schemas/__tests__/tag.test.ts`, add import and replace strings:

```typescript
import { TAG } from '../../constants/errorMessages'
```

Replace: `'Tag cannot be empty'` → `TAG.empty`, `'Tag is too long'` → `TAG.tooLong`, `'At least one tag is required'` → `TAG.minRequired`, `'Too many tags'` → `TAG.tooMany`

**Step 3: Run tests**

Run: `cd webui/frontend && npx vitest run src/schemas/__tests__/tag.test.ts`
Expected: all PASS

**Step 4: Commit**

```bash
git add webui/frontend/src/schemas/tag.ts webui/frontend/src/schemas/__tests__/tag.test.ts
git commit -m "refactor(#472): migrate tag.ts to centralized errorMessages"
```

---

### Task 4: Migrate species.ts

**Files:**
- Modify: `webui/frontend/src/schemas/species.ts`
- Test: `webui/frontend/src/schemas/__tests__/species.test.ts` (has hardcoded strings)

**Step 1: Update the schema**

In `webui/frontend/src/schemas/species.ts`, add import and replace inline strings:

```typescript
import { z } from 'zod'
import { METADATA_VALIDATION } from '../constants/config'
import { SPECIES, FORMAT } from '../constants/errorMessages'

export const CONFIDENCE_VALUES = ['certain', 'probable', 'possible', 'unknown'] as const

export const speciesSchema = z.object({
  species: z.string().trim().max(METADATA_VALIDATION.MAX_SPECIES_LENGTH, SPECIES.nameTooLong).optional().or(z.literal('')),
  commonName: z.string().trim().max(METADATA_VALIDATION.MAX_COMMON_NAME_LENGTH, SPECIES.commonNameTooLong).optional().or(z.literal('')),
  confidence: z.enum(CONFIDENCE_VALUES),
  referenceUrl: z.string()
    .max(METADATA_VALIDATION.MAX_REFERENCE_URL_LENGTH, SPECIES.urlTooLong)
    .refine((val) => {
      if (!val) return true
      try {
        const parsed = new URL(val)
        return parsed.protocol === 'http:' || parsed.protocol === 'https:'
      } catch {
        return false
      }
    }, { message: FORMAT.url })
    .optional()
    .or(z.literal('')),
})

export type SpeciesFormData = z.infer<typeof speciesSchema>
```

**Step 2: Update the test**

In `webui/frontend/src/schemas/__tests__/species.test.ts`, add import and replace:

```typescript
import { SPECIES, FORMAT } from '../../constants/errorMessages'
```

Replace: `'Species name is too long'` → `SPECIES.nameTooLong`, `'Common name is too long'` → `SPECIES.commonNameTooLong`, `'URL is too long'` → `SPECIES.urlTooLong`, `'Please enter a valid URL (e.g., https://example.com)'` → `FORMAT.url`

**Step 3: Run tests**

Run: `cd webui/frontend && npx vitest run src/schemas/__tests__/species.test.ts`
Expected: all PASS

**Step 4: Commit**

```bash
git add webui/frontend/src/schemas/species.ts webui/frontend/src/schemas/__tests__/species.test.ts
git commit -m "refactor(#472): migrate species.ts to centralized errorMessages"
```

---

### Task 5: Migrate preset.ts and camera-preset.ts

**Files:**
- Modify: `webui/frontend/src/schemas/preset.ts`
- Modify: `webui/frontend/src/schemas/camera-preset.ts`
- Test: `webui/frontend/src/schemas/__tests__/preset.test.ts` (has hardcoded strings)
- Test: `webui/frontend/src/schemas/__tests__/camera-preset.test.ts` (has hardcoded strings)

**Step 1: Update preset.ts**

```typescript
import { z } from 'zod';
import { REQUIRED, LENGTH, PRESET } from '../constants/errorMessages';

export const filterPresetNameSchema = z.object({
  name: z.string()
    .trim()
    .min(1, REQUIRED.field('Preset name'))
    .min(3, LENGTH.min(3))
    .max(50, LENGTH.max(50)),
});

export type FilterPresetNameData = z.infer<typeof filterPresetNameSchema>;

export const cameraPresetNameSchema = z.object({
  name: z.string()
    .trim()
    .min(1, REQUIRED.field('Preset name'))
    .min(3, LENGTH.min(3))
    .regex(/^[a-zA-Z0-9_]+$/, PRESET.alphanumericOnly)
    .max(50, LENGTH.max(50)),
});

export type CameraPresetNameData = z.infer<typeof cameraPresetNameSchema>;
```

**Step 2: Update camera-preset.ts**

```typescript
import { z } from 'zod'
import { cameraPresetNameSchema } from './preset'
import { LENGTH } from '../constants/errorMessages'

export const WORKFLOW_VALUES = ['photo', 'liveview', 'both'] as const

export const cameraPresetFormSchema = cameraPresetNameSchema.extend({
  description: z.string().max(200, LENGTH.max(200)),
  workflow: z.enum(WORKFLOW_VALUES),
})

export type CameraPresetFormData = z.infer<typeof cameraPresetFormSchema>
```

**Step 3: Update tests**

In `preset.test.ts` and `camera-preset.test.ts`, add imports and replace hardcoded strings:

```typescript
import { REQUIRED, LENGTH, PRESET } from '../../constants/errorMessages'
```

Replace: `'Preset name is required'` → `REQUIRED.field('Preset name')`, `'Name must be at least 3 characters'` → `LENGTH.min(3)`, `'Name must be 50 characters or less'` → `LENGTH.max(50)`, `'Name can only contain letters, numbers, and underscores'` → `PRESET.alphanumericOnly`, `'Description must be 200 characters or less'` → `LENGTH.max(200)`

**Step 4: Run tests**

Run: `cd webui/frontend && npx vitest run src/schemas/__tests__/preset.test.ts src/schemas/__tests__/camera-preset.test.ts`
Expected: all PASS

**Step 5: Commit**

```bash
git add webui/frontend/src/schemas/preset.ts webui/frontend/src/schemas/camera-preset.ts webui/frontend/src/schemas/__tests__/preset.test.ts webui/frontend/src/schemas/__tests__/camera-preset.test.ts
git commit -m "refactor(#472): migrate preset.ts and camera-preset.ts to centralized errorMessages"
```

---

### Task 6: Migrate deployment.ts

**Files:**
- Modify: `webui/frontend/src/schemas/deployment.ts`
- Test: `webui/frontend/src/schemas/__tests__/deployment.test.ts` (no hardcoded strings — only success/fail assertions)

**Step 1: Update the schema**

```typescript
import { z } from 'zod'
import { REQUIRED, LENGTH, COORDINATES, DEPLOYMENT as DEPLOYMENT_MSGS } from '../constants/errorMessages'

const optionalStr = (max?: number) => {
  const base = z.string()
  return (max ? base.max(max, LENGTH.max(max)) : base).optional().or(z.literal(''))
}

export const deploymentFieldEntrySchema = z.object({
  key: z.string(),
  value: z.string(),
})

export const deploymentSchema = z.object({
  deployment_name: z.string()
    .min(1, REQUIRED.field('Deployment name'))
    .max(200, LENGTH.max(200)),
  location_name: optionalStr(500),
  latitude: z.number().min(-90, COORDINATES.latitude).max(90, COORDINATES.latitude).nullable(),
  longitude: z.number().min(-180, COORDINATES.longitude).max(180, COORDINATES.longitude).nullable(),
  altitude: z.preprocess(
    (v) => (v === '' || v === null || v === undefined) ? null : v,
    z.coerce.number().nullable(),
  ),
  start_date: optionalStr(),
  end_date: optionalStr(),
  environmental: z.array(deploymentFieldEntrySchema),
  custom: z.array(deploymentFieldEntrySchema).max(50, DEPLOYMENT_MSGS.maxCustomFields(50)),
  mothbox_id: optionalStr(),
  firmware_version: optionalStr(),
}).refine(
  (d) => {
    if (!d.start_date || !d.end_date) return true
    return d.start_date <= d.end_date
  },
  { message: DEPLOYMENT_MSGS.endBeforeStart, path: ['end_date'] }
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

**Step 2: Run tests**

Run: `cd webui/frontend && npx vitest run src/schemas/__tests__/deployment.test.ts`
Expected: all PASS

**Step 3: Commit**

```bash
git add webui/frontend/src/schemas/deployment.ts
git commit -m "refactor(#472): migrate deployment.ts to centralized errorMessages"
```

---

### Task 7: Migrate gps-settings.ts

**Files:**
- Modify: `webui/frontend/src/schemas/gps-settings.ts`
- Test: `webui/frontend/src/schemas/__tests__/gps-settings.test.ts` (no hardcoded strings — only success/fail assertions)

**Step 1: Update the schema**

```typescript
import { z } from 'zod'
import { REQUIRED, RANGE, GPS } from '../constants/errorMessages'

export const BAUDRATE_VALUES = [4800, 9600, 19200, 38400, 57600, 115200] as const

const DEVICE_PATH_PATTERN = /^\/dev\/(ttyAMA\d+|ttyACM\d+|ttyS\d+|ttyUSB\d+|ttyO\d+|serial\d+)$/

export const gpsSettingsSchema = z.object({
  enabled: z.boolean(),
  device: z.string()
    .min(1, REQUIRED.field('Device path'))
    .regex(DEVICE_PATH_PATTERN, GPS.invalidPath),
  baudrate: z.coerce.number().refine(
    (v) => (BAUDRATE_VALUES as readonly number[]).includes(v),
    GPS.invalidBaudrate,
  ),
  timeout: z.coerce.number().min(1),
  timeout_hot: z.coerce.number().min(5, RANGE.min(5, 's')).max(60, RANGE.max(60, 's')),
  timeout_warm: z.coerce.number().min(30, RANGE.min(30, 's')).max(180, RANGE.max(180, 's')),
  timeout_cold: z.coerce.number().min(60, RANGE.min(60, 's')).max(300, RANGE.max(300, 's')),
  timeout_almanac: z.coerce.number().min(300, RANGE.min(300, 's')).max(1800, RANGE.max(1800, 's')),
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

**Note:** The GPS timeout messages change format slightly: `'Must be at least 5s'` → `'Must be at least 5 s'` (space before unit). Since no tests assert on these exact strings, this is safe. However, if strict preservation is required, add unit-specific messages to the GPS domain object instead. **Verify the test passes — if `RANGE.min(5, 's')` produces `'Must be at least 5 s'` but the original was `'Must be at least 5s'`, use `RANGE.min(5) + 's'` inline or add a GPS-specific timeout helper.**

**IMPORTANT:** Check the RANGE helper output. If `RANGE.min(5, 's')` → `"Must be at least 5 s"` (with space), but original was `"Must be at least 5s"` (no space), you must either:
- Option A: Use inline `\`Must be at least ${val}s\`` for GPS timeouts (keeping them as GPS-domain strings)
- Option B: Change RANGE to not add space when unit starts with a lowercase letter

**Recommended:** Since `'s'` is the only unit without a leading space, add GPS-specific timeout messages:

Add to `errorMessages.ts` GPS section:
```typescript
export const GPS = {
  invalidPath: 'Invalid device path format. Expected /dev/ttyAMA0, /dev/ttyUSB0, etc.',
  invalidBaudrate: 'Invalid baudrate',
  timeoutMin: (val: number) => `Must be at least ${val}s`,
  timeoutMax: (val: number) => `Cannot exceed ${val}s`,
} as const
```

Then use `GPS.timeoutMin(5)` and `GPS.timeoutMax(60)` instead of `RANGE.min/max`.

**Step 2: Run tests**

Run: `cd webui/frontend && npx vitest run src/schemas/__tests__/gps-settings.test.ts`
Expected: all PASS

**Step 3: Commit**

```bash
git add webui/frontend/src/schemas/gps-settings.ts webui/frontend/src/constants/errorMessages.ts
git commit -m "refactor(#472): migrate gps-settings.ts to centralized errorMessages"
```

---

### Task 8: Migrate metadata.ts

**Files:**
- Modify: `webui/frontend/src/schemas/metadata.ts`
- Test: `webui/frontend/src/schemas/__tests__/metadata.test.ts` (check for hardcoded strings)

**Step 1: Update the schema**

In `webui/frontend/src/schemas/metadata.ts`, add import and replace:

```typescript
import { z } from 'zod'
import { METADATA_VALIDATION } from '../constants/config'
import { speciesSchema } from './species'
import { REQUIRED, METADATA } from '../constants/errorMessages'

export const customFieldEntrySchema = z.object({
  key: z.string().min(1, REQUIRED.field('Field name')).max(100),
  value: z.string().max(1000),
})

export const metadataFormSchema = z.object({
  tags: z.array(z.string().trim().min(1).max(METADATA_VALIDATION.MAX_TAG_LENGTH)),
  ...speciesSchema.shape,
  notes: z.string().max(METADATA_VALIDATION.MAX_NOTES_LENGTH).optional().or(z.literal('')),
  custom: z.array(customFieldEntrySchema)
    .max(METADATA_VALIDATION.MAX_CUSTOM_FIELDS)
    .superRefine((entries, ctx) => {
      const seen = new Set<string>()
      entries.forEach((entry, i) => {
        if (seen.has(entry.key)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: METADATA.duplicateKey(entry.key),
            path: [i, 'key'],
          })
        }
        seen.add(entry.key)
      })
    }),
})

export type MetadataFormData = z.infer<typeof metadataFormSchema>
export type CustomFieldEntry = z.infer<typeof customFieldEntrySchema>
```

**Step 2: Run tests**

Run: `cd webui/frontend && npx vitest run src/schemas/__tests__/metadata.test.ts`
Expected: all PASS

**Step 3: Commit**

```bash
git add webui/frontend/src/schemas/metadata.ts
git commit -m "refactor(#472): migrate metadata.ts to centralized errorMessages"
```

---

### Task 9: Migrate scheduler schemas (interval, fixed-time, solar, cron)

**Files:**
- Modify: `webui/frontend/src/schemas/scheduler/interval.ts`
- Modify: `webui/frontend/src/schemas/scheduler/fixed-time.ts`
- Modify: `webui/frontend/src/schemas/scheduler/solar.ts`
- Modify: `webui/frontend/src/schemas/scheduler/cron.ts`
- Tests: corresponding `__tests__/` files

**Step 1: Update interval.ts**

```typescript
import { z } from 'zod'
import { SCHEDULE_LIMITS } from '../../components/scheduler/ScheduleEditor/constants'
import { TYPE, RANGE } from '../../constants/errorMessages'

export const intervalTriggerSchema = z.object({
  interval_minutes: z
    .number({ error: TYPE.number('Interval') })
    .int(TYPE.integer('Interval'))
    .min(
      SCHEDULE_LIMITS.MIN_INTERVAL_MINUTES,
      RANGE.min(SCHEDULE_LIMITS.MIN_INTERVAL_MINUTES, `minute${SCHEDULE_LIMITS.MIN_INTERVAL_MINUTES !== 1 ? 's' : ''}`),
    )
    .max(
      SCHEDULE_LIMITS.MAX_INTERVAL_MINUTES,
      RANGE.max(SCHEDULE_LIMITS.MAX_INTERVAL_MINUTES, 'minutes'),
    ),
})

export type IntervalTriggerFormData = z.infer<typeof intervalTriggerSchema>
```

**Step 2: Update fixed-time.ts**

```typescript
import { z } from 'zod'
import { TIME_FORMAT_REGEX } from '../../components/scheduler/ScheduleEditor/constants'
import { FORMAT } from '../../constants/errorMessages'

export const fixedTimeTriggerSchema = z.object({
  time_of_day: z
    .string()
    .regex(TIME_FORMAT_REGEX, FORMAT.validTime),
})

export type FixedTimeTriggerFormData = z.infer<typeof fixedTimeTriggerSchema>
```

**Step 3: Update solar.ts**

```typescript
import { z } from 'zod'
import {
  SCHEDULE_LIMITS,
  SOLAR_EVENTS,
  type SolarEventValue,
} from '../../components/scheduler/ScheduleEditor/constants'
import { TYPE, RANGE, SCHEDULER } from '../../constants/errorMessages'

const solarEventValues = SOLAR_EVENTS.map((e) => e.value) as [
  SolarEventValue,
  ...SolarEventValue[],
]

export const solarTriggerSchema = z.object({
  solar_event: z.enum(solarEventValues, {
    error: SCHEDULER.invalidSolarEvent,
  }),
  offset_minutes: z
    .number({ error: TYPE.number('Offset') })
    .int(TYPE.integer('Offset'))
    .min(
      -SCHEDULE_LIMITS.MAX_OFFSET_MINUTES,
      RANGE.min(-SCHEDULE_LIMITS.MAX_OFFSET_MINUTES, 'minutes'),
    )
    .max(
      SCHEDULE_LIMITS.MAX_OFFSET_MINUTES,
      RANGE.max(SCHEDULE_LIMITS.MAX_OFFSET_MINUTES, 'minutes'),
    ),
})

export type SolarTriggerFormData = z.infer<typeof solarTriggerSchema>
```

**Step 4: Update cron.ts**

```typescript
import { z } from 'zod'
import { TYPE, REQUIRED, CRON } from '../../constants/errorMessages'

// Keep CRON_FORMAT_REGEX and its comments unchanged
const CRON_FIELD = String.raw`(?:\*|[0-9]+(?:-[0-9]+)?)(?:/[0-9]+)?(?:,(?:\*|[0-9]+(?:-[0-9]+)?)(?:/[0-9]+)?)*`

export const CRON_FORMAT_REGEX = new RegExp(
  `^${CRON_FIELD}(?:\\s+${CRON_FIELD}){4}$`,
)

export const cronExpressionSchema = z.object({
  cron_expression: z
    .string({ error: TYPE.string('Cron expression') })
    .min(1, REQUIRED.field('Cron expression'))
    .regex(CRON_FORMAT_REGEX, CRON.format),
})

export type CronExpressionFormData = z.infer<typeof cronExpressionSchema>
```

**Step 5: Update test files**

For each test file (`interval.test.ts`, `fixed-time.test.ts`, `solar.test.ts`, `cron.test.ts`), add imports from `../../constants/errorMessages` and replace hardcoded strings with constants. Use the same mapping as the schema files.

**Step 6: Run tests**

Run: `cd webui/frontend && npx vitest run src/schemas/scheduler/__tests__/interval.test.ts src/schemas/scheduler/__tests__/fixed-time.test.ts src/schemas/scheduler/__tests__/solar.test.ts src/schemas/scheduler/__tests__/cron.test.ts`
Expected: all PASS

**Step 7: Commit**

```bash
git add webui/frontend/src/schemas/scheduler/interval.ts webui/frontend/src/schemas/scheduler/fixed-time.ts webui/frontend/src/schemas/scheduler/solar.ts webui/frontend/src/schemas/scheduler/cron.ts webui/frontend/src/schemas/scheduler/__tests__/interval.test.ts webui/frontend/src/schemas/scheduler/__tests__/fixed-time.test.ts webui/frontend/src/schemas/scheduler/__tests__/solar.test.ts webui/frontend/src/schemas/scheduler/__tests__/cron.test.ts
git commit -m "refactor(#472): migrate interval, fixed-time, solar, cron schemas to centralized errorMessages"
```

---

### Task 10: Migrate scheduler schemas (moon-phase, time-window, sensor, pre-condition, schedule)

**Files:**
- Modify: `webui/frontend/src/schemas/scheduler/moon-phase.ts`
- Modify: `webui/frontend/src/schemas/scheduler/time-window.ts`
- Modify: `webui/frontend/src/schemas/scheduler/sensor.ts`
- Modify: `webui/frontend/src/schemas/scheduler/pre-condition.ts`
- Modify: `webui/frontend/src/schemas/scheduler/schedule.ts`
- Tests: corresponding `__tests__/` files

**Step 1: Update moon-phase.ts**

```typescript
import { z } from 'zod'
import {
  SCHEDULE_LIMITS,
  MOON_PHASES,
  type MoonPhaseValue,
} from '../../components/scheduler/ScheduleEditor/constants'
import { REQUIRED, TYPE, RANGE, FORMAT, SCHEDULER } from '../../constants/errorMessages'

const moonPhaseValues = MOON_PHASES.map((p) => p.value) as [
  MoonPhaseValue,
  ...MoonPhaseValue[],
]

export const moonPhaseTriggerSchema = z.object({
  moon_phase: z.enum(moonPhaseValues, {
    error: SCHEDULER.invalidMoonPhase,
  }),
  time_of_day: z
    .string({ error: REQUIRED.field('Time') })
    .regex(/^([01]\d|2[0-3]):[0-5]\d$/, FORMAT.time),
  offset_days: z
    .number({ error: TYPE.number('Offset') })
    .int(TYPE.integer('Offset'))
    .min(
      -SCHEDULE_LIMITS.MAX_OFFSET_DAYS,
      RANGE.min(-SCHEDULE_LIMITS.MAX_OFFSET_DAYS, 'days'),
    )
    .max(
      SCHEDULE_LIMITS.MAX_OFFSET_DAYS,
      RANGE.max(SCHEDULE_LIMITS.MAX_OFFSET_DAYS, 'days'),
    ),
})

export type MoonPhaseTriggerFormData = z.infer<typeof moonPhaseTriggerSchema>
```

**Step 2: Update time-window.ts**

```typescript
import { z } from 'zod'
import {
  SOLAR_EVENTS,
  TIME_FORMAT_REGEX,
  type SolarEventValue,
} from '../../components/scheduler/ScheduleEditor/constants'
import { REQUIRED, TYPE, RANGE, FORMAT } from '../../constants/errorMessages'

const TIME_WINDOW_MAX_OFFSET_MINUTES = 120

const solarEventValues = SOLAR_EVENTS.map((e) => e.value) as [
  SolarEventValue,
  ...SolarEventValue[],
]

const timeValue = z
  .string({ error: REQUIRED.field('Time') })
  .refine(
    (v) =>
      TIME_FORMAT_REGEX.test(v) ||
      solarEventValues.includes(v as SolarEventValue),
    FORMAT.timeOrSolar,
  )

export const timeWindowSchema = z.object({
  start_time: timeValue,
  end_time: timeValue,
  start_offset_minutes: z
    .number({ error: TYPE.number('Offset') })
    .int(TYPE.integer('Offset'))
    .min(
      -TIME_WINDOW_MAX_OFFSET_MINUTES,
      RANGE.min(-TIME_WINDOW_MAX_OFFSET_MINUTES, 'minutes'),
    )
    .max(
      TIME_WINDOW_MAX_OFFSET_MINUTES,
      RANGE.max(TIME_WINDOW_MAX_OFFSET_MINUTES, 'minutes'),
    )
    .default(0),
  end_offset_minutes: z
    .number({ error: TYPE.number('Offset') })
    .int(TYPE.integer('Offset'))
    .min(
      -TIME_WINDOW_MAX_OFFSET_MINUTES,
      RANGE.min(-TIME_WINDOW_MAX_OFFSET_MINUTES, 'minutes'),
    )
    .max(
      TIME_WINDOW_MAX_OFFSET_MINUTES,
      RANGE.max(TIME_WINDOW_MAX_OFFSET_MINUTES, 'minutes'),
    )
    .default(0),
})

export type TimeWindowFormData = z.infer<typeof timeWindowSchema>
```

**Step 3: Update sensor.ts**

```typescript
import { z } from 'zod'
import {
  SENSOR_TYPES,
  SENSOR_COMPARISONS,
  SCHEDULE_LIMITS,
} from '../../components/scheduler/ScheduleEditor/constants'
import { TYPE, RANGE, SCHEDULER } from '../../constants/errorMessages'

const sensorTypeValues = SENSOR_TYPES.map((s) => s.value) as [string, ...string[]]
if (sensorTypeValues.length === 0) throw new Error('SENSOR_TYPES must not be empty')
const comparisonValues = SENSOR_COMPARISONS.map((c) => c.value) as [string, ...string[]]
if (comparisonValues.length === 0) throw new Error('SENSOR_COMPARISONS must not be empty')

export const sensorTriggerSchema = z.object({
  sensor_type: z.enum(sensorTypeValues, { error: SCHEDULER.invalidSensorType }),
  comparison: z.enum(comparisonValues, { error: SCHEDULER.invalidComparison }),
  threshold: z
    .number({ error: TYPE.number('Threshold') })
    .min(0, RANGE.min(0)),
  cooldown_minutes: z
    .number({ error: TYPE.number('Cooldown') })
    .int(TYPE.integer('Cooldown'))
    .min(1, RANGE.min(1, 'minute'))
    .max(
      SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES,
      RANGE.max(SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES, 'minutes'),
    ),
})

export type SensorTriggerFormData = z.infer<typeof sensorTriggerSchema>
```

**Step 4: Update pre-condition.ts**

```typescript
import { z } from 'zod'
import {
  SCHEDULE_LIMITS,
  TIME_FORMAT_REGEX,
} from '../../components/scheduler/ScheduleEditor/constants'
import { REQUIRED, TYPE, RANGE, FORMAT, SCHEDULER } from '../../constants/errorMessages'

/**
 * Cross-field error when start and end times match.
 * Now sourced from centralized errorMessages — single source of truth.
 */
export const TIME_WINDOW_SAME_ERROR = SCHEDULER.sameStartEnd

export const ALLOWED_SENSOR_TYPES = ['light', 'temperature'] as const

export const preConditionTimeWindowSchema = z
  .object({
    start_time: z
      .string({ error: REQUIRED.field('Start time') })
      .regex(TIME_FORMAT_REGEX, FORMAT.time),
    end_time: z
      .string({ error: REQUIRED.field('End time') })
      .regex(TIME_FORMAT_REGEX, FORMAT.time),
  })
  .refine((data) => data.start_time !== data.end_time, {
    message: TIME_WINDOW_SAME_ERROR,
    path: ['end_time'],
  })

export const preConditionSchema = z.object({
  sensor_type: z.enum(ALLOWED_SENSOR_TYPES, {
    error: SCHEDULER.invalidSensorType,
  }),
  comparison: z.enum(['lt', 'gt', 'eq'], {
    error: SCHEDULER.invalidComparison,
  }),
  threshold: z
    .number({ error: TYPE.number('Threshold') })
    .min(0, RANGE.min(0)),
  cooldown_minutes: z
    .number({ error: TYPE.number('Cooldown') })
    .min(
      SCHEDULE_LIMITS.MIN_COOLDOWN_MINUTES,
      RANGE.min(SCHEDULE_LIMITS.MIN_COOLDOWN_MINUTES, 'minutes'),
    )
    .max(
      SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES,
      RANGE.max(SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES, 'minutes'),
    ),
  time_window: preConditionTimeWindowSchema.nullable().default(null),
})

export type PreConditionFormData = z.infer<typeof preConditionSchema>
```

**Step 5: Update schedule.ts**

```typescript
import { z } from 'zod'
import { SCHEDULE_LIMITS } from '../../components/scheduler/ScheduleEditor/constants'
import { REQUIRED, LENGTH } from '../../constants/errorMessages'

export const scheduleSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, REQUIRED.field('Schedule name'))
    .max(
      SCHEDULE_LIMITS.NAME_MAX_LENGTH,
      LENGTH.max(SCHEDULE_LIMITS.NAME_MAX_LENGTH),
    ),
  description: z
    .string()
    .max(
      SCHEDULE_LIMITS.DESCRIPTION_MAX_LENGTH,
      LENGTH.max(SCHEDULE_LIMITS.DESCRIPTION_MAX_LENGTH),
    )
    .default(''),
})

export type ScheduleFormData = z.infer<typeof scheduleSchema>
```

**Step 6: Update test files**

For each test file, add imports from `../../constants/errorMessages` and replace hardcoded strings. Key replacements:

- `'Invalid sensor type'` → `SCHEDULER.invalidSensorType`
- `'Invalid comparison operator'` → `SCHEDULER.invalidComparison`
- `'Threshold must be a number'` → `TYPE.number('Threshold')`
- `'Threshold must be non-negative'` → `RANGE.min(0)` — **IMPORTANT:** verify `RANGE.min(0)` produces `'Must be at least 0'`. The original was `'Threshold must be non-negative'`. These don't match! Keep the original inline string in pre-condition.ts for threshold, OR add a domain message. **Decision: keep `'Threshold must be non-negative'` as-is in pre-condition.ts since it's a clearer UX message than `'Must be at least 0'`.**
- `'Threshold must be 0 or greater'` in sensor.ts — same issue, different wording. **Keep as-is.**

**Note on threshold messages:** The threshold min messages (`'Threshold must be non-negative'` in pre-condition, `'Threshold must be 0 or greater'` in sensor) are semantically unique messages that don't fit the generic `RANGE.min()` pattern well. Leave these as inline strings — they're only used once each and forcing them into a generic pattern would lose clarity.

Similarly, `'Cooldown must be at least 1 minute'` in sensor.ts — this works with `RANGE.min(1, 'minute')` but `'Cooldown must be a whole number'` is `TYPE.integer('Cooldown')`.

For the pre-condition test that imports from legacy errorMessages.js:
```typescript
// REMOVE this import:
// import { TIME_ERRORS } from '../../../components/scheduler/ScheduleEditor/errorMessages'
// REPLACE with:
import { SCHEDULER } from '../../../constants/errorMessages'
```

And update the drift guard test to compare against `SCHEDULER.sameStartEnd` instead of `TIME_ERRORS.SAME_START_END`.

**Step 7: Run tests**

Run: `cd webui/frontend && npx vitest run src/schemas/scheduler/__tests__/moon-phase.test.ts src/schemas/scheduler/__tests__/time-window.test.ts src/schemas/scheduler/__tests__/sensor.test.ts src/schemas/scheduler/__tests__/pre-condition.test.ts src/schemas/scheduler/__tests__/schedule.test.ts`
Expected: all PASS

**Step 8: Commit**

```bash
git add webui/frontend/src/schemas/scheduler/moon-phase.ts webui/frontend/src/schemas/scheduler/time-window.ts webui/frontend/src/schemas/scheduler/sensor.ts webui/frontend/src/schemas/scheduler/pre-condition.ts webui/frontend/src/schemas/scheduler/schedule.ts webui/frontend/src/schemas/scheduler/__tests__/moon-phase.test.ts webui/frontend/src/schemas/scheduler/__tests__/time-window.test.ts webui/frontend/src/schemas/scheduler/__tests__/sensor.test.ts webui/frontend/src/schemas/scheduler/__tests__/pre-condition.test.ts webui/frontend/src/schemas/scheduler/__tests__/schedule.test.ts
git commit -m "refactor(#472): migrate remaining scheduler schemas to centralized errorMessages"
```

---

### Task 11: Delete legacy errorMessages.js

**Files:**
- Delete: `webui/frontend/src/components/scheduler/ScheduleEditor/errorMessages.js`

**Step 1: Verify no remaining imports**

Run: `grep -r "errorMessages" webui/frontend/src/ --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx"`
Expected: NO results referencing the old file path. Only references to `constants/errorMessages`.

**Step 2: Delete the file**

```bash
git rm webui/frontend/src/components/scheduler/ScheduleEditor/errorMessages.js
```

**Step 3: Run full test suite**

Run: `cd webui/frontend && npx vitest run`
Expected: all PASS — no broken imports

**Step 4: Commit**

```bash
git commit -m "refactor(#472): delete legacy errorMessages.js — replaced by constants/errorMessages.ts"
```

---

### Task 12: Final verification and full test run

**Step 1: Verify no remaining inline strings in schemas**

Search for quoted strings in schema files that look like error messages:

Run: `grep -rn "'\(Must\|Cannot\|Invalid\|required\|too long\|too many\|cannot be\)" webui/frontend/src/schemas/ --include="*.ts"`

Expected: Only threshold messages in pre-condition.ts and sensor.ts (kept intentionally), runtime guard messages in sensor.ts, and `booleanish` in liveview-settings.ts (left as-is per design).

**Step 2: Run full frontend test suite**

Run: `cd webui/frontend && npx vitest run`
Expected: all PASS

**Step 3: Run linter**

Run: `cd webui/frontend && npx tsc --noEmit`
Expected: no new errors

**Step 4: Commit (if any fixes needed)**

```bash
git add -A
git commit -m "fix(#472): address issues found during final verification"
```

---

## String Preservation Notes

Some messages change slightly when migrated to generic patterns. Key decisions:

| Original | New (via centralized) | Same? | Action |
|---|---|---|---|
| `'Interval must be a number'` | `TYPE.number('Interval')` → `'Interval must be a number'` | Yes | Migrate |
| `'Preset name is required'` | `REQUIRED.field('Preset name')` → `'Preset name is required'` | Yes | Migrate |
| `'Must be at least 5s'` | `GPS.timeoutMin(5)` → `'Must be at least 5s'` | Yes | Migrate (GPS-specific) |
| `'Threshold must be non-negative'` | `RANGE.min(0)` → `'Must be at least 0'` | **No** | Keep inline |
| `'Threshold must be 0 or greater'` | `RANGE.min(0)` → `'Must be at least 0'` | **No** | Keep inline |
| `'Time is required'` | `REQUIRED.field('Time')` → `'Time is required'` | Yes | Migrate |
| `'Start time is required'` | `REQUIRED.field('Start time')` → `'Start time is required'` | Yes | Migrate |
| `'Cron expression is required'` | `REQUIRED.field('Cron expression')` → `'Cron expression is required'` | Yes | Migrate |
| `'Schedule name is required'` | `REQUIRED.field('Schedule name')` → `'Schedule name is required'` | Yes | Migrate |
| `'Deployment name is required'` | `REQUIRED.field('Deployment name')` → `'Deployment name is required'` | Yes | Migrate |
| `'Name must be X characters or less'` | `LENGTH.max(X)` → `'Must be X characters or less'` | **No** — lost "Name" prefix | Use `LENGTH.max(X)` — shorter is fine, field context is clear from position |
| `'Description must be X characters or less'` | `LENGTH.max(X)` → `'Must be X characters or less'` | **No** — lost "Description" prefix | Same as above |

**Files left unchanged (by design):**
- `src/schemas/liveview-settings.ts` — uses parameterized helpers, already DRY
- `src/schemas/export-options.ts` — no error messages
- `src/schemas/search.ts` — no error messages

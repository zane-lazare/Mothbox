# Design: Integrate Zod Schemas with Centralized errorMessages (#472)

## Problem

21 Zod schema files contain ~100+ inline error strings with ~15 duplicate messages across schemas. The existing `errorMessages.js` (scheduler-scoped, JS-only) is not imported by any schema. Error messages for the same concepts can drift between schemas and legacy components.

## Goals

1. **Consistency** — identical wording for the same concept everywhere
2. **Maintainability** — single source of truth; one edit to change a message
3. **i18n readiness** — centralized strings ready for extraction when #198 lands

## Decision

Replace the legacy `errorMessages.js` with a new TypeScript file using a hybrid organization (generic concepts + domain-specific groups).

### Alternatives Considered

- **A. Single flat file** — no logical grouping, naming collisions at scale. Rejected.
- **B. Single file, nested hybrid** — chosen. ~100 messages fits one file comfortably.
- **C. Multi-file module** — overkill for domains with 2-3 messages. Rejected.

## Design

### File: `src/constants/errorMessages.ts`

#### Generic Messages (by concept)

```ts
export const REQUIRED = {
  field: (name: string) => `${name} is required`,
  selection: (name: string) => `${name} must be selected`,
};

export const RANGE = {
  min: (val: number, unit?: string) => `Must be at least ${val}${unit ? ` ${unit}` : ''}`,
  max: (val: number, unit?: string) => `Cannot exceed ${val}${unit ? ` ${unit}` : ''}`,
  between: (min: number, max: number, unit?: string) =>
    `Must be between ${min} and ${max}${unit ? ` ${unit}` : ''}`,
};

export const LENGTH = {
  min: (val: number) => `Must be at least ${val} characters`,
  max: (val: number) => `Must be ${val} characters or less`,
};

export const TYPE = {
  number: (label?: string) => label ? `${label} must be a number` : 'Must be a number',
  integer: (label?: string) => label ? `${label} must be a whole number` : 'Must be a whole number',
  string: (label?: string) => label ? `${label} must be a string` : 'Must be a string',
};

export const FORMAT = {
  time: 'Must be in HH:MM format',
  url: 'Please enter a valid URL (e.g., https://example.com)',
};
```

#### Domain-Specific Messages

```ts
export const GPS = {
  invalidPath: 'Invalid device path format. Expected /dev/ttyAMA0, /dev/ttyUSB0, etc.',
};

export const DEPLOYMENT = {
  endBeforeStart: 'End date must be on or after start date',
  maxCustomFields: (max: number) => `Maximum ${max} custom fields`,
};

export const COORDINATES = {
  latitude: 'Latitude must be between -90 and 90',
  longitude: 'Longitude must be between -180 and 180',
};

export const SCHEDULER = {
  sameStartEnd: 'Start and end times cannot be the same',
};

export const CRON = {
  format: 'Must be 5 space-separated cron fields',
};

// Plus: PRESET, TAG, SPECIES, CAMERA, METADATA
```

### Schema Migration Pattern

Before (inline):
```ts
.min(MIN, `Interval must be at least ${MIN} minute`)
```

After (centralized):
```ts
import { RANGE } from '@/constants/errorMessages';
.min(MIN, RANGE.min(MIN, 'minute'))
```

### Legacy File Migration

1. Find all consumers of `src/components/scheduler/ScheduleEditor/errorMessages.js`
2. Map old exports to new equivalents (e.g., `NUMERIC_ERRORS.INVALID_INTERVAL` → `RANGE.between`)
3. Update consumers to import from `@/constants/errorMessages`
4. Delete the old file

### Message API

- Static strings where the message is fixed
- Generator functions where values are dynamic
- No i18n keys — deferred to #198 when the i18n framework is chosen

## Scope

### In scope
- Create `src/constants/errorMessages.ts`
- Update all 19 schema files with inline strings
- Migrate legacy `errorMessages.js` consumers
- Delete legacy `errorMessages.js`
- Update affected tests to import constants

### Out of scope
- i18n key extraction (#198)
- Changing user-visible error wording (strict string preservation)
- zodResolver workarounds (#485, #489)

## Testing

- Existing schema tests assert exact error strings — they are the regression safety net
- Tests updated to import from `errorMessages.ts` instead of hardcoding strings
- No dedicated test file for `errorMessages.ts` (pure constants, validated by consumers)
- Full test suite run after each schema update to catch string mismatches

## Risk

Main risk is typos during migration causing string drift. Mitigated by existing test coverage and running tests after each schema file change.

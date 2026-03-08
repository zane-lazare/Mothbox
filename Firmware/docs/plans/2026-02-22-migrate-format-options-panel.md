# Migrate FormatOptionsPanel Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate FormatOptionsPanel from manual useState/PropTypes/.jsx to react-hook-form + Zod + TypeScript, using Pattern 2 (Controlled) from the form validation design doc.

**Architecture:** Zod discriminated union schema keyed on `format` field. Component uses `useForm` with `zodResolver`, `useWatch` + `useEffect` to sync every change to parent. Parent contract preserved — `onChange` receives the flat options object.

**Tech Stack:** react-hook-form, zod, @hookform/resolvers, TypeScript, Vitest, React Testing Library

---

### Task 1: Create export-options schema

**Files:**
- Create: `webui/frontend/src/schemas/export-options.ts`

**Step 1: Write the failing test**

Create `webui/frontend/src/schemas/__tests__/export-options.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import {
  exportOptionsSchema,
  FORMAT_VALUES,
  DELIMITER_VALUES,
  EXPORT_DEFAULTS,
} from '../export-options'

/** Return the first Zod issue message from a failed parse, or null. */
function firstError(result: { success: boolean; error?: { issues: { message: string }[] } }): string | null {
  if (result.success) return null
  return result.error?.issues[0]?.message ?? null
}

describe('exportOptionsSchema', () => {
  describe('FORMAT_VALUES constant', () => {
    it('contains all four export formats', () => {
      expect(FORMAT_VALUES).toEqual(['darwin_core', 'inaturalist', 'json', 'csv'])
    })
  })

  describe('DELIMITER_VALUES constant', () => {
    it('contains comma, tab, semicolon', () => {
      expect(DELIMITER_VALUES).toEqual([',', '\t', ';'])
    })
  })

  describe('darwin_core format', () => {
    it('accepts valid darwin_core options', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'darwin_core',
        gps_precision: 2,
        validate: true,
        include_warnings: false,
      })
      expect(result.success).toBe(true)
    })

    it('rejects darwin_core with missing validate field', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'darwin_core',
        gps_precision: 2,
        include_warnings: false,
      })
      expect(result.success).toBe(false)
    })

    it('rejects darwin_core with csv-specific field', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'darwin_core',
        gps_precision: 2,
        validate: true,
        include_warnings: false,
        delimiter: ',',
      })
      expect(result.success).toBe(false)
    })
  })

  describe('inaturalist format', () => {
    it('accepts valid inaturalist options', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'inaturalist',
        gps_precision: 3,
        include_xmp_sidecars: true,
        include_manifest: true,
        include_csv_summary: false,
      })
      expect(result.success).toBe(true)
    })

    it('rejects inaturalist with missing include_xmp_sidecars', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'inaturalist',
        gps_precision: 3,
        include_manifest: true,
        include_csv_summary: false,
      })
      expect(result.success).toBe(false)
    })
  })

  describe('json format', () => {
    it('accepts valid json options', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'json',
        gps_precision: 2,
        pretty_print: true,
        include_raw_exif: false,
      })
      expect(result.success).toBe(true)
    })

    it('rejects json with missing pretty_print', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'json',
        gps_precision: 2,
        include_raw_exif: false,
      })
      expect(result.success).toBe(false)
    })
  })

  describe('csv format', () => {
    it('accepts valid csv options with comma delimiter', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'csv',
        gps_precision: 2,
        include_bom: true,
        delimiter: ',',
      })
      expect(result.success).toBe(true)
    })

    it('accepts tab delimiter', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'csv',
        gps_precision: 2,
        include_bom: true,
        delimiter: '\t',
      })
      expect(result.success).toBe(true)
    })

    it('accepts semicolon delimiter', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'csv',
        gps_precision: 2,
        include_bom: true,
        delimiter: ';',
      })
      expect(result.success).toBe(true)
    })

    it('rejects invalid delimiter', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'csv',
        gps_precision: 2,
        include_bom: true,
        delimiter: '|',
      })
      expect(result.success).toBe(false)
    })
  })

  describe('gps_precision validation', () => {
    it('accepts gps_precision 0', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'darwin_core',
        gps_precision: 0,
        validate: false,
        include_warnings: false,
      })
      expect(result.success).toBe(true)
    })

    it('accepts gps_precision 6', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'darwin_core',
        gps_precision: 6,
        validate: false,
        include_warnings: false,
      })
      expect(result.success).toBe(true)
    })

    it('rejects gps_precision below 0', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'darwin_core',
        gps_precision: -1,
        validate: false,
        include_warnings: false,
      })
      expect(result.success).toBe(false)
    })

    it('rejects gps_precision above 6', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'darwin_core',
        gps_precision: 7,
        validate: false,
        include_warnings: false,
      })
      expect(result.success).toBe(false)
    })

    it('rejects non-integer gps_precision', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'darwin_core',
        gps_precision: 2.5,
        validate: false,
        include_warnings: false,
      })
      expect(result.success).toBe(false)
    })
  })

  describe('discriminated union', () => {
    it('rejects unknown format', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'xml',
        gps_precision: 2,
      })
      expect(result.success).toBe(false)
    })

    it('rejects missing format', () => {
      const result = exportOptionsSchema.safeParse({
        gps_precision: 2,
      })
      expect(result.success).toBe(false)
    })
  })

  describe('EXPORT_DEFAULTS', () => {
    it('provides defaults for all four formats', () => {
      expect(EXPORT_DEFAULTS).toHaveProperty('darwin_core')
      expect(EXPORT_DEFAULTS).toHaveProperty('inaturalist')
      expect(EXPORT_DEFAULTS).toHaveProperty('json')
      expect(EXPORT_DEFAULTS).toHaveProperty('csv')
    })

    it('all defaults pass schema validation', () => {
      for (const format of FORMAT_VALUES) {
        const result = exportOptionsSchema.safeParse(EXPORT_DEFAULTS[format])
        expect(result.success).toBe(true)
      }
    })

    it('darwin_core defaults match current component behavior', () => {
      expect(EXPORT_DEFAULTS.darwin_core).toEqual({
        format: 'darwin_core',
        gps_precision: 2,
        validate: false,
        include_warnings: false,
      })
    })

    it('inaturalist defaults match current component behavior', () => {
      expect(EXPORT_DEFAULTS.inaturalist).toEqual({
        format: 'inaturalist',
        gps_precision: 2,
        include_xmp_sidecars: true,
        include_manifest: true,
        include_csv_summary: false,
      })
    })

    it('json defaults match current component behavior', () => {
      expect(EXPORT_DEFAULTS.json).toEqual({
        format: 'json',
        gps_precision: 2,
        pretty_print: true,
        include_raw_exif: false,
      })
    })

    it('csv defaults match current component behavior', () => {
      expect(EXPORT_DEFAULTS.csv).toEqual({
        format: 'csv',
        gps_precision: 2,
        include_bom: true,
        delimiter: ',',
      })
    })
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd webui/frontend && npx vitest run src/schemas/__tests__/export-options.test.ts`
Expected: FAIL — cannot find module `../export-options`

**Step 3: Write minimal implementation**

Create `webui/frontend/src/schemas/export-options.ts`:

```typescript
import { z } from 'zod'
import { getGpsPrecision } from '../utils/gpsPrecision'

export const FORMAT_VALUES = ['darwin_core', 'inaturalist', 'json', 'csv'] as const

export const DELIMITER_VALUES = [',', '\t', ';'] as const

const gpsPrecision = z.number().int().min(0).max(6)

const darwinCoreSchema = z.object({
  format: z.literal('darwin_core'),
  gps_precision: gpsPrecision,
  validate: z.boolean(),
  include_warnings: z.boolean(),
})

const inaturalistSchema = z.object({
  format: z.literal('inaturalist'),
  gps_precision: gpsPrecision,
  include_xmp_sidecars: z.boolean(),
  include_manifest: z.boolean(),
  include_csv_summary: z.boolean(),
})

const jsonSchema = z.object({
  format: z.literal('json'),
  gps_precision: gpsPrecision,
  pretty_print: z.boolean(),
  include_raw_exif: z.boolean(),
})

const csvSchema = z.object({
  format: z.literal('csv'),
  gps_precision: gpsPrecision,
  include_bom: z.boolean(),
  delimiter: z.enum(DELIMITER_VALUES),
})

export const exportOptionsSchema = z.discriminatedUnion('format', [
  darwinCoreSchema,
  inaturalistSchema,
  jsonSchema,
  csvSchema,
])

export type ExportOptionsFormData = z.infer<typeof exportOptionsSchema>

/** Per-format default values for form reset. */
export const EXPORT_DEFAULTS: Record<typeof FORMAT_VALUES[number], ExportOptionsFormData> = {
  darwin_core: {
    format: 'darwin_core',
    gps_precision: 2,
    validate: false,
    include_warnings: false,
  },
  inaturalist: {
    format: 'inaturalist',
    gps_precision: 2,
    include_xmp_sidecars: true,
    include_manifest: true,
    include_csv_summary: false,
  },
  json: {
    format: 'json',
    gps_precision: 2,
    pretty_print: true,
    include_raw_exif: false,
  },
  csv: {
    format: 'csv',
    gps_precision: 2,
    include_bom: true,
    delimiter: ',',
  },
}

/**
 * Build default values for a given format, using the user's stored GPS precision.
 * Call this at form initialization or when format changes to pick up localStorage.
 */
export function getExportDefaults(format: typeof FORMAT_VALUES[number]): ExportOptionsFormData {
  return { ...EXPORT_DEFAULTS[format], gps_precision: getGpsPrecision() }
}
```

**Step 4: Run test to verify it passes**

Run: `cd webui/frontend && npx vitest run src/schemas/__tests__/export-options.test.ts`
Expected: PASS — all tests green

**Step 5: Update schema barrel export**

Edit `webui/frontend/src/schemas/index.ts` — add these lines at the end:

```typescript
export { exportOptionsSchema, FORMAT_VALUES, DELIMITER_VALUES, EXPORT_DEFAULTS, getExportDefaults } from './export-options';
export type { ExportOptionsFormData } from './export-options';
```

**Step 6: Commit**

```bash
git add webui/frontend/src/schemas/export-options.ts webui/frontend/src/schemas/__tests__/export-options.test.ts webui/frontend/src/schemas/index.ts
git commit -m "feat(#442): add Zod discriminated union schema for export options"
```

---

### Task 2: Migrate FormatOptionsPanel to TypeScript + react-hook-form

**Files:**
- Delete: `webui/frontend/src/components/export/FormatOptionsPanel.jsx`
- Create: `webui/frontend/src/components/export/FormatOptionsPanel.tsx`
- Modify: `webui/frontend/src/components/export/index.js` (no change needed if import path stays same)

**Step 1: Write the component**

Create `webui/frontend/src/components/export/FormatOptionsPanel.tsx`:

```tsx
import { useEffect, useRef } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import {
  exportOptionsSchema,
  getExportDefaults,
  FORMAT_VALUES,
  type ExportOptionsFormData,
} from '../../schemas/export-options'
import { GPS_PRECISION_OPTIONS } from '../../utils/gpsPrecision'

type FormatValue = typeof FORMAT_VALUES[number]

interface FormatOptionsPanelProps {
  format: string | null
  options?: Record<string, unknown>
  onChange: (options: Record<string, unknown>) => void
  disabled?: boolean
}

function FormatOptionsPanel({
  format,
  options = {},
  onChange,
  disabled = false,
}: FormatOptionsPanelProps) {
  const onChangeRef = useRef(onChange)
  onChangeRef.current = onChange

  // Guard: only render for valid formats
  if (!format || !FORMAT_VALUES.includes(format as FormatValue)) {
    return null
  }

  const validFormat = format as FormatValue

  // Build initial values: merge parent options over defaults
  const defaults = getExportDefaults(validFormat)
  const initialValues = { ...defaults, ...options, format: validFormat } as ExportOptionsFormData

  const { control, register, reset } = useForm<ExportOptionsFormData>({
    resolver: zodResolver(exportOptionsSchema),
    defaultValues: initialValues,
    mode: 'onChange',
  })

  // Sync form changes to parent (strip `format` key)
  const watched = useWatch({ control })
  useEffect(() => {
    if (!watched || !watched.format) return
    const { format: _format, ...rest } = watched
    onChangeRef.current(rest as Record<string, unknown>)
  }, [watched])

  // Reset form when parent changes format
  const prevFormatRef = useRef(validFormat)
  useEffect(() => {
    if (validFormat !== prevFormatRef.current) {
      prevFormatRef.current = validFormat
      const newDefaults = getExportDefaults(validFormat)
      reset({ ...newDefaults, ...options, format: validFormat } as ExportOptionsFormData)
    }
  }, [validFormat, options, reset])

  const currentFormat = watched.format ?? validFormat

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
        Format Options
      </h3>

      {/* GPS Precision - Common to all formats (Issue #288) */}
      <div className="mb-4 pb-4 border-b border-gray-200 dark:border-gray-700">
        <label
          htmlFor="gps-precision"
          className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-1"
        >
          GPS Precision
        </label>
        <select
          id="gps-precision"
          {...register('gps_precision', { valueAsNumber: true })}
          disabled={disabled}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                    focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                    bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                    disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {GPS_PRECISION_OPTIONS.map(({ value, label }) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
          Reduce precision for privacy when sharing location data
        </p>
      </div>

      {/* Darwin Core Options */}
      {currentFormat === 'darwin_core' && (
        <div className="space-y-3">
          <label className="flex items-start gap-2">
            <input
              type="checkbox"
              {...register('validate' as never)}
              disabled={disabled}
              className="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500
                        disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <div>
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Validate output against Darwin Core schema
              </span>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Ensure exported data conforms to Darwin Core standards
              </p>
            </div>
          </label>

          <label className="flex items-start gap-2">
            <input
              type="checkbox"
              {...register('include_warnings' as never)}
              disabled={disabled}
              className="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500
                        disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <div>
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Include validation warnings
              </span>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Add warnings as comments in the CSV file
              </p>
            </div>
          </label>
        </div>
      )}

      {/* iNaturalist Options */}
      {currentFormat === 'inaturalist' && (
        <div className="space-y-3">
          <label className="flex items-start gap-2">
            <input
              type="checkbox"
              {...register('include_xmp_sidecars' as never)}
              disabled={disabled}
              className="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500
                        disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <div>
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Include XMP sidecar files
              </span>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Generate .xmp files alongside photos with embedded metadata
              </p>
            </div>
          </label>

          <label className="flex items-start gap-2">
            <input
              type="checkbox"
              {...register('include_manifest' as never)}
              disabled={disabled}
              className="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500
                        disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <div>
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Include manifest.json
              </span>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Add manifest file with export metadata and file list
              </p>
            </div>
          </label>

          <label className="flex items-start gap-2">
            <input
              type="checkbox"
              {...register('include_csv_summary' as never)}
              disabled={disabled}
              className="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500
                        disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <div>
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Include CSV summary
              </span>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Add a summary CSV file with photo metadata
              </p>
            </div>
          </label>
        </div>
      )}

      {/* JSON Options */}
      {currentFormat === 'json' && (
        <div className="space-y-3">
          <label className="flex items-start gap-2">
            <input
              type="checkbox"
              {...register('pretty_print' as never)}
              disabled={disabled}
              className="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500
                        disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <div>
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Pretty print JSON
              </span>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Format JSON with indentation for readability
              </p>
            </div>
          </label>

          <label className="flex items-start gap-2">
            <input
              type="checkbox"
              {...register('include_raw_exif' as never)}
              disabled={disabled}
              className="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500
                        disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <div>
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Include raw EXIF data
              </span>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Add complete EXIF data from photo files
              </p>
            </div>
          </label>
        </div>
      )}

      {/* CSV Options */}
      {currentFormat === 'csv' && (
        <div className="space-y-3">
          <label className="flex items-start gap-2">
            <input
              type="checkbox"
              {...register('include_bom' as never)}
              disabled={disabled}
              className="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500
                        disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <div>
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Include UTF-8 BOM
              </span>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Add byte order mark for Excel compatibility
              </p>
            </div>
          </label>

          <div>
            <label
              htmlFor="csv-delimiter"
              className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-1"
            >
              Delimiter
            </label>
            <select
              id="csv-delimiter"
              {...register('delimiter' as never)}
              disabled={disabled}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                        focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                        bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                        disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <option value=",">Comma (,)</option>
              <option value={'\t'}>Tab</option>
              <option value=";">Semicolon (;)</option>
            </select>
            <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
              Choose delimiter for CSV columns
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

export default FormatOptionsPanel
```

**Step 2: Delete old file**

```bash
git rm webui/frontend/src/components/export/FormatOptionsPanel.jsx
```

**Step 3: Verify build compiles**

Run: `cd webui/frontend && npx tsc --noEmit`
Expected: No type errors

**Step 4: Run existing tests to check for regressions**

Run: `cd webui/frontend && npx vitest run src/components/export/__tests__/FormatOptionsPanel.test.jsx`
Expected: May fail since import paths or behavior changed — this is expected and fixed in Task 3.

**Step 5: Commit**

```bash
git add webui/frontend/src/components/export/FormatOptionsPanel.tsx
git commit -m "feat(#442): migrate FormatOptionsPanel to TypeScript + react-hook-form"
```

---

### Task 3: Migrate component tests to TypeScript

**Files:**
- Delete: `webui/frontend/src/components/export/__tests__/FormatOptionsPanel.test.jsx`
- Create: `webui/frontend/src/components/export/__tests__/FormatOptionsPanel.test.tsx`

**Step 1: Write the migrated test file**

Create `webui/frontend/src/components/export/__tests__/FormatOptionsPanel.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import FormatOptionsPanel from '../FormatOptionsPanel'

// Mock getGpsPrecision to return a stable default (2) in tests
vi.mock('../../../utils/gpsPrecision', async () => {
  const actual = await vi.importActual('../../../utils/gpsPrecision')
  return {
    ...(actual as Record<string, unknown>),
    getGpsPrecision: () => 2,
  }
})

describe('FormatOptionsPanel', () => {
  let onChange: ReturnType<typeof vi.fn>

  beforeEach(() => {
    onChange = vi.fn()
  })

  it('shows Darwin Core options when format is darwin_core', () => {
    render(
      <FormatOptionsPanel format="darwin_core" options={{}} onChange={onChange} />
    )
    expect(screen.getByLabelText(/validate output/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/include validation warnings/i)).toBeInTheDocument()
  })

  it('shows iNaturalist options when format is inaturalist', () => {
    render(
      <FormatOptionsPanel format="inaturalist" options={{}} onChange={onChange} />
    )
    expect(screen.getByLabelText(/include xmp sidecar/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/include manifest/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/include csv summary/i)).toBeInTheDocument()
  })

  it('shows JSON options when format is json', () => {
    render(
      <FormatOptionsPanel format="json" options={{}} onChange={onChange} />
    )
    expect(screen.getByLabelText(/pretty print/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/include raw exif/i)).toBeInTheDocument()
  })

  it('shows CSV options when format is csv', () => {
    render(
      <FormatOptionsPanel format="csv" options={{}} onChange={onChange} />
    )
    expect(screen.getByLabelText(/include utf-8 bom/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/delimiter/i)).toBeInTheDocument()
  })

  it('calls onChange with updated options when checkbox toggled', async () => {
    const user = userEvent.setup()

    render(
      <FormatOptionsPanel
        format="darwin_core"
        options={{ validate: false }}
        onChange={onChange}
      />
    )

    const validateCheckbox = screen.getByLabelText(/validate output/i)
    await user.click(validateCheckbox)

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({ validate: true })
      )
    })
  })

  it('calls onChange when delimiter select changed', async () => {
    const user = userEvent.setup()

    render(
      <FormatOptionsPanel
        format="csv"
        options={{ delimiter: ',' }}
        onChange={onChange}
      />
    )

    const delimiterSelect = screen.getByLabelText(/delimiter/i)
    await user.selectOptions(delimiterSelect, '\t')

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({ delimiter: '\t' })
      )
    })
  })

  it('respects disabled prop for all controls', () => {
    render(
      <FormatOptionsPanel
        format="darwin_core"
        options={{}}
        onChange={onChange}
        disabled
      />
    )
    expect(screen.getByLabelText(/validate output/i)).toBeDisabled()
    expect(screen.getByLabelText(/include validation warnings/i)).toBeDisabled()
  })

  it('shows default values for iNaturalist options', () => {
    render(
      <FormatOptionsPanel
        format="inaturalist"
        options={{
          include_xmp_sidecars: true,
          include_manifest: true,
          include_csv_summary: false,
        }}
        onChange={onChange}
      />
    )
    expect(screen.getByLabelText(/include xmp sidecar/i)).toBeChecked()
    expect(screen.getByLabelText(/include manifest/i)).toBeChecked()
    expect(screen.getByLabelText(/include csv summary/i)).not.toBeChecked()
  })

  it('shows default values for JSON options', () => {
    render(
      <FormatOptionsPanel
        format="json"
        options={{
          pretty_print: true,
          include_raw_exif: false,
        }}
        onChange={onChange}
      />
    )
    expect(screen.getByLabelText(/pretty print/i)).toBeChecked()
    expect(screen.getByLabelText(/include raw exif/i)).not.toBeChecked()
  })

  it('shows default values for CSV options', () => {
    render(
      <FormatOptionsPanel
        format="csv"
        options={{
          include_bom: true,
          delimiter: ',',
        }}
        onChange={onChange}
      />
    )
    expect(screen.getByLabelText(/include utf-8 bom/i)).toBeChecked()
    expect(screen.getByLabelText(/delimiter/i)).toHaveValue(',')
  })

  it('shows delimiter options: comma, tab, semicolon', () => {
    render(
      <FormatOptionsPanel
        format="csv"
        options={{ delimiter: ',' }}
        onChange={onChange}
      />
    )

    const delimiterSelect = screen.getByLabelText(/delimiter/i)
    const optionValues = Array.from(
      (delimiterSelect as HTMLSelectElement).options
    ).map((opt) => opt.value)

    expect(optionValues).toContain(',')
    expect(optionValues).toContain('\t')
    expect(optionValues).toContain(';')
  })

  it('renders nothing when format is null', () => {
    const { container } = render(
      <FormatOptionsPanel format={null} options={{}} onChange={onChange} />
    )
    expect(container.firstChild).toBeNull()
  })

  // GPS Precision tests (Issue #288)
  describe('GPS Precision Option', () => {
    it('shows GPS precision dropdown for darwin_core format', () => {
      render(
        <FormatOptionsPanel format="darwin_core" options={{}} onChange={onChange} />
      )
      expect(screen.getByLabelText(/gps precision/i)).toBeInTheDocument()
    })

    it('shows GPS precision dropdown for inaturalist format', () => {
      render(
        <FormatOptionsPanel format="inaturalist" options={{}} onChange={onChange} />
      )
      expect(screen.getByLabelText(/gps precision/i)).toBeInTheDocument()
    })

    it('shows GPS precision dropdown for json format', () => {
      render(
        <FormatOptionsPanel format="json" options={{}} onChange={onChange} />
      )
      expect(screen.getByLabelText(/gps precision/i)).toBeInTheDocument()
    })

    it('shows GPS precision dropdown for csv format', () => {
      render(
        <FormatOptionsPanel format="csv" options={{}} onChange={onChange} />
      )
      expect(screen.getByLabelText(/gps precision/i)).toBeInTheDocument()
    })

    it('defaults to global precision setting (2) when not specified', () => {
      render(
        <FormatOptionsPanel format="darwin_core" options={{}} onChange={onChange} />
      )
      const precisionSelect = screen.getByLabelText(/gps precision/i)
      expect(precisionSelect).toHaveValue('2')
    })

    it('shows precision value when provided in options', () => {
      render(
        <FormatOptionsPanel
          format="darwin_core"
          options={{ gps_precision: 0 }}
          onChange={onChange}
        />
      )
      const precisionSelect = screen.getByLabelText(/gps precision/i)
      expect(precisionSelect).toHaveValue('0')
    })

    it('calls onChange with gps_precision when changed', async () => {
      const user = userEvent.setup()

      render(
        <FormatOptionsPanel
          format="darwin_core"
          options={{ gps_precision: 2 }}
          onChange={onChange}
        />
      )

      const precisionSelect = screen.getByLabelText(/gps precision/i)
      await user.selectOptions(precisionSelect, '0')

      await waitFor(() => {
        expect(onChange).toHaveBeenCalledWith(
          expect.objectContaining({ gps_precision: 0 })
        )
      })
    })

    it('shows all precision options (0-6)', () => {
      render(
        <FormatOptionsPanel format="darwin_core" options={{}} onChange={onChange} />
      )

      const precisionSelect = screen.getByLabelText(/gps precision/i)
      const optionValues = Array.from(
        (precisionSelect as HTMLSelectElement).options
      ).map((opt) => opt.value)

      expect(optionValues).toEqual(['0', '1', '2', '3', '4', '5', '6'])
    })

    it('preserves other options when changing gps_precision', async () => {
      const user = userEvent.setup()

      render(
        <FormatOptionsPanel
          format="darwin_core"
          options={{ validate: true, gps_precision: 2 }}
          onChange={onChange}
        />
      )

      const precisionSelect = screen.getByLabelText(/gps precision/i)
      await user.selectOptions(precisionSelect, '1')

      await waitFor(() => {
        expect(onChange).toHaveBeenCalledWith(
          expect.objectContaining({
            validate: true,
            gps_precision: 1,
          })
        )
      })
    })

    it('respects disabled prop for gps precision dropdown', () => {
      render(
        <FormatOptionsPanel
          format="darwin_core"
          options={{}}
          onChange={onChange}
          disabled
        />
      )
      expect(screen.getByLabelText(/gps precision/i)).toBeDisabled()
    })
  })

  it('updates only changed option while preserving others', async () => {
    const user = userEvent.setup()

    render(
      <FormatOptionsPanel
        format="json"
        options={{
          pretty_print: true,
          include_raw_exif: false,
        }}
        onChange={onChange}
      />
    )

    const rawExifCheckbox = screen.getByLabelText(/include raw exif/i)
    await user.click(rawExifCheckbox)

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({
          pretty_print: true,
          include_raw_exif: true,
        })
      )
    })
  })
})
```

**Key differences from original tests:**
- TypeScript types
- `waitFor` wrapping `onChange` assertions (useWatch + useEffect is async)
- Mock `getGpsPrecision` for stable test behavior
- `expect.objectContaining` instead of exact match (form may include all fields)
- Cast `as HTMLSelectElement` for `.options` access

**Step 2: Delete old test file**

```bash
git rm webui/frontend/src/components/export/__tests__/FormatOptionsPanel.test.jsx
```

**Step 3: Run tests to verify all pass**

Run: `cd webui/frontend && npx vitest run src/components/export/__tests__/FormatOptionsPanel.test.tsx`
Expected: All 20+ tests PASS

**Step 4: Run schema tests too**

Run: `cd webui/frontend && npx vitest run src/schemas/__tests__/export-options.test.ts`
Expected: All PASS

**Step 5: Commit**

```bash
git add webui/frontend/src/components/export/__tests__/FormatOptionsPanel.test.tsx
git commit -m "test(#442): migrate FormatOptionsPanel tests to TypeScript"
```

---

### Task 4: Verify no regressions and run lint

**Files:** None — verification only

**Step 1: Run all export-related tests**

Run: `cd webui/frontend && npx vitest run src/components/export/ src/schemas/ src/pages/__tests__/Export.test.jsx`
Expected: All PASS

**Step 2: Run TypeScript check**

Run: `cd webui/frontend && npx tsc --noEmit`
Expected: No errors

**Step 3: Run ESLint**

Run: `cd webui/frontend && npx eslint src/components/export/FormatOptionsPanel.tsx src/schemas/export-options.ts`
Expected: No errors (or only pre-existing warnings)

**Step 4: Build frontend**

Run: `cd webui/frontend && npm run build`
Expected: Build succeeds

**Step 5: Commit any lint fixes if needed**

```bash
git add -u
git commit -m "fix(#442): lint fixes for FormatOptionsPanel migration"
```

---

### Implementation Notes

**Hooks call order concern:** The component has a conditional early return (`if (!format)`) before `useForm`. React requires hooks to be called in the same order every render. The implementation must either:
- Move the early return AFTER hooks (render form hooks unconditionally, return null from JSX), OR
- Split into two components: outer guard + inner form component

The plan code above uses the early-return pattern. If React strict mode flags this, refactor into `FormatOptionsPanelInner` + outer guard wrapper. This is addressed during implementation.

**`as never` casts on register:** The discriminated union means field names like `validate` only exist on the `darwin_core` variant. TypeScript can't narrow inside `register()` since the form type is the union. Using `as never` is the established pattern for discriminated union forms in react-hook-form. An alternative is `register(fieldName as any)` but `as never` is safer.

**onChange ref pattern:** `onChangeRef` prevents `onChange` from being a dependency of the `useWatch` effect, avoiding infinite re-render loops when the parent creates a new function reference each render.

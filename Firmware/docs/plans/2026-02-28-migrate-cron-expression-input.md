# CronExpressionInput Migration Implementation Plan

**Goal:** Migrate CronExpressionInput, useCronValidation, and ExpertMode constants from .jsx/.js to .tsx/.ts with Zod schema and full TypeScript typing.

**Architecture:** Thin typed wrapper — no internal RHF form. Component stays pure controlled (`value`/`onChange`/`disabled`). A Zod schema provides sync format validation for composability. The existing `useCronValidation` hook is typed with explicit interfaces for the API response.

**Tech Stack:** TypeScript, Zod, React, TanStack Query, Vitest

---

### Task 1: Create Zod schema with tests

**Files:**
- Create: `src/schemas/scheduler/cron.ts`
- Create: `src/schemas/scheduler/__tests__/cron.test.ts`

**Context:** The schema validates cron expression format (5 space-separated fields). It does NOT replicate the server's full range validation — that stays in the API hook. Each field allows: `*`, `*/N`, `N`, `N-M`, `N,M`, or combinations like `1,3,5` and `1-5`.

**Step 1: Write the schema tests**

Create `src/schemas/scheduler/__tests__/cron.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { cronExpressionSchema, CRON_FORMAT_REGEX } from '../cron'

/** Return the first Zod issue message from a failed parse, or null. */
function firstError(
  result: { success: boolean; error?: { issues: { message: string }[] } },
): string | null {
  if (result.success) return null
  return result.error?.issues[0]?.message ?? null
}

describe('CRON_FORMAT_REGEX', () => {
  const valid = [
    '* * * * *',
    '0 * * * *',
    '*/5 * * * *',
    '0 21 * * *',
    '0 21 * * 1-5',
    '0,30 * * * *',
    '0 0 1,15 * *',
    '*/15 9-17 * * 1-5',
    '5 4 * * 0',
    '0 0 1 1 *',
  ]

  const invalid = [
    '',
    '*',
    '* *',
    '* * *',
    '* * * *',
    '* * * * * *',       // 6 fields
    'every 5 minutes',
    '@daily',             // special syntax not supported
    '0 21 * * * extra',
  ]

  it.each(valid)('accepts "%s"', (expr) => {
    expect(CRON_FORMAT_REGEX.test(expr)).toBe(true)
  })

  it.each(invalid)('rejects "%s"', (expr) => {
    expect(CRON_FORMAT_REGEX.test(expr)).toBe(false)
  })
})

describe('cronExpressionSchema', () => {
  it('accepts valid cron expression', () => {
    const result = cronExpressionSchema.safeParse({
      cron_expression: '0 21 * * *',
    })
    expect(result.success).toBe(true)
  })

  it('rejects empty string', () => {
    const result = cronExpressionSchema.safeParse({
      cron_expression: '',
    })
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe('Cron expression is required')
  })

  it('rejects malformed expression', () => {
    const result = cronExpressionSchema.safeParse({
      cron_expression: 'not a cron',
    })
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe('Must be 5 space-separated cron fields')
  })

  it('rejects missing field', () => {
    const result = cronExpressionSchema.safeParse({})
    expect(result.success).toBe(false)
  })

  it('rejects non-string', () => {
    const result = cronExpressionSchema.safeParse({
      cron_expression: 42,
    })
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe('Cron expression must be a string')
  })

  it('accepts all preset expressions', () => {
    const presets = [
      '0 * * * *',
      '*/5 * * * *',
      '*/15 * * * *',
      '0 0 * * *',
      '0 21 * * *',
      '0 21 * * 1-5',
    ]
    for (const expr of presets) {
      const result = cronExpressionSchema.safeParse({ cron_expression: expr })
      expect(result.success).toBe(true)
    }
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd webui/frontend && npx vitest run src/schemas/scheduler/__tests__/cron.test.ts`
Expected: FAIL (module not found)

**Step 3: Write the schema**

Create `src/schemas/scheduler/cron.ts`:

```ts
import { z } from 'zod'

/**
 * Regex matching a single cron field token.
 * Allows: *, N, N-M, N,M,... , * /N, N-M/N, and combinations.
 * Does NOT validate numeric ranges (server handles that).
 */
const CRON_FIELD = String.raw`(?:\*|[0-9]+(?:-[0-9]+)?)(?:/[0-9]+)?(?:,(?:\*|[0-9]+(?:-[0-9]+)?)(?:/[0-9]+)?)*`

/**
 * Regex matching a 5-field cron expression (minute hour day month weekday).
 * Exported for direct use in tests and parent schemas.
 */
export const CRON_FORMAT_REGEX = new RegExp(
  `^${CRON_FIELD}(?:\\s+${CRON_FIELD}){4}$`,
)

/**
 * Schema for a cron expression field.
 * Sync format validation only — full semantic validation (range checks,
 * day-of-month limits) is handled by the server via useCronValidation.
 */
export const cronExpressionSchema = z.object({
  cron_expression: z
    .string({ error: 'Cron expression must be a string' })
    .min(1, 'Cron expression is required')
    .regex(CRON_FORMAT_REGEX, 'Must be 5 space-separated cron fields'),
})

export type CronExpressionFormData = z.infer<typeof cronExpressionSchema>
```

**Step 4: Run tests to verify they pass**

Run: `cd webui/frontend && npx vitest run src/schemas/scheduler/__tests__/cron.test.ts`
Expected: All pass

**Step 5: Run tsc**

Run: `cd webui/frontend && npx tsc --noEmit`
Expected: No new errors

**Step 6: Commit**

```bash
git add src/schemas/scheduler/cron.ts src/schemas/scheduler/__tests__/cron.test.ts
git commit -m "feat(#451): add Zod schema and tests for cron expression"
```

---

### Task 2: Migrate ExpertMode constants to TypeScript

**Files:**
- Rename: `src/components/scheduler/ExpertMode/constants.js` → `constants.ts`

**Context:** The constants file exports `CRON_PRESETS` and `CRON_HELP`. Adding `as const` and explicit interfaces makes them type-safe for the component.

**Step 1: Rename and type the file**

Rename `constants.js` to `constants.ts` via `git mv`. Replace contents:

```ts
/**
 * Constants for Expert Mode Cron Expression Editor (Issue #233)
 */

export interface CronPreset {
  readonly label: string
  readonly expression: string
}

export interface CronFieldHelp {
  readonly name: string
  readonly range: string
}

export interface CronHelp {
  readonly format: string
  readonly fields: readonly CronFieldHelp[]
  readonly special: string
}

/** Quick preset cron expressions for common scheduling patterns */
export const CRON_PRESETS: readonly CronPreset[] = [
  { label: 'Every hour', expression: '0 * * * *' },
  { label: 'Every 5 min', expression: '*/5 * * * *' },
  { label: 'Every 15 min', expression: '*/15 * * * *' },
  { label: 'Daily midnight', expression: '0 0 * * *' },
  { label: 'Daily 9 PM', expression: '0 21 * * *' },
  { label: 'Weekdays 9 PM', expression: '0 21 * * 1-5' },
] as const

/** Help text for cron expression format */
export const CRON_HELP: CronHelp = {
  format: 'minute hour day month weekday',
  fields: [
    { name: 'minute', range: '0-59' },
    { name: 'hour', range: '0-23' },
    { name: 'day', range: '1-31' },
    { name: 'month', range: '1-12' },
    { name: 'weekday', range: '0-6 (Sun-Sat)' },
  ],
  special: '* = any, */N = every N, N-M = range, N,M = list',
} as const
```

**Step 2: Run tsc**

Run: `cd webui/frontend && npx tsc --noEmit`
Expected: No errors (Vite resolves .ts automatically; .jsx importers of constants work fine with bundler resolution)

**Step 3: Run existing component tests**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ExpertMode/__tests__/CronExpressionInput.test.jsx`
Expected: All 21 tests pass (import resolves .ts via Vite)

**Step 4: Commit**

```bash
git add src/components/scheduler/ExpertMode/constants.ts
git rm src/components/scheduler/ExpertMode/constants.js
git commit -m "refactor(#451): migrate ExpertMode constants to TypeScript"
```

---

### Task 3: Migrate useCronValidation hook to TypeScript

**Files:**
- Rename: `src/hooks/useCronValidation.js` → `useCronValidation.ts`

**Context:** The hook uses TanStack Query with debouncing. We add full interfaces for the API response and hook options. The `cronApi.js` file stays as-is (it's a shared utility used elsewhere, and `.js` imports work fine from `.ts` via bundler resolution).

**Step 1: Rename and type the file**

Rename via `git mv`. Replace contents:

```ts
/**
 * React Query hook for cron expression validation (Issue #233)
 *
 * Provides real-time validation of cron expressions with debounced input
 * to reduce unnecessary API calls while typing.
 */

import { useState, useEffect } from 'react'
import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
import { QUERY_KEYS } from '../utils/queryKeys'
// @ts-expect-error — cronApi.js has no type declarations (pre-migration)
import { validateCronExpression } from '../utils/cronApi'

// -- Types -------------------------------------------------------------------

/** Shape returned by the cron validation API endpoint. */
export interface CronValidationResult {
  valid: boolean
  expression: string
  /** Human-readable description (present when valid) */
  description?: string
  /** ISO timestamps of next N executions (present when valid) */
  next_executions?: string[]
  /** Error message (present when invalid) */
  error?: string
}

export interface UseCronValidationOptions {
  /** Number of next execution times to fetch (default: 5) */
  count?: number
  /** Additional React Query options */
  queryOptions?: Partial<UseQueryOptions<CronValidationResult>>
}

export interface UseCronValidationReturn {
  /** Validation result from the API */
  data: CronValidationResult | undefined
  /** Whether the query is currently loading */
  isLoading: boolean
  /** Whether the query errored */
  isError: boolean
  /** The error object if the query failed */
  error: Error | null
  /** Normalized error message for UI display */
  errorMessage: string | null
}

// -- Configuration -----------------------------------------------------------

/** Debounce delay — 300ms balances responsiveness vs API spam. */
const DEBOUNCE_DELAY_MS = 300

/** Cron validation results are deterministic, so 1 min stale time is fine. */
const STALE_TIME_MS = 60 * 1000

// -- Hook --------------------------------------------------------------------

/**
 * Hook for validating cron expressions with debouncing.
 *
 * @param expression - Cron expression to validate (e.g., "0 * * * *")
 * @param options - Optional count and query overrides
 */
export function useCronValidation(
  expression: string,
  options: UseCronValidationOptions = {},
): UseCronValidationReturn {
  const { count = 5, queryOptions = {} } = options

  // Debounce the expression to avoid excessive API calls
  const [debouncedExpression, setDebouncedExpression] = useState(expression)

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedExpression(expression)
    }, DEBOUNCE_DELAY_MS)

    return () => clearTimeout(timer)
  }, [expression])

  const query = useQuery<CronValidationResult>({
    queryKey: QUERY_KEYS.CRON_VALIDATION(debouncedExpression),
    queryFn: () => validateCronExpression(debouncedExpression, count),
    enabled: Boolean(debouncedExpression?.trim()),
    staleTime: STALE_TIME_MS,
    ...queryOptions,
  })

  // Normalize error messages for consistent UX
  const getErrorMessage = (): string | null => {
    if (query.isError) {
      const serverError = (query.error as { response?: { data?: { error?: string } } })
        ?.response?.data?.error
      if (serverError) return serverError
      if (query.error?.message) return `Validation failed: ${query.error.message}`
      return 'Unable to validate expression. Please try again.'
    }
    if (query.data?.valid === false) {
      return query.data.error || 'Invalid cron expression'
    }
    return null
  }

  return {
    data: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    errorMessage: getErrorMessage(),
  }
}

export default useCronValidation
```

**Step 2: Run tsc**

Run: `cd webui/frontend && npx tsc --noEmit`
Expected: No new errors

**Step 3: Run existing component tests** (they import via the component which imports the hook)

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ExpertMode/__tests__/CronExpressionInput.test.jsx`
Expected: All 21 tests pass

**Step 4: Commit**

```bash
git add src/hooks/useCronValidation.ts
git rm src/hooks/useCronValidation.js
git commit -m "refactor(#451): migrate useCronValidation hook to TypeScript"
```

---

### Task 4: Migrate CronExpressionInput component to TypeScript

**Files:**
- Rename: `src/components/scheduler/ExpertMode/CronExpressionInput.jsx` → `CronExpressionInput.tsx`
- Modify: `src/components/scheduler/ExpertMode/index.js` (barrel export)

**Context:** Pure controlled component. Add typed props interface, remove PropTypes import. No internal RHF. The existing behavior stays identical.

**Step 1: Rename and type the component**

Rename via `git mv`. Replace contents:

```tsx
import { useCronValidation } from '../../../hooks/useCronValidation'
import { CRON_PRESETS, CRON_HELP } from './constants'

// -- Types -------------------------------------------------------------------

export interface CronExpressionInputProps {
  /** Current cron expression value */
  value?: string
  /** Callback when expression changes */
  onChange: (value: string) => void
  /** Whether the input is disabled */
  disabled?: boolean
}

// -- Component ---------------------------------------------------------------

/**
 * CronExpressionInput — cron expression editor with real-time API validation.
 *
 * Features:
 * - Real-time validation with debounced API calls (via useCronValidation)
 * - Quick preset buttons for common patterns
 * - Visual success/error indicators
 * - Human-readable description of cron expression
 * - Next N execution times preview
 * - Format help text and field reference
 */
export default function CronExpressionInput({
  value = '',
  onChange,
  disabled = false,
}: CronExpressionInputProps) {
  // Validate the expression with debouncing
  const { data: validation, isLoading, errorMessage } = useCronValidation(value)

  /** Handle input change */
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(e.target.value)
  }

  /** Handle preset button click */
  const handlePresetClick = (expression: string) => {
    onChange(expression)
  }

  /** Format execution time for display */
  const formatExecutionTime = (isoTime: string): string => {
    try {
      const date = new Date(isoTime)
      return date.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return isoTime
    }
  }

  // Determine validation state
  const isValid = validation?.valid === true
  const isInvalid = validation?.valid === false
  const showValidation = value.trim() && validation && !isLoading

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <label
          htmlFor="cron-expression"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Cron Expression
        </label>

        {/* Input field with validation styling */}
        <div className="relative">
          <input
            id="cron-expression"
            type="text"
            value={value}
            onChange={handleChange}
            disabled={disabled}
            placeholder="e.g., 0 21 * * *"
            className={`
              w-full rounded-md border px-3 py-2 font-mono text-sm
              bg-white dark:bg-gray-800 text-gray-900 dark:text-white
              focus:ring-2 focus:ring-blue-500 focus:border-transparent
              disabled:opacity-50 disabled:cursor-not-allowed
              ${
                showValidation
                  ? isValid
                    ? 'border-green-500 dark:border-green-400'
                    : 'border-red-500 dark:border-red-400'
                  : 'border-gray-300 dark:border-gray-600'
              }
            `}
            aria-label="Cron expression input"
            aria-invalid={isInvalid}
            aria-describedby="cron-help cron-validation"
          />

          {/* Validation status icon */}
          {showValidation && !isLoading && (
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
              {isValid ? (
                <svg
                  className="h-5 w-5 text-green-500 dark:text-green-400"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                  aria-label="Valid expression"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clipRule="evenodd"
                  />
                </svg>
              ) : (
                <svg
                  className="h-5 w-5 text-red-500 dark:text-red-400"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                  aria-label="Invalid expression"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
            </div>
          )}

          {/* Loading indicator */}
          {isLoading && (
            <div
              className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none"
              aria-label="Validating"
            >
              <svg
                className="animate-spin h-5 w-5 text-gray-400 dark:text-gray-500"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            </div>
          )}
        </div>

        {/* Format help text */}
        <p
          id="cron-help"
          className="mt-1 text-xs text-gray-500 dark:text-gray-400 font-mono"
        >
          Format: {CRON_HELP.format} &bull; {CRON_HELP.special}
        </p>
      </div>

      {/* Validation message */}
      {showValidation && (
        <div id="cron-validation">
          {isValid ? (
            <div className="space-y-2">
              {/* Human-readable description */}
              <p className="text-sm text-green-600 dark:text-green-400 font-medium">
                {validation.description}
              </p>

              {/* Next execution times */}
              {validation.next_executions && validation.next_executions.length > 0 && (
                <div>
                  <p className="text-xs text-gray-700 dark:text-gray-300 font-medium mb-1">
                    Next executions:
                  </p>
                  <ul className="space-y-1">
                    {validation.next_executions.map((time) => (
                      <li
                        key={time}
                        className="text-xs text-gray-600 dark:text-gray-400 font-mono"
                      >
                        {formatExecutionTime(time)}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-red-600 dark:text-red-400">
              {errorMessage}
            </p>
          )}
        </div>
      )}

      {/* Preset buttons */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Quick presets:
        </label>
        <div className="flex flex-wrap gap-2">
          {CRON_PRESETS.map((preset) => (
            <button
              key={preset.expression}
              type="button"
              onClick={() => handlePresetClick(preset.expression)}
              disabled={disabled}
              className={`
                px-3 py-1.5 rounded-md text-xs font-medium
                transition-colors duration-150
                focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
                dark:focus:ring-offset-gray-800
                ${
                  value === preset.expression
                    ? 'bg-blue-500 text-white hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
                }
                ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              `}
              aria-label={`Set expression to ${preset.label}`}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      {/* Field reference */}
      <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
        <p className="text-xs text-gray-700 dark:text-gray-300 font-medium mb-2">
          Field reference:
        </p>
        <div className="grid grid-cols-2 gap-2">
          {CRON_HELP.fields.map((field) => (
            <div key={field.name} className="text-xs">
              <span className="font-medium text-gray-700 dark:text-gray-300">
                {field.name}:
              </span>{' '}
              <span className="text-gray-600 dark:text-gray-400 font-mono">
                {field.range}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
```

**Step 2: Update barrel export**

In `src/components/scheduler/ExpertMode/index.js`, the line `export { default as CronExpressionInput } from './CronExpressionInput'` resolves to `.tsx` automatically via Vite bundler resolution. No change needed unless tsc complains — in that case, verify the barrel still resolves correctly.

**Step 3: Run tsc**

Run: `cd webui/frontend && npx tsc --noEmit`
Expected: No new errors

**Step 4: Run existing component tests**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ExpertMode/__tests__/CronExpressionInput.test.jsx`
Expected: All 21 tests pass (same behavior, just typed)

**Step 5: Commit**

```bash
git add src/components/scheduler/ExpertMode/CronExpressionInput.tsx
git rm src/components/scheduler/ExpertMode/CronExpressionInput.jsx
git commit -m "feat(#451): migrate CronExpressionInput to TypeScript"
```

---

### Task 5: Migrate component tests to TypeScript

**Files:**
- Rename: `src/components/scheduler/ExpertMode/__tests__/CronExpressionInput.test.jsx` → `CronExpressionInput.test.tsx`

**Context:** Migrate the existing 21 tests from JSX to TSX. Add type imports, type the mock function, and type the renderComponent helper. No new behavioral tests — the component behavior is unchanged.

**Step 1: Rename and type the test file**

Rename via `git mv`. Update the file:

Changes needed:
1. Import `CronExpressionInputProps` type from the component
2. Type `mockOnChange` as `vi.fn<(value: string) => void>`
3. Type the `renderComponent` props parameter using `Partial<CronExpressionInputProps>`
4. Type the mock API response objects with `CronValidationResult` from the hook
5. Type the `resolvePromise` variable in the loading test

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import CronExpressionInput from '../CronExpressionInput'
import type { CronExpressionInputProps } from '../CronExpressionInput'
import type { CronValidationResult } from '../../../../hooks/useCronValidation'
import * as cronApi from '../../../../utils/cronApi'

// Mock the cronApi module
vi.mock('../../../../utils/cronApi')

const mockCronApi = cronApi as { validateCronExpression: ReturnType<typeof vi.fn> }

describe('CronExpressionInput', () => {
  let mockOnChange: ReturnType<typeof vi.fn<(value: string) => void>>
  let queryClient: QueryClient

  beforeEach(() => {
    mockOnChange = vi.fn<(value: string) => void>()
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    })
    vi.clearAllMocks()
  })

  /**
   * Helper to render component with QueryClient wrapper
   */
  function renderComponent(overrides: Partial<CronExpressionInputProps> = {}) {
    const defaultProps: CronExpressionInputProps = {
      value: '',
      onChange: mockOnChange,
      ...overrides,
    }

    return render(
      <QueryClientProvider client={queryClient}>
        <CronExpressionInput {...defaultProps} />
      </QueryClientProvider>,
    )
  }

  // ... (all existing test bodies stay identical, just update mock calls
  //  from cronApi.validateCronExpression to mockCronApi.validateCronExpression
  //  and type the mock response objects as CronValidationResult)
```

The test bodies are identical to the .jsx version. The only changes are:
- Import types
- Type `mockOnChange`, `queryClient`
- Type `renderComponent` parameter
- Cast `cronApi` mock for type-safe `.mockResolvedValue()` calls
- Type `resolvePromise` in the loading test as `(value: CronValidationResult) => void`

**Step 2: Run the migrated tests**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ExpertMode/__tests__/CronExpressionInput.test.tsx`
Expected: All 21 tests pass

**Step 3: Run tsc**

Run: `cd webui/frontend && npx tsc --noEmit`
Expected: No new errors

**Step 4: Commit**

```bash
git add src/components/scheduler/ExpertMode/__tests__/CronExpressionInput.test.tsx
git rm src/components/scheduler/ExpertMode/__tests__/CronExpressionInput.test.jsx
git commit -m "test(#451): migrate CronExpressionInput tests to TypeScript"
```

---

### Task 6: Final verification

**Step 1: Run tsc across the project**

Run: `cd webui/frontend && npx tsc --noEmit`
Expected: Zero errors

**Step 2: Run all related tests**

Run: `cd webui/frontend && npx vitest run src/schemas/scheduler/__tests__/cron.test.ts src/components/scheduler/ExpertMode/__tests__/CronExpressionInput.test.tsx`
Expected: All pass (schema + component)

**Step 3: Run the full frontend test suite**

Run: `cd webui/frontend && npx vitest run`
Expected: All tests pass, no regressions. Pay attention to:
- `TriggerForm.test.jsx` (imports CronExpressionInput — verify mock still works)
- `CronExpressionErrorBoundary.test.jsx` (sibling component)

**Step 4: Verify no stale .js/.jsx files remain**

Run: `ls src/components/scheduler/ExpertMode/CronExpressionInput.jsx src/components/scheduler/ExpertMode/constants.js src/hooks/useCronValidation.js 2>&1`
Expected: All "No such file" — the old files are gone

**Step 5: Commit if any fixups needed, otherwise done**

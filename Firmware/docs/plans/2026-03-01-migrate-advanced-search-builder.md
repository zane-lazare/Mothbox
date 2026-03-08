# AdvancedSearchBuilder Migration Implementation Plan

**Goal:** Migrate AdvancedSearchBuilder from manual useState + PropTypes + .jsx to react-hook-form + Zod + TypeScript (.tsx) with useFieldArray for dynamic conditions.

**Architecture:** Thin RHF wrapper — useForm + useFieldArray replaces useState, Zod schema validates form shape, existing generateQuery and parseInitialQuery preserved as typed pure functions. Modal (uncontrolled) pattern per design doc. No new UX behaviors.

**Tech Stack:** React 19, react-hook-form 7.x, Zod 4.x, @hookform/resolvers 5.x, Vitest, Testing Library

**Design doc:** `docs/plans/2026-03-01-migrate-advanced-search-builder-design.md`

---

## Context

### Current component
- `src/components/gallery/AdvancedSearchBuilder.jsx` (424 LOC)
- Visual query builder modal: dynamic condition rows (field/operator/value), boolean AND/OR, date range, query preview
- Uses 4x `useState` for conditions array, booleanOperator, dateFrom, dateTo
- `generateQuery()` transforms state to FTS5 query string
- `parseInitialQuery()` reverse-parses query string into state (regex-based)
- 38 existing tests in `src/components/gallery/__tests__/AdvancedSearchBuilder.test.jsx`

### Existing patterns to follow
- Schema: `src/schemas/tag.ts` — uses `z.array(z.object({...}))` with `useFieldArray`
- Schema tests: `src/schemas/__tests__/camera-preset.test.ts` — `safeParse` + error message assertions
- Barrel: `src/schemas/index.ts` — re-exports schemas, types, and constants

### Key files to read before starting
- Design doc (above)
- `src/schemas/tag.ts` — array schema pattern
- `src/schemas/__tests__/camera-preset.test.ts` — test pattern
- `src/components/gallery/AdvancedSearchBuilder.jsx` — current implementation
- `src/components/gallery/__tests__/AdvancedSearchBuilder.test.jsx` — current tests

---

## Task 1: Zod Schema and Tests

**Files:**
- Create: `src/schemas/search.ts`
- Create: `src/schemas/__tests__/search.test.ts`

### Step 1: Write the schema tests

Create `src/schemas/__tests__/search.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import {
  advancedSearchSchema,
  searchConditionSchema,
  SEARCH_FIELDS,
  SEARCH_OPERATORS,
  BOOLEAN_OPERATORS,
} from '../search'

/** Return the first Zod issue message from a failed parse, or null. */
function firstError(
  result: { success: boolean; error?: { issues: { message: string }[] } },
): string | null {
  if (result.success) return null
  return result.error?.issues[0]?.message ?? null
}

describe('constants', () => {
  it('SEARCH_FIELDS contains all six field options', () => {
    expect(SEARCH_FIELDS).toEqual(['tags', 'species', 'name', 'filename', 'notes', 'any'])
  })

  it('SEARCH_OPERATORS contains all four operators', () => {
    expect(SEARCH_OPERATORS).toEqual(['contains', 'equals', 'starts_with', 'excludes'])
  })

  it('BOOLEAN_OPERATORS contains AND and OR', () => {
    expect(BOOLEAN_OPERATORS).toEqual(['AND', 'OR'])
  })
})

describe('searchConditionSchema', () => {
  const validCondition = { field: 'tags', operator: 'contains', value: 'moth' }

  it('accepts valid condition', () => {
    const result = searchConditionSchema.safeParse(validCondition)
    expect(result.success).toBe(true)
  })

  it('accepts empty value string', () => {
    const result = searchConditionSchema.safeParse({ ...validCondition, value: '' })
    expect(result.success).toBe(true)
  })

  it.each(SEARCH_FIELDS)('accepts field "%s"', (field) => {
    const result = searchConditionSchema.safeParse({ ...validCondition, field })
    expect(result.success).toBe(true)
  })

  it.each(SEARCH_OPERATORS)('accepts operator "%s"', (operator) => {
    const result = searchConditionSchema.safeParse({ ...validCondition, operator })
    expect(result.success).toBe(true)
  })

  it('rejects invalid field', () => {
    const result = searchConditionSchema.safeParse({ ...validCondition, field: 'invalid' })
    expect(result.success).toBe(false)
  })

  it('rejects invalid operator', () => {
    const result = searchConditionSchema.safeParse({ ...validCondition, operator: 'like' })
    expect(result.success).toBe(false)
  })

  it('rejects missing field', () => {
    const { field, ...rest } = validCondition
    const result = searchConditionSchema.safeParse(rest)
    expect(result.success).toBe(false)
  })

  it('rejects missing operator', () => {
    const { operator, ...rest } = validCondition
    const result = searchConditionSchema.safeParse(rest)
    expect(result.success).toBe(false)
  })

  it('rejects missing value', () => {
    const { value, ...rest } = validCondition
    const result = searchConditionSchema.safeParse(rest)
    expect(result.success).toBe(false)
  })

  it('rejects non-string value', () => {
    const result = searchConditionSchema.safeParse({ ...validCondition, value: 42 })
    expect(result.success).toBe(false)
  })
})

describe('advancedSearchSchema', () => {
  const validData = {
    conditions: [{ field: 'tags', operator: 'contains', value: 'moth' }],
    booleanOperator: 'AND',
    dateFrom: '',
    dateTo: '',
  }

  it('accepts valid form data', () => {
    const result = advancedSearchSchema.safeParse(validData)
    expect(result.success).toBe(true)
  })

  it('accepts multiple conditions', () => {
    const result = advancedSearchSchema.safeParse({
      ...validData,
      conditions: [
        { field: 'tags', operator: 'contains', value: 'moth' },
        { field: 'species', operator: 'equals', value: 'Actias luna' },
      ],
    })
    expect(result.success).toBe(true)
  })

  it('accepts OR boolean operator', () => {
    const result = advancedSearchSchema.safeParse({ ...validData, booleanOperator: 'OR' })
    expect(result.success).toBe(true)
  })

  it('accepts date range strings', () => {
    const result = advancedSearchSchema.safeParse({
      ...validData,
      dateFrom: '2024-01-01',
      dateTo: '2024-12-31',
    })
    expect(result.success).toBe(true)
  })

  it('rejects empty conditions array', () => {
    const result = advancedSearchSchema.safeParse({ ...validData, conditions: [] })
    expect(result.success).toBe(false)
    expect(firstError(result)).toMatch(/too_small|at least/i)
  })

  it('rejects invalid boolean operator', () => {
    const result = advancedSearchSchema.safeParse({ ...validData, booleanOperator: 'XOR' })
    expect(result.success).toBe(false)
  })

  it('rejects missing conditions', () => {
    const { conditions, ...rest } = validData
    const result = advancedSearchSchema.safeParse(rest)
    expect(result.success).toBe(false)
  })

  it('rejects missing booleanOperator', () => {
    const { booleanOperator, ...rest } = validData
    const result = advancedSearchSchema.safeParse(rest)
    expect(result.success).toBe(false)
  })

  it('rejects condition with invalid field inside array', () => {
    const result = advancedSearchSchema.safeParse({
      ...validData,
      conditions: [{ field: 'bogus', operator: 'contains', value: 'x' }],
    })
    expect(result.success).toBe(false)
  })
})
```

### Step 2: Run tests to verify they fail

Run: `npx vitest run src/schemas/__tests__/search.test.ts`
Expected: FAIL — module `../search` does not exist

### Step 3: Write the schema implementation

Create `src/schemas/search.ts`:

```typescript
import { z } from 'zod'

/** Valid search field identifiers matching FIELD_OPTIONS in AdvancedSearchBuilder. */
export const SEARCH_FIELDS = ['tags', 'species', 'name', 'filename', 'notes', 'any'] as const

/** Operator options for search conditions. */
export const SEARCH_OPERATORS = ['contains', 'equals', 'starts_with', 'excludes'] as const

/** Boolean operators for combining conditions. */
export const BOOLEAN_OPERATORS = ['AND', 'OR'] as const

/** Schema for a single search condition row (field + operator + value). */
export const searchConditionSchema = z.object({
  field: z.enum(SEARCH_FIELDS),
  operator: z.enum(SEARCH_OPERATORS),
  value: z.string(),
})

/**
 * Schema for the AdvancedSearchBuilder form.
 * Intentionally permissive on value/date strings — the component generates
 * a query string for the FTS5 backend; server handles semantic validation.
 */
export const advancedSearchSchema = z.object({
  conditions: z.array(searchConditionSchema).min(1),
  booleanOperator: z.enum(BOOLEAN_OPERATORS),
  dateFrom: z.string(),
  dateTo: z.string(),
})

export type SearchCondition = z.infer<typeof searchConditionSchema>
export type AdvancedSearchFormData = z.infer<typeof advancedSearchSchema>
```

### Step 4: Run tests to verify they pass

Run: `npx vitest run src/schemas/__tests__/search.test.ts`
Expected: All tests PASS

### Step 5: Commit

```bash
git add src/schemas/search.ts src/schemas/__tests__/search.test.ts
git commit -m "feat(#452): add Zod schema and tests for advanced search"
```

---

## Task 2: Update barrel exports

**Files:**
- Modify: `src/schemas/index.ts`

### Step 1: Add search exports to barrel

Append to `src/schemas/index.ts`:

```typescript
export {
  advancedSearchSchema,
  searchConditionSchema,
  SEARCH_FIELDS,
  SEARCH_OPERATORS,
  BOOLEAN_OPERATORS,
} from './search'
export type { AdvancedSearchFormData, SearchCondition } from './search'
```

### Step 2: Verify TypeScript compiles

Run: `npx tsc --noEmit`
Expected: No errors

### Step 3: Commit

```bash
git add src/schemas/index.ts
git commit -m "refactor(#452): add search schema to barrel exports"
```

---

## Task 3: Migrate component to TypeScript with RHF

**Files:**
- Rename: `src/components/gallery/AdvancedSearchBuilder.jsx` → `.tsx`
- Reference: `src/schemas/search.ts`

### Step 1: Rename the file

```bash
git mv src/components/gallery/AdvancedSearchBuilder.jsx src/components/gallery/AdvancedSearchBuilder.tsx
```

### Step 2: Rewrite the component

Replace the full content of `src/components/gallery/AdvancedSearchBuilder.tsx`:

```tsx
import { useForm, useFieldArray, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { XMarkIcon } from '@heroicons/react/24/outline'
import { Z_INDEX } from '../../constants/config'
import {
  advancedSearchSchema,
  type AdvancedSearchFormData,
  type SearchCondition,
} from '../../schemas/search'

// -- Constants (component-local, single consumer) ----------------------------

interface FieldOption {
  readonly value: SearchCondition['field']
  readonly label: string
  readonly queryPrefix: string
}

const FIELD_OPTIONS: readonly FieldOption[] = [
  { value: 'tags', label: 'Tags', queryPrefix: 'tag' },
  { value: 'species', label: 'Species', queryPrefix: 'species' },
  { value: 'name', label: 'Common Name', queryPrefix: 'name' },
  { value: 'filename', label: 'Filename', queryPrefix: 'filename' },
  { value: 'notes', label: 'Notes', queryPrefix: 'notes' },
  { value: 'any', label: 'Any Field', queryPrefix: '' },
]

const OPERATOR_OPTIONS = [
  { value: 'contains', label: 'contains' },
  { value: 'equals', label: 'equals' },
  { value: 'starts_with', label: 'starts with' },
  { value: 'excludes', label: 'excludes' },
] as const

const BOOLEAN_OPTIONS = [
  { value: 'AND', label: 'AND' },
  { value: 'OR', label: 'OR' },
] as const

// -- Default values ----------------------------------------------------------

const DEFAULT_VALUES: AdvancedSearchFormData = {
  conditions: [{ field: 'tags', operator: 'contains', value: '' }],
  booleanOperator: 'AND',
  dateFrom: '',
  dateTo: '',
}

// -- Pure functions ----------------------------------------------------------

/** Transform form data into an FTS5 query string. */
function generateQuery(data: AdvancedSearchFormData): string {
  const conditionQueries = data.conditions
    .filter((c) => c.value.trim())
    .map((condition) => {
      const field = FIELD_OPTIONS.find((f) => f.value === condition.field)
      const prefix = field?.queryPrefix || ''
      let queryValue = condition.value.trim()

      switch (condition.operator) {
        case 'equals':
          queryValue = `"${queryValue}"`
          break
        case 'starts_with':
          queryValue = `${queryValue}*`
          break
        case 'excludes':
          return prefix ? `NOT ${prefix}:${queryValue}` : `NOT ${queryValue}`
        case 'contains':
        default:
          break
      }

      return prefix ? `${prefix}:${queryValue}` : queryValue
    })

  let query = conditionQueries.join(` ${data.booleanOperator} `)

  if (data.dateFrom && data.dateTo) {
    const dateQuery = `date:${data.dateFrom}..${data.dateTo}`
    query = query ? `${query} AND ${dateQuery}` : dateQuery
  }

  return query
}

/** Parse an FTS5 query string into form default values. */
function parseInitialQuery(query: string): AdvancedSearchFormData {
  const result: AdvancedSearchFormData = { ...DEFAULT_VALUES, conditions: [] }
  let remainingQuery = query

  // Extract date range filter (date:YYYY-MM-DD..YYYY-MM-DD)
  const dateRangePattern = /date:(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})/
  const dateRangeMatch = remainingQuery.match(dateRangePattern)
  if (dateRangeMatch) {
    result.dateFrom = dateRangeMatch[1]
    result.dateTo = dateRangeMatch[2]
    remainingQuery = remainingQuery.replace(dateRangePattern, '').trim()
  }

  // Handle comparison operators (date:>=YYYY-MM-DD, date:<=YYYY-MM-DD)
  const dateComparePattern = /date:([<>]=?)(\d{4}-\d{2}-\d{2})/
  const dateCompareMatch = remainingQuery.match(dateComparePattern)
  if (dateCompareMatch) {
    const [, operator, dateValue] = dateCompareMatch
    if (operator === '>=' || operator === '>') {
      result.dateFrom = dateValue
    } else if (operator === '<=' || operator === '<') {
      result.dateTo = dateValue
    }
    remainingQuery = remainingQuery.replace(dateComparePattern, '').trim()
  }

  // Remove trailing/leading AND/OR
  remainingQuery = remainingQuery.replace(/\s+(AND|OR)\s*$/i, '').trim()
  remainingQuery = remainingQuery.replace(/^\s*(AND|OR)\s+/i, '').trim()

  // Parse field:value patterns
  const fieldPattern = /(\w+):([^\s]+)/g
  const matches = [...remainingQuery.matchAll(fieldPattern)]

  const fieldMapping: Record<string, SearchCondition['field']> = {
    tag: 'tags',
    tags: 'tags',
    species: 'species',
    name: 'name',
    filename: 'filename',
    notes: 'notes',
  }

  if (matches.length > 0) {
    const parsedConditions: SearchCondition[] = matches
      .filter((match) => match[1] !== 'date')
      .map((match) => {
        const [, field, value] = match
        const mappedField = fieldMapping[field] || 'any'
        return { field: mappedField, operator: 'contains' as const, value }
      })

    if (parsedConditions.length > 0) {
      result.conditions = parsedConditions
    }
  } else if (!dateRangeMatch && !dateCompareMatch) {
    if (remainingQuery.trim()) {
      result.conditions = [{ field: 'any', operator: 'contains', value: remainingQuery.trim() }]
    }
  }

  // Ensure at least one condition
  if (result.conditions.length === 0) {
    result.conditions = [{ field: 'tags', operator: 'contains', value: '' }]
  }

  return result
}

// -- Component ---------------------------------------------------------------

export interface AdvancedSearchBuilderProps {
  onQueryChange: (query: string) => void
  onClose: () => void
  initialQuery?: string
}

export function AdvancedSearchBuilder({
  onQueryChange,
  onClose,
  initialQuery = '',
}: AdvancedSearchBuilderProps) {
  const defaultValues = initialQuery ? parseInitialQuery(initialQuery) : DEFAULT_VALUES

  const { register, control, reset } = useForm<AdvancedSearchFormData>({
    resolver: zodResolver(advancedSearchSchema),
    defaultValues,
    mode: 'onBlur',
  })

  const { fields, append, remove } = useFieldArray({ control, name: 'conditions' })

  // Watch all form values for query preview and apply
  const watchedValues = useWatch({ control }) as AdvancedSearchFormData

  const queryPreview = generateQuery(watchedValues)

  const handleApply = () => {
    onQueryChange?.(queryPreview)
  }

  const clearAll = () => {
    reset(DEFAULT_VALUES)
  }

  return (
    <div className={`fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center ${Z_INDEX.MODAL}`}>
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            Advanced Search
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700
                       focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <XMarkIcon className="w-6 h-6 text-gray-500 dark:text-gray-400" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Conditions */}
          <div className="space-y-4">
            {fields.map((item, index) => (
              <div key={item.id}>
                {/* Condition row */}
                <div className="flex items-center gap-2">
                  {/* Field select */}
                  <select
                    aria-label="Field"
                    {...register(`conditions.${index}.field`)}
                    className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                               focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                               bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  >
                    {FIELD_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>

                  {/* Operator select */}
                  <select
                    aria-label="Operator"
                    {...register(`conditions.${index}.operator`)}
                    className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                               focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                               bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  >
                    {OPERATOR_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>

                  {/* Value input */}
                  <input
                    type="text"
                    aria-label="Value"
                    {...register(`conditions.${index}.value`)}
                    placeholder="Enter value..."
                    className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                               focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                               bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                               placeholder-gray-500 dark:placeholder-gray-400"
                  />

                  {/* Remove button (only show if more than one condition) */}
                  {fields.length > 1 && (
                    <button
                      type="button"
                      onClick={() => remove(index)}
                      aria-label="Remove"
                      className="p-2 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20
                                 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                    >
                      <XMarkIcon className="w-5 h-5" />
                    </button>
                  )}
                </div>

                {/* Boolean operator (show between conditions) */}
                {index < fields.length - 1 && (
                  <div className="flex items-center justify-center my-2">
                    <select
                      aria-label="Combine with"
                      {...register('booleanOperator')}
                      className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-md
                                 focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                                 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
                                 text-sm font-medium"
                    >
                      {BOOLEAN_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Add Condition button */}
          <div>
            <button
              type="button"
              onClick={() => append({ field: 'tags', operator: 'contains', value: '' })}
              className="px-4 py-2 text-sm font-medium text-blue-600 dark:text-blue-400
                         hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-md
                         focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              + Add Condition
            </button>
          </div>

          {/* Date Range */}
          <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
            <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">
              Date Range (Optional)
            </h3>
            <div className="flex items-center gap-4">
              <div className="flex-1">
                <label
                  htmlFor="date-from"
                  className="block text-sm text-gray-700 dark:text-gray-300 mb-1"
                >
                  From Date
                </label>
                <input
                  type="date"
                  id="date-from"
                  aria-label="From Date"
                  {...register('dateFrom')}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                             focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                             bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                />
              </div>
              <div className="flex-1">
                <label
                  htmlFor="date-to"
                  className="block text-sm text-gray-700 dark:text-gray-300 mb-1"
                >
                  To Date
                </label>
                <input
                  type="date"
                  id="date-to"
                  aria-label="To Date"
                  {...register('dateTo')}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                             focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                             bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                />
              </div>
            </div>
          </div>

          {/* Query Preview */}
          <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
            <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
              Generated Query
            </h3>
            <div
              data-testid="query-preview"
              className="px-4 py-3 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700
                         rounded-md font-mono text-sm text-gray-900 dark:text-gray-100 break-all"
            >
              {queryPreview || <span className="text-gray-400">No query yet...</span>}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t border-gray-200 dark:border-gray-700">
          <button
            type="button"
            onClick={clearAll}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300
                       hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md
                       focus:outline-none focus:ring-2 focus:ring-gray-500"
          >
            Clear All
          </button>
          <button
            type="button"
            onClick={handleApply}
            className="px-6 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700
                       rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500
                       disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={!queryPreview}
          >
            Apply Search
          </button>
        </div>
      </div>
    </div>
  )
}
```

### Step 3: Verify TypeScript compiles

Run: `npx tsc --noEmit`
Expected: No errors

### Step 4: Commit

```bash
git add src/components/gallery/AdvancedSearchBuilder.tsx
git commit -m "refactor(#452): migrate AdvancedSearchBuilder to TypeScript with RHF"
```

---

## Task 4: Migrate Tests to TypeScript

**Files:**
- Rename: `src/components/gallery/__tests__/AdvancedSearchBuilder.test.jsx` → `.test.tsx`

### Step 1: Rename the test file

```bash
git mv src/components/gallery/__tests__/AdvancedSearchBuilder.test.jsx src/components/gallery/__tests__/AdvancedSearchBuilder.test.tsx
```

### Step 2: Update imports

Only change needed: import path now resolves to `.tsx`. The test file itself needs minimal changes:

- Add `import type` where appropriate (if any type imports needed)
- The existing tests interact via `screen.getByLabelText`, `userEvent`, etc. — all behavior-based, no type changes needed

If TypeScript complains about any mock types, add minimal type annotations. The tests should work as-is since they test rendered behavior, not internal state.

### Step 3: Run all component tests

Run: `npx vitest run src/components/gallery/__tests__/AdvancedSearchBuilder.test.tsx`
Expected: All 38 tests PASS

### Step 4: Run schema tests too

Run: `npx vitest run src/schemas/__tests__/search.test.ts`
Expected: All tests PASS

### Step 5: Verify no stale files remain

```bash
ls src/components/gallery/AdvancedSearchBuilder.jsx 2>/dev/null && echo "STALE" || echo "OK"
ls src/components/gallery/__tests__/AdvancedSearchBuilder.test.jsx 2>/dev/null && echo "STALE" || echo "OK"
```
Expected: Both print "OK"

### Step 6: Commit

```bash
git add src/components/gallery/__tests__/AdvancedSearchBuilder.test.tsx
git commit -m "test(#452): migrate AdvancedSearchBuilder tests to TypeScript"
```

---

## Task 5: Final Verification

### Step 1: TypeScript check

Run: `npx tsc --noEmit`
Expected: Clean (no errors)

### Step 2: ESLint check

Run: `npx eslint src/schemas/search.ts src/components/gallery/AdvancedSearchBuilder.tsx src/components/gallery/__tests__/AdvancedSearchBuilder.test.tsx`
Expected: No errors (warnings about pre-existing issues in other files are OK)

### Step 3: Run all related tests

Run: `npx vitest run src/schemas/__tests__/search.test.ts src/components/gallery/__tests__/AdvancedSearchBuilder.test.tsx`
Expected: All tests PASS

### Step 4: Run full frontend test suite

Run: `npx vitest run`
Expected: All tests PASS, no regressions

### Step 5: Verify no stale .jsx files

```bash
ls src/components/gallery/AdvancedSearchBuilder.jsx 2>/dev/null && echo "STALE" || echo "OK"
ls src/components/gallery/__tests__/AdvancedSearchBuilder.test.jsx 2>/dev/null && echo "STALE" || echo "OK"
```
Expected: Both "OK"

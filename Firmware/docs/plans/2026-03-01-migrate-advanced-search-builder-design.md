# AdvancedSearchBuilder Migration Design

**Issue**: #452
**Date**: 2026-03-01
**Status**: Design approved

## Goal

Migrate AdvancedSearchBuilder from manual `useState` + PropTypes + `.jsx` to `react-hook-form` + Zod + TypeScript (`.tsx`), using `useFieldArray` for dynamic condition rows.

## Architecture

**Pattern**: Modal (uncontrolled) — form owns state, calls parent `onQueryChange` on apply.

**Approach**: Thin RHF wrapper. Replace `useState` with `useForm` + `useFieldArray`. Preserve existing `generateQuery` and `parseInitialQuery` logic as typed pure functions. No new UX behaviors (no inline validation errors). Zod schema validates form shape; server validates query semantics.

## Schema (`src/schemas/search.ts`)

```typescript
import { z } from 'zod'

export const SEARCH_FIELDS = ['tags', 'species', 'name', 'filename', 'notes', 'any'] as const
export const SEARCH_OPERATORS = ['contains', 'equals', 'starts_with', 'excludes'] as const
export const BOOLEAN_OPERATORS = ['AND', 'OR'] as const

export const searchConditionSchema = z.object({
  field: z.enum(SEARCH_FIELDS),
  operator: z.enum(SEARCH_OPERATORS),
  value: z.string(),
})

export const advancedSearchSchema = z.object({
  conditions: z.array(searchConditionSchema).min(1),
  booleanOperator: z.enum(BOOLEAN_OPERATORS),
  dateFrom: z.string(),
  dateTo: z.string(),
})

export type SearchCondition = z.infer<typeof searchConditionSchema>
export type AdvancedSearchFormData = z.infer<typeof advancedSearchSchema>
```

Intentionally permissive on value/date strings — the component generates a query string for the FTS5 backend; server handles semantic validation.

## Component Changes (`AdvancedSearchBuilder.tsx`)

### State management replacement

| Before (useState) | After (react-hook-form) |
|---|---|
| `useState([{field, operator, value}])` | `useFieldArray({ control, name: 'conditions' })` |
| `useState('AND')` | `register('booleanOperator')` |
| `useState('')` (dateFrom) | `register('dateFrom')` |
| `useState('')` (dateTo) | `register('dateTo')` |
| `addCondition()` → `setConditions([...])` | `append({ field: 'tags', operator: 'contains', value: '' })` |
| `removeCondition(i)` → `filter` | `remove(i)` |
| `updateCondition(i, updates)` → spread | `register(`conditions.${i}.field`)` etc. |
| `clearAll()` → reset all state | `reset(DEFAULT_VALUES)` |
| `generateQuery()` reads state | `generateQuery(watch())` reads form |

### Props interface

```typescript
export interface AdvancedSearchBuilderProps {
  onQueryChange: (query: string) => void
  onClose: () => void
  initialQuery?: string
}
```

### Pure functions (typed, logic unchanged)

- `generateQuery(data: AdvancedSearchFormData): string` — transforms form data to FTS5 query
- `parseInitialQuery(query: string): AdvancedSearchFormData` — parses query string into form defaults

### Query preview

`watch()` feeds `generateQuery()` for real-time preview, same as current behavior where `generateQuery` reads state on every render.

### Constants

`FIELD_OPTIONS`, `OPERATOR_OPTIONS`, `BOOLEAN_OPTIONS` stay in the component file with explicit types. Single consumer — not worth extracting.

## Test Changes (`AdvancedSearchBuilder.test.tsx`)

- Rename `.test.jsx` → `.test.tsx`
- Add type imports
- All 38 existing tests preserved (behavior unchanged)
- No new validation error tests (no new UX)

## Barrel export update (`src/schemas/index.ts`)

Add:
```typescript
export { advancedSearchSchema, searchConditionSchema, SEARCH_FIELDS, SEARCH_OPERATORS, BOOLEAN_OPERATORS } from './search'
export type { AdvancedSearchFormData, SearchCondition } from './search'
```

## What stays the same

- Modal UI structure and all Tailwind styling
- Query generation logic (operator transforms, field prefixes, date range syntax)
- Initial query parsing logic (regex patterns, field mapping)
- Apply button disabled when no query generated
- All 38 existing test assertions
- No new dependencies (react-hook-form, zod, @hookform/resolvers already installed)

## Files

| Action | Path |
|---|---|
| Create | `src/schemas/search.ts` |
| Create | `src/schemas/__tests__/search.test.ts` |
| Rename+Rewrite | `src/components/gallery/AdvancedSearchBuilder.jsx` → `.tsx` |
| Rename+Rewrite | `src/components/gallery/__tests__/AdvancedSearchBuilder.test.jsx` → `.test.tsx` |
| Modify | `src/schemas/index.ts` (add exports) |

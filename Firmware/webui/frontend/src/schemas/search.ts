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

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
    const { field: _field, ...rest } = validCondition
    const result = searchConditionSchema.safeParse(rest)
    expect(result.success).toBe(false)
  })

  it('rejects missing operator', () => {
    const { operator: _operator, ...rest } = validCondition
    const result = searchConditionSchema.safeParse(rest)
    expect(result.success).toBe(false)
  })

  it('rejects missing value', () => {
    const { value: _value, ...rest } = validCondition
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
    expect(firstError(result)).toMatch(/too.small|at least/i)
  })

  it('rejects invalid boolean operator', () => {
    const result = advancedSearchSchema.safeParse({ ...validData, booleanOperator: 'XOR' })
    expect(result.success).toBe(false)
  })

  it('rejects missing conditions', () => {
    const { conditions: _conditions, ...rest } = validData
    const result = advancedSearchSchema.safeParse(rest)
    expect(result.success).toBe(false)
  })

  it('rejects missing booleanOperator', () => {
    const { booleanOperator: _booleanOperator, ...rest } = validData
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

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

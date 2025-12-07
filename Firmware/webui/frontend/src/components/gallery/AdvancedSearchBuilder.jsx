import { useState, useEffect } from 'react'
import PropTypes from 'prop-types'
import { XMarkIcon } from '@heroicons/react/24/outline'
import { Z_INDEX } from '../../constants/config'

// Field options for the dropdown
const FIELD_OPTIONS = [
  { value: 'tags', label: 'Tags', queryPrefix: 'tag' },
  { value: 'species', label: 'Species', queryPrefix: 'species' },
  { value: 'name', label: 'Common Name', queryPrefix: 'name' },
  { value: 'filename', label: 'Filename', queryPrefix: 'filename' },
  { value: 'notes', label: 'Notes', queryPrefix: 'notes' },
  { value: 'any', label: 'Any Field', queryPrefix: '' },
]

// Operator options
const OPERATOR_OPTIONS = [
  { value: 'contains', label: 'contains' },
  { value: 'equals', label: 'equals' },
  { value: 'starts_with', label: 'starts with' },
  { value: 'excludes', label: 'excludes' },
]

// Boolean operator options
const BOOLEAN_OPTIONS = [
  { value: 'AND', label: 'AND' },
  { value: 'OR', label: 'OR' },
]

/**
 * Advanced Search Builder component
 *
 * Visual query builder that generates search syntax
 *
 * @param {Object} props
 * @param {function} props.onQueryChange - Called when query changes
 * @param {function} props.onClose - Called when builder is closed
 * @param {string} [props.initialQuery] - Initial query to parse
 */
export function AdvancedSearchBuilder({
  onQueryChange,
  onClose,
  initialQuery = ''
}) {
  // State for search conditions
  const [conditions, setConditions] = useState([
    { field: 'tags', operator: 'contains', value: '' }
  ])

  // State for boolean operator between conditions
  const [booleanOperator, setBooleanOperator] = useState('AND')

  // State for date range
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  // Parse initial query if provided
  useEffect(() => {
    if (initialQuery) {
      parseInitialQuery(initialQuery)
    }
  }, [initialQuery])

  // Parse initial query into conditions
  const parseInitialQuery = (query) => {
    let remainingQuery = query

    // First, extract and handle date range filter (date:YYYY-MM-DD..YYYY-MM-DD)
    const dateRangePattern = /date:(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})/
    const dateRangeMatch = remainingQuery.match(dateRangePattern)
    if (dateRangeMatch) {
      setDateFrom(dateRangeMatch[1])
      setDateTo(dateRangeMatch[2])
      remainingQuery = remainingQuery.replace(dateRangePattern, '').trim()
    }

    // Handle comparison operators (date:>=YYYY-MM-DD, date:<=YYYY-MM-DD, etc.)
    const dateComparePattern = /date:([<>]=?)(\d{4}-\d{2}-\d{2})/
    const dateCompareMatch = remainingQuery.match(dateComparePattern)
    if (dateCompareMatch) {
      const [, operator, dateValue] = dateCompareMatch
      // For comparison operators, set as single boundary
      if (operator === '>=' || operator === '>') {
        setDateFrom(dateValue)
      } else if (operator === '<=' || operator === '<') {
        setDateTo(dateValue)
      }
      remainingQuery = remainingQuery.replace(dateComparePattern, '').trim()
    }

    // Remove any trailing AND/OR from query after removing date filter
    remainingQuery = remainingQuery.replace(/\s+(AND|OR)\s*$/i, '').trim()
    remainingQuery = remainingQuery.replace(/^\s*(AND|OR)\s+/i, '').trim()

    // Now parse remaining field:value patterns
    const fieldPattern = /(\w+):([^\s]+)/g
    const matches = [...remainingQuery.matchAll(fieldPattern)]

    // Map field to our internal field names
    const fieldMapping = {
      tag: 'tags',
      tags: 'tags',
      species: 'species',
      name: 'name',
      filename: 'filename',
      notes: 'notes',
    }

    if (matches.length > 0) {
      const parsedConditions = matches
        .filter(match => match[1] !== 'date') // Skip any remaining date: patterns
        .map(match => {
          const [, field, value] = match
          const mappedField = fieldMapping[field] || 'any'
          return { field: mappedField, operator: 'contains', value }
        })

      if (parsedConditions.length > 0) {
        setConditions(parsedConditions)
      }
    } else if (!dateRangeMatch && !dateCompareMatch) {
      // No field:value patterns and no date filter - might be plain text search
      if (remainingQuery.trim()) {
        setConditions([{ field: 'any', operator: 'contains', value: remainingQuery.trim() }])
      }
    }
  }

  // Generate query from current conditions
  const generateQuery = () => {
    // Build query from conditions
    const conditionQueries = conditions
      .filter(c => c.value.trim())
      .map(condition => {
        const field = FIELD_OPTIONS.find(f => f.value === condition.field)
        const prefix = field?.queryPrefix || ''
        let queryValue = condition.value.trim()

        // Apply operator transformations
        switch (condition.operator) {
          case 'equals':
            // Wrap in quotes for exact match
            queryValue = `"${queryValue}"`
            break
          case 'starts_with':
            // Add asterisk for prefix match
            queryValue = `${queryValue}*`
            break
          case 'excludes':
            // Add NOT operator
            return prefix ? `NOT ${prefix}:${queryValue}` : `NOT ${queryValue}`
          case 'contains':
          default:
            // Default behavior
            break
        }

        return prefix ? `${prefix}:${queryValue}` : queryValue
      })

    // Join conditions with boolean operator
    let query = conditionQueries.join(` ${booleanOperator} `)

    // Add date range if provided
    if (dateFrom && dateTo) {
      const dateQuery = `date:${dateFrom}..${dateTo}`
      query = query ? `${query} AND ${dateQuery}` : dateQuery
    }

    return query
  }

  // Add a new condition
  const addCondition = () => {
    setConditions([...conditions, { field: 'tags', operator: 'contains', value: '' }])
  }

  // Remove a condition
  const removeCondition = (index) => {
    if (conditions.length > 1) {
      const newConditions = conditions.filter((_, i) => i !== index)
      setConditions(newConditions)
    }
  }

  // Update a condition
  const updateCondition = (index, updates) => {
    const newConditions = [...conditions]
    newConditions[index] = { ...newConditions[index], ...updates }
    setConditions(newConditions)
  }

  // Clear all conditions
  const clearAll = () => {
    setConditions([{ field: 'tags', operator: 'contains', value: '' }])
    setBooleanOperator('AND')
    setDateFrom('')
    setDateTo('')
  }

  // Apply search
  const handleApply = () => {
    const query = generateQuery()
    onQueryChange?.(query)
  }

  // Get current query preview
  const queryPreview = generateQuery()

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
            {conditions.map((condition, index) => (
              <div key={index}>
                {/* Condition row */}
                <div className="flex items-center gap-2">
                  {/* Field select */}
                  <select
                    aria-label="Field"
                    value={condition.field}
                    onChange={(e) => updateCondition(index, { field: e.target.value })}
                    className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                               focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                               bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  >
                    {FIELD_OPTIONS.map(option => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>

                  {/* Operator select */}
                  <select
                    aria-label="Operator"
                    value={condition.operator}
                    onChange={(e) => updateCondition(index, { operator: e.target.value })}
                    className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                               focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                               bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  >
                    {OPERATOR_OPTIONS.map(option => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>

                  {/* Value input */}
                  <input
                    type="text"
                    aria-label="Value"
                    value={condition.value}
                    onChange={(e) => updateCondition(index, { value: e.target.value })}
                    placeholder="Enter value..."
                    className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                               focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                               bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                               placeholder-gray-500 dark:placeholder-gray-400"
                  />

                  {/* Remove button (only show if more than one condition) */}
                  {conditions.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeCondition(index)}
                      aria-label="Remove"
                      className="p-2 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20
                                 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                    >
                      <XMarkIcon className="w-5 h-5" />
                    </button>
                  )}
                </div>

                {/* Boolean operator (show between conditions) */}
                {index < conditions.length - 1 && (
                  <div className="flex items-center justify-center my-2">
                    <select
                      aria-label="Combine with"
                      value={booleanOperator}
                      onChange={(e) => setBooleanOperator(e.target.value)}
                      className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-md
                                 focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                                 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
                                 text-sm font-medium"
                    >
                      {BOOLEAN_OPTIONS.map(option => (
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
              onClick={addCondition}
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
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
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
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
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

AdvancedSearchBuilder.propTypes = {
  onQueryChange: PropTypes.func.isRequired,
  onClose: PropTypes.func.isRequired,
  initialQuery: PropTypes.string,
}

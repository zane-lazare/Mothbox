import { useState, useMemo, useCallback } from 'react'
import PropTypes from 'prop-types'
import { useQuery } from '@tanstack/react-query'
import { MagnifyingGlassIcon } from '@heroicons/react/24/outline'
import { useFilterContext } from '../../contexts/FilterContext'
import { api } from '../../utils/api'

/**
 * CustomFieldsFilter Component
 *
 * Dynamic custom fields filter that fetches available fields from the API
 * and displays appropriate input controls based on field type.
 *
 * Features:
 * - Auto-discovery of custom fields from sidecar metadata
 * - Text fields: text input with search
 * - Number fields: numeric input with range
 * - Select fields: dropdown with discovered values
 * - Loading, empty, and error states
 * - Integration with FilterContext
 *
 * @component
 * @example
 * <FilterSection id="customFields" title="Custom Fields">
 *   <CustomFieldsFilter />
 * </FilterSection>
 */
export function CustomFieldsFilter() {
  const { customFields, setCustomField } = useFilterContext()
  const [searchQueries, setSearchQueries] = useState({}) // Track search per text field

  // Fetch custom fields from API
  const {
    data: fieldsData,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['customFields'],
    queryFn: () => api.get('/sidecar/custom-fields').then(res => res.data),
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
    gcTime: 10 * 60 * 1000, // Keep in cache for 10 minutes
  })

  // Extract fields array
  const fields = useMemo(() => {
    if (!fieldsData?.fields) return []
    return fieldsData.fields
  }, [fieldsData])

  // Handle text field change
  const handleTextChange = useCallback((fieldName, value) => {
    setCustomField(fieldName, value || null)
  }, [setCustomField])

  // Handle number field change
  const handleNumberChange = useCallback((fieldName, value) => {
    const numValue = value === '' ? null : Number(value)
    setCustomField(fieldName, numValue)
  }, [setCustomField])

  // Handle select field change
  const handleSelectChange = useCallback((fieldName, value) => {
    setCustomField(fieldName, value || null)
  }, [setCustomField])

  // Handle search query change for text fields
  const handleSearchQueryChange = useCallback((fieldName, value) => {
    setSearchQueries(prev => ({
      ...prev,
      [fieldName]: value,
    }))
  }, [])

  // Render input based on field type
  const renderFieldInput = useCallback((field) => {
    const currentValue = customFields[field.name] || ''

    switch (field.type) {
      case 'text': {
        const searchQuery = searchQueries[field.name] || ''

        return (
          <div className="space-y-2">
            {/* Search input for text fields */}
            <div className="relative">
              <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                <MagnifyingGlassIcon className="h-4 w-4 text-gray-400" aria-hidden="true" />
              </div>
              <input
                type="text"
                placeholder={`Search ${field.name}...`}
                value={searchQuery}
                onChange={(e) => handleSearchQueryChange(field.name, e.target.value)}
                className="w-full pl-10 pr-3 py-2 text-sm
                         border border-gray-300 dark:border-gray-600
                         rounded-md
                         bg-white dark:bg-gray-800
                         text-gray-900 dark:text-gray-100
                         placeholder-gray-400 dark:placeholder-gray-500
                         focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                         transition-colors duration-150"
                aria-label={`Search ${field.name}`}
              />
            </div>

            {/* Display discovered values as clickable options */}
            {field.values && field.values.length > 0 && (
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {field.values
                  .filter(val => !searchQuery || val.toLowerCase().includes(searchQuery.toLowerCase()))
                  .map(value => {
                    const isSelected = currentValue === value

                    return (
                      <button
                        key={value}
                        type="button"
                        onClick={() => handleTextChange(field.name, isSelected ? '' : value)}
                        className={`w-full text-left px-3 py-2 text-sm rounded
                                 transition-colors duration-150
                                 ${isSelected
                                   ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-medium'
                                   : 'bg-gray-50 dark:bg-gray-700/50 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                                 }`}
                        aria-label={`Select ${value} for ${field.name}`}
                        aria-pressed={isSelected}
                      >
                        {value}
                      </button>
                    )
                  })}
              </div>
            )}

            {/* Show message when no values match search */}
            {field.values && field.values.length > 0 && searchQuery &&
             field.values.filter(val => val.toLowerCase().includes(searchQuery.toLowerCase())).length === 0 && (
              <div className="text-sm text-gray-500 dark:text-gray-400 text-center py-2">
                No values match &quot;{searchQuery}&quot;
              </div>
            )}
          </div>
        )
      }

      case 'number': {
        return (
          <div className="space-y-2">
            <input
              type="number"
              placeholder={`Enter ${field.name}...`}
              value={currentValue}
              onChange={(e) => handleNumberChange(field.name, e.target.value)}
              min={field.min}
              max={field.max}
              step="any"
              className="w-full px-3 py-2 text-sm
                       border border-gray-300 dark:border-gray-600
                       rounded-md
                       bg-white dark:bg-gray-800
                       text-gray-900 dark:text-gray-100
                       placeholder-gray-400 dark:placeholder-gray-500
                       focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                       transition-colors duration-150"
              aria-label={`Enter ${field.name}`}
            />
            {(field.min !== undefined || field.max !== undefined) && (
              <div className="text-xs text-gray-500 dark:text-gray-400">
                Range: {field.min ?? '-∞'} to {field.max ?? '∞'}
              </div>
            )}
          </div>
        )
      }

      case 'select': {
        return (
          <select
            value={currentValue}
            onChange={(e) => handleSelectChange(field.name, e.target.value)}
            className="w-full px-3 py-2 text-sm
                     border border-gray-300 dark:border-gray-600
                     rounded-md
                     bg-white dark:bg-gray-800
                     text-gray-900 dark:text-gray-100
                     focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                     transition-colors duration-150"
            aria-label={`Select ${field.name}`}
          >
            <option value="">Select {field.name}...</option>
            {field.options && field.options.map(option => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        )
      }

      default:
        return null
    }
  }, [customFields, searchQueries, handleTextChange, handleNumberChange, handleSelectChange, handleSearchQueryChange])

  // Loading state
  if (isLoading) {
    return (
      <div className="p-4">
        <div className="flex items-center justify-center py-8">
          <div className="animate-pulse text-gray-500 dark:text-gray-400">
            Loading custom fields...
          </div>
        </div>
      </div>
    )
  }

  // Error state
  if (isError) {
    return (
      <div className="p-4">
        <div className="text-sm text-red-600 dark:text-red-400">
          Failed to load custom fields: {error?.message || 'Unknown error'}
        </div>
      </div>
    )
  }

  // Empty state - no custom fields available
  if (fields.length === 0) {
    return (
      <div className="p-4">
        <div className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
          No custom fields available
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 space-y-4">
      {fields.map(field => (
        <div key={field.name} className="space-y-2">
          {/* Field Label */}
          <label
            htmlFor={`custom-field-${field.name}`}
            className="block text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            {field.name}
          </label>

          {/* Field Input */}
          <div id={`custom-field-${field.name}`}>
            {renderFieldInput(field)}
          </div>
        </div>
      ))}
    </div>
  )
}

CustomFieldsFilter.propTypes = {
  // No props - uses FilterContext
}

export default CustomFieldsFilter

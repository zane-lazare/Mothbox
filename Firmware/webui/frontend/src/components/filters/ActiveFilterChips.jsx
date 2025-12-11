import { memo, useCallback } from 'react'
import PropTypes from 'prop-types'
import { XMarkIcon } from '@heroicons/react/20/solid'
import { useFilterContext } from '../../contexts/FilterContext'
import { getActiveFilterSummaries } from '../../utils/filterQueryBuilder'

/**
 * ActiveFilterChips Component
 *
 * Displays active filters as removable chips above the gallery.
 * Shows filter type and value with click-to-remove functionality.
 *
 * @component
 * @example
 * // Basic usage (gets filters from context)
 * <ActiveFilterChips />
 *
 * @example
 * // With custom className
 * <ActiveFilterChips className="mb-4" />
 */
function ActiveFilterChips({ className = '' }) {
  const { clearFilter, clearAllFilters, ...filterState } = useFilterContext()

  // Get active filter summaries using the utility function
  const summaries = getActiveFilterSummaries(filterState)

  // Handle removing a filter
  const handleRemoveFilter = useCallback((filterType) => {
    clearFilter(filterType)
  }, [clearFilter])

  // Handle clearing all filters
  const handleClearAll = useCallback(() => {
    clearAllFilters()
  }, [clearAllFilters])

  // Don't render anything if no active filters
  if (summaries.length === 0) {
    return null
  }

  return (
    <div
      className={`flex flex-wrap items-center gap-2 ${className}`}
      role="group"
      aria-label="Active filters"
    >
      {summaries.map((summary, index) => (
        <FilterChip
          key={`${summary.type}-${index}`}
          label={summary.label}
          value={summary.value}
          onRemove={() => handleRemoveFilter(summary.type)}
        />
      ))}

      {summaries.length > 1 && (
        <button
          type="button"
          onClick={handleClearAll}
          className="
            text-xs px-2 py-1 rounded-md font-medium
            text-gray-700 dark:text-gray-300
            hover:bg-gray-100 dark:hover:bg-gray-700
            focus:outline-none focus:ring-2 focus:ring-blue-500
            transition-colors duration-150
          "
          aria-label="Clear all filters"
        >
          Clear all
        </button>
      )}
    </div>
  )
}

ActiveFilterChips.propTypes = {
  /** Additional CSS classes */
  className: PropTypes.string,
}

/**
 * FilterChip Component
 *
 * Individual filter chip with label, value, and remove button.
 * Internal component used by ActiveFilterChips.
 */
function FilterChip({ label, value, onRemove }) {
  const handleRemove = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    onRemove()
  }, [onRemove])

  const handleRemoveKeyDown = useCallback((e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      handleRemove(e)
    }
  }, [handleRemove])

  // Truncate long values to prevent overflow
  const truncatedValue = value.length > 40 ? `${value.substring(0, 37)}...` : value

  return (
    <div
      className="
        inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full
        bg-blue-100 dark:bg-blue-900
        text-blue-800 dark:text-blue-200
        text-xs font-medium
        transition-colors duration-150
      "
      role="status"
      aria-label={`Filter: ${label}: ${value}`}
    >
      <span className="font-semibold">{label}:</span>
      <span className="opacity-90" title={value}>
        {truncatedValue}
      </span>
      <button
        type="button"
        onClick={handleRemove}
        onKeyDown={handleRemoveKeyDown}
        className="
          ml-0.5 -mr-1 p-0.5 rounded-full
          hover:bg-blue-200 dark:hover:bg-blue-800
          focus:outline-none focus:ring-2 focus:ring-blue-500
          transition-colors duration-150
        "
        aria-label={`Remove ${label} filter`}
        tabIndex={0}
      >
        <XMarkIcon className="h-3.5 w-3.5" aria-hidden="true" />
      </button>
    </div>
  )
}

FilterChip.propTypes = {
  /** Filter label (e.g., "Date", "Tag", "Species") */
  label: PropTypes.string.isRequired,
  /** Filter value (e.g., "Last 7 Days", "moth") */
  value: PropTypes.string.isRequired,
  /** Remove button handler */
  onRemove: PropTypes.func.isRequired,
}

export default memo(ActiveFilterChips)

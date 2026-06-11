import { XMarkIcon } from '@heroicons/react/24/outline'
import { useFilterContext } from '../../contexts/FilterContext'

/**
 * FilterDrawerHeader Component
 *
 * Header for the filter drawer with title, active filter count badge,
 * clear all button, and close button.
 *
 * @example
 * <FilterDrawerHeader />
 */
export function FilterDrawerHeader() {
  const { activeFilterCount, hasActiveFilters, clearAllFilters, toggleDrawer } = useFilterContext()

  return (
    <div className="flex-shrink-0 border-b border-gray-200 dark:border-gray-700 p-4">
      <div className="flex items-center justify-between mb-3">
        {/* Title with badge */}
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Filters
          </h2>
          {hasActiveFilters && (
            <span
              className="inline-flex items-center justify-center min-w-[1.5rem] h-6 px-2
                         bg-blue-600 text-white text-xs font-medium rounded-full"
              aria-label={`${activeFilterCount} active filter${activeFilterCount !== 1 ? 's' : ''}`}
            >
              {activeFilterCount}
            </span>
          )}
        </div>

        {/* Close button - Hidden on desktop, shown on tablet/mobile */}
        <button
          onClick={toggleDrawer}
          aria-label="Close filters"
          className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700
                     focus:outline-none focus:ring-2 focus:ring-blue-500
                     lg:hidden"
        >
          <XMarkIcon className="h-5 w-5 text-gray-500 dark:text-gray-400" />
        </button>
      </div>

      {/* Clear All button */}
      <button
        onClick={clearAllFilters}
        disabled={!hasActiveFilters}
        className="w-full px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300
                   bg-gray-100 dark:bg-gray-700 rounded-md
                   hover:bg-gray-200 dark:hover:bg-gray-600
                   disabled:opacity-50 disabled:cursor-not-allowed
                   focus:outline-none focus:ring-2 focus:ring-blue-500
                   transition-colors duration-200"
        aria-label="Clear all filters"
      >
        Clear All
      </button>
    </div>
  )
}

export default FilterDrawerHeader

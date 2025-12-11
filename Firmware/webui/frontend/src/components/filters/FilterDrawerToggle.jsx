import { FunnelIcon } from '@heroicons/react/24/outline'
import { useFilterContext } from '../../contexts/FilterContext'

/**
 * FilterDrawerToggle Component
 *
 * Toolbar button to open the filter drawer. Shows a badge with the
 * active filter count when filters are applied.
 *
 * This button is typically placed in the gallery toolbar and is hidden
 * on desktop (≥1024px) where the drawer is always visible.
 *
 * @component
 * @example
 * <FilterDrawerToggle />
 */
export function FilterDrawerToggle() {
  const { activeFilterCount, hasActiveFilters, toggleDrawer } = useFilterContext()

  return (
    <button
      onClick={toggleDrawer}
      aria-label={`Show filters${hasActiveFilters ? ` (${activeFilterCount} active)` : ''}`}
      className="relative p-2 rounded-md text-gray-700 dark:text-gray-300
                 hover:bg-gray-100 dark:hover:bg-gray-700
                 focus:outline-none focus:ring-2 focus:ring-blue-500"
    >
      <FunnelIcon className="h-5 w-5" aria-hidden="true" />

      {/* Badge */}
      {hasActiveFilters && (
        <span
          className="absolute -top-1 -right-1 inline-flex items-center justify-center
                     min-w-[1.25rem] h-5 px-1.5 bg-blue-600 text-white text-xs
                     font-medium rounded-full"
          aria-hidden="true"
        >
          {activeFilterCount}
        </span>
      )}
    </button>
  )
}

export default FilterDrawerToggle

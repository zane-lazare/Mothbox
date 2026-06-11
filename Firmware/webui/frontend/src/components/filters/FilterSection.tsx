import { useMemo, type ReactNode } from 'react'
import { ChevronDownIcon } from '@heroicons/react/24/outline'
import { useFilterContext } from '../../contexts/FilterContext'

export interface FilterSectionProps {
  /** Section identifier (must match filter type in context) */
  id: string
  /** Display title for the section */
  title: string
  /** Filter content to render when expanded */
  children: ReactNode
  /** Initial expanded state (default: false) */
  defaultExpanded?: boolean
}

/**
 * FilterSection Component
 *
 * Collapsible accordion section for filter groups with:
 * - Smooth CSS transitions
 * - Active indicator dot when filter has values
 * - Keyboard accessibility (Enter/Space to toggle)
 * - ARIA attributes for screen readers
 *
 * @component
 * @example
 * <FilterSection id="tags" title="Tags" defaultExpanded={false}>
 *   <TagFilter />
 * </FilterSection>
 */
export function FilterSection({ id, title, children, defaultExpanded = false }: FilterSectionProps) {
  const {
    expandedSections,
    toggleSection,
    dateRange,
    tags,
    species,
    fileTypes,
    cameraSettings,
    notes,
    customFields,
  } = useFilterContext()

  // Determine if this section should be expanded
  const isExpanded = useMemo(() => {
    if (expandedSections.includes(id)) {
      return true
    }
    // Check if this is the first render and default should apply
    if (defaultExpanded && !expandedSections.some(s => s !== 'dateRange')) {
      return true
    }
    return false
  }, [expandedSections, id, defaultExpanded])

  // Determine if this filter section has active values
  const hasActiveValues = useMemo(() => {
    switch (id) {
      case 'dateRange':
        return Boolean(dateRange.preset || dateRange.startDate || dateRange.endDate)

      case 'tags':
        return tags.selected.length > 0

      case 'species':
        return species.selected.length > 0 || species.includeUnidentified

      case 'fileTypes':
        return fileTypes.selected.length > 0

      case 'cameraSettings':
        return (
          cameraSettings.iso.min !== null ||
          cameraSettings.iso.max !== null ||
          cameraSettings.aperture.min !== null ||
          cameraSettings.aperture.max !== null ||
          cameraSettings.shutterSpeed.min !== null ||
          cameraSettings.shutterSpeed.max !== null
        )

      case 'notes':
        return notes.hasNotes !== null || Boolean(notes.keywords)

      case 'customFields':
        return Object.keys(customFields).length > 0

      default:
        return false
    }
  }, [id, dateRange, tags, species, fileTypes, cameraSettings, notes, customFields])

  // Handle toggle via click or keyboard
  const handleToggle = () => {
    toggleSection(id)
  }

  // Handle keyboard events
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      handleToggle()
    }
  }

  return (
    <div className="border-b border-gray-200 dark:border-gray-700">
      {/* Section Header */}
      <button
        onClick={handleToggle}
        onKeyDown={handleKeyDown}
        aria-expanded={isExpanded}
        aria-controls={`filter-section-${id}`}
        className="w-full flex items-center justify-between p-4
                   text-left hover:bg-gray-50 dark:hover:bg-gray-700/50
                   focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500
                   transition-colors duration-200"
      >
        <div className="flex items-center gap-2">
          {/* Active indicator dot */}
          {hasActiveValues && (
            <span
              className="w-2 h-2 bg-blue-600 rounded-full"
              aria-label="Active filter"
            />
          )}
          <span className="font-medium text-gray-900 dark:text-gray-100">
            {title}
          </span>
        </div>

        {/* Chevron icon */}
        <ChevronDownIcon
          className={`h-5 w-5 text-gray-500 dark:text-gray-400
                     transition-transform duration-200
                     ${isExpanded ? 'rotate-180' : 'rotate-0'}`}
          aria-hidden="true"
        />
      </button>

      {/* Section Content */}
      <div
        id={`filter-section-${id}`}
        className={`overflow-hidden transition-all duration-200 ease-in-out
                   ${isExpanded ? 'max-h-[1000px] opacity-100' : 'max-h-0 opacity-0'}`}
        aria-hidden={!isExpanded}
      >
        {children}
      </div>
    </div>
  )
}

export default FilterSection
